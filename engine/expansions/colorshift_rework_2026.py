# ============================================================================
# engine/expansions/colorshift_rework_2026.py
# TOTAL REWORK (owner mandate 2026-06-09) of five color-shift categories with
# the engine/color_science toolkit + the fineness doctrine:
#   IRIDESCENT INSECTS (10) · ANIME INSPIRED (10) · NEON UNDERGROUND (10)
#   CHAMELEON (15) · PRIZM (29)  — 74 monolithics, same ids/names, brand-new
# algorithms: OKLab perceptual ramps, Beer–Lambert absorption, quantized
# interference, perceptual flip lattices, hue-travel roughness corridors, and
# decorrelated M/R/Cc choreography. CRUSHED-FINE detail per the owner doctrine
# ("2048 covers an ENTIRE CAR — 4-50x finer than looks right on a swatch").
#
# Registration: applied LAST over the originals via
# shokker_engine_v2._spb_apply_colorshift_rework_2026() (same two call sites
# as the owner_review_chameleon override, so it lands after every prior
# override of these ids and still gets the monolithic contract guards).
#
# CONTRACT: REWORK_MONOLITHICS[id] = (spec_fn, paint_fn)
#   paint_fn(paint, shape, mask, seed, pm, bb) -> float32 HxWx3/4 in [0,1]
#   spec_fn(shape, mask, seed, sm)            -> uint8  HxWx4 (M,R,Cc,A)
# Floors R>=15, Cc>=16; outside-mask M~4/R~120/Cc~80 (handled by _pack_spec).
#
# 2-copy file (root → electron-app/server via runtime-sync-manifest.json).
# ============================================================================
from __future__ import annotations

import numpy as np
import cv2

from engine.core import multi_scale_noise
from engine.color_science import (
    oklch_ramp,
    candy_absorb,
    interference_palette,
    tri_partition,
    flip_lattice,
    srgb_to_linear,
    linear_to_srgb,
    feature_fineness,
)
# Proven, perf-optimized plumbing (windowed scatter splats etc.) — single source.
from engine.paint_v2.fable_collection import (
    _shape2,
    _seed_of,
    _work_shape,
    _mask2,
    _msc,
    _coords,
    _edge,
    _scatter_field,
    _upscale,
    _pack_spec,
    _blend_paint,
)

# === REWORK FINISH BLOCKS ARE APPENDED BELOW (one block per finish) =========


# === IRIDESCENT INSECTS rework via recipe_kit (2026-06-10) ===
from engine.recipe_kit import (micro_scatter as _rk_sc, micro_voronoi as _rk_vor,
                               filament_web as _rk_web, flow_grain as _rk_gr,
                               ring_swarm as _rk_rings, ramp_lut as _rk_lut,
                               ramp_apply as _rk_ramp, per_label_lut as _rk_cell,
                               noise01 as _rk_n)


def _rw_pair(fid, paint_build, spec_build):
    def spec_fn(shape, mask, seed, sm, _b=spec_build, _f=fid):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        M, R, Cc = _b(h, w, _seed_of(_f, seed))
        M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
        return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)
    def paint_fn(paint, shape, mask, seed, pm, bb, _b=paint_build, _f=fid):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        eff = np.clip(_b(h, w, _seed_of(_f, seed)), 0, 1)
        eff = np.clip(eff * (0.52 + _rk_n(h, w, _seed_of(_f, seed) ^ 99, (2, 5))[..., None] * 0.88), 0, 1)
        return _blend_paint(paint, _upscale(eff, fh, fw), _mask2(mask, fh, fw), pm)
    return spec_fn, paint_fn


def _rwi_jewel_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 40))
    cells = _rk_cell(lab, s ^ 2, _rk_lut([(0.05, 0.45, 0.22), (0.55, 0.10, 0.45), (0.08, 0.30, 0.50)], 0.5))
    return cells * (1.0 - edge[..., None] * 0.75) + interference_palette(np.clip(d1 / max(d1.max(), 1e-5), 0, 1), 2.5, 0.7)[..., :3] * 0.22

def _rwi_jewel_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 40))
    rng = np.random.default_rng(s ^ 3)
    bright = (rng.random(int(lab.max()) + 1) > 0.55).astype(np.float32)[lab]
    return (24 + bright * (1 - edge) * 210,
            np.clip(200 - _rk_gr(h, w, s ^ 4, 3, 4.0) * 145, 15, 255),
            26 + _rk_n(h, w, s ^ 5, (30, 70)) * 60 + np.clip(d1 / max(d1.max(), 1e-5), 0, 1) * 120)


def _rwi_rainbow_paint(h, w, s):
    rings = _rk_rings(h, w, s ^ 1, 3600, 3.2, 1.6)
    th = np.clip(cv2.GaussianBlur(rings, (0, 0), 0.8) + _rk_n(h, w, s ^ 2, (3, 7)) * 0.3, 0, 1)
    return interference_palette(th, 3.0, 0.75, base_srgb=np.float32([0.30, 0.28, 0.30]))

def _rwi_rainbow_spec(h, w, s):
    rings = _rk_rings(h, w, s ^ 1, 3600, 3.2, 1.6)
    return (22 + rings * 220,
            np.clip(205 - _rk_gr(h, w, s ^ 3, 2, 3.5) * 150, 15, 255),
            28 + cv2.GaussianBlur(rings, (0, 0), 2.4) * 160)


def _rwi_morpho_paint(h, w, s):
    rows = _rk_gr(h, w, s ^ 1, 5, 3.2)
    flip = flip_lattice((h, w), s ^ 2, 1.2, 0.45)
    blue = _rk_ramp(np.clip(rows, 0, 1), _rk_lut([(0.02, 0.10, 0.45), (0.10, 0.45, 0.95)], 0.55))
    dark = np.float32([0.06, 0.04, 0.12])[None, None, :]
    return blue * flip[..., None] + dark * (1 - flip[..., None]) * (0.7 + rows[..., None] * 0.5)

def _rwi_morpho_spec(h, w, s):
    flip = flip_lattice((h, w), s ^ 2, 1.2, 0.45)
    rows = _rk_gr(h, w, s ^ 3, 5, 3.2)
    return (18 + flip * 215, np.clip(55 + rows * 130, 15, 255), 26 + _rk_n(h, w, s ^ 4, (40, 90)) * 145)


def _rwi_monarch_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 110))
    veins = _rk_web(h, w, s ^ 2, 1000, k=2)
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    amber = candy_absorb(np.full((h, w, 3), 0.85, np.float32), np.float32([0.85, 0.45, 0.10]), 0.5 + d1n * 1.3)
    dots = _rk_sc(h, w, s ^ 3, 1800, 1.3, "dot")
    return amber * (1 - veins[..., None] * 0.9) * (1 - edge[..., None] * 0.5) + dots[..., None] * 0.85

def _rwi_monarch_spec(h, w, s):
    veins = _rk_web(h, w, s ^ 2, 1000, k=2)
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 110))
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    return (20 + (1 - veins) * (1 - edge) * 170 + _rk_sc(h, w, s ^ 3, 1800, 1.3, "dot") * 60,
            np.clip(210 - _rk_n(h, w, s ^ 4, (3, 8)) * 150 + veins * 30, 15, 255),
            28 + (1 - veins) * d1n * 150)


def _rwi_dragonfly_paint(h, w, s):
    veins = _rk_web(h, w, s ^ 1, 7000, k=2)
    film = interference_palette(_rk_n(h, w, s ^ 2, (7, 16)), 2.0, 0.5) * 0.45
    smoke = _rk_ramp(_rk_n(h, w, s ^ 3, (3, 7)), _rk_lut([(0.55, 0.58, 0.60), (0.75, 0.78, 0.80)], 0.6))
    return smoke * 0.45 + film * (1 - veins[..., None]) + veins[..., None] * np.float32([0.10, 0.10, 0.12])

def _rwi_dragonfly_spec(h, w, s):
    veins = _rk_web(h, w, s ^ 1, 7000, k=2)
    return (16 + veins * 195 + _rk_sc(h, w, s ^ 4, 600, 1.5, "dot") * 60,
            np.clip(200 - _rk_n(h, w, s ^ 5, (5, 13)) * 145, 15, 255),
            28 + _rk_n(h, w, s ^ 6, (20, 45)) * 155)


def _rwi_scarab_paint(h, w, s):
    dim = _rk_sc(h, w, s ^ 1, 16000, 1.1, "dot")
    gold = _rk_ramp(np.clip(_rk_n(h, w, s ^ 2, (4, 10)) * 0.8 + 0.15, 0, 1),
                    _rk_lut([(0.55, 0.38, 0.08), (0.95, 0.80, 0.30)], 0.5))
    glow = cv2.GaussianBlur(dim, (0, 0), 1.2)
    return np.clip(gold * (1 - dim[..., None] * 0.35) + glow[..., None] * np.float32([0.10, 0.30, 0.10]) * 0.4, 0, 1)

def _rwi_scarab_spec(h, w, s):
    dim = _rk_sc(h, w, s ^ 1, 16000, 1.1, "dot")
    return (24 + dim * 230,
            np.clip(175 - _rk_gr(h, w, s ^ 3, 2, 3.0) * 125, 15, 255),
            26 + _rk_n(h, w, s ^ 4, (50, 110)) * 120 + dim * 40)


def _rwi_luna_paint(h, w, s):
    fur = _rk_sc(h, w, s ^ 1, 9000, 0.9, "streak", len_px=3.5)
    pale = _rk_ramp(np.clip(fur * 0.55 + _rk_n(h, w, s ^ 2, (4, 10)) * 0.5, 0, 1),
                    _rk_lut([(0.55, 0.72, 0.55), (0.85, 0.95, 0.80)], 0.6))
    glint = _rk_sc(h, w, s ^ 3, 160, 2.8, "star5")
    return np.clip(pale + glint[..., None] * np.float32([0.9, 0.95, 0.7]) * 0.4, 0, 1)

def _rwi_luna_spec(h, w, s):
    fur = _rk_sc(h, w, s ^ 1, 9000, 0.9, "streak", len_px=3.5)
    return (14 + _rk_sc(h, w, s ^ 3, 160, 2.8, "star5") * 205 + fur * 20,
            np.clip(90 + fur * 125, 15, 255),
            24 + _rk_n(h, w, s ^ 4, (60, 130)) * 120)


def _rwi_stag_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 36))
    bronze = edge[..., None] * np.float32([0.55, 0.35, 0.15])
    return np.clip(np.float32([0.07, 0.06, 0.06])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 2, (4, 10))[..., None] * 0.6) + bronze * 0.8, 0, 1)

def _rwi_stag_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 36))
    return (12 + edge * 205,
            np.clip(210 - _rk_n(h, w, s ^ 3, (3, 8)) * 60 - _rk_gr(h, w, s ^ 5, 2, 3.2) * 40, 15, 255),
            22 + _rk_sc(h, w, s ^ 4, 700, 2.0, "dot") * 150)


def _rwi_wasp_paint(h, w, s):
    a = _rk_sc(h, w, s ^ 1, 8000, 1.0, "streak", len_px=4)
    b = _rk_sc(h, w, s ^ 2, 8000, 1.0, "streak", len_px=4)
    zone = cv2.GaussianBlur(a - b, (0, 0), 0.5)
    amber = np.float32([0.90, 0.60, 0.08])[None, None, :]
    blk = np.float32([0.08, 0.07, 0.06])[None, None, :]
    m = np.clip(zone * 14 + 0.5 + (_rk_n(h, w, s ^ 3, (3, 7)) - 0.5) * 0.4, 0, 1)[..., None]
    return amber * m + blk * (1 - m) + a[..., None] * 0.15

def _rwi_wasp_spec(h, w, s):
    a = _rk_sc(h, w, s ^ 1, 8000, 1.0, "streak", len_px=4)
    b = _rk_sc(h, w, s ^ 2, 8000, 1.0, "streak", len_px=4)
    return (20 + a * 200, np.clip(120 + b * 110, 15, 255), 26 + _rk_n(h, w, s ^ 4, (40, 90)) * 130)


def _rwi_firefly_paint(h, w, s):
    glow = _rk_sc(h, w, s ^ 1, 7000, 1.2, "dot")
    base = np.float32([0.05, 0.08, 0.06])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 2, (3, 7))[..., None] * 0.7)
    return np.clip(base + cv2.GaussianBlur(glow, (0, 0), 0.8)[..., None] * np.float32([0.55, 0.85, 0.25]) * 0.30, 0, 1)

def _rwi_firefly_spec(h, w, s):
    glow = _rk_sc(h, w, s ^ 1, 7000, 1.2, "dot")
    cores = _rk_sc(h, w, s ^ 3, 1400, 1.0, "dot")
    return (8 + cores * 215,
            np.clip(190 - _rk_n(h, w, s ^ 4, (4, 10)) * 120, 15, 255),
            24 + cv2.GaussianBlur(glow, (0, 0), 2) * 185 + glow * 40)


REWORK_MONOLITHICS = {}
for _fid, _p, _s in (
    ("beetle_jewel", _rwi_jewel_paint, _rwi_jewel_spec),
    ("beetle_rainbow", _rwi_rainbow_paint, _rwi_rainbow_spec),
    ("butterfly_morpho", _rwi_morpho_paint, _rwi_morpho_spec),
    ("butterfly_monarch", _rwi_monarch_paint, _rwi_monarch_spec),
    ("dragonfly_wing", _rwi_dragonfly_paint, _rwi_dragonfly_spec),
    ("scarab_gold", _rwi_scarab_paint, _rwi_scarab_spec),
    ("moth_luna", _rwi_luna_paint, _rwi_luna_spec),
    ("beetle_stag", _rwi_stag_paint, _rwi_stag_spec),
    ("wasp_warning", _rwi_wasp_paint, _rwi_wasp_spec),
    ("firefly_glow", _rwi_firefly_paint, _rwi_firefly_spec),
):
    REWORK_MONOLITHICS[_fid] = _rw_pair(_fid, _p, _s)
# === IRIDESCENT INSECTS rework END ===


# === ANIME INSPIRED rework via recipe_kit (2026-06-10) ===
from engine.recipe_kit import halftone

def _rwa_cel_paint(h, w, s):
    f = _rk_n(h, w, s ^ 1, (3, 8))
    cel = np.floor(np.clip(f, 0, 0.999) * 5) / 5.0
    flip = flip_lattice((h, w), s ^ 2, 1.2, 0.5)
    body = _rk_ramp(cel, _rk_lut([(0.12, 0.16, 0.38), (0.55, 0.70, 0.95)], 0.5))
    chrome = _rk_ramp(cel, _rk_lut([(0.70, 0.74, 0.80), (0.95, 0.97, 1.0)], 0.6))
    return body * (1 - flip[..., None]) + chrome * flip[..., None]

def _rwa_cel_spec(h, w, s):
    flip = flip_lattice((h, w), s ^ 2, 1.2, 0.5)
    f = _rk_n(h, w, s ^ 1, (3, 8))
    edge = np.abs(np.diff(np.floor(f * 5), axis=0, prepend=0)) + np.abs(np.diff(np.floor(f * 5), axis=1, prepend=0))
    return (20 + flip * 220, np.clip(60 + _rk_gr(h, w, s ^ 3, 3, 3.5) * 125, 15, 255),
            26 + np.clip(edge, 0, 1) * 150 + _rk_n(h, w, s ^ 4, (15, 35)) * 40)

def _rwa_speed_paint(h, w, s):
    a = _rk_sc(h, w, s ^ 1, 5000, 1.0, "streak", len_px=8)
    b = _rk_sc(h, w, s ^ 2, 3200, 1.0, "streak", len_px=7)
    base = _rk_ramp(_rk_n(h, w, s ^ 3, (6, 14)), _rk_lut([(0.06, 0.08, 0.18), (0.14, 0.18, 0.34)], 0.5))
    return np.clip(base + a[..., None] * 0.85 + b[..., None] * np.float32([0.4, 0.7, 0.95]) * 0.5, 0, 1)

def _rwa_speed_spec(h, w, s):
    a = _rk_sc(h, w, s ^ 1, 5000, 1.0, "streak", len_px=8)
    return (18 + a * 215, np.clip(190 - _rk_gr(h, w, s ^ 4, 2, 3.2) * 135, 15, 255),
            24 + cv2.GaussianBlur(_rk_sc(h, w, s ^ 2, 3200, 1.0, "streak", len_px=7), (0, 0), 1.5) * 175)

def _rwa_sparkle_paint(h, w, s):
    st = _rk_sc(h, w, s ^ 1, 6000, 1.4, "star5")
    dt = _rk_sc(h, w, s ^ 2, 4000, 0.9, "dot")
    base = _rk_ramp(_rk_n(h, w, s ^ 3, (5, 12)), _rk_lut([(0.16, 0.07, 0.26), (0.30, 0.14, 0.42)], 0.5))
    return np.clip(base + st[..., None] * np.float32([0.95, 0.75, 0.85]) * 0.7 + dt[..., None] * np.float32([0.95, 0.85, 0.45]) * 0.5, 0, 1)

def _rwa_sparkle_spec(h, w, s):
    st = _rk_sc(h, w, s ^ 1, 6000, 1.4, "star5")
    return (20 + st * 230, np.clip(175 - _rk_gr(h, w, s ^ 4, 3, 3.5) * 120, 15, 255),
            26 + cv2.GaussianBlur(st, (0, 0), 2) * 165)

def _rwa_hair_paint(h, w, s):
    strand = _rk_gr(h, w, s ^ 1, 2, 3.0)
    silk = _rk_ramp(np.clip(strand * 0.6 + _rk_n(h, w, s ^ 2, (4, 9)) * 0.45, 0, 1),
                    _rk_lut([(0.85, 0.45, 0.65), (0.62, 0.50, 0.85), (0.35, 0.65, 0.80)], 0.6))
    return silk

def _rwa_hair_spec(h, w, s):
    strand = _rk_gr(h, w, s ^ 1, 2, 3.0)
    return (16 + _rk_sc(h, w, s ^ 3, 2400, 0.9, "streak", len_px=6) * 200,
            np.clip(45 + strand * 135, 15, 255), 26 + _rk_n(h, w, s ^ 4, (20, 45)) * 140)

def _rwa_mecha_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 60))
    riv = _rk_sc(h, w, s ^ 2, 3000, 1.0, "dot")
    gun = _rk_cell(lab, s ^ 3, _rk_lut([(0.28, 0.30, 0.34), (0.38, 0.40, 0.46)], 0.5))
    return np.clip(gun * (1 - edge[..., None] * 0.8) + riv[..., None] * 0.4, 0, 1)

def _rwa_mecha_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 60))
    riv = _rk_sc(h, w, s ^ 2, 3000, 1.0, "dot")
    return (22 + riv * 200 + edge * 90, np.clip(200 - _rk_n(h, w, s ^ 4, (3, 8)) * 140, 15, 255),
            24 + cv2.GaussianBlur(edge, (0, 0), 1.5) * 165)

def _rwa_sakura_paint(h, w, s):
    pet = _rk_sc(h, w, s ^ 1, 7000, 1.5, "petal")
    base = _rk_ramp(_rk_n(h, w, s ^ 2, (5, 12)), _rk_lut([(0.93, 0.88, 0.86), (0.97, 0.80, 0.84)], 0.6))
    return np.clip(base * (1 - pet[..., None] * 0.3) + pet[..., None] * np.float32([0.95, 0.55, 0.68]) * 0.75, 0, 1)

def _rwa_sakura_spec(h, w, s):
    pet = _rk_sc(h, w, s ^ 1, 7000, 1.5, "petal")
    return (16 + _rk_sc(h, w, s ^ 3, 2600, 1.2, "petal") * 195,
            np.clip(185 - _rk_gr(h, w, s ^ 4, 3, 3.4) * 125, 15, 255),
            26 + cv2.GaussianBlur(pet, (0, 0), 2) * 160)

def _rwa_aura_paint(h, w, s):
    f1 = _rk_web(h, w, s ^ 1, 5200, k=2)
    f2 = _rk_web(h, w, s ^ 2, 2600, k=2)
    base = np.float32([0.05, 0.05, 0.12])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 3, (6, 14))[..., None] * 0.6)
    return np.clip(base + f1[..., None] * np.float32([0.15, 0.85, 0.95]) * 0.55 + f2[..., None] * np.float32([0.90, 0.25, 0.80]) * 0.5, 0, 1)

def _rwa_aura_spec(h, w, s):
    f1 = _rk_web(h, w, s ^ 1, 5200, k=2)
    return (18 + f1 * 205, np.clip(125 + _rk_gr(h, w, s ^ 4, 2, 3.5) * 110, 15, 255),
            24 + cv2.GaussianBlur(_rk_web(h, w, s ^ 2, 2600, k=2), (0, 0), 2) * 180)

def _rwa_halftone_paint(h, w, s):
    dots = halftone(h, w, s ^ 1, 4.5, 3) * np.clip(_rk_n(h, w, s ^ 2, (6, 14)) * 1.4, 0.2, 1)
    paper = np.float32([0.93, 0.91, 0.86])[None, None, :]
    ink = np.float32([0.10, 0.12, 0.24])[None, None, :]
    return paper * (1 - dots[..., None] * 0.9) + ink * dots[..., None] * 0.9

def _rwa_halftone_spec(h, w, s):
    dots = halftone(h, w, s ^ 1, 4.5, 3)
    return (16 + dots * 185, np.clip(205 - _rk_gr(h, w, s ^ 3, 2, 3.0) * 145, 15, 255),
            24 + _rk_n(h, w, s ^ 4, (18, 40)) * 130)

def _rwa_outline_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 80))
    rng = np.random.default_rng(s ^ 2)
    hot = (rng.random(int(lab.max()) + 1) > 0.5).astype(np.float32)[lab]
    pink = np.float32([1.0, 0.25, 0.65])[None, None, :]
    cyan = np.float32([0.20, 0.90, 0.95])[None, None, :]
    base = np.float32([0.05, 0.05, 0.08])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 3, (5, 12))[..., None] * 0.6)
    return np.clip(base + edge[..., None] * (pink * hot[..., None] + cyan * (1 - hot[..., None])) * 0.9, 0, 1)

def _rwa_outline_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 80))
    return (14 + edge * 215, np.clip(190 - _rk_n(h, w, s ^ 4, (3, 8)) * 130, 15, 255),
            24 + cv2.GaussianBlur(edge, (0, 0), 2) * 190)

def _rwa_crystal_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(800, (h * w) // 38))
    cells = _rk_cell(lab, s ^ 2, _rk_lut([(0.25, 0.75, 0.85), (0.45, 0.30, 0.80), (0.90, 0.45, 0.65)], 0.55))
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    return np.clip(cells * (0.55 + d1n[..., None] * 0.6) * (1 - edge[..., None] * 0.6), 0, 1)

def _rwa_crystal_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(800, (h * w) // 38))
    rng = np.random.default_rng(s ^ 3)
    glint = (rng.random(int(lab.max()) + 1) > 0.6).astype(np.float32)[lab]
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    return (20 + glint * (1 - edge) * 210, np.clip(70 + edge * 90 + _rk_n(h, w, s ^ 4, (3, 8)) * 70, 15, 255),
            28 + d1n * 150)


# === NEON UNDERGROUND rework via recipe_kit (2026-06-10) ===

def _rwn_pink_paint(h, w, s):
    web = _rk_web(h, w, s ^ 1, 7000, k=2)
    base = np.float32([0.09, 0.07, 0.10])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 2, (6, 14))[..., None] * 0.6)
    return np.clip(base + web[..., None] * np.float32([1.0, 0.20, 0.55]) * 0.8 + cv2.GaussianBlur(web, (0, 0), 1.4)[..., None] * np.float32([0.9, 0.2, 0.5]) * 0.15, 0, 1)

def _rwn_pink_spec(h, w, s):
    web = _rk_web(h, w, s ^ 1, 7000, k=2)
    return (18 + web * 215, np.clip(180 - _rk_gr(h, w, s ^ 3, 3, 3.4) * 125, 15, 255),
            24 + cv2.GaussianBlur(web, (0, 0), 1.8) * 190)

def _rwn_toxic_paint(h, w, s):
    rings = _rk_rings(h, w, s ^ 1, 5200, 1.8, 1.2)
    base = np.float32([0.06, 0.09, 0.06])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 2, (5, 12))[..., None] * 0.6)
    return np.clip(base + rings[..., None] * np.float32([0.45, 0.95, 0.15]) * 0.8, 0, 1)

def _rwn_toxic_spec(h, w, s):
    rings = _rk_rings(h, w, s ^ 1, 5200, 1.8, 1.2)
    return (20 + rings * 210, np.clip(185 - _rk_n(h, w, s ^ 3, (4, 9)) * 130, 15, 255),
            24 + cv2.GaussianBlur(rings, (0, 0), 1.4) * 180)

def _rwn_blue_paint(h, w, s):
    a = _rk_sc(h, w, s ^ 1, 8000, 0.9, "streak", len_px=5)
    base = _rk_ramp(_rk_n(h, w, s ^ 2, (6, 14)), _rk_lut([(0.04, 0.06, 0.16), (0.08, 0.12, 0.28)], 0.5))
    return np.clip(base + a[..., None] * np.float32([0.25, 0.60, 1.0]) * 0.85, 0, 1)

def _rwn_blue_spec(h, w, s):
    a = _rk_sc(h, w, s ^ 1, 8000, 0.9, "streak", len_px=5)
    return (18 + a * 220, np.clip(185 - _rk_gr(h, w, s ^ 3, 2, 3.2) * 130, 15, 255),
            24 + cv2.GaussianBlur(_rk_sc(h, w, s ^ 4, 4000, 0.9, "streak", len_px=5), (0, 0), 1.8) * 175)

def _rwn_blacklight_paint(h, w, s):
    glyph = _rk_sc(h, w, s ^ 1, 9000, 0.9, "star5")
    base = np.float32([0.10, 0.06, 0.18])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 2, (3, 7))[..., None] * 0.6)
    return np.clip(base + glyph[..., None] * np.float32([0.45, 0.25, 0.85]) * 0.10, 0, 1)

def _rwn_blacklight_spec(h, w, s):
    glyph = _rk_sc(h, w, s ^ 1, 9000, 0.9, "star5")
    return (12 + glyph * 230, np.clip(195 - _rk_n(h, w, s ^ 3, (4, 9)) * 135, 15, 255),
            22 + _rk_sc(h, w, s ^ 5, 3000, 1.2, "dot") * 170 + _rk_n(h, w, s ^ 6, (15, 35)) * 60)

def _rwn_hazard_paint(h, w, s):
    ticks = _rk_sc(h, w, s ^ 1, 9000, 1.5, "arc")
    zone = np.clip(cv2.GaussianBlur(_rk_sc(h, w, s ^ 2, 4000, 1.0, "streak", len_px=5) - _rk_sc(h, w, s ^ 3, 4000, 1.0, "streak", len_px=5), (0, 0), 0.4) * 16 + 0.5, 0, 1)
    amber = np.float32([1.0, 0.55, 0.05])[None, None, :]
    blk = np.float32([0.07, 0.06, 0.05])[None, None, :]
    return np.clip(amber * zone[..., None] + blk * (1 - zone[..., None]) + ticks[..., None] * 0.25, 0, 1)

def _rwn_hazard_spec(h, w, s):
    ticks = _rk_sc(h, w, s ^ 1, 9000, 1.5, "arc")
    return (20 + ticks * 205, np.clip(140 + _rk_sc(h, w, s ^ 3, 4000, 1.0, "streak", len_px=5) * 90, 15, 255),
            24 + _rk_n(h, w, s ^ 4, (15, 35)) * 140)

def _rwn_red_paint(h, w, s):
    rings = _rk_rings(h, w, s ^ 1, 7000, 1.8, 1.2)
    base = np.float32([0.12, 0.04, 0.05])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 2, (5, 12))[..., None] * 0.6)
    return np.clip(base + rings[..., None] * np.float32([1.0, 0.15, 0.12]) * 0.8, 0, 1)

def _rwn_red_spec(h, w, s):
    rings = _rk_rings(h, w, s ^ 1, 7000, 1.8, 1.2)
    return (20 + rings * 215, np.clip(175 - _rk_gr(h, w, s ^ 3, 2, 3.2) * 120, 15, 255),
            24 + cv2.GaussianBlur(rings, (0, 0), 1.2) * 185)

def _rwn_yellow_paint(h, w, s):
    web = _rk_web(h, w, s ^ 1, 4600, k=2)
    vias = _rk_sc(h, w, s ^ 2, 3500, 1.0, "dot")
    base = np.float32([0.13, 0.13, 0.14])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 3, (5, 12))[..., None] * 0.6)
    return np.clip(base + web[..., None] * np.float32([1.0, 0.85, 0.10]) * 0.7 + vias[..., None] * np.float32([1.0, 0.95, 0.4]) * 0.5, 0, 1)

def _rwn_yellow_spec(h, w, s):
    web = _rk_web(h, w, s ^ 1, 4600, k=2)
    vias = _rk_sc(h, w, s ^ 2, 3500, 1.0, "dot")
    return (18 + web * 195 + vias * 50, np.clip(190 - _rk_n(h, w, s ^ 4, (3, 8)) * 130, 15, 255),
            24 + cv2.GaussianBlur(vias, (0, 0), 1.4) * 185)

def _rwn_ice_paint(h, w, s):
    fil = _rk_sc(h, w, s ^ 1, 9000, 0.8, "streak", len_px=3)
    gl = _rk_sc(h, w, s ^ 2, 160, 2.6, "star5")
    base = _rk_ramp(_rk_n(h, w, s ^ 3, (5, 12)), _rk_lut([(0.82, 0.87, 0.93), (0.92, 0.96, 1.0)], 0.6))
    return np.clip(base * (0.8 + fil[..., None] * 0.25) + gl[..., None] * 0.35, 0, 1)

def _rwn_ice_spec(h, w, s):
    fil = _rk_sc(h, w, s ^ 1, 9000, 0.8, "streak", len_px=3)
    gl = _rk_sc(h, w, s ^ 2, 160, 2.6, "star5")
    return (16 + gl * 215 + fil * 35, np.clip(60 + _rk_gr(h, w, s ^ 5, 2, 3.2) * 125, 15, 255),
            26 + _rk_n(h, w, s ^ 4, (20, 45)) * 150)

def _rwn_dual_paint(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 1.2, 0.5)
    mag = np.float32([0.85, 0.10, 0.55])[None, None, :]
    cyn = np.float32([0.10, 0.80, 0.90])[None, None, :]
    grain = _rk_n(h, w, s ^ 2, (3, 6))[..., None]
    return np.clip((mag * (1 - flip[..., None]) + cyn * flip[..., None]) * (0.55 + grain * 0.5), 0, 1)

def _rwn_dual_spec(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 1.2, 0.5)
    return (16 + flip * 225, np.clip(75 + _rk_gr(h, w, s ^ 3, 2, 3.2) * 120, 15, 255),
            24 + _rk_n(h, w, s ^ 4, (18, 40)) * 150)

def _rwn_rainbow_paint(h, w, s):
    web = _rk_web(h, w, s ^ 1, 4600, k=2)
    hue = _rk_ramp(_rk_n(h, w, s ^ 2, (5, 11)),
                   _rk_lut([(1.0, 0.2, 0.2), (1.0, 0.8, 0.1), (0.2, 0.9, 0.4), (0.2, 0.5, 1.0), (0.7, 0.25, 0.9)], 0.55))
    base = np.float32([0.07, 0.07, 0.09])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 3, (5, 12))[..., None] * 0.6)
    return np.clip(base + hue * web[..., None] * 0.9, 0, 1)

def _rwn_rainbow_spec(h, w, s):
    web = _rk_web(h, w, s ^ 1, 4600, k=2)
    return (18 + web * 210, np.clip(185 - _rk_gr(h, w, s ^ 4, 3, 3.4) * 125, 15, 255),
            24 + cv2.GaussianBlur(web, (0, 0), 1.5) * 180)


REWORK_MONOLITHICS.update({fid: _rw_pair(fid, p, sp) for fid, p, sp in (
    ("anime_cel_shade_chrome", _rwa_cel_paint, _rwa_cel_spec),
    ("anime_speed_lines", _rwa_speed_paint, _rwa_speed_spec),
    ("anime_sparkle_burst", _rwa_sparkle_paint, _rwa_sparkle_spec),
    ("anime_gradient_hair", _rwa_hair_paint, _rwa_hair_spec),
    ("anime_mecha_plate", _rwa_mecha_paint, _rwa_mecha_spec),
    ("anime_sakura_scatter", _rwa_sakura_paint, _rwa_sakura_spec),
    ("anime_energy_aura", _rwa_aura_paint, _rwa_aura_spec),
    ("anime_comic_halftone", _rwa_halftone_paint, _rwa_halftone_spec),
    ("anime_neon_outline", _rwa_outline_paint, _rwa_outline_spec),
    ("anime_crystal_facet", _rwa_crystal_paint, _rwa_crystal_spec),
    ("neon_pink_blaze", _rwn_pink_paint, _rwn_pink_spec),
    ("neon_toxic_green", _rwn_toxic_paint, _rwn_toxic_spec),
    ("neon_electric_blue", _rwn_blue_paint, _rwn_blue_spec),
    ("neon_blacklight", _rwn_blacklight_paint, _rwn_blacklight_spec),
    ("neon_orange_hazard", _rwn_hazard_paint, _rwn_hazard_spec),
    ("neon_red_alert", _rwn_red_paint, _rwn_red_spec),
    ("neon_cyber_yellow", _rwn_yellow_paint, _rwn_yellow_spec),
    ("neon_ice_white", _rwn_ice_paint, _rwn_ice_spec),
    ("neon_dual_glow", _rwn_dual_paint, _rwn_dual_spec),
    ("neon_rainbow_tube", _rwn_rainbow_paint, _rwn_rainbow_spec),
)})
# === ANIME + NEON rework END ===


# === CHAMELEON rework via recipe_kit (2026-06-10) — the color-flip flagship ===
# Every finish: its OWN geometry + signature hue pair; flip personalities split
# across spec channels so the hue swap happens with sun angle.

def _cs_dual(h, w, s, hue_a, hue_b, mask01):
    a = np.float32(hue_a)[None, None, :]
    b = np.float32(hue_b)[None, None, :]
    return a * (1 - mask01[..., None]) + b * mask01[..., None]


def _rwc_amethyst_paint(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 0.9, 0.48)
    g = _rk_n(h, w, s ^ 2, (3, 6))[..., None]
    return np.clip(_cs_dual(h, w, s, (0.42, 0.16, 0.62), (0.10, 0.55, 0.60), flip) * (0.55 + g * 0.55), 0, 1)

def _rwc_amethyst_spec(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 0.9, 0.48)
    return (16 + flip * 225, np.clip(70 + _rk_gr(h, w, s ^ 3, 2, 3.4) * 125, 15, 255),
            24 + _rk_n(h, w, s ^ 4, (16, 36)) * 150)


def _rwc_arctic_paint(h, w, s):
    fil = _rk_sc(h, w, s ^ 1, 8000, 0.8, "streak", len_px=4)
    flip = flip_lattice((h, w), s ^ 2, 1.4, 0.5)
    base = _cs_dual(h, w, s, (0.55, 0.68, 0.85), (0.85, 0.82, 0.95), flip)
    return np.clip(base * (0.7 + fil[..., None] * 0.45), 0, 1)

def _rwc_arctic_spec(h, w, s):
    flip = flip_lattice((h, w), s ^ 2, 1.4, 0.5)
    fil = _rk_sc(h, w, s ^ 1, 8000, 0.8, "streak", len_px=4)
    return (16 + flip * 215 + fil * 25, np.clip(55 + _rk_n(h, w, s ^ 3, (4, 9)) * 120, 15, 255),
            26 + _rk_n(h, w, s ^ 4, (20, 45)) * 145)


def _rwc_aurora_paint(h, w, s):
    cur = _rk_gr(h, w, s ^ 1, 3, 4.2)
    lut = _rk_lut([(0.05, 0.60, 0.35), (0.20, 0.30, 0.70), (0.55, 0.15, 0.65)], 0.55)
    return _rk_ramp(np.clip(cur + (_rk_n(h, w, s ^ 2, (3, 7)) - 0.5) * 0.3, 0, 1), lut)

def _rwc_aurora_spec(h, w, s):
    cur = _rk_gr(h, w, s ^ 1, 3, 4.2)
    return (18 + _rk_sc(h, w, s ^ 3, 5200, 0.9, "streak", len_px=6) * 205,
            np.clip(190 - cur * 130, 15, 255), 24 + _rk_n(h, w, s ^ 4, (18, 40)) * 155)


def _rwc_copper_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 42))
    rng = np.random.default_rng(s ^ 2)
    m = (rng.random(int(lab.max()) + 1) > 0.5).astype(np.float32)[lab]
    g = _rk_n(h, w, s ^ 3, (4, 9))[..., None]
    return np.clip(_cs_dual(h, w, s, (0.62, 0.32, 0.12), (0.08, 0.48, 0.30), m) * (0.5 + g * 0.6) * (1 - edge[..., None] * 0.4), 0, 1)

def _rwc_copper_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 42))
    rng = np.random.default_rng(s ^ 2)
    m = (rng.random(int(lab.max()) + 1) > 0.5).astype(np.float32)[lab]
    return (18 + m * (1 - edge) * 215, np.clip(195 - _rk_gr(h, w, s ^ 4, 2, 3.2) * 135, 15, 255),
            24 + edge * 130 + _rk_n(h, w, s ^ 5, (25, 55)) * 50)


def _rwc_emerald_paint(h, w, s):
    wv = _rk_gr(h, w, s ^ 1, 4, 3.0)
    flip = flip_lattice((h, w), s ^ 2, 1.0, 0.45)
    return np.clip(_cs_dual(h, w, s, (0.04, 0.42, 0.22), (0.80, 0.66, 0.18), flip) * (0.55 + wv[..., None] * 0.55), 0, 1)

def _rwc_emerald_spec(h, w, s):
    flip = flip_lattice((h, w), s ^ 2, 1.0, 0.45)
    return (16 + flip * 225, np.clip(80 + _rk_gr(h, w, s ^ 3, 3, 3.6) * 115, 15, 255),
            26 + _rk_n(h, w, s ^ 4, (14, 32)) * 145)


def _rwc_fire_paint(h, w, s):
    tongues = _rk_sc(h, w, s ^ 1, 6000, 1.4, "petal")
    lut = _rk_lut([(0.55, 0.05, 0.05), (0.95, 0.45, 0.05), (1.0, 0.85, 0.30)], 0.5)
    return _rk_ramp(np.clip(tongues * 0.8 + _rk_n(h, w, s ^ 2, (3, 7)) * 0.35, 0, 1), lut)

def _rwc_fire_spec(h, w, s):
    tongues = _rk_sc(h, w, s ^ 1, 6000, 1.4, "petal")
    return (20 + tongues * 215, np.clip(185 - _rk_gr(h, w, s ^ 3, 2, 3.2) * 125, 15, 255),
            24 + cv2.GaussianBlur(tongues, (0, 0), 1.6) * 175)


def _rwc_frost_paint(h, w, s):
    fern = _rk_web(h, w, s ^ 1, 6000, k=2, intensity=(0.25, 0.7))
    g = _rk_n(h, w, s ^ 2, (3, 6))[..., None]
    base = np.float32([0.72, 0.78, 0.88])[None, None, :]
    return np.clip(base * (0.6 + g * 0.45) + fern[..., None] * np.float32([0.85, 0.92, 1.0]) * 0.35, 0, 1)

def _rwc_frost_spec(h, w, s):
    fern = _rk_web(h, w, s ^ 1, 6000, k=2)
    return (14 + fern * 210, np.clip(60 + _rk_n(h, w, s ^ 3, (3, 8)) * 110, 15, 255),
            26 + _rk_n(h, w, s ^ 4, (22, 48)) * 150)


def _rwc_galaxy_paint(h, w, s):
    stars = _rk_sc(h, w, s ^ 1, 5200, 1.0, "dot")
    flip = flip_lattice((h, w), s ^ 2, 1.3, 0.5)
    base = _cs_dual(h, w, s, (0.16, 0.06, 0.32), (0.05, 0.25, 0.45), flip)
    g = _rk_n(h, w, s ^ 3, (5, 11))[..., None]
    return np.clip(base * (0.6 + g * 0.5) + stars[..., None] * 0.8, 0, 1)

def _rwc_galaxy_spec(h, w, s):
    stars = _rk_sc(h, w, s ^ 1, 5200, 1.0, "dot")
    flip = flip_lattice((h, w), s ^ 2, 1.3, 0.5)
    return (14 + stars * 160 + flip * 95, np.clip(185 - _rk_gr(h, w, s ^ 4, 2, 3.4) * 125, 15, 255),
            24 + _rk_n(h, w, s ^ 5, (20, 44)) * 150)


def _rwc_midnight_paint(h, w, s):
    g = _rk_n(h, w, s ^ 1, (3, 7))[..., None]
    glint = _rk_sc(h, w, s ^ 2, 4200, 0.9, "dot")
    return np.clip(np.float32([0.03, 0.04, 0.10])[None, None, :] * (0.7 + g * 0.6) + glint[..., None] * np.float32([0.15, 0.25, 0.60]) * 0.5, 0, 1)

def _rwc_midnight_spec(h, w, s):
    glint = _rk_sc(h, w, s ^ 2, 4200, 0.9, "dot")
    return (10 + glint * 230, np.clip(190 - _rk_n(h, w, s ^ 3, (4, 9)) * 120, 15, 255),
            22 + _rk_n(h, w, s ^ 4, (18, 40)) * 160)


def _rwc_neon_paint(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 1.0, 0.5)
    g = _rk_n(h, w, s ^ 2, (3, 7))[..., None]
    return np.clip(_cs_dual(h, w, s, (0.80, 0.08, 0.55), (0.25, 0.85, 0.15), flip) * (0.5 + g * 0.6), 0, 1)

def _rwc_neon_spec(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 1.0, 0.5)
    return (16 + flip * 230, np.clip(85 + _rk_gr(h, w, s ^ 3, 2, 3.0) * 120, 15, 255),
            24 + _rk_n(h, w, s ^ 4, (15, 34)) * 155)


def _rwc_obsidian_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 44))
    g = _rk_n(h, w, s ^ 2, (3, 6))[..., None]
    return np.clip(np.float32([0.05, 0.045, 0.05])[None, None, :] * (0.7 + g * 0.5) + edge[..., None] * np.float32([0.65, 0.45, 0.20]) * 0.55, 0, 1)

def _rwc_obsidian_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 44))
    return (12 + edge * 215, np.clip(200 - _rk_n(h, w, s ^ 3, (3, 8)) * 70, 15, 255),
            22 + _rk_sc(h, w, s ^ 4, 900, 1.8, "dot") * 160)


def _rwc_ocean_paint(h, w, s):
    swell = _rk_gr(h, w, s ^ 1, 3, 3.6)
    lut = _rk_lut([(0.03, 0.30, 0.40), (0.05, 0.12, 0.45)], 0.55)
    spray = _rk_sc(h, w, s ^ 2, 3600, 0.9, "dot")
    return np.clip(_rk_ramp(swell, lut) + spray[..., None] * np.float32([0.6, 0.85, 0.9]) * 0.3, 0, 1)

def _rwc_ocean_spec(h, w, s):
    swell = _rk_gr(h, w, s ^ 1, 3, 3.6)
    return (16 + _rk_sc(h, w, s ^ 2, 3600, 0.9, "dot") * 200, np.clip(70 + swell * 125, 15, 255),
            26 + _rk_n(h, w, s ^ 4, (20, 44)) * 150)


def _rwc_phoenix_paint(h, w, s):
    feathers = _rk_sc(h, w, s ^ 1, 5600, 1.5, "petal")
    flip = flip_lattice((h, w), s ^ 2, 1.2, 0.5)
    base = _cs_dual(h, w, s, (0.80, 0.30, 0.05), (0.75, 0.10, 0.45), flip)
    return np.clip(base * (0.5 + feathers[..., None] * 0.6), 0, 1)

def _rwc_phoenix_spec(h, w, s):
    feathers = _rk_sc(h, w, s ^ 1, 5600, 1.5, "petal")
    flip = flip_lattice((h, w), s ^ 2, 1.2, 0.5)
    return (16 + flip * 140 + feathers * 90, np.clip(180 - _rk_gr(h, w, s ^ 3, 3, 3.4) * 120, 15, 255),
            24 + cv2.GaussianBlur(feathers, (0, 0), 1.6) * 165)


def _rwc_venom_paint(h, w, s):
    scales = _rk_vor(h, w, s ^ 1, max(1100, (h * w) // 34))
    lab, d1, edge = scales
    rng = np.random.default_rng(s ^ 2)
    m = (rng.random(int(lab.max()) + 1) > 0.5).astype(np.float32)[lab]
    return np.clip(_cs_dual(h, w, s, (0.18, 0.55, 0.08), (0.38, 0.10, 0.55), m) * (1 - edge[..., None] * 0.65) * (0.6 + _rk_n(h, w, s ^ 3, (4, 9))[..., None] * 0.5), 0, 1)

def _rwc_venom_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1100, (h * w) // 34))
    return (18 + (1 - edge) * 150 + _rk_sc(h, w, s ^ 4, 2600, 0.9, "dot") * 70,
            np.clip(190 - _rk_n(h, w, s ^ 5, (3, 8)) * 130 + edge * 35, 15, 255),
            24 + _rk_n(h, w, s ^ 6, (18, 40)) * 150)


def _rwc_mystichrome_paint(h, w, s):
    m0, m1, m2 = tri_partition((h, w), s ^ 1, cells=max(2600, (h * w) // 16), soften_px=1.0)
    g = _rk_n(h, w, s ^ 2, (3, 7))[..., None]
    cob = np.float32([0.10, 0.20, 0.55])[None, None, :]
    vio = np.float32([0.38, 0.12, 0.55])[None, None, :]
    eme = np.float32([0.05, 0.45, 0.30])[None, None, :]
    return np.clip((cob * m0[..., None] + vio * m1[..., None] + eme * m2[..., None]) * (0.55 + g * 0.55), 0, 1)

def _rwc_mystichrome_spec(h, w, s):
    m0, m1, m2 = tri_partition((h, w), s ^ 1, cells=max(2600, (h * w) // 16), soften_px=1.0)
    return (16 + m1 * 220, np.clip(60 + m2 * 140 + _rk_n(h, w, s ^ 3, (3, 8)) * 40, 15, 255),
            24 + m0 * 150 + _rk_n(h, w, s ^ 4, (20, 44)) * 40)


REWORK_MONOLITHICS.update({fid: _rw_pair(fid, p, sp) for fid, p, sp in (
    ("chameleon_amethyst", _rwc_amethyst_paint, _rwc_amethyst_spec),
    ("chameleon_arctic", _rwc_arctic_paint, _rwc_arctic_spec),
    ("chameleon_aurora", _rwc_aurora_paint, _rwc_aurora_spec),
    ("chameleon_copper", _rwc_copper_paint, _rwc_copper_spec),
    ("chameleon_emerald", _rwc_emerald_paint, _rwc_emerald_spec),
    ("chameleon_fire", _rwc_fire_paint, _rwc_fire_spec),
    ("chameleon_frost", _rwc_frost_paint, _rwc_frost_spec),
    ("chameleon_galaxy", _rwc_galaxy_paint, _rwc_galaxy_spec),
    ("chameleon_midnight", _rwc_midnight_paint, _rwc_midnight_spec),
    ("chameleon_neon", _rwc_neon_paint, _rwc_neon_spec),
    ("chameleon_obsidian", _rwc_obsidian_paint, _rwc_obsidian_spec),
    ("chameleon_ocean", _rwc_ocean_paint, _rwc_ocean_spec),
    ("chameleon_phoenix", _rwc_phoenix_paint, _rwc_phoenix_spec),
    ("chameleon_venom", _rwc_venom_paint, _rwc_venom_spec),
    ("mystichrome", _rwc_mystichrome_paint, _rwc_mystichrome_spec),
)})

# ───────────────── 2026-06-21 COLOR SCIENCE REDIRECT — CHAMELEON ─────────────────
# Every chameleon finish gets a UNIQUE elaborate spec via color_science_2026 (candy-depth
# + a distinct high-math look + motion) — NO shared spec. Paint (the flip hue pairs) kept.
def _ch_cs_spec_build(recipe, seed_off):
    _rc = dict(recipe); _so = int(seed_off)

    def spec_build(h, w, s):
        from engine.paint_v2 import color_science_2026 as _csx
        spec = _csx.compose_cs_spec((int(h), int(w)), int(s) + _so, 1.0, _rc)
        return (spec[:, :, 0].astype(np.float32),
                spec[:, :, 1].astype(np.float32),
                spec[:, :, 2].astype(np.float32))
    return spec_build


_CH_CANDY = {
    "std": {}, "warm": dict(m_hi=242, r_core=22, cc_core=16, cc_edge=184, r_edge=118),
    "dark": dict(m_lo=66, m_hi=214, cc_edge=178), "icy": dict(m_hi=232, r_edge=94, cc_edge=150, gamma=1.55),
    "deep": dict(m_hi=238, cc_edge=192, r_core=20, gamma=1.5),
}
# fid -> (paint_build, look, look_kwargs, depth_from, candy_key, motion)
_CH_SPECS = (
    ("chameleon_amethyst", _rwc_amethyst_paint, "iridescent_flow", dict(scale=4.0), "structure", "deep", 0.40),
    ("chameleon_arctic",   _rwc_arctic_paint,   "oilslick_thinfilm", dict(bands=7.0), "structure", "icy", 0.35),
    ("chameleon_aurora",   _rwc_aurora_paint,   "iridescent_flow", dict(scale=5.0), "invert", "std", 0.45),
    ("chameleon_copper",   _rwc_copper_paint,   "oilslick_thinfilm", dict(bands=5.0), "structure", "warm", 0.35),
    ("chameleon_emerald",  _rwc_emerald_paint,  "iridescent_flow", dict(scale=4.0), "structure", "std", 0.40),
    ("chameleon_fire",     _rwc_fire_paint,     "spectral_spiral", dict(arms=10.0, twist=4.0), "structure", "warm", 0.44),
    ("chameleon_frost",    _rwc_frost_paint,    "crystal_facets", dict(cells=44.0), "structure", "icy", 0.30),
    ("chameleon_galaxy",   _rwc_galaxy_paint,   "spectral_spiral", dict(arms=4.0, twist=9.0), "invert", "dark", 0.42),
    ("chameleon_midnight", _rwc_midnight_paint, "iridescent_flow", dict(scale=3.0), "structure", "dark", 0.32),
    ("chameleon_neon",     _rwc_neon_paint,     "guilloche", dict(a=12.0, b=14.0), "structure", "std", 0.38),
    ("chameleon_obsidian", _rwc_obsidian_paint, "crystal_facets", dict(cells=36.0), "invert", "dark", 0.28),
    ("chameleon_ocean",    _rwc_ocean_paint,    "ripple_caustics", dict(rings=10.0), "structure", "std", 0.33),
    ("chameleon_phoenix",  _rwc_phoenix_paint,  "spectral_spiral", dict(arms=9.0, twist=5.0), "invert", "warm", 0.48),
    ("chameleon_venom",    _rwc_venom_paint,    "crystal_facets", dict(cells=52.0), "structure", "std", 0.32),
    ("mystichrome",        _rwc_mystichrome_paint, "spectral_spiral", dict(arms=6.0, twist=7.0), "structure", "deep", 0.42),
)
def _apply_chameleon_color_science():
    # Called AFTER the _f4 _SPEC_RECIPES install (which also overrides chameleon) so this
    # is the FINAL chameleon spec. Swaps only the spec; keeps the current paint.
    for _i, (_fid, _pb, _lk, _kw, _df, _ck, _mo) in enumerate(_CH_SPECS):
        if _fid not in REWORK_MONOLITHICS:
            continue
        _rec = {"look": _lk, "look_kwargs": dict(_kw), "depth_from": _df,
                "candy": dict(_CH_CANDY.get(_ck, {})), "motion": float(_mo),
                "phase": (_i % 7) * 0.5, "relief": 26.0}
        _spec_fn = _rw_pair(_fid, _pb, _ch_cs_spec_build(_rec, 5300 + _i * 41))[0]
        REWORK_MONOLITHICS[_fid] = (_spec_fn, REWORK_MONOLITHICS[_fid][1])
# === CHAMELEON rework END ===


# === PRIZM rework via recipe_kit (2026-06-10) — prismatic/holographic family ===

def _rwp_iri(h, w, s, scales, orders, q, base):
    th = np.clip(_rk_n(h, w, s, scales), 0, 1)
    return interference_palette(th, orders, q, base_srgb=np.float32(base))


def _rwp_adaptive_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1000, (h * w) // 38))
    rng = np.random.default_rng(s ^ 2)
    t = rng.random(int(lab.max()) + 1).astype(np.float32)[lab]
    lut = _rk_lut([(0.70, 0.20, 0.45), (0.15, 0.55, 0.70), (0.75, 0.60, 0.15)], 0.55)
    return np.clip(_rk_ramp(t, lut) * (1 - edge[..., None] * 0.5) * (0.6 + _rk_n(h, w, s ^ 3, (3, 7))[..., None] * 0.5), 0, 1)

def _rwp_adaptive_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1000, (h * w) // 38))
    rng = np.random.default_rng(s ^ 4)
    m = (rng.random(int(lab.max()) + 1) > 0.5).astype(np.float32)[lab]
    return (16 + m * (1 - edge) * 215, np.clip(190 - _rk_gr(h, w, s ^ 5, 2, 3.2) * 130, 15, 255),
            24 + _rk_n(h, w, s ^ 6, (16, 36)) * 150)


def _rwp_alien_paint(h, w, s):
    cells = _rk_rings(h, w, s ^ 1, 6000, 1.8, 1.2)
    film = _rwp_iri(h, w, s ^ 2, (5, 11), 2.0, 0.55, (0.25, 0.35, 0.25))
    return np.clip(film * (0.65 + cells[..., None] * 0.5), 0, 1)

def _rwp_alien_spec(h, w, s):
    cells = _rk_rings(h, w, s ^ 1, 6000, 1.8, 1.2)
    return (18 + cells * 205, np.clip(120 + _rk_gr(h, w, s ^ 3, 3, 3.4) * 100, 15, 255),
            26 + _rk_n(h, w, s ^ 4, (18, 40)) * 145)


def _rwp_arctic_paint(h, w, s):
    shards = _rk_sc(h, w, s ^ 1, 7000, 1.0, "streak", len_px=4)
    film = _rwp_iri(h, w, s ^ 2, (6, 13), 1.8, 0.5, (0.70, 0.78, 0.88))
    return np.clip(film * (0.75 + shards[..., None] * 0.35), 0, 1)

def _rwp_arctic_spec(h, w, s):
    shards = _rk_sc(h, w, s ^ 1, 7000, 1.0, "streak", len_px=4)
    return (16 + shards * 210, np.clip(55 + _rk_n(h, w, s ^ 3, (4, 9)) * 115, 15, 255),
            26 + _rk_n(h, w, s ^ 4, (22, 46)) * 150)


def _rwp_aurorashift_paint(h, w, s):
    cur = _rk_gr(h, w, s ^ 1, 4, 3.8)
    lut = _rk_lut([(0.10, 0.60, 0.40), (0.30, 0.20, 0.70), (0.05, 0.40, 0.65)], 0.6)
    return _rk_ramp(np.clip(cur + (_rk_n(h, w, s ^ 2, (3, 6)) - 0.5) * 0.25, 0, 1), lut)

def _rwp_aurorashift_spec(h, w, s):
    cur = _rk_gr(h, w, s ^ 1, 4, 3.8)
    return (16 + _rk_sc(h, w, s ^ 3, 4600, 0.9, "streak", len_px=5) * 205,
            np.clip(60 + cur * 135, 15, 255), 24 + _rk_n(h, w, s ^ 4, (20, 42)) * 155)


def _rwp_blackrainbow_paint(h, w, s):
    threads = _rk_web(h, w, s ^ 1, 5600, k=2, intensity=(0.2, 0.55))
    hue = _rk_ramp(_rk_n(h, w, s ^ 2, (4, 9)),
                   _rk_lut([(0.8, 0.1, 0.2), (0.8, 0.6, 0.1), (0.1, 0.7, 0.4), (0.2, 0.3, 0.9)], 0.5))
    base = np.float32([0.04, 0.04, 0.05])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 3, (4, 9))[..., None] * 0.5)
    return np.clip(base + hue * threads[..., None] * 0.85, 0, 1)

def _rwp_blackrainbow_spec(h, w, s):
    threads = _rk_web(h, w, s ^ 1, 6000, k=2)
    return (12 + threads * 225, np.clip(195 - _rk_n(h, w, s ^ 3, (3, 8)) * 80, 15, 255),
            22 + cv2.GaussianBlur(threads, (0, 0), 1.6) * 175)


def _rwp_bloodmoon_paint(h, w, s):
    halo = _rk_rings(h, w, s ^ 1, 6000, 1.8, 1.2)
    g = _rk_n(h, w, s ^ 2, (3, 6))[..., None]
    return np.clip(np.float32([0.22, 0.04, 0.05])[None, None, :] * (0.6 + g * 0.6) + halo[..., None] * np.float32([0.85, 0.25, 0.10]) * 0.55, 0, 1)

def _rwp_bloodmoon_spec(h, w, s):
    halo = _rk_rings(h, w, s ^ 1, 6000, 1.8, 1.2)
    return (16 + halo * 210, np.clip(180 - _rk_gr(h, w, s ^ 3, 2, 3.4) * 120, 15, 255),
            24 + cv2.GaussianBlur(halo, (0, 0), 1.2) * 170)


def _rwp_candy_paint(h, w, s):
    fl = _rk_sc(h, w, s ^ 1, 16000, 1.1, "dot")
    metal = np.dstack([0.45 + fl * 0.5] * 3)
    depth = 0.7 + _rk_n(h, w, s ^ 2, (4, 9)) * 0.9
    return candy_absorb(metal, np.float32([0.80, 0.06, 0.12]), depth)

def _rwp_candy_spec(h, w, s):
    fl = _rk_sc(h, w, s ^ 1, 16000, 1.1, "dot")
    return (24 + fl * 225, np.clip(170 - _rk_gr(h, w, s ^ 3, 2, 3.2) * 120, 15, 255),
            30 + _rk_n(h, w, s ^ 4, (14, 30)) * 160)


def _rwp_chromerose_paint(h, w, s):
    pet = _rk_sc(h, w, s ^ 1, 8000, 1.1, "petal")
    g = _rk_n(h, w, s ^ 2, (3, 6))[..., None]
    chrome = np.float32([0.72, 0.74, 0.78])[None, None, :] * (0.6 + g * 0.5)
    return np.clip(chrome + pet[..., None] * np.float32([0.85, 0.35, 0.50]) * 0.45, 0, 1)

def _rwp_chromerose_spec(h, w, s):
    pet = _rk_sc(h, w, s ^ 1, 8000, 1.1, "petal")
    return (60 + pet * 180, np.clip(50 + _rk_gr(h, w, s ^ 3, 3, 3.4) * 110, 15, 255),
            26 + cv2.GaussianBlur(pet, (0, 0), 1.2) * 160)


def _rwp_copperflame_paint(h, w, s):
    fl = _rk_sc(h, w, s ^ 1, 5600, 1.5, "petal")
    lut = _rk_lut([(0.45, 0.20, 0.08), (0.85, 0.45, 0.10), (0.95, 0.75, 0.30)], 0.5)
    return _rk_ramp(np.clip(fl * 0.85 + _rk_n(h, w, s ^ 2, (3, 7)) * 0.3, 0, 1), lut)

def _rwp_copperflame_spec(h, w, s):
    fl = _rk_sc(h, w, s ^ 1, 5600, 1.5, "petal")
    return (22 + fl * 210, np.clip(175 - _rk_n(h, w, s ^ 3, (4, 9)) * 120, 15, 255),
            24 + cv2.GaussianBlur(fl, (0, 0), 1.5) * 165)


def _rwp_cosmos_paint(h, w, s):
    stars = _rk_sc(h, w, s ^ 1, 8000, 0.9, "dot")
    neb = candy_absorb(np.full((h, w, 3), 0.55, np.float32), np.float32([0.30, 0.12, 0.55]), 0.6 + _rk_n(h, w, s ^ 2, (5, 10)) * 1.2)
    return np.clip(neb + stars[..., None] * 0.85, 0, 1)

def _rwp_cosmos_spec(h, w, s):
    stars = _rk_sc(h, w, s ^ 1, 8000, 0.9, "dot")
    return (14 + stars * 230, np.clip(190 - _rk_gr(h, w, s ^ 3, 2, 3.4) * 125, 15, 255),
            24 + _rk_n(h, w, s ^ 4, (18, 40)) * 150)


def _rwp_darkmatter_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1200, (h * w) // 32))
    g = _rk_n(h, w, s ^ 2, (3, 7))[..., None]
    return np.clip(np.float32([0.05, 0.04, 0.08])[None, None, :] * (0.7 + g * 0.5) + edge[..., None] * np.float32([0.35, 0.15, 0.60]) * 0.5, 0, 1)

def _rwp_darkmatter_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1200, (h * w) // 32))
    return (12 + edge * 210, np.clip(200 - _rk_n(h, w, s ^ 3, (3, 8)) * 75, 15, 255),
            22 + _rk_sc(h, w, s ^ 4, 1100, 1.6, "dot") * 165)


def _rwp_deepspace_paint(h, w, s):
    dust = _rk_sc(h, w, s ^ 1, 9000, 0.8, "dot")
    g = _rk_n(h, w, s ^ 2, (5, 11))[..., None]
    return np.clip(np.float32([0.04, 0.05, 0.10])[None, None, :] * (0.6 + g * 0.6) + dust[..., None] * np.float32([0.55, 0.65, 0.95]) * 0.45, 0, 1)

def _rwp_deepspace_spec(h, w, s):
    dust = _rk_sc(h, w, s ^ 1, 9000, 0.8, "dot")
    return (12 + dust * 215, np.clip(185 - _rk_gr(h, w, s ^ 3, 2, 3.2) * 120, 15, 255),
            22 + _rk_n(h, w, s ^ 4, (20, 44)) * 155)


def _rwp_duochrome_paint(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 1.0, 0.5)
    g = _rk_n(h, w, s ^ 2, (3, 7))[..., None]
    return np.clip(_cs_dual(h, w, s, (0.15, 0.45, 0.60), (0.70, 0.25, 0.55), flip) * (0.55 + g * 0.55), 0, 1)

def _rwp_duochrome_spec(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 1.0, 0.5)
    return (16 + flip * 228, np.clip(70 + _rk_gr(h, w, s ^ 3, 2, 3.2) * 120, 15, 255),
            24 + _rk_n(h, w, s ^ 4, (16, 36)) * 150)


def _rwp_ember_paint(h, w, s):
    sparks = _rk_sc(h, w, s ^ 1, 7000, 1.0, "dot")
    g = _rk_n(h, w, s ^ 2, (3, 6))[..., None]
    return np.clip(np.float32([0.14, 0.05, 0.03])[None, None, :] * (0.6 + g * 0.6) + sparks[..., None] * np.float32([1.0, 0.45, 0.10]) * 0.7, 0, 1)

def _rwp_ember_spec(h, w, s):
    sparks = _rk_sc(h, w, s ^ 1, 7000, 1.0, "dot")
    return (18 + sparks * 220, np.clip(185 - _rk_n(h, w, s ^ 3, (4, 9)) * 125, 15, 255),
            24 + cv2.GaussianBlur(sparks, (0, 0), 1.4) * 175)


def _rwp_fireice_paint(h, w, s):
    m0, m1, m2 = tri_partition((h, w), s ^ 1, cells=max(2400, (h * w) // 18), soften_px=0.8)
    hot = _rk_ramp(_rk_n(h, w, s ^ 2, (4, 9)), _rk_lut([(0.75, 0.15, 0.05), (1.0, 0.65, 0.15)], 0.5))
    cold = _rk_ramp(_rk_n(h, w, s ^ 3, (4, 9)), _rk_lut([(0.15, 0.40, 0.75), (0.70, 0.85, 0.95)], 0.5))
    mid = np.float32([0.20, 0.18, 0.22])[None, None, :]
    return np.clip(hot * m0[..., None] + cold * m1[..., None] + mid * m2[..., None], 0, 1)

def _rwp_fireice_spec(h, w, s):
    m0, m1, m2 = tri_partition((h, w), s ^ 1, cells=max(2400, (h * w) // 18), soften_px=0.8)
    return (16 + m0 * 200, np.clip(60 + m1 * 150 + _rk_n(h, w, s ^ 4, (3, 8)) * 40, 15, 255),
            24 + m2 * 140 + _rk_n(h, w, s ^ 5, (18, 40)) * 40)


def _rwp_galaxydust_paint(h, w, s):
    dust = _rk_sc(h, w, s ^ 1, 12000, 0.8, "dot")
    film = _rwp_iri(h, w, s ^ 2, (7, 15), 1.6, 0.45, (0.10, 0.07, 0.18))
    return np.clip(film + dust[..., None] * 0.65, 0, 1)

def _rwp_galaxydust_spec(h, w, s):
    dust = _rk_sc(h, w, s ^ 1, 12000, 0.8, "dot")
    return (14 + dust * 225, np.clip(180 - _rk_gr(h, w, s ^ 3, 2, 3.4) * 120, 15, 255),
            24 + _rk_n(h, w, s ^ 4, (16, 36)) * 150)


def _rwp_holo_paint(h, w, s):
    patches = _rk_gr(h, w, s ^ 1, 5, 2.6)
    hue = _rk_ramp(patches, _rk_lut([(0.9, 0.2, 0.3), (0.9, 0.8, 0.2), (0.2, 0.8, 0.5), (0.25, 0.4, 0.95), (0.7, 0.3, 0.9)], 0.6))
    sil = np.float32([0.65, 0.66, 0.70])[None, None, :]
    return np.clip(sil * 0.45 + hue * 0.65, 0, 1)

def _rwp_holo_spec(h, w, s):
    patches = _rk_gr(h, w, s ^ 1, 5, 2.6)
    return (90 + patches * 150, np.clip(40 + _rk_n(h, w, s ^ 3, (3, 8)) * 90, 15, 255),
            26 + _rk_n(h, w, s ^ 4, (14, 32)) * 150)


def _rwp_iridescent_paint(h, w, s):
    return _rwp_iri(h, w, s ^ 1, (3, 8), 2.4, 0.6, (0.45, 0.42, 0.48))

def _rwp_iridescent_spec(h, w, s):
    th = _rk_n(h, w, s ^ 1, (3, 8))
    return (20 + np.clip(np.abs(np.diff(np.floor(th * 5), axis=0, prepend=0)) + np.abs(np.diff(np.floor(th * 5), axis=1, prepend=0)), 0, 1) * 200,
            np.clip(80 + _rk_gr(h, w, s ^ 2, 3, 3.2) * 110, 15, 255),
            26 + _rk_n(h, w, s ^ 3, (20, 44)) * 145)


def _rwp_midnight_paint(h, w, s):
    rain = _rk_sc(h, w, s ^ 1, 5200, 0.9, "streak", len_px=7)
    g = _rk_n(h, w, s ^ 2, (3, 6))[..., None]
    return np.clip(np.float32([0.04, 0.05, 0.09])[None, None, :] * (0.7 + g * 0.5) + rain[..., None] * np.float32([0.30, 0.45, 0.80]) * 0.5, 0, 1)

def _rwp_midnight_spec(h, w, s):
    rain = _rk_sc(h, w, s ^ 1, 5200, 0.9, "streak", len_px=7)
    return (12 + rain * 215, np.clip(190 - _rk_n(h, w, s ^ 3, (4, 9)) * 110, 15, 255),
            22 + cv2.GaussianBlur(rain, (0, 0), 1.6) * 165)


def _rwp_mystichrome_paint(h, w, s):
    flow = _rk_gr(h, w, s ^ 1, 2, 3.4)
    lut = _rk_lut([(0.12, 0.22, 0.50), (0.30, 0.15, 0.50), (0.08, 0.40, 0.35)], 0.65)
    glass = _rk_ramp(np.clip(flow + (_rk_n(h, w, s ^ 2, (3, 6)) - 0.5) * 0.2, 0, 1), lut)
    return np.clip(glass * (0.75 + _rk_sc(h, w, s ^ 3, 4200, 0.8, "dot")[..., None] * 0.4), 0, 1)

def _rwp_mystichrome_spec(h, w, s):
    flow = _rk_gr(h, w, s ^ 1, 2, 3.4)
    return (30 + _rk_sc(h, w, s ^ 3, 4200, 0.8, "dot") * 200, np.clip(45 + flow * 120, 15, 255),
            28 + _rk_n(h, w, s ^ 4, (16, 36)) * 155)


def _rwp_neon_paint(h, w, s):
    web = _rk_web(h, w, s ^ 1, 5200, k=2)
    g = _rk_n(h, w, s ^ 2, (3, 6))[..., None]
    return np.clip(np.float32([0.06, 0.05, 0.09])[None, None, :] * (0.7 + g * 0.5) + web[..., None] * np.float32([0.55, 1.0, 0.20]) * 0.7, 0, 1)

def _rwp_neon_spec(h, w, s):
    web = _rk_web(h, w, s ^ 1, 5200, k=2)
    return (16 + web * 215, np.clip(185 - _rk_gr(h, w, s ^ 3, 2, 3.2) * 120, 15, 255),
            24 + cv2.GaussianBlur(web, (0, 0), 1.8) * 180)


def _rwp_oceanic_paint(h, w, s):
    caust = _rk_web(h, w, s ^ 1, 5200, k=2, intensity=(0.25, 0.6))
    lut = _rk_lut([(0.02, 0.25, 0.38), (0.05, 0.45, 0.55)], 0.55)
    return np.clip(_rk_ramp(_rk_n(h, w, s ^ 2, (5, 11)), lut) + caust[..., None] * np.float32([0.4, 0.85, 0.85]) * 0.4, 0, 1)

def _rwp_oceanic_spec(h, w, s):
    caust = _rk_web(h, w, s ^ 1, 5200, k=2)
    return (16 + caust * 205, np.clip(60 + _rk_n(h, w, s ^ 3, (4, 9)) * 120, 15, 255),
            26 + _rk_n(h, w, s ^ 4, (20, 42)) * 155)


def _rwp_phoenix_paint(h, w, s):
    plumes = _rk_sc(h, w, s ^ 1, 6400, 1.3, "petal")
    lut = _rk_lut([(0.70, 0.15, 0.05), (0.95, 0.55, 0.10), (0.85, 0.20, 0.45)], 0.5)
    return _rk_ramp(np.clip(plumes * 0.9 + _rk_n(h, w, s ^ 2, (3, 7)) * 0.25, 0, 1), lut)

def _rwp_phoenix_spec(h, w, s):
    plumes = _rk_sc(h, w, s ^ 1, 6400, 1.3, "petal")
    return (20 + plumes * 215, np.clip(180 - _rk_gr(h, w, s ^ 3, 3, 3.4) * 120, 15, 255),
            24 + cv2.GaussianBlur(plumes, (0, 0), 1.5) * 170)


def _rwp_solar_paint(h, w, s):
    gran = _rk_rings(h, w, s ^ 1, 5200, 1.8, 1.2)
    lut = _rk_lut([(0.85, 0.45, 0.05), (1.0, 0.80, 0.25)], 0.5)
    return _rk_ramp(np.clip(gran * 0.8 + _rk_n(h, w, s ^ 2, (3, 7)) * 0.35, 0, 1), lut)

def _rwp_solar_spec(h, w, s):
    gran = _rk_rings(h, w, s ^ 1, 5200, 1.8, 1.2)
    return (24 + gran * 210, np.clip(170 - _rk_n(h, w, s ^ 3, (4, 9)) * 115, 15, 255),
            26 + cv2.GaussianBlur(gran, (0, 0), 1.5) * 160)


def _rwp_spectrum_paint(h, w, s):
    warp = _rk_sc(h, w, s ^ 1, 6000, 0.9, "streak", len_px=6)
    hue = _rk_ramp(_rk_n(h, w, s ^ 2, (5, 11)),
                   _rk_lut([(0.9, 0.15, 0.2), (0.95, 0.75, 0.1), (0.15, 0.75, 0.35), (0.15, 0.45, 0.9), (0.6, 0.2, 0.85)], 0.6))
    return np.clip(hue * (0.55 + warp[..., None] * 0.55), 0, 1)

def _rwp_spectrum_spec(h, w, s):
    warp = _rk_sc(h, w, s ^ 1, 6000, 0.9, "streak", len_px=6)
    return (18 + warp * 215, np.clip(75 + _rk_gr(h, w, s ^ 3, 2, 3.2) * 115, 15, 255),
            24 + _rk_n(h, w, s ^ 4, (16, 36)) * 150)


def _rwp_sunset_paint(h, w, s):
    bands = _rk_gr(h, w, s ^ 1, 3, 4.6)
    lut = _rk_lut([(0.85, 0.35, 0.15), (0.80, 0.15, 0.45), (0.30, 0.15, 0.50)], 0.6)
    return _rk_ramp(np.clip(bands + (_rk_n(h, w, s ^ 2, (3, 6)) - 0.5) * 0.25, 0, 1), lut)

def _rwp_sunset_spec(h, w, s):
    bands = _rk_gr(h, w, s ^ 1, 3, 4.6)
    return (18 + _rk_sc(h, w, s ^ 3, 4600, 0.9, "dot") * 205, np.clip(65 + bands * 125, 15, 255),
            24 + _rk_n(h, w, s ^ 4, (18, 40)) * 150)


def _rwp_titanium_paint(h, w, s):
    brush = _rk_gr(h, w, s ^ 1, 3, 2.8)
    th = np.clip(np.floor(np.clip(_rk_n(h, w, s ^ 2, (7, 15)), 0, 0.999) * 4) / 4 + brush * 0.15, 0, 1)
    return interference_palette(th, 2.2, 0.8, base_srgb=np.float32([0.55, 0.55, 0.58]))

def _rwp_titanium_spec(h, w, s):
    brush = _rk_gr(h, w, s ^ 1, 3, 2.8)
    return (50 + _rk_sc(h, w, s ^ 3, 3600, 0.9, "dot") * 180, np.clip(50 + brush * 120, 15, 255),
            26 + _rk_n(h, w, s ^ 4, (16, 36)) * 145)


def _rwp_toxic_paint(h, w, s):
    drip = _rk_sc(h, w, s ^ 1, 7600, 1.0, "streak", len_px=6)
    g = _rk_n(h, w, s ^ 2, (3, 6))[..., None]
    return np.clip(np.float32([0.07, 0.10, 0.05])[None, None, :] * (0.6 + g * 0.6) + drip[..., None] * np.float32([0.55, 0.95, 0.10]) * 0.7, 0, 1)

def _rwp_toxic_spec(h, w, s):
    drip = _rk_sc(h, w, s ^ 1, 7600, 1.0, "streak", len_px=6)
    return (18 + drip * 215, np.clip(185 - _rk_n(h, w, s ^ 3, (4, 9)) * 120, 15, 255),
            24 + cv2.GaussianBlur(drip, (0, 0), 1.6) * 175)


def _rwp_venom_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1300, (h * w) // 30))
    rng = np.random.default_rng(s ^ 2)
    m = (rng.random(int(lab.max()) + 1) > 0.45).astype(np.float32)[lab]
    return np.clip(_cs_dual(h, w, s, (0.25, 0.55, 0.05), (0.30, 0.05, 0.45), m) * (1 - edge[..., None] * 0.6) * (0.55 + _rk_n(h, w, s ^ 3, (3, 7))[..., None] * 0.55), 0, 1)

def _rwp_venom_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1300, (h * w) // 30))
    return (16 + (1 - edge) * 145 + _rk_sc(h, w, s ^ 4, 3000, 0.8, "dot") * 75,
            np.clip(190 - _rk_n(h, w, s ^ 5, (3, 8)) * 125 + edge * 30, 15, 255),
            24 + _rk_n(h, w, s ^ 6, (16, 36)) * 150)


REWORK_MONOLITHICS.update({fid: _rw_pair(fid, p, sp) for fid, p, sp in (
    ("prizm_adaptive", _rwp_adaptive_paint, _rwp_adaptive_spec),
    ("prizm_alien_skin", _rwp_alien_paint, _rwp_alien_spec),
    ("prizm_arctic", _rwp_arctic_paint, _rwp_arctic_spec),
    ("prizm_aurora_shift", _rwp_aurorashift_paint, _rwp_aurorashift_spec),
    ("prizm_black_rainbow", _rwp_blackrainbow_paint, _rwp_blackrainbow_spec),
    ("prizm_blood_moon", _rwp_bloodmoon_paint, _rwp_bloodmoon_spec),
    ("prizm_candy_paint", _rwp_candy_paint, _rwp_candy_spec),
    ("prizm_chrome_rose", _rwp_chromerose_paint, _rwp_chromerose_spec),
    ("prizm_copper_flame", _rwp_copperflame_paint, _rwp_copperflame_spec),
    ("prizm_cosmos", _rwp_cosmos_paint, _rwp_cosmos_spec),
    ("prizm_dark_matter", _rwp_darkmatter_paint, _rwp_darkmatter_spec),
    ("prizm_deep_space", _rwp_deepspace_paint, _rwp_deepspace_spec),
    ("prizm_duochrome", _rwp_duochrome_paint, _rwp_duochrome_spec),
    ("prizm_ember", _rwp_ember_paint, _rwp_ember_spec),
    ("prizm_fire_ice", _rwp_fireice_paint, _rwp_fireice_spec),
    ("prizm_galaxy_dust", _rwp_galaxydust_paint, _rwp_galaxydust_spec),
    ("prizm_holographic", _rwp_holo_paint, _rwp_holo_spec),
    ("prizm_iridescent", _rwp_iridescent_paint, _rwp_iridescent_spec),
    ("prizm_midnight", _rwp_midnight_paint, _rwp_midnight_spec),
    ("prizm_mystichrome", _rwp_mystichrome_paint, _rwp_mystichrome_spec),
    ("prizm_neon", _rwp_neon_paint, _rwp_neon_spec),
    ("prizm_oceanic", _rwp_oceanic_paint, _rwp_oceanic_spec),
    ("prizm_phoenix", _rwp_phoenix_paint, _rwp_phoenix_spec),
    ("prizm_solar", _rwp_solar_paint, _rwp_solar_spec),
    ("prizm_spectrum", _rwp_spectrum_paint, _rwp_spectrum_spec),
    ("prizm_sunset_strip", _rwp_sunset_paint, _rwp_sunset_spec),
    ("prizm_titanium", _rwp_titanium_paint, _rwp_titanium_spec),
    ("prizm_toxic_waste", _rwp_toxic_paint, _rwp_toxic_spec),
    ("prizm_venom", _rwp_venom_paint, _rwp_venom_spec),
)})
# === PRIZM rework END ===


# === SPEC COLOR-DIVERSITY upgrade for ALL 74 reworked finishes (2026-06-10) ===
# Owner doctrine (FABLE round-3 proven, H2.1-3.0): every channel rides a dense
# hard-swing field — identity MOTIF spikes + own-seed lattice filler. Each
# finish's three motifs come from ITS OWN concept geometry (spirit rule:
# anime reads anime, neon reads neon). Paints untouched here except
# anime_cel_shade_chrome (owner: round-1 didn't read as cel-shade).

def _f4_chan(motif, filler, lo=36.0, hi=204.0, spike=233.0):
    f = np.maximum(np.clip(motif, 0, 1), filler * 0.8)
    return lo + f * (hi - lo) + np.clip(motif, 0, 1) * (spike - hi)


def _f4_make(fid, mM, mR, mC):
    hsc = (abs(hash(fid)) % 5) * 0.3
    def spec_fn(shape, mask, seed, sm, _mM=mM, _mR=mR, _mC=mC, _f=fid, _h=hsc):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(_f, seed)
        M = _f4_chan(_mM(h, w, s), flip_lattice((h, w), s ^ 0xA1, 0.9 + _h, 0.5))
        R = _f4_chan(_mR(h, w, s ^ 0x51), flip_lattice((h, w), s ^ 0xB2, 1.5 + _h, 0.52), 33, 206)
        Cc = _f4_chan(_mC(h, w, s ^ 0x92), flip_lattice((h, w), s ^ 0xC3, 2.0 + _h, 0.47))
        M, R, Cc = (_upscale(np.clip(a, 0, 255).astype(np.float32), fh, fw) for a in (M, R, Cc))
        return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)
    return spec_fn


def _f4_edge(h, w, s, div=40):
    lab, d1, edge = _rk_vor(h, w, s, max(900, (h * w) // div))
    return edge


def _f4_grbin(h, w, s, axes=3, fq=3.0):
    return (_rk_gr(h, w, s, axes, fq) > 0.5).astype(np.float32)


_SPEC_RECIPES = {
    # ── INSECTS: chitin/structural-color motifs
    "beetle_jewel": (lambda h, w, s: _f4_edge(h, w, s ^ 1), lambda h, w, s: _f4_grbin(h, w, s), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.4, "dot")),
    "beetle_rainbow": (lambda h, w, s: _rk_rings(h, w, s, 3600, 3.2, 1.6), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.4), lambda h, w, s: _rk_rings(h, w, s, 2600, 4.5, 2.4)),
    "butterfly_morpho": (lambda h, w, s: _f4_grbin(h, w, s, 5, 3.2), lambda h, w, s: _rk_sc(h, w, s, 8000, 0.8, "streak", len_px=4), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.6, "dot")),
    "butterfly_monarch": (lambda h, w, s: _rk_web(h, w, s, 2600, k=2), lambda h, w, s: _f4_grbin(h, w, s), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.5, "dot")),
    "dragonfly_wing": (lambda h, w, s: _rk_web(h, w, s, 3600, k=2), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.6), lambda h, w, s: _rk_sc(h, w, s, 4600, 1.8, "dot")),
    "scarab_gold": (lambda h, w, s: _rk_sc(h, w, s, 9000, 1.1, "dot"), lambda h, w, s: _f4_grbin(h, w, s, 2, 2.8), lambda h, w, s: _rk_sc(h, w, s, 4200, 2.0, "petal")),
    "moth_luna": (lambda h, w, s: _rk_sc(h, w, s, 5200, 1.8, "star5"), lambda h, w, s: _rk_sc(h, w, s, 9000, 0.8, "streak", len_px=3), lambda h, w, s: _rk_sc(h, w, s, 4600, 1.7, "dot")),
    "beetle_stag": (lambda h, w, s: _f4_edge(h, w, s, 36), lambda h, w, s: _f4_grbin(h, w, s), lambda h, w, s: _rk_sc(h, w, s, 4200, 1.8, "dot")),
    "wasp_warning": (lambda h, w, s: _rk_sc(h, w, s, 6000, 1.0, "streak", len_px=5), lambda h, w, s: _rk_sc(h, w, s, 6000, 1.0, "streak", len_px=5), lambda h, w, s: _rk_sc(h, w, s, 5200, 2.2, "arc")),
    "firefly_glow": (lambda h, w, s: _rk_sc(h, w, s, 5200, 1.0, "dot"), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.4), lambda h, w, s: _rk_sc(h, w, s, 6000, 1.6, "dot")),
    # ── ANIME: print/toon motifs (halftone trio = true CMYK-style separation)
    "anime_cel_shade_chrome": (lambda h, w, s: _rk_web(h, w, s, 3000, k=2), lambda h, w, s: (np.floor(np.clip(_rk_n(h, w, s, (5, 12)), 0, 0.999) * 4) % 2).astype(np.float32), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.4, "star5")),
    "anime_speed_lines": (lambda h, w, s: _rk_sc(h, w, s, 6000, 1.0, "streak", len_px=9), lambda h, w, s: _rk_sc(h, w, s, 6000, 1.0, "streak", len_px=6), lambda h, w, s: _rk_sc(h, w, s, 4600, 2.4, "arc")),
    "anime_sparkle_burst": (lambda h, w, s: _rk_sc(h, w, s, 6000, 1.5, "star5"), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.2), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.1, "dot")),
    "anime_gradient_hair": (lambda h, w, s: _rk_sc(h, w, s, 5200, 0.9, "streak", len_px=7), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.0), lambda h, w, s: _rk_sc(h, w, s, 4600, 1.8, "petal")),
    "anime_mecha_plate": (lambda h, w, s: _f4_edge(h, w, s, 55), lambda h, w, s: _f4_grbin(h, w, s), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.1, "dot")),
    "anime_sakura_scatter": (lambda h, w, s: _rk_sc(h, w, s, 6000, 1.6, "petal"), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.4), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.3, "petal")),
    "anime_energy_aura": (lambda h, w, s: _rk_web(h, w, s, 3600, k=2), lambda h, w, s: _f4_grbin(h, w, s, 4, 3.0), lambda h, w, s: _rk_web(h, w, s, 2600, k=2)),
    "anime_comic_halftone": (lambda h, w, s: halftone(h, w, s, 4.0, 1), lambda h, w, s: halftone(h, w, s, 5.0, 1), lambda h, w, s: halftone(h, w, s, 6.0, 1)),
    "anime_neon_outline": (lambda h, w, s: _f4_edge(h, w, s, 75), lambda h, w, s: _f4_grbin(h, w, s), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.5, "dot")),
    "anime_crystal_facet": (lambda h, w, s: _f4_edge(h, w, s, 50), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.2), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.4, "dot")),
    # ── NEON: tube cores / crossing tubes / halos
    "neon_pink_blaze": (lambda h, w, s: _rk_web(h, w, s, 3600, k=2), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.2), lambda h, w, s: _rk_web(h, w, s, 2600, k=2)),
    "neon_toxic_green": (lambda h, w, s: _rk_rings(h, w, s, 4200, 2.0, 1.3), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.4), lambda h, w, s: _rk_rings(h, w, s, 3000, 2.8, 1.8)),
    "neon_electric_blue": (lambda h, w, s: _rk_sc(h, w, s, 7000, 0.9, "streak", len_px=5), lambda h, w, s: _rk_sc(h, w, s, 5200, 0.9, "streak", len_px=8), lambda h, w, s: _rk_sc(h, w, s, 4600, 2.2, "arc")),
    "neon_blacklight": (lambda h, w, s: _rk_sc(h, w, s, 7000, 1.0, "star5"), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.0), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.5, "dot")),
    "neon_orange_hazard": (lambda h, w, s: _rk_sc(h, w, s, 6000, 1.0, "streak", len_px=4), lambda h, w, s: _rk_sc(h, w, s, 6000, 1.0, "streak", len_px=4), lambda h, w, s: _rk_sc(h, w, s, 6000, 1.6, "arc")),
    "neon_red_alert": (lambda h, w, s: _rk_rings(h, w, s, 4200, 1.8, 1.2), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.2), lambda h, w, s: _rk_rings(h, w, s, 3000, 2.6, 1.7)),
    "neon_cyber_yellow": (lambda h, w, s: _rk_web(h, w, s, 3200, k=2), lambda h, w, s: _f4_grbin(h, w, s), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.2, "dot")),
    "neon_ice_white": (lambda h, w, s: _rk_sc(h, w, s, 8000, 0.8, "streak", len_px=3), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.0), lambda h, w, s: _rk_sc(h, w, s, 4200, 2.2, "star5")),
    "neon_dual_glow": (lambda h, w, s: flip_lattice((h, w), s, 1.1, 0.32), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.2), lambda h, w, s: flip_lattice((h, w), s, 2.4, 0.30)),
    "neon_rainbow_tube": (lambda h, w, s: _rk_web(h, w, s, 3200, k=2), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.4), lambda h, w, s: _rk_web(h, w, s, 2400, k=2)),
    # ── CHAMELEON: flip-pair motifs
    "chameleon_amethyst": (lambda h, w, s: flip_lattice((h, w), s, 0.9, 0.48), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.2), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.4, "dot")),
    "chameleon_arctic": (lambda h, w, s: _rk_sc(h, w, s, 8000, 0.8, "streak", len_px=4), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.0), lambda h, w, s: _rk_sc(h, w, s, 4200, 2.0, "arc")),
    "chameleon_aurora": (lambda h, w, s: _rk_sc(h, w, s, 5200, 0.9, "streak", len_px=6), lambda h, w, s: _f4_grbin(h, w, s, 3, 4.0), lambda h, w, s: _rk_sc(h, w, s, 4600, 1.9, "petal")),
    "chameleon_copper": (lambda h, w, s: _f4_edge(h, w, s, 42), lambda h, w, s: _f4_grbin(h, w, s), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.3, "dot")),
    "chameleon_emerald": (lambda h, w, s: flip_lattice((h, w), s, 1.0, 0.30), lambda h, w, s: _f4_grbin(h, w, s, 4, 3.4), lambda h, w, s: _rk_sc(h, w, s, 4600, 1.6, "dot")),
    "chameleon_fire": (lambda h, w, s: _rk_sc(h, w, s, 6000, 1.5, "petal"), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.2), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.2, "dot")),
    "chameleon_frost": (lambda h, w, s: _rk_web(h, w, s, 4200, k=2), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.0), lambda h, w, s: _rk_sc(h, w, s, 4600, 1.7, "star5")),
    "chameleon_galaxy": (lambda h, w, s: _rk_sc(h, w, s, 6000, 1.0, "dot"), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.4), lambda h, w, s: flip_lattice((h, w), s, 2.5, 0.5)),
    "chameleon_midnight": (lambda h, w, s: _rk_sc(h, w, s, 5200, 0.9, "dot"), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.4), lambda h, w, s: _rk_sc(h, w, s, 3600, 2.0, "dot")),
    "chameleon_neon": (lambda h, w, s: flip_lattice((h, w), s, 1.0, 0.32), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.0), lambda h, w, s: _rk_web(h, w, s, 2600, k=2)),
    "chameleon_obsidian": (lambda h, w, s: _f4_edge(h, w, s, 44), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.2), lambda h, w, s: _rk_sc(h, w, s, 3600, 1.9, "dot")),
    "chameleon_ocean": (lambda h, w, s: _rk_sc(h, w, s, 4600, 0.9, "dot"), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.6), lambda h, w, s: _rk_sc(h, w, s, 4200, 2.0, "arc")),
    "chameleon_phoenix": (lambda h, w, s: _rk_sc(h, w, s, 5600, 1.5, "petal"), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.4), lambda h, w, s: _rk_sc(h, w, s, 4600, 1.8, "dot")),
    "chameleon_venom": (lambda h, w, s: _f4_edge(h, w, s, 34), lambda h, w, s: _f4_grbin(h, w, s), lambda h, w, s: _rk_sc(h, w, s, 4600, 1.2, "dot")),
    "mystichrome": (lambda h, w, s: tri_partition((h, w), s, cells=max(2600, (h * w) // 16), soften_px=1.0)[1], lambda h, w, s: _f4_grbin(h, w, s, 3, 3.2), lambda h, w, s: tri_partition((h, w), s, cells=max(2600, (h * w) // 16), soften_px=1.0)[0]),
    # ── PRIZM: prismatic motifs
    "prizm_adaptive": (lambda h, w, s: _f4_edge(h, w, s, 38), lambda h, w, s: _f4_grbin(h, w, s), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.3, "dot")),
    "prizm_alien_skin": (lambda h, w, s: _rk_rings(h, w, s, 4200, 1.8, 1.2), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.4), lambda h, w, s: _rk_rings(h, w, s, 3000, 2.6, 1.6)),
    "prizm_arctic": (lambda h, w, s: _rk_sc(h, w, s, 7000, 1.0, "streak", len_px=4), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.0), lambda h, w, s: _rk_sc(h, w, s, 4600, 1.8, "star5")),
    "prizm_aurora_shift": (lambda h, w, s: _rk_sc(h, w, s, 4600, 0.9, "streak", len_px=5), lambda h, w, s: _f4_grbin(h, w, s, 4, 3.8), lambda h, w, s: _rk_sc(h, w, s, 4200, 1.9, "petal")),
    "prizm_black_rainbow": (lambda h, w, s: _rk_web(h, w, s, 4200, k=2), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.2), lambda h, w, s: _rk_web(h, w, s, 3000, k=2)),
    "prizm_blood_moon": (lambda h, w, s: _rk_rings(h, w, s, 4600, 1.8, 1.2), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.4), lambda h, w, s: _rk_rings(h, w, s, 3200, 2.4, 1.5)),
    "prizm_candy_paint": (lambda h, w, s: _rk_sc(h, w, s, 12000, 1.1, "dot"), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.2), lambda h, w, s: _rk_sc(h, w, s, 6000, 1.5, "dot")),
    "prizm_chrome_rose": (lambda h, w, s: _rk_sc(h, w, s, 6000, 1.1, "petal"), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.4), lambda h, w, s: _rk_sc(h, w, s, 4600, 1.6, "petal")),
    "prizm_copper_flame": (lambda h, w, s: _rk_sc(h, w, s, 5600, 1.5, "petal"), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.0), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.1, "dot")),
    "prizm_cosmos": (lambda h, w, s: _rk_sc(h, w, s, 8000, 0.9, "dot"), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.4), lambda h, w, s: _rk_sc(h, w, s, 4200, 2.0, "dot")),
    "prizm_dark_matter": (lambda h, w, s: _f4_edge(h, w, s, 32), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.2), lambda h, w, s: _rk_sc(h, w, s, 3600, 1.7, "dot")),
    "prizm_deep_space": (lambda h, w, s: _rk_sc(h, w, s, 9000, 0.8, "dot"), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.0), lambda h, w, s: _rk_sc(h, w, s, 4600, 1.5, "dot")),
    "prizm_duochrome": (lambda h, w, s: flip_lattice((h, w), s, 1.0, 0.32), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.2), lambda h, w, s: flip_lattice((h, w), s, 2.3, 0.30)),
    "prizm_ember": (lambda h, w, s: _rk_sc(h, w, s, 7000, 1.0, "dot"), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.4), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.5, "dot")),
    "prizm_fire_ice": (lambda h, w, s: tri_partition((h, w), s, cells=max(2400, (h * w) // 18), soften_px=0.8)[0], lambda h, w, s: _f4_grbin(h, w, s, 3, 3.2), lambda h, w, s: tri_partition((h, w), s, cells=max(2400, (h * w) // 18), soften_px=0.8)[1]),
    "prizm_galaxy_dust": (lambda h, w, s: _rk_sc(h, w, s, 10000, 0.8, "dot"), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.0), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.4, "dot")),
    "prizm_holographic": (lambda h, w, s: _rk_sc(h, w, s, 7000, 0.9, "streak", len_px=5), lambda h, w, s: _f4_grbin(h, w, s, 4, 3.2), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.3, "dot")),
    "prizm_iridescent": (lambda h, w, s: _rk_rings(h, w, s, 3600, 2.6, 1.5), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.4), lambda h, w, s: _rk_rings(h, w, s, 2600, 3.4, 2.0)),
    "prizm_midnight": (lambda h, w, s: _rk_sc(h, w, s, 5200, 0.9, "streak", len_px=7), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.2), lambda h, w, s: _rk_sc(h, w, s, 4200, 1.8, "dot")),
    "prizm_mystichrome": (lambda h, w, s: _rk_sc(h, w, s, 4600, 0.8, "dot"), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.4), lambda h, w, s: _rk_sc(h, w, s, 4200, 1.9, "petal")),
    "prizm_neon": (lambda h, w, s: _rk_web(h, w, s, 4200, k=2), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.2), lambda h, w, s: _rk_web(h, w, s, 3000, k=2)),
    "prizm_oceanic": (lambda h, w, s: _rk_web(h, w, s, 4600, k=2), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.6), lambda h, w, s: _rk_sc(h, w, s, 4600, 1.9, "arc")),
    "prizm_phoenix": (lambda h, w, s: _rk_sc(h, w, s, 6400, 1.3, "petal"), lambda h, w, s: _f4_grbin(h, w, s, 3, 3.4), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.2, "dot")),
    "prizm_solar": (lambda h, w, s: _rk_rings(h, w, s, 5200, 1.6, 1.1), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.0), lambda h, w, s: _rk_rings(h, w, s, 3600, 2.2, 1.4)),
    "prizm_spectrum": (lambda h, w, s: _rk_sc(h, w, s, 6000, 0.9, "streak", len_px=6), lambda h, w, s: _f4_grbin(h, w, s, 4, 3.2), lambda h, w, s: _rk_sc(h, w, s, 4600, 1.6, "dot")),
    "prizm_sunset_strip": (lambda h, w, s: _rk_sc(h, w, s, 5200, 0.9, "dot"), lambda h, w, s: _f4_grbin(h, w, s, 3, 4.2), lambda h, w, s: _rk_sc(h, w, s, 4200, 2.0, "petal")),
    "prizm_titanium": (lambda h, w, s: _rk_sc(h, w, s, 4600, 0.9, "dot"), lambda h, w, s: _f4_grbin(h, w, s, 3, 2.8), lambda h, w, s: _rk_sc(h, w, s, 4200, 1.7, "arc")),
    "prizm_toxic_waste": (lambda h, w, s: _rk_sc(h, w, s, 6000, 1.0, "streak", len_px=6), lambda h, w, s: _f4_grbin(h, w, s, 2, 3.4), lambda h, w, s: _rk_sc(h, w, s, 5200, 1.4, "dot")),
    "prizm_venom": (lambda h, w, s: _f4_edge(h, w, s, 30), lambda h, w, s: _f4_grbin(h, w, s), lambda h, w, s: _rk_sc(h, w, s, 4200, 1.3, "dot")),
}

for _fid, (_a, _b, _c) in _SPEC_RECIPES.items():
    REWORK_MONOLITHICS[_fid] = (_f4_make(_fid, _a, _b, _c), REWORK_MONOLITHICS[_fid][1])

# 2026-06-21 COLOR SCIENCE REDIRECT: apply the elaborate per-finish chameleon specs
# AFTER the _f4 install above, so they are the final shipping chameleon spec.
_apply_chameleon_color_science()


# ── SPIRIT FIX: anime_cel_shade_chrome paint — true cel-shade: flat toon color
# cells with hard 3-step shading + bold dark outline (the anime ink line) +
# chrome star-glints. (Owner: round-1 "wouldn't be what I'd call Cel Shade
# Chrome in terms of Anime".)
def _rwa_cel_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 70))
    rng = np.random.default_rng(s ^ 2)
    lut = _rk_lut([(0.20, 0.35, 0.75), (0.45, 0.65, 0.92), (0.80, 0.88, 0.97)], 0.5)
    t = rng.random(int(lab.max()) + 1).astype(np.float32)
    cel = _rk_ramp((np.floor(np.clip(t[lab], 0, 0.999) * 3) / 2.0), lut)  # 3 hard toon steps
    ink = np.clip(edge * 1.6, 0, 1)
    glint = _rk_sc(h, w, s ^ 3, 4200, 1.5, "star5")
    eff = np.clip(cel * (1 - ink[..., None] * 0.92) + glint[..., None] * np.float32([0.95, 0.97, 1.0]) * 0.6, 0, 1)
    return np.clip(eff * (0.62 + _rk_n(h, w, s ^ 99, (2, 5))[..., None] * 0.65), 0, 1)


REWORK_MONOLITHICS["anime_cel_shade_chrome"] = (
    REWORK_MONOLITHICS["anime_cel_shade_chrome"][0],
    _rw_pair("anime_cel_shade_chrome", _rwa_cel_paint, lambda h, w, s: (np.zeros((h, w)), np.zeros((h, w)), np.zeros((h, w))))[1],
)
# === SPEC DIVERSITY upgrade END ===


# === IGNITION REBUILD 2026-06-10 START ===
# --- IGNITION: anime_cel_shade_chrome ---
def _ign_anime_cel_shade_chrome_paint(h, w, s):
    # Toon cells with 3 hard cel steps per panel (blue anime ramp); the ink
    # outlines are printed near-BLACK — they are the hidden ignition geometry —
    # and chrome star-glints spark the fills.
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 70))
    t = np.random.default_rng(s ^ 2).random(int(lab.max()) + 1).astype(np.float32)
    step = (np.floor(np.clip(t[lab], 0, 0.999) * 3) / 2.0).astype(np.float32)
    d1n = np.clip(d1 / max(float(d1.max()), 1e-5), 0, 1)
    cel = _rk_ramp(step, _rk_lut([(0.16, 0.30, 0.70), (0.44, 0.64, 0.92), (0.82, 0.90, 0.98)], 0.5))
    ink = np.clip(edge * 1.6, 0, 1)
    glint = _rk_sc(h, w, s ^ 3, 4200, 1.5, "star5")
    eff = cel * (1.0 - ink[..., None] * 0.93) * (0.92 + (1.0 - d1n)[..., None] * 0.13)
    eff = eff + glint[..., None] * np.float32([0.96, 0.98, 1.0]) * 0.62
    return np.clip(eff, 0, 1).astype(np.float32)


def _ign_anime_cel_shade_chrome_spec(h, w, s):
    # SAME cells / SAME ink lines / SAME glints / SAME cell-pool shading as the
    # paint (same seeds). IGNITION (M): the near-black ink linework detonates
    # to liquid chrome — invisible toon outlines that flash when the sun rakes
    # them. R rides the cel-step fills (dark step = matte), Cc pools in the
    # cell interiors around the star glints (third aspect).
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 70))
    t = np.random.default_rng(s ^ 2).random(int(lab.max()) + 1).astype(np.float32)
    step = (np.floor(np.clip(t[lab], 0, 0.999) * 3) / 2.0).astype(np.float32)
    d1n = np.clip(d1 / max(float(d1.max()), 1e-5), 0, 1)
    glint = _rk_sc(h, w, s ^ 3, 4200, 1.5, "star5")
    core = np.clip((edge - 0.58) / 0.30, 0, 1)
    M = np.clip(16 + core * 236 + glint * 70, 0, 252)
    R = np.clip(56 + (1.0 - step) * 118 - np.clip(edge * 1.6, 0, 1) * 30
                + (_rk_n(h, w, s ^ 4, (20, 47)) - 0.5) * 26, 15, 255)
    Cc = np.clip(26 + cv2.GaussianBlur(glint, (0, 0), 2.2) * 148 + (1.0 - d1n) * 62, 16, 240)
    return M, R, Cc


# --- IGNITION: anime_speed_lines ---
def _ign_anime_speed_lines_paint(h, w, s):
    # Two streak swarms at every angle over midnight blue: white pass-lines (a)
    # and cyan slip-streams (b). The white lines are the ignition set.
    a = _rk_sc(h, w, s ^ 1, 6000, 1.1, "streak", len_px=9)
    b = _rk_sc(h, w, s ^ 2, 2800, 1.0, "streak", len_px=7)
    n3 = _rk_n(h, w, s ^ 3, (6, 14))
    base = _rk_ramp(n3, _rk_lut([(0.06, 0.08, 0.19), (0.15, 0.20, 0.37)], 0.5))
    return np.clip(base + a[..., None] * np.float32([0.95, 0.97, 1.0]) * 0.9
                   + b[..., None] * np.float32([0.35, 0.70, 0.95]) * 0.55, 0, 1).astype(np.float32)


def _ign_anime_speed_lines_spec(h, w, s):
    # SAME streak fields, SAME seeds. IGNITION (M): every white pass-line in
    # the paint relights as a chrome hot-line. R rides the midnight macro field
    # with the cyan slip-streams cut glass-smooth; Cc is the blurred wake of
    # both swarms (a third aspect of the same motion system).
    a = _rk_sc(h, w, s ^ 1, 6000, 1.1, "streak", len_px=9)
    b = _rk_sc(h, w, s ^ 2, 2800, 1.0, "streak", len_px=7)
    n3 = _rk_n(h, w, s ^ 3, (6, 14))
    M = np.clip(15 + np.clip(a * 2.8, 0, 1) * 238, 0, 253)
    R = np.clip(62 + (1.0 - n3) * 118 - np.clip(b * 1.5, 0, 1) * 46
                + (_rk_n(h, w, s ^ 4, (24, 55)) - 0.5) * 24, 15, 255)
    Cc = np.clip(22 + cv2.GaussianBlur(np.maximum(a, b * 0.85), (0, 0), 2.4) * 175, 16, 245)
    return M, R, Cc


# --- IGNITION: anime_sparkle_burst ---
def _ign_anime_sparkle_burst_paint(h, w, s):
    # Deep violet panel; visible shoujo stars (st) + gold micro-dots (dt); a
    # GHOST bokeh swarm (gh) prints as barely-darker violet rounds — the hidden
    # ignition layer of the sparkle-eyes panel.
    st = _rk_sc(h, w, s ^ 1, 4800, 1.4, "star5")
    dt = _rk_sc(h, w, s ^ 2, 3000, 0.9, "dot")
    gh = np.clip(_rk_sc(h, w, s ^ 5, 5500, 2.6, "dot", amp=(0.75, 1.0)) * 2.0, 0, 1)
    base = _rk_ramp(_rk_n(h, w, s ^ 3, (5, 12)), _rk_lut([(0.17, 0.07, 0.27), (0.31, 0.14, 0.43)], 0.5))
    eff = base * (1.0 - gh[..., None] * 0.30)
    eff = eff + st[..., None] * np.float32([0.97, 0.78, 0.88]) * 0.72 + dt[..., None] * np.float32([0.95, 0.84, 0.42]) * 0.55
    return np.clip(eff, 0, 1).astype(np.float32)


def _ign_anime_sparkle_burst_spec(h, w, s):
    # SAME star/dot/ghost fields, SAME seeds. IGNITION (M): the ghost bokeh —
    # dark violet in the paint — detonates near-max: an invisible sparkle swarm
    # that erupts when the sun lines up. R rides the violet macro mottle with
    # the visible stars cut glassy; Cc blooms softly on the visible stars.
    st = _rk_sc(h, w, s ^ 1, 4800, 1.4, "star5")
    dt = _rk_sc(h, w, s ^ 2, 3000, 0.9, "dot")
    gh = np.clip(_rk_sc(h, w, s ^ 5, 5500, 2.6, "dot", amp=(0.75, 1.0)) * 2.0, 0, 1)
    M = np.clip(14 + gh * 240 + dt * 60, 0, 254)
    R = np.clip(58 + (1.0 - _rk_n(h, w, s ^ 3, (5, 12))) * 112 - np.clip(st * 1.5, 0, 1) * 52, 15, 255)
    Cc = np.clip(24 + cv2.GaussianBlur(st, (0, 0), 2.0) * 168 + dt * 40, 16, 244)
    return M, R, Cc


# --- IGNITION: anime_gradient_hair ---
def _ign_anime_gradient_hair_paint(h, w, s):
    # Multi-angle silk strands; hue drifts pink→lavender→teal along the SAME
    # strand+drift fields; a fine satin mottle (n4) breathes through the silk;
    # strand crests carry a lighter highlight — the crest set is the ignition
    # geometry.
    strand = _rk_gr(h, w, s ^ 1, 2, 3.0)
    drift = _rk_n(h, w, s ^ 2, (4, 9))
    n4 = _rk_n(h, w, s ^ 4, (22, 51))
    crest = np.clip((strand - 0.62) / 0.30, 0, 1)
    silk = _rk_ramp(np.clip(strand * 0.55 + drift * 0.50, 0, 1),
                    _rk_lut([(0.86, 0.46, 0.66), (0.60, 0.48, 0.84), (0.34, 0.64, 0.80)], 0.6))
    eff = silk * (0.80 + strand[..., None] * 0.25) * (0.90 + n4[..., None] * 0.18)
    eff = eff + crest[..., None] * np.float32([1.0, 0.94, 0.97]) * 0.16
    return np.clip(eff, 0, 1).astype(np.float32)


def _ign_anime_gradient_hair_spec(h, w, s):
    # SAME strand/drift/satin/crest fields, SAME seeds. IGNITION (Cc): the wet
    # shine-band flash detonates on the exact crest highlights the paint drew.
    # M flares only on the teal end of the SAME hue field with the crest set
    # carved out (shine band is glass, not metal — a designed split), R rides
    # the satin mottle the paint breathes through.
    strand = _rk_gr(h, w, s ^ 1, 2, 3.0)
    drift = _rk_n(h, w, s ^ 2, (4, 9))
    n4 = _rk_n(h, w, s ^ 4, (22, 51))
    crest = np.clip((strand - 0.62) / 0.30, 0, 1)
    hue = np.clip(strand * 0.55 + drift * 0.50, 0, 1)
    M = np.clip(20 + np.clip((hue - 0.62) / 0.30, 0, 1) * (1.0 - crest * 0.85) * 150, 0, 220)
    R = np.clip(50 + (1.0 - n4) * 118 - crest * 26, 15, 255)
    Cc = np.clip(18 + crest * 235 + drift * 16, 16, 253)
    return M, R, Cc


# --- IGNITION: anime_mecha_plate ---
def _ign_anime_mecha_plate_paint(h, w, s):
    # Voronoi armor panels with per-panel gunmetal (shared t-draw), micro
    # grime, rivet studs, and panel-line seams carrying a faint cyan edge-light
    # — the lit seams are the ignition geometry.
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 60))
    t = np.random.default_rng(s ^ 3).random(int(lab.max()) + 1).astype(np.float32)
    gun = _rk_ramp(t[lab], _rk_lut([(0.27, 0.29, 0.33), (0.40, 0.42, 0.48)], 0.5))
    grime = _rk_n(h, w, s ^ 4, (8, 19))
    riv = _rk_sc(h, w, s ^ 2, 3000, 1.2, "dot")
    glow = np.clip((edge - 0.45) / 0.35, 0, 1)
    eff = gun * (0.78 + grime[..., None] * 0.34) * (1.0 - np.clip(edge * 1.3, 0, 1)[..., None] * 0.62)
    eff = eff + glow[..., None] * np.float32([0.30, 0.85, 0.95]) * 0.60 + riv[..., None] * 0.38
    return np.clip(eff, 0, 1).astype(np.float32)


def _ign_anime_mecha_plate_spec(h, w, s):
    # SAME panels / SAME per-panel t-draw / SAME rivets / SAME seam field.
    # IGNITION (Cc): the cyan-lit seam cores detonate wet — energy panel-lines
    # flashing across the armor. M rides the per-panel gunmetal value + rivet
    # pins; R rides the grime with seam corridors slightly scuffed.
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 60))
    t = np.random.default_rng(s ^ 3).random(int(lab.max()) + 1).astype(np.float32)
    grime = _rk_n(h, w, s ^ 4, (8, 19))
    riv = _rk_sc(h, w, s ^ 2, 3000, 1.2, "dot")
    glow = np.clip((edge - 0.45) / 0.35, 0, 1)
    M = np.clip(58 + t[lab] * 108 + riv * 88 - glow * 30, 0, 230)
    R = np.clip(50 + (1.0 - grime) * 126 + np.clip(edge * 1.3, 0, 1) * 34, 15, 255)
    Cc = np.clip(18 + glow * 235 + cv2.GaussianBlur(glow, (0, 0), 2.2) * 40, 16, 254)
    return M, R, Cc


# --- IGNITION: anime_sakura_scatter ---
def _ign_anime_sakura_scatter_paint(h, w, s):
    day = _rk_sc(h, w, s ^ 1, 3200, 1.9, "petal")                    # micro blush petals
    moon = _rk_sc(h, w, s ^ 2, 5200, 4.2, "petal", amp=(0.75, 1.0))  # moonlit petal pads (ignition subset)
    dk = np.clip((moon - 0.02) * 13.0, 0, 1)                         # SAME silhouettes the spec detonates
    drift = cv2.GaussianBlur(np.maximum(day, dk), (0, 0), 3.0)       # petal drift-wake
    base = _rk_ramp(_rk_n(h, w, s ^ 3, (4, 9)), _rk_lut([(0.93, 0.87, 0.83), (0.97, 0.92, 0.89)], 0.6))
    pet = np.clip(day * 1.3, 0, 1)[..., None]
    eff = base * (1 - drift[..., None] * 0.12) * (1 - pet * 0.62) + np.float32([0.96, 0.55, 0.66]) * pet * 0.68
    eff = eff * (1 - dk[..., None] * 0.88) + np.float32([0.30, 0.10, 0.19]) * dk[..., None] * 0.62
    return np.clip(eff, 0, 1).astype(np.float32)


def _ign_anime_sakura_scatter_spec(h, w, s):
    day = _rk_sc(h, w, s ^ 1, 3200, 1.9, "petal")
    moon = _rk_sc(h, w, s ^ 2, 5200, 4.2, "petal", amp=(0.75, 1.0))
    dk = np.clip((moon - 0.02) * 13.0, 0, 1)
    drift = cv2.GaussianBlur(np.maximum(day, dk), (0, 0), 3.0)
    Cc = 18 + dk * 237                                               # EXACT moonlit petals detonate wet
    M = 16 + np.clip(day * 1.3, 0, 1) * 158                          # blush petals = calm pearl trace
    R = np.clip(190 - np.clip(drift * 1.8, 0, 1) * 140 - dk * 18, 15, 255)  # drift-wake gloss rivers
    return np.clip(M, 0, 255), R, np.clip(Cc, 0, 255)


# --- IGNITION: anime_energy_aura ---
def _ign_anime_energy_aura_paint(h, w, s):
    cyan = _rk_web(h, w, s ^ 1, 5200, k=2)                           # lit cyan aura
    dkt = np.clip((cv2.GaussianBlur(_rk_web(h, w, s ^ 2, 3600, k=2), (0, 0), 1.2) - 0.02) * 6.0, 0, 1)
    halo = cv2.GaussianBlur(cyan + dkt * 0.5, (0, 0), 4.0)
    base = np.float32([0.05, 0.05, 0.11])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 3, (6, 14))[..., None] * 0.6)
    eff = base + halo[..., None] * np.float32([0.10, 0.12, 0.22]) * 0.5
    eff = eff + cyan[..., None] * np.float32([0.15, 0.85, 0.95]) * 0.72
    eff = eff * (1 - dkt[..., None] * 0.5) + dkt[..., None] * np.float32([0.30, 0.04, 0.18]) * 0.55
    return np.clip(eff, 0, 1).astype(np.float32)


def _ign_anime_energy_aura_spec(h, w, s):
    cyan = _rk_web(h, w, s ^ 1, 5200, k=2)
    dkt = np.clip((cv2.GaussianBlur(_rk_web(h, w, s ^ 2, 3600, k=2), (0, 0), 1.2) - 0.02) * 6.0, 0, 1)
    halo = cv2.GaussianBlur(cyan + dkt * 0.5, (0, 0), 4.0)
    M = 12 + dkt * 243                                               # hidden magenta aura DETONATES
    R = np.clip(195 - np.clip(halo * 1.6, 0, 1) * 155, 15, 255)      # gloss corridors along ALL aura paths
    Cc = 22 + cyan * 150 + cv2.GaussianBlur(cyan, (0, 0), 1.6) * 35  # lit filaments traced wet (calm)
    return np.clip(M, 0, 255), R, np.clip(Cc, 0, 255)


# --- IGNITION: anime_comic_halftone ---
def _ign_anime_comic_halftone_paint(h, w, s):
    dots = halftone(h, w, s ^ 1, 4.5, 3)                             # visible ink screens
    ghost = halftone(h, w, s ^ 2, 8.0, 2)                            # hidden foil screen (watermark)
    paper = _rk_ramp(_rk_n(h, w, s ^ 3, (5, 11)), _rk_lut([(0.90, 0.87, 0.80), (0.95, 0.93, 0.87)], 0.6))
    d = np.clip(dots * 1.25, 0, 1)[..., None]
    eff = paper * (1 - d * 0.92) + np.float32([0.09, 0.11, 0.23]) * d * 0.92
    eff = eff * (1 - np.clip(ghost * 1.45, 0, 1)[..., None] * 0.10)  # ghost = faint watermark in albedo
    return np.clip(eff, 0, 1).astype(np.float32)


def _ign_anime_comic_halftone_spec(h, w, s):
    dots = halftone(h, w, s ^ 1, 4.5, 3)
    ghost = halftone(h, w, s ^ 2, 8.0, 2)
    density = cv2.GaussianBlur(dots, (0, 0), 5.0)                    # print-density bands
    M = 16 + np.clip(dots * 1.25, 0, 1) * 172                        # SAME ink dots read metallic-ink (calm)
    R = np.clip(60 + density * 165 + _rk_n(h, w, s ^ 4, (15, 35)) * 40, 15, 255)
    Cc = 20 + np.clip(ghost * 1.45, 0, 1) * 235                      # hidden screen DETONATES as foil stamp
    return np.clip(M, 0, 255), R, np.clip(Cc, 0, 255)


# --- IGNITION: anime_neon_outline ---
def _ign_anime_neon_outline_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 80))
    live = (np.random.default_rng(s ^ 2).random(int(lab.max()) + 1) > 0.45).astype(np.float32)[lab]
    lit, off = edge * live, edge * (1 - live)                        # powered tubes vs dead tubes
    glow = cv2.GaussianBlur(lit, (0, 0), 3.0)
    base = np.float32([0.05, 0.05, 0.08])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 3, (5, 12))[..., None] * 0.6)
    eff = base + glow[..., None] * np.float32([0.10, 0.45, 0.50]) * 0.35
    eff = eff + lit[..., None] * np.float32([0.20, 0.92, 0.96]) * 0.92
    eff = eff + off[..., None] * np.float32([0.30, 0.03, 0.14]) * 0.40  # dead tubes: faint dark magenta
    return np.clip(eff, 0, 1).astype(np.float32)


def _ign_anime_neon_outline_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 80))
    live = (np.random.default_rng(s ^ 2).random(int(lab.max()) + 1) > 0.45).astype(np.float32)[lab]
    lit, off = edge * live, edge * (1 - live)
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    M = 12 + np.clip(off * 1.8, 0, 1) * 243                          # dead tubes IGNITE mirror-pink
    R = np.clip(165 - d1n * 120 + edge * 50, 15, 255)                # cell-interior pools
    Cc = 24 + lit * 150 + cv2.GaussianBlur(lit, (0, 0), 2.2) * 55    # lit tubes wet-glow halo
    return np.clip(M, 0, 255), R, np.clip(Cc, 0, 255)


# --- IGNITION: anime_crystal_facet ---
def _ign_anime_crystal_facet_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(800, (h * w) // 38))
    t = np.random.default_rng(s ^ 2).random(int(lab.max()) + 1).astype(np.float32)[lab]
    mirror = (t > 0.78).astype(np.float32)                           # SAME draw picks the mirror facets
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    col = _rk_ramp(np.clip(t / 0.78, 0, 1), _rk_lut([(0.25, 0.75, 0.85), (0.45, 0.30, 0.80), (0.90, 0.45, 0.65)], 0.55))
    deep = np.float32([0.07, 0.04, 0.13])[None, None, :] * (0.5 + d1n[..., None] * 0.7)
    eff = col * (0.5 + d1n[..., None] * 0.65) * (1 - mirror[..., None]) + deep * mirror[..., None]
    return np.clip(eff * (1 - edge[..., None] * 0.6), 0, 1).astype(np.float32)


def _ign_anime_crystal_facet_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(800, (h * w) // 38))
    t = np.random.default_rng(s ^ 2).random(int(lab.max()) + 1).astype(np.float32)[lab]
    mirror = (t > 0.78).astype(np.float32)
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    M = 14 + mirror * (1 - edge) * 240                               # EXACT dark facets detonate
    R = np.clip(195 - np.clip(t / 0.78, 0, 1) * 145 + edge * 55, 15, 255)  # gloss walks the SAME ramp
    Cc = 24 + np.clip(cv2.GaussianBlur(edge, (0, 0), 1.6), 0, 1) * 130 + d1n * 80  # groove shimmer pools
    return np.clip(M, 0, 255), R, np.clip(Cc, 0, 255)


# --- IGNITION: chameleon_amethyst ---
def _ign_chameleon_amethyst_paint(h, w, s):
    # Violet satin body; ~26% micro teal cells painted near-BLACK teal (the hidden flip side).
    flip = flip_lattice((h, w), s ^ 1, 1.1, 0.26)
    seam = np.clip(np.abs(cv2.GaussianBlur(flip, (0, 0), 1.0) - flip) * 2.5, 0, 1)
    g = _rk_n(h, w, s ^ 2, (3, 6))
    violet = np.float32([0.40, 0.15, 0.60])[None, None, :] * (0.60 + g[..., None] * 0.55)
    teal = np.float32([0.02, 0.10, 0.11])[None, None, :] * (0.80 + g[..., None] * 0.40)
    eff = violet * (1.0 - flip[..., None]) + teal * flip[..., None]
    return np.clip(eff * (1.0 - seam[..., None] * 0.30), 0, 1)

def _ign_chameleon_amethyst_spec(h, w, s):
    # SAME lattice/seam/grain as the paint: M detonates on the dark teal cells (the flip),
    # R rides the cell-boundary corridors, Cc rides the violet body's satin pools.
    flip = flip_lattice((h, w), s ^ 1, 1.1, 0.26)
    seam = np.clip(np.abs(cv2.GaussianBlur(flip, (0, 0), 1.0) - flip) * 2.5, 0, 1)
    g = _rk_n(h, w, s ^ 2, (3, 6))
    M = 14.0 + np.clip(flip * 1.35, 0, 1) * 240.0 * (1.0 - seam * 0.25)
    R = np.clip(70.0 + seam * 150.0 - flip * 40.0, 15, 255)
    Cc = 26.0 + g * 160.0 * (1.0 - flip * 0.5) + seam * 25.0
    return M, R, Cc


# --- IGNITION: chameleon_arctic ---
def _ign_chameleon_arctic_paint(h, w, s):
    # Ice-blue/pale-violet soft flip body; 9500 icy filaments painted as bright threads.
    fil = _rk_sc(h, w, s ^ 1, 9500, 0.8, "streak", len_px=6)
    flip = flip_lattice((h, w), s ^ 2, 1.4, 0.5)
    swell = _rk_n(h, w, s ^ 3, (3, 7))
    a = np.float32([0.42, 0.58, 0.78])[None, None, :]
    b = np.float32([0.62, 0.58, 0.80])[None, None, :]
    eff = (a * (1.0 - flip[..., None]) + b * flip[..., None]) * (0.62 + swell[..., None] * 0.42)
    eff = eff + fil[..., None] * np.float32([0.88, 0.95, 1.0]) * 0.45
    return np.clip(eff, 0, 1)

def _ign_chameleon_arctic_spec(h, w, s):
    # SAME filaments/flip/swell: M traces the visible icy threads white-hot (saffron-style
    # ignition), R flips gloss on the pale-violet lattice cells, Cc pools on the drift + halos.
    fil = _rk_sc(h, w, s ^ 1, 9500, 0.8, "streak", len_px=6)
    flip = flip_lattice((h, w), s ^ 2, 1.4, 0.5)
    swell = _rk_n(h, w, s ^ 3, (3, 7))
    M = 16.0 + np.clip(fil * 2.8, 0, 1) * 239.0
    R = np.clip(150.0 - flip * 95.0 + swell * 30.0, 15, 255)
    Cc = 24.0 + swell * 95.0 + cv2.GaussianBlur(fil, (0, 0), 2.2) * 130.0
    return M, R, Cc


# --- IGNITION: chameleon_aurora ---
def _ign_chameleon_aurora_paint(h, w, s):
    # Multi-angle curtain field ramped green->blue->violet; crest lines emit bright green.
    cur = _rk_gr(h, w, s ^ 1, 3, 4.4)
    crest = np.clip((cur - 0.70) * 4.5, 0, 1)
    thr = _rk_sc(h, w, s ^ 2, 5200, 0.9, "streak", len_px=6)
    lut = _rk_lut([(0.03, 0.32, 0.20), (0.08, 0.22, 0.55), (0.36, 0.12, 0.55)], 0.5)
    eff = _rk_ramp(np.clip(cur * 0.92, 0, 1), lut) * (0.55 + thr[..., None] * 0.30)
    eff = eff + crest[..., None] * np.float32([0.25, 0.95, 0.45]) * 0.55
    return np.clip(eff, 0, 1)

def _ign_chameleon_aurora_spec(h, w, s):
    # SAME curtains/crests/threads: Cc detonates on the exact bright crest lines, M sparkles
    # along the thread filaments, R turns the curtain bodies satin.
    cur = _rk_gr(h, w, s ^ 1, 3, 4.4)
    crest = np.clip((cur - 0.70) * 4.5, 0, 1)
    thr = _rk_sc(h, w, s ^ 2, 5200, 0.9, "streak", len_px=6)
    Cc = 26.0 + crest * 229.0
    M = 18.0 + thr * 165.0 + crest * 30.0
    R = np.clip(185.0 - cur * 125.0 - thr * 25.0, 15, 255)
    return M, R, Cc


# --- IGNITION: chameleon_copper ---
def _ign_chameleon_copper_paint(h, w, s):
    # Micro plate mosaic: 72% warm copper plates, 28% painted near-BLACK emerald (hidden side).
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 42))
    rng = np.random.default_rng(s ^ 2)
    m = (rng.random(int(lab.max()) + 1) > 0.72).astype(np.float32)[lab]
    dome = np.clip(1.0 - d1 / max(float(d1.max()), 1e-5) * 1.6, 0, 1)
    g = _rk_n(h, w, s ^ 3, (4, 9))
    copper = np.float32([0.66, 0.34, 0.13])[None, None, :] * (0.55 + g[..., None] * 0.45 + dome[..., None] * 0.20)
    emerald = np.float32([0.02, 0.09, 0.05])[None, None, :] * (0.80 + dome[..., None] * 0.50)
    eff = copper * (1.0 - m[..., None]) + emerald * m[..., None]
    return np.clip(eff * (1.0 - edge[..., None] * 0.45), 0, 1)

def _ign_chameleon_copper_spec(h, w, s):
    # SAME mosaic + SAME per-cell draw (s^2): M detonates exactly on the dark emerald plates,
    # R rides the grout corridors, Cc rides the plate-center wet domes.
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 42))
    rng = np.random.default_rng(s ^ 2)
    m = (rng.random(int(lab.max()) + 1) > 0.72).astype(np.float32)[lab]
    dome = np.clip(1.0 - d1 / max(float(d1.max()), 1e-5) * 1.6, 0, 1)
    M = 16.0 + m * (1.0 - edge) * 239.0
    R = np.clip(85.0 + edge * 105.0 - m * 45.0, 15, 255)
    Cc = 26.0 + dome * 150.0 * (1.0 - edge * 0.5)
    return M, R, Cc


# --- IGNITION: chameleon_emerald ---
def _ign_chameleon_emerald_paint(h, w, s):
    # Deep emerald woven body; ~24% lattice cells painted DIM antique bronze (hidden gold).
    wv = _rk_gr(h, w, s ^ 1, 4, 3.0)
    flip = flip_lattice((h, w), s ^ 2, 1.1, 0.24)
    band = (wv > 0.55).astype(np.float32)
    g = _rk_n(h, w, s ^ 3, (3, 7))
    emerald = np.float32([0.03, 0.34, 0.16])[None, None, :] * (0.50 + wv[..., None] * 0.45 + g[..., None] * 0.25)
    gold = np.float32([0.16, 0.11, 0.03])[None, None, :] * (0.90 + band[..., None] * 0.40)
    eff = emerald * (1.0 - flip[..., None]) + gold * flip[..., None]
    return np.clip(eff, 0, 1)

def _ign_chameleon_emerald_spec(h, w, s):
    # SAME weave/lattice/grain: M detonates on the dim gold cells only where the weave band
    # crosses them (gold flashes woven), R alternates satin/matte on the bands, Cc pools.
    wv = _rk_gr(h, w, s ^ 1, 4, 3.0)
    flip = flip_lattice((h, w), s ^ 2, 1.1, 0.24)
    band = (wv > 0.55).astype(np.float32)
    g = _rk_n(h, w, s ^ 3, (3, 7))
    M = 14.0 + np.clip(flip * 1.3, 0, 1) * 241.0 * (0.70 + band * 0.30)
    R = np.clip(60.0 + band * 105.0 + g * 30.0 - flip * 25.0, 15, 255)
    Cc = 24.0 + g * 110.0 + np.clip((wv - 0.72) * 4.0, 0, 1) * 110.0
    return M, R, Cc


# --- IGNITION: chameleon_fire ---
def _ign_chameleon_fire_paint(h, w, s):
    # 8000 micro flame petals ramp crimson->orange; petal cores tipped molten gold; ember dust.
    tongues = _rk_sc(h, w, s ^ 1, 8000, 4.5, "petal", amp=(0.6, 1.0))
    sil = np.clip(tongues * 2.4, 0, 1)
    tips = np.clip((tongues - 0.45) * 2.5, 0, 1)
    embers = _rk_sc(h, w, s ^ 2, 3200, 0.7, "dot")
    g = _rk_n(h, w, s ^ 3, (4, 9))
    lut = _rk_lut([(0.30, 0.02, 0.03), (0.78, 0.16, 0.03), (0.98, 0.55, 0.08)], 0.5)
    eff = _rk_ramp(np.clip(sil * 0.85 + embers * 0.25, 0, 1), lut) * (0.75 + g[..., None] * 0.35)
    eff = eff + tips[..., None] * np.float32([1.00, 0.85, 0.35]) * 0.55
    return np.clip(eff, 0, 1)

def _ign_chameleon_fire_spec(h, w, s):
    # SAME petals/tips/embers/grain: Cc detonates on the exact flame bodies the paint ramps
    # (tips hottest), M sparkles on the ember dust, R rides the smoke pools between flames.
    tongues = _rk_sc(h, w, s ^ 1, 8000, 4.5, "petal", amp=(0.6, 1.0))
    sil = np.clip(tongues * 2.4, 0, 1)
    tips = np.clip((tongues - 0.45) * 2.5, 0, 1)
    embers = _rk_sc(h, w, s ^ 2, 3200, 0.7, "dot")
    g = _rk_n(h, w, s ^ 3, (4, 9))
    Cc = 24.0 + np.clip(tongues * 4.6, 0, 1) * 231.0
    M = 16.0 + embers * 180.0 + tips * 50.0
    R = np.clip(75.0 + g * 120.0 - sil * 55.0, 15, 255)
    return M, R, Cc


# --- IGNITION: chameleon_frost ---
def _ign_chameleon_frost_paint(h, w, s):
    # Polar blue-white body; frost-fern filaments painted as QUIET steel-blue veins.
    fern = _rk_web(h, w, s ^ 1, 6000, k=2, intensity=(0.45, 1.0))
    g = _rk_n(h, w, s ^ 2, (3, 6))
    swell = _rk_n(h, w, s ^ 3, (5, 11))
    body = np.float32([0.70, 0.76, 0.86])[None, None, :] * (0.66 + g[..., None] * 0.20 + swell[..., None] * 0.08)
    vein = np.float32([0.16, 0.24, 0.38])[None, None, :]
    eff = body * (1.0 - fern[..., None] * 0.78) + vein * fern[..., None] * 0.78
    return np.clip(eff, 0, 1)

def _ign_chameleon_frost_spec(h, w, s):
    # SAME ferns/grain/swell: M detonates silver on the exact quiet vein filaments,
    # R rides the frost-pool grain, Cc rides the macro drift with a faint fern halo.
    fern = _rk_web(h, w, s ^ 1, 6000, k=2, intensity=(0.45, 1.0))
    g = _rk_n(h, w, s ^ 2, (3, 6))
    swell = _rk_n(h, w, s ^ 3, (5, 11))
    M = 12.0 + np.clip(fern * 1.7, 0, 1) * 243.0
    R = np.clip(60.0 + g * 130.0 - fern * 30.0, 15, 255)
    Cc = 22.0 + swell * 120.0 + cv2.GaussianBlur(fern, (0, 0), 2.6) * 60.0
    return M, R, Cc


# --- IGNITION: chameleon_galaxy ---
def _ign_chameleon_galaxy_paint(h, w, s):
    # Violet/dark-cyan flip nebula breathing with gas swirl; 5200 micro stars as pinpoints.
    stars = _rk_sc(h, w, s ^ 1, 5200, 1.0, "dot")
    flip = flip_lattice((h, w), s ^ 2, 1.3, 0.24)
    gas = _rk_n(h, w, s ^ 3, (5, 11))
    swell = _rk_n(h, w, s ^ 4, (2, 4))
    violet = np.float32([0.23, 0.085, 0.44])[None, None, :]
    cyan = np.float32([0.015, 0.075, 0.12])[None, None, :]
    eff = (violet * (1.0 - flip[..., None]) + cyan * flip[..., None]) * (0.60 + gas[..., None] * 0.60)
    eff = eff * (0.85 + swell[..., None] * 0.30) + stars[..., None] * np.float32([0.80, 0.88, 1.0]) * 0.85
    return np.clip(eff, 0, 1)

def _ign_chameleon_galaxy_spec(h, w, s):
    # SAME stars/lattice/gas: M detonates on the dark cyan nebula cells AND the star
    # pinpoints together, R rides the gas swirl, Cc blooms on the star halos.
    stars = _rk_sc(h, w, s ^ 1, 5200, 1.0, "dot")
    flip = flip_lattice((h, w), s ^ 2, 1.3, 0.24)
    gas = _rk_n(h, w, s ^ 3, (5, 11))
    swell = _rk_n(h, w, s ^ 4, (2, 4))
    M = 12.0 + np.clip(flip * 1.3, 0, 1) * 243.0
    R = np.clip(180.0 - gas * 125.0, 15, 255)
    Cc = 22.0 + cv2.GaussianBlur(stars, (0, 0), 2.4) * 150.0 + swell * 85.0
    return M, R, Cc


# --- IGNITION: chameleon_midnight ---
def _ign_chameleon_midnight_paint(h, w, s):
    gr = _rk_gr(h, w, s ^ 1, 3, 3.4)                                   # brushed night grain (SHARED with spec)
    glint = _rk_sc(h, w, s ^ 2, 11000, 1.8, 'dot', amp=(0.7, 1.0))     # glint constellation (SHARED)
    gw = np.clip(glint * 1.7 + cv2.GaussianBlur(glint, (0, 0), 1.5) * 0.8, 0, 1)
    base = _rk_ramp(gr, _rk_lut([(0.035, 0.045, 0.09), (0.09, 0.11, 0.20)], 0.45))
    return np.clip(base + gw[..., None] * np.float32([0.10, 0.22, 0.60]) * 0.30, 0, 1).astype(np.float32)

def _ign_chameleon_midnight_spec(h, w, s):
    gr = _rk_gr(h, w, s ^ 1, 3, 3.4)                                   # SAME brushing field
    glint = _rk_sc(h, w, s ^ 2, 11000, 1.8, 'dot', amp=(0.7, 1.0))     # SAME constellation
    gw = np.clip(glint * 1.7 + cv2.GaussianBlur(glint, (0, 0), 1.5) * 0.8, 0, 1)
    halo = np.clip(cv2.GaussianBlur(glint, (0, 0), 5.0) * 3.2 - gw * 1.2, 0, 1)
    M = 10 + gw * 245                                                  # IGNITION: the buried blue glints detonate
    R = np.clip(58 + gr * 150, 15, 255)
    Cc = np.clip(20 + _rk_n(h, w, s ^ 3, (18, 40)) * 140 + halo * 45, 16, 255)
    return M, R, Cc

# --- IGNITION: chameleon_neon ---
def _ign_chameleon_neon_paint(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 1.1, 0.32)                      # green flake clan, 32% (SHARED)
    gr = _rk_gr(h, w, s ^ 2, 3, 3.2)                                   # micro grain (SHARED)
    seam = np.clip(1.0 - np.abs(cv2.GaussianBlur(flip, (0, 0), 1.2) * 2.0 - 1.0), 0, 1)
    mag = _rk_ramp(np.clip(0.25 + gr * 0.6, 0, 1), _rk_lut([(0.42, 0.02, 0.28), (0.96, 0.10, 0.62)], 0.5))
    grn = _rk_ramp(np.clip(gr * 0.5, 0, 1), _rk_lut([(0.012, 0.09, 0.035), (0.10, 0.42, 0.11)], 0.5))
    f3 = flip[..., None]
    return np.clip((mag * (1 - f3) + grn * f3) * (1 - seam[..., None] * 0.30), 0, 1).astype(np.float32)

def _ign_chameleon_neon_spec(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 1.1, 0.32)                      # SAME clan mask as the paint
    gr = _rk_gr(h, w, s ^ 2, 3, 3.2)
    seam = np.clip(1.0 - np.abs(cv2.GaussianBlur(flip, (0, 0), 1.2) * 2.0 - 1.0), 0, 1)
    pool = (0.5 + 0.5 * np.sin(cv2.GaussianBlur(flip, (0, 0), 9.0) * 13.0 + _rk_n(h, w, s ^ 3, (2, 5)) * 5.0)) ** 2
    M = 16 + flip * 236                                                # IGNITION: dark green clan -> electric flare
    R = np.clip(66 + seam * 120 + (gr - 0.5) * 84 - flip * 26, 15, 255)
    Cc = np.clip(22 + pool * 150 + seam * 42, 16, 255)
    return M, R, Cc

# --- IGNITION: chameleon_obsidian ---
def _ign_chameleon_obsidian_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1000, (h * w) // 44))     # glass-plate mosaic (SHARED)
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    tilt = np.random.default_rng(s ^ 2).random(int(lab.max()) + 1).astype(np.float32)[lab]  # per-plate tilt (SHARED draw)
    rim = edge ** 2.0                                                  # hot core of every seam (SHARED)
    glass = _rk_ramp(np.clip(0.12 + tilt * 0.30 + (1 - d1n) * 0.22, 0, 1),
                     _rk_lut([(0.030, 0.030, 0.045), (0.115, 0.115, 0.155)], 0.4))
    bronze = np.float32([0.50, 0.30, 0.10])[None, None, :]
    return np.clip(glass * (1 - edge[..., None] * 0.45) + bronze * rim[..., None] * 0.55, 0, 1).astype(np.float32)

def _ign_chameleon_obsidian_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1000, (h * w) // 44))     # SAME plates
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    tilt = np.random.default_rng(s ^ 2).random(int(lab.max()) + 1).astype(np.float32)[lab]  # SAME tilt draw
    rim = edge ** 2.0
    M = 12 + rim * 243                                                 # IGNITION: the bronze rims blaze molten
    R = np.clip(52 + tilt * 156 - edge * 38, 15, 255)
    Cc = np.clip(20 + ((1 - d1n) ** 2) * 128 + _rk_n(h, w, s ^ 3, (24, 56)) * 36, 16, 255)
    return M, R, Cc

# --- IGNITION: chameleon_ocean ---
def _ign_chameleon_ocean_paint(h, w, s):
    swell = _rk_gr(h, w, s ^ 1, 3, 3.8)                                # rolling swell field (SHARED)
    crest = np.clip((swell - 0.70) / 0.16, 0, 1)                       # breaking-crest corridors (SHARED)
    spray = _rk_sc(h, w, s ^ 2, 8000, 1.2, 'dot', amp=(0.6, 1.0)) * np.clip(swell * 1.5 - 0.45, 0, 1)
    lut = _rk_lut([(0.015, 0.06, 0.28), (0.02, 0.20, 0.38), (0.05, 0.46, 0.50)], 0.5)
    eff = _rk_ramp(np.clip(swell * 0.8 + crest * 0.2, 0, 1), lut)
    return np.clip(eff + spray[..., None] * np.float32([0.55, 0.85, 0.90]) * 0.40, 0, 1).astype(np.float32)

def _ign_chameleon_ocean_spec(h, w, s):
    swell = _rk_gr(h, w, s ^ 1, 3, 3.8)                                # SAME swell
    crest = np.clip((swell - 0.70) / 0.16, 0, 1)                       # SAME crest corridors the paint turns teal
    spray = _rk_sc(h, w, s ^ 2, 8000, 1.2, 'dot', amp=(0.6, 1.0)) * np.clip(swell * 1.5 - 0.45, 0, 1)
    Cc = np.clip(20 + crest * 235, 16, 255)                            # IGNITION: wet crest lines flash
    M = np.clip(14 + spray * 205 + crest * 30, 0, 255)
    R = np.clip(64 + _rk_n(h, w, s ^ 3, (26, 60)) * (84 + (1 - crest) * 78), 15, 255)
    return M, R, Cc

# --- IGNITION: chameleon_phoenix ---
def _ign_chameleon_phoenix_paint(h, w, s):
    A = _rk_sc(h, w, s ^ 1, 7000, 2.2, 'petal')                        # ember feather clan (SHARED)
    B = _rk_sc(h, w, s ^ 2, 7000, 2.4, 'petal')                        # hidden magenta clan (SHARED)
    Bw = np.clip(B * 1.5 + cv2.GaussianBlur(B, (0, 0), 2.5) * 1.8, 0, 1)
    gr = _rk_n(h, w, s ^ 3, (4, 9))
    ember = _rk_ramp(np.clip(0.18 + A * 0.62 + gr * 0.25, 0, 1),
                     _rk_lut([(0.34, 0.05, 0.03), (0.88, 0.34, 0.05), (1.0, 0.78, 0.25)], 0.5))
    maroon = np.float32([0.17, 0.02, 0.12])[None, None, :] * (0.7 + gr[..., None] * 0.5)
    b3 = Bw[..., None]
    return np.clip(ember * (1 - b3 * 0.85) + maroon * b3, 0, 1).astype(np.float32)

def _ign_chameleon_phoenix_spec(h, w, s):
    A = _rk_sc(h, w, s ^ 1, 7000, 2.2, 'petal')                        # SAME feather clans
    B = _rk_sc(h, w, s ^ 2, 7000, 2.4, 'petal')
    Bw = np.clip(B * 1.5 + cv2.GaussianBlur(B, (0, 0), 2.5) * 1.8, 0, 1)
    gr = _rk_n(h, w, s ^ 3, (4, 9))
    M = 14 + Bw * 240                                                  # IGNITION: dark feathers flare magenta
    R = np.clip(160 - (A + Bw) * 96 + (gr - 0.5) * 72, 15, 255)
    Cc = np.clip(20 + np.clip(cv2.GaussianBlur(A, (0, 0), 3.0) * 2.4, 0, 1) * 155, 16, 255)
    return M, R, Cc

# --- IGNITION: chameleon_venom ---
def _ign_chameleon_venom_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1100, (h * w) // 34))     # snake-scale mosaic (SHARED)
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    clan = np.random.default_rng(s ^ 2).random(int(lab.max()) + 1).astype(np.float32)[lab]
    mB = (clan > 0.68).astype(np.float32)                              # hidden violet clan (SHARED draw)
    dome = (1 - d1n) ** 2
    grn = _rk_ramp(np.clip(0.25 + dome * 0.55 + _rk_n(h, w, s ^ 3, (5, 11)) * 0.2, 0, 1),
                   _rk_lut([(0.06, 0.28, 0.03), (0.25, 0.72, 0.08)], 0.5))
    vio = np.float32([0.11, 0.025, 0.17])[None, None, :] * (0.65 + dome[..., None] * 0.55)
    m3 = mB[..., None]
    return np.clip((grn * (1 - m3) + vio * m3) * (1 - edge[..., None] * 0.72), 0, 1).astype(np.float32)

def _ign_chameleon_venom_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1100, (h * w) // 34))     # SAME mosaic
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    clan = np.random.default_rng(s ^ 2).random(int(lab.max()) + 1).astype(np.float32)[lab]  # SAME clan draw
    mB = (clan > 0.68).astype(np.float32)
    dome = (1 - d1n) ** 2
    M = 13 + mB * (1 - edge) * 242                                     # IGNITION: violet scales mirror-flip
    R = np.clip(64 + edge * 132 + (_rk_n(h, w, s ^ 4, (22, 50)) - 0.5) * 64, 15, 255)
    Cc = np.clip(18 + (1 - mB) * dome * 165, 16, 255)                  # green-clan venom-bead domes glow wet
    return M, R, Cc

# --- IGNITION: mystichrome ---
def _ign_mystichrome_paint(h, w, s):
    m0, m1, m2 = tri_partition((h, w), s ^ 1, cells=max(2600, (h * w) // 16), soften_px=1.0)  # SHARED territories
    gr = _rk_n(h, w, s ^ 2, (3, 7))
    cob = _rk_ramp(np.clip(0.25 + gr * 0.55, 0, 1), _rk_lut([(0.05, 0.13, 0.38), (0.17, 0.33, 0.78)], 0.5))
    vio = np.float32([0.075, 0.02, 0.13])[None, None, :] * (0.7 + gr[..., None] * 0.5)  # DEEP violet: the hidden phase
    eme = _rk_ramp(np.clip(0.20 + gr * 0.5, 0, 1), _rk_lut([(0.015, 0.16, 0.09), (0.05, 0.38, 0.22)], 0.5))
    return np.clip(cob * m0[..., None] + vio * m1[..., None] + eme * m2[..., None], 0, 1).astype(np.float32)

def _ign_mystichrome_spec(h, w, s):
    m0, m1, m2 = tri_partition((h, w), s ^ 1, cells=max(2600, (h * w) // 16), soften_px=1.0)  # SAME territories
    gr = _rk_n(h, w, s ^ 2, (3, 7))
    seam = np.clip((0.75 - np.maximum(np.maximum(m0, m1), m2)) * 4.0, 0, 1)
    M = 12 + m1 * 240                                                  # IGNITION: the buried violet third detonates
    R = np.clip(52 + m0 * (58 + gr * 112) + seam * 46, 15, 255)
    Cc = np.clip(18 + m2 * (90 + _rk_n(h, w, s ^ 3, (12, 28)) * 88), 16, 255)
    return M, R, Cc

# --- IGNITION: beetle_jewel ---
def _ign_beetle_jewel_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 40))
    tc = np.random.default_rng(s ^ 2).random(int(lab.max()) + 1).astype(np.float32)[lab]
    mirror = (tc > 0.78).astype(np.float32)
    jewel = _rk_ramp(np.clip(tc / 0.78, 0, 1), _rk_lut([(0.05, 0.45, 0.22), (0.55, 0.10, 0.45), (0.08, 0.30, 0.50)], 0.5))
    dark = np.float32([0.030, 0.048, 0.034])[None, None, :] * (0.7 + tc[..., None] * 0.5)
    d1n = np.clip(d1 / max(float(d1.max()), 1e-5), 0, 1)
    eff = (jewel * (1 - mirror[..., None]) + dark * mirror[..., None]) * (1 - edge[..., None] * 0.72)
    return np.clip(eff + interference_palette(d1n, 2.5, 0.7)[..., :3] * edge[..., None] * 0.30, 0, 1).astype(np.float32)

def _ign_beetle_jewel_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 40))
    tc = np.random.default_rng(s ^ 2).random(int(lab.max()) + 1).astype(np.float32)[lab]
    mirror = (tc > 0.78).astype(np.float32)
    d1n = np.clip(d1 / max(float(d1.max()), 1e-5), 0, 1)
    M = 14 + mirror * (1 - edge) * 241
    R = np.clip(96 + d1n * 118 - edge * 58 + (tc - 0.5) * 26, 15, 255)
    Cc = np.clip(26 + edge * 162 + d1n * 30, 0, 255)
    return M, R, Cc


# --- IGNITION: beetle_rainbow ---
def _ign_beetle_rainbow_paint(h, w, s):
    rings = _rk_rings(h, w, s ^ 1, 7400, 3.0, 1.4)
    th = np.clip(cv2.GaussianBlur(rings, (0, 0), 0.8) * 1.5 + _rk_n(h, w, s ^ 2, (3, 7)) * 0.45, 0, 1)
    film = interference_palette(th, 3.0, 0.75, base_srgb=np.float32([0.30, 0.28, 0.30]))[..., :3]
    chitin = np.float32([0.075, 0.065, 0.090])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 2, (3, 7))[..., None] * 0.6)
    crest = np.clip(rings * 5.0, 0, 1)[..., None]
    return np.clip(chitin * (1 - crest) + film * crest, 0, 1).astype(np.float32)

def _ign_beetle_rainbow_spec(h, w, s):
    rings = _rk_rings(h, w, s ^ 1, 7400, 3.0, 1.4)
    th = np.clip(cv2.GaussianBlur(rings, (0, 0), 0.8) * 1.5 + _rk_n(h, w, s ^ 2, (3, 7)) * 0.45, 0, 1)
    crest = np.clip(rings * 5.0, 0, 1)
    halo = cv2.GaussianBlur(rings, (0, 0), 3.0)
    M = 18 + crest * 234
    R = np.clip(186 - _rk_gr(h, w, s ^ 4, 3, 3.4) * 152 - _rk_n(h, w, s ^ 3, (5, 11)) * 25, 15, 255)
    Cc = np.clip(34 + (np.floor(_rk_n(h, w, s ^ 5, (13, 29)) * 3.0) % 2) * 128 + crest * 30, 0, 255)
    return M, R, Cc


# --- IGNITION: butterfly_morpho ---
def _ign_butterfly_morpho_paint(h, w, s):
    rows = _rk_gr(h, w, s ^ 1, 4, 3.2)
    dk = (flip_lattice((h, w), s ^ 2, 1.3, 0.75) < 0.5).astype(np.float32)
    blue = _rk_ramp(np.clip(rows, 0, 1), _rk_lut([(0.02, 0.10, 0.45), (0.10, 0.45, 0.95)], 0.55))
    dark = np.float32([0.045, 0.030, 0.10])[None, None, :] * (0.6 + rows[..., None] * 0.5)
    return np.clip(blue * (1 - dk[..., None]) + dark * dk[..., None], 0, 1).astype(np.float32)

def _ign_butterfly_morpho_spec(h, w, s):
    rows = _rk_gr(h, w, s ^ 1, 4, 3.2)
    dk = (flip_lattice((h, w), s ^ 2, 1.3, 0.75) < 0.5).astype(np.float32)
    M = 12 + dk * 243
    R = np.clip(58 + rows * 152, 15, 255)
    pool = cv2.GaussianBlur(_rk_n(h, w, s ^ 5, (11, 25)), (0, 0), 4.0)
    pool = (pool - pool.min()) / max(float(pool.max() - pool.min()), 1e-5)
    Cc = np.clip(30 + pool * 175, 0, 255)
    return M, R, Cc


# --- IGNITION: butterfly_monarch ---
def _ign_butterfly_monarch_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 110))
    veins = _rk_web(h, w, s ^ 2, 1000, k=2)
    dots = _rk_sc(h, w, s ^ 3, 1800, 1.3, "dot")
    d1n = np.clip(d1 / max(float(d1.max()), 1e-5), 0, 1)
    deep = (np.random.default_rng(s ^ 4).random(int(lab.max()) + 1) > 0.72).astype(np.float32)[lab]
    amber = candy_absorb(np.full((h, w, 3), 0.88, np.float32), np.float32([0.85, 0.45, 0.10]), 0.45 + d1n * 1.05 + deep * 1.9)
    eff = amber * (1 - veins[..., None] * 0.92) * (1 - edge[..., None] * 0.45)
    return np.clip(eff + dots[..., None] * np.float32([0.95, 0.93, 0.88]) * 0.85, 0, 1).astype(np.float32)

def _ign_butterfly_monarch_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(700, (h * w) // 110))
    veins = _rk_web(h, w, s ^ 2, 1000, k=2)
    dots = _rk_sc(h, w, s ^ 3, 1800, 1.3, "dot")
    d1n = np.clip(d1 / max(float(d1.max()), 1e-5), 0, 1)
    deep = (np.random.default_rng(s ^ 4).random(int(lab.max()) + 1) > 0.72).astype(np.float32)[lab]
    M = 16 + deep * (1 - veins) * (1 - edge * 0.8) * 236
    R = np.clip(172 - d1n * 118 + veins * 68, 15, 255)
    Cc = np.clip(28 + dots * 195 + cv2.GaussianBlur(dots, (0, 0), 2.2) * 60, 0, 255)
    return M, R, Cc


# --- IGNITION: dragonfly_wing ---
def _ign_dragonfly_wing_paint(h, w, s):
    veins = _rk_web(h, w, s ^ 1, 7000, k=2)
    filmth = _rk_n(h, w, s ^ 2, (7, 16))
    film = interference_palette(filmth, 2.0, 0.5, base_srgb=np.float32([0.55, 0.58, 0.62]))[..., :3]
    vmask = np.clip(veins * 2.0, 0, 1)[..., None]
    return np.clip(film * 0.55 * (1 - vmask) + vmask * np.float32([0.07, 0.07, 0.09]), 0, 1).astype(np.float32)

def _ign_dragonfly_wing_spec(h, w, s):
    veins = _rk_web(h, w, s ^ 1, 7000, k=2)
    filmth = _rk_n(h, w, s ^ 2, (7, 16))
    vmask = np.clip(veins * 2.0, 0, 1)
    M = 14 + vmask * 239
    R = np.clip(186 - filmth * 148 + vmask * 36, 15, 255)
    Cc = np.clip(32 + (np.floor(filmth * 2.0) % 2) * 146 + cv2.GaussianBlur(vmask, (0, 0), 2.5) * 52, 0, 255)
    return M, R, Cc


# --- IGNITION: scarab_gold ---
def _ign_scarab_gold_fields(h, w, s):
    glit = _rk_sc(h, w, s ^ 1, 5600, 1.2, "dot")                      # gold micro-glitter dimples
    sacred = np.clip(_rk_sc(h, w, s ^ 2, 3300, 3.8, "dot", amp=(0.8, 1.0)) * 1.7, 0, 1)  # hidden pits
    halo = cv2.GaussianBlur(sacred, (0, 0), 6.0)
    halo = halo / max(float(halo.max()), 1e-5)
    brush = _rk_gr(h, w, s ^ 3, 3, 3.2)                               # polished gold flow grain
    return glit, sacred, halo, brush


def _ign_scarab_gold_paint(h, w, s):
    glit, sacred, halo, brush = _ign_scarab_gold_fields(h, w, s)
    gold = _rk_ramp(np.clip(brush * 0.55 + _rk_n(h, w, s ^ 4, (4, 10)) * 0.45 + glit * 0.25, 0, 1),
                    _rk_lut([(0.45, 0.30, 0.06), (0.72, 0.55, 0.14), (0.97, 0.84, 0.34)], 0.45))
    pit = np.float32([0.03, 0.09, 0.045])[None, None, :]              # dark sacred-green pit
    eff = gold * (1 - sacred[..., None] * 0.92) + pit * sacred[..., None]
    eff = eff * (1 - halo[..., None] * 0.10) + halo[..., None] * np.float32([0.05, 0.16, 0.06]) * 0.22
    return np.clip(eff, 0, 1).astype(np.float32)


def _ign_scarab_gold_spec(h, w, s):
    glit, sacred, halo, brush = _ign_scarab_gold_fields(h, w, s)
    M = 30 + glit * 70 + sacred * 224                                 # IGNITION: same dark pits -> ~254 mirror
    R = np.clip(168 - brush * 122 + sacred * 30 - halo * 20, 15, 255)
    Cc = np.clip(24 + halo * 148 + glit * 44, 0, 255)
    return M, R, Cc


# --- IGNITION: moth_luna ---
def _ign_moth_luna_fields(h, w, s):
    fur = _rk_sc(h, w, s ^ 1, 5800, 0.9, "streak", len_px=3.5)        # pale scale-fur
    moon = np.clip(_rk_sc(h, w, s ^ 2, 3200, 4.2, "dot", amp=(0.8, 1.0)) * 1.55, 0, 1)  # moon-coins
    dust = _rk_n(h, w, s ^ 3, (4, 10))                                # drifting wing dust
    return fur, moon, dust


def _ign_moth_luna_paint(h, w, s):
    fur, moon, dust = _ign_moth_luna_fields(h, w, s)
    pale = _rk_ramp(np.clip(fur * 0.55 + dust * 0.5, 0, 1),
                    _rk_lut([(0.52, 0.70, 0.52), (0.72, 0.88, 0.70), (0.88, 0.97, 0.82)], 0.6))
    coin = np.float32([0.42, 0.50, 0.55])[None, None, :]              # dusky silver-blue coin, quiet
    mix = (moon * 0.62)[..., None]
    return np.clip(pale * (1 - mix) + coin * mix, 0, 1).astype(np.float32)


def _ign_moth_luna_spec(h, w, s):
    fur, moon, dust = _ign_moth_luna_fields(h, w, s)
    M = np.clip(26 + fur * 112 + moon * 22, 0, 255)
    R = np.clip(178 - dust * 128 + fur * 26 - moon * 30, 15, 255)
    Cc = np.clip(22 + moon * 233 + cv2.GaussianBlur(moon, (0, 0), 3.0) * 38, 0, 255)  # IGNITION
    return M, R, Cc


# --- IGNITION: beetle_stag ---
def _ign_beetle_stag_fields(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 38))
    d1n = np.clip(d1 / max(float(d1.max()), 1e-5), 0, 1)
    rng = np.random.default_rng((s ^ 2) & 0x7FFFFFFF)
    sel = (rng.random(int(lab.max()) + 1) < 0.18).astype(np.float32)[lab]
    ember = sel * (1 - edge) * np.clip(1 - d1n * 1.4, 0, 1)           # molten interiors of chosen cells
    seam = np.clip(edge * 1.25, 0, 1)                                 # bronze rim-light seams
    return seam, ember, d1n


def _ign_beetle_stag_paint(h, w, s):
    seam, ember, d1n = _ign_beetle_stag_fields(h, w, s)
    breath = _rk_n(h, w, s ^ 3, (4, 10))
    base = np.float32([0.055, 0.05, 0.05])[None, None, :] * (0.7 + breath[..., None] * 0.6)
    bronze = seam[..., None] * np.float32([0.58, 0.36, 0.14]) * 0.85  # seam light the spec will trace
    glow = ember[..., None] * np.float32([0.30, 0.13, 0.04]) * 0.5    # quiet ember flush
    return np.clip(base * (1 + d1n[..., None] * 0.35) + bronze + glow, 0, 1).astype(np.float32)


def _ign_beetle_stag_spec(h, w, s):
    seam, ember, d1n = _ign_beetle_stag_fields(h, w, s)
    M = 12 + (seam * seam) * 242                                      # IGNITION: same seams, sharp core, mirror
    R = np.clip(196 - d1n * 96 - ember * 60 + _rk_n(h, w, s ^ 4, (3, 8)) * 26, 15, 255)
    Cc = np.clip(26 + ember * 172 + seam * 30, 0, 255)
    return M, R, Cc


# --- IGNITION: wasp_warning ---
def _ign_wasp_warning_fields(h, w, s):
    a = _rk_sc(h, w, s ^ 1, 2000, 1.2, "streak", len_px=5)            # amber chevron strokes
    b = _rk_sc(h, w, s ^ 2, 2000, 1.2, "streak", len_px=5)            # black counter strokes
    zone = np.clip(cv2.GaussianBlur(a - b, (0, 0), 0.6) * 14 + 0.5 + (_rk_n(h, w, s ^ 3, (3, 7)) - 0.5) * 0.6, 0, 1)
    sting = np.clip(_rk_sc(h, w, s ^ 4, 2400, 5.5, "streak", len_px=11, amp=(0.85, 1.0)) * 2.0, 0, 1)
    return a, b, zone, sting


def _ign_wasp_warning_paint(h, w, s):
    a, b, zone, sting = _ign_wasp_warning_fields(h, w, s)
    amber = np.float32([0.92, 0.62, 0.07])[None, None, :]
    blk = np.float32([0.075, 0.065, 0.055])[None, None, :]
    eff = amber * zone[..., None] + blk * (1 - zone[..., None]) + a[..., None] * 0.14
    ink = np.float32([0.02, 0.02, 0.03])[None, None, :]               # wet jet-black sting needles
    return np.clip(eff * (1 - sting[..., None] * 0.88) + ink * sting[..., None], 0, 1).astype(np.float32)


def _ign_wasp_warning_spec(h, w, s):
    a, b, zone, sting = _ign_wasp_warning_fields(h, w, s)
    M = np.clip(18 + sting * 237, 0, 255)                             # IGNITION: black needles -> full mirror
    R = np.clip(186 - zone * 116 + (b - 0.5) * 34, 15, 255)
    Cc = np.clip(24 + cv2.GaussianBlur(np.maximum(a, b), (0, 0), 2.2) * 168, 0, 255)
    return M, R, Cc


# --- IGNITION: firefly_glow ---
def _ign_firefly_glow_fields(h, w, s):
    flies = np.clip(_rk_sc(h, w, s ^ 1, 5200, 3.4, "dot", amp=(0.7, 1.0)) * 1.55, 0, 1)
    swarm = cv2.GaussianBlur(flies, (0, 0), 9.0)
    swarm = swarm / max(float(swarm.max()), 1e-5)
    breath = _rk_n(h, w, s ^ 2, (3, 7))                               # night-air haze
    return flies, swarm, breath


def _ign_firefly_glow_paint(h, w, s):
    flies, swarm, breath = _ign_firefly_glow_fields(h, w, s)
    base = np.float32([0.055, 0.10, 0.065])[None, None, :] * (0.75 + breath[..., None] * 0.65)
    moss = np.float32([0.16, 0.30, 0.07])[None, None, :]              # faint warm-green pinpricks
    eff = base * (1 + swarm[..., None] * 0.30) + moss * flies[..., None] * 0.32
    return np.clip(eff, 0, 1).astype(np.float32)


def _ign_firefly_glow_spec(h, w, s):
    flies, swarm, breath = _ign_firefly_glow_fields(h, w, s)
    M = np.clip(16 + swarm * 92 + flies * 26, 0, 255)
    R = np.clip(198 - breath * 124 - swarm * 36, 15, 255)
    Cc = np.clip(22 + flies * 233 + cv2.GaussianBlur(flies, (0, 0), 2.6) * 44, 0, 255)  # IGNITION
    return M, R, Cc


# --- IGNITION: neon_pink_blaze ---
def _ign_neon_pink_blaze_paint(h, w, s):
    web = _rk_web(h, w, s ^ 1, 7000, k=2)                                   # neon tube web
    wcore = np.clip(web * 1.6, 0, 1)                                        # blazing tube cores — M ignites THESE
    halo = cv2.GaussianBlur(web, (0, 0), 2.2)                               # glow aspect of the SAME web
    felt = _rk_n(h, w, s ^ 2, (6, 14))                                      # charcoal felt
    base = np.float32([0.085, 0.07, 0.10])[None, None, :] * (0.7 + felt[..., None] * 0.6)
    pink = wcore[..., None] * np.float32([1.0, 0.16, 0.52]) * 0.80
    glow = np.clip(halo - web * 0.8, 0, 1)[..., None] * np.float32([0.85, 0.15, 0.48]) * 0.30
    return np.clip(base + pink + glow, 0, 1).astype(np.float32)


def _ign_neon_pink_blaze_spec(h, w, s):
    web = _rk_web(h, w, s ^ 1, 7000, k=2)                                   # SAME web as paint
    wcore = np.clip(web * 1.6, 0, 1)                                        # SAME tube cores
    halo = cv2.GaussianBlur(web, (0, 0), 2.2)                               # SAME glow
    felt = _rk_n(h, w, s ^ 2, (6, 14))                                      # SAME felt
    ring = np.clip(halo * 1.7 - web * 1.5, 0, 1)                            # halo-minus-core aspect
    M = 20 + wcore * 235                                                    # IGNITION: pink tubes flash white-hot
    R = np.clip(168 - felt * 95 - halo * 50, 15, 255)                       # felt mottle, silked along the glow
    Cc = 30 + ring * 150 + felt * 45                                        # wet halo corridors hug the tubes
    return M, R, Cc

# --- IGNITION: neon_toxic_green ---
def _ign_neon_toxic_green_paint(h, w, s):
    rings = _rk_rings(h, w, s ^ 1, 9000, 3.0, 2.0)                          # bubbling micro ring crests
    glow = cv2.GaussianBlur(rings, (0, 0), 1.4)                             # bubble-body luminescence
    lum = np.clip(rings * 1.7 + glow * 3.9, 0, 1)                           # acid-bright subset — Cc ignites THIS
    steel = _rk_n(h, w, s ^ 2, (5, 12))
    base = np.float32([0.05, 0.075, 0.06])[None, None, :] * (0.7 + steel[..., None] * 0.6)
    acid = lum[..., None] * np.float32([0.42, 0.95, 0.10]) * 0.78
    fil = rings[..., None] * np.float32([0.20, 0.55, 0.06]) * 0.30          # crisp crest filigree
    return np.clip(base + acid + fil, 0, 1).astype(np.float32)


def _ign_neon_toxic_green_spec(h, w, s):
    rings = _rk_rings(h, w, s ^ 1, 9000, 3.0, 2.0)                          # SAME crests as paint
    glow = cv2.GaussianBlur(rings, (0, 0), 1.4)                             # SAME bubble bodies
    lum = np.clip(rings * 1.7 + glow * 3.9, 0, 1)                           # SAME acid-bright subset
    steel = _rk_n(h, w, s ^ 2, (5, 12))                                     # SAME steel mottle
    M = 22 + (1 - np.clip(glow * 2.2, 0, 1)) * 55 + steel * 60              # raw steel BETWEEN the bubbles
    R = np.clip(190 - glow * 100 - steel * 60, 15, 255)                     # rough steel, slick bubble bodies
    Cc = 24 + lum * 231                                                     # IGNITION: acid bubbles wet-flash
    return M, R, Cc

# --- IGNITION: neon_electric_blue ---
def _ign_neon_electric_blue_paint(h, w, s):
    bolt = np.clip(_rk_sc(h, w, s ^ 1, 5000, 1.0, "streak", len_px=11, amp=(0.8, 1.0)) * 2.0, 0, 1)  # ghost lightning
    arcs = _rk_sc(h, w, s ^ 2, 3800, 0.9, "streak", len_px=6)               # visible storm
    nav = _rk_n(h, w, s ^ 3, (6, 14))
    navy = _rk_ramp(nav, _rk_lut([(0.035, 0.05, 0.14), (0.07, 0.11, 0.26)], 0.5))
    vis = arcs[..., None] * np.float32([0.22, 0.58, 1.0]) * 0.80
    ghost = bolt[..., None] * np.float32([0.30, 0.45, 0.85]) * 0.07         # near-invisible trace — M ignites THIS
    return np.clip(navy + vis + ghost, 0, 1).astype(np.float32)


def _ign_neon_electric_blue_spec(h, w, s):
    bolt = np.clip(_rk_sc(h, w, s ^ 1, 5000, 1.0, "streak", len_px=11, amp=(0.8, 1.0)) * 2.0, 0, 1)  # SAME ghosts
    arcs = _rk_sc(h, w, s ^ 2, 3800, 0.9, "streak", len_px=6)               # SAME visible storm
    nav = _rk_n(h, w, s ^ 3, (6, 14))                                       # SAME navy field
    M = 18 + bolt * 237                                                     # IGNITION: hidden lightning detonates
    R = np.clip(184 - arcs * 130 - nav * 45, 15, 255)                       # ionized smooth channels in rough navy
    Cc = 28 + cv2.GaussianBlur(np.maximum(arcs, bolt * 0.8), (0, 0), 2.4) * 165 + nav * 30
    return M, R, Cc

# --- IGNITION: neon_blacklight ---
def _ign_neon_blacklight_paint(h, w, s):
    glyph = _rk_sc(h, w, s ^ 1, 7500, 4.0, "star5", amp=(0.85, 1.0))        # hidden glyph swarm
    uv = np.clip(glyph * 4.0 + cv2.GaussianBlur(glyph, (0, 0), 1.3) * 3.4, 0, 1)  # UV-ink field — Cc ignites THIS
    fleck = _rk_sc(h, w, s ^ 2, 2500, 0.8, "dot")                           # lavender flecks
    blotch = _rk_n(h, w, s ^ 3, (4, 9))                                     # uneven violet felt
    base = np.float32([0.10, 0.065, 0.18])[None, None, :] * (0.65 + blotch[..., None] * 0.7)
    ink = uv[..., None] * np.float32([0.42, 0.20, 0.85]) * 0.10             # near-invisible ink
    spark = fleck[..., None] * np.float32([0.65, 0.50, 0.95]) * 0.22
    return np.clip(base + ink + spark, 0, 1).astype(np.float32)


def _ign_neon_blacklight_spec(h, w, s):
    glyph = _rk_sc(h, w, s ^ 1, 7500, 4.0, "star5", amp=(0.85, 1.0))        # SAME glyphs as paint
    uv = np.clip(glyph * 4.0 + cv2.GaussianBlur(glyph, (0, 0), 1.3) * 3.4, 0, 1)  # SAME UV-ink field
    fleck = _rk_sc(h, w, s ^ 2, 2500, 0.8, "dot")                           # SAME flecks
    blotch = _rk_n(h, w, s ^ 3, (4, 9))                                     # SAME felt
    M = 16 + fleck * 170 + blotch * 38                                      # the flecks carry the metal
    R = np.clip(152 + (blotch - 0.5) * 155 - uv * 45, 15, 255)              # felt pools; the ink lies slick
    Cc = 24 + uv * 231                                                      # IGNITION: blacklight ink detonates in the clear
    return M, R, Cc

# --- IGNITION: neon_orange_hazard ---
def _ign_neon_orange_hazard_paint(h, w, s):
    shard = flip_lattice((h, w), s ^ 1, 2.6, 0.42)                          # amber/black shatter territories
    raw = _rk_sc(h, w, s ^ 2, 8000, 5.6, "arc", amp=(0.7, 1.0))             # warning arc-tick swarm
    ticks = np.clip(raw * 3.0, 0, 1)
    emb = np.clip((ticks + cv2.GaussianBlur(raw, (0, 0), 1.0) * 2.7) * 1.5, 0, 1) * (1 - shard)  # ember subset — M ignites THIS
    grain = _rk_n(h, w, s ^ 3, (5, 12))
    amber = np.float32([1.0, 0.55, 0.05])[None, None, :] * (0.75 + grain[..., None] * 0.35)
    blk = np.float32([0.065, 0.055, 0.05])[None, None, :] * (0.7 + grain[..., None] * 0.5)
    eff = amber * shard[..., None] + blk * (1 - shard[..., None])
    eff = eff * (1 - (ticks * shard)[..., None] * 0.55)                     # scorch ticks on amber
    return np.clip(eff + emb[..., None] * np.float32([0.90, 0.28, 0.02]) * 0.13, 0, 1).astype(np.float32)


def _ign_neon_orange_hazard_spec(h, w, s):
    shard = flip_lattice((h, w), s ^ 1, 2.6, 0.42)                          # SAME territories as paint
    raw = _rk_sc(h, w, s ^ 2, 8000, 5.6, "arc", amp=(0.7, 1.0))             # SAME ticks
    ticks = np.clip(raw * 3.0, 0, 1)
    emb = np.clip((ticks + cv2.GaussianBlur(raw, (0, 0), 1.0) * 2.7) * 1.5, 0, 1) * (1 - shard)  # SAME ember subset
    grain = _rk_n(h, w, s ^ 3, (5, 12))                                     # SAME grain
    crack = 1 - np.abs(2 * cv2.GaussianBlur(shard, (0, 0), 1.6) - 1)        # shatter seam corridors
    M = 20 + emb * 235                                                      # IGNITION: hidden embers in the black shards
    R = np.clip(70 + (1 - shard) * 105 + grain * 55 - ticks * 40, 15, 255)
    Cc = 26 + crack * 160 + shard * 38                                      # wet seams + amber gloss pools
    return M, R, Cc

# --- IGNITION: neon_red_alert ---
def _ign_neon_red_alert_paint(h, w, s):
    siren = _rk_rings(h, w, s ^ 1, 5200, 1.8, 1.2)
    ghost = _rk_rings(h, w, s ^ 2, 2600, 3.2, 1.9)
    halo = cv2.GaussianBlur(siren, (0, 0), 2.2)
    base = np.float32([0.13, 0.045, 0.05])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 3, (5, 12))[..., None] * 0.6)
    eff = base + halo[..., None] * np.float32([0.55, 0.06, 0.06]) * 0.30
    eff = eff + siren[..., None] * np.float32([1.0, 0.14, 0.10]) * 0.85
    eff = eff * (1.0 - ghost[..., None] * 0.55)
    return np.clip(eff, 0, 1)

def _ign_neon_red_alert_spec(h, w, s):
    siren = _rk_rings(h, w, s ^ 1, 5200, 1.8, 1.2)
    ghost = _rk_rings(h, w, s ^ 2, 2600, 3.2, 1.9)
    halo = cv2.GaussianBlur(siren, (0, 0), 2.2)
    M = 18 + siren * 175 + ghost * 30
    R = np.clip(186 - halo * 150 - ghost * 35 + (_rk_n(h, w, s ^ 4, (20, 45)) - 0.5) * 40, 15, 255)
    Cc = 24 + np.clip(ghost * 1.45, 0, 1) * 229 + halo * 26
    return M, R, Cc

# --- IGNITION: neon_cyber_yellow ---
def _ign_neon_cyber_yellow_paint(h, w, s):
    web = _rk_web(h, w, s ^ 1, 4600, k=2)
    pads = _rk_sc(h, w, s ^ 2, 4200, 2.0, "dot")
    base = np.float32([0.12, 0.12, 0.13])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 3, (5, 12))[..., None] * 0.6)
    eff = base + web[..., None] * np.float32([1.0, 0.85, 0.10]) * 0.80
    eff = eff * (1.0 - np.clip(pads, 0, 1)[..., None] * 0.72)
    eff = eff + cv2.GaussianBlur(web, (0, 0), 1.6)[..., None] * np.float32([0.9, 0.75, 0.1]) * 0.12
    return np.clip(eff, 0, 1)

def _ign_neon_cyber_yellow_spec(h, w, s):
    web = _rk_web(h, w, s ^ 1, 4600, k=2)
    pads = _rk_sc(h, w, s ^ 2, 4200, 2.0, "dot")
    halo = cv2.GaussianBlur(web, (0, 0), 2.4)
    M = 20 + web * 172 + pads * 24
    R = np.clip(190 - halo * 145 - pads * 50 + (_rk_n(h, w, s ^ 4, (18, 40)) - 0.5) * 36, 15, 255)
    Cc = 26 + np.clip(pads * 1.5, 0, 1) * 229 + halo * 24
    return M, R, Cc

# --- IGNITION: neon_ice_white ---
def _ign_neon_ice_white_paint(h, w, s):
    cracks = _rk_web(h, w, s ^ 1, 2200, k=2)
    fil = _rk_sc(h, w, s ^ 2, 9000, 0.8, "streak", len_px=3)
    gl = _rk_sc(h, w, s ^ 3, 170, 2.6, "star5")
    base = _rk_ramp(_rk_n(h, w, s ^ 4, (5, 12)), _rk_lut([(0.86, 0.90, 0.95), (0.94, 0.97, 1.0)], 0.6))
    eff = base * (1.0 - cracks[..., None] * np.float32([0.52, 0.44, 0.30]))
    eff = eff * (0.86 + fil[..., None] * 0.20) + gl[..., None] * 0.30
    return np.clip(eff, 0, 1)

def _ign_neon_ice_white_spec(h, w, s):
    cracks = _rk_web(h, w, s ^ 1, 2200, k=2)
    fil = _rk_sc(h, w, s ^ 2, 9000, 0.8, "streak", len_px=3)
    gl = _rk_sc(h, w, s ^ 3, 170, 2.6, "star5")
    bloom = cv2.GaussianBlur(cracks, (0, 0), 3.0)
    M = 14 + np.clip(cracks * 1.35, 0, 1) * 238 + gl * 26
    R = np.clip(150 - fil * 120 + (_rk_n(h, w, s ^ 5, (20, 45)) - 0.5) * 44 - bloom * 30, 15, 255)
    Cc = 30 + bloom * 130 + gl * 80 + _rk_n(h, w, s ^ 6, (8, 18)) * 45
    return M, R, Cc

# --- IGNITION: neon_dual_glow ---
def _ign_neon_dual_glow_paint(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 1.3, 0.30)
    bnd = cv2.GaussianBlur(flip, (0, 0), 1.5)
    seam = np.clip(1.0 - np.abs(bnd * 2.0 - 1.0), 0, 1) ** 2
    grain = _rk_n(h, w, s ^ 2, (3, 6))[..., None]
    mag = np.float32([0.88, 0.12, 0.56])[None, None, :]
    teal = np.float32([0.03, 0.10, 0.12])[None, None, :]
    eff = (mag * (1 - flip[..., None]) + teal * flip[..., None]) * (0.70 + grain * 0.34)
    eff = eff + seam[..., None] * np.float32([0.55, 0.75, 0.9]) * 0.18
    return np.clip(eff, 0, 1)

def _ign_neon_dual_glow_spec(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 1.3, 0.30)
    bnd = cv2.GaussianBlur(flip, (0, 0), 1.5)
    seam = np.clip(1.0 - np.abs(bnd * 2.0 - 1.0), 0, 1) ** 2
    pools = cv2.GaussianBlur(_rk_n(h, w, s ^ 3, (9, 21)), (0, 0), 2.0)
    M = 12 + flip * 240
    R = np.clip(70 + seam * 130 + (_rk_n(h, w, s ^ 4, (16, 36)) - 0.5) * 50, 15, 255)
    Cc = 28 + (1.0 - flip) * np.clip(pools * 1.4 - 0.35, 0, 1) * 165 + seam * 40
    return M, R, Cc

# --- IGNITION: neon_rainbow_tube ---
def _ign_neon_rainbow_tube_paint(h, w, s):
    web = _rk_web(h, w, s ^ 1, 4200, k=2)
    sel = _rk_n(h, w, s ^ 2, (3, 7))
    on = np.clip((sel - 0.40) * 8.0, 0, 1)
    lit, dead = web * on, web * (1.0 - on)
    hue = _rk_ramp(_rk_n(h, w, s ^ 3, (4, 9)),
                   _rk_lut([(1.0, 0.2, 0.2), (1.0, 0.8, 0.1), (0.2, 0.9, 0.4), (0.2, 0.5, 1.0), (0.7, 0.25, 0.9)], 0.55))
    base = np.float32([0.075, 0.075, 0.095])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 4, (5, 12))[..., None] * 0.6)
    eff = base + hue * lit[..., None] * 0.92 + dead[..., None] * 0.085
    eff = eff + cv2.GaussianBlur(lit, (0, 0), 1.8)[..., None] * hue * 0.16
    return np.clip(eff, 0, 1)

def _ign_neon_rainbow_tube_spec(h, w, s):
    web = _rk_web(h, w, s ^ 1, 4200, k=2)
    sel = _rk_n(h, w, s ^ 2, (3, 7))
    on = np.clip((sel - 0.40) * 8.0, 0, 1)
    lit, dead = web * on, web * (1.0 - on)
    halo = cv2.GaussianBlur(web, (0, 0), 2.4)
    M = 16 + lit * 178 + dead * 26
    R = np.clip(188 - halo * 148 + (_rk_n(h, w, s ^ 5, (18, 40)) - 0.5) * 40, 15, 255)
    Cc = 22 + np.clip(dead * 1.5, 0, 1) * 233 + cv2.GaussianBlur(dead, (0, 0), 2.0) * 30
    return M, R, Cc

# --- IGNITION: prizm_adaptive ---
def _ign_prizm_adaptive_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1000, (h * w) // 38))
    t = np.random.default_rng(s ^ 2).random(int(lab.max()) + 1).astype(np.float32)[lab]
    dead = (t > 0.74).astype(np.float32)
    col = _rk_ramp(t, _rk_lut([(0.70, 0.20, 0.45), (0.15, 0.55, 0.70), (0.75, 0.60, 0.15)], 0.55))
    col = col * (1.0 - dead[..., None] * 0.82) * (1.0 - edge[..., None] * 0.55)
    return np.clip(col * (0.62 + _rk_n(h, w, s ^ 3, (3, 7))[..., None] * 0.5), 0, 1).astype(np.float32)

def _ign_prizm_adaptive_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1000, (h * w) // 38))
    t = np.random.default_rng(s ^ 2).random(int(lab.max()) + 1).astype(np.float32)[lab]
    dead = (t > 0.74).astype(np.float32)
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    M = 14 + dead * (1.0 - edge) * 241
    R = np.clip(92 + edge * 128 - t * 58, 15, 255)
    Cc = 28 + (1.0 - d1n) ** 2 * 168 * (1.0 - dead * 0.45)
    return M, R, Cc

# --- IGNITION: prizm_alien_skin ---
def _ign_prizm_alien_skin_paint(h, w, s):
    pores = np.clip((np.clip(_rk_rings(h, w, s ^ 1, 5200, 2.0, 1.3), 0, 1) - 0.012) / 0.062, 0, 1)
    th = np.clip(_rk_n(h, w, s ^ 2, (5, 11)), 0, 1)
    film = interference_palette(th, 2.0, 0.55, base_srgb=np.float32([0.26, 0.40, 0.25]))
    return np.clip(film * (1.0 - pores[..., None] * 0.80), 0, 1).astype(np.float32)

def _ign_prizm_alien_skin_spec(h, w, s):
    pores = np.clip((np.clip(_rk_rings(h, w, s ^ 1, 5200, 2.0, 1.3), 0, 1) - 0.012) / 0.062, 0, 1)
    th = np.clip(_rk_n(h, w, s ^ 2, (5, 11)), 0, 1)
    Cc = 24 + pores * 231
    M = 18 + (np.abs(th - 0.5) * 2.0) ** 3 * 160
    R = np.clip(192 - _rk_gr(h, w, s ^ 3, 3, 3.4) * 128 - pores * 28, 15, 255)
    return M, R, Cc

# --- IGNITION: prizm_arctic ---
def _ign_prizm_arctic_paint(h, w, s):
    shards = np.clip((np.clip(_rk_sc(h, w, s ^ 1, 9000, 1.1, "streak", len_px=5), 0, 1) - 0.06) / 0.15, 0, 1)
    th = np.clip(_rk_n(h, w, s ^ 2, (6, 13)), 0, 1)
    film = interference_palette(th, 1.8, 0.5, base_srgb=np.float32([0.60, 0.70, 0.82]))
    return np.clip(film * 0.74 + shards[..., None] * np.float32([0.72, 0.90, 1.0]) * 0.55, 0, 1).astype(np.float32)

def _ign_prizm_arctic_spec(h, w, s):
    shards = np.clip((np.clip(_rk_sc(h, w, s ^ 1, 9000, 1.1, "streak", len_px=5), 0, 1) - 0.06) / 0.15, 0, 1)
    th = np.clip(_rk_n(h, w, s ^ 2, (6, 13)), 0, 1)
    M = 16 + shards * 239
    R = np.clip(72 + _rk_gr(h, w, s ^ 3, 2, 3.0) * 122 - shards * 10, 15, 255)
    Cc = 28 + th ** 2 * 172
    return M, R, Cc

# --- IGNITION: prizm_aurora_shift ---
def _ign_prizm_aurora_shift_paint(h, w, s):
    cur = _rk_gr(h, w, s ^ 1, 4, 3.8)
    band = np.clip((cur - 0.76) / 0.07, 0, 1)
    stre = np.clip(_rk_sc(h, w, s ^ 3, 4200, 0.9, "streak", len_px=6), 0, 1)
    col = _rk_ramp(np.clip(cur + (_rk_n(h, w, s ^ 2, (3, 6)) - 0.5) * 0.22, 0, 1),
                   _rk_lut([(0.08, 0.55, 0.42), (0.28, 0.22, 0.68), (0.06, 0.38, 0.62)], 0.6))
    col = col * (1.0 - band[..., None] * 0.88) + band[..., None] * np.float32([0.02, 0.03, 0.06])
    return np.clip(col + stre[..., None] * np.float32([0.35, 0.85, 0.70]) * 0.22, 0, 1).astype(np.float32)

def _ign_prizm_aurora_shift_spec(h, w, s):
    cur = _rk_gr(h, w, s ^ 1, 4, 3.8)
    band = np.clip((cur - 0.76) / 0.07, 0, 1)
    stre = np.clip(_rk_sc(h, w, s ^ 3, 4200, 0.9, "streak", len_px=6), 0, 1)
    M = 14 + band * 240
    R = np.clip(58 + cur * 138 + (_rk_n(h, w, s ^ 2, (3, 6)) - 0.5) * 44, 15, 255)
    Cc = 26 + stre * 174 + cur * 36
    return M, R, Cc

# --- IGNITION: prizm_black_rainbow ---
def _ign_prizm_black_rainbow_paint(h, w, s):
    thr = np.clip((np.clip(_rk_web(h, w, s ^ 1, 5600, k=2, intensity=(0.25, 1.0)), 0, 1) - 0.18) / 0.20, 0, 1)
    hue = _rk_n(h, w, s ^ 2, (4, 9))
    col = _rk_ramp(hue, _rk_lut([(0.80, 0.10, 0.20), (0.80, 0.60, 0.10), (0.10, 0.70, 0.40), (0.20, 0.30, 0.90)], 0.5))
    base = np.float32([0.065, 0.065, 0.08])[None, None, :] * (0.7 + _rk_n(h, w, s ^ 3, (4, 9))[..., None] * 0.5)
    return np.clip(base + col * thr[..., None] * 0.92, 0, 1).astype(np.float32)

def _ign_prizm_black_rainbow_spec(h, w, s):
    thr = np.clip((np.clip(_rk_web(h, w, s ^ 1, 5600, k=2, intensity=(0.25, 1.0)), 0, 1) - 0.18) / 0.20, 0, 1)
    hue = _rk_n(h, w, s ^ 2, (4, 9))
    M = 12 + thr * 240
    R = np.clip(178 - cv2.GaussianBlur(thr, (0, 0), 2.4) * 148 - (_rk_n(h, w, s ^ 3, (4, 9)) - 0.5) * 40, 15, 255)
    Cc = 22 + hue * 158 + thr * 30
    return M, R, Cc

# --- IGNITION: prizm_blood_moon ---
def _ign_prizm_blood_moon_paint(h, w, s):
    halo = np.clip((np.clip(_rk_rings(h, w, s ^ 1, 4800, 2.2, 1.5), 0, 1) - 0.015) / 0.075, 0, 1)
    g = _rk_n(h, w, s ^ 2, (3, 6))
    base = np.float32([0.27, 0.05, 0.06])[None, None, :] * (0.65 + g[..., None] * 0.6)
    return np.clip(base * (1.0 - halo[..., None] * 0.62) + halo[..., None] * np.float32([0.09, 0.01, 0.02]), 0, 1).astype(np.float32)

def _ign_prizm_blood_moon_spec(h, w, s):
    halo = np.clip((np.clip(_rk_rings(h, w, s ^ 1, 4800, 2.2, 1.5), 0, 1) - 0.015) / 0.075, 0, 1)
    g = _rk_n(h, w, s ^ 2, (3, 6))
    Cc = 24 + halo * 231
    M = 14 + g ** 2 * 132
    R = np.clip(188 - _rk_gr(h, w, s ^ 3, 2, 3.4) * 126 + halo * 24, 15, 255)
    return M, R, Cc

# --- IGNITION: prizm_candy_paint ---
def _ign_prizm_candy_paint_paint(h, w, s):
    fl = np.clip((np.clip(_rk_sc(h, w, s ^ 1, 16000, 1.2, "dot"), 0, 1) - 0.08) / 0.155, 0, 1)
    dn = _rk_n(h, w, s ^ 2, (4, 9))
    metal = np.dstack([0.42 + fl * 0.55] * 3)
    return np.clip(candy_absorb(metal, np.float32([0.80, 0.06, 0.12]), 0.7 + dn * 1.1), 0, 1).astype(np.float32)

def _ign_prizm_candy_paint_spec(h, w, s):
    fl = np.clip((np.clip(_rk_sc(h, w, s ^ 1, 16000, 1.2, "dot"), 0, 1) - 0.08) / 0.155, 0, 1)
    dn = _rk_n(h, w, s ^ 2, (4, 9))
    M = 20 + fl * 235
    R = np.clip(152 - _rk_gr(h, w, s ^ 3, 2, 3.2) * 112, 15, 255)
    Cc = 32 + dn * 186
    return M, R, Cc

# --- IGNITION: prizm_chrome_rose ---
def _ign_prizm_chrome_rose_paint(h, w, s):
    pet = np.clip((np.clip(_rk_sc(h, w, s ^ 1, 22000, 2.0, "petal"), 0, 1) - 0.01) / 0.065, 0, 1)
    g = _rk_n(h, w, s ^ 2, (3, 6))
    chrome = np.float32([0.70, 0.72, 0.76])[None, None, :] * (0.62 + g[..., None] * 0.5)
    rose = np.float32([0.16, 0.02, 0.05])[None, None, :]
    return np.clip(chrome * (1.0 - pet[..., None] * 0.85) + rose * pet[..., None], 0, 1).astype(np.float32)

def _ign_prizm_chrome_rose_spec(h, w, s):
    pet = np.clip((np.clip(_rk_sc(h, w, s ^ 1, 22000, 2.0, "petal"), 0, 1) - 0.01) / 0.065, 0, 1)
    g = _rk_n(h, w, s ^ 2, (3, 6))
    M = np.clip(104 + pet * 144 + (g - 0.5) * 22, 0, 252)
    R = np.clip(54 + _rk_gr(h, w, s ^ 3, 3, 3.4) * 128 + pet * 26, 15, 255)
    Cc = 28 + g ** 2 * 162
    return M, R, Cc

# --- IGNITION: prizm_copper_flame ---
def _ign_prizm_copper_flame_paint(h, w, s):
    fl = np.clip(_rk_sc(h, w, s ^ 1, 18000, 1.9, "petal"), 0, 1)
    tip = np.clip((fl - 0.01) / 0.075, 0, 1)
    t = np.clip(fl * 0.85 + _rk_n(h, w, s ^ 2, (3, 7)) * 0.30, 0, 1)
    col = _rk_ramp(t, _rk_lut([(0.30, 0.13, 0.06), (0.85, 0.45, 0.10), (0.98, 0.80, 0.35)], 0.5))
    return np.clip(col * (0.9 + tip[..., None] * 0.25), 0, 1).astype(np.float32)

def _ign_prizm_copper_flame_spec(h, w, s):
    fl = np.clip(_rk_sc(h, w, s ^ 1, 18000, 1.9, "petal"), 0, 1)
    tip = np.clip((fl - 0.01) / 0.075, 0, 1)
    Cc = 26 + tip * 229
    M = 28 + np.clip(fl * 2.6, 0, 1) * (1.0 - tip) * 150 + (_rk_n(h, w, s ^ 2, (3, 7)) - 0.5) * 36
    R = np.clip(192 - _rk_gr(h, w, s ^ 3, 2, 3.0) * 128 - fl * 32, 15, 255)
    return M, R, Cc

# --- IGNITION: prizm_cosmos ---
def _ign_prizm_cosmos_paint(h, w, s):
    st = np.clip((np.clip(_rk_sc(h, w, s ^ 1, 16000, 1.2, "dot"), 0, 1) - 0.08) / 0.155, 0, 1)
    dn = _rk_n(h, w, s ^ 2, (5, 10))
    arm = _rk_n(h, w, s ^ 3, (2, 5))
    neb = candy_absorb(np.full((h, w, 3), 0.55, np.float32), np.float32([0.30, 0.12, 0.55]), 0.6 + dn * 1.2)
    return np.clip(neb * (0.82 + arm[..., None] * 0.38) + st[..., None] * 0.9, 0, 1).astype(np.float32)

def _ign_prizm_cosmos_spec(h, w, s):
    st = np.clip((np.clip(_rk_sc(h, w, s ^ 1, 16000, 1.2, "dot"), 0, 1) - 0.08) / 0.155, 0, 1)
    dn = _rk_n(h, w, s ^ 2, (5, 10))
    arm = _rk_n(h, w, s ^ 3, (2, 5))
    M = 12 + st * 243
    R = np.clip(186 - dn * 124, 15, 255)
    Cc = 24 + arm ** 2 * 172
    return M, R, Cc

# --- IGNITION: prizm_dark_matter ---
def _ign_prizm_dark_matter_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 110))
    g = _rk_n(h, w, s ^ 2, (3, 7))
    dots = np.clip(_rk_sc(h, w, s ^ 3, 1100, 1.6, "dot"), 0, 1)
    base = np.float32([0.07, 0.06, 0.10])[None, None, :] * (0.7 + g[..., None] * 0.5)
    return np.clip(base + edge[..., None] * np.float32([0.30, 0.12, 0.52]) * 0.22 + dots[..., None] * np.float32([0.55, 0.40, 0.85]) * 0.30, 0, 1).astype(np.float32)

def _ign_prizm_dark_matter_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(900, (h * w) // 110))
    g = _rk_n(h, w, s ^ 2, (3, 7))
    dots = np.clip(_rk_sc(h, w, s ^ 3, 1100, 1.6, "dot"), 0, 1)
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    M = 10 + edge * 245
    R = np.clip(198 - d1n * 132 + (g - 0.5) * 36, 15, 255)
    Cc = 22 + dots * 178 + g * 34
    return M, R, Cc

# --- IGNITION: prizm_deep_space ---
def _ign_prizm_deep_space_paint(h, w, s):
    vis = np.clip(_rk_sc(h, w, s ^ 1, 7000, 0.8, "dot"), 0, 1)
    hid = np.clip((np.clip(_rk_sc(h, w, s ^ 4, 14000, 1.2, "dot"), 0, 1) - 0.08) / 0.155, 0, 1)
    g = _rk_n(h, w, s ^ 2, (5, 11))
    base = np.float32([0.065, 0.075, 0.15])[None, None, :] * (0.65 + g[..., None] * 0.6)
    eff = base + vis[..., None] * np.float32([0.55, 0.65, 0.95]) * 0.5
    return np.clip(eff * (1.0 - hid[..., None] * 0.55), 0, 1).astype(np.float32)

def _ign_prizm_deep_space_spec(h, w, s):
    vis = np.clip(_rk_sc(h, w, s ^ 1, 7000, 0.8, "dot"), 0, 1)
    hid = np.clip((np.clip(_rk_sc(h, w, s ^ 4, 14000, 1.2, "dot"), 0, 1) - 0.08) / 0.155, 0, 1)
    g = _rk_n(h, w, s ^ 2, (5, 11))
    halo = cv2.GaussianBlur(vis, (0, 0), 2.0)
    halo = halo / max(float(halo.max()), 1e-5)
    M = 14 + hid * 241
    Cc = 24 + halo * 150 + g * 22
    R = np.clip(184 - _rk_gr(h, w, s ^ 3, 2, 3.2) * 118 - hid * 24, 15, 255)
    return M, R, Cc

# --- IGNITION: prizm_duochrome ---
def _ign_prizm_duochrome_paint(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 1.1, 0.30)
    p = _rk_n(h, w, s ^ 2, (2, 5))
    teal = np.float32([0.13, 0.46, 0.55])[None, None, :]
    wine = np.float32([0.14, 0.03, 0.09])[None, None, :]
    col = teal * (1.0 - flip[..., None]) + wine * flip[..., None]
    return np.clip(col * (0.66 + p[..., None] * 0.55), 0, 1).astype(np.float32)

def _ign_prizm_duochrome_spec(h, w, s):
    flip = flip_lattice((h, w), s ^ 1, 1.1, 0.30)
    p = _rk_n(h, w, s ^ 2, (2, 5))
    M = 15 + flip * 240
    R = np.clip(64 + _rk_gr(h, w, s ^ 3, 2, 3.2) * 132 - flip * 26, 15, 255)
    Cc = 26 + p ** 2 * 168
    return M, R, Cc

# --- IGNITION: prizm_ember ---
def _ign_prizm_ember_paint(h, w, s):
    sp = np.clip((np.clip(_rk_sc(h, w, s ^ 1, 9000, 1.2, "dot"), 0, 1) - 0.03) / 0.09, 0, 1)
    ck = np.clip(_rk_web(h, w, s ^ 2, 3600, k=2), 0, 1)
    glow = cv2.GaussianBlur(sp, (0, 0), 3.0)
    glow = glow / max(float(glow.max()), 1e-5)
    g = _rk_n(h, w, s ^ 3, (3, 6))
    base = np.float32([0.16, 0.06, 0.04])[None, None, :] * (0.6 + g[..., None] * 0.6)
    eff = base * (1.0 - ck[..., None] * 0.7) + glow[..., None] * np.float32([0.45, 0.14, 0.04]) * 0.35
    return np.clip(eff + sp[..., None] * np.float32([1.0, 0.45, 0.10]) * 0.8, 0, 1).astype(np.float32)

def _ign_prizm_ember_spec(h, w, s):
    sp = np.clip((np.clip(_rk_sc(h, w, s ^ 1, 9000, 1.2, "dot"), 0, 1) - 0.03) / 0.09, 0, 1)
    ck = np.clip(_rk_web(h, w, s ^ 2, 3600, k=2), 0, 1)
    glow = cv2.GaussianBlur(sp, (0, 0), 3.0)
    glow = glow / max(float(glow.max()), 1e-5)
    Cc = 22 + sp * 233
    M = 16 + glow * 150
    R = np.clip(64 + ck * 152 + (_rk_n(h, w, s ^ 3, (3, 6)) - 0.5) * 44, 15, 255)
    return M, R, Cc

# --- IGNITION: prizm_fire_ice ---
def _ign_prizm_fire_ice_paint(h, w, s):
    m0, m1, m2 = tri_partition((h, w), s ^ 1, cells=max(2400, (h * w) // 18), soften_px=0.8)
    fnz = _rk_n(h, w, s ^ 2, (4, 9))
    inz = _rk_n(h, w, s ^ 3, (4, 9))
    hot = _rk_ramp(fnz, _rk_lut([(0.75, 0.15, 0.05), (1.0, 0.65, 0.15)], 0.5))
    cold = _rk_ramp(inz, _rk_lut([(0.15, 0.40, 0.75), (0.70, 0.85, 0.95)], 0.5))
    obsidian = np.float32([0.05, 0.05, 0.07])[None, None, :]
    return np.clip(hot * m0[..., None] + cold * m1[..., None] + obsidian * m2[..., None], 0, 1).astype(np.float32)

def _ign_prizm_fire_ice_spec(h, w, s):
    m0, m1, m2 = tri_partition((h, w), s ^ 1, cells=max(2400, (h * w) // 18), soften_px=0.8)
    fnz = _rk_n(h, w, s ^ 2, (4, 9))
    inz = _rk_n(h, w, s ^ 3, (4, 9))
    M = 12 + m2 * 243
    R = np.clip(186 - m1 * 142 + (inz - 0.5) * 52, 15, 255)
    Cc = 22 + m0 * (0.45 + fnz * 0.55) * 198
    return M, R, Cc

# --- IGNITION: prizm_galaxy_dust ---
def _ign_prizm_galaxy_dust_paint(h, w, s):
    film_th = _rk_n(h, w, s ^ 1, (7, 15))
    stars = np.clip(_rk_sc(h, w, s ^ 2, 6000, 0.8, 'dot') * 1.5, 0, 1)
    void = np.clip(_rk_sc(h, w, s ^ 3, 8000, 1.0, 'dot') * 1.8, 0, 1)
    neb = interference_palette(film_th, 1.6, 0.45, base_srgb=np.float32([0.10, 0.07, 0.18]))
    eff = neb * (1.0 - void[..., None] * 0.85)
    eff = eff + stars[..., None] * np.float32([0.85, 0.88, 1.0]) * 0.7
    return np.clip(eff, 0, 1)

def _ign_prizm_galaxy_dust_spec(h, w, s):
    film_th = _rk_n(h, w, s ^ 1, (7, 15))
    stars = np.clip(_rk_sc(h, w, s ^ 2, 6000, 0.8, 'dot') * 1.5, 0, 1)
    void = np.clip(_rk_sc(h, w, s ^ 3, 8000, 1.0, 'dot') * 1.8, 0, 1)
    M = 14 + void * 240
    R = np.clip(170 - film_th * 120 + (_rk_n(h, w, s ^ 4, (24, 60)) - 0.5) * 30, 15, 255)
    Cc = 24 + cv2.GaussianBlur(stars, (0, 0), 2.0) * 185
    return M, R, Cc

# --- IGNITION: prizm_holographic ---
def _ign_prizm_holographic_paint(h, w, s):
    patches = _rk_gr(h, w, s ^ 1, 5, 2.6)
    band = np.floor(np.clip(patches, 0, 0.999) * 6)
    ghost = (band == 2).astype(np.float32)
    glint = np.clip(_rk_sc(h, w, s ^ 2, 6000, 0.9, 'streak', len_px=5) * 1.4, 0, 1)
    hue = _rk_ramp(patches, _rk_lut([(0.9, 0.2, 0.3), (0.9, 0.8, 0.2), (0.2, 0.8, 0.5), (0.25, 0.4, 0.95), (0.7, 0.3, 0.9)], 0.6))
    sil = np.float32([0.65, 0.66, 0.70])[None, None, :]
    eff = np.clip(sil * 0.45 + hue * 0.65, 0, 1)
    eff = eff * (1.0 - ghost[..., None] * 0.55)
    return np.clip(eff + glint[..., None] * np.float32([0.95, 0.97, 1.0]) * 0.30, 0, 1)

def _ign_prizm_holographic_spec(h, w, s):
    patches = _rk_gr(h, w, s ^ 1, 5, 2.6)
    band = np.floor(np.clip(patches, 0, 0.999) * 6)
    ghost = (band == 2).astype(np.float32)
    seam = np.clip(np.abs(np.diff(band, axis=0, prepend=band[:1])) + np.abs(np.diff(band, axis=1, prepend=band[:, :1])), 0, 1)
    glint = np.clip(_rk_sc(h, w, s ^ 2, 6000, 0.9, 'streak', len_px=5) * 1.4, 0, 1)
    M = 18 + ghost * 235
    R = np.clip(60 + seam * 150 + (_rk_n(h, w, s ^ 3, (20, 48)) - 0.5) * 40, 15, 255)
    Cc = 26 + glint * 195
    return M, R, Cc

# --- IGNITION: prizm_iridescent ---
def _ign_prizm_iridescent_paint(h, w, s):
    th = np.clip(_rk_n(h, w, s ^ 1, (3, 8)) + (_rk_n(h, w, s ^ 9, (40, 90)) - 0.5) * 0.08, 0, 1)
    band = np.floor(np.clip(th, 0, 0.999) * 5)
    fringe = np.clip(np.abs(np.diff(band, axis=0, prepend=band[:1])) + np.abs(np.diff(band, axis=1, prepend=band[:, :1])), 0, 1)
    fringe = np.clip(cv2.GaussianBlur(fringe, (0, 0), 1.2) * 2.8, 0, 1)
    slick = interference_palette(th, 2.4, 0.65, base_srgb=np.float32([0.45, 0.42, 0.48]))
    return np.clip(slick * (1.0 - fringe[..., None] * 0.72), 0, 1)

def _ign_prizm_iridescent_spec(h, w, s):
    th = np.clip(_rk_n(h, w, s ^ 1, (3, 8)) + (_rk_n(h, w, s ^ 9, (40, 90)) - 0.5) * 0.08, 0, 1)
    band = np.floor(np.clip(th, 0, 0.999) * 5)
    fringe = np.clip(np.abs(np.diff(band, axis=0, prepend=band[:1])) + np.abs(np.diff(band, axis=1, prepend=band[:, :1])), 0, 1)
    fringe = np.clip(cv2.GaussianBlur(fringe, (0, 0), 1.2) * 2.8, 0, 1)
    phase = 0.5 + 0.5 * np.cos(2 * np.pi * (th * 5 - band))
    M = 16 + fringe * 239
    R = np.clip(55 + band * 38 + (_rk_n(h, w, s ^ 2, (22, 52)) - 0.5) * 30, 15, 255)
    Cc = 22 + phase * 165
    return M, R, Cc

# --- IGNITION: prizm_midnight ---
def _ign_prizm_midnight_paint(h, w, s):
    rain = np.clip(_rk_sc(h, w, s ^ 1, 4800, 0.9, 'streak', len_px=7) * 1.5, 0, 1)
    ghost = np.clip(_rk_sc(h, w, s ^ 2, 5600, 0.9, 'streak', len_px=8) * 1.7, 0, 1)
    g = _rk_n(h, w, s ^ 3, (3, 6))[..., None]
    base = np.float32([0.055, 0.065, 0.12])[None, None, :] * (0.75 + g * 0.5)
    eff = base + rain[..., None] * np.float32([0.30, 0.45, 0.80]) * 0.55
    return np.clip(eff * (1.0 - ghost[..., None] * 0.6), 0, 1)

def _ign_prizm_midnight_spec(h, w, s):
    rain = np.clip(_rk_sc(h, w, s ^ 1, 4800, 0.9, 'streak', len_px=7) * 1.5, 0, 1)
    ghost = np.clip(_rk_sc(h, w, s ^ 2, 5600, 0.9, 'streak', len_px=8) * 1.7, 0, 1)
    g = _rk_n(h, w, s ^ 3, (3, 6))
    M = 12 + ghost * 243
    R = np.clip(195 - g * 120, 15, 255)
    Cc = 20 + cv2.GaussianBlur(rain, (0, 0), 1.8) * 175
    return M, R, Cc

# --- IGNITION: prizm_mystichrome ---
def _ign_prizm_mystichrome_paint(h, w, s):
    flow = np.clip(_rk_gr(h, w, s ^ 1, 2, 3.4) + (_rk_n(h, w, s ^ 2, (3, 6)) - 0.5) * 0.2, 0, 1)
    flip = flip_lattice((h, w), s ^ 3, 1.1, 0.42)
    teal = _rk_ramp(flow, _rk_lut([(0.03, 0.18, 0.22), (0.10, 0.45, 0.50)], 0.55))
    grape = _rk_ramp(flow, _rk_lut([(0.10, 0.04, 0.22), (0.34, 0.12, 0.55)], 0.55))
    crest = np.clip((flow - 0.74) / 0.10, 0, 1)
    eff = teal * (1 - flip[..., None]) + grape * flip[..., None]
    return np.clip(eff * (1.0 - crest[..., None] * 0.55) + crest[..., None] * np.float32([0.05, 0.03, 0.10]) * 0.4, 0, 1)

def _ign_prizm_mystichrome_spec(h, w, s):
    flow = np.clip(_rk_gr(h, w, s ^ 1, 2, 3.4) + (_rk_n(h, w, s ^ 2, (3, 6)) - 0.5) * 0.2, 0, 1)
    flip = flip_lattice((h, w), s ^ 3, 1.1, 0.42)
    crest = np.clip((flow - 0.74) / 0.10, 0, 1)
    M = 22 + flip * (90 + 120 * flow)
    R = np.clip(165 - flow * 120 + (_rk_n(h, w, s ^ 4, (20, 46)) - 0.5) * 36, 15, 255)
    Cc = 24 + crest * 231
    return M, R, Cc

# --- IGNITION: prizm_neon ---
def _ign_prizm_neon_paint(h, w, s):
    web = np.clip(_rk_web(h, w, s ^ 1, 4800, k=2) * 1.6, 0, 1)
    g = _rk_n(h, w, s ^ 2, (3, 6))
    grit = _rk_n(h, w, s ^ 3, (60, 140))
    base = np.float32([0.06, 0.05, 0.09])[None, None, :] * (0.7 + g[..., None] * 0.5 + grit[..., None] * 0.25)
    return np.clip(base + web[..., None] * np.float32([0.55, 1.0, 0.20]) * 0.85, 0, 1)

def _ign_prizm_neon_spec(h, w, s):
    web = np.clip(_rk_web(h, w, s ^ 1, 4800, k=2) * 1.6, 0, 1)
    grit = _rk_n(h, w, s ^ 3, (60, 140))
    M = 16 + web * 239
    R = np.clip(60 + grit * 150 - web * 35, 15, 255)
    Cc = 22 + cv2.GaussianBlur(web, (0, 0), 2.6) * 180
    return M, R, Cc

# --- IGNITION: prizm_oceanic ---
def _ign_prizm_oceanic_paint(h, w, s):
    depth = _rk_n(h, w, s ^ 1, (5, 11))
    caust = np.clip(_rk_web(h, w, s ^ 2, 4200, k=2, intensity=(0.25, 0.6)) * 1.8, 0, 1)
    current = np.clip(_rk_sc(h, w, s ^ 3, 4600, 1.9, 'arc') * 1.6, 0, 1)
    sea = _rk_ramp(depth, _rk_lut([(0.02, 0.25, 0.38), (0.05, 0.45, 0.55)], 0.55))
    eff = sea * (1.0 - current[..., None] * 0.62)
    return np.clip(eff + caust[..., None] * np.float32([0.40, 0.85, 0.85]) * 0.5, 0, 1)

def _ign_prizm_oceanic_spec(h, w, s):
    depth = _rk_n(h, w, s ^ 1, (5, 11))
    caust = np.clip(_rk_web(h, w, s ^ 2, 4200, k=2, intensity=(0.25, 0.6)) * 1.8, 0, 1)
    current = np.clip(_rk_sc(h, w, s ^ 3, 4600, 1.9, 'arc') * 1.6, 0, 1)
    M = 18 + caust * 175
    R = np.clip(190 - depth * 130, 15, 255)
    Cc = 22 + current * 233
    return M, R, Cc

# --- IGNITION: prizm_phoenix ---
def _ign_prizm_phoenix_paint(h, w, s):
    plumes = np.clip(_rk_sc(h, w, s ^ 1, 5800, 1.3, 'petal') * 1.3, 0, 1)
    char = np.clip((_rk_sc(h, w, s ^ 2, 5200, 1.1, 'petal') - 0.22) * 2.0, 0, 1)
    flick = _rk_n(h, w, s ^ 3, (3, 7))
    fire = _rk_ramp(np.clip(plumes * 0.9 + flick * 0.15, 0, 1),
                    _rk_lut([(0.70, 0.15, 0.05), (0.95, 0.55, 0.10), (0.85, 0.20, 0.45)], 0.5))
    return np.clip(fire * (1.0 - char[..., None] * 0.92), 0, 1)

def _ign_prizm_phoenix_spec(h, w, s):
    plumes = np.clip(_rk_sc(h, w, s ^ 1, 5800, 1.3, 'petal') * 1.3, 0, 1)
    char = np.clip((_rk_sc(h, w, s ^ 2, 5200, 1.1, 'petal') - 0.22) * 2.0, 0, 1)
    flick = _rk_n(h, w, s ^ 3, (3, 7))
    M = 16 + np.clip((plumes - 0.55) * 2.6, 0, 1) * 239
    R = np.clip(70 + flick * 130, 15, 255)
    Cc = 24 + cv2.GaussianBlur(plumes, (0, 0), 1.6) * 170
    return M, R, Cc

# --- IGNITION: prizm_solar ---
def _ign_prizm_solar_paint(h, w, s):
    gran = np.clip(_rk_rings(h, w, s ^ 1, 4800, 1.8, 1.2), 0, 1)
    spots = np.clip(_rk_sc(h, w, s ^ 2, 3600, 1.6, 'dot') * 1.7, 0, 1)
    jit = _rk_n(h, w, s ^ 3, (3, 7))
    gold = _rk_ramp(np.clip(gran * 0.8 + jit * 0.35, 0, 1), _rk_lut([(0.85, 0.45, 0.05), (1.0, 0.80, 0.25)], 0.5))
    return np.clip(gold * (1.0 - spots[..., None] * 0.82), 0, 1)

def _ign_prizm_solar_spec(h, w, s):
    gran = np.clip(_rk_rings(h, w, s ^ 1, 4800, 1.8, 1.2), 0, 1)
    spots = np.clip(_rk_sc(h, w, s ^ 2, 3600, 1.6, 'dot') * 1.7, 0, 1)
    jit = _rk_n(h, w, s ^ 3, (3, 7))
    M = 18 + spots * 237
    R = np.clip(170 - jit * 110, 15, 255)
    Cc = 26 + cv2.GaussianBlur(gran, (0, 0), 1.4) * 165
    return M, R, Cc

# --- IGNITION: prizm_spectrum ---
def _ign_prizm_spectrum_paint(h, w, s):
    hue_t = _rk_n(h, w, s ^ 1, (5, 11))
    slash = np.clip(_rk_sc(h, w, s ^ 2, 5600, 0.9, 'streak', len_px=6) * 1.5, 0, 1)
    rainbow = _rk_ramp(hue_t, _rk_lut([(0.9, 0.15, 0.2), (0.95, 0.75, 0.1), (0.15, 0.75, 0.35), (0.15, 0.45, 0.9), (0.6, 0.2, 0.85)], 0.6))
    eff = rainbow * (0.45 + slash[..., None] * 0.30)
    return np.clip(eff + slash[..., None] * np.float32([0.97, 0.97, 1.0]) * 0.45, 0, 1)

def _ign_prizm_spectrum_spec(h, w, s):
    hue_t = _rk_n(h, w, s ^ 1, (5, 11))
    slash = np.clip(_rk_sc(h, w, s ^ 2, 5600, 0.9, 'streak', len_px=6) * 1.5, 0, 1)
    band = np.floor(np.clip(hue_t, 0, 0.999) * 5)
    M = 18 + slash * 237
    R = np.clip(50 + band * 40 + (_rk_n(h, w, s ^ 3, (22, 50)) - 0.5) * 30, 15, 255)
    Cc = 26 + np.clip(1 - np.abs(hue_t - 0.5) * 2.4, 0, 1) ** 2 * 150
    return M, R, Cc

# --- IGNITION: prizm_sunset_strip ---
def _ign_prizm_sunset_strip_paint(h, w, s):
    bands = np.clip(_rk_gr(h, w, s ^ 1, 3, 4.6) + (_rk_n(h, w, s ^ 2, (3, 6)) - 0.5) * 0.25, 0, 1)
    bulbs = np.clip(_rk_sc(h, w, s ^ 3, 4600, 1.0, 'dot') * 1.6, 0, 1)
    lut = _rk_lut([(0.85, 0.35, 0.15), (0.80, 0.15, 0.45), (0.10, 0.04, 0.16)], 0.6)
    eff = _rk_ramp(bands, lut)
    return np.clip(eff + bulbs[..., None] * np.float32([1.0, 0.75, 0.35]) * 0.6, 0, 1)

def _ign_prizm_sunset_strip_spec(h, w, s):
    bands = np.clip(_rk_gr(h, w, s ^ 1, 3, 4.6) + (_rk_n(h, w, s ^ 2, (3, 6)) - 0.5) * 0.25, 0, 1)
    bulbs = np.clip(_rk_sc(h, w, s ^ 3, 4600, 1.0, 'dot') * 1.6, 0, 1)
    night = np.clip((bands - 0.62) / 0.12, 0, 1)
    M = 16 + night * 236
    R = np.clip(70 + np.clip(1 - np.abs(bands - 0.35) * 3.2, 0, 1) * 120, 15, 255)
    Cc = 24 + bulbs * 175
    return M, R, Cc

# --- IGNITION: prizm_titanium ---
def _ign_prizm_titanium_paint(h, w, s):
    brush = _rk_gr(h, w, s ^ 1, 3, 2.8)
    temper = np.floor(np.clip(_rk_n(h, w, s ^ 2, (7, 15)), 0, 0.999) * 4)
    th = np.clip(temper / 4 + brush * 0.15, 0, 1)
    eff = interference_palette(th, 2.2, 0.8, base_srgb=np.float32([0.55, 0.55, 0.58]))
    burn = (temper == 3).astype(np.float32)
    return np.clip(eff * (1.0 - burn[..., None] * 0.62), 0, 1)

def _ign_prizm_titanium_spec(h, w, s):
    brush = _rk_gr(h, w, s ^ 1, 3, 2.8)
    temper = np.floor(np.clip(_rk_n(h, w, s ^ 2, (7, 15)), 0, 0.999) * 4)
    burn = (temper == 3).astype(np.float32)
    seam = np.clip(np.abs(np.diff(temper, axis=0, prepend=temper[:1])) + np.abs(np.diff(temper, axis=1, prepend=temper[:, :1])), 0, 1)
    M = 24 + burn * 231
    R = np.clip(45 + brush * 130, 15, 255)
    Cc = 24 + np.clip(cv2.GaussianBlur(seam, (0, 0), 1.2) * 2.4, 0, 1) * 170
    return M, R, Cc

# --- IGNITION: prizm_toxic_waste ---
def _ign_prizm_toxic_waste_paint(h, w, s):
    drip = np.clip(_rk_sc(h, w, s ^ 1, 7000, 1.0, 'streak', len_px=6) * 1.4, 0, 1)
    bubbles = np.clip(_rk_sc(h, w, s ^ 2, 4200, 1.4, 'dot') * 1.5, 0, 1)
    g = _rk_n(h, w, s ^ 3, (3, 6))
    base = np.float32([0.07, 0.10, 0.05])[None, None, :] * (0.6 + g[..., None] * 0.6)
    eff = base + drip[..., None] * np.float32([0.55, 0.95, 0.10]) * 0.8
    return np.clip(eff + bubbles[..., None] * np.float32([0.25, 0.40, 0.08]) * 0.35, 0, 1)

def _ign_prizm_toxic_waste_spec(h, w, s):
    drip = np.clip(_rk_sc(h, w, s ^ 1, 7000, 1.0, 'streak', len_px=6) * 1.4, 0, 1)
    bubbles = np.clip(_rk_sc(h, w, s ^ 2, 4200, 1.4, 'dot') * 1.5, 0, 1)
    g = _rk_n(h, w, s ^ 3, (3, 6))
    M = 16 + drip * 239
    R = np.clip(195 - g * 130 - bubbles * 40, 15, 255)
    Cc = 22 + bubbles * 165 + cv2.GaussianBlur(drip, (0, 0), 2.0) * 60
    return M, R, Cc

# --- IGNITION: prizm_venom ---
def _ign_prizm_venom_paint(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1300, (h * w) // 30))
    rng = np.random.default_rng(s ^ 2)
    vmask = (rng.random(int(lab.max()) + 1) > 0.62).astype(np.float32)[lab]
    pool = np.clip(1.0 - d1 / max(float(d1.max()), 1e-5), 0, 1) ** 2
    g = _rk_n(h, w, s ^ 3, (3, 7))
    acid = _rk_ramp(np.clip(pool * 0.5 + g * 0.5, 0, 1), _rk_lut([(0.12, 0.30, 0.03), (0.45, 0.80, 0.08)], 0.5))
    venom = np.float32([0.10, 0.03, 0.16])[None, None, :] * (0.5 + pool[..., None] * 0.7)
    eff = acid * (1 - vmask[..., None]) + venom * vmask[..., None]
    return np.clip(eff * (1.0 - edge[..., None] * 0.7), 0, 1)

def _ign_prizm_venom_spec(h, w, s):
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1300, (h * w) // 30))
    rng = np.random.default_rng(s ^ 2)
    vmask = (rng.random(int(lab.max()) + 1) > 0.62).astype(np.float32)[lab]
    pool = np.clip(1.0 - d1 / max(float(d1.max()), 1e-5), 0, 1) ** 2
    M = 16 + vmask * (1 - edge) * 239
    R = np.clip(60 + edge * 160 + (_rk_n(h, w, s ^ 4, (20, 46)) - 0.5) * 30, 15, 255)
    Cc = 22 + pool * 178
    return M, R, Cc

REWORK_MONOLITHICS["anime_cel_shade_chrome"] = _rw_pair("anime_cel_shade_chrome", _ign_anime_cel_shade_chrome_paint, _ign_anime_cel_shade_chrome_spec)
REWORK_MONOLITHICS["anime_speed_lines"] = _rw_pair("anime_speed_lines", _ign_anime_speed_lines_paint, _ign_anime_speed_lines_spec)
REWORK_MONOLITHICS["anime_sparkle_burst"] = _rw_pair("anime_sparkle_burst", _ign_anime_sparkle_burst_paint, _ign_anime_sparkle_burst_spec)
REWORK_MONOLITHICS["anime_gradient_hair"] = _rw_pair("anime_gradient_hair", _ign_anime_gradient_hair_paint, _ign_anime_gradient_hair_spec)
REWORK_MONOLITHICS["anime_mecha_plate"] = _rw_pair("anime_mecha_plate", _ign_anime_mecha_plate_paint, _ign_anime_mecha_plate_spec)
REWORK_MONOLITHICS["anime_sakura_scatter"] = _rw_pair("anime_sakura_scatter", _ign_anime_sakura_scatter_paint, _ign_anime_sakura_scatter_spec)
REWORK_MONOLITHICS["anime_energy_aura"] = _rw_pair("anime_energy_aura", _ign_anime_energy_aura_paint, _ign_anime_energy_aura_spec)
REWORK_MONOLITHICS["anime_comic_halftone"] = _rw_pair("anime_comic_halftone", _ign_anime_comic_halftone_paint, _ign_anime_comic_halftone_spec)
REWORK_MONOLITHICS["anime_neon_outline"] = _rw_pair("anime_neon_outline", _ign_anime_neon_outline_paint, _ign_anime_neon_outline_spec)
REWORK_MONOLITHICS["anime_crystal_facet"] = _rw_pair("anime_crystal_facet", _ign_anime_crystal_facet_paint, _ign_anime_crystal_facet_spec)
REWORK_MONOLITHICS["chameleon_amethyst"] = _rw_pair("chameleon_amethyst", _ign_chameleon_amethyst_paint, _ign_chameleon_amethyst_spec)
REWORK_MONOLITHICS["chameleon_arctic"] = _rw_pair("chameleon_arctic", _ign_chameleon_arctic_paint, _ign_chameleon_arctic_spec)
REWORK_MONOLITHICS["chameleon_aurora"] = _rw_pair("chameleon_aurora", _ign_chameleon_aurora_paint, _ign_chameleon_aurora_spec)
REWORK_MONOLITHICS["chameleon_copper"] = _rw_pair("chameleon_copper", _ign_chameleon_copper_paint, _ign_chameleon_copper_spec)
REWORK_MONOLITHICS["chameleon_emerald"] = _rw_pair("chameleon_emerald", _ign_chameleon_emerald_paint, _ign_chameleon_emerald_spec)
REWORK_MONOLITHICS["chameleon_fire"] = _rw_pair("chameleon_fire", _ign_chameleon_fire_paint, _ign_chameleon_fire_spec)
REWORK_MONOLITHICS["chameleon_frost"] = _rw_pair("chameleon_frost", _ign_chameleon_frost_paint, _ign_chameleon_frost_spec)
REWORK_MONOLITHICS["chameleon_galaxy"] = _rw_pair("chameleon_galaxy", _ign_chameleon_galaxy_paint, _ign_chameleon_galaxy_spec)
REWORK_MONOLITHICS["chameleon_midnight"] = _rw_pair("chameleon_midnight", _ign_chameleon_midnight_paint, _ign_chameleon_midnight_spec)
REWORK_MONOLITHICS["chameleon_neon"] = _rw_pair("chameleon_neon", _ign_chameleon_neon_paint, _ign_chameleon_neon_spec)
REWORK_MONOLITHICS["chameleon_obsidian"] = _rw_pair("chameleon_obsidian", _ign_chameleon_obsidian_paint, _ign_chameleon_obsidian_spec)
REWORK_MONOLITHICS["chameleon_ocean"] = _rw_pair("chameleon_ocean", _ign_chameleon_ocean_paint, _ign_chameleon_ocean_spec)
REWORK_MONOLITHICS["chameleon_phoenix"] = _rw_pair("chameleon_phoenix", _ign_chameleon_phoenix_paint, _ign_chameleon_phoenix_spec)
REWORK_MONOLITHICS["chameleon_venom"] = _rw_pair("chameleon_venom", _ign_chameleon_venom_paint, _ign_chameleon_venom_spec)
REWORK_MONOLITHICS["mystichrome"] = _rw_pair("mystichrome", _ign_mystichrome_paint, _ign_mystichrome_spec)
REWORK_MONOLITHICS["beetle_jewel"] = _rw_pair("beetle_jewel", _ign_beetle_jewel_paint, _ign_beetle_jewel_spec)
REWORK_MONOLITHICS["beetle_rainbow"] = _rw_pair("beetle_rainbow", _ign_beetle_rainbow_paint, _ign_beetle_rainbow_spec)
REWORK_MONOLITHICS["butterfly_morpho"] = _rw_pair("butterfly_morpho", _ign_butterfly_morpho_paint, _ign_butterfly_morpho_spec)
REWORK_MONOLITHICS["butterfly_monarch"] = _rw_pair("butterfly_monarch", _ign_butterfly_monarch_paint, _ign_butterfly_monarch_spec)
REWORK_MONOLITHICS["dragonfly_wing"] = _rw_pair("dragonfly_wing", _ign_dragonfly_wing_paint, _ign_dragonfly_wing_spec)
REWORK_MONOLITHICS["scarab_gold"] = _rw_pair("scarab_gold", _ign_scarab_gold_paint, _ign_scarab_gold_spec)
REWORK_MONOLITHICS["moth_luna"] = _rw_pair("moth_luna", _ign_moth_luna_paint, _ign_moth_luna_spec)
REWORK_MONOLITHICS["beetle_stag"] = _rw_pair("beetle_stag", _ign_beetle_stag_paint, _ign_beetle_stag_spec)
REWORK_MONOLITHICS["wasp_warning"] = _rw_pair("wasp_warning", _ign_wasp_warning_paint, _ign_wasp_warning_spec)
REWORK_MONOLITHICS["firefly_glow"] = _rw_pair("firefly_glow", _ign_firefly_glow_paint, _ign_firefly_glow_spec)
REWORK_MONOLITHICS["neon_pink_blaze"] = _rw_pair("neon_pink_blaze", _ign_neon_pink_blaze_paint, _ign_neon_pink_blaze_spec)
REWORK_MONOLITHICS["neon_toxic_green"] = _rw_pair("neon_toxic_green", _ign_neon_toxic_green_paint, _ign_neon_toxic_green_spec)
REWORK_MONOLITHICS["neon_electric_blue"] = _rw_pair("neon_electric_blue", _ign_neon_electric_blue_paint, _ign_neon_electric_blue_spec)
REWORK_MONOLITHICS["neon_blacklight"] = _rw_pair("neon_blacklight", _ign_neon_blacklight_paint, _ign_neon_blacklight_spec)
REWORK_MONOLITHICS["neon_orange_hazard"] = _rw_pair("neon_orange_hazard", _ign_neon_orange_hazard_paint, _ign_neon_orange_hazard_spec)
REWORK_MONOLITHICS["neon_red_alert"] = _rw_pair("neon_red_alert", _ign_neon_red_alert_paint, _ign_neon_red_alert_spec)
REWORK_MONOLITHICS["neon_cyber_yellow"] = _rw_pair("neon_cyber_yellow", _ign_neon_cyber_yellow_paint, _ign_neon_cyber_yellow_spec)
REWORK_MONOLITHICS["neon_ice_white"] = _rw_pair("neon_ice_white", _ign_neon_ice_white_paint, _ign_neon_ice_white_spec)
REWORK_MONOLITHICS["neon_dual_glow"] = _rw_pair("neon_dual_glow", _ign_neon_dual_glow_paint, _ign_neon_dual_glow_spec)
REWORK_MONOLITHICS["neon_rainbow_tube"] = _rw_pair("neon_rainbow_tube", _ign_neon_rainbow_tube_paint, _ign_neon_rainbow_tube_spec)
REWORK_MONOLITHICS["prizm_adaptive"] = _rw_pair("prizm_adaptive", _ign_prizm_adaptive_paint, _ign_prizm_adaptive_spec)
REWORK_MONOLITHICS["prizm_alien_skin"] = _rw_pair("prizm_alien_skin", _ign_prizm_alien_skin_paint, _ign_prizm_alien_skin_spec)
REWORK_MONOLITHICS["prizm_arctic"] = _rw_pair("prizm_arctic", _ign_prizm_arctic_paint, _ign_prizm_arctic_spec)
REWORK_MONOLITHICS["prizm_aurora_shift"] = _rw_pair("prizm_aurora_shift", _ign_prizm_aurora_shift_paint, _ign_prizm_aurora_shift_spec)
REWORK_MONOLITHICS["prizm_black_rainbow"] = _rw_pair("prizm_black_rainbow", _ign_prizm_black_rainbow_paint, _ign_prizm_black_rainbow_spec)
REWORK_MONOLITHICS["prizm_blood_moon"] = _rw_pair("prizm_blood_moon", _ign_prizm_blood_moon_paint, _ign_prizm_blood_moon_spec)
REWORK_MONOLITHICS["prizm_candy_paint"] = _rw_pair("prizm_candy_paint", _ign_prizm_candy_paint_paint, _ign_prizm_candy_paint_spec)
REWORK_MONOLITHICS["prizm_chrome_rose"] = _rw_pair("prizm_chrome_rose", _ign_prizm_chrome_rose_paint, _ign_prizm_chrome_rose_spec)
REWORK_MONOLITHICS["prizm_copper_flame"] = _rw_pair("prizm_copper_flame", _ign_prizm_copper_flame_paint, _ign_prizm_copper_flame_spec)
REWORK_MONOLITHICS["prizm_cosmos"] = _rw_pair("prizm_cosmos", _ign_prizm_cosmos_paint, _ign_prizm_cosmos_spec)
REWORK_MONOLITHICS["prizm_dark_matter"] = _rw_pair("prizm_dark_matter", _ign_prizm_dark_matter_paint, _ign_prizm_dark_matter_spec)
REWORK_MONOLITHICS["prizm_deep_space"] = _rw_pair("prizm_deep_space", _ign_prizm_deep_space_paint, _ign_prizm_deep_space_spec)
REWORK_MONOLITHICS["prizm_duochrome"] = _rw_pair("prizm_duochrome", _ign_prizm_duochrome_paint, _ign_prizm_duochrome_spec)
REWORK_MONOLITHICS["prizm_ember"] = _rw_pair("prizm_ember", _ign_prizm_ember_paint, _ign_prizm_ember_spec)
REWORK_MONOLITHICS["prizm_fire_ice"] = _rw_pair("prizm_fire_ice", _ign_prizm_fire_ice_paint, _ign_prizm_fire_ice_spec)
REWORK_MONOLITHICS["prizm_galaxy_dust"] = _rw_pair("prizm_galaxy_dust", _ign_prizm_galaxy_dust_paint, _ign_prizm_galaxy_dust_spec)
REWORK_MONOLITHICS["prizm_holographic"] = _rw_pair("prizm_holographic", _ign_prizm_holographic_paint, _ign_prizm_holographic_spec)
REWORK_MONOLITHICS["prizm_iridescent"] = _rw_pair("prizm_iridescent", _ign_prizm_iridescent_paint, _ign_prizm_iridescent_spec)
REWORK_MONOLITHICS["prizm_midnight"] = _rw_pair("prizm_midnight", _ign_prizm_midnight_paint, _ign_prizm_midnight_spec)
REWORK_MONOLITHICS["prizm_mystichrome"] = _rw_pair("prizm_mystichrome", _ign_prizm_mystichrome_paint, _ign_prizm_mystichrome_spec)
REWORK_MONOLITHICS["prizm_neon"] = _rw_pair("prizm_neon", _ign_prizm_neon_paint, _ign_prizm_neon_spec)
REWORK_MONOLITHICS["prizm_oceanic"] = _rw_pair("prizm_oceanic", _ign_prizm_oceanic_paint, _ign_prizm_oceanic_spec)
REWORK_MONOLITHICS["prizm_phoenix"] = _rw_pair("prizm_phoenix", _ign_prizm_phoenix_paint, _ign_prizm_phoenix_spec)
REWORK_MONOLITHICS["prizm_solar"] = _rw_pair("prizm_solar", _ign_prizm_solar_paint, _ign_prizm_solar_spec)
REWORK_MONOLITHICS["prizm_spectrum"] = _rw_pair("prizm_spectrum", _ign_prizm_spectrum_paint, _ign_prizm_spectrum_spec)
REWORK_MONOLITHICS["prizm_sunset_strip"] = _rw_pair("prizm_sunset_strip", _ign_prizm_sunset_strip_paint, _ign_prizm_sunset_strip_spec)
REWORK_MONOLITHICS["prizm_titanium"] = _rw_pair("prizm_titanium", _ign_prizm_titanium_paint, _ign_prizm_titanium_spec)
REWORK_MONOLITHICS["prizm_toxic_waste"] = _rw_pair("prizm_toxic_waste", _ign_prizm_toxic_waste_paint, _ign_prizm_toxic_waste_spec)
REWORK_MONOLITHICS["prizm_venom"] = _rw_pair("prizm_venom", _ign_prizm_venom_paint, _ign_prizm_venom_spec)
# === IGNITION REBUILD 2026-06-10 END ===


# === IGN CALIB 2026-06-10 START ===

def _ign_ss_build(build, f):
    def b(h, w, s, _b=build, _f=f):
        import numpy as _np, cv2 as _cv
        H, W = int(round(h * _f)), int(round(w * _f))
        out = _b(H, W, s)

        def rs(a):
            if not hasattr(a, "ndim") or getattr(a, "ndim", 0) < 2:
                return a
            return _cv.resize(_np.asarray(a, _np.float32), (w, h), interpolation=_cv.INTER_AREA)
        if isinstance(out, tuple):
            return tuple(rs(a) for a in out)
        return rs(out)
    return b


def _ign_crush_build(build, amp=0.55):
    def b(h, w, s, _b=build, _a=amp):
        import numpy as _np
        out = _np.asarray(_b(h, w, s), _np.float32)
        g = _np.asarray(_rk_n(h, w, (int(s) ^ 0xC4C4C4) & 0x7FFFFFFF, (2, 4)), _np.float32)
        fleck = _np.clip((g - 0.42) * 5.0, 0.0, 1.0)
        return _np.clip(out * (1.0 + (fleck - float(fleck.mean())) * _a)[..., None], 0.0, 1.0)
    return b



def _ign_knee_packed(fn, ch, t_pct=92.0):
    """LEDGE remap: pixels above the t_pct percentile land on 210-255 (guaranteed
    ignition); an over-bright sub-ledge body is scaled under 195 for calm."""
    def f(shape, mask, seed, sm, _f=fn, _c=ch, _t=t_pct):
        import numpy as _np
        out = _f(shape, mask, seed, sm)
        c = out[:, :, _c].astype(_np.float32)
        # deterministic micro-dither breaks ties so flat-bright channels still
        # ledge their top 8% (reads as fine metal-flake sparkle, not a wall)
        c = c + _np.random.default_rng(0x1D17).random(c.shape).astype(_np.float32)
        sel = out[:, :, 3] > 0
        t = float(_np.percentile(c[sel] if sel.any() else c, _t))
        cmax = float(c.max())
        low = c * (195.0 / t) if t > 195.0 else c
        hi = 210.0 + 45.0 * (c - t) / max(1e-3, cmax - t)
        out[:, :, _c] = _np.clip(_np.where(c >= t, hi, low), 0, 255).astype(_np.uint8)
        return out
    return f


def _ign_crush_paint(fn, amp=0.50):
    """SHARP-edged 4-8px micro-fleck layer multiplied into the painted region —
    hard transitions carry the fine gradient energy the fineness metric reads
    (smooth grain does not move it)."""
    def f(paint, shape, mask, seed, pm, bb, _f=fn, _a=amp):
        import numpy as _np
        out = _f(paint, shape, mask, seed, pm, bb)
        fh, fw = _shape2(shape)
        wh, ww = min(fh, 1024), min(fw, 1024)
        g = _np.asarray(_msc(wh, ww, [2, 4], (int(seed) ^ 0xC4C4C4) & 0x7FFFFFFF), _np.float32)
        fleck = _np.clip((g - 0.42) * 5.0, 0.0, 1.0)
        fleck = _upscale(fleck, fh, fw)
        mk = _mask2(mask, fh, fw)
        mod = 1.0 + (fleck - float(fleck.mean())) * _a * mk
        out = _np.clip(_np.asarray(out, _np.float32) * mod[..., None], 0.0, 1.0)
        return out.astype(_np.float32)
    return f


REWORK_MONOLITHICS["butterfly_monarch"] = _rw_pair("butterfly_monarch", _ign_crush_build(_ign_ss_build(_ign_butterfly_monarch_paint, 1.43)), _ign_ss_build(_ign_butterfly_monarch_spec, 1.43))

REWORK_MONOLITHICS["scarab_gold"] = _rw_pair("scarab_gold", _ign_crush_build(_ign_ss_build(_ign_scarab_gold_paint, 1.44)), _ign_ss_build(_ign_scarab_gold_spec, 1.44))

REWORK_MONOLITHICS["moth_luna"] = _rw_pair("moth_luna", _ign_crush_build(_ign_ss_build(_ign_moth_luna_paint, 1.41)), _ign_ss_build(_ign_moth_luna_spec, 1.41))

REWORK_MONOLITHICS["wasp_warning"] = _rw_pair("wasp_warning", _ign_crush_build(_ign_ss_build(_ign_wasp_warning_paint, 1.39)), _ign_ss_build(_ign_wasp_warning_spec, 1.39))

REWORK_MONOLITHICS["firefly_glow"] = _rw_pair("firefly_glow", _ign_crush_build(_ign_ss_build(_ign_firefly_glow_paint, 1.39)), _ign_ss_build(_ign_firefly_glow_spec, 1.39))

REWORK_MONOLITHICS["anime_energy_aura"] = _rw_pair("anime_energy_aura", _ign_crush_build(_ign_ss_build(_ign_anime_energy_aura_paint, 1.42)), _ign_ss_build(_ign_anime_energy_aura_spec, 1.42))

REWORK_MONOLITHICS["anime_neon_outline"] = _rw_pair("anime_neon_outline", _ign_crush_build(_ign_ss_build(_ign_anime_neon_outline_paint, 1.37)), _ign_ss_build(_ign_anime_neon_outline_spec, 1.37))

REWORK_MONOLITHICS["anime_neon_outline"] = (_ign_knee_packed(REWORK_MONOLITHICS["anime_neon_outline"][0], 2), REWORK_MONOLITHICS["anime_neon_outline"][1])

REWORK_MONOLITHICS["neon_toxic_green"] = _rw_pair("neon_toxic_green", _ign_crush_build(_ign_ss_build(_ign_neon_toxic_green_paint, 1.49)), _ign_ss_build(_ign_neon_toxic_green_spec, 1.49))

REWORK_MONOLITHICS["neon_toxic_green"] = (_ign_knee_packed(REWORK_MONOLITHICS["neon_toxic_green"][0], 2), REWORK_MONOLITHICS["neon_toxic_green"][1])

REWORK_MONOLITHICS["neon_electric_blue"] = _rw_pair("neon_electric_blue", _ign_crush_build(_ign_ss_build(_ign_neon_electric_blue_paint, 1.36)), _ign_ss_build(_ign_neon_electric_blue_spec, 1.36))

REWORK_MONOLITHICS["neon_electric_blue"] = (_ign_knee_packed(REWORK_MONOLITHICS["neon_electric_blue"][0], 2), REWORK_MONOLITHICS["neon_electric_blue"][1])

REWORK_MONOLITHICS["neon_blacklight"] = _rw_pair("neon_blacklight", _ign_crush_build(_ign_ss_build(_ign_neon_blacklight_paint, 1.34)), _ign_ss_build(_ign_neon_blacklight_spec, 1.34))

REWORK_MONOLITHICS["neon_blacklight"] = (_ign_knee_packed(REWORK_MONOLITHICS["neon_blacklight"][0], 2), REWORK_MONOLITHICS["neon_blacklight"][1])

REWORK_MONOLITHICS["neon_red_alert"] = _rw_pair("neon_red_alert", _ign_crush_build(_ign_ss_build(_ign_neon_red_alert_paint, 1.36)), _ign_ss_build(_ign_neon_red_alert_spec, 1.36))

REWORK_MONOLITHICS["neon_red_alert"] = (_ign_knee_packed(REWORK_MONOLITHICS["neon_red_alert"][0], 0), REWORK_MONOLITHICS["neon_red_alert"][1])

REWORK_MONOLITHICS["neon_cyber_yellow"] = _rw_pair("neon_cyber_yellow", _ign_crush_build(_ign_ss_build(_ign_neon_cyber_yellow_paint, 1.4)), _ign_ss_build(_ign_neon_cyber_yellow_spec, 1.4))

REWORK_MONOLITHICS["neon_cyber_yellow"] = (_ign_knee_packed(REWORK_MONOLITHICS["neon_cyber_yellow"][0], 0), REWORK_MONOLITHICS["neon_cyber_yellow"][1])

REWORK_MONOLITHICS["neon_rainbow_tube"] = _rw_pair("neon_rainbow_tube", _ign_crush_build(_ign_ss_build(_ign_neon_rainbow_tube_paint, 1.4)), _ign_ss_build(_ign_neon_rainbow_tube_spec, 1.4))

REWORK_MONOLITHICS["neon_rainbow_tube"] = (_ign_knee_packed(REWORK_MONOLITHICS["neon_rainbow_tube"][0], 0), REWORK_MONOLITHICS["neon_rainbow_tube"][1])

REWORK_MONOLITHICS["mystichrome"] = _rw_pair("mystichrome", _ign_crush_build(_ign_ss_build(_ign_mystichrome_paint, 1.51)), _ign_ss_build(_ign_mystichrome_spec, 1.51))

REWORK_MONOLITHICS["prizm_dark_matter"] = _rw_pair("prizm_dark_matter", _ign_crush_build(_ign_ss_build(_ign_prizm_dark_matter_paint, 1.39)), _ign_ss_build(_ign_prizm_dark_matter_spec, 1.39))

REWORK_MONOLITHICS["prizm_fire_ice"] = _rw_pair("prizm_fire_ice", _ign_crush_build(_ign_ss_build(_ign_prizm_fire_ice_paint, 1.47)), _ign_ss_build(_ign_prizm_fire_ice_spec, 1.47))

REWORK_MONOLITHICS["prizm_iridescent"] = _rw_pair("prizm_iridescent", _ign_crush_build(_ign_ss_build(_ign_prizm_iridescent_paint, 1.36)), _ign_ss_build(_ign_prizm_iridescent_spec, 1.36))

REWORK_MONOLITHICS["prizm_iridescent"] = (_ign_knee_packed(REWORK_MONOLITHICS["prizm_iridescent"][0], 2), REWORK_MONOLITHICS["prizm_iridescent"][1])

REWORK_MONOLITHICS["prizm_midnight"] = _rw_pair("prizm_midnight", _ign_crush_build(_ign_ss_build(_ign_prizm_midnight_paint, 1.34)), _ign_ss_build(_ign_prizm_midnight_spec, 1.34))

REWORK_MONOLITHICS["prizm_midnight"] = (_ign_knee_packed(REWORK_MONOLITHICS["prizm_midnight"][0], 2), REWORK_MONOLITHICS["prizm_midnight"][1])

REWORK_MONOLITHICS["prizm_neon"] = _rw_pair("prizm_neon", _ign_crush_build(_ign_ss_build(_ign_prizm_neon_paint, 1.36)), _ign_ss_build(_ign_prizm_neon_spec, 1.36))

REWORK_MONOLITHICS["prizm_neon"] = (_ign_knee_packed(REWORK_MONOLITHICS["prizm_neon"][0], 0), REWORK_MONOLITHICS["prizm_neon"][1])

REWORK_MONOLITHICS["beetle_rainbow"] = _rw_pair("beetle_rainbow", _ign_crush_build(_ign_ss_build(_ign_beetle_rainbow_paint, 1.36)), _ign_ss_build(_ign_beetle_rainbow_spec, 1.36))

REWORK_MONOLITHICS["beetle_rainbow"] = (_ign_knee_packed(REWORK_MONOLITHICS["beetle_rainbow"][0], 0), REWORK_MONOLITHICS["beetle_rainbow"][1])

REWORK_MONOLITHICS["dragonfly_wing"] = _rw_pair("dragonfly_wing", _ign_crush_build(_ign_ss_build(_ign_dragonfly_wing_paint, 1.38)), _ign_ss_build(_ign_dragonfly_wing_spec, 1.38))

REWORK_MONOLITHICS["dragonfly_wing"] = (_ign_knee_packed(REWORK_MONOLITHICS["dragonfly_wing"][0], 0), REWORK_MONOLITHICS["dragonfly_wing"][1])

REWORK_MONOLITHICS["neon_pink_blaze"] = (_ign_knee_packed(REWORK_MONOLITHICS["neon_pink_blaze"][0], 0), REWORK_MONOLITHICS["neon_pink_blaze"][1])

REWORK_MONOLITHICS["neon_ice_white"] = (_ign_knee_packed(REWORK_MONOLITHICS["neon_ice_white"][0], 0), REWORK_MONOLITHICS["neon_ice_white"][1])

REWORK_MONOLITHICS["chameleon_aurora"] = (_ign_knee_packed(REWORK_MONOLITHICS["chameleon_aurora"][0], 2), REWORK_MONOLITHICS["chameleon_aurora"][1])

REWORK_MONOLITHICS["chameleon_frost"] = (_ign_knee_packed(REWORK_MONOLITHICS["chameleon_frost"][0], 0), REWORK_MONOLITHICS["chameleon_frost"][1])

REWORK_MONOLITHICS["prizm_black_rainbow"] = (_ign_knee_packed(REWORK_MONOLITHICS["prizm_black_rainbow"][0], 0), REWORK_MONOLITHICS["prizm_black_rainbow"][1])

REWORK_MONOLITHICS["prizm_blood_moon"] = (_ign_knee_packed(REWORK_MONOLITHICS["prizm_blood_moon"][0], 2), REWORK_MONOLITHICS["prizm_blood_moon"][1])

REWORK_MONOLITHICS["prizm_copper_flame"] = (_ign_knee_packed(REWORK_MONOLITHICS["prizm_copper_flame"][0], 2), REWORK_MONOLITHICS["prizm_copper_flame"][1])

REWORK_MONOLITHICS["prizm_mystichrome"] = (_ign_knee_packed(REWORK_MONOLITHICS["prizm_mystichrome"][0], 2), REWORK_MONOLITHICS["prizm_mystichrome"][1])

REWORK_MONOLITHICS["prizm_oceanic"] = (_ign_knee_packed(REWORK_MONOLITHICS["prizm_oceanic"][0], 0), REWORK_MONOLITHICS["prizm_oceanic"][1])

REWORK_MONOLITHICS["prizm_solar"] = (_ign_knee_packed(REWORK_MONOLITHICS["prizm_solar"][0], 0), REWORK_MONOLITHICS["prizm_solar"][1])

REWORK_MONOLITHICS["prizm_spectrum"] = (_ign_knee_packed(REWORK_MONOLITHICS["prizm_spectrum"][0], 0), REWORK_MONOLITHICS["prizm_spectrum"][1])

REWORK_MONOLITHICS["prizm_toxic_waste"] = (_ign_knee_packed(REWORK_MONOLITHICS["prizm_toxic_waste"][0], 0), REWORK_MONOLITHICS["prizm_toxic_waste"][1])

REWORK_MONOLITHICS["beetle_jewel"] = _rw_pair("beetle_jewel", _ign_crush_build(_ign_ss_build(_ign_beetle_jewel_paint, 1.51)), _ign_ss_build(_ign_beetle_jewel_spec, 1.51))

REWORK_MONOLITHICS["anime_speed_lines"] = _rw_pair("anime_speed_lines", _ign_crush_build(_ign_ss_build(_ign_anime_speed_lines_paint, 1.34)), _ign_ss_build(_ign_anime_speed_lines_spec, 1.34))

REWORK_MONOLITHICS["anime_speed_lines"] = (_ign_knee_packed(REWORK_MONOLITHICS["anime_speed_lines"][0], 0), REWORK_MONOLITHICS["anime_speed_lines"][1])

REWORK_MONOLITHICS["anime_gradient_hair"] = (_ign_knee_packed(REWORK_MONOLITHICS["anime_gradient_hair"][0], 2), REWORK_MONOLITHICS["anime_gradient_hair"][1])

REWORK_MONOLITHICS["anime_crystal_facet"] = _rw_pair("anime_crystal_facet", _ign_crush_build(_ign_ss_build(_ign_anime_crystal_facet_paint, 1.51)), _ign_ss_build(_ign_anime_crystal_facet_spec, 1.51))

REWORK_MONOLITHICS["chameleon_copper"] = _rw_pair("chameleon_copper", _ign_crush_build(_ign_ss_build(_ign_chameleon_copper_paint, 1.52)), _ign_ss_build(_ign_chameleon_copper_spec, 1.52))

REWORK_MONOLITHICS["chameleon_ocean"] = (_ign_knee_packed(REWORK_MONOLITHICS["chameleon_ocean"][0], 0), REWORK_MONOLITHICS["chameleon_ocean"][1])

REWORK_MONOLITHICS["chameleon_phoenix"] = (_ign_knee_packed(REWORK_MONOLITHICS["chameleon_phoenix"][0], 0), REWORK_MONOLITHICS["chameleon_phoenix"][1])

REWORK_MONOLITHICS["prizm_adaptive"] = _rw_pair("prizm_adaptive", _ign_crush_build(_ign_ss_build(_ign_prizm_adaptive_paint, 1.49)), _ign_ss_build(_ign_prizm_adaptive_spec, 1.49))

REWORK_MONOLITHICS["prizm_aurora_shift"] = (_ign_knee_packed(REWORK_MONOLITHICS["prizm_aurora_shift"][0], 0), REWORK_MONOLITHICS["prizm_aurora_shift"][1])

REWORK_MONOLITHICS["prizm_holographic"] = (_ign_knee_packed(REWORK_MONOLITHICS["prizm_holographic"][0], 0), REWORK_MONOLITHICS["prizm_holographic"][1])
# === IGN CALIB 2026-06-10 END ===


# ═══ 2026-06-21 COLOR SCIENCE REDIRECT — FINAL chameleon override (after ALL prior
# layers: original / _f4 / IGN-fire / IGN-knee). This MUST be the last chameleon write
# in the module so every chameleon ships the elaborate color_science_2026 spec. ═══
_apply_chameleon_color_science()
