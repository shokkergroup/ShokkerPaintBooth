# -*- coding: utf-8 -*-
"""FRACTURED MINDS v3 (2026-06-12 overnight run) — owner mandate: NO repeated
pattern designs, NO repeated spec designs, flips/rotations count as lazy.
22 finishes (10 rebuilds per his notes + 12 full replacements), each with its
OWN generator logic and its OWN hand-built spec recipe.

SPEC PHYSICS GATE (from his "won't shift even crushed" notes): every spec must
keep a strong tinted-metal lobe — mean(M) 150-235, frac(M<110) <= 0.30,
std(B) >= 48 (carve contrast), mean(G) 45-115. Blue zones welcome but bounded.
"""
import numpy as np
import cv2

from engine.expansions.redesign_wave2_2026 import (
    _rng, _noise, _n01, _sstep, _gauss, _coords, _warp, _curves, _dendrites,
    _flow_theta, _flowlines, _crystal, _gray_scott, _dirblur, _seed_int, _sr,
)

_WORKV = 1024
_V3_CACHE = {}


def _v3_fields(fid, h, w, s):
    key = (fid, h, w, s)
    if key in _V3_CACHE:
        return _V3_CACHE[key]
    if len(_V3_CACHE) > 5:
        _V3_CACHE.pop(next(iter(_V3_CACHE)))
    out = V3[fid]["fields"](h, w, s)
    _V3_CACHE[key] = out
    return out


def _rotuv(h, w, s, warp_px=8):
    yy, xx = _coords(h, w)
    if warp_px > 0:
        yy, xx = _warp(yy, xx, h, w, s, warp_px * _sr(h, w))
    a = float(_rng(s, 2).uniform(0, np.pi))
    return (xx * np.cos(a) + yy * np.sin(a), -xx * np.sin(a) + yy * np.cos(a))


def _edge_of(f, sg=1.2):
    gy, gx = np.gradient(_gauss(f, sg))
    return np.clip(_n01(np.abs(gx) + np.abs(gy)) * 2.2, 0, 1)


V3 = {}


def _def(fid):
    def deco(builder):
        V3[fid] = builder()
        return builder
    return deco


# ═══════════════════════════════════════════ REPLACEMENTS (12 new concepts)

# ── 1. PYTHON SKIN (replaces orbit_swarm) ──────────────────────────────────
# Irregular rosette blotches with pale rims — blotch colonies grown from
# multi-seed noise, rims extracted as offset bands. New logic: colony growth.
@_def("fm_python_skin")
def _b_python():
    def fields(h, w, s):
        sr = _sr(h, w)
        colony = _noise(h, w, s ^ 0x11, (6, 13, 28))
        blotch = _sstep(0.55, 0.62, colony)                       # dark saddles
        rim = np.clip(_sstep(0.50, 0.56, colony) - blotch, 0, 1)  # pale outline band
        scale_u, scale_v = _rotuv(h, w, s ^ 0x12, 3)
        p = 4.2 * sr                                              # belly scale micro
        scales = (0.5 + 0.5 * np.sin(scale_u * 2 * np.pi / p)) * (0.5 + 0.5 * np.sin(scale_v * 2 * np.pi / (p * 1.6)))
        scales = _sstep(0.3, 0.6, scales)
        speck = _sstep(0.78, 0.9, _noise(h, w, s ^ 0x13, (5, 11)))
        return blotch, rim, scales, speck

    def spec(F, s, h, w):
        blotch, rim, scales, speck = F
        # rims = pale gold metal halos; blotch hearts = deep CC pools; scales
        # carry a directional micro-shimmer; speckles pin.
        M = 168 + 70 * rim - 60 * blotch * (1 - rim) + 45 * scales * (1 - blotch) + 40 * speck
        G = 60 + 45 * (1 - scales) + 50 * speck
        B = 92 + 150 * blotch + 95 * rim + 55 * speck - 35 * scales * (1 - blotch)
        return M, G, B

    def paint(F, src_lum):
        blotch, rim, scales, speck = F
        c1 = np.float32([0.55, 0.38, 0.16])   # python tan
        c2 = np.float32([0.12, 0.10, 0.08])   # saddle brown-black
        c3 = np.float32([0.95, 0.88, 0.62])   # pale rim
        art = (c1[None, None, :] * (scales * (1 - blotch))[..., None]
               + c2[None, None, :] * blotch[..., None]
               + c3[None, None, :] * (rim * 1.2)[..., None])
        k = np.clip(blotch + rim + scales * 0.5, 0, 1) * 0.55
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 2. DIAMONDBACK (replaces serpentine) ───────────────────────────────────
# Rattler diamond chain with pale keel borders running along a winding spine.
@_def("fm_diamondback")
def _b_diamondback():
    def fields(h, w, s):
        sr = _sr(h, w)
        u, v = _rotuv(h, w, s, 26)
        p = 26.0 * sr
        spine = np.abs(((v / p) - np.floor(v / p + 0.5))) * p     # distance to spine rows
        along = u / (16.0 * sr)
        dia = np.clip(1 - (np.abs(along - np.floor(along + 0.5)) * 2.4 + spine / (p * 0.42)), 0, 1)
        diamond = _sstep(0.12, 0.30, dia)
        border = np.clip(_sstep(0.04, 0.14, dia) - diamond, 0, 1)
        u2, v2 = _rotuv(h, w, s ^ 0x21, 3)
        keel = (0.5 + 0.5 * np.sin(u2 * 2 * np.pi / (3.8 * sr)))  # keeled scale micro
        keel = _sstep(0.55, 0.8, keel)
        return diamond, border, keel, _n01(dia)

    def spec(F, s, h, w):
        diamond, border, keel, dia = F
        # the chain ignites along its length: a traveling gradient phase per row
        u, v = _rotuv(h, w, s ^ 0x99, 0)
        travel = _n01(np.sin(u * 0.006 + dia * 4))
        M = 175 + 60 * border - 70 * diamond * travel + 35 * keel
        G = 55 + 60 * keel * (1 - diamond) + 30 * (1 - border)
        B = 86 + 160 * diamond * (0.35 + 0.65 * travel) + 105 * border + 28 * keel * (1 - diamond)
        return M, G, B

    def paint(F, src_lum):
        diamond, border, keel, dia = F
        c1 = np.float32([0.35, 0.28, 0.18])
        c2 = np.float32([0.10, 0.08, 0.06])
        c3 = np.float32([0.92, 0.85, 0.60])
        art = (c2[None, None, :] * diamond[..., None]
               + c3[None, None, :] * (border * 1.3)[..., None]
               + c1[None, None, :] * (keel * (1 - diamond))[..., None])
        k = np.clip(diamond + border + keel * 0.4, 0, 1) * 0.55
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 3. STINGRAY SHAGREEN (replaces perforated) ─────────────────────────────
# Dense pearl-bead leather with a brighter "eye" stone line. New logic:
# size-field bead packing on a jittered hex lattice.
@_def("fm_stingray")
def _b_stingray():
    def fields(h, w, s):
        sr = _sr(h, w)
        u, v = _rotuv(h, w, s, 2)
        p = 5.2 * sr
        hx = u / p; hy = v / p * 1.1547
        row = np.floor(hy); hxo = hx + (row % 2) * 0.5
        cellx = np.floor(hxo + 0.5); celly = np.floor(hy + 0.5)
        jx = np.sin(cellx * 12.99 + celly * 7.31) * 0.16
        jy = np.sin(cellx * 39.4 + celly * 11.1) * 0.16
        du = (hxo - cellx - jx); dv = (hy - celly - jy)
        r = np.sqrt(du * du + dv * dv)
        size = 0.30 + 0.14 * _n01(np.sin(cellx * 3.7 + celly * 5.1))
        bead = np.clip(1 - r / np.maximum(size, 1e-3), 0, 1) ** 0.7
        # the eye line: a thin WINDING ridge corridor where beads swell (ray's
        # spine stones) — ridge of the noise field, not a blotchy threshold
        en = _noise(h, w, s ^ 0x31, (90, 220))
        eye = _sstep(0.80, 0.94, 1.0 - np.abs(en * 2.0 - 1.0))
        bead_eye = np.clip(bead + eye * bead * 0.8, 0, 1)
        gap = (bead < 0.05).astype(np.float32)
        return bead_eye.astype(np.float32), eye, gap, _n01(r)

    def spec(F, s, h, w):
        bead, eye, gap, r = F
        # every bead = a domed mirror (M crown, CC ring at the bead equator);
        # the eye-line beads go pure-blue mirror (metal dip — bounded area)
        crown = _sstep(0.55, 0.9, bead)
        equator = np.clip(_sstep(0.25, 0.5, bead) - crown, 0, 1)
        M = 170 + 60 * crown - 120 * crown * eye + 25 * equator
        G = 58 + 55 * gap + 25 * (1 - bead)
        B = 90 + 120 * equator + 130 * crown * eye + 45 * crown
        return M, G, B

    def paint(F, src_lum):
        bead, eye, gap, r = F
        c1 = np.float32([0.28, 0.30, 0.38])
        c2 = np.float32([0.85, 0.88, 0.95])
        c3 = np.float32([0.10, 0.45, 0.75])
        art = (c1[None, None, :] * (1 - bead)[..., None]
               + c2[None, None, :] * _sstep(0.5, 0.95, bead)[..., None]
               + c3[None, None, :] * (eye * bead)[..., None])
        k = np.clip(bead + gap * 0.4, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 4. GILA BEAD (replaces pin_matrix) ─────────────────────────────────────
# Gila-monster beaded reticulation: bead clusters in two clans (orange/black),
# clan borders crawl. New logic: clan id from smoothed noise majority.
@_def("fm_gila_bead")
def _b_gila():
    def fields(h, w, s):
        sr = _sr(h, w)
        u, v = _rotuv(h, w, s, 4)
        p = 6.5 * sr
        hx = u / p; hy = v / p * 1.1547
        row = np.floor(hy); hxo = hx + (row % 2) * 0.5
        du = (hxo - np.floor(hxo + 0.5)); dv = (hy - np.floor(hy + 0.5))
        r = np.sqrt(du * du + dv * dv)
        bead = np.clip(1 - r / 0.42, 0, 1) ** 0.8
        clan = _sstep(0.56, 0.62, _noise(h, w, s ^ 0x41, (26, 60, 130)))
        border = np.clip(1 - np.abs(_gauss(clan, 3) - 0.5) * 5, 0, 1)
        return bead.astype(np.float32), clan, border

    def spec(F, s, h, w):
        bead, clan, border = F
        # clan A beads = metal crowns; clan B beads = CC domes; the crawling
        # border between clans is a live wire (both channels surge)
        crown = _sstep(0.15, 0.60, bead)
        M = 160 + 75 * bead * clan - 55 * crown * (1 - clan) + 60 * border * bead
        G = 62 + 40 * (1 - bead) + 30 * clan
        B = 74 + 180 * crown * (1 - clan) * (1 - border) + 130 * border * crown + 18 * bead * clan
        return M, G, B

    def paint(F, src_lum):
        bead, clan, border = F
        c1 = np.float32([0.95, 0.45, 0.10])
        c2 = np.float32([0.12, 0.10, 0.10])
        c3 = np.float32([0.95, 0.80, 0.55])
        art = (c1[None, None, :] * (bead * clan)[..., None]
               + c2[None, None, :] * (bead * (1 - clan))[..., None]
               + c3[None, None, :] * (border * bead)[..., None])
        k = np.clip(bead, 0, 1) * 0.55
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 5. CROC HIDE (replaces scale_armor) ────────────────────────────────────
# Crocodile osteoderm scutes: rounded-rect plates with keeled domes and deep
# wrinkle channels. New logic: rounded-rect SDF grid with per-plate dome.
@_def("fm_croc_hide")
def _b_croc():
    def fields(h, w, s):
        sr = _sr(h, w)
        u, v = _rotuv(h, w, s, 10)
        pu, pv = 13.0 * sr, 9.0 * sr
        cu = (u / pu - np.floor(u / pu + 0.5)) * pu
        cvv = (v / pv - np.floor(v / pv + 0.5)) * pv
        idu = np.floor(u / pu); idv = np.floor(v / pv)
        per = _n01(np.sin(idu * 12.99 + idv * 7.31) + 1)
        hw_ = pu * (0.36 + 0.06 * per); hh_ = pv * (0.34 + 0.06 * per)
        dx = np.abs(cu) - hw_; dy = np.abs(cvv) - hh_
        sd = np.maximum(dx, dy)
        plate = 1.0 - _sstep(-1.4 * sr, 0.0, sd)                   # inside plates
        channel = _sstep(0.0, 1.6 * sr, sd)                        # wrinkle gaps
        dome = np.clip(1 - (np.abs(cu) / hw_) ** 2 - (np.abs(cvv) / hh_) ** 2, 0, 1) * plate
        keel = np.clip(1 - np.abs(cu) / (1.4 * sr), 0, 1) * plate
        return plate, dome.astype(np.float32), keel, channel, per

    def spec(F, s, h, w):
        plate, dome, keel, channel, per = F
        # ROUND-4 PINK FORMULA (owner r45 "very little change with the spec"):
        # plates = pink field (M high + CC mid-high); wrinkle channels = light
        # blue rivers (metal drops, clearcoat maxes); scattered blue scutes =
        # full pools whose dome crests stay mid-metal = the purple dot; caps
        # on normal plates = light-pink crests
        blue_scute = _sstep(0.78, 0.84, per) * plate
        cap = _sstep(0.72, 0.95, dome)
        crest = _sstep(0.55, 0.9, dome)
        M = (190 - 105 * channel - 108 * blue_scute * (1 - crest)
             - 44 * blue_scute * crest + 16 * keel * (1 - blue_scute))
        G = 58 + 34 * channel + 20 * (1 - dome) * plate
        B = (145 + 90 * channel + 95 * blue_scute
             + 38 * cap * (1 - blue_scute) - 12 * keel * (1 - blue_scute))
        return M, G, B

    def paint(F, src_lum):
        plate, dome, keel, channel, per = F
        blue_scute = _sstep(0.78, 0.84, per) * plate
        c1 = np.float32([0.90, 0.55, 0.75])
        c2 = np.float32([0.45, 0.55, 0.95])
        c3 = np.float32([0.20, 0.12, 0.25])
        art = (c1[None, None, :] * (dome * (1 - blue_scute))[..., None]
               + c2[None, None, :] * blue_scute[..., None]
               + c3[None, None, :] * channel[..., None])
        k = np.clip(plate * 0.6 + channel + blue_scute, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 6. TORTOISE SCUTE (replaces thorn_bramble) ─────────────────────────────
# Tortoise shell plates with INTERIOR GROWTH RINGS. New logic: per-cell
# concentric ring phase from distance-to-cell-center.
@_def("fm_tortoise")
def _b_tortoise():
    def fields(h, w, s):
        sr = _sr(h, w)
        cid, edge, orient, axial = _crystal(h, w, s, n_sites=900, aniso=1.25, res=0.5)
        per = _n01(np.sin(cid * 12.99) + 1)
        seam = 1.0 - _sstep(0.04, 0.13, edge)
        binp = (seam < 0.5).astype(np.uint8)
        dist = cv2.distanceTransform(binp, cv2.DIST_L2, 3)
        rings = (0.5 + 0.5 * np.sin(dist * (2 * np.pi / (5.5 * sr)) + per * 6.0)).astype(np.float32)
        ringline = _sstep(0.55, 0.82, rings) * (seam < 0.5)
        return seam, ringline, per, _n01(dist)

    def spec(F, s, h, w):
        seam, ringline, per, dist = F
        # growth rings flash SEQUENTIALLY from rim to center (phase = dist),
        # seams stay dark horn; per-plate phase offset breaks any repetition
        phase = _n01(dist + per * 0.8)
        gate = _sstep(0.35, 0.45, phase) * (1 - _sstep(0.6, 0.7, phase))
        M = 175 + 50 * ringline - 60 * seam + 28 * gate * (1 - ringline)
        G = 58 + 55 * seam + 22 * (1 - ringline)
        B = 80 + 130 * ringline + 55 * gate * (1 - seam) * (1 - ringline) + 26 * per * (1 - ringline) - 25 * seam
        return M, G, B

    def paint(F, src_lum):
        seam, ringline, per, dist = F
        c1 = np.float32([0.50, 0.32, 0.12])
        c2 = np.float32([0.18, 0.10, 0.05])
        c3 = np.float32([0.85, 0.62, 0.25])
        art = (c1[None, None, :] * (1 - seam)[..., None] * (0.5 + 0.5 * dist)[..., None]
               + c2[None, None, :] * seam[..., None]
               + c3[None, None, :] * ringline[..., None])
        k = np.clip((1 - seam) * 0.6 + seam, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 7. DRAGONFLY WING (replaces shatter_web) ───────────────────────────────
# Hierarchical wing venation: primary veins + secondary mesh + size-graded
# membrane cells. New logic: two-tier vein network with membrane iridescence.
@_def("fm_dragonfly")
def _b_dragonfly():
    def fields(h, w, s):
        sr = _sr(h, w)
        mains = _dendrites(h, w, s, n_roots=70, depth=4, seg=34 * sr, thick=2, spread=0.4)
        cid, edge, orient, axial = _crystal(h, w, s ^ 0x61, n_sites=2600, aniso=1.9, res=0.5)
        mesh = 1.0 - _sstep(0.03, 0.09, edge)
        veins = np.clip(mains * 1.4 + mesh * 0.7, 0, 1)
        membrane = (1.0 - _sstep(0.2, 0.5, veins))
        cellsize = _gauss((edge > 0.2).astype(np.float32), 9)
        return veins, membrane.astype(np.float32), _n01(cellsize), mains

    def spec(F, s, h, w):
        veins, membrane, cellsize, mains = F
        # membrane cells = thin-film panes whose CC level follows CELL SIZE —
        # only the BIG panes ignite (bounded, so the metal floor survives the
        # crush); primary veins = near-max conduits
        # self-calibrating pane gate: top ~35% of the cell-size field ignites,
        # whatever the field's actual distribution is
        q0, q1 = np.quantile(cellsize, [0.55, 0.80])
        panes = _sstep(float(q0), float(q1) + 1e-3, cellsize)
        M = 184 + 55 * mains - 65 * membrane * panes + 30 * veins
        G = 54 + 40 * membrane * (1 - panes) + 26 * (1 - veins)
        B = 80 + 150 * membrane * panes + 120 * mains * (1 - membrane * panes) + 35 * veins * (1 - mains)
        return M, G, B

    def paint(F, src_lum):
        veins, membrane, cellsize, mains = F
        c1 = np.float32([0.10, 0.30, 0.45])
        c2 = np.float32([0.55, 0.85, 0.90])
        c3 = np.float32([0.15, 0.10, 0.20])
        art = (c1[None, None, :] * membrane[..., None] * (0.5 + 0.5 * cellsize)[..., None]
               + c2[None, None, :] * (membrane * cellsize * 0.7)[..., None]
               + c3[None, None, :] * veins[..., None])
        k = np.clip(membrane * 0.6 + veins, 0, 1) * 0.55
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 8. EBRU MARBLE (replaces sonar) ────────────────────────────────────────
# Turkish paper marbling: ink bands combed into feathered chevrons. New logic:
# alternating ink streams + comb displacement field.
@_def("fm_ebru_marble")
def _b_ebru():
    def fields(h, w, s):
        sr = _sr(h, w)
        u, v = _rotuv(h, w, s, 0)
        comb1 = np.sin(v * 2 * np.pi / (9.0 * sr)) * 9.0 * sr
        comb2 = np.sin(v * 2 * np.pi / (38.0 * sr) + 1.3) * 22.0 * sr
        swirl = (_noise(h, w, s ^ 0x71, (60, 150)) - 0.5) * 30 * sr
        uu = u + comb1 + comb2 + swirl
        band = (uu / (7.5 * sr)) % 3.0
        ink_a = ((band >= 0) & (band < 1)).astype(np.float32)
        ink_b = ((band >= 1) & (band < 2)).astype(np.float32)
        ink_c = (band >= 2).astype(np.float32)
        vein = _edge_of(ink_a + ink_b * 2, 1.0)
        return ink_a, ink_b, ink_c, vein

    def spec(F, s, h, w):
        ink_a, ink_b, ink_c, vein = F
        # three inks = three spec identities: A tinted metal, B dielectric blue
        # (bounded ~33%), C textured gold; the combed boundaries are live veins
        M = 150 + 75 * ink_a - 85 * ink_b + 35 * ink_c + 60 * vein
        G = 50 + 60 * ink_c + 25 * (1 - vein)
        B = 84 + 130 * ink_b + 70 * vein + 30 * ink_a
        return M, G, B

    def paint(F, src_lum):
        ink_a, ink_b, ink_c, vein = F
        c1 = np.float32([0.70, 0.12, 0.30])
        c2 = np.float32([0.10, 0.25, 0.65])
        c3 = np.float32([0.92, 0.80, 0.40])
        art = (c1[None, None, :] * ink_a[..., None]
               + c2[None, None, :] * ink_b[..., None]
               + c3[None, None, :] * ink_c[..., None])
        k = np.clip(ink_a + ink_b + ink_c, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 9. BASALT COLUMNS (replaces tread_plate) ───────────────────────────────
# Giant's Causeway columnar basalt end-on: irregular hexagonal columns with
# chipped rims and onion-fracture rings inside each column.
@_def("fm_basalt")
def _b_basalt():
    def fields(h, w, s):
        sr = _sr(h, w)
        cid, edge, orient, axial = _crystal(h, w, s, n_sites=1500, aniso=1.05, res=0.5)
        per = _n01(np.sin(cid * 12.99) + 1)
        joint = 1.0 - _sstep(0.05, 0.14, edge)
        binp = (joint < 0.5).astype(np.uint8)
        dist = cv2.distanceTransform(binp, cv2.DIST_L2, 3)
        chip = _sstep(0.6, 0.8, _noise(h, w, s ^ 0x81, (6, 13))) * ((dist > 0.5) & (dist < 4.5 * sr)).astype(np.float32)
        rings = (0.5 + 0.5 * np.sin(dist * 2 * np.pi / (5.5 * sr) + per * 9)).astype(np.float32) * (joint < 0.5)
        return joint, chip.astype(np.float32), rings, per

    def spec(F, s, h, w):
        joint, chip, rings, per = F
        # columns split into hot/cold clans; chips sparkle; the onion rings give
        # every column its own radial flash signature
        hot = _sstep(0.55, 0.62, per)
        M = 160 + 60 * hot * (1 - joint) + 55 * chip + 35 * rings * (1 - hot)
        G = 60 + 60 * joint + 30 * (1 - rings)
        B = (76 + 178 * (1 - hot) * rings * (1 - chip) + 100 * chip + 55 * joint
             + 26 * per * (1 - rings) * (1 - chip) * (1 - joint))
        return M, G, B

    def paint(F, src_lum):
        joint, chip, rings, per = F
        c1 = np.float32([0.16, 0.17, 0.20])
        c2 = np.float32([0.38, 0.40, 0.46])
        c3 = np.float32([0.70, 0.45, 0.20])
        art = (c1[None, None, :] * (1 - joint)[..., None]
               + c2[None, None, :] * (rings * 0.8)[..., None]
               + c3[None, None, :] * chip[..., None])
        k = np.clip(1 - joint * 0.3 + chip, 0, 1) * 0.45
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 10. MUDCRACK CURL (replaces voronoi_silk) ──────────────────────────────
# Dried lakebed: crack polygons with CURLED LIPS (double-edge offset contour).
@_def("fm_mudcrack")
def _b_mudcrack():
    def fields(h, w, s):
        sr = _sr(h, w)
        cid, edge, orient, axial = _crystal(h, w, s, n_sites=2200, aniso=1.45, res=0.5)
        crack = 1.0 - _sstep(0.030, 0.085, edge)
        binp = (crack < 0.5).astype(np.uint8)
        dist = cv2.distanceTransform(binp, cv2.DIST_L2, 3)
        lip = ((dist > 1.2 * sr) & (dist < 2.6 * sr)).astype(np.float32)
        plate_core = _sstep(3.5 * sr, 7.0 * sr, dist)
        dust = _sstep(0.74, 0.88, _noise(h, w, s ^ 0x91, (2.5, 5.5)))
        return crack, lip, plate_core.astype(np.float32), dust

    def spec(F, s, h, w):
        crack, lip, plate_core, dust = F
        # cracks = deep CC canyons; curled lips = raised metal ridges; plate
        # cores crossfade clans on a macro gradient (the "throughout" travel)
        g = _n01(_noise(h, w, s ^ 0x92, (260, 600)))
        M = 162 + 70 * lip - 55 * crack + 40 * plate_core * g + 30 * dust
        G = 58 + 55 * crack + 26 * (1 - lip)
        B = 84 + 155 * crack + 90 * plate_core * (1 - g) * (1 - crack) + 50 * dust * (1 - crack)
        return M, G, B

    def paint(F, src_lum):
        crack, lip, plate_core, dust = F
        c1 = np.float32([0.48, 0.34, 0.22])
        c2 = np.float32([0.16, 0.10, 0.07])
        c3 = np.float32([0.80, 0.65, 0.45])
        art = (c1[None, None, :] * plate_core[..., None]
               + c2[None, None, :] * crack[..., None]
               + c3[None, None, :] * lip[..., None])
        k = np.clip(crack + lip + plate_core * 0.4, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 11. PENROSE QUASI (replaces wiremesh) ──────────────────────────────────
# Quasicrystal rhombs via the de Bruijn five-grid: 5 plane waves summed and
# thresholded — aperiodic forever, never repeats anywhere on the canvas.
@_def("fm_penrose")
def _b_penrose():
    def fields(h, w, s):
        sr = _sr(h, w)
        yy, xx = _coords(h, w)
        rng = _rng(s, 5)
        ph0 = rng.uniform(0, 2 * np.pi)
        p = 9.5 * sr
        acc = np.zeros((h, w), np.float32)
        for k in range(5):
            a = ph0 + k * 2 * np.pi / 5
            acc += np.cos((xx * np.cos(a) + yy * np.sin(a)) * (2 * np.pi / p) + rng.uniform(0, 6.3))
        nacc = _n01(acc)
        tiles = _sstep(0.52, 0.60, nacc)
        star = _sstep(0.74, 0.88, nacc)
        antistar = _sstep(0.74, 0.88, 1.0 - nacc)
        return tiles, star, antistar, nacc

    def spec(F, s, h, w):
        tiles, star, antistar, field = F
        # 5-fold stars = metal suns, antistars = blue wells; the LOW half of
        # the quasiperiodic field floods CC wholesale (anti-aligned with the
        # tile metal — the blue-insight carve) — aperiodic, never repeats
        M = 158 + 70 * star - 95 * antistar + 45 * tiles
        G = 56 + 40 * (1 - tiles) + 24 * antistar
        B = 70 + 115 * (1 - tiles) + 45 * field * (1 - tiles) + 60 * antistar + 30 * star
        return M, G, B

    def paint(F, src_lum):
        tiles, star, antistar, field = F
        c1 = np.float32([0.30, 0.24, 0.55])
        c2 = np.float32([0.95, 0.75, 0.25])
        c3 = np.float32([0.15, 0.60, 0.85])
        art = (c1[None, None, :] * tiles[..., None]
               + c2[None, None, :] * star[..., None]
               + c3[None, None, :] * antistar[..., None])
        k = np.clip(tiles + star + antistar, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 12. OCTOPUS SUCKERS (replaces origami) ─────────────────────────────────
# Curved arm rows of suckers: ring + cup + pore, sizes tapering along arms.
@_def("fm_octo_suckers")
def _b_octo():
    def fields(h, w, s):
        sr = _sr(h, w)
        rng = _rng(s, 7)
        ring = np.zeros((h, w), np.float32)
        cup = np.zeros((h, w), np.float32)
        pore = np.zeros((h, w), np.float32)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        n_arm = int(520 * sr * sr) + 100
        for _ in range(n_arm):
            x, y = rng.uniform(0, w), rng.uniform(0, h)
            a = rng.uniform(0, 2 * np.pi)
            curv = rng.uniform(-0.08, 0.08)
            R0 = rng.uniform(6.0, 9.0) * sr
            for k in range(16):
                R = R0 * (1 - k * 0.05)
                if R < 1.4 * sr:
                    break
                x += np.cos(a) * R * 2.1
                y += np.sin(a) * R * 2.1
                a += curv
                if not (-20 < x < w + 20 and -20 < y < h + 20):
                    break
                x0, x1 = int(max(0, x - R * 1.4)), int(min(w, x + R * 1.4))
                y0, y1 = int(max(0, y - R * 1.4)), int(min(h, y + R * 1.4))
                if x1 - x0 < 2 or y1 - y0 < 2:
                    continue
                dy = yy[y0:y1, x0:x1] - y
                dx = xx[y0:y1, x0:x1] - x
                r = np.sqrt(dx * dx + dy * dy) / R
                ring[y0:y1, x0:x1] = np.maximum(ring[y0:y1, x0:x1], np.clip(1 - np.abs(r - 0.85) * 5, 0, 1))
                cup[y0:y1, x0:x1] = np.maximum(cup[y0:y1, x0:x1], np.clip(1 - r * 1.45, 0, 1))
                pore[y0:y1, x0:x1] = np.maximum(pore[y0:y1, x0:x1], (r < 0.18).astype(np.float32))
        skin = _sstep(0.5, 0.8, _noise(h, w, s ^ 0xA1, (3, 7)))
        return ring, cup, pore, skin

    def spec(F, s, h, w):
        ring, cup, pore, skin = F
        # rings = metal lips; cup interiors = wet CC pools deepening toward the
        # pore (a radial gradient INSIDE every sucker); papillae shimmer between
        M = 168 + 65 * ring - 50 * cup * (1 - ring) + 25 * skin
        G = 58 + 40 * skin * (1 - cup) + 30 * (1 - ring)
        B = (84 + 150 * np.power(np.clip(cup, 0, 1), 0.45) * (1 - pore)
             + 160 * pore + 80 * ring * (1 - cup) - 18 * skin * (1 - cup) * (1 - ring))
        return M, G, B

    def paint(F, src_lum):
        ring, cup, pore, skin = F
        c1 = np.float32([0.55, 0.20, 0.35])
        c2 = np.float32([0.85, 0.55, 0.60])
        c3 = np.float32([0.25, 0.08, 0.18])
        art = (c1[None, None, :] * (skin * 0.7)[..., None]
               + c2[None, None, :] * ring[..., None]
               + c3[None, None, :] * cup[..., None])
        k = np.clip(ring + cup + skin * 0.4, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ═══════════════════════════════════════════ REBUILDS (10, per owner notes)

# ── 13. PETAL STORM (replaces barbed_wire, owner r14: "make something else.
# Anything.") — a storm of drifting flower petals: curved teardrop stamps at
# every angle and depth, each with a midrib vein. PASTEL spec doctrine
# (owner 2026-06-12): light-pink air, light-blue petals, light-purple ribs.
@_def("fm_petal_storm")
def _b_petalstorm():
    def fields(h, w, s):
        sr = _sr(h, w)
        rng = _rng(s, 29)
        petal = np.zeros((h, w), np.float32)
        rib = np.zeros((h, w), np.float32)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        for _ in range(int(2600 * sr * sr) + 240):
            cx, cy = rng.uniform(0, w), rng.uniform(0, h)
            a = rng.uniform(0, 2 * np.pi)
            L = rng.uniform(7, 15) * sr
            W2 = L * rng.uniform(0.38, 0.55)
            ca, sa = np.cos(a), np.sin(a)
            x0, x1 = int(max(0, cx - L - 2)), int(min(w, cx + L + 2))
            y0, y1 = int(max(0, cy - L - 2)), int(min(h, cy + L + 2))
            if x1 - x0 < 3 or y1 - y0 < 3:
                continue
            dx = xx[y0:y1, x0:x1] - cx
            dy = yy[y0:y1, x0:x1] - cy
            u = dx * ca + dy * sa
            v = -dx * sa + dy * ca
            # teardrop: round base, width tapering to the tip
            t = np.clip((u + L * 0.5) / (L * 1.5), 0, 1)
            wprof = W2 * np.sqrt(np.clip(1.0 - t, 0, 1)) * (0.35 + 0.65 * np.clip(t * 3, 0, 1))
            inside = ((np.abs(v) < wprof) & (u > -L * 0.5) & (u < L)).astype(np.float32)
            mid = (np.abs(v) < 0.9 * sr).astype(np.float32) * inside
            petal[y0:y1, x0:x1] = np.maximum(petal[y0:y1, x0:x1], inside)
            rib[y0:y1, x0:x1] = np.maximum(rib[y0:y1, x0:x1], mid)
        drift = _sstep(0.86, 0.95, _noise(h, w, s ^ 0x201, (3, 7)))
        depth = _n01(_noise(h, w, s ^ 0x202, (90, 220)))
        return petal, rib, drift.astype(np.float32), depth

    def spec(F, s, h, w):
        petal, rib, drift, depth = F
        # PASTEL: light-pink air, light-blue petals, light-purple midribs,
        # light-gray drift specks between
        M = (222 - 62 * petal * (1 - rib) - 28 * petal * rib
             - 34 * drift * (1 - petal) + 8 * depth)
        G = 158 + 18 * petal * (1 - rib) + 6 * rib + 22 * drift * (1 - petal) + 8 * depth
        B = (190 + 46 * petal * (1 - rib) + 44 * petal * rib
             + 6 * drift * (1 - petal) - 8 * depth)
        return M, G, B

    def paint(F, src_lum):
        petal, rib, drift, depth = F
        c1 = np.float32([0.95, 0.75, 0.85])
        c2 = np.float32([0.60, 0.70, 0.98])
        c3 = np.float32([0.80, 0.70, 0.98])
        art = (c1[None, None, :] * ((1 - petal) * drift)[..., None]
               + c2[None, None, :] * (petal * (1 - rib))[..., None]
               + c3[None, None, :] * rib[..., None])
        k = np.clip(petal + drift * 0.4, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 15. HERRINGBONE — "shift not coming through" → comet planks: every plank
# FADES metal->clearcoat along its own length; rows alternate direction.
@_def("fm_herringbone")
def _b_herring():
    def fields(h, w, s):
        sr = _sr(h, w)
        u, v = _rotuv(h, w, s, 2)
        rowp = 5.5 * sr
        band = np.floor(v / rowp) % 2
        uu = np.where(band == 0, u + v, u - v)
        plank_p = 16.0 * sr
        plank_id = np.floor(uu / plank_p)
        along = (uu / plank_p - plank_id).astype(np.float32)       # 0..1 along plank
        gap_u = (np.abs(along - 0.5) > 0.46).astype(np.float32)
        gap_v = (np.abs((v / rowp) - np.floor(v / rowp) - 0.5) > 0.42).astype(np.float32)
        gaps = np.clip(gap_u + gap_v, 0, 1)
        per = _n01(np.sin(plank_id * 12.99 + band * 7.3))
        return along, gaps, per, band.astype(np.float32)

    def spec(F, s, h, w):
        along, gaps, per, band = F
        # comet planks: head = metal blaze, tail = CC pool — direction flips
        # with the herringbone row so the floor shimmers both ways at once
        fade = np.where(band > 0.5, along, 1.0 - along)
        M = 152 + 90 * (1 - fade) * (1 - gaps) + 45 * gaps - 25 * fade
        G = 56 + 45 * gaps + 22 * fade
        # gaps go DEAD-dark in CC: the comet gradient swings against a black
        # grout floor (bimodal carve = strong contrast, not mush)
        B = 70 + 185 * fade * (1 - gaps)
        return M, G, B

    def paint(F, src_lum):
        along, gaps, per, band = F
        c1 = np.float32([0.70, 0.45, 0.20])
        c2 = np.float32([0.30, 0.15, 0.50])
        c3 = np.float32([0.10, 0.08, 0.07])
        fade = np.where(band > 0.5, along, 1.0 - along)
        art = (c1[None, None, :] * ((1 - fade) * (1 - gaps))[..., None]
               + c2[None, None, :] * (fade * (1 - gaps))[..., None]
               + c3[None, None, :] * gaps[..., None])
        k = np.clip(1 - gaps * 0.3, 0, 1) * 0.45
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 17. INFERNO VEINS — "not shifting even crushed" → physics-safe magma:
# metal NEVER collapses; veins are thin CC infernos with graded halos.
@_def("fm_inferno_veins")
def _b_inferno():
    def fields(h, w, s):
        sr = _sr(h, w)
        cid, edge, orient, axial = _crystal(h, w, s, n_sites=7000, aniso=1.7, res=0.5)
        plate = _sstep(0.42, 0.5, _n01(np.sin(cid * 12.99) + 1))
        vein = np.clip((1.0 - _sstep(0.02, 0.06, edge))
                       + _dendrites(h, w, s ^ 0xD1, n_roots=520, depth=4, seg=11 * sr, thick=1), 0, 1)
        halo = np.clip(_gauss(vein, 2.5 * sr) * 3.0, 0, 1)
        shimmer = (0.5 + 0.5 * np.sin(axial * 5.0)).astype(np.float32)
        return plate, vein, halo, shimmer

    def spec(F, s, h, w):
        plate, vein, halo, shimmer = F
        # ROUND-4 PINK FORMULA (this is the finish the owner wrote the formula
        # note on): plates = pink field; vein+halo corridors = light blue
        # (metal drops, clearcoat maxes); sparse embers INSIDE the veins keep
        # mid-metal = the purple dots that make the green glisten explode
        # PASTEL: light-pink plates, light-purple veins, light-blue halo
        # rivers — plus REAL orange embers inside the veins (the owner's
        # "red/orange/yellow concoction" experiment: M max + CC low + G mid)
        ember = _sstep(0.84, 0.94, _noise(h, w, s ^ 0xD3, (3, 7))) * vein
        M = (224 - 66 * halo * (1 - vein) - 30 * vein * (1 - ember) + 28 * ember
             + 6 * shimmer * plate * (1 - halo))
        G = 160 + 18 * halo * (1 - vein) + 2 * vein - 52 * ember + 6 * shimmer * plate
        B = (192 + 46 * halo * (1 - vein) + 42 * vein * (1 - ember) - 140 * ember
             + 6 * shimmer * (1 - plate) * (1 - halo) * (1 - vein))
        return M, G, B

    def paint(F, src_lum):
        plate, vein, halo, shimmer = F
        c1 = np.float32([0.30, 0.16, 0.30])
        c2 = np.float32([0.95, 0.45, 0.85])
        c3 = np.float32([0.55, 0.45, 0.98])
        art = (c1[None, None, :] * plate[..., None]
               + c2[None, None, :] * vein[..., None]
               + c3[None, None, :] * (halo * (1 - vein))[..., None])
        k = np.clip(vein + halo + plate * 0.3, 0, 1) * 0.55
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 18. LABYRINTH — "pattern AND spec won't shift" → spiral labyrinth tiles:
# a grid of mini square-spiral mazes with alternating chirality; corridors
# flood with light by depth-into-the-spiral. New logic entirely.
@_def("fm_labyrinth")
def _b_labyrinth():
    def fields(h, w, s):
        sr = _sr(h, w)
        u, v = _rotuv(h, w, s, 3)
        p = 22.0 * sr
        tu = np.floor(u / p); tv = np.floor(v / p)
        lu = (u / p - tu - 0.5) * 2          # -1..1 in tile
        lv = (v / p - tv - 0.5) * 2
        chir = (_n01(np.sin(tu * 12.99 + tv * 7.31) + 1) > 0.5)
        ang = np.where(chir, np.arctan2(lv, lu), np.arctan2(lu, lv))
        r = np.maximum(np.abs(lu), np.abs(lv))                      # square radius
        spiral = (r * 4.0 + ang / (2 * np.pi)) % 1.0
        wallw = 0.34
        wall = (spiral < wallw).astype(np.float32)
        # 1 - r^2 (not 1 - r): r = max(|u|,|v|) piles up near the tile edge, so
        # the square makes depth UNIFORM across the tile — the flood actually swings
        depth = _n01(1.0 - r * r)                                   # deep = centre
        return wall, depth, (spiral >= wallw).astype(np.float32)

    def spec(F, s, h, w):
        wall, depth, corridor = F
        # corridors flood CC brighter the deeper into each spiral; walls stay
        # tinted metal; tile centres detonate (the minotaur's chamber)
        core = _sstep(0.8, 0.97, depth)
        M = 170 + 50 * wall - 55 * core * corridor + 25 * depth
        G = 58 + 35 * wall + 22 * (1 - depth)
        # walls stay CC-dark: the corridor flood reads against black maze walls
        B = 72 + 175 * corridor * depth * (1 - core) + 178 * core
        return M, G, B

    def paint(F, src_lum):
        wall, depth, corridor = F
        c1 = np.float32([0.20, 0.25, 0.45])
        c2 = np.float32([0.85, 0.70, 0.30])
        c3 = np.float32([0.50, 0.12, 0.55])
        art = (c1[None, None, :] * wall[..., None]
               + c2[None, None, :] * (corridor * depth)[..., None]
               + c3[None, None, :] * _sstep(0.8, 0.97, depth)[..., None])
        k = np.clip(wall + corridor * depth, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 19. NANOWEAVE — "weak all around" → live-fiber nanoweave: micro twill
# with woven-in glowing data threads carrying CC pulses along their length.
@_def("fm_nanoweave")
def _b_nanoweave():
    def fields(h, w, s):
        sr = _sr(h, w)
        u, v = _rotuv(h, w, s, 1)
        p = 3.2 * sr
        tu = np.floor(u / p); tv = np.floor(v / p)
        twill = (((tu + tv * 2) % 4) < 2).astype(np.float32)
        warp_id = np.floor(u / p)
        live = (_n01(np.sin(warp_id * 12.99) + 1) > 0.74).astype(np.float32)   # ~26% live fibers
        pulse = ((v / (26 * sr) + _n01(np.sin(warp_id * 5.77))) % 1.0)
        pulse_dash = (pulse < 0.53).astype(np.float32) * live
        pulse_head = (np.abs(pulse - 0.58) < 0.05).astype(np.float32) * live   # disjoint from dash
        return twill, live, pulse_dash, pulse_head.astype(np.float32)

    def spec(F, s, h, w):
        twill, live, dash, head = F
        # the weave = fine tinted metal; live fibers carry CC current with
        # white-hot pulse heads racing along them
        M = 168 + 45 * twill - 60 * dash + 60 * head
        G = 58 + 30 * (1 - twill) + 20 * dash
        B = 86 + 142 * dash + 148 * head + 20 * twill * (1 - head)
        return M, G, B

    def paint(F, src_lum):
        twill, live, dash, head = F
        c1 = np.float32([0.22, 0.24, 0.30])
        c2 = np.float32([0.10, 0.85, 0.75])
        c3 = np.float32([0.95, 0.95, 1.00])
        art = (c1[None, None, :] * twill[..., None]
               + c2[None, None, :] * dash[..., None]
               + c3[None, None, :] * head[..., None])
        k = np.clip(twill * 0.5 + dash + head, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 20. RIVET ARRAY — "spec makes no sense, repeated" → aircraft skin: large
# brushed panels, rivet lines ONLY along the panel seams, lap-joint shadows;
# every panel's brushed grain runs its own direction.
@_def("fm_rivet_array")
def _b_rivets():
    def fields(h, w, s):
        sr = _sr(h, w)
        cid, edge, orient, axial = _crystal(h, w, s, n_sites=520, aniso=1.6, res=0.5)
        per = _n01(np.sin(cid * 12.99) + 1)
        seam = 1.0 - _sstep(0.035, 0.10, edge)
        binp = (seam < 0.5).astype(np.uint8)
        dist = cv2.distanceTransform(binp, cv2.DIST_L2, 3)
        rivet_band = ((dist > 2.2 * sr) & (dist < 4.4 * sr)).astype(np.float32)
        u, v = _rotuv(h, w, s ^ 0xE1, 0)
        dotline = (0.5 + 0.5 * np.sin((u + v) * 2 * np.pi / (6.5 * sr)))
        rivets = (rivet_band * _sstep(0.72, 0.9, dotline)).astype(np.float32)
        # per-panel brushed grain: orientation from the cell's own angle
        grain = (0.5 + 0.5 * np.sin((np.cos(per * np.pi) *
                 _coords(h, w)[1] + np.sin(per * np.pi) * _coords(h, w)[0]) * 2 * np.pi / (4.5 * sr)))
        grain = _sstep(0.35, 0.65, grain.astype(np.float32)) * (seam < 0.5)
        lap = ((dist > 0.5) & (dist < 1.8 * sr)).astype(np.float32)
        return seam, rivets, grain, lap, per

    def spec(F, s, h, w):
        seam, rivets, grain, lap, per = F
        # panels alternate warm-metal / cool-mirror by per; rivets are CC pins
        # in METAL bands; lap joints shade dark — reads as riveted aluminium
        cool = _sstep(0.76, 0.82, per)
        M = 165 + 45 * grain - 90 * cool * (1 - seam) * (1 - rivets) + 55 * rivets - 30 * lap
        G = 56 + 40 * lap + 24 * (1 - grain)
        B = (80 + 148 * cool * (1 - seam) * (0.42 + 0.58 * grain) * (1 - rivets)
             + 128 * rivets + 28 * lap * (1 - rivets)
             + 26 * grain * (1 - cool) * (1 - seam) * (1 - rivets))
        return M, G, B

    def paint(F, src_lum):
        seam, rivets, grain, lap, per = F
        c1 = np.float32([0.55, 0.58, 0.65])
        c2 = np.float32([0.30, 0.55, 0.70])
        c3 = np.float32([0.12, 0.12, 0.15])
        cool = _sstep(0.6, 0.68, per)
        art = (c1[None, None, :] * (grain * (1 - cool))[..., None]
               + c2[None, None, :] * (cool * (1 - seam))[..., None]
               + c3[None, None, :] * np.clip(seam + lap, 0, 1)[..., None])
        k = np.clip(grain * 0.5 + cool * 0.5 + seam + rivets, 0, 1) * 0.45
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 21. TIGER SLASH — "not coming through" → organic forked tiger stripes:
# tapered, broken, forking ridge stripes; alternating hot/cold stripe clans.
@_def("fm_tiger_slash")
def _b_tiger():
    def fields(h, w, s):
        sr = _sr(h, w)
        u, v = _rotuv(h, w, s, 18)
        carrier = np.sin(u * 2 * np.pi / (9.0 * sr)
                         + (_noise(h, w, s ^ 0xF1, (40, 110)) - 0.5) * 7.0)
        taper = _noise(h, w, s ^ 0xF2, (60, 150))
        stripe = _sstep(0.30, 0.45, _n01(carrier) * _sstep(0.25, 0.6, taper))
        sid = np.floor(u / (9.0 * sr) + 0.5)
        clan = (_n01(np.sin(sid * 12.99) + 1) > 0.5).astype(np.float32)
        edge = _edge_of(stripe, 1.0)
        return stripe, clan, edge, _n01(carrier)

    def spec(F, s, h, w):
        stripe, clan, edge, carrier = F
        # stripe clans alternate identities: clan A = blue mirror slashes,
        # clan B = molten metal slashes; a cross-stripe gradient sweeps both
        g = _n01(_noise(h, w, s ^ 0xF3, (260, 580)))
        M = 168 + 60 * stripe * clan - 90 * stripe * (1 - clan) * g + 45 * edge
        G = 56 + 35 * (1 - stripe) + 22 * edge
        B = 88 + 135 * stripe * (1 - clan) + 65 * stripe * clan * (1 - g) + 45 * edge
        return M, G, B

    def paint(F, src_lum):
        stripe, clan, edge, carrier = F
        c1 = np.float32([0.95, 0.55, 0.10])
        c2 = np.float32([0.12, 0.10, 0.10])
        c3 = np.float32([0.90, 0.85, 0.80])
        art = (c1[None, None, :] * (stripe * clan)[..., None]
               + c2[None, None, :] * (stripe * (1 - clan))[..., None]
               + c3[None, None, :] * (edge * 0.8)[..., None])
        k = np.clip(stripe + edge * 0.4, 0, 1) * 0.55
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 22. TOPO LINES — "pattern in spec ALL WRONG" → bathymetric glow: the
# elevation FIELD drives the spec (high ground floods with light), contour
# lines ride as metal threads, basin floors pool blue (bounded).
@_def("fm_topo_lines")
def _b_topo():
    def fields(h, w, s):
        sr = _sr(h, w)
        elev = _noise(h, w, s ^ 0x102, (50, 120, 280))
        band = (elev * 44) % 1.0
        line = (band < 0.38).astype(np.float32)
        # NOTE: _sstep clamps a reversed-edge denominator to +1e-6 — inverted
        # ramps MUST be written as 1 - _sstep(lo, hi, x)
        basin = 1.0 - _sstep(0.05, 0.18, elev)            # lowest ground (bounded)
        peak = _sstep(0.78, 0.92, elev)
        return line, _n01(elev), basin, peak

    def spec(F, s, h, w):
        line, elev, basin, peak = F
        # THE FIELD is the spec: CC floods with altitude (contrast-stretched so
        # the flood actually swings), peaks detonate, basins pool blue-mirror
        # (bounded area — metal floor survives the crush), contours metal
        elev_c = _sstep(0.28, 0.72, elev)
        alt = (np.floor(elev * 44) % 2).astype(np.float32)   # alternating intervals
        M = 172 + 50 * line + 35 * peak - 55 * basin * (1 - line)
        G = 58 + 30 * (1 - line) + 20 * basin
        # the flood is striped by alternating contour intervals so the carve
        # stays FINE (banded highlands, not blobs)
        B = (56 + 150 * elev_c * (0.50 + 0.50 * alt) + 42 * peak * alt - 18 * line
             + 95 * basin * (1 - elev_c))
        return M, G, B

    def paint(F, src_lum):
        line, elev, basin, peak = F
        c1 = np.float32([0.10, 0.30, 0.50])
        c2 = np.float32([0.90, 0.75, 0.35])
        c3 = np.float32([0.95, 0.95, 0.90])
        art = (c1[None, None, :] * ((1 - elev) * 0.9)[..., None]
               + c2[None, None, :] * (elev * 0.9)[..., None]
               + c3[None, None, :] * (line * 0.9 + peak * 0.5)[..., None])
        k = np.clip(0.45 + line * 0.3, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ═══════════════════════════ ROUND 4 (2026-06-12, owner verdict-driven)
# THE PINK FORMULA (owner, from LABYRINTH r81): combined spec = PINK field
# (M high + CC mid-high) with bounded LIGHT-BLUE pools (M drops, CC maxes)
# holding PURPLE DOTS (mid-M specks inside the pools) — "the blue with the
# little purple dots is where the magic is happening... glistening GREEN
# pops through on the purple base. It's exploding when it hits it."

# ── 23. GEODE SLICE (replaces feather_fall, r29) ───────────────────────────
# Agate geode cross-section: wobbling growth bands nested around scattered
# seed cores, every 4th band flooding blue, druzy crystal dots in the cores.
@_def("fm_geode_slice")
def _b_geode():
    def fields(h, w, s):
        sr = _sr(h, w)
        rng = _rng(s, 17)
        seeds = np.ones((h, w), np.uint8)
        for _ in range(int(70 * sr * sr) + 16):
            seeds[int(rng.uniform(0, h)), int(rng.uniform(0, w))] = 0
        dist = cv2.distanceTransform(seeds, cv2.DIST_L2, 5)
        dd = dist + (_noise(h, w, s ^ 0x121, (10, 24, 55)) - 0.5) * 9.0 * sr
        p = 5.4 * sr
        band01 = (0.5 + 0.5 * np.sin(dd * 2 * np.pi / p)).astype(np.float32)
        bandline = _sstep(0.58, 0.82, band01)
        bluering = ((np.floor(dd / p) % 3) == 1).astype(np.float32) * bandline
        core = 1.0 - _sstep(3.0 * sr, 5.0 * sr, dist)
        druzy = _sstep(0.85, 0.94, _noise(h, w, s ^ 0x122, (2.5, 5.5))) * _sstep(0.4, 0.7, core)
        return band01, bandline, bluering, core.astype(np.float32), druzy.astype(np.float32)

    def spec(F, s, h, w):
        band01, bandline, bluering, core, druzy = F
        # pink banded field; every 4th band + the seed cores = blue pools;
        # druzy crystal specks inside the cores = the purple dots
        # PASTEL doctrine (owner round-5: "Needs to be LIGHT PINK and LIGHT
        # blue in the spec"): light-pink banded field, LIGHT-blue rings+cores,
        # light-purple druzy, rare gold ember sparks in the druzy
        pool = np.clip(bluering + core, 0, 1)
        ember = _sstep(0.93, 0.985, _noise(h, w, s ^ 0x123, (2.0, 4.5))) * core
        M = (222 + 10 * bandline * (1 - pool) - 64 * pool * (1 - druzy)
             - 27 * pool * druzy + 30 * ember)
        G = 160 + 16 * pool + 14 * (band01 - 0.5) - 4 * bandline - 52 * ember
        B = (192 + 46 * pool * (1 - druzy) + 43 * pool * druzy
             - 6 * bandline * (1 - pool) - 138 * ember)
        return M, G, B

    def paint(F, src_lum):
        band01, bandline, bluering, core, druzy = F
        c1 = np.float32([0.75, 0.55, 0.90])
        c2 = np.float32([0.95, 0.60, 0.80])
        c3 = np.float32([0.98, 0.95, 1.00])
        art = (c1[None, None, :] * (bandline * (1 - bluering))[..., None]
               + c2[None, None, :] * bluering[..., None]
               + c3[None, None, :] * (core + druzy)[..., None] * 0.8)
        k = np.clip(bandline + core + druzy, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 24. THOUSAND EYES (replaces honeycomb, r37 — owner: "Horror inspired") ──
# A field of almond eyes staring out of the paint: vesica lids, striated
# irises, void pupils, bloodshot vein dendrites crawling between them.
@_def("fm_thousand_eyes")
def _b_eyes():
    def fields(h, w, s):
        sr = _sr(h, w)
        rng = _rng(s, 19)
        sclera = np.zeros((h, w), np.float32)
        iris = np.zeros((h, w), np.float32)
        pupil = np.zeros((h, w), np.float32)
        spokes = np.zeros((h, w), np.float32)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        for _ in range(int(1600 * sr * sr) + 200):
            cx, cy = rng.uniform(0, w), rng.uniform(0, h)
            a = rng.uniform(0, np.pi)
            L = rng.uniform(7, 13) * sr
            b2 = L * rng.uniform(0.42, 0.60)
            ca, sa = np.cos(a), np.sin(a)
            x0, x1 = int(max(0, cx - L - 2)), int(min(w, cx + L + 2))
            y0, y1 = int(max(0, cy - L - 2)), int(min(h, cy + L + 2))
            if x1 - x0 < 3 or y1 - y0 < 3:
                continue
            dx = xx[y0:y1, x0:x1] - cx
            dy = yy[y0:y1, x0:x1] - cy
            u = dx * ca + dy * sa
            v = -dx * sa + dy * ca
            c_off = b2 * 1.15
            r1 = (u / L) ** 2 + ((v - c_off) / (b2 * 2.0)) ** 2
            r2 = (u / L) ** 2 + ((v + c_off) / (b2 * 2.0)) ** 2
            inside = ((r1 < 1) & (r2 < 1)).astype(np.float32)
            ri = np.sqrt(u * u + v * v) / (b2 * 0.95)
            ir = ((ri < 1.0) & (ri > 0.45)).astype(np.float32) * inside
            pu = (ri <= 0.45).astype(np.float32) * inside
            sp = (np.sin(np.arctan2(v, u) * 9 + rng.uniform(0, 6.3)) > 0.55).astype(np.float32) * ir
            sclera[y0:y1, x0:x1] = np.maximum(sclera[y0:y1, x0:x1], inside * (1 - ir) * (1 - pu))
            iris[y0:y1, x0:x1] = np.maximum(iris[y0:y1, x0:x1], ir)
            pupil[y0:y1, x0:x1] = np.maximum(pupil[y0:y1, x0:x1], pu)
            spokes[y0:y1, x0:x1] = np.maximum(spokes[y0:y1, x0:x1], sp)
        veins = _dendrites(h, w, s ^ 0x131, n_roots=700, depth=4, seg=12 * sr, thick=1)
        veins = (veins * (iris < 0.5) * (pupil < 0.5)).astype(np.float32)
        return sclera, iris, pupil, spokes, veins

    def spec(F, s, h, w):
        sclera, iris, pupil, spokes, veins = F
        # skin + sclera = pink field; irises = blue pools, their striation
        # spokes = the purple dots; pupils = dead voids (both channels dark —
        # the horror reads in the shift: eyes glisten, pupils stare back black)
        # PASTEL horror: light-pink sclera field, LIGHT-blue irises with
        # light-purple striation spokes, light-gray vein webbing — pupils
        # stay dead-dark voids (the stare needs the contrast)
        M = (224 + 4 * sclera - 64 * iris * (1 - spokes) - 28 * iris * spokes
             - 150 * pupil - 36 * veins * (1 - iris) * (1 - pupil))
        G = (160 + 12 * sclera + 16 * iris * (1 - spokes) + 2 * iris * spokes
             - 100 * pupil + 22 * veins * (1 - iris) * (1 - pupil))
        B = (192 + 4 * sclera + 44 * iris - 130 * pupil
             + 4 * veins * (1 - iris) * (1 - pupil))
        return M, G, B

    def paint(F, src_lum):
        sclera, iris, pupil, spokes, veins = F
        c1 = np.float32([0.92, 0.88, 0.80])
        c2 = np.float32([0.55, 0.35, 0.85])
        c3 = np.float32([0.06, 0.04, 0.08])
        art = (c1[None, None, :] * sclera[..., None]
               + c2[None, None, :] * iris[..., None]
               + c3[None, None, :] * pupil[..., None]
               + np.float32([0.85, 0.20, 0.25])[None, None, :] * (veins * 0.7)[..., None])
        k = np.clip(sclera + iris + pupil + veins * 0.5, 0, 1) * 0.55
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ═══════════════ THE BLUE FLIPS (owner: "Flip it... MOSTLY blue in the
# combined spec channel. That may create a finish I've never even dreamed
# of.") — CC-dominant fields, bounded purple metal dots, subtle light pinks.

# ── 25. GLACIER CORE ────────────────────────────────────────────────────────
# Glacial ice from above: crevasse web over deep-ice windows, frost ridges.
@_def("fm_glacier_core")
def _b_glacier():
    def fields(h, w, s):
        sr = _sr(h, w)
        cid, edge, orient, axial = _crystal(h, w, s, n_sites=240, aniso=1.3, res=0.5)
        crev = 1.0 - _sstep(0.025, 0.075, edge)
        per = _n01(np.sin(cid * 12.99) + 1)
        window = _sstep(0.62, 0.70, per)
        grain = _sstep(0.55, 0.80, _noise(h, w, s ^ 0x141, (3, 8, 18)))
        ridge = (_sstep(0.55, 0.80, _gauss(crev, 2.0 * sr)) * (crev < 0.5)
                 * _sstep(0.72, 0.86, _noise(h, w, s ^ 0x143, (6, 14))))
        depth = _n01(_noise(h, w, s ^ 0x142, (120, 300)))
        return crev, window, grain.astype(np.float32), ridge.astype(np.float32), depth

    def spec(F, s, h, w):
        crev, window, grain, ridge, depth = F
        # MOSTLY-BLUE flip: the ice field is the mirror (CC dominant, metal
        # low); crevasse lines = purple veins; sparse frost ridges = light pink
        # PASTEL flip: LIGHT-blue ice field (metal stays high enough for the
        # body color to glow through), light-purple crevasses, light-pink
        # frost ridges, light-gray grain shimmer
        M = (160 + 42 * crev + 14 * grain * (1 - crev) - 18 * window * (1 - crev)
             + 64 * ridge * (1 - crev))
        G = 178 - 14 * crev + 6 * grain * (1 - window) - 14 * ridge * (1 - crev)
        B = 236 + 6 * window + 6 * depth - 20 * crev - 44 * ridge * (1 - crev)
        return M, G, B

    def paint(F, src_lum):
        crev, window, grain, ridge, depth = F
        c1 = np.float32([0.55, 0.75, 0.95])
        c2 = np.float32([0.25, 0.35, 0.80])
        c3 = np.float32([0.95, 0.80, 0.90])
        art = (c1[None, None, :] * (grain * (1 - window))[..., None]
               + c2[None, None, :] * window[..., None]
               + c3[None, None, :] * (ridge + crev * 0.5)[..., None])
        k = np.clip(grain * 0.5 + window + crev + ridge, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 26. FROST LACE ──────────────────────────────────────────────────────────
# Window frost: fern-crystal lace growing across a blue-mirror pane; the
# crystals are the metal (inverted role vs every vein finish so far).
@_def("fm_frost_lace")
def _b_frostlace():
    def fields(h, w, s):
        sr = _sr(h, w)
        lace = _dendrites(h, w, s, n_roots=1700, depth=5, seg=13 * sr, thick=1, spread=0.8)
        fuzz = np.clip(_gauss(lace, 1.1 * sr) * 2.2, 0, 1)
        sparse = 1.0 - np.clip(_gauss(lace, 3.0 * sr) * 1.6, 0, 1)
        tips = (_sstep(0.6, 0.9, lace) * _sstep(0.55, 0.85, sparse)).astype(np.float32)
        sheen = _n01(_noise(h, w, s ^ 0x151, (40, 100)))
        return lace, fuzz.astype(np.float32), tips, sheen

    def spec(F, s, h, w):
        lace, fuzz, tips, sheen = F
        # PASTEL rebuild (owner r63: blue should let the body color EXPLODE
        # through). Light-blue pane keeps metal HIGH (tinted lobe = your color)
        # while clearcoat maxes; lace = light gray, tips = light pink
        M = 158 + 40 * fuzz * (1 - tips) + 70 * tips + 8 * sheen * (1 - fuzz)
        G = 178 + 6 * fuzz * (1 - tips) - 16 * tips - 8 * sheen * (1 - fuzz)
        B = 236 - 40 * fuzz * (1 - tips) - 44 * tips + 4 * sheen * (1 - fuzz)
        return M, G, B

    def paint(F, src_lum):
        lace, fuzz, tips, sheen = F
        c1 = np.float32([0.50, 0.65, 0.95])
        c2 = np.float32([0.80, 0.70, 0.98])
        c3 = np.float32([0.98, 0.85, 0.92])
        art = (c1[None, None, :] * (sheen * (1 - fuzz) * 0.6)[..., None]
               + c2[None, None, :] * fuzz[..., None]
               + c3[None, None, :] * tips[..., None])
        k = np.clip(fuzz + tips + sheen * 0.3, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 27. ION DRIFT ───────────────────────────────────────────────────────────
# Charged plasma streams drifting through a blue mirror field, pulse heads
# burning light-pink, star pinpricks between the streams.
@_def("fm_ion_drift")
def _b_iondrift():
    def fields(h, w, s):
        sr = _sr(h, w)
        th = _flow_theta(h, w, s, scale=160)
        streams = _n01(_flowlines(h, w, s, n=2600, steps=85, step_len=2.4,
                                  theta=th, thick=1, fade=True))
        core = _sstep(0.28, 0.62, streams)
        heads = _sstep(0.78, 0.94, streams)
        stars = _sstep(0.93, 0.985, _noise(h, w, s ^ 0x161, (2.0, 4.5)))
        drift = _n01(_noise(h, w, s ^ 0x162, (150, 380)))
        return streams, core, heads, stars.astype(np.float32), drift

    def spec(F, s, h, w):
        streams, core, heads, stars, drift = F
        # PASTEL flip: light-blue plasma field, light-purple stream cores,
        # light-pink pulse heads, light-gray star pinpricks
        M = 158 + 44 * core * (1 - heads) + 68 * heads + 38 * stars * (1 - core) + 10 * drift
        G = 180 - 16 * core * (1 - heads) - 20 * heads + 6 * drift
        B = (236 + 4 * _sstep(0.2, 0.5, streams) * (1 - core)
             - 24 * core * (1 - heads) - 44 * heads - 40 * stars * (1 - core))
        return M, G, B

    def paint(F, src_lum):
        streams, core, heads, stars, drift = F
        c1 = np.float32([0.35, 0.50, 0.95])
        c2 = np.float32([0.70, 0.55, 0.98])
        c3 = np.float32([0.98, 0.75, 0.88])
        art = (c1[None, None, :] * (_sstep(0.2, 0.6, streams))[..., None]
               + c2[None, None, :] * core[..., None]
               + c3[None, None, :] * (heads + stars * 0.6)[..., None])
        k = np.clip(streams + stars * 0.5, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 28. TIDE GLASS ──────────────────────────────────────────────────────────
# Sunlight caustics on a pool floor: two interfering ridge webs over deep
# blue glass, web nodes sparking light-pink.
@_def("fm_tide_glass")
def _b_tideglass():
    def fields(h, w, s):
        sr = _sr(h, w)
        r1 = 1.0 - np.abs(_noise(h, w, s, (14, 30)) * 2 - 1)
        r2 = 1.0 - np.abs(_noise(h, w, s ^ 0x171, (8, 17)) * 2 - 1)
        web = _sstep(0.78, 0.92, r1 * 0.55 + r2 * 0.45)
        nodes = _sstep(0.90, 0.97, r1 * r2)
        depthg = _n01(_noise(h, w, s ^ 0x172, (130, 320)))
        return web, nodes, depthg, _n01(r1)

    def spec(F, s, h, w):
        web, nodes, depthg, r1 = F
        # PASTEL flip: light-blue pool floor, light-purple caustic web,
        # light-pink web nodes, light-gray depth swell
        M = 158 + 48 * web * (1 - nodes) + 66 * nodes + 32 * depthg * (1 - web)
        G = 180 - 16 * web * (1 - nodes) - 14 * nodes + 6 * depthg * (1 - web)
        B = 238 - 4 * web * (1 - nodes) - 44 * nodes - 38 * depthg * (1 - web)
        return M, G, B

    def paint(F, src_lum):
        web, nodes, depthg, r1 = F
        c1 = np.float32([0.30, 0.55, 0.90])
        c2 = np.float32([0.75, 0.60, 0.98])
        c3 = np.float32([0.98, 0.80, 0.90])
        art = (c1[None, None, :] * (r1 * 0.5)[..., None]
               + c2[None, None, :] * web[..., None]
               + c3[None, None, :] * nodes[..., None])
        k = np.clip(web + nodes + r1 * 0.3, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ── 29. WITCHLIGHT ──────────────────────────────────────────────────────────
# Drifting ghost-orbs with wisp tails over the deepest blue mirror: cores
# light-pink, halos hard blue, tails trailing purple.
@_def("fm_witchlight")
def _b_witchlight():
    def fields(h, w, s):
        sr = _sr(h, w)
        rng = _rng(s, 23)
        core = np.zeros((h, w), np.float32)
        halo = np.zeros((h, w), np.float32)
        tail = np.zeros((h, w), np.float32)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        for _ in range(int(700 * sr * sr) + 120):
            x, y = rng.uniform(0, w), rng.uniform(0, h)
            R = rng.uniform(4.0, 9.0) * sr
            a = rng.uniform(0, 2 * np.pi)
            for k in range(7):
                f = 1.0 - k / 7.0
                px, py = x - np.cos(a) * R * 1.15 * k, y - np.sin(a) * R * 1.15 * k
                rr = R * (0.45 + 0.55 * f)
                x0, x1 = int(max(0, px - rr * 1.8)), int(min(w, px + rr * 1.8))
                y0, y1 = int(max(0, py - rr * 1.8)), int(min(h, py + rr * 1.8))
                if x1 - x0 < 2 or y1 - y0 < 2:
                    continue
                d = np.sqrt((xx[y0:y1, x0:x1] - px) ** 2 + (yy[y0:y1, x0:x1] - py) ** 2) / rr
                if k == 0:
                    core[y0:y1, x0:x1] = np.maximum(core[y0:y1, x0:x1], np.clip(1 - d * 1.15, 0, 1))
                    halo[y0:y1, x0:x1] = np.maximum(halo[y0:y1, x0:x1], np.clip(1 - np.abs(d - 1.2) * 2.4, 0, 1))
                else:
                    tail[y0:y1, x0:x1] = np.maximum(tail[y0:y1, x0:x1], np.clip(1 - d, 0, 1) * f)
        skin = _sstep(0.5, 0.85, _noise(h, w, s ^ 0x181, (4, 9)))
        return core, halo, tail, skin

    def spec(F, s, h, w):
        core, halo, tail, skin = F
        # PASTEL flip: light blue-gray mist field, light-blue halos,
        # light-pink orb cores, light-purple wisp tails
        corep = _sstep(0.28, 0.68, core)
        mist = _n01(_noise(h, w, s ^ 0x182, (140, 340)))
        M = (178 + 56 * corep + 24 * tail * (1 - corep)
             - 24 * halo * (1 - corep) * (1 - tail) + 6 * skin + 12 * mist)
        G = 182 - 14 * corep - 16 * halo * (1 - corep) + 4 * skin
        B = (200 + 36 * halo * (1 - corep) - 14 * corep + 34 * tail * (1 - corep)
             + 8 * mist * (1 - halo) * (1 - corep))
        return M, G, B

    def paint(F, src_lum):
        core, halo, tail, skin = F
        c1 = np.float32([0.98, 0.78, 0.88])
        c2 = np.float32([0.40, 0.60, 0.98])
        c3 = np.float32([0.65, 0.50, 0.95])
        art = (c1[None, None, :] * _sstep(0.45, 0.85, core)[..., None]
               + c2[None, None, :] * halo[..., None]
               + c3[None, None, :] * tail[..., None])
        k = np.clip(core + halo + tail + skin * 0.2, 0, 1) * 0.5
        return art, k

    return {"fields": fields, "spec": spec, "paint": paint}


# ════════════════════════════════════════════════ WIRING
_V3_RETIRED = {
    "fm_orbit_swarm": "fm_python_skin", "fm_serpentine": "fm_diamondback",
    "fm_perforated": "fm_stingray", "fm_pin_matrix": "fm_gila_bead",
    "fm_scale_armor": "fm_croc_hide", "fm_thorn_bramble": "fm_tortoise",
    "fm_shatter_web": "fm_dragonfly", "fm_sonar": "fm_ebru_marble",
    "fm_tread_plate": "fm_basalt", "fm_voronoi_silk": "fm_mudcrack",
    "fm_wiremesh": "fm_penrose", "fm_origami": "fm_octo_suckers",
    # round 4 (2026-06-12): owner verdicts r29/r37 — replaced outright.
    # These ids ALSO exist in fractured_minds_2026 (v2), so they must be
    # retired here or the old v2 versions resurface when v3 stops shadowing.
    "fm_feather_fall": "fm_geode_slice", "fm_honeycomb": "fm_thousand_eyes",
    # round 5 (2026-06-12): owner r14 — barbed wire concept abandoned entirely.
    "fm_barbed_wire": "fm_petal_storm",
}


def _v3_mk(fid):
    d = V3[fid]

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        F = _v3_fields(fid, _WORKV, _WORKV, _seed_int(seed))
        M, G, B = d["spec"](F, _seed_int(seed), _WORKV, _WORKV)
        smf = float(sm)
        if abs(smf - 1.0) > 0.01:
            M = 128 + (np.asarray(M, np.float32) - 128) * (1 + (min(smf, 2.0) - 1) * 0.42)
        M, G, B = [cv2.resize(np.clip(np.asarray(a, np.float32), 0, 255), (fw, fh),
                              interpolation=cv2.INTER_LINEAR) for a in (M, G, B)]
        out = np.zeros((fh, fw, 4), np.uint8)
        mm = np.clip(m2, 0, 1)
        inv = 1.0 - mm
        out[:, :, 0] = np.clip(M * mm + 4.0 * inv, 0, 255)
        out[:, :, 1] = np.clip(np.clip(G, 16, 255) * mm + 120.0 * inv, 0, 255)
        out[:, :, 2] = np.clip(np.clip(B, 16, 255) * mm + 16.0 * inv, 0, 255)
        out[:, :, 3] = 255
        return out

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.max() > 1.5:
            src = src / 255.0
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        F = _v3_fields(fid, _WORKV, _WORKV, _seed_int(seed))
        art_w, k_w = d["paint"](F, None)
        art = cv2.resize(np.clip(art_w, 0, 1), (fw, fh), interpolation=cv2.INTER_LINEAR)
        k = cv2.resize(np.clip(k_w, 0, 1), (fw, fh), interpolation=cv2.INTER_LINEAR)
        lum = np.clip(src.mean(2, keepdims=True) * 2.2, 0, 1)
        strength = np.clip(m2 * float(pm), 0, 1)
        kk = (k * strength)[..., None]
        out = np.clip(src * (1.0 - kk) + art * lum * kk, 0, 1)
        return out.astype(np.float32)

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    entries = {}
    for fid in V3:
        entries[fid] = _v3_mk(fid)
        mono_reg[fid] = entries[fid]
    for old in _V3_RETIRED:
        mono_reg.pop(old, None)
    try:
        import engine.expansions.fusions as _fus
        _fus.FUSION_REGISTRY.update(entries)
        for old in _V3_RETIRED:
            _fus.FUSION_REGISTRY.pop(old, None)
    except Exception:
        pass
    return ("fractured-minds v3: %d bespoke rebuilds/replacements live, %d retired"
            % (len(entries), len(_V3_RETIRED)))
