# -*- coding: utf-8 -*-
"""REDESIGN WAVE 2 (2026-06-10) — the full rollout after the b10 proof batch.

Owner mandate: tackle EVERYTHING still busted — all 29 PRIZM (punted, full
drawing-board redo), the remaining LFR rebuilds, the hung spec overlays — with
truly UNIQUE, STUNNING designs. "NO COOKIE CUTTER crap. Come up with new
functions and paint ideas to really stretch the boundaries."

NEW ART-ENGINE PRIMITIVES (this file, never existed in SPB before):
  _attractor      strange-attractor density fields (De Jong / Clifford) — organic
                  filigree of literally millions of points, infinitely fine
  _gray_scott     Gray-Scott reaction-diffusion (coral/maze/mitosis/worms) — grown
                  micro-structure no hand-drawn noise can imitate
  _flowlines      particle advection through curl-noise wind fields — feathered
                  silk / aurora / current linework
  _caustics       refracted-light density (grid photons bent through a lens field)
                  — real pool-light webs, not voronoi fakes
  _harmonograph   damped twin-pendulum curves — banknote guilloche / engine-turn
  _crystal        anisotropic multi-seed crystal growth (per-site stretched metric)
                  — faceted shards with true grain direction
  _engrave        tone-modulated curved hatch engraving (banknote line shading)
  _dendrites      recursive branching growth — lightning / frost ferns / roots
  _stars          multi-magnitude starfields with diffraction-spiked anchors
  _curves         fast float polyline rasterizer with glow (cv2.polylines core)

Every finish below is a bespoke composition of these + color_science (oklch_ramp,
interference_palette, candy_absorb). Spec TRACES the paint geometry (same fields,
same seed — Wovenlight doctrine) with an angle-gated ignition per finish.
Coverage >= 0.80 enforced by harness; <= 2s at the 1024 work grid; patterns render
native-res. Wired live via install_into_engine() (monolithic + base + pattern
routes + spec-overlay catalog), called from _spb_apply_colorshift_rework_2026.
"""
import math

import numpy as np
import cv2

from engine.color_science import oklch_ramp, interference_palette, candy_absorb
from engine.expansions.redesign_b10_2026 import (
    _rng, _coords, _noise, _warp, _splat_points, _sr, _microtex,
    _seed_int, _up, _m2, _pack, _WORK,
)


def _n01(a):
    a = np.asarray(a, np.float32)
    a = a - a.min()
    return (a / max(float(a.max()), 1e-6)).astype(np.float32)


_FIELD_CACHE = {}


def _memo(fn):
    """Memoize a _fields(h, w, s) geometry builder. Paint + spec of the same
    finish share identical fields (Wovenlight marriage), so each live render
    calls the builder twice — this halves the real cost of every design."""
    def wrap(h, w, s):
        key = (fn.__name__, h, w, s)
        if key not in _FIELD_CACHE:
            if len(_FIELD_CACHE) > 10:
                _FIELD_CACHE.pop(next(iter(_FIELD_CACHE)))
            _FIELD_CACHE[key] = fn(h, w, s)
        return _FIELD_CACHE[key]
    wrap.__name__ = fn.__name__
    return wrap


def _polish(body, h, w, s, grain=0.06):
    """Work-grid coverage tooth: zero-mean 1-3px detail ADDED so even dark regions
    carry micro structure. The heavier lifting happens at NATIVE res afterwards
    (_native_finish) — calibrated 2026-06-10: upscale halves grain amplitude, so
    work-grid grain alone can't clear the coverage gate without looking like static."""
    g = (_noise(h, w, s ^ 0x9A1, (1.6, 3.2)) - 0.5)
    lift = 0.80 + 0.20 * np.asarray(body, np.float32).mean(2, keepdims=True)
    return np.clip(body + g[..., None] * grain * 2.0 * lift, 0, 1).astype(np.float32)


def _native_finish(eff, s, grain=0.14, sharp=0.85):
    """NATIVE-resolution finishing pass, applied AFTER the work->output upscale
    (live wiring + harness use the identical call). Two jobs:
      1. unsharp: re-amplifies the design's own 2-6px energy that INTER_LINEAR
         upscaling muted — restores crispness, no noise added;
      2. native grain: 1-3px zero-mean flake tooth at full output res — the
         mechanical full-coverage floor (calibrated vs the cov>=0.80 gate)."""
    fh, fw = eff.shape[:2]
    eff = np.asarray(eff, np.float32)
    blur = cv2.GaussianBlur(eff, (0, 0), 1.2)
    eff = np.clip(eff + (eff - blur) * sharp, 0, 1)
    g = (_noise(fh, fw, _seed_int(s) ^ 0x7E37, (1.5, 3.0)) - 0.5)
    lift = 0.75 + 0.25 * eff.mean(2, keepdims=True)
    return np.clip(eff + g[..., None] * grain * 2.0 * lift, 0, 1).astype(np.float32)


def _ramp(stops, t, flatten_lightness=0.0):
    """LUT-cached oklch_ramp: the real oklch_ramp runs its iterative gamut clamp
    over every pixel (~2s/call at 1024^2 - profiled, it dwarfed the geometry), so
    evaluate it once on 512 samples and index the field through the LUT. Identical
    output to per-pixel evaluation within 1/512 quantization."""
    lut = oklch_ramp(tuple(stops), np.linspace(0, 1, 512, dtype=np.float32),
                     flatten_lightness=flatten_lightness)
    idx = np.clip(np.asarray(t, np.float32) * 511.0, 0, 511).astype(np.int32)
    return np.asarray(lut, np.float32)[idx]


def _ipal(t, n_layers, strength, base_srgb):
    """LUT-cached interference_palette (same trick as _ramp)."""
    lut = interference_palette(np.linspace(0, 1, 512, dtype=np.float32),
                               n_layers, strength, base_srgb=base_srgb)[..., :3]
    idx = np.clip(np.asarray(t, np.float32) * 511.0, 0, 511).astype(np.int32)
    return np.asarray(lut, np.float32)[idx]


def _sstep(e0, e1, x):
    t = np.clip((x - e0) / max(e1 - e0, 1e-6), 0, 1)
    return (t * t * (3 - 2 * t)).astype(np.float32)


def _gauss(a, sg):
    return cv2.GaussianBlur(a, (0, 0), max(float(sg), 0.3))


# ---------------------------------------------------------------- curve rasterizer
def _curves(h, w, polys, thick=1, val=1.0, glow=0.0):
    """Rasterize a list of float polylines (each (n,2) [x,y]) onto a float canvas.
    cv2.polylines is the C++ fast path; glow adds a soft blurred halo."""
    img = np.zeros((h, w), np.float32)
    if polys:
        pts = [np.round(p).astype(np.int32).reshape(-1, 1, 2) for p in polys if len(p) >= 2]
        if pts:
            cv2.polylines(img, pts, False, float(val), int(max(1, thick)), cv2.LINE_AA)
    if glow > 0:
        img = np.maximum(img, _gauss(img, glow) * 2.2)
    return np.clip(img, 0, 1)


# ---------------------------------------------------------------- strange attractor
def _attractor(h, w, seed, kind="dejong", n_walk=4000, n_iter=620, params=None,
               span=2.15, sigma=0.0):
    """Density map of a strange attractor. n_walk walkers iterated n_iter times,
    vectorized per step -> ~2.5M points through histogram2d. Organic filigree."""
    rng = _rng(seed, 11)
    if params is None:
        # sample params until the orbit is non-degenerate (bounded, spread out)
        for _ in range(24):
            p = rng.uniform(-2.6, 2.6, 4)
            x = rng.uniform(-1, 1, 64); y = rng.uniform(-1, 1, 64)
            for _i in range(140):
                if kind == "clifford":
                    x, y = (np.sin(p[0] * y) + p[2] * np.cos(p[0] * x),
                            np.sin(p[1] * x) + p[3] * np.cos(p[1] * y))
                else:
                    x, y = (np.sin(p[0] * y) - np.cos(p[1] * x),
                            np.sin(p[2] * x) - np.cos(p[3] * y))
            if float(x.std() + y.std()) > 0.9:
                break
    else:
        p = np.asarray(params, np.float64)
    x = rng.uniform(-1, 1, n_walk); y = rng.uniform(-1, 1, n_walk)
    xs = np.empty((n_iter, n_walk), np.float32); ys = np.empty((n_iter, n_walk), np.float32)
    for i in range(n_iter + 24):
        if kind == "clifford":
            x, y = (np.sin(p[0] * y) + p[2] * np.cos(p[0] * x),
                    np.sin(p[1] * x) + p[3] * np.cos(p[1] * y))
        else:
            x, y = (np.sin(p[0] * y) - np.cos(p[1] * x),
                    np.sin(p[2] * x) - np.cos(p[3] * y))
        if i >= 24:
            xs[i - 24] = x; ys[i - 24] = y
    px = xs.ravel(); py = ys.ravel()
    if sigma > 0:
        px = px + rng.normal(0, sigma, px.size).astype(np.float32)
        py = py + rng.normal(0, sigma, py.size).astype(np.float32)
    hist, _, _ = np.histogram2d(py, px, bins=(h, w),
                                range=[[-span, span], [-span, span]])
    d = np.log1p(hist.astype(np.float32))
    return _n01(d)


# ---------------------------------------------------------------- reaction-diffusion
_GS_PRESETS = {
    "coral":   (0.0545, 0.0620),
    "mitosis": (0.0367, 0.0649),
    "worms":   (0.0780, 0.0610),
    "maze":    (0.0290, 0.0570),
    "solitons": (0.0300, 0.0620),
    "fingerprint": (0.0370, 0.0600),
}
_GS_KERN = np.float32([[0.05, 0.20, 0.05], [0.20, -1.0, 0.20], [0.05, 0.20, 0.05]])


def _gray_scott(h, w, seed, preset="coral", iters=260, grid=448, seeds=140, fine=1.0, speckle=0.0):
    """Gray-Scott reaction-diffusion grown from random seed spots; returns the
    grown V field upsampled to (h,w), normalized. Real grown micro-structure.
    fine<1 scales diffusion down -> proportionally finer wavelength at the SAME
    grid (the cheap way to crush features; big grids are too slow)."""
    f, k = _GS_PRESETS[preset]
    rng = _rng(seed, 23)
    g = int(grid)
    U = np.ones((g, g), np.float32)
    V = np.zeros((g, g), np.float32)
    for _ in range(int(seeds)):
        cy, cx = int(rng.uniform(0, g)), int(rng.uniform(0, g))
        r = int(rng.uniform(2, 6))
        V[max(0, cy - r):cy + r, max(0, cx - r):cx + r] = 1.0
    V += (rng.random((g, g)).astype(np.float32) < max(0.0015, speckle)) * 1.0
    du, dv = 0.21 * fine, 0.105 * fine
    for _ in range(int(iters)):
        lu = cv2.filter2D(U, -1, _GS_KERN, borderType=cv2.BORDER_REFLECT)
        lv = cv2.filter2D(V, -1, _GS_KERN, borderType=cv2.BORDER_REFLECT)
        uvv = U * V * V
        U += du * lu - uvv + f * (1.0 - U)
        V += dv * lv + uvv - (f + k) * V
        np.clip(U, 0, 1, out=U); np.clip(V, 0, 1, out=V)
    out = cv2.resize(V, (w, h), interpolation=cv2.INTER_CUBIC)
    return _n01(out)


# ---------------------------------------------------------------- flow-field lines
def _flow_theta(h, w, seed, scale=180.0, turns=2.0, swirls=0):
    """Smooth angle field; optional vortex swirl centers added on top."""
    th = _noise(h, w, seed ^ 0x4F1, (scale * 0.5, scale)) * (np.pi * 2 * turns)
    if swirls:
        yy, xx = _coords(h, w)
        rng = _rng(seed, 31)
        for _ in range(int(swirls)):
            cy, cx = rng.uniform(0, h), rng.uniform(0, w)
            th = th + np.arctan2(yy - cy, xx - cx) * rng.choice([-1.0, 1.0]) * \
                np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * (0.22 * max(h, w)) ** 2))
    return th.astype(np.float32)


def _flowlines(h, w, seed, n=1100, steps=120, step_len=2.2, theta=None,
               thick=1, glow=0.0, fade=False):
    """Advect n particles through an angle field; rasterize their paths.
    Feathered silk / aurora / current linework."""
    if theta is None:
        theta = _flow_theta(h, w, seed)
    rng = _rng(seed, 37)
    px = rng.uniform(0, w - 1, n).astype(np.float32)
    py = rng.uniform(0, h - 1, n).astype(np.float32)
    paths = np.empty((steps, n, 2), np.float32)
    for i in range(steps):
        ix = np.clip(px.astype(np.int32), 0, w - 1)
        iy = np.clip(py.astype(np.int32), 0, h - 1)
        a = theta[iy, ix]
        px = px + np.cos(a) * step_len
        py = py + np.sin(a) * step_len
        np.clip(px, 0, w - 1, out=px); np.clip(py, 0, h - 1, out=py)
        paths[i, :, 0] = px; paths[i, :, 1] = py
    if fade:
        # rasterize in 3 segments with decreasing value -> comet-fade strands
        out = np.zeros((h, w), np.float32)
        cuts = [(0, steps // 3, 0.35), (steps // 3, 2 * steps // 3, 0.65),
                (2 * steps // 3, steps, 1.0)]
        for a0, a1, v in cuts:
            polys = [paths[a0:a1, j] for j in range(n)]
            out = np.maximum(out, _curves(h, w, polys, thick=thick, val=v))
        if glow > 0:
            out = np.maximum(out, _gauss(out, glow) * 1.8)
        return np.clip(out, 0, 1)
    polys = [paths[:, j] for j in range(n)]
    return _curves(h, w, polys, thick=thick, val=1.0, glow=glow)


# ---------------------------------------------------------------- light caustics
def _caustics(h, w, seed, strength=42.0, scale=170.0, sharp=1.6, grid_mul=1.35):
    """Photon-refraction density: a uniform grid of rays bent by the gradient of a
    smooth lens field, binned -> bright caustic web exactly like pool light."""
    gh, gw = int(h * grid_mul), int(w * grid_mul)
    lens = _noise(gh, gw, seed ^ 0xCA57, (scale * 0.6, scale, scale * 2.2))
    gy, gx = np.gradient(_gauss(lens, scale * 0.06))
    yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
    px = (xx + gx * strength * gw / 12.0) * (w / gw)
    py = (yy + gy * strength * gh / 12.0) * (h / gh)
    hist, _, _ = np.histogram2d(py.ravel(), px.ravel(), bins=(h, w),
                                range=[[0, h], [0, w]])
    d = hist.astype(np.float32) * (h * w / (gh * gw))
    d = _gauss(d, 0.8)
    return np.clip(_n01(d) ** sharp, 0, 1)


# ---------------------------------------------------------------- harmonograph
def _harmonograph(h, w, seed, cells=1, m=2600, pens=2, decay=0.55, thick=1, jitter=0.0):
    """Damped twin-pendulum drawings — banknote guilloche. cells>1 lays a grid of
    independent rosettes (fine engine-turning)."""
    rng = _rng(seed, 41)
    allp = []
    cell_h, cell_w = h / cells, w / cells
    rad = 0.46 * min(cell_h, cell_w)
    t = np.linspace(0, 18 * np.pi, m).astype(np.float32)
    for cy in range(int(cells)):
        for cx in range(int(cells)):
            ctr = ((cx + 0.5 + rng.uniform(-jitter, jitter)) * cell_w,
                   (cy + 0.5 + rng.uniform(-jitter, jitter)) * cell_h)
            r_cell = rad * (rng.uniform(0.58, 0.94) if jitter else 1.0)
            for _ in range(pens):
                f1, f2 = rng.uniform(2.0, 7.0, 2)
                f2 = round(f2) + rng.choice([0.0, 0.005, 0.01])  # near-resonant
                p1, p2, p3, p4 = rng.uniform(0, 2 * np.pi, 4)
                d1, d2 = rng.uniform(0.002, 0.012, 2) * decay
                x = (np.sin(t * f1 + p1) * np.exp(-d1 * t) +
                     np.sin(t * f2 + p2) * np.exp(-d2 * t)) * 0.5
                y = (np.sin(t * f1 + p3) * np.exp(-d2 * t) +
                     np.sin(t * f2 + p4) * np.exp(-d1 * t)) * 0.5
                allp.append(np.stack([ctr[0] + x * r_cell, ctr[1] + y * r_cell], -1))
    return _curves(h, w, allp, thick=thick)


# ---------------------------------------------------------------- crystal growth
def _crystal(h, w, seed, n_sites=90, aniso=3.2, res=0.5):
    """Anisotropic multi-seed growth. Each site has its own grain direction and
    stretch; pixels claim the site with smallest TRANSFORMED distance among the
    k nearest euclidean candidates. Returns (cell_id, edge_dist01, orient, axial)
    — axial = signed coordinate along the winning site's grain (striations).
    res<1 computes on a reduced grid and upsamples (NEAREST for ids) — the cells
    are large-scale structure, so half-res is visually identical and ~4x faster."""
    if res < 1.0:
        sh, sw = max(64, int(h * res)), max(64, int(w * res))
        cid, edge, orient, axial = _crystal(sh, sw, seed, n_sites, aniso, res=1.0)
        cid = cv2.resize(cid.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST).astype(np.int64)
        edge = cv2.resize(edge, (w, h), interpolation=cv2.INTER_LINEAR)
        orient = cv2.resize(orient, (w, h), interpolation=cv2.INTER_NEAREST)
        axial = cv2.resize(axial, (w, h), interpolation=cv2.INTER_LINEAR) / res
        return cid, edge, orient, axial
    from scipy.spatial import cKDTree
    rng = _rng(seed, 53)
    pts = np.stack([rng.uniform(0, h, n_sites), rng.uniform(0, w, n_sites)], -1)
    ang = rng.uniform(0, np.pi, n_sites).astype(np.float32)
    stretch = rng.uniform(min(1.2, aniso * 0.92), aniso, n_sites).astype(np.float32)
    tree = cKDTree(pts)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    q = np.stack([yy.ravel(), xx.ravel()], -1)
    k = min(10, n_sites)
    _, idx = tree.query(q, k=k, workers=-1)
    # PERF 2026-06-13 (wave2 lane): the per-candidate transform below was the hot
    # cost (~0.4s of the core), and it was running in float64 because `pts` is
    # float64. Cast the gathered candidate coords to float32 so dy/dx/u/v/td are
    # float32 — halves the memory bandwidth of the (N*k) arrays. Visually identical
    # (edge delta ~5e-5; cell winners match modulo at most ~1 sub-pixel tie in 4M).
    ptsf = pts.astype(np.float32)
    dy = q[:, 0:1] - ptsf[idx, 0]; dx = q[:, 1:2] - ptsf[idx, 1]
    ca = np.cos(ang[idx]); sa = np.sin(ang[idx])
    u = (dx * ca + dy * sa) / stretch[idx]   # along grain (stretched -> grows long)
    v = (-dx * sa + dy * ca)
    td = u * u + v * v
    order = np.argsort(td, axis=1)
    nq = np.arange(len(q))
    o0 = order[:, 0]; o1 = order[:, 1]
    best = idx[nq, o0]
    d0 = np.sqrt(td[nq, o0])
    d1 = np.sqrt(td[nq, o1])
    edge = ((d1 - d0) / (d1 + d0 + 1e-5)).astype(np.float32)  # 0 at borders, ->1 inside
    ub = u[nq, o0].astype(np.float32)
    return (best.reshape(h, w), edge.reshape(h, w),
            ang[best].reshape(h, w), ub.reshape(h, w))


# ---------------------------------------------------------------- engraved hatching
def _engrave(h, w, tone, seed, pitch=7.0, curl=30.0, angle=None, sharp=3.0):
    """Banknote-style engraving: curved parallel grooves whose ink thickness is
    modulated by the tone field (dark tone = fat line, light = hairline)."""
    yy, xx = _coords(h, w)
    rng = _rng(seed, 61)
    a = float(rng.uniform(0, np.pi)) if angle is None else float(angle)
    phase = (xx * np.cos(a) + yy * np.sin(a)) + \
        (_noise(h, w, seed ^ 0xE6, (pitch * 9, pitch * 28)) - 0.5) * curl
    band = 0.5 + 0.5 * np.cos(phase * (2 * np.pi / max(pitch, 2.0)))
    t = np.clip(np.asarray(tone, np.float32), 0, 1)
    ink = np.clip((t * 1.06 + 0.02 - band) * sharp + 0.5, 0, 1)
    return ink.astype(np.float32)


# ---------------------------------------------------------------- dendrites
def _dendrites(h, w, seed, n_roots=26, depth=5, spread=0.62, seg=None, thick=2):
    """Recursive branching growth (lightning / frost ferns / river deltas).
    Segments collected per generation, rasterized thick->thin."""
    rng = _rng(seed, 71)
    sr = _sr(h, w)
    seg = seg or 26 * sr
    gen = [(np.stack([rng.uniform(0, w, n_roots), rng.uniform(0, h, n_roots)], -1),
            rng.uniform(0, 2 * np.pi, n_roots))]
    out = np.zeros((h, w), np.float32)
    for d in range(depth):
        pts, ang = gen[-1]
        n = len(pts)
        if n == 0 or n > 9000:
            break
        ln = seg * (0.82 ** d) * rng.uniform(0.7, 1.3, n)[:, None]
        steps = 5
        path = [pts]
        a = ang.copy()
        for _s in range(steps):
            a = a + rng.normal(0, 0.16, n)
            path.append(path[-1] + np.stack([np.cos(a), np.sin(a)], -1) * (ln / steps))
        polys = [np.stack([p[i] for p in path]) for i in range(n)]
        v = 1.0 - d * 0.13
        out = np.maximum(out, _curves(h, w, polys, thick=max(1, int(round(thick * (0.78 ** d)))), val=v))
        tips = path[-1]
        # branch: each tip spawns 2 children at +/- spread (with some die-off)
        keep = rng.random(n) < (0.94 if d < 2 else 0.8)
        tips = tips[keep]; a2 = a[keep]
        br = np.concatenate([tips, tips]); ba = np.concatenate([a2 - spread * rng.uniform(0.6, 1.3),
                                                                a2 + spread * rng.uniform(0.6, 1.3)])
        gen.append((br, ba))
    return out


# ---------------------------------------------------------------- starfield
def _stars(h, w, seed, n=9000, bright_frac=0.02, spikes=True):
    """Dense multi-magnitude starfield: thousands of sub-pixel stars via add.at,
    a handful of blazing anchors with gaussian cores + diffraction spikes."""
    rng = _rng(seed, 83)
    out = np.zeros((h, w), np.float32)
    xs = rng.uniform(0, w - 1, n); ys = rng.uniform(0, h - 1, n)
    mag = rng.power(4.5, n).astype(np.float32)  # skewed dim
    np.add.at(out, (ys.astype(np.int32), xs.astype(np.int32)), mag * 0.55)
    out = _gauss(out, 0.6)
    nb = max(4, int(n * bright_frac))
    bx = rng.uniform(0, w - 1, nb); by = rng.uniform(0, h - 1, nb)
    bv = rng.uniform(0.55, 1.0, nb)
    sr = _sr(h, w)
    star = np.zeros((h, w), np.float32)
    np.add.at(star, (by.astype(np.int32), bx.astype(np.int32)), bv)
    out = np.maximum(out, _gauss(star, 1.6 * sr) * 7.0)
    if spikes:
        polys = []
        for i in range(nb):
            L = bv[i] * 9.0 * sr
            polys.append(np.float32([[bx[i] - L, by[i]], [bx[i] + L, by[i]]]))
            polys.append(np.float32([[bx[i], by[i] - L], [bx[i], by[i] + L]]))
        out = np.maximum(out, _curves(h, w, polys, thick=1, val=0.8) * 0.7)
    return np.clip(out, 0, 1)


def _dirblur(a, angle, klen):
    """Directional (motion) blur along angle — brushed metal anisotropy."""
    klen = int(klen) | 1
    if klen < 3:
        return a
    k = np.zeros((klen, klen), np.float32)
    c = klen // 2
    for t in range(klen):
        x = int(round(c + math.cos(angle) * (t - c)))
        y = int(round(c + math.sin(angle) * (t - c)))
        if 0 <= x < klen and 0 <= y < klen:
            k[y, x] = 1.0
    k /= max(k.sum(), 1.0)
    return cv2.filter2D(a, -1, k)


def _mix(*layers):
    """Mix [(rgb_or_scalar, weight_field), ...] -> HxWx3."""
    h, w = None, None
    for c, m in layers:
        mm = np.asarray(m, np.float32)
        h, w = mm.shape[:2]
        break
    acc = np.zeros((h, w, 3), np.float32)
    wsum = np.zeros((h, w, 1), np.float32)
    for c, m in layers:
        c = np.asarray(c, np.float32)
        if c.ndim == 1:
            c = c[None, None, :]
        m = np.asarray(m, np.float32)[..., None]
        acc += c * m
        wsum += m
    return acc / np.maximum(wsum, 1e-5)


# ------------------------------------------------------------- coverage carriers
def _finefill(h, w, s, amp=0.20, scales=(1.5, 3, 7)):
    """Real-amplitude micro detail multiplied into every paint — the owner's
    full-coverage rule made mechanical: no pixel left flat. Amp must SURVIVE the
    1024->2048 upscale and the coverage gate's |g - blur4| > 0.012 test."""
    return (1.0 - amp * 0.5 + amp * _noise(h, w, s ^ 0xF1F, scales)).astype(np.float32)


def _flakes(h, w, s, density=0.10, bright=1.0):
    """Dense 1-2px metallic glitter layer; density = fraction of pixels lit."""
    n = _noise(h, w, s ^ 0x47AB, (1.6, 3.2))
    f = _sstep(1.0 - density * 1.6, 1.0 - density * 0.4, n) * bright
    return f.astype(np.float32)


# ════════════════════════════════════════════════════════════ PRIZM — 29 finishes
# Every design: a _fields() of shared geometry, paint + spec built from the SAME
# fields/seed (Wovenlight marriage), one angle-gated ignition motif per finish.

# ---------------------------------------------------------- 1. PRIZM ADAPTIVE
# Octopus camouflage: thousands of tiny skin plates, each flipping between two
# rival palettes by its own grain direction — the surface re-camouflages as the
# view angle moves. Dense papillae micro-bumps between plates.
@_memo
def _pz_adaptive_fields(h, w, s):
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=5200, aniso=1.7, res=0.5)
    pl = _sstep(0.10, 0.42, edge)                      # plate interiors
    per = _n01(np.sin(cid * 12.9898) + 1.0)            # stable per-plate random
    on = _n01(orient)
    papillae = _noise(h, w, s ^ 0xAD, (2, 4))
    return pl, per, on, papillae


def _pz_adaptive_paint(h, w, s):
    pl, per, on, pap = _pz_adaptive_fields(h, w, s)
    hue_a = _ramp([(0.16, 0.10, 0.24), (0.55, 0.27, 0.55), (0.93, 0.62, 0.50)], per, flatten_lightness=0.75)
    hue_b = _ramp([(0.05, 0.32, 0.38), (0.10, 0.62, 0.58), (0.55, 0.92, 0.86)], per, flatten_lightness=0.75)
    flip = _sstep(0.42, 0.58, on)[..., None]           # grain direction picks the side
    skin = hue_a * flip + hue_b * (1 - flip)
    body = skin * (0.92 + 0.08 * pl[..., None]) * (0.52 + 0.48 * pap[..., None])
    body += skin * _flakes(h, w, s ^ 0x5C, density=0.14, bright=0.8)[..., None] * 0.5
    return _polish(body * _finefill(h, w, s, 0.13)[..., None] + 0.03, h, w, s)


def _pz_adaptive_spec(h, w, s):
    pl, per, on, pap = _pz_adaptive_fields(h, w, s)
    gate = _sstep(0.40, 0.47, on) * (1.0 - _sstep(0.55, 0.62, on))
    M = 55 + 130 * pl * per + 60 * gate * pl
    R = np.clip(205 - 150 * pl + 38 * pap - 30 * gate, 0, 255)
    Cc = 24 + 205 * gate * pl + 28 * pap * pl           # gated plate flash
    return M.astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 2. PRIZM ALIEN SKIN
# Living exo-membrane: reaction-diffusion coral labyrinth GROWN at fine pitch —
# glossy raised ridges, bioluminescent cyan crest pulses, pore-speckled membrane.
@_memo
def _pz_alien_fields(h, w, s):
    cor = _gray_scott(h, w, s, "coral", iters=420, grid=448, seeds=40, fine=0.45, speckle=0.10)
    ridge = _sstep(0.40, 0.62, cor)
    ridge = np.clip(ridge - 0.5 * _gauss(ridge, 9) + 0.18, 0, 1)
    crest = _sstep(0.78, 0.96, cor)
    pores = _sstep(0.60, 0.86, _noise(h, w, s ^ 0x9, (2.0, 4.0)))
    depth = _gauss(ridge, 7)
    return ridge, crest, pores, depth


def _pz_alien_paint(h, w, s):
    ridge, crest, pores, depth = _pz_alien_fields(h, w, s)
    membrane = _ramp([(0.13, 0.05, 0.20), (0.34, 0.13, 0.42), (0.50, 0.28, 0.54)], depth, flatten_lightness=0.5)
    ridge_c = _ramp([(0.16, 0.30, 0.28), (0.25, 0.55, 0.46), (0.62, 0.95, 0.78)], ridge, flatten_lightness=0.45)
    skin = membrane * (1 - 0.55 * ridge[..., None]) + ridge_c * (0.55 * ridge[..., None])
    biolum = np.float32([0.35, 1.0, 0.92])[None, None, :] * (crest * 0.9)[..., None]
    skin = skin * (1 - 0.52 * pores[..., None]) + biolum
    return _polish(skin * _finefill(h, w, s, 0.12)[..., None] + 0.03, h, w, s, grain=0.075)


def _pz_alien_spec(h, w, s):
    ridge, crest, pores, depth = _pz_alien_fields(h, w, s)
    M = 40 + 95 * ridge + 115 * crest
    R = np.clip(215 - 165 * ridge - 30 * crest + 40 * pores, 0, 255)
    Cc = 26 + 205 * crest + 46 * ridge * (1 - depth)    # crest pulse = the ignition
    return M.astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 3. PRIZM ARCTIC
# Pack-ice mosaic: ~1500 slim anisotropic ice shards, tight internal striations,
# frost ferns etched along every seam, trapped-air micro sparkle throughout.
@_memo
def _pz_arctic_fields(h, w, s):
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=2600, aniso=4.6, res=0.5)
    stria = (0.5 + 0.5 * np.sin(axial * 6.2 + cid * 2.1)).astype(np.float32)
    seams = 1.0 - _sstep(0.03, 0.10, edge)
    frost = _dendrites(h, w, s ^ 0x1CE, n_roots=260, depth=4, seg=15 * _sr(h, w), thick=1)
    air = _flakes(h, w, s ^ 0xA1, density=0.07)
    return cid, edge, orient, stria, seams, frost, air


def _pz_arctic_paint(h, w, s):
    cid, edge, orient, stria, seams, frost, air = _pz_arctic_fields(h, w, s)
    per_cell = _n01(np.sin(cid * 12.9898) + 1.0)
    depth_t = np.clip(0.38 + 0.06 * per_cell + 0.56 * stria, 0, 1)
    ice = _ramp([(0.30, 0.55, 0.75), (0.62, 0.85, 0.97), (0.94, 0.99, 1.0)], depth_t, flatten_lightness=0.20)
    ice *= (0.72 + 0.28 * edge[..., None])
    ice = ice * (1 - 0.45 * seams[..., None]) + np.float32([0.78, 0.93, 1.0]) * (frost * 0.5)[..., None]
    ice += (air * 0.45)[..., None]
    return _polish(ice * _finefill(h, w, s, 0.10)[..., None], h, w, s)


def _pz_arctic_spec(h, w, s):
    cid, edge, orient, stria, seams, frost, air = _pz_arctic_fields(h, w, s)
    on = _n01(orient)
    gate = _sstep(0.30, 0.38, on) * (1 - _sstep(0.52, 0.60, on))
    M = 70 + 105 * stria * edge + 70 * gate * edge
    R = np.clip(58 + 95 * seams + 55 * frost - 40 * gate + 28 * stria, 0, 255)
    Cc = 20 + 24 * edge + 200 * air + 85 * gate * stria
    return M.astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 4. PRIZM AURORA SHIFT
# Aurora storm: thousands of sheared light strands, rippling green→teal→magenta
# over a micro-shimmering night sky thick with stars.
@_memo
def _pz_aurora_fields(h, w, s):
    base_a = float(_rng(s, 5).uniform(0, np.pi))
    th = (base_a + (_noise(h, w, s ^ 0xA0, (90, 240)) - 0.5) * 1.7).astype(np.float32)
    curt = _flowlines(h, w, s, n=3600, steps=62, step_len=2.6, theta=th, thick=1, glow=2.5, fade=True)
    yy, xx = _coords(h, w)
    rays = (0.55 + 0.45 * np.sin((xx * np.cos(base_a + np.pi / 2) + yy * np.sin(base_a + np.pi / 2)) * (2 * np.pi / 3.6) + _noise(h, w, s ^ 0x77, (30, 80)) * 9)).astype(np.float32)
    curt = (curt * rays).astype(np.float32)
    band = _noise(h, w, s ^ 0xB1, (40, 95, 210))
    sky = _stars(h, w, s ^ 0x51, n=30000, bright_frac=0.010)
    shimmer = _noise(h, w, s ^ 0x5A, (2, 4))
    return curt, band, sky, shimmer


def _pz_aurora_paint(h, w, s):
    curt, band, sky, shimmer = _pz_aurora_fields(h, w, s)
    aur = _ramp([(0.05, 0.85, 0.45), (0.10, 0.85, 0.72), (0.65, 0.30, 0.80), (0.92, 0.45, 0.60)], band)
    night = np.float32([0.03, 0.04, 0.09])[None, None, :] * (0.6 + 0.8 * shimmer[..., None])
    glow = _gauss(curt, 5)[..., None] * 0.15
    body = night + aur * (curt[..., None] * 0.95 + glow * 0.6 + 0.06) \
        + np.float32([0.9, 0.95, 1.0]) * sky[..., None] * 0.85
    return _polish(body, h, w, s, grain=0.07)


def _pz_aurora_spec(h, w, s):
    curt, band, sky, shimmer = _pz_aurora_fields(h, w, s)
    gate = _sstep(0.45, 0.52, band) * (1 - _sstep(0.62, 0.70, band))
    M = 35 + 155 * curt + 55 * gate * curt
    R = np.clip(195 - 145 * curt - 55 * _gauss(curt, 6) + 34 * shimmer, 0, 255)
    Cc = 18 + 210 * sky + 125 * curt * gate
    return M.astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 5. PRIZM BLACK RAINBOW
# Obsidian depths shot through with razor strange-attractor filigree burning in
# spectral interference; dense prismatic micro-flake keeps the black alive.
@_memo
def _pz_blackrb_fields(h, w, s):
    fil = np.zeros((h, w), np.float32)
    for i, z in enumerate((1.0, 0.55, 0.30)):
        a = _attractor(h, w, s + i * 97, kind="clifford", span=2.3 * z, sigma=0.014,
                       n_walk=3000, n_iter=520)
        fil = np.maximum(fil, a * (1.0 - 0.15 * i))
    fil = np.clip(fil * 2.6, 0, 1)
    flake = _flakes(h, w, s ^ 0xF7, density=0.30, bright=1.0)
    phase = _gauss(fil, 6) + 0.3 * _noise(h, w, s ^ 5, (110, 300))
    return fil, flake, _n01(phase)


def _pz_blackrb_paint(h, w, s):
    fil, flake, phase = _pz_blackrb_fields(h, w, s)
    # interference_palette MODULATES its base (black base -> black output, same
    # trap as candy transmission) - Black Rainbow needs an EMISSIVE spectrum ramp
    spectrum = _ramp([(0.95, 0.10, 0.16), (1.0, 0.62, 0.05), (0.95, 0.92, 0.10),
                      (0.10, 0.92, 0.45), (0.10, 0.55, 0.98), (0.55, 0.16, 0.95)],
                     phase, flatten_lightness=0.35)
    black = np.float32([0.065, 0.065, 0.080])[None, None, :] * _finefill(h, w, s, 0.5, (1.8, 3.5))[..., None]
    body = (black + spectrum * (fil[..., None] ** 1.15) * 1.55
            + (0.55 * spectrum + 0.45) * flake[..., None] * 0.85)
    return _polish(body, h, w, s, grain=0.08)


def _pz_blackrb_spec(h, w, s):
    fil, flake, phase = _pz_blackrb_fields(h, w, s)
    gate = _sstep(0.40, 0.47, phase) * (1 - _sstep(0.58, 0.66, phase))
    M = 28 + 190 * fil + 60 * flake
    R = np.clip(30 + 30 * _microtex(h, w, s ^ 9) + 85 * (1 - fil) - 50 * flake, 0, 255)
    Cc = 16 + 225 * fil * gate + 120 * flake * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 6. PRIZM BLOOD MOON
# Eclipsed regolith: a dense field of tiny sun-lit craters, fine ejecta dendrites,
# umbral blood gradient crimson→amber, gritty regolith grain everywhere.
@_memo
def _pz_bloodmoon_fields(h, w, s):
    sr = _sr(h, w)
    sun = float(_rng(s, 9).uniform(0, 2 * np.pi))

    def crater(dy, dx, rng, i):
        r = rng.uniform(2.5, 12) * sr
        d = np.sqrt(dy * dy + dx * dx) / r
        bowl = np.clip(1 - d, 0, 1) ** 1.6
        rim = np.exp(-((d - 1.0) ** 2) / 0.02)
        lit = 0.5 + 0.5 * np.clip((dx * np.cos(sun) + dy * np.sin(sun)) / (r + 1e-5), -1, 1)
        return np.clip(rim * lit - bowl * 0.65, -1, 1) * 0.5 + 0.5

    cra = _splat_points(h, w, s, int(1900 * sr * sr), crater, rad=int(9 * sr))
    cra = _sstep(0.30, 0.78, _n01(cra))
    rays = _dendrites(h, w, s ^ 0xE7, n_roots=240, depth=4, seg=18 * sr, thick=1) * 0.6
    umbra = _noise(h, w, s ^ 0x4D, (300, 700))
    reg = _noise(h, w, s ^ 0x88, (1.8, 4, 9))
    return cra, rays, umbra, reg


def _pz_bloodmoon_paint(h, w, s):
    cra, rays, umbra, reg = _pz_bloodmoon_fields(h, w, s)
    blood = _ramp([(0.30, 0.04, 0.05), (0.58, 0.09, 0.06), (0.82, 0.30, 0.10), (0.95, 0.60, 0.27)], umbra, flatten_lightness=0.70)
    relief = (0.62 + 0.38 * cra) * (0.44 + 0.56 * reg)
    body = blood * relief[..., None]
    body += np.float32([1.0, 0.72, 0.45])[None, None, :] * (rays * _sstep(0.5, 0.9, umbra))[..., None] * 0.35
    return _polish(body + 0.025, h, w, s, grain=0.07)


def _pz_bloodmoon_spec(h, w, s):
    cra, rays, umbra, reg = _pz_bloodmoon_fields(h, w, s)
    rim = _sstep(0.60, 0.82, cra)
    gate = _sstep(0.55, 0.62, umbra) * (1 - _sstep(0.75, 0.82, umbra))
    M = 35 + 125 * rim + 70 * gate * rim
    R = np.clip(165 - 85 * rim + 55 * reg - 40 * gate, 0, 255)
    Cc = 20 + 185 * rim * gate + 60 * rays
    return M.astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 7. PRIZM CANDY PAINT
# Kustom candy apple: deep Beer-Lambert crimson poured over a FULL engine-turned
# silver bed — fine interlocking guilloche net + dense metal flake, edge to edge.
@_memo
def _pz_candy_fields(h, w, s):
    turn = _harmonograph(h, w, s, cells=30, pens=1, m=540, thick=1, jitter=0.34)
    turn = np.maximum(turn, _harmonograph(h, w, s ^ 0x21, cells=54, pens=1, m=340, thick=1, jitter=0.34) * 0.75)
    flake = _flakes(h, w, s ^ 0xCF, density=0.30, bright=0.9)
    depth = _noise(h, w, s ^ 0x3C, (240, 560))
    return turn, flake, depth


def _pz_candy_paint(h, w, s):
    turn, flake, depth = _pz_candy_fields(h, w, s)
    silver = 0.34 + 0.38 * turn + 0.42 * flake
    metal = np.repeat(np.clip(silver, 0, 1)[..., None], 3, axis=2) * np.float32([0.97, 0.97, 1.0])[None, None, :]
    thick_map = np.clip(0.56 + 0.22 * depth - 0.22 * turn - 0.14 * flake, 0.08, 1.0)
    body = candy_absorb(metal, np.float32([0.92, 0.05, 0.10]), thick_map)
    return _polish(body * _finefill(h, w, s, 0.08)[..., None], h, w, s)


def _pz_candy_spec(h, w, s):
    turn, flake, depth = _pz_candy_fields(h, w, s)
    gate = _sstep(0.42, 0.50, depth) * (1 - _sstep(0.62, 0.70, depth))
    M = 90 + 110 * turn + 45 * flake
    R = np.clip(60 - 35 * turn + 30 * _microtex(h, w, s ^ 4) + 25 * (1 - depth), 0, 255)
    Cc = 30 + 175 * turn * gate + 125 * flake * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 8. PRIZM CHROME ROSE
# Liquid rose-gold chrome: tight refraction-caustic mesh streaking across hammered
# poured metal, rose→champagne, hairline polish swirl over every surface.
@_memo
def _pz_chromerose_fields(h, w, s):
    web = _caustics(h, w, s, strength=46, scale=62, sharp=1.15)
    web = np.clip(web * 2.8, 0, 1)
    pool = _noise(h, w, s ^ 0x6E, (140, 380))
    hammer = _sstep(0.25, 0.75, _noise(h, w, s ^ 0x9A, (5, 11)))
    ang = float(_rng(s, 3).uniform(0, np.pi))
    swirl = _dirblur(_noise(h, w, s ^ 0x99, (1.8, 3.5)), ang, int(15 * _sr(h, w)))
    return web, pool, hammer, swirl


def _pz_chromerose_paint(h, w, s):
    web, pool, hammer, swirl = _pz_chromerose_fields(h, w, s)
    rose = _ramp([(0.55, 0.24, 0.26), (0.80, 0.45, 0.40), (0.97, 0.78, 0.66), (1.0, 0.95, 0.88)],
                      np.clip(0.30 + 0.16 * pool + 0.44 * web + 0.26 * hammer, 0, 1), flatten_lightness=0.55)
    body = rose * (0.70 + 0.30 * swirl[..., None]) * (0.74 + 0.26 * hammer[..., None])
    body += np.float32([1.0, 0.94, 0.88])[None, None, :] * (web ** 1.6)[..., None] * 0.55
    return _polish(body, h, w, s)


def _pz_chromerose_spec(h, w, s):
    web, pool, hammer, swirl = _pz_chromerose_fields(h, w, s)
    gate = _sstep(0.45, 0.52, pool) * (1 - _sstep(0.66, 0.74, pool))
    M = 145 + 65 * web + 35 * swirl * hammer
    R = 42 + 58 * (1 - web) * swirl + 30 * (1 - hammer)
    Cc = 24 + 205 * web * gate + 45 * gate * hammer
    return np.clip(M, 0, 255).astype(np.float32), np.clip(R, 0, 255).astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 9. PRIZM COPPER FLAME
# Engraved fire: banknote hatching whose line weight follows licking flame tongues
# — polished copper body, teal heat-patina pooling in the burnt valleys.
@_memo
def _pz_copperflame_fields(h, w, s):
    yy, xx = _coords(h, w)
    wy, wx = _warp(yy, xx, h, w, s ^ 0xF1, 60 * _sr(h, w))
    flame = _n01(np.sin(wx * 0.018) + np.cos(wy * 0.013) + 2 * _noise(h, w, s ^ 0x3F, (30, 90, 220)))
    ink = _engrave(h, w, flame, s, pitch=4.6, curl=26, sharp=5.0)
    edge = np.abs(flame - _gauss(flame, 5)) * 8.0
    return flame, ink, np.clip(edge, 0, 1)


def _pz_copperflame_paint(h, w, s):
    flame, ink, edge = _pz_copperflame_fields(h, w, s)
    copper = _ramp([(0.30, 0.10, 0.05), (0.78, 0.38, 0.18), (1.0, 0.72, 0.42)], flame, flatten_lightness=0.40)
    patina = _ramp([(0.05, 0.30, 0.30), (0.10, 0.55, 0.52), (0.45, 0.85, 0.75)], 1.0 - flame, flatten_lightness=0.55)
    body = copper * (1 - 0.42 * ink[..., None]) + patina * (0.30 * (1 - flame) * ink)[..., None]
    body += np.float32([1.0, 0.75, 0.45])[None, None, :] * (edge * 0.30)[..., None]
    return _polish(body, h, w, s)


def _pz_copperflame_spec(h, w, s):
    flame, ink, edge = _pz_copperflame_fields(h, w, s)
    gate = _sstep(0.48, 0.55, flame) * (1 - _sstep(0.68, 0.76, flame))
    M = 80 + 110 * (1 - ink) * flame + 50 * gate * edge
    R = np.clip(70 + 120 * ink - 45 * gate + 25 * (1 - flame), 0, 255)
    Cc = 22 + 190 * edge * gate + 40 * (1 - ink) * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 10. PRIZM COSMOS
# A living galaxy: strange-attractor spiral arms of star-stuff, thousands of
# pin-stars, rose/indigo nebula breathing between the arms.
@_memo
def _pz_cosmos_fields(h, w, s):
    arms = np.maximum(_attractor(h, w, s, kind="clifford", span=2.0, sigma=0.02),
                      _attractor(h, w, s + 31, kind="dejong", span=1.7, sigma=0.03) * 0.8)
    arms = np.clip(arms * 2.2, 0, 1)
    sky = np.clip(_stars(h, w, s ^ 0x5C, n=30000, bright_frac=0.006), 0, 0.55) * 1.4
    neb = _noise(h, w, s ^ 0xB7, (50, 130, 320))
    return arms, sky, neb


def _pz_cosmos_paint(h, w, s):
    arms, sky, neb = _pz_cosmos_fields(h, w, s)
    nebula = _ramp([(0.06, 0.04, 0.16), (0.22, 0.10, 0.38), (0.55, 0.20, 0.42), (0.30, 0.34, 0.62)],
                   neb, flatten_lightness=0.66)
    starlight = _ramp([(0.95, 0.75, 0.45), (1.0, 0.95, 0.85), (0.70, 0.80, 1.0)], _noise(h, w, s ^ 0x21, (90, 240)))
    body = nebula * (0.55 + 0.45 * arms[..., None]) + starlight * (arms ** 1.3)[..., None] * 0.85
    body += np.float32([0.92, 0.95, 1.0])[None, None, :] * sky[..., None] * 0.9
    return _polish(body, h, w, s)


def _pz_cosmos_spec(h, w, s):
    arms, sky, neb = _pz_cosmos_fields(h, w, s)
    gate = _sstep(0.44, 0.52, neb) * (1 - _sstep(0.64, 0.72, neb))
    M = 35 + 165 * arms + 50 * sky
    R = np.clip(200 - 150 * arms - 70 * sky + 28 * _microtex(h, w, s ^ 3), 0, 255)
    Cc = 18 + 215 * sky + 120 * arms * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 11. PRIZM DARK MATTER
# Gravitational lensing: a brilliant caustic light-web warped around pitch-black
# void cores, each void rimmed in violet Cherenkov glow.
@_memo
def _pz_darkmatter_fields(h, w, s):
    web = np.clip(_caustics(h, w, s, strength=38, scale=30, sharp=1.1) * 2.6, 0, 1)
    voidf = _noise(h, w, s ^ 0xD4, (10, 26))
    voids = _sstep(0.62, 0.78, voidf)
    rim = np.clip(_sstep(0.55, 0.66, voidf) - voids, 0, 1)
    return web, voids, rim


def _pz_darkmatter_paint(h, w, s):
    web, voids, rim = _pz_darkmatter_fields(h, w, s)
    light = _ramp([(0.10, 0.12, 0.22), (0.35, 0.42, 0.60), (0.85, 0.92, 1.0)], web, flatten_lightness=0.45)
    body = light * (1 - 0.78 * voids[..., None])
    body += _ramp([(0.30, 0.05, 0.55), (0.62, 0.25, 0.95), (0.85, 0.60, 1.0)], rim)[...] * (rim * 0.85)[..., None]
    return _polish(body, h, w, s, grain=0.07)


def _pz_darkmatter_spec(h, w, s):
    web, voids, rim = _pz_darkmatter_fields(h, w, s)
    gate = _sstep(0.30, 0.40, web) * (1 - _sstep(0.62, 0.72, web))
    M = 40 + 150 * web * (1 - voids) + 60 * rim
    R = np.clip(60 + 160 * voids + 30 * _microtex(h, w, s ^ 8) - 40 * web, 0, 255)
    Cc = 20 + 200 * rim + 90 * web * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 12. PRIZM DEEP SPACE
# Long-exposure sky: thousands of concentric star-trail arcs sweeping around an
# unseen celestial pole, gold/blue/white trails over cosmic dust.
@_memo
def _pz_deepspace_fields(h, w, s):
    rng = _rng(s, 77)
    cy, cx = rng.uniform(-0.6, 1.6) * h, rng.uniform(-0.6, 1.6) * w
    polys, cols = [], []
    n_tr = 1500
    rr = np.sqrt(rng.uniform(0.02, 1.0, n_tr)) * 1.6 * max(h, w)
    a0 = rng.uniform(0, 2 * np.pi, n_tr)
    alen = rng.uniform(0.05, 0.55, n_tr)
    for i in range(n_tr):
        aa = np.linspace(a0[i], a0[i] + alen[i], max(4, int(alen[i] * rr[i] / 7)))
        polys.append(np.stack([cx + np.cos(aa) * rr[i], cy + np.sin(aa) * rr[i]], -1))
        cols.append(rng.random())
    trails = _curves(h, w, polys, thick=1)
    heads = np.zeros((h, w), np.float32)
    hx = np.clip((cx + np.cos(a0 + alen) * rr).astype(np.int32), 0, w - 1)
    hy = np.clip((cy + np.sin(a0 + alen) * rr).astype(np.int32), 0, h - 1)
    np.add.at(heads, (hy, hx), 1.0)
    heads = np.clip(_gauss(heads, 1.4) * 5.0, 0, 1)
    dust = _noise(h, w, s ^ 0x88, (40, 110, 260))
    return trails, heads, dust


def _pz_deepspace_paint(h, w, s):
    trails, heads, dust = _pz_deepspace_fields(h, w, s)
    sky = _ramp([(0.02, 0.03, 0.08), (0.07, 0.07, 0.16), (0.16, 0.10, 0.22)], dust, flatten_lightness=0.35)
    trailc = _ramp([(1.0, 0.85, 0.55), (0.95, 0.95, 0.95), (0.55, 0.75, 1.0)], _noise(h, w, s ^ 0x44, (60, 150)))
    body = sky + trailc * trails[..., None] * 0.9 + np.float32([1.0, 0.98, 0.9]) * heads[..., None]
    return _polish(body, h, w, s, grain=0.08)


def _pz_deepspace_spec(h, w, s):
    trails, heads, dust = _pz_deepspace_fields(h, w, s)
    gate = _sstep(0.45, 0.52, dust) * (1 - _sstep(0.66, 0.74, dust))
    M = 30 + 175 * trails + 60 * heads
    R = np.clip(195 - 150 * trails + 30 * _microtex(h, w, s ^ 5) - 60 * heads, 0, 255)
    Cc = 18 + 220 * heads + 110 * trails * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 13. PRIZM DUOCHROME
# True duochrome twill: a fine herringbone weave where every warp thread is teal
# and every weft thread magenta — the flip IS the fabric.
@_memo
def _pz_duochrome_fields(h, w, s):
    yy, xx = _coords(h, w)
    rng = _rng(s, 13)
    a = float(rng.uniform(0, np.pi))
    u = xx * np.cos(a) + yy * np.sin(a)
    v = -xx * np.sin(a) + yy * np.cos(a)
    p = 7.0 * _sr(h, w)
    band = np.floor(v / (p * 9)).astype(np.int32) % 2          # herringbone chevron flip
    uu = np.where(band == 0, u, -u)
    warp = (0.5 + 0.5 * np.sin(uu * (2 * np.pi / p))).astype(np.float32)
    weft = (0.5 + 0.5 * np.sin((v + 0.5 * p) * (2 * np.pi / p))).astype(np.float32)
    over = ((np.floor(uu / p) + np.floor(v / p)) % 2).astype(np.float32)   # over-under
    sheen = _noise(h, w, s ^ 0x77, (90, 240))
    return warp, weft, over, sheen


def _pz_duochrome_paint(h, w, s):
    warp, weft, over, sheen = _pz_duochrome_fields(h, w, s)
    teal = _ramp([(0.02, 0.30, 0.34), (0.05, 0.62, 0.66), (0.55, 0.95, 0.92)], warp, flatten_lightness=0.30)
    mage = _ramp([(0.30, 0.02, 0.26), (0.70, 0.08, 0.55), (0.98, 0.50, 0.85)], weft, flatten_lightness=0.30)
    body = teal * over[..., None] + mage * (1 - over[..., None])
    body *= (0.80 + 0.20 * sheen[..., None])
    return _polish(body, h, w, s)


def _pz_duochrome_spec(h, w, s):
    warp, weft, over, sheen = _pz_duochrome_fields(h, w, s)
    gate = _sstep(0.46, 0.54, sheen) * (1 - _sstep(0.66, 0.74, sheen))
    M = 60 + 110 * over * warp + 55 * gate * over
    R = np.clip(70 + 110 * (1 - over) * weft + 30 * _microtex(h, w, s ^ 6) - 30 * gate, 0, 255)
    Cc = 24 + 180 * over * gate * warp + 60 * (1 - over) * gate * weft
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 14. PRIZM EMBER
# Dying campfire crust: charred plates split by a glowing crack network breathing
# orange→white heat, spark streaks drifting off the hottest seams.
@_memo
def _pz_ember_fields(h, w, s):
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=2300, aniso=1.5, res=0.5)
    cracks = 1.0 - _sstep(0.04, 0.12, edge)
    heat = _gauss(cracks, 2) * _noise(h, w, s ^ 0xE3, (26, 70))
    char = _noise(h, w, s ^ 0x31, (2, 5, 11))
    th = _flow_theta(h, w, s ^ 0x91, scale=160, turns=1.2)
    sparks = _flowlines(h, w, s ^ 0x55, n=420, steps=26, step_len=2.4, theta=th, thick=1, fade=True)
    return cracks, heat, char, sparks


def _pz_ember_paint(h, w, s):
    cracks, heat, char, sparks = _pz_ember_fields(h, w, s)
    crust = _ramp([(0.08, 0.06, 0.06), (0.14, 0.11, 0.11), (0.22, 0.18, 0.17)], char, flatten_lightness=0.20)
    glow = _ramp([(0.45, 0.05, 0.01), (0.90, 0.32, 0.05), (1.0, 0.72, 0.28), (1.0, 0.88, 0.55)],
                 np.clip(heat * 1.2, 0, 1))
    body = crust * (1 - cracks[..., None]) + glow * cracks[..., None]
    body += np.float32([1.0, 0.72, 0.30])[None, None, :] * sparks[..., None] * 0.8
    return _polish(body, h, w, s, grain=0.08)


def _pz_ember_spec(h, w, s):
    cracks, heat, char, sparks = _pz_ember_fields(h, w, s)
    gate = _sstep(0.40, 0.50, heat) * (1 - _sstep(0.66, 0.76, heat))
    M = 30 + 170 * cracks * heat + 60 * sparks
    R = np.clip(185 - 120 * cracks + 45 * char - 40 * gate, 0, 255)
    Cc = 20 + 200 * cracks * gate + 90 * sparks
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 15. PRIZM FIRE & ICE
# Two rivers interleaved: warm currents flowing one way, glacial currents the
# other, woven through alternating bands — frost sparkle where they touch.
@_memo
def _pz_fireice_fields(h, w, s):
    rng = _rng(s, 19)
    a = float(rng.uniform(0, np.pi))
    thA = (a + (_noise(h, w, s ^ 0xF1, (70, 190)) - 0.5) * 1.2).astype(np.float32)
    thB = (a + np.pi / 2 + (_noise(h, w, s ^ 0x1F, (70, 190)) - 0.5) * 1.2).astype(np.float32)
    fire = _flowlines(h, w, s, n=1700, steps=55, step_len=2.4, theta=thA, thick=1, glow=2, fade=True)
    ice = _flowlines(h, w, s ^ 0x77, n=1700, steps=55, step_len=2.4, theta=thB, thick=1, glow=2, fade=True)
    yy, xx = _coords(h, w)
    bands = (0.5 + 0.5 * np.sin((xx * np.cos(a + np.pi / 4) + yy * np.sin(a + np.pi / 4)) * (2 * np.pi / (24 * _sr(h, w))) + _noise(h, w, s ^ 0x3, (120, 300)) * 5)).astype(np.float32)
    parity = _sstep(0.42, 0.58, bands)
    contact = np.clip(1 - np.abs(bands - 0.5) * 5, 0, 1)
    frost = _flakes(h, w, s ^ 0xAB, density=0.10) * contact
    return fire, ice, parity, frost


def _pz_fireice_paint(h, w, s):
    fire, ice, parity, frost = _pz_fireice_fields(h, w, s)
    fireC = _ramp([(0.20, 0.02, 0.01), (0.85, 0.25, 0.03), (1.0, 0.72, 0.25)], fire, flatten_lightness=0.25)
    iceC = _ramp([(0.02, 0.10, 0.22), (0.15, 0.50, 0.80), (0.80, 0.97, 1.0)], ice, flatten_lightness=0.25)
    base = _ramp([(0.07, 0.05, 0.07), (0.10, 0.07, 0.10)], parity, flatten_lightness=0.0)
    body = base + fireC * (fire * parity)[..., None] + iceC * (ice * (1 - parity))[..., None]
    body += np.float32([0.9, 0.97, 1.0])[None, None, :] * frost[..., None] * 0.55
    return _polish(body, h, w, s, grain=0.08)


def _pz_fireice_spec(h, w, s):
    fire, ice, parity, frost = _pz_fireice_fields(h, w, s)
    M = 40 + 130 * fire * parity + 130 * ice * (1 - parity)
    R = np.clip(190 - 120 * fire * parity - 150 * ice * (1 - parity) + 30 * _microtex(h, w, s ^ 4), 0, 255)
    Cc = 20 + 200 * frost + 90 * ice * (1 - parity)        # ignition: the ICE flashes, fire stays warm
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 16. PRIZM GALAXY DUST
# Golden-angle stardust: phyllotaxis spirals of micro-spangles at three nested
# scales, drifting violet dust lanes between the seed-spirals.
@_memo
def _pz_galaxydust_fields(h, w, s):
    rng = _rng(s, 23)
    pins = np.zeros((h, w), np.float32)
    ga = np.pi * (3.0 - np.sqrt(5.0))
    for layer, (n, spread) in enumerate(((2600, 1.25), (6400, 0.85), (15000, 0.55))):
        k = np.arange(1, n + 1, dtype=np.float32)
        r = np.sqrt(k / n) * spread * max(h, w)
        th = k * ga + rng.uniform(0, 2 * np.pi)
        cy, cx = rng.uniform(0.2, 0.8) * h, rng.uniform(0.2, 0.8) * w
        px = cx + np.cos(th) * r; py = cy + np.sin(th) * r
        ok = (px >= 0) & (px < w) & (py >= 0) & (py < h)
        np.add.at(pins, (py[ok].astype(np.int32), px[ok].astype(np.int32)), 0.9 - 0.18 * layer)
    pins = np.clip(_gauss(pins, 0.9) * 4.0, 0, 1)
    lanes = _noise(h, w, s ^ 0x6D, (70, 180, 400))
    return pins, lanes


def _pz_galaxydust_paint(h, w, s):
    pins, lanes = _pz_galaxydust_fields(h, w, s)
    dust = _ramp([(0.10, 0.05, 0.18), (0.26, 0.12, 0.36), (0.16, 0.20, 0.45)], lanes, flatten_lightness=0.45)
    spark = _ramp([(1.0, 0.85, 0.55), (0.92, 0.92, 1.0), (0.75, 0.60, 1.0)], _noise(h, w, s ^ 0x9C, (50, 130)))
    body = dust * (0.7 + 0.3 * (1 - pins)[..., None]) + spark * pins[..., None] * 0.95
    return _polish(body, h, w, s, grain=0.08)


def _pz_galaxydust_spec(h, w, s):
    pins, lanes = _pz_galaxydust_fields(h, w, s)
    gate = _sstep(0.44, 0.52, lanes) * (1 - _sstep(0.64, 0.72, lanes))
    M = 40 + 175 * pins
    R = np.clip(190 - 145 * pins + 30 * _microtex(h, w, s ^ 2), 0, 255)
    Cc = 20 + 215 * pins * (0.4 + 0.6 * gate)
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 17. PRIZM HOLOGRAPHIC
# Holo trading-foil: a mosaic of micro-prism tiles, each etched with a hairline
# diffraction grating at its own angle — every tile refracts its own rainbow.
@_memo
def _pz_holo_fields(h, w, s):
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=1900, aniso=1.25, res=0.5)
    per = _n01(np.sin(cid * 12.9898) + 1.0)
    yy, xx = _coords(h, w)
    ang = per * np.pi
    p = 3.6 * _sr(h, w)
    grat = (0.5 + 0.5 * np.sin((xx * np.cos(ang) + yy * np.sin(ang)) * (2 * np.pi / p))).astype(np.float32)
    seam = 1.0 - _sstep(0.03, 0.10, edge)
    return per, grat, seam


def _pz_holo_paint(h, w, s):
    per, grat, seam = _pz_holo_fields(h, w, s)
    rainbow = _ramp([(1.0, 0.12, 0.22), (1.0, 0.62, 0.02), (1.0, 0.95, 0.05),
                     (0.05, 0.95, 0.45), (0.05, 0.55, 1.0), (0.65, 0.18, 1.0)],
                    per, flatten_lightness=0.45)
    silver = 0.58 + 0.40 * grat
    body = rainbow * silver[..., None]
    body *= (1 - 0.5 * seam[..., None])
    return _polish(body, h, w, s)


def _pz_holo_spec(h, w, s):
    per, grat, seam = _pz_holo_fields(h, w, s)
    gate = _sstep(0.38, 0.46, per) * (1 - _sstep(0.56, 0.64, per))
    M = 90 + 100 * grat + 45 * gate
    R = np.clip(55 + 90 * seam + 40 * (1 - grat) - 30 * gate, 0, 255)
    Cc = 26 + 200 * gate * grat + 30 * grat
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 18. PRIZM IRIDESCENT
# Draining soap film: swirling thin-film bands with drain streaks and black film
# holes — pale pearl base so the interference travel glows.
@_memo
def _pz_irid_fields(h, w, s):
    rng = _rng(s, 29)
    thick = _noise(h, w, s ^ 0x1D, (24, 60, 135))
    streak = _dirblur(_noise(h, w, s ^ 0xD1, (3, 8)), float(rng.uniform(0, np.pi)), int(40 * _sr(h, w)))
    thick = _n01(thick + 0.35 * streak)
    holes = _sstep(0.88, 0.95, _noise(h, w, s ^ 0x4A, (30, 75)))
    return thick, streak, holes


def _pz_irid_paint(h, w, s):
    thick, streak, holes = _pz_irid_fields(h, w, s)
    film = _ipal(thick, 5.2, 0.9, np.float32([0.72, 0.74, 0.78]))
    body = film * (0.84 + 0.16 * streak[..., None])
    body *= (1 - 0.85 * holes[..., None])
    return _polish(body, h, w, s)


def _pz_irid_spec(h, w, s):
    thick, streak, holes = _pz_irid_fields(h, w, s)
    bandv = np.abs(np.cos(thick * np.pi * 6.0))
    gate = _sstep(0.42, 0.50, thick) * (1 - _sstep(0.62, 0.70, thick))
    M = 70 + 120 * bandv + 40 * gate
    R = np.clip(50 + 70 * streak + 120 * holes - 30 * gate, 0, 255)
    Cc = 24 + 190 * bandv * gate + 60 * (1 - holes) * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 19. PRIZM MIDNIGHT
# Nocturne sea: deep indigo swells crossed by hairline moon-silver engraving that
# follows the water, rare glints riding the crests.
@_memo
def _pz_midnight_fields(h, w, s):
    swell = _noise(h, w, s ^ 0x2E, (60, 150, 360))
    th = _flow_theta(h, w, s ^ 0x8B, scale=200, turns=0.8)
    ink = _engrave(h, w, _n01(swell + 0.2 * _noise(h, w, s ^ 0x5, (20, 50))), s, pitch=4.2, curl=34, sharp=4.5,
                   angle=float(_rng(s, 7).uniform(0, np.pi)))
    glint = _flakes(h, w, s ^ 0x99, density=0.05, bright=0.9) * _sstep(0.55, 0.8, swell)
    return swell, ink, glint


def _pz_midnight_paint(h, w, s):
    swell, ink, glint = _pz_midnight_fields(h, w, s)
    sea = _ramp([(0.03, 0.04, 0.12), (0.07, 0.09, 0.24), (0.13, 0.16, 0.38)], swell, flatten_lightness=0.30)
    silver = np.float32([0.80, 0.86, 1.0])[None, None, :]
    body = sea + silver * (ink * 0.42)[..., None] + silver * glint[..., None] * 0.8
    return _polish(body, h, w, s, grain=0.075)


def _pz_midnight_spec(h, w, s):
    swell, ink, glint = _pz_midnight_fields(h, w, s)
    gate = _sstep(0.50, 0.58, swell) * (1 - _sstep(0.70, 0.78, swell))
    M = 45 + 150 * ink + 55 * glint
    R = np.clip(170 - 110 * ink + 35 * _microtex(h, w, s ^ 4) - 40 * gate, 0, 255)
    Cc = 20 + 210 * glint + 110 * ink * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 20. PRIZM MYSTICHROME
# Liquid color-travel chrome: the classic teal→violet→magenta→gold sweep with
# molten metal flow-streaks combed ALONG the travel gradient.
@_memo
def _pz_mystichrome_fields(h, w, s):
    travel = _noise(h, w, s ^ 0x6A, (90, 220, 460))
    gy, gx = np.gradient(_gauss(travel, 8))
    th = np.arctan2(gy, gx).astype(np.float32) + np.pi / 2     # along iso-travel lines
    streaks = _flowlines(h, w, s, n=3300, steps=42, step_len=2.2, theta=th, thick=1, glow=1.2)
    comb = _dirblur(_noise(h, w, s ^ 0xC2, (2, 5)), 0.0, 5)
    return travel, streaks, comb


def _pz_mystichrome_paint(h, w, s):
    travel, streaks, comb = _pz_mystichrome_fields(h, w, s)
    chrome = _ramp([(0.02, 0.32, 0.36), (0.16, 0.16, 0.48), (0.55, 0.12, 0.50), (0.85, 0.55, 0.20)],
                   travel, flatten_lightness=0.78)
    body = chrome * (0.66 + 0.34 * comb[..., None])
    body += chrome * streaks[..., None] * 0.50 + streaks[..., None] * 0.14
    return _polish(body, h, w, s)


def _pz_mystichrome_spec(h, w, s):
    travel, streaks, comb = _pz_mystichrome_fields(h, w, s)
    gate = _sstep(0.46, 0.53, travel) * (1 - _sstep(0.64, 0.72, travel))
    M = 110 + 90 * streaks + 40 * gate
    R = np.clip(50 + 60 * (1 - streaks) * comb + 26 * _microtex(h, w, s ^ 7) - 30 * gate, 0, 255)
    Cc = 26 + 195 * streaks * gate + 45 * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 21. PRIZM NEON
# Buzzing neon alley: glowing glass-tube script loops (white-hot cores, colored
# halos) over a dark micro-brick wall.
@_memo
def _pz_neon_fields(h, w, s):
    tubes = np.maximum(_harmonograph(h, w, s, cells=26, pens=1, m=560, thick=1, jitter=0.4),
                       _harmonograph(h, w, s ^ 0x77, cells=44, pens=1, m=380, thick=1, jitter=0.4) * 0.9)
    hue = _noise(h, w, s ^ 0x4E, (160, 380))
    yy, xx = _coords(h, w)
    p = 9 * _sr(h, w)
    brick = (0.5 + 0.5 * np.sin(yy * (2 * np.pi / p))) * (0.5 + 0.5 * np.sin((xx + np.floor(yy / p) % 2 * p * 1.5) * (2 * np.pi / (p * 3))))
    return tubes, hue, brick.astype(np.float32)


def _pz_neon_paint(h, w, s):
    tubes, hue, brick = _pz_neon_fields(h, w, s)
    glow = _gauss(tubes, 3)
    neonc = _ramp([(1.0, 0.15, 0.35), (1.0, 0.45, 0.05), (0.15, 1.0, 0.55), (0.10, 0.65, 1.0), (0.80, 0.25, 1.0)],
                  hue, flatten_lightness=0.55)
    wall = np.float32([0.09, 0.09, 0.12])[None, None, :] * (0.5 + 0.9 * brick[..., None])
    body = wall + neonc * (glow * 0.55)[..., None] + np.float32([1, 1, 1]) * (tubes ** 1.5)[..., None] * 0.85
    return _polish(body, h, w, s, grain=0.075)


def _pz_neon_spec(h, w, s):
    tubes, hue, brick = _pz_neon_fields(h, w, s)
    glow = _gauss(tubes, 5)
    gate = _sstep(0.42, 0.50, hue) * (1 - _sstep(0.62, 0.70, hue))
    M = 35 + 180 * tubes + 40 * glow
    R = np.clip(190 - 140 * glow + 35 * brick * (1 - glow), 0, 255)
    Cc = 18 + 215 * tubes * (0.45 + 0.55 * gate)
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 22. PRIZM OCEANIC
# Sunlit reef floor: true refraction caustics dancing over turquoise→abyss depth,
# micro-foam flecks riding the bright web.
@_memo
def _pz_oceanic_fields(h, w, s):
    web = np.clip(_caustics(h, w, s, strength=40, scale=95, sharp=1.0, grid_mul=1.5) * 2.4, 0, 1)
    depthf = _noise(h, w, s ^ 0x0C, (180, 420))
    foam = _flakes(h, w, s ^ 0xF0, density=0.12) * _sstep(0.25, 0.6, web)
    ripple = _noise(h, w, s ^ 0x77, (2.5, 6))
    return web, depthf, foam, ripple


def _pz_oceanic_paint(h, w, s):
    web, depthf, foam, ripple = _pz_oceanic_fields(h, w, s)
    water = _ramp([(0.01, 0.10, 0.18), (0.02, 0.28, 0.40), (0.10, 0.55, 0.62), (0.45, 0.88, 0.85)],
                  np.clip(0.20 + 0.42 * depthf + 0.45 * web, 0, 1), flatten_lightness=0.30)
    body = water * (0.72 + 0.28 * ripple[..., None])
    body += np.float32([0.85, 1.0, 0.98])[None, None, :] * (web ** 1.6)[..., None] * 0.45
    body += foam[..., None] * 0.5
    return _polish(body, h, w, s)


def _pz_oceanic_spec(h, w, s):
    web, depthf, foam, ripple = _pz_oceanic_fields(h, w, s)
    gate = _sstep(0.44, 0.52, depthf) * (1 - _sstep(0.66, 0.74, depthf))
    M = 60 + 140 * web + 40 * foam
    R = np.clip(80 + 70 * (1 - web) + 40 * ripple - 50 * gate * web, 0, 255)
    Cc = 22 + 205 * web * gate + 80 * foam
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 23. PRIZM PHOENIX
# Rising firebird plumage: long arcing plume strands with fine barb hatching,
# ember-red roots burning to white-gold tips, spark dust shed along the way.
@_memo
def _pz_phoenix_fields(h, w, s):
    rng = _rng(s, 37)
    a = float(rng.uniform(0, np.pi))
    th = (a + (_noise(h, w, s ^ 0xFE, (110, 280)) - 0.5) * 2.4).astype(np.float32)
    plume = _flowlines(h, w, s, n=2800, steps=68, step_len=2.5, theta=th, thick=1, glow=2, fade=True)
    barbs = _engrave(h, w, _gauss(plume, 4), s ^ 0x12, pitch=3.8, curl=18, sharp=4.0, angle=a + np.pi / 3)
    heat = _gauss(plume, 6)
    sparks = _flakes(h, w, s ^ 0x21, density=0.05, bright=0.9)
    return plume, barbs, heat, sparks


def _pz_phoenix_paint(h, w, s):
    plume, barbs, heat, sparks = _pz_phoenix_fields(h, w, s)
    fire = _ramp([(0.28, 0.02, 0.02), (0.75, 0.12, 0.02), (1.0, 0.55, 0.10), (1.0, 0.92, 0.55)],
                 np.clip(plume * 0.85 + heat * 0.18, 0, 1), flatten_lightness=0.42)
    body = fire * (0.62 + 0.38 * barbs[..., None])
    body += np.float32([1.0, 0.85, 0.45])[None, None, :] * sparks[..., None] * 0.5
    return _polish(body, h, w, s, grain=0.075)


def _pz_phoenix_spec(h, w, s):
    plume, barbs, heat, sparks = _pz_phoenix_fields(h, w, s)
    gate = _sstep(0.40, 0.48, heat) * (1 - _sstep(0.62, 0.70, heat))
    M = 40 + 160 * plume + 50 * sparks
    R = np.clip(180 - 120 * plume + 50 * barbs * (1 - plume) - 40 * gate, 0, 255)
    Cc = 20 + 200 * plume * gate + 90 * sparks
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 24. PRIZM SOLAR
# The photosphere: boiling granulation cells, sunspot pores with filament
# penumbrae, white-hot magnetic loop arcs leaping between active regions.
@_memo
def _pz_solar_fields(h, w, s):
    gran = _gray_scott(h, w, s, "mitosis", iters=330, grid=448, seeds=30, fine=0.40, speckle=0.14)
    spots = _sstep(0.78, 0.84, _noise(h, w, s ^ 0x50, (80, 190)))
    pen = np.clip(_sstep(0.62, 0.74, _noise(h, w, s ^ 0x50, (80, 190))) - spots, 0, 1)
    rng = _rng(s, 41)
    polys = []
    for _ in range(26):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(28, 110) * _sr(h, w)
        a0 = rng.uniform(0, 2 * np.pi); al = rng.uniform(0.6, 2.2)
        aa = np.linspace(a0, a0 + al, 26)
        polys.append(np.stack([cx + np.cos(aa) * r, cy + np.sin(aa) * r * rng.uniform(0.4, 1.0)], -1))
    loops = _curves(h, w, polys, thick=1, glow=2.5)
    return gran, spots, pen, loops


def _pz_solar_paint(h, w, s):
    gran, spots, pen, loops = _pz_solar_fields(h, w, s)
    surf = _ramp([(1.0, 0.55, 0.08), (1.0, 0.78, 0.25), (1.0, 0.95, 0.62)], gran, flatten_lightness=0.22)
    body = surf * (1 - 0.55 * spots[..., None]) * (1 - 0.25 * pen[..., None])
    body += np.float32([1.0, 0.98, 0.88])[None, None, :] * loops[..., None] * 0.75
    return _polish(body, h, w, s)


def _pz_solar_spec(h, w, s):
    gran, spots, pen, loops = _pz_solar_fields(h, w, s)
    gate = _sstep(0.42, 0.50, gran) * (1 - _sstep(0.62, 0.70, gran))
    M = 70 + 110 * gran + 70 * loops
    R = np.clip(70 + 140 * spots + 60 * pen - 40 * gate, 0, 255)
    Cc = 24 + 200 * loops + 70 * gran * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 25. PRIZM SPECTRUM
# Laser-etched spectrum guilloche: a dense scatter of fine engine-turn rosettes,
# each refracting its own slice of the rainbow by position phase.
@_memo
def _pz_spectrum_fields(h, w, s):
    turn = np.maximum(_harmonograph(h, w, s, cells=34, pens=1, m=440, thick=1, jitter=0.34),
                      _harmonograph(h, w, s ^ 0x31, cells=58, pens=1, m=300, thick=1, jitter=0.34) * 0.8)
    phase = _noise(h, w, s ^ 0x5B, (120, 300, 640))
    flake = _flakes(h, w, s ^ 0x90, density=0.22, bright=0.85)
    return turn, phase, flake


def _pz_spectrum_paint(h, w, s):
    turn, phase, flake = _pz_spectrum_fields(h, w, s)
    rainbow = _ramp([(0.95, 0.15, 0.20), (1.0, 0.60, 0.08), (0.95, 0.90, 0.15),
                     (0.15, 0.88, 0.45), (0.12, 0.50, 0.96), (0.58, 0.20, 0.92)],
                    phase, flatten_lightness=0.66)
    bed = np.float32([0.21, 0.21, 0.24])[None, None, :] * (0.8 + 0.4 * _microtex(h, w, s)[..., None])
    body = bed + rainbow * (turn * 0.9 + flake * 0.5)[..., None]
    return _polish(body, h, w, s)


def _pz_spectrum_spec(h, w, s):
    turn, phase, flake = _pz_spectrum_fields(h, w, s)
    gate = _sstep(0.42, 0.50, phase) * (1 - _sstep(0.62, 0.70, phase))
    M = 60 + 140 * turn + 45 * flake
    R = np.clip(60 - 30 * turn + 40 * _microtex(h, w, s ^ 6) + 90 * (1 - turn) * (1 - flake), 0, 255)
    Cc = 24 + 190 * turn * gate + 110 * flake * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 26. PRIZM SUNSET STRIP
# Retro-chrome dusk: warm gradient cells swept by mirror chrome bands at scattered
# angles, micro scanline shimmer everywhere — 80s boulevard chrome.
@_memo
def _pz_sunsetstrip_fields(h, w, s):
    rng = _rng(s, 43)
    yy, xx = _coords(h, w)
    bands = np.zeros((h, w), np.float32)
    for _ in range(5):
        a = rng.uniform(0, np.pi)
        p = rng.uniform(13, 32) * _sr(h, w)
        ph = rng.uniform(0, 2 * np.pi)
        bands += np.sin((xx * np.cos(a) + yy * np.sin(a)) * (2 * np.pi / p) + ph + _noise(h, w, s ^ int(a * 99), (200, 500)) * 4)
    bands = _sstep(0.55, 0.75, _n01(bands))
    dusk = _noise(h, w, s ^ 0x5D, (160, 380))
    scan = (0.5 + 0.5 * np.sin((xx * np.cos(0.7) + yy * np.sin(0.7)) * (2 * np.pi / (3.2 * _sr(h, w))))).astype(np.float32)
    return bands, dusk, scan


def _pz_sunsetstrip_paint(h, w, s):
    bands, dusk, scan = _pz_sunsetstrip_fields(h, w, s)
    sky = _ramp([(0.95, 0.30, 0.45), (1.0, 0.55, 0.20), (0.55, 0.20, 0.55), (0.20, 0.12, 0.45)],
                dusk, flatten_lightness=0.45)
    chrome = _ramp([(0.35, 0.32, 0.40), (0.85, 0.85, 0.95), (1.0, 0.98, 0.92)], _gauss(bands, 1.2), flatten_lightness=0.30)
    body = sky * (1 - bands[..., None]) + chrome * bands[..., None]
    body *= (0.86 + 0.14 * scan[..., None])
    return _polish(body, h, w, s)


def _pz_sunsetstrip_spec(h, w, s):
    bands, dusk, scan = _pz_sunsetstrip_fields(h, w, s)
    gate = _sstep(0.44, 0.52, dusk) * (1 - _sstep(0.64, 0.72, dusk))
    M = 55 + 150 * bands + 30 * scan * bands
    R = np.clip(150 - 110 * bands + 40 * scan * (1 - bands), 0, 255)
    Cc = 24 + 195 * bands * gate + 40 * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 27. PRIZM TITANIUM
# Torch-anodized titanium: brushed metal grain blooming through the full anodize
# spectrum (straw→bronze→violet→cobalt) around heat zones, grinder arcs biting in.
@_memo
def _pz_titanium_fields(h, w, s):
    rng = _rng(s, 47)
    a = float(rng.uniform(0, np.pi))
    grain = _dirblur(_noise(h, w, s ^ 0x71, (1.4, 2.8)), a, int(22 * _sr(h, w)))
    heat = _noise(h, w, s ^ 0x7E, (150, 360, 760))
    polys = []
    for _ in range(70):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(40, 200) * _sr(h, w)
        a0 = rng.uniform(0, 2 * np.pi); al = rng.uniform(0.25, 0.9)
        aa = np.linspace(a0, a0 + al, 18)
        polys.append(np.stack([cx + np.cos(aa) * r, cy + np.sin(aa) * r], -1))
    arcs = _curves(h, w, polys, thick=1)
    return grain, heat, arcs


def _pz_titanium_paint(h, w, s):
    grain, heat, arcs = _pz_titanium_fields(h, w, s)
    anodize = _ramp([(0.55, 0.50, 0.42), (0.78, 0.62, 0.30), (0.55, 0.28, 0.45),
                     (0.16, 0.22, 0.62), (0.10, 0.45, 0.72)], heat, flatten_lightness=0.40)
    body = anodize * (0.52 + 0.48 * grain[..., None])
    body += np.float32([0.95, 0.95, 1.0])[None, None, :] * arcs[..., None] * 0.30
    return _polish(body, h, w, s)


def _pz_titanium_spec(h, w, s):
    grain, heat, arcs = _pz_titanium_fields(h, w, s)
    gate = _sstep(0.46, 0.54, heat) * (1 - _sstep(0.66, 0.74, heat))
    M = 90 + 90 * grain + 60 * gate
    R = np.clip(60 + 80 * (1 - grain) + 60 * arcs - 35 * gate, 0, 255)
    Cc = 24 + 185 * gate * grain + 70 * arcs
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 28. PRIZM TOXIC WASTE
# Bubbling biohazard sludge: reaction-diffusion foam cells, rim-lit rising
# bubbles, acid drips cutting through the crust — violent green on black.
@_memo
def _pz_toxic_fields(h, w, s):
    foam = _gray_scott(h, w, s, "solitons", iters=380, grid=448, seeds=24, fine=0.38, speckle=0.18)
    sr = _sr(h, w)

    def bubble(dy, dx, rng, i):
        r = rng.uniform(2.5, 11) * sr
        d = np.sqrt(dy * dy + dx * dx) / r
        return np.exp(-((d - 0.85) ** 2) / 0.03) * 0.9 + np.clip(1 - d, 0, 1) * 0.25

    bub = _n01(_splat_points(h, w, s ^ 0xB0, int(700 * sr * sr), bubble, rad=int(12 * sr)))
    rng = _rng(s, 53)
    drip = _dirblur(_sstep(0.80, 0.95, _noise(h, w, s ^ 0xDD, (6, 14))), float(rng.uniform(0, np.pi)), int(60 * sr))
    return foam, bub, np.clip(drip * 2.2, 0, 1)


def _pz_toxic_paint(h, w, s):
    foam, bub, drip = _pz_toxic_fields(h, w, s)
    acid = _ramp([(0.02, 0.07, 0.02), (0.10, 0.35, 0.04), (0.35, 0.85, 0.08), (0.80, 1.0, 0.30)],
                 np.clip(foam * 0.75 + bub * 0.45, 0, 1))
    body = acid + np.float32([0.75, 1.0, 0.25])[None, None, :] * (bub ** 2)[..., None] * 0.5
    body += np.float32([0.55, 0.95, 0.10])[None, None, :] * drip[..., None] * 0.45
    return _polish(body, h, w, s, grain=0.08)


def _pz_toxic_spec(h, w, s):
    foam, bub, drip = _pz_toxic_fields(h, w, s)
    gate = _sstep(0.42, 0.50, foam) * (1 - _sstep(0.64, 0.72, foam))
    M = 35 + 150 * bub + 60 * drip
    R = np.clip(180 - 130 * bub - 60 * drip + 40 * foam, 0, 255)
    Cc = 20 + 200 * bub * gate + 90 * drip
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ---------------------------------------------------------- 29. PRIZM VENOM
# Serpent armor: brick-packed keeled diamond scales, iridescent green-black with
# venom-yellow diamond lattice flashes, every scale ridge catching light.
@_memo
def _pz_venom_fields(h, w, s):
    yy, xx = _coords(h, w)
    rng = _rng(s, 59)
    a = float(rng.uniform(0, np.pi))
    wy, wx = _warp(yy, xx, h, w, s ^ 0x5E, 16 * _sr(h, w))
    u = wx * np.cos(a) + wy * np.sin(a)
    v = -wx * np.sin(a) + wy * np.cos(a)
    pu, pv = 11.0 * _sr(h, w), 15.0 * _sr(h, w)
    row = np.floor(v / pv)
    uo = u + (row % 2) * pu * 0.5
    du = np.abs((uo / pu) - np.floor(uo / pu + 0.5)) * 2     # 0 center -> 1 edge
    dv = np.abs((v / pv) - np.floor(v / pv + 0.5)) * 2
    diamond = np.clip(1 - (du + dv), 0, 1)                    # diamond scale mask
    keel = np.clip(1 - du * 6, 0, 1) * _sstep(0.05, 0.4, diamond)
    cellid = (np.floor(uo / pu) * 31 + np.floor(v / pv) * 17)
    per = _n01(np.sin(cellid * 0.731) + 1)
    return diamond.astype(np.float32), keel.astype(np.float32), per, dv.astype(np.float32)


def _pz_venom_paint(h, w, s):
    diamond, keel, per, dv = _pz_venom_fields(h, w, s)
    scale_c = _ramp([(0.03, 0.08, 0.04), (0.06, 0.22, 0.10), (0.12, 0.45, 0.16)], per, flatten_lightness=0.35)
    venom = np.float32([0.92, 0.95, 0.12])[None, None, :]
    lat = _sstep(0.62, 0.80, per) * _sstep(0.3, 0.7, diamond)
    body = scale_c * (0.55 + 0.45 * diamond[..., None])
    body = body * (1 - lat[..., None] * 0.8) + venom * lat[..., None] * (0.5 + 0.5 * diamond[..., None])
    body += np.float32([0.65, 0.95, 0.55])[None, None, :] * keel[..., None] * 0.45
    return _polish(body, h, w, s, grain=0.08)


def _pz_venom_spec(h, w, s):
    diamond, keel, per, dv = _pz_venom_fields(h, w, s)
    gate = _sstep(0.34, 0.42, per) * (1 - _sstep(0.55, 0.63, per))
    M = 50 + 120 * diamond + 80 * keel
    R = np.clip(190 - 130 * diamond + 40 * (1 - diamond) - 50 * keel, 0, 255)
    Cc = 22 + 205 * keel * (0.4 + 0.6 * gate) + 60 * diamond * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════════════════════════ LET FREEDOM RING — rebuilds
# 2 mono finishes + 6 patterns + 5 spec overlays. Abstract/scattered per the
# UV-orientation rule: no upright flags, no literal geometry.

# ------------------------------------------------- LFR OLD GLORY FLUX (mono)
# The flag as pure energy: scarlet and bone current-ribbons streaming through a
# shared wind, weaving over/under, indigo eddy pools spangled with micro stars.
@_memo
def _lfr_oldglory_fields(h, w, s):
    rng = _rng(s, 61)
    a = float(rng.uniform(0, np.pi))
    th = (a + (_noise(h, w, s ^ 0x06, (90, 230)) - 0.5) * 1.6).astype(np.float32)
    red = _flowlines(h, w, s, n=2100, steps=60, step_len=2.5, theta=th, thick=1, glow=2, fade=True)
    bone = _flowlines(h, w, s ^ 0x44, n=2100, steps=60, step_len=2.5, theta=th, thick=1, glow=2, fade=True)
    yy, xx = _coords(h, w)
    bands = (0.5 + 0.5 * np.sin((xx * np.cos(a + np.pi / 2) + yy * np.sin(a + np.pi / 2)) * (2 * np.pi / (26 * _sr(h, w))) + _noise(h, w, s ^ 0x3B, (130, 320)) * 6)).astype(np.float32)
    parity = _sstep(0.44, 0.56, bands)
    eddy = _sstep(0.55, 0.80, _noise(h, w, s ^ 0xED, (110, 260)))
    spark = _stars(h, w, s ^ 0x57, n=9000, bright_frac=0.02, spikes=False) * eddy
    return red, bone, parity, eddy, spark


def _lfr_oldglory_paint(h, w, s):
    red, bone, parity, eddy, spark = _lfr_oldglory_fields(h, w, s)
    base = _ramp([(0.05, 0.06, 0.16), (0.10, 0.11, 0.28)], eddy, flatten_lightness=0.0)
    redC = _ramp([(0.32, 0.02, 0.06), (0.78, 0.10, 0.14), (1.0, 0.35, 0.30)], red, flatten_lightness=0.25)
    boneC = _ramp([(0.40, 0.38, 0.34), (0.85, 0.83, 0.78), (1.0, 0.99, 0.94)], bone, flatten_lightness=0.25)
    body = base + redC * (red * parity * (1 - eddy * 0.5))[..., None] \
        + boneC * (bone * (1 - parity) * (1 - eddy * 0.5))[..., None]
    body += np.float32([0.85, 0.90, 1.0])[None, None, :] * spark[..., None] * 0.9
    return _polish(body, h, w, s, grain=0.08)


def _lfr_oldglory_spec(h, w, s):
    red, bone, parity, eddy, spark = _lfr_oldglory_fields(h, w, s)
    gate = _sstep(0.46, 0.54, eddy) * (1 - _sstep(0.70, 0.78, eddy))
    M = 40 + 130 * red * parity + 130 * bone * (1 - parity) + 60 * spark
    R = np.clip(185 - 120 * (red * parity + bone * (1 - parity)) + 30 * _microtex(h, w, s ^ 3), 0, 255)
    Cc = 20 + 210 * spark + 90 * bone * (1 - parity) * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ------------------------------------------------- LFR WE THE PEOPLE (mono)
# The parchment itself: dense copperplate engraving flowing like handwriting,
# iron-gall ink on foxed vellum, gold illumination curls catching light.
@_memo
def _lfr_wethepeople_fields(h, w, s):
    rng = _rng(s, 67)
    a = float(rng.uniform(0, np.pi))
    script_tone = _n01(_noise(h, w, s ^ 0x17, (14, 36, 90)) + 0.4 * _noise(h, w, s ^ 0x71, (110, 280)))
    ink = _engrave(h, w, script_tone, s, pitch=3.4, curl=22, sharp=5.5, angle=a)
    ink2 = _engrave(h, w, _n01(1 - script_tone), s ^ 0x2, pitch=5.2, curl=30, sharp=4.0, angle=a + 0.35)
    curls = _harmonograph(h, w, s ^ 0x91, cells=12, pens=1, m=520, thick=1, jitter=0.42, decay=1.4)
    fox = _sstep(0.74, 0.92, _noise(h, w, s ^ 0xF0, (18, 44)))
    vellum = _noise(h, w, s ^ 0x33, (2.5, 6, 14))
    return ink, ink2, curls, fox, vellum


def _lfr_wethepeople_paint(h, w, s):
    ink, ink2, curls, fox, vellum = _lfr_wethepeople_fields(h, w, s)
    parch = _ramp([(0.72, 0.62, 0.42), (0.88, 0.80, 0.60), (0.97, 0.92, 0.76)], vellum, flatten_lightness=0.20)
    gall = np.float32([0.13, 0.09, 0.06])[None, None, :]
    gold = np.float32([1.0, 0.80, 0.30])[None, None, :]
    inkm = np.clip(ink * 0.85 + ink2 * 0.45, 0, 1)
    body = parch * (1 - inkm[..., None] * 0.82) + gall * inkm[..., None] * 0.82
    body = body * (1 - 0.25 * fox[..., None])
    body = body * (1 - curls[..., None] * 0.85) + gold * curls[..., None] * 0.85
    return _polish(body, h, w, s, grain=0.05)


def _lfr_wethepeople_spec(h, w, s):
    ink, ink2, curls, fox, vellum = _lfr_wethepeople_fields(h, w, s)
    gate = _sstep(0.44, 0.52, vellum) * (1 - _sstep(0.64, 0.72, vellum))
    inkm = np.clip(ink * 0.85 + ink2 * 0.45, 0, 1)
    M = 35 + 90 * inkm + 130 * curls
    R = np.clip(140 - 70 * inkm - 90 * curls + 50 * fox + 30 * vellum, 0, 255)
    Cc = 20 + 205 * curls + 70 * inkm * gate
    return np.clip(M, 0, 255).astype(np.float32), R.astype(np.float32), np.clip(Cc, 0, 255).astype(np.float32)


# ════════════════════════════════════════════════════ LFR PATTERNS (alpha stamps)
# Contract: tex(h, w, s) -> float32 0..1 alpha. Native res, fast, dense fine line
# art; colors applied by the pattern route (lo/hi metal ramp).

def _lfrp_bunting_scallop_tex(h, w, s):
    """Layered bunting swags: rows of overlapping scallop fans, each pleated with
    fine radial hatching, scattered at several angles across the canvas."""
    rng = _rng(s, 71)
    sr = _sr(h, w)
    out = np.zeros((h, w), np.float32)
    yy0, xx0 = None, None
    for _layer in range(3):
        a = rng.uniform(0, np.pi)
        polys = []
        n_sw = int(60 * sr * sr) + 8
        for _ in range(n_sw):
            cx, cy = rng.uniform(0, w), rng.uniform(0, h)
            r = rng.uniform(22, 48) * sr
            a0 = a + rng.uniform(-0.3, 0.3)
            # scallop arc
            aa = np.linspace(a0, a0 + np.pi, 30)
            polys.append(np.stack([cx + np.cos(aa) * r, cy + np.sin(aa) * r], -1))
            # pleat hatch: radial lines inside the fan
            for k in range(9):
                ang = a0 + np.pi * (k + 0.5) / 9
                polys.append(np.float32([[cx + np.cos(ang) * r * 0.15, cy + np.sin(ang) * r * 0.15],
                                         [cx + np.cos(ang) * r * 0.92, cy + np.sin(ang) * r * 0.92]]))
            # swag cord
            aa2 = np.linspace(a0, a0 + np.pi, 16)
            sag = np.sin(np.linspace(0, np.pi, 16)) * r * 0.22
            polys.append(np.stack([cx + np.cos(aa2) * (r + 3) + np.cos(a0 + np.pi / 2) * sag,
                                   cy + np.sin(aa2) * (r + 3) + np.sin(a0 + np.pi / 2) * sag], -1))
        out = np.maximum(out, _curves(h, w, polys, thick=max(1, int(sr)), val=1.0 - 0.15 * _layer))
    return np.clip(out, 0, 1)


def _lfrp_firework_radial_tex(h, w, s):
    """Dense peony fireworks: every burst is a full ring of spark rays with dot
    terminals and a strobe ring; sizes nested so the sky is FULL."""
    rng = _rng(s, 73)
    sr = _sr(h, w)
    polys = []
    dots = np.zeros((h, w), np.float32)
    n_b = int(100 * sr * sr) + 16
    for _ in range(n_b):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(14, 60) * sr
        n_ray = int(rng.uniform(18, 34))
        a0 = rng.uniform(0, 2 * np.pi)
        for k in range(n_ray):
            ang = a0 + 2 * np.pi * k / n_ray + rng.normal(0, 0.03)
            r0 = r * rng.uniform(0.12, 0.2)
            r1 = r * rng.uniform(0.82, 1.0)
            # slight droop on the outer half
            mid = np.float32([[cx + np.cos(ang) * r0, cy + np.sin(ang) * r0],
                              [cx + np.cos(ang) * r1 * 0.6, cy + np.sin(ang) * r1 * 0.6],
                              [cx + np.cos(ang) * r1, cy + np.sin(ang) * r1 + r * 0.06]])
            polys.append(mid)
            ix, iy = int(mid[-1, 0]), int(mid[-1, 1])
            if 0 <= ix < w and 0 <= iy < h:
                dots[iy, ix] = 1.0
        # strobe ring
        aa = np.linspace(0, 2 * np.pi, 40)
        rr = r * rng.uniform(0.45, 0.6)
        polys.append(np.stack([cx + np.cos(aa) * rr, cy + np.sin(aa) * rr], -1))
    out = _curves(h, w, polys, thick=1)
    dots = np.clip(_gauss(dots, 1.4 * sr) * 9, 0, 1)
    return np.clip(np.maximum(out, dots), 0, 1)


def _lfrp_ribbon_weave_tex(h, w, s):
    """True over-under satin ribbon lattice: two ribbon families interlaced, each
    ribbon striped with a sheen line and edge shading."""
    rng = _rng(s, 79)
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    a = float(rng.uniform(0, np.pi))
    wy, wx = _warp(yy, xx, h, w, s ^ 0x52, 10 * sr)
    u = wx * np.cos(a) + wy * np.sin(a)
    v = -wx * np.sin(a) + wy * np.cos(a)
    p = 26.0 * sr
    fu = (u / p) - np.floor(u / p)
    fv = (v / p) - np.floor(v / p)
    ribU = (np.abs(fu - 0.5) < 0.26).astype(np.float32)
    ribV = (np.abs(fv - 0.5) < 0.26).astype(np.float32)
    over = ((np.floor(u / p) + np.floor(v / p)) % 2).astype(np.float32)
    lat = np.where(over > 0.5, np.maximum(ribU * 1.0, ribV * 0.55), np.maximum(ribV * 1.0, ribU * 0.55))
    edgeU = np.clip(1 - np.abs(np.abs(fu - 0.5) - 0.26) * 18, 0, 1) * ribU
    edgeV = np.clip(1 - np.abs(np.abs(fv - 0.5) - 0.26) * 18, 0, 1) * ribV
    sheenU = np.clip(1 - np.abs(fu - 0.5) * 9, 0, 1) * ribU
    sheenV = np.clip(1 - np.abs(fv - 0.5) * 9, 0, 1) * ribV
    out = lat * 0.62 + np.maximum(edgeU, edgeV) * 0.5 + np.maximum(sheenU, sheenV) * 0.38
    return np.clip(out, 0, 1).astype(np.float32)


def _lfrp_star_lattice_tex(h, w, s):
    """Stars made of stars: 5-point star outlines whose strokes are strings of
    micro-stars, at three nested scales — a constellation lattice."""
    rng = _rng(s, 83)
    sr = _sr(h, w)
    dots = np.zeros((h, w), np.float32)
    polys = []

    def star_pts(cx, cy, r, rot):
        pts = []
        for k in range(10):
            rr = r if k % 2 == 0 else r * 0.42
            ang = rot + np.pi * k / 5
            pts.append([cx + np.cos(ang) * rr, cy + np.sin(ang) * rr])
        pts.append(pts[0])
        return np.float32(pts)

    for scale_r, n in ((44, 40), (24, 150), (11, 480)):
        for _ in range(int(n * sr * sr)):
            cx, cy = rng.uniform(0, w), rng.uniform(0, h)
            r = scale_r * sr * rng.uniform(0.8, 1.2)
            rot = rng.uniform(0, 2 * np.pi)
            sp = star_pts(cx, cy, r, rot)
            if scale_r > 30:
                # stroke the outline with micro-star dots
                for i in range(len(sp) - 1):
                    seg = np.linspace(0, 1, 7)[:, None]
                    pp = sp[i][None, :] * (1 - seg) + sp[i + 1][None, :] * seg
                    for q in pp:
                        ix, iy = int(q[0]), int(q[1])
                        if 0 <= ix < w and 0 <= iy < h:
                            dots[iy, ix] = 1.0
            else:
                polys.append(sp)
    out = _curves(h, w, polys, thick=1)
    dots = np.clip(_gauss(dots, 1.0 * sr) * 6, 0, 1)
    return np.clip(np.maximum(out, dots * 0.9), 0, 1)


def _lfrp_stencil_stars_tex(h, w, s):
    """Spray-stencil stars: crisp filled cutouts, overspray halo speckle, paint
    drips running off random edges at one global angle."""
    rng = _rng(s, 89)
    sr = _sr(h, w)
    fill = np.zeros((h, w), np.float32)
    drip_a = rng.uniform(0, 2 * np.pi)
    drips = []
    for _ in range(int(70 * sr * sr) + 10):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(9, 34) * sr
        rot = rng.uniform(0, 2 * np.pi)
        pts = []
        for k in range(10):
            rr = r if k % 2 == 0 else r * 0.42
            ang = rot + np.pi * k / 5
            pts.append([cx + np.cos(ang) * rr, cy + np.sin(ang) * rr])
        cv2.fillPoly(fill, [np.round(np.float32(pts)).astype(np.int32)], float(rng.uniform(0.8, 1.0)))
        if rng.random() < 0.4:
            ln = rng.uniform(1.2, 3.0) * r
            drips.append(np.float32([[cx, cy], [cx + np.cos(drip_a) * ln, cy + np.sin(drip_a) * ln]]))
    halo = _gauss(fill, 6 * sr)
    spray = (_noise(h, w, s ^ 0x99, (1.5, 3)) > 0.62).astype(np.float32) * np.clip(halo * 2.2, 0, 0.5)
    dr = _curves(h, w, drips, thick=max(1, int(2 * sr)))
    return np.clip(fill + spray + dr * 0.55, 0, 1)


def _lfrp_stripe_drift_tex(h, w, s):
    """Pinstriper's drift: a field of fine parallel pinstripes flowing around
    invisible discs (potential flow) — the stripes part and rejoin like water."""
    rng = _rng(s, 97)
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    a = float(rng.uniform(0, np.pi))
    # potential flow: uniform stream + dipoles. (Only the cross-stream coordinate v
    # feeds the stream function psi; the along-stream u was computed but never used —
    # PERF 2026-06-13 wave2 lane: dropped, bit-identical, no rng consumed.)
    v = (-xx * np.sin(a) + yy * np.cos(a)).astype(np.float32)
    psi = v.copy()
    for _ in range(7):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        R = rng.uniform(40, 120) * sr
        du = (xx - cx) * np.cos(a) + (yy - cy) * np.sin(a)
        dv = -(xx - cx) * np.sin(a) + (yy - cy) * np.cos(a)
        r2 = du * du + dv * dv + 1e-3
        psi = psi - dv * (R * R) / r2
    p = 6.5 * sr
    stripes = (0.5 + 0.5 * np.sin(psi * (2 * np.pi / p)))
    out = _sstep(0.62, 0.85, stripes.astype(np.float32))
    return out.astype(np.float32)


_W2_PAT_TEX = {
    "lfr_bunting_scallop": _lfrp_bunting_scallop_tex,
    "lfr_firework_radial": _lfrp_firework_radial_tex,
    "lfr_ribbon_weave": _lfrp_ribbon_weave_tex,
    "lfr_star_lattice": _lfrp_star_lattice_tex,
    "lfr_stencil_stars": _lfrp_stencil_stars_tex,
    "lfr_stripe_drift": _lfrp_stripe_drift_tex,
}
_W2_PAT_COLOR = {
    "lfr_bunting_scallop": (np.float32([0.55, 0.10, 0.16]), np.float32([0.95, 0.90, 0.86])),
    "lfr_firework_radial": (np.float32([0.85, 0.55, 0.20]), np.float32([1.0, 0.95, 0.75])),
    "lfr_ribbon_weave": (np.float32([0.50, 0.45, 0.42]), np.float32([0.96, 0.93, 0.88])),
    "lfr_star_lattice": (np.float32([0.70, 0.75, 0.95]), np.float32([1.0, 1.0, 1.0])),
    "lfr_stencil_stars": (np.float32([0.80, 0.78, 0.72]), np.float32([1.0, 0.98, 0.92])),
    "lfr_stripe_drift": (np.float32([0.72, 0.14, 0.20]), np.float32([0.98, 0.92, 0.88])),
}


# ════════════════════════════════════════════ SPEC OVERLAY REBUILDS (catalog fns)
# Contract: fn(shape, seed, sm, **kw) -> HxWx3 float32 [0,1] stack(M,R,Cc).
# Decorrelated channels (each its own geometry), FINE detail, sub-second.

def _ov_sm(out, sm):
    """Compress toward 0.5 by sm, sm>1-safe (damped, never clips) — matches the
    engine's _sm_scale contract for spec overlays."""
    sm = float(sm)
    if sm >= 1.0:
        k = 1.0 + (min(sm, 2.0) - 1.0) * 0.42
    else:
        k = sm
    return np.clip(0.5 + (out - 0.5) * k, 0.0, 1.0).astype(np.float32)


def w2_spec_lfr_corridor_sheen(shape, seed, sm, **kw):
    """Micro-pleated satin corridors — three independent angle families of FINE
    pleat banding; M=pleats, R=cross-grain satin (signed), Cc=corridor pooling."""
    h, w = int(shape[0]), int(shape[1])
    s = _seed_int(seed)
    yy, xx = _coords(h, w)
    rng = _rng(s, 11)
    sr = _sr(h, w)
    accM = np.zeros((h, w), np.float32)
    for _ in range(4):
        a = rng.uniform(0, np.pi)
        p = rng.uniform(3.2, 6.5) * sr
        accM += np.sin((xx * np.cos(a) + yy * np.sin(a)) * (2 * np.pi / p) + _noise(h, w, s ^ int(a * 91), (60, 160)) * 7)
    M = 0.5 + 0.28 * np.sin(accM * 1.4) + 0.16 * (_noise(h, w, s ^ 0x1, (40, 110)) - 0.5)
    aB = rng.uniform(0, np.pi)
    grain = _dirblur(_noise(h, w, s ^ 0x2, (1.6, 3.4)), aB, int(20 * sr))
    pol = np.sign(np.sin((xx * np.cos(aB + np.pi / 2) + yy * np.sin(aB + np.pi / 2)) * (2 * np.pi / (90 * sr))))
    R = 0.5 + (grain - 0.5) * 0.34 * pol
    pool = _noise(h, w, s ^ 0x3, (130, 320))
    Cc = 0.42 + (pool - 0.5) * 0.42 + 0.10 * np.sin(accM)
    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(Cc, 0, 1)], -1).astype(np.float32)
    return _ov_sm(out, sm)


def w2_spec_lfr_firework_radial(shape, seed, sm, **kw):
    """Micro-burst glint field: M=dense radial spark spokes, R=signed smoke rings,
    Cc=afterglow pools around the burst hearts."""
    h, w = int(shape[0]), int(shape[1])
    s = _seed_int(seed)
    rng = _rng(s, 13)
    sr = _sr(h, w)
    polys, rings, hearts = [], [], np.zeros((h, w), np.float32)
    for _ in range(int(60 * sr * sr) + 12):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(10, 42) * sr
        n_ray = int(rng.uniform(14, 26))
        a0 = rng.uniform(0, 2 * np.pi)
        for k in range(n_ray):
            ang = a0 + 2 * np.pi * k / n_ray
            polys.append(np.float32([[cx + np.cos(ang) * r * 0.15, cy + np.sin(ang) * r * 0.15],
                                     [cx + np.cos(ang) * r, cy + np.sin(ang) * r]]))
        aa = np.linspace(0, 2 * np.pi, 30)
        rings.append(np.stack([cx + np.cos(aa) * r * 0.55, cy + np.sin(aa) * r * 0.55], -1))
        iy, ix = int(cy), int(cx)
        if 0 <= iy < h and 0 <= ix < w:
            hearts[iy, ix] = 1.0
    spokes = _curves(h, w, polys, thick=1)
    ringv = _curves(h, w, rings, thick=max(1, int(2 * sr)))
    M = 0.34 + spokes * 0.55 + 0.10 * (_noise(h, w, s ^ 0x4, (2, 5)) - 0.5)
    pol = np.sign(_noise(h, w, s ^ 0x5, (170, 400)) - 0.5)
    R = 0.5 + (ringv - 0.18) * 0.36 * pol
    glow = np.clip(_gauss(hearts, 22 * sr) * 70, 0, 1)
    Cc = 0.34 + glow * 0.48 + (_noise(h, w, s ^ 0x6, (130, 320)) - 0.5) * 0.16
    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(Cc, 0, 1)], -1).astype(np.float32)
    return _ov_sm(out, sm)


def w2_spec_lfr_sparkler_embers(shape, seed, sm, **kw):
    """Sparkler in the dark: M=thousands of micro-star pins, R=crackle branch
    twigs (signed), Cc=drifting ember decay pools."""
    h, w = int(shape[0]), int(shape[1])
    s = _seed_int(seed)
    sr = _sr(h, w)
    pins = _stars(h, w, s, n=int(16000 * sr * sr) + 2000, bright_frac=0.03, spikes=True)
    M = 0.30 + pins * 0.62
    twigs = _dendrites(h, w, s ^ 0x7, n_roots=180, depth=4, seg=14 * sr, thick=1)
    pol = np.sign(_noise(h, w, s ^ 0x8, (140, 340)) - 0.5)
    R = 0.5 + (twigs - 0.12) * 0.40 * pol
    decay = _noise(h, w, s ^ 0x9, (90, 220, 500))
    Cc = 0.36 + (decay - 0.5) * 0.40 + pins * 0.18
    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(Cc, 0, 1)], -1).astype(np.float32)
    return _ov_sm(out, sm)


def w2_spec_lfr_starfield_scatter(shape, seed, sm, **kw):
    """Deep night starfield, FAST (the old one hung): M=multi-magnitude stars with
    diffraction spikes, R=fine nebula grain, Cc=soft constellation corridors."""
    h, w = int(shape[0]), int(shape[1])
    s = _seed_int(seed)
    sr = _sr(h, w)
    sky = _stars(h, w, s, n=int(22000 * sr * sr) + 3000, bright_frac=0.015, spikes=True)
    M = 0.28 + sky * 0.66
    R = 0.5 + (_noise(h, w, s ^ 0xA, (2.2, 5, 12)) - 0.5) * 0.36
    corr = _noise(h, w, s ^ 0xB, (160, 380))
    Cc = 0.36 + (corr - 0.5) * 0.40 + sky * 0.20
    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(Cc, 0, 1)], -1).astype(np.float32)
    return _ov_sm(out, sm)


def w2_spec_lfr_torch_flicker(shape, seed, sm, **kw):
    """Torch flame anisotropy: M=fine flame-tongue hatching licking one way,
    R=heat-shimmer micro ripple (signed), Cc=torch pool glow."""
    h, w = int(shape[0]), int(shape[1])
    s = _seed_int(seed)
    sr = _sr(h, w)
    rng = _rng(s, 17)
    a = float(rng.uniform(0, np.pi))
    tone = _n01(_noise(h, w, s ^ 0xC, (20, 50, 130)))
    tongues = _engrave(h, w, tone, s, pitch=3.8, curl=30, sharp=4.5, angle=a)
    M = 0.32 + tongues * 0.52 + 0.10 * (_noise(h, w, s ^ 0xD, (2, 4)) - 0.5)
    shim = _dirblur(_noise(h, w, s ^ 0xE, (1.5, 3)), a + np.pi / 2, int(9 * sr))
    pol = np.sign(np.sin((_coords(h, w)[1] * np.cos(a) + _coords(h, w)[0] * np.sin(a)) * (2 * np.pi / (70 * sr))))
    R = 0.5 + (shim - 0.5) * 0.38 * pol
    pools = _noise(h, w, s ^ 0xF, (110, 280))
    Cc = 0.36 + (pools - 0.5) * 0.44 + tongues * 0.10
    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(Cc, 0, 1)], -1).astype(np.float32)
    return _ov_sm(out, sm)


def w2_crackle_network(shape, seed, sm, **kw):
    """Hierarchical crackle (rebuilt FAST — the old one hung for minutes):
    two nested anisotropic crack webs + micro-twigs, all sub-second.
    M=plate sheen by grain, R=crack walls rough (signed), Cc=crack depth."""
    h, w = int(shape[0]), int(shape[1])
    s = _seed_int(seed)
    sr = _sr(h, w)
    cid1, edge1, or1, ax1 = _crystal(h, w, s, n_sites=240, aniso=2.2, res=0.3)
    cid2, edge2, or2, ax2 = _crystal(h, w, s ^ 0x77, n_sites=1800, aniso=1.6, res=0.3)
    crack1 = 1.0 - _sstep(0.03, 0.10, edge1)
    crack2 = (1.0 - _sstep(0.04, 0.12, edge2)) * 0.6
    twigs = _dendrites(h, w, s ^ 0x3, n_roots=200, depth=3, seg=12 * sr, thick=1) * 0.4
    cracks = np.clip(crack1 + crack2 + twigs, 0, 1)
    M = 0.30 + _n01(np.sin(cid2 * 7.7) + 1) * 0.34 + (1 - cracks) * 0.12
    pol = np.sign(np.sin(or1 * 3.1) + 1e-3)
    R = 0.5 + (cracks - 0.25) * 0.42 * pol
    Cc = 0.62 - cracks * 0.42 + (_noise(h, w, s ^ 0x21, (60, 150)) - 0.5) * 0.18
    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(Cc, 0, 1)], -1).astype(np.float32)
    return _ov_sm(out, sm)


def w2_spec_abalone_crack_inlay(shape, seed, sm, **kw):
    """Abalone shell inlay (rebuilt FAST): nacre shards with interference banding
    along each shard's grain, dark grout channels. M=banding, R=per-shard polish
    (signed), Cc=grout depth + shard pin."""
    h, w = int(shape[0]), int(shape[1])
    s = _seed_int(seed)
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=520, aniso=3.0, res=0.3)
    per = _n01(np.sin(cid * 12.99) + 1)
    band = 0.5 + 0.5 * np.sin(axial * 1.7 + per * 9.0)
    grout = 1.0 - _sstep(0.04, 0.13, edge)
    M = 0.30 + band * 0.40 * (1 - grout) + per * 0.14
    pol = np.where(per > 0.5, 1.0, -1.0)
    R = 0.5 + (0.30 - band * 0.26) * pol * (1 - grout) + grout * 0.22
    Cc = 0.58 - grout * 0.40 + band * (1 - grout) * 0.16 + (_noise(h, w, s ^ 0x31, (50, 130)) - 0.5) * 0.14
    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(Cc, 0, 1)], -1).astype(np.float32)
    return _ov_sm(out, sm)


W2_SPEC_OVERLAYS = {
    "spec_lfr_corridor_sheen": w2_spec_lfr_corridor_sheen,
    "spec_lfr_firework_radial": w2_spec_lfr_firework_radial,
    "spec_lfr_sparkler_embers": w2_spec_lfr_sparkler_embers,
    "spec_lfr_starfield_scatter": w2_spec_lfr_starfield_scatter,
    "spec_lfr_torch_flicker": w2_spec_lfr_torch_flicker,
    "crackle_network": w2_crackle_network,
    "spec_abalone_crack_inlay": w2_spec_abalone_crack_inlay,
}

# Owner-rated REMOVE (2026-06-10 spec_overlay audit) — catalog cleanup, popped
# from spec_patterns.PATTERN_CATALOG at install time.
W2_REMOVED_OVERLAYS = [
    "aniso_grain", "crystal_shimmer", "demon_eye_field", "diagonal_bands",
    "engraved_crosshatch", "face_mill_bands", "guilloche_barleycorn",
    "guilloche_hobnail", "heat_distortion", "interference_bands",
    "jeweling_circles", "micro_facets", "micro_sparkle_warm", "moire_overlay",
    "radiator_grille_mesh", "reptile_scale", "spec_aerogel_surface",
    "spec_asphalt_aggregate_sharp", "spec_billet_chamfer_facets",
    "spec_carbon_plain_weave", "spec_carbon_wet_layup", "spec_chainlink_fence",
    "spec_clearcoat_orange_peel_pro", "spec_cloisonne_enamel_cell",
    "spec_cracked_powdercoat_edge", "spec_diffraction_grating_cd",
    "spec_electroformed_texture", "spec_engine_turn_coin_scale",
    "spec_faceted_diamond", "spec_fiberglass_crossply",
    "spec_fuel_stain_evap_ring", "spec_guilloche_watch_dial",
    "spec_heat_shield_dimple_foil", "spec_hexagonal_tiles",
    "spec_kintsugi_clear_crack", "spec_oil_film_gasket", "spec_oil_slick",
    "spec_riveted_plate", "spec_rivnut_grid", "spec_safety_wire_twist",
    "spec_sparkle_constellation", "spec_stamped_emboss",
    "spec_water_ripple_spec", "spec_woven_dyneema",
    "spec_wrinkle_black_engine_paint", "spec_xirallic_crystal",
    "topographic_steps", "torii_ember_lattice",
]


# ════════════════════════════════════════════════════ DESIGN REGISTRY + WIRING
DESIGNS = {
    # 29 PRIZM — full drawing-board redo
    "prizm_adaptive":      (_pz_adaptive_paint, _pz_adaptive_spec),
    "prizm_alien_skin":    (_pz_alien_paint, _pz_alien_spec),
    "prizm_arctic":        (_pz_arctic_paint, _pz_arctic_spec),
    "prizm_aurora_shift":  (_pz_aurora_paint, _pz_aurora_spec),
    "prizm_black_rainbow": (_pz_blackrb_paint, _pz_blackrb_spec),
    "prizm_blood_moon":    (_pz_bloodmoon_paint, _pz_bloodmoon_spec),
    "prizm_candy_paint":   (_pz_candy_paint, _pz_candy_spec),
    "prizm_chrome_rose":   (_pz_chromerose_paint, _pz_chromerose_spec),
    "prizm_copper_flame":  (_pz_copperflame_paint, _pz_copperflame_spec),
    "prizm_cosmos":        (_pz_cosmos_paint, _pz_cosmos_spec),
    "prizm_dark_matter":   (_pz_darkmatter_paint, _pz_darkmatter_spec),
    "prizm_deep_space":    (_pz_deepspace_paint, _pz_deepspace_spec),
    "prizm_duochrome":     (_pz_duochrome_paint, _pz_duochrome_spec),
    "prizm_ember":         (_pz_ember_paint, _pz_ember_spec),
    "prizm_fire_ice":      (_pz_fireice_paint, _pz_fireice_spec),
    "prizm_galaxy_dust":   (_pz_galaxydust_paint, _pz_galaxydust_spec),
    "prizm_holographic":   (_pz_holo_paint, _pz_holo_spec),
    "prizm_iridescent":    (_pz_irid_paint, _pz_irid_spec),
    "prizm_midnight":      (_pz_midnight_paint, _pz_midnight_spec),
    "prizm_mystichrome":   (_pz_mystichrome_paint, _pz_mystichrome_spec),
    "prizm_neon":          (_pz_neon_paint, _pz_neon_spec),
    "prizm_oceanic":       (_pz_oceanic_paint, _pz_oceanic_spec),
    "prizm_phoenix":       (_pz_phoenix_paint, _pz_phoenix_spec),
    "prizm_solar":         (_pz_solar_paint, _pz_solar_spec),
    "prizm_spectrum":      (_pz_spectrum_paint, _pz_spectrum_spec),
    "prizm_sunset_strip":  (_pz_sunsetstrip_paint, _pz_sunsetstrip_spec),
    "prizm_titanium":      (_pz_titanium_paint, _pz_titanium_spec),
    "prizm_toxic_waste":   (_pz_toxic_paint, _pz_toxic_spec),
    "prizm_venom":         (_pz_venom_paint, _pz_venom_spec),
    # 2 LFR monolithic finishes
    "lfr_old_glory_flux":  (_lfr_oldglory_paint, _lfr_oldglory_spec),
    "lfr_we_the_people":   (_lfr_wethepeople_paint, _lfr_wethepeople_spec),
}


# ═══════════════════════════════════════ 2026-06-21 COLOR SCIENCE REDIRECT — PRIZM
# Owner mandate: every PRIZM finish gets a UNIQUE, elaborate, deep, dynamic spec —
# NO shared spec. Each prizm spec_d is rebuilt onto engine/paint_v2/color_science_2026
# (candy-depth + a distinct high-math look per finish + motion). Paint kept as-is.
def _pz_cs_spec_d(recipe, seed_off):
    _rc = dict(recipe)
    _so = int(seed_off)

    def spec_d(h, w, s):
        from engine.paint_v2 import color_science_2026 as _csx
        spec = _csx.compose_cs_spec((int(h), int(w)), int(s) + _so, 1.0, _rc)
        return (spec[:, :, 0].astype(np.float32),
                spec[:, :, 1].astype(np.float32),
                spec[:, :, 2].astype(np.float32))
    return spec_d


_PZ_CANDY = {
    "std":  {},
    "warm": dict(m_hi=242, r_core=22, cc_core=16, cc_edge=184, r_edge=118),
    "dark": dict(m_lo=66, m_hi=214, cc_edge=178),
    "icy":  dict(m_hi=232, r_edge=94, cc_edge=150, gamma=1.55),
    "deep": dict(m_hi=238, cc_core=16, cc_edge=192, r_core=20, gamma=1.5),
}
# fid -> (look, look_kwargs, depth_from, candy_key, motion) — all distinct (no dupes)
_PZ_CS_RECIPES = {
    "prizm_holographic": ("holographic_mosaic", dict(cells=30), "structure", "std", 0.42),
    "prizm_spectrum":    ("spectral_spiral", dict(arms=7.0, twist=8.0), "structure", "std", 0.45),
    "prizm_iridescent":  ("iridescent_flow", dict(scale=4.0), "structure", "std", 0.35),
    "prizm_cosmos":      ("spectral_spiral", dict(arms=3.0, twist=11.0), "invert", "dark", 0.40),
    "prizm_oceanic":     ("ripple_caustics", dict(rings=11.0), "structure", "std", 0.30),
    "prizm_solar":       ("spectral_spiral", dict(arms=12.0, twist=3.0), "structure", "warm", 0.50),
    "prizm_neon":        ("guilloche", dict(a=13.0, b=15.0), "structure", "std", 0.36),
    "prizm_venom":       ("crystal_facets", dict(cells=50.0), "structure", "std", 0.30),
    "prizm_ember":       ("oilslick_thinfilm", dict(bands=6.0), "structure", "warm", 0.32),
    "prizm_fire_ice":    ("oilslick_thinfilm", dict(bands=9.0), "invert", "icy", 0.36),
    "prizm_midnight":    ("iridescent_flow", dict(scale=3.0), "structure", "dark", 0.30),
    "prizm_dark_matter": ("crystal_facets", dict(cells=34.0), "invert", "dark", 0.26),
    "prizm_black_rainbow": ("holographic_mosaic", dict(cells=22.0), "structure", "dark", 0.46),
    "prizm_blood_moon":  ("ripple_caustics", dict(rings=7.0), "structure", "warm", 0.30),
    "prizm_arctic":      ("crystal_facets", dict(cells=44.0), "structure", "icy", 0.30),
    "prizm_adaptive":    ("iridescent_flow", dict(scale=5.0), "invert", "std", 0.40),
    "prizm_duochrome":   ("oilslick_thinfilm", dict(bands=4.0), "structure", "deep", 0.40),
    "prizm_mystichrome": ("spectral_spiral", dict(arms=5.0, twist=6.0), "structure", "deep", 0.42),
    "prizm_phoenix":     ("spectral_spiral", dict(arms=9.0, twist=5.0), "invert", "warm", 0.50),
}
_PZ_LOOK_CYCLE = ["holographic_mosaic", "spectral_spiral", "crystal_facets",
                  "oilslick_thinfilm", "iridescent_flow", "ripple_caustics", "guilloche"]


def _pz_apply_color_science():
    """Mutate DESIGNS so every prizm_* finish uses a UNIQUE color_science_2026 spec."""
    i = 0
    for fid, (lk, kw, df, ck, mo) in _PZ_CS_RECIPES.items():
        if fid in DESIGNS:
            rec = {"look": lk, "look_kwargs": dict(kw), "depth_from": df,
                   "candy": dict(_PZ_CANDY.get(ck, {})), "motion": float(mo),
                   "phase": (i % 7) * 0.5, "relief": 26.0}
            DESIGNS[fid] = (DESIGNS[fid][0], _pz_cs_spec_d(rec, 4100 + i * 37))
            i += 1
    # any other prizm_* still on the old spec -> unique deterministic recipe
    candy_keys = list(_PZ_CANDY.keys())
    for fid in list(DESIGNS):
        if fid.startswith("prizm_") and fid not in _PZ_CS_RECIPES:
            hh = (sum(ord(c) for c in fid) * 2654435761) & 0x7FFFFFFF
            rec = {"look": _PZ_LOOK_CYCLE[hh % 7], "look_kwargs": {},
                   "depth_from": ("structure", "invert")[hh % 2],
                   "candy": dict(_PZ_CANDY[candy_keys[hh % len(candy_keys)]]),
                   "motion": 0.26 + (hh % 4) * 0.07, "phase": (hh % 7) * 0.4, "relief": 26.0}
            DESIGNS[fid] = (DESIGNS[fid][0], _pz_cs_spec_d(rec, 4800 + (hh % 5000)))


_pz_apply_color_science()


def _w2_mk_finish(fid):
    paint_d, spec_d = DESIGNS[fid]

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        eff = _up(paint_d(_WORK, _WORK, _seed_int(seed)), fh, fw)
        eff = _native_finish(eff, seed)        # unsharp + native flake tooth
        base = np.asarray(paint, np.float32)[:, :, :3]
        m = (_m2(mask, fh, fw) * float(pm))[..., None]
        return np.clip(base * (1.0 - m) + eff * m, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        M, R, Cc = spec_d(_WORK, _WORK, _seed_int(seed))
        return _pack(_up(M, fh, fw), _up(R, fh, fw), _up(Cc, fh, fw), _m2(mask, fh, fw), float(sm))

    def base_spec_fn(shape, seed, sm, base_m=None, base_r=None, **kw):
        fh, fw = int(shape[0]), int(shape[1])
        M, R, Cc = spec_d(_WORK, _WORK, _seed_int(seed))
        return _up(M, fh, fw), _up(R, fh, fw), _up(Cc, fh, fw)

    return spec_fn, paint_fn, base_spec_fn


def _w2_mk_pattern(fid):
    texfn = _W2_PAT_TEX[fid]
    lo, hi = _W2_PAT_COLOR[fid]

    def tex_route(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        val = np.asarray(texfn(fh, fw, _seed_int(seed)), np.float32)
        cc = np.clip(16.0 * (1.0 - val * 0.5), 0, 16).astype(np.uint8)
        return {"pattern_val": np.clip(val, 0, 1).astype(np.float32),
                "R_range": -120.0, "M_range": 95.0, "CC": cc}

    def paint_route(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        val = np.asarray(texfn(fh, fw, _seed_int(seed)), np.float32)
        if isinstance(bb, dict) and bb.get("pattern_val") is not None:
            val = np.clip(np.asarray(bb["pattern_val"], np.float32), 0, 1)
            if val.shape[:2] != (fh, fw):
                val = cv2.resize(val, (fw, fh), interpolation=cv2.INTER_LINEAR)
        metal = lo[None, None, :] + (hi - lo)[None, None, :] * val[..., None]
        base = np.asarray(paint, np.float32)[:, :, :3]
        # ALWAYS confined to the zone mask (owner bug 2026-06-10)
        a = (val * float(pm) * _m2(mask, fh, fw))[..., None]
        return np.clip(base * (1.0 - a) + metal * a, 0, 1).astype(np.float32)

    return tex_route, paint_route


def install_into_engine(mono_reg, base_reg):
    """Register every wave2 redesign into the live registries: 31 finishes
    (mono + base override), 6 LFR pattern routes, 7 spec-overlay rebuilds,
    48 owner-rated overlay removals. Returns a summary string."""
    nf = nb = npat = nov = nrm = 0
    for fid in DESIGNS:
        spec_fn, paint_fn, base_spec_fn = _w2_mk_finish(fid)
        mono_reg[fid] = (spec_fn, paint_fn)
        nf += 1
        be = base_reg.get(fid) if base_reg is not None else None
        if isinstance(be, dict) and "base_spec_fn" in be:
            be["paint_fn"] = paint_fn
            be["base_spec_fn"] = base_spec_fn
            nb += 1
    try:
        import engine.expansion_patterns as _xp
        if hasattr(_xp, "_IGN_TEX_ROUTES"):
            for fid in _W2_PAT_TEX:
                tex_route, paint_route = _w2_mk_pattern(fid)
                _xp._IGN_TEX_ROUTES[fid] = tex_route
                _xp._IGN_PAINT_ROUTES[fid] = paint_route
                npat += 1
    except Exception:
        pass
    try:
        from engine.spec_patterns import PATTERN_CATALOG as _cat
        # SPB-105 thumbnail/catalog repair tick 6 (2026-07-13). Owner verdict:
        # "The program needs to bake new and correct thumbnail previews for the
        # new SPEC PATTERN OVERLAYS." The July five-round overhaul intentionally
        # restores a small set of IDs that the June Wave-2 audit had retired.
        # Protect the current picker contract from this older cleanup pass;
        # runtime-resolvable visible overlays move 177/181 -> 181/181.
        try:
            from engine.spec_pattern_families.visible_overlays_2026 import PICKER_VISIBLE_SPEC_IDS
            _current_visible_overlays = frozenset(PICKER_VISIBLE_SPEC_IDS)
        except Exception:
            _current_visible_overlays = frozenset()
        for oid, fn in W2_SPEC_OVERLAYS.items():
            if oid in _cat:
                _cat[oid] = fn
                nov += 1
        for oid in W2_REMOVED_OVERLAYS:
            if oid in _current_visible_overlays:
                continue
            if _cat.pop(oid, None) is not None:
                nrm += 1
    except Exception:
        pass
    return ("wave2: %d finishes (%d base), %d LFR patterns, %d overlays rebuilt, "
            "%d overlays removed" % (nf, nb, npat, nov, nrm))
