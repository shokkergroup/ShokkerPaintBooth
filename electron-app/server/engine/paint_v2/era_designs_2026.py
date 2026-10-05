# -*- coding: utf-8 -*-
"""ERA SHELVES — one CONSTRUCTION per finish, chosen from what the finish IS.

Owner 2026-09-01: "YOU BUILD THE FINISHES FIRST THEN SPEC TO THE FINISHES."
Owner 2026-09-02: "MAKE IMAGES ... 1) spectacular? 2) UNIQUE? 3) lives up to the
NAME? 4) Will Ricky LOVE it? ... iterate ... pick the BEST."

The five era shelves (TACTICAL & FIELD, ALL THAT, BAD & RAD, CYBERPUNK, FAR OUT)
were built as `stack` recipes: two or three primitives from one kit, combined —
so a great many finishes on each shelf shared a construction with a neighbour,
and the hand-authored decks were laid on that duplicated paint.

era_base_2026.make() consults DESIGNS[prefix][fid] when present: construction
(ek:/NF dispatch) -> keyed detail -> PLACES -> FINE nested construction. The old
`stack` stays on the recipe for provenance and as the fallback for any finish not
yet designed here.

RULES per shelf (check()): every finish designed; no construction reused within a
LANE (the fifteen the picker shows together); no (construction, params) pair
reused anywhere on the shelf; cross-lane reuse reported as a count.
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════
# TACTICAL & FIELD (tac_)  — lanes: camo / hardware / field / night
# ═══════════════════════════════════════════════════════════════════════════
TACTICAL = {
    # camo
    "tac_m81_woodland":      ("ek:camo",         dict(patches=4, blob=150.0, roughness=1.0), "grain"),
    "tac_marpat_digital":    ("ek:digicam",      dict(cell=7.0, patches=4, cluster=2.2), "grain"),
    "tac_tiger_stripe":      ("ek:bands",        dict(n=44, shear=0.9, turb=0.7), "fibre"),          # horizontal brush strokes
    "tac_multicam_transition": ("ek:resist",     dict(), "grain"),                                   # colours that blend, not edge
    "tac_desert_dpm":        ("ek:eden",         dict(seeds=90, steps=30), "grain"),                 # two-colour disruptive blotches
    "tac_snow_overwhite":    ("ek:wrinkle",      dict(k=1.6, steps=20), "fibre"),                    # an oversuit's folds
    "tac_duck_blind":        ("ek:filaments",    dict(n=320, length=220, width=2.0, wander=0.10), "fibre"),  # reed and cattail
    "tac_urban_grey_digital": ("ek:pixels",      dict(cell=14.0, levels=4, dither=0.25), "grain"),
    "tac_brushstroke_field": ("ek:splatter",     dict(blobs=260, rmax=40.0, drips=0.7, spatter=0.6), "fibre"),  # painted by hand
    "tac_frog_skin":         ("ek:percolate",    dict(cells=60, p=0.48), "stipple"),                 # reversible spots
    "tac_chocolate_chip":    ("ek:craters",      dict(n=900, rmin=4.0, rmax=9.0, rim=0.5), "grain"), # black pebble spots
    "tac_rain_pattern":      ("ek:threads",      dict(), "fibre"),                                   # vertical dashes
    "tac_flecktarn":         ("ek:discs",        dict(n=6000, radius=5.0), "stipple"),               # dense spots dithering
    "tac_tigerstripe_night": ("ek:kh_braid",     dict(layers=22, shear=3.0), "fibre"),               # stripes in blacks
    "tac_break_up_bark":     ("ek:crinkle",      dict(scale=130, sharp=2.6, folds=2), "ridge"),      # photo bark
    # hardware
    "tac_cerakote_grey":     ("ek:fbm",          dict(octaves=(96, 192, 384, 768)), "grain"),        # sprayed thin, flat
    "tac_parkerised":        ("ek:craters",      dict(n=7000, rmin=0.7, rmax=1.8, rim=0.4), "grain"),  # porous phosphate (camo chips: 900/4-9)
    "tac_fde_polymer":       ("ek:knurl",        dict(pitch=18.0, angle=0.0, wobble=0.15), "grain"), # moulded-in texture
    "tac_kydex_sheet":       ("ek:scales",       dict(cell=9.0, keel=0.15), "grain"),                # pebble grain
    "tac_gun_blue":          ("ek:curl",         dict(scale=180, steps=30), "grain"),                # the oil wipe
    "tac_rail_section":      ("ek:scanline",     dict(lines=60.0, triad=1.0, bloom=0.5, roll=0.0, jitter=0.0), "ridge"),  # slots at a fixed pitch
    "tac_suppressor_heat":   ("ek:holo",         dict(rings=24.0, orders=1.0, warp=90.0, sharp=1.2), "grain"),  # heat-tint zones
    "tac_optic_glass":       ("ek:moire",        dict(), "flake"),                                   # multi-coat interference
    "tac_stippled_grip":     ("ek:splatter",     dict(blobs=6000, rmax=3.0, drips=0.0, spatter=1.0), "stipple"),  # soldering-iron stipple (camo strokes: 260/40)
    "tac_anodised_hard":     ("ek:worley",       dict(cells=220), "grain"),                          # hardcoat grain
    "tac_carbon_handguard":  ("ek:sett",         dict(pitch=26.0, twill=2.0), "fibre"),              # twill under resin
    "tac_nitride_black":     ("ek:percolate",    dict(cells=200, p=0.5), "grain"),                   # nitrided grain (camo frog: 60)
    "tac_battle_worn":       ("ek:spall",        dict(cells=60, lift=0.6), "crackle"),               # worn through at edges
    "tac_titanium_bead":     ("ek:discs",        dict(n=9000, radius=2.0), "grain"),                 # bead blast (camo fleck: 6000/5)
    "tac_sling_webbing":     ("ek:bands",        dict(n=120, shear=0.0, turb=0.05), "fibre"),        # nylon weave (camo tiger: 44 sheared)
    # field
    "tac_blaze_orange":      ("ek:ikat",         dict(), "fibre"),                                   # fluorescent knit, dye slightly bled
    "tac_canvas_duck":       ("ek:knurl",        dict(pitch=11.0, angle=0.0, wobble=0.1), "fibre"),  # twelve-ounce weave (hardware fde: 18)
    "tac_neoprene_wader":    ("ek:honeycomb",    dict(), "grain"),                                   # closed-cell foam
    "tac_trout_flank":       ("ek:scales",       dict(cell=16.0, keel=0.4), "flake"),                # guanine platelets (hardware kydex: 9/0.15)
    "tac_cedar_decoy":       ("ek:crinkle",      dict(scale=220, sharp=1.8, folds=1), "ridge"),      # carved, chipped (camo bark: 130/2.6)
    "tac_river_stone":       ("apollonian",      dict(rmax=0.07), "grain"),                          # rounded cobble
    "tac_topo_sheet":        ("ek:topo",         dict(lines=110.0, width=2.0), "grain"),             # the quad
    "tac_autumn_brush":      ("ek:eden",         dict(seeds=260, steps=22), "grain"),                # oak and maple patches (camo dpm: 90/30)
    "tac_fly_line":          ("ridge_flow",      dict(ridges=60, cores=2), "fibre"),                 # coils of line
    "tac_blaze_cap":         ("ek:sett",         dict(pitch=14.0, twill=1.0), "fibre"),              # knit (hardware carbon: 26/2)
    "tac_wet_waxed_cotton":  ("ek:wrinkle",      dict(k=2.2, steps=26), "grain"),                    # wax bloomed in the creases (camo overwhite: 1.6/20)
    "tac_creel_wicker":      ("ek:bricks",       dict(rows=40, cols=8, bind=0.08), "fibre"),         # split willow woven
    "tac_marsh_reed":        ("ek:filaments",    dict(n=180, length=420, width=2.5, wander=0.04), "fibre"),  # standing dead (camo duck: 320/220)
    "tac_bird_dog_tick":     ("ek:craters",      dict(n=4500, rmin=1.2, rmax=3.0, rim=0.5), "stipple"),  # roan ticking (hardware parkerised: 7000/0.7-1.8)
    "tac_frozen_bank":       ("ek:anneal_crack", dict(cells=70, width=2.0), "crackle"),              # shelf ice
    # night
    "tac_night_vision":      ("ek:stars",        dict(), "grain"),                                   # phosphor scintillation
    "tac_thermal_white_hot": ("gray_scott",      dict(feed=0.034, kill=0.063), "grain"),             # heat blobs
    "tac_ir_flat":           ("ek:percolate",    dict(cells=140, p=0.46), "grain"),                  # IR-matched black (hardware nitride: 200/0.5)
    "tac_chem_light":        ("ek:squiggle",     dict(n=240, length=220.0, amp=12.0, confetti=0.1, width=6.0), "grain"),  # snapped sticks
    "tac_muzzle_flash":      ("ek:splatter",     dict(blobs=2600, rmax=20.0, drips=0.2, spatter=2.6), "spark"),  # the flash blooming everywhere (1200 still left 71% void)
    "tac_moonlit_snow":      ("ek:dunes",        dict(n=28, crest=1.6), "grain"),                    # drifts with no colour
    "tac_starlight_scope":   ("ek:fbm",          dict(octaves=(256, 512, 1024)), "grain"),           # intensifier grain (hardware cerakote: 96-768)
    "tac_tracer_arc":        ("ek:filaments",    dict(n=260, length=520, width=2.2, wander=0.02), "spark"),  # every fifth round, a whole belt of them (70 left 55% void)
    "tac_red_lens":          ("ek:holo",         dict(rings=140.0, orders=1.0, warp=30.0, sharp=1.0), "grain"),  # filter over a map (hardware suppressor: 24)
    "tac_cold_steel_night":  ("ek:curl",         dict(scale=90, steps=18), "flake"),                 # bare metal, breath on it (hardware gun blue: 180/30)
    "tac_thermal_black_hot": ("ek:worley",       dict(cells=48), "grain"),                           # inverted palette cells (hardware anodised: 220)
    "tac_ambush_green":      ("ek:camo",         dict(patches=9, blob=50.0, roughness=1.5), "grain"),  # foliage through a tube (camo m81: 4/150)
    "tac_signal_mirror":     ("ek:facets",       dict(stones=260, table=0.45), "flake"),             # two square inches of glass
    "tac_blackout_curtain":  ("ek:shag",         dict(strands=9000, length=18, splay=1.2), "fibre"), # napped cloth
    "tac_frost_breath":      ("frost_fern",      dict(seeds=40, branch=0.4, drift=0.3), "flake"),    # vapour freezing on a collar
}

# ═══════════════════════════════════════════════════════════════════════════
# ALL THAT (at_) — lanes: cdrom / extreme / fresh / flannel
# ═══════════════════════════════════════════════════════════════════════════
ALL_THAT = {
    # cdrom
    "at_disc_rainbow":       ("ek:holo",         dict(rings=380.0, orders=3.0, warp=40.0, sharp=1.2), "flake"),  # data pits diffracting
    "at_beige_box":          ("ek:knurl",        dict(pitch=9.0, angle=0.0, wobble=0.3), "grain"),    # textured ABS
    "at_windows_teal":       ("ek:pixels",       dict(cell=24.0, levels=5, dither=0.1), "grain"),     # the desktop
    "at_pipes_screensaver":  ("maze",            dict(cells=48), "ridge"),                            # pipes at right angles, forever
    "at_y2k_chrome":         ("metaball",        dict(blobs=400, radius=0.03), "flake"),              # bubble chrome type
    "at_dial_up_green":      ("ek:microtext",    dict(), "grain"),                                    # a terminal at 14.4k
    "at_frosted_shell":      ("ek:craters",      dict(n=8000, rmin=0.6, rmax=1.6, rim=0.3), "grain"), # frosted polycarbonate
    "at_corrupt_jpeg":       ("ek:glitch",       dict(slices=48, shift=36.0, tear=0.35, block=0.4), "grain"),  # failed at 74%
    "at_floppy_black":       ("ek:bands",        dict(n=70, shear=0.0, turb=0.03), "ridge"),          # shutter slots and label lines
    "at_holo_sticker":       ("ek:scales",       dict(cell=12.0, keel=0.2), "flake"),                 # hologram facets
    "at_crt_blue_screen":    ("ek:scanline",     dict(lines=260.0, triad=3.0, bloom=0.8, roll=0.1, jitter=0.1), "grain"),  # the raster
    "at_mouse_ball_grime":   ("ek:percolate",    dict(cells=110, p=0.5), "grain"),                    # what the rollers held
    "at_zip_disk":           ("ek:worley",       dict(cells=64), "grain"),                            # moulded shell cells
    "at_iridescent_cd_r":    ("moire_beat",      dict(a=200.0, b=212.0, angle=0.05), "flake"),        # green-gold underside
    "at_cyber_café":    ("ek:honeycomb",    dict(), "grain"),                                    # perforated steel desks
    # extreme
    "at_snowboard_graphic":  ("ek:splatter",     dict(blobs=500, rmax=30.0, drips=0.4, spatter=1.0), "grain"),  # sublimated, scratched
    "at_windbreaker_block":  ("ek:polygons",     dict(cells=34, width=3.0), "grain"),                 # colour-blocked nylon (18 cells: SCALE 0.10)
    "at_dew_green":          ("ek:stars",        dict(), "grain"),                                    # visible from the other end
    "at_skatepark_concrete": ("ek:craters",      dict(n=3000, rmin=1.5, rmax=5.0, rim=0.4), "grain"), # poured bowl (cdrom frosted: 8000/0.6-1.6)
    "at_grip_tape":          ("ek:facets",       dict(stones=2200, table=0.2), "grain"),              # silicon carbide grit
    "at_big_dog_print":      ("ek:tooled",       dict(cell=120.0, petals=4, stamp=0.8, bevel=0.5), "grain"),  # cartoon print
    "at_surf_wax":           ("ek:dunes",        dict(n=36, crest=2.0), "grain"),                     # combed wax
    "at_bmx_dirt":           ("ek:worley",       dict(cells=160), "grain"),                          # packed clods (fbm read as plain mottle on the variant sheet; cdrom zip: 64)
    "at_anodised_peg":       ("ek:knurl",        dict(pitch=30.0, angle=0.785, wobble=0.0), "grain"), # scraped knurl (cdrom beige: 9 orthogonal)
    "at_neon_wetsuit":       ("ek:digicam",      dict(cell=30.0, patches=3, cluster=3.0), "grain"),   # fluoro panels
    "at_half_pipe_ply":      ("ek:bands",        dict(n=22, shear=0.0, turb=0.02), "ridge"),          # masonite seams (cdrom floppy: 70)
    "at_roller_blade":       ("ek:scales",       dict(cell=34.0, keel=0.5), "grain"),                 # vented shell (cdrom holo sticker: 12)
    "at_mountain_topo":      ("ek:topo",         dict(lines=120.0, width=2.2), "grain"),              # a trail map
    "at_chain_link":         ("ek:sett",         dict(pitch=34.0, twill=1.0), "ridge"),               # diamond mesh
    "at_bungee_cord":        ("ek:kh_braid",     dict(layers=40, shear=2.4), "fibre"),                # woven sheath
    # fresh
    "at_velour_tracksuit":   ("ek:shag",         dict(strands=8000, length=20, splay=1.3), "fibre"),  # the nap
    "at_gold_rope":          ("imbricate",       dict(rows=46, overlap=0.5), "flake"),                # herringbone links
    "at_cross_colour_block": ("ek:polygons",     dict(cells=22, width=4.0), "grain"),                 # primary blocks (10 cells: SCALE 0.11; extreme windbreaker: 34)
    "at_airbrush_tee":       ("ek:curl",         dict(scale=140, steps=26), "grain"),                 # boardwalk airbrush
    "at_bucket_hat":         ("ek:sett",         dict(pitch=18.0, twill=2.0), "fibre"),               # cotton twill (extreme chain link: 34 plain)
    "at_fresh_kicks":        ("ek:craters",      dict(n=1400, rmin=3.0, rmax=6.0, rim=0.7), "grain"), # mesh panel holes
    "at_boombox_chrome":     ("ek:knurl",        dict(pitch=6.0, angle=0.0, wobble=0.0), "flake"),    # perforated grille (cdrom beige: 9 wobbly)
    "at_velour_rose":        ("ek:crinkle",      dict(scale=160, sharp=1.6, folds=2), "fibre"),       # crushed nap
    "at_nameplate_gold":     ("ek:tooled",       dict(cell=80.0, petals=6, stamp=0.6, bevel=1.0), "flake"),  # cut from sheet (extreme big dog: 120/4)
    "at_denim_baggy":        ("ek:ikat",         dict(), "fibre"),                                    # stonewashed
    "at_graffiti_fill":      ("ek:splatter",     dict(blobs=900, rmax=30.0, drips=0.9, spatter=0.8), "grain"),  # two-tone fill, covered (200 big blobs left 50% void)
    "at_kangol_felt":        ("ek:threads",      dict(), "fibre"),                                    # angora nap
    "at_grill_chrome":       ("ek:facets",       dict(stones=120, table=0.6), "flake"),               # polished grill (extreme grip: 2200 grit)
    "at_vinyl_crate":        ("ek:guilloche",    dict(), "grain"),                                    # sleeves gone soft
    "at_starter_jacket":     ("ek:moire",        dict(), "flake"),                                    # satin shell sheen
    # flannel
    "at_flannel_red":        ("ek:sett",         dict(pitch=48.0, twill=2.0), "fibre"),               # buffalo check (fresh bucket: 18)
    "at_flannel_forest":     ("ek:knurl",        dict(pitch=52.0, angle=0.0, wobble=0.05), "fibre"),  # windowpane (cdrom beige: 9)
    "at_thrift_cardigan":    ("ek:scales",       dict(cell=20.0, keel=0.3), "fibre"),                 # knit stitches (extreme blade: 34)
    "at_seattle_rain":       ("ek:rt_fingers",   dict(n=60), "grain"),                                # the constant fine one
    "at_moss_sidewalk":      ("ek:percolate",    dict(cells=80, p=0.44), "grain"),                    # the cracks (cdrom grime: 110/0.5)
    "at_doc_marten":         ("ek:wrinkle",      dict(k=2.0, steps=24), "ridge"),                     # creased across the vamp
    "at_distressed_denim":   ("ek:spall",        dict(cells=44, lift=0.55), "fibre"),                 # worn through at the knee
    "at_band_tee_crack":     ("ek:anneal_crack", dict(cells=54, width=2.2), "crackle"),               # plastisol cracked
    "at_corduroy_olive":     ("ek:bands",        dict(n=96, shear=0.3, turb=0.15), "ridge"),          # narrow wale (cdrom floppy 70, extreme ply 22)
    "at_overcast_grey":      ("ek:dunes",        dict(n=10, crest=1.2), "grain"),                     # cloud strata (fbm read as plain mottle on the variant sheet; extreme wax: 36/2.0)
    "at_basement_amp":       ("ek:craters",      dict(n=6000, rmin=0.8, rmax=2.2, rim=0.5), "grain"), # tolex pebble (fresh kicks: 1400/3-6)
    "at_combat_boot_steel":  ("ek:eden",         dict(seeds=40, steps=40), "flake"),                  # steel showing through
    "at_sharpie_ink":        ("ek:squiggle",     dict(n=700, length=90.0, amp=14.0, confetti=0.2, width=3.0), "grain"),  # lyrics on a forearm
    "at_cassette_tape":      ("ek:scanline",     dict(lines=90.0, triad=1.0, bloom=0.4, roll=0.0, jitter=0.2), "ridge"),  # the tape (cdrom crt: 260 triad)
    "at_chipped_nail":       ("ek:camo",         dict(patches=3, blob=60.0, roughness=1.8), "flake"), # picked at
}

# keyed detail amount (default 0.40) — coarse constructions ask for more
DETAIL = {
    "tac_m81_woodland": 0.55, "tac_multicam_transition": 0.6, "tac_desert_dpm": 0.55, "tac_urban_grey_digital": 0.55,
    "tac_brushstroke_field": 0.55, "tac_rail_section": 0.6, "tac_suppressor_heat": 0.65, "tac_river_stone": 0.55,
    "tac_moonlit_snow": 0.6, "tac_ambush_green": 0.55, "tac_thermal_black_hot": 0.6,
    "at_windows_teal": 0.55, "at_pipes_screensaver": 0.6, "at_y2k_chrome": 0.6, "at_windbreaker_block": 0.65,
    "at_neon_wetsuit": 0.6, "at_half_pipe_ply": 0.6, "at_cross_colour_block": 0.7, "at_flannel_red": 0.5,
    "at_flannel_forest": 0.55, "at_overcast_grey": 0.6, "at_chipped_nail": 0.6,
}

# a second, smaller construction nested inside the first (intricacy)
FINE = {
    # TACTICAL
    "tac_m81_woodland":      ("ek:threads",  dict(), 0.25),                                   # the cotton it is printed on
    "tac_marpat_digital":    ("ek:sett",     dict(pitch=8.0, twill=1.0), 0.25),               # nyco weave
    "tac_tiger_stripe":      ("ek:threads",  dict(), 0.25),
    "tac_multicam_transition": ("ek:sett",   dict(pitch=9.0, twill=2.0), 0.25),
    "tac_desert_dpm":        ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),                # faded cotton
    "tac_snow_overwhite":    ("ek:threads",  dict(), 0.20),
    "tac_duck_blind":        ("ek:fbm",      dict(octaves=(256, 512, 1024)), 0.20),
    "tac_urban_grey_digital": ("ek:sett",    dict(pitch=8.0, twill=1.0), 0.25),
    "tac_brushstroke_field": ("ek:threads",  dict(), 0.25),                                   # shelter-half canvas
    "tac_frog_skin":         ("ek:sett",     dict(pitch=9.0, twill=1.0), 0.25),
    "tac_chocolate_chip":    ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),
    "tac_rain_pattern":      ("ek:sett",     dict(pitch=9.0, twill=2.0), 0.25),
    "tac_flecktarn":         ("ek:threads",  dict(), 0.20),
    "tac_tigerstripe_night": ("ek:sett",     dict(pitch=8.0, twill=1.0), 0.25),
    "tac_break_up_bark":     ("ek:scanline", dict(lines=500.0, triad=1.0, bloom=0.3, roll=0.1, jitter=0.5), 0.20),  # bark striations
    "tac_cerakote_grey":     ("ek:craters",  dict(n=8000, rmin=0.5, rmax=1.4, rim=0.3), 0.20),  # spray texture
    "tac_parkerised":        ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),
    "tac_fde_polymer":       ("ek:craters",  dict(n=7000, rmin=0.6, rmax=1.6, rim=0.4), 0.25),  # mould texture
    "tac_kydex_sheet":       ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),
    "tac_gun_blue":          ("ek:scanline", dict(lines=600.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.2), 0.25),  # 400-grit lines
    "tac_rail_section":      ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),                # anodised grain
    "tac_suppressor_heat":   ("ek:scanline", dict(lines=450.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.2), 0.20),  # machining marks
    "tac_optic_glass":       ("ek:stars",    dict(), 0.20),                                   # dust on the coating
    "tac_stippled_grip":     ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),
    "tac_anodised_hard":     ("ek:craters",  dict(n=9000, rmin=0.5, rmax=1.2, rim=0.3), 0.20),
    "tac_carbon_handguard":  ("ek:stars",    dict(), 0.20),                                   # resin glints
    "tac_nitride_black":     ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),
    "tac_battle_worn":       ("ek:scanline", dict(lines=500.0, triad=1.0, bloom=0.3, roll=0.2, jitter=0.6), 0.25),  # scratches
    "tac_titanium_bead":     ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),
    "tac_sling_webbing":     ("ek:threads",  dict(), 0.25),
    "tac_blaze_orange":      ("ek:sett",     dict(pitch=9.0, twill=1.0), 0.30),               # the weave
    "tac_canvas_duck":       ("ek:threads",  dict(), 0.25),
    "tac_neoprene_wader":    ("ek:craters",  dict(n=8000, rmin=0.5, rmax=1.4, rim=0.3), 0.25),  # foam cells
    "tac_trout_flank":       ("ek:stars",    dict(), 0.25),                                   # platelet glints
    "tac_cedar_decoy":       ("ek:scanline", dict(lines=450.0, triad=1.0, bloom=0.3, roll=0.1, jitter=0.5), 0.25),  # wood grain
    "tac_river_stone":       ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),                # stone grain
    "tac_topo_sheet":        ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),                # paper
    "tac_autumn_brush":      ("ek:threads",  dict(), 0.20),                                   # twigs
    "tac_fly_line":          ("ek:stars",    dict(), 0.15),
    "tac_blaze_cap":         ("ek:threads",  dict(), 0.25),                                   # yarn
    "tac_wet_waxed_cotton":  ("ek:craters",  dict(n=5000, rmin=0.8, rmax=2.2, rim=0.5), 0.25),  # beaded rain
    "tac_creel_wicker":      ("ek:threads",  dict(), 0.25),
    "tac_marsh_reed":        ("ek:fbm",      dict(octaves=(256, 512, 1024)), 0.20),
    "tac_bird_dog_tick":     ("ek:threads",  dict(), 0.25),                                   # the coat
    "tac_frozen_bank":       ("ek:stars",    dict(), 0.25),                                   # ice glints
    "tac_night_vision":      ("ek:scanline", dict(lines=600.0, triad=1.0, bloom=0.4, roll=0.0, jitter=0.1), 0.20),  # tube raster
    "tac_thermal_white_hot": ("ek:fbm",      dict(octaves=(256, 512, 1024)), 0.20),           # sensor noise
    "tac_ir_flat":           ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),
    "tac_chem_light":        ("ek:stars",    dict(), 0.20),
    "tac_muzzle_flash":      ("ek:stars",    dict(), 0.25),
    "tac_moonlit_snow":      ("ek:stars",    dict(), 0.25),                                   # crystal glints
    "tac_starlight_scope":   ("ek:craters",  dict(n=9000, rmin=0.5, rmax=1.2, rim=0.3), 0.20),
    "tac_tracer_arc":        ("ek:sparks",   dict(), 0.25),
    "tac_red_lens":          ("ek:microtext", dict(), 0.25),                                  # the map under it
    "tac_cold_steel_night":  ("ek:scanline", dict(lines=500.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.2), 0.20),
    "tac_thermal_black_hot": ("ek:fbm",      dict(octaves=(256, 512, 1024)), 0.20),
    "tac_ambush_green":      ("ek:stars",    dict(), 0.20),
    "tac_signal_mirror":     ("ek:scanline", dict(lines=600.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.1), 0.20),
    "tac_blackout_curtain":  ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),
    "tac_frost_breath":      ("ek:stars",    dict(), 0.25),
    # ALL THAT
    "at_disc_rainbow":       ("ek:scanline", dict(lines=700.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.0), 0.25),  # the track pitch
    "at_beige_box":          ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),
    "at_windows_teal":       ("ek:scanline", dict(lines=500.0, triad=3.0, bloom=0.5, roll=0.0, jitter=0.0), 0.25),  # CRT raster
    "at_pipes_screensaver":  ("ek:scanline", dict(lines=450.0, triad=1.0, bloom=0.5, roll=0.0, jitter=0.0), 0.20),  # pipe highlights
    "at_y2k_chrome":         ("ek:stars",    dict(), 0.20),
    "at_dial_up_green":      ("ek:scanline", dict(lines=520.0, triad=1.0, bloom=0.6, roll=0.1, jitter=0.0), 0.25),
    "at_frosted_shell":      ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),
    "at_corrupt_jpeg":       ("ek:pixels",   dict(cell=6.0, levels=6, dither=0.3), 0.30),     # macroblocks
    "at_floppy_black":       ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),
    "at_holo_sticker":       ("ek:stars",    dict(), 0.25),
    "at_crt_blue_screen":    ("ek:microtext", dict(), 0.30),                                  # hex addresses
    "at_mouse_ball_grime":   ("ek:craters",  dict(n=7000, rmin=0.6, rmax=1.6, rim=0.4), 0.25),
    "at_zip_disk":           ("ek:scanline", dict(lines=400.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.1), 0.20),  # label ridges
    "at_iridescent_cd_r":    ("ek:stars",    dict(), 0.20),
    "at_cyber_café":    ("ek:stars",    dict(), 0.20),                                   # blue LEDs
    "at_snowboard_graphic":  ("ek:scanline", dict(lines=500.0, triad=1.0, bloom=0.3, roll=0.3, jitter=0.7), 0.25),  # scratches
    "at_windbreaker_block":  ("ek:sett",     dict(pitch=8.0, twill=1.0), 0.25),               # nylon weave
    "at_dew_green":          ("ek:craters",  dict(n=8000, rmin=0.5, rmax=1.4, rim=0.3), 0.20),  # condensation
    "at_skatepark_concrete": ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),
    "at_grip_tape":          ("ek:stars",    dict(), 0.25),
    "at_big_dog_print":      ("ek:sett",     dict(pitch=9.0, twill=1.0), 0.25),               # the tee
    "at_surf_wax":           ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),
    "at_bmx_dirt":           ("ek:craters",  dict(n=6000, rmin=0.8, rmax=2.0, rim=0.4), 0.25),  # gravel
    "at_anodised_peg":       ("ek:scanline", dict(lines=600.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.6), 0.25),  # scrapes
    "at_neon_wetsuit":       ("ek:craters",  dict(n=8000, rmin=0.5, rmax=1.4, rim=0.3), 0.20),  # neoprene cells
    "at_half_pipe_ply":      ("ek:threads",  dict(), 0.25),                                   # masonite grain
    "at_roller_blade":       ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),
    "at_mountain_topo":      ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),                # paper
    "at_chain_link":         ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),                # galvanising
    "at_bungee_cord":        ("ek:threads",  dict(), 0.25),
    "at_velour_tracksuit":   ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),
    "at_gold_rope":          ("ek:stars",    dict(), 0.25),                                   # link glints
    "at_cross_colour_block": ("ek:sett",     dict(pitch=9.0, twill=2.0), 0.25),               # denim twill
    "at_airbrush_tee":       ("ek:sett",     dict(pitch=9.0, twill=1.0), 0.25),
    "at_bucket_hat":         ("ek:threads",  dict(), 0.20),
    "at_fresh_kicks":        ("ek:threads",  dict(), 0.20),                                   # the mesh
    "at_boombox_chrome":     ("ek:scanline", dict(lines=500.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.0), 0.20),  # brushed
    "at_velour_rose":        ("ek:threads",  dict(), 0.25),
    "at_nameplate_gold":     ("ek:scanline", dict(lines=600.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.1), 0.20),  # polish lines
    "at_denim_baggy":        ("ek:sett",     dict(pitch=9.0, twill=2.0), 0.30),               # the twill
    "at_graffiti_fill":      ("ek:craters",  dict(n=6000, rmin=0.6, rmax=1.6, rim=0.4), 0.20),  # overspray dots
    "at_kangol_felt":        ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),
    "at_grill_chrome":       ("ek:stars",    dict(), 0.25),
    "at_vinyl_crate":        ("ek:threads",  dict(), 0.20),                                   # cardboard fibre
    "at_starter_jacket":     ("ek:sett",     dict(pitch=8.0, twill=1.0), 0.25),               # satin weave
    "at_flannel_red":        ("ek:threads",  dict(), 0.30),                                   # brushed cotton
    "at_flannel_forest":     ("ek:threads",  dict(), 0.30),
    "at_thrift_cardigan":    ("ek:threads",  dict(), 0.30),                                   # wool
    "at_seattle_rain":       ("ek:craters",  dict(n=8000, rmin=0.5, rmax=1.4, rim=0.3), 0.25),  # droplets
    "at_moss_sidewalk":      ("ek:stars",    dict(), 0.20),
    "at_doc_marten":         ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),                # leather grain
    "at_distressed_denim":   ("ek:sett",     dict(pitch=9.0, twill=2.0), 0.30),               # twill under the wear
    "at_band_tee_crack":     ("ek:sett",     dict(pitch=9.0, twill=1.0), 0.25),               # the tee
    "at_corduroy_olive":     ("ek:threads",  dict(), 0.25),                                   # pile
    "at_overcast_grey":      ("ek:fbm",      dict(octaves=(256, 512, 1024)), 0.20),
    "at_basement_amp":       ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),
    "at_combat_boot_steel":  ("ek:scanline", dict(lines=500.0, triad=1.0, bloom=0.3, roll=0.2, jitter=0.6), 0.25),  # scuffs
    "at_sharpie_ink":        ("ek:threads",  dict(), 0.20),                                   # skin / canvas
    "at_cassette_tape":      ("ek:fbm",      dict(octaves=(512, 1024)), 0.15),
    "at_chipped_nail":       ("ek:stars",    dict(), 0.20),                                   # gloss glints
}

DESIGNS = {"tac_": TACTICAL, "at_": ALL_THAT}
try:
    from engine.paint_v2.era_designs2_2026 import RAD, CBP, FO, DETAIL2, FINE2
    DESIGNS.update({"rad_": RAD, "cbp_": CBP, "fo_": FO})
    DETAIL.update(DETAIL2)
    FINE.update(FINE2)
except ImportError:  # part 2 not present yet: those shelves fall back to their stacks
    pass


def design_for(fid):
    for prefix, table in DESIGNS.items():
        if fid.startswith(prefix):
            return table.get(fid)
    return None


def check(prefix, table, recipes):
    """recipes = the shelf's recipe dict (needs 'lane'). Raises on any hard rule."""
    ids = [f for f in recipes if f.startswith(prefix)]
    missing = sorted(set(ids) - set(table))
    if missing:
        raise ValueError("%s finishes with no construction: %s" % (prefix, missing))
    pairs = {}
    for fid, (form, params, _k) in table.items():
        pairs.setdefault((form, tuple(sorted((k, str(v)) for k, v in params.items()))), []).append(fid)
    same = {k: v for k, v in pairs.items() if len(v) > 1}
    if same:
        raise ValueError("identical construction+params: " + "; ".join(", ".join(v) for v in same.values()))
    by_lane = {}
    for fid in ids:
        by_lane.setdefault(recipes[fid].get("lane"), []).append(table[fid][0])
    for lane, forms in by_lane.items():
        if len(set(forms)) != len(forms):
            d = sorted({x for x in forms if forms.count(x) > 1})
            raise ValueError("%s lane %r reuses constructions: %s" % (prefix, lane, d))
    forms_only = [f for f, _p, _k in table.values()]
    return {"finishes": len(table), "distinct": len(set(forms_only)),
            "cross_lane_reuse": len(forms_only) - len(set(forms_only)),
            "fine_missing": sorted(set(table) - set(FINE))}
