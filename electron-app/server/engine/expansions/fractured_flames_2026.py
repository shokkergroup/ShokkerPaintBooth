# -*- coding: utf-8 -*-
"""🔥 FRACTURED FLAMES — the 2026-08-30 rebuild. 144 cards -> 75.

THE CATEGORY HAS ONE ARC: **the life of a fire**, in five chapters. A card is a
moment in that life, and its material state is what the fire did to the surface
at that moment — which is why the spec is authored per chapter, not per palette.

  🜂 IGNITION   the catch — sparks, char creep, the front before there is a flame
  🔥 FLAME      the body — reaction sheets, wrinkled fronts, turbulent braids
  ⚡ PLASMA      past flame — arcs, streamers, ionisation, magnetised jets
  🌋 MOLTEN     what melts — lava skin, slag, weld pools, quenched glass
  🜃 CINDER      after — ember beds, ash, soot, clinker, spall

WHAT THE OLD 135 GOT WRONG (measured, `_flames_work/triage.py`):
  * a CROSS-PRODUCT of 51 structures x 3 spec modes x a palette NAME, where the
    palette never reached the paint — every "(Blue)" card was orange, and a
    structure's 2-3 cards were byte-identical paint;
  * 42 of 51 structures were posters, not fields (`radial` scored car-band
    0.005 — one sunburst on a whole car).

So here: ONE card per idea, no matrix. Colour comes from `kit.emit()`, which is
Planck's law through the CIE observer plus real chemiluminescence, so the fuel
that is burning decides the hue *in the paint*. Every card stacks 2-4 field
primitives (owner Rule 4) tuned to the 8-32px car-visible window.

AI-as-compiler: the engine is `fractured_flames_kit_2026`; each finish below is
a ~6-line recipe. Adding a finish is adding a row, never new code.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

import engine.expansions.fractured_flames_kit_2026 as kit
from engine.expansions.fractured_flames_kit_2026 import GEN, WORK

ID_PREFIX = "ffl_"
GROUP = "🔥 FRACTURED FLAMES"

# ════════════════════════════════════════════════════════════════════════════
# FIELD COMBINATOR — a recipe's "build" is a stack of (primitive, weight, kw)
# ════════════════════════════════════════════════════════════════════════════

def _prim(name, shape, seed, kw):
    """Run one primitive. The two that also produce a label field return it so
    the card can tier its shades per cell and the spec can pick one complete
    material card per cell."""
    f = getattr(kit, name)
    out = f(shape, seed, **kw)
    return out if isinstance(out, tuple) else (out, None)


def build_heat(build, shape, seed, mix="sum"):
    """Stack primitives into one heat field (0..1) + the best label field found.

    `mix`:  sum  weighted average — layered material
            max  brightest wins   — sparks/embers ON something
            mul  product          — one field gates the other (masking)
    """
    acc = None
    lab = None
    wsum = 0.0
    h0 = int(shape[0])
    for i, (name, wgt, kw) in enumerate(build):
        # Secondary layers solve at half resolution and upscale — that is where
        # the multi-Worley cards were spending the last second of a 3s budget.
        # But ONLY the expensive field solvers. The cheap point/line primitives
        # (sparks, filaments, DLA — all under 0.1s) are precisely the ones
        # carrying the finest marks, and halving them doubled their feature size
        # and threw away the detail they were added for: a third fine layer
        # moved a failing card's car-band score by 0.01 instead of clearing it.
        _HEAVY = ("worley", "percolate", "anneal_crack", "spall", "curl",
                  "wrinkle", "eden", "rt_fingers")
        sub = (i > 0 and float(wgt) <= 0.7 and h0 >= 768 and name in _HEAVY)
        sh = (h0 // 2, int(shape[1]) // 2) if sub else shape
        f, l = _prim(name, sh, seed + 101 * i, dict(kw))
        if sub:
            f = kit.upscale(f, h0)
            l = kit.upscale(l, h0) if l is not None else None
        if l is not None and lab is None:
            lab = l
        if acc is None:
            acc = f * float(wgt)
            wsum = float(wgt)
        elif mix == "max":
            acc = np.maximum(acc, f * float(wgt))
        elif mix == "mul":
            acc = acc * (0.35 + 0.65 * f * float(wgt))
        else:
            acc = acc + f * float(wgt)
            wsum += float(wgt)
    if mix == "sum" and wsum > 0:
        acc = acc / wsum
    return kit.pct(acc), lab


# ════════════════════════════════════════════════════════════════════════════
# CHAPTER SPEC GRAMMAR — Spec Guide v1 §7 causality, one band map per chapter
# ════════════════════════════════════════════════════════════════════════════
#
# A band map reads bottom-up in heat: what the surface became at that heat.
#
# EVERY BAND MUST BE A MATERIALLY DIFFERENT SURFACE. The first pass stacked
# soot / porous / flat / ash in the same map — four names for "rough dielectric
# with no coat", separated by 10-30 bytes of green. Half the canvas was then one
# material wearing four labels, and the spec maps rendered as flat cyan with
# black dots. The fix is to walk the material cube, not one corner of it:
# alternate dielectric and metal, matte and polished, coated and bare, so
# adjacent bands are visibly different surfaces at every step. Causality still
# leads — this is what the fire DID — but two states that a driver could never
# tell apart do not both earn a band.
CHAPTER_SPEC = {
    # unburnt paint -> scorch -> oxidising metal -> the ignition point itself
    "ignition": dict(bands=(("flat", 0.24), ("soot", 0.42), ("scale", 0.60),
                            ("satin", 0.76), ("gloss", 0.90), ("spark", 1.01)),
                     edge="hotedge", razor=0.05, edge_pct=96.5, r_spread=30.0),
    # the body of a flame: dead soot, vitrified skin, bare metal, wet core
    "flame":    dict(bands=(("soot", 0.20), ("glaze", 0.38), ("steel", 0.56),
                            ("satin", 0.74), ("wet", 0.92), ("spark", 1.01)),
                     edge="hotedge", razor=0.08, edge_pct=97.0, r_spread=26.0),
    # ionised: the Fractured night-carrier population lives HERE and nowhere else
    "plasma":   dict(bands=(("soot", 0.20), ("carrier0", 0.42), ("carrier1", 0.62),
                            ("carrier2", 0.80), ("razor", 0.92), ("spark", 1.01)),
                     edge="spark", razor=0.14, edge_pct=97.6, r_spread=18.0,
                     cc_offset=5),
    # melted and re-frozen: ash crust, oxide scale, bare steel, wet melt
    "molten":   dict(bands=(("ash", 0.18), ("scale", 0.36), ("steel", 0.54),
                            ("satin", 0.72), ("wet", 0.90), ("spark", 1.01)),
                     edge="hotedge", razor=0.04, edge_pct=97.2, r_spread=34.0),
    # what is left: mostly dead, but the retained heat still shows as metal
    "cinder":   dict(bands=(("soot", 0.28), ("scale", 0.48), ("ash", 0.66),
                            ("steel", 0.82), ("satin", 0.94), ("gloss", 1.01)),
                     edge="steel", razor=0.02, edge_pct=98.4, r_spread=22.0),
}

CHAPTERS = {
    "ignition": "🜂 IGNITION",
    "flame": "🔥 FLAME",
    "plasma": "⚡ PLASMA",
    "molten": "🌋 MOLTEN",
    "cinder": "🜃 CINDER",
}


def R(name, chapter, fuel, seed, build, mix="sum", tiers=8, line_at=0.72,
      line_amt=0.85, jitter=0.10, gen=GEN, spec=None, desc="", **extra):
    """One finish. Everything a card needs, in one row.

    `**extra` lets a single card override any emit/spec knob the chapter default
    would otherwise give it — mix_fuel, mix_frac, tint, substrate, sub_at —
    without turning the shared engine into a pile of special cases."""
    row = dict(name=name, chapter=chapter, fuel=fuel, seed=seed, build=build,
               mix=mix, tiers=tiers, line_at=line_at, line_amt=line_amt,
               jitter=jitter, gen=gen, spec=spec or {}, desc=desc)
    row.update(extra)
    return row


# ════════════════════════════════════════════════════════════════════════════
# THE 75
# ════════════════════════════════════════════════════════════════════════════

_ROWS = [
    # ─────────────────────── 🜂 IGNITION (15) ────────────────────────────────
    R("Flashpoint", "ignition", "wood", 1101,
      [("eden", 1.0, dict(seeds=900, steps=14)), ("sparks", 0.8, dict(n=1900, life=34))],
      mix="max", desc="The instant it catches — a ragged burn front with the first embers already thrown clear."),
    R("Char Creep", "ignition", "char", 1102,
      [("eden", 1.0, dict(seeds=700, steps=18, aniso=(1.7, 0.7))), ("dla", 0.55, dict(seeds=420))],
      tiers=7, line_at=0.80, mono=True,   # grey by nature: ash and soot have no second chemistry
      desc="Blackening crawls across the surface along the grain, carbon dendrites trailing behind it."),
    R("Tinder Bloom", "ignition", "wood", 1103,
      [("filaments", 1.0, dict(n=340, length=38)), ("eden", 0.7, dict(seeds=1200, steps=10))],
      desc="Dry fibre catching all at once: hundreds of thin bright threads opening out of a rough front."),
    R("Match Head", "ignition", "strontium", 1104,
      [("sparks", 1.0, dict(n=2400, life=28, spread=2.1)), ("worley", 0.6, dict(cells=120))],
      mix="max", tiers=9, line_at=0.50, line_amt=0.72, tint=0.24,
      substrate=(0.10, 0.13, 0.26), sub_at=0.34,
      desc="Crimson strontium flare — the chemical head burning ahead of the wood."),
    R("Smoulder Bed", "ignition", "coal", 1105,
      [("percolate", 1.0, dict(cells=170, p=0.42)), ("dla", 0.5, dict(seeds=600))],
      tiers=9, line_at=0.78, desc="Heat travelling underground through a packed bed, glowing only where it found air."),
    R("Fuse Line", "ignition", "potassium", 1106,
      [("filaments", 1.0, dict(n=220, length=64, wander=0.18)), ("sparks", 0.7, dict(n=1400, life=26))],
      mix="max", desc="Lilac potassium running along a powder trail, spitting as it goes."),
    R("Kindle Lattice", "ignition", "wood", 1107,
      [("worley", 1.0, dict(cells=140)), ("eden", 0.65, dict(seeds=1500, steps=9))],
      desc="Stacked kindling seen from above, each cell lighting on its own schedule."),
    R("Spark Shower", "ignition", "thermite", 1108,
      [("sparks", 1.0, dict(n=2600, life=44, g=0.9, spread=2.4)), ("curl", 0.45, dict(scale=96))],
      mix="max", tiers=9, line_at=0.58, desc="White-gold thermite spray, every particle burning out along its own arc."),
    R("Ember Catch", "ignition", "coal", 1109,
      [("percolate", 1.0, dict(cells=150, p=0.46)), ("sparks", 0.75, dict(n=1500, life=30))],
      mix="max", desc="A landed ember taking hold — bright cores spreading into the cold bed around them."),
    R("Pilot Ring", "ignition", "methane", 1110,
      [("kh_braid", 1.0, dict(layers=96, shear=2.4)), ("worley", 0.8, dict(cells=118)),
       ("filaments", 0.42, dict(n=120, length=26))],
      tiers=7, line_at=0.60, line_amt=0.92, desc="The blue pilot crown: cool methane braids holding a steady standing flame."),
    R("Autoignition", "ignition", "furnace", 1111,
      [("wrinkle", 1.0, dict(k=1.1, steps=11)), ("dla", 0.5, dict(seeds=380))],
      desc="No spark needed — the whole surface reaches temperature at once and creases as it goes."),
    R("Firebrand Scatter", "ignition", "wood", 1112,
      [("sparks", 1.0, dict(n=1300, life=58, drag=0.03, width=1.1)), ("eden", 0.6, dict(seeds=600, steps=12))],
      mix="max", desc="Burning debris carried downwind, each brand starting a new small front where it lands."),
    R("Scorch Front", "ignition", "char", 1113,
      [("wrinkle", 1.0, dict(k=0.8, steps=10)), ("eden", 0.65, dict(seeds=1600, steps=8)),
       ("filaments", 0.5, dict(n=380, length=30, width=1.0))],
      tiers=7, line_at=0.82, desc="The dark boundary between what has burned and what has not, creased by its own heat."),
    R("Ignition Delay", "ignition", "sulfur", 1114,
      [("curl", 1.0, dict(scale=72, steps=14)), ("percolate", 0.6, dict(cells=190, p=0.38))],
      tiers=7, line_at=0.66, desc="Fuel and air mixed but not yet lit — pale sulfur blue drifting over a cold bed."),
    R("Touchpaper", "ignition", "sodium", 1115,
      [("dla", 1.0, dict(seeds=700, walkers=16000)), ("worley", 0.6, dict(cells=140)),
       ("filaments", 0.65, dict(n=260, length=30))],
      tiers=9, line_at=0.68, mix_fuel="cupric", mix_frac=0.34,
      desc="Amber sodium creeping through treated paper along every fibre at once."),

    # ─────────────────────── 🔥 FLAME (15) ───────────────────────────────────
    R("Diffusion Sheet", "flame", "wood", 1201,
      [("filaments", 1.0, dict(n=420, length=52, width=1.0)), ("curl", 0.7, dict(scale=64))],
      desc="Where fuel meets air the burn is a SURFACE, not a volume — a shoal of thin reaction sheets."),
    R("Wrinkled Front", "flame", "furnace", 1202,
      [("wrinkle", 1.0, dict(k=0.9, steps=16)), ("curl", 0.55, dict(scale=80))],
      desc="Michelson-Sivashinsky cusping: a flame front unstable to its own curvature, creasing everywhere."),
    R("Darrieus Cell", "flame", "methane", 1203,
      [("worley", 1.0, dict(cells=110)), ("wrinkle", 0.6, dict(k=1.2, steps=12))],
      tiers=7, line_at=0.58, line_amt=0.9, desc="Darrieus-Landau cellular instability — a premixed flame breaking into its own honeycomb."),
    R("Turbulent Braid", "flame", "wood", 1204,
      [("kh_braid", 1.0, dict(layers=96, shear=3.6)), ("curl", 0.7, dict(scale=56))],
      desc="Shear at the flame edge rolling into braid after braid, never one big billow."),
    R("Flamelet Storm", "flame", "coal", 1205,
      [("filaments", 1.0, dict(n=500, length=40)), ("wrinkle", 0.65, dict(k=1.0, steps=10))],
      desc="Turbulence tears the front into thousands of independent flamelets, each burning on its own."),
    R("Buoyant Fingers", "flame", "wood", 1206,
      [("rt_fingers", 1.0, dict(n=110, gain=1.6)), ("curl", 0.6, dict(scale=64))],
      desc="Rayleigh-Taylor: hot gas punching up through cold in a hundred small fingers."),
    R("Shear Tongue", "flame", "sodium", 1207,
      [("kh_braid", 1.0, dict(layers=84, shear=4.2)), ("filaments", 0.7, dict(n=300, length=44))],
      tiers=9, line_at=0.66, desc="Amber tongues leaning off a shear layer, licked into ribbons by the crossflow."),
    R("Pool Puff", "flame", "coal", 1208,
      [("rt_fingers", 1.0, dict(n=90, gain=1.3)), ("worley", 0.6, dict(cells=100))],
      desc="A pool fire breathing — the periodic puff of a buoyant plume, resolved into cells."),
    R("Candle Cone", "flame", "wood", 1209,
      [("wrinkle", 1.0, dict(k=0.7, steps=18, scale=220)), ("filaments", 0.6, dict(n=240, length=48))],
      tiers=9, line_at=0.70, desc="The quiet laminar burn of a wick, all its structure in the fine creases of the sheath."),
    R("Blowtorch", "flame", "methane", 1210,
      [("curl", 1.0, dict(scale=48, steps=18, step_px=3.4)), ("sparks", 0.55, dict(n=1200, life=24))],
      mix="max", tiers=7, line_at=0.56, line_amt=0.95, desc="Forced-air blue: the flame stretched thin and fast, streaks running with the jet."),
    R("Backdraft Wrinkle", "flame", "furnace", 1211,
      [("wrinkle", 1.0, dict(k=1.3, steps=10)), ("eden", 0.6, dict(seeds=800, steps=9))],
      desc="Starved, then fed — the front folds back on itself the instant the air arrives."),
    R("Fire Whirl Grain", "flame", "wood", 1212,
      [("curl", 1.0, dict(scale=40, steps=26)), ("kh_braid", 0.65, dict(layers=96, shear=2.8))],
      desc="Rotation stretches every filament into the same handedness — a whirl written in grain, not in a spiral."),
    R("Laminar Ladder", "flame", "methane", 1213,
      [("kh_braid", 1.0, dict(layers=96, shear=1.6)), ("worley", 0.75, dict(cells=112))],
      tiers=7, line_at=0.58, line_amt=0.9, desc="An orderly premixed burn: rungs of blue at a fixed spacing, cells filling between them."),
    R("Crown Fire", "flame", "wood", 1214,
      [("filaments", 1.0, dict(n=380, length=56, wander=0.42)), ("rt_fingers", 0.7, dict(n=100))],
      desc="Fire in the canopy — it stops running along the ground and starts leaping between crowns."),
    R("Stoichiometric Seam", "flame", "boron", 1215,
      [("filaments", 1.0, dict(n=300, length=50, width=1.0)), ("worley", 0.6, dict(cells=120))],
      tiers=9, line_at=0.64, line_amt=0.95, desc="Emerald boron marking the exact ratio line where fuel and oxidiser are perfectly matched."),

    # ─────────────────────── ⚡ PLASMA (15) ──────────────────────────────────
    R("Arc Filament", "plasma", "plasma", 1301,
      [("filaments", 1.0, dict(n=260, length=70, wander=0.22, width=1.0)), ("dla", 0.6, dict(seeds=400))],
      tiers=9, line_at=0.58, desc="Past burning: an ionised channel that carries current, not fuel."),
    R("Ionised Braid", "plasma", "plasma", 1302,
      [("kh_braid", 1.0, dict(layers=96, shear=4.6)), ("sparks", 0.6, dict(n=1800, life=26))],
      mix="max", tiers=9, line_at=0.60, desc="Current and field braiding around each other down the length of the column."),
    R("Magnetised Jet", "plasma", "cupric", 1303,
      [("curl", 0.7, dict(scale=30, steps=11, step_px=4.0)), ("filaments", 1.0, dict(n=460, length=38, width=1.0)),
       ("sparks", 0.8, dict(n=2600, life=24, width=0.8))],
      tiers=9, line_at=0.56, line_amt=0.95, desc="Copper-blue plasma collimated by its own magnetic field into a single hard direction."),
    R("Corona Grain", "plasma", "plasma", 1304,
      [("dla", 1.0, dict(seeds=900, walkers=18000)), ("sparks", 0.7, dict(n=2200, life=22))],
      mix="max", tiers=9, line_at=0.62, desc="The violet haze at the edge of a charged surface, grainy right down to the pixel."),
    R("Streamer Web", "plasma", "potassium", 1305,
      [("dla", 1.0, dict(seeds=520, walkers=20000, steps=52)), ("worley", 0.55, dict(cells=150)),
       ("filaments", 0.6, dict(n=200, length=60))],
      tiers=9, line_at=0.60, desc="Streamers branching ahead of the main channel, each looking for the easiest path."),
    R("Townsend Cascade", "plasma", "plasma", 1306,
      [("dla", 1.0, dict(seeds=700)), ("percolate", 0.65, dict(cells=180, p=0.40))],
      tiers=9, line_at=0.58, desc="One electron becomes two, two become four — avalanche until the whole gap conducts."),
    R("Pinch Instability", "plasma", "plasma", 1307,
      [("kh_braid", 1.0, dict(layers=96, shear=5.2)), ("rt_fingers", 0.7, dict(n=120, gain=1.7))],
      tiers=9, line_at=0.62, desc="The column squeezes itself, necks, and tears — sausage instability written across the surface."),
    R("Cathode Spot", "plasma", "magnesium", 1308,
      [("worley", 1.0, dict(cells=150)), ("sparks", 0.8, dict(n=2000, life=24, spread=2.2))],
      mix="max", tiers=9, line_at=0.66, desc="Blinding white attachment points skittering across the electrode surface."),
    R("Glow Discharge", "plasma", "boron", 1309,
      [("curl", 1.0, dict(scale=88, steps=14)), ("worley", 0.6, dict(cells=110))],
      tiers=8, line_at=0.60, line_amt=0.9, desc="Low pressure, low current — an even green glow with visible striations in it."),
    R("Lichtenberg Burn", "plasma", "plasma", 1310,
      [("dla", 1.0, dict(seeds=1100, walkers=24000, steps=58)), ("eden", 0.55, dict(seeds=700, steps=10))],
      tiers=9, line_at=0.56, desc="The fractal scar a discharge leaves behind, branching at every scale it can find."),
    R("Plasma Sheath", "plasma", "cupric", 1311,
      [("wrinkle", 0.75, dict(k=1.1, steps=12)), ("kh_braid", 0.6, dict(layers=96, shear=3.2)),
       ("sparks", 1.0, dict(n=2400, life=22, width=0.8))],
      tiers=8, line_at=0.58, line_amt=0.92, desc="The thin charged skin that forms wherever plasma meets a solid wall."),
    R("Spectral Line", "plasma", "barium", 1312,
      [("filaments", 1.0, dict(n=320, length=46)), ("worley", 0.6, dict(cells=130))],
      tiers=9, line_at=0.58, line_amt=0.95, desc="Apple-green barium emitting on one narrow line and nothing else."),
    R("Electron Avalanche", "plasma", "plasma", 1313,
      [("sparks", 1.0, dict(n=3000, life=30, spread=2.6, width=0.8)), ("dla", 0.7, dict(seeds=600))],
      mix="max", tiers=9, line_at=0.60, desc="Every track a carrier multiplying as it runs; the surface saturates from the leading edge back."),
    R("Tokamak Ripple", "plasma", "methane", 1314,
      [("kh_braid", 1.0, dict(layers=96, shear=2.0)), ("curl", 0.6, dict(scale=60))],
      tiers=8, line_at=0.56, line_amt=0.9, desc="Confined and stable — nested flux surfaces rippling in step."),
    R("Aurora Column", "plasma", "boron", 1315,
      [("curl", 0.7, dict(scale=44, steps=16)), ("rt_fingers", 0.6, dict(n=120, gain=1.4)),
       ("filaments", 1.0, dict(n=420, length=34, width=1.0))],
      tiers=9, line_at=0.58, line_amt=0.95, mix_fuel="strontium", mix_frac=0.30,
      desc="Charged particles following field lines down — curtains of green standing on end."),

    # ─────────────────────── 🌋 MOLTEN (15) ──────────────────────────────────
    R("Pahoehoe Skin", "molten", "coal", 1401,
      [("curl", 1.0, dict(scale=52, steps=16, step_px=3.2)), ("wrinkle", 0.7, dict(k=0.8, steps=10))],
      desc="The ropy skin of slow lava, folding over itself as the crust drags on the flow beneath."),
    R("Slag Crust", "molten", "furnace", 1402,
      [("anneal_crack", 1.0, dict(cells=64, width=2.2, gen=1)), ("percolate", 0.6, dict(cells=160, p=0.44))],
      desc="Waste glass floating on the melt, cracked into plates with heat still showing through the seams."),
    R("Lava Cell", "molten", "coal", 1403,
      [("worley", 1.0, dict(cells=96)), ("curl", 0.7, dict(scale=60))],
      desc="Convection cells on an open melt — dark crust above, orange shear at every boundary."),
    R("Quench Craze", "molten", "quench", 1404,
      [("anneal_crack", 1.0, dict(cells=80, width=1.8, gen=2)), ("worley", 0.5, dict(cells=150))],
      tiers=9, line_at=0.66, desc="Hot glass into cold water: a craze network that keeps sub-dividing its own biggest fragments."),
    R("Vitrified Glaze", "molten", "quench", 1405,
      [("anneal_crack", 1.0, dict(cells=110, width=1.4, gen=1)), ("worley", 0.55, dict(cells=140))],
      tiers=9, line_at=0.70, desc="Ash fused to a glassy skin, then cooled until it crazed — kiln chemistry, not paint."),
    R("Weld Pool", "molten", "furnace", 1406,
      [("kh_braid", 1.0, dict(layers=88, shear=2.2)), ("spall", 0.65, dict(cells=90))],
      desc="The frozen ripple record of a moving arc, each crescent one pulse of the weld."),
    R("Molten Drip", "molten", "thermite", 1407,
      [("filaments", 1.0, dict(n=280, length=68, wander=0.14)), ("curl", 0.6, dict(scale=56))],
      tiers=9, line_at=0.56, mix_fuel="copper", mix_frac=0.34, tint=0.24,
      desc="White-hot metal running and freezing on the way down, in hundreds of fine rivulets."),
    R("Crucible Skin", "molten", "furnace", 1408,
      [("spall", 1.0, dict(cells=84, lift=0.62)), ("anneal_crack", 0.6, dict(cells=100, width=2.0))],
      desc="Oxide plates lifting off the wall of a crucible, each curled at the edge and lit underneath."),
    R("Basalt Column", "molten", "char", 1409,
      [("worley", 1.0, dict(cells=72, jitter=0.55)), ("anneal_crack", 0.65, dict(cells=90, width=2.6))],
      tiers=7, line_at=0.80, desc="Cooling contraction cracking a flow into columns — the same physics as mud, at 1200 degrees."),
    R("Obsidian Chill", "molten", "char", 1410,
      [("anneal_crack", 1.0, dict(cells=120, width=1.6, gen=1)), ("curl", 0.6, dict(scale=64, steps=14))],
      tiers=7, line_at=0.84, mix_fuel="cupric", mix_frac=0.40, tint=0.26,
      substrate=(0.09, 0.11, 0.15), desc="Cooled too fast to crystallise: black glass with conchoidal fracture running through it."),
    R("Foundry Spatter", "molten", "thermite", 1411,
      [("sparks", 1.0, dict(n=2200, life=36, g=0.85)), ("spall", 0.6, dict(cells=80))],
      mix="max", tiers=9, line_at=0.60, desc="Thrown metal freezing where it lands, pocking the plate it lands on."),
    R("Tuyere Glow", "molten", "furnace", 1412,
      [("worley", 1.0, dict(cells=120)), ("curl", 0.65, dict(scale=48, steps=22))],
      desc="Looking in through the blast port: the hottest zone of the furnace, seen through moving gas."),
    R("Slumped Glass", "molten", "quench", 1413,
      [("curl", 1.0, dict(scale=68, steps=18)), ("wrinkle", 0.65, dict(k=0.7, steps=11))],
      tiers=9, line_at=0.72, desc="Glass gone soft and taken the shape it was resting on, the flow still legible in the surface."),
    R("Magma Vesicle", "molten", "coal", 1414,
      [("worley", 1.0, dict(cells=130, kind="f1")), ("percolate", 0.6, dict(cells=160, p=0.44))],
      desc="Gas coming out of solution — bubbles frozen at the instant the melt stopped moving."),
    R("Ropy Flow", "molten", "coal", 1415,
      [("curl", 1.0, dict(scale=40, steps=22, step_px=3.6)), ("filaments", 0.65, dict(n=300, length=54))],
      desc="Fast pahoehoe: the skin dragged into tight parallel ropes by the flow under it."),

    # ─────────────────────── 🜃 CINDER (15) ──────────────────────────────────
    R("Ember Bed", "cinder", "coal", 1501,
      [("percolate", 1.0, dict(cells=160, p=0.46)), ("worley", 0.6, dict(cells=120))],
      tiers=9, line_at=0.76, desc="What is left when the flame goes: a bed that is all heat and no light, breathing where air reaches it."),
    R("Ash Fall", "cinder", "char", 1502,
      [("dla", 1.0, dict(seeds=800, walkers=15000)), ("curl", 0.6, dict(scale=76))],
      tiers=7, line_at=0.84, mono=True,   # grey by nature: ash and soot have no second chemistry
      desc="Fine grey settling out of the air and building up wherever the wind lets it."),
    R("Soot Bloom", "cinder", "char", 1503,
      [("dla", 1.0, dict(seeds=900, walkers=22000, steps=54)), ("filaments", 0.55, dict(n=220, length=34)),
       ("worley", 0.45, dict(cells=150))],
      tiers=7, line_at=0.86, mono=True,   # grey by nature: ash and soot have no second chemistry
      desc="Carbon inception: dendrites branching out of nothing, the deadest material in the catalog."),
    R("Char Scale", "cinder", "char", 1504,
      [("spall", 1.0, dict(cells=100, lift=0.58)), ("anneal_crack", 0.6, dict(cells=110, width=1.8, gen=1))],
      tiers=7, line_at=0.82, desc="Burnt skin gone to alligator scale, every plate lifted a little at its edge."),
    R("Cinder Lattice", "cinder", "coal", 1505,
      [("percolate", 1.0, dict(cells=180, p=0.40)), ("eden", 0.6, dict(seeds=900, steps=12))],
      tiers=8, line_at=0.78, desc="The connected skeleton that survived — only the paths that stayed lit are still there."),
    R("Fly Ash", "cinder", "char", 1506,
      [("sparks", 1.0, dict(n=2400, life=48, g=0.25, drag=0.02, width=1.0)), ("dla", 0.6, dict(seeds=600))],
      mix="max", tiers=7, line_at=0.82, desc="Spent particles too light to fall, drifting until they cool to nothing."),
    R("Coke Cell", "cinder", "coal", 1507,
      [("worley", 1.0, dict(cells=104)), ("percolate", 0.6, dict(cells=170, p=0.42))],
      tiers=8, line_at=0.78, desc="Coal cooked without air until only the carbon cell wall is left standing."),
    R("Clinker Crust", "cinder", "char", 1508,
      [("spall", 1.0, dict(cells=76, lift=0.66)), ("percolate", 0.6, dict(cells=150, p=0.44))],
      tiers=7, line_at=0.84, desc="Fused ash that went hard and vitreous in the grate — the stuff you have to break out."),
    R("Ash Glaze", "cinder", "quench", 1509,
      [("anneal_crack", 1.0, dict(cells=130, width=1.3, gen=1)), ("dla", 0.55, dict(seeds=500)),
       ("worley", 0.45, dict(cells=120))],
      spec=dict(cell_jit=0.02),   # finest crack net in the set: cell jitter was
                                  # enough to move plates across a band edge
      tiers=9, line_at=0.74, desc="Wood ash melted onto the pot by its own kiln and crazed as it cooled."),
    R("Dying Coal", "cinder", "coal", 1510,
      [("percolate", 1.0, dict(cells=140, p=0.48)), ("curl", 0.6, dict(scale=72, steps=12))],
      tiers=9, line_at=0.80, desc="The last of the heat retreating into the middle of each lump."),
    R("Grey Front", "cinder", "char", 1511,
      [("eden", 1.0, dict(seeds=800, steps=16)), ("dla", 0.6, dict(seeds=500))],
      tiers=7, line_at=0.86, mono=True,   # grey by nature: ash and soot have no second chemistry
      desc="Ash advancing over ember — the moment a fire stops being orange."),
    R("Retained Heat", "cinder", "coal", 1512,
      [("worley", 1.0, dict(cells=110)), ("rt_fingers", 0.6, dict(n=100, gain=1.2))],
      tiers=9, line_at=0.80, desc="Cold on the outside, still dangerous in the core; convection barely moving above it."),
    R("Powder Burn", "cinder", "char", 1513,
      [("dla", 1.0, dict(seeds=1000, walkers=16000)), ("sparks", 0.6, dict(n=1600, life=22))],
      mix="max", tiers=7, line_at=0.82, mono=True,   # grey by nature: ash and soot have no second chemistry
      desc="Residue of a fast burn: scorched powder with a few grains that never went off."),
    R("Spall Field", "cinder", "char", 1514,
      [("spall", 1.0, dict(cells=92, lift=0.70)), ("worley", 0.5, dict(cells=140))],
      tiers=7, line_at=0.84, desc="Thermal shock popping flakes off the surface, each leaving a paler crater."),
    R("Cold Ash", "cinder", "char", 1515,
      [("dla", 1.0, dict(seeds=1400, walkers=13000)), ("worley", 0.55, dict(cells=150))],
      tiers=6, line_at=0.90, mono=True,   # grey by nature: ash and soot have no second chemistry
      desc="Completely out. Fine grey powder holding the shape of what it used to be."),
]


def _fid(name):
    return ID_PREFIX + name.lower().replace(" ", "_").replace("-", "_")


FLAMES = {_fid(r["name"]): r for r in _ROWS}


# ════════════════════════════════════════════════════════════════════════════
# RENDER CONTRACT
# ════════════════════════════════════════════════════════════════════════════

_LAB_OWN = {}


@lru_cache(maxsize=8)
def _heat_cached(fid):
    """The heat field + label field for a card, built from the card's OWN construction.

    SPB-105 / owner 2026-09-01: "STILL FUBAR'D ... TONS of repeating specs and
    paints just recolored bullshit" / "YOU BUILD THE FINISHES FIRST THEN SPEC TO
    THE FINISHES." The shelf had 63 stack recipes for 75 cards, all two- or
    three-way mixes of the same twelve primitives. flames_design_2026 names one
    construction per card from its physics (Darrieus-Landau is cellular, a
    Lichtenberg scar is a fractal tree, a weld pool's ripple record is crescents),
    a PLACES field gives it busy and calm zones, and FINE nests a second, smaller
    construction inside it. The recipe's old `build` is kept for provenance.

    Labels: only when the construction drew cells. An invented lattice fed to
    emit(cells=...) turns every f-only construction into the same mosaic (the
    cell_mean bug found on PARADIGM 2026-09-02); with cells=None emit chooses the
    tier per pixel and the construction's own detail survives.
    """
    from engine.expansions import flames_design_2026 as FDS
    from engine.expansions import nightshift_forms_2026 as NF
    from engine.paint_v2 import era_kit_2026 as EK

    d = FLAMES[fid]
    g = int(d.get("gen", GEN))
    form, params, kind = FDS.form_for(fid)
    fn = getattr(EK, form[3:]) if form.startswith("ek:") else getattr(NF, form)
    out = fn((g, g), d["seed"], **params)
    f, lab = out if isinstance(out, tuple) else (out, None)
    f = np.asarray(f, np.float32)
    f = NF.compose_form(f, d["seed"], kind=kind,
                        amount=float(d.get("detail", FDS.DETAIL.get(FDS.stem(fid), 0.40))), res=g)
    slow = np.asarray(kit.fbm((g, g), d["seed"] + 7, octaves=(5, 10, 20), weights=(1.0, 0.6, 0.35)), np.float32)
    slow = (slow - float(slow.min())) / max(float(slow.max() - slow.min()), 1e-6)
    mm = float(f.mean())
    f = np.clip(mm + (f - mm) * (0.50 + 1.0 * slow), 0, 1).astype(np.float32)
    fine = FDS.FINE.get(FDS.stem(fid))
    if fine is not None:
        form2, params2, w = fine
        fn2 = getattr(EK, form2[3:]) if form2.startswith("ek:") else getattr(NF, form2)
        out2 = fn2((g, g), d["seed"] + 41, **params2)
        f2 = np.asarray(out2[0] if isinstance(out2, tuple) else out2, np.float32)
        f2 = (f2 - float(f2.min())) / max(float(f2.max() - f2.min()), 1e-6)
        gy, gx = np.gradient(f)
        key = np.hypot(gx, gy)
        key = key / max(float(np.percentile(key, 98)), 1e-6)
        key = 0.45 + 0.55 * np.clip(key, 0, 1)
        f = np.clip(f * (1.0 - w) + f2 * w * key + f * w * (1.0 - key), 0, 1).astype(np.float32)
    _LAB_OWN[fid] = lab is not None
    if lab is not None:
        lab = np.asarray(lab)
    return kit.pct(f), lab

# A real fire bed is never one chemistry, and a single blackbody ladder is one
# hue family by construction — it walks red to orange to white and stops. Each
# chapter therefore has a pool of SECOND fuels that a minority of cells burn:
# salts in the kindling, slag chemistry in the melt, electrode metals in an arc.
# It is what a bonfire actually looks like, and it is where the chroma spread
# the owner keeps asking for comes from.
# What the fire is burning ON. Unburnt material keeps its own colour until the
# heat arrives, which is where a card's cold end gets a hue that a blackbody
# ladder simply cannot produce.
SUBSTRATE = {
    "ignition": (0.16, 0.19, 0.13),   # unburnt timber, still green-grey
    "flame":    (0.10, 0.11, 0.14),   # scorched ground under the burn
    "plasma":   (0.09, 0.12, 0.20),   # cold cathode steel, blue-grey
    "molten":   (0.20, 0.15, 0.11),   # firebrick and refractory
    "cinder":   (0.17, 0.17, 0.19),   # cold ash grey
}

# Every entry must carry a LINE in a different hue family from its host fuel —
# a warm mix fuel under a warm host (the first pass paired sodium-amber with
# wood, thermite with furnace) contributes no chroma at all and the cards
# measured 2 hue bins.
MIX_POOL = {
    "ignition": ("copper", "potassium", "cupric", "strontium"),
    "flame":    ("cupric", "copper", "barium", "lithium"),
    "plasma":   ("cupric", "barium", "potassium", "magnesium"),
    "molten":   ("copper", "quench", "cupric", "sulfur"),
    "cinder":   ("quench", "sulfur", "copper", "potassium"),
}


@lru_cache(maxsize=6)
def _art_cached(fid):
    """WORK-res paint. Colour comes from the fuel's real emission ladder."""
    d = FLAMES[fid]
    heat, lab = _heat_cached(fid)
    heat = kit.upscale(heat, WORK)
    lab_w = kit.upscale(lab, WORK) if lab is not None else None
    pool = MIX_POOL.get(d["chapter"], ())
    mix = d.get("mix_fuel", pool[d["seed"] % len(pool)] if pool else None)
    return kit.emit(heat, fuel=d["fuel"], tiers=d.get("tiers", 8), cells=lab_w,
                    jitter=d.get("jitter", 0.10), line_at=d.get("line_at", 0.72),
                    line_amt=d.get("line_amt", 0.85), seed=d["seed"],
                    mix_fuel=mix, mix_frac=d.get("mix_frac", 0.30),
                    tint=d.get("tint", 0.20),
                    substrate=d.get("substrate", SUBSTRATE.get(d["chapter"])),
                    sub_at=d.get("sub_at", 0.30))


# Per-finish spec composition (baked by _rebuild/rich_sweep.py flames)
_FFL_SPECKW = {
    "ffl_flashpoint": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "ffl_char_creep": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "ffl_tinder_bloom": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "ffl_match_head": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_smoulder_bed": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "ffl_fuse_line": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "ffl_kindle_lattice": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_spark_shower": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "ffl_ember_catch": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_pilot_ring": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "ffl_autoignition": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "ffl_firebrand_scatter": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "ffl_scorch_front": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "ffl_ignition_delay": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "ffl_touchpaper": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_diffusion_sheet": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "ffl_wrinkled_front": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "ffl_darrieus_cell": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "ffl_turbulent_braid": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "ffl_flamelet_storm": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "ffl_buoyant_fingers": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_shear_tongue": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "ffl_pool_puff": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "ffl_candle_cone": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_blowtorch": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "ffl_backdraft_wrinkle": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_fire_whirl_grain": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "ffl_laminar_ladder": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_crown_fire": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "ffl_stoichiometric_seam": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "ffl_arc_filament": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "ffl_ionised_braid": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "ffl_magnetised_jet": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "ffl_corona_grain": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_streamer_web": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "ffl_townsend_cascade": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "ffl_pinch_instability": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "ffl_cathode_spot": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "ffl_glow_discharge": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "ffl_lichtenberg_burn": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "ffl_plasma_sheath": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "ffl_spectral_line": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_electron_avalanche": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "ffl_tokamak_ripple": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "ffl_aurora_column": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "ffl_pahoehoe_skin": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_slag_crust": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_lava_cell": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "ffl_quench_craze": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "ffl_vitrified_glaze": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "ffl_weld_pool": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "ffl_molten_drip": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "ffl_crucible_skin": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "ffl_basalt_column": {"bands": "linear", "chips": 0.34, "edge_max": 0.14},
    "ffl_obsidian_chill": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "ffl_foundry_spatter": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "ffl_tuyere_glow": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_slumped_glass": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "ffl_magma_vesicle": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "ffl_ropy_flow": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_ember_bed": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_ash_fall": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_soot_bloom": {"bands": "quantile", "chips": 0.50, "edge_max": 0.07},
    "ffl_char_scale": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_cinder_lattice": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "ffl_fly_ash": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_coke_cell": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_clinker_crust": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "ffl_ash_glaze": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "ffl_dying_coal": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "ffl_grey_front": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "ffl_retained_heat": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "ffl_powder_burn": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "ffl_spall_field": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "ffl_cold_ash": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
}


def _mk(fid):
    d = FLAMES[fid]
    chap = dict(CHAPTER_SPEC[d["chapter"]])
    chap.update(d.get("spec", {}))

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
        art = _art_cached(fid)
        if cv2 is not None:
            art = cv2.resize(art, (fw, fh), interpolation=cv2.INTER_LINEAR)
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - kk) + art * kk, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        """Owner 2026-09-01: *"STILL FUBAR'D ... TONS of repeating specs."*

        This used to call kit.flame_spec with `chap` — the CHAPTER band list —
        so fifteen cards per chapter dealt an identical material set, with one
        per-card override in the whole shelf of seventy-five. The deck now comes
        from flames_decks_2026, authored per card off its own description, and
        the layout is composed against the RENDERED PAINT so material boundaries
        land on the artwork's own boundaries rather than on the heat field's.
        """
        from engine.paint_v2 import spec_story as ST
        from engine.expansions import flames_decks_2026 as FD

        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw) and cv2 is not None:
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        heat, lab = _heat_cached(fid)
        heat = kit.upscale(heat, fw)
        lab = kit.upscale(lab, fw) if lab is not None else None
        entry = FD.CARDS.get(fid)
        if entry is None:
            spec = kit.flame_spec(heat, lab, chap, fw, seed=d["seed"])
        else:
            cards, edge, kw = entry
            kw = dict(kw)
            kw.update(_FFL_SPECKW.get(fid, {}))
            art = _art_cached(fid)
            if cv2 is not None and art.shape[:2] != (fh, fw):
                art = cv2.resize(np.asarray(art, np.float32), (fw, fh),
                                 interpolation=cv2.INTER_LINEAR)
            spec = ST.compose(heat, cards, seed=d["seed"], res=fw, lab=lab,
                              edge=edge, art=art, **kw)
        mm = np.clip(m2, 0.0, 1.0)[..., None]
        return (np.asarray(spec, np.float32) * mm).clip(0, 255).astype(np.uint8)

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
    for fid in FLAMES:
        entry = _mk(fid)
        for reg in regs:
            try:
                reg[fid] = entry
            except Exception:
                pass
    return "%d finishes across %d chapters" % (len(FLAMES), len(CHAPTERS))
