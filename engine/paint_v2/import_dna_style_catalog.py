"""Import DNA style catalog — 75 bake personalities for SHOKK DROP (SPB-109).

Each style maps to Viva spec_personality knobs (kind, metal/rough/clear bases, flake, line).
Passed as the `style` argument to make_spec_plate; style id also appears in semantic routing text.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# kind ∈ sun | muertos | tile | glyph | water | neon | woven | organic | festival
_P = Tuple[str, float, float, float, float, float]  # kind, metal_base, rough_base, clear_base, flake, line


def _entry(style_id: str, desc: str, profile: _P) -> None:
    DNA_STYLE_DESCRIPTIONS[style_id] = desc
    k, mb, rb, cb, fl, ln = profile
    STYLE_PERSONALITY[style_id] = {
        "kind": k,
        "metal_base": mb,
        "rough_base": rb,
        "clear_base": cb,
        "flake": fl,
        "line": ln,
    }


DNA_STYLE_DESCRIPTIONS: Dict[str, str] = {}
STYLE_PERSONALITY: Dict[str, dict] = {}

# ── Original 10 (tuned) ──
_entry("halftone_hex", "Fine hex halftone — comic screen-tone shimmer", ("tile", 40, 82, 72, 1.15, 1.38))
_entry("casino_neon", "Neon casino glass — high metallic pops, glossy CC", ("neon", 68, 54, 74, 1.32, 1.30))
_entry("grunge_scratch", "Scratched distress — worn edges, roughness ridges", ("muertos", 50, 118, 42, 1.08, 1.40))
_entry("abstract_gradient", "Smooth gradient flow — gallery-art friendly", ("water", 32, 70, 78, 0.95, 1.12))
_entry("punk_checker", "Punk checker grit — bold contrast blocks", ("tile", 44, 90, 58, 1.10, 1.35))
_entry("worn_rust", "Worn rust & leather — deep roughness, aged patina", ("muertos", 44, 132, 28, 1.05, 1.40))
_entry("disco_glitter", "Disco holo glitter — mirror flecks, peak CC", ("neon", 72, 48, 82, 1.45, 1.28))
_entry("comic_pop", "Comic pop ink — thick edges, halftone accents", ("glyph", 52, 88, 54, 1.12, 1.42))
_entry("acid_wash", "Acid wash tie-dye — psychedelic M/CC swirl", ("water", 38, 76, 80, 1.18, 1.15))
_entry("metal_flake", "Metal flake & carbon — fine automotive sparkle", ("glyph", 62, 72, 58, 1.28, 1.35))

# ── Neon / electric (8) ──
_entry("electric_storm", "Electric storm — cyan-violet arcs, hot metallic veins", ("neon", 78, 42, 88, 1.42, 1.38))
_entry("plasma_edge", "Plasma rim light — edge-only neon corridors", ("neon", 82, 50, 90, 1.38, 1.45))
_entry("laser_grid", "Laser grid — scan lines + mirror CC strips", ("neon", 70, 46, 86, 1.35, 1.32))
_entry("cyber_magenta", "Cyber magenta — saturated holo pink metal", ("neon", 76, 44, 84, 1.40, 1.30))
_entry("toxic_lime", "Toxic lime — acid green gloss over dark rough", ("neon", 64, 58, 76, 1.30, 1.28))
_entry("arcade_gold", "Arcade gold — cabinet chrome + candy clear", ("sun", 74, 52, 80, 1.36, 1.26))
_entry("blacklight_ink", "Blacklight ink — UV reactive edge bloom", ("neon", 80, 48, 92, 1.44, 1.40))
_entry("sign_neon", "Sign neon — tube-glow metallic outlines", ("neon", 66, 56, 78, 1.28, 1.34))

# ── Holo / glitter / chrome (8) ──
_entry("holo_prism", "Holo prism — rainbow micro-facet CC chaos", ("neon", 74, 46, 94, 1.48, 1.22))
_entry("mirror_chrome", "Mirror chrome — near-255 metallic peaks", ("neon", 88, 36, 88, 1.40, 1.20))
_entry("oil_slick", "Oil slick — iridescent CC shift bands", ("water", 58, 54, 90, 1.38, 1.18))
_entry("diamond_dust", "Diamond dust — pin sparkle on satin clear", ("neon", 76, 50, 86, 1.46, 1.24))
_entry("foil_teal", "Foil teal — cool metallic leafing", ("water", 64, 48, 82, 1.32, 1.26))
_entry("rose_gold_flake", "Rose gold flake — warm pink metal grain", ("sun", 68, 56, 76, 1.34, 1.28))
_entry("champagne_spark", "Champagne spark — soft gold dust clear", ("sun", 62, 58, 84, 1.30, 1.22))
_entry("spectra_flake", "Spectra flake — multi-hue automotive sparkle", ("glyph", 70, 52, 80, 1.42, 1.30))

# ── Grunge / distress (8) ──
_entry("battle_worn", "Battle worn — chipped paint, exposed rough", ("muertos", 48, 128, 32, 1.02, 1.42))
_entry("salt_corrosion", "Salt corrosion — coastal matte + pitting", ("organic", 42, 122, 36, 0.98, 1.36))
_entry("asphalt_grit", "Asphalt grit — coarse R, low satin", ("muertos", 46, 130, 28, 1.00, 1.38))
_entry("scratch_mosaic", "Scratch mosaic — crossed micro-gouges", ("muertos", 52, 120, 38, 1.06, 1.44))
_entry("patina_bronze", "Patina bronze — oxidized green/brown rough", ("organic", 50, 118, 40, 1.04, 1.32))
_entry("desert_sun_bake", "Desert sun bake — faded clear, chalky R", ("sun", 40, 110, 44, 0.96, 1.28))
_entry("tar_and_feather", "Tar and feather — deep void, rim tar silk", ("muertos", 38, 134, 26, 1.00, 1.40))
_entry("distress_denim", "Distress denim — woven rough, soft metal", ("woven", 36, 116, 42, 0.94, 1.26))

# ── Pattern / tile / halftone (8) ──
_entry("micro_hex", "Micro hex — tight 8px cells, high CC", ("tile", 42, 78, 76, 1.18, 1.40))
_entry("carbon_weave", "Carbon weave — 12px twill, aniso metal", ("tile", 58, 68, 62, 1.26, 1.42))
_entry("diamond_plate", "Diamond plate — industrial tread highlights", ("tile", 56, 74, 58, 1.14, 1.36))
_entry("woven_mesh", "Woven mesh — grille metal rhythm", ("woven", 48, 82, 64, 1.10, 1.34))
_entry("dot_matrix", "Dot matrix — LED halftone shimmer", ("tile", 46, 80, 70, 1.16, 1.32))
_entry("circuit_trace", "Circuit trace — PCB fine lines + pads", ("glyph", 54, 76, 68, 1.20, 1.44))
_entry("stained_glass", "Stained glass — bold grout, jewel clear", ("tile", 50, 72, 82, 1.12, 1.38))
_entry("argyle_gloss", "Argyle gloss — rhombus satin corridors", ("woven", 44, 84, 66, 1.08, 1.30))

# ── Organic / water / nature (6) ──
_entry("river_pearl", "River pearl — flowing satin CC", ("water", 34, 64, 84, 1.02, 1.14))
_entry("moss_matte", "Moss matte — organic rough, low metal", ("organic", 30, 126, 38, 0.88, 1.08))
_entry("lava_glass", "Lava glass — dark rough, hot rim metal", ("sun", 58, 96, 52, 1.22, 1.36))
_entry("frost_crystal", "Frost crystal — icy clear, crisp micro edge", ("water", 36, 88, 72, 1.08, 1.20))
_entry("volcanic_obsidian", "Volcanic obsidian — glassy CC, void rough", ("organic", 52, 104, 48, 1.14, 1.32))
_entry("aurora_veil", "Aurora veil — soft shifting clear bands", ("water", 40, 62, 88, 1.16, 1.16))

# ── Sun / warm / festival (5) ──
_entry("solar_flare", "Solar flare — radial hot metal + sun clear", ("sun", 70, 58, 78, 1.32, 1.18))
_entry("copper_fire", "Copper fire — warm metal, low clear", ("sun", 64, 72, 56, 1.24, 1.30))
_entry("marigold_gloss", "Marigold gloss — festival gold satin", ("sun", 60, 66, 74, 1.20, 1.14))
_entry("ember_silk", "Ember silk — coal rough, ember edge metal", ("sun", 56, 90, 62, 1.18, 1.34))
_entry("candy_clear", "Candy clear — wet clearcoat, punchy metal", ("neon", 58, 54, 86, 1.26, 1.22))

# ── Glyph / tribal / graphic (5) ──
_entry("tribal_chrome", "Tribal chrome — bold glyph trace metal", ("glyph", 60, 70, 60, 1.24, 1.46))
_entry("serpent_scale", "Serpent scale — scale lattice rim accent", ("glyph", 58, 76, 64, 1.22, 1.40))
_entry("lightning_splice", "Lightning splice — forked edge metal", ("glyph", 66, 68, 58, 1.28, 1.42))
_entry("ink_wash", "Ink wash — brush edge, matte fill", ("glyph", 42, 94, 50, 1.06, 1.38))
_entry("razor_stripe", "Razor stripe — anisotropic stripe metal", ("glyph", 62, 74, 56, 1.20, 1.44))

# ── SPB-109 expansion to 75 — elevated variety for World / INSANE quads ──
_entry("neon_vein", "Neon vein — capillary glow under dark rough", ("neon", 74, 52, 90, 1.36, 1.42))
_entry("cryo_shard", "Cryo shard — ice facet CC with crisp micro edge", ("water", 38, 86, 78, 1.14, 1.24))
_entry("magma_crackle", "Magma crackle — heat rim metal over char rough", ("sun", 66, 102, 48, 1.26, 1.38))
_entry("pewter_dust", "Pewter dust — soft satin metal, chalk rough", ("organic", 46, 108, 44, 1.02, 1.18))
_entry("prism_shard", "Prism shard — shattered holo CC chips", ("neon", 80, 44, 96, 1.50, 1.26))
_entry("velvet_void", "Velvet void — deep matte with rare rim pin", ("muertos", 34, 136, 30, 0.92, 1.16))
_entry("riot_paint", "Riot paint — chaotic graphic edge metal", ("glyph", 64, 78, 62, 1.30, 1.48))
_entry("barcode_rush", "Barcode rush — vertical scan stripe metal", ("tile", 52, 70, 68, 1.22, 1.40))
_entry("coral_mist", "Coral mist — warm pearl clear haze", ("water", 42, 58, 86, 1.10, 1.12))
_entry("static_bloom", "Static bloom — TV snow sparkle on satin", ("neon", 70, 56, 84, 1.34, 1.32))
_entry("gunmetal_haze", "Gunmetal haze — blue-gray metal fog", ("glyph", 72, 64, 54, 1.24, 1.36))
_entry("jelly_iridescent", "Jelly iridescent — wet candy CC shift", ("neon", 56, 48, 92, 1.38, 1.20))
_entry("scarlet_glaze", "Scarlet glaze — red candy clear corridors", ("sun", 62, 60, 80, 1.28, 1.24))
_entry("cobalt_thread", "Cobalt thread — fine blue weave trace", ("woven", 48, 74, 70, 1.16, 1.38))
_entry("zenith_burst", "Zenith burst — radial sun clear explosion", ("sun", 76, 54, 88, 1.32, 1.16))
_entry("rag_doll_chrome", "Rag doll chrome — patchwork satin islands", ("woven", 50, 88, 66, 1.12, 1.30))
_entry("holo_serpent", "Holo serpent — scale holo rim corridors", ("glyph", 68, 62, 88, 1.44, 1.44))

DNA_STYLES: Tuple[str, ...] = tuple(DNA_STYLE_DESCRIPTIONS.keys())

WORLD_SLOT_STANDARD = 8
WORLD_SLOT_REMIX = 7
WORLD_SLOT_INSANE = 5
WORLD_VARIANT_COUNT = WORLD_SLOT_STANDARD + WORLD_SLOT_REMIX + WORLD_SLOT_INSANE

# Spread remix partners by kind family
_KIND_NEIGHBORS: Dict[str, List[str]] = {
    "neon": ["disco_glitter", "electric_storm", "holo_prism", "cyber_magenta", "blacklight_ink"],
    "sun": ["solar_flare", "copper_fire", "arcade_gold", "marigold_gloss", "ember_silk"],
    "muertos": ["grunge_scratch", "battle_worn", "worn_rust", "scratch_mosaic", "asphalt_grit"],
    "tile": ["halftone_hex", "micro_hex", "carbon_weave", "diamond_plate", "stained_glass"],
    "water": ["abstract_gradient", "river_pearl", "aurora_veil", "oil_slick", "frost_crystal"],
    "glyph": ["metal_flake", "tribal_chrome", "serpent_scale", "lightning_splice", "comic_pop"],
    "woven": ["woven_mesh", "distress_denim", "argyle_gloss", "punk_checker"],
    "organic": ["moss_matte", "volcanic_obsidian", "patina_bronze", "salt_corrosion"],
    "festival": ["candy_clear", "champagne_spark", "acid_wash"],
}


def remix_partners_for(style: str) -> List[str]:
    prof = STYLE_PERSONALITY.get(style, {})
    kind = str(prof.get("kind", "festival"))
    seeds = list(_KIND_NEIGHBORS.get(kind, []))
    for sid in DNA_STYLES:
        if sid != style and sid not in seeds:
            seeds.append(sid)
    return seeds


# Styles that get chromatic exotic amp (multi-tier M/R/CC cells, paint-hue keyed).
EXOTIC_STYLE_IDS: Tuple[str, ...] = (
    "disco_glitter",
    "holo_prism",
    "electric_storm",
    "acid_wash",
    "blacklight_ink",
    "oil_slick",
    "spectra_flake",
    "aurora_veil",
    "cyber_magenta",
    "plasma_edge",
    "candy_clear",
    "sign_neon",
    "casino_neon",
    "laser_grid",
    "toxic_lime",
    "diamond_dust",
    "mirror_chrome",
    "volcanic_obsidian",
    "lightning_splice",
    "serpent_scale",
    "prism_shard",
    "neon_vein",
    "holo_serpent",
    "static_bloom",
    "jelly_iridescent",
    "zenith_burst",
)

# Accent bias for exotic edge corridors (M,R,CC channel nudges — preview reads as color).
STYLE_EXOTIC_ACCENT: Dict[str, Tuple[int, int, int]] = {
    "disco_glitter": (255, 60, 220),
    "electric_storm": (60, 210, 255),
    "holo_prism": (180, 255, 120),
    "acid_wash": (255, 140, 40),
    "cyber_magenta": (255, 20, 180),
    "plasma_edge": (255, 80, 255),
    "blacklight_ink": (120, 255, 80),
    "oil_slick": (80, 255, 200),
    "spectra_flake": (255, 200, 80),
    "aurora_veil": (100, 255, 180),
    "serpent_scale": (255, 90, 60),
    "lightning_splice": (255, 240, 100),
    "casino_neon": (255, 180, 60),
    "toxic_lime": (180, 255, 60),
    "mirror_chrome": (220, 240, 255),
    "prism_shard": (200, 120, 255),
    "neon_vein": (255, 100, 180),
    "holo_serpent": (140, 255, 200),
    "static_bloom": (220, 220, 255),
    "magma_crackle": (255, 120, 40),
    "cryo_shard": (100, 200, 255),
}


# ── SPB-109 spec chroma (owner mandate 2026-05-28): wide color gamut IN the spec map ──
# The spec preview maps channels M->Red, R(oughness)->Green, CC(learcoat)->Blue. The old
# amp ramped M & CC together (and R inverse) => every finish collapsed to magenta/green.
# These "inks" are decorrelated (M,R,CC) targets that each read as a distinct, physically
# valid material state, so a single spec map can span the FULL spectrum with many shades.
#   red/orange/amber/gold/copper = warm polished->satin metal (high M, low/mid R, low CC)
#   yellow/lime                  = rough metallic (high M + high R)
#   green/emerald                = matte dielectric/metal mix
#   teal/cyan/sky/blue/indigo    = clearcoat-dominant gloss (high CC)
#   violet/purple/magenta/pink   = metal + clearcoat candy flake (high M + high CC)
#   chrome/steel/white/char/ink  = neutral material anchors
SPEC_INKS: Dict[str, Tuple[int, int, int]] = {
    "red": (236, 54, 46),
    "orange": (242, 140, 46),
    "amber": (236, 176, 56),
    "yellow": (228, 222, 62),
    "lime": (150, 226, 60),
    "green": (64, 210, 82),
    "emerald": (56, 196, 132),
    "teal": (52, 196, 196),
    "cyan": (70, 206, 232),
    "sky": (80, 150, 236),
    "blue": (58, 92, 236),
    "indigo": (96, 72, 226),
    "violet": (150, 72, 230),
    "purple": (190, 70, 226),
    "magenta": (236, 64, 196),
    "pink": (240, 120, 178),
    "rose": (236, 110, 130),
    "gold": (228, 168, 74),
    "copper": (210, 120, 66),
    "chrome": (196, 206, 222),
    "steel": (120, 132, 156),
    "char": (60, 70, 86),
    "white": (240, 238, 244),
    "ink": (40, 52, 70),
}

_RAINBOW = ["red", "orange", "yellow", "green", "cyan", "blue", "violet", "magenta"]

# Each style claims a band (or full sweep) of the spectrum. First ink is the anchor.
STYLE_SPEC_PALETTE: Dict[str, List[str]] = {
    # Original 10
    "halftone_hex": ["sky", "cyan", "magenta", "white"],
    "casino_neon": ["red", "orange", "gold", "magenta"],
    "grunge_scratch": ["copper", "amber", "steel", "char"],
    "abstract_gradient": ["indigo", "violet", "sky", "teal"],
    "punk_checker": ["red", "magenta", "yellow", "ink"],
    "worn_rust": ["copper", "orange", "amber", "char"],
    "disco_glitter": ["magenta", "cyan", "lime", "gold", "violet", "red"],
    "comic_pop": ["yellow", "red", "blue", "magenta"],
    "acid_wash": ["lime", "cyan", "violet", "magenta", "amber"],
    "metal_flake": ["steel", "chrome", "sky", "violet"],
    # Neon
    "electric_storm": ["cyan", "sky", "violet", "white"],
    "plasma_edge": ["violet", "magenta", "pink", "blue"],
    "laser_grid": ["emerald", "cyan", "lime", "white"],
    "cyber_magenta": ["magenta", "pink", "violet", "red"],
    "toxic_lime": ["lime", "green", "yellow", "cyan"],
    "arcade_gold": ["gold", "amber", "orange", "yellow"],
    "blacklight_ink": ["violet", "indigo", "magenta", "lime"],
    "sign_neon": ["pink", "magenta", "cyan", "red"],
    # Holo / chrome
    "holo_prism": list(_RAINBOW),
    "mirror_chrome": ["chrome", "white", "sky", "steel"],
    "oil_slick": ["teal", "violet", "magenta", "gold", "blue", "emerald"],
    "diamond_dust": ["white", "sky", "cyan", "chrome"],
    "foil_teal": ["teal", "cyan", "emerald", "sky"],
    "rose_gold_flake": ["rose", "pink", "gold", "copper"],
    "champagne_spark": ["gold", "amber", "yellow", "white"],
    "spectra_flake": ["red", "orange", "yellow", "green", "cyan", "violet"],
    # Grunge
    "battle_worn": ["copper", "amber", "steel", "char"],
    "salt_corrosion": ["teal", "emerald", "steel", "char"],
    "asphalt_grit": ["steel", "char", "ink", "sky"],
    "scratch_mosaic": ["copper", "steel", "amber", "char"],
    "patina_bronze": ["emerald", "green", "copper", "char"],
    "desert_sun_bake": ["amber", "gold", "orange", "char"],
    "tar_and_feather": ["ink", "char", "steel", "violet"],
    "distress_denim": ["blue", "sky", "indigo", "steel"],
    # Pattern / tile
    "micro_hex": ["cyan", "teal", "sky", "emerald"],
    "carbon_weave": ["steel", "char", "sky", "chrome"],
    "diamond_plate": ["steel", "chrome", "sky", "char"],
    "woven_mesh": ["steel", "teal", "sky", "char"],
    "dot_matrix": ["green", "lime", "emerald", "yellow"],
    "circuit_trace": ["emerald", "green", "cyan", "gold"],
    "stained_glass": ["red", "blue", "gold", "green", "violet"],
    "argyle_gloss": ["violet", "purple", "magenta", "sky"],
    # Organic / water
    "river_pearl": ["teal", "sky", "white", "violet"],
    "moss_matte": ["green", "emerald", "char", "amber"],
    "lava_glass": ["red", "orange", "amber", "char"],
    "frost_crystal": ["cyan", "sky", "white", "teal"],
    "volcanic_obsidian": ["ink", "char", "violet", "steel"],
    "aurora_veil": ["emerald", "teal", "violet", "sky"],
    # Sun / warm
    "solar_flare": ["amber", "gold", "orange", "yellow"],
    "copper_fire": ["copper", "orange", "amber", "red"],
    "marigold_gloss": ["gold", "amber", "yellow", "orange"],
    "ember_silk": ["red", "orange", "copper", "char"],
    "candy_clear": ["red", "magenta", "rose", "orange"],
    # Glyph / tribal
    "tribal_chrome": ["chrome", "steel", "sky", "white"],
    "serpent_scale": ["emerald", "green", "lime", "gold"],
    "lightning_splice": ["yellow", "amber", "white", "cyan"],
    "ink_wash": ["ink", "char", "steel", "sky"],
    "razor_stripe": ["chrome", "steel", "white", "sky"],
    # Expansion 17
    "neon_vein": ["magenta", "pink", "red", "violet"],
    "cryo_shard": ["cyan", "sky", "white", "teal"],
    "magma_crackle": ["red", "orange", "amber", "char"],
    "pewter_dust": ["steel", "chrome", "char", "sky"],
    "prism_shard": ["violet", "blue", "cyan", "emerald", "magenta", "gold"],
    "velvet_void": ["ink", "violet", "char", "purple"],
    "riot_paint": ["red", "yellow", "blue", "magenta", "green"],
    "barcode_rush": ["white", "ink", "steel", "chrome"],
    "coral_mist": ["rose", "pink", "orange", "gold"],
    "static_bloom": ["white", "sky", "steel", "cyan"],
    "gunmetal_haze": ["steel", "sky", "blue", "char"],
    "jelly_iridescent": ["magenta", "pink", "cyan", "violet", "gold"],
    "scarlet_glaze": ["red", "rose", "orange", "magenta"],
    "cobalt_thread": ["blue", "indigo", "sky", "teal"],
    "zenith_burst": ["gold", "amber", "yellow", "orange"],
    "rag_doll_chrome": ["chrome", "steel", "sky", "white"],
    "holo_serpent": ["emerald", "lime", "gold", "teal", "violet"],
}


def spec_palette_for(style: str) -> List[Tuple[int, int, int]]:
    """Return the (M,R,CC) ink anchors for a style's spec gamut (anchor-first)."""
    names = STYLE_SPEC_PALETTE.get(style)
    if not names:
        names = list(_RAINBOW)
    return [SPEC_INKS[n] for n in names if n in SPEC_INKS]


def spec_palette_weights(count: int) -> List[float]:
    """Anchor-weighted distribution (first inks dominate, all stay present)."""
    if count <= 0:
        return []
    raw = [max(0.55, 1.5 - i * 0.18) for i in range(count)]
    total = sum(raw)
    return [w / total for w in raw]


def pick_diverse_pairs(
    auto: str,
    count: int,
    *,
    seed: int = 0,
) -> List[Tuple[str, str, float]]:
    """Pick `count` remix pairs — cross-catalog, not all anchored on Auto style."""
    import random

    rng = random.Random(seed)
    pool = spread_styles_excluding(auto, min(28, len(DNA_STYLES) - 1), prefer_exotic=10, seed=seed ^ 0xA11FE)
    if len(pool) < count + 2:
        pool = [s for s in DNA_STYLES if s != auto]
        rng.shuffle(pool)
    pairs: List[Tuple[str, str, float]] = []
    seen: set = set()
    attempts = 0
    while len(pairs) < count and attempts < count * 40:
        attempts += 1
        i = len(pairs)
        a = pool[i % len(pool)]
        b = pool[(i + max(3, count // 2) + attempts) % len(pool)]
        if a == b:
            continue
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        t = round(0.28 + rng.random() * 0.44, 2)
        pairs.append((a, b, t))
    return pairs[:count]


def pick_insane_quads(count: int, *, seed: int = 0) -> List[Tuple[List[str], List[float]]]:
    """Pick `count` random 4-style blends with normalized weights (reproducible via seed)."""
    import random

    rng = random.Random(seed)
    pool = list(DNA_STYLES)
    out: List[Tuple[List[str], List[float]]] = []
    seen: set = set()
    while len(out) < count:
        quad = tuple(sorted(rng.sample(pool, 4)))
        if quad in seen:
            continue
        seen.add(quad)
        raw = [rng.random() + 0.08 for _ in quad]
        total = sum(raw)
        weights = [round(w / total, 3) for w in raw]
        out.append((list(quad), weights))
    return out


def is_exotic_style(style_id: str) -> bool:
    return style_id in EXOTIC_STYLE_IDS


def spread_styles_excluding(
    auto: str,
    count: int,
    *,
    prefer_exotic: int = 0,
    seed: int = 0,
) -> List[str]:
    """Pick `count` styles; `seed` shuffles catalog so runs differ per session."""
    import random

    rng = random.Random(seed)
    exotic_pool = [s for s in EXOTIC_STYLE_IDS if s != auto and s in DNA_STYLES]
    general_pool = [s for s in DNA_STYLES if s != auto and s not in exotic_pool]
    rng.shuffle(exotic_pool)
    rng.shuffle(general_pool)
    out: List[str] = []
    if prefer_exotic > 0 and exotic_pool:
        for i in range(min(prefer_exotic, count)):
            pick = exotic_pool[i % len(exotic_pool)]
            if pick not in out:
                out.append(pick)
    remaining = count - len(out)
    if remaining > 0:
        pool = general_pool + [s for s in exotic_pool if s not in out]
        rng.shuffle(pool)
        for pick in pool:
            if len(out) >= count:
                break
            if pick not in out:
                out.append(pick)
    return out[:count]
