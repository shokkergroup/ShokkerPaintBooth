#!/usr/bin/env python3
"""Build new SHOKKER specials taxonomy from backend mono list. Outputs JS _SPECIALS_* and section order."""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "scripts", "mono_ids_backend.txt")) as f:
    ALL_IDS = [line.strip() for line in f if line.strip()]

def take(prefixes, ids=ALL_IDS):
    return sorted([i for i in ids if any(i.startswith(p) for p in prefixes)])

def exact(names, ids=ALL_IDS):
    return [i for i in names if i in ids]

# ---- 1. SHOKKER ----
shokk = take(["shokk_"])
paradigm = exact(["blackbody", "ember", "p_aurora", "pulse", "thin_film", "crystal_lattice", "living_chrome",
    "mercury_pool", "quantum", "singularity", "gravity_well", "phase_shift", "void", "wormhole",
    "glass_armor", "magnetic", "p_static", "stealth"])

# ---- 2. Color Science ----
chameleon = take(["chameleon_"]) + exact(["mystichrome"])
prizm = take(["prizm_"])
cs_adaptive = exact(["cs_cool", "cs_warm", "cs_complementary", "cs_monochrome", "cs_subtle", "cs_rainbow",
    "cs_vivid", "cs_extreme", "cs_triadic", "cs_split", "cs_neon_shift", "cs_ocean_shift", "cs_chrome_shift",
    "cs_earth", "cs_prism_shift"])
cs_presets = exact(["cs_deepocean", "cs_solarflare", "cs_inferno", "cs_nebula", "cs_mystichrome", "cs_supernova",
    "cs_emerald", "cs_candypaint", "cs_oilslick", "cs_rose_gold_shift", "cs_goldrush", "cs_toxic", "cs_darkflame",
    "cs_rosegold", "cs_twilight", "cs_neon_dreams"])
cs_duos = [i for i in take(["cs_"]) if i not in cs_adaptive and i not in cs_presets]
grad_all = take(["grad_"])
grad_directional = [i for i in grad_all if "vortex" not in i]
grad_vortex = [i for i in grad_all if "vortex" in i]

# ---- 3. Material World ----
atelier = take(["atelier_"])
metals = exact(["forged_iron", "cast_iron", "hammered_copper", "brushed_steel_dark", "etched_metal", "bare_aluminum",
    "chrome_oxidized", "heat_blued", "oxidized_metal", "mill_scale", "weathered_metal", "carbon_raw", "weathered_paint",
    "worn_chrome", "phosphate_coat", "raw_weld", "grinding_marks"])
glass_surface = exact(["obsidian_glass", "stained_glass", "venetian_glass", "acid_etched_glass", "concrete", "granite",
    "raw_concrete", "sandstone", "slate_tile", "stucco", "terra_cotta", "volcanic_rock", "brick_wall"])
leather_texture = exact(["aged_leather", "crocodile_leather", "suede", "velvet", "velvet_crush", "linen", "burlap", "cork",
    "parchment", "bark", "petrified_wood"])

# ---- 4. Fusion Lab ----
ghost = take(["ghost_"])
depth = take(["depth_"])
gradient_fusion = take(["gradient_"])
aniso = take(["aniso_"])
reactive = take(["reactive_"])
sparkle = take(["sparkle_"])
multiscale = take(["multiscale_"])
weather = take(["weather_"])
exotic = take(["exotic_"])
trizone = take(["trizone_"])
halo = take(["halo_"])
wave = take(["wave_"])
fractal = take(["fractal_"])
spectral = take(["spectral_"])
quilt = take(["quilt_"])

# ---- 5. Racing Heritage ----
racing_heritage = exact([
    "barn_find", "dawn_patrol", "drafting", "drive_in", "hot_rod_flames", "classic_racing", "nascar_heritage",
    "nostalgia_drag", "old_school", "race_worn", "burnout_zone", "chicane_blur", "cool_down", "drag_chute",
    "last_lap", "pace_lap", "photo_finish", "pit_stop", "pole_position", "victory_burnout", "green_flag",
    "black_flag", "white_flag", "night_race", "rain_race", "under_lights", "muscle_car_stripe", "patina_truck",
    "faded_glory", "daily_driver", "beat_up_truck", "diner_chrome", "jukebox", "pin_up", "slipstream", "tunnel_run",
    "worn_asphalt", "grindhouse", "simulation", "time_warp", "zeppelin", "woodie", "woodie_wagon", "flag_wave",
    "red_mist", "wet_gloss", "liquid_gold", "moonshine", "art_deco_gold", "mother_of_pearl", "ruby", "sapphire",
    "alexandrite", "champagne_toast"
])

# ---- 6. Atmosphere (environmental only; weather_* fusion is in Fusion Lab) ----
atmosphere = exact([
    "acid_rain", "black_ice", "blizzard", "desert_mirage", "dew_drop", "dust_storm", "ember_glow", "fog_bank",
    "frost_bite", "frozen_lake", "hail_damage", "heat_wave", "hurricane", "lightning_strike", "liquid_metal",
    "magma_flow", "meteor_shower", "monsoon", "ocean_floor", "oil_slick", "permafrost", "solar_wind", "tidal_wave",
    "tornado_alley", "volcanic_glass"
])

# ---- 7. Signal ----
signal = exact([
    "aurora_glow", "bioluminescent_wave", "blacklight_paint", "cyber_punk", "electric_arc", "firefly", "fluorescent",
    "glow_stick", "laser_grid", "laser_show", "led_matrix", "magnesium_burn", "neon_glow", "neon_sign", "neon_vegas",
    "phosphorescent", "plasma_globe", "radioactive", "rave", "scorched", "sodium_lamp", "static", "tesla_coil",
    "tracer_round", "welding_arc"
])

# ---- 8. Multi-Spectrum ----
mc_all = take(["mc_"])
mc_swirl = [i for i in mc_all if i in ["mc_usa_flag", "mc_rasta", "mc_halloween", "mc_christmas", "mc_miami_vice",
    "mc_fire_storm", "mc_deep_space", "mc_tropical", "mc_vaporwave", "mc_earth_tone"]]
mc_camo = sorted([i for i in mc_all if "camo" in i])
mc_marble = sorted([i for i in mc_all if "marble" in i])
mc_splatter = sorted([i for i in mc_all if "splat" in i])

# ---- 9. Effects & Vision (everything not yet placed) ----
assigned = set()
for g in [shokk, paradigm, chameleon, prizm, cs_adaptive, cs_presets, cs_duos, grad_directional, grad_vortex,
          atelier, metals, glass_surface, leather_texture, ghost, depth, gradient_fusion, aniso, reactive, sparkle,
          multiscale, weather, exotic, trizone, halo, wave, fractal, spectral, quilt, racing_heritage, atmosphere,
          signal, mc_swirl, mc_camo, mc_marble, mc_splatter]:
    assigned.update(g)
effects_vision = sorted([i for i in ALL_IDS if i not in assigned])

# ---- Output JS ----
sections_order = [
    "SHOKKER",
    "Color Science",
    "Material World",
    "Fusion Lab",
    "Racing Heritage",
    "Atmosphere",
    "Signal",
    "Multi-Spectrum",
    "Effects & Vision",
]

groups = {
    "SHOKKER": {
        "Shokk Series": shokk,
        "PARADIGM": paradigm,
    },
    "Color Science": {
        "Chameleon": chameleon,
        "Prizm": prizm,
        "Color-Shift Adaptive": cs_adaptive,
        "Color-Shift Presets": cs_presets,
        "Color-Shift Duos": cs_duos,
        "Gradient Directional": grad_directional,
        "Gradient Vortex": grad_vortex,
    },
    "Material World": {
        "Atelier — Ultra Detail": atelier,
        "Metals & Forged": metals,
        "Glass & Surface": glass_surface,
        "Leather & Texture": leather_texture,
    },
    "Fusion Lab": {
        "Ghost Geometry": ghost,
        "Depth Illusion": depth,
        "Material Gradients": gradient_fusion,
        "Directional Grain": aniso,
        "Reactive Panels": reactive,
        "Sparkle Systems": sparkle,
        "Multi-Scale Texture": multiscale,
        "Weather & Age": weather,
        "Exotic Physics": exotic,
        "Tri-Zone Materials": trizone,
        "Metallic Halos": halo,
        "Light Waves": wave,
        "Fractal Chaos": fractal,
        "Spectral Reactive": spectral,
        "Panel Quilting": quilt,
    },
    "Racing Heritage": {
        "Racing Heritage": racing_heritage,
    },
    "Atmosphere": {
        "Atmosphere": atmosphere,
    },
    "Signal": {
        "Signal": signal,
    },
    "Multi-Spectrum": {
        "Multi Swirl": mc_swirl,
        "Multi Camo": mc_camo,
        "Multi Marble": mc_marble,
        "Multi Splatter": mc_splatter,
    },
    "Effects & Vision": {
        "Effects & Vision": effects_vision,
    },
}

# Flatten to _SPECIALS_* style
lines = []
lines.append("// =============================================================================")
lines.append("// SHOKKER — Reimagined Monolithic Taxonomy (628 finishes)")
lines.append("// Single source: only backend-registered IDs. No filler. The benchmark.")
lines.append("// =============================================================================\n")

for section in sections_order:
    sec_obj = groups[section]
    var = "_SPECIALS_" + section.upper().replace(" ", "_").replace("-", "_").replace("&", "")
    if section == "Effects & Vision":
        var = "_SPECIALS_EFFECTS_VISION"
    lines.append(f"const {var} = {{")
    for group_name, id_list in sec_obj.items():
        ids_js = ", ".join(f'"{x}"' for x in id_list)
        lines.append(f'    "{group_name}": [{ids_js}],')
    lines.append("};\n")

lines.append("// Section order and group → section map")
lines.append('const SPECIALS_SECTION_ORDER = ' + str(sections_order).replace("'", '"') + ";")
lines.append("const SPECIALS_SECTIONS = {")
for section in sections_order:
    group_names = list(groups[section].keys())
    lines.append(f'    "{section}": {str(group_names).replace(chr(39), chr(34))},')
lines.append("};")

# Merge SPECIAL_GROUPS
lines.append("\n// Merged flat object (all reimagined groups)")
lines.append("const SPECIAL_GROUPS = Object.assign({},")
for section in sections_order:
    var = "_SPECIALS_" + section.upper().replace(" ", "_").replace("-", "_").replace("&", "")
    if section == "Effects & Vision":
        var = "_SPECIALS_EFFECTS_VISION"
    lines.append(f"    {var},")
lines.append(");")

out = "\n".join(lines)
# Fix trailing comma in object (last entry in each object should not have comma for valid JS)
# Actually we want trailing commas for easier diff - modern JS allows them
out_path = os.path.join(ROOT, "scripts", "special_groups_output.js")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(out)
print("Wrote", out_path)

# Verify count
total = sum(len(v) for sec in groups.values() for v in sec.values())
assert total == len(ALL_IDS), f"Mismatch: {total} vs {len(ALL_IDS)}"
print("Total IDs in groups:", total)
