"""
engine/fusions.py - ALL Fusion Finishes
=========================================
150 Fusion finishes across 15 PARADIGM categories.
Each category is a distinct material-blending concept.

CATEGORY MAP - find what you need to fix by category:
  ┌─────────────────────────────┬────────────────────────────────────────────────┐
  │ Category                    │ Fix Guide                                      │
  ├─────────────────────────────┼────────────────────────────────────────────────┤
  │ Material Gradients (10)      │ gradient_chrome_matte, etc.                   │
  │ Ghost Geometry (10)          │ ghost_hex, ghost_scales, ghost_circuit, etc.  │
  │ Directional Grain (10)       │ aniso_horizontal, aniso_radial, etc.          │
  │ Reactive Panels (10)         │ reactive_stealth_pop, reactive_chrome_fade    │
  │ Sparkle Systems (10)         │ sparkle_diamond_dust, sparkle_starfield, etc. │
  │ Multi-Scale Texture (10)     │ multiscale_chrome_grain, multiscale_silk, etc.│
  │ Weather & Age (10)           │ weather_sun_fade, weather_acid_rain, etc.     │
  │ Exotic Physics (10)      │ exotic_glass, exotic_foggy_chrome     │
  │ Tri-Zone Materials (10)      │ trizone_chrome_candy_matte, etc.              │
  │ Depth Illusion (10)          │ depth_canyon, depth_bubble, etc.              │
  │ Metallic Halos (10)          │ halo_hex_chrome, halo_scale_gold, etc.        │
  │ Light Waves (10)             │ wave_chrome_tide, wave_pearl_current, etc.    │
  │ Fractal Chaos (10)           │ fractal_chrome_decay, fractal_candy_chaos     │
  │ Spectral Reactive (10)       │ spectral_rainbow_metal, spectral_warm_cool    │
  │ Panel Quilting (10)          │ quilt_chrome_mosaic, quilt_candy_tiles        │
  └─────────────────────────────┴────────────────────────────────────────────────┘

FIX GUIDE:
  "Halo Hex Chrome has pattern on base" → halo_hex functions in METALLIC HALOS section below
  "Sparkle Diamond Dust changes base green"→ see sparkle_diamond_dust paint_fn, seed_offset 7400
  "Ghost Hex wrong size" → _make_ghost_fusion, hex_size calculation
  "Weather gradient wrong direction" → _make_weather_fusion, invert_y parameter

HOW THE PAINT_FN WORKS FOR SPARKLE:
  paint_fn receives the base paint (current zone color).
  It should ADD sparkle/shimmer effects WITHOUT recoloring the base.
  Rule: sparkle brightening only affects sparkle POINT pixels, and only adds brightness.
  Never do full-zone hue shift in paint_fn - that recolors the base.

HOW TO ADD A NEW FUSION:
  1. Add the spec_fn and paint_fn functions as a tuple below in the right category
  2. Add the registry entry: FUSION_REGISTRY["my_fusion_id"] = (spec_fn, paint_fn)
  3. Add to get_fusion_group_map() in the right category list
  4. Add UI entry in paint-booth-v2.html

STATUS: All 150 fusions delegated to shokker_fusions_expansion.py.
        Halos and Sparkle have known color-shift issues flagged below for fix.
"""

import numpy as np

# ================================================================
# BRIDGE: delegate to legacy fusions expansion
# All 150 fusions currently live in shokker_fusions_expansion.py
# As individual fusions are fixed/rewritten, they move here.
# ================================================================

try:
    import shokker_fusions_expansion as _fexp
    FUSION_REGISTRY = getattr(_fexp, 'FUSION_REGISTRY', {})
    integrate_fusions = getattr(_fexp, 'integrate_fusions', None)
    get_fusion_group_map = _fexp.get_fusion_group_map
    get_fusion_counts = _fexp.get_fusion_counts
    _FUSIONS_LOADED = True
except Exception as _ex:
    print(f"[V5 Fusions] Warning: Could not load fusions: {_ex}")
    FUSION_REGISTRY = {}
    _FUSIONS_LOADED = False
    def get_fusion_group_map(): return {"fusions": {}}
    def get_fusion_counts(): return {"fusions": 0}


# ================================================================
# KNOWN ISSUES - Flagged for fix
# ================================================================
#
# METALLIC HALOS (halo_hex_chrome, halo_scale_gold, etc.)
# Problem: pattern renders on BOTH base and spec - should only be in spec.
# The paint_fn should NOT write any pattern. The base should be clean.
# Fix location: shokker_fusions_expansion.py → _make_halo_fusion → paint_fn
# V5 Fix: override specific halo paint_fns below when fixed.
#
# SPARKLE SYSTEMS (sparkle_diamond_dust, sparkle_starfield, sparkle_galaxy)
# Problem: base was rendering green - caused by hue shifting entire base.
# Fix location: _make_sparkle_fusion → paint_fn → seed_offset branch
# The sparkle paint_fn must ONLY affect sparkle-point pixels, not the whole base.
# Fixed in shokker_fusions_expansion.py (sparkle points only get brightness boost).
#
# ================================================================

# V5 TARGETED OVERRIDES
# When a specific fusion gets fixed/rewritten in V5, add an override here.
# Format: FUSION_REGISTRY["fusion_id"] = (new_spec_fn, new_paint_fn)
# Example:
#   FUSION_REGISTRY["halo_hex_chrome"] = (spec_halo_hex_fixed, paint_halo_hex_fixed)


# ================================================================
# CATEGORY REFERENCE - 15 Categories × 10 Finishes = 150 Total
# ================================================================
#
# PARADIGM 1: MATERIAL GRADIENTS - Spatial material transitions
#   gradient_chrome_matte, gradient_candy_frozen, gradient_pearl_chrome,
#   gradient_metallic_satin, gradient_obsidian_mirror, gradient_candy_matte,
#   gradient_anodized_gloss, gradient_ember_ice, gradient_carbon_chrome,
#   gradient_spectraflame_void
#
# PARADIGM 2: GHOST GEOMETRY - Invisible clearcoat patterns
#   ghost_hex, ghost_stripes, ghost_diamonds, ghost_waves, ghost_camo,
#   ghost_scales, ghost_circuit, ghost_vortex, ghost_fracture, ghost_quilt
#
# PARADIGM 3: DIRECTIONAL GRAIN - Anisotropic roughness simulation
#   aniso_horizontal_chrome, aniso_vertical_pearl, aniso_diagonal_candy,
#   aniso_radial_metallic, aniso_circular_chrome, aniso_crosshatch_steel,
#   aniso_spiral_mercury, aniso_wave_titanium, aniso_herringbone_gold,
#   aniso_turbulence_metal
#
# PARADIGM 4: REACTIVE PANELS - Fresnel-differentiated metallic zones
#   reactive_stealth_pop, reactive_pearl_flash, reactive_candy_reveal,
#   reactive_chrome_fade, reactive_matte_shine, reactive_dual_tone,
#   reactive_ghost_metal, reactive_mirror_shadow, reactive_warm_cold,
#   reactive_pulse_metal
#
# PARADIGM 5: STOCHASTIC SPARKLE - Micro-mirror point effects
#   sparkle_diamond_dust, sparkle_starfield, sparkle_galaxy, sparkle_firefly,
#   sparkle_snowfall, sparkle_champagne, sparkle_meteor, sparkle_constellation,
#   sparkle_confetti, sparkle_lightning_bug
#
# PARADIGM 6: MULTI-SCALE TEXTURE - Macro+micro roughness layers
#   multiscale_chrome_grain, multiscale_candy_frost, multiscale_metal_grit,
#   multiscale_pearl_texture, multiscale_satin_weave, multiscale_chrome_sand,
#   multiscale_matte_silk, multiscale_flake_grain, multiscale_carbon_micro,
#   multiscale_frost_crystal
#
# PARADIGM 7: WEATHER & AGE - Environmental clearcoat degradation
#   weather_sun_fade, weather_salt_spray, weather_acid_rain, weather_desert_blast,
#   weather_ice_storm, weather_road_spray, weather_hood_bake, weather_barn_dust,
#   weather_ocean_mist, weather_volcanic_ash
#
# PARADIGM 8: EXOTIC PHYSICS - Physically impossible material states
#   exotic_glass_paint, exotic_foggy_chrome, exotic_inverted_candy,
#   exotic_liquid_glass, exotic_phantom_mirror, exotic_ceramic_void,
#   exotic_anti_metal, exotic_crystal_clear, exotic_dark_glass,
#   exotic_wet_void
#
# PARADIGM 9: TRI-ZONE MATERIALS - Three distinct material regions
#   trizone_chrome_candy_matte, trizone_pearl_carbon_gold, trizone_frozen_ember_chrome,
#   trizone_anodized_candy_silk, trizone_vanta_chrome_pearl, trizone_glass_metal_matte,
#   trizone_mercury_obsidian_candy, trizone_titanium_copper_chrome,
#   trizone_ceramic_flake_satin, trizone_stealth_spectra_frozen
#
# PARADIGM 10: DEPTH ILLUSION - Topographic surface relief
#   depth_canyon, depth_bubble, depth_ripple, depth_scale, depth_honeycomb,
#   depth_crack, depth_wave, depth_pillow, depth_vortex, depth_erosion
#
# PARADIGM 11: METALLIC HALOS - Geometric cell borders in spec only
#   halo_hex_chrome, halo_scale_gold, halo_circle_pearl, halo_diamond_chrome,
#   halo_voronoi_metal, halo_wave_candy, halo_crack_chrome, halo_star_metal,
#   halo_grid_pearl, halo_ripple_chrome
#
# PARADIGM 12: LIGHT WAVES - Sinusoidal wave interference in spec
#   wave_chrome_tide, wave_candy_flow, wave_pearl_current, wave_metallic_pulse,
#   wave_dual_frequency, wave_diagonal_sweep, wave_circular_radar,
#   wave_turbulent_flow, wave_standing_chrome, wave_moire_metal
#
# PARADIGM 13: FRACTAL CHAOS - Noise-driven organic material breakup
#   fractal_chrome_decay, fractal_candy_chaos, fractal_pearl_cloud,
#   fractal_metallic_storm, fractal_matte_chrome, fractal_warm_cold,
#   fractal_deep_organic, fractal_electric_noise, fractal_cosmic_dust,
#   fractal_liquid_fire
#
# PARADIGM 14: SPECTRAL REACTIVE - Zone-aware hue response
#   spectral_rainbow_metal, spectral_warm_cool, spectral_dark_light,
#   spectral_sat_metal, spectral_complementary, spectral_neon_reactive,
#   spectral_earth_sky, spectral_mono_chrome, spectral_prismatic_flip,
#   spectral_inverse_logic
#
# PARADIGM 15: PANEL QUILTING - Geometric cell variety patterns
#   quilt_chrome_mosaic, quilt_candy_tiles, quilt_pearl_patchwork,
#   quilt_metallic_pixels, quilt_hex_variety, quilt_diamond_shimmer,
#   quilt_random_chaos, quilt_gradient_tiles, quilt_alternating_duo,
#   quilt_organic_cells
# ================================================================
