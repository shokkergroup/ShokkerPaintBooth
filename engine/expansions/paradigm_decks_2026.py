# -*- coding: utf-8 -*-
"""PARADIGM — one material story per finish, built from BOTH halves of its name.

Owner 2026-09-01: *"If it says MINERAL: CHALK CHROME then by GOD it should make
you instantly feel like this finish IS chalk chrome."*

`pdg_chalk_chrome` was sitting inside a group of ELEVEN finishes dealing an
identical material set. The shelf had six band lists for fifty finishes, because
the deck was taken from the second word of the name only — every `*_mercury`,
`*_chrome` and `*_mirror` card shared one, every `*_glass` another, and so on.
Measured story_ratio 0.38.

PARADIGM's whole concept is a finish that argues with itself: a substance is
given a material its substance would never honestly have. So the deck has to
carry BOTH halves — the substance's honest dead end at the rough end of the
ladder, and the imposed material at the sharp end. Chalk Chrome then reads as
chalk AND as chrome, which is the argument, and it stops being a clone of
Granite Mercury.

Both tables below are authored: each substance names the materials it would
honestly be, each imposed material names what it actually is.
"""
from __future__ import annotations

# ── what the substance would HONESTLY be (the rough end of the ladder) ──────
SUBSTANCE = {
    # ⬢ WOVEN
    "hessian":    ("bead_blast", "ceramic_matte", "powder"),
    "denim":      ("matte", "eggshell", "vinyl"),
    "wool":       ("vinyl", "satin", "eggshell"),
    "corduroy":   ("eggshell", "vinyl", "soft_gloss"),
    "felt":       ("clear_matte", "ceramic_matte", "powder"),
    "canvas":     ("ceramic_matte", "eggshell", "semi_gloss"),
    "tweed":      ("powder", "eggshell", "vinyl"),
    "burlap":     ("bead_blast", "powder", "matte"),
    "knit":       ("vinyl", "satin", "soft_gloss"),
    "silk":       ("satin", "soft_gloss", "semi_gloss"),
    # ⬣ GROWN
    "moss":       ("ceramic_matte", "powder", "patina"),
    "lichen":     ("bead_blast", "ceramic_matte", "patina"),
    "bark":       ("powder", "patina", "matte"),
    "leaf":       ("eggshell", "vinyl", "semi_gloss"),
    "hide":       ("eggshell", "satin", "vinyl"),
    "fur":        ("vinyl", "satin", "powder"),
    "coral":      ("ceramic_matte", "milk_glass", "bead_blast"),
    "root":       ("matte", "powder", "galvanized"),
    "petal":      ("satin", "eggshell", "soft_gloss"),
    "spore":      ("clear_matte", "powder", "ceramic_matte"),
    # ⬡ MINERAL
    "concrete":   ("ceramic_matte", "powder", "bead_blast"),
    "granite":    ("bead_blast", "galvanized", "brushed_ti"),
    "chalk":      ("clear_matte", "ceramic_matte", "matte"),
    "slate":      ("matte", "flat_black", "satin_carbon"),
    "terracotta": ("ceramic_matte", "powder", "eggshell"),
    "pumice":     ("void", "bead_blast", "powder"),
    "sandstone":  ("powder", "ceramic_matte", "semi_gloss"),
    "basalt":     ("flat_black", "matte", "gloss_carbon"),
    "gypsum":     ("clear_matte", "milk_glass", "ceramic_matte"),
    "grit":       ("bead_blast", "powder", "gunmetal"),
    # ⬠ MADE
    "kraft":      ("eggshell", "powder", "satin"),
    "corrugate":  ("vinyl", "eggshell", "matte"),
    "newsprint":  ("clear_matte", "matte", "vinyl"),
    "plywood":    ("semi_gloss", "eggshell", "satin"),
    "cork":       ("powder", "ceramic_matte", "vinyl"),
    "greyboard":  ("clear_matte", "matte", "powder"),
    "sawdust":    ("powder", "bead_blast", "eggshell"),
    # blotter is unsized paper — it DRINKS. Gypsum is a dry mineral crust, and
    # the two collided on (clear_matte, ceramic_matte, milk_glass); blotting
    # paper has a nap that gypsum does not.
    "blotter":    ("clear_matte", "eggshell", "milk_glass"),
    "chipboard":  ("powder", "matte", "semi_gloss"),
    "card":       ("eggshell", "clear_matte", "semi_gloss"),
    # ⬟ RUINED
    "rust":       ("patina", "bronze_raw", "bead_blast"),
    "verdigris":  ("patina", "galvanized", "ceramic_matte"),
    "ash":        ("void", "clear_matte", "powder"),
    "soot":       ("void", "flat_black", "satin_carbon"),
    "mould":      ("ceramic_matte", "patina", "vinyl"),
    "flake":      ("patina", "bead_blast", "anodized"),
    "corrosion":  ("patina", "galvanized", "bronze_raw"),
    "cinder":     ("void", "flat_black", "matte"),
    "decay":      ("clear_matte", "patina", "powder"),
    "weathered":  ("bead_blast", "ceramic_matte", "frozen_metal"),
}

# ── what it is GIVEN instead (the sharp end) ────────────────────────────────
IMPOSED = {
    "mercury": (("mercury", "mirror_deep"), "mercury"),
    "chrome":  (("chrome", "satin_chrome"), "chrome"),
    "mirror":  (("mirror_deep", "chrome"), "mercury"),
    "glass":   (("sea_glass", "liquid_glaze"), "sea_glass"),
    "liquid":  (("wet", "liquid_glaze"), "mercury"),
    "carrier": (("carrier_mid", "carrier_high"), "chrome"),
    "pearl":   (("pearl", "milk_glass"), "satin_chrome"),
    # a glaze is a fired vitreous coat — ceramic gloss over the body, not a metal
    "glaze":   (("ceramic_gloss", "liquid_glaze"), "candy_chrome"),
}


def deck_for(fid):
    """(cards, edge) for a pdg_<substance>_<imposed> id."""
    stem = fid[4:] if fid.startswith("pdg_") else fid
    parts = stem.rsplit("_", 1)
    if len(parts) != 2:
        raise ValueError("unparseable paradigm id %r" % fid)
    sub, imp = parts
    if sub not in SUBSTANCE:
        raise ValueError("%s: unknown substance %r" % (fid, sub))
    if imp not in IMPOSED:
        raise ValueError("%s: unknown imposed material %r" % (fid, imp))
    cards, edge = IMPOSED[imp]
    deck = tuple(SUBSTANCE[sub]) + tuple(cards)
    return deck, edge


def check(ids):
    seen = {}
    for fid in ids:
        deck, _e = deck_for(fid)
        seen.setdefault(frozenset(deck), []).append(fid)
    clash = {k: v for k, v in seen.items() if len(v) > 1}
    if clash:
        raise ValueError("PARADIGM duplicate material stories: " + "; ".join(
            ", ".join(sorted(v)) for v in clash.values()))
    return len(ids)
