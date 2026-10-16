# -*- coding: utf-8 -*-
"""CRAFT & SIGNALS chapter (cz_ 51-60): hulls, scripts, crop circles, records, sails, tiles, spectrograms, swarms.

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


def _gz(n, seed, amp=0.28):
    """Ground brightness modulation clipped to >= 0.58 plus 1 px grain against 8-bit banding."""
    g = np.clip(0.95 + amp * H.fbm(n, seed, cells=(2, 4, 8, 16), gain=0.6), 0.58, 1.5)
    g *= 1.0 + 0.05 * H.rng(seed + 977).standard_normal((n, n)).astype(F32)
    return g.astype(F32)


def _specks(n, seed, density, lo=0.10, hi=0.75, power=3.0):
    r = H.rng(seed)
    cnt = int(n * n * density)
    xs = r.integers(0, n, cnt)
    ys = r.integers(0, n, cnt)
    v = (lo + (hi - lo) * r.random(cnt) ** power).astype(F32)
    cvs = np.zeros((n, n), F32)
    H.points(cvs, xs, ys, v)
    return cvs


def _lic2(tex, uv, length, h):
    m = tex.shape[0]
    X, Y = H.xy(m)
    acc = tex.copy()
    for sg in (1.0, -1.0):
        px = np.array(X, F32)
        py = np.array(Y, F32)
        for _ in range(length):
            d = cv2.remap(uv, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            px += F32(sg * h) * d[..., 0]
            py += F32(sg * h) * d[..., 1]
            acc += cv2.remap(tex, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    acc /= F32(2 * length + 1)
    return acc


def _z(a):
    return ((a - a.mean()) / (a.std() + 1e-6)).astype(F32)


# -------------------------------------------------------------------------
# 51. Mothership Plating
# -------------------------------------------------------------------------
def mothership_plating(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 51 Mothership Plating: a hull of staggered armour plates fanning out in polar rings around ~50 saucer hubs - dark seams with a bright lip, rivet rows, one blue or gold heat tint per hub fading with distance, domed hubs with window lights; gunmetal titanium whose brushed grain turns with each plate (visual pass: tint per plate was confetti -> one tint per hub; speed: rivets/tint/dome only on subsets)
    n = N
    r = H.rng(seed)
    pts = H.jitter_pts(n, 245.0, seed + 1, jit=0.85, margin=120)
    d, lab, hx, hy = H.voronoi(n, pts)
    K = len(hx)
    li = (lab - 1).astype(np.int64)
    nsec = r.integers(11, 27, K).astype(F32)
    q = r.uniform(1.30, 1.55, K).astype(F32)
    lnq = np.log(q).astype(F32)
    r0 = r.uniform(15.0, 25.0, K).astype(F32)
    roff = r.random(K * 48).astype(F32)
    hub_gold = r.random(K) < 0.5
    hub_int = r.uniform(0.35, 1.0, K).astype(F32)
    X, Y = H.xy(n)
    dx = X - hx.astype(F32)[li]
    dy = Y - hy.astype(F32)[li]
    rho = np.hypot(dx, dy) + F32(1e-3)
    th = np.arctan2(dy, dx)
    lnqp = lnq[li]
    r0p = r0[li]
    lr = np.log(np.maximum(rho / r0p, F32(1e-3))) / lnqp
    fl = np.floor(lr)
    ring = np.clip(fl, 0, 47).astype(np.int64)
    frr = (lr - fl).astype(F32)
    nsp = nsec[li]
    f = (th + F32(np.pi)) / F32(2 * np.pi) * nsp + roff[li * 48 + ring]
    fs = np.floor(f)
    fr = (f - fs).astype(F32)
    d_ring = np.minimum(frr, 1.0 - frr) * rho * lnqp
    d_sec = np.minimum(fr, 1.0 - fr) * rho * F32(2 * np.pi) / nsp
    seam = np.minimum(np.minimum(d_ring, d_sec), H.edge_dist(lab))
    pk = li * 1000003 + ring * 7919 + fs.astype(np.int64) * 104729
    pid = H.hash01(pk, seed)
    pid2 = (pid * 7.31 + 0.37) % 1.0
    pid3 = (pid * 13.7 + 0.61) % 1.0
    lum = 0.15 + 0.40 * pid
    lum = lum * (1.0 + 0.16 * (fr - 0.5) + 0.12 * (0.5 - frr))
    b0 = _snoise(1800, 44, seed + 5)
    b1 = _snoise(44, 1800, seed + 6)
    brush = np.where(pid3 > 0.5, b0, b1)
    lum = lum * (1.0 + 0.09 * brush + 0.05 * H.rng(seed + 7).standard_normal((n, n)).astype(F32))
    groove = H.sstep(2.0, 0.9, seam)
    lip = H.sstep(0.9, 1.8, seam) * H.sstep(4.0, 2.2, seam)
    lum = lum * (1.0 - 0.86 * groove) * (1.0 + 0.55 * lip)
    cool = np.array([0.78, 0.84, 0.96], F32)
    col = lum[..., None] * cool
    # rivets: only near the ring seams
    ir = np.flatnonzero(d_ring < 9.0)
    rho_r = rho.ravel()[ir]
    nsp_r = nsp.ravel()[ir]
    rc = r0p.ravel()[ir] * np.exp(lnqp.ravel()[ir] * (ring.ravel()[ir].astype(F32) + F32(0.5)))
    nriv = np.maximum(2.0, np.round(rc * F32(2 * np.pi) / nsp_r / 11.0))
    ph = fr.ravel()[ir] * nriv
    rvx = (ph - np.floor(ph) - 0.5) * (rho_r * F32(2 * np.pi) / nsp_r / nriv)
    rvy = d_ring.ravel()[ir] - 5.4
    rr2 = rvx * rvx + rvy * rvy
    dot_r = np.exp(-rr2 / (2 * 1.25 ** 2))
    rim_r = np.exp(-((np.sqrt(rr2) - 2.6) / 0.9) ** 2)
    cf = col.reshape(-1, 3)
    cf[ir] = cf[ir] * (1.0 - 0.55 * rim_r)[:, None] + (0.85 * dot_r)[:, None] * np.array([0.95, 0.97, 1.0], F32)
    dot = np.zeros(n * n, F32)
    dot[ir] = dot_r
    dot = dot.reshape(n, n)
    # heat tint: one hue per hub, strongest at the seams and near the hub
    it = np.flatnonzero(seam < 20.0)
    hub_p = li.ravel()[it]
    hot = np.exp(-seam.ravel()[it] / 4.8) * hub_int[hub_p] * (0.25 + 0.75 * pid2.ravel()[it]) * (0.30 + 1.5 * np.exp(-rho.ravel()[it] / 110.0))
    hot = np.clip(hot, 0, 0.92)
    tintc = np.where(hub_gold[hub_p][:, None], np.array([1.0, 0.66, 0.20], F32), np.array([0.25, 0.48, 1.0], F32))
    cf[it] = cf[it] * (1.0 - 0.80 * hot)[:, None] + (0.95 * hot * (0.4 + 0.6 * lum.ravel()[it]))[:, None] * tintc
    col = cf.reshape(n, n, 3)
    # saucer dome and window lights, only near each hub
    ih = np.flatnonzero(rho < r0p * 2.4)
    rho_h = rho.ravel()[ih]
    r0_h = r0p.ravel()[ih]
    th_h = th.ravel()[ih]
    ns_h = nsp.ravel()[ih]
    rings_ = 0.5 + 0.5 * np.cos(rho_h * F32(2 * np.pi / 4.2))
    dl = 0.38 + 0.30 * rings_ + 0.9 * np.exp(-(rho_h / 5.0) ** 2)
    dedge = H.sstep(r0_h * 0.80, r0_h * 1.05, rho_h)
    dcol = (dl * (1.0 - 0.7 * dedge))[:, None] * np.array([0.84, 0.92, 1.0], F32)
    dome_h = rho_h < r0_h * 1.05
    win_h = np.exp(-((rho_h - 2.15 * r0_h) / 1.15) ** 2) * (np.sin(th_h * ns_h * 2.0 + 0.7) > 0.75)
    cf = col.reshape(-1, 3)
    cf[ih] = np.where(dome_h[:, None], dcol, cf[ih]) + (win_h * 0.95)[:, None] * np.array([0.55, 0.95, 1.0], F32)
    dome = np.zeros(n * n, bool)
    dome[ih] = dome_h
    dome = dome.reshape(n, n)
    win = np.zeros(n * n, F32)
    win[ih] = win_h
    win = win.reshape(n, n)
    rgb = np.clip(cf.reshape(n, n, 3), 0, 1)
    lt = np.clip(H.lum(rgb) / 0.70, 0, 1)
    M = H.lerp(176.0, 248.0, lt)
    R_ = H.lerp(165.0, 42.0, lt) + 7.0 * brush
    CC = H.lerp(48.0, 16.0, lt)
    hard = dome | (dot > 0.45) | (win > 0.4)
    M = np.where(hard, 255.0, M)
    R_ = np.where(dome | (dot > 0.45), 12.0, R_)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 52. Xenoglyph Script
# -------------------------------------------------------------------------
def xenoglyph_script(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 52 Xenoglyph Script: ~4000 invented alien glyphs (grammar: 3-6 curved or angled strokes joined on a 4x6 port lattice, a diacritic dot, mirrored and tilted) etched in wavy rows of words, rows turning 0, 90 and 27 degrees in three regions; dark etch in bright cool alloy with a bevel lip; chrome ground, matte etch
    n = N
    r = H.rng(seed)
    # three text regions from a coarse voronoi
    rp = H.jitter_pts(n, 760.0, seed + 1, jit=0.9, margin=300)
    _, rlab, _, _ = H.voronoi(n, rp)
    rlab = (rlab - 1) % 3
    gxs, gys, gas = [], [], []
    for li_, ang in enumerate((0.0, np.pi / 2, 0.47)):
        pitch = 44.0
        R_ = int(n * 1.5 / pitch) + 2
        C_ = 150
        wdt = r.uniform(19.0, 27.0, (R_, C_)).astype(F32)
        wlen = r.integers(3, 9, (R_, C_))
        cnt = np.cumsum(np.ones((R_, C_), np.int64), 1)
        gap = np.where((cnt % 6) == (wlen % 6), 18.0, 0.0).astype(F32)
        xs = np.cumsum(wdt + gap, 1) - 400.0 + r.uniform(0, 40, (R_, 1)).astype(F32)
        ys = (np.arange(R_, dtype=F32)[:, None] * pitch - 450.0 + 22.0) + 7.0 * np.sin(xs / 210.0 + r.uniform(0, 6.28, (R_, 1)).astype(F32)) + r.uniform(-2.0, 2.0, (R_, C_)).astype(F32)
        xs = xs + r.uniform(-1.5, 1.5, (R_, C_)).astype(F32)
        ca, sa = np.cos(ang), np.sin(ang)
        cxc, cyc = n / 2.0, n / 2.0
        gx = cxc + (xs - cxc) * ca - (ys - cyc) * sa
        gy = cyc + (xs - cxc) * sa + (ys - cyc) * ca
        gx, gy = gx.ravel(), gy.ravel()
        ok = (gx > -30) & (gx < n + 30) & (gy > -30) & (gy < n + 30) & (r.random(gx.shape) < 0.93)
        gx, gy = gx[ok], gy[ok]
        ix = np.clip(gx.astype(np.int64), 0, n - 1)
        iy = np.clip(gy.astype(np.int64), 0, n - 1)
        sel = rlab[iy, ix] == li_
        gxs.append(gx[sel])
        gys.append(gy[sel])
        gas.append(np.full(int(sel.sum()), ang, F32))
    gx = np.concatenate(gxs)
    gy = np.concatenate(gys)
    ga = np.concatenate(gas)
    G = len(gx)
    S = 6
    lw, lh = 16.0, 28.0
    ax_ = r.integers(0, 4, (G, S)).astype(F32) / 3.0 - 0.5
    ay_ = r.integers(0, 6, (G, S)).astype(F32) / 5.0 - 0.5
    bx_ = r.integers(0, 4, (G, S)).astype(F32) / 3.0 - 0.5
    by_ = r.integers(0, 6, (G, S)).astype(F32) / 5.0 - 0.5
    kind = r.random((G, S))
    # control point: straight, corner (arc-ish L) or free bend
    cxk = np.where(kind < 0.45, (ax_ + bx_) / 2, np.where(kind < 0.78, bx_, (ax_ + bx_) / 2 + r.uniform(-0.45, 0.45, (G, S))))
    cyk = np.where(kind < 0.45, (ay_ + by_) / 2, np.where(kind < 0.78, ay_, (ay_ + by_) / 2 + r.uniform(-0.45, 0.45, (G, S))))
    nst = r.integers(3, 7, G)
    use = np.arange(S)[None, :] < nst[:, None]
    ts = np.linspace(0, 1, 7, dtype=F32)
    # (G,S,7) quadratic Bezier in glyph-local units
    px = ((1 - ts) ** 2)[None, None] * ax_[..., None] + (2 * (1 - ts) * ts)[None, None] * cxk[..., None] + (ts ** 2)[None, None] * bx_[..., None]
    py = ((1 - ts) ** 2)[None, None] * ay_[..., None] + (2 * (1 - ts) * ts)[None, None] * cyk[..., None] + (ts ** 2)[None, None] * by_[..., None]
    scl = r.uniform(0.78, 1.15, G).astype(F32)
    mir = np.where(r.random(G) < 0.5, -1.0, 1.0).astype(F32)
    tilt = r.uniform(-0.22, 0.22, G).astype(F32) + ga
    ct, st_ = np.cos(tilt), np.sin(tilt)
    lx = px * lw * (scl * mir)[:, None, None]
    ly = py * lh * scl[:, None, None]
    wx = gx[:, None, None] + lx * ct[:, None, None] - ly * st_[:, None, None]
    wy = gy[:, None, None] + lx * st_[:, None, None] + ly * ct[:, None, None]
    # a diacritic dot above some glyphs: a tiny stroke
    dotm = r.random(G) < 0.55
    dxp = gx + (-lh * 0.78 * scl) * (-st_) + r.uniform(-3, 3, G)
    dyp = gy + (-lh * 0.78 * scl) * ct + r.uniform(-1, 1, G)
    sc = 16.0
    P = np.stack([wx, wy], -1)[use]                       # (M,7,2)
    pp = np.round(P * sc).astype(np.int32).reshape(-1, 7, 1, 2)
    canvas = np.zeros((n, n), np.uint8)
    cv2.polylines(canvas, list(pp), False, 255, 2, cv2.LINE_AA, 4)
    dd = np.stack([np.stack([dxp, dyp], -1), np.stack([dxp + 1.6, dyp + 0.5], -1)], 1)[dotm]
    dd = np.round(dd * sc).astype(np.int32).reshape(-1, 2, 1, 2)
    cv2.polylines(canvas, list(dd), False, 255, 3, cv2.LINE_AA, 4)
    E = canvas.astype(F32) / 255.0
    # alloy ground: bright, brushed, cool-to-bronze drift
    hue = np.clip(0.5 + 0.8 * H.fbm(n, seed + 2, cells=(2, 3, 5), gain=0.6), 0, 1)
    gl = 0.64 + 0.10 * H.fbm(n, seed + 3, cells=(3, 6, 12, 24), gain=0.6) + 0.045 * _snoise(70, 1500, seed + 4) + 0.03 * H.rng(seed + 5).standard_normal((n, n)).astype(F32)
    cool = np.array([0.72, 0.80, 0.90], F32)
    warm = np.array([0.88, 0.78, 0.62], F32)
    ground = gl[..., None] * (cool[None, None] * (1 - hue)[..., None] + warm[None, None] * hue[..., None])
    sh = np.roll(np.roll(E, 1, 0), 1, 1)
    lipm = np.clip(sh - E, 0, 1)
    ec = np.array([0.02, 0.06, 0.08], F32)[None, None] * (1 - hue)[..., None] + np.array([0.09, 0.04, 0.02], F32)[None, None] * hue[..., None]
    rgb = ground * (1 - 0.93 * E)[..., None] + ec * E[..., None]
    rgb += (0.40 * lipm)[..., None] * np.array([1.0, 1.0, 1.0], F32)
    rgb = np.clip(rgb, 0, 1)
    # [S19 coordinator polish A 2026-10-12] spec richness: the spec now carries the paint's structure (matte/rough ground with 1 px flake; lines, arcs, cores = satin then mirror metal)
    Es = H.blur(E, 0.8)
    band = np.clip(H.blur(E, 3.4) * 3.4, 0, 1)
    hz = H.sstep(0.35, 0.65, hue)
    fk = H.rng(seed + 92).standard_normal((n, n)).astype(F32)
    M = H.lerp(H.lerp(248.0, 190.0, hz), 150.0, band) + 5.0 * fk
    M = H.lerp(M, 14.0, Es)
    R_ = H.lerp(H.lerp(14.0, 62.0, hz), 100.0, band) + 8.0 * fk * (1 - Es) + 10.0 * _snoise(70, 1500, seed + 4) * (1 - Es)
    R_ = H.lerp(R_, 205.0, Es)
    CC = H.lerp(H.lerp(16.0, 60.0, hz), 120.0, band)
    CC = H.lerp(CC, 210.0, Es)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 53. Crop Formation Field
# -------------------------------------------------------------------------
def _crop_tile(kind, Rr, sd):
    S = 2 * Rr + 1
    y, x = np.mgrid[0:S, 0:S].astype(F32)
    x -= Rr
    y -= Rr
    rho = np.hypot(x, y) / Rr
    phi = np.arctan2(y, x)
    m = np.zeros((S, S), F32)
    cs = np.zeros((S, S, 2), F32)

    def put(mask, ang):
        nonlocal m, cs
        mm = mask.astype(F32)
        m = np.maximum(m, mm)
        vv = np.stack([np.cos(2 * ang), np.sin(2 * ang)], -1).astype(F32)
        cs = np.where(mask[..., None], vv, cs)

    rad = phi
    tan = phi + np.pi / 2
    if kind == 0:                                   # bullseye
        put(rho < 0.26, rad)
        put((rho > 0.40) & (rho < 0.60), tan)
        put((rho > 0.72) & (rho < 0.94), rad)
    elif kind == 1:                                 # ring of dots round a hub
        r_ = H.rng(sd)
        nd = int(r_.integers(6, 10))
        put(rho < 0.20, tan)
        for k in range(nd):
            a = 2 * np.pi * k / nd
            cx, cy = 0.64 * np.cos(a), 0.64 * np.sin(a)
            dd = np.hypot(x / Rr - cx, y / Rr - cy)
            put(dd < 0.17, np.arctan2(y / Rr - cy, x / Rr - cx))
        put((rho > 0.93) & (rho < 1.0), tan)
    elif kind == 2:                                 # spiral arms
        r_ = H.rng(sd)
        arms = int(r_.integers(2, 5))
        psi = (rho * 2.6 - phi / (2 * np.pi) * arms) % 1.0
        put((psi < 0.46) & (rho > 0.10) & (rho < 0.98), phi + np.pi / 2 + 0.9)
    elif kind == 3:                                 # pinwheel of wedges
        r_ = H.rng(sd)
        nw = int(2 * r_.integers(3, 6))
        wid = ((phi + np.pi) / (2 * np.pi) * nw)
        wi = np.floor(wid).astype(np.int64)
        fr = wid - np.floor(wid)
        inside = (rho > 0.18) & (rho < 0.97) & (fr > 0.12) & (fr < 0.88)
        put(inside & (wi % 2 == 0), rad)
        put(inside & (wi % 2 == 1), tan)
    else:                                           # combed bars
        r_ = H.rng(sd)
        nb = int(r_.integers(3, 6))
        for k in range(nb):
            yc = (k - (nb - 1) / 2.0) * 0.40
            bar = (np.abs(y / Rr - yc) < 0.14) & (np.abs(x / Rr) < 0.94 - 0.10 * abs(k - (nb - 1) / 2.0))
            put(bar, np.where(k % 2 == 0, 0.0, np.pi / 2) + np.zeros_like(phi))
    m = cv2.GaussianBlur(m, (0, 0), 0.8)
    return np.dstack([m, cs[..., 0], cs[..., 1]]).astype(F32)


def crop_formation(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 53 Crop Formation Field: a wheat field of combed straw-gold grain (line-integral convolution) in which ~110 flattened pictograms - bullseyes, dot rings, spirals, pinwheels, comb bars - lay the grain down in new directions so each catches the light differently; brushed metal that follows the grain
    n = N
    r = H.rng(seed)
    th0 = 0.62 + 1.3 * H.fbm(n, seed + 1, cells=(2, 3, 5, 9), gain=0.55)
    c2 = np.cos(2 * th0).astype(F32)
    s2 = np.sin(2 * th0).astype(F32)
    mk = np.zeros((n, n), F32)
    sizes = (34, 54, 80)
    tiles = []
    for kind in range(5):
        for Rr in sizes:
            base = _crop_tile(kind, Rr, seed * 7 + kind * 13 + Rr)
            tiles.append((base, kind, Rr))
    NR = 12
    rots = []
    for base, kind, Rr in tiles:
        rots.append(H.rotset(base, NR, np.pi))
    pts = H.jitter_pts(n, 164.0, seed + 2, jit=0.85, margin=60)
    pts = pts[r.random(len(pts)) < 0.78]
    K = len(pts)
    kinds = r.integers(0, 5, K)
    szi = r.choice(3, K, p=[0.38, 0.40, 0.22])
    rot = r.integers(0, NR, K)
    flp = r.integers(0, 4, K)
    for k in range(K):
        t = rots[kinds[k] * 3 + szi[k]][rot[k]]
        phi = np.pi * rot[k] / NR
        cr, sr = np.cos(2 * phi), np.sin(2 * phi)
        mm = t[..., 0]
        vc = t[..., 1] * cr - t[..., 2] * sr
        vs = t[..., 1] * sr + t[..., 2] * cr
        fl = int(flp[k])
        if fl & 1:
            mm, vc, vs = mm[:, ::-1], vc[:, ::-1], -vs[:, ::-1]
        if fl & 2:
            mm, vc, vs = mm[::-1], vc[::-1], -vs[::-1]
        S_ = mm.shape[0]
        x0 = int(pts[k, 0]) - S_ // 2
        y0 = int(pts[k, 1]) - S_ // 2
        sx0, sy0 = max(0, -x0), max(0, -y0)
        ex, ey = min(S_, n - x0), min(S_, n - y0)
        if ex <= sx0 or ey <= sy0:
            continue
        sl = (slice(y0 + sy0, y0 + ey), slice(x0 + sx0, x0 + ex))
        w = mm[sy0:ey, sx0:ex]
        c2[sl] = c2[sl] * (1 - w) + vc[sy0:ey, sx0:ex] * w
        s2[sl] = s2[sl] * (1 - w) + vs[sy0:ey, sx0:ex] * w
        mk[sl] = np.maximum(mk[sl], w)
    ang = 0.5 * np.arctan2(s2, c2)
    # light: flattened crops at different angles reflect differently
    lit = 0.5 + 0.5 * (c2 * np.cos(2 * 0.62) + s2 * np.sin(2 * 0.62))
    m1 = 1024
    uv = np.dstack([cv2.resize(np.cos(ang), (m1, m1), interpolation=cv2.INTER_AREA), cv2.resize(np.sin(ang), (m1, m1), interpolation=cv2.INTER_AREA)]).astype(F32)
    uvn = uv / (np.sqrt((uv ** 2).sum(-1, keepdims=True)) + 1e-6)
    t1 = r.standard_normal((m1, m1)).astype(F32)
    z1 = _z(_lic2(t1, uvn, 5, 1.2))
    z1 = cv2.resize(z1, (n, n), interpolation=cv2.INTER_CUBIC)
    t2 = r.standard_normal((m1, m1)).astype(F32)
    z2 = cv2.resize(_z(_lic2(t2, uvn, 3, 1.0)), (n, n), interpolation=cv2.INTER_CUBIC)
    micro = H.rng(seed + 9).standard_normal((n, n)).astype(F32)
    wall = np.clip(np.abs(mk - H.blur(mk, 1.8)) * 3.0, 0, 1)
    tt = 0.10 + 0.70 * lit + 0.10 * z1 + 0.06 * z2 + 0.035 * micro
    tt = np.clip(tt * (1.0 - 0.55 * wall), 0, 1)
    ripe = H.ramp(tt, [(0.0, '#241406'), (0.30, '#74501a'), (0.62, '#c99a3c'), (0.85, '#f3d57e'), (1.0, '#fff2c0')])
    green = H.ramp(tt, [(0.0, '#14200a'), (0.30, '#4a5c1a'), (0.62, '#97a438'), (0.85, '#d6d870'), (1.0, '#f5f2b8')])
    gm = np.clip(0.30 + 0.45 * H.fbm(n, seed + 3, cells=(2, 3, 5), gain=0.6), 0, 0.8)
    rgb = ripe * (1 - gm)[..., None] + green * gm[..., None]
    rgb = np.clip(rgb, 0, 1)
    tn = np.clip(H.lum(rgb) / 0.8, 0, 1)
    M = H.lerp(150.0, 220.0, tn)
    R_ = H.lerp(138.0, 60.0, tn) + 13.0 * z2
    CC = H.lerp(54.0, 18.0, tn)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 54. Golden Record Etching
# -------------------------------------------------------------------------
def _rec_tile(kind, T, sd):
    r = H.rng(sd)
    img = np.zeros((T, T), np.uint8)
    sc = 16.0
    c = T / 2.0

    def P(x, y):
        return (int(round(x * sc)), int(round(y * sc)))

    def line(a, b, th=1):
        cv2.line(img, P(*a), P(*b), 255, th, cv2.LINE_AA, 4)

    def circ(cx, cy, rad, th=1):
        cv2.circle(img, P(cx, cy), max(1, int(round(rad * sc))), 255, th, cv2.LINE_AA, 4)

    def poly(xs, ys, th=1):
        pp = np.round(np.stack([xs, ys], 1) * sc).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [pp], False, 255, th, cv2.LINE_AA, 4)

    k = T / 150.0
    if kind == 0:                                  # pulsar map: burst of tick-marked lines
        circ(c, c, 3.2 * k, -1)
        for i in range(int(r.integers(12, 17))):
            a = r.uniform(0, 2 * np.pi)
            L = r.uniform(0.22, 0.46) * T
            ca, sa = np.cos(a), np.sin(a)
            line((c + ca * 5 * k, c + sa * 5 * k), (c + ca * L, c + sa * L), 1)
            for j in range(int(r.integers(3, 7))):
                t = r.uniform(0.2, 1.0) * L
                tl = (4.0 if j else 7.0) * k
                line((c + ca * t - sa * tl, c + sa * t + ca * tl), (c + ca * t + sa * tl, c + sa * t - ca * tl), 1)
    elif kind == 1:                                # binary tick rows
        rows = int(r.integers(3, 6))
        for j in range(rows):
            y = c + (j - (rows - 1) / 2.0) * 0.20 * T
            nb = int(r.integers(12, 19))
            sp = 0.8 * T / nb
            x0 = c - 0.4 * T
            line((x0 - 2, y + 7 * k), (x0 + nb * sp, y + 7 * k), 1)
            for b in range(nb):
                hh = (13.0 if r.random() < 0.5 else 5.0) * k
                line((x0 + b * sp + 1, y + 7 * k), (x0 + b * sp + 1, y + 7 * k - hh), 1)
    elif kind == 2:                                # concentric circles with dots and a crossing line
        for rr in (0.17, 0.31, 0.45):
            circ(c, c, rr * T, 1)
        for rr in (0.17, 0.31, 0.45):
            for i in range(int(r.integers(3, 8))):
                a = r.uniform(0, 2 * np.pi)
                circ(c + np.cos(a) * rr * T, c + np.sin(a) * rr * T, r.uniform(1.6, 3.4) * k, -1)
        a0 = r.uniform(0, np.pi)
        line((c - np.cos(a0) * 0.5 * T, c - np.sin(a0) * 0.5 * T), (c + np.cos(a0) * 0.5 * T, c + np.sin(a0) * 0.5 * T), 1)
        for i in range(24):
            a = i * np.pi / 12
            line((c + np.cos(a) * 0.45 * T, c + np.sin(a) * 0.45 * T), (c + np.cos(a) * 0.49 * T, c + np.sin(a) * 0.49 * T), 1)
    elif kind == 3:                                # waveform trace with axis
        xs = np.linspace(0.06 * T, 0.94 * T, 220)
        f1, f2 = r.uniform(3.0, 7.0), r.uniform(9.0, 18.0)
        env = np.exp(-((xs / T - r.uniform(0.3, 0.7)) / r.uniform(0.12, 0.3)) ** 2)
        ys = c + 0.30 * T * env * (0.65 * np.sin(2 * np.pi * f1 * xs / T) + 0.35 * np.sin(2 * np.pi * f2 * xs / T + 1.1)) * 0.9
        poly(xs, ys, 2)
        line((0.04 * T, c), (0.96 * T, c), 1)
        for i in range(0, 13):
            x = 0.06 * T + i * 0.88 * T / 12
            line((x, c - 3 * k), (x, c + 3 * k), 1)
    elif kind == 4:                                # two-circle transition diagram
        cx1, cx2 = 0.25 * T, 0.75 * T
        circ(cx1, c, 0.15 * T, 1)
        circ(cx2, c, 0.15 * T, 1)
        circ(cx1, c, 2.4 * k, -1)
        circ(cx2, c, 2.4 * k, -1)
        line((cx1 + 0.15 * T, c), (cx2 - 0.15 * T, c), 1)
        for i in range(5):
            x = cx1 + 0.15 * T + (i + 0.5) * (cx2 - cx1 - 0.3 * T) / 5
            line((x, c - 5 * k), (x, c + 5 * k), 1)
        line((c - 0.1 * T, c - 0.30 * T), (c + 0.1 * T, c - 0.30 * T), 1)
        line((c, c - 0.34 * T), (c, c - 0.26 * T), 1)
    elif kind == 5:                                # solar system row of dots
        line((0.05 * T, c), (0.95 * T, c), 1)
        x = 0.08 * T
        for i in range(9):
            circ(x, c, (1.6 + 0.45 * i * (1 if i < 5 else 0.7)) * k, -1)
            line((x, c + 8 * k), (x, c + (14 + (i % 3) * 4) * k), 1)
            x += (0.05 + 0.011 * i * i / 4 + r.uniform(0, 0.01)) * T
        for b in range(int(r.integers(10, 16))):
            xx = 0.1 * T + b * 5.5 * k
            line((xx, c - 8 * k), (xx, c - (8 + (14 if r.random() < 0.5 else 6)) * k), 1)
    elif kind == 6:                                # log-spiral with beads
        th_ = np.linspace(0, 4.2 * np.pi, 260)
        rad = 0.02 * T * np.exp(0.19 * th_)
        poly(c + rad * np.cos(th_), c + rad * np.sin(th_), 1)
        for t in np.linspace(0.5 * np.pi, 4.2 * np.pi, int(r.integers(10, 17))):
            rr = 0.02 * T * np.exp(0.19 * t)
            circ(c + rr * np.cos(t), c + rr * np.sin(t), 2.0 * k, -1)
    elif kind == 7:                                # gauge dial
        circ(c, c, 0.42 * T, 1)
        circ(c, c, 0.30 * T, 1)
        for i in range(48):
            a = i * np.pi / 24
            ll = 0.07 if i % 4 == 0 else 0.035
            line((c + np.cos(a) * 0.42 * T, c + np.sin(a) * 0.42 * T), (c + np.cos(a) * (0.42 - ll) * T, c + np.sin(a) * (0.42 - ll) * T), 1)
        a = r.uniform(0, 2 * np.pi)
        line((c, c), (c + np.cos(a) * 0.30 * T, c + np.sin(a) * 0.30 * T), 2)
        circ(c, c, 3.0 * k, -1)
    elif kind == 8:                                # dot matrix with linked cells
        g = int(r.integers(5, 8))
        sp = 0.76 * T / (g - 1)
        o = c - 0.38 * T
        for i in range(g):
            for j in range(g):
                circ(o + i * sp, o + j * sp, 1.7 * k, -1)
        for q in range(int(r.integers(8, 16))):
            i, j = int(r.integers(0, g)), int(r.integers(0, g))
            i2, j2 = (i + 1, j) if r.random() < 0.5 else (i, j + 1)
            if i2 < g and j2 < g:
                line((o + i * sp, o + j * sp), (o + i2 * sp, o + j2 * sp), 2)
    else:                                          # star-chart polygon with chords
        nv = int(r.integers(5, 9))
        a0 = r.uniform(0, 2 * np.pi)
        vx = c + 0.40 * T * np.cos(a0 + np.arange(nv) * 2 * np.pi / nv)
        vy = c + 0.40 * T * np.sin(a0 + np.arange(nv) * 2 * np.pi / nv)
        for i in range(nv):
            line((vx[i], vy[i]), (vx[(i + 1) % nv], vy[(i + 1) % nv]), 1)
            line((vx[i], vy[i]), (vx[(i + 2) % nv], vy[(i + 2) % nv]), 1)
            circ(vx[i], vy[i], 2.6 * k, -1)
        circ(c, c, 0.08 * T, 1)
    return img.astype(F32) / 255.0


def golden_record(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 54 Golden Record Etching: a gold plate engraved all over with small interstellar diagrams - pulsar-map bursts, binary tick rows, concentric circles, waveforms, transition circles, a row of planets, spirals, gauges, dot matrices, star charts - each tilted and mirrored; dark engraving with a bright lip in mirror gold, matte etch
    n = N
    r = H.rng(seed)
    NR = 12
    big = []
    for kind in range(10):
        for v in range(2):
            big += H.rotset(_rec_tile(kind, 150, seed * 5 + kind * 17 + v), NR, np.pi)
    micro = []
    for kind in (0, 1, 2, 3, 5, 7, 8, 9):
        micro += H.rotset(_rec_tile(kind, 64, seed * 3 + kind * 29), NR, np.pi)
    E = np.zeros((n, n), F32)
    pts = H.jitter_pts(n, 128.0, seed + 1, jit=0.8, margin=40)
    pts = pts[r.random(len(pts)) < 0.88]
    K = len(pts)
    ti = r.integers(0, 20, K) * NR + r.integers(0, NR, K)
    H.splat(E, big, ti, pts[:, 0], pts[:, 1], flip=r.integers(0, 4, K), mode="max")
    occ = H.blur(E, 14.0)
    pm = H.jitter_pts(n, 62.0, seed + 2, jit=0.95, margin=30)
    ix = np.clip(pm[:, 0].astype(np.int64), 0, n - 1)
    iy = np.clip(pm[:, 1].astype(np.int64), 0, n - 1)
    pm = pm[(occ[iy, ix] < 0.045) & (r.random(len(pm)) < 0.9)]
    K2 = len(pm)
    ti2 = r.integers(0, 8, K2) * NR + r.integers(0, NR, K2)
    H.splat(E, micro, ti2, pm[:, 0], pm[:, 1], flip=r.integers(0, 4, K2), mode="max")
    E = np.clip(H.blur(E, 0.85) * 2.4, 0, 1)
    hue = np.clip(0.5 + 0.8 * H.fbm(n, seed + 3, cells=(2, 3, 5), gain=0.6), 0, 1)
    gold = np.array([0.90, 0.68, 0.22], F32)[None, None] * (1 - hue)[..., None] + np.array([0.92, 0.60, 0.40], F32)[None, None] * hue[..., None]
    gl = 0.80 + 0.07 * H.fbm(n, seed + 4, cells=(3, 6, 12, 24), gain=0.6) + 0.045 * _snoise(1500, 60, seed + 5) + 0.03 * H.rng(seed + 6).standard_normal((n, n)).astype(F32)
    patina = np.clip(1.0 - 0.14 * np.clip(H.fbm(n, seed + 7, cells=(6, 12, 24, 48), gain=0.7), 0, 2), 0.7, 1.0)
    ground = gold * (gl * patina)[..., None]
    sh = np.roll(np.roll(E, 1, 0), 1, 1)
    lipm = np.clip(sh - E, 0, 1)
    rgb = ground * (1 - 0.92 * E)[..., None] + np.array([0.06, 0.035, 0.02], F32) * E[..., None]
    rgb += (0.55 * lipm)[..., None] * np.array([1.0, 0.92, 0.70], F32)
    rgb = np.clip(rgb, 0, 1)
    Es = H.blur(E, 0.7)
    M = H.lerp(252.0, 24.0, Es)
    R_ = H.lerp(14.0, 190.0, Es) + 7.0 * _snoise(1500, 60, seed + 5) * (1 - Es)
    CC = H.lerp(16.0, 130.0, Es)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 55. Solar Sail Membrane
# -------------------------------------------------------------------------
def solar_sail(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 55 Solar Sail Membrane: mirror film cut into large smooth triangular GORES that radiate from ~16 grommet hubs (7-12 gores per hub, each gore a flat mirror panel with its own sky-reflection tone and a soft gradient along its length), dark seams with a bright lip between gores and a heavier seam between hub panels, a fine square rip-stop grid (26 px pitch, every 4th thread heavier) aligned to EACH gore so the grid turns at every seam, and only sparse hairline creases; silver with gold-tinted gores; chrome film, roughness rises on seams/grid/creases (coordinator fix 2026-10-12: stucco/rock -> gores + seams + rip-stop)
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)
    hubs = H.jitter_pts(n, 520.0, seed + 1, jit=0.8, margin=160)
    d, lab, hx, hy = H.voronoi(n, hubs)
    K = len(hx)
    li = (lab - 1).astype(np.int64)
    Gk = (7 + r.integers(0, 6, K)).astype(F32)
    ph = r.uniform(0, 2 * np.pi, K).astype(F32)
    dx = X - hx.astype(F32)[li]
    dy = Y - hy.astype(F32)[li]
    G = Gk[li]
    th = np.arctan2(dy, dx)
    th += F32(np.pi)
    th += ph[li]
    f = th * F32(1.0 / (2 * np.pi))
    f -= np.floor(f)
    f *= G
    kf = np.floor(f)
    fr = f - kf
    ks = kf.astype(np.int64)
    seam_d = np.minimum(fr, 1 - fr) * (F32(2 * np.pi) / G) * d
    key = li * 16 + ks
    tk_ = np.arange(K * 16 + 16)
    h1 = H.hash01(tk_, seed)[key]
    h2 = H.hash01(tk_, seed + 5)[key]
    h3 = H.hash01(tk_, seed + 9)[key]
    b0 = 0.20 + 0.72 * h1
    b = b0 + (h2 - 0.5) * 0.60 * np.clip(d / 330.0, 0, 1.3) + 0.34 * (h1 - 0.5) * (fr - 0.5)
    edp = H.edge_dist(lab)
    seam = np.exp(-(seam_d / 1.3) ** 2)
    lip = np.exp(-((seam_d - 2.8) / 1.0) ** 2)
    pseam = np.exp(-(edp / 2.6) ** 2)
    li_t = np.minimum(tk_ // 16, K - 1)
    phi_t = ((tk_ % 16 + 0.5) / Gk[li_t]) * 2 * np.pi - ph[li_t] - np.pi      # gore mid-angle table (tiny) -> gather, no per-pixel trig
    cp_ = np.cos(phi_t).astype(F32)[key]
    sp_ = np.sin(phi_t).astype(F32)[key]
    ur = dx * cp_ + dy * sp_
    vr = -dx * sp_ + dy * cp_
    P = F32(26.0)

    def thread(c):
        q_ = c / P
        fq = q_ - np.floor(q_)
        dd = np.minimum(fq, 1 - fq) * P
        q4 = (q_ + F32(0.5)) * F32(0.25)
        heavy = (q4 - np.floor(q4)) < F32(0.25)                                   # every 4th thread
        return np.exp(-(dd / F32(0.95)) ** 2) * np.where(heavy, F32(1.0), F32(0.55))

    grid = np.maximum(thread(ur), thread(vr)).astype(F32)
    cz = H.fbm(n, seed + 3, cells=(5, 10, 20, 40), gain=0.7)
    crease = H.zero_set_line(cz, 0.55) * H.sstep(0.0, 0.5, H.fbm(n, seed + 4, cells=(3, 6, 12), gain=0.6) + 0.15)
    vv = b * (1.0 - 0.55 * seam) * (1.0 - 0.62 * pseam) * (1.0 - 0.30 * grid) + 0.20 * lip - 0.20 * crease + 0.18 * crease * (1 - crease)
    grom = np.exp(-((d - 17.0) / 2.2) ** 2)
    hole = H.sstep(11.0, 8.0, d)
    vv = np.where(d < 24.0, vv * (1 - hole) + grom * 0.95, vv)
    vv = np.clip(vv + 0.010 * H.rng(seed + 8).standard_normal((n, n)).astype(F32), 0, 1)
    rgb = H.ramp(vv, [(0.0, '#161b28'), (0.28, '#566178'), (0.54, '#a8b2c6'), (0.78, '#e8edf4'), (0.93, '#fff0cc'), (1.0, '#ffffff')])
    gold = (h3 > 0.74).astype(F32) * 0.55
    rgb = rgb * (1.0 - gold[..., None] * np.array([0.02, 0.12, 0.50], F32))
    rgb = np.clip(rgb, 0, 1)
    # [S19 coordinator polish A 2026-10-12] spec richness: the spec now carries the paint's structure (matte/rough ground with 1 px flake; lines, arcs, cores = satin then mirror metal)
    M, R_, CC = H.structure_spec(rgb, seed + 91, [(0.80, 0.45, 215.0, 40.0, 24.0), (0.45, 0.18, 90.0, 120.0, 60.0)],
                                 ground_m=(218.0, 255.0), ground_r=(10.0, 52.0), ground_cc=16.0, flake=0.6, grain=1.22)
    lines_ = np.clip(seam + pseam + grid + crease, 0, 1)
    R_ = R_ + 75.0 * seam + 55.0 * pseam + 42.0 * grid + 60.0 * crease
    M = M - 150.0 * lines_
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 56. Re-entry Thermal Tiles
# -------------------------------------------------------------------------
def thermal_tiles(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 56 Re-entry Thermal Tiles: staggered brick rows of rounded black and white heat-shield tiles in ~16 regions that each turn and resize the grid, felt gap lines, every tile scorched from its leading edge to brown and soot with streaks; matte ceramic, satin glass-black tiles
    n = N
    r = H.rng(seed)
    pts = H.jitter_pts(n, 520.0, seed + 1, jit=0.9, margin=260)
    d, lab, sx, sy = H.voronoi(n, pts)
    K = len(sx)
    li = (lab - 1).astype(np.int64)
    ang = r.uniform(0, np.pi, K).astype(F32)
    tw = r.uniform(26.0, 40.0, K).astype(F32)
    thh = r.uniform(18.0, 26.0, K).astype(F32)
    pb = np.where(r.random(K) < 0.5, 0.80, 0.22).astype(F32)
    X, Y = H.xy(n)
    ca = np.cos(ang)[li]
    sa = np.sin(ang)[li]
    dx = X - sx.astype(F32)[li]
    dy = Y - sy.astype(F32)[li]
    u = dx * ca + dy * sa
    v = -dx * sa + dy * ca
    twp = tw[li]
    thp = thh[li]
    row = np.floor(v / thp)
    ri = row.astype(np.int64)
    off = (ri & 1) * 0.5 * twp + H.hash01(ri * 31 + li, seed + 3) * twp * 0.30
    uu = u - off
    col = np.floor(uu / twp)
    ul = (uu - col * twp).astype(F32)
    vl = (v - row * thp).astype(F32)
    tk = li * 2003 + ri * 9176 + col.astype(np.int64) * 137
    pid = H.hash01(tk, seed)
    pid2 = (pid * 7.31 + 0.37) % 1.0
    pid3 = (pid * 13.7 + 0.61) % 1.0
    black = pid < pb[li]
    black = np.where(pid3 > 0.93, ~black, black)
    rc = 3.6
    qx = np.abs(ul - twp * 0.5) - (twp * 0.5 - rc)
    qy = np.abs(vl - thp * 0.5) - (thp * 0.5 - rc)
    sd = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - rc
    tile = H.sstep(0.2, -1.4, sd)
    bev = H.sstep(0.0, 3.2, -sd)
    mott = H.fbm(n, seed + 4, cells=(110, 220, 440), gain=0.9)
    pit = H.rng(seed + 5).standard_normal((n, n)).astype(F32)
    wcol = np.array([0.80, 0.79, 0.74], F32)
    bcol = np.array([0.085, 0.088, 0.100], F32)
    base = np.where(black[..., None], bcol, wcol)
    surf = np.where(black, 1.0 + 0.45 * mott + 0.25 * pit, 1.0 + 0.14 * mott + 0.16 * pit)
    cbase = base * (surf * (0.74 + 0.26 * bev))[..., None]
    # leading-edge scorch with streaks
    g = np.clip(1.0 - ul / (twp * (0.45 + 0.9 * pid3)), 0, 1) ** 1.4
    sk = _snoise(1500, 80, seed + 6, ang=0.4)
    sc = np.clip(pid2 ** 1.1 * g * (0.75 + 0.60 * sk) + 0.12 * np.clip(mott, 0, 2) * pid2, 0, 0.97)
    scol = np.where(black[..., None], np.array([0.22, 0.14, 0.09], F32), np.array([0.38, 0.20, 0.09], F32))
    cbase = cbase * (1 - sc)[..., None] + scol * (sc * np.where(black, 0.9, 1.0))[..., None]
    felt = np.array([0.30, 0.285, 0.25], F32)[None, None] * (0.8 + 0.4 * pit[..., None])
    rgb = felt * (1 - tile)[..., None] + cbase * tile[..., None]
    rgb = np.clip(rgb, 0, 1)
    lt = np.clip(H.lum(rgb) / 0.85, 0, 1)
    sat_var = (pid2 - 0.5) * 36.0
    M = H.lerp(70.0, 0.0, lt ** 0.5) * tile
    R_ = H.lerp(62.0, 215.0, lt ** 0.7) + sat_var * (1 - lt) + 40.0 * sc
    R_ = np.where(tile > 0.5, R_, 240.0)
    CC = H.lerp(34.0, 255.0, lt ** 0.6)
    CC = np.where(tile > 0.5, CC, 255.0)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 57. Wow! Signal Waterfall
# -------------------------------------------------------------------------
def wow_waterfall(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 57 Wow! Signal Waterfall: a radio-telescope waterfall (time down, frequency across) in 3x2 px bins - exponential receiver hiss shaped by a bandpass and gain drift, ~70 narrowband carriers drifting with Doppler slope and scintillating, ~45 broadband bursts, ~30 dispersed pulse sweeps, flagged dead channels; black-green-yellow colormap, chrome signals on matte hiss
    n = N
    r = H.rng(seed)
    bw, bh = 3, 2
    cw = n // bw + 1
    chh = n // bh + 1
    pw = (-np.log(r.random((chh, cw), dtype=F32) + F32(1e-6))).astype(F32)
    bp = cv2.resize(r.standard_normal((1, 14)).astype(F32), (cw, 1), interpolation=cv2.INTER_CUBIC)[0]
    bp = np.clip(0.62 + 0.30 * bp, 0.25, 1.4).astype(F32)
    gt = cv2.resize(r.standard_normal((30, 1)).astype(F32), (1, chh), interpolation=cv2.INTER_CUBIC)[:, 0]
    gt = np.clip(1.0 + 0.16 * gt, 0.6, 1.5).astype(F32)
    zap = np.ones(cw, F32)
    for c in r.integers(0, cw, 16):
        zap[c:c + int(r.integers(1, 4))] = 0.10
    hiss = pw * bp[None, :] * gt[:, None] * zap[None, :]
    ri, ci, vv = [], [], []
    # narrowband carriers with Doppler drift and scintillation
    for k in range(78):
        L = int(r.integers(140, 900))
        r0 = int(r.integers(-100, chh))
        c0 = float(r.uniform(0, cw))
        d = float(r.choice([0.0, 1.0, 1.0, 1.0]) * r.uniform(-0.40, 0.40))
        A = float(np.exp(r.uniform(np.log(1.6), np.log(11.0))))
        t = np.arange(L)
        rows = r0 + t
        cols = c0 + d * t + np.cumsum(r.normal(0, 0.12, L))
        on = (np.repeat(r.random(L // 7 + 1) < 0.80, 7)[:L]).astype(F32)
        sc = (0.35 + 0.95 * r.random(L)).astype(F32) * on
        for wdt, wv in ((0, 1.0), (1, 0.55)):
            ri.append(rows)
            ci.append(np.round(cols).astype(np.int64) + wdt)
            vv.append(A * sc * wv)
    # dispersed pulse sweeps
    for k in range(32):
        L = int(r.integers(30, 130))
        r0 = int(r.integers(0, chh - L))
        c0 = float(r.uniform(0, cw - 60))
        w_ = float(r.uniform(50, 260))
        A = float(r.uniform(3.0, 9.0))
        t = np.arange(L)
        cols = c0 + w_ * (1.0 - (1.0 - t / L) ** 2.3)
        for wdt, wv in ((0, 1.0), (1, 0.7), (2, 0.35)):
            ri.append(r0 + t)
            ci.append(np.round(cols).astype(np.int64) + wdt)
            vv.append(A * wv * (0.55 + 0.9 * r.random(L)).astype(F32))
    ri = np.concatenate(ri)
    ci = np.concatenate(ci)
    vv = np.concatenate(vv).astype(F32)
    ok = (ri >= 0) & (ri < chh) & (ci >= 0) & (ci < cw)
    sig = np.bincount(ri[ok] * cw + ci[ok], weights=vv[ok], minlength=chh * cw).reshape(chh, cw).astype(F32)
    # broadband bursts
    for k in range(48):
        h_ = int(r.integers(1, 7))
        r0 = int(r.integers(0, chh - h_))
        w_ = int(r.integers(20, 200))
        c0 = int(r.integers(0, cw - w_))
        prof = np.exp(-((np.arange(w_) - r.uniform(0.2, 0.8) * w_) / (0.45 * w_)) ** 2).astype(F32)
        sig[r0:r0 + h_, c0:c0 + w_] += float(r.uniform(2.0, 7.0)) * prof[None, :] * (0.5 + 0.7 * r.random((h_, 1)).astype(F32))
    power = hiss * 0.78 + sig * (0.55 + 0.45 * pw) * zap[None, :]
    tn = 0.10 + 0.90 * (1.0 - np.exp(-power * F32(0.46)))
    tn = cv2.resize(tn.astype(F32), (n, n), interpolation=cv2.INTER_NEAREST)
    Xp = np.arange(n)
    gridx = ((Xp % bw) == 0)[None, :]
    gridy = ((Xp % bh) == 0)[:, None]
    tn = tn * (1.0 - 0.10 * (gridx | gridy))
    rgb = H.ramp(np.clip(tn, 0, 1), [(0.0, '#020a05'), (0.20, '#052a12'), (0.40, '#0e6428'), (0.60, '#3fa21e'), (0.80, '#cdd820'), (1.0, '#fffbd8')])
    rgb = np.clip(rgb, 0, 1)
    sm = H.sstep(0.50, 0.92, tn)
    M = H.lerp(8.0, 255.0, sm)
    R_ = H.lerp(214.0, 4.0, sm ** 0.8)
    CC = H.lerp(210.0, 16.0, sm)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 58. Dyson Swarm
# -------------------------------------------------------------------------
def _hexk(R, flat):
    k = np.zeros((2 * R + 1, 2 * R + 1), np.uint8)
    y, x = np.mgrid[-R:R + 1, -R:R + 1].astype(F32)
    if not flat:
        x, y = y, x
    inside = (np.abs(y) <= R * 0.866 + 0.3) & (np.abs(x) + np.abs(y) / 1.732 <= R + 0.3)
    k[inside] = 1
    return k


def dyson_swarm(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 58 Dyson Swarm: ~80 nested elliptical orbit bands of myriad tiny gold hexagonal collectors (2-8 px, each band with its own typical size), edge-lit with a bright centre pixel, a warm haze along every band and a few white glints; black space; mirror-gold flake collectors on a pearl dark ground
    n = N
    r = H.rng(seed)
    NS = 20
    xs_l, ys_l, cl_l, vl_l, ob_l = [], [], [], [], []
    sizes = np.array([2, 3, 4, 5, 7])
    cen = H.jitter_pts(n, 440.0, seed + 11, jit=0.9, margin=160)
    cen = cen[r.permutation(len(cen))[:NS]]
    for si in range(len(cen)):
        cx, cy = cen[si]
        phi0 = r.uniform(0, np.pi)
        ecc = r.uniform(0.30, 0.78)
        NE_ = int(r.integers(6, 11))
        for k in range(NE_):
            a = 40.0 + (k / max(1, NE_ - 1)) ** 1.2 * r.uniform(200.0, 400.0)
            b = a * np.clip(ecc + r.normal(0, 0.07), 0.2, 0.95)
            phi = phi0 + r.normal(0, 0.16)
            cnt = int(r.uniform(900, 1700) * (a / 300.0) ** 0.8)
            t = r.uniform(0, 2 * np.pi, cnt)
            wband = r.uniform(12.0, 42.0)
            off = r.normal(0, wband * 0.38, cnt)
            x = (a + off) * np.cos(t)
            y = (b + off * b / a) * np.sin(t)
            xs_l.append(cx + x * np.cos(phi) - y * np.sin(phi))
            ys_l.append(cy + x * np.sin(phi) + y * np.cos(phi))
            mode = int(r.integers(0, 5))
            pe = np.full(5, 0.10)
            pe[mode] = 0.55
            pe /= pe.sum()
            cl_l.append(r.choice(5, cnt, p=pe))
            vl_l.append(0.45 + 0.55 * r.random(cnt) ** 1.6)
            ob_l.append(r.integers(0, 2, cnt))
    xs = np.concatenate(xs_l)
    ys = np.concatenate(ys_l)
    cl = np.concatenate(cl_l)
    vl = np.concatenate(vl_l).astype(F32)
    ob = np.concatenate(ob_l)
    ix = np.round(xs).astype(np.int64)
    iy = np.round(ys).astype(np.int64)
    ok = (ix >= 0) & (ix < n) & (iy >= 0) & (iy < n)
    ix, iy, cl, vl, ob = ix[ok], iy[ok], cl[ok], vl[ok], ob[ok]
    glint = r.random(len(vl)) < 0.045
    vl = np.where(glint, 1.0, vl).astype(F32)
    hexv = np.zeros((n, n), F32)
    ctr = np.zeros((n, n), F32)
    dens = np.zeros((n, n), F32)
    for ci_, Rr in enumerate(sizes):
        for fl in (0, 1):
            sel = (cl == ci_) & (ob == fl)
            if not sel.any():
                continue
            pc = np.zeros((n, n), F32)
            H.points(pc, ix[sel], iy[sel], vl[sel])
            hexv = np.maximum(hexv, cv2.dilate(pc, _hexk(int(Rr), bool(fl))))
            ctr = np.maximum(ctr, pc)
    H.points(dens, ix, iy, np.ones(len(ix), F32), mode="add")
    core = cv2.erode(hexv, np.ones((3, 3), np.uint8))
    edge = np.clip(hexv - core, 0, 1)
    body = np.where(core > 0.01, core, hexv * 0.55)
    lv = np.clip(body * (1.0 - 0.18 * edge) + 0.40 * ctr, 0, 1.2)
    gold = H.ramp(np.clip(lv, 0, 1), [(0.0, '#000000'), (0.30, '#5a3a0a'), (0.58, '#c4861a'), (0.82, '#ffd34c'), (1.0, '#fff4c0')])
    haze = np.clip(H.blur(dens, 7.0) * 1.7 + H.blur(dens, 22.0) * 3.5, 0, 1.2)
    gz = _gz(n, seed + 2, 0.22)
    ground = np.array([0.060, 0.050, 0.078], F32)[None, None] * gz[..., None]
    rgb = ground + (haze * 0.20)[..., None] * np.array([1.0, 0.70, 0.28], F32)
    rgb = rgb * (1 - np.clip(lv * 3.0, 0, 1))[..., None] + gold
    rgb += _specks(n, seed + 3, 0.0015, 0.08, 0.55)[..., None] * np.array([0.9, 0.9, 1.0], F32)
    rgb = np.clip(rgb, 0, 1)
    fm = hexv > 0.01
    M = np.where(fm, 255.0, H.lerp(90.0, 130.0, np.clip(haze, 0, 1)))
    R_ = np.where(fm, 3.0 + 40.0 * edge, H.lerp(105.0, 80.0, np.clip(haze, 0, 1)))
    CC = np.where(fm, 16.0, 30.0)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 59. Derelict Xenotech
# -------------------------------------------------------------------------
def derelict_xenotech(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 59 Derelict Xenotech: dark-bronze biomechanical ribbing - parallel rounded tubes (straight or bending around far centres, one hub panel each with a seam groove, cross-joints every ~70 px, a specular line per tube) - crossed by ~170 bundled right-angle circuit traces with vias, pads and component blocks that glow teal and bleed light into the flesh; chrome traces, satin flesh
    n = N
    r = H.rng(seed)
    # dark-bronze biomechanical ribbing (coordinator fix 2026-10-12: leopard-print flesh -> parallel ribs/tubes that bend around)
    X, Y = H.xy(n)
    cells = H.jitter_pts(n, 560.0, seed + 5, jit=0.85, margin=200)
    _d, lab_, cx_, cy_ = H.voronoi(n, cells)
    Kc = len(cx_)
    li = (lab_ - 1).astype(np.int64)
    kind = r.random(Kc) < 0.40                       # True = arcs about a far centre, False = straight parallel ribs
    alpha = r.uniform(0, np.pi, Kc).astype(F32)
    per = r.uniform(46.0, 72.0, Kc).astype(F32)
    rd_ = r.uniform(240.0, 520.0, Kc).astype(F32)
    ux = (X - cx_[li].astype(F32)).astype(F32)
    uy = (Y - cy_[li].astype(F32)).astype(F32)
    ca = np.cos(alpha)[li]
    sa = np.sin(alpha)[li]
    lin = ux * ca + uy * sa
    arcx = ux - rd_[li] * ca
    arcy = uy - rd_[li] * sa
    kd = kind[li]
    phs = np.where(kd, np.hypot(arcx, arcy), lin)
    alo = np.where(kd, np.arctan2(arcy, arcx) * 420.0, -ux * sa + uy * ca)
    phs = (phs + 12.0 * H.fbm(n, seed + 2, cells=(6, 12, 24), gain=0.6) + 70.0 * H.fbm(n, seed + 3, cells=(2, 3, 5), gain=0.6)) / per[li]
    fq = phs - np.floor(phs)
    tube = np.sin(np.pi * fq) ** 1.4
    hl = np.exp(-((fq - 0.36) / 0.09) ** 2) * tube
    aq = alo / 90.0
    fa = aq - np.floor(aq)
    joint = np.exp(-(np.minimum(fa, 1 - fa) * 90.0 / 3.2) ** 2)
    pseam = np.exp(-(H.edge_dist(lab_) / 3.0) ** 2)
    mott = 0.82 + 0.30 * np.clip(0.5 + 0.7 * H.fbm(n, seed + 6, cells=(3, 6, 12), gain=0.6), 0, 1)
    t = tube * (1.0 - 0.85 * joint) * (1.0 - 0.80 * pseam)
    t = np.clip((0.05 + 0.62 * t + 0.42 * hl + 0.04 * H.rng(seed + 4).standard_normal((n, n)).astype(F32)) * mott, 0, 1)
    flesh = H.ramp(t, [(0.0, '#070405'), (0.30, '#20130a'), (0.55, '#46290f'), (0.78, '#7c5424'), (1.0, '#caa05a')])
    # right-angle trace routing
    polys, vals = [], []
    comps = []
    for k in range(175):
        x = float(r.uniform(-30, n + 30))
        y = float(r.uniform(-30, n + 30))
        horiz = bool(r.random() < 0.5)
        nseg = int(r.integers(3, 7))
        pts_ = [(x, y)]
        for s_ in range(nseg):
            Ls = float(r.uniform(26, 150)) * (1 if r.random() < 0.5 else -1)
            if horiz:
                x += Ls
            else:
                y += Ls
            horiz = not horiz
            pts_.append((x, y))
        P = np.array(pts_, np.float64)
        nb = int(r.choice([1, 1, 2, 3, 4], p=[0.3, 0.2, 0.2, 0.2, 0.1]))
        v = int(r.uniform(150, 255))
        for j in range(nb):
            polys.append(P + 9.0 * j)
            vals.append(v)
        comps.append((P[0], P[-1], nb))
    tr = H.lines_u8(n, polys, np.array(vals), thick=2).astype(F32) / 255.0
    pad = np.zeros((n, n), np.uint8)
    for (p0, p1, nb) in comps:
        for pp, rad in ((p0, 5), (p1, 5)):
            cv2.circle(pad, (int(pp[0]), int(pp[1])), rad, 255, -1, cv2.LINE_AA)
        if nb >= 2 and r.random() < 0.5:
            x0, y0 = int(p1[0]), int(p1[1])
            cv2.rectangle(pad, (x0 - 10, y0 - 7), (x0 + 10 + 4 * nb, y0 + 7 + 4 * nb), 255, 2, cv2.LINE_AA)
    # vias at corners
    for P_, v_ in zip(polys[::3], vals[::3]):
        for q_ in P_[1:-1]:
            cv2.circle(pad, (int(q_[0]), int(q_[1])), 3, 255, 1, cv2.LINE_AA)
    pd = pad.astype(F32) / 255.0
    trc = np.clip(np.maximum(tr, pd), 0, 1)
    glow = H.blur(trc, 2.0) * 0.55 + H.blur(trc, 8.0) * 0.40
    bleed = H.blur(trc, 4.5)
    rgb = flesh * (1.0 - 0.55 * np.clip(bleed * 1.6, 0, 1))[..., None]
    rgb += (glow * 0.85)[..., None] * np.array([0.10, 0.95, 0.80], F32)
    rgb += (trc * 0.75)[..., None] * np.array([0.60, 1.0, 0.95], F32)
    rgb = np.clip(rgb, 0, 1)
    fl_l = np.clip((H.lum(flesh) - 0.03) / 0.7, 0, 1)
    tm = np.clip(trc * 1.4, 0, 1)
    M = H.lerp(110.0, 175.0, fl_l)
    R_ = H.lerp(135.0, 62.0, fl_l)
    CC = H.lerp(54.0, 26.0, fl_l)
    M = H.lerp(M, 255.0, tm)
    R_ = H.lerp(R_, 6.0, tm)
    CC = H.lerp(CC, 16.0, tm)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 60. Hyperspace Jump
# -------------------------------------------------------------------------
def hyperspace(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 60 Hyperspace Jump: ~30000 stars stretched into long, nearly parallel blue-white streaks that fan gently away from ONE vanishing point far off the sheet (4300 px up-left): streak length grows with distance from it and varies wildly (many short, a few 500 px), white hot heads fading through blue to the tail, a few thick fast flares, bloom, a faint tunnel haze toward the vanishing point; chrome streaks on candy blue (coordinator fix 2026-10-12: anemone bursts -> long near-parallel fan from an off-canvas vanishing point)
    n = N
    r = H.rng(seed)
    ang = float(r.uniform(0.30, 0.95))
    D = 4300.0
    vx = n / 2 - D * np.cos(ang)
    vy = n / 2 - D * np.sin(ang)
    S = 13000
    px = r.uniform(-60, n + 60, S).astype(F32)
    py = r.uniform(-60, n + 60, S).astype(F32)
    dxv = px - vx
    dyv = py - vy
    dist = np.hypot(dxv, dyv).astype(F32)
    ux = dxv / dist
    uy = dyv / dist
    tt = np.clip((dist - (D - 1700.0)) / 3400.0, 0, 1)
    fast = r.random(S) < 0.06
    L = (r.uniform(0.08, 1.0, S) ** 1.8 * (70.0 + 520.0 * tt ** 1.2) + 5.0).astype(F32)
    L = np.where(fast, L * 1.5 + 40.0, L).astype(F32)
    bright = (0.25 + 0.75 * r.random(S) ** 1.4).astype(F32)
    NSEG = 8
    sc = 16.0
    out = {1: np.zeros((n, n), np.uint8), 3: np.zeros((n, n), np.uint8)}
    core = {1: np.zeros((n, n), np.uint8), 3: np.zeros((n, n), np.uint8)}
    vals, segs, th, ci = [], [], [], []
    for i in range(NSEG):
        a0 = L * (i / float(NSEG))
        a1 = L * ((i + 1) / float(NSEG))
        fade = (1.0 - i / float(NSEG)) ** 1.6
        vals.append((bright * 160.0 + 90.0) * (0.12 + 0.88 * fade))
        segs.append(np.stack([np.stack([px - ux * a0, py - uy * a0], -1), np.stack([px - ux * a1, py - uy * a1], -1)], 1))
        th.append(np.where(fast, 3, 1))
        ci.append(np.full(S, i == 0))
    val = np.concatenate(vals).astype(F32)
    seg = np.concatenate(segs, 0)
    thick = np.concatenate(th)
    iscore = np.concatenate(ci)
    pts_all = np.round(seg * sc).astype(np.int32).reshape(-1, 2, 1, 2)
    order = np.argsort(val, kind="stable")
    lv = np.minimum((val[order] / 256.0 * 14).astype(np.int64), 13)
    pts_s = pts_all[order]
    v_s = val[order]
    th_s = thick[order]
    cr_s = iscore[order]
    for b in range(14):
        for tk in (1, 3):
            sel = np.flatnonzero((lv == b) & (th_s == tk))
            if len(sel) == 0:
                continue
            col = int(np.clip(v_s[sel].mean(), 8, 255))
            cv2.polylines(out[tk], list(pts_s[sel]), False, col, tk, cv2.LINE_AA, 4)
            sc_ = sel[cr_s[sel]]
            if len(sc_):
                cv2.polylines(core[tk], list(pts_s[sc_]), False, min(255, col + 55), tk, cv2.LINE_AA, 4)
    stk = np.maximum(out[1], out[3]).astype(F32) / 255.0
    hot = np.maximum(core[1], core[3]).astype(F32) / 255.0
    hd_ = np.zeros((n, n), F32)
    H.points(hd_, np.round(px).astype(np.int64), np.round(py).astype(np.int64), bright)
    hot = np.clip(hot + H.blur(hd_, 1.1) * 3.0, 0, 1)
    bloom = H.blur(stk, 1.5) * 0.9 + H.blur(stk, 5.0) * 0.45
    X, Y = H.xy(n)
    dvp = np.hypot(X - vx, Y - vy)
    tun = np.clip(np.exp(-(dvp - (D - 1500.0)) / 1900.0), 0, 1) * 0.30
    hue = np.clip(0.5 + 0.9 * H.fbm(n, seed + 2, cells=(2, 4, 8), gain=0.6), 0, 1)
    f3 = np.clip(H.fbm(n, seed + 3, cells=(3, 6), gain=0.6), 0, 1.5)
    cA = np.array([0.80, 0.93, 1.0], F32)
    cB = np.array([0.36, 0.56, 1.0], F32)
    cC = np.array([0.62, 0.50, 1.0], F32)
    scol = (cA[None, None] * (1 - hue)[..., None] + cB[None, None] * hue[..., None])
    scol = scol * (1 - 0.35 * f3)[..., None] + cC[None, None] * (0.35 * f3)[..., None]
    gz = _gz(n, seed + 4, 0.22)
    ground = np.array([0.020, 0.045, 0.170], F32)[None, None] * gz[..., None]
    rgb = ground + tun[..., None] * np.array([0.42, 0.62, 1.0], F32) * (0.7 + 0.3 * gz[..., None])
    rgb += (np.clip(stk * 1.25, 0, 1) * (1.0 - 0.7 * hot))[..., None] * scol
    rgb += (hot * 1.1)[..., None] * np.array([1.0, 1.0, 1.0], F32)
    rgb += (bloom * 0.55)[..., None] * np.array([0.45, 0.65, 1.0], F32)
    rgb = np.clip(rgb, 0, 1)
    # [S19 coordinator polish A 2026-10-12] spec richness: the spec now carries the paint's structure (matte/rough ground with 1 px flake; lines, arcs, cores = satin then mirror metal)
    M, R_, CC = H.structure_spec(rgb, seed + 91, [(0.28, 0.55, 195.0, 50.0, 28.0), (0.70, 0.98, 255.0, 3.0, 16.0)],
                                 ground_m=(40.0, 95.0), halo=(2.2, 1.6, 135.0, 80.0, 36.0), brush=18.0)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


FINISHES = [
    ("cz_mothership_plating", "Mothership Plating",
     "Staggered armour plates fanning round saucer hubs: dark seams, rivet rows and blue-gold heat tint on brushed titanium.", mothership_plating),
    ("cz_xenoglyph_script", "Xenoglyph Script",
     "Thousands of invented alien glyphs etched in wavy rows across bright alloy, the rows turning in three regions.", xenoglyph_script),
    ("cz_crop_formation", "Crop Formation Field",
     "Combed olive-gold straw grain with flattened crop-circle pictograms catching the light in new directions.", crop_formation),
    ("cz_golden_record", "Golden Record Etching",
     "A gold plate engraved with small interstellar diagrams: pulsar bursts, binary ticks, circles, waveforms and star charts.", golden_record),
    ("cz_solar_sail", "Solar Sail Membrane",
     "Pale mirror-film sail cut into gores that radiate from black hubs, edged with seams and a fine rip-stop grid.", solar_sail),
    ("cz_thermal_tiles", "Re-entry Thermal Tiles",
     "Staggered black and white heat-shield tiles with scorched leading edges and felt gaps, the grid turning by region.", thermal_tiles),
    ("cz_wow_waterfall", "Wow! Signal Waterfall",
     "A radio spectrogram: green receiver hiss in coarse bins with drifting carrier lines, bursts and dispersed sweeps in yellow.", wow_waterfall),
    ("cz_dyson_swarm", "Dyson Swarm",
     "Myriad tiny gold collector specks streaming along many nested elliptical orbit bands in black space.", dyson_swarm),
    ("cz_derelict_xenotech", "Derelict Xenotech",
     "Dark bronze ribbed tubes and arcs crossed by right-angle glowing cyan circuit traces, vias and pads.", derelict_xenotech),
    ("cz_hyperspace", "Hyperspace Jump",
     "Blue-white star streaks stretching away from a single off-canvas vanishing point over a deep blue glow.", hyperspace),
]
