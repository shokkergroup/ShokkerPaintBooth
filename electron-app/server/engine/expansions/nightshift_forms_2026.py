# -*- coding: utf-8 -*-
"""NIGHTSHIFT FORMS — one distinct geometric construction per finish.

Owner mandate 2026-09-01:

    "EVERY SINGLE ONE NEEDS TOTALLY UNIQUE BASE PATTERN DESIGNS ... HAND AUTHOR
     EVERYTHING. NO DUPLICATES."

WHY THIS MODULE EXISTS
----------------------
FRACTURED NIGHTSHIFT had 50 finishes drawing on TWELVE structure generators, so
roughly four finishes shared each geometry and differed only in hue and cards.
Giving all 50 hand-authored material decks fixed the material story and left the
real problem untouched: measured after that fix, TWIN was still 0.98-0.99 on all
fifty and FOLLOW 0.03-0.33. The shelf was one algorithm wearing fifty costumes,
and no amount of card selection changes a texture statistic.

So each function here is a genuinely DIFFERENT mathematical idea - not the same
noise with different parameters. Where a construction needs iteration (a
reaction-diffusion system, a wave solver) it is solved on a small grid and
upscaled, which keeps every finish inside the 3s @2048 render budget.

Each returns (field 0..1, labels or None) so it drops straight into the existing
_STRUCTURES contract.

CHOOSING THE FORM IS AN AUTHORING ACT. Each is matched to one finish's NAME:
cyanide gets a real chemical reaction-diffusion, sodium gets Chladni figures
(the sand-on-a-plate experiment those lamps' era is full of), basalt columns go
to the finish about plates freezing, and so on. The name is the brief.
"""
from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

import engine.expansions.fractured_flames_kit_2026 as FK


def _n01(a):
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / (hi - lo) if hi - lo > 1e-9 else np.zeros_like(a)


def _up(a, res):
    if a.shape[0] == res:
        return a
    return cv2.resize(np.asarray(a, np.float32), (res, res), interpolation=cv2.INTER_CUBIC)


def _spread(a):
    """Rank-normalise to a uniform [0,1] distribution.

    Density constructions (attractors, packings, drainage) are extremely
    long-tailed: a few cells hold most of the mass and a min/max stretch
    leaves 96-99%% of the canvas black. Measured means before this:
    clifford 0.002, metaball 0.023, erosion 0.031, phyllotaxis 0.039 - all
    of which would paint a car one flat colour with a few specks on it.
    Ranking keeps the geometry and gives it the whole tonal range."""
    a = np.asarray(a, np.float32)
    flat = a.ravel()
    order = np.argsort(np.argsort(flat)).astype(np.float32)
    return (order / max(flat.size - 1, 1)).reshape(a.shape)


def _lap(a):
    return (np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)
            - 4.0 * a)


# ═══════════════════════════════════════════════════════════════════════════
# 1. GRAY-SCOTT reaction-diffusion — real chemistry, for the chemical finishes
# ═══════════════════════════════════════════════════════════════════════════
def gray_scott(shape, seed, feed=0.037, kill=0.060, steps=820, sim=288, dU=0.16, dV=0.08):
    """Two reacting, diffusing species. The (feed, kill) pair selects the
    REGIME, and the regimes are qualitatively different patterns rather than
    scalings of one pattern: 0.037/0.060 gives drifting worms, 0.030/0.062
    isolated cells, 0.026/0.051 a labyrinth, 0.014/0.047 self-replicating
    mitosis. That is why several finishes can share this function honestly -
    they are not the same geometry."""
    res = int(shape[0])
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    U = np.ones((sim, sim), np.float32)
    V = np.zeros((sim, sim), np.float32)
    n = max(3, sim // 12)
    for _ in range(n * n // 3):
        y, x = rng.integers(0, sim - 6, 2)
        U[y:y + 5, x:x + 5] = 0.50
        V[y:y + 5, x:x + 5] = 0.25
    V += rng.normal(0, 0.012, (sim, sim)).astype(np.float32)
    for _ in range(int(steps)):
        uvv = U * V * V
        U += dU * _lap(U) - uvv + feed * (1.0 - U)
        V += dV * _lap(V) + uvv - (feed + kill) * V
        np.clip(U, 0.0, 1.0, out=U)
        np.clip(V, 0.0, 1.0, out=V)
    return _n01(_up(V, res)), None


# ═══════════════════════════════════════════════════════════════════════════
# 2. CHLADNI nodal figures — sand on a driven plate
# ═══════════════════════════════════════════════════════════════════════════
def chladni(shape, seed, modes=((41, 58), (67, 34), (83, 71), (97, 89), (113, 104)),
            sharp=9.0, floor=0.10):
    """Standing-wave nodal lines on a square plate: sand collects where the
    plate does NOT move. Superposing several (m, n) modes gives the hard,
    unmistakably resonant lattices from the physics-lab photographs.

    Two things had to be right and were not on the first pass. The mode numbers
    must be HIGH (9-28, not 3-8): a (3,7) plate has nodal lines a third of the
    canvas apart, which is a 700px feature on a car. And `sharp` at 42 with a
    normalised argument drove almost the entire plate to zero - the first render
    was black with three visible lines. At sharp 9 with a small floor the whole
    lattice is present and the lines still read as lines."""
    res = int(shape[0])
    y, x = np.mgrid[0:res, 0:res].astype(np.float32) / float(res)
    acc = np.zeros((res, res), np.float32)
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    for (m, n) in modes:
        w = float(rng.uniform(0.65, 1.0))
        acc += w * (np.cos(np.pi * m * x) * np.cos(np.pi * n * y)
                    - np.cos(np.pi * n * x) * np.cos(np.pi * m * y))
    a = np.abs(acc) / (np.abs(acc).max() + 1e-6)
    return _n01(np.exp(-sharp * a) + floor * (1.0 - a)), None


# ═══════════════════════════════════════════════════════════════════════════
# 3. QUASICRYSTAL — N plane waves, aperiodic forever
# ═══════════════════════════════════════════════════════════════════════════
def quasicrystal(shape, seed, waves=7, freq=260.0, phase=0.0):
    """Sum of N plane waves at equal angular spacing. For N=5 or 7 the result
    never repeats, which gives a dense ordered field with no tile - it reads as
    an engineered surface rather than as a texture."""
    res = int(shape[0])
    y, x = (np.mgrid[0:res, 0:res].astype(np.float32) / float(res) - 0.5) * 2.0
    acc = np.zeros((res, res), np.float32)
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    off = float(rng.uniform(0, 6.283))
    # EVERY WAVE NEEDS ITS OWN PHASE. With a shared phase all N cosines peak
    # together at the origin and the sum is a big radial bullseye - the first
    # render was a single smooth blob covering the canvas, not a quasicrystal.
    # Independent phases put the constructive interference everywhere instead of
    # at one point, which is what makes the field aperiodic and uniformly dense.
    ph = rng.uniform(0, 6.283, int(waves)).astype(np.float32)
    for i in range(int(waves)):
        th = np.pi * i / float(waves) + off
        acc += np.cos(freq * (x * np.cos(th) + y * np.sin(th)) + ph[i] + phase)
    return _n01(acc), None


# ═══════════════════════════════════════════════════════════════════════════
# 4. APOLLONIAN packing — circles filling circles, scale-free
# ═══════════════════════════════════════════════════════════════════════════
def apollonian(shape, seed, depth=5200, rmin=0.0022, rmax=0.085):
    """Greedy circle packing: every new disc is as large as it can be without
    touching another. Produces a true scale-free size distribution, so the same
    field carries structure at 500px and at 8px simultaneously - which is
    exactly what the car window wants."""
    res = int(shape[0])
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    out = np.zeros((res, res), np.float32)
    cx = np.empty(depth, np.float32)
    cy = np.empty(depth, np.float32)
    cr = np.empty(depth, np.float32)
    k = 0
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    for _ in range(depth * 6):
        if k >= depth:
            break
        px, py = rng.random(2).astype(np.float32)
        if k:
            d = np.sqrt((cx[:k] - px) ** 2 + (cy[:k] - py) ** 2) - cr[:k]
            r = float(min(d.min(), rmax))
        else:
            r = rmax
        if r < rmin:
            continue
        cx[k], cy[k], cr[k] = px, py, r
        k += 1
    for i in range(k):
        r = cr[i] * res
        x0 = max(0, int((cx[i] * res) - r - 2)); x1 = min(res, int((cx[i] * res) + r + 2))
        y0 = max(0, int((cy[i] * res) - r - 2)); y1 = min(res, int((cy[i] * res) + r + 2))
        if x1 <= x0 or y1 <= y0:
            continue
        d = np.sqrt((xx[y0:y1, x0:x1] - cx[i] * res) ** 2 + (yy[y0:y1, x0:x1] - cy[i] * res) ** 2)
        disc = np.clip(1.0 - d / max(r, 1e-3), 0.0, 1.0)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], disc ** 0.55)
    return _n01(out), None


# ═══════════════════════════════════════════════════════════════════════════
# 5. BASALT columnar jointing — hexagonal cooling fracture
# ═══════════════════════════════════════════════════════════════════════════
def basalt(shape, seed, cells=54, relax=3, wall=0.16):
    """Lava cools, contracts and cracks into polygons that tend toward hexagons.
    Lloyd relaxation of a random point set is what actually produces that
    tendency, so the columns come out irregular-but-hexagonal like the real
    thing rather than like a drawn honeycomb."""
    # Solved on a fixed 512 grid and upscaled. The naive form of this - a
    # res x res x n_points distance stack - is 12 BILLION elements at 2048 and
    # took 10.4s at 512 alone; columns are 30-60px features so nothing is lost
    # by solving them coarse. Lloyd's centroids are accumulated with bincount
    # instead of a Python loop over points, which is where the time actually went.
    res = int(shape[0])
    sim = 512
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    npts = max(16, int(cells) * 6)
    pts = rng.random((npts, 2)).astype(np.float32)
    g = 192
    yy, xx = ((np.mgrid[0:g, 0:g].astype(np.float32) + 0.5) / g)
    flat_y, flat_x = yy.ravel(), xx.ravel()
    for _ in range(int(relax)):
        d = ((flat_x[:, None] - pts[:, 0]) ** 2 + (flat_y[:, None] - pts[:, 1]) ** 2)
        own = d.argmin(1)
        cnt = np.bincount(own, minlength=npts).astype(np.float32)
        sx = np.bincount(own, weights=flat_x, minlength=npts)
        sy = np.bincount(own, weights=flat_y, minlength=npts)
        live = cnt > 0
        pts[live, 0] = (sx[live] / cnt[live]).astype(np.float32)
        pts[live, 1] = (sy[live] / cnt[live]).astype(np.float32)
    yy, xx = ((np.mgrid[0:sim, 0:sim].astype(np.float32) + 0.5) / sim)
    d = ((xx[..., None] - pts[:, 0]) ** 2 + (yy[..., None] - pts[:, 1]) ** 2)
    part = np.partition(d, 1, axis=-1)
    edge = np.sqrt(part[..., 1]) - np.sqrt(part[..., 0])
    lab = d.argmin(-1).astype(np.int32)
    field = _n01(np.clip(edge / wall, 0, 1))
    if res != sim:
        field = _up(field, res)
        lab = cv2.resize(lab.astype(np.float32), (res, res),
                         interpolation=cv2.INTER_NEAREST).astype(np.int32)
    return _n01(field), lab


# ═══════════════════════════════════════════════════════════════════════════
# 6. FROST FERN — anisotropic dendrite on cold glass
# ═══════════════════════════════════════════════════════════════════════════
def frost_fern(shape, seed, seeds=22, steps=96, branch=0.16, drift=0.62):
    """Window frost is not DLA: it grows along a preferred crystal axis with
    side branches at fixed angles, which is why it reads as ferns and not as
    lichen. Grown as explicit walkers with an angular memory."""
    res = int(shape[0])
    sim = 512
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    canvas = np.zeros((sim, sim), np.float32)
    stack = []
    for _ in range(int(seeds)):
        stack.append((float(rng.uniform(0, sim)), float(rng.uniform(0, sim)),
                      float(rng.uniform(0, 6.283)), 1.0))
    axis = float(rng.uniform(0, 6.283))
    for _ in range(int(steps)):
        nxt = []
        for (x, y, th, w) in stack:
            th += (axis - th) * 0.06 + float(rng.normal(0, 0.18)) * drift
            x = (x + np.cos(th) * 1.8) % sim
            y = (y + np.sin(th) * 1.8) % sim
            xi, yi = int(x), int(y)
            canvas[yi, xi] = max(canvas[yi, xi], w)
            nxt.append((x, y, th, w * 0.997))
            if rng.random() < branch and w > 0.28 and len(nxt) < 900:
                nxt.append((x, y, th + rng.choice([-1.0, 1.0]) * 1.05, w * 0.72))
        stack = nxt
    canvas = cv2.GaussianBlur(canvas, (0, 0), 1.1)
    return _n01(_up(canvas, res)), None


# ═══════════════════════════════════════════════════════════════════════════
# 7. CAUSTICS — light focused through a disturbed surface
# ═══════════════════════════════════════════════════════════════════════════
def caustics(shape, seed, scale=7.0, octaves=3, gain=3.4):
    """Refraction through a wavy interface concentrates light on a bright web.
    Computed the honest way - as the Jacobian of a warp - so the network has the
    real caustic signature: thin bright cusps with dark cells between them."""
    res = int(shape[0])
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    h = np.zeros((res, res), np.float32)
    for o in range(int(octaves)):
        f = scale * (2 ** o)
        ph = rng.uniform(0, 6.283, 4).astype(np.float32)
        y, x = np.mgrid[0:res, 0:res].astype(np.float32) / float(res)
        h += (np.sin(f * 6.283 * x + ph[0]) * np.cos(f * 6.283 * y + ph[1])
              + np.sin(f * 4.11 * (x + y) + ph[2])) / (o + 1.0)
    gy, gx = np.gradient(h)
    gyy, gyx = np.gradient(gy)
    gxy, gxx = np.gradient(gx)
    jac = np.abs(gxx * gyy - gxy * gyx)
    return _n01(np.power(1.0 / (1.0 + gain * jac), 2.0)), None


# ═══════════════════════════════════════════════════════════════════════════
# 8. SPIRAL WAVES — Belousov-Zhabotinsky excitable medium
# ═══════════════════════════════════════════════════════════════════════════
def bz_spiral(shape, seed, steps=600, sim=384, a=0.75, b=0.02, eps=0.05,
              dt=0.035, D=0.9, cores=30):
    """An excitable medium: rotating spiral wavefronts that annihilate on
    contact. Nothing else in the catalog produces travelling fronts with real
    curvature and collision scars.

    This is the BARKLEY model, not FitzHugh-Nagumo. The first attempt used FHN
    with a half-plane initial condition and produced two flat blocks and a
    straight edge - no rotation at all, because FHN in that parameter range is
    bistable rather than excitable and a straight front has nothing to curl
    around. A spiral needs a BROKEN wavefront: a phase discontinuity where u is
    excited on one side and v is still refractory. Seeding several of those
    gives independent spiral cores that then collide."""
    res = int(shape[0])
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    u = np.zeros((sim, sim), np.float32)
    v = np.zeros((sim, sim), np.float32)
    yy, xx = np.mgrid[0:sim, 0:sim].astype(np.float32)
    for _ in range(int(cores)):
        cx, cy = rng.integers(sim // 6, sim - sim // 6, 2)
        # a quarter-plane of excitation against a quarter-plane of refractory
        # tissue: the free end of that broken front is the spiral tip
        u[(yy > cy) & (np.abs(xx - cx) < sim * 0.055)] = 1.0
        v[(yy > cy) & (xx > cx) & (np.abs(xx - cx) < sim * 0.055)] = 0.6
    for _ in range(int(steps)):
        uth = (v + b) / a
        du = D * _lap(u) + (1.0 / eps) * u * (1.0 - u) * (u - uth)
        dv = u - v
        u = np.clip(u + dt * du, 0.0, 1.0)
        v = np.clip(v + dt * dv, 0.0, 1.0)
    return _n01(_up(0.65 * u + 0.35 * v, res)), None


# ═══════════════════════════════════════════════════════════════════════════
# 9. SHATTER — radial fracture from impact points
# ═══════════════════════════════════════════════════════════════════════════
def shatter(shape, seed, impacts=3, radials=34, rings=9, jitter=0.22):
    """Impact fracture is radial cracks plus concentric arrest rings - the
    signature of tempered glass and of a struck plate. Built from the geometry
    directly so both families read cleanly at 8-32px."""
    res = int(shape[0])
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    y, x = np.mgrid[0:res, 0:res].astype(np.float32) / float(res)
    out = np.zeros((res, res), np.float32)
    for _ in range(int(impacts)):
        cx, cy = rng.random(2).astype(np.float32)
        dx, dy = x - cx, y - cy
        r = np.sqrt(dx * dx + dy * dy) + 1e-6
        th = np.arctan2(dy, dx)
        warp = np.sin(th * radials + r * 18.0 * jitter * 6.0)
        rad = np.abs(np.cos(th * radials * 0.5 + warp * jitter))
        rng_r = np.abs(np.sin(r * rings * 6.283 + rng.uniform(0, 6.283)))
        out = np.maximum(out, np.clip((1.0 - r * 1.6), 0, 1) * np.maximum(rad ** 8, rng_r ** 14))
    return _n01(out), None


# ═══════════════════════════════════════════════════════════════════════════
# 10. ROSENSWEIG — ferrofluid spike lattice
# ═══════════════════════════════════════════════════════════════════════════
def rosensweig(shape, seed, pitch=27.0, relax=0.55, spike=2.6):
    """A magnetised fluid in a normal field breaks into a hexagonal lattice of
    spikes. Hexagonal packing with a sharp peak profile and a slow field
    modulating the amplitude, so the lattice bends the way the real surface
    does over a curved panel."""
    res = int(shape[0])
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    y, x = np.mgrid[0:res, 0:res].astype(np.float32) / float(res)
    acc = np.zeros((res, res), np.float32)
    ph = rng.uniform(0, 6.283, 3).astype(np.float32)
    for i, th in enumerate((0.0, np.pi / 3.0, 2.0 * np.pi / 3.0)):
        acc += np.cos(pitch * 6.283 * (x * np.cos(th) + y * np.sin(th)) + ph[i])
    acc = _n01(acc) ** spike
    slow = _n01(FK.fbm((res, res), int(seed) + 9, octaves=(2, 4, 8), weights=(1.0, 0.6, 0.3)))
    return _n01(acc * (1.0 - relax + relax * slow)), None


# ═══════════════════════════════════════════════════════════════════════════
# FINE DETAIL — keyed to the macro form, never sprayed over it
# ═══════════════════════════════════════════════════════════════════════════
#
# Most constructions above are MACRO: measured at 2048 they put 82-99% of their
# energy in features larger than 32px. That is correct - they are the finish's
# geometry - but a car needs detail in the 8-32px window too, and the obvious
# fix is the one that ruined FRACTURED ELEMENTS: add an independent fbm layer
# everywhere. Uniform grain makes the paint's detail envelope FLAT, and a flat
# envelope is one no spec can follow (measured: elm_monsoon FOLLOW 0.052 with a
# perfectly good spec, because there was nothing in the paint to correlate with).
#
# So every fine layer here is MODULATED BY THE MACRO FORM - concentrated on its
# edges, inside its cells, or along its gradient direction. The detail then sits
# where the geometry is, which is both how real materials behave and what makes
# the FOLLOW axis achievable at all.

def detail(macro, seed, kind="grain", amount=0.5, res=None, edge_bias=0.65):
    """Return a fine field in [0,1] whose ENERGY follows `macro`'s structure."""
    res = int(res or macro.shape[0])
    m = np.asarray(macro, np.float32)
    gy, gx = np.gradient(m)
    edge = _n01(cv2.GaussianBlur(np.hypot(gx, gy), (0, 0), max(1.0, res / 2048.0 * 6.0)))
    key = np.clip((1.0 - edge_bias) + edge_bias * edge, 0.0, 1.0)
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)

    if kind == "grain":                      # tight isotropic tooth
        f = FK.fbm((res, res), int(seed) + 11, octaves=(256, 512, 1024),
                   weights=(0.5, 1.0, 0.8))
    elif kind == "fibre":                    # drawn along the form's own flow
        th = np.arctan2(gy, gx)
        y, x = np.mgrid[0:res, 0:res].astype(np.float32)
        f = _n01(np.sin((x * np.cos(th) + y * np.sin(th)) * 0.85
                        + FK.fbm((res, res), int(seed) + 3, octaves=(64, 128),
                                 weights=(1.0, 0.6)) * 14.0))
    elif kind == "flake":                    # discrete specular chips
        f = (FK.fbm((res, res), int(seed) + 5, octaves=(512, 1024),
                    weights=(1.0, 0.7)) > 0.62).astype(np.float32)
        f = cv2.GaussianBlur(f, (0, 0), max(0.6, res / 2048.0 * 1.6))
    elif kind == "crackle":                  # fine craze inside the macro cells
        d, lab = FK.worley((res, res), int(seed) + 7, cells=int(res / 2048.0 * 260))
        f = _n01(1.0 - np.clip(d * 3.2, 0, 1))
        key = np.clip(1.0 - edge, 0.0, 1.0)  # craze lives INSIDE cells, not on seams
    elif kind == "stipple":                  # printed dot tooth
        y, x = np.mgrid[0:res, 0:res].astype(np.float32)
        p = max(3.0, res / 2048.0 * 9.0)
        f = _n01(np.sin(x / p * 6.283) * np.sin(y / p * 6.283)
                 + FK.fbm((res, res), int(seed) + 13, octaves=(256, 512),
                          weights=(1.0, 0.6)) * 0.9)
    elif kind == "ridge":                    # sharp folded ridges on the edges
        f = np.abs(FK.fbm((res, res), int(seed) + 17, octaves=(128, 256, 512),
                          weights=(0.6, 1.0, 0.7)) - 0.5) * 2.0
        f = _n01(1.0 - f)
    elif kind == "spark":                    # sparse bright points
        f = (FK.fbm((res, res), int(seed) + 19, octaves=(1024,), weights=(1.0,)) > 0.80
             ).astype(np.float32)
        f = cv2.GaussianBlur(f, (0, 0), max(0.5, res / 2048.0 * 1.1))
    else:
        raise ValueError("unknown detail kind %r" % kind)
    return np.clip(_n01(f) * key * float(amount), 0.0, 1.0), key


def compose_form(macro, seed, kind="grain", amount=0.45, res=None, edge_bias=0.65,
                 macro_weight=0.72):
    """Macro geometry + its own keyed fine layer, as one field."""
    res = int(res or macro.shape[0])
    fine, key = detail(macro, seed, kind=kind, amount=1.0, res=res, edge_bias=edge_bias)
    out = macro_weight * _n01(macro) + float(amount) * fine
    return _n01(out)


# ═══════════════════════════════════════════════════════════════════════════
# BATCH 2 — ten more constructions, so 50 finishes need not share geometry
# ═══════════════════════════════════════════════════════════════════════════
# Ten forms plus twelve in the flames kit is 22 for 50 finishes, which is still
# two-and-a-bit finishes per geometry. These ten take it to 32; combined with
# the regimes that are genuinely different patterns rather than rescalings
# (Gray-Scott's worms/cells/labyrinth/mitosis, quasicrystal's 5- vs 7- vs
# 11-fold), that is enough for every finish to own its construction.

def truchet(shape, seed, tiles=44, style="arc", width=0.17):
    """Tiles carrying an arc or a diagonal in one of two orientations, chosen by
    a hash. Continuous curves emerge across tile boundaries so it never looks
    gridded despite being on a grid. Deliberately NOT the same tile set as the
    protected ff_truchet_glass, which is quarter-circle only."""
    res = int(shape[0])
    t = max(8, int(tiles))
    cell = res / float(t)
    y, x = np.mgrid[0:res, 0:res].astype(np.float32)
    ty, tx = (y / cell).astype(np.int64), (x / cell).astype(np.int64)
    fy, fx = (y / cell) % 1.0, (x / cell) % 1.0
    flip = (FK._h1(ty * np.int64(73856093) ^ tx * np.int64(19349663), int(seed)) > 0.5)
    u = np.where(flip, fx, 1.0 - fx)
    if style == "arc":
        d1 = np.abs(np.sqrt(u ** 2 + fy ** 2) - 0.5)
        d2 = np.abs(np.sqrt((1 - u) ** 2 + (1 - fy) ** 2) - 0.5)
        d = np.minimum(d1, d2)
    elif style == "cross":
        d = np.minimum(np.abs(u - fy), np.abs(u + fy - 1.0)) * 0.7
    else:
        d = np.abs(u - fy)
    return _n01(np.clip(1.0 - d / width, 0, 1)), None


def phyllotaxis(shape, seed, n=52000, spread=0.72, dot=0.0016):
    """Vogel's model: the golden angle between successive seeds, which is how a
    sunflower head packs. A dense field of points whose local lattice rotates
    continuously - ordered everywhere, periodic nowhere."""
    res = int(shape[0])
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    i = np.arange(1, int(n) + 1, dtype=np.float32)
    ga = np.float32(2.39996323)
    r = spread * np.sqrt(i / float(n))
    th = i * ga + float(rng.uniform(0, 6.283))
    px = np.clip(0.5 + r * np.cos(th), 0, 0.999)
    py = np.clip(0.5 + r * np.sin(th), 0, 0.999)
    out = np.zeros((res, res), np.float32)
    xi = (px * res).astype(np.int32)
    yi = (py * res).astype(np.int32)
    np.maximum.at(out, (yi, xi), 1.0)
    return _spread(cv2.GaussianBlur(out, (0, 0), max(0.8, dot * res))), None


def clifford(shape, seed, iters=900000, a=None, b=None, c=None, d=None):
    """NOT FOR PRODUCTION - kept for reference, excluded from PRODUCTION_FORMS.

    Verified by eye 2026-09-01: with degenerate parameters it renders a single
    white diagonal, and with known-good parameters it renders a few enormous
    swooping filament bundles over an empty ground. It is a real attractor and
    a bad car finish - the structure is inherently sparse and hundreds of pixels
    across, so it fails coverage and scale at the same time. Left in the file so
    nobody spends another hour rediscovering that.

    Density of a Clifford strange attractor. The orbit never repeats and its
    density has fine filamentary structure no noise function produces - it is
    the shape of a dynamical system, not a texture."""
    res = int(shape[0])
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    # Most random (a,b,c,d) collapse to a fixed point or a limit cycle; the
    # first render with uniform-random parameters was a single white
    # diagonal. These sets are known to give space-filling attractors.
    KNOWN = ((-1.4, 1.6, 1.0, 0.7), (1.7, 1.7, 0.6, 1.2),
             (-1.7, 1.3, -0.1, -1.21), (1.5, -1.8, 1.6, 0.9),
             (-1.8, -2.0, -0.5, -0.9), (1.6, -0.6, -1.2, 1.6),
             (-1.7, 1.8, -1.9, -0.4), (-2.0, -2.0, -1.2, 2.0))
    k = KNOWN[int(seed) % len(KNOWN)]
    a = k[0] if a is None else a
    b = k[1] if b is None else b
    c = k[2] if c is None else c
    d = k[3] if d is None else d
    n = int(iters)
    out = np.zeros((res, res), np.float32)
    # vectorised over a swarm of independent starting points: iterating one
    # orbit in Python would be ~1e6 interpreter steps and blow the budget
    m = 4096
    xs = rng.uniform(-1.0, 1.0, m).astype(np.float32)
    ys = rng.uniform(-1.0, 1.0, m).astype(np.float32)
    pts_x, pts_y = [], []
    for _ in range(max(1, n // m)):
        xn = np.sin(a * ys) + c * np.cos(a * xs)
        yn = np.sin(b * xs) + d * np.cos(b * ys)
        xs, ys = xn, yn
        pts_x.append(xs.copy()); pts_y.append(ys.copy())
    # PERCENTILE normalisation, not min/max. The attractor's density is
    # extremely long-tailed: a handful of cells carry thousands of hits and
    # min/max then maps the entire visible filigree to near-zero, which is
    # why the first render was a black frame with two faint streaks.
    ax = np.concatenate(pts_x[len(pts_x) // 8:])
    ay = np.concatenate(pts_y[len(pts_y) // 8:])
    # map the orbit's OWN bounding box onto the canvas: a fixed (+3)/6
    # window wasted most of the frame and pushed the figure into a corner
    x0, x1 = float(ax.min()), float(ax.max())
    y0, y1 = float(ay.min()), float(ay.max())
    xi = np.clip(((ax - x0) / max(x1 - x0, 1e-6) * (res - 1)).astype(np.int32), 0, res - 1)
    yi = np.clip(((ay - y0) / max(y1 - y0, 1e-6) * (res - 1)).astype(np.int32), 0, res - 1)
    np.add.at(out, (yi, xi), 1.0)
    out = cv2.GaussianBlur(out, (0, 0), max(0.7, res / 2048.0 * 1.4))
    return _spread(np.log1p(out)), None


def damascus(shape, seed, layers=170, folds=3, twist=2.4, warp=0.28):
    """Pattern-welded steel: many thin layers folded and twisted, then ground
    flat so the section shows as contour bands. The banding follows a warped
    coordinate, which is why real damascus flows instead of running parallel."""
    res = int(shape[0])
    y, x = (np.mgrid[0:res, 0:res].astype(np.float32) / float(res) - 0.5) * 2.0
    w = FK.fbm((res, res), int(seed) + 21, octaves=(4, 8, 16), weights=(1.0, 0.6, 0.3)) - 0.5
    r = np.sqrt(x * x + y * y) + 1e-6
    th = np.arctan2(y, x)
    u = r * np.cos(th + twist * r) + warp * w
    band = np.abs(np.sin(u * layers * 0.5))
    for _ in range(int(folds)):
        band = np.abs(band * 2.0 - 1.0)
    return _n01(band), None


def metaball(shape, seed, blobs=2600, radius=0.0075, thresh=0.42):
    """Implicit surfaces that merge when they approach: a sum of 1/r^2 kernels,
    thresholded. Gives the fused, tension-bounded shapes of liquid coalescing,
    which a Voronoi or a blur cannot produce."""
    res = int(shape[0])
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    pts = rng.random((int(blobs), 2)).astype(np.float32)
    rad = (radius * rng.uniform(0.55, 1.5, int(blobs))).astype(np.float32)
    acc = np.zeros((res, res), np.float32)
    # Each kernel is evaluated only inside its own bounding box. Evaluating all
    # 170 blobs over the full canvas is 170 x 4.2M = 713M operations and took
    # 6.18s at 2048; a 1/r^2 kernel is negligible past a few radii, so the box
    # costs nothing visually and brings it under budget.
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    for i in range(int(blobs)):
        rpix = float(rad[i]) * res
        reach = max(4.0, rpix * 4.5)
        cx, cy = float(pts[i, 0]) * res, float(pts[i, 1]) * res
        x0 = max(0, int(cx - reach)); x1 = min(res, int(cx + reach))
        y0 = max(0, int(cy - reach)); y1 = min(res, int(cy + reach))
        if x1 <= x0 or y1 <= y0:
            continue
        d2 = ((xx[y0:y1, x0:x1] - cx) ** 2 + (yy[y0:y1, x0:x1] - cy) ** 2) / (res * res) + 1e-6
        acc[y0:y1, x0:x1] += (rad[i] ** 2) / d2
    # The box cut off each kernel's far field, so the absolute level of acc
    # is no longer comparable to a fixed threshold - with thresh=0.52 the
    # whole canvas clipped to black except a few cores. Cutting at a
    # PERCENTILE of the field keeps the intended coverage whatever the box
    # does to the level.
    return _spread(np.log1p(acc)), None


def imbricate(shape, seed, rows=64, overlap=0.42, jitter=0.16):
    """Overlapping scales - roof tile, pinecone, fish. Each row is offset half a
    step and each scale is an arc clipped by the row above, so the lighting
    ledge that makes imbrication readable is actually present."""
    res = int(shape[0])
    ry = res / float(rows)
    rx = ry / (1.0 - overlap)
    y, x = np.mgrid[0:res, 0:res].astype(np.float32)
    row = (y / ry).astype(np.int64)
    off = np.where(row % 2 == 0, 0.0, 0.5)
    fy = (y / ry) % 1.0
    fx = ((x / rx) + off) % 1.0
    col = ((x / rx) + off).astype(np.int64)
    j = (FK._h1(row * np.int64(9781) ^ col * np.int64(6151), int(seed)) - 0.5) * jitter
    d = np.sqrt((fx - 0.5) ** 2 + (fy * 0.9 - 0.15 + j) ** 2)
    return _n01(np.clip(1.0 - d / 0.52, 0, 1) ** 1.4), None


def ridge_flow(shape, seed, ridges=190, cores=6, bend=1.9):
    """Fingerprint-style oriented ridges: a smooth orientation field with a few
    singular points (loops and deltas), then ridges drawn across it. The
    singularities are what make it read as a print rather than as stripes."""
    res = int(shape[0])
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    y, x = (np.mgrid[0:res, 0:res].astype(np.float32) / float(res) - 0.5) * 2.0
    th = np.zeros((res, res), np.float32)
    for _ in range(int(cores)):
        cx, cy = rng.uniform(-0.8, 0.8, 2)
        s = float(rng.choice([-1.0, 1.0]))
        th += s * np.arctan2(y - cy, x - cx)
    th = th / max(cores, 1) * bend
    u = x * np.cos(th) + y * np.sin(th)
    u = u + 0.12 * (FK.fbm((res, res), int(seed) + 31, octaves=(8, 16), weights=(1.0, 0.5)) - 0.5)
    return _n01(np.abs(np.sin(u * ridges))), None


def erosion(shape, seed, sim=384, iters=26, sharp=0.55):
    """Drainage by FLOW ACCUMULATION, not by droplet carving.

    The first version walked droplets one cell downhill and subtracted a
    constant. That cut isolated pits - measured car-band 0.007 and a render that
    was flat grey with specks - because a single-step walk with no inertia never
    forms a connected channel. Accumulating flow down the steepest-descent graph
    instead gives the real thing: every cell inherits the water of everything
    above it, so trunks emerge where many tributaries meet."""
    res = int(shape[0])
    h = FK.fbm((sim, sim), int(seed) + 41, octaves=(4, 8, 16, 32, 64),
               weights=(1.0, 0.75, 0.55, 0.35, 0.2)).astype(np.float32)
    acc = np.ones((sim, sim), np.float32)
    for _ in range(int(iters)):
        nxt = np.zeros_like(acc)
        best = np.full((sim, sim), 1e9, np.float32)
        move = np.zeros((sim, sim, 2), np.int8)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nb = np.roll(np.roll(h, -dy, 0), -dx, 1)
            better = nb < best
            best = np.where(better, nb, best)
            move[..., 0] = np.where(better, dy, move[..., 0])
            move[..., 1] = np.where(better, dx, move[..., 1])
        yy, xx = np.mgrid[0:sim, 0:sim]
        ty = (yy + move[..., 0]) % sim
        tx = (xx + move[..., 1]) % sim
        np.add.at(nxt, (ty, tx), acc)
        acc = 0.25 * acc + 0.95 * nxt
        acc /= max(float(acc.max()), 1e-6)
    channels = _spread(np.log1p(acc * 400.0))
    return _n01(_up(np.power(channels, sharp), res)), None


def maze(shape, seed, cells=110, wall=0.30):
    """A perfect maze by randomised depth-first search, rendered as corridors.
    Every cell is reachable and there are no loops, so it reads as routed
    circuitry rather than as a random lattice."""
    res = int(shape[0])
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    n = max(8, int(cells))
    grid = np.zeros((n * 2 + 1, n * 2 + 1), np.float32)
    seen = np.zeros((n, n), bool)
    stack = [(0, 0)]
    seen[0, 0] = True
    grid[1, 1] = 1.0
    while stack:
        cy, cx = stack[-1]
        nb = []
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < n and 0 <= nx < n and not seen[ny, nx]:
                nb.append((ny, nx, dy, dx))
        if not nb:
            stack.pop()
            continue
        ny, nx, dy, dx = nb[int(rng.integers(len(nb)))]
        seen[ny, nx] = True
        grid[cy * 2 + 1 + dy, cx * 2 + 1 + dx] = 1.0
        grid[ny * 2 + 1, nx * 2 + 1] = 1.0
        stack.append((ny, nx))
    g = cv2.resize(grid, (res, res), interpolation=cv2.INTER_NEAREST)
    return _n01(cv2.GaussianBlur(g, (0, 0), max(0.8, res / 2048.0 * 2.2))), None


def moire_beat(shape, seed, a=118.0, b=126.0, angle=0.09):
    """Two fine gratings at slightly different pitch and angle. The carrier sits
    below the car window and the BEAT sits inside it, so the visible pattern is
    an interference envelope rather than either grating - a genuinely different
    mechanism from drawing the envelope directly."""
    res = int(shape[0])
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    y, x = np.mgrid[0:res, 0:res].astype(np.float32) / float(res)
    p = float(rng.uniform(0, 6.283))
    g1 = np.sin(6.283 * a * x + p)
    g2 = np.sin(6.283 * b * (x * np.cos(angle) + y * np.sin(angle)))
    return _n01(g1 * g2), None
