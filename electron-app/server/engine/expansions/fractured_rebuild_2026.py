"""FRACTURED MINDS + SOULS REBUILD (2026-06-17) — owner audit: most MINDS/SOULS had their named
pattern absent/weak/duplicate. This module OVERRIDES those fm_/fs_ entries with bespoke per-name
generators (each genuinely produces what its name says), a palette that stands out, and a spec
that traces + complements that exact pattern (Wovenlight ignition). Installs LAST so it wins.

Single source of truth = the RECIPES dict (filled in batches by the overnight rebuild loop).
Same contract as fractured_forge_2026 / fractured_souls_2026:  reg[id] = (spec_fn, paint_fn).
Engines live in engine/paint_v2/fractured_math.py (one bespoke generator per named look).
KEEPERS (never overridden): fs_core_*, fs_soul_loom.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

import engine.paint_v2.fractured_math as fm
from engine.spec_sculpt.fracture import fracture_spec

_WORK = 1152

KEEPERS = {"fs_core_violet", "fs_core_abyss", "fs_core_emerald", "fs_core_crimson",
           "fs_core_aurum", "fs_soul_loom"}

# Large-feature / low-contrast finishes whose spec didn't strongly trace the paint (gate advisory).
# Force a stronger ignition tracery + glossier floor so the spec still complements the pattern.
_TRACE_BOOST = {"fm_graphene", "fm_carbon_weave", "fm_croc_hide", "fm_gila_bead", "fm_tiger_slash",
                "fm_tessellate", "fm_gyroid", "fs_ghost_silk", "fs_moire_phantom"}


def _drift(h, w, s):
    a = fm.worley(h, w, s, cells=300, kind="cracks")
    b = fm.curl_flow(h, w, s + 101)
    return fm._norm(a * (0.45 + 0.55 * b))


# id -> recipe.  engine = fractured_math fn name (or "_drift"); eargs = extra engine kwargs.
# spec defaults to fracture_spec(ignition, decorrelation); override per-recipe with sargs.
RECIPES = {
 "fm_magma": dict(name="Magma", engine="magma", eargs=dict(plates=180), seed=36,
    base=(10, 3, 1), glow=(205, 70, 8), edge=(255, 210, 70),
    kw=dict(gamma=0.85, fill_gain=1.0, edge_gain=1.2),
    sargs=dict(ignition=1.2, calm_floor=26.0),
    desc="Cooled basalt crust split by glowing molten cracks — true lava (orange/yellow), not the old blue speckle."),
 "fm_inferno_veins": dict(name="Inferno Veins", engine="lava_veins", eargs={}, seed=44,
    base=(10, 2, 2), glow=(215, 42, 12), edge=(255, 205, 110),
    kw=dict(gamma=0.68, fill_gain=1.15, edge_gain=1.45),
    sargs=dict(ignition=1.3, calm_floor=24.0),
    desc="A dendritic web of white-hot crest-veins glowing through dark rock — branching inferno (distinct from magma's cells)."),
 "fm_flame_helix": dict(name="Flame Helix", engine="flame_helix", eargs=dict(arms=5), seed=51,
    base=(11, 3, 2), glow=(205, 62, 10), edge=(255, 205, 70),
    kw=dict(gamma=0.88, edge_gain=1.1),
    sargs=dict(ignition=1.15, calm_floor=26.0),
    desc="Spiralling helical fire vortex — winding flame arms swirling from a turbulent core."),
 "fm_flame_lick": dict(name="Flame Lick", engine="flame_tongues", eargs=dict(n=150), seed=52,
    base=(8, 3, 1), glow=(212, 92, 14), edge=(255, 222, 92),
    kw=dict(gamma=0.9, edge_gain=1.05, ambient=0.3, ambient_sigma=50, ambient_floor=0.28),
    sargs=dict(ignition=1.1, calm_floor=28.0),
    desc="Scattered discrete licking flame tongues at every angle on near-black — individual flames, not a field."),
 "fm_flame_wall": dict(name="Flame Wall", engine="flame_field", eargs={}, seed=53,
    base=(12, 4, 2), glow=(214, 84, 14), edge=(255, 198, 74),
    kw=dict(gamma=0.74, fill_gain=1.1, edge_gain=1.05),
    sargs=dict(ignition=1.2, calm_floor=26.0),
    desc="A dense roiling wall of curling fire — turbulent full-coverage flame sheet."),
 "fm_honeycomb_burst": dict(name="Honeycomb Burst", engine="hexgrid", eargs=dict(cells=11, mode="filled", burst=True), seed=61,
    base=(10, 7, 2), glow=(190, 130, 20), edge=(255, 226, 112),
    kw=dict(gamma=1.0, edge_gain=0.95),
    sargs=dict(ignition=1.0, calm_floor=30.0),
    desc="Golden honeycomb cells radiating/growing outward from the centre — amber hex burst."),
 "fm_hexcore": dict(name="Hexcore", engine="hexgrid", eargs=dict(cells=12, mode="beveled"), seed=62,
    base=(5, 9, 12), glow=(40, 110, 140), edge=(170, 235, 255),
    kw=dict(gamma=0.95, edge_gain=1.0),
    sargs=dict(ignition=1.0, calm_floor=28.0),
    desc="Beveled tech hex cells — a steel/cyan hexagonal core lattice."),
 "fm_graphene": dict(name="Graphene", engine="hexgrid", eargs=dict(cells=24, mode="lattice"), seed=63,
    base=(6, 7, 9), glow=(70, 80, 96), edge=(195, 208, 228),
    kw=dict(gamma=1.0, edge_gain=1.15),
    sargs=dict(ignition=1.0, trace_strength=1.6, calm_floor=22.0),
    desc="A fine hexagonal atomic wireframe lattice — graphite graphene mesh."),
 "fm_herringbone": dict(name="Herringbone", engine="herringbone", eargs=dict(unit=26), seed=71,
    base=(9, 8, 7), glow=(95, 88, 80), edge=(210, 200, 188),
    kw=dict(gamma=1.0, edge_gain=1.0), sargs=dict(trace_strength=1.3, calm_floor=28.0),
    desc="Chevron herringbone tweed — diagonal hatch flipping every row into interlocking V's."),
 "fm_basketweave": dict(name="Basketweave", engine="basketweave", eargs=dict(cells=10), seed=72,
    base=(13, 10, 4), glow=(160, 120, 40), edge=(245, 215, 130),
    kw=dict(gamma=1.0, edge_gain=1.0), sargs=dict(trace_strength=1.3, calm_floor=28.0),
    desc="True over/under basket weave — wheat-gold thread bundles crossing in a checker."),
 "fm_carbon_weave": dict(name="Carbon Weave", engine="carbon_twill", eargs=dict(cells=40), seed=73,
    base=(4, 5, 7), glow=(72, 84, 108), edge=(150, 170, 205),
    kw=dict(gamma=1.3, fill_gain=1.0, edge_gain=0.3), sargs=dict(trace_strength=2.0, calm_floor=18.0),
    desc="2x2 carbon-fibre twill — dark graphite diagonal ribs (field-driven, no edge flood)."),
 "fm_nanoweave": dict(name="Nanoweave", engine="knurl", eargs=dict(cells=34), seed=74,
    base=(9, 6, 4), glow=(150, 108, 58), edge=(225, 188, 130),
    kw=dict(gamma=1.05, fill_gain=1.05, edge_gain=0.35), sargs=dict(trace_strength=1.5, calm_floor=24.0),
    desc="Crossed-grating diamond knurl — warm titanium-bronze diamonds on dark."),
 "fm_cable_knit": dict(name="Cable Knit", engine="knit_cable", eargs=dict(cols=11), seed=75,
    base=(14, 12, 9), glow=(155, 138, 108), edge=(248, 236, 210),
    kw=dict(gamma=1.0, edge_gain=0.95), sargs=dict(trace_strength=1.2, calm_floor=30.0),
    desc="Cream wool cable knit — braided rounded cords with purl bumps."),
 "fm_chainmail": dict(name="Chainmail", engine="chainmail_rings", eargs=dict(rings=14), seed=76,
    base=(8, 9, 11), glow=(92, 100, 112), edge=(218, 228, 242),
    kw=dict(gamma=1.0, edge_gain=1.05), sargs=dict(trace_strength=1.3, calm_floor=26.0),
    desc="Interlocking riveted silver rings — 4-in-1 chainmail mesh."),
 "fm_chainlink": dict(name="Chainlink", engine="chainlink", eargs=dict(cells=24), seed=77,
    base=(7, 10, 11), glow=(66, 96, 100), edge=(185, 220, 225),
    kw=dict(gamma=1.0, edge_gain=1.15), sargs=dict(trace_strength=1.35, calm_floor=26.0),
    desc="Galvanized chainlink fence — thin diagonal wire diamonds woven over/under."),
 "fm_diamond_plate": dict(name="Diamond Plate", engine="diamond_plate", eargs=dict(cells=18), seed=78,
    base=(11, 9, 5), glow=(150, 112, 40), edge=(240, 205, 120),
    kw=dict(gamma=1.0, edge_gain=1.1), sargs=dict(trace_strength=1.3, calm_floor=24.0),
    desc="Raised brass tread plate — 4-way diamond treads on flat industrial metal."),
 "fm_croc_hide": dict(name="Croc Hide", engine="croc_hide", eargs=dict(cells=18), seed=81,
    base=(7, 9, 5), glow=(78, 96, 42), edge=(165, 188, 110),
    kw=dict(gamma=1.0, edge_gain=0.6), sargs=dict(trace_strength=1.3, calm_floor=30.0),
    desc="Crocodile scutes — bulging swamp-green plates separated by deep grooves."),
 "fm_python_skin": dict(name="Python Skin", engine="python_scales", eargs=dict(cells=26), seed=82,
    base=(10, 8, 5), glow=(122, 96, 56), edge=(228, 196, 142),
    kw=dict(gamma=1.0, edge_gain=0.5), sargs=dict(trace_strength=1.3, calm_floor=28.0),
    desc="Python skin — a tan/umber diamond scale lattice broken by dark blotch markings."),
 "fm_diamondback": dict(name="Diamondback", engine="diamondback", eargs=dict(cells=26), seed=83,
    base=(9, 8, 6), glow=(118, 100, 64), edge=(235, 214, 160),
    kw=dict(gamma=1.0, edge_gain=0.85), sargs=dict(trace_strength=1.3, calm_floor=28.0),
    desc="Diamondback dorsal — bold sand-and-charcoal diamond chain markings."),
 "fm_stingray": dict(name="Stingray", engine="stingray_pebble", eargs={}, seed=84,
    base=(8, 9, 11), glow=(96, 102, 112), edge=(226, 232, 244),
    kw=dict(gamma=1.05, edge_gain=0.55), sargs=dict(trace_strength=1.4, calm_floor=26.0),
    desc="Stingray shagreen — fine pewter pebbled denticles with a bright central pearl spot."),
 "fm_tortoise": dict(name="Tortoise", engine="tortoise_shell", eargs=dict(cells=80), seed=85,
    base=(10, 6, 3), glow=(138, 86, 30), edge=(242, 192, 112),
    kw=dict(gamma=0.95, edge_gain=0.9), sargs=dict(trace_strength=1.3, calm_floor=28.0),
    desc="Tortoise shell — amber scute plates with concentric growth rings and dark seams."),
 "fm_gila_bead": dict(name="Gila Bead", engine="gila_bead", eargs=dict(cells=40), seed=86,
    base=(11, 4, 4), glow=(196, 78, 70), edge=(255, 168, 120),
    kw=dict(gamma=1.0, edge_gain=0.6), sargs=dict(trace_strength=1.35, calm_floor=28.0),
    desc="Gila-monster beadwork — coral-pink and black round beads, hex-packed."),
 "fm_tiger_slash": dict(name="Tiger Slash", engine="tiger_stripes", eargs=dict(stripes=9), seed=87,
    base=(8, 4, 2), glow=(214, 96, 16), edge=(255, 178, 64),
    kw=dict(gamma=0.95, edge_gain=0.7), sargs=dict(trace_strength=1.3, calm_floor=26.0),
    desc="Tiger stripes — bold orange ground slashed by dark curved tapering bands."),
 "fm_circuit_maze": dict(name="Circuit Maze", engine="circuitry", eargs=dict(gridn=40), seed=91,
    base=(4, 8, 5), glow=(24, 96, 48), edge=(130, 255, 165),
    kw=dict(gamma=1.0, edge_gain=0.9), sargs=dict(trace_strength=1.4, calm_floor=26.0),
    desc="PCB circuit maze — emerald Manhattan traces with pads/vias."),
 "fm_code_cascade": dict(name="Code Cascade", engine="_code_binary", eargs=dict(cols=80), seed=92,
    base=(2, 8, 4), glow=(22, 120, 42), edge=(120, 255, 140),
    kw=dict(gamma=0.95, edge_gain=0.8), sargs=dict(trace_strength=1.4, calm_floor=26.0),
    desc="Matrix code cascade — phosphor-green glyph columns raining down."),
 "fm_fiber_optic": dict(name="Fiber Optic", engine="fiber_strands", eargs=dict(n=130), seed=93,
    base=(2, 8, 12), glow=(20, 130, 170), edge=(140, 245, 255),
    kw=dict(gamma=0.85, edge_gain=0.9, ambient=0.3, ambient_sigma=52, ambient_floor=0.26),
    sargs=dict(trace_strength=1.3, calm_floor=26.0),
    desc="Fibre-optic strands — glowing cyan filaments fanning with a soft bloom."),
 "fm_rivet_array": dict(name="Rivet Array", engine="rivets", eargs=dict(gridn=52), seed=94,
    base=(9, 6, 4), glow=(135, 90, 45), edge=(245, 195, 130),
    kw=dict(gamma=1.0, edge_gain=0.5), sargs=dict(trace_strength=1.3, calm_floor=28.0),
    desc="Riveted copper panels — domed rivets on brushed metal with panel seams."),
 "fm_lattice": dict(name="Lattice", engine="box_lattice", eargs=dict(cells=10), seed=95,
    base=(5, 7, 10), glow=(55, 75, 105), edge=(178, 202, 238),
    kw=dict(gamma=1.0, edge_gain=1.1), sargs=dict(trace_strength=1.4, calm_floor=26.0),
    desc="Isometric box-girder lattice — a steel 3D strut cube grid."),
 "fm_checkerflash": dict(name="Checkerflash", engine="checker_warp", eargs=dict(cells=34), seed=96,
    base=(7, 6, 4), glow=(120, 96, 42), edge=(244, 216, 140),
    kw=dict(gamma=1.0, edge_gain=0.85), sargs=dict(trace_strength=1.3, calm_floor=28.0),
    desc="Warped gold checkerboard with a sweeping diagonal specular flash."),
 "fm_static_burst": dict(name="Static Burst", engine="static_burst", eargs={}, seed=97,
    base=(4, 6, 12), glow=(52, 84, 165), edge=(185, 212, 255),
    kw=dict(gamma=0.9, edge_gain=1.0), sargs=dict(trace_strength=1.35, calm_floor=26.0),
    desc="Radial electric static burst — angular streaks exploding from the centre over grain."),
 "fm_basalt": dict(name="Basalt", engine="basalt_columns", eargs=dict(cells=40), seed=98,
    base=(6, 7, 8), glow=(60, 66, 74), edge=(152, 166, 184),
    kw=dict(gamma=1.0, edge_gain=0.7), sargs=dict(trace_strength=1.3, calm_floor=28.0),
    desc="Columnar basalt — beveled slate column tops fractured by dark seams (Giant's Causeway)."),
 "fm_frost_feather": dict(name="Frost Feather", engine="_frost_feather_deep", eargs=dict(feathers=40), seed=101,
    base=(8, 11, 16), glow=(96, 150, 195), edge=(225, 245, 255),
    kw=dict(gamma=0.9, edge_gain=0.9, ambient=0.34, ambient_sigma=52, ambient_floor=0.3),
    sargs=dict(trace_strength=1.35, calm_floor=24.0),
    desc="Feather frost — pale cyan feather fans (rachis + tapering barbs) scattered at all angles."),
 "fm_frost_lace": dict(name="Frost Lace", engine="_frost_lace_deep", eargs=dict(seeds=40), seed=102,
    base=(9, 9, 16), glow=(120, 130, 195), edge=(238, 240, 255),
    kw=dict(gamma=0.9, edge_gain=0.9, ambient=0.34, ambient_sigma=52, ambient_floor=0.3),
    sargs=dict(trace_strength=1.35, calm_floor=24.0),
    desc="Window-frost lace — recursive white-violet fern dendrites branching across the pane."),
 "fm_glacier_core": dict(name="Glacier Core", engine="glacier_core", eargs=dict(facets=95), seed=103,
    base=(5, 10, 16), glow=(42, 92, 142), edge=(172, 222, 255),
    kw=dict(gamma=0.95, edge_gain=0.85), sargs=dict(trace_strength=1.3, calm_floor=22.0),
    desc="Glacier core — large deep-blue ice mirror facets split by thin crevasse seams."),
 "fm_geode_slice": dict(name="Geode Slice", engine="geode_bands", eargs=dict(cores=5), seed=104,
    base=(9, 5, 12), glow=(112, 52, 152), edge=(222, 172, 255),
    kw=dict(gamma=0.95, edge_gain=0.95), sargs=dict(trace_strength=1.35, calm_floor=26.0),
    desc="Agate geode — concentric amethyst growth bands around druzy crystal cores."),
 "fm_ebru_marble": dict(name="Ebru Marble", engine="ebru", eargs={}, seed=105,
    base=(8, 6, 12), glow=(126, 64, 112), edge=(245, 212, 142),
    kw=dict(gamma=0.95, edge_gain=0.85), sargs=dict(trace_strength=1.3, calm_floor=26.0),
    desc="Ebru paper marbling — purple-and-gold combed swirl bands."),
 "fm_mudcrack": dict(name="Mudcrack", engine="mudcrack", eargs=dict(cells=140), seed=106,
    base=(10, 7, 4), glow=(142, 96, 56), edge=(228, 182, 130),
    kw=dict(gamma=1.0, edge_gain=0.6), sargs=dict(trace_strength=1.4, calm_floor=28.0),
    desc="Dried mud — terracotta plates doming up between dark shrinkage cracks."),
 "fm_damascus": dict(name="Damascus", engine="damascus", eargs=dict(layers=22), seed=107,
    base=(6, 7, 9), glow=(78, 88, 104), edge=(202, 216, 236),
    kw=dict(gamma=1.0, edge_gain=0.55), sargs=dict(trace_strength=1.4, calm_floor=24.0),
    desc="Damascus steel — folded watering layers in pattern-welded blue-gray."),
 "fm_topo_lines": dict(name="Topo Lines", engine="topo", eargs=dict(levels=18), seed=108,
    base=(5, 9, 6), glow=(52, 112, 72), edge=(172, 238, 192),
    kw=dict(gamma=1.0, edge_gain=0.9), sargs=dict(trace_strength=1.4, calm_floor=26.0),
    desc="Topographic map — green iso-contour elevation lines."),
 "fm_riverine": dict(name="Riverine", engine="_riverine_deep", eargs=dict(rivers=11), seed=111,
    base=(5, 9, 11), glow=(40, 120, 120), edge=(165, 235, 235),
    kw=dict(gamma=0.9, edge_gain=0.9, ambient=0.3, ambient_sigma=54, ambient_floor=0.28),
    sargs=dict(trace_strength=1.4, calm_floor=24.0),
    desc="Braided river delta — bright teal distributary channels splitting through silt."),
 "fm_tide_glass": dict(name="Tide Glass", engine="tide_glass", eargs=dict(sources=5), seed=112,
    base=(4, 10, 13), glow=(36, 118, 140), edge=(178, 246, 250),
    kw=dict(gamma=0.95, edge_gain=0.9), sargs=dict(trace_strength=1.3, calm_floor=24.0),
    desc="Glassy tide ripples — smooth pale-cyan concentric wave-fronts through rippled glass."),
 "fm_tsunami": dict(name="Tsunami", engine="_tsunami_fine", eargs={}, seed=113,
    base=(4, 8, 16), glow=(30, 72, 142), edge=(222, 240, 255),
    kw=dict(gamma=0.9, edge_gain=1.0), sargs=dict(trace_strength=1.35, calm_floor=24.0),
    desc="Great wave — prussian-blue swells curling under bright white foam fingers."),
 "fm_petal_storm": dict(name="Petal Storm", engine="_petal_storm_dense", eargs=dict(n=520), seed=114,
    base=(12, 7, 12), glow=(178, 96, 150), edge=(255, 206, 232),
    kw=dict(gamma=0.95, edge_gain=0.85, ambient=0.26, ambient_sigma=46, ambient_floor=0.26),
    sargs=dict(ignition=1.1, trace_strength=1.5, calm_floor=24.0),
    desc="Petal storm — a dense blizzard of hundreds of tiny curved flower petals at every angle, "
         "layered front-to-back with fine wind-streaked fall trails (full coverage, no big blooms)."),
 "fm_dragonfly": dict(name="Dragonfly", engine="wing_venation", eargs=dict(cells=95), seed=115,
    base=(6, 8, 12), glow=(80, 112, 150), edge=(200, 230, 255),
    kw=dict(gamma=0.95, edge_gain=0.95), sargs=dict(trace_strength=1.4, calm_floor=24.0),
    desc="Dragonfly wing — iridescent thin veins bounding elongated translucent cells."),
 "fm_octo_suckers": dict(name="Octo Suckers", engine="_octo_suckers_fine", eargs=dict(cols=20), seed=116,
    base=(10, 5, 10), glow=(152, 62, 92), edge=(255, 162, 172),
    kw=dict(gamma=1.0, edge_gain=0.8), sargs=dict(trace_strength=1.35, calm_floor=26.0),
    desc="Octopus suckers — staggered rows of concentric purple-coral sucker cups."),
 "fm_thousand_eyes": dict(name="Thousand Eyes", engine="_thousand_eyes_deep", eargs=dict(n=240), seed=117,
    base=(7, 4, 8), glow=(168, 96, 36), edge=(255, 216, 110),
    kw=dict(gamma=1.0, edge_gain=0.95, ambient=0.24, ambient_sigma=42, ambient_floor=0.24),
    sargs=dict(ignition=1.15, trace_strength=1.6, calm_floor=22.0),
    desc="Thousand eyes — a teeming full-coverage swarm of many small watching eyes (amber/violet/"
         "emerald irises, dark pupils, bright catch-light), packed at varied sizes with depth."),
 "fm_witchlight": dict(name="Witchlight", engine="_witchlight_fine", eargs=dict(n=70), seed=118,
    base=(3, 9, 6), glow=(40, 142, 82), edge=(172, 255, 200),
    kw=dict(gamma=0.85, edge_gain=0.8, ambient=0.34, ambient_sigma=58, ambient_floor=0.3),
    sargs=dict(trace_strength=1.3, calm_floor=26.0),
    desc="Witchlight — spectral-green will-o'-wisp orbs drifting with fading wisp trails."),
 "fm_rope_coil": dict(name="Rope Coil", engine="rope", eargs=dict(coils=9), seed=121,
    base=(11, 9, 6), glow=(140, 110, 65), edge=(230, 200, 150),
    kw=dict(gamma=1.0, edge_gain=0.7), sargs=dict(trace_strength=1.35, calm_floor=28.0),
    desc="Twisted hemp rope — round rope laid in rows with a diagonal 3-strand twist."),
 "fm_tessellate": dict(name="Tessellate", engine="tessellation", eargs=dict(cells=8), seed=122,
    base=(8, 7, 6), glow=(122, 82, 46), edge=(236, 196, 140),
    kw=dict(gamma=1.0, edge_gain=0.85), sargs=dict(trace_strength=1.35, calm_floor=26.0),
    desc="Interlocking rotated-square tessellation — copper Escher-style pinwheel tiles."),
 "fm_labyrinth": dict(name="Labyrinth", engine="maze", eargs=dict(cells=24), seed=123,
    base=(6, 8, 7), glow=(64, 96, 80), edge=(178, 220, 196),
    kw=dict(gamma=1.0, edge_gain=0.9), sargs=dict(trace_strength=1.45, calm_floor=24.0),
    desc="A true orthogonal labyrinth — carved stone-green maze corridors."),
 "fm_gyro_cage": dict(name="Gyro Cage", engine="_gyro_cage_fine", eargs=dict(rings=120), seed=124,
    base=(8, 7, 4), glow=(135, 105, 45), edge=(245, 210, 130),
    kw=dict(gamma=1.0, edge_gain=0.9, ambient=0.3, ambient_sigma=54, ambient_floor=0.28),
    sargs=dict(trace_strength=1.4, calm_floor=26.0),
    desc="Gyroscope cage — a brass tangle of interlocking great-circle rings."),
 "fm_dragon_scale": dict(name="Dragon Scale", engine="dragon_scales_3d", eargs=dict(rows=30), seed=125,
    base=(5, 9, 6), glow=(58, 122, 70), edge=(190, 245, 170),
    kw=dict(gamma=0.95, edge_gain=0.75), sargs=dict(trace_strength=1.35, calm_floor=26.0),
    desc="Dragon scales — overlapping 3D-bulging emerald scallops with centre keels."),
 "fm_gyroid": dict(name="Gyroid", engine="_gyroid_fine", eargs={}, seed=126,
    base=(5, 7, 10), glow=(60, 85, 120), edge=(180, 205, 240),
    kw=dict(gamma=0.95, edge_gain=0.85), sargs=dict(trace_strength=1.35, calm_floor=24.0),
    desc="Schwarz-P minimal surface — a steel-blue triply-periodic lattice."),
 "fm_penrose": dict(name="Penrose", engine="penrose_rhombus", eargs=dict(lines=8), seed=127,
    base=(6, 9, 10), glow=(50, 115, 120), edge=(180, 240, 235),
    kw=dict(gamma=1.0, edge_gain=0.9), sargs=dict(trace_strength=1.35, calm_floor=26.0),
    desc="Penrose rhombi — filled teal aperiodic 5-fold tiles with crisp seams."),
 "fm_ion_drift": dict(name="Ion Drift", engine="plasma_drift", eargs=dict(cores=6), seed=128,
    base=(5, 4, 12), glow=(92, 52, 180), edge=(192, 172, 255),
    kw=dict(gamma=0.9, edge_gain=0.95), sargs=dict(trace_strength=1.3, calm_floor=26.0),
    desc="Ion drift — electric-violet plasma-ball cores throwing radial ion filaments."),
 "fs_wraith_veil": dict(name="Wraith Veil", engine="veils", eargs={}, seed=201,
    base=(8, 7, 12), glow=(80, 75, 110), edge=(210, 205, 235),
    kw=dict(gamma=0.95, edge_gain=0.9), sargs=dict(trace_strength=1.3, calm_floor=26.0),
    desc="Wraith veil — translucent spectral sheets draped into glowing folds."),
 "fs_moth_dust": dict(name="Moth Dust", engine="_moth_dust_fine", eargs=dict(motes=150), seed=202,
    base=(9, 8, 8), glow=(98, 84, 80), edge=(208, 192, 182),
    kw=dict(gamma=1.0, edge_gain=0.7), sargs=dict(trace_strength=1.35, calm_floor=26.0),
    desc="Moth dust — a powdery dusk wing-scale ground scattered with ~150 tiny motes (no big "
         "circles), fully abstract and full-coverage for the car UV."),
 "fs_blood_marble": dict(name="Blood Marble", engine="marble", eargs={}, seed=203,
    base=(10, 3, 4), glow=(132, 26, 30), edge=(232, 122, 110),
    kw=dict(gamma=0.95, edge_gain=0.8), sargs=dict(trace_strength=1.3, calm_floor=26.0),
    desc="Blood marble — dark crimson veining clotting through black stone."),
 "fs_night_tide": dict(name="Night Tide", engine="_night_tide_deep", eargs={}, seed=204,
    base=(3, 6, 14), glow=(26, 50, 118), edge=(168, 198, 255),
    kw=dict(gamma=0.95, edge_gain=1.0), sargs=dict(trace_strength=1.4, calm_floor=22.0),
    desc="Night tide — tight wind-rippled midnight swells with fine cross-chop, scattered "
         "moonlight crest glints + foam stipple and a soft depth gradient (full coverage, fine)."),
 "fs_static_veins": dict(name="Static Veins", engine="_static_veins_fine", eargs=dict(cells=440), seed=205,
    base=(6, 4, 12), glow=(95, 55, 175), edge=(205, 178, 255),
    kw=dict(gamma=1.0, edge_gain=1.05), sargs=dict(trace_strength=1.45, calm_floor=22.0),
    desc="Static veins — a VERY fine electric-violet crackle web (440 tiny cells) with a bright "
         "spark node punched at every cell core; distinct from broad mudcrack/shatter veins."),
 "fs_shatter_glass": dict(name="Shatter Glass", engine="shattered_glass", eargs=dict(impacts=4), seed=206,
    base=(5, 8, 13), glow=(55, 90, 140), edge=(205, 230, 255),
    kw=dict(gamma=1.0, edge_gain=1.0, ambient=0.3, ambient_sigma=50, ambient_floor=0.28),
    sargs=dict(trace_strength=1.35, calm_floor=24.0),
    desc="Shatter glass — true impact fracture: radial + concentric ring cracks in cold blue."),
 "fs_howl": dict(name="Howl", engine="wind_streaks", eargs={}, seed=207,
    base=(7, 8, 10), glow=(80, 92, 108), edge=(200, 212, 228),
    kw=dict(gamma=1.0, edge_gain=0.8), sargs=dict(trace_strength=1.35, calm_floor=26.0),
    desc="Howl — long grey-blue wind streaks smeared into howling gusts."),
 "fs_phantom_lattice": dict(name="Phantom Lattice", engine="phantom_grid", eargs=dict(cells=14), seed=208,
    base=(4, 9, 9), glow=(40, 105, 100), edge=(165, 235, 225),
    kw=dict(gamma=1.0, edge_gain=1.05), sargs=dict(trace_strength=1.35, calm_floor=26.0),
    desc="Phantom lattice — two incommensurate grids ghosting into a faint teal double-lattice."),
 "fs_ember_drift": dict(name="Ember Drift", engine="_embers_dense", eargs=dict(n=340), seed=211,
    base=(7, 2, 1), glow=(205, 70, 12), edge=(255, 214, 96),
    kw=dict(gamma=0.88, fill_gain=1.05, edge_gain=1.05), sargs=dict(trace_strength=1.35, calm_floor=24.0),
    desc="Ember drift — a dense storm of MANY small embers at three depth tiers with drift trails "
         "over a warm ember haze (deep crimson -> orange coal -> bright gold spark); full coverage."),
 "fs_carnival_night": dict(name="Carnival Night", engine="_carnival_lights", eargs=dict(strings=11, n=190), seed=212,
    base=(7, 4, 11), glow=(178, 52, 132), edge=(255, 224, 120),
    kw=dict(gamma=0.9, fill_gain=1.0, edge_gain=1.0), sargs=dict(trace_strength=1.35, calm_floor=24.0),
    desc="Carnival night — swagged strands of small festival string-lights + a confetti scatter of "
         "tiny bright sparks over soft glow, magenta-and-gold and vivid; reads as a fairground at night."),
 "fs_widow_braid": dict(name="Widow Braid", engine="_widow_braid_fine", eargs=dict(webs=10), seed=213,
    base=(6, 6, 7), glow=(72, 74, 82), edge=(206, 210, 220),
    kw=dict(gamma=1.0, edge_gain=0.95, ambient=0.28, ambient_sigma=50, ambient_floor=0.26),
    sargs=dict(trace_strength=1.45, calm_floor=24.0),
    desc="Widow braid — MANY small silver spider webs (radial spokes crossed by concentric capture "
         "threads) crushed fine into a braided lace over a silk haze; distinct, full coverage."),
 "fs_ghost_silk": dict(name="Ghost Silk", engine="spectral_silk", eargs={}, seed=214,
    base=(9, 9, 12), glow=(110, 105, 125), edge=(235, 232, 245),
    kw=dict(gamma=1.1, edge_gain=0.75), sargs=dict(trace_strength=1.3, calm_floor=28.0),
    desc="Ghost silk — a pale pearl-lavender directional sheen drifting like spectral fabric."),
 "fs_shattered_prism": dict(name="Prism Mesh", engine="_prism_mesh", eargs=dict(cells=48), seed=215,
    base=(5, 6, 12), glow=(70, 88, 168), edge=(206, 226, 255),
    kw=dict(gamma=1.0, edge_gain=1.0), sargs=dict(trace_strength=1.4, calm_floor=24.0),
    desc="Prism Mesh — a brand-new dense micro-prism sheet: a fine regular grid of tiny triangular "
         "prism facets fanning in 4 orientations with crisp seams and a per-facet spectral shimmer "
         "(geometric, fully covered, fine — NOT another shatter/voronoi/crystal-shard look)."),
 "fs_oil_serpent": dict(name="Oil Serpent", engine="oil_serpent", eargs={}, seed=216,
    base=(4, 7, 9), glow=(50, 110, 110), edge=(192, 172, 232),
    kw=dict(gamma=0.95, edge_gain=0.85), sargs=dict(trace_strength=1.3, calm_floor=26.0),
    desc="Oil serpent — serpentine coils glazed with petrol thin-film iridescence."),
 "fs_hex_hive": dict(name="Hex Hive", engine="hexgrid", eargs=dict(cells=30, mode="filled"), seed=217,
    base=(9, 6, 2), glow=(150, 100, 25), edge=(248, 198, 92),
    kw=dict(gamma=1.1, edge_gain=0.85), sargs=dict(trace_strength=1.45, calm_floor=24.0),
    desc="Hex hive — MANY more, much smaller dark-amber honeycomb hive cells (cells 13->30) with "
         "fine beveled rims dripping light; crushed fine, full coverage."),
 "fs_guilloche_ghost": dict(name="Guilloche Ghost", engine="_guilloche_fine", eargs=dict(reps=9), seed=218,
    base=(6, 7, 9), glow=(78, 88, 104), edge=(214, 226, 242),
    kw=dict(gamma=1.0, edge_gain=1.25, ambient=0.26, ambient_sigma=48, ambient_floor=0.22),
    sargs=dict(ignition=1.05, trace_strength=2.0, calm_floor=18.0),
    desc="Guilloche ghost — a FINE engine-turned guilloché lace: ~5x more, much smaller "
         "epicycloid rosettes interlaced into continuous banknote lace; the spec ignites the "
         "fine lines (high trace, low calm floor) so it mirrors the paint exactly."),
 "fs_petrol_halo": dict(name="Petrol Halo", engine="newton_rings", eargs=dict(halos=6), seed=221,
    base=(4, 7, 10), glow=(60, 100, 120), edge=(202, 180, 232),
    kw=dict(gamma=0.95, edge_gain=0.95), sargs=dict(trace_strength=1.3, calm_floor=24.0),
    desc="Petrol halo — overlapping oil-film Newton's rings shimmering with iridescence."),
 "fs_star_chart": dict(name="Star Chart", engine="starchart", eargs=dict(stars=680, lines=150), seed=222,
    base=(4, 5, 14), glow=(40, 50, 120), edge=(255, 232, 150),
    kw=dict(gamma=0.9, edge_gain=1.0, ambient=0.26, ambient_sigma=52, ambient_floor=0.24),
    sargs=dict(trace_strength=1.35, calm_floor=24.0),
    desc="Star chart — ~5x MORE stars (680, mostly small) joined by many more fine constellation "
         "lines over an indigo nebula; far denser + finer."),
 "fs_serpent_scale": dict(name="Serpent Scale", engine="serpent_scales", eargs=dict(rows=16), seed=223,
    base=(4, 10, 7), glow=(40, 120, 80), edge=(170, 250, 190),
    kw=dict(gamma=0.95, edge_gain=0.75), sargs=dict(trace_strength=1.35, calm_floor=26.0),
    desc="Serpent scale — tight rows of pointed jade scales with keeled ridges."),
 "fs_nova_burst": dict(name="Nova Burst", engine="nova", eargs={}, seed=224,
    base=(8, 6, 3), glow=(180, 140, 60), edge=(255, 245, 210),
    kw=dict(gamma=0.9, edge_gain=1.0), sargs=dict(trace_strength=1.3, calm_floor=24.0),
    desc="Nova burst — clean white-gold rays exploding from a bright central core flash."),
 "fs_circuit_soul": dict(name="Circuit Soul", engine="_circuit_dense", eargs=dict(gridn=66), seed=225,
    base=(3, 8, 10), glow=(30, 110, 130), edge=(150, 240, 255),
    kw=dict(gamma=1.0, edge_gain=1.0), sargs=dict(trace_strength=1.45, calm_floor=22.0),
    desc="Circuit soul — a MUCH denser fine cyan PCB: finer grid + ~3x trace walks with small "
         "pads/vias over a faint ground plane + trace haze (no blank spots), distinct from circuit_maze."),
 "fs_geode_vein": dict(name="Geode Vein", engine="_geode_vein_banded", eargs=dict(cores=5), seed=226,
    base=(10, 5, 3), glow=(150, 86, 30), edge=(252, 206, 128),
    kw=dict(gamma=0.95, edge_gain=1.0), sargs=dict(trace_strength=1.4, calm_floor=24.0),
    desc="Geode vein — a clearly BANDED warm-amber agate geode: high-contrast concentric growth "
         "bands ringing several cores, dark chalcedony vein seams between lobes, and a bright druzy "
         "crystal crust at each core; reads unmistakably as a geode, distinct from teal cell finishes."),
 "fs_moire_phantom": dict(name="Moire Phantom", engine="linear_moire", eargs={}, seed=227,
    base=(6, 5, 12), glow=(90, 55, 150), edge=(210, 180, 255),
    kw=dict(gamma=1.0, edge_gain=0.95), sargs=dict(trace_strength=1.3, calm_floor=26.0),
    desc="Moire phantom — two rotated gratings beating into spectral-violet interference bands."),
 "fs_aurora_threads": dict(name="Aurora Threads", engine="aurora_curtains", eargs={}, seed=228,
    base=(4, 9, 8), glow=(50, 130, 90), edge=(190, 170, 255),
    kw=dict(gamma=0.9, edge_gain=0.9), sargs=dict(trace_strength=1.3, calm_floor=26.0),
    desc="Aurora threads — wavering green curtains streaked with violet, fading up the sky."),
}


# ── CRUSH FIX 2026-06-17 (owner audit) ────────────────────────────────────────────────────────
# Owner: the named MINDS patterns render TOO BIG on the 2048 car and must be CRUSHED to finer
# detail (#1 complaint). Most are crushed purely by raising the count/grid/freq knob in `eargs`
# above (more, smaller repeats). A handful needed real rework (depth / full coverage / fine
# sub-texture / 1's-and-0's / a brand-new design) — those route to the LOCAL engines below.
# We must NOT edit engine/paint_v2/fractured_math.py, so these live here and import its primitives.
import cv2 as _cv2  # noqa: E402  (alias so local engines read clearly)
from engine.paint_v2.fractured_motifs import _fbm as _fbm, _rng as _rng  # noqa: E402


def _code_binary(h, w, seed, *, res=600, cols=80):
    """fm_code_cascade rebuild: Matrix code cascade using BOTH 1's and 0's (not just 0's), ~2x the
    columns (crushed ~50%), and a guaranteed dim glyph floor in every column so there are NO blank
    spots (full coverage). Each column rains glyph blocks fading behind a falling head."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / cols
    gh = max(2.0, s * 1.15)            # glyph cell height
    half = max(1, int(s * 0.32))
    for c in range(int(cols)):
        x = int((c + 0.5) * s)
        head = float(rng.uniform(0, res))
        length = float(rng.uniform(0.30, 0.85) * res)
        yy = 0.0
        while yy < res:
            dist = (yy - head) % res
            b = float(np.clip(1.0 - dist / length, 0.0, 1.0))
            b = max(b, 0.12)            # dim floor -> every cell carries a faint glyph (no gaps)
            if rng.random() < 0.92:
                y0 = int(yy)
                if rng.random() < 0.5:          # "1": a thin vertical bar
                    _cv2.rectangle(img, (x - max(1, half // 3), y0),
                                   (x + max(1, half // 3), int(yy + gh * 0.7)), b, -1)
                else:                            # "0": a small hollow ring
                    _cv2.ellipse(img, (x, int(yy + gh * 0.38)), (half, int(gh * 0.34)),
                                 0, 0, 360, b, max(1, int(s * 0.16)), _cv2.LINE_AA)
            yy += gh
    return _cv2.resize(_norm_(_cv2.GaussianBlur(img, (0, 0), 0.4)), (w, h), interpolation=_cv2.INTER_CUBIC)


def _frost_feather_deep(h, w, seed, *, res=600, feathers=40):
    """fm_frost_feather rebuild: many smaller feather fans (crushed) PLUS depth — a soft frosted
    ground bloom under the crisp barbs and a faint secondary blur layer so it's no longer flat."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(feathers)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        ang = float(rng.uniform(0, 6.283))
        L = float(rng.uniform(0.07, 0.17) * res)          # crushed ~2-2.5x vs original
        ex, ey = cx + np.cos(ang) * L, cy + np.sin(ang) * L
        _cv2.line(img, (int(cx), int(cy)), (int(ex), int(ey)), 0.95, 1, _cv2.LINE_AA)
        nb = max(4, int(L / 4))
        for i in range(nb):
            t = i / nb
            bx, by = cx + np.cos(ang) * L * t, cy + np.sin(ang) * L * t
            blen = (1.0 - t) * L * 0.42
            for side in (1.0, -1.0):
                ba = ang + side * 1.0
                _cv2.line(img, (int(bx), int(by)),
                          (int(bx + np.cos(ba) * blen), int(by + np.sin(ba) * blen)), 0.7, 1, _cv2.LINE_AA)
    crisp = _norm_(img)
    bloom = _norm_(_cv2.GaussianBlur(img, (0, 0), 5.0))     # frosted depth halo under the barbs
    grain = _fbm(res, res, rng, 5, 7).astype(np.float32)    # fine crystalline ground (kills flatness)
    field = _norm_(crisp * 0.9 + bloom * 0.45 + grain * 0.22)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _frost_lace_deep(h, w, seed, *, res=600, seeds=40):
    """fm_frost_lace rebuild: many more (crushed) recursive fern dendrites + real depth/contrast —
    a layered frost bloom plus a contrast-stretched fine ground so it stops reading flat/lazy."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)

    def fern(x, y, ang, length, depth):
        if depth <= 0 or length < 2.0:
            return
        ex, ey = x + np.cos(ang) * length, y + np.sin(ang) * length
        _cv2.line(img, (int(x), int(y)), (int(ex), int(ey)), float(0.45 + 0.14 * depth), 1, _cv2.LINE_AA)
        for i in range(1, 4):
            t = i / 4.0
            bx, by = x + (ex - x) * t, y + (ey - y) * t
            for side in (1.0, -1.0):
                fern(bx, by, ang + side * float(rng.uniform(0.5, 0.9)), length * 0.45, depth - 1)
        fern(ex, ey, ang + float(rng.uniform(-0.2, 0.2)), length * 0.68, depth - 1)

    for _ in range(int(seeds)):
        fern(float(rng.uniform(0, res)), float(rng.uniform(0, res)),
             float(rng.uniform(0, 6.283)), float(rng.uniform(20, 42)), 4)   # crushed ~2x (was 42-82)
    crisp = _norm_(img)
    halo = _norm_(_cv2.GaussianBlur(img, (0, 0), 4.0))      # ice-bloom depth
    ground = _fbm(res, res, rng, 5, 8).astype(np.float32)
    field = np.clip(crisp * 1.05 + halo * 0.4 + (ground - 0.5) * 0.5, 0.0, 1.0)  # boosted contrast
    return _cv2.resize(_norm_(field), (w, h), interpolation=_cv2.INTER_CUBIC)


def _riverine_deep(h, w, seed, *, res=600, rivers=11):
    """fm_riverine rebuild (was the worst, rated 34): a UNIQUE braided-channel network — many fine
    distributary rivers crushed HARD, carved as bright water with dark cut-banks on either side
    (depth) over a silt floor with fine bar texture. Distinct from topo/labyrinth/lava veins."""
    rng = _rng(seed)
    water = np.zeros((res, res), np.float32)
    banks = np.zeros((res, res), np.float32)

    def branch(x, y, ang, width, length, depth):
        if depth <= 0 or width < 0.6:
            return
        for _s in range(max(1, int(length / 5))):
            ang += float(rng.uniform(-0.18, 0.18))
            nx, ny = x + np.cos(ang) * 5.0, y + np.sin(ang) * 5.0
            wpx = max(1, int(width))
            _cv2.line(water, (int(x), int(y)), (int(nx), int(ny)), 1.0, wpx, _cv2.LINE_AA)
            _cv2.line(banks, (int(x), int(y)), (int(nx), int(ny)), 1.0, wpx + 3, _cv2.LINE_AA)
            x, y = nx % res, ny % res
        for _ in range(int(rng.integers(2, 4))):
            branch(x, y, ang + float(rng.uniform(-0.8, 0.8)), width * 0.62, length * 0.66, depth - 1)

    for _ in range(int(rivers)):
        e = int(rng.integers(0, 4))
        if e == 0:
            x, y, a = float(rng.uniform(0, res)), 0.0, 1.5
        elif e == 1:
            x, y, a = float(rng.uniform(0, res)), float(res), -1.5
        elif e == 2:
            x, y, a = 0.0, float(rng.uniform(0, res)), 0.0
        else:
            x, y, a = float(res), float(rng.uniform(0, res)), 3.14
        branch(x, y, a + float(rng.uniform(-0.5, 0.5)),
               float(rng.uniform(2.0, 4.5)), float(rng.uniform(0.5, 0.85) * res), 5)
    water = _norm_(_cv2.GaussianBlur(water, (0, 0), 0.6))
    bankline = _norm_(np.clip(_cv2.GaussianBlur(banks, (0, 0), 0.8) - water, 0, 1))   # cut-bank rim
    silt = _fbm(res, res, rng, 5, 7).astype(np.float32)                                # textured silt floor
    field = _norm_(0.22 * silt + 0.85 * water - 0.35 * bankline)   # bright water, dark banks (depth)
    return _cv2.resize(np.clip(field, 0, 1), (w, h), interpolation=_cv2.INTER_CUBIC)


def _tsunami_fine(h, w, seed, *, res=600):
    """fm_tsunami rebuild: the great-wave swell crushed finer (more, tighter bands) with much more
    fine detail — sharper foam stipple + a fine spray micro-texture so it's not blobby/macro."""
    base = fm.great_wave(res, res, seed)                  # the swell+foam look, kept
    base = _tile_finer_(base, 2)                           # crush features ~2x (tighter swells)
    rng = _rng(seed + 5)
    spray = (_fbm(res, res, rng, 7, 1) > 0.74).astype(np.float32)   # fine white spray flecks
    fine = 0.5 + 0.5 * np.sin(_norm_(base) * np.pi * 5.0)           # extra fine ripple harmonic
    field = _norm_(base * 0.78 + fine * 0.18 + spray * 0.35)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _petal_storm_dense(h, w, seed, *, res=600, n=520):
    """fm_petal_storm REPLACE (was rated 25): a dense storm of HUNDREDS of small curved petals at
    every angle, layered front-to-back with fine wind-fall streaks — full coverage, no big blooms."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    # back layer: faint blurred drift of distant petals (depth + coverage)
    for _ in range(int(n * 0.45)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        sz = float(rng.uniform(3.0, 7.0))
        _cv2.ellipse(img, (int(cx), int(cy)), (int(sz), max(1, int(sz * 0.5))),
                     float(rng.uniform(0, 360)), 0, 360, float(rng.uniform(0.18, 0.4)), -1, _cv2.LINE_AA)
    img = _cv2.GaussianBlur(img, (0, 0), 2.0)
    # front layer: crisp small petals with a faint fall-streak tail each
    for _ in range(int(n)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        sz = float(rng.uniform(4.0, 10.0))                 # SMALL (was 8-26)
        ang = float(rng.uniform(0, 360))
        b = float(rng.uniform(0.5, 1.0))
        ar = np.radians(ang)
        tx, ty = cx - np.cos(ar) * sz * 2.2, cy - np.sin(ar) * sz * 2.2
        _cv2.line(img, (int(tx), int(ty)), (int(cx), int(cy)), b * 0.3, 1, _cv2.LINE_AA)   # wind trail
        _cv2.ellipse(img, (int(cx), int(cy)), (int(sz), max(1, int(sz * 0.42))),
                     ang, 0, 360, b, -1, _cv2.LINE_AA)
    return _cv2.resize(_norm_(_cv2.GaussianBlur(img, (0, 0), 0.5)), (w, h), interpolation=_cv2.INTER_CUBIC)


def _octo_suckers_fine(h, w, seed, *, res=600, cols=20):
    """fm_octo_suckers rebuild: MANY small suckers (crushed hard, ~2.5x more rows/cols) on a fine
    pebbled skin sub-texture between them -> full coverage, no blank spots, not blobby."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / cols
    iy = 0
    for cy in np.arange(s * 0.5, res, s * 0.85):
        off = (iy % 2) * s * 0.5
        for cx in np.arange(off, res + s, s):
            r = int(s * 0.42 * float(rng.uniform(0.75, 1.0)))
            if r < 2:
                continue
            _cv2.circle(img, (int(cx), int(cy)), r, 0.8, 1, _cv2.LINE_AA)
            _cv2.circle(img, (int(cx), int(cy)), int(r * 0.55), 1.0, -1, _cv2.LINE_AA)
            _cv2.circle(img, (int(cx), int(cy)), int(r * 0.55), 0.3, 1, _cv2.LINE_AA)
        iy += 1
    img = _norm_(_cv2.GaussianBlur(img, (0, 0), 0.5))
    skin = _fbm(res, res, rng, 6, 8).astype(np.float32)    # fine cephalopod skin between suckers
    field = _norm_(img * 0.85 + skin * 0.3 + 0.06)         # +floor -> no dead corners
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _thousand_eyes_deep(h, w, seed, *, res=600, n=240):
    """fm_thousand_eyes heavy rework (was rated 28): a teeming full-coverage swarm of MANY small
    eyes at varied sizes/depth, with a RICH multi-hue iris field (the iris brightness varies per
    eye so colorize spreads it across amber/violet/emerald), dark pupils, bright catch-lights."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    # depth: a few size tiers, smallest drawn first (behind)
    for tier, (count, lo, hi, blur) in enumerate(
            [(int(n * 0.5), 4.0, 8.0, 1.6), (int(n * 0.35), 8.0, 14.0, 0.8), (int(n * 0.15), 14.0, 22.0, 0.4)]):
        layer = np.zeros((res, res), np.float32)
        for _ in range(count):
            cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
            r = float(rng.uniform(lo, hi))
            iris = float(rng.uniform(0.45, 1.0))           # varied iris tone -> hue variety via colorize
            _cv2.circle(layer, (int(cx), int(cy)), int(r), iris * 0.55, 1, _cv2.LINE_AA)   # rim
            _cv2.circle(layer, (int(cx), int(cy)), int(r * 0.72), iris, -1, _cv2.LINE_AA)  # iris
            _cv2.circle(layer, (int(cx), int(cy)), int(r * 0.34), 0.05, -1, _cv2.LINE_AA)  # pupil
            _cv2.circle(layer, (int(cx - r * 0.18), int(cy - r * 0.18)),
                        max(1, int(r * 0.12)), 1.0, -1, _cv2.LINE_AA)                       # catch-light
        if blur > 0:
            layer = _cv2.GaussianBlur(layer, (0, 0), blur)
        img = np.maximum(img, layer)
    ground = _fbm(res, res, rng, 6, 7).astype(np.float32)   # fine ground between eyes -> coverage+depth
    field = _norm_(img * 0.92 + ground * 0.22 + 0.05)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _witchlight_fine(h, w, seed, *, res=360, n=70):
    """fm_witchlight rebuild: MANY more, smaller will-o'-wisp orbs (crushed, less blobby) over a
    dim spectral mist so the whole canvas glows faintly -> full coverage, no blank spots. Drawn
    with cv2.circle splats (not per-orb full-grid hypot) so it stays well under budget."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(n)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        r = max(2, int(rng.uniform(0.012, 0.038) * res))   # SMALL orbs (was 0.03-0.09)
        _cv2.circle(img, (int(cx), int(cy)), r, 1.0, -1, _cv2.LINE_AA)   # orb core
        ang = float(rng.uniform(0, 6.28))
        for t in range(1, 6):                               # fading wisp trail
            tx = int(cx - np.cos(ang) * t * r * 1.1)
            ty = int(cy - np.sin(ang) * t * r * 1.1)
            _cv2.circle(img, (tx, ty), max(1, int(r * 0.5)), float(0.35 * (1.0 - t / 6.0)), -1, _cv2.LINE_AA)
    core = _norm_(_cv2.GaussianBlur(img, (0, 0), max(1.0, res / 220.0)))   # soft orb glow
    mist = _norm_(_cv2.GaussianBlur(img, (0, 0), res / 22.0))              # spectral mist -> dim full glow
    field = _norm_(core + mist * 0.5)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _gyro_cage_fine(h, w, seed, *, res=600, rings=70):
    """fm_gyro_cage rebuild: MANY more, smaller interlocking rings (crushed, less blobby) covering
    the whole frame, plus a faint brushed-metal ground so there are no blank gaps; differentiated
    from cage()'s sparse big ellipses."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(rings)):
        ccx, ccy = float(rng.uniform(0.0, 1.0) * res), float(rng.uniform(0.0, 1.0) * res)
        a = int(rng.uniform(0.04, 0.11) * res)             # SMALL rings (was 0.18-0.4; less blobby)
        b = int(a * float(rng.uniform(0.25, 1.0)))
        _cv2.ellipse(img, (int(ccx), int(ccy)), (max(2, a), max(2, b)), float(rng.uniform(0, 180)),
                     0, 360, float(rng.uniform(0.55, 1.0)), 1, _cv2.LINE_AA)
    img = _norm_(_cv2.GaussianBlur(img, (0, 0), 0.5))
    metal = _fbm(res, res, rng, 5, 7).astype(np.float32)   # brushed-metal ground -> full coverage
    field = _norm_(img * 0.9 + metal * 0.22 + 0.05)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _gyroid_fine(h, w, seed, *, res=600):
    """fm_gyroid rebuild: a TRUE gyroid TPMS slice (sin x cos y + ...) at higher frequency (crushed,
    finer cells), differentiated from the schwarz_surface look it shared — adds a thin bright wall
    network so it's a crisp lattice, not a blobby field."""
    rng = _rng(seed)
    scale = float(rng.uniform(9.0, 12.0))                  # higher freq -> crushed finer
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    x = gx / res * scale * 6.283
    y = gy / res * scale * 6.283
    z = float(rng.uniform(0, 6.283)) + (_fbm(res, res, rng, 3, 4) - 0.5) * 2.0
    g = np.sin(x) * np.cos(y) + np.sin(y) * np.cos(z) + np.sin(z) * np.cos(x)
    body = _norm_(np.abs(g))
    wall = _norm_(np.abs(_cv2.Laplacian(body, _cv2.CV_32F)))   # thin lattice walls
    field = _norm_(body * 0.7 + wall * 0.6)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


# ── SOULS CRUSH FIX 2026-06-17 (owner audit) ───────────────────────────────────────────────────
# The fs_ SOULS finishes below rendered TOO BIG / blobby / blank on the 2048 car. These local
# engines CRUSH them to fine detail with full coverage (no blank spots), and several get a real
# rework (depth, richer palette, name-matching structure, brand-new design). Same contract as the
# MINDS local engines above: (h, w, seed, **eargs) -> float32 0..1 field, drawn O(n) + blur so
# they stay well under the ~3s render budget. We import fractured_math primitives, never edit it.

def _moth_dust_fine(h, w, seed, *, res=600, motes=140):
    """fs_moth_dust rebuild (was 2 giant eyespots + plain bg): a powdery dusk wing-scale ground
    PLUS ~140 TINY scattered motes (small soft specks/ringlets at varied size) — fully abstract,
    full coverage, no big circles. Reads as drifting moth dust on a wing."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    # dense pixel-dust ground (powdery wing scales) -> guaranteed full coverage, no blank spots
    npx = int(res * res * 0.012)
    xs = rng.integers(0, res, npx); ys = rng.integers(0, res, npx)
    img[ys, xs] = rng.uniform(0.25, 0.9, npx).astype(np.float32)
    img = _cv2.GaussianBlur(img, (0, 0), 0.8)
    # ~140 tiny motes: small soft discs + a faint ring on the larger ones (no giant circles)
    for _ in range(int(motes)):
        cx, cy = int(rng.uniform(0, res)), int(rng.uniform(0, res))
        r = int(rng.uniform(0.006, 0.020) * res)            # TINY (3-12px @600), was 0.06-0.12
        b = float(rng.uniform(0.5, 1.0))
        _cv2.circle(img, (cx, cy), max(1, r), b, -1, _cv2.LINE_AA)
        if r >= 6 and rng.random() < 0.5:
            _cv2.circle(img, (cx, cy), r + 2, b * 0.5, 1, _cv2.LINE_AA)   # faint scale ring
    fine = _fbm(res, res, rng, 5, 9).astype(np.float32)      # fine crystalline dust texture
    field = _norm_(_cv2.GaussianBlur(img, (0, 0), 0.5) * 0.9 + fine * 0.25 + 0.05)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _night_tide_deep(h, w, seed, *, res=600):
    """fs_night_tide HEAVY rework (was 39: blank/big/flat/lazy): a UNIQUE fine ocean-at-night —
    tight wind-rippled swells (high-freq directional waves + fine cross-chop) carrying scattered
    small moonlight crest glints and a fine foam stipple, with a soft depth gradient. Full
    coverage, fine, distinct from blood_marble / static / shatter."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    # domain-warp the wave field so swells meander (not straight bands -> UV-agnostic)
    warp = (_fbm(res, res, rng, 4, 5) - 0.5) * res * 0.18
    ang = float(rng.uniform(0, 6.283))
    u = (gx * np.cos(ang) + gy * np.sin(ang)) + warp
    v = (-gx * np.sin(ang) + gy * np.cos(ang)) + warp * 0.6
    swell = (0.5 + 0.5 * np.sin(u / res * 22.0 * np.pi)) * 0.55          # tight primary swells
    chop = (0.5 + 0.5 * np.sin(v / res * 38.0 * np.pi + u * 0.01)) * 0.3  # finer cross-chop
    micro = _fbm(res, res, rng, 6, 9).astype(np.float32) * 0.25           # fine wind-ripple texture
    waves = _norm_(swell + chop + micro)
    crest = np.clip((waves - 0.78) * 5.0, 0, 1)                           # bright crests
    glint = (_fbm(res, res, rng, 7, 2) > 0.80).astype(np.float32) * crest # scattered moonlight glints
    foam = (_fbm(res, res, rng, 7, 1) > 0.86).astype(np.float32) * crest * 0.6
    depth = 0.45 + 0.55 * (gy / res)                                     # subtle deep->shallow shade
    field = _norm_(waves * depth * 0.7 + crest * 0.5 + glint * 0.9 + foam * 0.7)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _static_veins_fine(h, w, seed, *, res=600, cells=420):
    """fs_static_veins crush + differentiate: a VERY fine electric crackle web (many more, much
    smaller Voronoi cells) with bright spark NODES punched at the cell vertices and a faint
    high-freq electric grain between — distinct from the broad mudcrack / shatter veins."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, _ = cKDTree(pts).query(q, k=2)
    F1 = d[:, 0].reshape(res, res); F2 = d[:, 1].reshape(res, res)
    crack = np.clip(1.0 - _norm_(F2 - F1) * 11.0, 0, 1)                  # thinner = finer cracks
    node = np.clip(1.0 - _norm_(F1) * 30.0, 0, 1)                        # bright spark at each cell core
    grain = _fbm(res, res, rng, 7, 6).astype(np.float32)                # electric crackle haze
    field = _norm_(crack * 0.85 + node * 0.7 + grain * 0.12)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _embers_dense(h, w, seed, *, res=600, n=340):
    """fs_ember_drift rework (was 40: blank/big/flat/boring palette): a DENSE drift of MANY small
    glowing embers at three depth tiers (small dim behind -> bright sparks front) with short drift
    trails, over a warm ember haze floor so the whole canvas glows (full coverage). Richer warm
    range comes from the per-ember brightness spread feeding the colorize glow->edge ramp."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    haze = np.zeros((res, res), np.float32)
    for count, lo, hi, br in [(int(n * 0.5), 1.5, 3.0, (0.30, 0.6)),
                              (int(n * 0.35), 3.0, 5.0, (0.55, 0.85)),
                              (int(n * 0.15), 5.0, 8.0, (0.85, 1.0))]:
        for _ in range(count):
            cx, cy = int(rng.uniform(0, res)), int(rng.uniform(0, res))
            r = int(rng.uniform(lo, hi)); b = float(rng.uniform(*br))
            _cv2.circle(img, (cx, cy), max(1, r), b, -1, _cv2.LINE_AA)
            _cv2.circle(haze, (cx, cy), max(1, r), b, -1, _cv2.LINE_AA)
            for t in range(1, 4):                                       # upward drift trail
                _cv2.circle(img, (cx + int(rng.uniform(-1, 1)), cy - t * r),
                            max(1, int(r * (1.0 - t * 0.25))), b * 0.3, -1, _cv2.LINE_AA)
    core = _cv2.GaussianBlur(img, (0, 0), 0.7)
    glow = _cv2.GaussianBlur(haze, (0, 0), 11.0) * 0.9                   # warm ember haze -> no blank spots
    field = _norm_(core + glow + 0.04)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _carnival_lights(h, w, seed, *, res=600, strings=10, n=170):
    """fs_carnival_night rework (was 39: doesn't match name): an actual CARNIVAL NIGHT — strands
    of small round festival string-lights swagged across the dark, a confetti scatter of tiny
    bright sparks, and a few soft glow bokeh behind for depth. Vivid via brightness spread (the
    magenta->gold colorize ramp paints the bulbs across the carnival palette). Full coverage."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    # soft background bokeh glow (depth + base coverage)
    for _ in range(18):
        cx, cy = int(rng.uniform(0, res)), int(rng.uniform(0, res))
        _cv2.circle(img, (cx, cy), int(rng.uniform(0.03, 0.07) * res),
                    float(rng.uniform(0.1, 0.3)), -1, _cv2.LINE_AA)
    img = _cv2.GaussianBlur(img, (0, 0), 6.0)
    # swagged strings of small bulbs (catenary droop) across the frame at varied heights/angles
    for _ in range(int(strings)):
        y0 = float(rng.uniform(0.05, 0.95) * res)
        droop = float(rng.uniform(0.04, 0.14) * res)
        slope = float(rng.uniform(-0.25, 0.25))
        nb = int(rng.integers(12, 22))
        for i in range(nb):
            t = i / (nb - 1)
            x = t * res
            y = y0 + slope * (x - res * 0.5) + droop * np.sin(t * np.pi)
            b = float(rng.uniform(0.55, 1.0))
            _cv2.circle(img, (int(x), int(y)), int(rng.uniform(2.5, 4.5)), b, -1, _cv2.LINE_AA)
            _cv2.circle(img, (int(x), int(y)), int(rng.uniform(5, 8)), b * 0.25, -1, _cv2.LINE_AA)  # halo
    # confetti / distant sparks -> fine full-coverage twinkle
    for _ in range(int(n)):
        cx, cy = int(rng.uniform(0, res)), int(rng.uniform(0, res))
        _cv2.circle(img, (cx, cy), int(rng.uniform(1, 2.5)), float(rng.uniform(0.4, 1.0)), -1, _cv2.LINE_AA)
    field = _norm_(_cv2.GaussianBlur(img, (0, 0), 0.5) + 0.03)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _widow_braid_fine(h, w, seed, *, res=600, webs=9):
    """fs_widow_braid crush + differentiate: MANY small spider webs (crushed ~3x, finer threads)
    tiled across the frame with a faint silk-haze ground so there are no gaps — a fine braided
    web lace, distinct from the sparse single big web of spiderweb()."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(webs)):
        cx, cy = float(rng.uniform(0.05, 0.95) * res), float(rng.uniform(0.05, 0.95) * res)
        spokes = int(rng.integers(9, 14))
        R = float(rng.uniform(0.10, 0.20) * res)            # SMALL webs (was 0.3-0.5)
        for s in range(spokes):
            a = 2 * np.pi * s / spokes
            _cv2.line(img, (int(cx), int(cy)),
                      (int(cx + np.cos(a) * R), int(cy + np.sin(a) * R)), 0.65, 1, _cv2.LINE_AA)
        for rr in np.linspace(R * 0.14, R, 7):              # concentric capture threads (braid)
            pts = [(cx + np.cos(2 * np.pi * s / spokes) * rr,
                    cy + np.sin(2 * np.pi * s / spokes) * rr) for s in range(spokes + 1)]
            _cv2.polylines(img, [np.array(pts, np.int32)], False, 0.8, 1, _cv2.LINE_AA)
    silk = _fbm(res, res, rng, 6, 8).astype(np.float32)     # faint silk haze -> full coverage
    field = _norm_(_cv2.GaussianBlur(img, (0, 0), 0.5) * 0.92 + silk * 0.15)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _prism_mesh(h, w, seed, *, res=600, cells=46):
    """fs_shattered_prism REPLACE (was 50: 'way too many like this' — NO more shatter/voronoi):
    a brand-new structure = a dense MICRO-PRISM SHEET. A fine regular grid of tiny triangular
    facets (linear-prism film), each split along its diagonal into two slopes that catch the
    light differently, with crisp facet seams and a fine spectral shimmer modulating across the
    sheet. Geometric, periodic, fully covered, fine — distinct from every crack/cell finish."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / float(cells)
    u = (gx / s) % 1.0
    vv = (gy / s) % 1.0
    cellx = np.floor(gx / s); celly = np.floor(gy / s)
    # split each square cell along a diagonal into two triangular prism facets w/ opposite slope
    upper = (u + vv) < 1.0
    slope = np.where(upper, u + vv, 2.0 - (u + vv))         # 0..1 ramp up each prism face
    # alternate the diagonal direction in a checker so facets fan in 4 orientations (microprism)
    flip = ((cellx + celly) % 2).astype(bool)
    slope = np.where(flip, 1.0 - slope, slope)
    facet = 0.25 + 0.75 * slope
    seam = ((np.minimum(u, 1.0 - u) < 0.06) | (np.minimum(vv, 1.0 - vv) < 0.06)
            | (np.abs(u + vv - 1.0) < 0.07)).astype(np.float32)         # crisp triangular seams
    shimmer = 0.5 + 0.5 * np.sin((cellx * 0.7 + celly * 1.3) + float(rng.uniform(0, 6.28)))  # per-facet spectral tint
    field = _norm_(facet * (0.7 + 0.3 * shimmer) + seam * 0.55)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _guilloche_fine(h, w, seed, *, res=600, reps=9):
    """fs_guilloche_ghost crush (was 40: too big/blobby/no fine detail): MANY more, much smaller
    engine-turned epicycloid rosettes (reps 4 -> 9 => ~5x more), thin crisp lines, plus a faint
    interlacing rosette layer offset half a cell so the lace is continuous (no blobby gaps). The
    spec recipe boosts trace_strength + drops the calm floor so ignition rides the FINE lines."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    ts = np.linspace(0, 2 * np.pi, 520)
    s = res / float(reps)
    for layer, (ox, oy, gain) in enumerate([(0.0, 0.0, 1.0), (0.5, 0.5, 0.7)]):
        for i in range(reps + 1):
            for j in range(reps + 1):
                cx, cy = (i + ox) * s, (j + oy) * s
                R = s * 0.5
                r1 = float(rng.uniform(0.3, 0.5)); k = int(rng.integers(5, 10))
                x = cx + R * ((1 - r1) * np.cos(ts) + r1 * np.cos((1 - r1) / r1 * ts * k))
                y = cy + R * ((1 - r1) * np.sin(ts) - r1 * np.sin((1 - r1) / r1 * ts * k))
                _cv2.polylines(img, [np.stack([x, y], 1).astype(np.int32)], True,
                               0.9 * gain, 1, _cv2.LINE_AA)
    return _cv2.resize(_norm_(_cv2.GaussianBlur(img, (0, 0), 0.4)), (w, h), interpolation=_cv2.INTER_CUBIC)


def _circuit_dense(h, w, seed, *, res=600, gridn=66):
    """fs_circuit_soul crush (was 65: blank/big/blobby/no fine detail): a MUCH denser PCB —
    finer grid + ~3x the trace walks + small pads/vias, over a faint ground-plane fbm + dim trace
    haze so there are no blank spots. Fine, full coverage, distinct from the wide circuit_maze."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / float(gridn)
    for _ in range(int(gridn * 8)):                          # ~3x denser than circuitry()
        px, py = int(rng.integers(0, gridn)) * s, int(rng.integers(0, gridn)) * s
        for _step in range(int(rng.integers(4, 11))):
            if rng.random() < 0.5:
                nx, ny = px + float(rng.choice([-1, 1])) * s, py
            else:
                nx, ny = px, py + float(rng.choice([-1, 1])) * s
            _cv2.line(img, (int(px % res), int(py % res)),
                      (int(nx % res), int(ny % res)), 0.8, 1, _cv2.LINE_AA)
            px, py = nx % res, ny % res
        _cv2.circle(img, (int(px), int(py)), 2, 1.0, -1, _cv2.LINE_AA)   # small pad/via
    traces = _cv2.GaussianBlur(img, (0, 0), 0.5)
    plane = _fbm(res, res, rng, 5, 7).astype(np.float32)     # faint ground plane -> coverage
    haze = _cv2.GaussianBlur(img, (0, 0), 4.0) * 0.5         # dim trace bloom fills gaps
    field = _norm_(traces * 0.9 + haze + plane * 0.14 + 0.04)
    return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_CUBIC)


def _geode_vein_banded(h, w, seed, *, res=600, cores=5):
    """fs_geode_vein rework (was 50: doesn't match name / too similar): a clearly BANDED agate
    GEODE — strong concentric high-contrast growth bands rippling around several cores, dark
    chalcedony VEIN seams between the lobes, and a bright druzy sparkle crust at each core.
    Distinct banded look (warm-amber palette in the recipe) vs the teal cell/vein finishes."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cores), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, idx = cKDTree(pts).query(q, k=2)
    F1 = d[:, 0].reshape(res, res); F2 = d[:, 1].reshape(res, res)
    nF1 = _norm_(F1)
    # high-contrast concentric agate bands (sharpened sine -> crisp banding, not a soft ramp)
    band_raw = 0.5 + 0.5 * np.sin(nF1 * np.pi * 30.0 + float(rng.uniform(0, 6.28)))
    bands = np.clip((band_raw - 0.35) * 2.4, 0, 1)
    vein = np.clip(1.0 - _norm_(F2 - F1) * 7.0, 0, 1)        # dark chalcedony seam between lobes
    core = np.clip(1.0 - nF1 * 5.0, 0, 1)
    druzy = (_fbm(res, res, rng, 7, 1) > 0.66).astype(np.float32) * core   # sparkly crystal core crust
    field = _norm_(bands * 0.7 + core * 0.35 + druzy * 0.6 - vein * 0.45)
    return _cv2.resize(np.clip(field, 0, 1), (w, h), interpolation=_cv2.INTER_CUBIC)


# Local engines registry (resolved before falling back to fractured_math by name).
_LOCAL_ENGINES = {
    "_code_binary": _code_binary,
    "_frost_feather_deep": _frost_feather_deep,
    "_frost_lace_deep": _frost_lace_deep,
    "_riverine_deep": _riverine_deep,
    "_tsunami_fine": _tsunami_fine,
    "_petal_storm_dense": _petal_storm_dense,
    "_octo_suckers_fine": _octo_suckers_fine,
    "_thousand_eyes_deep": _thousand_eyes_deep,
    "_witchlight_fine": _witchlight_fine,
    "_gyro_cage_fine": _gyro_cage_fine,
    "_gyroid_fine": _gyroid_fine,
    # ── SOULS crush fix (2026-06-17) ──
    "_moth_dust_fine": _moth_dust_fine,
    "_night_tide_deep": _night_tide_deep,
    "_static_veins_fine": _static_veins_fine,
    "_embers_dense": _embers_dense,
    "_carnival_lights": _carnival_lights,
    "_widow_braid_fine": _widow_braid_fine,
    "_prism_mesh": _prism_mesh,
    "_guilloche_fine": _guilloche_fine,
    "_circuit_dense": _circuit_dense,
    "_geode_vein_banded": _geode_vein_banded,
}

# Post-process crush: fid -> callable(field, seed)->field. For knob-less crushes + added texture.
def _diamondback_post(field, seed):
    """Crush ~75% (tile finer 2x on top of the cells=26 bump) AND add fine background texture
    between the diamond chain so the dark ground isn't bare."""
    f = _tile_finer_(field, 2)
    rng = _rng(seed + 13)
    bg = _fbm(field.shape[0], field.shape[1], rng, 6, 8).astype(np.float32)
    return _norm_(f * 0.9 + bg * 0.18)


def _flame_lick_post(field, seed):
    """Crush ~50%: tile the discrete tongues 2x so each licking flame is ~half size, twice as many."""
    return _tile_finer_(field, 2)


_POST = {
    "fm_diamondback": _diamondback_post,
    "fm_flame_lick": _flame_lick_post,
}

# Stamp each recipe with its own id so _field can look up the right _POST crush.
for _fid, _rec in RECIPES.items():
    _rec["_fid"] = _fid


def _norm_(a):
    a = np.asarray(a, np.float32)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-9)


def _tile_finer_(field, k=2):
    """Local mirror of fm._tile_finer (crush feature scale: tile kxk then resize back)."""
    return fm._tile_finer(field, k)


def _seed_int(seed):
    try:
        return int(seed)
    except Exception:
        return abs(hash(str(seed))) % (2 ** 31)


def _field(d, work):
    eng = d["engine"]
    if eng == "_drift":
        fn = _drift
    elif eng in _LOCAL_ENGINES:
        fn = _LOCAL_ENGINES[eng]
    else:
        fn = getattr(fm, eng)
    field = fn(work, work, _seed_int(d["seed"]), **d.get("eargs", {}))
    post = _POST.get(d.get("_fid"))
    if post is not None:
        field = post(field, _seed_int(d["seed"]))
    return field


def _art_work(d):
    field = _field(d, _WORK)
    return np.clip(fm.colorize(field, d["base"], d["glow"], d["edge"], **d["kw"]), 0.0, 1.0)


@lru_cache(maxsize=8)
def _art_work_cached(fid):
    return _art_work(RECIPES[fid])


def _mk(fid):
    d = RECIPES[fid]
    sargs = d.get("sargs", {})

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
        ts = sargs.get("trace_strength", 1.0)
        cf = sargs.get("calm_floor", 30.0)
        if fid in _TRACE_BOOST:                  # advisory finishes: force stronger spec tracery
            ts = max(ts, 2.0)
            cf = min(cf, 19.0)
        return fracture_spec(art, m2,
                             ignition=sargs.get("ignition", 1.0),
                             trace_strength=ts,
                             calm_floor=cf,
                             decorrelation=sargs.get("decorrelation", 0.18),
                             as_uint8=True)

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
    n = 0
    for fid in RECIPES:
        if fid in KEEPERS:
            continue
        entry = _mk(fid)
        for reg in regs:
            reg[fid] = entry
        n += 1
    return f"fractured-rebuild: {n} MINDS/SOULS finishes rebuilt with bespoke patterns"
