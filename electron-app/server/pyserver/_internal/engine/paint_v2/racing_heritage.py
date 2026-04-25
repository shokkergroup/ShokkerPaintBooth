# -*- coding: utf-8 -*-
"""
RACING HERITAGE -- 14 bases, each with unique paint_fn + spec_fn
Racing-themed finishes from different motorsport disciplines.

Techniques (all different):
  asphalt_grind       - Erosion hash noise with directional scratch channels
  bullseye_chrome_rh  - Concentric ring Airy function diffraction
  checkered_chrome_rh - XOR flag modular arithmetic with chrome Fresnel
  dirt_track_satin    - Particle deposition splatter + embedded grit
  drag_strip_gloss    - Deep pour resin meniscus reflection model
  endurance_ceramic   - Thermal fatigue micro-craze network via Voronoi
  heat_shield         - Stefan-Boltzmann thermal gradient emission
  pace_car_pearl      - Multi-bounce tri-coat optical path length
  pit_lane_matte      - Rubber transfer contact mechanics model
  race_day_gloss      - Wet-look total internal reflection coating
  rally_mud           - Stochastic ballistic splatter simulation
  rat_rod_primer      - Hand-spray Poisson disc distribution model
  stock_car_enamel    - Orange peel rheology viscosity flow model
  victory_lane        - Confetti sparkle Poisson point process
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d


# ==================================================================
# ASPHALT GRIND - Erosion hash noise with directional scratches
# ==================================================================
def paint_asphalt_grind_v2(paint, shape, mask, seed, pm, bb):
    """Asphalt grind: erosion hash noise with directional scratch channels."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    rng = np.random.RandomState(seed + 1000)
    # Directional scratch channels (horizontal dominant from road contact)
    scratch_base = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 1001)
    y, x = get_mgrid((h, w))
    # Directional hash: stretch noise in X direction
    stretch_noise = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1002)
    scratch = np.clip((scratch_base - 0.55) * 6.0, 0, 1)  # thresholded scratch lines
    # Erosion darkening
    erode = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1003)
    gray = base.mean(axis=2)
    ground = np.clip(gray * 0.3 + 0.25, 0, 1)
    ground_eroded = ground - erode * 0.06 - scratch * 0.08
    effect = np.clip(np.stack([ground_eroded]*3, axis=-1), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_asphalt_grind(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    scratch = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 1001)
    erode = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1003)
    M = np.clip(30.0 + scratch * 20.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(200.0 + erode * 25.0 * sm, 15, 255).astype(np.float32)
    # CC 16=full, 255=dull. Rough asphalt = dead flat, no clearcoat
    CC = np.clip(180.0 + erode * 35.0, 16, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# BULLSEYE CHROME RH - Concentric ring Airy diffraction
# ==================================================================
def paint_bullseye_chrome_rh(paint, shape, mask, seed, pm, bb):
    """Bullseye chrome with concentric Airy diffraction ring pattern."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Airy diffraction pattern: concentric rings from circular aperture
    # Multiple bullseye centers
    rng = np.random.RandomState(seed + 1010)
    n_centers = 5
    centers = [(rng.randint(h//4, 3*h//4), rng.randint(w//4, 3*w//4)) for _ in range(n_centers)]
    ring_accum = np.zeros((h, w), dtype=np.float32)
    for cy, cx in centers:
        r = np.sqrt((y - cy)**2 + (x - cx)**2) + 1e-8
        # Airy function: (2*J1(x)/x)^2 approximated as sinc-like
        kr = r * 0.15  # spatial frequency
        airy = (np.sin(kr) / kr) ** 2
        ring_accum += airy
    ring_accum = np.clip(ring_accum / n_centers, 0, 1)
    # Chrome base + ring modulation
    gray = base.mean(axis=2)
    chrome = np.clip(gray * 0.2 + 0.65, 0, 1)
    effect = np.clip(np.stack([chrome * (0.85 + ring_accum * 0.15)]*3, axis=-1), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.42 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_bullseye_chrome_rh(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    ring = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 1011)
    M = np.clip(210.0 + ring * 35.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(3.0 + ring * 6.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + ring * 6.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# CHECKERED CHROME RH - XOR flag modular arithmetic + Fresnel
# ==================================================================
def paint_checkered_chrome_rh(paint, shape, mask, seed, pm, bb):
    """Checkered flag via XOR modular arithmetic with chrome Fresnel on white squares."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Checkered flag via XOR of row/col parity
    cell_size = 64
    row_parity = ((y / cell_size).astype(int) % 2).astype(np.float32)
    col_parity = ((x / cell_size).astype(int) % 2).astype(np.float32)
    checker = np.abs(row_parity - col_parity)  # XOR
    # Chrome Fresnel on white squares, matte black on dark
    fresnel = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 1021)
    n_chrome = 1.5 + fresnel * 0.03
    fresnel_r = ((n_chrome - 1.0) / (n_chrome + 1.0)) ** 2
    white_sq = 0.82 + fresnel_r * 0.15  # chrome white
    black_sq = 0.04 + fresnel_r * 0.02  # matte black
    surface = checker * white_sq + (1.0 - checker) * black_sq
    effect = np.clip(np.stack([surface]*3, axis=-1), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.38 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_checkered_chrome_rh(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    checker = np.abs(((y/64).astype(int)%2) - ((x/64).astype(int)%2)).astype(np.float32)
    # White squares: full clearcoat chrome. Black: matte (dull CC)
    M = np.clip(checker * 220.0 * sm + (1.0 - checker) * 10.0, 0, 255).astype(np.float32)
    R = np.clip(checker * 4.0 + (1.0 - checker) * 80.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(checker * 16.0 + (1.0 - checker) * 120.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# DIRT TRACK SATIN - Particle deposition splatter + embedded grit
# ==================================================================
def paint_dirt_track_satin_v2(paint, shape, mask, seed, pm, bb):
    """Dirt track satin with particle deposition splatter and embedded grit."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    rng = np.random.RandomState(seed + 1030)
    # Satin base (warm earth tone)
    gray = base.mean(axis=2)
    satin = np.clip(gray * 0.25 + 0.38, 0, 1)
    # Embedded grit particles (sparse, sharp)
    grit = rng.rand(h, w).astype(np.float32)
    grit_mask = (grit > 0.95).astype(np.float32) * 0.08
    # Dirt splatter (larger blotchy deposits)
    splat = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1031)
    dirt = np.clip((splat - 0.5) * 3.0, 0, 1) * 0.06
    effect_r = np.clip(satin + 0.04 - grit_mask - dirt, 0, 1)
    effect_g = np.clip(satin + 0.02 - grit_mask - dirt, 0, 1)
    effect_b = np.clip(satin - 0.03 - grit_mask - dirt, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_dirt_track_satin(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    splat = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1031)
    rng = np.random.RandomState(seed + 1030)
    grit = (rng.rand(h, w) > 0.95).astype(np.float32)
    M = np.clip(20.0 + splat * 15.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(100.0 + grit * 25.0 + splat * 20.0 * sm, 15, 255).astype(np.float32)
    # Satin = degraded clearcoat, not full gloss
    CC = np.clip(35.0 + splat * 25.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# DRAG STRIP GLOSS - Deep pour resin meniscus reflection
# ==================================================================
def paint_drag_strip_gloss_v2(paint, shape, mask, seed, pm, bb):
    """Drag strip deep pour resin with meniscus reflection and Fresnel highlights."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Self-leveling resin: meniscus creates depth gradient at edges
    depth = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 1041)
    # Fresnel from thick clear layer
    fresnel_boost = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 1042)
    n_resin = 1.55
    fresnel_r = ((n_resin - 1.0) / (n_resin + 1.0)) ** 2
    # Deep wet look: enhance color saturation + Fresnel highlight
    depth_mod = 0.90 + depth * 0.10
    effect = base * depth_mod[:,:,np.newaxis]
    effect = np.clip(effect + fresnel_r * fresnel_boost[:,:,np.newaxis] * 0.12, 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.22 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_drag_strip_gloss(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    depth = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 1041)
    M = np.clip(base_m * 0.7 + depth * 25.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(2.0 + depth * 4.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + depth * 4.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# ENDURANCE CERAMIC - Thermal fatigue micro-craze via Voronoi
# ==================================================================
def paint_endurance_ceramic_v2(paint, shape, mask, seed, pm, bb):
    """Endurance ceramic with thermal fatigue micro-craze network and heat discoloration."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Craze network from thermal cycling: Voronoi-like crack pattern
    craze = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 1051)
    # Crack detection via gradient magnitude (edges of noise cells = cracks)
    gy = np.gradient(craze, axis=0)
    gx = np.gradient(craze, axis=1)
    crack = np.sqrt(gy**2 + gx**2)
    crack = np.clip(crack / (crack.max() + 1e-8) * 3.0, 0, 1)
    # Ceramic base: off-white/cream with heat discoloration
    heat = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 1052)
    ceram_r = np.clip(0.72 + heat * 0.06 - crack * 0.10, 0, 1)
    ceram_g = np.clip(0.68 + heat * 0.04 - crack * 0.10, 0, 1)
    ceram_b = np.clip(0.60 - heat * 0.04 - crack * 0.10, 0, 1)
    effect = np.stack([ceram_r, ceram_g, ceram_b], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_endurance_ceramic(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    craze = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 1051)
    crack = np.sqrt(np.gradient(craze, axis=0)**2 + np.gradient(craze, axis=1)**2)
    crack = np.clip(crack / (crack.max() + 1e-8) * 3.0, 0, 1)
    M = np.clip(15.0 + crack * 10.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(80.0 + crack * 80.0 * sm, 15, 255).astype(np.float32)
    # Charred ceramic: degraded clearcoat over cracks
    CC = np.clip(40.0 + crack * 0.15, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# HEAT SHIELD - Stefan-Boltzmann thermal gradient emission
# ==================================================================
def paint_heat_shield_v2(paint, shape, mask, seed, pm, bb):
    """Heat shield titanium thermal gradient with Stefan-Boltzmann heat tint coloring."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Temperature gradient (hotter at bottom/center from exhaust proximity)
    y_norm = y / max(h - 1, 1)
    temp_base = np.clip(1.0 - y_norm, 0, 1)  # hot at top
    temp_var = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1061)
    temp = np.clip(temp_base * 0.7 + temp_var * 0.3, 0, 1)
    # Heat tint colors (titanium heat coloring): straw->gold->purple->blue
    # Parametric RGB based on temperature
    heat_r = np.clip(0.3 + temp * 0.5 - (temp - 0.6)**2 * 2.0, 0, 1)
    heat_g = np.clip(0.25 + temp * 0.3 - temp**2 * 0.4, 0, 1)
    heat_b = np.clip(0.4 - temp * 0.3 + (temp - 0.7)**2 * 1.5, 0, 1)
    effect = np.stack([heat_r, heat_g, heat_b], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.30 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_heat_shield(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    temp = np.clip(1.0 - y / max(h - 1, 1), 0, 1)
    M = np.clip(220.0 - temp * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + temp * 45.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + temp * 8.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# PACE CAR PEARL - Multi-bounce tri-coat optical path
# ==================================================================
def paint_pace_car_pearl_v2(paint, shape, mask, seed, pm, bb):
    """Pace car pearl tri-coat with multi-bounce optical path saturation depth."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Tri-coat: base -> pearl mid -> clear. Longer optical path = more color
    path_var = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1071)
    mica = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 1072)
    # Multi-bounce adds saturation and depth
    optical_path = 1.0 + path_var * 0.5
    pearl_shift = mica * 0.06 * optical_path
    gray = base.mean(axis=2)
    pearl_base = np.clip(gray * 0.3 + 0.50, 0, 1)
    effect = np.stack([
        np.clip(pearl_base + pearl_shift + 0.02, 0, 1),
        np.clip(pearl_base + pearl_shift * 0.7, 0, 1),
        np.clip(pearl_base + pearl_shift * 1.3 + 0.01, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.22 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_pace_car_pearl(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    mica = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 1072)
    M = np.clip(100.0 + mica * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(4.0 + mica * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + mica * 6.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# PIT LANE MATTE - Rubber transfer contact mechanics
# ==================================================================
def paint_pit_lane_matte_v2(paint, shape, mask, seed, pm, bb):
    """Pit lane industrial matte with rubber transfer contact scuff marks."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    rng = np.random.RandomState(seed + 1080)
    # Industrial matte dark surface
    gray = base.mean(axis=2)
    matte_base = np.clip(gray * 0.2 + 0.22, 0, 1)
    # Rubber transfer marks (tire scuffs from pit stops)
    # Elongated smears in random directions
    rubber_noise = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 1081)
    rubber_marks = np.clip((rubber_noise - 0.6) * 4.0, 0, 1) * 0.08
    # Scuff darkening from rubber
    effect = np.clip(np.stack([matte_base - rubber_marks]*3, axis=-1), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_pit_lane_matte(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    rubber = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 1081)
    marks = np.clip((rubber - 0.6) * 4.0, 0, 1)
    M = np.clip(8.0 + rubber * 10.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(120.0 + marks * 60.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(140.0 + rubber * 30.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# RACE DAY GLOSS - Wet-look TIR coating
# ==================================================================
def paint_race_day_gloss_v2(paint, shape, mask, seed, pm, bb):
    """Race day ultra-deep wet-look gloss with saturation boost from total internal reflection."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Ultra-deep gloss: multi-polish creates near-perfect surface
    polish = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 1091)
    # Polish removes micro-roughness, leaving only macro depth
    depth_enhance = 0.94 + polish * 0.06
    # Color saturation boost from deep clear (wet look)
    gray = base.mean(axis=2, keepdims=True)
    saturated = base + (base - gray) * 0.25  # push away from gray = more saturation
    effect = np.clip(saturated * depth_enhance[:,:,np.newaxis], 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.20 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_race_day_gloss(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    polish = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 1091)
    M = np.clip(base_m * 0.8 + polish * 20.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(1.0 + polish * 3.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + polish * 4.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# RALLY MUD - Stochastic ballistic splatter simulation
# ==================================================================
def paint_rally_mud_v2(paint, shape, mask, seed, pm, bb):
    """Rally mud stochastic ballistic splatter with dried texture and opacity variation."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    rng = np.random.RandomState(seed + 1100)
    # Ballistic splatter: mud droplets launched at various angles
    n_splats = 400
    splat_map = np.zeros((h, w), dtype=np.float32)
    sy = rng.randint(0, h, n_splats)
    sx = rng.randint(0, w, n_splats)
    radii = rng.randint(2, 12, n_splats)
    for i in range(n_splats):
        r = radii[i]
        y0, y1 = max(0, sy[i]-r), min(h, sy[i]+r)
        x0, x1 = max(0, sx[i]-r), min(w, sx[i]+r)
        opacity = rng.rand() * 0.3 + 0.1
        splat_map[y0:y1, x0:x1] = np.maximum(splat_map[y0:y1, x0:x1], opacity)
    # Dried mud texture
    dried = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 1101)
    mud_r = 0.35 + dried * 0.08
    mud_g = 0.28 + dried * 0.06
    mud_b = 0.18 + dried * 0.03
    # Blend mud over base paint
    gray = base.mean(axis=2)
    base_col = np.clip(gray * 0.3 + 0.35, 0, 1)
    effect_r = np.clip(base_col * (1.0 - splat_map) + mud_r * splat_map, 0, 1)
    effect_g = np.clip(base_col * (1.0 - splat_map) + mud_g * splat_map, 0, 1)
    effect_b = np.clip(base_col * (1.0 - splat_map) + mud_b * splat_map, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_rally_mud(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    dried = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 1101)
    splat_approx = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 1102)
    M = np.clip(15.0 + dried * 15.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(160.0 + splat_approx * 40.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(70.0 + splat_approx * 40.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# RAT ROD PRIMER - Hand-spray Poisson disc distribution
# ==================================================================
def paint_rat_rod_primer_v2(paint, shape, mask, seed, pm, bb):
    """Rat rod hand-sprayed primer with uneven coverage and drip runs."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Hand-sprayed primer: uneven coverage, visible spray overlap
    # Poisson-disc-like spray pattern (approximated with multi-scale noise)
    spray1 = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1111)
    spray2 = multi_scale_noise((h, w), [16, 32, 64], [0.35, 0.35, 0.3], seed + 1112)
    # Uneven coverage: some areas thicker, some bare
    coverage = np.clip(spray1 * 0.7 + spray2 * 0.3, 0, 1)
    # Primer gray with slight warm cast
    primer_r = 0.38 + coverage * 0.06
    primer_g = 0.36 + coverage * 0.04
    primer_b = 0.34 + coverage * 0.03
    # Drip runs where too much primer applied
    drip = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 1113)
    drip_marks = np.clip((drip - 0.7) * 4.0, 0, 1) * 0.04
    effect = np.stack([
        np.clip(primer_r + drip_marks, 0, 1),
        np.clip(primer_g + drip_marks * 0.8, 0, 1),
        np.clip(primer_b + drip_marks * 0.6, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_rat_rod_primer(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    spray = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1111)
    M = np.clip(5.0 + spray * 6.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(195.0 + spray * 25.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(185.0 + spray * 20.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# STOCK CAR ENAMEL - Orange peel rheology viscosity flow
# ==================================================================
def paint_stock_car_enamel_v2(paint, shape, mask, seed, pm, bb):
    """Stock car enamel with orange peel rheology from Rayleigh-Benard convection."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Enamel viscosity creates orange peel texture during cure
    # Rayleigh-Benard convection cells during drying
    convection = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 1121)
    # Orange peel: gentle undulation from surface tension vs viscosity
    peel = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 1122)
    peel_height = peel * 0.025  # subtle surface undulation
    # Thick enamel: good coverage, moderate gloss
    gray = base.mean(axis=2)
    enamel = np.clip(gray * 0.4 + 0.40, 0, 1)
    # Convection slightly modifies color concentration
    color_shift = convection * 0.02
    effect = np.stack([
        np.clip(enamel + peel_height + color_shift, 0, 1),
        np.clip(enamel + peel_height + color_shift * 0.8, 0, 1),
        np.clip(enamel + peel_height + color_shift * 0.5, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_stock_car_enamel(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    peel = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 1122)
    M = np.clip(6.0 + peel * 8.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + peel * 18.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + peel * 6.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# VICTORY LANE - Confetti sparkle Poisson point process
# ==================================================================
def paint_victory_lane_v2(paint, shape, mask, seed, pm, bb):
    """Victory lane celebratory gloss with confetti sparkle via Poisson point process."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    rng = np.random.RandomState(seed + 1130)
    # Poisson point process: random confetti-like sparkle points
    # Lambda (density) varies spatially
    density_field = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 1131)
    # Generate sparkle hits
    sparkle_chance = rng.rand(h, w).astype(np.float32)
    threshold = 0.92 - density_field * 0.04  # denser in some areas
    sparkle_mask = (sparkle_chance > threshold).astype(np.float32)
    # Each sparkle has random color (confetti)
    sparkle_r = sparkle_mask * rng.rand(h, w).astype(np.float32) * 0.15
    sparkle_g = sparkle_mask * rng.rand(h, w).astype(np.float32) * 0.15
    sparkle_b = sparkle_mask * rng.rand(h, w).astype(np.float32) * 0.15
    # Celebratory gloss base
    gray = base.mean(axis=2)
    gloss_base = np.clip(gray * 0.3 + 0.50, 0, 1)
    effect = np.stack([
        np.clip(gloss_base + sparkle_r, 0, 1),
        np.clip(gloss_base + sparkle_g, 0, 1),
        np.clip(gloss_base + sparkle_b, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_victory_lane(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    density = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 1131)
    rng = np.random.RandomState(seed + 1130)
    sparkle = (rng.rand(h, w) > 0.92).astype(np.float32)
    M = np.clip(60.0 + sparkle * 120.0 * sm + density * 20.0, 0, 255).astype(np.float32)
    R = np.clip(4.0 + density * 6.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + density * 6.0, 16, 255).astype(np.float32)
    return M, R, CC
