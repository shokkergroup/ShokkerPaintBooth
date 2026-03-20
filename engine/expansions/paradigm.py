"""
Shokker PARADIGM Expansion - "Exotic Materials"
=====================================================
10 finishes that exploit PBR physics in ways never attempted in sim racing.

These aren't just new textures. These are materials that shouldn't exist -
engineered by understanding how real-time PBR renderers interpret Metallic,
Roughness, and Clearcoat channels at the pixel level.

PBR PHYSICS EXPLOITS:
- Fresnel amplification: Tiny metallic differences invisible head-on become
  visible at glancing angles because Fresnel reflectance is non-linear
- Material state boundaries: Transition zones between M=0 (dielectric) and
  M=255 (conductor) create exotic-looking surface behaviors
- Roughness micro-variation: Sub-pixel roughness alternation tricks the GGX
  specular distribution into behaviors that don't exist in real materials
- Perceptual void: M=0 + R=255 + CC=0 creates "nothing" - the brain
  interprets zero-specular as transparency or absence

CONTENTS:
  10 Bases:       singularity, bioluminescent, liquid_obsidian, prismatic,
                  p_mercury, p_phantom, p_volcanic, arctic_ice, carbon_weave, nebula
  10 Patterns:    fresnel_ghost, caustic, dimensional, neural, p_plasma,
                  holographic, circuitboard, soundwave, p_topographic, p_tessellation
  17 Monolithics: void, living_chrome, quantum, p_aurora, magnetic, ember, stealth,
                  glass_armor, p_static, mercury_pool, phase_shift, gravity_well,
                  thin_film, blackbody, wormhole, crystal_lattice, pulse

PERFORMANCE v2: Capped point counts, PIL-rasterized axons, cached fields,
scipy KDTree Voronoi, larger quantum blocks with coherent noise.

Author: Shokker Engine - PARADIGM Series
"""

import numpy as np

def _paint_noop(paint, shape, mask, seed, pm, bb):
    return paint

from PIL import Image, ImageFilter, ImageDraw

try:
    from scipy.spatial import cKDTree
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# ================================================================
# HELPERS
# ================================================================

def _mgrid(shape):
    return np.mgrid[0:shape[0], 0:shape[1]]

def _noise(shape, scales, weights, seed):
    """Multi-octave noise."""
    h, w = shape
    result = np.zeros((h, w), dtype=np.float32)
    rng = np.random.RandomState(seed)
    for scale, weight in zip(scales, weights):
        sh, sw = max(1, h // scale), max(1, w // scale)
        small = rng.randn(sh, sw).astype(np.float32)
        mn, mx = small.min(), small.max()
        norm = ((small - mn) / (mx - mn + 1e-8) * 255).clip(0, 255).astype(np.uint8)
        img = Image.fromarray(norm).resize((w, h), Image.BILINEAR)
        arr = np.array(img).astype(np.float32) / 255.0
        arr = arr * (mx - mn) + mn
        result += arr * weight
    return result

def _voronoi(shape, n_points, seed):
    """Voronoi distance field + cell IDs. Uses scipy KDTree when available."""
    h, w = shape
    rng = np.random.RandomState(seed)
    pts = np.column_stack([rng.randint(0, h, n_points), rng.randint(0, w, n_points)])

    if HAS_SCIPY:
        tree = cKDTree(pts)
        y, x = np.mgrid[0:h, 0:w]
        coords = np.column_stack([y.ravel(), x.ravel()]).astype(np.float32)
        min_dist, cell_id = tree.query(coords, k=1)
        min_dist = min_dist.reshape(h, w).astype(np.float32)
        cell_id = cell_id.reshape(h, w).astype(np.int32)
    else:
        y, x = _mgrid(shape)
        yf = y.astype(np.float32)
        xf = x.astype(np.float32)
        min_dist = np.full((h, w), 1e9, dtype=np.float32)
        cell_id = np.zeros((h, w), dtype=np.int32)
        for i, (py, px) in enumerate(pts):
            d = np.sqrt((yf - py)**2 + (xf - px)**2)
            closer = d < min_dist
            cell_id[closer] = i
            min_dist = np.minimum(min_dist, d)
    return min_dist, cell_id, pts

def _hsv_to_rgb(h, s, v):
    """Vectorized HSV to RGB."""
    c = v * s
    hp = h * 6.0
    x = c * (1 - np.abs(hp % 2 - 1))
    r = np.zeros_like(c); g = np.zeros_like(c); b = np.zeros_like(c)
    for lo in range(6):
        m = (hp >= lo) & (hp < lo + 1)
        if lo == 0: r[m] = c[m]; g[m] = x[m]
        elif lo == 1: r[m] = x[m]; g[m] = c[m]
        elif lo == 2: g[m] = c[m]; b[m] = x[m]
        elif lo == 3: g[m] = x[m]; b[m] = c[m]
        elif lo == 4: r[m] = x[m]; b[m] = c[m]
        elif lo == 5: r[m] = c[m]; b[m] = x[m]
    off = v - c
    return r + off, g + off, b + off


# ================================================================
# FIELD CACHES - avoid recomputing expensive fields across
# texture_* and paint_* calls for the same finish/seed
# ================================================================
_field_cache = {}

def _get_cached_field(key, compute_fn):
    """Cache expensive field computations. Keeps last 4 entries."""
    if key in _field_cache:
        return _field_cache[key]
    result = compute_fn()
    # Evict oldest if cache too large
    if len(_field_cache) >= 4:
        oldest = next(iter(_field_cache))
        del _field_cache[oldest]
    _field_cache[key] = result
    return result

def clear_paradigm_cache():
    """Call after a render completes to free memory."""
    _field_cache.clear()

# ================================================================
# BASE #1: SINGULARITY - Black hole gravitational lensing material
# ================================================================

def paint_singularity(paint, shape, mask, seed, pm, bb):
    """Singularity - DEVASTATING gravitational lensing with blazing accretion rings."""
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 5000)
    n_wells = max(3, (h * w) // (512 * 512) * 5 + 3)
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)

    accum = np.zeros((h, w), dtype=np.float32)
    ring_accum = np.zeros((h, w), dtype=np.float32)
    for _ in range(n_wells):
        cy = rng.randint(h // 8, 7 * h // 8)
        cx = rng.randint(w // 8, 7 * w // 8)
        mass = rng.uniform(40, 100)
        dist = np.sqrt((yf - cy)**2 + (xf - cx)**2) + 1e-3
        potential = np.clip(mass / dist, 0, 3.0)
        ring_r = mass * 0.8
        ring = np.exp(-((dist - ring_r)**2) / (mass * 2))
        accum += potential * 0.3 + ring * 0.7
        ring_accum += ring

    accum = accum / (accum.max() + 1e-8)
    ring_accum = ring_accum / (ring_accum.max() + 1e-8)

    # Heavy darkening in gravity wells
    darken = np.clip(accum * 2.0, 0, 1) * 0.60 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - darken * mask), 0, 1)

    # Blazing accretion ring glow - orange-white hot
    ring_bright = np.clip(ring_accum, 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + ring_bright * 0.35 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + ring_bright * 0.20 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + ring_bright * 0.10 * pm * mask, 0, 1)

    # Hot white center of rings
    ring_core = np.clip((ring_accum - 0.4) * 2.0, 0, 1) * 0.45 * pm
    paint = np.clip(paint + ring_core[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# BASE #2: BIOLUMINESCENT - Living glow-from-within material
# ================================================================

def paint_bioluminescent(paint, shape, mask, seed, pm, bb):
    """Bioluminescent - VIVID organic cell glow with pulsing bio-light veins."""
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 5101)

    # Cell structure at multiple scales
    cell_noise = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 5100)
    cell_noise = (cell_noise - cell_noise.min()) / (cell_noise.max() - cell_noise.min() + 1e-8)
    cells = np.clip((cell_noise - 0.35) * 3.0, 0, 1)

    # Darken non-glowing areas for contrast
    dark_base = (1 - cells) * 0.25 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - dark_base * mask, 0, 1)

    # Strong bio-glow: cyan-green luminescence
    glow = cells * 0.35 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + glow * 0.15 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + glow * 1.0 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + glow * 0.7 * mask, 0, 1)

    # Bio-vein network - fine-scale connecting lines between cells
    vein_noise = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 5102)
    vein_noise = (vein_noise - vein_noise.min()) / (vein_noise.max() - vein_noise.min() + 1e-8)
    veins = np.clip(1.0 - np.abs(vein_noise - 0.5) * 6.0, 0, 1) * cells
    vein_glow = veins * 0.20 * pm
    paint[:, :, 1] = np.clip(paint[:, :, 1] + vein_glow * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + vein_glow * 0.5 * mask, 0, 1)

    # Bright sparkle nodes where cells peak
    sparkle = rng.random(shape).astype(np.float32)
    bio_spark = np.where((sparkle > 0.96) & (cells > 0.4), 0.22 * pm, 0.0)
    paint = np.clip(paint + bio_spark[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.6 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# BASE #3: LIQUID OBSIDIAN - Flowing glass-metal phase boundary
# ================================================================

def paint_liquid_obsidian(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    flow = _noise(shape, [16, 32, 64], [0.25, 0.4, 0.35], seed + 5200)
    flow = (flow - flow.min()) / (flow.max() - flow.min() + 1e-8)

    glass_zone = np.clip(1.0 - flow, 0, 1)
    metal_zone = np.clip(flow, 0, 1)

    # Strong desaturation in glass zones for that cold obsidian look
    desaturate = glass_zone * 0.30 * pm
    gray = paint.mean(axis=2, keepdims=True)
    for c in range(3):
        paint[:, :, c] = np.clip(
            paint[:, :, c] * (1 - desaturate * mask) + gray[:, :, 0] * desaturate * mask,
            0, 1
        )

    # Darken glass zones heavily - obsidian is DARK
    glass_darken = glass_zone * 0.35 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - glass_darken * mask), 0, 1)

    # Metal flow zones get bright reflective highlights
    metal_bright = metal_zone * 0.18 * pm
    paint = np.clip(paint + metal_bright[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Phase boundary edges - bright white-blue glow where glass meets metal
    gx = np.abs(np.diff(flow, axis=1, prepend=flow[:, :1]))
    gy = np.abs(np.diff(flow, axis=0, prepend=flow[:1, :]))
    boundary = np.clip((gx + gy) * 12, 0, 1)
    bound_glow = boundary * 0.25 * pm
    paint[:, :, 1] = np.clip(paint[:, :, 1] + bound_glow * 0.5 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + bound_glow * mask, 0, 1)
    paint = np.clip(paint + bound_glow[:, :, np.newaxis] * 0.3 * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# PATTERN #1: FRESNEL GHOST - Hidden pattern visible only at angle
# ================================================================

def _compute_fresnel_ghost_field(shape, seed):
    """Fresnel reflection zones: concentric elliptical rings that simulate
    angle-dependent reflection at material boundaries, with ghost reflections
    and thin-film edge glow. Physically inspired by Fresnel equations."""
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32) / max(h, 1)
    xf = x.astype(np.float32) / max(w, 1)

    rng = np.random.RandomState(seed + 5200)

    # --- Primary Fresnel reflection centers (material boundary points) ---
    n_centers = rng.randint(3, 6)
    field = np.zeros((h, w), dtype=np.float32)

    for i in range(n_centers):
        cy = rng.uniform(0.15, 0.85)
        cx = rng.uniform(0.15, 0.85)
        # Elliptical distortion simulates oblique viewing angle
        aspect = rng.uniform(0.4, 1.8)
        rotation = rng.uniform(0, np.pi)
        # Rotated elliptical distance
        dy = yf - cy
        dx = xf - cx
        ry = dy * np.cos(rotation) - dx * np.sin(rotation)
        rx = (dy * np.sin(rotation) + dx * np.cos(rotation)) * aspect
        dist = np.sqrt(ry**2 + rx**2)

        # Fresnel-like ring spacing: rings get closer together at grazing angles
        # (mimics how Fresnel reflectance rises sharply near 90 degrees)
        ring_freq = 18.0 + i * 7.0
        # Non-linear spacing: sqrt makes rings denser at edges
        ring_phase = np.sqrt(dist + 0.001) * ring_freq
        rings = np.cos(ring_phase * 2.0 * np.pi) * 0.5 + 0.5
        # Fresnel falloff: intensity increases at grazing angles (outer rings)
        fresnel_intensity = np.clip(dist * 2.5, 0.05, 1.0) ** 0.6
        # Fade at extreme distance
        fade = np.clip(1.0 - dist * 1.2, 0, 1) ** 0.5
        field += rings * fresnel_intensity * fade * (0.7 + 0.3 * (i / max(n_centers - 1, 1)))

    # --- Ghost reflections: faint shifted duplicates of the primary pattern ---
    ghost = np.zeros((h, w), dtype=np.float32)
    for g in range(2):
        shift_y = rng.randint(-int(h * 0.08), int(h * 0.08))
        shift_x = rng.randint(-int(w * 0.08), int(w * 0.08))
        ghost += np.roll(np.roll(field, shift_y, axis=0), shift_x, axis=1) * (0.15 - g * 0.05)
    field = field + ghost

    # --- Thin-film edge glow: sharp bright edges at ring transitions ---
    # Compute gradient magnitude of the field for edge detection
    grad_y = np.abs(np.diff(field, axis=0, prepend=field[:1, :]))
    grad_x = np.abs(np.diff(field, axis=1, prepend=field[:, :1]))
    edge_glow = np.clip((grad_y + grad_x) * 8.0, 0, 1) ** 0.7
    field = field * 0.75 + edge_glow * 0.25

    # Normalize
    field = (field - field.min()) / (field.max() - field.min() + 1e-8)
    return field

def texture_fresnel_ghost(shape, mask, seed, sm):
    cache_key = ("fresnel_ghost", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_fresnel_ghost_field(shape, seed))
    return {
        "pattern_val": field,
        "R_range": 5.0,
        "M_range": 15.0,
        "CC": None
    }

def paint_fresnel_ghost(paint, shape, mask, seed, pm, bb):
    """Fresnel ghost - subtle iridescent edge glow at Fresnel zone boundaries."""
    if pm == 0.0:
        return paint
    cache_key = ("fresnel_ghost", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_fresnel_ghost_field(shape, seed))

    # Compute gradient for edge-only color shift
    grad_y = np.abs(np.diff(field, axis=0, prepend=field[:1, :]))
    grad_x = np.abs(np.diff(field, axis=1, prepend=field[:, :1]))
    edges = np.clip((grad_y + grad_x) * 6.0, 0, 1)

    # Subtle spectral shift on edges - thin-film interference color
    hue = (field * 0.6 + 0.55) % 1.0  # cyan-to-violet range
    r_i, g_i, b_i = _hsv_to_rgb(hue, np.full_like(hue, 0.3), np.full_like(hue, 0.6))
    blend = edges * 0.12 * pm * mask

    paint[:, :, 0] = np.clip(paint[:, :, 0] + (r_i - 0.3) * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (g_i - 0.3) * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + (b_i - 0.3) * blend, 0, 1)
    return paint

# ================================================================
# PATTERN #2: CAUSTIC - Underwater dancing light pattern
# ================================================================

def _compute_caustic_field(shape, seed):
    """Real caustic network: light focused through curved transparent surfaces.
    Uses overlapping plane waves refracted at different angles to create
    the characteristic bright focal lines seen on pool bottoms."""
    h, w = shape
    yf = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    xf = np.linspace(0, 1, w, dtype=np.float32)[None, :]

    rng = np.random.RandomState(seed + 5300)

    # --- Step 1: Create a bumpy water surface (height field) ---
    # Multiple overlapping ripple sources at random positions
    surface = np.zeros((h, w), dtype=np.float32)
    n_ripples = 8
    for _ in range(n_ripples):
        cx = rng.uniform(0, 1)
        cy = rng.uniform(0, 1)
        freq = rng.uniform(8, 25)
        phase = rng.uniform(0, 2 * np.pi)
        dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
        surface += np.sin(dist * freq * 2 * np.pi + phase) * rng.uniform(0.3, 1.0)

    # Add directional waves (wind-driven)
    for _ in range(4):
        angle = rng.uniform(0, 2 * np.pi)
        freq = rng.uniform(12, 35)
        phase = rng.uniform(0, 2 * np.pi)
        wave_coord = yf * np.cos(angle) + xf * np.sin(angle)
        surface += np.sin(wave_coord * freq * 2 * np.pi + phase) * rng.uniform(0.2, 0.6)

    # --- Step 2: Compute refraction (gradient of surface = ray deflection) ---
    # Caustics form where refracted rays converge (high curvature = bright)
    # Use second derivative (Laplacian) as proxy for light convergence
    grad_y = np.gradient(surface, axis=0)
    grad_x = np.gradient(surface, axis=1)
    # Laplacian = convergence of refracted rays
    laplacian = np.gradient(grad_y, axis=0) + np.gradient(grad_x, axis=1)

    # --- Step 3: Convert to caustic brightness ---
    # Real caustics have sharp bright lines (convergence) on dark background
    # Take absolute value: both convergence and divergence create features
    # but convergence (positive laplacian) is brighter
    caustic_raw = np.abs(laplacian)
    # Enhance contrast: caustics are very sharp bright lines
    caustic_raw = caustic_raw ** 0.6  # Gamma to bring out detail
    caustic_raw = (caustic_raw - caustic_raw.min()) / (caustic_raw.max() - caustic_raw.min() + 1e-8)

    # --- Step 4: Add the characteristic network structure ---
    # Real caustics have a connected web of bright lines, not just dots
    # Overlay the absolute gradient magnitude for connected lines
    grad_mag = np.sqrt(grad_y**2 + grad_x**2)
    grad_mag = (grad_mag - grad_mag.min()) / (grad_mag.max() - grad_mag.min() + 1e-8)
    # Invert: caustic lines appear where gradient is LOW (flat = focused)
    # combined with where curvature is HIGH (Laplacian)
    flat_zones = 1.0 - np.clip(grad_mag * 2.0, 0, 1)

    # Blend: bright where curvature is high AND surface is relatively flat
    caustic = caustic_raw * 0.7 + flat_zones * caustic_raw * 0.3
    # Sharpen the network lines
    caustic = np.clip(caustic * 2.0, 0, 1) ** 1.5
    # Final normalize
    caustic = (caustic - caustic.min()) / (caustic.max() - caustic.min() + 1e-8)
    return caustic

def texture_caustic(shape, mask, seed, sm):
    cache_key = ("caustic", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_caustic_field(shape, seed))
    return {
        "pattern_val": field,
        "R_range": -60.0,
        "M_range": 80.0,
        "CC": None
    }

def paint_caustic(paint, shape, mask, seed, pm, bb):
    """Caustic - bright aqua-white focal lines on subtle dark background."""
    if pm == 0.0:
        return paint
    cache_key = ("caustic", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_caustic_field(shape, seed))

    # Caustic highlights: warm white-cyan light focused through water
    bright = field ** 0.8
    # Light is slightly warm-cyan where concentrated
    paint[:, :, 0] = np.clip(paint[:, :, 0] + bright * 0.12 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + bright * 0.20 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + bright * 0.17 * pm * mask, 0, 1)
    # Darken areas between caustic lines slightly
    dark = (1.0 - field) * 0.03 * pm
    paint = np.clip(paint - dark[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# PATTERN #3: DIMENSIONAL - Newton's rings / thin-film interference
# ================================================================
# PERF FIX: ring_field now cached so texture_ and paint_ share it.
# Also capped n_centers to 15 max.

def _compute_dimensional_field(shape, seed):
    """Dimensional rift / portal effect: gravitational lensing distortion,
    event horizon rings, and spacetime curvature visualization.
    Simulates a wormhole/portal tearing through the paint surface."""
    h, w = shape
    yf = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    xf = np.linspace(-1, 1, w, dtype=np.float32)[None, :]

    rng = np.random.RandomState(seed + 5400)

    # --- Primary rift: a main portal aperture ---
    rift_cy = rng.uniform(-0.2, 0.2)
    rift_cx = rng.uniform(-0.2, 0.2)
    # Elliptical rift opening (not perfectly circular)
    aspect = rng.uniform(0.5, 0.8)
    angle = rng.uniform(0, np.pi)
    dy = yf - rift_cy
    dx = xf - rift_cx
    ry = dy * np.cos(angle) - dx * np.sin(angle)
    rx = (dy * np.sin(angle) + dx * np.cos(angle)) * aspect
    dist = np.sqrt(ry**2 + rx**2 + 1e-8)

    # --- Event horizon rings: sharp concentric rings that get denser near center ---
    # Logarithmic spacing mimics gravitational time dilation
    log_dist = np.log(dist * 5.0 + 0.01)
    horizon_rings = np.sin(log_dist * 12.0) * 0.5 + 0.5
    # Rings are sharper near the center (higher contrast)
    ring_sharpness = np.clip(1.0 - dist * 0.8, 0.2, 1.0)
    horizon = horizon_rings * ring_sharpness

    # --- Gravitational lensing distortion: warp the background ---
    # Displacement field that bends space around the rift
    warp_strength = 0.15 / (dist + 0.05)
    warp_angle = np.arctan2(ry, rx + 1e-8)
    # Spiral distortion (frame-dragging effect of rotating black hole)
    spiral = np.sin(warp_angle * 3.0 + log_dist * 4.0) * 0.5 + 0.5
    spiral *= np.clip(warp_strength * 2.0, 0, 1)

    # --- Accretion disk: bright ring at a specific radius ---
    accretion_radius = rng.uniform(0.25, 0.4)
    accretion_width = 0.06
    accretion = np.exp(-((dist - accretion_radius) / accretion_width)**2)
    # Accretion disk has angular structure (hotspots from orbiting matter)
    accretion *= (np.sin(warp_angle * 5.0 + rng.uniform(0, 6.28)) * 0.3 + 0.7)

    # --- Spacetime curvature grid lines (like a rubber sheet diagram) ---
    # Radial lines that bend around the rift
    radial_lines = np.sin(warp_angle * 12.0) * 0.5 + 0.5
    radial_lines *= np.clip(1.0 - dist * 0.5, 0, 0.6)
    # Concentric rings (coordinate grid)
    coord_rings = np.sin(dist * 30.0) * 0.5 + 0.5
    coord_rings *= np.clip(dist * 2.0 - 0.3, 0, 0.4)  # fade near center
    grid = (radial_lines + coord_rings) * 0.3

    # --- Secondary smaller rifts ---
    secondary = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(1, 3)):
        sy = rng.uniform(-0.7, 0.7)
        sx = rng.uniform(-0.7, 0.7)
        sd = np.sqrt((yf - sy)**2 + (xf - sx)**2 + 1e-8)
        s_rings = np.sin(np.log(sd * 8.0 + 0.01) * 8.0) * 0.5 + 0.5
        s_fade = np.clip(1.0 - sd * 2.0, 0, 1) ** 2
        secondary += s_rings * s_fade * 0.25

    # --- Compose ---
    field = horizon * 0.35 + spiral * 0.2 + accretion * 0.25 + grid + secondary
    # Void center: dark core of the rift
    void_core = np.clip(1.0 - np.exp(-(dist / 0.08)**2), 0, 1)
    field *= void_core

    field = (field - field.min()) / (field.max() - field.min() + 1e-8)
    return field, dist, warp_angle

def texture_dimensional(shape, mask, seed, sm):
    cache_key = ("dimensional", shape, seed)
    data = _get_cached_field(cache_key, lambda: _compute_dimensional_field(shape, seed))
    field = data[0]
    return {
        "pattern_val": field,
        "R_range": -50.0,
        "M_range": 60.0,
        "CC": None
    }

def paint_dimensional(paint, shape, mask, seed, pm, bb):
    """Dimensional rift - deep violet/cyan void with hot accretion glow."""
    if pm == 0.0:
        return paint
    cache_key = ("dimensional", shape, seed)
    data = _get_cached_field(cache_key, lambda: _compute_dimensional_field(shape, seed))
    field, dist, warp_angle = data

    # Color scheme: deep violet core -> cyan mid -> hot orange accretion
    # Map distance from rift center to a color gradient
    # Close to center: deep indigo/violet
    # Mid range: electric cyan
    # Accretion ring: hot orange-white
    t = np.clip(dist * 2.5, 0, 1)
    # Violet (0.75) -> Cyan (0.5) -> Orange (0.08)
    hue = 0.75 - t * 0.67
    hue = hue % 1.0
    sat = np.clip(0.7 - field * 0.2, 0.3, 0.9)
    val = np.clip(field * 0.8, 0.1, 0.7)

    r_i, g_i, b_i = _hsv_to_rgb(hue, sat, val)
    blend = 0.25 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + r_i * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + g_i * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + b_i * blend * mask, 0, 1)
    return paint


# ================================================================
# PATTERN #4: NEURAL - Living neural network mesh
# ================================================================
# PERF FIX v2: Capped to 40 neurons max. Axons rasterized via PIL
# ImageDraw (bitmap) instead of per-pixel distance math. Voronoi
# cached between texture and paint. ~100x faster on 2048x2048.

def _compute_neural_field(shape, seed):
    """Neural network visualization: soma nodes with branching dendrite trees,
    axon pathways connecting distant nodes, and synaptic clusters at junctions.
    Looks like a microscope view of stained neurons."""
    h, w = shape
    rng = np.random.RandomState(seed + 5500)

    # CAP: max 30 soma (cell bodies)
    n_soma = min(30, max(8, (h * w) // (300 * 300) + 5))
    soma_pts = np.column_stack([rng.randint(int(h*0.05), int(h*0.95), n_soma),
                                 rng.randint(int(w*0.05), int(w*0.95), n_soma)])

    # --- Rasterize everything via PIL for performance ---
    # Layer 1: Dendrite trees (thin branching lines from each soma)
    dendrite_img = Image.new('L', (w, h), 0)
    d_draw = ImageDraw.Draw(dendrite_img)
    dendrite_width = max(1, h // 1024)

    for i in range(n_soma):
        sy, sx = int(soma_pts[i][0]), int(soma_pts[i][1])
        # Each soma sprouts 3-6 primary dendrites
        n_dendrites = rng.randint(3, 7)
        for _ in range(n_dendrites):
            # Dendrite grows in a random direction with branching
            angle = rng.uniform(0, 2 * np.pi)
            length = rng.uniform(h * 0.04, h * 0.15)
            points = [(sx, sy)]
            cx, cy_p = float(sx), float(sy)
            seg_len = length / 5
            for seg in range(5):
                angle += rng.uniform(-0.6, 0.6)  # gentle curves
                cx += np.cos(angle) * seg_len
                cy_p += np.sin(angle) * seg_len
                points.append((int(np.clip(cx, 0, w-1)), int(np.clip(cy_p, 0, h-1))))
                # Branch at segments 2 and 4
                if seg in (2, 4) and rng.random() > 0.3:
                    branch_angle = angle + rng.choice([-1, 1]) * rng.uniform(0.4, 1.0)
                    bx, by = cx, cy_p
                    branch_pts = [(int(np.clip(bx, 0, w-1)), int(np.clip(by, 0, h-1)))]
                    for _ in range(3):
                        branch_angle += rng.uniform(-0.3, 0.3)
                        bx += np.cos(branch_angle) * seg_len * 0.6
                        by += np.sin(branch_angle) * seg_len * 0.6
                        branch_pts.append((int(np.clip(bx, 0, w-1)), int(np.clip(by, 0, h-1))))
                    if len(branch_pts) > 1:
                        d_draw.line(branch_pts, fill=180, width=dendrite_width)
            if len(points) > 1:
                d_draw.line(points, fill=220, width=dendrite_width + 1)

    dendrite_field = np.array(dendrite_img).astype(np.float32) / 255.0

    # Layer 2: Axon highways (thicker lines connecting distant somas)
    axon_img = Image.new('L', (w, h), 0)
    a_draw = ImageDraw.Draw(axon_img)
    axon_width = max(2, min(5, h // 400))

    # Connect each soma to 2-3 nearest neighbors with curved axons
    for i in range(n_soma):
        dists = np.sqrt(((soma_pts - soma_pts[i])**2).sum(axis=1))
        dists[i] = 1e9
        nearest = np.argsort(dists)[:rng.randint(2, 4)]
        for j in nearest:
            p1y, p1x = int(soma_pts[i][0]), int(soma_pts[i][1])
            p2y, p2x = int(soma_pts[j][0]), int(soma_pts[j][1])
            # Curved axon via a control point offset
            mid_x = (p1x + p2x) // 2 + rng.randint(-int(w*0.05), int(w*0.05))
            mid_y = (p1y + p2y) // 2 + rng.randint(-int(h*0.05), int(h*0.05))
            # Draw as two-segment polyline through midpoint
            a_draw.line([(p1x, p1y), (mid_x, mid_y), (p2x, p2y)], fill=255, width=axon_width)

            # Synaptic clusters: small dots at connection endpoints
            for r in range(2, 5):
                a_draw.ellipse([(p2x-r, p2y-r), (p2x+r, p2y+r)], fill=200)

    axon_field = np.array(axon_img).astype(np.float32) / 255.0

    # Layer 3: Soma bodies (bright circles at each node)
    soma_img = Image.new('L', (w, h), 0)
    s_draw = ImageDraw.Draw(soma_img)
    soma_radius = max(4, min(12, h // 180))
    for i in range(n_soma):
        sy, sx = int(soma_pts[i][0]), int(soma_pts[i][1])
        s_draw.ellipse([(sx-soma_radius, sy-soma_radius),
                        (sx+soma_radius, sy+soma_radius)], fill=255)
        # Nucleus (brighter center)
        nr = max(2, soma_radius // 2)
        s_draw.ellipse([(sx-nr, sy-nr), (sx+nr, sy+nr)], fill=255)

    soma_field = np.array(soma_img).astype(np.float32) / 255.0

    # --- Blur for organic look ---
    def _blur(arr, radius):
        img = Image.fromarray((arr * 255).clip(0, 255).astype(np.uint8))
        img = img.filter(ImageFilter.GaussianBlur(radius=radius))
        return np.array(img).astype(np.float32) / 255.0

    dendrite_field = _blur(dendrite_field, 1.5)
    axon_field = _blur(axon_field, 1.0)
    soma_field = _blur(soma_field, 2.0)

    # --- Compose: soma brightest, then axons, then dendrites ---
    pattern = np.clip(dendrite_field * 0.5 + axon_field * 0.7 + soma_field * 1.0, 0, 1)
    return soma_pts, dendrite_field, axon_field, soma_field, pattern

def texture_neural(shape, mask, seed, sm):
    cache_key = ("neural", shape, seed)
    fields = _get_cached_field(cache_key, lambda: _compute_neural_field(shape, seed))
    pattern = fields[4]
    return {
        "pattern_val": pattern,
        "R_range": -90.0,
        "M_range": 100.0,
        "CC": None
    }

def paint_neural(paint, shape, mask, seed, pm, bb):
    """Neural - bioluminescent glow: soma bright cyan, axons electric blue,
    dendrites faint green. Like fluorescent-stained neurons under microscope."""
    if pm == 0.0:
        return paint
    cache_key = ("neural", shape, seed)
    fields = _get_cached_field(cache_key, lambda: _compute_neural_field(shape, seed))
    _, dendrite_field, axon_field, soma_field, _ = fields

    # Soma glow: bright cyan-white
    blend_s = soma_field * 0.20 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + blend_s * 0.4 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + blend_s * 1.0 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + blend_s * 0.9 * mask, 0, 1)

    # Axon glow: electric blue
    blend_a = axon_field * 0.12 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + blend_a * 0.1 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + blend_a * 0.5 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + blend_a * 1.0 * mask, 0, 1)

    # Dendrite glow: faint green
    blend_d = dendrite_field * 0.08 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + blend_d * 0.2 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + blend_d * 0.8 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + blend_d * 0.3 * mask, 0, 1)
    return paint

# ================================================================
# PATTERN #5: PLASMA - Plasma ball discharge tendrils
# ================================================================

def _compute_plasma_field(shape, seed):
    """Real plasma physics: Lichtenberg figures with branching lightning-like
    filamentary discharge structures and ionization fronts.
    Uses diffusion-limited aggregation (DLA) inspired approach via PIL rasterization."""
    h, w = shape
    rng = np.random.RandomState(seed + 5510)

    # --- Generate Lichtenberg branching discharge via random walk trees ---
    discharge_img = Image.new('L', (w, h), 0)
    draw = ImageDraw.Draw(discharge_img)

    # Multiple discharge origins (electrodes)
    n_origins = rng.randint(2, 5)
    branch_width_base = max(2, h // 300)

    for orig in range(n_origins):
        # Origin point (can be edge or interior)
        if rng.random() > 0.5:
            # Edge origin
            edge = rng.randint(0, 4)
            if edge == 0: oy, ox = 0, rng.randint(0, w)
            elif edge == 1: oy, ox = h-1, rng.randint(0, w)
            elif edge == 2: oy, ox = rng.randint(0, h), 0
            else: oy, ox = rng.randint(0, h), w-1
        else:
            oy, ox = rng.randint(int(h*0.2), int(h*0.8)), rng.randint(int(w*0.2), int(w*0.8))

        # Grow branching tree from origin
        # Stack: (y, x, angle, generation, remaining_segments)
        stack = []
        n_main = rng.randint(3, 6)
        for _ in range(n_main):
            angle = rng.uniform(0, 2 * np.pi)
            stack.append((float(oy), float(ox), angle, 0, rng.randint(8, 20)))

        max_gen = 5
        while stack:
            cy, cx, angle, gen, remaining = stack.pop()
            if remaining <= 0 or gen > max_gen:
                continue

            # Segment length decreases with generation
            seg_len = rng.uniform(h * 0.02, h * 0.06) / (1.0 + gen * 0.4)
            # Jagged path: sharp random turns (lightning is NOT smooth)
            angle += rng.uniform(-0.8, 0.8)
            ny = cy + np.sin(angle) * seg_len
            nx = cx + np.cos(angle) * seg_len
            ny = float(np.clip(ny, 0, h-1))
            nx = float(np.clip(nx, 0, w-1))

            # Draw segment - thinner at higher generations
            line_w = max(1, branch_width_base - gen)
            brightness = max(80, 255 - gen * 35)
            draw.line([(int(cx), int(cy)), (int(nx), int(ny))], fill=brightness, width=line_w)

            # Continue main branch
            stack.append((ny, nx, angle, gen, remaining - 1))

            # Probability of branching increases at each segment
            if rng.random() < 0.35 - gen * 0.04:
                branch_angle = angle + rng.choice([-1, 1]) * rng.uniform(0.4, 1.2)
                branch_segs = max(2, remaining // 2 - gen)
                stack.append((ny, nx, branch_angle, gen + 1, branch_segs))

    # --- Ionization front glow: soft halo around discharge paths ---
    discharge_arr = np.array(discharge_img).astype(np.float32) / 255.0

    # Create glow by blurring the discharge pattern
    glow_img = Image.fromarray((discharge_arr * 255).astype(np.uint8))
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=max(3, h // 200)))
    glow_field = np.array(glow_img).astype(np.float32) / 255.0

    # Wider atmospheric glow
    atmo_img = Image.fromarray((discharge_arr * 255).astype(np.uint8))
    atmo_img = atmo_img.filter(ImageFilter.GaussianBlur(radius=max(8, h // 80)))
    atmo_field = np.array(atmo_img).astype(np.float32) / 255.0

    # --- Compose: sharp discharge + inner glow + atmospheric glow ---
    field = discharge_arr * 0.6 + glow_field * 0.3 + atmo_field * 0.15
    field = (field - field.min()) / (field.max() - field.min() + 1e-8)
    return field, discharge_arr, glow_field

def texture_plasma(shape, mask, seed, sm):
    cache_key = ("plasma", shape, seed)
    data = _get_cached_field(cache_key, lambda: _compute_plasma_field(shape, seed))
    field = data[0]
    return {"pattern_val": field, "R_range": -70.0, "M_range": 90.0, "CC": None}

def paint_plasma(paint, shape, mask, seed, pm, bb):
    """Plasma discharge: white-hot core fading to electric violet/blue corona."""
    if pm == 0.0:
        return paint
    cache_key = ("plasma", shape, seed)
    data = _get_cached_field(cache_key, lambda: _compute_plasma_field(shape, seed))
    field, discharge, glow = data

    # Core discharge: white-hot (high in all channels)
    core = discharge * 0.22 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + core * 0.9 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + core * 0.8 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + core * 1.0 * mask, 0, 1)

    # Glow corona: electric purple-violet
    corona = glow * 0.15 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + corona * 0.6 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + corona * 0.1 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + corona * 0.8 * mask, 0, 1)
    return paint


# ================================================================
# PATTERN #6: HOLOGRAPHIC - Hologram diffraction grating
# ================================================================

def _compute_holographic_field(shape, seed):
    """Diffractive hologram: visible diffraction grating lines with angular
    rainbow color separation. Simulates a holographic security sticker with
    multiple diffractive zones, each with its own grating angle and frequency.
    NOT simple iridescence - this has visible line structure."""
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    rng = np.random.RandomState(seed + 5525)

    # --- Zone map: divide surface into irregular diffractive zones ---
    # Each zone has its own grating orientation (like a real holographic sticker)
    n_zones = rng.randint(5, 10)
    zone_pts = np.column_stack([rng.randint(0, h, n_zones),
                                 rng.randint(0, w, n_zones)])
    if HAS_SCIPY:
        tree = cKDTree(zone_pts)
        coords = np.column_stack([yf.ravel(), xf.ravel()]).astype(np.float32)
        _, zone_id = tree.query(coords, k=1)
        zone_id = zone_id.reshape(h, w)
    else:
        zone_id = np.zeros((h, w), dtype=np.int32)
        min_d = np.full((h, w), 1e9, dtype=np.float32)
        for i, (py, px) in enumerate(zone_pts):
            d = (yf - py)**2 + (xf - px)**2
            closer = d < min_d
            zone_id[closer] = i
            min_d = np.minimum(min_d, d)

    # --- Per-zone diffraction gratings with unique angles and frequencies ---
    grating_angles = rng.uniform(0, np.pi, n_zones)
    grating_freqs = rng.uniform(0.15, 0.50, n_zones)  # lines per pixel

    # Build the grating field: each zone gets its own oriented line pattern
    grating = np.zeros((h, w), dtype=np.float32)
    hue_field = np.zeros((h, w), dtype=np.float32)

    for z in range(n_zones):
        zmask = (zone_id == z).astype(np.float32)
        angle = grating_angles[z]
        freq = grating_freqs[z]
        # Oriented grating lines
        line_coord = yf * np.cos(angle) + xf * np.sin(angle)
        lines = np.sin(line_coord * freq * 2 * np.pi) * 0.5 + 0.5
        # Add second harmonic for sharper grating appearance
        lines2 = np.sin(line_coord * freq * 4 * np.pi + 0.5) * 0.25 + 0.25
        zone_grating = np.clip(lines * 0.7 + lines2 * 0.3, 0, 1)
        grating += zone_grating * zmask
        # Each zone's hue offset (simulates different diffraction order colors)
        hue_field += (z / float(n_zones)) * zmask

    # --- Thin-film interference overlay (adds depth beyond just lines) ---
    # Radial distance from center creates viewing-angle-dependent color shift
    cy, cx = h * 0.5, w * 0.5
    dist_center = np.sqrt((yf - cy)**2 + (xf - cx)**2)
    dist_norm = dist_center / (np.sqrt(cy**2 + cx**2) + 1e-8)
    # Interference fringes that shift with distance (angular dependence)
    interference = np.sin(dist_norm * 25.0) * 0.5 + 0.5

    # --- Rainbow diffraction: hue varies along grating lines ---
    # The key visual: color changes along the perpendicular to each grating
    rainbow_field = np.zeros((h, w), dtype=np.float32)
    for z in range(n_zones):
        zmask = (zone_id == z).astype(np.float32)
        angle = grating_angles[z]
        # Color shifts perpendicular to grating lines
        perp_coord = -yf * np.sin(angle) + xf * np.cos(angle)
        perp_norm = (perp_coord - perp_coord.min()) / (perp_coord.max() - perp_coord.min() + 1e-8)
        rainbow_field += perp_norm * zmask

    # --- Zone boundary shimmer (bright edges between diffractive zones) ---
    # Detect zone boundaries via gradient of zone_id
    zone_float = zone_id.astype(np.float32)
    gy = np.abs(np.diff(zone_float, axis=0, prepend=zone_float[:1, :]))
    gx = np.abs(np.diff(zone_float, axis=1, prepend=zone_float[:, :1]))
    boundary = np.clip((gy + gx) * 0.5, 0, 1)

    # --- Compose: grating structure + interference + boundaries ---
    field = grating * 0.55 + interference * 0.15 + boundary * 0.30
    field = (field - field.min()) / (field.max() - field.min() + 1e-8)
    return field, rainbow_field, grating, boundary

def texture_holographic(shape, mask, seed, sm):
    cache_key = ("holographic", shape, seed)
    data = _get_cached_field(cache_key, lambda: _compute_holographic_field(shape, seed))
    field = data[0]
    return {"pattern_val": field, "R_range": -70.0, "M_range": 100.0, "CC": None}

def paint_holographic(paint, shape, mask, seed, pm, bb):
    """Diffractive hologram: vivid rainbow that shifts per-zone with visible grating lines."""
    if pm == 0.0:
        return paint
    cache_key = ("holographic", shape, seed)
    data = _get_cached_field(cache_key, lambda: _compute_holographic_field(shape, seed))
    field, rainbow_field, grating, boundary = data

    # Rainbow color from diffraction: full spectrum mapped across each zone
    hue = (rainbow_field * 1.2 + grating * 0.3) % 1.0
    sat = np.clip(0.85 + boundary * 0.15, 0, 1.0)
    val = np.clip(0.65 + grating * 0.2 + boundary * 0.15, 0, 0.9)
    r_s, g_s, b_s = _hsv_to_rgb(hue, sat, val)

    blend = 0.30 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + r_s * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + g_s * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + b_s * blend * mask, 0, 1)
    return paint


# ================================================================
# PATTERN #7: CIRCUITBOARD - PCB trace pattern
# ================================================================

def _compute_circuit_field(shape, seed):
    """Real PCB circuit board: grid-aligned copper traces with 90-degree turns,
    vias (plated through-holes), IC pads (rectangular footprints), solder points,
    and ground plane zones. All geometry is grid-snapped for authenticity."""
    h, w = shape
    rng = np.random.RandomState(seed + 5520)

    # Grid spacing for PCB alignment
    grid_size = max(8, min(20, h // 80))
    n_grid_y = h // grid_size
    n_grid_x = w // grid_size

    # --- Rasterize via PIL for performance ---
    # Layer 1: Copper traces (the main signal lines)
    trace_img = Image.new('L', (w, h), 0)
    t_draw = ImageDraw.Draw(trace_img)
    trace_w = max(2, grid_size // 4)

    # Generate traces: start at random grid point, route with 90-degree turns
    n_traces = min(80, max(20, (n_grid_y * n_grid_x) // 8))
    for _ in range(n_traces):
        # Start point snapped to grid
        gy = rng.randint(1, max(2, n_grid_y - 1))
        gx = rng.randint(1, max(2, n_grid_x - 1))
        py, px = gy * grid_size, gx * grid_size
        # Route: series of horizontal/vertical segments with 90-degree turns
        n_segs = rng.randint(2, 7)
        horizontal = rng.random() > 0.5  # starting direction
        points = [(px, py)]
        for seg in range(n_segs):
            length = rng.randint(2, max(3, min(12, n_grid_x // 3))) * grid_size
            if horizontal:
                direction = rng.choice([-1, 1])
                nx = int(np.clip(px + direction * length, grid_size, w - grid_size))
                points.append((nx, py))
                px = nx
            else:
                direction = rng.choice([-1, 1])
                ny = int(np.clip(py + direction * length, grid_size, h - grid_size))
                points.append((px, ny))
                py = ny
            horizontal = not horizontal  # alternate direction (90-degree turn)

        if len(points) > 1:
            t_draw.line(points, fill=200, width=trace_w)

    # Layer 2: Vias (small filled circles - plated through-holes)
    via_img = Image.new('L', (w, h), 0)
    v_draw = ImageDraw.Draw(via_img)
    via_radius = max(2, grid_size // 3)
    via_inner = max(1, via_radius // 2)
    n_vias = min(60, max(10, (n_grid_y * n_grid_x) // 12))

    for _ in range(n_vias):
        vy = rng.randint(2, max(3, n_grid_y - 2)) * grid_size
        vx = rng.randint(2, max(3, n_grid_x - 2)) * grid_size
        # Via annular ring (outer circle)
        v_draw.ellipse([(vx - via_radius, vy - via_radius),
                        (vx + via_radius, vy + via_radius)], fill=255)
        # Via drill hole (dark center)
        v_draw.ellipse([(vx - via_inner, vy - via_inner),
                        (vx + via_inner, vy + via_inner)], fill=80)

    # Layer 3: IC pads (rectangular component footprints)
    pad_img = Image.new('L', (w, h), 0)
    p_draw = ImageDraw.Draw(pad_img)
    n_ics = rng.randint(3, 8)

    for _ in range(n_ics):
        # IC body position snapped to grid
        ic_gy = rng.randint(3, max(4, n_grid_y - 5))
        ic_gx = rng.randint(3, max(4, n_grid_x - 5))
        ic_y = ic_gy * grid_size
        ic_x = ic_gx * grid_size
        # IC size in grid cells
        ic_h = rng.randint(2, 5) * grid_size
        ic_w = rng.randint(3, 7) * grid_size
        # IC body outline
        p_draw.rectangle([(ic_x, ic_y), (ic_x + ic_w, ic_y + ic_h)], outline=160, width=1)
        # Pin pads along two sides
        pin_spacing = grid_size
        n_pins = ic_w // pin_spacing
        pad_size = max(2, grid_size // 4)
        for p in range(n_pins):
            px_pin = ic_x + p * pin_spacing + pin_spacing // 2
            # Top row of pins
            p_draw.rectangle([(px_pin - pad_size, ic_y - pad_size * 2),
                              (px_pin + pad_size, ic_y)], fill=220)
            # Bottom row of pins
            p_draw.rectangle([(px_pin - pad_size, ic_y + ic_h),
                              (px_pin + pad_size, ic_y + ic_h + pad_size * 2)], fill=220)

    # Layer 4: Solder points at trace intersections (small bright dots)
    solder_img = Image.new('L', (w, h), 0)
    s_draw = ImageDraw.Draw(solder_img)
    # Find where traces exist on grid intersections and add solder dots
    trace_arr = np.array(trace_img)
    solder_r = max(2, grid_size // 5)
    for gy in range(1, n_grid_y - 1, 2):
        for gx in range(1, n_grid_x - 1, 2):
            py, px = gy * grid_size, gx * grid_size
            if py < h and px < w and trace_arr[py, px] > 100:
                s_draw.ellipse([(px - solder_r, py - solder_r),
                                (px + solder_r, py + solder_r)], fill=255)

    # Layer 5: Ground plane (faint copper fill in empty areas)
    # Use a cross-hatch pattern for ground plane visualization
    ground_img = Image.new('L', (w, h), 0)
    g_draw = ImageDraw.Draw(ground_img)
    hatch_spacing = grid_size * 2
    for i in range(-max(h, w), max(h, w) * 2, hatch_spacing):
        g_draw.line([(i, 0), (i + h, h)], fill=30, width=1)
        g_draw.line([(i + h, 0), (i, h)], fill=30, width=1)

    # --- Compose all layers ---
    trace_field = np.array(trace_img).astype(np.float32) / 255.0
    via_field = np.array(via_img).astype(np.float32) / 255.0
    pad_field = np.array(pad_img).astype(np.float32) / 255.0
    solder_field = np.array(solder_img).astype(np.float32) / 255.0
    ground_field = np.array(ground_img).astype(np.float32) / 255.0

    # Anti-alias with slight blur
    def _aa(arr):
        img = Image.fromarray((arr * 255).clip(0, 255).astype(np.uint8))
        img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
        return np.array(img).astype(np.float32) / 255.0

    trace_field = _aa(trace_field)

    field = np.clip(ground_field * 0.15 + trace_field * 0.65 + via_field * 0.8 +
                    pad_field * 0.7 + solder_field * 0.9, 0, 1)
    return field, trace_field, via_field

def texture_circuitboard(shape, mask, seed, sm):
    cache_key = ("circuit", shape, seed)
    data = _get_cached_field(cache_key, lambda: _compute_circuit_field(shape, seed))
    field = data[0]
    return {"pattern_val": field, "R_range": -80.0, "M_range": 110.0, "CC": None}

def paint_circuitboard(paint, shape, mask, seed, pm, bb):
    """Circuit board: copper traces get green-gold PCB tint, vias get bright solder shine."""
    if pm == 0.0:
        return paint
    cache_key = ("circuit", shape, seed)
    data = _get_cached_field(cache_key, lambda: _compute_circuit_field(shape, seed))
    field, trace_field, via_field = data

    # Copper trace tint: warm gold-green (classic PCB color)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + trace_field * 0.12 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + trace_field * 0.18 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - trace_field * 0.02 * pm * mask, 0, 1)

    # Via solder shine: bright silvery highlight
    via_bright = via_field * 0.15 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + via_bright * 0.8 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + via_bright * 0.8 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + via_bright * 0.9 * mask, 0, 1)

    # Subtle dark solder mask in background areas
    bg = (1.0 - field) * 0.02 * pm
    paint[:, :, 1] = np.clip(paint[:, :, 1] + bg * 0.4 * mask, 0, 1)  # green solder mask
    return paint


# ================================================================
# PATTERN #8: SOUNDWAVE - Audio waveform visualization
# ================================================================

def _compute_soundwave_field(shape, seed):
    """Audio waveform visualization: oscilloscope-style display with multiple
    frequency bands, amplitude modulation, sharp waveform peaks, and a
    spectrum analyzer bar graph at the bottom. Looks like a real DAW display."""
    h, w = shape
    rng = np.random.RandomState(seed + 5530)

    field = np.zeros((h, w), dtype=np.float32)
    yf = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    xf = np.linspace(0, 1, w, dtype=np.float32)[None, :]

    # --- Section 1: Main waveform display (top 60% of texture) ---
    # Multiple frequency bands stacked vertically
    n_bands = rng.randint(4, 7)
    band_height = 0.6 / n_bands  # each band occupies a portion of top 60%

    for band in range(n_bands):
        # Vertical center of this band in normalized coords (-1 to 1)
        band_center = -0.7 + band * (1.4 / n_bands) + (0.7 / n_bands)
        # Generate a complex waveform for this frequency band
        wave = np.zeros((1, w), dtype=np.float32)
        base_freq = 3.0 + band * 4.0  # higher bands = higher frequency
        # Fundamental + harmonics
        for harmonic in range(1, 4):
            freq = base_freq * harmonic
            amp = rng.uniform(0.1, 0.4) / harmonic
            phase = rng.uniform(0, 2 * np.pi)
            wave += amp * np.sin(xf * freq * 2 * np.pi + phase)
        # Amplitude modulation envelope (waveform isn't constant amplitude)
        env_freq = rng.uniform(0.5, 3.0)
        envelope = np.abs(np.sin(xf * env_freq * np.pi + rng.uniform(0, np.pi)))
        envelope = np.clip(envelope, 0.1, 1.0)
        wave *= envelope

        # Normalize wave amplitude
        wave = wave / (np.abs(wave).max() + 1e-8) * band_height * 0.8

        # Distance from waveform line -> sharp bright line
        dist = np.abs(yf - band_center - wave)
        # Crisp primary line
        line = np.exp(-(dist / 0.008)**2)
        # Softer glow around the line
        glow = np.exp(-(dist / 0.03)**2) * 0.4
        # Filled waveform (area between centerline and wave)
        filled = np.clip(1.0 - np.abs(yf - band_center) / (np.abs(wave) + 0.005), 0, 1) * 0.2
        field += line + glow + filled

    # --- Section 2: Spectrum analyzer bars (bottom 25%) ---
    n_bars = rng.randint(24, 48)
    bar_width_px = max(2, w // n_bars)
    bar_region_top = 0.5  # in normalized y coords (-1 to 1), 0.5 = bottom quarter

    for bar in range(n_bars):
        # Bar height (frequency energy level) - shaped like typical music spectrum
        # Bass heavy, mid present, treble tapering
        freq_pos = bar / float(n_bars)
        base_energy = np.exp(-((freq_pos - 0.15)**2) / 0.05) * 0.8  # bass bump
        base_energy += np.exp(-((freq_pos - 0.4)**2) / 0.08) * 0.5   # mid bump
        base_energy += rng.uniform(0.1, 0.5) * (1.0 - freq_pos * 0.5)  # random variation
        bar_height = np.clip(base_energy, 0.05, 0.9) * 0.45

        # Bar x range
        bar_left = bar * (w / n_bars)
        bar_right = bar_left + bar_width_px * 0.8  # gap between bars

        # Bar y range (grows upward from bottom)
        x_in_bar = (xf * w >= bar_left) & (xf * w < bar_right)
        y_in_bar = (yf > bar_region_top - bar_height) & (yf < bar_region_top + 0.05)
        bar_mask = (x_in_bar & y_in_bar).astype(np.float32)

        # Gradient: brighter at top of each bar
        bar_gradient = np.clip((bar_region_top + 0.05 - yf) / (bar_height + 0.01), 0, 1)
        field += bar_mask * bar_gradient * 0.7

        # Peak indicator: bright dot at top of each bar
        peak_y = bar_region_top - bar_height - 0.015
        peak_mask = (x_in_bar & (np.abs(yf - peak_y) < 0.008)).astype(np.float32)
        field += peak_mask * 0.9

    # --- Section 3: Horizontal scan lines (CRT/oscilloscope aesthetic) ---
    scanline_freq = h / 3.0  # density of scan lines
    scanlines = np.sin(np.arange(h, dtype=np.float32)[:, None] / h * scanline_freq * 2 * np.pi)
    scanlines = scanlines * 0.5 + 0.5
    field *= (0.85 + scanlines * 0.15)  # subtle scan line overlay

    # --- Section 4: Grid lines (oscilloscope graticule) ---
    # Horizontal grid lines
    n_hgrid = 8
    for i in range(n_hgrid):
        grid_y = -1.0 + i * 2.0 / n_hgrid
        grid_dist = np.abs(yf - grid_y)
        field += np.exp(-(grid_dist / 0.003)**2) * 0.15

    # Vertical grid lines (time divisions)
    n_vgrid = 10
    for i in range(n_vgrid):
        grid_x = i / float(n_vgrid)
        grid_dist = np.abs(xf - grid_x)
        field += np.exp(-(grid_dist / 0.003)**2) * 0.10

    field = np.clip(field, 0, 1)
    return field

def texture_soundwave(shape, mask, seed, sm):
    cache_key = ("soundwave", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_soundwave_field(shape, seed))
    return {"pattern_val": field, "R_range": -60.0, "M_range": 85.0, "CC": None}

def paint_soundwave(paint, shape, mask, seed, pm, bb):
    """Soundwave: green phosphor oscilloscope glow with hot-white peaks."""
    if pm == 0.0:
        return paint
    cache_key = ("soundwave", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_soundwave_field(shape, seed))

    # Classic green phosphor oscilloscope color
    # Dim areas: deep green. Bright areas: white-green (phosphor saturation)
    bright = field ** 0.7
    hot = np.clip(field - 0.6, 0, 1) * 2.5  # hot-white on peaks

    paint[:, :, 0] = np.clip(paint[:, :, 0] + (bright * 0.06 + hot * 0.16) * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (bright * 0.22 + hot * 0.10) * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + (bright * 0.03 + hot * 0.08) * pm * mask, 0, 1)

    # Darken background for contrast (oscilloscope has dark screen)
    dark_bg = (1.0 - field) * 0.03 * pm
    paint = np.clip(paint - dark_bg[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# PATTERN #9: TOPOGRAPHIC - Contour map elevation lines
# ================================================================

def _compute_topo_field(shape, seed):
    h, w = shape
    elevation = _noise(shape, [16, 32, 64, 128], [0.15, 0.25, 0.35, 0.25], seed + 5540)
    elevation = (elevation - elevation.min()) / (elevation.max() - elevation.min() + 1e-8)
    # Contour lines: sharp bands at regular elevation intervals
    n_contours = 20
    contour_val = elevation * n_contours
    contour_frac = contour_val - np.floor(contour_val)
    # Lines where fractional part is near 0 or 1
    line_field = np.clip(1.0 - np.minimum(contour_frac, 1.0 - contour_frac) * 8, 0, 1)
    return line_field

def texture_topographic(shape, mask, seed, sm):
    cache_key = ("topo", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_topo_field(shape, seed))
    return {"pattern_val": field, "R_range": -55.0, "M_range": 75.0, "CC": None}

def paint_topographic(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    cache_key = ("topo", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_topo_field(shape, seed))
    paint = np.clip(paint + field[:, :, np.newaxis] * 0.15 * pm * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# PATTERN #10: TESSELLATION - Geometric Penrose-style tiling
# ================================================================

def texture_tessellation(shape, mask, seed, sm):
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Overlapping triangular grids at 3 angles (60° apart) = hexagonal tessellation
    a1 = np.sin(yf * 0.06) * 0.5 + 0.5
    a2 = np.sin(yf * 0.03 + xf * 0.052) * 0.5 + 0.5  # 60°
    a3 = np.sin(-yf * 0.03 + xf * 0.052) * 0.5 + 0.5  # -60°
    # Threshold each to create edge lines
    e1 = np.clip(1.0 - np.abs(a1 - 0.5) * 8, 0, 1)
    e2 = np.clip(1.0 - np.abs(a2 - 0.5) * 8, 0, 1)
    e3 = np.clip(1.0 - np.abs(a3 - 0.5) * 8, 0, 1)
    field = np.clip(e1 + e2 + e3, 0, 1)
    return {"pattern_val": field, "R_range": -65.0, "M_range": 80.0, "CC": None}

def paint_tessellation(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    a1 = np.sin(yf * 0.06) * 0.5 + 0.5
    a2 = np.sin(yf * 0.03 + xf * 0.052) * 0.5 + 0.5
    a3 = np.sin(-yf * 0.03 + xf * 0.052) * 0.5 + 0.5
    e1 = np.clip(1.0 - np.abs(a1 - 0.5) * 8, 0, 1)
    e2 = np.clip(1.0 - np.abs(a2 - 0.5) * 8, 0, 1)
    e3 = np.clip(1.0 - np.abs(a3 - 0.5) * 8, 0, 1)
    field = np.clip(e1 + e2 + e3, 0, 1)
    paint = np.clip(paint + field[:, :, np.newaxis] * 0.15 * pm * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #1: VOID - Material with apparent holes/transparency
# ================================================================
# PERF FIX: Capped to 25 voids max. Voronoi cached between spec/paint.

def _compute_void_field(shape, seed):
    """Generate void holes using a hex grid - dense honeycomb perforation pattern.
    Voids cover ~50% of cells for dramatic visible coverage across entire surface."""
    h, w = shape
    rng = np.random.RandomState(seed + 5600)

    # Hex grid cell size: ~6% of smaller dimension for denser, more visible pattern
    cell_size = max(16, int(min(h, w) * 0.06))
    hex_h = cell_size
    hex_w = int(cell_size * 1.1547)  # 2/sqrt(3)

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)

    # Hex grid row/col assignment
    row = (y_grid / hex_h).astype(np.int32)
    # Offset every other row by half a cell width
    x_offset = np.where(row % 2 == 0, 0.0, hex_w * 0.5)
    col = ((x_grid + x_offset) / hex_w).astype(np.int32)

    # Center of each hex cell
    cy = (row + 0.5) * hex_h
    cx = (col + 0.5) * hex_w - x_offset

    # Distance from pixel to its cell center
    dist_to_center = np.sqrt((y_grid - cy)**2 + (x_grid - cx)**2)

    # Void radius: ~42% of cell size for clean circular holes
    void_radius = cell_size * 0.42

    # Checkerboard pattern: every other cell is void using (row+col) % 2 == 0
    # This gives ~50% void coverage - dramatic and unmistakable
    is_void_cell = ((row + col) % 2 == 0).astype(np.float32)

    # Slight randomness: hash-based jitter to break perfect regularity
    cell_hash = ((row * 7919 + col * 104729 + seed) % 100).astype(np.float32) / 100.0
    # Keep 85% of void cells (vs old 35%) - much denser coverage
    is_void_cell = np.where(cell_hash < 0.85, is_void_cell, 0.0)

    # Circular void mask within void cells
    is_void = is_void_cell * np.clip(1.0 - dist_to_center / void_radius, 0, 1)

    # Smooth edges
    void_img = Image.fromarray((is_void * 255).clip(0, 255).astype(np.uint8))
    void_img = void_img.filter(ImageFilter.GaussianBlur(radius=max(2, cell_size // 12)))
    is_void_soft = np.array(void_img).astype(np.float32) / 255.0

    n_voids = int(is_void_cell.sum() / max(1, h * w / (hex_h * hex_w)))
    return is_void_soft, n_voids

def spec_void(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    cache_key = ("void", shape, seed)
    is_void_soft, n_voids = _get_cached_field(cache_key, lambda: _compute_void_field(shape, seed))

    # Independent noise for M channel independence from R
    void_noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 5605)
    void_noise = (void_noise - void_noise.min()) / (void_noise.max() - void_noise.min() + 1e-8)

    M = ((1 - is_void_soft) * 220 + void_noise * 35) * sm
    R = (is_void_soft * 230 + (1 - is_void_soft) * 2 + void_noise * 25) * sm

    # Edge detection for CC variation
    edge = np.abs(np.diff(is_void_soft, axis=1, prepend=is_void_soft[:, :1])) + \
           np.abs(np.diff(is_void_soft, axis=0, prepend=is_void_soft[:1, :]))
    edge = np.clip(edge * 3, 0, 1)
    # Scale n_voids into subtle CC modulation
    void_density = min(n_voids / 50.0, 1.0)
    void_field = is_void_soft * void_density
    CC = np.clip(140 + void_field * 80 + edge * 35, 16, 255)

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = CC.astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_void(paint, shape, mask, seed, pm, bb):
    """Void - darken void patches, keep chrome areas bright. Uses cached field."""
    if pm == 0.0:
        return paint
    cache_key = ("void", shape, seed)
    is_void_soft, _ = _get_cached_field(cache_key, lambda: _compute_void_field(shape, seed))

    darken = is_void_soft * 0.85 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - darken * mask), 0, 1)

    chrome_boost = (1 - is_void_soft) * 0.05 * pm
    paint = np.clip(paint + chrome_boost[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    edge = np.abs(np.diff(is_void_soft, axis=1, prepend=is_void_soft[:, :1])) + \
           np.abs(np.diff(is_void_soft, axis=0, prepend=is_void_soft[:1, :]))
    edge = np.clip(edge * 3, 0, 1) * 0.1 * pm
    paint = np.clip(paint + edge[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.6 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #2: LIVING CHROME - Chrome that appears to undulate
# ================================================================

def spec_living_chrome(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)

    wave1 = np.sin(yf * 0.008 + xf * 0.003) * 0.5 + 0.5
    wave2 = np.sin(yf * 0.005 - xf * 0.007) * 0.5 + 0.5
    wave3 = np.sin((yf + xf) * 0.004) * 0.5 + 0.5
    undulation = wave1 * 0.4 + wave2 * 0.35 + wave3 * 0.25

    micro = _noise(shape, [4, 8], [0.4, 0.6], seed + 5701)
    micro = (micro - micro.min()) / (micro.max() - micro.min() + 1e-8)

    M = np.clip(130 + undulation * 80 + micro * 45, 130, 255) * sm
    R = ((1 - undulation) * 80 + micro * 40 + 5) * sm
    CC = 16 + undulation * 80  # span 80, min 16

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC, 16, 96).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_living_chrome(paint, shape, mask, seed, pm, bb):
    """Living Chrome - UNDULATING liquid mirror with dramatic bright/dark wave contrast."""
    if pm == 0.0:
        return paint
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    rng = np.random.RandomState(seed + 5702)

    wave1 = np.sin(yf * 0.008 + xf * 0.003) * 0.5 + 0.5
    wave2 = np.sin(yf * 0.005 - xf * 0.007) * 0.5 + 0.5
    wave3 = np.sin((yf + xf) * 0.004) * 0.5 + 0.5
    undulation = wave1 * 0.4 + wave2 * 0.35 + wave3 * 0.25

    # Base chrome brightening
    paint = np.clip(paint + 0.12 * pm * mask[:, :, np.newaxis], 0, 1)

    # Wave peaks = mirror bright, wave troughs = dark recessed chrome
    bright = undulation * 0.28 * pm
    dark = (1 - undulation) * 0.25 * pm
    paint = np.clip(paint + bright[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - dark * mask, 0, 1)

    # Chrome rainbow caustic hints on wave peaks
    hue = (undulation * 2.0) % 1.0
    r_c, g_c, b_c = _hsv_to_rgb(hue, np.full_like(hue, 0.15), np.full_like(hue, 0.5))
    tint = 0.08 * pm * undulation
    paint[:, :, 0] = np.clip(paint[:, :, 0] + r_c * tint * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + g_c * tint * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + b_c * tint * mask, 0, 1)

    # Specular hotspots
    sparkle = rng.random(shape).astype(np.float32)
    chrome_spark = np.where((sparkle > 0.975) & (undulation > 0.5), 0.22 * pm, 0.0)
    paint = np.clip(paint + chrome_spark[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.4 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #3: QUANTUM - Simultaneously every material at once
# ================================================================
# VISUAL FIX: 16px blocks instead of 4px. Noise-based zones instead
# of pure random - creates coherent material "regions" that still
# look exotic but not like pixel soup.

def spec_quantum(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    rng_block = np.random.RandomState(seed + 5800)

    block_size = 16
    bh = (h + block_size - 1) // block_size
    bw = (w + block_size - 1) // block_size

    # Coherent noise for M and R instead of pure random
    m_noise = _noise((bh, bw), [2, 4, 8], [0.3, 0.4, 0.3], seed + 5800)
    r_noise = _noise((bh, bw), [2, 4, 8], [0.3, 0.4, 0.3], seed + 5801)
    m_noise = (m_noise - m_noise.min()) / (m_noise.max() - m_noise.min() + 1e-8)
    r_noise = (r_noise - r_noise.min()) / (r_noise.max() - r_noise.min() + 1e-8)

    # Independent noise for CC channel (new seed)
    cc_noise = _noise((bh, bw), [2, 4, 8], [0.3, 0.4, 0.3], seed + 5802)
    cc_noise = (cc_noise - cc_noise.min()) / (cc_noise.max() - cc_noise.min() + 1e-8)

    # Add some randomness on top of the noise for quantum unpredictability
    block_M = np.clip(m_noise * 200 + rng_block.randint(-40, 40, (bh, bw)), 0, 255).astype(np.float32)
    block_R = np.clip(r_noise * 200 + rng_block.randint(-40, 40, (bh, bw)), 0, 255).astype(np.float32)
    block_CC = np.clip(16 + cc_noise * 90, 16, 106).astype(np.float32)

    M_img = Image.fromarray(block_M.clip(0, 255).astype(np.uint8))
    R_img = Image.fromarray(block_R.clip(0, 255).astype(np.uint8))
    CC_img = Image.fromarray(block_CC.clip(0, 255).astype(np.uint8))
    M_full = np.array(M_img.resize((w, h), Image.NEAREST)).astype(np.float32)
    R_full = np.array(R_img.resize((w, h), Image.NEAREST)).astype(np.float32)
    CC_full = np.array(CC_img.resize((w, h), Image.NEAREST)).astype(np.float32)

    M_full = M_full * sm
    R_full = R_full * sm

    spec[:, :, 0] = np.clip(M_full * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R_full * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.where(mask > 0.5, CC_full, 0).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_quantum(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 5800)
    block_size = 16
    bh = (h + block_size - 1) // block_size
    bw = (w + block_size - 1) // block_size

    m_noise = _noise((bh, bw), [2, 4, 8], [0.3, 0.4, 0.3], seed + 5800)
    m_noise = (m_noise - m_noise.min()) / (m_noise.max() - m_noise.min() + 1e-8)
    block_hue = m_noise

    hue_img = Image.fromarray((block_hue * 255).clip(0, 255).astype(np.uint8))
    hue_full = np.array(hue_img.resize((w, h), Image.NEAREST)).astype(np.float32) / 255.0

    r_shift, g_shift, b_shift = _hsv_to_rgb(hue_full, np.full_like(hue_full, 0.6), np.full_like(hue_full, 0.6))
    blend = 0.22 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + r_shift * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + g_shift * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + b_shift * blend * mask, 0, 1)

    rng2 = np.random.RandomState(seed + 5801)
    sparkle = rng2.random((h, w)).astype(np.float32)
    spark = np.where(sparkle > 0.975, 0.20 * pm, 0.0)
    paint = np.clip(paint + spark[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #4: AURORA - Northern lights shimmer
# ================================================================
# PBR Exploit: Horizontal bands of varying M and R create aurora-like
# curtains. Low roughness bands catch environment lighting at different
# angles, producing traveling shimmer as camera moves.

def spec_aurora(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)

    # Horizontal curtain waves with slight x-wobble
    wobble = np.sin(xf * 0.01) * 30
    curtain1 = np.sin((yf + wobble) * 0.015) * 0.5 + 0.5
    curtain2 = np.sin((yf + wobble * 0.7) * 0.025) * 0.5 + 0.5
    curtain3 = np.sin((yf + wobble * 1.3) * 0.01) * 0.5 + 0.5
    aurora = (curtain1 * 0.4 + curtain2 * 0.35 + curtain3 * 0.25)

    # Independent noise for R channel
    curtain_noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 5805)
    curtain_noise = (curtain_noise - curtain_noise.min()) / (curtain_noise.max() - curtain_noise.min() + 1e-8)

    M = (aurora * 180 + 40) * sm
    R = ((1 - aurora) * 100 + curtain_noise * 30 + 5) * sm
    CC = np.clip(16 + (1 - aurora) * 90, 16, 106)  # Use aurora for CC variation (span 90)

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.where(mask > 0.5, CC, 0).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_aurora(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    wobble = np.sin(xf * 0.01) * 30
    curtain1 = np.sin((yf + wobble) * 0.015) * 0.5 + 0.5
    curtain2 = np.sin((yf + wobble * 0.7) * 0.025) * 0.5 + 0.5

    # Vivid aurora curtain: green-cyan dominant, purple undertone
    paint[:, :, 0] = np.clip(paint[:, :, 0] + curtain2 * 0.12 * pm * mask, 0, 1)  # purple in second curtain
    paint[:, :, 1] = np.clip(paint[:, :, 1] + curtain1 * 0.30 * pm * mask, 0, 1)  # strong green
    paint[:, :, 2] = np.clip(paint[:, :, 2] + curtain1 * 0.18 * pm * mask, 0, 1)  # cyan

    # Dark sky between curtain bands for contrast
    dark_sky = np.clip((0.3 - curtain1) * 3, 0, 1) * 0.20 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - dark_sky * mask, 0, 1)

    # Bright curtain peaks
    peak = np.clip((curtain1 - 0.7) * 4, 0, 1) * 0.20 * pm
    paint = np.clip(paint + peak[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #5: MAGNETIC - Iron filing magnetic field lines
# ================================================================

def spec_magnetic(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    rng = np.random.RandomState(seed + 5810)
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)

    # 2-3 magnetic poles
    n_poles = rng.randint(2, 4)
    field_x = np.zeros((h, w), dtype=np.float32)
    field_y = np.zeros((h, w), dtype=np.float32)
    for _ in range(n_poles):
        py, px = rng.randint(h//4, 3*h//4), rng.randint(w//4, 3*w//4)
        polarity = rng.choice([-1, 1])
        dy = yf - py
        dx = xf - px
        dist_sq = dy**2 + dx**2 + 1e-3
        field_x += polarity * dx / dist_sq
        field_y += polarity * dy / dist_sq

    # Field magnitude = metallic intensity
    mag = np.sqrt(field_x**2 + field_y**2)
    mag = (mag - mag.min()) / (mag.max() - mag.min() + 1e-8)
    # Field line texture: use atan2 for direction, create stripes
    angle = np.arctan2(field_y, field_x)
    lines = np.sin(angle * 8 + mag * 20) * 0.5 + 0.5

    # Independent noise for R channel
    mag_r_noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 5815)
    mag_r_noise = (mag_r_noise - mag_r_noise.min()) / (mag_r_noise.max() - mag_r_noise.min() + 1e-8)

    M = (lines * 200 + 30) * sm
    R = ((1 - lines) * 80 + mag_r_noise * 40 + 10) * sm
    CC = 16 + (1 - lines) * 80  # span 80, min 16

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC, 16, 96).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_magnetic(paint, shape, mask, seed, pm, bb):
    """Magnetic - VISIBLE field line pattern with pole glow and iron filing texture."""
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 5810)
    y, x = _mgrid(shape)
    yf = y.astype(np.float32); xf = x.astype(np.float32)

    n_poles = rng.randint(2, 4)
    field_x = np.zeros((h, w), dtype=np.float32)
    field_y = np.zeros((h, w), dtype=np.float32)
    mag_acc = np.zeros((h, w), dtype=np.float32)
    for _ in range(n_poles):
        py, px = rng.randint(h//4, 3*h//4), rng.randint(w//4, 3*w//4)
        polarity = rng.choice([-1, 1])
        dy = yf - py; dx = xf - px
        dist_sq = dy**2 + dx**2 + 1e-3
        dist = np.sqrt(dist_sq)
        field_x += polarity * dx / dist_sq
        field_y += polarity * dy / dist_sq
        mag_acc += 1.0 / dist

    mag_acc = (mag_acc - mag_acc.min()) / (mag_acc.max() - mag_acc.min() + 1e-8)
    angle = np.arctan2(field_y, field_x)
    lines = np.sin(angle * 8 + mag_acc * 20) * 0.5 + 0.5

    # Field line visibility - strong contrast between line and gap
    line_bright = lines * 0.22 * pm
    line_dark = (1 - lines) * 0.18 * pm
    paint = np.clip(paint + line_bright[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - line_dark * mask, 0, 1)

    # Pole proximity glow - bright white-blue near poles
    pole_glow = np.clip((mag_acc - 0.5) * 3, 0, 1) * 0.30 * pm
    paint[:, :, 1] = np.clip(paint[:, :, 1] + pole_glow * 0.5 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + pole_glow * mask, 0, 1)
    paint = np.clip(paint + pole_glow[:, :, np.newaxis] * 0.3 * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #6: EMBER - Glowing hot metal cooling
# ================================================================

def spec_ember(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    heat = _noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 5820)
    heat = (heat - heat.min()) / (heat.max() - heat.min() + 1e-8)

    # Independent noise for R channel
    ember_r_noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 5825)
    ember_r_noise = (ember_r_noise - ember_r_noise.min()) / (ember_r_noise.max() - ember_r_noise.min() + 1e-8)

    # Hot zones: low M (dielectric glow), low R (smooth emission look)
    # Cool zones: high M (dark metal), high R (rough cooled surface)
    M = ((1 - heat) * 220 + 10) * sm
    R = ((1 - heat) * 150 + ember_r_noise * 40 + 5) * sm

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(16 + heat * 80, 16, 96).astype(np.uint8)  # Cool=CC=16 max clearcoat, hot=CC=96 duller from heat damage
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_ember(paint, shape, mask, seed, pm, bb):
    """Ember - GLOWING hot metal with blazing orange cracks and dark cooled surface."""
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 5821)
    heat = _noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 5820)
    heat = (heat - heat.min()) / (heat.max() - heat.min() + 1e-8)

    # Cool zones darken heavily - cooled metal is near-black
    cool = np.clip((0.5 - heat) * 2.5, 0, 1)
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - cool * 0.50 * pm * mask), 0, 1)

    # Hot = blazing orange-red glow
    glow_r = heat * 0.35 * pm
    glow_g = heat * heat * 0.18 * pm  # squared = yellow only at hottest
    paint[:, :, 0] = np.clip(paint[:, :, 0] + glow_r * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + glow_g * mask, 0, 1)

    # White-hot cores
    white_core = np.clip((heat - 0.8) * 5, 0, 1) * 0.30 * pm
    paint = np.clip(paint + white_core[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Ember sparkle in hot zones
    sparkle = rng.random(shape).astype(np.float32)
    embers = np.where((sparkle > 0.975) & (heat > 0.3), 0.20 * pm, 0.0)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + embers * mask, 0, 1)

    paint = np.clip(paint + bb * 0.4 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #7: STEALTH - Radar-absorbing angular facets
# ================================================================

def spec_stealth(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    rng = np.random.RandomState(seed + 5830)

    # Angular faceted surface - large Voronoi cells with flat properties
    n_facets = min(30, max(10, (h * w) // (250 * 250)))
    _, cell_id, _ = _voronoi(shape, n_facets, seed + 5830)

    # Each facet gets varied material properties across wide ranges
    facet_R = rng.randint(80, 220, n_facets).astype(np.float32)
    facet_M = rng.randint(20, 160, n_facets).astype(np.float32)
    facet_CC = rng.randint(16, 96, n_facets).astype(np.float32)

    M = facet_M[cell_id] * sm
    R = facet_R[cell_id] * sm
    CC = facet_CC[cell_id]

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = CC.astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_stealth(paint, shape, mask, seed, pm, bb):
    """Stealth - ANGULAR faceted dark surface with visible facet edges and subtle green-gray tint."""
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 5831)

    # Very dark base
    darken = 0.72 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - darken * mask), 0, 1)

    # Faceted surface - Voronoi-based angular plates
    n_facets = min(30, max(10, (h * w) // (250 * 250)))
    min_dist, cell_id, _ = _voronoi(shape, n_facets, seed + 5830)
    max_d = min_dist.max() + 1e-8

    # Each facet gets slightly different darkness for angular contrast
    facet_bright = rng.uniform(0.0, 0.08, n_facets + 1).astype(np.float32)
    facet_val = facet_bright[np.clip(cell_id, 0, n_facets)]
    paint = np.clip(paint + facet_val[:, :, np.newaxis] * pm * mask[:, :, np.newaxis], 0, 1)

    # Facet edge highlights - visible seam lines
    edge = np.clip(1.0 - min_dist / (max_d * 0.04), 0, 1) * 0.12 * pm
    paint = np.clip(paint + edge[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Slight military green-gray tint
    paint[:, :, 1] = np.clip(paint[:, :, 1] + 0.02 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #8: GLASS ARMOR - Transparent armor plating illusion
# ================================================================

def spec_glass_armor(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    rng = np.random.RandomState(seed + 5840)

    # Rectangular plate grid
    plate_h = max(40, h // 12)
    plate_w = max(60, w // 10)
    y, x = _mgrid(shape)
    plate_y = (y % plate_h).astype(np.float32)
    plate_x = (x % plate_w).astype(np.float32)

    # Plate interior: glass-like (M=0, R=5, CC=16)
    # Plate edges: metallic frame (M=200, R=30)
    edge_y = np.minimum(plate_y, plate_h - plate_y) < 3
    edge_x = np.minimum(plate_x, plate_w - plate_x) < 3
    is_edge = (edge_y | edge_x).astype(np.float32)

    # Independent crack noise for R channel
    crack_noise = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 5845)
    crack_noise = (crack_noise - crack_noise.min()) / (crack_noise.max() - crack_noise.min() + 1e-8)

    M = (is_edge * 200 + (1 - is_edge) * 5) * sm
    R = (is_edge * 30 + (1 - is_edge) * 5 + crack_noise * 100) * sm
    CC = np.clip(16 + is_edge * 40 + (1 - is_edge) * 60, 16, 96)

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_glass_armor(paint, shape, mask, seed, pm, bb):
    """Glass Armor - VISIBLE plate grid with strong blue glass panels and dark metallic frame."""
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 5841)
    plate_h = max(40, h // 12)
    plate_w = max(60, w // 10)
    y, x = _mgrid(shape)
    plate_y = (y % plate_h).astype(np.float32)
    plate_x = (x % plate_w).astype(np.float32)
    edge_y = np.minimum(plate_y, plate_h - plate_y) < 4
    edge_x = np.minimum(plate_x, plate_w - plate_x) < 4
    is_edge = (edge_y | edge_x).astype(np.float32)
    glass = (1 - is_edge)

    # Strong blue-teal tint for glass panels
    paint[:, :, 0] = np.clip(paint[:, :, 0] + glass * 0.04 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + glass * 0.12 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + glass * 0.22 * pm * mask, 0, 1)

    # Glass panels get slight brightening for translucency feel
    paint = np.clip(paint + glass[:, :, np.newaxis] * 0.08 * pm * mask[:, :, np.newaxis], 0, 1)

    # Dark metallic frame edges - clearly visible grid
    paint = np.clip(paint - is_edge[:, :, np.newaxis] * 0.25 * pm * mask[:, :, np.newaxis], 0, 1)

    # Bright edge highlight on inner frame edge for 3D depth
    inner_edge_y = (np.minimum(plate_y, plate_h - plate_y) >= 4) & (np.minimum(plate_y, plate_h - plate_y) < 7)
    inner_edge_x = (np.minimum(plate_x, plate_w - plate_x) >= 4) & (np.minimum(plate_x, plate_w - plate_x) < 7)
    inner_edge = (inner_edge_y | inner_edge_x).astype(np.float32) * 0.10 * pm
    paint = np.clip(paint + inner_edge[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Glass sparkle reflections
    sparkle = rng.random(shape).astype(np.float32)
    glass_spark = np.where((sparkle > 0.98) & (glass > 0.5), 0.18 * pm, 0.0)
    paint = np.clip(paint + glass_spark[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #9: STATIC - TV static / signal noise
# ================================================================

def spec_static(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    rng = np.random.RandomState(seed + 5850)

    # Horizontal scan lines + noise
    scan_period = max(2, h // 256)
    y, _ = _mgrid(shape)
    scan_line = ((y // scan_period) % 2).astype(np.float32) * 0.3

    # Per-pixel noise (but generated at half-res and upscaled for speed)
    half_h, half_w = max(1, h // 2), max(1, w // 2)
    noise_small = rng.randint(0, 256, (half_h, half_w)).astype(np.uint8)
    noise_img = Image.fromarray(noise_small).resize((w, h), Image.NEAREST)
    noise_full = np.array(noise_img).astype(np.float32) / 255.0

    # Independent noise for CC channel
    cc_noise = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 5855)
    cc_noise = (cc_noise - cc_noise.min()) / (cc_noise.max() - cc_noise.min() + 1e-8)

    M = (noise_full * 255 * (1 - scan_line * 0.5)) * sm
    R = ((1 - noise_full) * 200 + scan_line * 55) * sm

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    CC = np.clip(16 + (spec[:, :, 0].astype(np.float32) / 255.0) * 80 + scan_line * 20, 16, 116)
    spec[:, :, 2] = CC.astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_static(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 5850)
    half_h, half_w = max(1, h // 2), max(1, w // 2)
    noise_small = rng.randint(0, 256, (half_h, half_w)).astype(np.uint8)
    noise_img = Image.fromarray(noise_small).resize((w, h), Image.NEAREST)
    noise_full = np.array(noise_img).astype(np.float32) / 255.0

    # Heavy desaturate toward gray static
    gray = paint.mean(axis=2, keepdims=True)
    desat = 0.55 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(
            paint[:, :, c] * (1 - desat * mask) + gray[:, :, 0] * desat * mask, 0, 1)

    # Strong noise brightness variation
    noise_bright = (noise_full - 0.5) * 0.25 * pm
    paint = np.clip(paint + noise_bright[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Scan line darkening
    scan_period = max(2, h // 256)
    y, _ = _mgrid(shape)
    scan_line = ((y // scan_period) % 2).astype(np.float32)
    scan_dark = scan_line * 0.12 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - scan_dark * mask, 0, 1)

    # Bright burst hotspots
    bursts = rng.random((h, w)).astype(np.float32)
    burst_pop = np.where(bursts > 0.99, 0.25 * pm, 0.0)
    paint = np.clip(paint + burst_pop[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #10: MERCURY POOL - Liquid mercury pooling effect
# ================================================================

def spec_mercury_pool(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)

    # Smooth flowing noise for mercury pools
    flow = _noise(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed + 5860)
    flow = (flow - flow.min()) / (flow.max() - flow.min() + 1e-8)

    # Mercury: full metallic everywhere, roughness varies with pools
    # Pool centers = mirror smooth, between pools = slightly rough
    pool = np.clip((flow - 0.3) * 3, 0, 1)  # threshold into pool shapes
    pool_img = Image.fromarray((pool * 255).astype(np.uint8))
    pool_img = pool_img.filter(ImageFilter.GaussianBlur(radius=4))
    pool_smooth = np.array(pool_img).astype(np.float32) / 255.0

    M = np.clip(120 + pool_smooth * 130, 120, 250) * sm
    R = ((1 - pool_smooth) * 120 + pool_smooth * 3) * sm  # Pools = mirror, gaps = rougher

    CC = 16 + pool_smooth * 80  # span 80, min 16

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC, 16, 96).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_mercury_pool(paint, shape, mask, seed, pm, bb):
    """Mercury Pool - DRAMATIC liquid metal pools with mirror-bright centers and dark gaps."""
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 5861)
    flow = _noise(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed + 5860)
    flow = (flow - flow.min()) / (flow.max() - flow.min() + 1e-8)
    pool = np.clip((flow - 0.3) * 3, 0, 1)
    pool_img = Image.fromarray((pool * 255).astype(np.uint8))
    pool_img = pool_img.filter(ImageFilter.GaussianBlur(radius=4))
    pool_smooth = np.array(pool_img).astype(np.float32) / 255.0

    # Pool centers = mirror-bright silver
    bright = pool_smooth * 0.30 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + bright * 0.85 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + bright * 0.90 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + bright * 1.0 * mask, 0, 1)

    # Gaps between pools = dark recessed channels
    gap = np.clip((0.3 - flow) * 4, 0, 1) * 0.30 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - gap * mask, 0, 1)

    # Pool edge highlight where mercury meets gap
    gx = np.abs(np.diff(pool_smooth, axis=1, prepend=pool_smooth[:, :1]))
    gy = np.abs(np.diff(pool_smooth, axis=0, prepend=pool_smooth[:1, :]))
    edge = np.clip((gx + gy) * 15, 0, 1) * 0.18 * pm
    paint = np.clip(paint + edge[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Mercury sparkle
    sparkle = rng.random(shape).astype(np.float32)
    merc_spark = np.where((sparkle > 0.975) & (pool_smooth > 0.4), 0.22 * pm, 0.0)
    paint = np.clip(paint + merc_spark[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# BASE #4: PRISMATIC - Rainbow-shifting metallic
# ================================================================

def paint_prismatic(paint, shape, mask, seed, pm, bb):
    """Prismatic - VIVID rainbow spectral shift with noise-warped iridescence."""
    if pm == 0.0:
        return paint
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32) / max(h, 1)
    xf = x.astype(np.float32) / max(w, 1)
    rng = np.random.RandomState(seed + 5170)

    # Noise-warped diagonal rainbow - not just a flat gradient
    warp = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 5171)
    warp = (warp - warp.min()) / (warp.max() - warp.min() + 1e-8) * 0.4
    hue = (yf * 0.6 + xf * 0.4 + warp) % 1.0
    r_c, g_c, b_c = _hsv_to_rgb(hue, np.full_like(hue, 0.85), np.full_like(hue, 0.80))

    # Strong rainbow blend
    blend = 0.30 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + r_c * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + g_c * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + b_c * blend * mask, 0, 1)

    # Iridescent sparkle at color transitions
    sparkle = rng.random(shape).astype(np.float32)
    prism_spark = np.where(sparkle > 0.975, 0.18 * pm, 0.0)
    paint = np.clip(paint + prism_spark[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.6 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# BASE #5: MERCURY - Liquid metal pooling surface
# ================================================================

def paint_mercury(paint, shape, mask, seed, pm, bb):
    """Mercury - LIQUID METAL pooling with dramatic bright/dark flow contrast."""
    if pm == 0.0:
        return paint
    h, w = shape
    flow = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 5210)
    flow = (flow - flow.min()) / (flow.max() - flow.min() + 1e-8)

    # Pool peaks = mirror-bright silver
    pools = np.clip((flow - 0.4) * 3, 0, 1)
    bright = pools * 0.30 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + bright * 0.85 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + bright * 0.90 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + bright * 1.0 * mask, 0, 1)

    # Between pools = darker recessed channels
    channels = np.clip((0.3 - flow) * 4, 0, 1) * 0.25 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - channels * mask, 0, 1)

    # Flow boundaries - bright edge highlights where mercury pools meet
    gx = np.abs(np.diff(flow, axis=1, prepend=flow[:, :1]))
    gy = np.abs(np.diff(flow, axis=0, prepend=flow[:1, :]))
    edge = np.clip((gx + gy) * 15, 0, 1) * 0.15 * pm
    paint = np.clip(paint + edge[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# BASE #6: PHANTOM - Barely-there translucent mist
# ================================================================

def paint_phantom(paint, shape, mask, seed, pm, bb):
    """Phantom - ETHEREAL translucent mist with ghostly wisps and spectral fade."""
    if pm == 0.0:
        return paint
    h, w = shape

    # Multi-layer mist at different scales
    mist1 = _noise(shape, [32, 64, 128], [0.2, 0.4, 0.4], seed + 5220)
    mist1 = (mist1 - mist1.min()) / (mist1.max() - mist1.min() + 1e-8)
    mist2 = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 5222)
    mist2 = (mist2 - mist2.min()) / (mist2.max() - mist2.min() + 1e-8)

    # Desaturate toward ghostly pale
    gray = paint.mean(axis=2, keepdims=True)
    desat = 0.40 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(
            paint[:, :, c] * (1 - desat * mask) + gray[:, :, 0] * desat * mask, 0, 1)

    # Fog brightening - push toward pale white-blue
    fog = mist1 * 0.25 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + fog * 0.7 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + fog * 0.8 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + fog * 1.0 * mask, 0, 1)

    # Ghostly wisps - thin bright streaks in second noise layer
    wisps = np.clip(1.0 - np.abs(mist2 - 0.5) * 5.0, 0, 1)
    wisp_bright = wisps * 0.18 * pm
    paint = np.clip(paint + wisp_bright[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Dark void pockets between mist layers for depth
    void = np.clip((0.25 - mist1) * 4, 0, 1) * 0.15 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - void * mask, 0, 1)

    paint = np.clip(paint + bb * 0.6 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# BASE #7: VOLCANIC - Lava cooling to rock
# ================================================================

def paint_volcanic(paint, shape, mask, seed, pm, bb):
    """Volcanic - MOLTEN LAVA with blazing cracks, scorched rock, and ember glow."""
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 5231)
    heat = _noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 5230)
    heat = (heat - heat.min()) / (heat.max() - heat.min() + 1e-8)

    # Cool rock zones - darken HARD to near-black
    cool = np.clip((0.45 - heat) * 3, 0, 1)
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - cool * 0.65 * pm * mask), 0, 1)

    # Hot lava veins - blazing orange-red-yellow
    lava = np.clip((heat - 0.35) * 3.0, 0, 1) * 0.50 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + lava * 0.40 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + lava * lava * 0.20 * pm * mask, 0, 1)  # yellow only at hottest

    # White-hot cores where lava peaks
    white_hot = np.clip((heat - 0.8) * 5, 0, 1) * 0.30 * pm
    paint = np.clip(paint + white_hot[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Ember sparkle in hot zones
    sparkle = rng.random(shape).astype(np.float32)
    embers = np.where((sparkle > 0.97) & (heat > 0.4), 0.20 * pm, 0.0)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + embers * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + embers * 0.3 * mask, 0, 1)

    paint = np.clip(paint + bb * 0.4 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# BASE #8: ARCTIC ICE - Frozen crystalline surface
# ================================================================

def paint_arctic_ice(paint, shape, mask, seed, pm, bb):
    """Arctic Ice - FROZEN crystalline with deep blue cracks and frost shimmer."""
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 5241)

    # Crystal crack network
    n_crystals = min(25, max(8, (h * w) // (350 * 350)))
    min_dist, cell_id, _ = _voronoi(shape, n_crystals, seed + 5240)
    max_d = min_dist.max() + 1e-8
    edge = np.clip(1.0 - min_dist / (max_d * 0.06), 0, 1)
    interior = 1 - edge

    # Base ice tint - push toward cold blue-white
    blend = 0.20 * pm
    paint[:, :, 0] = paint[:, :, 0] * (1 - mask * blend) + 0.70 * mask * blend
    paint[:, :, 1] = paint[:, :, 1] * (1 - mask * blend) + 0.82 * mask * blend
    paint[:, :, 2] = paint[:, :, 2] * (1 - mask * blend) + 0.95 * mask * blend

    # Deep blue crack lines - dramatically dark
    crack_dark = edge * 0.35 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] - crack_dark * 0.9 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] - crack_dark * 0.6 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - crack_dark * 0.2 * mask, 0, 1)

    # Interior ice body - subtle blue variation per crystal cell
    cell_hue = (cell_id % 5).astype(np.float32) / 5.0 * 0.08  # slight per-cell blue variation
    paint[:, :, 2] = np.clip(paint[:, :, 2] + interior * cell_hue * 0.15 * pm * mask, 0, 1)

    # Frost shimmer sparkle - dense crystalline dots
    sparkle = rng.random(shape).astype(np.float32)
    frost = np.where(sparkle > 0.92, sparkle * 0.30 * pm, 0)  # 8% of pixels get frost
    paint = np.clip(paint + frost[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)
    # Dense micro-frost - tiny blue-white dots for crystalline texture
    micro = rng.random(shape).astype(np.float32)
    micro_frost = np.where(micro > 0.85, micro * 0.08 * pm, 0)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + micro_frost * mask, 0, 1)  # Blue micro-dots
    paint = np.clip(paint + micro_frost[:, :, np.newaxis] * 0.3 * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.6 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# BASE #9: CARBON WEAVE - Carbon fiber with metallic threads
# ================================================================

def paint_carbon_weave(paint, shape, mask, seed, pm, bb):
    """Carbon Weave - DEEP carbon fiber with visible weave texture and metallic thread glint."""
    if pm == 0.0:
        return paint
    h, w = shape
    y, x = _mgrid(shape)
    rng = np.random.RandomState(seed + 5251)

    # Diagonal weave pattern
    weave_size = max(8, h // 128)
    diag1 = ((y + x) // weave_size % 2).astype(np.float32)
    diag2 = ((y - x) // weave_size % 2).astype(np.float32)
    weave = (diag1 + diag2) * 0.5

    # Heavy darkening - carbon fiber is DARK
    darken = 0.55 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - darken * mask), 0, 1)

    # Weave highlights - strong enough to see the pattern clearly
    highlight = weave * 0.18 * pm
    paint = np.clip(paint + highlight[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Metallic thread glint - scattered bright spots along weave peaks
    sparkle = rng.random(shape).astype(np.float32)
    thread_glint = np.where((sparkle > 0.96) & (weave > 0.4), 0.20 * pm, 0.0)
    paint = np.clip(paint + thread_glint[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Slight blue tint in weave valleys for depth
    valleys = (1 - weave) * 0.04 * pm
    paint[:, :, 2] = np.clip(paint[:, :, 2] + valleys * mask, 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# BASE #10: NEBULA - Space dust cloud material
# ================================================================

def paint_nebula(paint, shape, mask, seed, pm, bb):
    """Nebula - DEEP SPACE cosmic cloud with vivid purple-blue, hot pink, and bright stars."""
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 5262)

    # Multi-scale cloud layers
    cloud1 = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 5260)
    cloud2 = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 5261)
    cloud3 = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 5263)
    cloud1 = (cloud1 - cloud1.min()) / (cloud1.max() - cloud1.min() + 1e-8)
    cloud2 = (cloud2 - cloud2.min()) / (cloud2.max() - cloud2.min() + 1e-8)
    cloud3 = (cloud3 - cloud3.min()) / (cloud3.max() - cloud3.min() + 1e-8)

    # Darken base for space depth
    space_dark = (1 - cloud3) * 0.30 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - space_dark * mask), 0, 1)

    # Vivid nebula color palette - purple, blue, hot pink, cyan
    blend = 0.28 * pm
    r_n = cloud1 * 0.65 + cloud2 * 0.3  # purple-pink haze
    g_n = cloud2 * 0.25 + cloud3 * 0.15  # subtle cyan
    b_n = (cloud1 + cloud2) * 0.5  # dominant blue-purple
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + r_n * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + g_n * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + b_n * blend * mask, 0, 1)

    # Hot pink emission regions at cloud peaks
    emission = np.clip((cloud1 - 0.6) * 4, 0, 1) * 0.18 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + emission * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + emission * 0.5 * mask, 0, 1)

    # Bright star sparkles - more frequent, brighter
    stars = rng.random((h, w)).astype(np.float32)
    star_glow = np.where(stars > 0.99, 0.45 * pm, 0.0)
    paint = np.clip(paint + star_glow[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #11: PHASE SHIFT - Conductor/dielectric micro-stripe oscillation
# ================================================================
# PBR Exploit: Alternating 4px stripes of M=0 (dielectric) and M=255
# (conductor) force the renderer to interpolate between reflection
# models on adjacent pixels. The surface shifts between chrome and
# paint depending on viewing angle - neither state fully dominates.

def spec_phase_shift(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)

    # 4px alternating horizontal stripes - conductor vs dielectric
    stripe_width = 4
    stripe_phase = (y // stripe_width) % 2  # 0 or 1

    # Independent noise fields for R and CC
    phase_noise = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 6005)
    phase_noise = (phase_noise - phase_noise.min()) / (phase_noise.max() - phase_noise.min() + 1e-8)

    stripe_phase_f = stripe_phase.astype(np.float32)

    # Conductor stripes: M=255, variable R, CC from noise
    # Dielectric stripes: M=0, variable R, CC from noise
    M = (stripe_phase_f * 255).astype(np.float32) * sm
    R = (10 + stripe_phase_f * 50 + phase_noise * 60) * sm
    CC = np.clip(16 + stripe_phase_f * 40 + phase_noise * 30, 16, 86)

    # Add slight noise to prevent perfect banding artifacts
    rng = np.random.RandomState(seed + 6000)
    noise = rng.randint(-8, 9, (h, w)).astype(np.float32)
    M = np.clip(M + noise * stripe_phase_f, 0, 255)

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_phase_shift(paint, shape, mask, seed, pm, bb):
    """Phase Shift - DRAMATIC conductor/dielectric striping with warm-cool contrast and shimmer."""
    if pm == 0.0:
        return paint
    h, w = shape
    y, _ = _mgrid(shape)
    rng = np.random.RandomState(seed + 6051)

    stripe_width = 4
    stripe_phase = ((y // stripe_width) % 2).astype(np.float32)

    # Conductor stripes: warm gold-copper tint + bright
    warm = stripe_phase * 0.18 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + warm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + warm * 0.5 * mask, 0, 1)

    # Dielectric stripes: cool blue tint + darker
    cool = (1 - stripe_phase) * 0.15 * pm
    paint[:, :, 2] = np.clip(paint[:, :, 2] + cool * mask, 0, 1)
    cool_dark = (1 - stripe_phase) * 0.10 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - cool_dark * mask, 0, 1)

    # Phase transition shimmer at stripe boundaries
    transition = np.abs(np.diff(stripe_phase, axis=0, prepend=stripe_phase[:1, :]))
    shimmer = transition * 0.25 * pm
    paint = np.clip(paint + shimmer[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Sparkle on conductor stripes
    sparkle = rng.random(shape).astype(np.float32)
    cond_spark = np.where((sparkle > 0.98) & (stripe_phase > 0.5), 0.15 * pm, 0.0)
    paint = np.clip(paint + cond_spark[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #12: GRAVITY WELL - Radial Fresnel gradient depth trap
# ================================================================
# PBR Exploit: Concentric rings where M decreases 255→0 from center
# to edge while R increases 0→200 inverse. Each ring's Fresnel is
# different, creating a depth illusion - centers appear closer and
# reflective, edges appear recessed and matte.

def _compute_gravity_field(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed + 6100)
    n_wells = rng.randint(10, 18)
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    sz = min(h, w)

    # Layer 1: Ambient gravitational ripple - full surface coverage
    grav_noise = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 6101)
    grav_noise = (grav_noise - grav_noise.min()) / (grav_noise.max() - grav_noise.min() + 1e-8)
    well_field = grav_noise * 0.15  # subtle gravitational distortion everywhere

    # Layer 2: Gravity wells - more numerous with larger radii
    for _ in range(n_wells):
        cy = rng.randint(0, h)
        cx = rng.randint(0, w)
        radius = rng.uniform(sz * 0.10, sz * 0.25)
        dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
        well = np.clip(1.0 - dist / radius, 0, 1)
        well = well ** 1.5
        well_field = np.maximum(well_field, well)

    return well_field

def spec_gravity_well(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    cache_key = ("gravity", shape, seed)
    well = _get_cached_field(cache_key, lambda: _compute_gravity_field(shape, seed))

    # Independent turbulence noise for R channel
    turb_noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 6105)
    turb_noise = (turb_noise - turb_noise.min()) / (turb_noise.max() - turb_noise.min() + 1e-8)

    # Center = chrome (M=255, R=0), edge = matte dielectric (M=0, R=200)
    M = (well * 255) * sm
    R = ((1 - well) * 160 + turb_noise * 40) * sm
    CC = np.clip(16 + (1 - well) * 90, 16, 106)  # span 90, min 16

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_gravity_well(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    cache_key = ("gravity", shape, seed)
    well = _get_cached_field(cache_key, lambda: _compute_gravity_field(shape, seed))
    # Strong dark halos around wells
    darken = (1 - well) * 0.35 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - darken * mask), 0, 1)

    # Bright chrome centers
    brighten = well * 0.25 * pm
    paint = np.clip(paint + brighten[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Bright rim glow at well edges - the showstopper ring effect
    edge = np.abs(np.diff(well, axis=1, prepend=well[:, :1])) + \
           np.abs(np.diff(well, axis=0, prepend=well[:1, :]))
    rim = np.clip(edge * 8, 0, 1) * 0.28 * pm
    paint = np.clip(paint + rim[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Slight blue tint in dark halo regions
    halo_blue = (1 - well) * 0.06 * pm
    paint[:, :, 2] = np.clip(paint[:, :, 2] + halo_blue * mask, 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #13: THIN FILM - Physically-linked color + reflectivity
# ================================================================
# PBR Exploit: Film thickness noise maps to BOTH paint hue (HSV cycle)
# AND spec values. Thick film = high M, low R. Thin film = low M,
# high R. Color and reflectivity change together like real oil-on-water.
# Strongest paint blend in all of PARADIGM.

def _compute_film_field(shape, seed):
    h, w = shape
    # Multi-scale film thickness
    film = _noise(shape, [8, 16, 32, 64, 128], [0.1, 0.2, 0.3, 0.25, 0.15], seed + 6200)
    film = (film - film.min()) / (film.max() - film.min() + 1e-8)
    return film

def spec_thin_film(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    cache_key = ("thin_film", shape, seed)
    film = _get_cached_field(cache_key, lambda: _compute_film_field(shape, seed))

    # Independent noise for R channel
    film_r_noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 6205)
    film_r_noise = (film_r_noise - film_r_noise.min()) / (film_r_noise.max() - film_r_noise.min() + 1e-8)

    # Thick film = reflective metal, thin film = matte dielectric
    M = (film * 200 + 30) * sm  # 30-230 range
    R = ((1 - film) * 80 + film_r_noise * 35 + 5) * sm
    CC = np.clip(16 + (1 - film) * 90, 16, 106)  # span 90, min 16

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_thin_film(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    cache_key = ("thin_film", shape, seed)
    film = _get_cached_field(cache_key, lambda: _compute_film_field(shape, seed))
    # Film thickness → hue cycle (oil-on-water rainbow)
    hue = (film * 2.5) % 1.0  # 2.5 cycles through full spectrum
    sat = np.full_like(hue, 0.7)
    val = np.full_like(hue, 0.6)
    r_c, g_c, b_c = _hsv_to_rgb(hue, sat, val)
    # STRONG blend - this is the most visible paint in PARADIGM
    blend = 0.25 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + r_c * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + g_c * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + b_c * blend * mask, 0, 1)
    paint = np.clip(paint + bb * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #14: BLACKBODY - Continuous temperature emission spectrum
# ================================================================
# PBR Exploit: Smooth continuous gradient where M, R, AND paint color
# all change together following blackbody radiation physics.
# Cold=black+rough+dielectric → warm=red+moderate → hot=white+smooth+metal.
# The renderer treats each temperature as a completely different material.

def _compute_blackbody_field(shape, seed):
    h, w = shape
    # Temperature field: multi-scale noise with strong gradients
    temp = _noise(shape, [8, 16, 32, 64], [0.15, 0.3, 0.35, 0.2], seed + 6300)
    temp = (temp - temp.min()) / (temp.max() - temp.min() + 1e-8)
    # Sharpen contrast to create distinct hot/cold regions
    temp = np.clip((temp - 0.2) * 1.5, 0, 1)
    return temp

def spec_blackbody(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    cache_key = ("blackbody", shape, seed)
    temp = _get_cached_field(cache_key, lambda: _compute_blackbody_field(shape, seed))

    # Independent noise for R channel
    bb_r_noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 6305)
    bb_r_noise = (bb_r_noise - bb_r_noise.min()) / (bb_r_noise.max() - bb_r_noise.min() + 1e-8)

    # Temperature → material state (continuous, not binary like ember)
    # Cold (0): M=5, R=220 (rough dark dielectric)
    # Warm (0.5): M=100, R=80 (mid-metallic moderate rough)
    # Hot (1.0): M=250, R=5 (mirror-smooth full conductor)
    M = (temp * 245 + 5) * sm
    R = ((1 - temp) * 180 + bb_r_noise * 40 + 5) * sm

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(16 + temp * 100, 16, 116).astype(np.uint8)  # Cold=CC=16 glossy, hot=CC=116 heat-degraded clearcoat
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_blackbody(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    cache_key = ("blackbody", shape, seed)
    temp = _get_cached_field(cache_key, lambda: _compute_blackbody_field(shape, seed))
    # Actual blackbody color curve:
    # 0.0 = black, 0.3 = dark red, 0.5 = orange, 0.7 = yellow, 1.0 = white
    r_bb = np.clip(temp * 3.0, 0, 1)  # Red comes first
    g_bb = np.clip((temp - 0.3) * 2.5, 0, 1)  # Green later
    b_bb = np.clip((temp - 0.6) * 3.0, 0, 1)  # Blue last (white-hot)
    # Strong blend - this needs to be visible
    blend = 0.20 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + r_bb * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + g_bb * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + b_bb * blend * mask, 0, 1)
    # Extra darkening on cold zones
    cold = np.clip(1.0 - temp * 2, 0, 1) * 0.3 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - cold * mask), 0, 1)
    paint = np.clip(paint + bb * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #15: WORMHOLE - Connected void portal pairs
# ================================================================
# PBR Exploit: Circular void regions (M=0, R=255, CC=0 = perceptual
# nothing) with blazing chrome rims (M=255, R=0) connected by gradient
# tunnels. The void portals look like actual holes in the car.

def _compute_wormhole_field(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed + 6400)
    n_portals = rng.randint(6, 12)
    sz = min(h, w)
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)

    portal_field = np.zeros((h, w), dtype=np.float32)
    rim_field = np.zeros((h, w), dtype=np.float32)
    centers = []

    # Ambient spacetime distortion - full surface coverage
    warp = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 6401)
    warp = (warp - warp.min()) / (warp.max() - warp.min() + 1e-8)
    rim_field = warp * 0.12  # subtle spacetime warping everywhere

    for _ in range(n_portals):
        cy = rng.randint(0, h)
        cx = rng.randint(0, w)
        radius = rng.uniform(sz * 0.05, sz * 0.12)
        centers.append((cy, cx, radius))
        dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
        # Portal interior: smooth circle
        portal = np.clip(1.0 - dist / radius, 0, 1) ** 2
        portal_field = np.maximum(portal_field, portal)
        # Chrome rim: ring at portal edge - wider rim glow
        rim = np.exp(-((dist - radius)**2) / (radius * 0.5))
        rim_field = np.maximum(rim_field, rim)

    # Tunnels between portal pairs - wider connections
    tunnel_field = np.zeros((h, w), dtype=np.float32)
    if len(centers) >= 2:
        for i in range(len(centers) - 1):
            cy1, cx1, r1 = centers[i]
            cy2, cx2, r2 = centers[i + 1]
            dx = cx2 - cx1
            dy = cy2 - cy1
            length = np.sqrt(dx**2 + dy**2) + 1e-8
            t = np.clip(((xf - cx1) * dx + (yf - cy1) * dy) / (length**2), 0, 1)
            proj_x = cx1 + t * dx
            proj_y = cy1 + t * dy
            line_dist = np.sqrt((xf - proj_x)**2 + (yf - proj_y)**2)
            tunnel_width = max(r1, r2) * 0.7
            tunnel = np.clip(1.0 - line_dist / tunnel_width, 0, 1) * 0.55
            tunnel_field = np.maximum(tunnel_field, tunnel)

    return portal_field, rim_field, tunnel_field

def spec_wormhole(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    cache_key = ("wormhole", shape, seed)
    portal, rim, tunnel = _get_cached_field(cache_key, lambda: _compute_wormhole_field(shape, seed))

    # Portal interior: void (M=0, R=255, CC=0)
    # Rim: blazing chrome (M=255, R=0)
    # Tunnel: gradient metallic
    # Background: neutral metal
    M_base = 140.0
    M = M_base * (1 - portal) * (1 - rim * 0.8) + rim * 255 + tunnel * 200
    M = np.clip(M * (1 - portal) + portal * 0, 0, 255)  # Void = M=0
    R = np.clip(portal * 255 + (1 - portal) * (1 - rim) * 40 + rim * 2, 0, 255)
    CC = np.clip(100 + portal * 100 + rim * 55, 16, 255)  # span ~155, min 16

    M = M * sm
    R = R * sm

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_wormhole(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    cache_key = ("wormhole", shape, seed)
    portal, rim, tunnel = _get_cached_field(cache_key, lambda: _compute_wormhole_field(shape, seed))
    # Portals → deep void black
    darken = portal * 0.90 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - darken * mask), 0, 1)

    # Rim → BLAZING white-blue chrome edge glow
    rim_glow = rim * 0.35 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + rim_glow * 0.7 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + rim_glow * 0.85 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + rim_glow * 1.0 * mask, 0, 1)

    # Tunnel → visible blue-purple energy connection
    paint[:, :, 0] = np.clip(paint[:, :, 0] + tunnel * 0.10 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + tunnel * 0.22 * pm * mask, 0, 1)
    paint = np.clip(paint + tunnel[:, :, np.newaxis] * 0.06 * pm * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.4 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #16: CRYSTAL LATTICE - Multi-scale hex grid interference
# ================================================================
# PBR Exploit: 3 overlapping hex grids at different scales create a
# parallax illusion of 3D depth. Where grids align = M=255 nodes.
# Where they diverge = chaotic M/R mixing. Extreme depth illusion in 2D.

def spec_crystal_lattice(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)

    # Three hex grids at different scales
    layers = []
    for scale in [60, 90, 140]:
        hex_h = scale
        hex_w = int(scale * 1.1547)
        row = (yf / hex_h).astype(np.int32)
        offset = np.where(row % 2 == 0, 0.0, hex_w * 0.5)
        col = ((xf + offset) / hex_w).astype(np.int32)
        cy = (row + 0.5) * hex_h
        cx = (col + 0.5) * hex_w - offset
        dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
        # Node proximity: 1 at center, 0 at edge
        node = np.clip(1.0 - dist / (scale * 0.35), 0, 1)
        # Edge detection: where dist ≈ radius
        edge = np.clip(1.0 - np.abs(dist - scale * 0.45) / 4, 0, 1)
        layers.append((node, edge))

    # Combine layers: alignment = all nodes overlap
    node_sum = sum(n for n, e in layers) / 3.0
    edge_sum = np.clip(sum(e for n, e in layers), 0, 1)

    # Nodes: high metallic. Edges: varied. Background: low metallic
    M = np.clip(node_sum * 255 + edge_sum * 100, 0, 255) * sm
    R = np.clip((1 - node_sum) * 120 + edge_sum * 40, 0, 255) * sm
    CC = np.clip(16 + (1 - node_sum) * 90, 16, 106)  # span 90, min 16

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_crystal_lattice(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Compute node alignment for prismatic color at intersections
    node_sum = np.zeros((h, w), dtype=np.float32)
    for scale in [60, 90, 140]:
        hex_h = scale
        hex_w = int(scale * 1.1547)
        row = (yf / hex_h).astype(np.int32)
        offset = np.where(row % 2 == 0, 0.0, hex_w * 0.5)
        col = ((xf + offset) / hex_w).astype(np.int32)
        cy = (row + 0.5) * hex_h
        cx = (col + 0.5) * hex_w - offset
        dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
        node = np.clip(1.0 - dist / (scale * 0.35), 0, 1)
        node_sum += node
    node_sum /= 3.0
    # Darken background between lattice nodes
    bg_dark = np.clip(1.0 - node_sum * 2, 0, 1) * 0.20 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - bg_dark * mask, 0, 1)

    # Vivid prismatic hue shift at aligned nodes
    hue = (node_sum * 1.5) % 1.0
    r_c, g_c, b_c = _hsv_to_rgb(hue,
        np.clip(node_sum * 0.9, 0, 1),
        np.clip(node_sum * 0.8 + 0.2, 0, 1))
    blend = 0.25 * pm * node_sum
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + r_c * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + g_c * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + b_c * blend * mask, 0, 1)

    # Bright node intersection highlights
    bright_nodes = np.clip((node_sum - 0.6) * 4, 0, 1) * 0.20 * pm
    paint = np.clip(paint + bright_nodes[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #17: PULSE - Radial energy wavefront with metallic rings
# ================================================================
# PBR Exploit: Concentric sine rings from multiple epicenters.
# Ring crests: M=255, R=0 (mirror chrome catches all light).
# Ring troughs: M=0, R=180 (matte dielectric absorbs).
# Creates a "radar ping" effect - each ring catches light at
# different angles as the camera moves around the car.

def _compute_pulse_field(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed + 6500)
    n_epicenters = rng.randint(3, 6)
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)

    pulse_field = np.zeros((h, w), dtype=np.float32)
    for _ in range(n_epicenters):
        cy = rng.randint(0, h)
        cx = rng.randint(0, w)
        dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
        # Ring spacing tuned for 3-5 visible rings per car panel
        ring_freq = rng.uniform(0.04, 0.08)
        rings = np.sin(dist * ring_freq * 2 * np.pi) * 0.5 + 0.5
        # Fade with distance
        fade = np.clip(1.0 - dist / (max(h, w) * 0.6), 0, 1)
        pulse_field += rings * fade

    pulse_field = (pulse_field - pulse_field.min()) / (pulse_field.max() - pulse_field.min() + 1e-8)
    return pulse_field

def spec_pulse(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    cache_key = ("pulse", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_pulse_field(shape, seed))

    # Independent turbulence noise for R channel
    pulse_turb = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 6505)
    pulse_turb = (pulse_turb - pulse_turb.min()) / (pulse_turb.max() - pulse_turb.min() + 1e-8)

    # Ring crests (field≈1): M=255, R=0 (chrome mirror)
    # Ring troughs (field≈0): M=0, R=180 (matte dielectric)
    M = (field * 255) * sm
    R = ((1 - field) * 140 + pulse_turb * 40) * sm
    CC = np.clip(16 + (1 - field) * 90, 16, 106)  # span 90, min 16

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC, 16, 106).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_pulse(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    cache_key = ("pulse", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_pulse_field(shape, seed))
    # Bright white at ring crests
    crest_glow = field * 0.25 * pm
    paint = np.clip(paint + crest_glow[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Dark troughs with blue energy glow
    trough_dark = (1 - field) * 0.20 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - trough_dark * mask, 0, 1)
    trough_blue = (1 - field) * 0.15 * pm
    paint[:, :, 2] = np.clip(paint[:, :, 2] + trough_blue * mask, 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# REGISTRY ENTRIES - 10 Bases, 10 Patterns, 17 Monolithics
# ================================================================



# ================================================================
# NEW MIND-BENDING PARADIGM BASES (2026 OVERHAUL)
# ================================================================

def paint_superfluid(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 9001)
    
    # Frictionless creeping condensation effect - Bose-Einstein behavior
    vortex1 = _noise(shape, [16, 32], [0.6, 0.4], seed + 9002)
    vortex2 = _noise(shape, [8, 16], [0.5, 0.5], seed + 9003)
    fluid = np.clip((vortex1 * vortex2) * 5.0, 0, 1)
    
    # Frost-white spectral shift, heavily influenced by clearcoat transmission
    paint[:, :, 0] = np.clip(paint[:, :, 0] * 0.9 + fluid * 0.05 * mask * pm, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * 0.95 + fluid * 0.15 * mask * pm, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * 0.98 + fluid * 0.40 * mask * pm, 0, 1)
    
    paint = np.clip(paint + bb * 0.9 * mask[:, :, np.newaxis], 0, 1)
    return paint

def paint_coronal(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 9010)
    
    # Coronal Mass Ejection - Blinding looping fusion flares
    flare1 = _noise(shape, [32, 64], [0.3, 0.7], seed + 9011)
    flare2 = _noise(shape, [16, 32], [0.5, 0.5], seed + 9012)
    
    # High contrast looping
    fusion = np.clip((flare1 - flare2) * 10.0, 0, 1)
    core = np.clip((fusion - 0.5) * 4.0, 0, 1)
    
    # Base sun orange-yellow
    paint[:, :, 0] = np.clip(paint[:, :, 0] + fusion * 0.8 * mask * pm, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + fusion * 0.4 * mask * pm, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + core * 0.9 * mask * pm, 0, 1) # Hot white core

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

def paint_seismic(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape

    # Tectonic faultlines opening to reveal magma
    faults = _noise(shape, [16, 32, 64], [0.1, 0.3, 0.6], seed + 9020)
    cracks = np.clip(1.0 - np.abs(faults - 0.5) * 15.0, 0, 1)
    
    # Darken everything heavily (graphite plate)
    dark_mask = (1.0 - cracks) * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1.0 - dark_mask * mask), 0, 1)
        
    # Magma bleeding through the cracks
    paint[:, :, 0] = np.clip(paint[:, :, 0] + cracks * 0.9 * mask * pm, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + cracks * 0.2 * mask * pm, 0, 1)

    paint = np.clip(paint + bb * 0.4 * mask[:, :, np.newaxis], 0, 1)
    return paint

def paint_hypercane(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    # Volumetric trapped storm
    storm = _noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.4, 0.1], seed + 9030)
    blend = mask * pm  # gate ALL effects by pm

    # Lightning strikes inside the paint
    lightning = np.clip(1.0 - np.abs(storm - 0.7) * 40.0, 0, 1) * np.clip(storm * 10 - 5, 0, 1)

    # Deep stormy blue/black base (replacement blend, not destructive)
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * 0.7), 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * 0.6) + storm * 0.1 * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * 0.4) + storm * 0.3 * blend, 0, 1)

    # Add lightning
    paint[:, :, 0] = np.clip(paint[:, :, 0] + lightning * 0.6 * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + lightning * 0.8 * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + lightning * 1.0 * blend, 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

def paint_geomagnetic(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32) / max(h, 1)

    # Aurora borealis trapped entirely within a metallic matrix
    waves = np.sin(yf * 15.0 + _noise(shape, [32, 64], [0.5, 0.5], seed+9040)*5.0)
    aurora = np.clip((waves - 0.5) * 5.0, 0, 1)
    
    paint[:, :, 0] = np.clip(paint[:, :, 0] + aurora * 0.1 * mask * pm, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + aurora * 0.8 * mask * pm, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + aurora * 0.5 * mask * pm, 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

def paint_hypercube(paint, shape, mask, seed, pm, bb):
    """Non-Euclidean hypercube -- recursive fractal depth illusion with overlapping
    geometric planes at exotic angles and warped/folded space feel."""
    if pm == 0.0:
        return paint
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32) / max(h, 1)
    xf = x.astype(np.float32) / max(w, 1)

    # --- Domain distortion: warp UV coordinates through noise for folded-space feel ---
    warp1 = _noise(shape, [6, 12, 24], [0.3, 0.4, 0.3], seed + 9050)
    warp2 = _noise(shape, [6, 12, 24], [0.3, 0.4, 0.3], seed + 9051)
    yw = yf + warp1 * 0.35  # warped y
    xw = xf + warp2 * 0.35  # warped x

    # --- Layer 1: Recursive grid at multiple exotic scales (fractal depth) ---
    grid_acc = np.zeros((h, w), dtype=np.float32)
    for depth in range(5):
        freq = 3.0 * (2.0 ** depth)
        angle_offset = depth * 0.618 * np.pi  # golden-ratio rotation per depth
        cos_a = np.cos(angle_offset)
        sin_a = np.sin(angle_offset)
        ru = yw * cos_a - xw * sin_a
        rv = yw * sin_a + xw * cos_a
        # Intersecting line grids that create exotic cube edges
        lines_u = np.abs(np.sin(ru * freq * np.pi))
        lines_v = np.abs(np.sin(rv * freq * np.pi))
        # Combine as wireframe: sharp lines where either grid is near zero
        wireframe = np.clip(1.0 - np.minimum(lines_u, lines_v), 0, 1)
        # Weight deeper layers less (receding into depth)
        weight = 0.6 ** depth
        grid_acc += wireframe * weight

    # Normalize accumulated grid
    grid_max = grid_acc.max()
    if grid_max > 0:
        grid_acc = grid_acc / grid_max

    # --- Layer 2: Overlapping geometric planes at conflicting angles ---
    plane1 = np.sin(yw * 8.0 * np.pi + xw * 3.0 * np.pi) * 0.5 + 0.5
    plane2 = np.sin(yw * 3.0 * np.pi - xw * 7.0 * np.pi + warp1 * 4.0) * 0.5 + 0.5
    plane3 = np.sin((yw + xw) * 5.0 * np.pi + warp2 * 3.0) * 0.5 + 0.5
    # Each plane gets a different "depth" color channel emphasis
    planes_r = np.clip(plane1 * 0.6 + plane2 * 0.2, 0, 1)
    planes_g = np.clip(plane2 * 0.5 + plane3 * 0.3, 0, 1)
    planes_b = np.clip(plane3 * 0.6 + plane1 * 0.3, 0, 1)

    # --- Layer 3: Paradoxical shadow - depth cue from Escher-like shadow gradient ---
    depth_gradient = _noise(shape, [32, 64], [0.6, 0.4], seed + 9052)
    depth_shadow = np.clip(depth_gradient * 0.5 + 0.5, 0, 1)

    # --- Combine: wireframe structure + colored planes + depth shadow ---
    struct_r = grid_acc * 0.15 + planes_r * 0.25 + depth_shadow * 0.08
    struct_g = grid_acc * 0.45 + planes_g * 0.20 + depth_shadow * 0.12
    struct_b = grid_acc * 0.55 + planes_b * 0.30 + depth_shadow * 0.15

    # Darken base for depth, then overlay the structure
    strength = pm * mask
    dark_factor = 1.0 - strength * 0.6
    paint[:, :, 0] = np.clip(paint[:, :, 0] * dark_factor + struct_r * strength, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * dark_factor + struct_g * strength, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * dark_factor + struct_b * strength, 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

def paint_time_reversed(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    # Chaos dynamically resolving into geometric order (hexagons + static)
    rng = np.random.RandomState(seed + 9060)
    noise_chaos = rng.random(shape).astype(np.float32)

    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    hex_h = 30
    hex_w = hex_h * 0.866
    row = (yf / hex_h).astype(np.int32)
    col = (xf / hex_w).astype(np.int32)
    grid = (row % 2 + col % 3) / 4.0

    # Blend chaos into strict geometry based on bb strength
    bb_avg = bb.mean() if hasattr(bb, 'mean') else float(bb)
    structure = grid * bb_avg + noise_chaos * (1.0 - bb_avg)
    blend = mask * pm  # gate ALL effects by pm

    # Replacement blend toward structure pattern
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * 0.8) + structure * 0.8 * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * 0.6) + structure * 0.4 * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * 0.8) + structure * 0.9 * blend, 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

def paint_utility_fog(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    # Programmable nanobot swarm: void zones darken, mirror zones brighten
    swarm = _noise(shape, [2, 4], [0.5, 0.5], seed + 9070)

    void_state = np.where(swarm < 0.5, 1.0, 0.0)
    mirror_state = np.where(swarm >= 0.5, 1.0, 0.0)
    blend = mask * pm  # ALL effects gated by pm (slider)

    for c in range(3):
        # Void darkens paint (replacement blend toward black)
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - void_state * 0.7 * blend), 0, 1)
        # Mirror brightens paint
        paint[:, :, c] = np.clip(paint[:, :, c] + mirror_state * 0.4 * blend, 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

def paint_negative_mirror(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    # Warped reflection with ripple distortion
    y, x = _mgrid(shape)
    yf = y.astype(np.float32) / max(h, 1)
    xf = x.astype(np.float32) / max(w, 1)

    # A ripple in the reflection
    distortion = np.sin(yf * 30.0 + xf * 30.0) * 0.5 + 0.5
    blend = mask * pm  # gate everything by pm

    # Replacement blend: warp paint toward distorted reflection
    for c in range(3):
        target = paint[:, :, c] * distortion
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - blend * 0.7) + target * blend * 0.7, 0, 1)

    # Warm shift at strength
    paint[:, :, 0] = np.clip(paint[:, :, 0] + 0.08 * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - 0.06 * blend, 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint

def paint_schrodinger(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    h, w = shape
    # High frequency quantum flicker — two-state color overlay
    flicker = np.random.RandomState(seed + 9080).random(shape).astype(np.float32)
    state_a = np.where(flicker > 0.5, 1.0, 0.0)
    blend = mask * pm  # gate everything by pm

    # State A: cyan tint, State B: magenta tint (replacement blend, not destructive)
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * 0.6) + (1 - state_a) * 0.7 * blend * 0.6, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * 0.6) + state_a * 0.8 * blend * 0.6, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * 0.5) + 0.7 * blend * 0.5, 0, 1)

    paint = np.clip(paint + bb * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


# Spec maps for the 10 PARADIGM bases (structure-driven; CC 16-255). See engine/SPEC_MAP_REFERENCE.md.
def _get_paradigm_base_specs():
    from engine.paint_v2.paradigm_scifi import (
        spec_p_superfluid, spec_p_coronal, spec_p_seismic, spec_p_hypercane, spec_p_geomagnetic,
        spec_p_non_euclidean, spec_p_time_reversed, spec_p_programmable, spec_p_erised, spec_p_schrodinger,
    )
    return {
        "p_superfluid": spec_p_superfluid, "p_coronal": spec_p_coronal, "p_seismic": spec_p_seismic,
        "p_hypercane": spec_p_hypercane, "p_geomagnetic": spec_p_geomagnetic,
        "p_non_euclidean": spec_p_non_euclidean, "p_time_reversed": spec_p_time_reversed,
        "p_programmable": spec_p_programmable, "p_erised": spec_p_erised, "p_schrodinger": spec_p_schrodinger,
    }

_PARADIGM_SPEC_FNS = _get_paradigm_base_specs()

PARADIGM_BASES = {
    # PARADIGM - Elemental Forces (CC 16 = max clearcoat; R 0-255 only)
    "p_superfluid": {
        "M": 0, "R": 0, "CC": 16,
        "paint_fn": paint_superfluid,
        "base_spec_fn": _PARADIGM_SPEC_FNS["p_superfluid"],
        "desc": "Frictionless liquid helium behavior; flowing, crawling bose-einstein condensate",
    },
    "p_coronal": {
        "M": 220, "R": 50, "CC": 16,
        "paint_fn": paint_coronal,
        "base_spec_fn": _PARADIGM_SPEC_FNS["p_coronal"],
        "desc": "The blazing surface of a star. Violent fusion loops shifting across the chassis",
    },
    "p_seismic": {
        "M": 10, "R": 200, "CC": 120,
        "paint_fn": paint_seismic,
        "base_spec_fn": _PARADIGM_SPEC_FNS["p_seismic"],
        "desc": "Tectonic graphite base ripping open to reveal churning molten kinetic energy",
    },
    "p_hypercane": {
        "M": 50, "R": 80, "CC": 80,
        "paint_fn": paint_hypercane,
        "base_spec_fn": _PARADIGM_SPEC_FNS["p_hypercane"],
        "desc": "Volumetric, chaotic atmosphere trapped in paint. Dark stormy blues with lightning",
    },
    "p_geomagnetic": {
        "M": 250, "R": 20, "CC": 16,
        "paint_fn": paint_geomagnetic,
        "base_spec_fn": _PARADIGM_SPEC_FNS["p_geomagnetic"],
        "desc": "Polarized magnetic fields warping light into an aurora borealis across a metallic matrix",
    },

    # PARADIGM - Exotic Materials (no negative R; CC 16-255)
    "p_non_euclidean": {
        "M": 150, "R": 5, "CC": 16,
        "paint_fn": paint_hypercube,
        "base_spec_fn": _PARADIGM_SPEC_FNS["p_non_euclidean"],
        "desc": "Infinite recursive structural depth that actively defies exterior dimensions",
    },
    "p_time_reversed": {
        "M": 200, "R": 15, "CC": 16,
        "paint_fn": paint_time_reversed,
        "base_spec_fn": _PARADIGM_SPEC_FNS["p_time_reversed"],
        "desc": "Time-Reversed Entropy: Chaos dynamically resolving into perfect geometric order at glancing angles",
    },
    "p_programmable": {
        "M": 128, "R": 128, "CC": 16,
        "paint_fn": paint_utility_fog,
        "base_spec_fn": _PARADIGM_SPEC_FNS["p_programmable"],
        "desc": "Programmable Utility Fog: A shifting swarm of nanobots transitioning between matte void and absolute mirror",
    },
    "p_erised": {
        "M": 255, "R": 0, "CC": 16,
        "paint_fn": paint_negative_mirror,
        "base_spec_fn": _PARADIGM_SPEC_FNS["p_erised"],
        "desc": "Negative Normal Mirror: Physically exotic negative roughness bounds bending reflections past realistic distortion",
    },
    "p_schrodinger": {
        "M": 255, "R": 40, "CC": 50,
        "paint_fn": paint_schrodinger,
        "base_spec_fn": _PARADIGM_SPEC_FNS["p_schrodinger"],
        "desc": "Schrodinger's Dust: Quantum probability paint. Flickers and changes states rapidly based on the viewing angle",
    }
}


PARADIGM_PATTERNS = {
    "fresnel_ghost": {
        "texture_fn": texture_fresnel_ghost,
        "paint_fn": paint_fresnel_ghost,
        "variable_cc": False,
        "desc": "Hidden hex pattern - invisible head-on, appears at grazing angles via Fresnel",
    },
    "caustic": {
        "texture_fn": texture_caustic,
        "paint_fn": paint_caustic,
        "variable_cc": False,
        "desc": "Underwater dancing light - golden-ratio sine wave interference caustics",
    },
    "dimensional": {
        "texture_fn": texture_dimensional,
        "paint_fn": paint_dimensional,
        "variable_cc": False,
        "desc": "Newton's rings thin-film interference - rainbow concentric ring portals",
    },
    "neural": {
        "texture_fn": texture_neural,
        "paint_fn": paint_neural,
        "variable_cc": False,
        "desc": "Living neural network - Voronoi cells with glowing axon connections",
    },
    "p_plasma": {
        "texture_fn": texture_plasma,
        "paint_fn": paint_plasma,
        "variable_cc": False,
        "desc": "Plasma ball discharge - electric tendrils from overlapping sine fields",
    },
    "holographic": {
        "texture_fn": texture_holographic,
        "paint_fn": paint_holographic,
        "variable_cc": False,
        "desc": "Hologram diffraction grating - multi-angle rainbow interference lines",
    },
    "circuitboard": {
        "texture_fn": texture_circuitboard,
        "paint_fn": paint_circuitboard,
        "variable_cc": False,
        "desc": "PCB trace pattern - metallic circuit traces on dielectric substrate",
    },
    "soundwave": {
        "texture_fn": texture_soundwave,
        "paint_fn": paint_soundwave,
        "variable_cc": False,
        "desc": "Audio waveform visualization - undulating sine wave envelope pattern",
    },
    "p_topographic": {
        "texture_fn": texture_topographic,
        "paint_fn": paint_topographic,
        "variable_cc": False,
        "desc": "Contour map elevation lines - terrain-style isolines from noise field",
    },
    "p_tessellation": {
        "texture_fn": texture_tessellation,
        "paint_fn": paint_tessellation,
        "variable_cc": False,
        "desc": "Geometric Penrose-style tiling - triangular grid interference edges",
    },
}

PARADIGM_MONOLITHICS = {
    "void": (spec_void, paint_void),
    "living_chrome": (spec_living_chrome, paint_living_chrome),
    "quantum": (spec_quantum, paint_quantum),
    "p_aurora": (spec_aurora, paint_aurora),
    "magnetic": (spec_magnetic, paint_magnetic),
    "ember": (spec_ember, paint_ember),
    "stealth": (spec_stealth, paint_stealth),
    "glass_armor": (spec_glass_armor, paint_glass_armor),
    "p_static": (spec_static, paint_static),
    "mercury_pool": (spec_mercury_pool, paint_mercury_pool),
    "phase_shift": (spec_phase_shift, paint_phase_shift),
    "gravity_well": (spec_gravity_well, paint_gravity_well),
    "thin_film": (spec_thin_film, paint_thin_film),
    "blackbody": (spec_blackbody, paint_blackbody),
    "wormhole": (spec_wormhole, paint_wormhole),
    "crystal_lattice": (spec_crystal_lattice, paint_crystal_lattice),
    "pulse": (spec_pulse, paint_pulse),
}

# ================================================================
# INTEGRATION
# ================================================================

def _wrap_paradigm_texture(original_fn, pattern_id):
    """Wrap a paradigm texture_fn so pattern features scale with resolution.

    CRITICAL FIX: Many paradigm texture functions use fixed pixel sizes
    (e.g., fresnel_ghost hex_h=80, tessellation freq=0.06) or fixed-scale
    noise fields. At swatch resolution (128x128) these produce clearly
    visible features. At full render (2048x2048) they become either
    microscopic or wildly over-dense depending on the math.

    Solution: Generate at a reference resolution and upscale pattern_val.
    This keeps features proportionally sized at any output resolution.
    """
    _REFERENCE_SIZE = 4096  # Match engine MAX_TEX_DIM - let engine scale control pattern density

    def wrapped(shape, mask, seed, sm):
        h, w = shape
        # Round up to nearest 32 to prevent internal crashes in texture fns
        _ALIGN = 32
        safe_h = ((h + _ALIGN - 1) // _ALIGN) * _ALIGN
        safe_w = ((w + _ALIGN - 1) // _ALIGN) * _ALIGN
        if max(safe_h, safe_w) > _REFERENCE_SIZE:
            scale_factor = max(safe_h, safe_w) / _REFERENCE_SIZE
            gen_h = max(16, ((int(safe_h / scale_factor) + _ALIGN - 1) // _ALIGN) * _ALIGN)
            gen_w = max(16, ((int(safe_w / scale_factor) + _ALIGN - 1) // _ALIGN) * _ALIGN)
            # Generate mask at reduced size too
            if mask is not None and mask.size > 0:
                mask_img = Image.fromarray((mask * 255).clip(0, 255).astype(np.uint8))
                small_mask = np.array(mask_img.resize((gen_w, gen_h), Image.BILINEAR)).astype(np.float32) / 255.0
            else:
                small_mask = np.ones((gen_h, gen_w), dtype=np.float32)
            result = original_fn((gen_h, gen_w), small_mask, seed, sm)
            # Upscale pattern_val to exact target resolution
            pv = result["pattern_val"]
            pv_u8 = (pv * 255).clip(0, 255).astype(np.uint8)
            pv_img = Image.fromarray(pv_u8)
            pv_img = pv_img.resize((w, h), Image.BILINEAR)
            result["pattern_val"] = np.array(pv_img).astype(np.float32) / 255.0
            return result
        else:
            # Generate at safe aligned size, then crop to exact
            if safe_h != h or safe_w != w:
                if mask is not None and mask.size > 0:
                    safe_mask = np.pad(mask, ((0, safe_h - h), (0, safe_w - w)), mode='edge')
                else:
                    safe_mask = mask
                result = original_fn((safe_h, safe_w), safe_mask, seed, sm)
                result["pattern_val"] = result["pattern_val"][:h, :w]
            else:
                result = original_fn(shape, mask, seed, sm)
        return result
    wrapped.__name__ = f"wrapped_{pattern_id}"
    wrapped.__doc__ = f"Scaled wrapper for paradigm texture: {pattern_id}"
    return wrapped


def integrate_paradigm(engine_module):
    """Merge PARADIGM expansion into the engine's registries."""
    # Wrap all paradigm texture functions with reference-resolution scaling
    for pat_id, pat_data in PARADIGM_PATTERNS.items():
        if "texture_fn" in pat_data:
            pat_data["texture_fn"] = _wrap_paradigm_texture(pat_data["texture_fn"], pat_id)

    engine_module.BASE_REGISTRY.update(PARADIGM_BASES)
    engine_module.PATTERN_REGISTRY.update(PARADIGM_PATTERNS)
    engine_module.MONOLITHIC_REGISTRY.update(PARADIGM_MONOLITHICS)

    # --- Sort registries alphabetically after merge ---
    for reg_name in ('BASE_REGISTRY', 'PATTERN_REGISTRY', 'MONOLITHIC_REGISTRY'):
        reg = getattr(engine_module, reg_name, None)
        if reg is not None:
            sorted_reg = dict(sorted(reg.items()))
            reg.clear()
            reg.update(sorted_reg)

    counts = {
        "bases": len(PARADIGM_BASES),
        "patterns": len(PARADIGM_PATTERNS),
        "specials": len(PARADIGM_MONOLITHICS),
    }
    total = counts["bases"] + counts["patterns"] + counts["specials"]
    # Guard against double-print (legacy shokker_paradigm_expansion + engine.expansions.paradigm both call this)
    if not getattr(integrate_paradigm, '_printed', False):
        print(f"[PARADIGM] Loaded {total} materials: "
              f"{counts['bases']} bases, {counts['patterns']} patterns, {counts['specials']} specials")
        integrate_paradigm._printed = True
    return counts


def get_paradigm_group_map():
    """Return group metadata for UI organization."""
    return {
        "bases": {
            "PARADIGM - Exotic Materials": [
                "singularity", "bioluminescent", "liquid_obsidian",
                "prismatic", "p_mercury",
            ],
            "PARADIGM - Elemental Forces": [
                "p_phantom", "p_volcanic", "arctic_ice",
                "carbon_weave", "nebula",
            ],
        },
        "patterns": {
            "PARADIGM - Physics Exploits": [
                "fresnel_ghost", "caustic", "dimensional", "neural", "p_plasma",
            ],
            "PARADIGM - Digital Reality": [
                "holographic", "circuitboard", "soundwave",
                "p_topographic", "p_tessellation",
            ],
        },
        "specials": {
            "PARADIGM - Reality Break": [
                "void", "wormhole", "gravity_well", "phase_shift",
            ],
            "PARADIGM - Energy States": [
                "ember", "blackbody", "pulse", "p_aurora", "thin_film",
            ],
            "PARADIGM - Extreme Matter": [
                "living_chrome", "mercury_pool", "quantum", "crystal_lattice",
            ],
            "PARADIGM - Stealth Tech": [
                "stealth", "glass_armor", "magnetic", "p_static",
            ],
        },
    }


def get_paradigm_counts():
    return {
        "bases": len(PARADIGM_BASES),
        "patterns": len(PARADIGM_PATTERNS),
        "specials": len(PARADIGM_MONOLITHICS),
        "total": len(PARADIGM_BASES) + len(PARADIGM_PATTERNS) + len(PARADIGM_MONOLITHICS),
    }