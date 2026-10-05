"""Spec Sculpt presets — curated map of clean names to REAL SPB registry finishes.

2026-06-01 PIVOT: the procedural ``material_profiles`` approach was scrapped — it
produced low-diversity specs plus a grid-flash artifact. Instead each preset now
points at one (or a small blend) of the *real* registered SPB finish spec functions
(the same diverse, proven specs the main Paint Booth uses, resolved via
``engine.compose._resolve_finish_spec``). Spec Sculpt renders them through the
catalog path and SKIPS the Viva pre/post pass (that pass is what stamped the grid
flash on every preset). See ``engine/spec_sculpt/generate.py``.

Each preset: ``id`` (clean spec-sculpt slug), ``label``, ``category``, ``description``,
``tags``, and ``catalog`` = ``[(real_finish_id, weight), ...]``. The owner audits these
in ``spec-sculpt-audit.html`` (KEEP / REBUILD / RENAME / BUILD NEW); REBUILD just means
swap to a different real finish id.
"""
from __future__ import annotations

MAX_PRESET_STACK = 5
MAX_CATALOG_PER_STACK = 5


def _p(pid, label, category, fids, desc, tags):
    """Preset constructor. ``fids`` = real finish id string OR list of (id, weight)."""
    if isinstance(fids, str):
        catalog = [(fids, 1.0)]
    else:
        catalog = [(str(f[0]), float(f[1])) if isinstance(f, (list, tuple)) else (str(f), 1.0) for f in fids]
    return {
        "id": pid,
        "label": label,
        "description": desc,
        "category": category,
        "tags": list(tags),
        "catalog": catalog,
    }


# ============================================================================
# Curated best-of (~78) real finishes, picked by rendering family survey sheets
# (scripts/spb_curate_finishes.py) and keeping the most diverse / distinct.
# ============================================================================
SPEC_SCULPT_PRESETS: list[dict[str, object]] = [
    # ---- Chrome & metal -------------------------------------------------
    _p("mirror_chrome", "Mirror Chrome", "Chrome & metal", "enh_chrome",
       "Clean bright mirror metal — high reflect, low roughness.", ["chrome", "mirror"]),
    _p("mercury_flow", "Mercury Flow", "Chrome & metal", "mercury_pool",
       "Liquid mercury — swirling poured-metal chrome.", ["mercury", "liquid", "swirl"]),
    _p("radial_machined", "Radial Machined", "Chrome & metal", "aniso_radial_metallic",
       "Sunburst machined metal — radial tool-mark sheen.", ["machined", "radial", "aniso"]),
    _p("brushed_titanium", "Brushed Titanium", "Chrome & metal", "brushed_titanium",
       "Directional brushed titanium bands.", ["brushed", "titanium", "directional"]),
    _p("titanium_vortex", "Titanium Vortex", "Chrome & metal", "grad_titanium_vortex",
       "Spun titanium vortex — spiral flow.", ["titanium", "vortex", "spiral"]),
    _p("obsidian_mirror", "Obsidian Mirror", "Chrome & metal", "gradient_obsidian_mirror",
       "Dark glass mirror with a hot central bloom.", ["dark", "mirror", "obsidian"]),
    _p("midnight_chrome", "Midnight Chrome", "Chrome & metal", "cx_midnight_chrome",
       "Deep chrome with green-shift swirl.", ["chrome", "dark", "shift"]),
    _p("chrome_chainmail", "Chrome Chainmail", "Chrome & metal", "pp_chrome_oval_chain",
       "Interlocked oval chain-link chrome.", ["chain", "mail", "pattern"]),
    _p("kaido_chrome", "Kaido Chrome Bloom", "Chrome & metal", "rs_kaido_chrome_bloom",
       "Streaked bloom chrome, kaido-racer flavor.", ["chrome", "streak", "bloom"]),
    _p("weathered_steel", "Weathered Steel", "Chrome & metal", "f_weathering_steel",
       "Flat weathered steel — low-sheen industrial metal.", ["steel", "matte", "industrial"]),
    _p("diamond_chrome", "Diamond Chrome", "Chrome & metal", "halo_diamond_chrome",
       "Fine diamond-cut chrome mesh.", ["diamond", "chrome", "cut"]),
    _p("mystic_chrome", "Mystic Chrome", "Chrome & metal", "cs_mystichrome",
       "Dark mystic chrome with color-shift sparkle.", ["chrome", "mystic", "shift"]),
    _p("phantom_mirror", "Phantom Mirror", "Chrome & metal", "exotic_phantom_mirror",
       "Crystalline phantom mirror facets.", ["mirror", "crystal", "phantom"]),

    # ---- Carbon & matte -------------------------------------------------
    _p("satin_weave", "Satin Weave", "Carbon & matte", "enh_clear_satin",
       "Soft satin with a fine diagonal weave.", ["satin", "weave"]),
    _p("forged_carbon", "Forged Carbon", "Carbon & matte", "forged_carbon_vis",
       "Marbled forged-carbon chunk pattern.", ["carbon", "forged", "marble"]),
    _p("hybrid_weave", "Hybrid Weave", "Carbon & matte", "hybrid_weave",
       "Two-tone hybrid technical weave.", ["weave", "tech"]),
    _p("acid_carbon", "Acid Carbon Mesh", "Carbon & matte", "pp_acid_carbon_mesh",
       "Acid-etched carbon mesh.", ["carbon", "mesh", "acid"]),
    _p("checker_carbon", "Checker Carbon", "Carbon & matte", "pp_pink_checker_carbon",
       "Bold checkered carbon weave.", ["carbon", "checker"]),
    _p("weather_volcanic_ash", "Weather Volcanic Ash", "Carbon & matte", "weather_volcanic_ash",
       "Weather Volcanic Ash - matte / weave pick.", ["weather", "volcanic", "ash"]),
    _p("carbon_fiber", "Carbon Fiber", "Carbon & matte", "enh_carbon_fiber",
       "Classic 2x2 carbon-fiber weave.", ["carbon", "fiber", "weave"]),
    _p("ceramic_matte", "Ceramic Matte", "Carbon & matte", "ceramic_matte",
       "Even ceramic matte with fine tooth.", ["matte", "ceramic"]),
    _p("matte_silk", "Matte Silk", "Carbon & matte", "multiscale_matte_silk",
       "Deep silky matte — soft uniform field.", ["matte", "silk", "deep"]),
    _p("gunmetal_satin", "Gunmetal Satin", "Carbon & matte", "gunmetal_satin",
       "Dark satin gunmetal.", ["gunmetal", "satin", "dark"]),
    _p("frozen_matte", "Frozen Matte", "Carbon & matte", "frozen_matte",
       "Cold flat frozen matte.", ["matte", "frozen", "flat"]),
    _p("dark_matter", "Dark Matter", "Carbon & matte", "dark_matter",
       "Void-dark speckled matte.", ["matte", "void", "speckle"]),

    # ---- Candy & pearl --------------------------------------------------
    _p("candy_poison", "Candy Poison", "Candy & pearl", "cc_candy_poison",
       "Striped poison candy — diagonal color bands.", ["candy", "stripe", "bold"]),
    _p("cotton_candy", "Cotton Candy", "Candy & pearl", "cx_cotton_candy",
       "Soft two-tone candy stripes.", ["candy", "soft", "stripe"]),
    _p("inverted_candy", "Inverted Candy", "Candy & pearl", "exotic_inverted_candy",
       "Wavy inverted candy flow.", ["candy", "wave", "exotic"]),
    _p("pearl_chaser", "Pearl Chaser", "Candy & pearl", "fd_pearl_chaser",
       "Speckled chasing pearl shimmer.", ["pearl", "shimmer"]),
    _p("ghost_scales", "Ghost Scales", "Candy & pearl", "ghost_scales",
       "Reptile-scale ghost pearl.", ["pearl", "scales", "ghost"]),
    _p("ghost_waves", "Ghost Waves", "Candy & pearl", "ghost_waves",
       "Rolling ghost-pearl waves.", ["pearl", "wave", "ghost"]),
    _p("anodized_gloss", "Anodized Gloss", "Candy & pearl", "gradient_anodized_gloss",
       "Anodized diagonal gloss with a hot streak.", ["anodized", "gloss"]),
    _p("circle_pearl", "Circle Pearl", "Candy & pearl", "halo_circle_pearl",
       "Halo circle pearl dot field.", ["pearl", "dots", "halo"]),
    _p("candy_tiles", "Candy Tiles", "Candy & pearl", "quilt_candy_tiles",
       "Stained-glass candy tile mosaic.", ["candy", "tiles", "mosaic"]),
    _p("ghost_metal", "Ghost Metal", "Candy & pearl", "reactive_ghost_metal",
       "Plaid ghost-metal reactive pearl.", ["pearl", "plaid", "reactive"]),
    _p("mercury_candy", "Mercury Candy", "Candy & pearl", "trizone_mercury_obsidian_candy",
       "Mercury-obsidian-candy tri-blend swirl.", ["candy", "mercury", "swirl"]),
    _p("candy_flow", "Candy Flow", "Candy & pearl", "wave_candy_flow",
       "Flowing wave candy.", ["candy", "wave", "flow"]),
    _p("anodized", "Anodized", "Candy & pearl", "anodized",
       "Clean anodized color-metal gloss.", ["anodized", "gloss", "clean"]),
    _p("ghost_camo", "Ghost Camo", "Candy & pearl", "ghost_camo",
       "Subtle ghost-camo checker pearl.", ["pearl", "camo", "checker"]),

    # ---- Flake & sparkle ------------------------------------------------
    _p("chaos_flake", "Chaos Flake", "Flake & sparkle", "quilt_random_chaos",
       "Multicolor random flake mosaic.", ["flake", "mosaic", "chaos"]),
    _p("hex_flake", "Hex Flake", "Flake & sparkle", "quilt_hex_variety",
       "Varied hex-cell flake tiles.", ["flake", "hex", "tiles"]),
    _p("organic_flake", "Organic Flake Cells", "Flake & sparkle", "quilt_organic_cells",
       "Organic cell flake clusters.", ["flake", "organic", "cell"]),
    _p("chrome_mosaic", "Chrome Mosaic", "Flake & sparkle", "quilt_chrome_mosaic",
       "Chrome mosaic shard flake.", ["flake", "chrome", "mosaic"]),
    _p("sparkle_burst", "Sparkle Burst", "Flake & sparkle", "anime_sparkle_burst",
       "Voronoi burst sparkle.", ["sparkle", "burst"]),
    _p("akane_flake", "Akane Flake Fog", "Flake & sparkle", "rs_akane_flake_fog",
       "Foggy diagonal akane flake.", ["flake", "fog", "diagonal"]),
    _p("galaxy_sparkle", "Galaxy Sparkle", "Flake & sparkle", "sparkle_galaxy",
       "Galaxy sparkle with a drifting streak.", ["sparkle", "galaxy"]),
    _p("firefly_sparkle", "Firefly Sparkle", "Flake & sparkle", "sparkle_firefly",
       "Sparse firefly pinpoints.", ["sparkle", "sparse", "firefly"]),
    _p("metal_flake", "Metal Flake", "Flake & sparkle", "original_metal_flake",
       "Classic fine OEM metal flake.", ["flake", "fine", "oem"]),
    _p("ice_flake", "Ice Flake", "Flake & sparkle", "blue_ice_flake",
       "Cool blue ice flake.", ["flake", "ice", "cool"]),
    _p("gradient_tiles", "Gradient Tiles", "Flake & sparkle", "quilt_gradient_tiles",
       "Gradient voronoi tile flake.", ["flake", "tiles", "gradient"]),
    _p("duo_tiles", "Duo Tiles", "Flake & sparkle", "quilt_alternating_duo",
       "Alternating two-tone tile flake.", ["flake", "tiles", "duo"]),

    # ---- Holo & shift ---------------------------------------------------
    _p("arctic_chameleon", "Arctic Chameleon", "Holo & shift", "chameleon_arctic",
       "Radial arctic chameleon sunburst.", ["chameleon", "radial", "flip"]),
    _p("emerald_chameleon", "Emerald Chameleon", "Holo & shift", "chameleon_emerald",
       "Fine emerald chameleon mesh.", ["chameleon", "emerald", "flip"]),
    _p("venom_chameleon", "Venom Chameleon", "Holo & shift", "chameleon_venom",
       "Diagonal venom chameleon flip.", ["chameleon", "venom", "flip"]),
    _p("galaxy_chameleon", "Galaxy Chameleon", "Holo & shift", "chameleon_galaxy",
       "Galaxy-toned chameleon shift.", ["chameleon", "galaxy", "flip"]),
    _p("obsidian_chameleon", "Obsidian Chameleon", "Holo & shift", "chameleon_obsidian",
       "Dark obsidian chameleon mesh.", ["chameleon", "obsidian", "flip"]),
    _p("hyperflip_blue_copper", "Hyperflip Blue/Copper", "Holo & shift", "cx_hyperflip_electric_blue_copper",
       "Electric blue-to-copper hyperflip diffraction.", ["flip", "diffraction", "blue"]),
    _p("prism_shatter", "Prism Shatter", "Holo & shift", "cx_prism_shatter",
       "Shattered prism facets.", ["prism", "shatter"]),
    _p("holographic", "Holographic", "Holo & shift", "holographic_wrap",
       "Diagonal holographic diffraction.", ["holo", "diffraction", "rainbow"]),
    _p("spectral_rings", "Spectral Rings", "Holo & shift", "spectral_dark_light",
       "Concentric spectral diffraction rings.", ["spectral", "rings"]),
    _p("spectral_mono", "Spectral Mono", "Holo & shift", "spectral_mono_chrome",
       "Mono spectral line diffraction.", ["spectral", "mono", "lines"]),
    _p("rainbow_metal", "Rainbow Metal", "Holo & shift", "spectral_rainbow_metal",
       "Wavy rainbow-metal spectral flow.", ["spectral", "rainbow"]),
    _p("oil_slick_macro", "Oil Slick Macro", "Holo & shift", "spectrum_oilfilm_rain",
       "Big-cell oil-slick iridescence.", ["oil", "iridescent", "macro"]),
    _p("oil_slick_wave", "Oil Slick Wave", "Holo & shift", "spectrum_rainbow_river",
       "Wavy oil-slick iridescence.", ["oil", "iridescent", "wave"]),
    _p("spectral_edge", "Spectral Edge", "Holo & shift", "efx_spectral_edge",
       "Edge-lit spectral shimmer.", ["spectral", "edge"]),

    # ---- Exotic & glow --------------------------------------------------
    _p("neon_outline", "Neon Outline", "Exotic & glow", "anime_neon_outline",
       "Neon outline mesh glow.", ["neon", "outline", "glow"]),
    _p("aurora_chameleon", "Aurora Chameleon", "Exotic & glow", "chameleon_aurora",
       "Vertical aurora chameleon ribbons.", ["aurora", "chameleon", "ribbon"]),
    _p("copper_flame", "Copper Flame", "Exotic & glow", "grad_copper_flame",
       "Flowing copper flame waves.", ["copper", "flame", "warm"]),
    _p("fire_vortex", "Fire Vortex", "Exotic & glow", "grad_fire_vortex",
       "Spun fire vortex.", ["fire", "vortex", "warm"]),
    _p("neon_equalizer", "Neon Equalizer", "Exotic & glow", "living_neon_equalizer",
       "Neon equalizer bars.", ["neon", "bars", "glow"]),
    _p("molten_metal", "Molten Metal", "Exotic & glow", "molten_metal",
       "Glowing molten metal flow.", ["molten", "hot", "flow"]),
    _p("marble_pearl", "Marble Pearl", "Exotic & glow", "pp_marble_flow_pearl",
       "Flowing marble pearl veins.", ["marble", "pearl", "vein"]),
    _p("prizm_neon", "Prizm Neon", "Exotic & glow", "prizm_neon",
       "Prismatic neon shift.", ["neon", "prism", "glow"]),
    _p("aurora_wave", "Aurora Wave", "Exotic & glow", "spectrum_borealis_ice",
       "Aurora ribbon waves.", ["aurora", "wave", "ribbon"]),
    _p("gunmetal_gold", "Gunmetal Gold", "Exotic & glow", "cs_gunmetal_gold",
       "Gunmetal-to-gold shift.", ["gunmetal", "gold", "shift"]),
    _p("midnight_gold", "Midnight Gold", "Exotic & glow", "grad_midnight_gold",
       "Deep midnight-gold gradient.", ["gold", "dark", "warm"]),
    _p("satin_gold", "Satin Gold", "Exotic & glow", "satin_gold",
       "Warm satin gold sheen.", ["gold", "satin", "warm"]),
    _p("rose_gold", "Rose Gold", "Exotic & glow", "grad_rose_gold_h",
       "Soft rose-gold gradient.", ["gold", "rose", "warm"]),

    # ==== Auto-expanded batch (diverse spec-index picks; audit me) ====
    # ---- Chrome & metal ----
    _p("gradient_chrome_matte", "Gradient Chrome Matte", "Chrome & metal", "gradient_chrome_matte",
       "Gradient Chrome Matte - reflective metal pick.", ["gradient", "chrome", "matte"]),
    _p("aniso_wave_titanium", "Aniso Wave Titanium", "Chrome & metal", "aniso_wave_titanium",
       "Aniso Wave Titanium - reflective metal pick.", ["aniso", "wave", "titanium"]),
    _p("electric_arc", "Electric Arc", "Chrome & metal", "electric_arc",
       "Electric Arc - reflective metal pick.", ["electric", "arc"]),
    _p("kinpaku_blaze", "Kinpaku Blaze", "Chrome & metal", "rs_kinpaku_blaze",
       "Kinpaku Blaze - reflective metal pick.", ["kinpaku", "blaze", "rs"]),
    _p("brushed_metal_fine", "Brushed Metal Fine", "Chrome & metal", "brushed_metal_fine",
       "Brushed Metal Fine - reflective metal pick.", ["brushed", "metal", "fine"]),
    _p("void", "Void", "Chrome & metal", "void",
       "Void - reflective metal pick.", ["void"]),
    _p("gradient_metallic_satin", "Gradient Metallic Satin", "Chrome & metal", "gradient_metallic_satin",
       "Gradient Metallic Satin - reflective metal pick.", ["gradient", "metallic", "satin"]),
    _p("gradient_pearl_chrome", "Gradient Pearl Chrome", "Chrome & metal", "gradient_pearl_chrome",
       "Gradient Pearl Chrome - reflective metal pick.", ["gradient", "pearl", "chrome"]),
    # ---- Carbon & matte ----
    _p("trizone_stealth_spectra_frozen", "Trizone Stealth Spectra Frozen", "Carbon & matte", "trizone_stealth_spectra_frozen",
       "Trizone Stealth Spectra Frozen - matte / weave pick.", ["trizone", "stealth", "spectra"]),
    _p("weather_hood_bake", "Weather Hood Bake", "Carbon & matte", "weather_hood_bake",
       "Weather Hood Bake - matte / weave pick.", ["weather", "hood", "bake"]),
    _p("weather_sun_fade", "Weather Sun Fade", "Carbon & matte", "weather_sun_fade",
       "Weather Sun Fade - matte / weave pick.", ["weather", "sun", "fade"]),
    _p("weather_ocean_mist", "Weather Ocean Mist", "Carbon & matte", "weather_ocean_mist",
       "Weather Ocean Mist - matte / weave pick.", ["weather", "ocean", "mist"]),
    _p("weathered_paint", "Weathered Paint", "Carbon & matte", "weathered_paint",
       "Weathered Paint - matte / weave pick.", ["weathered", "paint"]),
    _p("reactive_matte_shine", "Reactive Matte Shine", "Carbon & matte", "reactive_matte_shine",
       "Reactive Matte Shine - matte / weave pick.", ["reactive", "matte", "shine"]),
    _p("weather_ice_storm", "Weather Ice Storm", "Carbon & matte", "weather_ice_storm",
       "Weather Ice Storm - matte / weave pick.", ["weather", "ice", "storm"]),
    _p("ember", "Ember", "Carbon & matte", "ember",
       "Ember - matte / weave pick.", ["ember"]),
    # ---- Candy & pearl ----
    _p("gradient_candy_frozen", "Gradient Candy Frozen", "Candy & pearl", "gradient_candy_frozen",
       "Gradient Candy Frozen - candy / pearl gloss pick.", ["gradient", "candy", "frozen"]),
    _p("gradient_candy_matte", "Gradient Candy Matte", "Candy & pearl", "gradient_candy_matte",
       "Gradient Candy Matte - candy / pearl gloss pick.", ["gradient", "candy", "matte"]),
    _p("maguey_pearl", "Maguey Pearl", "Candy & pearl", "vm_maguey_pearl",
       "Maguey Pearl - candy / pearl gloss pick.", ["maguey", "pearl", "vm"]),
    _p("trizone_anodized_candy_silk", "Trizone Anodized Candy Silk", "Candy & pearl", "trizone_anodized_candy_silk",
       "Trizone Anodized Candy Silk - candy / pearl gloss pick.", ["trizone", "anodized", "candy"]),
    _p("glass_armor", "Glass Armor", "Candy & pearl", "glass_armor",
       "Glass Armor - candy / pearl gloss pick.", ["glass", "armor"]),
    _p("aniso_diagonal_candy", "Aniso Diagonal Candy", "Candy & pearl", "aniso_diagonal_candy",
       "Aniso Diagonal Candy - candy / pearl gloss pick.", ["aniso", "diagonal", "candy"]),
    _p("windsor_guard_gloss", "Windsor Guard Gloss", "Candy & pearl", "uj_windsor_guard_gloss",
       "Windsor Guard Gloss - candy / pearl gloss pick.", ["windsor", "guard", "gloss", "uj"]),
    _p("candy", "Candy", "Candy & pearl", "f_candy",
       "Candy - candy / pearl gloss pick.", ["candy", "f"]),
    # ---- Flake & sparkle ----
    _p("spectrum_reptile_macro", "Spectrum Reptile Macro", "Flake & sparkle", "spectrum_beetle_elytra",
       "Spectrum Reptile Macro - flake / sparkle pick.", ["spectrum", "reptile", "macro"]),
    _p("sparkle_diamond_dust", "Sparkle Diamond Dust", "Flake & sparkle", "sparkle_diamond_dust",
       "Sparkle Diamond Dust - flake / sparkle pick.", ["sparkle", "diamond", "dust"]),
    _p("spectrum_reptile_micro", "Spectrum Reptile Micro", "Flake & sparkle", "spectrum_peacock_eye",
       "Spectrum Reptile Micro - flake / sparkle pick.", ["spectrum", "reptile", "micro"]),
    _p("goodwood_heritage_flake", "Goodwood Heritage Flake", "Flake & sparkle", "uj_goodwood_heritage_flake",
       "Goodwood Heritage Flake - flake / sparkle pick.", ["goodwood", "heritage", "flake", "uj"]),
    _p("spectrum_reptile_wave", "Spectrum Reptile Wave", "Flake & sparkle", "spectrum_nacre_tide",
       "Spectrum Reptile Wave - flake / sparkle pick.", ["spectrum", "reptile", "wave"]),
    _p("sparkle_lightning_bug", "Sparkle Lightning Bug", "Flake & sparkle", "sparkle_lightning_bug",
       "Sparkle Lightning Bug - flake / sparkle pick.", ["sparkle", "lightning", "bug"]),
    _p("spectrum_reptile_classic", "Spectrum Reptile Classic", "Flake & sparkle", "spectrum_jewel_box",
       "Spectrum Reptile Classic - flake / sparkle pick.", ["spectrum", "reptile", "classic"]),
    _p("sparkle_constellation", "Sparkle Constellation", "Flake & sparkle", "sparkle_constellation",
       "Sparkle Constellation - flake / sparkle pick.", ["sparkle", "constellation"]),
    # ---- Holo & shift ----
    _p("hypercane", "Hypercane", "Holo & shift", "p_hypercane",
       "Hypercane - color-shift / holo pick.", ["hypercane", "p"]),
    _p("black_ice", "Black Ice", "Holo & shift", "cx_black_ice",
       "Black Ice - color-shift / holo pick.", ["black", "ice", "cx"]),
    _p("spectrum_holographic_macro", "Spectrum Holographic Macro", "Holo & shift", "spectrum_grating_quilt",
       "Spectrum Holographic Macro - color-shift / holo pick.", ["spectrum", "holographic", "macro"]),
    _p("iridescent", "Iridescent", "Holo & shift", "iridescent",
       "Iridescent - color-shift / holo pick.", ["iridescent"]),
    _p("spectrum_mirage_micro", "Spectrum Mirage Micro", "Holo & shift", "spectrum_moire_silk",
       "Spectrum Mirage Micro - color-shift / holo pick.", ["spectrum", "mirage", "micro"]),
    _p("spectrum_vapor_macro", "Spectrum Vapor Macro", "Holo & shift", "spectrum_smoke_chroma",
       "Spectrum Vapor Macro - color-shift / holo pick.", ["spectrum", "vapor", "macro"]),
    _p("hyperflip_crimson_prism", "Hyperflip Crimson Prism", "Holo & shift", "cx_hyperflip_crimson_prism",
       "Hyperflip Crimson Prism - color-shift / holo pick.", ["hyperflip", "crimson", "prism", "cx"]),
    _p("rose_chrome", "Rose Chrome", "Holo & shift", "cx_rose_chrome",
       "Rose Chrome - color-shift / holo pick.", ["rose", "chrome", "cx"]),
    # ---- Exotic & glow ----
    _p("living_electric_current", "Living Electric Current", "Exotic & glow", "living_electric_current",
       "Living Electric Current - exotic / glow pick.", ["living", "electric", "current"]),
    _p("gradient_spectraflame_void", "Gradient Spectraflame Void", "Exotic & glow", "gradient_spectraflame_void",
       "Gradient Spectraflame Void - exotic / glow pick.", ["gradient", "spectraflame", "void"]),
    _p("blackbody", "Blackbody", "Exotic & glow", "blackbody",
       "Blackbody - exotic / glow pick.", ["blackbody"]),
    _p("wormhole", "Wormhole", "Exotic & glow", "wormhole",
       "Wormhole - exotic / glow pick.", ["wormhole"]),
    _p("kurogane_rain", "Kurogane Rain", "Exotic & glow", "rs_kurogane_rain",
       "Kurogane Rain - exotic / glow pick.", ["kurogane", "rain", "rs"]),
    _p("tesla_coil", "Tesla Coil", "Exotic & glow", "tesla_coil",
       "Tesla Coil - exotic / glow pick.", ["tesla", "coil"]),
    _p("topographic_dense", "Topographic Dense", "Exotic & glow", "topographic_dense",
       "Topographic Dense - exotic / glow pick.", ["topographic", "dense"]),
]

VALID_SPEC_SCULPT_PRESET_IDS = frozenset(str(p["id"]) for p in SPEC_SCULPT_PRESETS)

PRESET_CATALOG_BY_ID: dict[str, list[tuple[str, float]]] = {
    str(p["id"]): list(p["catalog"]) for p in SPEC_SCULPT_PRESETS  # type: ignore[arg-type]
}

# Owner audit (2026-06-01): these finishes read "pattern too big" on a car-sized canvas.
# Render ONLY these finer via seamless mirror-tiling (tile=2) — the other ~100 keeps stay
# whole-frame (tile=1) exactly as rated. See engine/spec_sculpt/catalog_blend.py.
PRESET_TILE_OVERRIDE: dict[str, float] = {
    pid: 2.0
    for pid in (
        "candy_tiles", "glass_armor", "dark_matter", "weathered_paint", "weather_ice_storm",
        "electric_arc", "void", "aurora_wave", "gradient_spectraflame_void", "tesla_coil",
        "hex_flake", "organic_flake", "chrome_mosaic", "gradient_tiles",
        "spectrum_reptile_macro", "spectrum_reptile_wave", "spectrum_reptile_classic",
        "oil_slick_macro", "oil_slick_wave", "spectral_edge", "hypercane", "spectrum_vapor_macro",
    )
}

#: Per-preset pattern-fineness factor (1.0 = whole-frame; >1 = finer mirror-tiled).
PRESET_TILE_BY_ID: dict[str, float] = {
    str(p["id"]): float(PRESET_TILE_OVERRIDE.get(str(p["id"]), 1.0)) for p in SPEC_SCULPT_PRESETS
}


def normalize_preset_stack(raw: object, *, max_layers: int = MAX_PRESET_STACK) -> list[tuple[str, float]]:
    """Parse API payload into sorted list of (preset_id, weight). Drops unknown ids."""
    if raw is None:
        return []
    items: list[tuple[str, float]] = []
    if isinstance(raw, list):
        for entry in raw[:max_layers]:
            if isinstance(entry, (tuple, list)) and len(entry) >= 2:
                pid = str(entry[0]).strip().lower()
                try:
                    w = float(entry[1])
                except (TypeError, ValueError):
                    continue
                if pid not in VALID_SPEC_SCULPT_PRESET_IDS or w <= 0:
                    continue
                items.append((pid, w))
            elif isinstance(entry, dict):
                pid = str(entry.get("id") or entry.get("preset") or "").strip().lower()
                try:
                    w = float(entry.get("weight", 1.0))
                except (TypeError, ValueError):
                    w = 1.0
                if pid not in VALID_SPEC_SCULPT_PRESET_IDS or w <= 0:
                    continue
                items.append((pid, w))
    if not items:
        return []
    tw = sum(w for _, w in items) or 1.0
    return [(pid, w / tw) for pid, w in items]


def preset_stack_to_catalog(stack: list[tuple[str, float]], *,
                            max_layers: int = MAX_CATALOG_PER_STACK) -> list[tuple[str, float]]:
    """Flatten a preset stack into a real-finish catalog stack ``[(finish_id, weight)]``.

    Each preset contributes its mapped finish(es), weighted by the preset's stack weight.
    Weights are summed per finish, then the top ``max_layers`` are kept and renormalized.
    """
    agg: dict[str, float] = {}
    for pid, w in stack:
        for fid, cw in PRESET_CATALOG_BY_ID.get(pid, []):
            agg[fid] = agg.get(fid, 0.0) + float(w) * float(cw)
    if not agg:
        return []
    ordered = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:max_layers]
    tw = sum(w for _, w in ordered) or 1.0
    return [(fid, w / tw) for fid, w in ordered]


# ---------------------------------------------------------------------------
# Back-compat shims (older imports / tests). The procedural mrc + chromatic
# levers are retired; these keep imports working without affecting rendering.
# ---------------------------------------------------------------------------
PRESET_MRC_TUNING: dict[str, tuple[float, float, float]] = {}


def preset_layer_chromatic(preset_id: str, global_chromatic: bool) -> bool:
    return bool(global_chromatic)


def apply_preset_layer_tuning(layer, preset_id):
    return layer


# ── Overnight ADDITIVE preset expansion (2026-06-18) ────────────────────────────────────
# Appends curated PROCEDURAL FRACTURED finishes (now resolvable via the spec-sculpt
# merged-registry fix) and rebuilds the derived lookups. Guarded so a failure can NEVER
# break preset loading. verify_resolve=False: the batch is pre-verified, and skipping the
# guard avoids dropping presets if this module is imported before expansions finish loading.
try:
    from engine.spec_sculpt import presets_overnight_2026 as _ov2026
    _ov2026.register(verify_resolve=False)
except Exception:
    pass

# ── 50 BESPOKE designer BLENDS (2026-06-25, campaign #17) ───────────────────────────────
# Designed cross-family material recipes built only from already-shipped finishes (resolvable
# for every buyer), validated by scripts/specsculpt_preset_audit.py. Guarded so it can never
# break preset loading.
try:
    from engine.spec_sculpt import presets_bespoke50_2026 as _bz2026
    _bz2026.register(verify_resolve=False)
except Exception:
    pass
