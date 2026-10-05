# -*- coding: utf-8 -*-
"""FRACTURED FLAMES — the CONSTRUCTION for each finish, chosen from its physics.

Owner 2026-09-01: "FRACTURED FLAMES ... STILL FUBAR'D ... TONS of repeating specs
and paints just recolored bullshit." and "YOU BUILD THE FINISHES FIRST THEN SPEC TO
THE FINISHES."

The shelf had 63 stack recipes for 75 finishes, every one a two- or three-way
combination of the same twelve flames-kit primitives (eden, sparks, dla,
filaments, worley, percolate, kh_braid, wrinkle, curl, rt_fingers, anneal_crack,
spall) — so darrieus_cell and lava_cell were both worley+something, and eight
finishes were dla+something. The hand-authored decks in flames_decks_2026 were
laid on that.

Every finish here names a real combustion / plasma / molten / cinder phenomenon,
and most of them ARE a known pattern-forming process: a Darrieus-Landau front is
cellular (worley), Michelson-Sivashinsky cusping is a wrinkle, Rayleigh-Taylor is
fingers, a Lichtenberg scar is a fractal tree, a weld pool's frozen ripple record
is crescents (imbricate), quench craze is an annealing crack, coke is carbon cell
walls (honeycomb), columnar basalt is basalt.

RULES (check()): every finish has a construction; NO construction is used twice
within a chapter (the fifteen the picker shows together); NO (construction,
params) pair is used twice anywhere; cross-chapter reuse is reported as a count.
FINE gives each finish a second, smaller construction nested in the first.
"""
from __future__ import annotations

# stem -> (construction, params, keyed-detail kind)
FORMS = {
    # ── IGNITION ────────────────────────────────────────────────────────────
    "flashpoint":        ("ek:eden",        dict(seeds=60, steps=40), "spark"),                 # ragged burn front
    "char_creep":        ("ek:filaments",   dict(n=220, length=260, width=2.0, wander=0.15), "grain"),  # blackening along the grain
    "tinder_bloom":      ("ek:threads",     dict(), "spark"),                                   # dry fibre catching all at once
    "match_head":        ("metaball",       dict(blobs=1200, radius=0.012), "spark"),           # strontium flare blobs
    "smoulder_bed":      ("ek:percolate",   dict(cells=70, p=0.50), "grain"),                   # heat travelling through a packed bed
    "fuse_line":         ("ridge_flow",     dict(ridges=40, cores=1), "spark"),               # squiggles were sparse and faint; a few long burning trails (Flame candle: 90/2)  # powder trail
    "kindle_lattice":    ("ek:bricks",      dict(rows=20, cols=6, bind=0.10), "crackle"),       # stacked kindling from above
    "spark_shower":      ("ek:sparks",      dict(), "spark"),                                   # thermite spray
    "ember_catch":       ("ek:craters",     dict(n=400, rmin=8.0, rmax=20.0, rim=0.9), "spark"),  # landed embers with bright cores
    "pilot_ring":        ("ek:holo",        dict(rings=30.0, orders=1.0, warp=40.0, sharp=1.6), "grain"),  # the blue crown
    "autoignition":      ("ek:worley",      dict(cells=200), "crackle"),                     # broad fbm was plain; every cell reaching temperature at once (Flame darrieus 60, Molten lava 40)     # whole surface at temperature
    "firebrand_scatter": ("ek:splatter",    dict(blobs=400, rmax=18.0, drips=0.6, spatter=1.0), "spark"),  # brands downwind
    "scorch_front":      ("ek:camo",        dict(patches=5, blob=200.0, roughness=1.6), "crackle"),  # burned / unburned
    "ignition_delay":    ("ek:curl",        dict(scale=160, steps=34), "grain"),                # pale sulfur drift
    "touchpaper":        ("ek:shred",       dict(), "spark"),                                   # creeping along paper fibre

    # ── FLAME ───────────────────────────────────────────────────────────────
    "diffusion_sheet":   ("ek:crinkle",     dict(scale=120, sharp=2.0, folds=2), "grain"),      # the burn is a surface
    "wrinkled_front":    ("ek:wrinkle",     dict(k=1.8, steps=22), "ridge"),                    # Michelson-Sivashinsky cusps
    "darrieus_cell":     ("ek:worley",      dict(cells=60), "crackle"),                         # cellular instability
    "turbulent_braid":   ("ek:kh_braid",    dict(layers=26, shear=3.6), "grain"),               # braid after braid
    "flamelet_storm":    ("ek:filaments",   dict(n=600, length=40, width=2.0, wander=0.4), "spark"),  # thousands of flamelets (Ignition: 220 long)
    "buoyant_fingers":   ("ek:rt_fingers",  dict(n=40), "grain"),                               # Rayleigh-Taylor
    "shear_tongue":      ("damascus",       dict(layers=60, folds=2, twist=3.0, warp=0.3), "grain"),  # tongues leaning off a shear layer
    "pool_puff":         ("moire_beat",     dict(a=70.0, b=76.0, angle=1.57), "grain"),      # puffs rise: the beat runs across, not up          # periodic puff = a beat
    "candle_cone":       ("ridge_flow",     dict(ridges=90, cores=2), "grain"),                 # laminar streamlines
    "blowtorch":         ("ek:scanline",    dict(lines=200.0, triad=1.0, bloom=1.4, roll=0.0, jitter=0.0), "spark"),  # jitter made a dot grid; a torch is streaks  # stretched thin and fast
    "backdraft_wrinkle": ("caustics",       dict(scale=8.0, octaves=3), "grain"),               # the front folding back
    "fire_whirl_grain":  ("ek:curl",        dict(scale=90, steps=40), "fibre"),                 # one handedness (Ignition delay: 160/34)
    "laminar_ladder":    ("ek:bands",       dict(n=60, shear=0.0, turb=0.05), "grain"),         # rungs at fixed spacing
    "crown_fire":        ("frost_fern",     dict(seeds=30, branch=0.4, drift=0.3), "spark"),    # branching canopy burning
    "stoichiometric_seam": ("ek:topo",      dict(lines=60.0, width=3.0), "grain"),              # the exact ratio line

    # ── PLASMA ──────────────────────────────────────────────────────────────
    "arc_filament":      ("ek:filaments",   dict(n=40, length=500, width=3.0, wander=0.08), "spark"),  # ionised channels (Flame: 600 short)
    "ionised_braid":     ("ek:guilloche",   dict(), "grain"),                                   # current and field braiding
    "magnetised_jet":    ("ek:bands",       dict(n=90, shear=0.8, turb=0.20), "grain"),      # 30 bands read as plain stripes         # collimated (Flame ladder: 60 straight)
    "corona_grain":      ("ek:fbm",         dict(octaves=(256, 512, 1024)), "grain"),        # stars drew big rosettes; a corona is grainy haze                                   # violet haze, grainy
    "streamer_web":      ("frost_fern",     dict(seeds=30, branch=0.5, drift=0.4), "spark"),  # dla drew dots; streamers ARE branching fronds  # streamers branching ahead
    "townsend_cascade":  ("ek:eden",        dict(seeds=40, steps=60), "spark"),              # 8 seeds = sparse blobs; an avalanche is many fronts                  # avalanche fronts (Ignition: 60/40)
    "pinch_instability": ("metaball",       dict(blobs=60, radius=0.05), "grain"),              # sausage links (Ignition match: 1200/0.012)
    "cathode_spot":      ("ek:craters",     dict(n=300, rmin=4.0, rmax=10.0, rim=1.0), "spark"),  # attachment points (Ignition ember: 400/8-20)
    "glow_discharge":    ("ek:moire",       dict(), "grain"),                                   # even glow with striations
    "lichtenberg_burn":  ("shatter",        dict(impacts=3, radials=40), "crackle"),         # 6 big ferns read as cells at car scale; radial scar branching (Molten obsidian: 5/34)  # the fractal scar (Flame crown: 30/0.4)
    "plasma_sheath":     ("ek:crinkle",     dict(scale=260, sharp=1.4, folds=1), "grain"),      # thin charged skin (Flame sheet: 120/2/2)
    "spectral_line":     ("ek:scanline",    dict(lines=90.0, triad=1.0, bloom=1.4, roll=0.0, jitter=0.1), "grain"),  # 30 lines read as plain bands  # one narrow line (Flame torch: 140)
    "electron_avalanche": ("ek:squiggle",   dict(n=800, length=120.0, amp=10.0, confetti=0.5, width=2.0), "spark"),  # every track a carrier multiplying (Ignition fuse: 300 long trails)
    "tokamak_ripple":    ("ek:holo",        dict(rings=40.0, orders=1.0, warp=60.0, sharp=1.2), "grain"),  # nested flux surfaces (Ignition pilot: 30)
    "aurora_column":     ("ek:rt_fingers",  dict(n=22), "fibre"),                               # curtains (Flame buoyant: 40)

    # ── MOLTEN ──────────────────────────────────────────────────────────────
    "pahoehoe_skin":     ("damascus",       dict(layers=100, folds=4, twist=3.0, warp=0.4), "ridge"),  # ropy skin (Flame tongue: 60/2)
    "slag_crust":        ("ek:spall",       dict(cells=40, lift=0.8), "crackle"),               # glass plates on the melt
    "lava_cell":         ("ek:worley",      dict(cells=40), "grain"),                           # convection cells (Flame darrieus: 60)
    "quench_craze":      ("ek:anneal_crack", dict(cells=100, width=1.4), "crackle"),            # craze network
    "vitrified_glaze":   ("ek:resist",      dict(), "grain"),                                   # ash fused and pooled
    "weld_pool":         ("imbricate",      dict(rows=50, overlap=0.5), "ridge"),               # frozen crescent ripples
    "molten_drip":       ("ek:filaments",   dict(n=90, length=400, width=4.0, wander=0.05), "grain"),  # running down (Plasma arc: 40/500/3)
    "crucible_skin":     ("ek:scales",      dict(cell=30.0, keel=0.6), "ridge"),                # oxide plates curling
    "basalt_column":     ("basalt",         dict(cells=90), "ridge"),                           # columnar jointing
    "obsidian_chill":    ("shatter",        dict(impacts=5, radials=34), "flake"),              # conchoidal glass
    "foundry_spatter":   ("ek:splatter",    dict(blobs=1600, rmax=10.0, drips=0.3, spatter=1.4), "spark"),  # 600 was sparse  # thrown metal (Ignition brands: 400/18)
    "tuyere_glow":       ("ek:holo",        dict(rings=20.0, orders=1.0, warp=120.0, sharp=1.0), "grain"),  # plain glow; concentric heat zones seen through the port (Ignition pilot 30, Plasma tokamak 40)            # the hottest zone (Ignition auto: 16-256)
    "slumped_glass":     ("ek:dunes",       dict(n=20, crest=1.2), "grain"),                    # gone soft, taken the shape
    "magma_vesicle":     ("ek:craters",     dict(n=3000, rmin=2.0, rmax=8.0, rim=0.6), "crackle"),  # bubbles frozen (Plasma spot: 300/4-10)
    "ropy_flow":         ("ridge_flow",     dict(ridges=140, cores=3), "fibre"),                # parallel ropes (Flame candle: 90/2)

    # ── CINDER ──────────────────────────────────────────────────────────────
    "ember_bed":         ("ek:percolate",   dict(cells=90, p=0.55), "spark"),                   # all heat, no flame (Ignition smoulder: 70/0.5)
    "ash_fall":          ("ek:fbm",         dict(octaves=(128, 256, 512, 1024)), "grain"),      # fine grey settling (fine octaves)
    "soot_bloom":        ("ek:curl",        dict(scale=60, steps=20), "grain"),               # dla drew dots at any scale; soot blooms as fine smoke curls  # carbon dendrites (Plasma streamer: 20 trees)
    "char_scale":        ("ek:spall",       dict(cells=60, lift=0.9), "crackle"),               # alligator scale lifted (Molten slag: 40/0.8)
    "cinder_lattice":    ("ek:knurl",       dict(pitch=22.0, angle=0.0, wobble=0.5), "spark"),  # pixel blocks read as a mosaic; a burnt, buckled lattice    # charred blocks that survived
    "fly_ash":           ("ek:discs",       dict(n=4000, radius=4.0), "grain"),                 # spent particles drifting
    "coke_cell":         ("ek:honeycomb",   dict(), "crackle"),                                 # carbon cell walls
    "clinker_crust":     ("ek:facets",      dict(stones=300, table=0.4), "crackle"),            # hard and vitreous
    "ash_glaze":         ("ek:anneal_crack", dict(cells=140, width=1.0), "crackle"),            # crazed as it cooled (Molten quench: 100/1.4)
    "dying_coal":        ("metaball",       dict(blobs=1500, radius=0.012), "spark"),     # 500 lumps at 0.02 = SCALE 0.08; smaller coals             # heat retreating into each lump
    "grey_front":        ("ek:eden",        dict(seeds=30, steps=50), "grain"),                 # ash advancing over ember
    "retained_heat":     ("gray_scott",     dict(feed=0.030, kill=0.062), "grain"),             # convection in the core
    "powder_burn":       ("ek:splatter",    dict(blobs=5000, rmax=3.0, drips=0.0, spatter=1.0), "spark"),  # scorched powder
    "spall_field":       ("ek:craters",     dict(n=800, rmin=4.0, rmax=12.0, rim=0.7), "crackle"),  # flakes popped off
    "cold_ash":          ("ek:wrinkle",     dict(k=1.2, steps=14), "grain"),                    # powder holding the shape (Flame front: 1.8/22)
}

# keyed-detail amount (default 0.40)
DETAIL = {
    "pilot_ring": 0.65, "tokamak_ripple": 0.65, "autoignition": 0.60, "tuyere_glow": 0.65,
    "spectral_line": 0.60, "laminar_ladder": 0.55, "kindle_lattice": 0.55, "basalt_column": 0.85,
    "slag_crust": 0.55, "char_scale": 0.55, "cinder_lattice": 0.60, "pinch_instability": 0.60,
    "obsidian_chill": 0.80, "streamer_web": 0.70, "dying_coal": 0.60,  # SCALE 0.14 / 0.165 / 0.08 on the gate
}

# how much of the construction's own field rides on the cell tone (default 0.52)
RELIEF = {"basalt_column": 0.95, "slag_crust": 0.85, "char_scale": 0.85, "kindle_lattice": 0.75, "coke_cell": 0.75}

# a second, smaller construction nested in the first (intricacy) — stem -> (form, params, weight)
FINE = {
    "flashpoint":        ("ek:sparks",    dict(), 0.30),                                   # the first sparks on the front
    "char_creep":        ("ek:threads",   dict(), 0.25),                                   # the grain itself
    "tinder_bloom":      ("ek:stars",     dict(), 0.30),                                   # points of ignition
    "match_head":        ("ek:craters",   dict(n=6000, rmin=0.7, rmax=1.8, rim=0.4), 0.25),  # chemical grain
    "smoulder_bed":      ("ek:craters",   dict(n=4000, rmin=1.0, rmax=3.0, rim=0.5), 0.30),  # the bed's particles
    "fuse_line":         ("ek:sparks",    dict(), 0.30),                                   # spitting
    "kindle_lattice":    ("ek:threads",   dict(), 0.25),                                   # wood grain on the sticks
    "spark_shower":      ("ek:stars",     dict(), 0.25),                                   # burnt-out particles
    "ember_catch":       ("ek:anneal_crack", dict(cells=220, width=1.0), 0.30),           # char craze around the cores
    "pilot_ring":        ("ek:threads",   dict(), 0.20),                                   # the braids in the crown
    "autoignition":      ("ek:stars",     dict(), 0.25),                                   # simultaneous points
    "firebrand_scatter": ("ek:sparks",    dict(), 0.25),                                   # trailing sparks
    "scorch_front":      ("ek:anneal_crack", dict(cells=200, width=1.2), 0.30),           # char craze in the burned zone
    "ignition_delay":    ("ek:fbm",       dict(octaves=(256, 512, 1024)), 0.20),          # vapour grain
    "touchpaper":        ("ek:craters",   dict(n=5000, rmin=0.8, rmax=2.0, rim=0.4), 0.25),  # burn-through pinholes
    "diffusion_sheet":   ("ek:fbm",       dict(octaves=(256, 512, 1024)), 0.20),          # soot on the sheet
    "wrinkled_front":    ("ek:scanline",  dict(lines=500.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.4), 0.20),  # cusp lines
    "darrieus_cell":     ("ek:craters",   dict(n=6000, rmin=0.8, rmax=2.0, rim=0.4), 0.25),  # cell texture
    "turbulent_braid":   ("ek:threads",   dict(), 0.25),                                   # fine braid strands
    "flamelet_storm":    ("ek:stars",     dict(), 0.25),                                   # flamelet tips
    "buoyant_fingers":   ("ek:fbm",       dict(octaves=(256, 512, 1024)), 0.20),          # hot-gas grain
    "shear_tongue":      ("ek:scanline",  dict(lines=450.0, triad=1.0, bloom=0.3, roll=0.1, jitter=0.4), 0.20),  # shear striations
    "pool_puff":         ("ek:stars",     dict(), 0.20),                                   # soot glints
    "candle_cone":       ("ek:fbm",       dict(octaves=(512, 1024)), 0.15),               # the quiet laminar grain
    "blowtorch":         ("ek:sparks",    dict(), 0.25),                                   # carried particles
    "backdraft_wrinkle": ("ek:threads",   dict(), 0.25),                                   # fold strands
    "fire_whirl_grain":  ("ek:filaments", dict(n=500, length=50, width=1.0, wander=0.2), 0.30),  # stretched filaments
    "laminar_ladder":    ("ek:fbm",       dict(octaves=(512, 1024)), 0.20),               # rung texture
    "crown_fire":        ("ek:sparks",    dict(), 0.30),                                   # embers off the canopy
    "stoichiometric_seam": ("ek:stars",   dict(), 0.20),                                  # boron points
    "arc_filament":      ("ek:sparks",    dict(), 0.30),                                   # side-arcs
    "ionised_braid":     ("ek:stars",     dict(), 0.25),                                   # recombination glints
    "magnetised_jet":    ("ek:filaments", dict(n=400, length=120, width=1.0, wander=0.05), 0.30),  # field lines
    "corona_grain":      ("ek:craters",   dict(n=8000, rmin=0.5, rmax=1.4, rim=0.4), 0.25),  # grain
    "streamer_web":      ("ek:sparks",    dict(), 0.25),                                   # tips
    "townsend_cascade":  ("ek:stars",     dict(), 0.30),                                   # carriers
    "pinch_instability": ("ek:scanline",  dict(lines=400.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.3), 0.20),  # pinch striations
    "cathode_spot":      ("ek:sparks",    dict(), 0.30),                                   # skittering
    "glow_discharge":    ("ek:fbm",       dict(octaves=(256, 512, 1024)), 0.20),          # even grain
    "lichtenberg_burn":  ("ek:anneal_crack", dict(cells=240, width=1.0), 0.30),           # scorched wood craze
    "plasma_sheath":     ("ek:stars",     dict(), 0.20),                                   # sheath sparkle
    "spectral_line":     ("ek:fbm",       dict(octaves=(512, 1024)), 0.20),               # emission grain
    "electron_avalanche": ("ek:stars",    dict(), 0.25),                                   # carriers
    "tokamak_ripple":    ("ek:threads",   dict(), 0.20),                                   # flux-surface fibre
    "aurora_column":     ("ek:threads",   dict(), 0.30),                                   # curtain rays
    "pahoehoe_skin":     ("ek:crinkle",   dict(scale=400, sharp=2.0, folds=1), 0.30),     # skin texture on the ropes
    "slag_crust":        ("ek:craters",   dict(n=5000, rmin=0.8, rmax=2.2, rim=0.4), 0.30),  # gas pits in the glass
    "lava_cell":         ("ek:anneal_crack", dict(cells=220, width=1.0), 0.30),           # crust cracking on the cells
    "quench_craze":      ("ek:stars",     dict(), 0.20),                                   # glass glints
    "vitrified_glaze":   ("ek:craters",   dict(n=6000, rmin=0.7, rmax=1.8, rim=0.4), 0.25),  # pinholes
    "weld_pool":         ("ek:scanline",  dict(lines=500.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.2), 0.25),  # ripple lines on the crescents
    "molten_drip":       ("ek:stars",     dict(), 0.20),                                   # sparks off the drip
    "crucible_skin":     ("ek:anneal_crack", dict(cells=240, width=1.0), 0.30),           # oxide craze on the plates
    "basalt_column":     ("ek:worley",    dict(cells=260), 0.30),                          # crystal mosaic
    "obsidian_chill":    ("ek:scanline",  dict(lines=450.0, triad=1.0, bloom=0.3, roll=0.2, jitter=0.5), 0.25),  # conchoidal ripples
    "foundry_spatter":   ("ek:craters",   dict(n=4000, rmin=1.0, rmax=3.0, rim=0.5), 0.30),  # pocks where it landed
    "tuyere_glow":       ("ek:craters",   dict(n=5000, rmin=0.8, rmax=2.0, rim=0.4), 0.25),  # coke grain
    "slumped_glass":     ("ek:holo",      dict(rings=500.0, orders=1.0, sharp=1.2), 0.20),  # glass sheen
    "magma_vesicle":     ("ek:fbm",       dict(octaves=(512, 1024)), 0.20),               # rock grain between bubbles
    "ropy_flow":         ("ek:crinkle",   dict(scale=380, sharp=2.2, folds=1), 0.30),     # skin on the ropes
    "ember_bed":         ("ek:craters",   dict(n=5000, rmin=0.8, rmax=2.2, rim=0.5), 0.30),  # the coals' surface
    "ash_fall":          ("ek:stars",     dict(), 0.15),                                   # glints in the ash
    "soot_bloom":        ("ek:stars",     dict(), 0.20),                                   # inception points
    "char_scale":        ("ek:anneal_crack", dict(cells=240, width=1.0), 0.30),           # craze on the scales
    "cinder_lattice":    ("ek:sparks",    dict(), 0.30),                                   # embers in the cracks
    "fly_ash":           ("ek:fbm",       dict(octaves=(512, 1024)), 0.20),               # haze grain
    "coke_cell":         ("ek:craters",   dict(n=6000, rmin=0.7, rmax=1.8, rim=0.4), 0.30),  # pores in the walls
    "clinker_crust":     ("ek:craters",   dict(n=4000, rmin=1.0, rmax=2.8, rim=0.5), 0.30),  # vesicles in the clinker
    "ash_glaze":         ("ek:stars",     dict(), 0.20),                                   # glaze glints
    "dying_coal":        ("ek:anneal_crack", dict(cells=200, width=1.2), 0.30),           # cooling cracks on the lumps
    "grey_front":        ("ek:fbm",       dict(octaves=(256, 512, 1024)), 0.25),          # ash grain
    "retained_heat":     ("ek:craters",   dict(n=5000, rmin=0.8, rmax=2.0, rim=0.4), 0.25),  # surface texture
    "powder_burn":       ("ek:stars",     dict(), 0.30),                                   # the grains alight
    "spall_field":       ("ek:anneal_crack", dict(cells=220, width=1.0), 0.30),           # thermal-shock craze
    "cold_ash":          ("ek:fbm",       dict(octaves=(256, 512, 1024)), 0.25),          # powder grain
}


def stem(fid):
    return fid[4:] if fid.startswith("ffl_") else fid


def form_for(fid):
    s = stem(fid)
    if s not in FORMS:
        raise ValueError("%s: no construction authored" % fid)
    return FORMS[s]


def check(table):
    ids = list(table)
    missing = sorted({stem(f) for f in ids} - set(FORMS))
    if missing:
        raise ValueError("finishes with no construction: %s" % missing)
    pairs = {}
    for s, (form, params, _k) in FORMS.items():
        pairs.setdefault((form, tuple(sorted((k, str(v)) for k, v in params.items()))), []).append(s)
    same = {k: v for k, v in pairs.items() if len(v) > 1}
    if same:
        raise ValueError("identical construction+params: " + "; ".join(", ".join(v) for v in same.values()))
    by_chapter = {}
    for f in ids:
        by_chapter.setdefault(table[f].get("chapter"), []).append(FORMS[stem(f)][0])
    for ch, forms in by_chapter.items():
        if len(set(forms)) != len(forms):
            d = sorted({x for x in forms if forms.count(x) > 1})
            raise ValueError("FRACTURED FLAMES chapter %r reuses constructions: %s" % (ch, d))
    forms_only = [f for f, _p, _k in FORMS.values()]
    return {"finishes": len(FORMS), "distinct": len(set(forms_only)),
            "cross_chapter_reuse": len(forms_only) - len(set(forms_only)),
            "fine_missing": sorted(set(FORMS) - set(FINE))}
