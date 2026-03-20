"""
engine/finishes.py - Standard Finish Functions
================================================
All spec_fn and paint_fn for the BASE_REGISTRY entries.
These are the "building blocks" - combinable bases that get pattern overlays.

─────────────────────────────────────────────────────────────────────────────
SPEC MAP CHANNEL REFERENCE - VERIFIED 2025/2026 (triple-confirmed in-sim)
─────────────────────────────────────────────────────────────────────────────

  R = Metallic   (0=pure paint/dielectric, 255=pure metal/conductor)
  G = Roughness  (0=perfect mirror, 255=chalk/fully diffuse)
  B = Clearcoat  (0=NO coat, 12-18=MAX GLOSS, 128=satin, 255=scuffed/dull)

  ┌─────────────────────────────────────────────────────────────────┐
  │ CLEARCOAT (B channel) - the "wet glass" layer over your paint  │
  │                                                                 │
  │  B = 0          No clearcoat - raw material surface            │
  │  B = 12–18      MAXIMUM GLOSS - factory fresh / show car       │
  │  B = 40–80      Satin / semi-gloss - slight haze               │
  │  B = 81–140     Weathered - daily driver, visible coat wear    │
  │  B = 141–200    Aged / oxidized - heavy haze, faded panels     │
  │  B = 201–255    Scuffed / destroyed - Brillo-pad dull          │
  │                                                                 │
  │ WHY 16 NOT 0 OR 255 FOR GLOSS:                                 │
  │   Old iRacing docs said "leave blue at 255" - back then CC     │
  │   wasn't active (255 was just a placeholder). Now that CC is   │
  │   live, 255 = most degraded clearcoat. Use 16 for max gloss.  │
  └─────────────────────────────────────────────────────────────────┘

FINISH TYPES (current standard bases):
  chrome           → Pure mirror: M=255, G=2,   CC=0
  gloss            → Showroom paint: M=0,   G=15,  CC=16
  metallic         → Standard metallic: M=200, G=45,  CC=16
  pearl            → Iridescent: M=110, G=35,  CC=16
  candy            → Deep lacquer: M=130, G=12,  CC=16
  satin            → Semi-gloss: M=0,   G=95,  CC=50  ← CC=50 not 10!
  matte            → Flat: M=0,   G=210, CC=0
  satin_metal      → Brushed metallic: M=235, G=60,  CC=16
  metal_flake      → Heavy flake: M=240, G=10,  CC=16
  holographic_flake→ Prismatic: M=235, G=8,   CC=16
  stardust         → Dark metal+stars: M=160, G=55,  CC=16
  brushed_titanium → Directional grain: M=180, G=70,  CC=0
  anodized         → Industrial: M=170, G=80,  CC=0
  carbon_fiber     → Twill weave: M=55,  G=30,  CC=16
  frozen           → Icy matte: M=225, G=140, CC=0
  hex_mesh         → Hex grid: varies
  ripple           → Ring interference: varies
  hammered         → Dimple impacts: M=180, G=var, CC=0

NEW RANGE-EXPLOITING FINISHES (use CC 17–255 deliberately):
  wet_gloss        → Ultra-premium gloss: M=0,   G=8,   CC=16  (G lower than standard)
  daily_driver     → Real-world used: M=0,   G=20,  CC=60
  weathered_metal  → Track-worn: M=200, G=55,  CC=100
  race_worn        → Heavily raced: M=180, G=80,  CC=140
  oxidized_metal   → Sun-damaged: M=160, G=90,  CC=200
  ghost_panel      → Clearcoat-only pattern: M=200, G=40, CC varies 16–120
  velvet           → Soft matte+thin coat: M=0,   G=155, CC=45

FIX GUIDE:
  "Satin looks like matte"     → CC was 10 (below threshold). Now 50. ✅ Fixed
  "Gloss looks plastic"        → spec_gloss: M should be 0, G lower (8-15)
  "Chrome has color tint"      → spec_chrome: M=255, G=2, CC=0
  "Metallic looks muddy"       → paint_metallic: lighten albedo when M>150
  "Candy not deep enough"      → CC=16 is correct; adjust G lower (10-12)
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.core import multi_scale_noise, get_mgrid


def _delegate(fn_name):
    """Get a finish function from the legacy engine."""
    try:
        import shokker_engine_v2 as _e
        return getattr(_e, fn_name, None)
    except Exception:
        return None


def _make_spec(M, G, CC, noise_M=0, noise_G=0, noise_CC=0):
    """
    Factory: create a spec_fn with given M/G/CC base values + optional noise.

    Args:
        M, G, CC: base channel values (int 0-255)
        noise_M/G/CC: noise amplitude for variation (0=flat, higher=more variation)
    Returns: spec_fn(shape, mask, seed, sm) → (h,w,4) uint8
    """
    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        spec = np.zeros((h, w, 4), dtype=np.float32)

        m_val = float(M)
        g_val = float(G)
        cc_val = float(CC)

        if noise_M > 0 or noise_G > 0 or noise_CC > 0:
            noise = multi_scale_noise(shape, [4, 8, 16], [0.35, 0.40, 0.25], seed)
            noise_sm = noise * (sm if sm else 1.0)
            if noise_M > 0:
                m_val = np.clip(m_val + noise_sm * noise_M, 0, 255)
            if noise_G > 0:
                g_val = np.clip(g_val + noise_sm * noise_G, 0, 255)
            if noise_CC > 0:
                cc_val = np.clip(cc_val + noise_sm * noise_CC, 0, 255)

        spec[:, :, 0] = m_val
        spec[:, :, 1] = g_val
        spec[:, :, 2] = cc_val
        spec[:, :, 3] = np.clip(mask * 255, 0, 255)

        return np.clip(spec, 0, 255).astype(np.uint8)
    return spec_fn


def _make_paint_passthrough():
    """Paint fn that passes paint through unchanged (for spec-only finishes)."""
    def paint_fn(paint, shape, mask, seed, pm, bb):
        return paint
    return paint_fn


# ================================================================
# SECTION 1: STANDARD BASE SPEC+PAINT FUNCTIONS
# Delegate to legacy engine (stable implementations there)
# All follow signature: spec_fn(shape, mask, seed, sm) → (h,w,4) uint8
#                       paint_fn(paint, shape, mask, seed, pm, bb) → (h,w,4)
# ================================================================

spec_gloss = _delegate('spec_gloss')
paint_gloss = _delegate('paint_gloss')

spec_matte = _delegate('spec_matte')
paint_matte = _delegate('paint_matte')

spec_satin = _delegate('spec_satin')
paint_satin = _delegate('paint_satin')

spec_metallic = _delegate('spec_metallic')
paint_metallic = _delegate('paint_metallic')

spec_pearl = _delegate('spec_pearl')
paint_pearl = _delegate('paint_pearl')

spec_chrome = _delegate('spec_chrome')
paint_chrome = _delegate('paint_chrome')

spec_satin_metal = _delegate('spec_satin_metal')
paint_satin_metal = _delegate('paint_satin_metal')

spec_metal_flake = _delegate('spec_metal_flake')
paint_metal_flake = _delegate('paint_metal_flake')

spec_holographic_flake = _delegate('spec_holographic_flake')
paint_holographic_flake = _delegate('paint_holographic_flake')

spec_stardust = _delegate('spec_stardust')
paint_stardust = _delegate('paint_stardust')

spec_candy = _delegate('spec_candy')
paint_candy = _delegate('paint_candy')

spec_brushed_titanium = _delegate('spec_brushed_titanium')
paint_brushed_titanium = _delegate('paint_brushed_titanium')

spec_anodized = _delegate('spec_anodized')
paint_anodized = _delegate('paint_anodized')

spec_hex_mesh = _delegate('spec_hex_mesh')
paint_hex_mesh = _delegate('paint_hex_mesh')

spec_frozen = _delegate('spec_frozen')
paint_frozen = _delegate('paint_frozen')

spec_carbon_fiber = _delegate('spec_carbon_fiber')
paint_carbon_fiber = _delegate('paint_carbon_fiber')

spec_ripple = _delegate('spec_ripple')
paint_ripple = _delegate('paint_ripple')

spec_hammered = _delegate('spec_hammered')
paint_hammered = _delegate('paint_hammered')


# ================================================================
# SECTION 2: NEW V5 BASE FINISHES - CC Range Exploitation
# These are the first NATIVE V5 spec functions - fully written here,
# no delegation. They deliberately use CC values from 17–255 to
# produce effects the legacy engine never had.
#
# CLEARCOAT REMINDER:
#   CC=0     → no coat (raw material)
#   CC=16    → max gloss / factory fresh
#   CC=50    → semi-gloss / satin
#   CC=100   → weathered / track-worn coat
#   CC=140   → aged / race-worn
#   CC=200   → oxidized / sun-damaged
#   CC=240+  → scuffed/dull (intentional weathered metallic)
# ================================================================


def spec_wet_gloss(shape, mask, seed, sm):
    """
    Wet Gloss - ultra-premium showroom finish.
    Like gloss but G=8 (even smoother) for a near-glass surface.
    M=0, G=8, CC=16 → dielectric + mirror-smooth + perfect coat.
    """
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = multi_scale_noise(shape, [4, 8, 16], [0.35, 0.40, 0.25], seed + 100)
    G = np.clip(8 + noise * 4 * sm, 0, 20).astype(np.uint8)
    spec[:, :, 0] = 0          # M=0: pure dielectric
    spec[:, :, 1] = G          # G=8±4: near-glass smoothness
    spec[:, :, 2] = 16         # CC=16: max gloss clearcoat
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_wet_gloss(paint, shape, mask, seed, pm, bb):
    """Wet gloss paint - slightly deepens saturation for the \"looking into depth\" effect."""
    result = paint.copy()
    # Slight saturation boost - the clearcoat deepens color perception
    for c in range(3):
        result[:, :, c] = np.clip(
            paint[:, :, c] * (1 + mask * 0.08 * pm),  # 8% saturation enhancement
            0, 1
        )
    return result


def spec_daily_driver(shape, mask, seed, sm):
    """
    Daily Driver - real-world used car finish.
    Perfect paint color + slightly worn clearcoat (CC=60).
    Matte paint base (M=0) like gloss, but clearcoat has visible everyday wear.
    """
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = multi_scale_noise(shape, [8, 16, 32], [0.30, 0.40, 0.30], seed + 200)
    # CC varies 40–80: different areas have more/less clearcoat wear
    CC = np.clip(60 + noise * 20 * sm, 40, 90).astype(np.uint8)
    G = np.clip(20 + noise * 8 * sm, 15, 35).astype(np.uint8)
    spec[:, :, 0] = 0
    spec[:, :, 1] = G
    spec[:, :, 2] = CC
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_daily_driver(paint, shape, mask, seed, pm, bb):
    """Daily driver paint - unchanged color, the worn effect is all in the spec."""
    return paint.copy()


def spec_weathered_metal(shape, mask, seed, sm):
    """
    Weathered Metal - track-worn metallic.
    High metallic base but clearcoat is well-worn (CC=100).
    Looks like a well-used metallic car that's seen real racing.
    Areas of heavier wear get higher CC (duller) driven by noise.
    """
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Large-scale wear pattern (scratches at panel scale)
    wear = multi_scale_noise(shape, [16, 32, 64], [0.30, 0.40, 0.30], seed + 300)
    wear_n = np.clip(wear * 0.5 + 0.5, 0, 1)
    # Fine metallic flake variation
    fine = multi_scale_noise(shape, [2, 4, 8], [0.40, 0.35, 0.25], seed + 310)

    M = np.clip(200 + fine * 30 * sm, 160, 240).astype(np.uint8)
    G = np.clip(55 + wear_n * 25 * sm, 40, 90).astype(np.uint8)
    CC = np.clip(100 + wear_n * 40 * sm, 80, 150).astype(np.uint8)

    spec[:, :, 0] = M
    spec[:, :, 1] = G
    spec[:, :, 2] = CC
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_weathered_metal(paint, shape, mask, seed, pm, bb):
    """Weathered metal - slight darkening of highlights to simulate grime."""
    noise = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 315)
    wear = np.clip(noise * 0.5 + 0.5, 0, 1)
    result = paint.copy()
    # Very subtle darkening on worn areas
    darken = (1.0 - wear * 0.10 * pm) * mask + (1.0 - mask)
    for c in range(3):
        result[:, :, c] = np.clip(paint[:, :, c] * darken, 0, 1)
    return result


def spec_race_worn(shape, mask, seed, sm):
    """
    Race Worn - heavily raced metallic.
    CC=140: significant clearcoat degradation from racing exposure.
    Patchy - some sections have less wear than others.
    M=180: still metallic but not showroom-fresh.
    """
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Large panel-scale wear pattern
    panel_wear = multi_scale_noise(shape, [32, 64, 128], [0.25, 0.45, 0.30], seed + 400)
    pn = np.clip(panel_wear * 0.5 + 0.5, 0, 1)
    # Fine surface scratches
    scratches = multi_scale_noise(shape, [2, 4], [0.50, 0.50], seed + 410)
    sn = np.clip(scratches * 0.5 + 0.5, 0, 1)

    M = np.clip(180 + sn * 40 * sm, 140, 230).astype(np.uint8)
    G = np.clip(80 + pn * 30 * sm, 60, 120).astype(np.uint8)
    CC = np.clip(140 + pn * 60 * sm, 100, 200).astype(np.uint8)

    spec[:, :, 0] = M
    spec[:, :, 1] = G
    spec[:, :, 2] = CC
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_race_worn(paint, shape, mask, seed, pm, bb):
    """Race worn paint - moderate darkening with warm-tinted grime."""
    rng = np.random.RandomState(seed + 415)
    noise = multi_scale_noise(shape, [8, 16, 32], [0.35, 0.40, 0.25], seed + 415)
    grime = np.clip(noise * 0.5 + 0.5, 0, 1) * mask
    result = paint.copy()
    # Add warm grime tint
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1 - grime * 0.12 * pm) + grime * 0.05 * pm, 0, 1)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1 - grime * 0.12 * pm) + grime * 0.04 * pm, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1 - grime * 0.15 * pm), 0, 1)
    return result


def spec_oxidized_metal(shape, mask, seed, sm):
    """
    Oxidized Metal - sun-damaged metallic panels.
    CC=200: heavy clearcoat degradation from UV exposure.
    The car still has metallic base (M=160) but the top coat is nearly destroyed.
    Creates that chalky metallic look of a car left in the sun for years.
    """
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Large blotchy oxidation pattern
    oxidation = multi_scale_noise(shape, [24, 48, 96], [0.25, 0.40, 0.35], seed + 500)
    ox = np.clip(oxidation * 0.5 + 0.5, 0, 1)

    M = np.clip(160 - ox * 40 * sm, 100, 180).astype(np.uint8)
    G = np.clip(90 + ox * 40 * sm, 70, 140).astype(np.uint8)
    CC = np.clip(200 + ox * 40 * sm, 160, 245).astype(np.uint8)

    spec[:, :, 0] = M
    spec[:, :, 1] = G
    spec[:, :, 2] = CC
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_oxidized_metal(paint, shape, mask, seed, pm, bb):
    """Oxidized - fades and desaturates the paint color for sun-damaged look."""
    noise = multi_scale_noise(shape, [24, 48], [0.5, 0.5], seed + 505)
    fade = np.clip(noise * 0.5 + 0.5, 0, 1) * mask
    result = paint.copy()
    # Desaturate + lighten (faded paint)
    lum = 0.299 * paint[:, :, 0] + 0.587 * paint[:, :, 1] + 0.114 * paint[:, :, 2]
    for c in range(3):
        result[:, :, c] = np.clip(
            paint[:, :, c] * (1 - fade * 0.35 * pm) + lum * fade * 0.25 * pm,
            0, 1
        )
    return result


def spec_ghost_panel(shape, mask, seed, sm):
    """
    Ghost Panel - clearcoat-only pattern.
    The M and G channels are UNIFORM everywhere (consistent metallic).
    Only the CC channel varies - some areas get CC=16 (perfect gloss),
    others get CC=80-120 (slightly hazed).

    Result: at most angles the car looks uniform. But as light rakes across
    the surface, hidden panels APPEAR in the clearcoat. A secret design
    that only reveals itself in certain lighting.

    PARADIGM 2 from the Spec Map Bible, now implemented.
    """
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Large-scale ghost pattern (panel-scale features)
    ghost = multi_scale_noise(shape, [32, 64, 128], [0.30, 0.40, 0.30], seed + 600)
    gn = np.clip(ghost * 0.5 + 0.5, 0, 1)

    # Threshold: above 0.55 = perfect clearcoat, below = hazed
    ghost_ok = (gn > 0.55).astype(np.float32)
    # Blend between CC=16 (perfect) and CC=90 (hazy)
    CC = (16 * ghost_ok + 90 * (1 - ghost_ok)).astype(np.uint8)

    spec[:, :, 0] = 200    # M: consistent metallic
    spec[:, :, 1] = 40     # G: consistent smoothness
    spec[:, :, 2] = CC     # CC: varies - the "ghost" is only in clearcoat
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_ghost_panel(paint, shape, mask, seed, pm, bb):
    """Ghost panel paint - unchanged. The effect is entirely in the spec map."""
    return paint.copy()


def spec_velvet(shape, mask, seed, sm):
    """
    Velvet - ultra-soft matte with a barely-there clearcoat.
    G=155: very rough surface (near-matte but not full matte).
    CC=45: just above satin - thin coat that softens without glossing.
    M=0: pure dielectric for maximum Fresnel contrast at edges.

    Result: the surface looks velvety soft. At normal incidence: nearly matte.
    At glancing angles: the Fresnel effect kicks in (dielectric) creating
    a subtle edge glow that real velvet has.
    """
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = multi_scale_noise(shape, [4, 8, 16], [0.40, 0.35, 0.25], seed + 700)
    G = np.clip(155 + noise * 20 * sm, 130, 180).astype(np.uint8)
    CC = np.clip(45 + noise * 10 * sm, 35, 60).astype(np.uint8)
    spec[:, :, 0] = 0
    spec[:, :, 1] = G
    spec[:, :, 2] = CC
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_velvet(paint, shape, mask, seed, pm, bb):
    """Velvet paint - slight warmth shift for the soft fabric feel."""
    result = paint.copy()
    # Very subtle warm tint enhancement
    result[:, :, 0] = np.clip(paint[:, :, 0] + mask * 0.03 * pm, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] - mask * 0.02 * pm, 0, 1)
    return result


# ================================================================
# SECTION 3: ADVANCED FINISH FUNCTIONS (24K Arsenal exclusive bases)
# ================================================================

def build_advanced_base_registry():
    """Return all 24K Arsenal base entries as a dict of (spec_fn, paint_fn) tuples."""
    try:
        import shokker_24k_expansion as _exp
        return getattr(_exp, 'BASE_REGISTRY', {})
    except Exception:
        return {}


# ================================================================
# NEW V5 FINISH REGISTRY - all native V5 bases in one dict
# Registry.py imports this and merges into BASE_REGISTRY
# ================================================================

V5_BASE_FINISHES = {
    "wet_gloss":        (spec_wet_gloss,       paint_wet_gloss),
    "daily_driver":     (spec_daily_driver,     paint_daily_driver),
    "weathered_metal":  (spec_weathered_metal,  paint_weathered_metal),
    "race_worn":        (spec_race_worn,         paint_race_worn),
    "oxidized_metal":   (spec_oxidized_metal,    paint_oxidized_metal),
    "ghost_panel":      (spec_ghost_panel,       paint_ghost_panel),
    "velvet":           (spec_velvet,            paint_velvet),
}
