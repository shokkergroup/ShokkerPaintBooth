# -*- coding: utf-8 -*-
"""SPECTRUM ARSENAL (2026-06-11) — new optical-physics paint engines for the
Spectrum Shift category reinvention. Owner: "flip that category on its head…
10-15 NEW FUNCTIONS, new WAYS to paint… mind altering."

Every function here models a REAL spectral phenomenon — not a palette swap:

  stress_fringes    photoelasticity: isochromatic fringe orders of a stressed
                    plate (the polarized-glass rainbow), real fringe physics
  tempered_quench   tempered-glass quench-spot stress lattice (the dark-rose
                    grid you see in car windows through polarized sunglasses)
  scratch_holo      scratch holography: concentric micro-arc families whose
                    glint position encodes depth — abrasion holograms
  grating_field     diffraction gratings: per-region groove direction + pitch
                    -> spectral order colors (CD / vinyl / holo-foil physics)
  lc_texture        cholesteric liquid crystal: fingerprint pitch bands and
                    focal-conic fan domains (polarised-microscope textures)
  opal_fire         opal play-of-color: silica lattice domains, each flashing
                    one spectral hue with its own angular gate phase
  newton_rings      thin-film contact interference: Airy ring systems around
                    contact points (r^2 ~ m*lambda spacing, per-wavelength)
  spectral_caustics refraction caustics split per-wavelength: every bright
                    filament is itself a tiny spectrum
  moire_phase       two fine lattices -> beat-phase field: giant slow rainbow
                    interference rolling over visible micro-lines
  hue_advect        spectrum as a FLUID: hue transported along a flow field
                    (rainbow rivers, eddies trap whirlpools of color)
  blackbody         true Planck-locus incandescence colors by temperature
  chromatic_split   lens dispersion: R/B channels sheared opposite ways along
                    the local gradient -> prism fringes on every edge
  spectral_contours map isolines cycling hue with slope shading
  spectral_lathe    spin-cut guilloche where hue follows cut angle
  doppler_field     red/blue shift of hue along a motion field
  einstein_arcs     gravitational lensing: background light smeared into
                    tangential arcs around dark mass cores
  hopper_terraces   bismuth hopper-crystal stepped spiral terraces
  fan_domains       focal-conic fan texture generator (LC / nacre fans)

Geometry engines come from redesign_wave2_2026 (attractors, reaction-diffusion,
crystals, caustics, flowlines, engraving, dendrites, stars, curves). All color
via the LUT-cached _ramp/_ipal (oklch_ramp direct = ~2s/call, never use raw).
"""
import math

import numpy as np
import cv2

from engine.expansions.redesign_wave2_2026 import (
    _rng, _coords, _noise, _warp, _sr, _n01, _sstep, _gauss, _curves,
    _crystal, _flow_theta, _flowlines, _caustics, _engrave, _dendrites,
    _stars, _dirblur, _ramp, _flakes, _memo,
)

# full-spectrum stops used by several engines (emissive, saturated)
SPECTRUM_STOPS = [(1.0, 0.10, 0.14), (1.0, 0.55, 0.02), (0.98, 0.92, 0.05),
                  (0.10, 0.92, 0.35), (0.05, 0.60, 1.0), (0.45, 0.15, 1.0),
                  (0.85, 0.12, 0.75)]


def spectral(t, flatten=0.42):
    """Full-spectrum hue wheel on a scalar field (LUT-cached)."""
    return _ramp(SPECTRUM_STOPS, np.clip(t, 0, 1), flatten_lightness=flatten)


def _cell_sin1(cid, k):
    """sin(cid*k)+1 evaluated per UNIQUE cell id then gathered to the pixel grid.
    PERF 2026-06-13 (arsenal lane): `cid` (from _crystal) holds only n_sites
    distinct integer ids in [0, max], yet `np.sin(cid*k)` was evaluating the
    transcendental on every one of the ~1e6 pixels. Build a tiny per-id LUT
    (one sin per cell, a few thousand) and index it — BIT-IDENTICAL because the
    LUT entry for integer id i is exactly sin(i*k)+1, the same float the
    per-pixel path produced. ~3x faster per call."""
    n = int(cid.max()) + 1
    lut = np.sin(np.arange(n, dtype=np.int64) * k) + 1
    return lut[cid]


# ---------------------------------------------------------------- photoelasticity
def stress_fringes(h, w, seed, n_loads=22, fringe_density=9.0):
    """Isochromatic fringe ORDER field of a plate under point loads.
    Each load contributes |principal stress difference| ~ P/r falling off with
    distance and lobed by angle (Flamant solution flavor). Returns (order, mag)
    where order cycles 0..1 per fringe and mag is total stress magnitude 0..1."""
    rng = _rng(seed, 101)
    yy, xx = _coords(h, w)
    sr = _sr(h, w)
    sig = np.zeros((h, w), np.float32)
    # PERF NOTE 2026-06-13 (arsenal lane): IRREDUCIBLE. The cost is the per-load
    # arctan2 + cos over the full grid (transcendentals). The loop is already a
    # clean float32 broadcast (dx is (1,w), dy is (h,1)); there is no redundant
    # full-grid temporary or float64 to strip. Any algebraic rewrite (e.g.
    # cos(th-phi)=(dx cosphi+dy sinphi)/r) reassociates the float math and shifts
    # a handful of fringe-WRAP pixels (order=(sig*density)%1 flips 0.999<->0.001),
    # so it cannot stay bit-identical. Left verbatim to guarantee identical pixels.
    for _ in range(int(n_loads)):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        P = rng.uniform(0.5, 1.6)
        phi = rng.uniform(0, np.pi)
        dx, dy = xx - cx, yy - cy
        r = np.sqrt(dx * dx + dy * dy) + 6.0 * sr
        th = np.arctan2(dy, dx)
        # two-lobed |sigma1-sigma2| pattern of a point load on a plate
        sig += P * np.abs(np.cos(th - phi)) / (r / (90.0 * sr))
    sig = sig / max(float(np.percentile(sig, 99)), 1e-5)
    order = (sig * fringe_density) % 1.0
    return order.astype(np.float32), np.clip(sig, 0, 1).astype(np.float32)


def tempered_quench(h, w, seed, pitch=64.0, fringe_density=5.0):
    """Tempered-glass quench-spot lattice: a jittered grid of cooling spots,
    each a radial stress rosette — the polarized-sunglasses window pattern."""
    rng = _rng(seed, 103)
    sr = _sr(h, w)
    p = pitch * sr
    yy, xx = _coords(h, w)
    a = float(rng.uniform(0, np.pi))
    u = xx * np.cos(a) + yy * np.sin(a)
    v = -xx * np.sin(a) + yy * np.cos(a)
    gu, gv = np.floor(u / p), np.floor(v / p)
    # jittered spot center per cell (hash-based)
    jx = np.sin(gu * 12.99 + gv * 78.23) * 0.5
    jy = np.sin(gu * 39.43 + gv * 11.13) * 0.5
    du = (u / p - gu - 0.5 - jx * 0.4) * p
    dv = (v / p - gv - 0.5 - jy * 0.4) * p
    r = np.sqrt(du * du + dv * dv) / p
    th = np.arctan2(dv, du)
    sig = np.exp(-r * 2.4) * (0.65 + 0.35 * np.cos(4 * th))   # quadrupole rosette
    order = (sig * fringe_density + _noise(h, w, seed ^ 0x5, (180, 420)) * 1.5) % 1.0
    return order.astype(np.float32), np.clip(sig * 1.4, 0, 1).astype(np.float32)


# ---------------------------------------------------------------- scratch hologram
def scratch_holo(h, w, seed, n_centers=9, arcs_per=120, glint_sigma=0.22):
    """Scratch holography: families of concentric circular micro-scratches.
    On each arc, a glint lives at a phase angle that varies smoothly with
    radius — tilting the view makes the glints CRAWL along the arcs.
    Returns (arcs, glints, phase) — phase 0..1 drives spectral coloring."""
    rng = _rng(seed, 107)
    sr = _sr(h, w)
    arc_img = np.zeros((h, w), np.float32)
    glint_img = np.zeros((h, w), np.float32)
    phase_img = np.zeros((h, w), np.float32)
    for _c in range(int(n_centers)):
        cx, cy = rng.uniform(-0.2, 1.2) * w, rng.uniform(-0.2, 1.2) * h
        r0 = rng.uniform(15, 60) * sr
        dr = rng.uniform(3.0, 6.5) * sr
        g0 = rng.uniform(0, 2 * np.pi)
        gslope = rng.uniform(0.5, 2.0) / (140 * sr)
        polys, gpts, gph = [], [], []
        for k in range(int(arcs_per)):
            r = r0 + k * dr
            if r > 1.7 * max(h, w):
                break
            a0 = rng.uniform(0, 2 * np.pi)
            alen = rng.uniform(1.2, 2 * np.pi)
            aa = np.linspace(a0, a0 + alen, max(8, int(alen * r / (9 * sr))))
            polys.append(np.stack([cx + np.cos(aa) * r, cy + np.sin(aa) * r], -1))
            ga = g0 + r * gslope          # glint phase crawls with radius
            gx, gy = cx + np.cos(ga) * r, cy + np.sin(ga) * r
            if -10 < gx < w + 10 and -10 < gy < h + 10:
                gpts.append((gx, gy)); gph.append((ga % (2 * np.pi)) / (2 * np.pi))
        arc_img = np.maximum(arc_img, _curves(h, w, polys, thick=1, val=1.0))
        for (gx, gy), ph in zip(gpts, gph):
            ix, iy = int(gx), int(gy)
            if 0 <= ix < w and 0 <= iy < h:
                glint_img[iy, ix] = 1.0
                phase_img[iy, ix] = ph
    glint_soft = _gauss(glint_img, 2.2 * sr)
    glints = np.clip(glint_soft * (1.0 / max(glint_soft.max(), 1e-5)), 0, 1)
    phase = _gauss(phase_img, 6 * sr) / np.maximum(_gauss((phase_img > 0).astype(np.float32), 6 * sr), 1e-4)
    return arc_img, glints.astype(np.float32), np.clip(phase, 0, 1).astype(np.float32)


# ---------------------------------------------------------------- diffraction grating
def grating_field(h, w, seed, theta, pitch=3.4):
    """Hairline diffraction grooves following a direction field + the local
    dispersion coordinate (hue = where you sit between spectral orders).
    Returns (grooves, disp) — disp 0..1 across groove-normal direction."""
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    phase = xx * np.cos(theta) + yy * np.sin(theta)
    grooves = (0.5 + 0.5 * np.sin(phase * (2 * np.pi / (pitch * sr)))).astype(np.float32)
    disp = _n01(np.sin(phase * (2 * np.pi / (pitch * sr * 34))) +
                _noise(h, w, seed ^ 0x47, (120, 300)) * 1.2)
    return grooves, disp


# ---------------------------------------------------------------- liquid crystal
def lc_texture(h, w, seed, kind="fingerprint", fine=0.55):
    """Cholesteric LC textures. 'fingerprint' = pitch bands (RD fingerprint
    preset); returns (bands01, defects) — defects are the disclination lines."""
    from engine.expansions.redesign_wave2_2026 import _gray_scott
    fp = _gray_scott(h, w, seed, "fingerprint", iters=380, grid=448, seeds=30,
                     fine=fine, speckle=0.12)
    bands = _n01(fp)
    gy, gx = np.gradient(_gauss(bands, 2))
    mag = np.sqrt(gx * gx + gy * gy)
    defects = _sstep(0.55, 0.9, 1.0 - _n01(mag)) * _sstep(0.35, 0.5, bands) * (1 - _sstep(0.5, 0.65, bands))
    return bands, np.clip(defects, 0, 1).astype(np.float32)


def fan_domains(h, w, seed, n_fans=160):
    """Focal-conic fan texture (smectic LC / nacre): packed fan-shaped domains,
    each ribbed radially from its apex. Returns (fans, rib, domain01)."""
    rng = _rng(seed, 109)
    sr = _sr(h, w)
    cid, edge, orient, axial = _crystal(h, w, seed, n_sites=n_fans, aniso=1.3, res=0.5)
    yy, xx = _coords(h, w)
    per = _n01(_cell_sin1(cid, 12.99))   # per-cell LUT (see _cell_sin1), bit-identical
    apex_a = per * 2 * np.pi
    # radial ribs from each cell's pseudo-apex: use axial coord + orient
    rib = (0.5 + 0.5 * np.sin(axial * (1.5 + 4.0 * per) + apex_a * 3)).astype(np.float32)
    fans = _sstep(0.06, 0.30, edge)
    return fans, rib, per


# ---------------------------------------------------------------- opal fire
def opal_fire(h, w, seed, n_domains=420, lit_frac=0.45, gate_bands=3):
    """Opal play-of-color: angular silica-lattice domains. Each domain owns a
    spectral hue + a gate phase; (hue, flash, edge) returned — flash already
    gated so a subset of domains 'fire' while neighbours sleep."""
    rng = _rng(seed, 113)
    cid, edge, orient, axial = _crystal(h, w, seed, n_sites=n_domains, aniso=1.4, res=0.5)
    per = _n01(_cell_sin1(cid, 12.99))
    gatep = _n01(_cell_sin1(cid, 7.31))
    # NOTE 2026-06-13: dropped the dead first `flash` (a narrow-band _sstep that
    # was immediately overwritten and never used). Hoisted the thrice-computed
    # (gatep*gate_bands)%1.0 band coordinate into one buffer — bit-identical.
    gb = (gatep * gate_bands) % 1.0
    flash = _sstep(0.42, 0.5, gb) * (1 - _sstep(0.5, 0.58, gb))
    keep = (per < lit_frac).astype(np.float32)
    inner = _sstep(0.10, 0.35, edge)
    return per, np.clip(flash * keep * inner, 0, 1).astype(np.float32), inner


# ---------------------------------------------------------------- newton rings
def newton_rings(h, w, seed, n_contacts=26, lam=11.0):
    """Thin-film contact interference: ring systems with TRUE Airy spacing
    (radius ~ sqrt(m*lambda*R)) around contact points; rings crowd outward.
    Returns (m_order mod 1, envelope)."""
    rng = _rng(seed, 127)
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    order = np.zeros((h, w), np.float32)
    env = np.zeros((h, w), np.float32)
    for _ in range(int(n_contacts)):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        R = rng.uniform(60, 220) * sr           # lens radius -> ring spacing
        dx, dy = xx - cx, yy - cy
        r2 = dx * dx + dy * dy
        m = r2 / (lam * R * sr)                  # fringe order grows ~ r^2
        e = np.exp(-r2 / (2 * (rng.uniform(60, 140) * sr) ** 2))
        order += m * e
        env = np.maximum(env, e)
    return (order % 1.0).astype(np.float32), np.clip(env, 0, 1).astype(np.float32)


# ---------------------------------------------------------------- dispersed caustics
def spectral_caustics(h, w, seed, strength=44, scale=80, split=2.6):
    """Caustic web split per wavelength: R/G/B webs refracted with slightly
    different indices then stacked -> every filament becomes a micro-spectrum.
    Returns HxWx3 dispersed web (0..1) ready to add as light."""
    # PERF 2026-06-13 (arsenal lane): the 3 _caustics calls (one per wavelength)
    # share seed+scale, so the lens noise field, its blurred gradient, and the
    # photon grid are IDENTICAL across all three — only `strength` (the ray
    # deflection magnitude) and the resulting histogram differ. The old code
    # rebuilt lens + cubic-upsampled 3-octave noise + GaussianBlur + gradient
    # THREE times (the bulk of the cost). Hoist that shared prefix and repeat
    # only the strength-dependent displacement + histogram2d. Bit-identical:
    # every per-wavelength op is byte-for-byte the body of _caustics.
    sharp = 1.15
    grid_mul = 1.35
    gh, gw = int(h * grid_mul), int(w * grid_mul)
    lens = _noise(gh, gw, seed ^ 0xCA57, (scale * 0.6, scale, scale * 2.2))
    gy, gx = np.gradient(_gauss(lens, scale * 0.06))
    yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
    cell = (h * w / (gh * gw))
    webs = []
    for k in (1.0 - 0.04 * split, 1.0, 1.0 + 0.04 * split):
        st = strength * k
        # exact original op order: (xx + gx*st*gw/12.0)*(w/gw)
        px = (xx + gx * st * gw / 12.0) * (w / gw)
        py = (yy + gy * st * gh / 12.0) * (h / gh)
        hist, _, _ = np.histogram2d(py.ravel(), px.ravel(), bins=(h, w),
                                    range=[[0, h], [0, w]])
        d = hist.astype(np.float32) * cell
        d = _gauss(d, 0.8)
        wv = np.clip(_n01(d) ** sharp, 0, 1)
        webs.append(np.clip(wv * 2.4, 0, 1))
    return np.stack(webs[::-1], -1).astype(np.float32)   # R gets the widest bend


# ---------------------------------------------------------------- moire beat
def moire_phase(h, w, seed, pitch=4.2, d_angle=0.06, d_pitch=0.03):
    """Two fine line lattices at slightly different angle/pitch. Returns
    (lines, beat) — beat is the giant slow interference phase 0..1 that rolls
    across the canvas while the micro-lines stay visible."""
    rng = _rng(seed, 131)
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    a = float(rng.uniform(0, np.pi))
    p = pitch * sr
    ph1 = (xx * np.cos(a) + yy * np.sin(a)) * (2 * np.pi / p)
    ph2 = (xx * np.cos(a + d_angle) + yy * np.sin(a + d_angle)) * (2 * np.pi / (p * (1 + d_pitch)))
    l1 = 0.5 + 0.5 * np.sin(ph1)
    l2 = 0.5 + 0.5 * np.sin(ph2)
    lines = np.maximum(l1, l2).astype(np.float32)
    beat = (0.5 + 0.5 * np.sin(ph1 - ph2)).astype(np.float32)
    return lines, _n01(_gauss(beat, 2))


# ---------------------------------------------------------------- hue advection
def hue_advect(h, w, seed, theta=None, steps=90, decay=0.92):
    """Spectrum as a fluid: seed a hue scalar from noise, advect it along the
    flow (semi-Lagrangian backtrace) so hue STREAMS and eddies trap color.
    Returns (hue01, speed01)."""
    if theta is None:
        theta = _flow_theta(h, w, seed, scale=150, turns=1.6, swirls=3)
    hsm = max(h // 2, 96)
    th = cv2.resize(theta, (hsm, hsm), interpolation=cv2.INTER_LINEAR)
    hue = _noise(hsm, hsm, seed ^ 0x9D, (40, 110)).astype(np.float32)
    yy, xx = np.mgrid[0:hsm, 0:hsm].astype(np.float32)
    step = 1.6
    for _ in range(int(steps)):
        bx = np.clip(xx - np.cos(th) * step, 0, hsm - 1)
        by = np.clip(yy - np.sin(th) * step, 0, hsm - 1)
        hue = cv2.remap(hue, bx, by, cv2.INTER_LINEAR)
    hue = cv2.resize(hue, (w, h), interpolation=cv2.INTER_CUBIC)
    gy, gx = np.gradient(_gauss(cv2.resize(th, (w, h)), 4))
    speed = _n01(np.abs(gx) + np.abs(gy))
    return _n01(hue), speed.astype(np.float32)


# ---------------------------------------------------------------- blackbody
_BB_STOPS = [(0.04, 0.01, 0.0), (0.45, 0.05, 0.0), (0.85, 0.28, 0.02),
             (1.0, 0.62, 0.18), (1.0, 0.92, 0.65), (1.0, 1.0, 0.97),
             (0.80, 0.88, 1.0)]


def blackbody(t_field, flatten=0.15):
    """True incandescence ramp (Planck locus path: black->cherry->orange->
    white->blue-white) on a 0..1 temperature field."""
    return _ramp(_BB_STOPS, np.clip(t_field, 0, 1), flatten_lightness=flatten)


# ---------------------------------------------------------------- chromatic split
def chromatic_split(img, seed, amount=4.0, theta=None):
    """Lens dispersion: shear R and B channels opposite ways along a direction
    field — every luminance edge grows a prism fringe."""
    h, w = img.shape[:2]
    sr = _sr(h, w)
    if theta is None:
        theta = _flow_theta(h, w, seed ^ 0x77, scale=240, turns=0.5)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = (np.cos(theta) * amount * sr).astype(np.float32)
    dy = (np.sin(theta) * amount * sr).astype(np.float32)
    R = cv2.remap(img[..., 0], xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    B = cv2.remap(img[..., 2], xx - dx, yy - dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    out = img.copy()
    out[..., 0] = R; out[..., 2] = B
    return np.clip(out, 0, 1)


# ---------------------------------------------------------------- contours / lathe
def spectral_contours(h, w, seed, n_bands=26, scales=(120, 300, 640)):
    """Topo isolines cycling phase + slope shade. Returns (line, band01, slope)."""
    elev = _noise(h, w, seed ^ 0xE1, scales)
    band = (elev * n_bands) % 1.0
    line = _sstep(0.0, 0.10, band) * (1 - _sstep(0.10, 0.2, band))
    gy, gx = np.gradient(_gauss(elev, 3))
    slope = _n01(np.abs(gx) + np.abs(gy))
    return line.astype(np.float32), _n01(elev), slope.astype(np.float32)


def spectral_lathe(h, w, seed, n_centers=14, pitch=5.0):
    """Spin-cut guilloche: overlapping circular cut systems; hue = local cut
    ANGLE (like light raking a turned metal dial). Returns (cuts, cutangle01)."""
    rng = _rng(seed, 137)
    sr = _sr(h, w)
    yy, xx = _coords(h, w)
    cuts = np.zeros((h, w), np.float32)
    angm = np.zeros((h, w), np.float32)
    wsum = np.zeros((h, w), np.float32)
    for _ in range(int(n_centers)):
        cx, cy = rng.uniform(-0.2, 1.2) * w, rng.uniform(-0.2, 1.2) * h
        dx, dy = xx - cx, yy - cy
        r = np.sqrt(dx * dx + dy * dy)
        ring = 0.5 + 0.5 * np.sin(r * (2 * np.pi / (pitch * sr * rng.uniform(0.8, 1.3))))
        env = np.exp(-r / (rng.uniform(220, 480) * sr))
        cuts = np.maximum(cuts, ring * env)
        a = (np.arctan2(dy, dx) / (2 * np.pi)) % 1.0
        angm += a * env; wsum += env
    return cuts.astype(np.float32), _n01(angm / np.maximum(wsum, 1e-4))


# ---------------------------------------------------------------- doppler
def doppler_field(h, w, seed, hue_base, theta=None, shift=0.22, smear=10):
    """Red/blue-shift a hue field along a motion direction: hue shifted down
    (red) where receding, up (blue) where approaching, with motion smear."""
    sr = _sr(h, w)
    if theta is None:
        theta = _flow_theta(h, w, seed ^ 0x3D, scale=200, turns=1.0)
    gy, gx = np.gradient(_gauss(hue_base, 4))
    radial = gx * np.cos(theta) + gy * np.sin(theta)
    shifted = np.clip(hue_base + np.tanh(radial * 40) * shift, 0, 1)
    a = float(_rng(seed, 7).uniform(0, np.pi))
    return _dirblur(shifted.astype(np.float32), a, int(smear * sr))


# ---------------------------------------------------------------- einstein lens
def einstein_arcs(h, w, seed, n_masses=7, strength=26.0):
    """Gravitational lensing: warp a background starfield/halo field
    tangentially around dark mass cores -> Einstein arcs + rings.
    Returns (lensed_light, cores)."""
    rng = _rng(seed, 139)
    sr = _sr(h, w)
    bg = _stars(h, w, seed ^ 0x21, n=22000, bright_frac=0.02) + \
        _noise(h, w, seed ^ 0x99, (50, 130)) * 0.25
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    mx, my = xx.copy(), yy.copy()
    cores = np.zeros((h, w), np.float32)
    for _ in range(int(n_masses)):
        cx, cy = rng.uniform(0.1, 0.9) * w, rng.uniform(0.1, 0.9) * h
        M = rng.uniform(0.5, 1.4) * strength * sr
        dx, dy = mx - cx, my - cy
        r2 = dx * dx + dy * dy + (8 * sr) ** 2
        # deflection toward the mass ~ M/r (point-lens)
        mx = mx - dx * (M * 28 * sr) / r2
        my = my - dy * (M * 28 * sr) / r2
        cores = np.maximum(cores, np.exp(-r2 / (2 * (16 * sr * M / strength / sr) ** 2 + 1e-3)))
        cores = np.maximum(cores, np.exp(-((np.sqrt(r2)) / (14 * sr)) ** 2))
    lensed = cv2.remap(bg.astype(np.float32), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return np.clip(lensed, 0, 1), np.clip(cores, 0, 1)


# ---------------------------------------------------------------- bismuth hoppers
def hopper_terraces(h, w, seed, n_crystals=70):
    """Bismuth hopper crystals: square-spiral stepped terraces per crystal —
    the instantly recognisable rainbow-anodized staircase geode look.
    Returns (step01, depth01, edge) — step01 quantized terrace levels."""
    rng = _rng(seed, 149)
    cid, edge, orient, axial = _crystal(h, w, seed, n_sites=n_crystals, aniso=1.15, res=0.5)
    yy, xx = _coords(h, w)
    per = _n01(_cell_sin1(cid, 12.99))   # per-cell LUT (see _cell_sin1), bit-identical
    ang = per * np.pi
    # square-spiral terraces: chebyshev distance in each crystal's frame
    ca, sa = np.cos(ang), np.sin(ang)
    u = xx * ca + yy * sa
    v = -xx * sa + yy * ca
    sr = _sr(h, w)
    p = (7.0 + per * 9.0) * sr
    cheb = np.maximum(np.abs((u / p) - np.round(u / p)), np.abs((v / p) - np.round(v / p)))
    lvl = np.floor(((u / p) % 1.0) * 0 + (cheb * 8)) / 8.0     # quantized terrace level
    depth = _n01(lvl + per * 2.0)
    # NOTE 2026-06-13: the two `step_edge` lines computed a value that was never
    # returned (the second overwrote the first, then nothing used it). Removed —
    # pure dead-code elimination, output is byte-identical (lvl/depth/edge only).
    return lvl.astype(np.float32), depth.astype(np.float32), np.clip(edge, 0, 1).astype(np.float32)
