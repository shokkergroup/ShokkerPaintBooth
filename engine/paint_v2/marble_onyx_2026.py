# -*- coding: utf-8 -*-
"""
engine/paint_v2/marble_onyx_2026.py — ★ MARBLE & ONYX (full bespoke rebuild 2026-06-15)

20 luxury polished-stone slabs. OWNER COMPLAINT (verbatim) on the old version:
"Tons of repeating vein patterns and ALL flat green specs." — the old module was a single
_stone() factory + per-finish color params, and _stone_spec() returned M=0 / CC=16 flat with
only R rippling on grain (i.e. the spec read as one flat green). THIS REWRITE TEARS THAT OUT.

DOCTRINE applied here:
  * Every stone gets its OWN veining/structure ALGORITHM (not one vein template recolored):
      marble_carrara    fine grey hairline fracture lattice
      marble_calacatta  bold dramatic gold trunk-and-branch veins
      marble_nero       Nero Marquina — black with sharp white fracture web
      marble_portoro     black with broad meandering GOLD rivers (flow-warped ridges)
      onyx_emerald      translucent layered onyx banding (back-lit depth)
      agate_blue        concentric agate bands around scattered nuclei
      marble_rose       soft rose CLOUDING (no hard veins — diffuse blooms)
      travertine        pitted/porous travertine (drilled voids + stratified layers)
      marble_verde_alpi serpentine breccia — angular fragments + serpentine veinlets
      marble_rosso      Rosso Levanto breccia — red plates caged by white calcite seams
      onyx_honey        honey onyx — warm translucent ribbon banding
      marble_statuario  sparse dramatic statuario veins on bright white
      onyx_pink         pink onyx swirl banding (rotational flow)
      lapis_lazuli      deep ultramarine + PYRITE gold flecks + calcite veinlets
      amethyst          amethyst crystal druzy (faceted geode points)
      tiger_iron        layered tiger-iron bands (hematite / jasper / gold tiger-eye silk)
      marble_bardiglio  Bardiglio grey — soft directional cloud striations
      onyx_white        white onyx — fine translucent feathered banding
      marble_fusion     multi-stone breccia fusion (cells of different stones + gold seams)
      obsidian_gold     black obsidian with gold sheen flow-lines + conchoidal fracture
  * Polished-stone SPEC: clearcoat/roughness FOLLOW the veins — wet gloss in the matrix,
    drier veins; M / R / CC ride DIFFERENT geometry & value distributions so the combined
    map (R=M,G=R,B=CC) reads MULTI-HUE (blues/oranges/teals/purples), never flat green.
    Channels are decorrelated by construction (|corr| < 0.85). Each spec recomputes the
    SAME fields the paint used (same seed/helpers) so it ignites the exact features shown.

Contracts: paint_x(paint,shape,mask,seed,pm,bb)->HxWx3 ; spec_x(shape,seed,sm,bm,br)->(M,R,CC)
  M = metalness 0..255 ; R = roughness (floor 15) ; CC = clearcoat (16=wet gloss). sm scales contrast.
FINE detail (full-res veins/flecks), UV-orientation-agnostic, < 3s @ 2048 (work-res caps + cKDTree).
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid, _resize_array, hsv_to_rgb_vec
from engine.color_science import interference_palette

try:
    import cv2 as _cv2
    _CV2 = True
except Exception:  # pragma: no cover
    _cv2 = None
    _CV2 = False

_MB_CACHE = {}


def _cache(key, fn):
    v = _MB_CACHE.get(key)
    if v is None:
        if len(_MB_CACHE) > 200:
            _MB_CACHE.clear()
        v = fn()
        _MB_CACHE[key] = v
    return v


def _norm01(a):
    a = np.asarray(a, dtype=np.float32)
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-7:
        return np.zeros_like(a, dtype=np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _noise(shape, scales, weights, seed, cap=560):
    """Multi-scale noise with a work-res cap so big smooth fields stay <3s @2048.
    These fields are low-frequency clouds/warps, so a 560px work grid upsamples cleanly."""
    h, w = shape[:2]
    key = ("n", h, w, tuple(scales), tuple(weights), int(seed), int(cap))

    def build():
        if cap and min(h, w) > cap:
            sh = max(64, int(round(h * cap / max(h, w))))
            sw = max(64, int(round(w * cap / max(h, w))))
            f = multi_scale_noise((sh, sw), scales, weights, seed)
            return _resize_array(np.asarray(f, np.float32), h, w)
        return np.asarray(multi_scale_noise((h, w), scales, weights, seed), np.float32)

    return _cache(key, build)


def _grain(shape, seed):
    """Full-res fine stone grain (kept crisp — this is the fineness layer)."""
    h, w = shape[:2]
    key = ("g", h, w, int(seed))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x6CA3) & 0xFFFFFFFF)
        n = rng.random((h, w), dtype=np.float32)
        return ((n + np.roll(n, 1, 0) + np.roll(n, 1, 1)) * 0.333).astype(np.float32)

    return _cache(key, build)


def _rot(shape, deg):
    h, w = shape[:2]
    a = np.deg2rad(deg); ca, sa = np.cos(a), np.sin(a)
    y, x = get_mgrid((h, w))
    return (x * ca + y * sa).astype(np.float32), (-x * sa + y * ca).astype(np.float32)


def _blur(a, px):
    if _CV2 and px > 0:
        return _cv2.GaussianBlur(np.asarray(a, np.float32), (0, 0), float(px))
    return np.asarray(a, np.float32)


# --------------------------------------------------------------------------- #
# Distinct STRUCTURE primitives — each stone wires these DIFFERENTLY (no shared
# recolor template). Heavy ones run at work-res then resize.
# --------------------------------------------------------------------------- #
def _vein_network(shape, seed, n_trunks, freq, sharp, warp_amt, branch=True, cap=420):
    """Branching vein NETWORK: distance-to-flowing-curves ridge field, 0..1 vein mask.
    Distinct curvy trunks (Calacatta/Statuario). Built at a 480px work grid then upsampled —
    ridges are smooth so it resizes crisply and keeps 2048 well under 3s even with 8 trunks."""
    h, w = shape[:2]
    key = ("vn", h, w, int(seed), int(n_trunks), float(freq), float(sharp), float(warp_amt), bool(branch), cap)

    def build():
        sh = cap if h >= w else max(64, int(round(cap * h / w)))
        sw = cap if w >= h else max(64, int(round(cap * w / h)))
        sh = min(sh, h); sw = min(sw, w)
        fscale = max(h, w) / float(max(sh, sw))
        y, x = np.mgrid[0:sh, 0:sw].astype(np.float32)
        warpx = np.asarray(multi_scale_noise((sh, sw), [40, 90], [0.6, 0.4], seed + 11), np.float32)
        warpy = np.roll(warpx, sh // 3, axis=0)        # cheap 2nd warp (skip a noise build)
        rng = np.random.default_rng((int(seed) ^ 0x91A7) & 0xFFFFFFFF)
        acc = np.zeros((sh, sw), np.float32)
        for k in range(int(n_trunks)):
            ang = rng.uniform(0, np.pi)
            ph = rng.uniform(0, 2 * np.pi)
            ca, sa = np.cos(ang), np.sin(ang)
            u = (x * ca + y * sa) + warpx * (warp_amt / fscale)
            v = (-x * sa + y * ca) + warpy * (warp_amt / fscale)
            # main meandering trunk = a sinuous line in v
            line = v - (np.sin(u * freq * fscale + ph) * (6.0 / fscale) + np.sin(u * freq * fscale * 2.3 + ph) * (3.0 / fscale))
            t = np.exp(-(line * line) * (sharp * 0.5 / (fscale * fscale)))
            acc = np.maximum(acc, t)
            if branch:  # finer offshoot ridges, perpendicular-ish
                line2 = u * 0.6 + v - (np.sin(v * freq * fscale * 1.7 + ph * 1.3) * (4.0 / fscale))
                acc = np.maximum(acc, np.exp(-(line2 * line2) * (sharp * 1.4 / (fscale * fscale))) * 0.6)
        acc = np.clip(acc, 0, 1)
        if (sh, sw) != (h, w):
            acc = _resize_array(acc, h, w)
        return acc.astype(np.float32)

    return _cache(key, build)


def _fracture_web(shape, seed, n, cap=680):
    """Sharp angular FRACTURE web (Voronoi ridge edges) — crackle hairlines.
    Returns (edge 0..1, cell_id 0..1). cKDTree at work-res then upsampled (the seam
    network stays crisp because the resize preserves the ridge geometry)."""
    from scipy.spatial import cKDTree
    h, w = shape[:2]
    key = ("fw", h, w, int(seed), int(n), cap)

    def build():
        sh = cap if h >= w else max(64, int(round(cap * h / w)))
        sw = cap if w >= h else max(64, int(round(cap * w / h)))
        sh = min(sh, h); sw = min(sw, w)
        rng = np.random.default_rng((int(seed) ^ 0x33B5) & 0xFFFFFFFF)
        pts = np.column_stack([rng.uniform(0, sh, n), rng.uniform(0, sw, n)]).astype(np.float32)
        ids = rng.random(n).astype(np.float32)
        yy, xx = np.mgrid[0:sh, 0:sw]
        grid = np.column_stack([yy.ravel(), xx.ravel()]).astype(np.float32)
        d, idx = cKDTree(pts).query(grid, k=2, workers=-1)
        cid = ids[idx[:, 0]].reshape(sh, sw)
        edge = np.clip(1.0 - (d[:, 1] - d[:, 0]).reshape(sh, sw) / 2.2, 0, 1)
        if (sh, sw) != (h, w):
            cid = _resize_array(cid.astype(np.float32), h, w)
            edge = _resize_array(edge.astype(np.float32), h, w)
        return edge.astype(np.float32), cid.astype(np.float32)

    return _cache(key, build)


def _agate_bands(shape, seed, n_nuclei, freq, cap=600):
    """Concentric agate bands around scattered nuclei (nearest-nucleus distance rings)."""
    h, w = shape[:2]
    key = ("ag", h, w, int(seed), int(n_nuclei), float(freq), cap)

    def build():
        sh = cap if h >= w else max(64, int(round(cap * h / w)))
        sw = cap if w >= h else max(64, int(round(cap * w / h)))
        sh = min(sh, h); sw = min(sw, w)
        fscale = max(h, w) / float(max(sh, sw))
        y, x = np.mgrid[0:sh, 0:sw].astype(np.float32)
        rng = np.random.default_rng((int(seed) ^ 0x7711) & 0xFFFFFFFF)
        acc = np.full((sh, sw), 1e9, np.float32)
        for _ in range(int(n_nuclei)):
            cy = rng.uniform(0, sh); cx = rng.uniform(0, sw)
            acc = np.minimum(acc, np.sqrt((y - cy) ** 2 + (x - cx) ** 2))
        warp = np.asarray(multi_scale_noise((sh, sw), [30, 70], [0.6, 0.4], seed + 9), np.float32) * 9.0
        rings = (0.5 + 0.5 * np.sin(acc * freq * fscale + warp)).astype(np.float32)
        if (sh, sw) != (h, w):
            rings = _resize_array(rings, h, w)
        return rings.astype(np.float32)

    return _cache(key, build)


def _flow_bands(shape, seed, freq, deg, warp_amt, oct2=False):
    """Flow-warped parallel banding (translucent onyx / portoro rivers / swirl)."""
    h, w = shape[:2]
    key = ("fb", h, w, int(seed), float(freq), float(deg), float(warp_amt), bool(oct2))

    def build():
        _u, v = _rot((h, w), deg)
        warp = _noise((h, w), [50, 110], [0.6, 0.4], seed + 7) * warp_amt
        b = 0.5 + 0.5 * np.sin(v * freq + warp)
        if oct2:
            b = 0.5 * b + 0.5 * (0.5 + 0.5 * np.sin(v * freq * 2.7 + warp * 1.6 + 1.1))
        return np.clip(b, 0, 1).astype(np.float32)

    return _cache(key, build)


def _swirl(shape, seed, freq, warp_amt):
    """Rotational swirl banding around a soft off-center pole (pink onyx)."""
    h, w = shape[:2]
    key = ("sw", h, w, int(seed), float(freq), float(warp_amt))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x5A21) & 0xFFFFFFFF)
        y, x = get_mgrid((h, w))
        cy = h * rng.uniform(0.3, 0.7); cx = w * rng.uniform(0.3, 0.7)
        ang = np.arctan2(y - cy, x - cx)
        rad = np.sqrt((y - cy) ** 2 + (x - cx) ** 2) / float(max(h, w))
        warp = _noise((h, w), [40, 90], [0.6, 0.4], seed + 3) * warp_amt
        return np.clip(0.5 + 0.5 * np.sin(ang * 3.0 + rad * freq + warp), 0, 1).astype(np.float32)

    return _cache(key, build)


def _flecks(shape, seed, density, smin=0.5, smax=1.0):
    """Scattered point flecks (pyrite / crystalline glints). Full-res, windowed splat."""
    h, w = shape[:2]
    rng = np.random.default_rng((int(seed) ^ 0xF1C9) & 0xFFFFFFFF)
    nf = min(int(h * w * density), 90000)
    fk = np.zeros((h, w), np.float32)
    yy = rng.integers(0, h, nf); xx = rng.integers(0, w, nf)
    fk[yy, xx] = rng.uniform(smin, smax, nf)
    return fk


# Paint colour is composed on a capped WORK grid (the per-finish HxWx3 arithmetic is the
# 2048 bottleneck); only the final grain + mask composite run at full res. All the crisp
# structure (veins/facets/seams) already comes from work-res fields that resize cleanly, so
# capping the colour grid is visually neutral and brings every paint well under 3s @2048.
_PCAP = 760


def _pshape(shape):
    """Work shape for paint colour composition (>= a sensible floor, capped at _PCAP)."""
    h, w = shape[:2]
    if max(h, w) <= _PCAP:
        return int(h), int(w)
    if h >= w:
        return _PCAP, max(64, int(round(_PCAP * w / h)))
    return max(64, int(round(_PCAP * h / w))), _PCAP


def _finish_paint(col, paint, mask, shape, seed, grain_amt=0.045):
    """Common tail: upsample work-res colour to full res, add full-res micro grain, mask.
    (Every stone's COLOR is computed bespoke at _pshape() before calling this.)"""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    col = np.asarray(col, np.float32)
    if col.shape[0] != h or col.shape[1] != w:
        if _CV2:
            col = _cv2.resize(col, (w, h), interpolation=_cv2.INTER_LINEAR)
        else:
            col = np.stack([_resize_array(col[:, :, c], h, w) for c in range(col.shape[2])], -1)
    g = _grain((h, w), seed + 3)[:, :, None]
    col = np.clip(col * (1.0 + grain_amt * (g - 0.5) * 2.0), 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)


def _mix(a, b, t):
    """Lerp by a HxW field t. a/b may be (3,) triples OR HxWx3 fields (mixed ok)."""
    a = np.asarray(a, np.float32); b = np.asarray(b, np.float32)
    if a.ndim == 1:
        a = a[None, None, :]
    if b.ndim == 1:
        b = b[None, None, :]
    t = np.asarray(t, np.float32)[:, :, None]
    return (a + (b - a) * t).astype(np.float32)


def _pack(M, R, CC):
    return (np.asarray(M, np.float32), np.asarray(R, np.float32), np.asarray(CC, np.float32))


# =====================================================================
# Polished-stone spec recipe (the anti-"flat green" core)
# ---------------------------------------------------------------------
# THE FIX for "all flat green specs": the combined map (R=M,G=R,B=CC) only
# shows many hues if EACH channel has real area both above AND below the
# perceptual midpoint, on DIFFERENT geometry. So:
#   M  (viz red)   rides a mineral/metal motif: low matrix -> HIGH (>mid) sheen.
#   R  (viz green) rides the vein/grain field : honed matrix (~mid) -> dry veins.
#   CC (viz blue)  rides its OWN gloss-pooling field: wet (low) -> dull (HIGH),
#                  deliberately crossing mid so blue actually appears.
# Physical meaning is preserved (wet matrix is glossier than dry veins) but each
# channel is authored to a wide, decorrelated distribution. caller MUST pass three
# genuinely different fields for vein / m_field / gloss_field.
# =====================================================================
def _ds(a, sh, sw):
    """Downsample a 2D field to (sh,sw) for work-res spec arithmetic."""
    a = np.asarray(a, np.float32)
    if a.shape[0] == sh and a.shape[1] == sw:
        return a
    if _CV2:
        return _cv2.resize(a, (sw, sh), interpolation=_cv2.INTER_AREA)
    return _resize_array(a, sh, sw)


def _us(a, h, w):
    """Upsample a 2D spec channel back to full (h,w)."""
    a = np.asarray(a, np.float32)
    if a.shape[0] == h and a.shape[1] == w:
        return a
    if _CV2:
        return _cv2.resize(a, (w, h), interpolation=_cv2.INTER_LINEAR)
    return _resize_array(a, h, w)


def _polish_spec(shape, seed, sm, vein, m_field, gloss_field,
                 r_matrix=70.0, r_vein=185.0, cc_lo=18.0, cc_hi=190.0,
                 m_lo=12.0, m_hi=205.0, grain_r=12.0):
    """vein, m_field, gloss_field: three independent 0..1 fields.
    R rides vein (G), M rides m_field (red), CC rides gloss_field (blue).
    All arithmetic runs on a capped work grid then upsamples (<3s @2048); the input
    fields were already built at work-res upstream so downsampling here is near-free."""
    h, w = shape[:2]
    sh, sw = _pshape(shape)
    vein = np.clip(_ds(vein, sh, sw), 0, 1)
    m_field = np.clip(_ds(m_field, sh, sw), 0, 1)
    gloss_field = np.clip(_ds(gloss_field, sh, sw), 0, 1)
    g = _grain((sh, sw), seed + 3)
    gn = (g - 0.5) * 2.0
    # Roughness (G): honed matrix -> drier veins, + fine crisp grain.
    R = r_matrix + (r_vein - r_matrix) * vein + grain_r * gn
    R = np.clip(128.0 + (R - 128.0) * sm, 15, 255)
    # Clearcoat (B): rides an INDEPENDENT field so blue varies on its own pixels.
    CC = cc_lo + (cc_hi - cc_lo) * gloss_field + (grain_r * 0.4) * gn
    CC = np.clip(128.0 + (CC - 128.0) * sm, 16, 255)
    # Metalness (R-viz): mineral/metal motif, fully independent geometry.
    M = m_lo + (m_hi - m_lo) * m_field
    M = np.clip(128.0 + (M - 128.0) * sm, 0, 255)
    return _pack(_us(M, h, w), _us(R, h, w), _us(CC, h, w))


# =====================================================================
# THE 20 — each finish is its OWN function pair (no factory).
# =====================================================================

# 1. CARRARA — fine grey hairline fracture lattice on warm white -------------
def paint_marble_carrara(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    edge, cid = _fracture_web((h, w), seed, 240)          # fine angular hairlines
    haze = _norm01(_noise((h, w), [120, 260], [0.6, 0.4], seed + 4))  # faint warm clouding
    base = _mix((0.93, 0.93, 0.945), (0.86, 0.865, 0.885), haze)
    vein = np.clip((edge - 0.45) * 2.4, 0, 1)             # crisp thin grey lines
    col = base * (1 - vein[:, :, None] * 0.55) + np.array([0.50, 0.51, 0.55], np.float32)[None, None, :] * vein[:, :, None] * 0.55
    return _finish_paint(np.clip(col, 0, 1), paint, mask, shape, seed, 0.035)

def spec_marble_carrara(shape, seed, sm, base_m, base_r):
    edge, cid = _fracture_web(shape, seed, 240)
    vein = np.clip((edge - 0.45) * 2.4, 0, 1)
    haze = _norm01(_noise(shape, [120, 260], [0.6, 0.4], seed + 4))
    # M cool sheen on cell-id, CC pools on the clouding, R on the hairlines (3 fields).
    return _polish_spec(shape, seed, sm, vein, m_field=cid,
                        gloss_field=haze, r_matrix=58, r_vein=200,
                        cc_lo=20, cc_hi=200, m_lo=10, m_hi=180)


# 2. CALACATTA — bold dramatic GOLD trunk-and-branch veins -------------------
def paint_marble_calacatta(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    veins = _vein_network((h, w), seed, 4, 0.020, 5.0, 7.0)   # bold meandering gold trunks
    hair = _fracture_web((h, w), seed + 50, 180)[0]
    base = _mix((0.95, 0.95, 0.955), (0.90, 0.895, 0.90),
                _norm01(_noise((h, w), [140, 300], [0.6, 0.4], seed + 2)))
    grey = np.clip((hair - 0.55) * 2.0, 0, 1)
    col = base * (1 - grey[:, :, None] * 0.30) + np.array([0.6, 0.6, 0.63], np.float32)[None, None, :] * grey[:, :, None] * 0.30
    gold = np.clip((veins - 0.30) * 1.8, 0, 1)
    col = col * (1 - gold[:, :, None]) + np.array([0.80, 0.61, 0.20], np.float32)[None, None, :] * gold[:, :, None]
    halo = np.clip((veins - 0.12) * 1.4, 0, 1) * (1 - gold)    # warm halo bleed
    col = np.clip(col + halo[:, :, None] * np.array([0.10, 0.07, 0.0], np.float32), 0, 1)
    return _finish_paint(col, paint, mask, shape, seed, 0.03)

def spec_marble_calacatta(shape, seed, sm, base_m, base_r):
    sp = _pshape(shape)                                # build fields at paint's work-res (cache share)
    veins = _vein_network(sp, seed, 4, 0.020, 5.0, 7.0)
    gold = np.clip((veins - 0.30) * 1.8, 0, 1)
    hair = _fracture_web(sp, seed + 50, 180)[0]
    # gold veins are METALLIC (high M) + drier; matrix glossy. CC pools on the marble field.
    cloud = _norm01(_noise(sp, [140, 300], [0.6, 0.4], seed + 2))
    sheen = _norm01(_noise(sp, [70, 150], [0.6, 0.4], seed + 29))   # broad mineral M field
    sheen = np.clip((sheen - 0.42) * 2.0 + 0.45, 0, 1)                 # crank -> M crosses mid widely
    m_field = np.clip(gold * 0.5 + sheen, 0, 1)
    return _polish_spec(shape, seed, sm, np.clip((hair - 0.55) * 2.0, 0, 1) * 0.6 + gold * 0.4,
                        m_field=m_field, gloss_field=cloud,
                        r_matrix=62, r_vein=192, cc_lo=22, cc_hi=205, m_lo=18, m_hi=215)


# 3. NERO MARQUINA — black with sharp white fracture web ---------------------
def paint_marble_nero(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    edge, cid = _fracture_web((h, w), seed, 200)
    base = _mix((0.045, 0.045, 0.055), (0.10, 0.10, 0.115),
                _norm01(_noise((h, w), [80, 180], [0.6, 0.4], seed + 2)))
    white = np.clip((edge - 0.40) * 2.6, 0, 1)            # crisp white seams
    col = base * (1 - white[:, :, None]) + np.array([0.90, 0.91, 0.94], np.float32)[None, None, :] * white[:, :, None]
    return _finish_paint(np.clip(col, 0, 1), paint, mask, shape, seed, 0.04)

def spec_marble_nero(shape, seed, sm, base_m, base_r):
    edge, cid = _fracture_web(shape, seed, 200)
    white = np.clip((edge - 0.40) * 2.6, 0, 1)
    cloud = _norm01(_noise(shape, [80, 180], [0.6, 0.4], seed + 2))   # independent CC field
    # R rides white seams (dry); M rides per-cell mineral sheen; CC pools on its own cloud.
    return _polish_spec(shape, seed, sm, white, m_field=cid,
                        gloss_field=cloud, r_matrix=55, r_vein=205,
                        cc_lo=20, cc_hi=190, m_lo=8, m_hi=190)


# 4. PORTORO — black with broad meandering GOLD rivers -----------------------
def paint_marble_portoro(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    rivers = _flow_bands((h, w), seed, 0.018, 28.0, 9.0, oct2=True)
    ridge = np.clip(1.0 - np.abs(rivers - 0.5) * 3.0, 0, 1)   # gold occupies ridge crests
    fine = _vein_network((h, w), seed + 30, 6, 0.045, 9.0, 5.0, branch=False)
    base = _mix((0.035, 0.035, 0.045), (0.085, 0.080, 0.07),
                _norm01(_noise((h, w), [70, 150], [0.6, 0.4], seed + 2)))
    gold = np.clip(ridge * 0.7 + (fine - 0.4) * 1.5 * 0.6, 0, 1)
    col = base * (1 - gold[:, :, None]) + np.array([0.82, 0.62, 0.20], np.float32)[None, None, :] * gold[:, :, None]
    col = np.clip(col + (gold * 0.4)[:, :, None] * np.array([0.12, 0.08, 0.0], np.float32), 0, 1)
    return _finish_paint(col, paint, mask, shape, seed, 0.035)

def spec_marble_portoro(shape, seed, sm, base_m, base_r):
    sp = _pshape(shape)
    rivers = _flow_bands(sp, seed, 0.018, 28.0, 9.0, oct2=True)
    ridge = np.clip(1.0 - np.abs(rivers - 0.5) * 3.0, 0, 1)
    fine = _vein_network(sp, seed + 30, 6, 0.045, 9.0, 5.0, branch=False)
    gold = np.clip(ridge * 0.7 + (fine - 0.4) * 1.5 * 0.6, 0, 1)
    cloud = _norm01(_noise(sp, [70, 150], [0.6, 0.4], seed + 2))   # CC on its own field
    sheen = _norm01(_noise(sp, [60, 130], [0.6, 0.4], seed + 35))  # broad mineral M field
    m_field = np.clip(gold + sheen * 0.5, 0, 1)
    # M ignites on gold rivers (metallic) over a broad mineral floor; R on finer veinlets; CC on cloud.
    return _polish_spec(shape, seed, sm, np.clip((fine - 0.4) * 1.5, 0, 1), m_field=m_field,
                        gloss_field=cloud, r_matrix=50, r_vein=195,
                        cc_lo=18, cc_hi=185, m_lo=12, m_hi=235)


# 5. ONYX EMERALD — translucent layered onyx banding (back-lit depth) --------
def paint_onyx_emerald(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    band = _flow_bands((h, w), seed, 0.030, 40.0, 6.0, oct2=True)
    depth = _norm01(_noise((h, w), [180, 380], [0.6, 0.4], seed + 5))    # broad translucency
    dark = np.array([0.015, 0.16, 0.085], np.float32)
    glow = np.array([0.10, 0.62, 0.34], np.float32)
    col = _mix(dark, glow, band * (0.55 + 0.45 * depth))
    seam = np.clip(1.0 - np.abs(band - 0.5) * 6.0, 0, 1)                 # bright translucent seams
    col = np.clip(col + seam[:, :, None] * np.array([0.18, 0.45, 0.28], np.float32) * 0.5, 0, 1)
    return _finish_paint(col, paint, mask, shape, seed, 0.03)

def spec_onyx_emerald(shape, seed, sm, base_m, base_r):
    band = _flow_bands(shape, seed, 0.030, 40.0, 6.0, oct2=True)
    depth = _norm01(_noise(shape, [180, 380], [0.6, 0.4], seed + 5))
    seam = np.clip(1.0 - np.abs(band - 0.5) * 6.0, 0, 1)
    # Translucent onyx = very wet (high CC) everywhere, gloss pools on the deep zones;
    # M rides the bright seams (mineral glint), R rides band layering -> 3 different fields.
    return _polish_spec(shape, seed, sm, np.clip(band, 0, 1), m_field=seam,
                        gloss_field=depth, r_matrix=45, r_vein=175,
                        cc_lo=18, cc_hi=170, m_lo=12, m_hi=185)


# 6. AGATE BLUE — concentric agate bands around scattered nuclei -------------
def paint_agate_blue(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    rings = _agate_bands((h, w), seed, 5, 0.10)
    edge, cid = _fracture_web((h, w), seed + 80, 120)
    dark = np.array([0.03, 0.10, 0.34], np.float32)
    light = np.array([0.30, 0.55, 0.92], np.float32)
    col = _mix(dark, light, rings)
    seam = np.clip(1.0 - np.abs(rings - 0.5) * 5.0, 0, 1)
    col = np.clip(col + seam[:, :, None] * np.array([0.4, 0.55, 0.7], np.float32) * 0.35, 0, 1)
    # crystalline druzy core glints in cell centers
    core = (cid > 0.85).astype(np.float32) * (_grain((h, w), seed + 6) > 0.8)
    col = np.clip(col + core[:, :, None] * np.array([0.5, 0.6, 0.7], np.float32), 0, 1)
    return _finish_paint(col, paint, mask, shape, seed, 0.03)

def spec_agate_blue(shape, seed, sm, base_m, base_r):
    rings = _agate_bands(shape, seed, 5, 0.10)
    edge, cid = _fracture_web(shape, seed + 80, 120)
    seam = np.clip(1.0 - np.abs(rings - 0.5) * 5.0, 0, 1)
    # M rides bright ring seams, CC pools on cell-id zones, R rides ring layering.
    return _polish_spec(shape, seed, sm, np.clip(rings, 0, 1), m_field=seam,
                        gloss_field=cid, r_matrix=48, r_vein=180,
                        cc_lo=20, cc_hi=200, m_lo=10, m_hi=185)


# 7. ROSE MARBLE — soft diffuse CLOUDING (no hard veins) ---------------------
def paint_marble_rose(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    c1 = _norm01(_noise((h, w), [90, 200], [0.6, 0.4], seed))
    c2 = _norm01(_noise((h, w), [50, 120], [0.55, 0.45], seed + 7))
    bloom = np.clip(c1 * 0.6 + c2 * 0.4, 0, 1)
    pale = np.array([0.93, 0.86, 0.85], np.float32)
    rose = np.array([0.80, 0.58, 0.60], np.float32)
    deep = np.array([0.62, 0.40, 0.45], np.float32)
    col = _mix(pale, rose, bloom)
    col = _mix(col, deep[None, None, :] * 0 + deep, np.clip((bloom - 0.7) * 3.0, 0, 1)) if False else col
    col = col * (1 - np.clip((bloom - 0.72) * 2.5, 0, 1)[:, :, None]) + deep[None, None, :] * np.clip((bloom - 0.72) * 2.5, 0, 1)[:, :, None]
    return _finish_paint(np.clip(col, 0, 1), paint, mask, shape, seed, 0.04)

def spec_marble_rose(shape, seed, sm, base_m, base_r):
    # Three independent clouds at DIFFERENT frequencies, each contrast-cranked so it crosses
    # the mid on its own geometry -> the soft no-vein rose still reads multi-hue + decorrelated.
    c1 = np.clip((_norm01(_noise(shape, [90, 200], [0.6, 0.4], seed)) - 0.45) * 1.9 + 0.45, 0, 1)
    c2 = np.clip((_norm01(_noise(shape, [40, 100], [0.55, 0.45], seed + 7)) - 0.45) * 1.9 + 0.45, 0, 1)
    c3 = np.clip((_norm01(_noise(shape, [24, 60], [0.6, 0.4], seed + 43)) - 0.45) * 1.9 + 0.45, 0, 1)
    return _polish_spec(shape, seed, sm, c2, m_field=c3,
                        gloss_field=c1, r_matrix=70, r_vein=190,
                        cc_lo=22, cc_hi=200, m_lo=16, m_hi=205, grain_r=9)


# 8. TRAVERTINE — pitted/porous stone (drilled voids + stratified layers) ----
def paint_travertine(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    strata = _flow_bands((h, w), seed, 0.020, 6.0, 3.0)        # near-horizontal layering
    pits = _norm01(_noise((h, w), [10, 22], [0.55, 0.45], seed + 9))  # fine porosity
    void = (pits > 0.74).astype(np.float32)
    void = _blur(void, 0.7)
    tan = np.array([0.78, 0.69, 0.52], np.float32)
    deep = np.array([0.58, 0.49, 0.34], np.float32)
    col = _mix(deep, tan, strata * 0.7 + 0.15)
    col = col * (1 - void[:, :, None] * 0.55) + np.array([0.34, 0.27, 0.18], np.float32)[None, None, :] * void[:, :, None] * 0.55
    return _finish_paint(np.clip(col, 0, 1), paint, mask, shape, seed, 0.05)

def spec_travertine(shape, seed, sm, base_m, base_r):
    strata = _flow_bands(shape, seed, 0.020, 6.0, 3.0)
    pits = _norm01(_noise(shape, [10, 22], [0.55, 0.45], seed + 9))
    void = (pits > 0.74).astype(np.float32)
    void = _blur(void, 0.7)
    # Pits are matte & uncoated (high R). M rides strata mineral sheen. CC pools on a
    # SEPARATE broad porosity field -> warm/orange/teal combined map, all decorrelated.
    cc_field = _norm01(_noise(shape, [40, 90], [0.6, 0.4], seed + 13))
    return _polish_spec(shape, seed, sm, np.clip(void * 0.7 + 0.15, 0, 1), m_field=strata,
                        gloss_field=cc_field, r_matrix=80, r_vein=215,
                        cc_lo=30, cc_hi=190, m_lo=10, m_hi=150, grain_r=16)


# 9. VERDE ALPI — serpentine breccia: angular fragments + serpentine veinlets-
def paint_marble_verde_alpi(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    edge, cid = _fracture_web((h, w), seed, 280)
    veinlet = _vein_network((h, w), seed + 40, 7, 0.05, 11.0, 4.0)
    dark = np.array([0.02, 0.16, 0.09], np.float32)
    mid = np.array([0.06, 0.34, 0.18], np.float32)
    col = _mix(dark, mid, cid)                                   # fragments of varied green
    white = np.clip((edge - 0.40) * 2.4, 0, 1)
    col = col * (1 - white[:, :, None]) + np.array([0.85, 0.92, 0.86], np.float32)[None, None, :] * white[:, :, None]
    serp = np.clip((veinlet - 0.4) * 1.8, 0, 1)                  # fine pale serpentine veinlets
    col = col * (1 - serp[:, :, None] * 0.6) + np.array([0.55, 0.78, 0.6], np.float32)[None, None, :] * serp[:, :, None] * 0.6
    return _finish_paint(np.clip(col, 0, 1), paint, mask, shape, seed, 0.035)

def spec_marble_verde_alpi(shape, seed, sm, base_m, base_r):
    sp = _pshape(shape)
    edge, cid = _fracture_web(sp, seed, 280)
    veinlet = _vein_network(sp, seed + 40, 7, 0.05, 11.0, 4.0)
    white = np.clip((edge - 0.40) * 2.4, 0, 1)
    serp = np.clip((veinlet - 0.4) * 1.8, 0, 1)
    vein = np.clip(white * 0.7 + serp * 0.5, 0, 1)
    cc_field = _norm01(_noise(sp, [50, 110], [0.6, 0.4], seed + 17))   # independent of cid
    # R rides white+serp veins; M rides fragment cell-id; CC pools on its own cloud.
    return _polish_spec(shape, seed, sm, vein, m_field=cid,
                        gloss_field=cc_field, r_matrix=52, r_vein=195,
                        cc_lo=20, cc_hi=185, m_lo=10, m_hi=185)


# 10. ROSSO LEVANTO — red breccia plates caged by white calcite seams --------
def paint_marble_rosso(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    edge, cid = _fracture_web((h, w), seed, 220)
    deepred = np.array([0.30, 0.05, 0.06], np.float32)
    red = np.array([0.55, 0.11, 0.10], np.float32)
    col = _mix(deepred, red, cid)
    white = np.clip((edge - 0.42) * 2.6, 0, 1)                  # caging calcite net
    col = col * (1 - white[:, :, None]) + np.array([0.93, 0.92, 0.90], np.float32)[None, None, :] * white[:, :, None]
    # green serpentine flecks in some plates (real Rosso Levanto)
    grn = (cid > 0.7).astype(np.float32) * np.clip((_norm01(_noise((h, w), [30, 60], [0.6, 0.4], seed + 12)) - 0.55) * 3.0, 0, 1)
    col = np.clip(col * (1 - grn[:, :, None] * 0.6) + np.array([0.10, 0.35, 0.18], np.float32)[None, None, :] * grn[:, :, None] * 0.6, 0, 1)
    return _finish_paint(col, paint, mask, shape, seed, 0.035)

def spec_marble_rosso(shape, seed, sm, base_m, base_r):
    edge, cid = _fracture_web(shape, seed, 220)
    white = np.clip((edge - 0.42) * 2.6, 0, 1)
    grn = (cid > 0.7).astype(np.float32)
    cc_field = _norm01(_noise(shape, [45, 100], [0.6, 0.4], seed + 19))
    # White seams chalky-dry (R); M ignites on green serpentine plates; CC on own cloud.
    return _polish_spec(shape, seed, sm, white, m_field=grn,
                        gloss_field=cc_field, r_matrix=55, r_vein=200,
                        cc_lo=20, cc_hi=185, m_lo=8, m_hi=200)


# 11. HONEY ONYX — warm translucent ribbon banding --------------------------
def paint_onyx_honey(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    ribbon = _flow_bands((h, w), seed, 0.024, 18.0, 7.0, oct2=True)
    depth = _norm01(_noise((h, w), [200, 420], [0.6, 0.4], seed + 5))
    amber = np.array([0.62, 0.40, 0.12], np.float32)
    honey = np.array([0.93, 0.72, 0.32], np.float32)
    pale = np.array([1.0, 0.90, 0.62], np.float32)
    col = _mix(amber, honey, ribbon)
    seam = np.clip(1.0 - np.abs(ribbon - 0.5) * 5.0, 0, 1)
    col = _mix(col, pale, seam * (0.4 + 0.6 * depth) * 0.7)       # translucent bright ribbons
    return _finish_paint(np.clip(col, 0, 1), paint, mask, shape, seed, 0.028)

def spec_onyx_honey(shape, seed, sm, base_m, base_r):
    ribbon = _flow_bands(shape, seed, 0.024, 18.0, 7.0, oct2=True)
    depth = _norm01(_noise(shape, [200, 420], [0.6, 0.4], seed + 5))
    seam = np.clip(1.0 - np.abs(ribbon - 0.5) * 5.0, 0, 1)
    return _polish_spec(shape, seed, sm, ribbon, m_field=seam,
                        gloss_field=depth, r_matrix=48, r_vein=178,
                        cc_lo=20, cc_hi=180, m_lo=14, m_hi=175)


# 12. STATUARIO — sparse dramatic veins on bright white ----------------------
def paint_marble_statuario(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    veins = _vein_network((h, w), seed, 3, 0.016, 8.0, 8.0)      # few, bold, dark-grey veins
    base = _mix((0.965, 0.965, 0.97), (0.92, 0.925, 0.935),
                _norm01(_noise((h, w), [160, 340], [0.6, 0.4], seed + 2)))
    grey = np.clip((veins - 0.32) * 2.0, 0, 1)
    col = base * (1 - grey[:, :, None]) + np.array([0.42, 0.44, 0.50], np.float32)[None, None, :] * grey[:, :, None]
    halo = np.clip((veins - 0.14) * 1.2, 0, 1) * (1 - grey)
    col = np.clip(col - halo[:, :, None] * 0.05, 0, 1)
    return _finish_paint(col, paint, mask, shape, seed, 0.025)

def spec_marble_statuario(shape, seed, sm, base_m, base_r):
    sp = _pshape(shape)
    veins = _vein_network(sp, seed, 3, 0.016, 8.0, 8.0)
    grey = np.clip((veins - 0.32) * 2.0, 0, 1)
    cloud = _norm01(_noise(sp, [160, 340], [0.6, 0.4], seed + 2))
    sheen = _norm01(_noise(sp, [60, 130], [0.6, 0.4], seed + 21))   # independent M field
    sheen = np.clip((sheen - 0.42) * 2.2 + 0.42, 0, 1)                 # crank contrast -> crosses mid
    # High-polish white marble: R rides the drama veins; M cool sheen domains; CC pools on cloud.
    return _polish_spec(shape, seed, sm, grey, m_field=sheen,
                        gloss_field=cloud, r_matrix=70, r_vein=185,
                        cc_lo=22, cc_hi=200, m_lo=12, m_hi=205, grain_r=8)


# 13. PINK ONYX — swirl banding (rotational flow) ---------------------------
def paint_onyx_pink(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    sw = _swirl((h, w), seed, 22.0, 8.0)
    depth = _norm01(_noise((h, w), [180, 360], [0.6, 0.4], seed + 5))
    rose = np.array([0.60, 0.28, 0.40], np.float32)
    pink = np.array([0.92, 0.58, 0.68], np.float32)
    pale = np.array([1.0, 0.86, 0.90], np.float32)
    col = _mix(rose, pink, sw)
    seam = np.clip(1.0 - np.abs(sw - 0.5) * 5.0, 0, 1)
    col = _mix(col, pale, seam * (0.4 + 0.6 * depth) * 0.7)
    return _finish_paint(np.clip(col, 0, 1), paint, mask, shape, seed, 0.028)

def spec_onyx_pink(shape, seed, sm, base_m, base_r):
    sw = _swirl(shape, seed, 22.0, 8.0)
    depth = _norm01(_noise(shape, [180, 360], [0.6, 0.4], seed + 5))
    seam = np.clip(1.0 - np.abs(sw - 0.5) * 5.0, 0, 1)
    return _polish_spec(shape, seed, sm, sw, m_field=seam,
                        gloss_field=depth, r_matrix=48, r_vein=178,
                        cc_lo=20, cc_hi=178, m_lo=12, m_hi=165)


# 14. LAPIS LAZULI — ultramarine + PYRITE gold flecks + calcite veinlets -----
def paint_lapis_lazuli(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    mottle = _norm01(_noise((h, w), [40, 90], [0.6, 0.4], seed))
    deep = np.array([0.04, 0.09, 0.42], np.float32)
    blue = np.array([0.12, 0.22, 0.72], np.float32)
    col = _mix(deep, blue, mottle)
    # calcite veinlets (white wandering)
    vein = np.clip((_vein_network((h, w), seed + 33, 8, 0.06, 9.0, 4.0) - 0.45) * 1.8, 0, 1)
    col = col * (1 - vein[:, :, None] * 0.7) + np.array([0.80, 0.82, 0.85], np.float32)[None, None, :] * vein[:, :, None] * 0.7
    # pyrite gold flecks
    py = _flecks((h, w), seed + 4, 0.004, 0.6, 1.0)
    col = np.clip(col + _blur(py, 0.5)[:, :, None] * np.array([0.95, 0.78, 0.20], np.float32), 0, 1)
    return _finish_paint(col, paint, mask, shape, seed, 0.03)

def spec_lapis_lazuli(shape, seed, sm, base_m, base_r):
    sp = _pshape(shape)
    py = _flecks(sp, seed + 4, 0.004, 0.6, 1.0)
    py = _blur(py, 0.5)
    vein = np.clip((_vein_network(sp, seed + 33, 8, 0.06, 9.0, 4.0) - 0.45) * 1.8, 0, 1)
    # M IGNITES on pyrite flecks (true metal) + a broad mineral floor so red appears widely;
    # calcite veins chalky-dry (R); CC pools on its OWN cloud. Three decorrelated fields.
    sheen = _norm01(_noise(sp, [55, 120], [0.6, 0.4], seed + 47))
    sheen = np.clip((sheen - 0.42) * 2.0 + 0.45, 0, 1)               # crank -> broad M crosses mid
    cc_field = np.clip((_norm01(_noise(sp, [70, 150], [0.6, 0.4], seed + 53)) - 0.45) * 1.8 + 0.45, 0, 1)
    m_field = np.clip(py * 1.4 + sheen, 0, 1)
    return _polish_spec(shape, seed, sm, np.clip(vein * 0.7 + 0.15, 0, 1),
                        m_field=m_field, gloss_field=cc_field,
                        r_matrix=72, r_vein=205, cc_lo=22, cc_hi=200, m_lo=18, m_hi=240)


# 15. AMETHYST — crystal druzy (faceted geode points) ------------------------
def paint_amethyst(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    edge, cid = _fracture_web((h, w), seed, 520)             # tight crystal facets
    facet = cid                                              # per-crystal brightness
    deep = np.array([0.16, 0.05, 0.34], np.float32)
    violet = np.array([0.46, 0.22, 0.70], np.float32)
    lilac = np.array([0.74, 0.56, 0.92], np.float32)
    col = _mix(deep, violet, facet)
    # bright facet tips where two crystals meet (edges) + sparkle
    tip = np.clip((edge - 0.5) * 2.0, 0, 1)
    col = _mix(col, lilac, tip * 0.75)
    spk = (_grain((h, w), seed + 8) > 0.86).astype(np.float32) * tip
    col = np.clip(col + spk[:, :, None] * np.array([0.5, 0.4, 0.6], np.float32), 0, 1)
    return _finish_paint(col, paint, mask, shape, seed, 0.03)

def spec_amethyst(shape, seed, sm, base_m, base_r):
    edge, cid = _fracture_web(shape, seed, 520)
    tip = np.clip((edge - 0.5) * 2.0, 0, 1)
    cc_field = _norm01(_noise(shape, [40, 90], [0.6, 0.4], seed + 27))   # independent of facets
    # Faceted crystal: M rides per-crystal cid + glinting tips; R rides tip dryness; CC own cloud.
    return _polish_spec(shape, seed, sm, np.clip(tip * 0.8 + 0.1, 0, 1),
                        m_field=np.clip(cid * 0.7 + tip * 0.4, 0, 1),
                        gloss_field=cc_field, r_matrix=44, r_vein=175,
                        cc_lo=20, cc_hi=185, m_lo=12, m_hi=195)


# 16. TIGER IRON — layered hematite / jasper / gold tiger-eye silk -----------
def paint_tiger_iron(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    u, v = _rot((h, w), 18.0)
    warp = _noise((h, w), [40, 90], [0.6, 0.4], seed) * 5.0
    layer = 0.5 + 0.5 * np.sin(v * 0.045 + warp)                # broad layered banding
    # three rock types by band phase
    jasper = np.array([0.55, 0.10, 0.07], np.float32)           # red jasper
    hem = np.array([0.18, 0.19, 0.22], np.float32)              # steely hematite
    gold = np.array([0.78, 0.55, 0.14], np.float32)             # tiger-eye gold
    sel = (layer * 3.0).astype(np.int32) % 3
    col = np.where(sel[:, :, None] == 0, jasper[None, None, :],
                   np.where(sel[:, :, None] == 1, hem[None, None, :], gold[None, None, :])).astype(np.float32)
    # tiger-eye SILK in the gold bands (fine chatoyant fibres)
    silk = np.clip((0.5 + 0.5 * np.sin(u * 1.4 + warp)) ** 1.5 * 1.4, 0, 1)
    goldband = (sel == 2).astype(np.float32)
    col = np.clip(col + (goldband * silk)[:, :, None] * np.array([0.22, 0.16, 0.04], np.float32), 0, 1)
    col = _mix(col * 0 + col, col, layer) if False else col
    return _finish_paint(col, paint, mask, shape, seed, 0.04)

def spec_tiger_iron(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    u, v = _rot((h, w), 18.0)
    warp = _noise((h, w), [40, 90], [0.6, 0.4], seed) * 5.0
    layer = 0.5 + 0.5 * np.sin(v * 0.045 + warp)
    sel = (layer * 3.0).astype(np.int32) % 3
    silk = np.clip((0.5 + 0.5 * np.sin(u * 1.4 + warp)) ** 1.5 * 1.4, 0, 1)
    hemband = (sel == 1).astype(np.float32)                     # hematite = high M (metallic iron)
    goldband = (sel == 2).astype(np.float32)
    # M: hematite metallic + silk on gold. R: jasper bands drier. CC on its OWN cloud.
    m_field = np.clip(hemband * 0.9 + goldband * silk * 0.7, 0, 1)
    vein = (sel == 0).astype(np.float32)                       # jasper drier (R)
    cc_field = _norm01(_noise(shape, [45, 100], [0.6, 0.4], seed + 31))
    return _polish_spec(shape, seed, sm, vein, m_field=m_field,
                        gloss_field=cc_field, r_matrix=55, r_vein=205,
                        cc_lo=20, cc_hi=190, m_lo=10, m_hi=235)


# 17. BARDIGLIO — soft directional cloud striations (grey) -------------------
def paint_marble_bardiglio(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    striate = _flow_bands((h, w), seed, 0.014, 35.0, 10.0, oct2=True)
    cloud = _norm01(_noise((h, w), [70, 160], [0.6, 0.4], seed + 4))
    dark = np.array([0.30, 0.31, 0.35], np.float32)
    light = np.array([0.55, 0.56, 0.60], np.float32)
    col = _mix(dark, light, np.clip(striate * 0.6 + cloud * 0.4, 0, 1))
    wisp = np.clip((_vein_network((h, w), seed + 20, 5, 0.05, 12.0, 5.0) - 0.5) * 1.6, 0, 1)
    col = col * (1 - wisp[:, :, None] * 0.4) + np.array([0.78, 0.79, 0.83], np.float32)[None, None, :] * wisp[:, :, None] * 0.4
    return _finish_paint(np.clip(col, 0, 1), paint, mask, shape, seed, 0.035)

def spec_marble_bardiglio(shape, seed, sm, base_m, base_r):
    sp = _pshape(shape)
    striate = _flow_bands(sp, seed, 0.014, 35.0, 10.0, oct2=True)
    cloud = _norm01(_noise(sp, [70, 160], [0.6, 0.4], seed + 4))
    wisp = np.clip((_vein_network(sp, seed + 20, 5, 0.05, 12.0, 5.0) - 0.5) * 1.6, 0, 1)
    striate = np.clip((striate - 0.45) * 1.8 + 0.45, 0, 1)            # sharpen -> crosses mid
    cloud = np.clip((cloud - 0.45) * 1.7 + 0.45, 0, 1)
    # R rides wisps; M rides directional striation sheen; CC pools on cloud (3 fields).
    return _polish_spec(shape, seed, sm, np.clip(wisp * 0.7 + 0.15, 0, 1), m_field=striate,
                        gloss_field=cloud, r_matrix=72, r_vein=185,
                        cc_lo=22, cc_hi=200, m_lo=14, m_hi=205)


# 18. WHITE ONYX — fine translucent feathered banding -----------------------
def paint_onyx_white(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    feather = _flow_bands((h, w), seed, 0.05, 50.0, 5.0, oct2=True)   # finer banding
    depth = _norm01(_noise((h, w), [220, 460], [0.6, 0.4], seed + 5))
    cool = np.array([0.80, 0.84, 0.88], np.float32)
    warm = np.array([0.95, 0.93, 0.88], np.float32)
    col = _mix(cool, warm, feather)
    seam = np.clip(1.0 - np.abs(feather - 0.5) * 6.0, 0, 1)
    col = _mix(col, np.array([1.0, 0.99, 0.97], np.float32), seam * (0.3 + 0.7 * depth) * 0.6)
    return _finish_paint(np.clip(col, 0, 1), paint, mask, shape, seed, 0.025)

def spec_onyx_white(shape, seed, sm, base_m, base_r):
    sp = _pshape(shape)
    feather = _flow_bands(sp, seed, 0.05, 50.0, 5.0, oct2=True)
    depth = _norm01(_noise(sp, [220, 460], [0.6, 0.4], seed + 5))
    seam = np.clip(1.0 - np.abs(feather - 0.5) * 6.0, 0, 1)
    return _polish_spec(shape, seed, sm, feather, m_field=seam,
                        gloss_field=depth, r_matrix=46, r_vein=172,
                        cc_lo=20, cc_hi=172, m_lo=12, m_hi=160, grain_r=7)


# 19. MARBLE FUSION — multi-stone breccia (cells of different stones + gold) --
def paint_marble_fusion(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    edge, cid = _fracture_web((h, w), seed, 90)               # large fragments = different stones
    # quantize cells to stone "types" with distinct palettes
    sel = (cid * 4.0).astype(np.int32) % 4
    sapphire = np.array([0.10, 0.16, 0.55], np.float32)
    emerald = np.array([0.06, 0.40, 0.24], np.float32)
    magenta = np.array([0.55, 0.12, 0.40], np.float32)
    onyxk = np.array([0.06, 0.06, 0.09], np.float32)
    inner = _norm01(_noise((h, w), [40, 90], [0.6, 0.4], seed + 13))   # internal stone texture
    cols = [sapphire, emerald, magenta, onyxk]
    col = np.zeros((h, w, 3), np.float32)
    for i, c in enumerate(cols):
        m_i = (sel == i).astype(np.float32)[:, :, None]
        shade = (0.7 + 0.5 * inner)[:, :, None]
        col += m_i * np.clip(c[None, None, :] * shade, 0, 1)
    gold = np.clip((edge - 0.42) * 2.6, 0, 1)                 # gold seams cage everything
    col = col * (1 - gold[:, :, None]) + np.array([0.85, 0.66, 0.20], np.float32)[None, None, :] * gold[:, :, None]
    return _finish_paint(np.clip(col, 0, 1), paint, mask, shape, seed, 0.035)

def spec_marble_fusion(shape, seed, sm, base_m, base_r):
    edge, cid = _fracture_web(shape, seed, 90)
    sel = (cid * 4.0).astype(np.int32) % 4
    gold = np.clip((edge - 0.42) * 2.6, 0, 1)
    inner = _norm01(_noise(shape, [40, 90], [0.6, 0.4], seed + 13))
    # Gold seams metallic; per-stone-type M (some fragments metallic, some matte); CC own cloud.
    m_field = np.clip(gold + (sel == 1).astype(np.float32) * 0.5 + (sel == 0).astype(np.float32) * 0.25, 0, 1)
    cc_field = _norm01(_noise(shape, [55, 120], [0.6, 0.4], seed + 37))
    return _polish_spec(shape, seed, sm, np.clip(gold * 0.6 + inner * 0.4, 0, 1),
                        m_field=m_field, gloss_field=cc_field,
                        r_matrix=50, r_vein=195, cc_lo=20, cc_hi=190, m_lo=8, m_hi=235)


# 20. OBSIDIAN GOLD — black glass + gold sheen flow + conchoidal fracture ----
def paint_obsidian_gold(paint, shape, mask, seed, pm, bb):
    h, w = _pshape(shape)
    # conchoidal (shell-shaped) fracture = concentric ridges around few impact points
    conch = _agate_bands((h, w), seed, 3, 0.06)
    ridge = np.clip(1.0 - np.abs(conch - 0.5) * 4.0, 0, 1)
    flow = _norm01(_noise((h, w), [60, 130], [0.6, 0.4], seed + 7))
    base = _mix((0.025, 0.025, 0.035), (0.07, 0.065, 0.06), flow)
    # gold sheen rides the flow + conchoidal ridges (thin-film warm)
    sheen = np.clip(flow * 0.5 + ridge * 0.7, 0, 1)
    film = np.asarray(interference_palette(sheen * 0.5 + 0.35, orders=1.4, quantize=0.5, brightness=0.9), np.float32)
    glint = np.clip((sheen - 0.6) * 2.0, 0, 1)
    col = base * (1 - glint[:, :, None] * 0.8) + film * glint[:, :, None] * 0.8
    col = np.clip(col + ridge[:, :, None] * np.array([0.10, 0.07, 0.0], np.float32) * 0.4, 0, 1)
    return _finish_paint(col, paint, mask, shape, seed, 0.03)

def spec_obsidian_gold(shape, seed, sm, base_m, base_r):
    conch = _agate_bands(shape, seed, 3, 0.06)
    ridge = np.clip(1.0 - np.abs(conch - 0.5) * 4.0, 0, 1)
    flow = _norm01(_noise(shape, [60, 130], [0.6, 0.4], seed + 7))
    sheen = np.clip(flow * 0.5 + ridge * 0.7, 0, 1)
    glint = np.clip((sheen - 0.6) * 2.0, 0, 1)
    # Obsidian = glass: glassy matrix; gold sheen ridges are METALLIC. M rides glint (ridge-tied),
    # so R must ride a DIFFERENT field (flow grain) and CC its OWN cloud -> decorrelated multi-hue.
    cc_field = _norm01(_noise(shape, [50, 110], [0.6, 0.4], seed + 41))
    r_field = _norm01(_noise(shape, [22, 48], [0.6, 0.4], seed + 59))   # fine glass grain, independent
    return _polish_spec(shape, seed, sm, r_field, m_field=glint,
                        gloss_field=cc_field, r_matrix=40, r_vein=185,
                        cc_lo=20, cc_hi=185, m_lo=10, m_hi=225)
