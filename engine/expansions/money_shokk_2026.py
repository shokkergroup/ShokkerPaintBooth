# -*- coding: utf-8 -*-
"""💵 MONEY SHOKK — the 2026-08-31 total rework. 40 finishes about wealth.

Owner: *"Forty themed exotic engines about wealth in every form — mint foil,
vault steel, counterfeit gold, burn-a-stack green. Flexes harder than chrome.
Right now we are falling WELL SHORT of it doing what it's supposed to. Needs a
total rework."*

WHAT WAS THERE. Forty ids named `{colour} {creature}` — Canary Coffin, Magenta
Widow, Cerulean Cobra, Lime Scorpion, Hyperpink Torii, Seafoam Piranha — in four
seeded batches (`msh_`, `mshc_`, `msha_`, `mshx_`) off shared engines. A colour ×
creature grid with a money name on the box. Nothing in it was about money.

THE IDEA. Money is not a colour, it is a MANUFACTURING PROCESS, and it is the
most over-engineered printed object on earth. Almost all of that engineering is
anti-counterfeiting texture at exactly the scale a car body wants: intaglio you
can feel with a thumbnail, guilloche cut on a rose engine, microtext too small
to photocopy, a security thread windowed through the paper. So these 40 trace
the whole life of wealth, in five chapters of eight:

  🖨 MINT         how currency is manufactured
  🏦 VAULT        where it is kept
  💎 ASSET        wealth that was never cash
  🎭 COUNTERFEIT  wealth that is a lie — every card here is deliberately WRONG
                  in one material, which is the tell
  🔥 BURN         wealth destroyed, shredded, spent, inflated to nothing

"Flexes harder than chrome" is the brief, so the loud cards — chrome, mercury,
carrier, spectraflame — are all here, but EARNED: they are the foil stripe, the
bullion, the diamond table, the hologram patch. Never the whole panel.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

import engine.expansions.money_shokk_kit_2026 as MK
from engine.paint_v2 import spec_cards as SC

ID_PREFIX = "msk_"
GROUP = "💵 MONEY SHOKK"
GEN = 1024
WORK = 1152

CHAPTERS = {"mint": "🖨 MINT", "vault": "🏦 VAULT", "asset": "💎 ASSET",
            "fake": "🎭 COUNTERFEIT", "burn": "🔥 BURN"}
CHAP_WORD = {"mint": "Mint", "vault": "Vault", "asset": "Asset",
             "fake": "Counterfeit", "burn": "Burn"}

_STRUCTS = {
    "guilloche": lambda sh, sd, k: (MK.guilloche(sh, sd, **k), None),
    "intaglio":  lambda sh, sd, k: (MK.intaglio(sh, sd, **k), None),
    "microtext": lambda sh, sd, k: (MK.microtext(sh, sd, **k), None),
    "threads":   lambda sh, sd, k: (MK.threads(sh, sd, **k), None),
    "moire":     lambda sh, sd, k: (MK.moire(sh, sd, **k), None),
    "knurl":     lambda sh, sd, k: (MK.knurl(sh, sd, **k), None),
    "facets":    lambda sh, sd, k: MK.facets(sh, sd, **k),
    "bricks":    lambda sh, sd, k: (MK.bricks(sh, sd, **k), None),
    "shred":     lambda sh, sd, k: (MK.shred(sh, sd, **k), None),
    "char":      lambda sh, sd, k: (MK.char(sh, sd, **k), None),
    "watermark": lambda sh, sd, k: (MK.watermark(sh, sd, **k), None),
    "craters":   lambda sh, sd, k: (MK.craters(sh, sd, **k), None),
    "cells":     lambda sh, sd, k: MK.worley(sh, sd, **k),
    "curl":      lambda sh, sd, k: (MK.curl(sh, sd, **k), None),
    "filaments": lambda sh, sd, k: (MK.filaments(sh, sd, **k), None),
    "dendrite":  lambda sh, sd, k: (MK.dla(sh, sd, **k), None),
    "percolate": lambda sh, sd, k: MK.percolate(sh, sd, **k),
    "spall":     lambda sh, sd, k: MK.spall(sh, sd, **k),
    "crack":     lambda sh, sd, k: MK.anneal_crack(sh, sd, **k),
    "sparks":    lambda sh, sd, k: (MK.sparks(sh, sd, **k), None),
    "wrinkle":   lambda sh, sd, k: (MK.wrinkle(sh, sd, **k), None),
    "eden":      lambda sh, sd, k: (MK.eden(sh, sd, **k), None),
}

# Palettes taken from the actual objects, not from "money is green". A US note
# is grey-green; a euro is brick and slate; a vault is oiled steel; bullion is
# three different yellows depending on whether it is cast, rolled or leafed.
P = {
    "greenback":  ((0.09, 0.13, 0.10), (0.22, 0.34, 0.26), (0.45, 0.58, 0.46), (0.76, 0.84, 0.74)),
    "rag_paper":  ((0.28, 0.27, 0.24), (0.55, 0.53, 0.47), (0.78, 0.76, 0.69), (0.95, 0.94, 0.89)),
    "euro_brick": ((0.14, 0.08, 0.09), (0.40, 0.22, 0.22), (0.66, 0.44, 0.40), (0.88, 0.72, 0.66)),
    "sterling":   ((0.10, 0.11, 0.16), (0.26, 0.30, 0.44), (0.48, 0.54, 0.70), (0.76, 0.80, 0.90)),
    "ovi_shift":  ((0.08, 0.12, 0.14), (0.16, 0.36, 0.34), (0.36, 0.30, 0.56), (0.72, 0.62, 0.86)),
    "ink_black":  ((0.04, 0.04, 0.05), (0.14, 0.14, 0.17), (0.30, 0.30, 0.35), (0.56, 0.56, 0.62)),
    "vault_steel":((0.10, 0.11, 0.12), (0.26, 0.28, 0.30), (0.46, 0.49, 0.52), (0.72, 0.75, 0.78)),
    "safe_green": ((0.06, 0.10, 0.09), (0.16, 0.26, 0.23), (0.32, 0.46, 0.41), (0.58, 0.72, 0.66)),
    "brass":      ((0.16, 0.11, 0.04), (0.44, 0.32, 0.10), (0.70, 0.55, 0.22), (0.92, 0.82, 0.50)),
    "oxblood":    ((0.11, 0.04, 0.05), (0.32, 0.10, 0.12), (0.54, 0.22, 0.24), (0.78, 0.46, 0.44)),
    "bullion":    ((0.20, 0.13, 0.02), (0.52, 0.37, 0.06), (0.80, 0.62, 0.18), (0.98, 0.88, 0.52)),
    "leaf_gold":  ((0.26, 0.18, 0.04), (0.60, 0.45, 0.12), (0.86, 0.72, 0.30), (1.00, 0.94, 0.68)),
    "platinum":   ((0.20, 0.21, 0.23), (0.46, 0.48, 0.52), (0.72, 0.74, 0.78), (0.95, 0.96, 0.98)),
    "diamond":    ((0.16, 0.19, 0.23), (0.44, 0.52, 0.60), (0.72, 0.80, 0.88), (0.97, 0.99, 1.00)),
    "deed":       ((0.24, 0.21, 0.15), (0.52, 0.47, 0.35), (0.76, 0.71, 0.57), (0.94, 0.91, 0.80)),
    "watchsteel": ((0.12, 0.13, 0.14), (0.32, 0.34, 0.36), (0.56, 0.58, 0.61), (0.84, 0.86, 0.89)),
    "plated":     ((0.18, 0.15, 0.08), (0.44, 0.38, 0.18), (0.66, 0.60, 0.34), (0.86, 0.82, 0.58)),
    "bleach":     ((0.30, 0.30, 0.28), (0.58, 0.58, 0.55), (0.80, 0.80, 0.77), (0.96, 0.96, 0.94)),
    "uv_dead":    ((0.10, 0.10, 0.13), (0.24, 0.24, 0.30), (0.42, 0.42, 0.50), (0.66, 0.66, 0.74)),
    "wrong_gold": ((0.20, 0.16, 0.06), (0.48, 0.40, 0.14), (0.72, 0.63, 0.26), (0.92, 0.86, 0.52)),
    "launder":    ((0.10, 0.14, 0.16), (0.24, 0.34, 0.38), (0.44, 0.56, 0.60), (0.72, 0.82, 0.86)),
    "scorch":     ((0.06, 0.04, 0.03), (0.24, 0.12, 0.05), (0.50, 0.28, 0.10), (0.80, 0.56, 0.24)),
    "ash_note":   ((0.08, 0.08, 0.08), (0.22, 0.22, 0.22), (0.42, 0.42, 0.42), (0.68, 0.68, 0.68)),
    "confetti":   ((0.12, 0.12, 0.14), (0.36, 0.30, 0.20), (0.62, 0.56, 0.36), (0.88, 0.84, 0.62)),
    "crash_red":  ((0.10, 0.04, 0.05), (0.36, 0.08, 0.10), (0.62, 0.18, 0.18), (0.86, 0.42, 0.36)),
    # thrown confetti is every note in the drawer at once, not one shredded bill
    "shred_mix":  ((0.10, 0.14, 0.22), (0.52, 0.16, 0.20), (0.30, 0.56, 0.34), (0.94, 0.82, 0.36)),
    "tape_white": ((0.22, 0.22, 0.23), (0.50, 0.50, 0.52), (0.75, 0.75, 0.78), (0.95, 0.95, 0.97)),
}

# ── material stories ────────────────────────────────────────────────────────
# A note is RAG PAPER with RAISED INK on it and one metallic stripe. That is the
# whole trick: a matte dielectric ground, a gloss ink relief, one loud card.
B_NOTE    = (("clear_matte", 0.30), ("powder", 0.52), ("gloss_carbon", 0.70),
             ("pearl", 0.85), ("candy", 0.95), ("spectraflame", 1.01))
B_FOIL    = (("powder", 0.26), ("eggshell", 0.48), ("gloss_carbon", 0.66),
             ("pearl", 0.82), ("spectraflame", 0.94), ("chrome", 1.01))
B_STEEL   = (("bead_blast", 0.24), ("satin_carbon", 0.46), ("brushed_ti", 0.64),
             ("galvanized", 0.79), ("gunmetal", 0.92), ("chrome", 1.01))
B_GOLD    = (("ceramic_matte", 0.24), ("patina", 0.46), ("metallic", 0.65),
             ("candy", 0.82), ("candy_chrome", 0.94), ("mercury", 1.01))
B_STONE   = (("frozen_film", 0.24), ("sea_glass", 0.46), ("milk_glass", 0.64),
             ("liquid_glaze", 0.80), ("wet", 0.92), ("chrome", 1.01))
# COUNTERFEIT decks always pair a convincing card with a WRONG one — the plated
# brass under the gold, the dead flat where the ink should sit up.
B_FAKE_G  = (("void", 0.28), ("clear_matte", 0.50), ("galvanized", 0.68),
             ("brushed_ti", 0.84), ("candy", 0.95), ("antique_chrome", 1.01))
B_FAKE_P  = (("flat_black", 0.28), ("vinyl", 0.50), ("satin", 0.68),
             ("semi_gloss", 0.84), ("anodized", 0.95), ("satin_chrome", 1.01))
B_BURN    = (("void", 0.30), ("flat_black", 0.52), ("patina", 0.70),
             ("satin_carbon", 0.85), ("carrier_mid", 0.95), ("carrier_high", 1.01))
B_ASH     = (("void", 0.32), ("frozen_metal", 0.54), ("satin_carbon", 0.72),
             ("gloss_carbon", 0.86), ("dark_chrome", 0.96), ("mercury", 1.01))


def R(name, chapter, palette, bands, seed, stack, mix="sum", edge="chrome",
      r_spread=26.0, gamma=1.0, dither=0.15, desc=""):
    return dict(name=name, chapter=chapter, palette=palette, bands=bands,
                seed=seed, stack=stack, mix=mix, edge=edge, r_spread=r_spread,
                gamma=gamma, dither=dither, desc=desc)


_ROWS = [
    # ────────────────────────── 🖨 MINT (8) ────────────────────────────────
    R("Intaglio Plate", "mint", "greenback", B_NOTE, 7101,
      [("intaglio", 1.0, dict(lpi=96, angle=24, cross=0.45)),
       ("guilloche", 0.55, dict(period=88, ring=11))],
      desc="Line engraving with the ink standing proud of the paper — the one security feature you check with a thumbnail."),
    R("Rose Engine", "mint", "rag_paper", B_NOTE, 7102,
      [("guilloche", 1.0, dict(period=86, ring=11, teeth=(5, 9, 13))),
       ("intaglio", 0.45, dict(lpi=132, angle=71))],
      desc="A lathe that cuts interfering rosettes no hand can redraw. The machine is called a rose engine; this is its output."),
    R("Security Thread", "mint", "sterling", B_FOIL, 7103,
      [("threads", 1.0, dict(stripes=15, window=0.44)), ("watermark", 0.6, dict(laid=190))],
      desc="A metal ribbon buried in the pulp, surfacing through windows, with the mill's loose fibres scattered around it."),
    R("Microtext Field", "mint", "ink_black", B_NOTE, 7104,
      [("microtext", 1.0, dict(rows=130, density=0.66)), ("guilloche", 0.4, dict(period=120, ring=16))],
      desc="Lettering below the resolution of any copier, woven into a field of language you can almost read."),
    R("Optically Variable", "mint", "ovi_shift", B_FOIL, 7105,
      [("facets", 1.0, dict(stones=230, table=0.30)), ("moire", 0.5, dict(lpi=190))],
      desc="Ink with interference flakes in it — the denomination that changes colour when the car turns."),
    R("Watermark Pulp", "mint", "rag_paper", B_NOTE, 7106,
      [("watermark", 1.0, dict(scale=9, depth=0.80, laid=200)),
       ("filaments", 1.0, dict(n=2800, length=12, wander=0.85)),
       ("microtext", 0.5, dict(rows=124, density=0.5, height=6))],
      desc="Not printed at all — the dandy roll pressed the pulp thinner, and the portrait is a map of paper thickness."),
    R("Denomination Foil", "mint", "euro_brick", B_FOIL, 7107,
      [("bricks", 1.0, dict(rows=44, cols=8, bind=0.20, offset=0.18)),
       ("guilloche", 0.5, dict(period=78, ring=10))],
      desc="The holographic patch, stamped in register and struck through with rose-engine work."),
    R("Fresh Sheet", "mint", "greenback", B_NOTE, 7108,
      [("bricks", 1.0, dict(rows=88, cols=12, bind=0.10, lean=0.2, offset=0.0)),
       ("intaglio", 0.6, dict(lpi=112, angle=52, cross=0.3))],
      desc="Thirty-two notes to a sheet, uncut, before the guillotine ever touches them."),

    # ────────────────────────── 🏦 VAULT (8) ───────────────────────────────
    R("Hardplate", "vault", "vault_steel", B_STEEL, 7201,
      [("knurl", 1.0, dict(pitch=22, angle=31)), ("cells", 0.55, dict(cells=150))],
      desc="Manganese hardplate — the layer a drill bit dies in. Cross-cut so the carbide skates."),
    R("Timelock", "vault", "brass", B_STEEL, 7202,
      [("facets", 1.0, dict(stones=150, table=0.36)), ("knurl", 0.6, dict(pitch=30, angle=12))],
      desc="Clockwork that refuses to open before morning, in polished brass and jewelled bearings."),
    R("Deposit Brass", "vault", "brass", B_GOLD, 7203,
      [("bricks", 1.0, dict(rows=58, cols=30, bind=0.30, offset=0.0, lean=0.0)),
       ("craters", 0.55, dict(n=2400, rmax=5.0, rim=0.8)),
       ("facets", 0.35, dict(stones=170, table=0.4))],
      desc="A wall of safe-deposit doors, every one with a name on it and two locks."),
    R("Cage Mesh", "vault", "vault_steel", B_STEEL, 7204,
      [("knurl", 1.0, dict(pitch=15, angle=45, relief=1.5, wobble=0.12)),
       ("knurl", 0.6, dict(pitch=44, angle=45, relief=1.1, wobble=0.08)),
       ("filaments", 0.22, dict(n=1100, length=14))],
      desc="Expanded steel between you and the money, close enough to see through and not to reach through."),
    R("Bullion Stack", "vault", "bullion", B_GOLD, 7205,
      [("bricks", 1.0, dict(rows=70, cols=10, bind=0.16, lean=0.9)), ("cells", 0.5, dict(cells=160))],
      desc="Four hundred troy ounces a bar, stacked five high, each one softer than you expect."),
    R("Tamper Seal", "vault", "oxblood", B_FOIL, 7206,
      [("crack", 1.0, dict(cells=110, width=2.0, gen=1)), ("microtext", 0.6, dict(rows=100))],
      desc="A seal designed to destroy itself: void lettering that surfaces the instant anyone lifts an edge."),
    R("Armoured Glass", "vault", "diamond", B_STONE, 7207,
      [("crack", 1.0, dict(cells=76, width=3.0)), ("facets", 0.6, dict(stones=150))],
      desc="Laminate that stops the round and keeps the spall, cracked into a web that holds together."),
    R("Night Deposit", "vault", "safe_green", B_STEEL, 7208,
      [("knurl", 1.0, dict(pitch=26, angle=58)), ("percolate", 0.55, dict(cells=170))],
      desc="The chute in the wall, painted the green every bank painted everything until 1979."),

    # ────────────────────────── 💎 ASSET (8) ───────────────────────────────
    R("Bullion Pour", "asset", "bullion", B_GOLD, 7301,
      [("curl", 1.0, dict(scale=46, steps=20)), ("cells", 0.6, dict(cells=158))],
      desc="Molten gold entering a mould — the moment before it becomes a number in a ledger."),
    R("Brilliant Cut", "asset", "diamond", B_STONE, 7302,
      [("facets", 1.0, dict(stones=210, table=0.32, brilliance=1.8)), ("sparks", 0.45, dict(n=2600, life=22))],
      desc="Fifty-seven facets arranged so light that goes in has to come back at you."),
    R("Leaf Gilding", "asset", "leaf_gold", B_GOLD, 7303,
      [("wrinkle", 1.0, dict(k=1.2, steps=16, scale=140)), ("spall", 0.6, dict(cells=120, lift=0.5))],
      desc="Gold beaten to a fifth of a micron, laid down in leaves that never quite meet."),
    R("Platinum Ingot", "asset", "platinum", B_STEEL, 7304,
      [("bricks", 1.0, dict(rows=66, cols=9, bind=0.22)), ("knurl", 0.5, dict(pitch=28, angle=8))],
      desc="Denser than gold, rarer than gold, and it does not care what you think of it."),
    R("Bearer Deed", "asset", "deed", B_NOTE, 7305,
      [("guilloche", 1.0, dict(period=112, ring=15, teeth=(4, 7, 10))),
       ("filaments", 0.5, dict(n=1900, length=14, wander=0.75))],
      desc="Whoever holds the paper owns the thing. No name on it anywhere, which is exactly the point."),
    R("Share Certificate", "asset", "deed", B_NOTE, 7306,
      [("intaglio", 1.0, dict(lpi=104, angle=14, cross=0.55)), ("microtext", 0.55, dict(rows=90))],
      desc="An engraved allegory of Industry, a serial number, and a claim on something you will never see."),
    R("Watch Movement", "asset", "watchsteel", B_STEEL, 7307,
      [("guilloche", 1.0, dict(period=64, ring=9, teeth=(7, 12))), ("facets", 0.55, dict(stones=190))],
      desc="Côtes de Genève on a bridge nobody will ever look at, because it should be right anyway."),
    R("Title Vellum", "asset", "rag_paper", B_NOTE, 7308,
      [("intaglio", 1.0, dict(lpi=140, angle=63, cross=0.35)),
       ("watermark", 0.62, dict(scale=6, depth=0.72, laid=160))],
      desc="Calfskin, a wax seal and a hand that has been dust for two centuries. Still enforceable."),

    # ─────────────────────── 🎭 COUNTERFEIT (8) ────────────────────────────
    R("Rescreened", "fake", "bleach", B_FAKE_P, 7401,
      [("moire", 1.0, dict(lpi=230, beat=1.05, angle=9, depth=0.42)),
       ("intaglio", 0.5, dict(lpi=112, angle=33))],
      desc="Photographed and reprinted. The scanner's grid beat against the engraving and left its confession."),
    R("Bleached Note", "fake", "bleach", B_FAKE_P, 7402,
      [("percolate", 1.0, dict(cells=176, p=0.44)), ("watermark", 0.6, dict(depth=0.35))],
      desc="A one washed to blank and reprinted as a hundred. The paper is genuine, which is the clever part."),
    R("Plated Brass", "fake", "plated", B_FAKE_G, 7403,
      [("spall", 1.0, dict(cells=118, lift=0.62)), ("knurl", 0.55, dict(pitch=30))],
      desc="Two microns of gold over brass, and it wears through exactly where a thumb would rest."),
    R("Salted Bar", "fake", "wrong_gold", B_FAKE_G, 7404,
      [("bricks", 1.0, dict(rows=76, cols=11, bind=0.18)), ("crack", 0.6, dict(cells=94, gen=1))],
      desc="Right weight, right stamp, tungsten core. It only fails the one test nobody runs."),
    R("UV Dead", "fake", "uv_dead", B_FAKE_P, 7405,
      [("microtext", 1.0, dict(rows=120, density=0.5)), ("threads", 0.5, dict(stripes=11, fibres=900))],
      desc="Perfect in daylight. Under the lamp at the till, the fibres that should light up stay black."),
    R("Superdollar", "fake", "greenback", B_FAKE_G, 7406,
      [("intaglio", 1.0, dict(lpi=118, angle=26, cross=0.4)), ("guilloche", 0.5, dict(period=92, ring=12))],
      desc="State-made, intaglio-printed, better paper than the original. The engraving is only wrong in one line."),
    R("Laundered", "fake", "launder", B_FAKE_P, 7407,
      [("curl", 1.0, dict(scale=52, steps=18)), ("moire", 0.5, dict(lpi=200, beat=1.03))],
      desc="Through a restaurant, a car wash and a shell in Nicosia, and it comes out the other side clean."),
    R("Wrong Watermark", "fake", "bleach", B_FAKE_P, 7408,
      [("moire", 1.0, dict(lpi=150, beat=1.04, depth=0.40)),
       ("watermark", 0.7, dict(scale=11, depth=0.8, laid=150))],
      desc="Printed on, not pressed in. It reads correctly flat and vanishes the moment you hold it up."),

    # ────────────────────────── 🔥 BURN (8) ────────────────────────────────
    R("Burn A Stack", "burn", "scorch", B_BURN, 7501,
      [("char", 1.0, dict(fronts=8, bite=1.4, ember=0.3)), ("bricks", 0.55, dict(rows=84, cols=12))],
      desc="A strapped brick going up all at once — the scorch corona running ahead of the black."),
    R("Cross Cut", "burn", "confetti", B_ASH, 7502,
      [("shred", 1.0, dict(strips=165, curl_amt=28)), ("cells", 0.5, dict(cells=170))],
      desc="Security-grade shredding: 2mm strips, cross-cut, unreconstructable and oddly beautiful."),
    R("Confetti Drop", "burn", "shred_mix", B_ASH, 7503,
      [("shred", 1.0, dict(strips=210, curl_amt=40, gap=0.42)), ("sparks", 0.5, dict(n=2400, life=30))],
      desc="A year's bonus turned into ticker tape and thrown off a balcony."),
    R("Ink Spill", "burn", "ink_black", B_ASH, 7504,
      [("curl", 1.0, dict(scale=42, steps=22)), ("dendrite", 0.55, dict(seeds=800))],
      desc="The dye pack goes off in the bag and marks every note, and the money is still money and worth nothing."),
    R("Ticker Crash", "burn", "crash_red", B_BURN, 7505,
      [("intaglio", 1.0, dict(lpi=124, angle=88, warp=44)), ("shred", 0.5, dict(strips=140))],
      desc="Tape running faster than anyone can read it, all of it in one direction."),
    R("Hyperinflation", "burn", "tape_white", B_ASH, 7506,
      [("microtext", 1.0, dict(rows=150, density=0.72, height=6)), ("bricks", 0.5, dict(rows=40, cols=9))],
      desc="A hundred trillion of something, printed on one side because the second pass costs more than the note."),
    R("Bond Ash", "burn", "ash_note", B_ASH, 7507,
      [("dendrite", 1.0, dict(seeds=1200)), ("char", 0.6, dict(fronts=5, ember=0.15))],
      desc="Cold ash holding the shape of the certificate right up until the moment you touch it."),
    R("Torn In Half", "burn", "greenback", B_BURN, 7508,
      [("crack", 1.0, dict(cells=112, width=3.4)),
       ("intaglio", 0.75, dict(lpi=116, angle=41, cross=0.35))], dither=0.22,
      desc="Half a note is worth nothing, so tearing one is the purest way to spend money on a gesture."),
]


def title(fid):
    d = MONEY[fid]
    return "%s: %s" % (CHAP_WORD[d["chapter"]], d["name"])


def _fid(name):
    return ID_PREFIX + name.lower().replace(" ", "_").replace("-", "_")


MONEY = {_fid(r["name"]): r for r in _ROWS}


def build(stack, shape, seed, mix="sum"):
    acc, lab, wsum = None, None, 0.0
    for i, (name, wgt, kw) in enumerate(stack):
        f, l = _STRUCTS[name](shape, seed + 101 * i, dict(kw))
        if l is not None and lab is None:
            lab = l
        if acc is None:
            acc, wsum = f * float(wgt), float(wgt)
        elif mix == "max":
            acc = np.maximum(acc, f * float(wgt))
        else:
            acc = acc + f * float(wgt)
            wsum += float(wgt)
    if mix == "sum" and wsum > 0:
        acc = acc / wsum
    return MK.pct(acc), lab


@lru_cache(maxsize=8)
def _field(fid):
    d = MONEY[fid]
    f, lab = build(d["stack"], (GEN, GEN), d["seed"], mix=d.get("mix", "sum"))
    if lab is None:
        _dd, lab = MK.worley((GEN, GEN), d["seed"] + 7, cells=168)
    return f, lab


@lru_cache(maxsize=6)
def _art(fid):
    d = MONEY[fid]
    f, lab = _field(fid)
    f = MK.upscale(f, WORK)
    lab = MK.upscale(lab, WORK)
    pal = np.asarray(P[d["palette"]], np.float32)
    fc = MK.cell_mean(f, lab)
    t = np.clip(fc ** float(d.get("gamma", 1.0)), 0, 1)
    idx = np.clip((t * (len(pal) - 1)).astype(np.int32), 0, len(pal) - 2)
    frac = np.clip(t * (len(pal) - 1) - idx, 0, 1)[..., None]
    art = pal[idx] * (1.0 - frac) + pal[idx + 1] * frac
    art = art * (0.72 + 0.56 * f)[..., None]
    if cv2 is not None:
        hsv = cv2.cvtColor(np.clip(art, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
        hsv[..., 0] = np.mod(hsv[..., 0] + (MK._h1(lab, 97) - 0.5) * 14.0, 360.0)
        hsv[..., 1] = np.clip(hsv[..., 1] * (0.88 + 0.24 * MK._h1(lab, 149)), 0, 1)
        art = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        g = MK.fbm((WORK, WORK), d["seed"] + 3, octaves=(128, 256, 512),
                   weights=(0.6, 1.0, 0.8)) - 0.5
        art = art * (1.0 + g * 0.22)[..., None]
    return np.clip(art, 0, 1).astype(np.float32)


def _spec_at(fid, res):
    d = MONEY[fid]
    f, lab = _field(fid)
    f = MK.upscale(f, res)
    lab = MK.upscale(lab, res)
    fc = MK.cell_mean(f, lab)
    # per-cell offset so six bands over a smooth cell-mean cannot merge whole
    # runs of neighbouring cells into one 80px slab (PARADIGM's SPECBAND lesson)
    fc = np.clip(fc + (MK._h1(lab, 61) - 0.5) * float(d.get("dither", 0.15)), 0.0, 1.0)
    bands_ = d["bands"]
    edges = np.asarray([u for _n, u in bands_], np.float32)
    deck = np.asarray([SC.CARDS[n] for n, _u in bands_], np.float32)
    qs = np.maximum.accumulate(np.asarray(
        np.percentile(fc[::4, ::4], np.clip(edges * 100.0, 0, 100)), np.float32))
    bi = np.clip(np.searchsorted(qs, fc.ravel(), side="left"), 0, len(bands_) - 1)
    out = deck[bi].reshape(res, res, 3)
    if cv2 is not None:
        hs = max(512, res // 2)
        hh = cv2.resize(f, (hs, hs), interpolation=cv2.INTER_AREA) if hs != res else f
        gy, gx = np.gradient(cv2.GaussianBlur(hh, (0, 0), 1.2))
        grad = np.hypot(gx, gy)
        gsub = grad[::2, ::2].ravel()
        lip = (grad > float(np.percentile(gsub, 97.6))).astype(np.float32)
        for q in (99.0, 99.5):
            if lip.mean() <= 0.06:
                break
            lip = (grad > float(np.percentile(gsub, q))).astype(np.float32)
        k = int(max(2, res / 700.0 * hs / float(res)))
        lip = cv2.dilate(lip, np.ones((k, k), np.float32))
        if hs != res:
            lip = cv2.resize(lip, (res, res), interpolation=cv2.INTER_NEAREST)
        out[lip > 0] = SC.card(d.get("edge", "chrome"))
    frac2 = float(d.get("r_spread", 26.0)) / 255.0
    out[..., 1] = np.clip(out[..., 1] * (1.0 + (MK._h1(lab, 173) - 0.5) * 2.0 * frac2), 0, 255)
    out[..., 0] = np.clip(out[..., 0] * (0.94 + 0.12 * MK._h1(lab, 211)), 0, 255)
    off = max(2, res // 420)
    out[..., 2] = np.roll(np.roll(out[..., 2], off, 0), -off, 1)
    return SC.iron_safe(out)


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
    for fid in MONEY:
        entry = _mk(fid)
        for reg in regs:
            try:
                reg[fid] = entry
            except Exception:
                pass
    return "%d finishes across %d chapters" % (len(MONEY), len(CHAPTERS))
