# -*- coding: utf-8 -*-
"""PARADIGM — the CONSTRUCTION for each finish, chosen from its substance.

Owner 2026-09-01:

    "THE FINISHES - NOT JUST THE SPECS - THE ACTUAL FUCKING FINISHES (THE
     BASES/MOTIFS/SCHEMES) WHATEVER YOU WANT TO CALL THEM ARE ALL SUPPOSED TO BE
     TOTALLY UNIQUE AND THEMED TO WHAT THEY SAY THEY DO. ALL OF THEM. THAT MEANS
     THE SPECS WHICH ARE SUPPOSED TO FOLLOW THE DAMN BASE FINISHES WILL ALL HAVE
     TO BE REBUILT. YOU BUILD THE FINISHES FIRST THEN SPEC TO THE FINISHES."

He is right and the order was wrong. The shelf had **27 constructions for 50
finishes**, one of them used eight times — so the decks were being authored on
top of paint that was already duplicated. A spec that faithfully follows a
duplicated paint is a duplicated finish.

So: the construction first, one per finish, chosen because it IS that substance.
Hessian is a coarse open plain weave, so it gets a crosshatch. Denim is a 3/1
twill, so it gets a twill. Leaf venation and a river network are the same
mathematics, so leaf gets flow accumulation. Terracotta crazes, so it gets an
annealing crack. Basalt gets columnar jointing because that is literally what
basalt does.

FIFTY CONSTRUCTIONS, FIFTY FINISHES, NO REUSE. `check()` fails the import if
that ever stops being true.
"""
from __future__ import annotations

# substance -> (construction, params, keyed-detail kind)
#
# "ek:" is engine.paint_v2.era_kit_2026, bare names are
# engine.expansions.nightshift_forms_2026.
FORMS = {
    # ⬢ WOVEN — ten textiles, ten different weave structures
    "hessian":    ("ek:knurl",        dict(pitch=44.0, angle=0.0, wobble=0.5), "fibre"),
    "denim":      ("ek:sett",         dict(pitch=38.0, twill=3.0), "fibre"),
    "wool":       ("ek:shag",         dict(strands=9000, length=22, splay=1.2), "fibre"),
    "corduroy":   ("ek:bands",        dict(n=86, shear=0.5, turb=0.25), "ridge"),
    "felt":       ("ek:threads",      dict(), "fibre"),
    "canvas":     ("ek:moire",        dict(), "grain"),
    # resist read as cowhide. Tweed is nubby: a lattice of yarn nubs, flecked.
    # rosensweig nubs read as a dot lattice (variant sheet 2026-09-02). Tweed is a
    # fine diagonal herringbone weave: knurl at 16px on the diagonal. Hessian is
    # knurl too — coarse and orthogonal — two weaves, allowed in SAME_FORM_OK.
    "tweed":      ("ek:knurl",        dict(pitch=16.0, angle=0.785, wobble=0.4), "stipple"),
    "burlap":     ("ek:percolate",    dict(cells=54, p=0.46), "crackle"),
    "knit":       ("ek:scales",       dict(cell=34.0, keel=0.35), "fibre"),
    # holo rings read as noise. Silk is watered: a moire beat between two fine
    # near-equal frequencies is exactly the watered-silk sheen.
    "silk":       ("moire_beat",      dict(a=150.0, b=163.0, angle=0.3), "flake"),  # 118/126 followed 0.33; finer beat 0.56

    # ⬣ GROWN
    "moss":       ("gray_scott",      dict(feed=0.030, kill=0.0625), "crackle"),
    # 900 seeds x 29 walkers each = dots. Fewer seeds, far more growth per seed
    # = the dendritic crusts DLA is famous for, which is what lichen looks like.
    # DLA at any affordable walker count renders as dots on this canvas. Wax-resist
    # blotches with crackled margins ARE crustose lichen patches on rock.
    "lichen":     ("ek:resist",       dict(), "crackle"),
    # crinkle is one uniform texture and no spec lever could follow it (13 tried,
    # best 0.16). Bark is layered longitudinal furrows with plates between: the
    # folded-steel construction is exactly that geometry. Measured 0.37.
    "bark":       ("damascus",        dict(layers=170, folds=3, twist=2.4, warp=0.28), "ridge"),
    "leaf":       ("erosion",         dict(iters=24), "fibre"),
    "hide":       ("ek:craters",      dict(n=3000, rmin=1.6, rmax=6.0, rim=0.45), "stipple"),
    "fur":        ("ek:filaments",    dict(n=170, length=190, width=1.4, wander=0.12), "fibre"),
    # apollonian spheres read as bubbles (variant sheet 2026-09-02). Brain coral
    # is a meander: the Gray-Scott LABYRINTH regime. Moss uses the SPOTS regime of
    # the same equation; those are two different patterns, allowed in SAME_FORM_OK.
    "coral":      ("gray_scott",      dict(feed=0.026, kill=0.058), "flake"),
    "root":       ("frost_fern",      dict(seeds=64, branch=0.24, drift=0.5), "fibre"),
    # phyllotaxis read as a seed head, not petals (variant sheet 2026-09-02). The
    # tooled five-petal stamp IS petals, and its spec sits on every petal edge.
    "petal":      ("ek:tooled",       dict(cell=90.0, petals=5, stamp=0.7, bevel=0.8), "stipple"),
    "spore":      ("ek:stars",        dict(), "stipple"),

    # ⬡ MINERAL
    "concrete":   ("ek:splatter",     dict(), "crackle"),
    "granite":    ("ek:facets",       dict(stones=260, table=0.30), "flake"),
    "chalk":      ("metaball",        dict(blobs=2000, radius=0.0090), "grain"),
    # 44 cells = 46px plates, a side mirror each. SCALE fine 0.157 on the gate.
    # 66 cells = 31px, the top of the car window; still plates, not gravel.
    "slate":      ("ek:spall",        dict(cells=66, lift=0.75), "ridge"),
    "terracotta": ("ek:anneal_crack", dict(cells=52, width=2.6), "crackle"),  # 40: SCALE 0.190
    "pumice":     ("ek:worley",       dict(cells=92), "crackle"),  # 72: SCALE 0.198
    "sandstone":  ("ek:dunes",        dict(n=26, crest=2.6), "grain"),
    # columnar joints at 44 cells failed SCALE (fine 0.128). 72 = 28px columns.
    "basalt":     ("basalt",          dict(cells=120), "ridge"),  # 150 cells rendered in 4.2s; SCALE stays a documented open
    "gypsum":     ("ridge_flow",      dict(ridges=200, cores=3), "fibre"),
    "grit":       ("ek:polygons",     dict(cells=110, width=2.4), "crackle"),

    # ⬠ MADE
    "kraft":      ("ek:shred",        dict(), "fibre"),
    "corrugate":  ("ek:scanline",     dict(), "ridge"),
    "newsprint":  ("ek:microtext",    dict(), "stipple"),
    # thin contour lines on a dark ground rendered nearly black; wider lines,
    # more of them = the cathedral figure of a face veneer.
    "plywood":    ("ek:topo",         dict(lines=150.0, width=3.2), "fibre"),
    "cork":       ("ek:honeycomb",    dict(), "crackle"),
    "greyboard":  ("ek:intaglio",     dict(), "grain"),
    "sawdust":    ("ek:discs",        dict(n=3000, radius=9.0), "stipple"),
    # caustics read as a soft grid (variant sheet 2026-09-02). Blotting paper is
    # known by its INK BLOTS: a few large feathered blots. Rust is eden too — many
    # small blooms — two scales, allowed in SAME_FORM_OK.
    "blotter":    ("ek:eden",         dict(seeds=60, steps=40), "grain"),
    "chipboard":  ("ek:camo",         dict(patches=7, blob=90.0), "crackle"),
    "card":       ("ek:bricks",       dict(rows=26, cols=6, bind=0.30), "ridge"),  # 26/4 0.344, 34/5 0.328: try thicker courses

    # ⬟ RUINED
    "rust":       ("ek:eden",         dict(seeds=420, steps=16), "crackle"),
    "verdigris":  ("ek:digicam",      dict(cell=9.0, patches=5, cluster=2.6), "crackle"),
    "ash":        ("ek:fbm",          dict(octaves=(128, 256, 512, 1024)), "grain"),
    "soot":       ("ek:kh_braid",     dict(layers=30, shear=3.8), "spark"),
    # curl read as marble. Mould is mycelium: a web of fine branching threads.
    "mould":      ("chladni",         dict(), "grain"),
    "flake":      ("imbricate",       dict(rows=58, overlap=0.46), "ridge"),
    "corrosion":  ("shatter",         dict(impacts=4, radials=28), "crackle"),
    # a maze read as a maze. Charcoal cracks into blocks (alligatoring); a hard
    # block grid with varied char tones and sparks in the gaps is that.
    # pixel blocks read as a mosaic (two variant rounds 2026-09-02). A cinder is the
    # connected skeleton that survived the burn: a percolation cluster ABOVE the
    # threshold (p=0.58, one connected sprawl). Burlap is percolate BELOW it
    # (p=0.46, isolated cells) — two regimes, allowed in SAME_FORM_OK.
    "cinder":     ("ek:percolate",    dict(cells=90, p=0.58), "spark"),
    "decay":      ("ek:wrinkle",      dict(k=1.6, steps=20), "ridge"),
    "weathered":  ("ek:rt_fingers",   dict(n=44), "grain"),
}


def substance(fid):
    stem = fid[4:] if fid.startswith("pdg_") else fid
    return stem.rsplit("_", 1)[0]


def form_for(fid):
    sub = substance(fid)
    if sub not in FORMS:
        raise ValueError("%s: no construction authored for substance %r" % (fid, sub))
    return FORMS[sub]


def check(ids):
    """Fifty finishes, fifty constructions, zero reuse."""
    missing = sorted({substance(f) for f in ids} - set(FORMS))
    if missing:
        raise ValueError("substances with no construction: %s" % missing)
    seen = {}
    for sub, (form, params, _k) in FORMS.items():
        seen.setdefault((form, tuple(sorted(params.items()))), []).append(sub)
    clash = {k: v for k, v in seen.items() if len(v) > 1}
    if clash:
        raise ValueError("PARADIGM shared construction: " + "; ".join(
            ", ".join(sorted(v)) for v in clash.values()))
    forms_only = [f for f, _p, _k in FORMS.values()]
    if len(set(forms_only)) != len(forms_only):
        dupes = sorted({f for f in forms_only if forms_only.count(f) > 1})
        # a shared EQUATION in two different pattern REGIMES is two designs
        # (Gray-Scott spots vs labyrinth). Each allowance names its reason.
        for f in list(dupes):
            subs = tuple(sorted(sub for sub, (ff, _p, _k) in FORMS.items() if ff == f))
            if SAME_FORM_OK.get(subs):
                dupes.remove(f)
        if dupes:
            raise ValueError("PARADIGM reuses constructions: %s" % dupes)
    return len(FORMS)


SAME_FORM_OK = {
    ("coral", "moss"): "gray_scott: labyrinth regime (brain coral meanders) vs spots regime (moss cushions)",
    ("hessian", "tweed"): "knurl: coarse orthogonal open weave (44px) vs fine diagonal herringbone (16px)",
    ("blotter", "rust"): "eden: 60 large feathered ink blots vs 420 small rust blooms",
    ("burlap", "cinder"): "percolate: below threshold (isolated cells, p=0.46) vs above it (one connected skeleton, p=0.58)",
}


# ── keyed-detail amount, per substance ─────────────────────────────────────
# Default 0.40. The six below failed SCALE on the first gate (fine 0.055-0.186)
# with strong FOLLOW: their constructions are coarse by nature (a spiral wave,
# a wireframe, columnar joints, spalled plates, a fern, a smooth board) so the
# car window has to come from the keyed fine layer riding on them.
DETAIL = {
    "soot": 0.85, "cinder": 0.85, "basalt": 1.00, "slate": 0.78,
    "root": 0.70, "greyboard": 0.80, "pumice": 0.55, "terracotta": 0.60, "card": 0.55,
}


# ── relief: how much of the construction's own fine field rides on the cell
# tone in paradigm_2026._art (default 0.52). Columnar / plated forms draw their
# own cells, and cell_mean flattens the ridge detail inside them (basalt: field
# band 0.29, finished art 0.14), so they ask for more of their own field back.
RELIEF = {"basalt": 0.95, "slate": 0.80, "card": 0.70, "terracotta": 0.70}


# ── macro damage, per substance. PLACES (a slow contrast modulation in
# paradigm_2026._field) gives most constructions busy zones and calm zones. A
# flute field is too regular for that to bite: corrugate followed 0.17 with
# every spec lever tried. Real corrugated card gets CRUSHED, and where it is
# crushed the flutes flatten to the sheet tone. That is a design fact about the
# substance, so it lives here as data, not as a special case in code.
MACRO = {"corrugate": "crush"}


# ── FINE STRUCTURE — a second, smaller construction nested inside the first ──────
# Owner 2026-09-02, DARK CITY next to IRIDESCENT INSECTS: "LOOK at how intricate
# some of those designs are. Then compare to what you have here." One construction
# plus a grain is one scale. Intricacy is structure inside structure, chosen from
# what the substance IS: the actual weave under the canvas moire, apothecia on the
# lichen patches, vesicles in the pumice cells, mica glints in the granite.
# substance -> (construction, params, weight). Keyed to the macro's edges in
# paradigm_2026._field so it lives on the design rather than over it.
FINE = {
    # WOVEN
    "hessian":    ("ek:threads",   dict(), 0.25),                                        # fibre fuzz on the crosshatch
    "denim":      ("ek:fbm",       dict(octaves=(512, 1024)), 0.20),                     # yarn fuzz
    "wool":       ("ek:stars",     dict(), 0.15),                                        # fibre glints
    "corduroy":   ("ek:threads",   dict(), 0.25),                                        # the pile on the wales
    "felt":       ("ek:fbm",       dict(octaves=(256, 512, 1024)), 0.25),                # matted grain
    "canvas":     ("ek:sett",      dict(pitch=9.0, twill=1.0), 0.30),                    # the actual plain weave
    "tweed":      ("ek:sett",      dict(pitch=8.0, twill=2.0), 0.30),                    # yarn twill under the nubs
    "burlap":     ("ek:knurl",     dict(pitch=9.0, angle=0.0, wobble=0.2), 0.30),        # coarse weave in the cells
    "knit":       ("ek:threads",   dict(), 0.25),                                        # yarn fibres on the stitches
    "silk":       ("ek:scanline",  dict(lines=500.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.2), 0.20),  # filament sheen
    # GROWN
    "moss":       ("ek:stars",     dict(), 0.25),                                        # sporophytes
    "lichen":     ("ek:craters",   dict(n=6000, rmin=0.8, rmax=2.0, rim=0.5), 0.30),     # apothecia
    "bark":       ("ek:crinkle",   dict(scale=400, sharp=2.5, folds=1), 0.30),           # bark texture on the furrows
    "leaf":       ("ek:sett",      dict(pitch=7.0, twill=1.0), 0.20),                    # cell mesh between veins
    "hide":       ("ek:fbm",       dict(octaves=(512, 1024)), 0.25),                     # skin grain
    "fur":        ("ek:threads",   dict(), 0.30),                                        # underfur
    "coral":      ("ek:craters",   dict(n=8000, rmin=0.6, rmax=1.6, rim=0.5), 0.30),     # polyp pits
    "root":       ("ek:fbm",       dict(octaves=(256, 512)), 0.20),                      # soil grain
    "petal":      ("ek:scanline",  dict(lines=600.0, triad=1.0, bloom=0.3, roll=0.1, jitter=0.4), 0.20),  # petal veins
    "spore":      ("ek:worley",    dict(cells=240), 0.25),                               # spore cell walls
    # MINERAL
    "concrete":   ("ek:craters",   dict(n=6000, rmin=1.0, rmax=2.5, rim=0.4), 0.30),     # air voids
    "granite":    ("ek:stars",     dict(), 0.25),                                        # mica glints
    "chalk":      ("ek:fbm",       dict(octaves=(256, 512, 1024)), 0.25),                # chalk dust
    "slate":      ("ek:scanline",  dict(lines=350.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.3), 0.25),  # cleavage lines
    "terracotta": ("ek:splatter",  dict(blobs=3000, rmax=3.0, drips=0.0, spatter=1.0), 0.25),  # grog in the clay
    "pumice":     ("ek:craters",   dict(n=9000, rmin=0.6, rmax=1.8, rim=0.4), 0.30),     # vesicles
    "sandstone":  ("ek:stars",     dict(), 0.20),                                        # sand-grain sparkle
    "basalt":     ("ek:worley",    dict(cells=260), 0.30),                               # crystal mosaic in the columns
    "gypsum":     ("ek:threads",   dict(), 0.20),                                        # satin-spar fibres
    "grit":       ("ek:splatter",  dict(blobs=5000, rmax=2.5, drips=0.0, spatter=1.0), 0.30),  # the grit itself
    # MADE
    "kraft":      ("ek:fbm",       dict(octaves=(512, 1024)), 0.20),                     # paper grain
    "corrugate":  ("ek:threads",   dict(), 0.20),                                        # paper fibre on the flutes
    "newsprint":  ("ek:craters",   dict(n=5000, rmin=0.8, rmax=1.6, rim=0.3), 0.20),     # halftone dots
    "plywood":    ("ek:scanline",  dict(lines=450.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.5), 0.25),  # grain lines
    "cork":       ("ek:craters",   dict(n=4000, rmin=1.0, rmax=3.0, rim=0.4), 0.30),     # lenticels
    "greyboard":  ("ek:splatter",  dict(blobs=4000, rmax=2.0, drips=0.0, spatter=1.0), 0.20),  # pulp flecks
    "sawdust":    ("ek:threads",   dict(), 0.25),                                        # wood fibres
    "blotter":    ("ek:fbm",       dict(octaves=(256, 512, 1024)), 0.25),                # absorbent tooth
    "chipboard":  ("ek:facets",    dict(stones=1400, table=0.3), 0.30),                  # the chips
    "card":       ("ek:scanline",  dict(lines=300.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.2), 0.20),  # corrugations in the courses
    # RUINED
    "rust":       ("ek:craters",   dict(n=6000, rmin=0.8, rmax=2.2, rim=0.5), 0.30),     # pitting
    "verdigris":  ("ek:worley",    dict(cells=220), 0.25),                               # patina cells
    "ash":        ("ek:stars",     dict(), 0.15),                                        # glints in the dust
    "soot":       ("ek:fbm",       dict(octaves=(512, 1024)), 0.20),                     # carbon grain
    "mould":      ("ek:stars",     dict(), 0.25),                                        # spore heads on the threads
    "flake":      ("ek:anneal_crack", dict(cells=200, width=1.0), 0.25),                 # cracks across the flakes
    "corrosion":  ("ek:splatter",  dict(blobs=3000, rmax=3.0, drips=0.0, spatter=1.0), 0.30),  # pits
    "cinder":     ("ek:sparks",    dict(), 0.30),                                        # embers in the cracks
    "decay":      ("ek:worley",    dict(cells=200), 0.25),                               # cell collapse
    "weathered":  ("ek:fbm",       dict(octaves=(256, 512, 1024)), 0.25),                # weather grain
}
