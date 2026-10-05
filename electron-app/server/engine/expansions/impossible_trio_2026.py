# -*- coding: utf-8 -*-
"""IMPOSSIBLE FINISHES — three physics-authored materials (owner ask 2026-09-02).

Owner: "3 more that totally push the boundaries of what's actually possible with your
coding and advanced levels of math. Millions of colors with the most intricate designs
you've ever made in the base paint AND spec paint."

Each finish is a FIELD (8-32 px features, whole canvas, no poster), its colour comes
from a continuous physical quantity (so every pixel is its own colour), and its
M/R/Cc population is attached to the same geometry so track lighting animates it.

  impossible_penrose_reactor  — an aperiodic five-fold quasicrystal (de Bruijn pentagrid).
        Five plane-wave lattices cut the canvas into polygons that NEVER repeat; each
        polygon belongs to one of five hue families by its pentagrid index sum, its exact
        hue slides with the five fractional phases, a golden-ratio inflated micro-lattice
        facets its interior, and a slow selector chooses which family runs chrome-hot
        per region so the lattice travels under a moving light.
  impossible_nacre_terrace    — thin-film interference on stepped aragonite platelets.
        Jittered Voronoi platelets carry a film thickness set by screw-dislocation
        growth terraces (Archimedean step spirals) plus a per-platelet tilt; the colour
        is the two-beam interference integral over twelve wavelengths mapped through
        cone-like response curves — true Newton colours, continuous within every
        platelet — and the terrace order sets the metal / roughness / coat tier.
  impossible_caustic_loom     — real refractive caustics through a woven micro-lens.
        A twill of crossed lens ribbons is a height field; parallel light is refracted
        (thin-lens deflection = D(n-1)∇h) and photon-binned onto the paint plane for
        five wavelengths with glass dispersion, so the folds of the light map are
        chromatic caustic filaments. Filaments are glass-gloss, ribbon crests chrome,
        troughs satin: the spec IS the optics that made the paint.
"""
from collections import OrderedDict
from threading import RLock

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

_CACHE, _LOCK = OrderedDict(), RLock()
WORK = 1024
PHI = (1 + 5 ** 0.5) / 2


def _work(shape):
    h, w = int(shape[0]), int(shape[1])
    q = min(1.0, WORK / float(max(h, w)))
    hh, ww = max(32, int(round(h * q))), max(32, int(round(w * q)))
    y, x = np.mgrid[0:hh, 0:ww].astype(np.float32)
    # X, Y on the 2048 REFERENCE canvas whatever the render size (the live preview renders at 1024)
    return (h, w), (hh, ww), x * (2048.0 / ww), y * (2048.0 / hh)


def _up(paint, M, R, C, native, work):
    if native != work and cv2 is not None:
        h, w = native
        paint = cv2.resize(paint, (w, h), interpolation=cv2.INTER_LINEAR)
        M, R, C = (cv2.resize(z, (w, h), interpolation=cv2.INTER_NEAREST) for z in (M, R, C))
    spec = np.stack((np.clip(M, 0, 255), np.clip(R, 0, 255), np.clip(C, 0, 255)), 2).astype(np.uint8)
    return np.clip(paint, 0, 1).astype(np.float32), spec


def _h01(*ints):
    """Deterministic per-cell scalar in [0,1) from integer arrays."""
    acc = np.zeros_like(ints[0], dtype=np.int64)
    for k, a in enumerate(ints):
        acc = acc * 1000003 + a.astype(np.int64) * (7919 + 104729 * k)
    acc = (acc ^ (acc >> 13)) * 1274126177
    return ((acc ^ (acc >> 16)) & 0xFFFFFF).astype(np.float32) / float(0x1000000)


def _hsv(h, s, v):
    h6 = (np.mod(h, 1.0) * 6.0)
    i = np.floor(h6)
    f = h6 - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    i = i.astype(np.int32) % 6
    r = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [v, q, p, p, t, v])
    g = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [t, v, v, q, p, p])
    b = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [p, p, t, v, v, q])
    return np.stack((r, g, b), 2).astype(np.float32)


# ───────────────────────────── 1. PENROSE REACTOR ─────────────────────────────
def _penrose_reactor(shape, seed):
    native, work, X, Y = _work(shape)
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    S = 24.0                                   # pentagrid spacing (native px): cells 8-26 px
    S2 = S / (PHI * PHI)                       # inflated micro-lattice ~9 px
    ang0 = rng.uniform(0, 2 * np.pi)
    n_idx, fracs, edge, micro = [], [], np.full(X.shape, 9.0, np.float32), np.zeros(X.shape, np.float32)
    for j in range(5):
        a = ang0 + 2 * np.pi * j / 5
        proj = X * np.cos(a) + Y * np.sin(a)
        t = proj / S + rng.uniform(0, 1)
        n = np.floor(t)
        f = t - n
        n_idx.append(n.astype(np.int64))
        fracs.append(f)
        edge = np.minimum(edge, np.minimum(f, 1 - f) * S)
        t2 = proj / S2 + rng.uniform(0, 1)
        micro += np.cos(2 * np.pi * t2)
    nsum = sum(n_idx)
    # (the plain index sum is de Bruijn's vertex index and takes only 1..4 values: weighted sum instead)
    family = np.mod(n_idx[0] + 2 * n_idx[1] + 3 * n_idx[2] + 4 * n_idx[3] + 5 * n_idx[4], 5).astype(np.int32)
    klass = np.mod(nsum * 3 + n_idx[1] - n_idx[3], 9).astype(np.int32)
    cell = _h01(*n_idx)
    meanf = sum(fracs) / 5.0
    # slow selector: which family runs hot in this region (coherent 250-500 px travel)
    sel = 0.5 + 0.28 * np.sin(X / 101.0 + 0.9 * np.sin(Y / 67.0)) + 0.22 * np.cos(Y / 89.0 - 0.6 * np.sin(X / 53.0))
    hot_k = np.clip(np.floor(sel * 9), 0, 8).astype(np.int32)
    hot = klass == hot_k
    warm = (klass == np.mod(hot_k + 3, 9)) | (klass == np.mod(hot_k + 6, 9))
    black = np.mod(nsum + n_idx[2], 3) == 0                                  # a third of the quiet cells are black
    # colour: five families on a hue wheel, slid by the fractional phases and the cell hash
    fam_hue = np.array([0.50, 0.86, 0.10, 0.27, 0.71], np.float32)[family]   # cyan, magenta, amber, lime, violet
    hue = fam_hue + 0.06 * (meanf - 0.5) + 0.05 * (cell - 0.5)
    micro_n = micro / 5.0                                                     # -1..1 five-fold rosettes
    facet = 0.5 + 0.5 * np.tanh(3.0 * micro_n)
    val = np.where(hot, 0.80 + 0.20 * facet, np.where(warm, 0.42 + 0.22 * facet, np.where(black, 0.03 + 0.03 * facet, 0.12 + 0.10 * facet)))
    sat = np.where(hot, 0.55 - 0.25 * facet, 0.96 - 0.15 * facet)
    col = _hsv(hue, sat, val)
    body = np.array((0.020, 0.024, 0.040), np.float32)
    paint = body[None, None, :] * (1 - val[..., None]) + col
    line = np.clip(1.0 - edge / 1.3, 0, 1)                                   # 1-2 px lattice lines
    glow = np.clip(1.0 - edge / 3.5, 0, 1) * hot                              # hot cells bleed light at their rim
    paint = paint * (1 - 0.85 * line[..., None]) + glow[..., None] * np.array((0.75, 0.90, 1.0), np.float32) * 0.18
    # spec: per-family tiers, hot chrome, matte lattice lines, micro-facets modulate roughness
    # cyan, magenta, amber, lime, violet: tiers ordered by the family's paint luma so the spec breathes with the paint
    # two populations (the Cinder lesson): quiet cells dielectric/rough/glossed with family shades,
    # warm cells metal/smooth/no-coat, hot cells chrome; facets nudge every tier
    M = np.array([40, 22, 66, 54, 16], np.float32)[family] + 22 * facet
    R = np.array([200, 228, 176, 190, 236], np.float32)[family] - 25 * facet
    C = np.array([20, 40, 14, 30, 56], np.float32)[family] + 20 * (1 - facet)
    Mw = np.array([236, 172, 214, 190, 156], np.float32)[family] - 20 * facet
    Rw = np.array([22, 58, 30, 66, 40], np.float32)[family] + 18 * facet
    Cw = np.array([238, 150, 196, 220, 168], np.float32)[family]
    M = np.where(hot, 252.0, np.where(warm, Mw, M))
    R = np.where(hot, 8.0 + 14 * facet, np.where(warm, Rw, R))
    C = np.where(hot, 16.0, np.where(warm, Cw, C))
    M = np.where(line > 0.5, 0.0, M)
    R = np.where(line > 0.5, 225.0, R)
    C = np.where(line > 0.5, 235.0, C)
    return _up(paint, M, R, C, native, work)


# ───────────────────────────── 2. NACRE TERRACE ─────────────────────────────
_LAM = np.linspace(400.0, 700.0, 12).astype(np.float32)
_CONE = np.stack((np.exp(-((_LAM - 600) / 48.0) ** 2) + 0.28 * np.exp(-((_LAM - 445) / 25.0) ** 2),
                  np.exp(-((_LAM - 548) / 52.0) ** 2),
                  np.exp(-((_LAM - 452) / 42.0) ** 2)), 0)                    # 3 x 12
_CONE = _CONE / _CONE.sum(1, keepdims=True)


def _interference_rgb(d_nm, n=1.62):
    """Two-beam thin-film reflectance colour for thickness d (nm), 12-wavelength integral."""
    phase = (4 * np.pi * n * d_nm[..., None]) / _LAM[None, None, :] + np.pi
    I = 0.5 * (1 + np.cos(phase))                                            # H x W x 12
    return np.einsum('hwl,cl->hwc', I.astype(np.float32), _CONE.astype(np.float32))


def _nacre_terrace(shape, seed):
    native, work, X, Y = _work(shape)
    rng = np.random.default_rng((int(seed) + 71) & 0x7FFFFFFF)
    P = 15.0                                   # platelet pitch (native px)
    gx, gy = np.floor(X / P), np.floor(Y / P)
    best1, best2, cid = np.full(X.shape, 1e9, np.float32), np.full(X.shape, 1e9, np.float32), np.zeros(X.shape, np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx, cy = gx + dx, gy + dy
            jx, jy = _h01(cx.astype(np.int64), cy.astype(np.int64)), _h01(cy.astype(np.int64), cx.astype(np.int64) + 7)
            sx, sy = (cx + 0.15 + 0.7 * jx) * P, (cy + 0.15 + 0.7 * jy) * P
            d = np.hypot(X - sx, Y - sy)
            closer = d < best1
            best2 = np.where(closer, best1, np.minimum(best2, d))
            best1 = np.where(closer, d, best1)
            cid = np.where(closer, _h01(cx.astype(np.int64) + 3, cy.astype(np.int64) + 11), cid)
    boundary = np.clip(1.0 - (best2 - best1) / 1.6, 0, 1)                    # conchiolin seams 1-2 px
    # screw-dislocation growth terraces: several spiral step fields, 38 px risers
    Xs, Ys = X[::2, ::2], Y[::2, ::2]
    step_field = np.zeros(Xs.shape, np.float32)
    n_c = 34
    for k in range(n_c):
        cx, cy = rng.uniform(0, 2048.0), rng.uniform(0, 2048.0)
        r = np.hypot(Xs - cx, Ys - cy)
        th = np.arctan2(Ys - cy, Xs - cx)
        turn = 1.0 if k % 2 == 0 else -1.0
        wgt = np.exp(-(r / (0.13 * 2048.0)) ** 2)
        step_field += wgt * (r / 14.0 + turn * th / (2 * np.pi))
    if cv2 is not None:
        step_field = cv2.resize(step_field, (X.shape[1], X.shape[0]), interpolation=cv2.INTER_LINEAR)
    else:
        step_field = np.repeat(np.repeat(step_field, 2, 0), 2, 1)[:X.shape[0], :X.shape[1]]
    terrace = np.floor(step_field).astype(np.int64)
    order = np.mod(terrace, 8)
    riser = np.clip(1.0 - np.abs(step_field - np.round(step_field)) * 14.0 / 1.2, 0, 1)   # step edges 1-2 px
    tilt = (np.mod(X, P) / P - 0.5) * (cid - 0.5) * 2.0                      # within-platelet gradient
    d_nm = 210.0 + 44.0 * order + 46.0 * (cid - 0.5) + 30.0 * tilt           # 190..560 nm: colour drifts along the terrace, each platelet its own shade
    irgb = _interference_rgb(d_nm)
    irgb = irgb / max(float(irgb.max()), 1e-6)
    mean = irgb.mean(2, keepdims=True)
    irgb = np.clip(mean + 1.9 * (irgb - mean), 0, 1)                         # nacre chroma: the film colours, not their pastel average
    pearl = np.array((0.92, 0.90, 0.86), np.float32)
    shade = 0.78 + 0.26 * _h01((cid * 4096).astype(np.int64), terrace)
    paint = (0.10 + 0.90 * irgb ** 0.80) * pearl[None, None, :] * shade[..., None]
    paint = paint * (1 - 0.72 * boundary[..., None]) * (1 + 0.28 * riser[..., None])
    # spec: terrace order alternates metal and dielectric pearl, coat by order, seams matte
    # owner 2026-09-02: the terrace-band spec 'lets me down'. Cinder lesson instead: every platelet is one
    # of sixteen material states in two populations (metal/smooth/no-coat and dielectric/rough/glossed),
    # shades seeded, the film's own luma nudging the tier, risers chrome and seams matte.
    from engine.expansions.impossible_glint_2026 import _spec_tables
    Ms, Rs, Cs, _kind = _spec_tables(int(seed) + 4201, n_on=7, n_mid=2)
    state = np.mod(np.floor(cid * 16).astype(np.int32) + order, 16)
    lum = np.clip(paint.mean(2) / 0.85, 0, 1)
    M = Ms[state] + 40 * (lum - 0.5) + 25 * tilt
    R = Rs[state] - 30 * (lum - 0.5) + 25 * np.abs(tilt)
    C = Cs[state] + 30 * (0.5 - lum) * (1 - shade)
    M = np.where(riser > 0.5, 255.0, M)
    C = np.where(riser > 0.5, 16.0, C)
    R = np.where(riser > 0.5, 6.0, R)
    M = np.where(boundary > 0.6, 0.0, M)
    R = np.where(boundary > 0.6, 215.0, R)
    C = np.where(boundary > 0.6, 225.0, C)
    return _up(paint, M, R, C, native, work)


# ───────────────────────────── 3. CAUSTIC LOOM ─────────────────────────────
def _caustic_loom(shape, seed):
    native, work, X, Y = _work(shape)
    hh, ww = work
    rng = np.random.default_rng((int(seed) + 977) & 0x7FFFFFFF)
    a = rng.uniform(0.35, 0.75)
    u0 = X * np.cos(a) + Y * np.sin(a)
    v0 = -X * np.sin(a) + Y * np.cos(a)
    P = 26.0
    # domain warp: the loom sags and twists, so the focal lines become sinuous filaments, not a dot grid
    u = u0 + 9.0 * np.sin(v0 / 61.0 + 1.3 * np.sin(u0 / 97.0)) + 4.0 * np.sin(u0 / 23.0 + v0 / 41.0)
    v = v0 + 9.0 * np.cos(u0 / 71.0 - 1.1 * np.sin(v0 / 83.0)) + 4.0 * np.cos(v0 / 19.0 - u0 / 37.0)                                   # ribbon pitch (native px)
    ru, rv = 0.5 + 0.5 * np.cos(2 * np.pi * u / P), 0.5 + 0.5 * np.cos(2 * np.pi * v / P)
    over_u = 0.5 + 0.5 * np.tanh(4.0 * np.sin(np.pi * u / P) * np.sin(np.pi * v / P))   # twill: which ribbon is on top
    h = ru ** 1.6 * (0.55 + 0.45 * over_u) + rv ** 1.6 * (0.55 + 0.45 * (1 - over_u))
    h += 0.05 * np.sin(u / 3.1 + 0.8 * np.sin(v / 5.3)) + 0.04 * np.sin(v / 2.7)
    scale = float(hh) / 2048.0                 # work px per reference px
    gy, gx = np.gradient(h)                    # per work pixel
    # thin-lens refraction onto the paint plane: deflection = D (n-1) grad h, dispersion in n
    D = 4.6 * scale
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    caustic = np.zeros((hh, ww, 3), np.float32)
    lam_w = np.array([[1.0, 0.0, 0.0], [0.6, 0.6, 0.0], [0.0, 1.0, 0.0], [0.0, 0.5, 0.7], [0.0, 0.0, 1.0]], np.float32)
    for i, dn in enumerate((0.11, 0.055, 0.0, -0.05, -0.10)):        # exaggerated glass dispersion: rainbow-edged folds
        k = D * (0.52 + dn)
        for sx, sy in ((0.0, 0.0), (0.5, 0.0), (0.0, 0.5), (0.5, 0.5)):    # 4 photons per work pixel
            px = np.clip(np.rint(xx + sx - k * gx * 40.0), 0, ww - 1).astype(np.int64)
            py = np.clip(np.rint(yy + sy - k * gy * 40.0), 0, hh - 1).astype(np.int64)
            hist = np.bincount((py * ww + px).ravel(), minlength=hh * ww).reshape(hh, ww).astype(np.float32)
            caustic += hist[..., None] * lam_w[i][None, None, :]
    caustic /= max(float(caustic.mean()), 1e-6)  # 1.0 = unfocused light
    if cv2 is not None:
        caustic = cv2.GaussianBlur(caustic, (0, 0), 0.7)
    light = np.clip((caustic - 0.9) / 2.6, 0, 1) ** 1.15   # only the folds (>= ~2x) shine
    body_u = np.array((0.02, 0.36, 0.40), np.float32)
    body_v = np.array((0.46, 0.04, 0.26), np.float32)
    body = body_u[None, None, :] * over_u[..., None] + body_v[None, None, :] * (1 - over_u[..., None])
    paint = body * (0.55 + 0.85 * h[..., None]) * (1 - 0.6 * light.mean(2)[..., None]) + light * 1.05
    bright = light.mean(2)
    crest = np.clip((h - 0.78) / 0.12, 0, 1)
    trough = np.clip((0.32 - h) / 0.14, 0, 1)
    # spec: caustic filaments are glass, ribbon crests chrome, troughs satin, under-ribbons darker coat
    M = 30 + 175 * crest + 60 * over_u * (1 - crest)
    R = 120 - 70 * crest - 40 * over_u + 60 * trough
    C = 90 + 90 * trough - 50 * crest + 40 * (1 - over_u)
    fil = bright > 0.45
    # the light itself is the material: where the folds land the coat is glass, the surface mirror-smooth
    M = M * (1 - bright) + 10.0 * bright
    R = R * (1 - bright) + 8.0 * bright
    C = C * (1 - bright) + 16.0 * bright
    # quantise to eight crisp tiers per channel so neighbours contrast under a moving light
    M, R, C = (np.round(z / 32.0) * 32.0 for z in (M, R, C))
    C = np.where(fil, 16.0, C)
    return _up(paint, M, R, C, native, work)


BUILDERS = {
    "impossible_penrose_reactor": _penrose_reactor,
    "impossible_nacre_terrace": _nacre_terrace,
    "impossible_caustic_loom": _caustic_loom,
}


def _arrays(fid, shape, seed):
    key = (fid, int(shape[0]), int(shape[1]), int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return _CACHE[key]
    value = BUILDERS[fid](shape, seed)
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 3:
            _CACHE.popitem(last=False)
    return value


def _mk(fid):
    def paint_fn(paint, shape, mask, seed, pm, bb, _fid=fid):
        del bb
        authored, _ = _arrays(_fid, shape, seed)
        src = np.asarray(paint, np.float32)[..., :3]
        if src.max(initial=0) > 1.5:
            src = src / 255.0
        m = np.asarray(mask, np.float32)
        m = m[..., 0] if m.ndim == 3 else m
        mix = (np.clip(m, 0, 1) * float(pm))[..., None]
        return np.clip(src * (1 - mix) + authored * mix, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm, _fid=fid):
        del sm
        _, spec = _arrays(_fid, shape, seed)
        m = np.asarray(mask, np.float32)
        m = m[..., 0] if m.ndim == 3 else m
        out = np.empty(spec.shape[:2] + (4,), np.uint8)
        out[..., :3] = (spec.astype(np.float32) * np.clip(m, 0, 1)[..., None]).astype(np.uint8)
        out[..., 3] = (np.clip(m, 0, 1) * 255).astype(np.uint8)
        return out
    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None, fusion_reg=None):
    for fid in BUILDERS:
        mono_reg[fid] = _mk(fid)
    return "%d impossible trio installed" % len(BUILDERS)
