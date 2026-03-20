"""
engine/base_registry_data.py - Canonical BASE_REGISTRY (96 bases).
Uses paint functions from engine.spec_paint only. No monolith def _paint_noop(paint, shape, mask, seed, pm, bb):
    return paint

import.
BLEND_BASES (10 entries) stay in shokker_engine_v2 and are merged by registry.py.
Audited & expanded 2026-03-08 - fixed 8 wrong-value entries, added 36+ missing bases.
"""
from engine.spec_paint import (
    paint_absolute_zero,
    paint_antique_patina,
    paint_aramid_fiber,
    paint_armor_plate_v2,
    paint_battleship_gray_v2,
    paint_bioluminescent,
    paint_black_hole_accretion,
    paint_blackout_v2,
    paint_brushed_grain,
    paint_burnt_metal,
    paint_carbon_darken,
    paint_cc_aramid,
    paint_cc_carbon,
    paint_cc_fiberglass,
    paint_cc_forged,
    paint_cc_graphene,
    paint_cerakote_v2,
    paint_ceramic_gloss,
    paint_cg_crystal,
    paint_cg_obsidian,
    paint_cg_porcelain,
    paint_carbon_weave,
    paint_chameleon_shift,
    paint_chrome_brighten,
    paint_cp_candy_burgundy,
    paint_cp_candy_cobalt,
    paint_cp_candy_emerald,
    paint_cp_chameleon,
    paint_cp_iridescent,
    paint_cp_moonstone,
    paint_cp_opal,
    paint_cp_spectraflame,
    paint_cp_tinted_clear,
    paint_cp_tri_coat_pearl,
    paint_dark_matter,
    paint_diamond_sparkle,
    paint_duracoat_v2,
    paint_electric_blue_tint,
    paint_f_clear_matte,
    paint_f_eggshell,
    paint_f_flat_black,
    paint_f_gloss,
    paint_f_matte,
    paint_f_primer,
    paint_f_satin,
    paint_f_semi_gloss,
    paint_f_silk,
    paint_f_wet_look,
    paint_f_scuffed_satin,
    paint_f_living_matte,
    paint_f_chalky_base,
    paint_f_pure_white,
    paint_fine_sparkle,
    paint_forged_carbon,
    paint_galvanized_speckle,
    paint_glass_tint,
    paint_graphene_mono,
    paint_gunship_gray_v2,
    paint_heat_tint,
    paint_holographic_base,
    paint_ice_cracks,
    paint_interference_shift,
    paint_iridescent_shift,
    paint_martian_regolith,
    paint_mercury_pool,
    paint_mil_spec_od_v3,
    paint_mil_spec_tan_v2,
    paint_moonstone_adularescence,
    paint_none,
    paint_obsidian_depth,
    paint_oil_slick,
    paint_opal_fire,
    paint_patina_green,
    paint_plasma_core,
    paint_plasma_shift,
    paint_powder_coat_v2,
    paint_primer_flat,
    paint_quantum_black,
    paint_rain_droplets,
    paint_raw_aluminum,
    paint_rose_gold_tint,
    paint_rubber_absorb,
    paint_rust_corrosion,
    paint_sandblasted_v2,
    paint_satin_wrap,
    paint_silk_sheen,
    paint_smoked_darken,
    paint_solar_panel,
    paint_spectraflame,
    paint_submarine_black_v2,
    paint_subtle_flake,
    paint_tactical_flat,
    paint_tinted_clearcoat,
    paint_tri_coat_depth,
    paint_tricolore_shift,
    paint_volcanic_ash,
    paint_warm_metal,
    paint_wet_gloss,
    spec_absolute_zero,
    spec_armor_plate_v2,
    spec_battleship_gray_v2,
    spec_bioluminescent,
    spec_black_hole_accretion,
    spec_blackout_v2,
    spec_brushed_grain,
    spec_cc_carbon,
    spec_cc_carbon_ceramic,
    spec_cc_forged,
    spec_cerakote_v2,
    spec_cg_glass,
    spec_cg_obsidian,
    spec_cg_porcelain,
    spec_cobalt_metal,
    spec_dark_matter,
    spec_duracoat_v2,
    spec_exotic_metal,
    spec_extreme_experimental,
    spec_gunship_gray_v2,
    spec_holographic_base,
    spec_industrial_tactical,
    spec_liquid_titanium,
    spec_martian_regolith,
    spec_metallic_standard,
    spec_mil_spec_od_v3,
    spec_mil_spec_tan_v2,
    spec_oem_automotive,
    spec_plasma_core,
    spec_platinum_metal,
    spec_powder_coat_v2,
    spec_premium_luxury,
    spec_quantum_black,
    spec_racing_heritage,
    spec_sandblasted_v2,
    spec_satin_wrap,
    spec_solar_panel,
    spec_submarine_black_v2,
    spec_tungsten_metal,
    spec_weathered_aged,
)











# --- BASE MATERIAL REGISTRY ---
# 96 bases. BLEND_BASES (10) are merged by registry.py from monolith.
BASE_REGISTRY = {
    # ── STANDARD FINISHES (FOUNDATION) ──────────────────────────────────────────────
    # Foundation: solid bases only, NO texture/pattern.
    # CC SCALE: 16=max gloss, 0=mirror/metallised, >16=progressively dull up to 255=maximum degradation.
    # The CC range is used deliberately here to spread these bases across the full sheen spectrum.
    "ceramic":          {"M": 60,  "R": 8,   "CC": 16, "paint_fn": paint_none,   "desc": "Ultra-smooth ceramic coating deep wet shine",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.3, "perlin_lacunarity": 2.0, "noise_M": 30, "noise_R": 15},
    "gloss":            {"M": 0,   "R": 30,  "CC": 16,  "paint_fn": paint_none,        "desc": "Standard glossy clearcoat - max gloss CC=16"},
    "piano_black":      {"M": 5,   "R": 3,   "CC": 16,  "paint_fn": paint_none, "base_spec_fn": spec_cg_glass, "desc": "Deep ebony piano black, smooth mirror-like clarity"},
    "wet_look":         {"M": 0,   "R": 22,  "CC": 16,  "paint_fn": paint_none,    "desc": "Deep wet clearcoat - gloss depth with subtle gamma"},
    "semi_gloss":       {"M": 0,   "R": 55,  "CC": 40,  "paint_fn": paint_none,  "desc": "Semi-gloss - slight sheen, CC=40 mild dulling"},
    "satin":            {"M": 0,   "R": 95,  "CC": 70,  "paint_fn": paint_none,       "desc": "Satin - mid sheen, CC=70 moderate clearcoat degradation"},
    "scuffed_satin":    {"M": 0,   "R": 110, "CC": 90,  "paint_fn": paint_none, "desc": "Scuffed satin - rougher version of satin, CC=90"},
    "silk":             {"M": 0,   "R": 85,  "CC": 60,  "paint_fn": paint_none,        "desc": "Silk - smooth low-reflection sheen, CC=60"},
    "eggshell":         {"M": 0,   "R": 130, "CC": 100, "paint_fn": paint_none,    "desc": "Eggshell - low sheen wall-paint finish, CC=100"},
    # Extra Foundation bases (solid, no texture) — spread across sheen spectrum
    "f_pure_white":     {"M": 0,   "R": 145, "CC": 110, "paint_fn": paint_none,  "desc": "Pure white foundation - eggshell sheen"},
    "f_pure_black":     {"M": 0,   "R": 240, "CC": 190, "paint_fn": paint_none,  "desc": "Pure black foundation - near-flat, CC=190"},
    "f_neutral_grey":   {"M": 0,   "R": 185, "CC": 150, "paint_fn": paint_none,      "desc": "Neutral grey foundation - dull flat, CC=150"},
    "f_soft_gloss":     {"M": 0,   "R": 42,  "CC": 22,  "paint_fn": paint_none,       "desc": "Soft gloss foundation - near-gloss CC=22"},
    "f_soft_matte":     {"M": 0,   "R": 200, "CC": 165, "paint_fn": paint_none,       "desc": "Soft matte foundation - flat finish, CC=165"},
    "f_clear_satin":    {"M": 0,   "R": 100, "CC": 75,  "paint_fn": paint_none,       "desc": "Clear satin foundation - CC=75"},
    "f_warm_white":     {"M": 0,   "R": 120, "CC": 95,  "paint_fn": paint_none,    "desc": "Warm white foundation - eggshell-plus sheen, CC=95"},
    # ── NEW FOUNDATION BASES (color-safe, paint_none) ─────────────────
    "f_chrome":         {"M": 255, "R": 2,   "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation chrome - pure mirror metallic, no color change",
                         "noise_scales": [1, 2], "noise_weights": [0.5, 0.5], "noise_M": 8, "noise_R": 5},
    "f_satin_chrome":   {"M": 250, "R": 45,  "CC": 40,  "paint_fn": paint_none,  "desc": "Foundation satin chrome - silky satin metallic",
                         "noise_scales": [2, 4], "noise_weights": [0.5, 0.5], "noise_M": 15, "noise_R": 12},
    "f_metallic":       {"M": 200, "R": 50,  "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation metallic - standard metallic flake, no color shift",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 15},
    "f_pearl":          {"M": 100, "R": 40,  "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation pearl - pearlescent sheen, no color shift",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 10},
    "f_carbon_fiber":   {"M": 55,  "R": 30,  "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation carbon fiber - carbon weave spec, no color change",
                         "noise_scales": [4, 8], "noise_weights": [0.5, 0.5], "noise_M": 25, "noise_R": 15},
    "f_brushed":        {"M": 180, "R": 75,  "CC": 65,  "paint_fn": paint_none,  "desc": "Foundation brushed - directional grain metallic, CC=65 grain-disrupted coat",
                         "perlin": True, "perlin_octaves": 4, "noise_M": 20, "noise_R": 25},
    "f_frozen":         {"M": 160, "R": 85,  "CC": 130, "paint_fn": paint_none,  "desc": "Foundation frozen matte - icy matte metal, CC=130 deliberately flat",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 35, "noise_R": 20},
    "f_powder_coat":    {"M": 10,  "R": 120, "CC": 145, "paint_fn": paint_none,  "desc": "Foundation powder coat - thick textured coating, CC=145 no traditional clearcoat",
                         "noise_scales": [1, 2], "noise_weights": [0.5, 0.5], "noise_M": 8, "noise_R": 30},
    "f_anodized":       {"M": 180, "R": 65,  "CC": 85,  "paint_fn": paint_none,  "desc": "Foundation anodized - anodized oxide layer finish, CC=85",
                         "noise_scales": [2, 4], "noise_weights": [0.5, 0.5], "noise_M": 25, "noise_R": 18},
    "f_vinyl_wrap":     {"M": 0,   "R": 100, "CC": 110, "paint_fn": paint_none,  "desc": "Foundation vinyl wrap - vinyl material finish, CC=110 no clearcoat",
                         "noise_scales": [1, 2], "noise_weights": [0.5, 0.5], "noise_M": 5, "noise_R": 15},
    "f_gel_coat":       {"M": 0,   "R": 12,  "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation gel coat - fiberglass gelcoat high-gloss, no color change",
                         "noise_scales": [2, 4], "noise_weights": [0.5, 0.5], "noise_M": 3, "noise_R": 8},
    "f_baked_enamel":   {"M": 0,   "R": 18,  "CC": 20,  "paint_fn": paint_none,  "desc": "Foundation baked enamel - hard baked traditional enamel, no color shift",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 5, "noise_R": 12},
    # ── METALLIC & FLAKE ──────────────────────────────────────────────
    "copper":           {"M": 190, "R": 55,  "CC": 16, "paint_fn": paint_warm_metal,      "desc": "Warm oxidized copper metallic",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 35, "noise_R": 20},
    "diamond_coat":     {"M": 220, "R": 3,   "CC": 16, "paint_fn": paint_diamond_sparkle, "desc": "Diamond dust ultra-fine sparkle coat",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 25, "noise_R": 8},
    "electric_ice":     {"M": 240, "R": 10,  "CC": 16, "paint_fn": paint_electric_blue_tint, "desc": "Icy electric blue metallic - cold neon shimmer",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 15, "noise_R": 8},
    "gunmetal":         {"M": 220, "R": 40,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Dark aggressive blue-gray metallic",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 30, "noise_R": 15},
    "metallic":         {"M": 200, "R": 50,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Standard metallic with visible flake",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 40, "noise_R": 18},
    "pearl":            {"M": 100, "R": 40,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Pearlescent iridescent sheen",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 12},
    "pearlescent_white":{"M": 120, "R": 30,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Tri-coat pearlescent white deep sparkle",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 10},
    "plasma_metal":     {"M": 250, "R": 20,  "CC": 16, "paint_fn": paint_plasma_shift, "desc": "Extraterrestrial smart-metal with phase-shifting liquid surface", "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.3, "noise_M": 100, "noise_R": -10},
    "rose_gold":        {"M": 10, "R": 60, "CC": 16, "paint_fn": paint_rose_gold_tint, "desc": "Disturbing synthetic flesh tone utilizing organic subsurface scattering algorithms", "perlin": True, "perlin_octaves": 6, "noise_R": 40},
    # ⚠️ FIXED 2026-03-08: satin_gold CC was 0 - gold with matte clearcoat gets CC=16.
    "satin_gold":       {"M": 235, "R": 60,  "CC": 16, "paint_fn": paint_warm_metal,      "desc": "Satin gold metallic warm sheen - factory satin clearcoat (CC=16)",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 15, "noise_R": 18},
    # ── CHROME & MIRROR ───────────────────────────────────────────────
    "chrome":           {"M": 255, "R": 2,   "CC": 16,  "paint_fn": paint_chrome_brighten, "desc": "Pure mirror chrome",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 20, "noise_R": 8},
    "dark_chrome":      {"M": 250, "R": 180, "CC": 200, "paint_fn": paint_carbon_darken, "desc": "A metal so dense and gravitationally heavy it traps light within its rough oxidized surface", "perlin": True, "noise_M": 50, "noise_R": 100},
    "mercury":          {"M": 255, "R": 3,   "CC": 16,  "paint_fn": paint_mercury_pool,    "desc": "Liquid mercury pooling mirror - desaturated chrome flow",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.5, "perlin_lacunarity": 1.8, "noise_M": 30, "noise_R": 10},
    "satin_chrome":     {"M": 250, "R": 45,  "CC": 40,  "paint_fn": paint_chrome_brighten, "desc": "BMW silky satin chrome",
                         "noise_scales": [4, 8], "noise_weights": [0.4, 0.6], "noise_M": 20, "noise_R": 25},
    "surgical_steel":   {"M": 250, "R": 50, "CC": 16, "paint_fn": paint_brushed_grain, "desc": "Indestructible weaponized metal alloy exhibiting incredibly aggressive, deep brushing gouges", "noise_scales": [32, 64], "noise_R": 150},
    # 🔴 ADDED 2026-03-08 - Chrome & Mirror missing entries
    "antique_chrome":   {"M": 220, "R": 18,  "CC": 50,  "paint_fn": paint_antique_patina,  "desc": "Antique chrome - warm brown/gold tarnish patina over aged chrome",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 20},
    "black_chrome":     {"M": 255, "R": 2,   "CC": 16,  "paint_fn": paint_smoked_darken,   "desc": "Black chrome - pure mirror physics, paint_fn darkens toward black",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 20, "noise_R": 8},
    "blue_chrome":      {"M": 255, "R": 2,   "CC": 16,  "paint_fn": paint_electric_blue_tint, "desc": "Blue chrome - mirror chrome with icy blue tint layer",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 20, "noise_R": 8},
    "red_chrome":       {"M": 220, "R": 5,   "CC": 50, "paint_fn": paint_plasma_shift, "desc": "Blood-tinted chrome with UV-reactive subsurface thick clearcoat", "noise_scales": [2, 4], "noise_weights": [0.5, 0.5], "noise_M": 10, "noise_R": 10},
    "mirror_gold":      {"M": 255, "R": 2,   "CC": 16,  "paint_fn": paint_warm_metal,      "desc": "Mirror gold - pure chrome physics with warm gold color push from paint_fn",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 15, "noise_R": 8},
    # ── CANDY & CLEARCOAT VARIANTS (CANDY & PEARL) ────────────────────────────────────
    "candy":            {"M": 200, "R": 15,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Deep wet candy transparent glass",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 35, "noise_R": 15},
    "candy_chrome":     {"M": 250, "R": 4,   "CC": 16, "paint_fn": paint_spectraflame,    "desc": "Candy-tinted chrome - deep color over mirror base",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 60, "noise_R": 15},
    "clear_matte":      {"M": 0,   "R": 175, "CC": 130, "paint_fn": paint_none,  "desc": "Matte clearcoat - CC=130 visibly flat, no gloss"},
    "smoked":           {"M": 10, "R": 10, "CC": 60, "paint_fn": paint_smoked_darken, "desc": "Charcoal grey medium capturing a deep smoky internal volumetric particle volume", "noise_scales": [4, 8], "noise_R": 40},
    "spectraflame":     {"M": 80, "R": 2, "CC": 120, "paint_fn": paint_cp_spectraflame, "desc": "Clear optical polymer that shifts its entire internal crystalline structure dynamically under light", "noise_scales": [4, 8], "noise_M": 180, "noise_R": 30},
    # ⚠️ FIXED 2026-03-08: tinted_clear M was 40 (metallic) - tinted clear is dielectric.
    "tinted_clear":     {"M": 0,   "R": 8,   "CC": 16, "paint_fn": paint_cp_tinted_clear,"desc": "Deep tinted clearcoat over base color - dielectric, pure wet glass depth",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.4, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 10},
    # 🔴 ADDED 2026-03-08 - Candy & Pearl missing entries
    "candy_burgundy":   {"M": 20, "R": 60, "CC": 16, "paint_fn": paint_oil_slick, "desc": "Viscous, dark thick semi-dried fluid coating, highly uneven and organically unsettling", "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.6, "noise_R": 100},
    "candy_cobalt":     {"M": 180, "R": 5,   "CC": 30, "paint_fn": paint_fine_sparkle, "desc": "Ultra-thick pressurized deep-ocean resin pour over dark scatter base", "noise_scales": [16, 32], "noise_weights": [0.5, 0.5], "noise_M": 30},
    "candy_emerald":    {"M": 190, "R": 2,   "CC": 16, "paint_fn": paint_electric_blue_tint, "desc": "Uranium glass generating intense radioluminescence", "perlin": True, "perlin_octaves": 4, "noise_M": -50, "noise_R": 80},
    "tri_coat_pearl":   {"M": 130, "R": 25,  "CC": 16, "paint_fn": paint_cp_tri_coat_pearl,          "desc": "Tri-coat pearl - three-layer candy pearl, directional mica waves + dense sparkle",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 12},
    "moonstone":        {"M": 80,  "R": 30,  "CC": 16, "paint_fn": paint_moonstone_adularescence, "desc": "Moonstone - soft milky translucent shimmer, blue-white adularescence",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 25, "noise_R": 15},
    "opal":             {"M": 180, "R": 50, "CC": 100, "paint_fn": paint_forged_carbon, "desc": "Massive multi-colored shifting pearl mimicking the biological armored plate of a dragon", "noise_scales": [8, 16], "noise_M": 120, "noise_R": 80},
    # ── CARBON & COMPOSITE ────────────────────────────────────────────────────────────
    # 🔴 ADDED 2026-03-08 - entire category was missing from engine
    "carbon_base":      {"M": 55,  "R": 30,  "CC": 16, "paint_fn": paint_cc_carbon, "base_spec_fn": spec_cc_carbon,   "desc": "Carbon fiber base - dense micro-strand 2x2 twill weave heavily absorbing ambient light",
                         "noise_scales": [16, 32, 64, 128], "noise_weights": [0.1, 0.2, 0.3, 0.4], "noise_M": 35, "noise_R": 35},
    "carbon_ceramic":   {"M": 120, "R": 25,  "CC": 120,  "paint_fn": paint_none, "base_spec_fn": spec_cc_carbon_ceramic,   "desc": "Carbon ceramic baked under extreme pressure and heat, exposing abrasive microscopic silica dust",
                         "noise_scales": [32, 64, 128], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 60, "noise_R": 60},
    "aramid":           {"M": 30,  "R": 90,  "CC": 100,  "paint_fn": paint_cc_aramid, "base_spec_fn": spec_cc_carbon,    "desc": "Aramid fiber - warm gold-amber interwoven synthetic threads catching light harshly at its peaks",
                         "perlin": True, "perlin_octaves": 6, "perlin_persistence": 0.5, "perlin_lacunarity": 3.0, "noise_M": 25, "noise_R": 50},
    "fiberglass":       {"M": 0,   "R": 55,   "CC": 30,  "paint_fn": paint_cc_fiberglass,            "desc": "Fiberglass - rough internal dielectric strands suspended in a milky resin, refracting at sharp angles",
                         "noise_scales": [16, 64], "noise_weights": [0.4, 0.6], "noise_M": 10, "noise_R": 40},
    "forged_composite": {"M": 90,  "R": 35,  "CC": 16, "paint_fn": paint_cc_forged, "base_spec_fn": spec_cc_forged,   "desc": "Forged composite - irregular micro-chopped carbon chunks reflecting light independently in extreme chaos",
                         "perlin": True, "perlin_octaves": 6, "perlin_persistence": 0.6, "perlin_lacunarity": 2.5, "noise_M": 90, "noise_R": 80},
    "graphene":         {"M": 210, "R": 12,  "CC": 16,  "paint_fn": paint_cc_graphene,   "desc": "Graphene sheet - an atomically thin dark lattice structure exhibiting extreme geometric micro-specular noise",
                         "noise_scales": [64, 128, 256], "noise_weights": [0.2, 0.3, 0.5], "noise_M": 40, "noise_R": 25},
    "hybrid_weave":     {"M": 70,  "R": 40,  "CC": 16, "paint_fn": paint_cc_carbon, "base_spec_fn": spec_cc_carbon,   "desc": "Hybrid weave - tight structural interplay between carbon dark and kevlar thread matrices",
                         "noise_scales": [32, 64, 128], "noise_weights": [0.2, 0.3, 0.5], "noise_M": 50, "noise_R": 45},
    "kevlar_base":      {"M": 20,  "R": 100, "CC": 180,  "paint_fn": paint_cc_aramid, "base_spec_fn": spec_cc_carbon,    "desc": "Kevlar base - raw ballistic macro-weave thread matrix completely devoid of sealant",
                         "perlin": True, "perlin_octaves": 6, "perlin_persistence": 0.6, "perlin_lacunarity": 2.8, "noise_R": 65},
    # ── CERAMIC & GLASS ──────────────────────────────────────────────────────────────
    # (ceramic and piano_black are in STANDARD FINISHES above)
    # 🔴 ADDED 2026-03-08 - most of this category was missing from engine
    "ceramic_matte":    {"M": 35,  "R": 120, "CC": 160, "paint_fn": paint_none,   "desc": "Diffuse fired ceramic with intense high-frequency abrasive grit structure (CC=160 flat)",
                         "perlin": True, "perlin_octaves": 5, "perlin_persistence": 0.55, "perlin_lacunarity": 3.0, "noise_M": 25, "noise_R": 60},
    "crystal_clear":    {"M": 0, "R": 5, "CC": 16, "paint_fn": paint_cg_crystal, "base_spec_fn": spec_cg_glass, "desc": "A completely lucid, perfectly clear viscous water coating that never dries or sets", "noise_scales": [16, 32, 64], "noise_weights": [0.2, 0.3, 0.5], "noise_R": 15},
    "enamel":           {"M": 0,   "R": 18,  "CC": 16, "paint_fn": paint_cg_crystal,   "desc": "Enamel - baked dielectric gloss filled with microscopic silica sediment imperfections",
                         "noise_scales": [64, 128], "noise_weights": [0.5, 0.5], "noise_R": 35},
    "obsidian":         {"M": 20,  "R": 4,   "CC": 16, "paint_fn": paint_cg_obsidian, "base_spec_fn": spec_cg_obsidian,  "desc": "Obsidian - extremely sharp fractured volcanic glass with intense razor-sharp micro-flaking edges",
                         "perlin": True, "perlin_octaves": 6, "perlin_persistence": 0.6, "perlin_lacunarity": 3.5, "noise_M": 60, "noise_R": 30},
    "porcelain":        {"M": 0, "R": 8, "CC": 16, "paint_fn": paint_cg_porcelain, "base_spec_fn": spec_cg_porcelain, "desc": "Fractured monolithic bone ivory finish with subsurface micro-cracks spreading continuously", "perlin": True, "perlin_octaves": 5, "perlin_lacunarity": 3.0, "noise_R": 70},
    "tempered_glass":   {"M": 0,   "R": 3,   "CC": 16, "paint_fn": paint_none, "base_spec_fn": spec_cg_glass,      "desc": "Tempered glass - heat-stressed layered glass containing severe high-frequency molecular tension",
                         "noise_scales": [128, 256], "noise_weights": [0.4, 0.6], "noise_R": 20},
    # ── GAP-FILL: COATED OVER METAL / DEEP GLASS ────────────────────────
    "hydrographic":     {"M": 240, "R": 5,   "CC": 16, "paint_fn": paint_chrome_brighten, "desc": "Mirror metal under maximum deep clearcoat - wet glass over chrome",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 20, "noise_R": 6},
    "jelly_pearl":      {"M": 120, "R": 10,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Ultra-wet candy pearl - max depth, like looking through colored glass",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 18, "noise_R": 8},
    "orange_peel_gloss":{"M": 0,   "R": 160, "CC": 16, "paint_fn": paint_none,            "desc": "Orange-peel texture sealed under thick clearcoat",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.7, "perlin_lacunarity": 2.2, "noise_M": 0, "noise_R": 40},
    "tinted_lacquer":   {"M": 130, "R": 80,  "CC": 16, "paint_fn": paint_tinted_clearcoat,"desc": "Semi-metallic under thick lacquer pour - depth and warmth",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.4, "perlin_lacunarity": 1.8, "noise_M": 25, "noise_R": 20},
    # ── MATTE & FLAT ─────────────────────────────────────────────────
    # CC=0 triggers the metallised path in the renderer — always use CC>=16 for non-chrome bases.
    # For dead-flat finishes use CC=180–255 (maximum clearcoat degradation = most dull).
    "blackout":         { "base_spec_fn": spec_blackout_v2,"M": 5,  "R": 210, "CC": 200, "paint_fn": paint_blackout_v2, "desc": "Stealth murdered-out - near-total absorption, dead flat (CC=200)"},
    "flat_black":       {"M": 0,   "R": 248, "CC": 220, "paint_fn": paint_none,  "desc": "Dead flat zero-sheen black - CC=220 maximum degradation"},
    # ⚠️ FIXED 2026-03-08: frozen CC was 0 - BMW Frozen paints have a matte clear over them.
    "frozen":           {"M": 225, "R": 140, "CC": 16,  "paint_fn": paint_subtle_flake,  "desc": "Frozen icy matte metal - BMW Individual style with matte clearcoat (CC=16)",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 30},
    "frozen_matte":     {"M": 210, "R": 160, "CC": 80,  "paint_fn": paint_subtle_flake,  "desc": "BMW Individual frozen matte metallic - CC=80 degraded matte clear",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 25},
    "matte":            {"M": 0,   "R": 200, "CC": 160, "paint_fn": paint_none,       "desc": "Flat matte - CC=160 heavily degraded clearcoat = no visible sheen"},
    "vantablack":       {"M": 0,   "R": 255, "CC": 240, "paint_fn": paint_none,          "desc": "Absolute void zero reflection - CC=240 maximum possible degradation",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 3, "noise_R": 5},
    "volcanic":         {"M": 80,  "R": 180, "CC": 70,  "paint_fn": paint_volcanic_ash,  "desc": "Volcanic ash coating - the ash layer IS the coat, heavily degraded (CC=70)"},
    # ── BRUSHED & DIRECTIONAL GRAIN ──────────────────────────────────
    "brushed_aluminum": {"base_spec_fn": spec_brushed_grain, "M": 230, "R": 55,  "CC": 16,  "paint_fn": paint_brushed_grain,   "desc": "Brushed natural aluminum directional grain",
                         "brush_grain": True, "noise_M": 15, "noise_R": 30},
    "brushed_titanium": {"base_spec_fn": spec_brushed_grain, "M": 180, "R": 70,  "CC": 16,  "paint_fn": paint_brushed_grain,   "desc": "Heavy directional titanium grain",
                         "brush_grain": True, "noise_M": 25, "noise_R": 45},
    "satin_metal":      {"base_spec_fn": spec_brushed_grain, "M": 235, "R": 65,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Subtle brushed satin metallic",
                         "brush_grain": True, "noise_R": 20},
    # ── TACTICAL & INDUSTRIAL ────────────────────────────────────────
    "cerakote":         { "base_spec_fn": spec_cerakote_v2,"M": 30, "R": 160, "CC": 170, "paint_fn": paint_cerakote_v2, "desc": "Mil-spec ceramic coating - heavy desaturation with high frequency hard chalky speckling (CC=170 flat)"},
    "duracoat":         { "base_spec_fn": spec_duracoat_v2,"M": 20, "R": 130, "CC": 150, "paint_fn": paint_duracoat_v2, "desc": "Tactical epoxy coat - rippling and uneven pooling from thick air-dry epoxy spray (CC=150 flat)"},
    "powder_coat":      { "base_spec_fn": spec_powder_coat_v2,"M": 10, "R": 90, "CC": 50,  "paint_fn": paint_powder_coat_v2, "desc": "Cured thick polyester block color with aggressive baked orange-peel rippling"},
    "rugged":           {"M": 50,  "R": 190, "CC": 175, "paint_fn": paint_tactical_flat,   "desc": "Rugged off-road coat - very rough protective layer (CC=175 flat)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 20, "noise_R": 35},
    # 🔴 ADDED 2026-03-08 - Industrial & Tactical missing entries
    "armor_plate":      { "base_spec_fn": spec_armor_plate_v2,"M": 60, "R": 160,  "CC": 130, "paint_fn": paint_armor_plate_v2, "desc": "Armor plate - heavy rolled steel, deep scuffs and slight oxidation, naked heavy metal (CC=130)"},
    "battleship_gray":  { "base_spec_fn": spec_battleship_gray_v2,"M": 20, "R": 140, "CC": 120, "paint_fn": paint_battleship_gray_v2, "desc": "Battleship gray - naval haze gray with significant vertical salt spray weathering (CC=120)"},
    "gunship_gray":     { "base_spec_fn": spec_gunship_gray_v2,"M": 5, "R": 200, "CC": 190, "paint_fn": paint_gunship_gray_v2, "desc": "Gunship gray - radar absorbent material (RAM), extremely gritty micro-texture (CC=190 near-flat)"},
    "mil_spec_od":      { "base_spec_fn": spec_mil_spec_od_v3,"M": 2, "R": 180, "CC": 195, "paint_fn": paint_mil_spec_od_v3, "desc": "Mil-spec OD - flat olive drab standard with heavy field mud smudging (CC=195 dead flat)"},
    "mil_spec_tan":     { "base_spec_fn": spec_martian_regolith,"M": 0, "R": 220, "CC": 200, "paint_fn": paint_martian_regolith, "desc": "Martian Regolith Dust - heavy iron oxide crushing, rust dunes, and sharp glass shards (CC=200)"},
    "sub_black":        {"base_spec_fn": spec_submarine_black_v2,"M": 0, "R": 235, "CC": 210, "paint_fn": paint_submarine_black_v2, "desc": "Sub black - anechoic rubber tile grid, absolute light absorption (CC=210 dead flat)"},
    "tungsten":         { "base_spec_fn": spec_tungsten_metal,"M": 240, "R": 25,  "CC": 16,  "paint_fn": paint_raw_aluminum,    "desc": "Tungsten - ultra-dense dark gray metal, near-chrome metallic, no coat",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.4, 0.3, 0.3], "noise_M": 15, "noise_R": 15},
    # ── EXOTIC METAL ─────────────────────────────────────────────────
    # 🔴 ADDED 2026-03-08 - Exotic Metal missing entries
    "cobalt_metal":     { "base_spec_fn": spec_cobalt_metal,"M": 195, "R": 28,  "CC": 16,  "paint_fn": paint_electric_blue_tint, "desc": "Cobalt metal - blue-tinted raw cobalt alloy, no clearcoat",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 15},
    "liquid_titanium":  { "base_spec_fn": spec_liquid_titanium,"M": 245, "R": 5,   "CC": 16,  "paint_fn": paint_mercury_pool,    "desc": "Liquid titanium - near-mirror flowing molten metal surface",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.4, "perlin_lacunarity": 2.0, "noise_M": 20, "noise_R": 8},
    "platinum":         { "base_spec_fn": spec_platinum_metal,"M": 255, "R": 4,   "CC": 16, "paint_fn": paint_chrome_brighten, "desc": "Platinum - pure dense mirror metal, slightly warmer than chrome, coated",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 12, "noise_R": 8},
    "titanium_raw":     {"M": 155, "R": 85,  "CC": 16,  "paint_fn": paint_raw_aluminum,    "desc": "Titanium raw - omnidirectional rough industrial surface, no grain, no coat",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 35},
    # ── RAW METAL & WEATHERED ────────────────────────────────────────
    "anodized":         {"M": 170, "R": 180, "CC": 140, "paint_fn": paint_subtle_flake,    "desc": "Gritty matte anodized aluminum (CC=140 flat)",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 25},
    "burnt_headers":    {"M": 190, "R": 45,  "CC": 16,  "paint_fn": paint_burnt_metal,     "desc": "Exhaust header heat-treated gold-blue oxide",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 20},
    "galvanized":       {"M": 195, "R": 65,  "CC": 30,  "paint_fn": paint_galvanized_speckle, "desc": "Hot-dip galvanized zinc - the zinc IS the coat (CC=30 thin metallic coat)",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.4, 0.3, 0.3], "noise_M": 25, "noise_R": 30},
    "heat_treated":     {"M": 185, "R": 35,  "CC": 16,  "paint_fn": paint_heat_tint,       "desc": "Heat-treated titanium blue-gold zones",
                         "noise_scales": [8, 16], "noise_weights": [0.4, 0.6], "noise_M": 20, "noise_R": 15},
    "patina_bronze":    {"M": 160, "R": 90,  "CC": 16,  "paint_fn": paint_patina_green,    "desc": "Aged oxidized bronze with green patina",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 35},
    "patina_coat":      {"M": 100, "R": 150, "CC": 50, "paint_fn": paint_patina_green,    "desc": "Old weathered paint with fresh satin clearcoat sprayed over - protected patina",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 35},
    "battle_patina":    {"M": 200, "R": 150, "CC": 50, "paint_fn": paint_burnt_metal,     "desc": "Heavily worn metal base with thin protective satin coat - used racecar look",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 40},
    # ⚠️ FIXED 2026-03-08: cerakote_gloss M was 200 (too metallic for ceramic). Real Cerakote Gloss is polymer - M=100.
    "cerakote_gloss":   {"M": 100, "R": 15,  "CC": 16, "paint_fn": paint_tactical_flat,   "desc": "Cerakote gloss - polymer ceramic, semi-metallic sealed gloss surface (M=100)",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 20},
    "raw_aluminum":     {"M": 240, "R": 30,  "CC": 16,  "paint_fn": paint_raw_aluminum,    "desc": "Bare unfinished aluminum sheet metal",
                         "noise_scales": [4, 8], "noise_weights": [0.4, 0.6], "noise_M": 25, "noise_R": 25},
    "sandblasted":      { "base_spec_fn": spec_sandblasted_v2,"M": 180, "R": 150, "CC": 155, "paint_fn": paint_sandblasted_v2, "desc": "Raw stripped metal - massive high frequency sharp static grit with omni-scattering reflections (CC=155 flat)"},
    # ── EXOTIC & COLOR-SHIFT ─────────────────────────────────────────
    "chameleon":        {"M": 160, "R": 25,  "CC": 16, "paint_fn": paint_cp_chameleon,  "desc": "Dual-tone color-shift angle-dependent",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 1.8, "noise_M": 60, "noise_R": 35},
    "iridescent":       {"M": 255, "R": 10,  "CC": 16, "paint_fn": paint_cp_iridescent, "desc": "Norse mythology rainbow bridge - hyper-metallic multidimensional lattice", "noise_scales": [2, 4], "noise_M": 100, "noise_R": 30},
    # ── WRAP & COATING ───────────────────────────────────────────────
    # ⚠️ FIXED 2026-03-08: liquid_wrap M was 80 (metallic) - rubber/vinyl wraps are dielectric.
    "liquid_wrap":      {"M": 0,   "R": 110, "CC": 50,  "paint_fn": paint_satin_wrap,      "desc": "Liquid rubber peel coat - dielectric, the rubber IS the clearcoat layer (CC=50 satin)"},
    "primer":           {"M": 0,   "R": 210, "CC": 180, "paint_fn": paint_none,     "desc": "Raw primer - zero sheen, CC=180 near-maximum degradation"},
    "satin_wrap":       {"M": 0,   "R": 130, "CC": 60,  "paint_fn": paint_satin_wrap,      "desc": "Vinyl wrap satin surface - the film IS the coat layer (CC=60)"},
    # ── ORGANIC / PERLIN NOISE ───────────────────────────────────────
    "living_matte":     {"M": 0,   "R": 190, "CC": 140, "paint_fn": paint_none, "desc": "Organic matte - low organic sheen, CC=140"},
    "organic_metal":    {"M": 210, "R": 45,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Organic flowing metallic with Perlin noise terrain",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "noise_M": 35, "noise_R": 20, "noise_CC": 8},
    "terrain_chrome":   {"M": 250, "R": 8,   "CC": 16,  "paint_fn": paint_chrome_brighten, "desc": "Chrome with Perlin terrain-like distortion in roughness",
                         "perlin": True, "perlin_octaves": 5, "perlin_persistence": 0.45, "noise_M": 0, "noise_R": 25},
    # ── WORN & DEGRADED CLEARCOAT (CC=81–255) ────────────────────────────────
    # track_worn: REMOVED per audit 2026-03-15
    "sun_fade":         {"M": 60,  "R": 130, "CC": 120, "paint_fn": paint_none,            "desc": "UV sun-damaged paint - bleached, chalky, coat breaking down (CC=120)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 30, "noise_CC": 20},
    "acid_etch":        {"M": 100, "R": 110, "CC": 130, "paint_fn": paint_patina_green,    "desc": "Acid-rain etched surface - pitted with partial clearcoat failure (CC=130)",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.4, 0.3, 0.3], "noise_M": 20, "noise_R": 25, "noise_CC": 25},
    "oxidized":         {"M": 180, "R": 70,  "CC": 160, "paint_fn": paint_burnt_metal,     "desc": "Oxidized metallic - rust bloom, clearcoat near-destroyed (CC=160)",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 35, "noise_CC": 30},
    "chalky_base":      {"M": 0,   "R": 210, "CC": 230, "paint_fn": paint_none,  "desc": "Chalky oxidised flat - CC=230 near-maximum degradation, powdery dead surface"},
    "barn_find":        { "base_spec_fn": spec_racing_heritage,"M": 80,  "R": 160, "CC": 210, "paint_fn": paint_primer_flat,     "desc": "Barn-find condition - decades of clearcoat breakdown, deep chalky flat (CC=210)",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.7, "perlin_lacunarity": 1.8, "noise_M": 10, "noise_R": 40, "noise_CC": 35},
    "crumbling_clear":  {"M": 30,  "R": 180, "CC": 235, "paint_fn": paint_none,    "desc": "Peeling, crumbling clearcoat - paint underneath showing through (CC=235)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.2, "noise_M": 8, "noise_R": 30, "noise_CC": 35},
    "destroyed_coat":   {"M": 0,   "R": 210, "CC": 255, "paint_fn": paint_none,            "desc": "Completely destroyed clearcoat - maximum degradation, pure chalk-rough (CC=255)"},

    # ══════════════════════════════════════════════════════════════════════
    # ADDED 2026-03-08 - Full JS→Python sync pass  (82 bases, all categories)
    # ══════════════════════════════════════════════════════════════════════

    # ── METALLIC STANDARD ─────────────────────────────────────────────────
    "candy_apple":      { "base_spec_fn": spec_metallic_standard,"M": 230, "R": 2, "CC": 24, "paint_fn": paint_smoked_darken, "desc": "A deeply unholy crimson candy gloss that pulls light into a violently crushed shadow point", "noise_scales": [4], "noise_M": 250, "noise_R": -10},
    "champagne":        { "base_spec_fn": spec_metallic_standard,"M": 200, "R": 30,  "CC": 16, "paint_fn": paint_warm_metal,      "desc": "Champagne metallic - warm gold-silver, French sparkling wine colour",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 20, "noise_R": 12},
    "metal_flake_base": { "base_spec_fn": spec_metallic_standard,"M": 215, "R": 28,  "CC": 40, "paint_fn": paint_subtle_flake,    "desc": "Metal flake base - heavy visible coarse metalflake in clear, classic show-car base",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 40, "noise_R": 15},
    "original_metal_flake": {"M": 250, "R": 50,  "CC": 30, "paint_fn": paint_subtle_flake, "desc": "Exploding star massive metallic chunks sealed in aerospace clear", "noise_scales": [1, 2, 4], "noise_M": 150, "noise_R": 80},
    "champagne_flake":  {"M": 255, "R": 0, "CC": 16, "paint_fn": paint_warm_metal, "desc": "A hyper-reflective pure 24K gold with absolute 0 roughness and high metal flake scaling", "noise_scales": [1, 2], "noise_M": 50},
    "fine_silver_flake": {"M": 0, "R": 5, "CC": 16, "paint_fn": paint_diamond_sparkle, "desc": "A dielectric clear thick resin suspending pure crushed silver mica shards", "noise_scales": [8, 16], "noise_M": 150},
    "blue_ice_flake":   {"M": 200, "R": 5, "CC": 30, "paint_fn": paint_ice_cracks, "desc": "Jagged frozen ice fractals catching deep light in a frozen state", "perlin": True, "perlin_octaves": 5, "noise_M": -50, "noise_R": 60},
    "bronze_flake":     {"M": 100, "R": 120, "CC": 100, "paint_fn": paint_patina_green, "desc": "10,000-year oxidized shipwreck brass, aggressively dripping with rich verdigris (CC=100 satin)", "perlin": True, "perlin_octaves": 4, "noise_R": 100},
    "gunmetal_flake":   {"M": 210, "R": 85,  "CC": 16, "paint_fn": paint_chameleon_shift, "desc": "Geometric stair-step oxidation layering of Bismuth", "perlin": True, "perlin_octaves": 5, "perlin_lacunarity": 3.0, "noise_M": 50, "noise_R": 60},
    "green_flake":      {"M": 180, "R": 20, "CC": 50, "paint_fn": paint_interference_shift, "desc": "Dark space meteorite that fades to an intense glowing neon green at its specular angles", "noise_scales": [2, 4], "noise_M": 100},
    "fire_flake":       {"M": 220, "R": 80, "CC": 20, "paint_fn": paint_burnt_metal, "desc": "The violent surface of the sun exploding with massive bright spots of solar plasma", "perlin": True, "perlin_octaves": 3, "noise_M": 150, "noise_R": 50},
    "midnight_pearl":   { "base_spec_fn": spec_metallic_standard,"M": 175, "R": 22,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Midnight pearl - deep dark paint with hidden pearl sparkle visible at angles",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 12},
    "pearlescent_white": {"M": 120, "R": 20,  "CC": 16, "paint_fn": paint_tri_coat_depth,  "desc": "Pearl white - tri-coat pearlescent white, deep directional sparkle",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 10},
    "pewter":           { "base_spec_fn": spec_metallic_standard,"M": 100, "R": 90, "CC": 80, "paint_fn": paint_chameleon_shift, "desc": "A dark, cursed grey meta-lead finish pulsing with forbidden underworld geometry (CC=80 satin)", "perlin": True, "perlin_octaves": 3, "noise_R": 40},

    # ── OEM AUTOMOTIVE ────────────────────────────────────────────────────
    "ambulance_white":  { "base_spec_fn": spec_oem_automotive,"M": 0,   "R": 8,   "CC": 16, "paint_fn": paint_none,            "desc": "Ambulance white - high-visibility emergency gloss white, pure dielectric"},
    "dealer_pearl":     { "base_spec_fn": spec_oem_automotive,"M": 80,  "R": 15,  "CC": 16, "paint_fn": paint_tri_coat_depth,  "desc": "Dealer pearl - typical dealership tri-coat pearl upgrade, subtle directional shimmer",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 8},
    "factory_basecoat": { "base_spec_fn": spec_oem_automotive,"M": 130, "R": 30,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Factory basecoat - standard OEM metallic, the average showroom car that left the plant",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 20, "noise_R": 12},
    "fire_engine":      {"M": 0,   "R": 6,   "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "Fire engine red - deep wet apparatus red, dielectric, maximum gloss (R=6)"},
    "fleet_white":      { "base_spec_fn": spec_oem_automotive,"M": 0, "R": 18, "CC": 16, "paint_fn": paint_ceramic_gloss, "desc": "Fleet white - crosslinked polyurethane commercial white, durable uniform dielectric finish", "perlin": True, "noise_R": 10},
    "police_black":     {"M": 0,   "R": 10,  "CC": 16, "paint_fn": paint_none,            "desc": "Police black - law enforcement glossy black, dielectric, mirror-like"},
    "school_bus":       { "base_spec_fn": spec_oem_automotive,"M": 0, "R": 15, "CC": 16, "paint_fn": paint_electric_blue_tint, "desc": "School bus yellow - Federal Standard 13432 chrome yellow with UV stabilizer haze"},
    "showroom_clear":   { "base_spec_fn": spec_oem_automotive,"M": 10, "R": 3, "CC": 16, "paint_fn": paint_ceramic_gloss, "desc": "Showroom clear - multi-layer Fresnel clearcoat stack, deep wet-look mirror finish", "perlin": True, "perlin_octaves": 4, "noise_R": 4},
    "taxi_yellow":      { "base_spec_fn": spec_oem_automotive,"M": 3, "R": 25, "CC": 110, "paint_fn": paint_burnt_metal, "desc": "Taxi yellow - UV-photodegraded cab yellow with chalking and mechanical wear zones (CC=110)", "perlin": True, "perlin_octaves": 4, "noise_R": 30},

    # ── PREMIUM LUXURY ────────────────────────────────────────────────────
    "bentley_silver":   { "base_spec_fn": spec_premium_luxury,"M": 235, "R": 12,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Bentley silver - Rolls-Royce/Bentley ultra-fine silver metallic",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 15, "noise_R": 6},
    "bugatti_blue":     { "base_spec_fn": spec_premium_luxury,"M": 180, "R": 10,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Bugatti Bleu de France - signature Bugatti deep two-tone blue",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 20, "noise_R": 6},
    "ferrari_rosso":    { "base_spec_fn": spec_premium_luxury,"M": 120, "R": 4, "CC": 22, "paint_fn": paint_fine_sparkle, "desc": "Ferrari Rosso Corsa - triple-layer candy coat with Beer-Lambert pigment absorption, deep clearcoat", "noise_scales": [2, 4, 8], "noise_M": 50, "noise_R": 8},
    "koenigsegg_clear": { "base_spec_fn": spec_premium_luxury,"M": 80,  "R": 20,  "CC": 16, "paint_fn": paint_forged_carbon,   "desc": "Koenigsegg clear carbon - visible clear-coated forged weave, semi-metallic",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 20, "noise_R": 15},
    "lamborghini_verde": { "base_spec_fn": spec_premium_luxury,"M": 0,   "R": 6,   "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "Lambo Verde Mantis - electric green dielectric, ceramic-like gloss surface"},
    "maybach_two_tone": { "base_spec_fn": spec_premium_luxury,"M": 180, "R": 12,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Maybach two-tone - Mercedes-Maybach duo-tone luxury split metallic",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 15, "noise_R": 6},
    "mclaren_orange":   { "base_spec_fn": spec_premium_luxury,"M": 0,   "R": 6,   "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "McLaren Papaya Spark - iconic McLaren orange, dielectric ceramic-smooth"},
    "pagani_tricolore": { "base_spec_fn": spec_premium_luxury,"M": 160, "R": 15,  "CC": 16, "paint_fn": paint_tricolore_shift,  "desc": "Pagani tricolore - premium three-tone angle-resolved shift paint",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 1.8, "noise_M": 50, "noise_R": 25},
    "porsche_pts":      { "base_spec_fn": spec_premium_luxury,"M": 150, "R": 14,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Porsche PTS - Paint-to-Sample deep custom coat with visible metallic depth",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 20, "noise_R": 8},

    # ── RACING HERITAGE ───────────────────────────────────────────────────
    "asphalt_grind":    { "base_spec_fn": spec_racing_heritage,"M": 30,  "R": 210, "CC": 200, "paint_fn": paint_primer_flat,     "desc": "Asphalt grind - rough road-surface texture, maximum roughness, zero coat (CC=200 dead flat)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 10, "noise_R": 35},
    "bullseye_chrome":  { "base_spec_fn": spec_racing_heritage,"M": 240, "R": 3,   "CC": 16, "paint_fn": paint_chrome_brighten, "desc": "Bullseye chrome - concentric Airy diffraction rings on polished chrome surface", "perlin": True, "perlin_octaves": 1, "perlin_persistence": 0.8, "noise_M": 5, "noise_R": 2},
    "checkered_chrome": { "base_spec_fn": spec_racing_heritage,"M": 250, "R": 4,   "CC": 16,  "paint_fn": paint_chrome_brighten, "desc": "Checkered chrome - polished chrome with checkered-flag reflection depth",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 12, "noise_R": 5},
    # dirt_track_satin: REMOVED per audit 2026-03-15
    "drag_strip_gloss": { "base_spec_fn": spec_racing_heritage,"M": 140, "R": 6,   "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "Drag strip gloss - ultra-polished show car finish, came off the trailer",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 25, "noise_R": 6},
    "endurance_ceramic": { "base_spec_fn": spec_racing_heritage,"M": 15, "R": 80, "CC": 50, "paint_fn": paint_volcanic_ash, "desc": "Endurance ceramic (Apollo Shield Char) - thermal fatigue micro-craze, charred reentry plating", "perlin": True, "perlin_octaves": 5, "noise_M": 10, "noise_R": 25},
    # heat_shield: REMOVED per audit 2026-03-15
    "pace_car_pearl":   { "base_spec_fn": spec_racing_heritage,"M": 110, "R": 16,  "CC": 16, "paint_fn": paint_tri_coat_depth,  "desc": "Pace car pearl - official pace car triple-pearl finish, directional shimmer",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 22, "noise_R": 8},
    # pit_lane_matte: REMOVED per audit 2026-03-15
    "race_day_gloss":   { "base_spec_fn": spec_racing_heritage,"M": 0,   "R": 2,   "CC": 16, "paint_fn": paint_ceramic_gloss, "desc": "Race day gloss - multi-polish wet-look total internal reflection coating, fresh off the trailer", "perlin": True, "noise_R": 3},
    "rally_mud":        { "base_spec_fn": spec_racing_heritage,"M": 20,  "R": 185, "CC": 80, "paint_fn": paint_primer_flat,     "desc": "Rally mud - partially mud-splattered paint, coat degrading from abuse",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 8, "noise_R": 30},
    # rat_rod_primer: REMOVED per audit 2026-03-15
    "stock_car_enamel": { "base_spec_fn": spec_racing_heritage,"M": 0,   "R": 18,  "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "Stock car enamel - traditional thick NASCAR enamel, hard-baked dielectric"},
    "victory_lane":     { "base_spec_fn": spec_racing_heritage,"M": 185, "R": 16,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Victory lane - champagne-soaked celebration metallic, dense festive sparkle",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 30, "noise_R": 10},

    # ── SATIN & WRAP ──────────────────────────────────────────────────────
    "brushed_wrap":     { "base_spec_fn": spec_satin_wrap,"M": 180, "R": 75,  "CC": 35, "paint_fn": paint_brushed_grain,   "desc": "Brushed wrap - brushed metal vinyl film, directional grain visible through coat",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 20, "noise_R": 18},
    "chrome_wrap":      { "base_spec_fn": spec_satin_wrap,"M": 255, "R": 3,   "CC": 16,  "paint_fn": paint_chrome_brighten, "desc": "Chrome wrap - mirror chrome vinyl, slightly textured vs real chrome",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 12, "noise_R": 5},
    "color_flip_wrap":  { "base_spec_fn": spec_satin_wrap,"M": 155, "R": 22,  "CC": 16, "paint_fn": paint_chameleon_shift,  "desc": "Color flip wrap - dual-colour angle-shift vinyl film",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 1.8, "noise_M": 45, "noise_R": 22},
    "gloss_wrap":       {"M": 0,   "R": 8,   "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "Gloss wrap - high-gloss smooth vinyl, dielectric, near-OEM gloss look"},
    "matte_wrap":       { "base_spec_fn": spec_satin_wrap,"M": 0,   "R": 145, "CC": 165, "paint_fn": paint_satin_wrap,      "desc": "Matte wrap - dead-flat vinyl, zero sheen, the wrap IS the protection layer (CC=165 flat)"},
    "stealth_wrap":     { "base_spec_fn": spec_satin_wrap,"M": 120, "R": 200, "CC": 170, "paint_fn": paint_glass_tint, "desc": "Predator-style refractive stealth boundary (CC=170 flat)", "perlin": True, "perlin_octaves": 4, "perlin_lacunarity": 2.8, "noise_M": 120, "noise_R": -100},
    "textured_wrap":    { "base_spec_fn": spec_satin_wrap,"M": 0,   "R": 95,  "CC": 40, "paint_fn": paint_galvanized_speckle, "desc": "Textured wrap - orange-peel embossed vinyl, slight speckle",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 0, "noise_R": 20},

    # ── SHOKK SERIES ──────────────────────────────────────────────────────
    "shokk_blood":      {"M": 200, "R": 14,  "CC": 16, "paint_fn": paint_plasma_shift,    "desc": "SHOKK Blood - deep arterial red metallic, dark micro-shifted edges",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 10},
    "shokk_pulse":      {"M": 220, "R": 10,  "CC": 16, "paint_fn": paint_electric_blue_tint, "desc": "SHOKK Pulse - electric pulse wave metallic, Shokker signature hot-pink/blue",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 35, "noise_R": 8},
    "shokk_static":     {"M": 210, "R": 18,  "CC": 16, "paint_fn": paint_plasma_shift,    "desc": "SHOKK Static - crackling static interference metallic blue-gray",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 30, "noise_R": 10},
    "shokk_venom":      {"M": 0,   "R": 10,  "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "SHOKK Venom - toxic acid green-yellow dielectric, ceramic-smooth reactive",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 40, "noise_R": 25},
    "shokk_void":       {"M": 0,   "R": 230, "CC": 230, "paint_fn": paint_rubber_absorb,   "desc": "SHOKK Void - near-vantablack, absolute absorption with subtle edge shimmer (CC=230 dead flat)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 2, "noise_R": 30},

    # ── WEATHERED & AGED ──────────────────────────────────────────────────
    "acid_rain":        { "base_spec_fn": spec_weathered_aged,"M": 60,  "R": 130, "CC": 140, "paint_fn": paint_patina_green,   "desc": "Acid rain - chemical etch damage, partial coat failure with oxidation patches",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 20, "noise_R": 30, "noise_CC": 20},
    "desert_worn":      { "base_spec_fn": spec_weathered_aged,"M": 20,  "R": 160, "CC": 130, "paint_fn": paint_tactical_flat,  "desc": "Desert worn - sand-blasted UV-hammered surface, coat nearly gone",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 8, "noise_R": 30, "noise_CC": 25},
    "oxidized_copper":  { "base_spec_fn": spec_weathered_aged,"M": 140, "R": 95,  "CC": 120, "paint_fn": paint_patina_green,    "desc": "Oxidized copper - fully green-oxidized Statue-of-Liberty patina (CC=120)",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 35},
    "salt_corroded":    { "base_spec_fn": spec_weathered_aged,"M": 130, "R": 140, "CC": 120, "paint_fn": paint_galvanized_speckle, "desc": "Salt corroded - coastal salt-air corrosion, speckled oxide with coat failure",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 25, "noise_R": 30, "noise_CC": 25},
    "sun_baked":        { "base_spec_fn": spec_weathered_aged,"M": 0,   "R": 150, "CC": 155, "paint_fn": paint_volcanic_ash,   "desc": "Sun baked - UV-cooked faded chalky surface, dielectric, coat crumbling",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 30, "noise_CC": 25},
    "vintage_chrome":   { "base_spec_fn": spec_weathered_aged,"M": 240, "R": 20,  "CC": 50,  "paint_fn": paint_antique_patina,  "desc": "Vintage chrome - 1950s chrome with warm tarnish and cloudy oxidation spots (CC=50 aged)",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 15},

    # ── EXTREME & EXPERIMENTAL ────────────────────────────────────────────
    "bioluminescent":   { "base_spec_fn": spec_bioluminescent,"M": 0,   "R": 10,  "CC": 16, "paint_fn": paint_bioluminescent, "desc": "Bioluminescent - deep sea organism soft internal glow, dielectric organic surface",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 12},
    "dark_matter":      { "base_spec_fn": spec_dark_matter,"M": 0,   "R": 240, "CC": 220, "paint_fn": paint_dark_matter,   "desc": "Dark matter - ultra-dark hidden angle-dependent reveal, maximum absorption (CC=220 dead flat)",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.7, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 35},
    "holographic_base": { "base_spec_fn": spec_holographic_base,"M": 200, "R": 6,   "CC": 16, "paint_fn": paint_holographic_base, "desc": "Holographic base - full prismatic rainbow hologram base, strong angle shift",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 50, "noise_R": 20},
    "neutron_star":     { "base_spec_fn": spec_black_hole_accretion,"M": 0, "R": 255, "CC": 255, "paint_fn": paint_black_hole_accretion, "desc": "Total void black sink surrounded by an intense glowing ring of orbital light reflection", "noise_scales": [2], "noise_R": 250},
    "plasma_core":      { "base_spec_fn": spec_plasma_core,"M": 220, "R": 8,   "CC": 16,  "paint_fn": paint_plasma_core,    "desc": "Plasma core - glowing plasma reactor metallic, electric purple-blue surface",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 40, "noise_R": 15},
    "quantum_black":    { "base_spec_fn": spec_quantum_black,"M": 0,   "R": 255, "CC": 235, "paint_fn": paint_quantum_black,   "desc": "Quantum black - near-perfect light absorption, maximum possible roughness (CC=235 dead flat)"},
    "solar_panel":      { "base_spec_fn": spec_solar_panel,"M": 15,  "R": 45,  "CC": 16, "paint_fn": paint_solar_panel,   "desc": "Solar panel - dark photovoltaic blue-black, slightly metallic cell grid look",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 8, "noise_R": 15},
    "superconductor":   { "base_spec_fn": spec_absolute_zero,"M": 255, "R": 90, "CC": 40, "paint_fn": paint_absolute_zero, "desc": "Heavily frosted metal sitting indefinitely at absolute zero, perpetually generating micro-ice", "noise_scales": [8, 16, 32], "noise_R": 90},

    # ── PARADIGM BASES ────────────────────────────────────────────────────
    # These IDs appear in the JS BASES array at the end - special physics
    "singularity":      {"M": 120, "R": 0, "CC": 16, "paint_fn": paint_iridescent_shift, "desc": "Theoretical boundary physics shifting colors infinitely toward standard absolute zero", "perlin": True, "perlin_octaves": 6, "noise_M": 200, "noise_R": -50},
    "liquid_obsidian":  {"M": 255, "R": 0,   "CC": 16,  "paint_fn": paint_obsidian_depth,  "desc": "Liquid obsidian - flowing glass-metal phase boundary, metallic oscillates at near-zero roughness",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 60, "noise_R": 10},
    "prismatic":        {"M": 200, "R": 10, "CC": 80, "paint_fn": paint_iridescent_shift, "desc": "Over-tuned holographic logic breaking standard M/R bounds to create truly impossible colors", "perlin": True, "perlin_octaves": 6, "noise_M": 255, "noise_R": 80},
    "p_mercury":        {"M": 255, "R": 2,   "CC": 16,  "paint_fn": paint_mercury_pool,    "desc": "Mercury (PARADIGM) - liquid metal pooling, flowing silver mercury surface",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.4, "perlin_lacunarity": 2.0, "noise_M": 15, "noise_R": 6},
    "p_phantom":        {"M": 0,   "R": 35,  "CC": 16, "paint_fn": paint_moonstone_adularescence, "desc": "Phantom (PARADIGM) - barely-there translucent mist, ghostly fog-like presence",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 15},
    "p_volcanic":       {"M": 60,  "R": 180, "CC": 120, "paint_fn": paint_burnt_metal,     "desc": "Volcanic (PARADIGM) - lava cooling to rock, glowing heat veins through dark stone (CC=120 rough surface)",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.65, "perlin_lacunarity": 2.0, "noise_M": 25, "noise_R": 35},
    "arctic_ice":       {"M": 0,   "R": 6,   "CC": 16, "paint_fn": paint_moonstone_adularescence, "desc": "Arctic ice - frozen crystalline surface, cracked ice with blue-white interior",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 10},
    "carbon_weave":     {"M": 70,  "R": 35,  "CC": 16, "paint_fn": paint_carbon_weave,    "desc": "Carbon weave - visible diagonal twill weave carbon fiber pattern under coat",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 20, "noise_R": 15},
    "nebula":           {"M": 0,   "R": 25,  "CC": 16, "paint_fn": paint_opal_fire,        "desc": "Nebula - space dust cloud, purple-blue cosmic nebula with star sparkles",
                         "perlin": True, "perlin_octaves": 5, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 20},

    # PARADIGM — pixel-level random spec ("every spec at once")
    "quantum_foam":     {"M": 128, "R": 128, "CC": 80, "paint_fn": paint_none, "desc": "Quantum Foam (PARADIGM) - every possible reflectance/gloss/matte at once at pixel scale; neutral base so spec is the star",
                         "perlin": True, "perlin_octaves": 8, "noise_M": 255, "noise_R": 255, "noise_CC": 200},
    "infinite_finish":  {"M": 128, "R": 128, "CC": 80, "paint_fn": paint_none, "desc": "Infinite Finish (PARADIGM) - same idea as Quantum Foam, different seed; pair them for variants",
                         "perlin": True, "perlin_octaves": 6, "noise_M": 200, "noise_R": 200, "noise_CC": 150},

    # ── ALIAS FIX ─────────────────────────────────────────────────────────
    # UI uses 'submarine_black', registry previously had 'sub_black'.
    # Both now exist. sub_black kept for backward compat.
    "submarine_black":  { "base_spec_fn": spec_industrial_tactical,"M": 0,   "R": 235, "CC": 215, "paint_fn": paint_rubber_absorb,   "desc": "Submarine hull black - anechoic submarine hull coating, absolute light absorption (CC=215 dead flat)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 3, "noise_R": 30},
}

# ── SHOKK SERIES v2 - 20 color-shift PBR bases ──────────────────────────────
try:
    from engine.shokk_series import SHOKK_BASES as _SHOKK_V2
    BASE_REGISTRY.update(_SHOKK_V2)
    print(f"[SHOKK Series] Loaded {len(_SHOKK_V2)} color-shift bases")
except Exception as _shokk_exc:
    print(f"[SHOKK Series] Load failed: {_shokk_exc}")


def _apply_staging_registry_patches():
    """Patch BASE_REGISTRY with v2 implementations from engine.paint_v2 (no _staging dependency)."""
    try:
        import numpy as np
        import importlib

        def _adapt_paint_fn_for_scalar_bb(fn):
            def _wrapped(paint, shape, mask, seed, pm, bb):
                bb_val = bb
                try:
                    if np.isscalar(bb):
                        h, w = shape[:2] if isinstance(shape, (tuple, list)) and len(shape) >= 2 else paint.shape[:2]
                        bb_val = np.full((int(h), int(w)), float(bb), dtype=np.float32)
                    elif hasattr(bb, "ndim") and bb.ndim == 0:
                        h, w = shape[:2] if isinstance(shape, (tuple, list)) and len(shape) >= 2 else paint.shape[:2]
                        bb_val = np.full((int(h), int(w)), float(bb), dtype=np.float32)
                except Exception:
                    bb_val = bb
                return fn(paint, shape, mask, seed, pm, bb_val)
            return _wrapped

        categories = [
            "brushed_directional", "candy_special", "carbon_composite", "ceramic_glass",
            "chrome_mirror", "exotic_metal", "finish_basic", "metallic_flake", "metallic_standard",
            "military_tactical", "oem_automotive", "paradigm_scifi", "premium_luxury",
            "racing_heritage", "raw_weathered", "shokk_series", "weathered_worn", "wrap_vinyl",
        ]
        paint_updates = 0
        spec_updates = 0
        for category in categories:
            try:
                patch_mod = importlib.import_module("engine.registry_patches." + category + "_reg")
                mod = importlib.import_module("engine.paint_v2." + category)
            except ImportError:
                continue
            reg_patch = getattr(patch_mod, "REGISTRY_PATCH", {}) or {}
            spec_patch = getattr(patch_mod, "SPEC_PATCH", {}) or {}
            for base_id, fn_name in reg_patch.items():
                if base_id in BASE_REGISTRY and hasattr(mod, fn_name):
                    BASE_REGISTRY[base_id]["paint_fn"] = _adapt_paint_fn_for_scalar_bb(getattr(mod, fn_name))
                    paint_updates += 1
            for base_id, fn_name in spec_patch.items():
                if base_id in BASE_REGISTRY and hasattr(mod, fn_name):
                    BASE_REGISTRY[base_id]["base_spec_fn"] = getattr(mod, fn_name)
                    spec_updates += 1
        if paint_updates or spec_updates:
            print(f"[V2 Registry] base_registry_data patched paint/spec: {paint_updates}/{spec_updates}")
    except Exception as exc:
        print(f"[V2 Registry] base_registry_data patch skipped: {exc}")


_apply_staging_registry_patches()
