# -*- coding: utf-8 -*-
"""Hand-authored per-finish material stories for the five era shelves.

Owner 2026-09-01: *"HAND AUTHOR EVERYTHING. NO DUPLICATES."* and *"the specs
should be diverse, unique, follow the pattern of the base paint and MAKE SENSE.
If it says MINERAL: CHALK CHROME then by GOD it should make you instantly feel
like this finish IS chalk chrome."*

The era shelves shipped with the spec deck chosen from a pool of 27 NAMED decks,
so roughly three finishes per shelf shared each one. Here every finish names its
own cards, chosen by reading its own description.

Format:  fid -> (cards, edge_card, spec_kwargs)

`cards` is ordered by spec_story roughness-descending, so the deadest material
lands in the artwork's darkest regions and the sharpest in its highlights.
`bands="linear"` is for finishes whose artwork is mostly background by area
(filament, spark and dendrite fields), where equal-population bands would slice
the background and give the actual structure a single card.
"""
from __future__ import annotations

CARDS = {
    # ═══════════════════════════════════════════════════════════════════════
    # 💿 ALL THAT — the 1990s
    # ═══════════════════════════════════════════════════════════════════════
    # ── 💾 CD-ROM ─────────────────────────────────────────────────────────
    # data pits under lacquer, diffracting the room
    "at_disc_rainbow":    (("gloss_carbon", "gloss", "liquid_glaze", "spectraflame", "candy_chrome", "mercury"), "chrome", {}),
    # textured ABS that went yellow in four years
    "at_beige_box":       (("ceramic_matte", "powder", "fiberglass", "vinyl", "semi_gloss"), "galvanized", {}),
    # the desktop everyone had
    "at_windows_teal":    (("matte", "eggshell", "semi_gloss", "soft_gloss", "gloss"), "razor", {"bands": "linear"}),
    # chrome pipes assembling themselves forever
    "at_pipes_screensaver": (("flat_black", "gunmetal", "brushed_ti", "satin_chrome", "chrome"), "mercury", {"bands": "linear", "edge_max": 0.03}),
    # bubble chrome type, on everything printed in 1999
    "at_y2k_chrome":      (("gloss_carbon", "satin_chrome", "antique_chrome", "candy_chrome", "chrome"), "chrome", {"bands": "linear", "edge_max": 0.03}),
    # a terminal at 14.4k — phosphor on black
    "at_dial_up_green":   (("void", "flat_black", "satin_carbon", "carrier_mid", "carrier_high"), "razor", {}),
    # translucent blueberry polycarbonate — you could see the works
    "at_frosted_shell":   (("fiberglass", "milk_glass", "sea_glass", "soft_gloss", "liquid_glaze"), "sea_glass", {"bands": "linear"}),
    # a download that failed at 74% and got saved anyway
    "at_corrupt_jpeg":    (("flat_black", "satin_carbon", "vinyl", "razor", "carrier_mid"), "razor", {"bands": "linear"}),
    # 3.5-inch high density, with a shutter that never quite shut
    "at_floppy_black":    (("flat_black", "satin_carbon", "vinyl", "brushed_ti", "gunmetal"), "brushed_ti", {"bands": "linear"}),
    # the authenticity hologram everyone peeled
    "at_holo_sticker":    (("semi_gloss", "pearl", "spectraflame", "candy_chrome", "chrome"), "spectraflame", {"edge_max": 0.03}),
    # white on blue, hex addresses, certainty
    "at_crt_blue_screen": (("void", "gloss_carbon", "semi_gloss", "carrier_mid", "razor"), "carrier_high", {"edge_max": 0.03}),
    # the rollers, and what you scraped off them
    "at_mouse_ball_grime": (("matte", "ceramic_matte", "powder", "patina", "vinyl"), "patina", {}),
    # 100 megabytes and the click of death
    "at_zip_disk":        (("satin_carbon", "vinyl", "semi_gloss", "gunmetal", "brushed_ti"), "gunmetal", {"bands": "linear", "edge_max": 0.03}),
    # the green-gold underside of a blank
    "at_iridescent_cd_r": (("gloss", "liquid_glaze", "spectraflame", "carrier_mid", "candy_chrome"), "candy_chrome", {}),
    # perforated steel desks, blue LEDs, an hour at a time
    "at_cyber_café":      (("gunmetal", "brushed_ti", "galvanized", "carrier_mid", "satin_chrome"), "satin_chrome", {}),

    # ── 🛹 EXTREME ────────────────────────────────────────────────────────
    # sublimated topsheet, scratched to the core
    "at_snowboard_graphic": (("bead_blast", "gloss", "ceramic_gloss", "liquid_glaze", "chrome"), "chrome", {"bands": "linear", "edge_max": 0.03}),
    # colour-blocked nylon that rustled
    "at_windbreaker_block": (("fiberglass", "vinyl", "semi_gloss", "soft_gloss", "satin"), "soft_gloss", {"bands": "linear"}),
    # a colour engineered to be visible from orbit
    "at_dew_green":       (("semi_gloss", "gloss", "carrier_low", "carrier_mid", "candy"), "carrier_high", {"bands": "linear", "edge_max": 0.03}),
    # poured bowl, waxed coping, municipal grey
    "at_skatepark_concrete": (("ceramic_matte", "powder", "bead_blast", "patina", "semi_gloss"), "bead_blast", {}),
    # silicon carbide on adhesive — the roughest deck on the shelf
    "at_grip_tape":       (("flat_black", "matte", "bead_blast", "satin_carbon", "powder"), "razor", {"bands": "linear"}),
    # an oversized tee worn to a nap
    "at_big_dog_print":   (("clear_matte", "eggshell", "vinyl", "satin", "soft_gloss"), "satin", {}),
    # combed into a deck, gone chalky and grey
    "at_surf_wax":        (("clear_matte", "ceramic_matte", "powder", "eggshell", "soft_gloss"), "milk_glass", {}),
    # a backyard jump packed hard
    "at_bmx_dirt":        (("powder", "ceramic_matte", "patina", "bead_blast", "matte"), "patina", {}),
    # purple ano on a chromoly peg, scraped back to metal
    "at_anodised_peg":    (("anodized", "brushed_ti", "galvanized", "satin_chrome", "chrome"), "chrome", {}),
    # neoprene with fluoro panels
    "at_neon_wetsuit":    (("vinyl", "satin", "semi_gloss", "carrier_low", "carrier_mid"), "carrier_high", {"bands": "linear", "edge_max": 0.03}),
    # two layers of masonite over ply, with a seam
    "at_half_pipe_ply":   (("matte", "eggshell", "powder", "semi_gloss", "satin"), "patina", {"bands": "linear"}),
    # vented plastic shell in three colours nobody wanted
    "at_roller_blade":    (("fiberglass", "vinyl", "semi_gloss", "soft_gloss", "gloss"), "gloss", {}),
    # a trail map folded into a pocket until the creases went
    "at_mountain_topo":   (("eggshell", "clear_matte", "ceramic_matte", "semi_gloss", "satin"), "soft_gloss", {"bands": "linear"}),
    # galvanised fence with the corner peeled
    "at_chain_link":      (("galvanized", "brushed_ti", "gunmetal", "bead_blast", "satin_chrome"), "galvanized", {"bands": "linear"}),
    # woven sheath over a rubber core
    "at_bungee_cord":     (("vinyl", "satin", "semi_gloss", "powder", "soft_gloss"), "semi_gloss", {}),

    # ── 🎤 FRESH ──────────────────────────────────────────────────────────
    # two pieces, matching, in a purple that reads as velvet
    "at_velour_tracksuit": (("vinyl", "eggshell", "satin", "pearl", "soft_gloss"), "pearl", {}),
    # herringbone links, worn outside the shirt
    "at_gold_rope":       (("bronze_raw", "antique_chrome", "spectraflame", "candy_chrome", "chrome"), "spectraflame", {}),
    # primary blocks on baggy denim
    "at_cross_colour_block": (("matte", "vinyl", "semi_gloss", "satin", "gloss"), "razor", {}),
    # boardwalk airbrush, name in bubble letters
    "at_airbrush_tee":    (("semi_gloss", "gloss", "ceramic_gloss", "candy", "liquid_glaze"), "candy_chrome", {"bands": "linear"}),
    # reversible cotton twill with a stitched brim
    "at_bucket_hat":      (("eggshell", "ceramic_matte", "satin", "powder", "semi_gloss"), "eggshell", {}),
    # patent toe, mesh panel, midsole kept white
    "at_fresh_kicks":     (("milk_glass", "ceramic_gloss", "gloss", "liquid_glaze", "chrome"), "chrome", {}),
    # twin decks, a graphic equaliser, D cells
    "at_boombox_chrome":  (("satin_carbon", "gunmetal", "brushed_ti", "satin_chrome", "chrome"), "chrome", {}),
    # crushed nap that shows every fingerprint
    "at_velour_rose":     (("vinyl", "satin", "powder", "pearl", "milk_glass"), "pearl", {"bands": "linear"}),
    # cut from sheet in a mall kiosk
    "at_nameplate_gold":  (("satin_chrome", "chrome", "mirror_deep", "brushed_ti", "candy_chrome"), "mercury", {"bands": "linear"}),
    # twenty-two inch leg, stonewashed, stacked
    "at_denim_baggy":     (("ceramic_matte", "powder", "eggshell", "vinyl", "satin"), "bead_blast", {}),
    # two-tone fill with a hard outline, done fast
    "at_graffiti_fill":   (("matte", "semi_gloss", "gloss", "candy", "razor"), "razor", {"bands": "linear"}),
    # angora felt with a nap you could write on
    "at_kangol_felt":     (("clear_matte", "ceramic_matte", "eggshell", "vinyl", "powder"), "soft_gloss", {"bands": "linear"}),
    # polished, removable, photographed more than worn
    "at_grill_chrome":    (("gloss_carbon", "satin_chrome", "candy_chrome", "mirror_deep", "mercury"), "mercury", {}),
    # twelve-inch sleeves gone soft at the corners
    "at_vinyl_crate":     (("matte", "ceramic_matte", "powder", "eggshell", "semi_gloss"), "patina", {}),
    # satin shell with a team logo and a lining that stuck
    "at_starter_jacket":  (("satin", "soft_gloss", "semi_gloss", "gloss", "ceramic_gloss"), "gloss", {}),

    # ── 🎸 FLANNEL ────────────────────────────────────────────────────────
    # buffalo check, brushed cotton
    "at_flannel_red":     (("eggshell", "vinyl", "satin", "powder", "semi_gloss"), "patina", {}),
    # green over black in a windowpane that goes soft
    "at_flannel_forest":  (("flat_black", "matte", "eggshell", "vinyl", "satin"), "powder", {"bands": "linear"}),
    # somebody's grandfather's, three sizes too big
    "at_thrift_cardigan": (("ceramic_matte", "powder", "eggshell", "vinyl", "soft_gloss"), "eggshell", {}),
    # not a downpour — the constant fine one
    "at_seattle_rain":    (("wet", "satin", "milk_glass", "semi_gloss", "clear_matte"), "wet", {}),
    # the green that grows in the cracks
    "at_moss_sidewalk":   (("ceramic_matte", "patina", "powder", "matte", "semi_gloss"), "patina", {"bands": "linear"}),
    # eight-hole, cherry red, creased across the vamp
    "at_doc_marten":      (("semi_gloss", "gloss", "ceramic_gloss", "liquid_glaze", "wet"), "liquid_glaze", {"bands": "linear"}),
    # worn through at the knee honestly, over a year
    "at_distressed_denim": (("ceramic_matte", "powder", "bead_blast", "eggshell", "vinyl"), "bead_blast", {}),
    # plastisol cracked into a map by a hundred washes
    "at_band_tee_crack":  (("matte", "eggshell", "semi_gloss", "clear_matte", "vinyl"), "razor", {"bands": "linear"}),
    # narrow wale olive
    "at_corduroy_olive":  (("vinyl", "satin", "eggshell", "powder", "soft_gloss"), "satin", {"edge_max": 0.03}),
    # nine months of the same sky
    "at_overcast_grey":   (("clear_matte", "ceramic_matte", "milk_glass", "eggshell", "soft_gloss"), "milk_glass", {}),
    # tolex over ply, cigarette-burned
    "at_basement_amp":    (("flat_black", "satin_carbon", "vinyl", "matte", "powder"), "gunmetal", {"bands": "linear"}),
    # a steel toe showing through the leather
    "at_combat_boot_steel": (("satin_carbon", "gunmetal", "brushed_ti", "galvanized", "steel_dark"), "steel_dark", {}),
    # lyrics on a forearm, bleeding
    "at_sharpie_ink":     (("void", "flat_black", "matte", "semi_gloss", "gloss"), "gloss", {"bands": "linear"}),
    # a mixtape with the track list in three pens
    "at_cassette_tape":   (("vinyl", "semi_gloss", "satin_carbon", "powder", "soft_gloss"), "vinyl", {"edge_max": 0.03}),
    # black polish, three days old, picked at
    "at_chipped_nail":    (("gloss", "candy", "vinyl", "flat_black", "bead_blast"), "chrome", {"bands": "linear", "edge_max": 0.03}),

    # ═══════════════════════════════════════════════════════════════════════
    # ⚡ BAD & RAD — the 1980s
    # ═══════════════════════════════════════════════════════════════════════
    # ── 🕹 ARCADE ─────────────────────────────────────────────────────────
    # P1 phosphor at 15 kHz, with the persistence
    "rad_phosphor_green":  (("void", "flat_black", "satin_carbon", "carrier_mid", "carrier_high"), "razor", {"bands": "linear"}),
    # the other monochrome tube — 80 columns of amber
    "rad_amber_terminal":  (("void", "gloss_carbon", "satin_carbon", "carrier_low", "carrier_mid"), "razor", {"bands": "linear"}),
    # sixteen by sixteen, four colours, one of them transparent
    "rad_sprite_sheet":    (("matte", "semi_gloss", "vinyl", "gloss", "razor"), "razor", {"bands": "linear"}),
    # the grid you could see with your face against the glass
    "rad_dot_matrix":      (("satin_carbon", "vinyl", "semi_gloss", "powder", "soft_gloss"), "razor", {"bands": "linear"}),
    # screen-printed vinyl on particle board, sun-faded
    "rad_cabinet_side_art": (("ceramic_matte", "powder", "vinyl", "semi_gloss", "gloss"), "patina", {"bands": "linear"}),
    # chase bulbs behind a translucent panel
    "rad_marquee_bulb":    (("milk_glass", "fiberglass", "soft_gloss", "ceramic_gloss", "liquid_glaze"), "chrome", {"bands": "linear"}),
    # brushed steel around the coin door, worn bright
    "rad_quarter_slot":    (("gunmetal", "brushed_ti", "galvanized", "satin_chrome", "chrome"), "chrome", {"bands": "linear"}),
    # the demo loop nobody watches
    "rad_attract_mode":    (("void", "flat_black", "gloss_carbon", "carrier_mid", "razor"), "carrier_high", {"bands": "linear"}),
    # phenolic ball polished by a million hands
    "rad_trackball_wear":  (("vinyl", "semi_gloss", "gloss", "ceramic_gloss", "liquid_glaze"), "gloss", {}),
    # no pixels at all — the beam draws the line
    "rad_vector_glow":     (("void", "flat_black", "carrier_low", "carrier_mid", "carrier_high"), "chrome", {"bands": "linear"}),
    # the textured plastic surround, matte so it never reflects
    "rad_bezel_black":     (("flat_black", "matte", "ceramic_matte", "vinyl", "satin_carbon"), "powder", {}),
    # two words, blinking
    "rad_insert_coin":     (("flat_black", "satin_carbon", "semi_gloss", "candy", "carrier_mid"), "candy_chrome", {"bands": "linear"}),
    # three initials in a table that gets wiped
    "rad_high_score":      (("gloss_carbon", "semi_gloss", "gloss", "milk_glass", "razor"), "razor", {}),
    # a red ball-top, cracked at the shaft
    "rad_joystick_ball":   (("semi_gloss", "gloss", "ceramic_gloss", "liquid_glaze", "candy"), "candy_chrome", {"bands": "linear"}),
    # the score panel etched permanently into the tube
    "rad_screen_burn":     (("clear_matte", "ceramic_matte", "matte", "eggshell", "powder"), "razor", {"bands": "linear"}),

    # ── 🌆 GRID ───────────────────────────────────────────────────────────
    # the grid running to a vanishing point
    "rad_vector_horizon":  (("void", "gloss_carbon", "carrier_low", "carrier_mid", "chrome"), "chrome", {"bands": "linear"}),
    # a sun cut into horizontal slices
    "rad_sunset_bars":     (("candy", "candy_chrome", "spectraflame", "gloss", "pearl"), "candy_chrome", {}),
    # extruded letters with a blue-to-magenta gradient
    "rad_chrome_type":     (("gloss_carbon", "satin_chrome", "spectraflame", "candy_chrome", "mercury"), "mercury", {"bands": "linear"}),
    # third-generation tape, tracking off
    "rad_vhs_tracking":    (("satin_carbon", "vinyl", "semi_gloss", "powder", "razor"), "razor", {"bands": "linear"}),
    # a twelve-inch disc catching the ceiling light
    "rad_laserdisc_rainbow": (("gloss", "liquid_glaze", "spectraflame", "candy_chrome", "mirror_deep"), "mercury", {}),
    # the side stripe on a car that only existed in an ad
    "rad_outrun_stripe":   (("matte", "semi_gloss", "gloss", "candy", "ceramic_gloss"), "candy_chrome", {}),
    # flamingo and teal on stucco, shot at magic hour
    "rad_miami_pastel":    (("ceramic_matte", "powder", "eggshell", "satin", "soft_gloss"), "pearl", {}),
    # argon and mercury in bent glass, buzzing
    "rad_neon_tube":       (("fiberglass", "milk_glass", "carrier_low", "carrier_mid", "carrier_high"), "chrome", {"bands": "linear"}),
    # the floor of every music video
    "rad_grid_floor":      (("flat_black", "gloss_carbon", "semi_gloss", "carrier_mid", "chrome"), "chrome", {"bands": "linear"}),
    # channel 3 with nothing on it
    "rad_static_snow":     (("matte", "ceramic_matte", "semi_gloss", "milk_glass", "razor"), "razor", {"bands": "linear"}),
    # a gradient with visible banding, because 8-bit
    "rad_digital_sunrise": (("semi_gloss", "gloss", "pearl", "spectraflame", "candy_chrome"), "spectraflame", {}),
    # smoked polystyrene with the little window
    "rad_cassette_shell":  (("satin_carbon", "vinyl", "fiberglass", "semi_gloss", "soft_gloss"), "vinyl", {}),
    # perforated steel over a ten-inch woofer
    "rad_boombox_grille":  (("gunmetal", "brushed_ti", "galvanized", "bead_blast", "satin_chrome"), "galvanized", {}),
    # ivory-look ABS gone slightly yellow
    "rad_synth_key":       (("ceramic_matte", "eggshell", "vinyl", "semi_gloss", "gloss"), "eggshell", {}),
    # beams through haze, arranged so they cross
    "rad_laser_grid":      (("void", "flat_black", "carrier_low", "carrier_high", "chrome"), "carrier_mid", {"bands": "linear"}),

    # ── 📐 MEMPHIS ────────────────────────────────────────────────────────
    # Sottsass drew the squiggle and the whole decade copied it
    "rad_milano_squiggle": (("ceramic_matte", "vinyl", "semi_gloss", "gloss", "razor"), "razor", {}),
    # the black-on-white scribble laminate
    "rad_bacterio_print":  (("clear_matte", "milk_glass", "semi_gloss", "gloss", "razor"), "razor", {"bands": "linear"}),
    # teal and purple on a paper cup
    "rad_jazz_cup":        (("ceramic_matte", "eggshell", "powder", "semi_gloss", "satin"), "soft_gloss", {"bands": "linear"}),
    # marble chips in white cement, ground flat
    "rad_terrazzo_chip":   (("ceramic_matte", "powder", "semi_gloss", "ceramic_gloss", "milk_glass"), "milk_glass", {}),
    # mint on a bathroom tile, with a black grout line
    "rad_pastel_mint":     (("flat_black", "ceramic_gloss", "gloss", "milk_glass", "liquid_glaze"), "gloss", {}),
    # peach flocking on a padded headboard
    "rad_peach_fuzz":      (("clear_matte", "vinyl", "satin", "eggshell", "powder"), "eggshell", {"bands": "linear"}),
    # scattered rectangles at random angles, fused under laminate
    "rad_confetti_laminate": (("matte", "eggshell", "semi_gloss", "gloss", "ceramic_gloss"), "razor", {"bands": "linear"}),
    # small square tiles in three colours
    "rad_grid_tile":       (("ceramic_gloss", "gloss", "semi_gloss", "milk_glass", "liquid_glaze"), "ceramic_gloss", {"bands": "linear"}),
    # a flatweave rug in colours that fight
    "rad_zigzag_runner":   (("eggshell", "vinyl", "satin", "powder", "ceramic_matte"), "satin", {}),
    # powder-coated rod bent into a chair
    "rad_neon_wire_chair": (("powder", "ceramic_matte", "semi_gloss", "gunmetal", "brushed_ti"), "brushed_ti", {"bands": "linear"}),
    # flecked wallpaper, the kind that hid a bad plaster job
    "rad_speckle_wall":    (("ceramic_matte", "powder", "eggshell", "clear_matte", "semi_gloss"), "bead_blast", {}),
    # fluted glass brick in a partition wall
    "rad_glass_block":     (("fiberglass", "sea_glass", "milk_glass", "liquid_glaze", "ceramic_gloss"), "sea_glass", {}),
    # high-gloss black lacquer with one primary-coloured door
    "rad_lacquer_cabinet": (("gloss_carbon", "gloss", "ceramic_gloss", "liquid_glaze", "mirror_deep"), "mercury", {"bands": "linear"}),
    # rag-rolled over base coat
    "rad_sponge_paint":    (("bead_blast", "ceramic_matte", "powder", "eggshell", "semi_gloss"), "patina", {}),
    # coloured aluminium extrusion on the edge of everything
    "rad_anodised_trim":   (("anodized", "brushed_ti", "galvanized", "satin_chrome", "spectraflame"), "spectraflame", {}),

    # ── 🎸 RADICAL ────────────────────────────────────────────────────────
    # thrown from a brush across a white shirt
    "rad_splatter_tee":    (("clear_matte", "eggshell", "vinyl", "semi_gloss", "gloss"), "razor", {"bands": "linear"}),
    # backcombed, sprayed, lit from behind
    "rad_hair_metal":      (("satin_carbon", "gunmetal", "spectraflame", "candy_chrome", "chrome"), "chrome", {"bands": "linear"}),
    # lycra in a colour that does not occur in nature
    "rad_neon_spandex":    (("vinyl", "satin", "semi_gloss", "carrier_low", "carrier_mid"), "carrier_high", {}),
    # grip tape over seven-ply maple
    "rad_skate_deck":      (("bead_blast", "matte", "powder", "ceramic_matte", "satin_carbon"), "razor", {"bands": "linear"}),
    # airbrushed stripes on a guitar body
    "rad_tiger_stripe":    (("gloss", "ceramic_gloss", "candy", "liquid_glaze", "mercury"), "candy_chrome", {}),
    # a headband, a striped leotard and a floor mat
    "rad_aerobics_gym":    (("vinyl", "satin", "semi_gloss", "eggshell", "soft_gloss"), "semi_gloss", {}),
    # soft edges, hard highlights, and a lens flare
    "rad_airbrush_portrait": (("satin", "semi_gloss", "gloss", "ceramic_gloss", "pearl"), "pearl", {"bands": "linear"}),
    # the same splatter under clear on a board
    "rad_rad_splatter_deck": (("gloss", "liquid_glaze", "candy", "clear_matte", "bead_blast"), "chrome", {"bands": "linear"}),
    # black on white in stripes that never repeat
    "rad_zebra_wrap":      (("flat_black", "matte", "milk_glass", "semi_gloss", "ceramic_gloss"), "razor", {}),
    # moulded rubber in fluorescent green
    "rad_neon_grip":       (("vinyl", "powder", "satin", "carrier_low", "carrier_mid"), "carrier_high", {"bands": "linear"}),
    # spring steel in a fabric sleeve, banned by every school
    "rad_slap_bracelet":   (("vinyl", "satin", "brushed_ti", "spectraflame", "candy_chrome"), "spectraflame", {}),
    # squeezed from a bottle onto a sweatshirt
    "rad_puffy_paint":     (("vinyl", "soft_gloss", "eggshell", "gloss", "satin"), "soft_gloss", {"bands": "linear"}),
    # scratch-and-sniff, googly-eye and puffy, layered
    "rad_trapper_sticker": (("vinyl", "semi_gloss", "gloss", "spectraflame", "candy_chrome"), "candy_chrome", {"bands": "linear"}),
    # thermochromic dye that changed where you touched it
    "rad_hypercolour":     (("satin", "semi_gloss", "pearl", "milk_glass", "spectraflame"), "pearl", {"bands": "linear"}),
    # the album cover: chrome type, lightning
    "rad_big_hair_chrome": (("gloss_carbon", "satin_chrome", "candy_chrome", "mirror_deep", "chrome"), "chrome", {"bands": "linear"}),

    # ═══════════════════════════════════════════════════════════════════════
    # 🌃 CYBERPUNK
    # ═══════════════════════════════════════════════════════════════════════
    # ── 🌃 STREET ─────────────────────────────────────────────────────────
    # the road after rain, holding every sign in the street
    "cbp_wet_asphalt":     (("satin_carbon", "matte", "semi_gloss", "wet", "liquid_glaze"), "mercury", {}),
    # low-pressure sodium: one wavelength, so nothing under it has a colour
    "cbp_sodium_vapour":   (("void", "flat_black", "gloss_carbon", "carrier_low", "carrier_mid"), "razor", {"bands": "linear"}),
    # stacked vertical signs, six deep
    "cbp_kanji_signage":   (("flat_black", "semi_gloss", "gloss", "carrier_mid", "carrier_high"), "chrome", {"bands": "linear"}),
    # a twelve-storey projection selling something that does not exist
    "cbp_holo_advert":     (("gloss_carbon", "gloss", "spectraflame", "candy_chrome", "mirror_deep"), "spectraflame", {"bands": "linear"}),
    # tarpaulin, strung bulbs, steam, forty stalls
    "cbp_night_market":    (("vinyl", "satin", "semi_gloss", "gloss", "ceramic_gloss"), "candy_chrome", {"bands": "linear"}),
    # falling through a sodium beam, pitting anything left out
    "cbp_acid_rain":       (("patina", "bead_blast", "powder", "wet", "liquid_glaze"), "antique_chrome", {"bands": "linear"}),
    # repainted over a repaint, previous operator showing through
    "cbp_taxi_panel":      (("ceramic_matte", "semi_gloss", "gloss", "candy", "ceramic_gloss"), "candy_chrome", {}),
    # cast iron over a vent, warm enough to sleep beside
    "cbp_steam_grate":     (("gunmetal", "galvanized", "patina", "brushed_ti", "bead_blast"), "gunmetal", {}),
    # the reflection is more saturated than the sign
    "cbp_puddle_neon":     (("gloss_carbon", "wet", "liquid_glaze", "carrier_mid", "mercury"), "chrome", {}),
    # a rolling shutter, down, with two generations of tags
    "cbp_shutter_tag":     (("ceramic_matte", "powder", "matte", "semi_gloss", "gloss"), "razor", {}),
    # vertical water on glass, with the drops that win races
    "cbp_rain_screen":     (("fiberglass", "sea_glass", "milk_glass", "wet", "liquid_glaze"), "sea_glass", {"bands": "linear"}),
    # particulate in the beam, which is the only reason you see it
    "cbp_sodium_fog":      (("clear_matte", "ceramic_matte", "milk_glass", "carrier_low", "soft_gloss"), "carrier_mid", {}),
    # a lit machine on an empty street, the brightest thing there
    "cbp_vending_glow":    (("vinyl", "semi_gloss", "fiberglass", "carrier_mid", "carrier_high"), "chrome", {"bands": "linear"}),
    # bent glass, argon, and a transformer that has been humming for years
    "cbp_neon_tube":       (("flat_black", "fiberglass", "carrier_low", "carrier_high", "chrome"), "carrier_mid", {"bands": "linear"}),
    # concrete under a bridge, stained by forty years of exhaust
    "cbp_overpass_sodium": (("ceramic_matte", "patina", "powder", "bead_blast", "semi_gloss"), "patina", {"bands": "linear"}),

    # ── 🦾 CHROME ─────────────────────────────────────────────────────────
    # armour under the skin, seams visible when the arm turns
    "cbp_subdermal_plate": (("satin_carbon", "gunmetal", "brushed_ti", "steel_dark", "chrome_dry"), "chrome", {}),
    # a socket machined to a tolerance you can feel
    "cbp_neural_port":     (("gunmetal", "brushed_ti", "steel_dark", "satin_chrome", "mercury"), "steel_dark", {}),
    # zirconia over a titanium frame, glazed white
    "cbp_ceramic_limb":    (("ceramic_matte", "milk_glass", "ceramic_gloss", "gloss", "liquid_glaze"), "milk_glass", {}),
    # the budget option: heavy, loud, does not pretend
    "cbp_gunmetal_aug":    (("matte", "satin_carbon", "gunmetal", "galvanized", "brushed_ti"), "gunmetal", {"bands": "linear"}),
    # cultured tissue over a lattice, kept wet
    "cbp_wetware_membrane": (("vinyl", "semi_gloss", "gloss", "wet", "liquid_glaze"), "pearl", {"bands": "linear"}),
    # plated pins in a connector
    "cbp_gold_contact":    (("satin_carbon", "bronze_raw", "antique_chrome", "spectraflame", "candy_chrome"), "spectraflame", {"bands": "linear"}),
    # twill weave under clear, light enough to be uncanny
    "cbp_carbon_limb":     (("gloss_carbon", "satin_carbon", "gloss", "ceramic_gloss", "liquid_glaze"), "razor", {}),
    # the lens catches light at angles a real eye does not
    "cbp_optic_implant":   (("sea_glass", "milk_glass", "liquid_glaze", "spectraflame", "mirror_deep"), "chrome", {}),
    # segmented, articulated, polished on the segments that show
    "cbp_chrome_spine":    (("gloss_carbon", "satin_chrome", "candy_chrome", "mercury", "chrome"), "mercury", {"bands": "linear"}),
    # subdermal mesh — you can feel the grid through the skin
    "cbp_skin_weave":      (("eggshell", "vinyl", "satin", "powder", "soft_gloss"), "brushed_ti", {"bands": "linear"}),
    # back-alley work, autoclaved twice
    "cbp_ripperdoc_steel": (("bead_blast", "galvanized", "gunmetal", "steel_dark", "satin_chrome"), "steel_dark", {"bands": "linear"}),
    # a full cosmetic shell, perfect, and four percent wrong
    "cbp_porcelain_face":  (("milk_glass", "ceramic_gloss", "pearl", "gloss", "liquid_glaze"), "pearl", {"bands": "linear"}),
    # moulded boot over the joint, keeping grit out
    "cbp_servo_housing":   (("matte", "vinyl", "satin", "powder", "semi_gloss"), "gunmetal", {"bands": "linear"}),
    # printed lattice bedded into bone
    "cbp_titanium_rib":    (("brushed_ti", "anodized", "galvanized", "frozen_metal", "satin_chrome"), "brushed_ti", {"bands": "linear"}),
    # worn indoors, at night, which was always the point
    "cbp_mirror_shades":   (("flat_black", "gloss_carbon", "mirror_deep", "candy_chrome", "chrome"), "chrome", {}),

    # ── 💊 NETRUN ─────────────────────────────────────────────────────────
    # intrusion countermeasures rendered as a surface
    "cbp_ice_wall":        (("fiberglass", "sea_glass", "milk_glass", "frozen_film", "liquid_glaze"), "satin_chrome", {"bands": "linear"}),
    # characters falling in columns
    "cbp_datastream":      (("void", "flat_black", "satin_carbon", "carrier_mid", "carrier_high"), "razor", {"bands": "linear"}),
    # a block that failed its checksum and got written anyway
    "cbp_corrupt_memory":  (("satin_carbon", "vinyl", "semi_gloss", "razor", "carrier_mid"), "razor", {"bands": "linear"}),
    # the kind that is legal to deploy and will stop your heart
    "cbp_black_ice":       (("void", "gloss_carbon", "carrier_low", "carrier_high", "mirror_deep"), "chrome", {"bands": "linear"}),
    # somebody walking back up the connection, one hop at a time
    "cbp_trace_route":     (("flat_black", "gunmetal", "brushed_ti", "carrier_mid", "satin_chrome"), "carrier_high", {"bands": "linear"}),
    # traffic that is there and not there
    "cbp_ghost_protocol":  (("clear_matte", "fiberglass", "milk_glass", "sea_glass", "soft_gloss"), "milk_glass", {"bands": "linear"}),
    # a key that is every value until somebody looks
    "cbp_quantum_violet":  (("gloss", "pearl", "spectraflame", "candy_chrome", "mirror_deep"), "spectraflame", {"bands": "linear"}),
    # a process with no owner, running since before the current management
    "cbp_daemon_red":      (("void", "matte", "gloss_carbon", "candy", "carrier_mid"), "candy_chrome", {"bands": "linear"}),
    # thirty percent gone, and the codec inventing the rest
    "cbp_packet_loss":     (("matte", "satin_carbon", "vinyl", "semi_gloss", "razor"), "razor", {"bands": "linear"}),
    # the boundary drawn as a lattice
    "cbp_firewall_grid":   (("flat_black", "semi_gloss", "carrier_low", "carrier_mid", "chrome"), "carrier_high", {"bands": "linear"}),
    # what the interface gives you when the connection is bad
    "cbp_neural_static":   (("clear_matte", "ceramic_matte", "matte", "semi_gloss", "razor"), "razor", {"bands": "linear"}),
    # cold storage, spinning down
    "cbp_deep_archive":    (("void", "flat_black", "matte", "satin_carbon", "gunmetal"), "steel_dark", {"bands": "linear"}),
    # propagation mapped over a night — organic because it is
    "cbp_worm_trail":      (("gloss_carbon", "semi_gloss", "carrier_low", "carrier_mid", "carrier_high"), "chrome", {"bands": "linear"}),
    # the cipher drawn as a crystal, which is a lie that helps
    "cbp_encryption_lattice": (("sea_glass", "milk_glass", "frozen_film", "liquid_glaze", "mirror_deep"), "chrome", {"bands": "linear"}),
    # one prompt, no password, everything downstream
    "cbp_root_access":     (("flat_black", "gloss_carbon", "candy", "carrier_high", "mercury"), "chrome", {"bands": "linear"}),

    # ── ☢ SPRAWL ──────────────────────────────────────────────────────────
    # the colour of every building owned by a company
    "cbp_corp_grey":       (("ceramic_matte", "powder", "eggshell", "semi_gloss", "soft_gloss"), "galvanized", {}),
    # the trefoil, stencilled, half worn off, still perfectly legible
    "cbp_rad_warning":     (("galvanized", "matte", "ceramic_matte", "semi_gloss", "gloss"), "razor", {}),
    # everything not bolted down was taken; this is what was left
    "cbp_scav_rust":       (("patina", "bead_blast", "galvanized", "powder", "bronze_raw"), "antique_chrome", {}),
    # galvanised trunking with thirty years of building on it
    "cbp_duct_grime":      (("galvanized", "patina", "gunmetal", "brushed_ti", "matte"), "galvanized", {}),
    # spalling where the rebar underneath has rusted
    "cbp_concrete_rot":    (("ceramic_matte", "powder", "patina", "bead_blast", "bronze_raw"), "patina", {}),
    # something growing in a stairwell
    "cbp_biohazard_bloom": (("ceramic_matte", "patina", "vinyl", "semi_gloss", "wet"), "carrier_mid", {"bands": "linear"}),
    # a film one wavelength thick
    "cbp_oil_slick_puddle": (("wet", "gloss", "liquid_glaze", "spectraflame", "mirror_deep"), "spectraflame", {"bands": "linear"}),
    # a floor plate that never got poured, going orange
    "cbp_rebar_skeleton":  (("powder", "patina", "bronze_raw", "galvanized", "steel_dark"), "steel_dark", {"bands": "linear"}),
    # particulate from something burning two districts over
    "cbp_ash_fall":        (("clear_matte", "ceramic_matte", "powder", "eggshell", "bead_blast"), "bead_blast", {"bands": "linear"}),
    # curtain wall, mirrored outward, so the building never looks back
    "cbp_corp_glass":      (("sea_glass", "milk_glass", "liquid_glaze", "mirror_deep", "chrome"), "mercury", {"bands": "linear"}),
    # diagonal yellow and black
    "cbp_hazard_stripe":   (("matte", "vinyl", "semi_gloss", "gloss", "ceramic_gloss"), "razor", {"bands": "linear"}),
    # runoff in a channel, iridescent where it should not be
    "cbp_sewer_bloom":     (("patina", "semi_gloss", "wet", "spectraflame", "liquid_glaze"), "candy_chrome", {"bands": "linear"}),
    # stick welded by somebody in a hurry, ground flat by nobody
    "cbp_scrap_weld":      (("bead_blast", "gunmetal", "steel_dark", "brushed_ti", "antique_chrome"), "steel_dark", {}),
    # a public display showing the same fault for a long time
    "cbp_static_screen":   (("flat_black", "satin_carbon", "vinyl", "semi_gloss", "carrier_low"), "razor", {"bands": "linear"}),
    # a panel array with a third of its cells shattered
    "cbp_cracked_solar":   (("gloss_carbon", "fiberglass", "sea_glass", "gloss", "liquid_glaze"), "razor", {"bands": "linear"}),

    # ═══════════════════════════════════════════════════════════════════════
    # 🪩 FAR OUT — the 1970s
    # ═══════════════════════════════════════════════════════════════════════
    # ── 🪩 DISCO ──────────────────────────────────────────────────────────
    # a thousand glass tiles on a motor
    "fo_mirror_ball":      (("gloss_carbon", "satin_chrome", "candy_chrome", "mirror_deep", "chrome"), "chrome", {}),
    # perspex squares lit from underneath
    "fo_lighted_floor":    (("fiberglass", "milk_glass", "sea_glass", "soft_gloss", "liquid_glaze"), "carrier_mid", {"bands": "linear"}),
    # metallic thread woven through the knit
    "fo_lurex_gold":       (("vinyl", "satin", "bronze_raw", "spectraflame", "candy_chrome"), "spectraflame", {}),
    # the same thread in rose gold
    "fo_lurex_rose":       (("satin", "eggshell", "pearl", "candy_chrome", "mercury"), "candy_chrome", {}),
    # sealed maple under blacklight, forty years of wax
    "fo_roller_rink":      (("eggshell", "semi_gloss", "gloss", "ceramic_gloss", "liquid_glaze"), "carrier_mid", {"bands": "linear"}),
    # gilt, mirror and a doorman; the room was mostly dark
    "fo_studio_gold":      (("satin_carbon", "bronze_raw", "antique_chrome", "spectraflame", "mercury"), "mercury", {"bands": "linear"}),
    # polyester in a colour that existed for about a year
    "fo_hustle_teal":      (("vinyl", "satin", "semi_gloss", "soft_gloss", "gloss"), "semi_gloss", {"bands": "linear"}),
    # the dots the ball throws, moving across everything
    "fo_glitter_ball_rain": (("void", "flat_black", "gloss_carbon", "satin_chrome", "chrome"), "chrome", {"bands": "linear"}),
    # overlapping paillettes stitched in courses
    "fo_sequin_sheet":     (("semi_gloss", "gloss", "satin_chrome", "candy_chrome", "mirror_deep"), "chrome", {"bands": "linear"}),
    # bent tube in three colours, buzzing
    "fo_boogie_neon":      (("flat_black", "fiberglass", "carrier_low", "carrier_mid", "carrier_high"), "chrome", {"bands": "linear"}),
    # crushed velvet, the deepest black in the building
    "fo_velvet_rope":      (("void", "flat_black", "vinyl", "satin", "eggshell"), "pewter_metal", {"bands": "linear"}),
    # patent leather on a four-inch stack — a mirror you walk on
    "fo_platform_patent":  (("gloss_carbon", "gloss", "ceramic_gloss", "liquid_glaze", "mirror_deep"), "mercury", {}),
    # a twelve-inch single lit from the side so the grooves show
    "fo_vinyl_groove":     (("satin_carbon", "gloss_carbon", "semi_gloss", "gloss", "razor"), "razor", {"bands": "linear"}),
    # dry ice and cigarette smoke holding the beams up
    "fo_discotheque_haze": (("clear_matte", "milk_glass", "fiberglass", "soft_gloss", "sea_glass"), "milk_glass", {"bands": "linear"}),
    # the white suit was the exception; everything else was chrome
    "fo_saturday_chrome":  (("gunmetal", "brushed_ti", "satin_chrome", "candy_chrome", "chrome"), "chrome", {}),

    # ── 🟫 SHAG ───────────────────────────────────────────────────────────
    # two inches of pile in a colour named after a fruit
    "fo_shag_avocado":     (("vinyl", "satin", "eggshell", "powder", "soft_gloss"), "satin", {}),
    # harvest gold, the other colour every appliance came in
    "fo_shag_harvest":     (("satin", "eggshell", "powder", "ceramic_matte", "semi_gloss"), "eggshell", {"bands": "linear"}),
    # burnt orange upholstery on a sunken bench
    "fo_conversation_pit": (("clear_matte", "vinyl", "eggshell", "satin", "semi_gloss"), "powder", {}),
    # photo-printed walnut on hardboard
    "fo_wood_panel":       (("semi_gloss", "gloss", "ceramic_gloss", "satin", "soft_gloss"), "gloss", {"bands": "linear"}),
    # jute knotted into a plant hanger
    "fo_macrame_hang":     (("ceramic_matte", "powder", "eggshell", "clear_matte", "vinyl"), "bead_blast", {}),
    # sheet vinyl with a repeat designed to hide crumbs
    "fo_linoleum_teal":    (("vinyl", "semi_gloss", "gloss", "soft_gloss", "ceramic_gloss"), "semi_gloss", {}),
    # sprayed texture with a little sparkle in it
    "fo_popcorn_ceiling":  (("clear_matte", "ceramic_matte", "powder", "bead_blast", "milk_glass"), "bead_blast", {}),
    # hammered copper on the good pot
    "fo_fondue_copper":    (("bronze_raw", "antique_chrome", "patina", "galvanized", "spectraflame"), "bronze_raw", {}),
    # wide wale, worn at the knee
    "fo_corduroy_brown":   (("eggshell", "vinyl", "satin", "powder", "matte"), "satin", {}),
    # barkcloth with a bold repeat on wooden rings
    "fo_tab_curtain":      (("ceramic_matte", "eggshell", "vinyl", "satin", "soft_gloss"), "eggshell", {}),
    # a peacock chair nobody could sit in comfortably
    "fo_rattan_weave":     (("bead_blast", "powder", "ceramic_matte", "eggshell", "vinyl"), "patina", {}),
    # chips of everything set in resin and ground flat
    "fo_terrazzo_kitchen": (("ceramic_matte", "semi_gloss", "ceramic_gloss", "gloss", "milk_glass"), "milk_glass", {}),
    # wax rising in a column
    "fo_lava_lamp":        (("fiberglass", "sea_glass", "milk_glass", "liquid_glaze", "candy"), "candy_chrome", {"bands": "linear"}),
    # bronze-tinted glass in the coffee table
    "fo_smoked_glass":     (("gloss_carbon", "sea_glass", "gloss", "liquid_glaze", "mirror_deep"), "mercury", {"bands": "linear"}),
    # laminate with the little shapes on it, and a chrome edge
    "fo_formica_boomerang": (("matte", "semi_gloss", "gloss", "ceramic_gloss", "satin_chrome"), "satin_chrome", {"bands": "linear"}),

    # ── 🤠 OUTLAW ─────────────────────────────────────────────────────────
    # Sheridan floral cut with a swivel knife and beveled
    "fo_tooled_saddle":    (("matte", "powder", "eggshell", "semi_gloss", "satin"), "patina", {"bands": "linear"}),
    # a basketweave stamp walked across the whole skirt
    "fo_basket_stamp":     (("ceramic_matte", "powder", "vinyl", "satin", "semi_gloss"), "patina", {}),
    # Sleeping Beauty stone in a hand-stamped bezel
    "fo_turquoise_silver": (("ceramic_matte", "milk_glass", "brushed_ti", "satin_chrome", "chrome"), "chrome", {}),
    # hammered silver discs down a belt
    "fo_concho_row":       (("brushed_ti", "galvanized", "satin_chrome", "antique_chrome", "chrome"), "antique_chrome", {"bands": "linear"}),
    # a Nudie suit: chain stitch, cactus, and more stones
    "fo_rhinestone_suit":  (("satin", "semi_gloss", "pearl", "candy_chrome", "chrome"), "chrome", {"bands": "linear"}),
    # selvedge twill, unwashed
    "fo_raw_denim":        (("matte", "ceramic_matte", "eggshell", "vinyl", "powder"), "bead_blast", {}),
    # arena dirt hanging in the light after eight seconds
    "fo_rodeo_dust":       (("clear_matte", "ceramic_matte", "powder", "bead_blast", "eggshell"), "powder", {"bands": "linear"}),
    # beaver felt, brushed one way, the darkest thing in the room
    "fo_black_hat":        (("flat_black", "matte", "vinyl", "satin", "powder"), "satin", {"bands": "linear"}),
    # belly cut, lacquered
    "fo_snakeskin_boot":   (("gloss_carbon", "gloss", "ceramic_gloss", "liquid_glaze", "mirror_deep"), "candy_chrome", {"bands": "linear"}),
    # sandstone in horizontal courses with the light going
    "fo_mesa_sunset":      (("ceramic_matte", "powder", "patina", "eggshell", "semi_gloss"), "patina", {}),
    # four-point wire on cedar posts, rusted
    "fo_barbed_wire":      (("patina", "galvanized", "brushed_ti", "bronze_raw", "steel_dark"), "steel_dark", {"bands": "linear"}),
    # brindle hide with the hair still on
    "fo_longhorn_hide":    (("vinyl", "eggshell", "satin", "powder", "semi_gloss"), "eggshell", {}),
    # a trophy buckle the size of a saucer
    "fo_silver_buckle":    (("brushed_ti", "satin_chrome", "antique_chrome", "mirror_deep", "chrome"), "mercury", {"bands": "linear"}),
    # chambray gone pale at the shoulders
    "fo_prairie_denim":    (("clear_matte", "ceramic_matte", "eggshell", "vinyl", "satin"), "bead_blast", {}),
    # exhaust and a kick starter, wiped with a rag
    "fo_outlaw_chrome":    (("gunmetal", "steel_dark", "brushed_ti", "satin_chrome", "chrome"), "chrome", {"bands": "linear"}),

    # ── 🚐 VAN ART ────────────────────────────────────────────────────────
    # a wizard, a wolf and a planet
    "fo_airbrush_mural":   (("satin", "candy", "pearl", "gloss", "candy_chrome"), "candy_chrome", {}),
    # big flake laid heavy under clear, sanded and shot again
    "fo_metalflake_blue":  (("gloss", "liquid_glaze", "spectraflame", "candy_chrome", "chrome"), "chrome", {"bands": "linear"}),
    # the same flake in red, which shows every flaw
    "fo_metalflake_red":   (("gloss_carbon", "gloss", "candy", "candy_chrome", "mercury"), "mercury", {"bands": "linear"}),
    # candy over a silver base, so the colour has depth
    "fo_candy_apple":      (("satin_chrome", "gloss", "candy", "liquid_glaze", "candy_chrome"), "candy_chrome", {"bands": "linear"}),
    # one-shot enamel pulled with a dagger brush, no tape
    "fo_pinstripe_kit":    (("matte", "semi_gloss", "gloss", "ceramic_gloss", "razor"), "razor", {"bands": "linear"}),
    # the graduated stripe down the flank
    "fo_sunset_stripe":    (("semi_gloss", "gloss", "candy", "ceramic_gloss", "spectraflame"), "spectraflame", {}),
    # gold leaf laid over size and burnished, then outlined
    "fo_eagle_gold":       (("bronze_raw", "antique_chrome", "spectraflame", "candy_chrome", "mirror_deep"), "spectraflame", {"bands": "linear"}),
    # a bubble window and a chrome trim ring
    "fo_porthole_chrome":  (("fiberglass", "sea_glass", "milk_glass", "satin_chrome", "chrome"), "chrome", {"bands": "linear"}),
    # the inside was carpeted. All of it.
    "fo_shag_interior":    (("clear_matte", "vinyl", "eggshell", "powder", "satin"), "satin", {}),
    # a chromed mic, a whip antenna and forty channels of noise
    "fo_cb_static":        (("satin_carbon", "gunmetal", "brushed_ti", "galvanized", "chrome"), "razor", {"bands": "linear"}),
    # airbrushed dunes with a saguaro in the middle distance
    "fo_desert_scene":     (("ceramic_matte", "eggshell", "powder", "semi_gloss", "gloss"), "soft_gloss", {}),
    # licks laid out in tape, shot hot in the middle
    "fo_flame_job":        (("matte", "semi_gloss", "gloss", "carrier_mid", "candy_chrome"), "carrier_high", {}),
    # pearl on pearl — invisible head-on and unmistakable at an angle
    "fo_ghost_mural":      (("satin", "semi_gloss", "pearl", "milk_glass", "soft_gloss"), "pearl", {}),
    # the part of the van the mural never reached
    "fo_wheel_well_rust":  (("patina", "bronze_raw", "bead_blast", "galvanized", "powder"), "antique_chrome", {"bands": "linear"}),
    # rays out of a single point on the back doors
    "fo_tailgate_sunburst": (("matte", "semi_gloss", "gloss", "spectraflame", "carrier_mid"), "carrier_high", {"bands": "linear"}),

    # ═══════════════════════════════════════════════════════════════════════
    # 🎯 TACTICAL & FIELD
    # ═══════════════════════════════════════════════════════════════════════
    # ── 🌲 CAMO ───────────────────────────────────────────────────────────
    # four colours, organic blobs, printed on cotton twill
    "tac_m81_woodland":    (("ceramic_matte", "matte", "powder", "eggshell", "semi_gloss"), "patina", {}),
    # pixels at two scales at once
    "tac_marpat_digital":  (("matte", "ceramic_matte", "powder", "vinyl", "satin"), "razor", {"bands": "linear"}),
    # brush strokes running horizontally, cut for jungle
    "tac_tiger_stripe":    (("eggshell", "vinyl", "satin", "powder", "semi_gloss"), "satin", {}),
    # seven colours that blend rather than edge
    "tac_multicam_transition": (("clear_matte", "ceramic_matte", "eggshell", "powder", "soft_gloss"), "eggshell", {}),
    # two-colour disruptive over sand, printed on cotton
    "tac_desert_dpm":      (("ceramic_matte", "powder", "eggshell", "clear_matte", "matte"), "bead_blast", {}),
    # an oversuit pulled over everything else, tearing
    "tac_snow_overwhite":  (("clear_matte", "milk_glass", "ceramic_matte", "bead_blast", "soft_gloss"), "milk_glass", {}),
    # photo-real reed and cattail
    "tac_duck_blind":      (("ceramic_matte", "eggshell", "vinyl", "semi_gloss", "soft_gloss"), "powder", {"bands": "linear"}),
    # the one everybody agrees does not work anywhere
    "tac_urban_grey_digital": (("matte", "ceramic_matte", "semi_gloss", "powder", "vinyl"), "razor", {"bands": "linear"}),
    # painted by hand onto shelter-halves
    "tac_brushstroke_field": (("powder", "ceramic_matte", "eggshell", "satin", "matte"), "patina", {}),
    # reversible spot pattern, green one side and beach the other
    "tac_frog_skin":       (("vinyl", "eggshell", "satin", "semi_gloss", "soft_gloss"), "semi_gloss", {}),
    # six colours with black pebble spots
    "tac_chocolate_chip":  (("ceramic_matte", "powder", "eggshell", "matte", "flat_black"), "bead_blast", {}),
    # vertical dashes over a base
    "tac_rain_pattern":    (("matte", "powder", "vinyl", "semi_gloss", "satin"), "razor", {"bands": "linear"}),
    # dense spots that dither into each other at ten metres
    "tac_flecktarn":       (("ceramic_matte", "matte", "powder", "satin", "semi_gloss"), "powder", {}),
    # the same stripe in blacks that differ only in how they hold light
    "tac_tigerstripe_night": (("void", "flat_black", "matte", "satin_carbon", "vinyl"), "satin_carbon", {}),
    # photo bark and limbs
    "tac_break_up_bark":   (("powder", "ceramic_matte", "patina", "eggshell", "vinyl"), "patina", {}),

    # ── 🔫 HARDWARE ───────────────────────────────────────────────────────
    # ceramic in a polymer carrier, sprayed thin and baked
    "tac_cerakote_grey":   (("ceramic_matte", "powder", "matte", "semi_gloss", "bead_blast"), "gunmetal", {"bands": "linear"}),
    # manganese phosphate, porous by design so it holds oil
    "tac_parkerised":      (("bead_blast", "powder", "galvanized", "gunmetal", "patina"), "gunmetal", {"bands": "linear"}),
    # moulded-in texture on a polymer frame
    "tac_fde_polymer":     (("vinyl", "powder", "ceramic_matte", "satin", "semi_gloss"), "powder", {"bands": "linear"}),
    # thermoformed over the mould, with the pebble grain
    "tac_kydex_sheet":     (("vinyl", "satin", "semi_gloss", "fiberglass", "soft_gloss"), "vinyl", {}),
    # hot salts and an oil wipe over polished steel
    "tac_gun_blue":        (("gloss_carbon", "gunmetal", "steel_dark", "satin_chrome", "mirror_deep"), "mercury", {"bands": "linear"}),
    # slots at a fixed pitch, anodised, numbered
    "tac_rail_section":    (("anodized", "brushed_ti", "gunmetal", "galvanized", "satin_chrome"), "brushed_ti", {"bands": "linear"}),
    # titanium that has been hot enough, often enough
    "tac_suppressor_heat": (("bronze_raw", "patina", "anodized", "brushed_ti", "spectraflame"), "spectraflame", {}),
    # multi-coated lens, purple in reflection
    "tac_optic_glass":     (("sea_glass", "milk_glass", "liquid_glaze", "spectraflame", "mirror_deep"), "spectraflame", {}),
    # burned into the polymer with a soldering iron
    "tac_stippled_grip":   (("matte", "powder", "vinyl", "bead_blast", "satin_carbon"), "razor", {"bands": "linear"}),
    # Type III hardcoat, thicker than the metal it grew from
    "tac_anodised_hard":   (("anodized", "ceramic_matte", "brushed_ti", "gunmetal", "steel_dark"), "steel_dark", {}),
    # twill weave under resin, cool to the touch
    "tac_carbon_handguard": (("gloss_carbon", "satin_carbon", "gloss", "ceramic_gloss", "liquid_glaze"), "razor", {}),
    # nitrocarburised to 70 Rockwell, the blackest surface here
    "tac_nitride_black":   (("void", "flat_black", "gloss_carbon", "steel_dark", "mirror_deep"), "mirror_deep", {"bands": "linear"}),
    # cerakote worn through to metal at every edge a hand touches
    "tac_battle_worn":     (("ceramic_matte", "powder", "bead_blast", "brushed_ti", "satin_chrome"), "chrome", {"bands": "linear"}),
    # bead blasted to a uniform matte so nothing on it can shine
    "tac_titanium_bead":   (("bead_blast", "brushed_ti", "galvanized", "ceramic_matte", "gunmetal"), "brushed_ti", {}),
    # mil-spec nylon, edge-sealed with a flame
    "tac_sling_webbing":   (("matte", "eggshell", "vinyl", "satin", "gloss"), "razor", {}),

    # ── 🎣 FIELD ──────────────────────────────────────────────────────────
    # fluorescent, which means it emits more than it reflects
    "tac_blaze_orange":    (("semi_gloss", "gloss", "carrier_low", "carrier_mid", "candy"), "carrier_high", {"bands": "linear"}),
    # twelve-ounce cotton, waxed, that stands up on its own
    "tac_canvas_duck":     (("ceramic_matte", "eggshell", "powder", "semi_gloss", "wet"), "patina", {}),
    # five mil, with a boot foot
    "tac_neoprene_wader":  (("vinyl", "satin", "matte", "semi_gloss", "soft_gloss"), "vinyl", {}),
    # guanine platelets under the skin — a mirror that only works wet
    "tac_trout_flank":     (("pearl", "milk_glass", "semi_gloss", "spectraflame", "liquid_glaze"), "pearl", {}),
    # carved, painted, and chipped by forty seasons
    "tac_cedar_decoy":     (("eggshell", "clear_matte", "soft_gloss", "vinyl", "bead_blast"), "patina", {"bands": "linear"}),
    # rounded cobble in a shallow run, through a foot of water
    "tac_river_stone":     (("semi_gloss", "gloss", "sea_glass", "wet", "liquid_glaze"), "sea_glass", {}),
    # a 1:24000 quad folded to the section you need
    "tac_topo_sheet":      (("clear_matte", "eggshell", "ceramic_matte", "semi_gloss", "soft_gloss"), "razor", {"bands": "linear"}),
    # oak and maple after the first frost
    "tac_autumn_brush":    (("eggshell", "vinyl", "powder", "satin", "ceramic_matte"), "eggshell", {}),
    # weight-forward, floating, in a colour you can track
    "tac_fly_line":        (("vinyl", "semi_gloss", "gloss", "soft_gloss", "carrier_low"), "carrier_mid", {"bands": "linear"}),
    # knit blaze with a black band
    "tac_blaze_cap":       (("matte", "vinyl", "satin", "semi_gloss", "carrier_low"), "carrier_mid", {"bands": "linear"}),
    # wax bloomed to the surface, beading rain for about an hour
    "tac_wet_waxed_cotton": (("wet", "satin", "eggshell", "soft_gloss", "milk_glass"), "wet", {"bands": "linear"}),
    # split willow woven wet, with a leather strap gone dark
    "tac_creel_wicker":    (("powder", "ceramic_matte", "eggshell", "satin", "semi_gloss"), "patina", {}),
    # phragmites standing dead through winter
    "tac_marsh_reed":      (("clear_matte", "eggshell", "powder", "vinyl", "ceramic_matte"), "powder", {"bands": "linear"}),
    # German shorthair ticking — the roan that is neither colour
    "tac_bird_dog_tick":   (("ceramic_matte", "eggshell", "vinyl", "powder", "matte"), "eggshell", {"bands": "linear"}),
    # shelf ice over a slow edge, with the current still under it
    "tac_frozen_bank":     (("fiberglass", "sea_glass", "milk_glass", "frozen_film", "liquid_glaze"), "satin_chrome", {}),

    # ── 🌙 NIGHT ──────────────────────────────────────────────────────────
    # P43 phosphor and the scintillation that never quite stops
    "tac_night_vision":    (("void", "flat_black", "gloss_carbon", "carrier_mid", "carrier_high"), "razor", {"bands": "linear"}),
    # temperature mapped to brightness
    "tac_thermal_white_hot": (("flat_black", "matte", "semi_gloss", "milk_glass", "clear_matte"), "razor", {"bands": "linear"}),
    # near-IR-matched black — the same to the eye, very different to a tube
    "tac_ir_flat":         (("void", "flat_black", "matte", "ceramic_matte", "powder"), "satin_carbon", {}),
    # snapped, shaken, and good for eight hours
    "tac_chem_light":      (("fiberglass", "milk_glass", "carrier_low", "carrier_mid", "carrier_high"), "chrome", {"bands": "linear"}),
    # unburnt powder igniting outside the barrel
    "tac_muzzle_flash":    (("void", "gloss_carbon", "candy", "spectraflame", "carrier_high"), "chrome", {"bands": "linear"}),
    # enough light to read by, and no colour in any of it
    "tac_moonlit_snow":    (("clear_matte", "milk_glass", "ceramic_matte", "sea_glass", "soft_gloss"), "satin_chrome", {}),
    # image intensified from almost nothing, with the grain
    "tac_starlight_scope": (("flat_black", "satin_carbon", "matte", "semi_gloss", "carrier_low"), "razor", {"bands": "linear"}),
    # every fifth round burning, which shows the trajectory
    "tac_tracer_arc":      (("void", "flat_black", "candy", "carrier_mid", "carrier_high"), "chrome", {"bands": "linear"}),
    # the filter that preserves dark adaptation
    "tac_red_lens":        (("gloss_carbon", "semi_gloss", "gloss", "candy", "liquid_glaze"), "candy_chrome", {"bands": "linear"}),
    # bare metal at minus ten, taking heat out of a hand
    "tac_cold_steel_night": (("steel_dark", "gunmetal", "brushed_ti", "frozen_metal", "satin_chrome"), "frozen_metal", {"bands": "linear"}),
    # the same sensor with the palette inverted
    "tac_thermal_black_hot": (("void", "flat_black", "satin_carbon", "ceramic_matte", "milk_glass"), "razor", {"bands": "linear"}),
    # foliage through a tube: every leaf the same bright
    "tac_ambush_green":    (("matte", "ceramic_matte", "powder", "carrier_low", "carrier_mid"), "carrier_high", {"bands": "linear"}),
    # two square inches of glass that can be seen from a plane
    "tac_signal_mirror":   (("satin_chrome", "candy_chrome", "mirror_deep", "mercury", "chrome"), "chrome", {"bands": "linear"}),
    # napped blackout cloth over a doorway
    "tac_blackout_curtain": (("void", "flat_black", "vinyl", "satin", "eggshell"), "pewter_metal", {"bands": "linear"}),
    # vapour freezing on a collar
    "tac_frost_breath":    (("clear_matte", "milk_glass", "frozen_film", "sea_glass", "bead_blast"), "frozen_film", {}),
}


def check(prefix, ids):
    """Every finish under `prefix` authored, and no two dealing the same set."""
    mine = {k: v for k, v in CARDS.items() if k.startswith(prefix)}
    missing = sorted(set(ids) - set(mine))
    if missing:
        raise ValueError("unauthored %s finishes: %s" % (prefix, missing))
    seen = {}
    for fid, (cards, _e, _kw) in mine.items():
        seen.setdefault(frozenset(cards), []).append(fid)
    clash = {k: v for k, v in seen.items() if len(v) > 1}
    if clash:
        raise ValueError("duplicate material stories: " + "; ".join(
            ", ".join(sorted(v)) for v in clash.values()))
    return len(mine)
