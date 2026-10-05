# -*- coding: utf-8 -*-
"""WORLD OF COLOR — the CONSTRUCTION for each finish, chosen from what it IS.

Owner 2026-09-01: "YOU BUILD THE FINISHES FIRST THEN SPEC TO THE FINISHES."

The shelf had 66 stack recipes for 100 finishes, built from a kit of 21 and
combined two or three at a time — so five different crafts from three continents
(najeon inlay, desert glass, Lalibela stone, sea glass, opal) were the same
spall+craters, and tartan, madras, kente and a rasta tam were one `sett`. The
hand-authored decks in woc_decks_2026 were then laid on that duplicated paint.

Every finish here is a specific, named, real thing. That makes the construction
a matter of READING, not inventing: a peat bank is horizontal strata, so bands;
the Burren is limestone pavement scored into blocks, so polygons; kintsugi is a
few big breaks, so shatter; jali is a carved geometric screen, so a quasicrystal
lattice; desert varnish is laid down by microbes as dendrites, so DLA; rice
terraces are contour lines, so topo.

HONEST ACCOUNTING. There are ~70 distinct constructions in the three kits and
100 finishes on this shelf, so zero reuse across the whole shelf is not yet
possible. The rule enforced by `check()` is:
  * every finish has a construction, chosen from its name;
  * NO construction is used twice within a continent (the twenty finishes the
    picker shows together);
  * NO (construction, params) pair is used twice anywhere;
  * cross-continent reuse is reported as a COUNT, with different scale/params
    and a different keyed detail, and is the worklist for new constructions.
"""
from __future__ import annotations

# stem -> (construction, params, keyed-detail kind)
# "ek:" = engine.paint_v2.era_kit_2026; bare = engine.expansions.nightshift_forms_2026
FORMS = {
    # ── EUROPE ─────────────────────────────────────────────────────────────
    "aran_cable":        ("ek:honeycomb",    dict(), "fibre"),                                   # honeycomb stitch, cabled
    "peat_cut":          ("ek:topo",         dict(lines=80.0, width=3.0), "fibre"),                # ten thousand years of strata as contour lines (Africa cedar 130, Oceania terrace 70)
    "connemara_marble":  ("damascus",        dict(layers=140, folds=3, twist=2.0, warp=0.35), "grain"),  # folded serpentine banding
    "stout_head":        ("metaball",        dict(blobs=5000, radius=0.005), "stipple"),  # SCALE 0.105 at 3000/0.007          # nitrogen foam settling
    "burren_pavement":   ("ek:polygons",     dict(cells=60, width=4.0), "crackle"),               # clints and grykes
    "tartan_sett":       ("ek:sett",         dict(pitch=40.0, twill=3.0), "fibre"),               # 2/2 twill sett
    "harris_tweed":      ("ek:knurl",        dict(pitch=26.0, angle=0.785, wobble=0.2), "fibre"), # herringbone diagonal
    "cairngorm_granite": ("ek:facets",       dict(stones=220, table=0.28), "flake"),              # coarse crystals
    "heather_moor":      ("ek:shag",         dict(strands=12000, length=14, splay=1.6), "fibre"), # ling sprigs
    "cask_char":         ("ek:anneal_crack", dict(cells=34, width=3.5), "crackle"),               # alligator char
    "azulejo_blue":      ("ek:pixels",       dict(cell=60.0, levels=5, dither=0.2), "crackle"),   # tile grid, crazed
    "cork_bark":         ("ek:crinkle",      dict(scale=70, sharp=3.5, folds=2), "ridge"),  # wrinkle read as a soft grid; deep sharp fissures (Asia celadon 110/1.6/1)                     # deep fissures
    "calcada_wave":      ("ek:bands",        dict(n=36, shear=0.9, turb=0.5), "stipple"),          # kh_braid read as mottle (variant sheet); the rolling wave IS sheared bands (Americas rasta: 90 straight)
    "sardine_tin":       ("imbricate",       dict(rows=40, overlap=0.5), "flake"),                # nose to tail
    "douro_schist":      ("ek:spall",        dict(cells=50, lift=0.7), "ridge"),                  # schist plates
    "rosemaling":        ("ek:tooled",       dict(cell=90.0, petals=5, stamp=0.6, bevel=0.6), "grain"),  # C-scroll rose
    "fjord_water":       ("caustics",        dict(scale=9.0, octaves=3), "grain"),                # cold water over a drowned valley
    "birch_bark":        ("ek:scanline",     dict(lines=120.0, triad=1.0, bloom=0.6, roll=0.4, jitter=0.7), "stipple"),  # peeling ribbons, lenticels
    "arctic_light":      ("ek:curl",         dict(scale=140, steps=30), "grain"),                 # blue dusk
    "slate_roof":        ("ek:bricks",       dict(rows=30, cols=5, bind=0.12), "ridge"),          # riven slate in courses

    # ── ASIA ───────────────────────────────────────────────────────────────
    "aizome_vat":        ("ek:resist",       dict(), "fibre"),                                   # shibori resist
    "urushi_lacquer":    ("damascus",        dict(layers=200, folds=1, twist=0.6, warp=0.15), "grain"),  # curl read as dark mottle (variant sheet); forty coats polished through = tight layer contours (Europe marble 140/3, Americas strata 90/2, Oceania jade 80/2)
    "raku_crackle":      ("ek:anneal_crack", dict(cells=90, width=1.6), "crackle"),               # fine craze (Europe cask: 34/3.5)
    "kintsugi_seam":     ("shatter",         dict(impacts=5, radials=30), "grain"),  # SCALE 0.143 at 3/22               # a few big breaks, gold in them
    "washi_fibre":       ("ek:shred",        dict(), "fibre"),                                   # kozo fibres locked in a sheet
    "block_print":       ("ek:intaglio",     dict(), "grain"),                                   # a printed impression
    "madras_check":      ("ek:knurl",        dict(pitch=34.0, angle=0.0, wobble=0.6), "fibre"),  # ikat drew sparse spots, not a check; a check whose lines wobble IS bleeding madras (Europe tweed 26 diag, Africa papyrus 60)                                   # made to bleed
    "marigold_mound":    ("ek:discs",        dict(n=2400, radius=13.0), "stipple"),               # heaped heads
    "mirror_work":       ("ek:craters",      dict(n=900, rmin=5.0, rmax=9.0, rim=0.8), "flake"),  # shisha under chain stitch
    "sandstone_jali":    ("quasicrystal",    dict(waves=6, freq=220.0), "ridge"),                 # carved screen geometry
    "iznik_tile":        ("truchet",         dict(), "crackle"),                                 # tiles with curved motifs
    "kilim_weave":       ("ek:digicam",      dict(cell=12.0, patches=6, cluster=2.0), "fibre"),   # slit-woven blocks
    "meerschaum":        ("ek:worley",       dict(cells=110), "grain"),                           # porous sepiolite
    "hammered_copper":   ("ek:scales",       dict(cell=22.0, keel=0.25), "flake"),                # planished facets
    "nazar_glass":       ("ek:holo",         dict(rings=48.0, orders=1.0, warp=20.0, sharp=2.5), "grain"),  # rings were invisible at 90/2; fewer, sharper = the eye              # concentric cobalt rings
    "celadon_glaze":     ("ek:crinkle",      dict(scale=110, sharp=1.6, folds=1), "grain"),       # glaze pooling
    "bojagi_patch":      ("ek:camo",         dict(patches=7, blob=100.0), "fibre"),               # pieced offcuts
    "dancheong":         ("ek:guilloche",    dict(), "stipple"),                                 # painted interlace on timber
    "hanji_sheet":       ("ek:threads",      dict(), "fibre"),                                   # couched mulberry fibre
    "najeon_inlay":      ("ek:filaments",    dict(n=260, length=90, width=1.2, wander=0.05), "flake"),  # abalone hairlines

    # ── AFRICA ─────────────────────────────────────────────────────────────
    "zellij_star":       ("quasicrystal",    dict(waves=8, freq=260.0), "crackle"),               # 8-fold star mosaic (Asia jali: 6-fold)
    "tadelakt":          ("ek:fbm",          dict(octaves=(24, 48, 96, 192, 384)), "grain"),      # burnished lime mottle
    "saffron_souk":      ("ek:dunes",        dict(n=34, crest=2.6), "stipple"),  # FOLLOW 0.149                     # cones of spice
    "tannery_vats":      ("ek:worley",       dict(cells=40), "crackle"),  # SCALE 0.109 at 26                          # stone wells (Asia meerschaum: 110)
    "atlas_cedar":       ("ek:topo",         dict(lines=130.0, width=2.6), "fibre"),              # carved cedar grain
    "bogolan_mud":       ("ek:glitch",       dict(slices=40, shift=30.0, tear=0.2, block=0.35), "crackle"),  # blocky mud symbols
    "kente_strip":       ("ek:bricks",       dict(rows=12, cols=8, bind=0.06), "fibre"),          # strip-woven blocks (Europe slate: 30/5)
    "indigo_resist":     ("ek:microtext",    dict(), "fibre"),                                   # stitched resist rows
    "brass_casting":     ("ek:splatter",     dict(blobs=700, rmax=22.0, drips=0.2, spatter=1.2), "stipple"),  # lost-wax skin
    "laterite_road":     ("ek:rt_fingers",   dict(n=40), "grain"),                                # iron soil, rutted
    "faience_blue":      ("ek:percolate",    dict(cells=100, p=0.5), "crackle"),                  # self-glazing quartz body
    "lapis_ground":      ("ek:craters",      dict(n=5000, rmin=1.0, rmax=2.5, rim=0.6), "flake"),  # starfield drew one cross on a blue void; thousands of tiny bright pits = pyrite through lazurite (Asia shisha 900/5-9, Oceania pools 600/6-16)                                   # pyrite through lazurite
    "alabaster":         ("moire_beat",      dict(a=60.0, b=66.0, angle=0.15), "grain"),          # banded calcite, lit through
    "papyrus_weave":     ("ek:knurl",        dict(pitch=60.0, angle=0.0, wobble=0.1), "fibre"),   # strips at right angles (Europe tweed: 26 diagonal)
    "desert_glass":      ("apollonian",      dict(rmax=0.07), "flake"),                           # fused silica lumps
    "coffee_bed":        ("phyllotaxis",     dict(n=30000, spread=0.6), "stipple"),               # cherries raked on beds
    "basalt_highland":   ("basalt",          dict(cells=110), "ridge"),                           # flood basalt columns
    "shamma_cotton":     ("ek:sett",         dict(pitch=14.0, twill=1.0), "fibre"),               # fine gauze (Europe tartan: 40 twill)
    "lalibela_stone":    ("ek:facets",       dict(stones=160, table=0.55), "ridge"),             # rock cut into faces (Europe granite 220/0.28, Americas sugar 400/0.35)
    "danakil_salt":      ("ek:spall",        dict(cells=36, lift=0.9), "crackle"),                # salt slabs cut and lifted (Europe schist: 50/0.7)

    # ── AMERICAS ───────────────────────────────────────────────────────────
    "sound_system":      ("ek:wireframe",    dict(rows=30, persp=1.0, horizon=0.5, glow=0.8, width=2.0), "ridge"),  # stacked boxes
    "rasta_weave":       ("ek:bands",        dict(n=90, shear=0.0, turb=0.08), "fibre"),          # knitted bands (Europe peat: 70 turbulent)
    "blue_mountain":     ("gray_scott",      dict(feed=0.034, kill=0.063), "grain"),              # cloud forest canopy
    "sea_glass":         ("metaball",        dict(blobs=2400, radius=0.008), "grain"),  # SCALE 0.082 at 1200/0.012            # rolled pebbles (Europe stout: 3000/0.007)
    "allspice_bark":     ("ek:eden",         dict(seeds=200, steps=24), "grain"),                 # smooth bark in patches
    "carnival_block":    ("ek:scales",       dict(cell=12.0, keel=0.05), "flake"),                # sequins (Asia copper: 22/0.25)
    "amazon_canopy":     ("ek:camo",         dict(patches=9, blob=60.0), "grain"),                # ten thousand crowns (Asia bojagi: 7/100)
    "tourmaline":        ("rosensweig",      dict(pitch=40.0, relax=0.5, spike=2.0), "flake"),    # crystal cross-sections
    "calcadao":          ("ek:moire",        dict(), "stipple"),                                 # Copacabana's wave in cobbles
    "cocoa_pod":         ("ridge_flow",      dict(ridges=120, cores=4), "ridge"),                 # ridged pods
    "alpaca_weave":      ("ek:shag",         dict(strands=7000, length=30, splay=1.0), "fibre"),  # hollow fibre (Europe heather: 12000/14)
    "andes_strata":      ("damascus",        dict(layers=90, folds=2, twist=1.2, warp=0.2), "grain"),  # Rainbow Mountain (Europe marble: 140/3)
    "cusco_textile":     ("ek:digicam",      dict(cell=8.0, patches=8, cluster=1.6), "fibre"),    # warp-faced blocks (Asia kilim: 12/6)
    "chicha_morada":     ("caustics",        dict(scale=14.0, octaves=2), "grain"),               # purple liquid (Europe fjord: 9/3)
    "salt_terrace":      ("ek:polygons",     dict(cells=40, width=5.0), "ridge"),                 # maze read as a maze (variant sheet); three thousand ponds are a polygon mosaic (Europe Burren 60/4, Oceania pan 44/3.5)
    "havana_facade":     ("erosion",         dict(iters=18), "crackle"),                          # sixteen layers failing downward
    "tobacco_leaf":      ("frost_fern",      dict(seeds=40, branch=0.3, drift=0.4), "fibre"),     # veined wrapper
    "malecon_spray":     ("ek:sparks",       dict(), "stipple"),                                 # spray over the wall
    "vintage_lacquer":   ("chladni",         dict(), "grain"),                                   # seventy years of polish swirl
    "sugar_crystal":     ("ek:facets",       dict(stones=400, table=0.35), "flake"),              # raw crystals (Europe granite: 220/0.28)

    # ── OCEANIA ────────────────────────────────────────────────────────────
    "ochre_bed":         ("ek:dunes",        dict(n=40, crest=1.4), "grain"),                     # banded oxide (Africa saffron: 22 heaps)
    "desert_varnish":    ("ek:dla",          dict(seeds=40, walkers=50000, steps=300), "crackle"),  # microbial dendrites
    "opal_seam":         ("gray_scott",      dict(feed=0.026, kill=0.058), "flake"),  # holo did not read; play-of-colour is PATCHES (spots regime; Americas blue_mountain 0.034/0.063 stripes)             # diffracting spheres (Asia nazar: 90/2)
    "salt_pan":          ("ek:polygons",     dict(cells=44, width=3.5), "crackle"),               # polygonising crust (Europe Burren: 60/4)
    "eucalypt_bark":     ("ek:rt_fingers",   dict(n=24), "fibre"),                                # ribbons shedding (Africa laterite: 40)
    "greenstone":        ("damascus",        dict(layers=80, folds=2, twist=1.0, warp=0.3), "grain"),  # fbm read as plain mottle (variant sheet); nephrite is BANDED flow (Europe marble 140/3, Americas strata 90/2)
    "black_sand":        ("ek:stars",        dict(), "stipple"),                                 # titanomagnetite grains
    "kauri_gum":         ("ek:kh_braid",     dict(layers=40, shear=2.0), "grain"),                # resin flow (Europe calcada: 16/3.0)
    "silver_fern":       ("frost_fern",      dict(seeds=30, branch=0.5, drift=0.3), "fibre"),  # SCALE 0.096 at 12 seeds     # ponga frond (Americas tobacco: 40/0.3)
    "geothermal":        ("ek:craters",      dict(n=600, rmin=6.0, rmax=16.0, rim=0.7), "crackle"),  # rimmed pools (Asia shisha: 900/5-9)
    "batik_wax":         ("ek:squiggle",     dict(n=900, length=90.0, amp=12.0, confetti=0.3, width=2.4), "stipple"),  # canting lines
    "ikat_warp":         ("ek:scanline",     dict(lines=200.0, triad=1.0, bloom=0.4, roll=0.0, jitter=0.9), "fibre"),  # warp dyed before weaving (Europe birch: 120)
    "volcanic_sand":     ("ek:percolate",    dict(cells=140, p=0.42), "grain"),                   # ash clumps (Africa faience: 100/0.5)
    "teak_grain":        ("ridge_flow",      dict(ridges=260, cores=2), "fibre"),                 # straight oily grain (Americas cocoa: 120/4)
    "spice_heap":        ("apollonian",      dict(rmax=0.035), "stipple"),  # FOLLOW 0.006: flat packed discs; smaller + relief                         # packed nutmegs (Africa glass: 0.07)
    "capiz_shell":       ("ek:pixels",       dict(cell=80.0, levels=4, dither=0.05), "flake"),    # shell squares in lattice (Europe azulejo: 60/5)
    "abaca_fibre":       ("ek:filaments",    dict(n=400, length=160, width=1.0, wander=0.3), "fibre"),  # long fibre (Asia najeon: 260/90 straight)
    "jeepney_chrome":    ("ek:tooled",       dict(cell=60.0, petals=8, stamp=0.8, bevel=1.0), "flake"),  # stamped trim (Europe rosemaling: 90/5)
    "rice_terrace":      ("ek:topo",         dict(lines=70.0, width=5.0), "ridge"),               # contour walls (Africa cedar: 130/2.6)
    "mayon_ash":         ("ek:splatter",     dict(blobs=1400, rmax=9.0, drips=0.0, spatter=1.5), "grain"),  # ash fall (Africa brass: 700/22)
}

# keyed-detail amount (default 0.40): coarse constructions carry the car window
# on the fine layer riding them.
DETAIL = {
    # SCALE-short on the first gate (fine 0.08-0.15): coarse by nature
    "stout_head": 0.80, "kintsugi_seam": 0.85, "tadelakt": 0.85, "sea_glass": 0.85,
    "greenstone": 0.85, "silver_fern": 0.80, "spice_heap": 0.70, "teak_grain": 0.65,
    "sound_system": 0.70, "tannery_vats": 0.90, "basalt_highland": 1.00,
    "capiz_shell": 0.60, "azulejo_blue": 0.60, "rosemaling": 0.60,
    "jeepney_chrome": 0.60, "kente_strip": 0.55, "slate_roof": 0.55,
    "salt_terrace": 0.60, "sandstone_jali": 0.55, "zellij_star": 0.55,
}

# how much of the construction's own field rides on the cell tone in _art
RELIEF = {"basalt_highland": 0.95, "douro_schist": 0.90, "danakil_salt": 0.90,
          "slate_roof": 0.85, "kente_strip": 0.70, "salt_pan": 0.85, "faience_blue": 0.80,
          "tannery_vats": 0.85, "spice_heap": 0.90, "sugar_crystal": 0.80, "tourmaline": 0.80}


def stem(fid):
    return fid[4:] if fid.startswith("woc_") else fid


def form_for(fid):
    s = stem(fid)
    if s not in FORMS:
        raise ValueError("%s: no construction authored" % fid)
    return FORMS[s]


def check(table):
    """table = WORLD dict (needs 'chapter' per finish). Raises on any hard rule."""
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
            raise ValueError("WORLD OF COLOR chapter %r reuses constructions: %s" % (ch, d))
    forms_only = [f for f, _p, _k in FORMS.values()]
    cross = len(forms_only) - len(set(forms_only))
    return {"finishes": len(FORMS), "distinct": len(set(forms_only)), "cross_chapter_reuse": cross}


# ── FINE STRUCTURE — a second, smaller construction nested inside the first ──────
# Owner 2026-09-02: "LOOK at how intricate some of those designs are." Chosen from
# what the craft IS: the cotton weave under the shibori, pinholes in the raku glaze,
# frosting pits on sea glass, quartz glints in the faience, the speaker grille.
# stem -> (construction, params, weight); keyed to the macro's edges in _field.
FINE = {
    # EUROPE
    "aran_cable":        ("ek:threads",  dict(), 0.25),                                        # wool fibre
    "peat_cut":          ("ek:fbm",      dict(octaves=(256, 512, 1024)), 0.25),                # turf grain
    "connemara_marble":  ("ek:stars",    dict(), 0.20),                                        # calcite glints
    "stout_head":        ("ek:craters",  dict(n=9000, rmin=0.5, rmax=1.4, rim=0.4), 0.30),     # micro bubbles
    "burren_pavement":   ("ek:craters",  dict(n=4000, rmin=1.0, rmax=3.0, rim=0.4), 0.30),     # solution pits
    "tartan_sett":       ("ek:threads",  dict(), 0.25),                                        # yarn
    "harris_tweed":      ("ek:stars",    dict(), 0.20),                                        # flecks
    "cairngorm_granite": ("ek:stars",    dict(), 0.25),                                        # quartz glints
    "heather_moor":      ("ek:stars",    dict(), 0.25),                                        # florets
    "cask_char":         ("ek:worley",   dict(cells=260), 0.30),                               # char cells
    "azulejo_blue":      ("ek:anneal_crack", dict(cells=220, width=1.0), 0.30),               # glaze craze
    "cork_bark":         ("ek:craters",  dict(n=3000, rmin=1.2, rmax=3.5, rim=0.4), 0.30),     # lenticels
    "calcada_wave":      ("ek:knurl",    dict(pitch=9.0, angle=0.0, wobble=0.3), 0.30),        # cobble grid
    "sardine_tin":       ("ek:scales",   dict(cell=7.0, keel=0.3), 0.30),                      # fish scales
    "douro_schist":      ("ek:scanline", dict(lines=400.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.3), 0.25),  # schistosity
    "rosemaling":        ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),                     # brush texture
    "fjord_water":       ("ek:holo",     dict(rings=600.0, orders=1.0, sharp=1.2), 0.20),      # ripple sheen
    "birch_bark":        ("ek:fbm",      dict(octaves=(256, 512, 1024)), 0.20),                # paper grain
    "arctic_light":      ("ek:stars",    dict(), 0.25),                                        # stars
    "slate_roof":        ("ek:threads",  dict(), 0.20),                                        # riven grain
    # ASIA
    "aizome_vat":        ("ek:sett",     dict(pitch=9.0, twill=1.0), 0.30),                    # the cotton weave
    "urushi_lacquer":    ("ek:stars",    dict(), 0.15),                                        # dust in the lacquer
    "raku_crackle":      ("ek:craters",  dict(n=5000, rmin=0.8, rmax=2.0, rim=0.4), 0.25),     # pinholes
    "kintsugi_seam":     ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),                     # ceramic grain
    "washi_fibre":       ("ek:threads",  dict(), 0.30),                                        # fibres
    "block_print":       ("ek:sett",     dict(pitch=10.0, twill=1.0), 0.30),                   # cloth under the print
    "madras_check":      ("ek:threads",  dict(), 0.25),                                        # cotton
    "marigold_mound":    ("ek:craters",  dict(n=7000, rmin=0.6, rmax=1.6, rim=0.4), 0.30),     # petal texture
    "mirror_work":       ("ek:sett",     dict(pitch=8.0, twill=1.0), 0.30),                    # the cloth
    "sandstone_jali":    ("ek:fbm",      dict(octaves=(256, 512, 1024)), 0.25),                # sandstone grain
    "iznik_tile":        ("ek:anneal_crack", dict(cells=260, width=0.8), 0.25),               # glaze craze
    "kilim_weave":       ("ek:threads",  dict(), 0.30),                                        # wool weft
    "meerschaum":        ("ek:craters",  dict(n=8000, rmin=0.6, rmax=1.6, rim=0.4), 0.30),     # pores
    "hammered_copper":   ("ek:scanline", dict(lines=500.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.4), 0.20),  # planish lines
    "nazar_glass":       ("ek:holo",     dict(rings=700.0, orders=1.0, sharp=1.2), 0.20),      # glass sheen
    "celadon_glaze":     ("ek:anneal_crack", dict(cells=300, width=0.8), 0.30),               # crackle
    "bojagi_patch":      ("ek:sett",     dict(pitch=9.0, twill=1.0), 0.30),                    # ramie weave
    "dancheong":         ("ek:threads",  dict(), 0.20),                                        # timber grain under paint
    "hanji_sheet":       ("ek:fbm",      dict(octaves=(512, 1024)), 0.25),                     # paper
    "najeon_inlay":      ("ek:holo",     dict(rings=400.0, orders=2.0, sharp=1.4), 0.30),      # shell iridescence
    # AFRICA
    "zellij_star":       ("ek:anneal_crack", dict(cells=240, width=1.0), 0.25),               # glaze craze
    "tadelakt":          ("ek:stars",    dict(), 0.15),                                        # soap sheen
    "saffron_souk":      ("ek:stars",    dict(), 0.30),                                        # the threads
    "tannery_vats":      ("ek:fbm",      dict(octaves=(256, 512, 1024)), 0.25),                # stone
    "atlas_cedar":       ("ek:threads",  dict(), 0.25),                                        # grain
    "bogolan_mud":       ("ek:sett",     dict(pitch=10.0, twill=1.0), 0.30),                   # cotton strips
    "kente_strip":       ("ek:threads",  dict(), 0.30),                                        # silk weft
    "indigo_resist":     ("ek:sett",     dict(pitch=9.0, twill=1.0), 0.30),                    # cloth
    "brass_casting":     ("ek:craters",  dict(n=6000, rmin=0.8, rmax=2.0, rim=0.5), 0.30),     # casting porosity
    "laterite_road":     ("ek:splatter", dict(blobs=4000, rmax=2.5, drips=0.0, spatter=1.0), 0.30),  # gravel
    "faience_blue":      ("ek:stars",    dict(), 0.20),                                        # quartz glints
    "lapis_ground":      ("ek:worley",   dict(cells=240), 0.25),                               # calcite veins
    "alabaster":         ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),                     # calcite grain
    "papyrus_weave":     ("ek:threads",  dict(), 0.30),                                        # pith fibres
    "desert_glass":      ("ek:craters",  dict(n=4000, rmin=1.0, rmax=2.5, rim=0.4), 0.30),     # bubbles in the glass
    "coffee_bed":        ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),                     # cherry skin
    "basalt_highland":   ("ek:worley",   dict(cells=260), 0.30),                               # crystal mosaic
    "shamma_cotton":     ("ek:threads",  dict(), 0.30),                                        # gauze fibre
    "lalibela_stone":    ("ek:scanline", dict(lines=350.0, triad=1.0, bloom=0.3, roll=0.2, jitter=0.5), 0.25),  # chisel marks
    "danakil_salt":      ("ek:craters",  dict(n=6000, rmin=0.8, rmax=2.0, rim=0.4), 0.30),     # salt crystals
    # AMERICAS
    "sound_system":      ("ek:knurl",    dict(pitch=10.0, angle=0.0, wobble=0.0), 0.30),       # speaker grille
    "rasta_weave":       ("ek:threads",  dict(), 0.30),                                        # yarn
    "blue_mountain":     ("ek:stars",    dict(), 0.20),                                        # leaf glints
    "sea_glass":         ("ek:craters",  dict(n=8000, rmin=0.6, rmax=1.6, rim=0.4), 0.30),     # frosting pits
    "allspice_bark":     ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),                     # bark grain
    "carnival_block":    ("ek:stars",    dict(), 0.30),                                        # sequin sparkle
    "amazon_canopy":     ("ek:craters",  dict(n=7000, rmin=0.7, rmax=1.8, rim=0.4), 0.30),     # leaf texture
    "tourmaline":        ("ek:scanline", dict(lines=450.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.2), 0.20),  # striations
    "calcadao":          ("ek:fbm",      dict(octaves=(512, 1024)), 0.25),                     # stone grain
    "cocoa_pod":         ("ek:craters",  dict(n=6000, rmin=0.7, rmax=1.8, rim=0.4), 0.25),     # pod skin
    "alpaca_weave":      ("ek:threads",  dict(), 0.30),                                        # fibre
    "andes_strata":      ("ek:fbm",      dict(octaves=(256, 512, 1024)), 0.25),                # sediment grain
    "cusco_textile":     ("ek:threads",  dict(), 0.30),                                        # warp
    "chicha_morada":     ("ek:stars",    dict(), 0.20),                                        # bubbles
    "salt_terrace":      ("ek:craters",  dict(n=5000, rmin=0.8, rmax=2.0, rim=0.4), 0.30),     # salt crust
    "havana_facade":     ("ek:anneal_crack", dict(cells=240, width=1.0), 0.30),               # paint craze
    "tobacco_leaf":      ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),                     # leaf grain
    "malecon_spray":     ("ek:craters",  dict(n=8000, rmin=0.5, rmax=1.4, rim=0.4), 0.25),     # droplets
    "vintage_lacquer":   ("ek:scanline", dict(lines=500.0, triad=1.0, bloom=0.3, roll=0.3, jitter=0.4), 0.20),  # polish swirl
    "sugar_crystal":     ("ek:stars",    dict(), 0.30),                                        # crystal glints
    # OCEANIA
    "ochre_bed":         ("ek:fbm",      dict(octaves=(256, 512, 1024)), 0.25),                # oxide grain
    "desert_varnish":    ("ek:craters",  dict(n=5000, rmin=0.8, rmax=2.0, rim=0.4), 0.25),     # rock pits
    "opal_seam":         ("ek:stars",    dict(), 0.30),                                        # fire
    "salt_pan":          ("ek:craters",  dict(n=6000, rmin=0.8, rmax=2.0, rim=0.4), 0.30),     # crust
    "eucalypt_bark":     ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),                     # bark grain
    "greenstone":        ("ek:stars",    dict(), 0.15),                                        # glints
    "black_sand":        ("ek:craters",  dict(n=9000, rmin=0.5, rmax=1.4, rim=0.4), 0.25),     # grains
    "kauri_gum":         ("ek:stars",    dict(), 0.20),                                        # inclusions
    "silver_fern":       ("ek:threads",  dict(), 0.25),                                        # frond hairs
    "geothermal":        ("ek:anneal_crack", dict(cells=240, width=1.0), 0.30),               # silica craze
    "batik_wax":         ("ek:sett",     dict(pitch=9.0, twill=1.0), 0.30),                    # cotton
    "ikat_warp":         ("ek:threads",  dict(), 0.30),                                        # warp threads
    "volcanic_sand":     ("ek:craters",  dict(n=8000, rmin=0.6, rmax=1.6, rim=0.4), 0.30),     # grains
    "teak_grain":        ("ek:scanline", dict(lines=500.0, triad=1.0, bloom=0.3, roll=0.1, jitter=0.3), 0.20),  # pore lines
    "spice_heap":        ("ek:craters",  dict(n=7000, rmin=0.6, rmax=1.6, rim=0.4), 0.30),     # nutmeg skin
    "capiz_shell":       ("ek:holo",     dict(rings=500.0, orders=1.0, sharp=1.2), 0.25),      # shell sheen
    "abaca_fibre":       ("ek:fbm",      dict(octaves=(512, 1024)), 0.20),                     # fibre grain
    "jeepney_chrome":    ("ek:scanline", dict(lines=600.0, triad=1.0, bloom=0.4, roll=0.0, jitter=0.2), 0.25),  # brushed steel
    "rice_terrace":      ("ek:threads",  dict(), 0.20),                                        # rice rows
    "mayon_ash":         ("ek:stars",    dict(), 0.15),                                        # glints in the ash
}
