"""Canonical record of spec-pattern LEGACY ALIASES.

This file documents IDs that were renamed during the race-livery pivot
(2026-05-26 and beyond). PATTERN_CATALOG dispatches both the new and old
key to the SAME function so painters who saved finishes with the old IDs
continue to render correctly.

Future cleanup tools / migration scripts should read this dict as the
single source of truth.
"""

# === RACING-PIVOT BATCH 1 LEGACY ALIASES (2026-05-26) ===
# Owner directive: shift to race-livery aesthetic. The 10 entries below
# were abstract / academic / fine-art slots that have been
# renamed-and-replaced with race-livery motifs (Predator Skins, Gothic,
# Engine-Turn, Carbon, Fire, Holographic).
SPEC_PATTERN_ALIASES_RACING_PIVOT_V1 = {
    # GOTHIC / HORROR
    "abstract_kandinsky_shapes":     "voodoo_sigil_field",
    "abstract_fluid_acrylic_pour":   "hex_blood_drip",
    # FIRE / HEAT
    "abstract_rothko_field":         "ember_field",
    # PREDATOR SKINS (highest owner interest)
    "abstract_color_field_bleed":    "dragon_scale_macro",
    "abstract_hard_edge_field":      "alligator_hide",
    "spec_velvet_sheen":             "snake_scale_diamond",
    # ENGINE-TURN / MACHINED
    "abstract_bauhaus_forms":        "engine_turn_radial_arc",
    "abstract_op_art_circles":       "jeweled_guilloche",
    # CARBON UNIQUE
    "abstract_cubist_facets":        "forged_carbon_chip",
    # HOLO / COLOR-SHIFT
    "spec_caustic_light":            "holo_prism_shift",
}


# === RACING-PIVOT BATCH 2 LEGACY ALIASES (2026-05-26 PM) ===
# Owner directive: replace 10 more abstract/brushed slots with PREDATOR SKINS
# and GOTHIC/HORROR finishes.
SPEC_PATTERN_ALIASES_RACING_PIVOT_V2 = {
    # PREDATOR SKINS
    "abstract_futurist_motion":      "shark_denticle",
    "abstract_ink_wash_gradient":    "raptor_feather",
    "abstract_minimalist_stripe":    "jaguar_rosette",
    "abstract_mondrian_grid":        "pangolin_armor",
    "abstract_suprematism":          "viper_pit_hex",
    # GOTHIC / HORROR
    "acid_etch":                     "skull_tessellation",
    "bead_blast_uniform":            "hellfire_crackle",
    "brushed_arc":                   "voodoo_bone_fetish",
    "brushed_linear":                "demon_eye_field",
    "brushed_linear_warm":           "crypt_brick",
}


# === RACING-PIVOT BATCH 3 LEGACY ALIASES (2026-05-26 R6 owner tick) ===
# Owner Mode-A rebuilds + sparkle-cluster diversification (3 sparkle-clone
# replacements). Replaces 'boring' aniso_grain + 'don't like' airbrush_bloom
# + diversifies the sparkle_* glut with predator/gothic motifs.
SPEC_PATTERN_ALIASES_RACING_PIVOT_V3 = {
    # PREDATOR / ARMOR
    "aniso_grain":               "chainmail_armor",
    "sparkle_champagne":         "tiger_stripe_field",
    "sparkle_shattered":         "razor_wire_coil",
    # ENGINE-TURN / MACHINED
    "airbrush_gradient_bloom":   "engine_turn_starburst",
    # GOTHIC / HORROR
    "brushed_sparkle":           "nordic_rune_field",
}


# === OWNER RENAME CLEANUP (2026-05-27) ===
# Owner liked the finish but rejected the old public name as inaccurate.
# Keep saved paints using the old id renderable, but treat the Adelson
# checker-shadow optical illusion as the canonical public id.
SPEC_PATTERN_ALIASES_RENAME_V4 = {
    "spec_stone_marble": "adelson_checker_shadow",
}


# Aggregated dict for PATTERN_CATALOG's alias-loop. Each new pivot batch
# should add its dict here in chronological order, so future tools can
# easily walk every legacy migration.
SPEC_PATTERN_ALIASES = {}
SPEC_PATTERN_ALIASES.update(SPEC_PATTERN_ALIASES_RACING_PIVOT_V1)
SPEC_PATTERN_ALIASES.update(SPEC_PATTERN_ALIASES_RACING_PIVOT_V2)
SPEC_PATTERN_ALIASES.update(SPEC_PATTERN_ALIASES_RACING_PIVOT_V3)
SPEC_PATTERN_ALIASES.update(SPEC_PATTERN_ALIASES_RENAME_V4)


__all__ = [
    "SPEC_PATTERN_ALIASES",
    "SPEC_PATTERN_ALIASES_RACING_PIVOT_V1",
    "SPEC_PATTERN_ALIASES_RACING_PIVOT_V2",
    "SPEC_PATTERN_ALIASES_RACING_PIVOT_V3",
    "SPEC_PATTERN_ALIASES_RENAME_V4",
]
