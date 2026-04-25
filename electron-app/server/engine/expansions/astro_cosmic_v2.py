# -*- coding: utf-8 -*-
"""Astrological & Cosmic v2 — reimagined pattern entries for Shokker Paint Booth V5.

12 unique astro/cosmic textures with physics-based visual character.
NO zodiac signs. Each texture_fn and paint_fn is UNIQUE.
All bb contributions gated by pm. NaN-safe. Real physics simulations.

TILING: Textures are computed in a small cell then tiled
to fill the full shape, so patterns are SMALL and REPEATING across the canvas
(like intricate reference patterns), not one massive motif per car.
"""
import numpy as np

# ---------------------------------------------------------------------------
# Cell sizes — each becomes one visible "motif" in the tiled grid
# ~8 tiles across 2048px = 256px per tile.  Denser patterns use 192 or 128.
# ---------------------------------------------------------------------------
CELL_LARGE = 256   # ~8x8 tiles on 2048
CELL_MEDIUM = 192  # ~10x10 tiles
CELL_SMALL = 128   # ~16x16 tiles (dense patterns)


def _bb_norm(bb, h, w):
    """Normalize bb to 2D (h,w) array for paint blending."""
    if np.isscalar(bb) or getattr(bb, 'ndim', 2) == 0:
        return np.full((h, w), float(bb), dtype=np.float32)
    arr = np.asarray(bb, dtype=np.float32)
    if arr.ndim == 3:
        return np.mean(arr[:h, :w, :3], axis=2)
    if arr.ndim == 2:
        return arr[:h, :w]
    return np.full((h, w), float(np.mean(arr)), dtype=np.float32)


def _tile_to_shape(cell_pattern, shape):
    """Tile (ch, cw) array to fill (h, w), then crop to shape."""
    ch, cw = cell_pattern.shape[:2]
    h, w = shape[0], shape[1]
    ny, nx = (h + ch - 1) // ch, (w + cw - 1) // cw
    tiled = np.tile(cell_pattern, (ny, nx))
    return tiled[:h, :w].astype(np.float32)


def _grid_px(shape):
    """Pixel-space grid (0..h, 0..w)."""
    h, w = shape[:2]
    return np.mgrid[:h, :w].astype(np.float32)


def _apply_paint(paint, mask, pm, bb, effect_fn):
    """Standard paint application: blend paint->result using mask and pm."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = paint.shape[:2]
    if pm == 0.0:
        return paint.copy()
    bb2d = _bb_norm(bb, h, w)
    result = effect_fn(paint.copy(), h, w)
    m3 = mask[:, :, np.newaxis]
    out = paint * (1.0 - m3 * pm) + result * (m3 * pm)
    out += bb2d[:, :, np.newaxis] * 0.03 * m3 * pm
    return np.clip(out, 0, 1).astype(np.float32)


def multi_scale_noise(shape, scales, weights, seed):
    """Local noise generator — matches engine signature."""
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)
    for scale, weight in zip(scales, weights):
        s = max(1, scale)
        sh, sw = max(1, (h + s - 1) // s), max(1, (w + s - 1) // s)  # ceil division
        tile = rng.randn(sh, sw).astype(np.float32)
        stretched = np.repeat(np.repeat(tile, s, axis=0), s, axis=1)[:h, :w]
        result += stretched * weight
    return result

# ============================================================================
# TEXTURE FUNCTIONS (12 unique, physics-based)
# ============================================================================

def texture_pulsar_beacon(shape, mask, seed, sm):
    """Rotating neutron star beam — small repeating cell, tiled."""
    h, w = CELL_LARGE, CELL_LARGE
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.ogrid[:h, :w]
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    theta = np.arctan2(yy - cy, xx - cx)
    rng = np.random.RandomState(seed)
    rotation = rng.uniform(0, 2 * np.pi)
    beam_angle = np.abs(np.sin(theta - rotation))
    primary = np.exp(-rr / (max(h, w) / 3.0)) * (beam_angle ** 0.5)
    secondary_angle = np.abs(np.sin(theta - rotation - np.pi))
    secondary = np.exp(-rr / (max(h, w) / 2.5)) * (secondary_angle ** 0.4) * 0.4
    core = np.exp(-(rr / (max(h, w) / 12.0)) ** 2) * 2.0
    cell = np.clip(primary + secondary + core, 0.0, 1.0)
    pattern = _tile_to_shape(cell, shape)
    return {"pattern_val": pattern, "R_range": 55.0, "M_range": 40.0, "CC": None}

def texture_event_horizon(shape, mask, seed, sm):
    """Black hole accretion disk with gravitational lensing, photon ring, and spiral accretion."""
    h, w = CELL_LARGE, CELL_LARGE
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.ogrid[:h, :w]
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    theta = np.arctan2(yy - cy, xx - cx)
    rng = np.random.RandomState(seed)
    phase = rng.uniform(0, 2 * np.pi)
    max_dim = max(h, w)

    # Deep void center (event horizon shadow)
    void_r = max_dim / 12.0
    void = np.exp(-(rr / void_r) ** 4)  # Sharp dark center

    # Bright photon ring (innermost stable orbit)
    ring_r = max_dim / 6.0
    ring_width = max_dim / 35.0
    photon_ring = np.exp(-((rr - ring_r) / ring_width) ** 2) * 1.5

    # Gravitational lensing warped secondary ring
    lens_distort = np.sin(theta * 2 + phase) * max_dim / 20.0
    lens_r = ring_r * 1.4
    warped = np.exp(-((rr - lens_r - lens_distort) / (ring_width * 1.5)) ** 2) * 0.8

    # Accretion disk spiral with turbulent structure
    n_arms = 3
    spiral_phase = (theta * n_arms / (2 * np.pi) - np.log(rr / ring_r + 1e-8) * 0.6 + phase) % 1.0
    spiral_band = (np.sin(spiral_phase * 2 * np.pi) * 0.5 + 0.5) ** 0.7
    # Disk falls off with distance from center
    disk_falloff = np.exp(-((rr - ring_r * 1.8) / (max_dim / 3.5)) ** 2)
    accretion = spiral_band * disk_falloff * 0.7

    # Turbulent eddies in the disk
    turb = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 100)
    turb_val = np.clip(turb * 0.5 + 0.5, 0, 1)
    accretion = accretion * (0.7 + turb_val * 0.3)

    # Gravitational lensing glow (light bending around the hole)
    glow_falloff = 1.0 / (1.0 + (rr / (ring_r * 0.8)) ** 2) * 0.3

    # Combine: void darkens center, rings + spiral + lensing glow
    cell = np.clip(
        photon_ring + warped + accretion + glow_falloff - void * 1.5,
        0.0, 1.0
    )
    pattern = _tile_to_shape(cell, shape)
    return {"pattern_val": pattern, "R_range": 55.0, "M_range": 40.0, "CC": None}

def texture_solar_corona(shape, mask, seed, sm):
    """Sun's corona — small cell, tiled."""
    h, w = CELL_LARGE, CELL_LARGE
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.ogrid[:h, :w]
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    theta = np.arctan2(yy - cy, xx - cx)
    disk_r = max(h, w) / 6.0
    disk = 1.0 - np.exp(-(rr / disk_r) ** 2)
    tendrils = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed)  # Finer tendrils (was [4,8,16] = chunky at 256px cell)
    tendrils = np.clip(tendrils, 0.0, 1.0)
    field_lines = np.sin(theta * 8) * 0.5 + 0.5
    field_lines = np.exp(-rr / (max(h, w) / 2.5)) * field_lines
    corona_intensity = np.exp(-(rr - disk_r) / (max(h, w) / 3.0))
    corona_intensity = np.clip(corona_intensity, 0.0, 1.0)
    cell = disk * (1.0 - corona_intensity * 0.8) + corona_intensity * tendrils * field_lines
    pattern = _tile_to_shape(np.clip(cell, 0.0, 1.0), shape)
    return {"pattern_val": pattern, "R_range": 55.0, "M_range": 40.0, "CC": None}

def texture_nebula_pillars(shape, mask, seed, sm):
    """Pillars of Creation v2 — denser cell, sharper edges."""
    h, w = 80, 80  # Smaller cell for density (was CELL_LARGE=256)
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.ogrid[:h, :w]
    rng = np.random.RandomState(seed)
    pillars = []
    for _ in range(3):
        px = rng.uniform(cx - w / 3, cx + w / 3)
        py = rng.uniform(cy - h / 3, cy + h / 3)
        pillars.append((py, px))
    pattern = np.zeros((h, w), dtype=np.float32)
    for py, px in pillars:
        dy = np.abs(yy - py)
        dx = np.abs(xx - px)
        pillar_dist = np.sqrt(dy ** 2 + dx ** 2)
        pillar_width = max(h, w) / 15.0

        # Tall columnar shape (wider at base)
        column = np.exp(-(pillar_dist / (pillar_width * (1 + dy / h))) ** 1.5)

        # Internal turbulence
        turbulence = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.3, 0.2], seed + int(px))
        turbulence = np.clip(turbulence, 0.0, 1.0)

        # Bright edges (photoevaporation glow)
        edge_glow = np.exp(-(pillar_dist - pillar_width) ** 2 / (pillar_width ** 2)) * 0.6

        pattern += column * (0.7 + turbulence * 0.3) + edge_glow
    cell = np.clip(pattern / 1.8, 0.0, 1.0)  # Less division = more contrast (was /3.0)
    pattern_out = _tile_to_shape(cell, shape)
    # Background nebula fill for coverage
    bg_fill = multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 700) * 0.18 + 0.10
    pattern_out = np.clip(np.maximum(pattern_out, bg_fill), 0, 1)
    return {"pattern_val": pattern_out, "R_range": 55.0, "M_range": 40.0, "CC": None}

def texture_magnetar_field(shape, mask, seed, sm):
    """Extreme magnetic field v2 — sharp dipole field lines with toroidal distortion.
    Dense 64px cell for car-scale visibility. High-contrast ridged field lines."""
    h, w = 64, 64  # Dense tiling: 32 tiles across 2048
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.ogrid[:h, :w]
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2).astype(np.float32)
    theta = np.arctan2(yy - cy, xx - cx).astype(np.float32)

    # Sharp dipole field lines using sin² ridges (not soft 1/r³)
    n_lines = 8  # 8 visible field line arcs
    field_lines = np.sin(theta * n_lines + rr / 8.0) ** 2  # sharp ridges

    # Radial intensity: bright near poles, visible everywhere
    r_norm = rr / (h / 2.0)
    radial = np.clip(1.0 - r_norm * 0.6, 0.2, 1.0)

    # Equatorial enhancement (toroidal brightening)
    equator = np.abs(yy - cy).astype(np.float32) / (h / 2.0)
    toroidal = np.clip(1.0 - equator * 0.5, 0.3, 1.0)

    cell = np.clip(field_lines * radial * toroidal, 0.0, 1.0).astype(np.float32)
    return {"pattern_val": _tile_to_shape(cell, shape), "R_range": 80.0, "M_range": 65.0, "CC": None}

def texture_asteroid_belt(shape, mask, seed, sm):
    """Dense asteroid field v2 — scattered rocky fragments with surface texture.
    Dense 48px cell, 150 small rocks, np.maximum stacking (not averaging)."""
    h, w = 48, 48  # Dense tiling: 42 tiles across 2048
    rng = np.random.RandomState(seed)
    pattern = np.zeros((h, w), dtype=np.float32)

    # 150 small rocks (more dense, smaller features)
    num_asteroids = 150
    yy, xx = np.ogrid[:h, :w]
    for _ in range(num_asteroids):
        ay = rng.uniform(0, h)
        ax = rng.uniform(0, w)
        size = rng.uniform(1.5, 6.0)  # Much smaller rocks for car scale
        angle = rng.uniform(0, np.pi)
        depth = rng.uniform(0.4, 1.0)

        major = max(1.0, size * depth)
        minor = max(0.8, size * (0.4 + 0.3 * depth))

        dy = (yy - ay).astype(np.float32)
        dx = (xx - ax).astype(np.float32)
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        dx_rot = dx * cos_a + dy * sin_a
        dy_rot = -dx * sin_a + dy * cos_a

        # Sharper falloff (power 1.5 not 2.0) for visible edges
        asteroid = np.exp(-((dx_rot / major) ** 2 + (dy_rot / minor) ** 2) ** 0.75)
        # Stack with max (not add then divide)
        pattern = np.maximum(pattern, asteroid * depth)

    cell = np.clip(pattern, 0.0, 1.0).astype(np.float32)
    return {"pattern_val": _tile_to_shape(cell, shape), "R_range": 75.0, "M_range": 60.0, "CC": None}

def texture_gravitational_lens(shape, mask, seed, sm):
    """Einstein ring v2 — denser concentric rings with lensing distortion."""
    h, w = 80, 80  # Was CELL_LARGE=256
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.ogrid[:h, :w]
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)

    # Einstein ring radius
    einstein_r = max(h, w) / 4.0

    # Distortion strength (decreases with radius)
    distortion_scale = 1.0 / (1.0 + rr / (max(h, w) / 2.0))

    # Multiple concentric rings with smooth falloff
    rings = []
    for ring_num in range(1, 4):
        ring_r = einstein_r * (0.7 + 0.3 * ring_num)
        ring_width = max(h, w) / 40.0
        ring = np.exp(-((rr - ring_r) / ring_width) ** 2)
        rings.append(ring)

    # Combine rings with distortion
    pattern = sum(rings) * distortion_scale * 0.8  # Don't divide by N (was /len(rings))

    # Add subtle arc brightening
    arc_brightness = np.sin(np.arctan2(yy - cy, xx - cx) * 2) * 0.3 + 0.7
    pattern *= arc_brightness
    cell = np.clip(pattern, 0.0, 1.0)
    return {"pattern_val": _tile_to_shape(cell, shape), "R_range": 70.0, "M_range": 55.0, "CC": None}

def texture_cosmic_web(shape, mask, seed, sm):
    """Cosmic web filaments — small cell, tiled."""
    h, w = CELL_SMALL, CELL_SMALL
    rng = np.random.RandomState(seed)

    # Generate cluster nodes
    num_nodes = rng.randint(6, 12)
    nodes = [(rng.uniform(0, h), rng.uniform(0, w)) for _ in range(num_nodes)]

    yy, xx = np.ogrid[:h, :w]
    pattern = np.zeros((h, w), dtype=np.float32)

    # Create filaments between nearby nodes
    for i, (y1, x1) in enumerate(nodes):
        for j, (y2, x2) in enumerate(nodes):
            if i < j:
                # Distance to line segment
                dy = y2 - y1
                dx = x2 - x1
                seg_len = np.sqrt(dy ** 2 + dx ** 2) + 1e-6

                # Perpendicular distance from each pixel to line
                t = np.clip(((xx - x1) * dx + (yy - y1) * dy) / (seg_len ** 2), 0, 1)
                closest_x = x1 + t * dx
                closest_y = y1 + t * dy
                dist_to_line = np.sqrt((xx - closest_x) ** 2 + (yy - closest_y) ** 2)

                filament = np.exp(-(dist_to_line / 8.0) ** 2)
                pattern += filament * 0.5

    # Add cluster brightness at nodes
    for y, x in nodes:
        dy = yy - y
        dx = xx - x
        cluster = np.exp(-((dy ** 2 + dx ** 2) / (30.0 ** 2)))
        pattern += cluster * 0.8
    cell = np.clip(pattern / (num_nodes * 0.8), 0.0, 1.0)
    return {"pattern_val": _tile_to_shape(cell, shape), "R_range": 55.0, "M_range": 40.0, "CC": None}

def texture_plasma_ejection(shape, mask, seed, sm):
    """CME loop — small cell, tiled."""
    h, w = CELL_LARGE, CELL_LARGE
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.ogrid[:h, :w]

    rng = np.random.RandomState(seed)

    # Base position (one edge)
    base_y = h - max(h, w) / 8.0
    base_x = cx + rng.uniform(-w / 6, w / 6)

    # Expanding loop arch
    dy = yy - base_y
    dx = xx - base_x
    dist_from_base = np.sqrt(dy ** 2 + dx ** 2)

    # Parabolic arch shape
    arch_radius = max(h, w) / 3.0
    arch = np.exp(-((dist_from_base - arch_radius) / (max(h, w) / 20.0)) ** 2)
    arch *= np.maximum(0, 1.0 - dy / (max(h, w) / 2.0))  # Upward only

    # Magnetic field containment lines (radial from base)
    theta_from_base = np.arctan2(dy, dx)
    field_containment = np.sin(theta_from_base * 6) * 0.4 + 0.6

    # Particle spray (turbulent noise)
    spray = multi_scale_noise((h, w), [16, 32, 64], [0.6, 0.3, 0.1], seed)
    spray = np.clip(spray, 0.0, 1.0)
    spray *= np.maximum(0, 1.0 - dist_from_base / (max(h, w) / 1.5))

    # Core brightness along arch
    core = np.exp(-((dist_from_base - arch_radius) / (max(h, w) / 40.0)) ** 2)

    cell = np.clip(arch * field_containment * 0.7 + spray * 0.3 + core * 0.5, 0.0, 1.0)
    tiled = _tile_to_shape(cell, shape)
    # Background plasma fill for coverage
    bg_fill = multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 700) * 0.18 + 0.10
    tiled = np.clip(np.maximum(tiled, bg_fill), 0, 1)
    return {"pattern_val": tiled, "R_range": 55.0, "M_range": 40.0, "CC": None}

def texture_dark_matter_halo(shape, mask, seed, sm):
    """Dark matter halo v2 — cosmic web filaments with gravitational lensing distortion.
    64px cell with sharp filament network and subhalo detail."""
    h, w = 64, 64  # Dense tiling for car scale
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.ogrid[:h, :w]
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2).astype(np.float32)
    theta = np.arctan2(yy - cy, xx - cx).astype(np.float32)

    rng = np.random.RandomState(seed)

    # Dark matter filament web: multiple intersecting sine² ridges
    n_filaments = 6
    filaments = np.zeros((h, w), dtype=np.float32)
    for i in range(n_filaments):
        angle = rng.uniform(0, np.pi)
        phase = rng.uniform(0, 2 * np.pi)
        freq = rng.uniform(0.15, 0.35)
        proj = (yy * np.cos(angle) + xx * np.sin(angle)).astype(np.float32)
        line = np.sin(proj * freq + phase) ** 2
        filaments = np.maximum(filaments, line * rng.uniform(0.5, 1.0))

    # Subhalo nodes: bright knots at filament intersections
    n_nodes = rng.randint(8, 15)
    nodes = np.zeros((h, w), dtype=np.float32)
    for _ in range(n_nodes):
        ny, nx = rng.randint(0, h), rng.randint(0, w)
        nr = rng.uniform(2.0, 5.0)
        nd = np.sqrt(((yy - ny).astype(np.float32)) ** 2 + ((xx - nx).astype(np.float32)) ** 2)
        nodes = np.maximum(nodes, np.clip(1.0 - nd / nr, 0, 1) * rng.uniform(0.6, 1.0))

    # Gravitational lensing: radial distortion ripples
    lens_ripple = np.sin(rr * 0.4 + theta * 2) ** 2 * 0.15

    cell = np.clip(filaments * 0.65 + nodes * 0.85 + lens_ripple, 0.0, 1.0).astype(np.float32)
    return {"pattern_val": _tile_to_shape(cell, shape), "R_range": 70.0, "M_range": 55.0, "CC": None}

def texture_quasar_jet(shape, mask, seed, sm):
    """Quasar jet v2 — tighter cell, stronger beam, proper R/M range."""
    h, w = 80, 80  # Was CELL_MEDIUM=192
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.ogrid[:h, :w]

    rng = np.random.RandomState(seed)

    # Jet angle
    jet_angle = rng.uniform(-0.3, 0.3)

    # Distance to jet axis
    cos_a = np.cos(jet_angle)
    sin_a = np.sin(jet_angle)
    dx = xx - cx
    dy = yy - cy

    dist_to_axis = np.abs(dy * cos_a - dx * sin_a)
    along_jet = dy * sin_a + dx * cos_a

    # Tight collimated beam (Gaussian profile)
    jet_width = max(h, w) / 30.0
    beam = np.exp(-(dist_to_axis / jet_width) ** 2)
    beam *= np.maximum(0, 1.0 - np.abs(along_jet) / (max(h, w) / 2.0))

    # Kelvin-Helmholtz instability knots
    kh_pattern = multi_scale_noise((h, w), [8, 16, 32], [0.5, 0.3, 0.2], seed)
    kh_knots = np.sin(along_jet / 20.0 + kh_pattern * np.pi) * 0.5 + 0.5
    kh_knots *= beam * 0.6

    # Cocoon glow (surrounding material)
    cocoon_width = jet_width * 3
    cocoon_dist = dist_to_axis - jet_width
    cocoon = np.exp(-(cocoon_dist / cocoon_width) ** 2) * 0.4
    cocoon *= beam

    cell = np.clip(beam * 1.2 + kh_knots + cocoon, 0.0, 1.0)  # Brighter beam
    tiled = _tile_to_shape(cell, shape)
    # Background cosmic fill for coverage
    bg_fill = multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 700) * 0.18 + 0.10
    tiled = np.clip(np.maximum(tiled, bg_fill), 0, 1)
    return {"pattern_val": tiled, "R_range": 80.0, "M_range": 65.0, "CC": None}

def texture_supernova_remnant(shape, mask, seed, sm):
    """Supernova remnant — small cell, tiled."""
    h, w = CELL_LARGE, CELL_LARGE
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.ogrid[:h, :w]
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    theta = np.arctan2(yy - cy, xx - cx)

    rng = np.random.RandomState(seed)

    # Shock shell at specific radius
    shell_r = max(h, w) / 3.5
    shell_width = max(h, w) / 40.0

    shell = np.exp(-((rr - shell_r) / shell_width) ** 2)

    # Rayleigh-Taylor instability fingers (radial perturbations)
    rt_amplitude = max(h, w) / 25.0
    rt_pattern = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed)
    rt_perturb = np.sin(theta * 8 + rt_pattern * np.pi * 2) * rt_amplitude

    perturbed_shell = np.exp(-((rr - shell_r - rt_perturb) / shell_width) ** 2)

    # Hot interior (swept-up ISM)
    interior = np.exp(-(rr / shell_r) ** 2) * (1.0 - shell)

    # Thin bright shell + finger features
    cell = np.clip(perturbed_shell * 0.9 + shell * 0.5 + interior * 0.3, 0.0, 1.0)
    return {"pattern_val": _tile_to_shape(cell, shape), "R_range": 55.0, "M_range": 40.0, "CC": None}

# ============================================================================
# PAINT FUNCTIONS (12 unique color effects, physics-themed)
# ============================================================================

def paint_pulsar_beacon(paint, shape, mask, seed, pm, bb):
    """Cool blue-white pulse brightening along neutron star beam."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    def fx(result, h, w):
        tex = texture_pulsar_beacon(shape, mask, seed, 0.0)
        e = tex["pattern_val"]
        # Cool blue-white pulse
        result[:, :, 0] = np.clip(result[:, :, 0] + e * 0.4, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] + e * 0.5, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] + e * 0.6, 0, 1)
        return result
    return _apply_paint(paint, mask, pm, bb, fx)

def paint_event_horizon(paint, shape, mask, seed, pm, bb):
    """Dramatic accretion disk: deep void center, hot orange-white photon ring, red spiral arms."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    def fx(result, h, w):
        tex = texture_event_horizon(shape, mask, seed, 0.0)
        e = tex["pattern_val"]
        # Void center is very dark
        cy_cell, cx_cell = CELL_LARGE / 2.0, CELL_LARGE / 2.0
        yy, xx = np.mgrid[:h, :w].astype(np.float32)
        # Approximate void mask from tiled pattern
        void_mask = np.clip(1.0 - e * 2.5, 0, 1)  # dark where pattern is low
        # Hot accretion colors: white-hot ring -> orange -> deep red spiral
        # Photon ring (brightest parts) = white-hot
        hot = np.clip((e - 0.6) * 4.0, 0, 1)  # bright ring regions
        warm = np.clip(e, 0, 1)  # general accretion glow
        result[:, :, 0] = np.clip(result[:, :, 0] * (1.0 - warm * 0.5) + hot * 0.95 + warm * 0.65, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] * (1.0 - warm * 0.6) + hot * 0.85 + warm * 0.25, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] * (1.0 - warm * 0.7) + hot * 0.7 + warm * 0.05, 0, 1)
        # Darken the void center hard
        darkness = np.clip(1.0 - e * 3.0, 0, 0.9)
        result[:, :, 0] = np.clip(result[:, :, 0] * (1.0 - darkness * 0.8), 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] * (1.0 - darkness * 0.85), 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] * (1.0 - darkness * 0.9), 0, 1)
        return result
    return _apply_paint(paint, mask, pm, bb, fx)

def paint_solar_corona(paint, shape, mask, seed, pm, bb):
    """Golden-white corona brightening on dark background."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    def fx(result, h, w):
        tex = texture_solar_corona(shape, mask, seed, 0.0)
        e = tex["pattern_val"]
        # Golden-white corona
        result[:, :, 0] = np.clip(result[:, :, 0] + e * 0.5, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] + e * 0.6, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] + e * 0.2, 0, 1)
        return result
    return _apply_paint(paint, mask, pm, bb, fx)

def paint_nebula_pillars(paint, shape, mask, seed, pm, bb):
    """Blue-green tint shift with dust reddening at pillar edges."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    def fx(result, h, w):
        tex = texture_nebula_pillars(shape, mask, seed, 0.0)
        e = tex["pattern_val"]
        # Blue-green interior + reddening at edges
        result[:, :, 0] = np.clip(result[:, :, 0] + e * 0.25, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] + e * 0.4, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] + e * 0.3, 0, 1)
        return result
    return _apply_paint(paint, mask, pm, bb, fx)

def paint_magnetar_field(paint, shape, mask, seed, pm, bb):
    """Electric violet/cyan field line highlighting."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    def fx(result, h, w):
        tex = texture_magnetar_field(shape, mask, seed, 0.0)
        e = tex["pattern_val"]
        # Violet/cyan field lines
        result[:, :, 0] = np.clip(result[:, :, 0] + e * 0.3, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] + e * 0.5, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] + e * 0.6, 0, 1)
        return result
    return _apply_paint(paint, mask, pm, bb, fx)

def paint_asteroid_belt(paint, shape, mask, seed, pm, bb):
    """Warm gray/brown rocky tint with depth darkening."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    def fx(result, h, w):
        tex = texture_asteroid_belt(shape, mask, seed, 0.0)
        e = tex["pattern_val"]
        # Rocky tint
        result[:, :, 0] = np.clip(result[:, :, 0] * (1.0 - e * 0.3) + e * 0.4, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] * (1.0 - e * 0.3) + e * 0.35, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] * (1.0 - e * 0.3) + e * 0.25, 0, 1)
        return result
    return _apply_paint(paint, mask, pm, bb, fx)

def paint_gravitational_lens(paint, shape, mask, seed, pm, bb):
    """Prismatic color separation at ring edges."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    def fx(result, h, w):
        tex = texture_gravitational_lens(shape, mask, seed, 0.0)
        e = tex["pattern_val"]
        # Prismatic color separation
        result[:, :, 0] = np.clip(result[:, :, 0] + e * 0.4, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] + e * 0.5, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] + e * 0.6, 0, 1)
        return result
    return _apply_paint(paint, mask, pm, bb, fx)

def paint_cosmic_web(paint, shape, mask, seed, pm, bb):
    """Faint blue-white filament glow on deep dark void."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    def fx(result, h, w):
        tex = texture_cosmic_web(shape, mask, seed, 0.0)
        e = tex["pattern_val"]
        # Darken void, brighten filaments
        void_dark = 1.0 - e * 0.5
        result[:, :, 0] = np.clip(result[:, :, 0] * void_dark + e * 0.3, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] * void_dark + e * 0.4, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] * void_dark + e * 0.5, 0, 1)
        return result
    return _apply_paint(paint, mask, pm, bb, fx)

def paint_plasma_ejection(paint, shape, mask, seed, pm, bb):
    """Hot orange-red plasma with white core."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    def fx(result, h, w):
        tex = texture_plasma_ejection(shape, mask, seed, 0.0)
        e = tex["pattern_val"]
        # Orange-red plasma with white core
        result[:, :, 0] = np.clip(result[:, :, 0] + e * 0.6, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] + e * 0.3, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] + e * 0.4, 0, 1)
        return result
    return _apply_paint(paint, mask, pm, bb, fx)

def paint_dark_matter_halo(paint, shape, mask, seed, pm, bb):
    """Subtle purple-blue density glow."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    def fx(result, h, w):
        tex = texture_dark_matter_halo(shape, mask, seed, 0.0)
        e = tex["pattern_val"]
        # Subtle purple-blue density glow
        result[:, :, 0] = np.clip(result[:, :, 0] + e * 0.2, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] + e * 0.1, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] + e * 0.35, 0, 1)
        return result
    return _apply_paint(paint, mask, pm, bb, fx)

def paint_quasar_jet(paint, shape, mask, seed, pm, bb):
    """Intense blue-white beam with orange cocoon."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    def fx(result, h, w):
        tex = texture_quasar_jet(shape, mask, seed, 0.0)
        e = tex["pattern_val"]
        # Blue-white beam + orange cocoon blended
        result[:, :, 0] = np.clip(result[:, :, 0] + e * 0.4, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] + e * 0.4, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] + e * 0.5, 0, 1)
        return result
    return _apply_paint(paint, mask, pm, bb, fx)

def paint_supernova_remnant(paint, shape, mask, seed, pm, bb):
    """Hot pink/red shock front, blue interior."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    def fx(result, h, w):
        tex = texture_supernova_remnant(shape, mask, seed, 0.0)
        e = tex["pattern_val"]
        # Hot pink/red shock front + blue interior
        result[:, :, 0] = np.clip(result[:, :, 0] + e * 0.7, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] + e * 0.2, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] + e * 0.5, 0, 1)
        return result
    return _apply_paint(paint, mask, pm, bb, fx)

# ============================================================================
# PATTERN REGISTRY
# ============================================================================

ASTRO_COSMIC_PATTERNS = {
    "pulsar_beacon": {
        "texture_fn": texture_pulsar_beacon,
        "paint_fn": paint_pulsar_beacon,
        "variable_cc": False,
        "desc": "Rotating neutron star beam with intensity falloff and secondary beam at 180°. Bright core and decaying arms."
    },
    "event_horizon": {
        "texture_fn": texture_event_horizon,
        "paint_fn": paint_event_horizon,
        "variable_cc": False,
        "desc": "Black hole accretion disk with warped elliptical ring and gravitational lensing. Dark void, bright photon ring."
    },
    "solar_corona": {
        "texture_fn": texture_solar_corona,
        "paint_fn": paint_solar_corona,
        "variable_cc": False,
        "desc": "Sun's corona during eclipse. Dark central disk with bright irregular corona tendrils and magnetic field structure."
    },
    "nebula_pillars": {
        "texture_fn": texture_nebula_pillars,
        "paint_fn": paint_nebula_pillars,
        "variable_cc": False,
        "desc": "Pillars of Creation columnar clouds with internal turbulence and photoevaporation glow edges."
    },
    "magnetar_field": {
        "texture_fn": texture_magnetar_field,
        "paint_fn": paint_magnetar_field,
        "variable_cc": False,
        "desc": "Extreme magnetic field dipole with toroidal distortion and 1/r³ intensity falloff."
    },
    "asteroid_belt": {
        "texture_fn": texture_asteroid_belt,
        "paint_fn": paint_asteroid_belt,
        "variable_cc": False,
        "desc": "Dense irregular rock field with scattered elliptical shapes and depth-based size variation with shadows."
    },
    "gravitational_lens": {
        "texture_fn": texture_gravitational_lens,
        "paint_fn": paint_gravitational_lens,
        "variable_cc": False,
        "desc": "Einstein ring effect with concentric distortion rings simulating light bending around massive object."
    },
    "cosmic_web": {
        "texture_fn": texture_cosmic_web,
        "paint_fn": paint_cosmic_web,
        "variable_cc": False,
        "desc": "Large-scale universe structure with filamentary network connecting node clusters across voids."
    },
    "plasma_ejection": {
        "texture_fn": texture_plasma_ejection,
        "paint_fn": paint_plasma_ejection,
        "variable_cc": False,
        "desc": "Coronal mass ejection expanding loop/arch with magnetic field containment lines and particle spray."
    },
    "dark_matter_halo": {
        "texture_fn": texture_dark_matter_halo,
        "paint_fn": paint_dark_matter_halo,
        "variable_cc": False,
        "desc": "Invisible mass distribution with smooth radial density gradient and NFW-profile subhalo clumps."
    },
    "quasar_jet": {
        "texture_fn": texture_quasar_jet,
        "paint_fn": paint_quasar_jet,
        "variable_cc": False,
        "desc": "Relativistic jet from active galactic nucleus with Kelvin-Helmholtz instability knots and cocoon glow."
    },
    "supernova_remnant": {
        "texture_fn": texture_supernova_remnant,
        "paint_fn": paint_supernova_remnant,
        "variable_cc": False,
        "desc": "Expanding shock shell with Rayleigh-Taylor instability fingers, hot interior, and swept-up ISM."
    }
}
