# -*- coding: utf-8 -*-
"""GRAVITY & EXOTIC chapter (cz_ 31-40): lenses, black holes, warped space, jets, foam.

[S19 2026-10-12 owner: Fractured Cosmos rebuild] one function per finish; each
writes its OWN structure and its OWN spec story. Only plumbing comes from helpers.
"""
from __future__ import annotations

import numpy as np
import cv2

from . import helpers as H

F32 = np.float32
N = H.N


def _snoise(rows, cols, seed, ang=0.0, n=N):
    """Anisotropic smooth noise: random (rows x cols) grid resampled to n x n (optionally rotated by ang)."""
    g = H.rng(seed).standard_normal((rows, cols)).astype(F32)
    if ang == 0.0:
        return cv2.resize(g, (n, n), interpolation=cv2.INTER_CUBIC)
    X, Y = H.xy(n)
    c, s = float(np.cos(ang)), float(np.sin(ang))
    u = ((X - n / 2) * c + (Y - n / 2) * s) * (cols / n) + cols / 2
    v = (-(X - n / 2) * s + (Y - n / 2) * c) * (rows / n) + rows / 2
    return cv2.remap(g, u.astype(F32), v.astype(F32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)


def _specks(n, seed, density, lo=0.10, hi=0.75, power=3.0):
    """1 px field stars: float canvas of single-pixel specks and their (xs, ys)."""
    r = H.rng(seed)
    cnt = int(n * n * density)
    xs = r.integers(0, n, cnt)
    ys = r.integers(0, n, cnt)
    v = (lo + (hi - lo) * r.random(cnt) ** power).astype(F32)
    cvs = np.zeros((n, n), F32)
    H.points(cvs, xs, ys, v)
    return cvs


def _gz(n, seed, amp=0.28):
    """Ground brightness modulation: smooth clouds clipped to >= 0.58 (a negative factor clipped to black
    leaves hard-edged dark islands) plus 1 px grain to break 8-bit banding of dark gradients."""
    g = np.clip(0.95 + amp * H.fbm(n, seed, cells=(2, 4, 8, 16), gain=0.6), 0.58, 1.5)
    g *= 1.0 + 0.05 * H.rng(seed + 977).standard_normal((n, n)).astype(F32)
    return g.astype(F32)


# -------------------------------------------------------------------------
# 31. Einstein Ring Arcs
# -------------------------------------------------------------------------
def einstein_arcs(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 31 Einstein Ring Arcs: many small gravitational lenses, each a tiny gold galaxy wrapped by tangentially stretched electric-blue arcs and broken rings (tapered ends), on a dark mirror-black ground
    n = N
    r = H.rng(seed)
    pts = H.jitter_pts(n, 132.0, seed + 1, jit=0.9, margin=40)
    pts = pts[r.random(len(pts)) < 0.88]
    K = len(pts)
    thE = np.exp(r.uniform(np.log(17.0), np.log(66.0), K))
    ell = r.uniform(0.0, 0.15, K)
    rot = r.uniform(0.0, 360.0, K)
    dd = np.zeros((n, n), np.uint8)
    bb = np.zeros((n, n), np.uint8)
    hh = np.zeros((n, n), np.uint8)
    SC, SH = 16, 4

    def arc(cvs, cx, cy, a, b, rt, a0, a1, val, tk):
        cv2.ellipse(cvs, (int(round(cx * SC)), int(round(cy * SC))), (max(1, int(round(a * SC))), max(1, int(round(b * SC)))),
                    float(rt), float(a0), float(a1), int(val), int(tk), cv2.LINE_AA, SH)

    def piece(cx, cy, a, b, rt, ac, L, tk, val):
        a0, a1 = ac - L / 2.0, ac + L / 2.0
        e = 0.3 * L
        arc(dd, cx, cy, a, b, rt, a0, a0 + e, 0.5 * val, 1)
        arc(dd, cx, cy, a, b, rt, a1 - e, a1, 0.5 * val, 1)
        arc(bb, cx, cy, a, b, rt, a0 + 0.6 * e, a1 - 0.6 * e, val, tk)
        if tk >= 3:
            arc(hh, cx, cy, a, b, rt, a0 + e, a1 - e, 255, 1)

    core = np.zeros((n, n), F32)
    core2 = np.zeros((n, n), F32)
    for i in range(K):
        cx, cy = float(pts[i, 0]), float(pts[i, 1])
        a = float(thE[i])
        b = a * (1.0 - float(ell[i]))
        rt = float(rot[i])
        tk = int(np.clip(a / 9.0 + r.uniform(0, 1.8), 2, 8))
        kind = r.random()
        if kind < 0.30:
            npc = int(r.integers(2, 4))
            a0 = r.uniform(0, 360)
            span = 360.0 / npc
            for j in range(npc):
                piece(cx, cy, a, b, rt, a0 + (j + 0.5) * span, span - r.uniform(30, 75), tk, r.uniform(170, 255))
        else:
            ac = r.uniform(0, 360)
            piece(cx, cy, a, b, rt, ac, r.uniform(55, 150), tk, r.uniform(185, 255))
            if r.random() < 0.55:
                piece(cx, cy, a, b, rt, ac + 180 + r.uniform(-35, 35), r.uniform(30, 90), max(2, tk - 1), r.uniform(130, 215))
            if r.random() < 0.22:
                piece(cx, cy, a * 0.52, b * 0.52, rt, ac + r.uniform(60, 120), r.uniform(30, 70), 2, r.uniform(110, 190))
        for _ in range(int(r.integers(1, 4))):            # weak-lensing arclets further out
            ra = a * r.uniform(1.5, 2.7)
            a0_ = r.uniform(0, 360)
            arc(dd, cx, cy, ra, ra * (1.0 - float(ell[i])), rt, a0_, a0_ + r.uniform(10, 26), r.uniform(95, 165), int(r.integers(1, 3)))
        jx, jy = r.normal(0, 1.6, 2)
        core[int(np.clip(cy + jy, 0, n - 1)), int(np.clip(cx + jx, 0, n - 1))] += r.uniform(30, 52)
        core2[int(np.clip(cy + jy, 0, n - 1)), int(np.clip(cx + jx, 0, n - 1))] += r.uniform(8, 14)
    A1 = dd.astype(F32) / 255.0
    A2 = bb.astype(F32) / 255.0
    Hh = hh.astype(F32) / 255.0
    arcs = np.clip(A1 + A2, 0, 1)
    tcol = np.clip(0.5 + 0.6 * H.fbm(n, seed + 2, cells=(3, 6, 12), gain=0.6), 0, 1)
    arccol = H.ramp(tcol, [(0.0, '#3a86ff'), (0.5, '#42d0ff'), (1.0, '#8c6cff')])
    cores = np.clip(H.blur(core, 2.6) + H.blur(core2, 1.1), 0, 1.4)
    fld = _specks(n, seed + 4, 0.0035, 0.08, 0.55, 3.0)
    gz = _gz(n, seed + 5)
    rgb = np.array([0.040, 0.070, 0.210], F32)[None, None, :] * gz[..., None]
    rgb += (arcs * 1.12)[..., None] * arccol
    rgb += (H.blur(A2, 2.4) * 0.5)[..., None] * arccol
    rgb += (Hh * 0.55)[..., None] * np.array([0.8, 0.95, 1.0], F32)
    rgb += cores[..., None] * np.array([1.0, 0.80, 0.34], F32)
    rgb += (H.blur(core, 7.0) * 1.3)[..., None] * np.array([0.9, 0.55, 0.12], F32)
    rgb += fld[..., None] * np.array([0.8, 0.88, 1.0], F32)
    rgb = np.clip(rgb, 0, 1)
    # [S19 coordinator polish A 2026-10-12] spec richness: the spec now carries the paint's structure (matte/rough ground with 1 px flake; lines, arcs, cores = satin then mirror metal)
    M, R, CC = H.structure_spec(rgb, seed + 91, [(0.14, 0.30, 205.0, 40.0, 24.0), (0.45, 0.85, 255.0, 5.0, 16.0)],
                                ground_m=(35.0, 85.0), halo=(3.0, 2.5, 130.0, 80.0, 40.0))
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 32. Black Hole Photon Rings
# -------------------------------------------------------------------------
def _bh_master(R, cosi, S):
    c = S // 2
    y, x = np.mgrid[0:S, 0:S].astype(F32)
    x -= c
    y -= c
    rr = np.hypot(x, y)
    yp = y / F32(cosi)
    rp = np.hypot(x, yp)
    phi = np.arctan2(yp, x)
    dop = (1.0 + 0.82 * np.cos(phi)) ** 2.6
    dop /= dop.max()
    inner, outer = 1.45 * R, 4.0 * R
    prof = H.sstep(inner * 0.9, inner * 1.12, rp) * (1.0 - H.sstep(inner, outer, rp)) ** 1.7
    bands = 0.80 + 0.20 * np.cos(rp / (0.2 * R) * 2.0)
    disk = prof * dop * bands
    lens = np.exp(-((rr - 1.34 * R) / (0.17 * R)) ** 2) * (0.30 + 0.70 * H.sstep(-0.3, 0.9, -y / (rr + 1e-3))) * (0.35 + 0.65 * dop ** 0.4)
    ring = np.exp(-((rr - 1.075 * R) / max(0.9, 0.034 * R)) ** 2)
    shadow = 1.0 - H.sstep(R - 0.7, R + 0.7, rr)
    return np.stack([disk + 0.9 * lens, ring, shadow], -1).astype(F32)


def photon_rings(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 32 Black Hole Photon Rings: tilted tiny black holes - jet-black shadow disc, razor-thin gold photon ring, lopsided Doppler-bright orange accretion haze with a lensed arc over the top
    n = N
    r = H.rng(seed)
    classes = (13.0, 20.0, 30.0)
    NR = 16
    tiles = []
    for ci, R in enumerate(classes):
        S = int(8.6 * R) | 1
        for v in range(2):
            cosi = (0.30, 0.78)[v] + 0.1 * r.random()
            tiles += H.rotset(_bh_master(R, cosi, S), NR, 2 * np.pi)
    pts = H.jitter_pts(n, 188.0, seed + 1, jit=0.88, margin=60)
    pts = pts[r.random(len(pts)) < 0.78]
    K = len(pts)
    cl = r.choice(3, K, p=[0.46, 0.32, 0.22])
    vv = r.integers(0, 2, K)
    rt = r.integers(0, NR, K)
    ti = (cl * 2 + vv) * NR + rt
    cv = np.zeros((n, n, 3), F32)
    H.splat(cv, tiles, ti, pts[:, 0], pts[:, 1], mode="add", flip=r.integers(0, 4, K))
    disk = np.clip(cv[..., 0], 0, 1.6)
    ring = np.clip(cv[..., 1], 0, 1.0)
    sh = np.clip(cv[..., 2], 0, 1.0)
    hot = H.ramp(np.clip(disk / 1.05, 0, 1), [(0.0, '#000000'), (0.18, '#5c1306'), (0.42, '#e25a10'), (0.70, '#ffb42e'),
                                              (0.90, '#ffe8a8'), (1.0, '#ffffff')])
    gz = _gz(n, seed + 2)
    rgb = np.array([0.090, 0.070, 0.125], F32)[None, None, :] * gz[..., None]
    rgb += _specks(n, seed + 3, 0.003, 0.1, 0.6)[..., None] * np.array([0.9, 0.9, 1.0], F32)
    rgb += hot
    rgb += (H.blur(disk, 8.0) * 0.45)[..., None] * np.array([0.60, 0.26, 0.05], F32)
    rgb += (ring * 1.15)[..., None] * np.array([1.0, 0.90, 0.58], F32)
    rgb *= (1.0 - 0.985 * sh)[..., None]
    rgb = np.clip(rgb, 0, 1)
    dk = np.clip(disk, 0, 1)
    rg = np.clip(ring * 1.2, 0, 1)
    gr = _snoise(1000, 1000, seed + 6)
    # [S19 coordinator polish A 2026-10-12] spec richness: the spec now carries the paint's structure (matte/rough ground with 1 px flake; lines, arcs, cores = satin then mirror metal)
    M, R_, CC = H.structure_spec(rgb, seed + 91, [(0.16, 0.40, 170.0, 40.0, 28.0), (0.62, 0.95, 250.0, 7.0, 16.0)],
                                 ground_m=(35.0, 85.0), halo=(4.0, 1.4, 110.0, 80.0, 40.0), grain=0.8)
    R_ = H.lerp(R_, 15.0, sh)
    M = M * (1 - sh)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 33. Spacetime Warp Grid
# -------------------------------------------------------------------------
def spacetime_grid(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 33 Spacetime Warp Grid: fine cyan graph paper pinched into funnels toward dozens of gravity wells (and stretched over a few hills), brighter where the sheet is compressed, on navy satin
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)
    qx = np.array(X, F32)
    qy = np.array(Y, F32)
    K = 30
    cx = r.uniform(0, n, K)
    cy = r.uniform(0, n, K)
    sig = np.exp(r.uniform(np.log(50.0), np.log(180.0), K))
    A = np.where(r.random(K) < 0.80, r.uniform(0.8, 2.3, K), r.uniform(-0.40, -0.15, K))
    for k in range(K):
        R4 = 3.6 * sig[k]
        x0, x1 = max(0, int(cx[k] - R4)), min(n, int(cx[k] + R4) + 1)
        y0, y1 = max(0, int(cy[k] - R4)), min(n, int(cy[k] + R4) + 1)
        dx = X[y0:y1, x0:x1] - F32(cx[k])
        dy = Y[y0:y1, x0:x1] - F32(cy[k])
        g = F32(A[k]) * np.exp(-(dx * dx + dy * dy) * F32(0.5 / sig[k] ** 2))
        qx[y0:y1, x0:x1] += g * dx
        qy[y0:y1, x0:x1] += g * dy
    sp = 21.0
    u = qx / F32(sp)
    v = qy / F32(sp)
    guy, gux = np.gradient(u)
    gvy, gvx = np.gradient(v)
    mu = np.hypot(gux, guy) + F32(1e-5)
    mv = np.hypot(gvx, gvy) + F32(1e-5)
    iu = np.round(u)
    iv = np.round(v)
    du = np.abs(u - iu) / mu
    dv = np.abs(v - iv) / mv
    mju = ((iu.astype(np.int32) % 5) == 0).astype(F32)
    mjv = ((iv.astype(np.int32) % 5) == 0).astype(F32)
    LU = np.exp(-(du / (0.72 + 0.55 * mju)) ** 2) * (0.60 + 0.40 * mju) * H.sstep(1.8, 4.6, 1.0 / mu)
    LV = np.exp(-(dv / (0.72 + 0.55 * mjv)) ** 2) * (0.60 + 0.40 * mjv) * H.sstep(1.8, 4.6, 1.0 / mv)
    L = np.maximum(LU, LV)
    maj = np.where(LU >= LV, mju, mjv)
    comp = np.sqrt(mu * mv) * F32(sp)
    gl = H.blur(H.sstep(1.3, 5.5, comp), 7.0)
    gz = _gz(n, seed + 3)
    rgb = np.array([0.030, 0.075, 0.215], F32)[None, None, :] * gz[..., None]
    rgb += gl[..., None] * np.array([0.05, 0.30, 0.50], F32)
    lc = np.array([0.28, 0.88, 1.0], F32)[None, None, :] * (1 - maj)[..., None] + np.array([0.82, 1.0, 1.0], F32)[None, None, :] * maj[..., None]
    L2 = np.clip(L * (1.0 + 0.55 * gl), 0, 1)
    rgb = rgb * (1 - L2)[..., None] + L2[..., None] * lc
    rgb = np.clip(rgb, 0, 1)
    lt = np.clip((H.lum(rgb) - 0.06) / 0.7, 0, 1)
    M = H.lerp(110.0, 250.0, lt)
    R_ = H.lerp(112.0, 12.0, lt ** 0.7) + 10.0 * _snoise(700, 700, seed + 7) * (1 - lt)
    CC = H.lerp(58.0, 16.0, H.sstep(0.0, 0.35, lt))
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 34. Gravitational Wave Chirp
# -------------------------------------------------------------------------
def gravitational_chirp(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 34 Gravitational Wave Chirp: six inspiralling binaries each shed a two-armed spiral wave whose arms tighten toward the source; where the waves meet they interfere into a lattice of teal and violet nodal lines with vortex points, on anodised metal (visual pass: contour-map blobs -> readable spirals, fewer stronger sources)
    n = N
    m = 1024
    r = H.rng(seed)
    X, Y = H.xy(m)
    K = 6
    sx = r.uniform(-30, m + 30, K)
    sy = r.uniform(-30, m + 30, K)
    Re = np.zeros((m, m), F32)
    Im = np.zeros((m, m), F32)
    for k in range(K):
        dx = X - F32(sx[k])
        dy = Y - F32(sy[k])
        rr = np.hypot(dx, dy) + F32(3.0)
        th = np.arctan2(dy, dx)
        pe = F32(r.uniform(0.50, 0.60))
        kap = F32(r.uniform(1.45, 2.2))
        sg = 1.0 if r.random() < 0.5 else -1.0
        ph = F32(2.0 * sg) * th - kap * np.power(rr, pe) + F32(r.uniform(0, 6.28))
        amp = F32(r.uniform(0.85, 1.4)) / (F32(1.0) + rr / F32(170.0)) ** F32(1.25)
        Re += amp * np.cos(ph)
        Im += amp * np.sin(ph)
    sd = float(Re.std()) + 1e-6
    Re = cv2.resize(Re / F32(sd), (n, n), interpolation=cv2.INTER_CUBIC)
    Im = cv2.resize(Im / F32(sd), (n, n), interpolation=cv2.INTER_CUBIC)
    la = H.zero_set_line(Re, 1.05)
    lb = H.zero_set_line(Im, 1.05)
    shd = 0.5 + 0.5 * np.tanh(1.5 * Re)
    am = np.clip(np.hypot(Re, Im) / 2.2, 0, 1)
    gz = _gz(n, seed + 3)
    rgb = np.array([0.100, 0.060, 0.270], F32)[None, None, :] * (0.50 + 1.0 * shd * gz)[..., None]
    rgb += (0.12 * am * (1 - shd))[..., None] * np.array([0.0, 0.5, 0.5], F32)
    rgb += (la * (0.55 + 0.45 * am))[..., None] * np.array([0.22, 0.95, 0.85], F32)
    rgb += (lb * 0.80)[..., None] * np.array([0.85, 0.42, 1.0], F32)
    rgb = np.clip(rgb, 0, 1)
    lt = np.clip((H.lum(rgb) - 0.05) / 0.6, 0, 1)
    M = H.lerp(232.0, 255.0, lt)
    R_ = H.lerp(66.0, 20.0, lt ** 0.8) + 22.0 * (1 - shd) * (1 - lt)
    CC = H.lerp(90.0, 16.0, H.sstep(0.0, 0.5, lt)) + 24.0 * (1 - shd)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 35. Quasar Jet Beams
# -------------------------------------------------------------------------
def quasar_beams(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 35 Quasar Jet Beams: fifty-odd bright quasar cores each firing a long hair-thin blue-white jet (and a shorter counter-jet) beaded with knots and ending in a puffy magenta radio lobe with a hot spot, on a pearl-flake sky
    n = N
    r = H.rng(seed)
    NQ = 46
    cx = r.uniform(-40, n + 40, NQ)
    cy = r.uniform(-40, n + 40, NQ)
    ang = r.uniform(0, np.pi * 2, NQ)
    Lh = r.uniform(240, 760, NQ)
    polys, vals = [], []
    kn = np.zeros((n, n), F32)
    kn2 = np.zeros((n, n), F32)
    lobeA = np.zeros((n, n), F32)
    lobeH = np.zeros((n, n), F32)
    coreA = np.zeros((n, n), F32)
    for i in range(NQ):
        ca, sa = float(np.cos(ang[i])), float(np.sin(ang[i]))
        bend = float(r.normal(0, 0.05))
        coreA[int(np.clip(cy[i], 0, n - 1)), int(np.clip(cx[i], 0, n - 1))] += r.uniform(1.0, 2.2)
        for sgn in (1.0, -1.0):
            L = float(Lh[i]) * (1.0 if sgn > 0 else r.uniform(0.35, 0.8))
            kb = 1.0 if sgn > 0 else 0.62
            ts = np.linspace(0, 1, 7)
            dd = ts * L
            px = cx[i] + sgn * (ca * dd) - sa * bend * dd * (dd / L)
            py = cy[i] + sgn * (sa * dd) + ca * bend * dd * (dd / L)
            for j in range(6):
                polys.append(np.array([[px[j], py[j]], [px[j + 1], py[j + 1]]]))
                vals.append(int(255 * kb * (1.0 - 0.50 * (j / 6.0))))
            m = int(r.integers(6, 13))
            tb = np.sort(r.random(m) ** 1.35)
            dk = tb * L
            kx = cx[i] + sgn * (ca * dk) - sa * bend * dk * (dk / L)
            ky = cy[i] + sgn * (sa * dk) + ca * bend * dk * (dk / L)
            amp = kb * (0.45 + 0.8 * (1 - tb)) * r.uniform(0.6, 1.3, m)
            ok = (kx >= 0) & (kx < n) & (ky >= 0) & (ky < n)
            H.points(kn, kx[ok], ky[ok], amp[ok], mode="add")
            big = r.random(m) < 0.35
            sel = ok & big
            H.points(kn2, kx[sel], ky[sel], amp[sel], mode="add")
            tx, ty = px[-1], py[-1]
            if 0 <= tx < n and 0 <= ty < n:
                H.points(lobeA, [tx], [ty], [r.uniform(3200, 6200)], mode="add")
                H.points(lobeH, [tx], [ty], [r.uniform(0.8, 1.6)], mode="add")
    va = np.array(vals, np.int32)
    beam = H.lines_u8(n, polys, va, thick=1)
    near = [k for k in range(len(polys)) if k % 6 < 2]            # first two segments of every side: thicker near the core
    H.lines_u8(n, [polys[k] for k in near], va[near], thick=2, canvas=beam)
    beam = beam.astype(F32) / 255.0
    beam = np.clip(beam + 0.5 * H.blur(beam, 1.3), 0, 1)
    knots = np.clip(H.blur(kn, 1.3) * 11.0 + H.blur(kn2, 3.0) * 0.07, 0, 1.2)
    cores = np.clip(H.blur(coreA, 2.2) * 26.0 + H.blur(coreA, 7.0) * 45.0, 0, 1.4)
    cloud = H.blur(lobeA, 30.0)
    dxw = (9.0 * H.fbm(n, seed + 4, cells=(6, 12, 24))).astype(F32)
    dyw = (9.0 * H.fbm(n, seed + 5, cells=(6, 12, 24))).astype(F32)
    cloud = H.warp(cloud, dxw, dyw)
    puff = np.clip(0.55 + 0.45 * H.fbm(n, seed + 6, cells=(20, 40, 80), gain=0.8), 0.1, 1.4)
    fil = np.clip(H.ridged(H.fbm(n, seed + 7, cells=(16, 32, 64, 128), gain=0.8)), 0, 1) ** 2
    cloud = cloud * (puff + 0.30 * fil)
    lobe = H.sstep(0.05, 0.62, cloud)
    lobcol = H.ramp(np.clip(cloud / 1.1, 0, 1), [(0.0, '#2a0c44'), (0.3, '#8a1c8e'), (0.65, '#e63aa8'), (1.0, '#ffc4ee')])
    hot = np.clip(H.blur(lobeH, 5.0) * 80.0, 0, 1)
    st = _specks(n, seed + 8, 0.0065, 0.12, 0.8, 2.6)
    gz = _gz(n, seed + 9)
    rgb = np.array([0.062, 0.062, 0.190], F32)[None, None, :] * gz[..., None]
    rgb += lobcol * lobe[..., None] * 0.95
    rgb += (hot * 0.9)[..., None] * np.array([1.0, 0.80, 0.95], F32)
    rgb += (beam * 0.95)[..., None] * np.array([0.72, 0.86, 1.0], F32)
    rgb += (knots * 0.9)[..., None] * np.array([0.9, 0.96, 1.0], F32)
    rgb += (cores)[..., None] * np.array([1.0, 0.95, 0.9], F32)
    rgb += st[..., None] * np.array([0.86, 0.9, 1.0], F32)
    rgb = np.clip(rgb, 0, 1)
    # [S19 coordinator polish A 2026-10-12] spec richness: the spec now carries the paint's structure (matte/rough ground with 1 px flake; lines, arcs, cores = satin then mirror metal)
    M, R_, CC = H.structure_spec(rgb, seed + 91, [(0.10, 0.20, 150.0, 85.0, 36.0), (0.30, 0.55, 205.0, 30.0, 24.0), (0.65, 0.95, 252.0, 5.0, 16.0)],
                                 ground_m=(35.0, 85.0))
    fl = st > 0.0
    M = np.where(fl, 255.0, M)
    R_ = np.where(fl, 4.0, R_)
    CC = np.where(fl, 16.0, CC)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 36. Dark Matter Caustics
# -------------------------------------------------------------------------
def dark_caustics(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 36 Dark Matter Caustics: a sharp web of bright violet-white caustic lines, like sunlight through a pool, from mapping millions of jittered points through the gradient of two smooth gravitational potentials (broad cells + fine ripples); brushed-metal floor (visual pass: regular-grid moire -> jittered samples; added the fine web for SCALE)
    n = N
    r = H.rng(seed)

    def caust(sd, cells, gain, cov, S):
        phi = H.fbm(n, sd, cells=cells, gain=gain)
        gy, gx = np.gradient(phi)
        hxx = np.gradient(gx, axis=1)
        hyy = np.gradient(gy, axis=0)
        h92 = float(np.percentile(np.abs(np.stack([hxx[::8, ::8], hyy[::8, ::8]])), 92)) + 1e-9
        A = cov / h92
        gxs = cv2.resize(gx, (S, S), interpolation=cv2.INTER_LINEAR)
        gys = cv2.resize(gy, (S, S), interpolation=cv2.INTER_LINEAR)
        step = F32(n / S)
        ss = (np.arange(S, dtype=F32) + F32(0.5)) * step
        px = ss[None, :] + F32(A) * gxs + (r.random((S, S), dtype=F32) - F32(0.5)) * step
        py = ss[:, None] + F32(A) * gys + (r.random((S, S), dtype=F32) - F32(0.5)) * step
        ix = np.floor(px).astype(np.int32)
        iy = np.floor(py).astype(np.int32)
        ok = (ix >= 0) & (ix < n) & (iy >= 0) & (iy < n)
        idx = iy[ok] * n + ix[ok]
        return np.bincount(idx, minlength=n * n).reshape(n, n).astype(F32) * F32((n / S) ** 2)

    d1 = caust(seed + 1, (5, 9, 17), 0.55, 1.25, 2800)
    d2 = caust(seed + 2, (22, 40, 74), 0.6, 0.95, 2600)
    dens = H.blur(d1 + 0.55 * d2, 0.9)
    tn = H.tonemap(np.maximum(dens - 0.55, 0), 0.42)
    pool = np.clip(0.95 + 0.28 * H.fbm(n, seed + 3, cells=(3, 6, 12, 24), gain=0.6), 0.6, 1.4)
    rgb = H.ramp(np.clip(tn, 0, 1), [(0.0, '#1c1258'), (0.22, '#382098'), (0.5, '#7c58f0'), (0.78, '#d0bcff'), (1.0, '#ffffff')])
    rgb = rgb * np.where(tn < 0.5, pool, 1.0)[..., None]
    rgb = np.clip(rgb, 0, 1)
    brush = _snoise(1400, 36, seed + 6, ang=0.42)
    M = H.lerp(176.0, 245.0, tn)
    R_ = H.lerp(118.0, 12.0, tn ** 0.65) + 20.0 * brush * (1 - tn)
    CC = H.lerp(38.0, 16.0, tn)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 37. Wormhole Tunnels
# -------------------------------------------------------------------------
def _tunnel_tile(R, arms, tw, rot0):
    S = int(2 * R * 1.10) | 1
    c = S // 2
    y, x = np.mgrid[0:S, 0:S].astype(F32)
    x -= c
    y -= c
    rr = np.hypot(x, y) / F32(R)
    th = np.arctan2(y, x)
    q = 0.76
    rho = -np.log(np.maximum(rr, 1e-3)) / np.log(1.0 / q)
    fr = rho - np.floor(rho)
    ringp = 0.10 + 0.90 * np.exp(-((fr - 0.5) / 0.17) ** 2)
    rad_l = (0.5 + 0.5 * np.cos(arms * th + tw * rho * 6.2832)) ** 7 * H.sstep(1.8, 5.0, 6.2832 * rr * R / arms)
    spoke = 0.45 + 0.55 * (0.5 + 0.5 * np.cos(arms * th + tw * rho * 6.2832))
    spacing = rr * R * np.log(1.0 / q)
    fade = H.sstep(1.1, 3.0, spacing)
    env = (0.18 + 0.82 * H.sstep(0.10, 0.92, rr) ** 0.8) * (1.0 - H.sstep(0.86, 1.0, rr))
    b = np.clip(ringp * spoke + 0.8 * rad_l * (0.3 + 0.7 * ringp), 0, 1.3) * fade * env
    throat = 1.0 - H.sstep(0.10, 0.15, rr)
    dep = np.clip(rr, 0, 1)
    col = H.ramp(dep, [(0.0, '#8a4cff'), (0.45, '#3a8cff'), (0.75, '#20d8d0'), (1.0, '#5cf0c0')])
    t = col * (b * (1 - throat))[..., None]
    t += (np.exp(-(rr / 0.06) ** 2) * 0.9)[..., None] * np.array([1.0, 1.0, 1.0], F32) + (np.exp(-(rr / 0.20) ** 2) * 0.30)[..., None] * np.array([0.55, 0.40, 1.0], F32)
    rg = H.rng(int(R * 31 + arms * 7 + rot0))
    for _ in range(7):
        a = rg.uniform(0, 6.2832)
        d = rg.uniform(0.0, 0.11) * R
        sx, sy = c + d * np.cos(a), c + d * np.sin(a)
        t += (np.exp(-((x - (sx - c)) ** 2 + (y - (sy - c)) ** 2) / 1.6) * rg.uniform(0.5, 1.0))[..., None] * np.array([1, 1, 1], F32)
    return t.astype(F32)


def wormhole_tunnels(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 37 Wormhole Tunnels: ~100 funnels seen at an angle, 76-300 px across - 14-20 nested rings that shrink geometrically toward a vanishing point OFFSET from the mouth (the offset is why it reads as a tunnel, not a target), wall shading between the rings, brightness falling into a black throat, colour sliding from the mouth hue to a deep hue (teal>violet, amber>crimson, lime>blue, magenta>indigo); NO spokes (coordinator fix 2026-10-12: spoked portals/buttons -> perspective funnels)
    n = N
    r = H.rng(seed)
    radii = (30, 42, 58, 80, 110, 150)
    tiles = []
    for ci, Rr in enumerate(radii):
        tiles.append([_funnel_tile(Rr, float(r.uniform(0.80, 0.88)), float(r.uniform(0.55, 0.88)), seed * 7 + ci * 13 + v) for v in range(3)])
    # [S19 coordinator polish B 2026-10-12] last try: ONE colour pair for the whole sheet (cyan mouth > deep indigo), rings crowd and darken toward a strongly offset throat, faint lensed stars bunched round every mouth
    colA = np.array([[0.22, 0.88, 0.96]], F32)
    colB = np.array([[0.22, 0.20, 0.90]], F32)
    pts = H.jitter_pts(n, 150.0, seed + 1, jit=0.92, margin=130)
    pts = pts[r.random(len(pts)) < 0.88]
    K = len(pts)
    cl = r.choice(6, K, p=[0.26, 0.26, 0.22, 0.14, 0.08, 0.04])
    vr = r.integers(0, 3, K)
    pal = np.zeros(K, np.int64)
    ang = r.uniform(0, 360, K)
    cv = np.zeros((n, n, 3), F32)
    for i in range(K):
        a_t, b_t = tiles[cl[i]][vr[i]]
        Sz = a_t.shape[0]
        Mx = cv2.getRotationMatrix2D(((Sz - 1) / 2.0, (Sz - 1) / 2.0), float(ang[i]), 1.0)
        ra = cv2.warpAffine(a_t, Mx, (Sz, Sz), flags=cv2.INTER_LINEAR)
        rb = cv2.warpAffine(b_t, Mx, (Sz, Sz), flags=cv2.INTER_LINEAR)
        loc = ra[..., None] * colA[pal[i]] + rb[..., None] * colB[pal[i]]
        _put_max(cv, loc, pts[i, 0], pts[i, 1])
    lm = H.lum(cv)
    NL = 44
    Rrk = np.array(radii, F32)[cl][:, None]
    th_ = r.uniform(0, 2 * np.pi, (K, NL)).astype(F32)
    rd_ = Rrk * (1.04 + 0.55 * r.random((K, NL)).astype(F32) ** 1.6)
    lens = np.zeros((n, n), F32)
    for dth in (-0.05, 0.0, 0.05):
        H.points(lens, (pts[:, 0:1] + rd_ * np.cos(th_ + dth)).ravel(), (pts[:, 1:2] + rd_ * np.sin(th_ + dth)).ravel(), np.tile((0.25 + 0.75 * r.random(NL) ** 2).astype(F32), K))
    gz = _gz(n, seed + 2)
    rgb = np.array([0.026, 0.085, 0.130], F32)[None, None, :] * gz[..., None]
    rgb += _specks(n, seed + 3, 0.004, 0.1, 0.55)[..., None] * np.array([0.85, 0.95, 1.0], F32)
    rgb += (H.blur(lens, 1.3) * 5.0)[..., None] * np.array([0.72, 0.90, 1.0], F32) * 0.60
    rgb += cv * 1.15
    rgb += (H.blur(lm, 9.0) * 0.55)[..., None] * np.array([0.14, 0.40, 0.55], F32)
    rgb = np.clip(rgb, 0, 1)
    lt = np.clip((H.lum(rgb) - 0.05) / 0.7, 0, 1)
    ci_ = (np.arange(n) // 20).astype(np.int64)
    key = ci_[None, :] * 4099 + ci_[:, None]
    hs = H.hash01(key, seed)
    M = H.lerp(36.0, 236.0, lt)
    R_ = H.lerp(150.0, 26.0, lt ** 0.8)
    CC = H.lerp(16.0, 205.0, hs ** 1.2)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


def _funnel_tile(R, q, off, seed):
    """One tunnel seen at an angle. Returns (A, B) float32 tiles (mouth-hue weight, deep-hue weight). The mouth circle
    (radius R) is centred in the tile; ring k has radius R*q^k and its centre slides toward +x by off*R*(1-q^k)."""
    r = H.rng(seed)
    S = 2 * int(R) + 9
    c = S // 2
    sc = 16
    K = int(np.clip(1 + np.log(0.06) / np.log(q), 12, 24))
    ks = np.arange(K)
    rk = R * q ** ks
    ck = c + off * R * (1.0 - q ** ks)
    d = ks / float(K - 1)
    A = np.zeros((S, S), np.uint8)
    B = np.zeros((S, S), np.uint8)

    def circ(cvs, k, val, tk):
        cv2.circle(cvs, (int(round(ck[k] * sc)), int(round(c * sc))), max(1, int(round(rk[k] * sc))), int(np.clip(val, 0, 255)), tk, cv2.LINE_AA, 4)

    for k in range(K):                                           # wall shading: nested filled discs, each darker
        w = 0.26 * (1.0 - d[k]) ** 1.25
        circ(A, k, 255 * w * (1.0 - d[k]), -1)
        circ(B, k, 255 * w * d[k] * 1.6, -1)
    for k in range(K):                                           # the rings
        tk = max(1, int(round(0.042 * rk[k])))
        b = (0.30 + 0.70 * (1.0 - d[k]) ** 0.8) * (0.80 + 0.30 * r.random())
        it = b * (1.0 - d[k]) ** 0.85 + 0.02
        circ(A, k, 255 * it * (1.0 - d[k]), tk)
        circ(B, k, 255 * it * d[k], tk)
    cv2.circle(A, (int(round(ck[-1] * sc)), int(round(c * sc))), max(1, int(round(rk[-1] * sc * 1.5))), 0, -1, cv2.LINE_AA, 4)
    cv2.circle(B, (int(round(ck[-1] * sc)), int(round(c * sc))), max(1, int(round(rk[-1] * sc * 1.5))), 0, -1, cv2.LINE_AA, 4)
    return A.astype(F32) / 255.0, B.astype(F32) / 255.0


def _put_max(cv, tl, x, y):
    h, w = tl.shape[:2]
    x0 = int(round(x)) - (w >> 1)
    y0 = int(round(y)) - (h >> 1)
    sx0 = max(0, -x0)
    sy0 = max(0, -y0)
    ex = min(w, cv.shape[1] - x0)
    ey = min(h, cv.shape[0] - y0)
    if ex <= sx0 or ey <= sy0:
        return
    dst = cv[y0 + sy0:y0 + ey, x0 + sx0:x0 + ex]
    np.maximum(dst, tl[sy0:ey, sx0:ex], out=dst)


# -------------------------------------------------------------------------
# 38. Cosmic Strings
# -------------------------------------------------------------------------
def cosmic_strings(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 38 Cosmic Strings: ~20 long kinked strings at several brightnesses (some crossing the whole sheet, some short) plus 5 closed loops, each with a wake band of galaxies that appear TWICE, split across the string (gravitational double images), over a dense clumpy multicolour starfield; candy-dark ground, chrome strings, flake stars (coordinator fix 2026-10-12: mostly empty dark canvas -> many strings + doubled-star wake fields so the whole sheet carries detail)
    n = N
    r = H.rng(seed)
    NS0 = 230000
    sx = r.uniform(0, n, NS0)
    sy = r.uniform(0, n, NS0)
    dn = H.fbm(256, seed + 31, cells=(3, 6, 12, 24), gain=0.7)
    pk = np.clip(0.30 + 0.80 * H.sstep(-0.9, 1.1, dn[(sy / 8).astype(int).clip(0, 255), (sx / 8).astype(int).clip(0, 255)]), 0, 1)
    kp = r.random(NS0) < pk
    sx, sy = sx[kp], sy[kp]
    NS = len(sx)
    mag = 0.14 + 0.86 * r.random(NS) ** 2.6
    cls = r.choice(4, NS, p=[0.46, 0.22, 0.20, 0.12])
    pal = np.array([[0.9, 0.93, 1.0], [0.62, 0.78, 1.0], [1.0, 0.82, 0.55], [1.0, 0.55, 0.42]], F32)
    strings = []                                           # (polyline (m,2), brightness 0..1)

    def walk(x0, y0, hd, length, step, sign):
        pts_ = [np.array([x0, y0])]
        for _ in range(int(length / step)):
            hd += r.normal(0, 0.010) + (r.normal(0, 0.17) if r.random() < 0.22 else 0.0)
            pts_.append(pts_[-1] + sign * np.array([np.cos(hd), np.sin(hd)]) * step)
        return pts_

    for s in range(20):
        ang = r.uniform(0, 2 * np.pi)
        x0 = n / 2 + r.uniform(-n * 0.62, n * 0.62)
        y0 = n / 2 + r.uniform(-n * 0.62, n * 0.62)
        step = r.uniform(80.0, 140.0)
        if r.random() < 0.55:
            fwd, bck = r.uniform(1100, 2400), r.uniform(1100, 2400)
        else:
            fwd, bck = r.uniform(250, 800), r.uniform(250, 800)
        back = walk(x0, y0, ang + np.pi, bck, step, 1.0)[::-1]
        front = walk(x0, y0, ang, fwd, step, 1.0)[1:]
        strings.append((np.array(back + front), 0.25 + 0.75 * r.random() ** 0.8))
    for s in range(5):                                      # closed kinked loops
        R0 = r.uniform(90.0, 330.0)
        cxl, cyl = r.uniform(0.08, 0.92, 2) * n
        m = int(r.integers(34, 60))
        th = np.linspace(0, 2 * np.pi, m, endpoint=False)
        rad = R0 * (1.0 + 0.10 * np.sin(2 * th + r.uniform(0, 6.3)) + 0.05 * np.sin(3 * th + r.uniform(0, 6.3)) + 0.03 * r.normal(0, 1, m))
        P = np.stack([cxl + rad * np.cos(th), cyl + rad * np.sin(th)], 1)
        strings.append((np.vstack([P, P[:1]]), 0.45 + 0.55 * r.random()))
    xs_l, ys_l, mg_l, cl_l = [sx], [sy], [mag], [cls]
    for P, bri in strings:                                  # doubled-galaxy wake band along every string
        seglen = np.hypot(*np.diff(P, axis=0).T)
        cnt = int(seglen.sum() * 1.15 * (0.6 + 0.8 * bri))
        idx = r.integers(0, len(P) - 1, cnt)
        t = r.random(cnt)
        base = P[idx] + (P[idx + 1] - P[idx]) * t[:, None]
        tg = P[idx + 1] - P[idx]
        tg = tg / (np.hypot(tg[:, 0], tg[:, 1])[:, None] + 1e-6)
        nm = np.stack([-tg[:, 1], tg[:, 0]], 1)
        off = r.normal(0, 26.0, cnt)
        delta = r.uniform(28.0, 52.0)
        p1 = base + nm * off[:, None]
        p2 = p1 - nm * (np.sign(off) * delta)[:, None]
        mg_ = 0.35 + 0.65 * r.random(cnt) ** 1.5
        c_ = r.choice(4, cnt, p=[0.4, 0.25, 0.25, 0.1])
        for pp_, f_ in ((p1, 1.0), (p2, 0.92)):
            xs_l.append(pp_[:, 0])
            ys_l.append(pp_[:, 1])
            mg_l.append(mg_ * f_)
            cl_l.append(c_)
    xs = np.concatenate(xs_l)
    ys = np.concatenate(ys_l)
    mg = np.concatenate(mg_l)
    cl = np.concatenate(cl_l)
    ix = np.round(xs).astype(np.int64)
    iy = np.round(ys).astype(np.int64)
    bright = mg > 0.46
    cvs = np.zeros((n, n, 3), F32)
    for c in range(3):
        ch = np.zeros((n, n), F32)
        H.points(ch, ix, iy, mg * pal[cl, c])
        cvs[..., c] = ch
    allst = np.zeros((n, n), F32)
    H.points(allst, ix, iy, mg, mode="add")
    halo_src = np.zeros((n, n), F32)
    H.points(halo_src, ix[bright], iy[bright], mg[bright])
    st1 = H.blur(halo_src, 1.3)
    st2 = H.blur(halo_src, 3.8)
    milk = H.blur(allst, 3.0) * 1.8 + H.blur(allst, 9.0) * 3.2
    vals = np.array([int(60 + 190 * b) for _, b in strings], np.int32)
    polys = [np.asarray(P) for P, _ in strings]
    dim = np.flatnonzero(vals < 150)
    brt = np.flatnonzero(vals >= 150)
    sline = np.zeros((n, n), np.uint8)
    if len(dim):
        H.lines_u8(n, [polys[i] for i in dim], vals[dim], thick=1, canvas=sline)
    if len(brt):
        H.lines_u8(n, [polys[i] for i in brt], vals[brt], thick=2, canvas=sline)
    sline = sline.astype(F32) / 255.0
    sglow = H.blur(sline, 3.2)
    gz = _gz(n, seed + 2)
    rgb = np.array([0.050, 0.070, 0.205], F32)[None, None, :] * gz[..., None]
    rgb += (milk * 0.80)[..., None] * np.array([0.55, 0.62, 0.95], F32)
    rgb += cvs * 1.60
    rgb += (st1 * 2.6 + st2 * 2.0)[..., None] * np.array([0.75, 0.82, 1.0], F32) * 0.70
    rgb += (sglow * 1.9)[..., None] * np.array([0.34, 0.50, 1.0], F32)
    rgb += (sline * 1.05)[..., None] * np.array([1.0, 1.0, 1.0], F32)
    rgb = np.clip(rgb, 0, 1)
    star = np.maximum(np.maximum(cvs[..., 0], cvs[..., 1]), cvs[..., 2])
    fl = star > 0.10
    # [S19 coordinator polish A 2026-10-12] spec richness: the spec now carries the paint's structure (matte/rough ground with 1 px flake; lines, arcs, cores = satin then mirror metal)
    sl = np.clip(sline * 1.5, 0, 1)
    M, R_, CC = H.structure_spec(rgb, seed + 91, [(0.22, 0.45, 205.0, 35.0, 24.0), (0.60, 0.95, 255.0, 2.0, 16.0)],
                                 ground_m=(35.0, 90.0), halo=(2.4, 2.2, 140.0, 70.0, 36.0))
    M = np.where(fl | (sl > 0.2), 255.0, M)
    R_ = np.where(fl, 0.0, R_)
    R_ = np.where(sl > 0.2, 2.0, R_)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 39. Quantum Foam
# -------------------------------------------------------------------------
def quantum_foam(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 39 Quantum Foam: dense multi-scale foam of nested and packed bubbles from 100 px down to 3 px, flickering violet-white walls round dark violet interiors; anodised walls, matte interiors
    n = N
    r = H.rng(seed)
    walls = np.zeros((n, n), np.uint8)
    fill = np.zeros((n, n), np.uint8)
    SC, SH = 16, 4
    free_d = np.full((n, n), 4000.0, F32)
    scales = (100.0, 62.0, 40.0, 26.0, 17.0, 11.0, 7.2, 4.8, 3.3)
    for si, rs in enumerate(scales):
        pts = H.jitter_pts(n, 2.45 * rs, seed + 11 * si + 3, jit=0.32, margin=int(rs))
        rad = rs * r.uniform(0.70, 0.82, len(pts))
        ix = np.clip(np.round(pts[:, 0]).astype(np.int64), 0, n - 1)
        iy = np.clip(np.round(pts[:, 1]).astype(np.int64), 0, n - 1)
        ok = free_d[iy, ix] >= rad + 1.3
        ok &= (pts[:, 0] > -rs) & (pts[:, 0] < n + rs) & (pts[:, 1] > -rs) & (pts[:, 1] < n + rs)
        keep = np.where(ok)[0]
        for k in keep:
            cx, cy = float(pts[k, 0]), float(pts[k, 1])
            rr = float(rad[k])
            tk = 1 if rr < 8 else (2 if rr < 20 else 3)
            if rs >= 11.0:
                cv2.circle(fill, (int(round(cx * SC)), int(round(cy * SC))), int(round(rr * SC)), int(r.integers(30, 215)), -1, cv2.LINE_8, SH)
            cv2.circle(walls, (int(round(cx * SC)), int(round(cy * SC))), int(round(rr * SC)), int(r.integers(95, 256)), tk, cv2.LINE_AA, SH)
        wmask = ((walls > 0) * 255).astype(np.uint8)
        free_d = cv2.distanceTransform(255 - wmask, cv2.DIST_L2, 3).astype(F32)
    wa = H.blur(walls.astype(F32) / 255.0, 0.55)
    fa = fill.astype(F32) / 255.0
    gz = _gz(n, seed + 2)
    base = np.array([0.108, 0.062, 0.275], F32)[None, None, :] * gz[..., None]
    fcol = H.ramp(np.clip(fa * 0.9 + 0.05, 0, 1), [(0.0, '#1c1046'), (0.5, '#35208a'), (1.0, '#6c34c8')])
    inside = (fill > 0).astype(F32)
    rgb = base * (1 - inside)[..., None] + fcol * (0.65 + 0.4 * gz[..., None] * 0.5) * inside[..., None]
    wcol = H.ramp(np.clip(wa, 0, 1), [(0.0, '#5a34c8'), (0.45, '#a888ff'), (0.8, '#e2d6ff'), (1.0, '#ffffff')])
    wal = np.clip(wa * 1.15, 0, 1)
    rgb = rgb * (1 - wal)[..., None] + wal[..., None] * wcol
    rgb += (H.blur(wa, 2.6) * 0.30)[..., None] * np.array([0.5, 0.3, 1.0], F32)
    rgb = np.clip(rgb, 0, 1)
    M = H.lerp(8.0, 255.0, np.clip(wa * 1.3, 0, 1))
    R_ = H.lerp(214.0, 34.0, np.clip(wa * 1.3, 0, 1) ** 0.8) - 38.0 * fa * (1 - np.clip(wa * 2, 0, 1))
    CC = H.lerp(236.0, 16.0, H.sstep(0.0, 0.4, wa))
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 40. Cosmic Ray Tracks
# -------------------------------------------------------------------------
def cosmic_ray_tracks(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 40 Cosmic Ray Tracks: bubble-chamber photograph - beaded tracks of charged particles curling into tight inward spirals as they lose energy, straight energetic tracks, V decays and electron-positron pairs, with tiny delta-ray curls, white and amber on midnight blue
    n = N
    r = H.rng(seed)
    T, ds = 420, 2.4
    P = {k: [] for k in ("x", "y", "th", "rho", "tau", "sg", "len", "val", "kind")}

    def add(x, y, th, rho, tau, sg, ln, val, kind):
        P["x"].append(x); P["y"].append(y); P["th"].append(th); P["rho"].append(rho); P["tau"].append(tau)
        P["sg"].append(sg); P["len"].append(ln); P["val"].append(val); P["kind"].append(kind)

    for _ in range(95):                                   # inward spirals
        add(r.uniform(0, n), r.uniform(0, n), r.uniform(0, 6.28), r.uniform(46, 230), r.uniform(190, 520),
            r.choice([-1.0, 1.0]), r.uniform(500, 1000), r.uniform(0.55, 1.0), 0)
    for _ in range(80):                                   # energetic, nearly straight
        add(r.uniform(-100, n + 100), r.uniform(-100, n + 100), r.uniform(0, 6.28), r.uniform(700, 4500), 1e5,
            r.choice([-1.0, 1.0]), r.uniform(450, 1000), r.uniform(0.7, 1.0), 1)
    for _ in range(46):                                   # V decays: two opposite arms from one vertex
        x, y, th = r.uniform(0, n), r.uniform(0, n), r.uniform(0, 6.28)
        sp = r.uniform(0.35, 1.1)
        rho = r.uniform(140, 480)
        ln = r.uniform(350, 800)
        add(x, y, th + sp, rho, 2200.0, 1.0, ln, 0.9, 2)
        add(x, y, th - sp, rho * r.uniform(0.7, 1.3), 2200.0, -1.0, ln * r.uniform(0.7, 1.1), 0.9, 2)
    for _ in range(48):                                   # e+ e- pairs: tight opposite spirals
        x, y, th = r.uniform(0, n), r.uniform(0, n), r.uniform(0, 6.28)
        rho = r.uniform(34, 90)
        tau = r.uniform(110, 260)
        add(x, y, th + 0.12, rho, tau, 1.0, r.uniform(300, 700), 0.95, 3)
        add(x, y, th - 0.12, rho * r.uniform(0.8, 1.2), tau, -1.0, r.uniform(300, 700), 0.95, 3)
    nmain = len(P["x"])
    arr = {k: np.array(v, np.float64) for k, v in P.items()}

    def trace(a):
        s = np.arange(T, dtype=np.float64) * ds
        rho_s = a["rho"][:, None] * np.exp(-s[None, :] / a["tau"][:, None])
        k = a["sg"][:, None] / np.maximum(rho_s, 1.0)
        th = a["th"][:, None] + np.cumsum(k * ds, axis=1)
        x = a["x"][:, None] + np.cumsum(np.cos(th) * ds, axis=1)
        y = a["y"][:, None] + np.cumsum(np.sin(th) * ds, axis=1)
        valid = (s[None, :] < a["len"][:, None]) & (rho_s > 4.0)
        return x, y, th, valid

    x, y, th, valid = trace(arr)
    # delta-ray curls branching off random points of the main tracks
    nd = 190
    ti_ = r.integers(0, nmain, nd)
    nv = valid.sum(1)
    tj = (r.random(nd) * np.maximum(nv[ti_] - 10, 1)).astype(np.int64) + 5
    dX = x[ti_, tj]
    dY = y[ti_, tj]
    dTh = th[ti_, tj] + r.choice([-1.0, 1.0], nd) * r.uniform(1.0, 2.0, nd)
    da = dict(x=dX, y=dY, th=dTh, rho=r.uniform(9, 24, nd), tau=r.uniform(30, 80, nd), sg=r.choice([-1.0, 1.0], nd),
              len=r.uniform(70, 190, nd), val=r.uniform(0.45, 0.8, nd), kind=np.full(nd, 4.0))
    dxx, dyy, dth, dval = trace(da)
    # the valid mask for the main tracks must also require the branch point to exist
    chans = [np.zeros((n, n), F32) for _ in range(3)]
    cols = {0: (1.0, 0.70, 0.28), 1: (0.86, 0.94, 1.0), 2: (1.0, 0.86, 0.55), 3: (1.0, 0.80, 0.42), 4: (1.0, 0.64, 0.24)}

    def paint(xx, yy, vv, aa):
        kinds = aa["kind"].astype(int)
        keep = r.random(vv.shape) < 0.90
        for kd in range(5):
            sel = (kinds == kd)[:, None] & vv & keep
            if not sel.any():
                continue
            px = xx[sel]
            py = yy[sel]
            rowi = np.broadcast_to(np.arange(len(kinds))[:, None], vv.shape)[sel]
            val = (aa["val"][rowi] * r.uniform(0.7, 1.0, px.shape[0])).astype(F32)
            ok = (px >= 1) & (px < n - 2) & (py >= 1) & (py < n - 2)
            px, py, val = px[ok], py[ok], val[ok]
            for c in range(3):
                for ox, oy in ((0, 0), (1, 0), (0, 1)):
                    H.points(chans[c], np.round(px + ox).astype(np.int64), np.round(py + oy).astype(np.int64), val * cols[kd][c] * (1.0 if ox + oy == 0 else 0.55))

    paint(x, y, valid, arr)
    paint(dxx, dyy, dval, da)
    tr = np.stack([H.blur(c, 0.8) for c in chans], -1)
    tr = np.clip(tr * 1.9, 0, 1.2)
    gz = _gz(n, seed + 2)
    rgb = np.array([0.046, 0.070, 0.200], F32)[None, None, :] * gz[..., None]
    rgb += _specks(n, seed + 3, 0.004, 0.08, 0.4)[..., None] * np.array([0.7, 0.85, 1.0], F32)
    rgb += tr
    rgb += (H.blur(np.max(tr, axis=2), 3.5) * 0.3)[..., None] * np.array([0.5, 0.45, 0.4], F32)
    rgb = np.clip(rgb, 0, 1)
    tmax = np.clip(np.max(tr, axis=2), 0, 1)
    lt = np.clip((H.lum(rgb) - 0.05) / 0.7, 0, 1)
    gr = _snoise(1100, 1100, seed + 6)
    M = H.lerp(0.0, 245.0, np.clip(tmax * 1.2, 0, 1))
    R_ = H.lerp(244.0, 10.0, np.clip(tmax * 1.3, 0, 1) ** 0.7) + 8.0 * gr * (1 - tmax)
    CC = H.lerp(255.0, 16.0, H.sstep(0.0, 0.45, tmax))
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
FINISHES = [
    ("cz_einstein_arcs", "Einstein Ring Arcs",
     "Tiny galaxies wrapped in broken cyan lensed arcs and rings on a deep navy mirror field.", einstein_arcs),
    ("cz_photon_rings", "Black Hole Photon Rings",
     "Tilted jet-black holes ringed in thin gold light with lopsided orange accretion haze.", photon_rings),
    ("cz_spacetime_grid", "Spacetime Warp Grid",
     "Fine cyan graph paper pinched into funnels toward gravity wells, glowing where compressed.", spacetime_grid),
    ("cz_gravitational_chirp", "Gravitational Wave Chirp",
     "Two-armed spiral waves tightening toward their sources, interfering into violet and navy bands edged with fine light lines.", gravitational_chirp),
    ("cz_quasar_beams", "Quasar Jet Beams",
     "Hair-thin white jets beaded with knots, long straight beams ending in puffy magenta lobes over deep indigo space.", quasar_beams),
    ("cz_dark_caustics", "Dark Matter Caustics",
     "A sharp web of bright violet-white caustic lines like sunlight on a pool floor.", dark_caustics),
    ("cz_wormhole_tunnels", "Wormhole Tunnels",
     "Cyan concentric-ring funnels crowding and darkening toward an offset black throat, with a faint starfield lensed around each.", wormhole_tunnels),
    ("cz_cosmic_strings", "Cosmic Strings",
     "Thin kinked white strings and wobbling loops across a dense blue starfield, doubling every star beside them.", cosmic_strings),
    ("cz_quantum_foam", "Quantum Foam",
     "Dense nested bubbles from 100 px to 3 px with flickering violet-white walls.", quantum_foam),
    ("cz_cosmic_ray_tracks", "Cosmic Ray Tracks",
     "Bubble-chamber tracks: beaded spirals, straight lines, V decays and pairs, white and amber on midnight blue.", cosmic_ray_tracks),
]
