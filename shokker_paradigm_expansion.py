"""
Shokker PARADIGM Expansion — "Impossible Materials"
=====================================================
10 finishes that exploit PBR physics in ways never attempted in sim racing.

These aren't just new textures. These are materials that shouldn't exist —
engineered by understanding how real-time PBR renderers interpret Metallic,
Roughness, and Clearcoat channels at the pixel level.

PBR PHYSICS EXPLOITS:
- Fresnel amplification: Tiny metallic differences invisible head-on become
  visible at glancing angles because Fresnel reflectance is non-linear
- Material state boundaries: Transition zones between M=0 (dielectric) and
  M=255 (conductor) create impossible-looking surface behaviors
- Roughness micro-variation: Sub-pixel roughness alternation tricks the GGX
  specular distribution into behaviors that don't exist in real materials
- Perceptual void: M=0 + R=255 + CC=0 creates "nothing" — the brain
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

Author: Shokker Engine — PARADIGM Series
"""

import numpy as np
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
# FIELD CACHES — avoid recomputing expensive fields across
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
# BASE #1: SINGULARITY — Black hole gravitational lensing material
# ================================================================

def paint_singularity(paint, shape, mask, seed, pm, bb):
    """Singularity — DEVASTATING gravitational lensing with blazing accretion rings."""
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

    # Blazing accretion ring glow — orange-white hot
    ring_bright = np.clip(ring_accum, 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + ring_bright * 0.35 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + ring_bright * 0.20 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + ring_bright * 0.10 * pm * mask, 0, 1)

    # Hot white center of rings
    ring_core = np.clip((ring_accum - 0.6) * 3.0, 0, 1) * 0.25 * pm
    paint = np.clip(paint + ring_core[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# BASE #2: BIOLUMINESCENT — Living glow-from-within material
# ================================================================

def paint_bioluminescent(paint, shape, mask, seed, pm, bb):
    """Bioluminescent — VIVID organic cell glow with pulsing bio-light veins."""
    h, w = shape
    rng = np.random.RandomState(seed + 5101)

    # Cell structure at multiple scales
    cell_noise = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 5100)
    cell_noise = (cell_noise - cell_noise.min()) / (cell_noise.max() - cell_noise.min() + 1e-8)
    cells = np.clip((cell_noise - 0.35) * 3.0, 0, 1)

    # Darken non-glowing areas for contrast
    dark_base = (1 - cells) * 0.20 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - dark_base * mask, 0, 1)

    # Strong bio-glow: cyan-green luminescence
    glow = cells * 0.35 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + glow * 0.15 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + glow * 1.0 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + glow * 0.7 * mask, 0, 1)

    # Bio-vein network — fine-scale connecting lines between cells
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

    paint = np.clip(paint + bb * 0.3 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# BASE #3: LIQUID OBSIDIAN — Flowing glass-metal phase boundary
# ================================================================

def paint_liquid_obsidian(paint, shape, mask, seed, pm, bb):
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

    # Darken glass zones heavily — obsidian is DARK
    glass_darken = glass_zone * 0.35 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - glass_darken * mask), 0, 1)

    # Metal flow zones get bright reflective highlights
    metal_bright = metal_zone * 0.18 * pm
    paint = np.clip(paint + metal_bright[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Phase boundary edges — bright white-blue glow where glass meets metal
    gx = np.abs(np.diff(flow, axis=1, prepend=flow[:, :1]))
    gy = np.abs(np.diff(flow, axis=0, prepend=flow[:1, :]))
    boundary = np.clip((gx + gy) * 12, 0, 1)
    bound_glow = boundary * 0.25 * pm
    paint[:, :, 1] = np.clip(paint[:, :, 1] + bound_glow * 0.5 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + bound_glow * mask, 0, 1)
    paint = np.clip(paint + bound_glow[:, :, np.newaxis] * 0.3 * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# PATTERN #1: FRESNEL GHOST — Hidden pattern visible only at angle
# ================================================================

def texture_fresnel_ghost(shape, mask, seed, sm):
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)

    hex_h = 80
    hex_w = int(hex_h * 1.732 / 2)
    row = (yf / hex_h).astype(np.int32)
    col = (xf / hex_w).astype(np.int32)
    offset_x = xf - col * hex_w - (row % 2) * hex_w * 0.5
    offset_y = yf - row * hex_h
    cx, cy = hex_w * 0.5, hex_h * 0.5
    dist = np.sqrt((offset_x - cx)**2 + (offset_y - cy)**2)
    hex_ring = np.clip(1.0 - np.abs(dist - hex_h * 0.35) / 4, 0, 1)

    return {
        "pattern_val": hex_ring,
        "R_range": 5.0,
        "M_range": 15.0,
        "CC": None
    }

def paint_fresnel_ghost(paint, shape, mask, seed, pm, bb):
    """Fresnel ghost — virtually no paint modification (effect is ALL in spec)."""
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    hex_h = 80
    hex_w = int(hex_h * 1.732 / 2)
    row = (yf / hex_h).astype(np.int32)
    col = (xf / hex_w).astype(np.int32)
    offset_x = xf - col * hex_w - (row % 2) * hex_w * 0.5
    offset_y = yf - row * hex_h
    dist = np.sqrt((offset_x - hex_w * 0.5)**2 + (offset_y - hex_h * 0.5)**2)
    hex_ring = np.clip(1.0 - np.abs(dist - hex_h * 0.35) / 4, 0, 1)
    paint = np.clip(paint + hex_ring[:, :, np.newaxis] * 0.008 * pm * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# PATTERN #2: CAUSTIC — Underwater dancing light pattern
# ================================================================

def texture_caustic(shape, mask, seed, sm):
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32) / max(h, 1)
    xf = x.astype(np.float32) / max(w, 1)

    np.random.seed(seed + 5300)
    phi = 1.6180339887
    freqs = [7.0, 7.0 * phi, 7.0 * phi**2, 11.0, 11.0 * phi]
    angles = np.random.uniform(0, 2 * np.pi, 5)

    caustic = np.zeros((h, w), dtype=np.float32)
    for freq, angle in zip(freqs, angles):
        wave = np.sin((yf * np.cos(angle) + xf * np.sin(angle)) * freq * 2 * np.pi)
        caustic += wave

    caustic = (caustic - caustic.min()) / (caustic.max() - caustic.min() + 1e-8)
    caustic = caustic ** 2

    return {
        "pattern_val": caustic,
        "R_range": -60.0,
        "M_range": 80.0,
        "CC": None
    }

def paint_caustic(paint, shape, mask, seed, pm, bb):
    """Caustic — subtle dancing light brightness pattern."""
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32) / max(h, 1)
    xf = x.astype(np.float32) / max(w, 1)

    np.random.seed(seed + 5300)
    phi = 1.6180339887
    freqs = [7.0, 7.0 * phi, 7.0 * phi**2, 11.0, 11.0 * phi]
    angles = np.random.uniform(0, 2 * np.pi, 5)

    caustic = np.zeros((h, w), dtype=np.float32)
    for freq, angle in zip(freqs, angles):
        wave = np.sin((yf * np.cos(angle) + xf * np.sin(angle)) * freq * 2 * np.pi)
        caustic += wave
    caustic = (caustic - caustic.min()) / (caustic.max() - caustic.min() + 1e-8)
    caustic = caustic ** 2

    brightness = caustic * 0.06 * pm
    paint = np.clip(paint + brightness[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# PATTERN #3: DIMENSIONAL — Newton's rings / thin-film interference
# ================================================================
# PERF FIX: ring_field now cached so texture_ and paint_ share it.
# Also capped n_centers to 15 max.

def _compute_dimensional_field(shape, seed):
    """Compute the dimensional ring field — cached between texture and paint calls."""
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)

    rng = np.random.RandomState(seed + 5400)
    n_centers = min(15, max(4, (h * w) // (300 * 300) + 3))
    centers = [(rng.randint(0, h), rng.randint(0, w)) for _ in range(n_centers)]

    ring_field = np.zeros((h, w), dtype=np.float32)
    for cy, cx in centers:
        dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
        rings = np.cos(np.sqrt(dist) * 1.2) * 0.5 + 0.5
        fade = np.clip(1.0 - dist / (max(h, w) * 0.4), 0, 1)
        ring_field += rings * fade

    ring_field = (ring_field - ring_field.min()) / (ring_field.max() - ring_field.min() + 1e-8)
    return ring_field

def texture_dimensional(shape, mask, seed, sm):
    cache_key = ("dimensional", shape, seed)
    ring_field = _get_cached_field(cache_key, lambda: _compute_dimensional_field(shape, seed))
    return {
        "pattern_val": ring_field,
        "R_range": -50.0,
        "M_range": 60.0,
        "CC": None
    }

def paint_dimensional(paint, shape, mask, seed, pm, bb):
    """Dimensional — iridescent color shift along interference rings. Uses cached field."""
    cache_key = ("dimensional", shape, seed)
    ring_field = _get_cached_field(cache_key, lambda: _compute_dimensional_field(shape, seed))

    hue = ring_field
    sat = np.full_like(hue, 0.4)
    val = np.full_like(hue, 0.5)
    r_i, g_i, b_i = _hsv_to_rgb(hue, sat, val)

    blend = 0.12 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + r_i * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + g_i * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + b_i * blend * mask, 0, 1)
    return paint


# ================================================================
# PATTERN #4: NEURAL — Living neural network mesh
# ================================================================
# PERF FIX v2: Capped to 40 neurons max. Axons rasterized via PIL
# ImageDraw (bitmap) instead of per-pixel distance math. Voronoi
# cached between texture and paint. ~100x faster on 2048x2048.

def _compute_neural_field(shape, seed):
    """Compute neural Voronoi + axon field. Cached between texture/paint."""
    h, w = shape
    # CAP: max 40 neurons regardless of resolution
    n_neurons = min(40, max(15, (h * w) // (200 * 200)))
    min_dist, cell_id, pts = _voronoi(shape, n_neurons, seed + 5500)

    max_d = min_dist.max() + 1e-8
    norm_dist = min_dist / (max_d * 0.15)
    boundary = np.clip(1.0 - norm_dist, 0, 1)

    # AXONS: Rasterize via PIL ImageDraw — O(n_neurons * 3) line draws
    # instead of O(n_neurons * 3 * h * w) per-pixel distance calcs
    axon_img = Image.new('L', (w, h), 0)
    draw = ImageDraw.Draw(axon_img)
    axon_width = max(2, min(4, h // 512))

    for i in range(len(pts)):
        dists_to_others = np.sqrt(((pts - pts[i])**2).sum(axis=1))
        dists_to_others[i] = 1e9
        nearest = np.argsort(dists_to_others)[:3]
        for j in nearest:
            p1y, p1x = int(pts[i][0]), int(pts[i][1])
            p2y, p2x = int(pts[j][0]), int(pts[j][1])
            draw.line([(p1x, p1y), (p2x, p2y)], fill=255, width=axon_width)

    axon_field = np.array(axon_img).astype(np.float32) / 255.0
    # Slight blur for anti-aliasing
    axon_blur = Image.fromarray((axon_field * 255).astype(np.uint8))
    axon_blur = axon_blur.filter(ImageFilter.GaussianBlur(radius=1))
    axon_field = np.array(axon_blur).astype(np.float32) / 255.0

    pattern = np.clip(boundary * 0.6 + axon_field * 0.8, 0, 1)
    return min_dist, cell_id, pts, boundary, axon_field, pattern

def texture_neural(shape, mask, seed, sm):
    cache_key = ("neural", shape, seed)
    fields = _get_cached_field(cache_key, lambda: _compute_neural_field(shape, seed))
    _, _, _, _, _, pattern = fields
    return {
        "pattern_val": pattern,
        "R_range": -90.0,
        "M_range": 100.0,
        "CC": None
    }

def paint_neural(paint, shape, mask, seed, pm, bb):
    """Neural — glow along axon paths, darken cell boundaries. Uses cached field."""
    cache_key = ("neural", shape, seed)
    fields = _get_cached_field(cache_key, lambda: _compute_neural_field(shape, seed))
    min_dist, _, _, boundary, _, _ = fields
    max_d = min_dist.max() + 1e-8

    paint = np.clip(paint - boundary[:, :, np.newaxis] * 0.08 * pm * mask[:, :, np.newaxis], 0, 1)
    center_glow = np.clip(min_dist / (max_d * 0.3) - 0.3, 0, 0.5) * 0.10 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + center_glow * 0.5 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + center_glow * 1.0 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + center_glow * 0.9 * mask, 0, 1)
    return paint

# ================================================================
# PATTERN #5: PLASMA — Plasma ball discharge tendrils
# ================================================================

def _compute_plasma_field(shape, seed):
    h, w = shape
    yf = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    xf = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    rng = np.random.RandomState(seed + 5510)
    field = np.zeros((h, w), dtype=np.float32)
    for _ in range(6):
        fx = rng.uniform(3, 12)
        fy = rng.uniform(3, 12)
        phase = rng.uniform(0, 2 * np.pi)
        field += np.sin(yf * fy * 2 * np.pi + xf * fx * 2 * np.pi + phase)
    field = (field - field.min()) / (field.max() - field.min() + 1e-8)
    # Sharpen into tendril-like structures
    field = np.clip((field - 0.45) * 5, 0, 1)
    return field

def texture_plasma(shape, mask, seed, sm):
    cache_key = ("plasma", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_plasma_field(shape, seed))
    return {"pattern_val": field, "R_range": -70.0, "M_range": 90.0, "CC": None}

def paint_plasma(paint, shape, mask, seed, pm, bb):
    cache_key = ("plasma", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_plasma_field(shape, seed))
    # Electric purple-blue glow on tendrils
    paint[:, :, 0] = np.clip(paint[:, :, 0] + field * 0.06 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + field * 0.01 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + field * 0.08 * pm * mask, 0, 1)
    return paint


# ================================================================
# PATTERN #6: HOLOGRAPHIC — Hologram diffraction grating
# ================================================================

def texture_holographic(shape, mask, seed, sm):
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Diagonal diffraction lines at multiple angles
    g1 = (np.sin(yf * 0.15 + xf * 0.08) * 0.5 + 0.5)
    g2 = (np.sin(yf * 0.06 - xf * 0.12) * 0.5 + 0.5)
    g3 = (np.sin((yf + xf) * 0.1) * 0.5 + 0.5)
    field = (g1 + g2 + g3) / 3.0
    return {"pattern_val": field, "R_range": -40.0, "M_range": 70.0, "CC": None}

def paint_holographic(paint, shape, mask, seed, pm, bb):
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    g1 = (np.sin(yf * 0.15 + xf * 0.08) * 0.5 + 0.5)
    g2 = (np.sin(yf * 0.06 - xf * 0.12) * 0.5 + 0.5)
    g3 = (np.sin((yf + xf) * 0.1) * 0.5 + 0.5)
    field = (g1 + g2 + g3) / 3.0
    # Rainbow shift based on grating position
    r_s, g_s, b_s = _hsv_to_rgb(field, np.full_like(field, 0.5), np.full_like(field, 0.5))
    blend = 0.10 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + r_s * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + g_s * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + b_s * blend * mask, 0, 1)
    return paint


# ================================================================
# PATTERN #7: CIRCUITBOARD — PCB trace pattern
# ================================================================

def _compute_circuit_field(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed + 5520)
    # Grid of traces — horizontal and vertical lines with junctions
    grid_h, grid_w = max(8, h // 128), max(8, w // 128)
    small = np.zeros((grid_h, grid_w), dtype=np.float32)
    # Random traces
    for _ in range(grid_h * 2):
        r = rng.randint(0, grid_h)
        c1, c2 = sorted(rng.randint(0, grid_w, 2))
        small[r, c1:c2+1] = 1.0
    for _ in range(grid_w * 2):
        c = rng.randint(0, grid_w)
        r1, r2 = sorted(rng.randint(0, grid_h, 2))
        small[r1:r2+1, c] = 1.0
    img = Image.fromarray((small * 255).astype(np.uint8))
    img = img.resize((w, h), Image.NEAREST)
    field = np.array(img).astype(np.float32) / 255.0
    # Slight blur for anti-aliasing
    blur = Image.fromarray((field * 255).astype(np.uint8))
    blur = blur.filter(ImageFilter.GaussianBlur(radius=1))
    return np.array(blur).astype(np.float32) / 255.0

def texture_circuitboard(shape, mask, seed, sm):
    cache_key = ("circuit", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_circuit_field(shape, seed))
    return {"pattern_val": field, "R_range": -80.0, "M_range": 110.0, "CC": None}

def paint_circuitboard(paint, shape, mask, seed, pm, bb):
    cache_key = ("circuit", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_circuit_field(shape, seed))
    # Traces get a green-gold tint
    paint[:, :, 0] = np.clip(paint[:, :, 0] + field * 0.03 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + field * 0.06 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - field * 0.02 * pm * mask, 0, 1)
    return paint


# ================================================================
# PATTERN #8: SOUNDWAVE — Audio waveform visualization
# ================================================================

def texture_soundwave(shape, mask, seed, sm):
    h, w = shape
    yf = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    xf = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    rng = np.random.RandomState(seed + 5530)
    # Stacked sine waves forming a waveform envelope
    wave = np.zeros((h, w), dtype=np.float32)
    for _ in range(4):
        freq = rng.uniform(4, 20)
        amp = rng.uniform(0.2, 0.6)
        wave += amp * np.sin(xf * freq * 2 * np.pi)
    wave = wave / (np.abs(wave).max() + 1e-8)
    # Distance from waveform centerline
    dist_from_wave = np.abs(yf - wave * 0.4)
    field = np.clip(1.0 - dist_from_wave * 4, 0, 1)
    return {"pattern_val": field, "R_range": -60.0, "M_range": 85.0, "CC": None}

def paint_soundwave(paint, shape, mask, seed, pm, bb):
    h, w = shape
    yf = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    xf = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    rng = np.random.RandomState(seed + 5530)
    wave = np.zeros((h, w), dtype=np.float32)
    for _ in range(4):
        freq = rng.uniform(4, 20)
        amp = rng.uniform(0.2, 0.6)
        wave += amp * np.sin(xf * freq * 2 * np.pi)
    wave = wave / (np.abs(wave).max() + 1e-8)
    dist_from_wave = np.abs(yf - wave * 0.4)
    field = np.clip(1.0 - dist_from_wave * 4, 0, 1)
    glow = field * 0.05 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + glow * 0.3 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + glow * 1.0 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + glow * 0.6 * mask, 0, 1)
    return paint

# ================================================================
# PATTERN #9: TOPOGRAPHIC — Contour map elevation lines
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
    cache_key = ("topo", shape, seed)
    field = _get_cached_field(cache_key, lambda: _compute_topo_field(shape, seed))
    paint = np.clip(paint + field[:, :, np.newaxis] * 0.04 * pm * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# PATTERN #10: TESSELLATION — Geometric Penrose-style tiling
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
    paint = np.clip(paint + field[:, :, np.newaxis] * 0.03 * pm * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #1: VOID — Material with apparent holes/transparency
# ================================================================
# PERF FIX: Capped to 25 voids max. Voronoi cached between spec/paint.

def _compute_void_field(shape, seed):
    """Generate void holes using a hex grid — dense honeycomb perforation pattern.
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
    # This gives ~50% void coverage — dramatic and unmistakable
    is_void_cell = ((row + col) % 2 == 0).astype(np.float32)

    # Slight randomness: hash-based jitter to break perfect regularity
    cell_hash = ((row * 7919 + col * 104729 + seed) % 100).astype(np.float32) / 100.0
    # Keep 85% of void cells (vs old 35%) — much denser coverage
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
    is_void_soft, _ = _get_cached_field(cache_key, lambda: _compute_void_field(shape, seed))

    M = (1 - is_void_soft) * 255 * sm
    R = is_void_soft * 255 + (1 - is_void_soft) * 2
    CC = np.zeros((h, w), dtype=np.float32)

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = CC.astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_void(paint, shape, mask, seed, pm, bb):
    """Void — darken void patches, keep chrome areas bright. Uses cached field."""
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
    paint = np.clip(paint + bb * 0.3 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #2: LIVING CHROME — Chrome that appears to undulate
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
    micro = (micro - micro.min()) / (micro.max() - micro.min() + 1e-8) * 0.1

    M = 255 * sm
    R = (undulation * 40 + micro * 15) * sm

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = 0
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_living_chrome(paint, shape, mask, seed, pm, bb):
    """Living Chrome — UNDULATING liquid mirror with dramatic bright/dark wave contrast."""
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
    return paint

# ================================================================
# MONOLITHIC #3: QUANTUM — Simultaneously every material at once
# ================================================================
# VISUAL FIX: 16px blocks instead of 4px. Noise-based zones instead
# of pure random — creates coherent material "regions" that still
# look impossible but not like pixel soup.

def spec_quantum(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    rng = np.random.RandomState(seed + 5800)

    block_size = 16
    bh = (h + block_size - 1) // block_size
    bw = (w + block_size - 1) // block_size

    # Coherent noise for M and R instead of pure random
    m_noise = _noise((bh, bw), [2, 4, 8], [0.3, 0.4, 0.3], seed + 5800)
    r_noise = _noise((bh, bw), [2, 4, 8], [0.3, 0.4, 0.3], seed + 5801)
    m_noise = (m_noise - m_noise.min()) / (m_noise.max() - m_noise.min() + 1e-8)
    r_noise = (r_noise - r_noise.min()) / (r_noise.max() - r_noise.min() + 1e-8)

    # Add some randomness on top of the noise for quantum unpredictability
    block_M = np.clip(m_noise * 200 + rng.randint(-40, 40, (bh, bw)), 0, 255).astype(np.float32)
    block_R = np.clip(r_noise * 200 + rng.randint(-40, 40, (bh, bw)), 0, 255).astype(np.float32)

    M_img = Image.fromarray(block_M.clip(0, 255).astype(np.uint8))
    R_img = Image.fromarray(block_R.clip(0, 255).astype(np.uint8))
    M_full = np.array(M_img.resize((w, h), Image.NEAREST)).astype(np.float32)
    R_full = np.array(R_img.resize((w, h), Image.NEAREST)).astype(np.float32)

    M_full = M_full * sm
    R_full = R_full * sm

    spec[:, :, 0] = np.clip(M_full * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R_full * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.where(mask > 0.5, 16, 0).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_quantum(paint, shape, mask, seed, pm, bb):
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
    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #4: AURORA — Northern lights shimmer
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

    M = (aurora * 180 + 40) * sm
    R = ((1 - aurora) * 60 + 5) * sm

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.where(mask > 0.5, 16, 0).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_aurora(paint, shape, mask, seed, pm, bb):
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

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #5: MAGNETIC — Iron filing magnetic field lines
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

    M = (lines * 200 + 30) * sm
    R = ((1 - lines) * 80 + 10) * sm

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = 0
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_magnetic(paint, shape, mask, seed, pm, bb):
    """Magnetic — VISIBLE field line pattern with pole glow and iron filing texture."""
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

    # Field line visibility — strong contrast between line and gap
    line_bright = lines * 0.22 * pm
    line_dark = (1 - lines) * 0.18 * pm
    paint = np.clip(paint + line_bright[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - line_dark * mask, 0, 1)

    # Pole proximity glow — bright white-blue near poles
    pole_glow = np.clip((mag_acc - 0.5) * 3, 0, 1) * 0.20 * pm
    paint[:, :, 1] = np.clip(paint[:, :, 1] + pole_glow * 0.5 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + pole_glow * mask, 0, 1)
    paint = np.clip(paint + pole_glow[:, :, np.newaxis] * 0.3 * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #6: EMBER — Glowing hot metal cooling
# ================================================================

def spec_ember(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    heat = _noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 5820)
    heat = (heat - heat.min()) / (heat.max() - heat.min() + 1e-8)

    # Hot zones: low M (dielectric glow), low R (smooth emission look)
    # Cool zones: high M (dark metal), high R (rough cooled surface)
    M = ((1 - heat) * 220 + 10) * sm
    R = ((1 - heat) * 180 + 5) * sm

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = 0
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_ember(paint, shape, mask, seed, pm, bb):
    """Ember — GLOWING hot metal with blazing orange cracks and dark cooled surface."""
    h, w = shape
    rng = np.random.RandomState(seed + 5821)
    heat = _noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 5820)
    heat = (heat - heat.min()) / (heat.max() - heat.min() + 1e-8)

    # Cool zones darken heavily — cooled metal is near-black
    cool = np.clip((0.5 - heat) * 2.5, 0, 1)
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - cool * 0.50 * pm * mask), 0, 1)

    # Hot = blazing orange-red glow
    glow_r = heat * 0.35 * pm
    glow_g = heat * heat * 0.18 * pm  # squared = yellow only at hottest
    paint[:, :, 0] = np.clip(paint[:, :, 0] + glow_r * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + glow_g * mask, 0, 1)

    # White-hot cores
    white_core = np.clip((heat - 0.8) * 5, 0, 1) * 0.25 * pm
    paint = np.clip(paint + white_core[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Ember sparkle in hot zones
    sparkle = rng.random(shape).astype(np.float32)
    embers = np.where((sparkle > 0.975) & (heat > 0.3), 0.20 * pm, 0.0)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + embers * mask, 0, 1)

    paint = np.clip(paint + bb * 0.15 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #7: STEALTH — Radar-absorbing angular facets
# ================================================================

def spec_stealth(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    rng = np.random.RandomState(seed + 5830)

    # Angular faceted surface — large Voronoi cells with flat properties
    n_facets = min(30, max(10, (h * w) // (250 * 250)))
    _, cell_id, _ = _voronoi(shape, n_facets, seed + 5830)

    # Each facet gets slightly different (but all very high) roughness
    facet_R = rng.randint(180, 245, n_facets).astype(np.float32)
    facet_M = rng.randint(5, 40, n_facets).astype(np.float32)

    M = facet_M[cell_id] * sm
    R = facet_R[cell_id] * sm

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = 0
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_stealth(paint, shape, mask, seed, pm, bb):
    """Stealth — ANGULAR faceted dark surface with visible facet edges and subtle green-gray tint."""
    h, w = shape
    rng = np.random.RandomState(seed + 5831)

    # Very dark base
    darken = 0.72 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - darken * mask), 0, 1)

    # Faceted surface — Voronoi-based angular plates
    n_facets = min(30, max(10, (h * w) // (250 * 250)))
    min_dist, cell_id, _ = _voronoi(shape, n_facets, seed + 5830)
    max_d = min_dist.max() + 1e-8

    # Each facet gets slightly different darkness for angular contrast
    facet_bright = rng.uniform(0.0, 0.08, n_facets + 1).astype(np.float32)
    facet_val = facet_bright[np.clip(cell_id, 0, n_facets)]
    paint = np.clip(paint + facet_val[:, :, np.newaxis] * pm * mask[:, :, np.newaxis], 0, 1)

    # Facet edge highlights — visible seam lines
    edge = np.clip(1.0 - min_dist / (max_d * 0.04), 0, 1) * 0.12 * pm
    paint = np.clip(paint + edge[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Slight military green-gray tint
    paint[:, :, 1] = np.clip(paint[:, :, 1] + 0.02 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #8: GLASS ARMOR — Transparent armor plating illusion
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

    M = (is_edge * 200 + (1 - is_edge) * 5) * sm
    R = (is_edge * 30 + (1 - is_edge) * 5) * sm
    CC = (1 - is_edge) * 16  # Clearcoat on glass only

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_glass_armor(paint, shape, mask, seed, pm, bb):
    """Glass Armor — VISIBLE plate grid with strong blue glass panels and dark metallic frame."""
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

    # Dark metallic frame edges — clearly visible grid
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

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #9: STATIC — TV static / signal noise
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

    M = (noise_full * 255 * (1 - scan_line * 0.5)) * sm
    R = ((1 - noise_full) * 200 + scan_line * 55) * sm

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = 0
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_static(paint, shape, mask, seed, pm, bb):
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

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# MONOLITHIC #10: MERCURY POOL — Liquid mercury pooling effect
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

    M = 250 * sm  # Always highly metallic
    R = ((1 - pool_smooth) * 70 + pool_smooth * 3) * sm  # Pools = mirror, gaps = rougher

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = 0  # No clearcoat — raw liquid metal
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_mercury_pool(paint, shape, mask, seed, pm, bb):
    """Mercury Pool — DRAMATIC liquid metal pools with mirror-bright centers and dark gaps."""
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

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# BASE #4: PRISMATIC — Rainbow-shifting metallic
# ================================================================

def paint_prismatic(paint, shape, mask, seed, pm, bb):
    """Prismatic — VIVID rainbow spectral shift with noise-warped iridescence."""
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32) / max(h, 1)
    xf = x.astype(np.float32) / max(w, 1)
    rng = np.random.RandomState(seed + 5170)

    # Noise-warped diagonal rainbow — not just a flat gradient
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

    paint = np.clip(paint + bb * 0.3 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# BASE #5: MERCURY — Liquid metal pooling surface
# ================================================================

def paint_mercury(paint, shape, mask, seed, pm, bb):
    """Mercury — LIQUID METAL pooling with dramatic bright/dark flow contrast."""
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

    # Flow boundaries — bright edge highlights where mercury pools meet
    gx = np.abs(np.diff(flow, axis=1, prepend=flow[:, :1]))
    gy = np.abs(np.diff(flow, axis=0, prepend=flow[:1, :]))
    edge = np.clip((gx + gy) * 15, 0, 1) * 0.15 * pm
    paint = np.clip(paint + edge[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# BASE #6: PHANTOM — Barely-there translucent mist
# ================================================================

def paint_phantom(paint, shape, mask, seed, pm, bb):
    """Phantom — ETHEREAL translucent mist with ghostly wisps and spectral fade."""
    h, w = shape
    rng = np.random.RandomState(seed + 5221)

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

    # Fog brightening — push toward pale white-blue
    fog = mist1 * 0.25 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + fog * 0.7 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + fog * 0.8 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + fog * 1.0 * mask, 0, 1)

    # Ghostly wisps — thin bright streaks in second noise layer
    wisps = np.clip(1.0 - np.abs(mist2 - 0.5) * 5.0, 0, 1)
    wisp_bright = wisps * 0.18 * pm
    paint = np.clip(paint + wisp_bright[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Dark void pockets between mist layers for depth
    void = np.clip((0.25 - mist1) * 4, 0, 1) * 0.15 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - void * mask, 0, 1)

    paint = np.clip(paint + bb * 0.3 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# BASE #7: VOLCANIC — Lava cooling to rock
# ================================================================

def paint_volcanic(paint, shape, mask, seed, pm, bb):
    """Volcanic — MOLTEN LAVA with blazing cracks, scorched rock, and ember glow."""
    h, w = shape
    rng = np.random.RandomState(seed + 5231)
    heat = _noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 5230)
    heat = (heat - heat.min()) / (heat.max() - heat.min() + 1e-8)

    # Cool rock zones — darken HARD to near-black
    cool = np.clip((0.45 - heat) * 3, 0, 1)
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - cool * 0.65 * pm * mask), 0, 1)

    # Hot lava veins — blazing orange-red-yellow
    lava = np.clip((heat - 0.45) * 3, 0, 1)
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

    paint = np.clip(paint + bb * 0.15 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# BASE #8: ARCTIC ICE — Frozen crystalline surface
# ================================================================

def paint_arctic_ice(paint, shape, mask, seed, pm, bb):
    """Arctic Ice — FROZEN crystalline with deep blue cracks and frost shimmer."""
    h, w = shape
    rng = np.random.RandomState(seed + 5241)

    # Crystal crack network
    n_crystals = min(25, max(8, (h * w) // (350 * 350)))
    min_dist, cell_id, _ = _voronoi(shape, n_crystals, seed + 5240)
    max_d = min_dist.max() + 1e-8
    edge = np.clip(1.0 - min_dist / (max_d * 0.06), 0, 1)
    interior = 1 - edge

    # Base ice tint — push toward cold blue-white
    blend = 0.20 * pm
    paint[:, :, 0] = paint[:, :, 0] * (1 - mask * blend) + 0.70 * mask * blend
    paint[:, :, 1] = paint[:, :, 1] * (1 - mask * blend) + 0.82 * mask * blend
    paint[:, :, 2] = paint[:, :, 2] * (1 - mask * blend) + 0.95 * mask * blend

    # Deep blue crack lines — dramatically dark
    crack_dark = edge * 0.35 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] - crack_dark * 0.9 * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] - crack_dark * 0.6 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - crack_dark * 0.2 * mask, 0, 1)

    # Interior ice body — subtle blue variation per crystal cell
    cell_hue = (cell_id % 5).astype(np.float32) / 5.0 * 0.08  # slight per-cell blue variation
    paint[:, :, 2] = np.clip(paint[:, :, 2] + interior * cell_hue * 0.15 * pm * mask, 0, 1)

    # Frost shimmer sparkle
    sparkle = rng.random(shape).astype(np.float32)
    frost = np.where(sparkle > 0.97, 0.22 * pm, 0.0)
    paint = np.clip(paint + frost[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.3 * mask[:, :, np.newaxis], 0, 1)
    return paint

# ================================================================
# BASE #9: CARBON WEAVE — Carbon fiber with metallic threads
# ================================================================

def paint_carbon_weave(paint, shape, mask, seed, pm, bb):
    """Carbon Weave — DEEP carbon fiber with visible weave texture and metallic thread glint."""
    h, w = shape
    y, x = _mgrid(shape)
    rng = np.random.RandomState(seed + 5251)

    # Diagonal weave pattern
    weave_size = max(8, h // 128)
    diag1 = ((y + x) // weave_size % 2).astype(np.float32)
    diag2 = ((y - x) // weave_size % 2).astype(np.float32)
    weave = (diag1 + diag2) * 0.5

    # Heavy darkening — carbon fiber is DARK
    darken = 0.55 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - darken * mask), 0, 1)

    # Weave highlights — strong enough to see the pattern clearly
    highlight = weave * 0.18 * pm
    paint = np.clip(paint + highlight[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Metallic thread glint — scattered bright spots along weave peaks
    sparkle = rng.random(shape).astype(np.float32)
    thread_glint = np.where((sparkle > 0.96) & (weave > 0.4), 0.20 * pm, 0.0)
    paint = np.clip(paint + thread_glint[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Slight blue tint in weave valleys for depth
    valleys = (1 - weave) * 0.04 * pm
    paint[:, :, 2] = np.clip(paint[:, :, 2] + valleys * mask, 0, 1)

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# BASE #10: NEBULA — Space dust cloud material
# ================================================================

def paint_nebula(paint, shape, mask, seed, pm, bb):
    """Nebula — DEEP SPACE cosmic cloud with vivid purple-blue, hot pink, and bright stars."""
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

    # Vivid nebula color palette — purple, blue, hot pink, cyan
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

    # Bright star sparkles — more frequent, brighter
    stars = rng.random((h, w)).astype(np.float32)
    star_glow = np.where(stars > 0.99, 0.30 * pm, 0.0)
    paint = np.clip(paint + star_glow[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #11: PHASE SHIFT — Conductor/dielectric micro-stripe oscillation
# ================================================================
# PBR Exploit: Alternating 4px stripes of M=0 (dielectric) and M=255
# (conductor) force the renderer to interpolate between reflection
# models on adjacent pixels. The surface shifts between chrome and
# paint depending on viewing angle — neither state fully dominates.

def spec_phase_shift(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)

    # 4px alternating horizontal stripes — conductor vs dielectric
    stripe_width = 4
    stripe_phase = (y // stripe_width) % 2  # 0 or 1

    # Conductor stripes: M=255, R=10, CC=0
    # Dielectric stripes: M=0, R=10, CC=16
    M = (stripe_phase * 255).astype(np.float32) * sm
    R = np.full((h, w), 10.0, dtype=np.float32) * sm
    CC = ((1 - stripe_phase) * 16).astype(np.float32)

    # Add slight noise to prevent perfect banding artifacts
    rng = np.random.RandomState(seed + 6000)
    noise = rng.randint(-8, 9, (h, w)).astype(np.float32)
    M = np.clip(M + noise * stripe_phase, 0, 255)

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_phase_shift(paint, shape, mask, seed, pm, bb):
    """Phase Shift — DRAMATIC conductor/dielectric striping with warm-cool contrast and shimmer."""
    h, w = shape
    y, x = _mgrid(shape)
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

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #12: GRAVITY WELL — Radial Fresnel gradient depth trap
# ================================================================
# PBR Exploit: Concentric rings where M decreases 255→0 from center
# to edge while R increases 0→200 inverse. Each ring's Fresnel is
# different, creating a depth illusion — centers appear closer and
# reflective, edges appear recessed and matte.

def _compute_gravity_field(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed + 6100)
    n_wells = rng.randint(10, 18)
    y, x = _mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    sz = min(h, w)

    # Layer 1: Ambient gravitational ripple — full surface coverage
    grav_noise = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 6101)
    grav_noise = (grav_noise - grav_noise.min()) / (grav_noise.max() - grav_noise.min() + 1e-8)
    well_field = grav_noise * 0.15  # subtle gravitational distortion everywhere

    # Layer 2: Gravity wells — more numerous with larger radii
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

    # Center = chrome (M=255, R=0), edge = matte dielectric (M=0, R=200)
    M = (well * 255) * sm
    R = ((1 - well) * 200) * sm
    CC = np.where(well < 0.3, 16, 0).astype(np.float32)  # Clearcoat on outer edges only

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_gravity_well(paint, shape, mask, seed, pm, bb):
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

    # Bright rim glow at well edges — the showstopper ring effect
    edge = np.abs(np.diff(well, axis=1, prepend=well[:, :1])) + \
           np.abs(np.diff(well, axis=0, prepend=well[:1, :]))
    rim = np.clip(edge * 8, 0, 1) * 0.28 * pm
    paint = np.clip(paint + rim[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)

    # Slight blue tint in dark halo regions
    halo_blue = (1 - well) * 0.06 * pm
    paint[:, :, 2] = np.clip(paint[:, :, 2] + halo_blue * mask, 0, 1)

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #13: THIN FILM — Physically-linked color + reflectivity
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

    # Thick film = reflective metal, thin film = matte dielectric
    M = (film * 200 + 30) * sm  # 30-230 range
    R = ((1 - film) * 110 + 5) * sm  # 5-115 range
    CC = np.full((h, w), 16.0, dtype=np.float32)  # Always clearcoated

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_thin_film(paint, shape, mask, seed, pm, bb):
    h, w = shape
    cache_key = ("thin_film", shape, seed)
    film = _get_cached_field(cache_key, lambda: _compute_film_field(shape, seed))
    # Film thickness → hue cycle (oil-on-water rainbow)
    hue = (film * 2.5) % 1.0  # 2.5 cycles through full spectrum
    sat = np.full_like(hue, 0.7)
    val = np.full_like(hue, 0.6)
    r_c, g_c, b_c = _hsv_to_rgb(hue, sat, val)
    # STRONG blend — this is the most visible paint in PARADIGM
    blend = 0.25 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + r_c * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + g_c * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + b_c * blend * mask, 0, 1)
    paint = np.clip(paint + bb * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #14: BLACKBODY — Continuous temperature emission spectrum
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

    # Temperature → material state (continuous, not binary like ember)
    # Cold (0): M=5, R=220 (rough dark dielectric)
    # Warm (0.5): M=100, R=80 (mid-metallic moderate rough)
    # Hot (1.0): M=250, R=5 (mirror-smooth full conductor)
    M = (temp * 245 + 5) * sm
    R = ((1 - temp) * 215 + 5) * sm

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = 0  # No clearcoat — raw thermal surface
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_blackbody(paint, shape, mask, seed, pm, bb):
    h, w = shape
    cache_key = ("blackbody", shape, seed)
    temp = _get_cached_field(cache_key, lambda: _compute_blackbody_field(shape, seed))
    # Actual blackbody color curve:
    # 0.0 = black, 0.3 = dark red, 0.5 = orange, 0.7 = yellow, 1.0 = white
    r_bb = np.clip(temp * 3.0, 0, 1)  # Red comes first
    g_bb = np.clip((temp - 0.3) * 2.5, 0, 1)  # Green later
    b_bb = np.clip((temp - 0.6) * 3.0, 0, 1)  # Blue last (white-hot)
    # Strong blend — this needs to be visible
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
# MONOLITHIC #15: WORMHOLE — Connected void portal pairs
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

    # Ambient spacetime distortion — full surface coverage
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
        # Chrome rim: ring at portal edge — wider rim glow
        rim = np.exp(-((dist - radius)**2) / (radius * 0.5))
        rim_field = np.maximum(rim_field, rim)

    # Tunnels between portal pairs — wider connections
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
    CC = np.zeros((h, w), dtype=np.float32)

    M = M * sm
    R = R * sm

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_wormhole(paint, shape, mask, seed, pm, bb):
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

    paint = np.clip(paint + bb * 0.15 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #16: CRYSTAL LATTICE — Multi-scale hex grid interference
# ================================================================
# PBR Exploit: 3 overlapping hex grids at different scales create a
# parallax illusion of 3D depth. Where grids align = M=255 nodes.
# Where they diverge = chaotic M/R mixing. Impossible depth in 2D.

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
    CC = (node_sum > 0.5).astype(np.float32) * 16  # Clearcoat on aligned nodes

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_crystal_lattice(paint, shape, mask, seed, pm, bb):
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

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# MONOLITHIC #17: PULSE — Radial energy wavefront with metallic rings
# ================================================================
# PBR Exploit: Concentric sine rings from multiple epicenters.
# Ring crests: M=255, R=0 (mirror chrome catches all light).
# Ring troughs: M=0, R=180 (matte dielectric absorbs).
# Creates a "radar ping" effect — each ring catches light at
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

    # Ring crests (field≈1): M=255, R=0 (chrome mirror)
    # Ring troughs (field≈0): M=0, R=180 (matte dielectric)
    M = (field * 255) * sm
    R = ((1 - field) * 180) * sm

    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = 0  # No clearcoat — raw oscillation
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_pulse(paint, shape, mask, seed, pm, bb):
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

    paint = np.clip(paint + bb * 0.2 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# REGISTRY ENTRIES — 10 Bases, 10 Patterns, 17 Monolithics
# ================================================================

PARADIGM_BASES = {
    "singularity": {
        "M": 240, "R": 8, "CC": 0,
        "paint_fn": paint_singularity,
        "desc": "Black hole gravitational lensing — accretion rings glow at grazing angles",
        "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3],
        "noise_M": 30, "noise_R": 15,
    },
    "bioluminescent": {
        "M": 40, "R": 15, "CC": 16,
        "paint_fn": paint_bioluminescent,
        "desc": "Living glow-from-within — organic cells emit light under clearcoat",
        "noise_scales": [32, 64, 128], "noise_weights": [0.3, 0.4, 0.3],
        "noise_M": 15, "noise_R": 8,
    },
    "liquid_obsidian": {
        "M": 130, "R": 6, "CC": 16,
        "paint_fn": paint_liquid_obsidian,
        "desc": "Flowing glass-metal phase boundary — impossible material state transition",
        "noise_scales": [16, 32, 64], "noise_weights": [0.25, 0.4, 0.35],
        "noise_M": 120, "noise_R": 5,
    },
    "prismatic": {
        "M": 200, "R": 12, "CC": 16,
        "paint_fn": paint_prismatic,
        "desc": "Rainbow-shifting metallic — diagonal spectral gradient under clearcoat",
        "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3],
        "noise_M": 25, "noise_R": 10,
    },
    "p_mercury": {
        "M": 245, "R": 4, "CC": 0,
        "paint_fn": paint_mercury,
        "desc": "Liquid metal pooling — flowing silver mercury surface",
        "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3],
        "noise_M": 10, "noise_R": 8,
    },
    "p_phantom": {
        "M": 15, "R": 30, "CC": 0,
        "paint_fn": paint_phantom,
        "desc": "Barely-there translucent mist — ghostly fog-like presence",
        "noise_scales": [32, 64, 128], "noise_weights": [0.2, 0.4, 0.4],
        "noise_M": 10, "noise_R": 20,
    },
    "p_volcanic": {
        "M": 60, "R": 120, "CC": 0,
        "paint_fn": paint_volcanic,
        "desc": "Lava cooling to rock — glowing heat veins through dark stone",
        "noise_scales": [8, 16, 32, 64], "noise_weights": [0.2, 0.3, 0.3, 0.2],
        "noise_M": 40, "noise_R": 60,
    },
    "arctic_ice": {
        "M": 20, "R": 8, "CC": 16,
        "paint_fn": paint_arctic_ice,
        "desc": "Frozen crystalline surface — cracked ice with blue-white interior",
        "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3],
        "noise_M": 15, "noise_R": 6,
    },
    "carbon_weave": {
        "M": 80, "R": 60, "CC": 16,
        "paint_fn": paint_carbon_weave,
        "desc": "Carbon fiber with metallic threads — woven diagonal weave pattern",
        "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3],
        "noise_M": 30, "noise_R": 20,
    },
    "nebula": {
        "M": 30, "R": 25, "CC": 16,
        "paint_fn": paint_nebula,
        "desc": "Space dust cloud — purple-blue cosmic nebula with star sparkles",
        "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3],
        "noise_M": 20, "noise_R": 15,
    },
}

PARADIGM_PATTERNS = {
    "fresnel_ghost": {
        "texture_fn": texture_fresnel_ghost,
        "paint_fn": paint_fresnel_ghost,
        "variable_cc": False,
        "desc": "Hidden hex pattern — invisible head-on, appears at grazing angles via Fresnel",
    },
    "caustic": {
        "texture_fn": texture_caustic,
        "paint_fn": paint_caustic,
        "variable_cc": False,
        "desc": "Underwater dancing light — golden-ratio sine wave interference caustics",
    },
    "dimensional": {
        "texture_fn": texture_dimensional,
        "paint_fn": paint_dimensional,
        "variable_cc": False,
        "desc": "Newton's rings thin-film interference — rainbow concentric ring portals",
    },
    "neural": {
        "texture_fn": texture_neural,
        "paint_fn": paint_neural,
        "variable_cc": False,
        "desc": "Living neural network — Voronoi cells with glowing axon connections",
    },
    "p_plasma": {
        "texture_fn": texture_plasma,
        "paint_fn": paint_plasma,
        "variable_cc": False,
        "desc": "Plasma ball discharge — electric tendrils from overlapping sine fields",
    },
    "holographic": {
        "texture_fn": texture_holographic,
        "paint_fn": paint_holographic,
        "variable_cc": False,
        "desc": "Hologram diffraction grating — multi-angle rainbow interference lines",
    },
    "circuitboard": {
        "texture_fn": texture_circuitboard,
        "paint_fn": paint_circuitboard,
        "variable_cc": False,
        "desc": "PCB trace pattern — metallic circuit traces on dielectric substrate",
    },
    "soundwave": {
        "texture_fn": texture_soundwave,
        "paint_fn": paint_soundwave,
        "variable_cc": False,
        "desc": "Audio waveform visualization — undulating sine wave envelope pattern",
    },
    "p_topographic": {
        "texture_fn": texture_topographic,
        "paint_fn": paint_topographic,
        "variable_cc": False,
        "desc": "Contour map elevation lines — terrain-style isolines from noise field",
    },
    "p_tessellation": {
        "texture_fn": texture_tessellation,
        "paint_fn": paint_tessellation,
        "variable_cc": False,
        "desc": "Geometric Penrose-style tiling — triangular grid interference edges",
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
    _REFERENCE_SIZE = 4096  # Match engine MAX_TEX_DIM — let engine scale control pattern density

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

    counts = {
        "bases": len(PARADIGM_BASES),
        "patterns": len(PARADIGM_PATTERNS),
        "specials": len(PARADIGM_MONOLITHICS),
    }
    total = counts["bases"] + counts["patterns"] + counts["specials"]
    print(f"[PARADIGM] Loaded {total} impossible materials: "
          f"{counts['bases']} bases, {counts['patterns']} patterns, {counts['specials']} specials")
    return counts


def get_paradigm_group_map():
    """Return group metadata for UI organization."""
    return {
        "bases": {
            "PARADIGM — Impossible Materials": [
                "singularity", "bioluminescent", "liquid_obsidian",
                "prismatic", "p_mercury",
            ],
            "PARADIGM — Elemental Forces": [
                "p_phantom", "p_volcanic", "arctic_ice",
                "carbon_weave", "nebula",
            ],
        },
        "patterns": {
            "PARADIGM — Physics Exploits": [
                "fresnel_ghost", "caustic", "dimensional", "neural", "p_plasma",
            ],
            "PARADIGM — Digital Reality": [
                "holographic", "circuitboard", "soundwave",
                "p_topographic", "p_tessellation",
            ],
        },
        "specials": {
            "PARADIGM — Reality Break": [
                "void", "wormhole", "gravity_well", "phase_shift",
            ],
            "PARADIGM — Energy States": [
                "ember", "blackbody", "pulse", "p_aurora", "thin_film",
            ],
            "PARADIGM — Extreme Matter": [
                "living_chrome", "mercury_pool", "quantum", "crystal_lattice",
            ],
            "PARADIGM — Stealth Tech": [
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