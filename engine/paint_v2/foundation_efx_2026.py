# -*- coding: utf-8 -*-
"""FOUNDATION EFX — textured foundations that carry paint AND spec.

Owner 2026-09-03 (FOUNDATION ONE, Phase B): three foundation categories became ONE
category with two shelves. The flat BASES shelf has no colour of its own. THIS shelf
is the other half: foundations with texture — glitter, rust, chalked paint, hammered
metal, holographic foil — that carry their own paint and spec. Owner: "The EFX ones
can have paint because we can always use source paint, solid color, etc."

THE MECHANISM (the same construction-first pipeline as DARK CITY, adapted to a base
that must work on ANY colour the painter picks)
------------------------------------------------------------------------------------
1. A FIELD.  Each row names its own construction (flames kit / nightshift forms /
   era kit) plus a FINE construction nested inside it (structure inside structure)
   and a grain kind. Nothing here is a re-seed of another row: 43 rows, 43 forms or
   form/parameter families, checked by `check()`.
2. A TEXTURE on the painter's colour.  The field drives a value multiplier (`tex`),
   optional STAINS (rust, gold, zinc, chalk — the material's own colour, laid where
   the field says), an optional thin-FILM colour (interference physics from
   engine/color_science.py, for holographic / heat-tint / nacre), and optional
   GLINT (discrete sparkle chips). The user's paint is the ground everywhere the
   stain is not; source paint, solid colour and gradients all work on top.
   Order: film -> stains -> value texture -> glint, so a rust patch is still lit by
   the dents it sits in (round 1 flattened every stain to a silhouette).
3. A SPEC dealt on the same field.  spec_story.compose() deals this row's own deck of
   Spec Guide cards onto the field's level sets, with the micro amplitude driven by
   the rendered texture, so FOLLOW/SCALE hold by construction. Per-row composition
   settings (`SPECKW`) are MEASURED by _efx_work/sweep.py against the FINISH LAW's
   own axis functions: the richest spec among the settings that still follow.

Registry contract (engine/base_registry_data.py merges FOUNDATION_EFX):
    paint_fn(paint, shape, mask, seed, pm, bb) -> HxWx3 float32 in [0,1]
    base_spec_fn(shape, seed, sm, base_m, base_r) -> (M, R, CC) float32 0-255

`efx_holographic_drift` is LOCKED (owner: "stay the same for sure") and is never
touched by this module; `efx_frost_fractal` / `efx_frost_mercury_duo` are the
owner's other keepers and are left on their original renderers too.
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
from engine.paint_v2 import spec_cards as SC
from engine.paint_v2 import spec_story as ST
from engine.color_science import interference_palette

GROUP = "Foundation EFX"
GEN = 1024          # fields are generated here ...
WORK = 1152         # ... textured here, and resized to the canvas on demand
LOCKED = ("efx_holographic_drift",)
KEPT = ("efx_holographic_drift", "efx_frost_fractal", "efx_frost_mercury_duo")


def E(fid, name, form, params, deck, edge, seed, *, paint, fine=None, grain="grain",
      detail=0.42, bands="quantile", chips=0.34, spec_grain=0.55, edge_max=0.08,
      places=1.0, use_lab=True, region_blur=0.0, paint_micro=0.0, cell_tone=0.0, desc="", swatch="#888888", spec_kw=None):
    """One textured foundation. `paint` is the texture recipe:
        tex     value modulation amount (0 = none), gamma shapes the field first
        stain   dict(color, at='high'|'low', cover=(lo, hi), a)  — material colour
        stain2  a second stain (pits, bare metal, remnants)
        film    dict(orders, quantize, a, brightness) — thin-film interference colour
        glint   dict(kind='spark'|'flake', amt, color) — sparkle keyed to the form's edges
                or dict(src='field', cover=(lo, hi), amt, color) — the field's own chips
    """
    return dict(fid=fid, name=name, form=form, params=params, deck=tuple(deck), edge=edge,
                seed=int(seed), paint=paint, fine=fine, grain=grain, detail=detail,
                bands=bands, chips=chips, spec_grain=spec_grain, edge_max=edge_max,
                places=float(places), use_lab=bool(use_lab), region_blur=float(region_blur),
                paint_micro=float(paint_micro), cell_tone=float(cell_tone), desc=desc, swatch=swatch, spec_kw=spec_kw or {})


# ═══════════════════════════════════════════════════════════════════════════════
# THE SHELF — 43 rows. Order = picker order (reworks, holographic, flake, weathered,
# shop metal, coatings, nature). Every row owns its construction AND its deck.
# Feature sizes are chosen for the 8-32px window at 2048 (fields generate at 1024, so
# a 10px cell here is a 20px cell on the car).
# ═══════════════════════════════════════════════════════════════════════════════
ROWS = [
    # ── reworked concepts (ids kept so saved projects resolve) ──────────────────
    E("efx_cathedral_veil", "Cathedral Veil", "basalt", dict(cells=150, relax=3, wall=0.20),
      ("gloss_carbon", "sea_glass", "milk_glass", "candy", "liquid_glaze", "mirror_deep"), "dark_chrome", 9101,
      paint=dict(tex=0.45, gamma=1.0, stain=dict(color=(0.10, 0.10, 0.11), at="low", cover=(0.0, 0.10), a=0.85)),
      fine=("fk:anneal_crack", dict(cells=140, width=1.2, gen=1), 0.35), grain="crackle",
      desc="Leaded glass panes in your colour, the came laid in dark chrome and every pane crazed.", swatch="#7fb3c9"),
    E("efx_kintsugi_bloom", "Kintsugi Bloom", "fk:anneal_crack", dict(cells=36, width=3.2, gen=1),
      ("ceramic_matte", "matte", "eggshell", "satin", "spectraflame", "candy_chrome"), "chrome", 9102,
      paint=dict(tex=0.18, stain=dict(color=(0.86, 0.62, 0.20), at="high", cover=(0.84, 0.96), a=0.95)),
      fine=("ek:crinkle", dict(scale=380, sharp=1.8, folds=1), 0.22), grain="stipple",
      desc="A matte body broken and mended in gold — the seams are the only metal on the car.", swatch="#c9a24a"),
    E("efx_quicksilver_pool", "Quicksilver Pool", "metaball", dict(blobs=5200, radius=0.0054, thresh=0.44),
      ("matte", "satin", "gunmetal", "mirror_deep", "mercury"), "mercury", 9103,
      paint=dict(tex=0.30, stain=dict(color=(0.86, 0.88, 0.90), at="high", cover=(0.60, 0.80), a=0.92)),
      fine=("caustics", dict(scale=11.0, octaves=3, gain=3.2), 0.45), grain="grain", detail=0.50,
      desc="Mercury pooled on matte paint — liquid mirror islands with caustic light inside them.", swatch="#c9ced4"),
    E("efx_volcanic_obsidian", "Volcanic Obsidian", "shatter", dict(impacts=14, radials=30, rings=10, jitter=0.30),
      ("void", "flat_black", "gloss_carbon", "liquid_glaze", "wet", "dark_chrome"), "liquid_glaze", 9104,
      paint=dict(tex=0.55, gamma=1.6, stain=dict(color=(0.05, 0.05, 0.07), at="low", cover=(0.0, 0.50), a=0.60)),
      fine=("fk:spall", dict(cells=120, lift=0.6), 0.30), grain="ridge", bands="linear",
      desc="Conchoidal fracture — glassy shells stepping down into dead-black rock.", swatch="#2a1e26"),
    E("efx_aurora_skin", "Aurora Skin", "fk:curl", dict(scale=260, steps=60),
      ("satin", "pearl", "candy", "spectraflame", "chrome_veil"), "pearl", 9105,
      paint=dict(tex=0.28, film=dict(orders=3.0, quantize=0.65, a=0.72, brightness=1.0, blur=9.0)),
      fine=("fk:fbm", dict(octaves=(256, 512), weights=(1.0, 0.7)), 0.30), grain="fibre", detail=0.15, places=1.6, paint_micro=0.6,
      desc="Curtains of thin-film colour drifting across your paint, threaded with fine fibre.", swatch="#6fd6c4"),
    E("efx_lace_filament", "Lace Filament", "fk:filaments", dict(n=1400, length=42, wander=0.35, width=1.2),
      ("eggshell", "satin", "milk_glass", "pearl", "satin_chrome"), "satin_chrome", 9106,
      paint=dict(tex=0.30, stain=dict(color=(0.93, 0.90, 0.84), at="high", cover=(0.70, 0.90), a=0.80)),
      fine=("truchet", dict(tiles=120, style="arc", width=0.12), 0.22), grain="fibre", bands="linear",
      desc="Ivory filament lace over your colour, the threads picked out in satin chrome.", swatch="#d9d1c4"),
    E("efx_tempered_spectrum", "Tempered Spectrum", "ridge_flow", dict(ridges=150, cores=5, bend=1.6),
      ("satin", "brushed_ti", "steel_dark", "antique_chrome", "liquid_glaze", "spectraflame", "anodized"), "chrome_veil", 9107,
      paint=dict(tex=0.20, film=dict(orders=1.5, quantize=0.45, a=0.70, brightness=0.95)),
      fine=("ek:scanline", dict(lines=520.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.4), 0.28), grain="fibre",
      desc="Titanium heat tint — straw, bronze, violet and blue oxide bands following the brushed grain.", swatch="#8a7fb8"),
    E("efx_damascus_fold", "Damascus Fold", "damascus", dict(layers=190, folds=3, twist=2.2, warp=0.30),
      ("matte", "steel_dark", "gunmetal", "brushed_ti", "satin_chrome", "candy", "chrome_dry"), "chrome", 9108,
      paint=dict(tex=0.42, gamma=1.2, stain=dict(color=(0.16, 0.15, 0.15), at="low", cover=(0.0, 0.35), a=0.55)),
      fine=("ek:knurl", dict(pitch=9.0, angle=0.6, wobble=0.5), 0.18), grain="fibre",
      desc="Folded and etched steel — the dark layers bite in, the bright layers polish up.", swatch="#8b8a7a"),
    E("efx_stardust_coat", "Stardust Coat", "ek:splatter", dict(blobs=40000, rmax=1.4, drips=0.0, spatter=1.6),
      ("flat_black", "matte", "gloss", "spectraflame", "candy_chrome", "chrome"), "candy_chrome", 9109,
      paint=dict(tex=0.12, gamma=1.3, glint=dict(src="field", cover=(0.80, 0.97), amt=0.95, color=(0.95, 0.95, 1.0)),
                 stain=dict(color=(0.06, 0.06, 0.09), at="low", cover=(0.0, 0.45), a=0.50)),
      fine=("ek:discs", dict(n=260, radius=3.0, tilt=0.9, facet=1.0), 0.25), grain="spark", bands="linear",
      desc="A deep coat with a star field in it — dense micro sparkle and a few bright stars.", swatch="#18243f"),
    E("efx_spectral_edge", "Prism Edge", "quasicrystal", dict(waves=7, freq=210.0),
      ("gloss", "liquid_glaze", "candy", "spectraflame", "mirror_deep", "razor"), "razor", 9110,
      paint=dict(tex=0.40, film=dict(orders=3.5, quantize=0.8, a=0.30, brightness=1.0)),
      fine=("ek:pixels", dict(cell=5.0, levels=5, dither=0.2), 0.20), grain="ridge",
      desc="Seven-fold quasicrystal facets, each edge splitting light into a hard prism band.", swatch="#cfe8ff"),
    # ── holographic siblings (Holographic Drift itself is locked) ───────────────
    E("efx_holo_flake", "Holo Flake", "ek:discs", dict(n=9000, radius=3.6, tilt=0.8, facet=1.0),
      ("gloss", "candy", "spectraflame", "candy_chrome", "chrome", "mirror_deep"), "chrome", 9111,
      paint=dict(tex=0.30, film=dict(orders=5.0, quantize=1.0, a=0.62, brightness=1.0),
                 glint=dict(src="field", cover=(0.70, 0.95), amt=0.70, color=(1.0, 1.0, 1.0))),
      fine=("ek:holo", dict(rings=520.0, orders=2.0, warp=40.0, sharp=1.4), 0.22), grain="flake",
      desc="Holographic glitter vinyl — thousands of flakes, each one its own rainbow order.", swatch="#d8ccff"),
    E("efx_holo_prism_cells", "Holo Prism Cells", "basalt", dict(cells=120, relax=2, wall=0.10),
      ("soft_gloss", "candy", "spectraflame", "chrome_veil", "carrier_mid", "mirror_deep"), "candy_chrome", 9112,
      paint=dict(tex=0.30, film=dict(orders=5.0, quantize=1.0, a=0.60, brightness=1.0)),
      fine=("ek:scanline", dict(lines=330.0, triad=3.0, bloom=0.5, roll=0.1, jitter=0.7), 0.42), grain="grain",
      desc="A honeycomb of holographic cells, every cell locked to one colour of the spectrum.", swatch="#c9b8ff"),
    E("efx_holo_scan", "Holo Scanline", "moire_beat", dict(a=150.0, b=163.0, angle=0.12),
      ("gloss", "satin", "pearl", "spectraflame", "chrome_veil"), "candy_chrome", 9113,
      paint=dict(tex=0.14, film=dict(orders=2.6, quantize=0.20, a=0.55, brightness=1.0)),
      fine=("ek:scanline", dict(lines=260.0, triad=3.0, bloom=0.6, roll=0.3, jitter=0.4), 0.30), grain="grain",
      desc="Two gratings beating against each other — moiré bands of holographic colour.", swatch="#b9d6ff"),
    # ── glitter and flake ──────────────────────────────────────────────────────
    E("efx_micro_glitter", "Micro Glitter", "apollonian", dict(depth=5200, rmin=0.0018, rmax=0.020),
      ("wet", "liquid_glaze", "pearl", "mirror_deep", "mercury", "razor"), "mercury", 9114,
      paint=dict(tex=0.12, glint=dict(src="field", cover=(0.72, 0.96), amt=1.0, color=(1.0, 0.98, 0.92))),
      fine=("fk:sparks", dict(n=2200, life=30), 0.20), grain="spark",
      desc="Packed micro glitter — circles inside circles, every one a point of chrome.", swatch="#e6e2d6"),
    E("efx_chunky_flake", "Chunky Metalflake", "ek:discs", dict(n=3600, radius=6.5, tilt=0.7, facet=1.0),
      ("candy", "gloss", "metallic", "spectraflame", "chrome"), "spectraflame", 9115,
      paint=dict(tex=0.45, glint=dict(src="field", cover=(0.60, 0.90), amt=0.90, color=(0.92, 0.92, 0.95))),
      fine=("fk:fbm", dict(octaves=(256, 512), weights=(1.0, 0.7)), 0.18), grain="flake", chips=0.0, spec_grain=0.35, edge_max=0.12, places=2.0, bands="linear", region_blur=4.0, paint_micro=0.5, spec_kw=dict(micro="paint"),
      desc="Big bass-boat metalflake under candy — tilted chips that flash one at a time.", swatch="#b04060"),
    E("efx_glass_flake", "Glass Flake", "ek:facets", dict(stones=2600, table=0.5),
      ("gloss", "sea_glass", "milk_glass", "liquid_glaze", "pearl", "chrome_veil"), "liquid_glaze", 9116,
      paint=dict(tex=0.45, glint=dict(src="field", cover=(0.70, 0.95), amt=0.80, color=(1.0, 1.0, 1.0))),
      fine=("fk:anneal_crack", dict(cells=160, width=1.0, gen=1), 0.20), grain="flake",
      desc="Translucent glass shards suspended in clear — faceted, crazed, catching white light.", swatch="#cde4ec"),
    E("efx_gold_leaf", "Gold Leaf", "fk:spall", dict(cells=64, lift=0.75),
      ("satin", "eggshell", "candy", "spectraflame", "antique_chrome", "chrome"), "antique_chrome", 9117,
      paint=dict(tex=0.20, stain=dict(color=(0.90, 0.70, 0.28), at="high", cover=(0.45, 0.60), a=0.92)),
      fine=("ek:crinkle", dict(scale=300, sharp=2.2, folds=2), 0.30), grain="ridge",
      desc="Gold leaf laid in sheets over your colour, crinkled and lifting at the corners.", swatch="#d4a83a"),
    # ── weathered ─────────────────────────────────────────────────────────────
    E("efx_surface_rust", "Surface Rust", "gray_scott", dict(feed=0.030, kill=0.062, steps=700, sim=448),
      ("satin", "eggshell", "matte", "patina", "bead_blast", "galvanized"), "galvanized", 9118,
      paint=dict(tex=0.15, stain=dict(color=(0.62, 0.30, 0.10), at="high", cover=(0.55, 0.75), a=0.85),
                 stain2=dict(color=(0.30, 0.14, 0.06), at="high", cover=(0.85, 0.95), a=0.90)),
      fine=("ek:craters", dict(n=5000, rmin=1.0, rmax=3.0, rim=0.5), 0.30), grain="stipple",
      desc="Rust blooming through the paint in spots — orange first, then the dark scabs.", swatch="#8c4a22"),
    E("efx_rust_through", "Rust-Through", "fk:percolate", dict(cells=60, p=0.50, rounds=3),
      ("matte", "clear_matte", "patina", "bead_blast", "steel_dark", "gunmetal"), "steel_dark", 9119,
      paint=dict(tex=0.25, stain=dict(color=(0.42, 0.19, 0.07), at="low", cover=(0.25, 0.55), a=0.90),
                 stain2=dict(color=(0.55, 0.55, 0.56), at="low", cover=(0.0, 0.12), a=0.85)),
      fine=("ek:splatter", dict(blobs=3000, rmax=4.0, drips=0.0, spatter=1.2), 0.30), grain="grain", bands="linear",
      desc="Paint islands left on rusted steel, pitted down to bare metal.", swatch="#5a3a24"),
    E("chalky_base", "Chalked Paint", "erosion", dict(sim=512, iters=30, sharp=0.6),
      ("ceramic_matte", "clear_matte", "matte", "eggshell", "satin", "gloss"), "eggshell", 9120,
      paint=dict(tex=0.18, stain=dict(color=(0.93, 0.92, 0.88), at="high", cover=(0.40, 0.80), a=0.55)),
      fine=("ek:craters", dict(n=40000, rmin=0.7, rmax=1.8, rim=0.3), 0.50), grain="stipple", detail=0.50,
      desc="Oxidised paint gone to chalk — powdery blotches fading your colour, pinholed all over.", swatch="#b9b5a8"),
    E("efx_peeling_clear", "Peeling Clear", "ek:camo", dict(patches=6, blob=48.0, roughness=1.4, edge=0.0),
      ("gloss", "liquid_glaze", "clear_matte", "matte", "eggshell", "void"), "liquid_glaze", 9121,
      paint=dict(tex=0.30, stain=dict(color=(0.86, 0.86, 0.82), at="high", cover=(0.50, 0.65), a=0.60)),
      fine=("fk:anneal_crack", dict(cells=90, width=1.4, gen=1), 0.15), grain="crackle", detail=0.15, bands="linear",
      desc="Clearcoat failure — islands of intact gloss beside hazed, crazed patches where it let go.", swatch="#9fa39a"),
    E("efx_sun_faded", "Sun Faded", "fk:fbm", dict(octaves=(6, 12, 24, 48), weights=(1.0, 0.7, 0.45, 0.30)),
      ("eggshell", "matte", "satin", "clear_matte", "ceramic_matte"), "satin", 9122,
      paint=dict(tex=0.35, stain=dict(color=(0.82, 0.80, 0.74), at="high", cover=(0.45, 0.85), a=0.50)),
      fine=("ek:craters", dict(n=40000, rmin=0.7, rmax=1.8, rim=0.3), 0.60), grain="stipple", detail=0.50, places=2.8, region_blur=4.0, paint_micro=0.9,
      desc="Twenty summers of sun — broad bleached zones and a fine dust-pitted skin.", swatch="#c7b9a2"),
    E("efx_galvanized_spangle", "Galvanized Spangle", "basalt", dict(cells=44, relax=3, wall=0.10),
      ("galvanized", "bead_blast", "brushed_ti", "satin_chrome", "chrome_dry", "pewter_metal"), "satin_chrome", 9123,
      paint=dict(tex=0.55, gamma=1.0),
      fine=("fk:filaments", dict(n=7000, length=14, wander=0.5, width=0.9), 0.60), grain="grain", detail=0.30,
      cell_tone=0.7, chips=0.0, spec_grain=0.30, places=1.8, region_blur=2.0, paint_micro=1.0, spec_kw=dict(micro="paint"),
      desc="Hot-dip zinc spangle — polygonal crystals in your colour, each one a different brightness, feathered inside.", swatch="#a9adb2"),
    E("efx_verdigris", "Verdigris", "fk:percolate", dict(cells=150, p=0.45, rounds=3),
      ("patina", "matte", "ceramic_matte", "bronze_raw", "antique_chrome"), "bronze_raw", 9124,
      paint=dict(tex=0.18, stain=dict(color=(0.30, 0.64, 0.52), at="high", cover=(0.45, 0.70), a=0.85),
                 stain2=dict(color=(0.60, 0.36, 0.22), at="low", cover=(0.0, 0.30), a=0.45)),
      fine=("ek:craters", dict(n=6000, rmin=1.0, rmax=2.6, rim=0.4), 0.35), grain="stipple",
      desc="Copper patina in a labyrinth — green crust, raw bronze in the channels.", swatch="#4f9a82"),
    E("efx_soot_wash", "Soot Wash", "ek:splatter", dict(blobs=700, rmax=26.0, drips=0.9, spatter=1.4),
      ("void", "flat_black", "matte", "satin", "gloss", "wet"), "wet", 9125,
      paint=dict(tex=0.40, stain=dict(color=(0.05, 0.05, 0.05), at="high", cover=(0.50, 0.80), a=0.90)),
      fine=("ek:splatter", dict(blobs=6000, rmax=3.0, drips=0.3, spatter=1.0), 0.30), grain="grain", detail=0.30, bands="linear",
      desc="Exhaust soot settling on the panel in smudges and drips, spattered and wet where it is thickest.", swatch="#2b2b2b"),
    E("efx_salt_bloom", "Salt Bloom", "frost_fern", dict(seeds=70, steps=80, branch=0.20, drift=0.5),
      ("matte", "eggshell", "ceramic_matte", "milk_glass", "sea_glass"), "milk_glass", 9126,
      paint=dict(tex=0.12, stain=dict(color=(0.95, 0.95, 0.92), at="high", cover=(0.55, 0.80), a=0.85)),
      fine=("fk:anneal_crack", dict(cells=200, width=0.9, gen=1), 0.22), grain="crackle", bands="linear",
      desc="Salt efflorescence — white crystal ferns growing out of the paint.", swatch="#e6e6dc"),
    # ── shop metal ────────────────────────────────────────────────────────────
    E("efx_hammered", "Hammered", "rosensweig", dict(pitch=64.0, relax=0.5, spike=1.6),
      ("brushed_ti", "gunmetal", "satin_chrome", "antique_chrome", "chrome", "pewter_metal"), "chrome", 9127,
      paint=dict(tex=0.50, gamma=1.1), fine=("fk:fbm", dict(octaves=(256, 512, 1024), weights=(0.5, 1.0, 0.8)), 0.15), grain="grain", chips=0.0, spec_grain=0.30, places=2.0, region_blur=5.0, paint_micro=0.8,
      desc="Ball-peen hammered metal — a lattice of dents, every facet catching its own light.", swatch="#9a9a9e"),
    E("efx_cast_iron", "Cast Iron", "ek:craters", dict(n=3500, rmin=2.0, rmax=6.0, rim=0.6),
      ("void", "flat_black", "bead_blast", "frozen_metal", "gunmetal", "steel_dark"), "steel_dark", 9128,
      paint=dict(tex=0.35, gamma=1.3, stain=dict(color=(0.17, 0.17, 0.18), at="low", cover=(0.0, 0.60), a=0.60)),
      fine=("ek:splatter", dict(blobs=9000, rmax=2.5, drips=0.0, spatter=1.0), 0.25), grain="stipple",
      desc="Sand-cast iron — porous, pitted, dead dark with a dull metal glint on the rims.", swatch="#3a3a3c"),
    E("efx_knurled", "Knurled", "ek:knurl", dict(pitch=15.0, angle=0.0, wobble=0.15),
      ("vinyl", "gunmetal", "brushed_ti", "steel_dark", "satin_chrome", "chrome"), "chrome", 9129,
      paint=dict(tex=0.45), fine=("fk:fbm", dict(octaves=(512, 1024), weights=(1.0, 0.7)), 0.12), grain="grain",
      desc="Machine-knurled diamonds — a grip texture cut into metal, light on every pyramid.", swatch="#8e9096"),
    E("efx_engine_turned", "Engine Turned", "imbricate", dict(rows=90, overlap=0.45, jitter=0.12),
      ("brushed_ti", "satin_chrome", "chrome_dry", "antique_chrome", "chrome", "mercury"), "mercury", 9130,
      paint=dict(tex=0.38), fine=("ek:scanline", dict(lines=600.0, triad=1.0, bloom=0.2, roll=0.0, jitter=0.5), 0.30), grain="fibre",
      desc="Jewelled aluminium — overlapping swirl discs, each one a circular brush mark.", swatch="#c0c4ca"),
    E("efx_sandblasted", "Sandblasted", "ek:craters", dict(n=30000, rmin=0.6, rmax=1.8, rim=0.3),
      ("vinyl", "bead_blast", "frozen_metal", "galvanized", "chrome_dry", "satin_chrome"), "satin_chrome", 9131,
      paint=dict(tex=0.30), fine=("fk:fbm", dict(octaves=(64, 128), weights=(1.0, 0.6)), 0.20), grain="stipple",
      desc="Blasted to a uniform micro-pitted tooth — dry metal with a soft sparkle.", swatch="#a6a6a4"),
    E("efx_wire_brushed", "Wire Brushed", "fk:curl", dict(scale=32, steps=70),
      ("matte", "brushed_ti", "steel_dark", "satin_chrome", "chrome_dry", "chrome"), "chrome", 9132,
      paint=dict(tex=0.40), fine=("ek:threads", dict(), 0.30), grain="fibre",
      desc="Wire-wheel swirl scratches sweeping across the metal, bright on the crests.", swatch="#9d9fa3"),
    E("efx_mill_scale", "Mill Scale", "fk:spall", dict(cells=96, lift=0.4),
      ("void", "flat_black", "steel_dark", "gunmetal", "bead_blast", "antique_chrome"), "antique_chrome", 9133,
      paint=dict(tex=0.25, stain=dict(color=(0.12, 0.13, 0.16), at="high", cover=(0.35, 0.55), a=0.85),
                 stain2=dict(color=(0.60, 0.60, 0.62), at="low", cover=(0.0, 0.20), a=0.60)),
      fine=("fk:anneal_crack", dict(cells=150, width=1.1, gen=1), 0.25), grain="crackle", bands="linear",
      desc="Hot-rolled steel skin — blue-black scale plates flaking off bright metal.", swatch="#33363c"),
    # ── coatings ──────────────────────────────────────────────────────────────
    E("efx_orange_peel", "Orange Peel", "fk:fbm", dict(octaves=(96, 192), weights=(1.0, 0.5)),
      ("metallic", "gloss", "soft_gloss", "semi_gloss", "liquid_glaze", "wet", "candy"), "liquid_glaze", 9134,
      paint=dict(tex=0.20), fine=("fk:fbm", dict(octaves=(384, 768), weights=(1.0, 0.6)), 0.18), grain="grain",
      desc="Real sprayed orange peel — a dimpled gloss that breaks reflections into cells.", swatch="#6aa0c8"),
    E("efx_crackle_lacquer", "Crackle Lacquer", "fk:anneal_crack", dict(cells=90, width=1.2, gen=1),
      ("gloss", "wet", "satin", "eggshell", "gloss_carbon", "flat_black"), "flat_black", 9135,
      paint=dict(tex=0.15, stain=dict(color=(0.10, 0.08, 0.06), at="high", cover=(0.84, 0.96), a=0.90)),
      fine=("fk:fbm", dict(octaves=(256, 512), weights=(1.0, 0.7)), 0.15), grain="crackle",
      desc="Crackle lacquer — a fine craze network opening onto a dark undercoat.", swatch="#8a6a52"),
    E("efx_wrinkle_coat", "Wrinkle Coat", "fk:wrinkle", dict(k=2.4, steps=30, scale=70),
      ("powder", "vinyl", "matte", "eggshell", "satin_carbon", "anodized"), "vinyl", 9136,
      paint=dict(tex=0.40), fine=("fk:fbm", dict(octaves=(512, 1024), weights=(1.0, 0.6)), 0.15), grain="ridge", detail=0.25, chips=0.3, edge_max=0.12, places=2.2, region_blur=5.0, paint_micro=0.5, spec_kw=dict(micro="paint"),
      desc="Wrinkle powder coat — the valve-cover texture, ridged and dry.", swatch="#556655"),
    E("efx_raku_glaze", "Raku Glaze", "caustics", dict(scale=5.0, octaves=3, gain=3.2),
      ("ceramic_gloss", "ceramic_matte", "candy", "antique_chrome", "bronze_raw", "mirror_deep"), "antique_chrome", 9137,
      paint=dict(tex=0.25, stain=dict(color=(0.72, 0.50, 0.28), at="high", cover=(0.60, 0.85), a=0.60)),
      fine=("fk:anneal_crack", dict(cells=110, width=1.3, gen=1), 0.30), grain="crackle",
      desc="Raku pottery — glaze flowing in caustic webs, copper lustre where it pooled, crazed all over.", swatch="#a06a40"),
    E("efx_powder_texture", "Textured Powder", "ek:splatter", dict(blobs=16000, rmax=3.2, drips=0.0, spatter=1.0),
      ("powder", "bead_blast", "eggshell", "vinyl", "frozen_film"), "frozen_film", 9138,
      paint=dict(tex=0.28), fine=("fk:fbm", dict(octaves=(256, 512, 1024), weights=(0.5, 1.0, 0.8)), 0.20), grain="stipple", detail=0.22, chips=0.0, spec_grain=0.30, edge_max=0.12, places=2.2, region_blur=5.0, paint_micro=0.8, spec_kw=dict(micro="paint"),
      desc="Sand-texture powder coat — a dense grit of raised specks in your colour.", swatch="#7b8079"),
    # ── nature and stone ──────────────────────────────────────────────────────
    E("efx_terrazzo", "Terrazzo", "ek:discs", dict(n=3200, radius=6.0, tilt=0.3, facet=0.0),
      ("ceramic_matte", "matte", "semi_gloss", "gloss", "ceramic_gloss", "milk_glass"), "gloss", 9139,
      paint=dict(tex=0.18, stain=dict(color=(0.92, 0.90, 0.86), at="high", cover=(0.55, 0.75), a=0.80),
                 stain2=dict(color=(0.16, 0.15, 0.15), at="high", cover=(0.90, 0.97), a=0.85)),
      fine=("fk:fbm", dict(octaves=(256, 512), weights=(1.0, 0.6)), 0.12), grain="stipple", bands="linear",
      desc="Terrazzo — stone chips set in your colour and ground flat, some white, some black.", swatch="#b8b0a4"),
    E("efx_leather_grain", "Leather Grain", "fk:worley", dict(cells=110, kind="f2f1"),
      ("vinyl", "satin", "eggshell", "semi_gloss", "soft_gloss", "pearl", "anodized"), "soft_gloss", 9140,
      paint=dict(tex=0.32, gamma=1.1), fine=("fk:wrinkle", dict(k=1.2, steps=16, scale=40), 0.25), grain="crackle", detail=0.15, chips=0.0, spec_grain=0.30, edge_max=0.14, places=1.8, region_blur=1.5, paint_micro=1.0, spec_kw=dict(micro="paint"),
      desc="Pebbled leather — a tight grain of soft cells with creases running between them.", swatch="#7a5a44"),
    E("efx_rain_beads", "Rain Beads", "fk:eden", dict(seeds=2600, steps=8),
      ("gloss", "liquid_glaze", "wet", "sea_glass", "mirror_deep", "mercury"), "mercury", 9141,
      paint=dict(tex=0.16, glint=dict(src="field", cover=(0.80, 0.97), amt=0.55, color=(1.0, 1.0, 1.0))),
      fine=("ek:craters", dict(n=3000, rmin=1.5, rmax=4.0, rim=0.8), 0.25), grain="grain",
      desc="Water beading on a waxed panel — every drop a lens with a chrome highlight.", swatch="#5f8fb0"),
    E("efx_snow_crust", "Snow Crust", "metaball", dict(blobs=2600, radius=0.009, thresh=0.35),
      ("ceramic_matte", "matte", "milk_glass", "frozen_film", "bead_blast"), "frozen_film", 9142,
      paint=dict(tex=0.40, stain=dict(color=(0.94, 0.95, 0.97), at="high", cover=(0.30, 0.70), a=0.85),
                 glint=dict(src="field", cover=(0.85, 0.98), amt=0.90, color=(1.0, 1.0, 1.0))),
      fine=("ek:craters", dict(n=20000, rmin=0.8, rmax=2.2, rim=0.5), 0.50), grain="spark", chips=0.0, spec_grain=0.30, places=2.0, region_blur=4.0, paint_micro=0.8,
      desc="Crusted snow — drifts dividing and merging over your colour, sparkling where it froze hard.", swatch="#e8ecf2"),
    E("efx_nacre", "Nacre", "fk:braid", dict(layers=60, shear=2.0),
      ("pearl", "satin", "milk_glass", "candy", "chrome_veil"), "pearl", 9143,
      paint=dict(tex=0.14, film=dict(orders=1.3, quantize=0.15, a=0.42, brightness=1.0)),
      fine=("ek:threads", dict(), 0.20), grain="fibre",
      desc="Mother of pearl — braided growth lines with a soft interference shimmer.", swatch="#e3dfe8"),
]

BY_ID = {r["fid"]: r for r in ROWS}
SHELF_ORDER = list(KEPT) + [r["fid"] for r in ROWS]

# Per-row spec composition, MEASURED by _efx_work/sweep.py against the FINISH LAW's own
# axes (bands x micro x chips at 768): the richest spec among settings that still follow.
# SPECKW-BEGIN
SPECKW = {
    'chalky_base': {'bands': 'quantile', 'micro': 'paint', 'chips': 0.34},
    'efx_aurora_skin': {'bands': 'quantile', 'micro': 'paint', 'chips': 0.34},
    'efx_cast_iron': {'bands': 'quantile', 'chips': 0.15},
    'efx_cathedral_veil': {'bands': 'quantile', 'micro': 'paint', 'chips': 0.34},
    'efx_chunky_flake': {'bands': 'linear', 'chips': 0.34},
    'efx_crackle_lacquer': {'bands': 'quantile', 'chips': 0.34},
    'efx_damascus_fold': {'bands': 'quantile', 'chips': 0.15},
    'efx_engine_turned': {'bands': 'linear', 'chips': 0.34},
    'efx_galvanized_spangle': {'bands': 'quantile', 'chips': 0.15},
    'efx_glass_flake': {'bands': 'quantile', 'chips': 0.15},
    'efx_gold_leaf': {'bands': 'quantile', 'chips': 0.15},
    'efx_hammered': {'bands': 'quantile', 'micro': 'paint', 'chips': 0.34},
    'efx_holo_flake': {'bands': 'quantile', 'micro': 'paint', 'chips': 0.34},
    'efx_holo_prism_cells': {'bands': 'quantile', 'chips': 0.15},
    'efx_holo_scan': {'bands': 'quantile', 'micro': 'paint', 'chips': 0.34},
    'efx_kintsugi_bloom': {'bands': 'linear', 'micro': 'paint', 'chips': 0.34},
    'efx_knurled': {'bands': 'linear', 'micro': 'paint', 'chips': 0.34},
    'efx_lace_filament': {'bands': 'linear', 'chips': 0.15},
    'efx_leather_grain': {'bands': 'quantile', 'chips': 0.34},
    'efx_micro_glitter': {'bands': 'linear', 'micro': 'paint', 'chips': 0.34},
    'efx_mill_scale': {'bands': 'linear', 'micro': 'paint', 'chips': 0.34},
    'efx_nacre': {'bands': 'quantile', 'micro': 'paint', 'chips': 0.34},
    'efx_orange_peel': {'bands': 'quantile', 'chips': 0.34},
    'efx_peeling_clear': {'bands': 'quantile', 'micro': 'paint', 'chips': 0.34},
    'efx_powder_texture': {'bands': 'quantile', 'chips': 0.34},
    'efx_quicksilver_pool': {'bands': 'linear', 'chips': 0.15},
    'efx_rain_beads': {'bands': 'quantile', 'micro': 'paint', 'chips': 0.15},
    'efx_raku_glaze': {'bands': 'quantile', 'chips': 0.34},
    'efx_rust_through': {'bands': 'linear', 'chips': 0.34},
    'efx_salt_bloom': {'bands': 'linear', 'micro': 'paint', 'chips': 0.34},
    'efx_sandblasted': {'bands': 'linear', 'micro': 'paint', 'chips': 0.15},
    'efx_snow_crust': {'bands': 'linear', 'micro': 'paint', 'chips': 0.34},
    'efx_soot_wash': {'bands': 'linear', 'micro': 'paint', 'chips': 0.34},
    'efx_spectral_edge': {'bands': 'linear', 'micro': 'paint', 'chips': 0.34},
    'efx_stardust_coat': {'bands': 'linear', 'chips': 0.34},
    'efx_sun_faded': {'bands': 'quantile', 'micro': 'paint', 'chips': 0.34},
    'efx_surface_rust': {'bands': 'quantile', 'micro': 'paint', 'chips': 0.34},
    'efx_tempered_spectrum': {'bands': 'linear', 'micro': 'paint', 'chips': 0.34},
    'efx_terrazzo': {'bands': 'linear', 'micro': 'paint', 'chips': 0.34},
    'efx_verdigris': {'bands': 'linear', 'chips': 0.15},
    'efx_volcanic_obsidian': {'bands': 'quantile', 'micro': 'paint', 'chips': 0.34},
    'efx_wire_brushed': {'bands': 'quantile', 'micro': 'paint', 'chips': 0.15},
    'efx_wrinkle_coat': {'bands': 'quantile', 'chips': 0.34},
}
# SPECKW-END


def check():
    """Shelf-level identity: every row owns its construction family and its deck."""
    problems = []
    decks = {}
    forms = {}
    for r in ROWS:
        for c in r["deck"] + (r["edge"],):
            if c not in SC.CARDS:
                problems.append(f"{r['fid']}: unknown card {c!r}")
        decks.setdefault(r["deck"], []).append(r["fid"])
        key = (r["form"], tuple(sorted((k, str(v)) for k, v in r["params"].items())))
        forms.setdefault(key, []).append(r["fid"])
    for d, ids in decks.items():
        if len(ids) > 1:
            problems.append(f"shared deck {ids}")
    for k, ids in forms.items():
        if len(ids) > 1:
            problems.append(f"shared construction {k[0]} {ids}")
    return problems


# ═══════════════════════════════════════════════════════════════════════════════
# FIELDS
# ═══════════════════════════════════════════════════════════════════════════════
def _form_field(form, params, shape, seed):
    p = dict(params)
    if form.startswith("fk:"):
        key = form[3:]
        fn = {
            "worley": lambda: FK.worley(shape, seed, **p),
            "filaments": lambda: (FK.filaments(shape, seed, **p), None),
            "braid": lambda: (FK.kh_braid(shape, seed, **p), None),
            "curl": lambda: (FK.curl(shape, seed, **p), None),
            "dla": lambda: (FK.dla(shape, seed, **p), None),
            "percolate": lambda: FK.percolate(shape, seed, **p),
            "spall": lambda: FK.spall(shape, seed, **p),
            "anneal_crack": lambda: FK.anneal_crack(shape, seed, **p),
            "eden": lambda: (FK.eden(shape, seed, **p), None),
            "wrinkle": lambda: (FK.wrinkle(shape, seed, **p), None),
            "rt_fingers": lambda: (FK.rt_fingers(shape, seed, **p), None),
            "sparks": lambda: (FK.sparks(shape, seed, **p), None),
            "fbm": lambda: (FK.fbm(shape, seed, **p), None),
        }[key]
        out = fn()
    elif form.startswith("ek:"):
        out = getattr(EK, form[3:])(shape, seed, **p)
    else:
        out = getattr(NF, form)(shape, seed, **p)
    f, lab = out if isinstance(out, tuple) else (out, None)
    f = np.asarray(f, np.float32)
    if f.ndim == 3:
        f = f.mean(axis=2)
    return FK.pct(f), lab


@lru_cache(maxsize=64)
def _field(fid):
    r = BY_ID[fid]
    f, lab = _form_field(r["form"], r["params"], (GEN, GEN), r["seed"])
    ct = float(r.get("cell_tone", 0.0))
    if ct > 0.0 and lab is not None:
        # spangle / crystal grains: every cell one flat tone, so a crystal reads as a crystal
        tone = ST._hash01(np.asarray(lab, np.int64), r["seed"] + 77).astype(np.float32)
        f = np.clip(f * (1.0 - ct) + tone * ct, 0, 1).astype(np.float32)
    f = NF.compose_form(f, r["seed"], kind=r["grain"], amount=float(r["detail"]), res=GEN)
    # places: busy zones and calm zones, so the FOLLOW axis has something to locate
    slow = np.asarray(FK.fbm((GEN, GEN), r["seed"] + 7, octaves=(5, 10, 20), weights=(1.0, 0.6, 0.35)), np.float32)
    slow = (slow - float(slow.min())) / max(float(slow.max() - slow.min()), 1e-6)
    if r["fine"] is not None:
        form2, params2, w = r["fine"]
        f2, _ = _form_field(form2, params2, (GEN, GEN), r["seed"] + 41)
        gy, gx = np.gradient(f)
        key = np.hypot(gx, gy)
        key = key / max(float(np.percentile(key, 98)), 1e-6)
        key = 0.45 + 0.55 * np.clip(key, 0, 1)
        f = np.clip(f * (1.0 - w) + f2 * w * key + f * w * (1.0 - key), 0, 1).astype(np.float32)
    # `places` > 1 flattens the calm zones harder and lifts the busy ones — the only way a
    # texture that is equally busy everywhere (wrinkle, powder, leather) gives FOLLOW anything
    # to locate (DARK CITY measured -0.21..0.15 on such fields before adding places). Applied
    # AFTER the nested fine layer, otherwise that layer re-busies the calm zones uniformly.
    m = float(f.mean())
    pl = float(r.get("places", 1.0))
    lo, hi = max(0.12, 0.55 / pl), 0.9 * pl
    f = np.clip(m + (f - m) * (lo + hi * slow), 0, 1).astype(np.float32)
    return FK.pct(f).astype(np.float32), lab


# ═══════════════════════════════════════════════════════════════════════════════
# TEXTURE (on the painter's colour)
# ═══════════════════════════════════════════════════════════════════════════════
def _smooth(x, lo, hi):
    t = np.clip((x - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _stain_alpha(tq, st):
    lo, hi = st.get("cover", (0.5, 0.8))
    if st.get("at", "high") == "high":
        a = _smooth(tq, lo, hi)
    else:
        a = 1.0 - _smooth(tq, lo, hi)
    return (a * float(st.get("a", 0.8))).astype(np.float32)


@lru_cache(maxsize=64)
def _tex(fid):
    """Everything the texture needs, at WORK res, independent of the painter's colour."""
    r = BY_ID[fid]
    pr = r["paint"]
    f, _ = _field(fid)
    f = np.asarray(FK.upscale(f, WORK), np.float32)
    tq = np.clip(f, 0, 1) ** float(pr.get("gamma", 1.0))
    out = {"t": tq.astype(np.float32)}
    tex = float(pr.get("tex", 0.0))
    out["mul"] = np.clip(1.0 + (tq - 0.5) * 2.0 * tex, 0.30, 1.70).astype(np.float32)
    for key in ("stain", "stain2"):
        st = pr.get(key)
        if st:
            out[key + "_a"] = _stain_alpha(tq, st)
            out[key + "_rgb"] = np.asarray(st["color"], np.float32)
    film = pr.get("film")
    if film:
        tf = tq
        fb = float(film.get("blur", 0.0))
        if fb > 0.0 and cv2 is not None:
            # thin-film colour follows the SLOW flow; the fine grain stays in the value channel
            tf = cv2.GaussianBlur(tq, (0, 0), fb)
        col = interference_palette(tf, orders=float(film.get("orders", 2.0)),
                                   quantize=float(film.get("quantize", 0.5)),
                                   brightness=float(film.get("brightness", 1.0)))
        out["film_rgb"] = np.asarray(col, np.float32)
        out["film_a"] = float(film.get("a", 0.5))
    gl = pr.get("glint")
    if gl:
        if gl.get("src") == "field":
            lo, hi = gl.get("cover", (0.75, 0.95))
            out["glint"] = _smooth(tq, lo, hi).astype(np.float32)
        elif cv2 is not None:
            g, _k = NF.detail(f, r["seed"] + 5, kind=gl.get("kind", "spark"), amount=1.0, res=WORK)
            out["glint"] = np.clip((g - 0.55) / 0.45, 0.0, 1.0).astype(np.float32)
        if "glint" in out:
            out["glint_amt"] = float(gl.get("amt", 0.6))
            out["glint_rgb"] = np.asarray(gl.get("color", (1.0, 1.0, 1.0)), np.float32)
    return out


def _fit(a, h, w):
    a = np.asarray(a, np.float32)
    if a.shape[0] == h and a.shape[1] == w:
        return a
    if cv2 is None:
        return a
    return cv2.resize(a, (w, h), interpolation=cv2.INTER_LINEAR)


def _apply(src, tex, h, w):
    out = np.asarray(src, np.float32)
    if "film_rgb" in tex:
        fa = float(tex["film_a"])
        out = out * (1.0 - fa) + _fit(tex["film_rgb"], h, w) * fa
    for key in ("stain", "stain2"):
        if key + "_a" in tex:
            a = _fit(tex[key + "_a"], h, w)[..., None]
            out = out * (1.0 - a) + tex[key + "_rgb"][None, None, :] * a
    out = out * _fit(tex["mul"], h, w)[..., None]
    if "glint" in tex:
        g = (_fit(tex["glint"], h, w) * tex["glint_amt"])[..., None]
        out = out + g * (tex["glint_rgb"][None, None, :] - out)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


@lru_cache(maxsize=64)
def _art_ref(fid):
    """The texture on neutral gray — what the gates render, and what the spec is dealt on."""
    tex = _tex(fid)
    return _apply(np.full((WORK, WORK, 3), 0.5, np.float32), tex, WORK, WORK)


# ═══════════════════════════════════════════════════════════════════════════════
# SPEC (dealt on the same field, amplitude from the rendered texture)
# ═══════════════════════════════════════════════════════════════════════════════
def _spec_square(fid, res):
    r = BY_ID[fid]
    f, lab = _field(fid)
    f = np.asarray(FK.upscale(f, res), np.float32)
    lab = FK.upscale(lab, res) if (lab is not None and r.get("use_lab", True)) else None
    art = _fit(_art_ref(fid), res, res)
    kw = dict(bands=r["bands"], chips=float(r["chips"]), grain=float(r["spec_grain"]))
    kw.update(r["spec_kw"])
    kw.update(SPECKW.get(fid, {}))
    # region_blur: cut the material regions on a lightly blurred paint, so on a texture that is
    # busy everywhere (wrinkle, powder, leather, spangle) the card boundaries follow the MACRO
    # tone and do not fall between every ridge. paint_micro then rides the spec's roughness on
    # the paint's own car-window band-pass (the FINISH LAW's exact 8-32px window), so the spec's
    # fine detail sits on the same pixels as the paint's.
    rb = float(r.get("region_blur", 0.0))
    art_regions = art
    if rb > 0.0 and cv2 is not None:
        art_regions = cv2.GaussianBlur(art, (0, 0), rb * res / 1024.0)
    spec = np.asarray(ST.compose(f, r["deck"], seed=r["seed"], res=res, lab=lab, edge=r["edge"],
                                 art=art_regions, edge_max=float(r["edge_max"]), **kw), np.float32)
    pm = float(r.get("paint_micro", 0.0))
    if pm > 0.0 and cv2 is not None:
        L = (0.2126 * art[..., 0] + 0.7152 * art[..., 1] + 0.0722 * art[..., 2]).astype(np.float32)
        lo = cv2.GaussianBlur(L, (0, 0), res / 2048.0 * 16.0)
        hi = cv2.GaussianBlur(L, (0, 0), max(0.6, res / 2048.0 * 4.0))
        bp = hi - lo
        bp = bp / max(float(np.percentile(np.abs(bp), 99.0)), 1e-6)
        bp = np.clip(bp, -1.0, 1.0)
        spec[..., 1] = np.clip(spec[..., 1] * (1.0 + bp * pm * 0.70), 15, 255)
        spec[..., 0] = np.clip(spec[..., 0] * (1.0 + bp * pm * 0.30), 0, 255)
        spec[..., 2] = np.clip(spec[..., 2] * (1.0 - bp * pm * 0.20), 16, 255)
    return spec


def _mk(fid):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)
        if src.ndim == 3:
            src = src[:, :, :3]
        else:
            src = np.repeat(src[..., None], 3, axis=2)
        if src.size and float(src.max()) > 1.5:
            src = src / 255.0
        if src.shape[0] != fh or src.shape[1] != fw:
            src = _fit(src, fh, fw)
        m2 = np.asarray(mask, np.float32) if mask is not None else np.ones((fh, fw), np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = _fit(m2, fh, fw)
        out = _apply(src, _tex(fid), fh, fw)
        kk = np.clip(m2 * float(pm if pm is not None else 1.0), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - kk) + out * kk, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, seed, sm, base_m, base_r):
        fh, fw = int(shape[0]), int(shape[1])
        res = max(fh, fw)
        spec = np.asarray(_spec_square(fid, res), np.float32)[:fh, :fw]
        safe = np.asarray(FK.iron_safe(spec), np.float32)
        return (np.ascontiguousarray(safe[..., 0]), np.ascontiguousarray(safe[..., 1]),
                np.ascontiguousarray(np.maximum(safe[..., 2], 16.0)))

    paint_fn.__name__ = "paint_" + fid
    spec_fn.__name__ = "spec_" + fid
    return paint_fn, spec_fn


def _anchor(deck):
    m, rr, cc = SC.CARDS[deck[len(deck) // 2]]
    return int(m), int(rr), int(cc)


def _entry(r):
    paint_fn, spec_fn = _mk(r["fid"])
    m, rr, cc = _anchor(r["deck"])
    return {"M": m, "R": rr, "CC": cc, "paint_fn": paint_fn, "base_spec_fn": spec_fn,
            "desc": r["desc"], "efx_name": r["name"], "efx_swatch": r["swatch"]}


FOUNDATION_EFX = {r["fid"]: _entry(r) for r in ROWS if r["fid"] not in LOCKED}


def install(base_reg):
    """Merge into a BASE_REGISTRY in place. Never touches the locked keeper."""
    n = 0
    for fid, e in FOUNDATION_EFX.items():
        if fid in LOCKED:
            continue
        base_reg[fid] = e
        n += 1
    return n
