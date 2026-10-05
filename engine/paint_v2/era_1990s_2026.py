# -*- coding: utf-8 -*-
"""💿 ALL THAT — the 1990s. A new shelf, 60 finishes.

Owner: *"I do NOT have a category for this yet but let's also do 1990s and come
up with a cute name for it that is Totally 90s. 60 finishes here too."*

The name is the Nickelodeon sketch show, which is about as 1990s as a phrase can
be and still be two ordinary words. It sits with SOCK HOP (1950s), GROOVY VIBES
(1960s), 🪩 FAR OUT (1970s) and ⚡ BAD & RAD (1980s).

FOUR ROOMS, fifteen each:

  💾 CD-ROM     the beige box, the screensaver, the holographic disc, Y2K chrome
  🛹 EXTREME    snowboard, skate, neon windbreaker, mountain-dew everything
  🎤 FRESH      velour, gold rope, airbrush, Cross Colours, bucket hat
  🎸 FLANNEL    Seattle — thrift, moss, rain, distressed, Doc Martens

MATERIALS. The 1990s pull hardest on the decks the 1980s did not: `suede` and
`velvet` for flannel and velour, `chalk` for thrift and concrete, `dichroic` and
`spectral` for the holographic disc and the frosted translucent plastic that
ended the decade. The Fractured rail appears four times in sixty, all in CD-ROM
where a surface is genuinely diffracting.
"""
from __future__ import annotations

from engine.paint_v2 import era_base_2026 as EB
from engine.paint_v2 import era_kit_2026 as K

ID_PREFIX = "at_"
GROUP = "💿 ALL THAT"
LANES = {"cdrom": "💾 CD-ROM", "extreme": "🛹 EXTREME", "fresh": "🎤 FRESH",
         "flannel": "🎸 FLANNEL"}

_STRUCTS = {
    "holo":      lambda sh, sd, k: (K.holo(sh, sd, **k), None),
    "glitch":    lambda sh, sd, k: (K.glitch(sh, sd, **k), None),
    "pixels":    lambda sh, sd, k: (K.pixels(sh, sd, **k), None),
    "scanline":  lambda sh, sd, k: (K.scanline(sh, sd, **k), None),
    "squiggle":  lambda sh, sd, k: (K.squiggle(sh, sd, **k), None),
    "splatter":  lambda sh, sd, k: (K.splatter(sh, sd, **k), None),
    "shag":      lambda sh, sd, k: (K.shag(sh, sd, **k), None),
    "scales":    lambda sh, sd, k: (K.scales(sh, sd, **k), None),
    "topo":      lambda sh, sd, k: (K.topo(sh, sd, **k), None),
    "sett":      lambda sh, sd, k: (K.sett(sh, sd, **k), None),
    "stars":     lambda sh, sd, k: (K.stars(sh, sd, **k), None),
    "ikat":      lambda sh, sd, k: (K.ikat(sh, sd, **k), None),
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
    "eden":      lambda sh, sd, k: (K.eden(sh, sd, **k), None),
    "discs":     lambda sh, sd, k: (K.discs(sh, sd, **k), None),
    "tooled":    lambda sh, sd, k: (K.tooled(sh, sd, **k), None),
    "guilloche": lambda sh, sd, k: (K.guilloche(sh, sd, **k), None),
}

P = {
    # CD-ROM
    "cdrainbow":  ((0.06, 0.07, 0.10), (0.18, 0.44, 0.52), (0.72, 0.30, 0.66), (0.96, 0.94, 0.84)),
    "beigebox":   ((0.24, 0.22, 0.18), (0.56, 0.52, 0.44), (0.80, 0.76, 0.66), (0.95, 0.93, 0.86)),
    "win95":      ((0.06, 0.10, 0.16), (0.14, 0.30, 0.52), (0.62, 0.66, 0.70), (0.96, 0.96, 0.94)),
    "screensaver":((0.03, 0.03, 0.07), (0.10, 0.36, 0.44), (0.60, 0.18, 0.62), (0.94, 0.90, 0.40)),
    "y2kchrome":  ((0.08, 0.09, 0.12), (0.34, 0.38, 0.46), (0.70, 0.76, 0.84), (0.98, 1.00, 1.00)),
    "dialup":     ((0.05, 0.06, 0.05), (0.16, 0.30, 0.20), (0.44, 0.62, 0.40), (0.84, 0.94, 0.72)),
    "frostplastic":((0.20, 0.24, 0.26), (0.48, 0.60, 0.64), (0.74, 0.86, 0.90), (0.96, 1.00, 1.00)),
    # EXTREME
    "snowboard":  ((0.05, 0.07, 0.14), (0.14, 0.30, 0.62), (0.86, 0.34, 0.16), (0.98, 0.92, 0.36)),
    "windbreaker":((0.06, 0.06, 0.10), (0.86, 0.22, 0.30), (0.16, 0.56, 0.72), (0.98, 0.94, 0.36)),
    "dewgreen":   ((0.05, 0.10, 0.04), (0.16, 0.44, 0.10), (0.56, 0.86, 0.16), (0.94, 1.00, 0.58)),
    "skatepark":  ((0.16, 0.16, 0.17), (0.40, 0.40, 0.41), (0.64, 0.64, 0.64), (0.88, 0.88, 0.88)),
    "bigdog":     ((0.10, 0.06, 0.05), (0.36, 0.18, 0.10), (0.72, 0.42, 0.16), (0.96, 0.80, 0.40)),
    "surfwax":    ((0.08, 0.14, 0.16), (0.20, 0.46, 0.52), (0.52, 0.78, 0.80), (0.92, 0.99, 0.98)),
    "bmxdirt":    ((0.12, 0.09, 0.05), (0.34, 0.26, 0.14), (0.58, 0.46, 0.26), (0.84, 0.74, 0.50)),
    # FRESH
    "velour":     ((0.10, 0.04, 0.10), (0.34, 0.10, 0.32), (0.64, 0.28, 0.58), (0.92, 0.68, 0.86)),
    "goldrope":   ((0.14, 0.10, 0.02), (0.46, 0.33, 0.05), (0.78, 0.60, 0.14), (0.99, 0.90, 0.48)),
    "crosscolour":((0.08, 0.08, 0.05), (0.72, 0.16, 0.14), (0.16, 0.52, 0.26), (0.98, 0.88, 0.20)),
    "airbrush90": ((0.06, 0.05, 0.12), (0.34, 0.10, 0.48), (0.82, 0.28, 0.56), (1.00, 0.84, 0.90)),
    "buckethat":  ((0.12, 0.13, 0.10), (0.32, 0.36, 0.26), (0.56, 0.60, 0.46), (0.84, 0.88, 0.72)),
    "kicks":      ((0.10, 0.10, 0.11), (0.30, 0.30, 0.32), (0.72, 0.20, 0.22), (0.97, 0.96, 0.94)),
    "boombox90":  ((0.07, 0.07, 0.08), (0.24, 0.24, 0.26), (0.52, 0.52, 0.54), (0.86, 0.86, 0.88)),
    # FLANNEL
    "flannel_red":((0.10, 0.04, 0.04), (0.36, 0.10, 0.10), (0.16, 0.16, 0.20), (0.86, 0.72, 0.64)),
    "flannel_grn":((0.06, 0.09, 0.06), (0.18, 0.30, 0.18), (0.12, 0.14, 0.16), (0.78, 0.82, 0.72)),
    "thrift":     ((0.14, 0.12, 0.10), (0.38, 0.34, 0.28), (0.62, 0.58, 0.50), (0.86, 0.84, 0.76)),
    "seattlerain":((0.10, 0.12, 0.13), (0.26, 0.32, 0.34), (0.48, 0.56, 0.58), (0.78, 0.86, 0.88)),
    "moss90":     ((0.05, 0.09, 0.05), (0.16, 0.28, 0.14), (0.34, 0.50, 0.28), (0.66, 0.80, 0.52)),
    "docmarten":  ((0.06, 0.04, 0.03), (0.20, 0.12, 0.08), (0.42, 0.26, 0.16), (0.70, 0.52, 0.34)),
    "grungeblue": ((0.07, 0.09, 0.14), (0.20, 0.26, 0.40), (0.40, 0.48, 0.64), (0.72, 0.80, 0.90)),
}


def R(name, lane, palette, deck, seed, stack, desc, mix="sum", edge=None,
      dither=0.15, r_spread=26.0, gamma=1.0, hue_jitter=13.0, cell_mean=1.0):
    return dict(name=name, lane=lane, palette=palette, deck=deck, seed=seed,
                stack=stack, desc=desc, mix=mix, edge=edge, dither=dither,
                r_spread=r_spread, gamma=gamma, hue_jitter=hue_jitter,
                cell_mean=cell_mean)


_ROWS = [
    # ══════════════════════ 💾 CD-ROM (15) ═════════════════════════════════
    R("Disc Rainbow", "cdrom", "cdrainbow", "dichroic", 2101,
      [("holo", 1.0, dict(rings=380, orders=3)), ("guilloche", 0.5, dict(period=70, ring=9, teeth=(3, 5)))],
      "Data pits under lacquer, diffracting the room back at you in order.", edge="chrome"),
    R("Beige Box", "cdrom", "beigebox", "plastic", 2102,
      [("knurl", 1.0, dict(pitch=17, angle=0, relief=0.8)), ("craters", 0.5, dict(n=3000, rmax=5.0))],
      "Textured ABS that went yellow within four years of leaving the factory."),
    R("Windows Teal", "cdrom", "win95", "gloss", 2103,
      [("polygons", 1.0, dict(cells=104, relief=0.4)), ("microtext", 0.5, dict(rows=130))],
      "The desktop everyone had, in the teal nobody chose."),
    R("Pipes Screensaver", "cdrom", "screensaver", "neon", 2104,
      [("filaments", 1.0, dict(n=1500, length=52, wander=0.22, width=3.0)),
       ("sparks", 0.9, dict(n=3400, life=22)), ("cells", 0.6, dict(cells=160))],
      "Chrome pipes assembling themselves forever because nobody hit a key."),
    R("Y2K Chrome", "cdrom", "y2kchrome", "chrome", 2105,
      [("bands", 1.0, dict(n=100, shear=1.0, vortex=5, turb=0.2)), ("facets", 0.5, dict(stones=190))],
      "Bubble chrome type, on everything printed between 1998 and 2001.", edge="mercury"),
    R("Dial-Up Green", "cdrom", "dialup", "neon", 2106,
      [("scanline", 1.0, dict(lines=176, triad=1.0)), ("microtext", 0.55, dict(rows=140))],
      "A terminal at 14.4k, with the handshake you could hum from memory."),
    R("Frosted Shell", "cdrom", "frostplastic", "glass", 2107,
      [("percolate", 1.0, dict(cells=180, p=0.5)), ("craters", 0.5, dict(n=2800, rmax=5.5))],
      "Translucent blueberry polycarbonate — you could see the machine's own guts."),
    R("Corrupt JPEG", "cdrom", "screensaver", "plastic", 2108,
      [("pixels", 1.0, dict(cell=5, levels=10)), ("sparks", 0.9, dict(n=4600, life=7)),
       ("glitch", 0.7, dict(slices=150, shift=58, tear=0.5, block=0.34))],
      "A download that failed at 74%, saved anyway, opened for years afterwards.", cell_mean=0.0),
    R("Floppy Black", "cdrom", "boombox90", "rubber", 2109,
      [("knurl", 1.0, dict(pitch=19, angle=90, relief=0.9)), ("percolate", 0.5, dict(cells=174))],
      "3.5-inch, high density, with a shutter that never quite closed straight."),
    R("Holo Sticker", "cdrom", "cdrainbow", "spectral", 2110,
      [("holo", 1.0, dict(rings=300, orders=2)), ("scales", 0.5, dict(cell=20))],
      "The authenticity hologram, which everyone peeled off and stuck somewhere else."),
    R("CRT Blue Screen", "cdrom", "win95", "neon", 2111,
      [("scanline", 1.0, dict(lines=190, triad=2.6)), ("microtext", 0.6, dict(rows=110, density=0.5))],
      "White on blue, hex addresses, and the certainty you had lost the work."),
    R("Mouse Ball Grime", "cdrom", "beigebox", "chalk", 2112,
      [("craters", 1.0, dict(n=3400, rmax=6.0)), ("percolate", 0.5, dict(cells=168))],
      "The rollers, and what you scraped off them with a fingernail once a month."),
    R("Zip Disk", "cdrom", "boombox90", "plastic", 2113,
      [("bands", 1.0, dict(n=96, shear=0.8, vortex=3, turb=0.18)), ("cells", 0.5, dict(cells=160))],
      "100 megabytes, and the click of death that took it all with it."),
    R("Iridescent CD-R", "cdrom", "cdrainbow", "carrier", 2114,
      [("holo", 1.0, dict(rings=420, orders=3)), ("cells", 0.4, dict(cells=176))],
      "The green-gold underside of a blank, burned at 2x with the drive door taped shut."),
    R("Cyber Café", "cdrom", "frostplastic", "steel", 2115,
      [("honeycomb", 1.0, dict(cells=156)), ("knurl", 0.5, dict(pitch=24, angle=30))],
      "Perforated steel desks, blue LEDs, and an hourly rate."),

    # ══════════════════════ 🛹 EXTREME (15) ════════════════════════════════
    R("Snowboard Graphic", "extreme", "snowboard", "gloss", 2201,
      [("splatter", 1.0, dict(blobs=560, rmax=18, drips=0.3, spatter=1.5)),
       ("bands", 0.9, dict(n=86, vortex=9)), ("cells", 0.6, dict(cells=156))],
      "Sublimated topsheet, scratched to the core by the second season."),
    R("Windbreaker Block", "extreme", "windbreaker", "plastic", 2202,
      [("polygons", 1.0, dict(cells=92, relief=0.5)), ("braid", 0.5, dict(layers=108, shear=1.4))],
      "Colour-blocked nylon that rustled loudly enough to annoy a whole classroom."),
    R("Dew Green", "extreme", "dewgreen", "neon", 2203,
      [("percolate", 1.0, dict(cells=166, p=0.46)), ("sparks", 0.5, dict(n=2800, life=20))],
      "A colour engineered in a lab to be visible from the other end of an aisle."),
    R("Skatepark Concrete", "extreme", "skatepark", "chalk", 2204,
      [("craters", 1.0, dict(n=3600, rmax=7.0)), ("percolate", 0.5, dict(cells=158))],
      "Poured bowl, waxed coping, and the grey that photographs badly on purpose."),
    R("Grip Tape", "extreme", "skatepark", "rubber", 2205,
      [("sparks", 1.0, dict(n=5200, life=8, spread=1.6)), ("percolate", 0.5, dict(cells=180))],
      "Silicon carbide on adhesive, sharp enough to take skin off."),
    R("Big Dog Print", "extreme", "bigdog", "suede", 2206,
      [("scales", 1.0, dict(cell=28, keel=0.5)), ("cells", 0.5, dict(cells=158))],
      "An oversized tee with a cartoon dog, worn to a waterpark in 1996."),
    R("Surf Wax", "extreme", "surfwax", "chalk", 2207,
      [("craters", 1.0, dict(n=4200, rmax=5.0, rim=0.6)), ("dunes", 0.45, dict(n=44))],
      "Combed into a deck, gone chalky and grey, smelling of coconut regardless."),
    R("BMX Dirt", "extreme", "bmxdirt", "chalk", 2208,
      [("dunes", 1.0, dict(n=48)), ("craters", 0.6, dict(n=3200, rmax=6.0))],
      "A backyard jump packed hard, with a lip built out of whatever was around."),
    R("Anodised Peg", "extreme", "dewgreen", "spectral", 2209,
      [("knurl", 1.0, dict(pitch=16, angle=90, relief=1.2)), ("bands", 0.5, dict(n=104, vortex=4))],
      "Purple ano on a chromoly peg, scraped back to silver on the grind side."),
    R("Neon Wetsuit", "extreme", "surfwax", "rubber", 2210,
      [("percolate", 1.0, dict(cells=172, p=0.5)), ("braid", 0.55, dict(layers=112, shear=1.2))],
      "Neoprene with fluoro panels, because the eighties had not fully let go."),
    R("Half Pipe Ply", "extreme", "bmxdirt", "suede", 2211,
      [("bands", 1.0, dict(n=98, shear=1.4, vortex=7, turb=0.32)), ("craters", 0.5, dict(n=2400, rmax=5.0))],
      "Two layers of masonite over ply, with a seam you learned to jump."),
    R("Roller Blade", "extreme", "windbreaker", "plastic", 2212,
      [("scales", 1.0, dict(cell=24, keel=0.65)), ("knurl", 0.45, dict(pitch=22))],
      "Vented plastic shell in three colours nobody would choose twice."),
    R("Mountain Topo", "extreme", "snowboard", "eggshell", 2213,
      [("topo", 1.0, dict(lines=240, index=5)),
       ("filaments", 1.0, dict(n=2800, length=12, wander=0.8)),
       ("cells", 0.7, dict(cells=150))],
      "A trail map folded into a pocket until the creases went through the paper."),
    R("Chain Link", "extreme", "skatepark", "steel", 2214,
      [("knurl", 1.0, dict(pitch=13, angle=45, relief=1.5)),
       ("filaments", 0.7, dict(n=2200, length=16)), ("cells", 0.5, dict(cells=164))],
      "Galvanised fence around the lot, with the corner everybody bent up."),
    R("Bungee Cord", "extreme", "dewgreen", "plastic", 2215,
      [("braid", 1.0, dict(layers=132, shear=2.2)), ("filaments", 0.5, dict(n=2000, length=18))],
      "Woven sheath over rubber core, in colours matched to nothing at all."),

    # ══════════════════════ 🎤 FRESH (15) ══════════════════════════════════
    R("Velour Tracksuit", "fresh", "velour", "velvet", 2301,
      [("shag", 1.0, dict(strands=5200, length=30, splay=0.6)), ("braid", 0.45, dict(layers=104, shear=1.2))],
      "Two pieces, matching, in a purple that reads as a texture more than a colour."),
    R("Gold Rope", "fresh", "goldrope", "gold", 2302,
      [("braid", 1.0, dict(layers=76, shear=3.0)), ("sparks", 0.55, dict(n=2600, life=18))],
      "Herringbone links, worn outside the shirt, weighed by hand at the counter."),
    R("Cross Colour Block", "fresh", "crosscolour", "plastic", 2303,
      [("polygons", 1.0, dict(cells=84, relief=0.55)), ("braid", 0.5, dict(layers=98, shear=1.6))],
      "Primary blocks on baggy denim, cut for a fit that took twenty years to return."),
    R("Airbrush Tee", "fresh", "airbrush90", "gloss", 2304,
      [("curl", 1.0, dict(scale=40, steps=20)), ("splatter", 0.5, dict(blobs=320, rmax=18))],
      "Boardwalk airbrush, name in bubble letters, drying while you waited."),
    R("Bucket Hat", "fresh", "buckethat", "suede", 2305,
      [("braid", 1.0, dict(layers=118, shear=1.8)), ("filaments", 0.5, dict(n=2200, length=13))],
      "Reversible cotton twill with a stitched brim that held its shape badly."),
    R("Fresh Kicks", "fresh", "kicks", "gloss", 2306,
      [("scales", 1.0, dict(cell=26, keel=0.6)), ("craters", 0.5, dict(n=2600, rmax=5.0))],
      "Patent toe, mesh panel, and a midsole kept white with a toothbrush."),
    R("Boombox Chrome", "fresh", "boombox90", "steel", 2307,
      [("honeycomb", 1.0, dict(cells=148)), ("knurl", 0.5, dict(pitch=22, angle=45))],
      "Twin decks, a graphic equaliser, and D cells by the dozen."),
    R("Velour Rose", "fresh", "velour", "velvet", 2308,
      [("shag", 1.0, dict(strands=4800, length=24, splay=0.5)), ("wrinkle", 0.5, dict(k=1.0, steps=14))],
      "Crushed nap that shows every fingerprint and every direction you brushed it."),
    R("Nameplate Gold", "fresh", "goldrope", "lacquer", 2309,
      [("tooled", 1.0, dict(cell=42, petals=5, stamp=0.5)), ("sparks", 0.5, dict(n=2400, life=20))],
      "Cut from sheet in a mall kiosk while you picked the font."),
    R("Denim Baggy", "fresh", "crosscolour", "suede", 2310,
      [("braid", 1.0, dict(layers=124, shear=2.0)), ("filaments", 0.6, dict(n=2400, length=12, wander=0.7))],
      "Twenty-two inch leg, stonewashed, stacked over the shoe."),
    R("Graffiti Fill", "fresh", "airbrush90", "gloss", 2311,
      [("splatter", 1.0, dict(blobs=640, rmax=17, drips=0.55, spatter=1.6)),
       ("bands", 0.9, dict(n=82, vortex=10)), ("cells", 0.6, dict(cells=158))],
      "Two-tone fill with a hard outline, done fast on a rolling shutter."),
    R("Kangol Felt", "fresh", "buckethat", "velvet", 2312,
      [("shag", 1.0, dict(strands=4400, length=18, splay=0.4)), ("cells", 0.4, dict(cells=172))],
      "Angora felt with a nap you could write on with a finger."),
    R("Grill Chrome", "fresh", "y2kchrome", "chrome", 2313,
      [("facets", 1.0, dict(stones=220, table=0.3)), ("knurl", 0.45, dict(pitch=20))],
      "Polished, removable, and photographed more than it was worn.", edge="chrome"),
    R("Vinyl Crate", "fresh", "boombox90", "chalk", 2314,
      [("guilloche", 1.0, dict(period=54, ring=7, teeth=(3, 5))), ("cells", 0.45, dict(cells=170))],
      "Twelve-inch sleeves gone soft at the corners from being flipped through."),
    R("Starter Jacket", "fresh", "kicks", "plastic", 2315,
      [("braid", 1.0, dict(layers=116, shear=1.4)), ("polygons", 0.5, dict(cells=96, relief=0.45))],
      "Satin shell with a team logo, and a lining that made you sweat instantly."),

    # ══════════════════════ 🎸 FLANNEL (15) ════════════════════════════════
    R("Flannel Red", "flannel", "flannel_red", "suede", 2401,
      [("sett", 1.0, dict(pitch=46, stripes=(0.32, 0.10, 0.06, 0.22, 0.08, 0.12)))],
      "Buffalo check, brushed cotton, tied round the waist more than worn."),
    R("Flannel Forest", "flannel", "flannel_grn", "suede", 2402,
      [("sett", 1.0, dict(pitch=38, stripes=(0.28, 0.12, 0.08, 0.26, 0.10, 0.16), twill=5))],
      "Green over black in a windowpane that goes soft after ten washes."),
    R("Thrift Cardigan", "flannel", "thrift", "velvet", 2403,
      [("shag", 1.0, dict(strands=4600, length=28, splay=0.8)), ("braid", 0.5, dict(layers=88, shear=1.6))],
      "Somebody's grandfather's, three sizes too big, with one button gone."),
    R("Seattle Rain", "flannel", "seattlerain", "wet", 2404,
      [("craters", 1.0, dict(n=3800, rmax=6.5, rim=0.75)), ("curl", 0.5, dict(scale=54, steps=16))],
      "Not a downpour — the constant fine one that soaks you over an hour."),
    R("Moss Sidewalk", "flannel", "moss90", "chalk", 2405,
      [("dendrite", 1.0, dict(seeds=1100)), ("percolate", 0.55, dict(cells=170))],
      "The green that grows in the cracks where the sun never reaches."),
    R("Doc Marten", "flannel", "docmarten", "gloss", 2406,
      [("percolate", 1.0, dict(cells=140, p=0.44)), ("wrinkle", 0.55, dict(k=1.1, steps=15))],
      "Eight-hole, cherry red, creased across the vamp exactly where the foot bends."),
    R("Distressed Denim", "flannel", "grungeblue", "chalk", 2407,
      [("braid", 1.0, dict(layers=128, shear=2.2)), ("spall", 0.55, dict(cells=112, lift=0.6))],
      "Worn through at the knee honestly, over about four years."),
    R("Band Tee Crack", "flannel", "thrift", "chalk", 2408,
      [("crack", 1.0, dict(cells=134, width=2.0, gen=1)), ("percolate", 0.5, dict(cells=176))],
      "Plastisol print cracked into a map by a hundred trips through a dryer."),
    R("Corduroy Olive", "flannel", "moss90", "suede", 2409,
      [("braid", 1.0, dict(layers=84, shear=0.8)), ("dunes", 0.5, dict(n=40))],
      "Narrow wale, olive, from a shop that also sold camping stoves."),
    R("Overcast Grey", "flannel", "seattlerain", "chalk", 2410,
      [("percolate", 1.0, dict(cells=184, p=0.52)), ("curl", 0.5, dict(scale=62, steps=14))],
      "Nine months of the same sky, which is a colour and also a mood."),
    R("Basement Amp", "flannel", "docmarten", "rubber", 2411,
      [("knurl", 1.0, dict(pitch=18, angle=45, relief=1.1)), ("percolate", 0.5, dict(cells=178))],
      "Tolex over ply, cigarette-burned on the top, with one corner stove in."),
    R("Combat Boot Steel", "flannel", "thrift", "steel", 2412,
      [("spall", 1.0, dict(cells=118, lift=0.65)), ("craters", 0.5, dict(n=2600, rmax=5.5))],
      "A steel toe showing through the leather, which counted as a look."),
    R("Sharpie Ink", "flannel", "grungeblue", "gloss", 2413,
      [("filaments", 1.0, dict(n=4200, length=22, wander=0.6, width=2.2)),
       ("cells", 0.9, dict(cells=150)), ("sparks", 0.6, dict(n=3200, life=9))],
      "Lyrics on a forearm and a rucksack, bleeding slightly into the weave."),
    R("Cassette Tape", "flannel", "docmarten", "plastic", 2414,
      [("bands", 1.0, dict(n=118, shear=0.5, vortex=2, turb=0.14)), ("cells", 0.45, dict(cells=166))],
      "A mixtape with the track list in three different pens."),
    R("Chipped Nail", "flannel", "flannel_red", "lacquer", 2415,
      [("spall", 1.0, dict(cells=126, lift=0.55)), ("craters", 0.5, dict(n=2800, rmax=5.0))],
      "Black polish, three days old, picked at during every single class."),
]


def _fid(name):
    return ID_PREFIX + name.lower().replace(" ", "_").replace("-", "_").replace("'", "")


ALL_THAT = {_fid(r["name"]): r for r in _ROWS}


def title(fid):
    return "%s: %s" % (ALL_THAT[fid]["lane"].title(), ALL_THAT[fid]["name"])


import sys as _sys                                            # noqa: E402
EB.make(_sys.modules[__name__], ALL_THAT, _STRUCTS, P)
