# -*- coding: utf-8 -*-
"""BLOOM chapter (wx_ 71-90): one plant per finish.

[S20 2026-10-12 owner: Fractured Wilds rebuild] one function per finish; each draws its OWN plant
(stamp masters / strokes / fields) and its OWN spec story. Only plumbing comes from helpers.
Stamp masters are premultiplied RGBA tiles built with the small painter kit below (_blob, _strokes, _put).
"""
from __future__ import annotations

import numpy as np
import cv2

from . import helpers as H
from .morpho import _z, _curves, _out, _rot_tiles, _aniso, _strands, _scalelat

F32 = np.float32
N = H.N
_hx = H.hexrgb

FINISHES = []


def _f(fid, name, desc):
    def deco(fn):
        FINISHES.append((fid, name, desc, fn))
        return fn
    return deco


# ------------------------------------------------------------------ stamp painter kit
def _mk(S, S2=None):
    return np.zeros((S2 or S, S, 4), F32)


def _put(M, rgb, a):
    a = np.clip(a, 0, 1).astype(F32)
    M[..., :3] = M[..., :3] * (1 - a[..., None]) + np.asarray(rgb, F32) * a[..., None]
    M[..., 3] = M[..., 3] * (1 - a) + a


def _putp(M, x0, y0, rgb, a):
    h, w = a.shape
    ys0, xs0 = max(y0, 0), max(x0, 0)
    ye, xe = min(y0 + h, M.shape[0]), min(x0 + w, M.shape[1])
    if ye <= ys0 or xe <= xs0:
        return
    a_ = np.clip(a[ys0 - y0:ye - y0, xs0 - x0:xe - x0], 0, 1)[..., None]
    c_ = rgb[ys0 - y0:ye - y0, xs0 - x0:xe - x0]
    sub = M[ys0:ye, xs0:xe]
    sub[..., :3] = sub[..., :3] * (1 - a_) + c_ * a_
    sub[..., 3:4] = sub[..., 3:4] * (1 - a_) + a_


def _blob(M, cx, cy, ax, ay, ang, c_edge, c_mid, c_hi=None, hi=0.0, soft=1.2):
    """Shaded ellipse (semi-axes ax along rotated x, ay along rotated y) painted onto master M."""
    R = int(max(ax, ay) * 1.15) + 3
    x0, y0 = int(cx) - R, int(cy) - R
    gx = (np.arange(x0, x0 + 2 * R + 1, dtype=F32) - F32(cx))[None, :]
    gy = (np.arange(y0, y0 + 2 * R + 1, dtype=F32) - F32(cy))[:, None]
    ca, sa = np.cos(ang), np.sin(ang)
    u = (gx * ca + gy * sa) / ax
    v = (-gx * sa + gy * ca) / ay
    d = np.sqrt(u * u + v * v)
    a = np.clip((1.0 - d) * min(ax, ay) / soft + 0.5, 0, 1)
    hg = np.sqrt(np.clip(1 - d * d, 0, 1))
    light = 0.5 + 0.5 * np.clip(-(gx * 0.55 + gy * 0.83) / max(ax, ay), -1, 1)
    ce = np.asarray(c_edge, F32)
    cm = np.asarray(c_mid, F32)
    col = (ce[None, None, :] * (1 - hg[..., None]) + cm[None, None, :] * hg[..., None]) * (0.70 + 0.60 * light)[..., None]
    if c_hi is not None:
        col = col + np.asarray(c_hi, F32)[None, None, :] * (hi * hg ** 8 * light)[..., None]
    _putp(M, x0, y0, col.astype(F32), a)


def _strokes(M, polys, width, rgb, shift=2):
    m = np.zeros(M.shape[:2], np.uint8)
    sc = 1 << shift
    cv2.polylines(m, [np.round(np.asarray(p, np.float64) * sc).astype(np.int32).reshape(-1, 1, 2) for p in polys],
                  False, 255, int(width), cv2.LINE_AA, shift)
    _put(M, rgb, m.astype(F32) / 255.0)


def _scatter(n, g, seed, nsz, nang, jit=0.30, stagger=True, ext=1):
    r = H.rng(seed)
    gi, gj = np.meshgrid(np.arange(-ext, g + ext), np.arange(-ext, g + ext))
    sp = n / g
    ex = ((gi + 0.5 + r.uniform(-jit, jit, gi.shape) + (0.5 * (gj & 1) if stagger else 0.0)) * sp).ravel()
    ey = ((gj + 0.5 + r.uniform(-jit, jit, gi.shape)) * sp).ravel()
    ti = (r.integers(0, nsz, ex.size) * nang + r.integers(0, nang, ex.size))
    o = np.argsort(ey, kind="stable")
    return ex[o], ey[o], ti[o]


def _trim(tiles):
    """Crop each RGBA tile symmetrically about its centre to the alpha bounding box (splat speed)."""
    out = []
    for t in tiles:
        h, w = t.shape[:2]
        ys, xs = np.nonzero(t[..., 3] > 0.003)
        if len(ys) == 0:
            out.append(t)
            continue
        cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
        hy = int(np.ceil(max(cy - ys.min(), ys.max() - cy))) + 1
        hx = int(np.ceil(max(cx - xs.min(), xs.max() - cx))) + 1
        y0, y1 = max(0, int(cy) - hy), min(h, int(cy) + hy + 1)
        x0, x1 = max(0, int(cx) - hx), min(w, int(cx) + hx + 1)
        out.append(np.ascontiguousarray(t[y0:y1, x0:x1]))
    return out


def _tint(r, K, lo=0.86, hi=1.10):
    t = r.uniform(lo, hi, (K, 3)).astype(F32)
    return t


def _fine(img, seed, amp, cells=(130, 200)):
    """multiplicative band-limited (10-16 px) micro-texture over the composite"""
    n = img.shape[0]
    t = sum(_z(H.noise(n, c, seed + 31 * k)) for k, c in enumerate(cells)) / np.sqrt(len(cells))
    return (img * (1.0 + amp * t)[..., None]).astype(F32)


def _comp(n, ground, tiles, ex, ey, ti, tint=None, amp=None, flip=None):
    img = np.ascontiguousarray(ground, F32).copy()
    H.splat_rgba(img, tiles, ti, ex, ey, tint=tint, amp=amp, flip=flip)
    return img


def _polar(S):
    gx, gy = H.tile_xy(S)
    x = gx / (S * 0.5)
    y = gy / (S * 0.5)
    return x, y, np.hypot(x, y), np.arctan2(y, x)


# =========================================================================
# 71 peony
# =========================================================================
def _peony_master(S=360):
    x, y, rr, th = _polar(S)
    M = _mk(S)
    layers = [(0.97, 7, 0.0), (0.84, 6, 0.5), (0.71, 6, 1.1), (0.58, 5, 0.3), (0.45, 5, 1.0), (0.33, 4, 0.6), (0.21, 4, 1.4), (0.11, 3, 0.2)]
    for k, (R, m, ph) in enumerate(layers):
        tri = 0.5 + 0.5 * np.cos(m * th + ph)
        rb = R * (0.78 + 0.22 * tri ** 0.6)
        rb = rb * (1.0 + 0.040 * np.sin(23.0 * th + 2.0 * k) + 0.022 * np.sin(51.0 * th + 5.0 * k))
        a = H.sstep(rb + 0.010, rb - 0.010, rr)
        t = np.clip((rb - rr) / (0.34 * R), 0, 1)
        fold = 0.5 + 0.5 * np.cos(2.0 * m * th + 2.0 * ph + 11.0 * rr)
        edge = np.exp(-((rb - rr) / 0.030) ** 2)
        col = H.ramp(np.clip(t * 0.8 + 0.2 * k / 7.0, 0, 1), [(0.0, '#fff0f2'), (0.28, '#f6b8c8'), (0.62, '#dc7094'), (1.0, '#a8325c')])
        col = col * (0.78 + 0.22 * fold)[..., None] + edge[..., None] * 0.18
        _put(M, col.astype(F32), a)
    return M


@_f("wx_peony_ruffle", "Peony Ruffles",
    "Dense pink peony blooms of layered, frilled petal edges, crumpled like silk, in blush, rose and cream.")
def peony_ruffle(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 71 Peony Ruffles: 8-layer peony master (scalloped petal edge + 23/51-lobe frill + silk fold lines), 3 sizes x 6 rotations on a dense staggered grid, per-bloom tint; SAT silk
    n = N
    r = H.rng(seed)
    ground = H.ramp(np.clip(0.30 + 0.12 * _z(H.fbm(n, seed + 1, cells=(6, 12, 24))), 0, 1), [(0.0, '#2a0a1c'), (0.5, '#5a1832'), (1.0, '#8a3050')])
    tiles = _rot_tiles(_peony_master(), (150, 185, 230), (0, 60, 120, 180, 240, 300))
    ex, ey, ti = _scatter(n, 15, seed + 2, 3, 6)
    img = _comp(n, ground, tiles, ex, ey, ti, tint=_tint(r, len(ex), 0.86, 1.10))
    Ln = H.sstep(0.10, 0.92, H.lum(img))
    M, R, CC = _curves(Ln, (6.0, 70.0), (150.0, 64.0), (40.0, 24.0))
    return _out(img, M, R, CC)


# =========================================================================
# 72 sunflower
# =========================================================================
def _sunflower_master(S=380):
    x, y, rr, th = _polar(S)
    M = _mk(S)
    m = 34
    for ring, (ph0, scl) in enumerate(((0.5, 0.93), (0.0, 1.0))):
        f = (th * m / (2 * np.pi) + ph0) % 1.0
        tri = 1.0 - np.abs(2 * f - 1)
        rp = scl * (0.56 + 0.44 * tri ** 0.7)
        a = H.sstep(rp + 0.010, rp - 0.010, rr) * H.sstep(0.46, 0.52, rr)
        t = np.clip((rr - 0.5) / (rp - 0.5 + 1e-3), 0, 1)
        col = H.ramp(t, [(0.0, '#a85a08'), (0.45, '#f0a812'), (0.8, '#ffd228'), (1.0, '#fff070')])
        groove = np.exp(-((1.0 - tri) / 0.10) ** 2)
        col = col * (0.62 + 0.38 * tri ** 0.5)[..., None] * (1.0 - 0.18 * groove)[..., None]
        _put(M, col.astype(F32), a)
    _put(M, _hx('#3a2008'), H.sstep(0.625, 0.60, rr))
    Ns = 50
    c = 0.575 * (S * 0.5) / np.sqrt(Ns)
    for i in range(1, Ns + 1):
        rI = c * np.sqrt(i)
        tI = i * 2.39996323
        cx, cy = S * 0.5 + rI * np.cos(tI), S * 0.5 + rI * np.sin(tI)
        sr = 0.64 * c * (0.75 + 0.5 * np.sqrt(i / Ns))
        q = rI / (0.575 * S * 0.5)
        base = H.ramp(np.array([q], F32), [(0.0, '#2a160a'), (0.5, '#5a3818'), (0.85, '#8a5a22'), (1.0, '#b08030')])[0]
        _blob(M, cx, cy, sr, sr, 0.0, base * 0.45, base * 1.25, _hx('#ffd890'), 0.32, 1.0)
    return M


@_f("wx_sunflower_spiral", "Sunflower Seed Heads",
    "Many sunflower heads, each a dark seed disc packed in Fibonacci spirals inside a ring of golden petals.")
def sunflower_spiral(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 72 Sunflower Seed Heads: Vogel phyllotaxis master (120 shaded seeds, golden angle 137.5 deg) + double ring of 34 pointed petals, 3 sizes x 5 rotations, dense hex-ish grid over leaf green; FLK
    n = N
    r = H.rng(seed)
    ground = H.ramp(np.clip(0.38 + 0.07 * _z(H.fbm(n, seed + 1, cells=(8, 16, 32))) + 0.15 * _z(H.noise(n, 90, seed + 7)) + 0.14 * _z(H.noise(n, 170, seed + 8)), 0, 1), [(0.0, '#0e280c'), (0.5, '#24501c'), (1.0, '#4a8a2c')])
    tiles = _rot_tiles(_sunflower_master(), (130, 165, 205), (0, 11, 22, 33, 44))
    ex, ey, ti = _scatter(n, 12, seed + 2, 3, 5, jit=0.34)
    img = _fine(_comp(n, ground, tiles, ex, ey, ti, tint=_tint(r, len(ex), 0.90, 1.08)), seed + 43, 0.12)
    Ln = H.sstep(0.05, 0.85, H.lum(img))
    M, R, CC = _curves(Ln, (20.0, 150.0), (190.0, 50.0), (100.0, 16.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 73 lavender rows
# =========================================================================
def _lav_master(S=256, seed=5):
    r = H.rng(seed)
    M = _mk(S)
    _strokes(M, [np.array([[128, 252], [128, 18]], np.float64)], 3, _hx('#587a42'))
    nw = 12
    for k in range(nw):
        yk = 232.0 - k * 17.5
        wsz = 11.5 - 0.50 * k
        top = k / (nw - 1.0)
        cm = _hx('#6a40c0') * (1 - top) + _hx('#a88cf0') * top
        for side in (-1, 1):
            for j in range(2):
                cx = 128 + side * (4.5 + wsz * 0.50 + j * wsz * 0.62)
                cy = yk + r.uniform(-3, 3) + j * 3.0
                _blob(M, cx, cy, wsz * 0.60, wsz * 1.10, side * 0.35 + r.uniform(-0.15, 0.15), _hx('#2a1668'), cm, _hx('#eadcff'), 0.30, 1.0)
        _blob(M, 128, yk + 6, 4.0, 5.0, 0.0, _hx('#3a5a30'), _hx('#7a9a62'))
    _blob(M, 128, 18, 5.0, 8.0, 0.0, _hx('#3a2090'), _hx('#b8a0ff'), _hx('#ffffff'), 0.3, 1.0)
    return M


@_f("wx_lavender_rows", "Lavender Field Rows",
    "Wavy rows of tiny purple lavender bud spikes swaying together over sage green, row after row.")
def lavender_rows(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 73 Lavender Field Rows: 12-whorl spike master (24 shaded buds + stalk + calyx), ~2300 stamps along 22 sinusoidal rows (19 px spacing, 3 sizes, +-27 deg sway from row slope + noise), painter order; FLK
    n = N
    r = H.rng(seed)
    ground = H.ramp(np.clip(0.36 + 0.16 * _z(H.fbm(n, seed + 1, cells=(6, 14, 30))), 0, 1), [(0.0, '#2a3620'), (0.5, '#4a5c36'), (1.0, '#7a8c58')])
    sizes = (130, 165, 200)
    angs = (-27, -18, -9, 0, 9, 18, 27)
    tiles = _trim(_rot_tiles(_lav_master(), sizes, angs))
    exs, eys, tis = [], [], []
    rs = 100.0
    for j in range(-1, 23):
        yb = (j + 0.6) * rs
        lam = r.uniform(520, 900)
        A = r.uniform(24, 46)
        ph = r.uniform(0, 6.283)
        xs = np.arange(-30, n + 30, 19.0) + r.uniform(-4, 4, 1)
        arg = 2 * np.pi * xs / lam + ph
        ys = yb + A * np.sin(arg) + r.uniform(-6, 6, len(xs))
        slope = np.degrees(np.arctan(A * 2 * np.pi / lam * np.cos(arg)))
        ang = -0.55 * slope + r.normal(0, 9.0, len(xs))
        ai = np.clip(np.rint(ang / 9.0).astype(int) + 3, 0, 6)
        si = r.integers(0, 3, len(xs))
        sz = np.array(sizes)[si]
        exs.append(xs)
        eys.append(ys - 0.38 * sz)
        tis.append(si * 7 + ai)
    ex, ey, ti = np.concatenate(exs), np.concatenate(eys), np.concatenate(tis)
    o = np.argsort(ey + 0.38 * np.array(sizes)[ti // 7], kind="stable")
    img = _comp(n, ground, tiles, ex[o], ey[o], ti[o], tint=_tint(r, len(ex), 0.88, 1.10))
    Ln = H.sstep(0.05, 0.75, H.lum(img))
    M, R, CC = _curves(Ln, (40.0, 190.0), (110.0, 50.0), (160.0, 30.0))
    return _out(img, M, R, CC)


# =========================================================================
# 74 fern fronds
# =========================================================================
@_f("wx_fern_fronds", "Fern Fiddleheads",
    "Fractal green fern fronds with finely divided leaflets, with tightly curled fiddleheads unrolling between them.")
def fern_fronds(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 74 Fern Fiddleheads: 34 curved fronds (60-pt rachis, 28 tapering curved pinnae per side, 3 sub-pinnules per pinna) drawn as batched polylines + 16 log-spiral fiddleheads; litter ground; SAT
    n = N
    r = H.rng(seed)
    z1 = _z(H.fbm(n, seed + 1, cells=(6, 12, 24)))
    ground = H.ramp(np.clip(0.40 + 0.16 * z1, 0, 1), [(0.0, '#1a2a14'), (0.5, '#2e3e1e'), (1.0, '#4e4a26')])
    pin, pv, sub, sv, rach, rv = [], [], [], [], [], []
    for f in range(34):
        base = r.random(2) * n
        a0 = r.uniform(0, 2 * np.pi)
        Lf = r.uniform(420, 620)
        kappa = r.uniform(-1.6, 1.6)
        t = np.linspace(0, 1, 60)
        ang = a0 + kappa * t
        T = np.stack([np.cos(ang), np.sin(ang)], 1)
        ds = Lf / 59.0
        P = base + ds * (np.cumsum(T, axis=0) - T[0])
        Nn = np.stack([-T[:, 1], T[:, 0]], 1)
        v0 = r.uniform(150, 235)
        Lp = r.uniform(95, 150)
        rach.append(P)
        rv.append(80.0)
        for i in range(4, 59, 2):
            ti_ = i / 59.0
            L = Lp * (1 - ti_) ** 0.6 * (0.55 + 0.45 * min(1.0, ti_ * 8))
            vv = v0 * (0.72 + 0.28 * ti_)
            for side in (-1.0, 1.0):
                q = [P[i]]
                seg = L / 3.0
                dirs = []
                for j in range(3):
                    aj = np.radians(62.0 - 24.0 * j / 2.0) * side
                    ca, sa = np.cos(aj), np.sin(aj)
                    d = np.array([T[i, 0] * ca - T[i, 1] * sa, T[i, 0] * sa + T[i, 1] * ca])
                    dirs.append(d)
                    q.append(q[-1] + seg * d)
                pin.append(np.array(q))
                pv.append(vv)
                for j in (1, 2, 3):
                    dj = dirs[j - 1]
                    for s2 in (-1.0, 1.0):
                        a2 = np.radians(55.0) * s2
                        c2, s2_ = np.cos(a2), np.sin(a2)
                        d2 = np.array([dj[0] * c2 - dj[1] * s2_, dj[0] * s2_ + dj[1] * c2])
                        sub.append(np.stack([q[j], q[j] + 0.30 * L * d2]))
                        sv.append(vv * 0.95)
    cv = H.lines3(n, np.stack(pin).astype(F32), np.stack([pv, np.full(len(pv), 255.0), np.zeros(len(pv))], 1), 4)
    cv = H.lines3(n, np.stack(sub).astype(F32), np.stack([sv, np.full(len(sv), 255.0), np.zeros(len(sv))], 1), 2, canvas=cv)
    cv = H.lines3(n, np.stack(rach).astype(F32), np.stack([rv, np.full(len(rv), 255.0), np.zeros(len(rv))], 1), 6, canvas=cv)
    # fiddleheads
    fh, fv = [], []
    for k in range(16):
        c0 = r.random(2) * n
        R0 = r.uniform(50, 85)
        rot = r.uniform(0, 2 * np.pi)
        th = np.linspace(0, 3.6 * np.pi, 70)
        rad = R0 * np.exp(-0.19 * th)
        P = np.stack([c0[0] + rad * np.cos(th + rot), c0[1] + rad * np.sin(th + rot)], 1)
        tail = np.stack([P[0], P[0] + np.array([np.cos(rot + 0.6), np.sin(rot + 0.6)]) * r.uniform(90, 160)])
        fh.append(P)
        fv.append(170.0)
        fh.append(np.concatenate([tail, tail[-1:]]))
        fv.append(110.0)
    cv = H.lines3(n, np.stack([np.vstack([p, np.repeat(p[-1:], 70 - len(p), 0)]) if len(p) < 70 else p for p in fh]).astype(F32),
                  np.stack([fv, np.full(len(fv), 255.0), np.zeros(len(fv))], 1), 9, canvas=cv)
    V = H.u8f(cv[..., 0])
    m = H.u8f(cv[..., 1])
    col = H.ramp(np.clip(V * 1.25, 0, 1), [(0.0, '#102a14'), (0.45, '#2e7a24'), (0.75, '#68b838'), (1.0, '#c4e878')])
    rgb = ground * (1.0 - m)[..., None] + col * m[..., None]
    Ln = H.sstep(0.04, 0.7, H.lum(rgb))
    M, R, CC = _curves(Ln, (30.0, 100.0), (170.0, 40.0), (30.0, 16.0))
    return _out(rgb, M, R, CC)


# =========================================================================
# 75 cherry blossom
# =========================================================================
def _petal_alpha_col(x, y, a, lim0=0.97):
    ca, sa = np.cos(a), np.sin(a)
    u = x * ca + y * sa
    v = -x * sa + y * ca
    w = 0.40 * np.sin(np.pi * np.clip(u, 0, 1)) ** 0.7
    lim = lim0 - 0.15 * np.exp(-(v / 0.075) ** 2)
    al = H.sstep(w + 0.015, w - 0.015, np.abs(v)) * H.sstep(0.0, 0.04, u) * H.sstep(lim + 0.015, lim - 0.015, u)
    col = H.ramp(np.clip(u, 0, 1), [(0.0, '#d03a78'), (0.35, '#f08cb4'), (0.75, '#fbc4d8'), (1.0, '#fff0f4')])
    veins = 0.5 + 0.5 * np.cos(np.arctan2(v, u + 0.25) * 30.0)
    col = col * (0.70 + 0.30 * veins)[..., None] * (1.0 - 0.18 * np.exp(-(v / 0.05) ** 2))[..., None]
    return al, col.astype(F32)


def _blossom_master(S=240):
    x, y, rr, th = _polar(S)
    M = _mk(S)
    for k in range(5):
        al, col = _petal_alpha_col(x, y, k * 2 * np.pi / 5 - np.pi / 2)
        _put(M, col, al)
    r = H.rng(11)
    fil = []
    for i in range(20):
        a = r.uniform(0, 2 * np.pi)
        L = r.uniform(0.20, 0.38) * S * 0.5
        fil.append(np.array([[S / 2, S / 2], [S / 2 + L * np.cos(a), S / 2 + L * np.sin(a)]]))
    _blob(M, S / 2, S / 2, 0.075 * S, 0.075 * S, 0.0, _hx('#8a1a4a'), _hx('#d8508a'))
    _strokes(M, fil, 1, _hx('#f4c8d8'))
    for p in fil:
        _blob(M, p[1, 0], p[1, 1], 3.2, 3.2, 0.0, _hx('#b87810'), _hx('#ffd84a'))
    return M


def _petal_master(S=120):
    x, y, rr, th = _polar(S)
    M = _mk(S)
    al, col = _petal_alpha_col(x + 0.5, y, 0.0)
    _put(M, col, al)
    return M


@_f("wx_cherry_petals", "Cherry Blossom Drift",
    "Falling five-petal cherry blossoms and loose notched pink petals scattered over dark streaked bark.")
def cherry_petals(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 75 Cherry Blossom Drift: vertical bark (ridged anisotropic streaks + crack lines + horizontal lenticel dashes + lichen specks) + 5-petal notched blossom master (stamens, calyx) + loose petal master, random sizes/rotations, painter order; petals FLK, bark MAT
    n = N
    r = H.rng(seed)
    r1 = H.ridged(_z(_aniso(n, 80, 5, seed + 1, 0.0)))
    bk = 0.06 + 0.78 * np.clip(r1, 0, 1) ** 1.6 + 0.16 * _z(_aniso(n, 150, 9, seed + 2, 4.0))
    crack = H.zero_set_line(_z(_aniso(n, 60, 4, seed + 3, 0.0)), 2.2) + 0.7 * H.zero_set_line(_z(_aniso(n, 110, 7, seed + 9, 0.0)), 1.6)
    ground = H.ramp(np.clip(bk, 0, 1), [(0.0, '#150d0a'), (0.5, '#33241a'), (1.0, '#6a5440')]) * (1.0 - 0.75 * np.clip(crack, 0, 1))[..., None]
    lich = H.flake_mask(n, 0.0012, seed + 4)
    lent = H.sstep(0.9, 1.4, _z(_aniso(n, 18, 230, seed + 12, 0.0))) * (0.5 + 0.5 * H.sstep(-0.5, 0.8, _z(_aniso(n, 110, 5, seed + 1, 0.0))))
    ground = np.clip(ground + lich[..., None] * _hx('#8a9a7a') * 0.5 + lent[..., None] * _hx('#b89c80') * 0.75, 0, 1)
    bt = _rot_tiles(_blossom_master(), (120, 150, 185), (0, 45, 90, 135, 180, 225, 270, 315))
    pt = _rot_tiles(_petal_master(), (76, 96), (0, 40, 80, 120, 160, 200, 240, 280))
    ex1, ey1, ti1 = _scatter(n, 12, seed + 5, 3, 8, jit=0.45)
    keep = r.random(len(ex1)) < 0.60
    ex1, ey1, ti1 = ex1[keep], ey1[keep], ti1[keep]
    ex2, ey2, ti2 = _scatter(n, 30, seed + 6, 2, 8, jit=0.5)
    keep = r.random(len(ex2)) < 0.65
    ex2, ey2, ti2 = ex2[keep], ey2[keep], ti2[keep] + len(bt)
    ex, ey, ti = np.concatenate([ex1, ex2]), np.concatenate([ey1, ey2]), np.concatenate([ti1, ti2])
    o = np.argsort(ey, kind="stable")
    img = _comp(n, ground, bt + pt, ex[o], ey[o], ti[o], tint=_tint(r, len(ex), 0.90, 1.08), flip=r.integers(0, 4, len(ex))[o])
    img = np.clip(img * (1.0 + 0.10 * _z(H.noise(n, 140, seed + 10)) + 0.08 * _z(H.noise(n, 210, seed + 11)))[..., None], 0, 1).astype(F32)
    Ln = H.sstep(0.05, 0.9, H.lum(img))
    M, R, CC = _curves(Ln, (8.0, 130.0), (210.0, 60.0), (200.0, 20.0))
    return _out(img, M, R, CC)


# =========================================================================
# 76 moss carpet
# =========================================================================
def _moss_master(S=64):
    x, y, rr, th = _polar(S)
    m = 9
    tri = np.abs(np.cos(m * th / 2.0))
    rb = 0.30 + 0.70 * tri ** 2.2
    a = H.sstep(rb + 0.05, rb - 0.05, rr)
    t = np.clip(rr / np.maximum(rb, 0.2), 0, 1)
    col = H.ramp(t, [(0.0, '#0e3a14'), (0.5, '#2e8a26'), (1.0, '#9ad850')])
    vein = np.exp(-((1.0 - tri) / 0.14) ** 2)
    col = col * (0.82 + 0.35 * vein)[..., None]
    M = _mk(S)
    _put(M, col.astype(F32), a)
    return M


def _capsule_master(S=96):
    M = _mk(S)
    _strokes(M, [np.array([[48, 92], [47, 60], [49, 26]], np.float64)], 2, _hx('#8a5a28'))
    _blob(M, 49, 20, 6.0, 11.0, 0.18, _hx('#4a1c08'), _hx('#c8641c'), _hx('#ffc890'), 0.35, 1.0)
    _blob(M, 49, 10, 5.0, 4.0, 0.18, _hx('#6a5a20'), _hx('#c8b050'))
    return M


@_f("wx_moss_carpet", "Moss Carpet",
    "A dense carpet of tiny star-shaped moss shoots in every shade of green, spotted with rusty spore capsules on thin stalks.")
def moss_carpet(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 76 Moss Carpet: 9-leaflet star master (3 sizes x 6 rotations, ~4000 stamps on a jittered 32 px grid, per-shoot tint) + ~300 rust spore capsules on setae painted last; MAT
    n = N
    r = H.rng(seed)
    ground = np.broadcast_to(_hx('#0c1e0a'), (n, n, 3)).astype(F32)
    tiles = _rot_tiles(_moss_master(), (38, 48, 60), (0, 20, 40, 60, 80, 100))
    ex, ey, ti = _scatter(n, 64, seed + 2, 3, 6, jit=0.55)
    t = r.uniform(0.70, 1.25, (len(ex), 1)).astype(F32) * np.array([1.0, 1.0, 0.8], F32) * r.uniform(0.9, 1.1, (len(ex), 3)).astype(F32)
    reg = H.sample(_z(H.fbm(256, seed + 3, cells=(3, 6, 12))), ex / 8.0, ey / 8.0)
    t = t * (1.0 + 0.12 * reg)[:, None] * np.array([1.0, 1.0, 1.0], F32)
    img = _comp(n, ground, tiles, ex, ey, ti, tint=np.clip(t, 0.4, 1.6).astype(F32))
    ct = _rot_tiles(_capsule_master(), (66, 86), (-24, -12, 0, 12, 24))
    K = 300
    cx = r.random(K) * n
    cy = r.random(K) * n
    cti = r.integers(0, 2, K) * 5 + r.integers(0, 5, K)
    o = np.argsort(cy)
    H.splat_rgba(img, ct, cti[o], cx[o], cy[o], tint=_tint(r, K, 0.9, 1.1)[o])
    Ln = H.sstep(0.03, 0.55, H.lum(img))
    M, R, CC = _curves(Ln, (0.0, 40.0), (230.0, 150.0), (220.0, 120.0))
    return _out(img, M, R, CC)


# =========================================================================
# 77 dahlia
# =========================================================================
def _dahlia_master(S=300):
    x, y, rr, th = _polar(S)
    M = _mk(S)
    m = 16
    for k in range(8):
        R = 0.97 - 0.105 * k
        f = (th * m / (2 * np.pi) + 0.5 * (k & 1)) % 1.0
        tri = 1.0 - np.abs(2 * f - 1)
        rb = R * (0.60 + 0.40 * tri ** 1.1)
        a = H.sstep(rb + 0.012, rb - 0.012, rr)
        t = np.clip((rb - rr) / (0.45 * R), 0, 1)
        col = H.ramp(t, [(0.0, '#ff7ad0'), (0.35, '#e0309a'), (0.75, '#a01068'), (1.0, '#5a0a3c')])
        rib = np.exp(-((1.0 - tri) / 0.12) ** 2)
        col = col * (0.62 + 0.38 * tri ** 0.7)[..., None] * (1.0 + 0.25 * rib)[..., None]
        _put(M, col.astype(F32), a)
    _put(M, _hx('#ffd0e8'), H.sstep(0.06, 0.04, rr) * 0.8)
    return M


@_f("wx_dahlia_geometry", "Dahlia Geometry",
    "Small magenta and wine dahlia blooms tiled edge to edge, every petal a sharp lance in perfectly concentric rings.")
def dahlia_geometry(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 77 Dahlia Geometry: 8 concentric rings x 16 pointed lance petals (alternating half-step phase, rib highlight, tip->base magenta/wine ramp), 2 sizes x 4 rotations on a tight staggered grid; CAN candy
    n = N
    r = H.rng(seed)
    ground = np.broadcast_to(_hx('#2a0420'), (n, n, 3)).astype(F32)
    tiles = _rot_tiles(_dahlia_master(), (125, 160, 195), (0, 5, 10, 15))
    ex, ey, ti = _scatter(n, 15, seed + 2, 3, 4, jit=0.10)
    tint = np.clip(_tint(r, len(ex), 0.82, 1.12) * np.array([1.0, 0.95, 1.0], F32), 0, 1.3)
    img = _comp(n, ground, tiles, ex, ey, ti, tint=tint)
    Ln = H.sstep(0.04, 0.8, H.lum(img))
    M, R, CC = _curves(Ln, (92.0, 192.0), (84.0, 16.0), (46.0, 16.0))  # [S20 story-split] dahlia: satin-metal deck
    return _out(img, M, R, CC)


# =========================================================================
# 78 lily pads
# =========================================================================
def _pad_master(S=300):
    x, y, rr, th = _polar(S)
    rad = 0.47 * (1.0 + 0.02 * np.sin(7.0 * th))
    q = np.clip(rr / rad, 0, 1)
    a = H.sstep(rad + 0.010, rad - 0.010, rr) * H.sstep(0.14, 0.19, np.abs(th))
    f = (th * 18.0 / (2 * np.pi)) % 1.0
    vein = np.exp(-(np.abs(f - 0.5) / 0.075) ** 2) * H.sstep(0.05, 0.25, q)
    col = H.ramp(q, [(0.0, '#4ab046'), (0.6, '#2c8236'), (1.0, '#124a22')])
    hgt = np.sqrt(np.clip(1.0 - q ** 6, 0, 1)) * 14.0
    dif, _ = H.shade(hgt.astype(F32), 1.0)
    col = col * (0.60 + 0.70 * dif)[..., None] + vein[..., None] * _hx('#8ad060') * 0.45
    col = col + np.exp(-((1.0 - q) / 0.05) ** 2)[..., None] * _hx('#6ab44a') * 0.35
    M = _mk(S)
    _put(M, col.astype(F32), a)
    return M


def _lotus_master(S=220):
    x, y, rr, th = _polar(S)
    M = _mk(S)
    for k, (R, m, ph) in enumerate(((0.97, 8, 0.0), (0.76, 8, 0.5), (0.54, 6, 0.25))):
        f = (th * m / (2 * np.pi) + ph) % 1.0
        tri = 1.0 - np.abs(2 * f - 1)
        rb = R * (0.45 + 0.55 * tri ** 0.9)
        a = H.sstep(rb + 0.012, rb - 0.012, rr)
        t = np.clip((rb - rr) / (0.5 * R), 0, 1)
        col = H.ramp(t, [(0.0, '#fff8f0'), (0.5, '#fdf0f2'), (1.0, '#f2b8cc')]) * (0.80 + 0.20 * tri)[..., None]
        _put(M, col.astype(F32), a)
    _blob(M, S / 2, S / 2, 0.14 * S, 0.14 * S, 0.0, _hx('#c88a10'), _hx('#ffd83a'), _hx('#fff6c0'), 0.4, 1.0)
    return M


@_f("wx_lily_pads", "Lily Pad Pond",
    "Overlapping round lily pads with a notch and radial veins floating on dark rippled water, with a few white lotus flowers.")
def lily_pads(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 78 Lily Pad Pond: notched round pad master (26 radial veins, dome-lit, curled rim), 3 sizes x 12 rotations, ~85% grid fill over dark ripple water; 3-ring white lotus flowers on top; WET pads / dark water
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)
    z = _z(H.fbm(n, seed + 1, cells=(4, 10, 24)))
    rip = 0.5 + 0.5 * np.sin(Y / 3.3 + 5.0 * z + 0.6 * np.sin(X / 40.0))
    ground = H.ramp(np.clip(0.12 + 0.10 * z + 0.55 * rip, 0, 1), [(0.0, '#02121a'), (0.5, '#0a3a48'), (1.0, '#3a8a90')])
    tiles = _rot_tiles(_pad_master(), (130, 170, 215), tuple(range(0, 360, 30)))
    ex, ey, ti = _scatter(n, 12, seed + 2, 3, 12, jit=0.38)
    keep = r.random(len(ex)) < 0.86
    ex, ey, ti = ex[keep], ey[keep], ti[keep]
    img = _comp(n, ground, tiles, ex, ey, ti, tint=_tint(r, len(ex), 0.85, 1.12))
    lt = _rot_tiles(_lotus_master(), (130, 170), (0, 15, 30, 45))
    fx, fy, fti = _scatter(n, 10, seed + 3, 2, 4, jit=0.5)
    k2 = r.random(len(fx)) < 0.16
    H.splat_rgba(img, lt, fti[k2], fx[k2], fy[k2])
    Ln = H.sstep(0.03, 0.7, H.lum(img))
    M, R, CC = _curves(Ln, (10.0, 90.0), (130.0, 6.0), (16.0, 16.0))
    return _out(img, M, R, CC)


# =========================================================================
# 79 cactus areoles
# =========================================================================
def _spine_master(S=72, seed=9):
    r = H.rng(seed)
    M = _mk(S)
    nsp = 14
    polys = []
    for i in range(nsp):
        a = i * 2 * np.pi / nsp + r.uniform(-0.2, 0.2)
        L = r.uniform(15, 33)
        polys.append(np.array([[S / 2, S / 2], [S / 2 + L * np.cos(a), S / 2 + L * np.sin(a)]]))
    _strokes(M, polys, 2, _hx('#f6f2e0'))
    _blob(M, S / 2, S / 2, 6.5, 6.5, 0.0, _hx('#8a8466'), _hx('#ece6cc'))
    _blob(M, S / 2, S / 2, 2.4, 2.4, 0.0, _hx('#1a1008'), _hx('#3a2a18'))
    return M


def _cw(Y):
    return 16.0 * np.sin(Y / 190.0) + 8.0 * np.sin(Y / 77.0 + 1.3)


@_f("wx_cactus_spines", "Cactus Areoles",
    "Ribbed green cactus skin with a star of white spines bursting from every areole along the rib crests.")
def cactus_spines(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 79 Cactus Areoles: 78 px wavy vertical ribs (sin^0.8 profile, bump-lit, wax grain) + 14-spine star stamps (felt ring, dark centre) at rib-crest areoles every 66 px (offset per rib); spines CHR, skin SAT
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)
    W = 78.0
    xs = X - _cw(Y)
    f = (xs / W) % 1.0
    hgt = (np.sin(np.pi * f) ** 0.8).astype(F32)
    dif, spc = H.shade(hgt * 16.0, 1.0)
    z = _z(H.fbm(n, seed + 1, cells=(10, 24, 60)))
    t = np.clip(0.18 + 0.42 * hgt + 0.30 * (dif - 0.5) + 0.05 * z + 0.03 * H.grain(n, seed + 2), 0, 1)
    ground = H.ramp(t, [(0.0, '#0e2a12'), (0.45, '#2e6a30'), (0.8, '#5a9a44'), (1.0, '#98c870')]) + (spc * 0.10)[..., None]
    tiles = _rot_tiles(_spine_master(), (54, 66, 80), tuple(range(0, 360, 30)))
    exs, eys = [], []
    for ri in range(-1, int(n / W) + 2):
        ys0 = np.arange(-20.0, n + 40, 66.0)
        ys = ys0 + 33.0 * (ri & 1) + r.uniform(-3, 3, len(ys0))
        exs.append((ri + 0.5) * W + _cw(ys) + r.uniform(-2, 2, len(ys)))
        eys.append(ys)
    ex, ey = np.concatenate(exs), np.concatenate(eys)
    ti = r.integers(0, 3, len(ex)) * 12 + r.integers(0, 12, len(ex))
    o = np.argsort(ey, kind="stable")
    img = _comp(n, ground, tiles, ex[o], ey[o], ti[o])
    Ln = H.sstep(0.05, 0.95, H.lum(img))
    M, R, CC = _curves(Ln, (10.0, 255.0), (140.0, 10.0), (80.0, 16.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 80 briar
# =========================================================================
def _leaf_master(S=48):
    M = _mk(S)
    _blob(M, S / 2, S / 2, S * 0.40, S * 0.17, 0.0, _hx('#0e3a14'), _hx('#3a9a30'), _hx('#c0f080'), 0.25, 1.0)
    _strokes(M, [np.array([[S * 0.12, S / 2], [S * 0.88, S / 2]], np.float64)], 1, _hx('#8ad060'))
    return M


def _hip_master(S=96):
    M = _mk(S)
    _blob(M, S / 2, S / 2 + 4, 34, 36, 0.0, _hx('#6a0c04'), _hx('#e83a18'), _hx('#ffd8c0'), 0.7, 1.0)
    polys = [np.array([[S / 2, S / 2 - 30], [S / 2 + 12 * np.cos(a), S / 2 - 30 + 12 * np.sin(a)]]) for a in np.linspace(0, 2 * np.pi, 6)[:-1]]
    _strokes(M, polys, 2, _hx('#3a2a10'))
    return M


@_f("wx_rose_thorns", "Thorned Briar",
    "A tangle of dark green briar stems armed with hooked red thorns, small leaflets and glossy scarlet rose hips.")
def rose_thorns(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 80 Thorned Briar: 70 curl-field stems (two widths, shadow + stem + highlight passes), ~1900 hooked thorn triangles along the stems, ~700 leaflet stamps, glossy rose-hip stamps with calyx star; SAT
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(6, 14, 30)))
    ground = H.ramp(np.clip(0.30 + 0.16 * z, 0, 1), [(0.0, '#0e1c0e'), (0.5, '#1e3418'), (1.0, '#3a5226')])
    u, v = H.curl_field(512, seed + 2, cells=(3, 6, 10))
    p0 = r.random((110, 2)).astype(F32) * n
    P = _strands(u, v, p0, 36, 14.0)
    K = P.shape[0]
    val = r.uniform(120, 230, K)
    major = r.random(K) < 0.45
    ones = np.full(K, 255.0)
    cv = H.lines3(n, P[major] + 4.0, np.stack([np.full(major.sum(), 30.0), np.full(major.sum(), 255.0), np.zeros(major.sum())], 1), 21)
    cv = H.lines3(n, P[~major] + 3.0, np.stack([np.full((~major).sum(), 30.0), np.full((~major).sum(), 255.0), np.zeros((~major).sum())], 1), 13, canvas=cv)
    cv = H.lines3(n, P[major], np.stack([val[major] * 0.55 + 40, np.full(major.sum(), 255.0), np.zeros(major.sum())], 1), 15, canvas=cv)
    cv = H.lines3(n, P[~major], np.stack([val[~major] * 0.55 + 40, np.full((~major).sum(), 255.0), np.zeros((~major).sum())], 1), 8, canvas=cv)
    cv = H.lines3(n, P[major] - 1.5, np.stack([np.minimum(val[major] + 40, 255), np.full(major.sum(), 255.0), np.zeros(major.sum())], 1), 3, canvas=cv)
    # thorns
    th = []
    ex, ey = [], []
    for k in range(K):
        pk = P[k]
        for i in range(3, pk.shape[0] - 3, 4):
            T = pk[i + 2] - pk[i - 2]
            T = T / (np.hypot(*T) + 1e-6)
            Nn = np.array([-T[1], T[0]])
            side = 1.0 if r.random() < 0.5 else -1.0
            tip = pk[i] + side * Nn * 30.0 + T * 24.0
            th.append(np.stack([pk[i] - 10.0 * T, tip, pk[i] + 10.0 * T]))
            if r.random() < 0.55:
                ex.append(pk[i] + side * Nn * 9.0)
                ey.append(0)
    th = np.stack(th).astype(F32)
    cv = H.fills3(n, th, np.stack([np.full(len(th), 235.0), np.full(len(th), 255.0), np.zeros(len(th))], 1), canvas=cv)
    V = H.u8f(cv[..., 0])
    m = H.u8f(cv[..., 1])
    col = H.ramp(np.clip(V * 1.2, 0, 1), [(0.0, '#102a12'), (0.35, '#2e5a28'), (0.6, '#6a5a2a'), (0.85, '#b04228'), (1.0, '#f0a080')])
    rgb = ground * (1.0 - m)[..., None] + col * m[..., None]
    # leaflets and hips
    lt = _rot_tiles(_leaf_master(), (32, 44), tuple(range(0, 360, 30)))
    lx = np.array([e[0] for e in ex]) + r.uniform(-8, 8, len(ex))
    ly = np.array([e[1] for e in ex]) + r.uniform(-8, 8, len(ex))
    lti = r.integers(0, 2, len(lx)) * 12 + r.integers(0, 12, len(lx))
    o = np.argsort(ly)
    img = np.ascontiguousarray(rgb, F32).copy()
    H.splat_rgba(img, lt, lti[o], lx[o], ly[o], tint=_tint(r, len(lx), 0.8, 1.15)[o])
    ht = _rot_tiles(_hip_master(), (62, 80), (0, 30, 60))
    hi = r.choice(len(lx), 60, replace=False)
    hx, hy = lx[hi], ly[hi]
    o = np.argsort(hy)
    H.splat_rgba(img, ht, (r.integers(0, 2, 60) * 3 + r.integers(0, 3, 60))[o], hx[o], hy[o])
    Ln = H.sstep(0.04, 0.7, H.lum(img))
    M, R, CC = _curves(Ln, (60.0, 160.0), (120.0, 30.0), (60.0, 40.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 81 wisteria
# =========================================================================
def _wist_master(S=380, seed=11):
    r = H.rng(seed)
    M = _mk(S)
    cx = S / 2.0
    top, bot = 4.0, S - 12.0
    _strokes(M, [np.array([[cx, top], [cx + 3, 120], [cx - 2, 250], [cx, bot - 20]], np.float64)], 3, _hx('#6a9050'))
    K = 260
    t = np.sort(r.random(K) ** 1.2)
    viol0, viol1, bud = _hx('#5a2aa8'), _hx('#b89cf0'), _hx('#a8d090')
    for tk in t:
        y = top + 8 + tk * (bot - top - 8)
        wmax = 46.0 * (1.0 - tk) ** 0.7 * min(1.0, tk / 0.07 + 0.30)
        x = cx + r.uniform(-1, 1) * wmax + 4.0 * np.sin(tk * 9.0)
        col = viol0 * (1 - tk ** 0.8) + viol1 * tk ** 0.8
        if tk > 0.84:
            q = (tk - 0.84) / 0.16 * 0.9
            col = col * (1 - q) + bud * q
        sz = 8.5 - 3.0 * tk + r.uniform(-1, 1)
        ang = r.uniform(0, 3.14159)
        _blob(M, x, y, sz * 1.15, sz * 0.85, ang, col * 0.45, col, _hx('#fff4ff'), 0.35, 1.0)
        _blob(M, x + r.uniform(-3, 3), y + sz * 0.5, sz * 0.7, sz * 0.55, ang + 0.8, col * 0.55, col * 1.15, None, 0.0, 1.0)
    return M


def _wleaf_master(S=72):
    M = _mk(S)
    _blob(M, S / 2, S / 2, S * 0.44, S * 0.17, 0.0, _hx('#1c4a20'), _hx('#6ab050'), _hx('#d8f8b0'), 0.30, 1.0)
    _strokes(M, [np.array([[S * 0.10, S / 2], [S * 0.90, S / 2]], np.float64)], 1, _hx('#b8e090'))
    return M


@_f("wx_wisteria_cascade", "Wisteria Cascade",
    "Long violet wisteria racemes hang from woody vines, florets fading to pale green buds among small leaflets.")
def wisteria_cascade(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 81 Wisteria Cascade: 260-floret raceme master (tapered, violet to lavender to green buds, banner+wing petals), ~320 racemes hung along 8 wavy vines (3 sizes, +-10 deg sway), ~1300 leaflet stamps along the vines; FLK
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(5, 11, 24)))
    ground = H.ramp(np.clip(0.34 + 0.15 * z + 0.05 * _z(H.noise(n, 120, seed + 9)), 0, 1), [(0.0, '#0c140c'), (0.5, '#1c2e1c'), (1.0, '#3a5a34')])
    vm = np.zeros((n, n), np.uint8)
    vines = []
    for j in range(8):
        yb = 100.0 + j * 262.0 + r.uniform(-30, 30)
        lam, A, ph = r.uniform(500, 900), r.uniform(30, 70), r.uniform(0, 6.283)
        xs = np.arange(-60.0, n + 60, 8.0)
        ys = yb + A * np.sin(2 * np.pi * xs / lam + ph) + 14.0 * np.sin(2 * np.pi * xs / (lam * 0.37) + 2 * ph)
        vines.append((xs, ys))
        cv2.polylines(vm, [np.round(np.stack([xs, ys], 1) * 4).astype(np.int32).reshape(-1, 1, 2)], False, 255, 11, cv2.LINE_AA, 2)
    va = cv2.GaussianBlur(vm.astype(F32) / 255.0, (0, 0), 0.8)
    vcol = _hx('#3a2a1c')[None, None, :] * (0.70 + 0.60 * np.clip(0.5 + 0.30 * _z(H.noise(n, 380, seed + 3)), 0, 1))[..., None]
    hl = np.clip(va - np.roll(va, (3, 3), (0, 1)), 0, 1)
    ground = ground * (1 - va[..., None]) + vcol * va[..., None] + (0.30 * hl)[..., None]
    img = np.ascontiguousarray(ground, F32)
    lt = _rot_tiles(_wleaf_master(), (50, 64), tuple(range(0, 360, 30)))
    lx, ly, lti = [], [], []
    for xs, ys in vines:
        for i in range(8, len(xs) - 8, 3):
            T = np.array([xs[i + 2] - xs[i - 2], ys[i + 2] - ys[i - 2]])
            a0 = np.arctan2(T[1], T[0])
            for side in (-1, 1):
                a = a0 + side * r.uniform(0.8, 1.4)
                dist = r.uniform(20, 34)
                lx.append(xs[i] + dist * np.cos(a))
                ly.append(ys[i] + dist * np.sin(a))
                lti.append(int(r.integers(0, 2)) * 12 + int(round(((-np.degrees(a)) % 360) / 30.0)) % 12)
    lx, ly, lti = np.array(lx), np.array(ly), np.array(lti)
    o = np.argsort(ly, kind="stable")
    H.splat_rgba(img, lt, lti[o], lx[o], ly[o], tint=_tint(r, len(lx), 0.80, 1.15)[o])
    sizes, angs = (300, 380, 460), (-10, -5, 0, 5, 10)
    rt = _trim(_rot_tiles(_wist_master(), sizes, angs))
    rx, ry, rti = [], [], []
    for xs, ys in vines:
        xb = np.arange(-30.0, n + 30, 70.0)
        xi = xb + r.uniform(-18, 18, len(xb))
        yi = np.interp(xi, xs, ys)
        ti = r.integers(0, 3, len(xi)) * 5 + r.integers(0, 5, len(xi))
        hh = np.array([rt[k].shape[0] for k in ti])
        rx.append(xi)
        ry.append(yi + hh / 2.0 - 8.0)
        rti.append(ti)
    rx, ry, rti = np.concatenate(rx), np.concatenate(ry), np.concatenate(rti)
    o = np.argsort(ry, kind="stable")
    H.splat_rgba(img, rt, rti[o], rx[o], ry[o], tint=_tint(r, len(rx), 0.88, 1.10)[o])
    Ln = H.sstep(0.04, 0.80, H.lum(img))
    M, R, CC = _curves(Ln, (30.0, 210.0), (150.0, 30.0), (90.0, 10.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 82 maple
# =========================================================================
def _maple_master(S, c_in, c_out, seed):
    M = _mk(S)
    ox, oy = S * 0.5, S * 0.60
    R = S * 0.46
    keys = [(-150, .30), (-130, .33), (-88, .62), (-68, .42), (-48, .88), (-24, .42), (0, 1.0), (24, .42), (48, .88), (68, .42), (88, .62), (130, .33), (150, .30)]
    pts = []
    for (a0, r0), (a1, r1) in zip(keys[:-1], keys[1:]):
        for i in range(6):
            f = i / 6.0
            rr = r0 + (r1 - r0) * f
            if i > 0:
                rr *= 1.0 + (0.10 if i % 2 == 1 else -0.04)
            pts.append((a0 + (a1 - a0) * f, rr))
    pts.append((150, .30))
    pts.append((180, .20))
    P = np.array([(ox + R * rr * np.sin(np.radians(a)), oy - R * rr * np.cos(np.radians(a))) for a, rr in pts], np.float64)
    m = np.zeros((S, S), np.uint8)
    cv2.fillPoly(m, [np.round(P * 16).astype(np.int32)], 255, cv2.LINE_AA, 4)
    aa = m.astype(F32) / 255.0
    gx, gy = H.tile_xy(S)
    t = np.clip(np.hypot(gx + (S - 1) / 2 - ox, gy + (S - 1) / 2 - oy) / R, 0, 1.1) ** 1.1
    col = np.asarray(c_in, F32)[None, None, :] * (1 - t[..., None]) + np.asarray(c_out, F32)[None, None, :] * t[..., None]
    blot = (0.86 + 0.28 * np.clip(0.5 + 0.35 * _z(H.noise(S, 9, seed)), 0, 1)) * (0.62 + 0.80 * np.clip(0.5 + 0.30 * _z(H.noise(S, 30, seed + 5)), 0, 1))
    dt = cv2.distanceTransform((m > 128).astype(np.uint8) * 255, cv2.DIST_L2, 3)
    col = col * blot[..., None] * (0.68 + 0.32 * np.clip(dt / 7.0, 0, 1))[..., None]
    _put(M, col.astype(F32), aa)
    _strokes(M, [np.array([[ox, oy], [ox + 3, S - 6]], np.float64)], 5, _hx('#6a2410'))
    vc = _hx('#ffe6a8')
    side, main = [], []
    for a, rr in ((0, 1.0), (-48, .88), (48, .88), (-88, .62), (88, .62)):
        ca, sa = np.sin(np.radians(a)), -np.cos(np.radians(a))
        L = R * rr * 0.93
        main.append(np.array([[ox, oy], [ox + L * ca, oy + L * sa]]))
        for u in np.arange(0.18, 0.88, 0.075):
            bx, by = ox + L * u * ca, oy + L * u * sa
            ln = (0.30 - 0.16 * u) * R * rr
            for sg in (-1, 1):
                aa2 = np.radians(a + sg * 52)
                side.append(np.array([[bx, by], [bx + ln * np.sin(aa2), by - ln * np.cos(aa2)]]))
    _strokes(M, side, 2, vc * 0.62)
    _strokes(M, main, 5, vc)
    return M


@_f("wx_maple_veins", "Maple Leaf Veins",
    "Overlapping maple leaves in scarlet, orange and gold, serrated lobes laced with pale veins and fine side veins.")
def maple_veins(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 82 Maple Leaf Veins: 5-lobe serrated outline (polar key points + 3 teeth per flank), gradient fill, 5 main veins + ~60 side veins per leaf, 3 colourways x 3 sizes x 12 rotations on a dense staggered grid; SAT with bright veins
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(6, 14, 30)))
    ground = H.ramp(np.clip(0.26 + 0.14 * z + 0.05 * _z(H.noise(n, 160, seed + 2)), 0, 1), [(0.0, '#2a1006'), (0.5, '#5a2810'), (1.0, '#8a4a1c')])
    sizes, angs = (130, 165, 205), tuple(range(0, 360, 30))
    pal = [('#e07818', '#a8100c'), ('#e8b820', '#d85a0c'), ('#c03a10', '#640a10')]
    tiles = []
    for k, (ci, co) in enumerate(pal):
        tiles += _trim(_rot_tiles(_maple_master(380, _hx(ci), _hx(co), seed + 20 + k), sizes, angs))
    ex, ey, ti0 = _scatter(n, 18, seed + 3, 3, 12, jit=0.36)
    ti = r.integers(0, 3, len(ex)) * 36 + ti0
    img = _fine(_comp(n, ground, tiles, ex, ey, ti, tint=_tint(r, len(ex), 0.88, 1.10)), seed + 40, 0.16)
    Ln = H.sstep(0.05, 0.85, H.lum(img))
    M, R, CC = _curves(Ln, (20.0, 170.0), (200.0, 70.0), (110.0, 40.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 83 orchid
# =========================================================================
def _orchid_petal(S, ratio, seed, spotk):
    M = _mk(S)
    gx, gy = H.tile_xy(S)
    L = S * 0.46
    Wd = L / ratio
    u = gx / L
    v = gy / Wd
    wprof = np.sqrt(np.clip(1.0 - u * u, 0, 1)) * (0.45 + 0.55 * H.sstep(-1.0, 0.1, u))
    e = (wprof - np.abs(v)) * Wd
    a = np.clip(e / 1.5 + 0.5, 0, 1)
    m = (0.70 * H.sstep(0.25, -0.95, u))[..., None]
    col = _hx('#f6e6ee')[None, None, :] * (1 - m) + _hx('#d84a96')[None, None, :] * m
    phi = np.arctan2(v * Wd, (u + 1.0) * L + 1e-3)
    rad = np.hypot(v * Wd, (u + 1.0) * L) / L
    vn = (0.5 + 0.5 * np.cos(24.0 * phi)) ** 8 * H.sstep(0.08, 0.35, rad)
    va = (0.50 * vn)[..., None]
    col = col * (1 - va) + _hx('#b8286e') * va
    z1 = _z(H.noise(S, 27, seed)) + 0.7 * _z(H.noise(S, 41, seed + 1))
    thr = 1.7 - 1.2 * H.sstep(0.7, -0.8, u) + (1.0 - spotk)
    sp = (H.sstep(thr, thr + 0.30, z1) * 0.92)[..., None]
    col = col * (1 - sp) + _hx('#6a0a34') * sp
    col = col * (0.76 + 0.24 * np.clip(e / 9.0, 0, 1))[..., None]
    col = col + (0.10 * np.exp(-(v * Wd / 1.6) ** 2) * (u > -0.9))[..., None]
    _put(M, np.clip(col, 0, 1).astype(F32), a)
    return M


def _orchid_lip(S, seed):
    r = H.rng(seed)
    M = _mk(S)
    c = S / 2.0
    L = S * 0.46
    for dy, ang, ax, ay in ((-0.22, -0.5, 0.34, 0.20), (0.22, 0.5, 0.34, 0.20), (0.0, 0.0, 0.46, 0.30)):
        _blob(M, c + 0.10 * L, c + dy * L, ax * L, ay * L, ang, _hx('#6a0a40'), _hx('#c82a80'), _hx('#ff9ac8'), 0.35, 1.0)
    polys = []
    for a in np.linspace(-1.1, 1.1, 15):
        polys.append(np.array([[c - 0.55 * L, c], [c - 0.55 * L + 0.95 * L * np.cos(a), c + 0.95 * L * np.sin(a)]]))
    _strokes(M, polys, 2, _hx('#4e0630'))
    _blob(M, c - 0.30 * L, c, 0.20 * L, 0.17 * L, 0.0, _hx('#a07808'), _hx('#f6c828'), _hx('#fff0a0'), 0.4, 1.0)
    for k in range(18):
        _blob(M, c - 0.30 * L + r.uniform(-0.15, 0.15) * L, c + r.uniform(-0.12, 0.12) * L, 2.6, 2.6, 0.0, _hx('#901010'), _hx('#d02020'), None, 0.0, 1.0)
    return M


@_f("wx_orchid_spots", "Orchid Throat Spots",
    "Overlapping orchid petals, white fading to magenta at the throat, crowded with maroon speckles and veins, plus frilled magenta lips.")
def orchid_spots(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 83 Orchid Throat Spots (v2: stamp petals instead of a Voronoi field, which read as cracked mud): pear-shaped petal master (white to magenta flush, 24 radial veins, threshold-noise maroon speckle dense at the base, edge AO, midrib) in round and narrow cuts + three-lobed lip master with yellow callus; ~250 randomly rotated overlapping stamps; WET
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(5, 11, 24)))
    ground = H.ramp(np.clip(0.30 + 0.14 * z, 0, 1), [(0.0, '#2a0618'), (0.5, '#4a0e30'), (1.0, '#7a2050')])
    sizes, angs = (150, 190), tuple(range(0, 360, 15))
    masters = [_orchid_petal(320, 1.15, seed + 11, 1.0), _orchid_petal(320, 2.1, seed + 12, 0.8), _orchid_lip(320, seed + 13)]
    tiles = []
    for m_ in masters:
        tiles += _trim(_rot_tiles(m_, sizes, angs))
    ex, ey, _ = _scatter(n, 22, seed + 3, 1, 1, jit=0.5)
    K = len(ex)
    kind = r.choice(3, K, p=[0.45, 0.35, 0.20])
    ti = kind * 48 + r.integers(0, 2, K) * 24 + r.integers(0, 24, K)
    img = _comp(n, ground, tiles, ex, ey, ti, tint=_tint(r, K, 0.90, 1.06))
    Ln = H.sstep(0.05, 0.90, H.lum(img))
    M, R, CC = _curves(Ln, (5.0, 60.0), (90.0, 10.0), (60.0, 16.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 84 pollen
# =========================================================================
def _tri(M, p0, p1, p2, rgb):
    P = np.array([p0, p1, p2], np.float64)
    x0, y0 = int(np.floor(P[:, 0].min())) - 2, int(np.floor(P[:, 1].min())) - 2
    x1, y1 = int(np.ceil(P[:, 0].max())) + 3, int(np.ceil(P[:, 1].max())) + 3
    w, h = x1 - x0, y1 - y0
    m = np.zeros((h, w), np.uint8)
    cv2.fillConvexPoly(m, np.round((P - [x0, y0]) * 16).astype(np.int32), 255, cv2.LINE_AA, 4)
    _putp(M, x0, y0, np.broadcast_to(np.asarray(rgb, F32), (h, w, 3)), m.astype(F32) / 255.0)


def _pollen_master(S=400):
    M = _mk(S)
    c = S / 2.0
    R, L = S * 0.28, S * 0.19
    Nn = 70
    i = np.arange(Nn) + 0.5
    zz = 1 - 2 * i / Nn
    rr = np.sqrt(1 - zz * zz)
    ph = i * 2.399963
    px, py = rr * np.cos(ph), rr * np.sin(ph)
    gold = _hx('#f0b830')

    def spike(k):
        x, y, z = px[k], py[k], zz[k]
        bx, by = c + R * x, c + R * y
        lit = 0.75 + 0.45 * np.clip(-(x * 0.55 + y * 0.83), -1, 1) * 0.5 + 0.2 * z
        if rr[k] * L < 8.0:
            _blob(M, bx, by, 5.0, 5.0, 0.0, _hx('#6a3a08') * lit, gold * lit, _hx('#fff4c0'), 0.6, 1.0)
        else:
            tx, ty = c + (R + L) * x, c + (R + L) * y
            ux, uy = x / rr[k], y / rr[k]
            w = 11.0
            _tri(M, (bx - uy * w, by + ux * w), (bx + uy * w, by - ux * w), (tx, ty), gold * lit)
            _strokes(M, [np.array([[bx - uy * w * 0.4, by + ux * w * 0.4], [tx, ty]])], 1, _hx('#fff0b0') * min(lit, 1.0))
    for k in np.nonzero((zz < 0) & (zz > -0.45))[0]:
        spike(k)
    _blob(M, c, c, R, R, 0.0, _hx('#8a5a14'), _hx('#e0a028'), _hx('#fff2b8'), 0.45, 1.2)
    j = np.arange(190) + 0.25
    z2 = 1 - 2 * j / 190
    r2 = np.sqrt(1 - z2 * z2)
    p2 = j * 2.399963 + 1.0
    for k in range(190):
        if z2[k] > 0.1:
            x, y = r2[k] * np.cos(p2[k]), r2[k] * np.sin(p2[k])
            _blob(M, c + R * 0.97 * x, c + R * 0.97 * y, 11.0 * max(z2[k], 0.3), 11.0, np.arctan2(y, x), _hx('#1a0c02'), _hx('#5a3208'), _hx('#e8b040'), 0.35, 1.0)
    for k in np.nonzero(zz >= 0)[0][::-1]:
        spike(k)
    return M


@_f("wx_pollen_grains", "Pollen Grains Macro",
    "Golden pollen grains under a microscope: spiky, pitted spheres with amber shading, sharp ones in front of blurred ones.")
def pollen_grains(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 84 Pollen Grains Macro: echinate pollen master (150 Fibonacci-sphere spikes as AA cones, rim spikes behind the body, 70 pits, shaded amber sphere), blurred dim background grains + sharp foreground grains in 3 sizes; FLK
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(5, 11, 24)))
    ground = H.ramp(np.clip(0.30 + 0.07 * z + 0.09 * _z(H.noise(n, 140, seed + 2)), 0, 1), [(0.0, '#100802'), (0.5, '#2a1606'), (1.0, '#5a3a10')])
    master = _pollen_master()
    img = np.ascontiguousarray(ground, F32)
    img = img + (H.flake_mask(n, 0.004, seed + 5)[..., None] * _hx('#c8901c') * 0.55 + 0.05 * _z(H.noise(n, 200, seed + 6))[..., None] * _hx('#c8901c')).astype(F32)
    bg = [cv2.GaussianBlur(t, (0, 0), 3.0) for t in _rot_tiles(master, (220, 280), (0, 40))]
    bx, by, bti = _scatter(n, 6, seed + 3, 2, 2, jit=0.45)
    H.splat_rgba(img, bg, bti, bx, by, amp=np.full(len(bx), 0.18, F32))
    st = _trim(_rot_tiles(master, (70, 90), (0, 50)))
    sx_, sy_, sti = _scatter(n, 20, seed + 7, 2, 2, jit=0.5)
    kp = r.random(len(sx_)) < 0.55
    H.splat_rgba(img, st, sti[kp], sx_[kp], sy_[kp], amp=np.full(int(kp.sum()), 0.85, F32))
    tiles = _trim(_rot_tiles(master, (120, 160, 215), (0, 25, 50, 75, 100)))
    ex, ey, ti = _scatter(n, 13, seed + 4, 3, 5, jit=0.42)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_tint(r, len(ex), 0.84, 1.10))
    img = _fine(img, seed + 41, 0.26)
    Ln = H.sstep(0.03, 0.80, H.lum(img))
    M, R, CC = _curves(Ln, (60.0, 190.0), (130.0, 60.0), (20.0, 16.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 85 dandelion clocks
# =========================================================================
def _dand_master(S=400):
    M = _mk(S)
    c = S / 2.0
    R = S * 0.40
    Nn = 130
    i = np.arange(Nn) + 0.5
    zz = 1 - 2 * i / Nn
    rr = np.sqrt(1 - zz * zz)
    ph = i * 2.399963
    px, py = rr * np.cos(ph), rr * np.sin(ph)
    r = H.rng(5)
    buckets = [(zz < -0.3, '#8a9a92', 2), ((zz >= -0.3) & (zz < 0.4), '#c8d8d0', 2), (zz >= 0.4, '#f4faf6', 2)]
    for bi, (sel, colr, wd) in enumerate(buckets):
        polys = []
        for k in np.nonzero(sel)[0]:
            x, y = px[k], py[k]
            s0 = np.array([c + 0.07 * R * x, c + 0.07 * R * y])
            T = np.array([c + R * x, c + R * y])
            polys.append(np.stack([s0, T]))
            if rr[k] < 0.5:
                angs = np.linspace(0, 2 * np.pi, 7)[:-1] + r.uniform(0, 1)
                ln = 0.065 * R
            else:
                base = np.arctan2(y, x)
                angs = base + np.linspace(-1.2, 1.2, 6)
                ln = 0.10 * R
            for a in angs:
                polys.append(np.stack([T, T + ln * np.array([np.cos(a), np.sin(a)])]))
        _strokes(M, polys, wd, _hx(colr))
        if bi == 1:
            _blob(M, c, c, 10, 10, 0.0, _hx('#2a2010'), _hx('#6a5a38'), None, 0.0, 1.0)
    return M


def _para_master(S=96):
    M = _mk(S)
    cx = S / 2.0
    top = np.array([cx, 26.0])
    polys = []
    for a in np.linspace(-1.35, 1.35, 17):
        polys.append(np.stack([top, top + 26.0 * np.array([np.sin(a), -np.cos(a)]) * (0.85 + 0.15 * np.cos(a))]))
    _strokes(M, polys, 1, _hx('#eef6f0'))
    _strokes(M, [np.array([[cx, 26.0], [cx, 68.0]])], 2, _hx('#c8d4cc'))
    _blob(M, cx, 76, 3.4, 9.0, 0.0, _hx('#3a2a14'), _hx('#9a7a44'), None, 0.0, 1.0)
    return M


@_f("wx_dandelion_clocks", "Dandelion Seed Clocks",
    "Silvery dandelion seed clocks of radiating feathery filaments, with loose parachute seeds drifting across grey-green.")
def dandelion_clocks(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 85 Dandelion Seed Clocks: puffball master (200 Fibonacci-sphere filaments in 3 depth buckets, tip tufts of 8 hairs, dark receptacle), blurred bokeh puffballs + sharp ones, ~520 loose parachute seeds; FLK silver
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(5, 11, 24)))
    ground = H.ramp(np.clip(0.32 + 0.10 * z + 0.04 * _z(H.noise(n, 150, seed + 2)) + 0.10 * _z(H.noise(n, 130, seed + 6)) + 0.09 * _z(H.noise(n, 200, seed + 7)), 0, 1), [(0.0, '#101a16'), (0.5, '#223028'), (1.0, '#3c5246')])
    ground = ground + (H.flake_mask(n, 0.004, seed + 8)[..., None] * _hx('#a8c0b0') * 0.6).astype(F32)
    img = np.ascontiguousarray(ground, F32)
    master = _dand_master()
    bg = [cv2.GaussianBlur(t, (0, 0), 4.0) for t in _rot_tiles(master, (250, 290), (0, 30))]
    bx, by, bti = _scatter(n, 9, seed + 3, 2, 2, jit=0.45)
    H.splat_rgba(img, bg, bti, bx, by, amp=np.full(len(bx), 0.12, F32))
    tiles = _trim(_rot_tiles(master, (125, 155, 190), (0, 17, 34, 51, 68)))
    ex, ey, ti = _scatter(n, 11, seed + 4, 3, 5, jit=0.40)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=np.repeat(r.uniform(0.93, 1.06, (len(ex), 1)).astype(F32), 3, 1))
    pt = _rot_tiles(_para_master(), (60, 80), tuple(range(0, 360, 30)))
    K = 1300
    sx, sy = r.random(K) * n, r.random(K) * n
    sti = r.integers(0, 2, K) * 12 + r.integers(0, 12, K)
    o = np.argsort(sy)
    H.splat_rgba(img, pt, sti[o], sx[o], sy[o], tint=np.repeat(r.uniform(0.9, 1.06, (K, 1)).astype(F32), 3, 1)[o])
    img = _fine(img, seed + 42, 0.12)
    Ln = H.sstep(0.05, 0.85, H.lum(img))
    M, R, CC = _curves(Ln, (40.0, 250.0), (170.0, 14.0), (70.0, 16.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 86 succulent
# =========================================================================
def _succ_master(S=380):
    M = _mk(S)
    c = S / 2.0
    Nl = 72
    Rm = 0.455 * S
    sage, pink = _hx('#9ab49a'), _hx('#c898a4')
    for i in range(Nl, 0, -1):
        q = np.sqrt(i / Nl)
        th = i * 2.399963
        T = Rm * q ** 0.95 + 5.0
        ln = 0.30 * Rm * (0.35 + 0.65 * q)
        B = T - ln
        rc = 0.5 * (B + T)
        cx, cy = c + rc * np.cos(th), c + rc * np.sin(th)
        col = sage * (1 - 0.55 * q) + pink * (0.55 * q)
        _blob(M, cx, cy, ln * 0.55, ln * 0.36, th, _hx('#3c5a46'), col, _hx('#f2f6ee'), 0.30, 1.1)
        tx, ty = c + (T - ln * 0.16) * np.cos(th), c + (T - ln * 0.16) * np.sin(th)
        _blob(M, tx, ty, ln * 0.20, ln * 0.17, th, _hx('#9a4a62'), _hx('#e29ab0'), _hx('#fff0f4'), 0.35, 1.0)
    return M


@_f("wx_succulent_rosette", "Succulent Rosettes",
    "Tight geometric echeveria rosettes of plump sage leaves in golden-angle spirals, each tipped in dusty pink.")
def succulent_rosette(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 86 Succulent Rosettes: 72-leaf phyllotaxis master (golden angle, outer leaves first, plump shaded blades with pink tip caps, sage to dusty pink by radius), 4 sizes x 6 rotations on a jittered bed + small filler rosettes, grit soil; SAT
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(5, 11, 24)))
    ground = H.ramp(np.clip(0.30 + 0.12 * z + 0.06 * _z(H.noise(n, 160, seed + 2)), 0, 1), [(0.0, '#150e0a'), (0.5, '#2c2018'), (1.0, '#5a4636')])
    img = np.ascontiguousarray(ground + (H.flake_mask(n, 0.004, seed + 3)[..., None] * _hx('#8a7a6a') * 0.6).astype(F32), F32)
    master = _succ_master()
    st = _trim(_rot_tiles(master, (80, 100), (0, 60, 120)))
    fx, fy, fti = _scatter(n, 23, seed + 4, 2, 3, jit=0.5)
    kp = r.random(len(fx)) < 0.60
    H.splat_rgba(img, st, fti[kp], fx[kp], fy[kp], tint=_tint(r, int(kp.sum()), 0.80, 1.00))
    tiles = _trim(_rot_tiles(master, (125, 155, 190, 230), (0, 60, 120, 180, 240, 300)))
    ex, ey, ti = _scatter(n, 14, seed + 5, 4, 6, jit=0.45)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_tint(r, len(ex), 0.90, 1.08))
    img = _fine(img, seed + 43, 0.08)
    Ln = H.sstep(0.05, 0.85, H.lum(img))
    M, R, CC = _curves(Ln, (10.0, 110.0), (190.0, 80.0), (120.0, 30.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 87 bamboo
# =========================================================================
def _bamboo_leaf_master(S=300):
    r = H.rng(7)
    M = _mk(S)
    c = S / 2.0
    for a in np.linspace(-1.35, 1.35, 8):
        for side in (0.0, 1.0):
            ang = a + side * 3.14159
            dr = 0.25 * S
            _blob(M, c + dr * np.cos(ang), c + dr * np.sin(ang), 0.20 * S, 0.026 * S, ang, _hx('#1c5a2a'), _hx('#6ab85a'), _hx('#d8f8b0'), 0.30, 1.0)
            ang2 = ang + 0.28 * (1 if np.sin(ang) > 0 else -1)
            dr2 = 0.46 * S
            _blob(M, c + dr2 * np.cos(ang2), c + dr2 * np.sin(ang2), 0.09 * S, 0.020 * S, ang2, _hx('#1c5a2a'), _hx('#5aa84c'), None, 0.0, 1.0)
    return M


@_f("wx_bamboo_grove", "Bamboo Grove",
    "Vertical jade bamboo culms with dark node rings and pale internodes, thin lanceolate leaves drooping from the nodes.")
def bamboo_grove(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 87 Bamboo Grove: 36 depth-sorted culms (width 34-124 px, cylinder shading, per-internode tone, node rings + pale ridge, vertical grain streaks, jade to yellow-green, haze on far culms) + leaf-cluster stamps at the nodes; BRU vertical
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(5, 11, 24)))
    img = H.ramp(np.clip(0.34 + 0.14 * z, 0, 1), [(0.0, '#08140e'), (0.5, '#143024'), (1.0, '#2c5a40')]).astype(F32).copy()
    streak = _z(_aniso(n, 170, 5, seed + 2, 0.0))
    yy = np.arange(n, dtype=F32)[:, None]
    jade = [(0.0, '#0a2616'), (0.30, '#1a6a3e'), (0.62, '#4ea468'), (0.88, '#a8d488'), (1.0, '#eaf6b6')]
    NC = 36
    depth = np.sort(r.random(NC))
    leaf_pos = []
    for ci in range(NC):
        d = depth[ci]
        w = 34.0 + 90.0 * d
        xc = r.uniform(-30, n + 30)
        lo, hi = max(int(xc - w / 2) - 2, 0), min(int(xc + w / 2) + 3, n)
        if hi <= lo:
            continue
        cols = np.arange(lo, hi, dtype=F32)[None, :]
        u = (cols - xc) / (w / 2.0)
        cyl = np.sqrt(np.clip(1 - u * u, 0, 1))
        a = np.clip((1 - np.abs(u)) * (w / 2.0) / 1.4 + 0.5, 0, 1)
        L = r.uniform(190.0, 420.0) * (0.7 + 0.5 * d)
        off = r.uniform(0, L)
        t = ((yy - off) % L)
        dn = np.minimum(t, L - t)
        kk = np.floor((yy - off) / L).astype(np.int64)
        seg = H.hash01(kk + ci * 997, seed + 5)
        ring = np.exp(-(dn / (3.5 + 2.5 * d)) ** 2)
        ridge = np.exp(-((dn - 8.0 - 6.0 * d) / (4.0 + 2.0 * d)) ** 2)
        tone = 0.28 + 0.58 * cyl - 0.62 * ring + 0.14 * ridge + 0.12 * (seg - 0.5) + 0.12 * streak[:, lo:hi] * (0.5 + 0.5 * cyl)
        col = H.ramp(np.clip(tone, 0, 1), jade)
        ym = r.random() * 0.8
        col = col * (1 - ym) + col * np.array([1.18, 1.05, 0.50], F32) * ym
        fog = (1 - d) * 0.55
        col = col * (0.50 + 0.50 * d) * (1 - fog) + _hx('#2a4a38')[None, None, :] * fog
        sub = img[:, lo:hi]
        sub[:] = sub * (1 - a[..., None]) + col * a[..., None]
        nodes = off + L * np.arange(-1, int(n / L) + 2)
        for yn in nodes:
            if -40 < yn < n + 40 and r.random() < 0.85:
                leaf_pos.append((xc + r.choice([-1, 1]) * w * 0.45, yn, d))
    lp = np.array(leaf_pos)
    tiles = _trim(_rot_tiles(_bamboo_leaf_master(), (150, 200, 260), tuple(range(0, 360, 20))))
    si = np.clip((lp[:, 2] * 3).astype(int), 0, 2)
    ti = si * 18 + r.integers(0, 18, len(lp))
    amp = (0.45 + 0.55 * lp[:, 2]).astype(F32)
    o = np.argsort(lp[:, 2], kind="stable")
    H.splat_rgba(img, tiles, ti[o], lp[o, 0], lp[o, 1], amp=amp[o])
    Ln = H.sstep(0.04, 0.80, H.lum(img))
    M, R, CC = _curves(Ln, (60.0, 200.0), (170.0, 40.0), (50.0, 24.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 88 lichen
# =========================================================================
def _lichen_master(S, stops, seed, ph=0.0):
    r = H.rng(seed)
    M = _mk(S)
    gx, gy = H.tile_xy(S)
    rr = np.hypot(gx, gy).astype(F32)
    th = np.arctan2(gy, gx).astype(F32)
    R0 = 0.44 * S
    p1, p2, p3 = r.uniform(0, 6.28, 3)
    Rt = R0 * (1 + 0.095 * np.sin(7 * th + p1) + 0.06 * np.sin(13 * th + p2) + 0.035 * np.sin(23 * th + p3))
    rho = (rr / Rt).astype(F32)
    disc = H.sstep(1.02, 0.97, rho)
    ringp = 7.5 + r.uniform(-0.5, 0.5)
    rings = 0.5 + 0.5 * np.cos(2 * np.pi * (rho * ringp + 0.05 * np.sin(5 * th + p2)))
    col = H.ramp(np.clip(rho, 0, 1).astype(F32), stops).astype(F32)
    g1 = _z(H.noise(S, max(2, S // 6), seed + 3))
    g2 = _z(H.noise(S, max(2, S // 3), seed + 4))
    lobe = np.cos(7 * th + p1) * H.sstep(0.62, 0.95, rho)
    shade = 1.0 + 0.20 * g1 + 0.10 * g2 + 0.20 * (rings - 0.5) + 0.12 * lobe
    col = col * shade[..., None]
    col = col * (1.0 - 0.30 * np.exp(-((rho - 0.12) / 0.12) ** 2))[..., None]
    rim = np.exp(-((rho - 0.985) / 0.035) ** 2)[..., None]
    col = col + rim * (0.16 + 0.10 * np.clip(-(gx * 0.55 + gy * 0.83) / R0, -1, 1)[..., None])
    _put(M, _hx('#2a2420'), np.exp(-((rho - 1.07) / 0.045) ** 2) * 0.33 * (rho > 1.0))
    _put(M, np.clip(col, 0, 1).astype(F32), disc)
    return M


@_f("wx_lichen_crust", "Lichen Crust",
    "Round lichen rosettes in yellow-green, orange and grey-green, lobed rims and crusty dark centres, overlapping on fine grey rock.")
def lichen_crust(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 88 Lichen Crust (v3, coordinator review 3: was cartoon hex patches with black outlines): 3 colourway rosette masters (lobed polar edge 7+13+23 harmonics, 7.5 concentric growth rings, 12-24 px granular texture, lobed-rim light, soft brown shadow instead of any outline) x 3 sizes x 8 rotations overlapping on a fine-grained grey rock ground with satellites; MAT
    n = N
    r = H.rng(seed)
    t = 0.50 + 0.09 * _z(H.fbm(n, seed + 1, cells=(6, 14, 30))) + 0.12 * _z(H.noise(n, 150, seed + 2)) + 0.10 * _z(H.noise(n, 210, seed + 3)) + 0.07 * _z(H.noise(n, 300, seed + 4))
    img = H.ramp(np.clip(t, 0, 1), [(0.0, '#4a4a48'), (0.5, '#74746f'), (1.0, '#a4a49e')]).astype(F32)
    img += (H.flake_mask(n, 0.010, seed + 5)[..., None] * 0.20).astype(F32) - (H.flake_mask(n, 0.010, seed + 6)[..., None] * 0.14).astype(F32)
    stops = [
        [(0.0, '#8a8420'), (0.5, '#c8cc3c'), (0.85, '#dcdc58'), (1.0, '#f0f4a0')],
        [(0.0, '#a84a0c'), (0.5, '#e07a1c'), (0.85, '#f4a030'), (1.0, '#ffd070')],
        [(0.0, '#566a52'), (0.5, '#8ea088'), (0.85, '#aebaa4'), (1.0, '#d4dcc8')],
    ]
    ms = [_lichen_master(300, stops[k], seed + 7 + k) for k in range(3)]
    angs = tuple(range(0, 360, 45))
    sm = _trim(sum([_rot_tiles(m, (62, 84), angs) for m in ms], []))
    fx, fy, fti = _scatter(n, 22, seed + 8, 6, 8, jit=0.5)
    kp = r.random(len(fx)) < 0.55
    H.splat_rgba(img, sm, fti[kp], fx[kp], fy[kp])
    tiles = _trim(sum([_rot_tiles(m, (115, 155, 205), angs) for m in ms], []))
    ex, ey, ti = _scatter(n, 12, seed + 9, 9, 8, jit=0.42)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=np.repeat(r.uniform(0.90, 1.08, (len(ex), 1)).astype(F32), 3, 1))
    img = _fine(img, seed + 44, 0.10)
    Ln = H.sstep(0.05, 0.85, H.lum(img))
    M, R, CC = _curves(Ln, (0.0, 30.0), (225.0, 120.0), (225.0, 100.0))
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 89 poppy
# =========================================================================
def _poppy_master(S=300):
    r = H.rng(13)
    M = _mk(S)
    c = S / 2.0
    for k in range(4):
        a = np.pi / 4 + k * np.pi / 2 + r.uniform(-0.15, 0.15)
        px, py = c + 0.15 * S * np.cos(a), c + 0.15 * S * np.sin(a)
        _blob(M, px, py, 0.30 * S, 0.27 * S, a, _hx('#7a0808'), _hx('#e8201a'), _hx('#ff9080'), 0.30, 1.4)
        polys = []
        for b in np.linspace(-0.9, 0.9, 11):
            p0 = np.array([c + 0.05 * S * np.cos(a), c + 0.05 * S * np.sin(a)])
            polys.append(np.stack([p0, p0 + 0.40 * S * np.array([np.cos(a + b * 0.8), np.sin(a + b * 0.8)])]))
        _strokes(M, polys, 1, _hx('#a00c0c'))
        _blob(M, c + 0.08 * S * np.cos(a), c + 0.08 * S * np.sin(a), 0.085 * S, 0.075 * S, a, _hx('#0a0202'), _hx('#2a0606'), None, 0.0, 1.0)
    for k in range(40):
        a = r.uniform(0, 6.2832)
        rr = r.uniform(0.11, 0.16) * S
        _blob(M, c + rr * np.cos(a), c + rr * np.sin(a), 2.8, 2.8, 0.0, _hx('#040404'), _hx('#202020'), _hx('#8a8a8a'), 0.3, 1.0)
    _blob(M, c, c, 0.075 * S, 0.075 * S, 0.0, _hx('#2a3a1a'), _hx('#6a8a48'), _hx('#c8e0a0'), 0.35, 1.0)
    _strokes(M, [np.stack([[c, c], [c + 0.075 * S * np.cos(b), c + 0.075 * S * np.sin(b)]]) for b in np.linspace(0, 6.2832, 10)[:-1]], 1, _hx('#101808'))
    return M


def _blades(n, rng, K, lens, w, col_rgb, canvas):
    x0 = rng.uniform(-20, n + 20, K)
    y0 = rng.uniform(0, n + 120, K)
    L = rng.uniform(lens[0], lens[1], K)
    lean = rng.normal(0, 0.28, K)
    bend = rng.normal(0, 0.30, K)
    ts = np.linspace(0, 1, 7)
    polys = []
    for k in range(K):
        a = lean[k] + bend[k] * ts
        px = x0[k] + L[k] * np.cumsum(np.sin(a)) / 7.0 * ts[-1] * 1.0
        py = y0[k] - L[k] * np.cumsum(np.cos(a)) / 7.0
        polys.append(np.round(np.stack([px, py], 1) * 4).astype(np.int32).reshape(-1, 1, 2))
    m = np.zeros((n, n), np.uint8)
    cv2.polylines(m, polys, False, 255, w, cv2.LINE_AA, 2)
    a = (m.astype(F32) / 255.0)[..., None]
    canvas[:] = canvas * (1 - a) + np.asarray(col_rgb, F32)[None, None, :] * a


@_f("wx_poppy_field", "Poppy Field",
    "Scattered scarlet poppies with crinkled petals and black centres standing in a thicket of layered green grass blades.")
def poppy_field(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 89 Poppy Field: 3 passes of ~2600 curved grass blades (dark/mid/light), ~120 four-petal poppy stamps (crinkle lines, black basal blotches, stamen ring, seed capsule) in 3 sizes x 6 rotations, 900 foreground blades; poppies CAN via a coverage mask
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(6, 14, 30)))
    img = H.ramp(np.clip(0.30 + 0.14 * z, 0, 1), [(0.0, '#06140a'), (0.5, '#0e2a12'), (1.0, '#1c4a1c')]).astype(F32).copy()
    _blades(n, r, 3000, (90, 230), 4, _hx('#14401a'), img)
    _blades(n, r, 2800, (80, 220), 4, _hx('#2c7a28'), img)
    _blades(n, r, 2400, (70, 200), 3, _hx('#78c040'), img)
    sizes, angs = (120, 150, 190), (0, 60, 120, 180, 240, 300)
    tiles = _trim(_rot_tiles(_poppy_master(), sizes, angs))
    ex, ey, ti = _scatter(n, 11, seed + 3, 3, 6, jit=0.5)
    kp = r.random(len(ex)) < 0.72
    ex, ey, ti = ex[kp], ey[kp], ti[kp]
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_tint(r, len(ex), 0.90, 1.08))
    mimg = np.zeros((n, n, 3), F32)
    ta = [np.concatenate([t[..., 3:4]] * 3 + [t[..., 3:4]], -1) for t in tiles]
    H.splat_rgba(mimg, ta, ti, ex, ey)
    _blades(n, r, 900, (50, 150), 3, _hx('#8ad04a'), img)
    Ln = H.sstep(0.03, 0.70, H.lum(img))
    M, R, CC = _curves(Ln, (20.0, 120.0), (150.0, 60.0), (80.0, 30.0))
    k = np.clip(mimg[..., 0], 0, 1) * 0.75
    M, R, CC = H.lerp(M, 216.0, k), H.lerp(R, 24.0, k), H.lerp(CC, 16.0, k)
    return _out(np.clip(img, 0, 1), M, R, CC)


# =========================================================================
# 90 venus flytrap
# =========================================================================
def _trap_master(S=340):
    r = H.rng(17)
    M = _mk(S)
    c = S / 2.0
    green, gl = _hx('#6a9a30'), _hx('#b8d868')
    _blob(M, c, c + 0.40 * S, 0.075 * S, 0.12 * S, 0.0, _hx('#2a4a14'), green, gl, 0.3, 1.0)
    _strokes(M, [np.array([[c, c + 0.28 * S], [c, c + 0.02 * S]])], 7, green * 0.85)
    for sg in (-1, 1):
        ex_, ey_ = c + sg * 0.19 * S, c - 0.03 * S
        ax_, ay_ = 0.165 * S, 0.34 * S
        tl = sg * 0.10
        for k in range(17):
            ph = np.radians(-85 + k * 10.6)
            ux, uy = sg * np.cos(ph), np.sin(ph)
            bx, by = ex_ + ax_ * ux * 1.0, ey_ + ay_ * uy
            nx, ny = ux / ax_, uy / ay_
            nn = np.hypot(nx, ny)
            nx, ny = nx / nn, ny / nn
            ln = 0.11 * S * (0.8 + 0.2 * np.cos(ph * 1.6))
            tx, ty = bx + nx * ln, by + ny * ln
            _tri(M, (bx - ny * 3.6, by + nx * 3.6), (bx + ny * 3.6, by - nx * 3.6), (tx, ty), green * 0.95)
            _strokes(M, [np.array([[bx + nx * ln * 0.55, by + ny * ln * 0.55], [tx, ty]])], 1, gl)
        _blob(M, ex_, ey_, ax_, ay_, 0.0, _hx('#4a7a1c'), green, gl, 0.25, 1.2)
        _blob(M, ex_ - sg * 0.004 * S, ey_, ax_ * 0.84, ay_ * 0.88, 0.0, _hx('#5a0610'), _hx('#d4141e'), _hx('#ff7a70'), 0.45, 1.2)
        polys = [np.stack([[c + sg * 0.025 * S, c + 0.02 * S * t], [ex_ + sg * ax_ * 0.8 * np.cos(ph2), ey_ + ay_ * 0.8 * np.sin(ph2)]])
                 for t, ph2 in zip(np.linspace(-1, 1, 10), np.radians(np.linspace(-75, 75, 10)))]
        _strokes(M, polys, 1, _hx('#8a0a16'))
        for hy in (-0.10, 0.04, 0.16):
            hx = ex_ - sg * 0.02 * S
            _strokes(M, [np.array([[hx, c + hy * S], [hx - sg * 0.015 * S, c + hy * S - 0.05 * S]])], 2, _hx('#200404'))
    _strokes(M, [np.array([[c, c - 0.30 * S], [c, c + 0.30 * S]])], 4, green * 0.8)
    return M


@_f("wx_venus_trap", "Venus Flytrap Teeth",
    "Rows of open flytrap lobes with blood-red veined interiors, fine trigger hairs and fringes of long comb-like green teeth.")
def venus_trap(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 90 Venus Flytrap Teeth: open-trap master (two kidney lobes, 17 AA comb teeth per lobe with pale tips, red interior gradient, 10 dark veins, 3 trigger hairs per lobe, midrib, leaf blade), 3 sizes x 6 small rotations on a staggered row grid over dark sphagnum bog; WET
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(6, 14, 30)))
    img = H.ramp(np.clip(0.30 + 0.14 * z + 0.05 * _z(H.noise(n, 150, seed + 2)), 0, 1), [(0.0, '#080e06'), (0.5, '#142010'), (1.0, '#28401a')]).astype(F32).copy()
    img = img + (H.flake_mask(n, 0.003, seed + 3)[..., None] * _hx('#a02018') * 0.6).astype(F32)
    tiles = _trim(_rot_tiles(_trap_master(), (150, 185, 225), (-25, -15, -5, 5, 15, 25)))
    ex, ey, ti = _scatter(n, 13, seed + 4, 3, 6, jit=0.25)
    H.splat_rgba(img, tiles, ti, ex, ey, tint=_tint(r, len(ex), 0.90, 1.08))
    img = _fine(img, seed + 44, 0.08)
    Ln = H.sstep(0.03, 0.75, H.lum(img))
    M, R, CC = _curves(Ln, (0.0, 72.0), (98.0, 14.0), (38.0, 16.0))  # [S20 story-split] venus trap: wet-lacquer deck
    return _out(np.clip(img, 0, 1), M, R, CC)
