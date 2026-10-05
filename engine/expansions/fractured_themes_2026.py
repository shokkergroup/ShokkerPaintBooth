"""FRACTURED themed categories (2026-06-17) — 5 NEW themed groups x 20 finishes each:
  🌊 FRACTURED DEEP · 👣 FRACTURED CRYPTID · 🛸 FRACTURED UFO · 🌈 FRACTURED RAINBOW · 🔮 FRACTURED OCCULT

Same machine as FRACTURED FORGE (fractured_forge_2026): a math engine in
engine/paint_v2/fractured_math.py produces an intricate full-canvas FIELD (or RGB for the multi-hue
traced-cell engines), colorize()/the engine turns it into dark-albedo art, and the canonical
fracture_spec() ignites it. These are ABSTRACT spec-map finishes evoking each theme (NOT literal
scenes), registered as monolithics. Recipe schema mirrors FORGE exactly.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

import engine.paint_v2.fractured_math as fm
from engine.spec_sculpt.fracture import fracture_spec
from engine.expansions.fractured_wilds_signatures_2026 import make_entry as _wilds_entry

_WORK = 1152

# ── 🌊 FRACTURED DEEP — abyssal deep-sea ──
DEEP = {
 "fd_anglerfish": dict(name="Anglerfish", engine="abyss_lure", eargs={}, seed=401,
    base=(2, 6, 10), glow=(30, 150, 160), edge=(190, 250, 255),
    kw=dict(gamma=0.85, edge_gain=0.9, ambient=0.4, ambient_sigma=58, ambient_floor=0.3),
    desc="A few intense bioluminescent lures glowing in dark deep-water currents — anglerfish in the abyss."),
 "fd_jellyfall": dict(name="Jellyfall", engine="jelly_drift", eargs={}, seed=402,
    base=(4, 6, 12), glow=(110, 60, 170), edge=(170, 220, 255),
    kw=dict(gamma=0.9, edge_gain=0.8, ambient=0.38, ambient_sigma=55, ambient_floor=0.3),
    desc="Soft glowing bells drifting on a slow current — a bloom of violet-and-blue jellyfish."),
 "fd_hadal_glow": dict(name="Hadal Glow", engine="hadal_glow", eargs={}, seed=403,
    base=(3, 9, 11), glow=(26, 120, 120), edge=(170, 255, 245), kw=dict(gamma=0.9, edge_gain=0.9),
    desc="A refracted caustic light-net warped through the deep — hadal-zone pooled aqua light."),
 "fd_bioluminescence": dict(name="Bioluminescence", engine="bioluminescence", eargs={}, seed=404,
    base=(2, 7, 9), glow=(30, 160, 140), edge=(180, 255, 210),
    kw=dict(gamma=0.9, edge_gain=0.95, ambient=0.4, ambient_sigma=55, ambient_floor=0.3),
    desc="Glowing plankton speckle scattered over a slow deep-current glow — bioluminescent water."),
 "fd_ripple_glass": dict(name="Ripple Glass", engine="ripple_glass",
    eargs=dict(sources=18, bands=28, palette=[(20, 130, 150), (60, 45, 165), (20, 95, 95)], edge=(180, 250, 255)), seed=405,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Concentric water-ripple cell bands in deep teal, violet and aqua shades, edged by bright ignitable wavefronts."),
 # ── DEEP batch 2 ──
 "fd_hydrothermal": dict(name="Hydrothermal Vent", engine="vent_plume", eargs={}, seed=406,
    base=(10, 4, 2), glow=(180, 80, 25), edge=(255, 180, 90),
    kw=dict(gamma=0.85, edge_gain=0.85, ambient=0.4, ambient_sigma=55, ambient_floor=0.32),
    desc="Mineral-rich black-smoker plumes rising through dark water — copper-and-ember hydrothermal vents."),
 "fd_maelstrom": dict(name="Maelstrom", engine="maelstrom", eargs={}, seed=407,
    base=(3, 8, 12), glow=(28, 110, 140), edge=(170, 230, 255), kw=dict(gamma=0.9, edge_gain=1.0),
    desc="Spiral phase-waves churned through a caustic field — a deep whirlpool maelstrom."),
 "fd_kelp_drift": dict(name="Kelp Drift", engine="kelp_drift", eargs={}, seed=408,
    base=(4, 9, 6), glow=(40, 120, 50), edge=(180, 230, 120), kw=dict(gamma=0.95, edge_gain=0.75),
    desc="Strands swaying in a slow current — a drifting deep-green kelp forest."),
 "fd_cephalopod": dict(name="Cephalopod", engine="cephalopod", eargs={}, seed=409,
    base=(8, 5, 12), glow=(120, 50, 130), edge=(200, 150, 230), kw=dict(gamma=0.95, edge_gain=0.8),
    desc="Rows of suckers warped over a tentacle — iridescent violet deep cephalopod skin."),
 "fd_nacre": dict(name="Nacre", engine="nacre", eargs={}, seed=410,
    base=(8, 9, 12), glow=(120, 130, 150), edge=(220, 210, 235), kw=dict(gamma=1.0, edge_gain=0.7),
    desc="Thin-film pearl iridescence over warped marble — deep mother-of-pearl nacre."),
 "fd_sonar_glass": dict(name="Sonar Glass", engine="sonar_glass",
    eargs=dict(cells=64, bands=7, palette=[(20, 140, 160), (60, 50, 165), (25, 100, 110)], edge=(170, 250, 255)), seed=411,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Voronoi cells ringed by concentric sonar bands in deep teal, violet and aqua shades, traced by bright ignitable contours."),
 "fd_brine_glass": dict(name="Brine Glass", engine="cobble_glass",
    eargs=dict(n=20, palette=[(25, 120, 130), (40, 90, 160), (30, 140, 120)], edge=(180, 245, 235)), seed=412,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Evenly-packed brine-pool cells in deep teal, blue and jade shades, set in bright ignitable salt-rims."),
 # ── DEEP batch 3 (swarm) ──
 "fd_krakenink": dict(name="Kraken Ink", engine="dpx_krakenink", eargs={}, seed=421,
    base=(4, 6, 12), glow=(60, 40, 150), edge=(170, 200, 255),
    kw=dict(gamma=0.9, edge_gain=0.9, ambient=0.38, ambient_sigma=55, ambient_floor=0.3),
    desc="Many fine ink filaments swirling through dark water — a kraken's violet-and-blue ink discharge. FRACTURED DEEP finish."),
 "fd_whalefall": dict(name="Whale Fall", engine="dpx_whalefall", eargs={}, seed=422,
    base=(6, 8, 7), glow=(40, 150, 110), edge=(190, 255, 200),
    kw=dict(gamma=0.88, edge_gain=0.85, ambient=0.4, ambient_sigma=58, ambient_floor=0.32),
    desc="A fine branching skeleton crawling with tiny glowing bone-eaters over a dim seafloor glow — a whale fall on the abyssal plain. FRACTURED DEEP finish."),
 "fd_abyssalsnow": dict(name="Abyssal Snow", engine="dpx_abyssalsnow", eargs={}, seed=423,
    base=(3, 7, 11), glow=(110, 160, 190), edge=(210, 240, 255),
    kw=dict(gamma=0.92, edge_gain=0.8, ambient=0.42, ambient_sigma=55, ambient_floor=0.34),
    desc="A dense fall of fine marine-snow flakes drifting on a slow current through the deep water column — abyssal snow. FRACTURED DEEP finish."),
 "fd_eeldischarge": dict(name="Electric Eel", engine="dpx_eeldischarge", eargs={}, seed=424,
    base=(3, 6, 10), glow=(40, 170, 200), edge=(200, 255, 255),
    kw=dict(gamma=0.85, edge_gain=1.0, ambient=0.32, ambient_sigma=52, ambient_floor=0.28),
    desc="Many fine branched arcs crackling across a resonant standing field — an electric eel discharging in the dark deep. FRACTURED DEEP finish."),
 "fd_pressurestrata": dict(name="Pressure Strata", engine="dpx_pressurestrata", eargs={}, seed=425,
    base=(7, 8, 11), glow=(30, 110, 130), edge=(170, 220, 240),
    kw=dict(gamma=0.95, edge_gain=0.85, ambient=0.35, ambient_sigma=55, ambient_floor=0.3),
    desc="Many thin compressed sediment laminae folded and fractured under crushing depth — abyssal pressure strata. FRACTURED DEEP finish."),
 "fd_siphonophore": dict(name="Siphonophore", engine="dpx_siphonophore",
    eargs=dict(rows=22, palette=[(20, 135, 150), (95, 50, 165), (25, 110, 120)], edge=(180, 250, 255)), seed=426,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A long chain of small glowing zooid bodies in deep teal, violet and aqua, strung on bright ignitable filaments — a drifting siphonophore colony. FRACTURED DEEP finish."),
 "fd_glasssquid": dict(name="Glass Squid", engine="dpx_glasssquid",
    eargs=dict(cells=20, palette=[(25, 140, 145), (35, 110, 165), (175, 130, 35)], edge=(190, 250, 255)), seed=427,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Evenly-packed translucent body cells in deep aqua, cyan and lure-gold, set in bright ignitable glassy membranes — a transparent glass squid in the deep. FRACTURED DEEP finish."),
 "fd_trenchfault": dict(name="Trench Fault", engine="dpx_trenchfault",
    eargs=dict(cols=18, palette=[(20, 120, 140), (40, 80, 165), (90, 55, 160)], edge=(170, 245, 255)), seed=428,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Offset cold-rock fault blocks in deep teal, blue and violet, split by bright ignitable fissure lines — a fractured deep-sea trench fault. FRACTURED DEEP finish."),
}

# ── 👣 FRACTURED CRYPTID · 🛸 FRACTURED UFO · 🌈 FRACTURED RAINBOW · 🔮 FRACTURED OCCULT (loop fills) ──
CRYPTID = {
 "fc_sasquatch_fur": dict(name="Sasquatch Fur", engine="cry_sasquatch_fur", eargs={}, seed=500, base=(10, 8, 6), glow=(120, 95, 60), edge=(210, 185, 140), kw=dict(gamma=0.95, edge_gain=0.8), desc="Matted shaggy strands curl-laid into a dense coat over a dark under-fur — a sasquatch pelt FRACTURED CRYPTID finish."),
 "fc_quill_bristle": dict(name="Quill Bristle", engine="cry_quill_bristle", eargs={}, seed=501, base=(8, 7, 6), glow=(140, 120, 90), edge=(220, 205, 170), kw=dict(gamma=0.9, edge_gain=0.85), desc="Dense fine porcupine bristles raked over a pebbled hide — a quilled-cryptid FRACTURED CRYPTID finish."),
 "fc_coarse_hide": dict(name="Coarse Hide", engine="cry_coarse_hide", eargs={}, seed=502, base=(9, 8, 7), glow=(110, 90, 70), edge=(190, 165, 130), kw=dict(gamma=0.95, edge_gain=0.9), desc="Fine warped leather plates over a tight pebble grain — coarse wrinkled cryptid hide FRACTURED CRYPTID finish."),
 "fc_eyeshine": dict(name="Eyeshine", engine="cry_eyeshine", eargs={}, seed=503, base=(3, 5, 4), glow=(40, 200, 90), edge=(200, 255, 160), kw=dict(gamma=0.85, edge_gain=0.95, ambient=0.35, ambient_sigma=58, ambient_floor=0.28), desc="Many small slit eye-spots glowing back from a near-black forest murk — an eyeshine FRACTURED CRYPTID finish."),
 "fc_bog_murk": dict(name="Bog Murk", engine="cry_bog_murk", eargs={}, seed=504, base=(4, 10, 9), glow=(25, 130, 120), edge=(150, 230, 210), kw=dict(gamma=0.9, edge_gain=0.85, ambient=0.35, ambient_sigma=55, ambient_floor=0.28), desc="Churning teal water veins threaded with bioluminescent scum — a still-black bog FRACTURED CRYPTID finish."),
 "fc_claw_rake": dict(name="Claw Rake", engine="cry_claw_rake", eargs={}, seed=505, base=(10, 8, 7), glow=(150, 60, 40), edge=(230, 150, 110), kw=dict(gamma=0.95, edge_gain=0.95), desc="Sets of fine taper slashes raking across a dark hide at every angle — a claw-rake FRACTURED CRYPTID finish."),
 "fc_bark_camo": dict(name="Bark Camo", engine="cry_bark_camo", eargs={}, seed=506, base=(7, 9, 6), glow=(80, 100, 55), edge=(170, 190, 120), kw=dict(gamma=0.95, edge_gain=0.8), desc="Furrowed bark ridge-veins broken by a fine forest-shadow contour web — a bark-camo FRACTURED CRYPTID finish."),
 "fc_feathered_wing": dict(name="Feathered Wing", engine="cry_feathered_wing", eargs={}, seed=507, base=(8, 8, 9), glow=(95, 105, 120), edge=(200, 210, 230), kw=dict(gamma=0.95, edge_gain=0.8), desc="Dense overlapping feather fans layered into fine barbed plumage — a feathered-wing FRACTURED CRYPTID finish."),
 "fc_dorsal_ridge": dict(name="Dorsal Ridge", engine="cry_dorsal_ridge", eargs={}, seed=508, base=(6, 9, 7), glow=(50, 120, 80), edge=(160, 230, 170), kw=dict(gamma=0.95, edge_gain=0.85), desc="Rows of fine keeled arc-scales curl-warped into a running spine of ridges — a reptilian dorsal-ridge FRACTURED CRYPTID finish."),
 "fc_webbed_membrane": dict(name="Webbed Membrane", engine="cry_webbed_membrane", eargs={}, seed=509, base=(5, 9, 9), glow=(40, 130, 130), edge=(170, 240, 230), kw=dict(gamma=0.9, edge_gain=0.9), desc="A fine vein-network bounding stretched translucent cells — the webbing of a swamp-cryptid's hand, a FRACTURED CRYPTID finish."),
 "fc_toad_skin": dict(name="Toad Skin", engine="cry_toad_skin", eargs={}, seed=510, base=(7, 9, 6), glow=(70, 120, 60), edge=(160, 220, 130), kw=dict(gamma=0.95, edge_gain=0.85), desc="Tightly hex-packed warty beads mottled over a damp sheen — a warty bog-toad FRACTURED CRYPTID finish."),
 "fc_antler_bone": dict(name="Antler Bone", engine="cry_antler_bone", eargs={}, seed=511, base=(8, 8, 7), glow=(130, 120, 95), edge=(220, 210, 180), kw=dict(gamma=0.95, edge_gain=0.85, ambient=0.3, ambient_sigma=55, ambient_floor=0.25), desc="Dense small branching tines and bone-forks scattered at every angle — an antler/bone FRACTURED CRYPTID finish."),
 "fc_mossy_stone": dict(name="Mossy Stone", engine="cry_mossy_stone", eargs={}, seed=512, base=(8, 9, 7), glow=(75, 105, 55), edge=(165, 195, 120), kw=dict(gamma=0.95, edge_gain=0.8), desc="Fine cracked stone plates with moss speckle pooling in the seams — a lichen-furred boulder FRACTURED CRYPTID finish."),
 "fc_will_o_wisp": dict(name="Will-o'-Wisp", engine="cry_will_o_wisp", eargs={}, seed=513, base=(3, 6, 5), glow=(60, 200, 130), edge=(190, 255, 210), kw=dict(gamma=0.85, edge_gain=0.9, ambient=0.4, ambient_sigma=58, ambient_floor=0.3), desc="A dense swarm of small drifting bog-lights trailing wisps over a black marsh — a will-o'-the-wisp FRACTURED CRYPTID finish."),
 "fc_snakeskin": dict(name="Snakeskin", engine="cry_snakeskin", eargs={}, seed=514, base=(8, 9, 6), glow=(90, 110, 55), edge=(190, 205, 120), kw=dict(gamma=0.95, edge_gain=0.85), desc="A fine diamond scale lattice broken by dark blotch banding — a serpent-cryptid snakeskin FRACTURED CRYPTID finish."),
 "fc_batwing": dict(name="Bat Wing", engine="cry_batwing", eargs={}, seed=515, base=(8, 6, 9), glow=(90, 60, 110), edge=(190, 160, 220), kw=dict(gamma=0.9, edge_gain=0.85), desc="Fine wing-vein cells stretched over a wrinkled membrane — a leathery bat/mothman wing FRACTURED CRYPTID finish."),
 "fc_gator_hide": dict(name="Gator Hide", engine="cry_gator_hide", eargs={}, seed=516, base=(7, 9, 6), glow=(70, 100, 55), edge=(160, 195, 120), kw=dict(gamma=0.95, edge_gain=0.85), desc="Fine bulging scutes in deep grooves with a few raised keel ridges — an armored gator-hide FRACTURED CRYPTID finish."),
 "fc_hide_scale_glass": dict(name="Hide Scale Glass", engine="cry_hide_scale_glass", eargs=dict(cells=144, palette=[(60, 95, 45), (95, 110, 55), (70, 80, 60)], edge=(170, 210, 110)), seed=518, base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={}, sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0), desc="Fine mottled forest-hued hide-scale cells, each a different shade, set in a bright ignitable scale-rim — a multi-tone hide FRACTURED CRYPTID finish."),
 "fc_dragon_hex_glass": dict(name="Dragon Hex Glass", engine="cry_dragon_hex_glass", eargs=dict(cells=24, palette=[(45, 80, 50), (40, 55, 45), (120, 80, 30)], edge=(210, 150, 60)), seed=519, base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={}, sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0), desc="Hex-packed dragon-hide scutes in swamp-green, charcoal and amber shades, traced by bright ignitable keels — a dragon-cryptid FRACTURED CRYPTID finish."),
 "fc_crackle_eyeshine_glass": dict(name="Crackle Eyeshine Glass", engine="cry_crackle_eyeshine_glass", eargs=dict(cells=130, palette=[(35, 45, 30), (30, 35, 38), (45, 38, 28)], edge=(240, 200, 60)), seed=520, base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={}, sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0), desc="Dark hide-toned crackle cells traced by a bright ignitable amber/green eyeshine seam-web — countless little eyes glinting along the cracks, a FRACTURED CRYPTID finish."),
}
UFO = {
 "fu_saucer_alloy": dict(name="Saucer Alloy", engine="ufx_saucer_alloy", eargs={}, seed=600,
    base=(10, 12, 14), glow=(150, 170, 190), edge=(225, 235, 250),
    kw=dict(gamma=1.0, edge_gain=0.8),
    desc="Dense machined turn-rings in brushed gunmetal hull alloy — a saucer's spun-metal underbelly. FRACTURED UFO finish."),
 "fu_tractor_beam": dict(name="Tractor Beam", engine="ufx_tractor_rings", eargs={}, seed=601,
    base=(4, 10, 6), glow=(40, 210, 120), edge=(170, 255, 200),
    kw=dict(gamma=0.9, edge_gain=0.95, ambient=0.4, ambient_sigma=55, ambient_floor=0.3),
    desc="A field of abduction-green beam wells pulsing tight concentric tractor rings. FRACTURED UFO finish."),
 "fu_alien_circuit": dict(name="Alien Circuit", engine="ufx_alien_circuitry", eargs={}, seed=602,
    base=(4, 8, 10), glow=(30, 170, 180), edge=(160, 255, 255),
    kw=dict(gamma=0.85, edge_gain=1.0),
    desc="Glowing extraterrestrial PCB traces with dense pads and vias on a fine grid. FRACTURED UFO finish."),
 "fu_glyph_grid": dict(name="Glyph Grid", engine="ufx_glyph_grid", eargs={}, seed=603,
    base=(6, 8, 4), glow=(120, 200, 40), edge=(210, 255, 150),
    kw=dict(gamma=0.9, edge_gain=0.95),
    desc="A tight inscribed matrix of small angular alien hieroglyph strokes and dots. FRACTURED UFO finish."),
 "fu_plasma_drive": dict(name="Plasma Drive", engine="ufx_plasma_drive", eargs={}, seed=604,
    base=(10, 4, 12), glow=(180, 40, 170), edge=(255, 160, 255),
    kw=dict(gamma=0.85, edge_gain=0.9, ambient=0.4, ambient_sigma=52, ambient_floor=0.3),
    desc="Many small plasma cores throwing radial ion filaments — a magenta engine bloom. FRACTURED UFO finish."),
 "fu_crop_circle": dict(name="Crop Circle", engine="ufx_crop_circle", eargs={}, seed=605,
    base=(6, 9, 5), glow=(60, 180, 70), edge=(190, 255, 170),
    kw=dict(gamma=0.95, edge_gain=0.95),
    desc="Scattered flattened-ring agroglyphs with spokes and satellites in a field of grain. FRACTURED UFO finish."),
 "fu_abduction_shaft": dict(name="Abduction Shafts", engine="ufx_abduction_shafts", eargs={}, seed=606,
    base=(5, 11, 6), glow=(50, 220, 110), edge=(180, 255, 190),
    kw=dict(gamma=0.9, edge_gain=0.8, ambient=0.45, ambient_sigma=55, ambient_floor=0.32),
    desc="A leaning forest of thin tapering abduction-light columns with floating dust motes. FRACTURED UFO finish."),
 "fu_oil_iridescent": dict(name="Oil Iridescence", engine="ufx_oil_iridescence", eargs={}, seed=607,
    base=(8, 8, 12), glow=(120, 130, 170), edge=(230, 200, 255),
    kw=dict(gamma=1.0, edge_gain=0.85),
    desc="Otherworldly thin-film petrol-sheen banding warped over alien hull grain. FRACTURED UFO finish."),
 "fu_hyperspace": dict(name="Hyperspace", engine="ufx_hyperspace", eargs={}, seed=608,
    base=(5, 7, 12), glow=(60, 140, 255), edge=(200, 230, 255),
    kw=dict(gamma=0.9, edge_gain=1.0),
    desc="Four warp-jump star tunnels of thousands of short radial light-streaks. FRACTURED UFO finish."),
 "fu_wormhole": dict(name="Wormhole", engine="ufx_wormhole_rings", eargs={}, seed=609,
    base=(8, 5, 12), glow=(140, 60, 200), edge=(210, 170, 255),
    kw=dict(gamma=0.9, edge_gain=0.95, ambient=0.38, ambient_sigma=55, ambient_floor=0.3),
    desc="A field of small spacetime funnels with nested rings twisted by a swirl phase. FRACTURED UFO finish."),
 "fu_reactor_core": dict(name="Reactor Lattice", engine="ufx_reactor_lattice", eargs={}, seed=610,
    base=(4, 10, 9), glow=(40, 200, 150), edge=(170, 255, 220),
    kw=dict(gamma=0.85, edge_gain=1.0),
    desc="An isometric strut scaffold charged by a fine energy-pulse overlay — an antimatter core. FRACTURED UFO finish."),
 "fu_biomech_skin": dict(name="Bio-Mech Skin", engine="ufx_biomech_skin", eargs={}, seed=611,
    base=(6, 9, 7), glow=(60, 160, 100), edge=(180, 240, 200),
    kw=dict(gamma=0.95, edge_gain=0.85),
    desc="A living membrane of fine warped chitin cells and tube seams — bio-mechanical alien hide. FRACTURED UFO finish."),
 "fu_hex_hull": dict(name="Hex Hull", engine="ufx_hex_hull", eargs={}, seed=612,
    base=(10, 11, 13), glow=(120, 150, 170), edge=(210, 235, 250),
    kw=dict(gamma=1.0, edge_gain=0.85),
    desc="Tight beveled hexagonal armor cells with seam highlights — small-scale ship-hull plating. FRACTURED UFO finish."),
 "fu_nebula_portal": dict(name="Nebula Portal", engine="ufx_nebula_portal", eargs={}, seed=614,
    base=(8, 6, 12), glow=(120, 50, 180), edge=(200, 160, 255),
    kw=dict(gamma=0.9, edge_gain=0.85, ambient=0.42, ambient_sigma=58, ambient_floor=0.3),
    desc="A churning interdimensional cloud pierced by bright ignition knots and a star speckle. FRACTURED UFO finish."),
 "fu_stargate": dict(name="Star-Gate", engine="ufx_stargate_spiral", eargs={}, seed=615,
    base=(5, 9, 11), glow=(40, 190, 200), edge=(170, 250, 255),
    kw=dict(gamma=0.9, edge_gain=0.95),
    desc="Four interlocking phase-vortex event-gates winding tight rippling arms. FRACTURED UFO finish."),
 "fu_antigrav": dict(name="Antigrav Ripple", engine="ufx_antigrav_ripple", eargs={}, seed=616,
    base=(6, 11, 8), glow=(50, 210, 130), edge=(180, 255, 200),
    kw=dict(gamma=0.9, edge_gain=0.9),
    desc="Many overlapping concentric pressure-wave fronts quivering — a repulsor field. FRACTURED UFO finish."),
 "fu_scanner_sweep": dict(name="Scanner Sweep", engine="ufx_scanner_sweep", eargs={}, seed=617,
    base=(4, 10, 8), glow=(40, 200, 140), edge=(170, 255, 210),
    kw=dict(gamma=0.9, edge_gain=0.95),
    desc="Fine diagonal scan-lines crossed by a sweeping gradient with bright detection ticks. FRACTURED UFO finish."),
 "fu_hull_cells": dict(name="Hull Cells", engine="ufx_hull_cells", seed=618,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(cells=120, palette=[(30, 150, 110), (40, 120, 160), (95, 70, 160)], edge=(150, 245, 220)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A fine mothership-hull plating of small alien-alloy panes in jade, blue and violet, ringed by bright ignitable seams. FRACTURED UFO finish."),
 "fu_glyph_cells": dict(name="Glyph Cells", engine="ufx_glyph_cells", seed=619,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(cells=22, palette=[(40, 160, 150), (160, 50, 170), (50, 90, 200)], edge=(170, 250, 255)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A dense hex hieroglyph-panel array in teal, magenta and plasma blue, each rune cell edged by a bright ignitable rim. FRACTURED UFO finish."),
 "fu_portal_rings": dict(name="Portal Rings", engine="ufx_portal_rings", seed=620,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(rings=18, sectors=14, palette=[(40, 170, 90), (60, 70, 165), (30, 140, 120)], edge=(120, 255, 180)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Concentric ring-sector portal cells in abduction green and void purple, traced by bright ignitable arcs. FRACTURED UFO finish."),
}
RAINBOW = {
 "fr_prism_shatter": dict(name="Prism Shatter", engine="rbw_prism_cells", seed=700,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(cells=150, palette=[(220, 40, 40), (235, 150, 25), (235, 220, 30), (40, 175, 70), (40, 95, 215), (150, 50, 195)], edge=(245, 250, 255)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Hundreds of small angular prism shards in vivid full-spectrum facets, traced by bright ignitable fault-lines. FRACTURED RAINBOW finish."),
 "fr_spectrum_voronoi": dict(name="Spectrum Voronoi", engine="rbw_spectrum_voronoi", seed=701,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(cells=26, palette=[(220, 40, 40), (235, 150, 25), (235, 220, 30), (40, 175, 70), (40, 95, 215), (150, 50, 195)], edge=(250, 250, 255)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Hundreds of evenly-packed rainbow Voronoi panes across the full spectrum, leaded by a bright ignitable lattice. FRACTURED RAINBOW finish."),
 "fr_hex_hive": dict(name="Spectrum Hex Hive", engine="rbw_hex_hive", seed=702,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(cells=30, palette=[(220, 40, 40), (235, 150, 25), (235, 220, 30), (40, 175, 70), (40, 95, 215), (150, 50, 195)], edge=(250, 250, 255)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A tight honeycomb of small full-spectrum hex cells, each ringed by a bright ignitable rim. FRACTURED RAINBOW finish."),
 "fr_kaleidoscope": dict(name="Kaleidoscope Tiles", engine="rbw_kaleidoscope", seed=703,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(cells=14, palette=[(220, 40, 40), (235, 150, 25), (235, 220, 30), (40, 175, 70), (40, 95, 215), (150, 50, 195)], edge=(250, 250, 255)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A grid of spinning four-wedge pinwheel tiles in full-spectrum hues — a kaleidoscope mosaic with bright ignitable spokes. FRACTURED RAINBOW finish."),
 "fr_chroma_rings": dict(name="Chroma Ripple Rings", engine="rbw_chroma_rings", seed=704,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(rings=26, sectors=18, palette=[(220, 40, 40), (235, 150, 25), (235, 220, 30), (40, 175, 70), (40, 95, 215), (150, 50, 195)], edge=(252, 250, 255)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Nine small concentric-ring rosettes split into rotating full-spectrum sectors, traced by bright ignitable ring-lines. FRACTURED RAINBOW finish."),
 "fr_rainbow_truchet": dict(name="Rainbow Truchet", engine="rbw_truchet", seed=705,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(tiles=20, palette=[(220, 40, 40), (235, 150, 25), (235, 220, 30), (40, 175, 70), (40, 95, 215), (150, 50, 195)], edge=(245, 250, 255)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Interlocking Truchet curved-arc tiles flowing through full-spectrum regions, seamed by bright ignitable arcs. FRACTURED RAINBOW finish."),
 "fr_prism_wheel": dict(name="Prism Wedge Wheel", engine="rbw_prism_wheel", seed=706,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(sectors=48, rings=11, palette=[(220, 40, 40), (235, 150, 25), (235, 220, 30), (40, 175, 70), (40, 95, 215), (150, 50, 195)], edge=(252, 250, 255)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Nine small shattered prism colour-wheels of radial wedge facets across the full spectrum, with bright ignitable spokes. FRACTURED RAINBOW finish."),
 "fr_iridescent_weave": dict(name="Iridescent Weave", engine="rbw_iris_weave", seed=707,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(cells=16, palette=[(220, 40, 40), (235, 150, 25), (235, 220, 30), (40, 175, 70), (40, 95, 215), (150, 50, 195)], edge=(250, 248, 255)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="An over-and-under basket-weave of full-spectrum thread tiles — an iridescent woven rainbow with bright ignitable seams. FRACTURED RAINBOW finish."),
 "fr_rainbow_caustics": dict(name="Rainbow Caustics", engine="rbw_caustic_cells", seed=708,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(sources=12, bands=26, palette=[(220, 40, 40), (235, 150, 25), (235, 220, 30), (40, 175, 70), (40, 95, 215), (150, 50, 195)], edge=(245, 250, 255)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Concentric ripple-caustic cell bands radiating from many scattered sources in full-spectrum hues, edged by bright ignitable wavefronts. FRACTURED RAINBOW finish."),
 "fr_opal_fire": dict(name="Opal Fire Cells", engine="rbw_opal_fire", seed=709,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(cells=90, palette=[(220, 40, 40), (235, 150, 25), (235, 220, 30), (40, 175, 70), (40, 95, 215), (150, 50, 195)], edge=(252, 250, 255)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Irregular crackle-glaze opal plates flashing full-spectrum opal fire, seamed by bright ignitable crack-lines. FRACTURED RAINBOW finish."),
 "fr_spectral_spiral": dict(name="Spectral Spiral", engine="rbw_spiral_prism", seed=710,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(arms=22, twist=20, palette=[(220, 40, 40), (235, 150, 25), (235, 220, 30), (40, 175, 70), (40, 95, 215), (150, 50, 195)], edge=(250, 248, 255)),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Nine small tight logarithmic-spiral prisms winding full-spectrum arms, traced by bright ignitable spiral seams. FRACTURED RAINBOW finish."),
 "fr_quasicrystal": dict(name="Spectral Quasicrystal", engine="rbw_quasi_cells", seed=711,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(bands=16),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A fine decagonal quasi-periodic interference lattice glowing the full spectrum, every fringe a vivid rainbow band with crisp ignitable contours. FRACTURED RAINBOW finish."),
 "fr_oil_slick": dict(name="Oil-Slick Iridescence", engine="rbw_oil_slick", seed=712,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(freq=12.0),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Curl-drifted oil-on-water thin-film iridescence beating into flowing full-spectrum bands with bright ignitable rims. FRACTURED RAINBOW finish."),
 "fr_holo_grating": dict(name="Holographic Grating", engine="rbw_holo_grating", seed=713,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(gratings=7),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Crossed high-frequency diffraction gratings splitting light into a dense field of fine full-spectrum holographic fringes. FRACTURED RAINBOW finish."),
 "fr_chroma_ripple": dict(name="Chromatic Aberration Ripple", engine="rbw_chroma_ripple", seed=714,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(halos=14),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Packed Newton-ring halos fringed with chromatic-aberration full-spectrum bands, edged by bright ignitable contours. FRACTURED RAINBOW finish."),
 "fr_dichroic_bands": dict(name="Dichroic Bands", engine="rbw_dichroic_bands", seed=715,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="High-frequency dichroic-glass stripes shifting angle across the panel, cycling the full spectrum with bright ignitable band-edges. FRACTURED RAINBOW finish."),
 "fr_holo_foil": dict(name="Holographic Foil", engine="rbw_holo_foil", seed=716,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Crinkled crystal-facet holographic foil throwing full-spectrum glints off every creased plane, with bright ignitable creases. FRACTURED RAINBOW finish."),
 "fr_rainbow_plasma": dict(name="Rainbow Plasma", engine="rbw_plasma", seed=717,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A dense turbulent plasma field cycling the full spectrum into many small drifting rainbow cells with bright ignitable threads. FRACTURED RAINBOW finish."),
 "fr_spectral_curl": dict(name="Spectral Curl-Flow", engine="rbw_spectral_curl", seed=718,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(freq=9.0),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A full-spectrum hue field smeared along a divergence-free curl flow into flowing rainbow streamlines with bright ignitable rims. FRACTURED RAINBOW finish."),
 "fr_spectral_marble": dict(name="Spectral Marble", engine="rbw_spectral_marble", seed=719,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Turbulent domain-warped marble veining mapped to a flowing full-spectrum hue field, with bright ignitable vein-edges. FRACTURED RAINBOW finish."),
}
OCCULT = {
 "fo_ectoplasm": dict(name="Ectoplasm", engine="occ_ectoplasm", eargs={}, seed=800,
    base=(5, 8, 7), glow=(110, 175, 130), edge=(195, 245, 210),
    kw=dict(gamma=0.9, edge_gain=0.85, ambient=0.4, ambient_sigma=58, ambient_floor=0.3),
    desc="Wraith smoke pulled across the dark in drifting vapour wisps — ectoplasm. A FRACTURED OCCULT finish."),
 "fo_blood_spatter": dict(name="Blood Spatter", engine="occ_blood_spatter", eargs=dict(drops=260), seed=801,
    base=(9, 2, 3), glow=(165, 20, 22), edge=(235, 90, 70),
    kw=dict(gamma=0.85, edge_gain=1.0, ambient=0.32, ambient_sigma=50, ambient_floor=0.26),
    desc="Splattered crimson droplets, cast-off specks and thin drip-runs — blood spatter. A FRACTURED OCCULT finish."),
 "fo_cobweb_lace": dict(name="Cobweb Lace", engine="occ_cobweb_lace", eargs=dict(webs=24), seed=802,
    base=(7, 7, 9), glow=(120, 125, 140), edge=(215, 220, 235),
    kw=dict(gamma=0.95, edge_gain=0.95, ambient=0.34, ambient_sigma=52, ambient_floor=0.28),
    desc="Tattered overlapping spider webs in a dusty veil of ash-grey silk — cobweb lace. A FRACTURED OCCULT finish."),
 "fo_sigil_grid": dict(name="Sigil Grid", engine="occ_sigil_grid", eargs=dict(n=16), seed=803,
    base=(8, 6, 9), glow=(150, 60, 175), edge=(225, 170, 245),
    kw=dict(gamma=0.95, edge_gain=1.0),
    desc="A carved grid of small occult glyphs glowing violet — a cursed sigil plate. A FRACTURED OCCULT finish."),
 "fo_bone_branch": dict(name="Bone Branch", engine="occ_bone_branch", eargs=dict(trunks=24), seed=804,
    base=(8, 8, 7), glow=(150, 145, 125), edge=(230, 225, 205),
    kw=dict(gamma=0.95, edge_gain=0.9),
    desc="A thicket of forked bone-white skeletal twigs with knobbed joints — bone branching. A FRACTURED OCCULT finish."),
 "fo_candle_wax": dict(name="Candle Wax", engine="occ_candle_wax", eargs=dict(columns=22), seed=805,
    base=(9, 6, 3), glow=(200, 130, 35), edge=(255, 195, 95),
    kw=dict(gamma=0.9, edge_gain=0.85, ambient=0.36, ambient_sigma=50, ambient_floor=0.28),
    desc="Molten tallow streaming down into pooled drips under amber flame-glow — candle wax. A FRACTURED OCCULT finish."),
 "fo_rune_lattice": dict(name="Rune Lattice", engine="occ_rune_lattice", eargs=dict(n=18), seed=806,
    base=(6, 8, 9), glow=(60, 150, 150), edge=(170, 235, 230),
    kw=dict(gamma=0.95, edge_gain=1.0),
    desc="A binding lattice of carved angular staves and branches edge to edge — cursed runes. A FRACTURED OCCULT finish."),
 "fo_shadow_mist": dict(name="Shadow Mist", engine="occ_shadow_mist", eargs={}, seed=807,
    base=(5, 5, 8), glow=(70, 60, 110), edge=(150, 140, 200),
    kw=dict(gamma=0.95, edge_gain=0.8, ambient=0.42, ambient_sigma=60, ambient_floor=0.32),
    desc="Creeping darkness in curl-warped tendrils with faint thinning rifts — shadow mist. A FRACTURED OCCULT finish."),
 "fo_seance_veil": dict(name="Seance Veil", engine="occ_seance_veil", eargs=dict(veils=6), seed=808,
    base=(7, 5, 10), glow=(125, 55, 165), edge=(205, 150, 240),
    kw=dict(gamma=0.95, edge_gain=0.9, ambient=0.36, ambient_sigma=54, ambient_floor=0.3),
    desc="Hanging translucent spirit-curtain folds in séance violet — a séance veil. A FRACTURED OCCULT finish."),
 "fo_pentagram_seal": dict(name="Pentagram Seal", engine="occ_pentagram_tiling", eargs=dict(n=7), seed=809,
    base=(8, 4, 5), glow=(175, 35, 45), edge=(240, 110, 90),
    kw=dict(gamma=0.95, edge_gain=1.0),
    desc="A tiled field of small inscribed pentagrams in their circles — conjuring seals. A FRACTURED OCCULT finish."),
 "fo_graveyard_moss": dict(name="Graveyard Moss", engine="occ_graveyard_moss", eargs=dict(cells=115), seed=810,
    base=(7, 9, 6), glow=(70, 130, 65), edge=(160, 215, 130),
    kw=dict(gamma=0.95, edge_gain=0.85, ambient=0.3, ambient_sigma=50, ambient_floor=0.26),
    desc="Weathered stone slabs crusted with sickly-green lichen and dark mortar — gravestone moss. A FRACTURED OCCULT finish."),
 "fo_spider_lattice": dict(name="Spider Lattice", engine="occ_spider_lattice", eargs=dict(cells=85), seed=811,
    base=(6, 6, 8), glow=(115, 120, 140), edge=(210, 215, 235),
    kw=dict(gamma=0.95, edge_gain=1.0, ambient=0.3, ambient_sigma=50, ambient_floor=0.26),
    desc="A taut Voronoi web of silk strands beaded bright at the junctions — a spider lattice. A FRACTURED OCCULT finish."),
 "fo_raven_feather": dict(name="Raven Feather", engine="occ_raven_feather", eargs=dict(feathers=64), seed=812,
    base=(5, 5, 8), glow=(70, 75, 110), edge=(175, 185, 215),
    kw=dict(gamma=0.95, edge_gain=0.9),
    desc="Overlapping dark plumes with fine angled barbs — glossy raven-feather plumage. A FRACTURED OCCULT finish."),
 "fo_witchfire": dict(name="Witchfire", engine="occ_witchfire", eargs=dict(n=380), seed=813,
    base=(4, 9, 6), glow=(60, 190, 90), edge=(150, 255, 160),
    kw=dict(gamma=0.85, edge_gain=0.9, ambient=0.4, ambient_sigma=54, ambient_floor=0.3),
    desc="Cold green-fire ember sparks with upward licks drifting in the dark — witchfire. A FRACTURED OCCULT finish."),
 "fo_cracked_tomb": dict(name="Cracked Tomb", engine="occ_cracked_tomb", eargs=dict(cells=72), seed=814,
    base=(7, 7, 8), glow=(120, 118, 122), edge=(205, 205, 210),
    kw=dict(gamma=0.95, edge_gain=0.95),
    desc="Aged granite slabs riven by deep fracture cracks with chiselled grain — a cracked tombstone. A FRACTURED OCCULT finish."),
 "fo_vampire_damask": dict(name="Vampire Damask", engine="occ_vampire_damask", eargs=dict(reps=6), seed=815,
    base=(9, 3, 5), glow=(150, 30, 50), edge=(220, 110, 95),
    kw=dict(gamma=0.95, edge_gain=0.95),
    desc="Ornate baroque scroll-leaf damask in oxblood velvet — vampire wallpaper. A FRACTURED OCCULT finish."),
 "fo_haunted_fog": dict(name="Haunted Fog", engine="occ_haunted_fog", eargs=dict(banks=5), seed=816,
    base=(6, 7, 8), glow=(95, 110, 120), edge=(190, 205, 215),
    kw=dict(gamma=0.95, edge_gain=0.85, ambient=0.42, ambient_sigma=58, ambient_floor=0.32),
    desc="Churning banks of rolling ground-mist with bright wispy crests — haunted graveyard fog. A FRACTURED OCCULT finish."),
 "fo_glyph_cells": dict(name="Glyph Cells", engine="occ_glyph_cells", eargs=dict(cells=120, palette=[(150, 30, 35), (90, 40, 130), (40, 90, 60)], edge=(225, 180, 90)), seed=818,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A dense ouija mosaic of spell-cells in blood, violet and green seamed by bright engraving — glyph cells. A FRACTURED OCCULT finish."),
 "fo_crimson_cells": dict(name="Crimson Cells", engine="occ_crimson_cells", eargs=dict(n=16, palette=[(150, 25, 30), (95, 20, 45), (60, 55, 55)], edge=(235, 120, 70)), seed=819,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Coagulated blood-cell panes in crimson, wine and ash with bright membranes — dripping crimson cells. A FRACTURED OCCULT finish."),
 "fo_stained_chapel": dict(name="Stained Chapel", engine="occ_stained_chapel", eargs=dict(cells=85, palette=[(95, 45, 140), (150, 30, 40), (175, 150, 95)], edge=(220, 175, 95)), seed=820,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A desecrated rose-window of violet, blood and bone-gold shards with igniting fault-lines — cursed chapel glass. A FRACTURED OCCULT finish."),
}

GROUPS = {
    "🌊 FRACTURED DEEP": DEEP,
    "👣 FRACTURED CRYPTID": CRYPTID,
    "🛸 FRACTURED UFO": UFO,
    "🌈 FRACTURED RAINBOW": RAINBOW,
    "🔮 FRACTURED OCCULT": OCCULT,
}

# id -> recipe across every theme (built from the literals above at import).
ALL = {}
for _grp in GROUPS.values():
    ALL.update(_grp)


def _seed_int(seed):
    try:
        return int(seed)
    except Exception:
        return abs(hash(str(seed))) % (2 ** 31)


def _field(d, work):
    return getattr(fm, d["engine"])(work, work, _seed_int(d["seed"]), **d.get("eargs", {}))


def _art_work(d):
    """Work-res art (0..1 HxWx3). Scalar fields get colorize()'d; multi-hue engines return RGB."""
    field = _field(d, _WORK)
    if getattr(field, "ndim", 0) == 3:
        return np.clip(field, 0.0, 1.0)
    return np.clip(fm.colorize(field, d["base"], d["glow"], d["edge"], **d["kw"]), 0.0, 1.0)


@lru_cache(maxsize=8)
def _art_work_cached(fid):
    return _art_work(ALL[fid])


def _mk(fid):
    # SPB-WILDS 2026-08-23 tick W-1. Owner: "Too much redundancy way too
    # similar looks. Must be VERY UNIQUE" and retain FRACTURED color flipping.
    # Cryptid now uses seven dense 8-32px mark families + independent eight-tier
    # M/R/CC phase populations. Measured worst structural NN 0.787 -> 0.414,
    # all-70 M7 minimum 85.0, native-2048 max 0.702s; _wilds_work/report.json.
    if fid.startswith("fc_"):
        return _wilds_entry(fid, ALL[fid], "cryptid")

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
        return fracture_spec(art, m2, ignition=1.0, decorrelation=0.18, as_uint8=True)

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Register every themed finish into the monolithic + UI group-map registries (mirrors FORGE)."""
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
    for fid in ALL:
        entry = _mk(fid)
        for reg in regs:
            reg[fid] = entry
        n += 1
    counts = ", ".join(f"{g.split(' ', 1)[-1]}:{len(d)}" for g, d in GROUPS.items())
    return f"fractured-themes: {n} themed finishes live ({counts})"
