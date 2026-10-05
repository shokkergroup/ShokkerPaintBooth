"""STRANGE ATTRACTORS & CHAOTIC MAPS as DENSITY fields — pack_attractors.

Each engine iterates a different nonlinear dynamical system over a huge ensemble of
PARALLEL trajectories (the recurrence is sequential per point but independent across
points, so it vectorizes), accumulates the visited points into a 2D log-density
histogram, and returns that as a full-coverage, fine-detail scalar FIELD in 0..1.

The math is the asset: each engine is a genuinely DIFFERENT system —
  clifford_web        — Clifford map (sin/cos cross-coupling) ribbon webs.
  hopalong_burst      — Barry Martin's Pickover/Hopalong (sign(x)*sqrt) starburst lace.
  gumowski_mira       — Gumowski-Mira recurrence; ornate "fractal butterfly" filigree.
  ikeda_swirl         — Ikeda laser map; logarithmic-spiral shear sheets.
  tinkerbell_orbit    — Tinkerbell quadratic map; folded crescent shells.
  bedhead_tangle      — Bedhead map (sin(xy/b)+cos...); tangled hair lace.
  thomas_section      — Thomas' cyclically-symmetric 3D flow, Z-slab Poincare density.
  aizawa_section      — Aizawa 3D attractor, projected shell density.
  halvorsen_section   — Halvorsen cyclically-symmetric 3D flow density.
  lorenz_section      — Lorenz butterfly, integrated & projected to a 2D wing density.
  dejong_lattice      — multi-parameter de Jong ensemble; layered moth-wing lattice.

CONTRACT (matches engine/paint_v2/fractured_math.py):
  fn(h, w, seed, *, res=512) -> np.ndarray float32 in [0,1], shape (h, w).
  Pure numpy + cv2 + scipy. Deterministic via np.random.default_rng(seed & 0xffffffff).
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy import ndimage as ndi


# --------------------------------------------------------------------------- helpers
def _rng(seed):
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-9)


def _up(field: np.ndarray, h: int, w: int) -> np.ndarray:
    return cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def _accumulate(x, y, res, lo, hi):
    """Bin parallel point clouds (shape [steps_kept, N] or [N]) into a res x res histogram."""
    sc = (res - 1) / (hi - lo)
    ix = np.clip(((x - lo) * sc).astype(np.int32), 0, res - 1).ravel()
    iy = np.clip(((y - lo) * sc).astype(np.int32), 0, res - 1).ravel()
    acc = np.zeros(res * res, np.float32)
    np.add.at(acc, iy.astype(np.int64) * res + ix.astype(np.int64), 1.0)
    return acc.reshape(res, res)


def _finish(acc, h, w, *, gamma=1.0, blur=0.7, gain=1.0):
    """log-density -> mild blur -> normalize -> optional gamma; fills + sharpens."""
    acc = np.log1p(acc.astype(np.float32) * gain)
    if blur > 0:
        acc = cv2.GaussianBlur(acc, (0, 0), blur)
    f = _norm(acc)
    if gamma != 1.0:
        f = np.power(f, gamma, dtype=np.float32)
    return _norm(_up(f, h, w))


def _spread_clip(x, y, q=2.0):
    """robust bounds so a few escaping points don't collapse the histogram."""
    xs = x.ravel(); ys = y.ravel()
    lo = np.nanpercentile(np.concatenate([xs, ys]), q)
    hi = np.nanpercentile(np.concatenate([xs, ys]), 100 - q)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi - lo < 1e-6:
        lo, hi = -2.0, 2.0
    return float(lo), float(hi)


def _coverage(x, y, probe=96):
    """fraction of a probe-grid occupied by the point cloud, with robust bounds.

    Used to REJECT degenerate parameter sets (a Clifford/de Jong/Bedhead/Gumowski-Mira
    map can land on a thin line or dust for some params -> a near-flat field). We probe
    cheaply and reseed until the attractor genuinely fills the plane."""
    lo, hi = _spread_clip(x, y, q=1.0)
    if hi - lo < 1e-4:
        return 0.0, lo, hi
    g = _accumulate(x, y, probe, lo, hi)
    return float((g > 0).mean()), lo, hi


def _pick_params(rng, gen_params, step_fn, seed_box=1.2, *, n_probe=4000,
                 probe_steps=60, tries=24, min_cov=0.18, min_fine=0.0):
    """Search candidate parameter sets and return the FIRST whose attractor genuinely
    fills the plane (probe coverage >= min_cov) AND, if min_fine>0, has crushed high-freq
    detail (probe fineness >= min_fine) — else the best seen. Deterministic.

    gen_params() -> tuple of params;  step_fn(x, y, params) -> (nx, ny).
    Guarantees a non-degenerate, busy attractor regardless of seed (kills line/dust/blob)."""
    best = None
    best_score = -1.0
    for _ in range(tries):
        params = gen_params()
        x = rng.uniform(-seed_box, seed_box, n_probe).astype(np.float64)
        y = rng.uniform(-seed_box, seed_box, n_probe).astype(np.float64)
        for _i in range(probe_steps):
            x, y = step_fn(x, y, params)
            np.clip(x, -1e6, 1e6, out=x); np.clip(y, -1e6, 1e6, out=y)
        if not (np.isfinite(x).all() and np.isfinite(y).all()):
            continue
        cov, lo, hi = _coverage(x, y)
        fine = 0.0
        if min_fine > 0.0 and cov > 0.0:
            g = _accumulate(x, y, 128, lo, hi)
            g = np.log1p(g)
            sd = g.std() + 1e-6
            fine = float((g - cv2.GaussianBlur(g, (0, 0), 4)).std() / sd)
        score = cov + min(fine, 1.0)
        if score > best_score:
            best_score, best = score, params
        if cov >= min_cov and fine >= min_fine:
            return params
    return best


def _tile_fields(stack, weights=None):
    """combine several normalized fields into one busy field (max-ish union)."""
    if weights is None:
        weights = [1.0] * len(stack)
    out = np.zeros_like(stack[0])
    for f, wgt in zip(stack, weights):
        out = np.maximum(out, _norm(f) * wgt)
    return out


# =========================================================================== ENGINES
def clifford_web(h, w, seed, *, res=480, trajectories=48000, steps=210, burn=22):
    """Clifford map  x'=sin(a y)+c cos(a x),  y'=sin(b x)+d cos(b y) — ribbon-web density."""
    rng = _rng(seed)

    def gen():
        a, b = rng.uniform(-2.0, 2.0, 2)
        c, d = rng.uniform(0.6, 2.0, 2) * rng.choice([-1, 1], 2)
        return a, b, c, d

    def step(x, y, p):
        a, b, c, d = p
        return np.sin(a * y) + c * np.cos(a * x), np.sin(b * x) + d * np.cos(b * y)

    a, b, c, d = _pick_params(rng, gen, step)
    x = rng.uniform(-1.5, 1.5, trajectories).astype(np.float64)
    y = rng.uniform(-1.5, 1.5, trajectories).astype(np.float64)
    acc = np.zeros((res, res), np.float32)
    lo = hi = None
    for i in range(steps):
        x, y = step(x, y, (a, b, c, d))
        if i == burn:  # auto-fit bounds to THIS attractor so it always fills the frame
            lo, hi = _spread_clip(x, y, q=0.5)
        if i >= burn and lo is not None:
            acc += _accumulate(x, y, res, lo, hi)
    return _finish(acc, h, w, gamma=0.85, blur=0.6)


def hopalong_burst(h, w, seed, *, res=480, trajectories=52000, steps=170, burn=18):
    """Barry Martin 'Hopalong' (Pickover):  x'=y - sign(x) sqrt(|b x - c|),  y'=a - x — lace burst."""
    rng = _rng(seed)
    a = rng.uniform(-4.0, 4.0)
    b = rng.uniform(0.5, 3.0)
    c = rng.uniform(0.5, 4.0)
    x = rng.uniform(-0.5, 0.5, trajectories).astype(np.float64)
    y = rng.uniform(-0.5, 0.5, trajectories).astype(np.float64)
    acc = np.zeros((res, res), np.float32)
    lo = hi = None
    for i in range(steps):
        nx = y - np.sign(x) * np.sqrt(np.abs(b * x - c))
        ny = a - x
        x, y = nx, ny
        np.clip(x, -1e6, 1e6, out=x); np.clip(y, -1e6, 1e6, out=y)
        if i == burn:
            lo, hi = _spread_clip(x, y, q=1.0)
        if i >= burn and lo is not None:
            acc += _accumulate(x, y, res, lo, hi)
    return _finish(acc, h, w, gamma=0.8, blur=0.6)


def gumowski_mira(h, w, seed, *, res=480, trajectories=46000, steps=190, burn=18):
    """Gumowski-Mira:  f(x)=a x + 2(1-a)x^2/(1+x^2);  x'=b y + f(x), y'=-x + f(x') — filigree."""
    rng = _rng(seed)

    def _f(t, a):
        return a * t + 2.0 * (1.0 - a) * t * t / (1.0 + t * t)

    def gen():
        # b in the chaotic-but-space-filling band: b->1 gives smooth invariant ovals
        # (blob), b->0 gives a thin sparse filament (empty frame). ~0.72-0.93 fills.
        return rng.uniform(-0.5, 0.5), rng.uniform(0.72, 0.93)  # (a, b)

    def step(x, y, p):
        a, b = p
        nx = b * y + _f(x, a)
        ny = -x + _f(nx, a)
        return nx, ny

    a, b = _pick_params(rng, gen, step, seed_box=0.5, min_cov=0.30,
                        min_fine=0.20, probe_steps=90, tries=40)
    x = rng.uniform(-0.4, 0.4, trajectories).astype(np.float64)
    y = rng.uniform(-0.4, 0.4, trajectories).astype(np.float64)
    acc = np.zeros((res, res), np.float32)
    lo = hi = None
    for i in range(steps):
        x, y = step(x, y, (a, b))
        np.clip(x, -1e6, 1e6, out=x); np.clip(y, -1e6, 1e6, out=y)
        if i == burn:
            lo, hi = _spread_clip(x, y, q=1.0)
        if i >= burn and lo is not None:
            acc += _accumulate(x, y, res, lo, hi)
    return _finish(acc, h, w, gamma=0.9, blur=0.4)


def ikeda_swirl(h, w, seed, *, res=480, trajectories=52000, steps=140, burn=16):
    """Ikeda laser map:  t=c-d/(1+x^2+y^2); x'=1+u(x cos t - y sin t); y'=u(x sin t + y cos t)."""
    rng = _rng(seed)
    u = rng.uniform(0.86, 0.94)
    c = rng.uniform(0.3, 0.5)
    d = rng.uniform(5.0, 8.0)
    x = rng.uniform(-0.2, 0.2, trajectories).astype(np.float64)
    y = rng.uniform(-0.2, 0.2, trajectories).astype(np.float64)
    acc = np.zeros((res, res), np.float32)
    lo = hi = None
    for i in range(steps):
        t = c - d / (1.0 + x * x + y * y)
        ct, st = np.cos(t), np.sin(t)
        nx = 1.0 + u * (x * ct - y * st)
        ny = u * (x * st + y * ct)
        x, y = nx, ny
        if i == burn:
            lo, hi = _spread_clip(x, y, q=1.0)
        if i >= burn and lo is not None:
            acc += _accumulate(x, y, res, lo, hi)
    return _finish(acc, h, w, gamma=0.8, blur=0.55)


def tinkerbell_orbit(h, w, seed, *, res=512, trajectories=55000, steps=150, burn=12):
    """Tinkerbell map:  x'=x^2-y^2+a x+b y;  y'=2 x y + c x + d y — folded crescent shells.

    The attractor is a thin folded ribbon. We seed a wide basin cloud and bin EVERY
    iteration (the transient crescents are part of the look), then a power-law gain
    spreads the density so the field fills the frame instead of collapsing to black."""
    rng = _rng(seed)
    a = rng.uniform(0.88, 0.93)
    b = rng.uniform(-0.65, -0.55)
    c = rng.uniform(1.9, 2.1)
    d = rng.uniform(0.45, 0.55)
    x = rng.uniform(-1.3, 0.7, trajectories).astype(np.float64)
    y = rng.uniform(-1.3, 0.7, trajectories).astype(np.float64)
    acc = np.zeros((res, res), np.float32)
    lo, hi = -1.05, 0.75
    for i in range(steps):
        nx = x * x - y * y + a * x + b * y
        ny = 2.0 * x * y + c * x + d * y
        x, y = nx, ny
        np.clip(x, -3.0, 3.0, out=x); np.clip(y, -3.0, 3.0, out=y)
        if i >= burn:
            acc += _accumulate(x, y, res, lo, hi)
    # log + sqrt gain widens the dense crescent into a full-frame filigree
    acc = np.sqrt(np.log1p(acc.astype(np.float32) * 6.0))
    acc = cv2.GaussianBlur(acc, (0, 0), 0.7)
    return _norm(_up(_norm(acc), h, w))


def bedhead_tangle(h, w, seed, *, res=480, trajectories=56000, steps=180, burn=18):
    """Bedhead map:  x'=sin(x y / b) + cos(a x - y);  y'=x + sin(y)/b — tangled-hair lace."""
    rng = _rng(seed)

    def gen():
        a = rng.uniform(-1.0, 1.0)
        b = rng.uniform(0.30, 1.0) * rng.choice([-1, 1])
        return a, b

    def step(x, y, p):
        a, b = p
        return np.sin(x * y / b) + np.cos(a * x - y), x + np.sin(y) / b

    a, b = _pick_params(rng, gen, step, seed_box=0.5, min_cov=0.16)
    x = rng.uniform(-0.5, 0.5, trajectories).astype(np.float64)
    y = rng.uniform(-0.5, 0.5, trajectories).astype(np.float64)
    acc = np.zeros((res, res), np.float32)
    lo = hi = None
    for i in range(steps):
        x, y = step(x, y, (a, b))
        if i == burn:
            lo, hi = _spread_clip(x, y, q=1.0)
        if i >= burn and lo is not None:
            acc += _accumulate(x, y, res, lo, hi)
    return _finish(acc, h, w, gamma=0.85, blur=0.6)


def thomas_section(h, w, seed, *, res=480, particles=32000, steps=540, burn=80, dt=0.13):
    """Thomas' cyclically-symmetric flow  x'=sin(y)-b x  (cyclic) — Poincare Z-slab density."""
    rng = _rng(seed)
    b = rng.uniform(0.14, 0.20)
    x = rng.uniform(-4, 4, particles)
    y = rng.uniform(-4, 4, particles)
    z = rng.uniform(-4, 4, particles)
    acc = np.zeros((res, res), np.float32)
    lo, hi = -7.0, 7.0
    for i in range(steps):
        dx = np.sin(y) - b * x
        dy = np.sin(z) - b * y
        dz = np.sin(x) - b * z
        x += dt * dx; y += dt * dy; z += dt * dz
        if i >= burn:
            slab = np.abs(z) < 0.6  # near a Poincare plane -> crisp section
            if slab.any():
                acc += _accumulate(x[slab], y[slab], res, lo, hi)
    return _finish(acc, h, w, gamma=0.9, blur=0.7, gain=3.0)


def aizawa_section(h, w, seed, *, res=480, particles=26000, steps=420, burn=72, dt=0.020):
    """Aizawa attractor (a..f params) — projected shell density (x-z plane)."""
    rng = _rng(seed)
    a = 0.95; b = 0.7; c = 0.6; d = 3.5; e = 0.25; f = 0.1
    jit = rng.uniform(-0.04, 0.04, 6)
    a += jit[0]; c += jit[2]; e += jit[4]
    x = rng.uniform(-0.3, 0.3, particles)
    y = rng.uniform(-0.3, 0.3, particles)
    z = rng.uniform(-0.1, 0.4, particles)
    acc = np.zeros((res, res), np.float32)
    lo, hi = -1.6, 1.8
    for i in range(steps):
        dx = (z - b) * x - d * y
        dy = d * x + (z - b) * y
        dz = c + a * z - z**3 / 3.0 - (x * x + y * y) * (1.0 + e * z) + f * z * x**3
        x += dt * dx; y += dt * dy; z += dt * dz
        if i >= burn:
            acc += _accumulate(x, z, res, lo, hi)
    return _finish(acc, h, w, gamma=0.85, blur=0.7, gain=2.0)


def halvorsen_section(h, w, seed, *, res=480, particles=27000, steps=360, burn=64, dt=0.009):
    """Halvorsen cyclically-symmetric attractor  x'=-a x -4y -4z -y^2 (cyclic) — projected density."""
    rng = _rng(seed)
    a = rng.uniform(1.3, 1.5)
    x = rng.uniform(-3, 3, particles)
    y = rng.uniform(-3, 3, particles)
    z = rng.uniform(-3, 3, particles)
    acc = np.zeros((res, res), np.float32)
    lo, hi = -10.0, 6.0
    for i in range(steps):
        dx = -a * x - 4.0 * y - 4.0 * z - y * y
        dy = -a * y - 4.0 * z - 4.0 * x - z * z
        dz = -a * z - 4.0 * x - 4.0 * y - x * x
        x += dt * dx; y += dt * dy; z += dt * dz
        np.clip(x, -50, 50, out=x); np.clip(y, -50, 50, out=y); np.clip(z, -50, 50, out=z)
        if i >= burn:
            acc += _accumulate(x, y, res, lo, hi)
    return _finish(acc, h, w, gamma=0.85, blur=0.7, gain=2.0)


def lorenz_section(h, w, seed, *, res=480, particles=26000, steps=300, burn=36, dt=0.010):
    """Lorenz butterfly  x'=s(y-x), y'=x(r-z)-y, z'=xy-bz.

    A straight x-z projection is a smooth blob, so we take a thin Poincare SECTION near
    y=0 (the plane the trajectory whips through) — that exposes the layered sheet
    structure of the attractor as crisp interleaved filament bands across the whole frame."""
    rng = _rng(seed)
    s = rng.uniform(9.5, 10.5)
    r = rng.uniform(27.0, 31.0)
    b = rng.uniform(2.4, 2.9)
    x = rng.uniform(-15, 15, particles)
    y = rng.uniform(-18, 18, particles)
    z = rng.uniform(5, 40, particles)
    acc = np.zeros((res, res), np.float32)   # full projection (fills frame)
    sec = np.zeros((res, res), np.float32)   # thin section (crisp layered sheets)
    lo, hi = -26.0, 48.0
    for i in range(steps):
        dx = s * (y - x)
        dy = x * (r - z) - y
        dz = x * y - b * z
        x += dt * dx; y += dt * dy; z += dt * dz
        if i >= burn:
            if i % 3 == 0:                       # full projection only every 3rd step (fills frame)
                acc += _accumulate(x, z, res, lo, hi)
            slab = np.abs(y) < 1.4               # near the y=0 plane -> exposes the sheet structure
            if slab.any():
                sec += _accumulate(x[slab], z[slab], res, lo, hi)
    base = _norm(np.log1p(acc * 2.0))
    sheets = _norm(np.log1p(sec * 6.0))
    out = np.maximum(base * 0.55, sheets)  # sheets dominate, base fills the wings
    out = cv2.GaussianBlur(out, (0, 0), 0.55)
    return _norm(_up(_norm(out), h, w))


def dejong_lattice(h, w, seed, *, res=464, trajectories=32000, steps=130, burn=14):
    """Layered de Jong ensemble:  x'=sin(a y)-cos(b x), y'=sin(c x)-cos(d y) over 3 param sets
    -> overlaid moth-wing lattices for extra full-coverage busy-ness."""
    rng = _rng(seed)

    def gen():
        return tuple(rng.uniform(-2.6, 2.6, 4))

    def step(x, y, p):
        a, b, c, d = p
        return np.sin(a * y) - np.cos(b * x), np.sin(c * x) - np.cos(d * y)

    fields = []
    for _ in range(3):
        a, b, c, d = _pick_params(rng, gen, step, min_cov=0.16)
        x = rng.uniform(-1.5, 1.5, trajectories).astype(np.float64)
        y = rng.uniform(-1.5, 1.5, trajectories).astype(np.float64)
        acc = np.zeros((res, res), np.float32)
        lo, hi = -2.2, 2.2
        for i in range(steps):
            x, y = step(x, y, (a, b, c, d))
            if i >= burn:
                acc += _accumulate(x, y, res, lo, hi)
        fields.append(_norm(np.log1p(acc)))
    out = _tile_fields(fields, weights=[1.0, 0.8, 0.65])
    out = cv2.GaussianBlur(out, (0, 0), 0.6)
    return _norm(_up(out, h, w))


ENGINES = {
    "clifford_web": clifford_web,
    "hopalong_burst": hopalong_burst,
    "gumowski_mira": gumowski_mira,
    "ikeda_swirl": ikeda_swirl,
    "tinkerbell_orbit": tinkerbell_orbit,
    "bedhead_tangle": bedhead_tangle,
    "thomas_section": thomas_section,
    "aizawa_section": aizawa_section,
    "halvorsen_section": halvorsen_section,
    "lorenz_section": lorenz_section,
    "dejong_lattice": dejong_lattice,
}


if __name__ == "__main__":
    import time

    H = W = 1024
    print(f"{'engine':<20} {'secs':>6} {'fine':>7} {'std':>6} {'min':>5} {'max':>5}  status")
    print("-" * 70)
    fails = 0
    for name, fn in ENGINES.items():
        # average over a couple seeds to confirm stability
        t0 = time.time()
        f = fn(H, W, 1234)
        secs = time.time() - t0
        finite = np.isfinite(f).all()
        fine = (f - cv2.GaussianBlur(f, (0, 0), 8)).std() / (f.std() + 1e-6)
        std = float(f.std())
        mn, mx = float(f.min()), float(f.max())
        ok = (secs < 2.5) and finite and (fine >= 0.12) and (std > 0.06) and (0.0 <= mn) and (mx <= 1.0)
        status = "OK" if ok else "FAIL"
        if not ok:
            fails += 1
        print(f"{name:<20} {secs:6.2f} {fine:7.3f} {std:6.3f} {mn:5.2f} {mx:5.2f}  {status}")
    print("-" * 70)
    print(f"{len(ENGINES)} engines, {fails} fail(s)")
