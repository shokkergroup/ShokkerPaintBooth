# -*- coding: utf-8 -*-
"""GRADIENT EXTENDED — one authored pattern construction per finish (2026-09-02).

Owner: "GRADIENT EXTENDED could be almost as good [as Color-Shift Duos] but has way
too many repeating patterns. Need to make a bunch of new pattern designs and get rid
of the repeats. But the specs are also very impressive there." Then: "just make them
all good."

Census before this file: 91 recipes on 32 topologies, 75 of them sharing one
('flow' x10, 'directional_prism' x9, 'braided_flow' x7, 'cyclone_cells' x7 ...), and
42 vertical + 40 vortex orientations — two shapes recoloured a hundred ways.

Here every finish in the picker group gets its OWN construction chosen from its
name (Frostbite grows frost ferns, Patriot is woven bunting, Black Gold is a
starfield of gold on black, Obsidian is shattered glass ...), drawn with the
era/nightshift kits at the 1024 work grid and blended with the finish's gradient
carrier (its directional ramp or its vortex sweep) so the colour progression still
reads across the car. The spec pipeline in gradient_overhaul_2026 is UNTOUCHED —
it composes its eight-tier materials from the new field exactly as before.

    python _rebuild/grad_sheet.py   # sheets + per-finish time + law
"""
from __future__ import annotations
import numpy as np
from functools import lru_cache

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

from engine.paint_v2 import era_kit_2026 as EK
from engine.expansions import nightshift_forms_2026 as NF

WORK = 1024   # kits are pixel-scaled: always draw at 1024 and resample, so thumbnails match the car

# fid: (form, params, carrier_mix)   form "ek:name" -> era_kit_2026, "nf:name" -> nightshift_forms_2026
# carrier_mix = weight of the gradient sweep (0..1); the rest is the design field.
DESIGNS = {
    # ── directional (vertical contract) ─────────────────────────────────────
    "grad_black_gold":        ("ek:starfield",  dict(n=4200, mag=2.0, spikes=0.05, glow=1.3), 0.42),
    "grad_patriot":           ("ek:bands",      dict(n=72, shear=0.4, vortex=0, turb=0.15), 0.38),
    "grad_frostbite":         ("nf:frost_fern", dict(seeds=40, steps=110, branch=0.18, drift=0.6), 0.40),
    "grad_neon_violet":       ("ek:scanline",   dict(lines=230.0, triad=3.0, bloom=1.2, roll=0.3), 0.42),
    "grad_aqua_drift":        ("nf:caustics",   dict(scale=9.0, octaves=3, gain=3.2), 0.40),
    "grad_iron_blood":        ("ek:hull",       dict(panels=92, seam=1.4, rivets=0.6, wear=0.5), 0.40),
    "grad_emerald_crown":     ("ek:facets",     dict(stones=320, table=0.4, brilliance=1.6), 0.40),
    "grad_candy_cane":        ("ek:knurl",      dict(pitch=30.0, angle=45.0, relief=1.0, wobble=0.15), 0.35),
    "grad_chrome_wave":       ("nf:damascus",   dict(layers=200, folds=2, twist=1.2, warp=0.22), 0.36),
    "grad_copper_flame":      ("ek:rt_fingers", dict(n=140, gain=1.6, stalks=1.0), 0.40),
    "grad_storm_front":       ("ek:curl",       dict(scale=90, steps=22, step_px=2.2), 0.40),
    "grad_ultraviolet":       ("nf:quasicrystal", dict(waves=9, freq=300.0), 0.44),
    "grad_antique_gold":      ("ek:tooled",     dict(cell=90.0, petals=8, stamp=0.6, bevel=1.0), 0.40),
    "grad_obsidian":          ("nf:shatter",    dict(impacts=5, radials=40, rings=12, jitter=0.25), 0.40),
    "grad_electric_lime":     ("ek:dla",        dict(seeds=600, walkers=16000, steps=42), 0.40),
    "grad_magma":             ("ek:anneal_crack", dict(cells=80, width=3.0, gen=2), 0.40),
    "grad_sapphire_ice":      ("nf:basalt",     dict(cells=70, relax=2, wall=0.14), 0.40),
    "grad_rose_gold":         ("ek:guilloche",  dict(period=80.0, ring=12.0, amp=0.34, warp=20.0), 0.40),
    "grad_forest_night":      ("ek:shag",       dict(strands=7000, length=40, splay=0.9, lean=0.35), 0.40),
    "grad_solar_flare":       ("ek:sparks",     dict(n=2200, life=50, g=0.5, spread=1.5), 0.40),
    # ── horizontal / diagonal (angle contract kept by the carrier) ─────────
    "grad_black_gold_h":      ("ek:threads",    dict(stripes=15, window=0.4, fibres=1800, tilt=7.0), 0.40),
    "grad_patriot_h":         ("ek:sett",       dict(pitch=52.0, twill=5.0, weave=1.0), 0.40),
    "grad_candy_cane_h":      ("ek:ikat",       dict(motifs=1200, blur=10.0, axis=0, sharp=1.3, rows=64), 0.40),
    "grad_magma_h":           ("nf:erosion",    dict(sim=384, iters=30, sharp=0.6), 0.40),
    "grad_rose_gold_h":       ("ek:moire",      dict(lpi=200.0, beat=1.04, angle=11.0, sharp=1.6), 0.40),
    "grad_black_gold_diag":   ("ek:kh_braid",   dict(layers=110, shear=3.4), 0.40),
    "grad_neon_violet_diag":  ("ek:wireframe",  dict(rows=30, persp=1.6, horizon=0.42, glow=1.0), 0.40),
    "grad_storm_front_diag":  ("ek:wrinkle",    dict(k=1.4, steps=16, scale=180), 0.40),
    "grad_emerald_crown_diag": ("ek:polygons",  dict(cells=90, width=2.2, relief=0.5), 0.40),
    # ── second directional wave ─────────────────────────────────────────────
    "grad_wine_silk":         ("ek:crinkle",    dict(scale=140, sharp=2.2, folds=3), 0.40),
    "grad_midnight_gold":     ("ek:glyphs",     dict(n=700, stroke=2.0, size=14.0), 0.40),
    "grad_coral_sea":         ("nf:gray_scott", dict(feed=0.030, kill=0.058), 0.40),
    "grad_ember_ash":         ("ek:percolate",  dict(cells=190, p=0.45, rounds=3), 0.40),
    "grad_jade_mist":         ("ek:resist",     dict(patches=140, crackle=1.0, cells=170, bleed=0.4), 0.40),
    "grad_plum_dawn":         ("ek:dunes",      dict(n=40, drift=0.42, crest=2.0), 0.40),
    "grad_amber_night":       ("ek:craters",    dict(n=3200, rmin=1.6, rmax=7.0, rim=0.5), 0.40),
    "grad_sage_bronze":       ("nf:imbricate",  dict(rows=56, overlap=0.45, jitter=0.16), 0.40),
    "grad_titanium_fire":     ("ek:spall",      dict(cells=90, lift=0.6), 0.40),
    "grad_ivory_cobalt":      ("nf:truchet",    dict(tiles=50, style="arc", width=0.17), 0.40),
    "grad_honey_slate":       ("ek:honeycomb",  dict(cells=110, wall=0.14, jitter=0.06), 0.40),
    "grad_rose_midnight":     ("ek:filaments",  dict(n=340, length=50, wander=0.3, width=1.3), 0.40),
    "grad_charcoal_gold":     ("ek:intaglio",   dict(lpi=130.0, angle=28.0, warp=26.0, depth=1.0), 0.40),
    "grad_lavender_dusk":     ("nf:metaball",   dict(blobs=3000, radius=0.007, thresh=0.42), 0.40),
    "grad_emerald_night":     ("nf:maze",       dict(cells=120, wall=0.3), 0.40),
    "grad_cream_crimson":     ("ek:splatter",   dict(blobs=600, rmax=30.0, drips=0.45, spatter=1.0), 0.40),
    "grad_blush_cobalt":      ("ek:discs",      dict(n=3000, radius=14.0, tilt=0.75, facet=1.0), 0.40),
    "grad_graphite_amber":    ("ek:pixels",     dict(cell=10.0, levels=8, dither=0.35), 0.40),
    "grad_mint_purple":       ("ek:squiggle",   dict(n=480, length=110.0, amp=16.0, confetti=0.55), 0.40),
    "grad_champagne_navy":    ("nf:apollonian", dict(depth=6000, rmin=0.0022, rmax=0.085), 0.40),
    "grad_pewter_rose":       ("ek:microtext",  dict(rows=120, density=0.62, height=7.0), 0.40),
    "grad_chocolate_gold":    ("ek:bricks",     dict(rows=38, cols=7, bind=0.22, lean=0.5), 0.40),
    # ── vortex (sweep carrier) ──────────────────────────────────────────────
    "grad_patriot_vortex":    ("ek:stars",      dict(cell=120.0, points=5, ring=0.35, interlace=1.0), 0.42),
    "grad_neon_violet_vortex": ("ek:holo",      dict(rings=380.0, orders=3.0, warp=90.0), 0.42),
    "grad_obsidian_vortex":   ("nf:clifford",   dict(iters=900000), 0.42),
    "grad_rose_gold_vortex":  ("nf:phyllotaxis", dict(n=60000, spread=0.72, dot=0.0016), 0.42),
    "grad_solar_vortex":      ("nf:bz_spiral",  dict(cores=24), 0.42),
    "grad_crimson_vortex":    ("nf:rosensweig", dict(pitch=30.0, relax=0.55, spike=2.6), 0.44),
    "grad_coral_vortex":      ("ek:eden",       dict(seeds=1000, steps=14), 0.44),
    "grad_amber_vortex":      ("nf:ridge_flow", dict(ridges=200, cores=6, bend=1.9), 0.44),
    "grad_honey_vortex":      ("ek:worley",     dict(cells=130, kind="f2f1", jitter=1.0), 0.44),
    "grad_emerald_vortex":    ("nf:chladni",    dict(sharp=9.0, floor=0.1), 0.44),
    "grad_jade_vortex":       ("ek:camo",       dict(patches=6, blob=110.0, roughness=1.0), 0.44),
    "grad_aqua_vortex":       ("ek:topo",       dict(lines=130.0, warp=1.2, index=5, width=1.4), 0.44),
    "grad_cerulean_vortex":   ("ek:scales",     dict(cell=24.0, rows=1.0, keel=0.5, sheen=1.0), 0.44),
    "grad_cobalt_vortex":     ("nf:basalt",     dict(cells=90, relax=2, wall=0.12), 0.44),
    "grad_indigo_vortex":     ("ek:ikat",       dict(motifs=1400, blur=8.0, axis=1, sharp=1.4, rows=72), 0.44),
    "grad_lavender_vortex":   ("ek:tooled",     dict(cell=70.0, petals=5, stamp=0.5, bevel=1.0), 0.44),
    "grad_plum_vortex":       ("ek:crinkle",    dict(scale=90, sharp=3.0, folds=4), 0.44),
    "grad_rose_vortex":       ("ek:guilloche",  dict(period=60.0, ring=9.0, amp=0.4, warp=30.0, spin=1.0), 0.44),
    "grad_blush_vortex":      ("ek:discs",      dict(n=2200, radius=18.0, tilt=0.9, facet=1.0), 0.44),
    "grad_maroon_vortex":     ("nf:damascus",   dict(layers=150, folds=4, twist=3.0, warp=0.3), 0.44),
    "grad_burgundy_vortex":   ("ek:shred",      dict(strips=170, curl_amt=30.0, gap=0.3), 0.44),
    "grad_chocolate_vortex":  ("ek:splatter",   dict(blobs=400, rmax=40.0, drips=0.7, spatter=0.8), 0.44),
    "grad_tan_vortex":        ("ek:dunes",      dict(n=48, drift=0.5, crest=2.2), 0.44),
    "grad_cream_vortex":      ("nf:imbricate",  dict(rows=70, overlap=0.4, jitter=0.2), 0.44),
    "grad_ivory_vortex":      ("nf:apollonian", dict(depth=4000, rmin=0.003, rmax=0.06), 0.44),
    "grad_slate_vortex":      ("ek:anneal_crack", dict(cells=100, width=2.0, gen=3), 0.44),
    "grad_charcoal_vortex":   ("ek:fbm",        dict(octaves=(16, 32, 64, 128, 256, 512), gain=0.6), 0.44),
    "grad_graphite_vortex":   ("ek:knurl",      dict(pitch=22.0, angle=60.0, relief=1.0, wobble=0.6), 0.44),
    "grad_pewter_vortex":     ("ek:hull",       dict(panels=110, seam=1.2, rivets=0.4, wear=0.3), 0.44),
    "grad_champagne_vortex":  ("ek:craters",    dict(n=4000, rmin=1.2, rmax=5.0, rim=0.6), 0.44),
    "grad_titanium_vortex":   ("ek:spall",      dict(cells=120, lift=0.4), 0.44),
    "grad_mint_vortex":       ("ek:percolate",  dict(cells=210, p=0.5, rounds=2), 0.44),
    "grad_sage_vortex":       ("ek:shag",       dict(strands=6000, length=30, splay=1.3, lean=0.2), 0.44),
    "grad_chartreuse_vortex": ("ek:dla",        dict(seeds=800, walkers=12000, steps=40), 0.44),
    "grad_peach_vortex":      ("nf:gray_scott", dict(feed=0.034, kill=0.063), 0.44),
    "grad_ruby_vortex":       ("ek:facets",     dict(stones=260, table=0.3, brilliance=1.8), 0.44),
    "grad_sapphire_vortex":   ("ek:polygons",   dict(cells=60, width=2.5, relief=0.7), 0.44),
    "grad_topaz_vortex":      ("nf:shatter",    dict(impacts=4, radials=30, rings=14, jitter=0.2), 0.44),
    "grad_amethyst_vortex":   ("nf:quasicrystal", dict(waves=5, freq=220.0), 0.44),
    "grad_opal_vortex":       ("ek:holo",       dict(rings=300.0, orders=4.0, warp=120.0, sharp=0.8), 0.44),
    # ── material gradients ─────────────────────────────────────────────────
    "gradient_anodized_gloss": ("ek:moire",     dict(lpi=230.0, beat=1.05, angle=7.0, sharp=1.4), 0.40),
    "gradient_candy_frozen":  ("nf:frost_fern", dict(seeds=30, steps=120, branch=0.2, drift=0.55), 0.40),
    "gradient_candy_matte":   ("ek:sett",       dict(pitch=40.0, twill=9.0, weave=1.0), 0.40),
    "gradient_carbon_chrome": ("ek:threads",    dict(stripes=11, window=0.5, fibres=2200, tilt=4.0), 0.40),
    "gradient_chrome_matte":  ("ek:bands",      dict(n=80, shear=1.0, vortex=10, turb=0.4), 0.40),
    "gradient_ember_ice":     ("ek:rt_fingers", dict(n=90, gain=1.3, stalks=0.8), 0.40),
    "gradient_metallic_satin": ("ek:wrinkle",   dict(k=0.7, steps=12, scale=220), 0.40),
    "gradient_obsidian_mirror": ("nf:clifford", dict(iters=700000), 0.40),
    "gradient_pearl_chrome":  ("ek:scales",     dict(cell=30.0, rows=1.2, keel=0.7, sheen=1.2), 0.40),
    "gradient_spectraflame_void": ("ek:sparks", dict(n=2600, life=60, g=0.45, spread=2.0), 0.40),
}


def check():
    """No form used more than twice, and never twice with the same params."""
    seen = {}
    for fid, (form, params, _mix) in DESIGNS.items():
        seen.setdefault(form, []).append((fid, tuple(sorted((k, str(v)) for k, v in params.items()))))
    bad = [(f, [x[0] for x in v]) for f, v in seen.items() if len(v) > 2 or len({x[1] for x in v}) < len(v)]
    if bad:
        raise ValueError("GRADIENT designs repeat: %r" % bad)
    return len(DESIGNS), len(seen)


def _norm(a):
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / max(hi - lo, 1e-6)


def _resize(f, h, w):
    if (h, w) == (WORK, WORK):
        return f
    if cv2 is not None:
        return cv2.resize(f, (int(w), int(h)), interpolation=cv2.INTER_AREA if w < WORK else cv2.INTER_LINEAR)
    ys = (np.arange(h) * WORK // h).astype(int)
    xs = (np.arange(w) * WORK // w).astype(int)
    return f[ys][:, xs]


@lru_cache(maxsize=4)
def _design_work(fid, seed):
    """(design 0..1, design-keyed fine grain 0..1) at WORK."""
    form, params, _mix = DESIGNS[fid]
    kit, name = form.split(":", 1)
    fn = getattr(EK if kit == "ek" else NF, name)
    out = fn((WORK, WORK), int(seed) & 0x7FFFFFFF, **params)
    f = np.asarray(out[0] if isinstance(out, tuple) else out, np.float32)
    if f.ndim == 3:
        f = f.mean(axis=2)
    f = _norm(f)
    # FINE construction keyed to the design's own edges (same law as every rebuilt shelf):
    # the macro kits alone measured SCALE fine 0.11-0.17 on ferns/caustics/damascus/curl.
    g = np.asarray(NF.compose_form(f, int(seed) & 0x7FFFFFFF, kind="grain", amount=1.0, res=WORK), np.float32)
    if cv2 is not None:
        g = g - cv2.GaussianBlur(g, (0, 0), 3.0)
    fine = _norm(g)
    f2 = _norm(f * 0.62 + fine * 0.38)
    return f2, fine


def design_field(fid, seed, h, w):
    """The named construction at the work grid, 0..1, drawn at WORK and resampled."""
    return _resize(_design_work(fid, int(seed))[0], h, w)


def fine_field(fid, seed, h, w):
    """Replaces the shelf-wide flow_grain carrier (the same diagonal screen on every
    finish at 1:1 was itself a repeat) with grain that follows THIS design's edges."""
    return _resize(_design_work(fid, int(seed))[1], h, w)


def raw_field(fid, seed, h, w, u, rad, theta, orientation):
    """Gradient carrier blended with the design. Carrier keeps the finish's contract:
    the directional ramp (angle already applied in u) or a radial sweep for a vortex."""
    d = design_field(fid, seed, h, w)
    mix = DESIGNS[fid][2]
    if orientation == "vortex":
        carrier = _norm(rad) * 0.8 + 0.2 * (0.5 + 0.5 * np.sin(theta * 3.0 + rad * 9.0))
    else:
        carrier = _norm(u)
    return carrier * mix + d * (1.0 - mix)
