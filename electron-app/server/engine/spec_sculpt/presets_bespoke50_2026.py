"""Spec Sculpt — 50 BESPOKE designer BLENDS (additive, 2026-06-25, campaign #17).

Not another auto-mirror of single finishes — these are 50 *designed* cross-family material
recipes ("Liquid Obsidian" = poured mercury over black-glass mirror; "Venom Candy" = venom
chameleon flip striped with poison candy). Each one BLENDS 2 already-shipped, resolvable finish
ids, so:
  * every source finish renders for every buyer (they're all in the shipped curated set),
  * the blend produces a genuinely new look no single preset can reach,
  * the spec-sculpt catalog-blend path + iron_fix keep it iRacing-legal.

Validated end-to-end by scripts/specsculpt_preset_audit.py (distinct vs baseline, non-degenerate,
iron-legal). Registered the same proven, guarded, idempotent way as presets_overnight_2026.
"""
from __future__ import annotations

# (slug, label, category, [(finish_id, weight), ...], description, tags)
_BESPOKE_BLENDS = [
    # ---- Designer · Chrome Fusion ----
    ("dz_liquid_obsidian", "Liquid Obsidian", "Designer · Chrome Fusion",
     [("mercury_pool", 0.55), ("gradient_obsidian_mirror", 0.45)],
     "Poured mercury flowing over a black-glass mirror.", ["mercury", "obsidian", "mirror"]),
    ("dz_diamond_mercury", "Diamond Mercury", "Designer · Chrome Fusion",
     [("halo_diamond_chrome", 0.5), ("mercury_pool", 0.5)],
     "Diamond-cut chrome mesh melting into liquid mercury.", ["diamond", "mercury", "chrome"]),
    ("dz_phantom_titanium", "Phantom Titanium", "Designer · Chrome Fusion",
     [("exotic_phantom_mirror", 0.5), ("grad_titanium_vortex", 0.5)],
     "Crystalline phantom facets spun through a titanium vortex.", ["phantom", "titanium", "vortex"]),
    ("dz_mystic_steel", "Mystic Steel", "Designer · Chrome Fusion",
     [("cs_mystichrome", 0.6), ("f_weathering_steel", 0.4)],
     "Color-shift mystic chrome grounded in weathered steel.", ["mystic", "steel", "shift"]),
    ("dz_chrome_carbon_split", "Chrome / Carbon Split", "Designer · Chrome Fusion",
     [("enh_chrome", 0.5), ("enh_carbon_fiber", 0.5)],
     "Mirror chrome interwoven with technical carbon.", ["chrome", "carbon", "split"]),
    ("dz_electric_titanium", "Electric Titanium", "Designer · Chrome Fusion",
     [("electric_arc", 0.45), ("aniso_wave_titanium", 0.55)],
     "Arc-lit electricity riding brushed titanium waves.", ["electric", "titanium", "arc"]),
    ("dz_midnight_pearl_chrome", "Midnight Pearl Chrome", "Designer · Chrome Fusion",
     [("cx_midnight_chrome", 0.55), ("gradient_pearl_chrome", 0.45)],
     "Deep midnight chrome with a chasing pearl bloom.", ["midnight", "pearl", "chrome"]),
    ("dz_brushed_obsidian", "Brushed Obsidian", "Designer · Chrome Fusion",
     [("brushed_metal_fine", 0.5), ("gradient_obsidian_mirror", 0.5)],
     "Fine brushed metal over a black-glass mirror.", ["brushed", "obsidian", "metal"]),

    # ---- Designer · Candy Fusion ----
    ("dz_venom_candy", "Venom Candy", "Designer · Candy Fusion",
     [("chameleon_venom", 0.5), ("cc_candy_poison", 0.5)],
     "Venom chameleon flip striped with poison candy.", ["venom", "candy", "flip"]),
    ("dz_mercury_candy_swirl", "Mercury Candy Swirl", "Designer · Candy Fusion",
     [("mercury_pool", 0.45), ("wave_candy_flow", 0.55)],
     "Liquid mercury swirling through flowing candy.", ["mercury", "candy", "swirl"]),
    ("dz_pearl_poison", "Pearl Poison", "Designer · Candy Fusion",
     [("fd_pearl_chaser", 0.5), ("cc_candy_poison", 0.5)],
     "Chasing pearl shimmer cut with poison candy stripes.", ["pearl", "poison", "candy"]),
    ("dz_cotton_aurora", "Cotton Aurora", "Designer · Candy Fusion",
     [("cx_cotton_candy", 0.55), ("chameleon_aurora", 0.45)],
     "Soft cotton-candy stripes under aurora ribbons.", ["cotton", "aurora", "candy"]),
    ("dz_ghost_candy_glass", "Ghost Candy Glass", "Designer · Candy Fusion",
     [("ghost_waves", 0.5), ("glass_armor", 0.5)],
     "Rolling ghost-pearl waves sealed under glass armor.", ["ghost", "glass", "candy"]),
    ("dz_anodized_inferno", "Anodized Inferno", "Designer · Candy Fusion",
     [("gradient_anodized_gloss", 0.5), ("grad_fire_vortex", 0.5)],
     "Anodized gloss spun into a fire vortex.", ["anodized", "fire", "gloss"]),
    ("dz_frozen_candy_chrome", "Frozen Candy Chrome", "Designer · Candy Fusion",
     [("gradient_candy_frozen", 0.55), ("enh_chrome", 0.45)],
     "Frozen candy gradient flashing to mirror chrome.", ["frozen", "candy", "chrome"]),
    ("dz_marble_pearl_candy", "Marble Pearl Candy", "Designer · Candy Fusion",
     [("pp_marble_flow_pearl", 0.5), ("exotic_inverted_candy", 0.5)],
     "Marble pearl veins flowing through inverted candy.", ["marble", "pearl", "candy"]),

    # ---- Designer · Carbon Fusion ----
    ("dz_forged_mercury", "Forged Mercury", "Designer · Carbon Fusion",
     [("forged_carbon_vis", 0.55), ("mercury_pool", 0.45)],
     "Marbled forged carbon shot through with mercury.", ["forged", "mercury", "carbon"]),
    ("dz_stealth_gold", "Stealth Gold", "Designer · Carbon Fusion",
     [("multiscale_matte_silk", 0.6), ("satin_gold", 0.4)],
     "Deep stealth matte with a warm satin-gold sheen.", ["stealth", "gold", "matte"]),
    ("dz_carbon_venom", "Carbon Venom", "Designer · Carbon Fusion",
     [("enh_carbon_fiber", 0.55), ("chameleon_venom", 0.45)],
     "Carbon weave that flips venom-green at angle.", ["carbon", "venom", "weave"]),
    ("dz_gunmetal_ember", "Gunmetal Ember", "Designer · Carbon Fusion",
     [("gunmetal_satin", 0.6), ("ember", 0.4)],
     "Dark gunmetal satin glowing with buried ember.", ["gunmetal", "ember", "satin"]),
    ("dz_frozen_steel_weave", "Frozen Steel Weave", "Designer · Carbon Fusion",
     [("frozen_matte", 0.5), ("hybrid_weave", 0.5)],
     "Cold frozen matte over a technical hybrid weave.", ["frozen", "steel", "weave"]),
    ("dz_dark_matter_holo", "Dark Matter Holo", "Designer · Carbon Fusion",
     [("dark_matter", 0.6), ("holographic_wrap", 0.4)],
     "Void-dark speckle with a holographic diffraction ghost.", ["dark", "holo", "void"]),
    ("dz_ceramic_chrome_edge", "Ceramic Chrome Edge", "Designer · Carbon Fusion",
     [("ceramic_matte", 0.6), ("efx_spectral_edge", 0.4)],
     "Even ceramic matte rimmed with spectral edge-light.", ["ceramic", "spectral", "edge"]),
    ("dz_acid_carbon_neon", "Acid Carbon Neon", "Designer · Carbon Fusion",
     [("pp_acid_carbon_mesh", 0.55), ("anime_neon_outline", 0.45)],
     "Acid-etched carbon mesh traced in neon outline.", ["acid", "carbon", "neon"]),

    # ---- Designer · Holo Fusion ----
    ("dz_prism_mercury", "Prism Mercury", "Designer · Holo Fusion",
     [("cx_prism_shatter", 0.5), ("mercury_pool", 0.5)],
     "Shattered prism facets pooling into mercury.", ["prism", "mercury", "shatter"]),
    ("dz_oilslick_obsidian", "Oilslick Obsidian", "Designer · Holo Fusion",
     [("spectrum_oilfilm_rain", 0.55), ("gradient_obsidian_mirror", 0.45)],
     "Oil-slick iridescence on a black-glass mirror.", ["oil", "obsidian", "iridescent"]),
    ("dz_venom_aurora", "Venom Aurora", "Designer · Holo Fusion",
     [("chameleon_venom", 0.5), ("chameleon_aurora", 0.5)],
     "Venom flip braided with aurora ribbons.", ["venom", "aurora", "flip"]),
    ("dz_spectral_gold", "Spectral Gold", "Designer · Holo Fusion",
     [("spectral_rainbow_metal", 0.55), ("cs_gunmetal_gold", 0.45)],
     "Rainbow-metal spectral flow shifting to gold.", ["spectral", "gold", "rainbow"]),
    ("dz_black_ice_holo", "Black Ice Holo", "Designer · Holo Fusion",
     [("cx_black_ice", 0.55), ("holographic_wrap", 0.45)],
     "Black-ice depth under a holographic sheen.", ["black", "ice", "holo"]),
    ("dz_rose_prism", "Rose Prism", "Designer · Holo Fusion",
     [("cx_rose_chrome", 0.55), ("cx_prism_shatter", 0.45)],
     "Rose chrome fracturing into prism shards.", ["rose", "prism", "chrome"]),
    ("dz_emerald_oilslick", "Emerald Oilslick", "Designer · Holo Fusion",
     [("chameleon_emerald", 0.5), ("spectrum_rainbow_river", 0.5)],
     "Emerald chameleon riding an oil-slick river.", ["emerald", "oil", "flip"]),
    ("dz_galaxy_diffraction", "Galaxy Diffraction", "Designer · Holo Fusion",
     [("chameleon_galaxy", 0.5), ("spectral_dark_light", 0.5)],
     "Galaxy chameleon split by spectral diffraction rings.", ["galaxy", "spectral", "flip"]),
    ("dz_hyperflip_mono", "Hyperflip Mono", "Designer · Holo Fusion",
     [("cx_hyperflip_electric_blue_copper", 0.55), ("spectral_mono_chrome", 0.45)],
     "Electric blue-copper hyperflip over mono diffraction.", ["hyperflip", "mono", "blue"]),

    # ---- Designer · Glow Fusion ----
    ("dz_copper_inferno", "Copper Inferno", "Designer · Glow Fusion",
     [("grad_copper_flame", 0.55), ("molten_metal", 0.45)],
     "Copper flame waves over molten metal flow.", ["copper", "molten", "fire"]),
    ("dz_neon_ice", "Neon Ice", "Designer · Glow Fusion",
     [("living_neon_equalizer", 0.5), ("spectrum_borealis_ice", 0.5)],
     "Neon equalizer bars frozen in borealis ice.", ["neon", "ice", "glow"]),
    ("dz_tesla_obsidian", "Tesla Obsidian", "Designer · Glow Fusion",
     [("tesla_coil", 0.5), ("gradient_obsidian_mirror", 0.5)],
     "Tesla arcs crawling over a black-glass mirror.", ["tesla", "obsidian", "electric"]),
    ("dz_blackbody_gold", "Blackbody Gold", "Designer · Glow Fusion",
     [("blackbody", 0.55), ("grad_midnight_gold", 0.45)],
     "Blackbody heat-glow bleeding into midnight gold.", ["blackbody", "gold", "glow"]),
    ("dz_wormhole_chrome", "Wormhole Chrome", "Designer · Glow Fusion",
     [("wormhole", 0.55), ("enh_chrome", 0.45)],
     "A wormhole pull warping a mirror-chrome shell.", ["wormhole", "chrome", "warp"]),
    ("dz_prizm_inferno", "Prizm Inferno", "Designer · Glow Fusion",
     [("prizm_neon", 0.5), ("grad_fire_vortex", 0.5)],
     "Prismatic neon spun into a fire vortex.", ["prizm", "fire", "neon"]),
    ("dz_electric_mercury", "Electric Mercury", "Designer · Glow Fusion",
     [("living_electric_current", 0.5), ("mercury_pool", 0.5)],
     "Living electric current arcing across liquid mercury.", ["electric", "mercury", "current"]),
    ("dz_rose_gold_glow", "Rose Gold Glow", "Designer · Glow Fusion",
     [("grad_rose_gold_h", 0.55), ("molten_metal", 0.45)],
     "Soft rose gold warmed by a molten core.", ["rose", "gold", "molten"]),
    ("dz_aurora_steel", "Aurora Steel", "Designer · Glow Fusion",
     [("spectrum_borealis_ice", 0.55), ("f_weathering_steel", 0.45)],
     "Aurora ribbons drifting over weathered steel.", ["aurora", "steel", "ribbon"]),

    # ---- Designer · Wild Fusion ----
    ("dz_chaos_chrome", "Chaos Chrome", "Designer · Wild Fusion",
     [("quilt_random_chaos", 0.5), ("enh_chrome", 0.5)],
     "Multicolor chaos flake erupting through chrome.", ["chaos", "chrome", "flake"]),
    ("dz_hex_holo", "Hex Holo", "Designer · Wild Fusion",
     [("quilt_hex_variety", 0.5), ("holographic_wrap", 0.5)],
     "Hex-cell flake under holographic diffraction.", ["hex", "holo", "flake"]),
    ("dz_galaxy_flake_candy", "Galaxy Flake Candy", "Designer · Wild Fusion",
     [("sparkle_galaxy", 0.5), ("wave_candy_flow", 0.5)],
     "Galaxy sparkle drifting through flowing candy.", ["galaxy", "candy", "sparkle"]),
    ("dz_diamond_dust_obsidian", "Diamond Dust Obsidian", "Designer · Wild Fusion",
     [("sparkle_diamond_dust", 0.5), ("gradient_obsidian_mirror", 0.5)],
     "Diamond-dust sparkle scattered on black glass.", ["diamond", "obsidian", "sparkle"]),
    ("dz_constellation_venom", "Constellation Venom", "Designer · Wild Fusion",
     [("sparkle_constellation", 0.5), ("chameleon_venom", 0.5)],
     "Constellation pinpoints over a venom flip.", ["constellation", "venom", "sparkle"]),
    ("dz_ice_flake_chrome", "Ice Flake Chrome", "Designer · Wild Fusion",
     [("blue_ice_flake", 0.55), ("enh_chrome", 0.45)],
     "Cool blue ice flake set in mirror chrome.", ["ice", "chrome", "flake"]),
    ("dz_mosaic_mercury", "Mosaic Mercury", "Designer · Wild Fusion",
     [("quilt_chrome_mosaic", 0.5), ("mercury_pool", 0.5)],
     "Chrome mosaic shards dissolving into mercury.", ["mosaic", "mercury", "chrome"]),
    ("dz_firefly_candy_glass", "Firefly Candy Glass", "Designer · Wild Fusion",
     [("sparkle_firefly", 0.5), ("glass_armor", 0.5)],
     "Firefly sparks suspended in candy glass.", ["firefly", "glass", "candy"]),
]

_registered = False
_count = 0


def register(verify_resolve: bool = False) -> int:
    """Append the 50 bespoke designer blends to SPEC_SCULPT_PRESETS. Idempotent + guarded.

    Only adds a blend whose every source finish id is already used by the shipped curated set
    (so it is guaranteed resolvable for every buyer). Rebuilds the derived lookups. Returns added.
    """
    global _registered, _count
    if _registered:
        return _count
    import engine.spec_sculpt.presets as P

    existing_slugs = {str(p["id"]) for p in P.SPEC_SCULPT_PRESETS}
    shipped_finishes = {fid for pr in P.SPEC_SCULPT_PRESETS for fid, _ in pr["catalog"]}

    added = 0
    for slug, label, category, blend, desc, tags in _BESPOKE_BLENDS:
        if slug in existing_slugs:
            continue
        # Safety: every source finish must already ship (resolvable for all buyers).
        if not all(fid in shipped_finishes for fid, _ in blend):
            continue
        P.SPEC_SCULPT_PRESETS.append(P._p(slug, label, category, blend, desc, tags))
        existing_slugs.add(slug)
        added += 1

    P.VALID_SPEC_SCULPT_PRESET_IDS = frozenset(str(p["id"]) for p in P.SPEC_SCULPT_PRESETS)
    P.PRESET_CATALOG_BY_ID = {str(p["id"]): list(p["catalog"]) for p in P.SPEC_SCULPT_PRESETS}
    P.PRESET_TILE_BY_ID = {
        str(p["id"]): float(P.PRESET_TILE_OVERRIDE.get(str(p["id"]), 1.0)) for p in P.SPEC_SCULPT_PRESETS
    }
    _registered = True
    _count = added
    return added
