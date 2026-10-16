# -*- coding: utf-8 -*-
"""WORLDS chapter (cz_ 21-30): surfaces and skies of planets, moons and comets.

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


def _prof(length, sizes, seed, gain=0.75, res=1.0):
    """1-D multi-scale noise profile, unit-ish std; `sizes` are feature sizes in profile samples."""
    rg = H.rng(seed)
    acc = np.zeros(length, F32)
    nrm = 0.0
    for i, sz in enumerate(sizes):
        c = max(2, int(length / sz))
        t = cv2.resize(rg.standard_normal((1, c)).astype(F32), (length, 1), interpolation=cv2.INTER_CUBIC)[0]
        w = gain ** i
        acc += F32(w) * t
        nrm += w * w
    return acc / F32(np.sqrt(nrm))


# -------------------------------------------------------------------------
# 21. Jovian Storm Belts
# -------------------------------------------------------------------------
def jovian_belts(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 21 Jovian Storm Belts: wandering zonal bands from a 1-D profile, Kelvin-Helmholtz curl warp concentrated on belt edges, white and red storm ovals with swirl arcs
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)
    off = 400
    drift = 80.0 * H.fbm(n, seed + 1, cells=(2, 3, 5), gain=0.6)
    prof = _prof(n + 2 * off, (210, 110, 52, 24, 11), seed + 2, gain=0.8)
    idx = np.clip((Y + drift + off).astype(np.int32), 0, n + 2 * off - 1)
    tone = prof[idx]
    g1 = np.abs(np.gradient(prof))
    edge = np.clip(g1[idx] / (float(np.percentile(g1, 90)) + 1e-6), 0, 1.4)
    dx = 52.0 * edge * H.fbm(n, seed + 3, cells=(34, 68, 136), gain=0.8) + 12.0 * H.fbm(n, seed + 4, cells=(150, 300), gain=0.8)
    dy = 36.0 * edge * H.fbm(n, seed + 5, cells=(34, 68, 136), gain=0.8) + 8.0 * H.fbm(n, seed + 6, cells=(150, 300), gain=0.8)
    tone = H.warp(tone.astype(F32), dx.astype(F32), dy.astype(F32))
    sc = 16
    ov = np.zeros((n, n), np.uint8)
    ovr = np.zeros((n, n), np.uint8)
    ring = np.zeros((n, n), np.uint8)
    for i in range(38):
        cx, cy = r.uniform(0, n, 2)
        a = float(r.uniform(36.0, 130.0))
        b = a * float(r.uniform(0.5, 0.72))
        ang = float(r.normal(0, 6))
        tgt = ovr if r.random() < 0.28 else ov
        cv2.ellipse(tgt, (int(cx * sc), int(cy * sc)), (int(a * sc), int(b * sc)), ang, 0, 360, 255, -1, cv2.LINE_AA, 4)
        for q, t0 in ((0.74, 30), (0.46, 100)):
            cv2.ellipse(ring, (int(cx * sc), int(cy * sc)), (int(a * q * sc), int(b * q * sc)), ang, t0, t0 + 270, 255, 2, cv2.LINE_AA, 4)
    ovf = H.warp(H.blur(ov.astype(F32) / 255.0, 1.3), (dx * 0.3).astype(F32), (dy * 0.3).astype(F32))
    ovrf = H.warp(H.blur(ovr.astype(F32) / 255.0, 1.3), (dx * 0.3).astype(F32), (dy * 0.3).astype(F32))
    rg_ = H.warp(H.blur(ring.astype(F32) / 255.0, 1.0), (dx * 0.3).astype(F32), (dy * 0.3).astype(F32))
    streak = _snoise(1500, 36, seed + 7)
    streak2 = _snoise(520, 64, seed + 9)
    t = H.sstep(-2.0, 2.0, tone) + 0.07 * streak + 0.22 * streak2 + 0.22 * H.fbm(n, seed + 8, cells=(64, 128, 256), gain=0.9)
    t = np.clip(t, 0, 1)
    rgb = H.ramp(t, [(0.0, '#5a2a16'), (0.2, '#9a5a30'), (0.4, '#c89060'), (0.62, '#e8cfa4'), (0.82, '#f6ecd0'), (1.0, '#fffaf0')])
    rgb = rgb * (1 - ovf)[..., None] + ovf[..., None] * np.array([0.98, 0.95, 0.88], F32)
    rgb = rgb * (1 - ovrf)[..., None] + ovrf[..., None] * np.array([0.74, 0.24, 0.12], F32)
    rgb = rgb * (1 - 0.35 * rg_)[..., None]
    lt = np.clip(H.lum(rgb) / 0.85, 0, 1)
    M = H.lerp(70.0, 40.0, lt) + 120.0 * ovrf
    R = H.lerp(150.0, 46.0, lt)
    CC = H.lerp(80.0, 16.0, lt)
    return H.finish_out(rgb, H.spec_pack(np.clip(M, 0, 255), R, CC))


# -------------------------------------------------------------------------
# 22. Ringlet Grooves
# -------------------------------------------------------------------------
def ringlet_grooves(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 22 Ringlet Grooves: distance from two far off-canvas centres -> 1-D multi-scale radial noise + chirped density waves, blended by a low-frequency mask; spoke shadows from stretched noise
    n = N
    X, Y = H.xy(n)
    cA, cB = (-1400.0, 3000.0), (3600.0, -1000.0)
    L1 = 5200 * 2
    wide = np.arange(L1, dtype=F32) * F32(0.5)

    def lookup(cx, cy, sd):
        rr = np.hypot(X - F32(cx), Y - F32(cy))
        ix = np.clip((rr * 2.0).astype(np.int32), 0, L1 - 1)
        P = _prof(L1, (5.0, 10.0, 22.0, 52.0, 140.0, 440.0), sd, gain=0.82)
        P = P + 0.45 * np.sin(wide * (0.11 + 0.000025 * wide))
        tone1 = H.sstep(-0.35, 0.8, P)
        S = _prof(L1, (900.0, 2600.0), sd + 5, gain=0.7)
        return tone1[ix], S[ix]

    tA, sA = lookup(*cA, seed + 1)
    tB, sB = lookup(*cB, seed + 2)
    m = H.sstep(-0.35, 0.35, H.fbm(n, seed + 3, cells=(2, 3)))
    tone = tA * m + tB * (1 - m)
    sdr = sA * m + sB * (1 - m)
    sp = H.sstep(0.55, 1.5, _snoise(3, 60, seed + 7, ang=float(np.arctan2(1024 - 3000, 1024 + 1400)))) * H.sstep(-0.2, 0.5, H.fbm(n, seed + 9, cells=(3, 6)))
    tone = np.clip(tone * (1 - 0.6 * sp) + 0.10 * H.fbm(n, seed + 11, cells=(160, 320, 640), gain=0.9), 0, 1)
    ch = H.ramp(tone, [(0.0, '#060504'), (0.25, '#5a4e3c'), (0.6, '#c8b894'), (1.0, '#f2e4c0')])
    gr = H.ramp(tone, [(0.0, '#050506'), (0.25, '#44484e'), (0.6, '#a8b0ba'), (1.0, '#e4eaf2')])
    mm = H.sstep(-0.4, 0.4, sdr)[..., None]
    rgb = ch * (1 - mm) + gr * mm
    br = H.fbm(n, seed + 12, cells=(256, 512, 1024), gain=0.9)
    M = H.lerp(10.0, 230.0, tone)
    R = H.lerp(200.0, 40.0, tone) + 14.0 * br * tone
    CC = H.lerp(255.0, 40.0, tone)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 23. Io Lava Paterae
# -------------------------------------------------------------------------
def io_paterae(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 23 Io Lava Paterae: fbm sulfur palette + poisson calderas via normalised Voronoi distance (black floor, glowing rim, red ring deposits, lava cracks)
    n = N
    r = H.rng(seed)
    pts = H.jitter_pts(n, 168.0, seed + 1, jit=0.9, margin=40)
    pts = pts[r.random(len(pts)) < 0.80]
    d, lab, sx, sy = H.voronoi(n, pts)
    K = len(sx)
    rad = np.concatenate([[1.0], r.uniform(11.0, 24.0, K)]).astype(F32)
    q = d / (rad[lab] * (1.0 + 0.22 * H.fbm(n, seed + 2, cells=(24, 48, 96, 192))))
    t = np.clip(0.5 + 0.30 * H.fbm(n, seed + 3, cells=(3, 6, 12, 24, 48, 96)) + 0.14 * H.fbm(n, seed + 4, cells=(160, 320, 640), gain=0.9), 0, 1)
    rgb = H.ramp(t, [(0.0, '#c89a10'), (0.28, '#f0cc20'), (0.5, '#f8f2b8'), (0.72, '#f09020'), (1.0, '#d05010')])
    nz = 0.7 + 0.3 * H.fbm(n, seed + 5, cells=(12, 24, 48))
    red = np.exp(-((q - 2.3) / 0.50) ** 2) * nz
    dk = np.exp(-((q - 1.55) / 0.10) ** 2) * 0.6
    halo = np.exp(-((q - 3.0) / 0.9) ** 2) * 0.25
    rgb = rgb * (1 - 0.85 * red)[..., None] + (0.85 * red)[..., None] * np.array([0.78, 0.16, 0.06], F32)
    rgb = rgb * (1 - dk)[..., None] + halo[..., None] * np.array([1.0, 0.95, 0.7], F32) * 0.4
    cal = 1.0 - H.sstep(0.92, 1.05, q)
    rim = np.exp(-((q - 1.12) / 0.12) ** 2)
    crack = H.zero_set_line(H.fbm(n, seed + 6, cells=(60, 120, 240), gain=0.8), 1.2)
    rgb = rgb * (1 - cal)[..., None] + cal[..., None] * np.array([0.025, 0.018, 0.018], F32)
    rgb += (rim * (1 - cal))[..., None] * np.array([1.0, 0.55, 0.12], F32) * 0.9
    rgb += (cal * crack)[..., None] * np.array([0.95, 0.16, 0.05], F32) * 0.75
    lt = np.clip(H.lum(np.clip(rgb, 0, 1)) / 0.9, 0, 1)
    M = H.lerp(6.0, 30.0, lt) + 225.0 * rim * (1 - cal) + 60.0 * cal
    R = H.lerp(218.0, 150.0, t) * (1 - cal) + 14.0 * cal
    R = R - 120.0 * rim * (1 - cal)
    CC = H.lerp(255.0, 190.0, t) * (1 - cal) + 16.0 * cal
    CC = np.where(rim > 0.4, 16.0, CC)
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(np.clip(M, 0, 255), np.clip(R, 0, 255), CC))


# -------------------------------------------------------------------------
# 24. Europa Lineae
# -------------------------------------------------------------------------
def europa_lineae(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 24 Europa Lineae: cracked Voronoi ice rafts crossed by long CURVED double ridges (reddish-brown band with a pale centre line): constant-curvature arcs of every size plus cycloid scallop chains, dense, four width classes (wave-2 review: twigs/sticks -> arcs and cycloids)
    n = N
    r = H.rng(seed)
    pts = H.jitter_pts(n, 120.0, seed + 1, jit=0.95, margin=40)
    d, lab, sx, sy = H.voronoi(n, pts)
    K = len(sx)
    pt = np.concatenate([[0.0], r.uniform(-1, 1, K)]).astype(F32)
    ed = H.edge_dist(lab)
    t = np.clip(0.50 + 0.10 * pt[lab] + 0.08 * H.fbm(n, seed + 2, cells=(3, 6, 12, 24)) + 0.07 * H.fbm(n, seed + 3, cells=(128, 256, 512), gain=0.9), 0, 1)
    ice = H.ramp(t, [(0.0, '#7a94b4'), (0.5, '#c4d6ea'), (1.0, '#eef5fb')])
    ice = ice * (1 - 0.30 * (1 - H.sstep(0.3, 1.8, ed)))[..., None]

    def arc(R, L, cx, cy, th, sg):
        m = max(8, int(L / 10))
        a = th + sg * np.linspace(0, L / R, m)
        return np.stack([cx + sg * R * (np.sin(a) - np.sin(th)), cy - sg * R * (np.cos(a) - np.cos(th))], 1)

    def chain(base, rho):
        # scallops: circular arcs of radius rho over successive baseline chords (cusps at the joints)
        seg = 2.0 * rho * 0.86
        out = []
        P = base
        # resample baseline by arclength
        dl = np.hypot(*np.diff(P, axis=0).T)
        cl = np.concatenate([[0], np.cumsum(dl)])
        k = np.arange(0, cl[-1], seg)
        Q = np.stack([np.interp(k, cl, P[:, 0]), np.interp(k, cl, P[:, 1])], 1)
        side = 1.0 if r.random() < 0.5 else -1.0
        for i in range(len(Q) - 1):
            a, b = Q[i], Q[i + 1]
            ch = b - a
            L_ = float(np.hypot(*ch)) + 1e-6
            nrm = np.array([-ch[1], ch[0]]) / L_
            dd = float(np.sqrt(max(rho * rho - (L_ / 2) ** 2, 1e-6)))
            ctr = (a + b) / 2 - side * nrm * dd
            a0 = np.arctan2(a[1] - ctr[1], a[0] - ctr[0])
            a1 = np.arctan2(b[1] - ctr[1], b[0] - ctr[0])
            da = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi
            tt = a0 + da * np.linspace(0, 1, 14)
            seg_ = np.stack([ctr[0] + rho * np.cos(tt), ctr[1] + rho * np.sin(tt)], 1)
            out.append(seg_)
        return np.concatenate(out, 0) if out else None

    band_p, band_v, band_t = [], [], []
    for tk, cnt, Lr, Rr in ((20, 6, (900, 2000), (500, 2800)), (13, 14, (500, 1500), (260, 2200)),
                            (7, 26, (300, 1000), (140, 1400)), (3, 50, (120, 520), (70, 700))):
        for _ in range(cnt):
            L = float(r.uniform(*Lr))
            R = float(np.exp(r.uniform(np.log(Rr[0]), np.log(Rr[1]))))
            L = min(L, 2.3 * R)
            P = arc(R, L, float(r.uniform(-100, n + 100)), float(r.uniform(-100, n + 100)), float(r.uniform(0, 2 * np.pi)), 1.0 if r.random() < 0.5 else -1.0)
            band_p.append(P)
            band_v.append(int(150 + 105 * r.random()))
            band_t.append(tk)
    for tk, cnt, rho in ((7, 8, (60, 120)), (4, 16, (26, 60))):
        for _ in range(cnt):
            x, y = r.uniform(0, n, 2)
            th = float(r.uniform(0, 2 * np.pi))
            m = 60
            hd = th + np.cumsum(r.normal(0, 0.03, m)) + np.linspace(0, float(r.uniform(-0.8, 0.8)), m)
            base = np.stack([x + np.cumsum(14 * np.cos(hd)), y + np.cumsum(14 * np.sin(hd))], 1)
            Pc = chain(base, float(r.uniform(*rho)))
            if Pc is not None:
                band_p.append(Pc)
                band_v.append(int(150 + 105 * r.random()))
                band_t.append(tk)
    band = np.zeros((n, n), np.uint8)
    cen = np.zeros((n, n), np.uint8)
    for tk in (20, 13, 7, 4, 3):
        sel = [i for i in range(len(band_p)) if band_t[i] == tk]
        if not sel:
            continue
        H.lines_u8(n, [band_p[i] for i in sel], np.array([band_v[i] for i in sel], np.int32), thick=tk, canvas=band)
        H.lines_u8(n, [band_p[i] for i in sel], np.full(len(sel), 255, np.int32), thick=max(1, tk // 3), canvas=cen)
    sh = []
    for i in range(320):
        x, y = r.uniform(0, n, 2)
        th = float(r.uniform(0, 2 * np.pi))
        L = float(r.uniform(30, 130))
        sh.append(np.array([[x, y], [x + np.cos(th) * L * 0.5, y + np.sin(th) * L * 0.5 + r.normal(0, 4)], [x + np.cos(th) * L, y + np.sin(th) * L]]))
    fine = H.lines_u8(n, sh, np.full(len(sh), 110, np.int32), thick=1)
    bd = H.blur(band.astype(F32) / 255.0, 0.9)
    cn = H.blur(cen.astype(F32) / 255.0, 0.7)
    fn_ = fine.astype(F32) / 255.0
    stain = np.clip(H.blur(bd, 8.0) * 1.3 + bd, 0, 1)
    brown = H.ramp(np.clip(0.35 + 0.4 * H.fbm(n, seed + 7, cells=(24, 48, 96, 192)), 0, 1), [(0.0, '#3a1a10'), (0.5, '#6a3420'), (1.0, '#9a5638')])
    rgb = ice * (1 - 0.30 * fn_)[..., None]
    rgb = rgb * (1 - 0.82 * stain)[..., None] + (0.82 * stain)[..., None] * brown
    rgb = rgb * (1 - 0.75 * cn)[..., None] + (0.75 * cn)[..., None] * np.array([0.93, 0.88, 0.80], F32)
    ms = np.clip(stain + cn, 0, 1)
    M = H.lerp(24.0, 6.0, stain)
    R = H.lerp(H.lerp(62.0, 28.0, t), 205.0, np.clip(stain, 0, 1))
    R = H.lerp(R, 40.0, cn)
    CC = H.lerp(16.0, 255.0, np.clip(stain, 0, 1))
    CC = H.lerp(CC, 24.0, cn)
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 25. Titan Methane Rivers
# -------------------------------------------------------------------------
def titan_channels(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 25 Titan Methane Rivers: branching drainage network grown by random walkers that spawn tributaries (5 generations, thinner each), over orange haze land; mirror channels
    n = N
    rg = np.random.default_rng(seed + 5)
    gens = [[] for _ in range(5)]
    stack = []
    for i in range(34):
        side = int(rg.integers(0, 4))
        t = float(rg.uniform(0.05, 0.95)) * n
        if side == 0:
            x, y, a = t, -40.0, np.pi / 2
        elif side == 1:
            x, y, a = t, n + 40.0, -np.pi / 2
        elif side == 2:
            x, y, a = -40.0, t, 0.0
        else:
            x, y, a = n + 40.0, t, np.pi
        stack.append((x, y, a + float(rg.normal(0, 0.5)), int(rg.integers(80, 130)), 0))
    while stack:
        x, y, a, Ls, g = stack.pop()
        tt = a + np.cumsum(rg.normal(0, 0.14, Ls))
        xs = x + np.cumsum(6.5 * np.cos(tt))
        ys = y + np.cumsum(6.5 * np.sin(tt))
        ok = (xs > -120) & (xs < n + 120) & (ys > -120) & (ys < n + 120)
        if not ok.all():
            k = int(np.argmin(ok))
            xs, ys, tt = xs[:k], ys[:k], tt[:k]
        if len(xs) < 2:
            continue
        gens[g].append(np.stack([xs, ys], 1))
        if g < 4:
            pb = 0.075 - 0.012 * g
            br = np.nonzero(rg.random(len(xs)) < pb)[0]
            for k in br:
                stack.append((float(xs[k]), float(ys[k]), float(tt[k] + rg.choice([-1.0, 1.0]) * rg.uniform(0.45, 1.0)),
                              max(6, int(Ls * rg.uniform(0.38, 0.62))), g + 1))
    cvs = np.zeros((n, n), np.uint8)
    for g, th in enumerate((6, 4, 3, 2, 1)):
        if gens[g]:
            H.lines_u8(n, gens[g], np.full(len(gens[g]), 255, np.int32), thick=th, canvas=cvs)
    c = cvs.astype(F32) / 255.0
    cs_ = H.blur(c, 1.0)
    land_t = np.clip(0.5 + 0.28 * H.fbm(n, seed + 1, cells=(3, 6, 12, 24, 48)) + 0.14 * H.ridged(H.fbm(n, seed + 2, cells=(96, 192, 384), gain=0.85)) - 0.07, 0, 1)
    land = H.ramp(land_t, [(0.0, '#4a1c06'), (0.4, '#a8481a'), (0.75, '#e08430'), (1.0, '#f8c060')])
    land = land * (1 - 0.40 * H.blur(c, 14.0))[..., None]
    bank = np.clip(H.blur(c, 4.0) - c, 0, 1)
    rgb = land * (1 - 0.94 * cs_)[..., None] + (0.94 * cs_)[..., None] * np.array([0.045, 0.028, 0.02], F32)
    rgb += (bank * 0.5)[..., None] * np.array([0.9, 0.5, 0.2], F32) * 0.4
    M = H.lerp(90.0, 255.0, cs_)
    R = H.lerp(H.lerp(150.0, 100.0, land_t), 4.0, cs_)
    CC = H.lerp(80.0, 16.0, cs_)
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 26. Martian Dust Devil Tracks
# -------------------------------------------------------------------------
def dust_devil_tracks(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 26 Dust Devil Tracks: 300 Brownian-with-momentum walkers (angular velocity memory) drawn as thin dark loops over rust-tan ground; tracks polished (lower roughness)
    n = N
    r = H.rng(seed)
    K, steps = 300, 520
    th = r.uniform(0, 2 * np.pi, K)
    om = np.zeros(K)
    pos = r.uniform(-60, n + 60, (K, 2))
    out = np.empty((K, steps, 2), F32)
    for i in range(steps):
        om = 0.93 * om + r.normal(0, 0.075, K)
        th = th + om
        pos[:, 0] += 3.2 * np.cos(th)
        pos[:, 1] += 3.2 * np.sin(th)
        out[:, i] = pos
    vals = (150 + 105 * r.random(K) ** 0.8).astype(np.int32)
    thick2 = r.random(K) < 0.30
    cvs = H.lines_u8(n, [out[i] for i in range(K) if not thick2[i]], vals[~thick2], thick=2)
    H.lines_u8(n, [out[i] for i in range(K) if thick2[i]], vals[thick2], thick=3, canvas=cvs)
    T = cvs.astype(F32) / 255.0
    Ts = H.blur(T, 0.8)
    t = np.clip(0.5 + 0.26 * H.fbm(n, seed + 1, cells=(3, 6, 12, 24, 48)) + 0.12 * H.fbm(n, seed + 2, cells=(128, 256, 512), gain=0.9), 0, 1)
    rgb = H.ramp(t, [(0.0, '#9a6a40'), (0.5, '#c8a074'), (1.0, '#e6d2ac')])
    fringe = np.clip(H.blur(T, 3.4) - Ts * 0.8, 0, 1)
    rgb = rgb * (1 - 0.82 * Ts)[..., None] + (0.82 * Ts)[..., None] * np.array([0.16, 0.08, 0.05], F32)
    rgb += (fringe * 0.35)[..., None] * np.array([0.9, 0.6, 0.38], F32)
    M = H.lerp(6.0, 40.0, Ts)
    R = H.lerp(H.lerp(215.0, 185.0, t), 60.0, np.clip(Ts * 1.2, 0, 1))
    CC = H.lerp(255.0, 120.0, Ts)
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 27. Lunar Ray Craters
# -------------------------------------------------------------------------
def ray_craters(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 27 Lunar Ray Craters: a relief-shaded crater field (bowl + raised rim, lit from the upper left, shadow inside the opposite wall) at six size classes, plus long thin bright ejecta rays 3-8 crater radii from a few fresh craters that run across their neighbours (wave-2 review: dandelion splats -> real crater bowls)
    n = N
    r = H.rng(seed)
    h = np.zeros((n, n), F32)
    alb = np.zeros((n, n), F32)
    big = []
    for R, cnt in ((6, 1100), (10, 480), (16, 210), (26, 92), (42, 34), (66, 11)):
        S = 2 * int(1.9 * R) + 1
        gy, gx = np.mgrid[0:S, 0:S].astype(F32)
        rr = np.hypot(gx - S // 2, gy - S // 2) / F32(R)
        prof = np.where(rr < 1.0, -(1.0 - rr ** 2) * 0.55, 0.0) + 0.34 * np.exp(-((rr - 1.0) / 0.22) ** 2) + 0.10 * np.exp(-((rr - 1.45) / 0.45) ** 2)
        tile = (prof * R).astype(F32)
        rim_t = np.exp(-((rr - 1.0) / 0.17) ** 2).astype(F32)
        xs = r.uniform(0, n, cnt)
        ys = r.uniform(0, n, cnt)
        amp = (0.45 + 0.75 * r.random(cnt)).astype(F32)
        z0 = np.zeros(cnt, np.int64)
        H.splat(h, [tile], z0, xs, ys, amp=amp, mode="add")
        fresh = r.random(cnt) < (0.22 if R >= 16 else 0.05)
        if fresh.any():
            H.splat(alb, [rim_t], z0[fresh], xs[fresh], ys[fresh], amp=amp[fresh], mode="add")
        if R >= 42:
            for i in range(cnt):
                big.append((xs[i], ys[i], float(R)))
    h += 1.1 * H.fbm(n, seed + 3, cells=(96, 192, 384), gain=0.85)
    hs = H.blur(h, 0.7)
    gy, gx = np.gradient(hs)
    b = 0.5 + 1.25 * 0.7071 * (gx + gy)
    f = np.clip(1.0 + 1.6 * (b - 0.5), 0.12, 1.9)
    rays = np.zeros((n, n), np.uint8)
    nrc = min(14, len(big))
    sel = r.choice(len(big), nrc, replace=False) if len(big) else []
    for ci in sel:
        x, y, R = big[ci]
        nr = int(r.integers(55, 100))
        ncl = int(r.integers(5, 10))
        cc = r.uniform(0, 2 * np.pi, ncl)
        an = cc[r.integers(0, ncl, nr)] + r.normal(0, 0.20, nr)
        polys, vals = [], []
        for a_ in an:
            Lr = R * (3.0 + 5.0 * float(r.random() ** 1.5))
            ca, sa = float(np.cos(a_)), float(np.sin(a_))
            r0 = 1.15 * R
            v0 = int(80 + 150 * r.random())
            for sg in range(3):
                d0, d1 = r0 + (Lr - r0) * sg / 3.0, r0 + (Lr - r0) * (sg + 1) / 3.0
                polys.append(np.array([[x + ca * d0, y + sa * d0], [x + ca * d1, y + sa * d1]]))
                vals.append(int(v0 * (1.0 - 0.28 * sg)))
        H.lines_u8(n, polys, np.array(vals, np.int32), thick=1, canvas=rays)
    ry = rays.astype(F32) / 255.0
    t = np.clip(0.5 + 0.20 * H.fbm(n, seed + 2, cells=(3, 6, 12, 24, 48)) + 0.12 * H.fbm(n, seed + 4, cells=(128, 256, 512), gain=0.9), 0, 1)
    reg = H.ramp(t, [(0.0, '#161618'), (0.5, '#46464a'), (1.0, '#80807f')])
    bone = np.array([0.93, 0.90, 0.82], F32)
    rgb = reg * f[..., None]
    rgb += (np.clip(alb, 0, 1) * 0.42)[..., None] * bone
    rgb += (ry * 0.85 + 0.40 * H.blur(ry, 1.6))[..., None] * bone
    fl = H.flake_mask(n, 0.30, seed + 11) & (ry > 0.25)
    lt = np.clip(H.lum(np.clip(rgb, 0, 1)) / 0.9, 0, 1)
    M = H.lerp(0.0, 40.0, lt)
    R_ = H.lerp(228.0, 120.0, lt)
    CC = H.lerp(255.0, 150.0, lt)
    M[fl] = 255.0
    R_[fl] = 6.0
    CC[fl] = 16.0
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R_, CC))


# -------------------------------------------------------------------------
# 28. Enceladus Tiger Stripes
# -------------------------------------------------------------------------
def tiger_stripes(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 28 Enceladus Tiger Stripes: warped parallel stripe family, per-stripe per-segment sideways offsets (en-echelon), teal-blue fissures with bright shoulders, frost spray speckle; pearly flaked ice, candy fissures
    n = N
    r = H.rng(seed)
    X, Y = H.xy(n)
    th = 0.42
    c, s_ = float(np.cos(th)), float(np.sin(th))
    wp = 120.0 * H.fbm(n, seed + 2, cells=(2, 3, 5, 9), gain=0.6)
    u = X * c + Y * s_ + wp
    v = -X * s_ + Y * c
    P = 138.0
    si = np.floor(u / P).astype(np.int32)
    h1 = H.hash01((si + 4096).astype(np.uint32), seed + 3)
    seg = np.floor((v + 700.0 * h1) / (210.0 + 160.0 * h1)).astype(np.int32)
    h2 = H.hash01(((si + 4096) * 977 + seg + 100000).astype(np.uint32), seed + 4)
    uu = u + (h2 - 0.5) * 44.0
    f = np.mod(uu, P)
    d = np.minimum(f, P - f)
    w = 3.4 + 5.6 * h2
    line = np.exp(-(d / w) ** 2)
    core = np.exp(-(d / (w * 0.45)) ** 2)
    shoulder = np.exp(-((d - w * 1.7) / (w * 0.75)) ** 2)
    t = np.clip(0.45 + 0.14 * H.fbm(n, seed + 5, cells=(3, 6, 12, 24)) + 0.12 * H.fbm(n, seed + 6, cells=(128, 256, 512), gain=0.9), 0, 1)
    ice = H.ramp(t, [(0.0, '#8ea8c8'), (0.5, '#cfdff0'), (1.0, '#f0f6fc')])
    tealc = H.ramp(core, [(0.0, '#2cc0b0'), (0.5, '#128aa0'), (1.0, '#06384a')])
    rgb = ice * (1 - 0.92 * line)[..., None] + (0.92 * line)[..., None] * tealc
    rgb += (shoulder * (1 - line) * 0.30)[..., None] * np.array([0.9, 0.97, 1.0], F32)
    dens = np.clip(H.blur(line, 26.0) * 1.2, 0, 1)
    K = 220000
    xs = r.integers(0, n, K)
    ys = r.integers(0, n, K)
    keep = r.random(K) < dens[ys, xs] * 0.45
    spr = np.zeros((n, n), F32)
    H.points(spr, xs[keep], ys[keep], 0.6 + 0.4 * r.random(int(keep.sum())))
    rgb = rgb + spr[..., None] * np.array([0.55, 0.66, 0.74], F32) * (1 - 0.5 * line)[..., None]
    fl = H.flake_mask(n, 0.06, seed + 11) & (line < 0.3)
    M = H.lerp(130.0, 205.0, line)
    R = H.lerp(80.0, 16.0, line)
    CC = H.lerp(16.0, 16.0, line)
    M[fl] = 255.0
    R[fl] = 8.0
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 29. Venus Tessera
# -------------------------------------------------------------------------
def venus_tessera(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 29 Venus Tessera: two roughly orthogonal sets of wavy ridges (warped periodic phases) cut the plain into crumpled BLOCKY tiles, each tile its own radar brightness and tilt, at two nested scales; radar grey-gold (wave-2 review: fur/wood -> blocky fold tiles)
    n = N
    X, Y = H.xy(n)

    def phase(ang, lam, sd, wamp):
        c, s = float(np.cos(ang)), float(np.sin(ang))
        w = wamp * H.fbm(n, sd, cells=(5, 10, 20, 40), gain=0.62)
        return ((X * c + Y * s) / lam + w).astype(F32)

    def tiles(angA, lamA, lamB, sd, wamp, ew):
        pa = phase(angA, lamA, sd, wamp)
        pb = phase(angA + np.pi / 2 + 0.16, lamB, sd + 50, wamp)
        ia = np.floor(pa)
        ib = np.floor(pb)
        fa = pa - ia
        fb = pb - ib
        key = (ia.astype(np.int32) * 7919 + ib.astype(np.int32) * 104729)
        h1 = H.hash01(key, sd + 1)
        gxt = H.hash01(key, sd + 2) * 2 - 1
        gyt = H.hash01(key, sd + 3) * 2 - 1
        tilt = gxt * (fa - 0.5) + gyt * (fb - 0.5)
        ea = np.exp(-(np.minimum(fa, 1 - fa) / ew) ** 2)
        eb = np.exp(-(np.minimum(fb, 1 - fb) / ew) ** 2)
        crest = np.exp(-((fa - 0.08) / ew) ** 2) + np.exp(-((fb - 0.08) / ew) ** 2)
        groove = np.exp(-((fa - 0.92) / ew) ** 2) + np.exp(-((fb - 0.92) / ew) ** 2)
        return h1, tilt, crest, groove

    h1, t1, c1, g1 = tiles(0.30, 104.0, 80.0, seed + 10, 0.36, 0.075)
    h2, t2, c2, g2 = tiles(0.34, 36.0, 28.0, seed + 30, 0.30, 0.10)
    tone = np.clip(-0.02 + 0.42 * h1 + 0.14 * h2 + 0.24 * t1 + 0.12 * t2 + 0.55 * c1 + 0.12 * c2 - 0.34 * g1 - 0.08 * g2
                   + 0.10 * H.fbm(n, seed + 3, cells=(128, 256, 512), gain=0.9), 0, 1)
    rgb = H.ramp(tone, [(0.0, '#1a1918'), (0.35, '#5a5852'), (0.65, '#a69a72'), (0.88, '#d8c488'), (1.0, '#fff0c0')])
    st = _snoise(900, 44, seed + 5, ang=0.35)
    M = H.lerp(30.0, 190.0, tone)
    R = H.lerp(212.0, 56.0, tone) + 16.0 * st
    CC = H.lerp(140.0, 30.0, tone)
    return H.finish_out(rgb, H.spec_pack(M, R, CC))


# -------------------------------------------------------------------------
# 30. Comet Nucleus Crust
# -------------------------------------------------------------------------
def comet_crust(seed):
    # [S19 2026-10-12 owner: Fractured Cosmos rebuild] 30 Comet Nucleus Crust: near-black rough crust with quantised TERRACES whose lit scarp faces carry broken bright ice, dark pits with ice only on the lit rim, faint dust-jet streaks (wave-2 review: confetti -> ice only on scarp edges and pit rims)
    n = N
    r = H.rng(seed)
    gfine = 0.5 * H.fbm(n, seed + 1, cells=(5, 10, 20, 40, 80), gain=0.75) + 0.55 * H.ridged(H.fbm(n, seed + 2, cells=(24, 48, 96, 192, 384), gain=0.8))
    # [S19 coordinator fix 2026-10-12] ice squiggles read as worms -> terraces are straight-edged Voronoi PLATES (76 px) at 4 levels, so scarps are straight, broken segments
    cp_ = H.jitter_pts(n, 112.0, seed + 5, jit=0.95, margin=60)
    _dd, lab_c, cxs, cys = H.voronoi(n, cp_)
    zlow = H.fbm(256, seed + 6, cells=(3, 5, 9, 18), gain=0.62)
    zc = zlow[np.clip(cys // 8, 0, 255), np.clip(cxs // 8, 0, 255)] + 0.55 * H.rng(seed + 7).standard_normal(len(cxs)).astype(F32)
    lo_, hi_ = np.percentile(zc, (2, 98))
    lvl = np.floor(np.clip((zc - lo_) / (hi_ - lo_ + 1e-6), 0, 0.999) * 4.0).astype(np.int16)
    hq = lvl[(lab_c - 1).astype(np.int64)]
    hs = H.blur(hq.astype(F32) * 5.0 + 5.0 * gfine, 1.4)
    gy, gx = np.gradient(hs)
    shade = np.clip(0.5 + 1.0 * 0.7071 * (gx + gy), 0, 1)
    ct = np.clip(0.50 * shade + 0.06 * hq.astype(F32) + 0.24 * np.clip(gfine * 0.8 + 0.4, 0, 1) + 0.20 * H.ridged(H.fbm(n, seed + 30, cells=(64, 128, 256), gain=0.95)), 0, 1)
    crust = H.ramp(ct, [(0.0, '#0d0b0a'), (0.55, '#262019'), (1.0, '#5c5046')])
    # lit scarps: boundary pixels on the LOW side of a step that rises toward the right or down (faces the light)
    up = (np.roll(hq, -1, axis=1) > hq) | (np.roll(hq, -1, axis=0) > hq)
    sc_ = cv2.dilate(up.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(F32)
    rag = H.sstep(0.18, 0.55, 0.45 + 0.9 * H.fbm(n, seed + 8, cells=(20, 40, 80, 160), gain=0.8))
    dash = H.sstep(-0.10, 0.40, H.fbm(n, seed + 9, cells=(110, 220, 440), gain=0.9))
    scarp = H.blur(sc_ * rag * dash, 0.8)
    # pits
    pa = H.jitter_pts(n, 130.0, seed + 3, jit=0.95, margin=50)
    pa = pa[r.random(len(pa)) < 0.55]
    pp = pa
    K = len(pp)
    rr = np.exp(r.uniform(np.log(12.0), np.log(40.0), K))
    pits = np.zeros((n, n), np.uint8)
    sc = 16
    for i in range(K):
        cv2.circle(pits, (int(pp[i, 0] * sc), int(pp[i, 1] * sc)), int(rr[i] * sc), 255, -1, cv2.LINE_AA, 4)
    pf = H.warp(pits.astype(F32) / 255.0, (7.0 * H.fbm(n, seed + 21, cells=(40, 80, 160))).astype(F32), (7.0 * H.fbm(n, seed + 22, cells=(40, 80, 160))).astype(F32))
    pf = np.clip(pf, 0, 1)
    ps = H.blur(pf, 1.5)
    qy, qx = np.gradient(ps)
    pe = np.clip(np.hypot(qx, qy) * 4.5, 0, 1)
    plit = np.clip((qx + qy) * 6.0, 0, 1)
    prim = np.clip((0.30 * pe + plit) * (0.55 + 0.45 * rag), 0, 1)
    # faint dust-jet streaks from a few pits
    jm = np.where(r.random(K) < 0.30)[0]
    polys, vals = [], []
    for i in jm:
        a0 = float(r.uniform(0, 2 * np.pi))
        for _ in range(int(r.integers(8, 22))):
            a_ = a0 + float(r.normal(0, 0.28))
            L = float(r.uniform(120, 480))
            polys.append(np.array([[pp[i, 0], pp[i, 1]], [pp[i, 0] + np.cos(a_) * L * 0.5, pp[i, 1] + np.sin(a_) * L * 0.5 + r.normal(0, 6)],
                                   [pp[i, 0] + np.cos(a_) * L, pp[i, 1] + np.sin(a_) * L + r.normal(0, 12)]]))
            vals.append(int(45 + 70 * r.random()))
    jet = H.lines_u8(n, polys, np.array(vals, np.int32), thick=1) if polys else np.zeros((n, n), np.uint8)
    jt = H.blur(jet.astype(F32) / 255.0, 1.2)
    ice = np.array([0.86, 0.93, 1.0], F32)
    rgb = crust * (1 - 0.45 * pf)[..., None]
    rgb += (jt * 1.1)[..., None] * np.array([0.40, 0.34, 0.28], F32)
    ice_a = np.clip(0.90 * scarp + 0.95 * prim, 0, 1)
    rgb = rgb * (1 - ice_a)[..., None] + ice_a[..., None] * ice * (0.70 + 0.30 * H.fbm(n, seed + 4, cells=(64, 128, 256)))[..., None]
    ia = np.clip(ice_a * 1.1, 0, 1)
    lt = np.clip(H.lum(np.clip(rgb, 0, 1)) / 0.45, 0, 1)
    M = H.lerp(0.0, 40.0, lt)
    M = np.maximum(M, 255.0 * ia)
    R = H.lerp(236.0, 110.0, lt)
    R = R * (1 - ia) + 6.0 * ia
    CC = H.lerp(255.0, 120.0, lt)
    CC = CC * (1 - ia) + 16.0 * ia
    return H.finish_out(np.clip(rgb, 0, 1), H.spec_pack(np.clip(M, 0, 255), R, CC))


FINISHES = [
    ("cz_jovian_belts", "Jovian Storm Belts",
     "Wandering cream, tan and rust cloud bands with curling shear waves and small white and red storm ovals.", jovian_belts),
    ("cz_ringlet_grooves", "Ringlet Grooves",
     "Thousands of fine champagne and ice-grey planetary ringlets like record grooves, with black gaps and spoke shadows.", ringlet_grooves),
    ("cz_io_paterae", "Io Lava Paterae",
     "Sulfur plains of yellow, orange and white pocked with black lava calderas ringed in red.", io_paterae),
    ("cz_europa_lineae", "Europa Lineae",
     "Pale blue cracked ice crossed by long curving rust-brown ridge lines and scalloped fracture arcs.", europa_lineae),
    ("cz_titan_channels", "Titan Methane Rivers",
     "Black branching drainage channels cutting orange hazy land.", titan_channels),
    ("cz_dust_devil_tracks", "Martian Dust Devil Tracks",
     "Dark looping scribble tracks crossing rust-tan Martian dust.", dust_devil_tracks),
    ("cz_ray_craters", "Lunar Ray Craters",
     "Small craters wearing bright radial ejecta rays over grey regolith.", ray_craters),
    ("cz_tiger_stripes", "Enceladus Tiger Stripes",
     "Bright pearly ice cut by parallel offset teal fissures and frost spray.", tiger_stripes),
    ("cz_venus_tessera", "Venus Tessera",
     "Dark basalt crumpled by two crossing fold sets, every ridge crest lit radar-gold like crinkled foil.", venus_tessera),
    ("cz_comet_crust", "Comet Nucleus Crust",
     "Coal-brown dusty crust with small bright ice flecks, curling gas-vent wisps and faint fracture plates.", comet_crust),
]
