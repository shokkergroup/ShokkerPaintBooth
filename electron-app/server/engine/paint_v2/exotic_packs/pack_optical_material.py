"""OPTICAL & MATERIAL math-engine pack for Shokker Paint Booth.

Eleven GENUINELY NOVEL scalar-field generators in the novel-optics / exotic-materials
family. Each is a DISTINCT algorithm (not a recolor of another) producing an intricate,
full-coverage, fine-detailed field in [0,1] over a whole 2048px car.

Engines:
  diffraction_grating   — multi-order grating spectrum: a periodic phase grating's far-field
                          intensity, sum over diffraction orders with order-dependent sinc
                          envelopes; jittered groove pitch gives a spectrum-fan texture.
  cd_dvd_rainbow        — concentric data-track grating (CD/DVD): radial track phase + the
                          Bragg condition d(sinθi+sinθo)=mλ resolved per pixel -> rainbow swirl.
  thinfilm_bands        — wavelength thin-film interference: variable dielectric thickness
                          map -> per-wavelength reflectance via Airy/Fresnel two-beam sum,
                          collapsed to a luminance band field (Newton-free, thickness-driven).
  widmanstatten         — meteorite Widmanstatten: 4 octahedral {111} kamacite lamellae
                          families (anisotropic band stacks at 4 crystal orientations) with
                          taenite rims; signed-distance lamellae union.
  mokume_gane           — wood-eye metal lamination: stacked metal sheets (layered SDF)
                          punched by drilled/forged depressions, then planed flat -> the
                          revealed contour rings of a laminated billet.
  labradorite_schiller  — labradorite schiller: lamellar twin domains each flashing at a
                          domain-specific viewing angle; angular gate * domain mask gives
                          discrete iridescent flares on a dark feldspar matrix.
  opal_playofcolor      — opal play-of-color: a Voronoi-free packed-sphere lattice of silica
                          colloids; each domain diffracts (Bragg) at its lattice spacing &
                          orientation -> sharp polychrome color-patch field.
  bismuth_terraces      — bismuth hopper crystal: recursive square-spiral stepped terraces
                          (hopper growth) -> nested rectangular ledges, oxide-iridescent edges.
  liesegang_rings       — Liesegang precipitation: reaction-diffusion-free analytic banding
                          from the Jablczynski spacing law about multiple nucleation centers.
  kirigami_creases      — kirigami/origami crease shadow: a folded crease graph (mountain/
                          valley straight-line arrangement) whose facets carry shaded normals
                          + sharp ridge shadows.
  guilloche_rose        — (bonus exotic optic) caustic rose-window: a rose-curve phase plate
                          focusing light into bright cusps; pure trig caustic field.
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from scipy import ndimage as ndi


# ----------------------------------------------------------------------------- helpers
def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-9)


def _up(field: np.ndarray, h: int, w: int) -> np.ndarray:
    return cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def _grid(res):
    u = np.linspace(0.0, 1.0, res, dtype=np.float32)
    return np.meshgrid(u, u)  # X, Y


def _value_noise(res, rng, scale, octaves=4):
    """Cheap fbm value noise via upsampled random lattices."""
    out = np.zeros((res, res), np.float32)
    amp = 1.0
    tot = 0.0
    s = scale
    for _ in range(octaves):
        n = max(2, int(s))
        lat = rng.random((n, n)).astype(np.float32)
        out += amp * cv2.resize(lat, (res, res), interpolation=cv2.INTER_CUBIC)
        tot += amp
        amp *= 0.5
        s *= 2.0
    return out / (tot + 1e-9)


# ----------------------------------------------------------------------------- 1
def diffraction_grating(h, w, seed, *, res=512) -> np.ndarray:
    """Periodic phase-grating far-field spectrum field.

    A blazed grating with slowly-varying local pitch diffracts into multiple orders m.
    Per pixel we sum sinc-enveloped order intensities whose spatial frequency scales with
    m / pitch, giving a crushed spectrum-fan of fine fringes."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    X, Y = _grid(res)
    # slowly varying groove pitch & groove angle across the sheet (fan-out)
    pitch = 18.0 + 26.0 * _value_noise(res, rng, 3, 4)
    ang = (rng.uniform(0.0, np.pi)) + 1.3 * (_value_noise(res, rng, 2, 3) - 0.5)
    ca, sa = np.cos(ang), np.sin(ang)
    coord = (X * ca + Y * sa)  # groove-perpendicular coordinate
    blaze = 2.0 * np.pi * (_value_noise(res, rng, 4, 4) - 0.5)
    field = np.zeros((res, res), np.float32)
    for m in range(1, 7):  # diffraction orders
        env = np.float32(np.sinc(m * 0.42)) ** 2  # grating-tooth sinc envelope per order
        phase = 2.0 * np.pi * m * coord * pitch + m * blaze
        field += (env / m) * (0.5 + 0.5 * np.cos(phase))
    # superpose a faint perpendicular order set for cross-grating sparkle
    coord2 = (-X * sa + Y * ca)
    field += 0.35 * (0.5 + 0.5 * np.cos(2.0 * np.pi * 3.0 * coord2 * pitch))
    field = field * (0.7 + 0.3 * _value_noise(res, rng, 6, 3))
    return _norm(_up(field, h, w))


# ----------------------------------------------------------------------------- 2
def cd_dvd_rainbow(h, w, seed, *, res=512) -> np.ndarray:
    """CD/DVD concentric data-track grating rainbow.

    Pressed disc tracks are concentric circles of constant pitch d. The Bragg grating
    condition d(sinθ_in + sinθ_out) = m λ makes which wavelength constructively reflects
    depend on local radius & azimuth. We resolve a per-pixel reinforced-order intensity ->
    rainbow swirl that sweeps with angle (CD glare)."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    X, Y = _grid(res)
    # two off-center disc hubs for an asymmetric, full-bleed sweep
    cx0, cy0 = rng.uniform(0.2, 0.8, 2)
    dx, dy = X - cx0, Y - cy0
    r = np.sqrt(dx * dx + dy * dy) + 1e-4
    az = np.arctan2(dy, dx)
    d_track = 0.0014 + 0.0006 * np.sin(7.0 * az)  # track pitch wobble
    tracks = 0.5 + 0.5 * np.cos(2.0 * np.pi * r / d_track)  # the data grooves
    # incidence sweep across the disc: effective path = r * cos(az - tilt)
    tilt = rng.uniform(0.0, 2.0 * np.pi)
    geom = r * np.cos(az - tilt)
    spectrum = np.zeros((res, res), np.float32)
    for m in range(1, 5):
        lam = m * (0.6 + 0.4 * geom)  # order-m reinforced wavelength proxy
        spectrum += (1.0 / m) * (0.5 + 0.5 * np.cos(2.0 * np.pi * 9.0 * lam))
    field = tracks * (0.45 + 0.55 * spectrum)
    field += 0.25 * (0.5 + 0.5 * np.cos(38.0 * az + 60.0 * r))  # radial glare fan
    return _norm(_up(field, h, w))


# ----------------------------------------------------------------------------- 3
def thinfilm_bands(h, w, seed, *, res=512) -> np.ndarray:
    """Wavelength thin-film interference (thickness-driven, NOT concentric Newton rings).

    A dielectric film of spatially varying thickness t(x,y) over a metal reflects each
    wavelength with two-beam (Airy) reflectance R(λ) = sin^2(2π n t / λ). We integrate a
    handful of wavelengths to a perceived luminance band map; turbulent thickness gives
    soap-film/heat-tint marbled bands with fine high-freq structure."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # turbulent optical thickness (n·t) in nm-ish proxy units, multi-scale
    t = 220.0 * _value_noise(res, rng, 3, 5) + 90.0 * _value_noise(res, rng, 9, 3)
    t += 40.0 * np.sin(2.0 * np.pi * 5.0 * _value_noise(res, rng, 2, 2))
    lum = np.zeros((res, res), np.float32)
    # sample the visible band; weight ~ photopic curve
    wls = [430.0, 480.0, 530.0, 580.0, 630.0, 680.0]
    wts = [0.35, 0.7, 1.0, 0.95, 0.75, 0.4]
    for lam, wt in zip(wls, wts):
        R = np.sin(2.0 * np.pi * t / lam) ** 2  # two-beam reflectance
        lum += wt * R
    lum /= sum(wts)
    # high-freq ripple from second-surface microroughness
    lum = lum * (0.8 + 0.2 * (0.5 + 0.5 * np.cos(2.0 * np.pi * 28.0 *
                 _value_noise(res, rng, 16, 2))))
    return _norm(_up(lum, h, w))


# ----------------------------------------------------------------------------- 4
def widmanstatten(h, w, seed, *, res=512) -> np.ndarray:
    """Meteorite Widmanstatten lamellae (octahedrite).

    Iron meteorites exsolve kamacite as plates on the four {111} octahedral planes ->
    four families of straight parallel lamellae crossing at fixed (~60°) angles, each a
    stack of sharp bands with taenite rims at the band edges. We build 4 oriented band
    stacks (signed sawtooth) and take their thin-edge union, on a noisy plessite ground."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    X, Y = _grid(res)
    base_ang = rng.uniform(0.0, np.pi)
    angles = base_ang + np.deg2rad([0.0, 60.0, 120.0, 35.0])  # 4 lamellae families
    field = np.zeros((res, res), np.float32)
    rims = np.zeros((res, res), np.float32)
    for k, a in enumerate(angles):
        ca, sa = np.cos(a), np.sin(a)
        coord = X * ca + Y * sa
        pitch = 22.0 + 6.0 * k + 8.0 * _value_noise(res, rng, 2, 2)
        # slightly meandering lamellae
        coord = coord + 0.02 * _value_noise(res, rng, 4, 3)
        s = np.abs(((coord * pitch) % 1.0) - 0.5) * 2.0  # 0 at band center, 1 at edge
        band = np.clip(1.0 - s, 0.0, 1.0) ** 1.4
        field = np.maximum(field, band * (0.6 + 0.1 * k))
        rims += (np.abs(s - 0.85) < 0.06).astype(np.float32)  # taenite rim lines
    ground = 0.25 * _value_noise(res, rng, 12, 4)  # plessite speckle between plates
    out = np.maximum(field, 0.0) + ground + 0.7 * np.clip(rims, 0, 1)
    return _norm(_up(out, h, w))


# ----------------------------------------------------------------------------- 5
def mokume_gane(h, w, seed, *, res=512) -> np.ndarray:
    """Mokume-gane (wood-eye metal lamination).

    A billet of N stacked metal sheets is punched with conical/round depressions then
    planed flat: each cut reveals the laminate's contour rings. We model a stack height
    map (parallel sheets) minus several drilled punches, then quantize height into sheet
    layers; the layer boundaries are the revealed wood-eye rings."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    X, Y = _grid(res)
    H = np.zeros((res, res), np.float32)
    # several forged depressions of varied shape pull the laminate up into rings
    npunch = 14
    for _ in range(npunch):
        cx, cy = rng.uniform(0.0, 1.0, 2)
        rad = rng.uniform(0.05, 0.22)
        d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        prof = np.exp(-(d / rad) ** 2) * rng.uniform(0.5, 1.4)
        if rng.random() < 0.4:  # chisel/twist punches add anisotropy
            prof *= (0.6 + 0.4 * np.cos(rng.uniform(0, 6.28) +
                     6.0 * np.arctan2(Y - cy, X - cx)))
        H += prof
    H += 0.15 * _value_noise(res, rng, 5, 4)  # hand-forge waviness
    H = cv2.GaussianBlur(H, (0, 0), 1.2)
    # plane flat: quantize into many thin sheet layers -> reveal contour rings
    layers = 26.0
    q = H * layers
    rings = np.abs(q - np.round(q))  # distance to nearest layer boundary
    field = 1.0 - np.clip(rings * 2.0, 0.0, 1.0)  # bright at the revealed laminae edges
    field = field * (0.7 + 0.3 * (np.round(q) % 2))  # alternating sheet alloys
    return _norm(_up(field, h, w))


# ----------------------------------------------------------------------------- 6
def labradorite_schiller(h, w, seed, *, res=512) -> np.ndarray:
    """Labradorite schiller (lamellar iridescence flares).

    Labradorite's exsolution lamellae each fire iridescent color only over a narrow
    viewing angle. We tessellate the surface into elongated twin domains (anisotropic
    Worley-ish via stretched feature points) and give each a random schiller angle; an
    angular gate lights discrete domains brightly while the feldspar matrix stays dark."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    X, Y = _grid(res)
    npts = 70
    # twin domains are LONG & narrow: anisotropic metric (stretch one axis)
    stretch = rng.uniform(2.5, 4.5)
    rot = rng.uniform(0.0, np.pi)
    cr, sr = np.cos(rot), np.sin(rot)
    px = rng.uniform(0.0, 1.0, npts)
    py = rng.uniform(0.0, 1.0, npts)
    schiller_ang = rng.uniform(0.0, 2.0 * np.pi, npts)  # firing angle per lamella
    # global "view direction" sweep across the sheet -> which lamellae flash
    view = 6.28 * (X * 0.7 + Y * 0.3) + 0.8 * _value_noise(res, rng, 3, 3)
    # transform coords into the anisotropic twin frame
    xr = (X * cr - Y * sr)
    yr = (X * sr + Y * cr) * stretch
    pxr = (px * cr - py * sr)
    pyr = (px * sr + py * cr) * stretch
    nearest = np.zeros((res, res), np.int32)
    best = np.full((res, res), 1e9, np.float32)
    for i in range(npts):
        dd = (xr - pxr[i]) ** 2 + (yr - pyr[i]) ** 2
        m = dd < best
        best = np.where(m, dd, best)
        nearest = np.where(m, i, nearest)
    fire_ang = schiller_ang[nearest]
    gate = 0.5 + 0.5 * np.cos(view - fire_ang)  # angular schiller gate per domain
    gate = gate ** 6  # narrow flash
    edges = np.clip(1.0 - 12.0 * np.sqrt(best), 0.0, 1.0)  # bright twin seams
    field = gate + 0.5 * edges + 0.08 * _value_noise(res, rng, 14, 3)
    return _norm(_up(field, h, w))


# ----------------------------------------------------------------------------- 7
def opal_playofcolor(h, w, seed, *, res=512) -> np.ndarray:
    """Precious-opal play-of-color (Bragg color patches).

    Opal is a 3D packed lattice of silica spheres; each ordered domain Bragg-diffracts a
    color set by its sphere spacing & orientation. We grow many color-domains as a
    randomly-oriented hex-lattice tiling and compute a per-domain Bragg-reinforced
    intensity (mλ = 2 d sinθ), giving sharp polychromatic patches with fine sparkle."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    X, Y = _grid(res)
    # domain map: coarse cells, each its own lattice spacing & orientation
    ncell = 9
    cells = rng.random((ncell, ncell)).astype(np.float32)
    spacing = 0.6 + 1.4 * cv2.resize(cells, (res, res), interpolation=cv2.INTER_NEAREST)
    cells2 = rng.random((ncell, ncell)).astype(np.float32)
    orient = 6.28 * cv2.resize(cells2, (res, res), interpolation=cv2.INTER_NEAREST)
    ca, sc = np.cos(orient), np.sin(orient)
    u = (X * ca + Y * sc)
    v = (-X * sc + Y * ca)
    # hex packing: three lattice vectors -> the ordered colloid planes
    f = 60.0 / spacing
    lat = (np.cos(2 * np.pi * f * u)
           + np.cos(2 * np.pi * f * (0.5 * u + 0.866 * v))
           + np.cos(2 * np.pi * f * (0.5 * u - 0.866 * v)))
    lat = (lat + 3.0) / 6.0
    # Bragg reinforcement: which order lights depends on domain spacing
    theta = 0.5 + 0.5 * np.cos(8.0 * spacing + 4.0 * _value_noise(res, rng, 4, 3))
    field = (lat ** 3) * (0.4 + 0.6 * theta)
    field += 0.18 * (lat > 0.92)  # pinfire sparkle
    return _norm(_up(field, h, w))


# ----------------------------------------------------------------------------- 8
def bismuth_terraces(h, w, seed, *, res=512) -> np.ndarray:
    """Bismuth hopper-crystal stepped terraces.

    Bismuth grows as hopper crystals: edges outrun faces leaving recursive square-spiral
    stepped pyramids. We build nested rectangular ledges via a Chebyshev (square) distance
    spiral around multiple nucleation seeds; ledge edges carry the oxide-iridescent tint
    that bismuth is prized for."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    X, Y = _grid(res)
    field = np.zeros((res, res), np.float32)
    nseed = 9
    for _ in range(nseed):
        cx, cy = rng.uniform(0.1, 0.9, 2)
        rot = rng.uniform(0.0, np.pi / 2)
        cr, sr = np.cos(rot), np.sin(rot)
        dx = (X - cx) * cr - (Y - cy) * sr
        dy = (X - cx) * sr + (Y - cy) * cr
        cheb = np.maximum(np.abs(dx), np.abs(dy))  # square iso-contours (hopper faces)
        ang = np.arctan2(dy, dx)
        step = 26.0 + 16.0 * rng.random()
        # square spiral: stepped terraces + a slight twist that makes the hopper spiral
        spiral = cheb * step + ang / (2.0 * np.pi) * 1.0
        terr = np.abs(spiral - np.floor(spiral) - 0.5) * 2.0  # ledge ramps
        edge = np.clip(1.0 - 18.0 * np.abs(terr - 0.0), 0.0, 1.0)  # bright ledge lips
        amp = np.exp(-cheb * 2.2)  # hopper depth falloff from seed
        field = np.maximum(field, (0.55 * terr + 0.45 * edge) * (0.4 + 0.6 * amp))
    field += 0.12 * _value_noise(res, rng, 10, 3)
    return _norm(_up(field, h, w))


# ----------------------------------------------------------------------------- 9
def liesegang_rings(h, w, seed, *, res=512) -> np.ndarray:
    """Liesegang precipitation banding (Jablczynski spacing law).

    Periodic precipitation in a gel forms bands whose radii follow a geometric spacing
    law r_{n+1}/r_n -> const (p>1). We sum analytic banded fields about several diffusion
    fronts; bands get sparser & sharper outward (unlike uniform rings), with a turbulent
    gel-inhomogeneity warp for fine mottling."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    X, Y = _grid(res)
    warp = 0.04 * (_value_noise(res, rng, 4, 4) - 0.5)
    field = np.zeros((res, res), np.float32)
    nfront = 6
    for _ in range(nfront):
        cx, cy = rng.uniform(-0.1, 1.1, 2)
        r = np.sqrt((X - cx + warp) ** 2 + (Y - cy + warp) ** 2)
        p = rng.uniform(1.18, 1.45)          # Jablczynski ratio
        # log-spaced bands: phase ~ log_p(r) gives geometrically spaced rings
        phase = np.log(r * 14.0 + 1.0) / np.log(p)
        band = 0.5 + 0.5 * np.cos(2.0 * np.pi * phase)
        band = band ** 3                      # sharpen the precipitate lines
        sharp = np.clip(1.0 - 1.2 * r, 0.05, 1.0)  # inner bands brighter
        field = np.maximum(field, band * sharp)
    field += 0.10 * _value_noise(res, rng, 16, 3)  # gel mottle
    return _norm(_up(field, h, w))


# ----------------------------------------------------------------------------- 10
def kirigami_creases(h, w, seed, *, res=512) -> np.ndarray:
    """Kirigami / origami crease-shadow facets.

    A straight-line crease arrangement partitions the sheet into facets; each facet tilts
    by a (mountain/valley) angle so it catches light differently, and the creases throw a
    sharp ridge shadow. We build a line arrangement, label facets, assign each a Lambert
    shade from a random facet normal, and burn crisp crease lines."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    X, Y = _grid(res)
    nlines = 26
    sdf = np.full((res, res), 1e9, np.float32)  # nearest-crease distance
    sign_acc = np.zeros((res, res), np.float32)  # composite facet code
    for i in range(nlines):
        a = rng.uniform(0.0, np.pi)
        ca, sa = np.cos(a), np.sin(a)
        off = rng.uniform(0.0, 1.0)
        dist = X * ca + Y * sa - off          # signed dist to this crease line
        sdf = np.minimum(sdf, np.abs(dist))
        # half-plane code accumulates -> unique facet ids where lines cross
        sign_acc += (i + 1) * (dist > 0).astype(np.float32) * (0.61803 ** (i % 7))
    # facet shading: hash facet code to a pseudo-normal Lambert value
    facet = np.sin(sign_acc * 2.39996) * 0.5 + 0.5     # golden-angle facet hash
    shade = 0.25 + 0.7 * facet
    # add a fold gradient inside facets so they aren't flat
    shade = shade * (0.85 + 0.15 * np.cos(8.0 * (X + Y)))
    ridge = np.clip(1.0 - sdf * 90.0, 0.0, 1.0)        # sharp crease lines
    shadow = np.clip(1.0 - np.abs(sdf - 0.012) * 60.0, 0.0, 1.0) * 0.5  # cast shadow
    field = shade - 0.6 * shadow + 0.5 * ridge
    return _norm(_up(field, h, w))


# ----------------------------------------------------------------------------- 11
def caustic_rose(h, w, seed, *, res=512) -> np.ndarray:
    """Rose-window caustic field (exotic optic).

    A phase plate whose retardation follows a rose curve r=cos(kθ) focuses light into a
    web of bright cusp caustics. We compute the gradient of a rose-modulated phase and
    take a Burgers-style fold density |1/(1+t·H)| proxy, giving sharp lacy caustic ridges
    over the whole sheet. Distinct from Newton rings / oilfilm (no concentric interference;
    this is geometric-optics fold caustics)."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    X, Y = _grid(res)
    cx, cy = rng.uniform(0.35, 0.65, 2)
    dx, dy = X - cx, Y - cy
    r = np.sqrt(dx * dx + dy * dy) + 1e-4
    th = np.arctan2(dy, dx)
    k = int(rng.integers(4, 10))
    # high-frequency rose-curve phase plate + radial chirp (crushed fringes)
    phase = 46.0 * r * (1.0 + 0.5 * np.cos(k * th)) + 7.0 * np.cos(5.0 * th)
    phase += 9.0 * _value_noise(res, rng, 6, 4)
    # geometric-optics fold caustic: bright where the warped ray map folds.
    # map source point through the phase gradient, then measure local compression.
    gx, gy = np.gradient(phase)
    sx = (X * res + 1.6 * gx)
    sy = (Y * res + 1.6 * gy)
    # Jacobian determinant of the ray map -> caustic where |J| -> 0 (rays pile up)
    jxx = np.gradient(sx, axis=1)
    jxy = np.gradient(sx, axis=0)
    jyx = np.gradient(sy, axis=1)
    jyy = np.gradient(sy, axis=0)
    det = jxx * jyy - jxy * jyx
    caustic = 1.0 / (0.06 + np.abs(det))          # sharp lacy cusp ridges
    caustic = np.tanh(caustic * 0.18)
    caustic = caustic + 0.6 * (0.5 + 0.5 * np.cos(2.0 * phase))  # fine fringe overlay
    caustic *= (0.55 + 0.45 * np.cos(k * th) ** 2)               # petal modulation
    return _norm(_up(caustic, h, w))


# ----------------------------------------------------------------------------- registry
ENGINES = {
    "diffraction_grating": diffraction_grating,
    "cd_dvd_rainbow": cd_dvd_rainbow,
    "thinfilm_bands": thinfilm_bands,
    "widmanstatten": widmanstatten,
    "mokume_gane": mokume_gane,
    "labradorite_schiller": labradorite_schiller,
    "opal_playofcolor": opal_playofcolor,
    "bismuth_terraces": bismuth_terraces,
    "liesegang_rings": liesegang_rings,
    "kirigami_creases": kirigami_creases,
    "caustic_rose": caustic_rose,
}


def _fineness(f: np.ndarray) -> float:
    return float((f - cv2.GaussianBlur(f, (0, 0), 8)).std() / (f.std() + 1e-6))


if __name__ == "__main__":
    H = W = 1024
    print(f"{'engine':24s} {'secs':>6s} {'fine':>6s} {'std':>6s} {'min':>5s} {'max':>5s}  ok")
    allok = True
    for name, fn in ENGINES.items():
        t0 = time.time()
        f = fn(H, W, 12345)
        dt = time.time() - t0
        fine = _fineness(f)
        std = float(f.std())
        finite = bool(np.isfinite(f).all())
        in01 = bool(f.min() >= -1e-5 and f.max() <= 1.0 + 1e-5)
        ok = (dt < 2.5) and (fine >= 0.12) and (std > 0.06) and finite and in01
        allok = allok and ok
        print(f"{name:24s} {dt:6.3f} {fine:6.3f} {std:6.3f} "
              f"{f.min():5.2f} {f.max():5.2f}  {'OK' if ok else 'FAIL'}")
    print("ALL PASS" if allok else "SOME FAILED")
