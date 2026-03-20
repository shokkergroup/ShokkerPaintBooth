"""
Shokker Paint Booth V5 - Finish Basic Paint Functions Module
Foundation bases (Gloss, Matte, Satin, Eggshell, Primer, etc.)

DESIGN RULE: Foundation bases are SOLID. Their paint_fn must NOT apply any
visible noise, texture, grain, or pattern to the paint color or spec map.
All texture variation lives in the BASE_REGISTRY M/R/CC values + Perlin noise
keys, NOT in these paint functions.

The paint_fn here only handles:
  - Subtle contrast/gamma for the base sheen level
  - Zero noise or multi_scale_noise calls on Foundation IDs

SPEC RETURN CONTRACT: base_spec_fn must return (M_arr, R_arr, CC_arr)
where all values are in 0-255 float32 range.
  Channel 0 (spec[:,:,0]) = Metallic (M)
  Channel 1 (spec[:,:,1]) = Roughness (R)
  Channel 2 (spec[:,:,2]) = Clearcoat (CC)
"""

import numpy as np
from engine.core import multi_scale_noise, get_mgrid


# ============================================================================
# BLACKOUT - Total light absorption matte black
# ============================================================================

def paint_blackout_v2(paint, shape, mask, seed, pm, bb):
    """Near-zero reflectance total black absorption."""
    h, w = shape[:2] if len(shape) > 2 else shape
    darkness = np.ones((h, w), dtype=np.float32) * 0.02
    effect = np.stack([darkness, darkness, darkness], axis=2)
    blend = pm * (bb[:,:,np.newaxis] ** 2.2)
    return np.clip(paint * (1.0 - mask[:,:,np.newaxis] * blend) +
                   effect * (mask[:,:,np.newaxis] * blend), 0, 1).astype(np.float32)

def spec_blackout(shape, seed, sm, base_m, base_r):
    """Blackout spec: CC=200 maximum degradation = near-dead flat matte."""
    h, w = shape
    z   = np.zeros((h, w), dtype=np.float32)
    cc  = np.full((h, w), 200.0, dtype=np.float32)
    return (z, z, cc)


# ============================================================================
# CERAMIC - Ceramic glaze (handled by paint_ceramic_gloss in spec_paint)
# ============================================================================

def paint_ceramic_v2(paint, shape, mask, seed, pm, bb):
    """Ceramic: pure pass-through, no texture or effect in base layer."""
    return paint.copy()

def spec_ceramic(shape, seed, sm, base_m, base_r):
    """Ceramic spec: high gloss, minimal roughness. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 16.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# CHAMELEON - Multi-layer interference color shift film
# ============================================================================

def paint_chameleon_v2(paint, shape, mask, seed, pm, bb):
    """Chameleon: pass-through, colour shift handled by spec."""
    return paint.copy()

def spec_chameleon(shape, seed, sm, base_m, base_r):
    """Chameleon spec: high gloss, moderate metallic. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 16.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# CLEAR_MATTE - Matte clearcoat, solid, no texture
# ============================================================================

def paint_clear_matte_v2(paint, shape, mask, seed, pm, bb):
    """Clear matte: solid flat finish, no texture."""
    darken = np.clip(paint * 0.87, 0, 1)
    flat = np.clip((darken - 0.5) * 0.72 + 0.5, 0, 1)
    return flat * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_clear_matte(shape, seed, sm, base_m, base_r):
    """Clear matte spec: CC=130 visibly flat. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 130.0 / 255.0,  dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# EGGSHELL - Low-sheen eggshell finish, SOLID
# ============================================================================

def paint_eggshell_v2(paint, shape, mask, seed, pm, bb):
    """Eggshell: slight desat, no grain, no noise."""
    gray = paint.mean(axis=2, keepdims=True)
    desat = np.clip(paint * 0.92 + gray * 0.08, 0, 1)
    return desat * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_eggshell(shape, seed, sm, base_m, base_r):
    """Eggshell spec: CC=100 low sheen. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 100.0 / 255.0,  dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# FLAT_BLACK - Flat black with zero specular component
# ============================================================================

def paint_flat_black_v2(paint, shape, mask, seed, pm, bb):
    """Flat black: pure absorption."""
    black = np.zeros_like(paint)
    edge = bb * 0.04 * mask
    black[:, :, 0] = edge
    black[:, :, 1] = edge
    black[:, :, 2] = edge
    return np.clip(black, 0, 1)

def spec_flat_black(shape, seed, sm, base_m, base_r):
    """Flat black spec: CC=220 near-maximum degradation = dead flat. Returns (M, R, CC)."""
    h, w = shape
    z   = np.zeros((h, w), dtype=np.float32)
    cc  = np.full((h, w), 220.0, dtype=np.float32)
    return (z, z, cc)


# ============================================================================
# FROZEN / FROZEN_MATTE - Pass through paint, spec handles the surface
# ============================================================================

def paint_frozen_v2(paint, shape, mask, seed, pm, bb):
    """Frozen metallic: pass-through paint, spec drives it."""
    return paint.copy()

def spec_frozen(shape, seed, sm, base_m, base_r):
    """Frozen spec: moderate matte metallic, flat. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 16.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))

def paint_frozen_matte_v2(paint, shape, mask, seed, pm, bb):
    """Frozen matte: pass-through, spec handles it."""
    return paint.copy()

def spec_frozen_matte(shape, seed, sm, base_m, base_r):
    """Frozen matte spec: high roughness, flat. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 80.0 / 255.0,    dtype=np.float32)  # CC=80 frozen matte
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# GLOSS - Standard high-gloss finish, SOLID
# ============================================================================

def paint_gloss_v2(paint, shape, mask, seed, pm, bb):
    """Gloss: subtle contrast only, no texture."""
    contrasted = np.clip((paint - 0.5) * 1.04 + 0.5, 0, 1)
    ping = np.clip(bb - 0.9, 0, 1) * 0.12 * pm
    return np.clip(contrasted + (ping * np.ones_like(mask))[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)

def spec_gloss(shape, seed, sm, base_m, base_r):
    """Gloss spec: maximum reflectance, minimum roughness. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 16.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# IRIDESCENT - Pass through (spec_paint handles the shift)
# ============================================================================

def paint_iridescent_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_iridescent(shape, seed, sm, base_m, base_r):
    """Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 16.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# LIQUID_OBSIDIAN - Pass through (deep black, spec handles it)
# ============================================================================

def paint_liquid_obsidian_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_liquid_obsidian(shape, seed, sm, base_m, base_r):
    """Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 16.0 / 255.0,    dtype=np.float32)  # CC=16 glossy obsidian
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# LIVING_MATTE - Organic matte, SOLID
# ============================================================================

def paint_living_matte_v2(paint, shape, mask, seed, pm, bb):
    """Living matte: solid organic matte, no Perlin variation."""
    darken = np.clip(paint * 0.88, 0, 1)
    flat = np.clip((darken - 0.5) * 0.75 + 0.5, 0, 1)
    return flat * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_living_matte(shape, seed, sm, base_m, base_r):
    """Living matte spec: CC=140 organic flat matte. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 140.0 / 255.0,  dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# MATTE - Standard matte finish, SOLID
# ============================================================================

def paint_matte_v2(paint, shape, mask, seed, pm, bb):
    """Matte: flat, no noise, no pattern."""
    darken = np.clip(paint * 0.85, 0, 1)
    flat = np.clip((darken - 0.5) * 0.70 + 0.5, 0, 1)
    return flat * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_matte(shape, seed, sm, base_m, base_r):
    """Matte spec: CC=160 heavily degraded = no visible sheen. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 160.0 / 255.0,  dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# MIRROR_GOLD - Warm gold mirror (subtle tint, no texture)
# ============================================================================

def paint_mirror_gold_v2(paint, shape, mask, seed, pm, bb):
    """Mirror gold: subtle warm gold/copper tint over base, no noise."""
    out = np.clip(paint + 0.0, 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0) * mask
    # Warm shift: more red/gold, less blue
    out[:, :, 0] = np.clip(out[:, :, 0] + 0.06 * blend, 0, 1)
    out[:, :, 1] = np.clip(out[:, :, 1] + 0.02 * blend, 0, 1)
    out[:, :, 2] = np.clip(out[:, :, 2] - 0.03 * blend, 0, 1)
    out = np.clip(out + (bb * 0.5 * blend)[:, :, np.newaxis], 0, 1)
    return out

def spec_mirror_gold(shape, seed, sm, base_m, base_r):
    """Mirror gold: max metallic, near-zero roughness, CC=16 (max clearcoat)."""
    h, w = shape
    M = np.full((h, w), 255.0, dtype=np.float32)
    R = np.full((h, w), 2.0, dtype=np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)  # CC=16 max clearcoat
    return M, R, CC


# ============================================================================
# NOISE_SCALES / PERLIN - pass through (these are test/debug bases)
# ============================================================================

def paint_noise_scales_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_noise_scales(shape, seed, sm, base_m, base_r):
    """Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 16.0 / 255.0,    dtype=np.float32)  # CC=16 default gloss
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))

def paint_perlin_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_perlin(shape, seed, sm, base_m, base_r):
    """Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 16.0 / 255.0,    dtype=np.float32)  # CC=16 default gloss
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# ORANGE_PEEL_GLOSS - pass through (Perlin noise keys handle surface)
# ============================================================================

def paint_orange_peel_gloss_v2(paint, shape, mask, seed, pm, bb):
    """Orange peel gloss: visible dimple texture simulating spray coating micro-texture."""
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    # Generate cellular dimple pattern (orange peel texture)
    # Use two scales of noise to create 6-8px cell-like bumps
    dimple_coarse = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 8800)
    dimple_fine = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 8801)
    # Create cellular bumps via thresholded noise
    cells = np.sin(dimple_coarse * np.pi * 12.0) * 0.5 + 0.5  # ~6-8px cells
    cells = cells * (0.8 + dimple_fine * 0.2)  # modulate with finer detail
    # Orange peel effect: subtle brightness variation following cell pattern
    texture = cells * 0.12 * pm  # visible but not overwhelming
    # Apply dimple texture to paint (highlights on dimple peaks, darker in valleys)
    contrasted = np.clip((paint - 0.5) * 1.06 + 0.5, 0, 1)  # slightly more contrast than before
    effect = np.clip(contrasted + texture[:,:,np.newaxis] - 0.06, 0, 1)
    result = effect * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])
    return np.clip(result, 0, 1).astype(np.float32)

def spec_orange_peel_gloss(shape, seed, sm, base_m, base_r):
    """Orange peel spec: fine cellular bumps (6-8px cells) simulating spray coating micro-texture."""
    h, w = shape
    # Cellular orange peel texture in spec (this IS the orange peel finish)
    dimple_coarse = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 8800)
    dimple_fine = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 8801)
    # Cell pattern: sine-based creates regular bumps
    cells = np.sin(dimple_coarse * np.pi * 12.0) * 0.5 + 0.5
    cells = cells * (0.8 + dimple_fine * 0.2)
    # M: base metallic with slight cell variation
    M = np.clip(base_m + cells * 15.0 * sm - 7.0, 0, 255).astype(np.float32)
    # R: the key channel - orange peel creates roughness variation (bumpy micro-texture)
    # Peaks are smoother (light catches), valleys are rougher
    R = np.clip(base_r + (1.0 - cells) * 30.0 * sm + cells * 5.0 * sm, 0, 255).astype(np.float32)
    # CC: standard glossy with micro-texture variation
    CC = np.clip(16.0 + (1.0 - cells) * 12.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


# ============================================================================
# ORGANIC_METAL - pass through (Perlin + noise_M/R handle the surface)
# ============================================================================

def paint_organic_metal_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_organic_metal(shape, seed, sm, base_m, base_r):
    """Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 16.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# PIANO_BLACK - near-black, no texture
# ============================================================================

def paint_piano_black_v2(paint, shape, mask, seed, pm, bb):
    """Piano black: deep near-black, no noise."""
    deep = np.clip(paint * 0.06, 0, 1)
    return deep * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_piano_black(shape, seed, sm, base_m, base_r):
    """Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 16.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# PRIMER - Solid primer grey, SOLID
# ============================================================================

def paint_primer_v2(paint, shape, mask, seed, pm, bb):
    """Primer: solid grey, no grain."""
    gray = np.full_like(paint, 0.42)
    primer = np.clip(paint * 0.25 + gray * 0.75, 0, 1)
    return primer * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_primer(shape, seed, sm, base_m, base_r):
    """Primer spec: CC=180 near-maximum degradation = zero sheen. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 180.0 / 255.0,  dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# SATIN - Standard satin finish, SOLID
# ============================================================================

def paint_satin_v2(paint, shape, mask, seed, pm, bb):
    """Satin: soft sheen, no pattern."""
    soft = np.clip(paint * 0.97 + 0.02, 0, 1)
    return soft * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_satin(shape, seed, sm, base_m, base_r):
    """Satin spec: CC=70 moderate clearcoat degradation. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 70.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# SATIN_METAL - pass through (brushed_grain handles it)
# ============================================================================

def paint_satin_metal_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_satin_metal(shape, seed, sm, base_m, base_r):
    """Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 16.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# SCUFFED_SATIN - Solid satin, no scuff texture pattern
# ============================================================================

def paint_scuffed_satin_v2(paint, shape, mask, seed, pm, bb):
    """Scuffed satin: clean foundation, no pattern."""
    soft = np.clip(paint * 0.96 + 0.03, 0, 1)
    return soft * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_scuffed_satin(shape, seed, sm, base_m, base_r):
    """Scuffed satin spec: CC=90 rougher than satin. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 90.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# SEMI_GLOSS - Semi-gloss finish, SOLID
# ============================================================================

def paint_semi_gloss_v2(paint, shape, mask, seed, pm, bb):
    """Semi-gloss: subtle contrast only, no noise."""
    contrasted = np.clip((paint - 0.5) * 1.02 + 0.5, 0, 1)
    return contrasted * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_semi_gloss(shape, seed, sm, base_m, base_r):
    """Semi-gloss spec: CC=40 mild dulling. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 40.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# SILK - Solid silk sheen, no weave texture
# ============================================================================

def paint_silk_v2(paint, shape, mask, seed, pm, bb):
    """Silk: soft lift, no weave pattern."""
    soft = np.clip(paint + 0.03 * pm * mask[:,:,np.newaxis], 0, 1)
    return soft * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_silk(shape, seed, sm, base_m, base_r):
    """Silk spec: CC=60 smooth low-reflection sheen. Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 60.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# TERRAIN_CHROME - pass through (Perlin noise keys handle distortion)
# ============================================================================

def paint_terrain_chrome_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_terrain_chrome(shape, seed, sm, base_m, base_r):
    """Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 16.0 / 255.0,    dtype=np.float32)  # CC=16 chrome gloss
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# VANTABLACK - Ultra-black, maximum absorption
# ============================================================================

def paint_vantablack_v2(paint, shape, mask, seed, pm, bb):
    """Vantablack: near-zero reflectance, no texture."""
    void = np.clip(paint * 0.002, 0, 1)
    return void * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_vantablack(shape, seed, sm, base_m, base_r):
    """Vantablack: CC=240 maximum degradation = absolutely dead surface."""
    h, w = shape
    z   = np.zeros((h, w), dtype=np.float32)
    cc  = np.full((h, w), 240.0, dtype=np.float32)
    return (z, z, cc)


# ============================================================================
# VOLCANIC - Pass through (volcanic_ash paint_fn handles it)
# ============================================================================

def paint_volcanic_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_volcanic(shape, seed, sm, base_m, base_r):
    """Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 70.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))


# ============================================================================
# WET_LOOK - Solid wet look, no texture
# ============================================================================

def paint_wet_look_v2(paint, shape, mask, seed, pm, bb):
    """Wet look: subtle depth gamma, no pattern."""
    wet = np.clip(paint ** 1.1, 0, 1)
    return wet * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_wet_look(shape, seed, sm, base_m, base_r):
    """Returns (M, R, CC)."""
    h, w = shape
    metal = np.full((h, w), base_m / 255.0, dtype=np.float32)
    spec  = np.full((h, w), base_r / 255.0, dtype=np.float32)
    cc    = np.full((h, w), 16.0 / 255.0,   dtype=np.float32)
    return (np.clip(metal * 255, 0, 255).astype(np.float32),
            np.clip(spec  * 255, 0, 255).astype(np.float32),
            np.clip(cc    * 255, 0, 255).astype(np.float32))
