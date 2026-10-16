# -*- coding: utf-8 -*-
"""CRYPTID chapter (wx_ 1-20): hides, fur, scale and bone of things nobody can prove exist.

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
    # [S20 v2] standardise a field to zero mean / unit std (fbm output is neither)
    f = np.asarray(f, F32)
    return ((f - f.mean()) / (f.std() + F32(1e-6))).astype(F32)


def _strands(u, v, p0, steps, h, jitter=None):
    """Bidirectional streamline paths (K, 2*steps+1, 2) through field (u, v)."""
    fw = H.trace(u, v, p0, steps, h)
    bw = H.trace(-u, -v, p0, steps, h)
    return np.concatenate([bw[:, ::-1][:, :-1], fw], 1)


# -------------------------------------------------------------------------
# 1. Sasquatch Pelt - hair tracts combed round whorls
# -------------------------------------------------------------------------
@_f("wx_sasquatch_pelt", "Sasquatch Pelt",
    "Dense matted umber and rust hair strands combed into swirling tracts with whorls where the hair parts.")
def sasquatch_pelt(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 1 Sasquatch Pelt: hair strands traced through a combed flow field with whorl singularities
    n = N
    m = 512
    r = H.rng(seed)
    ang = 1.25 + 0.5 * H.fbm(m, seed + 1, cells=(2, 4, 7), gain=0.7)
    u, v = np.cos(ang).astype(F32), np.sin(ang).astype(F32)
    nw = 11
    cs = r.random((nw, 2)) * m
    st = r.choice([-1.0, 1.0], nw) * r.uniform(1.8, 3.0, nw)
    su, sv = H.vortex_field(m, [tuple(c) for c in cs], st, r.uniform(28, 60, nw))
    u = u + su
    v = v + sv
    nr = np.hypot(u, v) + F32(1e-6)
    u = (u / nr).astype(F32)
    v = (v / nr).astype(F32)
    tract = H.fbm(m, seed + 3, cells=(3, 6, 12), gain=0.7)
    cvs = None
    for K, steps, hh, vlo, vhi in ((42000, 4, 4.0, 26, 100), (52000, 6, 4.4, 55, 175), (9000, 7, 4.6, 140, 235)):
        p0 = r.random((K, 2)).astype(F32) * n
        path = _strands(u, v, p0, steps, hh)
        tr = H.sample(tract, p0[:, 0] / 4.0, p0[:, 1] / 4.0)
        tr = np.clip(0.5 + 0.36 * tr, 0, 1) * 255
        val = r.uniform(vlo, vhi, K)
        cvs = H.lines3(n, path, np.stack([val, tr, np.zeros(K)], 1), 1, canvas=cvs)
    V = H.u8f(cvs[..., 0])
    T = H.u8f(cvs[..., 1])
    um = H.ramp(V, [(0.0, '#26160b'), (0.35, '#4d2f18'), (0.7, '#8a5b30'), (1.0, '#d3a870')])
    ru = H.ramp(V, [(0.0, '#2a110a'), (0.35, '#5a2416'), (0.7, '#9a4824'), (1.0, '#d98a52')])
    bl = H.ramp(V, [(0.0, '#14100c'), (0.4, '#2a2018'), (0.75, '#5a4635'), (1.0, '#a89070')])
    # three tract colours: black-brown, umber, rust, mixed by the low-frequency tract field
    w = np.clip(T * 1.7 - 0.45, 0, 1)[..., None]
    rgb = np.where(w < 0.5, bl + (um - bl) * (w * 2), um + (ru - um) * (w * 2 - 1)).astype(F32)
    rgb *= (0.92 + 0.08 * H.grain(n, seed + 7))[..., None]
    M = H.lerp(110.0, 228.0, V)
    R = H.lerp(158.0, 52.0, V)
    CC = H.lerp(62.0, 18.0, V)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 2. Mothman Wing Dust - vein-curved rows of rounded scales + red eye-spots
# -------------------------------------------------------------------------
@_f("wx_mothman_dust", "Mothman Wing Dust",
    "Rows of big overlapping grey wing scales with pale free edges, and a few large soft red-and-black ocelli.")
def mothman_dust(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 2 Mothman Wing Dust (v2, coordinator review): vein-curved rows of big shingled rounded wing scales (78x44 px) with light free edge / dark tuck + 14 large soft concentric ocelli
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)
    wx = 150.0 * H.fbm(n, seed + 1, cells=(2, 3, 5), gain=0.7)
    wy = 150.0 * H.fbm(n, seed + 2, cells=(2, 3, 5), gain=0.7)
    S = X + wx + 40.0 * np.sin(Y / 140.0 + 2.0 * wx / 150.0)
    T = Y + wy + 30.0 * np.sin(X / 170.0 + wy / 160.0)
    pw, ph = 78.0, 44.0
    row, col, lx, ly = H.cells_rows(S, T, pw, ph, 0.5)
    cr = H.cellhash(row, col, seed)
    u = lx / (pw * 0.5)
    vv = (ly + ph * 0.5) / ph
    edge = 0.80 - 0.34 * u * u
    free = H.sstep(edge + 0.06, edge - 0.05, vv)
    rim = np.exp(-((vv - edge + 0.04) / 0.07) ** 2) * free
    tuck = H.sstep(0.0, 0.40, vv)
    stri = 0.5 + 0.5 * np.sin(u * 9.0 + cr * 6.0)
    reg = H.fbm(n, seed + 4, cells=(4, 8, 16, 40), gain=0.7)
    b = (0.10 + 0.26 * cr + 0.10 * reg) * (0.22 + 0.78 * tuck) + 0.24 * vv * free * tuck + 0.34 * rim + 0.08 * stri
    b = np.clip(b, 0, 1)
    rgb = H.ramp(b, [(0.0, '#121315'), (0.25, '#25282c'), (0.5, '#4a4e53'), (0.75, '#8d908f'), (1.0, '#d6d3ca')])
    # ocelli: soft concentric ash / black / red eye-spots (14, large)
    S2 = 256
    gx, gy = H.tile_xy(S2)
    rr = np.hypot(gx, gy) / (S2 * 0.5)
    prof = H.ramp(np.clip(rr, 0, 1), [(0.0, '#0b0404'), (0.12, '#0b0404'), (0.24, '#7a0b0d'), (0.38, '#b81c20'), (0.50, '#5a0a0d'),
                                      (0.60, '#120808'), (0.72, '#4a4640'), (0.85, '#8a867e'), (1.0, '#a09c92')])
    al = H.sstep(1.0, 0.80, rr)
    hl = np.exp(-(((gx + 0.14 * S2 * 0.5) ** 2 + (gy + 0.18 * S2 * 0.5) ** 2) / (2 * (0.05 * S2) ** 2)))
    c = prof + (hl * H.sstep(0.28, 0.18, rr))[..., None] * 0.55
    rgbt = np.zeros((S2, S2, 4), F32)
    rgbt[..., :3] = c * al[..., None]
    rgbt[..., 3] = al
    sizes = (150, 210, 290)
    tiles = [cv2.resize(rgbt, (s, s), interpolation=cv2.INTER_AREA) for s in sizes]
    iris = H.sstep(0.62, 0.50, rr).astype(F32)
    cells_ = r.permutation(16)[:14]
    K = 14
    ox = ((cells_ % 4) + 0.5 + r.uniform(-0.3, 0.3, K)) * n / 4.0
    oy = ((cells_ // 4) + 0.5 + r.uniform(-0.3, 0.3, K)) * n / 4.0
    ti = r.integers(0, 3, K)
    img = np.ascontiguousarray(rgb, F32).copy()
    H.splat_rgba(img, tiles, ti, ox, oy, flip=r.integers(0, 4, K))
    ex = np.zeros((n, n), F32)
    H.splat(ex, [cv2.resize(iris, (s, s), interpolation=cv2.INTER_AREA) for s in sizes], ti, ox, oy, mode="max")
    rgb = img
    Lm = H.sstep(0.04, 0.55, H.lum(rgb))
    flk = (H.flake_mask(n, 0.050, seed + 9) & (rim > 0.25))
    M = H.lerp(70.0, 160.0, Lm) + 105.0 * flk
    R = H.lerp(150.0, 46.0, Lm) - 18.0 * flk
    CC = H.lerp(80.0, 26.0, Lm)
    M = H.lerp(M, 40.0, ex)
    R = H.lerp(R, 28.0, ex)
    CC = H.lerp(CC, 16.0, ex)
    return H.finish_out(rgb, H.spec_pack(np.clip(M, 0, 255), np.clip(R, 0, 255), CC))


# -------------------------------------------------------------------------
# 3. Dragon Keel Armor - shingled scales with a raised central keel
# -------------------------------------------------------------------------
@_f("wx_dragon_armor", "Dragon Keel Armor",
    "Big shingled scales, emerald crown to bronze free edge, a raised keel on each, drifting in size, black where they overlap.")
def dragon_armor(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 3 Dragon Keel Armor (v2, coordinator review): big shingled scales (152x80 px, drifting +-30% in size, wavy rows), emerald top -> bronze free edge per scale, raised keel + shadow
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)
    S = X + 110.0 * _z(H.fbm(n, seed + 1, cells=(2, 3, 5), gain=0.7)) + 14.0 * _z(H.fbm(n, seed + 3, cells=(14, 28), gain=0.7))
    T = Y + 90.0 * _z(H.fbm(n, seed + 2, cells=(2, 3, 5), gain=0.7)) + 24.0 * _z(H.fbm(n, seed + 4, cells=(4, 8), gain=0.7))
    w, h, rho = 152.0, 80.0, 98.0
    j0 = np.floor(T / h).astype(np.int32)
    covered = np.zeros((n, n), bool)
    near = np.full((n, n), 9.0, F32)
    dxw = np.zeros((n, n), F32)
    dyw = np.zeros((n, n), F32)
    dw = np.full((n, n), 9.0, F32)
    shw = np.full((n, n), 9.0, F32)
    rowW = np.zeros((n, n), np.int32)
    colW = np.zeros((n, n), np.int32)
    for jo in (-1, 0, 1, 2):
        jc = j0 + jo
        off = (jc & 1).astype(F32) * F32(w * 0.5)
        col = np.rint((S - off) / w).astype(np.int32)
        dx = S - (col.astype(F32) * F32(w) + off)
        dy = T - jc.astype(F32) * F32(h)
        d = np.hypot(dx, dy) / F32(rho)
        win = (d < 1.0) & ~covered
        dxw = np.where(win, dx, dxw)
        dyw = np.where(win, dy, dyw)
        dw = np.where(win, d, dw)
        shw = np.where(win, near, shw)
        rowW = np.where(win, jc, rowW)
        colW = np.where(win, col, colW)
        covered |= (d < 1.0)
        near = np.minimum(near, d)
    ux = dxw / F32(rho)
    uy = dyw / F32(rho)
    cr = H.cellhash(rowW, colW, seed)
    t = H.sstep(0.0, 1.0, np.clip(0.50 * dw + 0.50 * (uy * 0.55 + 0.45), 0, 1))     # emerald crown -> bronze free edge
    keel = np.exp(-((ux + 0.03) / 0.075) ** 2) * H.sstep(-1.0, 0.0, uy) * (1.0 - H.sstep(0.78, 0.96, dw))
    keel_sh = np.exp(-((ux - 0.11) / 0.10) ** 2) * H.sstep(-0.8, 0.2, uy) * (1.0 - H.sstep(0.78, 0.96, dw))
    under = np.exp(-(np.maximum(shw - 1.0, 0.0) * rho / 16.0) ** 2) * (shw < 3.0)   # shadow cast by the scale above
    ridges = 0.5 + 0.5 * np.sin(dw * 6.2832 * 13.0 + cr * 6.0)
    stri = np.sin(ux * 55.0 + cr * 9.0) * (1.0 - t)
    micro = H.grain(n, seed + 5)
    b = 0.30 + 0.20 * (1.0 - t) + 0.12 * t + 0.42 * keel - 0.22 * keel_sh + 0.16 * ridges + 0.12 * stri + 0.16 * micro + 0.16 * (cr - 0.5)
    b = b * (1.0 - 0.82 * under) * (1.0 - 0.92 * H.sstep(0.88, 0.985, dw))
    b = np.clip(b, 0, 1)
    em = H.ramp(b, [(0.0, '#04120c'), (0.3, '#0a5236'), (0.6, '#16a06a'), (0.85, '#6be3a8'), (1.0, '#d9ffec')])
    br = H.ramp(b, [(0.0, '#150b04'), (0.3, '#5e3510'), (0.6, '#b27428'), (0.85, '#efbe68'), (1.0, '#fff2c8')])
    rgb = (em + (br - em) * t[..., None]).astype(F32)
    rgb = np.where(covered[..., None], rgb, np.array([0.02, 0.03, 0.025], F32))
    gap = np.clip(under + H.sstep(0.88, 0.985, dw), 0, 1)
    Mm = H.lerp(80.0, 175.0, b) + 90.0 * keel
    Rr = H.lerp(150.0, 62.0, b) - 55.0 * keel
    CCc = H.lerp(60.0, 28.0, b)
    Mm = H.lerp(Mm, 10.0, gap)
    Rr = H.lerp(Rr, 218.0, gap)
    CCc = H.lerp(CCc, 190.0, gap)
    return H.finish_out(rgb, H.spec_pack(np.clip(Mm, 0, 255), np.clip(Rr, 0, 255), CCc))


# -------------------------------------------------------------------------
# 4. Chupacabra Quills - needle quills bristling off furrows of grey hide
# -------------------------------------------------------------------------
@_f("wx_chupacabra_quills", "Chupacabra Quills",
    "Porcupine coat of long overlapping quills swept one way, dark at the root, pale at the tip, with chrome points.")
def chupacabra_quills(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 4 Chupacabra Quills (v2, coordinator review): porcupine coat - long lanceolate quills on a staggered lattice, all swept along a smooth flow field, painter-ordered overlap, dark base -> pale tip, tips chrome
    n = N
    m = 256
    r = H.rng(seed)
    ang_m = 0.9 + 0.42 * _z(H.fbm(m, seed + 1, cells=(2, 3, 5), gain=0.7))
    rz = H.fbm(n, seed + 2, cells=(10, 20, 40), gain=0.85)
    ridge = H.zero_set_line(rz, 5.0)
    reg = H.fbm(n, seed + 3, cells=(5, 10, 24, 60, 140), gain=0.75)
    hide = np.clip(0.22 + 0.07 * reg + 0.05 * H.grain(n, seed + 4) + 0.10 * ridge, 0, 1)
    hide_rgb = H.ramp(hide, [(0.0, '#0e0f12'), (0.25, '#1c1d21'), (0.5, '#33343a'), (0.8, '#585a60'), (1.0, '#8a8c90')])
    sp = 20.0
    g = int(n / sp) + 8
    ii, jj = np.meshgrid(np.arange(g), np.arange(g))
    bx = ((ii + 0.5 * (jj & 1) + r.uniform(-0.30, 0.30, ii.shape)) * sp - 2 * sp).ravel()
    by = ((jj + r.uniform(-0.30, 0.30, ii.shape)) * sp - 2 * sp).ravel()
    K = len(bx)
    th = H.sample(ang_m, bx / 8.0, by / 8.0) + r.normal(0, 0.09, K)
    L = r.uniform(150, 270, K)
    hw = np.clip(L * 0.022 + 1.4, 2.4, 6.0)
    mth = float(np.angle(np.exp(1j * th).mean()))
    order = np.argsort(-(bx * np.cos(mth) + by * np.sin(mth)))
    dirv = np.stack([np.cos(th), np.sin(th)], 1)
    nrm = np.stack([-dirv[:, 1], dirv[:, 0]], 1)

    def poly(a, b, off=(0.0, 0.0)):
        ts = np.linspace(a, b, 6)
        prof = np.sin(np.pi * np.clip(ts, 0, 1) ** 0.8) ** 0.9
        E = np.stack([bx, by], 1)[:, None, :] + dirv[:, None, :] * (L[:, None, None] * ts[None, :, None]) + np.array(off, np.float64)
        wd = hw[:, None] * prof[None, :]
        lf = E + nrm[:, None, :] * wd[..., None]
        rt = E - nrm[:, None, :] * wd[..., None]
        return np.round(np.concatenate([lf, rt[:, ::-1]], 1) * 8).astype(np.int32)
    P_sh = poly(0.0, 1.0, (3.0, 4.0))
    P_b = poly(0.0, 0.40)
    P_m = poly(0.36, 0.66)
    P_d = poly(0.62, 0.78)
    P_t = poly(0.74, 1.0)
    vb = r.uniform(20, 52, K).astype(int)
    vm = r.uniform(185, 232, K).astype(int)
    vd = r.uniform(12, 40, K).astype(int)
    vt = r.uniform(238, 255, K).astype(int)
    cvs = np.zeros((n, n, 3), np.uint8)
    for k in order:
        cv2.fillPoly(cvs, [P_sh[k]], (6, 255, 0), cv2.LINE_AA, 3)
        cv2.fillPoly(cvs, [P_b[k]], (int(vb[k]), 255, 0), cv2.LINE_AA, 3)
        cv2.fillPoly(cvs, [P_m[k]], (int(vm[k]), 255, 0), cv2.LINE_AA, 3)
        cv2.fillPoly(cvs, [P_d[k]], (int(vd[k]), 255, 0), cv2.LINE_AA, 3)
        cv2.fillPoly(cvs, [P_t[k]], (int(vt[k]), 255, 255), cv2.LINE_AA, 3)
    A = cvs[..., 1].astype(F32) * F32(1 / 255.0)
    den = np.maximum(cvs[..., 1].astype(F32), 1.0)
    val = np.clip(cvs[..., 0].astype(F32) / den, 0, 1)
    tipm = np.clip(cvs[..., 2].astype(F32) / den, 0, 1)
    q_rgb = H.ramp(val, [(0.0, '#0e0a08'), (0.12, '#241a14'), (0.30, '#4a3a2c'), (0.60, '#c2b08a'), (0.85, '#ece2c6'), (1.0, '#fffaf0')])
    rgb = hide_rgb * (1 - A)[..., None] + q_rgb * A[..., None]
    rgb *= (0.93 + 0.07 * H.grain(n, seed + 5))[..., None]
    rgb = np.clip(rgb, 0, 1).astype(F32)
    tmask = np.clip(tipm * A, 0, 1)
    Lq = H.sstep(0.04, 0.7, H.lum(rgb))
    M = H.lerp(8.0, 170.0, Lq) + 70.0 * tmask
    R = H.lerp(214.0, 90.0, Lq) - 60.0 * tmask
    CC = H.lerp(205.0, 60.0, Lq)
    CC = H.lerp(CC, 16.0, tmask)
    return H.finish_out(rgb, H.spec_pack(np.clip(M, 0, 255), np.clip(R, 0, 255), CC))


# -------------------------------------------------------------------------
# 5. Kraken Sucker Rows - ringed cups in curving lanes over mottled skin
# -------------------------------------------------------------------------
@_f("wx_kraken_suckers", "Kraken Sucker Rows",
    "Curving lanes of cream-ringed sucker cups over mottled plum and coral skin dotted with chromatophores.")
def kraken_suckers(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 5 Kraken Sucker Rows: staggered cup lattice on curl-warped lane coordinates, ring + teeth + cup, chromatophore dots
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)
    c, s_ = float(np.cos(0.5)), float(np.sin(0.5))
    Xr = X * c + Y * s_
    Yr = -X * s_ + Y * c
    S = Xr + 90.0 * H.fbm(n, seed + 1, cells=(2, 3), gain=0.7)
    T = Yr + 90.0 * H.fbm(n, seed + 2, cells=(2, 3), gain=0.7)
    w, h = 60.0, 52.0
    row, col, lx, ly = H.cells_rows(S, T, w, h, 0.5)
    cr = H.cellhash(row, col, seed)
    size = 1.0 + 0.30 * H.fbm(n, seed + 3, cells=(3, 6))
    rho = 0.46 * w * (0.82 + 0.18 * cr) * np.clip(size, 0.80, 1.04)
    d = np.hypot(lx, ly) / rho
    ang = np.arctan2(ly, lx)
    teeth = 0.5 + 0.5 * np.cos(ang * 24.0 + cr * 6.0)
    rim = H.sstep(0.74, 0.82, d) * (1.0 - H.sstep(0.93, 1.0, d))
    cup = 1.0 - H.sstep(0.70, 0.77, d)
    ring2 = np.exp(-((d - 0.36) / 0.07) ** 2)
    hl = np.exp(-(((lx + 0.20 * rho) ** 2 + (ly + 0.26 * rho) ** 2) / (0.06 * rho) ** 2 / 2.0)) * cup
    halo = np.exp(-(np.maximum(d - 1.0, 0.0) / 0.28) ** 2) * (d > 1.0)
    mot = H.fbm(n, seed + 4, cells=(10, 20, 44, 100), gain=0.75)
    skin = np.clip(0.42 + 0.17 * mot + 0.05 * H.grain(n, seed + 5), 0, 1) * (1.0 - 0.38 * halo)
    skin_rgb = H.ramp(skin, [(0.0, '#2a0f22'), (0.3, '#5a1e3c'), (0.55, '#92303f'), (0.8, '#d05a54'), (1.0, '#f2a08a')])
    # chromatophore dots, denser in the red patches
    dots = (H.rng(seed + 6).random((n, n), dtype=F32) < (0.008 + 0.012 * H.sstep(-0.5, 1.0, mot))).astype(F32)
    dots = np.clip(H.blur(dots, 0.9) * 3.4, 0, 1)
    dcol = H.ramp(np.clip(0.55 + 0.5 * H.fbm(n, seed + 7, cells=(7, 14)), 0, 1), [(0.0, '#f6e3c8'), (0.5, '#ee8c6e'), (1.0, '#a4204a')])
    skin_rgb = skin_rgb * (1 - 0.8 * dots[..., None]) + dcol * (0.8 * dots[..., None])
    cupb = 0.06 + 0.16 * ring2 + 0.05 * (1 - d / 0.74).clip(0, 1) + 0.9 * hl
    cup_rgb = H.ramp(np.clip(cupb, 0, 1), [(0.0, '#14040f'), (0.4, '#3a0f2a'), (0.7, '#7a2442'), (1.0, '#ffe8e0')])
    rim_b = np.clip(0.55 + 0.35 * teeth * rim + 0.15 * cr - 0.10 * (ly / rho), 0, 1)
    rim_rgb = H.ramp(rim_b, [(0.0, '#4a2f2c'), (0.5, '#b8987f'), (1.0, '#f0dcc0')])
    rgb = skin_rgb
    rgb = rgb * (1 - rim[..., None]) + rim_rgb * rim[..., None]
    rgb = rgb * (1 - cup[..., None]) + cup_rgb * cup[..., None]
    Lm = H.lum(rgb)
    Ln = np.clip(Lm * 1.7, 0, 1)
    M = H.lerp(30.0, 175.0, Ln)
    R = H.lerp(132.0, 18.0, Ln)
    CC = H.lerp(110.0, 16.0, Ln)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 6. Loch Monster Hide - pebbly tubercles under streaks of lake-water sheen
# -------------------------------------------------------------------------
@_f("wx_loch_hide", "Loch Monster Hide",
    "Wet dark-olive hide studded with fine pebbly tubercles, streaked with silver lake-water sheen.")
def loch_hide(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 6 Loch Monster Hide: Voronoi cobble tubercles (edge-distance domes) + broad wet-sheen streak bands + per-tubercle wet glints
    n = N
    r = H.rng(seed)
    pts = H.jitter_pts(n, 23.0, seed + 1, jit=0.92, margin=30)
    d, lab, sx, sy = H.voronoi(n, pts)
    e = H.edge_dist(lab)
    K = len(sx)
    ch = np.concatenate([[0.0], 0.62 + 0.38 * r.random(K)]).astype(F32)
    dome = H.sstep(0.0, 10.0, e) ** 0.7 * ch[lab]
    lump = H.fbm(n, seed + 2, cells=(20, 40, 80), gain=0.8)
    height = 6.5 * dome + 1.2 * lump + 0.35 * H.grain(n, seed + 8)
    dif, spc = H.shade(height, k=1.0, L=(-0.5, -0.7, 0.5), shin=26.0)
    sg = r.standard_normal((6, 26)).astype(F32)
    st = cv2.resize(sg, (n, n), interpolation=cv2.INTER_CUBIC)
    st = H.warp(st, 60.0 * H.fbm(n, seed + 3, cells=(3, 5)), 40.0 * H.fbm(n, seed + 9, cells=(3, 6)))
    sheen = H.sstep(0.15, 1.5, st)
    b = 0.12 + 0.42 * dif + 0.28 * dome + 0.04 * H.grain(n, seed + 4)
    b *= (0.45 + 0.55 * H.sstep(0.0, 3.5, e))
    b = np.clip(b, 0, 1)
    rgb = H.ramp(b, [(0.0, '#0a0d06'), (0.3, '#252d12'), (0.55, '#4c5a22'), (0.8, '#7f9040'), (1.0, '#c0d27c')])
    peat = H.ramp(np.clip(b * 1.1, 0, 1), [(0.0, '#120b06'), (0.5, '#35230f'), (1.0, '#6d4c26')])
    mp = H.sstep(0.35, 1.0, H.fbm(n, seed + 5, cells=(3, 6, 14)))[..., None] * 0.5
    rgb = rgb * (1 - mp) + peat * mp
    silver = np.array([0.62, 0.78, 0.86], F32)
    sh = sheen * (0.10 + 0.55 * dome * dif) + spc * (0.35 + 0.65 * sheen)
    rgb = rgb * (1 - 0.18 * sheen[..., None]) + silver * np.clip(sh, 0, 1)[..., None] * 0.85
    M = 12.0 + 130.0 * sheen * dome  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    R = H.lerp(150.0, 6.0, np.clip(dome * (0.35 + 0.65 * dif) + 0.55 * sheen * dome, 0, 1))
    CC = H.lerp(16.0, 100.0, H.sstep(3.0, 0.0, e) * 0.7)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 7. Yeti Frost Fur - long frosted strands with ice crystals
# -------------------------------------------------------------------------
@_f("wx_yeti_frost", "Yeti Frost Fur",
    "Long hanging white-blue fur strands matted with glittering ice crystals over a deep glacier-blue undercoat.")
def yeti_frost(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 7 Yeti Frost Fur: long downward-leaning strands through a gentle flow + six-armed frost stars stamped on top
    n = N
    m = 512
    r = H.rng(seed)
    ang = np.pi / 2 + 0.60 * H.fbm(m, seed + 1, cells=(3, 6, 11), gain=0.7) + 0.22 * H.fbm(m, seed + 9, cells=(26, 52))
    u, v = np.cos(ang).astype(F32), np.sin(ang).astype(F32)
    tint = H.fbm(m, seed + 2, cells=(3, 7, 14))
    cvs = None
    for K, steps, hh, vlo, vhi in ((15000, 7, 9.5, 60, 130), (30000, 8, 8.5, 100, 215), (20000, 6, 9.5, 190, 255)):
        p0 = r.random((K, 2)).astype(F32) * n
        path = _strands(u, v, p0, steps, hh)
        tt = H.sample(tint, p0[:, 0] / 4.0, p0[:, 1] / 4.0)
        tt = np.clip(0.5 + 0.40 * tt + r.normal(0, 0.12, K), 0, 1) * 255
        cvs = H.lines3(n, path, np.stack([r.uniform(vlo, vhi, K), tt, np.zeros(K)], 1), 1, canvas=cvs)
    V = H.u8f(cvs[..., 0])
    T = H.u8f(cvs[..., 1])
    gnd = 0.16 + 0.05 * H.fbm(n, seed + 3, cells=(4, 9, 20))
    V = np.maximum(V, gnd)
    ice = H.ramp(V, [(0.0, '#1d3552'), (0.35, '#3f6c9e'), (0.65, '#9cc4e6'), (0.85, '#dcedf9'), (1.0, '#ffffff')])
    cyan = H.ramp(V, [(0.0, '#14344a'), (0.35, '#2f7c9c'), (0.65, '#8fd8ee'), (0.85, '#d6f4fb'), (1.0, '#ffffff')])
    rgb = (ice + (cyan - ice) * T[..., None]).astype(F32)
    # frost stars
    S = 21
    gx, gy = H.tile_xy(S)
    star = np.zeros((S, S), F32)
    for k in range(3):
        a = k * np.pi / 3
        dd = np.abs(-gx * np.sin(a) + gy * np.cos(a))
        al = np.abs(gx * np.cos(a) + gy * np.sin(a))
        star = np.maximum(star, np.exp(-(dd / 0.75) ** 2) * (1.0 - H.sstep(S * 0.30, S * 0.5, al)))
    star = np.maximum(star, np.exp(-((gx ** 2 + gy ** 2) / 5.0)))
    tiles = []
    for sz in (11, 15, 21):
        t0 = cv2.resize(star, (sz, sz), interpolation=cv2.INTER_AREA)
        tiles.extend(H.rotset(np.ascontiguousarray(t0), 6, np.pi / 3))
    K = 9500
    fs = np.zeros((n, n), F32)
    H.splat(fs, tiles, r.integers(0, len(tiles), K), r.random(K) * n, r.random(K) * n, amp=r.uniform(0.55, 1.0, K), mode="max")
    sp = np.zeros((n, n), F32)
    H.points(sp, r.random(26000) * n, r.random(26000) * n, 1.0)
    rgb = rgb + (np.array([0.82, 0.93, 1.0], F32) * (np.clip(fs * 0.95 + sp * 0.8, 0, 1))[..., None]) * (1 - rgb * 0.35)
    flk = ((fs > 0.55) | (sp > 0.5)).astype(F32)
    M = 96.0 + 40.0 * V
    R = H.lerp(132.0, 70.0, V)
    CC = H.lerp(54.0, 34.0, V)
    M = H.lerp(M, 255.0, flk)
    R = H.lerp(R, 0.0, flk)
    CC = H.lerp(CC, 16.0, flk)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 8. Thunderbird Plumes - big overlapping feathers, chevron bars, storm sheen
# -------------------------------------------------------------------------
def _feather_master(L, W, seed):
    # [S20 v2] one thunderbird feather as a premultiplied RGBA square tile (side ~ hypot(L, W)), tip toward +x:
    # curved cream shaft, lanceolate vane outline, barbs angled off the shaft toward the tip, white chevron bars.
    SS = 2
    Lh, Wh = L * SS, W * SS
    cvs = np.zeros((Wh, Lh, 3), np.uint8)
    al = np.zeros((Wh, Lh), np.uint8)
    t = np.linspace(0.0, 1.0, 241)
    xs = 0.03 * Lh + 0.94 * Lh * t
    yc = Wh * 0.5 + 0.07 * Wh * np.sin(np.pi * t)
    hw = 0.5 * Wh * 0.94 * np.sin(np.pi * np.clip(t * 0.98 + 0.01, 0, 1) ** 0.78) ** 0.75
    top = np.stack([xs, yc - hw], 1)
    bot = np.stack([xs, yc + hw], 1)
    poly = np.round(np.concatenate([top, bot[::-1]]) * 16).astype(np.int32)
    cv2.fillPoly(al, [poly], 255, cv2.LINE_AA, 4)
    cv2.fillPoly(cvs, [poly], (30, 44, 70), cv2.LINE_AA, 4)
    bars = (0.46, 0.68)
    for i in range(2, len(t) - 2):
        ti = t[i]
        inbar = any(abs(ti - b) < 0.028 for b in bars)
        if inbar:
            col = (232, 240, 248) if (i & 1) else (186, 202, 220)
        else:
            col = (76, 108, 158) if (i & 1) else (40, 58, 94)
        p0 = (int(round(xs[i] * 16)), int(round(yc[i] * 16)))
        for side in (-1.0, 1.0):
            p1 = (int(round((xs[i] + hw[i] * 0.95) * 16)), int(round((yc[i] + side * hw[i] * 0.97) * 16)))
            cv2.line(cvs, p0, p1, col, 2, cv2.LINE_AA, 4)
    cv2.polylines(cvs, [np.round(top * 16).astype(np.int32).reshape(-1, 1, 2), np.round(bot * 16).astype(np.int32).reshape(-1, 1, 2)],
                  False, (14, 22, 38), 3, cv2.LINE_AA, 4)
    sh = np.round(np.stack([xs, yc], 1) * 16).astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(cvs, [sh], False, (226, 216, 190), 6, cv2.LINE_AA, 4)
    cv2.polylines(cvs, [sh], False, (252, 246, 226), 2, cv2.LINE_AA, 4)
    rgb_f = cvs.astype(F32) / 255.0
    a_f = al.astype(F32) / 255.0
    rgba = np.concatenate([rgb_f * a_f[..., None], a_f[..., None]], -1)
    rgba = cv2.resize(rgba, (L, W), interpolation=cv2.INTER_AREA)
    side_ = int(np.ceil(np.hypot(L, W))) | 1
    tile = np.zeros((side_, side_, 4), F32)
    y0 = (side_ - W) // 2
    x0 = (side_ - L) // 2
    tile[y0:y0 + W, x0:x0 + L] = rgba
    return tile


@_f("wx_thunderbird_plumes", "Thunderbird Plumes",
    "Giant overlapping slate feathers with a pale shaft, angled barbs and white chevron bars, swept like a wing.")
def thunderbird_plumes(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 8 Thunderbird Plumes (v2, coordinator review): ~200 big shingled feathers (520x230 px, shaft + angled barbs + white chevron bars), swept down-right, painter-ordered
    n = N
    r = H.rng(seed)
    master = _feather_master(520, 230, seed)
    phi0 = -28.0
    angs = phi0 + np.linspace(-30.0, 30.0, 7)
    tiles = []
    for sz in (0.80, 1.0, 1.25):
        t0 = cv2.resize(master, None, fx=sz, fy=sz, interpolation=cv2.INTER_AREA if sz < 1 else cv2.INTER_LINEAR)
        s2 = t0.shape[0]
        c = (s2 - 1) / 2.0
        for a in angs:
            Mx = cv2.getRotationMatrix2D((c, c), float(a), 1.0)
            tiles.append(cv2.warpAffine(t0, Mx, (s2, s2), flags=cv2.INTER_LINEAR, borderValue=0))
    d = np.array([np.cos(np.deg2rad(28.0)), np.sin(np.deg2rad(28.0))])
    pp = np.array([-d[1], d[0]])
    sa, sb = 215.0, 150.0
    I, J = np.meshgrid(np.arange(-5, 23), np.arange(-11, 12))
    I = I.ravel().astype(np.float64)
    J = J.ravel().astype(np.float64)
    I += r.uniform(-0.28, 0.28, I.shape)
    J += r.uniform(-0.28, 0.28, J.shape)
    px = n * 0.5 + I * sa * d[0] + J * sb * pp[0]
    py = n * 0.5 + I * sa * d[1] + J * sb * pp[1]
    ok = (px > -220) & (px < n + 220) & (py > -220) & (py < n + 220)
    px, py = px[ok], py[ok]
    K = len(px)
    order = np.argsort(-(px * d[0] + py * d[1]))
    px, py = px[order], py[order]
    ti = r.integers(0, 3, K) * 7 + r.integers(0, 7, K)
    tint = np.ones((K, 3), F32)
    tint[:, 0] *= r.uniform(0.86, 1.06, K).astype(F32)
    tint[:, 1] *= r.uniform(0.90, 1.08, K).astype(F32)
    tint[:, 2] *= r.uniform(0.92, 1.16, K).astype(F32)
    bgf = H.fbm(n, seed + 3, cells=(4, 8, 16))
    img = (np.zeros((n, n, 3), F32) + H.hexrgb('#0a1020') * (1.0 + 0.5 * bgf)[..., None]).astype(F32)
    H.splat_rgba(img, tiles, ti, px, py, tint=tint)
    sheen = H.fbm(n, seed + 4, cells=(6, 12, 24), gain=0.6)
    rgb = img * (0.90 + 0.22 * sheen)[..., None]
    rgb = np.clip(rgb, 0, 1).astype(F32)
    Ln = H.sstep(0.03, 0.7, H.lum(rgb))
    M = H.lerp(30.0, 205.0, Ln)
    R = H.lerp(165.0, 54.0, Ln)
    CC = H.lerp(70.0, 16.0, Ln)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 9. Gorgon Diamondback - outlined diamond blotches over a micro scale grid
# -------------------------------------------------------------------------
@_f("wx_gorgon_diamondback", "Gorgon Diamondback",
    "Dark diamond blotches with cream borders in organic chains on a tan scaled hide, small blotches in the gaps.")
def gorgon_diamondback(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 9 Gorgon Diamondback (v2, coordinator review): organically warped chain of dark diamond blotches with cream borders on tan, small dual blotches in the gaps, fine keeled scale grid over everything
    n = N
    X, Y = H.xy(n)
    wx = 28.0 * H.fbm(n, seed + 1, cells=(4, 8, 16), gain=0.7)
    wy = 28.0 * H.fbm(n, seed + 2, cells=(4, 8, 16), gain=0.7)
    Xw, Yw = X + wx, Y + wy
    p = 250.0
    U = (Xw * 0.97 + Yw * 0.24) / p
    V = (Yw * 0.97 - Xw * 0.24) / p
    cu, cvv = np.rint(U), np.rint(V)
    lu, lv = U - cu, V - cvv
    ci, cj = cu.astype(np.int64), cvv.astype(np.int64)
    ax = 0.33 + 0.06 * H.cellhash(ci, cj, seed)
    ay = 0.35 + 0.06 * H.cellhash(ci, cj, seed + 1)
    en = 0.02 * H.fbm(n, seed + 3, cells=(30, 60, 120))
    d1 = np.abs(lu) / ax + np.abs(lv) / ay + en
    fu, fv = np.floor(U), np.floor(V)
    lu2, lv2 = U - fu - 0.5, V - fv - 0.5
    h3 = H.cellhash(fu.astype(np.int64), fv.astype(np.int64), seed + 2)
    d2 = (np.abs(lu2) + np.abs(lv2)) / (0.19 + 0.06 * h3) + en
    outer1 = H.sstep(1.10, 0.98, d1)
    inner1 = H.sstep(0.84, 0.72, d1)
    outer2 = H.sstep(1.10, 0.98, d2)
    inner2 = H.sstep(0.86, 0.72, d2)
    gt = np.clip(0.5 + 0.18 * _z(H.fbm(n, seed + 4, cells=(6, 14, 40), gain=0.7)), 0, 1)
    ground = H.ramp(gt, [(0.0, '#4e3f24'), (0.5, '#6b5632'), (1.0, '#86703f')])
    dk = np.clip(0.25 + 0.55 * (1.0 - np.minimum(d1, 1.0)) + 0.10 * H.fbm(n, seed + 5, cells=(20, 50)), 0, 1)
    dark = H.ramp(dk, [(0.0, '#1a0d06'), (0.5, '#2e1a0c'), (1.0, '#4c2c15')])
    cream = H.ramp(np.clip(0.6 + 0.3 * H.fbm(n, seed + 6, cells=(30, 90)), 0, 1), [(0.0, '#e4d6a8'), (1.0, '#faf2d8')])
    rgb = ground * (1 - outer1)[..., None] + cream * outer1[..., None]
    rgb = rgb * (1 - inner1)[..., None] + dark * inner1[..., None]
    rgb = rgb * (1 - outer2)[..., None] + cream * outer2[..., None]
    rgb = rgb * (1 - inner2)[..., None] + dark * inner2[..., None]
    row, col, lx, ly = H.cells_rows(Xw * 0.6 + X * 0.4, Yw * 0.6 + Y * 0.4, 21.0, 16.0, 0.5)
    uu = lx / 10.5
    vv = (ly + 8.0) / 16.0
    edge = 0.78 - 0.26 * uu * uu
    free = H.sstep(edge + 0.08, edge - 0.04, vv)
    keel = np.exp(-(uu / 0.22) ** 2) * (1 - H.sstep(0.0, 0.7, np.abs(vv - 0.5) * 1.4))
    sshade = (0.50 + 0.50 * free * H.sstep(0.0, 0.34, vv)) * (0.9 + 0.35 * keel) + 0.12 * np.exp(-((vv - edge + 0.04) / 0.07) ** 2) * free
    rgb = np.clip(rgb * (0.55 + 0.60 * sshade)[..., None], 0, 1).astype(F32)
    Ln = H.sstep(0.03, 0.75, H.lum(rgb))
    M = H.lerp(30.0, 200.0, Ln)
    R = H.lerp(190.0, 60.0, Ln)
    CC = H.lerp(120.0, 30.0, Ln)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 10. Wendigo Bone Marrow - porous trabecular bone
# -------------------------------------------------------------------------
@_f("wx_wendigo_marrow", "Wendigo Bone Marrow",
    "Ivory bone struts forming one connected lattice, with dark marrow pores of several sizes between them and soft 3D shading.")
def wendigo_marrow(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 10 Wendigo Bone Marrow (v5, coordinator review 2): INVERTED read - continuous ivory strut network (Voronoi walls from 3 merged lattices 62/34/19 px, per-cell wall 7-15 px, rounded) dominant, dark rounded marrow pores of 3+ sizes in the gaps, tube-profile struts lit from the upper left, shallow micro-pits in the bone
    n = N
    r = H.rng(seed)
    p1 = H.jitter_pts(n, 62, seed + 1, jit=0.9, margin=20)
    p2 = H.jitter_pts(n, 34, seed + 2, jit=0.9, margin=20)
    p3 = H.jitter_pts(n, 19, seed + 3, jit=0.9, margin=20)
    p2 = p2[r.random(len(p2)) < 0.30]
    p3 = p3[r.random(len(p3)) < 0.10]
    d, lab, sx, sy = H.voronoi(n, np.concatenate([p1, p2, p3]))
    idx = (lab - 1).astype(np.int64)
    hc = H.hash01(idx, seed + 4)
    ed = H.edge_dist(lab)
    pore0 = (ed > (3.0 + 4.0 * hc)).astype(F32)
    pore = H.sstep(0.35, 0.65, H.blur(pore0, 3.0))
    wx = 1.4 * H.fbm(n, seed + 5, cells=(50, 100, 200))
    wy = 1.4 * H.fbm(n, seed + 6, cells=(50, 100, 200))
    solid = H.warp((1.0 - pore).astype(F32), wx, wy)
    pit = np.zeros((n, n), F32)
    H.points(pit, r.random(30000) * n, r.random(30000) * n, r.uniform(0.5, 1.0, 30000), mode="max")
    pit = H.blur(pit, 1.4)
    din = cv2.distanceTransform((solid > 0.5).astype(np.uint8) * 255, cv2.DIST_L2, 5)
    dout = cv2.distanceTransform((solid < 0.5).astype(np.uint8) * 255, cv2.DIST_L2, 5)
    hb = np.sin(np.clip(din / 9.0, 0, 1) * 1.5708).astype(F32)
    depth = np.clip(dout / 18.0, 0, 1).astype(F32)
    pm = (1.0 - solid)
    Hh = hb * 3.5 - depth * 2.5 * pm
    relief = H.emboss(H.blur(Hh.astype(F32), 1.2), 1.0)
    ao = H.blur(pm, 4.0)
    reg = _z(H.fbm(n, seed + 7, cells=(4, 9, 22, 60), gain=0.7))
    bone_b = np.clip(0.55 + 0.55 * relief + 0.22 * hb + 0.06 * reg - 0.20 * ao - 0.30 * np.clip(pit * 3.0, 0, 1) * solid + 0.05 * H.grain(n, seed + 8), 0, 1)
    bone = H.ramp(bone_b, [(0.0, '#5a4630'), (0.35, '#b6a47e'), (0.7, '#ece3c8'), (1.0, '#fffaee')])
    marrow_t = np.clip(0.04 + 0.16 * depth + 0.30 * np.clip(relief, 0, 1) + 0.04 * H.grain(n, seed + 9), 0, 1)
    marrow = H.ramp(marrow_t, [(0.0, '#080302'), (0.4, '#26140b'), (0.75, '#4a2a14'), (1.0, '#6a4224')])
    rgb = (bone * solid[..., None] + marrow * (1 - solid[..., None])).astype(F32)
    Ln = np.clip(H.lum(rgb) * 1.5, 0, 1)
    M = H.lerp(14.0, 150.0, Ln) + 35.0 * np.clip(relief, 0, 1) * solid
    R = H.lerp(226.0, 70.0, Ln)
    CC = H.lerp(214.0, 40.0, Ln)
    return H.finish_out(rgb, H.spec_pack(np.clip(M, 0, 255), R, CC))


# -------------------------------------------------------------------------
# 11. Jersey Devil Membrane - branching veins, translucent amber between them
# -------------------------------------------------------------------------
def _walk(p0, th0, steps, h, jit, r):
    K = len(p0)
    P = np.empty((K, steps + 1, 2), F32)
    P[:, 0] = p0
    th = np.asarray(th0, F32).copy()
    p = np.asarray(p0, F32).copy()
    for i in range(steps):
        th += r.normal(0, jit, K).astype(F32)
        p[:, 0] += F32(h) * np.cos(th)
        p[:, 1] += F32(h) * np.sin(th)
        P[:, i + 1] = p
    return P


def _tang(P):
    t = np.gradient(P, axis=1)
    return np.arctan2(t[..., 1], t[..., 0])


@_f("wx_devil_membrane", "Jersey Devil Membrane",
    "Thin stretched wing membrane glowing amber between a branching net of dark leathery veins.")
def devil_membrane(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 11 Jersey Devil Membrane: sparse thick spars + dense thin flow-line veins + tiny perpendicular cross-links; membrane thickness = distance to veins
    n = N
    m = 512
    r = H.rng(seed)
    ang = 0.70 + 0.9 * H.fbm(m, seed + 1, cells=(2, 3, 5), gain=0.7)
    u, v = np.cos(ang).astype(F32), np.sin(ang).astype(F32)
    cvs = None
    sp0 = r.random((16, 2)).astype(F32) * n
    sp = _strands(u, v, sp0, 50, 9.0)
    cvs = H.lines3(n, sp, np.full(16, 255.0), 3, canvas=cvs)
    vp0 = r.random((190, 2)).astype(F32) * n
    vp = _strands(u, v, vp0, 36, 9.0)
    cvs = H.lines3(n, vp, r.uniform(150, 210, 190), 1, canvas=cvs)
    # cross veins: short segments leaving the veins at near-right angles
    T = _tang(vp)
    ii = r.integers(0, len(vp), 11000)
    jj = r.integers(2, vp.shape[1] - 2, 11000)
    base = vp[ii, jj]
    tha = T[ii, jj] + np.pi / 2 * np.where(r.random(11000) < 0.5, 1.0, -1.0) + r.normal(0, 0.30, 11000)
    L = r.uniform(10, 34, 11000)
    pa = np.stack([base, base + np.stack([np.cos(tha) * L * 0.5, np.sin(tha) * L * 0.5], 1) + r.normal(0, 1.2, (11000, 2)),
                   base + np.stack([np.cos(tha) * L, np.sin(tha) * L], 1)], 1).astype(F32)
    cvs = H.lines3(n, pa, r.uniform(70, 125, 11000), 1, canvas=cvs)
    V = H.u8f(cvs[..., 0])
    vein = np.clip(V * 1.6, 0, 1)
    dist = cv2.distanceTransform(((V < 0.10) * 255).astype(np.uint8), cv2.DIST_L2, 5).astype(F32)
    thick = np.exp(-dist / 9.0)
    reg = H.fbm(n, seed + 2, cells=(6, 14, 34, 90, 220), gain=0.8)
    glow = np.clip(0.82 - 0.42 * thick + 0.12 * reg, 0, 1)
    mem = H.ramp(glow, [(0.0, '#3a1608'), (0.3, '#8a3c10'), (0.55, '#d27a1c'), (0.8, '#f4b640'), (1.0, '#ffe39a')])
    vcol = H.ramp(np.clip(0.16 + 0.28 * V + 0.10 * H.grain(n, seed + 3), 0, 1), [(0.0, '#160805'), (0.5, '#3a1d0e'), (1.0, '#6e4224')])
    rgb = mem * (1 - vein[..., None]) + vcol * vein[..., None]
    Ln = np.clip(H.lum(rgb) * 1.5, 0, 1)
    M = H.lerp(214.0, 128.0, Ln)
    R = H.lerp(60.0, 140.0, 1.0 - Ln) * 0 + H.lerp(142.0, 58.0, Ln)
    CC = H.lerp(30.0, 62.0, 1.0 - Ln)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 12. Swamp Osteoderms - rows of pitted rectangular bony plates
# -------------------------------------------------------------------------
@_f("wx_swamp_osteoderms", "Swamp Osteoderms",
    "Rows of irregular rectangular gator plates in swamp green and khaki, each keeled and pitted, mud in the seams.")
def swamp_osteoderms(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 12 Swamp Osteoderms: slab/plate partition, domed plates with strong keel ridge, vertical micro-ridges, regional olive drift (not per-plate pixels), pits
    n = N
    r = H.rng(seed)
    hs = r.uniform(84, 124, 60)
    ye = np.cumsum(hs)
    ye = ye[ye < n + 60]
    ye = np.concatenate([[0.0], ye])
    xs1 = np.arange(n, dtype=F32)
    ys1 = np.arange(n, dtype=F32)
    reg = np.clip(0.5 + 0.55 * H.fbm(n, seed + 1, cells=(3, 6, 12)), 0, 1)     # smooth olive drift across the car
    val = np.zeros((n, n), F32)
    shade = np.zeros((n, n), F32)
    keelm = np.zeros((n, n), F32)
    litm = np.zeros((n, n), F32)
    seam = np.zeros((n, n), F32)
    pit_ok = np.zeros((n, n), F32)
    for k in range(len(ye) - 1):
        y0, y1 = int(ye[k]), min(int(ye[k + 1]), n)
        if y1 <= y0:
            continue
        wts = r.uniform(78, 128, 60)
        xe = np.cumsum(wts) - r.uniform(0, 60)
        xe = np.concatenate([[-60.0], xe[xe < n + 60]])
        j = np.searchsorted(xe, xs1, side="right") - 1
        j = np.clip(j, 0, len(xe) - 2)
        xl, xr_ = xe[j], xe[j + 1]
        dl = xs1 - xl
        dr = xr_ - xs1
        wpl = xr_ - xl
        yy = ys1[y0:y1]
        dt = yy - y0
        db = (y1 - 1) - yy
        e = np.minimum(np.minimum(dl[None, :], dr[None, :]), np.minimum(dt[:, None], db[:, None]))
        hid = r.random(len(xe))[j]
        cx = (xl + xr_) * 0.5
        kd = (xs1 - cx) / (0.13 * wpl)
        kx = np.exp(-kd ** 2)                                  # keel ridge, vertical, centred on the plate
        kside = np.clip(kd, -2, 2) * np.exp(-0.5 * kd ** 2)    # +ve on the right flank, -ve on the left (shaded sides)
        ky = np.sin(np.pi * np.clip((yy - y0) / (y1 - y0), 0, 1)) ** 0.5
        keel = kx[None, :] * ky[:, None]
        flank = kside[None, :] * ky[:, None]
        lit = np.exp(-dl[None, :] / 4.0) + np.exp(-dt[:, None] / 4.0) - np.exp(-dr[None, :] / 4.0) - np.exp(-db[:, None] / 4.0)
        sm = 1.0 - H.sstep(1.2, 3.0, e)
        dome = H.sstep(0.0, 16.0, e)
        val[y0:y1] = reg[y0:y1] + 0.30 * (hid[None, :] - 0.5)
        shade[y0:y1] = 0.44 + 0.34 * dome + 0.42 * lit + 0.85 * keel - 0.38 * flank
        keelm[y0:y1] = keel * (1 - sm)
        litm[y0:y1] = np.clip(lit, 0, 1) * (1 - sm)
        seam[y0:y1] = sm
        pit_ok[y0:y1] = H.sstep(4.0, 7.0, e)
    wx = 3.0 * H.fbm(n, seed + 2, cells=(14, 28, 56))
    wy = 3.0 * H.fbm(n, seed + 3, cells=(14, 28, 56))
    pk = np.stack([keelm, litm, seam, pit_ok], -1)
    pk = H.warp(np.ascontiguousarray(pk), wx, wy)
    val = H.warp(val, wx, wy)
    shade = H.warp(shade, wx, wy)
    keelm, litm, seam, pit_ok = pk[..., 0], pk[..., 1], pk[..., 2], pk[..., 3]
    # vertical micro-ridges (hide striations), 3-6 px wide, run along the plate
    rr = H.rng(seed + 4).standard_normal((n, n)).astype(F32)
    stri = cv2.GaussianBlur(rr, (0, 0), sigmaX=0.9, sigmaY=7.0)
    stri /= float(stri.std()) + 1e-6
    shade = shade * (1.0 + 0.26 * stri)
    pits = (H.rng(seed + 5).random((n, n), dtype=F32) < 0.036).astype(F32)
    pits = np.clip(H.blur(pits, 1.1) * 5.0, 0, 1) * pit_ok
    shade = shade * (1 - 0.62 * pits)
    base = H.ramp(np.clip(val, 0, 1), [(0.0, '#1e3220'), (0.3, '#2f4a28'), (0.6, '#4f5f2e'), (0.85, '#6c6c3c'), (1.0, '#85804c')])
    rgb = base * np.clip(shade, 0, 1.6)[..., None]
    mud = H.ramp(np.clip(0.2 + 0.2 * H.fbm(n, seed + 6, cells=(40, 100)), 0, 1), [(0.0, '#0a0e07'), (0.5, '#1c2210'), (1.0, '#37381c')])
    rgb = rgb * (1 - seam[..., None]) + mud * seam[..., None]
    rgb *= (0.92 + 0.08 * H.grain(n, seed + 7))[..., None]
    rgb = np.clip(rgb, 0, 1).astype(F32)
    metal = np.clip(keelm * 0.9 + litm * 0.5, 0, 1)
    M = H.lerp(10.0, 232.0, metal)
    Ln = np.clip(H.lum(rgb) * 2.6, 0, 1)
    R = H.lerp(214.0 - 80.0 * Ln, 46.0, metal) + 20.0 * seam + 25.0 * pits
    CC = H.lerp(200.0, 16.0, metal)
    return H.finish_out(rgb, H.spec_pack(M, np.clip(R, 0, 255), CC))


# -------------------------------------------------------------------------
# 13. Werewolf Grizzle - salt-and-pepper banded agouti hairs
# -------------------------------------------------------------------------
@_f("wx_werewolf_grizzle", "Werewolf Grizzle",
    "Pelt of long banded hairs flowing in tracts and whorls, dark saddle and silver flanks, white-frosted tips.")
def werewolf_grizzle(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 13 Werewolf Grizzle (v2, coordinator review): pelt - flow field with 7 whorls + tracts, 13-point banded hairs (base/band/tip), regional dark saddle vs silver flanks, parting seams
    n = N
    m = 512
    r = H.rng(seed)
    Xm, Ym = H.xy(m)
    ang = 1.30 + 0.55 * _z(H.fbm(m, seed + 1, cells=(2, 3, 5), gain=0.7))
    u = np.cos(ang).astype(F32)
    v = np.sin(ang).astype(F32)
    for k in range(7):
        cx, cy = r.uniform(0.08, 0.92) * m, r.uniform(0.08, 0.92) * m
        R = r.uniform(34.0, 80.0)
        sg = 1.0 if r.random() < 0.5 else -1.0
        dx, dy = Xm - cx, Ym - cy
        d2 = dx * dx + dy * dy
        wgt = np.exp(-d2 / (2 * R * R)).astype(F32)
        rr = np.sqrt(d2) + 1e-3
        u = u * (1 - wgt) + (-dy / rr * sg) * wgt
        v = v * (1 - wgt) + (dx / rr * sg) * wgt
    nm = np.sqrt(u * u + v * v) + 1e-6
    a2 = np.arctan2(v / nm, u / nm) + 0.22 * _z(H.fbm(m, seed + 2, cells=(24, 48), gain=0.7))
    u = np.cos(a2).astype(F32)
    v = np.sin(a2).astype(F32)
    reg = _z(H.fbm(m, seed + 3, cells=(3, 5, 9), gain=0.7))
    lock = _z(H.fbm(m, seed + 4, cells=(36, 72), gain=0.7))
    warm = _z(H.fbm(m, seed + 5, cells=(3, 6, 12), gain=0.7))
    cvs = None
    for K in (36000, 36000, 20000):
        p0 = r.random((K, 2)).astype(F32) * n
        path = _strands(u, v, p0, 6, 4.5)                # 13 points, ~54 px
        rs = H.sample(reg, p0[:, 0] / 4.0, p0[:, 1] / 4.0)
        ls = H.sample(lock, p0[:, 0] / 4.0, p0[:, 1] / 4.0)
        ws = H.sample(warm, p0[:, 0] / 4.0, p0[:, 1] / 4.0)
        pl = np.clip(0.5 + 0.30 * rs + 0.20 * ls, 0.03, 0.97)
        light = r.random(K) < pl
        j = r.uniform(0.0, 1.0, K)
        base_v = np.where(light, 110 + 50 * j, 16 + 36 * j)
        band_v = np.where(light, 205 + 50 * j, 130 + 70 * j)
        tip_v = np.where(light, 240, 10 + 22 * j)
        wc = np.clip(0.5 + 0.30 * ws, 0, 1) * 255
        for seg, vv_ in ((slice(0, 5), base_v), (slice(4, 9), band_v), (slice(8, 13), tip_v)):
            cvs = H.lines3(n, path[:, seg], np.stack([vv_, wc, np.zeros(K)], 1), 1, canvas=cvs)
    V = H.u8f(cvs[..., 0])
    W = H.u8f(cvs[..., 1])
    seam = H.ups(np.ascontiguousarray(H.zero_set_line(H.fbm(m, seed + 6, cells=(4, 8), gain=0.6), 7.0), F32), n)
    V = np.maximum(V, 0.11) * (1.0 - 0.38 * seam)
    cool = H.ramp(V, [(0.0, '#0b0c0e'), (0.3, '#2c2f34'), (0.6, '#7d838a'), (0.85, '#cfd4d8'), (1.0, '#f6f8f8')])
    warmc = H.ramp(V, [(0.0, '#100c09'), (0.3, '#352c24'), (0.6, '#8a7a6a'), (0.85, '#d6cdbf'), (1.0, '#faf6ee')])
    wcw = np.clip(W * 1.6 - 0.75, 0, 1)[..., None]
    rgb = (cool + (warmc - cool) * wcw).astype(F32)
    M = H.lerp(120.0, 255.0, V)  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    R = H.lerp(170.0, 50.0, V)
    CC = H.lerp(90.0, 16.0, V)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 14. Cane Toad Glands - swollen warts and glands with wet highlights
# -------------------------------------------------------------------------
@_f("wx_toad_glands", "Cane Toad Glands",
    "Swollen olive-yellow warts and big oval glands, merging bumps with wet mustard highlights and brown valleys.")
def toad_glands(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 14 Cane Toad Glands: additive gaussian metaballs at three sizes + anisotropic parotoid glands, soft-saturated into a lit heightfield
    n = N
    r = H.rng(seed)
    hgt = np.zeros((n, n), F32)
    for sig, K, S, amp0 in ((6.2, 5200, 41, 1.0), (2.6, 24000, 17, 0.55)):
        gx, gy = H.tile_xy(S)
        tl = np.exp(-(gx * gx + gy * gy) / (2.0 * sig * sig)).astype(F32)
        tl = [tl * F32(a) for a in (0.7, 0.85, 1.0, 1.2)]
        H.splat(hgt, tl, r.integers(0, 4, K), r.random(K) * n, r.random(K) * n, amp=r.uniform(0.6, 1.1, K) * amp0)
    # big glands
    gl = np.zeros((n, n), F32)
    X, Y = H.xy(n)
    pts = H.jitter_pts(n, 330.0, seed + 5, jit=0.8, margin=60)
    for (cx, cy) in pts:
        a = r.uniform(0, np.pi)
        ca, sa = np.cos(a), np.sin(a)
        L, W = r.uniform(58, 96), r.uniform(30, 52)
        x0, y0 = int(cx) - 110, int(cy) - 110
        xa, ya = max(x0, 0), max(y0, 0)
        xb, yb = min(x0 + 220, n), min(y0 + 220, n)
        if xb <= xa or yb <= ya:
            continue
        dx = X[ya:yb, xa:xb] - cx
        dy = Y[ya:yb, xa:xb] - cy
        q = ((dx * ca + dy * sa) / L) ** 2 + ((-dx * sa + dy * ca) / W) ** 2
        gl[ya:yb, xa:xb] = np.maximum(gl[ya:yb, xa:xb], np.exp(-q * 1.7).astype(F32))
    hgt = hgt + 1.6 * gl * (0.85 + 0.15 * H.grain(n, seed + 6))
    hh = 1.0 - np.exp(-1.35 * hgt)
    dif, spc = H.shade(hh * 5.5, k=0.8, L=(-0.5, -0.65, 0.55), shin=26.0)
    reg = H.fbm(n, seed + 3, cells=(4, 9, 20), gain=0.7)
    b = np.clip(0.18 + 0.38 * dif + 0.30 * hh + 0.06 * reg, 0, 1)
    ol = H.ramp(b, [(0.0, '#14140a'), (0.3, '#3a3a16'), (0.55, '#6c6a22'), (0.8, '#a2a032'), (1.0, '#d2cf64')])
    must = H.ramp(np.clip(b * 1.15, 0, 1), [(0.0, '#2a1c08'), (0.4, '#6e4a12'), (0.7, '#c88e20'), (1.0, '#fcd860')])
    wm = H.sstep(0.45, 0.95, hh) * H.sstep(-0.4, 0.8, reg + 0.4 * gl)
    rgb = ol * (1 - wm[..., None] * 0.7) + must * (wm[..., None] * 0.7)
    mud = H.ramp(np.clip(0.2 + 0.4 * hh, 0, 1), [(0.0, '#150d06'), (1.0, '#4a3a1c')])
    vall = (1.0 - H.sstep(0.0, 0.4, hh))[..., None] * 0.7
    rgb = rgb * (1 - vall) + mud * vall
    rgb = rgb + np.array([1.0, 0.95, 0.7], F32) * (spc * 0.85)[..., None]
    _q = np.clip(hh * (0.45 + 0.55 * dif), 0, 1)  # [S20 spec-widen 2026-10-12] channel std >= 20 bar
    M = 10.0 + 120.0 * spc
    R = H.lerp(150.0, 6.0, _q)
    CC = H.lerp(90.0, 16.0, _q)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


def _aniso(n, cx, cy, seed):
    """Anisotropic smooth noise: cx cells across, cy cells down (so features are n/cx wide, n/cy tall)."""
    g = H.rng(seed).standard_normal((int(cy), int(cx))).astype(F32)
    return cv2.resize(g, (n, n), interpolation=cv2.INTER_CUBIC)


# -------------------------------------------------------------------------
# 15. Marsh Ghost Lights - reeds, streaming mist, will-o-wisp orbs
# -------------------------------------------------------------------------
@_f("wx_marsh_lights", "Marsh Ghost Lights",
    "Dark reed marsh in three depth layers, horizontal mist bands, a few large cyan and gold ghost lights with ripples below.")
def marsh_lights(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 15 Marsh Ghost Lights (v2, coordinator review): 3 depth layers of tapered reed silhouettes, horizontal mist bands, ~20 large soft will-o-wisp orbs with rippled reflections below
    n = N
    r = H.rng(seed)
    yv, _ = H.vgrad(n)
    reg = _z(H.fbm(n, seed + 1, cells=(3, 6, 12), gain=0.7))
    rgb = H.ramp(np.clip(0.30 + 0.20 * (1.0 - yv) + 0.05 * reg, 0, 1),
                 [(0.0, '#050d0b'), (0.35, '#0d1f1a'), (0.7, '#1c3b33'), (1.0, '#355a50')]).astype(F32)

    def blades(K, ylo, yhi, Lr, wr, lean, stops, rib):
        bx = r.random(K) * n
        by = r.uniform(ylo, yhi, K)
        L = r.uniform(Lr[0], Lr[1], K)
        w0 = r.uniform(wr[0], wr[1], K)
        a0 = r.normal(0, lean, K)
        bend = r.normal(0, 0.22, K)
        t = np.linspace(0, 1, 7)
        th = -np.pi / 2 + a0[:, None] + bend[:, None] * t[None, :]
        seg = L[:, None] / 6.0
        cxp = bx[:, None] + np.concatenate([np.zeros((K, 1)), np.cumsum(np.cos(th[:, :-1]) * seg, 1)], 1)
        cyp = by[:, None] + np.concatenate([np.zeros((K, 1)), np.cumsum(np.sin(th[:, :-1]) * seg, 1)], 1)
        hw = 0.5 * w0[:, None] * (1.0 - t[None, :] ** 1.5) ** 0.9
        nx, ny = -np.sin(th), np.cos(th)
        lf = np.stack([cxp + nx * hw, cyp + ny * hw], -1)
        rt = np.stack([cxp - nx * hw, cyp - ny * hw], -1)
        poly = np.concatenate([lf, rt[:, ::-1]], 1).astype(F32)
        val = r.uniform(30, 200, K)
        cvs = H.fills3(n, poly, np.stack([val, np.full(K, 255.0), np.zeros(K)], 1))
        if rib:
            cvs = H.lines3(n, np.stack([cxp, cyp], -1).astype(F32),
                           np.stack([np.minimum(val + 60, 255.0), np.full(K, 255.0), np.zeros(K)], 1), 1, canvas=cvs)
        A = cvs[..., 1].astype(F32) * F32(1 / 255.0)
        V = np.clip(cvs[..., 0].astype(F32) / np.maximum(cvs[..., 1].astype(F32), 1.0), 0, 1)
        return A, H.ramp(V, stops)

    def mist(bands, amp, seed_):
        prof = np.zeros(n, F32)
        ys_ = np.arange(n, dtype=F32)
        for cy_, th_, am_ in bands:
            prof += F32(am_) * np.exp(-((ys_ - cy_) / th_) ** 2).astype(F32)
        noise = np.clip(0.55 + 0.30 * _z(_aniso(n, 7, 70, seed_)) + 0.18 * _z(_aniso(n, 40, 240, seed_ + 1)), 0, 1)
        return np.clip(prof[:, None] * noise * amp, 0, 0.8).astype(F32)

    Ab, cb = blades(3400, 80, n + 260, (110, 300), (3.0, 6.5), 0.10, [(0.0, '#15302a'), (0.5, '#25493f'), (1.0, '#3b6a5b')], False)
    rgb = rgb * (1 - 0.88 * Ab)[..., None] + cb * (0.88 * Ab)[..., None]
    b1 = [(r.uniform(100, 1950), r.uniform(45, 100), r.uniform(0.6, 1.0)) for _ in range(5)]
    ma = mist(b1, 0.75, seed + 20)
    mcol = H.ramp(np.clip(0.55 + 0.25 * _z(H.fbm(n, seed + 22, cells=(3, 6), gain=0.7)), 0, 1), [(0.0, '#6fa89c'), (1.0, '#b4e6d8')])
    rgb = rgb * (1 - ma)[..., None] + mcol * ma[..., None]
    Am, cm = blades(1700, 160, n + 340, (180, 420), (6.0, 11.0), 0.10, [(0.0, '#0b2018'), (0.5, '#173b2a'), (1.0, '#2a5c40')], False)
    rgb = rgb * (1 - 0.94 * Am)[..., None] + cm * (0.94 * Am)[..., None]
    # orbs on a jittered 5x5 grid (21 of 25): big soft cores, halos, and rippled reflections beneath
    Ic = np.zeros((n, n), F32)
    Ig = np.zeros((n, n), F32)
    cells_ = r.permutation(25)[:21]
    sig = np.where(np.arange(21) < 8, r.uniform(38, 56, 21), np.where(np.arange(21) < 15, r.uniform(24, 36, 21), r.uniform(10, 15, 21)))
    gold = r.random(21) < 0.30
    for q in range(21):
        c = cells_[q]
        ox = ((c % 5) + 0.5 + r.uniform(-0.28, 0.28)) * n / 5.0
        oy = ((c // 5) + 0.5 + r.uniform(-0.28, 0.28)) * n / 5.0 - 80.0
        s = float(sig[q])
        S = int(7 * s) | 1
        gx, gy = H.tile_xy(S)
        rr2 = gx * gx + gy * gy
        g = (np.exp(-rr2 / F32(2 * (0.33 * s) ** 2)) + 0.50 * np.exp(-rr2 / F32(2 * s * s)) + 0.10 * np.exp(-rr2 / F32(2 * (2.0 * s) ** 2))).astype(F32)
        tgt = Ig if gold[q] else Ic
        H.splat(tgt, [g], [0], [ox], [oy], amp=[r.uniform(1.0, 1.3)])
        # reflection: vertical smear with horizontal ripple bands
        sx_, sy_ = 0.5 * s, 2.6 * s
        Sx, Sy = int(7 * sx_) | 1, int(7 * sy_) | 1
        ax = (np.arange(Sx, dtype=F32) - (Sx - 1) / 2.0)
        ay = (np.arange(Sy, dtype=F32) - (Sy - 1) / 2.0)
        refl = np.exp(-(ax[None, :] ** 2) / F32(2 * sx_ * sx_)) * np.exp(-(ay[:, None] ** 2) / F32(2 * sy_ * sy_))
        refl = (refl * (0.55 + 0.45 * np.cos(ay[:, None] * (2 * np.pi / (0.42 * s + 6.0)) + 1.3 * np.sin(ax[None, :] / (0.4 * s))))).astype(F32)
        H.splat(tgt, [refl], [0], [ox + r.uniform(-6, 6)], [oy + 0.9 * sy_ + 0.7 * s], amp=[0.18])
    Gc, Gg = np.clip(Ic, 0, 1.3), np.clip(Ig, 0, 1.3)
    C = H.ramp(np.clip(Gc, 0, 1), [(0.0, '#000000'), (0.15, '#0b4a48'), (0.4, '#2a9c94'), (0.75, '#8ef0e0'), (1.0, '#f2fffb')])
    G = H.ramp(np.clip(Gg, 0, 1), [(0.0, '#000000'), (0.15, '#4a3a0c'), (0.4, '#b08a22'), (0.75, '#ffd56a'), (1.0, '#fffbe6')])
    rgb = 1.0 - (1.0 - rgb) * (1.0 - C) * (1.0 - G)
    b2 = [(r.uniform(300, 1900), r.uniform(35, 70), r.uniform(0.5, 0.9)) for _ in range(3)]
    ma2 = mist(b2, 0.55, seed + 30)
    rgb = rgb * (1 - ma2)[..., None] + mcol * ma2[..., None]
    Af, cf = blades(400, 280, n + 420, (320, 700), (11.0, 22.0), 0.07, [(0.0, '#040a06'), (0.5, '#0a170f'), (1.0, '#17301f')], True)
    spill = np.clip(0.28 * (Gc + Gg), 0, 0.45)[..., None] * H.hexrgb('#5fb8a8')
    cf = cf + spill
    rgb = rgb * (1 - 0.97 * Af)[..., None] + cf * (0.97 * Af)[..., None]
    rgb = np.clip(rgb, 0, 1).astype(F32)
    Ln = H.sstep(0.05, 0.55, H.lum(rgb))
    M = H.lerp(8.0, 245.0, Ln)
    R = H.lerp(205.0, 10.0, Ln)
    CC = H.lerp(200.0, 16.0, Ln)
    return H.finish_out(rgb, H.spec_pack(np.clip(M, 0, 255), np.clip(R, 0, 255), CC))


# -------------------------------------------------------------------------
# 16. Eyes in the Dark - paired tapetum glints between layered leaf silhouettes
# -------------------------------------------------------------------------
@_f("wx_eyes_in_dark", "Eyes in the Dark",
    "Pairs of glowing almond eyes with slit pupils, equal size and spacing, peering from black layered leaf silhouettes.")
def eyes_in_dark(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 16 Eyes in the Dark (v2, coordinator review): 128 clear PAIRS (equal almond eyes, slit pupils, spacing 3.0 x eye length, slight tilt, catch-lights) in dark holes among veined leaf silhouettes
    n = N
    r = H.rng(seed)
    reg = _z(H.fbm(n, seed + 1, cells=(3, 6, 12), gain=0.7))
    rgb = H.ramp(np.clip(0.36 + 0.10 * reg + 0.02 * H.grain(n, seed + 2), 0, 1),
                 [(0.0, '#050a07'), (0.5, '#0b160e'), (1.0, '#142a18')]).astype(F32)

    def leaves(K, Lr, wr, stops, veins, keep=None):
        L = r.uniform(Lr[0], Lr[1], K)
        W = L * r.uniform(wr[0], wr[1], K)
        th = r.uniform(0, 2 * np.pi, K)
        cx = r.random(K) * n
        cy = r.random(K) * n
        if keep is not None:
            ok = keep(cx, cy, L)
            L, W, th, cx, cy = L[ok], W[ok], th[ok], cx[ok], cy[ok]
            K = len(L)
        t = np.linspace(0, 1, 9)
        prof = np.sin(np.pi * t) ** 0.85
        xs = L[:, None] * t[None, :]
        ys = 0.5 * W[:, None] * prof[None, :]
        ex = np.concatenate([xs, xs[:, ::-1]], 1) - (L / 2)[:, None]
        ey = np.concatenate([ys, -ys[:, ::-1]], 1)
        c, s = np.cos(th)[:, None], np.sin(th)[:, None]
        poly = np.stack([cx[:, None] + ex * c - ey * s, cy[:, None] + ex * s + ey * c], -1).astype(F32)
        val = r.uniform(30, 190, K)
        cvs = H.fills3(n, poly, np.stack([val, np.full(K, 255.0), np.zeros(K)], 1))
        if veins:
            mx = cx[:, None] + (xs - (L / 2)[:, None]) * c
            my = cy[:, None] + (xs - (L / 2)[:, None]) * s
            vcol = np.stack([np.minimum(val + 80, 255.0), np.full(K, 255.0), np.zeros(K)], 1)
            cvs = H.lines3(n, np.stack([mx, my], -1).astype(F32), vcol, 1, canvas=cvs)
            sd = []
            for j in (2, 4, 6):
                for sgn in (1.0, -1.0):
                    p0 = np.stack([cx + (xs[:, j] - L / 2) * c[:, 0], cy + (xs[:, j] - L / 2) * s[:, 0]], -1)
                    px_ = xs[:, j + 1] - L / 2
                    py_ = sgn * ys[:, j + 1] * 0.92
                    p1 = np.stack([cx + px_ * c[:, 0] - py_ * s[:, 0], cy + px_ * s[:, 0] + py_ * c[:, 0]], -1)
                    sd.append(np.stack([p0, p1], 1))
            sd = np.concatenate(sd).astype(F32)
            cvs = H.lines3(n, sd, np.tile(vcol * np.array([0.8, 1.0, 1.0]), (6, 1)), 1, canvas=cvs)
        A = cvs[..., 1].astype(F32) * F32(1 / 255.0)
        V = np.clip(cvs[..., 0].astype(F32) / np.maximum(cvs[..., 1].astype(F32), 1.0), 0, 1)
        return A, H.ramp(V, stops)

    A1, c1 = leaves(1100, (70, 170), (0.28, 0.40), [(0.0, '#0a160e'), (1.0, '#14301b')], True)
    rgb = rgb * (1 - A1)[..., None] + c1 * A1[..., None]
    A2, c2 = leaves(480, (90, 200), (0.26, 0.38), [(0.0, '#0c1c12'), (0.6, '#163a1c'), (1.0, '#2c6a30')], True)
    rgb = rgb * (1 - A2)[..., None] + c2 * A2[..., None]
    # pairs: big / medium / small
    pcx, pcy, pd, pth, phue = [], [], [], [], []
    for cnt, dr in ((12, (170.0, 235.0)), (36, (96.0, 140.0)), (80, (52.0, 76.0))):
        pcx.append(r.random(cnt) * (n - 160) + 80)
        pcy.append(r.random(cnt) * (n - 160) + 80)
        pd.append(r.uniform(dr[0], dr[1], cnt))
        pth.append(r.normal(0, 0.17, cnt))
        phue.append(r.choice([0.10, 0.35, 0.60, 0.85], cnt, p=[0.45, 0.30, 0.15, 0.10]))
    pcx, pcy, pd, pth, phue = (np.concatenate(a) for a in (pcx, pcy, pd, pth, phue))
    a = 0.17 * pd                  # eye half-length
    b = 0.085 * pd                 # eye half-height
    ip, pp, cl, hole = [], [], [], []
    tt = np.linspace(-1.0, 1.0, 13)
    shape = (1.0 - tt * tt) ** 0.85
    for side in (-1.0, 1.0):
        ex = pcx + side * 0.5 * pd * np.cos(pth)
        ey = pcy + side * 0.5 * pd * np.sin(pth)
        tilt = pth - side * 0.30
        lx = np.concatenate([a[:, None] * tt[None, :], a[:, None] * tt[::-1][None, :]], 1)
        ly = np.concatenate([-b[:, None] * shape[None, :], 0.62 * b[:, None] * shape[::-1][None, :]], 1)
        ct, st = np.cos(tilt)[:, None], np.sin(tilt)[:, None]
        ip.append(np.stack([ex[:, None] + lx * ct - ly * st, ey[:, None] + lx * st + ly * ct], -1))
        u2 = np.linspace(0, 2 * np.pi, 10, endpoint=False)
        lx2 = (0.12 * a)[:, None] * np.cos(u2)[None, :]
        ly2 = (0.95 * b)[:, None] * np.sin(u2)[None, :]
        c2_, s2_ = np.cos(pth)[:, None], np.sin(pth)[:, None]
        pp.append(np.stack([ex[:, None] + lx2 * c2_ - ly2 * s2_, ey[:, None] + lx2 * s2_ + ly2 * c2_], -1))
        u3 = np.linspace(0, 2 * np.pi, 6, endpoint=False)
        rc = np.maximum(1.3, 0.09 * a)[:, None]
        hx, hy = ex - 0.38 * a * ct[:, 0] + 0.30 * b * st[:, 0], ey - 0.38 * a * st[:, 0] - 0.30 * b * ct[:, 0]
        cl.append(np.stack([hx[:, None] + rc * np.cos(u3)[None, :], hy[:, None] + rc * np.sin(u3)[None, :]], -1))
    ip = np.concatenate(ip).astype(F32)
    pp = np.concatenate(pp).astype(F32)
    cl = np.concatenate(cl).astype(F32)
    hv = np.concatenate([phue, phue])
    Np2 = len(hv)
    # dark holes behind each pair (soft)
    u4 = np.linspace(0, 2 * np.pi, 16, endpoint=False)
    hxp = pcx[:, None] + (0.78 * pd)[:, None] * np.cos(u4)[None, :] * np.cos(pth)[:, None] - (0.40 * pd)[:, None] * np.sin(u4)[None, :] * np.sin(pth)[:, None]
    hyp = pcy[:, None] + (0.78 * pd)[:, None] * np.cos(u4)[None, :] * np.sin(pth)[:, None] + (0.40 * pd)[:, None] * np.sin(u4)[None, :] * np.cos(pth)[:, None]
    HM = H.fills3(n, np.stack([hxp, hyp], -1).astype(F32), np.tile(np.array([[255.0, 0.0, 0.0]]), (len(pcx), 1)))
    hole = cv2.GaussianBlur(HM[..., 0].astype(F32) * F32(1 / 255.0), (0, 0), 9.0)
    rgb = rgb * (1.0 - 0.78 * hole)[..., None]
    EA = H.fills3(n, ip, np.stack([np.full(Np2, 255.0), hv * 255.0, np.zeros(Np2)], 1))
    EB = H.fills3(n, pp, np.stack([np.full(Np2, 255.0), np.zeros(Np2), np.zeros(Np2)], 1))
    EC = H.fills3(n, cl, np.stack([np.full(Np2, 255.0), np.zeros(Np2), np.zeros(Np2)], 1))
    Ie = (EA[..., 0].astype(F32) * F32(1 / 255.0)) * (1.0 - 0.96 * EB[..., 0].astype(F32) * F32(1 / 255.0))
    hue = EA[..., 1].astype(F32) / np.maximum(EA[..., 0].astype(F32), 1.0)
    ecol = H.ramp(np.clip(hue, 0, 1), [(0.10, '#ffc83a'), (0.35, '#a6ff2e'), (0.60, '#ff8a1e'), (0.85, '#c8f4ff')])
    Cpre = (ecol * Ie[..., None]).astype(F32)
    Cg = Cpre + 0.8 * cv2.GaussianBlur(Cpre, (0, 0), 2.5) + 0.45 * cv2.GaussianBlur(Cpre, (0, 0), 9.0)
    rgb = 1.0 - (1.0 - rgb) * (1.0 - np.clip(Cg * 1.2, 0, 1))
    rgb = np.maximum(rgb, (EC[..., 0].astype(F32) * F32(1 / 255.0))[..., None] * 0.95)
    # front leaves, culled so no pair is covered
    def keep(cx, cy, L):
        d2 = (cx[:, None] - pcx[None, :]) ** 2 + (cy[:, None] - pcy[None, :]) ** 2
        return (d2 > ((0.5 * L[:, None] + 1.05 * pd[None, :]) ** 2)).all(1)
    A3, c3 = leaves(150, (140, 300), (0.26, 0.38), [(0.0, '#0a1810'), (0.6, '#133418'), (1.0, '#2c6a30')], True, keep)
    rgb = rgb * (1 - A3)[..., None] + c3 * A3[..., None]
    rgb = np.clip(rgb, 0, 1).astype(F32)
    Ln = H.sstep(0.05, 0.75, H.lum(rgb))
    M = H.lerp(8.0, 250.0, Ln ** 1.4)
    R = H.lerp(150.0, 8.0, Ln)
    CC = H.lerp(130.0, 16.0, Ln)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 17. Claw Gouges - sets of four parallel curved gouges scored in walnut
# -------------------------------------------------------------------------
@_f("wx_claw_gouges", "Claw Gouges",
    "Sets of four parallel curved gouges raked through dark walnut, raw blonde wood in the grooves with lit lips and splinters.")
def claw_gouges(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 17 Claw Gouges: 140 stamped four-stroke gouge sets (tapered polygons) over walnut grain, relief-lit
    n = N
    r = H.rng(seed)
    g1 = cv2.GaussianBlur(r.standard_normal((n, n)).astype(F32), (0, 0), sigmaX=22.0, sigmaY=0.9)
    g1 /= float(g1.std()) + 1e-6
    g2 = cv2.GaussianBlur(r.standard_normal((n, n)).astype(F32), (0, 0), sigmaX=60.0, sigmaY=2.5)
    g2 /= float(g2.std()) + 1e-6
    _, ycol = H.xy(n)
    ring = np.sin(2 * np.pi * (ycol + 90.0 * H.fbm(n, seed + 1, cells=(2, 4, 7))) / 58.0) * 0.5 + 0.5
    wood = np.clip(0.40 + 0.08 * g1 + 0.09 * g2 + 0.16 * ring ** 1.5, 0, 1)
    base = H.ramp(wood, [(0.0, '#170d07'), (0.35, '#2b1a0e'), (0.65, '#452b1a'), (1.0, '#6a4528')])
    polys, fibs, vals = [], [], []
    tt = np.linspace(0, 1, 26)
    chip_x, chip_y = [], []
    for si in range(80):
        L = r.uniform(300, 720)
        th = r.uniform(0, 2 * np.pi)
        kap = r.uniform(-1.2, 1.2)
        cx0, cy0 = r.random(2) * n
        sp = r.uniform(16, 32)
        w0 = sp * r.uniform(0.42, 0.52)
        ang = th + kap * (tt - 0.5)
        Px = np.concatenate([[0.0], np.cumsum(np.cos(ang[:-1]) * L / 25)])
        Py = np.concatenate([[0.0], np.cumsum(np.sin(ang[:-1]) * L / 25)])
        Px = Px - Px.mean() + cx0
        Py = Py - Py.mean() + cy0
        nx, ny = -np.sin(ang), np.cos(ang)
        for i in range(4):
            off = (i - 1.5) * sp * (1 + 0.10 * np.sin(2.5 * tt + i))
            t0 = r.uniform(0.0, 0.14)
            t1 = r.uniform(0.84, 1.0)
            env = np.sin(np.pi * np.clip((tt - t0) / (t1 - t0), 0, 1)) ** 0.45
            w = w0 * env
            lx_, ly_ = Px + nx * (off + w / 2), Py + ny * (off + w / 2)
            rx_, ry_ = Px + nx * (off - w / 2), Py + ny * (off - w / 2)
            polys.append(np.stack([np.concatenate([lx_, rx_[::-1]]), np.concatenate([ly_, ry_[::-1]])], 1))
            vals.append(r.uniform(140, 255))
            ok = env > 0.2
            for fo in (-0.26, 0.0, 0.26):
                fibs.append(np.stack([(Px + nx * (off + fo * w))[ok], (Py + ny * (off + fo * w))[ok]], 1))
            e = np.array([0, -1])
            for q in e:
                chip_x.extend((Px[q] + nx[q] * off[q] + r.normal(0, 7, 5)).tolist())
                chip_y.extend((Py[q] + ny[q] * off[q] + r.normal(0, 7, 5)).tolist())
    polys = [p.astype(F32) for p in polys]
    K = len(polys)
    G = H.fills3(n, polys, np.stack([np.array(vals), np.full(K, 255.0), np.zeros(K)], 1))
    Gm = G[..., 1].astype(F32) * F32(1 / 255.0)
    Gv = np.clip(G[..., 0].astype(F32) / np.maximum(G[..., 1].astype(F32), 1.0), 0, 1)
    Kf = len(fibs)
    Fc = H.lines3(n, [f.astype(F32) for f in fibs], np.stack([np.full(Kf, 255.0), np.zeros(Kf), np.zeros(Kf)], 1), 1)
    Fm = Fc[..., 0].astype(F32) * F32(1 / 255.0) * Gm
    chips = np.zeros((n, n), F32)
    H.points(chips, np.array(chip_x), np.array(chip_y), r.uniform(0.5, 1.0, len(chip_x)), mode="max")
    relief = H.emboss(H.blur(Gm, 2.0) * 6.0, 1.0)
    floor_t = np.clip(0.30 + 0.45 * Gv + 0.10 * g1 + 0.20 * Fm, 0, 1)
    floor = H.ramp(floor_t, [(0.0, '#8a6038'), (0.5, '#c79a62'), (1.0, '#f4dcaa')])
    rgb = base * (1 - Gm)[..., None] + floor * Gm[..., None]
    rgb *= np.clip(1.0 + 1.1 * relief, 0.38, 1.7)[..., None]
    rgb = rgb * (1 - 0.5 * chips)[..., None] + H.hexrgb('#f0d4a0') * (0.55 * chips)[..., None]
    rgb = np.clip(rgb, 0, 1).astype(F32)
    Ln = H.sstep(0.04, 0.75, H.lum(rgb))
    M = H.lerp(40.0, 235.0, Ln)
    R = H.lerp(185.0, 70.0, Ln) + 14.0 * g1
    CC = H.lerp(85.0, 24.0, Ln)
    return H.finish_out(rgb, H.spec_pack(M, np.clip(R, 0, 255), CC))


# -------------------------------------------------------------------------
# 18. Feathered Serpent Plumage - long iridescent tail-covert ribbons
# -------------------------------------------------------------------------
@_f("wx_serpent_plumage", "Feathered Serpent Plumage",
    "Long overlapping quetzal tail-covert ribbons flowing in S-curves, barbed vanes shifting emerald to turquoise to blue with gold.")
def serpent_plumage(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 18 Feathered Serpent Plumage: 900 traced lanceolate ribbons, per-ribbon barbs + rachis, sheen drift
    n = N
    m = 512
    r = H.rng(seed)
    ang = 0.10 + 1.15 * H.fbm(m, seed + 1, cells=(2, 3, 5, 9), gain=0.65)
    u = np.cos(ang).astype(F32)
    v = np.sin(ang).astype(F32)
    K, steps, hh = 1500, 34, 5.0
    p0 = np.stack([r.random(K) * (n + 500) - 250, r.random(K) * (n + 500) - 250], 1).astype(F32)
    P = _strands(u, v, p0, steps, hh)
    Lp = P.shape[1]
    T = np.gradient(P, axis=1)
    T = T / (np.linalg.norm(T, axis=2, keepdims=True) + 1e-6)
    Nn = np.stack([-T[..., 1], T[..., 0]], -1)
    s = np.linspace(0, 1, Lp)
    w0 = r.uniform(14, 26, K)
    env = (np.sin(np.pi * s) ** 0.55)[None, :]
    wid = (w0[:, None] * (0.16 + 0.84 * env)).astype(F32)
    left = P + Nn * (wid / 2)[..., None]
    right = P - Nn * (wid / 2)[..., None]
    poly = np.round(np.concatenate([left, right[:, ::-1]], 1) * 8).astype(np.int32)
    j = np.arange(1, Lp - 1)
    en = np.empty((K, Lp - 2, 2, 2, 2), F32)
    for si, side in enumerate((1.0, -1.0)):
        st_ = P[:, j]
        e_ = st_ + Nn[:, j] * (side * wid[:, j] * 0.51)[..., None] - T[:, j] * (wid[:, j] * 0.5)[..., None]
        en[:, :, si, 0] = st_
        en[:, :, si, 1] = e_
    bar = np.round(en * 8).astype(np.int32)
    hf = H.fbm(m, seed + 2, cells=(2, 3, 6), gain=0.7)
    mid = P[:, Lp // 2]
    hue_i = np.clip(0.42 + 0.50 * H.sample(hf, mid[:, 0] / 4.0, mid[:, 1] / 4.0) + r.normal(0, 0.07, K), 0.03, 0.92)
    hue_i[r.random(K) < 0.06] = 0.97
    edge_l = np.round(left * 8).astype(np.int32)
    edge_r = np.round(right * 8).astype(np.int32)
    rach = np.round(P * 8).astype(np.int32)
    cvs = np.zeros((n, n, 3), np.uint8)
    par = (j & 1).astype(bool)
    for k in r.permutation(K):
        hcol = int(hue_i[k] * 255)
        cv2.fillPoly(cvs, [poly[k]], (hcol, 118, 255), cv2.LINE_AA, 3)
        b = bar[k]
        bb = b[par].reshape(-1, 2, 1, 2)
        bd = b[~par].reshape(-1, 2, 1, 2)
        cv2.polylines(cvs, list(bb.reshape(-1, 2, 1, 2)), False, (hcol, 240, 255), 1, cv2.LINE_AA, 3)
        cv2.polylines(cvs, list(bd.reshape(-1, 2, 1, 2)), False, (hcol, 36, 255), 1, cv2.LINE_AA, 3)
        cv2.polylines(cvs, [edge_l[k].reshape(-1, 1, 2), edge_r[k].reshape(-1, 1, 2)], False, (hcol, 40, 255), 1, cv2.LINE_AA, 3)
        cv2.polylines(cvs, [rach[k].reshape(-1, 1, 2)], False, (hcol, 255, 255), 1, cv2.LINE_AA, 3)
    A = cvs[..., 2].astype(F32) * F32(1 / 255.0)
    den = np.maximum(cvs[..., 2].astype(F32), 1.0)
    Hh = np.clip(cvs[..., 0].astype(F32) / den, 0, 1)
    Bb = np.clip(cvs[..., 1].astype(F32) / den, 0, 1)
    sheen = H.fbm(n, seed + 3, cells=(3, 6, 12), gain=0.6)
    Hh = np.clip(Hh + 0.20 * sheen, 0, 1)
    ribbon = H.ramp(Hh, [(0.0, '#0b4a24'), (0.25, '#16a04a'), (0.5, '#10b8a0'), (0.75, '#2a86d0'), (0.95, '#d8b43a')])
    ribbon = ribbon * (0.22 + 1.05 * Bb)[..., None]
    bg = H.hexrgb('#06261a')
    rgb = bg * (1 - A)[..., None] + ribbon * A[..., None]
    rgb *= (0.94 + 0.06 * H.grain(n, seed + 5))[..., None]
    rgb = np.clip(rgb, 0, 1).astype(F32)
    Ln = H.sstep(0.04, 0.6, H.lum(rgb))
    M = H.lerp(150.0, 255.0, Ln)
    R = H.lerp(110.0, 28.0, Ln)
    CC = H.lerp(70.0, 16.0, Ln)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 19. Bigfoot Tracks - giant footprints pressed into cracked mud
# -------------------------------------------------------------------------
def _foot_master(S=420):
    big = np.zeros((S * 2, S * 2), np.uint8)
    c = S
    k = S * 0.9

    def el(cx, cy, ax, ay, val, ang=0.0):
        cv2.ellipse(big, (int(round(c + cx * k)), int(round(c - cy * k))), (int(ax * k), int(ay * k)), ang, 0, 360, int(val), -1, cv2.LINE_AA)
    el(0.02, -0.62, 0.26, 0.28, 255)
    el(0.02, -0.32, 0.23, 0.32, 190)
    el(0.10, -0.20, 0.20, 0.28, 150)
    el(0.0, 0.22, 0.36, 0.26, 255)
    el(-0.27, 0.74, 0.16, 0.18, 235, 15)
    el(-0.04, 0.84, 0.12, 0.135, 225)
    el(0.17, 0.80, 0.11, 0.125, 220)
    el(0.32, 0.70, 0.10, 0.115, 215)
    el(0.42, 0.55, 0.085, 0.10, 205)
    t = cv2.resize(big, (S, S), interpolation=cv2.INTER_AREA).astype(F32) * F32(1 / 255.0)
    return cv2.GaussianBlur(t, (0, 0), 1.5)


@_f("wx_bigfoot_tracks", "Bigfoot Tracks",
    "Giant five-toed footprints pressed into sun-cracked mud, dark wet water pooled in each print, clay lips and crack polygons.")
def bigfoot_tracks(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 19 Bigfoot Tracks: stamped rotated/mirrored foot depth maps over a two-scale Voronoi mud-crack network
    n = N
    r = H.rng(seed)
    master = _foot_master(420)
    tiles = H.scaled_rotset(master, (250, 320, 400), k=24, span=2 * np.pi)
    Pm = np.zeros((n, n), F32)
    xs, ys, ti, fl = [], [], [], []
    for gy in range(5):
        for gx in range(5):
            if r.random() < 0.15:
                continue
            xs.append((gx + 0.5 + r.uniform(-0.36, 0.36)) * n / 5.0)
            ys.append((gy + 0.5 + r.uniform(-0.36, 0.36)) * n / 5.0)
            ti.append(int(r.integers(0, 3)) * 24 + int(r.integers(0, 24)))
            fl.append(int(r.integers(0, 2)))
    H.splat(Pm, tiles, ti, xs, ys, flip=fl, mode="max")
    pr = np.clip(Pm * 1.4, 0, 1)
    prb = H.blur(pr, 3.0)
    wet = H.sstep(0.12, 0.40, prb)
    # mud cracks, two scales
    wx = 4.0 * H.fbm(n, seed + 1, cells=(30, 60))
    wy = 4.0 * H.fbm(n, seed + 2, cells=(30, 60))
    d1, lab1, _, _ = H.voronoi(n, H.jitter_pts(n, 90.0, seed + 3, jit=0.95, margin=20))
    ed1 = H.warp(H.edge_dist(lab1), wx, wy)
    d2, lab2, _, _ = H.voronoi(n, H.jitter_pts(n, 34.0, seed + 4, jit=0.95, margin=20))
    ed2 = H.warp(H.edge_dist(lab2), wx, wy)
    dry = H.sstep(0.40, 0.62, H.fbm(n, seed + 5, cells=(4, 8, 16)) * 0.5 + 0.5)
    cw1 = 1.8 + 2.6 * np.clip(0.5 + 0.8 * H.fbm(n, seed + 6, cells=(10, 20, 40)), 0, 1)
    crack = np.maximum(1.0 - H.sstep(cw1, cw1 + 1.2, ed1), (1.0 - H.sstep(0.9, 2.1, ed2)) * dry)
    crack = crack * (1.0 - H.sstep(0.10, 0.45, prb))
    cell = H.hash01(lab1.astype(np.int64), 7)
    lift = np.exp(-ed1 / 12.0) * (1.0 - crack)
    val = np.clip(0.30 + 0.34 * cell + 0.14 * H.fbm(n, seed + 7, cells=(6, 14, 40)) + 0.30 * lift
                  + 0.05 * H.grain(n, seed + 8), 0, 1)
    mud = H.ramp(val, [(0.0, '#2d1f14'), (0.4, '#5a4128'), (0.7, '#8a6643'), (1.0, '#b48c60')])
    mud = mud * (1.0 - 0.9 * crack)[..., None] + H.hexrgb('#120c08') * (0.9 * crack)[..., None]
    relief = H.emboss(H.blur(Pm, 2.4) * 8.0, 1.0)
    inner = np.clip(0.10 + 0.32 * np.clip(prb * 1.6 - 0.2, 0, 1) + 0.30 * relief, 0, 1)
    wetc = H.ramp(inner, [(0.0, '#0b0806'), (0.5, '#201610'), (1.0, '#4a3624')])
    sheen = H.sstep(0.55, 0.90, H.fbm(n, seed + 9, cells=(5, 10)) * 0.5 + 0.5) * wet
    wetc = np.clip(wetc + (0.14 * sheen)[..., None] * np.array([0.9, 0.85, 0.8], F32), 0, 1)
    rgb = mud * (1 - wet)[..., None] + wetc * wet[..., None]
    rgb *= np.clip(1.0 + 0.7 * relief * (1 - 0.7 * wet), 0.5, 1.5)[..., None]
    rgb = np.clip(rgb, 0, 1).astype(F32)
    Ln = H.sstep(0.03, 0.5, H.lum(rgb))
    M = H.lerp(8.0 + 30.0 * Ln, 30.0, wet)
    R = H.lerp(H.lerp(240.0, 120.0, Ln), 8.0, wet)
    CC = H.lerp(H.lerp(240.0, 120.0, Ln), 16.0, wet)
    return H.finish_out(rgb, H.spec_pack(M, np.clip(R, 0, 255), CC))


# -------------------------------------------------------------------------
# 20. Mokele Hide - elephant-thick grey skin, deep crosshatched wrinkles, pores
# -------------------------------------------------------------------------
@_f("wx_mokele_wrinkle", "Mokele Hide",
    "Grey elephant-style hide scored by deep crisscross creases and a finer cross-hatch, clay dust on the ridges, pitted pores.")
def mokele_wrinkle(seed):
    # [S20 2026-10-12 owner: Fractured Wilds rebuild] 20 Mokele Hide (v3, coordinator review 2): two crossing sets of THIN wavy creases 60 deg apart (lam 36/42 -> ~45 px rhomb cells) + 3 long deep folds (lam 380) + fine cross-hatch (11-13 px); thin dark creases on grey, no thick stripes
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)
    ang_f = 0.05 * _z(H.fbm(n, seed + 1, cells=(2, 3, 5), gain=0.7))
    wA = _z(H.fbm(n, seed + 2, cells=(5, 10, 20), gain=0.7))
    wB = _z(H.fbm(n, seed + 3, cells=(6, 12, 24), gain=0.7))
    jit = H.ups(np.ascontiguousarray(_z(H.noise(512, 150, seed + 4)), F32), n)

    def fam(theta, lam, warp, cw, ws, mcells, thr, sd, soft=0.22):
        a_ = theta + ang_f
        xr = X * np.cos(a_) + Y * np.sin(a_)
        ph = (xr + warp * ws + 0.03 * lam * jit) / F32(lam)
        d = np.abs(ph - np.rint(ph))
        ln = np.exp(-(d / F32(cw)) ** 2)
        pres = H.sstep(thr - soft, thr + soft, H.ups(np.ascontiguousarray(_z(H.noise(512, mcells, sd)), F32), n))
        return (ln * pres).astype(F32)

    d1 = fam(0.52, 36.0, 6.0, 0.065, wA, 9, -1.2, seed + 10, soft=0.6)
    d2 = fam(-0.52, 42.0, 6.0, 0.065, wB, 11, -1.2, seed + 11, soft=0.6)
    d3 = fam(1.30, 380.0, 26.0, 0.022, wA, 6, -0.7, seed + 14, soft=0.5)
    f1 = fam(0.85, 13.0, 3.0, 0.15, wA, 60, -0.6, seed + 12, soft=0.5)
    f2 = fam(-0.70, 11.0, 3.0, 0.15, wB, 70, -0.6, seed + 13, soft=0.5)
    Ct = np.minimum(1.0, d1 + d2 + 1.2 * d3 + 0.22 * (f1 + f2)).astype(F32)
    fold = 0.5 + 0.5 * np.sin((Y + 60.0 * wA) / 70.0)
    hgt = -(d1 + d2 + 1.6 * d3 + 0.45 * (f1 + f2)) + 0.25 * fold
    relief = H.emboss(H.blur(hgt.astype(F32), 1.0), 3.0)
    ao = H.blur(Ct, 3.0)
    reg = _z(H.fbm(n, seed + 5, cells=(4, 8, 16, 40), gain=0.7))
    t = np.clip(0.66 - 0.46 * Ct - 0.22 * ao + 0.34 * relief + 0.05 * reg + 0.04 * H.grain(n, seed + 6), 0, 1)
    rgb = H.ramp(t, [(0.0, '#1a1817'), (0.3, '#383430'), (0.6, '#6a635b'), (0.85, '#9a9185'), (1.0, '#c4baa9')])
    patch = H.sstep(0.0, 0.9, _z(H.fbm(n, seed + 7, cells=(3, 6, 14), gain=0.7))) * (1.0 - Ct) * 0.2
    clay = H.ramp(np.clip(0.25 + 0.7 * t, 0, 1), [(0.0, '#2a1a10'), (0.5, '#7a4e30'), (1.0, '#c08a5c')])
    rgb = rgb * (1 - patch)[..., None] + clay * patch[..., None]
    pits = np.zeros((n, n), F32)
    H.points(pits, r.random(40000) * n, r.random(40000) * n, r.uniform(0.5, 1.0, 40000), mode="max")
    rgb = (rgb * (1.0 - 0.55 * pits)[..., None]).astype(F32)
    Ln = H.sstep(0.04, 0.7, H.lum(rgb))
    M = H.lerp(4.0, 40.0, Ln)
    R = H.lerp(238.0, 150.0, Ln)
    CC = H.lerp(235.0, 120.0, Ln)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


