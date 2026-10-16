# -*- coding: utf-8 -*-
"""MORPHO chapter (wx_ 21-70): structural colour in feathers, shells, stones and films. NO insects.

[S20 2026-10-12 owner: Fractured Wilds rebuild] one function per finish; each writes its OWN
structure and its OWN spec story. Only plumbing comes from helpers.
"""
from __future__ import annotations

import numpy as np
import cv2

from . import helpers as H

F32 = np.float32
N = H.N

FINISHES = []


def _f(fid, name, desc):
    def deco(fn):
        FINISHES.append((fid, name, desc, fn))
        return fn
    return deco


def _z(f):
    # standardise a field to zero mean / unit std (fbm output is neither)
    f = np.asarray(f, F32)
    return ((f - f.mean()) / (f.std() + F32(1e-6))).astype(F32)


def _strands(u, v, p0, steps, h):
    """Bidirectional streamline paths (K, 2*steps+1, 2) through field (u, v)."""
    fw = H.trace(u, v, p0, steps, h)
    bw = H.trace(-u, -v, p0, steps, h)
    return np.concatenate([bw[:, ::-1][:, :-1], fw], 1)


def _rot_tiles(master, sizes, angs):
    """Premultiplied RGBA master -> rotated copies; tile index = size_i * len(angs) + ang_i."""
    out = []
    for sz in sizes:
        t0 = cv2.resize(master, (sz, sz), interpolation=cv2.INTER_AREA if sz < master.shape[0] else cv2.INTER_LINEAR)
        c = (sz - 1) / 2.0
        for a in angs:
            Mx = cv2.getRotationMatrix2D((c, c), float(a), 1.0)
            out.append(cv2.warpAffine(t0, Mx, (sz, sz), flags=cv2.INTER_LINEAR, borderValue=0))
    return out


def _curves(Ln, M, R, CC):
    return H.lerp(M[0], M[1], Ln), H.lerp(R[0], R[1], Ln), H.lerp(CC[0], CC[1], Ln)


def _out(rgb, M, R, CC):
    return H.finish_out(np.clip(rgb, 0, 1).astype(F32), H.spec_pack(np.clip(M, 0, 255), np.clip(R, 0, 255), CC))


def _scalelat(n, w, h, warp, seed, stagger=0.5, wcells=(4, 8, 16)):
    """Warped staggered row lattice. Returns row, col, u (-1..1 across), vv (0..1 down), cr, cr2 (cell randoms), Sx, Sy."""
    X, Y = H.xy(n)
    S = X + warp * _z(H.fbm(n, seed + 101, cells=wcells, gain=0.7))
    T = Y + warp * _z(H.fbm(n, seed + 102, cells=wcells, gain=0.7))
    row, col, lx, ly = H.cells_rows(S, T, w, h, stagger)
    cr = H.cellhash(row, col, seed)
    cr2 = H.cellhash(row, col, seed + 1)
    return row, col, lx / (w * 0.5), (ly + h * 0.5) / h, cr, cr2, S, T
# -------------------------------------------------------------------------
# FEATHERS 21-32
# -------------------------------------------------------------------------
def _eye_master(S=256):
    gx, gy = H.tile_xy(S)
    rr = np.hypot(gx / 0.78, gy * 0.92) / (S * 0.5)
    col = H.ramp(np.clip(rr, 0, 1), [(0.0, '#0a1250'), (0.10, '#16227e'), (0.20, '#08104a'), (0.23, '#0e9aa0'), (0.34, '#17c4b4'),
                                     (0.42, '#0b7580'), (0.45, '#9a6a22'), (0.56, '#c28a38'), (0.62, '#e6cf6a'), (0.66, '#3a2410'),
                                     (0.74, '#1c3a22'), (1.0, '#2a6a34')])
    hl = np.exp(-(((gx + 0.10 * S) ** 2 + (gy + 0.07 * S) ** 2) / (2 * (0.045 * S) ** 2))) * (rr < 0.22)
    col = col + hl[..., None] * 0.55
    al = H.sstep(0.82, 0.72, rr)
    out = np.zeros((S, S, 4), F32)
    out[..., :3] = col * al[..., None]
    out[..., 3] = al
    return out


@_f("wx_peacock_ocelli", "Peacock Ocelli",
    "Eye-spots ringed in bronze, teal and navy scattered over a flow of green and gold barbs, peacock-tail style.")
def peacock_ocelli(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 21 Peacock Ocelli: barb streamlines (green->gold, 2 tones per barb) + 49 elliptical eye-spot stamps (navy heart, teal, bronze, gold, dark rings)
    n = N
    m = 512
    r = H.rng(seed)
    ang = 1.15 + 0.55 * _z(H.fbm(m, seed + 1, cells=(2, 3, 5), gain=0.7))
    u = np.cos(ang).astype(F32)
    v = np.sin(ang).astype(F32)
    hs = _z(H.fbm(m, seed + 2, cells=(3, 6, 12), gain=0.7))
    cvs = None
    for K in (52000, 52000):
        p0 = r.random((K, 2)).astype(F32) * n
        path = _strands(u, v, p0, 5, 5.0)
        hq = np.clip(0.5 + 0.30 * H.sample(hs, p0[:, 0] / 4.0, p0[:, 1] / 4.0), 0, 1) * 255
        val = r.uniform(70, 150, K)
        for seg, vv_ in ((slice(0, 6), val), (slice(5, 11), np.minimum(val + 95, 255))):
            cvs = H.lines3(n, path[:, seg], np.stack([vv_, hq, np.zeros(K)], 1), 1, canvas=cvs)
    V = np.maximum(H.u8f(cvs[..., 0]), 0.10)
    W = H.u8f(cvs[..., 1])
    rgb = H.hsv(0.34 - 0.22 * W + 0.03 * V, 0.90 - 0.45 * V ** 3, 0.10 + 0.95 * V ** 1.2)
    tiles = _rot_tiles(_eye_master(), (150, 190), (-10, -5, 0, 5, 10))
    g = 7
    sp = n / g
    gi, gj = np.meshgrid(np.arange(g), np.arange(g))
    ex = ((gi + 0.5 + r.uniform(-0.28, 0.28, gi.shape) + 0.5 * (gj & 1)) * sp).ravel()
    ey = ((gj + 0.5 + r.uniform(-0.28, 0.28, gi.shape)) * sp).ravel()
    ti = (r.integers(0, 2, ex.size) * 5 + r.integers(0, 5, ex.size))
    o = np.argsort(ey)
    img = np.ascontiguousarray(rgb, F32).copy()
    H.splat_rgba(img, tiles, ti[o], ex[o], ey[o])
    Ln = H.sstep(0.04, 0.8, H.lum(img))
    M, R, CC = _curves(Ln, (110.0, 255.0), (120.0, 30.0), (60.0, 16.0))
    return _out(img, M, R, CC)


@_f("wx_gorget_flash", "Hummingbird Gorget",
    "Rows of tiny overlapping scalloped throat feathers on black, flashing magenta, ruby and orange-gold in big patches.")
def gorget_flash(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 22 Hummingbird Gorget (v2, coordinator review 2): 26x18 px overlapping scalloped feather rows (dark gaps + lit tip rims + tucked tops), strong coherent REGIONAL flash patches (ruby core -> magenta -> black fade, gold hot spots) so feathers in a patch flash together
    n = N
    row, col, u, vv, cr, cr2, S, T = _scalelat(n, 26.0, 18.0, 40.0, seed, 0.5, (3, 6, 12))
    au = np.abs(u)
    edge = 0.88 - 0.50 * u * u
    body = H.sstep(edge + 0.07, edge - 0.04, vv)
    rim = np.exp(-((vv - edge + 0.07) / 0.10) ** 2) * body
    cover = 0.30 + 0.70 * H.sstep(0.0, 0.45, vv)
    zf = _z(H.fbm(n, seed + 2, cells=(3, 5, 9), gain=0.7)) + 0.55 * _z(H.fbm(n, seed + 5, cells=(6, 10, 18), gain=0.6))
    patch = H.sstep(-0.75, 1.0, zf)
    flare = H.sstep(0.9, 1.9, zf)
    hue = H.ramp(np.clip(0.12 + 0.46 * patch + 0.22 * flare + 0.10 * (cr - 0.5), 0, 1),
                 [(0.0, '#6a0a62'), (0.22, '#d412b8'), (0.42, '#ff1f8a'), (0.62, '#ff1838'), (0.82, '#ff6a20'), (1.0, '#ffd048')])
    lit = body * cover * (0.50 + 0.50 * rim + 0.25 * (cr2 - 0.5)) * (0.35 + 0.65 * (1.0 - au ** 2))
    lum = 0.03 + 1.10 * patch ** 1.3 * lit + 0.09 * body * (1.0 - patch) * (0.5 + 0.5 * rim)
    rgb = hue * lum[..., None] + 0.012
    Ln = H.sstep(0.03, 0.7, H.lum(rgb))
    M, R, CC = _curves(Ln, (40.0, 255.0), (150.0, 6.0), (60.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_starling_spangle", "Starling Spangles",
    "Oil-black plumage glossed purple and green, spangled with a small white V at every feather tip.")
def starling_spangle(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 23 Starling Spangles: 46x32 feather lattice, purple<->green gloss by field, white V-tip spangle per feather
    n = N
    row, col, u, vv, cr, cr2, S, T = _scalelat(n, 46.0, 32.0, 24.0, seed)
    edge = 0.86 - 0.36 * u * u
    body = H.sstep(edge + 0.05, edge - 0.04, vv)
    hf = _z(H.fbm(n, seed + 2, cells=(3, 6, 14), gain=0.7))
    ph = np.clip(0.5 + 0.28 * hf + 0.30 * (vv - 0.5) + 0.20 * (cr - 0.5), 0, 1)
    gloss = H.ramp(ph, [(0.0, '#6a22b8'), (0.35, '#4a28a8'), (0.5, '#1a6a78'), (0.7, '#18a070'), (1.0, '#34d890')])
    sheen = np.exp(-((vv - 0.42) / 0.24) ** 2) * body
    lum = 0.07 + 0.80 * sheen * (0.55 + 0.45 * cr2) + 0.12 * body
    base = gloss * lum[..., None]
    dy = edge - vv
    wl = 0.60 * (1.0 - dy / 0.30)
    vm = H.sstep(0.03, 0.06, dy) * (1.0 - H.sstep(0.26, 0.30, dy)) * (1.0 - H.sstep(wl - 0.06, wl, np.abs(u))) * (cr2 > 0.22) * body
    rgb = base * (1 - vm)[..., None] + vm[..., None] * (H.hexrgb('#f4f0e2') * (0.82 + 0.18 * cr)[..., None])
    Ln = H.sstep(0.03, 0.7, H.lum(rgb))
    M, R, CC = _curves(Ln, (60.0, 200.0), (130.0, 56.0), (70.0, 20.0))
    return _out(rgb, M, R, CC)


@_f("wx_pigeon_collar", "Pigeon Neck Shimmer",
    "Soft overlapping neck feathers shifting between slate, emerald and violet in broad shimmering bands.")
def pigeon_collar(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 24 Pigeon Neck Shimmer: 66x44 soft feather rows, hue flip field (slate->emerald->violet) in warped broad bands
    n = N
    row, col, u, vv, cr, cr2, S, T = _scalelat(n, 66.0, 44.0, 40.0, seed, wcells=(3, 6, 10))
    edge = 0.86 - 0.30 * u * u
    body = H.sstep(edge + 0.09, edge - 0.07, vv)
    band = _z(H.fbm(n, seed + 3, cells=(2, 3, 5), gain=0.6)) + 0.9 * np.sin(T / 190.0 + 1.5 * _z(H.fbm(n, seed + 4, cells=(2, 3), gain=0.6)))
    t = np.clip(0.5 + 0.27 * band + 0.14 * (cr - 0.5), 0, 1)
    col3 = H.ramp(t, [(0.0, '#46566a'), (0.28, '#1f9a6c'), (0.5, '#34d68e'), (0.74, '#7a50d6'), (1.0, '#a860ee')])
    shaft = np.exp(-(u / 0.05) ** 2) * H.sstep(0.1, 0.5, vv) * body
    lum = 0.30 + 0.62 * body * (0.55 + 0.45 * np.cos((vv - 0.3) * 2.6)) + 0.14 * shaft
    rgb = col3 * (lum * (0.80 + 0.20 * cr2) * (0.30 + 0.70 * body))[..., None] + H.hexrgb('#1a2028') * (1 - body)[..., None] * 0.7
    Ln = H.sstep(0.03, 0.7, H.lum(rgb))
    M, R, CC = _curves(Ln, (120.0, 255.0), (110.0, 30.0), (50.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_mallard_bar", "Mallard Speculum",
    "Overlapping brown wing feathers, with a band of iridescent blue-violet feathers edged in white and black running across.")
def mallard_bar(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 25 Mallard Speculum: 56x36 rounded wing-feather rows (barbed vanes, pale rims); every 8th row pair = iridescent blue-violet speculum feathers, white-rimmed, black row below
    n = N
    row, col, u, vv, cr, cr2, S, T = _scalelat(n, 56.0, 36.0, 26.0, seed)
    edge = 0.90 - 0.34 * u * u
    body = H.sstep(edge + 0.05, edge - 0.04, vv)
    rim = np.exp(-((vv - edge + 0.05) / 0.06) ** 2) * body
    au = np.abs(u)
    barb = 0.5 + 0.5 * np.sin(6.2832 * (vv * 8.0 - au * 4.0) + cr * 6.0)
    shaft = np.exp(-(u / 0.05) ** 2) * H.sstep(0.05, 0.3, vv) * body
    rr = np.mod(row, 8)
    is_spec = ((rr == 5) | (rr == 6)).astype(F32)
    is_blk = (rr == 7).astype(F32)
    bt = np.clip(0.30 + 0.30 * barb + 0.20 * (cr - 0.5) + 0.20 * (1.0 - vv), 0, 1)
    brown = H.ramp(bt, [(0.0, '#241408'), (0.5, '#6a4a2e'), (1.0, '#a8845a')])
    brown = brown + shaft[..., None] * 0.10 + rim[..., None] * H.hexrgb('#c8b08a') * 0.35
    st = np.clip(0.50 + 0.22 * np.sin(u * 2.4 + cr * 6.0) + 0.45 * (vv - 0.45) + 0.12 * (barb - 0.5), 0, 1)
    spc = H.ramp(st, [(0.0, '#0c1890'), (0.45, '#2858f0'), (0.78, '#6a50e8'), (1.0, '#b498ff')]) * (0.55 + 0.55 * barb)[..., None]
    spc = spc + rim[..., None] * H.hexrgb('#f4f2ee') * 0.85 + shaft[..., None] * 0.18
    blk = H.hexrgb('#0e0e12') * (0.6 + 0.8 * barb)[..., None] + rim[..., None] * H.hexrgb('#f0eee8') * 0.8
    gap = H.hexrgb('#120a05')
    mix = np.zeros_like(brown)
    mix = brown * (1 - is_spec - is_blk)[..., None] + spc * is_spec[..., None] + blk * is_blk[..., None]
    rgb = mix * body[..., None] + gap * (1 - body)[..., None]
    wsp = H.blur((is_spec * body).astype(F32), 2.5)
    Ln = H.sstep(0.03, 0.7, H.lum(rgb))
    M, R, CC = _curves(Ln, (10.0, 150.0), (235.0, 80.0), (225.0, 70.0))
    M = H.lerp(M, 150.0 + 105.0 * Ln, wsp)
    R = H.lerp(R, 78.0 - 62.0 * Ln, wsp)
    CC = H.lerp(CC, 62.0 - 44.0 * Ln, wsp)
    return _out(rgb, M, R, CC)


@_f("wx_magpie_gloss", "Magpie Tail Gloss",
    "Long slender black tail feathers laid in sweeping overlap, glossed blue, green and violet along every vane.")
def magpie_gloss(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 26 Magpie Tail Gloss: ~450 slender 380-560 px tail feathers drawn painter-ordered (8 gloss segments navy->blue->green->violet, bright core, silver shaft, ~20 barb lines/side)
    n = N
    r = H.rng(seed)
    img = np.zeros((n, n, 3), F32) + H.hexrgb('#05070b')
    a0 = np.deg2rad(-3.0)
    d = np.array([np.cos(a0), np.sin(a0)])
    pp = np.array([-d[1], d[0]])
    I, J = np.meshgrid(np.arange(-3, 9), np.arange(-30, 32))
    I = I.ravel() + r.uniform(-0.35, 0.35, I.size)
    J = J.ravel() + r.uniform(-0.35, 0.35, I.size)
    px = n * 0.5 + I * 300.0 * d[0] + J * 50.0 * pp[0]
    py = n * 0.5 + I * 300.0 * d[1] + J * 50.0 * pp[1]
    ok = (px > -360) & (px < n + 360) & (py > -360) & (py < n + 360)
    px, py = px[ok], py[ok]
    K = len(px)
    o = r.permutation(K)
    px, py = px[o], py[o]
    Ls = r.uniform(380, 560, K)
    HWs = r.uniform(22, 32, K)
    angs = a0 + r.normal(0.0, 0.07, K) + 0.06 * np.sin(py / 400.0)
    cb = r.uniform(0.80, 1.20, K)
    t0 = r.uniform(-0.12, 0.12, K)
    stops = [(0.0, '#0a1230'), (0.22, '#123a9c'), (0.45, '#1a78d0'), (0.62, '#12a888'), (0.80, '#48b860'), (1.0, '#8a38c8')]
    lut = H.ramp(np.linspace(0, 1, 64).astype(F32), stops)
    SH = 3
    SC = 8.0

    def P(a):
        return np.round(a * SC).astype(np.int32)

    tt = np.linspace(0.0, 1.0, 12)
    prof = np.sin(np.pi * np.clip(tt * 0.97 + 0.015, 0, 1) ** 0.62) ** 0.55
    for k in range(K):
        c, s_ = np.cos(angs[k]), np.sin(angs[k])
        L = Ls[k]
        hw = HWs[k] * prof
        ax = px[k] + (tt - 0.5) * L * c
        ay = py[k] + (tt - 0.5) * L * s_
        nx, ny = -s_, c
        up = np.stack([ax + nx * hw, ay + ny * hw], 1)
        lo = np.stack([ax - nx * hw, ay - ny * hw], 1)
        for q in range(0, 11, 1):
            tm = np.clip(0.5 * (tt[q] + tt[q + 1]) + t0[k], 0, 0.999)
            col = lut[int(tm * 63)] * cb[k] * 0.42
            poly = np.concatenate([up[q:q + 2], lo[q:q + 2][::-1]])
            cv2.fillPoly(img, [P(poly)], tuple(float(v) for v in col), cv2.LINE_AA, SH)
            cc = np.concatenate([up[q:q + 2] * 0.22 + 0.78 * np.stack([ax[q:q + 2], ay[q:q + 2]], 1),
                                 (lo[q:q + 2] * 0.22 + 0.78 * np.stack([ax[q:q + 2], ay[q:q + 2]], 1))[::-1]])
            cv2.fillPoly(img, [P(cc)], tuple(float(v) for v in np.minimum(col * 3.1 + 0.03, 1.0)), cv2.LINE_AA, SH)
        for si in (-1, 1):
            for b in range(1, 46):
                tb = 0.04 + 0.92 * b / 46.0
                i0 = min(int(tb * 11), 10)
                f = tb * 11 - i0
                bx = ax[i0] * (1 - f) + ax[i0 + 1] * f
                by = ay[i0] * (1 - f) + ay[i0 + 1] * f
                w_ = hw[i0] * (1 - f) + hw[i0 + 1] * f
                ex = bx + nx * si * w_ * 1.05 + c * 12.0
                ey = by + ny * si * w_ * 1.05 + s_ * 12.0
                tm = np.clip(tb + t0[k], 0, 0.999)
                col = lut[int(tm * 63)] * cb[k] * (1.9 if (b & 1) else 0.30)
                cv2.line(img, (int(bx * SC), int(by * SC)), (int(ex * SC), int(ey * SC)), tuple(float(v) for v in np.minimum(col, 1.0)), 1, cv2.LINE_AA, SH)
        cv2.polylines(img, [P(np.stack([ax, ay], 1))], False, (0.62, 0.68, 0.78), 1, cv2.LINE_AA, SH)
    rgb = np.clip(img * (0.9 + 0.2 * _z(H.fbm(n, seed + 3, cells=(4, 8, 16), gain=0.6)))[..., None], 0, 1).astype(F32)
    Ln = H.sstep(0.03, 0.7, H.lum(rgb))
    M, R, CC = _curves(Ln, (120.0, 255.0), (90.0, 8.0), (50.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_raven_sheen", "Raven Night Sheen",
    "Black feathers with visible barbs and a rachis, broad blue-violet sheen bands sweeping across the whole plumage.")
def raven_sheen(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 27 Raven Night Sheen (v2, coordinator review 2): 54x92 px pointed feather lattice with 12 px diagonal barbs + rachis, diagonal broad blue-violet sheen bands (520 px period, warped) gating the barbs so the sheen sweeps ACROSS feathers; dead-black between bands
    n = N
    X, Y = H.xy(n)
    row, col, u, vv, cr, cr2, S, T = _scalelat(n, 44.0, 76.0, 22.0, seed, 0.5, (3, 6, 12))
    au = np.abs(u)
    edge = 0.93 - 0.50 * au ** 1.4
    body = H.sstep(edge + 0.04, edge - 0.03, vv) * H.sstep(1.0, 0.92, au)
    ph = (vv * 76.0 - 1.3 * au * 22.0) / 12.0 + cr * 3.0
    barb = 0.5 + 0.5 * np.cos(6.2832 * ph)
    shaft = np.exp(-(u / 0.045) ** 2) * (vv < edge)
    zw = _z(H.fbm(n, seed + 2, cells=(2, 3, 5), gain=0.7))
    bd = 0.5 + 0.5 * np.cos(6.2832 * (0.60 * X + 0.80 * Y) / 430.0 + 1.5 * zw)
    sm = H.sstep(0.30, 0.90, bd)
    sh = np.clip(0.25 + 0.55 * sm + 0.25 * (cr2 - 0.5), 0, 1)
    sheen = H.ramp(sh, [(0.0, '#1c2a9a'), (0.4, '#3e46d8'), (0.75, '#8668f0'), (1.0, '#cbb8ff')])
    tipg = np.exp(-((vv - edge + 0.20) / 0.22) ** 2)
    shade = 0.55 + 0.45 * H.sstep(0.0, 0.12, vv)
    base = H.hexrgb('#161d48') * (0.12 + 1.10 * barb)[..., None]
    gain = (0.30 + 0.70 * sm) * (0.06 + 0.94 * barb ** 1.4) * (0.5 + 0.5 * tipg) * (0.35 + 0.65 * sm)
    col = (base + sheen * gain[..., None] * 1.25 + (shaft * (0.4 + 0.6 * sm) * 0.9)[..., None] * H.hexrgb('#4a5aa8')) * shade[..., None]
    rgb = col * body[..., None] + H.hexrgb('#02030a') * (1.0 - body)[..., None]
    Ln = H.sstep(0.03, 0.55, H.lum(rgb))
    M, R, CC = _curves(Ln, (20.0, 150.0), (200.0, 70.0), (180.0, 45.0))
    return _out(rgb, M, R, CC)


@_f("wx_kingfisher_streak", "Kingfisher Streak",
    "Cobalt and turquoise feather streaks with fine white shaft lines, flaring into warm orange flank patches.")
def kingfisher_streak(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 28 Kingfisher Streak: 30x84 tall pointed feather lattice (staggered), cobalt->turquoise->pale tip gradient, bright rachis line, diagonal barb stripes, orange flank patches switching per feather
    n = N
    row, col, u, vv, cr, cr2, S, T = _scalelat(n, 30.0, 84.0, 30.0, seed, wcells=(3, 6, 12))
    au = np.abs(u)
    edge = 0.95 - 0.55 * au ** 1.5
    body = H.sstep(edge + 0.03, edge - 0.03, vv)
    rimm = np.exp(-((vv - edge + 0.03) / 0.04) ** 2) * body
    barb = 0.5 + 0.5 * np.sin(6.2832 * (vv * 15.0 - au * 5.0) + cr * 6.0)
    shaft = np.exp(-(u / 0.07) ** 2) * H.sstep(0.05, 0.25, vv) * body
    og = _z(H.fbm(n, seed + 3, cells=(2, 3, 5), gain=0.7))
    om = H.sstep(0.35, 0.85, og + 0.9 * (cr - 0.5))
    tt = np.clip(vv / np.maximum(edge, 0.3), 0, 1)
    lum = 0.42 + 0.58 * barb * (0.55 + 0.45 * (1.0 - au))
    blue = H.ramp(np.clip(tt * 0.9 + 0.1 * (cr2 - 0.5), 0, 1), [(0.0, '#06185e'), (0.35, '#1048c8'), (0.65, '#1a9ce0'), (0.88, '#2cd8d8'), (1.0, '#a8f4f0')])
    orange = H.ramp(np.clip(tt * 0.9 + 0.1 * (cr2 - 0.5), 0, 1), [(0.0, '#4a1004'), (0.35, '#b83a0a'), (0.65, '#ee7a14'), (0.88, '#ffb040'), (1.0, '#ffe0a0')])
    c3 = blue * (1 - om)[..., None] + orange * om[..., None]
    rgb = c3 * lum[..., None] + (shaft * 0.75)[..., None] * H.hexrgb('#f4fcff') + (rimm * 0.30)[..., None] * c3
    rgb = rgb * body[..., None] + H.hexrgb('#050b24') * (1 - body)[..., None]
    Ln = H.sstep(0.04, 0.8, H.lum(rgb))
    M, R, CC = _curves(Ln, (120.0, 226.0), (112.0, 14.0), (64.0, 16.0))
    return _out(rgb, M, R, CC)


def _crescent_master(S=256):
    gx, gy = H.tile_xy(S)
    outer = np.hypot(gx, gy) / (S * 0.47)
    inner = np.hypot(gx, gy + 0.20 * S) / (S * 0.40)
    cres = H.sstep(1.0, 0.92, outer) * H.sstep(0.97, 1.05, inner)
    t = np.clip(0.15 + 0.85 * np.hypot(gx, gy + 0.2 * S) / (S * 0.5), 0, 1)
    col = H.ramp(t, [(0.0, '#05202e'), (0.3, '#0a7088'), (0.6, '#18d8c8'), (0.85, '#60ffe0'), (1.0, '#c8fff4')])
    ang = np.arctan2(gy + 0.20 * S, gx + 1e-3)
    stripes = 0.62 + 0.38 * np.sin(ang * 58.0)
    inner2 = np.hypot(gx, gy + 0.10 * S) / (S * 0.30)
    c2 = H.sstep(0.96, 0.88, inner2) * H.sstep(0.80, 0.88, np.hypot(gx, gy + 0.22 * S) / (S * 0.27))
    col = col * stripes[..., None] + c2[..., None] * H.hexrgb('#30c0ff') * 0.5 * (0.7 + 0.3 * np.sin(ang * 44.0))[..., None]
    al = np.clip(cres + c2 * 0.9, 0, 1)
    out = np.zeros((S, S, 4), F32)
    out[..., :3] = col * al[..., None]
    out[..., 3] = al
    return out.astype(F32)


@_f("wx_bird_of_paradise", "Bird-of-Paradise Shield",
    "Velvet-black plumage carrying a repeating glowing teal crescent breast shield with a smaller shield inside.")
def bird_of_paradise(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 29 Bird-of-Paradise Shield: ultra-matte velvet pile with 16-32 px barb ridges + 52 nested crescent shield stamps (radial barb striations, electric teal), black MAT / shield CHR
    n = N
    r = H.rng(seed)
    pile = 0.5 + 0.5 * _z(H.fbm(n, seed + 1, cells=(300, 700, 1400), gain=0.8))
    ridge = 0.5 + 0.5 * _z(H.fbm(n, seed + 7, cells=(48, 96, 160), gain=0.8))
    reg = _z(H.fbm(n, seed + 2, cells=(3, 6, 12), gain=0.6))
    ground = (0.30 + 0.80 * pile * (0.65 + 0.7 * ridge)) * (1 + 0.15 * reg)
    rgb = (H.hexrgb('#10131a')[None, None, :] * ground[..., None]).astype(F32)
    rgb = rgb + H.hexrgb('#0a1a2c')[None, None, :] * (0.45 + 0.55 * ridge)[..., None]
    tiles = _rot_tiles(_crescent_master(), (150, 184, 220), (-22, -11, 0, 11, 22))
    g = 8
    sp = n / g
    gi, gj = np.meshgrid(np.arange(g), np.arange(g))
    ex = ((gi + 0.5 + r.uniform(-0.25, 0.25, gi.shape) + 0.5 * (gj & 1)) * sp).ravel()
    ey = ((gj + 0.5 + r.uniform(-0.25, 0.25, gi.shape)) * sp).ravel()
    ti = r.integers(0, 3, ex.size) * 5 + r.integers(0, 5, ex.size)
    o = np.argsort(ey)
    img = np.ascontiguousarray(rgb, F32).copy()
    H.splat_rgba(img, tiles, ti[o], ex[o], ey[o])
    shield = H.blur(np.clip((H.lum(img) - 0.12) * 4.0, 0, 1).astype(F32), 1.5)
    Ln = H.sstep(0.05, 0.8, H.lum(img))
    M = H.lerp(0.0, 255.0, shield * (0.5 + 0.5 * Ln))
    R = H.lerp(232.0 - 50.0 * ridge, 6.0, shield)
    CC = H.lerp(255.0, 16.0, shield)
    return _out(img, M, R, CC)


@_f("wx_cassowary_wattle", "Cassowary Wattle Skin",
    "Wrinkled bare neck skin with fine papillae and long folds, blushing smoothly from cobalt blue through violet to scarlet red.")
def cassowary_wattle(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 30 Cassowary Wattle Skin (v2, coordinator review 2): continuous blue->violet->red gradient (no halves), 13 px papillae domes everywhere, long folds (lam 34/62) + fine creases (lam 12), relief shading + wet ridge highlights
    n = N
    X, Y = H.xy(n)
    wA = _z(H.fbm(n, seed + 1, cells=(5, 10, 20), gain=0.7))
    wB = _z(H.fbm(n, seed + 2, cells=(6, 12, 24), gain=0.7))
    zg = _z(H.fbm(n, seed + 3, cells=(2, 3, 5), gain=0.7))
    g = np.clip(0.5 + 0.20 * zg + 0.30 * np.sin(X / 330.0 + Y / 520.0 + 0.8 * wA * 0.4), 0, 1)
    jit = H.ups(np.ascontiguousarray(_z(H.noise(512, 150, seed + 4)), F32), n)

    def fam(a, lam, warp, cw, ws, mcells, thr, sd, soft=0.3):
        xr = X * np.cos(a) + Y * np.sin(a)
        ph = (xr + warp * ws + 0.05 * lam * jit) / F32(lam)
        d = np.abs(ph - np.rint(ph))
        pres = H.sstep(thr - soft, thr + soft, H.ups(np.ascontiguousarray(_z(H.noise(512, mcells, sd)), F32), n))
        return (np.exp(-(d / F32(cw)) ** 2) * pres).astype(F32)

    f1 = fam(0.04, 34.0, 26.0, 0.14, wA, 10, -0.55, seed + 10)
    f2 = fam(0.18, 62.0, 34.0, 0.12, wB, 8, -0.2, seed + 11)
    f3 = fam(1.35, 12.0, 6.0, 0.18, wA, 60, -0.2, seed + 12, soft=0.4)
    C_ = np.minimum(1.0, f1 + 0.8 * f2 + 0.35 * f3).astype(F32)
    d_, lab_, sx_, sy_ = H.voronoi(n, H.jitter_pts(n, 13, seed + 20, 0.9, 6))
    hp = H.hash01((lab_ - 1).astype(np.int64), seed + 21)
    pap = np.clip(1.0 - d_ / (5.2 + 2.2 * hp), 0, 1) ** 0.7
    hgt = -(f1 + 0.8 * f2 + 0.35 * f3) + 0.3 * (0.5 + 0.5 * np.sin((X + 50.0 * wA) / 70.0)) + 0.60 * pap * (1.0 - 0.6 * C_)
    relief = H.emboss(H.blur(hgt.astype(F32), 1.0), 2.6)
    ao = H.blur(C_, 3.0)
    tb = np.clip(0.58 - 0.30 * C_ - 0.10 * ao + 0.38 * relief + 0.04 * H.grain(n, seed + 5), 0, 1)
    hc = H.ramp(g, [(0.0, '#0a22b0'), (0.28, '#2a5af0'), (0.50, '#8a2ec4'), (0.72, '#e0204e'), (1.0, '#ff4a30')])
    rgb = hc * (0.30 + 1.05 * tb)[..., None]
    hl = H.sstep(0.18, 0.7, relief) * 0.40
    rgb = np.clip(rgb + hl[..., None] * 0.9, 0, 1).astype(F32)
    Ln = H.sstep(0.04, 0.8, H.lum(rgb))
    M, R, CC = _curves(Ln, (0.0, 110.0), (215.0, 20.0), (130.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar  # [S20 story-split] cassowary: matte wattle deck
    return _out(rgb, M, R, CC)


@_f("wx_lyrebird_lace", "Lyrebird Lace",
    "Filmy silver-white lace tail: open S-curved shafts hung with sparse curling barbs on smoky dark.")
def lyrebird_lace(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 31 Lyrebird Lace: 30 sinuous shafts + ~14k sparse curling barbs (silver), smoke mist ground
    n = N
    r = H.rng(seed)
    reg = _z(H.fbm(n, seed + 1, cells=(3, 6, 12), gain=0.7))
    rgb = H.ramp(np.clip(0.30 + 0.12 * reg + 0.03 * H.grain(n, seed + 2), 0, 1), [(0.0, '#0a0d12'), (0.5, '#1c232b'), (1.0, '#3a4650')]).astype(F32)
    cv = None
    ns = 30
    ts = np.linspace(-100, n + 100, 64)
    barbs = []
    bval = []
    shafts = []
    sval = []
    for s_ in range(ns):
        x0 = (s_ + r.uniform(0.0, 1.0)) * n / ns * 1.0 - 0.0
        A = r.uniform(110, 230)
        lam = r.uniform(650, 1100)
        ph = r.uniform(0, 6.283)
        slope = r.uniform(-0.25, 0.25)
        xs = x0 + A * np.sin(2 * np.pi * ts / lam + ph) + slope * (ts - n / 2)
        P = np.stack([xs, ts], 1)
        shafts.append(P)
        sval.append(r.uniform(200, 255))
        T = np.gradient(P, axis=0)
        T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-6
        Nn = np.stack([-T[:, 1], T[:, 0]], 1)
        # barb attach points every ~14 px (interpolate)
        t2 = np.linspace(0, len(ts) - 1, 190)
        i0 = np.floor(t2).astype(int).clip(0, len(ts) - 2)
        fr = (t2 - i0)[:, None]
        Q = P[i0] * (1 - fr) + P[i0 + 1] * fr
        Tq = T[i0] * (1 - fr) + T[i0 + 1] * fr
        Nq = Nn[i0] * (1 - fr) + Nn[i0 + 1] * fr
        for side in (-1.0, 1.0):
            L = r.uniform(55, 110, len(Q))[:, None]
            a = np.deg2rad(r.uniform(52, 72, len(Q)))[:, None]
            dirv = Tq * np.cos(a) + side * Nq * np.sin(a)
            curl = (side * Nq * 0.25 + Tq * 0.0)
            pts = [Q, Q + dirv * L * 0.4, Q + dirv * L * 0.75 + curl * L * 0.1, Q + dirv * L + Tq * L * 0.25]
            barbs.append(np.stack(pts, 1))
            bval.append(r.uniform(90, 235, len(Q)))
    B = np.concatenate(barbs).astype(F32)
    bv = np.concatenate(bval)
    cv = H.lines3(n, B, np.stack([bv, np.zeros(len(bv)), np.zeros(len(bv))], 1), 1)
    cv = H.lines3(n, np.stack(shafts).astype(F32), np.stack([np.array(sval), np.zeros(ns), np.zeros(ns)], 1), 2, canvas=cv)
    V = H.u8f(cv[..., 0])
    sil = H.ramp(np.clip(V, 0, 1), [(0.0, '#6a7c8a'), (0.5, '#c4d2dc'), (1.0, '#ffffff')])
    rgb = rgb * (1 - V * 0.9)[..., None] + sil * (V * 0.95)[..., None]
    Ln = H.sstep(0.05, 0.85, H.lum(rgb))
    M, R, CC = _curves(Ln, (40.0, 200.0), (200.0, 60.0), (150.0, 30.0))
    return _out(rgb, M, R, CC)


@_f("wx_sunbird_throat", "Sunbird Iridescent Throat",
    "Rows of round ringed throat scales whose metallic colour sweeps from lime green through teal to blue across the surface.")
def sunbird_throat(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 32 Sunbird Iridescent Throat (v2, coordinator review 2): 30x26 px hex-packed round scale-feathers with ring grooves + highlight; ONE smooth diagonal hue sweep (copper->gold->green->teal->blue->violet) plus per-scale angle shift, no regional blotches
    n = N
    X, Y = H.xy(n)
    row, col, u, vv, cr, cr2, S, T = _scalelat(n, 30.0, 26.0, 18.0, seed, 0.5, (3, 6, 12))
    lx = u * 15.0
    ly = (vv - 0.5) * 26.0
    d = np.hypot(lx / 15.0, ly / 14.0)
    disc = H.sstep(1.02, 0.86, d)
    ring = 0.80 + 0.20 * np.cos(6.2832 * d * 2.6 + 0.8 * cr2)
    zl = _z(H.fbm(n, seed + 3, cells=(2, 3, 5), gain=0.7))
    t = np.clip(0.02 + 1.05 * (0.55 * X / F32(n) + 0.40 * Y / F32(n)) + 0.09 * zl + 0.12 * (0.5 * lx / 15.0 + 0.5 * ly / 14.0) + 0.06 * (cr - 0.5), 0, 1)
    col3 = H.ramp(t, [(0.0, '#b8541a'), (0.18, '#e2a52e'), (0.38, '#58c040'), (0.58, '#12b8b0'), (0.78, '#3c56e0'), (1.0, '#a038d8')])
    hl = np.exp(-(((lx + 4.0) ** 2 + (ly + 4.0) ** 2) / (2 * 3.4 ** 2))) * disc
    lum = disc * (0.30 + 0.70 * np.clip(1.0 - d * d, 0, 1) ** 0.7) * (0.80 + 0.20 * cr) * ring + 0.55 * hl
    rgb = col3 * lum[..., None] + 0.012
    Ln = H.sstep(0.03, 0.75, H.lum(rgb))
    M, R, CC = _curves(Ln, (80.0, 255.0), (140.0, 20.0), (60.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_abalone_growth", "Abalone Growth Rings",
    "Swirled nacre laid down in warped growth rings, each ring flashing teal, green, pink and silver as it ages.")
def abalone_growth(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 33 Abalone Growth Rings: 3 umbo centres, soft-min ring distance warped 150 px, sawtooth ring brightness (period 34 px), hue = ring phase + regional field, tablet noise; ANO
    n = N
    X, Y = H.xy(n)
    Xw = X + 150.0 * _z(H.fbm(n, seed + 1, cells=(2, 4, 8), gain=0.7))
    Yw = Y + 150.0 * _z(H.fbm(n, seed + 2, cells=(2, 4, 8), gain=0.7))
    acc = np.zeros((n, n), F32)
    for cx, cy in ((0.20, 0.30), (0.76, 0.24), (0.48, 0.86)):
        d = np.hypot(Xw - cx * n, (Yw - cy * n) * 1.25)
        acc += np.exp(-d / F32(70.0))
    dmin = -70.0 * np.log(acc + 1e-9)
    ph = dmin / 34.0 + 0.7 * _z(H.fbm(n, seed + 3, cells=(6, 12, 24), gain=0.7))
    fl = np.floor(ph)
    fr = (ph - fl).astype(F32)
    regz = _z(H.fbm(n, seed + 4, cells=(2, 3, 6), gain=0.7))
    t = np.mod(0.5 * fr + 0.30 * regz + 0.13 * H.hash01(np.mod(fl, 4096).astype(np.int64), seed), 1.0)
    col = H.ramp(t, [(0.0, '#0a7a86'), (0.22, '#18c0a4'), (0.42, '#c8dce8'), (0.62, '#ec74b4'), (0.82, '#4a54d0'), (1.0, '#0a7a86')])
    lum = 0.30 + 0.80 * fr ** 0.8
    wall = np.exp(-(np.minimum(fr, 1.0 - fr) / 0.05) ** 2)
    tab = 0.88 + 0.22 * _z(H.noise(n, 230, seed + 5))
    rgb = col * (lum * tab * (1.0 - 0.7 * wall))[..., None]
    Ln = H.sstep(0.03, 0.85, H.lum(rgb))
    M, R, CC = _curves(Ln, (190.0, 255.0), (120.0, 24.0), (60.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_paua_storm", "Paua Lightning Nacre",
    "Deep indigo paua shell flowing in bands of electric green, cyan and violet, with bright storm-line crests.")
def paua_storm(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 34 Paua Lightning Nacre (v2): double domain-warped field, 5.5 colour bands filled (hue cycles green->cyan->blue->violet along z), crisp crest lines + flash patches; CHR
    n = N
    q1 = _z(H.fbm(n, seed + 1, cells=(2, 3, 5), gain=0.7))
    q2 = _z(H.fbm(n, seed + 2, cells=(2, 3, 5), gain=0.7))
    z0 = _z(H.fbm(n, seed + 3, cells=(3, 6, 12), gain=0.7))
    z = _z(H.warp(z0, 240.0 * q1, 240.0 * q2))
    z = _z(H.warp(z, 70.0 * q2, -70.0 * q1))
    s = z * 5.5
    cb = 0.5 + 0.5 * np.cos(6.2832 * s)
    v = np.abs(np.sin(np.pi * s))
    line = np.exp(-(v / 0.10) ** 2)
    hz = _z(H.fbm(n, seed + 4, cells=(3, 6, 12), gain=0.6))
    hue = H.ramp(np.clip(0.5 + 0.30 * hz + 0.5 * (cb - 0.5), 0, 1), [(0.0, '#6a28ff'), (0.30, '#1858ff'), (0.55, '#10d0e8'), (0.8, '#18ffa0'), (1.0, '#b8ff70')])
    fl = H.sstep(1.0, 2.0, _z(H.fbm(n, seed + 5, cells=(4, 8, 16), gain=0.7)))
    tab = 0.80 + 0.40 * H.sstep(-1.0, 1.0, _z(H.noise(n, 260, seed + 6)))
    body = 0.10 + 0.80 * cb ** 2.0
    rgb = hue * (body * tab)[..., None] * 0.85 + H.hexrgb('#07052a') * (1.0 - body)[..., None] * 0.9
    rgb = rgb + hue * (line * tab)[..., None] * 0.55 + (fl * 0.35 * body)[..., None] * H.hexrgb('#c070ff')
    Ln = H.sstep(0.03, 0.8, H.lum(rgb))
    M, R, CC = _curves(Ln, (150.0, 255.0), (96.0, 4.0), (70.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(rgb, M, R, CC)


@_f("wx_nacre_bricks", "Nacre Brick Wall",
    "A wall of big nacre tablets laid in staggered courses, each brick its own pearl pink, mint, lilac or champagne, set in dark mortar.")
def nacre_bricks(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 35 Nacre Brick Wall (v2, coordinator review 2): 96x42 px bricks in staggered courses (warp 7 px), 6 px dark mortar, per-brick palette of 6 pearl colours, growth lamellae (11 px), lit top/left bevel + shadow bottom edge, sparkle; courses read at 512
    n = N
    X, Y = H.xy(n)
    Xw = X + 7.0 * _z(H.fbm(n, seed + 1, cells=(10, 20), gain=0.6))
    Yw = Y + 6.0 * _z(H.fbm(n, seed + 2, cells=(10, 20), gain=0.6))
    row, col, lx, ly = H.cells_rows(Xw, Yw, 96.0, 42.0, 0.5)
    cr = H.cellhash(row, col, seed)
    cr2 = H.cellhash(row, col, seed + 1)
    ax = np.abs(lx)
    ay = np.abs(ly)
    tab = H.sstep(45.0, 42.5, ax) * H.sstep(18.0, 15.5, ay)
    pal = np.array([H.hexrgb(c) for c in ('#f0b6d2', '#a6e8cc', '#c4b2f4', '#f2e2b0', '#a8d0f4', '#f6c8b0')], F32)
    base = pal[np.minimum((cr * 6).astype(np.int64), 5)]
    th = (cr2 - 0.5) * 0.5
    lam = 0.5 + 0.5 * np.cos(6.2832 * (ly * np.cos(th) + lx * np.sin(th) * 0.3) / 11.0 + 3.0 * cr)
    lit = 0.80 + 0.20 * (-ly / 21.0) + 0.12 * (1.0 - ax / 48.0)
    de = np.minimum(42.5 - ax, 15.5 - ay)
    bv = np.exp(-(np.maximum(de, 0.0) / 2.4) ** 2)
    light = bv * (0.45 * (ly < -6) + 0.25 * (lx < -30))
    dark = bv * 0.38 * (ly > 6)
    plate = base * (lit * (0.88 + 0.12 * lam) * (1.0 - dark))[..., None] + light[..., None] * 0.55
    mortar = H.hexrgb('#1e1a2c') * (0.7 + 0.6 * _z(H.noise(n, 400, seed + 5)) * 0.3)[..., None]
    rgb = plate * tab[..., None] + mortar * (1.0 - tab)[..., None]
    flk = H.flake_mask(n, 0.008, seed + 7)
    rgb = np.clip(rgb + flk[..., None] * H.hexrgb('#fff2ff') * 0.40 * tab[..., None], 0, 1)
    Ln = H.sstep(0.04, 0.95, H.lum(rgb))
    M, R, CC = _curves(Ln, (70.0, 170.0), (118.0, 46.0), (62.0, 20.0))
    return _out(rgb, M, R, CC)


@_f("wx_black_lip_pearl", "Black-Lip Pearl",
    "Dark pearl skin glowing with soft overlapping orbs of peacock green, grey and aubergine orient, crossed by fine nacre lamellae.")
def black_lip_pearl(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 36 Black-Lip Pearl (v3): two overlapping Voronoi orb layers (110/170 px cells, soft gaussian glow radius 34-78), concentric orient rings 13 px inside each orb, 11 px nacre lamellae lines, peacock-green/grey/aubergine ramp per orb + regional drift, offset crisp highlight; SAT
    n = N
    X, Y = H.xy(n)
    reg = _z(H.fbm(n, seed + 5, cells=(2, 3, 6), gain=0.7))
    acc = np.zeros((n, n, 3), F32)
    for li, (cell, r0, r1) in enumerate(((110, 34.0, 60.0), (170, 44.0, 78.0))):
        pts = H.jitter_pts(n, cell, seed + 1 + 10 * li, 0.95, cell // 2)
        d, lab, sx, sy = H.voronoi(n, pts)
        idx = (lab - 1).astype(np.int64)
        h1 = H.hash01(idx, seed + 2 + 10 * li)
        h2 = H.hash01(idx, seed + 3 + 10 * li)
        rad = r0 + (r1 - r0) * h1
        g = np.exp(-(d / rad) ** 2) * H.sstep(0.0, 22.0, H.edge_dist(lab))
        ring = 0.62 + 0.38 * np.cos(6.2832 * d / 13.0 + 6.0 * h2)
        tc = np.clip(0.5 + 0.24 * reg + 0.55 * (h2 - 0.5), 0, 1)
        col = H.ramp(tc, [(0.0, '#5a2064'), (0.30, '#1c8a74'), (0.62, '#58a098'), (1.0, '#c0c2cc')])
        ox = X - sx[idx].astype(F32)
        oy = Y - sy[idx].astype(F32)
        hl = np.exp(-(((ox + 0.30 * rad) ** 2 + (oy + 0.32 * rad) ** 2) / (2 * (0.16 * rad) ** 2)))
        acc += col * (g * ring * (0.55 + 0.45 * h1) * (0.95 if li == 0 else 0.78))[..., None] + (hl * g * 0.30)[..., None]
    lam = 0.5 + 0.5 * np.cos(6.2832 * (Y + 30.0 * _z(H.fbm(n, seed + 6, cells=(3, 6, 12), gain=0.7))) / 11.0)
    rgb = H.hexrgb('#080b0e') * (0.8 + 0.4 * lam)[..., None] + acc * (0.78 + 0.22 * lam)[..., None]
    rgb = np.clip(rgb, 0, 1)
    Ln = H.sstep(0.03, 0.7, H.lum(rgb))
    M, R, CC = _curves(Ln, (90.0, 230.0), (150.0, 20.0), (110.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(rgb, M, R, CC)


@_f("wx_mussel_lines", "Blue Mussel Growth Lines",
    "Blue-black mussel shells, each with fine concentric growth lines around its hinge and a pearly violet inner edge.")
def mussel_lines(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 37 Blue Mussel Growth Lines (v2): ~100 umbo shells (Voronoi 210 px), concentric ridges period 22 px (r^0.9, noise-warped, strong), radial ribs, narrow pearly violet rim; BRU along lines
    n = N
    X, Y = H.xy(n)
    pts = H.jitter_pts(n, 210, seed + 1, 0.85, 60)
    d, lab, sx, sy = H.voronoi(n, pts)
    idx = (lab - 1).astype(np.int64)
    ed = H.edge_dist(lab)
    dx = X - sx[idx].astype(F32)
    dy = (Y - sy[idx].astype(F32)) * 1.15
    r = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)
    rph = np.power(r + 1.0, 0.90) / 21.0 + 0.45 * _z(H.fbm(n, seed + 2, cells=(8, 16, 32), gain=0.7))
    fr = rph - np.floor(rph)
    ridge = (1.0 - np.abs(2.0 * fr - 1.0)) ** 1.6
    rib = 0.5 + 0.5 * np.sin(ang * 40.0 + 4.0 * _z(H.fbm(n, seed + 3, cells=(6, 12), gain=0.6)))
    hz = _z(H.fbm(n, seed + 4, cells=(2, 3, 6), gain=0.7))
    ground = H.ramp(np.clip(0.22 + 0.50 * ridge + 0.14 * rib + 0.06 * hz, 0, 1), [(0.0, '#04061a'), (0.35, '#0c1840'), (0.7, '#2c46a0'), (1.0, '#6a88e0')])
    pearl = np.exp(-(ed / 9.0) ** 2)
    pcol = H.ramp(np.clip(0.5 + 0.3 * np.sin(ed / 5.0) + 0.2 * hz, 0, 1), [(0.0, '#a8a0e8'), (0.5, '#e4d4f8'), (1.0, '#98c0f0')])
    rgb = ground * (1.0 - 0.75 * pearl)[..., None] + pcol * (pearl * (0.40 + 0.35 * ridge))[..., None]
    gap = np.exp(-(ed / 1.4) ** 2)
    rgb = rgb * (1.0 - 0.7 * gap)[..., None]
    Ln = H.sstep(0.02, 0.8, H.lum(rgb))
    M, R, CC = _curves(Ln, (110.0, 240.0), (170.0, 20.0), (90.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(rgb, M, R, CC)


@_f("wx_nautilus_septa", "Nautilus Septa",
    "Cream nautilus cross-sections: log-spiral whorls, curved chamber walls and rust tiger-stripe flames on each.")
def nautilus_septa(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 38 Nautilus Septa (v2): ~48 Voronoi shells (300 px), log-spiral whorl w = 2.7 ln r - theta/2pi, bold whorl walls, curved septa (20/turn), thin tiger flames (44/turn); SAT
    n = N
    X, Y = H.xy(n)
    pts = H.jitter_pts(n, 300, seed + 1, 0.7, 120)
    d, lab, sx, sy = H.voronoi(n, pts)
    idx = (lab - 1).astype(np.int64)
    hc = H.hash01(idx, seed + 2)
    dx = X - sx[idx].astype(F32)
    dy = Y - sy[idx].astype(F32)
    r = np.hypot(dx, dy) + 3.0
    th = np.arctan2(dy, dx) + 6.2832 * hc
    w = np.log(r) * 2.7 - th / 6.2832
    fl_ = np.floor(w)
    fr = (w - fl_).astype(F32)
    wall = np.exp(-(np.minimum(fr, 1.0 - fr) / 0.045) ** 2)
    ps = th * 20.0 / 6.2832 + 1.6 * np.log(r) * 2.7 + 0.37 * fl_
    sept = np.exp(-(np.abs(ps - np.rint(ps)) / 0.06) ** 2) * H.sstep(0.08, 0.30, fr)
    sg = th * 44.0 / 6.2832 + 3.0 * _z(H.fbm(n, seed + 3, cells=(6, 12, 24), gain=0.7)) + 2.2 * fr
    flame = H.sstep(0.42, 0.80, np.sin(sg)) * H.sstep(0.12, 0.40, fr) * H.sstep(0.98, 0.84, fr) * H.sstep(12.0, 26.0, r)
    cream = H.ramp(np.clip(0.55 + 0.30 * fr + 0.08 * _z(H.noise(n, 180, seed + 4)), 0, 1), [(0.0, '#d8c8a0'), (0.6, '#efe2c2'), (1.0, '#faf2de')])
    rust = H.ramp(np.clip(0.4 + 0.35 * (1.0 - fr) + 0.15 * _z(H.noise(n, 200, seed + 5)), 0, 1), [(0.0, '#6a2a10'), (0.5, '#a24a1c'), (1.0, '#c8702c')])
    rgb = cream * (1.0 - flame)[..., None] + rust * flame[..., None]
    rgb = rgb * (1.0 - 0.80 * wall)[..., None] * (1.0 - 0.55 * sept)[..., None]
    edge = H.edge_dist(lab)
    rgb = rgb * (1.0 - 0.35 * np.exp(-(edge / 1.5) ** 2))[..., None]
    Ln = H.sstep(0.05, 0.95, H.lum(rgb))
    M, R, CC = _curves(Ln, (70.0, 150.0), (160.0, 80.0), (100.0, 30.0))
    return _out(rgb, M, R, CC)


@_f("wx_cowrie_gloss", "Tiger Cowrie Gloss",
    "Porcelain-glossy cream cowrie shell dotted with three sizes of dark brown spots under long mirror reflections.")
def cowrie_gloss(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 39 Tiger Cowrie Gloss: cream gradient + 3 spot layers (38/24/14 px lattices, ragged radii, 70/60/55% present) + long warped sine highlight bands; WET
    n = N
    X, Y = H.xy(n)
    regz = _z(H.fbm(n, seed + 1, cells=(2, 3, 5), gain=0.7))
    cream = H.ramp(np.clip(0.55 + 0.18 * regz + 0.20 * np.sin(Y / 520.0 + 1.3 * regz), 0, 1), [(0.0, '#c89c6c'), (0.5, '#f0e0c0'), (1.0, '#fcf4e2')])
    rgb = cream.astype(F32).copy()
    rag = _z(H.noise(n, 300, seed + 2))
    for si, (sp, r0, r1, hexc, dens) in enumerate(((38, 6.5, 15.0, '#44200e', 0.70), (24, 4.5, 9.5, '#28120a', 0.62), (14, 2.4, 5.2, '#6a381a', 0.58))):
        pts = H.jitter_pts(n, sp, seed + 10 + si, 0.85, sp)
        d, lab, sx, sy = H.voronoi(n, pts)
        idx = (lab - 1).astype(np.int64)
        h1 = H.hash01(idx, seed + 20 + si)
        h2 = H.hash01(idx, seed + 30 + si)
        rad = r0 + (r1 - r0) * h2
        dd = d + (2.2 - 0.5 * si) * rag
        m = H.sstep(rad + 0.9, rad - 0.9, dd) * (h1 < dens)
        rgb = rgb * (1.0 - 0.92 * m)[..., None] + H.hexrgb(hexc) * (0.92 * m * (0.8 + 0.4 * h2))[..., None]
    band = 0.5 + 0.5 * np.sin((X * 0.62 - Y * 0.26) / 120.0 + 2.4 * _z(H.fbm(n, seed + 4, cells=(2, 3, 5), gain=0.6)))
    spot_cov = np.clip(1.0 - H.lum(rgb) / 0.85, 0, 1)
    hl = H.sstep(0.93, 0.99, band) * (0.55 - 0.25 * spot_cov)
    rgb = np.clip(rgb + hl[..., None] * H.hexrgb('#fffdf4'), 0, 1).astype(F32)
    Ln = H.sstep(0.03, 0.95, H.lum(rgb))
    M, R, CC = _curves(Ln, (30.0, 112.0), (92.0, 6.0), (24.0, 16.0))  # [S20 story-split] cowrie: pearly gloss deck
    return _out(rgb, M, R, CC)


@_f("wx_conch_pink", "Queen Conch Lip",
    "Flaring glossy conch lip in pink, coral and cream, covered in rows of fine flame-shaped growth ridges.")
def conch_pink(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 40 Queen Conch Lip: ridge phase = (Y + 110 tri(X/200) + warp)/21 (zig-zag flame ridges), bump-lit gloss, pink->coral->cream gradient; WET
    n = N
    X, Y = H.xy(n)
    q = _z(H.fbm(n, seed + 1, cells=(2, 3, 5), gain=0.7))
    q2 = _z(H.fbm(n, seed + 2, cells=(4, 8, 16), gain=0.7))
    tri = np.abs(np.mod((X + 60.0 * q) / 200.0, 1.0) - 0.5)
    ph = (Y + 110.0 * tri + 70.0 * q2 + 30.0 * q) / 21.0
    hgt = (0.5 + 0.5 * np.sin(6.2832 * ph)) ** 1.5 + 0.05 * H.grain(n, seed + 3)
    hgt = (hgt + 0.25 * np.exp(-((np.mod(ph, 1.0) - 0.5) / 0.1) ** 2) * 0).astype(F32)
    dif, spc = H.shade(H.blur(hgt.astype(F32), 0.8), 3.2)
    t = np.clip(0.5 + 0.22 * _z(H.fbm(n, seed + 4, cells=(2, 3, 5), gain=0.7)) + 0.10 * np.sin(Y / 300.0), 0, 1)
    base = H.ramp(t, [(0.0, '#c0486a'), (0.35, '#f07a8a'), (0.65, '#f49a62'), (1.0, '#fbd8b0')])
    rgb = base * (0.40 + 0.75 * dif)[..., None] + spc[..., None] * 0.55
    Ln = H.sstep(0.03, 0.95, H.lum(rgb))
    M, R, CC = _curves(Ln, (20.0, 140.0), (120.0, 4.0), (60.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(rgb, M, R, CC)


def _oper_master(S=256):
    gx, gy = H.tile_xy(S)
    rr = np.hypot(gx, gy) / (S * 0.5)
    th = np.arctan2(gy, gx)
    sp = 0.5 + 0.5 * np.sin(th * 3.0 - 6.5 * np.log(rr + 0.06))
    green = H.ramp(np.clip(sp * (0.55 + 0.45 * (1.0 - rr * 1.2)), 0, 1), [(0.0, '#042c18'), (0.45, '#128a48'), (0.8, '#42c868'), (1.0, '#c4f4a0')])
    tan = H.ramp(np.clip((rr - 0.62) / 0.2, 0, 1), [(0.0, '#6a3a1a'), (1.0, '#b88040')])
    rim = H.sstep(0.80, 0.83, rr) * H.sstep(0.90, 0.87, rr)
    inner = H.sstep(0.66, 0.62, rr)
    col = tan * (1 - inner)[..., None] + green * inner[..., None]
    col = col * (1 - rim)[..., None] + H.hexrgb('#f6f2e8') * rim[..., None]
    hl = np.exp(-(((gx + 0.14 * S) ** 2 + (gy + 0.16 * S) ** 2) / (2 * (0.055 * S) ** 2))) * 0.6 * inner
    col = col + hl[..., None]
    al = H.sstep(0.90, 0.86, rr)
    out = np.zeros((S, S, 4), F32)
    out[..., :3] = np.clip(col, 0, 1) * al[..., None]
    out[..., 3] = al
    return out


@_f("wx_turban_operculum", "Cat's Eye Operculum",
    "Round shell doors with swirling green centres and white rims, scattered over ribbed brown turban-shell hide.")
def turban_operculum(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 41 Cat's Eye Operculum: 81 round operculum stamps (log-spiral green centre, tan ring, white rim, glints; 3 sizes x 8 rotations) on horizontally ribbed brown turban ground; CHR
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)
    z = _z(H.fbm(n, seed + 1, cells=(3, 6, 12), gain=0.7))
    rib = 0.5 + 0.5 * np.sin((Y + 22.0 * z) * (6.2832 / 15.0))
    mottle = _z(H.noise(n, 160, seed + 2))
    t = np.clip(0.35 + 0.30 * rib + 0.10 * mottle + 0.08 * z, 0, 1)
    ground = H.ramp(t, [(0.0, '#2e1808'), (0.4, '#6a3a18'), (0.75, '#a8662a'), (1.0, '#d89a50')])
    fleck = H.flake_mask(n, 0.01, seed + 3)
    ground = ground + fleck[..., None] * H.hexrgb('#ffd8a0') * 0.25
    tiles = _rot_tiles(_oper_master(), (110, 140, 172), (0, 45, 90, 135, 180, 225, 270, 315))
    g = 9
    sp = n / g
    gi, gj = np.meshgrid(np.arange(g), np.arange(g))
    ex = ((gi + 0.5 + r.uniform(-0.32, 0.32, gi.shape) + 0.5 * (gj & 1)) * sp).ravel()
    ey = ((gj + 0.5 + r.uniform(-0.32, 0.32, gi.shape)) * sp).ravel()
    ti = r.integers(0, 3, ex.size) * 8 + r.integers(0, 8, ex.size)
    o = np.argsort(ey)
    img = np.ascontiguousarray(ground, F32).copy()
    H.splat_rgba(img, tiles, ti[o], ex[o], ey[o])
    Ln = H.sstep(0.03, 0.9, H.lum(img))
    M, R, CC = _curves(Ln, (60.0, 220.0), (150.0, 8.0), (110.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(img, M, R, CC)


def _scallop_master(S=256):
    gx, gy = H.tile_xy(S)
    dx = gx
    dy = gy - 0.46 * S
    r = np.hypot(dx, dy) / (S * 0.92)
    th = np.arctan2(dx, -dy)
    rib = 0.5 + 0.5 * np.sin(th * 13.0)
    edge = 1.0 - 0.03 * (1.0 - np.cos(th * 13.0 * 1.0)) * 0.5 - 0.02
    inside = H.sstep(edge + 0.012, edge - 0.012, r) * H.sstep(1.0, 0.9, np.abs(th))
    growth = 0.5 + 0.5 * np.sin(r * 62.0)
    col = H.ramp(np.clip(r, 0, 1), [(0.0, '#6a2438'), (0.30, '#b8342a'), (0.58, '#ee7a2a'), (0.82, '#f8c446'), (1.0, '#fff0c4')])
    col = col * (0.50 + 0.50 * rib)[..., None] * (0.72 + 0.28 * growth)[..., None]
    gl = np.exp(-((np.mod(r * 9.0, 1.0) - 0.5) / 0.05) ** 2) * 0.30
    col = col + gl[..., None] * H.hexrgb('#fff4e0')
    out = np.zeros((S, S, 4), F32)
    out[..., :3] = np.clip(col, 0, 1) * inside[..., None]
    out[..., 3] = inside
    return out


@_f("wx_scallop_ribs", "Painted Scallop Ribs",
    "Overlapping scallop-shell fans in sunset yellow, orange and red, each with radiating ribs and white growth lines.")
def scallop_ribs(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 42 Painted Scallop Ribs: ~430 fan stamps (13 ribs, scalloped rim, growth bands, sunset ramp), staggered roof-tile rows 118x82, tint-varied (orange/red/yellow/white), painter-ordered; BRU along ribs
    n = N
    r = H.rng(seed)
    angs = (-12, -6, 0, 6, 12)
    tiles = _rot_tiles(_scallop_master(), (170, 200), angs)
    rows = int(n / 104) + 3
    xs, ys = [], []
    for j in range(rows):
        cols = int(n / 118) + 3
        for i in range(cols):
            xs.append((i - 0.5 + 0.5 * (j & 1)) * 118.0 + r.uniform(-9, 9))
            ys.append((j - 0.5) * 104.0 + r.uniform(-6, 6))
    xs = np.array(xs)
    ys = np.array(ys)
    K = len(xs)
    ti = r.integers(0, 2, K) * 5 + r.integers(0, 5, K)
    pal = np.array([(1.0, 1.0, 1.0), (1.0, 0.78, 0.72), (1.0, 1.0, 0.66), (1.25, 1.2, 1.15), (0.92, 0.66, 0.60), (1.0, 0.9, 0.5)], F32)
    tint = pal[r.integers(0, len(pal), K)] * r.uniform(0.9, 1.1, (K, 1)).astype(F32)
    img = np.zeros((n, n, 3), F32) + H.hexrgb('#2a0e14')
    H.splat_rgba(img, tiles, ti, xs, ys, tint=tint)
    img = np.clip(img, 0, 1)
    Ln = H.sstep(0.03, 0.95, H.lum(img))
    M, R, CC = _curves(Ln, (70.0, 230.0), (170.0, 20.0), (90.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(img, M, R, CC)
# -------------------------------------------------------------------------
# STONES 43-52
# -------------------------------------------------------------------------
def _aniso(n, cx, cy, seed, ang):
    """Streak noise: cx x cy random grid stretched to n x n, rotated by ang degrees (unit std-ish)."""
    g = H.rng(seed).standard_normal((int(cy), int(cx))).astype(F32)
    m = cv2.resize(g, (n, n), interpolation=cv2.INTER_CUBIC)
    Mx = cv2.getRotationMatrix2D((n / 2.0, n / 2.0), float(ang), 1.0)
    return cv2.warpAffine(m, Mx, (n, n), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


@_f("wx_opal_harlequin", "Harlequin Opal",
    "A harlequin lattice of diamond patches, each flashing a rainbow of spectral colour, alternating with black potch.")
def opal_harlequin(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 43 Harlequin Opal (v2): warped 51 px diamond lattice (checker bias + random potch), per-patch spectral hue with strong horizontal rainbow gradient, black seams; CHR flashes
    n = N
    X, Y = H.xy(n)
    Xw = X + 16.0 * _z(H.fbm(n, seed + 1, cells=(3, 6, 12), gain=0.7))
    Yw = Y + 16.0 * _z(H.fbm(n, seed + 2, cells=(3, 6, 12), gain=0.7))
    a = (Xw + Yw) / F32(51.0)
    b = (Xw - Yw) / F32(51.0)
    ia = np.floor(a).astype(np.int64)
    ib = np.floor(b).astype(np.int64)
    fa = (a - ia - 0.5).astype(F32)
    fb = (b - ib - 0.5).astype(F32)
    h1 = H.cellhash(ia, ib, seed + 3)
    h2 = H.cellhash(ia, ib, seed + 4)
    h3 = H.cellhash(ia, ib, seed + 5)
    par = ((ia + ib) & 1) == 0
    live = H.sstep(0.0, 0.0001, np.where(par, h3 - 0.12, h3 - 0.80))
    edv = 0.5 - np.maximum(np.abs(fa), np.abs(fb))
    seam = H.sstep(0.012, 0.055, edv)
    inner = 0.55 + 0.45 * H.sstep(0.0, 0.22, edv)
    hue = np.mod(h1 + 0.45 * fa * np.where(h2 > 0.5, 1.0, -1.0) + 0.25 * fb, 1.0)
    col = H.hsv(hue, 0.96, 1.0)
    flash = 0.50 + 0.50 * h2
    rgb = col * (live * inner * seam * flash)[..., None] + H.hexrgb('#0a0a12') * (0.5 + 0.5 * seam)[..., None] * (1.0 - 0.65 * live)[..., None]
    Ln = H.sstep(0.03, 0.75, H.lum(rgb))
    M, R, CC = _curves(Ln, (60.0, 255.0), (150.0, 10.0), (96.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_opal_pinfire", "Pinfire Opal",
    "Dark milky grey-blue opal pricked with dense, crisp pinpoints of saturated fire, each 70 px patch in its own red, green, blue or violet.")
def opal_pinfire(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 44 Pinfire Opal (v3, coordinator review 3: was pale blurry pastel): DARK milky grey-blue body (0.25-0.55 luma, 23 + 14 px mottle + 40 px milky veils), 70 px pinfire patches (voronoi) each with its own spectral hue, UNBLURRED 1 px pinpoints + 3x3 dilated 3 px pinpoints at 2-8% density per patch, fully saturated, no halo; ANO
    n = N
    reg = _z(H.fbm(n, seed + 1, cells=(3, 6, 12), gain=0.7))
    mott = _z(H.noise(n, 90, seed + 2))
    mott2 = _z(H.noise(n, 150, seed + 6))
    veil = H.ridged(_z(H.fbm(n, seed + 7, cells=(30, 60, 110), gain=0.6)))
    ground = H.ramp(np.clip(0.40 + 0.06 * reg + 0.10 * mott + 0.07 * mott2 + 0.10 * (veil - 0.7), 0, 1), [(0.0, '#222c42'), (0.5, '#46557a'), (1.0, '#7c8cb0')])
    d_, lab_, sx_, sy_ = H.voronoi(n, H.jitter_pts(n, 70, seed + 1, 0.95, 30))
    idx = (lab_ - 1).astype(np.int64)
    hp = H.hash01(idx, seed + 3)
    alive = H.hash01(idx, seed + 4)
    dens = (0.012 + 0.07 * H.sstep(0.25, 0.75, alive)) * (0.6 + 0.4 * H.sstep(-0.8, 0.8, _z(H.noise(n, 50, seed + 5))))
    r = H.rng(seed + 5)
    d1 = (r.random((n, n), dtype=F32) < dens).astype(F32)
    d2 = cv2.dilate((r.random((n, n), dtype=F32) < dens * 0.22).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(F32)
    dots = np.maximum(d1, d2)
    hr = cv2.GaussianBlur(r.standard_normal((n, n)).astype(F32), (0, 0), 1.5)
    hr = hr / (hr.std() + 1e-6)
    pin = H.ramp(np.clip(hp + 0.12 * hr, 0, 1), [(0.0, '#ff1010'), (0.25, '#ffb000'), (0.5, '#00ff40'), (0.75, '#0a88ff'), (1.0, '#b020ff')])
    bright = 0.86 + 0.14 * r.random((n, n), dtype=F32)
    rgb = ground * (1.0 - dots)[..., None] + pin * (dots * bright)[..., None]
    Ln = H.sstep(0.12, 0.60, H.lum(rgb))
    M, R, CC = _curves(Ln, (255.0, 90.0), (16.0, 130.0), (16.0, 90.0))
    return _out(np.clip(rgb, 0, 1), M, R, CC)


@_f("wx_labradorite_schiller", "Labradorite Schiller",
    "Dark grey feldspar whose crystal grains flash sheets of electric blue or gold across fine parallel lamellae.")
def labradorite_schiller(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 45 Labradorite Schiller: 250 px crystal grains, per-grain lamella angle (period 13 px), grain-wise blue/gold schiller sheets gated by a noise mask, slate base, dark grain boundaries; ANO
    n = N
    X, Y = H.xy(n)
    pts = H.jitter_pts(n, 250, seed + 1, 0.9, 100)
    d, lab, sx, sy = H.voronoi(n, pts)
    idx = (lab - 1).astype(np.int64)
    ed = H.edge_dist(lab)
    th = 6.2832 * H.hash01(idx, seed + 2)
    wv = 9.0 * _z(H.fbm(n, seed + 3, cells=(6, 12, 24), gain=0.7))
    xr = X * np.cos(th) + Y * np.sin(th) + wv
    lam = 0.5 + 0.5 * np.cos(6.2832 * xr / 13.0)
    sc = H.sstep(0.18, 0.55, H.hash01(idx, seed + 4))
    gm = _z(H.fbm(n, seed + 5, cells=(5, 10, 20), gain=0.7))
    inten = H.sstep(-0.9, 0.8, gm) * sc
    typ = H.hash01(idx, seed + 6) > 0.52
    t = np.where(typ, 0.76 + 0.20 * lam, 0.10 + 0.40 * lam).astype(F32)
    cs = H.ramp(t, [(0.0, '#0a2a90'), (0.2, '#1a6cff'), (0.4, '#18d0e4'), (0.6, '#7ee08a'), (0.76, '#f0c030'), (1.0, '#f08a20')])
    grey = 0.13 + 0.07 * lam + 0.04 * _z(H.noise(n, 400, seed + 7))
    rgb = (H.hexrgb('#2a3038') * (grey / 0.2)[..., None]) + cs * (inten * (0.12 + 0.95 * lam))[..., None] * 1.15
    rgb = rgb * (1.0 - 0.7 * np.exp(-(ed / 1.6) ** 2))[..., None]
    Ln = H.sstep(0.03, 0.85, H.lum(rgb))
    M, R, CC = _curves(Ln, (140.0, 255.0), (150.0, 34.0), (90.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_moonstone_glow", "Moonstone Adularescence",
    "Milky translucent moonstone with long silky fibres and soft cornflower-blue glows floating through it.")
def moonstone_glow(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 46 Moonstone Adularescence: milky base + silky streak fibres (5x260 cells @24 deg) + 4 warped Gaussian blue glows modulated by the fibres + inclusion specks; SAT
    n = N
    X, Y = H.xy(n)
    fib = _z(_aniso(n, 5, 260, seed + 1, 24.0))
    fib2 = _z(_aniso(n, 8, 120, seed + 2, 24.0))
    mott = _z(H.fbm(n, seed + 3, cells=(4, 8, 16, 32), gain=0.6))
    Xw = X + 200.0 * _z(H.fbm(n, seed + 4, cells=(2, 3, 5), gain=0.7))
    Yw = Y + 200.0 * _z(H.fbm(n, seed + 5, cells=(2, 3, 5), gain=0.7))
    G = np.zeros((n, n), F32)
    for cx, cy, s_ in ((0.25, 0.30, 330.0), (0.72, 0.22, 280.0), (0.60, 0.70, 360.0), (0.15, 0.85, 260.0)):
        G += np.exp(-(((Xw - cx * n) ** 2) + ((Yw - cy * n) ** 2) * 1.3) / F32(2 * s_ * s_))
    gl = np.clip(G, 0, 1.0) * (0.40 + 0.60 * H.sstep(-0.8, 1.0, 0.7 * fib + 0.6 * fib2))
    fib3 = _z(_aniso(n, 6, 700, seed + 7, 24.0))
    base = H.ramp(np.clip(0.60 + 0.12 * fib + 0.08 * fib2 + 0.08 * fib3 + 0.05 * mott, 0, 1), [(0.0, '#a4acb8'), (0.5, '#d8dce4'), (1.0, '#f6f6f4')])
    gcol = H.ramp(np.clip(gl, 0, 1), [(0.0, '#dce4ff'), (0.45, '#86a8ff'), (1.0, '#4a78f0')])
    rgb = base * (1.0 - 0.65 * gl)[..., None] + gcol * (gl * 0.95)[..., None]
    spk = H.flake_mask(n, 0.002, seed + 6)
    rgb = np.clip(rgb + spk[..., None] * 0.30, 0, 1)
    Ln = H.sstep(0.78, 0.97, H.lum(rgb))  # [S20 spec-widen 2026-10-12] moonstone luma lives in 0.77-0.97; window it so the spec follows the glows
    M, R, CC = _curves(Ln, (190.0, 20.0), (40.0, 170.0), (20.0, 110.0))
    return _out(rgb, M, R, CC)


@_f("wx_fire_agate", "Fire Agate Bubbles",
    "Packed brown botryoidal bubbles, each glowing fire orange at its crown and shading through gold to green at its rim.")
def fire_agate(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 47 Fire Agate Bubbles: 40 px Voronoi domes (radius 18-26), bump-lit, thin-film hue by dome slope (orange crown -> gold -> green rim, per-dome offset), dark brown grooves; CAN
    n = N
    pts = H.jitter_pts(n, 40, seed + 1, 0.9, 20)
    d, lab, sx, sy = H.voronoi(n, pts)
    idx = (lab - 1).astype(np.int64)
    h1 = H.hash01(idx, seed + 2)
    h2 = H.hash01(idx, seed + 3)
    rad = 17.0 + 9.0 * h1
    u = np.clip(d / rad, 0, 1)
    hgt = np.sqrt(np.clip(1.0 - u * u, 0, 1)).astype(F32)
    dif, spc = H.shade(H.blur(hgt, 0.7), 7.0)
    reg = _z(H.fbm(n, seed + 4, cells=(2, 3, 6), gain=0.7))
    t = np.clip(0.12 + 0.62 * (1.0 - hgt) ** 0.9 + 0.75 * (h2 - 0.5) + 0.20 * reg, 0, 1)
    film = H.ramp(t, [(0.0, '#6a2e0c'), (0.22, '#f07818'), (0.46, '#e0b424'), (0.70, '#4ab858'), (0.90, '#18a8a0'), (1.0, '#2870c8')])
    groove = H.sstep(0.90, 0.99, u)
    rgb = film * (0.50 + 0.80 * dif)[..., None] + (spc * 0.45)[..., None]
    rgb = rgb * (1.0 - 0.85 * groove)[..., None] + H.hexrgb('#3a1a0a') * (0.85 * groove)[..., None]
    Ln = H.sstep(0.03, 0.85, H.lum(rgb))
    M, R, CC = _curves(Ln, (150.0, 235.0), (66.0, 18.0), (30.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_bornite_tarnish", "Peacock Ore Tarnish",
    "Coppery metal blotched with tarnish films of gold, magenta, purple, blue and teal, crazed with fine dark veins.")
def bornite_tarnish(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 48 Peacock Ore Tarnish: two-scale blotch thickness map (cells 3-12 + 10-40) terraced by sin, copper->gold->magenta->purple->blue->teal film ramp, metallic grain, vein cracks; CHR
    n = N
    r1 = _z(H.fbm(n, seed + 1, cells=(3, 6, 12), gain=0.7))
    r2 = _z(H.fbm(n, seed + 2, cells=(10, 20, 40), gain=0.7))
    r3 = _z(H.fbm(n, seed + 3, cells=(60, 100, 160), gain=0.7))
    t = 0.5 + 0.24 * r1 + 0.14 * r2 + 0.11 * r3
    t = t + 0.05 * np.sin(6.2832 * t * 7.0)
    film = H.ramp(np.clip(t, 0, 1), [(0.0, '#a84e1c'), (0.16, '#d88c46'), (0.30, '#e8c23e'), (0.44, '#c8368e'), (0.58, '#6a28c0'), (0.74, '#2a50e0'), (0.88, '#18b8d0'), (1.0, '#d8a050')])
    grain = 0.84 + 0.30 * H.grain(n, seed + 4) + 0.12 * _z(H.noise(n, 120, seed + 8))
    veins = H.zero_set_line(_z(H.fbm(n, seed + 5, cells=(14, 28, 56), gain=0.6)), 1.6)
    rgb = film * grain[..., None] * (1.0 - 0.75 * veins)[..., None]
    rgb = np.clip(rgb, 0, 1)
    Ln = H.sstep(0.03, 0.85, H.lum(rgb))
    M, R, CC = _curves(Ln, (160.0, 255.0), (110.0, 4.0), (100.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(rgb, M, R, CC)


@_f("wx_ammolite_mosaic", "Ammolite Dragon Skin",
    "A crazed mosaic of tiny iridescent tiles, each tile its own red, orange, green, blue or violet, split by a fine crack network.")
def ammolite_mosaic(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 49 Ammolite Dragon Skin (v3, coordinator review 2): 21 px Voronoi tiles each owning its hue (+ per-tile tilt shift), 1.8 px dark crazing cracks, second 85 px fracture lattice with 3.5 px dark seams, dome shading; CHR
    n = N
    X, Y = H.xy(n)
    d, lab, sx, sy = H.voronoi(n, H.jitter_pts(n, 21, seed + 1, 0.85, 10))
    idx = (lab - 1).astype(np.int64)
    ed = H.edge_dist(lab)
    h1 = H.hash01(idx, seed + 2)
    h2 = H.hash01(idx, seed + 3)
    h3 = H.hash01(idx, seed + 6)
    lx = X - sx[idx].astype(F32)
    ly = Y - sy[idx].astype(F32)
    a = 6.2832 * h3
    tilt = (lx * np.cos(a) + ly * np.sin(a)) / 11.0
    reg = _z(H.fbm(n, seed + 4, cells=(2, 3, 6), gain=0.7))
    t = np.mod(h1 + 0.10 * tilt + 0.06 * reg, 1.0)
    col = H.ramp(t, [(0.0, '#e00028'), (0.17, '#ff7414'), (0.33, '#f2d020'), (0.5, '#20d860'), (0.67, '#18c8d8'), (0.83, '#2850f4'), (1.0, '#c030f0')])
    d2_, lab2_, sx2_, sy2_ = H.voronoi(n, H.jitter_pts(n, 85, seed + 8, 0.9, 40))
    ed2 = H.edge_dist(lab2_)
    dome = 0.50 + 0.50 * np.clip(ed / 9.0, 0, 1) ** 0.8
    craze = H.sstep(1.9, 0.6, ed)
    seam = H.sstep(3.6, 1.2, ed2)
    rgb = col * (dome * (0.75 + 0.25 * h2))[..., None]
    rgb = rgb * (1.0 - 0.92 * craze)[..., None] * (1.0 - 0.97 * seam)[..., None]
    Ln = H.sstep(0.03, 0.8, H.lum(rgb))
    M, R, CC = _curves(Ln, (30.0, 255.0), (150.0, 12.0), (100.0, 16.0))
    return _out(np.clip(rgb, 0, 1), M, R, CC)


@_f("wx_sunstone_aventurine", "Sunstone Copper Glitter",
    "Glowing translucent orange feldspar with sparse, large flat copper platelets glinting gold and white at their own angles.")
def sunstone_aventurine(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 50 Sunstone Copper Glitter (v2, coordinator review 2): translucent amber ground + 9k dim out-of-focus platelets (14-30 px) + 3.5k SPARSE bright front platelets (18-40 px hexagons, random angle + flash) + white-gold glints; FLK copper
    n = N
    z1 = _z(H.fbm(n, seed + 1, cells=(3, 6, 12), gain=0.7))
    z2 = _z(H.fbm(n, seed + 2, cells=(24, 48), gain=0.6))
    ground = H.ramp(np.clip(0.48 + 0.18 * z1 + 0.08 * z2, 0, 1), [(0.0, '#9a3a0c'), (0.5, '#e07020'), (1.0, '#f8b45c')])
    ang6 = np.linspace(0.0, 6.2832, 7)[:-1]

    def layer(K, wlo, whi, sd, scale=1.0, keep=None):
        rr = H.rng(sd)
        cx = rr.random(K) * n
        cy = rr.random(K) * n
        a = rr.uniform(0, np.pi, K)
        w = rr.uniform(wlo, whi, K)
        h = w * rr.uniform(0.40, 0.65, K)
        fl = rr.random(K) ** 1.6
        if keep is not None:
            m = fl > keep
            cx, cy, a, w, h, fl = cx[m], cy[m], a[m], w[m], h[m], fl[m]
        w = w * scale
        h = h * scale
        c, s_ = np.cos(a), np.sin(a)
        px = np.cos(ang6)[None, :] * (w[:, None] * 0.5)
        py = np.sin(ang6)[None, :] * (h[:, None] * 0.5)
        pl = np.zeros((len(cx), 6, 2), F32)
        pl[..., 0] = cx[:, None] + c[:, None] * px - s_[:, None] * py
        pl[..., 1] = cy[:, None] + s_[:, None] * px + c[:, None] * py
        cv = H.fills3(n, pl, np.stack([fl * 255.0, np.full(len(cx), 255.0), np.zeros(len(cx))], 1))
        return H.u8f(cv[..., 0]), H.u8f(cv[..., 1])

    Bd, Md = layer(9000, 14.0, 30.0, seed + 3)
    Bf, Mf = layer(3500, 18.0, 40.0, seed + 4)
    Bg, Mg = layer(3500, 18.0, 40.0, seed + 4, scale=0.42, keep=0.55)
    Md = H.blur(Md, 1.3)
    cd = H.ramp(Bd, [(0.0, '#5a2008'), (0.5, '#9a4a14'), (1.0, '#d88a30')])
    cf = H.ramp(Bf, [(0.0, '#7a3010'), (0.4, '#d8782a'), (0.75, '#ffb858'), (1.0, '#fff0c0')])
    rgb = ground * (1.0 - 0.50 * Md)[..., None] + cd * (0.50 * Md)[..., None]
    rgb = rgb * (1.0 - 0.97 * Mf)[..., None] + cf * (0.97 * Mf)[..., None]
    rgb = rgb + (Mg * 0.85)[..., None] * H.hexrgb('#fff4cc')
    rgb = np.clip(rgb, 0, 1)
    Ln = H.sstep(0.15, 0.85, H.lum(rgb))
    M, R, CC = _curves(Ln, (40.0, 255.0), (150.0, 12.0), (110.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_alexandrite_shift", "Alexandrite Twin",
    "Cut-gem facets that read teal green on one side of the car and raspberry red on the other, with a grey change zone.")
def alexandrite_shift(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 51 Alexandrite Twin: 92 px facets with random tilt brightness + 32 px sub-facets + bright edge lines; hue switches teal-green -> raspberry across X (warped step); CHR
    n = N
    X, Y = H.xy(n)
    pts = H.jitter_pts(n, 92, seed + 1, 0.95, 40)
    d, lab, sx, sy = H.voronoi(n, pts)
    idx = (lab - 1).astype(np.int64)
    ed = H.edge_dist(lab)
    tilt = H.hash01(idx, seed + 2)
    pts2 = H.jitter_pts(n, 26, seed + 3, 0.95, 16)
    d2, lab2, sx2, sy2 = H.voronoi(n, pts2)
    idx2 = (lab2 - 1).astype(np.int64)
    tilt2 = H.hash01(idx2, seed + 4)
    ed2 = H.edge_dist(lab2)
    b = np.clip(0.10 + 0.62 * tilt ** 1.4 + 0.45 * (tilt2 - 0.5), 0, 1)
    zr = _z(H.fbm(n, seed + 5, cells=(2, 3, 5), gain=0.7))
    s = H.sstep(0.38, 0.62, X / F32(n) + 0.13 * zr)
    g = H.ramp(b, [(0.0, '#03281a'), (0.45, '#10b088'), (0.8, '#58e8c4'), (1.0, '#c8fff0')])
    rr = H.ramp(b, [(0.0, '#2a0414'), (0.45, '#cc1e66'), (0.8, '#ff6aa8'), (1.0, '#ffd0e4')])
    mid = np.exp(-((s - 0.5) / 0.30) ** 2) * (1.0 - np.abs(2.0 * s - 1.0) ** 0.5)
    rgb = g * (1.0 - s)[..., None] + rr * s[..., None]
    rgb = rgb * (1.0 - 0.45 * mid)[..., None] + (mid * 0.12 * b)[..., None] * H.hexrgb('#8890a0')
    line = np.exp(-(ed / 1.3) ** 2) * 0.55 + np.exp(-(ed2 / 1.0) ** 2) * 0.38
    rgb = np.clip(rgb * (1.0 - 0.25 * np.exp(-(ed2 / 3.0) ** 2))[..., None] + line[..., None] * H.hexrgb('#e8f0f4'), 0, 1)
    Ln = H.sstep(0.03, 0.9, H.lum(rgb))
    M, R, CC = _curves(Ln, (210.0, 255.0), (90.0, 8.0), (70.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_tigers_eye", "Tiger's Eye Chatoyance",
    "Silky golden-brown fibres with narrow bright cat's-eye bands that roll across the surface.")
def tigers_eye(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 52 Tiger's Eye Chatoyance: three streak-fibre scales (5x600, 4x300 cells @22 deg + wide 3x90), chatoyant light bands (period 150 px, power 4, warped), gold ramp; BRU along fibres
    n = N
    X, Y = H.xy(n)
    f1 = _z(_aniso(n, 5, 600, seed + 1, 22.0))
    f2 = _z(_aniso(n, 4, 300, seed + 2, 22.0))
    f3 = _z(_aniso(n, 3, 90, seed + 3, 22.0))
    zr = _z(H.fbm(n, seed + 4, cells=(2, 3, 5), gain=0.7))
    ca, sa = np.cos(np.deg2rad(22.0)), np.sin(np.deg2rad(22.0))
    ph = (Y * ca - X * sa) / 150.0 + 1.5 * zr
    band = (0.5 + 0.5 * np.cos(6.2832 * ph)) ** 4
    wide = 0.5 + 0.5 * np.cos(6.2832 * ph / 3.1 + 1.0)
    t = np.clip(0.34 + 0.18 * f1 + 0.10 * f2 + 0.10 * f3 + 0.40 * band + 0.10 * (wide - 0.5), 0, 1)
    rgb = H.ramp(t, [(0.0, '#1a0c04'), (0.3, '#5a3010'), (0.55, '#b8781c'), (0.8, '#e8b038'), (1.0, '#fff0a8')])
    Ln = H.sstep(0.03, 0.9, H.lum(rgb))
    M, R, CC = _curves(Ln, (205.0, 255.0), (120.0, 40.0), (30.0, 16.0))
    return _out(rgb, M, R, CC)
# -------------------------------------------------------------------------
# STONES 53-58
# -------------------------------------------------------------------------
def _potential(n, m, seed, K, rlo, rhi, warp):
    """Sum of K soft bumps s/(1+(d/R)^2) at m x m (positions in n-px space), domain-warped; returns float32 (m, m) upsampled to n."""
    r = H.rng(seed)
    a = np.arange(m, dtype=F32) * F32(n / m)
    Xm = np.broadcast_to(a[None, :], (m, m))
    Ym = np.broadcast_to(a[:, None], (m, m))
    Xw = Xm + warp * _z(H.fbm(m, seed + 1, cells=(3, 6, 12), gain=0.7))
    Yw = Ym + warp * _z(H.fbm(m, seed + 2, cells=(3, 6, 12), gain=0.7))
    cx = r.random(K) * n
    cy = r.random(K) * n
    Rr = r.uniform(rlo, rhi, K)
    sg = r.uniform(0.6, 1.4, K)
    f = np.zeros((m, m), F32)
    for i in range(K):
        f += F32(sg[i]) / (1.0 + ((Xw - cx[i]) ** 2 + (Yw - cy[i]) ** 2) / F32(Rr[i] ** 2))
    return H.ups(np.ascontiguousarray(f, F32), n)


@_f("wx_malachite_bands", "Malachite Bands",
    "Green malachite banded in merging concentric rings around many centres, dark black-green to bright mint.")
def malachite_bands(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 53 Malachite Bands: 26 bump potentials (merging contours, warped 90 px) -> 9 bands/unit with sawtooth brightness + dark band walls, mottle; SAT
    n = N
    f = _potential(n, 512, seed, 26, 110.0, 260.0, 90.0)
    ph = f * 9.0 + 0.35 * _z(H.fbm(n, seed + 3, cells=(8, 16, 32), gain=0.7))
    fr = (ph - np.floor(ph)).astype(F32)
    lum = 0.20 + 0.80 * fr ** 1.3
    wall = np.exp(-(np.minimum(fr, 1.0 - fr) / 0.06) ** 2)
    tab = 0.88 + 0.16 * _z(H.noise(n, 300, seed + 4))
    col = H.ramp(np.clip(lum * tab, 0, 1), [(0.0, '#03140c'), (0.35, '#0a6a3c'), (0.7, '#16a864'), (1.0, '#a0ecbc')])
    rgb = col * (1.0 - 0.75 * wall)[..., None]
    Ln = H.sstep(0.02, 0.8, H.lum(rgb))
    M, R, CC = _curves(Ln, (20.0, 140.0), (170.0, 30.0), (130.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(rgb, M, R, CC)


@_f("wx_rainbow_hematite", "Rainbow Hematite",
    "Mirror-black kidney-ore domes with a rainbow oxide film burning at every rim and bright pinpoint reflections.")
def rainbow_hematite(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 54 Rainbow Hematite (v3): 120 px Voronoi kidney domes (radius 52-66) cut into 6 concentric terraces, one thin-film rainbow colour per terrace, black-chrome crown, sharp spec glints; CHR
    n = N
    pts = H.jitter_pts(n, 120, seed + 1, 0.9, 54)
    d, lab, sx, sy = H.voronoi(n, pts)
    idx = (lab - 1).astype(np.int64)
    h1 = H.hash01(idx, seed + 2)
    h2 = H.hash01(idx, seed + 3)
    rad = 52.0 + 14.0 * h1
    u = np.clip(d / rad, 0, 1)
    big = _z(H.fbm(n, seed + 4, cells=(4, 8, 16), gain=0.7))
    kk = np.floor(u * 6.0)
    us = (kk + H.sstep(0.65, 1.0, u * 6.0 - kk)) / 6.0
    hgt = np.sqrt(np.clip(1.0 - us * us, 0, 1)).astype(F32) + 0.10 * big
    dif, spc = H.shade(H.blur(hgt.astype(F32), 0.8), 11.0)
    regz = _z(H.fbm(n, seed + 6, cells=(2, 3, 6), gain=0.7))
    dnm = 250.0 + 105.0 * kk + 90.0 * h2 + 60.0 * big + 170.0 * regz
    film = H.thinfilm(dnm, 1.33, 2400.0)
    lipf = u * 6.0 - kk
    rim = (0.34 + 0.66 * H.sstep(0.35, 0.90, lipf)) * H.sstep(0.06, 0.30, u) * H.sstep(1.02, 0.90, u) + 0.04
    film = np.clip(0.5 + 2.0 * (film - 0.5), 0, 1)
    rgb = H.hexrgb('#0e0e14') * (0.45 + 0.9 * dif)[..., None] + film * (rim * (0.40 + 0.90 * dif))[..., None] * 1.10 + (spc * 0.55)[..., None] + (0.07 * dif * (1.0 - u))[..., None] * H.hexrgb('#a8c0ff')
    Ln = H.sstep(0.03, 0.9, H.lum(rgb))
    M, R, CC = _curves(Ln, (150.0, 255.0), (110.0, 20.0), (122.0, 16.0))  # [S20 story-split] hematite: deeper clearcoat range
    return _out(rgb, M, R, CC)


def _hopper_master(S=256):
    gx, gy = H.tile_xy(S)
    ax = np.abs(gx) / (S * 0.5)
    ay = np.abs(gy) / (S * 0.5)
    cheb = np.maximum(ax, ay)
    K = 9
    dep = (1.0 - cheb) * K
    lev = np.floor(dep)
    fr = dep - lev
    sidex = ax >= ay
    nx = np.where(sidex, np.sign(gx), 0.0)
    ny = np.where(sidex, 0.0, np.sign(gy))
    lit = np.clip(0.5 - 0.5 * (nx + ny) * 0.707, 0, 1)
    ox = np.clip(0.5 + 2.1 * (H.thinfilm(210.0 + 85.0 * lev, 1.33, 4000.0) - 0.5), 0, 1)
    tread = 0.80 - 0.04 * lev
    riser = 0.30 + 0.70 * lit
    isr = H.sstep(0.28, 0.20, fr)
    shade = tread * (1 - isr) + riser * isr
    col = ox * shade[..., None]
    line = np.exp(-((fr - 0.0) / 0.03) ** 2)
    col = col * (1 - 0.5 * line)[..., None]
    al = H.sstep(1.0, 0.975, cheb)
    out = np.zeros((S, S, 4), F32)
    out[..., :3] = np.clip(col, 0, 1) * al[..., None]
    out[..., 3] = al
    return out


@_f("wx_bismuth_hopper", "Bismuth Hopper Crystals",
    "Dense stepped square-spiral hopper crystals, every terrace tinted in rainbow oxide gold, magenta, teal and blue.")
def bismuth_hopper(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 55 Bismuth Hopper Crystals: ~150 square terrace stamps (9 steps, bevel-lit risers, thin-film oxide per depth; 3 sizes x 5 angles), painter-ordered; CHR
    n = N
    r = H.rng(seed)
    tiles = _rot_tiles(_hopper_master(), (130, 180, 240), (-9, -4, 0, 4, 9))
    g = 10
    sp = n / g
    gi, gj = np.meshgrid(np.arange(g + 1), np.arange(g + 1))
    ex = ((gi + 0.5 * (gj & 1) + r.uniform(-0.28, 0.28, gi.shape)) * sp).ravel()
    ey = ((gj + r.uniform(-0.28, 0.28, gi.shape)) * sp).ravel()
    ti = r.integers(0, 3, ex.size) * 5 + r.integers(0, 5, ex.size)
    tint = np.ones((ex.size, 3), F32) * r.uniform(0.85, 1.12, (ex.size, 1)).astype(F32)
    tint = tint * np.array([1.0, 1.0, 1.0], F32) + (r.random((ex.size, 3)).astype(F32) - 0.5) * 0.18
    o = np.argsort(ey)
    z = _z(H.fbm(n, seed + 1, cells=(6, 12, 24), gain=0.6))
    img = (H.hexrgb('#2a1c12') * (0.7 + 0.35 * z)[..., None]).astype(F32)
    H.splat_rgba(img, tiles, ti[o], ex[o], ey[o], tint=tint[o])
    img = np.clip(img, 0, 1)
    Ln = H.sstep(0.03, 0.8, H.lum(img))
    M, R, CC = _curves(Ln, (170.0, 255.0), (90.0, 16.0), (60.0, 16.0))
    return _out(img, M, R, CC)


@_f("wx_pyrite_cubes", "Fool's Gold Cubes",
    "Clustered sharp brassy pyrite cubes at every angle, each face finely striated and shaded in three tones.")
def pyrite_cubes(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 56 Fool's Gold Cubes: ~1500 isometric cubes (26-66 px, random yaw, 3 lit faces, 5 striation lines per face) in ~70 clusters on dark host rock, painter-ordered by y; CHR
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(6, 12, 24, 48), gain=0.6))
    img = (H.hexrgb('#262420') * (0.75 + 0.35 * z)[..., None]).astype(F32)
    K = 3400
    ncl = 100
    cc = r.random((ncl, 2)) * n
    asg = r.integers(0, ncl, K)
    cx = cc[asg, 0] + r.normal(0, 120, K)
    cy = cc[asg, 1] + r.normal(0, 120, K)
    ok = (cx > -80) & (cx < n + 80) & (cy > -80) & (cy < n + 80)
    cx, cy = cx[ok], cy[ok]
    K = len(cx)
    sz = r.uniform(22, 58, K)
    yaw = r.uniform(0, np.pi / 2, K)
    brass = r.uniform(0.80, 1.20, K)
    grey = r.random(K) < 0.30
    o = np.argsort(cy)
    phi = np.deg2rad(32.0)
    cph, sph = np.cos(phi), np.sin(phi)
    L = np.array([-0.5, 0.7, 0.5])
    L = L / np.linalg.norm(L)
    base_hex = np.array(H.hexrgb('#d8b040'))
    grey_hex = np.array(H.hexrgb('#a8a898'))
    SC = 8.0
    for k in o:
        s_ = sz[k] * 0.5
        c, sn = np.cos(yaw[k]), np.sin(yaw[k])
        colb = (grey_hex if grey[k] else base_hex) * brass[k]
        for a in range(3):
            for sg in (1.0, -1.0):
                b_, c_ = [(1, 2), (0, 2), (0, 1)][a]
                cor = []
                for (p, q) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    v = np.zeros(3)
                    v[a] = sg
                    v[b_] = p
                    v[c_] = q
                    cor.append(v)
                nv = np.zeros(3)
                nv[a] = sg
                x1 = nv[0] * c + nv[2] * sn
                z1 = -nv[0] * sn + nv[2] * c
                y1 = nv[1]
                y2 = y1 * cph - z1 * sph
                z2 = y1 * sph + z1 * cph
                if z2 <= 0.05:
                    continue
                shade = 0.30 + 0.80 * max(0.0, x1 * L[0] + y2 * L[1] + z2 * L[2])
                pts = []
                for v in cor:
                    vx = v[0] * c + v[2] * sn
                    vz = -v[0] * sn + v[2] * c
                    vy = v[1]
                    vy2 = vy * cph - vz * sph
                    pts.append((cx[k] + vx * s_, cy[k] - vy2 * s_))
                P = np.array(pts)
                col = tuple(float(v) for v in np.clip(colb * shade, 0, 1))
                cv2.fillPoly(img, [np.round(P * SC).astype(np.int32)], col, cv2.LINE_AA, 3)
                dk = tuple(float(v) * 0.55 for v in col)
                for t in np.linspace(0.12, 0.88, 5):
                    p0 = P[0] + t * (P[1] - P[0])
                    p1 = P[3] + t * (P[2] - P[3])
                    cv2.line(img, (int(p0[0] * SC), int(p0[1] * SC)), (int(p1[0] * SC), int(p1[1] * SC)), dk, 1, cv2.LINE_AA, 3)
                cv2.polylines(img, [np.round(P * SC).astype(np.int32)], True, (0.04, 0.035, 0.02), 1, cv2.LINE_AA, 3)
    img = np.clip(img, 0, 1).astype(F32)
    Ln = H.sstep(0.04, 0.8, H.lum(img))
    M, R, CC = _curves(Ln, (120.0, 255.0), (120.0, 30.0), (80.0, 16.0))
    return _out(img, M, R, CC)


@_f("wx_chalcopyrite_bloom", "Chalcopyrite Bloom",
    "Brassy gold faceted ore points tarnishing in many 100 px patches to rich blue, teal and purple, all over the surface.")
def chalcopyrite_bloom(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 57 Chalcopyrite Bloom (v2, coordinator review 2): 30x26 staggered faceted pyramids; tarnish bloom field now cells 7-28 (+20-80 detail) = many ~100 px patches (gold -> blue -> teal -> purple -> magenta) all over instead of two halves; ANO
    n = N
    X, Y = H.xy(n)
    Xw = X + 6.0 * _z(H.fbm(n, seed + 1, cells=(10, 20), gain=0.6))
    Yw = Y + 6.0 * _z(H.fbm(n, seed + 2, cells=(10, 20), gain=0.6))
    row, col, lx, ly = H.cells_rows(Xw, Yw, 30.0, 26.0, 0.5)
    cr = H.cellhash(row, col, seed)
    ang = (cr - 0.5) * 1.1
    ca, sa = np.cos(ang), np.sin(ang)
    px = lx * ca + ly * sa
    py = -lx * sa + ly * ca
    ax_ = np.abs(px) / 15.0
    ay_ = np.abs(py) / 13.0
    cheb = np.maximum(ax_, ay_)
    h = np.clip(1.0 - cheb, 0, 1)
    sidex = ax_ >= ay_
    nx = np.where(sidex, np.sign(px), 0.0)
    ny = np.where(sidex, 0.0, np.sign(py))
    shade = np.clip(0.52 - 0.48 * (nx + ny) * 0.707, 0, 1)
    tip = np.exp(-(cheb / 0.16) ** 2) * 0.35
    zb = _z(H.fbm(n, seed + 3, cells=(7, 14, 28), gain=0.7)) + 0.5 * _z(H.fbm(n, seed + 7, cells=(20, 40, 80), gain=0.6))
    b = H.sstep(-1.7, 1.7, zb)
    t = np.clip(0.06 + 0.86 * b + 0.18 * (h - 0.3) + 0.10 * (cr - 0.5), 0, 1)
    colr = H.ramp(t, [(0.0, '#bf9628'), (0.22, '#e8c03c'), (0.40, '#d09a44'), (0.52, '#2860e0'), (0.68, '#18a8d8'), (0.82, '#7a38d0'), (1.0, '#c84890')])
    rgb = colr * (0.40 + 0.70 * shade)[..., None] + tip[..., None]
    rgb = rgb * (1.0 - 0.60 * H.sstep(0.90, 1.0, cheb))[..., None]
    Ln = H.sstep(0.03, 0.9, H.lum(rgb))
    M, R, CC = _curves(Ln, (170.0, 255.0), (100.0, 30.0), (80.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_spectrolite_veins", "Spectrolite Fire Veins",
    "Dark stone cut by branching veins of vivid red, green, blue and violet fire that change colour along their length.")
def spectrolite_veins(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 58 Spectrolite Fire Veins: three zero-set vein networks (widths 3.4/2.0/1.2 px at scales 10/22/48 cells) coloured by a travelling hue field + glow + flash patches on a dark mottled stone; CHR veins
    n = N
    X, Y = H.xy(n)
    V = np.zeros((n, n), F32)
    for cells, wd, amp, salt in ((10, 3.4, 1.0, 11), (22, 2.0, 0.85, 12), (48, 1.2, 0.65, 13)):
        zf = _z(H.fbm(n, seed + salt, cells=(cells, cells * 2), gain=0.6))
        V = np.maximum(V, amp * H.zero_set_line(zf, wd))
    zh = _z(H.fbm(n, seed + 4, cells=(3, 6, 12), gain=0.7))
    hh = np.mod(0.9 * zh + 0.5 * X / F32(n), 1.0)
    hue = H.hsv(hh, 0.95, 1.0)
    glow = H.blur(V, 6.0)
    fl = H.sstep(1.2, 2.2, _z(H.fbm(n, seed + 5, cells=(5, 10, 20), gain=0.7))) * 0.32
    mott = 0.9 + 0.2 * _z(H.noise(n, 160, seed + 6))
    base = H.hexrgb('#171922') * mott[..., None]
    rgb = base + hue * (V * 1.0 + glow * 0.55 + fl * 0.6)[..., None]
    rgb = np.clip(rgb, 0, 1)
    Ln = H.sstep(0.05, 0.9, H.lum(rgb))
    M, R, CC = _curves(Ln, (20.0, 255.0), (120.0, 10.0), (70.0, 16.0))
    return _out(rgb, M, R, CC)
# -------------------------------------------------------------------------
# FILMS 59-66
# -------------------------------------------------------------------------
def _sat(c, k=1.4):
    return np.clip(0.5 + k * (c - 0.5), 0, 1).astype(F32)


@_f("wx_soap_film", "Soap Film Swirl",
    "Thin-film interference swirls of magenta, gold, cyan and green curling through each other, with black thin-film spots.")
def soap_film(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 59 Soap Film Swirl: curl-flow double-warped thickness field -> thin-film interference colour (140-1300 nm, drains downward), 16 fine bands/unit, ragged black thin spots; ANO
    n = N
    X, Y = H.xy(n)
    u, v = H.curl_field(512, seed + 1, cells=(2, 3, 5))
    z0 = _z(H.fbm(n, seed + 2, cells=(2, 3, 6, 12), gain=0.7))
    uu = H.ups(np.ascontiguousarray(u, F32), n)
    vv = H.ups(np.ascontiguousarray(v, F32), n)
    zw = _z(H.warp(z0, 190.0 * uu, 190.0 * vv))
    dnm = 180.0 + 640.0 * (0.5 + 0.5 * np.clip(zw / 2.2, -1, 1)) + 260.0 * (Y / F32(n)) + 14.0 * _z(_aniso(n, 40, 10, seed + 7, 0.0))
    film = _sat(H.thinfilm(dnm, 1.33, 1400.0), 1.3)
    fine = 0.60 + 0.40 * np.sin(6.2832 * (zw * 13.0 + 0.55 * _z(H.fbm(n, seed + 8, cells=(40, 80, 160), gain=0.7))))
    zb = _z(H.fbm(n, seed + 3, cells=(6, 12, 24), gain=0.7))
    spot = H.sstep(1.35, 1.75, zb)
    rgb = film * (0.30 + 0.70 * fine)[..., None] * (1.0 - spot)[..., None] + 0.03
    Ln = H.sstep(0.03, 0.9, H.lum(rgb))
    M, R, CC = _curves(Ln, (110.0, 255.0), (130.0, 6.0), (100.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(rgb, M, R, CC)


@_f("wx_oil_puddle", "Oil on Wet Asphalt",
    "Rainbow oil slicks floating in puddles over dark wet asphalt, every aggregate stone showing through.")
def oil_puddle(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 60 Oil on Wet Asphalt: 9 px Voronoi aggregate stones (grey, 0.08-0.34) + puddle mask (3 cells) carrying curl-warped thin-film oil colour at 80% over darkened stone; WET
    n = N
    d, lab, sx, sy = H.voronoi(n, H.jitter_pts(n, 9, seed + 1, 0.9, 4))
    idx = (lab - 1).astype(np.int64)
    h = H.hash01(idx, seed + 2)
    ed = H.edge_dist(lab)
    d2_, lab2_, sx2_, sy2_ = H.voronoi(n, H.jitter_pts(n, 24, seed + 7, 0.9, 10))
    idx2_ = (lab2_ - 1).astype(np.int64)
    big_ = H.sstep(8.0, 4.0, d2_) * (H.hash01(idx2_, seed + 8) < 0.55) * (0.15 + 0.30 * H.hash01(idx2_, seed + 9))
    stone = 0.08 + 0.26 * h ** 1.5 + 0.03 * H.grain(n, seed + 3) + big_
    asph = H.hexrgb('#b8bcc4') * stone[..., None] * (1.0 - 0.5 * np.exp(-(ed / 1.2) ** 2))[..., None]
    zm = _z(H.fbm(n, seed + 4, cells=(3, 6, 12), gain=0.7))
    m = H.sstep(-0.25, 0.65, zm)
    u, v = H.curl_field(512, seed + 5, cells=(2, 3, 5))
    zt = _z(H.fbm(n, seed + 6, cells=(3, 6, 12, 24), gain=0.7))
    zt = _z(H.warp(zt, 120.0 * H.ups(np.ascontiguousarray(u, F32), n), 120.0 * H.ups(np.ascontiguousarray(v, F32), n)))
    dnm = 200.0 + 950.0 * (0.5 + 0.5 * np.clip(zt / 2.2, -1, 1)) + 30.0 * _z(H.fbm(n, seed + 11, cells=(60, 120, 240), gain=0.7))
    film = _sat(H.thinfilm(dnm, 1.33, 1800.0), 1.35)
    rgb = asph * (1.0 - 0.45 * m)[..., None] + film * (m * 0.80 * (0.40 + 1.1 * stone))[..., None]
    Ln = H.sstep(0.03, 0.7, H.lum(rgb))
    M, R, CC = _curves(Ln, (10.0, 60.0), (120.0, 10.0), (60.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_foam_network", "Bubble Foam Network",
    "Foam of polygonal bubbles in three sizes, bright rainbow-filmed walls, thin dark borders and a window glint in each bubble.")
def foam_network(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 61 Bubble Foam Network (v2, coordinator review 2): Voronoi from three merged lattices (150/84/46 px, thinned) = bubbles of several sizes; 13 px BRIGHT thin-film walls (saturated, value ~1), thin dark Plateau core line, blue-grey bubble interior + window glint; FLK
    n = N
    X, Y = H.xy(n)
    p1 = H.jitter_pts(n, 150, seed + 1, 0.9, 40)
    p2 = H.jitter_pts(n, 84, seed + 2, 0.9, 30)
    p3 = H.jitter_pts(n, 46, seed + 7, 0.9, 20)
    p2 = p2[H.rng(seed + 3).random(len(p2)) < 0.45]
    p3 = p3[H.rng(seed + 8).random(len(p3)) < 0.18]
    d, lab, sx, sy = H.voronoi(n, np.concatenate([p1, p2, p3]))
    idx = (lab - 1).astype(np.int64)
    ed = H.edge_dist(lab)
    h1 = H.hash01(idx, seed + 4)
    lx = X - sx[idx].astype(F32)
    ly = Y - sy[idx].astype(F32)
    reg = _z(H.fbm(n, seed + 5, cells=(2, 3, 6), gain=0.7))
    wall = H.sstep(13.0, 3.0, ed)
    dnm = 200.0 + 560.0 * (1.0 - np.clip(ed / 13.0, 0, 1)) + 380.0 * h1 + 260.0 * reg
    film = _sat(H.thinfilm(dnm, 1.33, 2200.0), 1.55)
    core = np.exp(-(ed / 1.3) ** 2)
    hl = np.exp(-(((lx + 8.0) ** 2 + (ly + 9.0) ** 2) / (2 * 5.5 ** 2)))
    inner = H.hexrgb('#16223c') * (0.7 + 0.5 * h1)[..., None] + film * (0.22 * (0.4 + 0.6 * h1))[..., None] + hl[..., None] * H.hexrgb('#b8d0ff') * 0.55
    rgb = inner * (1.0 - wall)[..., None] + film * (wall * 1.05)[..., None]
    rgb = rgb * (1.0 - 0.85 * core)[..., None]
    flk = H.flake_mask(n, 0.004, seed + 6)
    rgb = np.clip(rgb + flk[..., None] * 0.5, 0, 1)
    Ln = H.sstep(0.03, 0.8, H.lum(rgb))
    M, R, CC = _curves(Ln, (60.0, 200.0), (100.0, 20.0), (70.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_tempered_steel", "Temper Colours",
    "Heat-tinted steel: straw, gold, brown, purple and blue temper bands spreading around many weld patches over fine brushing.")
def tempered_steel(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 62 Temper Colours: 34 bump potentials (merging heat patches, warped 70 px) -> temper ramp grey->straw->gold->brown->purple->blue->pale blue, brushed horizontal grain, faint weld ripples; CHR
    n = N
    f = _potential(n, 512, seed, 34, 90.0, 230.0, 70.0)
    lo_, hi_ = np.percentile(f, (3, 99))
    tt = np.clip((f - lo_) / (hi_ - lo_ + 1e-6), 0, 1.0) ** 1.1
    col = H.ramp(tt, [(0.0, '#8a8e98'), (0.15, '#e6d49a'), (0.30, '#d8a248'), (0.45, '#a45a2a'), (0.60, '#74328e'), (0.78, '#2c48b8'), (0.92, '#78a8d8'), (1.0, '#a8b0b8')])
    brush = _z(_aniso(n, 4, 280, seed + 3, 0.0))
    ripple = 0.5 + 0.5 * np.cos(6.2832 * f * 16.0)
    streak = _z(_aniso(n, 8, 340, seed + 5, 0.0))
    micro = _z(_aniso(n, 3, 900, seed + 8, 0.0))
    rgb = col * (0.86 + 0.10 * brush + 0.50 * (ripple - 0.5) + 0.07 * streak + 0.05 * micro + 0.06 * H.grain(n, seed + 6))[..., None]
    rgb = np.clip(rgb, 0, 1)
    Ln = H.sstep(0.05, 0.8, H.lum(rgb))
    M, R, CC = _curves(Ln, (160.0, 255.0), (130.0, 6.0), (90.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(rgb, M, R, CC)


@_f("wx_titanium_anodize", "Anodized Titanium Steps",
    "Diagonal terraces of anodised titanium stepping through gold, magenta, purple, blue, teal and green, each cut in fine micro-steps.")
def titanium_anodize(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 63 Anodized Titanium Steps: 240 px colour terraces (6-colour cycle) along a 35 deg warped axis, 10 micro-steps per terrace (24 px) with edge lines, brushed grain; ANO
    n = N
    X, Y = H.xy(n)
    zr = _z(H.fbm(n, seed + 1, cells=(2, 3, 5), gain=0.7))
    ca, sa = np.cos(np.deg2rad(35.0)), np.sin(np.deg2rad(35.0))
    z = (X * ca + Y * sa) / F32(240.0) + 0.55 * zr
    k = np.floor(z).astype(np.int64)
    fr = (z - k).astype(F32)
    pal = np.array([H.hexrgb(c) for c in ('#d8b040', '#c83890', '#7a38d0', '#2860e8', '#18b8c8', '#30c070')], F32)
    col = pal[np.mod(k, 6)]
    sub = np.floor(fr * 16.0)
    sfr = fr * 16.0 - sub
    lum = 0.40 + 0.022 * sub + 0.26 * np.mod(sub, 2.0)
    edge = np.exp(-(sfr / 0.12) ** 2)
    brush = _z(_aniso(n, 3, 900, seed + 2, 0.0))
    rgb = col * (lum * (0.93 + 0.08 * brush + 0.13 * _z(_aniso(n, 4, 150, seed + 3, 0.0))) * (1.0 - 0.70 * edge))[..., None]
    big = np.exp(-(np.minimum(fr, 1.0 - fr) / 0.012) ** 2)
    rgb = np.clip(rgb * (1.0 - 0.6 * big)[..., None], 0, 1)
    Ln = H.sstep(0.05, 0.8, H.lum(rgb))
    M, R, CC = _curves(Ln, (110.0, 255.0), (6.0, 150.0), (16.0, 100.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(rgb, M, R, CC)


def _bead_master(S=48):
    gx, gy = H.tile_xy(S)
    h = S * 0.5
    nx_, ny_ = gx / h, gy / h
    rr = np.hypot(nx_, ny_)
    nz = np.sqrt(np.clip(1.0 - rr * rr, 0, 1))
    L = np.array([-0.45, -0.5, 0.74])
    L = L / np.linalg.norm(L)
    lam = np.clip(nx_ * L[0] + ny_ * L[1] + nz * L[2], 0, 1)
    pearl = np.array([0.95, 0.92, 0.94], F32)[None, None, :] * (0.30 + 0.80 * lam)[..., None]
    rim = H.thinfilm(260.0 + 420.0 * (1.0 - nz), 1.33, 3000.0) * ((1.0 - nz) ** 1.4 * 0.55)[..., None]
    spec = (lam ** 30) * 0.9
    col = np.clip(pearl + rim + spec[..., None], 0, 1)
    al = H.sstep(1.0, 0.92, rr)
    out = np.zeros((S, S, 4), F32)
    out[..., :3] = col * al[..., None]
    out[..., 3] = al
    return out.astype(F32)


@_f("wx_nacre_beads", "Pearl Bead Strands",
    "Rows of tiny glossy pearls strung in swags that droop and cross each other, in white, rose, champagne and grey.")
def nacre_beads(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 64 Pearl Bead Strands: ~35 draped rows of parabolic swags (260-420 px wide, sag 22-34%), equal arc-length beads (18/22/26 px sphere stamps, per-string tint), painter-ordered by y on velvet; CHR beads
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(4, 8, 16, 100), gain=0.6))
    img = (H.hexrgb('#1c1624') * (0.85 + 0.20 * z)[..., None]).astype(F32)
    tiles = _rot_tiles(_bead_master(), (18, 22, 26), (0,))
    pal = np.array([(1.0, 1.0, 1.0), (1.0, 0.82, 0.88), (1.0, 0.93, 0.78), (0.82, 0.84, 0.92), (1.0, 0.88, 0.80)], F32)
    xs, ys, tn, ti = [], [], [], []
    rows = int(n / 58) + 3
    for j in range(rows):
        y0 = -20.0 + j * 58.0 + r.uniform(-10, 10)
        tint = pal[int(r.integers(0, len(pal)))]
        szi = int(r.integers(0, 3))
        step = (18, 22, 26)[szi] * 0.92
        x = -r.uniform(0, 300)
        while x < n + 100:
            w = r.uniform(260, 420)
            sag = w * r.uniform(0.22, 0.34)
            t = np.linspace(0, 1, 300)
            px = x + t * w
            py = y0 + 4.0 * sag * t * (1.0 - t)
            cs = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(px), np.diff(py)))])
            nb = int(cs[-1] / step)
            ix = np.clip(np.searchsorted(cs, (np.arange(nb) + 0.5) * step), 0, 299)
            xs.extend(px[ix])
            ys.extend(py[ix])
            tn.extend([tint] * nb)
            ti.extend([szi] * nb)
            x += w
    xs = np.array(xs)
    ys = np.array(ys)
    tn = np.array(tn, F32) * r.uniform(0.92, 1.05, (len(xs), 1)).astype(F32)
    ti = np.array(ti)
    o = np.argsort(ys)
    H.splat_rgba(img, tiles, ti[o], xs[o], ys[o], tint=tn[o])
    img = np.clip(img, 0, 1)
    Ln = H.sstep(0.05, 0.85, H.lum(img))
    M, R, CC = _curves(Ln, (0.0, 255.0), (190.0, 6.0), (160.0, 16.0))
    return _out(img, M, R, CC)


@_f("wx_cd_rainbow", "Diffraction Grooves",
    "Silver disc surfaces cut with fine concentric grooves that split reflected light into rainbow sectors.")
def cd_rainbow(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 65 Diffraction Grooves: 760 px Voronoi discs, 9 px groove arcs (cos), two-lobed rainbow sectors (hue by angle, 3 turns, drifting with radius), brushed silver base; BRU along grooves
    n = N
    X, Y = H.xy(n)
    pts = H.jitter_pts(n, 760, seed + 1, 0.8, 300)
    d, lab, sx, sy = H.voronoi(n, pts)
    idx = (lab - 1).astype(np.int64)
    ed = H.edge_dist(lab)
    h = H.hash01(idx, seed + 2)
    dx = X - sx[idx].astype(F32)
    dy = Y - sy[idx].astype(F32)
    r = np.hypot(dx, dy)
    th = np.arctan2(dy, dx) + 6.2832 * h
    groove = 0.5 + 0.5 * np.cos(6.2832 * r / 9.0 + 0.8 * _z(H.noise(n, 60, seed + 3)))
    wedge = (0.5 + 0.5 * np.cos(2.0 * th)) ** 1.6
    hue = np.mod(th / 6.2832 * 3.0 + 0.10 * np.sin(r / 70.0) + 0.10 * np.cos(r / 230.0), 1.0)
    brush = _z(H.noise(n, 700, seed + 4))
    silver = (0.30 + 0.38 * groove) * (0.94 + 0.06 * brush)
    rgb = H.hexrgb('#c8ccd4') * silver[..., None] + H.hsv(hue, 0.92, 1.0) * (wedge * (0.30 + 0.70 * groove) * 0.85)[..., None]
    rgb = rgb * (1.0 - 0.7 * np.exp(-(ed / 2.2) ** 2))[..., None]
    rgb = np.clip(rgb, 0, 1)
    Ln = H.sstep(0.05, 0.9, H.lum(rgb))
    M, R, CC = _curves(Ln, (170.0, 255.0), (150.0, 16.0), (90.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(rgb, M, R, CC)


@_f("wx_aurora_film", "Polar Film",
    "Deep blue cracked polar ice, frosted along white fracture webs, with a slanted rainbow oil film banding each plate.")
def aurora_film(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 66 Polar Film (v2, coordinator review 2): dark clear-ice plates (150 px two lattices + 60 px chips) with white sub-surface fracture web, frost crystals along every crack, fine bubble flecks; slanted thin-film bands (230 nm across a plate) show as 1-2 saturated rainbow bands per plate; WET
    n = N
    X, Y = H.xy(n)
    p1 = H.jitter_pts(n, 150, seed + 1, 0.9, 60)
    p2 = H.jitter_pts(n, 150, seed + 2, 0.9, 60)
    p3 = H.jitter_pts(n, 60, seed + 10, 0.9, 30)
    p2 = p2[H.rng(seed + 3).random(len(p2)) < 0.5]
    p3 = p3[H.rng(seed + 11).random(len(p3)) < 0.10]
    d, lab, sx, sy = H.voronoi(n, np.concatenate([p1, p2, p3]))
    idx = (lab - 1).astype(np.int64)
    ed = H.edge_dist(lab)
    h1 = H.hash01(idx, seed + 4)
    h2 = H.hash01(idx, seed + 5)
    lx = X - sx[idx].astype(F32)
    ly = Y - sy[idx].astype(F32)
    ga = 6.2832 * h1
    slant = (lx * np.cos(ga) + ly * np.sin(ga)) / 75.0
    zf = _z(H.fbm(n, seed + 6, cells=(3, 6, 12), gain=0.7))
    dnm = 300.0 + 600.0 * h2 + 110.0 * slant + 40.0 * zf
    film = _sat(H.thinfilm(dnm, 1.33, 3500.0), 1.2)
    depth = np.clip(0.42 + 0.10 * zf + 0.10 * _z(H.noise(n, 140, seed + 7)) + 0.06 * slant, 0, 1)
    ice = H.ramp(depth, [(0.0, '#14407a'), (0.5, '#3a84b8'), (1.0, '#a4d4f0')])
    veins = np.maximum(H.zero_set_line(_z(H.fbm(n, seed + 9, cells=(8, 16, 32), gain=0.6)), 1.6),
                       0.7 * H.zero_set_line(_z(H.fbm(n, seed + 12, cells=(18, 36, 72), gain=0.6)), 1.1))
    crack = np.exp(-(ed / 1.8) ** 2)
    fn = np.maximum(_z(H.noise(n, 420, seed + 8)), 0)
    frost = H.sstep(30.0, 0.0, ed) * 0.32 * fn + 0.16 * H.sstep(8.0, 0.0, ed)
    fpat = H.sstep(0.6, 1.5, _z(H.fbm(n, seed + 14, cells=(6, 12, 24), gain=0.7))) * fn
    plate = ice * 0.80 + film * 0.28 + (0.42 * fpat)[..., None] * H.hexrgb('#e8f4ff')
    white = H.hexrgb('#f0f8ff')
    plate = plate * (1.0 - 0.7 * veins)[..., None] + white * (0.80 * veins)[..., None]
    plate = plate + frost[..., None] * white
    flk = H.flake_mask(n, 0.006, seed + 13)
    rgb = plate * (1.0 - crack)[..., None] + white * (crack * 0.95)[..., None] + (flk * 0.45)[..., None]
    rgb = np.clip(rgb, 0, 1)
    Ln = H.sstep(0.10, 0.95, H.lum(rgb))
    M, R, CC = _curves(Ln, (20.0, 170.0), (130.0, 6.0), (90.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(rgb, M, R, CC)


@_f("wx_jay_barring", "Blue Jay Barring",
    "Long overlapping wing feathers in vivid azure, every vane crossed by fine black bars and finished with a white tip.")
def jay_barring(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 67 Blue Jay Barring: 76x210 px staggered long-feather lattice (warped 16 px), curved 9 px black bars across each vane (phase per feather), azure ramp per feather + barb hatch, black subterminal band + white tip, pale rachis, shadowed overlaps; MAT
    n = N
    row, col, u, vv, cr, cr2, S, T = _scalelat(n, 76, 210, 30.0, seed, 0.5, (3, 6, 12))
    au = np.abs(u)
    tipv = 0.90 - 0.10 * au ** 2
    inside = H.sstep(tipv + 0.012, tipv - 0.012, vv) * H.sstep(1.0, 0.90, au)
    ph = (vv * 210.0 + 22.0 * u * u) / 14.0 + cr2 * 3.0
    bars = H.sstep(0.36, 0.52, 0.5 + 0.5 * np.cos(6.2832 * ph))
    t = np.clip(0.30 + 0.55 * cr + 0.10 * np.cos(6.2832 * (u * 26.0 + vv * 5.0)), 0, 1)
    blue = H.ramp(t, [(0.0, '#1a46c0'), (0.5, '#2e86ee'), (1.0, '#78cbff')])
    barb = 0.84 + 0.16 * np.cos(6.2832 * (u * 30.0 + vv * 6.0))
    navy = H.hexrgb('#080e30')
    col = blue * (bars * barb)[..., None] + navy * (1.0 - bars)[..., None]
    tipzone = H.sstep(0.76, 0.80, vv)
    sub = H.sstep(0.66, 0.69, vv) * (1.0 - tipzone)
    col = col * (1.0 - sub)[..., None] + navy * sub[..., None]
    col = col * (1.0 - tipzone)[..., None] + H.hexrgb('#eef4ff') * (tipzone * (0.80 + 0.20 * barb))[..., None]
    ra = np.exp(-(u / 0.05) ** 2) * (vv < 0.9)
    col = col + ra[..., None] * H.hexrgb('#a8c4ff') * 0.45
    shade = (1.0 - 0.65 * H.sstep(0.84, 1.0, au)) * (0.55 + 0.45 * H.sstep(0.0, 0.08, vv))
    rgb = col * (shade * inside)[..., None] + H.hexrgb('#02030c') * (1.0 - inside)[..., None]
    rgb = np.clip(rgb, 0, 1)
    Ln = H.sstep(0.03, 0.62, H.lum(rgb))
    M, R, CC = _curves(Ln, (10.0, 70.0), (215.0, 120.0), (200.0, 60.0))
    return _out(rgb, M, R, CC)


@_f("wx_trogon_belly", "Trogon Copper Belly",
    "Warm metallic round breast scales: copper cores, gold then emerald-green rims, the whole body shifting from copper to green.")
def trogon_belly(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 68 Trogon Copper Belly (v2, coordinator review 2): 64x58 px round scale-feather lattice (warped 34 px); WARM palette only (dark copper, copper, bright copper-gold, olive-gold, green, emerald) - rims green, cores copper, regional shift copper->green; arc sheen band + barb hatch + scallop shadow; CHR
    n = N
    row, col, u, vv, cr, cr2, S, T = _scalelat(n, 64, 58, 34.0, seed, 0.5, (2, 3, 5))
    au = np.abs(u)
    tipv = 0.97 - 0.24 * au ** 2.2
    d = np.minimum((1.0 - au) * 32.0, (tipv - vv) * 58.0)
    inside = H.sstep(-0.5, 1.5, d)
    reg = _z(H.fbm(n, seed + 3, cells=(2, 3, 5), gain=0.7))
    regsm = H.sstep(-0.9, 0.9, reg)
    rimn = 1.0 - np.clip(d / 26.0, 0, 1)
    t = np.clip(0.10 + 0.50 * regsm + 0.40 * rimn ** 1.3 + 0.10 * (cr - 0.5), 0, 1)
    col = H.ramp(t, [(0.0, '#4a1a08'), (0.18, '#b44c14'), (0.34, '#e89432'), (0.5, '#d2b838'), (0.66, '#6ab43a'), (0.82, '#18a064'), (1.0, '#0a7060')])
    sheen = np.exp(-((vv - 0.42) / 0.26) ** 2)
    rip = 0.74 + 0.26 * np.cos(6.2832 * d / 9.0 + 2.0 * cr2)
    hatch = 0.76 + 0.24 * np.cos(6.2832 * (vv * 58.0 / 7.0 + au * 2.4)) + 0.45 * np.exp(-(u / 0.04) ** 2) * (vv < tipv)
    glow = 0.72 + 0.28 * H.sstep(0.0, 16.0, d)
    lum = rip * hatch * glow * (0.55 + 0.60 * sheen)
    rgb = col * (lum * inside)[..., None] + H.hexrgb('#2a0e08') * ((1.0 - inside) * (0.45 + 0.55 * H.sstep(1.0, 0.7, vv)))[..., None]
    rgb = np.clip(rgb, 0, 1)
    Ln = H.sstep(0.03, 0.70, H.lum(rgb))
    M, R, CC = _curves(Ln, (140.0, 252.0), (70.0, 10.0), (60.0, 16.0))
    return _out(rgb, M, R, CC)


@_f("wx_chiton_plates", "Chiton Armor Plates",
    "Stacked overlapping chevron armour plates studded with fine pustules and growth lines, each row edged by a dark speckled girdle.")
def chiton_plates(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 69 Chiton Armor Plates: 512 px zig-zag (V ridge) bands 170 px tall (wavy), plate = 11 px Voronoi pustules + 12 px growth lines + jugum ridge, slate/olive/rust/teal/mauve per plate with mottle + cream flecks, dark spiculed girdle strip; SAT
    n = N
    X, Y = H.xy(n)
    Xw = X + 12.0 * H.ups(_z(H.fbm(512, seed + 1, cells=(3, 6, 12), gain=0.7)), n)
    Yw = Y + 12.0 * H.ups(_z(H.fbm(512, seed + 2, cells=(3, 6, 12), gain=0.7)), n)
    W = 512.0
    pc = np.floor(Xw / W)
    xl = Xw - (pc + 0.5) * W
    ax = np.abs(xl)
    yv = Yw + 0.34 * ax
    BH = 170.0
    rw = np.floor(yv / BH).astype(np.int64)
    v = ((yv - rw * BH) / BH).astype(F32)
    pid = rw * 977 + pc.astype(np.int64) * 131
    h1 = H.hash01(np.mod(pid, 1 << 30), seed + 3)
    d, lab, sx, sy = H.voronoi(n, H.jitter_pts(n, 11, seed + 4, 0.9, 5))
    idx = (lab - 1).astype(np.int64)
    hp = H.hash01(idx, seed + 5)
    pust = np.clip(1.0 - d / (4.6 + 2.4 * hp), 0, 1) ** 0.6
    grow = 0.5 + 0.5 * np.cos(6.2832 * v * BH / 12.0 + 0.8 * H.ups(_z(H.noise(512, 60, seed + 6)), n))
    ridge = np.exp(-(ax / 5.0) ** 2)
    bulge = np.sin(np.pi * np.clip(v / 0.8, 0, 1))
    hgt = 0.9 * pust + 0.35 * grow + 2.4 * ridge + 0.6 * bulge
    dif, spc = H.shade(H.blur(hgt.astype(F32), 0.7), 3.0)
    pal = np.array([H.hexrgb(c) for c in ('#3a4c62', '#53502e', '#74391f', '#2b4f50', '#584656')], F32)
    base = pal[np.minimum((h1 * 5).astype(np.int64), 4)]
    mot = 0.70 + 0.50 * H.sstep(-1.0, 1.2, H.ups(_z(H.fbm(1024, seed + 7, cells=(30, 60, 120), gain=0.7)), n))
    fleck = H.sstep(0.80, 1.00, H.ups(_z(H.noise(1024, 140, seed + 8)), n))
    plate = base * (mot * (0.45 + 0.95 * dif) * (0.60 + 0.40 * H.sstep(0.0, 0.05, v)))[..., None]
    plate += H.hexrgb('#d8c8a0') * (0.35 * fleck * dif * (0.60 + 0.40 * H.sstep(0.0, 0.05, v)))[..., None]
    plate += (spc * 0.45 * (0.60 + 0.40 * H.sstep(0.0, 0.05, v)))[..., None]
    lip = np.exp(-(((v - 0.79) / 0.014) ** 2))
    girdle = (H.hexrgb('#34281c') * (0.45 + 1.0 * hp)[..., None] + H.flake_mask(n, 0.010, seed + 9)[..., None] * 0.55).astype(F32)
    pm = H.sstep(0.815, 0.785, v)
    plate *= pm[..., None]
    girdle *= (1.0 - pm)[..., None]
    plate += girdle
    plate += (lip * 0.35)[..., None]
    rgb = np.clip(plate, 0, 1)
    Ln = H.sstep(0.03, 0.75, H.lum(rgb))
    M, R, CC = _curves(Ln, (90.0, 190.0), (150.0, 70.0), (70.0, 30.0))
    return _out(rgb, M, R, CC)


def _nodule_master(S=128, green=False, rot=0.0):
    gx, gy = H.tile_xy(S)
    h = S * 0.5
    nx_, ny_ = gx / h, gy / h
    rr = np.hypot(nx_, ny_)
    th = np.arctan2(ny_, nx_) + rot
    nz = np.sqrt(np.clip(1.0 - rr * rr, 0, 1))
    L = np.array([-0.45, -0.5, 0.74])
    L = L / np.linalg.norm(L)
    lam = np.clip(nx_ * L[0] + ny_ * L[1] + nz * L[2], 0, 1)
    fib = (0.5 + 0.5 * np.cos(th * 30.0 + 0.7 * np.sin(rr * 5.0))) ** 1.4
    ring = 0.5 + 0.5 * np.cos(rr * 6.2832 * 4.0)
    t = np.clip(0.03 + 0.42 * lam + 0.34 * fib + 0.12 * ring, 0, 1)
    if green:
        stops = [(0.0, '#02100a'), (0.35, '#0a5a30'), (0.65, '#18a860'), (0.85, '#60dc98'), (1.0, '#d8ffe8')]
    else:
        stops = [(0.0, '#02051c'), (0.35, '#0a2a90'), (0.65, '#1a5ad8'), (0.85, '#4a9cf4'), (1.0, '#bfe4ff')]
    col = H.ramp(t, stops) * (0.50 + 0.50 * nz ** 0.5)[..., None]
    col = np.clip(col + ((lam ** 26) * 0.75)[..., None], 0, 1)
    al = H.sstep(1.0, 0.94, rr)
    out = np.zeros((S, S, 4), F32)
    out[..., :3] = col * al[..., None]
    out[..., 3] = al
    return out.astype(F32)


@_f("wx_azurite_nodules", "Azurite Nodules",
    "Clusters of deep royal-blue azurite nodules with radial crystal fibres and growth rings, with green malachite beads on black matrix.")
def azurite_nodules(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 70 Azurite Nodules: ~1500 overlapping fibrous-sphere stamps (44/64/92/132 px, 4 fibre phases; 14 curved radial fibres + 4 growth rings), big first / small on top, 18% malachite-green small ones, over black matrix with green crust; CAN
    n = N
    r = H.rng(seed)
    z = _z(H.fbm(n, seed + 1, cells=(8, 16, 32), gain=0.7))
    crust = H.sstep(0.7, 1.4, _z(H.fbm(n, seed + 2, cells=(60, 120), gain=0.7)))
    img = (H.hexrgb('#05060e') * (0.7 + 0.5 * z)[..., None] + crust[..., None] * H.hexrgb('#0c5030') * 0.5).astype(F32)
    sizes = (30, 44, 64, 92, 132)
    tiles = []
    for g in (False, True):
        for ro in range(4):
            tiles += _rot_tiles(_nodule_master(128, g, ro * 1.571), sizes, (0,))
    K = 2300
    si = r.choice(5, K, p=(0.32, 0.28, 0.20, 0.13, 0.07))
    grn = ((r.random(K) < 0.18) & (si <= 1)).astype(np.int64)
    ro = r.integers(0, 4, K)
    ti = (grn * 4 + ro) * 5 + si
    xs = r.uniform(-30, n + 30, K)
    ys = r.uniform(-30, n + 30, K)
    o = np.argsort(-np.array(sizes, np.float64)[si] + r.random(K) * 4.0)
    H.splat_rgba(img, tiles, ti[o], xs[o], ys[o])
    img = np.clip(img, 0, 1)
    Ln = H.sstep(0.03, 0.7, H.lum(img))
    M, R, CC = _curves(Ln, (130.0, 255.0), (100.0, 4.0), (70.0, 16.0))  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    return _out(img, M, R, CC)
