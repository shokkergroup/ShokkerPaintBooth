# -*- coding: utf-8 -*-
"""FRACTURED FLAMES — one hand-authored material story per card.

Owner 2026-09-01: *"STILL FUBAR'D and needs MAJOR work: FRACTURED FLAMES and
it's 75 finishes. Same issue. TONS of repeating specs and paints just recolored
bullshit."*

He is right. The shelf had FIVE band lists — one per chapter — for seventy-five
cards, with exactly ONE per-card override. Fifteen cards per deck.

Combustion actually gives an unusually rich material vocabulary, and the shelf
was spending none of it: cold fuel and char are dead blacks, a burning surface
is a wet luminous film, plasma is the carrier rail doing the one job it is for,
molten rock is vitreous, molten metal is a mirror, and ash is chalk. Each card
below is read off its own description.

Format: fid -> (cards, edge_card, spec_kwargs)
"""
from __future__ import annotations

CARDS = {
    # ── 🔥 IGNITION — the moment it catches ───────────────────────────────
    "ffl_flashpoint":        (("void", "matte", "satin_carbon", "candy", "carrier_high"), "chrome", {"bands": "linear"}),
    "ffl_char_creep":        (("void", "flat_black", "satin_carbon", "matte", "patina"), "razor", {"bands": "linear"}),
    "ffl_tinder_bloom":      (("ceramic_matte", "powder", "eggshell", "candy", "carrier_mid"), "carrier_high", {"bands": "linear"}),
    "ffl_match_head":        (("matte", "semi_gloss", "candy", "candy_chrome", "carrier_high"), "chrome", {}),
    "ffl_smoulder_bed":      (("flat_black", "matte", "powder", "bronze_raw", "candy"), "candy_chrome", {}),
    "ffl_fuse_line":         (("satin_carbon", "powder", "carrier_low", "carrier_mid", "carrier_high"), "chrome", {"bands": "linear"}),
    "ffl_kindle_lattice":    (("powder", "ceramic_matte", "eggshell", "semi_gloss", "candy"), "candy_chrome", {}),
    "ffl_spark_shower":      (("void", "gloss_carbon", "spectraflame", "candy_chrome", "chrome"), "chrome", {"bands": "linear"}),
    "ffl_ember_catch":       (("flat_black", "matte", "patina", "bronze_raw", "candy_chrome"), "candy_chrome", {}),
    "ffl_pilot_ring":        (("gunmetal", "gloss_carbon", "sea_glass", "carrier_low", "carrier_mid"), "chrome", {}),
    "ffl_autoignition":      (("matte", "semi_gloss", "gloss", "candy", "carrier_mid"), "candy_chrome", {}),
    "ffl_firebrand_scatter": (("flat_black", "satin_carbon", "powder", "candy", "carrier_high"), "chrome", {"bands": "linear"}),
    "ffl_scorch_front":      (("void", "flat_black", "matte", "ceramic_matte", "patina"), "bronze_raw", {"bands": "linear"}),
    "ffl_ignition_delay":    (("clear_matte", "milk_glass", "sea_glass", "carrier_low", "soft_gloss"), "satin_chrome", {}),
    "ffl_touchpaper":        (("eggshell", "clear_matte", "powder", "spectraflame", "candy_chrome"), "spectraflame", {"bands": "linear"}),

    # ── 🔥 FLAME — the burning surface ────────────────────────────────────
    "ffl_diffusion_sheet":   (("semi_gloss", "gloss", "ceramic_gloss", "candy", "liquid_glaze"), "candy_chrome", {}),
    "ffl_wrinkled_front":    (("matte", "semi_gloss", "gloss", "spectraflame", "carrier_mid"), "chrome", {}),
    "ffl_darrieus_cell":     (("satin", "semi_gloss", "gloss", "candy_chrome", "carrier_mid"), "chrome", {}),
    "ffl_turbulent_braid":   (("gloss_carbon", "semi_gloss", "candy", "carrier_mid", "carrier_high"), "chrome", {}),
    "ffl_flamelet_storm":    (("flat_black", "matte", "candy", "carrier_mid", "carrier_high"), "chrome", {"bands": "linear"}),
    "ffl_buoyant_fingers":   (("satin_carbon", "semi_gloss", "candy", "spectraflame", "carrier_mid"), "candy_chrome", {}),
    "ffl_shear_tongue":      (("matte", "semi_gloss", "gloss", "spectraflame", "candy_chrome"), "spectraflame", {}),
    "ffl_pool_puff":         (("gloss_carbon", "satin", "gloss", "candy", "liquid_glaze"), "candy_chrome", {}),
    "ffl_candle_cone":       (("milk_glass", "soft_gloss", "semi_gloss", "candy", "carrier_low"), "satin_chrome", {}),
    "ffl_blowtorch":         (("gloss_carbon", "sea_glass", "carrier_low", "carrier_mid", "chrome"), "chrome", {}),
    "ffl_backdraft_wrinkle": (("flat_black", "satin_carbon", "semi_gloss", "candy", "candy_chrome"), "chrome", {}),
    "ffl_fire_whirl_grain":  (("matte", "gloss", "candy", "spectraflame", "mercury"), "mercury", {"bands": "linear"}),
    "ffl_laminar_ladder":    (("gloss_carbon", "semi_gloss", "sea_glass", "carrier_low", "carrier_mid"), "razor", {}),
    "ffl_crown_fire":        (("powder", "ceramic_matte", "semi_gloss", "candy", "carrier_high"), "candy_chrome", {}),
    "ffl_stoichiometric_seam": (("void", "gloss_carbon", "semi_gloss", "carrier_mid", "carrier_high"), "chrome", {"bands": "linear"}),

    # ── ⚡ PLASMA — past burning ───────────────────────────────────────────
    "ffl_arc_filament":      (("void", "flat_black", "gloss_carbon", "carrier_high", "chrome"), "chrome", {"bands": "linear"}),
    "ffl_ionised_braid":     (("gloss_carbon", "satin_carbon", "carrier_low", "carrier_mid", "carrier_high"), "mercury", {}),
    "ffl_magnetised_jet":    (("gloss_carbon", "bronze_raw", "carrier_mid", "spectraflame", "chrome"), "chrome", {"bands": "linear"}),
    "ffl_corona_grain":      (("void", "satin_carbon", "bead_blast", "carrier_low", "carrier_mid"), "satin_chrome", {}),
    "ffl_streamer_web":      (("flat_black", "gloss_carbon", "carrier_low", "carrier_high", "mirror_deep"), "chrome", {"bands": "linear"}),
    "ffl_townsend_cascade":  (("void", "matte", "satin_carbon", "carrier_mid", "chrome"), "razor", {"bands": "linear"}),
    "ffl_pinch_instability": (("satin_carbon", "gunmetal", "carrier_mid", "carrier_high", "mercury"), "mercury", {}),
    "ffl_cathode_spot":      (("void", "gloss_carbon", "satin_chrome", "mirror_deep", "chrome"), "chrome", {"bands": "linear"}),
    "ffl_glow_discharge":    (("gloss_carbon", "semi_gloss", "carrier_low", "carrier_mid", "soft_gloss"), "razor", {}),
    "ffl_lichtenberg_burn":  (("eggshell", "ceramic_matte", "matte", "satin_carbon", "bronze_raw"), "steel_dark", {"bands": "linear"}),
    "ffl_plasma_sheath":     (("fiberglass", "sea_glass", "milk_glass", "carrier_low", "liquid_glaze"), "satin_chrome", {}),
    "ffl_spectral_line":     (("void", "flat_black", "semi_gloss", "carrier_high", "razor"), "chrome", {"bands": "linear"}),
    "ffl_electron_avalanche": (("void", "satin_carbon", "razor", "carrier_mid", "carrier_high"), "chrome", {"bands": "linear"}),
    "ffl_tokamak_ripple":    (("gloss_carbon", "gunmetal", "brushed_ti", "carrier_mid", "satin_chrome"), "satin_chrome", {}),
    "ffl_aurora_column":     (("void", "gloss_carbon", "sea_glass", "carrier_low", "carrier_mid"), "chrome", {"bands": "linear"}),

    # ── 🌋 MOLTEN — rock and metal ────────────────────────────────────────
    "ffl_pahoehoe_skin":     (("flat_black", "satin_carbon", "gloss_carbon", "candy", "liquid_glaze"), "candy_chrome", {}),
    "ffl_slag_crust":        (("bead_blast", "ceramic_matte", "patina", "sea_glass", "liquid_glaze"), "sea_glass", {}),
    "ffl_lava_cell":         (("void", "flat_black", "matte", "candy", "carrier_high"), "candy_chrome", {}),
    "ffl_quench_craze":      (("fiberglass", "sea_glass", "milk_glass", "ceramic_gloss", "liquid_glaze"), "razor", {"bands": "linear"}),
    "ffl_vitrified_glaze":   (("ceramic_matte", "ceramic_gloss", "gloss", "liquid_glaze", "spectraflame"), "liquid_glaze", {}),
    "ffl_weld_pool":         (("gunmetal", "brushed_ti", "steel_dark", "satin_chrome", "mirror_deep"), "mercury", {}),
    "ffl_molten_drip":       (("steel_dark", "gunmetal", "satin_chrome", "spectraflame", "chrome"), "chrome", {}),
    "ffl_crucible_skin":     (("patina", "bronze_raw", "bead_blast", "galvanized", "antique_chrome"), "bronze_raw", {}),
    "ffl_basalt_column":     (("flat_black", "matte", "ceramic_matte", "gloss_carbon", "semi_gloss"), "gunmetal", {}),
    "ffl_obsidian_chill":    (("void", "gloss_carbon", "gloss", "liquid_glaze", "mirror_deep"), "mercury", {}),
    "ffl_foundry_spatter":   (("bead_blast", "galvanized", "gunmetal", "brushed_ti", "chrome"), "steel_dark", {"bands": "linear"}),
    "ffl_tuyere_glow":       (("flat_black", "satin_carbon", "candy", "spectraflame", "carrier_high"), "chrome", {}),
    "ffl_slumped_glass":     (("sea_glass", "milk_glass", "ceramic_gloss", "gloss", "liquid_glaze"), "liquid_glaze", {}),
    "ffl_magma_vesicle":     (("matte", "ceramic_matte", "patina", "semi_gloss", "candy"), "bronze_raw", {}),
    "ffl_ropy_flow":         (("satin_carbon", "matte", "semi_gloss", "candy", "candy_chrome"), "candy_chrome", {}),

    # ── 🌑 CINDER — what is left ──────────────────────────────────────────
    "ffl_ember_bed":         (("flat_black", "matte", "patina", "candy", "carrier_high"), "candy_chrome", {}),
    "ffl_ash_fall":          (("clear_matte", "ceramic_matte", "powder", "eggshell", "milk_glass"), "bead_blast", {"bands": "linear"}),
    "ffl_soot_bloom":        (("void", "flat_black", "satin_carbon", "matte", "powder"), "razor", {"bands": "linear"}),
    "ffl_char_scale":        (("void", "flat_black", "matte", "bead_blast", "satin_carbon"), "patina", {}),
    "ffl_cinder_lattice":    (("flat_black", "matte", "powder", "patina", "bronze_raw"), "steel_dark", {"bands": "linear"}),
    "ffl_fly_ash":           (("clear_matte", "milk_glass", "powder", "ceramic_matte", "soft_gloss"), "milk_glass", {"bands": "linear"}),
    "ffl_coke_cell":         (("void", "satin_carbon", "matte", "bead_blast", "gunmetal"), "gunmetal", {}),
    "ffl_clinker_crust":     (("bead_blast", "ceramic_matte", "patina", "sea_glass", "ceramic_gloss"), "ceramic_gloss", {}),
    "ffl_ash_glaze":         (("ceramic_matte", "powder", "ceramic_gloss", "liquid_glaze", "gloss"), "liquid_glaze", {}),
    "ffl_dying_coal":        (("void", "flat_black", "matte", "candy", "candy_chrome"), "candy_chrome", {}),
    "ffl_grey_front":        (("clear_matte", "ceramic_matte", "powder", "matte", "candy"), "patina", {"bands": "linear"}),
    "ffl_retained_heat":     (("flat_black", "satin_carbon", "matte", "bronze_raw", "spectraflame"), "spectraflame", {}),
    "ffl_powder_burn":       (("ceramic_matte", "powder", "bead_blast", "matte", "galvanized"), "razor", {}),
    "ffl_spall_field":       (("bead_blast", "ceramic_matte", "powder", "galvanized", "brushed_ti"), "brushed_ti", {}),
    "ffl_cold_ash":          (("clear_matte", "ceramic_matte", "powder", "matte", "bead_blast"), "powder", {}),
}


def check(ids):
    missing = sorted(set(ids) - set(CARDS))
    if missing:
        raise ValueError("unauthored FLAMES cards: %s" % missing)
    seen = {}
    for fid, (cards, _e, _kw) in CARDS.items():
        seen.setdefault(frozenset(cards), []).append(fid)
    clash = {k: v for k, v in seen.items() if len(v) > 1}
    if clash:
        raise ValueError("FLAMES duplicate material stories: " + "; ".join(
            ", ".join(sorted(v)) for v in clash.values()))
    return len(CARDS)
