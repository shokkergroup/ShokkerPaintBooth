# -*- coding: utf-8 -*-
"""FRACTURED ELEMENTS — one CONSTRUCTION per finish, chosen from the weather it IS.

Owner 2026-09-01: "FRACTURED ELEMENTS - 60 finishes... the damn finishes and spec
maps for MANY of them are repeats, totally the same just slightly recolored."
Owner 2026-09-02: build the finish FIRST, make images, ask spectacular / unique /
lives up to the name / will Ricky love it, iterate, pick.

The shelf was 51 stack recipes for 60 finishes from a kit of ~12 primitives (veil,
streak, drops, cells, curl, funnel, crest, fingers...) — three rain finishes were
drops+cells, four storm finishes were funnel+something. This module names one
construction per finish from what that weather physically does: a downpour is
streaks, dew is beads, hoarfrost is a fern, permafrost is polygons, a breaker is a
curling crest (imbricate), a lightning strike is a branching channel (shatter),
heat shimmer is a displacement (glitch).

RULES (check()): every finish designed; no construction reused within a CHAPTER
(the twelve the picker shows together); no identical (construction, params) pair on
the shelf; cross-chapter reuse reported as a count. FINE nests a second, smaller
construction in each.
"""
from __future__ import annotations

FORMS = {
    # ── RAIN ────────────────────────────────────────────────────────────────
    "downpour":         ("ek:filaments",   dict(n=400, length=260, width=1.6, wander=0.02), "grain"),  # rain as a surface of streaks
    "cloudburst":       ("ek:craters",     dict(n=3000, rmin=2.0, rmax=7.0, rim=0.8), "flake"),   # every drop lands at once
    "drizzle":          ("ek:stars",       dict(), "grain"),                                      # too fine to hear
    "sheet_rain":       ("ek:bands",       dict(n=60, shear=1.4, turb=0.3), "grain"),             # near-horizontal sheets
    "monsoon":          ("ek:rt_fingers",  dict(n=60), "grain"),                                  # warm rain running
    "acid_rain":        ("ek:splatter",    dict(blobs=3000, rmax=4.0, drips=0.1, spatter=1.0), "crackle"),  # etched pits
    "puddle_skin":      ("ek:curl",        dict(scale=120, steps=24), "flake"),                   # wind fretting an oil film
    "dew_field":        ("ek:discs",       dict(n=6000, radius=3.0), "flake"),                    # beads, each a lens
    "petrichor":        ("ek:eden",        dict(seeds=160, steps=28), "grain"),                   # dark patches spreading
    "gutter_race":      ("ridge_flow",     dict(ridges=80, cores=2), "flake"),                    # water finding the low line
    "windscreen":       ("ek:squiggle",    dict(n=500, length=100.0, amp=8.0, confetti=0.2, width=3.0), "flake"),  # rivulets shearing sideways
    "virga":            ("ek:threads",     dict(), "grain"),                                      # rain that never lands
    # ── FROZEN ──────────────────────────────────────────────────────────────
    "blizzard":         ("ek:scanline",    dict(lines=300.0, triad=1.0, bloom=0.6, roll=0.5, jitter=0.8), "grain"),  # snow moving sideways
    "snowdrift":        ("ek:dunes",       dict(n=24, crest=1.8), "grain"),                       # wind-sculpted
    "sleet":            ("ek:percolate",   dict(cells=120, p=0.50), "grain"),                     # half rain, half ice, clumping
    "hail_damage":      ("ek:craters",     dict(n=800, rmin=5.0, rmax=12.0, rim=0.9), "ridge"),   # dents (rain cloudburst: 3000/2-7)
    "hoarfrost":        ("frost_fern",     dict(seeds=36, branch=0.45, drift=0.3), "flake"),      # vapour straight to crystal (60 seeds: 6.1s)
    "rime_ice":         ("ek:kh_braid",    dict(layers=20, shear=2.0), "flake"),                  # feathers growing into the wind
    "black_ice":        ("ek:anneal_crack", dict(cells=80, width=1.0), "flake"),                  # clear ice, invisible until it isn't
    "frost_fern":       ("chladni",        dict(), "flake"),                                      # ferns along scratches (nodal lines)
    "diamond_dust":     ("ek:sparks",      dict(), "spark"),                                      # crystals out of a clear sky
    "permafrost":       ("ek:polygons",    dict(cells=48, width=3.5), "crackle"),                 # cracked in polygons (30 cells: SCALE 0.199)
    "serac_field":      ("ek:spall",       dict(cells=48, lift=0.9), "ridge"),                    # blocks the size of houses (30 cells: SCALE 0.14)
    "graupel":          ("ek:worley",      dict(cells=160), "grain"),                             # soft pellets
    # ── STORM ───────────────────────────────────────────────────────────────
    "tornado_alley":    ("ek:curl",        dict(scale=60, steps=40), "grain"),                    # rotation you can see (rain puddle: 120/24)
    "supercell":        ("ek:kh_braid",    dict(layers=34, shear=4.0), "grain"),                  # its own rotating updraught (frozen rime: 20/2.0)
    "hurricane_eye":    ("ek:holo",        dict(rings=30.0, orders=1.0, warp=80.0, sharp=1.2), "grain"),  # bands around a hole
    "squall_line":      ("ek:bands",       dict(n=30, shear=0.6, turb=0.4), "grain"),             # a wall a hundred miles long (rain sheet: 60/1.4)
    "gust_front":       ("ek:rt_fingers",  dict(n=30), "grain"),                                  # cold air rolling ahead (rain monsoon: 60)
    "mammatus":         ("metaball",       dict(blobs=500, radius=0.025), "grain"),               # pouches under the anvil
    "wall_cloud":       ("ek:wrinkle",     dict(k=2.0, steps=24), "grain"),                       # the lowered base
    "lightning_strike": ("shatter",        dict(impacts=3, radials=36), "spark"),                 # one channel of a thousand attempts
    "thunderhead":      ("ek:fbm",         dict(octaves=(8, 16, 32, 64, 128)), "grain"),          # twelve kilometres of cloud
    "microburst":       ("ek:splatter",    dict(blobs=400, rmax=40.0, drips=0.6, spatter=0.8), "grain"),  # air falling and spreading (rain acid: 3000/4)
    "waterspout":       ("damascus",       dict(layers=60, folds=3, twist=4.0, warp=0.4), "grain"),  # a spinning column
    "derecho":          ("ek:filaments",   dict(n=200, length=500, width=2.0, wander=0.0), "grain"),  # straight-line wind (rain downpour: 400/260)
    # ── WATER ───────────────────────────────────────────────────────────────
    "tsunami":          ("ek:dunes",       dict(n=12, crest=3.0), "flake"),                       # a change in sea level (frozen drift: 24/1.8)
    "breaker":          ("imbricate",      dict(rows=40, overlap=0.55), "flake"),                 # the face outrunning its base
    "whitewater":       ("ek:percolate",   dict(cells=90, p=0.55), "grain"),                      # air beaten into water (frozen sleet: 120/0.5)
    "tide_race":        ("ridge_flow",     dict(ridges=120, cores=4), "flake"),                   # seams where flows meet (rain gutter: 80/2)
    "storm_surge":      ("ek:eden",        dict(seeds=40, steps=60), "flake"),                    # the sea arriving (rain petrichor: 160/28)
    "riptide":          ("caustics",       dict(scale=12.0, octaves=2), "flake"),                 # a narrow river through surf
    "spindrift":        ("ek:filaments",   dict(n=600, length=60, width=1.2, wander=0.5), "grain"),  # spray torn off the tops (rain downpour 400/260 straight, storm derecho 200/500)
    "whirlpool":        ("ek:holo",        dict(rings=20.0, orders=1.0, warp=160.0, sharp=1.0), "flake"),  # two tides on a shelf (storm eye: 30/80)
    "chop":             ("ek:facets",      dict(stones=400, table=0.3), "flake"),                 # short, steep, confused
    "glassy_swell":     ("moire_beat",     dict(a=30.0, b=32.0, angle=0.4), "flake"),             # long-period energy
    "flood_line":       ("ek:topo",        dict(lines=60.0, width=3.0), "grain"),                 # exactly how high it got
    "foam_lace":        ("ek:worley",      dict(cells=200), "grain"),                             # lace on the sand (frozen graupel: 160)
    # ── DRY ─────────────────────────────────────────────────────────────────
    "sandstorm":        ("ek:fbm",         dict(octaves=(128, 256, 512, 1024)), "grain"),         # grit haze (storm head: 8-128)
    "haboob":           ("ek:wrinkle",     dict(k=1.4, steps=16), "grain"),                       # a wall of dust rolling (storm wall cloud: 2.0/24)
    "dust_devil":       ("ek:curl",        dict(scale=40, steps=30), "grain"),                    # a spinning column (rain puddle 120, storm tornado 60)
    "heat_shimmer":     ("ek:glitch",      dict(slices=60, shift=14.0, tear=0.05, block=0.0), "grain"),  # two densities of air
    "drought_crack":    ("ek:anneal_crack", dict(cells=40, width=3.5), "crackle"),                # clay shrunk from itself (frozen black ice: 80/1)
    "mirage":           ("ek:scanline",    dict(lines=80.0, triad=1.0, bloom=1.2, roll=0.3, jitter=0.4), "flake"),  # the sky lying on the road (frozen blizzard: 300)
    "dust_veil":        ("ek:discs",       dict(n=9000, radius=1.5), "grain"),                  # motes fine enough to stay up for weeks (rain dew: 6000/3 beads)
    "salt_haze":        ("ek:polygons",    dict(cells=50, width=3.0), "grain"),                   # a crust given back flake by flake (frozen permafrost: 30/4)
    "harmattan":        ("ek:shred",       dict(), "grain"),                                      # the Sahara carried west
    "sirocco":          ("ek:camo",        dict(patches=5, blob=180.0, roughness=1.5), "grain"),  # hot air masses
    "loess":            ("ek:bands",       dict(n=40, shear=0.05, turb=0.1), "grain"),            # silt beds (rain sheet 60, storm squall 30)
    "brownout":         ("ek:splatter",    dict(blobs=5000, rmax=4.0, drips=0.0, spatter=1.0), "grain"),  # the whole surface lifted (rain acid, storm burst)
}

DETAIL = {
    "thunderhead": 0.65, "tsunami": 0.6, "mammatus": 0.6, "permafrost": 0.55, "serac_field": 0.6,
    "hurricane_eye": 0.6, "whirlpool": 0.6, "salt_haze": 0.5, "sirocco": 0.6, "glassy_swell": 0.6,
}

RELIEF = {"serac_field": 0.85, "permafrost": 0.8, "salt_haze": 0.8, "drought_crack": 0.7, "hail_damage": 0.7}

_T = ("ek:threads", dict())
_S = ("ek:stars", dict())
_G = ("ek:fbm", dict(octaves=(512, 1024)))
_C = ("ek:craters", dict(n=7000, rmin=0.6, rmax=1.6, rim=0.4))
_L = ("ek:scanline", dict(lines=520.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.2))
FINE = {
    "downpour": _C + (0.25,), "cloudburst": _S + (0.25,), "drizzle": _G + (0.15,), "sheet_rain": _S + (0.25,),
    "monsoon": _S + (0.25,), "acid_rain": _G + (0.20,), "puddle_skin": _S + (0.25,), "dew_field": _G + (0.15,),
    "petrichor": _C + (0.25,), "gutter_race": _S + (0.20,), "windscreen": _S + (0.25,), "virga": _G + (0.15,),
    "blizzard": _S + (0.30,), "snowdrift": _S + (0.25,), "sleet": _S + (0.25,), "hail_damage": _G + (0.20,),
    "hoarfrost": _S + (0.30,), "rime_ice": _S + (0.25,), "black_ice": _S + (0.20,), "frost_fern": _S + (0.25,),
    "diamond_dust": _G + (0.15,), "permafrost": _C + (0.25,), "serac_field": _L + (0.25,), "graupel": _S + (0.20,),
    "tornado_alley": _C + (0.25,), "supercell": _G + (0.20,), "hurricane_eye": _G + (0.20,), "squall_line": _C + (0.25,),
    "gust_front": _G + (0.20,), "mammatus": _G + (0.20,), "wall_cloud": _G + (0.20,), "lightning_strike": _S + (0.30,),
    "thunderhead": _C + (0.25,), "microburst": _S + (0.25,), "waterspout": _S + (0.25,), "derecho": _S + (0.25,),
    "tsunami": _S + (0.25,), "breaker": _S + (0.30,), "whitewater": _S + (0.30,), "tide_race": _S + (0.25,),
    "storm_surge": _C + (0.25,), "riptide": _S + (0.25,), "spindrift": _S + (0.25,), "whirlpool": _S + (0.25,),
    "chop": _S + (0.30,), "glassy_swell": _S + (0.20,), "flood_line": _C + (0.25,), "foam_lace": _S + (0.25,),
    "sandstorm": _C + (0.20,), "haboob": _C + (0.25,), "dust_devil": _C + (0.25,), "heat_shimmer": _G + (0.15,),
    "drought_crack": _G + (0.20,), "mirage": _S + (0.20,), "dust_veil": _G + (0.15,), "salt_haze": _S + (0.25,),
    "harmattan": _G + (0.15,), "sirocco": _C + (0.25,), "loess": _C + (0.25,), "brownout": _G + (0.15,),
}


def stem(fid):
    return fid[4:] if fid.startswith("elm_") else fid


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
    by_ch = {}
    for f in ids:
        by_ch.setdefault(table[f].get("chapter"), []).append(FORMS[stem(f)][0])
    for ch, forms in by_ch.items():
        if len(set(forms)) != len(forms):
            d = sorted({x for x in forms if forms.count(x) > 1})
            raise ValueError("ELEMENTS chapter %r reuses constructions: %s" % (ch, d))
    forms_only = [f for f, _p, _k in FORMS.values()]
    return {"finishes": len(FORMS), "distinct": len(set(forms_only)),
            "cross_chapter_reuse": len(forms_only) - len(set(forms_only)),
            "fine_missing": sorted(set(FORMS) - set(FINE))}
