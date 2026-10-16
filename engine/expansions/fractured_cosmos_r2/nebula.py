# -*- coding: utf-8 -*-
"""NEBULAE chapter (cz_ 11-20): dust, gas, shocks and ice between the stars.

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


# -------------------------------------------------------------------------
# 11. Pillars of Creation - dark dust columns with glowing rims on teal-gold gas
# -------------------------------------------------------------------------
def pillars(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 11 Pillars of Creation: tall VERTICAL dust columns rising from the floor of each of four bands, tapering, rim-lit on the upper-left edge, evaporating finger tips (vertically stretched noise), against glowing teal-gold gas (wave-2 review: diagonal rust camo -> tall pillars)
    n = N
    r = H.rng(seed)
    NB = 4
    bh = n // NB
    val = np.full((n, n), -400.0, F32)
    xs = np.arange(n, dtype=F32)
    Yr = np.arange(n, dtype=F32)[:, None]
    for b in range(NB):
        prof = np.zeros(n, F32)
        for _ in range(int(r.integers(5, 8))):
            x0 = float(r.uniform(-0.03, 1.03) * n)
            h = float(r.uniform(0.36, 0.94) * bh)
            w = float(r.uniform(42.0, 105.0))
            dx = np.abs(xs - x0) / w
            pr = h * np.clip(1.0 - dx ** 1.25, 0, 1) ** 0.62
            np.maximum(prof, pr.astype(F32), out=prof)
        for _ in range(int(r.integers(3, 6))):
            x0 = float(r.uniform(0, 1) * n)
            h = float(r.uniform(0.10, 0.34) * bh)
            w = float(r.uniform(28.0, 60.0))
            dx = np.abs(xs - x0) / w
            np.maximum(prof, (h * np.clip(1.0 - dx ** 1.25, 0, 1) ** 0.62).astype(F32), out=prof)
        yf = (b + 1) * bh - 40.0 + 36.0 * _snoise(1, 9, seed + 60 + b)[0].astype(F32)       # undulating floor line per column
        vb = np.minimum(prof[None, :] + 30.0 - (yf[None, :] - Yr), 70.0 + (yf[None, :] - Yr))
        np.maximum(val, vb, out=val)
    nzA = _snoise(3, 120, seed + 3)
    nzB = _snoise(10, 330, seed + 4)
    fn = H.fbm(n, seed + 5, cells=(40, 100, 220, 440), gain=0.7)
    val = val + 58.0 * nzA + 24.0 * nzB + 12.0 * fn
    dm = H.sstep(-2.5, 2.5, val)
    ds = H.blur(dm, 2.2)
    gy, gx = np.gradient(ds)
    lit = np.clip((gx + gy) * 3.8, 0, 1)
    edge = np.clip(np.hypot(gx, gy) * 5.0, 0, 1)
    rim = np.clip(lit + 0.26 * edge, 0, 1)
    gas_t = np.clip(0.52 + 0.26 * H.fbm(n, seed + 2, cells=(3, 6, 12, 24, 48)) + 0.14 * _snoise(5, 150, seed + 6) + 0.16 * _snoise(24, 300, seed + 13) + 0.22 * _snoise(18, 250, seed + 14), 0, 1)
    gas = H.ramp(gas_t, [(0.0, '#04242c'), (0.38, '#0c5c64'), (0.62, '#1e9a94'), (0.82, '#c0a244'), (1.0, '#ffe08a')])
    dust_t = np.clip(0.5 + 0.40 * H.fbm(n, seed + 7, cells=(48, 96, 192, 384), gain=0.85) + 0.45 * _snoise(30, 420, seed + 12) + 0.25 * _snoise(8, 210, seed + 16), 0, 1)
    dust = H.ramp(dust_t, [(0.0, '#100804'), (1.0, '#6a4026')])
    halo = H.blur(dm, 16.0)
    rgb = gas * (1 - dm)[..., None] + dust * dm[..., None]
    rgb += (0.70 * halo * (1 - dm))[..., None] * np.array([0.95, 0.72, 0.30], F32)
    rgb += H.blur(rim, 6.0)[..., None] * np.array([0.9, 0.7, 0.3], F32) * 0.55
    rgb += rim[..., None] * np.array([1.0, 0.82, 0.45], F32) * 0.95
    b = np.clip(H.lum(np.clip(rgb, 0, 1)) / 0.75, 0, 1)
    rm = np.clip(rim * 1.6, 0, 1)
    M = H.lerp(H.lerp(90.0, 6.0, dm), 245.0, rm)
    R = H.lerp(H.lerp(130.0 - 70.0 * b, 235.0 - 40.0 * b, dm), 10.0, rm)
    CC = H.lerp(H.lerp(70.0, 255.0, dm), 16.0, rm)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 12. Bok Globules - opaque dark blobs over pink H-alpha haze
# -------------------------------------------------------------------------
def bok_globules(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 12 Bok Globules: SOFT-edged dark globules (metaballs, wide soft threshold) with a thin glowing rim that is brightest on the star-lit upper-left, inside warped FILAMENTARY pink gas (wave-2 review: hard black blobs with white outlines read as cartoon holes)
    n = N
    r = H.rng(seed)
    pts = H.jitter_pts(n, 112.0, seed + 1, jit=0.95, margin=60)
    pts = pts[r.random(len(pts)) < 0.78]
    cls = r.choice(5, len(pts), p=[0.28, 0.28, 0.2, 0.15, 0.09])
    sigs = (7.0, 10.0, 14.5, 20.0, 28.0)
    g = np.zeros((n, n), F32)
    for c in range(5):
        m = cls == c
        if not m.any():
            continue
        layer = np.zeros((n, n), F32)
        H.points(layer, pts[m, 0], pts[m, 1], (2 * np.pi * sigs[c] ** 2) * (0.75 + 0.55 * r.random(int(m.sum()))), mode="add")
        g += H.blur(layer, sigs[c])
    dx = 12.0 * H.fbm(n, seed + 5, cells=(8, 16, 32, 64))
    dy = 12.0 * H.fbm(n, seed + 6, cells=(8, 16, 32, 64))
    g = H.warp(g, dx, dy)
    T = 0.25
    gl = H.sstep(0.03, 0.55, g)
    gg = H.blur(g, 2.0)
    gy, gx = np.gradient(gg)
    gm = np.hypot(gx, gy) + F32(1e-6)
    facing = 0.5 + 0.5 * ((gx + gy) / gm) * 0.7071
    rim = np.exp(-((g - 0.09) / 0.045) ** 2) * (1 - gl) * (0.22 + 0.95 * facing ** 1.6)
    z = H.fbm(n, seed + 9, cells=(5, 10, 20, 40, 80), gain=0.72)
    z = H.warp(z.astype(F32), (46.0 * H.fbm(n, seed + 15, cells=(3, 6, 12))).astype(F32), (46.0 * H.fbm(n, seed + 16, cells=(3, 6, 12))).astype(F32))
    fil = H.ridged(z * 1.6)
    z2 = H.fbm(n, seed + 17, cells=(24, 48, 96, 160), gain=0.8)
    z2 = H.warp(z2.astype(F32), (30.0 * H.fbm(n, seed + 18, cells=(4, 8, 16, 32))).astype(F32), (30.0 * H.fbm(n, seed + 19, cells=(4, 8, 16, 32))).astype(F32))
    fil2 = np.clip(H.ridged(1.8 * z2), 0, 1) ** 2
    hz = np.clip(0.18 + 0.26 * H.fbm(n, seed + 2, cells=(3, 6, 12, 24, 48, 96)) + 0.55 * np.clip(fil, 0, 1) ** 2.2 + 0.55 * fil2 + 0.14 * H.fbm(n, seed + 3, cells=(96, 192), gain=0.9), 0, 1)
    haze = H.ramp(hz, [(0.0, '#40102e'), (0.4, '#b02a6c'), (0.72, '#f46c9c'), (1.0, '#ffd2e2')])
    ext = 1.0 - 0.70 * H.blur(gl, 18.0)
    st = np.zeros((n, n), F32)
    sx = r.integers(0, n, 14000)
    sy = r.integers(0, n, 14000)
    H.points(st, sx, sy, 0.15 + 0.85 * r.random(14000) ** 2)
    big = r.integers(0, n, (260, 2))
    H.points(st, big[:, 0], big[:, 1], np.ones(260, F32))
    stg = (st + 0.9 * H.blur(st, 1.2) * (st > 0.8) + 0.25 * H.blur(st, 3.5) * (st > 0.8)) * (1 - gl)
    core = np.array([0.040, 0.020, 0.032], F32)[None, None, :] * (0.7 + 0.8 * H.fbm(n, seed + 21, cells=(24, 48, 96)))[..., None] + 0.10 * haze * ext[..., None]
    rgb = haze * ext[..., None] * (1 - gl)[..., None] + gl[..., None] * core
    rgb += rim[..., None] * np.array([1.0, 0.80, 0.80], F32) * 0.95
    rgb += stg[..., None] * np.array([0.95, 0.92, 1.0], F32)
    lm = np.clip(H.lum(np.clip(rgb, 0, 1)) / 0.7, 0, 1)
    M = 14.0 + 210.0 * np.clip(rim, 0, 1) + 200.0 * np.clip(stg, 0, 1)
    fz = H.fbm(n, seed + 40, cells=(160, 320, 640), gain=0.95)
    R = H.lerp(235.0, 30.0, lm ** 0.6) + 31.0 * fz
    M = M + 29.0 * fz * (1 - gl)
    CC = H.lerp(255.0, 16.0, H.sstep(0.04, 0.22, lm))
    return H.finish_out(rgb, H.spec_pack(np.clip(M, 0, 255), R, CC))


# -------------------------------------------------------------------------
# 13. Veil Nebula Strands - combed cyan and crimson hair
# -------------------------------------------------------------------------
def veil_strands(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 13 Veil Nebula Strands: thousands of particle traces through a low-frequency curl field with a mean sweep (combed hair); crimson set uses a slightly different field so it braids with the cyan
    n = N
    r = H.rng(seed)
    m = 256
    u1, v1 = H.curl_field(m, seed + 1, cells=(2, 4, 8), gain=0.55)
    u2, v2 = H.curl_field(m, seed + 9, cells=(2, 4, 8), gain=0.55)
    ca, sa = float(np.cos(0.35)), float(np.sin(0.35))

    def sweep(u, v, w):
        a = u * w + 0.95
        b = v * w
        s = np.sqrt(a * a + b * b)
        a, b = a / s, b / s
        return (a * ca - b * sa).astype(F32), (a * sa + b * ca).astype(F32)

    uA, vA = sweep(u1, v1, 0.55)
    uB, vB = sweep(0.65 * u1 + 0.35 * u2, 0.65 * v1 + 0.35 * v2, 0.55)
    dens = H.fbm(n, seed + 3, cells=(3, 6, 12), gain=0.6)
    K = 5200
    p0 = np.stack([r.uniform(-260, n, K), r.uniform(-260, n, K)], 1).astype(F32)
    keep = r.random(K) < (0.30 + 0.70 * H.sstep(-0.8, 0.9, dens[np.clip(p0[:, 1], 0, n - 1).astype(int), np.clip(p0[:, 0], 0, n - 1).astype(int)]))
    p0 = p0[keep]
    K = len(p0)
    pB0 = p0 + r.normal(0, 3.2, p0.shape).astype(F32)
    trA = H.trace(uA, vA, p0, 82, 7.5)
    trB = H.trace(uB, vB, pB0, 82, 7.5)
    cA = H.lines_u8(n, list(trA), (70 + 185 * r.random(K) ** 0.8).astype(np.int32), thick=1)
    cB = H.lines_u8(n, list(trB), (70 + 185 * r.random(K) ** 0.8).astype(np.int32), thick=1)
    a = cA.astype(F32) / 255.0
    b = cB.astype(F32) / 255.0
    ground = H.ramp(0.5 + 0.30 * H.fbm(n, seed + 4, cells=(4, 9, 20, 44, 90)), [(0.0, '#05060e'), (0.5, '#0a0e1e'), (1.0, '#141c3a')])
    cy = np.array([0.20, 0.92, 1.0], F32)
    cr = np.array([1.0, 0.12, 0.20], F32)
    A = a + 0.8 * H.blur(a, 1.6) + 0.30 * H.blur(a, 5.0)
    B = b + 0.8 * H.blur(b, 1.6) + 0.30 * H.blur(b, 5.0)
    rgb = ground + A[..., None] * cy + B[..., None] * cr
    I = np.clip(np.maximum(a, b) + 0.5 * H.blur(np.maximum(a, b), 1.5), 0, 1)
    M = H.lerp(110.0, 245.0, I)
    R = H.lerp(130.0, 12.0, I)
    CC = H.lerp(130.0, 16.0, I)
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 14. Herbig-Haro Bow Shocks - chains of nested crescents along invisible jets
# -------------------------------------------------------------------------
def bow_shocks(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 14 Herbig-Haro Bow Shocks: nested elliptical arcs stamped in chains that widen and fade along random jet lines
    n = N
    r = H.rng(seed)
    sc = 16
    arcs = np.zeros((n, n), np.uint8)
    knots = np.zeros((n, n), np.uint8)
    jets = np.zeros((n, n), np.uint8)
    for j in range(170):
        x0, y0 = r.uniform(-60, n + 60, 2)
        th = float(r.uniform(0, 2 * np.pi))
        L = float(r.uniform(220, 560))
        ns = int(r.integers(4, 10))
        t = np.cumsum(r.uniform(0.6, 1.4, ns))
        t = t / t[-1] * L
        ct, st = float(np.cos(th)), float(np.sin(th))
        cv2.line(jets, (int(x0 * sc), int(y0 * sc)), (int((x0 + ct * L) * sc), int((y0 + st * L) * sc)), 26, 1, cv2.LINE_AA, 4)
        for d in t:
            cx, cy = x0 + ct * d, y0 + st * d
            sz = (13.0 + 40.0 * d / L) * float(r.uniform(0.75, 1.25))
            val = (1.0 - 0.55 * d / L) * float(r.uniform(0.7, 1.0))
            for q in range(3):
                rr = sz * (1 - 0.24 * q)
                cv2.ellipse(arcs, (int(cx * sc), int(cy * sc)), (max(1, int(rr * sc)), max(1, int(rr * 0.78 * sc))),
                            float(np.degrees(th)), -74.0, 74.0, int(255 * val * (1 - 0.18 * q)), 2 if q == 0 else 1, cv2.LINE_AA, 4)
            cv2.circle(knots, (int((cx + ct * sz) * sc), int((cy + st * sz) * sc)), int(sc * 1.4), int(255 * val), -1, cv2.LINE_AA, 4)
    a = arcs.astype(F32) / 255.0
    k = knots.astype(F32) / 255.0
    jt = jets.astype(F32) / 255.0
    I = np.clip(a + k, 0, 1.4)
    Ig = I + 0.7 * H.blur(I, 2.5) + 0.30 * H.blur(I, 7.0)
    ground = H.ramp(0.5 + 0.30 * H.fbm(n, seed + 3, cells=(3, 6, 12, 24, 48)) + 0.12 * H.fbm(n, seed + 4, cells=(96, 192, 384), gain=0.9),
                    [(0.0, '#031418'), (0.45, '#09303a'), (0.8, '#0f5058'), (1.0, '#187080')])
    col = H.ramp(np.clip(Ig * 0.85, 0, 1), [(0.0, '#2a0806'), (0.35, '#c0300c'), (0.7, '#ff7a1c'), (1.0, '#fff0b8')])
    rgb = ground + col * np.clip(Ig * 1.1, 0, 1)[..., None] + jt[..., None] * np.array([0.10, 0.30, 0.34], F32)
    It = np.clip(Ig, 0, 1)
    fl = H.flake_mask(n, 0.07, seed + 11) | (H.flake_mask(n, 0.30, seed + 12) & (It > 0.2))
    M = H.lerp(150.0, 235.0, It)
    R = H.lerp(118.0, 30.0, It)
    CC = H.lerp(34.0, 16.0, It)
    M[fl] = 255.0
    R[fl] = 6.0
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 15. Helix Cometary Knots - thousands of tiny comets, tails away from several centres
# -------------------------------------------------------------------------
def helix_knots(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 15 Helix Cometary Knots: knots arranged on ANNULUS systems (concentric rings around seven centres), tails pointing radially outward, bright cyan-white heads, rust-gold tails, gas halo (wave-2 review: flat blue at 512 -> ring systems, higher contrast)
    n = N
    r = H.rng(seed)
    NA = 48
    Ls = (22, 40, 70, 110)
    sets = []
    for L in Ls:
        S = 2 * L + 9
        gy, gx = np.mgrid[0:S, 0:S].astype(F32)
        a = gx - S // 2
        b = gy - S // 2
        w = 6.2 * (1 - np.clip(a / L, 0, 1)) + 1.1
        tail = np.exp(-np.clip(a, 0, None) / (0.45 * L)) * np.exp(-(b / w) ** 2) * (a >= 0) * (a <= L)
        sets.append(H.rotset(tail.astype(F32), k=NA, span=2 * np.pi))
    cen = np.array([[0.20, 0.22], [0.62, 0.14], [0.90, 0.40], [0.46, 0.50], [0.12, 0.72], [0.74, 0.76], [0.42, 0.92]], F32) * n
    cen += r.normal(0, 40, cen.shape).astype(F32)
    pts, angs, lsel = [], [], []
    for c in range(len(cen)):
        r0 = float(r.uniform(60, 120))
        for ring in range(int(r.integers(3, 5))):
            wd = float(r.uniform(80, 150))
            rr = r0
            while rr < r0 + wd:
                m_ = max(6, int(2 * np.pi * rr / 40.0))
                th0 = r.uniform(0, 2 * np.pi)
                tt = th0 + 2 * np.pi * (np.arange(m_) + r.uniform(-0.3, 0.3, m_)) / m_
                rj = rr + r.normal(0, 4.0, m_)
                pts.append(np.stack([cen[c, 0] + rj * np.cos(tt), cen[c, 1] + rj * np.sin(tt)], 1))
                angs.append(tt)
                f = np.clip((rr - 60.0) / 380.0, 0, 1)
                lsel.append(r.choice(4, m_, p=np.array([0.5 - 0.35 * f, 0.34, 0.12 + 0.2 * f, 0.04 + 0.15 * f]) / (1.0 + 0.0 * f)))
                rr += float(r.uniform(32, 44))
            r0 += wd + float(r.uniform(40, 90))
            if r0 > 620:
                break
    pp = np.concatenate(pts, 0).astype(F32)
    ang = np.concatenate(angs, 0)
    lsel = np.concatenate(lsel, 0)
    keep = (pp[:, 0] > -60) & (pp[:, 0] < n + 60) & (pp[:, 1] > -60) & (pp[:, 1] < n + 60) & (r.random(len(pp)) < 0.92)
    pp, ang, lsel = pp[keep], ang[keep], lsel[keep]
    K = len(pp)
    ai = np.round(np.mod(ang, 2 * np.pi) / (2 * np.pi) * NA).astype(np.int64) % NA
    amp = (0.65 + 0.35 * r.random(K)).astype(F32)
    tails = np.zeros((n, n), F32)
    for c in range(4):
        m = np.where(lsel == c)[0]
        if len(m):
            H.splat(tails, sets[c], ai[m], pp[m, 0], pp[m, 1], amp=amp[m], mode="add")
    heads = np.zeros((n, n), F32)
    H.points(heads, pp[:, 0], pp[:, 1], amp)
    hd = H.blur(heads, 2.2) * 26.0 + H.blur(heads, 5.0) * 18.0 + H.blur(heads, 12.0) * 6.0
    hd = np.clip(hd, 0, 2.4)
    ground = H.ramp(0.5 + 0.30 * H.fbm(n, seed + 3, cells=(3, 6, 12, 24, 48, 96)) + 0.10 * H.fbm(n, seed + 4, cells=(128, 256, 512), gain=0.9),
                    [(0.0, '#050c2a'), (0.5, '#0b1a56'), (1.0, '#1830a0')])
    gasd = H.blur(heads, 34.0) * 160.0
    rgb = ground + np.clip(gasd, 0, 1)[..., None] * np.array([0.05, 0.24, 0.30], F32) * 0.9
    rgb += np.clip(tails, 0, 1.3)[..., None] * np.array([1.0, 0.56, 0.18], F32) * 1.7
    rgb += (H.blur(tails, 5.0) * 1.2)[..., None] * np.array([0.9, 0.35, 0.08], F32)
    rgb += H.tonemap(hd, 1.3)[..., None] * np.array([0.78, 0.97, 1.0], F32)
    # [S19 coordinator polish A 2026-10-12] spec richness: the spec now carries the paint's structure (matte/rough ground with 1 px flake; lines, arcs, cores = satin then mirror metal)
    M, R, CC = H.structure_spec(rgb, seed + 91, [(0.30, 0.55, 190.0, 58.0, 30.0), (0.62, 0.92, 252.0, 6.0, 16.0)],
                                halo=(2.6, 1.8, 120.0, 90.0, 38.0))
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 16. Interstellar Ice Grains - hexagonal plates and needles with prismatic edges
# -------------------------------------------------------------------------
def ice_grains(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 16 Interstellar Ice Grains: poisson hex plates (rainbow edge per facet, glassy fill, glint) and needles with split-hue ends
    n = N
    r = H.rng(seed)
    sh = 3
    sc = float(1 << sh)
    cvs = np.zeros((n, n, 3), np.uint8)
    pp = H.jitter_pts(n, 58.0, seed + 1, jit=0.95, margin=40)
    pp = pp[r.random(len(pp)) < 0.80]
    K = len(pp)
    typ = r.random(K)
    th = r.uniform(0, 2 * np.pi, K)
    h0 = r.random(K)
    rho = r.uniform(11.0, 26.0, K)
    nl = r.uniform(26.0, 70.0, K)
    glass = np.array([64, 84, 110], np.int32)

    def hsv(h, v=255, s=0.80):
        c = cv2.cvtColor(np.array([[[int((h % 1.0) * 179), int(s * 255), v]]], np.uint8), cv2.COLOR_HSV2RGB)[0, 0]
        return (int(c[0]), int(c[1]), int(c[2]))

    for i in range(K):
        x, y = float(pp[i, 0]), float(pp[i, 1])
        t = float(th[i])
        if typ[i] < 0.62:
            R_ = float(rho[i])
            P = np.array([[x + R_ * np.cos(t + k * np.pi / 3), y + R_ * np.sin(t + k * np.pi / 3)] for k in range(6)])
            pi_ = np.round(P * sc).astype(np.int32).reshape(-1, 1, 2)
            cv2.fillConvexPoly(cvs, pi_, (int(glass[0]), int(glass[1]), int(glass[2])), cv2.LINE_AA, sh)
            tk = 2 if R_ > 15.0 else 1
            for k in range(6):
                a_, b_ = pi_[k], pi_[(k + 1) % 6]
                cv2.line(cvs, (int(a_[0][0]), int(a_[0][1])), (int(b_[0][0]), int(b_[0][1])), hsv(float(h0[i]) + k / 6.0), tk, cv2.LINE_AA, sh)
            q = np.round(P[int(typ[i] * 97) % 6] * sc).astype(np.int32)
            cv2.line(cvs, (int(x * sc), int(y * sc)), (int(q[0]), int(q[1])), (255, 255, 255), 1, cv2.LINE_AA, sh)
        else:
            L = float(nl[i])
            dx, dy = np.cos(t) * L / 2, np.sin(t) * L / 2
            m0 = (int(x * sc), int(y * sc))
            cv2.line(cvs, (int((x - dx) * sc), int((y - dy) * sc)), m0, hsv(float(h0[i])), 1, cv2.LINE_AA, sh)
            cv2.line(cvs, m0, (int((x + dx) * sc), int((y + dy) * sc)), hsv(float(h0[i]) + 0.45), 1, cv2.LINE_AA, sh)
            cv2.line(cvs, (int((x - dx * 0.5) * sc), int((y - dy * 0.5) * sc)), (int((x + dx * 0.5) * sc), int((y + dy * 0.5) * sc)), (255, 255, 255), 1, cv2.LINE_AA, sh)
    g = cvs.astype(F32) / 255.0
    ground = H.ramp(0.5 + 0.30 * H.fbm(n, seed + 3, cells=(3, 6, 12, 24, 48, 96)) + 0.08 * H.fbm(n, seed + 4, cells=(160, 320, 640), gain=0.9),
                    [(0.0, '#04060e'), (0.5, '#0a1020'), (1.0, '#16223a')])
    st = np.zeros((n, n), F32)
    H.points(st, r.integers(0, n, 3500), r.integers(0, n, 3500), 0.3 + 0.7 * r.random(3500))
    mx = g.max(-1)
    rgb = ground + g * 1.15 + 0.7 * H.blur(g, 1.4) + st[..., None] * np.array([0.8, 0.85, 1.0], F32)
    I = np.clip(mx * 1.1, 0, 1)
    fl = H.flake_mask(n, 0.05, seed + 11) & (I > 0.45)
    M = H.lerp(24.0, 255.0, H.sstep(0.12, 0.6, I))
    R = H.lerp(58.0, 4.0, I)
    CC = H.lerp(26.0, 16.0, H.sstep(0.05, 0.35, I))
    M[fl] = 255.0
    R[fl] = 0.0
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 17. Ionization Front - bright edge where magenta gas eats a dark cloud
# -------------------------------------------------------------------------
def ionization_front(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 17 Ionization Front: domain-warped fbm + diagonal finger noise, zero-set bright rim, glowing magenta ion side vs textured neutral cloud
    n = N
    z = H.fbm(n, seed + 1, cells=(2, 4, 8, 16, 32), gain=0.62)
    dx = 60.0 * H.fbm(n, seed + 2, cells=(3, 6, 12))
    dy = 60.0 * H.fbm(n, seed + 3, cells=(3, 6, 12))
    z = H.warp(z, dx, dy)
    z = z + 0.55 * _snoise(7, 74, seed + 9, ang=0.62) + 0.20 * H.fbm(n, seed + 8, cells=(40, 80, 160), gain=0.8)
    ion = H.sstep(-0.03, 0.03, z)
    rim = H.zero_set_line(z, 2.4)
    rim2 = H.zero_set_line(z, 10.0) * 0.35
    zp = np.clip(z, 0, 3.0)
    bi = 0.28 + 0.66 * np.exp(-zp / 0.55) + 0.10 * H.fbm(n, seed + 4, cells=(64, 128, 256, 512), gain=0.85)
    ioncol = H.ramp(np.clip(bi, 0, 1), [(0.0, '#40104a'), (0.45, '#a41a94'), (0.8, '#ff4ccc'), (1.0, '#ffcdf2')])
    dt = np.clip(0.5 + 0.40 * H.fbm(n, seed + 5, cells=(24, 48, 96, 192, 384), gain=0.85) + 0.18 * H.ridged(H.fbm(n, seed + 6, cells=(32, 64, 128), gain=0.8)), 0, 1)
    deep = 0.62 + 0.38 * H.sstep(-1.3, 0.0, z)
    neut = H.ramp(dt, [(0.0, '#100a16'), (0.55, '#2a1c2e'), (1.0, '#5a4060')]) * deep[..., None]
    neut += (0.30 * np.exp(np.clip(z, -9, 0) / 0.18) * (1 - ion))[..., None] * np.array([0.55, 0.16, 0.30], F32)
    rgb = ion[..., None] * ioncol + (1 - ion)[..., None] * neut
    rgb += rim[..., None] * np.array([1.0, 0.82, 0.96], F32) + (rim2 * ion)[..., None] * np.array([0.9, 0.2, 0.7], F32) * 0.4
    lm = np.clip(H.lum(np.clip(rgb, 0, 1)) / 0.6, 0, 1)
    M = np.clip(H.lerp(5.0, 70.0, ion) + 190.0 * rim, 0, 255)
    R = H.lerp(228.0, 22.0, H.sstep(0.05, 0.55, lm))
    R = np.minimum(R, H.lerp(R, 6.0, rim))
    CC = H.lerp(255.0, 16.0, np.maximum(ion * 0.9, rim))
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 18. Emission Spectra - stacked slit strips with sharp coloured lines
# -------------------------------------------------------------------------
def emission_spectra(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 18 Emission Spectra: per-strip 1-D emission-line profile (H-alpha red, OIII green, H-beta blue ...) looked up through a per-strip shear, dim rainbow continuum, fine grain
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)
    rgb = np.zeros((n, n, 3), F32)
    Ii = np.zeros((n, n), F32)
    Sm = np.zeros((n, n), F32)
    pal = np.array([[1.0, 0.10, 0.08], [1.0, 0.50, 0.08], [1.0, 0.86, 0.20], [0.25, 1.0, 0.35],
                    [0.10, 0.92, 0.92], [0.20, 0.42, 1.0], [0.62, 0.20, 1.0]], F32)
    pad = 320
    xs1 = np.arange(-pad, n + pad, dtype=F32)
    cont_base = H.ramp(np.clip((xs1 + pad) / (n + 2 * pad), 0, 1)[None, :],
                       [(0.0, '#a01020'), (0.2, '#c06a10'), (0.4, '#a0b020'), (0.6, '#20a860'), (0.8, '#2060c0'), (1.0, '#7020b0')])[0]
    fine = H.fbm(n, seed + 5, cells=(256, 512, 1024), gain=0.9)
    y = 0
    while y < n:
        h = int(r.integers(44, 118))
        gap = int(r.integers(5, 12))
        sh = float(r.uniform(-0.16, 0.16))
        P = np.zeros((len(xs1), 3), F32)
        Pi = np.zeros(len(xs1), F32)
        for _ in range(int(r.integers(22, 46))):
            p = float(r.uniform(-pad, n + pad))
            w = float(r.choice([1.2, 1.8, 2.6, 3.6]))
            a = float(r.uniform(0.35, 1.0) ** 1.3)
            prof = (a * np.exp(-((xs1 - p) / w) ** 2)).astype(F32)
            P += prof[:, None] * pal[int(r.integers(0, 7))]
            Pi = np.maximum(Pi, prof)
        sm = cv2.resize(r.standard_normal(40).astype(F32)[None, :], (len(xs1), 1), interpolation=cv2.INTER_CUBIC)[0]
        cont = cont_base * (0.12 + 0.12 * np.clip(sm * 0.5 + 0.5, 0, 1))[:, None]
        y1 = min(y + h, n)
        Yb = Y[y:y1]
        Xb = X[y:y1]
        U = np.clip((Xb - sh * (Yb - (y + h / 2.0)) + pad).astype(np.int32), 0, len(xs1) - 1)
        mod = 1.0 + 0.30 * fine[y:y1]
        ve = H.sstep(0.0, 3.5, np.minimum(Yb - y, (y1 - 1) - Yb))
        blk = (P[U] * 1.8 + cont[U]) * (mod * ve)[..., None]
        rgb[y:y1] = blk
        Ii[y:y1] = np.clip(Pi[U] * mod * ve, 0, 1.2)
        Sm[y:y1] = ve
        y = y1 + gap
    rgb += 0.012
    Ig = np.clip(Ii + 0.4 * H.blur(Ii, 1.6), 0, 1)
    rgb = rgb + 0.35 * H.blur(rgb, 2.2)
    M = H.lerp(8.0, H.lerp(205.0, 250.0, Ig), Sm)
    R = H.lerp(236.0, H.lerp(72.0, 8.0, Ig), Sm)
    CC = H.lerp(255.0, H.lerp(32.0, 16.0, Ig), Sm)
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 19. Stardust Aggregates - fluffy dendritic comet-dust grains
# -------------------------------------------------------------------------
def _agg_tile(S, npts, rg):
    """Fluffy dendritic aggregate: branching walk with persistence (a cheap stand-in for a DLA cluster)."""
    c = S / 2.0
    P = np.zeros((npts, 2))
    D = np.zeros(npts)
    P[0] = (c, c)
    D[0] = rg.uniform(0, 2 * np.pi)
    par = np.zeros(npts, np.int64)
    for i in range(1, npts):
        j = max(0, i - 1 - int(rg.exponential(3.0)))
        a = D[j] + rg.uniform(-1.25, 1.25)
        P[i] = P[j] + 2.3 * np.array([np.cos(a), np.sin(a)])
        D[i] = a
        par[i] = j
    P += c - 0.5 * (P.min(0) + P.max(0))
    t = np.zeros((S, S), np.float32)
    for i in range(1, npts):
        cv2.line(t, (int(P[par[i]][0] * 8), int(P[par[i]][1] * 8)), (int(P[i][0] * 8), int(P[i][1] * 8)), 0.55, 1, cv2.LINE_AA, 3)
    for i in range(npts):
        cv2.circle(t, (int(P[i][0] * 8), int(P[i][1] * 8)), int(8 * (0.9 + 0.7 * rg.random())), 1.0, -1, cv2.LINE_AA, 3)
    return cv2.GaussianBlur(t, (0, 0), 0.55)


def stardust_aggregate(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 19 Stardust Aggregates: precomputed fluffy dendritic grain tiles (three sizes) stamped with rotation, bronze-gold on smoke; brushed short-streak spec
    n = N
    r = H.rng(seed)
    rg = np.random.default_rng(seed + 77)
    sets = []
    for (S, npts) in ((41, 46), (57, 78), (79, 130)):
        sets.append([t for _ in range(8) for t in [H.rotset(_agg_tile(S, npts, rg), k=9, span=2 * np.pi)]])
    pp = H.jitter_pts(n, 36.0, seed + 1, jit=0.95, margin=30)
    pp = pp[r.random(len(pp)) < 0.66]
    K = len(pp)
    size = r.choice(3, K, p=[0.50, 0.34, 0.16])
    tone = r.random(K).astype(F32)[:, None]
    col = (np.array([0.56, 0.32, 0.12], F32)[None, :] * (1 - tone) + np.array([1.0, 0.80, 0.34], F32)[None, :] * tone).astype(F32)
    amp = (0.65 + 0.55 * r.random(K)).astype(F32)
    gr = np.zeros((n, n, 3), F32)
    gi = np.zeros((n, n), F32)
    for c in range(3):
        m = np.where(size == c)[0]
        if not len(m):
            continue
        flat = [t for st_ in sets[c] for t in st_]
        ti = r.integers(0, len(flat), len(m))
        H.splat(gr, flat, ti, pp[m, 0], pp[m, 1], amp=amp[m], col=col[m], mode="add")
        H.splat(gi, flat, ti, pp[m, 0], pp[m, 1], amp=amp[m], mode="add")
    ground = H.ramp(0.5 + 0.30 * H.fbm(n, seed + 3, cells=(4, 8, 16, 32, 64)) + 0.10 * H.fbm(n, seed + 4, cells=(128, 256, 512), gain=0.9),
                    [(0.0, '#0d0a08'), (0.5, '#201812'), (1.0, '#3a2c20')])
    rgb = ground + gr * 1.15 + 0.5 * H.blur(gr, 2.0)
    It = np.clip(gi * 0.9, 0, 1)
    sb = _snoise(900, 70, seed + 9)
    M = H.lerp(8.0, 215.0, It)
    R = H.lerp(212.0, 58.0, It) + 30.0 * sb * It
    CC = H.lerp(255.0, 30.0, It)
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 20. Wolf-Rayet Wind Bubbles - overlapping thin iridescent shells
# -------------------------------------------------------------------------
def wind_bubbles(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 20 Wolf-Rayet Wind Bubbles: random rings summed over four canvases (overlaps add), warped turbulent walls, thin-film cosine palette, faint filled interiors
    n = N
    r = H.rng(seed)
    walls = [np.zeros((n, n), np.uint8) for _ in range(4)]
    fills = [np.zeros((n, n), np.uint8) for _ in range(4)]
    K = 190
    cx = r.uniform(-40, n + 40, K)
    cy = r.uniform(-40, n + 40, K)
    rad = np.exp(r.uniform(np.log(38.0), np.log(210.0), K))
    for i in range(K):
        w = int(r.choice([2, 3, 3, 4]))
        H.circles_u8(n, [cx[i]], [cy[i]], [rad[i]], [int(r.integers(150, 256))], thick=w, canvas=walls[i % 4])
        H.circles_u8(n, [cx[i]], [cy[i]], [rad[i]], [40], thick=-1, canvas=fills[i % 4])
    I = sum(w_.astype(F32) for w_ in walls) / 255.0
    Fi = sum(f_.astype(F32) for f_ in fills) / 40.0
    dx = 7.0 * H.fbm(n, seed + 2, cells=(24, 48, 96, 192), gain=0.8)
    dy = 7.0 * H.fbm(n, seed + 3, cells=(24, 48, 96, 192), gain=0.8)
    I = H.warp(I, dx, dy)
    Fi = H.warp(Fi, dx * 0.4, dy * 0.4)
    I = I * (0.62 + 0.38 * np.clip(0.5 + 0.5 * H.fbm(n, seed + 4, cells=(200, 400, 800), gain=0.9), 0, 1))
    Ig = I + 0.9 * H.blur(I, 2.0) + 0.4 * H.blur(I, 6.0)
    phi = 0.9 * H.fbm(n, seed + 5, cells=(3, 6, 12), gain=0.6) + 0.4 * I
    ph = phi[..., None] + np.array([0.0, 0.18, 0.40], F32)
    colr = np.array([0.45, 0.45, 0.50], F32) + np.array([0.45, 0.45, 0.45], F32) * np.cos(2 * np.pi * ph)
    ground = H.ramp(0.5 + 0.30 * H.fbm(n, seed + 6, cells=(4, 8, 16, 32, 64, 128)), [(0.0, '#030708'), (0.5, '#08120f'), (1.0, '#0f2420')])
    rgb = ground + np.clip(Fi, 0, 4)[..., None] * 0.045 * np.array([0.35, 0.8, 0.9], F32) + Ig[..., None] * colr * 1.2
    It = H.tonemap(Ig, 1.1)
    M = H.lerp(100.0, 225.0, It)
    R = H.lerp(126.0, 44.0, It)
    CC = H.lerp(112.0, 50.0, It)
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


FINISHES = [
    ("cz_pillars", "Pillars of Creation",
     "Jagged dark-brown dust spires in several sizes, striped with vertical teal and gold gas streaks.", pillars),
    ("cz_bok_globules", "Bok Globules",
     "Ink-black cloud globules with bright pink-white rims scattered over mottled magenta H-alpha haze.", bok_globules),
    ("cz_veil_strands", "Veil Nebula Strands",
     "Thousands of hair-thin cyan, crimson and white strands combed and braided across dark space.", veil_strands),
    ("cz_bow_shocks", "Herbig-Haro Bow Shocks",
     "Chains of nested orange crescent shocks marching along hidden jets over dark teal.", bow_shocks),
    ("cz_helix_knots", "Helix Cometary Knots",
     "Thousands of tiny cream-gold comets with fading tails streaming outward from several centres over deep indigo.", helix_knots),
    ("cz_ice_grains", "Interstellar Ice Grains",
     "Tiny glassy hexagon plates and needles with rainbow edges and sparkle on dark slate.", ice_grains),
    ("cz_ionization_front", "Ionization Front",
     "Glowing magenta gas with a crisp bright edge, eating diagonal teeth into a textured black cloud.", ionization_front),
    ("cz_emission_spectra", "Emission Spectra",
     "Stacked slit strips of black crossed by sharp red, green, blue and violet emission lines.", emission_spectra),
    ("cz_stardust_aggregate", "Stardust Aggregates",
     "Fluffy fractal comet-dust grains in bronze and gold scattered on smoke.", stardust_aggregate),
    ("cz_wind_bubbles", "Wolf-Rayet Wind Bubbles",
     "Overlapping thin turbulent shells in iridescent cyan, gold and pink on dark teal, brighter where they cross.", wind_bubbles),
]
