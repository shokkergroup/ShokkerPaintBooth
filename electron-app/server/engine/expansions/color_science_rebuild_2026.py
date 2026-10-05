# ============================================================================
# engine/expansions/color_science_rebuild_2026.py
# ----------------------------------------------------------------------------
# OWNER MANDATE 2026-06-21 (post-freeze): TOTAL rebuild of the COLOR SCIENCE
# groups. The paint MUST match its name, every finish + spec must be UNIQUE
# (no shared mechanic recolored), and the spec must TRACE the paint's own
# field. This module is installed DEAD-LAST (after colorshift_rework_2026 and
# owner_review_gradients) so its ids win, in BOTH MONOLITHIC and BASE
# registries (see shokker_engine_v2._spb_apply_color_science_rebuild_2026).
#
# Wave 1 = CHAMELEON (15). Each finish gets a DISTINCT structural engine
# (voronoi shards / caustics / curtains / patina-flow / cleavage facets /
# flame petals / dendrite ferns / nebula spiral / dark starfield / neon tubes
# / fracture plates / ocean swell / feather plume / dragonscale / chrome flow)
# plus a name-themed multi-hue TRAVEL (interference overlay = the chameleon
# shift). The spec re-reads the SAME fields so M/R/Cc ride decorrelated
# aspects of one geometry (paint + spec work together).
#
# CONTRACT (mirrors colorshift_rework_2026):
#   REBUILD_MONOLITHICS[id] = (spec_fn, paint_fn)
#   builders: paint_build(h,w,s) -> HxWx3 float [0,1]
#             spec_build(h,w,s)  -> (M, R, Cc) float arrays (work-res)
# Gates targeted: uniqueness<80%, |corr|<0.85, iron (R>=15, Cc>=16), <3s@2048,
#   M.std>=~20, full coverage + crushed fine detail (rule #0b).
# 2-copy file (root -> electron-app/server).
# ============================================================================
from __future__ import annotations

import numpy as np
import cv2

from engine.color_science import interference_palette, tri_partition, flip_lattice
from engine.recipe_kit import (
    micro_scatter as _sc, micro_voronoi as _vor, filament_web as _web,
    flow_grain as _gr, ring_swarm as _rings, ramp_lut as _lut,
    ramp_apply as _ramp, per_label_lut as _cell, noise01 as _n,
)
from engine.paint_v2.color_science_2026 import (
    ripple_caustics as _caustics, crystal_facets as _facets,
    oilslick_thinfilm as _oilslick, iridescent_flow as _iflow,
    spectral_spiral as _spiral, holographic_mosaic as _holo,
)
from engine.paint_v2.fable_collection import (
    _shape2, _seed_of, _work_shape, _mask2, _upscale, _pack_spec, _blend_paint,
)
from engine.spec_sculpt.fracture import fracture_spec as _fracture_spec
import hashlib


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------
def _n01(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    lo = float(a.min()); rng = float(np.ptp(a))
    return np.zeros_like(a) if rng < 1e-9 else (a - lo) / rng


def _label_rng(seed: int, lab: np.ndarray) -> np.ndarray:
    """Per-voronoi-cell random value in 0..1, broadcast back to the pixel grid."""
    r = np.random.default_rng(int(seed) & 0xFFFFFFFF).random(int(lab.max()) + 1).astype(np.float32)
    return r[lab]


def _travel(field, stops, *, irid=0.30, cycles=2.4, sat=0.7, smooth=0.5, base=None):
    """Chameleon color-TRAVEL: a smooth name-themed multi-stop ramp over `field`
    with an iridescent thin-film overlay (the angle-shift shimmer). `stops` is a
    list of sRGB triples the hue walks through."""
    f = np.clip(field, 0, 1).astype(np.float32)
    col = _ramp(f, _lut([tuple(c) for c in stops], smooth))
    if irid > 0.0:
        b = base if base is not None else np.float32([0.10, 0.10, 0.12])
        irf = interference_palette(f, cycles, sat, base_srgb=np.float32(b))[..., :3]
        col = np.clip(col * (1.0 - irid) + irf * irid, 0, 1)
    return np.clip(col, 0, 1).astype(np.float32)


def _pair(fid, paint_build, spec_build):
    """Wrap simple (h,w,s) builders into the monolithic (spec_fn, paint_fn) contract."""
    def spec_fn(shape, mask, seed, sm, _b=spec_build, _f=fid):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        M, R, Cc = _b(h, w, _seed_of(_f, seed))
        # dynamism backstop: a flat metallic channel reads dead on the car.
        _msd = float(np.std(M))
        if 1e-3 < _msd < 20.0:
            _mm = float(np.mean(M)); M = np.clip(_mm + (M - _mm) * (20.0 / _msd), 0, 255)
        M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
        return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)

    def paint_fn(paint, shape, mask, seed, pm, bb, _b=paint_build, _f=fid):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        eff = np.clip(_b(h, w, _seed_of(_f, seed)), 0, 1)
        # gentle high-freq micro-lighting so the body never reads flat (coverage+fineness)
        eff = np.clip(eff * (0.72 + _n(h, w, _seed_of(_f, seed) ^ 0x5A, (3, 7))[..., None] * 0.52), 0, 1)
        return _blend_paint(paint, _upscale(eff, fh, fw), _mask2(mask, fh, fw), pm)

    return spec_fn, paint_fn


# ===========================================================================
# CHAMELEON — 15 finishes, each a distinct engine + name-matched hue travel
# ===========================================================================

# --- amethyst: crystal geode shards, violet->magenta->indigo travel ---------
def _amethyst_paint(h, w, s):
    lab, d1, edge = _vor(h, w, s ^ 1, max(1400, (h * w) // 70))
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    tilt = _label_rng(s ^ 2, lab)
    phase = np.clip(tilt * 0.65 + (1 - d1n) * 0.45 + _n(h, w, s ^ 3, (4, 9)) * 0.22, 0, 1)
    col = _travel(phase, [(0.16, 0.04, 0.30), (0.42, 0.06, 0.55), (0.58, 0.10, 0.42), (0.22, 0.10, 0.55)],
                  irid=0.36, cycles=3.0, sat=0.85, base=(0.10, 0.03, 0.18))
    glint = edge ** 2.0
    return np.clip(col * (1 - edge[..., None] * 0.5) + glint[..., None] * np.float32([0.9, 0.7, 1.0]) * 0.4, 0, 1)

def _amethyst_spec(h, w, s):
    lab, d1, edge = _vor(h, w, s ^ 1, max(1400, (h * w) // 70))
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    tilt = _label_rng(s ^ 2, lab)
    M = 14 + (tilt > 0.58).astype(np.float32) * (1 - edge) * 238          # bright facets mirror-flip
    R = np.clip(70 + edge * 150 - tilt * 30, 15, 255)                     # facet edges = satin corridors
    Cc = np.clip(22 + (1 - d1n) ** 2 * 150 + edge * 20, 16, 255)          # facet centers = wet pools
    return M, R, Cc


# --- arctic: ice caustics + frost cracks, pale cyan->teal->white travel ------
def _arctic_paint(h, w, s):
    st, sh = _caustics(h, w, s ^ 1, rings=11.0)
    cracks = _web(h, w, s ^ 2, 5000, k=2, intensity=(0.4, 1.0))
    phase = np.clip(st * 0.7 + _n(h, w, s ^ 3, (4, 9)) * 0.3, 0, 1)
    col = _travel(phase, [(0.50, 0.70, 0.86), (0.38, 0.64, 0.78), (0.80, 0.86, 0.94), (0.62, 0.60, 0.84)],
                  irid=0.26, cycles=2.2, sat=0.5, base=(0.30, 0.40, 0.55))
    return np.clip(col * (1 - cracks[..., None] * 0.4) + cracks[..., None] * np.float32([0.85, 0.93, 1.0]) * 0.5, 0, 1)

def _arctic_spec(h, w, s):
    st, sh = _caustics(h, w, s ^ 1, rings=11.0)
    cracks = _web(h, w, s ^ 2, 5000, k=2, intensity=(0.4, 1.0))
    g = _n(h, w, s ^ 3, (9, 19))                                         # independent frost grain (R's own field)
    M = 16 + np.clip(cracks * 2.0, 0, 1) * 236                            # cracks ignite silver
    R = np.clip(60 + g * 150 - cracks * 30, 15, 255)                      # frost grain, not the caustic field
    Cc = np.clip(22 + st * 150 + cv2.GaussianBlur(cracks, (0, 0), 2.0) * 50, 16, 255)  # caustic pools
    return M, R, Cc


# --- aurora: vertical curtains, green->cyan->violet->magenta travel ----------
def _aurora_paint(h, w, s):
    cur = _gr(h, w, s ^ 1, 3, 4.4)
    crest = np.clip((cur - 0.66) * 4.0, 0, 1)
    thr = _sc(h, w, s ^ 2, 5200, 0.9, "streak", len_px=6)
    phase = np.clip(cur * 0.9 + _n(h, w, s ^ 3, (3, 7)) * 0.2, 0, 1)
    col = _travel(phase, [(0.03, 0.34, 0.18), (0.04, 0.30, 0.45), (0.20, 0.10, 0.50), (0.45, 0.08, 0.45)],
                  irid=0.30, cycles=2.6, sat=0.85, base=(0.02, 0.06, 0.10))
    col = col + crest[..., None] * np.float32([0.30, 0.95, 0.55]) * 0.5 + thr[..., None] * np.float32([0.7, 0.9, 0.8]) * 0.22
    return np.clip(col, 0, 1)

def _aurora_spec(h, w, s):
    cur = _gr(h, w, s ^ 1, 3, 4.4)
    crest = np.clip((cur - 0.66) * 4.0, 0, 1)
    thr = _sc(h, w, s ^ 2, 5200, 0.9, "streak", len_px=6)
    g = _gr(h, w, s ^ 3, 4, 3.0)                                         # broad shimmer field for M
    Cc = np.clip(26 + crest * 225, 16, 255)                               # crest lines flash wet
    M = np.clip(18 + thr * 165 + g * 120, 0, 255)                         # threads + broad shimmer (decorrelated from crest)
    R = np.clip(185 - cur * 125 - thr * 25, 15, 255)
    return M, R, Cc


# --- copper: oxidation patina flow, copper->verdigris travel -----------------
def _copper_paint(h, w, s):
    fl, shf = _iflow(h, w, s ^ 1, scale=4.0)
    veins = _web(h, w, s ^ 2, 3500, k=3, intensity=(0.3, 1.0))
    phase = np.clip(fl * 0.8 + veins * 0.3, 0, 1)
    col = _travel(phase, [(0.58, 0.30, 0.10), (0.68, 0.42, 0.16), (0.10, 0.44, 0.36), (0.18, 0.52, 0.40)],
                  irid=0.20, cycles=2.0, sat=0.6, base=(0.30, 0.18, 0.08))
    return np.clip(col * (1 - veins[..., None] * 0.35), 0, 1)

def _copper_spec(h, w, s):
    fl, shf = _iflow(h, w, s ^ 1, scale=4.0)
    veins = _web(h, w, s ^ 2, 3500, k=3, intensity=(0.3, 1.0))
    M = 16 + np.clip(fl * 1.6, 0, 1) * 150 + shf * 60                     # patina sheen rolls with the flow
    R = np.clip(80 + veins * 140 - fl * 30, 15, 255)                      # corroded veins = matte corridors
    Cc = np.clip(22 + (1 - veins) * fl * 150, 16, 255)
    return M, R, Cc


# --- emerald: cleavage-plane gem facets, green->gold->cyan travel ------------
def _emerald_paint(h, w, s):
    st, sh = _facets(h, w, s ^ 1, cells=46.0)
    band = _gr(h, w, s ^ 2, 5, 2.6)
    phase = np.clip(st * 0.7 + band * 0.3, 0, 1)
    col = _travel(phase, [(0.02, 0.34, 0.16), (0.05, 0.48, 0.24), (0.32, 0.50, 0.10), (0.08, 0.42, 0.40)],
                  irid=0.28, cycles=2.6, sat=0.78, base=(0.02, 0.16, 0.08))
    gold = np.clip((st - 0.7) * 3, 0, 1)[..., None] * np.float32([0.85, 0.70, 0.20])
    return np.clip(col + gold * 0.35, 0, 1)

def _emerald_spec(h, w, s):
    st, sh = _facets(h, w, s ^ 1, cells=46.0)
    band = _gr(h, w, s ^ 2, 5, 2.6)
    g = _n(h, w, s ^ 3, (10, 22))                                        # independent grain (Cc's own field)
    M = 14 + np.clip((st - 0.5) * 2.4, 0, 1) * 236                        # gem flash on the cleavage planes
    R = np.clip(60 + band * 130 + sh * 40, 15, 255)                       # cleavage banding
    Cc = np.clip(20 + g * 120 + (1 - band) * 60, 16, 255)                 # grain + band valleys (not st)
    return M, R, Cc


# --- fire: flame tongues red->orange->gold + chameleon violet flicker --------
def _fire_paint(h, w, s):
    tongues = _sc(h, w, s ^ 1, 9000, 4.5, "petal", amp=(0.6, 1.0))
    sil = np.clip(tongues * 2.4, 0, 1)
    tips = np.clip((tongues - 0.45) * 2.5, 0, 1)
    embers = _sc(h, w, s ^ 2, 3500, 0.7, "dot")
    phase = np.clip(sil * 0.85 + _n(h, w, s ^ 3, (4, 9)) * 0.2, 0, 1)
    col = _travel(phase, [(0.30, 0.02, 0.03), (0.78, 0.16, 0.03), (0.98, 0.55, 0.08), (1.0, 0.85, 0.40)],
                  irid=0.16, cycles=1.8, sat=0.7, base=(0.12, 0.02, 0.02))
    twist = np.clip((tongues - 0.8) * 4, 0, 1)[..., None] * np.float32([0.4, 0.05, 0.5])
    return np.clip(col + tips[..., None] * np.float32([1.0, 0.85, 0.35]) * 0.5 + embers[..., None] * 0.4 + twist * 0.3, 0, 1)

def _fire_spec(h, w, s):
    tongues = _sc(h, w, s ^ 1, 9000, 4.5, "petal", amp=(0.6, 1.0))
    sil = np.clip(tongues * 2.4, 0, 1)
    tips = np.clip((tongues - 0.45) * 2.5, 0, 1)
    embers = _sc(h, w, s ^ 2, 3500, 0.7, "dot")
    g = _n(h, w, s ^ 3, (4, 9))
    g2 = _gr(h, w, s ^ 5, 4, 3.0)                                         # broad heat-shimmer field for M
    Cc = np.clip(24 + np.clip(tongues * 4.6, 0, 1) * 230, 16, 255)        # flame bodies flash
    M = np.clip(14 + embers * 160 + g2 * 120 + tips * 40, 0, 255)         # embers + broad heat (decorrelated from flames)
    R = np.clip(80 + g * 130 - sil * 55, 15, 255)                         # smoke pools between flames
    return M, R, Cc


# --- frost: dendrite ferns, white->cyan->pale-violet travel ------------------
def _frost_paint(h, w, s):
    fern = _web(h, w, s ^ 1, 7000, k=2, intensity=(0.45, 1.0))
    swell = _n(h, w, s ^ 2, (3, 7))
    phase = np.clip(swell * 0.6 + fern * 0.5, 0, 1)
    col = _travel(phase, [(0.70, 0.78, 0.88), (0.55, 0.72, 0.84), (0.80, 0.80, 0.92), (0.66, 0.62, 0.84)],
                  irid=0.22, cycles=2.0, sat=0.4, base=(0.40, 0.50, 0.62))
    return np.clip(col * (1 - fern[..., None] * 0.3) + fern[..., None] * np.float32([0.9, 0.96, 1.0]) * 0.45, 0, 1)

def _frost_spec(h, w, s):
    fern = _web(h, w, s ^ 1, 7000, k=2, intensity=(0.45, 1.0))
    g = _n(h, w, s ^ 2, (3, 6))
    swell = _n(h, w, s ^ 3, (5, 11))
    M = 12 + np.clip(fern * 1.7, 0, 1) * 243                              # fern veins detonate silver
    R = np.clip(60 + g * 130 - fern * 30, 15, 255)
    Cc = np.clip(22 + swell * 120 + cv2.GaussianBlur(fern, (0, 0), 2.6) * 60, 16, 255)
    return M, R, Cc


# --- galaxy: nebula spiral + stars, violet->blue->magenta->teal travel -------
def _galaxy_paint(h, w, s):
    sp_st, sp_sh = _spiral(h, w, s ^ 1, arms=2.0, twist=5.0)
    gas = _n(h, w, s ^ 2, (5, 11))
    stars = _sc(h, w, s ^ 3, 5200, 1.0, "dot")
    phase = np.clip(sp_st * 0.6 + gas * 0.5, 0, 1)
    col = _travel(phase, [(0.10, 0.04, 0.22), (0.20, 0.08, 0.45), (0.45, 0.08, 0.45), (0.05, 0.20, 0.40)],
                  irid=0.30, cycles=2.8, sat=0.85, base=(0.03, 0.02, 0.08))
    return np.clip(col * (0.7 + gas[..., None] * 0.6) + stars[..., None] * np.float32([0.85, 0.9, 1.0]) * 0.85, 0, 1)

def _galaxy_spec(h, w, s):
    sp_st, sp_sh = _spiral(h, w, s ^ 1, arms=2.0, twist=5.0)
    gas = _n(h, w, s ^ 2, (5, 11))
    stars = _sc(h, w, s ^ 3, 5200, 1.0, "dot")
    M = np.clip(12 + stars * 235 + np.clip(sp_sh - 0.5, 0, 1) * 120, 0, 255)   # stars + spiral shimmer
    R = np.clip(180 - gas * 125, 15, 255)
    Cc = np.clip(22 + cv2.GaussianBlur(stars, (0, 0), 2.4) * 150 + sp_st * 40, 16, 255)
    return M, R, Cc


# --- midnight: DEEP night navy, sparse starlight + moonlit sheen -------------
def _midnight_paint(h, w, s):
    gr = _gr(h, w, s ^ 1, 3, 3.0)
    glint = _sc(h, w, s ^ 2, 9000, 1.6, "dot", amp=(0.7, 1.0))
    sheen = np.clip(np.sin(_n(h, w, s ^ 4, (2, 4)) * 6.2832 * 1.5) * 0.5 + 0.5, 0, 1)
    phase = np.clip(gr * 0.5 + sheen * 0.3, 0, 1)
    col = _travel(phase, [(0.015, 0.02, 0.07), (0.03, 0.05, 0.14), (0.02, 0.08, 0.16), (0.05, 0.04, 0.13)],
                  irid=0.18, cycles=1.6, sat=0.5, base=(0.01, 0.015, 0.05))
    gw = np.clip(glint * 1.6, 0, 1)[..., None] * np.float32([0.5, 0.65, 1.0])
    return np.clip(col + gw * 0.5 + sheen[..., None] * np.float32([0.06, 0.10, 0.22]) * 0.3, 0, 1)

def _midnight_spec(h, w, s):
    gr = _gr(h, w, s ^ 1, 3, 3.0)
    glint = _sc(h, w, s ^ 2, 9000, 1.6, "dot", amp=(0.7, 1.0))
    gw = np.clip(glint * 1.7 + cv2.GaussianBlur(glint, (0, 0), 1.5) * 0.8, 0, 1)
    halo = np.clip(cv2.GaussianBlur(glint, (0, 0), 5.0) * 3.2 - gw * 1.2, 0, 1)
    M = 10 + gw * 245                                                     # buried starlight detonates
    R = np.clip(58 + gr * 150, 15, 255)
    Cc = np.clip(20 + _n(h, w, s ^ 3, (18, 40)) * 140 + halo * 45, 16, 255)
    return M, R, Cc


# --- neon: glowing neon TUBES on dark, electric pink/cyan/lime cycling -------
def _neon_paint(h, w, s):
    tubes = np.clip(_web(h, w, s ^ 1, 2600, k=2, intensity=(0.6, 1.0)) * 1.4, 0, 1)
    glow = cv2.GaussianBlur(tubes, (0, 0), 3.0)
    region = _gr(h, w, s ^ 2, 2, 2.0)
    tubecol = _travel(region, [(1.0, 0.05, 0.6), (0.05, 0.9, 0.95), (0.55, 1.0, 0.1), (0.7, 0.1, 1.0)],
                      irid=0.0, smooth=0.35)
    bg = np.float32([0.02, 0.02, 0.04])[None, None, :] * (0.6 + _n(h, w, s ^ 3, (3, 7))[..., None] * 0.4)
    eff = bg + tubecol * tubes[..., None] * 1.25 + tubecol * glow[..., None] * 0.55
    return np.clip(eff, 0, 1)

def _neon_spec(h, w, s):
    tubes = np.clip(_web(h, w, s ^ 1, 2600, k=2, intensity=(0.6, 1.0)) * 1.4, 0, 1)
    glow = cv2.GaussianBlur(tubes, (0, 0), 3.0)
    grain = _n(h, w, s ^ 2, (10, 22))                                     # dark-glass micro grain (R's own field)
    M = 14 + tubes * 238                                                  # tubes blaze (lit gas)
    R = np.clip(55 + grain * 150 - tubes * 40, 15, 255)                   # glass grain, not just inverse tubes
    Cc = np.clip(20 + glow * 170 + tubes * 30, 16, 255)                   # bloom halos pool clearcoat
    return M, R, Cc


# --- obsidian: big conchoidal fracture plates, bronze/teal sheen on glass ----
def _obsidian_paint(h, w, s):
    lab, d1, edge = _vor(h, w, s ^ 1, max(400, (h * w) // 400))
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    tilt = _label_rng(s ^ 2, lab)
    rim = edge ** 1.8
    phase = np.clip(tilt * 0.6 + (1 - d1n) * 0.4, 0, 1)
    sheen = _travel(phase, [(0.04, 0.04, 0.06), (0.10, 0.08, 0.05), (0.05, 0.10, 0.12), (0.12, 0.06, 0.10)],
                    irid=0.5, cycles=3.5, sat=0.9, base=(0.02, 0.02, 0.03))
    bronze = np.float32([0.5, 0.32, 0.12])[None, None, :]
    return np.clip(sheen * (1 - edge[..., None] * 0.4) + bronze * rim[..., None] * 0.55, 0, 1)

def _obsidian_spec(h, w, s):
    lab, d1, edge = _vor(h, w, s ^ 1, max(400, (h * w) // 400))
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    tilt = _label_rng(s ^ 2, lab)
    rim = edge ** 1.8
    M = 12 + rim * 243                                                    # fracture rims blaze molten
    R = np.clip(52 + tilt * 156 - edge * 38, 15, 255)
    Cc = np.clip(20 + ((1 - d1n) ** 2) * 128 + _n(h, w, s ^ 3, (24, 56)) * 36, 16, 255)
    return M, R, Cc


# --- ocean: swell + caustic crests + foam, teal->blue->aqua travel ----------
def _ocean_paint(h, w, s):
    swell = _gr(h, w, s ^ 1, 3, 3.8)
    crest = np.clip((swell - 0.68) / 0.16, 0, 1)
    foam = _sc(h, w, s ^ 2, 8000, 1.2, "dot", amp=(0.6, 1.0)) * np.clip(swell * 1.5 - 0.45, 0, 1)
    phase = np.clip(swell * 0.8 + crest * 0.2, 0, 1)
    col = _travel(phase, [(0.01, 0.10, 0.30), (0.02, 0.24, 0.40), (0.04, 0.46, 0.46), (0.02, 0.38, 0.30)],
                  irid=0.22, cycles=2.2, sat=0.6, base=(0.01, 0.05, 0.14))
    return np.clip(col + foam[..., None] * np.float32([0.6, 0.85, 0.9]) * 0.45, 0, 1)

def _ocean_spec(h, w, s):
    swell = _gr(h, w, s ^ 1, 3, 3.8)
    crest = np.clip((swell - 0.68) / 0.16, 0, 1)
    foam = _sc(h, w, s ^ 2, 8000, 1.2, "dot", amp=(0.6, 1.0)) * np.clip(swell * 1.5 - 0.45, 0, 1)
    g = _gr(h, w, s ^ 4, 4, 3.4)                                         # broad sub-surface shimmer for M
    Cc = np.clip(20 + crest * 235, 16, 255)                               # wet crest lines flash
    M = np.clip(14 + foam * 170 + g * 120 + crest * 30, 0, 255)           # foam + broad shimmer (decorrelated from crest)
    R = np.clip(64 + _n(h, w, s ^ 3, (26, 60)) * (84 + (1 - crest) * 78), 15, 255)
    return M, R, Cc


# --- phoenix: rising feather plume, ember red->gold + hidden magenta ---------
def _phoenix_paint(h, w, s):
    A = _sc(h, w, s ^ 1, 8000, 2.4, "petal")
    plume = _gr(h, w, s ^ 2, 3, 3.0)
    gr = _n(h, w, s ^ 3, (4, 9))
    phase = np.clip(0.15 + A * 0.6 + plume * 0.3, 0, 1)
    col = _travel(phase, [(0.30, 0.03, 0.04), (0.78, 0.20, 0.04), (0.98, 0.60, 0.10), (1.0, 0.90, 0.50)],
                  irid=0.18, cycles=2.0, sat=0.7, base=(0.10, 0.02, 0.02))
    magenta = np.clip((A - 0.6) * 3, 0, 1)[..., None] * np.float32([0.6, 0.05, 0.4])
    return np.clip(col * (0.8 + plume[..., None] * 0.4) + magenta * 0.3 + gr[..., None] * 0.05, 0, 1)

def _phoenix_spec(h, w, s):
    A = _sc(h, w, s ^ 1, 8000, 2.4, "petal")
    plume = _gr(h, w, s ^ 2, 3, 3.0)
    gr = _n(h, w, s ^ 3, (4, 9))
    M = np.clip(14 + np.clip(A * 2.2, 0, 1) * 240, 0, 255)                # feather barbs flare
    R = np.clip(160 - (A + plume) * 96 + (gr - 0.5) * 72, 15, 255)
    Cc = np.clip(20 + np.clip(cv2.GaussianBlur(A, (0, 0), 3.0) * 2.4, 0, 1) * 155, 16, 255)
    return M, R, Cc


# --- venom: snake dragonscale + toxic drip, acid-green->violet travel --------
def _venom_paint(h, w, s):
    lab, d1, edge = _vor(h, w, s ^ 1, max(1200, (h * w) // 40))
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    clan = _label_rng(s ^ 2, lab)
    dome = (1 - d1n) ** 2
    phase = np.clip(0.25 + dome * 0.5 + _n(h, w, s ^ 3, (5, 11)) * 0.2, 0, 1)
    col = _travel(phase, [(0.06, 0.28, 0.03), (0.25, 0.72, 0.08), (0.50, 0.85, 0.05), (0.20, 0.05, 0.30)],
                  irid=0.24, cycles=2.4, sat=0.85, base=(0.03, 0.10, 0.02))
    vmask = (clan > 0.70).astype(np.float32)[..., None]
    vio = vmask * np.float32([0.18, 0.03, 0.25])
    return np.clip((col * (1 - vmask * 0.7) + vio) * (1 - edge[..., None] * 0.6), 0, 1)

def _venom_spec(h, w, s):
    lab, d1, edge = _vor(h, w, s ^ 1, max(1200, (h * w) // 40))
    d1n = np.clip(d1 / max(d1.max(), 1e-5), 0, 1)
    clan = _label_rng(s ^ 2, lab)
    dome = (1 - d1n) ** 2
    mB = (clan > 0.70).astype(np.float32)
    M = 13 + mB * (1 - edge) * 242                                        # violet scales mirror-flip
    R = np.clip(64 + edge * 132 + (_n(h, w, s ^ 4, (22, 50)) - 0.5) * 64, 15, 255)
    Cc = np.clip(18 + (1 - mB) * dome * 165, 16, 255)                     # green venom-bead domes glow wet
    return M, R, Cc


# --- mystichrome: chrome flow + oilslick travel + tri territories -----------
def _mystichrome_paint(h, w, s):
    st, sh = _oilslick(h, w, s ^ 1, bands=7.0)
    m0, m1, m2 = tri_partition((h, w), s ^ 2, cells=max(2600, (h * w) // 20), soften_px=1.2)
    phase = np.clip(st * 0.7 + sh * 0.3, 0, 1)
    col = _travel(phase, [(0.07, 0.02, 0.13), (0.02, 0.16, 0.16), (0.04, 0.22, 0.10), (0.02, 0.02, 0.03)],
                  irid=0.45, cycles=3.2, sat=0.9, base=(0.03, 0.03, 0.05))
    tint = (m0[..., None] * np.float32([0.10, 0.02, 0.16])
            + m1[..., None] * np.float32([0.0, 0.12, 0.12])
            + m2[..., None] * np.float32([0.02, 0.14, 0.05]))
    return np.clip(col * 0.7 + tint * 0.8 + sh[..., None] * 0.15, 0, 1)

def _mystichrome_spec(h, w, s):
    st, sh = _oilslick(h, w, s ^ 1, bands=7.0)
    m0, m1, m2 = tri_partition((h, w), s ^ 2, cells=max(2600, (h * w) // 20), soften_px=1.2)
    seam = np.clip(np.abs(cv2.GaussianBlur(m1, (0, 0), 1.3) - m1) * 3.0, 0, 1)
    M = np.clip(20 + np.clip(st * 1.8, 0, 1) * 220, 0, 255)               # chrome mirror rolls with the slick
    R = np.clip(60 + seam * 150 - st * 30, 15, 255)                       # territory seams = matte
    Cc = np.clip(20 + sh * 150 + m2 * 40, 16, 255)
    return M, R, Cc


# ===========================================================================
# PRIZM — owner-flagged fixes (2026-06-21). prizm = prismatic/full-spectrum.
# Kept structurally distinct from the chameleon cousins (different engines) so
# they clear the cross-catalog uniqueness gate.
# ===========================================================================
RAINBOW = [(0.90, 0.05, 0.10), (0.95, 0.50, 0.05), (0.90, 0.90, 0.10),
           (0.10, 0.80, 0.22), (0.05, 0.70, 0.90), (0.10, 0.20, 0.90), (0.60, 0.05, 0.85)]


# --- prizm_neon: glowing prismatic neon ARCS (was b/w specks) ----------------
def _prizm_neon_paint(h, w, s):
    rings = _rings(h, w, s ^ 1, 3200, 3.0, 1.6)                           # concentric neon arcs
    lines = _web(h, w, s ^ 2, 1800, k=2, intensity=(0.5, 1.0))
    glow_src = np.clip(rings * 0.7 + lines * 0.85, 0, 1)
    glow = cv2.GaussianBlur(glow_src, (0, 0), 2.6)
    region = _gr(h, w, s ^ 3, 3, 3.0)
    spectrum = _travel(region, RAINBOW, irid=0.25, cycles=3.0, sat=1.0, smooth=0.4)
    bg = np.float32([0.015, 0.01, 0.03])[None, None, :] * (0.6 + _n(h, w, s ^ 4, (3, 7))[..., None] * 0.4)
    return np.clip(bg + spectrum * glow_src[..., None] * 1.25 + spectrum * glow[..., None] * 0.5, 0, 1)

def _prizm_neon_spec(h, w, s):
    rings = _rings(h, w, s ^ 1, 3200, 3.0, 1.6)
    lines = _web(h, w, s ^ 2, 1800, k=2, intensity=(0.5, 1.0))
    glow_src = np.clip(rings * 0.7 + lines * 0.85, 0, 1)
    grain = _n(h, w, s ^ 3, (10, 22))
    M = 14 + np.clip(glow_src * 1.6, 0, 1) * 238                          # lit gas blazes
    R = np.clip(55 + grain * 150 - glow_src * 40, 15, 255)                # dark glass grain
    Cc = np.clip(20 + cv2.GaussianBlur(glow_src, (0, 0), 3.0) * 175 + glow_src * 30, 16, 255)
    return M, R, Cc


# --- prizm_black_rainbow: BLACK body, visible rainbow oil-slick bands --------
def _prizm_black_rainbow_paint(h, w, s):
    st, sh = _oilslick(h, w, s ^ 1, bands=9.0)
    flow, fsh = _iflow(h, w, s ^ 2, scale=3.0)
    phase = np.clip(st * 0.7 + flow * 0.3, 0, 1)
    rainbow = _travel(phase, RAINBOW, irid=0.4, cycles=4.0, sat=1.0, smooth=0.3)
    vis = np.clip((phase - 0.35) * 1.9, 0, 1)[..., None]                  # rainbow only in the bands
    black = np.float32([0.01, 0.01, 0.015])[None, None, :]
    return np.clip(black + rainbow * vis * 0.95, 0, 1)

def _prizm_black_rainbow_spec(h, w, s):
    st, sh = _oilslick(h, w, s ^ 1, bands=9.0)
    flow, fsh = _iflow(h, w, s ^ 2, scale=3.0)
    phase = np.clip(st * 0.7 + flow * 0.3, 0, 1)
    grain = _n(h, w, s ^ 3, (10, 22))
    M = np.clip(16 + np.clip((phase - 0.4) * 2.4, 0, 1) * 230, 0, 255)    # rainbow bands flash
    R = np.clip(55 + grain * 150 - phase * 25, 15, 255)
    Cc = np.clip(18 + sh * 150 + flow * 40, 16, 255)
    return M, R, Cc


# --- prizm_cosmos: FINER cosmic nebula (was too big) ------------------------
def _prizm_cosmos_paint(h, w, s):
    gas = _n(h, w, s ^ 1, (6, 13))                                        # finer gas (higher octaves)
    sp, spsh = _spiral(h, w, s ^ 2, arms=3.0, twist=7.0)
    stars = _sc(h, w, s ^ 3, 9000, 0.8, "dot")                           # many fine stars
    dust = _sc(h, w, s ^ 4, 14000, 0.5, "dot")
    phase = np.clip(gas * 0.6 + sp * 0.4, 0, 1)
    col = _travel(phase, [(0.05, 0.02, 0.12), (0.25, 0.05, 0.35), (0.50, 0.08, 0.40),
                          (0.05, 0.25, 0.45), (0.30, 0.10, 0.50)], irid=0.30, cycles=3.2, sat=0.85, base=(0.02, 0.01, 0.05))
    eff = col * (0.6 + gas[..., None] * 0.6) + stars[..., None] * np.float32([0.9, 0.92, 1.0]) * 0.9 + dust[..., None] * 0.4
    return np.clip(eff, 0, 1)

def _prizm_cosmos_spec(h, w, s):
    gas = _n(h, w, s ^ 1, (6, 13))
    sp, spsh = _spiral(h, w, s ^ 2, arms=3.0, twist=7.0)
    stars = _sc(h, w, s ^ 3, 9000, 0.8, "dot")
    M = np.clip(12 + stars * 235 + np.clip(spsh - 0.5, 0, 1) * 110, 0, 255)
    R = np.clip(175 - gas * 120, 15, 255)
    Cc = np.clip(22 + cv2.GaussianBlur(stars, (0, 0), 2.0) * 140 + sp * 45, 16, 255)
    return M, R, Cc


# --- prizm_midnight: DEEP midnight + fine prismatic facet glints -------------
def _prizm_midnight_paint(h, w, s):
    facet, fsh = _facets(h, w, s ^ 1, cells=80.0)                         # fine prismatic micro-facets
    g = _n(h, w, s ^ 2, (4, 9))
    glint = _sc(h, w, s ^ 3, 6000, 1.2, "dot", amp=(0.6, 1.0))
    phase = np.clip(facet * 0.5 + g * 0.4, 0, 1)
    col = _travel(phase, [(0.01, 0.015, 0.06), (0.02, 0.04, 0.12), (0.04, 0.03, 0.14), (0.02, 0.06, 0.13)],
                  irid=0.22, cycles=2.0, sat=0.7, base=(0.008, 0.012, 0.04))
    prism = np.clip((facet - 0.7) * 3, 0, 1)[..., None] * _travel(fsh, RAINBOW, irid=0.0, smooth=0.4) * 0.25
    return np.clip(col + prism + glint[..., None] * np.float32([0.4, 0.5, 0.9]) * 0.4, 0, 1)

def _prizm_midnight_spec(h, w, s):
    facet, fsh = _facets(h, w, s ^ 1, cells=80.0)
    g = _n(h, w, s ^ 2, (4, 9))
    glint = _sc(h, w, s ^ 3, 6000, 1.2, "dot", amp=(0.6, 1.0))
    M = np.clip(12 + np.clip(glint * 1.7, 0, 1) * 235 + np.clip((facet - 0.7) * 3, 0, 1) * 80, 0, 255)
    R = np.clip(60 + g * 150 - facet * 25, 15, 255)
    Cc = np.clip(20 + (1 - facet) * 130 + cv2.GaussianBlur(glint, (0, 0), 3.0) * 50, 16, 255)
    return M, R, Cc


_PRIZM_FIXES = (
    ("prizm_neon",          _prizm_neon_paint,          _prizm_neon_spec),
    ("prizm_black_rainbow", _prizm_black_rainbow_paint, _prizm_black_rainbow_spec),
    ("prizm_cosmos",        _prizm_cosmos_paint,        _prizm_cosmos_spec),
    ("prizm_midnight",      _prizm_midnight_paint,      _prizm_midnight_spec),
)


# ===========================================================================
# COLOR CLASH — owner-flagged fixes (2026-06-21). cc = two clashing colors.
# ===========================================================================

# --- cc_blood_orange: true blood-orange (blood-red vs vivid orange citrus) ---
def _cc_blood_orange_paint(h, w, s):
    flow, fsh = _iflow(h, w, s ^ 1, scale=3.5)                           # marbled citrus flesh
    seg = flip_lattice((h, w), s ^ 2, 1.0, 0.45)                         # clash territories
    veins = _web(h, w, s ^ 3, 4000, k=2, intensity=(0.4, 1.0))          # rind/pith veins
    blood = _ramp(np.clip(flow, 0, 1), _lut([(0.30, 0.02, 0.03), (0.62, 0.05, 0.04), (0.80, 0.12, 0.03)], 0.5))
    orange = _ramp(np.clip(flow * 0.9 + 0.1, 0, 1), _lut([(0.85, 0.30, 0.02), (0.98, 0.55, 0.06), (1.0, 0.72, 0.18)], 0.5))
    eff = blood * (1 - seg[..., None]) + orange * seg[..., None]
    return np.clip(eff * (1 - veins[..., None] * 0.35) + veins[..., None] * np.float32([0.5, 0.18, 0.05]) * 0.3, 0, 1)

def _cc_blood_orange_spec(h, w, s):
    flow, fsh = _iflow(h, w, s ^ 1, scale=3.5)
    seg = flip_lattice((h, w), s ^ 2, 1.0, 0.45)
    veins = _web(h, w, s ^ 3, 4000, k=2, intensity=(0.4, 1.0))
    g = _gr(h, w, s ^ 4, 4, 3.0)
    seam = np.clip(np.abs(cv2.GaussianBlur(seg, (0, 0), 1.2) - seg) * 3, 0, 1)
    M = np.clip(16 + np.clip(veins * 1.8, 0, 1) * 200 + g * 70, 0, 255)
    R = np.clip(70 + (1 - flow) * 120 - veins * 30, 15, 255)
    Cc = np.clip(20 + seam * 150 + flow * 60, 16, 255)
    return M, R, Cc


# --- cc_chaos_theory: bright many-shade chaotic attractor gradient -----------
def _cc_chaos_theory_paint(h, w, s):
    sp, spsh = _spiral(h, w, s ^ 1, arms=4.0, twist=9.0)
    flow, fsh = _iflow(h, w, s ^ 2, scale=5.0)
    phase = np.clip(sp * 0.5 + flow * 0.5, 0, 1)
    col = _travel(phase, [(0.10, 0.35, 0.85), (0.10, 0.75, 0.60), (0.70, 0.85, 0.10),
                          (0.95, 0.45, 0.10), (0.85, 0.10, 0.45), (0.45, 0.15, 0.85)],
                  irid=0.30, cycles=3.6, sat=0.9, smooth=0.45, base=(0.15, 0.15, 0.20))
    return np.clip(col * (0.6 + flow[..., None] * 0.6) + 0.12, 0, 1)     # +0.12 brighten (was too dark)

def _cc_chaos_theory_spec(h, w, s):
    sp, spsh = _spiral(h, w, s ^ 1, arms=4.0, twist=9.0)
    flow, fsh = _iflow(h, w, s ^ 2, scale=5.0)
    g = _gr(h, w, s ^ 3, 4, 3.2)
    M = np.clip(16 + np.clip(spsh - 0.4, 0, 1) * 200 + g * 70, 0, 255)
    R = np.clip(70 + (1 - flow) * 120, 15, 255)
    Cc = np.clip(20 + sp * 150 + fsh * 40, 16, 255)
    return M, R, Cc


# --- cc_nuclear_dawn: FINE radioactive fallout + toxic dawn (crushed scale) --
def _cc_nuclear_dawn_paint(h, w, s):
    fallout = _sc(h, w, s ^ 1, 16000, 0.6, "dot")                       # many fine particles
    streaks = _sc(h, w, s ^ 2, 9000, 0.8, "streak", len_px=4)
    gas = _n(h, w, s ^ 3, (7, 15))                                       # fine gas (high octave)
    dawn = _gr(h, w, s ^ 4, 4, 4.0)
    phase = np.clip(dawn * 0.6 + gas * 0.4, 0, 1)
    col = _travel(phase, [(0.05, 0.06, 0.02), (0.40, 0.45, 0.04), (0.95, 0.70, 0.08), (0.60, 0.95, 0.10)],
                  irid=0.18, cycles=2.4, sat=0.8, base=(0.02, 0.03, 0.01))
    hot = np.clip((dawn - 0.75) * 4, 0, 1)[..., None] * np.float32([1.0, 0.95, 0.6])
    eff = col * (0.7 + gas[..., None] * 0.5) + fallout[..., None] * np.float32([0.7, 1.0, 0.4]) * 0.5 + streaks[..., None] * 0.3 + hot * 0.4
    return np.clip(eff, 0, 1)

def _cc_nuclear_dawn_spec(h, w, s):
    fallout = _sc(h, w, s ^ 1, 16000, 0.6, "dot")
    gas = _n(h, w, s ^ 3, (7, 15))
    dawn = _gr(h, w, s ^ 4, 4, 4.0)
    g2 = _gr(h, w, s ^ 5, 4, 3.0)
    M = np.clip(14 + fallout * 210 + g2 * 90, 0, 255)
    R = np.clip(75 + gas * 130 - fallout * 30, 15, 255)
    Cc = np.clip(20 + np.clip((dawn - 0.7) * 4, 0, 1) * 180 + gas * 40, 16, 255)
    return M, R, Cc


_CC_FIXES = (
    ("cc_blood_orange",  _cc_blood_orange_paint,  _cc_blood_orange_spec),
    ("cc_chaos_theory",  _cc_chaos_theory_paint,  _cc_chaos_theory_spec),
    ("cc_nuclear_dawn",  _cc_nuclear_dawn_paint,  _cc_nuclear_dawn_spec),
)


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------
_CHAMELEON = (
    ("chameleon_amethyst", _amethyst_paint, _amethyst_spec),
    ("chameleon_arctic",   _arctic_paint,   _arctic_spec),
    ("chameleon_aurora",   _aurora_paint,   _aurora_spec),
    ("chameleon_copper",   _copper_paint,   _copper_spec),
    ("chameleon_emerald",  _emerald_paint,  _emerald_spec),
    ("chameleon_fire",     _fire_paint,     _fire_spec),
    ("chameleon_frost",    _frost_paint,    _frost_spec),
    ("chameleon_galaxy",   _galaxy_paint,   _galaxy_spec),
    ("chameleon_midnight", _midnight_paint, _midnight_spec),
    ("chameleon_neon",     _neon_paint,     _neon_spec),
    ("chameleon_obsidian", _obsidian_paint, _obsidian_spec),
    ("chameleon_ocean",    _ocean_paint,    _ocean_spec),
    ("chameleon_phoenix",  _phoenix_paint,  _phoenix_spec),
    ("chameleon_venom",    _venom_paint,    _venom_spec),
    ("mystichrome",        _mystichrome_paint, _mystichrome_spec),
)

_ALL_REBUILDS = _CHAMELEON + _PRIZM_FIXES + _CC_FIXES
REBUILD_MONOLITHICS = {}
for _fid, _p, _sp in _ALL_REBUILDS:
    REBUILD_MONOLITHICS[_fid] = _pair(_fid, _p, _sp)


# ===========================================================================
# PRIZM keepers — KEEP the owner-liked paint, give each a UNIQUE spec that
# TRACES its own paint art (fracture_spec on the real pixels). Per-finish dials
# + M/Cc modulation so no two traced specs are twins (the "no reused spec" fix).
# Excludes the 4 full-redos above, prizm_alien_skin (untouched), prizm_adaptive.
# ===========================================================================
PRIZM_KEEPERS = [
    "prizm_arctic", "prizm_aurora_shift", "prizm_blood_moon", "prizm_candy_paint",
    "prizm_chrome_rose", "prizm_copper_flame", "prizm_dark_matter", "prizm_deep_space",
    "prizm_duochrome", "prizm_ember", "prizm_fire_ice", "prizm_galaxy_dust",
    "prizm_holographic", "prizm_iridescent", "prizm_mystichrome", "prizm_oceanic",
    "prizm_phoenix", "prizm_solar", "prizm_spectrum", "prizm_sunset_strip",
    "prizm_titanium", "prizm_toxic_waste", "prizm_venom",
]


def _hash01(s, salt=0):
    return (int(hashlib.md5((str(s) + "|" + str(salt)).encode()).hexdigest(), 16) % 100000) / 100000.0


def _make_trace_spec(existing_paint_fn, fid):
    """A spec_fn that derives a UNIQUE FRACTURE-ignition spec from the finish's own paint."""
    ig = 0.85 + _hash01(fid, 1) * 0.7          # ignition 0.85..1.55
    ag = 0.70 + _hash01(fid, 2) * 0.9          # angle_gate 0.70..1.60
    cf = 18.0 + _hash01(fid, 3) * 55.0         # calm_floor 18..73
    dc = 0.18 + _hash01(fid, 4) * 0.30         # decorrelation 0.18..0.48
    moct = 3 + int(_hash01(fid, 5) * 4)        # M-grain octave 3..6

    def spec_fn(shape, mask, seed, sm):
        fh, fw = _shape2(shape); h, w, _ = _work_shape(shape)
        onw = np.ones((h, w), np.float32)
        try:
            art = existing_paint_fn(np.zeros((h, w, 3), np.float32), (h, w), onw, seed, 1.0, 0.0)
        except Exception:
            art = existing_paint_fn(np.zeros((h, w, 3), np.float32), (h, w), onw, seed, 1.0, np.zeros((h, w), np.float32))
        art = np.clip(np.asarray(art)[:, :, :3], 0, 1)
        spec4 = _fracture_spec(art, onw, ignition=ig, angle_gate=ag, calm_floor=cf,
                               decorrelation=dc, as_uint8=False)
        M = spec4[..., 0].astype(np.float32); R = spec4[..., 1].astype(np.float32); Cc = spec4[..., 2].astype(np.float32)
        # per-finish modulation so the near-chrome body / clearcoat aren't cross-finish twins
        gM = _gr(h, w, _seed_of(fid, seed) ^ 0x33, moct, 3.0)
        gC = _n(h, w, _seed_of(fid, seed) ^ 0x77, (12, 26))
        M = np.clip(M * (0.55 + 0.6 * gM), 0, 255)
        Cc = np.clip(Cc * (0.72 + 0.4 * gC), 16, 255)
        R = np.clip(R, 15, 255)
        _msd = float(np.std(M))                            # dynamism backstop (target >20 with clip margin)
        if 1e-3 < _msd < 25.0:
            _mm = float(np.mean(M)); M = np.clip(_mm + (M - _mm) * (25.0 / _msd), 0, 255)
        M, R, Cc = (_upscale(a, fh, fw) for a in (M, R, Cc))
        return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)
    return spec_fn


def _install_traces(mono_reg, ids):
    """KEEP each id's paint, replace its spec with a unique paint-traced one.
    Call AFTER REBUILD_MONOLITHICS is applied (so the paints are present)."""
    n = 0
    for fid in ids:
        e = mono_reg.get(fid)
        if not e:
            continue
        paint_old = e[1] if isinstance(e, (tuple, list)) else e.get("paint_fn")
        if paint_old is None:
            continue
        mono_reg[fid] = (_make_trace_spec(paint_old, fid), paint_old)
        n += 1
    return n


# COLOR CLASH keepers: keep paint, derive a unique paint-traced spec (excludes
# the 3 full-redos cc_blood_orange/cc_chaos_theory/cc_nuclear_dawn above).
CC_KEEPERS = [
    "cc_acid_burn", "cc_bruised_sky", "cc_candy_poison", "cc_chemical_spill",
    "cc_coral_venom", "cc_deep_friction", "cc_digital_rot", "cc_electric_conflict",
    "cc_fever_dream", "cc_flash_burn", "cc_magma_freeze", "cc_neon_bruise",
    "cc_neon_war", "cc_plasma_edge", "cc_punk_static", "cc_radioactive",
    "cc_rust_vs_ice", "cc_solar_clash", "cc_toxic_sunset", "cc_ultraviolet_burn",
    "cc_venom_strike", "cc_voltage_split",
]


def install_prizm_spec_traces(mono_reg):
    return _install_traces(mono_reg, PRIZM_KEEPERS)


def install_colorclash_spec_traces(mono_reg):
    return _install_traces(mono_reg, CC_KEEPERS)


# ===========================================================================
# GRADIENTS (126) — TOTAL ground-up rebuild. A real gradient ENGINE with many
# structure modes + name-derived palettes, so each is a distinct premium
# abstract gradient (NOT one ramp recolored). Orientation variants (_h/_diag/
# _vortex) get DIFFERENT structures, not literal directions (UV-agnostic).
# ===========================================================================
CONCEPT_PALETTES = {
    "arctic_dawn": [(0.45, 0.66, 0.85), (0.80, 0.84, 0.92), (0.96, 0.66, 0.62), (0.70, 0.58, 0.80)],
    "bruise": [(0.10, 0.04, 0.16), (0.38, 0.08, 0.45), (0.78, 0.12, 0.42), (0.20, 0.45, 0.20)],
    "copper_patina": [(0.62, 0.34, 0.14), (0.72, 0.46, 0.18), (0.10, 0.50, 0.40), (0.18, 0.58, 0.42)],
    "fire_fade": [(0.30, 0.02, 0.02), (0.80, 0.16, 0.03), (0.98, 0.55, 0.06), (1.0, 0.85, 0.30)],
    "forest_canopy": [(0.02, 0.20, 0.08), (0.10, 0.45, 0.16), (0.40, 0.65, 0.18), (0.85, 0.85, 0.40)],
    "golden_hour": [(0.55, 0.28, 0.08), (0.88, 0.58, 0.14), (1.0, 0.78, 0.30), (1.0, 0.90, 0.62)],
    "ice_fire": [(0.45, 0.68, 0.88), (0.82, 0.90, 0.95), (0.92, 0.30, 0.10), (0.70, 0.10, 0.05)],
    "lava_flow": [(0.04, 0.02, 0.02), (0.50, 0.05, 0.02), (0.92, 0.28, 0.04), (1.0, 0.72, 0.16)],
    "midnight_ember": [(0.02, 0.03, 0.10), (0.18, 0.06, 0.10), (0.70, 0.18, 0.05), (0.95, 0.45, 0.10)],
    "neon_rush": [(0.95, 0.05, 0.55), (0.55, 0.05, 0.85), (0.05, 0.85, 0.92), (0.55, 0.95, 0.10)],
    "ocean_depths": [(0.01, 0.05, 0.16), (0.02, 0.20, 0.38), (0.04, 0.42, 0.48), (0.30, 0.70, 0.70)],
    "steel_forge": [(0.14, 0.15, 0.18), (0.34, 0.40, 0.48), (0.60, 0.62, 0.66), (0.95, 0.55, 0.18)],
    "sunset": [(0.10, 0.10, 0.30), (0.45, 0.15, 0.45), (0.92, 0.40, 0.25), (1.0, 0.70, 0.45)],
    "toxic_waste": [(0.04, 0.08, 0.02), (0.20, 0.45, 0.04), (0.55, 0.85, 0.06), (0.80, 0.95, 0.20)],
    "twilight": [(0.04, 0.06, 0.22), (0.18, 0.10, 0.42), (0.42, 0.16, 0.52), (0.85, 0.40, 0.55)],
    "black_gold": [(0.02, 0.02, 0.03), (0.20, 0.14, 0.05), (0.62, 0.44, 0.12), (0.92, 0.74, 0.28)],
    "patriot": [(0.62, 0.06, 0.10), (0.92, 0.92, 0.95), (0.06, 0.12, 0.45), (0.20, 0.25, 0.65)],
    "frostbite": [(0.05, 0.10, 0.30), (0.30, 0.62, 0.85), (0.85, 0.92, 0.98), (0.55, 0.45, 0.80)],
    "neon_violet": [(0.45, 0.08, 0.70), (0.80, 0.10, 0.62), (0.20, 0.30, 0.92), (0.55, 0.20, 0.95)],
    "aqua_drift": [(0.04, 0.40, 0.45), (0.15, 0.70, 0.72), (0.45, 0.88, 0.80), (0.75, 0.95, 0.88)],
    "iron_blood": [(0.18, 0.18, 0.20), (0.40, 0.10, 0.10), (0.65, 0.12, 0.10), (0.55, 0.30, 0.18)],
    "emerald_crown": [(0.02, 0.28, 0.16), (0.05, 0.55, 0.32), (0.30, 0.72, 0.20), (0.90, 0.78, 0.30)],
    "candy_cane": [(0.78, 0.06, 0.12), (0.95, 0.92, 0.93), (0.85, 0.10, 0.18), (0.60, 0.04, 0.10)],
    "chrome_wave": [(0.35, 0.40, 0.48), (0.62, 0.68, 0.74), (0.88, 0.92, 0.96), (0.20, 0.28, 0.40)],
    "copper_flame": [(0.45, 0.20, 0.08), (0.72, 0.40, 0.14), (0.95, 0.50, 0.10), (1.0, 0.78, 0.24)],
    "storm_front": [(0.12, 0.14, 0.18), (0.30, 0.36, 0.46), (0.55, 0.62, 0.72), (0.92, 0.95, 1.0)],
    "ultraviolet": [(0.20, 0.04, 0.40), (0.40, 0.08, 0.72), (0.20, 0.20, 0.90), (0.70, 0.15, 0.85)],
    "antique_gold": [(0.30, 0.22, 0.10), (0.55, 0.42, 0.18), (0.82, 0.66, 0.32), (0.92, 0.86, 0.62)],
    "obsidian": [(0.02, 0.02, 0.03), (0.12, 0.12, 0.15), (0.22, 0.18, 0.26), (0.40, 0.30, 0.45)],
    "electric_lime": [(0.04, 0.10, 0.02), (0.35, 0.70, 0.05), (0.62, 0.95, 0.10), (0.85, 1.0, 0.35)],
    "magma": [(0.03, 0.01, 0.01), (0.45, 0.04, 0.02), (0.90, 0.26, 0.04), (1.0, 0.70, 0.14)],
    "sapphire_ice": [(0.04, 0.10, 0.40), (0.10, 0.30, 0.75), (0.45, 0.65, 0.92), (0.85, 0.92, 0.98)],
    "rose_gold": [(0.55, 0.28, 0.28), (0.85, 0.50, 0.48), (0.95, 0.72, 0.62), (0.92, 0.84, 0.68)],
    "forest_night": [(0.02, 0.08, 0.06), (0.04, 0.22, 0.16), (0.10, 0.40, 0.30), (0.35, 0.55, 0.40)],
    "solar_flare": [(0.40, 0.10, 0.02), (0.85, 0.35, 0.04), (1.0, 0.70, 0.12), (1.0, 0.95, 0.70)],
    "solar": [(0.55, 0.20, 0.04), (0.92, 0.50, 0.08), (1.0, 0.75, 0.18), (1.0, 0.92, 0.55)],
}
COLOR_WORDS = {
    "wine": (0.40, 0.05, 0.12), "silk": (0.85, 0.82, 0.75), "midnight": (0.02, 0.04, 0.12),
    "gold": (0.85, 0.65, 0.15), "coral": (0.95, 0.45, 0.35), "sea": (0.05, 0.40, 0.45),
    "ember": (0.72, 0.18, 0.05), "ash": (0.42, 0.40, 0.38), "jade": (0.10, 0.55, 0.40),
    "mist": (0.70, 0.78, 0.78), "plum": (0.35, 0.12, 0.35), "dawn": (0.95, 0.62, 0.52),
    "amber": (0.86, 0.55, 0.12), "night": (0.03, 0.04, 0.10), "sage": (0.55, 0.62, 0.45),
    "bronze": (0.50, 0.32, 0.12), "titanium": (0.60, 0.62, 0.66), "fire": (0.85, 0.20, 0.05),
    "ivory": (0.92, 0.88, 0.78), "cobalt": (0.10, 0.20, 0.72), "honey": (0.86, 0.60, 0.20),
    "slate": (0.35, 0.40, 0.48), "rose": (0.86, 0.40, 0.46), "charcoal": (0.15, 0.15, 0.17),
    "lavender": (0.60, 0.50, 0.80), "dusk": (0.30, 0.25, 0.42), "cream": (0.93, 0.90, 0.80),
    "crimson": (0.70, 0.05, 0.12), "blush": (0.95, 0.70, 0.72), "graphite": (0.22, 0.23, 0.25),
    "mint": (0.50, 0.86, 0.66), "purple": (0.45, 0.10, 0.62), "champagne": (0.88, 0.80, 0.60),
    "navy": (0.05, 0.10, 0.32), "pewter": (0.50, 0.52, 0.56), "chocolate": (0.30, 0.18, 0.10),
    "tan": (0.75, 0.60, 0.42), "ruby": (0.70, 0.08, 0.22), "topaz": (0.86, 0.60, 0.15),
    "amethyst": (0.50, 0.30, 0.72), "opal": (0.70, 0.82, 0.86), "cerulean": (0.10, 0.50, 0.82),
    "indigo": (0.20, 0.15, 0.56), "maroon": (0.40, 0.08, 0.12), "burgundy": (0.40, 0.05, 0.18),
    "chartreuse": (0.62, 0.86, 0.10), "peach": (0.98, 0.70, 0.50), "sky": (0.45, 0.70, 0.92),
    "teal": (0.05, 0.52, 0.52), "green": (0.10, 0.60, 0.22), "blue": (0.10, 0.30, 0.85),
    "white": (0.92, 0.92, 0.95), "pink": (0.95, 0.45, 0.72), "orange": (0.96, 0.50, 0.10),
    "red": (0.82, 0.10, 0.10), "shadow": (0.10, 0.10, 0.13), "violet": (0.50, 0.15, 0.78),
    "aqua": (0.20, 0.80, 0.80), "emerald": (0.05, 0.60, 0.35), "copper": (0.70, 0.40, 0.18),
    "sapphire": (0.10, 0.25, 0.72), "iron": (0.30, 0.30, 0.34), "steel": (0.40, 0.46, 0.54),
    "lime": (0.60, 0.90, 0.12),
}


def _palette_from_name(core):
    if core in CONCEPT_PALETTES:
        return [tuple(map(float, c)) for c in CONCEPT_PALETTES[core]]
    cols = [COLOR_WORDS[t] for t in core.split("_") if t in COLOR_WORDS]
    if not cols:
        cols = [(0.18, 0.18, 0.24), (0.70, 0.70, 0.78)]
    if len(cols) == 1:
        c = np.float32(cols[0])
        cols = [tuple(np.clip(c * 0.30, 0, 1)), tuple(c), tuple(np.clip(c * 0.45 + 0.55, 0, 1))]
    return [tuple(map(float, c)) for c in cols]


def _grad_struct(h, w, s, mode, freq):
    """Return (structure01, hero01, fine01) for an abstract omnidirectional gradient."""
    if mode == "flow":
        st, sh = _iflow(h, w, s, scale=int(freq)); hero = np.clip((st - 0.68) * 3, 0, 1); fine = sh
    elif mode == "marble":
        st, sh = _iflow(h, w, s, scale=int(freq))
        veins = np.clip(1.0 - np.abs(np.sin(st * 6.2832 * 3.0)), 0, 1)
        st = _n01(st * 0.7 + veins * 0.3); hero = veins; fine = sh
    elif mode == "caustic":
        st, sh = _caustics(h, w, s, rings=float(freq + 4)); hero = sh; fine = _n(h, w, s ^ 6, (10, 22))
    elif mode == "spiral":
        st, sh = _spiral(h, w, s, arms=float(max(2, freq - 1)), twist=float(freq + 2)); hero = np.clip((st - 0.6) * 3, 0, 1); fine = sh
    elif mode == "ridge":
        nz = _gr(h, w, s, 4, float(freq) * 0.6); st = np.abs(nz - 0.5) * 2.0
        hero = np.clip((st - 0.6) * 3, 0, 1); fine = _n(h, w, s ^ 5, (9, 19))
    elif mode == "interference":
        st, sh = _oilslick(h, w, s, bands=float(freq + 3)); hero = sh; fine = _n(h, w, s ^ 6, (10, 22))
    elif mode == "facet":
        lab, d1, edge = _vor(h, w, s, max(700, (h * w) // int(36 + freq * 8)))
        st = _label_rng(s ^ 3, lab); hero = edge ** 2.0; fine = _n(h, w, s ^ 6, (10, 22))
    elif mode == "swirl":
        st, sh = _spiral(h, w, s, arms=float(freq + 2), twist=float(freq) * 1.6)
        sw = _gr(h, w, s ^ 2, 3, 3.0); st = _n01(st * 0.6 + sw * 0.4); hero = np.clip((sh - 0.5) * 2, 0, 1); fine = _n(h, w, s ^ 6, (10, 22))
    else:  # "pool"
        lo = _n(h, w, s, (2, 5)); st = lo; hero = np.clip((lo - 0.68) * 3, 0, 1); fine = _n(h, w, s ^ 7, (10, 22))
    return _n01(st).astype(np.float32), np.clip(hero, 0, 1).astype(np.float32), np.clip(fine, 0, 1).astype(np.float32)


def _grad_recipe(fid):
    core = fid[5:] if fid.startswith("grad_") else fid
    suffix = None
    for suf in ("_vortex", "_diag", "_h"):
        if core.endswith(suf):
            suffix = suf[1:]; core = core[:-len(suf)]; break
    pal = _palette_from_name(core)
    base_modes = ["flow", "caustic", "interference", "facet", "pool", "spiral", "marble"]
    if suffix == "vortex":
        mode = "swirl"
    elif suffix == "h":
        mode = "marble"
    elif suffix == "diag":
        mode = "ridge"
    else:
        mode = base_modes[int(_hash01(core, 9) * len(base_modes)) % len(base_modes)]
    freq = 3 + int(_hash01(fid, 11) * 6)
    return pal, mode, freq


def _grad_paint_fn(pal, mode, freq):
    base = tuple(np.clip(np.float32(pal[0]) * 0.45, 0, 1))
    hi = np.float32(pal[-1])

    def f(h, w, s):
        st, hero, fine = _grad_struct(h, w, s, mode, freq)
        col = _travel(st, pal, irid=0.16, cycles=2.2, sat=0.6, smooth=0.5, base=base)
        col = col * (0.62 + fine[..., None] * 0.5) + hero[..., None] * hi[None, None, :] * 0.35
        return np.clip(col, 0, 1)
    return f


def _grad_spec_fn(pal, mode, freq):
    def f(h, w, s):
        st, hero, fine = _grad_struct(h, w, s, mode, freq)
        gM = _gr(h, w, s ^ 0x5C, 4, 2.6)                                    # M's own broad heat
        gR = _gr(h, w, s ^ 0x2B, 4, 3.2)                                    # R's own micro-roughness grain
        M = np.clip(14 + np.clip(hero * 1.6, 0, 1) * 200 + gM * 60, 0, 255)  # feature ignition + broad
        R = np.clip(58 + gR * 150, 15, 255)                                  # independent grain (decoupled from M/Cc)
        Cc = np.clip(20 + fine * 130 + _n(h, w, s ^ 0x4D, (3, 7)) * 55, 16, 255)  # fine detail + own low-freq
        return M, R, Cc
    return f


def _mk_base_pair(fid, paint_build, spec_build):
    """Build (base_spec_fn, paint_fn) for a BASE_REGISTRY dict entry.
    base_spec_fn(shape, seed, sm, base_m, base_r) -> (M, R, Cc) full-res float."""
    _, paint_fn = _pair(fid, paint_build, spec_build)

    def base_spec_fn(shape, seed, sm, base_m=None, base_r=None, _b=spec_build, _f=fid, **_kw):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        M, R, Cc = _b(h, w, _seed_of(_f, seed))
        _msd = float(np.std(M))
        if 1e-3 < _msd < 20.0:
            _mm = float(np.mean(M)); M = np.clip(_mm + (M - _mm) * (20.0 / _msd), 0, 255)
        M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
        return np.clip(M, 0, 255), np.clip(R, 15, 255), np.clip(Cc, 16, 255)
    return base_spec_fn, paint_fn


def _install_ground_up(mono_reg, base_reg, prefix, paint_factory, spec_factory, recipe, idset=None):
    """Override every matching id in BOTH registries (base entries get the base
    contract, monolithic entries the (spec_fn, paint_fn) tuple). If `idset` is
    given, match by membership (exact allowlist) instead of prefix."""
    match = (lambda k: k in idset) if idset is not None else (lambda k: k.startswith(prefix))
    ids = set()
    if base_reg:
        for fid in list(base_reg.keys()):
            if not match(fid):
                continue
            be = base_reg.get(fid)
            if not (isinstance(be, dict) and "base_spec_fn" in be):
                continue
            pal, mode, freq = recipe(fid)
            bsf, pfn = _mk_base_pair(fid, paint_factory(pal, mode, freq), spec_factory(pal, mode, freq))
            be["base_spec_fn"] = bsf; be["paint_fn"] = pfn
            ids.add(fid)
    for fid in list(mono_reg.keys()):
        if not match(fid):
            continue
        pal, mode, freq = recipe(fid)
        mono_reg[fid] = _pair(fid, paint_factory(pal, mode, freq), spec_factory(pal, mode, freq))
        ids.add(fid)
    return len(ids)


def install_gradients(mono_reg, base_reg=None):
    return _install_ground_up(mono_reg, base_reg, "grad_", _grad_paint_fn, _grad_spec_fn, _grad_recipe)


# ===========================================================================
# PRISM FORGE (50 pf_*) — TOTAL ground-up, prismatic/spectral. Reuses the
# gradient structure engine but with a PRISMATIC paint factory (high iridescent
# travel + full-spectrum shimmer on the hero feature). Rainbow fallback for the
# abstract spectral names (apex_spectrum, prismatic_void_madness, hyperwave...).
# ===========================================================================
PF_WORDS = {
    "solar": (0.95, 0.55, 0.10), "daffodil": (0.95, 0.85, 0.12), "canary": (0.96, 0.90, 0.18),
    "seafoam": (0.40, 0.90, 0.70), "orchid": (0.80, 0.40, 0.85), "magenta": (0.90, 0.10, 0.60),
    "hyperpink": (0.98, 0.10, 0.55), "tar": (0.03, 0.03, 0.04), "bitumen": (0.05, 0.05, 0.06),
    "obsidian": (0.04, 0.04, 0.06), "coal": (0.05, 0.05, 0.05), "gild": (0.85, 0.68, 0.20),
    "eclipse": (0.06, 0.05, 0.10), "iris": (0.50, 0.30, 0.80), "tidepool": (0.05, 0.50, 0.50),
    "pearl": (0.85, 0.85, 0.90), "void": (0.02, 0.02, 0.05), "nova": (0.70, 0.85, 1.0),
    "inferno": (0.85, 0.20, 0.04), "sunrise": (0.98, 0.55, 0.35), "moon": (0.80, 0.82, 0.86),
    "glacial": (0.60, 0.80, 0.92), "oil": (0.10, 0.12, 0.15), "quantum": (0.20, 0.40, 0.90),
    "crystal": (0.80, 0.88, 0.95), "velvet": (0.25, 0.10, 0.32), "venetian": (0.60, 0.10, 0.10),
    "mage": (0.45, 0.15, 0.72), "ocean": (0.04, 0.30, 0.45), "golden": (0.85, 0.65, 0.15),
    "ultraviolet": (0.35, 0.10, 0.80), "cyan": (0.10, 0.80, 0.85), "sunset": (0.92, 0.45, 0.30),
    "blood": (0.55, 0.04, 0.06), "fire": (0.85, 0.20, 0.05), "halo": (0.70, 0.78, 0.92),
}
PF_CONCEPTS = {
    "event_horizon_spectra": [(0.02, 0.02, 0.05), (0.45, 0.08, 0.70), (0.10, 0.30, 0.90), (0.95, 0.55, 0.10), (0.05, 0.80, 0.75)],
    "chromatic_storm": list(RAINBOW),
    "apex_spectrum": list(RAINBOW),
    "spectrum_chaos_crown": list(RAINBOW),
    "prismatic_void_madness": [(0.02, 0.02, 0.04)] + list(RAINBOW),
    "hyperwave": [(0.05, 0.10, 0.45), (0.10, 0.70, 0.90), (0.80, 0.10, 0.70), (0.40, 0.20, 0.95)],
    "spectral_tidepool_wash": [(0.03, 0.30, 0.40), (0.05, 0.60, 0.62), (0.30, 0.40, 0.85), (0.55, 0.20, 0.80)],
    "iris_velvet_crossfade": [(0.25, 0.10, 0.45), (0.50, 0.15, 0.78), (0.20, 0.25, 0.85), (0.80, 0.30, 0.80)],
    "white_castle_of_fear": [(0.85, 0.85, 0.92), (0.45, 0.50, 0.62), (0.15, 0.16, 0.24), (0.55, 0.20, 0.55)],
}


def _pf_palette(core):
    if core in PF_CONCEPTS:
        return [tuple(map(float, c)) for c in PF_CONCEPTS[core]]
    if core in CONCEPT_PALETTES:
        return [tuple(map(float, c)) for c in CONCEPT_PALETTES[core]]
    lut = dict(COLOR_WORDS); lut.update(PF_WORDS)
    cols = [lut[t] for t in core.split("_") if t in lut]
    if len(cols) >= 2:
        return [tuple(map(float, c)) for c in cols]
    if len(cols) == 1:
        c = cols[0]
        return [tuple(np.clip(np.float32(c) * 0.30, 0, 1)), tuple(map(float, c)), (0.10, 0.70, 0.90), (0.85, 0.10, 0.60)]
    return [tuple(map(float, c)) for c in RAINBOW]                       # prismatic fallback for abstract names


def _pf_paint_fn(pal, mode, freq):
    base = tuple(np.clip(np.float32(pal[0]) * 0.40, 0, 1)); hi = np.float32(pal[-1])

    def f(h, w, s):
        st, hero, fine = _grad_struct(h, w, s, mode, freq)
        col = _travel(st, pal, irid=0.38, cycles=3.2, sat=0.85, smooth=0.45, base=base)
        spectro = _travel(fine, RAINBOW, irid=0.0, smooth=0.30)          # prismatic shimmer
        col = col * (0.60 + fine[..., None] * 0.42) + hero[..., None] * hi[None, None, :] * 0.32 + spectro * (hero[..., None] * 0.28)
        return np.clip(col, 0, 1)
    return f


def _pf_recipe(fid):
    core = fid[3:] if fid.startswith("pf_") else fid
    for pre in ("cluster_", "bright_", "blend_", "tri_", "quad_", "fade_", "gradient_"):
        if core.startswith(pre):
            core = core[len(pre):]; break
    pal = _pf_palette(core)
    pf_modes = ["spiral", "swirl", "caustic", "interference", "flow", "facet", "pool", "marble"]
    mode = pf_modes[int(_hash01(core, 17) * len(pf_modes)) % len(pf_modes)]
    freq = 3 + int(_hash01(fid, 19) * 6)
    return pal, mode, freq


def install_prismforge(mono_reg, base_reg=None):
    return _install_ground_up(mono_reg, base_reg, "pf_", _pf_paint_fn, _grad_spec_fn, _pf_recipe)


# ===========================================================================
# MONEY SHOKK (40: msh_/mshc_/msha_/mshx_) — TOTAL ground-up. Bold luxe:
# a hero color (from the name) on a near-black base + GOLD ignition on the
# hero feature (money). High saturation, high contrast, motif-driven structure.
# ===========================================================================
MSH_WORDS = {
    "tigerblood": (0.85, 0.25, 0.05), "oxblood": (0.35, 0.04, 0.06), "acid": (0.60, 0.90, 0.05),
    "neonice": (0.40, 0.90, 0.95), "rosethorn": (0.80, 0.20, 0.35), "fuji": (0.55, 0.70, 0.88),
    "volcanic": (0.55, 0.10, 0.04), "cherry": (0.90, 0.20, 0.35), "waxen": (0.85, 0.82, 0.70),
    "blueprint": (0.10, 0.35, 0.75), "glacier": (0.60, 0.82, 0.92), "miami": (0.10, 0.75, 0.75),
    "royal": (0.25, 0.12, 0.65), "dover": (0.85, 0.86, 0.90), "kintsugi": (0.85, 0.68, 0.20),
    "oni": (0.70, 0.08, 0.10), "venom": (0.20, 0.72, 0.10), "prism": (0.55, 0.30, 0.85),
    "emerald": (0.05, 0.60, 0.35), "amber": (0.86, 0.55, 0.12), "coral": (0.95, 0.45, 0.35),
}


def _msh_palette(core):
    first = core.split("_")[0]
    lut = dict(COLOR_WORDS); lut.update(PF_WORDS); lut.update(MSH_WORDS)
    hero = np.float32(lut.get(first, (0.88, 0.10, 0.50)))                 # default hot luxe pink
    return [(0.015, 0.015, 0.02), tuple(np.clip(hero * 0.45, 0, 1)), tuple(map(float, hero)), (0.86, 0.68, 0.22)]


def _msh_paint_fn(pal, mode, freq):
    base = tuple(np.float32(pal[0])); gold = np.float32(pal[3])

    def f(h, w, s):
        st, hero, fine = _grad_struct(h, w, s, mode, freq)
        col = _travel(st, pal, irid=0.22, cycles=2.4, sat=0.95, smooth=0.40, base=base)
        col = col * (0.50 + fine[..., None] * 0.55) + hero[..., None] * gold[None, None, :] * 0.45  # gold luxe ignition
        return np.clip(col, 0, 1)
    return f


def _msh_recipe(fid):
    core = fid
    for pre in ("mshc_", "msha_", "mshx_", "msh_"):
        if core.startswith(pre):
            core = core[len(pre):]; break
    pal = _msh_palette(core)
    msh_modes = ["facet", "marble", "spiral", "ridge", "swirl", "flow", "interference"]
    mode = msh_modes[int(_hash01(core, 23) * len(msh_modes)) % len(msh_modes)]
    freq = 3 + int(_hash01(fid, 29) * 6)
    return pal, mode, freq


def install_moneyshokk(mono_reg, base_reg=None):
    return _install_ground_up(mono_reg, base_reg, "msh", _msh_paint_fn, _grad_spec_fn, _msh_recipe)


# ===========================================================================
# COLOR SCIENCE cs_ shift (110: Adaptive 15 + Presets 16 + Duos 79) — TOTAL
# ground-up. Color-SHIFT / duochrome: a flowing structure carrying a clear
# A<->B (or themed) color travel by angle. EXPLICIT allowlist (never a blind
# cs_ prefix scan) so unrelated ids are never touched.
# ===========================================================================
CS_WORDS = {
    "black": (0.04, 0.04, 0.05), "silver": (0.75, 0.77, 0.80), "gunmetal": (0.28, 0.30, 0.34),
    "candy": (0.90, 0.10, 0.40), "yellow": (0.95, 0.85, 0.10), "flame": (0.90, 0.30, 0.05),
    "neon": (0.10, 0.95, 0.75), "chrome": (0.72, 0.76, 0.82), "earth": (0.45, 0.32, 0.18),
}
CS_CONCEPTS = {
    "cool": [(0.02, 0.10, 0.25), (0.05, 0.45, 0.70), (0.20, 0.75, 0.85), (0.55, 0.85, 0.92)],
    "warm": [(0.30, 0.04, 0.02), (0.80, 0.25, 0.05), (0.95, 0.55, 0.10), (1.0, 0.85, 0.40)],
    "complementary": [(0.05, 0.20, 0.55), (0.20, 0.45, 0.85), (0.95, 0.50, 0.10), (0.98, 0.72, 0.30)],
    "monochrome": [(0.03, 0.03, 0.04), (0.30, 0.31, 0.34), (0.62, 0.64, 0.68), (0.92, 0.93, 0.96)],
    "subtle": [(0.20, 0.24, 0.30), (0.40, 0.46, 0.52), (0.58, 0.62, 0.66), (0.78, 0.80, 0.82)],
    "rainbow": list(RAINBOW), "vivid": list(RAINBOW), "prism": list(RAINBOW),
    "extreme": [(0.90, 0.05, 0.60), (0.05, 0.85, 0.92), (0.60, 0.95, 0.10), (0.55, 0.10, 0.90)],
    "triadic": [(0.80, 0.10, 0.12), (0.10, 0.60, 0.22), (0.12, 0.25, 0.80), (0.90, 0.80, 0.15)],
    "split": [(0.05, 0.50, 0.52), (0.45, 0.18, 0.72), (0.95, 0.50, 0.12), (0.85, 0.80, 0.40)],
    "earth": [(0.20, 0.14, 0.06), (0.45, 0.32, 0.16), (0.30, 0.42, 0.18), (0.70, 0.62, 0.42)],
    "deepocean": [(0.01, 0.06, 0.18), (0.02, 0.24, 0.42), (0.05, 0.50, 0.55), (0.35, 0.78, 0.78)],
    "solarflare": [(0.35, 0.08, 0.02), (0.85, 0.35, 0.04), (1.0, 0.70, 0.12), (1.0, 0.95, 0.65)],
    "inferno": [(0.04, 0.01, 0.01), (0.55, 0.05, 0.02), (0.92, 0.28, 0.04), (1.0, 0.72, 0.18)],
    "nebula": [(0.04, 0.02, 0.12), (0.30, 0.08, 0.45), (0.55, 0.10, 0.55), (0.15, 0.30, 0.70)],
    "mystichrome": [(0.07, 0.02, 0.13), (0.10, 0.45, 0.40), (0.06, 0.55, 0.20), (0.40, 0.20, 0.62)],
    "supernova": [(0.05, 0.05, 0.12), (0.30, 0.40, 0.85), (0.70, 0.55, 0.95), (0.95, 0.95, 1.0)],
    "emerald": [(0.02, 0.20, 0.12), (0.05, 0.55, 0.32), (0.30, 0.70, 0.20), (0.90, 0.78, 0.30)],
    "candypaint": [(0.30, 0.02, 0.08), (0.80, 0.08, 0.30), (0.95, 0.45, 0.62), (0.98, 0.85, 0.88)],
    "oilslick": [(0.03, 0.03, 0.05)] + list(RAINBOW),
    "goldrush": [(0.25, 0.16, 0.04), (0.55, 0.40, 0.10), (0.85, 0.66, 0.20), (0.98, 0.90, 0.55)],
    "toxic": [(0.04, 0.10, 0.02), (0.25, 0.55, 0.05), (0.60, 0.88, 0.08), (0.85, 0.98, 0.25)],
    "darkflame": [(0.03, 0.02, 0.04), (0.45, 0.05, 0.10), (0.80, 0.12, 0.20), (0.55, 0.10, 0.55)],
    "twilight": [(0.04, 0.06, 0.22), (0.18, 0.10, 0.42), (0.45, 0.16, 0.52), (0.88, 0.42, 0.58)],
    "neon_dreams": [(0.05, 0.02, 0.12), (0.90, 0.10, 0.62), (0.10, 0.85, 0.92), (0.60, 0.95, 0.20)],
}
CS_IDS = [
    "cs_cool", "cs_warm", "cs_complementary", "cs_monochrome", "cs_subtle", "cs_rainbow", "cs_vivid",
    "cs_extreme", "cs_triadic", "cs_split", "cs_neon_shift", "cs_ocean_shift", "cs_chrome_shift",
    "cs_earth", "cs_prism_shift",
    "cs_deepocean", "cs_solarflare", "cs_inferno", "cs_nebula", "cs_mystichrome", "cs_supernova",
    "cs_emerald", "cs_candypaint", "cs_oilslick", "cs_rose_gold_shift", "cs_goldrush", "cs_toxic",
    "cs_darkflame", "cs_rosegold", "cs_twilight", "cs_neon_dreams",
    "cs_amber_indigo", "cs_aqua_maroon", "cs_black_blue", "cs_black_gold", "cs_black_red", "cs_black_silver",
    "cs_blue_orange", "cs_blush_emerald", "cs_bronze_green", "cs_bronze_navy", "cs_bronze_purple", "cs_bronze_red",
    "cs_burgundy_gold", "cs_candy_paint", "cs_champagne_cobalt", "cs_charcoal_honey", "cs_chocolate_mint",
    "cs_copper_blue", "cs_copper_gold", "cs_copper_lime", "cs_copper_teal", "cs_copper_violet", "cs_coral_cobalt",
    "cs_crimson_jade", "cs_dark_flame", "cs_fire_ice", "cs_gold_emerald", "cs_gold_navy", "cs_gold_rush",
    "cs_graphite_coral", "cs_green_blue", "cs_green_gold", "cs_gunmetal_gold", "cs_gunmetal_lime",
    "cs_gunmetal_orange", "cs_honey_plum", "cs_ivory_indigo", "cs_lavender_jade", "cs_lime_blue", "cs_lime_pink",
    "cs_lime_violet", "cs_magenta_blue", "cs_magenta_gold", "cs_magenta_teal", "cs_mint_maroon", "cs_navy_gold",
    "cs_navy_orange", "cs_navy_silver", "cs_orange_navy", "cs_orange_purple", "cs_peach_cobalt", "cs_pewter_rose",
    "cs_pink_gold", "cs_pink_purple", "cs_pink_teal", "cs_purple_gold", "cs_purple_lime", "cs_red_black",
    "cs_red_gold", "cs_red_purple", "cs_rose_emerald", "cs_sage_crimson", "cs_silver_purple", "cs_silver_red",
    "cs_silver_teal", "cs_sky_gold", "cs_slate_amber", "cs_sunset_ocean", "cs_teal_orange", "cs_teal_pink",
    "cs_titanium_crimson", "cs_violet_gold", "cs_violet_teal", "cs_white_blue", "cs_white_green", "cs_white_purple",
    "cs_white_red", "cs_yellow_blue",
]


def _cs_palette(core):
    core = core.replace("_shift", "")
    if core in CS_CONCEPTS:
        return [tuple(map(float, c)) for c in CS_CONCEPTS[core]]
    if core in CONCEPT_PALETTES:
        return [tuple(map(float, c)) for c in CONCEPT_PALETTES[core]]
    lut = dict(COLOR_WORDS); lut.update(PF_WORDS); lut.update(MSH_WORDS); lut.update(CS_WORDS)
    toks = [lut[t] for t in core.split("_") if t in lut]
    if len(toks) >= 2:
        a = np.float32(toks[0]); b = np.float32(toks[-1])                 # duochrome A<->B travel
        return [tuple(np.clip(a * 0.32, 0, 1)), tuple(map(float, a)), tuple(map(float, b)), tuple(np.clip(b * 0.55 + 0.45, 0, 1))]
    if len(toks) == 1:
        c = np.float32(toks[0]); comp = tuple(np.clip(1.0 - c, 0, 1))
        return [tuple(np.clip(c * 0.30, 0, 1)), tuple(map(float, c)), comp, (0.85, 0.85, 0.90)]
    return [tuple(map(float, c)) for c in RAINBOW]


def _cs_paint_fn(pal, mode, freq):
    base = tuple(np.clip(np.float32(pal[0]) * 0.6, 0, 1)); hi = np.float32(pal[-1])

    def f(h, w, s):
        st, hero, fine = _grad_struct(h, w, s, mode, freq)
        col = _travel(st, pal, irid=0.30, cycles=2.6, sat=0.85, smooth=0.55, base=base)  # clear A<->B shift
        col = col * (0.62 + fine[..., None] * 0.45) + hero[..., None] * hi[None, None, :] * 0.25
        return np.clip(col, 0, 1)
    return f


def _cs_recipe(fid):
    core = fid[3:] if fid.startswith("cs_") else fid
    pal = _cs_palette(core)
    cs_modes = ["flow", "marble", "caustic", "interference", "swirl", "spiral", "facet", "pool", "ridge"]
    mode = cs_modes[int(_hash01(core, 31) * len(cs_modes)) % len(cs_modes)]
    freq = 3 + int(_hash01(fid, 37) * 6)
    return pal, mode, freq


def install_csshift(mono_reg, base_reg=None):
    return _install_ground_up(mono_reg, base_reg, "cs_", _cs_paint_fn, _grad_spec_fn, _cs_recipe, idset=set(CS_IDS))


# ===========================================================================
# SHOKK SERIES (final, ~25) — energy/sci-fi. Bold electric travel + dramatic
# structure. EXPLICIT allowlist EXCLUDING owner keepers (shokk_tesseract_v2,
# shokk_cipher, shokk_helix, shokk_venom, burnt_headers).
# ===========================================================================
SHOKK_CONCEPTS = {
    "electric_ice": [(0.02, 0.05, 0.15), (0.10, 0.40, 0.80), (0.40, 0.80, 0.95), (0.85, 0.95, 1.0)],
    "mercury": [(0.10, 0.10, 0.12), (0.40, 0.42, 0.46), (0.70, 0.72, 0.78), (0.92, 0.93, 0.96)],
    "plasma_metal": [(0.05, 0.02, 0.12), (0.60, 0.05, 0.70), (0.10, 0.60, 0.85), (0.85, 0.30, 0.90)],
    "shokk_blood": [(0.05, 0.0, 0.0), (0.40, 0.02, 0.04), (0.75, 0.06, 0.08), (0.95, 0.30, 0.20)],
    "shokk_pulse": [(0.02, 0.05, 0.10), (0.10, 0.50, 0.70), (0.70, 0.10, 0.50), (0.95, 0.80, 0.20)],
    "shokk_static": [(0.05, 0.05, 0.06), (0.30, 0.30, 0.33), (0.60, 0.62, 0.66), (0.90, 0.90, 0.92)],
    "shokk_void": [(0.01, 0.01, 0.03), (0.08, 0.06, 0.14), (0.20, 0.10, 0.30), (0.45, 0.25, 0.60)],
    "volcanic": [(0.03, 0.01, 0.01), (0.50, 0.05, 0.02), (0.90, 0.28, 0.04), (1.0, 0.70, 0.15)],
    "shokk_flux": [(0.04, 0.06, 0.12), (0.10, 0.55, 0.60), (0.50, 0.20, 0.75), (0.90, 0.60, 0.20)],
    "shokk_phase": [(0.06, 0.04, 0.12), (0.20, 0.30, 0.70), (0.60, 0.20, 0.60), (0.20, 0.70, 0.70)],
    "shokk_dual": [(0.05, 0.05, 0.08), (0.80, 0.20, 0.10), (0.10, 0.40, 0.85), (0.90, 0.85, 0.40)],
    "shokk_spectrum": list(RAINBOW),
    "shokk_aurora": [(0.02, 0.06, 0.10), (0.03, 0.50, 0.30), (0.10, 0.40, 0.70), (0.45, 0.15, 0.60)],
    "shokk_catalyst": [(0.04, 0.08, 0.04), (0.30, 0.70, 0.10), (0.70, 0.90, 0.20), (0.20, 0.60, 0.80)],
    "shokk_mirage": [(0.10, 0.08, 0.04), (0.60, 0.50, 0.20), (0.30, 0.60, 0.70), (0.85, 0.80, 0.60)],
    "shokk_polarity": [(0.02, 0.04, 0.10), (0.10, 0.30, 0.85), (0.90, 0.30, 0.10), (0.90, 0.90, 0.95)],
    "shokk_reactor": [(0.02, 0.06, 0.04), (0.10, 0.70, 0.40), (0.70, 0.95, 0.20), (0.90, 1.0, 0.60)],
    "shokk_prism": list(RAINBOW),
    "shokk_wraith": [(0.03, 0.05, 0.06), (0.20, 0.35, 0.40), (0.45, 0.60, 0.62), (0.70, 0.85, 0.85)],
    "shokk_fusion_base": [(0.04, 0.02, 0.08), (0.70, 0.20, 0.40), (0.20, 0.50, 0.85), (0.95, 0.70, 0.30)],
    "shokk_rift": [(0.02, 0.02, 0.06), (0.30, 0.05, 0.40), (0.60, 0.10, 0.70), (0.20, 0.40, 0.90)],
    "shokk_vortex": [(0.03, 0.04, 0.10), (0.10, 0.45, 0.70), (0.50, 0.20, 0.70), (0.85, 0.50, 0.20)],
    "shokk_surge": [(0.02, 0.06, 0.12), (0.10, 0.60, 0.85), (0.50, 0.85, 0.95), (0.95, 0.95, 0.60)],
    "shokk_inferno": [(0.04, 0.01, 0.01), (0.60, 0.06, 0.02), (0.95, 0.30, 0.04), (1.0, 0.80, 0.20)],
    "shokk_apex": [(0.05, 0.04, 0.10), (0.50, 0.10, 0.60), (0.10, 0.60, 0.85), (0.95, 0.85, 0.30)],
}
SHOKK_IDS = list(SHOKK_CONCEPTS.keys())                                   # 25, excludes the 5 keepers


def _shokk_paint_fn(pal, mode, freq):
    base = tuple(np.clip(np.float32(pal[0]) * 0.55, 0, 1)); hi = np.float32(pal[-1])

    def f(h, w, s):
        st, hero, fine = _grad_struct(h, w, s, mode, freq)
        col = _travel(st, pal, irid=0.28, cycles=2.8, sat=0.90, smooth=0.45, base=base)
        col = col * (0.55 + fine[..., None] * 0.50) + hero[..., None] * hi[None, None, :] * 0.40  # electric core glow
        return np.clip(col, 0, 1)
    return f


def _shokk_recipe(fid):
    pal = [tuple(map(float, c)) for c in SHOKK_CONCEPTS.get(fid, RAINBOW)]
    modes = ["caustic", "swirl", "spiral", "flow", "interference", "ridge", "facet", "marble", "pool"]
    mode = modes[int(_hash01(fid, 41) * len(modes)) % len(modes)]
    freq = 3 + int(_hash01(fid, 43) * 6)
    return pal, mode, freq


def install_shokkseries(mono_reg, base_reg=None):
    return _install_ground_up(mono_reg, base_reg, "shokk_", _shokk_paint_fn, _grad_spec_fn, _shokk_recipe, idset=set(SHOKK_IDS))


def _self_test():
    import time
    def corr(a, b):
        a = a.astype(np.float64).ravel() - a.mean(); b = b.astype(np.float64).ravel() - b.mean()
        return float((a * b).sum() / ((np.sqrt((a * a).sum()) * np.sqrt((b * b).sum())) + 1e-9))
    print("color_science_rebuild_2026 — CHAMELEON self-test (1024)")
    ones = np.ones((1024, 1024), np.float32)
    for fid, _, _ in _ALL_REBUILDS:
        sfn, pfn = REBUILD_MONOLITHICS[fid]
        t = time.time()
        spec = sfn((1024, 1024), ones, 7, 1.0)
        pnt = pfn(np.zeros((1024, 1024, 3), np.float32), (1024, 1024), ones, 7, 1.0, None)
        dt = time.time() - t
        M, R, Cc = spec[:, :, 0], spec[:, :, 1], spec[:, :, 2]
        mx = max(abs(corr(M, R)), abs(corr(M, Cc)), abs(corr(R, Cc)))
        iron = bool(((Cc == 0) | (Cc >= 16)).all() and (R[M < 240] >= 15).all())
        print(f"  {fid:22s} {dt:4.2f}s maxcorr={mx:.2f} M.std={float(M.std()):5.1f} "
              f"paint[{float(pnt.min()):.2f}..{float(pnt.max()):.2f}] iron={iron}")


if __name__ == "__main__":
    _self_test()
