"""
engine/base_registry_data.py - Canonical BASE_REGISTRY (96 bases).
Uses paint functions from engine.spec_paint only. No monolith def _paint_noop(paint, shape, mask, seed, pm, bb):
    return paint

import.
BLEND_BASES (10 entries) stay in shokker_engine_v2 and are merged by registry.py.
Audited & expanded 2026-03-08 - fixed 8 wrong-value entries, added 36+ missing bases.
"""
# COLORSHOXX — premium color-shifting finishes with married paint+spec
from engine.paint_v2.structural_color import (
    paint_colorshoxx_inferno, spec_colorshoxx_inferno,
    paint_colorshoxx_arctic, spec_colorshoxx_arctic,
    paint_colorshoxx_venom, spec_colorshoxx_venom,
    paint_colorshoxx_solar, spec_colorshoxx_solar,
    paint_colorshoxx_phantom, spec_colorshoxx_phantom,
    # Wave 2 — 10 extreme dual-tone
    paint_cx_chrome_void, spec_cx_chrome_void,
    paint_cx_blood_mercury, spec_cx_blood_mercury,
    paint_cx_neon_abyss, spec_cx_neon_abyss,
    paint_cx_glacier_fire, spec_cx_glacier_fire,
    paint_cx_obsidian_gold, spec_cx_obsidian_gold,
    paint_cx_electric_storm, spec_cx_electric_storm,
    paint_cx_rose_chrome, spec_cx_rose_chrome,
    paint_cx_toxic_chrome, spec_cx_toxic_chrome,
    paint_cx_midnight_chrome, spec_cx_midnight_chrome,
    paint_cx_white_lightning, spec_cx_white_lightning,
    # Wave 2 — 5 three-color
    paint_cx_aurora_borealis, spec_cx_aurora_borealis,
    paint_cx_dragon_scale, spec_cx_dragon_scale,
    paint_cx_frozen_nebula, spec_cx_frozen_nebula,
    paint_cx_hellfire, spec_cx_hellfire,
    paint_cx_ocean_trench, spec_cx_ocean_trench,
    # Wave 2 — 5 four-color
    paint_cx_supernova, spec_cx_supernova,
    paint_cx_prism_shatter, spec_cx_prism_shatter,
    paint_cx_acid_rain, spec_cx_acid_rain,
    paint_cx_royal_spectrum, spec_cx_royal_spectrum,
    paint_cx_apocalypse, spec_cx_apocalypse,
)

# MORTAL SHOKK — fighting-game-inspired married paint+spec finishes
from engine.paint_v2.mortal_shokkbat import (
    paint_ms_frozen_fury, spec_ms_frozen_fury,
    paint_ms_venom_strike, spec_ms_venom_strike,
    paint_ms_thunder_lord, spec_ms_thunder_lord,
    paint_ms_chrome_cage, spec_ms_chrome_cage,
    paint_ms_dragon_flame, spec_ms_dragon_flame,
    paint_ms_royal_edge, spec_ms_royal_edge,
    paint_ms_feral_grin, spec_ms_feral_grin,
    paint_ms_acid_scale, spec_ms_acid_scale,
    paint_ms_soul_drain, spec_ms_soul_drain,
    paint_ms_emerald_shadow, spec_ms_emerald_shadow,
    paint_ms_void_walker, spec_ms_void_walker,
    paint_ms_ghost_vapor, spec_ms_ghost_vapor,
    paint_ms_shape_shift, spec_ms_shape_shift,
    paint_ms_titan_bronze, spec_ms_titan_bronze,
    paint_ms_war_hammer, spec_ms_war_hammer,
)

# NEON UNDERGROUND — blacklight reactive neon-glow married paint+spec finishes
from engine.paint_v2.neon_underground import (
    paint_neon_pink_blaze, spec_neon_pink_blaze,
    paint_neon_toxic_green, spec_neon_toxic_green,
    paint_neon_electric_blue, spec_neon_electric_blue,
    paint_neon_blacklight, spec_neon_blacklight,
    paint_neon_orange_hazard, spec_neon_orange_hazard,
    paint_neon_red_alert, spec_neon_red_alert,
    paint_neon_cyber_yellow, spec_neon_cyber_yellow,
    paint_neon_ice_white, spec_neon_ice_white,
    paint_neon_dual_glow, spec_neon_dual_glow,
    paint_neon_rainbow_tube, spec_neon_rainbow_tube,
)

# ANIME INSPIRED — anime/manga-style married paint+spec finishes
from engine.paint_v2.anime_style import (
    paint_anime_cel_shade_chrome, spec_anime_cel_shade_chrome,
    paint_anime_speed_lines, spec_anime_speed_lines,
    paint_anime_sparkle_burst, spec_anime_sparkle_burst,
    paint_anime_gradient_hair, spec_anime_gradient_hair,
    paint_anime_mecha_plate, spec_anime_mecha_plate,
    paint_anime_sakura_scatter, spec_anime_sakura_scatter,
    paint_anime_energy_aura, spec_anime_energy_aura,
    paint_anime_comic_halftone, spec_anime_comic_halftone,
    paint_anime_neon_outline, spec_anime_neon_outline,
    paint_anime_crystal_facet, spec_anime_crystal_facet,
)

# IRIDESCENT INSECTS — insect-inspired structural-color married paint+spec finishes
from engine.paint_v2.iridescent_insects import (
    paint_beetle_jewel, spec_beetle_jewel,
    paint_beetle_rainbow, spec_beetle_rainbow,
    paint_butterfly_morpho, spec_butterfly_morpho,
    paint_butterfly_monarch, spec_butterfly_monarch,
    paint_dragonfly_wing, spec_dragonfly_wing,
    paint_scarab_gold, spec_scarab_gold,
    paint_moth_luna, spec_moth_luna,
    paint_beetle_stag, spec_beetle_stag,
    paint_wasp_warning, spec_wasp_warning,
    paint_firefly_glow, spec_firefly_glow,
)

from engine.paint_v2.paradigm_scifi import (
    paint_p_volcanic_v2,
    spec_p_volcanic,
)

from engine.paint_v2.exotic_metal import paint_liquid_titanium_v2

from engine.spec_paint import (
    # ── Research Session 6: 9 new base finishes ──
    spec_alubeam_base,
    paint_alubeam,
    spec_satin_candy_base,
    paint_satin_candy,
    spec_velvet_floc_base,
    paint_velvet_floc,
    spec_deep_pearl_base,
    paint_deep_pearl,
    spec_gunmetal_satin_base,
    paint_gunmetal_satin,
    spec_forged_carbon_vis_base,
    paint_forged_carbon_vis,
    spec_electroplated_gold_base,
    paint_electroplated_gold,
    spec_cerakote_pvd_base,
    paint_cerakote_pvd,
    spec_hypershift_spectral_base,
    paint_hypershift_spectral,
    # ── end Research Session 6 imports ──
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
    # paint_hummingbird_gorget — imported from structural_color V2 above
    # paint_labradorite_flash — imported from structural_color V2 above
    paint_ice_cracks,
    paint_infinite_warp,
    paint_interference_shift,
    paint_iridescent_shift,
    paint_singularity_v2,
    paint_martian_regolith,
    paint_mercury_pool,
    paint_mil_spec_od_v3,
    paint_mil_spec_tan_v2,
    # paint_morpho_blue — imported from structural_color V2 above
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
    paint_liquid_wrap_fn,
    paint_matte_flat,
    paint_scuffed_satin_fn,
    paint_silk_sheen,
    paint_smoked_darken,
    paint_solar_panel,
    paint_spectraflame,
    paint_submarine_black_v2,
    paint_subtle_flake,
    paint_tactical_flat,
    paint_desert_worn,
    paint_tinted_clearcoat,
    paint_tri_coat_depth,
    paint_tricolore_shift,
    paint_volcanic_ash,
    paint_warm_metal,
    paint_wet_gloss,
    paint_anodized_exotic,
    paint_chromaflair,
    paint_xirallic,
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
    spec_anodized_exotic_base,
    spec_chromaflair_base,
    spec_xirallic_base,
    spec_pearl_base,
    paint_sun_fade_v2,
)
from engine.paint_v2.chrome_mirror import (
    paint_chrome_mirror,
    paint_black_chrome_v2,
    paint_blue_chrome_v2,
    paint_red_chrome_v2,
    paint_satin_chrome_v2,
    paint_antique_chrome_v2,
    paint_bullseye_chrome_v2,
    paint_checkered_chrome_v2,
    paint_dark_chrome_v2,
    paint_vintage_chrome_v2,
    spec_chrome_mirror,
    spec_black_chrome,
    spec_blue_chrome,
    spec_red_chrome,
    spec_satin_chrome,
    spec_antique_chrome,
    spec_bullseye_chrome,
    spec_checkered_chrome,
    spec_dark_chrome,
    spec_vintage_chrome,
)
from engine.paint_v2.wrap_vinyl import paint_textured_wrap_v2
from engine.paint_v2.candy_special import (
    paint_opal_v2,
    spec_opal,
    spec_tri_coat_pearl,
)











# Enhanced Foundation — 30 premium bases with real spec+paint functions
from engine.paint_v2.foundation_enhanced import ENHANCED_FOUNDATION

# --- BASE MATERIAL REGISTRY ---
# 96+ bases. BLEND_BASES (10) are merged by registry.py from monolith.
BASE_REGISTRY = {
    # ── STANDARD FINISHES (FOUNDATION) ──────────────────────────────────────────────
    # Foundation: solid bases only, NO texture/pattern.
    # CC SCALE: 16=max gloss, 0=mirror/metallised, >16=progressively dull up to 255=maximum degradation.
    # The CC range is used deliberately here to spread these bases across the full sheen spectrum.
    "ceramic":          {"M": 10,  "R": 15,  "CC": 16, "paint_fn": paint_none,   "desc": "Ultra-smooth ceramic coating deep wet shine — FOUNDATION-AUDIT: noise_M 30→10 (ceramic should be uniformly non-metallic)",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.3, "perlin_lacunarity": 2.0, "noise_M": 10, "noise_R": 10},
    # 2026-04-20 HEENAN HARDMODE-FOUND-3 — gloss was bare dielectric
    # with no noise. Real fresh paint has tiny dust/wax micro-variation.
    # Add minimal high-freq perlin so the surface reads as "real" gloss
    # instead of computer-perfect plastic. Sponsor-safe.
    "gloss":            {"M": 0,   "R": 30,  "CC": 16,  "paint_fn": paint_none,        "desc": "Standard glossy clearcoat with painter-grade micro-variation — sponsor-safe foundation (HARDMODE-FOUND-3: added subtle micro-noise)",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.35, "perlin_lacunarity": 2.2, "noise_M": 3, "noise_R": 5},
    # 2026-04-20 HEENAN HARDMODE-FOUND-1 — piano_black was M=5, perfect
    # dielectric. Audi/BMW piano lacquer has slight metallic depth from
    # the under-base. M=18 + low-freq noise gives visible "deep liquid"
    # micro-modulation without breaking the mirror character.
    "piano_black":      {"M": 18,  "R": 15,  "CC": 16,  "paint_fn": paint_none, "base_spec_fn": spec_cg_glass, "desc": "Deep ebony piano black with liquid-lacquer depth modulation — Audi/BMW signature trim depth (HARDMODE-FOUND-1: M 5->18, added depth noise)",
                         "noise_scales": [32, 64, 128], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 8, "noise_R": 4},
    # 2026-04-20 HEENAN HARDMODE-FOUND-2 — wet_look was a pure dielectric
    # with zero noise. Add micro-perlin so the "fresh wax" surface has
    # visible flow-out variation; CC stays at max gloss but the spec
    # response now shows subtle wave-like depth.
    "wet_look":         {"M": 0,   "R": 22,  "CC": 16,  "paint_fn": paint_none,    "desc": "Deep wet clearcoat — fresh-waxed flow-out variation with concours depth (HARDMODE-FOUND-2: added micro-perlin)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.4, "perlin_lacunarity": 2.0, "noise_M": 4, "noise_R": 6},
    "semi_gloss":       {"M": 0,   "R": 55,  "CC": 40,  "paint_fn": paint_none,  "desc": "Semi-gloss - slight sheen, CC=40 mild dulling. FLAT-FIX: added perlin noise.",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 15, "noise_R": 8},
    "satin":            {"M": 0,   "R": 95,  "CC": 70,  "paint_fn": paint_none,       "desc": "Satin - mid sheen, CC=70 moderate clearcoat degradation — WEAK-014: noise variation",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_R": 20},
    "scuffed_satin":    {"M": 0,   "R": 160, "CC": 110, "paint_fn": paint_f_scuffed_satin, "desc": "Scuffed satin — WEAK-015 FIX: R=160 rougher+CC=110 duller than plain satin (was R=110, CC=90 — wrong direction)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_R": 30, "noise_M": 12},
    # 2026-04-20 HEENAN HARDMODE-FOUND-4 — silk had zero noise. Real silk
    # textile has fine directional sheen variation. Add fine fabric-like
    # noise so the silk foundation reads as "fabric-soft" instead of just
    # mid-CC dielectric.
    "silk":             {"M": 0,   "R": 85,  "CC": 60,  "paint_fn": paint_none,        "desc": "Silk — smooth low-reflection sheen with fabric-soft directional micro-variation (HARDMODE-FOUND-4: added fine-grain noise)",
                         "noise_scales": [32, 64, 128], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 6, "noise_R": 12},
    "eggshell":         {"M": 0,   "R": 130, "CC": 100, "paint_fn": paint_none,    "desc": "Eggshell - low sheen wall-paint finish, CC=100. FLAT-FIX: added perlin noise.",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 15, "noise_R": 8},
    # Foundation Bases — 2026-04-21 painter fix: ALL f_* entries are FLAT.
    # No noise_*, no perlin, no noise_scales/weights. A Foundation Base is
    # a pure material property: constant M, R, CC everywhere. The painter's
    # chosen paint colour shows through unchanged; the spec map gets a
    # constant, non-noisy material signal. If a painter wants visible
    # flake / grain / weave texture, that belongs in a Pattern or Spec
    # Pattern Overlay — NEVER baked into a Foundation.
    "f_pure_white":     {"M": 0,   "R": 145, "CC": 110, "paint_fn": paint_none,  "desc": "Pure white foundation - eggshell sheen"},
    "f_pure_black":     {"M": 0,   "R": 240, "CC": 190, "paint_fn": paint_none,  "desc": "Pure black foundation - near-flat, CC=190"},
    "f_neutral_grey":   {"M": 0,   "R": 185, "CC": 150, "paint_fn": paint_none,  "desc": "Neutral grey foundation - dull flat, CC=150"},
    "f_soft_gloss":     {"M": 0,   "R": 42,  "CC": 22,  "paint_fn": paint_none,  "desc": "Soft gloss foundation - near-gloss CC=22"},
    "f_soft_matte":     {"M": 0,   "R": 200, "CC": 165, "paint_fn": paint_none,  "desc": "Soft matte foundation - flat finish, CC=165"},
    "f_clear_satin":    {"M": 0,   "R": 100, "CC": 75,  "paint_fn": paint_none,  "desc": "Clear satin foundation - CC=75"},
    "f_warm_white":     {"M": 0,   "R": 120, "CC": 95,  "paint_fn": paint_none,  "desc": "Warm white foundation - eggshell-plus sheen, CC=95"},
    "f_chrome":         {"M": 255, "R": 2,   "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation chrome - pure mirror metallic, flat"},
    "f_satin_chrome":   {"M": 250, "R": 45,  "CC": 40,  "paint_fn": paint_none,  "desc": "Foundation satin chrome - silky satin metallic, flat"},
    "f_metallic":       {"M": 200, "R": 50,  "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation metallic - standard metallic flake, no color shift, flat"},
    "f_pearl":          {"M": 100, "R": 40,  "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation pearl - pearlescent sheen, flat"},
    "f_carbon_fiber":   {"M": 55,  "R": 30,  "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation carbon fiber - material baseline, flat (add `carbon_fiber` pattern for visible weave)"},
    "f_brushed":        {"M": 180, "R": 75,  "CC": 65,  "paint_fn": paint_none,  "desc": "Foundation brushed - directional grain metallic, flat (add a brushed Spec Pattern for grain texture)"},
    "f_frozen":         {"M": 160, "R": 85,  "CC": 130, "paint_fn": paint_none,  "desc": "Foundation frozen matte - icy matte metal, CC=130 deliberately flat"},
    "f_powder_coat":    {"M": 10,  "R": 120, "CC": 145, "paint_fn": paint_none,  "desc": "Foundation powder coat - thick textured coating, CC=145 no traditional clearcoat, flat"},
    "f_anodized":       {"M": 180, "R": 65,  "CC": 85,  "paint_fn": paint_none,  "desc": "Foundation anodized - anodized oxide layer finish, CC=85, flat"},
    "f_vinyl_wrap":     {"M": 0,   "R": 100, "CC": 110, "paint_fn": paint_none,  "desc": "Foundation vinyl wrap - vinyl material finish, CC=110 no clearcoat, flat"},
    "f_gel_coat":       {"M": 0,   "R": 15,  "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation gel coat - fiberglass gelcoat high-gloss, flat"},
    "f_baked_enamel":   {"M": 0,   "R": 18,  "CC": 20,  "paint_fn": paint_none,  "desc": "Foundation baked enamel - hard baked traditional enamel, flat"},
    # ── METALLIC & FLAKE ──────────────────────────────────────────────
    "copper":           {"M": 190, "R": 55,  "CC": 16, "paint_fn": paint_warm_metal,      "desc": "Warm oxidized copper metallic",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 35, "noise_R": 20},
    "diamond_coat":     {"M": 220, "R": 15,  "CC": 16, "paint_fn": paint_diamond_sparkle, "desc": "Diamond dust ultra-fine sparkle coat — GGX-FIX: R=3→15 (M=220 non-chrome metallic)",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 25, "noise_R": 8},
    "electric_ice":     {"M": 240, "R": 10,  "CC": 16, "paint_fn": paint_electric_blue_tint, "desc": "Icy electric blue metallic - cold neon shimmer",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 15, "noise_R": 8},
    "gunmetal":         {"M": 220, "R": 40,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Dark aggressive blue-gray metallic",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 30, "noise_R": 15},
    "metallic":         {"M": 200, "R": 50,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Standard metallic with visible flake",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 40, "noise_R": 18},
    "pearl":            {"M": 100, "R": 40,  "CC": 16, "paint_fn": paint_fine_sparkle, "base_spec_fn": spec_pearl_base,    "desc": "Pearlescent iridescent sheen — per-platelet M/R/CC variation, fine platelet flash. WEAK-031 FIX.",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 12},
    "plasma_metal":     {"M": 250, "R": 20,  "CC": 16, "paint_fn": paint_plasma_shift, "desc": "Extraterrestrial smart-metal with phase-shifting liquid surface", "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.3, "noise_M": 100, "noise_R": -10},
    "rose_gold":        {"M": 220, "R": 30, "CC": 16, "paint_fn": paint_rose_gold_tint, "desc": "Pink-gold metallic warm shimmer — BASE-011 FIX: M=220 (metallic alloy), R=30, CC=16",
                         "perlin": True, "perlin_octaves": 6, "noise_R": 40},
    # ⚠️ FIXED 2026-03-08: satin_gold CC was 0 - gold with matte clearcoat gets CC=16.
    "satin_gold":       {"M": 235, "R": 60,  "CC": 16, "paint_fn": paint_warm_metal,      "desc": "Satin gold metallic warm sheen - factory satin clearcoat (CC=16)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 15, "noise_R": 18},
    # ── CHROME & MIRROR ───────────────────────────────────────────────
    "chrome":           {"base_spec_fn": spec_chrome_mirror, "M": 255, "R": 2,   "CC": 16,  "paint_fn": paint_chrome_mirror, "desc": "Pure mirror chrome — Fresnel reflection + environment distortion",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 20, "noise_R": 8},
    "dark_chrome":      {"base_spec_fn": spec_dark_chrome, "M": 250, "R": 15, "CC": 40, "paint_fn": paint_dark_chrome_v2, "desc": "PVD dark chrome — exponential darkening, specular highlight preservation, near-mirror M=250",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.45, "perlin_lacunarity": 2.0, "noise_M": 35, "noise_R": 12},
    "mercury":          {"M": 255, "R": 3,   "CC": 16,  "paint_fn": paint_mercury_pool,    "desc": "Liquid mercury pooling mirror - desaturated chrome flow",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.5, "perlin_lacunarity": 1.8, "noise_M": 30, "noise_R": 10},
    "satin_chrome":     {"base_spec_fn": spec_satin_chrome, "M": 250, "R": 45,  "CC": 40,  "paint_fn": paint_satin_chrome_v2, "desc": "BMW silky satin chrome — directional micro-brushing, anisotropic reflection",
                         "noise_scales": [16, 32], "noise_weights": [0.4, 0.6], "noise_M": 20, "noise_R": 25},
    "surgical_steel":   {"M": 250, "R": 50, "CC": 16, "paint_fn": paint_brushed_grain, "desc": "Indestructible weaponized metal alloy exhibiting incredibly aggressive, deep brushing gouges", "noise_scales": [32, 64], "noise_R": 150},
    # 🔴 ADDED 2026-03-08 - Chrome & Mirror missing entries
    "antique_chrome":   {"base_spec_fn": spec_antique_chrome, "M": 220, "R": 18,  "CC": 50,  "paint_fn": paint_antique_chrome_v2,  "desc": "Antique chrome — patina accumulation + pitting corrosion model. FLAT-FIX: boosted noise.",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 35, "noise_R": 25},
    "black_chrome":     {"base_spec_fn": spec_black_chrome, "M": 255, "R": 2,   "CC": 16,  "paint_fn": paint_black_chrome_v2,   "desc": "Black chrome — Beer-Lambert smoke absorption, double-pass, specular highlights preserved",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 20, "noise_R": 8},
    "blue_chrome":      {"base_spec_fn": spec_blue_chrome, "M": 255, "R": 2,   "CC": 16,  "paint_fn": paint_blue_chrome_v2, "desc": "Blue chrome — thin-film interference, soap bubble physics on metal (blue→purple→gold→green-blue)",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 20, "noise_R": 8},
    "red_chrome":       {"base_spec_fn": spec_red_chrome, "M": 220, "R": 15,  "CC": 16, "paint_fn": paint_red_chrome_v2, "desc": "Red chrome — anodization simulation, oxide layer selective wavelength absorption — GGX-FIX: R=5->15 (M=220 not pure chrome)", "noise_scales": [32, 64], "noise_weights": [0.5, 0.5], "noise_M": 10, "noise_R": 10},
    "mirror_gold":      {"M": 255, "R": 2,   "CC": 16,  "paint_fn": paint_warm_metal,      "desc": "Mirror gold - pure chrome physics with warm gold color push from paint_fn",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 15, "noise_R": 8},
    # ── CANDY & CLEARCOAT VARIANTS (CANDY & PEARL) ────────────────────────────────────
    "candy":            {"M": 200, "R": 15,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Deep wet candy transparent glass",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 35, "noise_R": 15},
    "candy_chrome":     {"M": 250, "R": 4,   "CC": 16, "paint_fn": paint_spectraflame,    "desc": "Candy-tinted chrome - deep color over mirror base",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 60, "noise_R": 15},
    "clear_matte":      {"M": 0,   "R": 220, "CC": 210, "paint_fn": paint_f_clear_matte, "desc": "Precision matte clearcoat (BMW Frozen/Porsche Chalk style) — R=220 true matte roughness, CC=210 flat/no gloss"},
    "smoked":           {"M": 10, "R": 30, "CC": 60, "paint_fn": paint_smoked_darken, "desc": "Charcoal grey medium capturing a deep smoky internal volumetric particle volume — BASE-043 FIX: R=30 (smoked should have haze roughness, not mirror)", "noise_scales": [16, 32], "noise_R": 40},
    "spectraflame":     {"M": 245, "R": 15, "CC": 16, "paint_fn": paint_cp_spectraflame, "desc": "Hot Wheels candy-over-chrome deep sparkle — BASE-012 FIX: M=245 (chrome base), CC=16. GGX-FIX: R=8→15",
                         "noise_scales": [16, 32], "noise_M": 80, "noise_R": 25},
    # ⚠️ FIXED 2026-03-08: tinted_clear M was 40 (metallic) - tinted clear is dielectric.
    "tinted_clear":     {"M": 0,   "R": 15,  "CC": 16, "paint_fn": paint_cp_tinted_clear,"desc": "Deep tinted clearcoat over base color - dielectric, pure wet glass depth — GGX-FIX: R=8→15",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.4, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 10},
    # 🔴 ADDED 2026-03-08 - Candy & Pearl missing entries
    "candy_burgundy":   {"M": 180, "R": 15, "CC": 16, "paint_fn": paint_cp_candy_burgundy, "desc": "Deep burgundy candy over chrome base — BASE-013 FIX: M=180 (candy metallic base), R=15, CC=16",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.6, "noise_M": 15, "noise_R": 20},
    "candy_cobalt":     {"M": 180, "R": 15,  "CC": 26, "paint_fn": paint_fine_sparkle, "desc": "Ultra-thick pressurized deep-ocean resin pour over dark scatter base — GGX-FIX: R=5→15, CC=30→26 (candy range)", "noise_scales": [16, 32], "noise_weights": [0.5, 0.5], "noise_M": 30},
    "candy_emerald":    {"M": 190, "R": 15,  "CC": 16, "paint_fn": paint_electric_blue_tint, "desc": "Uranium glass generating intense radioluminescence — GGX-FIX: R=2→15", "perlin": True, "perlin_octaves": 4, "noise_M": 15, "noise_R": 12},
    "tri_coat_pearl":   {"M": 130, "R": 25,  "CC": 16, "paint_fn": paint_cp_tri_coat_pearl,          "desc": "Tri-coat pearl - three-layer candy pearl, directional mica waves + dense sparkle",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 12},
    "moonstone":        {"M": 80,  "R": 30,  "CC": 16, "paint_fn": paint_moonstone_adularescence, "desc": "Moonstone - soft milky translucent shimmer, blue-white adularescence. FLAT-FIX: boosted noise.",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 35, "noise_R": 20},
    "opal":             {"M": 180, "R": 50, "CC": 16, "paint_fn": paint_opal_v2, "base_spec_fn": spec_opal, "desc": "Dragon's Pearl Scale — iridescent hexagonal scale pattern, multi-colored angle-shift shimmer, pearlescent clearcoat variation per scale. WEAK-033 FIX: paint_opal_v2+spec_opal wired directly.", "noise_scales": [8, 16], "noise_M": 120, "noise_R": 80},
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
    "graphene":         {"M": 210, "R": 15,  "CC": 16,  "paint_fn": paint_cc_graphene,   "desc": "Graphene sheet — GGX-FIX: R=12→15. Atomically thin dark lattice with extreme geometric micro-specular noise",
                         "noise_scales": [64, 128, 256], "noise_weights": [0.2, 0.3, 0.5], "noise_M": 40, "noise_R": 25},
    "hybrid_weave":     {"M": 70,  "R": 40,  "CC": 16, "paint_fn": paint_cc_carbon, "base_spec_fn": spec_cc_carbon,   "desc": "Hybrid weave - tight structural interplay between carbon dark and kevlar thread matrices",
                         "noise_scales": [32, 64, 128], "noise_weights": [0.2, 0.3, 0.5], "noise_M": 50, "noise_R": 45},
    "kevlar_base":      {"M": 20,  "R": 100, "CC": 180,  "paint_fn": paint_cc_aramid, "base_spec_fn": spec_cc_carbon,    "desc": "Kevlar base - raw ballistic macro-weave thread matrix completely devoid of sealant",
                         "perlin": True, "perlin_octaves": 6, "perlin_persistence": 0.6, "perlin_lacunarity": 2.8, "noise_R": 65},
    # ── CERAMIC & GLASS ──────────────────────────────────────────────────────────────
    # (ceramic and piano_black are in STANDARD FINISHES above)
    # 🔴 ADDED 2026-03-08 - most of this category was missing from engine
    # 2026-04-19 HEENAN HA11 — Animal sister-hunt: name promises matte, R=155
    # was satin/scuffed band (matte threshold R>=180). Bumped to R=195 — true
    # matte ceramic. The flat-diffusion documented intent now matches the spec.
    "ceramic_matte":    {"M": 10,  "R": 195, "CC": 160, "paint_fn": paint_none,   "desc": "Diffuse fired ceramic with intense high-frequency abrasive grit structure (CC=160 flat). HA11: R 155→195 (true matte threshold). FLAG-CER-001 FIX: M=10. FLAT-FIX: boosted noise.",
                         "perlin": True, "perlin_octaves": 5, "perlin_persistence": 0.55, "perlin_lacunarity": 3.0, "noise_M": 30, "noise_R": 65},
    "crystal_clear":    {"M": 0, "R": 15, "CC": 16, "paint_fn": paint_cg_crystal, "base_spec_fn": spec_cg_glass, "desc": "A completely lucid, perfectly clear viscous water coating that never dries or sets — GGX-FIX: R=5->15. FLAT-FIX: added noise_M, boosted noise_R.", "noise_scales": [16, 32, 64], "noise_weights": [0.2, 0.3, 0.5], "noise_M": 8, "noise_R": 20},
    "enamel":           {"M": 0,   "R": 18,  "CC": 16, "paint_fn": paint_cg_crystal,   "desc": "Enamel - baked dielectric gloss filled with microscopic silica sediment imperfections. FLAT-FIX: added noise_M.",
                         "noise_scales": [64, 128], "noise_weights": [0.5, 0.5], "noise_M": 15, "noise_R": 35},
    "obsidian":         {"M": 20,  "R": 15,  "CC": 16, "paint_fn": paint_cg_obsidian, "base_spec_fn": spec_cg_obsidian,  "desc": "Obsidian - extremely sharp fractured volcanic glass with intense razor-sharp micro-flaking edges — GGX-FIX: R=4->15. FLAT-FIX: boosted noise.",
                         "perlin": True, "perlin_octaves": 6, "perlin_persistence": 0.6, "perlin_lacunarity": 3.5, "noise_M": 70, "noise_R": 40},
    "porcelain":        {"M": 0, "R": 15, "CC": 16, "paint_fn": paint_cg_porcelain, "base_spec_fn": spec_cg_porcelain, "desc": "Fractured monolithic bone ivory finish with subsurface micro-cracks spreading continuously — GGX-FIX: R=8->15", "perlin": True, "perlin_octaves": 5, "perlin_lacunarity": 3.0, "noise_R": 70},
    "tempered_glass":   {"M": 0,   "R": 15,  "CC": 16, "paint_fn": paint_none, "base_spec_fn": spec_cg_glass,      "desc": "Tempered glass - heat-stressed layered glass containing severe high-frequency molecular tension — GGX-FIX: R=3->15",
                         "noise_scales": [128, 256], "noise_weights": [0.4, 0.6], "noise_R": 20},
    # ── GAP-FILL: COATED OVER METAL / DEEP GLASS ────────────────────────
    "hydrographic":     {"M": 240, "R": 15,  "CC": 16, "paint_fn": paint_chrome_brighten, "desc": "Mirror metal under maximum deep clearcoat - wet glass over chrome — GGX-FIX: R=5→15",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 20, "noise_R": 6},
    "jelly_pearl":      {"M": 120, "R": 15,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Ultra-wet candy pearl - max depth, like looking through colored glass — GGX-FIX: R=10→15",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 18, "noise_R": 8},
    "orange_peel_gloss":{"M": 0,   "R": 55,  "CC": 16, "paint_fn": paint_none,            "desc": "Orange-peel texture sealed under thick clearcoat — MATL-FIX: R=160->55 (gloss clearcoat surface roughness, texture comes from perlin underneath)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.7, "perlin_lacunarity": 2.2, "noise_M": 0, "noise_R": 40},
    "tinted_lacquer":   {"M": 130, "R": 80,  "CC": 16, "paint_fn": paint_tinted_clearcoat,"desc": "Semi-metallic under thick lacquer pour - depth and warmth. FLAT-FIX: boosted noise.",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.4, "perlin_lacunarity": 1.8, "noise_M": 35, "noise_R": 30},
    # ── MATTE & FLAT ─────────────────────────────────────────────────
    # CC=0 triggers the metallised path in the renderer — always use CC>=16 for non-chrome bases.
    # For dead-flat finishes use CC=180–255 (maximum clearcoat degradation = most dull).
    "blackout":         { "base_spec_fn": spec_blackout_v2,"M": 5,  "R": 210, "CC": 200, "paint_fn": paint_blackout_v2, "desc": "Stealth murdered-out - near-total absorption, dead flat (CC=200)"},
    # 2026-04-20 HEENAN HARDMODE-FOUND-5 — flat_black was pure dielectric
    # noise-less. Real military matte black has subtle organic micro-pore
    # variation. Add fine perlin noise to give the surface chalky organic
    # character without breaking the dead-flat reading.
    "flat_black":       {"M": 0,   "R": 248, "CC": 220, "paint_fn": paint_none,  "desc": "Dead flat zero-sheen black with organic chalky micro-pore variation — military/rat-rod authentic (HARDMODE-FOUND-5: added pore noise)",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.45, "perlin_lacunarity": 2.1, "noise_M": 2, "noise_R": 12},
    # ⚠️ FIXED 2026-03-08: frozen CC was 0 - BMW Frozen paints have a matte clear over them.
    "frozen":           {"M": 225, "R": 140, "CC": 100, "paint_fn": paint_subtle_flake,  "desc": "Frozen icy metallic — WEAK-017 FIX: ice-crystal Worley spec, blue iridescence in paint (via registry_patches) — BASE-025 FIX: CC=100 (BMW Frozen matte/satin clear)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.2, 0.45, 0.35], "noise_M": 40, "noise_R": 35},
    "frozen_matte":     {"M": 60,  "R": 210, "CC": 175, "paint_fn": paint_subtle_flake,  "desc": "BMW Individual frozen matte — WEAK-017 FIX: frosted-glass surface, uniform micro-roughness, no sparkle (via registry_patches)",
                         "noise_scales": [2, 3, 5], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 10, "noise_R": 20},
    "matte":            {"M": 0,   "R": 200, "CC": 160, "paint_fn": paint_matte_flat,  "desc": "Flat matte — WEAK-012 FIX: upgraded from paint_none + noise variation for organic chalky texture",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.5, 0.3, 0.2], "noise_R": 25},
    "vantablack":       {"M": 0,   "R": 255, "CC": 240, "paint_fn": paint_none,          "desc": "Absolute void zero reflection - CC=240 maximum possible degradation",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 3, "noise_R": 5},
    "volcanic":         {"M": 80,  "R": 180, "CC": 70,  "paint_fn": paint_volcanic_ash,  "desc": "Volcanic ash coating - the ash layer IS the coat, heavily degraded (CC=70)"},
    # ── BRUSHED & DIRECTIONAL GRAIN ──────────────────────────────────
    "brushed_aluminum": {"base_spec_fn": spec_brushed_grain, "M": 200, "R": 55,  "CC": 16,  "paint_fn": paint_brushed_grain,   "desc": "Brushed natural aluminum directional grain — BASE-026 FIX: M=200 (real brushed aluminum, not near-chrome)",
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
                         "noise_scales": [16, 32, 64], "noise_weights": [0.4, 0.3, 0.3], "noise_M": 15, "noise_R": 15},
    # ── EXOTIC METAL ─────────────────────────────────────────────────
    # 🔴 ADDED 2026-03-08 - Exotic Metal missing entries
    "cobalt_metal":     { "base_spec_fn": spec_cobalt_metal,"M": 195, "R": 28,  "CC": 16,  "paint_fn": paint_electric_blue_tint, "desc": "Cobalt metal - blue-tinted raw cobalt alloy, no clearcoat",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 15},
    "liquid_titanium":  { "base_spec_fn": spec_liquid_titanium,"M": 245, "R": 5,   "CC": 16,  "paint_fn": paint_liquid_titanium_v2, "desc": "Liquid titanium - near-mirror flowing molten metal surface",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.4, "perlin_lacunarity": 2.0, "noise_M": 20, "noise_R": 8},
    "platinum":         { "base_spec_fn": spec_platinum_metal,"M": 255, "R": 4,   "CC": 16, "paint_fn": paint_chrome_brighten, "desc": "Platinum - pure dense mirror metal, slightly warmer than chrome, coated",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 12, "noise_R": 8},
    "titanium_raw":     {"M": 155, "R": 85,  "CC": 16,  "paint_fn": paint_raw_aluminum,    "desc": "Titanium raw - omnidirectional rough industrial surface, no grain, no coat",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 35},
    # ── RAW METAL & WEATHERED ────────────────────────────────────────
    "anodized":         {"M": 170, "R": 80,  "CC": 140, "paint_fn": paint_subtle_flake,    "desc": "Gritty matte anodized aluminum (CC=140 flat) — BASE-034 FIX: R=80 (standard anodized aluminum surface roughness)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 25},
    "burnt_headers":    {"M": 190, "R": 45,  "CC": 16,  "paint_fn": paint_burnt_metal,     "desc": "Exhaust header heat-treated gold-blue oxide",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 20},
    "galvanized":       {"M": 195, "R": 65,  "CC": 30,  "paint_fn": paint_galvanized_speckle, "desc": "Hot-dip galvanized zinc - the zinc IS the coat (CC=30 thin metallic coat)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.4, 0.3, 0.3], "noise_M": 25, "noise_R": 30},
    "heat_treated":     {"M": 140, "R": 35,  "CC": 16,  "paint_fn": paint_heat_tint,       "desc": "Heat-treated tool steel blue-gold zones — BASE-035 FIX: M=140 (tool steel/gun barrel, not titanium-range)",
                         "noise_scales": [8, 16], "noise_weights": [0.4, 0.6], "noise_M": 20, "noise_R": 15},
    "patina_bronze":    {"M": 40,  "R": 90,  "CC": 100, "paint_fn": paint_patina_green,    "desc": "Aged oxidized bronze with green patina — FLAG-WA-002 FIX: M=40 (CuO/Cu2O/CuCO3 oxide layers are dielectric, not metallic)",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 35},
    "patina_coat":      {"M": 100, "R": 150, "CC": 50, "paint_fn": paint_patina_green,    "desc": "Old weathered paint with fresh satin clearcoat sprayed over - protected patina",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 35},
    "battle_patina":    {"M": 140, "R": 150, "CC": 50, "paint_fn": paint_burnt_metal,     "desc": "Heavily worn metal base with thin protective satin coat - used racecar look — BASE-036 FIX: M=140 (worn+patina reduces metallic from 200)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 40},
    # ⚠️ FIXED 2026-03-08: cerakote_gloss M was 200 (too metallic for ceramic). Real Cerakote Gloss is polymer - M=100.
    "cerakote_gloss":   {"M": 45,  "R": 55,  "CC": 16, "paint_fn": paint_tactical_flat,   "desc": "Cerakote gloss - polymer ceramic sealed gloss surface — FLAG-IND-001 FIX: M=45 (semi-metallic polymer, not highly metallic), R=55 (smooth but not mirror-level; was M=100/R=15 — too metallic/too smooth for industrial ceramic)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 20},
    "raw_aluminum":     {"M": 200, "R": 30,  "CC": 100, "paint_fn": paint_raw_aluminum,    "desc": "Bare unfinished aluminum sheet metal — BASE-033 FIX: M=200 (real bare aluminum, not near-chrome), CC=100 (no clearcoat on bare metal)",
                         "noise_scales": [16, 32], "noise_weights": [0.4, 0.6], "noise_M": 25, "noise_R": 25},
    "sandblasted":      { "base_spec_fn": spec_sandblasted_v2,"M": 180, "R": 150, "CC": 155, "paint_fn": paint_sandblasted_v2, "desc": "Raw stripped metal - massive high frequency sharp static grit with omni-scattering reflections (CC=155 flat)"},
    # ── EXOTIC & COLOR-SHIFT ─────────────────────────────────────────
    "chameleon":        {"M": 160, "R": 25,  "CC": 16, "paint_fn": paint_cp_chameleon,  "desc": "Dual-tone color-shift angle-dependent",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 1.8, "noise_M": 60, "noise_R": 35},
    "iridescent":       {"M": 200, "R": 15,  "CC": 16, "paint_fn": paint_cp_iridescent, "desc": "Norse mythology rainbow bridge - iridescent wrap with angle-shift color — BASE-038 FIX: M=200. GGX-FIX: R=10→15", "noise_scales": [32, 64], "noise_M": 80, "noise_R": 30},
    "chromaflair":      {"M": 210, "R": 15,  "CC": 18, "paint_fn": paint_chromaflair,      "desc": "ChromaFlair Light Shift — 3-angle color flip via multi-stop hue rotation — GGX-FIX: R=12->15",
                         "base_spec_fn": spec_chromaflair_base},
    "xirallic":         {"M": 170, "R": 20,  "CC": 18, "paint_fn": paint_xirallic,          "desc": "Xirallic Crystal Flake — large sparse alumina flakes with iron oxide blue-silver interference",
                         "base_spec_fn": spec_xirallic_base},
    "anodized_exotic":  {"M": 110, "R": 38,  "CC": 45, "paint_fn": paint_anodized_exotic,   "desc": "Anodized Exotic — dye-impregnated oxide layer, semi-gloss, subtle hex pore micro-texture",
                         "base_spec_fn": spec_anodized_exotic_base},
    # ── WRAP & COATING ───────────────────────────────────────────────
    # ⚠️ FIXED 2026-03-08: liquid_wrap M was 80 (metallic) - rubber/vinyl wraps are dielectric.
    "liquid_wrap":      {"M": 0,   "R": 80,  "CC": 50,  "paint_fn": paint_liquid_wrap_fn,  "desc": "Liquid rubber peel coat — WEAK-016 FIX: distinct rubber/vinyl character (R=80 slightly rougher, no metallic, rubber micro-texture)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_R": 18, "noise_M": 5},
    # 2026-04-20 HEENAN HARDMODE-FOUND-6 — primer was pure dielectric with
    # zero noise. Real raw primer has visible sand-grit and coverage
    # variation. Add gritty noise so the unfinished-build aesthetic reads
    # as actual primer instead of just a flat grey shape.
    "primer":           {"M": 0,   "R": 210, "CC": 180, "paint_fn": paint_none,     "desc": "Raw grey primer with sand-grit + coverage variation — unfinished build / project-car authenticity (HARDMODE-FOUND-6: added grit noise)",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.4, 0.4, 0.2], "noise_M": 3, "noise_R": 18},
    "satin_wrap":       {"M": 0,   "R": 130, "CC": 60,  "paint_fn": paint_satin_wrap,      "desc": "Vinyl wrap satin surface - the film IS the coat layer (CC=60)"},
    # ── ORGANIC / PERLIN NOISE ───────────────────────────────────────
    "living_matte":     {"M": 0,   "R": 190, "CC": 140, "paint_fn": paint_none, "desc": "Organic matte - low organic sheen, CC=140"},
    "organic_metal":    {"M": 210, "R": 45,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Organic flowing metallic with Perlin noise terrain",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "noise_M": 35, "noise_R": 20, "noise_CC": 8},
    "terrain_chrome":   {"M": 250, "R": 8,   "CC": 16,  "paint_fn": paint_chrome_brighten, "desc": "Chrome with Perlin terrain-like distortion in roughness",
                         "perlin": True, "perlin_octaves": 5, "perlin_persistence": 0.45, "noise_M": 0, "noise_R": 25},
    # ── WORN & DEGRADED CLEARCOAT (CC=81–255) ────────────────────────────────
    # track_worn: REMOVED per audit 2026-03-15
    "sun_fade":         {"M": 10,  "R": 130, "CC": 120, "paint_fn": paint_sun_fade_v2,    "desc": "UV sun-damaged paint - FBM bleach + 40% desaturation, chalky, coat breaking down. FLAG-WA-004 FIX: M=10 (UV-damaged dielectric paint, compare sun_baked M=0).",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 30, "noise_CC": 20},
    "acid_etch":        {"M": 25,  "R": 160, "CC": 130, "paint_fn": paint_patina_green,    "desc": "Acid-rain etched surface - pitted with partial clearcoat failure. FLAG-WA-005 FIX: M=25 (acid strips metal, pitted dielectric surface), R=160 (deep pitting = high roughness; was M=100/R=110 — too metallic/too smooth for chemical etch)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.4, 0.3, 0.3], "noise_M": 20, "noise_R": 25, "noise_CC": 25},
    "oxidized":         {"M": 15,  "R": 70,  "CC": 160, "paint_fn": paint_none,            "desc": "Oxidized metallic - rust/iron-oxide bloom, clearcoat near-destroyed (CC=160). FLAG-WA-003 FIX: M=15 (Fe2O3 is dielectric), paint_none (burnt_metal applied thermal heat-tint colors — wrong for room-temp rust).",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 35, "noise_CC": 30},
    "chalky_base":      {"M": 0,   "R": 210, "CC": 230, "paint_fn": paint_none,  "desc": "Chalky oxidised flat - CC=230 near-maximum degradation, powdery dead surface",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 5, "noise_R": 25, "noise_CC": 20},
    "barn_find":        { "base_spec_fn": spec_racing_heritage,"M": 80,  "R": 160, "CC": 210, "paint_fn": paint_primer_flat,     "desc": "Barn-find condition - decades of clearcoat breakdown, deep chalky flat (CC=210)",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.7, "perlin_lacunarity": 1.8, "noise_M": 10, "noise_R": 40, "noise_CC": 35},
    "crumbling_clear":  {"M": 30,  "R": 180, "CC": 235, "paint_fn": paint_none,    "desc": "Peeling, crumbling clearcoat - paint underneath showing through (CC=235)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.2, "noise_M": 8, "noise_R": 30, "noise_CC": 35},
    "destroyed_coat":   {"M": 0,   "R": 210, "CC": 255, "paint_fn": paint_none,            "desc": "Completely destroyed clearcoat - maximum degradation, pure chalk-rough (CC=255)"},

    # ══════════════════════════════════════════════════════════════════════
    # ADDED 2026-03-08 - Full JS→Python sync pass  (82 bases, all categories)
    # ══════════════════════════════════════════════════════════════════════

    # ── METALLIC STANDARD ─────────────────────────────────────────────────
    "candy_apple":      { "base_spec_fn": spec_metallic_standard,"M": 230, "R": 15, "CC": 24, "paint_fn": paint_smoked_darken, "desc": "A deeply unholy crimson candy gloss that pulls light into a violently crushed shadow point — GGX-FIX: R=2->15", "noise_scales": [4], "noise_M": 250, "noise_R": -10},
    "champagne":        { "base_spec_fn": spec_metallic_standard,"M": 200, "R": 30,  "CC": 16, "paint_fn": paint_warm_metal,      "desc": "Champagne metallic - warm gold-silver, French sparkling wine colour",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 20, "noise_R": 12},
    "metal_flake_base": { "base_spec_fn": spec_metallic_standard,"M": 215, "R": 28,  "CC": 18, "paint_fn": paint_subtle_flake,    "desc": "Metal flake base - heavy visible coarse metalflake in clear, classic show-car base — BASE-037 FIX: CC=18 (show-car max gloss)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 40, "noise_R": 15},
    "original_metal_flake": {"M": 250, "R": 50,  "CC": 30, "paint_fn": paint_subtle_flake, "desc": "Exploding star massive metallic chunks sealed in aerospace clear", "noise_scales": [1, 2, 4], "noise_M": 150, "noise_R": 80},
    "champagne_flake":  {"M": 255, "R": 2, "CC": 16, "paint_fn": paint_warm_metal, "desc": "A hyper-reflective pure 24K gold with near-zero roughness and high metal flake scaling — BASE-015 FIX: R=2 (PBR minimum)", "noise_scales": [1, 2], "noise_M": 50},
    # 2026-04-19 HEENAN HA8 — Animal engine identity audit. M=160 promised
    # "silver" but rendered as muted aluminum (silver class needs M≥220).
    # Bumped to M=235 — true silver mirror. The comment "BASE-041 FIX: M=160"
    # was a previous over-correction that lost the silver promise.
    "fine_silver_flake": {"M": 235, "R": 15, "CC": 16, "paint_fn": paint_diamond_sparkle, "desc": "Crushed silver mica shards suspended in thick clear resin — silver mirror class (HEENAN HA8 fix: M 160→235). GGX-FIX: R=5→15", "noise_scales": [8, 16], "noise_M": 150},
    "blue_ice_flake":   {"M": 200, "R": 15, "CC": 30, "paint_fn": paint_ice_cracks, "desc": "Jagged frozen ice fractals catching deep light in a frozen state — GGX-FIX: R=5→15", "perlin": True, "perlin_octaves": 5, "noise_M": -50, "noise_R": 60},
    "bronze_flake":     {"M": 100, "R": 120, "CC": 100, "paint_fn": paint_patina_green, "desc": "10,000-year oxidized shipwreck brass, aggressively dripping with rich verdigris (CC=100 satin)", "perlin": True, "perlin_octaves": 4, "noise_R": 100},
    "gunmetal_flake":   {"M": 210, "R": 30,  "CC": 16, "paint_fn": paint_chameleon_shift, "desc": "Geometric stair-step oxidation layering of Bismuth — BASE-042 FIX: R=30 (metallic flake sparkle needs low roughness)", "perlin": True, "perlin_octaves": 5, "perlin_lacunarity": 3.0, "noise_M": 50, "noise_R": 40},
    "green_flake":      {"M": 180, "R": 20, "CC": 50, "paint_fn": paint_interference_shift, "desc": "Dark space meteorite that fades to an intense glowing neon green at its specular angles", "noise_scales": [32, 64], "noise_M": 100},
    "fire_flake":       {"M": 220, "R": 80, "CC": 20, "paint_fn": paint_burnt_metal, "desc": "The violent surface of the sun exploding with massive bright spots of solar plasma", "perlin": True, "perlin_octaves": 3, "noise_M": 150, "noise_R": 50},
    "midnight_pearl":   { "base_spec_fn": spec_pearl_base,"M": 175, "R": 22,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Midnight pearl - deep dark paint with hidden pearl sparkle visible at angles. WEAK-031 FIX: spec_pearl_base.",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 12},
    "pearlescent_white": {"M": 120, "R": 20,  "CC": 16, "paint_fn": paint_tri_coat_depth,  "desc": "Pearl white - tri-coat pearlescent white, deep directional sparkle",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 10},
    "pewter":           { "base_spec_fn": spec_metallic_standard,"M": 100, "R": 90, "CC": 80, "paint_fn": paint_chameleon_shift, "desc": "A dark, cursed grey meta-lead finish pulsing with forbidden underworld geometry (CC=80 satin)", "perlin": True, "perlin_octaves": 3, "noise_R": 40},

    # ── OEM AUTOMOTIVE ────────────────────────────────────────────────────
    "ambulance_white":  { "base_spec_fn": spec_oem_automotive,"M": 0,   "R": 15,  "CC": 16, "paint_fn": paint_none,            "desc": "Ambulance white - high-visibility emergency gloss white, pure dielectric — GGX-FIX: R=8->15"},
    "dealer_pearl":     { "base_spec_fn": spec_tri_coat_pearl,"M": 80,  "R": 15,  "CC": 16, "paint_fn": paint_tri_coat_depth,  "desc": "Dealer pearl - typical dealership tri-coat pearl upgrade, three distinct coat zones. WEAK-032 FIX: spec_tri_coat_pearl.",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 8},
    "factory_basecoat": { "base_spec_fn": spec_oem_automotive,"M": 130, "R": 30,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Factory basecoat - standard OEM metallic, the average showroom car that left the plant",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 20, "noise_R": 12},
    "fire_engine":      {"M": 0,   "R": 15,  "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "Fire engine red - deep wet apparatus red, dielectric, maximum gloss — GGX-FIX: R=6→15. FLAT-FIX: added perlin noise.",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 8, "noise_R": 12},
    "fleet_white":      { "base_spec_fn": spec_oem_automotive,"M": 0, "R": 18, "CC": 16, "paint_fn": paint_ceramic_gloss, "desc": "Fleet white - crosslinked polyurethane commercial white, durable uniform dielectric finish", "perlin": True, "noise_R": 10},
    "police_black":     {"M": 0,   "R": 15,  "CC": 16, "paint_fn": paint_none,            "desc": "Police black - law enforcement glossy black, dielectric — GGX-FIX: R=10→15. FLAT-FIX: added perlin noise.",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 8, "noise_R": 12},
    "school_bus":       { "base_spec_fn": spec_oem_automotive,"M": 0, "R": 15, "CC": 16, "paint_fn": paint_none, "desc": "School bus yellow - Federal Standard 13432 chrome yellow with UV stabilizer haze — FLAG-OEM-002 FIX: paint_none preserves correct yellow base (was paint_electric_blue_tint — cold blue hue on a warm yellow finish). FLAT-FIX: added perlin noise.",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 8, "noise_R": 12},
    "showroom_clear":   { "base_spec_fn": spec_oem_automotive,"M": 10, "R": 15, "CC": 16, "paint_fn": paint_ceramic_gloss, "desc": "Showroom clear - multi-layer Fresnel clearcoat stack, deep wet-look mirror finish — GGX-FIX: R=3->15", "perlin": True, "perlin_octaves": 4, "noise_R": 4},
    "taxi_yellow":      { "base_spec_fn": spec_oem_automotive,"M": 3, "R": 25, "CC": 110, "paint_fn": paint_burnt_metal, "desc": "Taxi yellow - UV-photodegraded cab yellow with chalking and mechanical wear zones (CC=110). FLAT-FIX: added noise_M.", "perlin": True, "perlin_octaves": 4, "noise_M": 10, "noise_R": 30},

    # ── PREMIUM LUXURY ────────────────────────────────────────────────────
    "bentley_silver":   { "base_spec_fn": spec_premium_luxury,"M": 235, "R": 15,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Bentley silver - Rolls-Royce/Bentley ultra-fine silver metallic — GGX-FIX: R=12->15",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 15, "noise_R": 6},
    "bugatti_blue":     { "base_spec_fn": spec_premium_luxury,"M": 180, "R": 15,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Bugatti Bleu de France - signature Bugatti deep two-tone blue — GGX-FIX: R=10->15",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 20, "noise_R": 6},
    "ferrari_rosso":    { "base_spec_fn": spec_premium_luxury,"M": 120, "R": 15, "CC": 22, "paint_fn": paint_fine_sparkle, "desc": "Ferrari Rosso Corsa - triple-layer candy coat with Beer-Lambert pigment absorption, deep clearcoat — GGX-FIX: R=4->15", "noise_scales": [16, 32, 64], "noise_M": 50, "noise_R": 8},
    "koenigsegg_clear": { "base_spec_fn": spec_premium_luxury,"M": 80,  "R": 20,  "CC": 16, "paint_fn": paint_forged_carbon,   "desc": "Koenigsegg clear carbon - visible clear-coated forged weave, semi-metallic",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 20, "noise_R": 15},
    "lamborghini_verde": { "base_spec_fn": spec_premium_luxury,"M": 0,   "R": 15,  "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "Lambo Verde Mantis - electric green dielectric, ceramic-like gloss surface — GGX-FIX: R=6->15"},
    "maybach_two_tone": { "base_spec_fn": spec_premium_luxury,"M": 180, "R": 15,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Maybach two-tone - Mercedes-Maybach duo-tone luxury split metallic — GGX-FIX: R=12->15",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 15, "noise_R": 6},
    "mclaren_orange":   { "base_spec_fn": spec_premium_luxury,"M": 0,   "R": 15,  "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "McLaren Papaya Spark - iconic McLaren orange, dielectric ceramic-smooth — GGX-FIX: R=6->15"},
    "pagani_tricolore": { "base_spec_fn": spec_premium_luxury,"M": 160, "R": 15,  "CC": 16, "paint_fn": paint_tricolore_shift,  "desc": "Pagani tricolore - premium three-tone angle-resolved shift paint",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 1.8, "noise_M": 50, "noise_R": 25},
    "porsche_pts":      { "base_spec_fn": spec_premium_luxury,"M": 150, "R": 15,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Porsche PTS - Paint-to-Sample deep custom coat with visible metallic depth — GGX-FIX: R=14->15. FLAT-FIX: boosted noise.",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 30, "noise_R": 15},

    # ── RACING HERITAGE ───────────────────────────────────────────────────
    "asphalt_grind":    { "base_spec_fn": spec_racing_heritage,"M": 10,  "R": 210, "CC": 200, "paint_fn": paint_primer_flat,     "desc": "Asphalt grind - rough road-surface texture, maximum roughness, zero coat (CC=200 dead flat) — MATL-FIX: M=30->10 (asphalt is dielectric aggregate)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 10, "noise_R": 35},
    "bullseye_chrome":  { "base_spec_fn": spec_bullseye_chrome,"M": 240, "R": 3,   "CC": 16, "paint_fn": paint_bullseye_chrome_v2, "desc": "Bullseye chrome — concentric ring diffraction pattern, rotational polishing rings", "perlin": True, "perlin_octaves": 1, "perlin_persistence": 0.8, "noise_M": 5, "noise_R": 2},
    "checkered_chrome": { "base_spec_fn": spec_checkered_chrome,"M": 250, "R": 4,   "CC": 16,  "paint_fn": paint_checkered_chrome_v2, "desc": "Checkered chrome — checker-flag threshold-modulated reflectance, chrome squares vs dark matte",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 12, "noise_R": 5},
    # dirt_track_satin: REMOVED per audit 2026-03-15
    "drag_strip_gloss": { "base_spec_fn": spec_racing_heritage,"M": 140, "R": 15,  "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "Drag strip gloss - ultra-polished show car finish, came off the trailer — GGX-FIX: R=6->15",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 25, "noise_R": 6},
    "endurance_ceramic": { "base_spec_fn": spec_racing_heritage,"M": 15, "R": 80, "CC": 50, "paint_fn": paint_volcanic_ash, "desc": "Endurance ceramic (Apollo Shield Char) - thermal fatigue micro-craze, charred reentry plating", "perlin": True, "perlin_octaves": 5, "noise_M": 10, "noise_R": 25},
    # heat_shield: REMOVED per audit 2026-03-15
    "pace_car_pearl":   { "base_spec_fn": spec_tri_coat_pearl,"M": 110, "R": 16,  "CC": 16, "paint_fn": paint_tri_coat_depth,  "desc": "Pace car pearl - official pace car triple-pearl finish, three distinct coat zones. WEAK-032 FIX: spec_tri_coat_pearl.",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 22, "noise_R": 8},
    # pit_lane_matte: REMOVED per audit 2026-03-15
    "race_day_gloss":   { "base_spec_fn": spec_racing_heritage,"M": 0,   "R": 15,  "CC": 16, "paint_fn": paint_ceramic_gloss, "desc": "Race day gloss - multi-polish wet-look total internal reflection coating, fresh off the trailer — GGX-FIX: R=2->15. FLAT-FIX: boosted noise.", "perlin": True, "noise_M": 8, "noise_R": 12},
    "rally_mud":        { "base_spec_fn": spec_racing_heritage,"M": 20,  "R": 185, "CC": 80, "paint_fn": paint_primer_flat,     "desc": "Rally mud - partially mud-splattered paint, coat degrading from abuse",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 8, "noise_R": 30},
    # rat_rod_primer: REMOVED per audit 2026-03-15
    "stock_car_enamel": { "base_spec_fn": spec_racing_heritage,"M": 0,   "R": 18,  "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "Stock car enamel - traditional thick NASCAR enamel, hard-baked dielectric. FLAT-FIX: added perlin noise.",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 8, "noise_R": 12},
    "victory_lane":     { "base_spec_fn": spec_racing_heritage,"M": 185, "R": 16,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Victory lane - champagne-soaked celebration metallic, dense festive sparkle",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 30, "noise_R": 10},

    # ── SATIN & WRAP ──────────────────────────────────────────────────────
    "brushed_wrap":     { "base_spec_fn": spec_satin_wrap,"M": 180, "R": 75,  "CC": 35, "paint_fn": paint_brushed_grain,   "desc": "Brushed wrap - brushed metal vinyl film, directional grain visible through coat",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 20, "noise_R": 18},
    "chrome_wrap":      { "base_spec_fn": spec_satin_wrap,"M": 255, "R": 3,   "CC": 16,  "paint_fn": paint_chrome_brighten, "desc": "Chrome wrap - mirror chrome vinyl, slightly textured vs real chrome",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 12, "noise_R": 5},
    "color_flip_wrap":  { "base_spec_fn": spec_satin_wrap,"M": 155, "R": 22,  "CC": 16, "paint_fn": paint_chameleon_shift,  "desc": "Color flip wrap - dual-colour angle-shift vinyl film",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 1.8, "noise_M": 45, "noise_R": 22},
    "gloss_wrap":       {"M": 0,   "R": 15,  "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "Gloss wrap - high-gloss smooth vinyl, dielectric — GGX-FIX: R=8→15. FLAT-FIX: added perlin noise.",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 8, "noise_R": 12},
    "matte_wrap":       { "base_spec_fn": spec_satin_wrap,"M": 0,   "R": 195, "CC": 165, "paint_fn": paint_satin_wrap,      "desc": "Matte wrap - dead-flat vinyl, zero sheen, the wrap IS the protection layer (CC=165 flat) — BASE-029 FIX: R=195 (dead-flat vinyl)"},
    "stealth_wrap":     { "base_spec_fn": spec_satin_wrap,"M": 10, "R": 200, "CC": 170, "paint_fn": paint_glass_tint, "desc": "Predator-style refractive stealth boundary (CC=170 flat) — BASE-030 FIX: M=10 (stealth = non-metallic, no reflections)", "perlin": True, "perlin_octaves": 4, "perlin_lacunarity": 2.8, "noise_M": 20, "noise_R": -100},
    "textured_wrap":    { "base_spec_fn": spec_satin_wrap,"M": 0,   "R": 95,  "CC": 40, "paint_fn": paint_textured_wrap_v2, "desc": "Textured wrap - orange-peel embossed vinyl, color-preserving bump texture. WARN-WRAP-001 FIX: was paint_galvanized_speckle (hardcoded charcoal).",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 0, "noise_R": 20},

    # Paint Technique - real painterly application marks, patched to v2 source functions.
    "paint_drip_gravity":   {"M": 20, "R": 72, "CC": 32, "paint_fn": paint_none, "desc": "Gravity-dripped paint runs with vertical curtain streaks, beads, and pooled wet clearcoat."},
    "paint_splatter_loose": {"M": 18, "R": 88, "CC": 40, "paint_fn": paint_none, "desc": "Loose paint splatter with dense atomized mist and irregular droplets."},
    "paint_sponge_stipple": {"M": 8,  "R": 135, "CC": 120, "paint_fn": paint_none, "desc": "Sponge-stippled faux finish with irregular pores, dabs, and matte texture."},
    "paint_roller_streak":  {"M": 6,  "R": 112, "CC": 92, "paint_fn": paint_none, "desc": "Roller-applied paint with lap lines, dry edges, and fine roller fibers."},
    "paint_spray_fade":     {"M": 18, "R": 62, "CC": 30, "paint_fn": paint_none, "desc": "Airbrushed spray fade with soft atomized gradient and paint-gun mist."},
    "paint_brush_stroke":   {"M": 12, "R": 84, "CC": 58, "paint_fn": paint_none, "desc": "Visible brush strokes with bristle ridges, troughs, and impasto paint load."},

    # ── SHOKK SERIES ──────────────────────────────────────────────────────
    "shokk_blood":      {"M": 200, "R": 15,  "CC": 16, "paint_fn": paint_plasma_shift,    "desc": "SHOKK Blood - deep arterial red metallic, dark micro-shifted edges — GGX-FIX: R=14->15",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 10},
    "shokk_pulse":      {"M": 220, "R": 15,  "CC": 16, "paint_fn": paint_electric_blue_tint, "desc": "SHOKK Pulse - electric pulse wave metallic, Shokker signature hot-pink/blue — GGX-FIX: R=10->15",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 35, "noise_R": 8},
    # 2026-04-19 HEENAN H4HR-BOCK1 — Bockwinkel SHOKK audit: noise scales
    # [1,2,4] were sub-pixel (no visible "static crackle"). Bumped to
    # [4,16,32] so the static character is actually visible at car-shape
    # scale. noise_M boosted 30→55 to give the crackle real contrast vs the
    # base metallic. shokk_static no longer collides visually with shokk_blood
    # (which keeps paint_plasma_shift at its denser scales).
    "shokk_static":     {"M": 210, "R": 18,  "CC": 16, "paint_fn": paint_plasma_shift,    "desc": "SHOKK Static - crackling static interference metallic blue-gray (H4HR-BOCK1: noise scales [1,2,4]→[4,16,32], noise_M 30→55 for visible crackle)",
                         "noise_scales": [4, 16, 32], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 55, "noise_R": 18},
    "shokk_venom":      {"M": 0,   "R": 15,  "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "SHOKK Venom - toxic acid green-yellow dielectric, ceramic-smooth reactive — GGX-FIX: R=10->15. FLAT-FIX: boosted noise.",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 50, "noise_R": 35},
    "shokk_void":       {"M": 0,   "R": 230, "CC": 230, "paint_fn": paint_rubber_absorb,   "desc": "SHOKK Void - near-vantablack, absolute absorption with subtle edge shimmer (CC=230 dead flat)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 2, "noise_R": 30},

    # ── WEATHERED & AGED ──────────────────────────────────────────────────
    "acid_rain":        { "base_spec_fn": spec_weathered_aged,"M": 60,  "R": 130, "CC": 140, "paint_fn": paint_patina_green,   "desc": "Acid rain - chemical etch damage, partial coat failure with oxidation patches",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 20, "noise_R": 30, "noise_CC": 20},
    "desert_worn":      { "base_spec_fn": spec_weathered_aged,"M": 20,  "R": 160, "CC": 130, "paint_fn": paint_desert_worn,   "desc": "Desert worn - sand-blasted UV-hammered surface, coat nearly gone",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 8, "noise_R": 30, "noise_CC": 25},
    "oxidized_copper":  { "base_spec_fn": spec_weathered_aged,"M": 25,  "R": 95,  "CC": 120, "paint_fn": paint_patina_green,    "desc": "Oxidized copper - fully green-oxidized Statue-of-Liberty patina (CC=120). FLAG-WA-001 FIX: M=25 (CuCO3/Cu(OH)2 verdigris is dielectric; fully oxidized copper reads near-zero metallic).",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 35},
    "salt_corroded":    { "base_spec_fn": spec_weathered_aged,"M": 40,  "R": 180, "CC": 120, "paint_fn": paint_galvanized_speckle, "desc": "Salt corroded - coastal salt-air corrosion, speckled oxide with coat failure. FLAG-WA-006 FIX: M=40 (corrosion products are dielectric oxides/salts), R=180 (heavily pitted rough surface; was M=130/R=140 — too metallic/too smooth for corroded metal)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 25, "noise_R": 30, "noise_CC": 25},
    "sun_baked":        { "base_spec_fn": spec_weathered_aged,"M": 0,   "R": 150, "CC": 155, "paint_fn": paint_sun_fade_v2,   "desc": "Sun baked - UV-cooked faded chalky surface, FBM bleach + 40% desat, coat crumbling. WARN-WA-001 FIX.",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 30, "noise_CC": 25},
    "vintage_chrome":   { "base_spec_fn": spec_vintage_chrome,"M": 240, "R": 20,  "CC": 50,  "paint_fn": paint_vintage_chrome_v2,  "desc": "Vintage chrome — UV yellowing + micro-pit scatter, 1950s chrome with dignified aging (CC=50 aged)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 15},

    # ── EXTREME & EXPERIMENTAL ────────────────────────────────────────────
    "bioluminescent":   { "base_spec_fn": spec_bioluminescent,"M": 0,   "R": 15,  "CC": 16, "paint_fn": paint_bioluminescent, "desc": "Bioluminescent - deep sea organism soft internal glow, dielectric organic surface — GGX-FIX: R=10->15",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 12},
    "dark_matter":      { "base_spec_fn": spec_dark_matter,"M": 0,   "R": 240, "CC": 220, "paint_fn": paint_dark_matter,   "desc": "Dark matter - ultra-dark hidden angle-dependent reveal, maximum absorption (CC=220 dead flat)",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.7, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 35},
    "holographic_base": { "base_spec_fn": spec_holographic_base,"M": 200, "R": 15,  "CC": 16, "paint_fn": paint_holographic_base, "desc": "Holographic base - full prismatic rainbow hologram base, strong angle shift — GGX-FIX: R=6->15",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 50, "noise_R": 20},
    "neutron_star":     { "base_spec_fn": spec_black_hole_accretion,"M": 0, "R": 255, "CC": 255, "paint_fn": paint_black_hole_accretion, "desc": "Total void black sink surrounded by an intense glowing ring of orbital light reflection", "noise_scales": [2], "noise_R": 250},
    "plasma_core":      { "base_spec_fn": spec_plasma_core,"M": 220, "R": 15,  "CC": 16,  "paint_fn": paint_plasma_core,    "desc": "Plasma core - glowing plasma reactor metallic, electric purple-blue surface — GGX-FIX: R=8->15",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 40, "noise_R": 15},
    "quantum_black":    { "base_spec_fn": spec_quantum_black,"M": 0,   "R": 255, "CC": 235, "paint_fn": paint_quantum_black,   "desc": "Quantum black - near-perfect light absorption, maximum possible roughness (CC=235 dead flat)"},
    "solar_panel":      { "base_spec_fn": spec_solar_panel,"M": 15,  "R": 45,  "CC": 16, "paint_fn": paint_solar_panel,   "desc": "Solar panel - dark photovoltaic blue-black, slightly metallic cell grid look",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 8, "noise_R": 15},
    "superconductor":   { "base_spec_fn": spec_absolute_zero,"M": 200, "R": 145, "CC": 40, "paint_fn": paint_absolute_zero, "desc": "Heavily frosted metal sitting indefinitely at absolute zero, perpetually generating micro-ice — BASE-039 FIX: M=200 (frosted metal), R=145 (frost roughness)", "noise_scales": [8, 16, 32], "noise_R": 60},

    # ── PARADIGM BASES ────────────────────────────────────────────────────
    # These IDs appear in the JS BASES array at the end - special physics
    "singularity":      {"M": 120, "R": 65, "CC": 16, "paint_fn": paint_singularity_v2, "desc": "Theoretical boundary physics shifting colors infinitely toward standard absolute zero — LAZY-ANGLE-001 FIX: radial concentric rainbow rings. WARN-GGX-PARADIGM-001 FIX: R=2→65 so negative noise_R=-50 stays ≥15 (GGX floor)", "perlin": True, "perlin_octaves": 6, "noise_M": 200, "noise_R": -50},
    "liquid_obsidian":  {"M": 255, "R": 2,   "CC": 16,  "paint_fn": paint_obsidian_depth,  "desc": "Liquid obsidian - flowing glass-metal phase boundary, metallic oscillates at near-zero roughness — BASE-017 FIX: R=2 (PBR minimum)",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 60, "noise_R": 10},
    "prismatic":        {"M": 200, "R": 15, "CC": 16, "paint_fn": paint_iridescent_shift, "desc": "Over-tuned holographic logic breaking standard M/R bounds to create truly impossible colors — BASE-040 FIX: CC=16. GGX-FIX: R=10->15", "perlin": True, "perlin_octaves": 6, "noise_M": 255, "noise_R": 80},
    "p_mercury":        {"M": 255, "R": 2,   "CC": 16,  "paint_fn": paint_mercury_pool,    "desc": "Mercury (PARADIGM) - liquid metal pooling, flowing silver mercury surface",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.4, "perlin_lacunarity": 2.0, "noise_M": 15, "noise_R": 6},
    "p_phantom":        {"M": 0,   "R": 35,  "CC": 16, "paint_fn": paint_moonstone_adularescence, "desc": "Phantom (PARADIGM) - barely-there translucent mist, ghostly fog-like presence",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 15},
    "p_volcanic":       {"base_spec_fn": spec_p_volcanic, "M": 60,  "R": 180, "CC": 120, "paint_fn": paint_p_volcanic_v2, "desc": "Volcanic (PARADIGM) - lava cooling to rock, glowing heat veins through dark stone (CC=120 rough surface)",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.65, "perlin_lacunarity": 2.0, "noise_M": 25, "noise_R": 35},
    "arctic_ice":       {"M": 80,  "R": 50,  "CC": 90, "paint_fn": paint_moonstone_adularescence, "desc": "Arctic ice - frozen crystalline surface, cracked ice with blue-white interior — BASE-024 FIX: M=80 (ice crystal scattering), R=50 (crystalline micro-roughness), CC=90 (glossy ice)",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 30, "noise_R": 15},
    "carbon_weave":     {"M": 70,  "R": 35,  "CC": 16, "paint_fn": paint_carbon_weave,    "desc": "Carbon weave - visible diagonal twill weave carbon fiber pattern under coat",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 20, "noise_R": 15},
    "nebula":           {"M": 0,   "R": 25,  "CC": 16, "paint_fn": paint_opal_fire,        "desc": "Nebula - space dust cloud, purple-blue cosmic nebula with star sparkles",
                         "perlin": True, "perlin_octaves": 5, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 20},

    # PARADIGM — pixel-level random spec ("every spec at once")
    "quantum_foam":     {"M": 128, "R": 128, "CC": 80, "paint_fn": paint_none, "desc": "Quantum Foam (PARADIGM) - every possible reflectance/gloss/matte at once at pixel scale; neutral base so spec is the star",
                         "perlin": True, "perlin_octaves": 8, "noise_M": 255, "noise_R": 255, "noise_CC": 200},
    "infinite_finish":  {"M": 160, "R": 60, "CC": 16, "paint_fn": paint_infinite_warp, "desc": "Infinite Finish (PARADIGM) - fractal dimensional warp: self-similar chrome-matte inversion at every scale, surface appears to recede infinitely into itself — LAZY FIX: replaced paint_none dup of quantum_foam with domain-warped FBM",
                         "perlin": True, "perlin_octaves": 7, "noise_M": 180, "noise_R": 120, "noise_CC": 60},

    # ── ALIAS FIX ─────────────────────────────────────────────────────────
    # UI uses 'submarine_black', registry previously had 'sub_black'.
    # Both now exist. sub_black kept for backward compat.
    "submarine_black":  { "base_spec_fn": spec_industrial_tactical,"M": 0,   "R": 235, "CC": 215, "paint_fn": paint_rubber_absorb,   "desc": "Submarine hull black - anechoic submarine hull coating, absolute light absorption (CC=215 dead flat)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 3, "noise_R": 30},

    # ══════════════════════════════════════════════════════════════════════
    # RESEARCH SESSION 6 — 9 New Base Finishes (2026-03-29)
    # ══════════════════════════════════════════════════════════════════════

    # 3.1 Alubeam / Liquid Mirror — fills blurry-chrome zone (M=245, R=18, CC=16)
    "alubeam":          { "base_spec_fn": spec_alubeam_base, "M": 245, "R": 18,  "CC": 16, "paint_fn": paint_alubeam,
                         "desc": "BASF Alubeam liquid mirror — ultra-fine oriented aluminum flake, coherent blur between chrome and metallic. FLAT-FIX: boosted noise.",
                         "noise_scales": [32, 64], "noise_weights": [0.55, 0.45], "noise_M": 18, "noise_R": 15},

    # 3.2 Satin Candy / Matte Candy — candy under satin clear (R=0, G=170, CC=6)
    "satin_candy":      { "base_spec_fn": spec_satin_candy_base, "M": 0, "R": 170, "CC": 65, "paint_fn": paint_satin_candy,
                         "desc": "Satin Candy / Matte Candy — vivid pigment under satin clear, glowing-coal effect: color all, shine none",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.5, 0.3, 0.2], "noise_R": 20},

    # 3.3 Velvet / Suede Floc — true void black (R=0, G=248, CC=0)
    "velvet_floc":      { "base_spec_fn": spec_velvet_floc_base, "M": 0, "R": 248, "CC": 245, "paint_fn": paint_velvet_floc,
                         "desc": "Velvet / Suede Floc — absolute light absorption, G=248 eliminates all microfacet response, car becomes silhouette",
                         "noise_scales": [32, 64], "noise_weights": [0.6, 0.4], "noise_R": 8},

    # 3.4 Deep Pearl Type III — three-stage pearl with flop angle shift (M=88, R=58, CC=16)
    "deep_pearl":       { "base_spec_fn": spec_deep_pearl_base, "M": 88,  "R": 58,  "CC": 16, "paint_fn": paint_deep_pearl,
                         "desc": "Deep Pearl Type III — three-stage tri-coat pearl with edge-weighted metallic flop; warm/cool color shift at raking angles",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 18, "noise_R": 18},

    # 3.5 Gunmetal Satin Dark Industrial — dark metallic without gloss (M=205, R=145, CC=28)
    # 2026-04-19 HEENAN HA9 — Animal engine identity audit. R=145 reads as
    # matte-class (R≥140 is matte territory). "Satin" promises R 60-130.
    # Dropped to R=110 — true satin in the dark-industrial register. The
    # `subtle metallic sparkle` of the desc is preserved by the noise_R=28
    # spread on top of the new base R.
    "gunmetal_satin":   { "base_spec_fn": spec_gunmetal_satin_base, "M": 205, "R": 110, "CC": 28, "paint_fn": paint_gunmetal_satin,
                         "desc": "Gunmetal Satin / Dark Industrial Metallic — CNC-machined alloy zone, dark grey with subtle metallic sparkle, no gloss (HA9: R 145→110 — true satin range)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 25, "noise_R": 28},

    # 3.6 Forged Carbon Visible Weave — Lamborghini random-fiber composite (M=28, R=35, CC=18)
    "forged_carbon_vis": { "base_spec_fn": spec_forged_carbon_vis_base, "M": 28, "R": 35, "CC": 18, "paint_fn": paint_forged_carbon_vis,
                         "desc": "Forged Carbon Visible Weave — Lamborghini-style random-fiber organic composite; non-repeating charcoal with wet clearcoat depth",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 18, "noise_R": 22},

    # 3.7 Electroplated Gold / Rose Gold — warm mirror chrome (M=250, R=10, CC=16)
    "electroplated_gold": { "base_spec_fn": spec_electroplated_gold_base, "M": 250, "R": 10, "CC": 16, "paint_fn": paint_electroplated_gold,
                         "desc": "Electroplated Gold / Rose Gold — warm mirror: near-chrome metallic with warm gold or rose-gold albedo, Rolls-Royce Bespoke reference. FLAT-FIX: boosted noise.",
                         "noise_scales": [32, 64], "noise_weights": [0.55, 0.45], "noise_M": 18, "noise_R": 15},

    # 3.8 Cerakote / PVD Hard Coat — hard flat industrial coating (M=178, R=174, CC=5)
    "cerakote_pvd":     { "base_spec_fn": spec_cerakote_pvd_base, "M": 55, "R": 174, "CC": 160, "paint_fn": paint_cerakote_pvd,
                         "desc": "Cerakote / PVD Hard Coat — TiN/TiAlN thin hard coating: muted colors, flat surface, no clearcoat — FLAG-IND-005 FIX: M=55 (semi-metallic hard coat, not near-chrome), CC=160 (flat industrial, no clearcoat sheen; was CC=5 triggering metallised renderer path)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 35, "noise_R": 28},

    # 3.9 Hypershift Spectral — 360° color rotation with defined anchors (M=218, R=33, CC=16)
    "hypershift_spectral": { "base_spec_fn": spec_hypershift_spectral_base, "M": 218, "R": 33, "CC": 16, "paint_fn": paint_hypershift_spectral,
                         "desc": "Hypershift Spectral 360° — PPG HyperShift: 6-anchor full spectral sweep with steeper transitions than chameleon; distinct color at every viewing angle",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 40, "noise_R": 28},

    # ══════════════════════════════════════════════════════════════════════
    # ★ STRUCTURAL COLOR — Biologically-inspired finishes (2026-03-30)
    # Each paint+spec pair is MARRIED: spec knows paint's spatial structure.
    # No wild patterns — fine M/R/CC detail that serves the color physics.
    # ══════════════════════════════════════════════════════════════════════

    # (Structural Color SC-01/02/03 removed — shelved, functions no longer exist)

    # ══════════════════════════════════════════════════════════════════════
    # ★ COLORSHOXX — Premium color-shifting dual-tone flips (2026-03-31)
    # Paint creates two colors. Spec makes one flash at specular, other steady.
    # ══════════════════════════════════════════════════════════════════════

    "cx_inferno":    { "base_spec_fn": spec_colorshoxx_inferno, "M": 180, "R": 30, "CC": 20, "paint_fn": paint_colorshoxx_inferno,
                     "desc": "COLORSHOXX Inferno Flip — crimson red ↔ midnight blue dual-tone. Red zones flash metallic at specular, blue holds steady at normal incidence."},

    "cx_arctic":     { "base_spec_fn": spec_colorshoxx_arctic, "M": 170, "R": 35, "CC": 22, "paint_fn": paint_colorshoxx_arctic,
                     "desc": "COLORSHOXX Arctic Mirage — ice silver ↔ deep teal dual-tone. Silver zones flash brilliantly, teal zones stay deep and steady."},

    "cx_venom":      { "base_spec_fn": spec_colorshoxx_venom, "M": 150, "R": 40, "CC": 25, "paint_fn": paint_colorshoxx_venom,
                     "desc": "COLORSHOXX Venom Shift — toxic green ↔ black-purple dual-tone. Green zones pop metallic, purple stays dark and menacing."},

    "cx_solar":      { "base_spec_fn": spec_colorshoxx_solar, "M": 200, "R": 28, "CC": 20, "paint_fn": paint_colorshoxx_solar,
                     "desc": "COLORSHOXX Solar Flare — warm gold ↔ copper-red dual-tone. Gold zones flash like liquid metal, copper glows warmly."},

    "cx_phantom":    { "base_spec_fn": spec_colorshoxx_phantom, "M": 160, "R": 35, "CC": 24, "paint_fn": paint_colorshoxx_phantom,
                     "desc": "COLORSHOXX Phantom Violet — electric violet ↔ gunmetal dual-tone. Violet pops vivid metallic, gunmetal stays cold and steely."},

    # ── COLORSHOXX WAVE 2: 10 Extreme Dual-Tone (chrome↔matte) ──
    "cx_chrome_void":    { "base_spec_fn": spec_cx_chrome_void, "M": 120, "R": 100, "CC": 80, "paint_fn": paint_cx_chrome_void, "desc": "Chrome Void — pure mirror chrome ↔ absolute matte black. Maximum possible contrast."},
    "cx_blood_mercury":  { "base_spec_fn": spec_cx_blood_mercury, "M": 150, "R": 45, "CC": 28, "paint_fn": paint_cx_blood_mercury, "desc": "Blood Mercury — liquid chrome silver ↔ deep arterial crimson."},
    "cx_neon_abyss":     { "base_spec_fn": spec_cx_neon_abyss, "M": 120, "R": 90, "CC": 80, "paint_fn": paint_cx_neon_abyss, "desc": "Neon Abyss — electric hot pink chrome ↔ abyssal black-green matte."},
    "cx_glacier_fire":   { "base_spec_fn": spec_cx_glacier_fire, "M": 135, "R": 70, "CC": 60, "paint_fn": paint_cx_glacier_fire, "desc": "Glacier Fire — icy white-blue chrome ↔ molten orange-red matte."},
    "cx_obsidian_gold":  { "base_spec_fn": spec_cx_obsidian_gold, "M": 125, "R": 110, "CC": 100, "paint_fn": paint_cx_obsidian_gold, "desc": "Obsidian Gold — liquid 24k gold chrome ↔ volcanic obsidian dead matte."},
    "cx_electric_storm": { "base_spec_fn": spec_cx_electric_storm, "M": 130, "R": 80, "CC": 70, "paint_fn": paint_cx_electric_storm, "desc": "Electric Storm — crackling blue chrome ↔ thundercloud dark matte."},
    "cx_rose_chrome":    { "base_spec_fn": spec_cx_rose_chrome, "M": 135, "R": 90, "CC": 80, "paint_fn": paint_cx_rose_chrome, "desc": "Rose Chrome — rose gold chrome mirror ↔ deep burgundy velvet matte."},
    "cx_toxic_chrome":   { "base_spec_fn": spec_cx_toxic_chrome, "M": 125, "R": 95, "CC": 90, "paint_fn": paint_cx_toxic_chrome, "desc": "Toxic Chrome — acid green chrome ↔ chemical waste matte."},
    "cx_midnight_chrome": { "base_spec_fn": spec_cx_midnight_chrome, "M": 125, "R": 120, "CC": 110, "paint_fn": paint_cx_midnight_chrome, "desc": "Midnight Chrome — dark blue chrome mirror ↔ pure flat black void."},
    "cx_white_lightning": { "base_spec_fn": spec_cx_white_lightning, "M": 130, "R": 95, "CC": 80, "paint_fn": paint_cx_white_lightning, "desc": "White Lightning — blinding white chrome ↔ charcoal matte."},

    # ── COLORSHOXX WAVE 2: 5 Three-Color ──
    "cx_aurora_borealis": { "base_spec_fn": spec_cx_aurora_borealis, "M": 145, "R": 50, "CC": 30, "paint_fn": paint_cx_aurora_borealis, "desc": "Aurora Borealis — electric green + deep teal + violet purple. Three-zone northern lights."},
    "cx_dragon_scale":    { "base_spec_fn": spec_cx_dragon_scale, "M": 145, "R": 80, "CC": 70, "paint_fn": paint_cx_dragon_scale, "desc": "Dragon Scale — chrome gold + ember orange + charcoal black. Three-zone fire wyrm."},
    "cx_frozen_nebula":   { "base_spec_fn": spec_cx_frozen_nebula, "M": 145, "R": 60, "CC": 50, "paint_fn": paint_cx_frozen_nebula, "desc": "Frozen Nebula — ice white chrome + cosmic blue + deep purple void. Three-zone deep space."},
    "cx_hellfire":        { "base_spec_fn": spec_cx_hellfire, "M": 130, "R": 85, "CC": 80, "paint_fn": paint_cx_hellfire, "desc": "Hellfire — white-hot chrome + lava orange + scorched black. Three-zone inferno."},
    "cx_ocean_trench":    { "base_spec_fn": spec_cx_ocean_trench, "M": 120, "R": 80, "CC": 70, "paint_fn": paint_cx_ocean_trench, "desc": "Ocean Trench — bioluminescent teal + deep navy + abyssal black. Three-zone deep sea."},

    # ── COLORSHOXX WAVE 2: 5 Four-Color ──
    "cx_supernova":      { "base_spec_fn": spec_cx_supernova, "M": 140, "R": 70, "CC": 60, "paint_fn": paint_cx_supernova, "desc": "Supernova — white-hot chrome + electric blue + magenta + void black. Four-stage stellar explosion."},
    "cx_prism_shatter":  { "base_spec_fn": spec_cx_prism_shatter, "M": 175, "R": 35, "CC": 25, "paint_fn": paint_cx_prism_shatter, "desc": "Prism Shatter — chrome red + gold + teal + indigo. Four-color shattered light spectrum."},
    "cx_acid_rain":      { "base_spec_fn": spec_cx_acid_rain, "M": 125, "R": 70, "CC": 55, "paint_fn": paint_cx_acid_rain, "desc": "Acid Rain — toxic yellow chrome + sick green + bruise purple + ash gray matte."},
    "cx_royal_spectrum":  { "base_spec_fn": spec_cx_royal_spectrum, "M": 195, "R": 28, "CC": 20, "paint_fn": paint_cx_royal_spectrum, "desc": "Royal Spectrum — chrome silver + sapphire blue + ruby red + emerald green. Crown jewels."},
    "cx_apocalypse":     { "base_spec_fn": spec_cx_apocalypse, "M": 120, "R": 80, "CC": 70, "paint_fn": paint_cx_apocalypse, "desc": "Apocalypse — scorching white chrome + blood red + rust orange + dead black. End times."},

    # ══════════════════════════════════════════════════════════════════════
    # ★ MORTAL SHOKK — Fighting-game-inspired married paint+spec (2026-03-31)
    # ══════════════════════════════════════════════════════════════════════

    "ms_frozen_fury":    { "base_spec_fn": spec_ms_frozen_fury, "M": 150, "R": 50, "CC": 30, "paint_fn": paint_ms_frozen_fury, "desc": "Frozen Fury — ice blue + frozen white chrome. White zones flash at specular, blue holds steady."},
    "ms_venom_strike":   { "base_spec_fn": spec_ms_venom_strike, "M": 120, "R": 100, "CC": 80, "paint_fn": paint_ms_venom_strike, "desc": "Venom Strike — deep gold metallic flash + black matte fire zones. Scorpion heat."},
    "ms_thunder_lord":   { "base_spec_fn": spec_ms_thunder_lord, "M": 140, "R": 60, "CC": 40, "paint_fn": paint_ms_thunder_lord, "desc": "Thunder Lord — electric blue + white lightning veins on dark navy base."},
    "ms_chrome_cage":    { "base_spec_fn": spec_ms_chrome_cage, "M": 185, "R": 30, "CC": 22, "paint_fn": paint_ms_chrome_cage, "desc": "Chrome Cage — Hollywood gold chrome + green energy shimmer."},
    "ms_dragon_flame":   { "base_spec_fn": spec_ms_dragon_flame, "M": 130, "R": 70, "CC": 55, "paint_fn": paint_ms_dragon_flame, "desc": "Dragon Flame — red + orange fire gradient with ember particles on dark smoke."},
    "ms_royal_edge":     { "base_spec_fn": spec_ms_royal_edge, "M": 155, "R": 45, "CC": 30, "paint_fn": paint_ms_royal_edge, "desc": "Royal Edge — royal blue silk + silver steel blade streaks."},
    "ms_feral_grin":     { "base_spec_fn": spec_ms_feral_grin, "M": 155, "R": 55, "CC": 35, "paint_fn": paint_ms_feral_grin, "desc": "Feral Grin — hot pink + venomous purple. Aggressive contrast."},
    "ms_acid_scale":     { "base_spec_fn": spec_ms_acid_scale, "M": 115, "R": 75, "CC": 55, "paint_fn": paint_ms_acid_scale, "desc": "Acid Scale — acid green + dark scale cell pattern. Voronoi-like reptile skin."},
    "ms_soul_drain":     { "base_spec_fn": spec_ms_soul_drain, "M": 105, "R": 120, "CC": 100, "paint_fn": paint_ms_soul_drain, "desc": "Soul Drain — glowing red energy mist on absolute black void."},
    "ms_emerald_shadow": { "base_spec_fn": spec_ms_emerald_shadow, "M": 85, "R": 100, "CC": 70, "paint_fn": paint_ms_emerald_shadow, "desc": "Emerald Shadow — deep emerald + shadow black stealth zones."},
    "ms_void_walker":    { "base_spec_fn": spec_ms_void_walker, "M": 40, "R": 130, "CC": 120, "paint_fn": paint_ms_void_walker, "desc": "Void Walker — absolute black with faint shadow duplicate shimmer."},
    "ms_ghost_vapor":    { "base_spec_fn": spec_ms_ghost_vapor, "M": 150, "R": 65, "CC": 50, "paint_fn": paint_ms_ghost_vapor, "desc": "Ghost Vapor — gray smoke wisps + chrome peek-through."},
    "ms_shape_shift":    { "base_spec_fn": spec_ms_shape_shift, "M": 160, "R": 45, "CC": 30, "paint_fn": paint_ms_shape_shift, "desc": "Shape Shift — morphing 3-color zones: mystic green + amber + deep purple."},
    "ms_titan_bronze":   { "base_spec_fn": spec_ms_titan_bronze, "M": 135, "R": 85, "CC": 65, "paint_fn": paint_ms_titan_bronze, "desc": "Titan Bronze — massive bronze metallic + dark brutal texture."},
    "ms_war_hammer":     { "base_spec_fn": spec_ms_war_hammer, "M": 105, "R": 95, "CC": 70, "paint_fn": paint_ms_war_hammer, "desc": "War Hammer — dark armor plate + blood red accent veins."},

    # ══════════════════════════════════════════════════════════════════════
    # ★ NEON UNDERGROUND — blacklight reactive neon-glow finishes (2026-04-03)
    # Seeds 9200-9209.  High M (240+), low R (15-20), CC=16.
    # ══════════════════════════════════════════════════════════════════════

    "neon_pink_blaze":    { "base_spec_fn": spec_neon_pink_blaze, "M": 242, "R": 16, "CC": 16, "paint_fn": paint_neon_pink_blaze, "desc": "Neon Pink Blaze — hot pink neon with concentric pulsing glow zones."},
    "neon_toxic_green":   { "base_spec_fn": spec_neon_toxic_green, "M": 245, "R": 15, "CC": 16, "paint_fn": paint_neon_toxic_green, "desc": "Neon Toxic Green — radioactive green with Geiger-counter scatter particles."},
    "neon_electric_blue": { "base_spec_fn": spec_neon_electric_blue, "M": 240, "R": 17, "CC": 16, "paint_fn": paint_neon_electric_blue, "desc": "Neon Electric Blue — deep UV blue with plasma discharge veins."},
    "neon_blacklight":    { "base_spec_fn": spec_neon_blacklight, "M": 244, "R": 18, "CC": 16, "paint_fn": paint_neon_blacklight, "desc": "Neon Blacklight — UV-reactive purple that glows in dark zones."},
    "neon_orange_hazard": { "base_spec_fn": spec_neon_orange_hazard, "M": 240, "R": 15, "CC": 16, "paint_fn": paint_neon_orange_hazard, "desc": "Neon Orange Hazard — construction orange with diagonal warning stripe pattern."},
    "neon_red_alert":     { "base_spec_fn": spec_neon_red_alert, "M": 243, "R": 15, "CC": 16, "paint_fn": paint_neon_red_alert, "desc": "Neon Red Alert — emergency red with siren-like concentric rings."},
    "neon_cyber_yellow":  { "base_spec_fn": spec_neon_cyber_yellow, "M": 240, "R": 16, "CC": 16, "paint_fn": paint_neon_cyber_yellow, "desc": "Neon Cyber Yellow — cyberpunk yellow with circuit trace PCB pattern."},
    "neon_ice_white":     { "base_spec_fn": spec_neon_ice_white, "M": 248, "R": 15, "CC": 16, "paint_fn": paint_neon_ice_white, "desc": "Neon Ice White — cold white neon with frost crystallization dendrites."},
    "neon_dual_glow":     { "base_spec_fn": spec_neon_dual_glow, "M": 242, "R": 16, "CC": 16, "paint_fn": paint_neon_dual_glow, "desc": "Neon Dual Glow — two-color neon (pink+blue) split by warped spatial field."},
    "neon_rainbow_tube":  { "base_spec_fn": spec_neon_rainbow_tube, "M": 245, "R": 15, "CC": 16, "paint_fn": paint_neon_rainbow_tube, "desc": "Neon Rainbow Tube — full spectrum neon tube with horizontal banding."},

    # ══════════════════════════════════════════════════════════════════════
    # ★ ANIME INSPIRED — anime/manga-style finishes (Pack #7)
    # Seeds 9300-9309.  Married paint+spec, cel shading, speed lines, sparkle.
    # ══════════════════════════════════════════════════════════════════════

    "anime_cel_shade_chrome": { "base_spec_fn": spec_anime_cel_shade_chrome, "M": 200, "R": 30, "CC": 20, "paint_fn": paint_anime_cel_shade_chrome, "desc": "Anime Cel Shade Chrome — flat cel-shaded bands with sharp metallic highlight steps."},
    "anime_speed_lines":      { "base_spec_fn": spec_anime_speed_lines, "M": 180, "R": 40, "CC": 30, "paint_fn": paint_anime_speed_lines, "desc": "Anime Speed Lines — radial motion lines from focal point. White streaks on dark."},
    "anime_sparkle_burst":    { "base_spec_fn": spec_anime_sparkle_burst, "M": 220, "R": 20, "CC": 25, "paint_fn": paint_anime_sparkle_burst, "desc": "Anime Sparkle Burst — 4-pointed starburst sparkle clusters on midnight base."},
    "anime_gradient_hair":    { "base_spec_fn": spec_anime_gradient_hair, "M": 140, "R": 35, "CC": 20, "paint_fn": paint_anime_gradient_hair, "desc": "Anime Gradient Hair — vivid magenta-pink top fading to deep indigo bottom."},
    "anime_mecha_plate":      { "base_spec_fn": spec_anime_mecha_plate, "M": 190, "R": 40, "CC": 22, "paint_fn": paint_anime_mecha_plate, "desc": "Anime Mecha Plate — hard geometric panel grid with metallic zones and dark seams."},
    "anime_sakura_scatter":   { "base_spec_fn": spec_anime_sakura_scatter, "M": 100, "R": 45, "CC": 20, "paint_fn": paint_anime_sakura_scatter, "desc": "Anime Sakura Scatter — cherry blossom petal scatter on soft pink background."},
    "anime_energy_aura":      { "base_spec_fn": spec_anime_energy_aura, "M": 210, "R": 25, "CC": 22, "paint_fn": paint_anime_energy_aura, "desc": "Anime Energy Aura — radial power glow field with energy rays and bright core."},
    "anime_comic_halftone":   { "base_spec_fn": spec_anime_comic_halftone, "M": 50, "R": 90, "CC": 45, "paint_fn": paint_anime_comic_halftone, "desc": "Anime Comic Halftone — Ben-Day dot pattern with size variation on paper base."},
    "anime_neon_outline":     { "base_spec_fn": spec_anime_neon_outline, "M": 200, "R": 30, "CC": 25, "paint_fn": paint_anime_neon_outline, "desc": "Anime Neon Outline — dark base with bright cyan-magenta neon edge highlights."},
    "anime_crystal_facet":    { "base_spec_fn": spec_anime_crystal_facet, "M": 210, "R": 25, "CC": 20, "paint_fn": paint_anime_crystal_facet, "desc": "Anime Crystal Facet — large angular Voronoi crystalline facets with jewel colors."},

    # ══════════════════════════════════════════════════════════════════════
    # ★ IRIDESCENT INSECTS — insect-inspired structural-color finishes (Pack #9)
    # Seeds 9400-9409.  Married paint+spec, thin-film iridescence, wing patterns.
    # ══════════════════════════════════════════════════════════════════════

    "beetle_jewel":       { "base_spec_fn": spec_beetle_jewel, "M": 200, "R": 25, "CC": 18, "paint_fn": paint_beetle_jewel, "desc": "Beetle Jewel — Chrysina green-gold iridescent shell with organic flow zones."},
    "beetle_rainbow":     { "base_spec_fn": spec_beetle_rainbow, "M": 220, "R": 20, "CC": 18, "paint_fn": paint_beetle_rainbow, "desc": "Beetle Rainbow — Chrysochroa full-spectrum wing case via thin-film interference."},
    "butterfly_morpho":   { "base_spec_fn": spec_butterfly_morpho, "M": 230, "R": 20, "CC": 16, "paint_fn": paint_butterfly_morpho, "desc": "Butterfly Morpho — brilliant Morpho blue structural color with angle-dependent flash."},
    "butterfly_monarch":  { "base_spec_fn": spec_butterfly_monarch, "M": 55, "R": 80, "CC": 30, "paint_fn": paint_butterfly_monarch, "desc": "Butterfly Monarch — orange-black monarch wing pattern with Voronoi vein network."},
    "dragonfly_wing":     { "base_spec_fn": spec_dragonfly_wing, "M": 130, "R": 20, "CC": 18, "paint_fn": paint_dragonfly_wing, "desc": "Dragonfly Wing — transparent wing membrane with rainbow interference and dark veins."},
    "scarab_gold":        { "base_spec_fn": spec_scarab_gold, "M": 210, "R": 25, "CC": 18, "paint_fn": paint_scarab_gold, "desc": "Scarab Gold — Egyptian scarab golden-green iridescent shift with shell texture."},
    "moth_luna":          { "base_spec_fn": spec_moth_luna, "M": 40, "R": 120, "CC": 70, "paint_fn": paint_moth_luna, "desc": "Moth Luna — pale green Luna moth with concentric eye-spot patterns. Soft matte."},
    "beetle_stag":        { "base_spec_fn": spec_beetle_stag, "M": 170, "R": 30, "CC": 20, "paint_fn": paint_beetle_stag, "desc": "Beetle Stag — dark metallic stag beetle armor plates with chitin shine."},
    "wasp_warning":       { "base_spec_fn": spec_wasp_warning, "M": 80, "R": 50, "CC": 30, "paint_fn": paint_wasp_warning, "desc": "Wasp Warning — yellow-black aposematic banding with metallic shimmer."},
    "firefly_glow":       { "base_spec_fn": spec_firefly_glow, "M": 160, "R": 40, "CC": 30, "paint_fn": paint_firefly_glow, "desc": "Firefly Glow — dark exoskeleton with bioluminescent yellow-green lantern zones."},
}

# Merge Enhanced Foundation (30 premium bases with real spec+paint functions)
BASE_REGISTRY.update(ENHANCED_FOUNDATION)

# ── SHOKK SERIES v2 - 20 color-shift PBR bases ──────────────────────────────
try:
    from engine.shokk_series import SHOKK_BASES as _SHOKK_V2
    BASE_REGISTRY.update(_SHOKK_V2)
    pass  # SHOKK Series loaded; print removed (fired on every engine import)
except Exception as _shokk_exc:
    print(f"[SHOKK Series] Load failed: {_shokk_exc}")


def _apply_staging_registry_patches():
    """Patch BASE_REGISTRY with v2 implementations from engine.paint_v2 (no _staging dependency)."""
    try:
        import numpy as np
        import importlib

        def _adapt_paint_fn_for_scalar_bb(fn):
            def _wrapped(paint, shape, mask, seed, pm, bb):
                if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
                bb_val = bb
                try:
                    h, w = shape[:2] if isinstance(shape, (tuple, list)) and len(shape) >= 2 else paint.shape[:2]
                    if np.isscalar(bb) or (hasattr(bb, "ndim") and bb.ndim == 0):
                        bb_val = np.full((int(h), int(w)), float(bb), dtype=np.float32)
                    elif hasattr(bb, "ndim") and bb.ndim == 3:
                        bb_val = np.mean(bb[:int(h), :int(w), :3], axis=2).astype(np.float32)
                    elif hasattr(bb, "ndim") and bb.ndim == 2:
                        bb_val = bb[:int(h), :int(w)].astype(np.float32)
                except Exception:
                    bb_val = bb
                return fn(paint, shape, mask, seed, pm, bb_val)
            return _wrapped

        categories = [
            "brushed_directional", "candy_special", "carbon_composite", "ceramic_glass",
            "chrome_mirror", "exotic_metal", "finish_basic", "metallic_flake", "metallic_standard",
            "military_tactical", "oem_automotive", "paradigm_scifi", "premium_luxury",
            "paint_technique", "racing_heritage", "raw_weathered", "shokk_series",
            "weathered_worn", "wrap_vinyl",
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
    except Exception as exc:
        print(f"[V2 Registry] base_registry_data patch skipped: {exc}")


_apply_staging_registry_patches()


def _spec_foundation_flat(shape, seed, sm, base_m, base_r):
    """Return flat M/R channels for vanilla Foundation picker entries."""
    import numpy as np

    h, w = shape[:2] if len(shape) > 2 else shape
    base_m_f = float(base_m)
    base_r_f = float(base_r) if base_m_f >= 240 else max(float(base_r), 15.0)
    M_arr = np.full((h, w), base_m_f, dtype=np.float32)
    R_arr = np.full((h, w), base_r_f, dtype=np.float32)
    return M_arr, R_arr


def _normalize_classic_foundation_contract():
    """Keep the regular Foundation picker finishes paint-identity + flat spec.

    Painter mandate (2026-04-22): the non-`f_*` entries that still live under
    BASE_GROUPS["Foundation"] are vanilla material responses only. They may
    change the sheen constants (M/R/CC), but they must not recolor paint or add
    baked-in per-pixel texture on the spec map.
    """
    classic_foundation_ids = {
        "ceramic",
        "gloss",
        "piano_black",
        "wet_look",
        "semi_gloss",
        "satin",
        "scuffed_satin",
        "silk",
        "eggshell",
        "clear_matte",
        "primer",
        "flat_black",
        "matte",
        "living_matte",
        "chalky_base",
    }
    noise_keys = {
        "noise_M", "noise_R", "noise_CC",
        "noise_scales", "noise_weights",
        "perlin", "perlin_octaves", "perlin_persistence", "perlin_lacunarity",
    }
    for base_id in classic_foundation_ids:
        entry = BASE_REGISTRY.get(base_id)
        if not entry:
            continue
        entry["paint_fn"] = paint_none
        entry["base_spec_fn"] = _spec_foundation_flat
        for key in noise_keys:
            entry.pop(key, None)


_normalize_classic_foundation_contract()
