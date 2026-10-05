# -*- coding: utf-8 -*-
"""ERA SHELVES, part 2 — BAD & RAD (rad_), CYBERPUNK (cbp_), FAR OUT (fo_).
Same contract as era_designs_2026 (construction per finish, chosen from what it
IS; no reuse within a lane; FINE nested construction per finish). Merged into
era_designs_2026.DESIGNS / DETAIL / FINE at import.
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════
# BAD & RAD (rad_) — lanes: arcade / grid / memphis / radical
# ═══════════════════════════════════════════════════════════════════════════
RAD = {
    # arcade
    "rad_phosphor_green":    ("ek:scanline",   dict(lines=300.0, triad=1.0, bloom=1.2, roll=0.15, jitter=0.1), "grain"),  # P1 raster with persistence
    "rad_amber_terminal":    ("ek:microtext",  dict(), "grain"),                                   # 80 columns of amber
    "rad_sprite_sheet":      ("ek:pixels",     dict(cell=20.0, levels=4, dither=0.0), "grain"),    # 16x16, four colours
    "rad_dot_matrix":        ("ek:knurl",      dict(pitch=8.0, angle=0.0, wobble=0.0), "grain"),   # the grid you could see
    "rad_cabinet_side_art":  ("ek:splatter",   dict(blobs=900, rmax=26.0, drips=0.3, spatter=1.0), "grain"),  # 300 left 82% void  # screen-printed, sun-faded
    "rad_marquee_bulb":      ("ek:craters",    dict(n=300, rmin=10.0, rmax=16.0, rim=0.9), "flake"),  # chase bulbs
    "rad_quarter_slot":      ("ek:bands",      dict(n=200, shear=0.0, turb=0.02), "flake"),        # brushed steel
    "rad_attract_mode":      ("ek:glitch",     dict(slices=40, shift=40.0, tear=0.3, block=0.3), "grain"),  # the demo loop
    "rad_trackball_wear":    ("ek:fbm",        dict(octaves=(48, 96, 192, 384)), "grain"),         # polished haze
    "rad_vector_glow":       ("ek:filaments",  dict(n=60, length=500, width=2.5, wander=0.02), "spark"),  # the beam draws the line
    "rad_bezel_black":       ("ek:percolate",  dict(cells=220, p=0.5), "grain"),                   # textured surround
    "rad_insert_coin":       ("ek:sett",       dict(pitch=12.0, twill=1.0), "grain"),              # character cells
    "rad_high_score":        ("ek:bricks",     dict(rows=44, cols=4, bind=0.06), "grain"),         # the table (30/3: SCALE 0.199)
    "rad_joystick_ball":     ("ek:facets",     dict(stones=180, table=0.5), "flake"),              # cracked at the shaft
    "rad_screen_burn":       ("ek:holo",       dict(rings=60.0, orders=1.0, warp=80.0, sharp=1.0), "grain"),  # etched phosphor
    # grid
    "rad_vector_horizon":    ("ek:wireframe",  dict(rows=60, persp=1.7, horizon=0.42, glow=1.0, width=1.4), "spark"),  # the grid to a vanishing point (30 rows: SCALE 0.167)
    "rad_sunset_bars":       ("ek:bands",      dict(n=26, shear=0.0, turb=0.0), "grain"),          # a sun in slices (arcade quarter: 200)
    "rad_chrome_type":       ("metaball",      dict(blobs=300, radius=0.035), "flake"),            # extruded letters
    "rad_vhs_tracking":      ("ek:glitch",     dict(slices=20, shift=60.0, tear=0.6, block=0.1), "grain"),  # head switching (arcade attract: 40/40)
    "rad_laserdisc_rainbow": ("ek:holo",       dict(rings=300.0, orders=3.0, warp=30.0, sharp=1.4), "flake"),  # (arcade burn: 60/1)
    "rad_outrun_stripe":     ("ek:kh_braid",   dict(layers=12, shear=2.0), "grain"),               # the side stripe
    "rad_miami_pastel":      ("ek:craters",    dict(n=7000, rmin=0.6, rmax=1.6, rim=0.3), "grain"),  # stucco (arcade marquee: 300/10-16)
    "rad_neon_tube":         ("ek:squiggle",   dict(n=420, length=320.0, amp=34.0, confetti=0.0, width=7.0), "spark"),  # 120 tubes left 92% void  # bent glass
    "rad_grid_floor":        ("ek:sett",       dict(pitch=60.0, twill=1.0), "grain"),              # the floor of every video (arcade coin: 12)
    "rad_static_snow":       ("ek:fbm",        dict(octaves=(512, 1024)), "grain"),                # channel 3 (arcade trackball: 48-384)
    "rad_digital_sunrise":   ("moire_beat",    dict(a=30.0, b=33.0, angle=0.0), "grain"),          # visible banding
    "rad_cassette_shell":    ("ek:knurl",      dict(pitch=12.0, angle=0.0, wobble=0.2), "grain"),  # smoked polystyrene (arcade dots: 8 exact)
    "rad_boombox_grille":    ("ek:honeycomb",  dict(), "grain"),                                   # perforated steel
    "rad_synth_key":         ("ek:bricks",     dict(rows=6, cols=40, bind=0.04), "grain"),         # the keys (arcade score: 30/3)
    "rad_laser_grid":        ("ek:filaments",  dict(n=40, length=600, width=3.0, wander=0.0), "spark"),  # beams through haze (arcade vector: 60/500)
    # memphis
    "rad_milano_squiggle":   ("ek:squiggle",   dict(n=400, length=150.0, amp=25.0, confetti=0.3, width=8.0), "grain"),  # the squiggle (grid tube: 120 long)
    "rad_bacterio_print":    ("ek:curl",       dict(scale=40, steps=12), "grain"),                 # the scribble laminate
    "rad_jazz_cup":          ("ek:kh_braid",   dict(layers=8, shear=1.4), "grain"),                # teal strokes (grid stripe: 12/2.0)
    "rad_terrazzo_chip":     ("ek:facets",     dict(stones=600, table=0.3), "flake"),              # marble chips (arcade ball: 180)
    "rad_pastel_mint":       ("ek:sett",       dict(pitch=70.0, twill=1.0), "grain"),              # tile with grout (grid floor: 60)
    "rad_peach_fuzz":        ("ek:shag",       dict(strands=9000, length=16, splay=1.5), "fibre"), # flocking
    "rad_confetti_laminate": ("ek:discs",      dict(n=800, radius=12.0), "grain"),                 # scattered rectangles
    "rad_grid_tile":         ("ek:pixels",     dict(cell=40.0, levels=3, dither=0.0), "grain"),    # small square tiles (arcade sprite: 20/4)
    "rad_zigzag_runner":     ("ek:bands",      dict(n=30, shear=1.2, turb=0.0), "fibre"),          # flatweave zigzag (grid sun: 26 straight)
    "rad_neon_wire_chair":   ("ek:knurl",      dict(pitch=40.0, angle=0.0, wobble=0.0), "ridge"),  # bent rod (grid shell: 12)
    "rad_speckle_wall":      ("ek:stars",      dict(), "grain"),                                   # flecked wallpaper
    "rad_glass_block":       ("ek:polygons",   dict(cells=30, width=4.0), "flake"),                # fluted glass brick (12 cells: SCALE 0.06)
    "rad_lacquer_cabinet":   ("ek:holo",       dict(rings=10.0, orders=1.0, warp=240.0, sharp=0.5), "flake"),  # polish swirl in high-gloss black (fbm read plain; grid laserdisc 300/3, arcade burn 60/1)
    "rad_sponge_paint":      ("ek:resist",     dict(), "grain"),                                   # rag-rolled
    "rad_anodised_trim":     ("ek:scanline",   dict(lines=120.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.0), "flake"),  # extrusion lines (arcade phosphor: 300 bloom)
    # radical
    "rad_splatter_tee":      ("ek:splatter",   dict(blobs=600, rmax=22.0, drips=0.5, spatter=1.2), "grain"),  # thrown from a brush (arcade cabinet: 300/44)
    "rad_hair_metal":        ("ek:threads",    dict(), "fibre"),                                   # backcombed
    "rad_neon_spandex":      ("ek:knurl",      dict(pitch=7.0, angle=0.0, wobble=0.1), "fibre"),  # lycra knit (ikat left 57% void; grid shell 12, arcade dots 8, memphis chair 40)                                   # stretched dye
    "rad_skate_deck":        ("ek:discs",      dict(n=9000, radius=1.5), "grain"),                 # grip tape (memphis confetti: 800/12)
    "rad_tiger_stripe":      ("ek:rt_fingers", dict(n=36), "fibre"),                               # tapering airbrush stripes
    "rad_aerobics_gym":      ("moire_beat",    dict(a=90.0, b=96.0, angle=1.57), "fibre"),         # striped leotard (grid sunrise: 30/33)
    "rad_airbrush_portrait": ("ek:curl",       dict(scale=160, steps=30), "grain"),                # soft edges (memphis bacterio: 40/12)
    "rad_rad_splatter_deck": ("ek:eden",       dict(seeds=120, steps=26), "flake"),                # splatter under clear
    "rad_zebra_wrap":        ("damascus",      dict(layers=50, folds=2, twist=1.5, warp=0.3), "grain"),  # stripes that never repeat
    "rad_neon_grip":         ("ek:craters",    dict(n=4000, rmin=2.0, rmax=5.0, rim=0.6), "ridge"),  # moulded rubber nubs (arcade marquee 300 big, grid stucco 7000 tiny)
    "rad_slap_bracelet":     ("ek:scales",     dict(cell=18.0, keel=0.3), "flake"),                # fabric sleeve over spring steel
    "rad_puffy_paint":       ("metaball",      dict(blobs=900, radius=0.015), "grain"),            # domed squeeze lines (grid chrome type: 300/0.035)
    "rad_trapper_sticker":   ("ek:tooled",     dict(cell=60.0, petals=5, stamp=0.9, bevel=0.3), "flake"),  # puffy stickers layered
    "rad_hypercolour":       ("ek:camo",       dict(patches=4, blob=170.0, roughness=1.2), "grain"),  # where you touched it
    "rad_big_hair_chrome":   ("ek:sparks",     dict(), "spark"),                                   # lightning
}

# ═══════════════════════════════════════════════════════════════════════════
# CYBERPUNK (cbp_) — lanes: street / chrome / netrun / sprawl
# ═══════════════════════════════════════════════════════════════════════════
CBP = {
    # street
    "cbp_wet_asphalt":       ("ek:craters",    dict(n=6000, rmin=0.8, rmax=2.2, rim=0.5), "grain"),  # aggregate under the film
    "cbp_sodium_vapour":     ("ek:holo",       dict(rings=14.0, orders=1.0, warp=200.0, sharp=0.6), "grain"),  # one wavelength: its own interference swirl (fbm read plain; holo_advert moved to moire_beat)
    "cbp_kanji_signage":     ("ek:microtext",  dict(), "grain"),                                   # stacked signs
    "cbp_holo_advert":       ("moire_beat",    dict(a=200.0, b=214.0, angle=0.1), "flake"),         # the projection: interference of two near frequencies (netrun quantum 140/150)
    "cbp_night_market":      ("ek:stars",      dict(), "spark"),                                   # strung bulbs
    "cbp_acid_rain":         ("ek:rt_fingers", dict(n=50), "grain"),                               # pitting runs
    "cbp_taxi_panel":        ("ek:spall",      dict(cells=50, lift=0.6), "grain"),                 # repaint over repaint
    "cbp_steam_grate":       ("ek:knurl",      dict(pitch=26.0, angle=0.0, wobble=0.0), "ridge"),  # cast iron grate
    "cbp_puddle_neon":       ("ek:curl",       dict(scale=120, steps=24), "flake"),                # the reflection
    "cbp_shutter_tag":       ("ek:bands",      dict(n=40, shear=0.0, turb=0.02), "grain"),         # rolling shutter slats
    "cbp_rain_screen":       ("ek:filaments",  dict(n=300, length=300, width=1.6, wander=0.02), "flake"),  # drops racing
    "cbp_sodium_fog":        ("caustics",      dict(scale=10.0, octaves=3), "grain"),              # particulate in the beam
    "cbp_vending_glow":      ("ek:pixels",     dict(cell=30.0, levels=5, dither=0.1), "flake"),    # the lit machine
    "cbp_neon_tube":         ("ek:squiggle",   dict(n=440, length=300.0, amp=32.0, confetti=0.0, width=7.0), "spark"),  # 140 left 90% void  # bent glass
    "cbp_overpass_sodium":   ("ek:percolate",  dict(cells=90, p=0.5), "grain"),                    # stained concrete
    # chrome
    "cbp_subdermal_plate":   ("ek:polygons",   dict(cells=40, width=3.0), "flake"),                # armour plates (22 cells: SCALE 0.10)
    "cbp_neural_port":       ("ek:craters",    dict(n=200, rmin=8.0, rmax=14.0, rim=1.0), "flake"),  # sockets (street asphalt: 6000 tiny)
    "cbp_ceramic_limb":      ("ek:anneal_crack", dict(cells=60, width=1.6), "grain"),              # glaze crazing
    "cbp_gunmetal_aug":      ("ek:bands",      dict(n=90, shear=0.0, turb=0.0), "flake"),          # machined grooves (street shutter: 40)
    "cbp_wetware_membrane":  ("gray_scott",    dict(feed=0.030, kill=0.062), "grain"),             # cultured tissue
    "cbp_gold_contact":      ("ek:sett",       dict(pitch=20.0, twill=1.0), "flake"),              # pin grid
    "cbp_carbon_limb":       ("ek:knurl",      dict(pitch=14.0, angle=0.785, wobble=0.0), "flake"),  # twill under clear (street grate: 26 orthogonal)
    "cbp_optic_implant":     ("ek:holo",       dict(rings=40.0, orders=2.0, warp=20.0, sharp=1.6), "flake"),  # (street advert: 200/3)
    "cbp_chrome_spine":      ("ek:scales",     dict(cell=28.0, keel=0.6), "flake"),                # segments
    "cbp_skin_weave":        ("ek:threads",    dict(), "grain"),                                   # mesh under skin
    "cbp_ripperdoc_steel":   ("ek:spall",      dict(cells=80, lift=0.9), "flake"),                 # back-alley work (street taxi: 50/0.6)
    "cbp_porcelain_face":    ("ek:fbm",        dict(octaves=(512, 1024)), "flake"),                # perfect shell (street sodium: 32-256)
    "cbp_servo_housing":     ("ek:wrinkle",    dict(k=1.8, steps=22), "grain"),                    # moulded boot
    "cbp_titanium_rib":      ("ek:honeycomb",  dict(), "flake"),                                   # printed lattice
    "cbp_mirror_shades":     ("ek:facets",     dict(stones=140, table=0.6), "flake"),              # worn indoors
    # netrun
    "cbp_ice_wall":          ("ek:facets",     dict(stones=160, table=0.5), "flake"),              # ICE as a surface (chrome shades: 140/0.6)
    "cbp_datastream":        ("ek:bands",      dict(n=160, shear=0.0, turb=0.0), "spark"),         # falling columns (chrome aug 90, street shutter 40, sprawl hazard 14)
    "cbp_corrupt_memory":    ("ek:glitch",     dict(slices=44, shift=40.0, tear=0.4, block=0.4), "grain"),  # failed checksum
    "cbp_black_ice":         ("frost_fern",    dict(seeds=24, branch=0.5, drift=0.3), "spark"),    # ice ferns
    "cbp_trace_route":       ("ek:squiggle",   dict(n=800, length=200.0, amp=14.0, confetti=0.3, width=3.5), "spark"),  # 200 left 94% void  # one hop at a time (street tube: 140/380 wide)
    "cbp_ghost_protocol":    ("ek:curl",       dict(scale=220, steps=44), "grain"),                # there and not there (street puddle: 120/24)
    "cbp_quantum_violet":    ("moire_beat",    dict(a=140.0, b=150.0, angle=0.3), "flake"),        # every value until observed
    "cbp_daemon_red":        ("ek:scanline",   dict(lines=180.0, triad=1.0, bloom=1.0, roll=0.3, jitter=0.2), "spark"),  # a process with no owner
    "cbp_packet_loss":       ("ek:pixels",     dict(cell=16.0, levels=6, dither=0.4), "grain"),    # codec blocks (street vending: 30/5)
    "cbp_firewall_grid":     ("ek:wireframe",  dict(rows=34, persp=1.0, horizon=0.5, glow=1.0, width=1.8), "spark"),  # the boundary as lattice
    "cbp_neural_static":     ("ek:fbm",        dict(octaves=(256, 512, 1024)), "grain"),           # bad connection (chrome porcelain: 512-1024)
    "cbp_deep_archive":      ("ek:bricks",     dict(rows=30, cols=8, bind=0.05), "grain"),         # racks in cold storage
    "cbp_worm_trail":        ("ek:eden",       dict(seeds=140, steps=40), "grain"),  # 30 seeds left 76% void                 # propagation mapped
    "cbp_encryption_lattice": ("quasicrystal", dict(waves=7, freq=240.0), "flake"),                # the cipher as a crystal
    "cbp_root_access":       ("ek:topo",       dict(lines=90.0, width=2.4), "spark"),              # everything downstream
    # sprawl
    "cbp_corp_grey":         ("ek:bricks",     dict(rows=14, cols=5, bind=0.10), "grain"),         # cladding panels (netrun archive: 30/8)
    "cbp_rad_warning":       ("ek:tooled",     dict(cell=140.0, petals=3, stamp=0.9, bevel=0.3), "grain"),  # the trefoil, stencilled
    "cbp_scav_rust":         ("ek:percolate",  dict(cells=60, p=0.55), "grain"),                   # what the building did (street overpass: 90/0.5)
    "cbp_duct_grime":        ("ek:scanline",   dict(lines=70.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.1), "grain"),  # trunking ribs (netrun daemon: 180 bloom)
    "cbp_concrete_rot":      ("ek:anneal_crack", dict(cells=64, width=2.4), "crackle"),            # spalling over rebar (36 cells: SCALE 0.16; chrome ceramic: 60/1.6)
    "cbp_biohazard_bloom":   ("gray_scott",    dict(feed=0.026, kill=0.058), "grain"),             # something growing (chrome wetware: spots regime)
    "cbp_oil_slick_puddle":  ("moire_beat",    dict(a=150.0, b=160.0, angle=0.8), "flake"),        # one wavelength thick (netrun quantum: 140/150)
    "cbp_rebar_skeleton":    ("ek:sett",       dict(pitch=60.0, twill=1.0), "ridge"),              # the grid never poured (chrome contact: 20)
    "cbp_ash_fall":          ("ek:dunes",      dict(n=34, crest=1.4), "grain"),                    # settled particulate
    "cbp_corp_glass":        ("ek:polygons",   dict(cells=26, width=2.0), "flake"),                # curtain wall (8 cells: SCALE 0.11; chrome subdermal: 40)
    "cbp_hazard_stripe":     ("ek:bands",      dict(n=14, shear=1.0, turb=0.0), "grain"),          # diagonal yellow and black (street shutter, chrome aug: straight)
    "cbp_sewer_bloom":       ("caustics",      dict(scale=6.0, octaves=4), "flake"),               # runoff, iridescent (street fog: 10/3)
    "cbp_scrap_weld":        ("imbricate",     dict(rows=46, overlap=0.45), "ridge"),              # stick-welded crescents
    "cbp_static_screen":     ("ek:glitch",     dict(slices=26, shift=70.0, tear=0.7, block=0.2), "grain"),  # the same fault (netrun corrupt: 44/40)
    "cbp_cracked_solar":     ("shatter",       dict(impacts=6, radials=30), "flake"),              # a third shattered
}

# ═══════════════════════════════════════════════════════════════════════════
# FAR OUT (fo_) — lanes: disco / shag / outlaw / van
# ═══════════════════════════════════════════════════════════════════════════
FO = {
    # disco
    "fo_mirror_ball":        ("ek:pixels",     dict(cell=22.0, levels=4, dither=0.1), "flake"),    # a thousand glass tiles
    "fo_lighted_floor":      ("ek:sett",       dict(pitch=90.0, twill=1.0), "flake"),              # perspex squares
    "fo_lurex_gold":         ("ek:knurl",      dict(pitch=10.0, angle=0.0, wobble=0.1), "flake"),  # metallic thread in the knit
    "fo_lurex_rose":         ("ek:threads",    dict(), "flake"),                                   # the same thread, body-con
    "fo_roller_rink":        ("ek:scanline",   dict(lines=40.0, triad=1.0, bloom=0.4, roll=0.0, jitter=0.3), "grain"),  # maple boards, wheel marks
    "fo_studio_gold":        ("ek:guilloche",  dict(), "flake"),                                   # gilt
    "fo_hustle_teal":        ("ek:ikat",       dict(), "fibre"),                                   # polyester
    "fo_glitter_ball_rain":  ("ek:discs",      dict(n=4000, radius=3.0), "flake"),                 # the dots the ball throws
    "fo_sequin_sheet":       ("imbricate",     dict(rows=52, overlap=0.5), "flake"),               # paillettes in courses
    "fo_boogie_neon":        ("ek:squiggle",   dict(n=400, length=320.0, amp=38.0, confetti=0.0, width=7.0), "spark"),  # 130 left 62% void  # bent tube
    "fo_velvet_rope":        ("ek:shag",       dict(strands=9000, length=18, splay=1.1), "fibre"), # crushed velvet
    "fo_platform_patent":    ("ek:wrinkle",    dict(k=1.6, steps=18), "flake"),                    # patent creases
    "fo_vinyl_groove":       ("moire_beat",    dict(a=300.0, b=310.0, angle=0.0), "flake"),        # the groove pitch
    "fo_discotheque_haze":   ("ek:curl",       dict(scale=150, steps=28), "grain"),                # smoke holding the beams
    "fo_saturday_chrome":    ("ek:facets",     dict(stones=200, table=0.55), "flake"),             # everything else in that room
    # shag
    "fo_shag_avocado":       ("ek:shag",       dict(strands=5200, length=46, splay=0.9), "fibre"), # two inches of pile (disco rope: 9000/18)
    "fo_shag_harvest":       ("ek:scales",     dict(cell=7.0, keel=0.1), "fibre"),                # pile tufts (outlaw snakeskin: 20/0.5)
    "fo_conversation_pit":   ("ek:wrinkle",    dict(k=2.2, steps=26), "fibre"),                    # burnt orange upholstery (disco patent: 1.6/18)
    "fo_wood_panel":         ("ek:topo",       dict(lines=130.0, width=2.4), "grain"),             # photo-printed walnut
    "fo_macrame_hang":       ("ek:kh_braid",   dict(layers=24, shear=2.0), "fibre"),               # jute knots
    "fo_linoleum_teal":      ("ek:tooled",     dict(cell=100.0, petals=4, stamp=0.7, bevel=0.4), "grain"),  # the repeat
    "fo_popcorn_ceiling":    ("ek:splatter",   dict(blobs=4000, rmax=4.0, drips=0.0, spatter=1.0), "grain"),  # sprayed texture
    "fo_fondue_copper":      ("ek:craters",    dict(n=3000, rmin=3.0, rmax=7.0, rim=0.6), "flake"),  # hammered
    "fo_corduroy_brown":     ("ek:bands",      dict(n=50, shear=0.1, turb=0.1), "fibre"),          # wide wale
    "fo_tab_curtain":        ("ek:resist",     dict(), "fibre"),                                   # barkcloth bold repeat
    "fo_rattan_weave":       ("ek:sett",       dict(pitch=30.0, twill=1.0), "fibre"),              # the peacock chair (disco floor: 90)
    "fo_terrazzo_kitchen":   ("ek:facets",     dict(stones=700, table=0.3), "grain"),              # chips of everything (disco chrome: 200/0.55)
    "fo_lava_lamp":          ("metaball",      dict(blobs=40, radius=0.06), "grain"),              # wax rising
    "fo_smoked_glass":       ("ek:polygons",   dict(cells=24, width=1.5), "flake"),                # bronze-tinted PANES (fbm read plain; outlaw turquoise 46/4)
    "fo_formica_boomerang":  ("ek:squiggle",   dict(n=500, length=40.0, amp=12.0, confetti=0.0, width=4.0), "grain"),  # the little shapes (disco neon: 130 long)
    # outlaw
    "fo_tooled_saddle":      ("ek:tooled",     dict(cell=110.0, petals=6, stamp=0.6, bevel=1.0), "grain"),  # Sheridan floral (shag lino: 100/4)
    "fo_basket_stamp":       ("ek:knurl",      dict(pitch=20.0, angle=0.785, wobble=0.0), "grain"),  # basketweave stamp (disco lurex: 10 orthogonal)
    "fo_turquoise_silver":   ("ek:polygons",   dict(cells=46, width=4.0), "flake"),                # matrix in the stone (30 cells: SCALE 0.12)
    "fo_concho_row":         ("ek:discs",      dict(n=520, radius=22.0), "flake"),                 # hammered silver discs (300/30: SCALE 0.14; disco glitter: 4000/3)
    "fo_rhinestone_suit":    ("ek:stars",      dict(), "flake"),                                   # more stones than fabric
    "fo_raw_denim":          ("ek:sett",       dict(pitch=12.0, twill=3.0), "fibre"),              # selvedge twill (disco floor 90 plain, shag rattan 30 plain)
    "fo_rodeo_dust":         ("ek:dunes",      dict(n=30, crest=2.0), "grain"),                    # arena dirt in the light
    "fo_black_hat":          ("ek:fbm",        dict(octaves=(256, 512, 1024)), "fibre"),           # beaver felt (shag smoked: 12-48)
    "fo_snakeskin_boot":     ("ek:scales",     dict(cell=20.0, keel=0.5), "flake"),                # belly cut
    "fo_mesa_sunset":        ("ek:bands",      dict(n=30, shear=0.2, turb=0.3), "grain"),          # sandstone courses (shag corduroy: 50)
    "fo_barbed_wire":        ("ek:filaments",  dict(n=130, length=600, width=3.0, wander=0.0), "spark"),  # 40 strands left 51% void  # four-point wire
    "fo_longhorn_hide":      ("ek:camo",       dict(patches=5, blob=160.0, roughness=1.6), "fibre"),  # brindle
    "fo_silver_buckle":      ("ek:facets",     dict(stones=90, table=0.7), "flake"),               # engraved facets (disco 200, shag 700, van 3000)
    "fo_prairie_denim":      ("ek:moire",      dict(), "fibre"),                                   # chambray sheen
    "fo_outlaw_chrome":      ("ek:spall",      dict(cells=60, lift=0.7), "flake"),                 # exhaust, wiped down
    # van
    "fo_airbrush_mural":     ("ek:curl",       dict(scale=90, steps=18), "grain"),                 # a wizard, a wolf (disco haze: 150/28)
    "fo_metalflake_blue":    ("ek:facets",     dict(stones=3000, table=0.2), "flake"),             # big flake under clear (disco chrome 200, shag terrazzo 700)
    "fo_metalflake_red":     ("ek:craters",    dict(n=9000, rmin=0.6, rmax=1.4, rim=0.4), "flake"),  # flake showing every flaw (shag fondue: 3000/3-7)
    "fo_candy_apple":        ("ek:holo",       dict(rings=400.0, orders=1.0, warp=30.0, sharp=1.0), "flake"),  # depth you can fall into
    "fo_pinstripe_kit":      ("ridge_flow",    dict(ridges=70, cores=2), "spark"),                 # pulled with a dagger brush
    "fo_sunset_stripe":      ("moire_beat",    dict(a=20.0, b=22.0, angle=0.0), "grain"),          # the graduated stripe (disco groove: 300/310)
    "fo_eagle_gold":         ("ek:intaglio",   dict(), "flake"),                                   # gold leaf, outlined
    "fo_porthole_chrome":    ("ek:discs",      dict(n=80, radius=60.0), "flake"),                  # bubble window rings (outlaw concho: 300/30)
    "fo_shag_interior":      ("ek:shag",       dict(strands=7000, length=30, splay=1.0), "fibre"), # carpeted, all of it (disco 9000/18, shag 5200/46)
    "fo_cb_static":          ("ek:scanline",   dict(lines=320.0, triad=1.0, bloom=0.6, roll=0.2, jitter=0.6), "grain"),  # forty channels of nothing (disco rink: 40)
    "fo_desert_scene":       ("ek:dunes",      dict(n=18, crest=2.6), "grain"),                    # airbrushed dunes (outlaw rodeo: 30/2.0)
    "fo_flame_job":          ("ek:kh_braid",   dict(layers=14, shear=3.4), "spark"),               # licks laid out in tape (shag macrame: 24/2.0)
    "fo_ghost_mural":        ("ek:camo",       dict(patches=3, blob=220.0, roughness=0.8), "flake"),  # pearl on pearl, soft (outlaw hide: 5/160 rough)
    "fo_wheel_well_rust":    ("ek:percolate",  dict(cells=70, p=0.52), "grain"),                   # where the mural never reached
    "fo_tailgate_sunburst":  ("ek:bands",      dict(n=24, shear=2.5, turb=0.0), "spark"),          # rays (shag corduroy 50, outlaw mesa 30: straight)
}

DETAIL2 = {
    "rad_sunset_bars": 0.6, "rad_vector_horizon": 0.6, "rad_grid_floor": 0.6, "rad_chrome_type": 0.6, "rad_pastel_mint": 0.6,
    "rad_glass_block": 0.7, "rad_lacquer_cabinet": 0.6, "rad_synth_key": 0.55, "rad_zebra_wrap": 0.5, "rad_hypercolour": 0.55,
    "rad_cassette_shell": 0.7, "rad_vector_horizon": 0.7, "rad_high_score": 0.6,
    "cbp_sodium_vapour": 0.6, "cbp_subdermal_plate": 0.55, "cbp_corp_grey": 0.55, "cbp_corp_glass": 0.6, "cbp_hazard_stripe": 0.6,
    "cbp_neural_port": 0.55, "cbp_rebar_skeleton": 0.55, "cbp_rad_warning": 0.55, "cbp_firewall_grid": 0.55,
    "cbp_biohazard_bloom": 0.85, "cbp_carbon_limb": 0.7, "cbp_concrete_rot": 0.6,  # SCALE 0.05 / 0.15 / 0.16
    "fo_lighted_floor": 0.6, "fo_lava_lamp": 0.6, "fo_smoked_glass": 0.6, "fo_concho_row": 0.55, "fo_porthole_chrome": 0.6,
    "fo_sunset_stripe": 0.6, "fo_tailgate_sunburst": 0.6, "fo_mesa_sunset": 0.5, "fo_desert_scene": 0.55,
    "fo_vinyl_groove": 0.65, "fo_concho_row": 0.6, "fo_turquoise_silver": 0.6,  # SCALE 0.13 / 0.14 / 0.12
}

_T = ("ek:threads", dict())
_S = ("ek:stars", dict())
_G = ("ek:fbm", dict(octaves=(512, 1024)))
_C = ("ek:craters", dict(n=7000, rmin=0.6, rmax=1.6, rim=0.4))
_L = ("ek:scanline", dict(lines=520.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.2))
_W = ("ek:sett", dict(pitch=9.0, twill=1.0))
FINE2 = {
    # BAD & RAD
    "rad_phosphor_green": _S + (0.25,), "rad_amber_terminal": _L + (0.25,), "rad_sprite_sheet": _L + (0.25,),
    "rad_dot_matrix": _G + (0.15,), "rad_cabinet_side_art": _C + (0.25,), "rad_marquee_bulb": _S + (0.25,),
    "rad_quarter_slot": _C + (0.20,), "rad_attract_mode": _L + (0.25,), "rad_trackball_wear": _L + (0.20,),
    "rad_vector_glow": _S + (0.25,), "rad_bezel_black": _G + (0.15,), "rad_insert_coin": _L + (0.25,),
    "rad_high_score": _L + (0.25,), "rad_joystick_ball": _G + (0.20,), "rad_screen_burn": _L + (0.30,),
    "rad_vector_horizon": _S + (0.25,), "rad_sunset_bars": _L + (0.25,), "rad_chrome_type": _S + (0.25,),
    "rad_vhs_tracking": _L + (0.30,), "rad_laserdisc_rainbow": _L + (0.25,), "rad_outrun_stripe": _S + (0.20,),
    "rad_miami_pastel": _G + (0.20,), "rad_neon_tube": _S + (0.20,), "rad_grid_floor": _L + (0.20,),
    "rad_static_snow": _L + (0.30,), "rad_digital_sunrise": _G + (0.20,), "rad_cassette_shell": _G + (0.15,),
    "rad_boombox_grille": _G + (0.15,), "rad_synth_key": _G + (0.15,), "rad_laser_grid": _S + (0.25,),
    "rad_milano_squiggle": _C + (0.20,), "rad_bacterio_print": _G + (0.15,), "rad_jazz_cup": _C + (0.20,),
    "rad_terrazzo_chip": _S + (0.25,), "rad_pastel_mint": _C + (0.25,), "rad_peach_fuzz": _G + (0.15,),
    "rad_confetti_laminate": _G + (0.15,), "rad_grid_tile": _C + (0.20,), "rad_zigzag_runner": _T + (0.30,),
    "rad_neon_wire_chair": _G + (0.15,), "rad_speckle_wall": _G + (0.20,), "rad_glass_block": _L + (0.30,),
    "rad_lacquer_cabinet": _S + (0.15,), "rad_sponge_paint": _C + (0.25,), "rad_anodised_trim": _G + (0.15,),
    "rad_splatter_tee": _W + (0.25,), "rad_hair_metal": _S + (0.25,), "rad_neon_spandex": _W + (0.30,),
    "rad_skate_deck": _G + (0.15,), "rad_tiger_stripe": _G + (0.20,), "rad_aerobics_gym": _W + (0.25,),
    "rad_airbrush_portrait": _W + (0.25,), "rad_rad_splatter_deck": _S + (0.20,), "rad_zebra_wrap": _W + (0.25,),
    "rad_neon_grip": _C + (0.25,), "rad_slap_bracelet": _W + (0.25,), "rad_puffy_paint": _W + (0.25,),
    "rad_trapper_sticker": _C + (0.20,), "rad_hypercolour": _W + (0.30,), "rad_big_hair_chrome": _S + (0.25,),
    # CYBERPUNK
    "cbp_wet_asphalt": _G + (0.20,), "cbp_sodium_vapour": _C + (0.20,), "cbp_kanji_signage": _S + (0.25,),
    "cbp_holo_advert": _L + (0.30,), "cbp_night_market": _T + (0.20,), "cbp_acid_rain": _C + (0.25,),
    "cbp_taxi_panel": _L + (0.25,), "cbp_steam_grate": _C + (0.20,), "cbp_puddle_neon": _S + (0.25,),
    "cbp_shutter_tag": _C + (0.20,), "cbp_rain_screen": _S + (0.25,), "cbp_sodium_fog": _S + (0.20,),
    "cbp_vending_glow": _L + (0.30,), "cbp_neon_tube": _S + (0.20,), "cbp_overpass_sodium": _C + (0.25,),
    "cbp_subdermal_plate": _L + (0.25,), "cbp_neural_port": _L + (0.25,), "cbp_ceramic_limb": _C + (0.20,),
    "cbp_gunmetal_aug": _C + (0.20,), "cbp_wetware_membrane": _C + (0.25,), "cbp_gold_contact": _S + (0.25,),
    "cbp_carbon_limb": _S + (0.20,), "cbp_optic_implant": _S + (0.25,), "cbp_chrome_spine": _L + (0.25,),
    "cbp_skin_weave": _G + (0.15,), "cbp_ripperdoc_steel": _L + (0.25,), "cbp_porcelain_face": _C + (0.15,),
    "cbp_servo_housing": _C + (0.20,), "cbp_titanium_rib": _C + (0.25,), "cbp_mirror_shades": _L + (0.25,),
    "cbp_ice_wall": _S + (0.25,), "cbp_datastream": _L + (0.30,), "cbp_corrupt_memory": ("ek:pixels", dict(cell=6.0, levels=6, dither=0.3), 0.30),
    "cbp_black_ice": _S + (0.25,), "cbp_trace_route": _S + (0.20,), "cbp_ghost_protocol": _L + (0.25,),
    "cbp_quantum_violet": _S + (0.25,), "cbp_daemon_red": ("ek:microtext", dict(), 0.30), "cbp_packet_loss": _L + (0.30,),
    "cbp_firewall_grid": _S + (0.25,), "cbp_neural_static": _L + (0.30,), "cbp_deep_archive": _S + (0.20,),
    "cbp_worm_trail": _S + (0.20,), "cbp_encryption_lattice": _S + (0.25,), "cbp_root_access": ("ek:microtext", dict(), 0.25),
    "cbp_corp_grey": _G + (0.15,), "cbp_rad_warning": _C + (0.25,), "cbp_scav_rust": _C + (0.25,),
    "cbp_duct_grime": _C + (0.25,), "cbp_concrete_rot": _C + (0.25,), "cbp_biohazard_bloom": _S + (0.20,),
    "cbp_oil_slick_puddle": _S + (0.20,), "cbp_rebar_skeleton": _C + (0.25,), "cbp_ash_fall": _S + (0.15,),
    "cbp_corp_glass": _L + (0.25,), "cbp_hazard_stripe": _C + (0.25,), "cbp_sewer_bloom": _S + (0.20,),
    "cbp_scrap_weld": _C + (0.25,), "cbp_static_screen": _L + (0.30,), "cbp_cracked_solar": _W + (0.30,),
    # FAR OUT
    "fo_mirror_ball": _S + (0.30,), "fo_lighted_floor": _L + (0.25,), "fo_lurex_gold": _S + (0.25,),
    "fo_lurex_rose": _S + (0.25,), "fo_roller_rink": _G + (0.20,), "fo_studio_gold": _S + (0.25,),
    "fo_hustle_teal": _W + (0.30,), "fo_glitter_ball_rain": _G + (0.15,), "fo_sequin_sheet": _S + (0.25,),
    "fo_boogie_neon": _S + (0.20,), "fo_velvet_rope": _G + (0.15,), "fo_platform_patent": _S + (0.25,),
    "fo_vinyl_groove": _S + (0.20,), "fo_discotheque_haze": _S + (0.25,), "fo_saturday_chrome": _L + (0.25,),
    "fo_shag_avocado": _G + (0.15,), "fo_shag_harvest": _G + (0.15,), "fo_conversation_pit": _T + (0.25,),
    "fo_wood_panel": _L + (0.25,), "fo_macrame_hang": _T + (0.25,), "fo_linoleum_teal": _C + (0.20,),
    "fo_popcorn_ceiling": _S + (0.20,), "fo_fondue_copper": _L + (0.20,), "fo_corduroy_brown": _T + (0.25,),
    "fo_tab_curtain": _W + (0.30,), "fo_rattan_weave": _T + (0.25,), "fo_terrazzo_kitchen": _S + (0.25,),
    "fo_lava_lamp": _S + (0.20,), "fo_smoked_glass": _S + (0.15,), "fo_formica_boomerang": _G + (0.15,),
    "fo_tooled_saddle": _C + (0.25,), "fo_basket_stamp": _C + (0.20,), "fo_turquoise_silver": _S + (0.25,),
    "fo_concho_row": _L + (0.25,), "fo_rhinestone_suit": _W + (0.25,), "fo_raw_denim": _T + (0.25,),
    "fo_rodeo_dust": _C + (0.25,), "fo_black_hat": _T + (0.25,), "fo_snakeskin_boot": _S + (0.25,),
    "fo_mesa_sunset": _G + (0.20,), "fo_barbed_wire": _S + (0.20,), "fo_longhorn_hide": _T + (0.30,),
    "fo_silver_buckle": _S + (0.25,), "fo_prairie_denim": _T + (0.30,), "fo_outlaw_chrome": _C + (0.25,),
    "fo_airbrush_mural": _S + (0.20,), "fo_metalflake_blue": _S + (0.30,), "fo_metalflake_red": _S + (0.30,),
    "fo_candy_apple": _S + (0.20,), "fo_pinstripe_kit": _G + (0.15,), "fo_sunset_stripe": _S + (0.20,),
    "fo_eagle_gold": _L + (0.25,), "fo_porthole_chrome": _L + (0.25,), "fo_shag_interior": _G + (0.15,),
    "fo_cb_static": _S + (0.25,), "fo_desert_scene": _S + (0.20,), "fo_flame_job": _S + (0.25,),
    "fo_ghost_mural": _S + (0.25,), "fo_wheel_well_rust": _C + (0.25,), "fo_tailgate_sunburst": _S + (0.25,),
}
