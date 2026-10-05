"""COMPLEX DYNAMICS pack — escape-time & complex-dynamical field generators.

Each engine returns a float32 scalar FIELD in [0,1], shape (h, w), full-coverage and
high-frequency (premium crushed detail across a 2048px car). Computed at low `res`,
upscaled with cv2, then normalized to 0..1. Pure numpy + cv2 + scipy. Deterministic by
seed via np.random.default_rng.

These are GENUINELY DIFFERENT algorithms in the escape-time / complex-dynamics family:

  * mandelbrot_orbit_trap  — z->z^2+c, distance-to-orbit-trap (point/cross/ring) coloring.
  * julia_smooth           — Julia set z->z^2+c, smooth (continuous) escape-time potential.
  * burning_ship           — z->(|Re|+i|Im|)^2 + c escape time; the spiky "armada" geometry.
  * newton_basins          — Newton's method roots of p(z); basin index XOR iteration shade.
  * nova_fractal           — relaxed Newton (Nova): z - R*p/p' + c; basin/speed hybrid field.
  * phoenix_fractal        — z_{n+1}=z^2 + c + p*z_{n-1} (memory term) escape potential.
  * magnet_fractal         — Magnet type-I rational map ((z^2+c-1)/(2z+c-2))^2 escape.
  * domain_coloring        — phase of a meromorphic f(z)=prod(z-zk)/prod(z-pk), arg as field
                             with log-modulus contour grid (full plane, no escape).
  * nebulabrot_density     — Buddhabrot/nebulabrot: density of ESCAPING orbit trajectories.
  * lyapunov_marble        — Lyapunov-exponent fractal over a logistic map driven by an
                             A/B sequence on the (a,b) plane (Markus-Lyapunov).
  * collatz_escape         — smooth escape of a holomorphic Collatz extension
                             f(z)=0.25*(2+7z-(2+5z)cos(pi z)) (different recurrence/geometry).

11 engines, all distinct math.
"""
from __future__ import annotations

import time

import cv2
import numpy as np

# Escape-time iteration intentionally lets points blow up to inf before they are culled;
# the overflow/invalid is expected and handled (nan_to_num on output). Silence the noise.
np.seterr(over="ignore", invalid="ignore", divide="ignore")


# --------------------------------------------------------------------------- helpers
def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-9)


def _up(field: np.ndarray, h: int, w: int) -> np.ndarray:
    field = np.nan_to_num(field.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    return cv2.resize(field, (w, h), interpolation=cv2.INTER_LINEAR)


def _grid(res, cx, cy, span, rng=None, rot=0.0):
    """Complex grid centered at (cx,cy) with width `span`, optional rotation."""
    lin = np.linspace(-0.5, 0.5, res, dtype=np.float64)
    gx, gy = np.meshgrid(lin * span, lin * span)
    if rot:
        c, s = np.cos(rot), np.sin(rot)
        gx, gy = gx * c - gy * s, gx * s + gy * c
    return (gx + cx) + 1j * (gy + cy)


def _hifreq(field, rng, amount=0.6):
    """Inject crushed high-frequency texture keyed to the field's own gradient so the
    result is never a smooth ramp/blob even in slowly-varying basins. Multiplicative
    ridged modulation -> guarantees fineness without destroying the macro structure."""
    res = field.shape[0]
    n = rng.standard_normal((res, res)).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), 1.0)
    gy, gx = np.gradient(field.astype(np.float32))
    g = np.hypot(gx, gy)
    g = g / (g.max() + 1e-6)
    fine = np.abs(np.sin(field * 90.0 + n * 4.0)) ** 2
    return field * (1.0 - amount) + (0.5 + 0.5 * (fine - 0.5)) * amount + 0.15 * g


# --------------------------------------------------------------------------- 1. Mandelbrot orbit trap
def mandelbrot_orbit_trap(h, w, seed, *, res=512) -> np.ndarray:
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # interesting seahorse/spiral region near the boundary
    cx = rng.uniform(-0.75, -0.70)
    cy = rng.uniform(0.08, 0.16)
    span = rng.uniform(0.012, 0.05)
    C = _grid(res, cx, cy, span, rng, rot=rng.uniform(0, np.pi))
    Z = np.zeros_like(C)
    trap = float(rng.uniform(0.0, 0.6)) + 0.0j  # point trap (orbit-distance to a point)
    mind = np.full((res, res), 1e9, dtype=np.float32)
    mind2 = np.full((res, res), 1e9, dtype=np.float32)
    C = C.astype(np.complex64)
    Z = Z.astype(np.complex64)
    tr = np.float32(trap.real)
    for _ in range(70):
        Z = Z * Z + C
        zr, zi = Z.real, Z.imag
        d = np.hypot(zr - tr, zi)
        np.minimum(mind, d, out=mind)
        # cross trap (distance to nearest axis) for a second high-freq channel
        cr = np.minimum(np.abs(zr), np.abs(zi))
        np.minimum(mind2, cr, out=mind2)
    f = np.log1p(1.0 / (mind + 1e-3)) + 0.6 * np.log1p(1.0 / (mind2 + 1e-3))
    f = _norm(f)
    f = _hifreq(f, rng, amount=0.45)
    return _norm(_up(f, h, w))


# --------------------------------------------------------------------------- 2. Julia (smooth)
def julia_smooth(h, w, seed, *, res=512) -> np.ndarray:
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # pick c on/near interesting Julia parameters
    theta = rng.uniform(0, 2 * np.pi)
    r = rng.uniform(0.70, 0.79)
    c = r * np.cos(theta) + 1j * r * np.sin(theta)
    span = rng.uniform(2.6, 3.4)
    Z = _grid(res, 0.0, 0.0, span, rng, rot=rng.uniform(0, np.pi)).astype(np.complex64)
    c = np.complex64(c)
    n_iter = np.zeros((res, res), dtype=np.float32)
    alive = np.ones((res, res), bool)
    bail = 1e6
    for i in range(130):
        Z[alive] = Z[alive] * Z[alive] + c
        mag2 = Z.real * Z.real + Z.imag * Z.imag
        esc = mag2 > bail
        newly = esc & alive
        # smooth (continuous) iteration count
        n_iter[newly] = i + 1 - np.log(np.log(np.sqrt(mag2[newly]) + 1e-12) / np.log(bail)) / np.log(2)
        alive &= ~esc
    # interior gets potential from final magnitude so it isn't flat
    mag2 = Z.real * Z.real + Z.imag * Z.imag
    n_iter[alive] = 130 + np.tanh(np.log1p(mag2[alive]))
    f = _norm(np.sqrt(np.abs(n_iter)))
    f = _hifreq(f, rng, amount=0.4)
    return _norm(_up(f, h, w))


# --------------------------------------------------------------------------- 3. Burning Ship
def burning_ship(h, w, seed, *, res=512) -> np.ndarray:
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # zoom into the masts/antennae region
    cx = rng.uniform(-1.78, -1.72)
    cy = rng.uniform(-0.045, 0.02)
    span = rng.uniform(0.06, 0.18)
    C = _grid(res, cx, cy, span, rng)
    zx = np.zeros((res, res), np.float32)
    zy = np.zeros((res, res), np.float32)
    cxr, cyr = C.real.astype(np.float32), C.imag.astype(np.float32)
    n_iter = np.zeros((res, res))
    alive = np.ones((res, res), bool)
    bail = 1e4
    for i in range(80):
        ax = np.abs(zx)
        ay = np.abs(zy)
        nx = ax * ax - ay * ay + cxr
        ny = 2.0 * ax * ay + cyr
        # freeze escaped points so multiply doesn't keep overflowing
        zx = np.where(alive, nx, zx)
        zy = np.where(alive, ny, zy)
        mag2 = zx * zx + zy * zy
        esc = (mag2 > bail) & alive
        n_iter[esc] = i + 1 - np.log(np.log(np.sqrt(mag2[esc])) / np.log(bail)) / np.log(2)
        alive &= ~(mag2 > bail)
    n_iter[alive] = n_iter.max() if n_iter.max() > 0 else 1.0
    f = _norm(np.power(_norm(n_iter), 0.55))
    f = _hifreq(f, rng, amount=0.45)
    return _norm(_up(f, h, w))


# --------------------------------------------------------------------------- 4. Newton basins
def newton_basins(h, w, seed, *, res=512) -> np.ndarray:
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # random complex polynomial roots -> basin map
    nroots = int(rng.integers(4, 8))
    ang = np.sort(rng.uniform(0, 2 * np.pi, nroots))
    rad = rng.uniform(0.7, 1.3, nroots)
    roots = rad * np.cos(ang) + 1j * rad * np.sin(ang)
    coeffs = np.poly(roots)            # p(z) coefficients
    dcoeffs = np.polyder(coeffs)       # p'(z)
    span = rng.uniform(2.6, 3.4)
    Z = _grid(res, 0.0, 0.0, span, rng, rot=rng.uniform(0, np.pi)).astype(np.complex64)
    relax = rng.uniform(0.9, 1.4)
    iters_used = np.zeros((res, res), np.float32)
    coeffs = coeffs.astype(np.complex64)
    dcoeffs = dcoeffs.astype(np.complex64)
    roots = roots.astype(np.complex64)
    for i in range(18):
        p = np.polyval(coeffs, Z)
        dp = np.polyval(dcoeffs, Z)
        step = relax * p / (dp + 1e-12)
        Z = Z - step
        moved = np.abs(step) > 1e-4
        iters_used[moved] = i + 1
    # which root did each pixel converge to (loop over roots, cheaper than 3D broadcast)
    basin = np.zeros((res, res), dtype=np.float64)
    best = np.full((res, res), 1e18)
    for ri, r0 in enumerate(roots):
        d = np.abs(Z - r0)
        upd = d < best
        best[upd] = d[upd]
        basin[upd] = ri
    # combine basin hue index with convergence-speed shading -> sharp web
    f = np.mod(basin / max(nroots - 1, 1) + iters_used / 60.0 * 0.9, 1.0)
    f = _norm(f)
    # edge enhance so basin boundaries crush to fine filigree
    edges = np.abs(cv2.Laplacian(basin.astype(np.float32), cv2.CV_32F, ksize=3))
    f = _norm(f + 0.5 * _norm(edges))
    f = _hifreq(f, rng, amount=0.35)
    return _norm(_up(f, h, w))


# --------------------------------------------------------------------------- 5. Nova fractal
def nova_fractal(h, w, seed, *, res=512) -> np.ndarray:
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # Nova: z_{n+1} = z - R*(z^p - 1)/(p*z^(p-1)) + c   (relaxed Newton + additive c)
    p = int(rng.integers(3, 6))
    R = rng.uniform(0.9, 1.6)
    cx = rng.uniform(-0.4, 0.4)
    cy = rng.uniform(-0.4, 0.4)
    add_c = cx + 1j * cy
    span = rng.uniform(2.2, 3.2)
    Z = _grid(res, 0.0, 0.0, span, rng, rot=rng.uniform(0, np.pi)).astype(np.complex64)
    Z = Z + np.complex64(0.0001)
    add_c = np.complex64(add_c)
    speed = np.zeros((res, res), np.float32)
    prev = Z.copy()
    converged = np.zeros((res, res), bool)
    for i in range(45):
        zpm1 = Z ** (p - 1)         # integer power -> fast repeated multiply
        zp = zpm1 * Z
        num = zp - 1.0
        den = p * zpm1 + 1e-12
        Z = Z - R * num / den + add_c
        delta = np.abs(Z - prev)
        done = (delta < 1e-5) & (~converged)
        speed[done] = i
        converged |= done
        prev = Z.copy()
    speed[~converged] = 45
    # phase of final z for fine angular structure
    phase = (np.angle(Z) + np.pi) / (2 * np.pi)
    f = _norm(np.mod(_norm(speed) * 3.0 + phase * 2.0, 1.0))
    f = _hifreq(f, rng, amount=0.4)
    return _norm(_up(f, h, w))


# --------------------------------------------------------------------------- 6. Phoenix fractal
def phoenix_fractal(h, w, seed, *, res=512) -> np.ndarray:
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # z_{n+1} = z_n^2 + c + p * z_{n-1}   (memory term -> flame/feather geometry)
    c = complex(rng.uniform(0.50, 0.60), 0.0)
    pp = complex(rng.uniform(-0.6, -0.4), rng.uniform(-0.05, 0.05))
    span = rng.uniform(2.4, 3.4)
    # iterate over a Julia-style plane; classic Phoenix uses (y,x) swapped axes
    Z = _grid(res, 0.0, 0.0, span, rng, rot=np.pi / 2).astype(np.complex64)
    c = np.complex64(c)
    pp = np.complex64(pp)
    Zprev = np.zeros_like(Z)
    n_iter = np.zeros((res, res), np.float32)
    alive = np.ones((res, res), bool)
    bail = 1e6
    for i in range(95):
        Znew = Z * Z + c + pp * Zprev
        Zprev = np.where(alive, Z, Zprev)
        Z = np.where(alive, Znew, Z)
        mag2 = Z.real * Z.real + Z.imag * Z.imag
        esc = (mag2 > bail) & alive
        n_iter[esc] = i + 1 - np.log(np.log(np.sqrt(mag2[esc])) / np.log(bail)) / np.log(2)
        alive &= ~(mag2 > bail)
    mag2 = Z.real * Z.real + Z.imag * Z.imag
    n_iter[alive] = 115 + np.tanh(np.log1p(mag2[alive]))
    f = _norm(np.power(_norm(n_iter), 0.6))
    f = _hifreq(f, rng, amount=0.4)
    return _norm(_up(f, h, w))


# --------------------------------------------------------------------------- 7. Magnet fractal
def magnet_fractal(h, w, seed, *, res=512) -> np.ndarray:
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # Magnet type-I:  z_{n+1} = ((z^2 + c - 1) / (2z + c - 2))^2
    cx = rng.uniform(-1.2, 2.2)
    cy = rng.uniform(-1.4, 1.4)
    c = complex(cx, cy)
    span = rng.uniform(2.4, 4.0)
    Z = _grid(res, rng.uniform(0.2, 1.2), 0.0, span, rng, rot=rng.uniform(0, np.pi)).astype(np.complex64)
    c = np.complex64(c)
    n_iter = np.zeros((res, res), np.float32)
    alive = np.ones((res, res), bool)
    bail = 1e5
    for i in range(70):
        num = Z * Z + (c - 1.0)
        den = 2.0 * Z + (c - 2.0)
        r = num / (den + 1e-12)
        Z = r * r
        # magnet fractals converge to z=1 (the fixed point) OR escape
        conv = (np.abs(Z.real - 1.0) + np.abs(Z.imag)) < 1e-4
        mag2 = Z.real * Z.real + Z.imag * Z.imag
        esc = (mag2 > bail) & alive
        n_iter[esc] = i
        done = (conv & alive)
        n_iter[done] = i + 0.5
        alive &= ~(esc | conv)
    n_iter[alive] = 70
    f = _norm(np.power(_norm(n_iter), 0.5))
    # angular detail from final phase
    phase = (np.angle(Z) + np.pi) / (2 * np.pi)
    f = _norm(f + 0.4 * phase)
    f = _hifreq(f, rng, amount=0.4)
    return _norm(_up(f, h, w))


# --------------------------------------------------------------------------- 8. Domain coloring
def domain_coloring(h, w, seed, *, res=512) -> np.ndarray:
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # meromorphic f(z) = prod(z - zeros) / prod(z - poles) ; field = blend of phase + |f| contours
    nz = int(rng.integers(3, 6))
    npoles = int(rng.integers(2, 5))
    span = rng.uniform(3.0, 4.5)
    zeros = rng.uniform(-1.4, 1.4, nz) + 1j * rng.uniform(-1.4, 1.4, nz)
    poles = rng.uniform(-1.4, 1.4, npoles) + 1j * rng.uniform(-1.4, 1.4, npoles)
    Z = _grid(res, 0.0, 0.0, span, rng, rot=rng.uniform(0, np.pi))
    f = np.ones((res, res), dtype=np.complex128)
    for z0 in zeros:
        f = f * (Z - z0)
    for p0 in poles:
        f = f / (Z - p0 + 1e-9)
    phase = (np.angle(f) + np.pi) / (2 * np.pi)            # 0..1 hue-like phase
    mod = np.log(np.abs(f) + 1e-9)
    # log-modulus contour grid (fractional part) -> crushed concentric detail
    contour = np.abs(np.sin(mod * np.pi * 2.0)) ** 0.4
    # phase isolines too
    pgrid = np.abs(np.sin(phase * np.pi * float(rng.integers(8, 16)))) ** 0.5
    field = _norm(phase * 0.6 + contour * 0.5 + pgrid * 0.3)
    field = _hifreq(field, rng, amount=0.35)
    return _norm(_up(field, h, w))


# --------------------------------------------------------------------------- 9. Nebulabrot density
def nebulabrot_density(h, w, seed, *, res=512) -> np.ndarray:
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # Buddhabrot/nebulabrot: accumulate the trajectories of ESCAPING points.
    acc = np.zeros((res, res), dtype=np.float64)
    lo, hi = -2.1, 1.1
    lo_y, hi_y = -1.6, 1.6
    sx = (res - 1) / (hi - lo)
    sy = (res - 1) / (hi_y - lo_y)
    nsamp = 180000
    max_iter = 120
    cre = rng.uniform(lo, hi, nsamp).astype(np.float32)
    cim = rng.uniform(lo_y, hi_y, nsamp).astype(np.float32)
    c = (cre + 1j * cim).astype(np.complex64)
    z = np.zeros(nsamp, dtype=np.complex64)
    # quick pre-pass: which escape (we only plot escaping orbits)
    alive = np.ones(nsamp, bool)
    escaped = np.zeros(nsamp, bool)
    # record full path for escaping points -> store iteration history compactly
    paths_x = np.empty((max_iter, nsamp), dtype=np.float32)
    paths_y = np.empty((max_iter, nsamp), dtype=np.float32)
    nstep = np.zeros(nsamp, dtype=np.int32)
    for i in range(max_iter):
        z[alive] = z[alive] * z[alive] + c[alive]
        paths_x[i] = z.real
        paths_y[i] = z.imag
        mag2 = z.real * z.real + z.imag * z.imag
        esc = (mag2 > 4.0) & alive
        escaped |= esc
        nstep[esc] = i + 1
        alive &= ~(mag2 > 4.0)
    # accumulate paths of escaped points up to their escape step
    idx = np.where(escaped)[0]
    for k in idx_chunks(idx, 40000):
        ns = nstep[k]
        for i in range(max_iter):
            sel = k[ns > i]
            if sel.size == 0:
                continue
            xr = paths_x[i, sel]
            yr = paths_y[i, sel]
            ix = ((xr - lo) * sx).astype(np.int32)
            iy = ((yr - lo_y) * sy).astype(np.int32)
            m = (ix >= 0) & (ix < res) & (iy >= 0) & (iy < res)
            np.add.at(acc, (iy[m], ix[m]), 1.0)
    acc = np.log1p(acc)
    f = _norm(acc)
    f = cv2.GaussianBlur(f, (0, 0), 0.6)
    f = _hifreq(f, rng, amount=0.3)
    return _norm(_up(f, h, w))


def idx_chunks(arr, n):
    for i in range(0, arr.size, n):
        yield arr[i:i + n]


# --------------------------------------------------------------------------- 10. Lyapunov (Markus) fractal
def lyapunov_marble(h, w, seed, *, res=512) -> np.ndarray:
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # Markus-Lyapunov: logistic map x->r*x*(1-x) where r alternates between a,b
    # by a fixed binary sequence; field = Lyapunov exponent over the (a,b) plane.
    seqlen = int(rng.integers(4, 9))
    seq = rng.integers(0, 2, seqlen)
    if seq.sum() == 0 or seq.sum() == seqlen:
        seq[0] = 1 - seq[0]
    a0, a1 = rng.uniform(2.4, 3.0), rng.uniform(3.0, 4.0)
    b0, b1 = rng.uniform(2.4, 3.0), rng.uniform(3.0, 4.0)
    lin = np.linspace(0, 1, res)
    A, B = np.meshgrid(a0 + (a1 - a0) * lin, b0 + (b1 - b0) * lin)
    x = np.full((res, res), 0.5)
    lyap = np.zeros((res, res))
    warm = 50
    total = 150
    seq_pat = [A if seq[n % seqlen] == 0 else B for n in range(seqlen)]
    for n in range(total):
        r = seq_pat[n % seqlen]
        x = r * x * (1.0 - x)
        if n >= warm:
            deriv = np.abs(r * (1.0 - 2.0 * x)) + 1e-12
            lyap += np.log(deriv)
    lyap /= float(total - warm)
    # chaotic (positive) vs stable (negative) regions -> sharp marbled bands
    f = np.tanh(lyap)
    f = _norm(f)
    # the boundary is naturally fine; amplify
    f = _hifreq(f, rng, amount=0.4)
    return _norm(_up(f, h, w))


# --------------------------------------------------------------------------- 11. Collatz holomorphic escape
def collatz_escape(h, w, seed, *, res=512) -> np.ndarray:
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # Holomorphic extension of the Collatz map:
    #   f(z) = 0.25 * (2 + 7z - (2 + 5z) cos(pi z))
    # iterate and measure smooth escape -> ornate, distinctly-non-Mandelbrot lattice.
    span = rng.uniform(3.5, 6.0)
    cx = rng.uniform(-1.0, 2.0)
    cy = rng.uniform(-1.0, 1.0)
    Z = _grid(res, cx, cy, span, rng, rot=rng.uniform(0, np.pi)).astype(np.complex64)
    n_iter = np.zeros((res, res), np.float32)
    alive = np.ones((res, res), bool)
    bail = 1e8
    for i in range(48):
        Za = Z[alive]
        cz = np.cos(np.pi * Za)
        Z[alive] = 0.25 * (2.0 + 7.0 * Za - (2.0 + 5.0 * Za) * cz)
        mag2 = Z.real * Z.real + Z.imag * Z.imag
        esc = (mag2 > bail) & alive
        with np.errstate(invalid="ignore", divide="ignore"):
            sm = i + 1 - np.log(np.log(np.sqrt(mag2) + 1e-12) + 1e-12) / np.log(2)
        n_iter[esc] = sm[esc]
        alive &= ~(mag2 > bail)
    n_iter[alive] = n_iter[np.isfinite(n_iter)].max() if np.isfinite(n_iter).any() else 1.0
    n_iter = np.nan_to_num(n_iter, nan=0.0, posinf=0.0, neginf=0.0)
    f = _norm(np.power(_norm(n_iter), 0.5))
    f = _hifreq(f, rng, amount=0.42)
    return _norm(_up(f, h, w))


# --------------------------------------------------------------------------- registry
ENGINES = {
    "mandelbrot_orbit_trap": mandelbrot_orbit_trap,
    "julia_smooth": julia_smooth,
    "burning_ship": burning_ship,
    "newton_basins": newton_basins,
    "nova_fractal": nova_fractal,
    "phoenix_fractal": phoenix_fractal,
    "magnet_fractal": magnet_fractal,
    "domain_coloring": domain_coloring,
    "nebulabrot_density": nebulabrot_density,
    "lyapunov_marble": lyapunov_marble,
    "collatz_escape": collatz_escape,
}


# --------------------------------------------------------------------------- self-test
if __name__ == "__main__":
    H = W = 1024
    print(f"{'engine':<24} {'secs':>7} {'fine':>7} {'min':>6} {'max':>6} {'std':>6}  status")
    print("-" * 78)
    all_ok = True
    for name, fn in ENGINES.items():
        t0 = time.time()
        f = fn(H, W, 12345, res=512)
        dt = time.time() - t0
        f = np.asarray(f, dtype=np.float32)
        fine = float((f - cv2.GaussianBlur(f, (0, 0), 8)).std() / (f.std() + 1e-6))
        finite = bool(np.isfinite(f).all())
        std = float(f.std())
        ok = (dt < 2.5) and (fine >= 0.12) and (std > 0.06) and finite \
            and f.min() >= -1e-4 and f.max() <= 1.0 + 1e-4
        all_ok &= ok
        status = "OK" if ok else "FAIL " + ("slow " if dt >= 2.5 else "") + \
            ("flat " if std <= 0.06 else "") + ("smooth " if fine < 0.12 else "") + \
            ("nan " if not finite else "")
        print(f"{name:<24} {dt:7.3f} {fine:7.3f} {f.min():6.3f} {f.max():6.3f} {std:6.3f}  {status}")
    print("-" * 78)
    print("ALL PASS" if all_ok else "SOME FAILED")
