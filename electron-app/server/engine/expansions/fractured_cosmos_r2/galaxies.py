# -*- coding: utf-8 -*-
"""GALAXIES & LARGE SCALE chapter (cz_ 41-50): the web, the zoo, clusters, rifts, maps, trails, bursts.

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
    """Ground brightness modulation clipped to >= 0.58 (a negative factor clipped to black leaves hard-edged
    dark islands) plus 1 px grain against 8-bit banding."""
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


# -------------------------------------------------------------------------
# 41. Cosmic Web
# -------------------------------------------------------------------------
def cosmic_web(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 41 Cosmic Web: glowing beaded filaments joining bright gold nodes around dark voids at two scales (Delaunay-circumcentre network, wavy segments, beads along each); matte void, pearl-flake filaments
    from scipy.spatial import Delaunay
    n = N
    r = H.rng(seed)
    lines = np.zeros((n, n), np.uint8)
    beadA = np.zeros((n, n), F32)
    nodeA = np.zeros((n, n), F32)
    nodeB = np.zeros((n, n), F32)
    dens = H.fbm(256, seed + 21, cells=(3, 6, 12), gain=0.7)

    def web(spacing, sd, thick, vlo, vhi, sig_node, target):
        pts = H.jitter_pts(n, spacing, sd, jit=0.95, margin=int(spacing * 1.2))
        tri = Delaunay(pts)
        s = tri.simplices
        a, b, c = pts[s[:, 0]], pts[s[:, 1]], pts[s[:, 2]]
        d = 2.0 * (a[:, 0] * (b[:, 1] - c[:, 1]) + b[:, 0] * (c[:, 1] - a[:, 1]) + c[:, 0] * (a[:, 1] - b[:, 1]))
        d = np.where(np.abs(d) < 1e-9, 1e-9, d)
        a2, b2, c2 = (a ** 2).sum(1), (b ** 2).sum(1), (c ** 2).sum(1)
        ux = (a2 * (b[:, 1] - c[:, 1]) + b2 * (c[:, 1] - a[:, 1]) + c2 * (a[:, 1] - b[:, 1])) / d
        uy = (a2 * (c[:, 0] - b[:, 0]) + b2 * (a[:, 0] - c[:, 0]) + c2 * (b[:, 0] - a[:, 0])) / d
        cc = np.stack([ux, uy], 1)
        T = len(s)
        ti = np.repeat(np.arange(T), 3)
        nj = tri.neighbors.ravel()
        m = nj > ti
        p0, p1 = cc[ti[m]], cc[nj[m]]
        ln = np.hypot(*(p1 - p0).T)
        ok = (ln < 2.3 * spacing) & (ln > 4.0)
        ok &= (p0[:, 0] > -60) & (p0[:, 0] < n + 60) & (p0[:, 1] > -60) & (p0[:, 1] < n + 60)
        p0, p1, ln = p0[ok], p1[ok], ln[ok]
        S = len(p0)
        ts = np.linspace(0, 1, 7)
        nrm = np.stack([-(p1 - p0)[:, 1], (p1 - p0)[:, 0]], 1) / (ln[:, None] + 1e-6)
        wob = r.normal(0, 0.07, (S, 7)) * ln[:, None] * np.sin(np.pi * ts)[None, :]
        path = p0[:, None, :] + (p1 - p0)[:, None, :] * ts[None, :, None] + nrm[:, None, :] * wob[..., None]
        mid = path[:, 3, :]
        dm = dens[np.clip((mid[:, 1] / 8).astype(int), 0, 255), np.clip((mid[:, 0] / 8).astype(int), 0, 255)]
        w = (0.45 + 0.55 * H.sstep(-1.0, 1.0, dm)) * (0.45 + 0.55 * r.random(S) ** 0.7)
        vals = (vlo + (vhi - vlo) * w).astype(np.int32)
        H.lines_u8(n, [path[i] for i in range(S)], vals, thick=thick, canvas=lines)
        cnt = (ln / 10.0).astype(int) + 1
        si = np.repeat(np.arange(S), cnt)
        tt = r.random(len(si))
        pp = p0[si] + (p1 - p0)[si] * tt[:, None] + nrm[si] * (r.normal(0, 1.2, len(si)) * 1.0)[:, None]
        H.points(beadA, pp[:, 0], pp[:, 1], (vals[si] / 255.0) * (0.35 + 0.65 * r.random(len(si)) ** 1.5), mode="add")
        inn = (cc[:, 0] > 0) & (cc[:, 0] < n) & (cc[:, 1] > 0) & (cc[:, 1] < n)
        amp = (0.45 + 0.55 * r.random(inn.sum()) ** 1.3) * 2 * np.pi * sig_node ** 2
        H.points(target, cc[inn, 0], cc[inn, 1], amp, mode="add")

    web(300.0, seed + 1, 2, 120, 255, 5.5, nodeA)
    web(118.0, seed + 2, 1, 55, 160, 2.6, nodeB)
    fil = lines.astype(F32) / 255.0
    fil = np.clip(fil + 0.55 * H.blur(fil, 2.0), 0, 1.3)
    beads = np.clip(H.blur(beadA, 1.0) * 7.0, 0, 1.2)
    nodes = np.clip(H.blur(nodeA, 5.5) + H.blur(nodeB, 2.6), 0, 1.4)
    halo = H.blur(nodeA, 14.0) * 1.2 + H.blur(nodeB, 6.0) * 0.8
    hue = np.clip(0.5 + 0.6 * H.fbm(n, seed + 3, cells=(2, 4, 8), gain=0.6), 0, 1)
    fcol = H.ramp(hue, [(0.0, '#5a8cff'), (0.5, '#8cc8ff'), (1.0, '#c6b0ff')])
    gz = _gz(n, seed + 4)
    rgb = np.array([0.045, 0.060, 0.150], F32)[None, None, :] * gz[..., None]
    rgb += (fil * 0.85 + beads * 0.6)[..., None] * fcol
    rgb += (halo * 0.30)[..., None] * np.array([0.7, 0.55, 0.25], F32)
    rgb += nodes[..., None] * np.array([1.0, 0.80, 0.38], F32)
    rgb += _specks(n, seed + 5, 0.002, 0.08, 0.5)[..., None] * np.array([0.8, 0.9, 1.0], F32)
    rgb = np.clip(rgb, 0, 1)
    f = np.clip(fil * 0.8 + beads * 0.6 + nodes, 0, 1)
    fm = r.random((n, n), dtype=F32) < 0.55
    flk = (f > 0.18) & fm
    M = H.lerp(0.0, 200.0, f ** 0.7)
    R_ = H.lerp(228.0, 44.0, f ** 0.6)
    CC = H.lerp(232.0, 20.0, H.sstep(0.0, 0.3, f))
    M = np.where(flk, 255.0, M)
    R_ = np.where(flk, 0.0, R_)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 42. Galaxy Zoo
# -------------------------------------------------------------------------
def _gal_master(kind, R, sd, cosi):
    S = int(2 * R * 1.15) | 1
    c = S // 2
    y, x = np.mgrid[0:S, 0:S].astype(F32)
    x -= c
    y -= c
    rg = H.rng(sd)
    if kind == 0:                                              # face-on / inclined spiral
        yp = y / F32(cosi)
        r_ = np.hypot(x, yp) / F32(R)
        th = np.arctan2(yp, x)
        k = rg.uniform(4.5, 7.5)
        arms = (0.5 + 0.5 * np.cos(2 * th - k * np.log(r_ + 0.05) + rg.uniform(0, 6.28))) ** 2.2
        body = np.exp(-r_ / 0.40) * (0.22 + 0.95 * arms * H.sstep(0.10, 0.38, r_)) * (1 - H.sstep(0.80, 1.05, r_))
        core = np.exp(-(r_ / 0.13) ** 2) * 1.2
    elif kind == 1:                                            # elliptical (Sersic n=4)
        e = rg.uniform(0.0, 0.62)
        r_ = np.hypot(x, y / F32(1.0 - e)) / F32(0.33 * R)
        body = np.exp(-7.67 * (np.power(r_ + 1e-3, 0.25) - 1.0)) * 0.22 * (1 - H.sstep(2.0, 3.0, r_))
        core = np.exp(-(r_ / 0.35) ** 2) * 0.9
    elif kind == 2:                                            # edge-on disc with dust lane
        disc = np.exp(-np.abs(x) / (0.50 * R)) * np.exp(-(y / (0.075 * R)) ** 2)
        lane = 1.0 - 0.75 * np.exp(-(y / (0.022 * R)) ** 2) * H.sstep(0.05, 0.3, np.abs(x) / R)
        bulge = np.exp(-((x / (0.28 * R)) ** 2 + (y / (0.17 * R)) ** 2))
        body = (disc * lane + 0.6 * bulge * lane) * (1 - H.sstep(0.85, 1.1, np.abs(x) / R))
        core = np.exp(-((x / (0.10 * R)) ** 2 + (y / (0.06 * R)) ** 2)) * 1.1
    else:                                                      # irregular clumps
        body = np.zeros((S, S), F32)
        for _ in range(7):
            gx, gy = rg.normal(0, 0.28 * R, 2)
            sg = rg.uniform(0.10, 0.22) * R
            body += np.exp(-(((x - gx) ** 2 + (y - gy) ** 2) / (2 * sg * sg))) * rg.uniform(0.4, 1.0)
        body *= (0.55 + 0.45 * np.clip(rg.standard_normal((S, S)).astype(F32), -1, 1)) * (1 - H.sstep(0.85, 1.1, np.hypot(x, y) / R))
        core = np.exp(-((x ** 2 + y ** 2) / (2 * (0.09 * R) ** 2))) * 0.5
    return np.clip(body, 0, 2).astype(F32), np.clip(core, 0, 2).astype(F32)


def galaxy_zoo(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 42 Galaxy Zoo: ~1,700 tiny galaxies of mixed kinds (two-arm spirals, glowing ellipticals, edge-on discs with dust lanes, lumpy irregulars), 8-50 px, every colour and rotation; chrome cores, satin arms on a wet-gloss black ground
    n = N
    r = H.rng(seed)
    classes = (11.0, 17.0, 26.0, 40.0)
    NR = 12
    variants = [(0, 0.50), (0, 0.82), (0, 1.0), (1, 0), (1, 0), (2, 0), (2, 0), (3, 0), (3, 0)]
    tb, tc = [], []
    for ci, R in enumerate(classes):
        for vi, (kd, cosi) in enumerate(variants):
            bd, cr = _gal_master(kd, R, seed * 7 + ci * 31 + vi, cosi if cosi else 1.0)
            tb += H.rotset(bd, NR, np.pi)
            tc += H.rotset(cr, NR, np.pi)
    pts = H.jitter_pts(n, 62.0, seed + 1, jit=0.92, margin=40)
    pts = pts[r.random(len(pts)) < 0.88]
    K = len(pts)
    cl = r.choice(4, K, p=[0.30, 0.34, 0.24, 0.12])
    kind = r.choice(4, K, p=[0.38, 0.27, 0.15, 0.20])
    vsel = np.zeros(K, np.int64)
    for kd in range(4):
        idxs = [i for i, v in enumerate(variants) if v[0] == kd]
        m = kind == kd
        vsel[m] = np.array(idxs)[r.integers(0, len(idxs), int(m.sum()))]
    rt = r.integers(0, NR, K)
    ti = (cl * len(variants) + vsel) * NR + rt
    base_col = np.array([[0.55, 0.72, 1.0], [1.0, 0.76, 0.42], [0.95, 0.86, 0.70], [0.62, 0.88, 1.0]], F32)[kind]
    hs = r.normal(0, 0.10, (K, 3)).astype(F32)
    col = np.clip(base_col + hs, 0.05, 1.2)
    pink = r.random(K) < 0.12
    col[pink] = np.array([1.0, 0.55, 0.75], F32)
    amp = r.uniform(0.8, 1.35, K)
    flip = r.integers(0, 4, K)
    body = np.zeros((n, n, 3), F32)
    corec = np.zeros((n, n), F32)
    H.splat(body, tb, ti, pts[:, 0], pts[:, 1], amp=amp, col=col, flip=flip, mode="add")
    H.splat(corec, tc, ti, pts[:, 0], pts[:, 1], amp=amp, flip=flip, mode="add")
    gz = _gz(n, seed + 3)
    rgb = np.array([0.062, 0.066, 0.152], F32)[None, None, :] * gz[..., None]
    rgb += body * 1.05
    rgb += (corec * 0.85)[..., None] * np.array([1.0, 0.95, 0.85], F32)
    rgb += _specks(n, seed + 4, 0.003, 0.08, 0.5)[..., None] * np.array([0.8, 0.88, 1.0], F32)
    rgb = np.clip(rgb, 0, 1)
    bl = np.clip(H.lum(np.clip(body, 0, 1.5)) * 1.4, 0, 1)
    cr_ = np.clip(corec * 1.3, 0, 1)
    M = H.lerp(14.0, 150.0, bl)
    M = H.lerp(M, 248.0, cr_)
    R_ = H.lerp(26.0, 92.0, H.sstep(0.0, 0.25, bl))
    R_ = H.lerp(R_, 8.0, cr_)
    R_ = np.where(bl < 0.03, 26.0 + 6.0 * _snoise(900, 900, seed + 6), R_)
    CC = H.lerp(16.0, 42.0, H.sstep(0.0, 0.3, bl))
    CC = H.lerp(CC, 16.0, cr_)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 43. Globular Star Swarm
# -------------------------------------------------------------------------
def globular_swarm(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 43 Globular Star Swarm: three dozen globular clusters of pinpoint stars sampled from Plummer profiles, thickening to blazing cores, with orange red giants, blue-white stragglers and a warm glow; dark satin ground, every star a flake
    n = N
    r = H.rng(seed)
    NC = 30
    cx = r.uniform(-40, n + 40, NC)
    cy = r.uniform(-40, n + 40, NC)
    ac = np.exp(r.uniform(np.log(26.0), np.log(92.0), NC))
    xs_l, ys_l, mg_l, cl_l = [], [], [], []
    for k in range(NC):
        Ns = int(260 + 1100 * (ac[k] / 92.0) ** 1.4)
        u = r.random(Ns) * 0.992
        rr = np.minimum(ac[k] / np.sqrt(u ** (-2.0 / 3.0) - 1.0), 7.0 * ac[k])
        th = r.uniform(0, 2 * np.pi, Ns)
        el = r.uniform(0.0, 0.32)
        ph = r.uniform(0, np.pi)
        px = rr * np.cos(th)
        py = rr * np.sin(th) * (1.0 - el)
        xs_l.append(cx[k] + px * np.cos(ph) - py * np.sin(ph))
        ys_l.append(cy[k] + px * np.sin(ph) + py * np.cos(ph))
        mg = 0.34 + 0.66 * r.random(Ns) ** 2.0
        c_ = np.zeros(Ns, np.int64)
        gi = (r.random(Ns) < 0.05) & (rr > 0.8 * ac[k])
        bs = (r.random(Ns) < 0.07) & (rr < 1.2 * ac[k])
        c_[gi] = 1
        c_[bs] = 2
        mg[gi] = 0.7 + 0.3 * r.random(int(gi.sum()))
        mg[bs] = 0.6 + 0.4 * r.random(int(bs.sum()))
        mg_l.append(mg)
        cl_l.append(c_)
    NF = 26000
    xs_l.append(r.uniform(0, n, NF))
    ys_l.append(r.uniform(0, n, NF))
    mg_l.append(0.20 + 0.7 * r.random(NF) ** 2.4)
    cl_l.append(np.zeros(NF, np.int64))
    xs = np.concatenate(xs_l)
    ys = np.concatenate(ys_l)
    mg = np.concatenate(mg_l)
    cl = np.concatenate(cl_l)
    ix = np.round(xs).astype(np.int64)
    iy = np.round(ys).astype(np.int64)
    pal = np.array([[1.0, 0.92, 0.74], [1.0, 0.50, 0.24], [0.66, 0.82, 1.0]], F32)
    jit = r.random(len(xs))
    base = np.where(cl[:, None] == 0, np.where(jit[:, None] < 0.45, np.array([0.92, 0.94, 1.0], F32), pal[0]), pal[np.clip(cl, 0, 2)])
    cvs = np.zeros((n, n, 3), F32)
    allst = np.zeros((n, n), F32)
    for c in range(3):
        ch = np.zeros((n, n), F32)
        H.points(ch, ix, iy, mg * base[:, c])
        cvs[..., c] = ch
    H.points(allst, ix, iy, mg, mode="add")
    big = (mg > 0.50) | (cl > 0)
    big2 = (mg > 0.80) | (cl > 0)
    bright = np.zeros((n, n, 3), F32)
    for c in range(3):
        ch = np.zeros((n, n), F32)
        H.points(ch, ix[big], iy[big], (mg * base[:, c])[big])
        bright[..., c] = ch
    bright2 = np.zeros((n, n, 3), F32)
    for c in range(3):
        ch = np.zeros((n, n), F32)
        H.points(ch, ix[big2], iy[big2], (mg * base[:, c])[big2])
        bright2[..., c] = ch
    st1 = np.stack([H.blur(bright[..., c], 1.2) for c in range(3)], -1)
    st2 = np.stack([H.blur(bright[..., c], 3.2) for c in range(3)], -1)
    st3 = np.stack([H.blur(bright2[..., c], 6.0) for c in range(3)], -1)
    glow = H.blur(allst, 4.0) * 5.0 + H.blur(allst, 16.0) * 14.0
    gz = _gz(n, seed + 3)
    rgb = np.array([0.075, 0.062, 0.120], F32)[None, None, :] * gz[..., None]
    rgb += cvs * 1.5
    rgb += st1 * 1.6 + st2 * 5.2 + st3 * 7.0
    rgb += (glow * 0.02)[..., None] * np.array([1.0, 0.78, 0.50], F32)
    # [S19 coordinator fix 2026-10-12] optional: brighter cluster cores (dense small clusters blaze warm white)
    corel = np.clip(H.blur(allst, 5.0) * 14.0 - 0.25, 0, 1.2)
    rgb += (corel ** 1.4 * 0.85)[..., None] * np.array([1.0, 0.88, 0.70], F32)
    rgb = np.clip(rgb, 0, 1)
    star = np.maximum(np.maximum(cvs[..., 0], cvs[..., 1]), cvs[..., 2])
    fl = star > 0.08
    # [S19 coordinator polish A 2026-10-12] spec richness: the spec now carries the paint's structure (matte/rough ground with 1 px flake; lines, arcs, cores = satin then mirror metal)
    M, R_, CC = H.structure_spec(rgb, seed + 91, [(0.14, 0.30, 190.0, 55.0, 28.0), (0.40, 0.80, 252.0, 4.0, 16.0)],
                                 ground_m=(35.0, 85.0), halo=(3.5, 2.0, 120.0, 85.0, 36.0))
    M = np.where(fl, 255.0, M)
    R_ = np.where(fl, 0.0, R_)
    CC = np.where(fl, 16.0, CC)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 44. Galactic Dust Rift
# -------------------------------------------------------------------------
def galactic_rift(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 44 Galactic Dust Rift: a warm Milky Way - two wide wavering bands of cream-to-gold star glow (three hundred thousand stars sampled by band density) on an indigo night sky, cut by dark branching dust lanes at three scales whose soft edges burn brown; stars are flakes on a satin glow, the dust is dead matte (coordinator fix 2026-10-12: grey static -> warm glowing band + brown dust lanes)
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)

    def band(ang, off, sig, sd, wamp):
        c_, s_ = float(np.cos(ang)), float(np.sin(ang))
        u = (X - n / 2) * (-s_) + (Y - n / 2) * c_ + off + wamp * H.fbm(n, sd, cells=(2, 3, 5, 9), gain=0.6)
        return np.exp(-(u / sig) ** 2).astype(F32)

    g1 = band(0.38, 0.0, 340.0, seed + 1, 210.0)
    g2 = band(-0.95, 230.0, 230.0, seed + 2, 160.0)
    cloud = np.clip(0.80 + 0.45 * H.fbm(n, seed + 12, cells=(4, 8, 16, 32), gain=0.7), 0.30, 1.5)
    G = np.clip((np.maximum(g1, 0.82 * g2) * cloud + 0.10), 0, 1.3).astype(F32)
    z = H.fbm(n, seed + 3, cells=(3, 6, 12, 24), gain=0.62)
    z = H.warp(z.astype(F32), (80.0 * H.fbm(n, seed + 4, cells=(2, 4, 8))).astype(F32), (80.0 * H.fbm(n, seed + 5, cells=(2, 4, 8))).astype(F32))
    z2 = H.fbm(n, seed + 6, cells=(14, 28, 56, 112), gain=0.8)
    z2 = H.warp(z2.astype(F32), (30.0 * H.fbm(n, seed + 7, cells=(4, 8, 16))).astype(F32), (30.0 * H.fbm(n, seed + 8, cells=(4, 8, 16))).astype(F32))
    z3 = H.fbm(n, seed + 9, cells=(34, 68, 136, 272), gain=0.85)
    gk = np.clip(G * 1.7, 0, 1)
    d1 = np.exp(-(z / 0.26) ** 2)
    d2 = np.exp(-(z2 / 0.22) ** 2)
    d3 = np.exp(-(z3 / 0.19) ** 2)
    dust = np.clip((1.10 * d1 + 0.80 * d2 * (0.25 + 0.75 * np.clip(d1 * 2.0, 0, 1)) + 1.0 * d3) * (0.30 + 0.70 * gk), 0, 1)
    dust = H.blur(dust.astype(F32), 1.0)
    NS0 = 320000
    sx = r.integers(0, n, NS0)
    sy = r.integers(0, n, NS0)
    dens = 0.05 + 0.95 * np.clip(G[sy, sx], 0, 1) ** 1.25
    dens = dens * (1.0 - 0.92 * dust[sy, sx])
    kp = r.random(NS0) < dens
    sx, sy = sx[kp], sy[kp]
    NS = len(sx)
    mg = 0.12 + 0.88 * r.random(NS) ** 3.0
    cl = r.choice(4, NS, p=[0.34, 0.30, 0.22, 0.14])
    pal = np.array([[1.0, 0.96, 0.86], [1.0, 0.82, 0.55], [0.78, 0.86, 1.0], [1.0, 0.62, 0.40]], F32)
    cvs = np.zeros((n, n, 3), F32)
    allst = np.zeros((n, n), F32)
    for c in range(3):
        ch = np.zeros((n, n), F32)
        H.points(ch, sx, sy, mg * pal[cl, c])
        cvs[..., c] = ch
    H.points(allst, sx, sy, mg, mode="add")
    big = mg > 0.46
    bst = np.zeros((n, n), F32)
    H.points(bst, sx[big], sy[big], mg[big])
    milk = np.clip(H.blur(allst, 2.2) * 2.0 + H.blur(allst, 9.0) * 4.0, 0, 1.6)
    mott = np.clip(1.0 + 0.95 * H.fbm(n, seed + 13, cells=(64, 128, 256, 512), gain=1.0), 0.25, 2.3)
    D = np.clip(((0.80 * G * cloud + 0.40 * milk) * mott) / 1.2, 0, 1)
    big2 = (mg > 0.60)
    b2 = np.zeros((n, n), F32)
    H.points(b2, sx[big2], sy[big2], mg[big2])
    b2 = H.blur(b2, 3.0) * 5.5
    sky = H.ramp(D, [(0.0, '#080a22'), (0.22, '#1c1840'), (0.45, '#6e4634'), (0.68, '#c98c4a'), (0.86, '#f3cd8a'), (1.0, '#fff2d2')])
    brown = np.array([0.20, 0.105, 0.055], F32)[None, None, :] * (0.55 + 0.9 * np.clip(G, 0, 1))[..., None]
    ds = H.blur(dust, 2.6)
    edge = np.clip(4.0 * ds * (1.0 - ds), 0, 1) * np.clip(G * 1.4, 0, 1)
    rgb = sky * (1.0 - 0.90 * dust)[..., None] + brown * (0.90 * dust)[..., None]
    rgb += edge[..., None] * np.array([0.52, 0.27, 0.10], F32) * 0.55
    rgb += cvs * 1.6 * (1.0 - 0.85 * dust)[..., None]
    rgb += b2[..., None] * np.array([1.0, 0.88, 0.70], F32) * 0.9 * (1.0 - 0.85 * dust)[..., None]
    rgb += (H.blur(bst, 1.2) * 1.3 + H.blur(bst, 2.8) * 2.6 + H.blur(bst, 5.5) * 2.4)[..., None] * np.array([1.0, 0.92, 0.80], F32) * 0.55 * (1.0 - 0.8 * dust)[..., None]
    rgb = np.clip(rgb, 0, 1)
    star = np.maximum(np.maximum(cvs[..., 0], cvs[..., 1]), cvs[..., 2])
    fl = (star > 0.10) & (dust < 0.55)
    gl = np.clip(D * (1 - dust), 0, 1)
    M = H.lerp(0.0, 126.0, gl)
    R_ = H.lerp(236.0, 98.0, gl ** 0.8)
    CC = H.lerp(236.0, 28.0, gl)
    M = np.where(fl, 255.0, M)
    R_ = np.where(fl, 0.0, R_)
    CC = np.where(fl, 16.0, CC)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 45. Cosmic Microwave Background
# -------------------------------------------------------------------------
def cmb_map(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 45 Cosmic Microwave Background: the Planck temperature map - blotchy blue and orange-red spots about 30 px wide from a ring-shaped (acoustic peak) power spectrum, fine speckle on top; metal follows temperature
    n = N
    z = H.fft_noise(n, seed + 1, lambda k: np.exp(-((k - 34.0) / 11.0) ** 2) + 0.28 * np.exp(-(k / 9.0) ** 2) + 0.09 * np.exp(-((k - 190.0) / 110.0) ** 2))
    fine = H.fbm(n, seed + 2, cells=(256, 512, 1024), gain=0.9)
    t = np.clip(0.5 + 0.20 * z + 0.035 * fine, 0, 1)
    rgb = H.ramp(t, [(0.0, '#0a0a8c'), (0.14, '#0a30ff'), (0.30, '#4aa0ff'), (0.44, '#e8f0ff'), (0.54, '#fff0b4'),
                     (0.68, '#ffb440'), (0.84, '#ff4410'), (1.0, '#7c0000')])
    ln = np.clip(H.lum(rgb) / 0.85, 0, 1)
    ten = np.abs(t - 0.5) * 2.0
    M = H.lerp(24.0, 236.0, t)
    R_ = H.lerp(188.0, 22.0, ln) + 12.0 * fine * (1 - ten)
    CC = H.lerp(150.0, 16.0, H.sstep(0.1, 0.9, ten))
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 46. Galactic Magnetic Drapery
# -------------------------------------------------------------------------
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


def magnetic_drapery(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 46 Galactic Magnetic Drapery: silky streaks combed along a turbulent curl-noise field (line-integral convolution) - gold folds through deep teal, like Planck dust polarisation; brushed metal along every streak
    n = N
    m = 1024
    r = H.rng(seed)
    u, v = H.curl_field(m, seed + 1, cells=(3, 6, 12, 24), gain=0.62)
    uv = np.dstack([u, v]).astype(F32)
    t1 = r.standard_normal((m, m)).astype(F32)
    z = _lic2(t1, uv, 12, 2.3)
    z = (z - z.mean()) / (z.std() + 1e-6)
    t2 = r.standard_normal((m, m)).astype(F32)
    z2 = _lic2(t2, uv, 5, 1.0)
    z2 = (z2 - z2.mean()) / (z2.std() + 1e-6)
    z = cv2.resize(z, (n, n), interpolation=cv2.INTER_CUBIC)
    z2 = cv2.resize(z2, (n, n), interpolation=cv2.INTER_CUBIC)
    lit = np.clip(0.5 + 0.35 * H.fbm(n, seed + 2, cells=(2, 4, 8), gain=0.6), 0.15, 1.0)
    tt = np.clip(0.50 + 0.22 * z + 0.08 * z2, 0, 1) * (0.55 + 0.7 * lit)
    tt = np.clip(tt, 0, 1)
    hue = np.clip(0.5 + 0.7 * H.fbm(n, seed + 3, cells=(2, 3, 5), gain=0.6), 0, 1)
    teal = H.ramp(tt, [(0.0, '#0a2230'), (0.35, '#106070'), (0.7, '#30b0b8'), (1.0, '#b0f4ee')])
    gold = H.ramp(tt, [(0.0, '#2a1c0c'), (0.35, '#8a5a1c'), (0.7, '#e8b040'), (1.0, '#fff0c0')])
    rgb = teal * (1 - hue)[..., None] + gold * hue[..., None]
    rgb = np.clip(rgb, 0, 1)
    # [S19 coordinator polish A 2026-10-12] spec richness: the spec now carries the paint's structure (matte/rough ground with 1 px flake; lines, arcs, cores = satin then mirror metal)
    M, R_, CC = H.structure_spec(rgb, seed + 91, [(0.30, 0.62, 170.0, 60.0, 30.0), (0.66, 0.90, 250.0, 8.0, 16.0)],
                                 ground_m=(40.0, 90.0), brush=14.0)
    R_ = R_ + 8.0 * z2
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 47. Star Trails
# -------------------------------------------------------------------------
def star_trails(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 47 Star Trails: a long-exposure night sky - about 2,000 short coloured arcs, each star tracing the same angle around one of four off-canvas poles, so the arcs cross in four families; candy trails on a matte night-blue sky
    n = N
    r = H.rng(seed)
    cvs = np.zeros((n, n, 3), np.uint8)
    SC, SH = 16, 4
    pal = np.array([[255, 245, 235], [255, 214, 150], [150, 190, 255], [255, 150, 130], [150, 255, 232], [226, 170, 255]], np.int32)
    pw = np.array([0.30, 0.20, 0.22, 0.10, 0.10, 0.08])
    jobs = []
    for k in range(4):
        a = r.uniform(0, 2 * np.pi)
        rp = r.uniform(1250, 1800)
        px, py = n / 2 + rp * np.cos(a), n / 2 + rp * np.sin(a)
        span = r.uniform(6.0, 14.0)
        for _ in range(520):
            x, y = r.uniform(0, n, 2)
            rho = float(np.hypot(x - px, y - py))
            th = float(np.degrees(np.arctan2(y - py, x - px)))
            sp = span * r.uniform(0.55, 1.45)
            val = float(0.25 + 0.75 * r.random() ** 1.6)
            ci = int(r.choice(6, p=pw))
            jobs.append((val, px, py, rho, th, sp, ci, 1 if val < 0.7 else 2))
    jobs.sort(key=lambda j: j[0])
    for val, px, py, rho, th, sp, ci, tk in jobs:
        col = tuple(int(c * val) for c in pal[ci][::-1])
        dim = tuple(int(c * 0.40) for c in col)
        ctr = (int(round(px * SC)), int(round(py * SC)))
        ax = (int(round(rho * SC)), int(round(rho * SC)))
        cv2.ellipse(cvs, ctr, ax, 0.0, th - sp / 2, th + sp / 2, dim, tk, cv2.LINE_AA, SH)
        cv2.ellipse(cvs, ctr, ax, 0.0, th + 0.05 * sp, th + sp / 2, col, tk, cv2.LINE_AA, SH)
    tr = cvs[..., ::-1].astype(F32) / 255.0
    lum = H.lum(tr)
    Y = np.linspace(0, 1, n, dtype=F32)[:, None]
    gz = _gz(n, seed + 2)
    sky = (np.array([0.040, 0.060, 0.200], F32)[None, None, :] * (1 - Y)[..., None] + np.array([0.075, 0.085, 0.250], F32)[None, None, :] * Y[..., None]) * gz[..., None]
    rgb = sky + tr * 1.1 + (H.blur(lum, 3.0) * 0.6)[..., None] * np.array([0.7, 0.75, 1.0], F32)
    rgb += _specks(n, seed + 3, 0.0025, 0.08, 0.5)[..., None] * np.array([0.8, 0.88, 1.0], F32)
    rgb = np.clip(rgb, 0, 1)
    tm = np.clip(lum * 1.7, 0, 1)
    M = H.lerp(0.0, 222.0, tm)
    R_ = H.lerp(232.0, 22.0, tm ** 0.7)
    CC = H.lerp(236.0, 16.0, H.sstep(0.0, 0.35, tm))
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 48. Tidal Tails
# -------------------------------------------------------------------------
def tidal_tails(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 48 Tidal Tails: ~15 colliding galaxy PAIRS (Antennae look) - two overlapping elliptical gold-cored discs 60-120 px apart, each throwing one long smooth sweeping blue tail (300-800 px, curving 1.2-2.6 rad) of fine star grain that fades outward, a star bridge between the cores, pink star-forming knots; dark matte sky, bright metal minority (coordinator fix 2026-10-12: bead chains -> paired cores + long smooth fading tails)
    n = N
    r = H.rng(seed)
    pc = H.jitter_pts(n, 600.0, seed + 1, jit=0.8, margin=100)
    pc = pc[r.random(len(pc)) < 0.95]
    knots = np.zeros((n, n), F32)
    cores = np.zeros((n, n), F32)
    cores2 = np.zeros((n, n), F32)
    halo = np.zeros((n, n), F32)
    tcol = np.array([0.52, 0.74, 1.0], F32)
    chans = [np.zeros((n, n), F32) for _ in range(3)]
    bs = np.zeros((n, n), F32)

    def stars(path, spread0, spread1, cnt, amp_fall, col, tpow=0.9):
        t = r.random(cnt) ** tpow
        idx = np.minimum((t * (len(path) - 1)).astype(int), len(path) - 2)
        fr = t * (len(path) - 1) - idx
        pos = path[idx] * (1 - fr[:, None]) + path[idx + 1] * fr[:, None]
        tg = path[idx + 1] - path[idx]
        tg = tg / (np.hypot(tg[:, 0], tg[:, 1])[:, None] + 1e-6)
        nm = np.stack([-tg[:, 1], tg[:, 0]], 1)
        sp = spread0 + (spread1 - spread0) * t
        pos = pos + nm * (r.normal(0, 1, cnt) * sp)[:, None] + tg * (r.normal(0, 1, cnt) * 3.0)[:, None]
        v = (0.22 + 0.78 * r.random(cnt) ** 2.2) * (1.0 - amp_fall * t) ** 1.6
        for c in range(3):
            H.points(chans[c], pos[:, 0], pos[:, 1], v * col[c], mode="max")
        H.points(bs, pos[:, 0], pos[:, 1], np.where(v > 0.35, v, 0.0).astype(F32), mode="max")
        return pos

    for i in range(len(pc)):
        c0 = pc[i]
        ang = r.uniform(0, 2 * np.pi)
        sep = r.uniform(60, 120)
        d = np.array([np.cos(ang), np.sin(ang)])
        A, B = c0 - d * sep / 2, c0 + d * sep / 2
        for src, away in ((A, -d), (B, d)):
            L = r.uniform(240, 560)           # [S19 coordinator polish B 2026-10-12] thinner tails that fade into star grain, brighter core pair
            m = 110
            sg_ = r.choice([-1.0, 1.0])
            hd = np.arctan2(away[1], away[0]) + sg_ * r.uniform(0.15, 0.55)
            total = sg_ * r.uniform(0.7, 1.5)
            hh = hd + total * (np.arange(1, m + 1) / float(m)) ** 0.9
            path = np.vstack([src, src + np.cumsum(np.stack([np.cos(hh), np.sin(hh)], 1) * (L / m), 0)])
            stars(path, 4.0, 30.0, int(L * 9), 1.0, tcol, 1.15)
            for tk_ in r.uniform(0.06, 0.88, int(r.integers(34, 56))):
                kp = path[int(tk_ * (len(path) - 1))] + r.normal(0, 11, 2)
                H.points(knots, [kp[0]], [kp[1]], [r.uniform(40.0, 110.0)], mode="add")
            ph = r.uniform(0, np.pi)
            gs = r.normal(0, 1, (2600, 2)) * np.array([r.uniform(24, 32), r.uniform(11, 16)])
            body = src + np.stack([gs[:, 0] * np.cos(ph) - gs[:, 1] * np.sin(ph), gs[:, 0] * np.sin(ph) + gs[:, 1] * np.cos(ph)], 1)
            for c in range(3):
                H.points(chans[c], body[:, 0], body[:, 1], (0.30 + 0.70 * r.random(2600) ** 2.0) * np.array([0.98, 0.90, 0.76], F32)[c], mode="max")
        perp = np.array([-d[1], d[0]]) * r.choice([-1.0, 1.0]) * sep * 0.30
        tt = np.linspace(0, 1, 40)[:, None]
        bridge = (1 - tt) ** 2 * A + 2 * (1 - tt) * tt * ((A + B) / 2 + perp) + tt ** 2 * B
        stars(bridge, 4.0, 12.0, 1100, 0.0, np.array([0.72, 0.80, 1.0], F32), 1.0)
        for p_ in (A, B):
            H.points(cores, [p_[0]], [p_[1]], [r.uniform(26, 44)], mode="add")
            H.points(cores2, [p_[0]], [p_[1]], [r.uniform(6, 11)], mode="add")
            H.points(halo, [p_[0]], [p_[1]], [r.uniform(2200, 3800)], mode="add")
    dw = np.zeros((n, n), F32)
    NDW = 900
    H.points(dw, r.integers(0, n, NDW), r.integers(0, n, NDW), (0.25 + 0.75 * r.random(NDW) ** 1.6).astype(F32))
    dwb = H.blur(dw, 3.5) * 22.0 + H.blur(dw, 8.0) * 60.0
    tails = np.stack([H.blur(c, 0.6) * 1.1 + H.blur(c, 1.2) * 1.3 for c in chans], -1)
    clump = np.clip(0.20 + 1.45 * H.fbm(n, seed + 11, cells=(110, 220, 440), gain=0.9), 0.0, 2.8)
    tails = tails * clump[..., None]
    mx = np.max(tails, axis=2)
    dif = (H.blur(mx, 6.0) * 0.07 + H.blur(mx, 16.0) * 0.02) * np.clip(0.55 + 0.9 * H.fbm(n, seed + 9, cells=(120, 240, 480), gain=0.9), 0.1, 1.5)
    kn = np.clip(H.blur(knots, 5.0) * 0.95, 0, 1.3) * clump
    co = np.clip(H.blur(cores, 14.0) * 2.6 + H.blur(cores2, 4.5) * 1.8, 0, 1.8)
    ha = np.clip(H.blur(halo, 16.0), 0, 1.0)
    gz = _gz(n, seed + 3)
    rgb = np.array([0.060, 0.062, 0.150], F32)[None, None, :] * gz[..., None]
    rgb += tails * 1.25
    rgb += (dwb * 1.0)[..., None] * np.array([0.62, 0.74, 1.0], F32)
    rgb += dif[..., None] * np.array([0.40, 0.58, 1.0], F32)
    rgb += kn[..., None] * np.array([1.0, 0.42, 0.72], F32)
    rgb += (kn * np.clip(0.5 + 1.2 * H.fbm(n, seed + 15, cells=(8, 16), gain=0.6), 0, 1))[..., None] * np.array([0.35, 0.6, 1.0], F32) * 0.8
    rgb += (H.blur(bs, 2.8) * 10.0)[..., None] * tcol * 0.9
    rgb += (ha * 0.16)[..., None] * np.array([1.0, 0.78, 0.45], F32)
    rgb += co[..., None] * np.array([1.0, 0.82, 0.45], F32)
    rgb += _specks(n, seed + 4, 0.003, 0.08, 0.5)[..., None] * np.array([0.8, 0.88, 1.0], F32)
    NB = 110000
    bg = np.zeros((n, n), F32)
    H.points(bg, r.integers(0, n, NB), r.integers(0, n, NB), (0.10 + 0.55 * r.random(NB) ** 2.2).astype(F32))
    rgb += (H.blur(bg, 1.9) * 9.0)[..., None] * np.array([0.78, 0.86, 1.0], F32)
    rgb = np.clip(rgb, 0, 1)
    lm = np.clip(H.lum(rgb), 0, 1)
    mt = H.sstep(0.075, 0.36, lm)
    M = H.lerp(0.0, 236.0, mt)
    R_ = H.lerp(236.0, 20.0, mt)
    CC = H.lerp(240.0, 16.0, mt)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 49. Starburst Superwind
# -------------------------------------------------------------------------
def _plume_master(Hh, sd):
    S = 2 * Hh + 1
    c = Hh
    y0, x0 = np.mgrid[0:S, 0:S].astype(F32)
    x0 -= c
    y0 -= c
    nzw = H.fbm(S, sd, cells=(4, 8, 16), gain=0.65)
    nz2 = H.fbm(S, sd + 1, cells=(9, 18, 36), gain=0.7)
    stn = np.clip(H.ridged(H.fbm(S, sd + 3, cells=(12, 24, 48), gain=0.8) * 1.4), 0, 1)
    plume = np.zeros((S, S), F32)
    for tilt, scl, amp in ((0.0, 1.0, 1.0), (6.0, 0.80, 0.55), (-7.0, 0.74, 0.50)):
        ct, st_ = np.cos(np.radians(tilt)), np.sin(np.radians(tilt))
        x = x0 * ct - y0 * st_
        y = x0 * st_ + y0 * ct
        ay = np.abs(y)
        Hs = Hh * scl
        tn = np.tan(np.radians(13.0))
        w = (0.040 * Hs + ay * tn) * (1.0 + 0.34 * nzw)
        s = (x - 0.34 * y * np.abs(y) / Hs + 7.0 * nz2 * (ay / Hs)) / (w + 1e-3)
        inside = H.sstep(1.30, 0.75, np.abs(s)) * H.sstep(0.02 * Hs, 0.12 * Hs, ay) * (1.0 - H.sstep(0.78 * Hs, 1.0 * Hs, ay))
        ph = s * np.pi * 11.0 + 4.0 * nzw + 2.6 * nz2 * (ay / Hs)
        st = 0.5 + 0.5 * np.cos(ph)
        fil = (0.06 + 0.94 * st ** 2.8) * (0.40 + 0.60 * stn)
        limb = np.exp(-((np.abs(s) - 0.90) / 0.12) ** 2)
        body = inside * np.exp(-ay / (0.55 * Hs)) * np.where(y > 0, 1.0, 0.55)
        plume += amp * (body * fil * (1.0 + 0.8 * limb) + 0.08 * body * (0.6 + 0.4 * nz2))
    disc = np.exp(-((x0 / (0.15 * Hh)) ** 2 + (y0 / (0.022 * Hh)) ** 2)) * (1.0 - 0.55 * np.exp(-(y0 / (0.008 * Hh)) ** 2))
    disc += 0.7 * np.exp(-((x0 / (0.045 * Hh)) ** 2 + (y0 / (0.018 * Hh)) ** 2))
    return np.stack([plume, disc], -1).astype(F32)


def starburst_wind(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 49 Starburst Superwind: edge-on starburst galaxies, each a small bright disc blowing a wobbly double cone of red H-alpha filaments up and down (limb-brightened, fading with height), ~40 of them at random angles; candy-red plumes, satin discs, matte sky (visual pass: straight bow-tie fans -> turbulent wobbling filaments)
    n = N
    r = H.rng(seed)
    NR = 12
    sizes = (100, 148, 200)
    tiles = []
    for ci, Hh in enumerate(sizes):
        for v in range(2):
            tiles += H.rotset(_plume_master(Hh, seed * 3 + ci * 11 + v), NR, np.pi)
    pts = H.jitter_pts(n, 215.0, seed + 1, jit=0.9, margin=100)
    pts = pts[r.random(len(pts)) < 0.70]
    K = len(pts)
    cl = r.choice(3, K, p=[0.30, 0.42, 0.28])
    vv = r.integers(0, 2, K)
    rt = r.integers(0, NR, K)
    ti = (cl * 2 + vv) * NR + rt
    cv = np.zeros((n, n, 2), F32)
    H.splat(cv, tiles, ti, pts[:, 0], pts[:, 1], mode="add", flip=r.integers(0, 4, K), amp=r.uniform(0.75, 1.15, K))
    plume = np.clip(cv[..., 0], 0, 1.6)
    disc = np.clip(cv[..., 1], 0, 1.5)
    pc = H.ramp(np.clip(plume / 1.2, 0, 1), [(0.0, '#1c0e24'), (0.22, '#6a0c20'), (0.50, '#e0261a'), (0.80, '#ff7a54'), (1.0, '#fff0e0')])
    gz = _gz(n, seed + 3)
    rgb = pc * (0.55 + 0.45 * gz[..., None])
    rgb += (H.blur(plume, 6.0) * 0.12)[..., None] * np.array([0.8, 0.12, 0.10], F32)
    rgb += (disc * 1.0)[..., None] * np.array([1.0, 0.94, 0.80], F32)
    rgb += _specks(n, seed + 4, 0.003, 0.08, 0.5)[..., None] * np.array([0.9, 0.85, 0.9], F32)
    rgb = np.clip(rgb, 0, 1)
    pl = np.clip(plume * 1.1, 0, 1)
    dc = np.clip(disc, 0, 1)
    M = H.lerp(0.0, 215.0, pl)
    M = H.lerp(M, 150.0, dc)
    R_ = H.lerp(238.0, 24.0, pl ** 0.7)
    R_ = H.lerp(R_, 80.0, dc)
    CC = H.lerp(236.0, 16.0, H.sstep(0.0, 0.3, pl))
    CC = H.lerp(CC, 42.0, dc)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 50. Gamma-Ray Photon Counts
# -------------------------------------------------------------------------
def photon_counts(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 50 Gamma-Ray Photon Counts: a pixelated sky map of 12 px diamond-shaped detector pixels, each coloured by its Poisson photon count on a black-purple-orange-yellow heat map, with bright point-source clusters; every diamond has its own clearcoat
    n = N
    r = H.rng(seed)
    q = 12.0
    s2 = np.float32(np.sqrt(2.0))
    X, Y = H.xy(n)
    a = (X + Y) / s2
    b = (X - Y) / s2
    fa = a / F32(q)
    fb = b / F32(q)
    offb = int(np.floor(-(n - 1) / np.sqrt(2.0) / q))
    ia = np.floor(fa).astype(np.int32)
    ib = np.floor(fb).astype(np.int32) - offb
    ca = (np.arange(ia.max() + 1) + 0.5) * q
    cb = (np.arange(ib.max() + 1) + offb + 0.5) * q
    CA, CB = np.meshgrid(ca, cb, indexing="ij")
    cxx = ((CA + CB) / np.sqrt(2.0)).astype(F32)
    cyy = ((CA - CB) / np.sqrt(2.0)).astype(F32)
    m = 512
    fm = H.fbm(m, seed + 1, cells=(3, 6, 12, 24), gain=0.62)
    lam = np.exp(1.0 * fm + 0.2) * 0.9
    Xm, Ym = H.xy(m)
    NSRC = 110
    sxp = r.uniform(0, m, NSRC)
    syp = r.uniform(0, m, NSRC)
    sa = np.exp(r.uniform(np.log(12.0), np.log(450.0), NSRC))
    ss_ = r.uniform(1.4, 2.8, NSRC)
    for k in range(NSRC):
        R4 = int(ss_[k] * 4.5) + 1
        x0, x1 = max(0, int(sxp[k]) - R4), min(m, int(sxp[k]) + R4 + 1)
        y0, y1 = max(0, int(syp[k]) - R4), min(m, int(syp[k]) + R4 + 1)
        lam[y0:y1, x0:x1] += F32(sa[k]) * np.exp(-((Xm[y0:y1, x0:x1] - F32(sxp[k])) ** 2 + (Ym[y0:y1, x0:x1] - F32(syp[k])) ** 2) / F32(2 * ss_[k] ** 2))
    # diffuse band across the map
    lam += 6.0 * np.exp(-((Xm - Ym * 0.6 - 120.0) / 60.0) ** 2)
    px_ = (cxx * (m / n)).clip(0, m - 1.001)
    py_ = (cyy * (m / n)).clip(0, m - 1.001)
    lc = H.sample(lam.astype(F32), px_, py_)
    cnt = r.poisson(np.maximum(lc, 0.0)).astype(F32)
    cm = cnt[ia, ib]
    tt = np.clip(np.log1p(cm) / np.log(280.0), 0, 1)
    rgb = H.ramp(tt, [(0.0, '#220c38'), (0.12, '#3a1060'), (0.34, '#8a1c70'), (0.56, '#e0501a'), (0.78, '#ffaa22'), (1.0, '#fff8b0')])
    ea = np.minimum(fa - np.floor(fa), 1.0 - (fa - np.floor(fa)))
    eb = np.minimum(fb - np.floor(fb), 1.0 - (fb - np.floor(fb)))
    gap = H.sstep(0.0, 0.085, np.minimum(ea, eb))
    rgb = rgb * (0.30 + 0.70 * gap)[..., None]
    rgb = np.clip(rgb, 0, 1)
    key = (ia.astype(np.int64) * 7919 + ib.astype(np.int64) * 104729)
    hs = H.hash01(key, seed)
    t2 = tt * gap
    M = H.lerp(30.0, 236.0, t2) * gap
    R_ = H.lerp(150.0, 28.0, t2 ** 0.8)
    R_ = H.lerp(255.0, R_, gap)
    CC = H.lerp(16.0, 205.0, hs ** 1.2)
    CC = H.lerp(255.0, CC, gap)
    return H.finish_out(rgb, H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
FINISHES = [
    ("cz_cosmic_web", "Cosmic Web",
     "Thin blue filaments joining bright white-gold nodes around dark voids, at two nested scales.", cosmic_web),
    ("cz_galaxy_zoo", "Galaxy Zoo",
     "Hundreds of tiny galaxies: spirals, ellipticals, edge-on discs and irregulars in every colour.", galaxy_zoo),
    ("cz_globular_swarm", "Globular Star Swarm",
     "Round clusters of pinpoint stars thickening to bright cores, scattered over a fine field of lone stars.", globular_swarm),
    ("cz_galactic_rift", "Galactic Dust Rift",
     "A glowing cream-gold star cloud torn by dark brown branching dust lanes, deep blue space showing through.", galactic_rift),
    ("cz_cmb_map", "Cosmic Microwave Background",
     "The Planck temperature map: blotchy blue and orange-red spots with fine speckle.", cmb_map),
    ("cz_magnetic_drapery", "Galactic Magnetic Drapery",
     "Silky gold-to-teal streaks combed into swirling eddies along a turbulent magnetic field.", magnetic_drapery),
    ("cz_star_trails", "Star Trails",
     "Short coloured arcs of a long-exposure night sky, crossing in four families around off-canvas poles.", star_trails),
    ("cz_tidal_tails", "Tidal Tails",
     "Long curved tails of white stars with pink knots, thickest at a bright galaxy core and fading into star grain.", tidal_tails),
    ("cz_starburst_wind", "Starburst Superwind",
     "Edge-on galaxies blowing double cones of red filaments up and down.", starburst_wind),
    ("cz_photon_counts", "Gamma-Ray Photon Counts",
     "A map of diamond detector pixels coloured by photon count, black-purple to hot yellow, with bright sources.", photon_counts),
]
