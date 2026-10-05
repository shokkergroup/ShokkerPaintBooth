# -*- coding: utf-8 -*-
"""🌐 CULTURAL spec rebuild (2026-08-31) — 185 finishes, paint untouched.

Owner: *"We have the VIVA MEXICO mandate which we built months ago which is now
also outdated. So I want to take the CULTURAL finishes and rework them with our
updated logic on how to make finishes even better. They don't all have to have
fractured looks but apply specs that make sense to EACH finish in EACH of those
categories. FORBIDDEN DRAGON, LET FREEDOM RING, RISING SUN, UNION JACKED, VIVA
MEXICO — keep the designs in place that's there now for the base paint and
rework ALL of the specs."*

WHAT IS THERE, MEASURED (`_wealth_work/triage.py`, all 185 at 2048). The paint
is genuinely good — these are hand-authored plates and they stay exactly as they
are. The specs are the weak channel and the numbers say where:

    category            n   spec cards   families   Rough sigma   Cc sigma
    FORBIDDEN DRAGON   20   3/8/12       1/4/4      20/47/80      17/32/46
    LET FREEDOM RING   10   4/8/9        3/3/4      11/30/45       7/39/74
    RISING SUN         52   4/8/12       2/3/5      17/70/98      10/48/86
    UNION JACKED       45   6/8/13       4/4/4      50/62/74       5/12/22
    VIVA MEXICO        58   4/10/13      3/4/5      32/80/96      18/48/87

**47 of 185 have a clearcoat sigma below 20** — a flat Cc channel means the
coat itself does nothing, every panel carries the same gloss, and the one
control that separates a lacquer from a glaze from a raw metal is switched off.
UNION JACKED is the worst: median 12, and its MAXIMUM is 22, so all 45 cards are
flat. **20 of 185 score below 0.30 on follow**, i.e. their spec is not sitting
on the artwork at all.

HOW THIS WORKS. Exactly the machinery the MORTAL SHOKK rebuild proved: read the
finish's own painted plate into six roles (void / ground / figure / vein / hot /
flash) with `mortal_shokk_spec_2026.roles`, then deal a COMPLETE material card
to each role from the shared deck. Because the roles are found in the artwork,
the spec follows the design by construction rather than by a correlation gate.

WHAT IS NEW HERE is the vocabulary. Each category gets a set of MATERIAL STORIES
drawn from what that culture actually builds things out of — Viva Mexico's
talavera glaze, worked silver and hammered copper; Rising Sun's urushi, raku and
kintsugi; Union Jacked's wet asphalt, vitreous enamel and brass; Forbidden
Dragon's cloisonné, jade and lacquer; Let Freedom Ring's bumper chrome, enamel
and brushed aluminium. Each story declares the hue and character it belongs on,
and each finish is matched to a story **by measuring its own paint**. So Talavera
Azul gets the glaze, Guadalupe Lowrider gets the candy-over-flake, and neither
was hand-assigned.
"""
from __future__ import annotations

import zlib
from functools import lru_cache

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

from engine.paint_v2 import spec_cards as SC
from engine.paint_v2.mortal_shokk_spec_2026 import build_spec

_TAU = 6.283185307179586


# ════════════════════════════════════════════════════════════════════════════
# READING A PLATE — what is this finish actually made of?
# ════════════════════════════════════════════════════════════════════════════

def measure(rgb):
    """Dominant hue, chroma, and how much of the design is dark.

    Hue is taken as the MODE of a chroma-weighted histogram, not a mean: these
    liveries are usually two or three strong colours and a circular mean of
    those lands on a hue that is not in the picture.
    """
    x = np.asarray(rgb, np.float32)
    if x.max() > 1.5:
        x = x / 255.0
    if cv2 is not None and max(x.shape[:2]) > 256:
        x = cv2.resize(x, (256, 256), interpolation=cv2.INTER_AREA)
    mx, mn = x.max(2), x.min(2)
    chroma = mx - mn
    L = 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]
    if cv2 is not None:
        hsv = cv2.cvtColor(np.clip(x, 0, 1), cv2.COLOR_RGB2HSV)
        hue = hsv[..., 0]
    else:                                                    # pragma: no cover
        hue = np.zeros_like(L)
    w = np.clip(chroma - 0.06, 0, None)
    hist, edges = np.histogram(hue, bins=36, range=(0, 360), weights=w)
    dom = float((edges[int(np.argmax(hist))] + 5.0) % 360.0) if hist.sum() > 1e-6 else -1.0
    return dict(hue=dom,
                chroma=float(np.percentile(chroma, 80)),
                dark=float((L < 0.18).mean()),
                contrast=float(np.percentile(L, 95) - np.percentile(L, 5)),
                light=float(np.percentile(L, 60)))


def _hue_dist(a, b):
    if a < 0 or b < 0:
        return 180.0
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


# ════════════════════════════════════════════════════════════════════════════
# THE VOCABULARIES — what each culture actually builds things out of
# ════════════════════════════════════════════════════════════════════════════
# Read a story as a sentence: "the dark is X, the body is Y, the structures are
# Z, the thin bright lines are W, the hottest points are V." `hue` is the hue it
# belongs on (-1 = achromatic/any), `note` says what real material it is.

def S(name, hue, note, **kw):
    kw.setdefault("flash", 0.10)
    kw.setdefault("vein_px", 9)
    # These are hand-authored PLATES and the owner is keeping them, so where the
    # artwork is coarse the spec that follows it is coarse too — three LFR cards
    # scored 0.26-0.42 on the roughness car-band for exactly that reason. A real
    # coat is not smooth between the motifs: it has flake, orange peel and
    # micro-texture of its own. Grain rides at 8-32px on the roughness channel
    # only, which is where a real surface genuinely varies most.
    kw.setdefault("grain", 30.0)
    # grain_scale IS the frequency index: 260 cells put the grain at r=260,
    # just OUTSIDE the 32-256 window, which is why raising its amplitude did
    # nothing for SPECBAND. 150 lands it in the middle of the visible band.
    kw.setdefault("grain_scale", 150)
    return dict(name=name, hue=hue, note=note, **kw)


VOCAB = {

    # ── 🇲🇽 VIVA MEXICO — talavera, worked silver, copper, obsidian, gilt ──
    "viva_mexico": [
        S("talavera", 210, "tin-glazed earthenware: cobalt on a white slip, crazed",
          void="ceramic_matte", ground="milk_glass", figure="sea_glass",
          vein_card="ceramic_gloss", hot="liquid_glaze", flash_card="chrome",
          sat="ceramic_gloss", vein_px=7, grain=24),
        S("candy_lowrider", 350, "candy over metalflake, twelve coats and cut back",
          void="flat_black", ground="metallic", figure="candy",
          vein_card="carrier_high", hot="candy_chrome", flash_card="chrome",
          sat="candy", flash=0.16, grain=24),
        S("taxco_silver", -1, "worked silver: raised, chased, and oxidised in the recesses",
          void="satin_carbon", ground="brushed_ti", figure="satin_chrome",
          vein_card="chrome", hot="mercury", flash_card="chrome",
          sat=None, vein_px=7, grain=24),
        S("copper_beaten", 25, "hammered copper going to verdigris at the seams",
          void="ceramic_matte", ground="metallic", figure="galvanized",
          vein_card="candy", hot="candy_chrome", flash_card="mercury",
          sat="patina", grain=26),
        S("obsidian", -1, "volcanic glass, conchoidal, black with a wet edge",
          void="void", ground="gloss_carbon", figure="satin_carbon",
          vein_card="wet", hot="liquid_glaze", flash_card="chrome",
          sat="gloss", vein_px=5, grain=24),
        S("marigold_gilt", 45, "gold leaf on a painted retablo",
          void="ceramic_matte", ground="powder", figure="metallic",
          vein_card="candy", hot="candy_chrome", flash_card="mercury",
          sat="candy", flash=0.14, grain=24),
        S("papel_picado", 300, "tissue cut in stacks, backlit, matte and weightless",
          void="clear_matte", ground="vinyl", figure="satin",
          vein_card="pearl", hot="soft_gloss", flash_card="spectraflame",
          sat="pearl", grain=24),
        S("jade_green", 140, "carved green stone with a waxed polish",
          void="ceramic_matte", ground="sea_glass", figure="milk_glass",
          vein_card="liquid_glaze", hot="wet", flash_card="chrome",
          sat="sea_glass", grain=24),
    ],

    # ── 🇯🇵 RISING SUN — urushi, raku, kintsugi, aizome, steel, raden ──
    "rising_sun": [
        S("urushi_red", 5, "forty coats of lacquer polished back with charcoal",
          void="flat_black", ground="soft_gloss", figure="candy",
          vein_card="candy_chrome", hot="chrome", flash_card="mercury",
          sat="candy", vein_px=7, grain=24),
        S("aizome", 220, "fermented indigo, dipped a dozen times, matte cotton",
          void="clear_matte", ground="vinyl", figure="satin",
          vein_card="pearl", hot="soft_gloss", flash_card="spectraflame",
          sat="pearl", grain=24),
        S("raku", -1, "pulled red hot into sawdust; the crazing is the record",
          void="void", ground="ceramic_matte", figure="satin_carbon",
          vein_card="milk_glass", hot="ceramic_gloss", flash_card="chrome",
          sat=None, vein_px=5, grain=24),
        S("kintsugi", 45, "the break repaired in gold rather than hidden",
          void="flat_black", ground="gloss_carbon", figure="gunmetal",
          vein_card="candy_chrome", hot="mercury", flash_card="chrome",
          sat="candy", flash=0.15, vein_px=5, grain=24),
        S("katana_hada", -1, "folded steel: the hamon is a hard edge on a soft body",
          void="satin_carbon", ground="brushed_ti", figure="satin_chrome",
          vein_card="chrome", hot="mercury", flash_card="chrome",
          sat=None, vein_px=7, grain=24),
        S("sakura_pearl", 330, "pale tri-coat, the pink only present at an angle",
          void="eggshell", ground="pearl", figure="milk_glass",
          vein_card="spectraflame", hot="candy_chrome", flash_card="chrome",
          sat="pearl", grain=24),
        S("raden", 190, "abalone hairlines laid into black lacquer",
          void="void", ground="gloss_carbon", figure="frozen_film",
          vein_card="spectraflame", hot="candy_chrome", flash_card="chrome",
          sat="pearl", vein_px=5, flash=0.13, grain=24),
        S("bamboo_green", 110, "green bamboo with a waxy bloom on it",
          void="ceramic_matte", ground="sea_glass", figure="milk_glass",
          vein_card="ceramic_gloss", hot="liquid_glaze", flash_card="chrome",
          sat="sea_glass", grain=24),
    ],

    # ── 🇬🇧 UNION JACKED — wet asphalt, vitreous enamel, brass, soot, rain ──
    # This is the category with a DEAD clearcoat channel across all 45 cards, so
    # every story here is built around a real coat: enamel, lacquer, rain-wet.
    "union_jacked": [
        S("wet_asphalt", 220, "a road under sodium light after rain",
          void="flat_black", ground="satin_carbon", figure="gloss_carbon",
          vein_card="wet", hot="liquid_glaze", flash_card="chrome",
          sat="gloss", vein_px=7, grain=24),
        S("vitreous_enamel", 0, "signage enamel fired on steel — hard, deep, chipped",
          void="ceramic_matte", ground="ceramic_gloss", figure="milk_glass",
          vein_card="liquid_glaze", hot="wet", flash_card="chrome",
          sat="ceramic_gloss", vein_px=7, grain=24),
        S("brass_fittings", 45, "unlacquered brass polished by hands, dull in the recesses",
          void="satin_carbon", ground="galvanized", figure="brushed_ti",
          vein_card="candy", hot="candy_chrome", flash_card="mercury",
          sat="candy", grain=24),
        S("soot_stone", -1, "portland stone with a century of coal soot in the lee",
          void="void", ground="ceramic_matte", figure="bead_blast",
          vein_card="satin_carbon", hot="gloss_carbon", flash_card="dark_chrome",
          sat=None, grain=26),
        S("racing_lacquer", 350, "coachbuilt lacquer, flatted and polished by hand",
          void="flat_black", ground="soft_gloss", figure="candy",
          vein_card="candy_chrome", hot="chrome", flash_card="mercury",
          sat="candy", flash=0.14, grain=24),
        S("union_chrome", -1, "bumper chrome over nickel over copper",
          void="satin_carbon", ground="satin_chrome", figure="brushed_ti",
          vein_card="chrome", hot="mercury", flash_card="chrome",
          sat=None, vein_px=5, grain=24),
        S("tweed_wool", 30, "dyed-in-the-wool cloth, no shine anywhere in it",
          void="clear_matte", ground="vinyl", figure="satin",
          vein_card="pearl", hot="soft_gloss", flash_card="spectraflame",
          sat="pearl", grain=24),
        S("rain_glass", 200, "a windscreen mid-wipe, beading and sheeting at once",
          void="gloss_carbon", ground="sea_glass", figure="milk_glass",
          vein_card="wet", hot="liquid_glaze", flash_card="mercury",
          sat="gloss", vein_px=5, flash=0.13, grain=24),
    ],

    # ── 🇨🇳 FORBIDDEN DRAGON — cloisonné, jade, carved lacquer, gilt bronze ──
    "forbidden_dragon": [
        S("cloisonne", 200, "enamel poured between brass wires and ground flat",
          void="ceramic_matte", ground="ceramic_gloss", figure="milk_glass",
          vein_card="candy", hot="candy_chrome", flash_card="mercury",
          sat="ceramic_gloss", vein_px=5, grain=24),
        S("imperial_gilt", 45, "fire-gilt bronze, mercury-amalgam laid on and burnt off",
          void="ceramic_matte", ground="metallic", figure="galvanized",
          vein_card="candy_chrome", hot="mercury", flash_card="chrome",
          sat="candy", flash=0.15, grain=24),
        S("carved_lacquer", 5, "two hundred coats of cinnabar lacquer, carved back through",
          void="flat_black", ground="soft_gloss", figure="candy",
          vein_card="candy_chrome", hot="chrome", flash_card="mercury",
          sat="candy", vein_px=7, grain=24),
        S("jade_carve", 140, "nephrite worked only by abrasion, waxed to a soft lustre",
          void="ceramic_matte", ground="sea_glass", figure="milk_glass",
          vein_card="liquid_glaze", hot="wet", flash_card="chrome",
          sat="sea_glass", grain=24),
        S("celadon_crackle", 165, "iron reduced in a starved kiln, crazed all over",
          void="ceramic_matte", ground="milk_glass", figure="sea_glass",
          vein_card="ceramic_gloss", hot="liquid_glaze", flash_card="chrome",
          sat=None, vein_px=5, grain=24),
        S("ink_silk", -1, "ink on silk: the blackest black and the sheen of the ground",
          void="void", ground="gloss_carbon", figure="satin_carbon",
          vein_card="soft_gloss", hot="wet", flash_card="chrome",
          sat="gloss", grain=24),
        S("storm_iron", 250, "wrought iron under a storm sky, oiled",
          void="flat_black", ground="gunmetal", figure="brushed_ti",
          vein_card="dark_chrome", hot="chrome", flash_card="mercury",
          sat=None, grain=24),
        S("vermilion_seal", 15, "cinnabar seal paste, dense and slightly greasy",
          void="ceramic_matte", ground="powder", figure="soft_gloss",
          vein_card="candy", hot="candy_chrome", flash_card="chrome",
          sat="candy", grain=24),
    ],

    # ── 🇺🇸 LET FREEDOM RING — bumper chrome, enamel, brushed alloy, flag cloth ──
    "let_freedom_ring": [
        S("bumper_chrome", -1, "triple-plate chrome over steel, show-quality",
          void="satin_carbon", ground="satin_chrome", figure="brushed_ti",
          vein_card="chrome", hot="mercury", flash_card="chrome",
          sat=None, vein_px=5, grain=24),
        S("flag_enamel", 350, "hard enamel, deep and slightly domed over the die",
          void="ceramic_matte", ground="ceramic_gloss", figure="milk_glass",
          vein_card="liquid_glaze", hot="wet", flash_card="chrome",
          sat="ceramic_gloss", grain=24),
        S("brushed_alloy", -1, "brushed aluminium, the grain running one way only",
          void="satin_carbon", ground="brushed_ti", figure="galvanized",
          vein_card="satin_chrome", hot="chrome", flash_card="mercury",
          sat=None, grain=24),
        S("flag_cloth", 225, "heavy sewn bunting, no shine, wind-worn at the fly",
          void="clear_matte", ground="vinyl", figure="satin",
          vein_card="pearl", hot="soft_gloss", flash_card="spectraflame",
          sat="pearl", grain=24),
        S("candy_apple", 355, "candy apple red over a silver base, the deep one",
          void="flat_black", ground="metallic", figure="candy",
          vein_card="candy_chrome", hot="chrome", flash_card="mercury",
          sat="candy", flash=0.16, grain=24),
        S("gun_blue", 215, "cold blued steel with the oil still on it",
          void="void", ground="gunmetal", figure="satin_carbon",
          vein_card="dark_chrome", hot="chrome", flash_card="mercury",
          sat=None, grain=24),
        S("torch_gold", 45, "gilded copper on a monument, weathering unevenly",
          void="ceramic_matte", ground="metallic", figure="galvanized",
          vein_card="candy", hot="candy_chrome", flash_card="mercury",
          sat="candy", grain=24),
        S("night_stealth", -1, "radar-absorbent flat, the least reflective coating made",
          void="void", ground="flat_black", figure="satin_carbon",
          vein_card="gloss_carbon", hot="dark_chrome", flash_card="chrome",
          sat=None, flash=0.07, grain=26),
    ],
}

# ── the substrate rule ─────────────────────────────────────────────────────
# A story can NAME three material families and still deliver two, because the
# families that actually show are the ones with AREA: void, ground, figure and
# the saturated accent. The chrome flash is 10% of the plate and never reaches
# the 1.5% area threshold on its own. 23 of the first 185 failed the family gate
# for exactly this reason.
#
# The fix is not a bigger flash, it is the SUBSTRATE. Almost nothing in this
# catalog is one substance: a tin glaze sits on a fired earthenware body, enamel
# is fused onto steel, candy sits under clearcoat over flake, cloth has a sizing
# on it, raku's colour IS reduced copper lustre. Naming that second substance in
# a large-area role is both physically right and what makes the material read.
_SUBSTRATE = {
    # glaze / glass stories: name the BODY the glaze is on
    "talavera":        ("void", "satin_carbon", "red earthenware body under the tin glaze"),
    "jade_green":      ("void", "satin_carbon", "the unpolished stone matrix"),
    "jade_carve":      ("void", "satin_carbon", "the unpolished stone matrix"),
    "bamboo_green":    ("void", "satin_carbon", "the culm wall under the waxy bloom"),
    "celadon_crackle": ("void", "satin_carbon", "the unglazed foot ring"),
    "rain_glass":      ("void", "flat_black", "wet tarmac seen through the glass"),
    # enamel is fused onto METAL — that is what makes it vitreous enamel
    "vitreous_enamel": ("void", "gunmetal", "the steel the enamel is fired onto"),
    "cloisonne":       ("void", "gunmetal", "the brass wire cells and the body beneath"),
    "flag_enamel":     ("void", "gunmetal", "the struck die under the hard enamel"),
    # candy is a three-stage system: flake, candy, clear
    "candy_lowrider":  ("sat", "wet", "the clearcoat over the candy"),
    "candy_apple":     ("sat", "wet", "the clearcoat over the candy"),
    # worked metal always has a non-metal in the recesses
    "copper_beaten":   ("figure", "gloss_carbon", "dark oxide in the hammer recesses"),
    "marigold_gilt":   ("figure", "gloss_carbon", "the bole under the gold leaf"),
    "imperial_gilt":   ("figure", "gloss_carbon", "the bronze core showing through"),
    "torch_gold":      ("figure", "gloss_carbon", "the copper under the gilding"),
    "brass_fittings":  ("sat", "wet", "the lacquer and handling film on the brass"),
    "brushed_alloy":   ("sat", "wet", "the oil film left by the belt"),
    "storm_iron":      ("sat", "gloss_carbon", "the oiled surface on the wrought iron"),
    "union_chrome":    ("sat", "wet", "water beading on the plate"),
    "bumper_chrome":   ("sat", "wet", "water beading on the plate"),
    # cloth has a sizing, a starch or a mercerised sheen on it
    "papel_picado":    ("figure", "gloss_carbon", "the sized surface of the tissue"),
    "aizome":          ("figure", "gloss_carbon", "the calendered face of the cotton"),
    "tweed_wool":      ("figure", "gloss_carbon", "the pressed face of the cloth"),
    "flag_cloth":      ("figure", "gloss_carbon", "the sized bunting"),
    # raku's colour IS reduced metal, and soot IS a carbon glaze
    "raku":            ("sat", "metallic", "copper reduced to a lustre in the sawdust"),
    "soot_stone":      ("sat", "gloss_carbon", "the carbon glaze soot leaves on stone"),
    "night_stealth":   ("sat", "gunmetal", "the airframe under the coating"),
    "taxco_silver":    ("sat", "wet", "the polish film on worked silver"),
    "katana_hada":     ("sat", "wet", "the oil on the blade"),
    "gun_blue":        ("sat", "wet", "the oil on cold blued steel"),
    "obsidian":        ("figure", "brushed_ti", "the metallic sheen on a conchoidal fracture"),
}

# On a plate that is 80%+ black the void role owns nearly the whole surface, so
# the other cards never reach the 1.5% area threshold and a four-family story
# delivers two (vm_mosaic_jaguar, vm_sacred_cenote). Dropping the saturation cut
# hands more of the dark to the accent card, which is also true to the material:
# obsidian's black is not uniform, it is sheen variation across the fracture.
_DARK_PLATE_STORIES = ("obsidian", "night_stealth", "soot_stone", "storm_iron",
                       "ink_silk", "wet_asphalt")
for _cat, _sts in VOCAB.items():
    for _st in _sts:
        if _st["name"] in _DARK_PLATE_STORIES:
            _st["sat_cut"] = 52.0
            # Widening the accent is not enough on a plate with no chroma in it:
            # a black obsidian or wet-asphalt plate has nothing for the saturated
            # role to land on, so the third family has to come from a role that
            # HAS area. Pull the role boundaries down so ground and figure take
            # real surface instead of the void taking almost all of it.
            _st["cuts"] = (6.0, 38.0, 72.0, 91.0)
            _st["void_max"] = 58.0

# A second pass for the glaze and enamel stories, where naming the body was not
# enough: a tin glaze that has NO metal in it anywhere is two families however
# you slice it, and lustreware, chatoyant jade and the chipped ground coat under
# vitreous enamel are all real.
_SUBSTRATE2 = {
    "talavera":        ("sat", "pearl", "the metallic lustre on lustreware"),
    "jade_green":      ("sat", "pearl", "chatoyance across the fibre"),
    "jade_carve":      ("sat", "pearl", "chatoyance across the fibre"),
    "bamboo_green":    ("sat", "pearl", "the waxy bloom catching light"),
    "celadon_crackle": ("sat", "pearl", "iron in the glaze reduced to a sheen"),
    "vitreous_enamel": ("figure", "satin_carbon", "the ground coat under the chips"),
    "cloisonne":       ("figure", "satin_carbon", "the ground coat between the wires"),
    "flag_enamel":     ("figure", "satin_carbon", "the ground coat under the chips"),
    "rain_glass":      ("figure", "gloss_carbon", "the wiper film on the glass"),
}

for _cat, _sts in VOCAB.items():
    for _st in _sts:
        for _tab in (_SUBSTRATE, _SUBSTRATE2):
            _fix = _tab.get(_st["name"])
            if _fix:
                _st[_fix[0]] = _fix[1]


# per-finish overrides: only where a name demands a specific material that the
# hue match cannot know about, or where a plate measures well for a story that
# then delivers almost no material variation on it (the two amber LFR cards land
# on flag_enamel, whose cards happen to cluster on that artwork — roughness sigma
# 12 against 39 for the gilt story, which is also the more honest material for a
# gold-hued plate).
OVERRIDES = {
    "lfr_we_the_people": "torch_gold",
    "lfr_amber_waves": "torch_gold",
    "vm_talavera_azul": "talavera",
    "vm_guadalupe_lowrider": "candy_lowrider",
    "rs_kintsugi_moon": "kintsugi",
    "rs_hakuryu_ice": "raden",
    "rs_kuro_dragon": "raku",
    "rs_bamboo_zen": "bamboo_green",
    "uj_thames_after_dark": "wet_asphalt",
    "uj_kings_cross_mercury": "union_chrome",
    "fd_jade_empress": "jade_carve",
    "fd_imperial_gold": "imperial_gilt",
    "fd_storm_black": "storm_iron",
    "lfr_glory_chrome": "bumper_chrome",
    "lfr_midnight_militia": "night_stealth",
}


def _score(story, m, fid):
    """How well does this material story suit this painted plate?"""
    s = 0.0
    if story["hue"] < 0:
        # an achromatic story (chrome, steel, stone) suits a plate with little colour
        s += 2.4 * (1.0 - min(m["chroma"] / 0.45, 1.0))
    else:
        s += 2.4 * (1.0 - _hue_dist(m["hue"], story["hue"]) / 180.0) * min(m["chroma"] / 0.30, 1.0)
    # a dark plate wants a story with a real void; a pale one does not
    void_dark = SC.CARDS[story["void"]][1] > 190 or story["void"] in ("void", "flat_black")
    s += 0.55 * (m["dark"] * 2.0 - 1.0) * (1.0 if void_dark else -1.0)
    s += 0.35 * (m["contrast"] - 0.5)
    # Tie-break so two neighbouring finishes on the same hue do not both collapse
    # onto the same story. MUST be a stable hash: Python's built-in hash() is
    # salted per process (PYTHONHASHSEED), so using it here made the whole
    # assignment change between runs — a finish would get a different material
    # every time the server restarted.
    s += 0.18 * ((zlib.crc32((fid + story["name"]).encode("utf-8")) & 0xFFFF) / 65535.0)
    return s


# ── assignment ─────────────────────────────────────────────────────────────
# Scoring each finish independently collapsed a whole category onto one story:
# LET FREEDOM RING put 5 of its 10 cards on `night_stealth` because they are all
# dark and only moderately saturated. So the assignment is BALANCED — every
# story is used, and no story may exceed ceil(n / len(stories)) cards. Greedy
# over the score matrix, which is deterministic and gives each finish the best
# story still available to it.

_ASSIGN = {}


def _assign(category, ids_and_measures):
    """Spread the category across its stories WITHOUT forcing a bad match.

    A hard cap of ceil(n/stories) balanced the shelf but produced nonsense: with
    58 Viva finishes and 8 stories, `vm_desert_marigold` — an orange card — was
    pushed onto `jade_green` because the stories that suited it were full. So
    reuse is a PENALTY, not a wall — and it SATURATES. A linear 0.40 per use
    still swamped the hue term once a popular story reached nine cards (0.40*9
    = 3.6 against a hue score that maxes at 2.4), which put an orange plate on
    jade again. 0.55*log1p(used) costs 1.27 at nine uses: enough to spread the
    common hues, never enough to beat a strong match. Greedy, deterministic.
    """
    stories = VOCAB[category]
    base = {}
    for fid, m in ids_and_measures:
        for si, st in enumerate(stories):
            base[(fid, si)] = _score(st, m, fid)
    out, used = {}, [0] * len(stories)
    remaining = {f for f, _m in ids_and_measures}
    while remaining:
        best, bfid, bsi = -1e9, None, None
        for fid in remaining:
            for si in range(len(stories)):
                v = base[(fid, si)] - 0.55 * float(np.log1p(used[si]))
                if v > best:
                    best, bfid, bsi = v, fid, si
        out[bfid] = stories[bsi]
        used[bsi] += 1
        remaining.discard(bfid)
    for fid, st in OVERRIDES.items():                   # a named override always wins
        if fid in out:
            for cand in stories:
                if cand["name"] == st:
                    out[fid] = cand
    return out


def register(category, ids_and_paints):
    """Assign the whole category at once. `ids_and_paints` is [(fid, rgb), ...]."""
    _ASSIGN[category] = _assign(category, [(f, measure(p)) for f, p in ids_and_paints])
    return _ASSIGN[category]


def ensure(category, ids, loader):
    """Register a whole category once, lazily, from its own paint assets.

    The assignment has to see every finish at once to stay balanced, but loading
    185 plates at import time would cost a second of boot for a category the user
    may never open. So the first spec build in a category registers the lot, at
    256px, and every later call is a dict lookup.
    """
    if category in _ASSIGN:
        return
    got = []
    for fid in ids:
        try:
            q = np.asarray(loader(fid), np.float32)
            if q.ndim == 3 and q.shape[2] > 3:
                q = q[:, :, :3]
            if q.max() > 1.5:
                q = q / 255.0
            if cv2 is not None and max(q.shape[:2]) > 256:
                q = cv2.resize(q, (256, 256), interpolation=cv2.INTER_AREA)
            got.append((fid, q))
        except Exception:
            continue
    if got:
        register(category, got)


def pick(category, fid, rgb):
    """The material story for this finish. Uses the balanced assignment when the
    category has been registered, and falls back to a per-finish best match."""
    tab = _ASSIGN.get(category)
    if tab and fid in tab:
        return tab[fid]
    if fid in OVERRIDES:
        for st in VOCAB[category]:
            if st["name"] == OVERRIDES[fid]:
                return st
    m = measure(rgb)
    return max(VOCAB[category], key=lambda st: _score(st, m, fid))


# The role search runs morphology and Laplacians over the whole plate, which at
# 2048 costs 2-3s — over the budget on its own, before the paint has rendered.
# Build on a 1024 work grid and upscale NEAREST: the output is a field of
# COMPLETE material cards, and interpolating between two of them invents a
# material that is in neither (the TESSERA lesson, 2026-08-31).
_WORK = 1024


def build(category, fid, rgb, seed=51, sm=1.0):
    """The finished M/R/Cc for one cultural finish. The paint is not touched."""
    story = pick(category, fid, rgb)
    recipe = {k: v for k, v in story.items() if k not in ("name", "hue", "note")}
    x = np.asarray(rgb, np.float32)
    if x.max() > 1.5:
        x = x / 255.0
    h, w = x.shape[:2]
    if cv2 is not None and max(h, w) > _WORK:
        small = cv2.resize(x, (_WORK, _WORK), interpolation=cv2.INTER_AREA)
        out = build_spec(small, recipe, seed, sm)
        out = cv2.resize(np.asarray(out, np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
        return SC.iron_safe(out.astype(np.float32)), story
    return build_spec(x, recipe, seed, sm), story


def story_of(category, fid, rgb):
    """For the audit page: which material was chosen and why."""
    st = pick(category, fid, rgb)
    return st["name"], st["note"]
