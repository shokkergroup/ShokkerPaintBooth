"""LIVERY THEME LIBRARY — the curated design brain behind "Design It" + "Photo->Livery".

PURELY ADDITIVE data module (no global-state mutation, no registry boot on import).
``engine/livery_designer.py`` imports this to turn a parsed vibe into an INTENTIONAL,
harmonious, multi-zone livery instead of one flat color.

What a THEME is
---------------
Each theme is a hand-authored *art direction*: a small harmonious palette (OKLab-
validated so the colors always sit well together) plus FINISH ROLES drawn from REAL
catalog ids — favoring the crown-jewel families (Fractured Souls ``fs_*``, Fractured
Minds ``fm_*``, ``chameleon_*``, ``prizm_*``, ``spectrum_*``, candy/chrome/pearl).

A role is one of:
    body     the dominant finish over the largest area (1 required, list = ranked
             candidates, first live wins)
    body2    optional secondary body finish for a two-tone split
    feature  optional hood/roof "hero" finish (the wow panel)
    accent   small-area accent finish (stripes, mirrors, wing...)

Each role also carries a *palette index* (which palette color it wears) so the
designer can paint a cohesive multi-color livery, and a *kind* ('mono' or 'base').

Every id below was verified live against the booted registry on 2026-06-13
(MONOLITHIC_REGISTRY 1167 / BASE_REGISTRY 518). At runtime the designer still
re-checks each id and falls through the candidate list, so output always renders.

The matcher vocabulary (``synonyms``) maps free-text mood/vibe/racing words onto
themes; ``engine/livery_designer`` scores a prompt against every theme's synonyms
plus its name and palette color words.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

# A role spec: (role_name, [candidate_ids], kind, palette_index)
# kind: "mono" -> zone["finish"], "base" -> zone["base"].
Role = Tuple[str, List[str], str, int]


def _t(name: str, palette: List[Tuple[int, int, int]], roles: List[Role],
       synonyms: List[str], number: Tuple[int, int, int] = None,
       mood: str = "", tags: List[str] = None) -> Dict:
    """Build one theme.

    ``tags`` group themes into vibe FAMILIES (dark, fire, ice, neon, cosmic,
    iridescent, luxury, candy, chrome, pearl, nature, blood, racing, military,
    cyber, japan, glitch, sunset, color-forward...). The designer uses tags to
    pick VARIATIONS that stay on-vibe (a related family) instead of an opposite
    wildcard — the heart of the "3 distinct-but-coherent options" moment.
    """
    return {
        "name": name,
        "palette": [tuple(int(c) for c in rgb) for rgb in palette],
        "roles": roles,
        "synonyms": synonyms,
        # readable number color; if None the designer derives a high-contrast one.
        "number": tuple(number) if number else None,
        "mood": mood,
        "tags": list(tags or []),
    }


# ---------------------------------------------------------------------------
# THE THEME LIBRARY.  ~55 curated art directions.
# Palettes are authored as harmonious anchors; livery_designer re-validates/
# perceptually spaces them through color_science (OKLab) at build time.
# ---------------------------------------------------------------------------
THEMES: List[Dict] = [

    # ---- DARK / MENACE ----------------------------------------------------
    _t("Midnight Menace",
       [(14, 15, 22), (120, 16, 22), (190, 196, 204)],
       [("body", ["fs_blood_marble", "ghost_fracture", "fm_inferno_veins"], "mono", 0),
        ("feature", ["fs_shatter_glass", "fs_static_veins", "fm_damascus"], "mono", 1),
        ("accent", ["black_chrome", "dark_chrome", "gunmetal"], "base", 2)],
       ["menacing", "menace", "sinister", "dark", "evil", "villain", "intimidating",
        "aggressive", "angry", "brutal", "savage", "fierce", "vicious", "ruthless",
        "rage", "wrath", "demon", "devil", "hell", "blackout", "night", "shadow",
        "darth", "vader", "predator", "hunter", "killer", "deadly", "lethal", "war"],
       number=(210, 30, 32), mood="brooding blacked-out aggression with a blood-red tell",
       tags=["dark", "aggressive", "blood"]),

    _t("Carbon Stealth",
       [(22, 24, 28), (40, 44, 50), (96, 102, 110)],
       [("body", ["carbon_weave", "enh_carbon_fiber", "forged_carbon_vis"], "base", 0),
        ("feature", ["fm_carbon_weave", "fm_graphene", "fm_nanoweave"], "mono", 1),
        ("accent", ["gunmetal_satin", "matte", "flat_black"], "base", 2)],
       ["stealth", "stealthy", "carbon", "fiber", "fibre", "tactical", "covert",
        "blackops", "murdered", "murderedout", "satin", "weave", "matte", "flat",
        "ghostgray", "incognito", "lowkey", "subtle", "sleeper", "nightops"],
       number=(150, 158, 168), mood="all-business forged carbon, no shine to give it away",
       tags=["dark", "carbon", "stealth"]),

    _t("Phantom Wraith",
       [(36, 38, 48), (150, 156, 170), (210, 214, 224)],
       [("body", ["fs_wraith_veil", "fs_ghost_silk", "fs_phantom_lattice"], "mono", 0),
        ("feature", ["fs_moire_phantom", "ghost_fracture", "wraith"], "mono", 1),
        ("accent", ["midnight_pearl", "pearl", "satin"], "base", 2)],
       ["ghost", "ghostly", "phantom", "wraith", "haunted", "haunting", "spirit",
        "spooky", "spectral", "veil", "apparition", "specter", "eerie", "fog",
        "mist", "misty", "smoke", "smoky", "soul", "souls", "ethereal", "faint",
        "whisper", "shroud", "pale"],
       number=(220, 224, 232), mood="a livery that's barely there until the light hits it",
       tags=["ghost", "stealth", "dark"]),

    _t("Gunmetal Brute",
       [(54, 58, 66), (28, 30, 36), (188, 64, 30)],
       [("body", ["gunmetal_flake", "gunmetal", "cobalt_metal"], "base", 0),
        ("feature", ["fm_diamond_plate", "fm_rivet_array", "fm_damascus"], "mono", 1),
        ("accent", ["satin_metal", "metallic", "black_chrome"], "base", 2)],
       ["gunmetal", "industrial", "machined", "heavy", "armor", "armour", "battleship",
        "forged", "metal", "raw", "mechanical", "brute", "brutal", "rugged", "tank",
        "mech", "robot", "robotic", "steampunk", "diesel", "grit", "hardcore"],
       number=(232, 120, 40), mood="machined gunmetal with a hot orange edge",
       tags=["dark", "metal", "aggressive", "military"]),

    # ---- FIRE / HEAT ------------------------------------------------------
    _t("Inferno",
       [(140, 12, 10), (240, 96, 16), (255, 196, 40)],
       # WARMTH FIX (2026-06-13): the old fm_inferno_veins / fm_magma / fm_flame_*
       # ids render COOL blue-violet on-car (verified frac_warm<0.2, mean(R-B)<0 @2048).
       # Swapped to ids verified WARM @2048 (fractal_liquid_fire R-B+140,
       # spectrum_forge_heat +127, prizm_copper_flame +150, ember_glow +40).
       [("body", ["fractal_liquid_fire", "spectrum_forge_heat", "prizm_copper_flame"], "mono", 0),
        ("feature", ["ember_glow", "prizm_copper_flame", "fractal_liquid_fire"], "mono", 1),
        ("accent", ["candy_apple", "candy", "gloss"], "base", 2)],
       ["fire", "fiery", "inferno", "flame", "flames", "flaming", "blaze", "blazing",
        "lava", "magma", "molten", "burning", "burn", "hellfire", "scorch", "scorched",
        "hot", "heat", "ember", "embers", "volcano", "volcanic", "eruption", "erupt",
        "wildfire", "pyro", "combust", "torch", "brimstone"],
       number=(255, 214, 60), mood="a car that looks like it's still on fire",
       tags=["fire", "aggressive"]),

    _t("Phoenix Rising",
       [(180, 24, 18), (255, 120, 20), (255, 210, 70)],
       # WARMTH FIX (2026-06-13): body ids were already warm (prizm_phoenix R-B+168,
       # chameleon_phoenix +140, fd_phoenix_fenghuang +89), but the FEATURE used the
       # cool fm_flame_helix / fm_magma — swapped to verified-warm fs_ember_drift (+24)
       # and fractal_liquid_fire (+140) so the hero panel stays in the fire family.
       [("body", ["prizm_phoenix", "chameleon_phoenix", "fd_phoenix_fenghuang"], "mono", 0),
        ("feature", ["fs_ember_drift", "fractal_liquid_fire", "ember_glow"], "mono", 1),
        ("accent", ["satin_gold", "candy", "gloss"], "base", 2)],
       ["phoenix", "rising", "reborn", "rebirth", "firebird", "ash", "ashes",
        "resurrection", "resurrect", "feather", "wing", "wings", "immortal", "eternal"],
       number=(255, 222, 90), mood="reds bleeding up into gold like rising flame",
       tags=["fire", "luxury", "mythic"]),

    _t("Solar Forge",
       [(70, 28, 14), (220, 110, 24), (255, 224, 120)],
       # WARMTH FIX (2026-06-13): kept the verified-warm spectrum_forge_heat (R-B+127)
       # as body but dropped the COOL fallbacks grad_steel_forge / fable_oilforge and
       # the COOL feature spectrum_star_temperature (a blue swirl, R-B-27) + fm_magma.
       # Body now leads forge-heat then warm grad/prizm copper flame; feature is the
       # bright glowing-metal ember_glow. Distinct from Inferno (fractal_liquid_fire).
       [("body", ["spectrum_forge_heat", "grad_copper_flame", "prizm_copper_flame"], "mono", 0),
        ("feature", ["ember_glow", "fractal_liquid_fire", "fs_ember_drift"], "mono", 1),
        ("accent", ["satin_metal", "metallic", "gloss"], "base", 2)],
       ["forge", "forged", "molten", "solar", "sun", "furnace", "smelt", "tempered",
        "weld", "welding", "anneal", "metalwork", "smith", "blacksmith", "smithy",
        "kiln", "foundry"],
       number=(255, 230, 130), mood="glowing tempered-metal heat gradient",
       tags=["fire", "metal"]),

    # ---- ICE / WATER ------------------------------------------------------
    _t("Arctic Ice",
       [(214, 232, 244), (120, 186, 224), (40, 70, 120)],
       [("body", ["fm_frost_lace", "fm_glacier_core", "fm_frost_feather"], "mono", 0),
        ("feature", ["black_ice", "fs_phantom_lattice", "crystal_lattice"], "mono", 1),
        ("accent", ["pearlescent_white", "deep_pearl", "pearl"], "base", 2)],
       ["ice", "icy", "frost", "frosty", "frozen", "freeze", "freezing", "glacier",
        "glacial", "arctic", "antarctic", "cold", "winter", "wintry", "crystal",
        "snow", "snowy", "chill", "chilly", "subzero", "tundra", "polar", "blizzard",
        "iceberg", "permafrost"],
       number=(30, 60, 110), mood="cracked glacier whites and deep cold blues",
       tags=["ice"]),

    _t("Deep Ocean",
       [(8, 30, 52), (16, 96, 128), (60, 200, 200)],
       [("body", ["cs_deepocean", "cs_ocean_shift", "ocean_floor"], "mono", 0),
        ("feature", ["bioluminescent_wave", "depth_wave", "fs_night_tide"], "mono", 1),
        ("accent", ["deep_pearl", "pearl", "gloss"], "base", 2)],
       ["ocean", "oceanic", "sea", "deep", "abyss", "abyssal", "marine", "aquatic",
        "tide", "wave", "waves", "nautical", "submarine", "fathom", "current", "water",
        "underwater", "depths", "bioluminescent", "bioluminescence", "kraken",
        "leviathan", "trench", "reef"],
       number=(70, 210, 210), mood="abyssal blues with a bioluminescent glow",
       tags=["ocean", "ice"]),

    _t("Frost & Fire",
       [(220, 80, 30), (235, 240, 248), (40, 150, 210)],
       [("body", ["prizm_fire_ice", "cs_fire_ice", "dualshift_ice_fire"], "mono", 0),
        ("feature", ["gradient_ember_ice", "ms_frozen_inferno", "fm_tide_glass"], "mono", 1),
        ("accent", ["gloss", "candy", "pearl"], "base", 2)],
       ["fireandice", "fireice", "hotandcold", "duality", "dual", "split", "yin",
        "yang", "contrast", "opposites", "opposite", "balance", "twoface", "halfhalf"],
       number=(245, 245, 250), mood="one half molten, one half glacial",
       tags=["fire", "ice"]),

    # ---- TOXIC / NEON -----------------------------------------------------
    _t("Toxic Racer",
       [(18, 26, 14), (120, 240, 30), (200, 255, 60)],
       [("body", ["prizm_toxic_waste", "neon_toxic_green", "cc_radioactive"], "mono", 0),
        ("feature", ["pp_neon_fracture_net", "fm_circuit_maze", "radioactive"], "mono", 1),
        ("accent", ["flat_black", "matte", "black_chrome"], "base", 2)],
       ["toxic", "radioactive", "acid", "acidic", "venom", "venomous", "poison",
        "poisonous", "biohazard", "hazard", "nuclear", "uranium", "plutonium",
        "chemical", "mutant", "mutated", "slime", "sludge", "ooze", "fallout",
        "chernobyl", "waste", "sewer", "infected"],
       number=(180, 255, 40), mood="electric hazard-green over a dark chassis",
       tags=["toxic", "neon", "dark", "aggressive"]),

    _t("Synthwave Sunset",
       [(20, 8, 40), (236, 28, 152), (40, 220, 235)],
       [("body", ["spectrum_vhs_phantom", "spectrum_vinyl_groove", "prizm_neon"], "mono", 0),
        ("feature", ["laser_grid", "rs_time_attack_grid_shock", "neon_dual_glow"], "mono", 1),
        ("accent", ["neon_electric_blue", "candy_cobalt", "gloss"], "base", 2)],
       ["synthwave", "retro", "retrowave", "vaporwave", "outrun", "miami", "neon",
        "eighties", "80s", "1980s", "arcade", "vhs", "grid", "sunset", "vice",
        "tron", "laserwave", "darkwave", "nightdrive", "cassette", "synth", "disco"],
       number=(40, 230, 240), mood="hot-pink and cyan neon over deep violet night",
       tags=["neon", "retro", "sunset", "cyber"]),

    _t("Electric Bloom",
       [(12, 10, 24), (255, 40, 180), (60, 255, 140)],
       [("body", ["neon_pink_blaze", "chameleon_neon", "neon_glow"], "mono", 0),
        ("feature", ["reactive_plasma", "plasma_globe", "neon_rainbow_tube"], "mono", 1),
        ("accent", ["neon_electric_blue", "gloss", "candy"], "base", 2)],
       ["neon", "electric", "glow", "glowing", "luminous", "fluorescent", "bright",
        "vivid", "rave", "club", "laser", "blacklight", "uv", "highlighter", "fluo",
        "glowstick", "edm", "festival", "psychedelic"],
       number=(70, 255, 150), mood="blacklight-bright neon pinks and greens",
       tags=["neon", "color-forward"]),

    # ---- COSMIC / SPACE ---------------------------------------------------
    _t("Galaxy Cosmic",
       [(10, 8, 28), (90, 40, 170), (60, 180, 230)],
       [("body", ["chameleon_galaxy", "galaxy", "prizm_deep_space"], "mono", 0),
        ("feature", ["fs_star_chart", "sparkle_starfield", "cs_nebula"], "mono", 1),
        ("accent", ["deep_pearl", "midnight_pearl", "pearl"], "base", 2)],
       ["cosmic", "cosmos", "galaxy", "galactic", "space", "spacey", "nebula",
        "stellar", "universe", "interstellar", "starry", "stars", "celestial",
        "deepspace", "void", "astro", "astral", "milkyway", "constellation",
        "orbit", "planet", "moon", "lunar", "comet", "meteor"],
       number=(120, 200, 240), mood="deep-space purples and blues flecked with stars",
       tags=["cosmic", "iridescent", "dark"]),

    _t("Aurora Borealis",
       [(8, 18, 26), (40, 210, 150), (90, 70, 200)],
       [("body", ["chameleon_aurora", "aurora", "fs_aurora_threads"], "mono", 0),
        ("feature", ["aurora_glow", "spectrum_borealis_ice", "fable_aurora_travel"], "mono", 1),
        ("accent", ["deep_pearl", "pearl", "gloss"], "base", 2)],
       ["aurora", "borealis", "northern", "lights", "polar", "shimmer", "shimmering",
        "ethereal", "iceland", "norway", "ribbons", "dreamy", "tranquil", "serene"],
       number=(80, 230, 180), mood="green-to-violet northern-lights ribbons on midnight",
       tags=["aurora", "iridescent", "cosmic", "ice"]),

    _t("Nova Burst",
       [(18, 6, 30), (255, 120, 40), (255, 230, 120)],
       [("body", ["fs_nova_burst", "spectrum_swirl_supernova", "spectrum_singularity_lens"], "mono", 0),
        ("feature", ["fs_core_violet", "sparkle_galaxy", "spectrum_event_horizon"], "mono", 1),
        ("accent", ["satin_gold", "gloss", "candy"], "base", 2)],
       ["nova", "supernova", "explosion", "explosive", "burst", "blast", "starburst",
        "bigbang", "radiate", "detonate", "detonation", "blackhole", "singularity",
        "eventhorizon", "quasar", "pulsar"],
       number=(255, 234, 130), mood="a violent stellar explosion, violet core to gold rim",
       tags=["cosmic", "fire", "aggressive"]),

    # ---- IRIDESCENT / CHAMELEON ------------------------------------------
    _t("Oilslick Iridescent",
       [(16, 18, 24), (40, 120, 90), (150, 60, 170)],
       [("body", ["fs_oil_serpent", "cs_oilslick", "oil_slick"], "mono", 0),
        ("feature", ["fs_petrol_halo", "spectrum_oilfilm_rain", "microshift_oil_slick"], "mono", 1),
        ("accent", ["black_chrome", "dark_chrome", "gloss"], "base", 2)],
       ["oilslick", "oil", "petrol", "petroleum", "gasoline", "slick", "iridescent",
        "rainbow", "sheen", "filmy", "thinfilm", "beetle", "scarab", "soapbubble",
        "bubble", "greasy", "shimmerdark"],
       number=(210, 214, 220), mood="dark gasoline-rainbow swirl, color that moves",
       tags=["iridescent", "dark"]),

    _t("Chameleon Shift",
       [(20, 30, 50), (40, 160, 120), (160, 70, 180)],
       [("body", ["chameleon_emerald", "prizm_mystichrome", "mystichrome"], "mono", 0),
        ("feature", ["prizm_duochrome", "cs_chrome_shift", "prizm_iridescent"], "mono", 1),
        ("accent", ["chrome", "candy_chrome", "gloss"], "base", 2)],
       ["chameleon", "colorshift", "colorshifting", "colorchanging", "flip", "flipflop",
        "duochrome", "multichrome", "shift", "shifting", "mystichrome", "pearlshift",
        "morph", "morphing", "psychedelic", "trippy", "mood"],
       number=(220, 224, 230), mood="a finish that swaps color as the car turns",
       tags=["iridescent", "chrome"]),

    _t("Prism Holographic",
       [(12, 12, 18), (60, 200, 220), (240, 90, 200)],
       [("body", ["prizm_holographic", "prizm_spectrum", "prizm_iridescent"], "mono", 0),
        ("feature", ["spectrum_diamond_fire", "spectrum_rainbow_river", "fs_shattered_prism"], "mono", 1),
        ("accent", ["chrome", "candy_chrome", "gloss"], "base", 2)],
       ["holographic", "holo", "prismatic", "prism", "rainbow", "spectral",
        "spectrum", "diffraction", "hologram", "psychedelic", "kaleidoscope",
        "kaleidoscopic", "unicorn", "opal", "opalescent", "dichroic"],
       number=(240, 240, 245), mood="full-spectrum holographic diffraction sparkle",
       tags=["iridescent", "chrome", "neon"]),

    # ---- LUXURY / GOLD ----------------------------------------------------
    _t("Gold Luxury",
       [(12, 12, 14), (196, 150, 44), (236, 210, 130)],
       [("body", ["cs_black_gold", "grad_black_gold", "fd_imperial_gold"], "mono", 0),
        ("feature", ["baroque_scrollwork", "rs_temple_gold", "scarab_gold"], "mono", 1),
        ("accent", ["satin_gold", "chrome", "gloss"], "base", 2)],
       ["luxury", "luxurious", "gold", "golden", "opulent", "rich", "premium",
        "expensive", "vip", "couture", "lavish", "elite", "gatsby", "artdeco",
        "deco", "bullion", "moneyed", "blingrich", "millionaire", "lacquer"],
       number=(236, 212, 140), mood="black lacquer with liquid-gold detailing",
       tags=["luxury", "dark"]),

    _t("Royal Baroque",
       [(24, 12, 36), (120, 28, 52), (210, 176, 90)],
       [("body", ["baroque_scrollwork", "uj_midnight_hearse_baroque", "grad_wine_silk"], "mono", 0),
        ("feature", ["cs_burgundy_gold", "grad_black_gold", "rs_temple_gold"], "mono", 1),
        ("accent", ["satin_gold", "deep_pearl", "pearl"], "base", 2)],
       ["royal", "regal", "imperial", "baroque", "majestic", "monarch", "crown",
        "throne", "ornate", "palace", "noble", "aristocrat", "renaissance", "versailles",
        "rococo", "gilded", "gild", "filigree", "victorian", "pharaoh", "egyptian",
        "egypt", "tomb", "dynasty"],
       number=(214, 182, 100), mood="deep plum and burgundy with gilded scrollwork",
       tags=["luxury", "blood", "color-forward"]),

    _t("Rose Gold Couture",
       [(40, 24, 30), (224, 150, 130), (236, 200, 170)],
       [("body", ["cs_rosegold", "grad_rose_gold", "prizm_chrome_rose"], "mono", 0),
        ("feature", ["grad_rose_gold_vortex", "cs_pink_gold", "cx_pink_to_gold"], "mono", 1),
        ("accent", ["pearl", "satin", "gloss"], "base", 2)],
       ["rosegold", "rose", "blush", "champagne", "couture", "elegant", "feminine",
        "soft", "boutique", "glam", "glamour", "glamorous", "chic", "fashion",
        "luxe", "millennial", "peachy"],
       number=(240, 210, 185), mood="warm rose-gold chrome, soft and expensive",
       tags=["luxury", "chrome", "pearl", "color-forward"]),

    # ---- CANDY / SHOW CAR -------------------------------------------------
    _t("Candy Show Car",
       [(150, 12, 24), (236, 30, 40), (240, 220, 60)],
       [("body", ["candy_apple", "candy", "f_candy"], "base", 0),
        ("feature", ["prizm_candy_paint", "cs_candypaint", "halo_wave_candy"], "mono", 1),
        ("accent", ["chrome", "candy_chrome", "gloss"], "base", 2)],
       ["candy", "showcar", "show", "lowrider", "custom", "wet", "glossy", "gloss",
        "kandy", "metalflake", "applered", "hotrod", "musclecar", "cruiser",
        "kustom", "deeppaint", "slammed"],
       number=(245, 224, 70), mood="deep liquid candy-apple with a mile of gloss",
       tags=["candy", "color-forward", "chrome"]),

    _t("Cotton Candy",
       [(248, 184, 214), (180, 210, 245), (250, 244, 224)],
       [("body", ["cx_cotton_candy", "jelly_pearl", "pearl"], "base", 0),
        ("feature", ["gradient_candy_frozen", "prizm_arctic", "chameleon_frost"], "mono", 1),
        ("accent", ["pearlescent_white", "satin", "gloss"], "base", 2)],
       ["cottoncandy", "pastel", "candyfloss", "kawaii", "dreamy", "soft", "bubblegum",
        "sweet", "cute", "babyblue", "babypink", "unicorncute", "macaron", "marshmallow",
        "icecream"],
       number=(120, 130, 180), mood="pastel pink and sky-blue dreamscape",
       tags=["candy", "pearl", "color-forward"]),

    # ---- CHROME / METAL ---------------------------------------------------
    _t("Liquid Chrome",
       [(180, 186, 196), (60, 66, 76), (220, 226, 234)],
       [("body", ["chrome", "living_chrome", "enh_chrome"], "base", 0),
        ("feature", ["fractal_chrome_decay", "spectrum_smoke_chroma", "worn_chrome"], "mono", 1),
        ("accent", ["black_chrome", "dark_chrome", "gunmetal"], "base", 2)],
       ["chrome", "mirror", "mirrored", "polished", "polish", "liquid", "metallic",
        "shiny", "shine", "reflective", "mercury", "silver", "quicksilver", "platinum",
        "molten metal", "moltenmetal", "liquidmetal", "t1000", "terminator"],
       number=(40, 44, 52), mood="poured liquid mirror, sky reflected in the paint",
       tags=["chrome", "metal"]),

    _t("Titanium Anodize",
       [(60, 64, 78), (120, 90, 160), (200, 140, 80)],
       [("body", ["prizm_titanium", "trizone_titanium_copper_chrome", "aniso_wave_titanium"], "mono", 0),
        ("feature", ["spectrum_tempered_ghost", "grad_titanium_fire", "cs_titanium_crimson"], "mono", 1),
        ("accent", ["gunmetal_satin", "satin_metal", "metallic"], "base", 2)],
       ["titanium", "anodized", "anodize", "tempered", "burnt", "exhaust", "heatblue",
        "alloy", "aerospace", "jet", "fighterjet", "turbine", "afterburner", "spaceship"],
       number=(210, 150, 90), mood="heat-tempered titanium blues and burnt coppers",
       tags=["metal", "chrome", "iridescent"]),

    _t("Chrome Flake",
       [(30, 34, 44), (150, 158, 170), (96, 150, 220)],
       [("body", ["metal_flake_base", "gunmetal_flake", "original_metal_flake"], "base", 0),
        ("feature", ["sparkle_galaxy", "multiscale_chrome_grain", "halo_diamond_chrome"], "mono", 1),
        ("accent", ["chrome", "candy_chrome", "gloss"], "base", 2)],
       ["flake", "metalflake", "sparkle", "sparkly", "glitter", "glittery", "grain",
        "shimmer", "fleck", "diamond", "diamonds", "bedazzled", "blingflake", "twinkle"],
       number=(110, 170, 235), mood="coarse metal-flake that throws sparks of light",
       tags=["metal", "chrome", "color-forward"]),

    # ---- PEARL / ELEGANT --------------------------------------------------
    _t("Pearl Elegance",
       [(232, 230, 232), (90, 100, 130), (40, 50, 80)],
       [("body", ["tri_coat_pearl", "deep_pearl", "pearl"], "base", 0),
        ("feature", ["midnight_pearl", "jelly_pearl", "pace_car_pearl"], "base", 1),
        ("accent", ["chrome", "satin", "gloss"], "base", 2)],
       ["elegant", "elegance", "classy", "class", "refined", "sophisticated",
        "sophistication", "pearl", "pearlescent", "tasteful", "understated",
        "graceful", "clean", "minimal", "minimalist", "executive", "tuxedo", "formal"],
       number=(40, 50, 80), mood="luminous tri-coat pearl with deep navy detail",
       tags=["pearl", "luxury"]),

    _t("Midnight Pearl",
       [(14, 18, 38), (40, 60, 110), (150, 170, 210)],
       [("body", ["midnight_pearl", "deep_pearl", "pearl"], "base", 0),
        ("feature", ["fs_night_tide", "chameleon_midnight", "prizm_midnight"], "mono", 1),
        ("accent", ["pearlescent_white", "satin", "gloss"], "base", 2)],
       ["midnight", "navy", "indigo", "twilight", "dusk", "evening", "deepblue",
        "nautical", "moonlit", "moonlight", "nightsky", "starrynight", "navyblue"],
       number=(160, 180, 220), mood="deep midnight-blue pearl that glows at the edges",
       tags=["pearl", "dark", "ocean", "cosmic"]),

    # ---- NATURE -----------------------------------------------------------
    _t("Emerald Serpent",
       [(8, 26, 18), (20, 130, 80), (150, 220, 120)],
       [("body", ["fs_serpent_scale", "fm_python_skin", "fm_dragon_scale"], "mono", 0),
        ("feature", ["chameleon_emerald", "cs_gold_emerald", "fs_core_emerald"], "mono", 1),
        ("accent", ["satin_gold", "gloss", "candy_emerald"], "base", 2)],
       ["serpent", "snake", "snakeskin", "python", "viper", "reptile", "reptilian",
        "scale", "scales", "scaled", "emerald", "jade", "cobra", "lizard", "anaconda",
        "mamba", "gecko", "iguana"],
       number=(160, 230, 130), mood="iridescent green serpent-scale with gold",
       tags=["nature", "iridescent", "luxury"]),

    _t("Jungle Predator",
       [(18, 24, 12), (96, 120, 40), (200, 150, 30)],
       [("body", ["fm_tiger_slash", "fm_croc_hide", "fm_tortoise"], "mono", 0),
        ("feature", ["ghost_camo", "fm_python_skin", "fm_stingray"], "mono", 1),
        ("accent", ["matte", "satin", "flat_black"], "base", 2)],
       ["jungle", "predator", "tiger", "leopard", "cheetah", "panther", "lion",
        "wild", "feral", "safari", "camouflage", "camo", "beast", "animal", "savage",
        "tropical", "apex", "prowl", "stalk", "claws", "fangs"],
       number=(220, 170, 40), mood="muddy greens and amber with predator markings",
       tags=["nature", "military", "aggressive"]),

    _t("Dragon Scale",
       [(28, 8, 12), (150, 24, 30), (210, 150, 40)],
       [("body", ["fm_dragon_scale", "rs_kuro_dragon", "fd_dragon_phoenix"], "mono", 0),
        ("feature", ["ms_dragon_soul", "rs_thunder_dragon", "fs_serpent_scale"], "mono", 1),
        ("accent", ["satin_gold", "candy_apple", "gloss"], "base", 2)],
       ["dragon", "dragons", "wyrm", "drake", "mythic", "mythical", "legendary",
        "legend", "fantasy", "scaled", "beast", "lair", "wyvern", "imperial dragon",
        "imperialdragon", "gameofthrones", "khaleesi", "draconic", "hydra"],
       number=(220, 170, 50), mood="crimson dragon-scale armor edged in gold",
       tags=["nature", "blood", "luxury", "mythic", "japan"]),

    _t("Geode Crystal",
       [(20, 14, 32), (110, 60, 160), (90, 200, 220)],
       [("body", ["fs_geode_vein", "fm_geode_slice", "fm_basalt"], "mono", 0),
        ("feature", ["crystal_lattice", "spectrum_jewel_box", "fs_core_violet"], "mono", 1),
        ("accent", ["deep_pearl", "gloss", "pearl"], "base", 2)],
       ["geode", "crystal", "crystalline", "amethyst", "gem", "gemstone", "mineral",
        "quartz", "druzy", "jewel", "jewels", "jeweled", "agate", "opal", "diamond",
        "facet", "faceted", "prismstone"],
       number=(110, 210, 230), mood="cracked-open geode, violet rind to crystal core",
       tags=["nature", "iridescent", "cosmic"]),

    # ---- BLOOD / DARK FANTASY --------------------------------------------
    _t("Blood Moon",
       [(10, 8, 12), (110, 14, 20), (200, 160, 70)],
       [("body", ["prizm_blood_moon", "fs_blood_marble", "blood_oath"], "mono", 0),
        ("feature", ["rs_oni_bloodshift", "fs_widow_braid", "ms_blood_empress"], "mono", 1),
        ("accent", ["black_chrome", "dark_chrome", "satin_gold"], "base", 2)],
       ["blood", "bloody", "bloodmoon", "crimson", "gothic", "goth", "vampire",
        "vampiric", "horror", "macabre", "eclipse", "ritual", "occult", "occultist",
        "cult", "witchcraft", "witch", "witchy", "darkmagic", "sorcery", "demonic",
        "satanic", "cursed", "necromancer", "darkfantasy", "funeral", "mourning"],
       number=(206, 168, 76), mood="black night, blood-red moon, pale gold halo",
       tags=["blood", "dark", "aggressive", "luxury"]),

    _t("Widow's Web",
       [(12, 12, 16), (60, 64, 74), (150, 24, 30)],
       [("body", ["fs_widow_braid", "fm_thousand_eyes", "fs_static_veins"], "mono", 0),
        ("feature", ["ghost_fracture", "fs_moire_phantom", "fm_chainmail"], "mono", 1),
        ("accent", ["matte", "black_chrome", "flat_black"], "base", 2)],
       ["widow", "web", "webbed", "spider", "trap", "lurk", "arachnid", "silk",
        "creep", "creepy", "tarantula", "cobweb", "lair", "predatory"],
       number=(200, 36, 40), mood="black widow web with a red hourglass tell",
       tags=["dark", "blood", "aggressive", "nature"]),

    # ---- PATRIOTIC / RACING -----------------------------------------------
    _t("Patriot",
       [(180, 22, 38), (245, 245, 248), (24, 40, 120)],
       [("body", ["candy_apple", "candy", "race_day_gloss"], "base", 0),
        ("body2", ["candy_cobalt", "deep_pearl", "midnight_pearl"], "base", 2),
        ("feature", ["fs_star_chart", "sparkle_starfield", "lfr_glory_chrome"], "mono", 1),
        ("accent", ["pearlescent_white", "chrome", "gloss"], "base", 1)],
       ["patriotic", "patriot", "america", "american", "usa", "stars", "stripes",
        "freedom", "liberty", "independence", "redwhiteblue", "fourthofjuly",
        "stateside", "captainamerica", "uncle sam", "unclesam", "starsandstripes"],
       number=(245, 245, 248), mood="bold red, white and blue with star detail",
       tags=["racing", "color-forward"]),

    _t("Race Day",
       [(220, 30, 36), (245, 245, 248), (20, 22, 28)],
       [("body", ["race_day_gloss", "drag_strip_gloss", "gloss"], "base", 0),
        ("body2", ["flat_black", "matte", "satin"], "base", 2),
        ("feature", ["fm_checkerflash", "rs_time_attack_grid_shock", "fm_circuit_maze"], "mono", 1),
        ("accent", ["gloss_wrap", "chrome", "gloss"], "base", 1)],
       ["race", "racing", "racer", "motorsport", "track", "trackday", "grid",
        "speed", "speedy", "fast", "competition", "gt", "gt3", "sport", "sports",
        "checker", "checkered", "flag", "podium", "f1", "formula", "lemans", "nascar",
        "touring", "factory", "team", "pitlane"],
       number=(245, 245, 248), mood="clean factory-team red, white and black",
       tags=["racing", "color-forward"]),

    _t("Sunset Cruiser",
       [(40, 18, 60), (236, 96, 64), (250, 200, 90)],
       [("body", ["grad_sunset", "cx_sunset_horizon", "cs_sunset_ocean"], "mono", 0),
        ("feature", ["dualshift_sunset", "cx_tropical_sunset", "vm_adobe_sunset"], "mono", 1),
        ("accent", ["satin", "pearl", "gloss"], "base", 2)],
       ["sunset", "sundown", "cruiser", "cruise", "dusk", "horizon", "warm", "golden",
        "evening", "coast", "coastal", "beach", "beachy", "summer", "palm", "palms",
        "vacation", "tropical", "tropics", "malibu", "california", "vaporsunset",
        "goldenhour", "seaside", "resort"],
       number=(252, 210, 110), mood="purple-to-amber sunset gradient, warm and easy",
       tags=["sunset", "color-forward", "retro"]),

    # ---- MILITARY / UTILITY -----------------------------------------------
    _t("Military Spec",
       [(56, 62, 44), (34, 38, 30), (150, 130, 70)],
       [("body", ["ghost_camo", "fm_diamond_plate", "fm_basalt"], "mono", 0),
        ("feature", ["fm_rivet_array", "cc_digital_rot", "fm_chainlink"], "mono", 1),
        ("accent", ["matte", "flat_black", "gunmetal_satin"], "base", 2)],
       ["military", "army", "soldier", "combat", "warzone", "fieldgear", "olive",
        "fatigue", "fatigues", "utility", "rugged", "milspec", "tank", "navyseal",
        "marines", "warfare", "trooper", "battalion", "platoon", "ammo", "gunner"],
       number=(160, 142, 80), mood="olive-drab field camo with stenciled markings",
       tags=["military", "dark", "nature"]),

    _t("Desert Storm",
       [(96, 80, 50), (200, 170, 110), (60, 56, 48)],
       [("body", ["fm_mudcrack", "fm_topo_lines", "fm_basalt"], "mono", 0),
        ("feature", ["ghost_camo", "fm_riverine", "weather_ice_storm"], "mono", 1),
        ("accent", ["matte", "satin", "scuffed_satin"], "base", 2)],
       ["desert", "sand", "sandy", "dune", "dunes", "storm", "arid", "dust", "dusty",
        "tan", "outback", "expedition", "rally", "dakar", "baja", "offroad", "overland",
        "wasteland", "madmax", "saharan", "canyon"],
       number=(70, 64, 54), mood="cracked-earth tan and dust, rally-rugged",
       tags=["military", "nature"]),

    # ---- COLOR-FORWARD SINGLES -------------------------------------------
    _t("Electric Blue",
       [(8, 22, 60), (24, 90, 235), (90, 190, 250)],
       [("body", ["candy_cobalt", "neon_electric_blue", "cobalt_metal"], "base", 0),
        ("feature", ["chameleon_ocean", "prizm_oceanic", "cs_ocean_shift"], "mono", 1),
        ("accent", ["chrome", "gloss", "candy_chrome"], "base", 2)],
       ["blue", "cobalt", "sapphire", "azure", "electricblue", "royalblue", "cyan",
        "sky", "skyblue", "bluish", "aqua", "turquoise", "teal"],
       number=(100, 200, 252), mood="deep cobalt that flares electric in the light",
       tags=["color-forward", "ocean", "chrome"]),

    _t("Viper Green",
       [(8, 20, 10), (40, 200, 60), (200, 255, 90)],
       [("body", ["candy_emerald", "neon_toxic_green", "chameleon_venom"], "base", 0),
        ("feature", ["fs_serpent_scale", "fm_gila_bead", "prizm_venom"], "mono", 1),
        ("accent", ["black_chrome", "flat_black", "matte"], "base", 2)],
       ["green", "lime", "viper", "snakegreen", "kelly", "greenish", "emeraldcar"],
       number=(210, 255, 100), mood="aggressive viper-green over black",
       tags=["color-forward", "toxic", "aggressive", "nature"]),

    _t("Purple Reign",
       [(20, 8, 36), (110, 40, 190), (210, 130, 240)],
       [("body", ["chameleon_amethyst", "cx_purple_gold_majesty", "prizm_iridescent"], "mono", 0),
        ("feature", ["cs_violet_gold", "grad_neon_violet", "fs_core_violet"], "mono", 1),
        ("accent", ["satin_gold", "chrome", "gloss"], "base", 2)],
       ["purple", "violet", "amethyst", "royalpurple", "lavender", "grape", "plum",
        "reign", "majesty", "purplish", "ultraviolet", "orchid", "mauve"],
       number=(216, 140, 244), mood="rich royal purple with a gold shift",
       tags=["color-forward", "luxury", "iridescent"]),

    _t("Hot Pink Riot",
       [(30, 6, 22), (240, 30, 140), (255, 130, 190)],
       [("body", ["neon_pink_blaze", "cs_pink_gold", "candy_burgundy"], "mono", 0),
        ("feature", ["dualshift_pink_to_gold", "cx_pink_to_gold", "prizm_chrome_rose"], "mono", 1),
        ("accent", ["chrome", "candy_chrome", "gloss"], "base", 2)],
       ["pink", "magenta", "fuchsia", "hotpink", "riot", "bold", "loud", "punk",
        "barbie", "girly", "flamingo", "neonpink", "pinkish"],
       number=(255, 150, 200), mood="loud hot-pink that shifts toward gold",
       tags=["color-forward", "neon", "luxury"]),

    _t("Tangerine Heat",
       [(40, 16, 8), (240, 110, 24), (255, 190, 70)],
       [("body", ["candy", "candy_apple", "f_candy"], "base", 0),
        ("feature", ["cc_blood_orange", "grad_copper_flame", "prizm_copper_flame"], "mono", 1),
        ("accent", ["satin_metal", "gloss", "chrome"], "base", 2)],
       ["orange", "tangerine", "amber", "copper", "rust", "burnt", "sunkist",
        "marigold", "pumpkin", "orangey", "mango", "apricot", "papaya"],
       number=(255, 200, 80), mood="juicy tangerine candy with copper depth",
       tags=["color-forward", "candy", "fire"]),

    # ---- ABSTRACT / ARTISTIC ---------------------------------------------
    _t("Circuit Soul",
       [(10, 70, 150), (1, 200, 245), (130, 245, 255)],
       [("body", ["chameleon_ocean", "prizm_oceanic", "neon_electric_blue"], "mono", 0),
        ("feature", ["fs_circuit_soul", "spectrum_circuit_awakens", "fm_circuit_maze"], "mono", 1),
        ("accent", ["chrome", "black_chrome", "gloss"], "base", 2)],
       ["circuit", "cyber", "cyberpunk", "tech", "techno", "technology", "digital",
        "matrix", "data", "code", "ai", "futuristic", "future", "sci-fi", "scifi",
        "neonblue", "hacker", "mainframe", "circuitry", "nanotech", "android",
        "hologrid", "neuralnet", "wired", "blade runner", "bladerunner", "robocop"],
       number=(130, 245, 255), mood="electric-blue body with glowing cyan circuit panels",
       tags=["cyber", "neon", "color-forward"]),

    _t("Damascus Steel",
       [(28, 30, 36), (90, 96, 108), (180, 150, 90)],
       [("body", ["fm_damascus", "fm_basketweave", "fm_herringbone"], "mono", 0),
        ("feature", ["fractal_chrome_decay", "worn_chrome", "spectrum_smoke_chroma"], "mono", 1),
        ("accent", ["gunmetal_satin", "satin_metal", "metallic"], "base", 2)],
       ["damascus", "folded", "steel", "blade", "katana", "wootz", "swordsmith",
        "metalgrain", "sword", "machete", "cleaver", "forgedsteel", "bladed"],
       number=(190, 158, 96), mood="folded-steel watered pattern, blade-cold",
       tags=["metal", "dark", "japan"]),

    _t("Marble Veined",
       [(236, 232, 228), (60, 64, 72), (180, 150, 90)],
       [("body", ["fm_ebru_marble", "fs_blood_marble", "fm_geode_slice"], "mono", 0),
        ("feature", ["baroque_scrollwork", "grad_black_gold", "fs_geode_vein"], "mono", 1),
        ("accent", ["satin_gold", "pearl", "gloss"], "base", 2)],
       ["marble", "marbled", "veined", "stone", "carrara", "sculpture", "classical",
        "gallery", "museum", "statue", "greek", "roman", "alabaster", "onyx"],
       number=(70, 74, 84), mood="white marble laced with gold veins",
       tags=["luxury", "pearl", "color-forward"]),

    _t("Petal Storm",
       [(36, 10, 28), (230, 70, 130), (250, 200, 140)],
       [("body", ["fm_petal_storm", "rs_jorogumo_silk", "grad_rose_gold"], "mono", 0),
        ("feature", ["fable_stained_aurora", "cx_cotton_candy", "fs_carnival_night"], "mono", 1),
        ("accent", ["pearl", "satin", "gloss"], "base", 2)],
       ["petal", "petals", "floral", "flower", "flowers", "bloom", "blossom",
        "garden", "spring", "botanical", "rosegarden", "wildflower", "lotus"],
       number=(252, 210, 150), mood="a storm of pink petals over deep plum",
       tags=["color-forward", "candy", "japan"]),

    _t("Carnival Night",
       [(10, 6, 26), (236, 40, 120), (250, 210, 60)],
       [("body", ["fs_carnival_night", "neon_rainbow_tube", "prizm_neon"], "mono", 0),
        ("feature", ["spectrum_jewel_box", "neon_rainbow_tube", "sparkle_galaxy"], "mono", 1),
        ("accent", ["candy_chrome", "chrome", "gloss"], "base", 2)],
       ["carnival", "circus", "festival", "fairground", "party", "fun", "playful",
        "confetti", "celebration", "mardigras", "fiesta", "carnaval", "funfair"],
       number=(252, 214, 70), mood="midnight carnival lights, hot pink and gold",
       tags=["neon", "color-forward", "candy"]),

    _t("Moth Dust",
       [(24, 22, 30), (120, 110, 96), (200, 180, 140)],
       [("body", ["fs_moth_dust", "fm_dragonfly", "fm_stingray"], "mono", 0),
        ("feature", ["fs_petrol_halo", "spectrum_beetle_elytra", "dragonfly_wing"], "mono", 1),
        ("accent", ["satin", "matte", "pearl"], "base", 2)],
       ["moth", "powdery", "muted", "earthy", "vintage", "antique", "faded", "sepia",
        "weathered", "patina", "rustic", "aged", "nostalgic", "oldschool"],
       number=(210, 192, 152), mood="powdery moth-wing taupes with a faint sheen",
       tags=["nature", "pearl", "stealth"]),

    _t("Howl",
       [(14, 16, 24), (70, 90, 130), (200, 210, 230)],
       [("body", ["fs_howl", "fs_night_tide", "fs_static_veins"], "mono", 0),
        ("feature", ["aurora_glow", "chameleon_arctic", "fs_aurora_threads"], "mono", 1),
        ("accent", ["midnight_pearl", "deep_pearl", "satin"], "base", 2)],
       ["howl", "wolf", "wolves", "lunar", "primal", "wilderness", "pack", "hunt",
        "moonlitwolf", "fenrir", "lycan", "werewolf"],
       number=(210, 218, 236), mood="cold steel-blue night, a wolf's howl made paint",
       tags=["dark", "ice", "nature", "cosmic"]),

    # ---- JAPAN / RISING SUN ----------------------------------------------
    _t("Rising Sun",
       [(18, 14, 22), (190, 24, 36), (236, 214, 150)],
       [("body", ["rs_kuro_dragon", "rs_oni_nocturne", "rs_kurogane_rain"], "mono", 0),
        ("feature", ["rs_oni_bloodshift", "rs_kuro_dragon", "fs_shatter_glass"], "mono", 1),
        ("accent", ["black_chrome", "satin_gold", "matte"], "base", 2)],
       ["samurai", "bushido", "ronin", "shogun", "katana", "ninja", "shinobi",
        "japan", "japanese", "nippon", "tokyo", "kyoto", "oni", "yokai", "kabuki",
        "edo", "feudal", "dojo", "honor", "warrior", "blade", "risingsun"],
       number=(236, 30, 36), mood="black lacquer, rising-sun crimson, gilded edge",
       tags=["japan", "dark", "blood", "aggressive"]),

    _t("Sakura Drift",
       [(28, 18, 30), (236, 130, 170), (250, 240, 246)],
       [("body", ["rs_sakura_storm", "rs_sakura_cascade", "rs_geisha_whisper"], "mono", 0),
        ("feature", ["rs_drift_hanami_oversteer", "rs_fuji_dawn", "rs_crane_garden"], "mono", 1),
        ("accent", ["pearl", "satin", "gloss"], "base", 2)],
       ["sakura", "hanami", "cherry", "cherryblossom", "geisha", "fuji", "zen",
        "kimono", "origami", "koi", "crane", "kawaii japan", "harajuku", "drift",
        "touge", "jdm", "shutoko"],
       number=(120, 60, 90), mood="cherry-blossom pinks drifting over twilight",
       tags=["japan", "candy", "color-forward", "pearl"]),

    # ---- CYBER / GLITCH ---------------------------------------------------
    _t("Cyber Grid",
       [(8, 6, 22), (200, 30, 150), (40, 230, 235)],
       [("body", ["spectrum_vhs_phantom", "fm_circuit_maze", "spectrum_circuit_awakens"], "mono", 0),
        ("feature", ["rs_time_attack_grid_shock", "laser_grid", "fs_circuit_soul"], "mono", 1),
        ("accent", ["neon_electric_blue", "black_chrome", "chrome"], "base", 2)],
       ["cyberpunk", "cyber", "neon city", "neoncity", "nightcity", "dystopia",
        "dystopian", "augmented", "chrome city", "neondrive", "rgb", "gamer",
        "edgerunner", "samuraicyber", "streetracer", "underground"],
       number=(40, 235, 240), mood="neon-grid night city, magenta and cyan over black",
       tags=["cyber", "neon", "color-forward", "retro"]),

    _t("Datamosh Glitch",
       [(10, 10, 14), (236, 28, 90), (30, 230, 220)],
       [("body", ["datamosh", "glitch", "spectrum_aberration_glitch"], "mono", 0),
        ("feature", ["spectrum_aberration_glitch", "crt_scanline", "cc_punk_static"], "mono", 1),
        ("accent", ["black_chrome", "matte", "flat_black"], "base", 2)],
       ["glitch", "glitchy", "glitched", "datamosh", "datamoshing", "static", "noise",
        "corrupt", "corrupted", "vaporglitch", "pixelsort", "broken", "error", "404",
        "crt", "scanline", "scanlines", "tvstatic", "signal", "distortion", "artifact",
        "databend", "bitcrush"],
       number=(30, 230, 220), mood="corrupted-signal RGB tearing over black",
       tags=["glitch", "cyber", "neon", "dark"]),
]


# ---------------------------------------------------------------------------
# DEFAULT THEME — used when a prompt matches nothing recognizable.
# ---------------------------------------------------------------------------
DEFAULT_THEME = _t(
    "Signature Gloss",
    [(30, 60, 150), (150, 158, 170), (96, 150, 220)],
    [("body", ["prizm_spectrum", "chameleon_galaxy", "prizm_holographic"], "mono", 0),
     ("feature", ["spectrum_diamond_fire", "fs_shattered_prism", "prizm_holographic"], "mono", 1),
     ("accent", ["chrome", "gloss", "candy_chrome"], "base", 2)],
    ["surprise", "random", "anything", "cool", "awesome", "sick", "dope", "wow",
     "amazing", "stunning", "beautiful", "epic", "insane", "crazy", "fire emoji",
     "viral", "trending", "showstopper", "headturner"],
    number=(110, 170, 235), mood="a striking show-stopper when no vibe is given",
    tags=["iridescent", "chrome", "cosmic"],
)


def all_themes() -> List[Dict]:
    """Return the theme list (DEFAULT excluded — it's the fallback only)."""
    return THEMES


def theme_by_name(name: str) -> Dict:
    key = (name or "").strip().lower()
    for t in THEMES:
        if t["name"].lower() == key:
            return t
    return DEFAULT_THEME


__all__ = ["THEMES", "DEFAULT_THEME", "all_themes", "theme_by_name"]
