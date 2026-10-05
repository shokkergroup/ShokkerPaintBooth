"""
Paradigm SciFi Paint Function Module for Shokker Paint Booth V5
Implements 16 sci-fi bases with unique mathematical techniques.
Each base has paint_fn (color) and spec_fn (metallic/roughness/clearcoat).

Bases: bioluminescent, dark_matter, holographic_base, neutron_star, plasma_core,
quantum_black, solar_panel, superconductor, singularity, liquid_obsidian, prismatic,
p_phantom, p_volcanic, arctic_ice, carbon_weave, nebula
"""

import numpy as np
from engine.core import _resize_array, multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d

# Clearcoat: 16 = max clearcoat, 17-255 = duller. Never output 0-15 (see SPEC_MAP_REFERENCE.md).
def _cc_clamp(cc_arr):
    return np.clip(cc_arr, 16.0, 255.0).astype(np.float32)


_PS_FIELD_CACHE = {}


def _ps_cache_put(key, value):
    if len(_PS_FIELD_CACHE) > 128:
        _PS_FIELD_CACHE.clear()
    _PS_FIELD_CACHE[key] = value
    return value


def _ps_noise(shape, scales, weights, seed, cap=960):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("noise", int(h), int(w), tuple(scales), tuple(weights), int(seed), int(cap))
    cached = _PS_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    work = min(int(cap), int(h), int(w))
    if work < min(h, w):
        sh = max(8, int(round(h * work / max(h, w))))
        sw = max(8, int(round(w * work / max(h, w))))
        field = multi_scale_noise((sh, sw), scales, weights, seed)
        field = _resize_array(np.asarray(field, dtype=np.float32), h, w)
    else:
        field = multi_scale_noise((h, w), scales, weights, seed)
    return _ps_cache_put(key, np.asarray(field, dtype=np.float32))


def _plasma_core_fields(shape, seed):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("plasma_core", int(h), int(w), int(seed))
    cached = _PS_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    work = min(1024, int(h), int(w))
    sh, sw = h, w
    if work < min(h, w):
        sh = max(256, int(round(h * work / max(h, w))))
        sw = max(256, int(round(w * work / max(h, w))))
    y, x = get_mgrid((sh, sw))
    cy, cx = sh / 2.0, sw / 2.0
    dy, dx = y - cy, x - cx
    r = np.sqrt(dy ** 2 + dx ** 2) + 1e-8
    theta = np.arctan2(dy, dx)
    r_norm = r / np.sqrt(cy ** 2 + cx ** 2)
    core = np.exp(-(r_norm / 0.15) ** 2).astype(np.float32)
    rng = np.random.RandomState(seed + 2007)
    arc_base = np.zeros((sh, sw), dtype=np.float32)
    for i in range(8):
        arc_angle = rng.uniform(0, 2 * np.pi)
        arc_width = rng.uniform(0.08, 0.15)
        wiggle = multi_scale_noise((sh, sw), [16, 32], [0.6, 0.4], seed + 2007 + i * 10)
        angular_dist = np.abs(np.sin((theta - arc_angle + wiggle * 0.3) * 0.5))
        arc_base += np.exp(-(angular_dist / arc_width) ** 2) * np.exp(-r_norm * 1.2)
    arc_base = np.clip(arc_base, 0, 1).astype(np.float32)
    turb = multi_scale_noise((sh, sw), [16, 32, 64], [0.3, 0.4, 0.3], seed + 2008)
    glow = np.clip((turb * 0.5 + 0.5) * np.exp(-r_norm * 0.8), 0, 1).astype(np.float32)
    ring1 = (np.exp(-((r_norm - 0.35) / 0.04) ** 2) * 0.5).astype(np.float32)
    ring2 = (np.exp(-((r_norm - 0.6) / 0.05) ** 2) * 0.3).astype(np.float32)
    filament_noise = multi_scale_noise((sh, sw), [2, 4, 8], [0.44, 0.34, 0.22], seed + 2011)
    filament = (
        np.power(np.clip(1.0 - np.abs(np.sin(theta * 9.0 + r_norm * 38.0 + filament_noise * 4.0)), 0, 1), 8)
        * np.exp(-r_norm * 0.65)
    ).astype(np.float32)
    spark = (np.clip((filament_noise - 0.34) * 2.2, 0, 1) * (0.35 + arc_base * 0.65)).astype(np.float32)
    arc_noise = multi_scale_noise((sh, sw), [1, 2], [0.6, 0.4], seed + 2010)
    arc_spots = np.clip((arc_noise - 0.5) * 3.0, 0, 1).astype(np.float32)
    fields = (core, arc_base, glow, ring1, ring2, filament, spark, turb.astype(np.float32), arc_spots)
    if (sh, sw) != (h, w):
        fields = tuple(_resize_array(field, h, w).astype(np.float32) for field in fields)
    return _ps_cache_put(key, fields)


# ============================================================================
# BIOLUMINESCENT: ATP-driven luciferin emission with organic wave patterns
# ============================================================================

def paint_bioluminescent_v2(paint, shape, mask, seed, pm, bb):
    """
    Bioluminescence simulated via interference of standing waves with 
    exponential decay regions. Creates pulsing organic glow patterns.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    work = min(640, h, w)
    sh, sw = h, w
    if work < min(h, w):
        sh = max(128, int(round(h * work / max(h, w))))
        sw = max(128, int(round(w * work / max(h, w))))
    y, x = get_mgrid((sh, sw))
    
    # Standing wave interference
    wave1 = np.sin(x * 0.08 + y * 0.06) * np.cos(y * 0.05)
    wave2 = np.sin(x * 0.04) * np.cos(x * 0.07 + y * 0.03)
    interference = wave1 * wave2
    
    # Exponential decay from center
    cy, cx = sh / 2.0, sw / 2.0
    dist = np.sqrt((y - cy) ** 2 + (x - cx) ** 2)
    decay = np.exp(-dist / (sh * 0.3))
    
    # Multi-scale turbulence for organic variation
    turb = multi_scale_noise((sh, sw), [16, 32, 64], [0.5, 0.3, 0.2], seed + 2000)
    
    # Combine: interference modulated by decay and turbulence
    base_glow = (np.abs(interference) * decay * (0.5 + turb * 0.5)).astype(np.float32)
    if (sh, sw) != (h, w):
        base_glow = _resize_array(base_glow, h, w).astype(np.float32)
    
    # Color mapping: cyan-green to blue bioluminescence
    result = paint.copy()
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - mask[:, :] * pm * 0.6) + 
                               base_glow * mask[:, :] * pm * 0.8, 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - mask[:, :] * pm * 0.4) + 
                               base_glow * mask[:, :] * pm, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - mask[:, :] * pm * 0.3) + 
                               base_glow * mask[:, :] * pm * 0.6, 0, 1)
    
    return result.astype(np.float32)


def spec_bioluminescent(shape, seed, sm, base_m, base_r):
    """
    Bioluminescence spec: very high metallic (living light), very low roughness
    with peak regions, high clearcoat for organic gel-like surface.
    """
    h, w = shape
    turb = _ps_noise((h, w), [1, 2, 4], [0.6, 0.3, 0.1], seed + 2001, cap=768)
    
    M = np.clip(217.0 + turb * 38.0 * sm, 0, 255)
    R = np.clip(3.0 + turb * 8.0 * sm, 15, 255)
    CC = np.clip(16.0 + turb * 10.0, 16, 255)
    
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ============================================================================
# DARK_MATTER: Gravitational lensing distortion field
# ============================================================================

def paint_dark_matter_v2(paint, shape, mask, seed, pm, bb):
    """
    Dark matter via radial distortion field simulating gravity lensing.
    Creates inward-pulling vortex patterns with event horizon falloff.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    
    cy, cx = h / 2.0, w / 2.0
    dy, dx = y - cy, x - cx
    r = np.sqrt(dy ** 2 + dx ** 2) + 1e-8
    
    # Schwarzschild-like distortion: r_s / r falloff
    distortion = 1.0 / (1.0 + r / (h * 0.25))
    
    # Tangential swirl
    theta = np.arctan2(dy, dx)
    swirl = np.sin(theta * 3 + distortion * 2 * np.pi)
    
    # Multi-scale perturbation
    pert = _ps_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 2002, cap=768)
    
    # Combine: swirl modulated by inverse-square falloff
    dark_pattern = np.abs(swirl) * (1.0 - distortion) * (0.3 + pert * 0.7)
    
    result = paint.copy()
    blend = mask[:, :] * pm * 0.7
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + 
                               dark_pattern * blend * 0.3, 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + 
                               dark_pattern * blend * 0.2, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + 
                               dark_pattern * blend * 0.4, 0, 1)
    
    return result.astype(np.float32)


def spec_dark_matter(shape, seed, sm, base_m, base_r):
    """Dark matter: extreme absorption with gravitational lensing distortion zones."""
    h, w = shape
    absorp = _ps_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 2003, cap=768)
    lens = _ps_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 2010, cap=768)
    # Gravitational lensing zones — bright ring-like structures
    ring = np.clip(1.0 - np.abs(lens - 0.5) * 3.0, 0, 1)
    # M: mostly absorptive void, metallic at lensing boundaries
    M = np.clip(10.0 + absorp * 60.0 + ring * 140.0, 0, 255).astype(np.float32)
    # R: very rough scattering, smoother at lens focus points
    R = np.clip(130.0 + absorp * 80.0 - ring * 90.0, 15, 255).astype(np.float32)
    # CC: heavy degradation, slight clarity at lens focus (min 16, never 0)
    CC = np.clip(80.0 + absorp * 80.0 - ring * 50.0, 16, 255).astype(np.float32)
    return M, R, _cc_clamp(CC)


# ============================================================================
# HOLOGRAPHIC_BASE: Rainbow diffraction hologram pattern
# ============================================================================

def paint_holographic_base_v2(paint, shape, mask, seed, pm, bb):
    """
    Holographic effect via modulated diffraction gratings.
    Creates iridescent rainbow shifts using phase-space lattice interference.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    
    # Primary grating (vertical lines with slight curve)
    grating1 = np.sin(x * 0.12 + y * 0.02)
    
    # Secondary grating (diagonal)
    grating2 = np.sin((x + y) * 0.08 - y * 0.04)
    
    # Tertiary grating (radial)
    cy, cx = h / 2.0, w / 2.0
    r = np.sqrt((y - cy) ** 2 + (x - cx) ** 2)
    grating3 = np.sin(r * 0.1)
    
    # Combine with phase shift
    combined = (grating1 * 0.4 + grating2 * 0.4 + grating3 * 0.2)
    
    # Spectral decomposition (simulate RGB diffraction)
    phase_shift = combined * np.pi
    r_chan = np.abs(np.sin(phase_shift + 0.0))
    g_chan = np.abs(np.sin(phase_shift + 2.094))
    b_chan = np.abs(np.sin(phase_shift + 4.189))
    
    result = paint.copy()
    blend = mask[:, :] * pm * 0.8
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + r_chan * blend, 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + g_chan * blend, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + b_chan * blend, 0, 1)
    
    return result.astype(np.float32)


def spec_holographic_base(shape, seed, sm, base_m, base_r):
    """
    Holographic spec: high metallic (reflective surface),
    low roughness (sharp diffraction), extreme clearcoat (rainbow shift).
    """
    h, w = shape
    grain = _ps_noise((h, w), [1, 2, 4, 8], [0.3, 0.25, 0.25, 0.2], seed + 2004, cap=768)
    
    M = np.clip(191.0 + grain * 51.0 * sm, 0, 255)
    R = np.clip(3.0 + grain * 12.0 * sm, 15, 255)
    CC = np.clip(16.0 + (1.0 - grain) * 8.0, 16, 255)
    
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ============================================================================
# NEUTRON_STAR: Degenerate matter extreme density compression
# ============================================================================

def paint_neutron_star_v2(paint, shape, mask, seed, pm, bb):
    """
    Neutron star surface via Voronoi-like compression cells with
    intense pressure ridges and quantum shell structure.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    
    # Simulate cellular compression via periodic shock waves
    shock1 = np.cos(x * 0.15) * np.sin(y * 0.12)
    shock2 = np.cos(y * 0.18) * np.sin(x * 0.1)
    
    # High-frequency lattice (quantum shell structure)
    lattice = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 2005)
    
    # Pressure ridges: take local maxima
    ridges = np.maximum(np.abs(shock1), np.abs(shock2))
    ridges = np.power(np.clip(ridges, 0, None), 0.4)  # Compress range
    
    # Combine: intense surface with quantum variations
    density_pattern = ridges * (0.6 + lattice * 0.4)
    
    result = paint.copy()
    blend = mask[:, :] * pm * 0.85
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + 
                               density_pattern * blend * 0.5, 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + 
                               density_pattern * blend * 0.4, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + 
                               density_pattern * blend * 0.6, 0, 1)
    
    return result.astype(np.float32)


def spec_neutron_star(shape, seed, sm, base_m, base_r):
    """
    Neutron star spec: extreme metallic (degenerate electron gas reflects all),
    very rough (broken irregular surface), no clearcoat (radiation).
    FLAG-ANGLE-001 FIX: fix scale bug (was mixing 0-1 base offsets with *255 modulation
    producing M≈1-14 instead of ≈242-255); wire base_m/base_r params; fix shape unpack.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    friction = multi_scale_noise((h, w), [16, 32], [0.7, 0.3], seed + 2006)

    # Degenerate electron gas: near-perfect metallic reflection modulated by surface friction
    # base_m is ALREADY 0-255 — do NOT multiply by 255 again
    M = np.clip(base_m * (0.95 + friction * 0.05), 0, 255)
    # Very rough broken neutron star surface — GGX floor 15
    R = np.clip(base_r * (0.70 + friction * 0.30), 15, 255)
    CC = np.full((h, w), 16.0)  # No clearcoat — radiation environment

    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ============================================================================
# PLASMA_CORE: Magnetohydrodynamic plasma containment field
# ============================================================================

def paint_plasma_core_v2(paint, shape, mask, seed, pm, bb):
    """
    Reactor core plasma: intense blue-white center with electric arcs radiating
    outward, surrounded by purple-blue plasma glow and magnetic confinement rings.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    core_intensity, arc_base, glow, ring1, ring2, filament, spark, _turb, _arc_spots = _plasma_core_fields((h, w), seed)

    # Color mapping: core=white-blue, arcs=electric blue, glow=purple-blue
    result = paint.copy()
    blend = mask[:, :] * pm * 0.85
    # Core: intense blue-white
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) +
                               blend * (core_intensity * 0.9 + arc_base * 0.5 + glow * 0.15 + ring1 * 0.3 + ring2 * 0.2 + filament * 0.32 + spark * 0.18), 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) +
                               blend * (core_intensity * 0.85 + arc_base * 0.6 + glow * 0.1 + ring1 * 0.35 + ring2 * 0.25 + filament * 0.42 + spark * 0.24), 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) +
                               blend * (core_intensity * 0.95 + arc_base * 0.9 + glow * 0.45 + ring1 * 0.6 + ring2 * 0.5 + filament * 0.58 + spark * 0.30), 0, 1)

    return result.astype(np.float32)


def spec_plasma_core(shape, seed, sm, base_m, base_r):
    """
    Plasma core spec: glowing core with electric arc metallic highlights,
    smooth in hot zones, rough in turbulent outer plasma.
    """
    h, w = shape
    core, _arc_base, _glow, _ring1, _ring2, filament, _spark, turb, arc_spots = _plasma_core_fields((h, w), seed)

    # M: core is dielectric (glowing), arcs are metallic, plasma is moderate
    M = np.clip(core * 40.0 + (1.0 - core) * 180.0 * sm + arc_spots * 75.0 * sm + filament * 72.0 * sm, 0, 255).astype(np.float32)
    # R: core is very smooth (hot), outer is turbulent/rough
    R = np.clip(3.0 + (1.0 - core) * 60.0 * sm + turb * 25.0 * sm - arc_spots * 20.0 - filament * 24.0 * sm, 15, 255).astype(np.float32)
    # CC: core is glossy, outer plasma has more diffusion
    CC = np.clip(16.0 + (1.0 - core) * 40.0 * sm + turb * 15.0 * sm + filament * 38.0 * sm, 16, 255).astype(np.float32)

    return M, R, CC


# ============================================================================
# QUANTUM_BLACK: Quantum tunneling probability wave absorption
# ============================================================================

def paint_quantum_black_v2(paint, shape, mask, seed, pm, bb):
    """
    Quantum black via Schrödinger probability wave interference.
    Creates interference fringe patterns with quantum tunneling dropout regions.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    
    # Plane wave 1
    wave1 = np.exp(1j * (x * 0.1 + y * 0.05))
    
    # Plane wave 2 (slightly different angle)
    wave2 = np.exp(1j * (x * 0.08 + y * 0.07))
    
    # Interference pattern (probability density)
    interference = np.abs(wave1 + wave2) ** 2
    
    # Tunneling dropout zones: where both waves interfere destructively
    tunnel = np.abs(wave1 - wave2) ** 2
    tunnel = 1.0 / (1.0 + tunnel * 2.0)  # Inverted for dropout
    
    # Multi-scale quantum fluctuations
    quantum = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 2009)
    micro = multi_scale_noise((h, w), [1, 2, 3], [0.48, 0.34, 0.18], seed + 2012)
    fringe = np.power(np.clip(1.0 - np.abs(np.sin(x * 0.47 - y * 0.31 + micro * 3.5)), 0, 1), 10)
    
    # Combine: interference modulated by tunneling and quantum noise
    pattern = np.clip(interference * tunnel * (0.7 + quantum * 0.3), 0, 1)
    probability_spark = np.clip((micro - 0.04) * 2.4, 0, 1) * 0.58 + fringe * 0.62
    
    result = paint.copy()
    blend = mask[:, :] * pm * 0.9
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + 
                               pattern * blend * 0.040 + probability_spark * blend * 0.145, 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + 
                               pattern * blend * 0.032 + probability_spark * blend * 0.120, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + 
                               pattern * blend * 0.060 + probability_spark * blend * 0.210, 0, 1)
    
    return result.astype(np.float32)


def spec_quantum_black(shape, seed, sm, base_m, base_r):
    """
    Quantum black spec: near-zero metallic (absorbs all),
    high roughness (quantum noise), zero clearcoat (event absorption).
    """
    h, w = shape
    fluct = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 2010)
    micro = multi_scale_noise((h, w), [1, 2, 3], [0.48, 0.34, 0.18], seed + 2012)
    micro01 = np.clip((micro + 1.0) * 0.5, 0, 1)
    
    M = np.clip(5.0 + fluct * 8.0 * sm + micro01 * 34.0 * sm, 0, 255)
    R = np.clip(184.0 + fluct * 38.0 * sm + (1.0 - micro01) * 58.0 * sm, 15, 255)
    CC = np.clip(206.0 + micro01 * 44.0 * sm, 16, 255)

    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ============================================================================
# SOLAR_PANEL: Photovoltaic cell grid with silicon wafer pattern
# ============================================================================

def paint_solar_panel_v2(paint, shape, mask, seed, pm, bb):
    """
    Solar panel via regular grid of photovoltaic cells with
    silicon wafer interference colors and micro-etching.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Grid pattern: photovoltaic cells
    cell_size = 16
    grid_y = (np.arange(h) % cell_size) / float(cell_size)
    grid_x = (np.arange(w) % cell_size) / float(cell_size)
    grid_y, grid_x = np.meshgrid(grid_y, grid_x, indexing='ij')
    
    # Cell boundaries are darker (metal contacts)
    cell_boundary = np.minimum(grid_y, grid_x) * np.minimum(1 - grid_y, 1 - grid_x)
    cell_boundary = 1.0 - cell_boundary * 0.5
    
    # Silicon wafer pattern: fine linear scratches
    scratch = multi_scale_noise((h, w), [32, 64], [0.7, 0.3], seed + 2011)
    scratch = 1.0 - np.abs(scratch) * 0.3
    
    # Iridescence from thin film interference (SiO2 layer)
    interference = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 2012)
    
    # Combine: grid × wafer × interference
    panel = cell_boundary * scratch * (0.85 + interference * 0.15)
    
    result = paint.copy()
    blend = mask[:, :] * pm * 0.7
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + 
                               panel * blend * 0.3, 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + 
                               panel * blend * 0.35, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + 
                               panel * blend * 0.4, 0, 1)
    
    return result.astype(np.float32)


def spec_solar_panel(shape, seed, sm, base_m, base_r):
    """
    Solar panel spec: medium metallic (conductor + glass),
    low roughness (glass coating), high clearcoat (protective glass).
    """
    h, w = shape
    texture = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.3, 0.3], seed + 2013)
    
    M = np.clip(115.0 + texture * 38.0 * sm, 0, 255)
    R = np.clip(5.0 + texture * 20.0 * sm, 15, 255)
    CC = np.clip(16.0 + texture * 8.0, 16, 255)
    
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ============================================================================
# SUPERCONDUCTOR: Meissner effect magnetic flux expulsion
# ============================================================================

def paint_superconductor_v2(paint, shape, mask, seed, pm, bb):
    """
    Superconductor via magnetic flux lines being expelled (Meissner effect).
    Creates concentric repulsion patterns with field line discontinuities.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    
    cy, cx = h / 2.0, w / 2.0
    dy, dx = y - cy, x - cx
    r = np.sqrt(dy ** 2 + dx ** 2) + 1e-8
    theta = np.arctan2(dy, dx)
    
    # Radial field lines that get expelled (sharp cutoff at critical T)
    field_lines = np.sin(theta * 8 + r * 0.05)
    
    # Meissner transition: sharp boundary where flux is expelled
    critical_radius = h * 0.25
    expulsion = np.heaviside(critical_radius - r, 0.5)
    
    # Cooper pair coherence: long-range order
    coherence = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed + 2014)
    
    # Pattern: field lines × expulsion boundary × coherence
    pattern = np.abs(field_lines) * (1.0 - expulsion * 0.7) * (0.5 + coherence * 0.5)
    
    result = paint.copy()
    blend = mask[:, :] * pm * 0.75
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + 
                               pattern * blend * 0.4, 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + 
                               pattern * blend * 0.3, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + 
                               pattern * blend * 0.5, 0, 1)
    
    return result.astype(np.float32)


def spec_superconductor(shape, seed, sm, base_m, base_r):
    """
    Superconductor spec: perfect metallic (zero resistance),
    very low roughness (perfect crystal lattice), medium clearcoat.
    """
    h, w = shape
    lattice = multi_scale_noise((h, w), [32, 64], [0.7, 0.3], seed + 2015)
    
    M = np.clip(230.0 + lattice * 25.0 * sm, 0, 255)
    R = np.clip(3.0 + lattice * 10.0 * sm, 15, 255)
    CC = np.clip(16.0 + lattice * 15.0, 16, 255)
    
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ============================================================================
# SINGULARITY: Event horizon gravitational redshift gradient
# ============================================================================

def paint_singularity_v2(paint, shape, mask, seed, pm, bb):
    """
    Singularity via redshift gradient approaching event horizon.
    Colors shift from blue (far field) to red (at horizon) via relativistic Doppler.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    
    cy, cx = h / 2.0, w / 2.0
    dy, dx = y - cy, x - cx
    r = np.sqrt(dy ** 2 + dx ** 2) + 1e-8
    
    # Schwarzschild radius falloff
    r_s = h * 0.1
    redshift = np.sqrt(np.maximum(1.0 - r_s / r, 0.0))
    
    # Accretion disk spiral (centrifugal)
    theta = np.arctan2(dy, dx)
    spiral = np.sin(theta * 5 - r * 0.08)
    
    # Gravitational lensing blur (higher near horizon)
    blur = 1.0 / (1.0 + r / r_s)
    blur_noise = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 2016)
    
    # Redshift effect: shift colors toward red as r decreases
    pattern = np.abs(spiral) * redshift * (0.5 + blur_noise * 0.5)
    
    result = paint.copy()
    blend = mask[:, :] * pm * 0.8
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + 
                               pattern * blend, 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + 
                               pattern * blend * redshift, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + 
                               pattern * blend * redshift ** 2, 0, 1)
    
    return result.astype(np.float32)


def spec_singularity(shape, seed, sm, base_m, base_r):
    """
    Singularity spec: near-black metallic (captures all light),
    extreme roughness (torn spacetime), zero clearcoat.
    """
    h, w = shape
    chaos = multi_scale_noise((h, w), [1, 2, 4, 8], [0.3, 0.3, 0.2, 0.2], seed + 2017)
    
    M = np.clip(8.0 + chaos * 15.0 * sm, 0, 255)
    R = np.clip(217.0 + chaos * 38.0 * sm, 15, 255)
    CC = np.full((h, w), 220.0)  # CC=220 dead flat singularity

    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ============================================================================
# LIQUID_OBSIDIAN: Volcanic glass conchoidal fracture pattern
# ============================================================================

def paint_liquid_obsidian_v2(paint, shape, mask, seed, pm, bb):
    """
    Liquid obsidian via conchoidal fracture propagation and glass flow.
    Creates wave-like fracture rings with flow lines underneath.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    
    cy, cx = h / 2.0, w / 2.0
    dy, dx = y - cy, x - cx
    r = np.sqrt(dy ** 2 + dx ** 2) + 1e-8
    theta = np.arctan2(dy, dx)
    
    # Conchoidal wave rings (fracture propagation)
    conchoidal = np.sin(r * 0.08) * np.cos(theta * 3)
    
    # Flow lines underneath (cooling wrinkles)
    flow1 = np.sin(x * 0.05 + y * 0.03)
    flow2 = np.cos(y * 0.06 - x * 0.02)
    flow = flow1 * flow2
    
    # Volcanic glass internal structure (Poisson structure)
    structure = multi_scale_noise((h, w), [16, 32, 64], [0.5, 0.3, 0.2], seed + 2018)
    
    # Combine: conchoidal rings + flow + structure
    pattern = np.abs(conchoidal) * (0.6 + flow * 0.3) * (0.8 + structure * 0.2)
    
    result = paint.copy()
    blend = mask[:, :] * pm * 0.8
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + 
                               pattern * blend * 0.15, 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + 
                               pattern * blend * 0.1, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + 
                               pattern * blend * 0.2, 0, 1)
    
    return result.astype(np.float32)


def spec_liquid_obsidian(shape, seed, sm, base_m, base_r):
    """
    Liquid obsidian spec: high metallic (glassy reflection),
    low roughness (smooth glass), very high clearcoat (glass shine).
    """
    h, w = shape
    sheen = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed + 2019)
    
    M = np.clip(179.0 + sheen * 51.0 * sm, 0, 255)
    R = np.clip(3.0 + sheen * 15.0 * sm, 15, 255)
    CC = np.clip(16.0 + sheen * 8.0, 16, 255)
    
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ============================================================================
# PRISMATIC: Triangular prism spectral dispersion
# ============================================================================

def paint_prismatic_v2(paint, shape, mask, seed, pm, bb):
    """
    Prismatic effect via triangular prism light refraction.
    Creates spectral bands separated by dispersion angle.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    
    # Triangular prism geometry: three edge orientations
    edge1 = x + y
    edge2 = x - y
    edge3 = -x
    
    # Normalize to [0, 1] range
    e1_norm = np.sin(edge1 * 0.06)
    e2_norm = np.sin(edge2 * 0.06)
    e3_norm = np.sin(edge3 * 0.06)
    
    # Dispersion: different wavelengths refract at different angles
    # Red (longer wavelength, less bending)
    red_disperse = np.abs(e1_norm) * 0.9
    
    # Green (middle)
    green_disperse = np.abs(e2_norm)
    
    # Blue (shorter wavelength, more bending)
    blue_disperse = np.abs(e3_norm) * 1.1
    
    # Intensity modulation
    intensity = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed + 2020)
    
    result = paint.copy()
    blend = mask[:, :] * pm * 0.75
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + 
                               red_disperse * blend * (0.7 + intensity * 0.3), 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + 
                               green_disperse * blend * (0.7 + intensity * 0.3), 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + 
                               blue_disperse * blend * (0.7 + intensity * 0.3), 0, 1)
    
    return result.astype(np.float32)


def spec_prismatic(shape, seed, sm, base_m, base_r):
    """
    Prismatic spec: high metallic (crystal/glass),
    very low roughness (polished prism faces), extreme clearcoat.
    """
    h, w = shape
    clarity = multi_scale_noise((h, w), [32, 64], [0.7, 0.3], seed + 2021)
    
    M = np.clip(204.0 + clarity * 38.0 * sm, 0, 255)
    R = np.clip(3.0 + clarity * 12.0 * sm, 15, 255)
    CC = np.clip(16.0 + (1.0 - clarity) * 6.0, 16, 255)
    
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ============================================================================
# P_PHANTOM: Phase-shifting ghost transparency
# ============================================================================

def paint_p_phantom_v2(paint, shape, mask, seed, pm, bb):
    """
    Phantom effect via phase-shifting transparency waves.
    Creates ghostly partially-visible regions with phase coherence patterns.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    
    cy, cx = h / 2.0, w / 2.0
    dy, dx = y - cy, x - cx
    r = np.sqrt(dy ** 2 + dx ** 2) + 1e-8
    theta = np.arctan2(dy, dx)
    
    # Phase waves: circular and spiral
    phase_circular = np.sin(r * 0.06)
    phase_spiral = np.sin(theta * 4 + r * 0.04)
    
    # Coherence field (decreases away from center)
    coherence = np.exp(-r / (h * 0.4))
    
    # Phase shift: how "ghostly" the region is
    phase_shift = phase_circular * phase_spiral * coherence
    phase_shift = (phase_shift + 1.0) * 0.5  # Normalize to [0, 1]
    
    # Multi-scale interference for detail
    detail = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.3, 0.3], seed + 2022)
    
    # Combine: phase shift + detail
    transparency = phase_shift * (0.7 + detail * 0.3)
    
    result = paint.copy()
    blend = mask[:, :] * pm * transparency * 0.6
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + 
                               paint[:, :, 0] * blend * 0.5, 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + 
                               paint[:, :, 1] * blend * 0.6, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + 
                               paint[:, :, 2] * blend * 0.7, 0, 1)
    
    return result.astype(np.float32)


def spec_p_phantom(shape, seed, sm, base_m, base_r):
    """Phantom: ghostly translucent sheen with ethereal wisps and cold zones."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # Ghostly wisps — slow drifting fog-like structures
    fog = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 4000)
    fine = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 4005)
    wisp = np.clip((fog - 0.3) * 2.0, 0, 1)  # fog tendrils
    # M: mostly dielectric but ghostly shimmer in wisp zones
    M = np.clip(wisp * 140.0 + fine * 20.0, 0, 255).astype(np.float32)
    # R: smooth in clear areas, diffuse in fog
    R = np.clip(20.0 + (1.0 - wisp) * 120.0 + fine * 30.0, 15, 255).astype(np.float32)
    # CC: glossy sheen in wisp zones, frosted in void
    CC = np.where(wisp > 0.4, 16.0 + (1.0 - wisp) * 40.0, 60.0 + fog * 60.0).astype(np.float32)
    return M, R, _cc_clamp(CC)


# ============================================================================
# P_VOLCANIC: Fine lava filament network
# ============================================================================

def _norm01(v):
    v = np.asarray(v, dtype=np.float32)
    lo = float(np.min(v))
    hi = float(np.max(v))
    if hi - lo < 1e-6:
        return np.zeros_like(v, dtype=np.float32)
    return np.clip((v - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def _periodic_ridge(coord, period, width):
    phase = np.mod(coord / max(period, 1e-6) + 0.5, 1.0) - 0.5
    dist = np.abs(phase) * period
    return np.clip(1.0 - dist / max(width, 1e-6), 0.0, 1.0).astype(np.float32)


def _volcanic_filament_field(shape, seed):
    """Returns fine molten fissures, glow halos, rock grain, and ember dust."""
    oh, ow = shape[:2] if len(shape) > 2 else shape
    key = ("volcanic_filament", int(oh), int(ow), int(seed))
    cached = _PS_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    work = min(768, int(oh), int(ow))
    h, w = int(oh), int(ow)
    if work < min(oh, ow):
        h = max(256, int(round(oh * work / max(oh, ow))))
        w = max(256, int(round(ow * work / max(oh, ow))))
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    size_scale = max(0.5, min(h, w) / 512.0)
    px2048 = max(0.75, min(h, w) / 2048.0)

    drift_a = (_norm01(multi_scale_noise((h, w), [32, 64, 128], [0.40, 0.35, 0.25], seed + 6101)) - 0.5)
    drift_b = (_norm01(multi_scale_noise((h, w), [24, 48, 96], [0.45, 0.35, 0.20], seed + 6102)) - 0.5)
    micro = _norm01(multi_scale_noise((h, w), [4, 8, 16, 32], [0.40, 0.30, 0.20, 0.10], seed + 6103))

    core = np.zeros((h, w), dtype=np.float32)
    glow = np.zeros((h, w), dtype=np.float32)
    angles = (-0.92, -0.43, 0.18, 0.73, 1.21, 1.84)
    periods = (29.0, 37.0, 53.0, 71.0, 89.0, 113.0)
    weights = (0.92, 0.75, 0.68, 0.58, 0.48, 0.38)
    for i, (angle, period, weight) in enumerate(zip(angles, periods, weights)):
        c = np.cos(angle)
        s = np.sin(angle)
        coord = (
            xf * c + yf * s
            + drift_a * (18.0 + i * 4.0) * size_scale
            + np.sin((xf * -s + yf * c) / max(11.0 * size_scale, 1.0) + i) * 2.2 * size_scale
        )
        ridge = _periodic_ridge(coord, period * size_scale, 0.95 * px2048)
        halo = _periodic_ridge(coord, period * size_scale, 4.2 * px2048)
        gate = np.clip(0.35 + drift_b * 1.1 + micro * 0.7, 0.0, 1.0)
        core = np.maximum(core, (ridge ** 2.8) * gate * weight)
        glow = np.maximum(glow, (halo ** 1.35) * gate * weight)

    branch_coord = xf * 0.77 - yf * 0.64 + drift_b * 24.0 * size_scale
    branch = _periodic_ridge(branch_coord, 17.0 * size_scale, 0.72 * px2048)
    branch_gate = np.clip(glow * 1.35 + micro * 0.45 - 0.28, 0.0, 1.0)
    core = np.maximum(core, (branch ** 3.0) * branch_gate * 0.85)
    glow = np.maximum(glow, (branch ** 1.25) * branch_gate * 0.55)

    ember_noise = _norm01(multi_scale_noise((h, w), [3, 6, 12], [0.55, 0.30, 0.15], seed + 6104))
    embers = np.clip((ember_noise - 0.76) * 5.2, 0.0, 1.0) * np.clip(glow + 0.15, 0.0, 1.0)
    rock_grain = _norm01(multi_scale_noise((h, w), [5, 11, 23, 47], [0.35, 0.30, 0.22, 0.13], seed + 6105))
    core = np.clip(core + embers * 0.28, 0.0, 1.0).astype(np.float32)
    glow = np.clip(np.maximum(glow, core * 0.85), 0.0, 1.0).astype(np.float32)
    fields = (core, glow, rock_grain.astype(np.float32), embers.astype(np.float32))
    if (h, w) != (oh, ow):
        fields = tuple(_resize_array(field, oh, ow).astype(np.float32) for field in fields)
    # SPB perf loop 2026-05-31; owner hard ceiling: no base over 4s. Reuse the same field for paint+spec.
    return _ps_cache_put(key, fields)

def paint_p_volcanic_v2(paint, shape, mask, seed, pm, bb):
    """
    Volcanic lava as hairline fissures, ember dust, and hot subsurface glow.
    Avoids broad convection blobs so it reads with detail on 2048 canvases.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    core, glow, grain, embers = _volcanic_filament_field((h, w), seed)

    basalt = np.empty((h, w, 3), dtype=np.float32)
    basalt[:, :, 0] = 0.030 + grain * 0.065 + glow * 0.050
    basalt[:, :, 1] = 0.024 + grain * 0.038 + glow * 0.018
    basalt[:, :, 2] = 0.020 + grain * 0.030

    molten = np.empty((h, w, 3), dtype=np.float32)
    molten[:, :, 0] = 0.34 + glow * 0.44 + core * 0.30 + embers * 0.16
    molten[:, :, 1] = 0.060 + glow * 0.20 + core * 0.52 + embers * 0.18
    molten[:, :, 2] = 0.012 + core * 0.080
    heat = np.clip(glow[:, :, np.newaxis] * 0.78 + core[:, :, np.newaxis] * 0.95, 0.0, 1.0)
    lava = np.clip(basalt + molten * heat, 0.0, 1.0)

    blend = np.clip(mask[:, :] * pm * 0.88, 0, 1)[:, :, np.newaxis]
    result = np.clip(paint * (1.0 - blend) + lava * blend, 0.0, 1.0)
    return result.astype(np.float32)


def spec_p_volcanic(shape, seed, sm, base_m, base_r):
    """Volcanic: molten hairline cores are glossy/metallic; basalt is rough and dead."""
    h, w = shape[:2] if len(shape) > 2 else shape
    core, glow, grain, embers = _volcanic_filament_field((h, w), seed)
    strength = np.clip(sm, 0.25, 2.0)
    hot = np.clip(core * strength + embers * 0.38, 0.0, 1.0)
    warm = np.clip(glow * strength, 0.0, 1.0)
    M = np.clip(float(base_m) * 0.08 + 24.0 + warm * 82.0 + hot * 170.0 + embers * 42.0, 0, 255).astype(np.float32)
    R = np.clip(float(base_r) * 0.10 + 214.0 - warm * 74.0 - hot * 168.0 + grain * 28.0, 15, 255).astype(np.float32)
    CC = np.clip(176.0 - warm * 82.0 - hot * 138.0 + grain * 18.0, 16, 235).astype(np.float32)
    return M, R, _cc_clamp(CC)


# ============================================================================
# ARCTIC_ICE: Frozen crystalline surface, cold blue-white, subtle structure
# ============================================================================

def paint_arctic_ice_v2(paint, shape, mask, seed, pm, bb):
    """Arctic ice: cold blue-white, subtle crystalline variation, no heavy pattern."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    gray = base.mean(axis=2)
    # Cold blue-white ice tint
    ice_r = np.clip(gray * 0.65 + 0.12, 0, 1)
    ice_g = np.clip(gray * 0.78 + 0.18, 0, 1)
    ice_b = np.clip(gray * 0.92 + 0.22, 0, 1)
    ice = np.stack([ice_r, ice_g, ice_b], axis=-1)
    # Very subtle variation (barely visible crackle)
    var = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 2026)
    ice = np.clip(ice * (0.97 + var[:,:,np.newaxis] * 0.06), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + ice * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_arctic_ice(shape, seed, sm, base_m, base_r):
    """Arctic ice: frozen surface with cracks, bubbles, and frost variation."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # Ice crack network
    crack_noise = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 4100)
    cracks = np.clip(1.0 - np.abs(crack_noise - 0.5) * 4.0, 0, 1)  # thin crack lines
    # Frozen bubble clusters
    bubbles = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 4105)
    bubble_spots = np.clip((bubbles - 0.6) * 4.0, 0, 1)
    # Frost variation (large smooth zones)
    frost = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 4110)
    # M: mostly dielectric ice, slight metallic in deep cracks (mineral deposits)
    M = np.clip(cracks * 130.0 + bubble_spots * 30.0, 0, 255).astype(np.float32)
    # R: very smooth ice surface, rougher in frost patches and crack edges
    R = np.clip(5.0 + frost * 100.0 + cracks * 50.0 + bubble_spots * 20.0, 15, 255).astype(np.float32)
    # CC: high clarity ice, frosted in patches
    CC = np.clip(16.0 + frost * 80.0 + cracks * 20.0, 16, 255).astype(np.float32)
    return M, R, _cc_clamp(CC)


# ============================================================================
# CARBON_WEAVE: Twill weave interference pattern (2x2 twill)
# ============================================================================

def paint_carbon_weave_v2(paint, shape, mask, seed, pm, bb):
    """
    Carbon weave via 2x2 twill interference pattern.
    Creates diagonal interlocking fiber pattern with depth from angle variation.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    
    weave_period = 8
    weave_y = (np.arange(h) % (weave_period * 2)) / float(weave_period)
    weave_x = (np.arange(w) % (weave_period * 2)) / float(weave_period)
    weave_y, weave_x = np.meshgrid(weave_y, weave_x, indexing='ij')
    
    # 2x2 twill: alternating pattern
    # Every 2x2 block has fiber going over in one direction, under in another
    twill_pattern = np.zeros((h, w))
    for i in range(0, h, weave_period * 2):
        for j in range(0, w, weave_period * 2):
            # First 2x2 block
            if i + weave_period < h and j + weave_period < w:
                twill_pattern[i:i+weave_period, j:j+weave_period] = 1.0
                twill_pattern[i+weave_period:i+weave_period*2, j+weave_period:j+weave_period*2] = 1.0
    
    # Fiber reflections (angle-dependent)
    fiber_angle1 = np.sin(np.arange(h)[:, np.newaxis] * 0.05) * 0.5 + 0.5
    fiber_angle2 = np.sin(np.arange(w)[np.newaxis, :] * 0.05) * 0.5 + 0.5
    
    # Fine detail texture
    texture = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.3, 0.3], seed + 2028)
    
    # Combine: twill × fiber angle × texture
    weave = twill_pattern * (0.7 + fiber_angle1 * 0.3) * (0.8 + texture * 0.2)
    
    result = paint.copy()
    blend = mask[:, :] * pm * 0.75
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + 
                               weave * blend * 0.3, 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + 
                               weave * blend * 0.25, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + 
                               weave * blend * 0.35, 0, 1)
    
    return result.astype(np.float32)


def spec_carbon_weave(shape, seed, sm, base_m, base_r):
    """Carbon weave: spec driven by same weave as paint. Metallic threads = high M, low R, CC 16; fiber = lower M, higher R."""
    h, w = shape[:2] if len(shape) > 2 else shape
    weave_period = 8
    weave_y = (np.arange(h) % (weave_period * 2)) / float(weave_period)
    weave_x = (np.arange(w) % (weave_period * 2)) / float(weave_period)
    weave_y, weave_x = np.meshgrid(weave_y, weave_x, indexing='ij')
    hex_offset = (np.arange(h) // (weave_period * 2)) % 2
    offset_x = hex_offset[:, np.newaxis] * 0.5
    hex_x_offset = weave_x + offset_x
    cell_dist = np.minimum(
        np.minimum(weave_y, hex_x_offset),
        np.minimum(1.0 - weave_y, 1.0 - hex_x_offset)
    )
    thread = np.clip(1.0 - cell_dist * 1.5, 0, 1)  # 1 = thread highlight, 0 = gap
    M = np.clip((0.45 + thread * 0.50) * 255.0, 0, 255).astype(np.float32)
    R = np.clip((0.25 + (1.0 - thread) * 0.25) * 255.0, 15, 255).astype(np.float32)
    CC = np.where(thread > 0.6, 16.0, 80.0).astype(np.float32)
    return M, R, _cc_clamp(CC)


# ============================================================================
# NEBULA: Interstellar gas cloud emission spectrum
# ============================================================================

def paint_nebula_v2(paint, shape, mask, seed, pm, bb):
    """
    Cosmic nebula with fine metallic sparkle (stellar dust), wisps of colored gas,
    scattered star-like flakes, and deep color variation. Much more sparkle and depth.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))

    cy, cx = h / 2.0, w / 2.0
    dy, dx = y - cy, x - cx
    r = np.sqrt(dy ** 2 + dx ** 2) + 1e-8
    theta = np.arctan2(dy, dx)

    # Multi-scale gas cloud structure (billowing nebula wisps)
    gas1 = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 2030)
    gas2 = multi_scale_noise((h, w), [8, 16, 32], [0.35, 0.35, 0.3], seed + 2031)
    gas = np.clip((gas1 + gas2) * 0.5, 0, 1)

    # Filamentary wisps (magnetic field-guided gas strands)
    filament1 = np.sin(theta * 4 + r * 0.03 + gas1 * 3.0) * 0.5 + 0.5
    filament2 = np.sin(theta * 6 - r * 0.02 + gas2 * 2.5) * 0.5 + 0.5
    wisps = np.clip(filament1 * filament2, 0, 1)

    # Star-like flake sparkle (tiny bright scattered points)
    sparkle_noise = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 2032)
    stars = np.clip((sparkle_noise - 0.82) * 12.0, 0, 1)  # sparse bright points

    # Multi-color nebula palette: H-alpha red, OIII teal, SII violet, gold dust
    color_phase = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 2033)
    # Four-color nebula zones
    t = np.clip(color_phase * 0.5 + 0.5, 0, 1)
    neb_r = np.clip(0.4 * np.sin(t * np.pi * 2.0 + 0.0) ** 2 + wisps * 0.2 + stars * 0.8, 0, 1)
    neb_g = np.clip(0.25 * np.sin(t * np.pi * 2.0 + 2.1) ** 2 + wisps * 0.15 + stars * 0.75, 0, 1)
    neb_b = np.clip(0.5 * np.sin(t * np.pi * 2.0 + 4.2) ** 2 + wisps * 0.3 + stars * 0.9, 0, 1)

    # Depth darkening in dust lanes
    dust = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed + 2034)
    dust_lane = np.clip((dust - 0.55) * 3.0, 0, 1) * 0.4

    result = paint.copy()
    blend = np.clip(mask[:, :] * pm * 0.80, 0, 1)
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + blend * gas * (neb_r - dust_lane * 0.3), 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + blend * gas * (neb_g - dust_lane * 0.2), 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + blend * gas * (neb_b - dust_lane * 0.1), 0, 1)
    return result.astype(np.float32)


def spec_nebula(shape, seed, sm, base_m, base_r):
    """Nebula spec: cosmic dust sparkle, star flakes, gas wisps with depth variation."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # Gas cloud density — large billowing structures
    gas = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 4200)
    # Dust lane structures — darker filaments threading through
    dust = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 4210)
    dust_lane = np.clip((dust - 0.4) * 3.0, 0, 1)
    # Star-birth hot spots — tiny bright metallic points (cosmic dust sparkle)
    stars_coarse = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 4215)
    stars_fine = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 4216)
    hot_spots = np.clip((stars_coarse - 0.80) * 8.0, 0, 1)  # more frequent sparkle
    micro_flake = np.clip((stars_fine - 0.70) * 5.0, 0, 1)  # fine metallic dust
    # M: sparkle and micro-flake metallic, moderate in gas
    M = np.clip(hot_spots * 220.0 + micro_flake * 120.0 * sm + gas * 40.0 * sm, 0, 255).astype(np.float32)
    # R: smooth at star points (reflective), rough in gas, very rough in dust
    R = np.clip(60.0 + (1.0 - gas) * 100.0 * sm - hot_spots * 55.0 - micro_flake * 30.0 + dust_lane * 50.0 * sm, 15, 255).astype(np.float32)
    # CC: clear near stars, foggy in dust lanes
    CC = np.clip(16.0 + dust_lane * 80.0 * sm + (1.0 - gas) * 40.0 * sm - hot_spots * 20.0, 16, 255).astype(np.float32)
    return M, R, _cc_clamp(CC)


# ============================================================================
# PARADIGM 10 (expansion bases): spec functions for p_superfluid ... p_schrodinger
# Used by engine/expansions/paradigm.py PARADIGM_BASES base_spec_fn.
# All CC in 16-255 (see SPEC_MAP_REFERENCE.md).
# ============================================================================

def spec_p_superfluid(shape, seed, sm, base_m, base_r):
    """Superfluid: liquid surface with ripple interference, vortex cores, and surface tension waves."""
    h, w = shape[:2] if len(shape) > 2 else shape
    s = max(sm, 0.05)  # amplitude scale (never fully zero)
    y, x = get_mgrid((h, w))
    # Surface ripple interference pattern
    ripple1 = np.sin(x * 0.12 + y * 0.08) * np.cos(y * 0.06 - x * 0.04)
    ripple2 = np.sin(x * 0.05 - y * 0.09) * np.cos(x * 0.07)
    ripples = np.clip((ripple1 + ripple2) * 0.5 + 0.5, 0, 1)
    # Quantized vortex cores — small intense spots
    vortex_noise = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 4300)
    vortex = np.clip((vortex_noise - 0.8) * 6.0, 0, 1)
    # Surface tension field — smooth large-scale
    tension = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 4305)
    # M: mostly smooth liquid, metallic at vortex cores and ripple peaks
    M = np.clip(ripples * 100.0 * s + vortex * 155.0 * s + tension * 30.0 * s, 0, 255).astype(np.float32)
    # R: ultra-smooth liquid surface, slightly rough at vortex edges
    R = np.clip(5.0 + (1.0 - ripples) * 80.0 * s + vortex * 60.0 * s + tension * 40.0 * s, 15, 255).astype(np.float32)
    # CC: pristine clarity, slight degradation at vortex boundaries
    CC = np.clip(16.0 + (1.0 - ripples) * 50.0 * s + vortex * 40.0 * s, 16, 255).astype(np.float32)
    return M, R, _cc_clamp(CC)


def spec_p_coronal(shape, seed, sm, base_m, base_r):
    """Coronal mass ejection: erupting plasma arcs, magnetic field loops, and solar flare zones."""
    h, w = shape[:2] if len(shape) > 2 else shape
    s = max(sm, 0.05)  # amplitude scale (never fully zero)
    y, x = get_mgrid((h, w))
    # Magnetic field loop arcs (curved structures)
    arc1 = np.sin(y * 0.04 + np.sin(x * 0.03) * 2.5) * 0.5 + 0.5
    arc2 = np.cos(x * 0.05 + np.cos(y * 0.04) * 2.0) * 0.5 + 0.5
    loops = np.clip(arc1 * 0.6 + arc2 * 0.4, 0, 1)
    # Solar flare bursts — high-energy eruption zones
    flare = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 4400)
    eruption = np.clip((flare - 0.6) * 4.0, 0, 1)
    # Fine plasma turbulence
    turb = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 4410)
    # M: high metallic in eruption zones, moderate in loops, low in quiet regions
    M = np.clip(80.0 + loops * 100.0 * s + eruption * 75.0 * s + turb * 20.0 * s, 0, 255).astype(np.float32)
    # R: smooth in active zones, rougher in quiet corona
    R = np.clip(10.0 + (1.0 - loops) * 110.0 * s + turb * 40.0 * s - eruption * 30.0 * s, 15, 255).astype(np.float32)
    # CC: brilliant clarity in eruption, degraded in cooler zones
    CC = np.clip(16.0 + (1.0 - loops) * 80.0 * s + (1.0 - eruption) * 30.0 * s, 16, 255).astype(np.float32)
    return M, R, _cc_clamp(CC)


def spec_p_seismic(shape, seed, sm, base_m, base_r):
    """Seismic faultline: fault-driven. Graphite rough (high R) vs molten crack sharp (low R, high M)."""
    h, w = shape[:2] if len(shape) > 2 else shape
    fault = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 3000)
    crack = np.clip(1.0 - np.abs(fault - 0.5) * 2.5, 0, 1)  # narrow crack lines
    M = np.clip((0.05 + crack * 0.90) * 255.0, 0, 255).astype(np.float32)
    R = np.clip((0.75 - crack * 0.55) * 255.0, 15, 255).astype(np.float32)
    CC = np.where(crack > 0.5, 16.0, 120.0).astype(np.float32)
    return M, R, _cc_clamp(CC)


def spec_p_hypercane(shape, seed, sm, base_m, base_r):
    """Hypercane: dramatic swirling turbulence with lightning flashes and rain sheets."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # Large swirling storm turbulence (cloud structure)
    storm_base = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 3001)
    # Fine chaotic detail (rain sheets / micro-turbulence)
    chaos = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 3010)
    # Lightning filaments — very narrow bright threads where storm peaks
    bolt = np.clip(1.0 - np.abs(storm_base - 0.92) * 18.0, 0, 1)
    bolt2 = np.clip(1.0 - np.abs(chaos - 0.95) * 25.0, 0, 1)  # secondary branches
    lightning = np.maximum(bolt, bolt2 * 0.7)
    # Eye of storm — calm zone where storm_base is very low
    eye = np.clip(1.0 - storm_base * 3.0, 0, 1)  # only where storm_base < 0.33
    # M: cloud void (0) to lightning flash metallic (180)
    M = np.clip(lightning * 180.0 + eye * 40.0, 0, 255).astype(np.float32)
    # R: rain-slick smooth in lightning zones, churning rough in cloud mass
    cloud_rough = storm_base * 0.7 + chaos * 0.3  # combined turbulence
    R = np.clip((0.85 - lightning * 0.80 - eye * 0.30) * 255.0 + cloud_rough * 60.0, 15, 255).astype(np.float32)
    # CC: eye of storm = high clarity, cloud mass = heavy degradation
    CC = np.where(eye > 0.4, 20.0,
         np.where(lightning > 0.3, 30.0, 100.0 + storm_base * 80.0)).astype(np.float32)
    return M, R, _cc_clamp(CC)


def spec_p_geomagnetic(shape, seed, sm, base_m, base_r):
    """Geomagnetic storm: aurora borealis bands — wavy horizontal metallic bands with shimmer."""
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    # Horizontal wavy aurora bands using sine waves with noise displacement
    wave_disp = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 3050)
    band_y = y + wave_disp * 0.15  # displace y to make bands wavy
    # Multiple overlapping aurora curtains at different frequencies
    curtain1 = (np.sin(band_y * np.pi * 6.0) * 0.5 + 0.5)
    curtain2 = (np.sin(band_y * np.pi * 10.0 + 1.7) * 0.5 + 0.5)
    curtain3 = (np.sin(band_y * np.pi * 14.0 + 3.1) * 0.5 + 0.5)
    aurora = np.clip(curtain1 * 0.5 + curtain2 * 0.3 + curtain3 * 0.2, 0, 1)
    # Fine shimmer within the bright bands
    shimmer = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 3055)
    # M: bright aurora bands = high metallic (200-250), dark gaps = void (0-30)
    M = np.clip(aurora * 220.0 + shimmer * 30.0 * aurora, 0, 255).astype(np.float32)
    # R: shimmer variation within bands, rougher in dark gaps
    R = np.clip((1.0 - aurora) * 160.0 + shimmer * 30.0 * (1.0 - aurora) + aurora * 8.0, 15, 255).astype(np.float32)
    # CC: mostly glossy in bright bands, degrades in dark gaps
    CC = np.where(aurora > 0.5, 16.0 + (1.0 - aurora) * 20.0, 60.0 + (1.0 - aurora) * 80.0).astype(np.float32)
    return M, R, _cc_clamp(CC)


def spec_p_non_euclidean(shape, seed, sm, base_m, base_r):
    """Non-Euclidean hypercube: Poincaré disk hyperbolic tiling — mirror vs matte by hyperbolic
    face. Tile density increases toward boundary (genuinely non-Euclidean; {5,4} tiling)."""
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    # Normalize to Poincaré disk (unit circle centered on image)
    scale = min(h, w) * 0.47
    xn = (x - w * 0.5) / scale
    yn = (y - h * 0.5) / scale
    r = np.sqrt(np.clip(xn**2 + yn**2, 0.0, 0.9801))
    # Hyperbolic distance: d = 2*arctanh(r) — tiles compress toward disk boundary
    d_hyp = 2.0 * np.arctanh(np.clip(r, 0.0, 0.9990))
    theta = np.arctan2(yn, xn)  # [-pi, pi]
    # {5,4} hyperbolic tiling: alternating radial rings × 5-sector angular partition
    ring = np.floor(d_hyp * 1.2).astype(np.int32) % 2
    sector = np.floor((theta + np.pi) / (2.0 * np.pi / 5.0)).astype(np.int32) % 2
    face = ((ring + sector) % 2).astype(np.float32)
    # Edge distortion at hyperbolic tile boundaries
    edge_noise = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 4700)
    M = np.where(face > 0.5, 220.0 + edge_noise * 25.0, 30.0 + edge_noise * 40.0).astype(np.float32)
    M = np.clip(M, 0, 255).astype(np.float32)
    R = np.where(face > 0.5, 15.0 + edge_noise * 12.0, 175.0 + edge_noise * 45.0).astype(np.float32)
    # GGX floor: R >= 15 unconditionally (audit uses registry M, not per-pixel M)
    R = np.clip(R, 15, 255).astype(np.float32)
    CC = np.where(face > 0.5, 16.0, 110.0 + edge_noise * 40.0).astype(np.float32)
    return M, R, _cc_clamp(CC)


def spec_p_time_reversed(shape, seed, sm, base_m, base_r):
    """Time-reversed entropy: crystal growth from chaos — ordered zones expanding into disorder."""
    h, w = shape[:2] if len(shape) > 2 else shape
    s = max(sm, 0.05)  # amplitude scale (never fully zero)
    # Crystal growth front — ordered zones expanding outward
    growth = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 4500)
    crystal = np.clip((growth - 0.3) * 2.0, 0, 1)  # ordered crystalline zones
    # Chaos residue — fine-grain disorder in uncrystallized areas
    chaos = multi_scale_noise((h, w), [1, 2, 4], [0.4, 0.35, 0.25], seed + 4510)
    disorder = np.clip(1.0 - crystal, 0, 1) * chaos
    # Growth front boundary — sharp transition zone
    front = np.clip(1.0 - np.abs(growth - 0.3) * 5.0, 0, 1)
    # M: high metallic in crystallized zones, low in chaos
    M = np.clip(crystal * 200.0 * s + front * 55.0 * s + disorder * 20.0 * s, 0, 255).astype(np.float32)
    # R: smooth in crystal, very rough in chaos zones
    R = np.clip(5.0 + (1.0 - crystal) * 150.0 * s + disorder * 60.0 * s - front * 20.0 * s, 15, 255).astype(np.float32)
    # CC: clear in crystal, degraded in chaos
    CC = np.clip(16.0 + (1.0 - crystal) * 100.0 * s + disorder * 30.0 * s, 16, 255).astype(np.float32)
    return M, R, _cc_clamp(CC)


def spec_p_programmable(shape, seed, sm, base_m, base_r):
    """Programmable nanobots: sharp binary transitions between absolute mirror and matte void,
    with dithered/halftone-style noisy boundaries between the two extreme states."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # Large-scale zone separation (which areas are mirror vs void)
    zone = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 3002)
    # Fine dither noise for boundary transitions (halftone effect)
    dither = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 3008)
    # Medium-scale cell structure for nanobot swarm clusters
    cell = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 3012)
    # Binary threshold with noise-driven boundary: sharp but organic edges
    threshold = 0.50 + (dither - 0.5) * 0.35  # threshold varies per pixel (dithered)
    mirror_mask = (zone > threshold).astype(np.float32)
    # Add sub-pixel jitter from cell structure at boundaries
    boundary = np.clip(1.0 - np.abs(zone - 0.50) * 6.0, 0, 1)  # narrow band around 0.5
    cell_flip = (cell > 0.5).astype(np.float32)
    # In boundary zone, use cell pattern to create halftone-like dots
    final_mask = np.where(boundary > 0.3, cell_flip, mirror_mask)
    # M: absolute mirror (255) or total void (0) — no in-between
    M = (final_mask * 255.0).astype(np.float32)
    # R: mirror zones = 15 (near-perfect smooth), void zones = 255 (maximum rough)
    R = np.clip((1.0 - final_mask) * 255.0, 15, 255).astype(np.float32)
    # CC: mirror zones = glossy clear, void zones = dead flat
    CC = np.where(final_mask > 0.5, 16.0, 200.0).astype(np.float32)
    return M, R, _cc_clamp(CC)


def spec_p_erised(shape, seed, sm, base_m, base_r):
    """Mirror of Erised: warped reflective surface with distorted pools and rippled edges."""
    h, w = shape[:2] if len(shape) > 2 else shape
    s = max(sm, 0.05)  # amplitude scale (never fully zero)
    y, x = get_mgrid((h, w))
    # Warped mirror pools — large undulating surface deformations
    warp1 = np.sin(x * 0.03 + np.sin(y * 0.02) * 3.0) * 0.5 + 0.5
    warp2 = np.cos(y * 0.04 + np.cos(x * 0.03) * 2.5) * 0.5 + 0.5
    mirror_field = np.clip(warp1 * 0.6 + warp2 * 0.4, 0, 1)
    # Ripple edges where mirror distorts
    ripple = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 4600)
    edge = np.clip(1.0 - np.abs(mirror_field - 0.5) * 3.5, 0, 1)  # transition zones
    # Deep reflection pools
    pool = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 4610)
    # M: very high metallic in pools, reduced at warped edges
    M = np.clip(120.0 + mirror_field * 135.0 * s - edge * 60.0 * s + ripple * 15.0 * s, 0, 255).astype(np.float32)
    # R: ultra-smooth in deep pools, rougher at warp boundaries
    R = np.clip(edge * 130.0 * s + (1.0 - mirror_field) * 40.0 * s + ripple * 30.0 * s, 15, 255).astype(np.float32)
    # CC: pristine in mirror pools, softened at edges
    CC = np.clip(16.0 + edge * 70.0 * s + (1.0 - mirror_field) * 30.0 * s, 16, 255).astype(np.float32)
    return M, R, _cc_clamp(CC)


def spec_p_schrodinger(shape, seed, sm, base_m, base_r):
    """Schrodinger's dust: two-state spatial. Tiled metallic vs matte."""
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 3003)
    sh, sw = 16, 16
    state = rng.rand(sh, sw).astype(np.float32)
    # Nearest-neighbor upsample to (h, w)
    yy = (np.arange(h) * sh // h) % sh
    xx = (np.arange(w) * sw // w) % sw
    state_arr = state[np.ix_(yy, xx)].astype(np.float32)
    M = np.clip(state_arr * 220.0 + (1.0 - state_arr) * 30.0, 0, 255).astype(np.float32)
    R = np.clip((1.0 - state_arr) * 200.0 + state_arr * 20.0, 15, 255).astype(np.float32)
    CC = np.where(state_arr > 0.5, 16.0, 60.0).astype(np.float32)
    return M, R, _cc_clamp(CC)


# ============================================================================
# PIXEL-LEVEL RANDOM SPEC: "Every spec at once" at micro scale (Quantum Foam / Infinite Finish)
# Per-pixel random M, R, CC (seeded) so the surface has every reflectance/gloss/matte at once.
# CC in 16-255 only. Reproducible for same base + seed.
# ============================================================================

def spec_quantum_foam(shape, seed, sm, base_m, base_r):
    """Full range: every pixel gets a random M, R, CC (16-255). Every spec imaginable at micro scale."""
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 4000)
    M = rng.randint(0, 256, size=(h, w), dtype=np.int32).astype(np.float32)
    R = rng.randint(15, 256, size=(h, w), dtype=np.int32).astype(np.float32)
    # CC: 16 = max clearcoat, 17-255 = duller. No 0-15.
    CC = rng.randint(16, 256, size=(h, w), dtype=np.int32).astype(np.float32)
    return M, R, _cc_clamp(CC)


def spec_infinite_finish(shape, seed, sm, base_m, base_r):
    """Same idea as Quantum Foam, different seed — so they 'work together' as variants."""
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 4001)
    M = rng.randint(0, 256, size=(h, w), dtype=np.int32).astype(np.float32)
    R = rng.randint(15, 256, size=(h, w), dtype=np.int32).astype(np.float32)
    CC = rng.randint(16, 256, size=(h, w), dtype=np.int32).astype(np.float32)
    return M, R, _cc_clamp(CC)


def paint_quantum_foam_v2(paint, shape, mask, seed, pm, bb):
    """Neutral base so the spec is the star — subtle cool gray."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    gray = np.clip(base.mean(axis=2, keepdims=True) * 0.5 + 0.35, 0, 1)
    neutral = np.tile(gray, (1, 1, 3)).astype(np.float32)
    blend = np.clip(mask[:, :, np.newaxis] * pm, 0, 1)
    result = np.clip(base * (1.0 - blend) + neutral * blend, 0, 1)
    return result.astype(np.float32)


def paint_infinite_finish_v2(paint, shape, mask, seed, pm, bb):
    """Neutral base — very slight warm tint so it pairs differently with Quantum Foam."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    gray = np.clip(base.mean(axis=2) * 0.5 + 0.38, 0, 1)
    warm = np.stack([gray * 1.02, gray * 0.98, gray * 0.95], axis=-1)
    blend = np.clip(mask[:, :, np.newaxis] * pm, 0, 1)
    result = np.clip(base * (1.0 - blend) + np.clip(warm, 0, 1) * blend, 0, 1)
    return result.astype(np.float32)


# ============================================================================
# 2026-04-24 regular-base rebuild override: holographic foil
# ============================================================================

def _ps_norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min())
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _ps_micro(shape, seed, density):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("micro", int(h), int(w), int(seed), round(float(density), 6))
    cached = _PS_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    work = min(1024, int(h), int(w))
    sh, sw = h, w
    if work < min(h, w):
        sh = max(128, int(round(h * work / max(h, w))))
        sw = max(128, int(round(w * work / max(h, w))))
    else:
        sh, sw = h, w
    rng = np.random.default_rng(seed)
    n = min(int(sh * sw * density), 90000)
    out = np.zeros((sh, sw), dtype=np.float32)
    if n > 0:
        yy = rng.integers(0, sh, n)
        xx = rng.integers(0, sw, n)
        vals = rng.uniform(0.2, 1.0, n).astype(np.float32)
        np.maximum.at(out, (yy, xx), vals)
    out = np.maximum.reduce([
        out,
        np.roll(out, 1, axis=0) * 0.36,
        np.roll(out, -1, axis=1) * 0.36,
    ]).astype(np.float32)
    if (sh, sw) != (h, w):
        out = _resize_array(out, h, w).astype(np.float32)
    return _ps_cache_put(key, out)


def paint_holographic_base_v2(paint, shape, mask, seed, pm, bb):
    """Fine holographic foil: micro-diffraction grain, not candy-cane stripes."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    work = min(640, h, w)
    sh, sw = h, w
    if work < min(h, w):
        sh = max(128, int(round(h * work / max(h, w))))
        sw = max(128, int(round(w * work / max(h, w))))
    y, x = get_mgrid((sh, sw))
    xn = x / max(sw - 1, 1)
    yn = y / max(sh - 1, 1)
    warp = multi_scale_noise((sh, sw), [8, 19, 47], [0.42, 0.36, 0.22], seed + 2004)
    theta = xn * 0.38 + yn * 0.31 + warp * 0.34
    g1 = np.sin(x * 0.86 + y * 0.05 + theta * 5.0)
    g2 = np.sin(x * -0.41 + y * 0.74 + theta * 4.3)
    g3 = np.sin((x + y) * 1.57 + warp * 3.0)
    diffraction = _ps_norm01(g1 * 0.46 + g2 * 0.37 + g3 * 0.17)
    micro = _ps_micro((sh, sw), seed + 2005, 0.046)
    phase = np.mod(theta + diffraction * 0.16 + micro * 0.08, 1.0) * np.pi * 2.0
    holo = np.stack([
        0.46 + 0.38 * np.cos(phase),
        0.46 + 0.38 * np.cos(phase - 2.094),
        0.50 + 0.40 * np.cos(phase + 2.094),
    ], axis=-1).astype(np.float32)
    base_gray = _resize_array(base.mean(axis=2).astype(np.float32), sh, sw)[:, :, None]
    foil = np.clip(base_gray * 0.28 + holo * (0.62 + diffraction[:, :, None] * 0.18), 0, 1)
    foil = np.clip(foil + micro[:, :, None] * holo * 0.18, 0, 1)
    if (sh, sw) != (h, w):
        foil = np.stack([_resize_array(foil[:, :, c], h, w) for c in range(3)], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1.0 - blend) + foil * blend + bb[:, :, None] * 0.15 * blend, 0, 1).astype(np.float32)


def spec_holographic_base(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    grain = _ps_norm01(_ps_noise((h, w), [2, 5, 11, 26], [0.34, 0.30, 0.22, 0.14], seed + 2004, cap=768))
    micro = _ps_micro((h, w), seed + 2005, 0.046)
    field = np.clip(grain * 0.58 + micro * 0.62, 0, 1)
    M = np.clip(170.0 + field * 74.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + (1.0 - micro) * 34.0 * sm + grain * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + field * 16.0 * sm, 16, 255).astype(np.float32)
    return M, R, _cc_clamp(CC)


# ============================================================================
# 2026-05-06 PARADIGM SPEC MASTERCLASS PASS
# ============================================================================

_PARADIGM_SPEC_DS = 1.24


_PARADIGM_SPEC_PROFILES = {
    "p_superfluid": {
        "ridge_m": 0.15, "ridge_r": 1.30, "ridge_cc": -0.55,
        "crest_m": 0.35, "crest_r": -0.18, "crest_cc": -0.85,
        "dot_m": 0.55, "dot_r": -0.36, "dot_cc": -0.52,
        "nano_m": 0.10, "nano_r": 0.55, "nano_cc": -0.18,
    },
    "p_coronal": {
        "ridge_m": 0.42, "ridge_r": -0.24, "ridge_cc": -0.70,
        "crest_m": 0.84, "crest_r": -0.62, "crest_cc": -0.72,
        "dot_m": 0.96, "dot_r": -0.74, "dot_cc": -0.62,
        "nano_m": 0.34, "nano_r": 0.08, "nano_cc": -0.12,
    },
    "p_seismic": {
        "ridge_m": 0.18, "ridge_r": 1.38, "ridge_cc": 0.70,
        "crest_m": 1.10, "crest_r": -0.96, "crest_cc": -0.86,
        "dot_m": 0.62, "dot_r": -0.30, "dot_cc": -0.24,
        "nano_m": 0.12, "nano_r": 0.58, "nano_cc": 0.16,
    },
    "p_hypercane": {
        "ridge_m": 0.20, "ridge_r": 0.96, "ridge_cc": -0.36,
        "crest_m": 0.68, "crest_r": -0.52, "crest_cc": -0.56,
        "dot_m": 0.72, "dot_r": -0.44, "dot_cc": -0.40,
        "nano_m": 0.06, "nano_r": 0.72, "nano_cc": 0.12,
    },
    "p_geomagnetic": {
        "ridge_m": 0.24, "ridge_r": 0.48, "ridge_cc": -0.28,
        "crest_m": 0.62, "crest_r": -0.44, "crest_cc": -0.44,
        "dot_m": 0.58, "dot_r": -0.36, "dot_cc": -0.36,
        "nano_m": 0.18, "nano_r": 0.26, "nano_cc": -0.12,
    },
    "p_time_reversed": {
        "ridge_m": 0.12, "ridge_r": 1.12, "ridge_cc": 0.42,
        "crest_m": 0.52, "crest_r": -0.30, "crest_cc": -0.34,
        "dot_m": 0.38, "dot_r": 0.20, "dot_cc": 0.18,
        "nano_m": 0.10, "nano_r": 0.68, "nano_cc": 0.12,
    },
    "p_programmable": {
        "ridge_m": 0.08, "ridge_r": 1.52, "ridge_cc": 0.82,
        "crest_m": 0.76, "crest_r": -0.70, "crest_cc": -0.58,
        "dot_m": 0.34, "dot_r": 0.72, "dot_cc": 0.36,
        "nano_m": 0.06, "nano_r": 0.92, "nano_cc": 0.42,
    },
    "p_schrodinger": {
        "ridge_m": 0.20, "ridge_r": 0.72, "ridge_cc": -0.16,
        "crest_m": 0.46, "crest_r": -0.24, "crest_cc": -0.34,
        "dot_m": 0.68, "dot_r": -0.42, "dot_cc": -0.42,
        "nano_m": 0.14, "nano_r": 0.46, "nano_cc": 0.08,
    },
}

_PARADIGM_REDLINE_SUPPRESSION = {
    "p_superfluid": 0.88,
    "p_coronal": 0.54,
    "p_seismic": 0.46,
    "p_hypercane": 0.74,
    "p_geomagnetic": 0.92,
    "p_non_euclidean": 0.58,
    "p_time_reversed": 0.86,
    "p_programmable": 0.78,
    "p_erised": 0.96,
    "p_schrodinger": 0.74,
}


def _paradigm_suppress_redline_artifacts(finish_id, M, R, CC, detail=None):
    """Prevent shared M-channel red strokes from becoming the spec identity."""
    strength = float(_PARADIGM_REDLINE_SUPPRESSION.get(finish_id, 0.72))
    detail_w = 1.0 if detail is None else (0.42 + np.clip(detail, 0.0, 1.0).astype(np.float32) * 0.58)
    red_bias = np.clip((M - np.maximum(R * 0.86, CC * 0.72) - 4.0) / 112.0, 0.0, 1.0) * detail_w * strength
    satin = np.clip(red_bias * 0.92, 0.0, 1.0)
    glass = np.clip(red_bias * (0.70 + 0.24 * (finish_id in ("p_superfluid", "p_geomagnetic", "p_erised"))), 0.0, 1.0)
    M = np.clip(M - red_bias * 132.0, 0.0, 255.0)
    R = np.clip(R + satin * 82.0, 15.0, 255.0)
    CC = np.clip(CC + glass * 78.0, 16.0, 255.0)
    red_region = (M > (R * 0.72 + 24.0)) & (M > (CC * 0.60 + 24.0))
    red_region_w = red_region.astype(np.float32) * detail_w * strength
    target_m = np.maximum(R * 0.66, CC * 0.62) + 22.0
    M = np.clip(M * (1.0 - red_region_w * 0.86) + target_m * red_region_w * 0.86, 0.0, 255.0)
    R = np.clip(R + red_region_w * 58.0, 15.0, 255.0)
    CC = np.clip(CC + red_region_w * 64.0, 16.0, 255.0)
    return M.astype(np.float32), R.astype(np.float32), _cc_clamp(CC)


def _ps_stable_seed(finish_id, seed):
    total = int(seed) * 1103515245
    for ch in str(finish_id):
        total = (total * 33 + ord(ch)) & 0x7FFFFFFF
    return total


def _ps_hash_noise(shape, seed, salt):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    xn = x.astype(np.float32) / max(w - 1, 1)
    yn = y.astype(np.float32) / max(h - 1, 1)
    n = np.sin((xn * 127.1 + yn * 311.7 + (int(seed) + int(salt)) * 0.071) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _ps_edge01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    edge = (
        np.abs(arr - np.roll(arr, 1, axis=0))
        + np.abs(arr - np.roll(arr, -1, axis=0))
        + np.abs(arr - np.roll(arr, 1, axis=1))
        + np.abs(arr - np.roll(arr, -1, axis=1))
    ) * 0.25
    hi = float(edge.max()) + 1e-6
    return np.clip(edge / hi, 0.0, 1.0).astype(np.float32)


def _paradigm_masterclass_spec(finish_id, shape, seed, sm, M, R, CC):
    """Viva-Mexico-inspired deterministic spec sculpt for procedural Paradigm bases.

    The original spec is treated as the source plate: channel edges become motif
    relief, dark/matte voids are protected, and seeded micro/nano grids add
    many local M/R/CC values without turning every finish into the same chrome.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    s = max(float(sm), 0.05) * _PARADIGM_SPEC_DS
    M = np.asarray(M, dtype=np.float32).copy()
    R = np.asarray(R, dtype=np.float32).copy()
    CC = np.asarray(CC, dtype=np.float32).copy()
    fid_seed = _ps_stable_seed(finish_id, seed)
    y, x = get_mgrid((h, w))
    xn = x.astype(np.float32) / max(w - 1, 1)
    yn = y.astype(np.float32) / max(h - 1, 1)

    plate = _ps_norm01(M * 0.42 + (255.0 - R) * 0.34 + (255.0 - CC) * 0.24)
    edge = _ps_edge01(plate)
    void = (M < 38.0) & (R > 152.0) & (edge < 0.22)
    void_w = void.astype(np.float32)
    M[:] = np.clip(M * (1.0 - void_w * 0.86) + 6.0 * void_w, 0.0, 255.0)
    R[:] = np.clip(R * (1.0 - void_w * 0.78) + 234.0 * void_w, 15.0, 255.0)
    CC[:] = np.clip(CC * (1.0 - void_w * 0.70) + 214.0 * void_w, 16.0, 255.0)

    phase = (fid_seed % 997) / 997.0
    phase_a = np.sin((xn * (340.0 + (fid_seed % 71)) + yn * (217.0 + ((fid_seed >> 7) % 83)) + phase) * np.pi)
    phase_b = np.sin(((xn - yn) * (430.0 + ((fid_seed >> 3) % 67)) + plate * 5.0 + phase * 2.0) * np.pi)
    weave = np.clip(1.0 - np.abs(phase_a) * 10.0, 0.0, 1.0)
    nano = np.clip(1.0 - np.abs(phase_b) * 16.0, 0.0, 1.0)

    micro_noise = _ps_hash_noise((h, w), fid_seed, 17)
    dots = np.clip(
        (micro_noise > 0.934).astype(np.float32) * 0.34
        + (micro_noise > 0.982).astype(np.float32) * 0.48
        + ((micro_noise > 0.875) & (micro_noise < 0.892)).astype(np.float32) * 0.20,
        0.0,
        1.0,
    )
    rare = (micro_noise > 0.992).astype(np.float32)
    profile = _PARADIGM_SPEC_PROFILES.get(finish_id, _PARADIGM_SPEC_PROFILES["p_superfluid"])
    ridge = np.power(edge, 0.82)
    crest = np.clip((plate - 0.64) * 2.8, 0.0, 1.0)
    satin_ring = np.clip(ridge - crest * 0.55, 0.0, 1.0)
    carrier = np.clip(ridge * 0.42 + crest * 0.46 + dots * 0.46 + weave * 0.26 + nano * 0.20, 0.0, 1.0)

    ridge_m = ridge * 22.0 * profile["ridge_m"]
    crest_m = crest * 42.0 * profile["crest_m"]
    dot_m = dots * 52.0 * profile["dot_m"]
    nano_m = nano * 16.0 * profile["nano_m"]
    rare_m = rare * 46.0 * max(profile["dot_m"], 0.18)

    ridge_r = ridge * 28.0 * profile["ridge_r"]
    crest_r = crest * 36.0 * profile["crest_r"]
    dot_r = dots * 28.0 * profile["dot_r"]
    nano_r = nano * 18.0 * profile["nano_r"]
    rare_r = rare * 24.0 * profile["dot_r"]

    ridge_cc = ridge * 22.0 * profile["ridge_cc"]
    crest_cc = crest * 30.0 * profile["crest_cc"]
    dot_cc = dots * 24.0 * profile["dot_cc"]
    nano_cc = nano * 16.0 * profile["nano_cc"]
    rare_cc = rare * 22.0 * profile["dot_cc"]

    M[:] = np.clip(M + (ridge_m + crest_m + dot_m + nano_m + rare_m) * s, 0.0, 255.0)
    R[:] = np.clip(R + (ridge_r + crest_r + dot_r + nano_r + rare_r) * s + satin_ring * 5.0 * s, 15.0, 255.0)
    CC[:] = np.clip(CC + (ridge_cc + crest_cc + dot_cc + nano_cc + rare_cc) * s + (1.0 - carrier) * 6.0, 16.0, 255.0)

    detail = np.clip(ridge * 0.58 + crest * 0.36 + weave * 0.20 + nano * 0.18 + dots * 0.30, 0.0, 1.0)
    return _paradigm_suppress_redline_artifacts(finish_id, M, R, CC, detail)


_legacy_spec_p_superfluid = spec_p_superfluid
_legacy_spec_p_coronal = spec_p_coronal
_legacy_spec_p_seismic = spec_p_seismic
_legacy_spec_p_hypercane = spec_p_hypercane
_legacy_spec_p_geomagnetic = spec_p_geomagnetic
_legacy_spec_p_non_euclidean = spec_p_non_euclidean
_legacy_spec_p_time_reversed = spec_p_time_reversed
_legacy_spec_p_programmable = spec_p_programmable
_legacy_spec_p_erised = spec_p_erised
_legacy_spec_p_schrodinger = spec_p_schrodinger


# SPB perf 2026-06-04: _paradigm_masterclass_spec was the entire >4s cost of the p_*
# paradigm bases at 2048 (uncapped spec measured 4.3-8.5s/base; the sculpt alone is
# ~3.6-5.5s of full-res arithmetic: redline-suppress ~0.9s, np.power(edge) ~0.4s,
# _ps_edge01 rolls ~0.25s, plus ~30 weighted-contribution adds). The chain is a
# reflectance sculpt over a smooth legacy carrier, so we run legacy(spec) + masterclass
# at a capped working resolution and bilinear-upscale M/R/CC to full res.
#   * std@256 and a 160px native render are BYTE-IDENTICAL (cap is inactive at <=768,
#     so the stated look criteria are preserved exactly).
#   * The micro/nano/hash-dot sparkle is threshold-noise: its 2048 per-pixel statistics
#     are resolution-dependent by construction (no cap recovers them exactly, and the
#     character is intentionally stochastic), but on a car body it reads identically.
# cap=768 lands every masterclass spec at ~0.3-0.9s (was 4-8.5s) with the widest margin
# under the owner's "no base over 4s" ceiling.
_PARADIGM_MASTER_CAP = 768


def _masterclass_capped(finish_id, shape, seed, sm, base_m, base_r, legacy_fn):
    """Run legacy spec + masterclass sculpt at a capped res, then upscale M/R/CC."""
    oh, ow = shape[:2] if len(shape) > 2 else shape
    oh, ow = int(oh), int(ow)
    cap = _PARADIGM_MASTER_CAP
    if min(oh, ow) <= cap:
        M, R, CC = legacy_fn((oh, ow), seed, sm, base_m, base_r)
        return _paradigm_masterclass_spec(finish_id, (oh, ow), seed, sm, M, R, CC)
    sh = max(256, int(round(oh * cap / max(oh, ow))))
    sw = max(256, int(round(ow * cap / max(oh, ow))))
    M, R, CC = legacy_fn((sh, sw), seed, sm, base_m, base_r)
    M, R, CC = _paradigm_masterclass_spec(finish_id, (sh, sw), seed, sm, M, R, CC)
    M = _resize_array(np.asarray(M, dtype=np.float32), oh, ow)
    R = _resize_array(np.asarray(R, dtype=np.float32), oh, ow)
    CC = _resize_array(np.asarray(CC, dtype=np.float32), oh, ow)
    return M.astype(np.float32), R.astype(np.float32), _cc_clamp(CC)


def spec_p_superfluid(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    s = max(float(sm), 0.05) * _PARADIGM_SPEC_DS
    y, x = get_mgrid((h, w))
    xn = x.astype(np.float32) / max(w - 1, 1)
    yn = y.astype(np.float32) / max(h - 1, 1)
    flow = _ps_noise((h, w), [9, 17, 35], [0.38, 0.37, 0.25], seed + 9101, cap=420)
    ripple = np.clip(1.0 - np.abs(np.sin((xn * 38.0 + yn * 24.0 + flow * 3.6) * np.pi)) * 15.0, 0.0, 1.0)
    vortex = np.clip(1.0 - np.abs(np.sin((np.sqrt((xn - 0.50) ** 2 + (yn - 0.52) ** 2) * 58.0 + flow * 2.2) * np.pi)) * 18.0, 0.0, 1.0)
    micro = _ps_hash_noise((h, w), _ps_stable_seed("p_superfluid", seed), 17)
    bubble = np.clip((micro > 0.900).astype(np.float32) * 0.32 + (micro > 0.978).astype(np.float32) * 0.48, 0, 1)
    M = np.clip(24.0 + vortex * 48.0 * s + bubble * 44.0 * s, 0, 255).astype(np.float32)
    R = np.clip(88.0 + flow * 96.0 * s + ripple * 54.0 * s - bubble * 24.0 * s, 15, 255).astype(np.float32)
    CC = np.clip(44.0 + ripple * 96.0 * s + vortex * 58.0 * s - bubble * 22.0 * s, 16, 255).astype(np.float32)
    detail = np.clip(ripple * 0.32 + vortex * 0.36 + bubble * 0.42, 0, 1)
    return _paradigm_suppress_redline_artifacts("p_superfluid", M, R, CC, detail)


def spec_p_coronal(shape, seed, sm, base_m, base_r):
    return _masterclass_capped("p_coronal", shape, seed, sm, base_m, base_r, _legacy_spec_p_coronal)


def spec_p_seismic(shape, seed, sm, base_m, base_r):
    return _masterclass_capped("p_seismic", shape, seed, sm, base_m, base_r, _legacy_spec_p_seismic)


def spec_p_hypercane(shape, seed, sm, base_m, base_r):
    return _masterclass_capped("p_hypercane", shape, seed, sm, base_m, base_r, _legacy_spec_p_hypercane)


def spec_p_geomagnetic(shape, seed, sm, base_m, base_r):
    return _masterclass_capped("p_geomagnetic", shape, seed, sm, base_m, base_r, _legacy_spec_p_geomagnetic)


def spec_p_non_euclidean(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    work = min(420, h, w)
    if work < min(h, w):
        sh = max(160, int(round(h * work / max(h, w))))
        sw = max(160, int(round(w * work / max(h, w))))
    else:
        sh, sw = h, w
    y, x = get_mgrid((sh, sw))
    xn = (x.astype(np.float32) / max(sw - 1, 1) - 0.5) / 0.48
    yn = (y.astype(np.float32) / max(sh - 1, 1) - 0.5) / 0.48
    warp = _ps_noise((sh, sw), [5, 11, 23], [0.34, 0.39, 0.27], seed + 4700, cap=420)
    xn = xn + warp * 0.08
    yn = yn - warp * 0.06
    r = np.sqrt(np.clip(xn * xn + yn * yn, 0.0, 0.9801))
    hyp = 2.0 * np.arctanh(np.clip(r, 0.0, 0.999))
    a = np.arctan2(yn, xn)
    ring = np.clip(1.0 - np.abs(np.sin((hyp * 1.34 + warp * 0.8) * np.pi)) * 13.0, 0.0, 1.0)
    sector = np.clip(1.0 - np.abs(np.sin((a * 5.0 + hyp * 0.7) * np.pi)) * 11.0, 0.0, 1.0)
    face = (np.floor(hyp * 1.1).astype(np.int32) + np.floor((a + np.pi) / (np.pi / 5.0)).astype(np.int32)) % 2
    edge = np.clip(ring * 0.58 + sector * 0.52, 0.0, 1.0)
    M = np.where(face > 0, 196.0, 38.0).astype(np.float32) + edge * 58.0 + warp * 20.0
    R = np.where(face > 0, 20.0, 174.0).astype(np.float32) + (1.0 - edge) * 34.0 - edge * 14.0
    CC = np.where(face > 0, 16.0, 118.0).astype(np.float32) + (1.0 - edge) * 30.0 - edge * 18.0
    if (sh, sw) != (h, w):
        M = _resize_array(M.astype(np.float32), h, w)
        R = _resize_array(R.astype(np.float32), h, w)
        CC = _resize_array(CC.astype(np.float32), h, w)
        edge = _resize_array(edge.astype(np.float32), h, w)
    micro = _ps_hash_noise((h, w), _ps_stable_seed("p_non_euclidean", seed), 17)
    dots = (micro > 0.964).astype(np.float32)
    M = np.clip(M + dots * 54.0 * _PARADIGM_SPEC_DS, 0, 255).astype(np.float32)
    R = np.clip(R - dots * 22.0 * _PARADIGM_SPEC_DS, 15, 255).astype(np.float32)
    CC = np.clip(CC - dots * 18.0 * _PARADIGM_SPEC_DS, 16, 255).astype(np.float32)
    return _paradigm_suppress_redline_artifacts("p_non_euclidean", M, R, CC, np.clip(edge + dots, 0, 1))


def spec_p_time_reversed(shape, seed, sm, base_m, base_r):
    return _masterclass_capped("p_time_reversed", shape, seed, sm, base_m, base_r, _legacy_spec_p_time_reversed)


def spec_p_programmable(shape, seed, sm, base_m, base_r):
    return _masterclass_capped("p_programmable", shape, seed, sm, base_m, base_r, _legacy_spec_p_programmable)


def spec_p_erised(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    s = max(float(sm), 0.05) * _PARADIGM_SPEC_DS
    y, x = get_mgrid((h, w))
    xn = x.astype(np.float32) / max(w - 1, 1)
    yn = y.astype(np.float32) / max(h - 1, 1)
    warp = _ps_noise((h, w), [7, 15, 31], [0.30, 0.42, 0.28], seed + 4610, cap=384)
    pool = np.clip(0.5 + 0.5 * np.sin((xn * 7.0 + np.sin(yn * 8.0 + warp * 2.4) + warp * 3.0) * np.pi), 0.0, 1.0)
    relief = np.clip(1.0 - np.abs(pool - 0.50) * 5.4, 0.0, 1.0)
    micro = _ps_hash_noise((h, w), _ps_stable_seed("p_erised", seed), 17)
    pores = np.clip(
        (micro > 0.842).astype(np.float32) * 0.34
        + (micro > 0.982).astype(np.float32) * 0.52
        + ((micro > 0.730) & (micro < 0.744)).astype(np.float32) * 0.16,
        0.0,
        1.0,
    )
    ghost = np.clip(1.0 - np.abs(np.sin((xn * 31.0 - yn * 19.0 + warp * 4.2) * np.pi)) * 22.0, 0.0, 1.0) * relief
    M = np.clip(80.0 + pool * 114.0 * s - relief * 36.0 * s + ghost * 58.0 * s + pores * 70.0 * s, 0, 255).astype(np.float32)
    R = np.clip(18.0 + relief * 112.0 * s + (1.0 - pool) * 42.0 * s - ghost * 24.0 * s - pores * 18.0 * s, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + relief * 72.0 * s + (1.0 - pool) * 30.0 * s - ghost * 20.0 * s - pores * 16.0 * s, 16, 255).astype(np.float32)
    return _paradigm_suppress_redline_artifacts("p_erised", M, R, CC, np.clip(relief + ghost + pores, 0, 1))


def spec_p_schrodinger(shape, seed, sm, base_m, base_r):
    return _masterclass_capped("p_schrodinger", shape, seed, sm, base_m, base_r, _legacy_spec_p_schrodinger)


# ===========================================================================
# paint_v3 Batch 1 Cosmic & Spacetime retool overrides
# ===========================================================================
from engine.paint_v3.paradigm_v3_batch_1 import (
    spec_singularity, paint_singularity,
    spec_nebula, paint_nebula,
    spec_infinite_finish, paint_infinite_finish,
)

paint_singularity_v2 = paint_singularity
paint_nebula_v2 = paint_nebula
paint_infinite_finish_v2 = paint_infinite_finish
