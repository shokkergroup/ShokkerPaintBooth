# -*- coding: utf-8 -*-
"""FRACTURED COSMOS R2 - LOW-LEVEL helpers only.

[S19 2026-10-12 owner: Fractured Cosmos rebuild] Every finish's STRUCTURE lives in
its own function in a chapter module. This file holds only plumbing: noise,
voronoi labels, curl field, LIC, FFT filtering, polyline raster, stamp splatting,
palette ramps and spec packing. R1 failed because 13 shared *primitives* were
stacked through one palette; nothing here knows what a "finish" is.

Canvas is always N = 2048 (the real car sheet). Everything is float32.
"""
from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None
try:
    import scipy.fft as _sfft
except Exception:                                            # pragma: no cover
    _sfft = None

N = 2048
F32 = np.float32


# --------------------------------------------------------------------- basics
def rng(seed):
    return np.random.default_rng(int(seed) & 0x7FFFFFFF)


_XY = {}


def xy(n=N):
    """Read-only (X, Y) float32 pixel-coordinate grids."""
    if n not in _XY:
        a = np.arange(n, dtype=F32)
        _XY[n] = (np.broadcast_to(a[None, :], (n, n)), np.broadcast_to(a[:, None], (n, n)))
    return _XY[n]


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(F32)


def lerp(a, b, t):
    return a + (b - a) * t


def lum(rgb):
    return (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]).astype(F32)


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], F32)


def hash01(a, salt=0):
    """Vectorised integer hash -> [0,1). `a` int array."""
    x = a.astype(np.uint32) + np.uint32(salt & 0xFFFFFFFF)
    x = x * np.uint32(2654435761)
    x ^= x >> np.uint32(15)
    x = x * np.uint32(2246822519)
    x ^= x >> np.uint32(13)
    x = x * np.uint32(3266489917)
    x ^= x >> np.uint32(16)
    return (x >> np.uint32(8)).astype(F32) / F32(1 << 24)


# ---------------------------------------------------------------------- noise
def noise(n, cells, seed):
    """Smooth gaussian-ish value noise, ~unit std, feature size n/cells px."""
    c = int(max(2, min(cells, n)))
    g = rng(seed).standard_normal((c, c)).astype(F32)
    out = cv2.resize(g, (n, n), interpolation=cv2.INTER_CUBIC if c < n else cv2.INTER_NEAREST)
    return out


def fbm(n, seed, cells=(4, 8, 16, 32, 64, 128), gain=0.6, w=None):
    acc = None
    norm = 0.0
    for i, c in enumerate(cells):
        wi = float(w[i]) if w is not None else gain ** i
        t = noise(n, c, seed * 131 + i * 17 + 5)
        t *= F32(wi)
        if acc is None:
            acc = t
        else:
            acc += t
        norm += wi * wi
    acc /= F32(np.sqrt(norm))
    return acc


def ridged(z):
    """1 - |z| : crest lines along the zero set of z (z ~ unit std)."""
    return (1.0 - np.abs(z)).astype(F32)


def zero_set_line(z, width):
    """Distance-normalised line mask along z == 0: ~constant `width` px at any slope."""
    gy, gx = np.gradient(z)
    g = np.hypot(gx, gy) + F32(1e-4)
    d = np.abs(z) / g
    return np.exp(-(d / F32(width)) ** 2).astype(F32)


def warp(img, dx, dy, border=None):
    n = img.shape[0]
    X, Y = xy(n)
    return cv2.remap(img, (X + dx).astype(F32), (Y + dy).astype(F32), cv2.INTER_LINEAR,
                     borderMode=border if border is not None else cv2.BORDER_REFLECT)


def blur(img, sigma):
    """Gaussian blur that stays fast for big sigma (down/up trick)."""
    if sigma < 0.3:
        return img
    if sigma <= 5.0:
        return cv2.GaussianBlur(img, (0, 0), float(sigma))
    f = int(max(2, sigma // 2.5))
    h, w = img.shape[:2]
    sm = cv2.resize(img, (max(2, w // f), max(2, h // f)), interpolation=cv2.INTER_AREA)
    sm = cv2.GaussianBlur(sm, (0, 0), float(sigma) / f)
    return cv2.resize(sm, (w, h), interpolation=cv2.INTER_CUBIC)


def glow(layer, sigmas=(2.0, 6.0, 16.0), weights=(1.0, 0.6, 0.35)):
    out = None
    for s, w in zip(sigmas, weights):
        b = blur(layer, s) * F32(w)
        out = b if out is None else out + b
    return out


def downs(img, n):
    return cv2.resize(img, (n, n), interpolation=cv2.INTER_AREA)


def ups(img, n, cubic=True):
    return cv2.resize(img, (n, n), interpolation=cv2.INTER_CUBIC if cubic else cv2.INTER_LINEAR)


# ----------------------------------------------------------------- voronoi
def jitter_pts(n, spacing, seed, jit=0.9, margin=0):
    g = int(np.ceil((n + 2 * margin) / spacing))
    r = rng(seed)
    gx, gy = np.meshgrid(np.arange(g, dtype=F32), np.arange(g, dtype=F32))
    px = (gx + 0.5 + (r.random((g, g), dtype=F32) - 0.5) * jit) * spacing - margin
    py = (gy + 0.5 + (r.random((g, g), dtype=F32) - 0.5) * jit) * spacing - margin
    return np.stack([px.ravel(), py.ravel()], 1)


def voronoi(n, pts):
    """Return (dist_to_seed, label (1-based, raster order of seeds), sx, sy)
    for seeds pts (K,2). Seeds outside the canvas are dropped. label-1 indexes sx/sy."""
    ix = np.round(pts[:, 0]).astype(np.int64)
    iy = np.round(pts[:, 1]).astype(np.int64)
    ok = (ix >= 0) & (ix < n) & (iy >= 0) & (iy < n)
    ix, iy = ix[ok], iy[ok]
    _, ui = np.unique(iy * n + ix, return_index=True)
    ix, iy = ix[ui], iy[ui]
    order = np.lexsort((ix, iy))
    ix, iy = ix[order], iy[order]
    seed = np.full((n, n), 255, np.uint8)
    seed[iy, ix] = 0
    d, lab = cv2.distanceTransformWithLabels(seed, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    return d.astype(F32), lab, ix, iy


def label_edges(lab):
    e = np.zeros(lab.shape, np.uint8)
    e[:, :-1] |= (lab[:, :-1] != lab[:, 1:])
    e[:-1, :] |= (lab[:-1, :] != lab[1:, :])
    return e


def edge_dist(lab):
    """px distance from every pixel to the nearest cell border."""
    e = label_edges(lab)
    return cv2.distanceTransform(((1 - e) * 255).astype(np.uint8), cv2.DIST_L2, 5).astype(F32)


# ------------------------------------------------------------- vector fields
def curl_field(m, seed, cells=(3, 6, 12), gain=0.6):
    """Divergence-free unit-ish velocity (u, v) at m x m."""
    psi = fbm(m, seed, cells=cells, gain=gain)
    gy, gx = np.gradient(psi)
    u, v = gy, -gx
    s = np.sqrt(u * u + v * v) + F32(1e-6)
    return (u / s).astype(F32), (v / s).astype(F32)


def sample(field, px, py):
    """Bilinear sample of a 2-D field at float coords (arrays)."""
    m = field.shape[0]
    x = np.clip(px, 0, m - 1.001)
    y = np.clip(py, 0, m - 1.001)
    x0 = x.astype(np.int64)
    y0 = y.astype(np.int64)
    fx = (x - x0).astype(F32)
    fy = (y - y0).astype(F32)
    a = field[y0, x0]
    b = field[y0, x0 + 1]
    c = field[y0 + 1, x0]
    d = field[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def trace(u, v, p0, steps, h, n=N):
    """Trace streamlines through (u,v) (res m) starting at canvas px p0 (K,2).
    Returns (K, steps+1, 2) in canvas px. RK2."""
    m = u.shape[0]
    k = n / float(m)
    p = np.asarray(p0, F32).copy()
    out = np.empty((p.shape[0], steps + 1, 2), F32)
    out[:, 0] = p
    for i in range(steps):
        a = sample(u, p[:, 0] / k, p[:, 1] / k)
        b = sample(v, p[:, 0] / k, p[:, 1] / k)
        mx = p[:, 0] + 0.5 * h * a
        my = p[:, 1] + 0.5 * h * b
        a2 = sample(u, mx / k, my / k)
        b2 = sample(v, mx / k, my / k)
        p[:, 0] += h * a2
        p[:, 1] += h * b2
        out[:, i + 1] = p
    return out


def lic(tex, u, v, length=14, h=1.0):
    """Line-integral convolution of `tex` along (u,v); all at the same res."""
    m = tex.shape[0]
    X, Y = xy(m)
    acc = tex.copy()
    for sgn in (1.0, -1.0):
        px = np.array(X, F32)
        py = np.array(Y, F32)
        for _ in range(length):
            su = cv2.remap(u, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            sv = cv2.remap(v, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            px += F32(sgn * h) * su
            py += F32(sgn * h) * sv
            acc += cv2.remap(tex, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    acc /= F32(2 * length + 1)
    return acc


# ------------------------------------------------------------------- FFT
def rfft2(x):
    return _sfft.rfft2(x, workers=-1) if _sfft is not None else np.fft.rfft2(x)


def irfft2(f, n):
    return _sfft.irfft2(f, s=(n, n), workers=-1) if _sfft is not None else np.fft.irfft2(f, s=(n, n))


def fft_noise(n, seed, radial_gain):
    """Gaussian random field with power spectrum shaped by radial_gain(k) where
    k = cycles per canvas (0..n/2). Standardised."""
    w = rng(seed).standard_normal((n, n)).astype(F32)
    f = rfft2(w)
    ky = np.fft.fftfreq(n, 1.0 / n).astype(F32)[:, None]
    kx = np.fft.rfftfreq(n, 1.0 / n).astype(F32)[None, :]
    k = np.sqrt(ky * ky + kx * kx)
    f *= radial_gain(k).astype(F32)
    out = irfft2(f, n).astype(F32)
    out -= out.mean()
    out /= (out.std() + F32(1e-6))
    return out


def tile_to(tile, n):
    r = int(np.ceil(n / tile.shape[0]))
    return np.tile(tile, (r, r) + (1,) * (tile.ndim - 2))[:n, :n]


# ------------------------------------------------------------- raster/stamps
def lines_u8(n, polys, vals, thick=1, canvas=None, shift=4):
    """Antialiased polylines into a uint8 canvas (later lines overwrite)."""
    cvs = canvas if canvas is not None else np.zeros((n, n), np.uint8)
    sc = float(1 << shift)
    # [S19 fix 2026-10-12] draw DIMMEST first so a brighter line is never overwritten by a dimmer one
    # (cv2.polylines overwrites; random order made blocky dark patches inside bright ribbons).
    order = np.argsort(np.asarray(vals, np.float64), kind="stable")
    for i in order:
        pts = np.round(np.asarray(polys[i], np.float64) * sc).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(cvs, [pts], False, int(vals[i]), thick, cv2.LINE_AA, shift)
    return cvs


def circles_u8(n, cx, cy, r, vals, thick=1, canvas=None, shift=4):
    cvs = canvas if canvas is not None else np.zeros((n, n), np.uint8)
    sc = float(1 << shift)
    for x, y, rr, v in zip(cx, cy, r, vals):
        cv2.circle(cvs, (int(round(x * sc)), int(round(y * sc))), int(round(rr * sc)),
                   int(v), thick, cv2.LINE_AA, shift)
    return cvs


def rotset(master, k=24, span=np.pi):
    S = master.shape[0]
    c = (S - 1) / 2.0
    out = []
    for i in range(k):
        M = cv2.getRotationMatrix2D((c, c), float(np.degrees(span * i / k)), 1.0)
        out.append(cv2.warpAffine(master, M, (S, S), flags=cv2.INTER_LINEAR, borderValue=0))
    return out


def splat(cvs, tiles, ti, xs, ys, amp=None, col=None, flip=None, mode="add"):
    """Stamp tiles[ti[k]] centred at (xs[k], ys[k]). cvs (H,W) or (H,W,3) with `col` (K,3)."""
    H, W = cvs.shape[:2]
    xs = np.asarray(xs).astype(np.int64)
    ys = np.asarray(ys).astype(np.int64)
    for k in range(len(xs)):
        t = tiles[int(ti[k])]
        if flip is not None:
            fl = int(flip[k])
            if fl & 1:
                t = t[:, ::-1]
            if fl & 2:
                t = t[::-1]
        h, w = t.shape[:2]
        x0 = int(xs[k]) - (w >> 1)
        y0 = int(ys[k]) - (h >> 1)
        sx0 = 0 if x0 >= 0 else -x0
        sy0 = 0 if y0 >= 0 else -y0
        ex = min(w, W - x0)
        ey = min(h, H - y0)
        if ex <= sx0 or ey <= sy0:
            continue
        dst = cvs[y0 + sy0:y0 + ey, x0 + sx0:x0 + ex]
        src = t[sy0:ey, sx0:ex]
        if amp is not None:
            src = src * F32(amp[k])
        if col is not None:
            src = src[..., None] * col[k]
        if mode == "add":
            dst += src
        else:
            np.maximum(dst, src, out=dst)
    return cvs


def points(cvs, xs, ys, vals, mode="max"):
    xs = np.asarray(xs).astype(np.int64)
    ys = np.asarray(ys).astype(np.int64)
    ok = (xs >= 0) & (xs < cvs.shape[1]) & (ys >= 0) & (ys < cvs.shape[0])
    xs, ys = xs[ok], ys[ok]
    vals = np.asarray(vals, F32)
    vals = vals[ok] if vals.ndim else vals
    if mode == "max":
        cvs[ys, xs] = np.maximum(cvs[ys, xs], vals)
    else:
        cvs[ys, xs] += vals
    return cvs


def flake_mask(n, density, seed):
    return rng(seed).random((n, n), dtype=F32) < density


# ----------------------------------------------------------------- palette
def lut(stops, size=1024):
    pos = np.array([s[0] for s in stops], np.float64)
    cols = np.array([hexrgb(s[1]) if isinstance(s[1], str) else np.asarray(s[1], F32)
                     for s in stops], np.float64)
    t = np.linspace(0, 1, size)
    return np.stack([np.interp(t, pos, cols[:, c]) for c in range(3)], 1).astype(F32)


def ramp(t, stops_or_lut, size=1024):
    L = stops_or_lut if isinstance(stops_or_lut, np.ndarray) else lut(stops_or_lut, size)
    idx = np.clip(t * F32(L.shape[0] - 1) + F32(0.5), 0, L.shape[0] - 1).astype(np.int32)
    return L[idx]


def tonemap(x, gain=1.0):
    return (1.0 - np.exp(-np.maximum(x, 0) * F32(gain))).astype(F32)


def over(base, col, a):
    """base (H,W,3) += alpha-over of colour col(3,) with alpha a (H,W) - in place."""
    base *= (1.0 - a)[..., None]
    base += a[..., None] * np.asarray(col, F32)
    return base


# -------------------------------------------------------------------- spec
def spec_pack(M, R, CC, n=N):
    out = np.empty((n, n, 3), F32)
    out[..., 0] = M
    out[..., 1] = R
    out[..., 2] = CC
    return out


def iron_safe_u8(s):
    """Spec Guide legality: roughness floor 15 unless mirror tier; CC never 1..15."""
    s = np.asarray(s, F32)
    mirror = s[..., 0] >= 240.0
    s[..., 1] = np.where(mirror, s[..., 1], np.clip(s[..., 1], 15, 255))
    cc = s[..., 2]
    s[..., 2] = np.where((cc > 0) & (cc < 16), 16.0, cc)
    return np.clip(s, 0, 255).astype(np.uint8)


def finish_out(rgb, spec):
    return np.clip(rgb, 0, 1).astype(F32), iron_safe_u8(spec)


def structure_spec(rgb, seed, tiers, ground_m=(40.0, 100.0), ground_r=(112.0, 150.0), ground_cc=46.0,
                   halo=None, flake=1.0, brush=0.0, grain=0.0):
    """[S19 2026-10-12 coordinator polish A: spec richness] A spec whose STRUCTURE is the paint's structure.

    The ground is a matte-ish, rough metal carrying a 1 px flake (and an optional brushed streak,
    `brush` = streak length in px). Every tier (lo, hi, M, R, CC) pulls the pixels whose PAINT luma is
    between lo and hi toward that metal/rough state (lo > hi inverts: the DARKER the paint, the more of
    the state). `halo` = (sigma, gain, M, R, CC) puts a satin skirt around the first tier (a bloom
    that keeps thin lines visible at thumbnail size). Returns float32 M, R, CC; the paint is not touched."""
    n = rgb.shape[0]
    r = rng(seed)
    lm = lum(rgb)
    g1 = r.standard_normal((n, n)).astype(F32)
    g2 = r.standard_normal((n, n)).astype(F32)
    if brush > 0:
        g2 = cv2.GaussianBlur(g2, (0, 0), sigmaX=float(brush), sigmaY=0.6).astype(F32)
        g2 /= max(float(g2.std()), 1e-6)
    m0, m1 = ground_m
    r0, r1 = ground_r
    M = (0.5 * (m0 + m1) + 0.30 * (m1 - m0) * flake * g1).astype(F32)
    R = (0.5 * (r0 + r1) + 0.30 * (r1 - r0) * flake * g2).astype(F32)
    CC = (ground_cc + 5.0 * flake * g1).astype(F32)
    if grain > 0:      # mid-scale (8-32 px) grain on the ground: white noise blurred to sigma ~2 px lands in the SCALE band
        g3 = cv2.GaussianBlur(r.standard_normal((n, n)).astype(F32), (0, 0), 2.1).astype(F32)
        g4 = cv2.GaussianBlur(r.standard_normal((n, n)).astype(F32), (0, 0), 2.1).astype(F32)
        g3 /= max(float(g3.std()), 1e-6)
        g4 /= max(float(g4.std()), 1e-6)
        M = M + 0.45 * (m1 - m0) * grain * g3
        R = R + 0.45 * (r1 - r0) * grain * g4
    if halo is not None and tiers:
        sig, gain, hm, hr, hc = halo
        f0 = sstep(tiers[0][0], tiers[0][1], lm)
        hl = np.clip(blur(f0, sig) * gain, 0, 1).astype(F32)
        M = M + (hm - M) * hl
        R = R + (hr - R) * hl
        CC = CC + (hc - CC) * hl
    for lo, hi, tm, tr, tc in tiers:
        t = sstep(lo, hi, lm)
        M = M + (tm - M) * t
        R = R + (tr - R) * t
        CC = CC + (tc - CC) * t
    return M.astype(F32), R.astype(F32), CC.astype(F32)
