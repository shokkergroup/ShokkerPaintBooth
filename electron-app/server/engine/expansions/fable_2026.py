# -*- coding: utf-8 -*-
"""✨ FABLE — 50 finishes taken from actual stories.

Owner 2026-09-01:

    "I want FABLE - it's currently 20 finishes that say they are STORYBOOK
     MATERIAL - and they are NOT. Turn them into 50 ACTUAL STORYBOOK looks.
     Taking from FABLES. Make sure that if someone is looking at these finishes
     and they see it says FABLE they can say - yeah I can see it. These DO look
     like finishes that could be grabbed from FABLES/STORIES."

He is right about the twenty. They were called Ember Glass, Glacier Core, Abyss
Lantern, Prism Veil, Oilforge — a set of abstract optical effects filed under a
word that promises something else entirely.

So every finish here is a THING OUT OF A STORY, and the material follows from
what the thing is actually made of rather than from a mood:

  📕 ONCE UPON   the physical book — vellum, iron gall ink, gilt edge, wax seal
  👑 COURT       glass slipper, spindle gold, briar hedge, pumpkin coach
  🐺 WOODS       wolf pelt, breadcrumb trail, gingerbread, thorn thicket
  🐉 WYRM        dragon scale, hoard gold, phoenix ash, kraken ink
  🔮 SPELL       cauldron, wishing well, moon path, rune stone

A glass slipper gets caustics and glass cards because that is what it is. Iron
gall ink gets filaments and a dead black that goes wet where it pooled. Wax seal
gets coalescing metaballs. The test the owner set is the right one: read the
name, look at the finish, and the two should agree.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

import engine.expansions.fractured_flames_kit_2026 as FK
import engine.expansions.nightshift_forms_2026 as NF
from engine.paint_v2 import era_kit_2026 as EK
from engine.paint_v2 import spec_story as ST

ID_PREFIX = "fab_"
GROUP = "✨ FABLE"
GEN = 1024
WORK = 1152


P = {
    "parchment":  ((0.30, 0.26, 0.19), (0.62, 0.56, 0.43), (0.82, 0.76, 0.62), (0.96, 0.93, 0.84)),
    # 2026-09-02: was near-black ink with pale strokes and measured 0.73 of the
    # canvas dead. A storybook's iron gall ink is dark strokes ON PARCHMENT:
    # ground stops are parchment, stroke stops are the brown-black ink.
    "ink":        ((0.80, 0.72, 0.54), (0.87, 0.80, 0.63), (0.24, 0.15, 0.08), (0.08, 0.05, 0.03)),
    "gilt":       ((0.14, 0.10, 0.03), (0.44, 0.31, 0.08), (0.76, 0.58, 0.20), (1.00, 0.90, 0.56)),
    "rose":       ((0.20, 0.06, 0.10), (0.52, 0.18, 0.26), (0.80, 0.40, 0.48), (0.99, 0.78, 0.80)),
    "forest":     ((0.04, 0.10, 0.06), (0.12, 0.28, 0.16), (0.28, 0.50, 0.30), (0.68, 0.86, 0.58)),
    "ruby":       ((0.14, 0.02, 0.04), (0.44, 0.05, 0.12), (0.74, 0.16, 0.24), (1.00, 0.60, 0.58)),
    "emerald":    ((0.02, 0.12, 0.08), (0.06, 0.34, 0.22), (0.16, 0.60, 0.40), (0.66, 0.94, 0.76)),
    "twilight":   ((0.07, 0.06, 0.16), (0.18, 0.16, 0.38), (0.36, 0.32, 0.62), (0.78, 0.74, 0.96)),
    "moonlight":  ((0.14, 0.16, 0.22), (0.38, 0.42, 0.52), (0.68, 0.72, 0.80), (0.96, 0.98, 1.00)),
    "ember":      ((0.12, 0.03, 0.01), (0.42, 0.12, 0.03), (0.78, 0.36, 0.08), (1.00, 0.78, 0.36)),
    "sea":        ((0.03, 0.12, 0.16), (0.08, 0.34, 0.44), (0.22, 0.60, 0.70), (0.74, 0.94, 0.96)),
    "amber":      ((0.18, 0.09, 0.02), (0.52, 0.28, 0.05), (0.84, 0.56, 0.16), (1.00, 0.86, 0.52)),
    "bone":       ((0.24, 0.22, 0.19), (0.56, 0.53, 0.47), (0.80, 0.78, 0.72), (0.97, 0.96, 0.92)),
    "verdigris":  ((0.05, 0.13, 0.11), (0.14, 0.36, 0.32), (0.34, 0.64, 0.58), (0.76, 0.94, 0.88)),
    "plum":       ((0.11, 0.04, 0.14), (0.30, 0.10, 0.36), (0.54, 0.24, 0.60), (0.86, 0.66, 0.92)),
    "oak":        ((0.14, 0.09, 0.05), (0.38, 0.26, 0.14), (0.62, 0.46, 0.28), (0.88, 0.76, 0.56)),
    "slate_blue": ((0.06, 0.09, 0.14), (0.18, 0.26, 0.36), (0.38, 0.50, 0.62), (0.80, 0.88, 0.96)),
    "wolf":       ((0.10, 0.10, 0.11), (0.28, 0.28, 0.30), (0.52, 0.51, 0.52), (0.86, 0.86, 0.88)),
}


def R(name, palette, form, params, deck, edge, seed, *, grain="grain", gamt=0.22,
      detail=0.42, desc="", **kw):
    return dict(name=name, palette=palette, form=form, params=params, deck=deck,
                edge=edge, seed=seed, grain=grain, gamt=gamt, detail=detail,
                desc=desc, **kw)


ROWS = [
    # ── 📕 ONCE UPON — the book itself ────────────────────────────────────
    R("Vellum Leaf", "parchment", "ek:crinkle", dict(scale=140, sharp=2.2, folds=3),
      ("clear_matte", "eggshell", "ceramic_matte", "soft_gloss", "milk_glass"), "razor", 4101,
      grain="grain", desc="Calfskin scraped, limed and stretched, still showing the follicle side."),
    R("Iron Gall Ink", "ink", "ek:squiggle", dict(n=600, length=120.0, amp=14.0, confetti=0.2, width=3.0),
      ("void", "flat_black", "matte", "gloss", "liquid_glaze"), "mercury", 4102,
      grain="fibre", desc="Oak gall and green vitriol — black going brown, and eating the page slowly."),
    R("Gilt Edge", "gilt", "ek:bands", dict(n=44, shear=1.8, vortex=20),
      ("eggshell", "semi_gloss", "bronze_raw", "spectraflame", "candy_chrome"), "spectraflame", 4103,
      grain="flake", desc="Leaf laid on the block edge and burnished, so the closed book is solid gold."),
    R("Ribbon Marker", "ruby", "ek:moire", dict(),
      ("vinyl", "satin", "semi_gloss", "gloss", "ceramic_gloss"), "candy_chrome", 4104,
      grain="fibre", desc="Woven silk bound into the spine, frayed at the end from a century of use."),
    R("Foxed Page", "parchment", "ek:splatter", dict(blobs=1500, rmax=6.0, drips=0.0, spatter=1.0),
      ("clear_matte", "eggshell", "powder", "patina", "ceramic_matte"), "patina", 4105,
      grain="crackle", desc="Rust-coloured spots blooming through the paper wherever the damp got in."),
    R("Woodcut Block", "oak", "ek:scanline", dict(lines=120.0, triad=1.0, bloom=0.3, roll=0.2, jitter=0.6),
      ("matte", "ceramic_matte", "powder", "semi_gloss", "satin"), "razor", 4106,
      grain="ridge", desc="Cut against the end grain so the line can be as fine as the printer dares."),
    R("Illuminated Capital", "gilt", "ek:guilloche", dict(period=70.0, ring=9.0),
      ("ceramic_matte", "semi_gloss", "bronze_raw", "spectraflame", "candy_chrome"), "spectraflame", 4107,
      grain="flake", desc="One letter given a week, gold over gesso, with a hare in the descender."),
    R("Marbled Endpaper", "twilight", "damascus", dict(layers=140, twist=2.8),
      ("semi_gloss", "gloss", "ceramic_gloss", "liquid_glaze", "pearl"), "pearl", 4108,
      grain="fibre", desc="Colour floated on size and combed, then lifted in one pull. No two ever match."),
    R("Calf Binding", "oak", "ek:wrinkle", dict(),
      ("eggshell", "vinyl", "satin", "semi_gloss", "powder"), "patina", 4109,
      grain="grain", desc="Full calf, blind-tooled, darkened at the joints where the hands go."),
    R("Wax Seal", "ruby", "ek:tooled", dict(cell=160.0, petals=5, stamp=0.9, bevel=1.2),
      ("matte", "semi_gloss", "gloss", "candy", "ceramic_gloss"), "candy_chrome", 4110,
      grain="stipple", desc="Poured, stamped, and cracked across the middle the moment it was opened."),

    # ── 👑 COURT ──────────────────────────────────────────────────────────
    R("Glass Slipper", "moonlight", "caustics", dict(scale=8.0, octaves=3),
      ("frozen_film", "sea_glass", "mirror_deep", "gloss", "chrome_veil"), "chrome", 4111,
      grain="flake", desc="It fits one person and it is made of glass — both facts are the whole story."),
    R("Spindle Gold", "gilt", "ek:filaments", dict(n=320, length=70, width=1.2),
      ("satin", "bronze_raw", "antique_chrome", "spectraflame", "candy_chrome"), "spectraflame", 4112,
      grain="fibre", desc="Straw in at night and gold on the bobbin by morning, at a price agreed too fast."),
    R("Crown Jewel", "ruby", "ek:facets", dict(stones=150, table=0.34, brilliance=1.6),
      ("gloss", "ceramic_gloss", "liquid_glaze", "candy_chrome", "mirror_deep"), "mercury", 4113,
      grain="flake", desc="Cut to throw light rather than to keep weight, which is a choice about being seen."),
    R("Mirror Mirror", "moonlight", "truchet", dict(tiles=36, style="arc"),
      ("gloss_carbon", "satin_chrome", "mirror_deep", "mercury", "chrome"), "mercury", 4114,
      grain="grain", desc="It only ever answers the question it was asked, which is the trouble with it."),
    R("Poisoned Apple", "ruby", "metaball", dict(blobs=1400, radius=0.011),
      ("gloss", "ceramic_gloss", "liquid_glaze", "candy", "candy_chrome"), "candy_chrome", 4115,
      grain="flake", desc="One side red enough to sell it, and the seller ate the other half first."),
    R("Royal Velvet", "plum", "ek:shag", dict(strands=8200, length=26, lean=0.15),
      ("void", "vinyl", "satin", "eggshell", "soft_gloss"), "pearl", 4116,
      grain="fibre", desc="Cut pile deep enough to hold a handprint, in the purple nobody else was allowed."),
    R("Seven-League Boot", "oak", "ek:camo", dict(patches=4, blob=120.0, roughness=1.4),
      ("matte", "eggshell", "vinyl", "semi_gloss", "gloss"), "patina", 4117,
      grain="ridge", desc="Twenty-one miles a stride, and creased across the instep like any other boot."),
    R("Tower Stone", "bone", "ek:bricks", dict(rows=28, cols=5, bind=0.24),
      ("ceramic_matte", "powder", "bead_blast", "matte", "patina"), "bead_blast", 4118,
      grain="crackle", desc="Coursed rubble with one window, set higher than anybody sensible would build."),
    R("Briar Hedge", "forest", "chladni", dict(),
      ("void", "matte", "ceramic_matte", "patina", "bronze_raw"), "steel_dark", 4119,
      grain="spark", desc="A hundred years of growth in one night, and every thorn pointing outward."),
    R("Pumpkin Coach", "amber", "ek:topo", dict(lines=40.0, width=4.0),
      ("semi_gloss", "gloss", "ceramic_gloss", "candy", "spectraflame"), "candy_chrome", 4120,
      grain="flake", desc="Ribbed, gilded, and on a strict schedule."),

    # ── 🐺 WOODS ──────────────────────────────────────────────────────────
    R("Wolf Pelt", "wolf", "ek:threads", dict(),
      ("matte", "vinyl", "satin", "powder", "eggshell"), "eggshell", 4121,
      grain="fibre", gamt=0.26, desc="Guard hairs over a dense undercoat, banded so the grey is never one grey."),
    R("Breadcrumb Trail", "parchment", "ek:eden", dict(seeds=400, steps=8),
      ("eggshell", "powder", "ceramic_matte", "bead_blast", "matte"), "razor", 4122,
      grain="spark", desc="A plan that depended on the birds not being hungry."),
    R("Gingerbread", "oak", "ek:craters", dict(n=1400, rmin=3.0, rmax=14.0),
      ("ceramic_matte", "eggshell", "powder", "semi_gloss", "gloss"), "candy_chrome", 4123,
      grain="stipple", desc="Baked hard, iced at the seams, and structurally sounder than it looks."),
    R("Red Hood", "ruby", "ek:sett", dict(),
      ("matte", "vinyl", "satin", "semi_gloss", "ceramic_gloss"), "candy_chrome", 4124,
      grain="grain", desc="Wool, hooded, and the single most visible thing in a winter wood."),
    R("Thorn Thicket", "forest", "shatter", dict(impacts=6, radials=40),
      ("void", "flat_black", "matte", "patina", "bronze_raw"), "steel_dark", 4125,
      grain="spark", desc="Blackthorn: the spines are modified branches, which is why they are that hard."),
    R("Moss Stone", "emerald", "ek:percolate", dict(),
      ("ceramic_matte", "patina", "powder", "vinyl", "semi_gloss"), "patina", 4126,
      grain="crackle", desc="North face, always. It is the only compass in the story that works."),
    R("Lantern Path", "amber", "ek:stars", dict(),
      ("void", "gloss_carbon", "semi_gloss", "candy", "spectraflame"), "spectraflame", 4127,
      grain="spark", desc="Lit one at a time, ahead of you, by somebody who left before you arrived."),
    R("Owl Feather", "bone", "ek:shred", dict(),
      ("clear_matte", "eggshell", "vinyl", "powder", "soft_gloss"), "milk_glass", 4128,
      grain="fibre", desc="A serrated leading edge that breaks the air up so nothing downstairs hears it."),
    R("Fox Fur", "ember", "ek:rt_fingers", dict(n=40),
      ("eggshell", "vinyl", "satin", "gloss", "clear_matte"), "patina", 4129,
      grain="fibre", gamt=0.24, desc="Red over cream over black, in that order, on every single hair."),
    R("Beanstalk", "emerald", "ridge_flow", dict(ridges=90, cores=2, bend=2.4),
      ("matte", "ceramic_matte", "vinyl", "semi_gloss", "gloss"), "patina", 4130,
      grain="fibre", desc="Twining left to right because that is what beans do, all the way up."),

    # ── 🐉 WYRM ───────────────────────────────────────────────────────────
    R("Dragon Scale", "emerald", "imbricate", dict(rows=48, overlap=0.44),
      ("gloss_carbon", "gloss", "ceramic_gloss", "spectraflame", "mirror_deep"), "spectraflame", 4131,
      grain="flake", desc="Overlapping, keeled, and each one anchored deeper than it looks."),
    R("Hoard Gold", "gilt", "ek:discs", dict(n=3200, radius=11.0, tilt=0.6),
      ("bronze_raw", "antique_chrome", "spectraflame", "candy_chrome", "mirror_deep"), "spectraflame", 4132,
      grain="flake", desc="Counted once, a very long time ago, and every coin missed since."),
    R("Phoenix Ash", "ember", "gray_scott", dict(feed=0.026, kill=0.058),
      ("void", "flat_black", "powder", "candy", "carrier_high"), "chrome", 4133,
      grain="spark", desc="The interesting part is not the fire. It is what is still warm underneath."),
    R("Griffin Bronze", "verdigris", "ek:worley", dict(cells=110),
      ("patina", "bronze_raw", "antique_chrome", "galvanized", "spectraflame"), "bronze_raw", 4134,
      grain="crackle", desc="Cast in two halves and pinned, with the join green where the rain sits."),
    R("Unicorn Horn", "bone", "ek:kh_braid", dict(layers=8, shear=6.0),
      ("milk_glass", "ceramic_gloss", "pearl", "liquid_glaze", "spectraflame"), "pearl", 4135,
      grain="fibre", desc="A single spiral groove, always the same handedness, in something that is not ivory."),
    R("Mermaid Scale", "sea", "ek:scales", dict(cell=14.0, keel=0.5),
      ("sea_glass", "milk_glass", "pearl", "liquid_glaze", "spectraflame"), "spectraflame", 4136,
      grain="flake", desc="Guanine platelets stacked to a quarter wavelength, which is why they are that colour."),
    R("Basilisk Stone", "slate_blue", "basalt", dict(cells=48),
      ("matte", "ceramic_matte", "gunmetal", "bead_blast", "gloss_carbon"), "steel_dark", 4137,
      grain="crackle", desc="Whatever it looked at last is still standing there, in considerable detail."),
    R("Kraken Ink", "ink", "ek:curl", dict(scale=90, steps=30),
      ("void", "flat_black", "gloss_carbon", "wet", "liquid_glaze"), "mercury", 4138,
      grain="grain", desc="Released as a decoy shaped roughly like the animal that released it."),
    R("Faerie Wing", "twilight", "quasicrystal", dict(waves=5, freq=230.0),
      ("clear_matte", "frozen_film", "pearl", "spectraflame", "sea_glass"), "spectraflame", 4139,
      grain="flake", desc="Structural colour in a membrane two cells thick. No pigment involved at all."),
    R("Troll Granite", "wolf", "ek:spall", dict(),
      ("bead_blast", "ceramic_matte", "galvanized", "powder", "brushed_ti"), "brushed_ti", 4140,
      grain="crackle", desc="Caught out by the sunrise, and now part of the landscape."),

    # ── 🔮 SPELL ──────────────────────────────────────────────────────────
    R("Cauldron Brew", "emerald", "ek:honeycomb", dict(),
      ("void", "gloss_carbon", "matte", "carrier_mid", "carrier_high"), "chrome", 4141,
      grain="grain", desc="Double, double. It has been on since Tuesday and nobody remembers the recipe."),
    R("Spellbook Vellum", "parchment", "ek:glyphs", dict(n=420, stroke=2.2, size=18.0),
      ("clear_matte", "eggshell", "ceramic_matte", "semi_gloss", "powder"), "razor", 4142,
      grain="stipple", desc="Written in a hand that expected to be read aloud, and once only."),
    R("Wishing Well", "slate_blue", "ek:holo", dict(rings=40.0, orders=1.0, warp=30.0, sharp=1.2),
      ("gloss_carbon", "sea_glass", "wet", "liquid_glaze", "mercury"), "mercury", 4143,
      grain="grain", desc="Nine metres of cold water and about forty years of small change."),
    R("Moon Path", "moonlight", "moire_beat", dict(a=110.0, b=118.0),
      ("void", "gloss_carbon", "milk_glass", "soft_gloss", "satin_chrome"), "satin_chrome", 4144,
      grain="grain", desc="It points at you from wherever you stand, which is either lovely or a warning."),
    R("Star Dust", "twilight", "phyllotaxis", dict(n=56000, spread=0.76),
      ("void", "flat_black", "satin_carbon", "pearl", "chrome"), "chrome", 4145,
      grain="spark", desc="Everything heavier than helium, and all of it secondhand."),
    R("Enchanted Ice", "sea", "frost_fern", dict(seeds=24, branch=0.17),
      ("fiberglass", "sea_glass", "milk_glass", "frozen_film", "liquid_glaze"), "satin_chrome", 4146,
      grain="fibre", desc="It does not melt, which is the tell. Real ice is always in a hurry."),
    R("Witch Amber", "amber", "ek:dunes", dict(n=24, crest=1.6),
      ("satin", "candy", "liquid_glaze", "bronze_raw", "antique_chrome"), "spectraflame", 4147,
      grain="flake", desc="Something small is in it, and it has been looking out for a very long time."),
    R("Rune Stone", "wolf", "ek:intaglio", dict(),
      ("matte", "ceramic_matte", "powder", "galvanized", "bronze_raw"), "razor", 4148,
      grain="ridge", desc="Straight lines only — carved across the grain, by people who carved into wood first."),
    R("Potion Glass", "verdigris", "ek:polygons", dict(),
      ("sea_glass", "milk_glass", "gloss", "liquid_glaze", "candy"), "candy_chrome", 4149,
      grain="flake", desc="Hand-blown, unevenly walled, and stoppered with something chewed."),
    R("Genie Brass", "gilt", "ek:knurl", dict(),
      ("bronze_raw", "antique_chrome", "galvanized", "spectraflame", "mirror_deep"), "mercury", 4150,
      grain="ridge", desc="Polished on one side from rubbing, and considerably larger on the inside."),
]



# ── BANDING, CHOSEN PER FINISH ON MEASUREMENT ─────────────────────────────
# Quantile bands give every card real area (the spec is diverse — measured
# median 8 distinct materials); linear bands track a value-skewed field better.
# Both are required, so the mode is measured per finish and quantile is only
# given up where it cannot follow the paint. Quantile wins for 32 of 50.
_BANDS = {
    "fab_vellum_leaf": "quantile",
    "fab_iron_gall_ink": "quantile",
    "fab_gilt_edge": "quantile",
    "fab_ribbon_marker": "quantile",
    "fab_foxed_page": "quantile",
    "fab_woodcut_block": "linear",
    "fab_illuminated_capital": "linear",
    "fab_marbled_endpaper": "quantile",
    "fab_calf_binding": "linear",
    "fab_wax_seal": "linear",
    "fab_glass_slipper": "linear",
    "fab_spindle_gold": "quantile",
    "fab_crown_jewel": "quantile",
    "fab_mirror_mirror": "linear",
    "fab_poisoned_apple": "quantile",
    "fab_royal_velvet": "quantile",
    "fab_seven_league_boot": "quantile",
    "fab_tower_stone": "quantile",
    "fab_briar_hedge": "linear",
    "fab_pumpkin_coach": "quantile",
    "fab_wolf_pelt": "linear",
    "fab_breadcrumb_trail": "linear",
    "fab_gingerbread": "quantile",
    "fab_red_hood": "quantile",
    "fab_thorn_thicket": "linear",
    "fab_moss_stone": "quantile",
    "fab_lantern_path": "quantile",
    "fab_owl_feather": "quantile",
    "fab_fox_fur": "quantile",
    "fab_beanstalk": "quantile",
    "fab_dragon_scale": "quantile",
    "fab_hoard_gold": "linear",
    "fab_phoenix_ash": "linear",
    "fab_griffin_bronze": "quantile",
    "fab_unicorn_horn": "quantile",
    "fab_mermaid_scale": "quantile",
    "fab_basilisk_stone": "quantile",
    "fab_kraken_ink": "linear",
    "fab_faerie_wing": "quantile",
    "fab_troll_granite": "quantile",
    "fab_cauldron_brew": "linear",
    "fab_spellbook_vellum": "linear",
    "fab_wishing_well": "linear",
    "fab_moon_path": "quantile",
    "fab_star_dust": "quantile",
    "fab_enchanted_ice": "quantile",
    "fab_witch_amber": "quantile",
    "fab_rune_stone": "linear",
    "fab_potion_glass": "linear",
    "fab_genie_brass": "quantile"
}

def _fid(name):
    return ID_PREFIX + "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")


FABLE = {_fid(r["name"]): r for r in ROWS}
FABLE["fab_phoenix_ash"]["detail"] = 0.85   # labyrinth regime is coarse by nature; SCALE 0.12 without it

for _f, _m in _BANDS.items():
    if _f in FABLE:
        FABLE[_f].setdefault("spec_kw", {})["bands"] = _m


_ALIAS = {"fk:vein": "filaments", "fk:drift": "curl", "fk:dendrite": "dla", "fk:bed": "percolate",
          "fk:plate": "spall", "fk:crack": "anneal_crack", "fk:front": "eden", "fk:crease": "wrinkle",
          "fk:finger": "rt_fingers", "fk:spark": "sparks", "fk:braid": "kh_braid"}


def _canonical(form):
    if form in _ALIAS:
        return _ALIAS[form]
    return form[3:] if form.startswith(("ek:", "fk:")) else form


def check():
    # Owner 2026-09-01: no repeats. Compare the ALGORITHM, not the label (fk:front IS eden).
    _forms = [_canonical(d.get("form")) for d in FABLE.values()] if "FABLE" in globals() else []
    if _forms and len(set(_forms)) != len(_forms):
        _d = sorted({f for f in _forms if _forms.count(f) > 1})
        raise ValueError("FABLE reuses constructions (by algorithm): %s" % _d)
    seen_form, seen_deck = {}, {}
    for fid, d in FABLE.items():
        seen_form.setdefault((d["form"], tuple(sorted(d["params"].items()))), []).append(fid)
        seen_deck.setdefault(frozenset(d["deck"]), []).append(fid)
    for label, tbl in (("construction+params", seen_form), ("material story", seen_deck)):
        clash = {k: v for k, v in tbl.items() if len(v) > 1}
        if clash:
            raise ValueError("FABLE duplicate %s: %s" % (
                label, "; ".join(", ".join(sorted(v)) for v in clash.values())))
    return len(FABLE)


def _form_field(d, shape, seed):
    form, params = d["form"], d["params"]
    if form.startswith("ek:"):
        out = getattr(EK, form[3:])(shape, seed, **params)
    elif form.startswith("fk:"):
        out = getattr(FK, form[3:])(shape, seed, **params)
    else:
        out = getattr(NF, form)(shape, seed, **params)
    f, lab = out if isinstance(out, tuple) else (out, None)
    return np.asarray(f, np.float32), lab


@lru_cache(maxsize=4)
def _field(fid):
    d = FABLE[fid]
    f, lab = _form_field(d, (GEN, GEN), d["seed"])
    f = NF.compose_form(f, d["seed"], kind=d["grain"],
                        amount=float(d.get("detail", 0.42)), res=GEN)
    return f, lab


@lru_cache(maxsize=4)
def _art(fid):
    d = FABLE[fid]
    f, _lab = _field(fid)
    f = FK.upscale(f, WORK)
    pal = np.asarray(P[d["palette"]], np.float32)
    t = FK.pct(f)                       # re-ranked, so the whole ramp is used
    idx = np.clip((t * (len(pal) - 1)).astype(np.int32), 0, len(pal) - 2)
    frac = np.clip(t * (len(pal) - 1) - idx, 0, 1)[..., None]
    art = pal[idx] * (1.0 - frac) + pal[idx + 1] * frac
    if cv2 is not None:
        g, _k = NF.detail(f, d["seed"] + 3, kind=d["grain"], amount=1.0, res=WORK)
        art = art * (1.0 + (g - 0.5) * 2.0 * float(d["gamt"]))[..., None]
    return np.clip(art, 0, 1).astype(np.float32)


def _spec_at(fid, res):
    d = FABLE[fid]
    f, lab = _field(fid)
    f = FK.upscale(f, res)
    lab = FK.upscale(lab, res) if lab is not None else None
    art = _art(fid)
    if cv2 is not None and art.shape[0] != res:
        art = cv2.resize(np.asarray(art, np.float32), (res, res),
                         interpolation=cv2.INTER_LINEAR)
    return ST.compose(f, d["deck"], seed=d["seed"], res=res, lab=lab,
                      edge=d["edge"], art=art, chip_floor=0.08,
                      **d.get("spec_kw", {}))


# Per-finish spec composition (baked by _rebuild/rich_sweep.py)
_FAB_SPECKW = {
    "fab_vellum_leaf": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "fab_iron_gall_ink": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "fab_gilt_edge": {"bands": "quantile", "chips": 0.50, "edge_max": 0.07},
    "fab_ribbon_marker": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "fab_foxed_page": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "fab_woodcut_block": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "fab_illuminated_capital": {"bands": "linear", "chips": 0.34, "edge_max": 0.14},
    "fab_marbled_endpaper": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "fab_calf_binding": {"bands": "linear", "chips": 0.34, "edge_max": 0.07},
    "fab_wax_seal": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "fab_glass_slipper": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "fab_spindle_gold": {"bands": "quantile", "chips": 0.50, "edge_max": 0.07},
    "fab_crown_jewel": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "fab_mirror_mirror": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "fab_poisoned_apple": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "fab_royal_velvet": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "fab_seven_league_boot": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "fab_tower_stone": {"bands": "quantile", "chips": 0.50, "edge_max": 0.07},
    "fab_briar_hedge": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "fab_pumpkin_coach": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "fab_wolf_pelt": {"bands": "linear", "chips": 0.34, "edge_max": 0.14},
    "fab_breadcrumb_trail": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "fab_gingerbread": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "fab_red_hood": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "fab_thorn_thicket": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "fab_moss_stone": {"bands": "quantile", "chips": 0.50, "edge_max": 0.07},
    "fab_lantern_path": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "fab_owl_feather": {"bands": "quantile", "chips": 0.50, "edge_max": 0.07},
    "fab_fox_fur": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "fab_beanstalk": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "fab_dragon_scale": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "fab_hoard_gold": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "fab_phoenix_ash": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "fab_griffin_bronze": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "fab_unicorn_horn": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "fab_mermaid_scale": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "fab_basilisk_stone": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "fab_kraken_ink": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "fab_faerie_wing": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "fab_troll_granite": {"bands": "linear", "chips": 0.34, "edge_max": 0.14},
    "fab_cauldron_brew": {"bands": "quantile", "chips": 0.50, "edge_max": 0.07},
    "fab_spellbook_vellum": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "fab_wishing_well": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "fab_moon_path": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "fab_star_dust": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "fab_enchanted_ice": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "fab_witch_amber": {"bands": "linear", "chips": 0.34, "edge_max": 0.07},
    "fab_rune_stone": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "fab_potion_glass": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "fab_genie_brass": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
}
for _f, _kw in _FAB_SPECKW.items():
    if _f in FABLE:
        FABLE[_f].setdefault("spec_kw", {}).update(_kw)


def _mk(fid):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and src.max() > 1.5:
            src = src / 255.0
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw) and cv2 is not None:
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        art = _art(fid)
        if cv2 is not None:
            art = cv2.resize(art, (fw, fh), interpolation=cv2.INTER_LINEAR)
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - kk) + art * kk, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw) and cv2 is not None:
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        spec = _spec_at(fid, fw)
        mm = np.clip(m2, 0.0, 1.0)[..., None]
        return (np.asarray(spec, np.float32) * mm).clip(0, 255).astype(np.uint8)

    paint_fn.__name__ = "paint_" + fid
    spec_fn.__name__ = "spec_" + fid
    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    n = 0
    for fid in FABLE:
        mono_reg[fid] = _mk(fid)
        n += 1
    return "%d FABLE finishes installed" % n
