# -*- coding: utf-8 -*-
"""FRACTURED MOLTEN (2026-07-30) — category 1/10 of the FRACTURED expansion
(owner brief 2026-07-30: 10 new categories, color diversity mandate). Pilot
built end-to-end by the foundation agent to prove the catlib template.

Palette: ember red / orange / gold / sulfur yellow / white-hot on black —
hue windows (hues/hspan) spanned across all 20 recipes so no two adjacent
contact-sheet tiles read as the same color.

Structure: 6 NEW generators (engine/expansions/fractured_catlib_2026.py
machinery; nothing here touches fractured_morpho_2026.py or fractured_math.py):
  crust    — rafted lava-crust plates: big overlapping elliptical rafts with
             dome profiles + bright COLLISION seams. Different math from
             flame_lava (KD-tree Voronoi F2-F1 cracks) and fm_mudcrack
             (Voronoi edges + curled lips): this is max-composited rafts.
  rivers   — magma river channels: anisotropic ridged-noise channel networks
             with hot cores and cooler banks (NOT iso-Voronoi, NOT tongues).
  pillow   — pillow lava mounds: worley-cell DOMES with concentric cooling
             rings and dark interstitial grooves (MORPHO pits are hex-lattice
             BOWLS — inverted profile, different lattice).
  columns  — columnar basalt SIDE VIEW: warped vertical column stripes with
             per-column width jitter and horizontal joint ledges. MINDS
             fm_basalt + flame_math basalt_columns are END-ON Voronoi/hex
             column tops — different composition, different math (the
             uniqueness gate is color-independent, so this had to differ).
  obsidian — obsidian ripple flows: contour ripples of a curl-advected
             stream function (glass flow-folds), sharp banded T.
  crackweb — cooling crack webs: thin iso-CONTOUR crack networks of a
             low-freq field at several levels + bright intersection nodes
             (not Voronoi-cell edges — organic branching contours).

Plus one category-specific macro kind: "caldera" (crater ring composition),
registered through CategoryKit(extra_macro=...).
"""
from __future__ import annotations

import numpy as np

from engine.expansions import fractured_catlib_2026 as catlib
from engine.expansions.fractured_catlib_2026 import (
    coords, fbm, frac, gauss, h2, n01, rng, rot, sstep, warp_pair, worley,
)

# ════════════════════════════════════════════════════════════════════════════
# STRUCTURAL GENERATORS — each returns an optical-thickness field T (0..1).
# ════════════════════════════════════════════════════════════════════════════

def g_crust(res, seed, rafts=8, jit=0.55, dome=0.45, seam=0.50, seam_w=0.10,
            warp=16.0, crackle=0.08, fine=0.06):
    """Rafted lava-crust plates: a few large rotated elliptical rafts,
    max-composited; where two raft fields meet, a hot collision seam glows.
    Per-raft thickness base + dome bulge + fine crackle."""
    r0 = rng(seed, 211)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 212, warp)
    x = xx + wu; y = yy + wv
    acc = np.full((res, res), -1e9, np.float32)
    second = np.full((res, res), -1e9, np.float32)
    n = max(4, int(rafts))
    for i in range(n):
        cx, cy = r0.uniform(0, res), r0.uniform(0, res)
        rad = res * float(r0.uniform(0.28, 0.52))
        an = float(r0.uniform(0, np.pi))
        asp = float(r0.uniform(0.55, 1.0))
        dx = (x - cx) * np.cos(an) + (y - cy) * np.sin(an)
        dy = -(x - cx) * np.sin(an) + (y - cy) * np.cos(an)
        d = np.sqrt((dx / rad) ** 2 + (dy / (rad * asp)) ** 2)
        base = float(r0.uniform(0, jit))
        field = base + dome * np.clip(1.0 - d * d, 0.0, 1.0) - d * 0.15
        second = np.maximum(second, np.minimum(acc, field))
        acc = np.maximum(acc, field)
    coll = np.clip(1.0 - (acc - second) / max(float(seam_w), 1e-3), 0.0, 1.0)
    coll = sstep(0.25, 0.95, coll)                       # collision seam mask
    crack = sstep(0.55, 0.9, fbm(res, res, rng(seed, 213), 4, 24))
    macro = fbm(res, res, rng(seed, 214), 3, 3)
    T = (acc + coll * seam + crack * crackle + macro * 0.12
         + fbm(res, res, rng(seed, 215), 2, 190) * fine)
    return frac(T)


def g_rivers(res, seed, freq=4.0, width=0.10, banks=0.35, aniso=2.2,
             warp=20.0, fine=0.06):
    """Magma river channels: anisotropically stretched ridged noise -> thin
    branching channel networks with white-hot cores, warm banks, cool levee
    falloff. Different math from FLAMES tongues (advected plumes)."""
    yy, xx = coords(res)
    a = float(rng(seed, 221).uniform(0, np.pi))
    u, v = rot((yy, xx), a)
    u = u / float(aniso)                              # stretch along flow
    wu, wv = warp_pair(res, seed, 222, warp)
    u += wu / float(aniso); v += wv
    f = fbm(res, res, rng(seed, 223), 4, 4)
    g = fbm(res, res, rng(seed, 224), 3, 6)
    p = (f * 0.7 + g * 0.3 + u / res * 0.6) * float(freq)
    ridged = 1.0 - np.abs(2.0 * frac(p) - 1.0)        # channel centerlines
    core = sstep(1.0 - float(width), 1.0, ridged)     # hot river core
    bank = sstep(1.0 - float(width) * 3.0, 1.0 - float(width), ridged) * (1.0 - core)
    macro = fbm(res, res, rng(seed, 225), 3, 3)
    T = (core * 0.85 + bank * float(banks) + macro * 0.15
         + fbm(res, res, rng(seed, 226), 2, 200) * fine)
    return frac(T)


def g_pillow(res, seed, cells=13, jit=0.50, dome=0.65, rings=3.0,
             ring_amp=0.25, groove=0.30, fine=0.06):
    """Pillow lava mounds: worley-cell DOMES (ballooning quench blobs) with
    concentric cooling rings and dark interstitial grooves."""
    d, bid = worley(res, seed, cells, 231)
    d2 = np.clip(d * 1.35, 0.0, 1.4)
    bulge = np.clip(1.0 - d2 * d2, 0.0, 1.0) ** 1.5
    ring = frac(d2 * float(rings))
    grv = sstep(0.78, 1.05, d2)
    macro = fbm(res, res, rng(seed, 232), 3, 3)
    T = (bid * jit + bulge * dome + ring * ring_amp * (1.0 - grv)
         - grv * groove + macro * 0.12
         + fbm(res, res, rng(seed, 233), 2, 180) * fine)
    return frac(T)


def g_columns(res, seed, cols=14, ledges=5.0, warp=12.0, jit=0.70,
              ledge_amp=0.30, tilt=0.12, fine=0.06):
    """Columnar basalt SIDE VIEW (Devils Postpile elevation): warped vertical
    column stripes with jittered widths + horizontal joint ledges climbing
    each column. NOT end-on hex tops (fm_basalt / flame basalt_columns)."""
    yy, xx = coords(res)
    a = float(rng(seed, 241).uniform(-0.3, 0.3))
    u, v = rot((yy, xx), a)
    wu, wv = warp_pair(res, seed, 242, warp)
    u += wu; v += wv
    u = u + v * float(tilt)                            # slight fan of columns
    cw = res / float(cols)
    # jittered column boundaries via per-strip phase hash
    ci = np.floor(u / cw)
    fi = frac(u / cw)
    width_j = 0.75 + 0.5 * h2(ci, 0.0, 243)
    cbody = sstep(0.03, 0.12, fi) * sstep(0.97, 0.88, fi)  # 1 inside column
    lp = frac(v / (cw * 1.6) + h2(ci, 0.0, 244))
    ledge = sstep(0.0, 0.10, lp) * sstep(0.42, 0.30, lp)   # joint ledges
    macro = fbm(res, res, rng(seed, 245), 3, 3)
    T = (h2(ci, 0.0, 246) * jit + cbody * 0.18 + ledge * ledge_amp * width_j
         + macro * 0.15 + fbm(res, res, rng(seed, 247), 2, 185) * fine)
    return frac(T)


def g_obsidian(res, seed, bands=12.0, adv=0.30, steps=2, sharp=2.2,
               fold=0.30, fine=0.05):
    """Obsidian ripple flows: contour ripples of a curl-advected stream
    function — glass flow-folds frozen mid-shear. Sharp banded thickness."""
    import cv2
    psi = fbm(res, res, rng(seed, 251), 4, 5)
    gy, gx = np.gradient(psi)
    ys, xs = coords(res)
    f = fbm(res, res, rng(seed, 252), 4, 4)
    for _ in range(int(steps)):
        f = cv2.remap(f, np.clip(xs + gx * res * float(adv), 0, res - 1),
                      np.clip(ys - gy * res * float(adv), 0, res - 1),
                      cv2.INTER_LINEAR)
    p = n01(f) * float(bands) + psi * float(fold) * float(bands)
    band = (1.0 - np.abs(2.0 * frac(p) - 1.0)) ** float(sharp)
    macro = fbm(res, res, rng(seed, 253), 3, 3)
    T = (band * 0.8 + frac(p) * 0.15 + macro * 0.12
         + fbm(res, res, rng(seed, 254), 2, 195) * fine)
    return frac(T)


def g_crackweb(res, seed, levels=4, freq=4.5, width=0.045, nodes=0.40,
               warp=8.0, fine=0.06):
    """Cooling crack webs: thin iso-CONTOUR lines of a low-freq field at
    several levels -> organic branching crack network; bright nodes where
    cracks of different levels intersect. Not Voronoi-cell edges."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 261, warp)
    f = fbm(res, res, rng(seed, 262), 4, 3)
    f = n01(f + (wu + wv) / res * 0.5) * float(freq)
    web = np.zeros((res, res), np.float32)
    node = np.zeros((res, res), np.float32)
    prev = np.zeros((res, res), np.float32)
    for k in range(int(levels)):
        lev = (k + 0.5 + float(h2(k, 0.0, 263)) * 0.6) / float(levels)
        crack = 1.0 - sstep(0.0, float(width) * float(freq), np.abs(frac(f) - lev))
        node = np.maximum(node, prev * crack)
        prev = np.maximum(prev, crack)
        web = np.maximum(web, crack)
    macro = fbm(res, res, rng(seed, 264), 3, 3)
    T = (web * 0.75 + node * nodes + macro * 0.15
         + fbm(res, res, rng(seed, 265), 2, 200) * fine)
    return frac(T)


ENGINES = {
    "crust": g_crust, "rivers": g_rivers, "pillow": g_pillow,
    "columns": g_columns, "obsidian": g_obsidian, "crackweb": g_crackweb,
}


# ════════════════════════════════════════════════════════════════════════════
# CATEGORY-SPECIFIC MACRO KIND — caldera (crater ring composition)
# ════════════════════════════════════════════════════════════════════════════

def m_caldera(r, mp, seed, K):
    """Crater: luminous rim ring around a dark bowl, radial sectors = domain."""
    yy, xx = K.coords(r)
    cx, cy = float(mp.get("cx", 0.5)), float(mp.get("cy", 0.52))
    dist = np.hypot((xx / r) - cx, (yy / r) - cy) / max(float(mp.get("radius", 0.42)), 1e-3)
    ang = np.arctan2((yy / r) - cy, (xx / r) - cx)
    rim = np.exp(-((dist - 1.0) ** 2) * float(mp.get("rim_sharp", 9.0)))
    bowl = K.sstep(0.85, 0.25, dist)                    # dark inside the bowl
    out = K.sstep(1.05, 1.9, dist) * 0.35               # dim apron outside
    M = np.clip(rim * 1.1 + out + bowl * float(mp.get("floor_glow", 0.18)), 0.0, 1.0)
    sect = float(mp.get("sectors", 7.0))
    D = K.n01(K.h2(np.floor((ang / np.pi + 1.0) * sect), np.floor(dist * 2.0), 41)
              + dist * 0.25)
    return M, D


# ════════════════════════════════════════════════════════════════════════════
# RECIPES — 20 finishes, ids fml_*, seeds 1000-1019. Hero hues SPAN
# red(0.00) / ember(0.04) / orange(0.06) / gold(0.11) / sulfur(0.155) /
# white-hot (low-sat flash dials); adjacent tiles never share a hero hue.
# Every recipe carries a dated audit comment (owner brief 2026-07-30).
# ════════════════════════════════════════════════════════════════════════════

CRUST_FIELD = {
 # [audit 2026-07-30] classic black crust rafts, deep ember-red seams — the category anchor
 "fml_ember_crust": dict(name="Ember Crust", engine="crust",
    eargs=dict(rafts=9, jit=0.5, dome=0.70, seam=0.80, seam_w=0.16, warp=14.0, crackle=0.14, fine=0.12),
    seed=1000, lut=(380.0, 980.0, 1.0, 1.25, 0.6), val=0.22,
    hues=[0.01], hspan=0.045, macro=("continents", dict(base=3, cells=4.0)), vd=(0.15, 1.35), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=48, floor=0.10, sparkle=0.30),
    desc="Rafted lava-crust plates split by glowing ember-red collision seams on black basalt. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] same crust math, molten-gold hero + big plate domains
 "fml_golden_seams": dict(name="Golden Seams", engine="crust",
    eargs=dict(rafts=7, jit=0.6, dome=0.42, seam=0.8, seam_w=0.12, warp=10.0, crackle=0.06, fine=0.10),
    seed=1001, lut=(400.0, 940.0, 0.95, 1.3, 2.1), val=0.22,
    hues=[0.10], hspan=0.04, macro=("domains", dict(cells=7)), vd=(0.18, 1.28), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=50, floor=0.11, sparkle=0.25, mswing=1.6),
    desc="Broad crust rafts welded by rivers of molten gold along every collision seam. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] sulfur-yellow crust, banded composition — brimstone flats
 # [m7 2026-07-30] sparkle+fine for m5; twin sulfur/gold anchors raise color population
 "fml_sulfur_plates": dict(name="Sulfur Plates", engine="crust",
    eargs=dict(rafts=11, jit=0.45, dome=0.55, seam=0.45, seam_w=0.08, warp=20.0, crackle=0.12, fine=0.12),
    seed=1002, lut=(420.0, 900.0, 1.05, 1.35, 3.8), val=0.21,
    hues=[0.135, 0.10], hspan=0.035, macro=("bands", dict(angle=0.5, freq=2.5, warp=0.3)), vd=(0.20, 1.22), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.32),
    desc="Brimstone-yellow crust plates banded across a cooling sulfur flat. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] white-hot caldera vent crust — flash dial gates chroma to luma peaks
 "fml_whitehot_caldera": dict(name="White-Hot Caldera", engine="crust",
    eargs=dict(rafts=8, jit=0.5, dome=0.6, seam=0.85, seam_w=0.10, warp=8.0, crackle=0.08, fine=0.11),
    seed=1003, lut=(400.0, 880.0, 0.9, 1.1, 1.2), val=0.22,
    hues=[0.08], hspan=0.05, satboost=0.9, macro=("caldera", dict(radius=0.40, sectors=8)), vd=(0.32, 1.60), tmod=0.40,
    kw=dict(ambient=0.32, ambient_sigma=52, floor=0.11, sparkle=0.38, gray=0.45, flash=(0.35, 0.62), ccboost=1.5),
    desc="A blinding white-hot caldera rim ringing a dark crater bowl of cooling crust. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] twin-hero orange/gold concentric rim bands — crater lake
 "fml_caldera_rim": dict(name="Caldera Rim", engine="crust",
    eargs=dict(rafts=6, jit=0.65, dome=0.5, seam=0.55, seam_w=0.11, warp=12.0, crackle=0.07),
    seed=1004, lut=(390.0, 960.0, 1.0, 1.3, 4.4), val=0.20,
    hues=[0.04, 0.10], hspan=0.045, macro=("rings", dict(freq=6.0, two=True)), vd=(0.16, 1.25), tmod=0.40,
    kw=dict(ambient=0.30, ambient_sigma=50, floor=0.10, sparkle=0.10),
    desc="Concentric caldera rims alternating orange and gold fire around a cooling crater lake. A FRACTURED MOLTEN finish."),
}

RIVERS = {
 # [audit 2026-07-30] ember-orange channel network — the archetypal lava river
 "fml_magma_river": dict(name="Magma River", engine="rivers",
    eargs=dict(freq=3.0, width=0.16, banks=0.50, aniso=2.4, warp=14.0, fine=0.12),
    seed=1005, lut=(380.0, 1000.0, 1.0, 1.3, 0.9), val=0.21,
    hues=[0.045], hspan=0.04, macro=("continents", dict(base=3, cells=3.0)), vd=(0.15, 1.30), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=48, floor=0.10, sparkle=0.22, mswing=1.5),
    desc="Branching magma river channels burning ember-orange through black cooling banks. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] liquid-gold channels over dark plate domains
 # [m7 2026-07-30] mswing 1.4 (m2 "gold" wants specMRange HIGH) + sparkle/fine for m5
 "fml_river_gold": dict(name="River of Gold", engine="rivers",
    eargs=dict(freq=3.2, width=0.17, banks=0.45, aniso=2.0, warp=12.0, fine=0.12),
    seed=1006, lut=(410.0, 920.0, 0.95, 1.25, 2.6), val=0.22,
    hues=[0.10], hspan=0.04, macro=("domains", dict(cells=6)), vd=(0.18, 1.30), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=52, floor=0.11, sparkle=0.22, mswing=2.0, mfloor=10.0),
    desc="Wide liquid-gold channels meandering between dark quenched levee domains. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] sulfur-yellow delta braids, fine anastomosing network
 "fml_sulfur_delta": dict(name="Sulfur Delta", engine="rivers",
    eargs=dict(freq=6.0, width=0.07, banks=0.30, aniso=2.8, warp=26.0, fine=0.14),
    seed=1007, lut=(430.0, 900.0, 1.05, 1.35, 4.9), val=0.20,
    hues=[0.13, 0.16], hspan=0.035, macro=("domains", dict(cells=6)), vd=(0.18, 1.22), tmod=0.30,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.20, mswing=1.3),
    desc="A fine braided delta of sulfur-yellow channels anastomosing across dark tephra. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] white-hot rapids — flash-gated chroma, gray dial for the white body
 "fml_whitehot_rapids": dict(name="White-Hot Rapids", engine="rivers",
    eargs=dict(freq=4.5, width=0.09, banks=0.35, aniso=3.0, warp=30.0, fine=0.12),
    seed=1008, lut=(400.0, 880.0, 0.9, 1.05, 1.7), val=0.22,
    hues=[0.07], hspan=0.05, satboost=0.85, macro=("rachis", dict(angle=0.35, lanes=6.0)), vd=(0.28, 1.50), tmod=0.35,
    kw=dict(ambient=0.32, ambient_sigma=54, floor=0.11, sparkle=0.40, gray=0.50, flash=(0.38, 0.60), ccboost=1.6),
    desc="Raging white-hot rapids shearing down a dark volcanic flume in silver-fire streaks. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] deep-red slow channels — cooling flow at the red edge
 "fml_ember_channels": dict(name="Ember Channels", engine="rivers",
    eargs=dict(freq=2.8, width=0.16, banks=0.50, aniso=1.8, warp=10.0, fine=0.12),
    seed=1009, lut=(370.0, 980.0, 1.0, 1.2, 5.5), val=0.19,
    hues=[0.0, 0.05], hspan=0.045, macro=("continents", dict(base=4, cells=4.0)), vd=(0.13, 1.25), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.30, mswing=1.3),
    desc="Slow deep-red channels of cooling magma pulsing at the dull-red edge of visibility. A FRACTURED MOLTEN finish."),
}

PILLOWS_COLUMNS = {
 # [audit 2026-07-30] orange pillow mounds — quench blobs with cooling rings
 # [uniq 2026-07-30] gate FAIL 80% vs fmo_black_opal (worley domes+rings+domains):
 # bigger mounds, dome-driven (low jit), deeper grooves, continents macro
 "fml_pillow_glow": dict(name="Pillow Glow", engine="pillow",
    eargs=dict(cells=9, jit=0.35, dome=0.8, rings=4.5, ring_amp=0.28, groove=0.45, fine=0.12),
    seed=1010, lut=(390.0, 960.0, 1.0, 1.3, 0.3), val=0.19,
    hues=[0.04, 0.08], hspan=0.045, macro=("continents", dict(base=3, cells=3.0)), vd=(0.16, 1.28), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=48, floor=0.10, sparkle=0.28, mswing=1.3),
    desc="Bulging pillow-lava mounds glowing orange through their concentric quench rings. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] sulfur-yellow pillow field, big continent composition
 "fml_sulfur_pillows": dict(name="Sulfur Pillows", engine="pillow",
    eargs=dict(cells=16, jit=0.55, dome=0.6, rings=4.0, ring_amp=0.22, groove=0.30),
    seed=1011, lut=(420.0, 910.0, 1.05, 1.35, 2.9), val=0.20,
    hues=[0.135], hspan=0.035, macro=("continents", dict(base=3, cells=3.5)), vd=(0.18, 1.20), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.08),
    desc="A heaped field of sulfur-yellow quench pillows stacked across dark volcanic glass. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] golden pillow rings — ring macro rides the mound rings
 "fml_golden_pillows": dict(name="Golden Pillows", engine="pillow",
    eargs=dict(cells=10, jit=0.45, dome=0.75, rings=2.5, ring_amp=0.35, groove=0.40),
    seed=1012, lut=(400.0, 940.0, 0.95, 1.3, 4.1), val=0.20,
    hues=[0.10], hspan=0.04, macro=("rings", dict(freq=5.0)), vd=(0.18, 1.30), tmod=0.40,
    kw=dict(ambient=0.30, ambient_sigma=50, floor=0.11, sparkle=0.10, mswing=1.5),
    desc="Great golden pillow mounds ringed with bright quench hoops on a black flow field. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] SIDE-VIEW colonnade: red-hot joint ledges climbing dark columns
 # [m7 2026-07-30] sparkle+fine octave for m5 (was paint-quiet), twin red/ember anchors
 "fml_basalt_colonnade": dict(name="Basalt Colonnade", engine="columns",
    eargs=dict(cols=13, ledges=5.0, warp=12.0, jit=0.7, ledge_amp=0.4, tilt=0.10, fine=0.14),
    seed=1013, lut=(380.0, 990.0, 1.0, 1.25, 1.4), val=0.18,
    hues=[0.02, 0.07], hspan=0.04, macro=("bands", dict(angle=0.2, freq=2.5, warp=0.25)), vd=(0.14, 1.28), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.32),
    desc="A towering basalt colonnade in side view, every joint ledge glowing dull red. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] ember-orange jointed pillars, finer columns + stronger warp
 "fml_jointed_ember": dict(name="Jointed Ember", engine="columns",
    eargs=dict(cols=15, ledges=6.0, warp=8.0, jit=0.65, ledge_amp=0.45, tilt=0.08, fine=0.14),
    seed=1014, lut=(390.0, 950.0, 1.0, 1.3, 3.3), val=0.22,
    hues=[0.04, 0.09], hspan=0.045, macro=("rachis", dict(angle=0.05, lanes=8.0)), vd=(0.16, 1.25), tmod=0.30,
    kw=dict(ambient=0.28, ambient_sigma=48, floor=0.10, sparkle=0.36, mswing=1.3),
    desc="Fine jointed pillars fanned and warped, ember-orange fire climbing every ledge. A FRACTURED MOLTEN finish."),
}

GLASS_WEB = {
 # [audit 2026-07-30] deep-red obsidian flow folds — glass ripples in a vortex
 # [m7 2026-07-30] m2 "obsidian" wants sat LOW: gray+flash dials (fire lives in
 # luma peaks); twin red anchors raise color population for m5 coherence
 # [m7b 2026-07-30] sat LOW band is ABSOLUTE <=0.082 (measured: 0.229 still
 # missed) -> gray 0.88 (black_opal precedent); fine back to LOW band for the
 # second m2 axis; m5 held by pop=11 + Cc carve
 # [m7c 2026-07-30] m2 fine axis is a percentile rank (LOW<=0.40): sparkle/fine
 # octaves down to land fine ~0.02; m5 rebuilt on block+residual energy instead
 # (deeper vd drama, brighter val) + wider anchor pair for color population
 # [m7d 2026-07-30] fine 0.0488 still ranked >0.40 (bands 14 + val overshot):
 # bands 14->10, fine octave 0.03->0.02; block/residual keep m5 on vd drama
 # [m7e 2026-07-30] measured ranks: LOW = fine <=0.034 absolute (rank 0.40);
 # bands 10->8 + sharp 2.0 lands fine ~0.032. M floor 10 escapes the 255-40 pin.
 # [m7f 2026-07-30] fine rank 0.46 (0.0401) — one more structural notch:
 # bands 8->7, sharp 1.7, sparkle 0.01; vd drama widened for block energy (m5)
 # [m7g 2026-07-30] rank 0.44 (0.0376) vs the 0.40 line: bands 7->6, sharp 1.5
 # [m7h 2026-07-30] rank exactly at the 0.40 boundary (0.0335, fail on the <=):
 # fold 0.35->0.22 + fine 0.005 shaves the last ripple octave
 "fml_obsidian_flow": dict(name="Obsidian Flow", engine="obsidian",
    eargs=dict(bands=6.0, adv=0.35, steps=3, sharp=1.5, fold=0.22, fine=0.005),
    seed=1015, lut=(370.0, 1000.0, 1.0, 1.25, 0.1), val=0.22,
    hues=[0.0, 0.08], hspan=0.04, macro=("vortex", dict(arms=2.0, twist=8.0)), vd=(0.08, 1.55), tmod=0.35,
    kw=dict(ambient=0.26, ambient_sigma=44, floor=0.10, sparkle=0.01, gray=0.88, flash=(0.30, 0.55), mswing=1.8, mfloor=10.0, ccboost=1.4),
    desc="Deep-red fire rippling through folded obsidian glass in slow vortex shears. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] gold glass ripples in steep bands — Pele's glass
 "fml_glass_gold": dict(name="Golden Glass", engine="obsidian",
    eargs=dict(bands=16.0, adv=0.25, steps=2, sharp=2.8, fold=0.25, fine=0.10),
    seed=1016, lut=(410.0, 930.0, 0.95, 1.3, 2.2), val=0.21,
    hues=[0.10], hspan=0.04, macro=("bands", dict(angle=0.8, freq=3.0, warp=0.3)), vd=(0.18, 1.28), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=50, floor=0.10, sparkle=0.25, mswing=1.3),
    desc="Golden ripples frozen mid-flow in volcanic glass, banded like Pele's tears. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] white-hot glass — flash-gated silver-fire flow folds
 # [m7 2026-07-30] sparkle 0.22->0.15: fine energy back into the MID band the
 # m2 "glass" token expects (was HIGH=miss), m5 stays healthy
 # [m7b 2026-07-30] mswing 1.3: M range 204 missed the HIGH band (~215+);
 # sparkle 0.15->0.08 lands fine ~0.04 (the MID hit measured on glass_gold)
 # [m7c 2026-07-30] fine still ranked HIGH (0.05): sparkle 0.08->0.04 + fine
 # octave 0.05->0.035 to land inside the 0.30-0.70 MID rank window
 # [m7d 2026-07-30] fine 0.0479 still >0.70 rank: bands 10->8 + fine 0.02 to
 # reach ~0.035 (glass_gold's measured MID hit); m5 held by Cc+pop
 "fml_whitehot_glass": dict(name="White-Hot Glass", engine="obsidian",
    eargs=dict(bands=8.0, adv=0.40, steps=3, sharp=1.8, fold=0.40, fine=0.02),
    seed=1017, lut=(400.0, 890.0, 0.9, 1.05, 3.0), val=0.22,
    hues=[0.08], hspan=0.05, satboost=0.85, macro=("vortex", dict(arms=1.0, twist=6.0)), vd=(0.30, 1.50), tmod=0.35,
    kw=dict(ambient=0.32, ambient_sigma=54, floor=0.11, sparkle=0.04, gray=0.50, flash=(0.36, 0.60), ccboost=1.6, mswing=1.4, mfloor=10.0),
    desc="White-hot glass flowing in blinding silver-fire folds over a black obsidian body. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] sulfur crack web — iso-contour cooling cracks + bright nodes
 # [uniq 2026-07-30] nearest fmo_ulysses_flash at the 80% line (domains macro
 # shared with that platelets finish): continents macro + coarser web
 "fml_sulfur_web": dict(name="Sulfur Web", engine="crackweb",
    eargs=dict(levels=3, freq=3.6, width=0.05, nodes=0.5, warp=10.0),
    seed=1018, lut=(430.0, 905.0, 1.05, 1.35, 4.7), val=0.20,
    hues=[0.135], hspan=0.035, macro=("continents", dict(base=3, cells=4.0)), vd=(0.17, 1.25), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.09),
    desc="A branching web of sulfur-yellow cooling cracks with blazing intersection nodes. A FRACTURED MOLTEN finish."),
 # [audit 2026-07-30] ember-red crack web, denser levels — contraction mesh
 "fml_ember_web": dict(name="Ember Web", engine="crackweb",
    eargs=dict(levels=5, freq=5.5, width=0.038, nodes=0.35, warp=12.0, fine=0.08),
    seed=1019, lut=(380.0, 970.0, 1.0, 1.25, 1.9), val=0.17,
    hues=[0.03], hspan=0.04, macro=("continents", dict(base=3, cells=4.0)), vd=(0.14, 1.28), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.26),
    desc="A dense ember-red contraction web crackling across a cooling black flow. A FRACTURED MOLTEN finish."),
}

GROUPS = {
    "CRUST FIELD": CRUST_FIELD,
    "RIVERS": RIVERS,
    "PILLOWS & COLUMNS": PILLOWS_COLUMNS,
    "GLASS & WEB": GLASS_WEB,
}

KIT = catlib.CategoryKit(engines=ENGINES, groups=GROUPS, tag="fractured-molten",
                         extra_macro={"caldera": m_caldera})

ALL = KIT.ALL
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
