# -*- coding: utf-8 -*-
"""STELLAR chapter (cz_ 1-10): the sun, its spots and loops, and what stars die into.

[S19 2026-10-12 owner: Fractured Cosmos rebuild] one function per finish; each
writes its OWN structure and its OWN spec story. Only plumbing comes from helpers.
"""
from __future__ import annotations

import numpy as np
import cv2

from . import helpers as H

F32 = np.float32
N = H.N


# -------------------------------------------------------------------------
# 1. Solar Granulation - bright convection cells split by dark lanes
# -------------------------------------------------------------------------
def solar_granulation(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 1 Solar Granulation: Voronoi granules, per-cell brightness, dark intergranular lanes
    n = N
    pts = H.jitter_pts(n, 17.0, seed, jit=0.95, margin=20)
    d, lab, sx, sy = H.voronoi(n, pts)
    K = len(sx)
    r = H.rng(seed + 1)
    cb = np.concatenate([[0.0], 0.40 + 0.60 * r.random(K)]).astype(F32)
    hole = np.concatenate([[0.0], (r.random(K) < 0.07).astype(F32)])      # exploding granules
    reg = H.fbm(n, seed + 2, cells=(3, 6, 12))
    e = H.edge_dist(lab)
    prof = H.sstep(0.0, 6.5, e)                      # plateau inside, falling to the lane
    lane = 1.0 - H.sstep(0.55, 2.3, e)
    b = cb[lab] * (0.52 + 0.48 * prof)
    b *= (1.0 + 0.10 * reg)
    fine = H.fbm(n, seed + 3, cells=(160, 320, 640, 1024), gain=0.9)
    b += 0.075 * fine * (1.0 - lane)
    b -= hole[lab] * np.exp(-(d / 2.8) ** 2) * 0.55
    b *= (1.0 - 0.92 * lane)
    b = np.clip(b, 0, 0.985)
    rgb = H.ramp(b, [(0.0, '#2a1006'), (0.22, '#6e2c0b'), (0.48, '#c4571a'),
                     (0.72, '#f2a33a'), (0.88, '#ffd98a'), (1.0, '#fff1c4')])
    M = H.lerp(125.0, 185.0, b)
    R = H.lerp(112.0, 66.0, b)
    CC = H.lerp(62.0, 30.0, b)
    M = H.lerp(M, 14.0, lane)
    R = H.lerp(R, 218.0, lane)
    CC = H.lerp(CC, 190.0, lane)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 2. Sunspot Penumbra - black umbra, radial filament penumbra, over mottle
# -------------------------------------------------------------------------
def sunspot_penumbra(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 2 Sunspot Penumbra: poisson spots, polar-noise radial fibrils
    n = N
    gz = H.fbm(n, seed, cells=(40, 90, 180, 360, 720), gain=0.85)
    gz2 = H.fbm(n, seed + 9, cells=(5, 10, 20))
    t = np.clip(0.52 + 0.17 * gz + 0.05 * gz2, 0, 1)
    rgb = H.ramp(t, [(0.0, '#4a1c06'), (0.35, '#9a4a12'), (0.6, '#d8832a'), (0.85, '#f6bf62'), (1.0, '#ffe3a0')])
    M = H.lerp(110.0, 150.0, t)
    R = H.lerp(125.0, 88.0, t)
    CC = np.full((n, n), 48.0, F32)
    r = H.rng(seed + 4)
    # master periodic polar fibril image: 48 radial x 640 angular, 40 cycles around
    g = r.standard_normal((9, 40)).astype(F32)
    gp = np.pad(g, ((0, 0), (3, 3)), mode='wrap')
    big = cv2.resize(gp, ((40 + 6) * 16, 9 * 6), interpolation=cv2.INTER_CUBIC)
    P = np.ascontiguousarray(big[:, 3 * 16:3 * 16 + 640])
    ring = cv2.resize(np.pad(r.standard_normal(6).astype(F32), (3, 3), mode='wrap')[None, :],
                      ((6 + 6) * 60, 1), interpolation=cv2.INTER_CUBIC)[0][3 * 60:3 * 60 + 360]
    spots = []
    for sp, keep, rlo, rhi in ((250.0, 0.88, 38.0, 100.0), (118.0, 0.55, 11.0, 24.0)):
        pp = H.jitter_pts(n, sp, r.integers(1 << 30), jit=0.85, margin=60)
        pp = pp[r.random(len(pp)) < keep]
        for (x, y) in pp:
            Rr_ = r.uniform(rlo, rhi)
            spots.append((x, y, Rr_, int(np.clip(round(Rr_ / 22.0), 1, 5)), int(r.integers(0, 360)),
                          r.uniform(0.9, 1.35)))
    for (x, y, Rr, k, off, amp) in spots:
        E = int(Rr * 1.5) + 2
        x0, y0 = int(round(x)) - E, int(round(y)) - E
        sx0, sy0 = max(0, -x0), max(0, -y0)
        ex, ey = min(2 * E + 1, n - x0), min(2 * E + 1, n - y0)
        if ex <= sx0 or ey <= sy0:
            continue
        gy, gx = np.mgrid[-E:E + 1, -E:E + 1].astype(F32)
        rad = np.hypot(gx, gy)
        th = np.arctan2(gy, gx)
        fr = (th + np.pi) / (2 * np.pi)
        ridx = (fr * 360 + off).astype(np.int32) % 360
        rn = rad / (Rr * (1.0 + 0.20 * ring[ridx]))
        mx = (((fr * k) % 1.0) * 640.0).astype(F32)
        my = np.clip(rn, 0, 1.2) * F32(40.0)
        fib = cv2.remap(P, mx, my.astype(F32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        fv = H.sstep(-0.9, 1.1, fib)
        alpha = 1.0 - H.sstep(0.97, 1.07, rn)
        umb = 1.0 - H.sstep(0.36, 0.46, rn)
        pen = alpha * (1.0 - umb)
        shade = (0.30 + 0.70 * fv) * (0.60 + 0.40 * H.sstep(0.40, 0.95, rn)) * amp
        col = H.ramp(np.clip(shade, 0, 1), [(0.0, '#050201'), (0.25, '#4a1d08'), (0.55, '#a8581a'),
                                            (0.8, '#e3993c'), (1.0, '#ffd88a')])
        col = col * (1.0 - umb)[..., None]
        dots = (r.random(umb.shape) < 0.004).astype(F32) * umb
        col += dots[..., None] * F32(0.5)
        sl = (slice(y0 + sy0, y0 + ey), slice(x0 + sx0, x0 + ex))
        tl = (slice(sy0, ey), slice(sx0, ex))
        a = alpha[tl][..., None]
        rgb[sl] = rgb[sl] * (1 - a) + col[tl] * a
        # spec: umbra WET black, penumbra BRU streaked with the fibrils
        a2 = alpha[tl]
        u2 = umb[tl]
        pm = pen[tl]
        Mw = M[sl]
        Rw = R[sl]
        Cw = CC[sl]
        Mw[:] = Mw * (1 - a2) + (22.0 * u2 + (205.0 - 30.0 * (1 - fv[tl])) * pm)
        Rw[:] = Rw * (1 - a2) + (14.0 * u2 + (46.0 + 78.0 * (1 - fv[tl])) * pm)
        Cw[:] = Cw * (1 - a2) + (16.0 * u2 + 30.0 * pm)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 3. Coronal Loops - hundreds of glowing magnetic arcades on black
# -------------------------------------------------------------------------
def coronal_loops(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 3 Coronal Loops: parametric half-ellipse arcades + gaussian glow
    n = N
    r = H.rng(seed)
    K = 3800
    cx = r.random(K) * n
    cy = r.random(K) * n
    a = np.exp(r.uniform(np.log(7.0), np.log(62.0), K))
    b = a * r.uniform(0.45, 1.6, K)
    phi = r.random(K) * np.pi * 2
    bright = np.clip(r.beta(1.6, 1.8, K) * 255, 40, 255)
    t = np.linspace(0, np.pi, 26)
    polys, vals, foot = [], [], []
    for i in range(K):
        for s, vm in ((1.0, 1.0), (0.78, 0.8), (0.58, 0.65)):
            if s < 1.0 and r.random() > 0.50:
                continue
            ex = a[i] * s * np.cos(t)
            ey = b[i] * s * np.sin(t) * (1 + 0.12 * np.sin(2 * t + i))
            c, sn = np.cos(phi[i]), np.sin(phi[i])
            px = cx[i] + ex * c - ey * sn
            py = cy[i] + ex * sn + ey * c
            polys.append(np.stack([px, py], 1))
            vals.append(bright[i] * vm)
        foot.append((cx[i] + a[i] * np.cos(phi[i]), cy[i] + a[i] * np.sin(phi[i]), bright[i]))
        foot.append((cx[i] - a[i] * np.cos(phi[i]), cy[i] - a[i] * np.sin(phi[i]), bright[i]))
    core = H.lines_u8(n, polys, vals, thick=1).astype(F32) / 255.0
    fx = np.array([f[0] for f in foot])
    fy = np.array([f[1] for f in foot])
    fv = np.array([f[2] for f in foot], F32) / 255.0
    dots = np.zeros((n, n), F32)
    H.points(dots, fx, fy, fv)
    I = core * 0.9 + H.blur(dots, 1.4) * 4.0
    I += 1.1 * H.blur(core, 1.6) + 0.9 * H.blur(core, 4.5) + 0.7 * H.blur(core, 12.0)
    I = I * 1.15
    plage = 0.05 + 0.035 * H.fbm(n, seed + 3, cells=(4, 9, 20))
    I = H.tonemap(I + plage, 1.0)
    rgb = H.ramp(I, [(0.0, '#2a0a10'), (0.10, '#4a0c10'), (0.26, '#92150c'), (0.45, '#e04c12'),
                     (0.66, '#ffb12c'), (0.84, '#fff0b6'), (1.0, '#ffffff')])
    s = H.sstep(0.20, 0.60, I)
    M = H.lerp(8.0, 252.0, s)
    R = H.lerp(210.0, 6.0, s)
    CC = H.lerp(200.0, 16.0, s)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 4. Flare Ribbons - paired ribbons running along curl-field streamlines
# -------------------------------------------------------------------------
def flare_ribbons(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 4 Flare Ribbons: streamline pairs of a curl field, offset +-d along the normal
    n = N
    r = H.rng(seed)
    u, v = H.curl_field(512, seed + 1, cells=(3, 5, 9), gain=0.75)
    K = 1500
    p0 = r.random((K, 2)).astype(F32) * n
    fw = H.trace(u, v, p0, 36, 5.5)
    bw = H.trace(-u, -v, p0, 36, 5.5)
    path = np.concatenate([bw[:, ::-1][:, :-1], fw], 1)            # (K, 73, 2)
    tang = np.gradient(path, axis=1)
    tn = np.hypot(tang[..., 0], tang[..., 1])[..., None] + F32(1e-6)
    nor = np.stack([-tang[..., 1], tang[..., 0]], -1) / tn
    d0 = r.uniform(2.6, 7.5, K).astype(F32)
    sw = np.linspace(-1, 1, path.shape[1], dtype=F32)
    taper = (0.45 + 0.55 * np.cos(sw * np.pi * 0.5))[None, :, None]
    off = nor * d0[:, None, None] * taper
    A = path + off
    B = path - off
    val = np.clip(r.beta(2.0, 1.6, K) * 255, 70, 255)
    rib = H.lines_u8(n, list(A) + list(B), np.concatenate([val, val]), thick=2)
    core = H.lines_u8(n, list(path), val * 0.35, thick=1).astype(F32) / 255.0
    rb = rib.astype(F32) / 255.0
    I = rb + 0.5 * core + 0.55 * H.blur(rb, 1.8) + 0.4 * H.blur(rb, 5.0) + 0.3 * H.blur(rb, 16.0)
    ground = 0.10 + 0.05 * H.fbm(n, seed + 5, cells=(3, 7, 14, 30))
    I = H.tonemap(I * 1.2 + ground * 0.6, 1.1)
    rgb = H.ramp(I, [(0.0, '#2a1250'), (0.14, '#341263'), (0.34, '#7a1a9e'), (0.55, '#d92fb8'),
                     (0.76, '#ff82e2'), (0.92, '#ffe4f7'), (1.0, '#ffffff')])
    s = H.sstep(0.22, 0.62, I)
    M = H.lerp(40.0, 228.0, s)
    R = H.lerp(185.0, 20.0, s)
    CC = H.lerp(95.0, 16.0, s)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 5. Pulsar Beacons - twin lighthouse cones + timing rings around hot dots
# -------------------------------------------------------------------------
def pulsar_beacons(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 5 Pulsar Beacons: tiny hot point + TWO opposed narrow beam cones (bright core, soft cone glow, 70-330 px, random angles, crossing) + 2-4 faint timing-ring ARCS that break where the beams pass (wave-2 review: circle+bar read as a NO sign)
    n = N
    r = H.rng(seed)
    # [S19 coordinator polish B 2026-10-12] last try: fewer, longer beam pairs through a CLEARLY VISIBLE bright star (white-hot disc + wide bloom) so each reads as one pulsar, not needles
    pp = H.jitter_pts(n, 214.0, seed + 1, jit=0.85, margin=80)
    pp = pp[r.random(len(pp)) < 0.85]
    K = len(pp)
    Ls = (100, 150, 200)
    NA = 36
    sets = {}
    for L in Ls:
        S = 2 * L + 13
        gy, gx = np.mgrid[0:S, 0:S].astype(F32)
        a = np.abs(gx - S // 2)
        b = gy - S // 2
        fall = np.clip(1 - a / L, 0, 1)
        core = np.exp(-(b / (1.6 + 0.04 * a)) ** 2) * fall ** 1.2 * (1.0 + 2.5 * np.exp(-a / 9.0))
        halo = np.exp(-(b / (5.0 + 0.19 * a)) ** 2) * fall ** 1.6 * 0.55
        sets[L] = H.rotset((core * 0.8 + halo * 1.2).astype(F32), k=NA)
    lens = r.choice(Ls, K, p=[0.30, 0.40, 0.30])
    ai = r.integers(0, NA, K)
    tq = r.random(K).astype(F32)[:, None]
    cols = (np.array([0.30, 0.62, 1.0], F32)[None, :] * (1 - tq)
            + np.array([0.60, 0.97, 1.0], F32)[None, :] * tq).astype(F32)
    beams = np.zeros((n, n, 3), F32)
    for L in Ls:
        idx = np.where(lens == L)[0]
        if not len(idx):
            continue
        H.splat(beams, sets[L], ai[idx], pp[idx, 0], pp[idx, 1],
                amp=0.55 + 0.6 * r.random(len(idx)), col=cols[idx], mode="add")
    # timing rings: arcs on the equator side only (beam axis +-35 deg is left open), so no ring is ever crossed by a bar
    rings = np.zeros((n, n), np.uint8)
    sc = 16
    for i in range(K):
        if r.random() > 0.50:
            continue
        beta = -180.0 * ai[i] / NA
        nrg = int(r.integers(2, 5))
        rad = 20.0 + 8.0 * r.random()
        for j in range(nrg):
            v = int(205 - 28 * j)
            c0 = (int(round(pp[i, 0] * sc)), int(round(pp[i, 1] * sc)))
            ax = (int(rad * sc), int(rad * sc))
            for off in (0.0, 180.0):
                cv2.ellipse(rings, c0, ax, 0, beta + off + 38.0, beta + off + 142.0, v, 1, cv2.LINE_AA, 4)
            rad += 12.0 + 7.0 * r.random()
    rg = rings.astype(F32) / 255.0
    dots = np.zeros((n, n), F32)
    # [S19 coordinator fix 2026-10-12] pulsar read as scattered needles -> every beam pair gets a bright point source with a soft 25 px glow
    H.points(dots, pp[:, 0], pp[:, 1], (0.90 + 0.45 * r.random(K)).astype(F32))
    core = H.blur(dots, 3.4) * 170.0 + H.blur(dots, 8.0) * 520.0 + H.blur(dots, 18.0) * 700.0 + H.blur(dots, 40.0) * 330.0
    core += (cv2.GaussianBlur(dots, (0, 0), sigmaX=16.0, sigmaY=0.9) + cv2.GaussianBlur(dots, (0, 0), sigmaX=0.9, sigmaY=16.0)) * 34.0   # 4-spike star flare
    ground = H.ramp(0.5 + 0.28 * H.fbm(n, seed + 3, cells=(4, 9, 20, 44, 90)),
                    [(0.0, '#070c20'), (0.5, '#0b1330'), (1.0, '#142650')])
    ringc = (rg * 0.50 + H.blur(rg, 1.8) * 0.45)[..., None] * np.array([0.38, 0.66, 1.0], F32)
    NSD = 110000
    sdf = np.zeros((n, n), F32)
    H.points(sdf, r.integers(0, n, NSD), r.integers(0, n, NSD), (0.25 + 0.75 * r.random(NSD) ** 1.8).astype(F32))
    sdf = H.blur(sdf, 2.0) * 9.0
    rgb = ground + beams * 1.35 + ringc + (sdf * 0.80)[..., None] * np.array([0.70, 0.84, 1.0], F32)
    rgb += H.tonemap(core, 1.0)[..., None] * np.array([0.88, 0.96, 1.0], F32)
    rgb = H.tonemap(rgb, 1.5)
    # [S19 coordinator polish A+B 2026-10-12] spec carries the stars, cones and flare in satin then mirror metal over a matte flaked ground
    M, R, CC = H.structure_spec(rgb, seed + 91, [(0.26, 0.48, 190.0, 55.0, 28.0), (0.60, 0.95, 252.0, 4.0, 16.0)],
                                ground_m=(14.0, 64.0), ground_r=(150.0, 205.0), ground_cc=110.0, halo=(3.0, 1.6, 120.0, 100.0, 50.0), grain=0.8)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 6. Crystallized Star Core - 5-fold pentagrid quasicrystal facets
# -------------------------------------------------------------------------
def _pentagrid(n, lam, seed, base, need_fr=True):
    """de Bruijn pentagrid: 5 line families at 72 deg steps (rotated by `base`). Returns (int32 line indices, float32 fractional positions)."""
    r = H.rng(seed)
    X, Y = H.xy(n)
    g = r.random(5)
    frs, ns = [], []
    tmp = np.empty((n, n), F32)
    for j in range(5):
        ang = 2 * np.pi * j / 5 + base
        s = X * F32(np.cos(ang) / lam)
        np.multiply(Y, F32(np.sin(ang) / lam), out=tmp)
        s += tmp
        s += F32(g[j] * 3.7)
        nj = np.floor(s)
        if need_fr:
            s -= nj
            frs.append(s)
        ns.append(nj.astype(np.int32))
    return ns, frs


def _facet_hash(ns, salt):
    x = ns[0] * np.int32(73856093)
    x ^= ns[1] * np.int32(19349663)
    x ^= ns[2] * np.int32(83492791)
    x ^= ns[3] * np.int32(2654435761 - (1 << 32))
    x ^= ns[4] * np.int32(40503)
    return H.hash01(x.view(np.uint32), salt)


def _segment_edges(ns, frs, lam, seed, width=0.85):
    """Bright facet edges, but each SEGMENT (a line piece between crossings) gets its own random
    brightness, so no line runs the whole canvas as one straight seam."""
    n = ns[0].shape[0]
    edge = np.zeros(n * n, F32)
    thr = 2.2 * width / lam
    for j in range(5):
        fj = frs[j]
        idx = np.nonzero((np.abs(fj - F32(0.5)) > F32(0.5 - thr)).ravel())[0]
        if not len(idx):
            continue
        fv = fj.ravel()[idx]
        dd = np.minimum(fv, 1 - fv) * F32(lam)
        line = ns[j].ravel()[idx].astype(np.int64) + (fv >= 0.5)
        key = line + 977 * j
        for k in (1, 2, 3):
            key = key * 131 + ns[(j + k) % 5].ravel()[idx]
        h = H.hash01((key & 0xFFFFFFFF).astype(np.uint32), seed + j)
        vis = H.sstep(0.30, 0.92, h)
        edge[idx] = np.maximum(edge[idx], np.exp(-(dd / F32(width)) ** 2) * vis)
    return edge.reshape(n, n)


def crystal_core(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 6 Crystallized Star Core: THREE pentagrid scales (macro 150 px at half res, 62, 26) -> bold macro facets read at 512, mid + fine facets at 1:1; per-facet jitter; edges broken per segment; spec = per-level roughness steps (round-2 wave-1 review: blotchy at 512 -> macro facets)
    n = N
    n2 = n // 2
    nsM, frM = _pentagrid(n2, 75.0, seed + 41, 0.14)
    nsB, frB = _pentagrid(n, 52.0, seed + 7, 0.47)
    nsC, _ = _pentagrid(n, 24.0, seed + 13, 0.83, need_fr=False)
    hM = cv2.resize(_facet_hash(nsM, seed + 2), (n, n), interpolation=cv2.INTER_NEAREST)
    hB = _facet_hash(nsB, seed + 3)
    hC = _facet_hash(nsC, seed + 4)
    eM = cv2.resize(_segment_edges(nsM, frM, 75.0, seed + 20, 0.75), (n, n), interpolation=cv2.INTER_LINEAR)
    grad = np.where(hB * 7.0 % 1.0 > 0.5, frB[0], frB[1]) - F32(0.5)
    reg = H.fbm(n, seed + 5, cells=(3, 6, 12))
    fine = H.fbm(n, seed + 6, cells=(160, 320, 640), gain=0.9)
    v = 0.5 + 0.46 * (hM - 0.5) + 0.38 * (hB - 0.5) + 0.32 * (hC - 0.5) + 0.12 * grad + 0.07 * reg + 0.04 * fine
    v = np.clip((v - 0.5) * 1.40 + 0.5, 0, 1) ** 1.7
    eB = _segment_edges(nsB, frB, 52.0, seed + 21, 0.9)
    eC = np.clip((np.abs(np.diff(hC, axis=0, prepend=hC[:1])) + np.abs(np.diff(hC, axis=1, prepend=hC[:, :1]))) * 1.6 - 0.12, 0, 1)
    edge = np.maximum(np.minimum(1.0, 1.4 * eM), np.maximum(0.8 * eB, 0.55 * eC))
    base = H.ramp(v, [(0.0, '#0a1020'), (0.22, '#2a4670'), (0.5, '#7aa6d4'), (0.78, '#cce2fa'), (1.0, '#f2f9ff')])
    rgb = base + edge[..., None] * np.array([0.48, 0.56, 0.64], F32)
    sp = H.flake_mask(n, 0.0060, seed + 11) & (v > 0.40)
    rgb[sp] = 1.0
    q = np.floor(v * 5.0) / 4.0
    M = H.lerp(236.0, 255.0, q)
    R = H.lerp(125.0, 3.0, q) + 26.0 * (edge > 0.3)
    CC = H.lerp(34.0, 16.0, q)
    M[sp] = 255.0
    R[sp] = 0.0
    CC[sp] = 16.0
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 7. Nuclear Pasta - labyrinth of lasagna, spaghetti and gnocchi phases
# -------------------------------------------------------------------------
def nuclear_pasta(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 7 Nuclear Pasta: regional PHASE PATCHES (gnocchi dots -> rods -> sheets -> labyrinth -> holes) in randomly oriented crystal grains, each phase on its own colour pair; fine plane-wave textures (wave-2 review: big purple-top/white-bottom gradient removed)
    n = N
    r = H.rng(seed)
    m = 1024
    Xm, Ym = np.mgrid[0:m, 0:m].astype(F32) * F32(n / m)
    X, Y = Ym, Xm
    wx = X + 70.0 * H.fbm(m, seed + 11, cells=(3, 6, 12))
    wy = Y + 70.0 * H.fbm(m, seed + 12, cells=(3, 6, 12))
    cen = H.jitter_pts(n, 300.0, seed + 1, jit=0.9, margin=0)
    G = len(cen)
    best = np.full((m, m), 1e12, F32)
    lab = np.zeros((m, m), np.int32)
    for i in range(G):
        dd = (wx - cen[i, 0]) ** 2 + (wy - cen[i, 1]) ** 2
        mk = dd < best
        best[mk] = dd[mk]
        lab[mk] = i
    ang = r.uniform(0, np.pi, G).astype(F32)
    lam = r.uniform(13.0, 22.0, G).astype(F32)
    ca = np.cos(ang)[lab]
    sa = np.sin(ang)[lab]
    k = (2 * np.pi / lam)[lab].astype(F32)
    c60, s60 = float(np.cos(np.pi / 3)), float(np.sin(np.pi / 3))
    c2, s2 = ca * c60 - sa * s60, sa * c60 + ca * s60
    c3, s3 = ca * c60 + sa * s60, sa * c60 - ca * s60
    a1 = (X * ca + Y * sa) * k
    a2 = (X * c2 + Y * s2) * k
    a3 = (X * c3 + Y * s3) * k
    ap = (-X * sa + Y * ca) * k
    wn = H.fbm(m, seed + 13, cells=(18, 36, 72), gain=0.7)
    w = (np.cos(a1) + np.cos(a2) + np.cos(a3)) / 3.0
    s_dots = H.sstep(0.14, 0.34, w)
    s_holes = 1.0 - H.sstep(0.18, 0.40, w)
    q = np.cos(a1 + 1.5 * wn) * np.cos(0.45 * ap + 2.0 * wn)
    s_rods = H.sstep(0.16, 0.42, q)
    s_sheet = H.sstep(-0.10, 0.10, np.cos(a1 + 2.4 * wn))
    kk = lambda k0: (lambda kx: np.exp(-((kx - k0) / (0.16 * k0)) ** 2))
    u1 = H.fft_noise(m, seed + 21, kk(m / 5.5))
    s_lab = H.sstep(-0.05, 0.22, u1)
    z = H.fbm(m, seed + 31, cells=(2, 3, 5, 9), gain=0.7)
    lo_, hi_ = np.percentile(z[::4, ::4], (3, 97))
    z5 = np.clip((z - lo_) / (hi_ - lo_ + 1e-6), 0, 0.9999) * 5.0
    fields = [s_dots, s_rods, s_sheet, s_lab, s_holes]
    inks = ['#1a0e48', '#0c1850', '#1a1450', '#0a1840', '#1e0e44']
    brights = ['#ff74dc', '#66b0ff', '#c8b4ff', '#5cecd0', '#f08a48']
    s = np.zeros((m, m), F32)
    ink = np.zeros((m, m, 3), F32)
    bri = np.zeros((m, m, 3), F32)
    wsum = np.zeros((m, m), F32)
    for t_ in range(5):
        wt = np.clip((0.5 + 0.10 - np.abs(z5 - (t_ + 0.5))) / 0.20, 0, 1).astype(F32)
        wsum += wt
        s += wt * fields[t_]
        ink += wt[..., None] * H.hexrgb(inks[t_])
        bri += wt[..., None] * H.hexrgb(brights[t_])
    wsum = np.maximum(wsum, 1e-3)
    s /= wsum
    ink /= wsum[..., None]
    bri /= wsum[..., None]
    gt = (0.80 + 0.40 * H.hash01(np.arange(G, dtype=np.uint32), seed + 41))[lab].astype(F32)
    up = lambda a_: cv2.resize(a_, (n, n), interpolation=cv2.INTER_CUBIC)
    s = np.clip(up(s), 0, 1)
    p = np.clip(0.80 * s + 0.35 * H.blur(s, 2.2) + 0.10 * H.blur(s, 7.0), 0, 1)
    ink, bri, gt = up(ink), up(bri), up(gt)
    rgb = ink * (1 - p)[..., None] + bri * (p * gt)[..., None]
    rgb += (0.25 * H.sstep(0.82, 1.0, p))[..., None]
    b = np.clip(H.lum(np.clip(rgb, 0, 1)) / 0.70, 0, 1)
    M = H.lerp(60.0, 236.0, b)
    R = H.lerp(172.0, 40.0, b) + 10.0 * H.noise(n, 700, seed + 8)
    CC = H.lerp(120.0, 20.0, b)
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 8. Magnetar Iron Filings - dashes aligned to a sum of dipole fields
# -------------------------------------------------------------------------
def magnetar_filings(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 8 Magnetar Iron Filings: randomly placed (non-lattice) dipoles, summed field direction, line-integral-convolution of fine noise along the field = dense dark filings on pale steel; field loops visible between pole pairs (wave-2 review: hex maze read as a tiled pattern)
    n = N
    r = H.rng(seed)
    m = 1024
    gy, gx = np.mgrid[0:m, 0:m].astype(F32) * (n / m)
    Bx = np.zeros((m, m), F32)
    By = np.zeros((m, m), F32)
    poles = []
    tries = 0
    while len(poles) < 20 and tries < 400:
        tries += 1
        px, py = r.uniform(0.03, 0.97, 2) * n
        if all((px - a) ** 2 + (py - b) ** 2 > 230.0 ** 2 for a, b in poles):
            poles.append((px, py))
    for (px, py) in poles:
        mo = r.uniform(0, 2 * np.pi)
        st_ = r.uniform(0.6, 1.8)
        mx, my = np.cos(mo) * st_, np.sin(mo) * st_
        rx, ry = gx - px, gy - py
        r2 = rx * rx + ry * ry + 30.0 ** 2
        rr = np.sqrt(r2)
        dotp = (mx * rx + my * ry) / rr
        s = 3.0 * dotp / (r2 * rr)
        Bx += s * rx / rr - mx / (r2 * rr)
        By += s * ry / rr - my / (r2 * rr)
    mag = np.hypot(Bx, By) + F32(1e-12)
    u = (Bx / mag).astype(F32)
    v = (By / mag).astype(F32)
    tex = r.random((m, m)).astype(F32)
    uv = np.dstack([u, v]).astype(F32)
    X0, Y0 = H.xy(m)
    acc = tex.copy()
    for sgn in (1.0, -1.0):
        px = np.array(X0, F32)
        py = np.array(Y0, F32)
        for _ in range(7):
            sv = cv2.remap(uv, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            px += F32(sgn * 2.0) * sv[..., 0]
            py += F32(sgn * 2.0) * sv[..., 1]
            acc += cv2.remap(tex, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    t = acc / F32(15.0)
    t = cv2.resize(t, (n, n), interpolation=cv2.INTER_CUBIC)
    t = (t - float(t.mean())) / (float(t.std()) + 1e-6)
    t = t + 0.30 * H.fbm(n, seed + 9, cells=(512, 1024), gain=0.9)
    lm = np.log1p(mag / (float(np.median(mag[::4, ::4])) + 1e-12))
    lo_, hi_ = np.percentile(lm[::4, ::4], (3, 99.0))
    lm = cv2.resize(np.clip((lm - lo_) / (hi_ - lo_ + 1e-6), 0, 1).astype(F32), (n, n), interpolation=cv2.INTER_LINEAR)
    thr = 0.70 - 1.30 * lm
    dark = H.sstep(thr - 0.16, thr + 0.16, t)
    glow = H.blur(lm, 18.0)
    paper = H.ramp(np.clip(0.30 + 0.45 * glow + 0.18 * H.fbm(n, seed + 5, cells=(3, 6, 12, 24)), 0, 1),
                   [(0.0, '#8a929e'), (0.5, '#bcc4d0'), (1.0, '#e6ecf4')])
    sheen = 0.7 + 0.8 * H.sstep(1.4, 2.8, t)
    fil = np.array([0.045, 0.052, 0.075], F32)[None, None, :] * sheen[..., None]
    rgb = paper * (1.0 - 0.94 * dark)[..., None] + dark[..., None] * fil
    pd_ = np.zeros((n, n), np.uint8)
    sc = 16
    for (px, py) in poles:
        cv2.circle(pd_, (int(px * sc), int(py * sc)), int(5.5 * sc), 255, -1, cv2.LINE_AA, 4)
    pdf = pd_.astype(F32) / 255.0
    rgb = rgb * (1 - 0.9 * pdf)[..., None] + pdf[..., None] * np.array([0.02, 0.025, 0.04], F32)
    b = np.clip(H.lum(np.clip(rgb, 0, 1)) / 0.62, 0, 1)
    M = H.lerp(40.0, 215.0, b)
    R = H.lerp(224.0, 54.0, b) + 8.0 * H.noise(n, 700, seed + 8)
    CC = H.lerp(200.0, 18.0, b)
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 9. Crab Nebula Cage - tangled orange filaments around blue synchrotron fog
# -------------------------------------------------------------------------
def crab_cage(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 9 Crab Nebula Cage: four scales of distance-normalised zero-set loops over smooth blue fbm
    n = N
    wx = 20.0 * H.fbm(n, seed + 1, cells=(6, 13, 27))
    wy = 20.0 * H.fbm(n, seed + 2, cells=(6, 13, 27))
    lines = None
    for i, (cells, wd, amp) in enumerate(((20, 2.0, 1.0), (42, 1.5, 0.92), (88, 1.15, 0.8), (150, 0.95, 0.6))):
        z = H.fbm(n, seed + 20 + i, cells=(cells, cells * 2), gain=0.6)
        z = H.warp(z, wx * (0.5 + 0.4 * i), wy * (0.5 + 0.4 * i))
        l = H.zero_set_line(z, wd) * amp
        lines = l if lines is None else np.maximum(lines, l)
    mod = 0.45 + 0.55 * H.sstep(-1, 1, H.fbm(n, seed + 3, cells=(10, 22, 50, 110)))
    fil = lines * mod
    fog = H.fbm(n, seed + 4, cells=(3, 6, 12, 24, 48), gain=0.62)
    fv = H.sstep(-1.5, 2.2, fog) ** 2.0
    fogc = H.ramp(fv, [(0.0, '#050a30'), (0.3, '#0a2890'), (0.62, '#1355d8'), (0.88, '#3f98f0'), (1.0, '#6cbcff')])
    fl = np.clip(fil * 1.15 + 0.45 * H.blur(fil, 2.0), 0, 1.4)
    filc = H.ramp(np.clip(fl, 0, 1), [(0.0, '#5a0c04'), (0.35, '#d0300e'), (0.7, '#ff7a24'), (1.0, '#ffe8a0')])
    a = np.clip(fl * 1.3, 0, 1)[..., None]
    rgb = fogc * (1 - a) + filc * a
    rgb += 0.14 * H.blur(fil, 6.0)[..., None] * np.array([1.0, 0.4, 0.08], F32)
    s = H.sstep(0.15, 0.65, fl)
    M = H.lerp(H.lerp(110.0, 170.0, fv), 228.0, s)
    R = H.lerp(H.lerp(122.0, 66.0, fv), 20.0, s)
    CC = H.lerp(52.0, 16.0, s)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 10. Roche Lobe Streams - a donor star pouring a stream into its partner's disk
# -------------------------------------------------------------------------
def roche_streams(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 9 Roche Lobe Streams: random binaries (2 masses, 150-400 px apart, random orientation); nested equipotential CONTOURS of the real Roche potential (figure-8 lobes touching at L1), thin bright mass-transfer stream L1 -> tilted ring disk on the accretor (wave-2 review: tadpole read -> contour lines, no solid blobs)
    n = N
    r = H.rng(seed)
    sc = 16
    placed = []
    tries = 0
    while len(placed) < 40 and tries < 1200:
        tries += 1
        d = float(r.uniform(150.0, 380.0))
        x, y = r.uniform(0.03 * n, 0.97 * n, 2)
        if all(((x - px) ** 2 + (y - py) ** 2) ** 0.5 > 0.64 * (d + pd) for px, py, pd in placed):
            placed.append((x, y, d))
    lines_c, lines_1, lines_s = [], [], []        # (value, int32 polyline, closed, thick)
    fills, dots_l = [], []                        # [S19 coordinator fix 2026-10-12] lobe fills (side, polyline); L1 touch points
    dots_a, dots_d = [], []                       # accretor / donor point sources (x, y, amp)
    step = 2.0
    for (x, y, d) in placed:
        q = float(r.uniform(0.25, 0.90))
        th = float(r.uniform(0, 2 * np.pi))
        ct, st_ = float(np.cos(th)), float(np.sin(th))
        xc = q / (1 + q)
        ax = np.linspace(0.04, 0.96, 500)
        phx = -1.0 / ax - q / (1 - ax) - 0.5 * (1 + q) * (ax - xc) ** 2
        iL1 = int(np.argmax(phx))
        xL1, pL1 = float(ax[iL1]), float(phx[iL1])
        bx = np.linspace(1.03, 2.2, 500)
        phb = -1.0 / bx - q / (bx - 1) - 0.5 * (1 + q) * (bx - xc) ** 2
        pL2 = float(np.max(phb))
        xs_ = np.arange(-0.95 * d, 1.90 * d, step, dtype=np.float32)
        ys_ = np.arange(-0.95 * d, 0.95 * d, step, dtype=np.float32)
        gx, gy = np.meshgrid(xs_ / d, ys_ / d)
        r1 = np.sqrt(gx * gx + gy * gy + 1.5e-4)
        r2 = np.sqrt((gx - 1) ** 2 + gy * gy + 1.5e-4)
        phi = -1.0 / r1 - q / r2 - 0.5 * (1 + q) * ((gx - xc) ** 2 + gy * gy)
        # (level, brightness, thickness, canvas) : deep lobes, the figure-8 at L1, two common-envelope contours
        lv = []
        for s_, v_ in ((0.12, 120), (0.32, 135), (0.62, 150), (1.10, 165), (2.0, 180)):
            lv.append((pL1 * (1 + s_), v_, 1, 0))
        lv.append((pL1 * 1.0006, 255, 3, 1))          # the two lobes almost touching at L1 = the critical figure-8
        for t_, v_ in ((0.30, 120), (0.66, 95)):
            lv.append((pL1 + t_ * (pL2 - pL1), v_, 1, 0))
        Hh, Ww = phi.shape
        for lev, v_, tk, which in lv:
            msk = (phi <= lev).astype(np.uint8) * 255
            cs, _h = cv2.findContours(msk, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
            for c in cs:
                c = c[:, 0, :].astype(np.float32)
                if len(c) < 12:
                    continue
                if c[:, 0].min() <= 0 or c[:, 1].min() <= 0 or c[:, 0].max() >= Ww - 1 or c[:, 1].max() >= Hh - 1:
                    continue
                lx = (xs_[0] + c[:, 0] * step - xc * d)
                ly = (ys_[0] + c[:, 1] * step)
                P = np.stack([x + lx * ct - ly * st_, y + lx * st_ + ly * ct], 1)
                Pi = np.round(P * sc).astype(np.int32).reshape(-1, 1, 2)
                (lines_1 if which else lines_c).append((v_, Pi, tk))
                if which:
                    fills.append((0 if float((xs_[0] + c[:, 0] * step).mean()) < xL1 * d else 1, Pi))
        # accretor = primary (local origin); donor = secondary; stream from L1 spirals in to a tilted ring disk
        def to_g(px_, py_):
            lx = px_ - xc * d
            return (x + lx * ct - py_ * st_, x * 0 + y + lx * st_ + py_ * ct)
        side = 1.0 if r.random() < 0.5 else -1.0
        rL1 = xL1 * d
        rd = float(r.uniform(0.14, 0.24)) * rL1
        tt = np.linspace(-0.18, 1.0, 82)
        ang = side * 1.0 * np.clip(tt, 0, None) ** 0.9
        rad = rL1 * (1 - tt) + rd * tt
        sxp, syp = rad * np.cos(ang), rad * np.sin(ang)
        gxs, gys = to_g(sxp, syp)
        P = np.stack([gxs, gys], 1)
        lines_s.append((255, np.round(P * sc).astype(np.int32).reshape(-1, 1, 2), 3))
        dots_l.append(to_g(rL1, 0.0))
        ox, oy = to_g(0.0, 0.0)
        tilt = float(np.degrees(r.uniform(0, np.pi)))
        incl = float(r.uniform(0.25, 0.6))
        dots_a.append((ox, oy, 1.0))
        px2, py2 = to_g(d, 0.0)
        dots_d.append((px2, py2, float(r.uniform(0.55, 0.9))))
        lines_s.append((-1, (ox, oy, rd, incl, tilt), 0))
    cnv_c = np.zeros((n, n), np.uint8)
    cnv_1 = np.zeros((n, n), np.uint8)
    cnv_s = np.zeros((n, n), np.uint8)
    for lst, cnv in ((lines_c, cnv_c), (lines_1, cnv_1)):
        lst.sort(key=lambda t: t[0])
        for v_, P, tk in lst:
            cv2.polylines(cnv, [P], True, int(v_), tk, cv2.LINE_AA, 4)
    for v_, P, tk in lines_s:
        if v_ < 0:
            ox, oy, rd, incl, tilt = P
            for f_, vv in ((1.0, 235), (0.62, 150)):
                cv2.ellipse(cnv_s, (int(ox * sc), int(oy * sc)), (int(rd * f_ * sc), int(rd * f_ * incl * sc)), tilt, 0, 360, vv, 2, cv2.LINE_AA, 4)
        else:
            cv2.polylines(cnv_s, [P], False, int(v_), tk, cv2.LINE_AA, 4)
    fa = np.zeros((n, n), np.uint8)
    fd = np.zeros((n, n), np.uint8)
    for side_l, Pi in fills:
        cv2.fillPoly(fa if side_l == 0 else fd, [Pi], 255, cv2.LINE_AA, 4)
    pl1 = np.zeros((n, n), F32)
    for (ox, oy) in dots_l:
        H.points(pl1, np.array([ox]), np.array([oy]), np.array([1.0], F32))
    l1g = H.blur(pl1, 1.6) * 16.0 + H.blur(pl1, 5.0) * 26.0 + H.blur(pl1, 12.0) * 60.0
    cc_ = cnv_c.astype(F32) / 255.0
    c1_ = cnv_1.astype(F32) / 255.0
    cs_ = cnv_s.astype(F32) / 255.0
    pa = np.zeros((n, n), F32)
    pd_ = np.zeros((n, n), F32)
    for (ox, oy, a_) in dots_a:
        H.points(pa, np.array([ox]), np.array([oy]), np.array([a_], F32))
    for (ox, oy, a_) in dots_d:
        H.points(pd_, np.array([ox]), np.array([oy]), np.array([a_], F32))
    hot = H.blur(pa, 2.0) * 22.0 + H.blur(pa, 5.5) * 16.0 + H.blur(pa, 13.0) * 7.0
    don = H.blur(pd_, 2.2) * 16.0 + H.blur(pd_, 6.0) * 11.0 + H.blur(pd_, 15.0) * 5.0
    ground = H.ramp(0.5 + 0.30 * H.fbm(n, seed + 3, cells=(3, 6, 12, 24, 48, 96)) + 0.10 * H.fbm(n, seed + 4, cells=(128, 256, 512), gain=0.9),
                    [(0.0, '#150833'), (0.5, '#25104d'), (1.0, '#381a70')])
    rgb = ground.copy()
    rgb += (fa.astype(F32) / 255.0 * 0.20)[..., None] * np.array([0.30, 0.55, 1.0], F32)
    rgb += (fd.astype(F32) / 255.0 * 0.18)[..., None] * np.array([1.0, 0.62, 0.22], F32)
    rgb += H.tonemap(l1g, 1.0)[..., None] * np.array([1.0, 0.93, 0.72], F32)
    rgb += (cc_ * 0.95 + H.blur(cc_, 1.8) * 0.55)[..., None] * np.array([0.62, 0.52, 1.0], F32)
    rgb += (c1_ * 0.80 + H.blur(c1_, 2.2) * 0.55 + H.blur(c1_, 7.0) * 0.20)[..., None] * np.array([1.0, 0.90, 0.62], F32)
    rgb += (cs_ * 1.10 + H.blur(cs_, 1.8) * 0.85 + H.blur(cs_, 6.0) * 0.30)[..., None] * np.array([0.62, 0.95, 1.0], F32)
    rgb += H.tonemap(hot, 1.0)[..., None] * np.array([0.78, 0.97, 1.0], F32)
    rgb += H.tonemap(don, 1.0)[..., None] * np.array([1.0, 0.82, 0.38], F32)
    rgb = H.tonemap(rgb, 1.4)
    Il = np.clip(np.maximum(np.maximum(cc_, c1_), cs_) * 1.1, 0, 1)
    Ih = np.maximum(np.maximum(H.tonemap(hot, 0.8), H.tonemap(don, 0.8)), H.tonemap(l1g, 0.8))
    I = np.maximum(Il, Ih)
    M = H.lerp(30.0, 252.0, I)
    R = H.lerp(190.0, 24.0, I)
    CC = H.lerp(150.0, 16.0, I)
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


FINISHES = [
    ("cz_solar_granulation", "Solar Granulation",
     "Boiling sun surface: gold-white convection cells split by thin dark umber lanes.", solar_granulation),
    ("cz_sunspot_penumbra", "Sunspot Penumbra",
     "Black sunspot cores ringed by radial copper filaments over a mottled amber sun.", sunspot_penumbra),
    ("cz_coronal_loops", "Coronal Loops",
     "Dense tangle of small magnetic loops glowing gold-orange and red on dark maroon.", coronal_loops),
    ("cz_flare_ribbons", "Flare Ribbons",
     "Glowing pink-white ribbons flowing along eddying streamlines over deep violet.", flare_ribbons),
    ("cz_pulsar_beacons", "Pulsar Beacons",
     "Bright white stars each firing two opposed ice-blue spindle beams over a blue starfield, with faint timing arcs.", pulsar_beacons),
    ("cz_crystal_core", "Crystallized Star Core",
     "Frozen white dwarf: sharp five-fold quasicrystal facets in ice blue and steel.", crystal_core),
    ("cz_nuclear_pasta", "Nuclear Pasta",
     "Patchwork of nuclear-pasta phases: dot lattices, wavy stripe mazes and tube fields in violet, teal, cream and amber.", nuclear_pasta),
    ("cz_magnetar_filings", "Magnetar Iron Filings",
     "Black iron-filing lines looping out of hidden magnetic poles across pale steel-grey, like filings over a magnet.", magnetar_filings),
    ("cz_crab_cage", "Crab Nebula Cage",
     "Tangled gold-orange filament loops wrapped around electric-blue fog.", crab_cage),
    ("cz_roche_streams", "Roche Lobe Streams",
     "Binary Roche-lobe figure-8s of nested lilac contour rings, a white gas stream curling from one star toward the other, on violet.", roche_streams),
]
