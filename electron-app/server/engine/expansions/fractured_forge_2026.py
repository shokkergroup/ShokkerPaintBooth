"""FRACTURED FORGE (2026-06-16) — the generative-pattern MATH ENGINES wired in as finishes.

These are NOT color-shift bases (that's FRACTURED MINDS/SOULS). Each FORGE finish is a
standalone procedural look: a math engine in engine/paint_v2/fractured_math.py produces an
intricate full-canvas FIELD, colorize() turns it into dark-albedo FRACTURED art, and the
canonical fracture_spec() ignites it (near-chrome body, Fresnel clearcoat, roughness tracery
along the pattern's own lanes).

ONE recipe table is the single source of truth: id -> (engine, seed, palette, colorize dials).
33 vetted recipes ship first (owner-approved 2026-06-16); the same engines back the planned
expansion to 100 by adding more seed/palette recipes (each must clear the uniqueness gate).

Registry contract mirrors fractured_souls_2026: mono_reg[id] = (spec_fn, paint_fn).
  spec_fn(shape, mask, seed, sm) -> HxWx4 uint8 (M, R, Cc, A)
  paint_fn(paint, shape, mask, seed, pm, bb) -> HxWx3 float 0..1
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

import engine.paint_v2.fractured_math as fm
from engine.spec_sculpt.fracture import fracture_spec

_WORK = 1152          # compute art at this res then resize to the requested render size
_GROUP = "⚛ FRACTURED FORGE"


def _drift(h, w, s):  # the Drift Lattice composition (fracture x curl flow)
    a = fm.worley(h, w, s, cells=300, kind="cracks")
    b = fm.curl_flow(h, w, s + 101)
    return fm._norm(a * (0.45 + 0.55 * b))


# id -> recipe.  engine = fractured_math fn name (or "_drift"); eargs = extra engine kwargs.
FORGE = {
 # ── Wave 1 ───────────────────────────────────────────────────────────────
 "ff_abyssal_currents": dict(name="Abyssal Currents", engine="attractor_web", eargs=dict(kind="dejong", layers=4), seed=3,
    base=(3, 8, 14), glow=(22, 95, 155), edge=(135, 225, 255),
    kw=dict(gamma=0.74, fill_gain=1.05, edge_gain=0.6, ambient=0.25, ambient_sigma=60, ambient_floor=0.22),
    desc="Layered de Jong strange-attractor web (toroidally wrapped) — an intricate blue filament net filling the whole panel."),
 "ff_leviathan_filaments": dict(name="Leviathan Filaments", engine="attractor_web", eargs=dict(kind="dejong", layers=4), seed=31,
    base=(4, 13, 10), glow=(22, 140, 92), edge=(150, 255, 200),
    kw=dict(gamma=0.74, fill_gain=1.05, edge_gain=0.6, ambient=0.25, ambient_sigma=60, ambient_floor=0.22),
    desc="Layered de Jong attractor web in deep emerald — bioluminescent filaments edge to edge."),
 "ff_spectral_veil": dict(name="Spectral Veil", engine="attractor_web", eargs=dict(kind="clifford", layers=4), seed=5,
    base=(12, 5, 12), glow=(150, 40, 130), edge=(255, 150, 230),
    kw=dict(gamma=0.74, fill_gain=1.05, edge_gain=0.6, ambient=0.25, ambient_sigma=60, ambient_floor=0.22),
    desc="Layered Clifford attractor web in magenta — looping spectral veils across the canvas."),
 "ff_ghost_coil": dict(name="Ghost Coil", engine="strange_attractor", eargs=dict(kind="clifford"), seed=23,
    base=(6, 6, 16), glow=(72, 62, 168), edge=(195, 205, 255),
    kw=dict(gamma=0.7, fill_gain=1.05, edge_gain=0.5, ambient=0.35, ambient_sigma=60, ambient_floor=0.3),
    desc="Dense Clifford attractor — a coiled violet ghost-web of fine filaments."),
 "ff_riptide": dict(name="Riptide", engine="curl_flow", eargs={}, seed=9,
    base=(4, 9, 16), glow=(28, 80, 150), edge=(165, 222, 255),
    kw=dict(gamma=0.82, edge_gain=0.95),
    desc="Divergence-free curl-noise flow — fluid streamline currents in deep ocean blue."),
 "ff_fracture_web": dict(name="Fracture Web", engine="worley", eargs=dict(cells=340, kind="cracks"), seed=12,
    base=(11, 5, 3), glow=(125, 52, 15), edge=(255, 182, 92),
    kw=dict(gamma=1.0, edge_gain=0.85),
    desc="Voronoi fracture cracks (fine shards) in molten copper — intricate shattered tracery."),
 "ff_scale_mail": dict(name="Scale Mail", engine="worley", eargs=dict(kind="cells"), seed=17,
    base=(5, 11, 14), glow=(24, 96, 104), edge=(120, 200, 195),
    kw=dict(gamma=1.25, fill_gain=0.8, edge_gain=0.45),
    desc="Voronoi cellular scales in teal — armored chainmail plating."),
 "ff_stormfork": dict(name="Stormfork", engine="stormfork", eargs=dict(bolts=44), seed=21,
    base=(9, 5, 3), glow=(165, 82, 20), edge=(255, 210, 125),
    kw=dict(gamma=0.82, edge_gain=1.0, ambient=0.5, ambient_sigma=46, ambient_floor=0.4),
    desc="Dense branching Lichtenberg discharge — ember lightning forking into every corner."),
 "ff_drift_lattice": dict(name="Drift Lattice", engine="_drift", eargs={}, seed=14,
    base=(8, 6, 14), glow=(60, 90, 150), edge=(210, 200, 255),
    kw=dict(gamma=0.95, edge_gain=0.9),
    desc="Composition: 300-cell fracture advected by a curl flow — a drifting violet lattice."),
 "ff_quasicrystal": dict(name="Quasicrystal", engine="quasicrystal", eargs={}, seed=8,
    base=(6, 6, 16), glow=(60, 40, 150), edge=(150, 255, 245),
    kw=dict(gamma=1.0, edge_gain=1.1),
    desc="Crisp n-fold plane-wave quasicrystal interference — sharp aperiodic fringes."),
 "ff_marble": dict(name="Marble", engine="marble", eargs={}, seed=6,
    base=(12, 9, 4), glow=(155, 100, 30), edge=(255, 212, 130),
    kw=dict(gamma=0.95, edge_gain=0.8),
    desc="Domain-warped fBm + multi-scale veining in amber — dense turbulent marble."),
 "ff_truchet_flow": dict(name="Truchet Flow", engine="truchet", eargs={}, seed=4,
    base=(4, 10, 14), glow=(26, 110, 130), edge=(170, 250, 255),
    kw=dict(gamma=1.0, edge_gain=1.0, ambient=0.7, ambient_sigma=42, ambient_floor=0.45),
    desc="Curved Truchet tiling — a flowing maze/circuit on a lit teal substrate."),
 "ff_conformal_lattice": dict(name="Conformal Lattice", engine="conformal_lattice", eargs={}, seed=2,
    base=(10, 5, 2), glow=(142, 74, 22), edge=(255, 190, 100),
    kw=dict(gamma=1.0, edge_gain=1.0),
    desc="A lattice of conformal singularities (w=Σ1/(z-pk)) — copper swirl-medallions tiling the canvas."),
 # ── Wave 2 ───────────────────────────────────────────────────────────────
 "ff_loomwork": dict(name="Loomwork", engine="gabor_weave", eargs={}, seed=7,
    base=(10, 7, 3), glow=(150, 95, 30), edge=(255, 205, 120),
    kw=dict(gamma=1.0, edge_gain=0.8),
    desc="Anisotropic Gabor thread bands woven over/under — bronze fabric weave."),
 "ff_sunwheel": dict(name="Sunwheel", engine="phyllotaxis", eargs={}, seed=11,
    base=(6, 9, 5), glow=(130, 120, 26), edge=(235, 255, 140),
    kw=dict(gamma=0.85, edge_gain=0.9, ambient=0.6, ambient_sigma=58, ambient_floor=0.4),
    desc="Vogel golden-angle phyllotaxis seed-cell mosaic — a full sunflower-head floret packing."),
 "ff_apollonia": dict(name="Apollonia", engine="apollonian", eargs={}, seed=4,
    base=(12, 7, 5), glow=(180, 92, 66), edge=(255, 214, 170),
    kw=dict(gamma=1.0, edge_gain=1.0, ambient=0.4, ambient_sigma=46, ambient_floor=0.32),
    desc="Dense rim-lit bubble packing in peach/rose-gold — glassy nested rings."),
 "ff_pentangle": dict(name="Pentangle", engine="pentagrid", eargs={}, seed=9,
    base=(8, 5, 14), glow=(92, 50, 152), edge=(212, 182, 255),
    kw=dict(gamma=1.0, edge_gain=1.0),
    desc="de Bruijn pentagrid — Penrose-like aperiodic 5-fold ribbons in violet."),
 "ff_ridgeline": dict(name="Ridgeline", engine="ridged_terrain", eargs={}, seed=6,
    base=(9, 5, 3), glow=(122, 56, 20), edge=(255, 190, 110),
    kw=dict(gamma=0.9, edge_gain=0.7),
    desc="Ridged multifractal — sharp molten mountain-ridge veins in orange."),
 "ff_pendulum_veil": dict(name="Pendulum Veil", engine="harmonograph", eargs={}, seed=14,
    base=(4, 8, 14), glow=(30, 92, 152), edge=(170, 225, 255),
    kw=dict(gamma=0.85, edge_gain=0.85, ambient=0.6, ambient_sigma=58, ambient_floor=0.4),
    desc="Overlaid damped harmonograph ribbons on a textured ground — spirograph lacework."),
 "ff_causticline": dict(name="Causticline", engine="caustics", eargs={}, seed=3,
    base=(3, 9, 11), glow=(26, 122, 130), edge=(172, 255, 250),
    kw=dict(gamma=0.95, edge_gain=0.9, ambient=0.45, ambient_sigma=58, ambient_floor=0.4),
    desc="Refracted-ray bunching — a pool-light caustic network in aqua."),
 "ff_vortex_choir": dict(name="Vortex Choir", engine="spiral_waves", eargs=dict(vortices=7, k=26.0), seed=8,
    base=(10, 5, 12), glow=(132, 36, 122), edge=(255, 162, 236),
    kw=dict(gamma=1.0, edge_gain=1.15, ambient=0.42, ambient_sigma=55, ambient_floor=0.3),
    desc="Kuramoto phase-oscillator spiral waves — a sculpted 3D magenta swirl with layered fine detail."),
 "ff_heartwood": dict(name="Heartwood", engine="wood_grain", eargs={}, seed=5,
    base=(10, 6, 3), glow=(122, 72, 28), edge=(232, 172, 92),
    kw=dict(gamma=1.0, edge_gain=0.7),
    desc="Warped concentric rings + streaks — rich wood grain."),
 "ff_dragonscale": dict(name="Dragonscale", engine="dragonscale", eargs={}, seed=12,
    base=(10, 6, 3), glow=(150, 96, 34), edge=(255, 200, 120),
    kw=dict(gamma=1.0, edge_gain=0.85),
    desc="Staggered overlapping arc-scales (seigaiha) with per-scale shading — bronze dragon scales."),
 "ff_rosetta_moire": dict(name="Rosetta Moire", engine="moire", eargs={}, seed=2,
    base=(4, 8, 13), glow=(30, 92, 142), edge=(172, 226, 255),
    kw=dict(gamma=1.0, edge_gain=0.95),
    desc="Two offset concentric ring-gratings — hypnotic moire interference rosettes."),
 "ff_dactyl": dict(name="Dactyl", engine="flow_labyrinth", eargs={}, seed=16,
    base=(7, 7, 14), glow=(72, 72, 152), edge=(192, 212, 255),
    kw=dict(gamma=1.0, edge_gain=0.9, ambient=0.5, ambient_sigma=50, ambient_floor=0.38),
    desc="Curl-oriented relaxation — fingerprint / labyrinth ridges in violet."),
 "ff_shroud_silk": dict(name="Shroud Silk", engine="spectral_silk", eargs={}, seed=1,
    base=(8, 7, 12), glow=(92, 78, 124), edge=(222, 212, 246),
    kw=dict(gamma=1.05, edge_gain=0.8),
    desc="Anisotropic power-law Fourier noise — directional brushed silk sheen."),
 "ff_gyre": dict(name="Gyre", engine="gyroid", eargs={}, seed=10,
    base=(4, 11, 9), glow=(26, 122, 96), edge=(162, 255, 222),
    kw=dict(gamma=0.95, edge_gain=0.85),
    desc="Wavy slice of a gyroid minimal surface — an organic emerald lattice."),
 "ff_resonance": dict(name="Resonance", engine="chladni", eargs={}, seed=15,
    base=(10, 8, 3), glow=(150, 110, 28), edge=(255, 224, 130),
    kw=dict(gamma=1.0, edge_gain=0.9),
    desc="Chladni plate vibration — sand on the nodal lines of standing modes, in brass."),
 # ── Wave 3 — the INVENTED engines (calling card) ─────────────────────────
 "ff_phase_reliquary": dict(name="Phase Reliquary", engine="phase_reliquary", eargs={}, seed=5,
    base=(4, 6, 14), glow=(44, 74, 162), edge=(182, 228, 255),
    kw=dict(gamma=0.9, edge_gain=0.85, ambient=0.45, ambient_sigma=54, ambient_floor=0.36),
    desc="INVENTED — phase singularities of attractor-sampled complex plane-waves: an isotropic speckle filigree."),
 "ff_mycelinth": dict(name="Mycelinth", engine="mycelinth", eargs={}, seed=9,
    base=(4, 10, 10), glow=(24, 122, 110), edge=(172, 255, 240),
    kw=dict(gamma=1.0, edge_gain=0.95, ambient=0.5, ambient_sigma=50, ambient_floor=0.4),
    desc="INVENTED — a shock-filter growth PDE on a multifractal: self-organizing teal vein walls."),
 "ff_hyperflora": dict(name="Hyperflora", engine="hyperflora", eargs={}, seed=3,
    base=(8, 5, 12), glow=(122, 46, 132), edge=(255, 182, 236),
    kw=dict(gamma=0.95, edge_gain=0.9),
    desc="INVENTED — a 5-fold x 7-fold quasicrystal as one complex field: tight non-repeating florets."),
 "ff_soliton_reef": dict(name="Soliton Reef", engine="soliton_reef", eargs={}, seed=7,
    base=(6, 8, 10), glow=(120, 72, 86), edge=(255, 198, 168),
    kw=dict(gamma=0.9, edge_gain=0.95),
    desc="INVENTED — a new transcendental escape-time fractal under z -> sin(z)+c/z: rose-gold damask coral."),
 "ff_aurora_loom": dict(name="Aurora Loom", engine="aurora_loom", eargs={}, seed=11,
    base=(4, 9, 12), glow=(28, 122, 118), edge=(180, 255, 234),
    kw=dict(gamma=0.85, edge_gain=0.9, ambient=0.35, ambient_sigma=60, ambient_floor=0.3),
    desc="INVENTED — curl flow advecting particles through an attractor-seeded interference phase: woven aurora."),
 # ── FORGE-100 expansion · F1 flow fusions ──
 "ff_tideglass_gyre": dict(name="Tideglass Gyre", engine="gyroid_flow", eargs={}, seed=301,
    base=(4, 11, 10), glow=(28, 120, 110), edge=(165, 255, 225), kw=dict(gamma=0.95, edge_gain=0.9),
    desc="A gyroid lattice swept into flowing currents by a curl field — liquid emerald glass."),
 "ff_magma_current": dict(name="Magma Current", engine="ridge_flow", eargs={}, seed=302,
    base=(9, 4, 2), glow=(180, 80, 20), edge=(255, 190, 90), kw=dict(gamma=0.85, edge_gain=0.85),
    sargs=dict(ignition=1.2, calm_floor=24.0),
    desc="Ridged-multifractal lava ridges advected into molten flowing currents."),
 "ff_liquid_agate": dict(name="Liquid Agate", engine="marble_flow", eargs={}, seed=303,
    base=(8, 5, 11), glow=(120, 60, 130), edge=(245, 200, 150), kw=dict(gamma=0.95, edge_gain=0.8),
    desc="Domain-warped marble pulled into a slow amethyst-and-gold liquid swirl."),
 "ff_hivewake": dict(name="Hivewake", engine="hex_flow", eargs={}, seed=304,
    base=(9, 7, 3), glow=(160, 110, 30), edge=(255, 215, 110), kw=dict(gamma=1.0, edge_gain=0.7),
    desc="A honeycomb lattice rippling in a warm amber current — melting hive."),
 "ff_resonant_tide": dict(name="Resonant Tide", engine="chladni_flow", eargs={}, seed=305,
    base=(5, 7, 12), glow=(60, 90, 150), edge=(180, 210, 255), kw=dict(gamma=0.95, edge_gain=0.85),
    desc="Chladni nodal figures dissolved into flowing standing-wave tides."),
 "ff_watered_silk": dict(name="Watered Silk", engine="silk_flow", eargs={}, seed=306,
    base=(10, 7, 9), glow=(140, 90, 110), edge=(250, 220, 225), kw=dict(gamma=1.0, edge_gain=0.7),
    desc="Directional Fourier silk rippled by a curl flow — rose-pearl watered silk."),
 "ff_quasiflux": dict(name="Quasiflux", engine="quasi_flow", eargs={}, seed=307,
    base=(5, 6, 14), glow=(40, 90, 150), edge=(170, 235, 250), kw=dict(gamma=1.0, edge_gain=1.0),
    desc="A quasicrystal interference field bent into flowing aperiodic flux lines."),
 "ff_conduit": dict(name="Conduit", engine="lattice_flow", eargs={}, seed=308,
    base=(5, 8, 11), glow=(50, 100, 130), edge=(175, 225, 250), kw=dict(gamma=1.0, edge_gain=1.05),
    desc="An isometric strut lattice warped into flowing steel conduits."),
 # ── FORGE-100 · MULTI-HUE TRACED CELLS (owner request: outline ignites, interiors fire multi-colour) ──
 "ff_prism_glass": dict(name="Prism Glass", engine="prism_glass",
    eargs=dict(cells=55, palette=[(120, 40, 165), (28, 140, 95), (38, 90, 205)], edge=(185, 235, 255)), seed=311,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.25, trace_strength=1.7, calm_floor=20.0),
    desc="Stained-glass Voronoi panes — purple, green and blue at shifting shades behind a bright leading that ignites at angle."),
 "ff_spectral_hive": dict(name="Spectral Hive", engine="spectral_hive",
    eargs=dict(cells=34, palette=[(30, 150, 140), (150, 50, 160), (190, 140, 30)], edge=(200, 240, 255)), seed=312,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Hex hive cells in teal, violet and amber shades, each ringed by a bright ignitable rim."),
 "ff_prism_shatter": dict(name="Prism Shatter", engine="prism_shatter",
    eargs=dict(cells=85, palette=[(40, 90, 205), (160, 40, 150), (30, 150, 150)], edge=(225, 240, 255)), seed=313,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.25, trace_strength=1.8, calm_floor=18.0),
    desc="Angular shattered shards in blue, magenta and teal shades — fault-lines ignite white-bright."),
 "ff_mosaic_drift": dict(name="Mosaic Drift", engine="mosaic_drift",
    eargs=dict(cells=70, palette=[(40, 140, 70), (175, 120, 30), (195, 70, 30)], edge=(255, 225, 130)), seed=314,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.6, calm_floor=22.0),
    desc="A curl-drifted mosaic of green, gold and ember tiles seamed by a glowing gold lattice."),
 # ── F2 · 3 more multi-hue traced cells + 5 cellular fusions ──
 "ff_spectra_wheel": dict(name="Spectra Wheel", engine="spectra_wheel",
    eargs=dict(sectors=28, rings=7, palette=[(200, 40, 140), (30, 160, 180), (220, 160, 30)], edge=(245, 245, 255)), seed=321,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.25, trace_strength=1.7, calm_floor=20.0),
    desc="A shattered colour-wheel — magenta, cyan and gold radial wedges behind bright ignitable spokes."),
 "ff_brickwork_prism": dict(name="Brickwork Prism", engine="brickwork_prism",
    eargs=dict(cols=14, palette=[(190, 90, 40), (160, 130, 40), (40, 120, 120)], edge=(255, 225, 150)), seed=322,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Offset brick courses in rust, ochre and teal shades with glowing mortar that ignites at angle."),
 "ff_scale_prism": dict(name="Scale Prism", engine="scale_prism",
    eargs=dict(rows=15, palette=[(40, 150, 120), (90, 60, 170), (180, 110, 40)], edge=(210, 245, 255)), seed=323,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Staggered rounded scales in jade, indigo and copper shades, each rimmed by a bright ignitable edge."),
 "ff_wovencell": dict(name="Wovencell", engine="wovencell", eargs={}, seed=324,
    base=(8, 6, 4), glow=(140, 100, 50), edge=(240, 200, 140), kw=dict(gamma=1.0, edge_gain=0.75),
    desc="Voronoi cells woven through a Gabor thread field — a cellular bronze textile."),
 "ff_geode_facet": dict(name="Geode Facet", engine="geode_facet", eargs={}, seed=325,
    base=(6, 6, 12), glow=(90, 70, 140), edge=(190, 220, 255), kw=dict(gamma=0.95, edge_gain=0.9),
    desc="Faceted crystal cells veined by domain-warped marble — amethyst geode facets."),
 "ff_shardfield": dict(name="Shardfield", engine="shardfield", eargs=dict(cells=140), seed=326,
    base=(5, 7, 12), glow=(50, 90, 150), edge=(190, 225, 255), kw=dict(gamma=1.0, edge_gain=1.0),
    desc="Chebyshev-Voronoi angular shard fractures — an ice-blue shattered field."),
 "ff_cellwave": dict(name="Cellwave", engine="cellwave", eargs={}, seed=327,
    base=(4, 10, 9), glow=(30, 120, 100), edge=(160, 255, 210), kw=dict(gamma=0.95, edge_gain=0.85),
    desc="Voronoi cells modulated by radial wave interference — emerald cells pulsing under moire."),
 "ff_resonant_cells": dict(name="Resonant Cells", engine="resonant_cells", eargs={}, seed=328,
    base=(9, 5, 3), glow=(150, 90, 35), edge=(255, 200, 120), kw=dict(gamma=0.95, edge_gain=0.85),
    sargs=dict(ignition=1.15, calm_floor=24.0),
    desc="Chladni nodal lines fracturing a copper cell network — resonant cracked plates."),
 # ── F3 · 3 more multi-hue traced cells + 5 wave/optical fusions ──
 "ff_aura_rings": dict(name="Aura Rings", engine="aura_rings",
    eargs=dict(rings=14, sectors=10, palette=[(210, 140, 30), (190, 50, 90), (80, 60, 180)], edge=(250, 245, 255)), seed=331,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.25, trace_strength=1.7, calm_floor=20.0),
    desc="Concentric aura ring-bands in gold, rose and indigo shades, ringed by bright ignitable lines."),
 "ff_trihedra": dict(name="Trihedra", engine="trihedra",
    eargs=dict(cells=14, palette=[(30, 160, 170), (150, 200, 40), (180, 40, 150)], edge=(230, 245, 255)), seed=332,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Triangular tiling in cyan, lime and magenta shades with bright ignitable edges."),
 "ff_spiral_prism": dict(name="Spiral Prism", engine="spiral_prism",
    eargs=dict(arms=9, twist=8, palette=[(30, 150, 140), (110, 60, 180), (200, 130, 40)], edge=(245, 240, 255)), seed=333,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.25, trace_strength=1.7, calm_floor=20.0),
    desc="Logarithmic-spiral arms in teal, violet and amber shades, seamed by bright ignitable spirals."),
 "ff_holo_grating": dict(name="Holo Grating", engine="holo_grating", eargs=dict(gratings=5), seed=334,
    base=(5, 5, 12), glow=(70, 50, 150), edge=(190, 230, 255), kw=dict(gamma=1.0, edge_gain=1.1),
    desc="Superposed diffraction gratings — a spectral holographic interference field."),
 "ff_newton_bloom": dict(name="Newton Bloom", engine="newton_bloom", eargs={}, seed=335,
    base=(4, 8, 10), glow=(50, 110, 120), edge=(190, 220, 255), kw=dict(gamma=0.95, edge_gain=0.9),
    desc="Oil-film Newton's rings advected into blooming petrol halos."),
 "ff_standing_field": dict(name="Standing Field", engine="standing_field", eargs={}, seed=336,
    base=(6, 5, 12), glow=(90, 55, 150), edge=(200, 180, 255), kw=dict(gamma=0.95, edge_gain=0.9),
    desc="Chladni nodal figures crossed with radial interference — a violet standing-wave field."),
 "ff_moire_vortex": dict(name="Moire Vortex", engine="moire_vortex", eargs={}, seed=337,
    base=(4, 7, 13), glow=(40, 95, 150), edge=(175, 225, 255), kw=dict(gamma=1.0, edge_gain=0.95),
    desc="Moire ring-gratings wound through a spiral phase — a hypnotic blue vortex interference."),
 "ff_caustic_lace": dict(name="Caustic Lace", engine="caustic_lace", eargs={}, seed=338,
    base=(4, 9, 10), glow=(40, 120, 110), edge=(255, 230, 160), kw=dict(gamma=0.95, edge_gain=0.9),
    desc="A caustic light-net draped over Voronoi cells — aqua-and-gold pooled light lace."),
 # ── F4 · 3 more multi-hue traced cells + 5 optical/iridescent fusions ──
 "ff_cubist_prism": dict(name="Cubist Prism", engine="cubist_prism",
    eargs=dict(splits=170, palette=[(190, 95, 35), (40, 125, 120), (175, 150, 40)], edge=(255, 225, 150)), seed=341,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A cubist mosaic of rust, teal and ochre rectangle panels seamed by glowing ignitable mortar."),
 "ff_pinwheel_glass": dict(name="Pinwheel Glass", engine="pinwheel_glass",
    eargs=dict(cells=8, palette=[(60, 70, 185), (30, 150, 175), (120, 55, 175)], edge=(200, 245, 255)), seed=342,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.25, trace_strength=1.7, calm_floor=20.0),
    desc="Square panes each split into four pinwheel wedges — indigo, cyan and violet shades behind bright ignitable spokes."),
 "ff_aurora_basins": dict(name="Aurora Basins", engine="aurora_basins",
    eargs=dict(cells=42, palette=[(30, 150, 110), (40, 110, 175), (120, 60, 170)], edge=(205, 255, 225)), seed=343,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=22.0),
    desc="Curved weighted-Voronoi basins in emerald, blue and violet shades, rimmed by pale ignitable aurora lines."),
 "ff_oilskin_weave": dict(name="Oilskin Weave", engine="oilfilm_weave", eargs={}, seed=344,
    base=(4, 8, 10), glow=(30, 95, 120), edge=(180, 150, 235), kw=dict(gamma=0.95, edge_gain=0.72),
    desc="Thin-film petrol iridescence rippling through a woven thread field — oil-on-silk sheen."),
 "ff_dichroic_drift": dict(name="Dichroic Drift", engine="dichroic_drift", eargs={}, seed=345,
    base=(6, 5, 12), glow=(120, 40, 150), edge=(90, 205, 220), kw=dict(gamma=1.0, edge_gain=0.78),
    desc="Thin-film dichroic bands advected by a curl flow — magenta-to-cyan colour-shifting drift."),
 "ff_prism_facet": dict(name="Prism Facet", engine="prism_facet", eargs={}, seed=346,
    base=(5, 7, 12), glow=(60, 110, 150), edge=(210, 235, 255), kw=dict(gamma=0.95, edge_gain=0.95),
    desc="Crystal facets lit by plane-wave interference — an icy prism scattering cold spectral glints."),
 "ff_peacock_optic": dict(name="Peacock", engine="peacock_optic", eargs={}, seed=347,
    base=(3, 10, 8), glow=(22, 120, 88), edge=(220, 195, 70), kw=dict(gamma=0.95, edge_gain=0.9),
    desc="Newton-ring ocelli swept through a vortex — packed emerald-and-gold peacock eyes."),
 "ff_spectral_ridge": dict(name="Spectral Ridge", engine="thinfilm_ridge", eargs={}, seed=348,
    base=(8, 6, 11), glow=(110, 70, 140), edge=(95, 210, 200), kw=dict(gamma=0.95, edge_gain=0.78),
    desc="Thin-film spectral bands draped over sharp ridges — iridescent violet-and-teal mountain veins."),
 # ── F5 · 3 more multi-hue traced cells + 5 organic/natural fusions ──
 "ff_parquet_glass": dict(name="Parquet Glass", engine="parquet_glass",
    eargs=dict(cells=10, palette=[(150, 95, 45), (110, 65, 35), (170, 140, 60)], edge=(255, 225, 150)), seed=351,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Basketweave parquet of interlocking tiles in oak, walnut and brass shades, seamed by glowing ignitable grout."),
 "ff_crackle_glaze": dict(name="Crackle Glaze", engine="crackle_glaze",
    eargs=dict(cells=42, palette=[(60, 150, 140), (205, 200, 175), (40, 90, 170)], edge=(245, 250, 255)), seed=352,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.25, trace_strength=1.7, calm_floor=20.0),
    desc="Irregular ceramic craquelure plates in celadon, cream and cobalt shades, crazed by bright ignitable crack-lines."),
 "ff_catacomb_glass": dict(name="Catacomb Glass", engine="catacomb_glass",
    eargs=dict(cells=16, palette=[(70, 80, 160), (150, 60, 150), (180, 120, 50)], edge=(235, 235, 250)), seed=353,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=22.0),
    desc="Merged maze-room cells (dominoes and L-shapes) in slate-blue, violet and ember shades behind bright ignitable walls."),
 "ff_brain_coral": dict(name="Brain Coral", engine="coral_marble", eargs={}, seed=354,
    base=(12, 5, 6), glow=(190, 80, 90), edge=(255, 180, 150), kw=dict(gamma=0.95, edge_gain=0.8),
    desc="A Gray-Scott coral Turing labyrinth veined by marble — convoluted coral-pink brain coral."),
 "ff_banded_agate": dict(name="Banded Agate", engine="agate_band", eargs={}, seed=355,
    base=(10, 7, 4), glow=(150, 100, 40), edge=(190, 230, 235), kw=dict(gamma=0.95, edge_gain=0.9),
    desc="Concentric geode growth bands gently warped — a sliced amber-and-teal banded agate."),
 "ff_leaf_vein": dict(name="Leaf Vein", engine="leaf_vein", eargs={}, seed=356,
    base=(5, 11, 5), glow=(60, 130, 40), edge=(200, 230, 120), kw=dict(gamma=0.95, edge_gain=0.78),
    desc="A bright vein network bounding translucent cells over marble — backlit leaf venation."),
 "ff_plumage": dict(name="Plumage", engine="feather_flow", eargs={}, seed=357,
    base=(4, 10, 12), glow=(30, 110, 130), edge=(170, 210, 255), kw=dict(gamma=1.0, edge_gain=0.7),
    desc="Feather fans drifting through a curl flow — layered teal-and-blue plumage."),
 "ff_dendrite_frost": dict(name="Dendrite Frost", engine="dendrite_frost", eargs={}, seed=358,
    base=(6, 9, 14), glow=(60, 110, 160), edge=(210, 235, 255), kw=dict(gamma=0.95, edge_gain=0.85),
    desc="Window-frost fern dendrites sharpened over ridges — crystalline icy-blue frost."),
 # ── F6 · 3 more multi-hue traced cells + 5 geometric/tech fusions ──
 "ff_truchet_glass": dict(name="Truchet Glass", engine="truchet_glass",
    eargs=dict(tiles=10, palette=[(30, 150, 170), (60, 80, 190), (130, 55, 175)], edge=(200, 245, 255)), seed=361,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.25, trace_strength=1.7, calm_floor=20.0),
    desc="Truchet curved-arc tiles in teal, blue and violet shades, flowing behind bright ignitable arc-seams."),
 "ff_argyle_glass": dict(name="Argyle Glass", engine="argyle_glass",
    eargs=dict(cells=9, palette=[(180, 90, 40), (160, 135, 45), (40, 120, 115)], edge=(255, 230, 170)), seed=362,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A diagonal argyle diamond lattice in rust, gold and teal shades laced by bright ignitable cross-seams."),
 "ff_ziggurat_glass": dict(name="Ziggurat Glass", engine="ziggurat_glass",
    eargs=dict(cells=6, rings=4, palette=[(60, 90, 175), (40, 150, 160), (140, 60, 170)], edge=(220, 235, 255)), seed=363,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=22.0),
    desc="A grid of nested-square frame stacks in steel-blue, cyan and violet shades, stepped by bright ignitable frame-lines."),
 "ff_penrose_quartz": dict(name="Penrose Quartz", engine="penrose_quartz", eargs={}, seed=364,
    base=(6, 6, 14), glow=(70, 55, 160), edge=(180, 225, 255), kw=dict(gamma=1.0, edge_gain=1.0),
    desc="Aperiodic Penrose rhombus tiles lit by plane-wave interference — a faceted violet quartz lattice."),
 "ff_tracewerk": dict(name="Tracewerk", engine="tracewerk", eargs={}, seed=365,
    base=(3, 9, 6), glow=(30, 140, 70), edge=(220, 200, 90), kw=dict(gamma=0.95, edge_gain=0.9),
    desc="PCB circuit traces glowing under a soft caustic bloom — a lit green-and-gold circuit board."),
 "ff_quicksilver": dict(name="Quicksilver", engine="isogrid", eargs={}, seed=366,
    base=(5, 8, 11), glow=(50, 100, 135), edge=(180, 220, 245), kw=dict(gamma=0.95, edge_gain=0.85),
    desc="A Schwarz-P minimal-surface lattice of rounded interlocking cells — pooled liquid-chrome quicksilver."),
 "ff_knurled_steel": dict(name="Knurled Steel", engine="knurl_flash", eargs={}, seed=367,
    base=(7, 7, 9), glow=(95, 100, 115), edge=(210, 180, 120), kw=dict(gamma=1.0, edge_gain=0.85),
    desc="A diamond knurl lit by plane-wave interference — machined gunmetal catching amber light."),
 "ff_guilloche": dict(name="Guilloché", engine="guilloche_drift", eargs={}, seed=368,
    base=(6, 9, 7), glow=(120, 95, 40), edge=(90, 200, 150), kw=dict(gamma=0.95, edge_gain=0.9),
    desc="Guilloché engine-turned rosettes gently warped — drifting copper-and-mint banknote engraving."),
 # ── F7 · 3 more multi-hue traced cells + 5 cosmic/energy fusions ──
 "ff_cobble_glass": dict(name="Cobble Glass", engine="cobble_glass",
    eargs=dict(n=9, palette=[(170, 95, 55), (150, 140, 80), (80, 120, 70)], edge=(250, 235, 190)), seed=371,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Evenly-spaced cobblestone Voronoi cells in terracotta, sand and moss shades, set in bright ignitable mortar."),
 "ff_iceshard": dict(name="Iceshard", engine="iceshard",
    eargs=dict(cells=70, palette=[(40, 140, 180), (70, 90, 200), (140, 90, 200)], edge=(235, 245, 255)), seed=372,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.25, trace_strength=1.8, calm_floor=18.0),
    desc="Manhattan-metric diamond/kite shards in cyan, blue and violet shades, split by bright ignitable fractures."),
 "ff_tartan_glass": dict(name="Tartan Glass", engine="tartan_glass",
    eargs=dict(n=9, palette=[(160, 50, 45), (40, 110, 70), (40, 60, 130)], edge=(220, 190, 90)), seed=373,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=22.0),
    desc="An irregular tartan of red, forest and navy rectangles crossed by bright ignitable gold thread-lines."),
 "ff_nebula": dict(name="Nebula", engine="nebula_cloud", eargs={}, seed=374,
    base=(5, 4, 12), glow=(120, 40, 140), edge=(90, 200, 230), kw=dict(gamma=0.9, edge_gain=0.85, ambient=0.4, ambient_sigma=58, ambient_floor=0.34),
    desc="Plasma-ball ion clouds turbulated by marble — a deep-space magenta-and-cyan nebula."),
 "ff_ion_bloom": dict(name="Ion Bloom", engine="ion_bloom", eargs={}, seed=375,
    base=(3, 8, 12), glow=(30, 120, 150), edge=(190, 160, 255), kw=dict(gamma=0.9, edge_gain=0.9, ambient=0.4, ambient_sigma=55, ambient_floor=0.32),
    desc="Glowing bokeh orbs blooming over a plasma field — drifting cyan-and-violet ions."),
 "ff_plasma_arc": dict(name="Plasma Arc", engine="plasma_arc", eargs={}, seed=376,
    base=(4, 6, 14), glow=(60, 90, 200), edge=(200, 225, 255), kw=dict(gamma=0.85, edge_gain=1.05, ambient=0.45, ambient_sigma=50, ambient_floor=0.38),
    desc="Branching Lichtenberg discharge crackling over a plasma glow — high-voltage electric-blue arcs."),
 "ff_aurora_veil": dict(name="Aurora Veil", engine="aurora_veil", eargs={}, seed=377,
    base=(3, 10, 9), glow=(30, 150, 110), edge=(160, 120, 230), kw=dict(gamma=0.9, edge_gain=0.85),
    desc="Aurora curtains curl-warped into rippling omnidirectional veils — green-and-violet northern lights."),
 "ff_spiral_galaxy": dict(name="Spiral Galaxy", engine="spiral_galaxy", eargs={}, seed=378,
    base=(5, 5, 12), glow=(130, 70, 150), edge=(230, 210, 150), kw=dict(gamma=0.9, edge_gain=0.95, ambient=0.4, ambient_sigma=55, ambient_floor=0.32),
    desc="Scattered spiral-wave swirls salted with bokeh stars — a field of purple-and-gold mini galaxies."),
}


def _seed_int(seed):
    try:
        return int(seed)
    except Exception:
        return abs(hash(str(seed))) % (2 ** 31)


def _field(d, work):
    eng = d["engine"]
    fn = _drift if eng == "_drift" else getattr(fm, eng)
    return fn(work, work, _seed_int(d["seed"]), **d.get("eargs", {}))


def _art_work(d):
    """Compute the FRACTURED art at work resolution (0..1 HxWx3). Engines that return a scalar
    field get colorize()'d; multi-hue engines that already return RGB (HxWx3) pass straight through."""
    field = _field(d, _WORK)
    if getattr(field, "ndim", 0) == 3:          # multi-hue traced-cell engine -> RGB already
        return np.clip(field, 0.0, 1.0)
    return np.clip(fm.colorize(field, d["base"], d["glow"], d["edge"], **d["kw"]), 0.0, 1.0)


@lru_cache(maxsize=6)
def _art_work_cached(fid):
    """Work-res art is deterministic per finish and render-size-independent, so memoize it:
    paint_fn + spec_fn for the same finish then share one (sometimes ~1.7s) compute instead of two.
    Small LRU bounds memory; resize downstream returns fresh arrays so the cached one is never mutated."""
    return _art_work(FORGE[fid])


def _mk(fid):
    d = FORGE[fid]

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and src.max() > 1.5:
            src = src / 255.0
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        art = cv2.resize(_art_work_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        # FORGE finishes are full procedural patterns: the art IS the look (full replace in-mask).
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        out = src * (1.0 - kk) + art * kk
        return np.clip(out, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        art = cv2.resize(_art_work_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        # canonical FRACTURED ignition traced from the art's own geometry; decorrelation keeps
        # the M/R/Cc channels distinct (helps each finish clear the uniqueness gate).
        return fracture_spec(art, m2, ignition=1.0, decorrelation=0.18, as_uint8=True)

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Register the FORGE finishes into the monolithic registry + the UI group-map registries
    (fusions.FUSION_REGISTRY + the live engine FUSION_REGISTRY), mirroring spectrum_shift_2026."""
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
    _removed = {"ff_prism_glass", "ff_prism_shatter", "ff_mosaic_drift", "ff_aura_rings", "ff_spiral_prism",
                "ff_newton_bloom", "ff_aurora_basins", "ff_prism_facet", "ff_crackle_glaze", "ff_plumage",
                "ff_dendrite_frost", "ff_guilloche", "ff_cobble_glass", "ff_iceshard", "ff_tartan_glass"}  # owner pre-ship cull 2026-06-17
    n = 0
    for fid in FORGE:
        if fid in _removed:
            continue
        entry = _mk(fid)
        for reg in regs:
            reg[fid] = entry
        n += 1
    return f"fractured-forge: {n} math-engine finishes live ({_GROUP})"
