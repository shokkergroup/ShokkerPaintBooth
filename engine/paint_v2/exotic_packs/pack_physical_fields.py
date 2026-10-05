"""PHYSICAL / FLUID FIELDS — generative-math engines for Shokker Paint Booth.

Each engine produces an intricate, FULL-COVERAGE scalar field in 0..1 over a whole
2048px car. Each is a DIFFERENT kind of math (a distinct physical/numerical algorithm),
not a recolor of another:

  * stable_fluids_ink   — Stam's stable-fluids semi-Lagrangian advection of an ink scalar
                          through a self-stirred incompressible velocity field.
  * curl_smoke          — buoyant smoke: density advected through curl-noise turbulence with
                          vorticity-confinement wisps.
  * magnetic_dipole     — analytic superposition of magnetic dipole fields; field-line
                          density (|B| streak integral) gives the iron-filings look.
  * electrostatic_equipotential — Poisson solve (FFT) for the potential of random point
                          charges; equipotential contour banding.
  * schlieren_refraction — knife-edge Schlieren: deflection of light by the gradient of a
                          turbulent refractive index, shadowgraph shock fronts.
  * ferrofluid_spikes   — Rosensweig instability: hex-packed peaks whose amplitude follows the
                          dispersion of a magnetised fluid surface (Bessel-like cones).
  * dla_aggregate       — diffusion-limited aggregation grown on a lattice (random walkers
                          sticking) -> fractal dendritic frost/coral.
  * eden_growth         — Eden cluster: surface-tension-free stochastic accretion -> rough
                          self-affine blobs with crinkled boundaries.
  * viscous_fingering   — Saffman-Taylor: pressure-driven Laplacian growth of a low-viscosity
                          fluid into a high-viscosity one -> Hele-Shaw fingers.
  * curl_streaklines    — line-integral-convolution of a divergence-free vorticity field ->
                          dense silky streaklines (a DIFFERENT renderer than curl_smoke).
  * potential_flow_cylinders — complex-potential flow (uniform + doublets + vortices) past
                          obstacles; streamfunction contours with wake shedding.

Pure numpy + cv2 + scipy. Deterministic by seed. Computed at low res then upscaled.
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from scipy import ndimage


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _rng(seed):
    return np.random.default_rng(int(seed) & 0xffffffff)


def _norm(a):
    a = a.astype(np.float32)
    p = float(np.ptp(a))
    return (a - a.min()) / (p + 1e-9)


def _up(field, h, w):
    return cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def _fbm(res, rng, octaves=5, base=4, gain=0.55):
    """Periodic fractal value noise via summed upsampled white-noise lattices."""
    out = np.zeros((res, res), np.float32)
    amp = 1.0
    tot = 0.0
    for o in range(octaves):
        n = base * (2 ** o)
        n = min(n, res)
        lat = rng.standard_normal((n, n)).astype(np.float32)
        layer = cv2.resize(lat, (res, res), interpolation=cv2.INTER_CUBIC)
        out += amp * layer
        tot += amp
        amp *= gain
    return out / (tot + 1e-9)


def _sample_bilinear(F, x, y):
    """Bilinear sample of array F (res,res) at float coords x (col), y (row), wrapped."""
    res = F.shape[0]
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    fx = (x - x0).astype(np.float32)
    fy = (y - y0).astype(np.float32)
    x0 %= res
    y0 %= res
    x1 = (x0 + 1) % res
    y1 = (y0 + 1) % res
    return (F[y0, x0] * (1 - fx) * (1 - fy) + F[y0, x1] * fx * (1 - fy)
            + F[y1, x0] * (1 - fx) * fy + F[y1, x1] * fx * fy)


# ---------------------------------------------------------------------------
# 1. STABLE FLUIDS — semi-Lagrangian ink advection (Jos Stam)
# ---------------------------------------------------------------------------
def stable_fluids_ink(h, w, seed, *, res=200, steps=44):
    rng = _rng(seed)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    # incompressible-ish base velocity from curl of an fbm potential, plus swirl centers
    psi = _fbm(res, rng, octaves=5, base=5)
    gy, gx = np.gradient(psi)
    vx = gy.copy()
    vy = -gx.copy()
    for _ in range(int(rng.integers(4, 7))):
        cx, cy = rng.uniform(0, res, 2)
        s = rng.uniform(-1, 1) * 2.4
        dx = xx - cx
        dy = yy - cy
        r2 = dx * dx + dy * dy + 30.0
        vx += s * (-dy) / r2 * 60.0
        vy += s * (dx) / r2 * 60.0
    spd = np.hypot(vx, vy) + 1e-6
    vx /= spd.mean()
    vy /= spd.mean()
    # ink: many narrow blobs to seed high-frequency filaments
    ink = np.zeros((res, res), np.float32)
    for _ in range(70):
        cx, cy = rng.uniform(0, res, 2)
        r = rng.uniform(1.5, 4.0)
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        ink += np.exp(-d2 / (2 * r * r)) * rng.uniform(0.5, 1.0)
    dt = 1.6
    for _ in range(int(steps)):
        # backtrace
        sx = (xx - dt * vx)
        sy = (yy - dt * vy)
        ink = _sample_bilinear(ink, sx, sy)
        # also advect velocity (self-advection -> turbulent stirring)
        nvx = _sample_bilinear(vx, sx, sy)
        nvy = _sample_bilinear(vy, sx, sy)
        vx, vy = nvx, nvy
        ink *= 0.997
        ink += 0.0  # conserve
    ink = _norm(ink)
    ink = np.power(ink, 0.65)  # fuller histogram
    ink = ink + 1.4 * (ink - cv2.GaussianBlur(ink, (0, 0), 8.0))  # crush detail
    return _norm(_up(ink, h, w))


# ---------------------------------------------------------------------------
# 2. CURL-NOISE SMOKE with vorticity-confinement wisps
# ---------------------------------------------------------------------------
def curl_smoke(h, w, seed, *, res=224, steps=40):
    rng = _rng(seed)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    psi = _fbm(res, rng, octaves=6, base=4)
    gy, gx = np.gradient(psi)
    vx = gy
    vy = -gx
    # buoyancy: add upward drift modulated by a second noise
    buoy = _fbm(res, rng, octaves=4, base=3)
    vy -= 0.6 * (buoy - buoy.mean())
    sp = np.hypot(vx, vy).mean() + 1e-6
    vx /= sp
    vy /= sp
    dens = np.zeros((res, res), np.float32)
    # emitters
    emit = np.zeros((res, res), np.float32)
    for _ in range(28):
        cx, cy = rng.uniform(0, res, 2)
        r = rng.uniform(2, 5)
        emit += np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r))
    dt = 1.5
    for _ in range(int(steps)):
        sx = xx - dt * vx
        sy = yy - dt * vy
        dens = _sample_bilinear(dens, sx, sy)
        dens += emit * 0.10
        # vorticity confinement -> curl wisps
        cgy, cgx = np.gradient(dens)
        gmag = np.hypot(cgx, cgy) + 1e-6
        Nx = cgx / gmag
        Ny = cgy / gmag
        # curl of velocity (2D scalar)
        wz = np.gradient(vy, axis=1) - np.gradient(vx, axis=0)
        vx += 0.5 * (Ny * wz)
        vy += 0.5 * (-Nx * wz)
        dens *= 0.99
    dens = np.power(_norm(dens), 0.7)  # lift midtones -> fuller histogram
    dens = dens + 1.3 * (dens - cv2.GaussianBlur(dens, (0, 0), 6.0))
    return _norm(_up(dens, h, w))


# ---------------------------------------------------------------------------
# 3. MAGNETIC DIPOLE FIELD LINES (iron filings)
# ---------------------------------------------------------------------------
def magnetic_dipole(h, w, seed, *, res=384, dipoles=10):
    rng = _rng(seed)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    Bx = np.zeros((res, res), np.float32)
    By = np.zeros((res, res), np.float32)
    for _ in range(int(dipoles)):
        px, py = rng.uniform(0, res, 2)
        ang = rng.uniform(0, 2 * np.pi)
        mx, my = np.cos(ang), np.sin(ang)
        strength = rng.uniform(0.6, 1.6) * (res ** 2) * 0.04
        rx = xx - px
        ry = yy - py
        r2 = rx * rx + ry * ry + 9.0
        r = np.sqrt(r2)
        mr = (mx * rx + my * ry) / r2
        # 2D dipole field B ~ (2(m.rhat)rhat - m)/r^2
        Bx += strength * (3 * mr * (rx / r) - mx) / r2
        By += strength * (3 * mr * (ry / r) - my) / r2
    ang = np.arctan2(By, Bx)
    mag = np.hypot(Bx, By)
    # LIC-style streak: integrate a noise texture along the field direction
    noise = rng.standard_normal((res, res)).astype(np.float32)
    acc = noise.copy()
    cnt = np.ones((res, res), np.float32)
    dx = np.cos(ang)
    dy = np.sin(ang)
    for sgn in (1.0, -1.0):
        px = xx.copy()
        py = yy.copy()
        for k in range(18):
            px = px + sgn * dx
            py = py + sgn * dy
            acc += _sample_bilinear(noise, px, py)
            cnt += 1.0
    lic = acc / cnt
    lic = lic + 0.4 * np.log1p(mag) / (np.log1p(mag).max() + 1e-9)
    lic = lic + 0.8 * (lic - cv2.GaussianBlur(lic, (0, 0), 4.0))
    return _norm(_up(lic, h, w))


# ---------------------------------------------------------------------------
# 4. ELECTROSTATIC EQUIPOTENTIALS (FFT Poisson solve)
# ---------------------------------------------------------------------------
def electrostatic_equipotential(h, w, seed, *, res=384, charges=24):
    rng = _rng(seed)
    rho = np.zeros((res, res), np.float32)
    for _ in range(int(charges)):
        cx = int(rng.integers(0, res))
        cy = int(rng.integers(0, res))
        q = rng.choice([-1.0, 1.0]) * rng.uniform(0.5, 1.5)
        rho[cy, cx] += q
    rho -= rho.mean()  # neutralize for periodic Poisson
    # solve laplacian(phi) = -rho  via FFT
    ky = np.fft.fftfreq(res).reshape(-1, 1)
    kx = np.fft.fftfreq(res).reshape(1, -1)
    k2 = (2 * np.pi) ** 2 * (kx * kx + ky * ky)
    k2[0, 0] = 1.0
    phi = np.real(np.fft.ifft2(np.fft.fft2(rho) / k2)).astype(np.float32)
    phi[0, 0] = phi.mean()
    # equipotential banding: sinusoid of potential -> fine contour rings
    pn = _norm(phi)
    bands = 0.5 + 0.5 * np.cos(pn * np.pi * 2 * 22.0)
    # mix in field magnitude for crisp nodes near charges
    gy, gx = np.gradient(phi)
    field = np.log1p(np.hypot(gx, gy))
    out = bands * (0.6 + 0.4 * _norm(field))
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 5. SCHLIEREN REFRACTION (knife-edge shadowgraph)
# ---------------------------------------------------------------------------
def schlieren_refraction(h, w, seed, *, res=384):
    rng = _rng(seed)
    # turbulent refractive index field (multi-scale)
    n = _fbm(res, rng, octaves=7, base=3, gain=0.6)
    # inject shock fronts: sharp ridges from a few moving "blast" sources
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    for _ in range(int(rng.integers(3, 6))):
        cx, cy = rng.uniform(0, res, 2)
        r = np.hypot(xx - cx, yy - cy)
        k = rng.uniform(0.05, 0.12)
        n += 0.4 * np.exp(-((r - rng.uniform(40, 120)) ** 2) / 200.0) * np.cos(r * k)
    # knife-edge: deflection ~ gradient of n, project onto a knife direction
    gy, gx = np.gradient(n)
    theta = rng.uniform(0, 2 * np.pi)
    deflect = np.cos(theta) * gx + np.sin(theta) * gy
    # second derivative term gives the classic schlieren density streaks
    g2y, g2x = np.gradient(deflect)
    schlieren = deflect + 0.5 * (np.cos(theta) * g2x + np.sin(theta) * g2y)
    schlieren = np.tanh(schlieren * 6.0)
    schlieren = schlieren + 0.7 * (schlieren - cv2.GaussianBlur(schlieren, (0, 0), 3.0))
    return _norm(_up(schlieren, h, w))


# ---------------------------------------------------------------------------
# 6. FERROFLUID ROSENSWEIG SPIKES (hex peak lattice w/ disorder)
# ---------------------------------------------------------------------------
def ferrofluid_spikes(h, w, seed, *, res=384):
    rng = _rng(seed)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    field = np.zeros((res, res), np.float32)
    # hexagonal lattice of spikes (the Rosensweig instability selects a hex pattern)
    spacing = res / rng.uniform(14, 20)
    rows = int(res / (spacing * 0.866)) + 2
    cols = int(res / spacing) + 2
    jitter = spacing * 0.18
    for j in range(rows):
        for i in range(cols):
            cx = i * spacing + (spacing * 0.5 if j % 2 else 0.0)
            cy = j * spacing * 0.866
            cx += rng.uniform(-jitter, jitter)
            cy += rng.uniform(-jitter, jitter)
            amp = rng.uniform(0.7, 1.0)
            sig = spacing * rng.uniform(0.22, 0.34)
            d2 = (xx - cx) ** 2 + (yy - cy) ** 2
            # cone-like peak (Bessel-ish): sharp tip
            r = np.sqrt(d2)
            field += amp * np.exp(-d2 / (2 * sig * sig)) * (1.0 + 0.4 * np.cos(r / sig * 3.0))
    # surface ripples between spikes for crushed detail
    field += 0.18 * _fbm(res, rng, octaves=5, base=8)
    field = field + 0.6 * (field - cv2.GaussianBlur(field, (0, 0), 5.0))
    return _norm(_up(field, h, w))


# ---------------------------------------------------------------------------
# 7. DIFFUSION-LIMITED AGGREGATION (DLA)
# ---------------------------------------------------------------------------
def dla_aggregate(h, w, seed, *, res=256, n_walkers=14000, max_steps=900):
    """Vectorized DLA: a swarm of walkers takes random steps in lockstep; any that land
    next to the aggregate stick. Wrapped lattice for full coverage."""
    rng = _rng(seed)
    grid = np.zeros((res, res), np.uint8)
    age = np.zeros((res, res), np.float32)
    nseed = 9
    for _ in range(nseed):
        sy = int(rng.integers(res // 8, res - res // 8))
        sx = int(rng.integers(res // 8, res - res // 8))
        grid[sy, sx] = 1
        age[sy, sx] = 1.0
    a = 1.0
    # swarm of walkers (vectorized)
    px = rng.integers(0, res, n_walkers)
    py = rng.integers(0, res, n_walkers)
    alive = np.ones(n_walkers, dtype=bool)
    for step in range(int(max_steps)):
        if not alive.any():
            break
        idx = np.where(alive)[0]
        x = px[idx]
        y = py[idx]
        # neighbor occupancy (4-neigh, wrapped) -> stick test
        up = grid[(y - 1) % res, x]
        dn = grid[(y + 1) % res, x]
        lf = grid[y, (x - 1) % res]
        rt = grid[y, (x + 1) % res]
        touch = (up | dn | lf | rt).astype(bool)
        if touch.any():
            stx = x[touch]
            sty = y[touch]
            # dedupe by linear index, keep first
            lin = sty.astype(np.int64) * res + stx.astype(np.int64)
            uniq, first = np.unique(lin, return_index=True)
            uy = (uniq // res).astype(np.int64)
            ux = (uniq % res).astype(np.int64)
            newcell = grid[uy, ux] == 0
            a += 1.0
            grid[uy[newcell], ux[newcell]] = 1
            age[uy[newcell], ux[newcell]] = a + rng.uniform(0, 0.9, int(newcell.sum()))
            alive[idx[touch]] = False
            idx = np.where(alive)[0]
            x = px[idx]
            y = py[idx]
        if len(idx) == 0:
            break
        d = rng.integers(0, 4, len(idx))
        x = (x + (d == 0) - (d == 1)) % res
        y = (y + (d == 2) - (d == 3)) % res
        px[idx] = x
        py[idx] = y
        # respawn a fraction of long-running walkers to keep coverage high
        if step > 0 and step % 120 == 0:
            far = idx
            px[far] = rng.integers(0, res, len(far))
            py[far] = rng.integers(0, res, len(far))
    occ = grid.astype(np.float32)
    dist = ndimage.distance_transform_edt(1 - grid).astype(np.float32)
    fld = np.exp(-dist / (res * 0.012))  # glow around branches
    agen = _norm(age) * occ
    out = fld + 0.6 * cv2.GaussianBlur(agen, (0, 0), 1.0)
    out = out + 0.6 * (out - cv2.GaussianBlur(out, (0, 0), 3.0))
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 8. EDEN GROWTH (stochastic surface accretion)
# ---------------------------------------------------------------------------
def eden_growth(h, w, seed, *, res=320):
    rng = _rng(seed)
    grid = np.zeros((res, res), np.uint8)
    age = np.zeros((res, res), np.float32)
    # several nucleation sites -> competing clusters fill the plane
    nsites = 9
    perim = []  # list of (y,x) candidate growth sites
    a = 0
    for _ in range(nsites):
        sy = int(rng.integers(0, res))
        sx = int(rng.integers(0, res))
        if not grid[sy, sx]:
            grid[sy, sx] = 1
            a += 1
            age[sy, sx] = a
            perim.append((sy, sx))
    offs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    target = int(res * res * 0.92)
    perim_set = set(perim)
    # grow until plane is ~full; pick a random perimeter cell, occupy an empty neighbor
    perim_list = list(perim_set)
    while a < target and perim_list:
        idx = int(rng.integers(0, len(perim_list)))
        cy, cx = perim_list[idx]
        # find empty neighbors
        empties = []
        for dy, dx in offs:
            ny = (cy + dy) % res
            nx = (cx + dx) % res
            if not grid[ny, nx]:
                empties.append((ny, nx))
        if not empties:
            # remove from perimeter
            perim_list[idx] = perim_list[-1]
            perim_list.pop()
            continue
        ny, nx = empties[int(rng.integers(0, len(empties)))]
        grid[ny, nx] = 1
        a += 1
        age[ny, nx] = a
        perim_list.append((ny, nx))
    # render the AGE field -> self-affine accretion fronts (rough Eden boundaries)
    out = _norm(age)
    # crush detail: high-pass of the age field shows the crinkled growth fronts
    out = out + 1.0 * (out - cv2.GaussianBlur(out, (0, 0), 4.0))
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 9. SAFFMAN-TAYLOR VISCOUS FINGERING (Laplacian growth)
# ---------------------------------------------------------------------------
def viscous_fingering(h, w, seed, *, res=200, grow=2600):
    rng = _rng(seed)
    occ = np.zeros((res, res), np.float32)
    # central injection blob
    cy, cx = res // 2, res // 2
    rr = res // 14
    yy, xx = np.mgrid[0:res, 0:res]
    occ[(yy - cy) ** 2 + (xx - cx) ** 2 < rr * rr] = 1.0
    age = occ.copy()
    a = 1.0
    # Laplacian growth: pressure field p with p=0 inside, p=1 at boundary; grow at
    # boundary with probability ~ |grad p|^eta. Solve p by Jacobi relaxation, regrow.
    p = np.zeros((res, res), np.float32)
    eta = 1.3
    relax_iters = 26
    chunks = 36
    per_chunk = max(1, int(grow / chunks))
    for c in range(chunks):
        # relax laplace(p)=0 with p=0 on occupied, p=1 on far boundary frame
        for _ in range(relax_iters):
            p = 0.25 * (np.roll(p, 1, 0) + np.roll(p, -1, 0)
                        + np.roll(p, 1, 1) + np.roll(p, -1, 1))
            p[occ > 0.5] = 0.0
            p[0, :] = p[-1, :] = p[:, 0] = p[:, -1] = 1.0
        # boundary sites: empty cells adjacent to occupied
        nb = (np.roll(occ, 1, 0) + np.roll(occ, -1, 0)
              + np.roll(occ, 1, 1) + np.roll(occ, -1, 1))
        boundary = (occ < 0.5) & (nb > 0.5)
        ys, xs = np.where(boundary)
        if len(ys) == 0:
            break
        prob = np.maximum(p[ys, xs], 1e-4) ** eta
        prob = prob / prob.sum()
        ngrow = min(per_chunk, len(ys))
        pick = rng.choice(len(ys), size=ngrow, replace=True, p=prob)
        a += 1.0
        for k in pick:
            occ[ys[k], xs[k]] = 1.0
            age[ys[k], xs[k]] = a + rng.uniform(0, 0.9)
    dist = ndimage.distance_transform_edt(1 - (occ > 0.5)).astype(np.float32)
    glow = np.exp(-dist / (res * 0.02))
    out = _norm(age) * (occ > 0.5) + 0.7 * glow
    out = out + 0.6 * (out - cv2.GaussianBlur(out, (0, 0), 3.0))
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 10. CURL STREAKLINES via line-integral convolution (silky flow)
# ---------------------------------------------------------------------------
def curl_streaklines(h, w, seed, *, res=320):
    rng = _rng(seed)
    # vorticity field from blobs -> streamfunction by FFT Poisson -> divergence-free vel
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    omega = np.zeros((res, res), np.float32)
    for _ in range(int(rng.integers(10, 18))):
        cx, cy = rng.uniform(0, res, 2)
        s = rng.uniform(0.05, 0.10) * res
        sgn = rng.choice([-1.0, 1.0])
        omega += sgn * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s))
    omega -= omega.mean()
    ky = np.fft.fftfreq(res).reshape(-1, 1)
    kx = np.fft.fftfreq(res).reshape(1, -1)
    k2 = (2 * np.pi) ** 2 * (kx * kx + ky * ky)
    k2[0, 0] = 1.0
    psi = np.real(np.fft.ifft2(np.fft.fft2(omega) / k2)).astype(np.float32)
    gy, gx = np.gradient(psi)
    vx = gy
    vy = -gx
    sp = np.hypot(vx, vy) + 1e-6
    dx = vx / sp
    dy = vy / sp
    # LIC: integrate white noise along streamlines both directions
    noise = rng.standard_normal((res, res)).astype(np.float32)
    acc = noise.copy()
    cnt = np.ones((res, res), np.float32)
    for sgn in (1.0, -1.0):
        px = xx.copy()
        py = yy.copy()
        cdx = dx.copy()
        cdy = dy.copy()
        for k in range(16):
            px = px + sgn * cdx
            py = py + sgn * cdy
            acc += _sample_bilinear(noise, px, py)
            cnt += 1.0
            cdx = _sample_bilinear(dx, px, py)
            cdy = _sample_bilinear(dy, px, py)
    lic = acc / cnt
    lic = lic + 1.0 * (lic - cv2.GaussianBlur(lic, (0, 0), 3.0))
    return _norm(_up(lic, h, w))


# ---------------------------------------------------------------------------
# 11. POTENTIAL FLOW PAST CYLINDERS (complex potential)
# ---------------------------------------------------------------------------
def potential_flow_cylinders(h, w, seed, *, res=448):
    rng = _rng(seed)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float64)
    z = (xx / res * 8.0 - 4.0) + 1j * (yy / res * 8.0 - 4.0)
    Uang = rng.uniform(0, 2 * np.pi)
    U = np.exp(1j * Uang)
    psi = (U * z).imag  # uniform stream
    # doublets (cylinders) + vortices
    for _ in range(int(rng.integers(5, 9))):
        z0 = complex(rng.uniform(-3.5, 3.5), rng.uniform(-3.5, 3.5))
        a2 = rng.uniform(0.10, 0.45)
        # doublet: -a^2 U / (z - z0)  ; stream func = imag
        w_complex = -a2 * U / (z - z0 + 1e-6)
        psi += w_complex.imag
        # bound vortex -> wake shedding
        gamma = rng.uniform(-1.2, 1.2)
        psi += (-gamma / (2 * np.pi)) * np.log(np.abs(z - z0) + 1e-3)
    psi = psi.astype(np.float32)
    # streamfunction contour banding -> fine streamlines around the obstacles
    pn = _norm(psi)
    bands = 0.5 + 0.5 * np.cos(pn * np.pi * 2 * 40.0)
    # speed field highlights stagnation/acceleration zones
    gy, gx = np.gradient(psi)
    speed = _norm(np.log1p(np.hypot(gx, gy)))
    out = bands * (0.45 + 0.55 * speed)
    out = out + 1.0 * (out - cv2.GaussianBlur(out, (0, 0), 2.0))
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
ENGINES = {
    "stable_fluids_ink": stable_fluids_ink,
    "curl_smoke": curl_smoke,
    "magnetic_dipole": magnetic_dipole,
    "electrostatic_equipotential": electrostatic_equipotential,
    "schlieren_refraction": schlieren_refraction,
    "ferrofluid_spikes": ferrofluid_spikes,
    "dla_aggregate": dla_aggregate,
    "eden_growth": eden_growth,
    "viscous_fingering": viscous_fingering,
    "curl_streaklines": curl_streaklines,
    "potential_flow_cylinders": potential_flow_cylinders,
}


if __name__ == "__main__":
    H = W = 1024
    print(f"{'engine':30s} {'secs':>7s} {'fine':>7s} {'std':>7s} {'min':>5s} {'max':>5s}  ok")
    allok = True
    for name, fn in ENGINES.items():
        t0 = time.time()
        f = fn(H, W, 12345)
        secs = time.time() - t0
        f = np.asarray(f, np.float32)
        finite = np.isfinite(f).all()
        fine = (f - cv2.GaussianBlur(f, (0, 0), 8)).std() / (f.std() + 1e-6)
        std = float(f.std())
        ok = (secs < 2.5) and (fine >= 0.12) and (std > 0.06) and finite \
            and f.min() >= -1e-4 and f.max() <= 1.0 + 1e-4
        allok = allok and ok
        print(f"{name:30s} {secs:7.3f} {fine:7.3f} {std:7.3f} "
              f"{f.min():5.2f} {f.max():5.2f}  {'OK' if ok else 'FAIL'}")
    print("ALL PASS" if allok else "SOME FAILED")
