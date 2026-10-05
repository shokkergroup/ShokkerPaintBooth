# -*- coding: utf-8 -*-
"""🌗 FRACTURED NIGHTSHIFT — the 2026-08-31 rebuild. 101 → 50.

Owner: *"right now 100 finishes. Trim it to 50 and make this a brand new
category. This was supposed to make cars change hues between day and night and
not JUST blow it out to white but this category did NOT live up to the hype of
what it was supposed to do."*

MEASURED, BEFORE TOUCHING ANYTHING. `engine/paint_v2/daynight.py` simulates a
paint+spec pair under broad daylight and under hard night point-lights and
reports the hue shift between them. Across the existing 101:

    median hue shift  1.3°        only 1 of 101 reached 25°
    11 finishes blew >10% of the night image out to colourless white

The category was named for a thing it did not do, and nothing measured it.

WHY IT FAILED, AND WHAT ACTUALLY WORKS
--------------------------------------
Spec Guide v1 §1: *metallic reflection is tinted by the albedo and suppresses
diffuse; dielectric and clearcoat highlights are substantially white.* So a car
changes HUE between day and night when it carries two populations:

    DAY   dielectric (M≈0), MATTE, in hue A — broad daylight is diffuse, so
          this population's own colour is what the car reads as
    NIGHT chrome-tier (M≥240), smooth, in a DIFFERENT hue B — a hard point
          light makes this population's tinted reflection the brightest thing
          on the car, and it reads as B

Three parameters decide whether it works, all measured on a two-population
bench before a single finish was authored:

    day population MATTE  → 44° shift        day population GLOSS  → 14°
    night population CHROME → 44°            night population METALLIC → 23°
    night share 0.35–0.50 → 35–44°           share 0.20 → 12°, share 0.80 → 1°

and, decisively:

    night population = the FRACTURED CARRIER → **7°**

which is why the old category failed: it was built on the carrier rail, and the
carrier flips BRIGHTNESS, not hue. It is a magnificent night material and a
poor day/night hue mechanism, and those are different jobs.

WHITEOUT is the owner's other complaint and it has one cause: a night
population whose albedo is near-white or whose highlight is the white clearcoat
lobe rather than a tinted metal one. Every night albedo here is saturated, and
the night card never carries a strong active coat.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

import engine.expansions.fractured_flames_kit_2026 as FK
from engine.paint_v2 import spec_cards as SC

ID_PREFIX = "nsx_"
GROUP = "🌗 FRACTURED NIGHTSHIFT"
GEN = 1024
WORK = 1152

# The night population must be chrome tier: only a metal tints its own
# reflection, and only a tinted reflection can carry a hue after dark.
NIGHT_CARDS = ("chrome", "mercury", "candy_chrome", "spectraflame",
               "dark_chrome", "satin_chrome", "antique_chrome",
               # metals under DIFFERENT COATS, added 2026-09-01. The original
               # seven span Cc 16-50 and R 2-45 — visually one material — so
               # fifty hand-authored "distinct" night decks still rendered as
               # the same sheet of red. These stay chrome-tier (M >= 228, so the
               # day/night flip is untouched) and vary the coat instead.
               "mirror_deep", "chrome_veil", "chrome_dry",
               "bronze_raw", "pewter_metal", "steel_dark")
# The day population must be matte: a glossy dielectric already has a strong
# highlight in daylight, so it never yields the car to the metal at night.
DAY_CARDS = ("matte", "clear_matte", "eggshell", "vinyl", "satin",
             "ceramic_matte", "powder", "flat_black", "satin_carbon")


def _hsv(h, s, v, shape):
    out = np.zeros(shape + (3,), np.float32)
    out[..., 0] = float(h) % 360.0
    out[..., 1] = float(s)
    out[..., 2] = float(v)
    return cv2.cvtColor(out, cv2.COLOR_HSV2RGB) if cv2 is not None else out


# ════════════════════════════════════════════════════════════════════════════
# THE FIELD — where the night population lives
# ════════════════════════════════════════════════════════════════════════════

_STRUCTURES = {
    "cell":      lambda sh, sd, k: FK.worley(sh, sd, cells=k.get("cells", 96)),
    "vein":      lambda sh, sd, k: (FK.filaments(sh, sd, n=k.get("n", 320),
                                                 length=k.get("length", 46)), None),
    "braid":     lambda sh, sd, k: (FK.kh_braid(sh, sd, layers=k.get("layers", 96),
                                                shear=k.get("shear", 3.2)), None),
    "drift":     lambda sh, sd, k: (FK.curl(sh, sd, scale=k.get("scale", 56),
                                            steps=k.get("steps", 16)), None),
    "dendrite":  lambda sh, sd, k: (FK.dla(sh, sd, seeds=k.get("seeds", 800)), None),
    "bed":       lambda sh, sd, k: FK.percolate(sh, sd, cells=k.get("cells", 160),
                                                p=k.get("p", 0.44)),
    "plate":     lambda sh, sd, k: FK.spall(sh, sd, cells=k.get("cells", 88),
                                            lift=k.get("lift", 0.6)),
    "crack":     lambda sh, sd, k: FK.anneal_crack(sh, sd, cells=k.get("cells", 96),
                                                   width=k.get("width", 1.9), gen=1),
    "front":     lambda sh, sd, k: (FK.eden(sh, sd, seeds=k.get("seeds", 2600),
                                            steps=k.get("steps", 7)), None),
    "crease":    lambda sh, sd, k: (FK.wrinkle(sh, sd, k=k.get("k", 0.9),
                                               steps=k.get("steps", 12)), None),
    "finger":    lambda sh, sd, k: (FK.rt_fingers(sh, sd, n=k.get("n", 110)), None),
    "spark":     lambda sh, sd, k: (FK.sparks(sh, sd, n=k.get("n", 1800),
                                              life=k.get("life", 34)), None),
}


def _field(name, shape, seed, kw):
    f = _STRUCTURES[name](shape, seed, kw)
    return f if isinstance(f, tuple) else (f, None)


@lru_cache(maxsize=4)
def _labels_from_field(f, seed, cells):
    """Cells derived from THIS finish's own field.

    Watershed-ish: quantise the construction into bands, then split each band by
    a jittered lattice that is warped BY the field. The resulting cells follow
    the artwork's own contours instead of importing an unrelated worley mosaic.
    """
    n = int(f.shape[0])
    q = np.clip((FK.pct(f) * 9.0).astype(np.int64), 0, 8)
    step = max(2, int(round(n / max(np.sqrt(max(cells, 1)), 1.0))))
    yy, xx = np.mgrid[0:n, 0:n]
    warp = (f - 0.5) * step * 1.6
    gy = ((yy + warp) / step).astype(np.int64)
    gx = ((xx - warp) / step).astype(np.int64)
    return (q * np.int64(1000003) + gy * np.int64(7919) + gx).astype(np.int32)


@lru_cache(maxsize=4)
def _designed_field(fid, shape, seed):
    """The finish's OWN construction, from nightshift_design_2026.

    SPB-105 / owner 2026-09-01: "EVERY SINGLE ONE NEEDS TOTALLY UNIQUE BASE
    PATTERN DESIGNS." The twelve `_STRUCTURES` above were shared roughly four
    ways across fifty finishes, which is why the shelf measured TWIN 0.98-0.99
    on every card even after all fifty were given hand-authored material decks.

    Each finish now names its own construction (19 new forms in
    nightshift_forms_2026, verified by eye at 1:1, plus the twelve kit
    generators), and the fine detail is KEYED to that construction rather than
    sprayed over it — a uniform grain layer is what flattens the paint's detail
    envelope and makes the spec impossible to follow.

    CACHED because both _pop (for the paint) and _spec_at ask for it, and some
    of these constructions are iterative solvers. Uncached, a Gray-Scott finish
    ran its 1800-step simulation twice per render and the shelf measured
    7.5-13.5s at 2048 against a 3s budget.
    """
    from engine.expansions import nightshift_design_2026 as ND
    from engine.expansions import nightshift_forms_2026 as NF

    form, params, kind, amount, _edge = ND.DESIGN[fid]
    if form.startswith("fk:"):
        f, lab = _field(form[3:], shape, seed, params)
    else:
        f, lab = getattr(NF, form)(shape, seed, **params)
    f = NF.compose_form(np.asarray(f, np.float32), seed, kind=kind,
                        amount=float(amount), res=int(shape[0]))
    return f, lab


# ════════════════════════════════════════════════════════════════════════════
# THE RECIPES
# ════════════════════════════════════════════════════════════════════════════

def R(name, day_h, night_h, structure, day_card, night_card, seed,
      share=0.40, sargs=None, day_s=0.72, day_v=0.62, night_s=0.92, night_v=0.42,
      tiers=8, desc="", **extra):
    """One finish: two hues, two material families, and the geometry that
    interleaves them. `share` is the night population's area — the bench says
    0.35–0.50, outside which the flip collapses in one direction or the other."""
    row = dict(name=name, day_h=day_h, night_h=night_h, structure=structure,
               day_card=day_card, night_card=night_card, seed=seed,
               share=share, sargs=sargs or {}, day_s=day_s, day_v=day_v,
               night_s=night_s, night_v=night_v, tiers=tiers, desc=desc)
    row.update(extra)          # pop_jit, shade_cells - per-card overrides
    return row


_ROWS = [
    # ── 🌑 OPPOSITION — complementary flips, the loudest change ─────────────
    R("Cyanide Hour", 186, 32, "cell", "matte", "chrome", 2101, sargs=dict(cells=92),
      desc="Teal all day; at the first floodlight it turns to hot copper and stays there."),
    R("Ember Verdict", 205, 28, "vein", "clear_matte", "candy_chrome", 2102, sargs=dict(n=340),
      desc="Slate blue with a filament network that only announces itself as ember after dark."),
    R("Violet Sentence", 96, 288, "braid", "eggshell", "mercury", 2103, share=0.40,
      desc="Sober olive by day, liquid violet by night — the braid does the handing over."),
    R("Copper Confession", 168, 24, "drift", "matte", "spectraflame", 2104,
      desc="Sea-green drift that confesses to copper under the lights."),
    R("Magenta Testimony", 128, 320, "crack", "ceramic_matte", "candy_chrome", 2105,
      sargs=dict(cells=104), desc="A chalk-green plate whose crack network burns magenta at night."),
    R("Ice to Rust", 198, 18, "plate", "clear_matte", "chrome", 2106, share=0.46,
      desc="Lifted ice plates that oxidise the moment the sun leaves."),
    R("Jade Reversal", 150, 330, "cell", "vinyl", "mercury", 2107, sargs=dict(cells=110),
      desc="Jade cells, rose-mirror seams — the two never appear together."),
    R("Sodium Trial", 212, 44, "bed", "matte", "spectraflame", 2108,
      desc="Cold blue bed with sodium-lamp amber waiting inside it."),
    R("Aqua Betrayal", 176, 4, "front", "eggshell", "chrome", 2109, share=0.38,
      pop_jit=0.20, desc="An aqua burn front that turns blood-red under a point light."),
    R("Chartreuse Alibi", 74, 262, "dendrite", "powder", "candy_chrome", 2110,
      pop_jit=0.19, desc="Acid-green powder coat; the dendrites hold an indigo alibi for after dark."),

    # ── 🌒 EMBER — cool day, warm night ────────────────────────────────────
    R("Slate Ember", 214, 26, "crease", "matte", "candy_chrome", 2111,
      desc="Creased slate that keeps a bed of embers in every fold."),
    R("Harbour Amber", 200, 40, "braid", "clear_matte", "spectraflame", 2112, share=0.44,
      desc="Cold harbour grey braided with the amber of the dock lamps."),
    R("Gunsmoke Coal", 220, 16, "plate", "satin_carbon", "dark_chrome", 2113,
      desc="Gunsmoke plates with coal-red heat surviving underneath them."),
    R("Frost Filament", 190, 34, "vein", "ceramic_matte", "chrome", 2114, share=0.36,
      desc="Frosted ceramic threaded with filaments that light warm."),
    R("Deep Water Forge", 208, 22, "drift", "matte", "spectraflame", 2115,
      desc="Deep-water drift with a forge glow under the surface."),
    R("Pewter Sunset", 226, 36, "cell", "eggshell", "candy_chrome", 2116, sargs=dict(cells=100),
      desc="Pewter cells that each hold one sunset."),
    R("Storm Copper", 202, 30, "finger", "clear_matte", "candy_chrome", 2117, share=0.46,
      desc="Storm-grey fingering shot through with old copper."),
    R("Blue Hour Brass", 218, 46, "crack", "vinyl", "spectraflame", 2118, sargs=dict(cells=112),
      desc="The blue hour, cracked, with brass in every fracture."),
    R("Cinder Vault", 194, 12, "bed", "matte", "chrome", 2119, share=0.42, day_v=0.30,
      desc="A near-black vault whose floor is entirely cinder once the lamps come on."),
    R("Anchor Rust", 210, 20, "front", "matte", "dark_chrome", 2120,
      desc="Cold anchor grey overtaken by a rust front after dark."),

    # ── 🌓 FROST — warm day, cool night ────────────────────────────────────
    R("Rust to Glacier", 22, 196, "plate", "matte", "chrome", 2121,
      desc="Rusted plate by day; every lifted edge goes glacier blue at night."),
    R("Amber Cryonic", 38, 208, "cell", "eggshell", "mercury", 2122, sargs=dict(cells=104),
      desc="Amber cells with a cryogenic mirror sleeping in the seams."),
    R("Terracotta Freeze", 18, 190, "crack", "ceramic_matte", "chrome", 2123,
      desc="Terracotta that freezes solid the moment the sun drops."),
    R("Bronze Nocturne", 34, 220, "braid", "clear_matte", "mercury", 2124, share=0.46,
      desc="Bronze braid playing a blue nocturne after hours."),
    R("Saffron Midnight", 44, 236, "vein", "matte", "mercury", 2125,
      pop_jit=0.18, desc="Saffron ground, midnight veins — they trade places at dusk."),
    R("Ochre Arctic", 30, 200, "drift", "powder", "chrome", 2126,
      desc="Ochre drift with arctic light moving under it."),
    R("Foundry Frost", 26, 212, "crease", "satin_carbon", "satin_chrome", 2127,
      desc="Foundry heat by day, frost in the creases by night."),
    R("Marigold Abyss", 48, 244, "bed", "vinyl", "candy_chrome", 2128, share=0.40,
      desc="A marigold bed that opens onto an abyss-blue floor."),
    R("Sienna Signal", 20, 186, "spark", "matte", "chrome", 2129, sargs=dict(n=2200),
      desc="Sienna field with cold signal sparks that only fire at night."),
    R("Kiln Blue", 36, 224, "front", "eggshell", "mercury", 2130,
      pop_jit=0.20, desc="A kiln-warm front that cools to blue behind it."),

    # ── 🌔 VENOM — into the acids ──────────────────────────────────────────
    R("Venom Curfew", 300, 88, "dendrite", "matte", "candy_chrome", 2131,
      sargs=dict(seeds=1500),
      desc="Purple curfew broken by acid-green dendrites after dark."),
    R("Absinthe Night", 330, 92, "vein", "ceramic_matte", "mercury", 2132,
      desc="Rose by day; absinthe threads take the whole car at night."),
    R("Toxic Recess", 250, 96, "cell", "ceramic_matte", "chrome", 2133, sargs=dict(cells=98),
      desc="Indigo recess cells with a toxic charge in the walls."),
    R("Chlorine Watch", 200, 62, "bed", "ceramic_matte", "chrome", 2134, share=0.36, night_s=0.98,
      desc="Pool-blue watch that turns chlorine-green under the lamps."),
    R("Lime Interrogation", 268, 84, "crack", "powder", "spectraflame", 2135,
      desc="Violet powder coat, lime in every crack — nothing stays hidden."),
    R("Serpent Shift", 320, 100, "braid", "matte", "mercury", 2136,
      desc="Magenta braid that sheds into serpent green."),
    R("Uranium Dusk", 232, 70, "plate", "satin_carbon", "candy_chrome", 2137,
      desc="Cold plates over a uranium glow that only shows at the edges."),
    R("Wormwood Vigil", 286, 92, "drift", "eggshell", "chrome", 2138,
      desc="A mauve vigil drifting toward wormwood by midnight."),
    R("Acid Testament", 260, 66, "finger", "clear_matte", "spectraflame", 2139, share=0.38,
      desc="Blue-violet fingering with an acid testament underneath."),
    R("Hemlock Hour", 306, 104, "front", "matte", "candy_chrome", 2140,
      desc="Orchid front, hemlock behind it, and one hour where you see both."),

    # ── 🌕 ROYAL — into violet, rose and gold ──────────────────────────────
    R("Royal Nightfall", 100, 292, "cell", "matte", "mercury", 2141, sargs=dict(cells=106),
      desc="Olive court by day; royal violet takes the throne at night."),
    R("Rose Assize", 156, 336, "vein", "eggshell", "candy_chrome", 2142,
      pop_jit=0.18, desc="Green bench, rose verdict — the veins deliver it."),
    R("Gilt Sentence", 190, 42, "crack", "ceramic_matte", "spectraflame", 2143,
      desc="Cold ceramic sentenced to gilt after dark."),
    R("Imperial Drift", 82, 276, "drift", "clear_matte", "mercury", 2144,
      desc="Imperial drift from moss to amethyst as the light fails."),
    R("Orchid Curfew", 64, 300, "braid", "vinyl", "candy_chrome", 2145, share=0.46,
      desc="A yellow-green braid that closes into orchid at curfew."),
    R("Cardinal Watch", 140, 350, "plate", "matte", "chrome", 2146,
      desc="Green watch-plates, cardinal red beneath every lifted edge."),
    R("Amethyst Bench", 110, 284, "bed", "powder", "satin_chrome", 2147,
      desc="A powder-green bed with amethyst working up through it."),
    R("Coronation Blue", 40, 228, "crease", "matte", "mercury", 2148,
      desc="Gold creases at noon, coronation blue by ten."),
    R("Fuchsia Docket", 118, 312, "spark", "eggshell", "candy_chrome", 2149,
      sargs=dict(n=2000), desc="Fern ground with fuchsia sparks that only strike at night."),
    R("Last Session", 172, 356, "front", "clear_matte", "chrome", 2150, share=0.40,
      pop_jit=0.20, desc="The last session of the day: sea-green gives way to crimson mirror."),
]


def _fid(name):
    return ID_PREFIX + name.lower().replace(" ", "_").replace("-", "_")


NIGHTSHIFT = {_fid(r["name"]): r for r in _ROWS}


# ════════════════════════════════════════════════════════════════════════════
# RENDER
# ════════════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════════════
# THE MATERIAL STORIES — hand authored, one per finish
# ════════════════════════════════════════════════════════════════════════════
#
# Owner 2026-09-01: "HAND AUTHOR EVERYTHING. NO DUPLICATES."
#
# A first pass at this used a greedy picker with a reuse penalty. It produced
# 50/50 distinct sets and was still wrong, because distinctness is not the
# point — MEANING is. It handed ABSINTHE NIGHT ceramic_matte + eggshell +
# powder + vinyl, four cards that say nothing about absinthe. The owner's rule
# is that the name is the brief: "If it says MINERAL: CHALK CHROME then by GOD
# it should make you instantly feel like this finish IS chalk chrome."
#
# So every deck below is chosen by reading that finish's own name and
# description. Day decks come from the matte family and night decks from the
# chrome family — that separation is the flip mechanism and is not negotiable —
# but WHICH mattes and WHICH chromes is an authored decision each time.
#
#   day: what the surface is made of in daylight
#   night: what the metal underneath turns into when a light hits it
DECKS = {
    # ── 🌑 OPPOSITION — complementary flips ────────────────────────────────
    # clinical chemical chalk; copper comes up hot and slightly aged
    "nsx_cyanide_hour":      (("ceramic_matte", "clear_matte", "matte", "powder"),
                              ("candy_chrome", "bronze_raw", "chrome")),
    # slate that stays dull until the filament net lights like a element
    "nsx_ember_verdict":     (("clear_matte", "matte", "satin", "vinyl"),
                              ("candy_chrome", "spectraflame", "steel_dark")),
    # "liquid violet" — mercury leads, the braid needs a true liquid metal
    "nsx_violet_sentence":   (("eggshell", "satin", "vinyl", "matte"),
                              ("mercury", "spectraflame", "mirror_deep")),
    # sea-green drift; copper confessed in an old, oxidised tone
    "nsx_copper_confession": (("matte", "powder", "ceramic_matte", "satin"),
                              ("bronze_raw", "antique_chrome", "spectraflame")),
    # a chalk-green PLATE — the flattest day deck on the shelf, so the crack burns
    "nsx_magenta_testimony": (("ceramic_matte", "powder", "clear_matte", "flat_black"),
                              ("candy_chrome", "spectraflame", "chrome_veil")),
    # ice by day, oxide by night: the night deck is deliberately the dullest metals
    "nsx_ice_to_rust":       (("clear_matte", "ceramic_matte", "eggshell", "satin"),
                              ("bronze_raw", "antique_chrome", "steel_dark")),
    # jade is a stone with a waxy sheen — vinyl and satin, not chalk
    "nsx_jade_reversal":     (("vinyl", "satin", "eggshell", "ceramic_matte"),
                              ("mercury", "candy_chrome", "chrome_veil")),
    # sodium lamps: cold dead blue ground, amber discharge
    "nsx_sodium_trial":      (("matte", "powder", "flat_black", "clear_matte"),
                              ("spectraflame", "candy_chrome", "bronze_raw")),
    # a burn FRONT — smooth day surface so the red edge is the whole event
    "nsx_aqua_betrayal":     (("eggshell", "vinyl", "satin", "clear_matte"),
                              ("chrome", "candy_chrome", "mirror_deep")),
    # named for its powder coat, so powder leads
    "nsx_chartreuse_alibi":  (("powder", "ceramic_matte", "matte", "vinyl"),
                              ("candy_chrome", "mercury", "chrome_dry")),
    # slate + soot; embers are dark metal with heat in it
    "nsx_slate_ember":       (("matte", "satin_carbon", "flat_black", "satin"),
                              ("candy_chrome", "steel_dark", "dark_chrome")),
    # wet cold dock stone, sodium dock lamps
    "nsx_harbour_amber":     (("clear_matte", "satin", "powder", "eggshell"),
                              ("spectraflame", "chrome_veil", "antique_chrome")),
    # gunsmoke IS carbon; coal-red is the darkest metal that still carries hue
    "nsx_gunsmoke_coal":     (("satin_carbon", "flat_black", "matte", "vinyl"),
                              ("steel_dark", "dark_chrome", "bronze_raw")),
    # frost on ceramic; the filaments run warm but clean
    "nsx_frost_filament":    (("ceramic_matte", "clear_matte", "eggshell", "powder"),
                              ("chrome", "chrome_veil", "spectraflame")),
    # deep water is soft and rubbery; forge light is the brightest thing here
    "nsx_deep_water_forge":  (("matte", "vinyl", "satin_carbon", "satin"),
                              ("spectraflame", "mirror_deep", "candy_chrome")),
    # pewter is a soft dull alloy — eggshell/satin; each cell holds one sunset
    "nsx_pewter_sunset":     (("eggshell", "satin", "powder", "matte"),
                              ("pewter_metal", "candy_chrome", "antique_chrome")),
    # storm grey with OLD copper, so antique leads the night
    "nsx_storm_copper":      (("clear_matte", "powder", "vinyl", "satin_carbon"),
                              ("bronze_raw", "antique_chrome", "steel_dark")),
    # blue hour, cracked, brass in the fractures
    "nsx_blue_hour_brass":   (("vinyl", "eggshell", "clear_matte", "flat_black"),
                              ("spectraflame", "bronze_raw", "chrome")),
    # "near-black vault" — the deadest day deck in the shelf
    "nsx_cinder_vault":      (("flat_black", "matte", "satin_carbon", "ceramic_matte"),
                              ("mirror_deep", "dark_chrome", "chrome")),
    # cold anchor grey, rust front
    "nsx_anchor_rust":       (("matte", "clear_matte", "powder", "vinyl"),
                              ("steel_dark", "bronze_raw", "antique_chrome")),

    # ── 🌓 INVERSION — warm day, cold night ────────────────────────────────
    # rust is powdery iron oxide; glacier is the cleanest mirror
    "nsx_rust_to_glacier":   (("matte", "powder", "ceramic_matte", "vinyl"),
                              ("chrome", "mercury", "chrome_veil")),
    # amber is resin — eggshell and satin, never chalk; cryogenic seams
    "nsx_amber_cryonic":     (("eggshell", "satin", "vinyl", "clear_matte"),
                              ("mercury", "mirror_deep", "chrome")),
    # fired clay: ceramic first, and it freezes to a hard clean mirror
    "nsx_terracotta_freeze": (("ceramic_matte", "powder", "matte", "eggshell"),
                              ("chrome", "satin_chrome", "chrome_veil")),
    # bronze is an aged alloy; the nocturne is liquid and blue
    "nsx_bronze_nocturne":   (("clear_matte", "satin", "satin_carbon", "powder"),
                              ("bronze_raw", "pewter_metal", "mercury")),
    # saffron is a dry spice — chalk and powder; midnight runs liquid
    "nsx_saffron_midnight":  (("matte", "ceramic_matte", "powder", "satin"),
                              ("mercury", "mirror_deep", "candy_chrome")),
    # ochre pigment, arctic light moving underneath
    "nsx_ochre_arctic":      (("powder", "matte", "eggshell", "satin_carbon"),
                              ("chrome", "chrome_veil", "mirror_deep")),
    # foundry = carbon and heat; frost forms in the creases
    "nsx_foundry_frost":     (("satin_carbon", "flat_black", "vinyl", "clear_matte"),
                              ("satin_chrome", "chrome_dry", "steel_dark")),
    # marigold petal has a soft sheen; the abyss below is deep and dark
    "nsx_marigold_abyss":    (("vinyl", "eggshell", "satin", "powder"),
                              ("candy_chrome", "mirror_deep", "pewter_metal")),
    # sienna earth pigment, cold signal sparks
    "nsx_sienna_signal":     (("matte", "powder", "clear_matte", "ceramic_matte"),
                              ("chrome", "satin_chrome", "steel_dark")),
    # kiln-warm ceramic cooling to blue behind the front
    "nsx_kiln_blue":         (("eggshell", "ceramic_matte", "satin", "matte"),
                              ("mercury", "chrome_veil", "spectraflame")),

    # ── 🌘 TOXIC — acid greens against night violets ───────────────────────
    # purple curfew, acid dendrites
    "nsx_venom_curfew":      (("matte", "vinyl", "flat_black", "eggshell"),
                              ("candy_chrome", "spectraflame", "chrome_dry")),
    # absinthe: a spirit. Glassy, wet, not chalky — vinyl/satin lead, mercury pours
    "nsx_absinthe_night":    (("vinyl", "satin", "eggshell", "clear_matte"),
                              ("mercury", "spectraflame", "chrome_veil")),
    # a RECESS: cells with walls, so the day deck is dark and the charge is in the seams
    "nsx_toxic_recess":      (("flat_black", "satin_carbon", "matte", "powder"),
                              ("chrome", "candy_chrome", "steel_dark")),
    # pool chemistry: wet-looking vinyl, clean chlorine metal
    "nsx_chlorine_watch":    (("vinyl", "eggshell", "ceramic_matte", "satin"),
                              ("chrome", "satin_chrome", "chrome_veil")),
    # violet POWDER COAT, named as such; lime burns out of every crack
    "nsx_lime_interrogation": (("powder", "ceramic_matte", "flat_black", "matte"),
                               ("spectraflame", "candy_chrome", "chrome_dry")),
    # a serpent SHEDS — the day deck is skin-like, the night is wet scale
    "nsx_serpent_shift":     (("vinyl", "satin", "matte", "satin_carbon"),
                              ("mercury", "spectraflame", "pewter_metal")),
    # cold plates over a glow that only shows at the edges
    "nsx_uranium_dusk":      (("satin_carbon", "flat_black", "clear_matte", "eggshell"),
                              ("candy_chrome", "spectraflame", "mirror_deep")),
    # wormwood is a dry bitter herb — chalk and powder
    "nsx_wormwood_vigil":    (("eggshell", "powder", "ceramic_matte", "vinyl"),
                              ("chrome", "dark_chrome", "chrome_dry")),
    # acid under a cold blue-violet surface
    "nsx_acid_testament":    (("clear_matte", "matte", "satin", "flat_black"),
                              ("spectraflame", "chrome", "pewter_metal")),
    # hemlock behind an orchid front — soft, waxy, poisonous
    "nsx_hemlock_hour":      (("matte", "vinyl", "eggshell", "ceramic_matte"),
                              ("candy_chrome", "mercury", "chrome_veil")),

    # ── 🌗 REGALIA — court colours, olive/green by day ─────────────────────
    # an olive COURT: sober, flat, and violet takes the throne
    "nsx_royal_nightfall":   (("matte", "clear_matte", "eggshell", "flat_black"),
                              ("mercury", "candy_chrome", "mirror_deep")),
    # a green bench, rose verdict delivered along the veins
    "nsx_rose_assize":       (("eggshell", "satin", "powder", "matte"),
                              ("candy_chrome", "mercury", "pewter_metal")),
    # cold ceramic sentenced to GILT — gilding is thin, bright, slightly antique
    "nsx_gilt_sentence":     (("ceramic_matte", "clear_matte", "satin", "vinyl"),
                              ("spectraflame", "antique_chrome", "bronze_raw")),
    # moss drifting to amethyst; imperial means deep and liquid
    "nsx_imperial_drift":    (("clear_matte", "powder", "vinyl", "eggshell"),
                              ("mercury", "chrome", "mirror_deep")),
    # an orchid petal has a waxy bloom — vinyl leads
    "nsx_orchid_curfew":     (("vinyl", "eggshell", "ceramic_matte", "flat_black"),
                              ("candy_chrome", "mercury", "chrome_veil")),
    # watch-plates: hard, lifted, cardinal red underneath every edge
    "nsx_cardinal_watch":    (("matte", "satin_carbon", "powder", "clear_matte"),
                              ("chrome", "candy_chrome", "steel_dark")),
    # a powder-green BED with amethyst working up through it
    "nsx_amethyst_bench":    (("powder", "matte", "vinyl", "satin"),
                              ("satin_chrome", "mercury", "pewter_metal")),
    # gold creases at noon; coronation blue is ceremonial and deep
    "nsx_coronation_blue":   (("matte", "eggshell", "satin_carbon", "ceramic_matte"),
                              ("mercury", "chrome", "mirror_deep")),
    # fern ground, fuchsia SPARKS — the night deck must be the brightest
    "nsx_fuchsia_docket":    (("eggshell", "vinyl", "powder", "satin"),
                              ("candy_chrome", "chrome", "spectraflame")),
    # the last session: sea-green giving way to crimson, everything cooling
    "nsx_last_session":      (("clear_matte", "satin", "matte", "ceramic_matte"),
                              ("chrome", "dark_chrome", "chrome_veil")),
}


@lru_cache(maxsize=1)
def _checked_decks():
    """Validate the hand-authored table at import.

    Three things must hold, and a violation is an ImportError rather than a
    quiet degradation, because that is exactly how this shelf shipped with ten
    material stories across fifty finishes.
    """
    missing = sorted(set(NIGHTSHIFT) - set(DECKS))
    extra = sorted(set(DECKS) - set(NIGHTSHIFT))
    if missing or extra:
        raise ValueError("NIGHTSHIFT deck table out of sync — missing %s, unknown %s"
                         % (missing, extra))
    for fid, (dd, nn) in DECKS.items():
        bad_d = [c for c in dd if c not in DAY_CARDS]
        bad_n = [c for c in nn if c not in NIGHT_CARDS]
        if bad_d or bad_n:
            # the day/night family split IS the flip mechanism
            raise ValueError("%s breaks the population split: day%s night%s" % (fid, bad_d, bad_n))
    seen = {}
    for fid, (dd, nn) in DECKS.items():
        seen.setdefault((frozenset(dd), frozenset(nn)), []).append(fid)
    clash = {k: v for k, v in seen.items() if len(v) > 1}
    if clash:
        raise ValueError("NIGHTSHIFT duplicate material stories: " + "; ".join(
            "%s" % (", ".join(sorted(v))) for v in clash.values()))
    return {fid: (tuple(sorted(dd, key=lambda c: -SC.CARDS[c][1])),
                  tuple(sorted(nn, key=lambda c: -SC.CARDS[c][1])))
            for fid, (dd, nn) in DECKS.items()}


def decks_for(fid):
    return _checked_decks()[fid]


@lru_cache(maxsize=8)
def _pop(fid):
    """(night-population mask, cell labels) at GEN.

    The mask is cut at a PERCENTILE of the structure field so the night share
    is exactly what the recipe asks for whatever the field's histogram looks
    like — the bench showed the whole effect lives between 0.35 and 0.50, so
    landing on it by accident is not good enough.
    """
    d = NIGHTSHIFT[fid]
    # the finish's OWN hand-authored construction, not one of twelve shared ones
    f, _lab_unused = _designed_field(fid, (GEN, GEN), d["seed"])
    # always a dedicated fine lattice, never the structure's own labels
    _dd, lab = FK.worley((GEN, GEN), d["seed"] + 5, cells=int(d.get("shade_cells", 178)))
    # decide per CELL, so the two populations interleave as coherent 8-32px
    # material patches rather than per-pixel confetti
    # `flatten` is how much of the construction is averaged into its cells.
    # 0.0 keeps the geometry intact, which is right for anything with real
    # structure of its own; plate-like finishes can dial it up.
    flat = float(d.get("flatten", 0.0))
    fc = (FK.cell_mean(f, lab) * flat + f * (1.0 - flat)) if flat > 0 else f
    # DITHER THE POPULATION BOUNDARY at cell scale. A smooth structure field
    # (a burn front, a filament net, a dendrite) crosses the threshold along one
    # long smooth contour, so the car's single biggest contrast — day hue against
    # night hue — lands at macro scale and the finish fails the car-band law
    # however fine its shading is. Adding per-cell noise before the cut makes
    # cells NEAR the threshold flip individually, which is both what a real
    # two-phase material does at its interface and what puts that contrast in
    # the 8-32px window. Cells far from the threshold are unaffected, so the
    # structure keeps its character.
    jit = float(d.get("pop_jit", 0.09))
    if jit > 0:
        # A COHERENT fine field, not per-cell white noise. Dithering the
        # boundary with a per-cell hash does put energy in the car band, but it
        # puts it there as salt-and-pepper: neighbouring cells disagree at
        # random and the car reads as confetti, which is the one thing the owner
        # has rejected most often. A band-limited field at 4-10px instead makes
        # small GROUPS of cells flip together, so the interface breaks into
        # flecks, scales and streaks — in the same 8-32px window, but shaped.
        fine = FK.fbm((GEN, GEN), d["seed"] + 71, octaves=(96, 192, 384),
                      weights=(0.55, 1.0, 0.7))
        fine_c = FK.cell_mean(fine, lab) if flat > 0 else fine
        fc = fc + (fine_c - 0.5) * 2.0 * jit * float(fc.std() + 1e-6) * 3.4
    # THE DENSITY IS COMPOSED, not uniform. Both populations have to be present
    # everywhere for the flip to work, but nothing says they must be present in
    # the same PROPORTION everywhere — and a constant proportion is what makes a
    # two-population field read as flat noise instead of as paint. Letting the
    # local share drift between roughly 0.20 and 0.62 across a slow field gives
    # the car drifts, banks and clearings of each colour, which is how a real
    # two-tone flake finish actually looks, while the global mean stays on the
    # 0.35-0.50 the flip needs.
    share = float(d["share"])
    comp = float(d.get("compose", 0.20))
    if comp > 0:
        slow = FK.fbm((GEN, GEN), d["seed"] + 137, octaves=(3, 6, 12, 24),
                      weights=(1.0, 0.85, 0.5, 0.28))
        slow = FK.cell_mean(slow, lab) if flat > 0 else slow
        local = np.clip(share + (slow - 0.5) * 2.0 * comp, 0.24, 0.62)
    else:
        local = np.full(fc.shape, share, np.float32)
    # rank each cell inside the field, then keep the top `local` fraction - a
    # spatially varying threshold, done by rank so the field's own shape leads
    # one argsort + scatter instead of argsort(argsort(...)); identical ranks,
    # half the sorting on a 1M-element field
    _o = np.argsort(fc.ravel())
    order = np.empty(fc.size, np.float32)
    order[_o] = np.arange(fc.size, dtype=np.float32)
    order /= max(fc.size - 1, 1)
    keep = (1.0 - order.reshape(fc.shape)) < local
    return keep, lab, FK.pct(f)


@lru_cache(maxsize=6)
def _art(fid):
    d = NIGHTSHIFT[fid]
    night, lab, field = _pop(fid)
    night = FK.upscale(night.astype(np.float32), WORK) > 0.5
    lab = FK.upscale(lab, WORK)
    field = FK.upscale(field, WORK)

    from engine.expansions import nightshift_design_2026 as ND
    from engine.expansions import nightshift_forms_2026 as NF
    pt = ND.PAINT[fid]

    # THE TREATMENT IS PER FINISH. A single shared treatment is what kept this
    # shelf at TWIN 0.98-0.99 even after all fifty had their own construction:
    # an 8-tier per-cell ladder plus a fixed grain flattens thirty-one different
    # geometries into one statistical signature.
    tiers = int(pt["tiers"])
    if tiers <= 0:
        # continuous - no ladder at all, the construction's own value shades it
        step = np.clip(field, 0.0, 1.0)
    elif pt["ladder"] == "field":
        step = (np.clip((np.clip(field, 0, 1) * tiers).astype(np.int32), 0, tiers - 1)
                .astype(np.float32) / max(tiers - 1, 1))
    else:
        tt = FK._h1(lab, 31 + d["seed"])
        step = (np.clip((tt * tiers).astype(np.int32), 0, tiers - 1).astype(np.float32)
                / max(tiers - 1, 1))

    # Both populations carry the owner's shade ladder; the night one is kept
    # SATURATED, because a near-white night albedo is precisely what makes a
    # car blow out to white instead of changing colour.
    day = _hsv(d["day_h"], d["day_s"], 1.0, (WORK, WORK)) * (0.55 + 0.75 * step)[..., None] * d["day_v"] * 2.0
    ngt = _hsv(d["night_h"], d["night_s"], 1.0, (WORK, WORK)) * (0.60 + 0.70 * step)[..., None] * d["night_v"] * 2.0
    shade = (1.0 - float(pt["shade"]) + float(pt["shade"]) * 2.0 * field)[..., None]
    art = np.where(night[..., None], ngt, day * shade)

    if cv2 is not None:
        hsv = cv2.cvtColor(np.clip(art, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
        hsv[..., 0] = np.mod(hsv[..., 0] + (FK._h1(lab, 97) - 0.5) * float(pt["wobble"]), 360.0)
        hsv[..., 1] = np.clip(hsv[..., 1] * (0.90 + 0.20 * FK._h1(lab, 149)), 0, 1)
        art = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        # the finish's OWN keyed detail, not one shared fbm. Keyed detail also
        # keeps the paint's detail envelope structured, which is what makes the
        # spec able to follow it at all.
        g, _key = NF.detail(field, d["seed"] + 3, kind=pt["grain"], amount=1.0, res=WORK)
        art = art * (1.0 + (g - 0.5) * 2.0 * float(pt["gamt"]))[..., None]
    return np.clip(art, 0, 1).astype(np.float32)


def _spec_at(fid, res):
    """The finish's hand-authored material story, laid on its own artwork.

    SPB-105 / owner 2026-09-01. Two owner verdicts drive this function:
    "the specs should be diverse, unique, follow the pattern of the base paint
    and MAKE SENSE", and "HAND AUTHOR EVERYTHING. NO DUPLICATES."

    The deck comes from DECKS (hand written, one per finish, materials chosen to
    mean the finish's name). The LAYOUT comes from spec_story.compose against the
    RENDERED PAINT, so every material boundary sits on a tonal boundary of the
    artwork. Composing against the pre-paint field instead measured FOLLOW 0.05-
    0.33 across this shelf; composing against the paint measured 0.665 on the
    first finish converted.
    """
    from engine.paint_v2 import spec_story as ST
    from engine.expansions import nightshift_design_2026 as ND

    d = NIGHTSHIFT[fid]
    day_deck, night_deck = decks_for(fid)
    _form, _params, _kind, _amount, edge = ND.DESIGN[fid]

    field, lab = _designed_field(fid, (GEN, GEN), d["seed"])
    field = FK.upscale(field, res)
    lab = FK.upscale(lab, res) if lab is not None else None
    if lab is None:
        # built at 512 and NEAREST-upscaled: a label field feeds cell_mean and
        # per-cell hashes, so it needs correct cell IDENTITY, not resolution.
        # Generating it at 2048 measured 2.86s of a 3s budget.
        lw = min(512, res)
        _dd, lab = FK.worley((lw, lw), d["seed"] + 5,
                             cells=int(d.get("shade_cells", 178) * lw / 2048.0 * 4.0))
        if lw != res and cv2 is not None:
            lab = cv2.resize(lab.astype(np.float32), (res, res),
                             interpolation=cv2.INTER_NEAREST).astype(np.int32)

    art = _art(fid)
    if art.shape[0] != res:
        art = cv2.resize(np.asarray(art, np.float32), (res, res),
                         interpolation=cv2.INTER_LINEAR)

    # Day cards run the dull end of the deck and night cards the sharp end;
    # spec_story orders roughness-descending, so concatenating day+night keeps
    # the two populations in their own halves of the ladder and the flip
    # mechanism survives.
    deck = tuple(day_deck) + tuple(night_deck)
    tune = getattr(ND, "SPEC_TUNE", {}).get(fid, {})
    return ST.compose(field, deck, seed=d["seed"], res=res, lab=lab,
                      edge=edge, art=art, **tune)


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
        return (spec.astype(np.float32) * mm).clip(0, 255).astype(np.uint8)

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    regs = [mono_reg]
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys as _sys
    _eng = _sys.modules.get("shokker_engine_v2")
    if _eng is not None and hasattr(_eng, "FUSION_REGISTRY"):
        regs.append(_eng.FUSION_REGISTRY)
    for fid in NIGHTSHIFT:
        entry = _mk(fid)
        for reg in regs:
            try:
                reg[fid] = entry
            except Exception:
                pass
    return "%d day/night flips live" % len(NIGHTSHIFT)
