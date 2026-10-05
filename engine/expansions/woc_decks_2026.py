# -*- coding: utf-8 -*-
"""WORLD OF COLOR — one hand-authored material story per finish.

Owner 2026-09-01: *"we cannot have repeats, we cannot have laziness"* and *"the
specs should be diverse, unique, follow the pattern of the base paint and MAKE
SENSE."*

Measured before this file: **10 distinct band tuples across 100 finishes**, the
largest shared by 22. The decks were written per continental chapter, so twenty
different crafts from four countries dealt the same cards.

Every finish here is a specific named craft or material, which makes the deck a
matter of reading rather than inventing: urushi is forty coats of lacquer, raku
is crackled glaze off a red-hot kiln, bogolan is iron mud on tannin-soaked
cloth, capiz is windowpane oyster shell. Cards are chosen to BE that thing.

Format: fid -> (cards, edge_card, spec_kwargs)
"""
from __future__ import annotations

CARDS = {
    # ── Ireland ───────────────────────────────────────────────────────────
    "woc_aran_cable":       (("vinyl", "satin", "eggshell", "milk_glass", "soft_gloss"), "eggshell", {}),
    "woc_peat_cut":         (("void", "flat_black", "matte", "powder", "patina"), "patina", {"bands": "linear"}),
    "woc_connemara_marble": (("ceramic_matte", "semi_gloss", "gloss", "ceramic_gloss", "liquid_glaze"), "sea_glass", {}),
    "woc_stout_head":       (("void", "gloss_carbon", "milk_glass", "soft_gloss", "ceramic_gloss"), "milk_glass", {}),
    "woc_burren_pavement":  (("clear_matte", "ceramic_matte", "bead_blast", "powder", "matte"), "bead_blast", {"bands": "linear"}),
    # ── Scotland ──────────────────────────────────────────────────────────
    "woc_tartan_sett":      (("eggshell", "vinyl", "satin", "powder", "semi_gloss"), "satin", {}),
    "woc_harris_tweed":     (("powder", "eggshell", "vinyl", "bead_blast", "matte"), "powder", {}),
    "woc_cairngorm_granite": (("bead_blast", "ceramic_matte", "galvanized", "sea_glass", "liquid_glaze"), "brushed_ti", {}),
    "woc_heather_moor":     (("ceramic_matte", "powder", "matte", "vinyl", "patina"), "patina", {"bands": "linear"}),
    "woc_cask_char":        (("void", "flat_black", "satin_carbon", "matte", "bronze_raw"), "steel_dark", {}),
    # ── Portugal ──────────────────────────────────────────────────────────
    "woc_azulejo_blue":     (("ceramic_gloss", "gloss", "milk_glass", "pearl", "liquid_glaze"), "liquid_glaze", {}),
    "woc_cork_bark":        (("powder", "ceramic_matte", "vinyl", "eggshell", "matte"), "bead_blast", {}),
    "woc_calcada_wave":     (("clear_matte", "ceramic_matte", "bead_blast", "semi_gloss", "milk_glass"), "razor", {}),
    "woc_sardine_tin":      (("satin_chrome", "brushed_ti", "gloss", "liquid_glaze", "chrome"), "chrome", {}),
    "woc_douro_schist":     (("matte", "satin_carbon", "bead_blast", "patina", "galvanized"), "steel_dark", {}),
    # ── Norway ────────────────────────────────────────────────────────────
    "woc_rosemaling":       (("semi_gloss", "gloss", "ceramic_gloss", "satin", "candy"), "candy_chrome", {}),
    "woc_fjord_water":      (("gloss_carbon", "sea_glass", "gloss", "wet", "liquid_glaze"), "mercury", {}),
    "woc_birch_bark":       (("clear_matte", "milk_glass", "eggshell", "powder", "ceramic_matte"), "razor", {"bands": "linear"}),
    "woc_arctic_light":     (("void", "gloss_carbon", "sea_glass", "milk_glass", "soft_gloss"), "satin_chrome", {}),
    "woc_slate_roof":       (("matte", "flat_black", "satin_carbon", "bead_blast", "powder"), "gunmetal", {}),
    # ── Japan ─────────────────────────────────────────────────────────────
    "woc_aizome_vat":       (("matte", "ceramic_matte", "vinyl", "satin", "semi_gloss"), "patina", {}),
    "woc_urushi_lacquer":   (("gloss_carbon", "gloss", "ceramic_gloss", "liquid_glaze", "mirror_deep"), "mercury", {}),
    "woc_raku_crackle":     (("ceramic_matte", "ceramic_gloss", "bead_blast", "patina", "liquid_glaze"), "razor", {"bands": "linear"}),
    "woc_kintsugi_seam":    (("flat_black", "ceramic_matte", "ceramic_gloss", "bronze_raw", "spectraflame"), "spectraflame", {"bands": "linear"}),
    "woc_washi_fibre":      (("clear_matte", "milk_glass", "eggshell", "soft_gloss", "ceramic_matte"), "milk_glass", {"bands": "linear"}),
    # ── India ─────────────────────────────────────────────────────────────
    "woc_block_print":      (("clear_matte", "eggshell", "vinyl", "semi_gloss", "gloss"), "razor", {}),
    "woc_madras_check":     (("clear_matte", "eggshell", "vinyl", "soft_gloss", "satin"), "soft_gloss", {}),
    "woc_marigold_mound":   (("satin", "semi_gloss", "gloss", "eggshell", "candy"), "candy_chrome", {}),
    "woc_mirror_work":      (("vinyl", "satin", "satin_chrome", "mirror_deep", "chrome"), "chrome", {}),
    "woc_sandstone_jali":   (("ceramic_matte", "powder", "bead_blast", "eggshell", "semi_gloss"), "powder", {"bands": "linear"}),
    # ── Türkiye ───────────────────────────────────────────────────────────
    "woc_iznik_tile":       (("ceramic_matte", "milk_glass", "ceramic_gloss", "gloss", "liquid_glaze", "sea_glass"), "liquid_glaze", {}),
    "woc_kilim_weave":      (("eggshell", "powder", "vinyl", "satin", "ceramic_matte"), "satin", {}),
    "woc_meerschaum":       (("clear_matte", "ceramic_matte", "milk_glass", "eggshell", "soft_gloss", "patina"), "bronze_raw", {}),
    "woc_hammered_copper":  (("bronze_raw", "antique_chrome", "patina", "galvanized", "spectraflame"), "bronze_raw", {}),
    "woc_nazar_glass":      (("sea_glass", "gloss", "ceramic_gloss", "liquid_glaze", "mirror_deep"), "mercury", {}),
    # ── Korea ─────────────────────────────────────────────────────────────
    "woc_celadon_glaze":    (("ceramic_matte", "ceramic_gloss", "sea_glass", "gloss", "liquid_glaze"), "sea_glass", {}),
    "woc_bojagi_patch":     (("clear_matte", "eggshell", "vinyl", "soft_gloss", "semi_gloss"), "razor", {}),
    "woc_dancheong":        (("matte", "semi_gloss", "gloss", "ceramic_gloss", "candy"), "candy_chrome", {}),
    "woc_hanji_sheet":      (("clear_matte", "powder", "eggshell", "frozen_film", "soft_gloss"), "milk_glass", {}),
    "woc_najeon_inlay":     (("gloss_carbon", "gloss", "pearl", "spectraflame", "mirror_deep"), "spectraflame", {"bands": "linear"}),
    # ── Morocco ───────────────────────────────────────────────────────────
    "woc_zellij_star":      (("bead_blast", "ceramic_matte", "ceramic_gloss", "gloss", "semi_gloss", "liquid_glaze"), "razor", {}),
    "woc_tadelakt":         (("ceramic_matte", "satin", "soft_gloss", "eggshell", "wet"), "soft_gloss", {}),
    "woc_saffron_souk":     (("powder", "ceramic_matte", "eggshell", "matte", "satin"), "powder", {}),
    "woc_tannery_vats":     (("patina", "ceramic_matte", "semi_gloss", "wet", "liquid_glaze"), "patina", {}),
    "woc_atlas_cedar":      (("eggshell", "satin", "semi_gloss", "gloss", "powder"), "patina", {}),
    # ── Mali ──────────────────────────────────────────────────────────────
    "woc_bogolan_mud":      (("matte", "ceramic_matte", "powder", "patina", "bead_blast"), "patina", {"bands": "linear"}),
    "woc_kente_strip":      (("vinyl", "satin", "semi_gloss", "eggshell", "gloss"), "satin", {}),
    "woc_indigo_resist":    (("void", "matte", "vinyl", "satin", "clear_matte"), "razor", {"bands": "linear"}),
    "woc_brass_casting":    (("bead_blast", "bronze_raw", "antique_chrome", "galvanized", "patina", "spectraflame"), "spectraflame", {}),
    "woc_laterite_road":    (("patina", "powder", "ceramic_matte", "bead_blast", "bronze_raw"), "bronze_raw", {}),
    # ── Egypt ─────────────────────────────────────────────────────────────
    "woc_faience_blue":     (("ceramic_matte", "ceramic_gloss", "sea_glass", "liquid_glaze", "candy"), "sea_glass", {}),
    "woc_lapis_ground":     (("matte", "ceramic_matte", "semi_gloss", "bronze_raw", "spectraflame"), "spectraflame", {"bands": "linear"}),
    "woc_alabaster":        (("clear_matte", "milk_glass", "ceramic_gloss", "soft_gloss", "liquid_glaze"), "milk_glass", {}),
    "woc_papyrus_weave":    (("eggshell", "clear_matte", "powder", "ceramic_matte", "semi_gloss"), "razor", {}),
    "woc_desert_glass":     (("fiberglass", "sea_glass", "frozen_film", "gloss", "mirror_deep"), "liquid_glaze", {}),
    # ── Ethiopia ──────────────────────────────────────────────────────────
    "woc_coffee_bed":       (("vinyl", "semi_gloss", "gloss", "eggshell", "ceramic_gloss"), "patina", {}),
    "woc_basalt_highland":  (("flat_black", "matte", "satin_carbon", "ceramic_matte", "gloss_carbon"), "gunmetal", {}),
    "woc_shamma_cotton":    (("clear_matte", "powder", "eggshell", "soft_gloss", "milk_glass"), "milk_glass", {"bands": "linear"}),
    "woc_lalibela_stone":   (("ceramic_matte", "powder", "bead_blast", "patina", "matte", "semi_gloss"), "bead_blast", {}),
    "woc_danakil_salt":     (("clear_matte", "milk_glass", "ceramic_matte", "bead_blast", "ceramic_gloss"), "razor", {"bands": "linear"}),
    # ── Jamaica ───────────────────────────────────────────────────────────
    "woc_sound_system":     (("flat_black", "matte", "vinyl", "satin_carbon", "brushed_ti"), "gunmetal", {}),
    "woc_rasta_weave":      (("vinyl", "satin", "powder", "soft_gloss", "matte"), "satin", {}),
    "woc_blue_mountain":    (("clear_matte", "milk_glass", "sea_glass", "soft_gloss", "ceramic_matte"), "sea_glass", {}),
    "woc_sea_glass":        (("bead_blast", "milk_glass", "sea_glass", "ceramic_gloss", "soft_gloss"), "sea_glass", {}),
    "woc_allspice_bark":    (("powder", "ceramic_matte", "patina", "eggshell", "semi_gloss"), "patina", {}),
    # ── Brazil ────────────────────────────────────────────────────────────
    "woc_carnival_block":   (("gloss", "candy", "candy_chrome", "spectraflame", "mirror_deep"), "chrome", {}),
    "woc_amazon_canopy":    (("matte", "vinyl", "satin", "semi_gloss", "gloss"), "patina", {"bands": "linear"}),
    "woc_tourmaline":       (("sea_glass", "gloss", "ceramic_gloss", "liquid_glaze", "spectraflame"), "spectraflame", {}),
    "woc_calcadao":         (("flat_black", "milk_glass", "ceramic_matte", "semi_gloss", "bead_blast"), "razor", {}),
    "woc_cocoa_pod":        (("eggshell", "vinyl", "semi_gloss", "gloss", "powder"), "bronze_raw", {}),
    # ── Peru ──────────────────────────────────────────────────────────────
    "woc_alpaca_weave":     (("clear_matte", "eggshell", "vinyl", "satin", "powder"), "eggshell", {}),
    "woc_andes_strata":     (("ceramic_matte", "powder", "patina", "bead_blast", "semi_gloss"), "patina", {"bands": "linear"}),
    "woc_cusco_textile":    (("clear_matte", "vinyl", "eggshell", "satin", "bronze_raw"), "satin", {}),
    "woc_chicha_morada":    (("satin", "candy", "gloss", "wet", "candy_chrome"), "candy_chrome", {}),
    "woc_salt_terrace":     (("clear_matte", "ceramic_matte", "milk_glass", "wet", "liquid_glaze"), "razor", {"bands": "linear"}),
    # ── Cuba ──────────────────────────────────────────────────────────────
    "woc_havana_facade":    (("ceramic_matte", "powder", "eggshell", "semi_gloss", "patina", "gloss"), "razor", {}),
    "woc_tobacco_leaf":     (("eggshell", "vinyl", "satin", "semi_gloss", "soft_gloss", "wet"), "patina", {}),
    "woc_malecon_spray":    (("bead_blast", "ceramic_matte", "semi_gloss", "wet", "liquid_glaze"), "galvanized", {}),
    "woc_vintage_lacquer":  (("eggshell", "satin", "soft_gloss", "candy", "antique_chrome"), "candy_chrome", {}),
    "woc_sugar_crystal":    (("powder", "frozen_film", "sea_glass", "gloss", "mirror_deep"), "chrome", {}),
    # ── Australia ─────────────────────────────────────────────────────────
    "woc_ochre_bed":        (("powder", "ceramic_matte", "patina", "bead_blast", "matte", "bronze_raw"), "bronze_raw", {"bands": "linear"}),
    "woc_desert_varnish":   (("satin_carbon", "matte", "patina", "gloss_carbon", "bronze_raw"), "steel_dark", {}),
    "woc_opal_seam":        (("milk_glass", "pearl", "spectraflame", "liquid_glaze", "candy_chrome"), "spectraflame", {}),
    "woc_salt_pan":         (("clear_matte", "ceramic_matte", "bead_blast", "milk_glass", "powder"), "razor", {"bands": "linear"}),
    "woc_eucalypt_bark":    (("eggshell", "clear_matte", "powder", "vinyl", "semi_gloss"), "patina", {"bands": "linear"}),
    # ── Aotearoa ──────────────────────────────────────────────────────────
    "woc_greenstone":       (("satin", "semi_gloss", "gloss", "liquid_glaze", "mirror_deep"), "sea_glass", {}),
    "woc_black_sand":       (("void", "flat_black", "satin_carbon", "bead_blast", "gunmetal"), "steel_dark", {}),
    "woc_kauri_gum":        (("eggshell", "semi_gloss", "gloss", "liquid_glaze", "spectraflame"), "liquid_glaze", {}),
    "woc_silver_fern":      (("clear_matte", "eggshell", "pearl", "satin", "milk_glass"), "milk_glass", {"bands": "linear"}),
    "woc_geothermal":       (("ceramic_matte", "bead_blast", "milk_glass", "wet", "liquid_glaze"), "sea_glass", {}),
    # ── Indonesia ─────────────────────────────────────────────────────────
    "woc_batik_wax":        (("matte", "vinyl", "satin", "clear_matte", "semi_gloss"), "razor", {"bands": "linear"}),
    "woc_ikat_warp":        (("eggshell", "satin", "pearl", "soft_gloss", "semi_gloss"), "soft_gloss", {}),
    "woc_volcanic_sand":    (("void", "flat_black", "matte", "powder", "bead_blast"), "gunmetal", {}),
    "woc_teak_grain":       (("satin", "semi_gloss", "gloss", "eggshell", "ceramic_gloss"), "patina", {}),
    "woc_spice_heap":       (("powder", "ceramic_matte", "eggshell", "clear_matte", "satin"), "powder", {}),
    # ── Philippines ───────────────────────────────────────────────────────
    "woc_capiz_shell":      (("milk_glass", "pearl", "soft_gloss", "ceramic_gloss", "liquid_glaze"), "pearl", {}),
    "woc_abaca_fibre":      (("powder", "ceramic_matte", "eggshell", "bead_blast", "vinyl"), "bead_blast", {}),
    "woc_jeepney_chrome":   (("brushed_ti", "satin_chrome", "candy_chrome", "mirror_deep", "chrome"), "chrome", {}),
    "woc_rice_terrace":     (("ceramic_matte", "powder", "semi_gloss", "wet", "patina"), "patina", {"bands": "linear"}),
    "woc_mayon_ash":        (("clear_matte", "ceramic_matte", "powder", "bead_blast", "gunmetal"), "bead_blast", {}),
}


def check(ids):
    missing = sorted(set(ids) - set(CARDS))
    if missing:
        raise ValueError("unauthored WOC finishes: %s" % missing)
    seen = {}
    for fid, (cards, _e, _kw) in CARDS.items():
        seen.setdefault(frozenset(cards), []).append(fid)
    clash = {k: v for k, v in seen.items() if len(v) > 1}
    if clash:
        raise ValueError("WOC duplicate material stories: " + "; ".join(
            ", ".join(sorted(v)) for v in clash.values()))
    return len(CARDS)
