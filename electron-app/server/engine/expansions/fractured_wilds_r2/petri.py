# -*- coding: utf-8 -*-
"""PETRI chapter (wx_ 91-110): one microbe or organism per finish, microscope / lab-plate looks.

[S20 2026-10-12 owner: Fractured Wilds rebuild] one function per finish; each draws its OWN organism
(stamp masters / strokes / fields) and its OWN spec story (monotone curves of the final paint luma, varied per finish).
Painter kit comes from bloom.py (_blob, _strokes, _tri, ...); only plumbing comes from helpers.
"""
from __future__ import annotations

import numpy as np
import cv2

from . import helpers as H
from .morpho import _z, _curves, _out, _rot_tiles, _aniso
from .bloom import _mk, _put, _putp, _blob, _strokes, _scatter, _trim, _tint, _comp, _fine, _tri

F32 = np.float32
N = H.N
_hx = H.hexrgb

FINISHES = []


def _f(fid, name, desc):
    def deco(fn):
        FINISHES.append((fid, name, desc, fn))
        return fn
    return deco


def _dotmask(S, xs, ys, rs):
    m = np.zeros((S, S), np.uint8)
    for x, y, r_ in zip(xs, ys, rs):
        cv2.circle(m, (int(round(x * 16)), int(round(y * 16))), int(round(r_ * 16)), 255, -1, cv2.LINE_AA, 4)
    return m.astype(F32) / 255.0


def _runs(P, front):
    out, cur = [], []
    for p, f in zip(P, front):
        if f:
            cur.append(p)
        else:
            if len(cur) > 1:
                out.append(np.array(cur))
            cur = []
    if len(cur) > 1:
        out.append(np.array(cur))
    return out


def _gray_tint(r, K, lo, hi):
    return np.repeat(r.uniform(lo, hi, (K, 1)).astype(F32), 3, 1)


# =========================================================================
# 91 diatoms
# =========================================================================
def _diatom_round(S=300):
    M = _mk(S)
    c = S / 2.0
    R = 0.46 * S
    gx, gy = H.tile_xy(S)
    rr = np.hypot(gx, gy)
    disc = H.sstep(R + 1.2, R - 1.2, rr)
    _put(M, _hx('#7ac8dc'), disc * 0.30)
    xs, ys, rs = [], [], []
    for k, rad in enumerate(np.arange(0.12 * S, 0.43 * S, 0.05 * S)):
        cnt = max(6, int(2 * np.pi * rad / 12.0))
        ph = (k % 2) * 0.5 * 2 * np.pi / cnt
        for j in range(cnt):
            a = 2 * np.pi * j / cnt + ph
            xs.append(c + rad * np.cos(a))
            ys.append(c + rad * np.sin(a))
            rs.append(3.6)
    _put(M, _hx('#0a3a48'), _dotmask(S, xs, ys, rs) * 0.85 * disc)
    _put(M, _hx('#e8fcff'), np.exp(-((rr - R) / 2.6) ** 2) * 0.95)
    _put(M, _hx('#bfeaf4'), np.exp(-((rr - 0.09 * S) / 2.2) ** 2) * 0.6)
    _put(M, _hx('#ffffff'), np.clip(-(gx * 0.6 + gy * 0.8) / R, 0, 1) ** 3 * disc * 0.25)
    return M


def _diatom_boat(S=360):
    M = _mk(S)
    gx, gy = H.tile_xy(S)
    L = 0.46 * S
    W = L / 3.0
    u = gx / L
    wprof = np.clip(1 - u * u, 0, 1) ** 0.55
    e = wprof * W - np.abs(gy)
    disc = np.clip(e / 1.3 + 0.5, 0, 1)
    _put(M, _hx('#7ac8dc'), disc * 0.30)
    xs, ys, rs = [], [], []
    for xk in np.arange(-0.86 * L, 0.86 * L, 14.0):
        wk = (1 - (xk / L) ** 2) ** 0.55 * W
        for yk in np.arange(0.14 * W, wk - 5, 12.5):
            for sg in (-1, 1):
                xs.append(S / 2 + xk)
                ys.append(S / 2 + sg * yk)
                rs.append(3.4)
    _put(M, _hx('#0a3a48'), _dotmask(S, xs, ys, rs) * 0.85 * disc)
    _put(M, _hx('#e8fcff'), np.exp(-((e - 1.0) / 2.6) ** 2) * 0.95 * (e > -3))
    _put(M, _hx('#d8f8ff'), np.exp(-(gy / 1.6) ** 2) * disc * 0.9)
    _blob(M, S / 2, S / 2, 7, 6, 0.0, _hx('#7ac8dc'), _hx('#e8fcff'), None, 0.0, 1.0)
    return M


def _diatom_tri(S=320):
    M = _mk(S)
    gx, gy = H.tile_xy(S)
    ds = [0.22 * S - (gx * np.cos(t) + gy * np.sin(t)) for t in (np.pi / 2, np.pi / 2 + 2.0944, np.pi / 2 + 4.1888)]
    e = -np.log(sum(np.exp(-0.18 * d) for d in ds)) / 0.18
    disc = np.clip(e / 1.3 + 0.5, 0, 1)
    _put(M, _hx('#7ac8dc'), disc * 0.30)
    xs, ys, rs = [], [], []
    for j, yy in enumerate(np.arange(-0.34 * S, 0.30 * S, 11.0)):
        for xx in np.arange(-0.40 * S, 0.40 * S, 12.5):
            xs.append(S / 2 + xx + (j % 2) * 6.25)
            ys.append(S / 2 + yy)
            rs.append(3.3)
    xs, ys = np.array(xs), np.array(ys)
    inside = np.array([e[int(np.clip(y, 0, S - 1)), int(np.clip(x, 0, S - 1))] > 9 for x, y in zip(xs, ys)])
    _put(M, _hx('#0a3a48'), _dotmask(S, xs[inside], ys[inside], np.array(rs)[inside]) * 0.85 * disc)
    _put(M, _hx('#e8fcff'), np.exp(-((e - 1.5) / 2.6) ** 2) * 0.95 * (e > -3))
    _put(M, _hx('#ffffff'), np.clip(-(gx * 0.6 + gy * 0.8) / (0.4 * S), 0, 1) ** 3 * disc * 0.2)
    return M


@_f("wx_diatom_frustules", "Diatom Frustules",
    "Glassy diatom shells in round, boat and triangular forms, each etched with rows of tiny pores, on a dark blue field.")
def diatom_frustules(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 91 Diatom Frustules: three translucent glass masters (centric disc with 50 px ring rows of pores, navicula boat with transverse striae + raphe + nodule, triangular frustule with hex pore lattice and soft-min rounded corners), ~230 overlapping stamps, 6/24/24 tiles; CHR glass
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(5, 11, 24)))
    ground = H.ramp(np.clip(0.30 + 0.14 * z + 0.05 * _z(H.noise(n, 150, seed + 2)), 0, 1), [(0.0, '#0a1a22'), (0.5, '#12303c'), (1.0, '#22505e')]).astype(F32)
    ground = ground + (H.flake_mask(n, 0.0025, seed + 3)[..., None] * _hx('#5aa0b0') * 0.5).astype(F32)
    tiles = (_trim(_rot_tiles(_diatom_round(), (200, 260, 320), (0, 20)))
             + _trim(_rot_tiles(_diatom_boat(), (240, 320), tuple(range(0, 360, 30))))
             + _trim(_rot_tiles(_diatom_tri(), (200, 260), tuple(range(0, 360, 30)))))
    ex, ey, _ = _scatter(n, 12, seed + 4, 1, 1, jit=0.5)
    K = len(ex)
    kind = r.choice(3, K, p=[0.34, 0.36, 0.30])
    ti = np.where(kind == 0, r.integers(0, 6, K), np.where(kind == 1, 6 + r.integers(0, 24, K), 30 + r.integers(0, 24, K)))
    img = _comp(n, ground, tiles, ex, ey, ti, tint=_gray_tint(r, K, 0.85, 1.10))
    img = _fine(img, seed + 45, 0.10)
    Ln = H.sstep(0.05, 0.85, H.lum(img))
    M, R, CC = _curves(Ln, (40.0, 250.0), (110.0, 8.0), (10.0, 16.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 92 radiolaria
# =========================================================================
def _radio_master(S=360, tilt=0.55):
    M = _mk(S)
    c = S / 2.0
    R = 0.28 * S
    ca, sa = np.cos(tilt), np.sin(tilt)

    def proj(x, y, z, k=1.0):
        y2 = y * ca - z * sa
        z2 = y * sa + z * ca
        return c + R * k * x, c + R * k * y2, z2

    t = np.linspace(0, 2 * np.pi, 96)
    lams = np.linspace(0, np.pi, 8, endpoint=False)
    curves = []
    for l in lams:
        curves.append(proj(np.cos(t) * np.cos(l), np.sin(t), np.cos(t) * np.sin(l)))
    for ph in np.radians(np.linspace(-62, 62, 7)):
        curves.append(proj(np.cos(ph) * np.cos(t), np.full_like(t, np.sin(ph)), np.cos(ph) * np.sin(t)))
    nodes = []
    for l in np.concatenate([lams, lams + np.pi]):
        for ph in np.radians(np.linspace(-62, 62, 7)):
            nodes.append((np.cos(ph) * np.cos(l), np.sin(ph), np.cos(ph) * np.sin(l), ph))
    nodes = [nd for nd in nodes if abs(nd[3]) < np.radians(70)]
    # back: dim lattice + dim spines
    _strokes(M, [np.stack([cx, cy], 1) for cx, cy, cz in curves], 1, _hx('#4a5a80'))
    for i, (x, y, z, ph) in enumerate(nodes):
        if i % 2 == 0:
            bx, by, bz = proj(x, y, z)
            tx, ty, tz = proj(x, y, z, 1.62)
            if bz < 0:
                _tri(M, (bx - 3.0, by), (bx + 3.0, by + 1.0), (tx, ty), _hx('#5a6a90'))
    _put(M, _hx('#c0d8ff'), H.sstep(R + 1.5, R - 1.5, np.hypot(*H.tile_xy(S))) * 0.10)
    # inner nucleus lattice
    inner = [proj(np.cos(t) * np.cos(l), np.sin(t), np.cos(t) * np.sin(l), 0.45) for l in lams[::2]]
    _strokes(M, [np.stack([cx, cy], 1) for cx, cy, cz in inner], 1, _hx('#8aa0d0'))
    # front lattice
    for cx, cy, cz in curves:
        runs = _runs(np.stack([cx, cy], 1), cz > 0)
        if runs:
            _strokes(M, runs, 2, _hx('#e8f0ff'))
    for i, (x, y, z, ph) in enumerate(nodes):
        bx, by, bz = proj(x, y, z)
        if bz >= 0:
            if i % 2 == 0:
                tx, ty, tz = proj(x, y, z, 1.62)
                ux, uy = tx - bx, ty - by
                ln = np.hypot(ux, uy) + 1e-6
                nx, ny = -uy / ln, ux / ln
                _tri(M, (bx - nx * 3.4, by - ny * 3.4), (bx + nx * 3.4, by + ny * 3.4), (tx, ty), _hx('#f2f6ff'))
            _blob(M, bx, by, 3.4, 3.4, 0.0, _hx('#7a8ab0'), _hx('#f4f8ff'), _hx('#ffffff'), 0.5, 1.0)
    return M


@_f("wx_radiolarian_lattice", "Radiolarian Lattice",
    "Scattered radiolarian skeletons: glassy white geodesic lattice spheres bristling with long spines on a dark navy field.")
def radiolarian_lattice(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 92 Radiolarian Lattice: orthographic lat-long lattice sphere (8 meridians x 7 parallels, dim back pass, bright front runs, ~60 nodes each with spine cone, inner nucleus lattice), 3 sizes x 4 rotations jittered grid + small fillers; CHR silica
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(5, 11, 24)))
    ground = H.ramp(np.clip(0.30 + 0.14 * z + 0.05 * _z(H.noise(n, 150, seed + 2)), 0, 1), [(0.0, '#0c1222'), (0.5, '#16203a'), (1.0, '#26345a')]).astype(F32)
    ground = ground + (H.flake_mask(n, 0.003, seed + 3)[..., None] * _hx('#7a90c0') * 0.5).astype(F32)
    img = np.ascontiguousarray(ground, F32)
    master = _radio_master()
    st = _trim(_rot_tiles(master, (110, 140), (0, 60)))
    fx, fy, fti = _scatter(n, 16, seed + 4, 2, 2, jit=0.5)
    kp = r.random(len(fx)) < 0.50
    H.splat_rgba(img, st, fti[kp], fx[kp], fy[kp], amp=np.full(int(kp.sum()), 0.8, F32))
    tiles = _trim(_rot_tiles(master, (180, 240, 300), (0, 45, 90, 135)))
    ex, ey, ti = _scatter(n, 9, seed + 5, 3, 4, jit=0.5)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_gray_tint(r, len(ex), 0.9, 1.08))
    img = _fine(img, seed + 46, 0.10)
    Ln = H.sstep(0.05, 0.85, H.lum(img))
    M, R, CC = _curves(Ln, (60.0, 255.0), (90.0, 10.0), (0.0, 16.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 93 bacterial colonies
# =========================================================================
def _grow(r, x, y, ang, ln, depth, maxd, out):
    k = max(3, int(ln / 13))
    a = ang + np.cumsum(r.normal(0, 0.16, k))
    px = x + np.concatenate([[0], np.cumsum(ln / k * np.cos(a))])
    py = y + np.concatenate([[0], np.cumsum(ln / k * np.sin(a))])
    out[depth].append(np.stack([px, py], 1))
    if depth < maxd:
        ae = a[-1]
        for sg in (-1, 1):
            _grow(r, px[-1], py[-1], ae + sg * r.uniform(0.35, 0.8), ln * 0.70, depth + 1, maxd, out)
        if r.random() < 0.55:
            m = k // 2
            _grow(r, px[m], py[m], a[max(m - 1, 0)] + r.choice([-1, 1]) * r.uniform(0.7, 1.1), ln * 0.55, depth + 1, maxd, out)


@_f("wx_bacterial_colony", "Bacillus Branching Colony",
    "Cream dendritic bacterial colonies branching across amber agar, fine white arms forking again and again from each centre.")
def bacterial_colony(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 93 Bacillus Colony Rings: 9 colonies each with 10 recursive wobbly arms (6 depth levels, 190 px root, 0.7 decay, mid-branch spurs), masks per depth with decreasing widths, distance-transform tube shading, concentric growth rings in colony and halo on the agar, speckled amber agar; SAT
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(5, 11, 24)))
    cen = H.jitter_pts(n, 700, seed + 2, jit=0.55, margin=0)
    out = [[] for _ in range(6)]
    for cx, cy in cen:
        for k in range(10):
            _grow(r, cx, cy, 2 * np.pi * k / 10 + r.uniform(-0.2, 0.2), 190.0, 0, 5, out)
    wd = (8, 5, 4, 3, 2, 2)
    m = np.zeros((n, n), np.uint8)
    for d in range(6):
        pl = [np.round(p * 4).astype(np.int32).reshape(-1, 1, 2) for p in out[d]]
        cv2.polylines(m, pl, False, 255, wd[d], cv2.LINE_AA, 2)
    rho = np.full((n, n), 1e4, F32)
    X, Y = H.xy(n)
    for cx, cy in cen:
        rho = np.minimum(rho, np.hypot(X - cx, Y - cy))
    ring = 0.5 + 0.5 * np.cos(2 * np.pi * rho / 17.0 + 2.0 * _z(H.noise(n, 30, seed + 3)))
    halo = H.sstep(560.0, 380.0, rho)
    at = np.clip(0.42 + 0.12 * z + 0.06 * _z(H.noise(n, 200, seed + 4)) + 0.09 * (ring - 0.5) * halo + 0.5 * 0.0, 0, 1)
    agar = H.ramp(at, [(0.0, '#5a2e08'), (0.5, '#a86a14'), (1.0, '#e0b040')]).astype(F32)
    agar = agar + (H.flake_mask(n, 0.0025, seed + 5)[..., None] * _hx('#f4d880') * 0.45).astype(F32)
    dt = cv2.distanceTransform((m > 100).astype(np.uint8) * 255, cv2.DIST_L2, 3)
    a = (m.astype(F32) / 255.0)
    tt = np.clip(dt / 3.5, 0, 1)
    body = H.ramp(np.clip(0.30 + 0.55 * tt + 0.22 * (ring - 0.5) + 0.10 * H.grain(n, seed + 6), 0, 1), [(0.0, '#8a6a30'), (0.5, '#e4d4a0'), (1.0, '#fff6d8')]).astype(F32)
    img = agar * (1 - a[..., None]) + body * a[..., None]
    img = _fine(img, seed + 47, 0.09)
    Ln = H.sstep(0.05, 0.90, H.lum(img))
    M, R, CC = _curves(Ln, (0.0, 70.0), (200.0, 90.0), (180.0, 60.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 94 slime mold
# =========================================================================
@_f("wx_slime_mold", "Slime Mold Network",
    "Yellow Physarum tubes linking food nodes in a branching network, thick trunks thinning to hair-fine feeders, on dark agar.")
def slime_mold(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 94 Slime Mold Network: Delaunay edges over ~290 jittered food nodes, MST + 13% shortcut loops, tube width from subtree flow (3 + 1.9*sqrt(size), cap 30), curved bezier tubes in 3 passes (dark rim, yellow body, bright core) + emboss + oat-flake nodes; WET
    from scipy.spatial import Delaunay
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import minimum_spanning_tree, breadth_first_order
    n = N
    r = H.rng(seed)
    pts = H.jitter_pts(n, 86, seed + 1, jit=0.95, margin=40).astype(np.float64)
    tri = Delaunay(pts)
    es = set()
    for s_ in tri.simplices:
        for a, b in ((s_[0], s_[1]), (s_[1], s_[2]), (s_[0], s_[2])):
            es.add((min(a, b), max(a, b)))
    E = np.array(sorted(es))
    d = np.hypot(*(pts[E[:, 0]] - pts[E[:, 1]]).T)
    w = d * (1 + 0.35 * r.random(len(E)))
    G = coo_matrix((w, (E[:, 0], E[:, 1])), shape=(len(pts), len(pts))).tocsr()
    T = minimum_spanning_tree(G).tocoo()
    tedges = set((min(a, b), max(a, b)) for a, b in zip(T.row, T.col))
    A = coo_matrix((np.ones(len(T.row)), (T.row, T.col)), shape=(len(pts), len(pts))).tocsr()
    root = int(np.argmin(np.hypot(pts[:, 0] - n / 2, pts[:, 1] - n / 2)))
    order, pred = breadth_first_order(A + A.T, root, directed=False, return_predecessors=True)
    size = np.ones(len(pts))
    for v in order[::-1]:
        if pred[v] >= 0:
            size[pred[v]] += size[v]
    edges = []
    for a, b in tedges:
        child = b if pred[b] == a else a
        edges.append((a, b, min(26.0, 4.0 + 1.5 * np.sqrt(size[child]))))
    for (a, b), dd in zip(E, d):
        if (a, b) not in tedges and dd < 130 and r.random() < 0.20:
            edges.append((a, b, 4.0))
    edges.sort(key=lambda e: e[2])
    masks = [np.zeros((n, n), np.uint8) for _ in range(3)]
    for a, b, wd in edges:
        p0, p1 = pts[a], pts[b]
        dv = p1 - p0
        ln = np.hypot(*dv) + 1e-6
        nv = np.array([-dv[1], dv[0]]) / ln
        t_ = np.linspace(0, 1, 9)[:, None]
        mid = (p0 + p1) / 2 + nv * r.normal(0, 0.10) * ln
        P = (1 - t_) ** 2 * p0 + 2 * (1 - t_) * t_ * mid + t_ ** 2 * p1
        pl = [np.round(P * 4).astype(np.int32).reshape(-1, 1, 2)]
        cv2.polylines(masks[0], pl, False, 255, int(wd + 4), cv2.LINE_AA, 2)
        cv2.polylines(masks[1], pl, False, 255, int(wd), cv2.LINE_AA, 2)
        cv2.polylines(masks[2], pl, False, 255, max(1, int(wd * 0.4)), cv2.LINE_AA, 2)
    m0, m1, m2 = [mm.astype(F32) / 255.0 for mm in masks]
    z = _z(H.fbm(n, seed + 2, cells=(5, 11, 24)))
    img = H.ramp(np.clip(0.34 + 0.14 * z + 0.05 * _z(H.noise(n, 160, seed + 3)), 0, 1), [(0.0, '#241a0a'), (0.5, '#3a2c14'), (1.0, '#5a4624')]).astype(F32)
    img = img + (H.flake_mask(n, 0.002, seed + 4)[..., None] * _hx('#a89060') * 0.5).astype(F32)
    deg = np.bincount(np.concatenate([[a for a, b, w_ in edges], [b for a, b, w_ in edges]]), minlength=len(pts))
    oat = [(x, y) for (x, y), dg in zip(pts, deg) if dg >= 3 and r.random() < 0.22]
    base = np.zeros((n, n, 4), F32)
    for x, y in oat:
        if 24 < x < n - 24 and 24 < y < n - 24:
            _blob(base, x, y, 24.0, 16.0, r.uniform(0, 3.14), _hx('#5a4a30'), _hx('#b8a070'), _hx('#e8dcb0'), 0.3, 1.0)
    ba = base[..., 3:4]
    img = img * (1 - ba) + base[..., :3] * ba
    relief = H.emboss(H.blur(m1, 2.0), 3.0)
    body = H.ramp(np.clip(0.55 + 0.40 * relief * 6.0 + 0.10 * H.grain(n, seed + 5), 0, 1), [(0.0, '#8a6a08'), (0.5, '#e8c418'), (1.0, '#fff48a')]).astype(F32)
    img = img * (1 - 0.60 * m0[..., None]) + _hx('#6a5000') * (0.60 * m0[..., None]) * (1 - m1[..., None])
    img = img * (1 - m1[..., None]) + body * m1[..., None]
    img = img + (m2 * 0.35)[..., None] * _hx('#fff6a0')
    img = _fine(img, seed + 48, 0.10)
    Ln = H.sstep(0.05, 0.85, H.lum(img))
    M, R, CC = _curves(Ln, (10.0, 96.0), (150.0, 28.0), (44.0, 16.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 95 volvox
# =========================================================================
def _volvox_shell(M, cx, cy, Rs, Nn, lo, hi, part, ph0, scale):
    i = np.arange(Nn) + 0.5
    zz = 1 - 2 * i / Nn
    rho = np.sqrt(1 - zz * zz)
    ph = i * 2.399963 + ph0
    for k in np.argsort(zz):
        z = zz[k]
        if (part == 'back') != (z < 0):
            continue
        x, y = cx + Rs * rho[k] * np.cos(ph[k]), cy + Rs * rho[k] * np.sin(ph[k])
        f = 0.30 if z < 0 else 0.55 + 0.45 * z
        sz = scale * (0.45 + 0.55 * abs(z))
        _blob(M, x, y, sz, sz * 0.82, ph[k], lo * f, hi * f, _hx('#f0ffd8'), 0.5 * max(z, 0), 1.0)


def _volvox_master(S=360, seed=5):
    r = H.rng(seed)
    M = _mk(S)
    c = S / 2.0
    R = 0.44 * S
    gx, gy = H.tile_xy(S)
    rr = np.hypot(gx, gy)
    _put(M, _hx('#206a40'), H.sstep(R + 1.2, R - 1.2, rr) * 0.22)
    lo, hi = _hx('#1a6a30'), _hx('#7aff70')
    _volvox_shell(M, c, c, R * 0.97, 300, lo, hi, 'back', 0.0, 6.5)
    for k in range(4):
        a, d = r.uniform(0, 6.283), r.uniform(0.0, 0.50) * R
        dx, dy = c + d * np.cos(a), c + d * np.sin(a)
        dr = r.uniform(0.15, 0.21) * S
        _put(M, _hx('#a89818'), H.sstep(dr + 1.0, dr - 1.0, np.hypot(gx - (dx - c), gy - (dy - c))) * 0.35)
        _volvox_shell(M, dx, dy, dr, 90, _hx('#8a7a10'), _hx('#f0dc50'), 'back', k, 4.2)
        _volvox_shell(M, dx, dy, dr, 90, _hx('#8a7a10'), _hx('#f0dc50'), 'front', k, 4.2)
        _put(M, _hx('#e8d850'), np.exp(-((np.hypot(gx - (dx - c), gy - (dy - c)) - dr) / 1.8) ** 2) * 0.7)
    _volvox_shell(M, c, c, R * 0.97, 300, lo, hi, 'front', 0.0, 6.5)
    _put(M, _hx('#b8ffb0'), np.exp(-((rr - R) / 2.2) ** 2) * 0.8)
    return M


@_f("wx_volvox_spheres", "Volvox Spheres",
    "Translucent green Volvox colonies, shells of bright flagellate cells with golden daughter colonies swelling inside.")
def volvox_spheres(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 95 Volvox Spheres: Fibonacci-sphere shell master (300 cells, dim back hemisphere, 4 golden daughter colonies with their own 90-cell shells, bright rim), 3 sizes x 3 rotations on a jittered grid + blurred depth spheres over a dark teal plankton field; FLK
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(5, 11, 24)))
    ground = H.ramp(np.clip(0.30 + 0.14 * z + 0.05 * _z(H.noise(n, 150, seed + 2)), 0, 1), [(0.0, '#06201c'), (0.5, '#0c3a34'), (1.0, '#145a4c')]).astype(F32)
    ground = ground + (H.flake_mask(n, 0.003, seed + 3)[..., None] * _hx('#58c0a0') * 0.5).astype(F32)
    img = np.ascontiguousarray(ground, F32)
    master = _volvox_master()
    bg = [cv2.GaussianBlur(t, (0, 0), 4.0) for t in _rot_tiles(master, (260, 330), (0, 40))]
    bx, by, bti = _scatter(n, 6, seed + 4, 2, 2, jit=0.45)
    H.splat_rgba(img, bg, bti, bx, by, amp=np.full(len(bx), 0.30, F32))
    tiles = _trim(_rot_tiles(master, (200, 250, 310), (0, 40, 80)))
    ex, ey, ti = _scatter(n, 8, seed + 5, 3, 3, jit=0.45)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_gray_tint(r, len(ex), 0.9, 1.1))
    img = _fine(img, seed + 49, 0.10)
    Ln = H.sstep(0.05, 0.80, H.lum(img))
    M, R, CC = _curves(Ln, (30.0, 200.0), (150.0, 40.0), (70.0, 20.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 96 mycelium
# =========================================================================
def _hyphae(r, n, starts, steps=90, step=6.0, pb=0.03, Tmax=1500):
    K0 = len(starts)
    P = np.zeros((Tmax, steps + 1, 2), F32)
    ang = np.zeros(Tmax, F32)
    gen = np.zeros(Tmax, np.int16)
    pos = np.zeros((Tmax, 2), F32)
    P[:K0, 0] = starts
    pos[:K0] = P[:K0, 0]
    ang[:K0] = r.uniform(0, 6.2832, K0)
    T = K0
    for s in range(1, steps + 1):
        ang[:T] += r.normal(0, 0.22, T).astype(F32)
        pos[:T, 0] += step * np.cos(ang[:T])
        pos[:T, 1] += step * np.sin(ang[:T])
        P[:T, s] = pos[:T]
        if T < Tmax:
            sp = np.nonzero(r.random(T) < pb)[0][:Tmax - T]
            m = len(sp)
            if m:
                P[T:T + m, :s + 1] = P[sp, s][:, None, :]
                ang[T:T + m] = ang[sp] + r.choice([-1, 1], m) * r.uniform(0.5, 1.2, m)
                gen[T:T + m] = gen[sp] + 1
                pos[T:T + m] = pos[sp]
                T += m
    return P[:T], gen[:T]


@_f("wx_mycelium_web", "Mycelium Web",
    "A glowing white mycelium of branching hyphae that fork, wander and fuse into a fine lace over dark forest soil.")
def mycelium_web(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 96 Mycelium Web: vectorised hyphal growth sim (45 founders, 90 steps of 6 px, heading noise 0.22, 4% fork rate to ~1300 tips) drawn in 3 width classes by generation + ~15% cKDTree anastomosis links, glow from two blurs, granular soil; BRU along hyphae
    from scipy.spatial import cKDTree
    n = N
    r = H.rng(seed)
    P, gen = _hyphae(r, n, H.jitter_pts(n, 205, seed + 7, jit=0.9, margin=0).astype(F32))
    K = len(P)
    cv = None
    for lo_, hi_, th in ((0, 0, 3), (1, 2, 2), (3, 99, 1)):
        sel = (gen >= lo_) & (gen <= hi_)
        if sel.any():
            val = np.clip(255 - 20 * gen[sel], 120, 255).astype(np.float64)
            cv = H.lines3(n, P[sel], val, th, canvas=cv)
    sub = np.unique(np.round(P[:, ::6].reshape(-1, 2) / 3.0) * 3.0, axis=0)
    tree = cKDTree(sub)
    prs = np.array(sorted(tree.query_pairs(22.0)))
    if len(prs):
        dd_ = np.hypot(*(sub[prs[:, 0]] - sub[prs[:, 1]]).T)
        prs = prs[(dd_ > 9.0) & (r.random(len(prs)) < 0.15)]
    if len(prs):
        links = np.stack([sub[prs[:, 0]], sub[prs[:, 1]]], 1)
        cv = H.lines3(n, links, np.full(len(links), 200.0), 1, canvas=cv)
    V = H.u8f(cv[..., 0])
    glow = 0.6 * H.blur(V, 2.0) + 0.4 * H.blur(V, 7.0)
    z = _z(H.fbm(n, seed + 2, cells=(5, 11, 24)))
    soil = H.ramp(np.clip(0.34 + 0.14 * z + 0.05 * _z(H.noise(n, 180, seed + 3)), 0, 1), [(0.0, '#1c140e'), (0.5, '#2e2216'), (1.0, '#4a3824')]).astype(F32)
    soil = soil + (H.flake_mask(n, 0.004, seed + 4)[..., None] * _hx('#8a7050') * 0.5).astype(F32)
    img = soil + V[..., None] * _hx('#f2f2e8') * 0.95 + glow[..., None] * _hx('#c8d8b0') * 0.45
    img = _fine(img, seed + 50, 0.10)
    Ln = H.sstep(0.05, 0.90, H.lum(img))
    M, R, CC = _curves(Ln, (0.0, 120.0), (230.0, 70.0), (200.0, 60.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 97 gram stain
# =========================================================================
def _rodm(S, ax, ay, e, m, h, n_=1):
    M = _mk(S)
    _blob(M, S / 2, S / 2, ax, ay, 0.0, _hx(e), _hx(m), _hx(h), 0.35, 1.0)
    _strokes(M, [np.array([[S / 2, S / 2 - ay * 0.8], [S / 2, S / 2 + ay * 0.8]])], 1, _hx(e))
    return M


def _chainm(S, e, m, h):
    M = _mk(S)
    for k in range(5):
        x = S / 2 + (k - 2) * 0.19 * S
        y = S / 2 + 0.05 * S * np.sin(k * 0.9)
        _blob(M, x, y, 0.105 * S, 0.046 * S, 0.0, _hx(e), _hx(m), _hx(h), 0.35, 1.0)
    return M


def _coccus(S, e, m, h):
    M = _mk(S)
    _blob(M, S / 2, S / 2, 24, 24, 0.0, _hx(e), _hx(m), _hx(h), 0.4, 1.0)
    return M


def _clusterm(S, e, m, h, seed):
    r = H.rng(seed)
    M = _mk(S)
    P = []
    for k in range(15):
        a, d = r.uniform(0, 6.283), 0.26 * S * np.sqrt(r.random())
        P.append((S / 2 + d * np.cos(a), S / 2 + d * np.sin(a)))
    for x, y in sorted(P, key=lambda p: p[1]):
        _blob(M, x, y, 0.072 * S, 0.072 * S, 0.0, _hx(e), _hx(m), _hx(h), 0.4, 1.0)
    return M


@_f("wx_gram_stain", "Gram Stain Smear",
    "A stained microscope slide: violet Gram-positive rods, chains and grape clusters mixed with pink Gram-negative rods.")
def gram_stain(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 97 Gram Stain Smear: rod / 5-rod chain / 15-coccus cluster / single coccus masters in two stains (crystal violet, safranin pink), ~1300 randomly rotated + shuffled stamps over a mauve smear field with stain debris; two stain families
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(5, 11, 24)))
    img = H.ramp(np.clip(0.55 + 0.12 * z + 0.05 * _z(H.noise(n, 170, seed + 2)), 0, 1), [(0.0, '#a888a0'), (0.5, '#d2b8c6'), (1.0, '#ecd8e0')]).astype(F32)
    img = img - (H.flake_mask(n, 0.003, seed + 3)[..., None] * 0.18).astype(F32)
    pv = ('#2a0c5a', '#6a3ab0', '#c0a0f0')
    pk = ('#8a1a50', '#e0709a', '#ffd0e0')
    kinds = [
        (_rodm(140, 61, 13, *pv), (90, 110, 130), tuple(range(0, 360, 30)), 260),
        (_rodm(140, 61, 13, *pk), (90, 110, 130), tuple(range(0, 360, 30)), 170),
        (_chainm(300, *pv), (170, 220), tuple(range(0, 360, 30)), 50),
        (_chainm(300, *pk), (170, 220), tuple(range(0, 360, 30)), 30),
        (_clusterm(200, *pv, seed + 11), (110, 150), (0, 120, 240), 36),
        (_clusterm(200, *pk, seed + 12), (110, 150), (0, 120, 240), 30),
        (_coccus(60, *pv), (22, 28), (0,), 260),
        (_coccus(60, *pk), (22, 28), (0,), 200),
    ]
    tiles, off, tis, xs, ys = [], 0, [], [], []
    for master, sizes, angs, cnt in kinds:
        if master.shape[0] == 60:
            ts = [cv2.resize(master, (sz, sz), interpolation=cv2.INTER_AREA) for sz in sizes]
        else:
            ts = _rot_tiles(master, sizes, angs)
        ts = _trim(ts)
        tiles += ts
        tis.append(off + r.integers(0, len(ts), cnt))
        xs.append(r.random(cnt) * n)
        ys.append(r.random(cnt) * n)
        off += len(ts)
    ti, ex, ey = np.concatenate(tis), np.concatenate(xs), np.concatenate(ys)
    o = r.permutation(len(ti))
    H.splat_rgba(img, tiles, ti[o], ex[o], ey[o], tint=_gray_tint(r, len(ti), 0.88, 1.10))
    img = _fine(img, seed + 51, 0.10)
    Ln = H.sstep(0.05, 0.85, H.lum(img))
    M, R, CC = _curves(Ln, (10.0, 150.0), (190.0, 40.0), (160.0, 20.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 98 tardigrade
# =========================================================================
def _tardi_master(S=360):
    M = _mk(S)
    c = S / 2.0
    xs = [c + 0.22 * S, c + 0.11 * S, c, c - 0.11 * S]
    for x in xs:
        for sg in (-1, 1):
            lx, ly = x + 0.005 * S, c + sg * 0.12 * S
            _blob(M, lx, ly, 0.036 * S, 0.048 * S, 0.0, _hx('#6a6a3a'), _hx('#d8d4a0'), _hx('#f8f4d0'), 0.3, 1.0)
            _strokes(M, [np.array([[lx, ly + sg * 0.04 * S], [lx + dx_ * 0.03 * S, ly + sg * 0.07 * S]]) for dx_ in (-1, 0, 1)], 2, _hx('#fff0c0'))
    for x, ry in ((c + 0.24 * S, 0.075 * S), (c + 0.12 * S, 0.092 * S), (c, 0.100 * S), (c - 0.12 * S, 0.092 * S)):
        _blob(M, x, c, 0.09 * S, ry, 0.0, _hx('#7a7a48'), _hx('#e8e4bc'), _hx('#fffbe0'), 0.4, 1.2)
    _blob(M, c + 0.04 * S, c, 0.20 * S, 0.042 * S, 0.0, _hx('#4a5a2a'), _hx('#8a9a48'), None, 0.0, 1.5)
    _blob(M, c - 0.23 * S, c, 0.065 * S, 0.062 * S, 0.0, _hx('#7a7a48'), _hx('#eeeac4'), _hx('#fffbe0'), 0.4, 1.2)
    _blob(M, c - 0.285 * S, c, 0.014 * S, 0.014 * S, 0.0, _hx('#2a2410'), _hx('#4a4020'), None, 0.0, 1.0)
    for sg in (-1, 1):
        _blob(M, c - 0.235 * S, c + sg * 0.034 * S, 0.010 * S, 0.010 * S, 0.0, _hx('#000000'), _hx('#202020'), None, 0.0, 1.0)
    return M


def _leaflet(S=64):
    M = _mk(S)
    _blob(M, S / 2, S / 2, 26, 8.5, 0.0, _hx('#1e2c10'), _hx('#5a7a2a'), _hx('#b8d070'), 0.3, 1.0)
    _strokes(M, [np.array([[S * 0.10, S / 2], [S * 0.90, S / 2]])], 1, _hx('#9ab858'))
    return M


@_f("wx_tardigrade_moss", "Water Bear Moss",
    "Chubby eight-legged tardigrades with clawed feet lumber through a dense thatch of olive moss leaflets.")
def tardigrade_moss(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 98 Water Bear Moss: segmented tardigrade master (4 trunk segments, 4 clawed leg pairs, head with mouth + 2 eyes, gut), ~18 stamps in 3 sizes x 12 rotations; ~4200 olive moss leaflet stamps below and ~500 over them; SAT
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(5, 11, 24)))
    img = H.ramp(np.clip(0.30 + 0.14 * z, 0, 1), [(0.0, '#10160a'), (0.5, '#1e2a10'), (1.0, '#34481c')]).astype(F32)
    lt = _rot_tiles(_leaflet(), (44, 60), tuple(range(0, 360, 30)))

    def leaves(K):
        lx, ly = r.random(K) * n, r.random(K) * n
        li = r.integers(0, 2, K) * 12 + r.integers(0, 12, K)
        o = np.argsort(ly)
        H.splat_rgba(img, lt, li[o], lx[o], ly[o], tint=_gray_tint(r, K, 0.65, 1.25)[o])
    leaves(4200)
    tt = _trim(_rot_tiles(_tardi_master(), (300, 360, 420), tuple(range(0, 360, 30))))
    ex, ey, _ = _scatter(n, 4, seed + 4, 1, 1, jit=0.45)
    kp = r.random(len(ex)) < 0.75
    ex, ey = ex[kp], ey[kp]
    ti = r.integers(0, 3, len(ex)) * 12 + r.integers(0, 12, len(ex))
    H.splat_rgba(img, tt, ti, ex, ey, tint=_gray_tint(r, len(ex), 0.9, 1.08))
    leaves(500)
    img = _fine(img, seed + 52, 0.08)
    Ln = H.sstep(0.04, 0.80, H.lum(img))
    M, R, CC = _curves(Ln, (0.0, 90.0), (210.0, 100.0), (150.0, 40.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 99 paramecium
# =========================================================================
def _para_cell(S=300, seed=3):
    r = H.rng(seed)
    M = _mk(S)
    c = S / 2.0
    ax, ay = 0.40 * S, 0.145 * S
    polys = []
    for t in np.linspace(0, 2 * np.pi, 46, endpoint=False):
        x, y = c + ax * np.cos(t), c + ay * np.sin(t)
        nx, ny = np.cos(t) / ax, np.sin(t) / ay
        nn = np.hypot(nx, ny)
        ln = 0.072 * S * (0.8 + 0.4 * r.random())
        polys.append(np.array([[x, y], [x + nx / nn * ln, y + ny / nn * ln]]))
    _strokes(M, polys, 3, _hx('#c8f4ff'))
    _blob(M, c, c, ax, ay, 0.0, _hx('#2a8a9a'), _hx('#8ae4ee'), _hx('#e8ffff'), 0.35, 1.5)
    # pellicle alveoli: hex dot lattice across the body (carries the 8-32 px band)
    pr = 17.0
    for jj, yy in enumerate(np.arange(-ay * 0.9, ay * 0.9 + 1, pr * 0.866)):
        for xx in np.arange(-ax * 0.95 + (pr * 0.5 if jj % 2 else 0.0), ax * 0.95 + 1, pr):
            if (xx / (ax * 0.95)) ** 2 + (yy / (ay * 0.9)) ** 2 < 1.0:
                _blob(M, c + xx, c + yy, 4.6, 4.6, 0.0, _hx('#1c6a7c'), _hx('#2a8a9e'), None, 0.0, 1.0)
    _strokes(M, [np.array([[c - 0.34 * S, c - 0.02 * S], [c - 0.20 * S, c + 0.04 * S], [c - 0.05 * S, c + 0.05 * S]])], 3, _hx('#1c5a68'))
    _blob(M, c + 0.05 * S, c - 0.01 * S, 0.07 * S, 0.045 * S, 0.0, _hx('#2a5a7a'), _hx('#5a8aaa'), None, 0.0, 1.2)
    for vx, vy in ((c - 0.22 * S, c - 0.05 * S), (c + 0.26 * S, c + 0.04 * S)):
        _strokes(M, [np.array([[vx, vy], [vx + 0.06 * S * np.cos(a), vy + 0.06 * S * np.sin(a)]]) for a in np.linspace(0, 6.283, 8)[:-1]], 1, _hx('#e8ffff'))
        _blob(M, vx, vy, 0.035 * S, 0.035 * S, 0.0, _hx('#6ac0d0'), _hx('#e0fcff'), _hx('#ffffff'), 0.5, 1.0)
    for k in range(14):
        a, d = r.uniform(0, 6.283), r.uniform(0.0, 0.8)
        _blob(M, c + 0.30 * S * d * np.cos(a), c + 0.10 * S * d * np.sin(a), 0.018 * S, 0.018 * S, 0.0, _hx('#2a5a1a'), _hx('#5a9a3a'), None, 0.0, 1.0)
    for k in range(34):
        a, d = r.uniform(0, 6.283), np.sqrt(r.random()) * 0.90
        dark = k % 2 == 0
        _blob(M, c + 0.35 * S * d * np.cos(a), c + 0.115 * S * d * np.sin(a), 0.034 * S, 0.034 * S, 0.0, _hx('#14566a') if dark else _hx('#7ad0e0'), _hx('#1e7a90') if dark else _hx('#e8ffff'), None, 0.0, 1.0)
    return M


@_f("wx_paramecium_cilia", "Ciliate Swarm",
    "A swarm of glassy aqua slipper-shaped ciliates, their bodies fringed with beating cilia, vacuoles and dark nuclei inside.")
def paramecium_cilia(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 99 Ciliate Swarm: slipper master (110 cilia strokes of jittered length, oral groove, macronucleus, 2 star-canal contractile vacuoles, 14 food vacuoles), 3 sizes x 12 rotations on a jittered grid + small fillers, dark indigo darkfield water with plankton; FLK
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(5, 11, 24)))
    img = H.ramp(np.clip(0.34 + 0.035 * z + 0.02 * _z(H.noise(n, 150, seed + 2)) + 0.15 * _z(H.noise(n, 130, seed + 8)) + 0.13 * _z(H.noise(n, 200, seed + 9)), 0, 1), [(0.0, '#0c0a2a'), (0.5, '#1a1244'), (1.0, '#2c2068')]).astype(F32)
    dts = np.zeros((n, n), F32)
    H.points(dts, r.random(3600) * n, r.random(3600) * n, r.uniform(0.5, 1.0, 3600))
    dts = H.sstep(0.25, 0.60, H.blur(dts, 3.2) * 63.0)
    img = img + (dts[..., None] * _hx('#c8b8ff') * 0.62).astype(F32)
    master = _para_cell()
    st = _trim(_rot_tiles(master, (90, 110), tuple(range(0, 360, 60))))
    fx, fy, fti = _scatter(n, 18, seed + 4, 2, 6, jit=0.5)
    kp = r.random(len(fx)) < 0.50
    H.splat_rgba(img, st, fti[kp], fx[kp], fy[kp], amp=np.full(int(kp.sum()), 0.85, F32))
    tiles = _trim(_rot_tiles(master, (140, 180, 225), tuple(range(0, 360, 30))))
    ex, ey, ti = _scatter(n, 11, seed + 5, 3, 12, jit=0.45)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_gray_tint(r, len(ex), 0.9, 1.08))
    img = _fine(img, seed + 53, 0.19)
    Ln = H.sstep(0.05, 0.85, H.lum(img))
    M, R, CC = _curves(Ln, (30.0, 170.0), (110.0, 20.0), (40.0, 16.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 100 cyanobacterial mat
# =========================================================================
@_f("wx_cyanobacteria_mat", "Stromatolite Mat",
    "Cross-section of a laminated cyanobacterial mat: thin teal, olive, brown and cream layers draped over rising domes.")
def cyanobacteria_mat(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 100 Stromatolite Mat: 7 gaussian domes (230-420 px wide) warp the lamina coordinate, band phase s/16 + low-frequency thickness noise, per-lamina palette pick (teal/olive/brown/cream/dark) by hash, bottom-dark shading per band, 20 px micro-lamination, sand grains; SAT
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)
    nd = 7
    xi = (np.arange(nd) + 0.5) * n / nd + r.uniform(-90, 90, nd)
    wi, ai = r.uniform(230, 420, nd), r.uniform(110, 230, nd)
    xs = np.arange(n, dtype=F32)
    Hx = np.zeros(n, F32)
    for x0, w_, a_ in zip(xi, wi, ai):
        Hx += (a_ * np.exp(-((xs - x0) / w_) ** 2)).astype(F32)
    s = Y + Hx[None, :] + 20.0 * _z(H.fbm(n, seed + 1, cells=(3, 6, 12)))
    ph = s / 16.0 + 2.2 * _z(H.fbm(n, seed + 2, cells=(2, 4, 8)))
    k = np.floor(ph)
    fr = (ph - k).astype(F32)
    h = H.hash01(k.astype(np.int64), seed + 3)
    pal = np.array([_hx('#2a7a78'), _hx('#6a6a2a'), _hx('#6a4a2a'), _hx('#e0d4b0'), _hx('#1a3a30')], F32)
    col = pal[np.minimum((h * 5).astype(np.int64), 4)]
    col = col * (0.62 + 0.52 * fr ** 0.7)[..., None]
    col = col * (1 + 0.07 * np.sin(s / 3.2))[..., None]
    col = col - (H.flake_mask(n, 0.01, seed + 4)[..., None] * 0.18).astype(F32) + (H.flake_mask(n, 0.01, seed + 5)[..., None] * 0.14).astype(F32)
    img = _fine(col.astype(F32), seed + 54, 0.08)
    Ln = H.sstep(0.05, 0.85, H.lum(img))
    M, R, CC = _curves(Ln, (0.0, 90.0), (200.0, 100.0), (150.0, 50.0))
    return _out(np.clip(img, 0, 1), M, R, CC)



# =========================================================================
# 101 virus capsids
# =========================================================================
def _capsid_master(S=300, seed=1, tone=0):
    r = H.rng(seed)
    M = _mk(S)
    c = S / 2.0
    Rc = 0.27 * S
    spikes = 12
    polys, knobs = [], []
    for k in range(spikes):
        a = 2 * np.pi * k / spikes
        l0 = Rc * 0.90
        l1 = Rc + 0.16 * S * (0.85 + 0.30 * r.random())
        polys.append(np.array([[c + l0 * np.cos(a), c + l0 * np.sin(a)], [c + l1 * np.cos(a), c + l1 * np.sin(a)]]))
        knobs.append((c + (l1 + 3) * np.cos(a), c + (l1 + 3) * np.sin(a)))
    _strokes(M, polys, 6, _hx('#c42a2e'))
    for kx, ky in knobs:
        _blob(M, kx, ky, 10.5, 10.5, 0.0, _hx('#7a1014'), _hx('#e84844'), _hx('#ffd8cc'), 0.55, 1.0)
    V = [np.array([c + Rc * np.cos(np.pi / 6 + k * np.pi / 3), c + Rc * np.sin(np.pi / 6 + k * np.pi / 3)]) for k in range(6)]
    lite = (0.84, 0.66, 0.92, 0.74, 0.58, 0.88) if tone == 0 else (0.62, 0.90, 0.70, 0.84, 0.96, 0.66)
    base = _hx('#aab0ba') if tone == 0 else _hx('#b4aeb4')
    for k in range(6):
        _tri(M, (c, c), tuple(V[k]), tuple(V[(k + 1) % 6]), base * lite[k])
    gx, gy = H.tile_xy(S)
    hexd = np.maximum.reduce([np.abs(gx * np.cos(t) + gy * np.sin(t)) for t in (0.0, np.pi / 3, 2 * np.pi / 3)]) / (Rc * 0.866)
    ins = (hexd < 1.0).astype(F32)
    pr = 17.0
    for jj, yy in enumerate(np.arange(-Rc * 0.84, Rc * 0.84 + 1, pr * 0.866)):
        for xx in np.arange(-Rc * 0.9 + (pr * 0.5 if jj % 2 else 0.0), Rc * 0.9 + 1, pr):
            px_, py_ = c + xx, c + yy
            if hexd[int(py_), int(px_)] < 0.80:
                fk = int(((np.arctan2(yy, xx) - np.pi / 6) % (2 * np.pi)) // (np.pi / 3)) % 6
                mid = base * lite[fk] * 1.18
                _blob(M, px_, py_, 5.0, 5.0, 0.0, mid * 0.22, np.clip(mid, 0, 1), _hx('#ffffff'), 0.7, 1.0)
    edges = [np.array([V[k], V[(k + 1) % 6]]) for k in range(6)] + [np.array([(c, c), V[k]]) for k in range(6)]
    _strokes(M, edges, 2, _hx('#eef1f6'))
    _put(M, _hx('#0a0c12'), np.clip(0.20 * (gx + gy) / Rc + 0.14, 0, 0.45) * ins)
    return M


@_f("wx_virus_capsids", "Virus Capsids",
    "Dense faceted icosahedral virus capsids in steel grey, each bristling with red spike proteins, over a dark plasma field.")
def virus_capsids(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 101 Virus Capsids: 2 hex-silhouette capsid masters (6 shaded facets, capsomere dot lattice, 12 knobbed red spikes), 3 sizes x 4 rotations on a jittered grid over smaller filler capsids, dark blue-grey plasma ground; CHR
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(6, 14, 40)))
    img = H.ramp(np.clip(0.34 + 0.06 * z + 0.08 * _z(H.noise(n, 150, seed + 2)), 0, 1), [(0.0, '#080a12'), (0.5, '#161a2a'), (1.0, '#2c3450')]).astype(F32)
    masters = [_capsid_master(300, seed + 3 + k, k) for k in range(2)]
    angs = (0, 7, 14, 21)
    sm = _trim(sum([_rot_tiles(m, (80, 100), angs) for m in masters], []))
    fx, fy, fti = _scatter(n, 24, seed + 4, 4, 4, jit=0.5)
    kp = r.random(len(fx)) < 0.62
    H.splat_rgba(img, sm, fti[kp], fx[kp], fy[kp], amp=np.full(int(kp.sum()), 0.9, F32))
    tiles = _trim(sum([_rot_tiles(m, (130, 165, 205), angs) for m in masters], []))
    ex, ey, ti = _scatter(n, 13, seed + 5, 6, 4, jit=0.42)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_gray_tint(r, len(ex), 0.9, 1.1))
    img = _fine(img, seed + 51, 0.10)
    Ln = H.sstep(0.04, 0.78, H.lum(img))
    M, R, CC = _curves(Ln, (90.0, 255.0), (150.0, 2.0), (16.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 102 turing spots
# =========================================================================
def _spotfield(n, spacing, sig, amp, pair_p, d_rng, sd, jit=0.95):
    pts = H.jitter_pts(n, spacing, sd, jit=jit)
    K = len(pts)
    rr = H.rng(sd + 7)
    am = rr.uniform(amp[0], amp[1], K).astype(F32)
    xs, ys = pts[:, 0], pts[:, 1]
    cv = np.zeros((n, n), F32)
    H.points(cv, xs, ys, am, mode="add")
    pm = rr.random(K) < pair_p
    a = rr.uniform(0, 6.2832, K)
    d = rr.uniform(d_rng[0], d_rng[1], K)
    H.points(cv, (xs + np.cos(a) * d)[pm], (ys + np.sin(a) * d)[pm], am[pm] * rr.uniform(0.7, 1.0, int(pm.sum())).astype(F32), mode="add")
    return (cv2.GaussianBlur(cv, (0, 0), float(sig)) * F32(2 * np.pi * sig * sig)).astype(F32)


@_f("wx_turing_spots", "Reaction-Diffusion Spots",
    "Leopard-like reaction-diffusion spots in black on ochre, many splitting in two like dividing cells, ringed with dark halos.")
def turing_spots(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 102 Reaction-Diffusion Spots: Gaussian-blurred impulse fields thresholded at 0.85 (sigma 10 spots with 40% dividing peanut pairs at d 24-30, rosette cores where the summed field is high) + sigma 4 freckles + dark halos on an ochre fur ground; TWO (matte black spots, metallic ochre)
    n = N
    r = H.rng(seed)
    f1 = _spotfield(n, 58, 14.0, (1.35, 1.95), 0.32, (34, 43), seed + 11, jit=0.6)
    f2 = _spotfield(n, 30, 6.0, (1.25, 1.75), 0.0, (0, 1), seed + 12)
    t = 0.5 + 0.17 * _z(H.fbm(n, seed + 1, cells=(4, 9, 20, 44))) + 0.07 * _z(H.noise(n, 150, seed + 2))
    ground = H.ramp(np.clip(t, 0, 1), [(0.0, '#8a5a1c'), (0.5, '#c8963e'), (1.0, '#ecc874')]).astype(F32)
    halo = H.sstep(0.12, 0.80, f1)
    img = ground * (1.0 - 0.30 * halo)[..., None] + (_hx('#5a300c') * (0.30 * halo)[..., None]).astype(F32)
    free = H.sstep(0.45, 0.15, f1)
    blk = np.maximum(H.sstep(0.80, 0.90, f1), H.sstep(0.88, 0.98, f2) * free)
    core = H.sstep(2.05, 2.15, f1)
    img = img * (1.0 - blk)[..., None] + (_hx('#0a0604') * blk[..., None]).astype(F32)
    img = img * (1.0 - core)[..., None] + (ground * 0.74 * core[..., None]).astype(F32)
    img = _fine(img, seed + 61, 0.12)
    Ls = H.sstep(0.10, 0.22, H.lum(img))
    M, R, CC = _curves(Ls, (8.0, 238.0), (236.0, 26.0), (250.0, 16.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 103 algae bloom
# =========================================================================
@_f("wx_algae_bloom", "Algae Bloom Swirls",
    "Green algae dragged into marbled swirling streaks across dark water, bright scum riding the vortex arms.")
def algae_bloom(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 103 Algae Bloom Swirls: 4-octave noise dye advected backwards 16 times along a curl field (swirl arcs), banded marbling ramp dark water -> teal -> green -> chartreuse with iso-level water lines and scum flecks; WET
    n = N
    h2 = n // 2
    u, v = H.curl_field(512, seed + 1, cells=(3, 5, 9), gain=0.65)
    U = cv2.resize(u, (h2, h2), interpolation=cv2.INTER_LINEAR)
    V = cv2.resize(v, (h2, h2), interpolation=cv2.INTER_LINEAR)
    t = sum(w * _z(H.noise(h2, c, seed + 2 + k)) for k, (c, w) in enumerate(((30, 1.0), (64, 1.0), (130, 1.0), (260, 1.1), (420, 0.9)))) / 2.2
    st = F32(4.0)
    for k in range(16):
        t = H.warp(t.astype(F32), -U * st, -V * st)
    t = cv2.resize(_z(t), (n, n), interpolation=cv2.INTER_CUBIC)
    q = 0.5 + 0.5 * np.tanh(0.80 * t)
    img = H.ramp(q.astype(F32), [(0.0, '#030e12'), (0.25, '#0a363c'), (0.44, '#10685a'), (0.60, '#27a040'), (0.76, '#74c63a'), (0.91, '#d2e95a'), (1.0, '#f4ffb0')]).astype(F32)
    fr = (q * 13.0) % 1.0
    line = np.exp(-((fr - 0.5) / 0.08) ** 2).astype(F32)
    img *= (1.0 - 0.34 * line)[..., None]
    img += (H.flake_mask(n, 0.004, seed + 7)[..., None] * _hx('#b8f060') * 0.55).astype(F32)
    img = _fine(img, seed + 62, 0.15)
    Ln = H.sstep(0.04, 0.80, H.lum(img))
    M, R, CC = _curves(Ln, (4.0, 58.0), (15.0, 1.0), (16.0, 16.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 104 penicillium
# =========================================================================
def _colony_master(S=360, seed=1, brushes=70):
    r = H.rng(seed)
    M = _mk(S)
    c = S / 2.0
    R = 0.34 * S
    gx, gy = H.tile_xy(S)
    rr = np.hypot(gx, gy)
    th = np.arctan2(gy, gx)
    Rw = R * (1 + 0.045 * np.sin(3 * th + r.uniform(0, 6)) + 0.03 * np.sin(5 * th + r.uniform(0, 6)) + 0.02 * np.sin(9 * th + r.uniform(0, 6)))
    q = rr / Rw
    disc = H.sstep(1.015, 0.985, q)
    stops = [(0.0, '#1f6a68'), (0.30, '#2f8a80'), (0.62, '#4cae98'), (0.72, '#7cc4ae'), (0.84, '#e6f6ea'), (0.95, '#f8fdf8'), (1.0, '#ffffff')]
    col = H.ramp(np.clip(q, 0, 1).astype(F32), stops).astype(F32)
    g = _z(H.noise(S, max(2, S // 7), seed + 3))
    g2 = _z(H.noise(S, max(2, S // 3), seed + 4))
    rings = 1.0 - 0.20 * np.exp(-((((q * 5.5) % 1.0) - 0.5) / 0.12) ** 2)
    col = col * (1.0 + 0.20 * g + 0.10 * g2)[..., None] * rings[..., None]
    _put(M, np.clip(col, 0, 1), disc)
    polys = []
    for k in range(240):
        a = r.uniform(0, 2 * np.pi)
        r0 = R * r.uniform(0.90, 1.0)
        r1 = R * r.uniform(1.04, 1.13)
        bend = r.uniform(-0.10, 0.10)
        polys.append(np.array([[c + r0 * np.cos(a), c + r0 * np.sin(a)],
                               [c + (r0 + r1) * 0.5 * np.cos(a + bend * 0.5), c + (r0 + r1) * 0.5 * np.sin(a + bend * 0.5)],
                               [c + r1 * np.cos(a + bend), c + r1 * np.sin(a + bend)]]))
    _strokes(M, polys, 2, _hx('#f8fcf6'))
    stalks, fans, tips = [], [], []
    for k in range(brushes):
        a, d = r.uniform(0, 6.283), np.sqrt(r.random()) * 0.74
        bx, by = c + R * d * np.cos(a), c + R * d * np.sin(a)
        ph = r.uniform(0, 6.283)
        L = r.uniform(15, 22)
        tx, ty = bx + L * np.cos(ph), by + L * np.sin(ph)
        stalks.append(np.array([[bx, by], [tx, ty]]))
        for off in (-0.9, -0.45, 0.0, 0.45, 0.9):
            ex_, ey_ = tx + 10.5 * np.cos(ph + off), ty + 10.5 * np.sin(ph + off)
            fans.append(np.array([[tx, ty], [ex_, ey_]]))
            tips.append((ex_, ey_))
    _strokes(M, stalks, 2, _hx('#1a5650'))
    _strokes(M, fans, 2, _hx('#c4eedc'))
    for ex_, ey_ in tips:
        _blob(M, ex_, ey_, 2.8, 2.8, 0.0, _hx('#6ac0a4'), _hx('#e6fbf0'), None, 0.0, 1.0)
    return M


@_f("wx_penicillium", "Penicillium Brush",
    "Blue-green penicillium colonies on cream agar, granular rings inside white fuzzy margins, bristling with tiny brush-like conidiophores.")
def penicillium(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 104 Penicillium Brush: wobbly colony disk masters (colour ramp centre blue-green -> white margin, 7 px granules, concentric rings, 240 fuzzy margin hairs, 70 conidiophore brushes with spore tips), big colonies on a g=8 grid + satellite colonies on cream agar with bubbles; MAT
    n = N
    r = H.rng(seed)
    t = 0.5 + 0.20 * _z(H.fbm(n, seed + 1, cells=(5, 12, 28, 60))) + 0.08 * _z(H.noise(n, 160, seed + 2))
    img = H.ramp(np.clip(t, 0, 1), [(0.0, '#bba978'), (0.5, '#d6c796'), (1.0, '#e6dbb0')]).astype(F32)
    bub = np.zeros((n, n), F32)
    H.points(bub, r.random(900) * n, r.random(900) * n, r.uniform(0.5, 1.0, 900))
    bub = H.sstep(0.22, 0.55, cv2.GaussianBlur(bub, (0, 0), 3.0) * 60.0)
    img += (bub[..., None] * _hx('#f8f2d4') * 0.30).astype(F32)
    big = _colony_master(360, seed + 3, 70)
    sml = _colony_master(240, seed + 4, 22)
    angs = tuple(range(0, 360, 30))
    st = _trim(_rot_tiles(sml, (62, 82), angs))
    fx, fy, fti = _scatter(n, 22, seed + 5, 2, 12, jit=0.5)
    kp = r.random(len(fx)) < 0.55
    H.splat_rgba(img, st, fti[kp], fx[kp], fy[kp])
    tiles = _trim(_rot_tiles(big, (180, 225, 285), angs))
    ex, ey, ti = _scatter(n, 8, seed + 6, 3, 12, jit=0.40)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_tint(r, len(ex), 0.90, 1.10))
    img = _fine(img, seed + 63, 0.08)
    Ln = H.sstep(0.10, 0.90, H.lum(img))
    M, R, CC = _curves(Ln, (2.0, 36.0), (240.0, 172.0), (240.0, 130.0))
    return _out(np.clip(img, 0, 1), M, R, CC)



# =========================================================================
# 105 neuron culture
# =========================================================================
def _neuron_master(S=360, seed=1):
    r = H.rng(seed)
    M = _mk(S)
    c = S / 2.0
    segs = []

    def grow(x, y, ang, L, depth):
        if depth > 3 or L < 7:
            return
        x1, y1 = x + L * np.cos(ang), y + L * np.sin(ang)
        segs.append((x, y, x1, y1, depth))
        k = 2 if (depth < 3 or r.random() < 0.5) else 1
        for j in range(k):
            grow(x1, y1, ang + r.uniform(0.35, 0.80) * (1 if j == 0 else -1) + r.normal(0, 0.10), L * r.uniform(0.64, 0.80), depth + 1)

    nd = int(r.integers(5, 8))
    a0 = r.uniform(0, 6.283)
    for k in range(nd):
        a = a0 + 2 * np.pi * k / nd + r.uniform(-0.3, 0.3)
        grow(c + 16 * np.cos(a), c + 16 * np.sin(a), a, r.uniform(34, 48), 0)
    wid = (6, 5, 4, 3)
    for d in range(4):
        pl = [np.array([[x, y], [x1, y1]]) for (x, y, x1, y1, dd) in segs if dd == d]
        if pl:
            _strokes(M, pl, wid[d] + 4, _hx('#0f5a2c'))
    for d in range(4):
        pl = [np.array([[x, y], [x1, y1]]) for (x, y, x1, y1, dd) in segs if dd == d]
        if pl:
            _strokes(M, pl, wid[d], _hx('#46ff86'))
    for (x, y, x1, y1, dd) in segs:
        if dd == 3:
            _blob(M, x1, y1, 4.5, 4.5, 0.0, _hx('#2aa860'), _hx('#c8ffd8'), None, 0.0, 1.0)
    aa = a0 + r.uniform(0.0, 6.283)
    P = [np.array([c + 18 * np.cos(aa), c + 18 * np.sin(aa)])]
    for i in range(1, 15):
        aa += r.normal(0, 0.10)
        P.append(P[-1] + 11.5 * np.array([np.cos(aa), np.sin(aa)]))
    _strokes(M, [np.array(P)], 7, _hx('#106a50'))
    _strokes(M, [np.array(P)], 3, _hx('#7affd8'))
    _blob(M, c, c, 30, 28, 0.0, _hx('#2a0626'), _hx('#58124e'), None, 0.0, 4.0)
    _blob(M, c, c, 19, 17, 0.0, _hx('#7a0a5a'), _hx('#e41ec0'), _hx('#ffd0f4'), 0.7, 1.5)
    _blob(M, c + 3, c - 2, 6, 6, 0.0, _hx('#4a0a3a'), _hx('#8a1478'), None, 0.0, 1.0)
    return M


@_f("wx_neuron_culture", "Neuron Culture",
    "Fluorescent neuron culture: glowing magenta somas sprouting branching green dendrites and long cyan axons across a dark blue dish.")
def neuron_culture(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 105 Neuron Culture: 3 soma masters (recursive 4-level dendrite trees with glow, magenta soma + nucleolus, curved axon) on a g=7 grid over smaller filler neurons, plus a canvas-wide web of 130 random-walk axons with blurred glow, deep blue dish with fluorescent haze; CHR axons
    n = N
    r = H.rng(seed)
    t = 0.45 + 0.22 * _z(H.fbm(n, seed + 1, cells=(4, 9, 22, 48))) + 0.05 * _z(H.noise(n, 160, seed + 2))
    img = H.ramp(np.clip(t, 0, 1), [(0.0, '#080c26'), (0.5, '#10183c'), (1.0, '#22346e')]).astype(F32)
    axm = np.zeros((n, n), np.uint8)
    polys = []
    for k in range(130):
        p = np.array([r.uniform(0, n), r.uniform(0, n)])
        a = r.uniform(0, 6.283)
        L = []
        for i in range(70):
            a += r.normal(0, 0.12)
            p = p + 12.0 * np.array([np.cos(a), np.sin(a)])
            L.append(p.copy())
        polys.append(np.round(np.array(L) * 4).astype(np.int32).reshape(-1, 1, 2))
    cv2.polylines(axm, polys, False, 255, 3, cv2.LINE_AA, 2)
    am = axm.astype(F32) / 255.0
    glow = cv2.GaussianBlur(am, (0, 0), 5.0)
    img += (glow[..., None] * _hx('#1ec880') * 0.60).astype(F32)
    img += (am[..., None] * _hx('#78ffd0') * 0.80).astype(F32)
    masters = [_neuron_master(360, seed + 3 + k) for k in range(3)]
    angs = tuple(range(0, 360, 30))
    sm = _trim(sum([_rot_tiles(m, (150, 190), angs) for m in masters], []))
    fx, fy, fti = _scatter(n, 12, seed + 4, 6, 12, jit=0.5)
    kp = r.random(len(fx)) < 0.45
    H.splat_rgba(img, sm, fti[kp], fx[kp], fy[kp], amp=np.full(int(kp.sum()), 0.85, F32))
    tiles = _trim(sum([_rot_tiles(m, (230, 280, 330), angs) for m in masters], []))
    ex, ey, ti = _scatter(n, 7, seed + 5, 9, 12, jit=0.45)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_gray_tint(r, len(ex), 0.85, 1.1))
    img = _fine(img, seed + 64, 0.09)
    Ln = H.sstep(0.05, 0.75, H.lum(img))
    M, R, CC = _curves(Ln, (120.0, 255.0), (120.0, 0.0), (44.0, 16.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 106 blood smear
# =========================================================================
def _rbc_master(S=96, ecc=1.0):
    M = _mk(S)
    gx, gy = H.tile_xy(S)
    ax = 0.47 * S
    rr = np.hypot(gx / ax, gy / (ax * ecc)).astype(F32)
    disc = H.sstep(1.03, 0.97, rr)
    col = H.ramp(np.clip(rr, 0, 1), [(0.0, '#f4b0ac'), (0.30, '#ea8c8a'), (0.50, '#d84444'), (0.82, '#c02a32'), (0.95, '#8a121e'), (1.0, '#6a0a16')]).astype(F32)
    light = 0.86 + 0.22 * np.clip(-(gx * 0.55 + gy * 0.83) / ax, -1, 1)
    _put(M, np.clip(col * light[..., None], 0, 1), disc)
    return M


def _wbc_master(S=200, seed=1):
    r = H.rng(seed)
    M = _mk(S)
    c = S / 2.0
    gx, gy = H.tile_xy(S)
    rr = np.hypot(gx, gy) / (0.46 * S)
    g = _z(H.noise(S, max(2, S // 6), seed + 3))
    col = H.ramp(np.clip(rr, 0, 1).astype(F32), [(0.0, '#d8c0e4'), (0.7, '#c8aedc'), (0.93, '#a088c0'), (1.0, '#7a64a0')]).astype(F32)
    col = col * (1.0 + 0.10 * g)[..., None]
    _put(M, np.clip(col, 0, 1), H.sstep(1.03, 0.97, rr))
    for k in range(34):
        a, d = r.uniform(0, 6.283), np.sqrt(r.random()) * 0.8
        _blob(M, c + 0.46 * S * d * np.cos(a), c + 0.46 * S * d * np.sin(a), 2.4, 2.4, 0.0, _hx('#b05aa0'), _hx('#e8a0d8'), None, 0.0, 1.0)
    a0 = r.uniform(0, 6.283)
    pts = [(c + 0.20 * S * np.cos(a0 + 2.1 * k), c + 0.20 * S * np.sin(a0 + 2.1 * k)) for k in range(3)]
    _strokes(M, [np.array([pts[0], pts[1], pts[2]])], 9, _hx('#3a1a78'))
    for (px_, py_) in pts:
        _blob(M, px_, py_, 0.115 * S, 0.095 * S, a0, _hx('#241060'), _hx('#5a34a8'), _hx('#a888e8'), 0.55, 1.2)
    return M


@_f("wx_blood_smear", "Blood Smear",
    "A crowded blood smear: pale-centred red cells packed edge to edge, a few lobed purple white cells and dotted platelets between.")
def blood_smear(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 106 Blood Smear: biconcave RBC disc masters (radial ramp with central pallor, 3 sizes x 8 rotations, 2 eccentricities) packed on a g=40 stagger grid over pale pink plasma, ~20 three-lobed purple WBC stamps, 300 purple platelets; SAT
    n = N
    r = H.rng(seed)
    t = 0.5 + 0.16 * _z(H.fbm(n, seed + 1, cells=(6, 14, 34))) + 0.05 * _z(H.noise(n, 150, seed + 2))
    img = H.ramp(np.clip(t, 0, 1), [(0.0, '#d6a0aa'), (0.5, '#e8bcc2'), (1.0, '#f4d6d8')]).astype(F32)
    angs = tuple(range(0, 360, 45))
    tiles = _trim(sum([_rot_tiles(_rbc_master(96, e), (54, 62, 70), angs) for e in (1.0, 0.86)], []))
    ex, ey, ti = _scatter(n, 40, seed + 4, 6, 8, jit=0.42)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_gray_tint(r, len(ex), 0.88, 1.10))
    wb = _trim(_rot_tiles(_wbc_master(200, seed + 6), (125, 150), (0, 90, 180, 270)))
    wx_, wy_, wti = _scatter(n, 5, seed + 7, 2, 4, jit=0.5, ext=0)
    kp = r.random(len(wx_)) < 0.7
    H.splat_rgba(img, wb, wti[kp], wx_[kp], wy_[kp])
    K = 320
    pm = _dotmask(n, r.random(K) * n, r.random(K) * n, r.uniform(3.5, 7.0, K))
    img = img * (1.0 - 0.9 * pm)[..., None] + (_hx('#9a58aa') * (0.9 * pm)[..., None]).astype(F32)
    img = _fine(img, seed + 65, 0.07)
    Ln = H.sstep(0.05, 0.85, H.lum(img))
    M, R, CC = _curves(Ln, (125.0, 186.0), (100.0, 72.0), (56.0, 28.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 107 foraminifera
# =========================================================================
def _foram_master(S, seed, g, k, pal, sweep=1.6):
    r = H.rng(seed)
    M = _mk(S)
    gx, gy = H.tile_xy(S)
    R = 0.46 * S
    rr = np.hypot(gx, gy) + F32(1e-3)
    th = np.arctan2(gy, gx)
    Rw = R * (1 + 0.025 * np.sin(2 * th + r.uniform(0, 6)) + 0.018 * np.sin(5 * th + r.uniform(0, 6)))
    b = np.log(g) / (2 * np.pi)
    lr = np.log(np.maximum(rr, 4.0) / 5.0)
    s1 = th - lr / b
    s2 = th + lr / (b * sweep)
    f1 = (s1 / (2 * np.pi)) % 1.0
    f2 = (s2 * k / (2 * np.pi)) % 1.0
    h = (np.sin(np.pi * f1) ** 0.55) * (np.sin(np.pi * f2) ** 0.55) * (0.55 + 0.45 * np.clip(rr / Rw, 0, 1))
    dif, spc = H.shade(h.astype(F32), 26.0)
    idx = np.floor(s2 * k / (2 * np.pi)).astype(np.int64) % k
    hv = H.hash01(idx, seed)
    base = H.ramp((0.10 + 0.80 * hv).astype(F32), pal).astype(F32)
    col = base * (0.30 + 0.85 * dif)[..., None] + spc[..., None] * 0.30
    dw = np.minimum(f1, 1 - f1) * 2 * np.pi * b * rr
    ds = np.minimum(f2, 1 - f2) * (2 * np.pi / k) * rr * 0.8
    line = np.maximum(H.sstep(3.4, 1.5, dw), H.sstep(3.6, 1.6, ds))
    col = col * (1.0 - 0.80 * line)[..., None]
    pr_ = H.sstep(7.5, 5.5, rr)[..., None]
    col = col * (1.0 - pr_) + _hx('#fff4d8') * pr_ * 0.9
    col = col + _hx('#fff2d0') * (np.exp(-((rr - Rw + 2.0) / 2.4) ** 2) * 0.7)[..., None]
    _put(M, _hx('#2a1a08'), np.exp(-((rr - Rw - 5.0) / 7.0) ** 2) * 0.40 * (rr > Rw))
    _put(M, np.clip(col, 0, 1).astype(F32), H.sstep(Rw + 1.2, Rw - 1.2, rr))
    return M


@_f("wx_foraminifera", "Foraminifera Sand",
    "Tiny spiral-chambered foraminifera shells, curved sutures sweeping across each whorl, strewn thick among tan sand grains.")
def foraminifera(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 107 Foraminifera Sand: log-spiral planispiral shell masters (wall coordinate theta-ln r/b, backswept suture coordinate, dome heightfield lit by shade(), per-chamber tint, keel ring, proloculus; 2 shell types x 3 sizes x 8 rotations) over 28k AA sand grains in cream/tan/brown/quartz; SAT
    n = N
    r = H.rng(seed)
    t = 0.45 + 0.14 * _z(H.fbm(n, seed + 1, cells=(6, 14, 34)))
    img = H.ramp(np.clip(t, 0, 1), [(0.0, '#7a5c36'), (0.5, '#a88858'), (1.0, '#c8aa78')]).astype(F32)
    pal = ['#e0c890', '#c8a468', '#a88048', '#d8b078', '#8c6a3c', '#e8d8b0', '#b09878', '#f0e4c4', '#6c5230', '#c0b8a8']
    cols = np.array([[int(h_[i:i + 2], 16) for i in (1, 3, 5)] for h_ in pal], np.uint8)
    cv_ = np.zeros((n, n, 3), np.uint8)
    K = 14000
    gxs, gys = r.random(K) * n, r.random(K) * n
    grs = r.uniform(1.5, 5.2, K)
    gci = r.integers(0, len(cols), K)
    for i in range(K):
        c3 = tuple(int(v) for v in cols[gci[i]])
        cx_, cy_, rad = int(gxs[i] * 4), int(gys[i] * 4), int(grs[i] * 4)
        cv2.circle(cv_, (cx_, cy_), rad, c3, -1, cv2.LINE_AA, 2)
        c4 = tuple(min(255, int(v * 1.25 + 14)) for v in cols[gci[i]])
        cv2.circle(cv_, (cx_ - rad // 4, cy_ - rad // 4), max(1, rad // 2), c4, -1, cv2.LINE_AA, 2)
    gm = np.zeros((n, n), np.uint8)
    gm = (cv_.max(axis=2) > 0).astype(F32)
    gm = cv2.GaussianBlur(gm, (0, 0), 0.6)
    img = img * (1.0 - gm)[..., None] + (cv_.astype(F32) / 255.0) * gm[..., None]
    pal1 = [(0.0, '#8a5e2c'), (0.5, '#e0bc7a'), (1.0, '#fbeabc')]
    pal2 = [(0.0, '#8a6a44'), (0.5, '#e8d2a8'), (1.0, '#fff4dc')]
    angs = tuple(range(0, 360, 45))
    ma = _foram_master(260, seed + 3, 3.4, 8, pal1, 5.0)
    mb = _foram_master(260, seed + 4, 2.7, 11, pal2, 7.0)
    sm = _trim(_rot_tiles(ma, (70, 90), angs) + _rot_tiles(mb, (70, 90), angs))
    fx, fy, fti = _scatter(n, 22, seed + 5, 4, 8, jit=0.5)
    kp = r.random(len(fx)) < 0.50
    H.splat_rgba(img, sm, fti[kp], fx[kp], fy[kp], amp=np.full(int(kp.sum()), 0.95, F32))
    tiles = _trim(_rot_tiles(ma, (120, 150, 185), angs) + _rot_tiles(mb, (120, 150, 185), angs))
    ex, ey, ti = _scatter(n, 11, seed + 6, 6, 8, jit=0.42)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_gray_tint(r, len(ex), 0.92, 1.08))
    img = _fine(img, seed + 66, 0.08)
    Ln = H.sstep(0.08, 0.88, H.lum(img))
    M, R, CC = _curves(Ln, (100.0, 168.0), (122.0, 68.0), (70.0, 32.0))
    return _out(np.clip(img, 0, 1), M, R, CC)



# =========================================================================
# 108 euglena
# =========================================================================
def _euglena_master(S=170, seed=1):
    r = H.rng(seed)
    M = _mk(S)
    c = S / 2.0
    gx, gy = H.tile_xy(S)
    L = 0.66 * S
    W = 0.205 * S
    u = gx / (L * 0.5)
    wprof = np.clip(1 - u * u, 0, 1) ** np.where(u < 0, 0.45, 1.05)
    bend = 0.045 * S * np.sin(u * 2.0 + r.uniform(0, 1.0))
    e = wprof * (W * 0.5) - np.abs(gy - bend)
    disc = np.clip(e / 1.2 + 0.5, 0, 1)
    d = np.clip(e / (W * 0.5), 0, 1)
    col = H.ramp(np.clip(d * 1.2, 0, 1).astype(F32), [(0.0, '#0e5a20'), (0.45, '#38b838'), (1.0, '#a8f070')]).astype(F32)
    light = 0.82 + 0.28 * np.clip(-(gy - bend) / (W * 0.5), -1, 1)
    _put(M, np.clip(col * light[..., None], 0, 1), disc)
    for k in range(22):
        xx = r.uniform(-0.82, 0.82) * L * 0.5
        wk = (1 - (xx / (L * 0.5)) ** 2) ** (0.45 if xx < 0 else 1.05) * W * 0.5
        yy = r.uniform(-0.62, 0.62) * wk + 0.045 * S * np.sin(xx / (L * 0.5) * 2.0)
        _blob(M, c + xx, c + yy + 0.0, r.uniform(2.6, 3.8), r.uniform(1.8, 2.6), r.uniform(0, 3.14), _hx('#0a4a14'), _hx('#2a9a30'), None, 0.0, 1.0)
    for sg in (-1, 1):
        _blob(M, c + 0.10 * S, c + sg * 0.012 * S + 0.045 * S * np.sin(0.4), 6.5, 3.0, 0.0, _hx('#bfe8b0'), _hx('#f4fff0'), None, 0.0, 1.0)
    fb = -0.39 * S
    _blob(M, c + fb * 0.62, c + 0.045 * S * np.sin(-0.3) - 3.5, 4.6, 4.6, 0.0, _hx('#a01010'), _hx('#ff3a30'), _hx('#ffd0c0'), 0.6, 1.0)
    tt = np.linspace(0, 1, 14)
    fl = [np.stack([c + fb + 2 - tt * 0.15 * S, c + 0.045 * S * np.sin(-1.2) + 0.035 * S * np.sin(tt * 7.0 + r.uniform(0, 2)) * tt], 1)]
    _strokes(M, fl, 2, _hx('#d4ffc0'))
    return M


@_f("wx_euglena_streaks", "Euglena Bloom",
    "A green bloom of spindle-shaped euglena, each with a flickering flagellum and a red eye-spot, streaming together in the current.")
def euglena_streaks(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 108 Euglena Bloom: curved spindle masters (blunt front, pointed tail, chloroplast granules, paramylon rods, red eye-spot, flagellum) quantised to 24 headings sampled from a curl flow field at each cell, 3 sizes on a jittered grid; LIC water-streak ground; FLK (pearl satin, 1 px metal flakes in the spec)
    n = N
    r = H.rng(seed)
    u, v = H.curl_field(512, seed + 1, cells=(2, 4, 8), gain=0.6)
    tex = _z(H.noise(512, 190, seed + 2)) + 0.6 * _z(H.noise(512, 90, seed + 3))
    st = H.lic(tex.astype(F32), u, v, length=16)
    st = cv2.resize(_z(st), (n, n), interpolation=cv2.INTER_CUBIC)
    t = 0.45 + 0.16 * st + 0.06 * _z(H.fbm(n, seed + 4, cells=(5, 12, 28)))
    img = H.ramp(np.clip(t, 0, 1), [(0.0, '#03120a'), (0.5, '#0a2a14'), (1.0, '#164a22')]).astype(F32)
    mst = _euglena_master(170, seed + 5)
    tiles = _trim(_rot_tiles(mst, (74, 92, 112), tuple(range(0, 360, 15))))
    ex, ey, _ = _scatter(n, 44, seed + 6, 1, 1, jit=0.55)
    kp = r.random(len(ex)) < 0.86
    ex, ey = ex[kp], ey[kp]
    fu = H.sample(u, ex / 4.0, ey / 4.0)
    fv = H.sample(v, ex / 4.0, ey / 4.0)
    ang = -np.degrees(np.arctan2(fv, fu)) + r.normal(0, 14.0, len(ex)) + np.where(r.random(len(ex)) < 0.5, 180.0, 0.0)
    ai = np.round((ang % 360.0) / 15.0).astype(np.int64) % 24
    si = r.integers(0, 3, len(ex))
    ti = si * 24 + ai
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_gray_tint(r, len(ex), 0.88, 1.10))
    img = _fine(img, seed + 67, 0.08)
    Ln = H.sstep(0.05, 0.75, H.lum(img))
    M, R, CC = _curves(Ln, (80.0, 150.0), (118.0, 58.0), (44.0, 16.0))
    fk = H.flake_mask(n, 0.006, seed + 9)
    M = np.where(fk, 255.0, M).astype(F32)
    R = np.where(fk, 0.0, R).astype(F32)
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 109 mitosis
# =========================================================================
def _chromo(M, pts, ln, wd, r, hi=True):
    polys = []
    for (x, y) in pts:
        a = r.uniform(0, 3.1416)
        polys.append(np.array([[x - ln * 0.5 * np.cos(a), y - ln * 0.5 * np.sin(a)], [x + ln * 0.5 * np.cos(a), y + ln * 0.5 * np.sin(a)]]))
    _strokes(M, polys, wd + 3, _hx('#2238b8'))
    _strokes(M, polys, wd + 1, _hx('#4a76ff'))
    if hi:
        _strokes(M, polys, max(2, wd // 3), _hx('#8ca8ff'))


def _centro(M, x, y, rays, r, rad=7.0, reach=34):
    pl = []
    for k in range(rays):
        a = r.uniform(0, 6.283)
        pl.append(np.array([[x, y], [x + reach * r.uniform(0.6, 1.0) * np.cos(a), y + reach * r.uniform(0.6, 1.0) * np.sin(a)]]))
    _strokes(M, pl, 2, _hx('#46e87a'))
    _blob(M, x, y, rad, rad, 0.0, _hx('#a01010'), _hx('#ff3a30'), _hx('#ffe0d0'), 0.7, 1.0)


def _mitosis_master(S, kind, seed):
    r = H.rng(seed)
    M = _mk(S)
    c = S / 2.0
    cy = c
    if kind == 0:   # interphase
        _blob(M, c, c, 98, 94, 0.0, _hx('#0c4a22'), _hx('#1a7a38'), _hx('#6aff90'), 0.10, 1.6)
        _blob(M, c, c, 54, 50, 0.0, _hx('#1a2c8a'), _hx('#3c64e8'), _hx('#a0b8ff'), 0.45, 1.5)
        for k in range(2):
            _blob(M, c + r.uniform(-18, 18), c + r.uniform(-18, 18), 8, 8, 0.0, _hx('#2a40b0'), _hx('#c4d4ff'), None, 0.0, 1.0)
        for k in range(26):
            a, d = r.uniform(0, 6.283), np.sqrt(r.random()) * 40
            _blob(M, c + d * np.cos(a), c + d * np.sin(a), 3.0, 3.0, 0.0, _hx('#3a58d8'), _hx('#9ab4ff'), None, 0.0, 1.0)
        _centro(M, c + 66, c - 52, 8, r, 6.0, 26)
    elif kind == 1:   # prophase
        _blob(M, c, c, 98, 94, 0.0, _hx('#0c4a22'), _hx('#1a7a38'), _hx('#6aff90'), 0.10, 1.6)
        _blob(M, c, c, 58, 55, 0.0, _hx('#12206a'), _hx('#1c3498'), None, 0.0, 1.2)
        polys = []
        for k in range(22):
            a, d = r.uniform(0, 6.283), np.sqrt(r.random()) * 36
            x0, y0 = c + d * np.cos(a), c + d * np.sin(a)
            pp = [(x0, y0)]
            th = r.uniform(0, 6.283)
            for i in range(5):
                th += r.normal(0, 0.55)
                pp.append((pp[-1][0] + 7.5 * np.cos(th), pp[-1][1] + 7.5 * np.sin(th)))
            polys.append(np.array(pp))
        _strokes(M, polys, 6, _hx('#2a46c8'))
        _strokes(M, polys, 4, _hx('#5a86ff'))
        _strokes(M, polys, 2, _hx('#b4ccff'))
        _centro(M, c - 70, c + 20, 10, r, 7.0, 30)
        _centro(M, c + 70, c - 20, 10, r, 7.0, 30)
    elif kind == 2:   # metaphase
        _blob(M, c, c, 104, 88, 0.0, _hx('#0c4a22'), _hx('#1a7a38'), _hx('#6aff90'), 0.10, 1.6)
        fib = []
        for sg in (-1, 1):
            for k in range(15):
                fib.append(np.array([[c + sg * 84, c], [c + r.normal(0, 4), c + r.uniform(-46, 46)]]))
        _strokes(M, fib, 2, _hx('#1f9a48'))
        _strokes(M, fib[::4], 2, _hx('#46e87a'))
        pts = [(c + r.normal(0, 3.5), c - 46 + 92 * (k + 0.5) / 22 + r.normal(0, 1.5)) for k in range(22)]
        _chromo(M, pts, 15, 6, r)
        _centro(M, c - 86, c, 12, r, 7.5, 18)
        _centro(M, c + 86, c, 12, r, 7.5, 18)
    elif kind == 3:   # anaphase
        _blob(M, c, c, 112, 72, 0.0, _hx('#0c4a22'), _hx('#1a7a38'), _hx('#6aff90'), 0.10, 1.6)
        fib = []
        for sg in (-1, 1):
            for k in range(13):
                fib.append(np.array([[c + sg * 96, c], [c + sg * 44, c + r.uniform(-34, 34)]]))
        for k in range(6):
            fib.append(np.array([[c - 42, c + r.uniform(-30, 30)], [c + 42, c + r.uniform(-30, 30)]]))
        _strokes(M, fib, 2, _hx('#1f9a48'))
        for sg in (-1, 1):
            pts = [(c + sg * 44 + r.normal(0, 2.5), c - 34 + 68 * (k + 0.5) / 18 + r.normal(0, 1.5)) for k in range(18)]
            _chromo(M, pts, 13, 6, r)
        _centro(M, c - 98, c, 10, r, 7.0, 16)
        _centro(M, c + 98, c, 10, r, 7.0, 16)
    else:   # telophase
        for sg in (-1, 1):
            _blob(M, c + sg * 52, c, 62, 66, 0.0, _hx('#0c4a22'), _hx('#1a7a38'), _hx('#6aff90'), 0.10, 1.6)
        _strokes(M, [np.array([[c, c - 36], [c, c + 36]])], 6, _hx('#9cffb4'))
        for sg in (-1, 1):
            _blob(M, c + sg * 66, c, 25, 27, 0.0, _hx('#1c2c98'), _hx('#4a74f0'), _hx('#b8ccff'), 0.5, 1.2)
            _centro(M, c + sg * 22, c + r.uniform(-18, 18), 8, r, 6.0, 20)
    return M


@_f("wx_cell_division", "Mitosis Field",
    "Fluorescent cells caught mid-division: blue chromosomes in bars and threads, green spindle fibres, red centrosomes, on black.")
def cell_division(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 109 Mitosis Field: 5 stage masters (interphase nucleus, prophase threads, metaphase plate with spindle, anaphase twin plates, telophase pinch), 3 sizes x 12 rotations on a g=9 grid over smaller fillers, dark green fluorescence haze; TWO (matte cells, metallic chromosomes/fibres/centrosomes)
    n = N
    r = H.rng(seed)
    t = 0.40 + 0.18 * _z(H.fbm(n, seed + 1, cells=(4, 9, 22, 48))) + 0.04 * _z(H.noise(n, 160, seed + 2))
    img = H.ramp(np.clip(t, 0, 1), [(0.0, '#03100a'), (0.5, '#072a16'), (1.0, '#0e4a26')]).astype(F32)
    angs = tuple(range(0, 360, 30))
    ms = [_mitosis_master(240, k, seed + 3 + k) for k in range(5)]
    sm = _trim(sum([_rot_tiles(m, (90, 112), angs) for m in ms], []))
    fx, fy, fti = _scatter(n, 22, seed + 4, 10, 12, jit=0.5)
    kp = r.random(len(fx)) < 0.60
    H.splat_rgba(img, sm, fti[kp], fx[kp], fy[kp], amp=np.full(int(kp.sum()), 0.85, F32))
    tiles = _trim(sum([_rot_tiles(m, (125, 155, 190), angs) for m in ms], []))
    ex, ey, ti = _scatter(n, 12, seed + 5, 15, 12, jit=0.45)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_gray_tint(r, len(ex), 0.9, 1.1))
    img = _fine(img, seed + 68, 0.08)
    Ls = H.sstep(0.36, 0.52, H.lum(img))
    M, R, CC = _curves(Ls, (10.0, 240.0), (228.0, 26.0), (250.0, 16.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 110 biofilm towers
# =========================================================================
@_f("wx_biofilm_towers", "Biofilm Towers",
    "Amber biofilm towers seen from above, mushroom-capped and merging in chains, with dark wet channels winding between them.")
def biofilm_towers(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 110 Biofilm Towers: blurred-impulse metaball field (sigma 12, spacing 62, amplitude 1.4-2.2), dome height sqrt(ln(f/thr)) lit by shade(), growth-ring modulation cos(14 ln f), dark cap-edge shadow rim, brown slime channel floor with pits, cream bead flecks; WET (channels mirror-wet, towers satin)
    n = N
    sig = 20.0
    pts = H.jitter_pts(n, 96, seed + 11, jit=0.40)
    rr = H.rng(seed + 12)
    K = len(pts)
    am = rr.uniform(1.6, 2.4, K).astype(F32)
    cv = np.zeros((n, n), F32)
    H.points(cv, pts[:, 0], pts[:, 1], am, mode="add")
    pm = rr.random(K) < 0.18
    pa = rr.uniform(0, 6.2832, K)
    pd = rr.uniform(40, 50, K)
    H.points(cv, (pts[:, 0] + np.cos(pa) * pd)[pm], (pts[:, 1] + np.sin(pa) * pd)[pm], am[pm] * 0.8, mode="add")
    f = (cv2.GaussianBlur(cv, (0, 0), sig) * F32(2 * np.pi * sig * sig)).astype(F32)
    thr = 0.45
    hh = np.clip(np.log(np.maximum(f, 1e-4) / thr), 0, None).astype(F32)
    h = np.sqrt(hh).astype(F32)
    ring = np.cos(hh * 9.0).astype(F32)
    lob = np.stack([(pts[:, 0] + np.cos(pa) * pd)[pm], (pts[:, 1] + np.sin(pa) * pd)[pm]], 1)
    _, lab, sx, sy = H.voronoi(n, np.concatenate([pts, lob]).astype(F32))
    X, Y = H.xy(n)
    th = np.arctan2(Y - sy[lab - 1], X - sx[lab - 1])
    phs = rr.uniform(0, 6.28, K + len(lob) + 8).astype(F32)
    wr = (np.cos(9.0 * th + phs[lab - 1]) * H.sstep(0.15, 0.6, h)).astype(F32)
    dif, spc = H.shade((h + 0.045 * ring + 0.07 * wr).astype(F32), 24.0, shin=36.0)
    base = H.ramp(np.clip(0.12 + 0.62 * h / 1.5, 0, 1).astype(F32), [(0.0, '#6a3a12'), (0.5, '#c07a24'), (1.0, '#f4dca4')]).astype(F32)
    col = base * (0.34 + 0.86 * dif)[..., None] * (1.0 - 0.14 * (0.5 - 0.5 * ring))[..., None] + spc[..., None] * 0.30
    rim = np.exp(-((f - thr) / 0.07) ** 2).astype(F32)
    col = col * (1.0 - 0.55 * rim)[..., None]
    mask = H.sstep(thr - 0.035, thr + 0.035, f)
    tch = 0.5 + 0.22 * _z(H.noise(n, 150, seed + 3)) + 0.12 * _z(H.noise(n, 220, seed + 4))
    chan = H.ramp(np.clip(tch, 0, 1), [(0.0, '#160a02'), (0.5, '#2e1808'), (1.0, '#4a2a10')]).astype(F32)
    img = chan * (1.0 - mask)[..., None] + col * mask[..., None]
    img += (H.flake_mask(n, 0.004, seed + 7)[..., None] * _hx('#f8e8c0') * 0.42 * mask[..., None]).astype(F32)
    img = _fine(img, seed + 69, 0.10)
    Ln = H.sstep(0.04, 0.80, H.lum(img))
    M, R, CC = _curves(Ln, (10.0, 120.0), (4.0, 120.0), (16.0, 70.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(np.clip(img, 0, 1), M, R, CC)
