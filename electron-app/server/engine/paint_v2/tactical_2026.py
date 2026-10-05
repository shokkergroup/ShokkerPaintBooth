# -*- coding: utf-8 -*-
"""🎯 TACTICAL & FIELD — 60 finishes. Half of the TACTICAL & CYBERPUNK split.

Owner: *"TACTICAL & CYBERPUNK — SPLIT IT into two categories with 60 finishes
each. The TACTICAL side will also include camo, outdoors-y stuff. I'm thinking
all different kinds of camo/military looks along with actual tactical stuff,
hunting/fishing etc."*

WHAT WAS THERE. Twenty ids doing two unrelated jobs in one shelf — ten camo /
military (`multicam`, `marpat_woodland`, `tiger_stripe`, `m81_woodland`,
`od_drab`, `coyote_fde`…) and ten neon-cyber (`tron_grid`, `data_rain`,
`glitch_rgb`, `holo_vapor`, `chrome_neon`…). They share a shelf and nothing
else, which is why splitting was the right call rather than a rebuild.

FOUR LANES, fifteen each:

  🌲 CAMO       the printed patterns — organic, digital, and the ones between
  🔫 HARDWARE   what the pattern is printed ON: cerakote, parkerising, kydex
  🎣 FIELD      hunting and fishing — canvas, blaze, waders, scale, topo
  🌙 NIGHT      what any of it looks like when the light is gone

MATERIALS. Almost none of this is shiny, which makes it a good test of the flat
end of the deck: `chalk`, `primer`, `rubber`, `suede`, `oxide` and `steel` carry
most of the shelf. Two finishes use the Fractured rail and both are in NIGHT,
where a surface is genuinely emitting. Blaze orange is the loudest thing here,
and it is loud because it is fluorescent, not because it is metallic.
"""
from __future__ import annotations

from engine.paint_v2 import era_base_2026 as EB
from engine.paint_v2 import era_kit_2026 as K

ID_PREFIX = "tac_"
GROUP = "🎯 TACTICAL & FIELD"
LANES = {"camo": "🌲 CAMO", "hardware": "🔫 HARDWARE", "field": "🎣 FIELD",
         "night": "🌙 NIGHT"}

_STRUCTS = {
    "camo":      lambda sh, sd, k: (K.camo(sh, sd, **k), None),
    "digicam":   lambda sh, sd, k: (K.digicam(sh, sd, **k), None),
    "topo":      lambda sh, sd, k: (K.topo(sh, sd, **k), None),
    "scales":    lambda sh, sd, k: (K.scales(sh, sd, **k), None),
    "knurl":     lambda sh, sd, k: (K.knurl(sh, sd, **k), None),
    "shag":      lambda sh, sd, k: (K.shag(sh, sd, **k), None),
    "tooled":    lambda sh, sd, k: (K.tooled(sh, sd, **k), None),
    "splatter":  lambda sh, sd, k: (K.splatter(sh, sd, **k), None),
    "glitch":    lambda sh, sd, k: (K.glitch(sh, sd, **k), None),
    "holo":      lambda sh, sd, k: (K.holo(sh, sd, **k), None),
    "scanline":  lambda sh, sd, k: (K.scanline(sh, sd, **k), None),
    "pixels":    lambda sh, sd, k: (K.pixels(sh, sd, **k), None),
    "sett":      lambda sh, sd, k: (K.sett(sh, sd, **k), None),
    "bands":     lambda sh, sd, k: (K.bands(sh, sd, **k), None),
    "curl":      lambda sh, sd, k: (K.curl(sh, sd, **k), None),
    "filaments": lambda sh, sd, k: (K.filaments(sh, sd, **k), None),
    "braid":     lambda sh, sd, k: (K.kh_braid(sh, sd, **k), None),
    "sparks":    lambda sh, sd, k: (K.sparks(sh, sd, **k), None),
    "craters":   lambda sh, sd, k: (K.craters(sh, sd, **k), None),
    "dunes":     lambda sh, sd, k: (K.dunes(sh, sd, **k), None),
    "cells":     lambda sh, sd, k: K.worley(sh, sd, **k),
    "percolate": lambda sh, sd, k: K.percolate(sh, sd, **k),
    "spall":     lambda sh, sd, k: K.spall(sh, sd, **k),
    "crack":     lambda sh, sd, k: K.anneal_crack(sh, sd, **k),
    "polygons":  lambda sh, sd, k: K.polygons(sh, sd, **k),
    "honeycomb": lambda sh, sd, k: K.honeycomb(sh, sd, **k),
    "dendrite":  lambda sh, sd, k: (K.dla(sh, sd, **k), None),
    "eden":      lambda sh, sd, k: (K.eden(sh, sd, **k), None),
    "wrinkle":   lambda sh, sd, k: (K.wrinkle(sh, sd, **k), None),
    "hull":      lambda sh, sd, k: K.hull(sh, sd, **k),
    "microtext": lambda sh, sd, k: (K.microtext(sh, sd, **k), None),
    "facets":    lambda sh, sd, k: K.facets(sh, sd, **k),
}

P = {
    # CAMO
    "woodland":   ((0.07, 0.09, 0.05), (0.20, 0.26, 0.14), (0.38, 0.36, 0.24), (0.62, 0.58, 0.44)),
    "marpat":     ((0.10, 0.12, 0.09), (0.26, 0.30, 0.20), (0.44, 0.42, 0.30), (0.70, 0.66, 0.52)),
    "tiger":      ((0.08, 0.10, 0.06), (0.18, 0.24, 0.13), (0.34, 0.32, 0.20), (0.58, 0.56, 0.40)),
    "multicam":   ((0.16, 0.14, 0.09), (0.36, 0.32, 0.20), (0.56, 0.50, 0.32), (0.80, 0.74, 0.54)),
    "desertcam":  ((0.22, 0.18, 0.11), (0.48, 0.41, 0.26), (0.70, 0.62, 0.44), (0.90, 0.85, 0.68)),
    "snowcam":    ((0.30, 0.32, 0.34), (0.58, 0.61, 0.64), (0.80, 0.83, 0.86), (0.97, 0.98, 1.00)),
    "duckblind":  ((0.10, 0.09, 0.05), (0.28, 0.24, 0.13), (0.50, 0.42, 0.24), (0.76, 0.66, 0.44)),
    "urbancam":   ((0.14, 0.15, 0.16), (0.34, 0.36, 0.38), (0.56, 0.58, 0.60), (0.82, 0.84, 0.86)),
    # HARDWARE
    "cerakote":   ((0.10, 0.11, 0.10), (0.26, 0.28, 0.26), (0.44, 0.46, 0.43), (0.66, 0.68, 0.64)),
    "parkerized": ((0.09, 0.09, 0.10), (0.22, 0.22, 0.24), (0.40, 0.40, 0.42), (0.62, 0.62, 0.64)),
    "fde":        ((0.18, 0.15, 0.10), (0.40, 0.34, 0.23), (0.62, 0.55, 0.40), (0.84, 0.78, 0.62)),
    "kydex":      ((0.07, 0.07, 0.08), (0.20, 0.20, 0.22), (0.36, 0.36, 0.38), (0.58, 0.58, 0.60)),
    "gunblue":    ((0.05, 0.06, 0.08), (0.14, 0.17, 0.22), (0.28, 0.32, 0.40), (0.50, 0.55, 0.64)),
    "odgreen":    ((0.09, 0.10, 0.06), (0.22, 0.26, 0.15), (0.38, 0.42, 0.26), (0.60, 0.64, 0.44)),
    "titanium":   ((0.16, 0.17, 0.18), (0.38, 0.40, 0.42), (0.62, 0.64, 0.66), (0.86, 0.88, 0.90)),
    # FIELD
    "blaze":      ((0.20, 0.06, 0.01), (0.60, 0.20, 0.02), (0.92, 0.42, 0.04), (1.00, 0.72, 0.30)),
    "canvasduck": ((0.20, 0.16, 0.10), (0.46, 0.38, 0.24), (0.70, 0.60, 0.42), (0.90, 0.84, 0.66)),
    "waders":     ((0.08, 0.10, 0.11), (0.20, 0.26, 0.28), (0.36, 0.44, 0.46), (0.58, 0.68, 0.70)),
    "troutscale": ((0.10, 0.13, 0.14), (0.28, 0.36, 0.36), (0.54, 0.62, 0.58), (0.84, 0.90, 0.84)),
    "decoy":      ((0.09, 0.07, 0.04), (0.26, 0.20, 0.11), (0.46, 0.36, 0.20), (0.72, 0.60, 0.38)),
    "riverstone": ((0.14, 0.15, 0.15), (0.34, 0.36, 0.36), (0.56, 0.58, 0.58), (0.82, 0.84, 0.84)),
    "autumnbrush":((0.13, 0.08, 0.04), (0.36, 0.22, 0.09), (0.62, 0.40, 0.16), (0.88, 0.70, 0.40)),
    # NIGHT
    "nvgreen":    ((0.01, 0.04, 0.02), (0.03, 0.22, 0.08), (0.14, 0.56, 0.24), (0.60, 0.96, 0.66)),
    "thermal":    ((0.03, 0.02, 0.10), (0.28, 0.06, 0.40), (0.86, 0.26, 0.14), (1.00, 0.90, 0.42)),
    "irblack":    ((0.03, 0.03, 0.04), (0.10, 0.10, 0.12), (0.22, 0.22, 0.26), (0.40, 0.40, 0.46)),
    "chemlight":  ((0.03, 0.07, 0.05), (0.10, 0.34, 0.16), (0.42, 0.78, 0.24), (0.86, 1.00, 0.60)),
    "muzzle":     ((0.04, 0.03, 0.02), (0.26, 0.14, 0.03), (0.72, 0.44, 0.08), (1.00, 0.88, 0.44)),
    "moonlit":    ((0.05, 0.07, 0.11), (0.14, 0.20, 0.30), (0.30, 0.40, 0.54), (0.60, 0.72, 0.86)),
    "starlight":  ((0.02, 0.03, 0.05), (0.08, 0.12, 0.18), (0.22, 0.30, 0.42), (0.52, 0.64, 0.80)),
}


def R(name, lane, palette, deck, seed, stack, desc, mix="sum", edge=None,
      dither=0.15, r_spread=26.0, gamma=1.0, hue_jitter=9.0, cell_mean=1.0):
    return dict(name=name, lane=lane, palette=palette, deck=deck, seed=seed,
                stack=stack, desc=desc, mix=mix, edge=edge, dither=dither,
                r_spread=r_spread, gamma=gamma, hue_jitter=hue_jitter,
                cell_mean=cell_mean)


_ROWS = [
    # ══════════════════════ 🌲 CAMO (15) ═══════════════════════════════════
    R("M81 Woodland", "camo", "woodland", "chalk", 3101,
      [("camo", 1.0, dict(patches=4, blob=140)), ("braid", 0.85, dict(layers=124, shear=1.2)),
       ("cells", 0.5, dict(cells=170))],
      "Four colours, organic blobs, and the pattern every army copied for thirty years.", cell_mean=0.35),
    R("MARPAT Digital", "camo", "marpat", "chalk", 3102,
      [("braid", 1.0, dict(layers=140, shear=1.0)),
       ("digicam", 0.85, dict(cell=5, patches=4, cluster=2.0)),
       ("filaments", 0.6, dict(n=2400, length=12, wander=0.8))],
      "Pixels at two scales at once, so it breaks up close AND at distance.", cell_mean=0.35),
    R("Tiger Stripe", "camo", "tiger", "suede", 3103,
      [("bands", 1.0, dict(n=72, shear=2.8, vortex=22, turb=0.6)), ("camo", 0.6, dict(patches=3, blob=110))],
      "Brush strokes running horizontally, cut for jungle where the light is vertical."),
    R("Multicam Transition", "camo", "multicam", "chalk", 3104,
      [("camo", 1.0, dict(patches=5, blob=170, roughness=0.7)),
       ("braid", 0.9, dict(layers=120, shear=1.3)), ("percolate", 0.5, dict(cells=168))],
      "Seven colours that blend rather than edge, so it works in more than one place.", cell_mean=0.35),
    R("Desert DPM", "camo", "desertcam", "chalk", 3105,
      [("braid", 1.0, dict(layers=140, shear=1.5)),
       ("camo", 0.85, dict(patches=3, blob=190, roughness=1.2)),
       ("filaments", 0.6, dict(n=2600, length=12, wander=0.8))],
      "Two-colour disruptive over sand, printed on cotton that faded in one tour.", cell_mean=0.35),
    R("Snow Overwhite", "camo", "snowcam", "chalk", 3106,
      [("braid", 1.0, dict(layers=144, shear=1.1)), ("camo", 0.8, dict(patches=3, blob=210)),
       ("craters", 0.7, dict(n=3600, rmax=4.5))],
      "An oversuit pulled over everything else, tearing on the first fence.", cell_mean=0.35),
    R("Duck Blind", "camo", "duckblind", "suede", 3107,
      [("filaments", 1.0, dict(n=2600, length=42, wander=0.5)), ("camo", 0.6, dict(patches=4, blob=130))],
      "Photo-real reed and cattail, printed so the pattern never repeats in view."),
    R("Urban Grey Digital", "camo", "urbancam", "chalk", 3108,
      [("braid", 1.0, dict(layers=142, shear=1.0)), ("digicam", 0.85, dict(cell=5, patches=4)),
       ("knurl", 0.6, dict(pitch=16))],
      "The one everybody agrees does not work anywhere, still issued for a decade.", cell_mean=0.35),
    R("Brushstroke Field", "camo", "woodland", "suede", 3109,
      [("splatter", 1.0, dict(blobs=520, rmax=20, drips=0.15, spatter=1.4)),
       ("braid", 0.9, dict(layers=118, shear=1.4)), ("camo", 0.6, dict(patches=3, blob=150))],
      "Painted by hand onto shelter-halves, which is where all of this started."),
    R("Frog Skin", "camo", "marpat", "suede", 3110,
      [("percolate", 1.0, dict(cells=132, p=0.44)), ("scales", 0.5, dict(cell=30, keel=0.35))],
      "Reversible spot pattern, green one side and beach the other."),
    R("Chocolate Chip", "camo", "desertcam", "chalk", 3111,
      [("camo", 1.0, dict(patches=4, blob=160)), ("craters", 0.55, dict(n=2600, rmax=6.5))],
      "Six colours with black pebble spots, for a desert that had no pebbles."),
    R("Rain Pattern", "camo", "urbancam", "chalk", 3112,
      [("filaments", 1.0, dict(n=3000, length=30, wander=0.12)), ("camo", 0.5, dict(patches=3, blob=170))],
      "Vertical dashes over a base, the Eastern Bloc answer to everything above."),
    R("Flecktarn", "camo", "woodland", "chalk", 3113,
      [("craters", 1.0, dict(n=4400, rmax=7.0, rim=0.5)), ("camo", 0.6, dict(patches=4, blob=120))],
      "Dense spots that dither into each other at ten metres."),
    R("Tigerstripe Night", "camo", "irblack", "rubber", 3114,
      [("bands", 1.0, dict(n=66, shear=3.0, vortex=24, turb=0.66)), ("percolate", 0.5, dict(cells=176))],
      "The same stripe in blacks that differ only in how they take IR."),
    R("Break-Up Bark", "camo", "autumnbrush", "suede", 3115,
      [("crack", 1.0, dict(cells=112, width=2.4, gen=1)), ("filaments", 0.6, dict(n=2200, length=34))],
      "Photo bark and limbs, printed so a treestand outline stops being a shape."),

    # ══════════════════════ 🔫 HARDWARE (15) ═══════════════════════════════
    R("Cerakote Grey", "hardware", "cerakote", "primer", 3201,
      [("percolate", 1.0, dict(cells=182, p=0.5)), ("craters", 0.5, dict(n=3200, rmax=4.5))],
      "Ceramic in a polymer carrier, sprayed thin and baked — flatter than paint."),
    R("Parkerised", "hardware", "parkerized", "primer", 3202,
      [("craters", 1.0, dict(n=4200, rmax=5.5, rim=0.6)), ("cells", 0.5, dict(cells=164))],
      "Manganese phosphate, porous by design so it holds oil in the surface."),
    R("FDE Polymer", "hardware", "fde", "rubber", 3203,
      [("knurl", 1.0, dict(pitch=16, angle=45, relief=1.2)), ("percolate", 0.5, dict(cells=178))],
      "Moulded-in texture on a polymer frame, in the tan that replaced black."),
    R("Kydex Sheet", "hardware", "kydex", "plastic", 3204,
      [("knurl", 1.0, dict(pitch=20, angle=0, relief=0.85)), ("wrinkle", 0.5, dict(k=0.9, steps=13))],
      "Thermoformed over the mould, with the pebble grain the sheet came with."),
    R("Gun Blue", "hardware", "gunblue", "steel", 3205,
      [("curl", 1.0, dict(scale=52, steps=16)), ("craters", 0.45, dict(n=2400, rmax=4.5))],
      "Hot salts and an oil wipe, over steel polished to 400 grit first."),
    R("Rail Section", "hardware", "cerakote", "steel", 3206,
      [("bands", 1.0, dict(n=112, shear=0.5, vortex=2, turb=0.12)), ("knurl", 0.5, dict(pitch=22))],
      "Slots at a fixed pitch, anodised, with the numbers laser-etched."),
    R("Suppressor Heat", "hardware", "titanium", "oxide", 3207,
      [("bands", 1.0, dict(n=88, shear=1.6, vortex=10, turb=0.4)), ("percolate", 0.5, dict(cells=160))],
      "Titanium that has been hot enough, often enough, to colour in rings."),
    R("Optic Glass", "hardware", "gunblue", "glass", 3208,
      [("holo", 1.0, dict(rings=330, orders=2)), ("craters", 0.4, dict(n=2200, rmax=5.0))],
      "Multi-coated lens, purple in reflection, doing its job by not being seen."),
    R("Stippled Grip", "hardware", "kydex", "rubber", 3209,
      [("craters", 1.0, dict(n=5200, rmax=4.0, rim=0.9)), ("percolate", 0.45, dict(cells=180))],
      "Burned into the polymer with a soldering iron, badly, by the owner."),
    R("Anodised Hard", "hardware", "odgreen", "steel", 3210,
      [("knurl", 1.0, dict(pitch=19, angle=30, relief=1.0)), ("cells", 0.5, dict(cells=166))],
      "Type III hardcoat — thicker than the metal it grew out of, and matte."),
    R("Carbon Handguard", "hardware", "parkerized", "steel", 3211,
      [("braid", 1.0, dict(layers=126, shear=1.6)), ("knurl", 0.45, dict(pitch=24))],
      "Twill weave under resin, cool to the touch after a string nobody should fire."),
    R("Nitride Black", "hardware", "irblack", "primer", 3212,
      [("percolate", 1.0, dict(cells=186, p=0.52)), ("craters", 0.5, dict(n=3600, rmax=4.0))],
      "Nitrocarburised to 70 Rockwell, and the blackest surface in the case."),
    R("Battle Worn", "hardware", "fde", "oxide", 3213,
      [("spall", 1.0, dict(cells=112, lift=0.66)), ("craters", 0.55, dict(n=3000, rmax=6.0))],
      "Cerakote worn through to metal at every edge a hand or a wall has found."),
    R("Titanium Bead", "hardware", "titanium", "steel", 3214,
      [("craters", 1.0, dict(n=4600, rmax=4.5, rim=0.75)), ("cells", 0.45, dict(cells=172))],
      "Bead blasted to a uniform matte so nothing on it can catch the sun."),
    R("Sling Webbing", "hardware", "odgreen", "suede", 3215,
      [("braid", 1.0, dict(layers=96, shear=1.0)), ("filaments", 0.55, dict(n=2000, length=16))],
      "Mil-spec nylon, edge-sealed with a flame, in the green that fades to grey."),

    # ══════════════════════ 🎣 FIELD (15) ══════════════════════════════════
    R("Blaze Orange", "field", "blaze", "chalk", 3301,
      [("braid", 1.0, dict(layers=110, shear=1.3)), ("percolate", 0.5, dict(cells=172))],
      "Fluorescent, which means it emits more than it reflects, which is the point."),
    R("Canvas Duck", "field", "canvasduck", "suede", 3302,
      [("braid", 1.0, dict(layers=88, shear=0.9)), ("filaments", 0.6, dict(n=2400, length=14))],
      "Twelve-ounce cotton, waxed, that stands up on its own after a season."),
    R("Neoprene Wader", "field", "waders", "rubber", 3303,
      [("percolate", 1.0, dict(cells=176, p=0.5)), ("knurl", 0.5, dict(pitch=20, angle=45))],
      "Five mil, with a boot foot and a patch kit you will need in October."),
    R("Trout Flank", "field", "troutscale", "pearl", 3304,
      [("scales", 1.0, dict(cell=18, keel=0.7, sheen=1.2)), ("craters", 0.45, dict(n=2600, rmax=4.5))],
      "Guanine platelets under the skin — a mirror that only works from below."),
    R("Cedar Decoy", "field", "decoy", "eggshell", 3305,
      [("bands", 1.0, dict(n=96, shear=1.4, vortex=8, turb=0.34)), ("spall", 0.5, dict(cells=118))],
      "Carved, painted, and chipped by forty seasons of being thrown into a bag."),
    R("River Stone", "field", "riverstone", "chalk", 3306,
      [("cells", 1.0, dict(cells=112)), ("craters", 0.55, dict(n=2800, rmax=6.5))],
      "Rounded cobble in a shallow run, seen through a foot of moving water."),
    R("Topo Sheet", "field", "canvasduck", "eggshell", 3307,
      [("filaments", 1.0, dict(n=3000, length=12, wander=0.85)),
       ("topo", 0.9, dict(lines=240, index=5)), ("cells", 0.6, dict(cells=152))],
      "A 1:24000 quad folded to the section you need, with a pencil line on it."),
    R("Autumn Brush", "field", "autumnbrush", "suede", 3308,
      [("filaments", 1.0, dict(n=3400, length=22, wander=0.6)),
       ("eden", 0.7, dict(seeds=2400, steps=9)), ("cells", 0.5, dict(cells=162))],
      "Oak and maple after the first frost, which is when everything moves."),
    R("Fly Line", "field", "troutscale", "plastic", 3309,
      [("filaments", 1.0, dict(n=1800, length=54, wander=0.1, width=2.4)),
       ("cells", 0.9, dict(cells=158)), ("craters", 0.5, dict(n=2600, rmax=5.0))],
      "Weight-forward, floating, in a colour you can track against grey water."),
    R("Blaze Cap", "field", "blaze", "suede", 3310,
      [("sett", 1.0, dict(pitch=44, stripes=(0.34, 0.08, 0.06, 0.26, 0.08, 0.10))),
       ("filaments", 0.5, dict(n=1800, length=13))],
      "Knit blaze with a black band, the one thing everyone in the woods agrees on."),
    R("Wet Waxed Cotton", "field", "decoy", "wet", 3311,
      [("wrinkle", 1.0, dict(k=1.15, steps=16)), ("craters", 0.5, dict(n=2600, rmax=5.0))],
      "Wax bloomed to the surface, beading rain for about the first hour."),
    R("Creel Wicker", "field", "canvasduck", "suede", 3312,
      [("braid", 1.0, dict(layers=76, shear=2.4)), ("cells", 0.5, dict(cells=158))],
      "Split willow woven wet, with a leather strap gone black at the buckle."),
    R("Marsh Reed", "field", "duckblind", "chalk", 3313,
      [("filaments", 1.0, dict(n=2800, length=54, wander=0.22)), ("dunes", 0.45, dict(n=40))],
      "Phragmites standing dead through winter, the colour of old straw."),
    R("Bird Dog Tick", "field", "riverstone", "suede", 3314,
      [("craters", 1.0, dict(n=4800, rmax=5.0, rim=0.55)), ("percolate", 0.5, dict(cells=164))],
      "German shorthair ticking — the roan that is neither white nor liver."),
    R("Frozen Bank", "field", "snowcam", "glass", 3315,
      [("crack", 1.0, dict(cells=124, width=2.2, gen=1)), ("craters", 0.5, dict(n=2800, rmax=5.5))],
      "Shelf ice over a slow edge, with the current still moving under it."),

    # ══════════════════════ 🌙 NIGHT (15) ══════════════════════════════════
    R("Night Vision", "night", "nvgreen", "neon", 3401,
      [("sparks", 1.0, dict(n=5200, life=9, spread=1.5)), ("scanline", 0.5, dict(lines=170, bloom=0.6))],
      "P43 phosphor and the scintillation that never quite settles."),
    R("Thermal White Hot", "night", "thermal", "carrier", 3402,
      [("curl", 1.0, dict(scale=48, steps=18)), ("percolate", 0.5, dict(cells=166))],
      "Temperature mapped to brightness, so a warm engine is the brightest thing."),
    R("IR Flat", "night", "irblack", "primer", 3403,
      [("percolate", 1.0, dict(cells=184, p=0.52)), ("craters", 0.5, dict(n=3400, rmax=4.5))],
      "Near-IR-matched black — the same to the eye, very different through a tube."),
    R("Chem Light", "night", "chemlight", "carrier", 3404,
      [("sparks", 1.0, dict(n=5000, life=12)),
       ("filaments", 0.8, dict(n=2400, length=34, wander=0.2, width=2.4)),
       ("cells", 0.5, dict(cells=158))],
      "Snapped, shaken, and good for eight hours of exactly one colour."),
    R("Muzzle Flash", "night", "muzzle", "gold", 3405,
      [("sparks", 1.0, dict(n=3800, life=26, spread=2.0)), ("curl", 0.5, dict(scale=38, steps=18))],
      "Unburnt powder igniting outside the barrel, gone in two milliseconds."),
    R("Moonlit Snow", "night", "moonlit", "glass", 3406,
      [("craters", 1.0, dict(n=3200, rmax=6.0)), ("dunes", 0.5, dict(n=44))],
      "Enough light to read by, and no colour in any of it."),
    R("Starlight Scope", "night", "starlight", "chalk", 3407,
      [("sparks", 1.0, dict(n=4600, life=7, spread=1.2)), ("percolate", 0.5, dict(cells=178))],
      "Image intensified from almost nothing, with the grain that comes free."),
    R("Tracer Arc", "night", "muzzle", "neon", 3408,
      [("filaments", 1.0, dict(n=520, length=110, wander=0.1, width=2.0)),
       ("sparks", 0.6, dict(n=2200, life=30))],
      "Every fifth round burning, which shows the trajectory to everyone."),
    R("Red Lens", "night", "thermal", "gloss", 3409,
      [("holo", 1.0, dict(rings=300, orders=2)), ("cells", 0.45, dict(cells=170))],
      "The filter that preserves dark adaptation, over a map at 0300."),
    R("Cold Steel Night", "night", "gunblue", "steel", 3410,
      [("curl", 1.0, dict(scale=56, steps=16)), ("craters", 0.45, dict(n=2400, rmax=5.0))],
      "Bare metal at minus ten, taking heat out of a hand through a glove."),
    R("Thermal Black Hot", "night", "irblack", "rubber", 3411,
      [("curl", 1.0, dict(scale=44, steps=20)), ("percolate", 0.55, dict(cells=172))],
      "The same sensor with the palette inverted, which some people prefer."),
    R("Ambush Green", "night", "nvgreen", "chalk", 3412,
      [("sparks", 1.0, dict(n=4600, life=10)), ("eden", 0.8, dict(seeds=2200, steps=9)),
       ("cells", 0.5, dict(cells=164))],
      "Foliage through a tube: every leaf the same brightness, no depth at all."),
    R("Signal Mirror", "night", "moonlit", "chrome", 3413,
      [("facets", 1.0, dict(stones=200, table=0.32)), ("knurl", 0.45, dict(pitch=26))],
      "Two square inches of glass that can be seen from an aircraft at ten miles."),
    R("Blackout Curtain", "night", "irblack", "velvet", 3414,
      [("shag", 1.0, dict(strands=4800, length=26, splay=0.5)), ("cells", 0.4, dict(cells=176))],
      "Napped blackout cloth over a doorway, so no light says anyone is here."),
    R("Frost Breath", "night", "starlight", "glass", 3415,
      [("crack", 1.0, dict(cells=138, width=1.9, gen=1)), ("craters", 0.5, dict(n=3000, rmax=5.0))],
      "Vapour freezing on a collar, which is the one thing camouflage cannot fix."),
]


def _fid(name):
    return ID_PREFIX + name.lower().replace(" ", "_").replace("-", "_").replace("'", "")


TACTICAL = {_fid(r["name"]): r for r in _ROWS}


def title(fid):
    return "%s: %s" % (TACTICAL[fid]["lane"].title(), TACTICAL[fid]["name"])


import sys as _sys                                            # noqa: E402
EB.make(_sys.modules[__name__], TACTICAL, _STRUCTS, P)
