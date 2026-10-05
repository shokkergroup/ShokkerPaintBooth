"""FRACTURED generative-pattern MATH — the reusable engines (the math is the asset, not
the look). Each engine produces an intricate, full-coverage scalar FIELD in 0..1 that a
colorizer turns into dark-albedo FRACTURED art and fracture_spec() then ignites.

Engines (all deterministic by seed, computed at low res then upscaled to stay in budget):
  * reaction_diffusion  — Gray-Scott; organic Turing patterns (coral / labyrinth / mitosis
                          / spots / worms / holes) selected by (feed, kill) regime.
  * strange_attractor   — de Jong / Clifford map; ethereal filament webs (millions of
                          points accumulated, vectorized over parallel trajectories).
  * curl_flow           — divergence-free curl-noise field; advected particle density gives
                          fluid streamlines.
  * worley              — Voronoi F1/F2 distance fields; cellular scales or fracture webs.
  * interference        — superposed radial wave sources; moire / phase fields.

These COMPOSE (advect an RD field along a curl flow, modulate an attractor by Worley, ...)
to invent new looks from the same math. colorize() maps any field -> FRACTURE-ready RGB.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.paint_v2.fractured_motifs import _fbm, _rng


def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-9)


def _up(field: np.ndarray, h: int, w: int) -> np.ndarray:
    return cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)


def _lap(Z: np.ndarray) -> np.ndarray:
    """5/9-point wrapped Laplacian (toroidal, so patterns tile seamlessly on the UV sheet)."""
    return (
        0.20 * (np.roll(Z, 1, 0) + np.roll(Z, -1, 0) + np.roll(Z, 1, 1) + np.roll(Z, -1, 1))
        + 0.05 * (np.roll(np.roll(Z, 1, 0), 1, 1) + np.roll(np.roll(Z, 1, 0), -1, 1)
                  + np.roll(np.roll(Z, -1, 0), 1, 1) + np.roll(np.roll(Z, -1, 0), -1, 1))
        - Z
    )


# Classic Gray-Scott regimes (feed, kill) — each a different organism.
RD_REGIMES = {
    "coral":     (0.0545, 0.0620),
    "mitosis":   (0.0367, 0.0649),
    "labyrinth": (0.0290, 0.0570),
    "spots":     (0.0300, 0.0625),
    "worms":     (0.0540, 0.0630),
    "holes":     (0.0390, 0.0580),
    "waves":     (0.0140, 0.0500),
    "flower":    (0.0550, 0.0610),
}


def reaction_diffusion(h, w, seed, *, regime="coral", iters=2400, res=320,
                       du=0.16, dv=0.08, seeds=18) -> np.ndarray:
    """Gray-Scott reaction-diffusion -> organic Turing pattern field (0..1).

    NOTE: PARKED — finicky to keep alive across regimes and slow (>10s at useful res).
    Not used in the live showcase; revisit with per-regime tuning + a cached precompute
    before shipping it as a finish engine."""
    rng = _rng(seed)
    feed, kill = RD_REGIMES.get(regime, RD_REGIMES["coral"])
    U = np.ones((res, res), np.float32)
    V = np.zeros((res, res), np.float32)
    for _ in range(int(seeds)):
        cy, cx = int(rng.integers(0, res)), int(rng.integers(0, res))
        r = int(rng.integers(3, 9))
        U[max(0, cy - r):cy + r, max(0, cx - r):cx + r] = 0.5
        V[max(0, cy - r):cy + r, max(0, cx - r):cx + r] = 0.25
    V += (rng.random((res, res)).astype(np.float32) * 0.04)
    for _ in range(int(iters)):
        uvv = U * V * V
        U += du * _lap(U) - uvv + feed * (1.0 - U)
        V += dv * _lap(V) + uvv - (feed + kill) * V
        np.clip(U, 0.0, 1.0, out=U)
        np.clip(V, 0.0, 1.0, out=V)
    return _norm(_up(V, h, w))


def strange_attractor(h, w, seed, *, res=900, kind="dejong",
                      trajectories=22000, steps=240, burn=30) -> np.ndarray:
    """de Jong / Clifford attractor density -> intricate filament web (0..1).

    Vectorized over many parallel trajectories (the recurrence is sequential per point,
    but independent across points), accumulated into a 2D log-density histogram."""
    rng = _rng(seed)
    a, b, c, d = (float(v) for v in rng.uniform(-3.0, 3.0, 4))
    x = rng.uniform(-2.0, 2.0, trajectories).astype(np.float32)
    y = rng.uniform(-2.0, 2.0, trajectories).astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    lo, hi = -2.2, 2.2
    sc = (res - 1) / (hi - lo)
    for i in range(int(steps)):
        if kind == "clifford":
            nx = np.sin(a * y) + c * np.cos(a * x)
            ny = np.sin(b * x) + d * np.cos(b * y)
        else:  # de Jong
            nx = np.sin(a * y) - np.cos(b * x)
            ny = np.sin(c * x) - np.cos(d * y)
        x, y = nx, ny
        if i >= burn:
            ix = np.clip(((x - lo) * sc).astype(np.int32), 0, res - 1)
            iy = np.clip(((y - lo) * sc).astype(np.int32), 0, res - 1)
            np.add.at(acc, (iy, ix), 1.0)
    acc = np.log1p(acc)
    acc = cv2.GaussianBlur(acc, (0, 0), 0.8)
    return _norm(_up(acc, h, w))


def curl_flow(h, w, seed, *, res=512, particles=70000, steps=46, step_len=1.4) -> np.ndarray:
    """Divergence-free curl-noise flow; advected-particle density -> fluid streamlines (0..1)."""
    rng = _rng(seed)
    psi = _fbm(res, res, rng, octaves=5, base=6)
    gy, gx = np.gradient(psi.astype(np.float32))
    vx, vy = gy, -gx  # curl of the scalar potential (incompressible)
    nrm = np.hypot(vx, vy) + 1e-6
    vx, vy = vx / nrm, vy / nrm
    px = rng.uniform(0, res, particles).astype(np.float32)
    py = rng.uniform(0, res, particles).astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    for _ in range(int(steps)):
        ix = np.clip(px.astype(np.int32), 0, res - 1)
        iy = np.clip(py.astype(np.int32), 0, res - 1)
        np.add.at(acc, (iy, ix), 1.0)
        px = (px + vx[iy, ix] * step_len) % res
        py = (py + vy[iy, ix] * step_len) % res
    acc = cv2.GaussianBlur(np.log1p(acc), (0, 0), 0.7)
    return _norm(_up(acc, h, w))


def worley(h, w, seed, *, res=560, cells=150, kind="cracks") -> np.ndarray:
    """Voronoi F1/F2 distance field. kind: 'cracks' (cell edges), 'cells' (rounded scales),
    'shards' (F2)."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    tree = cKDTree(pts)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], axis=1).astype(np.float32)
    dist, _ = tree.query(q, k=2)
    F1 = dist[:, 0].reshape(res, res)
    F2 = dist[:, 1].reshape(res, res)
    if kind == "cells":
        field = 1.0 - _norm(F1)
    elif kind == "shards":
        field = _norm(F2)
    else:  # cracks — bright where F2-F1 is small (equidistant = cell boundary)
        edge = _norm(F2 - F1)
        field = np.clip(1.0 - edge * 3.2, 0.0, 1.0)
    return _up(field, h, w)


def interference(h, w, seed, *, sources=7, res=600) -> np.ndarray:
    """Superposed radial wave sources -> moire / phase interference field (0..1)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    for _ in range(int(sources)):
        cx, cy = rng.uniform(0, res, 2)
        k = rng.uniform(0.06, 0.16)
        d = np.sqrt((gx - cx) ** 2 + (gy - cy) ** 2)
        acc += np.sin(d * k + rng.uniform(0, 6.28))
    return _norm(_up(acc, h, w))


def colorize(field, base_rgb, glow_rgb, edge_rgb, *, gamma=1.0, fill_gain=0.85,
             edge_gain=1.0, edge_sigma=1.1, ambient=0.0, ambient_sigma=18.0,
             ambient_floor=0.0) -> np.ndarray:
    """Map a 0..1 field to FRACTURE-ready dark-albedo RGB: dark base + glow on the field's
    intensity + crisp edge highlights on its gradient (the fine detail the spec ignites).
    ambient>0 adds a soft wide-blur bloom of the field so SPARSE engines (attractor webs)
    cast a dim full-canvas glow = full coverage without losing the crisp web on top.
    ambient_floor (0..1) lifts the bloom's darkest regions to a guaranteed minimum, so even
    empty corners get a dim tint -> true full-canvas coverage for line-art / wispy engines."""
    f = np.clip(_norm(field), 0.0, 1.0) ** float(gamma)
    fl = cv2.GaussianBlur(f, (0, 0), edge_sigma)
    gx = cv2.Sobel(fl, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(fl, cv2.CV_32F, 0, 1, ksize=3)
    edge = _norm(np.hypot(gx, gy))
    amb = None
    if ambient > 0:
        amb = _norm(cv2.GaussianBlur(f, (0, 0), ambient_sigma))
        if ambient_floor > 0:
            amb = float(ambient_floor) + (1.0 - float(ambient_floor)) * amb
    h, w = field.shape[:2]
    out = np.empty((h, w, 3), np.float32)
    for i in range(3):
        out[:, :, i] = (base_rgb[i] / 255.0
                        + f * fill_gain * (glow_rgb[i] / 255.0)
                        + edge * edge_gain * (edge_rgb[i] / 255.0))
        if amb is not None:
            out[:, :, i] += amb * ambient * (glow_rgb[i] / 255.0)
    return np.clip(out, 0.0, 1.0)


# ── Wave 1 new engines ────────────────────────────────────────────────────────
def quasicrystal(h, w, seed, *, waves=9, freq=None, res=None) -> np.ndarray:
    """Sum of plane waves at evenly-spaced angles -> n-fold quasicrystal interference, computed
    at NATIVE output res and unsharp-masked so the fringes are crisp (not the soft upscaled
    field they used to be)."""
    rng = _rng(seed)
    if freq is None:
        freq = rng.uniform(12.0, 19.0)
    if res is None:
        res = max(int(h), int(w))
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    x = gx / res - 0.5
    y = gy / res - 0.5
    acc = np.zeros((res, res), np.float32)
    p0 = rng.uniform(0, 6.283)
    for i in range(int(waves)):
        ang = np.pi * i / waves + p0
        acc += np.cos((x * np.cos(ang) + y * np.sin(ang)) * freq * 6.283 + rng.uniform(0, 6.283))
    f = _norm(acc)
    sharp = np.clip(f + 1.4 * (f - cv2.GaussianBlur(f, (0, 0), 2.2)), 0.0, 1.0)  # unsharp -> crisp
    return _norm(_up(sharp, h, w))


def marble(h, w, seed, *, res=560, warps=3, veins=7.0) -> np.ndarray:
    """Iterated domain-warped fBm + multi-scale sine veining -> dense turbulent marble (the
    veins now run through the whole slab, not a few sparse seams)."""
    rng = _rng(seed)
    base = _fbm(res, res, rng, octaves=5, base=5)
    ys, xs = np.mgrid[0:res, 0:res].astype(np.float32)
    for _ in range(int(warps)):
        wx = (_fbm(res, res, rng, 4, 6) - 0.5) * res * 0.16
        wy = (_fbm(res, res, rng, 4, 6) - 0.5) * res * 0.16
        base = cv2.remap(base, np.clip(xs + wx, 0, res - 1), np.clip(ys + wy, 0, res - 1),
                         cv2.INTER_LINEAR)
    nb = _norm(base)
    veined = 0.6 * np.abs(np.sin(nb * np.pi * float(veins))) \
        + 0.4 * np.abs(np.sin(nb * np.pi * float(veins) * 2.3 + 1.0))  # second finer vein scale
    return _norm(_up(veined, h, w))


def truchet(h, w, seed, *, res=720, tiles=16) -> np.ndarray:
    """Curved Truchet tiling -> flowing maze / circuit (full coverage, classic + beautiful)."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    t = max(8, res // tiles)
    for i in range(0, res, t):
        for j in range(0, res, t):
            r = t // 2
            if rng.random() < 0.5:
                cv2.ellipse(img, (j, i), (r, r), 0, 0, 90, 1.0, 2, cv2.LINE_AA)
                cv2.ellipse(img, (j + t, i + t), (r, r), 0, 180, 270, 1.0, 2, cv2.LINE_AA)
            else:
                cv2.ellipse(img, (j + t, i), (r, r), 0, 90, 180, 1.0, 2, cv2.LINE_AA)
                cv2.ellipse(img, (j, i + t), (r, r), 0, 270, 360, 1.0, 2, cv2.LINE_AA)
    return _norm(_up(img, h, w))


def conformal_lattice(h, w, seed, *, res=820) -> np.ndarray:
    """A LATTICE of conformal singularities (Weierstrass-style sum of poles  w = Σ 1/(z - p_k)
    over a grid): the intricate high-frequency 1/z swirl now repeats at EVERY pole, so the
    beautiful dense detail of a single singularity tiles the whole canvas seamlessly instead of
    blurring out toward the edges."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float64)
    span = 3.0
    z = (gx / res - 0.5) * span + 1j * ((gy / res - 0.5) * span)
    n = 3                       # poles -n..n on each axis -> (2n+1)^2 singularities
    step = span / (2 * n + 1)   # pole spacing -> a cell per swirl, filling the frame
    jit = rng.uniform(-0.06, 0.06, (2 * n + 1, 2 * n + 1, 2)) * step
    wv = np.zeros_like(z)
    for ix, px in enumerate(range(-n, n + 1)):
        for iy, py in enumerate(range(-n, n + 1)):
            pole = (px * step + jit[ix, iy, 0]) + 1j * (py * step + jit[ix, iy, 1])
            wv += 1.0 / (z - pole + 1e-4)
    freq = rng.uniform(3.5, 5.5)
    grid = np.cos(wv.real * freq) + np.cos(wv.imag * freq)
    return _norm(_up(grid, h, w))


def shattered_glass(h, w, seed, *, res=760, impacts=4) -> np.ndarray:
    """TRUE impact fracture: radial cracks + concentric ring cracks from impact points
    (a real rethink vs the Voronoi 'shards' — looks like smashed glass, not cells)."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(impacts)):
        cx, cy = float(rng.uniform(0.12, 0.88) * res), float(rng.uniform(0.12, 0.88) * res)
        for _ in range(int(rng.integers(9, 17))):  # radial cracks
            ang = rng.uniform(0, 6.283)
            L = rng.uniform(0.30, 0.85) * res
            pts = [(cx, cy)]
            x, y = cx, cy
            for _s in range(9):
                ang += rng.uniform(-0.16, 0.16)
                x += np.cos(ang) * L / 9
                y += np.sin(ang) * L / 9
                pts.append((x, y))
            cv2.polylines(img, [np.array(pts, np.int32)], False, 1.0, 1, cv2.LINE_AA)
        for rr in np.linspace(0.06, 0.55, int(rng.integers(3, 6))) * res:  # concentric ring cracks
            cv2.circle(img, (int(cx), int(cy)), int(rr), 1.0, 1, cv2.LINE_AA)
    return _norm(_up(img, h, w))


# ── Wave 2 advanced-math engines ────────────────────────────────────────────
def _splat(pts_xy: np.ndarray, res: int, sigma: float = 1.2) -> np.ndarray:
    """Accumulate (x,y) points into a density field with a small gaussian blur (a KDE)."""
    acc = np.zeros((res, res), np.float32)
    ix = np.clip(pts_xy[:, 0].astype(np.int32), 0, res - 1)
    iy = np.clip(pts_xy[:, 1].astype(np.int32), 0, res - 1)
    np.add.at(acc, (iy, ix), 1.0)
    return cv2.GaussianBlur(acc, (0, 0), sigma)


def gabor_weave(h, w, seed, *, res=600, threads=32):
    """Crossed anisotropic thread bands with an over/under checker -> woven fabric."""
    rng = _rng(seed)
    ys, xs = np.mgrid[0:res, 0:res].astype(np.float32)
    wx = (_fbm(res, res, rng, 4, 5) - 0.5) * res * 0.05
    wy = (_fbm(res, res, rng, 4, 5) - 0.5) * res * 0.05
    u = np.abs(np.sin((xs + wx) / res * threads * np.pi))
    v = np.abs(np.sin((ys + wy) / res * threads * np.pi))
    over = (np.floor(xs / (res / threads)) + np.floor(ys / (res / threads))) % 2
    return _norm(_up(np.where(over > 0.5, u, v), h, w))


def phyllotaxis(h, w, seed, *, res=620, n=2300):
    """Vogel golden-angle spiral seeds rendered as their nearest-seed CELLS (a true sunflower-head
    packing) so the florets TILE the whole frame edge-to-edge with no bare ground. Bright seed
    centres + bright cell walls give the woven floret mosaic; the disc overflows the frame."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    ga = np.pi * (3.0 - np.sqrt(5.0))
    i = np.arange(1, n + 1, dtype=np.float32)
    r = np.sqrt(i / n) * (res * 0.98)  # overflow the frame -> seeds reach every corner
    th = i * ga + rng.uniform(0, 6.283)
    cy = res / 2 + r * np.sin(th)
    cx = res / 2 + r * np.cos(th)
    pts = np.stack([cy, cx], 1).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    dist, idx = cKDTree(pts).query(q, k=1)
    idx = idx.reshape(res, res)
    cell = _norm(dist.reshape(res, res))
    wall = ((idx != np.roll(idx, 1, 0)) | (idx != np.roll(idx, 1, 1))).astype(np.float32)
    field = (1.0 - cell) * 0.7 + wall
    return _norm(_up(field, h, w))


def apollonian(h, w, seed, *, res=720, target=750):
    """Dense bubble packing: many SMALL circles greedily packed wall-to-wall, each drawn as a
    rim-lit ring + inner ring so it reads as a glassy bubble. Reworked from the old sparse
    big-circle look (those circles would 'eat' a whole car panel)."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    cs = np.zeros((0, 3), np.float32)  # (x, y, r)
    tries = 0
    while len(cs) < target and tries < 60000:
        tries += 1
        rr = rng.uniform(2.5, res * 0.065) * (1.0 - len(cs) / target) ** 0.35
        x = rng.uniform(rr, res - rr)
        y = rng.uniform(rr, res - rr)
        if len(cs) and (((cs[:, 0] - x) ** 2 + (cs[:, 1] - y) ** 2) < (cs[:, 2] + rr) ** 2 * 1.03).any():
            continue
        cs = np.vstack([cs, (x, y, rr)])
        b = float(rng.uniform(0.55, 1.0))
        cv2.circle(img, (int(x), int(y)), int(rr), b, 1, cv2.LINE_AA)
        if rr > 6:
            cv2.circle(img, (int(x), int(y)), int(rr * 0.6), b * 0.55, 1, cv2.LINE_AA)
    return _norm(_up(img, h, w))


def pentagrid(h, w, seed, *, res=720, lines=8):
    """de Bruijn pentagrid (5 superposed line families) -> Penrose-like aperiodic ribbons."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    x = gx / res - 0.5
    y = gy / res - 0.5
    off = rng.uniform(0, 1, 5)
    acc = np.zeros((res, res), np.float32)
    for k in range(5):
        ang = 2 * np.pi * k / 5 + 0.1
        proj = (x * np.cos(ang) + y * np.sin(ang)) * lines + off[k]
        acc += np.abs(proj - np.round(proj))
    return _norm(_up(1.0 - _norm(acc), h, w))


def ridged_terrain(h, w, seed, *, res=600, octaves=6):
    """Ridged multifractal -> sharp mountainous ridge-line veins."""
    rng = _rng(seed)
    out = np.zeros((res, res), np.float32)
    amp = 0.5
    for o in range(octaves):
        n = _fbm(res, res, rng, 1, 3 * (o + 1) + 2)
        out += amp * (1.0 - np.abs(2.0 * n - 1.0)) ** 2
        amp *= 0.55
    return _norm(_up(out, h, w))


def harmonograph(h, w, seed, *, res=680, t_n=70000, curves=4):
    """Several damped harmonograph (multi-pendulum) curves at varied amplitudes overlaid so the
    looping ribbon spans the whole frame, on a finely-textured ground (not flat color) — so even
    a corner that maps to a full car panel still carries pattern."""
    rng = _rng(seed)
    field = np.zeros((res, res), np.float32)
    for _ in range(int(curves)):
        f = rng.uniform(2, 5, 4) * rng.choice([1.0, 1.0, 2.0], 4)
        p = rng.uniform(0, 6.283, 4)
        d = rng.uniform(0.0008, 0.0032, 4)
        t = np.linspace(0, 110, t_n).astype(np.float32)
        x = np.sin(t * f[0] + p[0]) * np.exp(-d[0] * t) + np.sin(t * f[1] + p[1]) * np.exp(-d[1] * t)
        y = np.sin(t * f[2] + p[2]) * np.exp(-d[2] * t) + np.sin(t * f[3] + p[3]) * np.exp(-d[3] * t)
        amp = rng.uniform(0.40, 0.50)
        cx = res / 2 + x / 2.05 * res * amp + rng.uniform(-0.06, 0.06) * res
        cy = res / 2 + y / 2.05 * res * amp + rng.uniform(-0.06, 0.06) * res
        field += _splat(np.stack([cx, cy], 1), res, sigma=1.0)
    tex = _fbm(res, res, rng, 5, 7)  # textured ground, never flat
    return _norm(_up(_norm(np.log1p(field)) * 0.82 + tex * 0.2, h, w))


def caustics(h, w, seed, *, res=560):
    """Where light rays bunch after refraction: density of a domain-warped grid -> caustic net."""
    rng = _rng(seed)
    ys, xs = np.mgrid[0:res, 0:res].astype(np.float32)
    wx = (_fbm(res, res, rng, 5, 5) - 0.5) * res * 0.20
    wy = (_fbm(res, res, rng, 5, 5) - 0.5) * res * 0.20
    f = _splat(np.stack([(xs + wx).ravel(), (ys + wy).ravel()], 1), res, sigma=1.1)
    return _norm(_up(np.log1p(f) ** 1.7, h, w))


def spiral_waves(h, w, seed, *, res=620, vortices=6, k=22.0):
    """Phase-oscillator (Kuramoto-style) spiral waves. The smooth winding+radial term keeps the
    sculpted 'elevation' look; a finer harmonic and a touch of multifractal are layered on so the
    surface carries much more fine detail (no longer a clean low-frequency swirl)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    phase = np.zeros((res, res), np.float32)
    for _ in range(int(vortices)):
        cx, cy = rng.uniform(0.15, 0.85, 2) * res
        phase += rng.choice([-1.0, 1.0]) * np.arctan2(gy - cy, gx - cx)
    rad = np.hypot(gx - res / 2, gy - res / 2) / res * k
    base = np.sin(phase + rad)                                # smooth swirl = the 3D 'elevation'
    fine = 0.5 * np.sin(phase * 3.0 + rad * 4.5)             # more arms + ripples (richer detail)
    micro = 0.28 * np.sin(rad * 6.0 + phase)                 # fine concentric detail rings
    grit = 0.3 * (_fbm(res, res, rng, 6, 8) - 0.5)          # multifractal micro-grain
    return _norm(_up(base + fine + micro + grit, h, w))


def wood_grain(h, w, seed, *, res=600, rings=20):
    """Warped concentric rings + streaks -> wood grain."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx, cy = rng.uniform(-0.3, 0.1) * res, rng.uniform(0.3, 0.7) * res
    warp = (_fbm(res, res, rng, 5, 4) - 0.5) * res * 0.13
    r = np.hypot(gx - cx, gy - cy) + warp
    grain = np.abs(np.sin(r / res * rings * 6.283))
    streak = (_fbm(res, res, rng, 3, 9) - 0.5)
    return _norm(_up(grain + streak * 0.25, h, w))


def domain_labyrinth(h, w, seed, *, res=300, iters=26):
    """Spinodal-style relaxation (blur + saturate) of noise -> magnetic-domain maze with bright walls."""
    rng = _rng(seed)
    z = rng.standard_normal((res, res)).astype(np.float32)
    for _ in range(iters):
        z = np.tanh(cv2.GaussianBlur(z, (0, 0), 1.4) * 3.0)
    edge = _norm(np.abs(cv2.Laplacian(z, cv2.CV_32F)))
    return _norm(_up(_norm(z) * 0.45 + edge * 0.9, h, w))


def moire(h, w, seed, *, res=640):
    """Two offset concentric ring-gratings multiplied -> moire interference rosettes."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx, cy = res / 2, res / 2
    k = rng.uniform(0.18, 0.34)
    dx, dy = rng.uniform(8, 22), rng.uniform(-18, 18)
    r1 = np.hypot(gx - cx, gy - cy)
    r2 = np.hypot(gx - cx - dx, gy - cy - dy)
    return _norm(_up(np.sin(r1 * k) * np.sin(r2 * k), h, w))


def flow_labyrinth(h, w, seed, *, res=320, iters=20):
    """Relaxation smeared along a curl-orientation field -> fingerprint / labyrinth ridges."""
    rng = _rng(seed)
    psi = _fbm(res, res, rng, 5, 5).astype(np.float32)
    gy, gx = np.gradient(psi)
    ang = np.arctan2(gy, gx)
    z = rng.standard_normal((res, res)).astype(np.float32)
    ys, xs = np.mgrid[0:res, 0:res].astype(np.float32)
    sx = np.clip(xs + np.cos(ang), 0, res - 1).astype(np.float32)
    sy = np.clip(ys + np.sin(ang), 0, res - 1).astype(np.float32)
    for _ in range(iters):
        z = np.tanh((0.5 * z + 0.5 * cv2.remap(z, sx, sy, cv2.INTER_LINEAR)) * 2.2)
    edge = _norm(np.abs(cv2.Laplacian(z, cv2.CV_32F)))
    return _norm(_up(edge + _norm(z) * 0.35, h, w))


def spectral_silk(h, w, seed, *, res=512, beta=2.6):
    """Anisotropic power-law Fourier noise -> directional silk / brushed sheen."""
    rng = _rng(seed)
    n = rng.standard_normal((res, res)).astype(np.float32)
    F = np.fft.fft2(n)
    fy = np.fft.fftfreq(res)[:, None]
    fx = np.fft.fftfreq(res)[None, :]
    r = np.hypot(fx, fy) + 1e-6
    ang = np.arctan2(fy * np.ones_like(fx), fx * np.ones_like(fy))
    th0 = rng.uniform(0, np.pi)
    amp = r ** (-beta / 2) * np.exp(2.6 * (np.cos(ang - th0) ** 2))
    out = np.fft.ifft2(F * amp).real
    return _norm(_up(out, h, w))


def gyroid(h, w, seed, *, res=600, scale=None):
    """A wavy slice through a gyroid triply-periodic minimal surface -> organic lattice."""
    rng = _rng(seed)
    scale = rng.uniform(4.0, 7.0) if scale is None else scale
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    x = gx / res * scale * 6.283
    y = gy / res * scale * 6.283
    z = rng.uniform(0, 6.283) + (_fbm(res, res, rng, 3, 3) - 0.5) * 2.2
    g = np.sin(x) * np.cos(y) + np.sin(y) * np.cos(z) + np.sin(z) * np.cos(x)
    return _norm(_up(np.abs(g), h, w))


def crystal_facets(h, w, seed, *, res=560, cells=90):
    """Flat-shaded Voronoi regions with crisp seams -> faceted gemstone / cut crystal."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    _, idx = cKDTree(pts).query(q, k=1)
    idx = idx.reshape(res, res)
    shade = rng.uniform(0.18, 1.0, int(cells)).astype(np.float32)[idx]
    edge = (idx != np.roll(idx, 1, 0)) | (idx != np.roll(idx, 1, 1))
    shade[edge] = 1.0
    return _norm(_up(shade, h, w))


# ── Wave 3 — INVENTED engines (novel math syntheses; FRACTURED calling card) ──
def phase_reliquary(h, w, seed, *, res=448, waves=90):
    """INVENTED. A complex wave field whose component MAGNITUDES |k| are drawn from a de Jong
    attractor orbit (chaos-shaped spectrum) but whose DIRECTIONS are isotropic (so it has no
    car-UV bias); the optical PHASE of their sum forms a web of singularities (zero-amplitude
    points where phase winds). Rendering the wrapped phase-gradient lights exactly that web —
    an isotropic, chaos-seeded speckle filigree no single classical method produces."""
    rng = _rng(seed)
    a, b, c, d = rng.uniform(-3.0, 3.0, 4)
    x, y, rad = 0.1, 0.1, []
    for i in range(waves + 40):
        x, y = np.sin(a * y) - np.cos(b * x), np.sin(c * x) - np.cos(d * y)
        if i >= 40:
            rad.append(float(np.hypot(x, y)))
    mag = 6.0 + 11.0 * _norm(np.array(rad, np.float32))  # chaos-derived spatial frequencies
    ang = rng.uniform(0, 6.283, len(mag))                # isotropic directions (no UV bias)
    kx, ky = mag * np.cos(ang), mag * np.sin(ang)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    X, Y = gx / res, gy / res
    field = np.zeros((res, res), np.complex64)
    for kxi, kyi, p in zip(kx, ky, rng.uniform(0, 6.283, len(mag))):
        field += np.exp(1j * ((kxi * X + kyi * Y) * 6.283 + p)).astype(np.complex64)
    ph = np.angle(field)
    gxp = np.angle(np.exp(1j * (np.roll(ph, -1, 1) - ph)))
    gyp = np.angle(np.exp(1j * (np.roll(ph, -1, 0) - ph)))
    return _norm(_up(np.hypot(gxp, gyp), h, w))


def mycelinth(h, w, seed, *, res=320, iters=14):
    """INVENTED. A SHOCK-FILTER PDE  (I_t = -sign(lap I)*|grad I|)  iterated on a multifractal:
    each step pushes values away from edges, sharpening soft noise into thin piecewise-constant
    cell WALLS. A growth process (not a static texture) that self-organizes into a vein lattice."""
    rng = _rng(seed)
    z = _fbm(res, res, rng, 4, 4).astype(np.float32)
    for _ in range(iters):
        z = cv2.GaussianBlur(z, (0, 0), 0.8)
        lap = cv2.Laplacian(z, cv2.CV_32F)
        gy, gx = np.gradient(z)
        z = _norm(z - 0.6 * np.sign(lap) * np.hypot(gx, gy))
    return _norm(_up(_norm(np.abs(cv2.Laplacian(z, cv2.CV_32F))), h, w))


def hyperflora(h, w, seed, *, res=760):
    """INVENTED. Take a 5-fold and a 7-fold quasicrystal as the REAL and IMAGINARY parts of one
    complex field z; render |z| modulated by arg(z). The two incommensurate symmetries beat
    against each other into quasiperiodic florets that tile the plane yet never repeat."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    # evaluate over an OFF-CENTRE, higher-frequency window so the beat's central ring sits off
    # the canvas -> florets stay tight and uniform everywhere (no big circle in the middle).
    ox, oy = float(rng.uniform(2.5, 5.0)), float(rng.uniform(2.5, 5.0))
    x, y = gx / res - 0.5 + ox, gy / res - 0.5 + oy

    def qc(nfold, f, ph):
        a = np.zeros((res, res), np.float32)
        for k in range(nfold):
            ang = np.pi * k / nfold + ph
            a += np.cos((x * np.cos(ang) + y * np.sin(ang)) * f * 6.283)
        return a

    z = qc(5, rng.uniform(11, 15), rng.uniform(0, 3)) + 1j * qc(7, rng.uniform(13, 18), rng.uniform(0, 3))
    mag, arg = _norm(np.abs(z)), _norm(np.angle(z))
    return _norm(_up(np.abs(np.sin(mag * np.pi * 3.0) * np.cos(arg * np.pi * 5.0)), h, w))


def soliton_reef(h, w, seed, *, res=620, iters=48):
    """INVENTED. A NEW transcendental escape-time fractal under the reciprocal-sine map
    z -> sin(z) + c/z  (mine). The sine's periodicity + the pole at 0 braid the escape set into
    coral-reef boundaries unlike any polynomial Julia set. The bounded 'coral' is given interior
    structure (orbit |z|/arg banding) so it reads as textured reef, not flat negative space;
    boundary gradient is emphasized so the filigree pops. Imag clamped to avoid overflow."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float64)
    sc = rng.uniform(1.25, 1.7)  # zoom further INTO the boundary so coral fills the frame (denser)
    ox, oy = rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3)
    z = (gx / res - 0.5) * sc + ox + 1j * ((gy / res - 0.5) * sc + oy)
    c = complex(rng.uniform(-0.7, 0.7), rng.uniform(-0.7, 0.7))
    cnt = np.zeros((res, res), np.float64)
    alive = np.ones((res, res), bool)
    for i in range(iters):
        z = np.sin(z) + c / (z + 1e-3)
        z = z.real + 1j * np.clip(z.imag, -12.0, 12.0)
        esc = np.abs(z) > 1e3
        cnt[esc & alive] = i
        alive &= ~esc
        z = np.where(alive, z, 0)
    cnt[alive] = iters
    esc_f = _norm(np.sqrt(_norm(cnt)))
    interior = 0.5 + 0.5 * np.sin(np.abs(z) * 4.0 + np.angle(z + 1e-9) * 3.0)  # finer reef texture
    # lift bounded 'voids' AND fast-escape flats so no large near-black blank panel survives
    field = np.where(alive, 0.52 + 0.46 * interior, 0.36 + 0.64 * esc_f).astype(np.float32)
    edge = _norm(np.abs(cv2.Laplacian(esc_f.astype(np.float32), cv2.CV_32F)))  # pop the filigree
    floor_tex = (_fbm(res, res, _rng(seed + 7), 5, 6).astype(np.float32) - 0.5)  # organic reef floor
    return _norm(_up(np.clip(_norm(field) * 0.78 + edge * 0.46 + 0.12 * floor_tex, 0, 1), h, w))


def aurora_loom(h, w, seed, *, res=480, steps=42, particles=60000):
    """INVENTED (showcase fusion). A divergence-free CURL flow advects particles through an
    interference PHASE field whose sources sit on a STRANGE-ATTRACTOR orbit; each particle
    deposits weight by the local phase. Flow + chaos + wave-interference co-author the image —
    remove any one and the iridescent woven streamlines collapse. The composition IS the look."""
    rng = _rng(seed)
    psi = _fbm(res, res, rng, 5, 5).astype(np.float32)
    gy, gx = np.gradient(psi)
    vx, vy = gy, -gx
    nrm = np.hypot(vx, vy) + 1e-6
    vx, vy = vx / nrm, vy / nrm
    a, b, c, d = rng.uniform(-2.5, 2.5, 4)
    xx, yy, src = 0.1, 0.1, []
    for i in range(70):
        xx, yy = np.sin(a * yy) - np.cos(b * xx), np.sin(c * xx) - np.cos(d * yy)
        if i >= 12:
            src.append(((xx + 2) / 4 * res, (yy + 2) / 4 * res))
    gy2, gx2 = np.mgrid[0:res, 0:res].astype(np.float32)
    phase = np.zeros((res, res), np.float32)
    for sxc, syc in src:
        phase += np.sin(np.hypot(gx2 - sxc, gy2 - syc) * 0.08 + rng.uniform(0, 6.283))
    px = rng.uniform(0, res, particles).astype(np.float32)
    py = rng.uniform(0, res, particles).astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    for _ in range(steps):
        ix = np.clip(px.astype(np.int32), 0, res - 1)
        iy = np.clip(py.astype(np.int32), 0, res - 1)
        np.add.at(acc, (iy, ix), 0.5 + 0.5 * np.sin(phase[iy, ix]))
        px = (px + vx[iy, ix] * 1.5) % res
        py = (py + vy[iy, ix] * 1.5) % res
    return _norm(_up(cv2.GaussianBlur(np.log1p(acc), (0, 0), 0.8), h, w))


# ── Revision 2 — full-canvas / replacement engines (no blank panels rule) ────
def attractor_web(h, w, seed, *, kind="dejong", layers=4, res=900,
                  trajectories=16000, steps=210, burn=30):
    """Many strange-attractor sheets (varied params, each rotated, scaled and toroidally WRAPPED
    to a different offset) summed into one density -> a filament WEB whose actual pattern covers
    the whole canvas edge-to-edge, instead of one sparse attractor curve floating on a glow."""
    rng = _rng(seed)
    acc = np.zeros((res, res), np.float32)
    lo, hi = -2.2, 2.2
    sc = (res - 1) / (hi - lo)
    for _ in range(int(layers)):
        a, b, c, d = (float(v) for v in rng.uniform(-3.0, 3.0, 4))
        x = rng.uniform(-2.0, 2.0, trajectories).astype(np.float32)
        y = rng.uniform(-2.0, 2.0, trajectories).astype(np.float32)
        rot = float(rng.uniform(0, 6.283))
        cosr, sinr = np.cos(rot), np.sin(rot)
        offx, offy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        zoom = float(rng.uniform(0.85, 1.35))
        for i in range(int(steps)):
            if kind == "clifford":
                x, y = np.sin(a * y) + c * np.cos(a * x), np.sin(b * x) + d * np.cos(b * y)
            else:
                x, y = np.sin(a * y) - np.cos(b * x), np.sin(c * x) - np.cos(d * y)
            if i >= burn:
                px = ((x - lo) * sc - res / 2) * zoom
                py = ((y - lo) * sc - res / 2) * zoom
                ix = ((px * cosr - py * sinr + offx) % res).astype(np.int32)
                iy = ((px * sinr + py * cosr + offy) % res).astype(np.int32)
                np.add.at(acc, (iy, ix), 1.0)
    return _norm(_up(cv2.GaussianBlur(np.log1p(acc), (0, 0), 0.7), h, w))


def stormfork(h, w, seed, *, res=720, bolts=34):
    """Recursive midpoint-displaced branching discharge (Lichtenberg / lightning) with bloom —
    the all-new replacement for shattered glass. Many bolts spawn from scattered points and fork
    aggressively (a fork can itself fork) so the discharge tree densely fills every corner."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)

    def bolt(x0, y0, x1, y1, depth, inten):
        if depth <= 0:
            cv2.line(img, (int(x0), int(y0)), (int(x1), int(y1)), float(inten), 1, cv2.LINE_AA)
            return
        spread = (abs(x1 - x0) + abs(y1 - y0)) * 0.13
        mx = (x0 + x1) / 2 + rng.normal(0, spread)
        my = (y0 + y1) / 2 + rng.normal(0, spread)
        bolt(x0, y0, mx, my, depth - 1, inten)
        bolt(mx, my, x1, y1, depth - 1, inten)
        if depth > 2 and rng.random() < 0.62:  # fork a side branch (can recurse into more forks)
            ang = np.arctan2(y1 - y0, x1 - x0) + rng.uniform(-1.1, 1.1)
            ln = np.hypot(x1 - x0, y1 - y0) * rng.uniform(0.5, 0.95)
            bolt(mx, my, mx + np.cos(ang) * ln, my + np.sin(ang) * ln, depth - 1, inten * 0.7)

    # distribute bolt ORIGINS across a jittered grid so the discharge erupts from every region
    # (incl. corners), then strike toward a random target -> no dark corners
    gn = max(2, int(np.ceil(np.sqrt(bolts))))
    cell = res / gn
    origins = [((i + 0.5) * cell, (j + 0.5) * cell) for i in range(gn) for j in range(gn)]
    for k in range(int(bolts)):
        sx, sy = origins[k % len(origins)]
        sx += rng.uniform(-cell / 2, cell / 2)
        sy += rng.uniform(-cell / 2, cell / 2)
        ang = rng.uniform(0, 6.283)
        ln = rng.uniform(0.35, 0.7) * res
        bolt(sx, sy, sx + np.cos(ang) * ln, sy + np.sin(ang) * ln, 7, 1.0)
    core = cv2.GaussianBlur(img, (0, 0), 0.7)
    glow = cv2.GaussianBlur(img, (0, 0), 6.0) * 0.7
    return _norm(_up(core + glow, h, w))


def dragonscale(h, w, seed, *, res=680, rows=15):
    """Staggered overlapping arc 'scales' (seigaiha-style) with per-scale shading -> ornate
    dragon/fish-scale tiling that fills the whole canvas. Replaces the redundant labyrinth."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    step = res / rows
    r = step * 0.97  # overlap rows so scales tile with no gaps (full coverage)
    jit = float(rng.uniform(0, 6.283))
    cy = -step
    ri = 0
    while cy <= res + step:
        offset = (step / 2) if (ri % 2) else 0.0
        cx = -step
        while cx <= res + step:
            shade = 0.62 + 0.32 * np.sin(cx * 0.045 + cy * 0.05 + jit)
            ctr = (int(cx + offset), int(cy))
            cv2.ellipse(img, ctr, (int(r), int(r)), 0, 0, 180, float(shade), -1, cv2.LINE_AA)  # filled scale
            for rr in (r * 0.72, r * 0.45, r * 0.2):  # bright concentric ridges
                cv2.ellipse(img, ctr, (int(rr), int(rr)), 0, 0, 180,
                            float(min(1.0, shade * 1.45)), 2, cv2.LINE_AA)
            cx += step
        cy += step
        ri += 1
    return _norm(_up(img, h, w))


def chladni(h, w, seed, *, res=700, modes=5):
    """Chladni plate vibration: sand collects on the NODAL lines of a sum of (n,m) standing
    modes -> intricate symmetric resonance figures. Non-Voronoi, fills the frame. Replaces the
    crystal-facet look (too many Voronoi engines already)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    x, y = gx / res, gy / res
    field = np.zeros((res, res), np.float32)
    for _ in range(int(modes)):
        n, m = int(rng.integers(2, 9)), int(rng.integers(2, 9))
        amp = float(rng.uniform(-1, 1))
        field += amp * (np.sin(n * np.pi * x) * np.sin(m * np.pi * y)
                        + np.sin(m * np.pi * x) * np.sin(n * np.pi * y))
    nodal = 1.0 - _norm(np.abs(field))  # bright where field ~ 0 (the nodal lines)
    return _norm(_up(nodal ** 2.4, h, w))


# ── Rebuild engines (bespoke per-name generators for the MINDS/SOULS rebuild) ──
def magma(h, w, seed, *, res=560, plates=110):
    """Cooled basalt crust split by a network of glowing molten cracks -> lava. Dark crust
    where the field is low, hot cracks where plate boundaries meet (high field)."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    crust = _fbm(res, res, rng, 5, 4).astype(np.float32)
    pts = rng.uniform(0, res, (int(plates), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    dd, _ = cKDTree(pts).query(q, k=2)
    F1 = dd[:, 0].reshape(res, res)
    F2 = dd[:, 1].reshape(res, res)
    crack = np.clip(1.0 - _norm(F2 - F1) * 4.5, 0.0, 1.0)   # bright along plate boundaries
    molten = crack * (0.55 + 0.45 * _norm(crust))           # crust modulates the glow
    field = _norm(0.22 * _norm(crust) + 1.0 * molten)        # dark crust + hot cracks
    return _up(field, h, w)


def flame_field(h, w, seed, *, res=512):
    """Roiling turbulent fire SHEET: multi-octave |fbm| ridges warped by a curl field so the heat
    licks and curls — a dense full-coverage flame wall (distinct from discrete tongues)."""
    rng = _rng(seed)
    turb = np.zeros((res, res), np.float32)
    amp = 0.5
    for o in range(5):
        turb += amp * np.abs(2.0 * _fbm(res, res, rng, 1, 3 * (o + 1) + 2) - 1.0)
        amp *= 0.55
    turb = _norm(turb)
    psi = _fbm(res, res, rng, 4, 5).astype(np.float32)
    gy, gx = np.gradient(psi)
    ys, xs = np.mgrid[0:res, 0:res].astype(np.float32)
    warped = cv2.remap(turb, np.clip(xs + gx * res * 0.14, 0, res - 1),
                       np.clip(ys + gy * res * 0.14, 0, res - 1), cv2.INTER_LINEAR)
    return _up(_norm(warped), h, w)


def flame_tongues(h, w, seed, *, res=512, n=70):
    """Discrete licking flame TONGUES: tapering blob-trails scattered and curl-wobbled at every
    angle (UV-agnostic) -> individual flames on near-black, not a uniform field."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(n)):
        x, y = rng.uniform(0.04, 0.96) * res, rng.uniform(0.04, 0.96) * res
        ang = rng.uniform(0, 6.283)
        L = rng.uniform(0.08, 0.24) * res
        r = rng.uniform(7, 17)
        for s in range(11):
            ang += rng.uniform(-0.28, 0.28)
            x += np.cos(ang) * L / 11
            y += np.sin(ang) * L / 11
            rr = max(1, int(r * (1.0 - s / 11.0)))
            cv2.circle(img, (int(x), int(y)), rr, float(1.0 - s / 13.0), -1, cv2.LINE_AA)
    img = cv2.GaussianBlur(img, (0, 0), 1.4)
    return _up(_norm(img), h, w)


def flame_helix(h, w, seed, *, res=512, arms=5):
    """Helical / spiralling flame columns: a winding spiral phase modulated by turbulence and
    faded radially -> swirling fire vortex."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx, cy = res * rng.uniform(0.4, 0.6), res * rng.uniform(0.4, 0.6)
    ang = np.arctan2(gy - cy, gx - cx)
    rad = np.hypot(gy - cy, gx - cx) / res
    turb = _fbm(res, res, rng, 5, 5).astype(np.float32) * 6.283
    spiral = np.sin(ang * arms + rad * 22.0 + turb)
    heat = _norm(spiral) * np.clip(1.25 - rad, 0.0, 1.0)
    heat = _norm(heat + 0.4 * np.abs(2.0 * _fbm(res, res, rng, 4, 6) - 1.0))
    return _up(heat, h, w)


def lava_veins(h, w, seed, *, res=512):
    """A branching network of glowing crest-veins from a ridged multifractal (the ridge crests
    form a dendritic vein web) -> glowing inferno veins through dark rock (NOT magma's cells)."""
    rng = _rng(seed)
    out = np.zeros((res, res), np.float32)
    amp = 0.5
    for o in range(6):
        n = _fbm(res, res, rng, 1, 3 * (o + 1) + 2)
        out += amp * (1.0 - np.abs(2.0 * n - 1.0))
        amp *= 0.5
    ridge = _norm(out)
    veins = _norm(np.abs(cv2.Laplacian(ridge, cv2.CV_32F))) ** 0.5   # crest lines = vein web (lifted)
    return _up(_norm(veins * 1.0 + ridge * 0.18), h, w)


def hexgrid(h, w, seed, *, res=600, cells=13, mode="filled", burst=False):
    """Hexagonal lattice via three 60°-spaced plane waves. mode: 'filled' (honeycomb cell bodies),
    'beveled' (rounded tech cells), 'lattice' (thin atomic wireframe). burst=radial frequency
    bloom from centre. Three genuinely different renders of the same hex math."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    x = gx / res - 0.5
    y = gy / res - 0.5
    if burst:
        rr = np.hypot(x, y) + 0.18
        x, y = x / rr, y / rr   # radial warp -> cells radiate/grow outward
    f = cells * 6.283
    ph = rng.uniform(0, 6.283)
    a = np.cos(x * f + ph)
    b = np.cos((x * 0.5 + y * 0.8660254) * f + ph)
    c = np.cos((x * 0.5 - y * 0.8660254) * f + ph)
    hexf = _norm(a + b + c)
    if mode == "lattice":
        field = _norm(np.abs(cv2.Laplacian(hexf, cv2.CV_32F)))   # thin hex edges only
    elif mode == "beveled":
        field = hexf ** 0.6
    else:  # filled honeycomb
        field = np.clip(hexf * 1.25, 0.0, 1.0)
    return _up(field, h, w)


def herringbone(h, w, seed, *, res=600, unit=26):
    """Chevron herringbone tweed: diagonal hatch whose direction flips every row -> interlocking V."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    row = np.floor(gy / unit).astype(np.int32)
    u = np.abs(((gx + gy) / unit) % 2.0 - 1.0)
    v = np.abs(((gx - gy) / unit) % 2.0 - 1.0)
    field = np.where(row % 2 == 0, u, v)
    return _up(_norm(field), h, w)


def basketweave(h, w, seed, *, res=600, cells=10):
    """True over/under basket: checkerboard tiles alternate horizontal vs vertical thread bundles."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    horiz = np.abs(np.sin(gy / s * np.pi * 3.0))
    vert = np.abs(np.sin(gx / s * np.pi * 3.0))
    checker = (np.floor(gx / s).astype(np.int32) + np.floor(gy / s).astype(np.int32)) % 2
    field = np.where(checker > 0, horiz, vert)
    return _up(_norm(field), h, w)


def carbon_twill(h, w, seed, *, res=600, cells=42):
    """2x2 twill diagonal rib (carbon fibre): offset diagonal weft floats give the woven sheen."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    rib = np.abs(((gx + gy) / s) % 2.0 - 1.0)              # main diagonal rib
    cross = 0.35 * np.abs(((gx - gy) / s) % 2.0 - 1.0)     # faint counter weave
    block = 0.25 * np.abs(np.sin(gx / (s * 4) * np.pi) * np.sin(gy / (s * 4) * np.pi))
    return _up(_norm(rib + cross + block), h, w)


def knurl(h, w, seed, *, res=600, cells=34):
    """Crossed triangle-wave diamond knurl — sharp filled diamond ridges (tooled grip texture)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    p = res / cells
    u = np.abs(((gx + gy) / p) % 2.0 - 1.0)
    v = np.abs(((gx - gy) / p) % 2.0 - 1.0)
    return _up(_norm(np.maximum(u, v) ** 1.4), h, w)


def knit_cable(h, w, seed, *, res=600, cols=11):
    """Knit cable columns: rounded cords braiding up each column with purl bumps."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cols
    colx = (gx % s) / s
    cord = np.sin(colx * np.pi)                              # rounded cord per column
    braid = np.abs(np.sin(gy / s * 6.283 * 2.0 + np.sin(colx * 6.283) * 2.2))
    purl = 0.3 * np.abs(np.sin(gy / s * 6.283 * 4.0))
    return _up(_norm(cord * (0.55 + 0.45 * braid) + purl * cord), h, w)


def chainmail_rings(h, w, seed, *, res=640, rings=14):
    """Interlocking riveted rings (4-in-1 mail): offset rows of overlapping rings."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / rings
    r = s * 0.62
    iy = 0
    cy = -s
    while cy <= res + s:
        off = (s / 2) if (iy % 2) else 0.0
        cx = -s
        while cx <= res + s:
            cv2.circle(img, (int(cx + off), int(cy)), int(r), 1.0, 2, cv2.LINE_AA)
            cv2.circle(img, (int(cx + off), int(cy)), int(r * 0.58), 0.45, 2, cv2.LINE_AA)
            cx += s
        cy += s
        iy += 1
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.7)), h, w)


def chainlink(h, w, seed, *, res=640, cells=12):
    """Galvanized chainlink fence: thin diagonal wire diamonds woven over/under."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    u = np.abs(np.sin((gx + gy) / res * cells * 6.283))
    v = np.abs(np.sin((gx - gy) / res * cells * 6.283))
    wire = np.maximum(1.0 - u, 1.0 - v)                      # thin diagonal wires -> diamonds
    return _up(_norm(np.clip(wire, 0, 1) ** 3.0), h, w)


def diamond_plate(h, w, seed, *, res=600, cells=9):
    """Industrial tread plate: raised short diagonal bars in a 4-way diamond tread on flat metal."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    bar1 = np.clip(np.sin((gx + gy) / s * np.pi * 2.0), 0, 1)
    bar2 = np.clip(np.sin((gx - gy) / s * np.pi * 2.0), 0, 1)
    # window the bars into short segments so they read as discrete treads, not continuous lines
    seg = (np.abs(np.sin(gx / s * np.pi)) * np.abs(np.sin(gy / s * np.pi))) ** 0.3
    return _up(_norm(np.maximum(bar1, bar2) * (0.4 + 0.6 * seg)), h, w)


def croc_hide(h, w, seed, *, res=600, cells=9):
    """Crocodile scutes: a jitter-warped grid of bulging square plates separated by deep grooves."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    jx = (_fbm(res, res, rng, 3, 4) - 0.5) * s * 0.55
    jy = (_fbm(res, res, rng, 3, 5) - 0.5) * s * 0.55
    u = ((gx + jx) % s) / s
    v = ((gy + jy) % s) / s
    d = np.maximum(np.abs(u - 0.5) * 2.0, np.abs(v - 0.5) * 2.0)   # chebyshev -> square plates
    plate = np.clip(1.0 - d, 0, 1) ** 0.5
    groove = 1.0 - np.clip((d - 0.8) * 5.0, 0, 1)
    return _up(_norm(plate * groove), h, w)


def tortoise_shell(h, w, seed, *, res=600, cells=22):
    """Tortoise shell: large Voronoi scute plates, each with concentric growth rings + dark seams."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    dist, idx = cKDTree(pts).query(q, k=2)
    F1 = dist[:, 0].reshape(res, res)
    F2 = dist[:, 1].reshape(res, res)
    idx0 = idx[:, 0].reshape(res, res)
    seam = np.clip(1.0 - _norm(F2 - F1) * 5.0, 0, 1)
    rings = 0.5 + 0.5 * np.sin(_norm(F1) * np.pi * 7.0)
    shade = rng.uniform(0.45, 0.95, int(cells)).astype(np.float32)[idx0]
    return _up(_norm(shade * (0.62 + 0.38 * rings) * (1.0 - seam * 0.85)), h, w)


def gila_bead(h, w, seed, *, res=600, cells=20):
    """Gila-monster beadwork: tightly hex-packed round beads with a mottled tone."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    row = np.floor(gy / s)
    off = (row % 2) * 0.5
    u = ((gx / s - off) % 1.0) - 0.5
    v = ((gy / s) % 1.0) - 0.5
    d = np.sqrt(u * u + v * v) / 0.5
    bead = np.clip(1.0 - d, 0, 1) ** 0.6
    mott = _fbm(res, res, rng, 3, 4)
    return _up(_norm(bead * (0.5 + 0.5 * mott)), h, w)


def stingray_pebble(h, w, seed, *, res=600, denticles=440):
    """Stingray shagreen: fine pebbled denticles + the signature bright central pearl spot."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(denticles), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, _ = cKDTree(pts).query(q, k=1)
    peb = np.clip(1.0 - _norm(d.reshape(res, res)) * 1.4, 0, 1)
    cx, cy = res * float(rng.uniform(0.4, 0.6)), res * float(rng.uniform(0.4, 0.6))
    r = np.hypot(gx.astype(np.float32) - cx, gy.astype(np.float32) - cy)
    spot = np.clip(1.0 - r / (res * 0.11), 0, 1) ** 2
    return _up(_norm(peb * 0.8 + spot), h, w)


def python_scales(h, w, seed, *, res=600, cells=26):
    """Python skin: a diamond scale lattice darkened by large irregular blotch markings."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    u = ((gx + gy) / s) % 1.0
    v = ((gx - gy) / s) % 1.0
    scale = np.clip(1.0 - np.maximum(np.abs(u - 0.5) * 2.0, np.abs(v - 0.5) * 2.0), 0, 1) ** 0.5
    blot = np.clip((_fbm(res, res, rng, 3, 3) - 0.5) * 4.0, 0, 1)   # dark python blotches
    return _up(_norm(scale * (0.4 + 0.6 * (1.0 - blot))), h, w)


def diamondback(h, w, seed, *, res=600, cells=7):
    """Diamondback dorsal: bold large diamond outlines + fills in a chain, slightly warped."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    wx = (_fbm(res, res, rng, 3, 4) - 0.5) * s * 0.3
    u = ((gx + wx) / s) % 1.0
    v = ((gy) / s) % 1.0
    dia = np.abs(u - 0.5) * 2.0 + np.abs(v - 0.5) * 2.0          # L1 diamond distance
    border = np.clip(1.0 - np.abs(dia - 0.7) * 6.0, 0, 1)
    fill = np.clip(0.7 - dia, 0, 1)
    bg = _fbm(res, res, rng, 3, 5) * 0.25
    return _up(_norm(border * 1.0 + fill * 0.55 + bg), h, w)


def tiger_stripes(h, w, seed, *, res=600, stripes=9):
    """Tiger stripes: parallel bands domain-warped into bold curved tapering slashes (markings dark)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    warp = (_fbm(res, res, rng, 4, 4) - 0.5) * res * 0.45
    stripe = np.abs(np.sin((gx + warp) / res * stripes * np.pi))
    brk = _fbm(res, res, rng, 3, 6)
    mark = np.clip((0.45 - stripe) * 4.0, 0, 1) * np.clip(brk * 1.6, 0, 1)   # dark slash markings
    return _up(_norm(1.0 - mark), h, w)


def circuitry(h, w, seed, *, res=600, gridn=24):
    """PCB circuit traces: orthogonal Manhattan random-walk tracks with pads/vias at the ends."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / gridn
    for _ in range(gridn * 3):
        px, py = int(rng.integers(0, gridn)) * s, int(rng.integers(0, gridn)) * s
        for _step in range(int(rng.integers(4, 12))):
            if rng.random() < 0.5:
                nx, ny = px + float(rng.choice([-1, 1])) * s, py
            else:
                nx, ny = px, py + float(rng.choice([-1, 1])) * s
            cv2.line(img, (int(px % res), int(py % res)), (int(nx % res), int(ny % res)), 0.8, 1, cv2.LINE_AA)
            px, py = nx % res, ny % res
        cv2.circle(img, (int(px), int(py)), 3, 1.0, -1, cv2.LINE_AA)   # pad/via
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.6)), h, w)


def code_rain(h, w, seed, *, res=600, cols=40):
    """Matrix code rain: columns of glyph-blocks fading behind a falling head."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / cols
    gh = s * 0.95
    for c in range(cols):
        x = int((c + 0.5) * s)
        head = float(rng.uniform(0, res))
        length = float(rng.uniform(0.2, 0.75) * res)
        yy = 0.0
        while yy < res:
            dist = (yy - head) % res
            b = float(np.clip(1.0 - dist / length, 0, 1))
            if b > 0.03 and rng.random() < 0.85:
                cv2.rectangle(img, (int(x - s * 0.3), int(yy)),
                              (int(x + s * 0.3), int(yy + gh * 0.6)), b, -1)
            yy += gh
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.5)), h, w)


def fiber_strands(h, w, seed, *, res=600, n=130):
    """Glowing fibre-optic strands: sparse curved bright filaments with a soft bloom."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(n)):
        x, y = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        ang = float(rng.uniform(0, 6.283))
        pts = [(x, y)]
        for _s in range(int(rng.integers(10, 22))):
            ang += float(rng.uniform(-0.16, 0.16))
            x += np.cos(ang) * 8.0
            y += np.sin(ang) * 8.0
            pts.append((x, y))
        cv2.polylines(img, [np.array(pts, np.int32)], False, float(rng.uniform(0.5, 1.0)), 1, cv2.LINE_AA)
    glow = cv2.GaussianBlur(img, (0, 0), 0.7) + cv2.GaussianBlur(img, (0, 0), 3.5) * 0.55
    return _up(_norm(glow), h, w)


def rivets(h, w, seed, *, res=600, gridn=16):
    """Riveted metal panel: a grid of domed rivets on brushed metal with panel seams."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / gridn
    u = (gx % s) / s - 0.5
    v = (gy % s) / s - 0.5
    rivet = np.clip(1.0 - np.sqrt(u * u + v * v) / 0.18, 0, 1) ** 0.6
    seam = ((np.abs(np.sin(gx / (s * 4) * np.pi)) < 0.06) | (np.abs(np.sin(gy / (s * 4) * np.pi)) < 0.06)).astype(np.float32)
    metal = 0.32 + 0.18 * _fbm(res, res, rng, 3, 5)
    return _up(_norm(metal + rivet * 0.7 + seam * 0.18), h, w)


def box_lattice(h, w, seed, *, res=600, cells=10):
    """Isometric strut lattice: three 60°-spaced line families -> a 3D box-girder cube grid."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    a = np.abs(np.sin(gx / s * np.pi))
    b = np.abs(np.sin((gx * 0.5 + gy * 0.8660254) / s * np.pi))
    c = np.abs(np.sin((gx * 0.5 - gy * 0.8660254) / s * np.pi))
    strut = np.maximum(np.maximum(a, b), c)
    return _up(_norm(strut ** 4.0), h, w)


def checker_warp(h, w, seed, *, res=600, cells=10):
    """Domain-warped checkerboard with a diagonal specular flash sweeping across it."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    wx = (_fbm(res, res, rng, 3, 4) - 0.5) * res * 0.1
    wy = (_fbm(res, res, rng, 3, 5) - 0.5) * res * 0.1
    s = res / cells
    chk = ((np.floor((gx + wx) / s) + np.floor((gy + wy) / s)) % 2).astype(np.float32)
    flash = _norm(np.abs(np.sin((gx + gy) / res * 8.0)))
    return _up(_norm(chk * 0.7 + 0.3 * flash + 0.08), h, w)


def static_burst(h, w, seed, *, res=600):
    """Radial electric static: angular high-frequency streaks bursting from a centre, over grain."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx, cy = res * float(rng.uniform(0.4, 0.6)), res * float(rng.uniform(0.4, 0.6))
    ang = np.arctan2(gy - cy, gx - cx)
    rad = np.hypot(gy - cy, gx - cx) / res
    noise = _fbm(res, res, rng, 6, 2)
    streak = np.abs(np.sin(ang * 60.0 + noise * 20.0))
    burst = streak * np.clip(1.2 - rad, 0, 1) + _fbm(res, res, rng, 7, 1) * 0.3
    return _up(_norm(burst), h, w)


def basalt_columns(h, w, seed, *, res=600, cells=40):
    """Columnar basalt (Giant's Causeway, top-down): polygonal column tops, beveled, dark fractures."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, idx = cKDTree(pts).query(q, k=2)
    F1 = d[:, 0].reshape(res, res)
    F2 = d[:, 1].reshape(res, res)
    idx0 = idx[:, 0].reshape(res, res)
    bevel = np.clip(1.0 - _norm(F1) * 1.3, 0, 1)
    frac = np.clip(1.0 - _norm(F2 - F1) * 5.0, 0, 1)
    shade = rng.uniform(0.5, 0.92, int(cells)).astype(np.float32)[idx0]
    return _up(_norm(shade * bevel * (1.0 - frac * 0.9)), h, w)


def frost_feather(h, w, seed, *, res=600, feathers=15):
    """Feather frost: scattered feather fans — a central rachis with side barbs tapering off, at
    every orientation (UV-agnostic)."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(feathers)):
        cx, cy = float(rng.uniform(0.1, 0.9) * res), float(rng.uniform(0.1, 0.9) * res)
        ang = float(rng.uniform(0, 6.283))
        L = float(rng.uniform(0.2, 0.46) * res)
        ex, ey = cx + np.cos(ang) * L, cy + np.sin(ang) * L
        cv2.line(img, (int(cx), int(cy)), (int(ex), int(ey)), 0.9, 1, cv2.LINE_AA)
        nb = max(4, int(L / 7))
        for i in range(nb):
            t = i / nb
            bx, by = cx + np.cos(ang) * L * t, cy + np.sin(ang) * L * t
            blen = (1.0 - t) * L * 0.38
            for side in (1.0, -1.0):
                ba = ang + side * 1.0
                cv2.line(img, (int(bx), int(by)),
                         (int(bx + np.cos(ba) * blen), int(by + np.sin(ba) * blen)), 0.7, 1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.6)), h, w)


def frost_lace(h, w, seed, *, res=600, seeds=10):
    """Window-frost fern dendrites: recursive isotropic branching crystals (no central shaft)."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)

    def fern(x, y, ang, length, depth):
        if depth <= 0 or length < 3.0:
            return
        ex, ey = x + np.cos(ang) * length, y + np.sin(ang) * length
        cv2.line(img, (int(x), int(y)), (int(ex), int(ey)), float(0.35 + 0.12 * depth), 1, cv2.LINE_AA)
        for i in range(1, 4):
            t = i / 4.0
            bx, by = x + (ex - x) * t, y + (ey - y) * t
            for side in (1.0, -1.0):
                fern(bx, by, ang + side * float(rng.uniform(0.5, 0.9)), length * 0.45, depth - 1)
        fern(ex, ey, ang + float(rng.uniform(-0.2, 0.2)), length * 0.68, depth - 1)

    for _ in range(int(seeds)):
        fern(float(rng.uniform(0, res)), float(rng.uniform(0, res)),
             float(rng.uniform(0, 6.283)), float(rng.uniform(42, 82)), 4)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.5)), h, w)


def glacier_core(h, w, seed, *, res=600, facets=30):
    """Glacier ice: a few large flat mirror facets split by thin deep crevasses."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(facets), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, idx = cKDTree(pts).query(q, k=2)
    F1 = d[:, 0].reshape(res, res)
    F2 = d[:, 1].reshape(res, res)
    i0 = idx[:, 0].reshape(res, res)
    crev = np.clip(1.0 - _norm(F2 - F1) * 8.0, 0, 1)
    facet = rng.uniform(0.4, 0.92, int(facets)).astype(np.float32)[i0]
    ice = 0.72 * facet + 0.2 * _fbm(res, res, rng, 4, 5)
    return _up(_norm(ice * (1.0 - crev * 0.95)), h, w)


def geode_bands(h, w, seed, *, res=600, cores=5):
    """Agate geode: concentric growth bands around several seed cores + a druzy sparkle core."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cores), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, idx = cKDTree(pts).query(q, k=1)
    F1 = _norm(d.reshape(res, res))
    band = 0.5 + 0.5 * np.sin(F1 * np.pi * 16.0 + float(rng.uniform(0, 6.28)))
    core = np.clip(1.0 - F1 * 4.0, 0, 1)
    spark = (_fbm(res, res, rng, 7, 1) > 0.7).astype(np.float32) * core
    return _up(_norm(band * 0.7 + core * 0.4 + spark * 0.5), h, w)


def ebru(h, w, seed, *, res=600):
    """Ebru (Turkish paper marbling): a stone field raked by crossed combs into swirled bands."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    base = _fbm(res, res, rng, 4, 4).astype(np.float32)
    rake = np.sin(gy / res * np.pi * 8.0) * res * 0.04
    warped = cv2.remap(base, np.clip(gx + rake, 0, res - 1), gy, cv2.INTER_LINEAR)
    rake2 = np.sin(gx / res * np.pi * 6.0) * res * 0.03
    warped = cv2.remap(warped, gx, np.clip(gy + rake2, 0, res - 1), cv2.INTER_LINEAR)
    return _up(_norm(0.5 + 0.5 * np.sin(_norm(warped) * np.pi * 7.0)), h, w)


def mudcrack(h, w, seed, *, res=600, cells=45):
    """Dried mud: wide irregular plates that dome up, separated by dark shrinkage cracks (no glow)."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, idx = cKDTree(pts).query(q, k=2)
    F1 = d[:, 0].reshape(res, res)
    F2 = d[:, 1].reshape(res, res)
    i0 = idx[:, 0].reshape(res, res)
    crack = np.clip(1.0 - _norm(F2 - F1) * 6.0, 0, 1)
    plate = rng.uniform(0.55, 0.95, int(cells)).astype(np.float32)[i0]
    dome = 1.0 - _norm(F1) * 0.5
    return _up(_norm(plate * dome * (1.0 - crack)), h, w)


def damascus(h, w, seed, *, res=600, layers=22):
    """Damascus steel: folded watering — parallel layer bands domain-warped by the forge folds."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    warp = (_fbm(res, res, rng, 5, 3) - 0.5) * res * 0.35
    layered = np.abs(np.sin((gy + warp) / res * layers * np.pi))
    warp2 = (_fbm(res, res, rng, 4, 4) - 0.5) * res * 0.2
    layered2 = np.abs(np.sin((gx + warp2) / res * layers * 0.5 * np.pi))
    return _up(_norm(layered * 0.7 + layered2 * 0.3), h, w)


def topo(h, w, seed, *, res=600, levels=18):
    """Topographic contour map: iso-contour lines of a height field + faint elevation shading."""
    rng = _rng(seed)
    height = _fbm(res, res, rng, 5, 4).astype(np.float32)
    q = height * levels
    contour = np.abs(q - np.round(q))
    lines = np.clip(1.0 - contour * levels * 0.5, 0, 1)
    return _up(_norm(lines * 0.85 + height * 0.2), h, w)


def river_delta(h, w, seed, *, res=600, rivers=4):
    """Braided river delta: trunks entering from the edges and splitting into tapering
    distributary channels (bright water on silt)."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)

    def branch(x, y, ang, width, length, depth):
        if depth <= 0 or width < 1.0:
            return
        for _s in range(max(1, int(length / 6))):
            ang += float(rng.uniform(-0.12, 0.12))
            nx, ny = x + np.cos(ang) * 6.0, y + np.sin(ang) * 6.0
            cv2.line(img, (int(x), int(y)), (int(nx), int(ny)), 0.9, max(1, int(width)), cv2.LINE_AA)
            x, y = nx, ny
        for _ in range(int(rng.integers(2, 4))):
            branch(x, y, ang + float(rng.uniform(-0.7, 0.7)), width * 0.6, length * 0.7, depth - 1)

    for _ in range(int(rivers)):
        e = int(rng.integers(0, 4))
        if e == 0:
            x, y, a = float(rng.uniform(0, res)), 0.0, 1.5
        elif e == 1:
            x, y, a = float(rng.uniform(0, res)), float(res), -1.5
        elif e == 2:
            x, y, a = 0.0, float(rng.uniform(0, res)), 0.0
        else:
            x, y, a = float(res), float(rng.uniform(0, res)), 3.14
        branch(x, y, a + float(rng.uniform(-0.5, 0.5)), float(rng.uniform(5, 9)), float(rng.uniform(0.5, 0.8) * res), 4)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 1.0)), h, w)


def tide_glass(h, w, seed, *, res=600, sources=5):
    """Glassy tide ripples: overlapping smooth concentric wave-fronts seen through rippled glass."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    for _ in range(int(sources)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        k = float(rng.uniform(0.04, 0.09))
        acc += np.sin(np.hypot(gx - cx, gy - cy) * k + float(rng.uniform(0, 6.28)))
    field = _norm(acc)
    return _up(_norm(0.5 + 0.5 * np.sin(field * np.pi * 2.0)), h, w)


def great_wave(h, w, seed, *, res=600):
    """Cresting wave: parallel swells curled by a swirl + bright foam stipple at the crests."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx, cy = res * 0.5, res * 0.5
    ang = np.arctan2(gy - cy, gx - cx)
    rad = np.hypot(gy - cy, gx - cx) / res
    swirl = np.sin(ang * 2.0 + rad * 10.0)
    warp = (_fbm(res, res, rng, 4, 4) - 0.5) * res * 0.3
    bands = np.sin((gy + warp) / res * 8.0 * np.pi + swirl * 2.0)
    wave = _norm(bands)
    foam = (_fbm(res, res, rng, 7, 1) > 0.62).astype(np.float32) * np.clip(wave - 0.5, 0, 1) * 2.0
    return _up(_norm(wave * 0.7 + foam), h, w)


def petals(h, w, seed, *, res=600, n=95):
    """Drifting flower petals: soft elliptical petals scattered at every angle and size."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(n)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        sz = float(rng.uniform(8, 26))
        cv2.ellipse(img, (int(cx), int(cy)), (int(sz), int(sz * 0.45)),
                    float(rng.uniform(0, 360)), 0, 360, float(rng.uniform(0.4, 1.0)), -1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 1.2)), h, w)


def wing_venation(h, w, seed, *, res=600, cells=95):
    """Dragonfly wing: a network of thin bright veins bounding elongated translucent cells."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel() * 0.6], 1).astype(np.float32)   # x-stretch -> elongated cells
    pts2 = pts.copy()
    pts2[:, 1] *= 0.6
    d, _ = cKDTree(pts2).query(q, k=2)
    F1 = d[:, 0].reshape(res, res)
    F2 = d[:, 1].reshape(res, res)
    vein = np.clip(1.0 - _norm(F2 - F1) * 6.0, 0, 1)
    membrane = 0.25 + 0.2 * _fbm(res, res, rng, 3, 5)
    return _up(_norm(vein * 0.9 + membrane * 0.4), h, w)


def octo_suckers(h, w, seed, *, res=600, cols=8):
    """Octopus arm suckers: staggered rows of concentric sucker discs (outer ring + raised cup)."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / cols
    iy = 0
    for cy in np.arange(s * 0.5, res, s * 0.8):
        off = (iy % 2) * s * 0.5
        for cx in np.arange(off, res, s):
            r = int(s * 0.4 * float(rng.uniform(0.7, 1.0)))
            if r < 2:
                continue
            cv2.circle(img, (int(cx), int(cy)), r, 0.8, 2, cv2.LINE_AA)
            cv2.circle(img, (int(cx), int(cy)), int(r * 0.55), 1.0, -1, cv2.LINE_AA)
            cv2.circle(img, (int(cx), int(cy)), int(r * 0.55), 0.3, 2, cv2.LINE_AA)
        iy += 1
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.6)), h, w)


def eyes(h, w, seed, *, res=600, n=62):
    """A field of watching eyes: scattered concentric eye-spots — bright iris, dark pupil, outer ring."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(n)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        r = float(rng.uniform(12, 30))
        cv2.circle(img, (int(cx), int(cy)), int(r), 0.5, 2, cv2.LINE_AA)
        cv2.circle(img, (int(cx), int(cy)), int(r * 0.7), 0.9, -1, cv2.LINE_AA)
        cv2.circle(img, (int(cx), int(cy)), int(r * 0.34), 0.05, -1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.6) + _fbm(res, res, rng, 4, 4) * 0.15), h, w)


def orbs(h, w, seed, *, res=600, n=22):
    """Will-o'-wisp witchlight: drifting soft glowing orbs trailing fading wisps."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(n)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        r = float(rng.uniform(0.03, 0.09) * res)
        img += np.clip(1.0 - np.hypot(gx - cx, gy - cy) / r, 0, 1) ** 2
        ang = float(rng.uniform(0, 6.28))
        for t in range(1, 8):
            tx, ty = cx - np.cos(ang) * t * r * 0.5, cy - np.sin(ang) * t * r * 0.5
            img += np.clip(1.0 - np.hypot(gx - tx, gy - ty) / (r * 0.4 * (1.0 - t / 10.0)), 0, 1) * 0.28
    return _up(_norm(img), h, w)


def rope(h, w, seed, *, res=600, coils=9):
    """Twisted rope: rows of round rope laid with a strong diagonal 3-strand twist lay."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    warp = (_fbm(res, res, rng, 3, 4) - 0.5) * res * 0.16
    band = (gy + warp) / (res / coils)
    within = np.abs((band % 1.0) - 0.5) * 2.0
    rope_round = np.clip(1.0 - within, 0, 1) ** 0.6
    twist = 0.5 + 0.5 * np.sin((gx * 2.0 + (gy + warp)) / res * coils * 6.283)
    return _up(_norm(rope_round * (0.5 + 0.5 * twist)), h, w)


def tessellation(h, w, seed, *, res=600, cells=8):
    """Interlocking rotated-square tessellation (Escher-ish pinwheel) with shaded tiles + seams."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / cells
    for i in range(-1, cells + 1):
        for j in range(-1, cells + 1):
            cx, cy = (i + 0.5) * s, (j + 0.5) * s
            ang = ((i + j) % 2) * 45.0 + 20.0
            rect = cv2.boxPoints(((cx, cy), (s * 0.96, s * 0.96), ang)).astype(np.int32)
            shade = 0.4 + 0.5 * (((i * 3 + j) % 3) / 2.0)
            cv2.fillConvexPoly(img, rect, float(shade))
            cv2.polylines(img, [rect], True, 1.0, 1, cv2.LINE_AA)
    return _up(_norm(img), h, w)


def maze(h, w, seed, *, res=600, cells=24):
    """A true orthogonal labyrinth: recursive-backtracker maze, corridors carved bright."""
    rng = _rng(seed)
    n = int(cells)
    visited = np.zeros((n, n), bool)
    img = np.zeros((res, res), np.float32)
    cs = res / n
    stack = [(0, 0)]
    visited[0, 0] = True

    def px(cx, cy):
        return int((cx + 0.5) * cs), int((cy + 0.5) * cs)

    while stack:
        x, y = stack[-1]
        nbrs = [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if 0 <= x + dx < n and 0 <= y + dy < n and not visited[y + dy, x + dx]]
        if nbrs:
            nx, ny = nbrs[int(rng.integers(0, len(nbrs)))]
            cv2.line(img, px(x, y), px(nx, ny), 1.0, max(2, int(cs * 0.35)), cv2.LINE_AA)
            visited[ny, nx] = True
            stack.append((nx, ny))
        else:
            stack.pop()
    return _up(_norm(img), h, w)


def cage(h, w, seed, *, res=600, rings=20):
    """Gyroscope cage: a tangle of interlocking great-circle ellipse rings at varied centres."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(rings)):
        ccx, ccy = float(rng.uniform(0.2, 0.8) * res), float(rng.uniform(0.2, 0.8) * res)
        a = int(rng.uniform(0.18, 0.4) * res)
        b = int(a * float(rng.uniform(0.18, 1.0)))
        cv2.ellipse(img, (int(ccx), int(ccy)), (a, b), float(rng.uniform(0, 180)),
                    0, 360, float(rng.uniform(0.5, 1.0)), 1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.6)), h, w)


def dragon_scales_3d(h, w, seed, *, res=600, rows=12):
    """Dragon scales: overlapping 3D-bulging scallop scales with a centre keel ridge (not flat arcs)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / rows
    row = np.floor(gy / s)
    off = (row % 2) * 0.5
    u = ((gx / s - off) % 1.0) - 0.5
    v = (gy / s) % 1.0
    d = np.sqrt(u * u * 4.0 + (v - 0.2) ** 2)
    scale = np.clip(1.0 - d * 1.5, 0, 1) ** 0.5
    keel = np.clip(1.0 - np.abs(u) * 8.0, 0, 1) * np.clip(v, 0, 1) * 0.4
    return _up(_norm(scale + keel), h, w)


def schwarz_surface(h, w, seed, *, res=600, scale=None):
    """Slice of a Schwarz-P triply-periodic minimal surface (cos x + cos y + cos z) — a DIFFERENT
    TPMS lattice from the gyroid."""
    rng = _rng(seed)
    scale = float(rng.uniform(4.0, 7.0)) if scale is None else scale
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    x = gx / res * scale * 6.283
    y = gy / res * scale * 6.283
    z = float(rng.uniform(0, 6.283)) + (_fbm(res, res, rng, 3, 3) - 0.5) * 2.0
    p = np.cos(x) + np.cos(y) + np.cos(z)
    return _up(_norm(np.abs(p)), h, w)


def penrose_rhombus(h, w, seed, *, res=720, lines=8):
    """Filled Penrose-style aperiodic rhombus tiles (pentagrid parities -> shaded tiles + seams),
    distinct from the pentagrid RIBBON look."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    x = gx / res - 0.5
    y = gy / res - 0.5
    off = rng.uniform(0, 1, 5)
    acc = np.zeros((res, res), np.float32)
    for k in range(5):
        ang = 2 * np.pi * k / 5 + 0.1
        proj = (x * np.cos(ang) + y * np.sin(ang)) * lines + off[k]
        acc += np.floor(proj) % 2
    field = _norm(np.sin(acc * 1.3))
    edge = _norm(np.abs(cv2.Laplacian(field, cv2.CV_32F)))
    return _up(_norm(field * 0.7 + edge * 0.5), h, w)


def plasma_drift(h, w, seed, *, res=512, cores=6):
    """Plasma drift: several plasma-ball cores throwing radial ion filaments with glowing centres."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    field = np.zeros((res, res), np.float32)
    for _ in range(int(cores)):
        cx, cy = float(rng.uniform(0.15, 0.85) * res), float(rng.uniform(0.15, 0.85) * res)
        ang = np.arctan2(gy - cy, gx - cx)
        rad = np.hypot(gy - cy, gx - cx)
        noise = _fbm(res, res, rng, 5, 3)
        fil = np.abs(np.sin(ang * float(rng.integers(8, 16)) + noise * 12.0))
        glow = np.clip(1.0 - rad / (res * 0.4), 0, 1)
        field += fil * glow + glow ** 3 * 1.5
    return _up(_norm(field), h, w)


def veils(h, w, seed, *, res=512):
    """Wraith veils: a soft low-frequency field curl-draped into translucent sheets with bright
    fold lines — ghostly hanging fabric."""
    rng = _rng(seed)
    base = _fbm(res, res, rng, 3, 3).astype(np.float32)
    psi = _fbm(res, res, rng, 4, 4).astype(np.float32)
    gy, gx = np.gradient(psi)
    ys, xs = np.mgrid[0:res, 0:res].astype(np.float32)
    drape = cv2.remap(base, np.clip(xs + gy * res * 0.2, 0, res - 1),
                      np.clip(ys - gx * res * 0.2, 0, res - 1), cv2.INTER_LINEAR)
    folds = _norm(np.abs(cv2.Laplacian(cv2.GaussianBlur(drape, (0, 0), 2.0), cv2.CV_32F)))
    return _up(_norm(drape * 0.5 + folds * 0.7), h, w)


def moth_dust(h, w, seed, *, res=512, specks=3200):
    """Moth-wing dust: a powdery scatter of wing-scale specks with a few staring eyespots."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    xs = rng.integers(0, res, int(specks))
    ys = rng.integers(0, res, int(specks))
    img[ys, xs] = rng.uniform(0.3, 1.0, int(specks)).astype(np.float32)
    img = cv2.GaussianBlur(img, (0, 0), 0.8)
    for _ in range(int(rng.integers(2, 4))):
        cx, cy = int(rng.uniform(0.2, 0.8) * res), int(rng.uniform(0.2, 0.8) * res)
        r = int(rng.uniform(0.06, 0.12) * res)
        cv2.circle(img, (cx, cy), r, 0.7, -1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), int(r * 0.5), 0.2, -1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), r, 0.9, 2, cv2.LINE_AA)
    return _up(_norm(img * 0.8 + _fbm(res, res, rng, 4, 4) * 0.3), h, w)


def night_tide(h, w, seed, *, res=512, sources=4):
    """Nocturnal tide: dark broad swells with sparse bright moonlight glints on the crests."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    for _ in range(int(sources)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        acc += np.sin(np.hypot(gx - cx, gy - cy) * float(rng.uniform(0.03, 0.06)) + float(rng.uniform(0, 6.28)))
    swell = _norm(acc)
    glint = (swell > 0.85).astype(np.float32) * np.clip((swell - 0.85) * 6.0, 0, 1)
    return _up(_norm(swell * 0.5 + glint * 0.8), h, w)


def static_crackle(h, w, seed, *, res=512, cells=120):
    """Static veins: a very fine Voronoi crackle web with bright spark nodes at the vertices."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, _ = cKDTree(pts).query(q, k=2)
    F1 = d[:, 0].reshape(res, res)
    F2 = d[:, 1].reshape(res, res)
    crack = np.clip(1.0 - _norm(F2 - F1) * 9.0, 0, 1)
    spark = cv2.GaussianBlur((crack > 0.5).astype(np.float32), (0, 0), 1.0) * crack
    return _up(_norm(crack * 0.9 + spark * 0.5), h, w)


def wind_streaks(h, w, seed, *, res=512):
    """Howling wind: white noise smeared by a directional motion blur then curl-warped into gusts."""
    rng = _rng(seed)
    noise = rng.standard_normal((res, res)).astype(np.float32)
    ang = float(rng.uniform(0, np.pi))
    k = 51
    kernel = np.zeros((k, k), np.float32)
    c = k // 2
    for t in range(k):
        x = int(c + (t - c) * np.cos(ang))
        y = int(c + (t - c) * np.sin(ang))
        if 0 <= x < k and 0 <= y < k:
            kernel[y, x] = 1.0
    kernel /= max(kernel.sum(), 1.0)
    streak = cv2.filter2D(noise, -1, kernel)
    psi = _fbm(res, res, rng, 3, 4).astype(np.float32)
    gyv, gxv = np.gradient(psi)
    ys, xs = np.mgrid[0:res, 0:res].astype(np.float32)
    streak = cv2.remap(streak, np.clip(xs + gyv * res * 0.1, 0, res - 1),
                       np.clip(ys - gxv * res * 0.1, 0, res - 1), cv2.INTER_LINEAR)
    return _up(_norm(streak), h, w)


def phantom_grid(h, w, seed, *, res=512, cells=14):
    """Phantom lattice: two incommensurate grids overlaid into a faint ghosting double-lattice."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s1 = res / cells
    s2 = res / (cells * 1.37)
    g1 = np.abs(np.sin(gx / s1 * np.pi)) * np.abs(np.sin(gy / s1 * np.pi))
    g2 = np.abs(np.sin((gx + s1 * 0.5) / s2 * np.pi)) * np.abs(np.sin((gy + s1 * 0.3) / s2 * np.pi))
    return _up(_norm(((1.0 - g1) * 0.5 + (1.0 - g2) * 0.5) ** 1.5), h, w)


def embers(h, w, seed, *, res=512, n=180):
    """Drifting embers: dense small glowing coals with short drift trails over a warm glow haze.
    Drawn with cv2 stamps (O(n)) + a blur for the bloom, so it stays well inside render budget."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(n)):
        cx, cy = int(rng.uniform(0, res)), int(rng.uniform(0, res))
        r = int(rng.uniform(2, 6))
        b = float(rng.uniform(0.4, 1.0))
        cv2.circle(img, (cx, cy), r, b, -1, cv2.LINE_AA)
        for t in range(1, 4):
            cv2.circle(img, (cx, int(cy + t * r * 0.9)), max(1, int(r * (1.0 - t * 0.2))), b * 0.25, -1, cv2.LINE_AA)
    core = cv2.GaussianBlur(img, (0, 0), 0.8)
    haze = cv2.GaussianBlur(img, (0, 0), 9.0) * 0.5
    return _up(_norm(core + haze), h, w)


def bokeh(h, w, seed, *, res=512, n=70):
    """Carnival bokeh: out-of-focus light discs with bright rims scattered through the night."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(n)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        r = float(rng.uniform(0.02, 0.10) * res)
        b = float(rng.uniform(0.3, 1.0))
        d = np.hypot(gx - cx, gy - cy)
        disc = np.clip((r - d) / r, 0, 1)
        ring = np.clip(1.0 - np.abs(d - r) / (r * 0.2), 0, 1) * 0.5
        img += disc * b * 0.5 + ring * b
    return _up(_norm(img), h, w)


def spiderweb(h, w, seed, *, res=512, webs=3):
    """Spider/widow web: radial spokes crossed by concentric capture threads (a braided lattice)."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(webs)):
        cx, cy = float(rng.uniform(0.2, 0.8) * res), float(rng.uniform(0.2, 0.8) * res)
        spokes = int(rng.integers(10, 16))
        R = float(rng.uniform(0.3, 0.5) * res)
        for s in range(spokes):
            a = 2 * np.pi * s / spokes
            cv2.line(img, (int(cx), int(cy)), (int(cx + np.cos(a) * R), int(cy + np.sin(a) * R)), 0.7, 1, cv2.LINE_AA)
        for rr in np.linspace(R * 0.12, R, 8):
            pts = [(cx + np.cos(2 * np.pi * s / spokes) * rr, cy + np.sin(2 * np.pi * s / spokes) * rr)
                   for s in range(spokes + 1)]
            cv2.polylines(img, [np.array(pts, np.int32)], False, 0.8, 1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.6)), h, w)


def oil_serpent(h, w, seed, *, res=512):
    """Oil-on-water serpent: serpentine warped bands shot through with thin-film iridescence."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    warp = (_fbm(res, res, rng, 3, 3) - 0.5) * res * 0.5
    serp = np.sin((gx + warp) / res * 5.0 * np.pi)
    psi = _fbm(res, res, rng, 4, 5)
    film = 0.5 + 0.5 * np.sin(psi * np.pi * 8.0 + serp * 3.0)
    return _up(_norm(np.abs(serp) * 0.5 + film * 0.6), h, w)


def guilloche(h, w, seed, *, res=512, reps=4):
    """Guilloché engine-turning: a grid of overlaid epicycloid rosettes (banknote / watch-dial)."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / reps
    ts = np.linspace(0, 2 * np.pi, 420)
    for i in range(reps):
        for j in range(reps):
            cx, cy = (i + 0.5) * s, (j + 0.5) * s
            R = s * 0.46
            r1 = float(rng.uniform(0.3, 0.5))
            k = int(rng.integers(5, 9))
            x = cx + R * ((1 - r1) * np.cos(ts) + r1 * np.cos((1 - r1) / r1 * ts * k))
            y = cy + R * ((1 - r1) * np.sin(ts) - r1 * np.sin((1 - r1) / r1 * ts * k))
            cv2.polylines(img, [np.stack([x, y], 1).astype(np.int32)], True, 0.9, 1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.5)), h, w)


def newton_rings(h, w, seed, *, res=512, halos=6):
    """Oil-film Newton's rings: overlapping sqrt-spaced interference halos -> petrol iridescence."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    for _ in range(int(halos)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        d = np.hypot(gx - cx, gy - cy)
        acc += np.sin(np.sqrt(d + 1.0) * float(rng.uniform(1.2, 2.0)))
    return _up(_norm(0.5 + 0.5 * np.sin(_norm(acc) * np.pi * 4.0)), h, w)


def starchart(h, w, seed, *, res=512, stars=130, lines=32):
    """Constellation star chart: scattered stars joined by faint constellation lines on a nebula."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    pts = rng.uniform(0, res, (int(stars), 2))
    tree = cKDTree(pts)
    for _ in range(int(lines)):
        a = int(rng.integers(0, stars))
        _, idx = tree.query(pts[a], k=3)
        b = int(idx[int(rng.integers(1, 3))])
        cv2.line(img, (int(pts[a][0]), int(pts[a][1])), (int(pts[b][0]), int(pts[b][1])), 0.35, 1, cv2.LINE_AA)
    for i in range(int(stars)):
        r = int(rng.choice([1, 1, 1, 2, 2, 3]))
        cv2.circle(img, (int(pts[i][0]), int(pts[i][1])), r, float(rng.uniform(0.6, 1.0)), -1, cv2.LINE_AA)
    return _up(_norm(img + _fbm(res, res, rng, 4, 3) * 0.12), h, w)


def serpent_scales(h, w, seed, *, res=512, rows=16):
    """Serpent scales: tight rows of pointed (chevron-tipped) overlapping scales with a keel."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / rows
    row = np.floor(gy / s)
    off = (row % 2) * 0.5
    u = ((gx / s - off) % 1.0) - 0.5
    v = (gy / s) % 1.0
    tip = np.abs(u) * 2.0 + np.clip(v - 0.5, 0, 1) * 1.5
    scale = np.clip(1.0 - tip, 0, 1) ** 0.7
    keel = np.clip(1.0 - np.abs(u) * 10.0, 0, 1) * v * 0.3
    return _up(_norm(scale + keel), h, w)


def nova(h, w, seed, *, res=512):
    """Nova burst: clean radial rays exploding from a bright central core flash."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx, cy = res * float(rng.uniform(0.4, 0.6)), res * float(rng.uniform(0.4, 0.6))
    ang = np.arctan2(gy - cy, gx - cx)
    rad = np.hypot(gy - cy, gx - cx) / res
    rays = np.abs(np.sin(ang * float(rng.integers(18, 30)))) ** 2
    core = np.clip(1.0 - rad * 2.5, 0, 1) ** 2
    return _up(_norm(rays * np.clip(1.0 - rad, 0, 1) + core * 1.5 + _fbm(res, res, rng, 5, 2) * 0.15), h, w)


def linear_moire(h, w, seed, *, res=512):
    """Linear moire: two slightly-rotated line gratings beating into phantom interference bands."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    a1 = float(rng.uniform(0, 0.3))
    a2 = a1 + float(rng.uniform(0.05, 0.15))
    k = float(rng.uniform(0.3, 0.5))
    g1 = np.sin((gx * np.cos(a1) + gy * np.sin(a1)) * k)
    g2 = np.sin((gx * np.cos(a2) + gy * np.sin(a2)) * k)
    return _up(_norm(g1 * g2), h, w)


def aurora_curtains(h, w, seed, *, res=512):
    """Aurora curtains: wavering vertical light sheets with downward thread streaks, fading up."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    warp = (_fbm(res, res, rng, 4, 3) - 0.5) * res * 0.3
    curtain = np.abs(np.sin((gx + warp) / res * 9.0 * np.pi))
    threads = 0.5 + 0.5 * np.sin(gy / res * 40.0 * np.pi + warp * 0.1)
    field = _norm(curtain ** 1.5 * (0.6 + 0.4 * threads))
    fade = np.clip(1.2 - gy / res, 0.3, 1.0)
    return _up(_norm(field * fade), h, w)


# ── FORGE-100 compositions: sweep an engine's field through a curl flow ───────
def _curl_warp(field, seed, res, amt=0.15):
    """Advect a scalar field along a divergence-free curl-noise flow (domain warp) -> a flowing
    version of any pattern. The compositional backbone of the FORGE flow-fusion finishes."""
    rng = _rng(seed)
    psi = _fbm(res, res, rng, 4, 5).astype(np.float32)
    gy, gx = np.gradient(psi)
    ys, xs = np.mgrid[0:res, 0:res].astype(np.float32)
    f = np.asarray(field, np.float32)
    if f.shape[:2] != (res, res):
        f = cv2.resize(f, (res, res), interpolation=cv2.INTER_LINEAR)
    return cv2.remap(f, np.clip(xs + gy * res * amt, 0, res - 1),
                     np.clip(ys - gx * res * amt, 0, res - 1), cv2.INTER_LINEAR)


def gyroid_flow(h, w, seed, *, res=560):
    return _up(_norm(_curl_warp(gyroid(res, res, seed), seed + 7, res, 0.16)), h, w)


def ridge_flow(h, w, seed, *, res=560):
    return _up(_norm(_curl_warp(ridged_terrain(res, res, seed), seed + 7, res, 0.18)), h, w)


def marble_flow(h, w, seed, *, res=560):
    return _up(_norm(_curl_warp(marble(res, res, seed), seed + 7, res, 0.16)), h, w)


def hex_flow(h, w, seed, *, res=560):
    return _up(_norm(_curl_warp(hexgrid(res, res, seed, cells=12, mode="filled"), seed + 7, res, 0.13)), h, w)


def chladni_flow(h, w, seed, *, res=560):
    return _up(_norm(_curl_warp(chladni(res, res, seed), seed + 7, res, 0.12)), h, w)


def silk_flow(h, w, seed, *, res=560):
    return _up(_norm(_curl_warp(spectral_silk(res, res, seed), seed + 7, res, 0.16)), h, w)


def quasi_flow(h, w, seed, *, res=560):
    return _up(_norm(_curl_warp(quasicrystal(res, res, seed, waves=9), seed + 7, res, 0.14)), h, w)


def lattice_flow(h, w, seed, *, res=560):
    return _up(_norm(_curl_warp(box_lattice(res, res, seed, cells=9), seed + 7, res, 0.15)), h, w)


# ── MULTI-HUE TRACED CELLS (owner 2026-06-17): cells filled from a 2-3 colour palette at varied
#    per-cell shades + a bright ignitable traced OUTLINE. Engines RETURN RGB (HxWx3) directly. ──
def colorize_cells(labels, base_rgb, palette, edge_rgb, *, shade_lo=0.40, shade_hi=0.96, seam=2):
    """Each region (label) gets a palette colour at a per-cell random shade; boundaries become a
    bright traced outline (edge_rgb). The outline's high contrast = what fracture_spec ignites; the
    multi-hue interiors = the colours that fire to life on the car. Returns float RGB 0..1 HxWx3."""
    li = np.asarray(labels, np.int64)
    P = max(1, len(palette))
    pal = np.array(palette, np.float32) / 255.0
    hsh = (li * 2654435761) & 0x7FFFFFFF
    idx = (hsh % P).astype(np.int64)
    shade = shade_lo + (shade_hi - shade_lo) * (((hsh // P) % 1000).astype(np.float32) / 1000.0)
    out = pal[idx] * shade[..., None]                      # multi-hue cell bodies
    bnd = ((li != np.roll(li, 1, 0)) | (li != np.roll(li, 1, 1))
           | (li != np.roll(li, -1, 0)) | (li != np.roll(li, -1, 1)))
    if seam > 1:
        bnd = cv2.dilate(bnd.astype(np.uint8), np.ones((seam, seam), np.uint8)).astype(bool)
    out[bnd] = np.array(edge_rgb, np.float32) / 255.0      # bright traced outline
    return np.clip(out, 0.0, 1.0)


def _voronoi_labels(res, seed, cells, p=2):
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    _, i = cKDTree(pts).query(q, k=1, p=p)
    return i.reshape(res, res)


def _hex_labels(res, cells):
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    q = (gx * (np.sqrt(3) / 3.0) - gy / 3.0) / s
    r = (gy * 2.0 / 3.0) / s
    x, z = q, r
    y = -x - z
    rx, ry, rz = np.round(x), np.round(y), np.round(z)
    dx, dy, dz = np.abs(rx - x), np.abs(ry - y), np.abs(rz - z)
    c1 = (dx > dy) & (dx > dz)
    rx = np.where(c1, -ry - rz, rx)
    c2 = (~c1) & (dy > dz)
    rz = np.where(c2, -rx - ry, rz)
    return (rx.astype(np.int64) * 73856093) ^ (rz.astype(np.int64) * 19349663)


def prism_glass(h, w, seed, *, res=720, cells=55, palette=None, edge=(185, 235, 255)):
    """Stained-glass Voronoi panes — multi-hue cells behind a bright ignitable leading."""
    palette = palette or [(120, 40, 165), (28, 140, 95), (38, 90, 205)]
    return _up(colorize_cells(_voronoi_labels(res, seed, cells), (6, 7, 10), palette, edge), h, w)


def spectral_hive(h, w, seed, *, res=720, cells=16, palette=None, edge=(200, 240, 255)):
    """Hex hive cells in multi-hue shades, each ringed by a bright ignitable rim."""
    palette = palette or [(30, 150, 140), (150, 50, 160), (190, 140, 30)]
    return _up(colorize_cells(_hex_labels(res, cells), (6, 7, 9), palette, edge, seam=3), h, w)


def prism_shatter(h, w, seed, *, res=720, cells=85, palette=None, edge=(225, 240, 255)):
    """Angular shattered shards (Chebyshev Voronoi) in multi-hue shades; fault-lines ignite bright."""
    palette = palette or [(40, 90, 205), (160, 40, 150), (30, 150, 150)]
    return _up(colorize_cells(_voronoi_labels(res, seed, cells, p=np.inf), (5, 6, 11), palette, edge), h, w)


def mosaic_drift(h, w, seed, *, res=720, cells=70, palette=None, edge=(255, 225, 130)):
    """A curl-drifted mosaic of multi-hue tiles seamed by a glowing lattice."""
    palette = palette or [(40, 140, 70), (175, 120, 30), (195, 70, 30)]
    lab = _voronoi_labels(res, seed, cells).astype(np.float32)
    rng = _rng(seed + 7)
    psi = _fbm(res, res, rng, 4, 5).astype(np.float32)
    gyv, gxv = np.gradient(psi)
    ys, xs = np.mgrid[0:res, 0:res].astype(np.float32)
    labw = cv2.remap(lab, np.clip(xs + gyv * res * 0.12, 0, res - 1),
                     np.clip(ys - gxv * res * 0.12, 0, res - 1), cv2.INTER_NEAREST)
    return _up(colorize_cells(labw.astype(np.int64), (8, 6, 3), palette, edge), h, w)


def _wedge_labels(res, sectors, rings, seed):
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx, cy = res * 0.5, res * 0.5
    ang = (np.arctan2(gy - cy, gx - cx) + np.pi) / (2 * np.pi)
    rad = np.hypot(gy - cy, gx - cx) / (res * 0.72)
    si = np.floor(ang * sectors).astype(np.int64)
    ri = np.clip(np.floor(rad * rings), 0, rings - 1).astype(np.int64)
    si = (si + ri * 2) % sectors           # twist each ring -> shattered wheel
    return si * rings + ri


def spectra_wheel(h, w, seed, *, res=720, sectors=28, rings=7, palette=None, edge=(245, 245, 255)):
    """Shattered colour-wheel — radial wedge sectors, multi-hue, bright ignitable spokes/rings."""
    palette = palette or [(200, 40, 140), (30, 160, 180), (220, 160, 30)]
    return _up(colorize_cells(_wedge_labels(res, sectors, rings, seed), (6, 6, 9), palette, edge, seam=2), h, w)


def _brick_labels(res, cols, seed):
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cols
    ry = np.floor(gy / s).astype(np.int64)
    cxi = np.floor(gx / s + (ry % 2) * 0.5).astype(np.int64)
    return ry * 100003 + cxi


def brickwork_prism(h, w, seed, *, res=720, cols=14, palette=None, edge=(255, 225, 150)):
    """Offset brick courses, each brick a multi-hue tone, glowing mortar that ignites."""
    palette = palette or [(190, 90, 40), (160, 130, 40), (40, 120, 120)]
    return _up(colorize_cells(_brick_labels(res, cols, seed), (7, 5, 3), palette, edge, seam=3), h, w)


def _stagger_labels(res, rows, seed):
    from scipy.spatial import cKDTree
    s = res / rows
    pts = []
    iy = 0
    cy = s * 0.5
    while cy <= res + s:
        off = (iy % 2) * 0.5 * s
        cx = off
        while cx <= res + s:
            pts.append((cy, cx))
            cx += s
        cy += s
        iy += 1
    pts = np.array(pts, np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    _, i = cKDTree(pts).query(q, k=1)
    return i.reshape(res, res)


def scale_prism(h, w, seed, *, res=720, rows=15, palette=None, edge=(210, 245, 255)):
    """Staggered rounded scale/pebble cells, multi-hue, bright ignitable rims."""
    palette = palette or [(40, 150, 120), (90, 60, 170), (180, 110, 40)]
    return _up(colorize_cells(_stagger_labels(res, rows, seed), (5, 8, 8), palette, edge, seam=2), h, w)


# ── F2 cellular fusions (scalar fields -> colorize) ──
def wovencell(h, w, seed, *, res=600):
    return _up(_norm(worley(res, res, seed, cells=120, kind="cells") * (0.5 + 0.5 * gabor_weave(res, res, seed + 3))), h, w)


def geode_facet(h, w, seed, *, res=600):
    return _up(_norm(0.6 * crystal_facets(res, res, seed, cells=70) + 0.5 * marble(res, res, seed + 3)), h, w)


def shardfield(h, w, seed, *, res=600, cells=140):
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, _ = cKDTree(pts).query(q, k=2, p=np.inf)
    F1 = d[:, 0].reshape(res, res)
    F2 = d[:, 1].reshape(res, res)
    return _up(np.clip(1.0 - _norm(F2 - F1) * 5.0, 0, 1), h, w)


def cellwave(h, w, seed, *, res=600):
    return _up(_norm(worley(res, res, seed, cells=90, kind="cells") * (0.4 + 0.6 * interference(res, res, seed + 3))), h, w)


def resonant_cells(h, w, seed, *, res=600):
    return _up(_norm(0.5 * chladni(res, res, seed) + 0.6 * worley(res, res, seed + 3, cells=80, kind="cracks")), h, w)


# ── more multi-hue traced-cell label structures ──
def _ring_labels(res, rings, sectors, seed):
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx, cy = res * 0.5, res * 0.5
    rad = np.hypot(gy - cy, gx - cx) / (res * 0.72)
    ang = (np.arctan2(gy - cy, gx - cx) + np.pi) / (2 * np.pi)
    ri = np.clip(np.floor(rad * rings), 0, rings).astype(np.int64)
    si = np.floor(ang * sectors).astype(np.int64)
    return ri * 1000 + (si + ri) % sectors


def aura_rings(h, w, seed, *, res=720, rings=14, sectors=10, palette=None, edge=(250, 245, 255)):
    """Concentric ring bands split into rotating sectors, multi-hue, bright ignitable ring-lines."""
    palette = palette or [(210, 140, 30), (190, 50, 90), (80, 60, 180)]
    return _up(colorize_cells(_ring_labels(res, rings, sectors, seed), (6, 6, 9), palette, edge, seam=2), h, w)


def _triangle_labels(res, cells):
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    u, v = gx / s, gy / s
    cu, cv = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
    tri = ((u - cu) + (v - cv) > 1.0).astype(np.int64)
    return (cu * 100003 + cv) * 2 + tri


def trihedra(h, w, seed, *, res=720, cells=14, palette=None, edge=(230, 245, 255)):
    """Triangular tiling, multi-hue triangles, bright ignitable edges."""
    palette = palette or [(30, 160, 170), (150, 200, 40), (180, 40, 150)]
    return _up(colorize_cells(_triangle_labels(res, cells), (5, 6, 9), palette, edge, seam=2), h, w)


def _spiral_labels(res, arms, twist, seed):
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx, cy = res * 0.5, res * 0.5
    ang = np.arctan2(gy - cy, gx - cx)
    rad = np.hypot(gy - cy, gx - cx) / res
    return np.floor(ang / (2 * np.pi) * arms + rad * twist).astype(np.int64)


def spiral_prism(h, w, seed, *, res=720, arms=9, twist=8, palette=None, edge=(245, 240, 255)):
    """Logarithmic-spiral arms, multi-hue, bright ignitable spiral seams."""
    palette = palette or [(30, 150, 140), (110, 60, 180), (200, 130, 40)]
    return _up(colorize_cells(_spiral_labels(res, arms, twist, seed), (5, 7, 9), palette, edge, seam=2), h, w)


# ── F3 wave / optical fusions (scalar) ──
def holo_grating(h, w, seed, *, res=600, gratings=5):
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    for _ in range(int(gratings)):
        a = float(rng.uniform(0, np.pi))
        f = float(rng.uniform(20, 60))
        acc += np.sin((gx * np.cos(a) + gy * np.sin(a)) / res * f * 6.283 + float(rng.uniform(0, 6.28)))
    return _up(_norm(np.abs(acc)), h, w)


def newton_bloom(h, w, seed, *, res=560):
    return _up(_norm(_curl_warp(newton_rings(res, res, seed), seed + 7, res, 0.14)), h, w)


def standing_field(h, w, seed, *, res=600):
    return _up(_norm(chladni(res, res, seed) * (0.4 + 0.6 * interference(res, res, seed + 3))), h, w)


def moire_vortex(h, w, seed, *, res=600):
    return _up(_norm(moire(res, res, seed) * (0.4 + 0.6 * spiral_waves(res, res, seed + 3, vortices=3))), h, w)


def caustic_lace(h, w, seed, *, res=600):
    return _up(_norm(caustics(res, res, seed) * (0.5 + 0.5 * worley(res, res, seed + 3, cells=80, kind="cells"))), h, w)


# ── F4 · optical / iridescent fusions + 3 new multi-hue traced-cell structures ──
def _thinfilm(res, seed, freq=6.0):
    """Thin-film (oil-on-water) interference: a smooth height field -> multi-wavelength phase beats,
    giving fine iridescent banding. Returned as a scalar intensity for colorize()."""
    rng = _rng(seed)
    hh = _fbm(res, res, rng, 4, 5).astype(np.float32)
    ph = hh * float(freq) * 6.283185
    val = (np.sin(ph) + np.sin(ph * 1.21) + np.sin(ph * 1.47)) / 3.0
    return _norm(np.abs(val))


def oilfilm_weave(h, w, seed, *, res=600):
    """Thin-film iridescence rippling through a woven Gabor thread field — petrol-on-silk."""
    return _up(_norm(_thinfilm(res, seed, 7.0) * (0.45 + 0.55 * gabor_weave(res, res, seed + 5))), h, w)


def dichroic_drift(h, w, seed, *, res=600):
    """Thin-film dichroic bands advected by a curl flow — a colour-shifting drifting sheen."""
    return _up(_norm(_curl_warp(_thinfilm(res, seed, 5.0), seed + 7, res, 0.14)), h, w)


def prism_facet(h, w, seed, *, res=600):
    """Crystal facets lit by plane-wave interference — a faceted prism scattering spectral glints."""
    return _up(_norm(crystal_facets(res, res, seed, cells=80) * (0.4 + 0.6 * interference(res, res, seed + 3))), h, w)


def peacock_optic(h, w, seed, *, res=600):
    """Newton-ring ocelli swept through a vortex field — packed peacock eyes."""
    return _up(_norm(newton_rings(res, res, seed, halos=10) * (0.5 + 0.5 * spiral_waves(res, res, seed + 3, vortices=5))), h, w)


def thinfilm_ridge(h, w, seed, *, res=600):
    """Thin-film spectral bands draped over ridged terrain — iridescent mountain ridges."""
    return _up(_norm(0.55 * _thinfilm(res, seed, 6.0) + 0.55 * ridged_terrain(res, res, seed + 3)), h, w)


def _quad_labels(res, seed, splits=170):
    """Recursive rectangle partition (split the largest rect each step, slightly random cut) ->
    a cubist Mondrian tiling of varied rectangle regions."""
    rng = _rng(seed)
    rects = [(0, 0, res, res)]
    for _ in range(int(splits)):
        areas = [(r[2] - r[0]) * (r[3] - r[1]) for r in rects]
        i = int(np.argmax(areas))
        y0, x0, y1, x1 = rects.pop(i)
        hh, ww = y1 - y0, x1 - x0
        if hh < 14 and ww < 14:
            rects.append((y0, x0, y1, x1))
            continue
        if ww >= hh:
            cut = int(x0 + ww * float(rng.uniform(0.32, 0.68)))
            rects.append((y0, x0, y1, cut)); rects.append((y0, cut, y1, x1))
        else:
            cut = int(y0 + hh * float(rng.uniform(0.32, 0.68)))
            rects.append((y0, x0, cut, x1)); rects.append((cut, x0, y1, x1))
    lab = np.zeros((res, res), np.int64)
    for j, (y0, x0, y1, x1) in enumerate(rects):
        lab[y0:y1, x0:x1] = j + 1
    return lab


def cubist_prism(h, w, seed, *, res=720, splits=170, palette=None, edge=(255, 225, 150)):
    """Cubist rectangle mosaic, multi-hue panels, glowing ignitable seams."""
    palette = palette or [(190, 95, 35), (40, 125, 120), (175, 150, 40)]
    return _up(colorize_cells(_quad_labels(res, seed, splits), (7, 6, 4), palette, edge, seam=3), h, w)


def _pinwheel_labels(res, cells):
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    cu = np.floor(gx / s).astype(np.int64)
    cv = np.floor(gy / s).astype(np.int64)
    fx = gx / s - cu - 0.5
    fy = gy / s - cv - 0.5
    quad = ((np.arctan2(fy, fx) + np.pi) / (2 * np.pi) * 4).astype(np.int64) % 4
    return (cu * 100003 + cv) * 4 + quad


def pinwheel_glass(h, w, seed, *, res=720, cells=8, palette=None, edge=(200, 245, 255)):
    """Square cells each split into four pinwheel wedges, multi-hue, bright ignitable spokes."""
    palette = palette or [(60, 70, 185), (30, 150, 175), (120, 55, 175)]
    return _up(colorize_cells(_pinwheel_labels(res, cells), (5, 6, 11), palette, edge, seam=2), h, w)


def _weighted_voronoi_labels(res, seed, cells):
    """Multiplicatively-weighted Voronoi -> curved cell boundaries (organic basins)."""
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    wt = rng.uniform(0.62, 1.5, int(cells)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    best = np.full((res, res), 1e18, np.float32)
    lab = np.zeros((res, res), np.int64)
    for i in range(int(cells)):
        d = ((gy - pts[i, 0]) ** 2 + (gx - pts[i, 1]) ** 2) / (wt[i] * wt[i])
        m = d < best
        best = np.where(m, d, best)
        lab = np.where(m, i, lab)
    return lab


def aurora_basins(h, w, seed, *, res=720, cells=42, palette=None, edge=(205, 255, 225)):
    """Curved weighted-Voronoi basins, aurora multi-hue interiors, bright ignitable rims."""
    palette = palette or [(30, 150, 110), (40, 110, 175), (120, 60, 170)]
    return _up(colorize_cells(_weighted_voronoi_labels(res, seed, cells), (5, 8, 9), palette, edge, seam=2), h, w)


# ── F5 · organic / natural fusions (scalar -> colorize) ──
def coral_marble(h, w, seed, *, res=560):
    """Spinodal domain-maze lobed by large Worley cells — dense convoluted brain coral.
    (Built on domain_labyrinth, not the parked Gray-Scott RD, for full-canvas reliability.)"""
    return _up(_norm(domain_labyrinth(res, res, seed) * (0.55 + 0.45 * worley(res, res, seed + 3, cells=40, kind="cells"))), h, w)


def agate_band(h, w, seed, *, res=560):
    """Concentric geode growth bands curl-warped, then embossed into crisp concentric ridge-lines so
    the band boundaries ignite — sliced/slabbed banded agate."""
    g = _norm(_curl_warp(geode_bands(res, res, seed, cores=6), seed + 7, res, 0.18))
    ridges = np.abs(np.sin(g * 6.283185 * 7.0))      # sharp band edges for fracture_spec to trace
    return _up(_norm(0.5 * g + 0.6 * ridges), h, w)


def leaf_vein(h, w, seed, *, res=560):
    """Dragonfly/leaf vein network modulated by marble — organic venation."""
    return _up(_norm(wing_venation(res, res, seed, cells=110) * (0.5 + 0.5 * marble(res, res, seed + 3))), h, w)


def feather_flow(h, w, seed, *, res=560):
    """Dense feather fans softly curl-warped — layered drifting plumage."""
    return _up(_norm(_curl_warp(frost_feather(res, res, seed, feathers=24), seed + 7, res, 0.06)), h, w)


def dendrite_frost(h, w, seed, *, res=560):
    """Window-frost fern dendrites over full-canvas ridged terrain — crystalline frost, no voids."""
    return _up(_norm(0.7 * frost_lace(res, res, seed, seeds=20) + 0.6 * ridged_terrain(res, res, seed + 3)), h, w)


# ── F5 multi-hue traced-cell label structures: parquet / crackle plates / merged rooms ──
def _basketweave_labels(res, cells=10):
    """2x1 domino parquet — orientation alternates per super-block (basketweave)."""
    gy, gx = np.mgrid[0:res, 0:res].astype(np.int64)
    s = max(1, int(res / cells))
    bx, by = gx // s, gy // s
    parity = ((bx // 2) + (by // 2)) % 2
    horiz = by * 100003 + (bx // 2)
    vert = bx * 100003 + (by // 2) + 50000000
    return np.where(parity == 0, horiz, vert)


def parquet_glass(h, w, seed, *, res=720, cells=10, palette=None, edge=(255, 225, 150)):
    """Basketweave parquet of 2x1 tiles, warm multi-hue, glowing ignitable seams."""
    palette = palette or [(150, 95, 45), (110, 65, 35), (170, 140, 60)]
    return _up(colorize_cells(_basketweave_labels(res, cells), (7, 5, 3), palette, edge, seam=3), h, w)


def _crackle_labels(res, seed, cells=42):
    """Connected-component plates of a mudcrack field -> irregular ceramic craquelure plates."""
    fld = mudcrack(res, res, seed, cells=cells)
    b = (fld > 0.5).astype(np.uint8)
    n1, l1 = cv2.connectedComponents(b)
    n2, l2 = cv2.connectedComponents((1 - b).astype(np.uint8))
    return np.where(b > 0, l1, l2 + n1).astype(np.int64)


def crackle_glaze(h, w, seed, *, res=720, cells=42, palette=None, edge=(245, 250, 255)):
    """Irregular ceramic craquelure plates, multi-hue glaze, bright ignitable crack-lines."""
    palette = palette or [(60, 150, 140), (205, 200, 175), (40, 90, 170)]
    return _up(colorize_cells(_crackle_labels(res, seed, cells), (8, 9, 10), palette, edge, seam=2), h, w)


def _rooms_labels(res, seed, cells=16):
    """Grid cells randomly merged with a right/down neighbour (union-find) -> maze-room partition
    of dominoes, L-shapes and singles."""
    rng = _rng(seed)
    n = int(cells)
    parent = list(range(n * n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(n):
        for j in range(n):
            idx = i * n + j
            r = float(rng.uniform(0.0, 1.0))
            if r < 0.32 and j < n - 1:
                union(idx, idx + 1)
            elif r < 0.55 and i < n - 1:
                union(idx, idx + n)
    cellmap = np.array([find(k) for k in range(n * n)], np.int64).reshape(n, n)
    s = res / n
    gy, gx = np.mgrid[0:res, 0:res]
    ci = np.clip((gx / s).astype(np.int64), 0, n - 1)
    cj = np.clip((gy / s).astype(np.int64), 0, n - 1)
    return cellmap[cj, ci]


def catacomb_glass(h, w, seed, *, res=720, cells=16, palette=None, edge=(235, 235, 250)):
    """Merged maze-room cells (dominoes/L-shapes), multi-hue, bright ignitable walls."""
    palette = palette or [(70, 80, 160), (150, 60, 150), (180, 120, 50)]
    return _up(colorize_cells(_rooms_labels(res, seed, cells), (6, 6, 9), palette, edge, seam=3), h, w)


# ── F6 · geometric / tech fusions (scalar -> colorize) ──
def penrose_quartz(h, w, seed, *, res=600):
    """Aperiodic Penrose rhombus tiles lit by plane-wave interference — a faceted quartz lattice."""
    return _up(_norm(penrose_rhombus(res, res, seed) * (0.45 + 0.55 * interference(res, res, seed + 3))), h, w)


def tracewerk(h, w, seed, *, res=600):
    """Dense PCB circuit traces over a soft caustic substrate glow — a fully-routed lit board."""
    c = circuitry(res, res, seed, gridn=30)
    cau = caustics(res, res, seed + 3)
    return _up(_norm(0.7 * c + 0.4 * cau + 0.12), h, w)


def isogrid(h, w, seed, *, res=600):
    """A Schwarz-P minimal-surface lattice lightly embossed by ridges — a machined isogrid."""
    return _up(_norm(0.8 * schwarz_surface(res, res, seed) + 0.3 * ridged_terrain(res, res, seed + 3)), h, w)


def knurl_flash(h, w, seed, *, res=600):
    """A fine diamond knurl over a coarse crisp diamond-tread plate — the big ridges ignite, the
    knurl shimmers between them (machined gunmetal tread)."""
    k = knurl(res, res, seed, cells=30)
    dp = diamond_plate(res, res, seed + 3, cells=8)
    return _up(_norm(0.5 * k + 0.62 * dp), h, w)


def guilloche_drift(h, w, seed, *, res=600):
    """Guilloché engine-turned rosettes gently curl-warped — drifting banknote engraving."""
    return _up(_norm(_curl_warp(guilloche(res, res, seed, reps=5), seed + 7, res, 0.07)), h, w)


# ── F6 multi-hue traced-cell label structures: truchet arcs / argyle diamonds / nested frames ──
def _truchet_labels(res, seed, tiles=10):
    """Classic Truchet two-arc tiles -> two flowing regions per tile (curvy connected blobs)."""
    rng = _rng(seed)
    s = res / tiles
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    ti = np.clip(np.floor(gx / s), 0, tiles - 1).astype(np.int64)
    tj = np.clip(np.floor(gy / s), 0, tiles - 1).astype(np.int64)
    orient = rng.integers(0, 2, (tiles, tiles))[tj, ti]
    lx = gx - ti * s
    ly = gy - tj * s
    d = np.where(orient == 0,
                 np.minimum(np.hypot(lx, ly), np.hypot(lx - s, ly - s)),
                 np.minimum(np.hypot(lx - s, ly), np.hypot(lx, ly - s)))
    inside = (d < s * 0.5).astype(np.int64)
    return (tj * 100003 + ti) * 2 + inside


def truchet_glass(h, w, seed, *, res=720, tiles=10, palette=None, edge=(200, 245, 255)):
    """Truchet curved-arc tiles, multi-hue regions, bright ignitable arc seams."""
    palette = palette or [(30, 150, 170), (60, 80, 190), (130, 55, 175)]
    return _up(colorize_cells(_truchet_labels(res, seed, tiles), (5, 7, 11), palette, edge, seam=2), h, w)


def _argyle_labels(res, cells=9):
    """45-degree rotated square lattice -> diamond (argyle) tiles."""
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    u = (gx + gy) / s
    v = (gx - gy) / s
    return np.floor(u).astype(np.int64) * 100003 + np.floor(v).astype(np.int64)


def argyle_glass(h, w, seed, *, res=720, cells=9, palette=None, edge=(255, 230, 170)):
    """Diagonal diamond (argyle) lattice, warm multi-hue, bright ignitable cross-seams."""
    palette = palette or [(180, 90, 40), (160, 135, 45), (40, 120, 115)]
    return _up(colorize_cells(_argyle_labels(res, cells), (8, 6, 4), palette, edge, seam=2), h, w)


def _frame_labels(res, cells=6, rings=4):
    """A grid of cells, each holding concentric square frames (Chebyshev rings) -> nested ziggurats."""
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    ci = np.floor(gx / s).astype(np.int64)
    cj = np.floor(gy / s).astype(np.int64)
    lx = (gx / s - ci) - 0.5
    ly = (gy / s - cj) - 0.5
    cheb = np.maximum(np.abs(lx), np.abs(ly))
    ri = np.clip((cheb * 2 * rings).astype(np.int64), 0, rings - 1)
    return (cj * 100003 + ci) * 100 + ri


def ziggurat_glass(h, w, seed, *, res=720, cells=6, rings=4, palette=None, edge=(220, 235, 255)):
    """A grid of nested-square frame stacks, multi-hue rings, bright ignitable frame-lines."""
    palette = palette or [(60, 90, 175), (40, 150, 160), (140, 60, 170)]
    return _up(colorize_cells(_frame_labels(res, cells, rings), (6, 7, 10), palette, edge, seam=2), h, w)


# ── F7 · cosmic / energy fusions (scalar -> colorize) ──
def nebula_cloud(h, w, seed, *, res=560):
    """Plasma-ball ion clouds turbulated by domain-warped marble — a deep-space nebula."""
    return _up(_norm(plasma_drift(res, res, seed, cores=6) * (0.5 + 0.5 * marble(res, res, seed + 3))), h, w)


def ion_bloom(h, w, seed, *, res=560):
    """Glowing bokeh orbs blooming over a plasma field — drifting ions."""
    return _up(_norm(0.55 * plasma_drift(res, res, seed, cores=6) + 0.7 * bokeh(res, res, seed + 3, n=80)), h, w)


def plasma_arc(h, w, seed, *, res=560):
    """Branching Lichtenberg discharge over a plasma glow — high-voltage arcs."""
    return _up(_norm(0.7 * stormfork(res, res, seed, bolts=40) + 0.5 * plasma_drift(res, res, seed + 3, cores=5)), h, w)


def aurora_veil(h, w, seed, *, res=560):
    """Aurora curtains curl-warped into omnidirectional rippling veils (verticality broken for UV)."""
    return _up(_norm(_curl_warp(aurora_curtains(res, res, seed), seed + 7, res, 0.18)), h, w)


def spiral_galaxy(h, w, seed, *, res=560):
    """Scattered spiral-wave swirls salted with bokeh stars — a field of mini galaxies."""
    return _up(_norm(0.6 * spiral_waves(res, res, seed, vortices=5, k=20.0) + 0.7 * bokeh(res, res, seed + 3, n=90)), h, w)


# ── F7 multi-hue traced-cell label structures: jittered (even) / Manhattan diamond / tartan ──
def _jittered_voronoi_labels(res, seed, n=9, jitter=0.4):
    """Jittered-grid (blue-noise-ish) Voronoi -> evenly-spaced organic cells (no clumping)."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    s = res / n
    gi, gj = np.mgrid[0:n, 0:n].astype(np.float32)
    cy = (gi + 0.5 + rng.uniform(-jitter, jitter, (n, n))) * s
    cx = (gj + 0.5 + rng.uniform(-jitter, jitter, (n, n))) * s
    pts = np.stack([cy.ravel(), cx.ravel()], 1).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    _, i = cKDTree(pts).query(q, k=1)
    return i.reshape(res, res)


def cobble_glass(h, w, seed, *, res=720, n=9, palette=None, edge=(250, 235, 190)):
    """Evenly-spaced cobblestone Voronoi cells, warm earth multi-hue, bright ignitable mortar."""
    palette = palette or [(170, 95, 55), (150, 140, 80), (80, 120, 70)]
    return _up(colorize_cells(_jittered_voronoi_labels(res, seed, n), (8, 7, 5), palette, edge, seam=3), h, w)


def iceshard(h, w, seed, *, res=720, cells=70, palette=None, edge=(235, 245, 255)):
    """Manhattan-metric (p=1) Voronoi -> diamond/kite shards, cool multi-hue, bright ignitable fractures."""
    palette = palette or [(40, 140, 180), (70, 90, 200), (140, 90, 200)]
    return _up(colorize_cells(_voronoi_labels(res, seed, cells, p=1), (5, 7, 12), palette, edge, seam=2), h, w)


def _tartan_labels(res, seed, n=9):
    """Irregular plaid: non-uniform band edges in x and y -> a tartan of varied rectangles."""
    rng = _rng(seed)
    bx = np.sort(rng.uniform(0, res, n - 1)).astype(np.float32)
    by = np.sort(rng.uniform(0, res, n - 1)).astype(np.float32)
    cix = np.searchsorted(bx, np.arange(res)).astype(np.int64)
    ciy = np.searchsorted(by, np.arange(res)).astype(np.int64)
    CIX, CIY = np.meshgrid(cix, ciy)
    return CIY * 1000 + CIX


def tartan_glass(h, w, seed, *, res=720, n=9, palette=None, edge=(220, 190, 90)):
    """An irregular tartan of varied rectangles, multi-hue, bright ignitable thread-lines."""
    palette = palette or [(160, 50, 45), (40, 110, 70), (40, 60, 130)]
    return _up(colorize_cells(_tartan_labels(res, seed, n), (6, 5, 6), palette, edge, seam=3), h, w)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# THEMED FRACTURED CATEGORIES (owner 2026-06-17) — abstract spec-map art evoking each theme.
# OWNER SCALE RULE: patterns render TOO BIG on the 2048 car — crush features ~2-4x finer than they
# look right in the swatch. Use a count/frequency knob where one exists; _tile_finer() for engines
# (spirals, single-motif fields) that have no knob.
def _tile_finer(field, k=2):
    """Crush feature scale: tile the pattern kxk then resize back to size -> features 1/k as big,
    k*k copies. Universal scale-crush for single-motif/centred engines with no frequency knob."""
    f = np.asarray(field, np.float32)
    h0, w0 = f.shape[:2]
    return cv2.resize(np.tile(f, (int(k), int(k))), (w0, h0), interpolation=cv2.INTER_AREA)


# ── 🌊 FRACTURED DEEP — abyssal deep-sea ──
def abyss_lure(h, w, seed, *, res=560):
    """Many small intense glowing lures scattered through a fine caustic deep-water field —
    anglerfish in the abyss (crushed fine; distributed, no dead corners)."""
    return _up(_norm(0.65 * plasma_drift(res, res, seed, cores=16)
                     + 0.45 * (caustics(res, res, seed + 3) * (0.5 + 0.5 * worley(res, res, seed + 9, cells=150, kind="cells")))
                     + 0.1), h, w)


def jelly_drift(h, w, seed, *, res=560):
    """Many small glowing bells advected by a curl flow — a dense bloom of drifting jellyfish."""
    return _up(_norm(_curl_warp(bokeh(res, res, seed, n=120), seed + 7, res, 0.13)), h, w)


def hadal_glow(h, w, seed, *, res=560):
    """A fine refracted caustic light-net over deep cell structure, curl-warped — hadal pooled light."""
    base = caustics(res, res, seed) * (0.45 + 0.55 * worley(res, res, seed + 5, cells=150, kind="cells"))
    return _up(_norm(_curl_warp(base, seed + 7, res, 0.13)), h, w)


def bioluminescence(h, w, seed, *, res=560):
    """Fine glowing plankton speckle scattered over a slow deep-current glow — bioluminescent water."""
    return _up(_norm(0.7 * moth_dust(res, res, seed, specks=7000) + 0.55 * night_tide(res, res, seed + 3)), h, w)


def _ripple_labels(res, seed, sources=7, bands=16):
    """Concentric distance-bands around the NEAREST of several scattered sources -> rain-on-pond
    ripples (multiple ripple centres meeting at ridges; no single centred motif)."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(sources), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, _ = cKDTree(pts).query(q, k=1)
    d = d.reshape(res, res)
    return np.clip(np.floor(_norm(d) * bands), 0, bands).astype(np.int64)


def ripple_glass(h, w, seed, *, res=720, sources=4, bands=15, palette=None, edge=(180, 250, 255)):
    """Concentric water-ripple cell bands, deep multi-hue, bright ignitable wavefronts."""
    palette = palette or [(20, 130, 150), (60, 45, 165), (20, 95, 95)]
    return _up(colorize_cells(_ripple_labels(res, seed, sources, bands), (3, 8, 11), palette, edge, seam=2), h, w)


def vent_plume(h, w, seed, *, res=560):
    """Fine mineral black-smoker plumes: many small magma plates curl-warped into rising vent smoke."""
    return _up(_norm(_curl_warp(magma(res, res, seed, plates=240), seed + 7, res, 0.20)), h, w)


def maelstrom(h, w, seed, *, res=560):
    """Many small tight whirlpools churned through a caustic field — a deep maelstrom (no single big eye)."""
    sp = _tile_finer(spiral_waves(res, res, seed, vortices=4, k=26.0), 2)   # 2x2 -> 4 smaller whirlpools
    return _up(_norm(sp * (0.45 + 0.55 * caustics(res, res, seed + 3))), h, w)


def kelp_drift(h, w, seed, *, res=560):
    """Many fine strands swaying in a curl current over a deep-water glow — a drifting kelp forest."""
    fs = _curl_warp(fiber_strands(res, res, seed, n=380), seed + 7, res, 0.14)
    return _up(_norm(0.8 * fs + 0.35 * caustics(res, res, seed + 5)), h, w)


def cephalopod(h, w, seed, *, res=560):
    """Many small suckers curl-warped over fine skin texture — deep cephalopod hide (crushed fine,
    octo_suckers was rated too-big/blobby so add a fine worley sub-texture between the suckers)."""
    sk = octo_suckers(res, res, seed, cols=18) * (0.5 + 0.5 * worley(res, res, seed + 9, cells=200, kind="cells"))
    return _up(_norm(_curl_warp(sk, seed + 7, res, 0.10)), h, w)


def nacre(h, w, seed, *, res=560):
    """Fine thin-film pearl iridescence over warped marble — mother-of-pearl nacre (more bands)."""
    return _up(_norm(_thinfilm(res, seed, 11.0) * (0.5 + 0.5 * marble(res, res, seed + 3))), h, w)


def _sonar_labels(res, seed, cells=22, bands=5):
    """Voronoi cells, each subdivided into concentric distance bands -> sonar rings inside cells."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, i = cKDTree(pts).query(q, k=1)
    d = d.reshape(res, res)
    i = i.reshape(res, res)
    ring = np.clip((_norm(d) * bands).astype(np.int64), 0, bands - 1)
    return i * 10 + ring


def sonar_glass(h, w, seed, *, res=720, cells=22, bands=5, palette=None, edge=(170, 250, 255)):
    """Voronoi cells ringed by sonar bands, deep multi-hue, bright ignitable contours."""
    palette = palette or [(20, 140, 160), (60, 50, 165), (25, 100, 110)]
    return _up(colorize_cells(_sonar_labels(res, seed, cells, bands), (3, 8, 11), palette, edge, seam=2), h, w)


# ── 🌊 FRACTURED DEEP — new engines (pack of 8) ──
# Paste these def blocks into engine/paint_v2/fractured_math.py.
# All call primitives with BARE names (worley(...), _curl_warp(...), _rng(...), etc.).

# ── SCALAR engines (field -> colorize) ─────────────────────────────────────
def dpx_krakenink(h, w, seed, *, res=560):
    """Many fine ink filaments swirling through dark water — kraken ink discharge.
    Domain-warped marble veins crushed fine (2x2) and lobed by a dense worley cell field so the
    ink twists into many small curls (no single big plume), covering the whole canvas."""
    ink = _curl_warp(_tile_finer(marble(res, res, seed, veins=11.0), 2), seed + 7, res, 0.22)
    return _up(_norm(ink * (0.5 + 0.5 * worley(res, res, seed + 5, cells=130, kind="cells"))), h, w)


def dpx_whalefall(h, w, seed, *, res=560):
    """A fine branching skeleton crawling with tiny glowing bone-eaters over a dim seafloor glow —
    a whale fall on the abyssal plain. River-delta ribs crushed fine (3x3) into many small bone
    branches, lit by a dense ember speckle (the bone-eating worms); a soft caustic floor keeps the
    corners alive so there are no dead patches."""
    ribs = _tile_finer(river_delta(res, res, seed, rivers=10), 3)
    crawlers = embers(res, res, seed + 4, n=420)
    floor = caustics(res, res, seed + 9) * 0.42
    return _up(_norm(0.55 * ribs + 0.7 * crawlers + floor), h, w)


def dpx_abyssalsnow(h, w, seed, *, res=560):
    """A dense fall of fine marine-snow flakes drifting on a slow curl current over deep cell
    structure — abyssal snow sinking through the water column. A pure dense pixel-speck scatter
    (no eyespots, no big discs) is given a hair of bloom, advected by curl noise and modulated by
    a fine worley so the snow pools and thins like real falling detritus while still covering the
    whole frame."""
    rng = _rng(seed)
    flakes = np.zeros((res, res), np.float32)
    n = 9000
    ys = rng.integers(0, res, n); xs = rng.integers(0, res, n)
    flakes[ys, xs] = rng.uniform(0.45, 1.0, n).astype(np.float32)
    flakes = cv2.GaussianBlur(flakes, (0, 0), 0.9) + 0.4 * cv2.GaussianBlur(flakes, (0, 0), 2.6)
    snow = _curl_warp(_norm(flakes), seed + 7, res, 0.16)
    return _up(_norm(snow * (0.5 + 0.5 * worley(res, res, seed + 5, cells=130, kind="cells"))), h, w)


def dpx_eeldischarge(h, w, seed, *, res=560):
    """Many fine branched arcs of electric discharge crackling across a resonant standing field —
    an electric eel firing in the dark. Crushed stormfork bolts (2x2 -> lots of small forks) are lit
    on the nodal resonance lines of a chladni plate so the whole frame flickers with fine sparks."""
    arcs = _tile_finer(stormfork(res, res, seed, bolts=48), 2)
    res_field = chladni(res, res, seed + 4, modes=6)
    return _up(_norm(0.78 * arcs + 0.5 * arcs * res_field + 0.18 * res_field), h, w)


def dpx_pressurestrata(h, w, seed, *, res=560):
    """Many thin compressed sediment laminae folded under crushing depth — abyssal pressure strata.
    A high-frequency sine lamination (the bedding planes) is gently buckled by a low-amplitude
    curl warp (the folding), then sharpened by a worley crack net (the fracture cleavage) so the
    whole canvas reads as fine layered rock, not big blobs."""
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    warp = (_curl_warp(ridged_terrain(res, res, seed + 2, octaves=6), seed + 7, res, 0.10) - 0.5)
    bands = 0.5 + 0.5 * np.sin((gy / res * 46.0 + warp * 9.0) * np.pi)   # ~23 fine laminae, buckled
    fracture = worley(res, res, seed + 5, cells=90, kind="cracks")
    return _up(_norm(bands * (0.6 + 0.4 * fracture)), h, w)


# ── MULTI-HUE engines (return RGB HxWx3 directly via colorize_cells) ────────
def dpx_siphonophore(h, w, seed, *, res=720, rows=22, palette=None, edge=(180, 250, 255)):
    """A long chain of small glowing zooid bodies in deep teal, violet and aqua, strung on bright
    ignitable connective filaments — a drifting siphonophore colony. Staggered scale-cells (the
    zooids) traced by a bright seam (the shared stem)."""
    palette = palette or [(20, 135, 150), (95, 50, 165), (25, 110, 120)]
    return _up(colorize_cells(_stagger_labels(res, rows, seed), (2, 7, 11), palette, edge, seam=2), h, w)


def dpx_glasssquid(h, w, seed, *, res=720, cells=20, palette=None, edge=(190, 250, 255)):
    """Evenly-packed translucent body cells in deep aqua, cyan and lure-gold, set in bright
    ignitable glassy membranes — a transparent glass squid hovering in the deep. Jittered-grid
    Voronoi keeps the cells even (no clumping)."""
    palette = palette or [(25, 140, 145), (35, 110, 165), (175, 130, 35)]
    return _up(colorize_cells(_jittered_voronoi_labels(res, seed, cells), (2, 6, 9), palette, edge, seam=2), h, w)


def dpx_trenchfault(h, w, seed, *, res=720, cols=18, palette=None, edge=(170, 245, 255)):
    """Offset fault blocks of cold trench rock in deep teal, blue and violet, split by bright
    ignitable fissure lines — a fractured deep-sea trench fault. Offset brick courses give the
    staggered block-fault geometry."""
    palette = palette or [(20, 120, 140), (40, 80, 165), (90, 55, 160)]
    return _up(colorize_cells(_brick_labels(res, cols, seed), (2, 6, 10), palette, edge, seam=2), h, w)


# ── 🛸 FRACTURED UFO — engine functions (bare names, pasted into fractured_math.py) ──
# Each returns a 0..1 scalar FIELD (HxWx3 RGB for the multi-hue traced-cell ufx fns).
# Designed FINE: high freq / counts, full coverage, no single centred macro motif.
# Deps already present in fractured_math.py: np, cv2, _rng, _fbm, _norm, _up,
#   _curl_warp, _tile_finer, colorize_cells, _hex_labels, _jittered_voronoi_labels,
#   _ring_labels.


def ufx_saucer_alloy(h, w, seed, *, res=600, rings=46):
    """Brushed saucer-hull alloy: dense concentric turned rings warped by anisotropic brush
    grain -> fine machined disc metal (NOT one big disc — tight repeating turn lines)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx, cy = res * 0.5, res * 0.5
    warp = (_fbm(res, res, rng, 5, 6) - 0.5) * res * 0.05
    r = np.hypot(gx - cx, gy - cy) + warp
    turn = np.abs(np.sin(r / res * rings * 6.283))                 # turned rings
    brush = 0.30 * np.abs(np.sin(gx / res * 70.0 * np.pi + warp * 0.2))
    grain = 0.22 * (_fbm(res, res, rng, 4, 9) - 0.5)
    field = _norm(turn * 0.8 + brush + grain)
    return _up(_tile_finer(field, 2), h, w)


def ufx_tractor_rings(h, w, seed, *, res=600, beams=16, rings=46):
    """Tractor-beam rings: many small beam wells each radiating tight concentric pulse rings on a
    4x4 jittered grid -> a field of abduction wells with crisp rings, never one giant beam."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    s = res / 4.0
    for i in range(int(beams)):
        cx = (i % 4 + rng.uniform(0.25, 0.75)) * s
        cy = (i // 4 % 4 + rng.uniform(0.25, 0.75)) * s
        d = np.hypot(gx - cx, gy - cy)
        local = np.clip(1.0 - d / (res * 0.20), 0, 1)             # confine rings to the well
        acc += np.sin(d / res * rings * 6.283 + rng.uniform(0, 6.28)) * local
        acc += local ** 3 * 1.6                                   # bright core well
    return _up(_norm(acc), h, w)


def ufx_alien_circuitry(h, w, seed, *, res=600, gridn=40):
    """Alien circuitry: orthogonal trace tracks with dense pads/vias on a fine grid -> glowing
    extraterrestrial PCB (high gridn = small traces, full coverage)."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / gridn
    for _ in range(gridn * 5):
        px, py = int(rng.integers(0, gridn)) * s, int(rng.integers(0, gridn)) * s
        for _step in range(int(rng.integers(3, 9))):
            if rng.random() < 0.5:
                nx, ny = px + float(rng.choice([-1, 1])) * s, py
            else:
                nx, ny = px, py + float(rng.choice([-1, 1])) * s
            cv2.line(img, (int(px % res), int(py % res)),
                     (int(nx % res), int(ny % res)), 0.8, 1, cv2.LINE_AA)
            px, py = nx % res, ny % res
        cv2.circle(img, (int(px), int(py)), 2, 1.0, -1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.5)), h, w)


def ufx_glyph_grid(h, w, seed, *, res=600, gridn=22):
    """Alien hieroglyph grid: a tight matrix of small angular rune-strokes (segments + dots)
    in every cell -> an inscribed plate of dense xeno-glyphs."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / gridn
    for iy in range(gridn):
        for ix in range(gridn):
            cx, cy = (ix + 0.5) * s, (iy + 0.5) * s
            for _ in range(int(rng.integers(1, 4))):
                ax = cx + rng.uniform(-0.32, 0.32) * s
                ay = cy + rng.uniform(-0.32, 0.32) * s
                if rng.random() < 0.75:                            # stroke
                    bx = ax + rng.choice([-1, 0, 1]) * s * 0.32
                    by = ay + rng.choice([-1, 0, 1]) * s * 0.32
                    cv2.line(img, (int(ax), int(ay)), (int(bx), int(by)),
                             float(rng.uniform(0.6, 1.0)), 1, cv2.LINE_AA)
                else:                                              # dot
                    cv2.circle(img, (int(ax), int(ay)), 1, 1.0, -1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.45)), h, w)


def ufx_plasma_drive(h, w, seed, *, res=560, cores=14):
    """Plasma-drive glow: many small plasma cores throwing tight radial ion filaments —
    a dense engine-bloom field, scaled small."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    field = np.zeros((res, res), np.float32)
    for _ in range(int(cores)):
        cx, cy = float(rng.uniform(0.05, 0.95) * res), float(rng.uniform(0.05, 0.95) * res)
        ang = np.arctan2(gy - cy, gx - cx)
        rad = np.hypot(gy - cy, gx - cx)
        noise = _fbm(res, res, rng, 5, 4)
        fil = np.abs(np.sin(ang * float(rng.integers(10, 20)) + noise * 14.0))
        glow = np.clip(1.0 - rad / (res * 0.22), 0, 1)
        field += fil * glow + glow ** 3 * 1.3
    return _up(_norm(field), h, w)


def ufx_crop_circle(h, w, seed, *, res=600, motifs=16):
    """Crop-circle geometry: scattered small flattened-ring agroglyphs (rings + radial spokes +
    satellite dots) bedded in a faint field grain — many small circles, no one big formation."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(motifs)):
        cx, cy = int(rng.uniform(0.08, 0.92) * res), int(rng.uniform(0.08, 0.92) * res)
        R = int(rng.uniform(0.03, 0.07) * res)
        cv2.circle(img, (cx, cy), R, float(rng.uniform(0.6, 1.0)), 1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), int(R * 0.5), float(rng.uniform(0.4, 0.8)), 1, cv2.LINE_AA)
        for k in range(int(rng.integers(4, 8))):                   # satellites
            a = 6.283 * k / 6 + rng.uniform(0, 1)
            sx, sy = int(cx + np.cos(a) * R), int(cy + np.sin(a) * R)
            cv2.circle(img, (sx, sy), max(1, int(R * 0.12)), 1.0, -1, cv2.LINE_AA)
            if rng.random() < 0.5:
                cv2.line(img, (cx, cy), (sx, sy), 0.45, 1, cv2.LINE_AA)
    grain = _fbm(res, res, rng, 4, 12) * 0.15
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.5) + grain), h, w)


def ufx_abduction_shafts(h, w, seed, *, res=560, shafts=46):
    """Abduction light-shafts: a dense forest of narrow tapering vertical beams with floating dust
    motes, curl-warped so they lean -> many thin light columns (fine, full-width, no big band)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(shafts)):
        x0 = rng.uniform(0, res)
        wd = rng.uniform(0.004, 0.011) * res                        # thinner shafts
        taper = 1.0 + (gy / res) * 1.2
        beam = np.exp(-((gx - x0) / (wd * taper)) ** 2)
        img += beam * (0.4 + 0.6 * (1.0 - gy / res)) * rng.uniform(0.5, 1.0)
    motes = (rng.uniform(0, 1, (res, res)) > 0.996).astype(np.float32)
    img += cv2.GaussianBlur(motes, (0, 0), 0.7) * 2.0
    img = _curl_warp(img, seed + 3, res, 0.05)
    return _up(_norm(img), h, w)


def ufx_oil_iridescence(h, w, seed, *, res=600, freq=11.0):
    """Otherworldly oil-film iridescence: high-frequency thin-film phase beats over warped grain
    -> fine alien petrol sheen banding."""
    rng = _rng(seed)
    hh = _fbm(res, res, rng, 5, 7).astype(np.float32)
    hh = _curl_warp(hh, seed + 5, res, 0.10)
    ph = hh * float(freq) * 6.283185
    val = (np.sin(ph) + np.sin(ph * 1.27) + np.sin(ph * 1.61) + np.sin(ph * 0.83)) / 4.0
    micro = 0.25 * np.sin(ph * 3.3)
    return _up(_norm(np.abs(val) + micro), h, w)


def ufx_hyperspace(h, w, seed, *, res=600, streaks=2600):
    """Hyperspace streaks: thousands of short radial star-streaks pulled from a central vanishing
    point, denser toward the rim -> warp-jump star tunnel (fine, many tiny lines)."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    cx, cy = res * float(rng.uniform(0.42, 0.58)), res * float(rng.uniform(0.42, 0.58))
    for _ in range(int(streaks)):
        a = rng.uniform(0, 6.283)
        r0 = rng.uniform(0.05, 0.5) * res
        ln = rng.uniform(0.02, 0.10) * res
        x0, y0 = cx + np.cos(a) * r0, cy + np.sin(a) * r0
        x1, y1 = cx + np.cos(a) * (r0 + ln), cy + np.sin(a) * (r0 + ln)
        cv2.line(img, (int(x0), int(y0)), (int(x1), int(y1)),
                 float(rng.uniform(0.4, 1.0)), 1, cv2.LINE_AA)
    field = _norm(cv2.GaussianBlur(img, (0, 0), 0.5))
    return _up(_tile_finer(field, 2), h, w)   # 4 tunnels -> no single centred vanishing point


def ufx_wormhole_rings(h, w, seed, *, res=600, wells=10, rings=34):
    """Wormhole rings: several small funnels each with tight nested elliptical rings twisted by
    a swirl phase -> a field of spacetime drains (small, repeated)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    for _ in range(int(wells)):
        cx, cy = rng.uniform(0.1, 0.9) * res, rng.uniform(0.1, 0.9) * res
        ang = np.arctan2(gy - cy, gx - cx)
        d = np.hypot(gx - cx, gy - cy)
        swirl = ang * float(rng.integers(2, 5))
        acc += np.sin(d / res * rings * 6.283 + swirl + rng.uniform(0, 6.28))
        acc += np.clip(1.0 - d / (res * 0.18), 0, 1) ** 2 * 1.2
    return _up(_norm(acc), h, w)


def ufx_reactor_lattice(h, w, seed, *, res=600, cells=18):
    """Reactor lattice: an isometric three-family strut grid charged by a fine energy-pulse
    overlay -> a glowing antimatter core scaffold (dense small cells)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    s = res / cells
    fams = np.zeros((res, res), np.float32)
    for ang in (0.0, np.pi / 3.0, 2 * np.pi / 3.0):
        proj = gx * np.cos(ang) + gy * np.sin(ang)
        fams += np.clip(1.0 - np.abs(((proj / s) % 1.0) - 0.5) * 6.0, 0, 1)
    nodes = ((np.abs(((gx / s) % 1.0) - 0.5) < 0.08) &
             (np.abs(((gy / s) % 1.0) - 0.5) < 0.08)).astype(np.float32)
    pulse = 0.3 * np.abs(np.sin(np.hypot(gx - res / 2, gy - res / 2) / res * 24.0 * np.pi))
    return _up(_norm(fams * 0.7 + nodes * 0.8 + pulse), h, w)


def ufx_biomech_skin(h, w, seed, *, res=600, cells=70):
    """Bio-mechanical alien skin: a fine Worley-cell membrane warped by curl flow with ridged
    seams -> living chitin-and-tube hide (many small organic cells)."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, _ = cKDTree(pts).query(q, k=2)
    F1 = d[:, 0].reshape(res, res)
    F2 = d[:, 1].reshape(res, res)
    membrane = _norm(F1)
    seam = np.clip(1.0 - _norm(F2 - F1) * 8.0, 0, 1)
    field = membrane * 0.6 + seam * 0.9
    field = _curl_warp(field, seed + 4, res, 0.10)
    tube = 0.3 * np.abs(np.sin(_fbm(res, res, rng, 4, 6) * 9.0))
    return _up(_norm(field + tube), h, w)


def ufx_hex_hull(h, w, seed, *, res=600, cells=20):
    """Hex hull plating: tight beveled hexagonal armor cells with seam highlights and rivet
    pins -> a small-scale ship-hull tessellation."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    x = gx / res - 0.5
    y = gy / res - 0.5
    f = cells * 6.283
    ph = rng.uniform(0, 6.283)
    a = np.cos(x * f + ph)
    b = np.cos((x * 0.5 + y * 0.8660254) * f + ph)
    c = np.cos((x * 0.5 - y * 0.8660254) * f + ph)
    hexf = _norm(a + b + c)
    bevel = hexf ** 0.6
    edge = _norm(np.abs(cv2.Laplacian(hexf, cv2.CV_32F)))
    grain = 0.12 * (_fbm(res, res, rng, 4, 8) - 0.5)
    return _up(_norm(bevel * 0.7 + edge * 0.7 + grain), h, w)


def ufx_nebula_portal(h, w, seed, *, res=560, knots=9):
    """Nebula portal: domain-warped fBm cloud pierced by many small bright ignition knots and a
    fine star speckle -> a churning interdimensional gateway haze (no single centred portal)."""
    rng = _rng(seed)
    cloud = _fbm(res, res, rng, 6, 4).astype(np.float32)
    cloud = _curl_warp(cloud, seed + 6, res, 0.16)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    knot = np.zeros((res, res), np.float32)
    for _ in range(int(knots)):
        cx, cy = rng.uniform(0.1, 0.9) * res, rng.uniform(0.1, 0.9) * res
        d = np.hypot(gx - cx, gy - cy)
        knot += np.clip(1.0 - d / (res * 0.10), 0, 1) ** 2
    stars = (rng.uniform(0, 1, (res, res)) > 0.9975).astype(np.float32)
    return _up(_norm(cloud * 0.7 + knot * 0.6 + cv2.GaussianBlur(stars, (0, 0), 0.6) * 1.5), h, w)


def ufx_stargate_spiral(h, w, seed, *, res=620, vortices=14, k=44.0):
    """Star-gate spiral: many scattered phase-vortices winding tight arms with fine harmonic
    ripples -> a dense field of interlocking event-gates (no single centred spiral)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    phase = np.zeros((res, res), np.float32)
    rcx = res * float(rng.uniform(0.35, 0.65))
    rcy = res * float(rng.uniform(0.35, 0.65))
    for _ in range(int(vortices)):
        cx, cy = rng.uniform(0.08, 0.92, 2) * res
        phase += rng.choice([-1.0, 1.0]) * np.arctan2(gy - cy, gx - cx)
    rad = np.hypot(gx - rcx, gy - rcy) / res * k
    base = np.sin(phase + rad)
    fine = 0.6 * np.sin(phase * 5.0 + rad * 6.0)
    micro = 0.35 * np.sin(rad * 10.0 + phase)
    field = _norm(base + fine + micro)
    return _up(_tile_finer(field, 2), h, w)   # 2x2 interlocking gates -> no single dominant centre


def ufx_antigrav_ripple(h, w, seed, *, res=600, ripples=18):
    """Antigravity ripple: many overlapping concentric pressure-wave fronts (sqrt-spaced) over a
    fine substrate -> a quivering repulsor field (small, dense rings)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    for _ in range(int(ripples)):
        cx, cy = rng.uniform(0, res, 2)
        d = np.hypot(gx - cx, gy - cy)
        acc += np.sin(np.sqrt(d + 1.0) * float(rng.uniform(1.6, 2.6)) + rng.uniform(0, 6.28))
    field = _norm(0.5 + 0.5 * np.sin(_norm(acc) * np.pi * 5.0))
    return _up(field, h, w)


def ufx_scanner_sweep(h, w, seed, *, res=600, bands=14):
    """Scanner sweep: fine diagonal scan-lines crossed by a sweeping gradient and bright
    detection ticks -> an alien sensor readout (tight lines, full coverage)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    ang = float(rng.uniform(0.3, 1.2))
    proj = gx * np.cos(ang) + gy * np.sin(ang)
    scan = 0.5 + 0.5 * np.sin(proj / res * bands * 6.283)
    sweep = np.clip(np.sin(gx / res * 2.0 * np.pi + gy / res * 0.5), 0, 1)
    ticks = (rng.uniform(0, 1, (res, res)) > 0.996).astype(np.float32)
    ticks = cv2.GaussianBlur(ticks, (0, 0), 0.8) * 2.0
    fine = 0.4 * np.abs(np.sin(gy / res * 90.0 * np.pi))
    return _up(_norm(scan * 0.6 + sweep * 0.3 + fine + ticks), h, w)


def ufx_hull_cells(h, w, seed, *, res=720, cells=120, palette=None, edge=(150, 245, 220)):
    """MULTI-HUE traced cells: a fine jittered Voronoi mothership-hull plating in alien-alloy
    hues, each plate ringed by a bright ignitable seam (many small plates)."""
    palette = palette or [(30, 150, 110), (40, 120, 160), (95, 70, 160)]
    return _up(colorize_cells(_jittered_voronoi_labels(res, seed, n=cells, jitter=0.45),
                              (5, 8, 8), palette, edge, seam=2), h, w)


def ufx_glyph_cells(h, w, seed, *, res=720, cells=22, palette=None, edge=(170, 250, 255)):
    """MULTI-HUE traced cells: a dense hex hieroglyph-panel array in plasma hues, each rune cell
    edged by a bright ignitable rim (small hex cells, full coverage)."""
    palette = palette or [(40, 160, 150), (160, 50, 170), (50, 90, 200)]
    return _up(colorize_cells(_hex_labels(res, cells), (5, 6, 10), palette, edge, seam=3), h, w)


def ufx_portal_rings(h, w, seed, *, res=720, rings=18, sectors=14, palette=None, edge=(120, 255, 180)):
    """MULTI-HUE traced cells: concentric ring-sector portal cells in abduction-green / void
    hues, traced by bright ignitable arcs (many small ring segments, NOT one big portal)."""
    palette = palette or [(40, 170, 90), (60, 70, 165), (30, 140, 120)]
    return _up(colorize_cells(_ring_labels(res, rings, sectors, seed),
                              (4, 8, 6), palette, edge, seam=2), h, w)


# ── 👣 FRACTURED CRYPTID — abstract spec-map art evoking cryptid / folklore-creature surfaces.
# All engines use BARE primitive names (pasted into fractured_math.py). Scale crushed 2-4x finer
# than it looks right at 360px (owner SCALE RULE #0): high counts, _tile_finer, full coverage.

# ── SCALAR engines (field 0..1) ──
def cry_sasquatch_fur(h, w, seed, *, res=560):
    """Matted shaggy sasquatch fur: many fine curved strands curl-warped into a wind-laid coat,
    with a dark under-fur fbm so the whole pelt is dense (no bare patches)."""
    fs = _curl_warp(fiber_strands(res, res, seed, n=520), seed + 7, res, 0.12)
    under = _fbm(res, res, _rng(seed + 3), 4, 6)
    return _up(_norm(0.85 * fs + 0.3 * under), h, w)


def cry_quill_bristle(h, w, seed, *, res=560):
    """Dense porcupine/quill bristles: very fine short straight strands raked one way over a
    pebbled hide — crushed fine so it reads as bristle stubble, not big spikes."""
    q = _tile_finer(fiber_strands(res, res, seed, n=420), 2)
    hide = worley(res, res, seed + 5, cells=240, kind="cells")
    return _up(_norm(0.8 * q + 0.45 * hide), h, w)


def cry_coarse_hide(h, w, seed, *, res=560):
    """Coarse leathery cryptid hide: fine mudcrack plates domain-warped, over a tight worley
    pebble so the leather grain is dense and wrinkled everywhere."""
    mc = _curl_warp(mudcrack(res, res, seed, cells=160), seed + 7, res, 0.10)
    grain = worley(res, res, seed + 5, cells=300, kind="cells")
    return _up(_norm(0.75 * mc + 0.4 * grain), h, w)


def cry_eyeshine(h, w, seed, *, res=560):
    """Slit-eyeshine in the dark: many small bright eye-spots scattered through a near-black
    forest murk — eyes glowing back at you from the trees (crushed fine, many small eyes)."""
    ey = _tile_finer(eyes(res, res, seed, n=70), 2)
    murk = night_tide(res, res, seed + 3) * 0.4
    return _up(_norm(ey * 0.95 + murk), h, w)


def cry_bog_murk(h, w, seed, *, res=560):
    """Swamp/bog murk with sparse bioluminescence: dense warped marble water veins (teal) threaded
    by a fine fbm scum so the surface is a churning still-black bog lit from within."""
    water = _curl_warp(marble(res, res, seed, veins=16.0), seed + 7, res, 0.16)
    scum = _fbm(res, res, _rng(seed + 5), 5, 6)
    return _up(_norm(0.7 * water + 0.4 * scum), h, w)


def cry_claw_rake(h, w, seed, *, res=560):
    """Claw-rake gouges: parallel taper slashes (tiger-stripe markings) crushed fine and curl-warped
    so sets of three-claw gouges rake across a dark hide at every angle."""
    rake = _curl_warp(_tile_finer(tiger_stripes(res, res, seed, stripes=14), 2), seed + 7, res, 0.08)
    grain = _fbm(res, res, _rng(seed + 3), 4, 6) * 0.3
    return _up(_norm((1.0 - rake) * 0.9 + grain), h, w)


def cry_bark_camo(h, w, seed, *, res=560):
    """Bark-and-shadow forest camo: crisp wood-grain ridge veins broken by a fine topo contour
    shadow web so the cryptid blends into furrowed bark and dappled forest shade (crushed fine)."""
    bark = _tile_finer(ridged_terrain(res, res, seed, octaves=7), 2)
    shade = topo(res, res, seed + 5, levels=64)
    return _up(_norm(_curl_warp(0.6 * bark + 0.6 * shade, seed + 9, res, 0.07)), h, w)


def cry_feathered_wing(h, w, seed, *, res=560):
    """Feathered wing: many small feather fans scattered and overlapped (crushed fine) so the
    surface reads as a dense plumage of layered barbs, not a few big feathers."""
    fw = _tile_finer(frost_feather(res, res, seed, feathers=26), 2)
    return _up(_norm(0.9 * fw + 0.2 * _fbm(res, res, _rng(seed + 3), 4, 5)), h, w)


def cry_dorsal_ridge(h, w, seed, *, res=560):
    """Reptilian dorsal ridges: rows of overlapping arc scales (dragonscale) crushed fine and
    curl-warped into a running spine of fine keeled ridges."""
    ds = _curl_warp(dragonscale(res, res, seed, rows=34), seed + 7, res, 0.07)
    return _up(_norm(0.9 * ds + 0.2 * worley(res, res, seed + 5, cells=260, kind="cells")), h, w)


def cry_webbed_membrane(h, w, seed, *, res=560):
    """Webbed membrane: a fine network of thin bright veins bounding stretched translucent cells —
    the webbing between a swamp-creature's clawed fingers (high cell count = fine)."""
    return _up(wing_venation(res, res, seed, cells=300), h, w)


def cry_toad_skin(h, w, seed, *, res=560):
    """Mottled toad skin: tightly hex-packed warty beads (gila beadwork) crushed finer and mottled,
    over a damp fbm sheen — a warty bog-toad hide."""
    warts = _tile_finer(gila_bead(res, res, seed, cells=34), 2)
    damp = _fbm(res, res, _rng(seed + 3), 4, 6)
    return _up(_norm(0.8 * warts + 0.35 * damp), h, w)


def cry_antler_bone(h, w, seed, *, res=560):
    """Antler/bone branching: braided river-delta channels read as branching antler tines + bone
    forks, crushed 2x finer and scattered across a dark field at every orientation (dense, small)."""
    branch = _tile_finer(river_delta(res, res, seed, rivers=12), 2)
    return _up(_norm(_curl_warp(0.95 * branch + 0.12 * _fbm(res, res, _rng(seed + 3), 3, 6), seed + 9, res, 0.06)), h, w)


def cry_mossy_stone(h, w, seed, *, res=560):
    """Mossy standing-stone: fine mudcrack stone plates with a fine worley moss speckle pooling in
    the cracks — a lichen-furred boulder where the beast lurks (smaller plates, crisper moss)."""
    stone = mudcrack(res, res, seed, cells=240)
    moss = cv2.GaussianBlur(worley(res, res, seed + 5, cells=320, kind="cells").astype('float32'), (0, 0), 1.4)
    return _up(_norm(0.6 * stone + 0.55 * moss), h, w)


def cry_will_o_wisp(h, w, seed, *, res=200):
    """Will-o'-the-wisp bog lights: many small drifting glowing orbs with fading wisp-trails over
    a near-black marsh — crushed fine (a small low-res orb tile repeated 3x) so it's a dense swarm
    of little lights, not a few big blobs. Orbs' per-orb python loop is the cost, so keep res/n
    small and let _tile_finer multiply them up cheaply."""
    wisps = _tile_finer(orbs(res, res, seed, n=22), 3)
    marsh = night_tide(res, res, seed + 3) * 0.3
    return _up(_norm(wisps * 0.95 + marsh), h, w)


def cry_snakeskin(h, w, seed, *, res=560):
    """Snakeskin: a fine diamond scale lattice (python scales) crushed finer, broken by dark
    irregular blotch banding — a serpent cryptid's shed-ready hide."""
    return _up(python_scales(res, res, seed, cells=64), h, w)


def cry_batwing(h, w, seed, *, res=560):
    """Leathery bat-wing: fine wing-vein cells stretched and curl-warped over a thin wrinkled
    membrane fbm — a mothman/bat membrane stretched between finger-struts."""
    vein = _curl_warp(wing_venation(res, res, seed, cells=220), seed + 7, res, 0.09)
    wrinkle = _fbm(res, res, _rng(seed + 3), 4, 6) * 0.3
    return _up(_norm(0.85 * vein + wrinkle), h, w)


def cry_gator_hide(h, w, seed, *, res=560):
    """Gator hide: fine bulging crocodile scutes (croc_hide) crushed finer, with deep grooves and
    a few raised keel ridges from ridged terrain — armored swamp-lizard back."""
    scutes = croc_hide(res, res, seed, cells=20)
    keel = ridged_terrain(res, res, seed + 5, octaves=5) * 0.3
    return _up(_norm(0.85 * scutes + keel), h, w)


# ── MULTI-HUE traced-cell engines (return RGB HxWx3 directly) ──
def cry_hide_scale_glass(h, w, seed, *, res=720, cells=130, palette=None, edge=(170, 210, 110)):
    """Hide-scale Voronoi cells in mottled forest hues, each a different shade, set in a bright
    ignitable scale-rim — a multi-tone reptilian/amphibian hide (crushed fine, many cells)."""
    palette = palette or [(60, 95, 45), (95, 110, 55), (70, 80, 60)]
    return _up(colorize_cells(_jittered_voronoi_labels(res, seed, max(2, int(round(cells ** 0.5)))),
                              (5, 8, 4), palette, edge, seam=2), h, w)


def cry_dragon_hex_glass(h, w, seed, *, res=720, cells=22, palette=None, edge=(210, 150, 60)):
    """Hex-packed dragon-hide scutes in swamp-green/charcoal/amber, each scale a different shade,
    traced by bright ignitable keels — a dragon/lizard cryptid's plated hide (fine hex)."""
    palette = palette or [(45, 80, 50), (40, 55, 45), (120, 80, 30)]
    return _up(colorize_cells(_hex_labels(res, cells), (4, 6, 4), palette, edge, seam=2), h, w)


def cry_crackle_eyeshine_glass(h, w, seed, *, res=720, cells=120, palette=None, edge=(240, 200, 60)):
    """Crackle-glaze cells in dark hide tones, traced by a bright ignitable amber/green eyeshine
    seam-web — countless little eyes glinting along the cracks of a dark cryptid hide (fine)."""
    palette = palette or [(35, 45, 30), (30, 35, 38), (45, 38, 28)]
    return _up(colorize_cells(_crackle_labels(res, seed, cells), (3, 4, 3), palette, edge, seam=2), h, w)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 🔮 FRACTURED OCCULT engines (occ_* bare primitives — pasted into fractured_math.py).
# ABSTRACT spec-map art evoking ghosts / vampires / spooky / conjuring / cursed symbols.
# SCALE RULE #0: many small features, full coverage, NO single centred macro motif. High counts;
# _tile_finer() any single-motif/centred field 2-3x.
# ══════════════════════════════════════════════════════════════════════════════════════════════

def occ_ectoplasm(h, w, seed, *, res=512):
    """Ghostly ectoplasm: low-frequency mist curl-draped into many drifting wisps with bright
    vapour-fold filaments — wraith smoke pulled across the whole sheet."""
    rng = _rng(seed)
    base = _fbm(res, res, rng, 3, 4).astype(np.float32)
    psi = _fbm(res, res, rng, 4, 6).astype(np.float32)
    gy, gx = np.gradient(psi)
    ys, xs = np.mgrid[0:res, 0:res].astype(np.float32)
    drape = cv2.remap(base, np.clip(xs + gy * res * 0.30, 0, res - 1),
                      np.clip(ys - gx * res * 0.30, 0, res - 1), cv2.INTER_LINEAR)
    drape = cv2.remap(drape, np.clip(xs + gy * res * 0.18, 0, res - 1),
                      np.clip(ys - gx * res * 0.18, 0, res - 1), cv2.INTER_LINEAR)
    wisp = _norm(np.abs(cv2.Laplacian(cv2.GaussianBlur(drape, (0, 0), 1.4), cv2.CV_32F))) ** 0.6
    return _up(_norm(drape * 0.45 + wisp * 0.85), h, w)


def occ_blood_spatter(h, w, seed, *, res=512, drops=240):
    """Blood spatter: many small splattered droplets with cast-off satellite specks and a few
    thin drip-runs trailing down — crime-scene crimson scatter, full coverage."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(drops)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        r = float(rng.uniform(2, 9))
        cv2.circle(img, (int(cx), int(cy)), int(r), float(rng.uniform(0.6, 1.0)), -1, cv2.LINE_AA)
        for _s in range(int(rng.integers(3, 8))):  # cast-off satellites
            a = rng.uniform(0, 6.283)
            d = rng.uniform(r, r * 4.0)
            sx, sy = int(cx + np.cos(a) * d), int(cy + np.sin(a) * d)
            cv2.circle(img, (sx, sy), int(max(1, rng.uniform(1, 2.5))), float(rng.uniform(0.4, 0.8)), -1, cv2.LINE_AA)
        if rng.uniform() < 0.25:  # occasional drip run
            dl = int(rng.uniform(r * 3, r * 8))
            cv2.line(img, (int(cx), int(cy)), (int(cx + rng.uniform(-2, 2)), int(cy + dl)),
                     float(rng.uniform(0.5, 0.9)), max(1, int(r * 0.4)), cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.6)), h, w)


def occ_cobweb_lace(h, w, seed, *, res=512, webs=22):
    """Cobweb lace: many small tattered spider webs (radial spokes + sagging capture spirals)
    overlapping into a dusty lace veil across the whole surface."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(webs)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        spokes = int(rng.integers(7, 11))
        R = float(rng.uniform(0.07, 0.13) * res)
        a0 = rng.uniform(0, 6.283)
        for s in range(spokes):
            a = a0 + 2 * np.pi * s / spokes
            cv2.line(img, (int(cx), int(cy)), (int(cx + np.cos(a) * R), int(cy + np.sin(a) * R)),
                     float(rng.uniform(0.4, 0.7)), 1, cv2.LINE_AA)
        for rr in np.linspace(R * 0.18, R, int(rng.integers(4, 7))):
            sag = rr * 0.12
            pts = [(cx + np.cos(a0 + 2 * np.pi * s / spokes) * (rr - sag * (s % 2)),
                    cy + np.sin(a0 + 2 * np.pi * s / spokes) * (rr - sag * (s % 2)))
                   for s in range(spokes + 1)]
            cv2.polylines(img, [np.array(pts, np.int32)], False, float(rng.uniform(0.5, 0.8)), 1, cv2.LINE_AA)
    dust = _fbm(res, res, rng, 4, 5) * 0.10
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.35) + dust), h, w)


def occ_sigil_grid(h, w, seed, *, res=600, n=16):
    """Cursed sigil grid: a dense grid of small carved occult glyphs (rings, crossbars, ticks,
    dots) — an engraved spellbook plate, fine and full-coverage."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / n
    for i in range(n):
        for j in range(n):
            cx, cy = (i + 0.5) * s, (j + 0.5) * s
            r = s * 0.34
            k = int(rng.integers(0, 6))
            v = float(rng.uniform(0.6, 1.0))
            if k == 0:
                cv2.circle(img, (int(cx), int(cy)), int(r), v, 1, cv2.LINE_AA)
            elif k == 1:
                cv2.line(img, (int(cx - r), int(cy)), (int(cx + r), int(cy)), v, 1, cv2.LINE_AA)
                cv2.line(img, (int(cx), int(cy - r)), (int(cx), int(cy + r)), v, 1, cv2.LINE_AA)
            elif k == 2:
                cv2.circle(img, (int(cx), int(cy)), int(r), v, 1, cv2.LINE_AA)
                cv2.line(img, (int(cx - r), int(cy + r)), (int(cx + r), int(cy - r)), v, 1, cv2.LINE_AA)
            elif k == 3:
                pts = np.array([(cx, cy - r), (cx + r, cy + r), (cx - r, cy + r)], np.int32)
                cv2.polylines(img, [pts], True, v, 1, cv2.LINE_AA)
            elif k == 4:
                cv2.line(img, (int(cx), int(cy - r)), (int(cx), int(cy + r)), v, 1, cv2.LINE_AA)
                for t in (-0.5, 0.0, 0.5):
                    cv2.line(img, (int(cx - r * 0.6), int(cy + r * t)), (int(cx + r * 0.6), int(cy + r * t)), v, 1, cv2.LINE_AA)
            else:
                cv2.circle(img, (int(cx), int(cy)), int(r * 0.3), v, -1, cv2.LINE_AA)
                cv2.circle(img, (int(cx), int(cy)), int(r), v, 1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.5)), h, w)


def occ_bone_branch(h, w, seed, *, res=560, trunks=22):
    """Skeletal bone branching: many recursive forked bone-white limbs growing inward from the
    edges with knobbed joints — a thicket of dead skeletal twigs."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)

    def branch(x, y, ang, width, length, depth):
        if depth <= 0 or width < 0.7:
            return
        steps = max(1, int(length / 7))
        for _s in range(steps):
            ang += float(rng.uniform(-0.10, 0.10))
            nx, ny = x + np.cos(ang) * 7.0, y + np.sin(ang) * 7.0
            cv2.line(img, (int(x), int(y)), (int(nx), int(ny)), float(rng.uniform(0.6, 0.95)), max(1, int(width)), cv2.LINE_AA)
            x, y = nx, ny
        cv2.circle(img, (int(x), int(y)), max(1, int(width)), 0.9, -1, cv2.LINE_AA)  # knuckle joint
        for _ in range(int(rng.integers(2, 4))):
            branch(x, y, ang + float(rng.uniform(-0.8, 0.8)), width * 0.62, length * 0.66, depth - 1)

    for _ in range(int(trunks)):
        # seed from anywhere on the sheet at a random heading so growth fills the whole frame
        x, y = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        a = float(rng.uniform(0, 6.283))
        branch(x, y, a, float(rng.uniform(2.0, 3.8)), float(rng.uniform(0.16, 0.26) * res), 4)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.6)), h, w)


def occ_candle_wax(h, w, seed, *, res=512, columns=22):
    """Dripping candle wax: many vertical wax runs pooling into rounded drips with soft flame-glow
    blooms — molten tallow streaming down a candelabra, fine columns."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    glow = np.zeros((res, res), np.float32)
    for c in range(int(columns)):
        x = (c + 0.5) * res / columns + rng.uniform(-4, 4)
        y = rng.uniform(0, res * 0.4)
        wmax = rng.uniform(2.5, 5.0)
        while y < res:
            seg = rng.uniform(8, 22)
            x += rng.uniform(-1.5, 1.5)
            ww = wmax * rng.uniform(0.6, 1.0)
            cv2.line(img, (int(x), int(y)), (int(x), int(y + seg)), float(rng.uniform(0.5, 0.85)), max(1, int(ww)), cv2.LINE_AA)
            if rng.uniform() < 0.4:  # pooled bead
                cv2.circle(img, (int(x), int(y + seg)), int(ww * rng.uniform(1.1, 1.8)), float(rng.uniform(0.7, 1.0)), -1, cv2.LINE_AA)
            y += seg
        if c % 4 == 0:  # a few flame-glow blooms near the top
            cv2.circle(glow, (int(x), int(rng.uniform(0, res * 0.2))), int(rng.uniform(0.05, 0.10) * res), 1.0, -1, cv2.LINE_AA)
    glow = cv2.GaussianBlur(glow, (0, 0), 12.0)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.5) + glow * 0.5), h, w)


def occ_rune_lattice(h, w, seed, *, res=600, n=18):
    """Cursed rune lattice: a tight diagonal lattice of carved angular runes (Elder-Futhark-like
    staves and branches) at the cell nodes — a binding spell engraved edge to edge."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / n
    for i in range(n + 1):
        for j in range(n + 1):
            cx, cy = i * s, j * s
            r = s * 0.42
            v = float(rng.uniform(0.6, 1.0))
            cv2.line(img, (int(cx), int(cy - r)), (int(cx), int(cy + r)), v, 1, cv2.LINE_AA)  # vertical stave
            for _ in range(int(rng.integers(1, 4))):
                ty = cy + rng.uniform(-r, r)
                dirx = 1 if rng.uniform() < 0.5 else -1
                cv2.line(img, (int(cx), int(ty)), (int(cx + dirx * r * 0.7), int(ty - r * 0.5)), v, 1, cv2.LINE_AA)
    # faint connecting lattice threads
    for i in range(n + 1):
        cv2.line(img, (int(i * s), 0), (int(i * s + s * 0.5), res), 0.12, 1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.5)), h, w)


def occ_shadow_mist(h, w, seed, *, res=512):
    """Shadow mist: layered dark fBm fog with curl-warped tendrils reaching across the surface and
    faint brighter rifts where the mist thins — creeping darkness."""
    rng = _rng(seed)
    f1 = _fbm(res, res, rng, 5, 3).astype(np.float32)
    f2 = _fbm(res, res, rng, 6, 7).astype(np.float32)
    field = f1 * 0.6 + f2 * 0.4
    field = _curl_warp(field, seed + 5, res, 0.22)
    rift = _norm(np.abs(cv2.Laplacian(cv2.GaussianBlur(field, (0, 0), 3.0), cv2.CV_32F))) ** 0.7
    return _up(_norm(field * 0.5 + rift * 0.6), h, w)


def occ_seance_veil(h, w, seed, *, res=512, veils=6):
    """Séance violet veil: overlapping translucent draped sheets with bright fold-seams, curl-warped
    into a hanging spirit curtain — fine repeated folds, not one big sheet."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    for _ in range(int(veils)):
        warp = (_fbm(res, res, rng, 4, 5) - 0.5) * res * 0.4
        freq = rng.uniform(7.0, 12.0)
        ang = rng.uniform(0, np.pi)
        coord = (gx * np.cos(ang) + gy * np.sin(ang) + warp)
        acc += np.abs(np.sin(coord / res * freq * np.pi))
    veil = _norm(acc)
    seams = _norm(np.abs(cv2.Laplacian(cv2.GaussianBlur(veil, (0, 0), 1.2), cv2.CV_32F))) ** 0.6
    return _up(_norm(veil * 0.45 + seams * 0.8), h, w)


def occ_pentagram_tiling(h, w, seed, *, res=640, n=7):
    """Occult-geometry tiling: a grid of small inscribed pentagrams within circles (the classic
    conjuring seal), repeated edge to edge — many small sigils, never one centred star."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / n
    for i in range(n):
        for j in range(n):
            cx, cy = (i + 0.5) * s, (j + 0.5) * s
            R = s * 0.40
            a0 = rng.uniform(0, 1.2)
            pts = [(cx + np.cos(a0 + 2 * np.pi * k / 5) * R, cy + np.sin(a0 + 2 * np.pi * k / 5) * R) for k in range(5)]
            order = [pts[(k * 2) % 5] for k in range(6)]  # five-point star skip-2
            cv2.polylines(img, [np.array(order, np.int32)], True, 0.9, 1, cv2.LINE_AA)
            cv2.circle(img, (int(cx), int(cy)), int(R), 0.7, 1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.5)), h, w)


def occ_graveyard_moss(h, w, seed, *, res=560, cells=110):
    """Gravestone moss: weathered stone plates (Worley) crusted with a sickly-green mossy mottle
    and dark mortar seams — many small slabs, lichen-eaten."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, idx = cKDTree(pts).query(q, k=2)
    F1 = d[:, 0].reshape(res, res); F2 = d[:, 1].reshape(res, res)
    seam = np.clip(1.0 - _norm(F2 - F1) * 7.0, 0, 1)
    plate = rng.uniform(0.30, 0.7, int(cells)).astype(np.float32)[idx[:, 0].reshape(res, res)]
    moss = _fbm(res, res, rng, 5, 6).astype(np.float32)
    moss = (moss > 0.55).astype(np.float32) * moss
    return _up(_norm(plate * 0.5 + moss * 0.7 - seam * 0.4 + 0.2), h, w)


def occ_spider_lattice(h, w, seed, *, res=560, cells=80):
    """Spider lattice: an irregular Voronoi web of taut silk strands with bright node-beads at the
    junctions — a structural web filling the whole frame, fine cells."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, _ = cKDTree(pts).query(q, k=2)
    F1 = d[:, 0].reshape(res, res); F2 = d[:, 1].reshape(res, res)
    strand = np.clip(1.0 - _norm(F2 - F1) * 11.0, 0, 1)
    node = cv2.GaussianBlur((strand > 0.6).astype(np.float32), (0, 0), 1.2) * strand
    return _up(_norm(strand * 0.85 + node * 0.6), h, w)


def occ_raven_feather(h, w, seed, *, res=560, feathers=60):
    """Raven feathers: many overlapping dark plumes — a central rachis with fine angled barbs —
    scattered and rotated into a glossy black plumage, fine and dense."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(feathers)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        L = rng.uniform(0.07, 0.14) * res
        ang = rng.uniform(0, 6.283)
        ex, ey = cx + np.cos(ang) * L, cy + np.sin(ang) * L
        cv2.line(img, (int(cx), int(cy)), (int(ex), int(ey)), float(rng.uniform(0.6, 0.9)), 1, cv2.LINE_AA)
        nb = int(L / 4)
        for t in range(1, nb):
            f = t / nb
            px, py = cx + (ex - cx) * f, cy + (ey - cy) * f
            blen = (1.0 - f) * L * 0.45
            for sgn in (-1, 1):
                ba = ang + sgn * rng.uniform(0.7, 1.0)
                cv2.line(img, (int(px), int(py)), (int(px + np.cos(ba) * blen), int(py + np.sin(ba) * blen)),
                         float(rng.uniform(0.4, 0.7)), 1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.5)), h, w)


def occ_witchfire(h, w, seed, *, res=512, n=260):
    """Witchfire embers: a dense scatter of cold-burning ember coals with short upward lick-trails
    over a low spectral haze — sickly green-fire sparks drifting across the dark."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    for _ in range(int(n)):
        cx, cy = int(rng.uniform(0, res)), int(rng.uniform(0, res))
        r = int(rng.uniform(1, 5))
        b = float(rng.uniform(0.5, 1.0))
        cv2.circle(img, (cx, cy), r, b, -1, cv2.LINE_AA)
        for t in range(1, int(rng.integers(3, 6))):  # upward lick
            jx = int(cx + rng.uniform(-2, 2))
            cv2.circle(img, (jx, int(cy - t * r * 1.1)), max(1, int(r * (1.0 - t * 0.18))), b * 0.3, -1, cv2.LINE_AA)
    core = cv2.GaussianBlur(img, (0, 0), 0.7)
    haze = cv2.GaussianBlur(img, (0, 0), 11.0) * 0.45
    return _up(_norm(core + haze), h, w)


def occ_cracked_tomb(h, w, seed, *, res=600, cells=70):
    """Cracked tombstone: aged stone slabs riven by deep dark fracture cracks with a chiselled
    grain in each plate — weathered granite splitting apart, many small plates."""
    from scipy.spatial import cKDTree
    rng = _rng(seed)
    pts = rng.uniform(0, res, (int(cells), 2)).astype(np.float32)
    gy, gx = np.mgrid[0:res, 0:res]
    q = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
    d, idx = cKDTree(pts).query(q, k=2)
    F1 = d[:, 0].reshape(res, res); F2 = d[:, 1].reshape(res, res)
    crack = np.clip(1.0 - _norm(F2 - F1) * 6.0, 0, 1)
    grain = _fbm(res, res, rng, 5, 5).astype(np.float32) * 0.4
    plate = rng.uniform(0.4, 0.85, int(cells)).astype(np.float32)[idx[:, 0].reshape(res, res)]
    return _up(_norm(plate * (1.0 - crack) * 0.7 + grain * (1.0 - crack)), h, w)


def occ_vampire_damask(h, w, seed, *, res=600, reps=6):
    """Vampire-velvet damask: a tight repeated grid of ornate baroque damask motifs (paired
    scroll-leaves around a central boss) — gothic wallpaper, fine and full-coverage."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / reps
    ts = np.linspace(0, 2 * np.pi, 240)
    for i in range(reps + 1):
        for j in range(reps + 1):
            off = (s * 0.5) if (j % 2) else 0.0  # brick-offset rows
            cx, cy = i * s + off, j * s
            R = s * 0.34
            cv2.circle(img, (int(cx), int(cy)), int(R * 0.35), 0.9, 1, cv2.LINE_AA)  # central boss
            for sgn in (-1, 1):  # paired scroll leaves
                lx = cx + sgn * R * 0.55
                x = lx + sgn * R * 0.45 * np.cos(ts) * (0.4 + 0.6 * np.cos(ts * 0.5))
                y = cy + R * np.sin(ts) * (0.5 + 0.5 * np.sin(ts * 1.5))
                cv2.polylines(img, [np.stack([x, y], 1).astype(np.int32)], False, 0.7, 1, cv2.LINE_AA)
            # ogee diamond frame
            dpts = np.array([(cx, cy - R), (cx + R, cy), (cx, cy + R), (cx - R, cy)], np.int32)
            cv2.polylines(img, [dpts], True, 0.4, 1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.5)), h, w)


def occ_haunted_fog(h, w, seed, *, res=512, banks=5):
    """Haunted fog: horizontal banks of rolling ground-mist with bright wispy crests, stacked and
    curl-sheared so the whole sheet is a churning graveyard fog — many thin bands."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    for _ in range(int(banks)):
        warp = (_fbm(res, res, rng, 4, 4) - 0.5) * res * 0.5
        freq = rng.uniform(4.0, 8.0)
        acc += 0.5 + 0.5 * np.sin((gy + warp) / res * freq * np.pi + rng.uniform(0, 6.283))
    fog = _curl_warp(_norm(acc), seed + 3, res, 0.16)
    crest = _norm(np.abs(cv2.Sobel(cv2.GaussianBlur(fog, (0, 0), 1.5), cv2.CV_32F, 0, 1, ksize=3))) ** 0.6
    return _up(_norm(fog * 0.5 + crest * 0.7), h, w)


# ── MULTI-HUE traced-cell occult engines (return RGB; palette+edge come from eargs) ──

def occ_glyph_cells(h, w, seed, *, res=720, cells=120, palette=None, edge=(225, 180, 90)):
    """Ouija/glyph cells: a dense Voronoi mosaic of small spell-cells in occult multi-hues, each
    seamed by a bright ignitable engraved border — a fragmented incantation plate."""
    palette = palette or [(150, 30, 35), (90, 40, 130), (40, 90, 60)]
    return _up(colorize_cells(_voronoi_labels(res, seed, cells), (6, 5, 6), palette, edge, seam=2), h, w)


def occ_crimson_cells(h, w, seed, *, res=720, n=16, palette=None, edge=(235, 120, 70)):
    """Dripping crimson cells: evenly-packed blood-cell panes in crimson, wine and ash multi-hues
    with bright ignitable membranes — coagulated stained glass, fine even cells."""
    palette = palette or [(150, 25, 30), (95, 20, 45), (60, 55, 55)]
    return _up(colorize_cells(_jittered_voronoi_labels(res, seed, n), (7, 4, 5), palette, edge, seam=3), h, w)


def occ_stained_chapel(h, w, seed, *, res=720, cells=85, palette=None, edge=(220, 175, 95)):
    """Cursed chapel glass: angular shattered shards (Chebyshev Voronoi) in séance violet, blood
    and bone-gold multi-hues, fault-lines igniting bright — a desecrated rose window."""
    palette = palette or [(95, 45, 140), (150, 30, 40), (175, 150, 95)]
    return _up(colorize_cells(_voronoi_labels(res, seed, cells, p=np.inf), (6, 5, 8), palette, edge, seam=2), h, w)


# 🌈 FRACTURED RAINBOW — engine functions (bare names; pasted into fractured_math.py).
# numpy-only hue math (NO colorsys). Each rbw_* returns either a scalar FIELD (HxW 0..1)
# for colorize(), or RGB (HxWx3 0..1) directly for the multi-hue / iridescent-sweep finishes.

# ── numpy-only spectral ramp: map t in 0..1 -> vivid full-spectrum RGB (6-stop lerp) ──
_RBW_STOPS = np.array([
    [0.92, 0.10, 0.12],   # red
    [0.98, 0.55, 0.06],   # orange
    [0.96, 0.92, 0.10],   # yellow
    [0.10, 0.78, 0.28],   # green
    [0.10, 0.45, 0.95],   # blue
    [0.62, 0.16, 0.86],   # violet
], np.float32)


def _rbw_ramp(t, stops=None):
    """Map a 0..1 field to a vivid full-spectrum RGB via a piecewise-linear stop lerp (numpy only)."""
    s = _RBW_STOPS if stops is None else np.asarray(stops, np.float32)
    t = np.clip(np.asarray(t, np.float32), 0.0, 1.0)
    n = len(s) - 1
    x = t * n
    i = np.clip(np.floor(x).astype(np.int64), 0, n - 1)
    f = (x - i)[..., None]
    return s[i] * (1.0 - f) + s[i + 1] * f


def _rbw_shade(rgb, lum):
    """Multiply a spectral RGB by a 0..1 luminance/texture field (keeps hue, adds fine relief)."""
    return np.clip(rgb * np.clip(lum, 0.0, 1.0)[..., None], 0.0, 1.0)


def _rbw_edges(field, sigma=1.0, gain=0.9, edge_rgb=(1.0, 1.0, 1.0)):
    """Bright traced highlight on a field's gradient (the fine detail fracture_spec ignites)."""
    fl = cv2.GaussianBlur(np.clip(_norm(field), 0, 1), (0, 0), sigma)
    gx = cv2.Sobel(fl, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(fl, cv2.CV_32F, 0, 1, ksize=3)
    e = _norm(np.hypot(gx, gy))[..., None] * float(gain)
    return e * np.array(edge_rgb, np.float32)


# ════════════════════ MULTI-HUE TRACED-CELL (full-spectrum palettes) ════════════════════
# default vivid full-spectrum palette for the cell finishes
_RBW_PAL = [(220, 40, 40), (235, 150, 25), (235, 220, 30),
            (40, 175, 70), (40, 95, 215), (150, 50, 195)]


def rbw_prism_cells(h, w, seed, *, res=720, cells=150, palette=None, edge=(245, 250, 255)):
    """Angular shattered prism shards (Chebyshev Voronoi), full-spectrum facets, bright ignitable faults."""
    palette = palette or _RBW_PAL
    return _up(colorize_cells(_voronoi_labels(res, seed, cells, p=np.inf), (6, 6, 9), palette, edge,
                              shade_lo=0.55, shade_hi=1.0, seam=2), h, w)


def rbw_spectrum_voronoi(h, w, seed, *, res=720, cells=26, palette=None, edge=(250, 250, 255)):
    """Jittered-grid Voronoi rainbow cells — many evenly-spaced full-spectrum panes, bright leading
    (cells is PER-AXIS: cells^2 panes)."""
    palette = palette or _RBW_PAL
    return _up(colorize_cells(_jittered_voronoi_labels(res, seed, n=cells, jitter=0.5),
                              (6, 6, 9), palette, edge, shade_lo=0.55, shade_hi=1.0, seam=2), h, w)


def rbw_hex_hive(h, w, seed, *, res=720, cells=30, palette=None, edge=(250, 250, 255)):
    """Tight hex-hive cells in full-spectrum shades, each ringed by a bright ignitable rim."""
    palette = palette or _RBW_PAL
    return _up(colorize_cells(_hex_labels(res, cells), (6, 7, 9), palette, edge,
                              shade_lo=0.55, shade_hi=1.0, seam=3), h, w)


def rbw_kaleidoscope(h, w, seed, *, res=720, cells=14, palette=None, edge=(250, 250, 255)):
    """Pinwheel-wedge tiles (4 spinning wedges per cell) in full-spectrum hues — a kaleidoscope mosaic."""
    palette = palette or _RBW_PAL
    return _up(colorize_cells(_pinwheel_labels(res, cells), (6, 6, 10), palette, edge,
                              shade_lo=0.55, shade_hi=1.0, seam=2), h, w)


def rbw_chroma_rings(h, w, seed, *, res=720, rings=26, sectors=18, palette=None, edge=(252, 250, 255)):
    """Many concentric ring bands split into rotating sectors, full-spectrum, bright ignitable ring-lines.
    Tiled 3x3 so there are NINE ripple centres (no single big centred motif)."""
    palette = palette or _RBW_PAL
    rgb = colorize_cells(_ring_labels(res, rings, sectors, seed), (6, 6, 9), palette, edge,
                         shade_lo=0.55, shade_hi=1.0, seam=2)
    rgb = np.stack([_tile_finer(rgb[..., c], 3) for c in range(3)], -1)
    return _up(np.clip(rgb, 0, 1), h, w)


def rbw_truchet(h, w, seed, *, res=720, tiles=20, palette=None, edge=(245, 250, 255)):
    """Truchet curved-arc tiles, full-spectrum flowing regions, bright ignitable arc seams."""
    palette = palette or _RBW_PAL
    return _up(colorize_cells(_truchet_labels(res, seed, tiles), (5, 6, 10), palette, edge,
                              shade_lo=0.55, shade_hi=1.0, seam=2), h, w)


def rbw_prism_wheel(h, w, seed, *, res=720, sectors=48, rings=11, palette=None, edge=(252, 250, 255)):
    """Shattered prism colour-wheels — many radial wedge facets, full-spectrum, bright ignitable spokes.
    Tiled 3x3 so NINE small wheels pack the canvas (no single centred motif)."""
    palette = palette or _RBW_PAL
    rgb = colorize_cells(_wedge_labels(res, sectors, rings, seed), (6, 6, 9), palette, edge,
                         shade_lo=0.55, shade_hi=1.0, seam=2)
    rgb = np.stack([_tile_finer(rgb[..., c], 3) for c in range(3)], -1)
    return _up(np.clip(rgb, 0, 1), h, w)


def rbw_iris_weave(h, w, seed, *, res=720, cells=16, palette=None, edge=(250, 248, 255)):
    """Basket-weave over/under tiles in full-spectrum hues — an iridescent woven rainbow."""
    palette = palette or _RBW_PAL
    return _up(colorize_cells(_basketweave_labels(res, cells), (6, 6, 9), palette, edge,
                              shade_lo=0.55, shade_hi=1.0, seam=2), h, w)


def rbw_caustic_cells(h, w, seed, *, res=720, sources=12, bands=26, palette=None, edge=(245, 250, 255)):
    """Concentric water-ripple cell bands radiating from scattered sources, full-spectrum, bright wavefronts."""
    palette = palette or _RBW_PAL
    return _up(colorize_cells(_ripple_labels(res, seed, sources, bands), (5, 6, 10), palette, edge,
                              shade_lo=0.55, shade_hi=1.0, seam=2), h, w)


def rbw_opal_fire(h, w, seed, *, res=720, cells=90, palette=None, edge=(252, 250, 255)):
    """Crackle-glaze opal cells (irregular shard crackle) flashing full-spectrum opal fire, bright crack seams."""
    palette = palette or _RBW_PAL
    return _up(colorize_cells(_crackle_labels(res, seed, cells), (6, 6, 9), palette, edge,
                              shade_lo=0.55, shade_hi=1.0, seam=2), h, w)


def rbw_spiral_prism(h, w, seed, *, res=720, arms=22, twist=20, palette=None, edge=(250, 248, 255)):
    """Tight logarithmic-spiral prism arms in full-spectrum hues, bright ignitable spiral seams.
    Tiled 3x3 so NINE small spirals fill the canvas (no single centred motif)."""
    palette = palette or _RBW_PAL
    rgb = colorize_cells(_spiral_labels(res, arms, twist, seed), (5, 6, 10), palette, edge,
                         shade_lo=0.55, shade_hi=1.0, seam=2)
    rgb = np.stack([_tile_finer(rgb[..., c], 3) for c in range(3)], -1)
    return _up(np.clip(rgb, 0, 1), h, w)


def rbw_quasi_cells(h, w, seed, *, res=720, palette=None, edge=(250, 250, 255), bands=16):
    """Spectral quasicrystal: decagonal plane-wave interference mapped DIRECTLY through the full
    spectrum (cycled), so every interference fringe glows a vivid rainbow band with crisp ignitable
    contours — a fine quasi-periodic full-spectrum lattice (no white wash, no centred motif)."""
    qc = _norm(quasicrystal(res, res, seed, waves=10, freq=18.0))
    t = ((qc * float(bands) * 0.45) % 1.0).astype(np.float32)   # many spectral cycles across fringes
    rgb = _rbw_shade(_rbw_ramp(t), 0.55 + 0.45 * qc)
    rgb = rgb + _rbw_edges(qc, 0.9, 0.55)
    return _up(np.clip(rgb, 0, 1), h, w)


# ════════════════════ IRIDESCENT SPECTRAL-SWEEP (numpy hue ramp on an optical field) ════════
def rbw_oil_slick(h, w, seed, *, res=600, freq=12.0):
    """Oil-on-water thin-film iridescence: a fine height field beats into full-spectrum bands, curl-drifted.
    Phase is wrapped (% 1) so the WHOLE spectrum cycles many times -> no warm-only bias."""
    tf = _curl_warp(_thinfilm(res, seed, freq), seed + 7, res, 0.12)
    t = ((tf * 4.0) % 1.0).astype(np.float32)           # cycle full rainbow ~4x across the field
    rgb = _rbw_shade(_rbw_ramp(t), 0.5 + 0.5 * _norm(tf))
    rgb = rgb + _rbw_edges(tf, 1.1, 0.7)
    return _up(np.clip(rgb, 0, 1), h, w)


def rbw_holo_grating(h, w, seed, *, res=600, gratings=7):
    """Holographic diffraction grating: crossed high-freq gratings split white into full-spectrum fringes."""
    # build the grating phase directly so the spectral cycle is crisp & saturated (the library
    # holo_grating's |sum| collapses toward mid-grey and washed the hues out).
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    for _ in range(int(gratings)):
        a = float(rng.uniform(0, np.pi))
        f = float(rng.uniform(26, 52))
        acc += np.sin((gx * np.cos(a) + gy * np.sin(a)) / res * f * 6.283 + float(rng.uniform(0, 6.28)))
    ph = _norm(acc)
    t = ((ph * 5.0) % 1.0).astype(np.float32)         # many crisp full-spectrum diffraction fringes
    relief = _norm(0.5 + 0.5 * np.sin(ph * 5.0 * 6.283))
    rgb = _rbw_shade(_rbw_ramp(t), 0.6 + 0.4 * relief)
    rgb = rgb + _rbw_edges(relief, 0.8, 0.45)
    return _up(np.clip(rgb, 0, 1), h, w)


def rbw_chroma_ripple(h, w, seed, *, res=600, halos=14):
    """Chromatic-aberration ripple rings: packed Newton-ring halos fringed with full-spectrum bands."""
    nr = _tile_finer(newton_rings(res, res, seed, halos=halos), 2)
    t = _norm((nr * 6.0) % 1.0)
    rgb = _rbw_shade(_rbw_ramp(t), 0.4 + 0.6 * nr)
    rgb = rgb + _rbw_edges(nr, 1.0, 0.8)
    return _up(np.clip(rgb, 0, 1), h, w)


def rbw_dichroic_bands(h, w, seed, *, res=600):
    """Dichroic-glass bands: high-freq directional gratings phase full-spectrum stripes that shift
    angle across the panel (the full rainbow cycles many times -> vivid, not warm-collapsed)."""
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    rng = _rng(seed)
    a = float(rng.uniform(0, np.pi))
    warp = _fbm(res, res, rng, 4, 5).astype(np.float32) - 0.5
    coord = (gx * np.cos(a) + gy * np.sin(a)) / res + 0.5 * warp
    t = ((coord * 9.0) % 1.0).astype(np.float32)        # 9 full spectral cycles across the panel
    relief = _norm(0.5 + 0.5 * np.sin(coord * 9.0 * 6.283))
    rgb = _rbw_shade(_rbw_ramp(t), 0.5 + 0.5 * relief)
    rgb = rgb + _rbw_edges(relief, 0.9, 0.8)
    return _up(np.clip(rgb, 0, 1), h, w)


def rbw_holo_foil(h, w, seed, *, res=600):
    """Crinkled holographic foil: thin-film over crystal facets, full-spectrum glints on creased planes."""
    fac = crystal_facets(res, res, seed, cells=120)
    tf = _thinfilm(res, seed + 3, 8.0)
    # per-facet spectral shift + a full thin-film cycle inside each facet -> crinkled foil glints
    t = ((fac * 5.0 + tf * 3.0) % 1.0).astype(np.float32)
    rgb = _rbw_shade(_rbw_ramp(t), 0.55 + 0.45 * _norm(0.5 * fac + 0.5 * tf))
    rgb = rgb + _rbw_edges(fac, 0.9, 0.7)
    return _up(np.clip(rgb, 0, 1), h, w)


def rbw_plasma(h, w, seed, *, res=560):
    """Rainbow plasma: a fine turbulent fBm field phases a full-spectrum hue map that cycles many
    times -> dense small plasma cells covering the whole canvas (no single centred blob)."""
    rng = _rng(seed)
    pl = _norm(_fbm(res, res, rng, 6, 7) + 0.4 * _thinfilm(res, seed + 5, 9.0))
    t = ((pl * 5.0) % 1.0).astype(np.float32)
    rgb = _rbw_shade(_rbw_ramp(t), 0.5 + 0.5 * pl)
    rgb = rgb + _rbw_edges(pl, 1.0, 0.6)
    return _up(np.clip(rgb, 0, 1), h, w)


def rbw_spectral_curl(h, w, seed, *, res=560, freq=9.0):
    """Spectral curl-flow: a full-spectrum hue field smeared along a divergence-free curl flow."""
    base = _thinfilm(res, seed, freq)
    flow = _curl_warp(base, seed + 7, res, 0.22)
    t = ((flow * 4.0) % 1.0).astype(np.float32)        # full rainbow cycles along the curl streamlines
    rgb = _rbw_shade(_rbw_ramp(t), 0.5 + 0.5 * _norm(flow))
    rgb = rgb + _rbw_edges(flow, 1.2, 0.6)
    return _up(np.clip(rgb, 0, 1), h, w)


def rbw_spectral_marble(h, w, seed, *, res=560):
    """Spectral marble: turbulent domain-warped marble veining mapped to a flowing full-spectrum hue field."""
    mb = _norm(marble(res, res, seed, veins=11.0))
    flow = _curl_warp(mb, seed + 7, res, 0.16)
    t = ((flow * 4.0) % 1.0).astype(np.float32)        # spectrum sweeps along the marble veining
    rgb = _rbw_shade(_rbw_ramp(t), 0.5 + 0.5 * mb)
    rgb = rgb + _rbw_edges(mb, 1.1, 0.75)
    return _up(np.clip(rgb, 0, 1), h, w)
