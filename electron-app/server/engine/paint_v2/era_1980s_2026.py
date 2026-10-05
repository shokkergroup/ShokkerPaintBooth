# -*- coding: utf-8 -*-
"""⚡ BAD & RAD — the 1980s. Marble & Onyx rebuilt, 20 → 60.

Owner: *"MARBLE & ONYX from the BASE CATEGORIES — tons of repeating designs in
here. LAZY… needs total rework. Make this one 1980s since we are going to flip
OPTIC LAB to 1970s. The 1980s with all of it's unique looks/vibes… Maybe the 80s
can be Bad and Rad."*

WHAT WAS THERE. Twenty stone finishes that were one veining algorithm recoloured
nineteen times — `marble_carrara`, `marble_calacatta`, `marble_nero`,
`marble_portoro`, `marble_statuario`, `marble_bardiglio`, `marble_rose`,
`marble_rosso`, `marble_verde_alpi`, `marble_fusion`, then the same field again
as four onyxes and an agate. The category name described the source photograph,
not a design idea.

THE DECADE. Four rooms, fifteen each:

  🕹 ARCADE     the cabinet, the CRT, the sprite, the marquee
  🌆 GRID       synthwave — the vector horizon, chrome type, VHS, laserdisc
  📐 MEMPHIS    Milano squiggles, terrazzo, jazz-cup confetti, pastel geometry
  🎸 RADICAL    hair metal, splatter, neon spandex, skate, airbrush

MATERIALS. The 1980s are the decade of PLASTIC and of NEON, and both are things
the catalog has been weak at, so this shelf leans on the `plastic`, `neon`,
`rubber`, `dichroic` and `glitter` decks far more than on metal. Eighteen decks
across the sixty; the Fractured rail is used five times, all of them where a
finish is genuinely meant to look like it is emitting light.
"""
from __future__ import annotations

from engine.paint_v2 import era_base_2026 as EB
from engine.paint_v2 import era_kit_2026 as K

ID_PREFIX = "rad_"
GROUP = "⚡ BAD & RAD"
LANES = {"arcade": "🕹 ARCADE", "grid": "🌆 GRID", "memphis": "📐 MEMPHIS",
         "radical": "🎸 RADICAL"}

_STRUCTS = {
    "scanline":  lambda sh, sd, k: (K.scanline(sh, sd, **k), None),
    "pixels":    lambda sh, sd, k: (K.pixels(sh, sd, **k), None),
    "wireframe": lambda sh, sd, k: (K.wireframe(sh, sd, **k), None),
    "glitch":    lambda sh, sd, k: (K.glitch(sh, sd, **k), None),
    "holo":      lambda sh, sd, k: (K.holo(sh, sd, **k), None),
    "squiggle":  lambda sh, sd, k: (K.squiggle(sh, sd, **k), None),
    "splatter":  lambda sh, sd, k: (K.splatter(sh, sd, **k), None),
    "discs":     lambda sh, sd, k: (K.discs(sh, sd, **k), None),
    "scales":    lambda sh, sd, k: (K.scales(sh, sd, **k), None),
    "topo":      lambda sh, sd, k: (K.topo(sh, sd, **k), None),
    "sett":      lambda sh, sd, k: (K.sett(sh, sd, **k), None),
    "stars":     lambda sh, sd, k: (K.stars(sh, sd, **k), None),
    "bands":     lambda sh, sd, k: (K.bands(sh, sd, **k), None),
    "curl":      lambda sh, sd, k: (K.curl(sh, sd, **k), None),
    "filaments": lambda sh, sd, k: (K.filaments(sh, sd, **k), None),
    "braid":     lambda sh, sd, k: (K.kh_braid(sh, sd, **k), None),
    "sparks":    lambda sh, sd, k: (K.sparks(sh, sd, **k), None),
    "craters":   lambda sh, sd, k: (K.craters(sh, sd, **k), None),
    "cells":     lambda sh, sd, k: K.worley(sh, sd, **k),
    "percolate": lambda sh, sd, k: K.percolate(sh, sd, **k),
    "spall":     lambda sh, sd, k: K.spall(sh, sd, **k),
    "crack":     lambda sh, sd, k: K.anneal_crack(sh, sd, **k),
    "polygons":  lambda sh, sd, k: K.polygons(sh, sd, **k),
    "honeycomb": lambda sh, sd, k: K.honeycomb(sh, sd, **k),
    "knurl":     lambda sh, sd, k: (K.knurl(sh, sd, **k), None),
    "facets":    lambda sh, sd, k: K.facets(sh, sd, **k),
    "moire":     lambda sh, sd, k: (K.moire(sh, sd, **k), None),
    "wrinkle":   lambda sh, sd, k: (K.wrinkle(sh, sd, **k), None),
    "dendrite":  lambda sh, sd, k: (K.dla(sh, sd, **k), None),
    "microtext": lambda sh, sd, k: (K.microtext(sh, sd, **k), None),
    "dunes":     lambda sh, sd, k: (K.dunes(sh, sd, **k), None),
}

P = {
    # ARCADE — a dark room, a lit screen
    "crt_green":  ((0.02, 0.05, 0.03), (0.04, 0.26, 0.10), (0.20, 0.66, 0.30), (0.72, 1.00, 0.80)),
    "crt_amber":  ((0.05, 0.03, 0.01), (0.28, 0.14, 0.02), (0.72, 0.42, 0.06), (1.00, 0.84, 0.42)),
    "coinop":     ((0.05, 0.04, 0.09), (0.34, 0.06, 0.26), (0.10, 0.42, 0.62), (0.98, 0.86, 0.22)),
    "sprite8":    ((0.04, 0.04, 0.12), (0.72, 0.14, 0.16), (0.16, 0.56, 0.30), (0.98, 0.90, 0.34)),
    "marquee":    ((0.06, 0.03, 0.08), (0.44, 0.06, 0.30), (0.86, 0.24, 0.10), (1.00, 0.92, 0.52)),
    "quarterbin": ((0.08, 0.07, 0.05), (0.28, 0.24, 0.14), (0.56, 0.48, 0.26), (0.86, 0.78, 0.48)),
    "attractmode":((0.03, 0.03, 0.10), (0.10, 0.10, 0.44), (0.36, 0.30, 0.80), (0.86, 0.82, 1.00)),
    # GRID — synthwave
    "gridpurple": ((0.05, 0.02, 0.12), (0.26, 0.05, 0.40), (0.72, 0.14, 0.56), (1.00, 0.62, 0.86)),
    "gridsun":    ((0.10, 0.02, 0.12), (0.52, 0.06, 0.30), (0.94, 0.30, 0.20), (1.00, 0.82, 0.30)),
    "chrometype": ((0.06, 0.07, 0.10), (0.30, 0.34, 0.42), (0.66, 0.72, 0.80), (0.98, 1.00, 1.00)),
    "vhs":        ((0.05, 0.05, 0.07), (0.24, 0.16, 0.30), (0.60, 0.32, 0.52), (0.94, 0.80, 0.88)),
    "laserdisc":  ((0.04, 0.06, 0.10), (0.10, 0.28, 0.46), (0.34, 0.62, 0.82), (0.86, 0.96, 1.00)),
    "outrun":     ((0.06, 0.02, 0.10), (0.34, 0.04, 0.34), (0.90, 0.18, 0.44), (1.00, 0.72, 0.42)),
    "miamivice":  ((0.05, 0.09, 0.12), (0.14, 0.40, 0.48), (0.92, 0.52, 0.70), (0.99, 0.94, 0.92)),
    # MEMPHIS — Milano, terrazzo, jazz cup
    "memphis":    ((0.08, 0.08, 0.10), (0.86, 0.20, 0.34), (0.16, 0.52, 0.72), (0.98, 0.88, 0.28)),
    "jazzcup":    ((0.10, 0.10, 0.12), (0.16, 0.30, 0.72), (0.86, 0.24, 0.44), (0.96, 0.96, 0.94)),
    "terrazzo80": ((0.20, 0.20, 0.21), (0.52, 0.52, 0.53), (0.78, 0.76, 0.74), (0.98, 0.97, 0.95)),
    "pastel_mint":((0.14, 0.24, 0.22), (0.40, 0.72, 0.64), (0.72, 0.94, 0.86), (0.98, 1.00, 0.98)),
    "pastel_peach":((0.22, 0.13, 0.12), (0.62, 0.38, 0.32), (0.92, 0.68, 0.58), (1.00, 0.92, 0.86)),
    "bacterio":   ((0.08, 0.08, 0.09), (0.28, 0.28, 0.30), (0.66, 0.66, 0.68), (0.98, 0.98, 0.99)),
    "squiggle80": ((0.09, 0.06, 0.12), (0.44, 0.14, 0.52), (0.20, 0.62, 0.58), (0.98, 0.86, 0.34)),
    # RADICAL — hair metal, splatter, skate
    "hairmetal":  ((0.07, 0.05, 0.09), (0.42, 0.10, 0.34), (0.84, 0.32, 0.24), (1.00, 0.88, 0.46)),
    "splattertee":((0.09, 0.09, 0.10), (0.72, 0.16, 0.24), (0.20, 0.58, 0.76), (0.98, 0.92, 0.30)),
    "spandex":    ((0.06, 0.04, 0.10), (0.20, 0.06, 0.44), (0.84, 0.14, 0.52), (1.00, 0.70, 0.88)),
    "skatedeck":  ((0.07, 0.06, 0.06), (0.34, 0.14, 0.10), (0.72, 0.32, 0.16), (0.96, 0.74, 0.36)),
    "neon_gym":   ((0.05, 0.09, 0.06), (0.14, 0.44, 0.16), (0.52, 0.90, 0.24), (0.94, 1.00, 0.66)),
    "tigerstripe80": ((0.08, 0.05, 0.02), (0.42, 0.20, 0.03), (0.86, 0.54, 0.10), (1.00, 0.90, 0.52)),
    "airbrush80": ((0.06, 0.04, 0.11), (0.28, 0.10, 0.46), (0.76, 0.26, 0.62), (1.00, 0.80, 0.92)),
}


def R(name, lane, palette, deck, seed, stack, desc, mix="sum", edge=None,
      dither=0.15, r_spread=26.0, gamma=1.0, hue_jitter=13.0, cell_mean=1.0):
    return dict(name=name, lane=lane, palette=palette, deck=deck, seed=seed,
                stack=stack, desc=desc, mix=mix, edge=edge, dither=dither,
                r_spread=r_spread, gamma=gamma, hue_jitter=hue_jitter,
                cell_mean=cell_mean)


_ROWS = [
    # ══════════════════════ 🕹 ARCADE (15) ═════════════════════════════════
    R("Phosphor Green", "arcade", "crt_green", "neon", 1101,
      [("scanline", 1.0, dict(lines=200, triad=3.0)), ("cells", 0.4, dict(cells=176))],
      "P1 phosphor at 15 kHz, with the persistence that smears a moving sprite.", cell_mean=0.25),
    R("Amber Terminal", "arcade", "crt_amber", "neon", 1102,
      [("scanline", 1.0, dict(lines=168, triad=1.0, roll=0.4)), ("microtext", 0.5, dict(rows=120))],
      "The other monochrome tube — 80 columns of amber, easier on a night shift.", cell_mean=0.25),
    R("Sprite Sheet", "arcade", "sprite8", "plastic", 1103,
      [("pixels", 1.0, dict(cell=6, levels=10, sprite=0.30)),
       ("sparks", 0.9, dict(n=4200, life=8)), ("scanline", 0.5, dict(lines=150))],
      "Sixteen by sixteen, four colours, one of them transparent.", cell_mean=0.0),
    R("Dot Matrix", "arcade", "coinop", "plastic", 1104,
      [("pixels", 1.0, dict(cell=6, levels=6, dither=0.5)),
       ("scanline", 0.8, dict(lines=140))],
      "The grid you could see if you put your face close enough to the glass.", cell_mean=0.0),
    R("Cabinet Side Art", "arcade", "marquee", "gloss", 1105,
      [("splatter", 1.0, dict(blobs=520, rmax=18, drips=0.2, spatter=1.5)),
       ("bands", 0.9, dict(n=90, vortex=8)), ("cells", 0.6, dict(cells=154))],
      "Screen-printed vinyl on particle board, sun-faded on the side facing the door."),
    R("Marquee Bulb", "arcade", "marquee", "glass", 1106,
      [("discs", 1.0, dict(n=2400, radius=14.0, tilt=0.55)), ("sparks", 0.5, dict(n=2600, life=20))],
      "Chase bulbs behind a translucent panel, three of them always out."),
    R("Quarter Slot", "arcade", "quarterbin", "steel", 1107,
      [("knurl", 1.0, dict(pitch=18, angle=40)), ("craters", 0.55, dict(n=2800, rmax=5.0))],
      "Brushed steel around the coin door, worn bright where thumbs go."),
    R("Attract Mode", "arcade", "attractmode", "neon", 1108,
      [("scanline", 1.0, dict(lines=124)), ("glitch", 0.7, dict(slices=64, shift=36, tear=0.35))],
      "The demo loop nobody watches, running to an empty room at 2am.", cell_mean=0.0),
    R("Trackball Wear", "arcade", "quarterbin", "plastic", 1109,
      [("craters", 1.0, dict(n=3200, rmax=6.0, rim=0.7)), ("cells", 0.5, dict(cells=158))],
      "Phenolic ball polished by a million hands, with the hazing that comes with it."),
    R("Vector Glow", "arcade", "attractmode", "neon", 1110,
      [("filaments", 1.0, dict(n=760, length=64, wander=0.2)), ("sparks", 0.6, dict(n=2400, life=24))],
      "No pixels at all — the beam draws the line and the phosphor holds it."),
    R("Bezel Black", "arcade", "quarterbin", "rubber", 1111,
      [("percolate", 1.0, dict(cells=178, p=0.48)), ("scanline", 0.4, dict(lines=150, bloom=0))],
      "The textured plastic surround, matte so it never reflects the screen."),
    R("Insert Coin", "arcade", "coinop", "candy", 1112,
      [("microtext", 1.0, dict(rows=104, density=0.6)), ("scanline", 0.7, dict(lines=136))],
      "Two words, blinking, in the only typeface the hardware had.", cell_mean=0.25),
    R("High Score", "arcade", "crt_green", "glass", 1113,
      [("pixels", 1.0, dict(cell=7, levels=5)),
       ("scanline", 0.7, dict(lines=132))],
      "Three initials in a table that gets wiped every time the power blinks.", cell_mean=0.0),
    R("Joystick Ball", "arcade", "sprite8", "gloss", 1114,
      [("facets", 1.0, dict(stones=200, table=0.34)), ("craters", 0.5, dict(n=2200, rmax=5.5))],
      "A red ball-top, cracked at the shaft, replaced twice a year."),
    R("Screen Burn", "arcade", "crt_amber", "chalk", 1115,
      [("scanline", 1.0, dict(lines=160, bloom=0.3, jitter=0.2)), ("microtext", 0.6, dict(rows=100))],
      "The score panel etched permanently into the phosphor after ten thousand hours.", cell_mean=0.25),

    # ══════════════════════ 🌆 GRID (15) ═══════════════════════════════════
    R("Vector Horizon", "grid", "gridpurple", "neon", 1201,
      [("wireframe", 1.0, dict(rows=64, persp=1.5)), ("sparks", 0.7, dict(n=3000, life=26)),
       ("cells", 0.5, dict(cells=170))],
      "The grid running to a vanishing point, because in 1984 that WAS the future.", cell_mean=0.25),
    R("Sunset Bars", "grid", "gridsun", "gloss", 1202,
      [("bands", 1.0, dict(n=92, shear=0.9, vortex=4, turb=0.24)), ("holo", 0.5, dict(rings=300))],
      "A sun cut into horizontal slices, each one a different heat."),
    R("Chrome Type", "grid", "chrometype", "chrome", 1203,
      [("bands", 1.0, dict(n=104, shear=1.1, vortex=5, turb=0.2)), ("knurl", 0.5, dict(pitch=24))],
      "Extruded letters with a blue-to-magenta gradient down the face.", edge="chrome"),
    R("VHS Tracking", "grid", "vhs", "plastic", 1204,
      [("glitch", 1.0, dict(slices=120, shift=52, tear=0.42, block=0.28)),
       ("scanline", 0.9, dict(lines=196, bloom=0.4)), ("cells", 0.4, dict(cells=172))],
      "Third-generation tape, tracking off, the head switching visible at the bottom.", cell_mean=0.25),
    R("Laserdisc Rainbow", "grid", "laserdisc", "dichroic", 1205,
      [("holo", 1.0, dict(rings=360, orders=3)), ("cells", 0.45, dict(cells=170))],
      "A twelve-inch disc catching the ceiling light in every order at once."),
    R("Outrun Stripe", "grid", "outrun", "candy", 1206,
      [("bands", 1.0, dict(n=86, shear=1.3, vortex=7, turb=0.3)), ("sparks", 0.45, dict(n=2200, life=20))],
      "The side stripe on a car that only existed in an attract screen."),
    R("Miami Pastel", "grid", "miamivice", "satin", 1207,
      [("stars", 1.0, dict(cell=96, points=4, interlace=0.4)), ("cells", 0.5, dict(cells=162))],
      "Flamingo and teal on stucco, shot at magic hour with a filter on."),
    R("Neon Tube", "grid", "gridpurple", "carrier", 1208,
      [("filaments", 1.0, dict(n=620, length=76, wander=0.16)), ("holo", 0.5, dict(rings=280))],
      "Argon and mercury in bent glass, buzzing at the transformer."),
    R("Grid Floor", "grid", "gridsun", "plastic", 1209,
      [("moire", 1.0, dict(lpi=210, depth=0.5, angle=24)),
       ("polygons", 0.8, dict(cells=124, relief=0.5)),
       ("wireframe", 0.4, dict(rows=90, persp=1.1, horizon=0.24))],
      "The floor of every music video, receding forever under a fog machine.", cell_mean=0.3),
    R("Static Snow", "grid", "vhs", "chalk", 1210,
      [("glitch", 1.0, dict(slices=150, shift=64, tear=0.6, block=0.35)),
       ("sparks", 0.8, dict(n=4200, life=8)), ("cells", 0.5, dict(cells=180))],
      "Channel 3 with nothing on it, which is a real image of the early universe.", cell_mean=0.25),
    R("Digital Sunrise", "grid", "outrun", "spectral", 1211,
      [("holo", 1.0, dict(rings=320)), ("bands", 0.6, dict(n=80, vortex=6))],
      "A gradient with visible banding, because 8-bit colour could not do better."),
    R("Cassette Shell", "grid", "chrometype", "plastic", 1212,
      [("knurl", 1.0, dict(pitch=20, angle=0, relief=0.9)), ("craters", 0.5, dict(n=2600, rmax=4.5))],
      "Smoked polystyrene with the little window and the five screws."),
    R("Boombox Grille", "grid", "quarterbin", "steel", 1213,
      [("honeycomb", 1.0, dict(cells=150)), ("knurl", 0.5, dict(pitch=26, angle=45))],
      "Perforated steel over a ten-inch woofer, dented on one corner."),
    R("Synth Key", "grid", "chrometype", "plastic", 1214,
      [("bands", 1.0, dict(n=112, shear=0.6, vortex=2, turb=0.16)), ("cells", 0.5, dict(cells=166))],
      "Ivory-look ABS gone slightly yellow, with the wear stripe at the front edge."),
    R("Laser Grid", "grid", "laserdisc", "neon", 1215,
      [("filaments", 1.0, dict(n=880, length=84, wander=0.08, width=2.2)),
       ("wireframe", 0.6, dict(rows=48, persp=1.2, horizon=0.5, width=1.2)),
       ("sparks", 0.6, dict(n=2800, life=22))],
      "Beams through haze, arranged so they cross exactly where the camera is.", cell_mean=0.25),

    # ══════════════════════ 📐 MEMPHIS (15) ════════════════════════════════
    R("Milano Squiggle", "memphis", "memphis", "plastic", 1301,
      [("squiggle", 1.0, dict(n=460, length=110, confetti=0.6)),
       ("cells", 0.9, dict(cells=150)), ("craters", 0.5, dict(n=2800, rmax=6.0))],
      "Sottsass drew the squiggle and the whole decade copied it onto everything."),
    R("Bacterio Print", "memphis", "bacterio", "plastic", 1302,
      [("squiggle", 1.0, dict(n=760, length=52, amp=10, confetti=0.35, width=2.2)),
       ("percolate", 0.9, dict(cells=168)), ("cells", 0.5, dict(cells=158))],
      "The black-on-white scribble laminate, named after what it looks like."),
    R("Jazz Cup", "memphis", "jazzcup", "chalk", 1303,
      [("squiggle", 1.0, dict(n=380, length=96, confetti=0.75, width=4.0)),
       ("cells", 0.9, dict(cells=146)), ("craters", 0.5, dict(n=3000, rmax=5.5))],
      "Teal and purple on a paper cup, the most-printed pattern of the decade."),
    R("Terrazzo Chip", "memphis", "terrazzo80", "plastic", 1304,
      [("craters", 1.0, dict(n=4200, rmax=8.0, rim=0.85)), ("cells", 0.55, dict(cells=140))],
      "Marble chips in white cement, ground flat and polished — the lobby floor."),
    R("Pastel Mint", "memphis", "pastel_mint", "satin", 1305,
      [("stars", 1.0, dict(cell=88, points=8, interlace=0.5)), ("cells", 0.45, dict(cells=170))],
      "Mint on a bathroom tile, with a black grout line that was a design decision."),
    R("Peach Fuzz", "memphis", "pastel_peach", "suede", 1306,
      [("percolate", 1.0, dict(cells=180, p=0.5)), ("filaments", 0.55, dict(n=2400, length=12))],
      "Peach flocking on a padded headboard, in a bedroom nobody would design now."),
    R("Confetti Laminate", "memphis", "memphis", "plastic", 1307,
      [("squiggle", 1.0, dict(n=180, length=50, confetti=1.0, width=2.0)), ("cells", 0.4, dict(cells=168))],
      "Scattered rectangles at random angles, fused under melamine."),
    R("Grid Tile", "memphis", "jazzcup", "gloss", 1308,
      [("polygons", 1.0, dict(cells=112, relief=0.45)), ("moire", 0.45, dict(lpi=160, depth=0.35))],
      "Small square tiles in three colours laid to no pattern at all, on purpose."),
    R("Zigzag Runner", "memphis", "squiggle80", "eggshell", 1309,
      [("sett", 1.0, dict(pitch=42, stripes=(0.30, 0.10, 0.08, 0.24, 0.10, 0.12), twill=4))],
      "A flatweave rug in colours that fight, which was the point."),
    R("Neon Wire Chair", "memphis", "squiggle80", "steel", 1310,
      [("filaments", 1.0, dict(n=900, length=54, wander=0.24)), ("knurl", 0.5, dict(pitch=24))],
      "Powder-coated rod bent into a chair that was better to look at than sit in."),
    R("Speckle Wall", "memphis", "terrazzo80", "chalk", 1311,
      [("sparks", 1.0, dict(n=4200, life=10, spread=1.4)), ("percolate", 0.5, dict(cells=172))],
      "Flecked wallpaper, the kind that hid a bad plaster job in a rented flat."),
    R("Glass Block", "memphis", "pastel_mint", "glass", 1312,
      [("polygons", 1.0, dict(cells=76, relief=0.7)), ("craters", 0.5, dict(n=2400, rmax=6.0))],
      "Fluted glass brick in a partition wall, in every dentist's office made after 1985."),
    R("Lacquer Cabinet", "memphis", "bacterio", "lacquer", 1313,
      [("bands", 1.0, dict(n=98, shear=0.7, vortex=3, turb=0.2)), ("cells", 0.5, dict(cells=164))],
      "High-gloss black lacquer with one primary-colour drawer, on castors."),
    R("Sponge Paint", "memphis", "pastel_peach", "chalk", 1314,
      [("percolate", 1.0, dict(cells=142, p=0.44)), ("craters", 0.6, dict(n=3000, rmax=7.0))],
      "Rag-rolled over base coat, in a technique every magazine ran for six years."),
    R("Anodised Trim", "memphis", "memphis", "spectral", 1315,
      [("bands", 1.0, dict(n=106, shear=1.0, vortex=6)), ("knurl", 0.5, dict(pitch=22))],
      "Coloured aluminium extrusion, on the edge of every surface in the room."),

    # ══════════════════════ 🎸 RADICAL (15) ════════════════════════════════
    R("Splatter Tee", "radical", "splattertee", "chalk", 1401,
      [("splatter", 1.0, dict(blobs=620, rmax=22, drips=0.5, spatter=1.3)),
       ("cells", 0.9, dict(cells=152)), ("percolate", 0.5, dict(cells=170))],
      "Thrown from a brush across a white shirt, then worn until it fell apart."),
    R("Hair Metal", "radical", "hairmetal", "glitter", 1402,
      [("filaments", 1.0, dict(n=2800, length=40, wander=0.7)), ("sparks", 0.6, dict(n=3000, life=20))],
      "Backcombed, sprayed, and lit from behind by the entire lighting rig."),
    R("Neon Spandex", "radical", "spandex", "gloss", 1403,
      [("braid", 1.0, dict(layers=126, shear=1.6)), ("holo", 0.5, dict(rings=310))],
      "Lycra in a colour that does not occur in nature, stretched over a leg warmer."),
    R("Skate Deck", "radical", "skatedeck", "suede", 1404,
      [("craters", 1.0, dict(n=3600, rmax=6.0, rim=0.6)), ("bands", 0.5, dict(n=88, vortex=7))],
      "Grip tape over seven-ply maple, with the graphic already worn off the tail."),
    R("Tiger Stripe", "radical", "tigerstripe80", "lacquer", 1405,
      [("bands", 1.0, dict(n=74, shear=2.6, vortex=20, turb=0.55)), ("filaments", 0.5, dict(n=1400, length=30))],
      "Airbrushed stripes on a guitar body, tapering exactly like the animal's do."),
    R("Aerobics Gym", "radical", "neon_gym", "plastic", 1406,
      [("sett", 1.0, dict(pitch=40, stripes=(0.28, 0.14, 0.08, 0.26, 0.10, 0.14))),
       ("cells", 0.4, dict(cells=172))],
      "A headband, a striped leotard and a floor made of the same three colours."),
    R("Airbrush Portrait", "radical", "airbrush80", "lacquer", 1407,
      [("curl", 1.0, dict(scale=42, steps=20)), ("holo", 0.5, dict(rings=290))],
      "Soft edges, hard highlights, and a lens flare added by hand with a stencil."),
    R("Rad Splatter Deck", "radical", "splattertee", "gloss", 1408,
      [("splatter", 1.0, dict(blobs=560, rmax=18, drips=0.35, spatter=1.6)),
       ("cells", 0.9, dict(cells=156)), ("craters", 0.6, dict(n=2800, rmax=5.0))],
      "The same splatter under clear on a board, which is how it survived."),
    R("Zebra Wrap", "radical", "hairmetal", "suede", 1409,
      [("bands", 1.0, dict(n=68, shear=3.0, vortex=24, turb=0.6)), ("cells", 0.45, dict(cells=164))],
      "Black on white in stripes that never repeat, on a jacket with shoulder pads."),
    R("Neon Grip", "radical", "neon_gym", "rubber", 1410,
      [("knurl", 1.0, dict(pitch=15, angle=45, relief=1.3)), ("percolate", 0.5, dict(cells=176))],
      "Moulded rubber in fluorescent green, on a BMX bar that glowed under UV."),
    R("Slap Bracelet", "radical", "spandex", "dichroic", 1411,
      [("holo", 1.0, dict(rings=340, orders=3)), ("scales", 0.5, dict(cell=22))],
      "Spring steel in a fabric sleeve, banned by every school by 1991."),
    R("Puffy Paint", "radical", "airbrush80", "plastic", 1412,
      [("filaments", 1.0, dict(n=2400, length=30, wander=0.55, width=2.4)),
       ("cells", 0.85, dict(cells=158)), ("craters", 0.55, dict(n=3000, rmax=5.0))],
      "Squeezed from a bottle onto a sweatshirt and left to dome as it dried."),
    R("Trapper Sticker", "radical", "splattertee", "gloss", 1413,
      [("stars", 1.0, dict(cell=84, points=5, interlace=0.6)), ("sparks", 0.5, dict(n=2600, life=18))],
      "Scratch-and-sniff, googly-eye and puffy, layered until the folder would not shut."),
    R("Hypercolour", "radical", "pastel_peach", "pearl", 1414,
      [("percolate", 1.0, dict(cells=150, p=0.46)), ("holo", 0.55, dict(rings=300))],
      "Thermochromic dye that changed where you touched it and died in the first wash."),
    R("Big Hair Chrome", "radical", "hairmetal", "carrier", 1415,
      [("filaments", 1.0, dict(n=2200, length=52, wander=0.6)), ("holo", 0.5, dict(rings=330))],
      "The album cover: chrome type, lightning, and hair with its own key light."),
]


def _fid(name):
    return ID_PREFIX + name.lower().replace(" ", "_").replace("-", "_").replace("'", "")


BAD_AND_RAD = {_fid(r["name"]): r for r in _ROWS}


def title(fid):
    return "%s: %s" % (BAD_AND_RAD[fid]["lane"].title(), BAD_AND_RAD[fid]["name"])


import sys as _sys                                            # noqa: E402
EB.make(_sys.modules[__name__], BAD_AND_RAD, _STRUCTS, P)
