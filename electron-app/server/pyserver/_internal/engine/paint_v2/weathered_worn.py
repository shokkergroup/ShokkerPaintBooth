import numpy as np
from engine.core import multi_scale_noise, get_mgrid


# =============================================================================
# ACID_ETCH - Hydrofluoric acid etching with reaction front propagation
# =============================================================================

def paint_acid_etch_v2(paint, shape, mask, seed, pm, bb):
    """
    Hydrofluoric acid etching: reaction front propagates from edges inward,
    creating characteristic V-shaped etch pits with variable depth.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Reaction front propagation (diffusion-like spread)
    front = multi_scale_noise((h, w), [1, 2, 4, 8], [0.4, 0.3, 0.2, 0.1], seed + 3000)
    front = np.clip(front, 0, 1)
    
    # Distance from edges (reaction front source)
    y, x = get_mgrid((h, w))
    dist_from_edge = np.minimum(y, np.minimum(x, np.minimum(h - 1 - y, w - 1 - x)))
    dist_from_edge = np.clip(dist_from_edge / max(h, w) * 2, 0, 1)
    
    # Reaction depth (deeper in high-front, near-edge areas)
    etch_depth = front * (1.0 - dist_from_edge) * 0.4
    
    # V-shaped pit geometry (sharper edges)
    pit_geometry = np.abs(np.sin(front * np.pi * 4)) * 0.3
    
    # Combine effects
    effect = np.stack([
        np.clip(paint[:, :, 0] * (1.0 - etch_depth * 0.6), 0, 1),
        np.clip(paint[:, :, 1] * (1.0 - etch_depth * 0.5), 0, 1),
        np.clip(paint[:, :, 2] * (1.0 - etch_depth * 0.4), 0, 1)
    ], axis=2)
    
    blend = pm * mask
    result = np.clip(
        paint * (1.0 - blend[:, :, np.newaxis]) + 
        effect * (blend[:, :, np.newaxis]),
        0, 1
    )
    return result.astype(np.float32)


def spec_acid_etch(shape, seed, sm, base_m, base_r):
    """
    Metallic spec for acid etch: reduced gloss from pitted surface,
    rough micro-texture.
    """
    h, w = shape
    base_m = base_m / 255.0
    base_r = base_r / 255.0
    
    # Pitting roughness
    rough = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 3001)
    M = np.clip(base_m * (1.0 - rough * 0.4), 0, 1)
    
    # Roughness increases
    R = np.clip(base_r + rough * 0.35, 0, 1)
    
    # Metallic character preserved but scattered
    CC = np.ones((h, w), dtype=np.float32) * 0.7
    
    return (np.clip(M.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(R.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(CC.astype(np.float32) * 255.0, 0, 255).astype(np.float32))


# =============================================================================
# ACID_RAIN - Acid rain pitting with calcium carbonate dissolution
# =============================================================================

def paint_acid_rain_v2(paint, shape, mask, seed, pm, bb):
    """
    Acid rain pitting: water runoff channels with pooling areas,
    uneven dissolution creating striations and pit clusters.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Directional flow (gravity-influenced rain runoff)
    flow_base = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 3010)
    y, x = get_mgrid((h, w))
    flow = (y / h) * 0.6 + flow_base * 0.4
    
    # Pit clustering (pooling areas)
    pits = multi_scale_noise((h, w), [1, 3, 6], [0.5, 0.3, 0.2], seed + 3011)
    pits = np.clip(pits, 0, 1)
    pit_depth = np.clip(pits, 0, None) ** 1.5 * 0.35
    
    # Dissolution pattern (streaky)
    dissolution = multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 3012)
    dissolution = np.clip(dissolution, 0, 1)
    
    # Combined darkening from flow + pitting
    combined_damage = (flow * 0.3 + pit_depth * 0.7) * dissolution
    
    effect = np.stack([
        np.clip(paint[:, :, 0] * (1.0 - combined_damage * 0.5), 0, 1),
        np.clip(paint[:, :, 1] * (1.0 - combined_damage * 0.55), 0, 1),
        np.clip(paint[:, :, 2] * (1.0 - combined_damage * 0.6), 0, 1)
    ], axis=2)
    
    blend = pm * mask
    result = np.clip(
        paint * (1.0 - blend[:, :, np.newaxis]) + 
        effect * (blend[:, :, np.newaxis]),
        0, 1
    )
    return result.astype(np.float32)


def spec_acid_rain(shape, seed, sm, base_m, base_r):
    """
    Spec for acid rain: variable gloss from wet pooling and dry edges,
    moderate roughness increase.
    """
    h, w = shape
    base_m = base_m / 255.0
    base_r = base_r / 255.0
    
    # Pooling creates local gloss variations
    pooling = multi_scale_noise((h, w), [3, 6], [0.6, 0.4], seed + 3013)
    M = np.clip(base_m * (0.7 + pooling * 0.3), 0, 1)
    
    # Roughness from dissolution
    rough = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 3014)
    R = np.clip(base_r + rough * 0.3, 0, 1)
    
    CC = np.ones((h, w), dtype=np.float32) * 0.75
    
    return (np.clip(M.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(R.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(CC.astype(np.float32) * 255.0, 0, 255).astype(np.float32))


# =============================================================================
# BARN_FIND - Decades-dormant dust/debris accumulation with patchy reveal
# =============================================================================

def paint_barn_find_v2(paint, shape, mask, seed, pm, bb):
    """
    Barn find aesthetic: thick dust overlay with breakthrough areas showing
    original paint, gravity-driven settling with edge pooling.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Dust accumulation (heavier at bottom)
    y, x = get_mgrid((h, w))
    gravity_bias = (y / h) * 0.7
    
    # Large dust clumps
    dust_clumps = multi_scale_noise((h, w), [8, 16, 32], [0.5, 0.3, 0.2], seed + 3020)
    dust_clumps = np.clip(dust_clumps, 0, 1)
    
    # Breakthrough areas (random exposure)
    breakthrough = multi_scale_noise((h, w), [4, 8], [0.6, 0.4], seed + 3021)
    breakthrough = breakthrough ** 2  # Favor small exposed areas
    
    # Dust color (brown/tan)
    dust_color = np.array([0.5, 0.4, 0.3])
    dust_overlay = dust_color[np.newaxis, np.newaxis, :] * (gravity_bias + dust_clumps * 0.6)[:, :, np.newaxis]
    
    # Blend dust with breakthrough areas
    dust_opacity = (1.0 - breakthrough * 0.8) * dust_clumps
    
    effect = np.stack([
        np.clip(paint[:, :, 0] * (1.0 - dust_opacity * 0.5) + dust_overlay[:,:,0] * dust_opacity * 0.4, 0, 1),
        np.clip(paint[:, :, 1] * (1.0 - dust_opacity * 0.5) + dust_overlay[:,:,1] * dust_opacity * 0.4, 0, 1),
        np.clip(paint[:, :, 2] * (1.0 - dust_opacity * 0.5) + dust_overlay[:,:,2] * dust_opacity * 0.4, 0, 1)
    ], axis=2)
    
    blend = pm * mask
    result = np.clip(
        paint * (1.0 - blend[:, :, np.newaxis]) + 
        effect * (blend[:, :, np.newaxis]),
        0, 1
    )
    return result.astype(np.float32)


def spec_barn_find(shape, seed, sm, base_m, base_r):
    """
    Spec for barn find: dust dulls gloss significantly, very rough surface.
    """
    h, w = shape
    base_m = base_m / 255.0
    base_r = base_r / 255.0
    
    # Dust coverage
    dust = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 3022)
    M = np.clip(base_m * (0.2 + dust * 0.3), 0, 1)
    
    # Heavy roughness from dust texture
    rough = multi_scale_noise((h, w), [4, 8, 16], [0.4, 0.3, 0.3], seed + 3023)
    R = np.clip(base_r + rough * 0.6, 0, 1)
    
    CC = np.ones((h, w), dtype=np.float32) * 0.3
    
    return (np.clip(M.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(R.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(CC.astype(np.float32) * 255.0, 0, 255).astype(np.float32))

# =============================================================================
# CHALKY_BASE - Chalk oxidation with UV degradation polymer chain scission
# =============================================================================

def paint_chalky_base_v2(paint, shape, mask, seed, pm, bb):
    """
    Chalky oxidation: polymer chains break down under UV, creating powdery
    surface. Color is heavily desaturated and lifted toward a pale grey-white.
    Strong whitening push makes it visually read as chalk/powder.
    """
    h, w = shape[:2] if len(shape) > 2 else shape

    # UV exposure gradient (top gets more damage)
    y, x = get_mgrid((h, w))
    uv_gradient = (1.0 - y / h) * 0.7 + 0.3

    # Multi-scale degradation noise
    scission = multi_scale_noise((h, w), [2, 4, 8, 16], [0.3, 0.25, 0.25, 0.2], seed + 3030)
    scission = np.clip(scission, 0, 1)

    # Strong desaturation toward pale chalky grey-white
    # Chalk = color drains away and a dusty white powder takes over
    gray = paint.mean(axis=2, keepdims=True)
    chalk_lift = (uv_gradient * scission * 0.7)[:, :, np.newaxis]  # heavy lift

    # Desaturate toward grey then push toward white
    desaturated = paint * 0.4 + gray * 0.6               # heavy desaturation
    whitened    = desaturated * (1.0 - chalk_lift * 0.6) + chalk_lift * 0.6  # lift to white

    effect = np.clip(whitened, 0, 1)

    blend = pm * mask
    result = np.clip(
        paint * (1.0 - blend[:, :, np.newaxis]) +
        effect * blend[:, :, np.newaxis],
        0, 1
    )
    return result.astype(np.float32)


def spec_chalky_base(shape, seed, sm, base_m, base_r):
    """
    Spec for chalky: severe polymer degradation - CC=230 near-maximum
    clearcoat breakdown. Surface is powdery dead, zero gloss.
    """
    h, w = shape
    base_r_n = base_r / 255.0

    # Roughness increases toward top (more UV exposure)
    y, _ = get_mgrid((h, w))
    uv_effect = (1.0 - y / h) * 0.6 + 0.4

    rough = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.3, 0.3], seed + 3031)
    R = np.clip(base_r_n + rough * 0.3 + uv_effect * 0.15, 0, 1)

    # M stays near zero — chalk is completely dielectric
    M = np.zeros((h, w), dtype=np.float32)

    # CC=230 — maximum clearcoat degradation = completely dead/powdery surface
    CC = np.full((h, w), 230.0, dtype=np.float32)

    return (np.clip(M * 255.0, 0, 255).astype(np.float32),
            np.clip(R * 255.0, 0, 255).astype(np.float32),
            CC)


# =============================================================================
# CRUMBLING_CLEAR - Clearcoat delamination with adhesion failure zones
# =============================================================================

def paint_crumbling_clear_v2(paint, shape, mask, seed, pm, bb):
    """
    Clearcoat delamination: adhesion failures create lifted flakes,
    exponential crack network propagation.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Adhesion failure zones (Voronoi-like clustering)
    failure_centers = multi_scale_noise((h, w), [8, 16], [0.7, 0.3], seed + 3040)
    failure_zones = np.clip(np.sqrt(np.clip(failure_centers, 0, None)), 0, 1)
    
    # Crack network (fractal-like propagation)
    cracks = multi_scale_noise((h, w), [1, 2, 4, 8, 16], [0.2, 0.2, 0.2, 0.2, 0.2], seed + 3041)
    cracks = np.clip(cracks, 0, 1)
    crack_severity = failure_zones * cracks
    
    # Edge lifting effect (darker underneath exposed paint)
    lift_shadow = np.abs(np.sin(cracks * np.pi * 8)) * crack_severity * 0.3
    
    # Exposed base color slightly yellowed
    exposed_color = np.array([1.0, 0.98, 0.92])
    
    effect = np.stack([
        np.clip(paint[:, :, 0] * (1.0 - crack_severity * 0.4) + lift_shadow, 0, 1),
        np.clip(paint[:, :, 1] * (1.0 - crack_severity * 0.35) + lift_shadow, 0, 1),
        np.clip(paint[:, :, 2] * (1.0 - crack_severity * 0.3) + lift_shadow * 0.5, 0, 1)
    ], axis=2)
    
    blend = pm * mask
    result = np.clip(
        paint * (1.0 - blend[:, :, np.newaxis]) + 
        effect * (blend[:, :, np.newaxis]),
        0, 1
    )
    return result.astype(np.float32)


def spec_crumbling_clear(shape, seed, sm, base_m, base_r):
    """
    Spec for crumbling clear: gloss lost at failure zones, high roughness
    from lifted flakes.
    """
    h, w = shape
    base_m = base_m / 255.0
    base_r = base_r / 255.0
    
    failure = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 3042)
    crack = multi_scale_noise((h, w), [2, 4, 8], [0.33, 0.33, 0.34], seed + 3043)
    
    delamination = failure * crack
    M = np.clip(base_m * (1.0 - delamination * 0.8), 0, 1)
    
    R = np.clip(base_r + delamination * 0.45, 0, 1)
    
    CC = np.ones((h, w), dtype=np.float32) * 0.5
    
    return (np.clip(M.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(R.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(CC.astype(np.float32) * 255.0, 0, 255).astype(np.float32))


# =============================================================================
# DESERT_WORN - Aeolian abrasion sand erosion pattern
# =============================================================================

def paint_desert_worn_v2(paint, shape, mask, seed, pm, bb):
    """
    Desert wind erosion: directional abrasion pattern (left-to-right default),
    sand blast pitting with smooth rounded edges.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Wind direction (left to right = higher damage on right)
    x_pos = np.linspace(0, 1, w)
    wind_gradient = np.tile(x_pos[np.newaxis, :], (h, 1))
    
    # Sand blast pitting (erosion centers)
    blasting = multi_scale_noise((h, w), [4, 8, 16], [0.4, 0.3, 0.3], seed + 3050)
    blasting = np.clip(blasting, 0, 1)
    
    # Smooth erosion profile (not sharp)
    erosion_depth = wind_gradient * blasting * 0.45
    
    effect = np.stack([
        np.clip(paint[:, :, 0] * (1.0 - erosion_depth * 0.5), 0, 1),
        np.clip(paint[:, :, 1] * (1.0 - erosion_depth * 0.5), 0, 1),
        np.clip(paint[:, :, 2] * (1.0 - erosion_depth * 0.6), 0, 1)
    ], axis=2)
    
    blend = pm * mask
    result = np.clip(
        paint * (1.0 - blend[:, :, np.newaxis]) + 
        effect * (blend[:, :, np.newaxis]),
        0, 1
    )
    return result.astype(np.float32)


def spec_desert_worn(shape, seed, sm, base_m, base_r):
    """
    Spec for desert: moderate gloss loss from sand abrasion,
    directional roughness increase.
    """
    h, w = shape
    base_m = base_m / 255.0
    base_r = base_r / 255.0
    
    x_pos = np.linspace(0, 1, w)
    wind = np.tile(x_pos[np.newaxis, :], (h, 1))
    
    sand = multi_scale_noise((h, w), [4, 8], [0.6, 0.4], seed + 3051)
    
    M = np.clip(base_m * (0.6 + wind * sand * 0.3), 0, 1)
    
    R = np.clip(base_r + wind * sand * 0.4, 0, 1)
    
    CC = np.ones((h, w), dtype=np.float32) * 0.65
    
    return (np.clip(M.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(R.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(CC.astype(np.float32) * 255.0, 0, 255).astype(np.float32))

# =============================================================================
# DESTROYED_COAT - Complete coating failure with substrate exposure
# =============================================================================

def paint_destroyed_coat_v2(paint, shape, mask, seed, pm, bb):
    """
    Complete paint failure: large areas of substrate exposure, heavy
    flaking pattern with irregular edges.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Flake boundaries (jagged edges)
    flakes = multi_scale_noise((h, w), [4, 8, 16, 32], [0.3, 0.25, 0.25, 0.2], seed + 3060)
    flakes = np.clip(flakes, 0, 1)
    
    # Exposure severity (threshold)
    exposure = (flakes - 0.4) * 2.0
    exposure = np.clip(exposure, 0, 1)
    
    # Substrate color (bare metal - darker, cooler)
    substrate = np.array([0.3, 0.35, 0.4])
    
    # Flake edges show rust/corrosion
    edge_rust = np.abs(np.sin(flakes * np.pi * 12)) * exposure * 0.25
    
    effect = np.stack([
        np.clip(paint[:, :, 0] * (1.0 - exposure * 0.8) + substrate[0] * exposure + edge_rust, 0, 1),
        np.clip(paint[:, :, 1] * (1.0 - exposure * 0.8) + substrate[1] * exposure + edge_rust * 0.8, 0, 1),
        np.clip(paint[:, :, 2] * (1.0 - exposure * 0.8) + substrate[2] * exposure + edge_rust * 0.6, 0, 1)
    ], axis=2)
    
    blend = pm * mask
    result = np.clip(
        paint * (1.0 - blend[:, :, np.newaxis]) + 
        effect * (blend[:, :, np.newaxis]),
        0, 1
    )
    return result.astype(np.float32)


def spec_destroyed_coat(shape, seed, sm, base_m, base_r):
    """
    Spec for destroyed: zero gloss in exposed areas, exposed substrate
    is very rough.
    """
    h, w = shape
    base_m = base_m / 255.0
    base_r = base_r / 255.0
    
    flakes = multi_scale_noise((h, w), [4, 8, 16], [0.35, 0.33, 0.32], seed + 3061)
    exposure = np.clip((flakes - 0.4) * 2.0, 0, 1)
    
    # Remaining paint gloss only in unexposed areas
    M = np.clip(base_m * (1.0 - exposure), 0, 1)
    
    # Roughness extreme in exposed areas
    R = np.clip(base_r * (1.0 - exposure * 0.3) + exposure * 0.95, 0, 1)
    
    CC = np.ones((h, w), dtype=np.float32) * 0.4
    
    return (np.clip(M.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(R.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(CC.astype(np.float32) * 255.0, 0, 255).astype(np.float32))


# =============================================================================
# OXIDIZED - General iron oxide rust formation (Fe2O3)
# =============================================================================

def paint_oxidized_v2(paint, shape, mask, seed, pm, bb):
    """
    Iron oxide rust: reddish-brown oxidation with surface layering,
    uses exponential growth model for rust depth variation.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Oxidation nucleation sites (rust starts at defects)
    nucleation = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 3070)
    nucleation = np.clip(nucleation, 0, 1)
    
    # Rust spreading (exponential growth)
    spreading = np.clip(nucleation, 0, None) ** 0.7 * 0.6
    
    # Surface oxidation layer depth
    oxide_depth = spreading * 0.5
    
    # Rust color (Fe2O3 - reddish-brown)
    rust_color = np.array([0.7, 0.35, 0.15])
    
    effect = np.stack([
        np.clip(paint[:, :, 0] * (1.0 - oxide_depth * 0.4) + rust_color[0] * oxide_depth * 0.6, 0, 1),
        np.clip(paint[:, :, 1] * (1.0 - oxide_depth * 0.5) + rust_color[1] * oxide_depth * 0.6, 0, 1),
        np.clip(paint[:, :, 2] * (1.0 - oxide_depth * 0.6) + rust_color[2] * oxide_depth * 0.6, 0, 1)
    ], axis=2)
    
    blend = pm * mask
    result = np.clip(
        paint * (1.0 - blend[:, :, np.newaxis]) + 
        effect * (blend[:, :, np.newaxis]),
        0, 1
    )
    return result.astype(np.float32)


def spec_oxidized(shape, seed, sm, base_m, base_r):
    """
    Spec for oxidized: gloss dulled by rust layer, moderate roughness
    increase from oxide texture.
    """
    h, w = shape
    base_m = base_m / 255.0
    base_r = base_r / 255.0
    
    oxide = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 3071)
    oxide = np.clip(oxide, 0, 1) ** 0.7
    
    M = np.clip(base_m * (0.5 + oxide * 0.3), 0, 1)
    
    R = np.clip(base_r + oxide * 0.4, 0, 1)
    
    CC = np.ones((h, w), dtype=np.float32) * 0.55
    
    return (np.clip(M.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(R.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(CC.astype(np.float32) * 255.0, 0, 255).astype(np.float32))


# =============================================================================
# OXIDIZED_COPPER - Cupric oxide green patina (Cu2O → CuO → CuCO3)
# =============================================================================

def paint_oxidized_copper_v2(paint, shape, mask, seed, pm, bb):
    """
    Copper oxidation progression: Cu2O (red) → CuO (black) → CuCO3 (green patina).
    Uses time-evolution modeling.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Oxidation age (different areas at different stages)
    age = multi_scale_noise((h, w), [3, 6, 12], [0.5, 0.3, 0.2], seed + 3080)
    age = np.clip(age, 0, 1)
    
    # Stage progression: young (red) -> old (green)
    young_stage = (1.0 - age) * 0.5  # Cu2O red
    old_stage = age * 0.5  # CuCO3 green
    
    # Color progression
    red_tone = young_stage[:, :, np.newaxis] * np.array([0.8, 0.3, 0.1])[np.newaxis, np.newaxis, :]
    green_tone = old_stage[:, :, np.newaxis] * np.array([0.2, 0.6, 0.3])[np.newaxis, np.newaxis, :]
    
    patina_color = red_tone + green_tone
    patina_strength = young_stage + old_stage
    
    effect = np.stack([
        np.clip(paint[:, :, 0] * (1.0 - patina_strength * 0.5) + patina_color[:,:,0] * 0.7, 0, 1),
        np.clip(paint[:, :, 1] * (1.0 - patina_strength * 0.4) + patina_color[:,:,1] * 0.7, 0, 1),
        np.clip(paint[:, :, 2] * (1.0 - patina_strength * 0.6) + patina_color[:,:,2] * 0.7, 0, 1)
    ], axis=2)
    
    blend = pm * mask
    result = np.clip(
        paint * (1.0 - blend[:, :, np.newaxis]) + 
        effect * (blend[:, :, np.newaxis]),
        0, 1
    )
    return result.astype(np.float32)


def spec_oxidized_copper(shape, seed, sm, base_m, base_r):
    """
    Spec for copper patina: gloss reduced by oxidation layers,
    varying roughness by age stage.
    """
    h, w = shape
    base_m = base_m / 255.0
    base_r = base_r / 255.0
    
    age = multi_scale_noise((h, w), [3, 6], [0.6, 0.4], seed + 3081)
    age = np.clip(age, 0, 1)
    
    # Young oxidation more reflective, old patina duller
    M = np.clip(base_m * (0.6 + age * 0.2), 0, 1)
    
    R = np.clip(base_r + age * 0.35, 0, 1)
    
    CC = np.ones((h, w), dtype=np.float32) * 0.6
    
    return (np.clip(M.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(R.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(CC.astype(np.float32) * 255.0, 0, 255).astype(np.float32))

# =============================================================================
# SALT_CORRODED - Galvanic corrosion from salt spray exposure
# =============================================================================

def paint_salt_corroded_v2(paint, shape, mask, seed, pm, bb):
    """
    Salt spray galvanic corrosion: aggressive pitting with white salt
    residue halos, electrochemical cell activity creates clustered damage.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Galvanic cells (corrosion centers)
    cells = multi_scale_noise((h, w), [3, 6, 12], [0.4, 0.3, 0.3], seed + 3090)
    cells = np.clip(cells, 0, 1)
    
    # Pit depth from cell activity
    pit_depth = np.clip(cells, 0, None) ** 1.3 * 0.5
    
    # Salt halo around pits (white residue)
    halo = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 3091)
    halo = np.clip(halo * cells, 0, 1)
    
    # Corrosion color (dark pit + white halo)
    pit_color = np.array([0.2, 0.3, 0.35])
    salt_color = np.array([0.9, 0.9, 0.88])
    
    effect = np.stack([
        np.clip(paint[:, :, 0] * (1.0 - pit_depth * 0.6) + pit_color[0] * pit_depth * 0.5 + salt_color[0] * halo * 0.3, 0, 1),
        np.clip(paint[:, :, 1] * (1.0 - pit_depth * 0.6) + pit_color[1] * pit_depth * 0.5 + salt_color[1] * halo * 0.3, 0, 1),
        np.clip(paint[:, :, 2] * (1.0 - pit_depth * 0.6) + pit_color[2] * pit_depth * 0.5 + salt_color[2] * halo * 0.3, 0, 1)
    ], axis=2)
    
    blend = pm * mask
    result = np.clip(
        paint * (1.0 - blend[:, :, np.newaxis]) + 
        effect * (blend[:, :, np.newaxis]),
        0, 1
    )
    return result.astype(np.float32)


def spec_salt_corroded(shape, seed, sm, base_m, base_r):
    """
    Spec for salt corrosion: pitting creates dramatic gloss loss,
    high roughness from galvanic pitting pattern.
    """
    h, w = shape
    base_m = base_m / 255.0
    base_r = base_r / 255.0
    
    cells = multi_scale_noise((h, w), [3, 6], [0.6, 0.4], seed + 3092)
    cells = np.clip(cells, 0, 1)
    
    pit_damage = np.clip(cells, 0, None) ** 1.3
    M = np.clip(base_m * (0.35 + pit_damage * 0.2), 0, 1)
    
    R = np.clip(base_r + pit_damage * 0.55, 0, 1)
    
    CC = np.ones((h, w), dtype=np.float32) * 0.45
    
    return (np.clip(M.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(R.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(CC.astype(np.float32) * 255.0, 0, 255).astype(np.float32))


# =============================================================================
# SUN_BAKED - Solar UV photodegradation with chalking and color fade
# =============================================================================

def paint_sun_baked_v2(paint, shape, mask, seed, pm, bb):
    """
    Sun baking: intense UV exposure causes polymer crosslinking failure,
    chalking, and color saturation loss.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # UV intensity map (stronger at top/center)
    y, x = get_mgrid((h, w))
    uv_map = (1.0 - (np.abs(x - w/2) + np.abs(y - h/2)) / (w + h) * 2) * 0.7 + 0.3
    
    # Photodegradation (intensity-based)
    degradation = multi_scale_noise((h, w), [4, 8, 16], [0.4, 0.3, 0.3], seed + 3100)
    degradation = np.clip(degradation, 0, 1)
    
    # Combined sun damage
    sun_damage = uv_map * degradation * 0.7
    
    # Saturation loss (colors desaturate)
    gray = (paint[:, :, 0] + paint[:, :, 1] + paint[:, :, 2]) / 3.0
    
    effect = np.stack([
        np.clip(paint[:, :, 0] * (1.0 - sun_damage * 0.5) + gray * sun_damage * 0.3, 0, 1),
        np.clip(paint[:, :, 1] * (1.0 - sun_damage * 0.5) + gray * sun_damage * 0.3, 0, 1),
        np.clip(paint[:, :, 2] * (1.0 - sun_damage * 0.6) + gray * sun_damage * 0.2, 0, 1)
    ], axis=2)
    
    blend = pm * mask
    result = np.clip(
        paint * (1.0 - blend[:, :, np.newaxis]) + 
        effect * (blend[:, :, np.newaxis]),
        0, 1
    )
    return result.astype(np.float32)


def spec_sun_baked(shape, seed, sm, base_m, base_r):
    """
    Spec for sun baked: severe gloss loss from UV crosslinking,
    high roughness from chalking.
    """
    h, w = shape
    base_m = base_m / 255.0
    base_r = base_r / 255.0
    
    y, x = get_mgrid((h, w))
    uv_map = (1.0 - (np.abs(x - w/2) + np.abs(y - h/2)) / (w + h) * 2) * 0.7 + 0.3
    
    degrade = multi_scale_noise((h, w), [4, 8], [0.6, 0.4], seed + 3101)
    
    sun_damage = uv_map * degrade
    M = np.clip(base_m * (0.2 + sun_damage * 0.2), 0, 1)
    
    R = np.clip(base_r + sun_damage * 0.5, 0, 1)
    
    CC = np.ones((h, w), dtype=np.float32) * 0.3
    
    return (np.clip(M.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(R.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(CC.astype(np.float32) * 255.0, 0, 255).astype(np.float32))


# =============================================================================
# SUN_FADE - Directional UV fade gradient (top-down exposure)
# =============================================================================

def paint_sun_fade_v2(paint, shape, mask, seed, pm, bb):
    """
    Sun fade: unidirectional UV exposure creates strong top-to-bottom
    gradient, intense color desaturation in exposed areas.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Top-down UV gradient
    y, x = get_mgrid((h, w))
    uv_gradient = 1.0 - (y / h) ** 0.8
    
    # Local variation in fade intensity
    fade_noise = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 3110)
    fade_noise = np.clip(fade_noise, 0, 1)
    
    fade_intensity = uv_gradient * fade_noise * 0.8
    
    # Desaturation via color shift toward gray
    gray = (paint[:, :, 0] + paint[:, :, 1] + paint[:, :, 2]) / 3.0
    
    # Slight yellow shift (aged appearance)
    aged_color = np.array([1.0, 0.98, 0.9])
    
    effect = np.stack([
        np.clip(paint[:, :, 0] * (1.0 - fade_intensity * 0.6) + aged_color[0] * fade_intensity * 0.2, 0, 1),
        np.clip(paint[:, :, 1] * (1.0 - fade_intensity * 0.6) + aged_color[1] * fade_intensity * 0.2, 0, 1),
        np.clip(paint[:, :, 2] * (1.0 - fade_intensity * 0.7) + aged_color[2] * fade_intensity * 0.1, 0, 1)
    ], axis=2)
    
    blend = pm * mask
    result = np.clip(
        paint * (1.0 - blend[:, :, np.newaxis]) + 
        effect * (blend[:, :, np.newaxis]),
        0, 1
    )
    return result.astype(np.float32)


def spec_sun_fade(shape, seed, sm, base_m, base_r):
    """
    Spec for sun fade: gloss loss proportional to fade gradient,
    moderate roughness increase.
    """
    h, w = shape
    base_m = base_m / 255.0
    base_r = base_r / 255.0
    
    y, _ = get_mgrid((h, w))
    uv_gradient = 1.0 - (y / h) ** 0.8
    
    fade_noise = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 3111)
    
    fade_effect = uv_gradient * fade_noise
    M = np.clip(base_m * (0.4 + fade_effect * 0.3), 0, 1)
    
    R = np.clip(base_r + fade_effect * 0.35, 0, 1)
    
    CC = np.ones((h, w), dtype=np.float32) * 0.5
    
    return (np.clip(M.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(R.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(CC.astype(np.float32) * 255.0, 0, 255).astype(np.float32))

# =============================================================================
# TRACK_WORN - Abrasion wear pattern from racing contact zones
# =============================================================================

def paint_track_worn_v2(paint, shape, mask, seed, pm, bb):
    """
    Track wear: directional abrasion from racing contact, creates linear
    wear patterns with rounded contact zones. Uses directional flow field.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Contact zone centers (racing line pattern)
    contact_zones = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 3120)
    contact_zones = np.clip(contact_zones, 0, 1)
    
    # Directional wear flow (diagonal racing line)
    y, x = get_mgrid((h, w))
    racing_line = (y + x) / (h + w)
    
    # Wear intensity combines contact zones with directional flow
    wear_intensity = contact_zones * (0.5 + racing_line * 0.5)
    wear_depth = np.clip(wear_intensity, 0, None) ** 0.9 * 0.45
    
    # Metal substrate exposure in wear zones
    metal_color = np.array([0.35, 0.38, 0.42])
    
    effect = np.stack([
        np.clip(paint[:, :, 0] * (1.0 - wear_depth * 0.7) + metal_color[0] * wear_depth * 0.5, 0, 1),
        np.clip(paint[:, :, 1] * (1.0 - wear_depth * 0.7) + metal_color[1] * wear_depth * 0.5, 0, 1),
        np.clip(paint[:, :, 2] * (1.0 - wear_depth * 0.7) + metal_color[2] * wear_depth * 0.5, 0, 1)
    ], axis=2)
    
    blend = pm * mask
    result = np.clip(
        paint * (1.0 - blend[:, :, np.newaxis]) + 
        effect * (blend[:, :, np.newaxis]),
        0, 1
    )
    return result.astype(np.float32)


def spec_track_worn(shape, seed, sm, base_m, base_r):
    """
    Spec for track wear: gloss loss in high-wear contact zones,
    extreme roughness in wear patches from metal exposure.
    """
    h, w = shape
    base_m = base_m / 255.0
    base_r = base_r / 255.0
    
    contact = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 3121)
    contact = np.clip(contact, 0, 1)
    
    y, x = get_mgrid((h, w))
    racing_line = (y + x) / (h + w)
    
    wear = contact * (0.5 + racing_line * 0.5)
    wear_depth = np.clip(wear, 0, None) ** 0.9
    
    # Paint remains glossy but wear zones are matte
    M = np.clip(base_m * (1.0 - wear_depth * 0.8), 0, 1)
    
    R = np.clip(base_r * (1.0 - wear_depth * 0.3) + wear_depth * 0.85, 0, 1)
    
    CC = np.ones((h, w), dtype=np.float32) * 0.6
    
    return (np.clip(M.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(R.astype(np.float32) * 255.0, 0, 255).astype(np.float32), np.clip(CC.astype(np.float32) * 255.0, 0, 255).astype(np.float32))


# =============================================================================
# VINTAGE_CHROME - 1950s chrome with warm tarnish and cloudy oxidation
# =============================================================================

def paint_vintage_chrome_v2(paint, shape, mask, seed, pm, bb):
    """
    Vintage chrome: localized tarnish zones darken and warm the surface,
    cloudy oxidation creates milky patches over reflective chrome base.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    tarnish = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 3200)
    tarnish = np.clip(tarnish, 0, 1) ** 1.4

    oxidation = multi_scale_noise((h, w), [4, 8, 16], [0.35, 0.35, 0.3], seed + 3201)
    cloud = np.clip((oxidation - 0.55) * 4.0, 0, 1)

    chrome_base = 0.72 + multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 3202) * 0.08
    tarnish_r = chrome_base - tarnish * 0.15 + tarnish * 0.04
    tarnish_g = chrome_base - tarnish * 0.18
    tarnish_b = chrome_base - tarnish * 0.22
    effect_r = np.clip(tarnish_r + cloud * 0.10, 0, 1)
    effect_g = np.clip(tarnish_g + cloud * 0.08, 0, 1)
    effect_b = np.clip(tarnish_b + cloud * 0.06, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    return result.astype(np.float32)


def spec_vintage_chrome(shape, seed, sm, base_m, base_r):
    """
    Vintage chrome spec: high metallic where chrome survives, dropping
    sharply in tarnish/oxidation zones. Roughness rises in cloudy patches.
    """
    h, w = shape
    base_m = base_m / 255.0
    base_r = base_r / 255.0

    tarnish = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 3200)
    tarnish = np.clip(tarnish, 0, 1) ** 1.4
    cloud = multi_scale_noise((h, w), [4, 8, 16], [0.35, 0.35, 0.3], seed + 3201)
    cloud = np.clip((cloud - 0.55) * 4.0, 0, 1)

    M = np.clip(base_m * (1.0 - tarnish * 0.5 - cloud * 0.3), 0, 1)
    R = np.clip(base_r + tarnish * 0.15 + cloud * 0.35, 0, 1)
    CC = np.clip(0.08 + cloud * 0.12, 0, 1)

    return (np.clip(M * 255.0, 0, 255).astype(np.float32),
            np.clip(R * 255.0, 0, 255).astype(np.float32),
            np.clip(CC * 255.0, 0, 255).astype(np.float32))
