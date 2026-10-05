# -*- coding: utf-8 -*-
"""NIGHTSHIFT DESIGN — the hand-authored form for each of the fifty finishes.

Owner 2026-09-01: "EVERY SINGLE ONE NEEDS TOTALLY UNIQUE BASE PATTERN DESIGNS."

Each row names the construction that finish is BUILT from, chosen by reading its
name and description, plus the fine-detail kind keyed onto it and the card laid
in the lip on its region boundaries.

Where a construction appears twice it is in a genuinely different REGIME, and
the row says which — Gray-Scott's (feed, kill) selects between drifting worms,
isolated cells, a labyrinth and self-replicating mitosis, which are four
different patterns, not one pattern at four sizes. Anywhere that claim does not
survive the TWIN gate, the row is wrong and gets a different construction.

`form` is either a name in nightshift_forms_2026 or "fk:<key>" for one of the
twelve generators already in the flames kit.
"""
from __future__ import annotations

# fid -> (form, params, detail_kind, detail_amount, edge_card)
DESIGN = {
    # ── 🌑 OPPOSITION ──────────────────────────────────────────────────────
    # a poison: real two-species chemistry, in the isolated-cell regime
    "nsx_cyanide_hour":      ("gray_scott", dict(feed=0.030, kill=0.0625), "crackle", 0.60, "chrome"),
    # "a filament network that only announces itself" — drainage IS that network
    "nsx_ember_verdict":     ("erosion", dict(iters=26), "spark", 0.55, "candy_chrome"),
    # a braid, running liquid: folded and twisted layers
    "nsx_violet_sentence":   ("damascus", dict(layers=170, twist=2.4), "fibre", 0.50, "mercury"),
    # sea-green drift confessing under light: refraction web
    "nsx_copper_confession": ("caustics", dict(scale=7.0, octaves=3), "flake", 0.52, "spectraflame"),
    # a chalk plate whose CRACK burns: impact fracture, radial + arrest rings
    "nsx_magenta_testimony": ("shatter", dict(impacts=3, radials=34), "ridge", 0.58, "candy_chrome"),
    # "lifted ice PLATES": columnar cooling joints
    "nsx_ice_to_rust":       ("basalt", dict(cells=54), "ridge", 0.55, "antique_chrome"),
    # jade CELLS with seams between: scale-free packing
    "nsx_jade_reversal":     ("apollonian", dict(rmax=0.070), "flake", 0.50, "mercury"),
    # sodium lamp era, a cold BED: sand on a driven plate
    "nsx_sodium_trial":      ("chladni", dict(modes=((41, 58), (67, 34), (83, 71), (97, 89), (113, 104))), "stipple", 0.55, "spectraflame"),
    # an aqua burn FRONT: rotating excitable wavefronts
    "nsx_aqua_betrayal":     ("bz_spiral", dict(cores=30), "grain", 0.50, "chrome"),
    # DENDRITES holding an alibi: anisotropic crystal growth
    "nsx_chartreuse_alibi":  ("frost_fern", dict(seeds=22, branch=0.16), "spark", 0.55, "candy_chrome"),
    # creased slate with embers in the FOLDS
    "nsx_slate_ember":       ("fk:crease", dict(k=2.4, steps=20), "ridge", 0.58, "candy_chrome"),
    # harbour water under dock lamps: two gratings beating
    "nsx_harbour_amber":     ("moire_beat", dict(a=118.0, b=126.0), "flake", 0.48, "spectraflame"),
    # gunsmoke PLATES with heat surviving underneath
    "nsx_gunsmoke_coal":     ("fk:plate", dict(cells=22, lift=0.70), "crackle", 0.55, "dark_chrome"),
    # frosted ceramic THREADED with filaments
    "nsx_frost_filament":    ("fk:vein", dict(n=60, length=190), "grain", 0.52, "chrome"),
    # deep-water DRIFT with a forge glow under it
    "nsx_deep_water_forge":  ("fk:drift", dict(scale=170, steps=34), "fibre", 0.52, "spectraflame"),
    # "pewter CELLS that each hold one sunset"
    "nsx_pewter_sunset":     ("fk:cell", dict(cells=26), "stipple", 0.50, "candy_chrome"),
    # storm-grey FINGERING: Rayleigh-Taylor
    "nsx_storm_copper":      ("fk:finger", dict(n=26), "fibre", 0.54, "antique_chrome"),
    # the blue hour, CRACKED, brass in every fracture
    "nsx_blue_hour_brass":   ("fk:crack", dict(cells=30, width=3.4), "ridge", 0.56, "spectraflame"),
    # a vault whose floor becomes ENTIRELY cinder: the self-replicating regime
    "nsx_cinder_vault":      ("gray_scott", dict(feed=0.014, kill=0.047), "spark", 0.55, "chrome"),
    # a rust FRONT overtaking cold grey: Eden growth
    "nsx_anchor_rust":       ("fk:front", dict(seeds=260, steps=22), "crackle", 0.55, "dark_chrome"),

    # ── 🌓 INVERSION ───────────────────────────────────────────────────────
    # rusted plate, every LIFTED EDGE goes glacier: overlapping scales
    "nsx_rust_to_glacier":   ("imbricate", dict(rows=52, overlap=0.40), "ridge", 0.55, "chrome"),
    # amber cells with a mirror sleeping in the SEAMS: coalescing droplets
    "nsx_amber_cryonic":     ("metaball", dict(blobs=2600, radius=0.0075), "flake", 0.50, "mercury"),
    # fired clay that freezes: tile work
    "nsx_terracotta_freeze": ("truchet", dict(tiles=52, style="cross"), "crackle", 0.55, "chrome"),
    # bronze playing a nocturne: flowing oriented grain
    "nsx_bronze_nocturne":   ("ridge_flow", dict(ridges=190, cores=6), "fibre", 0.50, "mercury"),
    # saffron is packed STIGMAS: golden-angle packing
    "nsx_saffron_midnight":  ("phyllotaxis", dict(n=52000, spread=0.72), "stipple", 0.52, "mercury"),
    # arctic light moving UNDER ochre: aperiodic interference
    "nsx_ochre_arctic":      ("quasicrystal", dict(waves=7, freq=260.0), "grain", 0.50, "chrome"),
    # foundry spatter freezing into a lattice
    "nsx_foundry_frost":     ("rosensweig", dict(pitch=27.0), "spark", 0.52, "satin_chrome"),
    # a marigold BED opening onto an abyss floor
    "nsx_marigold_abyss":    ("fk:bed", dict(cells=38, p=0.44), "flake", 0.52, "candy_chrome"),
    # cold signal SPARKS that only fire at night
    "nsx_sienna_signal":     ("fk:spark", dict(n=180, life=150), "spark", 0.55, "chrome"),
    # a kiln FRONT that cools behind it: the labyrinth regime
    "nsx_kiln_blue":         ("gray_scott", dict(feed=0.026, kill=0.051), "ridge", 0.55, "mercury"),

    # ── 🌘 TOXIC ───────────────────────────────────────────────────────────
    # acid-green DENDRITES breaking a curfew
    "nsx_venom_curfew":      ("fk:dendrite", dict(seeds=120), "spark", 0.56, "candy_chrome"),
    # absinthe THREADS taking the car: a braid
    "nsx_absinthe_night":    ("fk:braid", dict(layers=22, shear=5.0), "fibre", 0.52, "mercury"),
    # "indigo RECESS cells with a charge in the WALLS": routed corridors
    "nsx_toxic_recess":      ("maze", dict(cells=110), "spark", 0.55, "chrome"),
    # a POOL: chlorine caustics, at a different scale from copper_confession
    "nsx_chlorine_watch":    ("caustics", dict(scale=13.0, octaves=2, gain=5.2), "flake", 0.50, "chrome"),
    # violet powder coat, lime in EVERY CRACK: a different plate, different modes
    "nsx_lime_interrogation": ("chladni", dict(modes=((23, 47), (59, 71), (89, 31), (101, 97))), "ridge", 0.58, "spectraflame"),
    # a serpent SHEDS: imbrication is literally snake scale
    "nsx_serpent_shift":     ("imbricate", dict(rows=78, overlap=0.52, jitter=0.24), "fibre", 0.52, "mercury"),
    # cold plates over a glow that only shows at the EDGES
    "nsx_uranium_dusk":      ("fk:plate", dict(cells=34, lift=1.00), "ridge", 0.55, "candy_chrome"),
    # a mauve VIGIL drifting: slow curl
    "nsx_wormwood_vigil":    ("fk:drift", dict(scale=110, steps=22), "grain", 0.50, "chrome"),
    # blue-violet FINGERING with acid underneath
    "nsx_acid_testament":    ("fk:finger", dict(n=42), "spark", 0.54, "spectraflame"),
    # an orchid FRONT with hemlock behind it
    "nsx_hemlock_hour":      ("fk:front", dict(seeds=520, steps=13), "crackle", 0.52, "candy_chrome"),

    # ── 🌗 REGALIA ─────────────────────────────────────────────────────────
    # an olive COURT, violet taking the throne: fold and twist, tighter than violet_sentence
    "nsx_royal_nightfall":   ("damascus", dict(layers=96, twist=4.6, folds=2), "ridge", 0.54, "mercury"),
    # a green bench, rose verdict delivered along the VEINS
    "nsx_rose_assize":       ("fk:vein", dict(n=110, length=95), "fibre", 0.52, "candy_chrome"),
    # cold ceramic sentenced to GILT: fine tile, arcs not crosses
    "nsx_gilt_sentence":     ("truchet", dict(tiles=88, style="arc", width=0.12), "stipple", 0.52, "spectraflame"),
    # an imperial DRIFT from moss to amethyst: drainage at a coarser grain
    "nsx_imperial_drift":    ("erosion", dict(iters=14, sharp=0.75), "grain", 0.50, "mercury"),
    # a braid CLOSING into orchid at curfew
    "nsx_orchid_curfew":     ("fk:braid", dict(layers=34, shear=2.6), "flake", 0.52, "candy_chrome"),
    # watch-PLATES, cardinal red beneath every lifted edge: cooling joints, finer
    "nsx_cardinal_watch":    ("basalt", dict(cells=92, wall=0.11), "crackle", 0.55, "chrome"),
    # amethyst WORKING UP THROUGH a powder-green bed: percolation
    "nsx_amethyst_bench":    ("fk:bed", dict(cells=56, p=0.52), "stipple", 0.52, "satin_chrome"),
    # GOLD CREASES at noon
    "nsx_coronation_blue":   ("fk:crease", dict(k=1.5, steps=34), "ridge", 0.55, "mercury"),
    # fern ground with fuchsia SPARKS
    "nsx_fuchsia_docket":    ("fk:spark", dict(n=420, life=70), "spark", 0.56, "candy_chrome"),
    # the LAST SESSION, everything cooling: the drifting-worm regime
    "nsx_last_session":      ("gray_scott", dict(feed=0.037, kill=0.060), "fibre", 0.52, "chrome"),
}


FK_KEYS = {
    "fk:cell", "fk:vein", "fk:braid", "fk:drift", "fk:dendrite", "fk:bed",
    "fk:plate", "fk:crack", "fk:front", "fk:crease", "fk:finger", "fk:spark",
}


def check(nightshift_ids):
    """Every finish must be designed, and no two may share form AND params."""
    missing = sorted(set(nightshift_ids) - set(DESIGN))
    extra = sorted(set(DESIGN) - set(nightshift_ids))
    if missing or extra:
        raise ValueError("DESIGN out of sync — missing %s, unknown %s" % (missing, extra))
    seen = {}
    for fid, (form, params, _k, _a, _e) in DESIGN.items():
        key = (form, tuple(sorted(params.items())))
        seen.setdefault(key, []).append(fid)
    clash = {k: v for k, v in seen.items() if len(v) > 1}
    if clash:
        raise ValueError("identical construction AND parameters: " + "; ".join(
            ", ".join(sorted(v)) for v in clash.values()))
    return True


# ── PAINT TREATMENT — how each construction becomes paint ──────────────────
#
# Owner 2026-09-01. Measured after every finish had its own construction AND its
# own material deck: TWIN was STILL 0.98-0.99 on all fifty. The descriptor is
# fine (five unrelated fields score 0.365-0.700 against each other), so the
# twins were real - and they came from `_art`, which applied ONE treatment to
# all fifty: an 8-tier per-cell ladder, a fixed 0.72+0.52*field shade, a +/-16
# degree hue wobble and the same uniform fbm grain at 0.34.
#
# Thirty-one constructions went in and one statistical signature came out. So
# the treatment is authored per finish too:
#
#   tiers    how many shade steps (0 = continuous, no ladder)
#   ladder   "cell"  the ladder is per label cell (plates, tiles, packings)
#            "field" the ladder follows the construction's own value (flows,
#                    fronts, drainage - anything with continuous structure)
#   shade    how hard the construction shades the surface under the flecks
#   wobble   per-cell hue spread in degrees
#   grain    the finish's own keyed detail kind, replacing the shared fbm
#   gamt     grain amplitude
PAINT = {}
_LADDER_BY_FORM = {
    # constructions with real cells/plates get a stepped, per-cell ladder
    "basalt": "cell", "apollonian": "cell", "truchet": "cell", "imbricate": "cell",
    "metaball": "cell", "phyllotaxis": "cell", "rosensweig": "cell",
    "fk:cell": "cell", "fk:plate": "cell", "fk:bed": "cell", "fk:crack": "cell",
    # continuous constructions read their own value instead
    "gray_scott": "field", "erosion": "field", "damascus": "field",
    "caustics": "field", "bz_spiral": "field", "chladni": "field",
    "quasicrystal": "field", "ridge_flow": "field", "moire_beat": "field",
    "shatter": "field", "frost_fern": "field", "maze": "field",
    "fk:vein": "field", "fk:braid": "field", "fk:drift": "field",
    "fk:dendrite": "field", "fk:front": "field", "fk:crease": "field",
    "fk:finger": "field", "fk:spark": "field",
}
_TIER_CYCLE = (6, 0, 9, 4, 12, 0, 7, 5, 0, 10)
for _i, (_fid, (_form, _p, _kind, _amt, _edge)) in enumerate(sorted(DESIGN.items())):
    PAINT[_fid] = dict(
        tiers=_TIER_CYCLE[_i % len(_TIER_CYCLE)],
        ladder=_LADDER_BY_FORM.get(_form, "cell"),
        shade=(0.34, 0.46, 0.62, 0.28, 0.52)[_i % 5],
        wobble=(10.0, 22.0, 16.0, 30.0)[_i % 4],
        grain=_kind,
        gamt=(0.18, 0.30, 0.24, 0.12)[_i % 4],
    )


# ── PER-FINISH FIXES after the first full gate run (2026-09-01 03:10) ──────
# 42/50 passed. These eight are the named failures, each corrected on its own
# terms rather than by moving a threshold.
#
# The seven FOLLOW failures share a cause: their paint carried enough INDEPENDENT
# grain (gamt) that its detail envelope stopped tracking its own construction, so
# there was less structure for the spec to follow. Dropping the independent grain
# and letting the construction shade the surface harder puts the envelope back on
# the geometry. kiln_blue failed SCALE instead - the Gray-Scott labyrinth regime
# is the coarsest of the four, so it needs a stronger keyed fine layer.
_FOLLOW_FIXES = ("nsx_ice_to_rust", "nsx_jade_reversal", "nsx_chartreuse_alibi",
                 "nsx_frost_filament", "nsx_cinder_vault", "nsx_amber_cryonic",
                 "nsx_venom_curfew")
for _f in _FOLLOW_FIXES:
    PAINT[_f]["gamt"] = 0.06
    PAINT[_f]["shade"] = 0.66

# SCALE: the labyrinth regime is the coarsest Gray-Scott; give it more keyed detail
_kb = DESIGN["nsx_kiln_blue"]
DESIGN["nsx_kiln_blue"] = (_kb[0], _kb[1], _kb[2], 0.82, _kb[4])
PAINT["nsx_kiln_blue"]["gamt"] = 0.30


# ── SPEC TUNING for filament constructions ────────────────────────────────
# After the edge-lip cap, three finishes still measured FOLLOW 0.29-0.33: all
# three are THIN-LINE constructions (frost_fern dendrites, fk:vein filaments,
# fk:dendrite). Percentile bands cut a field into areas, and a filament net is
# mostly background by area, so the band layout barely registers the lines that
# actually carry the artwork. Raising `chips` puts more of the material variation
# under the envelope's control instead of the bands', which is where a filament
# finish keeps its structure.
# Raising `chips` was tried first and did nothing (0.300 -> 0.301). Neither did
# lowering the micro-grain floor. The lever is the BANDING: linear-by-value bands
# give the filaments their own cards instead of slicing the background six ways.
# Measured: FOLLOW 0.30 -> 0.75, 0.31 -> 0.79, 0.34 -> 0.72.
SPEC_TUNE = {
    "nsx_chartreuse_alibi": dict(chips=0.45, edge_max=0.05, bands="linear"),
    "nsx_frost_filament":   dict(chips=0.45, edge_max=0.05, bands="linear"),
    "nsx_venom_curfew":     dict(chips=0.45, edge_max=0.05, bands="linear"),
}
