"""PARAMETRIC CURVES & HARMONICS field-generator pack for Shokker Paint Booth.

Eleven GENUINELY DISTINCT generative-math engines in the parametric-curve / harmonic
family. Each produces an intricate, full-coverage scalar FIELD in 0..1, shape (h, w),
computed at low `res` then upscaled. None are recolors of one another: each is a
different curve/harmonic algorithm (spirograph, Lissajous, Maurer rose, rhodonea,
Fourier epicycles, superformula/Gielis, butterfly curve, Clelie spherical spiral,
cardioid caustic, wallpaper-group wave sums, plus an epitrochoid offset-curve weave).

CONTRACT (matches engine/paint_v2/fractured_math.py):
  def NAME(h, w, seed, *, res=512) -> np.ndarray float32 in [0,1], shape (h, w)
  Compute at low res, cv2.resize INTER_LINEAR up, then normalize.
  Pure numpy + cv2 + scipy only. Deterministic via np.random.default_rng(seed & 0xffffffff).

HARD bars (self-test enforces): <2.5s @1024, fineness>=0.12, std>0.06, finite [0,1].
"""
from __future__ import annotations

import numpy as np
import cv2
from scipy.ndimage import distance_transform_edt, maximum_filter


# ----------------------------------------------------------------------------- helpers
def _rng(seed):
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-9)


def _up(field: np.ndarray, h: int, w: int) -> np.ndarray:
    return cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def _finish(field, h, w):
    """Upscale, sanitize, normalize."""
    f = _up(np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0), h, w)
    return _norm(np.nan_to_num(f, nan=0.0, posinf=0.0, neginf=0.0))


def _splat_lines(acc, xs, ys, res, val=1.0):
    """Anti-aliased-ish point splat of parametric samples into an accumulator (toroidal)."""
    ix = np.mod(np.round(xs).astype(np.int64), res)
    iy = np.mod(np.round(ys).astype(np.int64), res)
    np.add.at(acc, (iy, ix), val)


def _grid(res):
    t = np.linspace(0.0, 1.0, res, dtype=np.float32)
    return np.meshgrid(t, t)


# ============================================================================ ENGINES

def spirograph_lattice(h, w, seed, *, res=512):
    """Hypotrochoid (spirograph) GRID: a tiled lattice of inked spirograph curves whose
    R/r/d ratios vary per cell, accumulated as a fine line-density field."""
    rng = _rng(seed)
    acc = np.zeros((res, res), np.float32)
    cells = int(rng.integers(4, 6))
    cw = res / cells
    rad = cw * 0.46
    t = np.linspace(0.0, 2.0 * np.pi, 2600, dtype=np.float32)
    for gy in range(cells):
        for gx in range(cells):
            cx = (gx + 0.5) * cw
            cy = (gy + 0.5) * cw
            R = rng.uniform(0.55, 1.0)
            r = R / rng.uniform(2.2, 6.5)
            d = r * rng.uniform(1.4, 3.2)
            turns = int(rng.integers(7, 16))
            tt = t * turns
            k = (R - r) / max(r, 1e-3)
            x = (R - r) * np.cos(tt) + d * np.cos(k * tt)
            y = (R - r) * np.sin(tt) - d * np.sin(k * tt)
            sc = rad / (abs(R - r) + d + 1e-6)
            _splat_lines(acc, cx + x * sc, cy + y * sc, res)
    acc = np.log1p(acc)
    acc = cv2.GaussianBlur(acc, (0, 0), 0.7)
    # carve thin bright filigree over a faint backing so coverage is full + busy
    acc = acc + 0.18 * cv2.GaussianBlur(acc, (0, 0), 5.0)
    return _finish(acc, h, w)


def lissajous_lattice(h, w, seed, *, res=512):
    """Lissajous LATTICE: a 2D field built from products of harmonically-related sinusoids
    sin(a*x+px)*sin(b*y+py) summed over several (a,b) modes -> woven harmonic mesh."""
    rng = _rng(seed)
    X, Y = _grid(res)
    X = X * 2.0 * np.pi
    Y = Y * 2.0 * np.pi
    field = np.zeros((res, res), np.float32)
    modes = int(rng.integers(5, 8))
    for _ in range(modes):
        a = int(rng.integers(3, 14))
        b = int(rng.integers(3, 14))
        px = rng.uniform(0, 2 * np.pi)
        py = rng.uniform(0, 2 * np.pi)
        ph = rng.uniform(0, 2 * np.pi)
        amp = 1.0 / (1.0 + 0.4 * (a + b - 6))
        field += amp * np.sin(a * X + px) * np.sin(b * Y + py + ph)
    # ridge-fold to crush detail into sharp Lissajous contours
    field = np.abs(np.sin(field * np.pi * 1.7))
    field = field + 0.25 * np.abs(np.sin((X + Y) * rng.uniform(2, 5)))
    return _finish(field, h, w)


def maurer_rose(h, w, seed, *, res=512):
    """MAURER ROSE: connect points of a rose r=sin(n*theta) at k-degree steps with straight
    chords; the chord web forms the signature Maurer-rose moire of fine straight lines."""
    rng = _rng(seed)
    acc = np.zeros((res, res), np.float32)
    cx = cy = res / 2.0
    rad = res * 0.47
    # ---- guaranteed full-coverage rhodonea interference base (independent of chord density):
    # an analytic rose-petal moire so the field is never near-flat on sparse (n,d) seeds.
    X, Y = _grid(res)
    dx = (X - 0.5) * 2.0
    dy = (Y - 0.5) * 2.0
    rr = np.hypot(dx, dy)
    th = np.arctan2(dy, dx)
    n_a = int(rng.integers(3, 9))
    n_b = int(rng.integers(3, 9))
    base = (np.cos(n_a * th + rr * 9.0) * np.cos(n_b * th - rr * 7.0))
    base = np.abs(np.sin(base * np.pi * 1.5 + rr * 12.0))
    roses = int(rng.integers(2, 4))
    for _ in range(roses):
        n = int(rng.integers(3, 9))
        d = int(rng.integers(29, 121))
        rot = rng.uniform(0, np.pi)
        k = np.arange(0, 361, dtype=np.float32)
        theta = np.deg2rad(k * d)
        r = np.sin(n * theta)
        px = r * np.cos(theta + rot)
        py = r * np.sin(theta + rot)
        # densify each chord segment with linear interpolation
        steps = 60
        ts = np.linspace(0, 1, steps, dtype=np.float32)[None, :]
        x0 = px[:-1, None]; x1 = px[1:, None]
        y0 = py[:-1, None]; y1 = py[1:, None]
        xx = (x0 + (x1 - x0) * ts).ravel()
        yy = (y0 + (y1 - y0) * ts).ravel()
        _splat_lines(acc, cx + xx * rad, cy + yy * rad, res)
    acc = np.log1p(acc)
    acc = cv2.GaussianBlur(acc, (0, 0), 0.6)
    # bright chord web (filigree) laid over the analytic rose-interference base so coverage
    # is full and busy regardless of how sparse the chord set is for this seed.
    acc = 0.55 * _norm(acc) + 0.45 * base
    return _finish(acc, h, w)


def rhodonea_field(h, w, seed, *, res=512):
    """RHODONEA (rose curve) IMPLICIT FIELD: r - sin(k*theta) distance in polar over a tiled
    grid of rose centers -> overlapping petal interference, evaluated as a continuous field."""
    rng = _rng(seed)
    X, Y = _grid(res)
    field = np.zeros((res, res), np.float32)
    centers = int(rng.integers(6, 11))
    for _ in range(centers):
        ox = rng.uniform(0.1, 0.9)
        oy = rng.uniform(0.1, 0.9)
        kk = rng.choice([3, 4, 5, 6, 7, 8])
        freq = rng.uniform(7.0, 16.0)
        rot = rng.uniform(0, 2 * np.pi)
        dx = X - ox
        dy = Y - oy
        r = np.hypot(dx, dy) * freq
        th = np.arctan2(dy, dx) + rot
        petal = np.cos(kk * th)
        field += np.cos((r - petal) * np.pi) / (1.0 + r * 0.35)
    field = np.abs(field)
    field = field + 0.3 * np.abs(np.cos(field * 6.0))
    return _finish(field, h, w)


def fourier_epicycle(h, w, seed, *, res=512):
    """FOURIER EPICYCLE DRAWING: a closed contour reconstructed from random Fourier
    coefficients (chain of rotating circles), drawn many times with phase offsets to weave
    a dense epicyclic ribbon field."""
    rng = _rng(seed)
    acc = np.zeros((res, res), np.float32)
    cx = cy = res / 2.0
    rad = res * 0.46
    n_harm = int(rng.integers(6, 11))
    ks = np.concatenate([np.arange(1, n_harm + 1), -np.arange(1, n_harm + 1)]).astype(np.float32)
    amps = (rng.uniform(0.15, 1.0, ks.size) / (np.abs(ks) ** rng.uniform(0.8, 1.4))).astype(np.float32)
    phs = rng.uniform(0, 2 * np.pi, ks.size).astype(np.float32)
    t = np.linspace(0.0, 2.0 * np.pi, 4200, dtype=np.float32)
    passes = int(rng.integers(7, 12))
    for p in range(passes):
        drift = p * (2 * np.pi / passes) * rng.uniform(0.4, 1.2)
        ang = t[:, None] * ks[None, :] + phs[None, :] + drift
        z = amps[None, :] * np.exp(1j * ang)
        s = z.sum(axis=1)
        x = s.real
        y = s.imag
        # scale each closed contour to fill the disc (avoids tiny collapsed seeds)
        ext = max(np.abs(x).max(), np.abs(y).max(), 1e-6)
        x = x / ext
        y = y / ext
        _splat_lines(acc, cx + x * rad, cy + y * rad, res)
    acc = np.log1p(acc)
    acc = cv2.GaussianBlur(acc, (0, 0), 0.7)
    # analytic epicyclic interference base: radial harmonics summed over the same ks so the
    # field is intrinsically full-coverage and busy even on a degenerate contour seed.
    X, Y = _grid(res)
    rr = np.hypot((X - 0.5) * 2.0, (Y - 0.5) * 2.0)
    th = np.arctan2((Y - 0.5), (X - 0.5))
    base = np.zeros((res, res), np.float32)
    for kk, am, pp in zip(ks, amps, phs):
        base += am * np.cos(kk * th + rr * (6.0 + abs(kk)) + pp)
    base = np.abs(np.sin(base * 1.6 + rr * 10.0))
    acc = 0.55 * _norm(acc) + 0.45 * base
    return _finish(acc, h, w)


def superformula_field(h, w, seed, *, res=512):
    """SUPERFORMULA (Gielis) FIELD: the generalized superellipse radius r(theta;m,n1,n2,n3)
    used as an implicit boundary over a tiled grid of supershapes -> organic faceted cells."""
    rng = _rng(seed)
    X, Y = _grid(res)
    field = np.zeros((res, res), np.float32)
    cells = int(rng.integers(3, 5))
    cw = 1.0 / cells
    for gy in range(cells):
        for gx in range(cells):
            ox = (gx + 0.5) * cw
            oy = (gy + 0.5) * cw
            m = rng.integers(3, 12)
            n1 = rng.uniform(0.3, 4.0)
            n2 = rng.uniform(0.3, 6.0)
            n3 = rng.uniform(0.3, 6.0)
            a = b = 1.0
            rot = rng.uniform(0, 2 * np.pi)
            dx = (X - ox) / (cw * 0.55)
            dy = (Y - oy) / (cw * 0.55)
            r = np.hypot(dx, dy)
            phi = np.arctan2(dy, dx) + rot
            t1 = np.abs(np.cos(m * phi / 4.0) / a) ** n2
            t2 = np.abs(np.sin(m * phi / 4.0) / b) ** n3
            rr = (t1 + t2) ** (-1.0 / n1)
            rr = np.nan_to_num(rr, nan=0.0, posinf=0.0)
            # implicit signed band: rings of the supershape boundary
            band = np.cos((r / (rr + 1e-3)) * np.pi * 3.0)
            field += np.abs(band) / (1.0 + r * 0.6)
    field += 0.25 * np.abs(np.sin(field * 5.0))
    return _finish(field, h, w)


def butterfly_curve(h, w, seed, *, res=512):
    """BUTTERFLY CURVE swarm (Fay's transcendental butterfly): a scattered field of
    butterfly curves at varied scales/rotations, accumulated into a winged line-density."""
    rng = _rng(seed)
    acc = np.zeros((res, res), np.float32)
    t = np.linspace(0.0, 12.0 * np.pi, 6000, dtype=np.float32)
    base = np.exp(np.cos(t)) - 2.0 * np.cos(4.0 * t) - np.sin(t / 12.0) ** 5
    bx = np.sin(t) * base
    by = np.cos(t) * base
    bx = bx / (np.abs(bx).max() + 1e-6)
    by = by / (np.abs(by).max() + 1e-6)
    swarm = int(rng.integers(7, 13))
    for _ in range(swarm):
        cx = rng.uniform(0.12, 0.88) * res
        cy = rng.uniform(0.12, 0.88) * res
        sc = rng.uniform(0.10, 0.30) * res
        rot = rng.uniform(0, 2 * np.pi)
        ca, sa = np.cos(rot), np.sin(rot)
        x = bx * ca - by * sa
        y = bx * sa + by * ca
        _splat_lines(acc, cx + x * sc, cy + y * sc, res)
    acc = np.log1p(acc)
    acc = cv2.GaussianBlur(acc, (0, 0), 0.7)
    halo = cv2.GaussianBlur(acc, (0, 0), 5.0)
    acc = acc + 0.45 * halo + 0.28 * np.abs(np.cos(_norm(halo) * np.pi * 5.0))
    return _finish(acc, h, w)


def clelie_spiral(h, w, seed, *, res=512):
    """CLELIE SPHERICAL SPIRAL projection: a Clelia curve on a sphere (phi = c*theta)
    orthographically projected, layered at several c -> interlocking globe-spiral lattice."""
    rng = _rng(seed)
    acc = np.zeros((res, res), np.float32)
    cx = cy = res / 2.0
    rad = res * 0.47
    layers = int(rng.integers(3, 6))
    theta = np.linspace(0.0, 2.0 * np.pi, 7000, dtype=np.float32)
    for _ in range(layers):
        c = rng.uniform(6.0, 22.0)
        tilt = rng.uniform(0.4, 1.2)
        rot = rng.uniform(0, 2 * np.pi)
        phi = c * theta  # latitude sweep
        # spherical -> cartesian, then orthographic with a tilt
        sx = np.sin(theta) * np.cos(phi)
        sy = np.sin(theta) * np.sin(phi)
        sz = np.cos(theta)
        x = sx
        y = sy * np.cos(tilt) - sz * np.sin(tilt)
        ca, sa = np.cos(rot), np.sin(rot)
        xr = x * ca - y * sa
        yr = x * sa + y * ca
        _splat_lines(acc, cx + xr * rad, cy + yr * rad, res)
    acc = np.log1p(acc)
    acc = cv2.GaussianBlur(acc, (0, 0), 0.6)
    halo = cv2.GaussianBlur(acc, (0, 0), 5.0)
    acc = acc + 0.4 * halo + 0.25 * np.abs(np.cos(_norm(halo) * np.pi * 6.0))
    return _finish(acc, h, w)


def cardioid_caustic(h, w, seed, *, res=512):
    """CARDIOID CAUSTIC (string-art envelope): the caustic envelope formed by chords
    n -> 2n mod N on a circle, drawn as a dense line bundle whose envelope is the cardioid /
    nephroid family. Multiplier varies to layer cardioid+nephroid+higher caustics."""
    rng = _rng(seed)
    acc = np.zeros((res, res), np.float32)
    cx = cy = res / 2.0
    rad = res * 0.47
    layers = int(rng.integers(2, 4))
    for _ in range(layers):
        N = int(rng.integers(180, 380))
        mult = int(rng.choice([2, 3, 4, 5]))
        rot = rng.uniform(0, 2 * np.pi)
        sub = rng.uniform(0.7, 1.0)
        n = np.arange(N, dtype=np.float32)
        a1 = 2 * np.pi * n / N + rot
        a2 = 2 * np.pi * (mult * n % N) / N + rot
        x0 = np.cos(a1); y0 = np.sin(a1)
        x1 = np.cos(a2); y1 = np.sin(a2)
        steps = 90
        ts = np.linspace(0, 1, steps, dtype=np.float32)[None, :]
        xx = (x0[:, None] + (x1 - x0)[:, None] * ts).ravel()
        yy = (y0[:, None] + (y1 - y0)[:, None] * ts).ravel()
        _splat_lines(acc, cx + xx * rad * sub, cy + yy * rad * sub, res)
    acc = np.log1p(acc)
    acc = cv2.GaussianBlur(acc, (0, 0), 0.6)
    acc += 0.18 * cv2.GaussianBlur(acc, (0, 0), 4.0)
    return _finish(acc, h, w)


def wallpaper_p6m(h, w, seed, *, res=512):
    """WALLPAPER-GROUP (p6m / p4m) WAVE SUM: a sum of plane waves whose wavevectors are the
    symmetry directions of a hexagonal (or square) lattice -> a perfectly symmetric, crushed
    crystallographic interference field with the exact wallpaper symmetry group."""
    rng = _rng(seed)
    X, Y = _grid(res)
    X = (X - 0.5) * 2.0
    Y = (Y - 0.5) * 2.0
    hexagonal = bool(rng.integers(0, 2))
    n_dirs = 3 if hexagonal else 2  # 6-fold vs 4-fold base directions (mirror gives full group)
    field = np.zeros((res, res), np.float32)
    harmonics = int(rng.integers(3, 6))
    base_freq = rng.uniform(9.0, 18.0)
    glob_rot = rng.uniform(0, 2 * np.pi)
    for d in range(n_dirs):
        ang = glob_rot + d * (np.pi / n_dirs)
        kx = np.cos(ang)
        ky = np.sin(ang)
        for hh in range(1, harmonics + 1):
            f = base_freq * hh
            amp = 1.0 / (hh ** 1.1)
            ph = rng.uniform(0, 2 * np.pi)
            # cos of |k·r| enforces the mirror symmetry of p4m/p6m
            field += amp * np.cos(np.abs(f * (kx * X + ky * Y)) + ph)
    field = np.abs(np.sin(field * 1.3))
    return _finish(field, h, w)


def epitrochoid_weave(h, w, seed, *, res=512):
    """EPITROCHOID OFFSET-CURVE WEAVE: families of epitrochoids (rolling-circle curves)
    with incrementally offset phase, sampled as a parallel-curve bundle -> a woven guilloche-
    free harmonic basket distinct from the spirograph (epi = external rolling, parallel
    offset family, not a tiled grid)."""
    rng = _rng(seed)
    acc = np.zeros((res, res), np.float32)
    cx = cy = res / 2.0
    rad = res * 0.46
    R = rng.uniform(1.0, 2.0)
    r = R / rng.uniform(3.0, 9.0)
    d = r * rng.uniform(1.2, 3.0)
    turns = int(rng.integers(10, 22))
    t = np.linspace(0.0, 2.0 * np.pi * turns, 9000, dtype=np.float32)
    k = (R + r) / max(r, 1e-3)
    bx = (R + r) * np.cos(t) - d * np.cos(k * t)
    by = (R + r) * np.sin(t) - d * np.sin(k * t)
    sc = rad / ((R + r) + d + 1e-6)
    family = int(rng.integers(8, 16))
    for i in range(family):
        ph = i * (2 * np.pi / family)
        rr = 1.0 + 0.12 * np.sin(ph * 3.0)
        ca, sa = np.cos(ph * 0.25), np.sin(ph * 0.25)
        x = (bx * ca - by * sa) * rr
        y = (bx * sa + by * ca) * rr
        _splat_lines(acc, cx + x * sc, cy + y * sc, res)
    acc = np.log1p(acc)
    acc = cv2.GaussianBlur(acc, (0, 0), 0.7)
    acc += 0.18 * cv2.GaussianBlur(acc, (0, 0), 5.0)
    return _finish(acc, h, w)


ENGINES = {
    "spirograph_lattice": spirograph_lattice,
    "lissajous_lattice": lissajous_lattice,
    "maurer_rose": maurer_rose,
    "rhodonea_field": rhodonea_field,
    "fourier_epicycle": fourier_epicycle,
    "superformula_field": superformula_field,
    "butterfly_curve": butterfly_curve,
    "clelie_spiral": clelie_spiral,
    "cardioid_caustic": cardioid_caustic,
    "wallpaper_p6m": wallpaper_p6m,
    "epitrochoid_weave": epitrochoid_weave,
}


if __name__ == "__main__":
    import time

    SZ = 1024
    print(f"{'engine':22s} {'secs':>6s} {'fine':>6s} {'std':>6s} {'min':>5s} {'max':>5s}  status")
    print("-" * 72)
    fails = 0
    for name, fn in ENGINES.items():
        t0 = time.time()
        f = fn(SZ, SZ, 12345)
        secs = time.time() - t0
        f = np.asarray(f, dtype=np.float32)
        fine = (f - cv2.GaussianBlur(f, (0, 0), 8)).std() / (f.std() + 1e-6)
        std = f.std()
        finite = bool(np.isfinite(f).all())
        in01 = bool(f.min() >= -1e-4 and f.max() <= 1.0 + 1e-4)
        ok = (secs < 2.5) and (fine >= 0.12) and (std > 0.06) and finite and in01 \
            and f.shape == (SZ, SZ)
        if not ok:
            fails += 1
        status = "OK" if ok else "FAIL"
        print(f"{name:22s} {secs:6.3f} {fine:6.3f} {std:6.3f} "
              f"{f.min():5.2f} {f.max():5.2f}  {status}")
    print("-" * 72)
    print(f"{len(ENGINES)} engines, {fails} fail(s)")
