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
from engine.core import multi_scale_noise, get_mgrid, hsv_to_rgb_vec


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
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 16.0,          dtype=np.float32)
    return (M, R, CC)


# ============================================================================
# CHAMELEON - Multi-layer interference color shift film
# ============================================================================

def paint_chameleon_v2(paint, shape, mask, seed, pm, bb):
    """Chameleon: DRAMATIC dual-shift interference color rotation.
    Uses SAME noise seeds (2200, 2201) as spec_chameleon so paint and spec are married.
    Creates 3+ distinct color zones visible across the car surface via large-scale FBM
    driving a full hue rotation. Viewing-angle color shift is OBVIOUS, not subtle."""
    h, w = shape
    out = paint.copy()
    # ── Same noise fields as spec_chameleon (seed+2200, seed+2201) for marriage ──
    shift_fbm = multi_scale_noise((h, w), [8, 16, 32], [0.45, 0.35, 0.2], seed + 2200)
    sparkle   = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 2201)
    combined  = shift_fbm * 0.7 + sparkle * 0.3
    # Normalize to 0-1 range for hue mapping
    c_min, c_max = combined.min(), combined.max()
    if c_max - c_min > 1e-6:
        norm = (combined - c_min) / (c_max - c_min)
    else:
        norm = np.full_like(combined, 0.5)
    # ── 5-stop chameleon hue anchors for 3+ distinct color zones ──
    # Teal(0.48) → Purple(0.78) → Red/Magenta(0.95) → Gold(0.12) → Green(0.35) → Teal(0.48)
    stops_h = np.array([0.48, 0.78, 0.95, 0.12, 0.35, 0.48], dtype=np.float32)
    stops_s = np.array([0.90, 0.85, 0.92, 0.88, 0.85, 0.90], dtype=np.float32)
    stops_v = np.array([0.80, 0.72, 0.78, 0.85, 0.76, 0.80], dtype=np.float32)
    n_stops = len(stops_h)
    # Steepen transitions for distinct zones (gamma < 1)
    steep = np.clip(np.power(norm, 0.55), 0, 1)
    t = steep * (n_stops - 1)
    idx = np.clip(t.astype(np.int32), 0, n_stops - 2)
    frac = t - idx.astype(np.float32)
    out_h = np.zeros((h, w), dtype=np.float32)
    out_s = np.zeros((h, w), dtype=np.float32)
    out_v = np.zeros((h, w), dtype=np.float32)
    for i in range(n_stops - 1):
        seg = (idx == i)
        f = frac[seg]
        # Handle hue wraparound for segments that cross 0/1 boundary
        h0, h1 = stops_h[i], stops_h[i + 1]
        if abs(h1 - h0) > 0.5:
            # Wrap: go the short way around
            if h0 > h1:
                out_h[seg] = (h0 + (h1 + 1.0 - h0) * f) % 1.0
            else:
                out_h[seg] = (h0 - (h0 + 1.0 - h1) * f) % 1.0
        else:
            out_h[seg] = h0 * (1 - f) + h1 * f
        out_s[seg] = stops_s[i] * (1 - f) + stops_s[i + 1] * f
        out_v[seg] = stops_v[i] * (1 - f) + stops_v[i + 1] * f
    # Convert chameleon color field to RGB
    ch_r, ch_g, ch_b = hsv_to_rgb_vec(out_h, out_s, out_v)
    # ── Strong blend — paint modifier drives visibility, boosted for drama ──
    # Use pm * 0.85 for high-visibility chameleon effect (was pass-through before)
    blend = np.clip(pm * 0.85, 0.0, 1.0) * mask
    out[:, :, 0] = np.clip(out[:, :, 0] * (1 - blend) + ch_r * blend, 0, 1)
    out[:, :, 1] = np.clip(out[:, :, 1] * (1 - blend) + ch_g * blend, 0, 1)
    out[:, :, 2] = np.clip(out[:, :, 2] * (1 - blend) + ch_b * blend, 0, 1)
    return out

def spec_chameleon(shape, seed, sm, base_m, base_r):
    """Chameleon spec: DUAL-SHIFT FIX — interference film needs real M/R variation.
    Multi-layer thin-film interference creates angle-dependent color AND specular shifts.
    Flat M/R produced zero visible shift. Now: large-scale FBM drives M and R variation
    so the interference layers catch light at different intensities across the surface."""
    h, w = shape
    # Large-scale interference pattern — simulates thin-film thickness variation
    shift_fbm = multi_scale_noise((h, w), [8, 16, 32], [0.45, 0.35, 0.2], seed + 2200)
    # Secondary high-freq sparkle layer for micro-flake interference
    sparkle = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 2201)
    combined = shift_fbm * 0.7 + sparkle * 0.3
    # M: interference film is highly metallic with strong spatial variation
    # Range: base_m +/- 50, giving real visual shift across the surface
    M  = np.clip(base_m + combined * 100.0 * sm - 50.0, 0, 255).astype(np.float32)
    # R: low roughness overall but with interference-driven variation
    # Thin-film creates specular hotspots where layers align
    R  = np.clip(base_r + (1.0 - combined) * 40.0 * sm - 20.0, 0, 255).astype(np.float32)
    # CC: glossy with slight variation from film thickness
    CC = np.clip(16.0 + combined * 20.0 * sm, 16, 255).astype(np.float32)
    return (M, R, CC)


# ============================================================================
# CLEAR_MATTE - Matte clearcoat, solid, no texture
# ============================================================================

def paint_clear_matte_v2(paint, shape, mask, seed, pm, bb):
    """Clear matte: WEAK-013 FIX — precision matte clearcoat preserves base color almost perfectly.
    Matte clearcoat (BMW Frozen, Porsche Chalk style) does not tint or darken — just a tiny
    value increase (0.02) from the protective clear layer. No contrast reduction."""
    protected = np.clip(paint + 0.02, 0, 1)
    return protected * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_clear_matte(shape, seed, sm, base_m, base_r):
    """Clear matte spec: WEAK-013 FIX — precision engineered matte clearcoat (factory matte cars).
    Very uniform roughness with very low amplitude noise (±5, not ±30) — matte clearcoats are
    engineered to be consistent. Near-zero metallic with fine-scale dust flicker (0-15).
    B/CC: 180-200 (not as extreme as flat matte — slight sheen from protective clear).
    Previously: flat constant near-duplicate of living_matte. Returns (M, R, CC)."""
    h, w = shape
    # Very low amplitude FBM — engineered uniformity, not organic variation
    precision_fbm = multi_scale_noise((h, w), [16, 32, 64], [0.6, 0.3, 0.1], seed + 1300)
    # Fine-scale dust-particle noise for metallic flicker (very high frequency, tiny scale)
    dust_noise = multi_scale_noise((h, w), [64, 128], [0.7, 0.3], seed + 1301)
    # M: near-zero metallic — fine-scale dust particle flicker only (0-15 range)
    M  = np.clip(dust_noise * 15.0 * sm, 0, 255).astype(np.float32)
    # R: uniform G=200-220, very low amplitude (±5 noise) — engineered consistency
    R  = np.clip(210.0 + precision_fbm * 10.0 * sm - 5.0, 0, 255).astype(np.float32)
    # CC: 180-200 — matte clearcoat has slight sheen, not dead flat
    CC = np.clip(190.0 + precision_fbm * 10.0 - 5.0, 160, 255).astype(np.float32)
    return (M, R, CC)


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
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 100.0,         dtype=np.float32)
    return (M, R, CC)


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
    """Frozen (ice-crystal): WEAK-017 FIX — distinct from frozen_matte.
    Ice-crystal frozen effect: slight blue iridescence giving cold metallic character.
    Frozen = crystalline sparkle; frozen_matte = frosted/etched uniform surface."""
    h, w = shape[:2] if len(shape) > 2 else shape
    out = paint.copy()
    blend = np.clip(pm, 0.0, 1.0) * mask
    # Slight blue iridescence: push toward cool blue-ice
    out[:, :, 0] = np.clip(out[:, :, 0] - 0.025 * blend, 0, 1)  # reduce red slightly
    out[:, :, 2] = np.clip(out[:, :, 2] + 0.04  * blend, 0, 1)  # boost blue for icy cast
    return out

def spec_frozen(shape, seed, sm, base_m, base_r):
    """Frozen spec: WEAK-017 FIX — ice-crystal pattern using Worley-style distance to random points.
    High spec variation, crystalline roughness pattern — distinctly different from frozen_matte's
    uniform micro-roughness. Previously: flat constant output identical to frozen_matte."""
    h, w = shape
    # Worley-style crystalline pattern: distance to nearest random seed points
    rng = np.random.RandomState(seed + 7700)
    n_crystals = 80
    pts_y = rng.uniform(0, h, n_crystals).astype(np.float32)
    pts_x = rng.uniform(0, w, n_crystals).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Compute distance to nearest crystal center
    dist = np.full((h, w), 1e9, dtype=np.float32)
    for i in range(n_crystals):
        d = np.sqrt((yy - pts_y[i]) ** 2 + (xx - pts_x[i]) ** 2)
        dist = np.minimum(dist, d)
    # Normalize distance field to 0-1
    crystal = np.clip(dist / (dist.max() + 1e-6), 0, 1)
    # M: base metallic with crystalline sparkle variation (high spec variation)
    M  = np.clip(base_m + crystal * 40.0 * sm - 20.0, 0, 255).astype(np.float32)
    # R: crystalline roughness — variation at crystal boundaries creates sharp specular edges
    R  = np.clip(base_r + (1.0 - crystal) * 35.0 * sm, 0, 255).astype(np.float32)
    # CC: slight variation following crystal edges
    CC = np.clip(16.0 + crystal * 20.0 * sm, 16, 255).astype(np.float32)
    return (M, R, CC)

def paint_frozen_matte_v2(paint, shape, mask, seed, pm, bb):
    """Frozen matte (frosted glass): WEAK-017 FIX — distinct from frozen (ice-crystal).
    Frosted/etched glass surface character: slight desaturation + brightness reduction
    simulating translucency. No blue iridescence, no crystalline sparkle — uniform diffusion."""
    h, w = shape[:2] if len(shape) > 2 else shape
    out = paint.copy()
    gray = out.mean(axis=2, keepdims=True)
    # Slight desaturation for frosted translucency effect
    desaturated = out * 0.93 + gray * 0.07
    # Slight brightness reduction: frosted surface scatters and absorbs more
    dimmed = np.clip(desaturated * 0.96, 0, 1)
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, np.newaxis]
    return np.clip(out * (1.0 - blend) + dimmed * blend, 0, 1)

def spec_frozen_matte(shape, seed, sm, base_m, base_r):
    """Frozen matte spec: WEAK-017 FIX — frosted/etched glass surface, distinct from frozen.
    Uniform micro-roughness (G: 200-230), no crystalline pattern.
    Previously: flat constants identical structure to spec_frozen."""
    h, w = shape
    # Fine uniform micro-roughness: isotropic FBM at small scales (frosted surface)
    frost_fbm = multi_scale_noise((h, w), [2, 3, 5], [0.5, 0.3, 0.2], seed + 7710)
    # M: low metallic — frosted matte suppresses metallic highlights (0-30 range)
    M  = np.clip(base_m * 0.12 + frost_fbm * 10.0 * sm, 0, 255).astype(np.float32)
    # R: uniform high micro-roughness 200-230 — frosted surface is uniformly rough
    R  = np.clip(200.0 + frost_fbm * 30.0 * sm, 0, 255).astype(np.float32)
    # CC: high/flat CC (CC=160-200) — frosted = no clearcoat sparkle
    CC = np.clip(160.0 + frost_fbm * 40.0, 16, 255).astype(np.float32)
    return (M, R, CC)


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
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 16.0,          dtype=np.float32)
    return (M, R, CC)


# ============================================================================
# IRIDESCENT - Pass through (spec_paint handles the shift)
# ============================================================================

def paint_iridescent_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_iridescent(shape, seed, sm, base_m, base_r):
    """Iridescent spec: glossy with base M/R. Returns (M, R, CC)."""
    h, w = shape
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 16.0,          dtype=np.float32)
    return (M, R, CC)


# ============================================================================
# LIQUID_OBSIDIAN - Pass through (deep black, spec handles it)
# ============================================================================

def paint_liquid_obsidian_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_liquid_obsidian(shape, seed, sm, base_m, base_r):
    """Liquid obsidian spec: CC=16 glossy obsidian. Returns (M, R, CC)."""
    h, w = shape
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 16.0,          dtype=np.float32)
    return (M, R, CC)


# ============================================================================
# LIVING_MATTE - Organic matte, SOLID
# ============================================================================

def paint_living_matte_v2(paint, shape, mask, seed, pm, bb):
    """Living matte: WEAK-013 FIX — organic irregular matte with slight patchy character.
    Slight desaturation and darkening simulate a natural matte surface with irregular absorption.
    Previously: solid flat finish identical in character to clear_matte."""
    h, w = shape[:2] if len(shape) > 2 else shape
    gray = paint.mean(axis=2, keepdims=True)
    # Slight desaturation for organic chalky undertone
    desat = paint * 0.88 + gray * 0.12
    # Moderate darkening — organic matte absorbs more light than clearcoat matte
    flat = np.clip((desat - 0.5) * 0.75 + 0.5, 0, 1)
    darkened = np.clip(flat * 0.92, 0, 1)
    return darkened * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_living_matte(shape, seed, sm, base_m, base_r):
    """Living matte spec: WEAK-013 FIX — organic irregular matte with high-amplitude 3-octave FBM.
    Noticeably patchy G: 210-255, high amplitude variation — distinctly different from the
    precision-engineered uniform clear_matte. Natural surface irregularity (dirt, skin oil,
    uneven spray absorption). Previously: flat constants, near-duplicate of clear_matte. Returns (M, R, CC)."""
    h, w = shape
    # High-amplitude 3-octave FBM — organic, patchy surface variation
    organic_fbm = multi_scale_noise((h, w), [4, 8, 16], [0.5, 0.33, 0.17], seed + 1310)
    # Secondary variation layer for additional patchiness
    patch_fbm   = multi_scale_noise((h, w), [6, 12, 24], [0.5, 0.35, 0.15], seed + 1311)
    # M: near-zero metallic — slight random organic variation (0-20 range)
    M  = np.clip(organic_fbm * 20.0 * sm, 0, 255).astype(np.float32)
    # R: patchy roughness G=210-255 — high amplitude, noticeably irregular
    R  = np.clip(232.0 + organic_fbm * 45.0 * sm - 22.0, 0, 255).astype(np.float32)
    # CC: patchy coverage variation (175-230) — organic matte has uneven protective quality
    CC = np.clip(202.0 + patch_fbm * 55.0 - 27.0, 160, 255).astype(np.float32)
    return (M, R, CC)


# ============================================================================
# MATTE - Standard matte finish, SOLID
# ============================================================================

def paint_matte_v2(paint, shape, mask, seed, pm, bb):
    """Matte: WEAK-010 FIX — ~12% desaturation + slight darkening for chalky matte undertone.
    Previously: 0.85 darkening with flat contrast reduction — no color character for matte."""
    h, w = shape[:2] if len(shape) > 2 else shape
    gray = paint.mean(axis=2, keepdims=True)
    # ~12% desaturation for chalky undertone
    desat = paint * 0.88 + gray * 0.12
    # Slight contrast reduction + darkening (~5%) to simulate matte light absorption
    flat = np.clip((desat - 0.5) * 0.75 + 0.5, 0, 1)
    darkened = np.clip(flat * 0.95, 0, 1)
    return darkened * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_matte(shape, seed, sm, base_m, base_r):
    """Matte spec: WEAK-010 FIX — 3-octave FBM roughness variation G: 220-255.
    Near-zero metallic with micro-variation (R_ch: 0-30), CC near flat with noise.
    Previously: flat constants — zero spatial variation in any channel."""
    h, w = shape
    rough_fbm = multi_scale_noise((h, w), [8, 16, 32], [0.5, 0.3, 0.2], seed + 4100)
    # M: near-zero with micro-variation (0-30 range)
    M  = np.clip(rough_fbm * 30.0 * sm, 0, 255).astype(np.float32)
    # R: matte roughness 220-255 spatially varied
    R  = np.clip(220.0 + rough_fbm * 35.0 * sm, 0, 255).astype(np.float32)
    # CC: near-flat (200-230) with slight noise variation
    cc_noise = multi_scale_noise((h, w), [4, 8, 16], [0.4, 0.35, 0.25], seed + 4101)
    CC = np.clip(200.0 + cc_noise * 30.0, 160, 255).astype(np.float32)
    return (M, R, CC)


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
    """Noise scales spec: CC=16 default gloss. Returns (M, R, CC)."""
    h, w = shape
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 16.0,          dtype=np.float32)
    return (M, R, CC)

def paint_perlin_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_perlin(shape, seed, sm, base_m, base_r):
    """Perlin spec: CC=16 default gloss. Returns (M, R, CC)."""
    h, w = shape
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 16.0,          dtype=np.float32)
    return (M, R, CC)


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
    R = np.clip(base_r + (1.0 - cells) * 30.0 * sm + cells * 5.0 * sm, 15, 255).astype(np.float32)
    # CC: standard glossy with micro-texture variation
    CC = np.clip(16.0 + (1.0 - cells) * 12.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


# ============================================================================
# ORGANIC_METAL - pass through (Perlin + noise_M/R handle the surface)
# ============================================================================

def paint_organic_metal_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_organic_metal(shape, seed, sm, base_m, base_r):
    """Organic metal spec: glossy with base M/R. Returns (M, R, CC)."""
    h, w = shape
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 16.0,          dtype=np.float32)
    return (M, R, CC)


# ============================================================================
# PIANO_BLACK - near-black, no texture
# ============================================================================

def paint_piano_black_v2(paint, shape, mask, seed, pm, bb):
    """Piano black: deep near-black, no noise."""
    deep = np.clip(paint * 0.06, 0, 1)
    return deep * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_piano_black(shape, seed, sm, base_m, base_r):
    """Piano black spec: glossy with base M/R. Returns (M, R, CC)."""
    h, w = shape
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 16.0,          dtype=np.float32)
    return (M, R, CC)


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
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 180.0,         dtype=np.float32)
    return (M, R, CC)


# ============================================================================
# SATIN - Standard satin finish, SOLID
# ============================================================================

def paint_satin_v2(paint, shape, mask, seed, pm, bb):
    """Satin: soft sheen, no pattern. Preserve saturation (satin = preserve color vibrancy)."""
    soft = np.clip(paint * 0.97 + 0.02, 0, 1)
    return soft * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_satin(shape, seed, sm, base_m, base_r):
    """Satin spec: WEAK-011 FIX — real 2-octave FBM sheen variation. R: 80-140, CC: 40-90.
    Previously: flat constants, R formula produced constant 100 everywhere regardless of mask."""
    h, w = shape
    # 2-octave FBM for subtle satin sheen variation
    sheen_coarse = multi_scale_noise((h, w), [8, 16], [0.55, 0.45], seed + 3800)
    sheen_fine   = multi_scale_noise((h, w), [2,  4],  [0.6,  0.4], seed + 3801)
    sheen_fbm    = sheen_coarse * 0.7 + sheen_fine * 0.3
    # M: near-zero with micro-variation for subtle satin sheen (range 0-18)
    M  = np.clip(sheen_fbm * 18.0 * sm, 0, 255).astype(np.float32)
    # R: satin roughness 80-140 with spatial noise
    R  = np.clip(80.0 + sheen_fbm * 60.0 * sm, 0, 255).astype(np.float32)
    # CC: satin clearcoat 40-90 with slight noise (moderately glossy)
    cc_noise = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 3802)
    CC = np.clip(40.0 + cc_noise * 50.0, 16, 255).astype(np.float32)
    return (M, R, CC)


# ============================================================================
# SATIN_METAL - pass through (brushed_grain handles it)
# ============================================================================

def paint_satin_metal_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_satin_metal(shape, seed, sm, base_m, base_r):
    """Satin metal spec: glossy with base M/R. Returns (M, R, CC)."""
    h, w = shape
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 16.0,          dtype=np.float32)
    return (M, R, CC)


# ============================================================================
# SCUFFED_SATIN - Solid satin, no scuff texture pattern
# ============================================================================

def paint_scuffed_satin_v2(paint, shape, mask, seed, pm, bb):
    """Scuffed satin: WEAK-015 FIX — physically corrected to be rougher/duller than clean satin.
    Scuffing removes surface gloss: ~8% desaturation + micro-abrasion darkening.
    Previously brightened via paint*0.96+0.03 which was physically backward."""
    h, w = shape[:2] if len(shape) > 2 else shape
    gray = paint.mean(axis=2, keepdims=True)
    desat = paint * 0.92 + gray * 0.08
    darkened = np.clip(desat * 0.97, 0, 1)
    micro = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 5902)
    darkened = np.clip(darkened * (1.0 - micro[:,:,np.newaxis] * 0.04 * pm), 0, 1)
    return darkened * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_scuffed_satin(shape, seed, sm, base_m, base_r):
    """Scuffed satin spec: WEAK-015 FIX — must be ROUGHER and DULLER than plain satin.
    Plain satin: R=95, CC=70. Scuffed must be: R=160-200 (higher), CC=90-140 (higher/duller).
    Also: scuffing exposes micro-metal highlights — occasional bright spots in R (metallic) channel.
    Previously: R=90/255 flat, CC=90/255 — was actually smoother and nearly same as satin."""
    h, w = shape
    # FBM noise for scuff texture variation — seed+5902 matches paint_scuffed_satin_v2
    scuff_fbm = multi_scale_noise((h, w), [2, 4, 8], [0.45, 0.35, 0.2], seed + 5902)
    # R (Metallic): scuffing exposes micro-metal highlights — mostly low but occasional bright spots
    # Base low metallic (0-25) with sparse bright highlights (up to 180+)
    bright_spots = multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 5903)
    bright_mask  = np.clip((bright_spots - 0.88) / 0.12, 0, 1)  # top 12% become bright spots
    M = np.clip(scuff_fbm * 25.0 * sm + bright_mask * 180.0, 0, 255).astype(np.float32)
    # G (Roughness): 160-200 range — significantly rougher than base satin (R=95)
    R = np.clip(160.0 + scuff_fbm * 40.0 * sm, 15, 255).astype(np.float32)
    # B (Clearcoat): 90-140 range — duller than satin (CC=70) — scuffed = less glossy
    CC = np.clip(90.0 + scuff_fbm * 50.0, 16, 255).astype(np.float32)
    return (M, R, CC)


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
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 40.0,          dtype=np.float32)
    return (M, R, CC)


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
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 60.0,          dtype=np.float32)
    return (M, R, CC)


# ============================================================================
# TERRAIN_CHROME - pass through (Perlin noise keys handle distortion)
# ============================================================================

def paint_terrain_chrome_v2(paint, shape, mask, seed, pm, bb):
    return paint.copy()

def spec_terrain_chrome(shape, seed, sm, base_m, base_r):
    """Terrain chrome spec: CC=16 chrome gloss. Returns (M, R, CC)."""
    h, w = shape
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 16.0,          dtype=np.float32)
    return (M, R, CC)


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
    """Volcanic: darken base, warm orange/red in bright zones, cool charcoal
    in dark zones, ash texture noise overlay."""
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    gray = base.mean(axis=2)
    # Darken base significantly
    darkened = np.clip(base * 0.35, 0, 1)
    # Ash texture noise
    ash = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 6600)
    ash_fine = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 6601)
    ash_tex = ash * 0.06 + ash_fine * 0.03
    # Warm orange/red tint in bright zones, cool charcoal in dark zones
    bright_mask = np.clip((gray - 0.3) * 2.5, 0, 1)
    warm_r = 0.55 + ash * 0.12
    warm_g = 0.18 + ash * 0.06
    warm_b = 0.05 + ash * 0.03
    cool_r = 0.12 + ash * 0.04
    cool_g = 0.12 + ash * 0.03
    cool_b = 0.14 + ash * 0.03
    # Blend warm and cool based on original brightness
    bm3 = bright_mask[:, :, np.newaxis]
    warm = np.stack([warm_r, warm_g, warm_b], axis=-1)
    cool = np.stack([cool_r, cool_g, cool_b], axis=-1)
    volcanic_color = warm * bm3 + cool * (1.0 - bm3)
    # Mix volcanic color with darkened base + ash texture
    effect = np.clip(darkened * 0.4 + volcanic_color * 0.6 + ash_tex[:, :, np.newaxis], 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    result = np.clip(base * (1.0 - m3 * blend) + effect * (m3 * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.20 * pm * m3, 0, 1).astype(np.float32)

def spec_volcanic(shape, seed, sm, base_m, base_r):
    """Volcanic spec: CC=70 semi-gloss. Returns (M, R, CC)."""
    h, w = shape
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 70.0,          dtype=np.float32)
    return (M, R, CC)


# ============================================================================
# WET_LOOK - Solid wet look, no texture
# ============================================================================

def paint_wet_look_v2(paint, shape, mask, seed, pm, bb):
    """Wet look: subtle depth gamma, no pattern."""
    wet = np.clip(paint ** 1.1, 0, 1)
    return wet * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def spec_wet_look(shape, seed, sm, base_m, base_r):
    """Wet look spec: CC=16 glossy. Returns (M, R, CC)."""
    h, w = shape
    M  = np.full((h, w), float(base_m), dtype=np.float32)
    R  = np.full((h, w), float(base_r), dtype=np.float32)
    CC = np.full((h, w), 16.0,          dtype=np.float32)
    return (M, R, CC)
