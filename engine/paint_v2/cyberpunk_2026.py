# -*- coding: utf-8 -*-
"""🌃 CYBERPUNK — 60 finishes. The other half of the TACTICAL & CYBERPUNK split.

Owner: *"The Cyberpunk can be it's own thing with 60 finishes. There's so many
lanes we can play with in Cyberpunk."*

WHAT WAS THERE. Ten ids sharing a shelf with ten camo patterns — `neon_circuit`,
`tron_grid`, `synthwave`, `data_rain`, `glitch_rgb`, `hex_tech`, `holo_vapor`,
`chrome_neon`, `plasma_pulse`, `cyber_camo`. Half of them are the same neon-on-
black idea at different hues, and `synthwave` belongs to the 1980s shelf now.

FOUR LANES, fifteen each — and they are deliberately four different KINDS of
surface, not four colourways of neon:

  🌃 STREET     the wet city at night — signage, rain, market, sodium, holo ad
  🦾 CHROME     the body — augments, ports, subdermals, ceramic, wetware
  💊 NETRUN     inside the system — ICE, datastream, corrupt memory, daemon
  ☢ SPRAWL     the parts nobody photographs — decay, corp grey, rad, scav

MATERIALS. STREET is wet and emissive, CHROME is metal and ceramic, NETRUN is
glass and glitch, SPRAWL is oxide, rubber and chalk. That spread is the point:
the old shelf's failure was that "cyberpunk" meant "neon", and neon is a light
source, not a material. Fractured rail on eight of sixty — the highest of the
five new shelves, and appropriate here because a Fractured carrier reads as
exactly the kind of surface that should not exist.
"""
from __future__ import annotations

from engine.paint_v2 import era_base_2026 as EB
from engine.paint_v2 import era_kit_2026 as K

ID_PREFIX = "cbp_"
GROUP = "🌃 CYBERPUNK"
LANES = {"street": "🌃 STREET", "chrome": "🦾 CHROME", "netrun": "💊 NETRUN",
         "sprawl": "☢ SPRAWL"}

_STRUCTS = {
    "glitch":    lambda sh, sd, k: (K.glitch(sh, sd, **k), None),
    "holo":      lambda sh, sd, k: (K.holo(sh, sd, **k), None),
    "scanline":  lambda sh, sd, k: (K.scanline(sh, sd, **k), None),
    "pixels":    lambda sh, sd, k: (K.pixels(sh, sd, **k), None),
    "wireframe": lambda sh, sd, k: (K.wireframe(sh, sd, **k), None),
    "scales":    lambda sh, sd, k: (K.scales(sh, sd, **k), None),
    "topo":      lambda sh, sd, k: (K.topo(sh, sd, **k), None),
    "digicam":   lambda sh, sd, k: (K.digicam(sh, sd, **k), None),
    "knurl":     lambda sh, sd, k: (K.knurl(sh, sd, **k), None),
    "microtext": lambda sh, sd, k: (K.microtext(sh, sd, **k), None),
    "glyphs":    lambda sh, sd, k: (K.glyphs(sh, sd, **k), None),
    "hull":      lambda sh, sd, k: K.hull(sh, sd, **k),
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
    "dendrite":  lambda sh, sd, k: (K.dla(sh, sd, **k), None),
    "eden":      lambda sh, sd, k: (K.eden(sh, sd, **k), None),
    "wrinkle":   lambda sh, sd, k: (K.wrinkle(sh, sd, **k), None),
    "facets":    lambda sh, sd, k: K.facets(sh, sd, **k),
    "discs":     lambda sh, sd, k: (K.discs(sh, sd, **k), None),
    "dunes":     lambda sh, sd, k: (K.dunes(sh, sd, **k), None),
    "guilloche": lambda sh, sd, k: (K.guilloche(sh, sd, **k), None),
    "stars":     lambda sh, sd, k: (K.stars(sh, sd, **k), None),
    "moire":     lambda sh, sd, k: (K.moire(sh, sd, **k), None),
    "shag":      lambda sh, sd, k: (K.shag(sh, sd, **k), None),
}

P = {
    # STREET
    "sodium":     ((0.06, 0.04, 0.02), (0.30, 0.16, 0.03), (0.72, 0.44, 0.10), (1.00, 0.84, 0.44)),
    "wetasphalt": ((0.04, 0.05, 0.07), (0.14, 0.17, 0.22), (0.34, 0.40, 0.48), (0.72, 0.80, 0.90)),
    "signage":    ((0.05, 0.03, 0.08), (0.44, 0.06, 0.32), (0.10, 0.52, 0.60), (0.98, 0.88, 0.40)),
    "nightmarket":((0.08, 0.05, 0.03), (0.36, 0.14, 0.08), (0.80, 0.36, 0.14), (1.00, 0.80, 0.42)),
    "hoload":     ((0.04, 0.05, 0.12), (0.14, 0.28, 0.56), (0.62, 0.24, 0.70), (0.94, 0.88, 0.98)),
    "acidrain":   ((0.05, 0.08, 0.07), (0.14, 0.30, 0.24), (0.36, 0.58, 0.46), (0.76, 0.92, 0.82)),
    "taxiyellow": ((0.10, 0.07, 0.02), (0.42, 0.30, 0.04), (0.82, 0.66, 0.10), (1.00, 0.94, 0.50)),
    # CHROME
    "subdermal":  ((0.12, 0.11, 0.12), (0.34, 0.32, 0.34), (0.66, 0.64, 0.66), (0.94, 0.94, 0.96)),
    "porthole":   ((0.07, 0.08, 0.10), (0.22, 0.26, 0.32), (0.48, 0.54, 0.62), (0.82, 0.88, 0.94)),
    "ceramicarm": ((0.20, 0.21, 0.22), (0.52, 0.54, 0.56), (0.80, 0.82, 0.84), (0.98, 0.99, 1.00)),
    "gunmetalaug":((0.08, 0.09, 0.10), (0.24, 0.26, 0.30), (0.46, 0.50, 0.56), (0.74, 0.78, 0.84)),
    "wetware":    ((0.10, 0.05, 0.08), (0.32, 0.12, 0.22), (0.58, 0.30, 0.42), (0.86, 0.66, 0.74)),
    "goldport":   ((0.12, 0.09, 0.03), (0.40, 0.30, 0.06), (0.72, 0.56, 0.16), (0.96, 0.86, 0.46)),
    "carbonlimb": ((0.05, 0.05, 0.06), (0.16, 0.16, 0.18), (0.34, 0.34, 0.38), (0.60, 0.60, 0.66)),
    # NETRUN
    "icewall":    ((0.02, 0.06, 0.12), (0.06, 0.26, 0.52), (0.26, 0.60, 0.90), (0.78, 0.94, 1.00)),
    "datastream": ((0.02, 0.06, 0.04), (0.05, 0.28, 0.14), (0.20, 0.62, 0.30), (0.70, 0.98, 0.74)),
    "corrupt":    ((0.06, 0.03, 0.08), (0.34, 0.06, 0.30), (0.76, 0.16, 0.44), (0.98, 0.72, 0.84)),
    "daemon":     ((0.05, 0.02, 0.03), (0.28, 0.05, 0.08), (0.66, 0.14, 0.16), (0.94, 0.56, 0.50)),
    "blacktrace": ((0.03, 0.03, 0.05), (0.10, 0.10, 0.16), (0.26, 0.26, 0.38), (0.56, 0.56, 0.72)),
    "ghostnet":   ((0.06, 0.09, 0.11), (0.18, 0.30, 0.36), (0.44, 0.62, 0.70), (0.84, 0.94, 0.98)),
    "quantumviol":((0.05, 0.03, 0.11), (0.20, 0.08, 0.42), (0.52, 0.26, 0.78), (0.88, 0.72, 0.99)),
    # SPRAWL
    "corpgrey":   ((0.13, 0.14, 0.15), (0.32, 0.34, 0.36), (0.54, 0.56, 0.58), (0.78, 0.80, 0.82)),
    "radwarn":    ((0.10, 0.09, 0.03), (0.34, 0.30, 0.05), (0.72, 0.64, 0.10), (0.98, 0.92, 0.44)),
    "scavrust":   ((0.11, 0.05, 0.02), (0.34, 0.16, 0.06), (0.60, 0.32, 0.14), (0.86, 0.58, 0.32)),
    "ductgrime":  ((0.08, 0.08, 0.07), (0.22, 0.22, 0.20), (0.40, 0.40, 0.36), (0.64, 0.64, 0.58)),
    "concreterot":((0.16, 0.16, 0.15), (0.38, 0.38, 0.36), (0.60, 0.60, 0.57), (0.84, 0.84, 0.80)),
    "biohazard":  ((0.05, 0.09, 0.05), (0.16, 0.34, 0.14), (0.46, 0.72, 0.20), (0.88, 0.98, 0.56)),
    "oilslick":   ((0.04, 0.04, 0.06), (0.14, 0.16, 0.22), (0.40, 0.28, 0.48), (0.78, 0.70, 0.86)),
}


def R(name, lane, palette, deck, seed, stack, desc, mix="sum", edge=None,
      dither=0.15, r_spread=26.0, gamma=1.0, hue_jitter=12.0, cell_mean=1.0):
    return dict(name=name, lane=lane, palette=palette, deck=deck, seed=seed,
                stack=stack, desc=desc, mix=mix, edge=edge, dither=dither,
                r_spread=r_spread, gamma=gamma, hue_jitter=hue_jitter,
                cell_mean=cell_mean)


_ROWS = [
    # ══════════════════════ 🌃 STREET (15) ═════════════════════════════════
    R("Wet Asphalt", "street", "wetasphalt", "wet", 4101,
      [("curl", 1.0, dict(scale=50, steps=18)), ("craters", 0.55, dict(n=3200, rmax=6.0))],
      "The road after rain, holding every sign in the street upside down."),
    R("Sodium Vapour", "street", "sodium", "neon", 4102,
      [("filaments", 1.0, dict(n=820, length=60, wander=0.2)), ("sparks", 0.5, dict(n=2400, life=24))],
      "Low-pressure sodium: one wavelength, so nothing under it has a colour."),
    R("Kanji Signage", "street", "signage", "neon", 4103,
      [("glyphs", 1.0, dict(n=620, stroke=2.4, size=18)), ("filaments", 0.5, dict(n=900, length=40))],
      "Stacked vertical signs, six deep, all of them for something on floor four."),
    R("Holo Advert", "street", "hoload", "dichroic", 4104,
      [("holo", 1.0, dict(rings=350, orders=3)), ("scanline", 0.5, dict(lines=180, bloom=0.7))],
      "A twelve-storey projection selling something that does not need selling."),
    R("Night Market", "street", "nightmarket", "gloss", 4105,
      [("honeycomb", 1.0, dict(cells=142)), ("sparks", 0.5, dict(n=3000, life=20))],
      "Tarpaulin, strung bulbs, steam, and forty stalls in one alley."),
    R("Acid Rain", "street", "acidrain", "wet", 4106,
      [("craters", 1.0, dict(n=4200, rmax=6.0, rim=0.8)), ("curl", 0.5, dict(scale=58, steps=16))],
      "Falling through a sodium beam, pitting anything left outside."),
    R("Taxi Panel", "street", "taxiyellow", "lacquer", 4107,
      [("spall", 1.0, dict(cells=118, lift=0.55)), ("microtext", 0.5, dict(rows=120))],
      "Repainted over a repaint, with the previous operator's number showing through."),
    R("Steam Grate", "street", "ductgrime", "steel", 4108,
      [("knurl", 1.0, dict(pitch=17, angle=0, relief=1.2)), ("percolate", 0.5, dict(cells=172))],
      "Cast iron over a vent, warm enough to sleep beside if you get there first."),
    R("Puddle Neon", "street", "signage", "wet", 4109,
      [("curl", 1.0, dict(scale=44, steps=20)), ("holo", 0.5, dict(rings=300))],
      "The reflection is more saturated than the sign, which is why it gets shot."),
    R("Shutter Tag", "street", "nightmarket", "chalk", 4110,
      [("bands", 1.0, dict(n=118, shear=0.4, vortex=2, turb=0.12)),
       ("filaments", 0.6, dict(n=1600, length=40, wander=0.5))],
      "A rolling shutter, down, with two generations of tags on it."),
    R("Rain Screen", "street", "wetasphalt", "glass", 4111,
      [("filaments", 1.0, dict(n=2600, length=44, wander=0.06)), ("craters", 0.5, dict(n=2800, rmax=5.0))],
      "Vertical water on glass, with the drops that win racing the ones that don't."),
    R("Sodium Fog", "street", "sodium", "chalk", 4112,
      [("curl", 1.0, dict(scale=64, steps=14)), ("sparks", 0.45, dict(n=2600, life=18))],
      "Particulate in the beam, which is the only reason you can see the beam."),
    R("Vending Glow", "street", "hoload", "plastic", 4113,
      [("polygons", 1.0, dict(cells=96, relief=0.5)), ("scanline", 0.5, dict(lines=190))],
      "A lit machine on an empty street, the brightest thing for two blocks."),
    R("Neon Tube", "street", "signage", "carrier", 4114,
      [("filaments", 1.0, dict(n=1800, length=48, wander=0.14, width=2.2)),
       ("holo", 0.8, dict(rings=340)), ("sparks", 0.6, dict(n=3200, life=14))],
      "Bent glass, argon, and a transformer that has been humming since 2019."),
    R("Overpass Sodium", "street", "taxiyellow", "oxide", 4115,
      [("percolate", 1.0, dict(cells=150, p=0.46)), ("spall", 0.55, dict(cells=110))],
      "Concrete under a bridge, stained by forty years of exactly one colour of light."),

    # ══════════════════════ 🦾 CHROME (15) ═════════════════════════════════
    R("Subdermal Plate", "chrome", "subdermal", "chrome", 4201,
      [("hull", 1.0, dict(panels=90, seam=1.6, rivets=0.5)), ("knurl", 0.45, dict(pitch=24))],
      "Armour under the skin, with the seams visible when the light rakes.", edge="chrome"),
    R("Neural Port", "chrome", "porthole", "steel", 4202,
      [("craters", 1.0, dict(n=2600, rmax=9.0, rim=0.9)), ("knurl", 0.5, dict(pitch=20))],
      "A socket at the base of the skull, machined to a tolerance nobody checks."),
    R("Ceramic Limb", "chrome", "ceramicarm", "gloss", 4203,
      [("crack", 1.0, dict(cells=140, width=1.8, gen=1)), ("cells", 0.5, dict(cells=164))],
      "Zirconia over a titanium frame, glazed white and already hairline-crazed."),
    R("Gunmetal Aug", "chrome", "gunmetalaug", "steel", 4204,
      [("bands", 1.0, dict(n=104, shear=1.0, vortex=5, turb=0.22)), ("craters", 0.5, dict(n=2600, rmax=5.0))],
      "The budget option: heavy, loud, and it does not pretend to be a hand."),
    R("Wetware Membrane", "chrome", "wetware", "wet", 4205,
      [("dendrite", 1.0, dict(seeds=1000)), ("curl", 0.55, dict(scale=46, steps=18))],
      "Cultured tissue over a lattice, kept wet because it is still alive."),
    R("Gold Contact", "chrome", "goldport", "gold", 4206,
      [("guilloche", 1.0, dict(period=64, ring=9)), ("sparks", 0.5, dict(n=2400, life=18))],
      "Plated pins in a connector, gold because it is the metal that will not oxidise."),
    R("Carbon Limb", "chrome", "carbonlimb", "steel", 4207,
      [("braid", 1.0, dict(layers=130, shear=1.6)), ("knurl", 0.45, dict(pitch=22))],
      "Twill weave under clear, light enough to be uncanny to watch move."),
    R("Optic Implant", "chrome", "porthole", "glass", 4208,
      [("holo", 1.0, dict(rings=340, orders=2)), ("facets", 0.5, dict(stones=200))],
      "The lens catches light at angles a real eye does not, and everyone notices."),
    R("Chrome Spine", "chrome", "subdermal", "chrome", 4209,
      [("scales", 1.0, dict(cell=20, keel=0.75)), ("knurl", 0.5, dict(pitch=18))],
      "Segmented, articulated, and polished on the segments a jacket does not cover."),
    R("Skin Weave", "chrome", "wetware", "suede", 4210,
      [("braid", 1.0, dict(layers=122, shear=1.3)), ("filaments", 0.6, dict(n=2600, length=12, wander=0.8))],
      "Subdermal mesh — you can feel the grid through the skin over it."),
    R("Ripperdoc Steel", "chrome", "gunmetalaug", "steel", 4211,
      [("spall", 1.0, dict(cells=116, lift=0.6)), ("craters", 0.5, dict(n=3000, rmax=5.5))],
      "Back-alley work, autoclaved twice, installed under a light that flickers."),
    R("Porcelain Face", "chrome", "ceramicarm", "pearl", 4212,
      [("percolate", 1.0, dict(cells=178, p=0.5)), ("holo", 0.5, dict(rings=290))],
      "A full cosmetic shell, perfect, and about four percent too symmetrical."),
    R("Servo Housing", "chrome", "carbonlimb", "rubber", 4213,
      [("knurl", 1.0, dict(pitch=15, angle=45, relief=1.35)), ("percolate", 0.5, dict(cells=180))],
      "Moulded boot over the joint, keeping grit out of something expensive."),
    R("Titanium Rib", "chrome", "subdermal", "steel", 4214,
      [("hull", 1.0, dict(panels=110, seam=1.2, rivets=0.7)), ("craters", 0.45, dict(n=2400, rmax=4.5))],
      "Printed lattice, bedded into bone, showing on an X-ray like a rumour."),
    R("Mirror Shades", "chrome", "goldport", "chrome", 4215,
      [("facets", 1.0, dict(stones=210, table=0.30)), ("holo", 0.5, dict(rings=310))],
      "Worn indoors, at night, which was always the point of them.", edge="mercury"),

    # ══════════════════════ 💊 NETRUN (15) ═════════════════════════════════
    R("Ice Wall", "netrun", "icewall", "glass", 4301,
      [("polygons", 1.0, dict(cells=132, relief=0.7)), ("crack", 0.9, dict(cells=130, gen=1)),
       ("knurl", 0.5, dict(pitch=18, angle=45))],
      "Intrusion countermeasures rendered as a surface, because a mind needs a metaphor."),
    R("Datastream", "netrun", "datastream", "neon", 4302,
      [("glyphs", 1.0, dict(n=760, stroke=2.0, size=15)), ("filaments", 0.55, dict(n=1400, length=52, wander=0.08))],
      "Characters falling in columns, which is not how data moves and looks right anyway.", cell_mean=0.0),
    R("Corrupt Memory", "netrun", "corrupt", "plastic", 4303,
      [("glitch", 1.0, dict(slices=140, shift=62, tear=0.52, block=0.36)),
       ("pixels", 0.9, dict(cell=6, levels=9)), ("sparks", 0.6, dict(n=3400, life=8))],
      "A block that failed its checksum and got written to screen anyway.", cell_mean=0.0),
    R("Black ICE", "netrun", "daemon", "carrier", 4304,
      [("dendrite", 1.0, dict(seeds=1100, walkers=22000)), ("cells", 0.9, dict(cells=156)),
       ("sparks", 0.6, dict(n=3000, life=26))],
      "The kind that is legal to deploy and will stop your heart on the way out."),
    R("Trace Route", "netrun", "blacktrace", "steel", 4305,
      [("guilloche", 1.0, dict(period=72, ring=10, teeth=(4, 7))), ("microtext", 0.5, dict(rows=130))],
      "Somebody walking back up the connection, one hop at a time, patiently."),
    R("Ghost Protocol", "netrun", "ghostnet", "glass", 4306,
      [("holo", 1.0, dict(rings=330, orders=3)), ("curl", 0.5, dict(scale=54, steps=16))],
      "Traffic that is there and not there, depending on which log you read."),
    R("Quantum Violet", "netrun", "quantumviol", "spectral", 4307,
      [("holo", 1.0, dict(rings=380, orders=3)), ("moire", 0.5, dict(lpi=190, depth=0.45))],
      "A key that is every value until somebody looks at it."),
    R("Daemon Red", "netrun", "daemon", "neon", 4308,
      [("scanline", 1.0, dict(lines=128)), ("glitch", 0.8, dict(slices=120, shift=44, tear=0.4)),
       ("sparks", 0.5, dict(n=3000, life=9))],
      "A process with no owner, running since before the current administration.", cell_mean=0.0),
    R("Packet Loss", "netrun", "blacktrace", "plastic", 4309,
      [("pixels", 1.0, dict(cell=6, levels=9, dither=0.5)),
       ("glitch", 0.8, dict(slices=150, shift=48)), ("sparks", 0.6, dict(n=3600, life=8))],
      "Thirty percent gone, and the codec inventing the rest with confidence.", cell_mean=0.0),
    R("Firewall Grid", "netrun", "icewall", "neon", 4310,
      [("sparks", 1.0, dict(n=5200, life=14)),
       ("wireframe", 0.8, dict(rows=110, persp=1.1, width=1.3)),
       ("cells", 0.5, dict(cells=166))],
      "The boundary drawn as a lattice, which is at least honest about being a rule.", cell_mean=0.0),
    R("Neural Static", "netrun", "ghostnet", "chalk", 4311,
      [("sparks", 1.0, dict(n=5000, life=8, spread=1.4)), ("percolate", 0.5, dict(cells=178))],
      "What the interface gives you when the connection is bad and the jack is warm."),
    R("Deep Archive", "netrun", "blacktrace", "rubber", 4312,
      [("microtext", 1.0, dict(rows=150, density=0.66)), ("percolate", 0.5, dict(cells=176))],
      "Cold storage, spinning down, holding something everyone has agreed to forget."),
    R("Worm Trail", "netrun", "corrupt", "carrier", 4313,
      [("dendrite", 1.0, dict(seeds=1200)), ("glitch", 0.5, dict(slices=64, shift=38))],
      "Propagation mapped over a night — it looks organic because it is."),
    R("Encryption Lattice", "netrun", "quantumviol", "glass", 4314,
      [("polygons", 1.0, dict(cells=128, relief=0.6)), ("holo", 0.5, dict(rings=300))],
      "The cipher drawn as a crystal, which is a lie that helps."),
    R("Root Access", "netrun", "datastream", "carrier", 4315,
      [("filaments", 1.0, dict(n=900, length=66, wander=0.18)), ("glyphs", 0.55, dict(n=520, size=14))],
      "One prompt, no password, and everything downstream now belongs to somebody else."),

    # ══════════════════════ ☢ SPRAWL (15) ══════════════════════════════════
    R("Corp Grey", "sprawl", "corpgrey", "primer", 4401,
      [("hull", 1.0, dict(panels=104, seam=1.3, rivets=0.4, wear=0.5)),
       ("percolate", 0.5, dict(cells=176))],
      "The colour of every building owned by a company with a three-letter name."),
    R("Rad Warning", "sprawl", "radwarn", "chalk", 4402,
      [("stars", 1.0, dict(cell=88, points=3, interlace=0.4)), ("spall", 0.5, dict(cells=114))],
      "The trefoil, stencilled, half worn off, and still perfectly legible."),
    R("Scav Rust", "sprawl", "scavrust", "oxide", 4403,
      [("percolate", 1.0, dict(cells=146, p=0.48)), ("spall", 0.6, dict(cells=108, lift=0.68))],
      "Everything not bolted down was taken; this is what the bolts left behind."),
    R("Duct Grime", "sprawl", "ductgrime", "rubber", 4404,
      [("knurl", 1.0, dict(pitch=18, angle=90, relief=1.0)), ("dendrite", 0.5, dict(seeds=900))],
      "Galvanised trunking with thirty years of building on the outside of it."),
    R("Concrete Rot", "sprawl", "concreterot", "chalk", 4405,
      [("crack", 1.0, dict(cells=118, width=2.8, gen=1)), ("craters", 0.55, dict(n=3200, rmax=6.5))],
      "Spalling where the rebar underneath has rusted and grown."),
    R("Biohazard Bloom", "sprawl", "biohazard", "chalk", 4406,
      [("eden", 1.0, dict(seeds=2600, steps=10)), ("percolate", 0.55, dict(cells=168))],
      "Something growing in a stairwell that the building manual does not cover."),
    R("Oil Slick Puddle", "sprawl", "oilslick", "dichroic", 4407,
      [("holo", 1.0, dict(rings=360, orders=3)), ("curl", 0.5, dict(scale=48, steps=18))],
      "A film one wavelength thick, which is why it is every colour at once."),
    R("Rebar Skeleton", "sprawl", "scavrust", "steel", 4408,
      [("filaments", 1.0, dict(n=1100, length=60, wander=0.2, width=2.6)),
       ("percolate", 0.5, dict(cells=164))],
      "A floor plate that never got poured, going orange in the weather."),
    R("Ash Fall", "sprawl", "ductgrime", "chalk", 4409,
      [("dunes", 1.0, dict(n=46)), ("sparks", 0.5, dict(n=3400, life=10))],
      "Particulate from something burning two districts over, settling on everything."),
    R("Corp Glass", "sprawl", "corpgrey", "glass", 4410,
      [("polygons", 1.0, dict(cells=84, relief=0.65)), ("craters", 0.5, dict(n=2600, rmax=5.0))],
      "Curtain wall, mirrored outward, so the building never has to look at the street."),
    R("Hazard Stripe", "sprawl", "radwarn", "plastic", 4411,
      [("bands", 1.0, dict(n=78, shear=1.8, vortex=6, turb=0.24)), ("spall", 0.5, dict(cells=120))],
      "Diagonal yellow and black, which every species on earth now reads as a threat."),
    R("Sewer Bloom", "sprawl", "biohazard", "wet", 4412,
      [("dendrite", 1.0, dict(seeds=1300)), ("curl", 0.5, dict(scale=52, steps=16))],
      "Runoff in a channel, iridescent where it should not be."),
    R("Scrap Weld", "sprawl", "scavrust", "steel", 4413,
      [("craters", 1.0, dict(n=2600, rmax=8.5, rim=0.85)), ("spall", 0.5, dict(cells=112))],
      "Stick welded by somebody in a hurry, ground flat by nobody at all."),
    R("Static Screen", "sprawl", "corpgrey", "plastic", 4414,
      [("scanline", 1.0, dict(lines=134)), ("glitch", 0.85, dict(slices=150, shift=56, tear=0.55, block=0.3)),
       ("cells", 0.5, dict(cells=170))],
      "A public display that has shown the same fault for long enough to be a landmark.", cell_mean=0.0),
    R("Cracked Solar", "sprawl", "oilslick", "glass", 4415,
      [("polygons", 1.0, dict(cells=136, relief=0.55)), ("crack", 0.55, dict(cells=126, gen=1))],
      "A panel array with a third of its cells shattered and still feeding the grid."),
]


def _fid(name):
    out = name.lower().replace(" ", "_").replace("-", "_").replace("'", "")
    out = "".join(ch for ch in out if ch.isascii())
    return ID_PREFIX + out.strip("_")


CYBERPUNK = {_fid(r["name"]): r for r in _ROWS}


def title(fid):
    return "%s: %s" % (CYBERPUNK[fid]["lane"].title(), CYBERPUNK[fid]["name"])


import sys as _sys                                            # noqa: E402
EB.make(_sys.modules[__name__], CYBERPUNK, _STRUCTS, P)
