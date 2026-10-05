// =============================================================================
// SHOKKER — Reimagined Monolithic Taxonomy (628 finishes)
// Single source: only backend-registered IDs. No filler. The benchmark.
// =============================================================================

const _SPECIALS_SHOKKER = {
    "Shokk Series": ["shokk_adrenaline", "shokk_affliction", "shokk_aftermath", "shokk_blackout", "shokk_defib", "shokk_dia_de_muertos", "shokk_ekg", "shokk_flatline", "shokk_lafleur", "shokk_northern_soul", "shokk_overload", "shokk_resurrection", "shokk_samurai", "shokk_unleashed", "shokk_voltage"],
    "PARADIGM": ["blackbody", "ember", "p_aurora", "pulse", "thin_film", "crystal_lattice", "living_chrome", "mercury_pool", "quantum", "singularity", "gravity_well", "phase_shift", "void", "wormhole", "glass_armor", "magnetic", "p_static", "stealth"],
};

const _SPECIALS_COLOR_SCIENCE = {
    "Chameleon": ["chameleon_amethyst", "chameleon_arctic", "chameleon_aurora", "chameleon_copper", "chameleon_emerald", "chameleon_fire", "chameleon_frost", "chameleon_galaxy", "chameleon_midnight", "chameleon_neon", "chameleon_obsidian", "chameleon_ocean", "chameleon_phoenix", "chameleon_venom", "mystichrome"],
    "Prizm": ["prizm_adaptive", "prizm_arctic", "prizm_black_rainbow", "prizm_blood_moon", "prizm_cosmos", "prizm_dark_matter", "prizm_duochrome", "prizm_ember", "prizm_fire_ice", "prizm_holographic", "prizm_iridescent", "prizm_midnight", "prizm_mystichrome", "prizm_neon", "prizm_oceanic", "prizm_phoenix", "prizm_solar", "prizm_spectrum", "prizm_venom"],
    "Color-Shift Adaptive": ["cs_cool", "cs_warm", "cs_complementary", "cs_monochrome", "cs_subtle", "cs_rainbow", "cs_vivid", "cs_extreme", "cs_triadic", "cs_split", "cs_neon_shift", "cs_ocean_shift", "cs_chrome_shift", "cs_earth", "cs_prism_shift"],
    "Color-Shift Presets": ["cs_deepocean", "cs_solarflare", "cs_inferno", "cs_nebula", "cs_mystichrome", "cs_supernova", "cs_emerald", "cs_candypaint", "cs_oilslick", "cs_rose_gold_shift", "cs_goldrush", "cs_toxic", "cs_darkflame", "cs_rosegold", "cs_twilight", "cs_neon_dreams"],
    "Color-Shift Duos": ["cs_amber_indigo", "cs_aqua_maroon", "cs_black_blue", "cs_black_gold", "cs_black_red", "cs_black_silver", "cs_blue_orange", "cs_blush_emerald", "cs_bronze_green", "cs_bronze_navy", "cs_bronze_purple", "cs_bronze_red", "cs_burgundy_gold", "cs_candy_paint", "cs_champagne_cobalt", "cs_charcoal_honey", "cs_chocolate_mint", "cs_copper_blue", "cs_copper_gold", "cs_copper_lime", "cs_copper_teal", "cs_copper_violet", "cs_coral_cobalt", "cs_crimson_jade", "cs_dark_flame", "cs_fire_ice", "cs_gold_emerald", "cs_gold_navy", "cs_gold_rush", "cs_graphite_coral", "cs_green_blue", "cs_green_gold", "cs_gunmetal_gold", "cs_gunmetal_lime", "cs_gunmetal_orange", "cs_honey_plum", "cs_ivory_indigo", "cs_lavender_jade", "cs_lime_blue", "cs_lime_pink", "cs_lime_violet", "cs_magenta_blue", "cs_magenta_gold", "cs_magenta_teal", "cs_mint_maroon", "cs_navy_gold", "cs_navy_orange", "cs_navy_silver", "cs_orange_navy", "cs_orange_purple", "cs_peach_cobalt", "cs_pewter_rose", "cs_pink_gold", "cs_pink_purple", "cs_pink_teal", "cs_purple_gold", "cs_purple_lime", "cs_red_black", "cs_red_gold", "cs_red_purple", "cs_rose_emerald", "cs_sage_crimson", "cs_silver_purple", "cs_silver_red", "cs_silver_teal", "cs_sky_gold", "cs_slate_amber", "cs_sunset_ocean", "cs_teal_orange", "cs_teal_pink", "cs_titanium_crimson", "cs_violet_gold", "cs_violet_teal", "cs_white_blue", "cs_white_green", "cs_white_purple", "cs_white_red", "cs_yellow_blue"],
    "Gradient Directional": ["grad_arctic_dawn", "grad_bruise", "grad_copper_patina", "grad_fire_fade", "grad_fire_fade_diag", "grad_fire_fade_h", "grad_forest_canopy", "grad_golden_hour", "grad_golden_hour_h", "grad_ice_fire", "grad_lava_flow", "grad_midnight_ember", "grad_neon_rush", "grad_neon_rush_h", "grad_ocean_depths", "grad_ocean_depths_diag", "grad_ocean_depths_h", "grad_steel_forge", "grad_sunset", "grad_sunset_diag", "grad_toxic_waste", "grad_twilight", "grad_twilight_diag", "grad_twilight_h"],
    "Gradient Vortex": ["grad_blue_vortex", "grad_copper_vortex", "grad_fire_vortex", "grad_gold_vortex", "grad_green_vortex", "grad_pink_vortex", "grad_shadow_vortex", "grad_teal_vortex", "grad_violet_vortex", "grad_white_vortex"],
};

const _SPECIALS_MATERIAL_WORLD = {
    "Atelier — Ultra Detail": ["atelier_brushed_titanium", "atelier_carbon_weave_micro", "atelier_cathedral_glass", "atelier_ceramic_glaze", "atelier_damascus_layers", "atelier_engine_turned", "atelier_fluid_metal", "atelier_forged_iron_texture", "atelier_gold_leaf_micro", "atelier_hand_brushed_metal", "atelier_japanese_lacquer", "atelier_marble_vein_fine", "atelier_micro_flake_burst", "atelier_obsidian_glass", "atelier_pearl_depth_layers", "atelier_silk_weave", "atelier_vintage_enamel_crackle"],
    "Metals & Forged": ["forged_iron", "cast_iron", "hammered_copper", "brushed_steel_dark", "etched_metal", "bare_aluminum", "chrome_oxidized", "heat_blued", "oxidized_metal", "mill_scale", "weathered_metal", "carbon_raw", "weathered_paint", "worn_chrome", "phosphate_coat", "raw_weld", "grinding_marks"],
    "Glass & Surface": ["obsidian_glass", "stained_glass", "venetian_glass", "acid_etched_glass", "concrete", "granite", "raw_concrete", "sandstone", "slate_tile", "stucco", "terra_cotta", "volcanic_rock", "brick_wall"],
    "Leather & Texture": ["aged_leather", "crocodile_leather", "suede", "velvet", "velvet_crush", "linen", "burlap", "cork", "parchment", "bark", "petrified_wood"],
};

const _SPECIALS_FUSION_LAB = {
    "Ghost Geometry": ["ghost_camo", "ghost_circuit", "ghost_diamonds", "ghost_fracture", "ghost_hex", "ghost_panel", "ghost_quilt", "ghost_scales", "ghost_stripes", "ghost_vortex", "ghost_waves"],
    "Depth Illusion": ["depth_bubble", "depth_canyon", "depth_crack", "depth_erosion", "depth_honeycomb", "depth_map", "depth_pillow", "depth_ripple", "depth_scale", "depth_vortex", "depth_wave"],
    "Material Gradients": ["gradient_anodized_gloss", "gradient_candy_frozen", "gradient_candy_matte", "gradient_carbon_chrome", "gradient_chrome_matte", "gradient_ember_ice", "gradient_metallic_satin", "gradient_obsidian_mirror", "gradient_pearl_chrome", "gradient_spectraflame_void"],
    "Directional Grain": ["aniso_circular_chrome", "aniso_crosshatch_steel", "aniso_diagonal_candy", "aniso_herringbone_gold", "aniso_horizontal_chrome", "aniso_radial_metallic", "aniso_spiral_mercury", "aniso_turbulence_metal", "aniso_vertical_pearl", "aniso_wave_titanium"],
    "Reactive Panels": ["reactive_candy_reveal", "reactive_chrome_fade", "reactive_dual_tone", "reactive_ghost_metal", "reactive_matte_shine", "reactive_mirror_shadow", "reactive_pearl_flash", "reactive_pulse_metal", "reactive_stealth_pop", "reactive_warm_cold"],
    "Sparkle Systems": ["sparkle_champagne", "sparkle_confetti", "sparkle_constellation", "sparkle_diamond_dust", "sparkle_firefly", "sparkle_galaxy", "sparkle_lightning_bug", "sparkle_meteor", "sparkle_snowfall", "sparkle_starfield"],
    "Multi-Scale Texture": ["multiscale_candy_frost", "multiscale_carbon_micro", "multiscale_chrome_grain", "multiscale_chrome_sand", "multiscale_flake_grain", "multiscale_frost_crystal", "multiscale_matte_silk", "multiscale_metal_grit", "multiscale_pearl_texture", "multiscale_satin_weave"],
    "Weather & Age": ["weather_acid_rain", "weather_barn_dust", "weather_desert_blast", "weather_hood_bake", "weather_ice_storm", "weather_ocean_mist", "weather_road_spray", "weather_salt_spray", "weather_sun_fade", "weather_volcanic_ash"],
    "Exotic Physics": ["exotic_anti_metal", "exotic_ceramic_void", "exotic_crystal_clear", "exotic_dark_glass", "exotic_foggy_chrome", "exotic_glass_paint", "exotic_inverted_candy", "exotic_liquid_glass", "exotic_phantom_mirror", "exotic_wet_void"],
    "Tri-Zone Materials": ["trizone_anodized_candy_silk", "trizone_ceramic_flake_satin", "trizone_chrome_candy_matte", "trizone_frozen_ember_chrome", "trizone_glass_metal_matte", "trizone_mercury_obsidian_candy", "trizone_pearl_carbon_gold", "trizone_stealth_spectra_frozen", "trizone_titanium_copper_chrome", "trizone_vanta_chrome_pearl"],
    "Metallic Halos": ["halo_circle_pearl", "halo_crack_chrome", "halo_diamond_chrome", "halo_grid_pearl", "halo_hex_chrome", "halo_ripple_chrome", "halo_scale_gold", "halo_star_metal", "halo_voronoi_metal", "halo_wave_candy"],
    "Light Waves": ["wave_candy_flow", "wave_chrome_tide", "wave_circular_radar", "wave_diagonal_sweep", "wave_dual_frequency", "wave_metallic_pulse", "wave_moire_metal", "wave_pearl_current", "wave_standing_chrome", "wave_turbulent_flow"],
    "Fractal Chaos": ["fractal_candy_chaos", "fractal_chrome_decay", "fractal_cosmic_dust", "fractal_deep_organic", "fractal_dimension", "fractal_electric_noise", "fractal_liquid_fire", "fractal_matte_chrome", "fractal_metallic_storm", "fractal_pearl_cloud", "fractal_warm_cold"],
    "Spectral Reactive": ["spectral_complementary", "spectral_dark_light", "spectral_earth_sky", "spectral_inverse_logic", "spectral_mono_chrome", "spectral_neon_reactive", "spectral_prismatic_flip", "spectral_rainbow_metal", "spectral_sat_metal", "spectral_warm_cool"],
    "Panel Quilting": ["quilt_alternating_duo", "quilt_candy_tiles", "quilt_chrome_mosaic", "quilt_diamond_shimmer", "quilt_gradient_tiles", "quilt_hex_variety", "quilt_metallic_pixels", "quilt_organic_cells", "quilt_pearl_patchwork", "quilt_random_chaos"],
};

const _SPECIALS_RACING_HERITAGE = {
    "Racing Heritage": ["barn_find", "dawn_patrol", "drafting", "drive_in", "hot_rod_flames", "classic_racing", "nascar_heritage", "nostalgia_drag", "old_school", "race_worn", "burnout_zone", "chicane_blur", "cool_down", "drag_chute", "last_lap", "pace_lap", "photo_finish", "pit_stop", "pole_position", "victory_burnout", "green_flag", "black_flag", "white_flag", "night_race", "rain_race", "under_lights", "muscle_car_stripe", "patina_truck", "faded_glory", "daily_driver", "beat_up_truck", "diner_chrome", "jukebox", "pin_up", "slipstream", "tunnel_run", "worn_asphalt", "grindhouse", "simulation", "time_warp", "zeppelin", "woodie", "woodie_wagon", "flag_wave", "red_mist", "wet_gloss", "liquid_gold", "moonshine", "art_deco_gold", "mother_of_pearl", "ruby", "sapphire", "alexandrite", "champagne_toast"],
};

const _SPECIALS_ATMOSPHERE = {
    "Atmosphere": ["acid_rain", "black_ice", "blizzard", "desert_mirage", "dew_drop", "dust_storm", "ember_glow", "fog_bank", "frost_bite", "frozen_lake", "hail_damage", "heat_wave", "hurricane", "lightning_strike", "liquid_metal", "magma_flow", "meteor_shower", "monsoon", "ocean_floor", "oil_slick", "permafrost", "solar_wind", "tidal_wave", "tornado_alley", "volcanic_glass"],
};

const _SPECIALS_SIGNAL = {
    "Signal": ["aurora_glow", "bioluminescent_wave", "blacklight_paint", "cyber_punk", "electric_arc", "firefly", "fluorescent", "glow_stick", "laser_grid", "laser_show", "led_matrix", "magnesium_burn", "neon_glow", "neon_sign", "neon_vegas", "phosphorescent", "plasma_globe", "radioactive", "rave", "scorched", "sodium_lamp", "static", "tesla_coil", "tracer_round", "welding_arc"],
};

const _SPECIALS_MULTI_SPECTRUM = {
    "Multi Swirl": ["mc_christmas", "mc_deep_space", "mc_earth_tone", "mc_fire_storm", "mc_halloween", "mc_miami_vice", "mc_rasta", "mc_tropical", "mc_usa_flag", "mc_vaporwave"],
    "Multi Camo": ["mc_blue_camo", "mc_desert_camo", "mc_neon_camo", "mc_snow_camo", "mc_urban_camo", "mc_woodland_camo"],
    "Multi Marble": ["mc_black_marble", "mc_gold_marble", "mc_green_marble", "mc_red_marble", "mc_white_marble"],
    "Multi Splatter": ["mc_blood_splat", "mc_ink_splat", "mc_neon_splat", "mc_paint_splat"],
};

const _SPECIALS_EFFECTS_VISION = {
    "Effects & Vision": ["acid_trip", "antimatter", "astral", "aurora", "banshee", "black_diamond", "blood_oath", "bone", "catacombs", "cel_shade", "chromatic_aberration", "crt_scanline", "crystal_cave", "cursed", "daguerreotype", "dark_fairy", "dark_ritual", "datamosh", "death_metal", "demon_forge", "double_exposure", "dragon_breath", "dreamscape", "eclipse", "embossed", "enchanted", "ethereal", "film_burn", "fish_eye", "fourth_dimension", "galaxy", "gargoyle", "glitch", "glitch_reality", "graveyard", "grid_walk", "halftone", "hallucination", "haunted", "heat_haze", "hellhound", "holographic_wrap", "infrared", "iron_maiden", "kaleidoscope", "levitation", "lich_king", "long_exposure", "mirage", "multiverse", "nebula_core", "necrotic", "negative", "nightmare", "parallax", "phantom", "phantom_zone", "polarized", "portal", "possessed", "psychedelic", "reaper", "refraction", "rust", "sepia", "shadow_realm", "silk_road", "solarization", "spectral", "tesseract", "thermochromic", "tin_type", "uv_blacklight", "vinyl_record", "void_walker", "voodoo", "wraith", "x_ray"],
};

// Section order and group → section map
const SPECIALS_SECTION_ORDER = ["SHOKKER", "Color Science", "Material World", "Fusion Lab", "Racing Heritage", "Atmosphere", "Signal", "Multi-Spectrum", "Effects & Vision"];
const SPECIALS_SECTIONS = {
    "SHOKKER": ["Shokk Series", "PARADIGM"],
    "Color Science": ["Chameleon", "Prizm", "Color-Shift Adaptive", "Color-Shift Presets", "Color-Shift Duos", "Gradient Directional", "Gradient Vortex"],
    "Material World": ["Atelier — Ultra Detail", "Metals & Forged", "Glass & Surface", "Leather & Texture"],
    "Fusion Lab": ["Ghost Geometry", "Depth Illusion", "Material Gradients", "Directional Grain", "Reactive Panels", "Sparkle Systems", "Multi-Scale Texture", "Weather & Age", "Exotic Physics", "Tri-Zone Materials", "Metallic Halos", "Light Waves", "Fractal Chaos", "Spectral Reactive", "Panel Quilting"],
    "Racing Heritage": ["Racing Heritage"],
    "Atmosphere": ["Atmosphere"],
    "Signal": ["Signal"],
    "Multi-Spectrum": ["Multi Swirl", "Multi Camo", "Multi Marble", "Multi Splatter"],
    "Effects & Vision": ["Effects & Vision"],
};

// Merged flat object (all reimagined groups)
const SPECIAL_GROUPS = Object.assign({},
    _SPECIALS_SHOKKER,
    _SPECIALS_COLOR_SCIENCE,
    _SPECIALS_MATERIAL_WORLD,
    _SPECIALS_FUSION_LAB,
    _SPECIALS_RACING_HERITAGE,
    _SPECIALS_ATMOSPHERE,
    _SPECIALS_SIGNAL,
    _SPECIALS_MULTI_SPECTRUM,
    _SPECIALS_EFFECTS_VISION,
);