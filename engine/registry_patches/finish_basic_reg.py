"""
Registry patch for Finish Basic category.
"""

REGISTRY_PATCH = {
    "blackout": "paint_blackout_v2",
    "ceramic": "paint_ceramic_v2",
    # "chameleon" removed — WEAK-037 FIX: paint_chameleon_v2 is pass-through; BASE_REGISTRY uses paint_cp_chameleon (HSV hue shift)
    "clear_matte": "paint_clear_matte_v2",
    "eggshell": "paint_eggshell_v2",
    "flat_black": "paint_flat_black_v2",
    "frozen": "paint_frozen_v2",
    "frozen_matte": "paint_frozen_matte_v2",
    "gloss": "paint_gloss_v2",
    # "iridescent" removed — WEAK-038 FIX: paint_iridescent_v2 is pass-through; BASE_REGISTRY uses paint_cp_iridescent (3-phase rainbow)
    "liquid_obsidian": "paint_liquid_obsidian_v2",
    "living_matte": "paint_living_matte_v2",
    "matte": "paint_matte_v2",
    "mirror_gold": "paint_mirror_gold_v2",
    "noise_scales": "paint_noise_scales_v2",
    "orange_peel_gloss": "paint_orange_peel_gloss_v2",
    "organic_metal": "paint_organic_metal_v2",
    "perlin": "paint_perlin_v2",
    "piano_black": "paint_piano_black_v2",
    "primer": "paint_primer_v2",
    "satin": "paint_satin_v2",
    "satin_metal": "paint_satin_metal_v2",
    "scuffed_satin": "paint_scuffed_satin_v2",
    "semi_gloss": "paint_semi_gloss_v2",
    "silk": "paint_silk_v2",
    "terrain_chrome": "paint_terrain_chrome_v2",
    "vantablack": "paint_vantablack_v2",
    "volcanic": "paint_volcanic_v2",
    "wet_look": "paint_wet_look_v2",
}


SPEC_PATCH = {
    "blackout": "spec_blackout",
    "ceramic": "spec_ceramic",
    # "chameleon" removed — WEAK-037 FIX: flat-constant spec_chameleon replaced; BASE_REGISTRY M=160/R=25/CC=16 with perlin noise will apply
    "clear_matte": "spec_clear_matte",
    "eggshell": "spec_eggshell",
    "flat_black": "spec_flat_black",
    "frozen": "spec_frozen",
    "frozen_matte": "spec_frozen_matte",
    "gloss": "spec_gloss",
    # "iridescent" removed — WEAK-038 FIX: flat-constant spec_iridescent replaced; BASE_REGISTRY M=200/R=10/CC=16 noise_scales=[2,4] will apply
    "liquid_obsidian": "spec_liquid_obsidian",
    "living_matte": "spec_living_matte",
    "matte": "spec_matte",
    "mirror_gold": "spec_mirror_gold",
    "noise_scales": "spec_noise_scales",
    "orange_peel_gloss": "spec_orange_peel_gloss",
    "organic_metal": "spec_organic_metal",
    "perlin": "spec_perlin",
    "piano_black": "spec_piano_black",
    "primer": "spec_primer",
    "satin": "spec_satin",
    "satin_metal": "spec_satin_metal",
    "scuffed_satin": "spec_scuffed_satin",
    "semi_gloss": "spec_semi_gloss",
    "silk": "spec_silk",
    "terrain_chrome": "spec_terrain_chrome",
    "vantablack": "spec_vantablack",
    "volcanic": "spec_volcanic",
    "wet_look": "spec_wet_look",
}
