# -*- coding: utf-8 -*-
"""🪩 FAR OUT — the 1970s. ★ OPTIC LAB rebuilt, 50 → 60.

Owner: *"OPTIC LAB — currently 50 finishes of kind of bullshit here too. Let's
totally rework this category as well. We already have SOCK HOP for 1950s looks,
GROOVY VIBES for 1960s looks, how about we make OPTIC LAB totally 1970s —
DISCO, SHAG CARPET LOOKS, OUTLAW COUNTRY WESTERN, etc."*

WHAT WAS THERE. Fifty ids across five sub-lanes that were really five separate
one-off modules bolted together: `flash_stone` minerals, `night_bloom`
retroreflective sheeting, `two_face` split flips, `fluid_pour` acrylic pours and
`sequin_disco`. Only the last had anything to do with a decade. As a category it
said "optical effects", which is a technique, not a story — and half the catalog
is optical effects.

THE DECADE. Four rooms of the 1970s, fifteen each:

  🪩 DISCO      the floor, the ball, the lurex, the roller rink
  🟫 SHAG       the sunken living room — pile, panelling, avocado, macramé
  🤠 OUTLAW     tooled leather, turquoise and silver, denim, the rhinestone suit
  🚐 VAN ART    airbrushed murals, metalflake, pinstripe, the shag-lined van

MATERIALS. Owner: *"DO NOT just automatically make them all Fractured styles…
SOME finishes should lean flat, chalky, glossy, wet, GLITTERY."* The 1970s are
unusually good for that because the decade genuinely ran the whole range at
once: a mirror ball and a brown corduroy beanbag were in the same room. This
shelf uses 18 of the 27 material decks and reaches for the Fractured rail on 7
of 60 — the ball, the lurex and the four hottest airbrush cards.
"""
from __future__ import annotations

from engine.paint_v2 import era_base_2026 as EB
from engine.paint_v2 import era_kit_2026 as K

ID_PREFIX = "fo_"
GROUP = "🪩 FAR OUT"
LANES = {"disco": "🪩 DISCO", "shag": "🟫 SHAG", "outlaw": "🤠 OUTLAW",
         "van": "🚐 VAN ART"}

_STRUCTS = {
    "discs":     lambda sh, sd, k: (K.discs(sh, sd, **k), None),
    "shag":      lambda sh, sd, k: (K.shag(sh, sd, **k), None),
    "tooled":    lambda sh, sd, k: (K.tooled(sh, sd, **k), None),
    "splatter":  lambda sh, sd, k: (K.splatter(sh, sd, **k), None),
    "holo":      lambda sh, sd, k: (K.holo(sh, sd, **k), None),
    "scales":    lambda sh, sd, k: (K.scales(sh, sd, **k), None),
    "topo":      lambda sh, sd, k: (K.topo(sh, sd, **k), None),
    "sett":      lambda sh, sd, k: (K.sett(sh, sd, **k), None),
    "stars":     lambda sh, sd, k: (K.stars(sh, sd, **k), None),
    "ikat":      lambda sh, sd, k: (K.ikat(sh, sd, **k), None),
    "bands":     lambda sh, sd, k: (K.bands(sh, sd, **k), None),
    "curl":      lambda sh, sd, k: (K.curl(sh, sd, **k), None),
    "filaments": lambda sh, sd, k: (K.filaments(sh, sd, **k), None),
    "braid":     lambda sh, sd, k: (K.kh_braid(sh, sd, **k), None),
    "dendrite":  lambda sh, sd, k: (K.dla(sh, sd, **k), None),
    "sparks":    lambda sh, sd, k: (K.sparks(sh, sd, **k), None),
    "craters":   lambda sh, sd, k: (K.craters(sh, sd, **k), None),
    "dunes":     lambda sh, sd, k: (K.dunes(sh, sd, **k), None),
    "cells":     lambda sh, sd, k: K.worley(sh, sd, **k),
    "percolate": lambda sh, sd, k: K.percolate(sh, sd, **k),
    "spall":     lambda sh, sd, k: K.spall(sh, sd, **k),
    "crack":     lambda sh, sd, k: K.anneal_crack(sh, sd, **k),
    "polygons":  lambda sh, sd, k: K.polygons(sh, sd, **k),
    "honeycomb": lambda sh, sd, k: K.honeycomb(sh, sd, **k),
    "wrinkle":   lambda sh, sd, k: (K.wrinkle(sh, sd, **k), None),
    "eden":      lambda sh, sd, k: (K.eden(sh, sd, **k), None),
    "moire":     lambda sh, sd, k: (K.moire(sh, sd, **k), None),
    "knurl":     lambda sh, sd, k: (K.knurl(sh, sd, **k), None),
    "facets":    lambda sh, sd, k: K.facets(sh, sd, **k),
    "guilloche": lambda sh, sd, k: (K.guilloche(sh, sd, **k), None),
    "crinkle":   lambda sh, sd, k: (K.crinkle(sh, sd, **k), None),
}

P = {
    # DISCO — the floor is lit, everything else is not
    "mirrorball": ((0.10, 0.11, 0.13), (0.36, 0.39, 0.44), (0.66, 0.70, 0.76), (0.96, 0.98, 1.00)),
    "floorlit":   ((0.10, 0.04, 0.14), (0.44, 0.08, 0.36), (0.16, 0.44, 0.62), (0.96, 0.82, 0.30)),
    "lurex_gold": ((0.14, 0.09, 0.02), (0.46, 0.32, 0.06), (0.76, 0.58, 0.16), (0.99, 0.88, 0.48)),
    "lurex_rose": ((0.14, 0.05, 0.09), (0.44, 0.13, 0.26), (0.74, 0.36, 0.52), (0.98, 0.76, 0.86)),
    "rollerink":  ((0.06, 0.07, 0.16), (0.18, 0.16, 0.46), (0.52, 0.24, 0.62), (0.92, 0.70, 0.94)),
    "studio54":   ((0.08, 0.06, 0.08), (0.30, 0.14, 0.22), (0.62, 0.44, 0.24), (0.98, 0.90, 0.60)),
    "hustle":     ((0.05, 0.10, 0.12), (0.12, 0.34, 0.38), (0.36, 0.62, 0.62), (0.84, 0.94, 0.92)),
    # SHAG — the sunken living room
    "avocado":    ((0.10, 0.11, 0.04), (0.30, 0.32, 0.10), (0.52, 0.55, 0.22), (0.78, 0.80, 0.46)),
    "harvest":    ((0.16, 0.10, 0.02), (0.48, 0.32, 0.05), (0.76, 0.56, 0.14), (0.96, 0.82, 0.40)),
    "burntorange":((0.16, 0.06, 0.02), (0.48, 0.18, 0.05), (0.76, 0.36, 0.12), (0.95, 0.62, 0.32)),
    "walnut":     ((0.10, 0.06, 0.03), (0.28, 0.18, 0.10), (0.50, 0.34, 0.20), (0.74, 0.58, 0.38)),
    "macrame":    ((0.24, 0.20, 0.14), (0.52, 0.46, 0.34), (0.76, 0.70, 0.56), (0.94, 0.90, 0.78)),
    "teal70":     ((0.04, 0.11, 0.12), (0.10, 0.32, 0.34), (0.30, 0.56, 0.56), (0.70, 0.86, 0.84)),
    "chocolate":  ((0.08, 0.05, 0.03), (0.24, 0.15, 0.09), (0.44, 0.30, 0.19), (0.68, 0.52, 0.36)),
    # OUTLAW — leather, silver, denim, rhinestone
    "saddle":     ((0.12, 0.07, 0.03), (0.36, 0.21, 0.09), (0.60, 0.40, 0.20), (0.84, 0.66, 0.42)),
    "turquoise":  ((0.04, 0.13, 0.14), (0.10, 0.40, 0.42), (0.30, 0.66, 0.66), (0.72, 0.92, 0.90)),
    "denim70":    ((0.06, 0.09, 0.15), (0.16, 0.24, 0.40), (0.36, 0.48, 0.66), (0.68, 0.78, 0.90)),
    "nudie":      ((0.10, 0.08, 0.10), (0.34, 0.28, 0.34), (0.70, 0.62, 0.66), (0.99, 0.96, 0.98)),
    "rodeo_dust": ((0.16, 0.12, 0.07), (0.42, 0.34, 0.20), (0.68, 0.58, 0.38), (0.92, 0.85, 0.64)),
    "blackhat":   ((0.05, 0.05, 0.06), (0.16, 0.16, 0.18), (0.34, 0.34, 0.37), (0.60, 0.60, 0.64)),
    "sunset_mesa":((0.14, 0.05, 0.06), (0.44, 0.16, 0.12), (0.76, 0.40, 0.20), (0.97, 0.74, 0.42)),
    # VAN ART — airbrush, flake, pinstripe
    "vanmural":   ((0.05, 0.05, 0.14), (0.16, 0.14, 0.44), (0.52, 0.28, 0.62), (0.96, 0.72, 0.44)),
    "flake_blue": ((0.03, 0.06, 0.16), (0.08, 0.20, 0.48), (0.26, 0.44, 0.78), (0.72, 0.86, 0.99)),
    "flake_red":  ((0.12, 0.02, 0.04), (0.40, 0.05, 0.09), (0.72, 0.18, 0.20), (0.96, 0.56, 0.48)),
    "candy_apple":((0.10, 0.02, 0.03), (0.36, 0.04, 0.07), (0.70, 0.14, 0.16), (0.95, 0.50, 0.42)),
    "pinstripe":  ((0.06, 0.06, 0.07), (0.20, 0.20, 0.22), (0.62, 0.56, 0.30), (0.96, 0.90, 0.54)),
    "eagle_gold": ((0.14, 0.09, 0.03), (0.44, 0.30, 0.07), (0.74, 0.56, 0.18), (0.98, 0.86, 0.46)),
    "sunstripe":  ((0.14, 0.04, 0.02), (0.48, 0.16, 0.03), (0.82, 0.44, 0.08), (0.99, 0.80, 0.34)),
}


def R(name, lane, palette, deck, seed, stack, desc, mix="sum", edge=None,
      dither=0.15, r_spread=26.0, gamma=1.0, hue_jitter=13.0, cell_mean=1.0):
    return dict(name=name, lane=lane, palette=palette, deck=deck, seed=seed,
                stack=stack, desc=desc, mix=mix, edge=edge, dither=dither,
                r_spread=r_spread, gamma=gamma, hue_jitter=hue_jitter,
                cell_mean=cell_mean)


_ROWS = [
    # ══════════════════════ 🪩 DISCO (15) ══════════════════════════════════
    R("Mirror Ball", "disco", "mirrorball", "sequin", 9101,
      [("discs", 1.0, dict(n=3200, radius=13.0, tilt=0.8)), ("cells", 0.5, dict(cells=168))],
      "A thousand glass tiles on a motor, each throwing the same light somewhere else.", edge="chrome"),
    R("Lighted Floor", "disco", "floorlit", "plastic", 9102,
      [("polygons", 1.0, dict(cells=88, relief=0.55)), ("moire", 0.5, dict(lpi=150, depth=0.4))],
      "Perspex squares lit from underneath, each one changing on its own count."),
    R("Lurex Gold", "disco", "lurex_gold", "lurex", 9103,
      [("braid", 1.0, dict(layers=118, shear=1.5)), ("filaments", 0.7, dict(n=2600, length=12, wander=0.7))],
      "Metallic thread woven through the knit so the whole shirt is a light source."),
    R("Lurex Rose", "disco", "lurex_rose", "lurex", 9104,
      [("braid", 1.0, dict(layers=104, shear=2.1)), ("discs", 0.55, dict(n=1600, radius=8.0))],
      "The same thread in rose gold, on a body-con knit that has no give in it at all."),
    R("Roller Rink", "disco", "rollerink", "gloss", 9105,
      [("bands", 1.0, dict(n=96, shear=1.4, vortex=14, turb=0.4)), ("craters", 0.5, dict(n=2600, rmax=5.0))],
      "Sealed maple under blacklight, with forty years of wheel polish on it."),
    R("Studio Gold", "disco", "studio54", "gold", 9106,
      [("guilloche", 1.0, dict(period=92, ring=12)), ("sparks", 0.55, dict(n=2600, life=22))],
      "Gilt, mirror and a doorman. The room was mostly dark and entirely gold."),
    R("Hustle Teal", "disco", "hustle", "satin", 9107,
      [("ikat", 1.0, dict(rows=54, motifs=1000, blur=8)), ("cells", 0.5, dict(cells=160))],
      "Polyester in a colour that only existed for about six years."),
    R("Glitter Ball Rain", "disco", "mirrorball", "glitter", 9108,
      [("sparks", 1.0, dict(n=3400, life=30, spread=1.8)), ("discs", 0.6, dict(n=1400, radius=7.0))],
      "The dots the ball throws, moving across everything in the room at once."),
    R("Sequin Sheet", "disco", "lurex_rose", "sequin", 9109,
      [("discs", 1.0, dict(n=4200, radius=9.0, tilt=0.6, facet=1.2)), ("cells", 0.45, dict(cells=172))],
      "Overlapping paillettes stitched in courses, every one free to flip.", edge="mercury"),
    R("Boogie Neon", "disco", "floorlit", "neon", 9110,
      [("filaments", 1.0, dict(n=900, length=52, wander=0.28)), ("holo", 0.6, dict(rings=300))],
      "Bent tube in three colours, buzzing, with the transformer hum you can feel."),
    R("Velvet Rope", "disco", "studio54", "velvet", 9111,
      [("shag", 1.0, dict(strands=4200, length=30)), ("braid", 0.5, dict(layers=96, shear=1.2))],
      "Crushed velvet, the deepest black in the building and the softest thing in it."),
    R("Platform Patent", "disco", "rollerink", "wet", 9112,
      [("wrinkle", 1.0, dict(k=1.1, steps=16, scale=150)), ("cells", 0.55, dict(cells=158))],
      "Patent leather on a four-inch stack — a mirror you can walk in."),
    R("Vinyl Groove", "disco", "blackhat", "gloss", 9113,
      [("guilloche", 1.0, dict(period=58, ring=7, teeth=(3, 5))), ("cells", 0.4, dict(cells=176))],
      "A twelve-inch single, lit from the side so the groove pitch shows."),
    R("Discotheque Haze", "disco", "hustle", "glass", 9114,
      [("curl", 1.0, dict(scale=54, steps=20)), ("sparks", 0.5, dict(n=2200, life=26))],
      "Dry ice and cigarette smoke holding the beams up where you can see them."),
    R("Saturday Chrome", "disco", "mirrorball", "chrome", 9115,
      [("facets", 1.0, dict(stones=190, table=0.34)), ("knurl", 0.5, dict(pitch=30))],
      "The white suit was the exception. Everything else in that club was chrome.", edge="chrome"),

    # ══════════════════════ 🟫 SHAG (15) ═══════════════════════════════════
    R("Shag Avocado", "shag", "avocado", "velvet", 9201,
      [("shag", 1.0, dict(strands=5600, length=52, splay=1.0))],
      "Two inches of pile in a colour named after a fruit, and a rake to comb it."),
    R("Shag Harvest", "shag", "harvest", "velvet", 9202,
      [("shag", 1.0, dict(strands=5200, length=46, splay=0.8)), ("cells", 0.4, dict(cells=170))],
      "Harvest gold, the other colour every appliance came in."),
    R("Conversation Pit", "shag", "burntorange", "suede", 9203,
      [("braid", 1.0, dict(layers=88, shear=1.0)), ("wrinkle", 0.6, dict(k=1.0, steps=14))],
      "Burnt orange upholstery on a sunken bench you had to step down into."),
    R("Wood Panel", "shag", "walnut", "satin", 9204,
      [("bands", 1.0, dict(n=104, shear=1.5, vortex=7, turb=0.34)),
       ("filaments", 0.6, dict(n=1500, length=28, wander=0.16))],
      "Photo-printed walnut on hardboard, and nobody minded that it was fake."),
    R("Macramé Hang", "shag", "macrame", "chalk", 9205,
      [("braid", 1.0, dict(layers=72, shear=2.4)), ("filaments", 0.75, dict(n=2000, length=34, wander=0.5))],
      "Jute knotted into a plant hanger by somebody in the family."),
    R("Linoleum Teal", "shag", "teal70", "plastic", 9206,
      [("craters", 1.0, dict(n=3200, rmax=5.5)), ("polygons", 0.5, dict(cells=120, relief=0.35))],
      "Sheet vinyl with a repeating pattern designed to hide absolutely everything."),
    R("Popcorn Ceiling", "shag", "macrame", "chalk", 9207,
      [("percolate", 1.0, dict(cells=182, p=0.5)), ("craters", 0.6, dict(n=3600, rmax=4.5))],
      "Sprayed texture with a little sparkle in it, and asbestos, probably."),
    R("Fondue Copper", "shag", "burntorange", "gold", 9208,
      [("craters", 1.0, dict(n=2200, rmax=8.0, rim=0.7)), ("cells", 0.5, dict(cells=150))],
      "Hammered copper on the good pot, brought out for guests four times a year."),
    R("Corduroy Brown", "shag", "chocolate", "suede", 9209,
      [("braid", 1.0, dict(layers=80, shear=0.8)), ("dunes", 0.5, dict(n=42))],
      "Wide wale, worn at the knee, in the brown that swallowed every room."),
    R("Tab Curtain", "shag", "harvest", "eggshell", 9210,
      [("sett", 1.0, dict(pitch=52, stripes=(0.30, 0.12, 0.08, 0.22, 0.08, 0.14)))],
      "Barkcloth with a bold repeat, hung on wooden rings that never ran smoothly."),
    R("Rattan Weave", "shag", "macrame", "satin", 9211,
      [("braid", 1.0, dict(layers=110, shear=1.8)), ("cells", 0.55, dict(cells=154))],
      "A peacock chair nobody could actually sit in comfortably."),
    R("Terrazzo Kitchen", "shag", "avocado", "plastic", 9212,
      [("craters", 1.0, dict(n=3400, rmax=7.5, rim=0.8)), ("cells", 0.6, dict(cells=140))],
      "Chips of everything set in resin and ground flat, indestructible."),
    R("Lava Lamp", "shag", "burntorange", "glass", 9213,
      [("curl", 1.0, dict(scale=40, steps=22)), ("percolate", 0.5, dict(cells=160))],
      "Wax rising in a column, never quite the same shape twice."),
    R("Smoked Glass", "shag", "chocolate", "glass", 9214,
      [("crinkle", 1.0, dict(scale=130, sharp=2.4)), ("cells", 0.5, dict(cells=166))],
      "Bronze-tinted glass in the coffee table and the shower door alike."),
    R("Formica Boomerang", "shag", "teal70", "plastic", 9215,
      [("stars", 1.0, dict(cell=78, points=6, interlace=0.5)), ("cells", 0.5, dict(cells=164))],
      "Laminate with the little shapes on it, and a chrome edge strip."),

    # ══════════════════════ 🤠 OUTLAW (15) ═════════════════════════════════
    R("Tooled Saddle", "outlaw", "saddle", "suede", 9301,
      [("tooled", 1.0, dict(cell=52, petals=6)), ("cells", 0.45, dict(cells=168))],
      "Sheridan floral cut with a swivel knife and beveled by hand, one stamp at a time."),
    R("Basket Stamp", "outlaw", "saddle", "suede", 9302,
      [("tooled", 1.0, dict(cell=38, petals=4, stamp=0.7, bevel=0.8)), ("cells", 0.4, dict(cells=172))],
      "The other tooling: a basketweave stamp walked across the whole skirt."),
    R("Turquoise Silver", "outlaw", "turquoise", "steel", 9303,
      [("crack", 1.0, dict(cells=120, width=2.6, gen=1)), ("knurl", 0.5, dict(pitch=34))],
      "Sleeping Beauty stone in a hand-stamped bezel, with the matrix showing."),
    R("Concho Row", "outlaw", "nudie", "chrome", 9304,
      [("discs", 1.0, dict(n=4200, radius=11.0, tilt=0.5, facet=0.8)),
       ("tooled", 0.5, dict(cell=48))],
      "Hammered silver discs down a belt, each one covering a stitch line.", edge="mercury"),
    R("Rhinestone Suit", "outlaw", "nudie", "glitter", 9305,
      [("sparks", 1.0, dict(n=4200, life=18, spread=1.2)), ("filaments", 0.5, dict(n=1400, length=30))],
      "A Nudie suit: chain stitch, cactus, and more stones than the wearer could afford.", edge="chrome"),
    R("Raw Denim", "outlaw", "denim70", "suede", 9306,
      [("braid", 1.0, dict(layers=120, shear=2.0)), ("filaments", 0.6, dict(n=2400, length=13, wander=0.7))],
      "Selvedge twill, unwashed, that will take a year to look like anything."),
    R("Rodeo Dust", "outlaw", "rodeo_dust", "chalk", 9307,
      [("dunes", 1.0, dict(n=46)), ("craters", 0.6, dict(n=3000, rmax=5.0))],
      "Arena dirt hanging in the light after eight seconds of work."),
    R("Black Hat", "outlaw", "blackhat", "velvet", 9308,
      [("shag", 1.0, dict(strands=4600, length=22, splay=0.5)), ("cells", 0.4, dict(cells=176))],
      "Beaver felt, brushed one way, the darkest thing anyone in the room owns."),
    R("Snakeskin Boot", "outlaw", "saddle", "gloss", 9309,
      [("scales", 1.0, dict(cell=24, keel=0.6)), ("cells", 0.45, dict(cells=162))],
      "Belly cut, lacquered, on a boot that cost more than the horse."),
    R("Mesa Sunset", "outlaw", "sunset_mesa", "eggshell", 9310,
      [("bands", 1.0, dict(n=76, shear=2.4, vortex=18, turb=0.5)), ("dunes", 0.5, dict(n=38))],
      "Sandstone in horizontal courses with the light going down behind it."),
    R("Barbed Wire", "outlaw", "blackhat", "oxide", 9311,
      [("filaments", 1.0, dict(n=800, length=64, wander=0.2)), ("sparks", 0.5, dict(n=1800, life=16))],
      "Four-point wire on cedar posts, rusted to the colour of the ground."),
    R("Longhorn Hide", "outlaw", "saddle", "suede", 9312,
      [("percolate", 1.0, dict(cells=132, p=0.44)), ("filaments", 0.6, dict(n=2600, length=11, wander=0.85))],
      "Brindle hide with the hair still on, thrown over the back of a chair."),
    R("Silver Buckle", "outlaw", "nudie", "steel", 9313,
      [("tooled", 1.0, dict(cell=44, petals=8, stamp=0.6)), ("facets", 0.55, dict(stones=210))],
      "A trophy buckle the size of a saucer, engraved and gold-washed."),
    R("Prairie Denim", "outlaw", "denim70", "chalk", 9314,
      [("sett", 1.0, dict(pitch=44, stripes=(0.34, 0.08, 0.06, 0.24, 0.08, 0.12), ratio=1.4)),
       ("filaments", 0.5, dict(n=1800, length=14))],
      "Chambray gone pale at the shoulders from a decade of sun."),
    R("Outlaw Chrome", "outlaw", "blackhat", "steel", 9315,
      [("knurl", 1.0, dict(pitch=20, angle=38)), ("spall", 0.5, dict(cells=118))],
      "Exhaust and a kick starter, wiped down with a rag every single night."),

    # ══════════════════════ 🚐 VAN ART (15) ════════════════════════════════
    R("Airbrush Mural", "van", "vanmural", "lacquer", 9401,
      [("curl", 1.0, dict(scale=46, steps=20)), ("holo", 0.5, dict(rings=280))],
      "A wizard, a wolf and a planet, on the side of a panel van, freehand."),
    R("Metalflake Blue", "van", "flake_blue", "flake", 9402,
      [("sparks", 1.0, dict(n=4600, life=14, spread=1.0)), ("cells", 0.5, dict(cells=168))],
      "Big flake laid heavy under clear, sanded and shot four more times.", edge="chrome"),
    R("Metalflake Red", "van", "flake_red", "flake", 9403,
      [("sparks", 1.0, dict(n=4200, life=16, spread=1.1)), ("craters", 0.45, dict(n=2400, rmax=4.5))],
      "The same flake in red, which shows every single flaw in the bodywork."),
    R("Candy Apple", "van", "candy_apple", "candy", 9404,
      [("curl", 1.0, dict(scale=52, steps=16)), ("cells", 0.5, dict(cells=160))],
      "Candy over a silver base, so the colour has depth you can look into."),
    R("Pinstripe Kit", "van", "pinstripe", "gloss", 9405,
      [("filaments", 1.0, dict(n=700, length=70, wander=0.14)), ("guilloche", 0.5, dict(period=104, ring=13))],
      "One-shot enamel pulled with a dagger brush, no tape, no second chances."),
    R("Sunset Stripe", "van", "sunstripe", "lacquer", 9406,
      [("bands", 1.0, dict(n=88, shear=1.2, vortex=6, turb=0.3)), ("sparks", 0.45, dict(n=2200, life=20))],
      "The graduated stripe down the flank, orange through yellow, on every van."),
    R("Eagle Gold", "van", "eagle_gold", "gold", 9407,
      [("tooled", 1.0, dict(cell=50, petals=5, stamp=0.5)), ("sparks", 0.6, dict(n=3000, life=18))],
      "Gold leaf laid over size and burnished, then outlined in black."),
    R("Porthole Chrome", "van", "pinstripe", "chrome", 9408,
      [("discs", 1.0, dict(n=3400, radius=13.0, tilt=0.4)), ("knurl", 0.6, dict(pitch=22))],
      "A bubble window and a chrome trim ring, because the van needed both."),
    R("Shag Interior", "van", "burntorange", "velvet", 9409,
      [("shag", 1.0, dict(strands=5000, length=42)), ("braid", 0.4, dict(layers=90, shear=1.4))],
      "The inside was carpeted. All of it. Including the ceiling."),
    R("CB Static", "van", "flake_blue", "steel", 9410,
      [("knurl", 1.0, dict(pitch=16, angle=42)), ("sparks", 0.6, dict(n=2800, life=18))],
      "A chromed mic, a whip antenna and forty channels of nothing much."),
    R("Desert Scene", "van", "sunset_mesa", "eggshell", 9411,
      [("dunes", 1.0, dict(n=40)), ("topo", 0.55, dict(lines=100, index=4))],
      "Airbrushed dunes with a saguaro in the middle distance, always."),
    R("Flame Job", "van", "sunstripe", "carrier", 9412,
      [("curl", 1.0, dict(scale=36, steps=22)), ("filaments", 0.5, dict(n=1200, length=40, wander=0.4))],
      "Licks laid out in tape, shot hot in the middle and cool at the tips."),
    R("Ghost Mural", "van", "vanmural", "pearl", 9413,
      [("holo", 1.0, dict(rings=320, orders=3)), ("curl", 0.55, dict(scale=58, steps=16))],
      "Pearl on pearl — invisible head-on and unmistakable from the kerb."),
    R("Wheel Well Rust", "van", "walnut", "oxide", 9414,
      [("percolate", 1.0, dict(cells=150, p=0.48)), ("spall", 0.6, dict(cells=104, lift=0.65))],
      "The part of the van the mural never reached, going back to the earth."),
    R("Tailgate Sunburst", "van", "eagle_gold", "carrier", 9415,
      [("guilloche", 1.0, dict(period=86, ring=11, teeth=(6, 9, 12))), ("sparks", 0.5, dict(n=2600, life=22))],
      "Rays out of a single point on the back doors, in six shades of the same idea."),
]


def _fid(name):
    return ID_PREFIX + name.lower().replace(" ", "_").replace("-", "_") \
        .replace("é", "e").replace("'", "")


FAR_OUT = {_fid(r["name"]): r for r in _ROWS}


def title(fid):
    return "%s: %s" % (FAR_OUT[fid]["lane"].title(), FAR_OUT[fid]["name"])


import sys as _sys                                            # noqa: E402
EB.make(_sys.modules[__name__], FAR_OUT, _STRUCTS, P)
