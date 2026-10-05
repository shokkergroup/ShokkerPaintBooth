# -*- coding: utf-8 -*-
"""FRACTURED ELEMENTS — one hand-authored material story per finish.

Owner 2026-08-31/09-01: *"the damn finishes and spec maps for MANY of them are
repeats, totally the same just slightly recolored. The specs are EXACTLY the
same. HOW COULD YOU DO THIS?"* — and he was exactly right. The shelf shipped 60
finishes with the spec deck attached to the CHAPTER instead of the finish:

    rain 12 finishes -> 1 deck      water 12 -> 1 deck
    frozen 12 -> 1 deck            dry 12 -> 1 deck
    storm 12 -> 1 deck

with **zero** per-finish spec overrides. Measured: story_ratio 0.30, one group
of twelve finishes dealing an identical material set, 60/60 failing the law.

The PAINT was never the problem — the structure stacks are genuinely varied
(streak+drops, dendrite+flakes, funnel+crest+cells, polygons+crack). So this
module fixes what was actually broken: every finish gets its own deck, chosen by
reading its own description, and the spec is composed against the RENDERED PAINT
so its material boundaries land on the artwork's own tonal boundaries.

The owner's rule for choosing cards: *"If it says MINERAL: CHALK CHROME then by
GOD it should make you instantly feel like this finish IS chalk chrome."* So a
finish about standing water gets liquid glaze and mercury; one about a dry lake
crust gets ceramic and bead-blast; hail damage gets dented galvanised metal.

Decks are ordered roughness-DESCENDING by spec_story, so the darkest part of
each artwork takes the deadest material and the highlights take the sharpest.
"""
from __future__ import annotations

# fid -> (deck, edge_card, spec_kwargs)
#
# `bands="linear"` is set on finishes whose artwork is mostly background by area
# — filament, dendrite and spark fields — where equal-population quantile bands
# would slice the background six ways and give the actual structure one card.
DECKS = {
    # ═══ 🌧 RAIN — falling and landed water ════════════════════════════════
    # "rain hard enough to be a surface of its own" — it IS the wet surface
    "elm_downpour":     (("void", "satin", "gloss", "wet", "liquid_glaze", "chrome"), "chrome", {}),
    # every drop landing at once: a whole sheet of water over a dead ground
    "elm_cloudburst":   (("matte", "semi_gloss", "gloss", "wet", "liquid_glaze"), "mercury", {}),
    # "too fine to hear" — nothing sharp anywhere, all soft sheen
    "elm_drizzle":      (("eggshell", "satin", "soft_gloss", "semi_gloss", "milk_glass"), "soft_gloss", {}),
    # wind-driven, near-horizontal: hard streaks of water on a slate ground
    "elm_sheet_rain":   (("satin_carbon", "gloss_carbon", "gloss", "wet", "chrome"), "chrome", {}),
    # a season, not a shower: warm heavy rain, deep gloss
    "elm_monsoon":      (("flat_black", "satin", "gloss", "wet", "liquid_glaze", "candy"), "candy_chrome", {}),
    # rain that ETCHES — pits, oxide, blasted metal
    "elm_acid_rain":    (("patina", "bead_blast", "powder", "galvanized", "wet"), "antique_chrome", {}),
    # standing water with wind fretting it: the glassiest deck on the shelf
    "elm_puddle_skin":  (("satin", "semi_gloss", "gloss", "wet", "liquid_glaze", "mercury"), "mercury", {}),
    # condensation BEADED on cold paint — each bead its own lens
    "elm_dew_field":    (("eggshell", "semi_gloss", "milk_glass", "sea_glass", "gloss", "pearl"), "chrome", {}),
    # dry ground taking the first rain: dark wet patches on dust
    "elm_petrichor":    (("ceramic_matte", "powder", "patina", "semi_gloss", "wet"), "dark_chrome", {}),
    # water finding the low line and running it fast
    "elm_gutter_race":  (("satin_carbon", "gloss_carbon", "gloss", "wet", "mercury"), "mercury", {}),
    # beads shearing sideways into rivulets: automotive GLASS
    "elm_windscreen":   (("fiberglass", "sea_glass", "milk_glass", "liquid_glaze", "chrome"), "chrome", {}),
    # rain that never lands — it evaporates; nothing wet, only veil
    "elm_virga":        (("clear_matte", "ceramic_matte", "milk_glass", "fiberglass", "soft_gloss"), "satin_chrome", {}),

    # ═══ ❄ FROZEN — every way water goes solid ═════════════════════════════
    # snow moving sideways fast enough to erase the ground
    "elm_blizzard":     (("clear_matte", "ceramic_matte", "milk_glass", "bead_blast", "frozen_film"), "satin_chrome", {}),
    # wind SCULPTING snow the way it sculpts sand
    "elm_snowdrift":    (("ceramic_matte", "powder", "eggshell", "milk_glass", "satin"), "milk_glass", {}),
    # half rain, half ice, and unpleasant: wet AND frozen in one deck
    "elm_sleet":        (("bead_blast", "frozen_film", "sea_glass", "wet", "liquid_glaze"), "chrome", {}),
    # DENTS you can feel through the paint — struck, blasted, galvanised
    "elm_hail_damage":  (("bead_blast", "galvanized", "brushed_ti", "gunmetal", "powder"), "gunmetal", {}),
    # vapour straight to crystal: needle frost on ceramic
    "elm_hoarfrost":    (("ceramic_matte", "frozen_film", "milk_glass", "sea_glass", "satin_chrome"), "satin_chrome",
                         {"bands": "linear"}),
    # freezing fog BUILDING INTO THE WIND — rime is rough, not clear
    "elm_rime_ice":     (("ceramic_matte", "bead_blast", "frozen_film", "milk_glass", "frozen_metal"), "frozen_metal", {}),
    # "invisible until it is far too late" — clear film over near-black
    "elm_black_ice":    (("flat_black", "gloss_carbon", "wet", "liquid_glaze", "chrome"), "chrome", {}),
    # window frost: ferns growing along scratches, on glass
    "elm_frost_fern":   (("fiberglass", "sea_glass", "milk_glass", "frozen_film", "chrome"), "chrome",
                         {"bands": "linear"}),
    # ice crystals out of a clear sky, each one a mirror
    "elm_diamond_dust": (("milk_glass", "sea_glass", "satin_chrome", "mercury", "chrome"), "mercury",
                         {"bands": "linear"}),
    # ground that has not thawed in ten thousand years: mineral, dead, ancient
    "elm_permafrost":   (("ceramic_matte", "powder", "patina", "frozen_metal", "galvanized"), "frozen_metal", {}),
    # a glacier breaking over a step — blocks of cold glass
    "elm_serac_field":  (("bead_blast", "milk_glass", "sea_glass", "frozen_metal", "satin_chrome"), "satin_chrome", {}),
    # SOFT hail: snow that fell through supercooled water
    "elm_graupel":      (("powder", "ceramic_matte", "eggshell", "milk_glass", "bead_blast"), "milk_glass", {}),

    # ═══ 🌀 STORM — rotation and violence in the air ═══════════════════════
    # rotation you can see: the field turns before the funnel does
    "elm_tornado_alley": (("void", "flat_black", "satin_carbon", "gunmetal", "chrome"), "chrome", {}),
    # one storm with its own rotating updraught — the darkest deck here
    "elm_supercell":    (("void", "flat_black", "satin_carbon", "gunmetal", "dark_chrome"), "dark_chrome", {}),
    # bands wrapped tight enough to leave a HOLE in the middle
    "elm_hurricane_eye": (("satin_carbon", "gloss_carbon", "gunmetal", "brushed_ti", "chrome"), "chrome", {}),
    # a wall of weather a hundred miles long, arriving as an edge
    "elm_squall_line":  (("flat_black", "satin_carbon", "gunmetal", "razor", "chrome"), "razor", {}),
    # the cold air a storm pushes AHEAD of itself: dust lifted, not water
    "elm_gust_front":   (("powder", "bead_blast", "galvanized", "gunmetal", "satin"), "gunmetal", {}),
    # pouches hanging under the anvil — sinking air, soft and heavy
    "elm_mammatus":     (("vinyl", "satin", "eggshell", "pearl", "gunmetal"), "pearl", {}),
    # the lowered base under the updraught
    "elm_wall_cloud":   (("void", "flat_black", "satin_carbon", "gunmetal", "brushed_ti"), "gunmetal", {}),
    # ONE channel out of a thousand attempts: the carrier rail earns its place
    "elm_lightning_strike": (("void", "flat_black", "gloss_carbon", "carrier_mid", "carrier_high", "chrome"), "chrome",
                             {"bands": "linear"}),
    # twelve kilometres of vertical development
    "elm_thunderhead":  (("satin_carbon", "gunmetal", "brushed_ti", "galvanized", "chrome"), "brushed_ti", {}),
    # air falling out of a cloud fast enough to spread on impact
    "elm_microburst":   (("bead_blast", "galvanized", "gunmetal", "satin_chrome", "chrome"), "satin_chrome", {}),
    # a tornado that found the sea and started lifting it
    "elm_waterspout":   (("gloss_carbon", "sea_glass", "wet", "gunmetal", "chrome"), "chrome", {}),
    # straight-line wind that keeps going for six hundred miles
    "elm_derecho":      (("flat_black", "satin_carbon", "gunmetal", "brushed_ti", "dark_chrome"), "dark_chrome", {}),

    # ═══ 🌊 WATER — water with a surface ═══════════════════════════════════
    # "not a wave — a change in sea level": deep, heavy, unstoppable
    "elm_tsunami":      (("gloss_carbon", "gloss", "wet", "liquid_glaze", "mercury"), "mercury", {}),
    # the moment the wave face outruns its own base
    "elm_breaker":      (("sea_glass", "gloss", "wet", "milk_glass", "chrome"), "chrome", {}),
    # air beaten into water until it stops being either
    "elm_whitewater":   (("bead_blast", "milk_glass", "ceramic_gloss", "pearl", "soft_gloss"), "pearl", {}),
    # a whole ocean forced through a gap
    "elm_tide_race":    (("gloss_carbon", "wet", "liquid_glaze", "gunmetal", "mercury"), "mercury", {}),
    # the sea arriving somewhere it does not belong — it brings the flood with it
    "elm_storm_surge":  (("patina", "powder", "semi_gloss", "wet", "gunmetal"), "gunmetal", {}),
    # a narrow river running OUT through the surf
    "elm_riptide":      (("wet", "sea_glass", "semi_gloss", "gloss", "satin"), "chrome", {}),
    # spray torn off the wave tops and carried
    "elm_spindrift":    (("clear_matte", "milk_glass", "pearl", "bead_blast", "soft_gloss"), "pearl",
                         {"bands": "linear"}),
    # two tides meeting on a shelf and neither giving way
    "elm_whirlpool":    (("wet", "gloss", "liquid_glaze", "mirror_deep", "chrome_veil"), "mercury", {}),
    # short, steep, confused water
    "elm_chop":         (("satin", "semi_gloss", "sea_glass", "gloss", "wet"), "sea_glass", {}),
    # long-period energy from a storm a thousand miles away: GLASSY
    "elm_glassy_swell": (("sea_glass", "gloss", "liquid_glaze", "mercury", "chrome"), "liquid_glaze", {}),
    # silt and debris marking exactly how high it got
    "elm_flood_line":   (("ceramic_matte", "powder", "patina", "galvanized", "semi_gloss"), "patina", {}),
    # what is left on the sand after the wave goes back
    "elm_foam_lace":    (("eggshell", "ceramic_matte", "milk_glass", "pearl", "soft_gloss"), "milk_glass",
                         {"bands": "linear"}),

    # ═══ 🏜 DRY — when the air carries dust instead ════════════════════════
    # visibility measured in metres
    "elm_sandstorm":    (("ceramic_matte", "powder", "bead_blast", "patina", "brushed_ti"), "brushed_ti", {}),
    # a wall of dust a mile high
    "elm_haboob":       (("powder", "ceramic_matte", "patina", "galvanized", "bead_blast"), "galvanized", {}),
    # ground heated until the air above it has to move
    "elm_dust_devil":   (("bead_blast", "powder", "brushed_ti", "satin", "galvanized"), "brushed_ti", {}),
    # air of two different densities in the same place — pure optics
    "elm_heat_shimmer": (("fiberglass", "milk_glass", "sea_glass", "clear_matte", "liquid_glaze"), "sea_glass", {}),
    # clay that has given up all its water and SHRUNK
    "elm_drought_crack": (("flat_black", "ceramic_matte", "powder", "patina", "semi_gloss"), "patina", {}),
    # an inverted image of the SKY lying on the road
    "elm_mirage":       (("semi_gloss", "sea_glass", "liquid_glaze", "milk_glass", "mercury"), "mercury", {}),
    # fine enough to stay up for weeks
    "elm_dust_veil":    (("clear_matte", "ceramic_matte", "powder", "milk_glass", "soft_gloss"), "milk_glass", {}),
    # a dry lake giving its CRUST back to the wind
    "elm_salt_haze":    (("ceramic_matte", "milk_glass", "bead_blast", "clear_matte", "galvanized"), "bead_blast", {}),
    # a trade wind carrying the Sahara west
    "elm_harmattan":    (("powder", "patina", "ceramic_matte", "brushed_ti", "eggshell"), "brushed_ti", {}),
    # desert air pulled north across the Mediterranean — it arrives damp
    "elm_sirocco":      (("patina", "powder", "galvanized", "bead_blast", "semi_gloss"), "galvanized", {}),
    # windblown silt laid down in BEDS deep enough to build in
    "elm_loess":        (("powder", "ceramic_matte", "patina", "eggshell", "satin"), "patina", {}),
    # rotor wash lifting the whole surface at once
    "elm_brownout":     (("powder", "ceramic_matte", "bead_blast", "satin_carbon", "galvanized"), "gunmetal", {}),
}


def check(element_ids):
    """Every finish designed, and no two dealing the same set of cards."""
    missing = sorted(set(element_ids) - set(DECKS))
    extra = sorted(set(DECKS) - set(element_ids))
    if missing or extra:
        raise ValueError("ELEMENTS deck table out of sync — missing %s, unknown %s"
                         % (missing, extra))
    seen = {}
    for fid, (deck, _edge, _kw) in DECKS.items():
        seen.setdefault(frozenset(deck), []).append(fid)
    clash = {k: v for k, v in seen.items() if len(v) > 1}
    if clash:
        raise ValueError("ELEMENTS duplicate material stories: " + "; ".join(
            ", ".join(sorted(v)) for v in clash.values()))
    return True
