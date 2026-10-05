# -*- coding: utf-8 -*-
"""FRACTURED MORPHO (2026-07-30) — 50 color-shifting finishes built on nature's
STRUCTURAL color: thin-film / multilayer interference (morpho wings, jewel beetles,
hummingbird gorgets, nacre, opal, labradorite, bornite). The theme IS the doctrine:
a physical interference phase response is the ultimate color shifter.

Architecture mirrors fractured_themes_2026.py exactly (recipe dicts, GROUPS/ALL,
_mk closure, lru_cache'd work art shared by paint_fn + spec_fn, install_into_engine).
Engines are defined IN-MODULE (fractured_themes_fix_2026 precedent) — nothing here
touches engine/paint_v2/fractured_math.py.

MATH CORE — thin-film interference:
  structural generator -> optical-thickness field T (0..1) at <=640^2 -> cubic-up to
  _WORK=1152 -> one fancy-index into a precomputed 1024-entry interference LUT
  (sin^2 phase terms at ~640/550/470nm) -> iridescent RGB. Fully vectorized; nothing
  iterates at render res.

SPEC DOCTRINE (ghost_shift_2026 / fractured_souls_2026, owner-proven four dials):
  METAL ~215 mean (color amplifier, modulated by the SAME art so the gate std
  holds; swing widened to clip 60..255 after the 2026-07-30 M7 audit — the
  metalness travel across an interference field is physically large),
  ROUGHNESS floor ~20 rising toward ~140 along traced lanes (angular aperture),
  CLEARCOAT carved by the HUE domains of the art (env-reflection travel across
  interference color cells IS the color shift; hue-carving also decorrelates
  Cc from the luma-derived M/R channels — measured channel independence),
  PAINT crushed to recipe value x _VAL_GAIN (M7 audit 2026-07-30: the 0.10-0.22
  crush left the paint channel near-black and glass-smooth — M5 read
  spec-louder-than-paint on all 50; value recalibrated so the microstructure
  reads in the paint channel too; saturation kept),
  calm fallback (M=4, R=120, Cc=16) outside mask.
  pattern/edge/micro are traced FROM THE SAME cached art => spec mirrors paint.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from engine.expansions.fractured_wilds_signatures_2026 import make_entry as _wilds_entry

_WORK = 1152
_GEN = 640          # structural generators run here, then cubic-up to _WORK
# M7 audit revision (2026-07-30): uniform paint-value recalibration. The old
# 0.10-0.22 crush rendered the paint channel near-black (fine-energy rank 0.16,
# color population 2-8 bins) while the spec channel screamed -> M5 incoherence
# on all 50 finishes. Gain lifts the SAME art (no recolor, no structure change)
# so the interference microstructure reads in the paint channel too.
_VAL_GAIN = 2.4
_LUT_N = 1024

# ════════════════════════════════════════════════════════════════════════════
# SMALL VECTOR HELPERS (self-contained; no fractured_math imports)
# ════════════════════════════════════════════════════════════════════════════

def _rng(seed, salt=0):
    return np.random.default_rng([(int(seed) * 100003) & 0x7FFFFFFF, int(salt) & 0x7FFFFFFF])


def _n01(a):
    a = np.asarray(a, np.float32)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-9)


def _gauss(a, s):
    return cv2.GaussianBlur(np.asarray(a, np.float32), (0, 0), float(s))


def _sstep(a, b, x):
    t = np.clip((np.asarray(x, np.float32) - a) / (b - a + 1e-9), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _frac(a):
    a = np.asarray(a, np.float32)
    return (a - np.floor(a)).astype(np.float32)


def _coords(res):
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    return yy, xx


def _h2(cx, cy, salt=0):
    """Deterministic 2D cell hash -> 0..1 (per-scale / per-domain jitter)."""
    return _frac(np.sin(cx * 127.1 + cy * 311.7 + salt * 74.7) * 43758.5453)


def _fbm(h, w, rng, octaves=4, base=4, gain=0.55):
    """Multi-octave value noise (cubic-upscaled random grids). Vectorized."""
    acc = np.zeros((h, w), np.float32)
    amp, tot, res = 1.0, 0.0, int(base)
    for _ in range(int(octaves)):
        g = rng.random((res, res)).astype(np.float32)
        acc += amp * cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
        tot += amp
        amp *= gain
        res = min(res * 2, max(h, w) + 1)
        if res > max(h, w):
            break
    return acc / max(tot, 1e-9)


def _warp_pair(res, seed, salt, amt):
    """Two smooth warp-offset fields (domain warp), amplitude amt in px."""
    sr = res / 640.0
    wu = (_fbm(res, res, _rng(seed, salt), 3, 5) - 0.5) * float(amt) * sr
    wv = (_fbm(res, res, _rng(seed, salt + 1), 3, 5) - 0.5) * float(amt) * sr
    return wu.astype(np.float32), wv.astype(np.float32)


def _rot(uv, a):
    c, s = np.cos(a), np.sin(a)
    return uv[1] * c + uv[0] * s, -uv[1] * s + uv[0] * c


# ════════════════════════════════════════════════════════════════════════════
# THIN-FILM INTERFERENCE LUT — the physics core
# ════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=64)
def _thinfilm_lut(t_lo, t_hi, gamma, sat, phase):
    """1024-entry RGB LUT: optical thickness (nm) -> reflectance per channel via
    sin^2 phase terms at ~640/550/470nm (two-beam thin-film interference).
    sat<1 pulls toward the pearly mean, sat>1 pushes spectral purity."""
    i = np.arange(_LUT_N, dtype=np.float32) / (_LUT_N - 1)
    T = float(t_lo) + i * (float(t_hi) - float(t_lo))
    lam = np.array([640.0, 550.0, 470.0], np.float32)
    I = np.sin(2.0 * np.pi * T[:, None] / lam[None, :] + float(phase)) ** 2
    rgb = np.clip(I, 0.0, 1.0) ** float(gamma)
    m = rgb.mean(axis=1, keepdims=True)
    rgb = np.clip(m + (rgb - m) * float(sat), 0.0, 1.0)
    return rgb.astype(np.float32)


# ════════════════════════════════════════════════════════════════════════════
# STRUCTURAL GENERATORS — each returns an optical-thickness field T (0..1) at res.
# The STRUCTURE (not the palette) is what makes each finish unique.
# ════════════════════════════════════════════════════════════════════════════

def g_scales(res, seed, rows=24, aniso=1.30, rib=10.0, rib_amp=0.06, jit=0.55,
             warp=9.0, prof=0.35, drift=0.20, rim=0.0):
    """Butterfly wing-scale shingles: staggered overlapping elliptical scales,
    per-scale thickness jitter + rib striations along each scale. rim>0 adds a
    crisp interference ring at each scale's overlap edge (sharp luma steps)."""
    sr = res / 640.0
    rng = _rng(seed, 11)
    yy, xx = _coords(res)
    a = float(rng.uniform(0, np.pi))
    u, v = _rot((yy, xx), a)
    wu, wv = _warp_pair(res, seed, 12, warp)
    u += wu; v += wv
    rh = res / float(rows)
    v2 = v / rh
    row = np.floor(v2)
    u2 = u / (rh * float(aniso)) + 0.5 * (row % 2.0)
    col = np.floor(u2)
    fu = (u2 - col - 0.5).astype(np.float32)
    fv = (v2 - row - 0.62).astype(np.float32)
    d = np.sqrt(fu * fu + (fv * 1.30) ** 2)
    cell = _h2(col, row)
    dome = 0.5 - 0.5 * np.cos(np.pi * np.clip(d, 0.0, 1.0))          # scale bulge
    ribs = 0.5 + 0.5 * np.sin(fu * float(rib) * 2.0 * np.pi)          # fine ribs
    macro = _fbm(res, res, _rng(seed, 13), 3, 3)
    T = (cell * jit + dome * prof + ribs * rib_amp + macro * drift
         + _fbm(res, res, _rng(seed, 14), 2, 160) * 0.05)
    if rim > 0:
        T = T + float(rim) * np.exp(-((d - 0.50) ** 2) / 0.004)       # edge ring
    return _frac(T)


def g_ridges(res, seed, bands=70, warp=16.0, jit=0.40, lam=7.0, lam_amp=0.10,
             sharp=2.0, mix2=0.0, angle2=0.9, drift=0.25):
    """Morpho ridge lamellae: stacked directional ridges -> strong interference
    bands; per-ridge jitter + a fine cross-lamella ripple."""
    rng = _rng(seed, 21)
    yy, xx = _coords(res)
    a = float(rng.uniform(0, np.pi))
    u, v = _rot((yy, xx), a)
    wu, wv = _warp_pair(res, seed, 22, warp)
    u += wu; v += wv
    ph = u / (res / float(bands))
    band = np.floor(ph)
    fb = (ph - band).astype(np.float32)
    ridge = (1.0 - np.abs(2.0 * fb - 1.0)) ** float(sharp)
    lamella = 0.5 + 0.5 * np.sin(ph * 2.0 * np.pi * float(lam))
    macro = _fbm(res, res, _rng(seed, 23), 3, 3)
    T = _h2(band, 0) * jit + ridge * 0.5 + lamella * lam_amp + macro * drift
    if mix2 > 0:
        u2, _ = _rot((yy, xx), a + float(angle2))
        ph2 = u2 / (res / (float(bands) * 0.55)) + wu / res
        r2 = (1.0 - np.abs(2.0 * _frac(ph2) - 1.0)) ** float(sharp)
        T = T + r2 * float(mix2)
    T += _fbm(res, res, _rng(seed, 24), 2, 170) * 0.05
    return _frac(T)


def g_pits(res, seed, cells=24, depth=0.75, jit=0.50, rim=0.15, warp=5.0,
           fine=0.06):
    """Beetle pit lattice: hex-packed carapace dimples; bowl depth + bright rims
    + per-pit thickness jitter."""
    rng = _rng(seed, 31)
    yy, xx = _coords(res)
    a = float(rng.uniform(0, np.pi))
    u, v = _rot((yy, xx), a)
    wu, wv = _warp_pair(res, seed, 32, warp)
    u += wu; v += wv
    size = res / float(cells)
    x = u / size; y = v / size
    q = (np.sqrt(3.0) / 3.0) * x - y / 3.0
    r = (2.0 / 3.0) * y
    cz = -q - r
    rq, rr, rz = np.round(q), np.round(r), np.round(cz)
    dq, dr, dz = np.abs(rq - q), np.abs(rr - r), np.abs(rz - cz)
    fixq = (dq > dr) & (dq > dz)
    fixr = (~fixq) & (dr > dz)
    rq = np.where(fixq, -rr - rz, rq)
    rr = np.where(fixr, -rq - rz, rr)
    px = np.sqrt(3.0) * (q + r / 2.0); py = 1.5 * r
    ccx = np.sqrt(3.0) * (rq + rr / 2.0); ccy = 1.5 * rr
    d = np.sqrt((px - ccx) ** 2 + (py - ccy) ** 2).astype(np.float32)  # 0..~1
    bowl = (1.0 - np.clip(d, 0.0, 1.0)) ** 2
    ring = np.exp(-((d - 0.86) ** 2) / 0.006)
    macro = _fbm(res, res, _rng(seed, 33), 3, 3)
    T = (_h2(rq, rr) * jit + depth * bowl + rim * ring + macro * 0.18
         + _fbm(res, res, _rng(seed, 34), 2, 180) * fine)
    return _frac(T)


def g_barbules(res, seed, pitch=7.0, warp=12.0, second=0.30, sangle=1.15,
               bundle=0.23, drift=0.55, fine=0.05):
    """Feather barbules: anisotropic parallel striations with slow bundle
    modulation (hooks) and a second crossed striation family."""
    rng = _rng(seed, 41)
    yy, xx = _coords(res)
    a = float(rng.uniform(0, np.pi))
    u, v = _rot((yy, xx), a)
    wu, wv = _warp_pair(res, seed, 42, warp)
    u += wu; v += wv
    stri = u / (float(pitch) * res / 640.0)
    main = 0.5 + 0.5 * np.cos(2.0 * np.pi * stri)
    hook = 0.5 + 0.5 * np.cos(2.0 * np.pi * stri * float(bundle))
    macro = _fbm(res, res, _rng(seed, 43), 3, 3)
    T = macro * drift + main * (0.06 + 0.10 * hook)
    if second > 0:
        u2, _ = _rot((yy, xx), a + float(sangle))
        u2 += wv
        s2 = 0.5 + 0.5 * np.cos(2.0 * np.pi * u2 / (float(pitch) * 1.6 * res / 640.0))
        T += s2 * float(second) * 0.12
    T += _fbm(res, res, _rng(seed, 44), 2, 200) * fine
    return _frac(T)


def _worley(res, seed, cells, salt):
    """Jittered-grid Worley: (min distance 0..1, winning cell id hash). 9 taps."""
    g = res / float(cells)
    yy, xx = _coords(res)
    cu = np.floor(xx / g); cv = np.floor(yy / g)
    best = np.full((res, res), 1e9, np.float32)
    bid = np.zeros((res, res), np.float32)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            jx = _h2(cu + di, cv + dj, salt)
            jy = _h2(cu + di, cv + dj, salt + 50)
            fx = (cu + di + 0.15 + 0.7 * jx) * g
            fy = (cv + dj + 0.15 + 0.7 * jy) * g
            d = np.sqrt((xx - fx) ** 2 + (yy - fy) ** 2) / (g * 1.6)
            m = d < best
            best = np.where(m, d, best)
            bid = np.where(m, _h2(cu + di, cv + dj, salt + 90), bid)
    return np.clip(best, 0.0, 1.0), bid


def g_platelets(res, seed, cells=36, jit=0.85, rings=3.0, ring_amp=0.30,
                fine=0.05, gap=0.0):
    """Hummingbird platelet patches: angle-tuned hue domains (worley cells),
    each with its own base thickness + internal concentric rings."""
    d, bid = _worley(res, seed, cells, 51)
    ring = _frac(d * float(rings))
    macro = _fbm(res, res, _rng(seed, 52), 3, 3)
    T = bid * jit + ring * ring_amp + macro * 0.15
    if gap > 0:
        T += _sstep(0.92, 1.0, d) * float(gap)
    T += _fbm(res, res, _rng(seed, 53), 2, 190) * fine
    return _frac(T)


def g_nacre(res, seed, rows=32, aniso=2.0, mortar=0.07, jit=0.45, wave=0.10,
            warp=6.0, fine=0.05):
    """Nacre brick-and-mortar: staggered aragonite tablets with mortar grooves,
    per-tablet jitter and an internal growth wave."""
    rng = _rng(seed, 61)
    yy, xx = _coords(res)
    a = float(rng.uniform(0, np.pi))
    u, v = _rot((yy, xx), a)
    wu, wv = _warp_pair(res, seed, 62, warp)
    u += wu; v += wv
    rh = res / float(rows)
    v2 = v / rh
    row = np.floor(v2)
    u2 = u / (rh * float(aniso)) + 0.5 * (row % 2.0)
    col = np.floor(u2)
    fu = (u2 - col).astype(np.float32)         # 0..1 inside tablet
    fv = (v2 - row).astype(np.float32)
    dome = np.sin(np.pi * fu) * np.sin(np.pi * fv)
    eu = np.minimum(fu, 1.0 - fu); ev = np.minimum(fv, 1.0 - fv)
    groove = 1.0 - np.clip(np.minimum(eu, ev) / float(mortar), 0.0, 1.0)
    stri = 0.5 + 0.5 * np.sin(fv * 9.0 * np.pi + _h2(col, row, 3) * 6.0)
    macro = _fbm(res, res, _rng(seed, 63), 3, 3)
    T = (_h2(col, row) * jit + wave * dome - 0.25 * groove + 0.05 * stri
         + macro * 0.15 + _fbm(res, res, _rng(seed, 64), 2, 180) * fine)
    return _frac(T)


def g_film(res, seed, freq=9.0, octaves=2, amt=0.16, steps=2, grain=0.06,
           drain=0.0):
    """Curl-flow soap/oil film: a noise field advected along divergence-free
    curl noise (drainage swirls) -> flowing interference bands."""
    rng = _rng(seed, 71)
    psi = _fbm(res, res, rng, 4, 5)
    gy, gx = np.gradient(psi)
    f = _fbm(res, res, _rng(seed, 72), 5, 4)
    ys, xs = _coords(res)
    for _ in range(int(steps)):
        f = cv2.remap(f, np.clip(xs + gx * res * float(amt), 0, res - 1),
                      np.clip(ys - gy * res * float(amt), 0, res - 1),
                      cv2.INTER_LINEAR)
    T = _n01(f) * float(freq)
    if drain > 0:  # vertical drainage gradient on top (soap-film runoff)
        T += (ys / res) * float(drain)
    T += _fbm(res, res, _rng(seed, 73), 2, 200) * float(grain)
    return _frac(T)


def g_opal(res, seed, cells=26, jit=1.0, dome=0.6, speck=0.08, rings=2.0):
    """Opal sphere domains: packed silica-sphere patches, each a play-of-color
    domain with its own base thickness and a radial (dome) gradient."""
    d, bid = _worley(res, seed, cells, 81)
    macro = _fbm(res, res, _rng(seed, 82), 3, 3)
    T = (bid * jit + (d ** 2) * float(dome) + _frac(d * float(rings)) * 0.25
         + macro * 0.12 + _fbm(res, res, _rng(seed, 83), 2, 210) * float(speck))
    return _frac(T)


def g_lamellae(res, seed, bands=12, warp=10.0, twin=0.35, within=0.40,
               angle2=0.9, mix2=0.30, fine=0.05):
    """Labradorite twin lamellae: broad directional flash bands, each band its
    own hue offset, fine twin striations inside, second family crossing."""
    rng = _rng(seed, 91)
    yy, xx = _coords(res)
    a = float(rng.uniform(0, np.pi))
    u, v = _rot((yy, xx), a)
    wu, wv = _warp_pair(res, seed, 92, warp)
    u += wu; v += wv
    w = res / float(bands)
    bid = np.floor(u / w)
    fb = _frac(u / w)
    stripe = 0.5 + 0.5 * np.sin(2.0 * np.pi * (v / (w * 0.22) + _h2(bid, 0, 7) * 9.0))
    T = _h2(bid, 0) * 0.85 + fb * float(within) + stripe * float(twin) * 0.30
    if mix2 > 0:
        u2, _ = _rot((yy, xx), a + float(angle2))
        b2 = np.floor(u2 / (w * 1.7))
        T += (_h2(b2, 0, 5) * 0.6 + _frac(u2 / (w * 1.7)) * 0.3) * float(mix2)
    T += _fbm(res, res, _rng(seed, 93), 2, 190) * float(fine)
    return _frac(T)


def g_tarnish(res, seed, freq=3.0, octaves=5, warp=20.0, ridge=0.40,
              pit=0.20, fine=0.05):
    """Bornite/chalcopyrite tarnish: marbled multi-octave blotches, ridged
    veins and pitting — slow hue geography with sharp mineral detail."""
    rng = _rng(seed, 101)
    f = _fbm(res, res, rng, int(octaves), 3)
    psi = _fbm(res, res, _rng(seed, 102), 4, 5)
    gy, gx = np.gradient(psi)
    ys, xs = _coords(res)
    f = cv2.remap(f, np.clip(xs + gx * res * (float(warp) / res), 0, res - 1),
                  np.clip(ys - gy * res * (float(warp) / res), 0, res - 1),
                  cv2.INTER_LINEAR)
    r = 1.0 - np.abs(2.0 * _frac(_n01(f) * float(freq) * 0.5) - 1.0)   # ridged
    T = (_n01(f) * float(freq) + r * float(ridge)
         + _fbm(res, res, _rng(seed, 103), 3, 60) * float(pit)
         + _fbm(res, res, _rng(seed, 104), 2, 210) * float(fine))
    return _frac(T)


def g_grating(res, seed, gratings=4, f0=90.0, moire=0.50, warp=6.0, fine=0.05):
    """Crossed diffraction gratings: several fine line families at rotated
    angles beat into a holographic moire (butterfly ridge cross-section)."""
    rng = _rng(seed, 111)
    yy, xx = _coords(res)
    wu, wv = _warp_pair(res, seed, 112, warp)
    acc = np.zeros((res, res), np.float32)
    a0 = float(rng.uniform(0, np.pi))
    for k in range(int(gratings)):
        u, _ = _rot((yy, xx), a0 + k * (np.pi / (int(gratings) + 0.5)))
        u += wu * (1.0 + 0.2 * k)
        fr = float(f0) * (1.0 + 0.13 * k)
        acc += np.sin(2.0 * np.pi * u * fr / res)
    T = _n01(acc) * float(moire)
    T += _fbm(res, res, _rng(seed, 113), 2, 200) * float(fine)
    return _frac(T)


def g_eyespot(res, seed, spots=24, rmin=60.0, rmax=130.0, jit=0.40, fine=0.05):
    """Peacock-eye / owl-eye packets: scattered concentric-ring eyespots whose
    radial thickness ramp cycles the LUT into hue rings."""
    sr = res / 640.0
    rng = _rng(seed, 121)
    acc = np.zeros((res, res), np.float32)
    wsum = np.zeros((res, res), np.float32)
    n = max(6, int(spots * sr * sr))
    for _ in range(n):
        cx, cy = rng.uniform(0, res), rng.uniform(0, res)
        R = float(rng.uniform(rmin, rmax)) * sr
        x0, x1 = int(max(0, cx - R)), int(min(res, cx + R + 1))
        y0, y1 = int(max(0, cy - R)), int(min(res, cy + R + 1))
        if x1 <= x0 or y1 <= y0:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / R
        env = np.exp(-(r ** 2) * 2.2)
        acc[y0:y1, x0:x1] += env * (r + float(rng.uniform(0, jit)))
        wsum[y0:y1, x0:x1] += env
    macro = _fbm(res, res, _rng(seed, 122), 3, 3)
    T = (acc / np.maximum(wsum, 1e-3)) * 0.9 + macro * 0.25
    T += _fbm(res, res, _rng(seed, 123), 2, 200) * float(fine)
    return _frac(T)


ENGINES = {
    "scales": g_scales, "ridges": g_ridges, "pits": g_pits,
    "barbules": g_barbules, "platelets": g_platelets, "nacre": g_nacre,
    "film": g_film, "opal": g_opal, "lamellae": g_lamellae,
    "tarnish": g_tarnish, "grating": g_grating, "eyespot": g_eyespot,
}

# ════════════════════════════════════════════════════════════════════════════
# RECIPES — 50 finishes, ids fmo_*, seeds 900-949 (unique).
# Schema: name / engine / eargs / seed / lut=(t_lo,t_hi nm, gamma, sat, phase) /
#         val=paint crush value / kw=(ambient, ambient_sigma, floor, sparkle) / desc.
# Every recipe carries a one-line audit comment (ticket: owner brief 2026-07-30).
# ════════════════════════════════════════════════════════════════════════════

LEPIDOPTERA = {
 # [audit 2026-07-30] fine dense shingle scales, high rib count + crisp rim rings — the classic morpho
 # [wow 2026-07-30] hero BLUE window + wing-margin banding: dark rim, luminous blue-violet band
 "fmo_morpho_blue": dict(name="Morpho Blue", engine="scales",
    eargs=dict(rows=56, aniso=1.25, rib=20.0, rib_amp=0.28, jit=0.5, warp=8.0, prof=0.5, rim=0.42),
    seed=900, lut=(510.0, 680.0, 1.25, 0.55, 0.4), val=0.21,
    hues=[0.60], hspan=0.07, macro=("margin", dict(freq=3.0, radius=0.75)), vd=(0.22, 1.15), tmod=0.35,
    kw=dict(ambient=0.50, ambient_sigma=46, floor=0.10, sparkle=0.20, gray=0.75),
    desc="Overlapping wing-scale shingles ribbed with fine striations flashing electric blue-violet interference. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] broad sunset-moth ridge bands, wide multi-cycle thickness range
 # [wow 2026-07-30] sunset continents: magenta/amber/cyan in big coherent sweeps
 "fmo_sunset_moth": dict(name="Sunset Moth", engine="ridges",
    eargs=dict(bands=46, warp=20.0, jit=0.5, lam=5.0, lam_amp=0.12, sharp=1.6, drift=0.3),
    seed=901, lut=(220.0, 1450.0, 0.95, 1.25, 2.2), val=0.18,
    hues=[0.02, 0.10, 0.55], hspan=0.07, macro=("continents", dict(base=3, cells=4.0)), vd=(0.30, 1.10), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=50, floor=0.10, sparkle=0.07),
    desc="Broad stacked ridge lamellae sweeping the full sunset spectrum band by band. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] coarse low-rib scales + strong warp — monarch wing-cell feel
 # [wow 2026-07-30] ember-orange hero + wing-cell domains veined dark
 "fmo_monarch_vein": dict(name="Monarch Vein", engine="scales",
    eargs=dict(rows=14, aniso=1.6, rib=5.0, rib_amp=0.05, jit=0.65, warp=22.0, prof=0.45, drift=0.3),
    seed=902, lut=(300.0, 900.0, 1.0, 1.15, 4.0), val=0.16,
    hues=[0.07], hspan=0.05, macro=("domains", dict(cells=8)), vd=(0.25, 1.10), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=52, floor=0.10, sparkle=0.06),
    desc="Large warped wing-cell scales in ember-orange iridescence veined with dark grooves. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] very coarse atlas-wing scales, high dome profile
 # [wow 2026-07-30] bronze+teal twin heroes, concentric wing margin
 "fmo_atlas_wing": dict(name="Atlas Wing", engine="scales",
    eargs=dict(rows=9, aniso=1.1, rib=7.0, rib_amp=0.09, jit=0.7, warp=12.0, prof=0.55, drift=0.25),
    seed=903, lut=(260.0, 1100.0, 1.05, 1.2, 1.4), val=0.17,
    hues=[0.10, 0.45], hspan=0.06, macro=("margin", dict(freq=2.5, radius=0.78)), vd=(0.28, 1.12), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=54, floor=0.10, sparkle=0.07),
    desc="Huge overlapping atlas-moth scales domed with bronze-and-teal structural fire. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] fine dusted scales + heavy warp — luna-moth soft sheen
 # [wow 2026-07-30] pale moon-green window, soft dust patches (gray/flash dials kept for the sat-LOW intent)
 "fmo_luna_dust": dict(name="Luna Dust", engine="scales",
    eargs=dict(rows=48, aniso=1.45, rib=18.0, rib_amp=0.28, jit=0.4, warp=26.0, prof=0.45, drift=0.35),
    seed=904, lut=(300.0, 820.0, 1.0, 0.35, 5.2), val=0.30,
    hues=[0.30], hspan=0.08, satboost=1.0, macro=("domains", dict(cells=6)), vd=(0.55, 1.15), tmod=0.30,
    kw=dict(ambient=0.50, ambient_sigma=58, floor=0.14, sparkle=0.50, gray=0.40, flash=(0.40, 0.65), ccboost=1.8),
    desc="A dense dusting of tiny warped scales shimmering pale moon-green and pearl. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] angled swallowtail band ridges, two crossed families
 # [wow 2026-07-30] blue+gold heroes in steep diagonal flash bands
 "fmo_swallowtail": dict(name="Swallowtail Flash", engine="ridges",
    eargs=dict(bands=28, warp=10.0, jit=0.45, lam=9.0, lam_amp=0.1, sharp=2.4, mix2=0.35, angle2=0.8),
    seed=905, lut=(240.0, 1000.0, 1.0, 1.3, 3.6), val=0.18,
    hues=[0.58, 0.12], hspan=0.06, macro=("bands", dict(angle=0.9, freq=3.0)), vd=(0.25, 1.15), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.07),
    desc="Steep crossed ridge bands flashing blue and gold like a swallowtail's hindwing. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] platelet hue domains — ulysses angle-flash patches
 # [wow 2026-07-30] pure cobalt hero, deep dark field + detonating angle-tuned patch flashes
 "fmo_ulysses_flash": dict(name="Ulysses Flash", engine="platelets",
    eargs=dict(cells=52, jit=0.9, rings=2.0, ring_amp=0.2, gap=0.12),
    seed=906, lut=(300.0, 760.0, 0.9, 1.35, 0.9), val=0.17,
    hues=[0.58], hspan=0.05, macro=("domains", dict(cells=8)), vd=(0.15, 1.25), tmod=0.35,
    kw=dict(ambient=0.26, ambient_sigma=42, floor=0.10, sparkle=0.08, mswing=2.0, mfloor=10.0),
    desc="Angle-tuned platelet domains detonating cobalt flashes across a deep wing-dark field. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] owl-butterfly eyespot packets, concentric hue rings
 # [wow 2026-07-30] bronze+teal concentric eye rings — macro rings ARE the finish
 "fmo_owl_eye": dict(name="Owl Eye", engine="eyespot",
    eargs=dict(spots=18, rmin=90.0, rmax=180.0, jit=0.5),
    seed=907, lut=(260.0, 1250.0, 1.0, 1.2, 2.8), val=0.16,
    hues=[0.09, 0.55], hspan=0.06, macro=("rings", dict(freq=8.0, two=True)), vd=(0.25, 1.15), tmod=0.40,
    kw=dict(ambient=0.32, ambient_sigma=56, floor=0.10, sparkle=0.06),
    desc="Great concentric eyespot rings cycling bronze, violet and teal interference. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] glasswing membrane — low-freq curl film, pearly low saturation
 # [wow 2026-07-30] aqua-violet membrane sweeps, glassy low chroma
 "fmo_glasswing": dict(name="Glasswing", engine="film",
    eargs=dict(freq=4.5, octaves=2, amt=0.10, steps=2, grain=0.05),
    seed=908, lut=(240.0, 640.0, 1.15, 0.75, 1.1), val=0.15,
    hues=[0.50, 0.58], hspan=0.06, satboost=0.9, macro=("bands", dict(angle=0.4, freq=2.0, warp=0.30)), vd=(0.40, 1.15), tmod=0.30,
    kw=dict(ambient=0.36, ambient_sigma=60, floor=0.12, sparkle=0.06),
    desc="Clear membrane panels edged with faint pearly thin-film shimmer. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] high-aniso emperor scales, strong ribs, violet range
 # [wow 2026-07-30] regal purple+gold twin heroes, imperial margin banding
 "fmo_emperor_scale": dict(name="Emperor Scale", engine="scales",
    eargs=dict(rows=24, aniso=2.1, rib=11.0, rib_amp=0.26, jit=0.6, warp=6.0, prof=0.5, rim=0.30),
    seed=909, lut=(290.0, 840.0, 0.95, 1.35, 5.6), val=0.18,
    hues=[0.72, 0.12], hspan=0.06, macro=("margin", dict(freq=3.5, radius=0.72)), vd=(0.25, 1.12), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=44, floor=0.10, sparkle=0.30, rswing=2.6, rceil=225.0),
    desc="Stretched imperial scale rows ribbed with regal purple-and-gold interference. A FRACTURED MORPHO finish."),
}

COLEOPTERA = {
 # [audit 2026-07-30] fine hex pit lattice — jewel scarab dimpled carapace
 # [wow 2026-07-30] deep emerald hero with ruby flash pockets, big domain patches
 "fmo_jewel_scarab": dict(name="Jewel Scarab", engine="pits",
    eargs=dict(cells=30, depth=0.8, jit=0.55, rim=0.2, warp=4.0),
    seed=910, lut=(300.0, 820.0, 1.0, 1.3, 2.0), val=0.17,
    hues=[0.38, 0.0], hspan=0.06, macro=("domains", dict(cells=7)), vd=(0.18, 1.22), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.14),
    desc="A hex-packed lattice of dimpled pits blazing emerald-and-ruby structural metal. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] coarse warped pits — tiger beetle dappled elytra
 # [wow 2026-07-30] hunter-teal hero, bold diagonal flash bands over dark elytra
 "fmo_tiger_beetle": dict(name="Tiger Beetle", engine="pits",
    eargs=dict(cells=16, depth=0.65, jit=0.75, rim=0.12, warp=16.0, fine=0.08),
    seed=911, lut=(280.0, 940.0, 1.0, 1.25, 4.4), val=0.17,
    hues=[0.46, 0.09], hspan=0.06, macro=("bands", dict(angle=0.7, freq=2.5, warp=0.3)), vd=(0.20, 1.18), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=50, floor=0.10, sparkle=0.07),
    desc="Warped dappled pit fields flashing hunter-green and copper across hard elytra. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] broad lamellae — stag beetle chestnut carapace bands
 # [wow 2026-07-30] chestnut-bronze hero, big armour continents
 "fmo_stag_carapace": dict(name="Stag Carapace", engine="lamellae",
    eargs=dict(bands=9, warp=8.0, twin=0.25, within=0.5, mix2=0.2),
    seed=912, lut=(300.0, 980.0, 1.05, 1.1, 5.0), val=0.16,
    hues=[0.05, 0.30], hspan=0.05, macro=("continents", dict(base=3, cells=3.0)), vd=(0.16, 1.20), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=52, floor=0.10, sparkle=0.26),
    desc="Broad armour-plate lamellae glowing chestnut, bronze and bottle-green by angle. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] smooth low-freq film — chrysina liquid-gold mirror
 # [wow 2026-07-30] pure gold-amber hero, liquid mirror vortex
 "fmo_chrysina_gold": dict(name="Chrysina Gold", engine="film",
    eargs=dict(freq=5.5, octaves=2, amt=0.08, steps=1, grain=0.08),
    seed=913, lut=(350.0, 700.0, 1.0, 1.1, 0.2), val=0.20,
    hues=[0.11], hspan=0.05, macro=("vortex", dict(arms=2.0, twist=8.0)), vd=(0.30, 1.18), tmod=0.30,
    kw=dict(ambient=0.32, ambient_sigma=58, floor=0.11, sparkle=0.16, mswing=2.0, mfloor=10.0),
    desc="A liquid golden mirror film swirling with fine champagne interference ripples. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] dark oily curl film — oil beetle violet-black sheen
 # [wow 2026-07-30] violet-blue hero on black, slow curl vortex drains
 "fmo_oil_beetle": dict(name="Oil Beetle", engine="film",
    eargs=dict(freq=7.5, octaves=2, amt=0.22, steps=3, grain=0.14, drain=0.6),
    seed=914, lut=(260.0, 860.0, 1.05, 1.2, 3.2), val=0.15,
    hues=[0.68, 0.55], hspan=0.06, macro=("vortex", dict(arms=1.0, twist=6.0)), vd=(0.15, 1.20), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=48, floor=0.10, sparkle=0.14),
    desc="Thick violet-black oil sheen draining in slow curl swirls across the shell. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] warm platelet domains — firefly lantern shell
 # [wow 2026-07-30] amber lantern rings glowing out of near-black, concentric macro
 "fmo_firefly_shell": dict(name="Firefly Shell", engine="platelets",
    eargs=dict(cells=28, jit=0.7, rings=4.0, ring_amp=0.65, fine=0.28),
    seed=915, lut=(320.0, 900.0, 0.9, 1.25, 1.7), val=0.18,
    hues=[0.12, 0.33], hspan=0.05, macro=("rings", dict(freq=6.0)), vd=(0.16, 1.25), tmod=0.40,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.60, mswing=2.0, mfloor=10.0),
    desc="Lantern-warm platelet patches ringed with amber-and-green interference ripples. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] ultra-fine dense pitting — weevil rostrum texture
 # [wow 2026-07-30] turquoise-lime hero, broad margin band so the stipple has a stage
 "fmo_weevil_pit": dict(name="Weevil Pit", engine="pits",
    eargs=dict(cells=52, depth=0.7, jit=0.6, rim=0.25, warp=3.0, fine=0.08),
    seed=916, lut=(300.0, 800.0, 1.0, 1.3, 5.8), val=0.16,
    hues=[0.50, 0.30], hspan=0.06, macro=("margin", dict(freq=2.0, radius=0.75)), vd=(0.22, 1.15), tmod=0.30,
    kw=dict(ambient=0.26, ambient_sigma=42, floor=0.10, sparkle=0.09),
    desc="Countless micro-pits stippled across the shell, each glinting turquoise and lime. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] fine aniso elytra striae — ground beetle ridge rows
 # [wow 2026-07-30] violet-black hero, rachis shaft + striae lanes
 "fmo_ground_beetle": dict(name="Ground Beetle", engine="ridges",
    eargs=dict(bands=120, warp=6.0, jit=0.3, lam=3.0, lam_amp=0.06, sharp=3.0, drift=0.2),
    seed=917, lut=(280.0, 880.0, 1.0, 1.2, 2.5), val=0.16,
    hues=[0.70, 0.09], hspan=0.05, macro=("rachis", dict(angle=0.15, lanes=7.0)), vd=(0.18, 1.18), tmod=0.30,
    kw=dict(ambient=0.28, ambient_sigma=44, floor=0.10, sparkle=0.07),
    desc="Fine grooved elytra striae running the shell in violet-and-bronze interference rows. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] rugged coarse scales — scarab horn chitin
 # [wow 2026-07-30] dark amber + forest twin heroes, horn-band sweep
 "fmo_scarab_horn": dict(name="Scarab Horn", engine="scales",
    eargs=dict(rows=12, aniso=1.8, rib=6.0, rib_amp=0.07, jit=0.75, warp=18.0, prof=0.5),
    seed=918, lut=(310.0, 960.0, 1.05, 1.15, 0.4), val=0.17,
    hues=[0.09, 0.33], hspan=0.06, macro=("bands", dict(angle=1.2, freq=2.0, warp=0.35)), vd=(0.20, 1.16), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=50, floor=0.10, sparkle=0.16),
    desc="Rugged horn-chitin plates mottled with dark amber and forest-green structural fire. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] large domed opal cells — ladybird dome shell
 # [wow 2026-07-30] scarlet dome hero with gold roll-off, big dome domains
 "fmo_ladybird_dome": dict(name="Ladybird Dome", engine="opal",
    eargs=dict(cells=14, jit=0.85, dome=0.75, rings=1.5),
    seed=919, lut=(300.0, 1050.0, 0.95, 1.25, 3.9), val=0.18,
    hues=[0.02, 0.12], hspan=0.05, macro=("domains", dict(cells=5)), vd=(0.22, 1.20), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=50, floor=0.10, sparkle=0.16),
    desc="Bulging domed shell cells rolling scarlet, gold and jet interference across each dome. A FRACTURED MORPHO finish."),
}

AVIAN = {
 # [audit 2026-07-30] ultra-fine platelets — hummingbird gorget flash tiles
 # [wow 2026-07-30] ruby-to-emerald gorget: big coherent angle-tuned patches on black
 "fmo_hummingbird_gorget": dict(name="Hummingbird Gorget", engine="platelets",
    eargs=dict(cells=64, jit=0.95, rings=1.5, ring_amp=0.15, gap=0.1),
    seed=920, lut=(300.0, 820.0, 0.9, 1.4, 2.4), val=0.17,
    hues=[0.93, 0.35], hspan=0.06, macro=("domains", dict(cells=6)), vd=(0.20, 1.28), tmod=0.35,
    kw=dict(ambient=0.26, ambient_sigma=40, floor=0.10, sparkle=0.18),
    desc="A mosaic of tiny angle-tuned platelets detonating magenta-to-emerald gorget fire. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] dense small eyespots — peacock train ocelli
 # [wow 2026-07-30] sapphire/emerald/bronze ocelli — radial eye-spot rings ARE the finish
 "fmo_peacock_eye": dict(name="Peacock Eye", engine="eyespot",
    eargs=dict(spots=34, rmin=50.0, rmax=95.0, jit=0.6),
    seed=921, lut=(270.0, 1150.0, 0.95, 1.3, 1.2), val=0.17,
    hues=[0.58, 0.35, 0.09], hspan=0.06, macro=("rings", dict(freq=7.0, two=True)), vd=(0.22, 1.18), tmod=0.40,
    kw=dict(ambient=0.30, ambient_sigma=50, floor=0.10, sparkle=0.07),
    desc="A dense train of ocellated eyes ringed in sapphire, emerald and bronze. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] fine silky barbules — starling purple-green sheen
 # [wow 2026-07-30] oily purple+emerald twin heroes, feather rachis flow
 "fmo_starling_sheen": dict(name="Starling Sheen", engine="barbules",
    eargs=dict(pitch=5.5, warp=14.0, second=0.35, bundle=0.19, drift=0.5, fine=0.14),
    seed=922, lut=(290.0, 780.0, 1.0, 1.25, 4.8), val=0.20,
    hues=[0.72, 0.36], hspan=0.06, macro=("rachis", dict(angle=0.35, lanes=6.0)), vd=(0.20, 1.16), tmod=0.30,
    kw=dict(ambient=0.30, ambient_sigma=48, floor=0.10, sparkle=0.22),
    desc="Silky fine feather striations shimmering oily purple and green in lockstep. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] broad flash lamellae — magpie wing blue-white bars
 # [wow 2026-07-30] steel-blue wing bars with ivory shafts, rachis + lanes
 "fmo_magpie_wing": dict(name="Magpie Wing", engine="lamellae",
    eargs=dict(bands=14, warp=12.0, twin=0.4, within=0.45, mix2=0.35, angle2=1.1),
    seed=923, lut=(280.0, 900.0, 1.0, 1.2, 0.8), val=0.16,
    hues=[0.58, 0.13], hspan=0.05, macro=("rachis", dict(angle=0.8, lanes=5.0)), vd=(0.18, 1.22), tmod=0.30,
    kw=dict(ambient=0.30, ambient_sigma=50, floor=0.10, sparkle=0.06),
    desc="Bold wing-bar lamellae flashing steel blue and ivory across dark feather vanes. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] one broad curved speculum band system — duck wing flash
 # [wow 2026-07-30] teal-to-violet single sweeping speculum band on dark
 "fmo_duck_speculum": dict(name="Duck Speculum", engine="ridges",
    eargs=dict(bands=18, warp=30.0, jit=0.55, lam=4.0, lam_amp=0.14, sharp=1.4, drift=0.35),
    seed=924, lut=(300.0, 820.0, 0.95, 1.35, 3.0), val=0.17,
    hues=[0.52, 0.68], hspan=0.05, macro=("bands", dict(angle=1.1, freq=1.5, warp=0.4, lo=0.25, hi=0.75)), vd=(0.25, 1.30), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=52, floor=0.10, sparkle=0.07),
    desc="A sweeping curved speculum band blazing teal-to-violet like a mallard's wing flash. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] tight swirl film — pigeon neck green-pink shift
 # [wow 2026-07-30] emerald+rose twin heroes, neck-curl vortex
 "fmo_pigeon_neck": dict(name="Pigeon Neck", engine="film",
    eargs=dict(freq=10.0, octaves=2, amt=0.28, steps=3, grain=0.06),
    seed=925, lut=(280.0, 800.0, 1.0, 1.2, 5.4), val=0.15,
    hues=[0.36, 0.90], hspan=0.06, macro=("vortex", dict(arms=2.0, twist=9.0, two=True)), vd=(0.18, 1.22), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=48, floor=0.10, sparkle=0.32),
    desc="Tight neck-feather swirls shifting emerald to rose-pink with every turn. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] chaotic high-freq oil film — grackle rainbow-oil sheen
 # [wow 2026-07-30] bronze+violet oil churn: big vortex on black plumage
 "fmo_grackle_oil": dict(name="Grackle Oil", engine="film",
    eargs=dict(freq=13.0, octaves=3, amt=0.34, steps=4, grain=0.08, drain=0.3),
    seed=926, lut=(250.0, 1150.0, 0.95, 1.3, 1.9), val=0.15,
    hues=[0.09, 0.68], hspan=0.07, macro=("vortex", dict(arms=1.0, twist=7.0)), vd=(0.14, 1.22), tmod=0.40,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.08),
    desc="Chaotic rainbow-oil rivulets churning bronze, blue and violet across black plumage. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] very fine scales — sunbird throat glitter scales
 # [wow 2026-07-30] crimson+emerald spark patches, throat-flash domains
 "fmo_sunbird_throat": dict(name="Sunbird Throat", engine="scales",
    eargs=dict(rows=52, aniso=1.35, rib=16.0, rib_amp=0.06, jit=0.55, warp=10.0, prof=0.28),
    seed=927, lut=(300.0, 780.0, 0.9, 1.4, 2.1), val=0.17,
    hues=[0.96, 0.36], hspan=0.06, macro=("domains", dict(cells=5)), vd=(0.22, 1.25), tmod=0.35,
    kw=dict(ambient=0.26, ambient_sigma=42, floor=0.10, sparkle=0.18),
    desc="A glittering throat of microscopic scales firing crimson and emerald sparks. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] coarse double barbule quills — cassowary hair-feather
 # [wow 2026-07-30] blue-black quill strands + ember accents, wild rachis sweep
 "fmo_cassowary_quill": dict(name="Cassowary Quill", engine="barbules",
    eargs=dict(pitch=11.0, warp=20.0, second=0.5, sangle=0.7, bundle=0.31, drift=0.65, fine=0.14),
    seed=928, lut=(290.0, 880.0, 1.05, 1.15, 4.1), val=0.20,
    hues=[0.60, 0.06], hspan=0.06, macro=("rachis", dict(angle=1.4, lanes=5.0, sweep=6.0)), vd=(0.18, 1.20), tmod=0.30,
    kw=dict(ambient=0.30, ambient_sigma=50, floor=0.10, sparkle=0.22),
    desc="Coarse double quill strands raking blue-black iridescence in wild directions. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] fine dense lamellae — raven feather blue-flash vanes
 # [wow 2026-07-30] petrol-blue flash lanes across true raven black
 "fmo_raven_flash": dict(name="Raven Flash", engine="lamellae",
    eargs=dict(bands=26, warp=14.0, twin=0.5, within=0.35, mix2=0.25, angle2=0.6),
    seed=929, lut=(280.0, 840.0, 1.0, 1.25, 3.3), val=0.15,
    hues=[0.58, 0.72], hspan=0.05, macro=("bands", dict(angle=0.5, freq=2.5, warp=0.25)), vd=(0.12, 1.28), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=48, floor=0.10, sparkle=0.07, mswing=2.0, mfloor=10.0),
    desc="Dense feather-vane lamellae igniting petrol-blue flashes across raven black. A FRACTURED MORPHO finish."),
}

NACRE_FILM = {
 # [audit 2026-07-30] heavy-warp nacre tablets — abalone drift swirls
 # [wow 2026-07-30] teal/rose/silver-green currents in big drift bands
 "fmo_abalone_drift": dict(name="Abalone Drift", engine="nacre",
    eargs=dict(rows=26, aniso=2.4, mortar=0.09, jit=0.5, wave=0.14, warp=18.0),
    seed=930, lut=(260.0, 980.0, 0.95, 1.2, 0.5), val=0.18,
    hues=[0.50, 0.92, 0.38], hspan=0.06, macro=("bands", dict(angle=0.35, freq=2.5, warp=0.45)), vd=(0.25, 1.15), tmod=0.40,
    kw=dict(ambient=0.30, ambient_sigma=50, floor=0.11, sparkle=0.14),
    desc="Warped nacre tablets drifting in teal, rose and silver-green currents. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] slow dark film — black pearl deep orient
 # [wow 2026-07-30] charcoal body + slow peacock-orient vortex (gray/flash dials kept for sat-LOW intent)
 "fmo_black_pearl": dict(name="Black Pearl", engine="film",
    eargs=dict(freq=3.5, octaves=2, amt=0.12, steps=2, grain=0.24),
    seed=931, lut=(300.0, 700.0, 1.1, 0.38, 4.6), val=0.22,
    hues=[0.65, 0.38], hspan=0.07, satboost=0.8, macro=("vortex", dict(arms=1.0, twist=5.0)), vd=(0.30, 1.15), tmod=0.30,
    kw=dict(ambient=0.34, ambient_sigma=60, floor=0.10, sparkle=0.24, gray=0.55, flash=(0.40, 0.65), mswing=2.0, mfloor=10.0),
    desc="A deep charcoal orient rolling slow peacock hues beneath the surface. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] thin wide-cycle film with drainage — soap bubble
 # [wow 2026-07-30] full interference rainbow but in BIG curl vortices, not noise
 "fmo_soap_bubble": dict(name="Soap Bubble", engine="film",
    eargs=dict(freq=6.0, octaves=2, amt=0.18, steps=2, grain=0.05, drain=1.4),
    seed=932, lut=(180.0, 1300.0, 0.9, 1.15, 0.0), val=0.20,
    hues=[0.58, 0.05, 0.85], hspan=0.09, macro=("vortex", dict(arms=2.0, twist=11.0, two=True)), vd=(0.30, 1.12), tmod=0.55,
    kw=dict(ambient=0.30, ambient_sigma=52, floor=0.12, sparkle=0.06),
    desc="Draining soap-film bands swirling the full interference rainbow edge to edge. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] strong curl oil slick, mid frequency
 # [wow 2026-07-30] petrol rainbow in long shearing curl streaks on dark water
 "fmo_oil_slick": dict(name="Oil Slick", engine="film",
    eargs=dict(freq=8.5, octaves=3, amt=0.40, steps=4, grain=0.07, drain=0.4),
    seed=933, lut=(200.0, 1200.0, 0.95, 1.25, 2.7), val=0.18,
    hues=[0.75, 0.50, 0.12], hspan=0.08, macro=("vortex", dict(arms=1.0, twist=12.0, sectors=6.0)), vd=(0.16, 1.25), tmod=0.50,
    kw=dict(ambient=0.28, ambient_sigma=48, floor=0.11, sparkle=0.07),
    desc="Petrol-slick rainbows shearing across dark water in long curl-driven streaks. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] fine even nacre bricks — classic mother-of-pearl
 # [wow 2026-07-30] soft pink-mint-ivory pearl, gentle banded glow (low chroma by intent)
 "fmo_mother_of_pearl": dict(name="Mother of Pearl", engine="nacre",
    eargs=dict(rows=44, aniso=1.8, mortar=0.06, jit=0.4, wave=0.22, warp=5.0),
    seed=934, lut=(300.0, 760.0, 1.1, 0.85, 1.5), val=0.26,
    hues=[0.95, 0.42], hspan=0.07, satboost=0.50, macro=("bands", dict(angle=0.2, freq=2.0, warp=0.3)), vd=(0.52, 1.10), tmod=0.30,
    kw=dict(ambient=0.32, ambient_sigma=54, floor=0.12, sparkle=0.06, mswing=2.0, mfloor=10.0),
    desc="Fine even aragonite bricks shimmering soft pink, mint and ivory pearl. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] coarse bold nacre bricks — chunky brick-and-mortar
 # [wow 2026-07-30] per-brick pearl hue patchwork — big readable bricks
 "fmo_nacre_brick": dict(name="Nacre Brick", engine="nacre",
    eargs=dict(rows=16, aniso=2.8, mortar=0.11, jit=0.6, wave=0.16, warp=8.0),
    seed=935, lut=(280.0, 900.0, 1.0, 1.1, 3.4), val=0.19,
    hues=[0.50, 0.60, 0.10], hspan=0.06, macro=("domains", dict(cells=9)), vd=(0.28, 1.15), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=48, floor=0.11, sparkle=0.06),
    desc="Chunky brickwork tablets mortared with dark seams, each brick a different pearl hue. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] high-warp curved ridges — mussel shell growth lines
 # [wow 2026-07-30] deep blue-violet hero, curved growth-line margin
 "fmo_mussel_shell": dict(name="Mussel Shell", engine="ridges",
    eargs=dict(bands=60, warp=34.0, jit=0.5, lam=6.0, lam_amp=0.1, sharp=1.8, drift=0.4),
    seed=936, lut=(290.0, 860.0, 1.0, 1.2, 5.0), val=0.16,
    hues=[0.62, 0.72], hspan=0.05, macro=("margin", dict(freq=4.0, radius=0.8)), vd=(0.20, 1.18), tmod=0.35,
    kw=dict(ambient=0.30, ambient_sigma=50, floor=0.10, sparkle=0.06),
    desc="Curved growth-line ridges rippling deep blue and violet nacre along the shell. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] small packed opal domains — sea-foam bubble film
 # [wow 2026-07-30] aqua-violet foam rings — packed bubble eyes
 "fmo_foam_film": dict(name="Foam Film", engine="opal",
    eargs=dict(cells=48, jit=0.9, dome=0.5, rings=3.0, speck=0.1),
    seed=937, lut=(220.0, 1000.0, 0.95, 1.1, 1.0), val=0.19,
    hues=[0.52, 0.65], hspan=0.07, macro=("rings", dict(freq=10.0, two=True)), vd=(0.32, 1.12), tmod=0.40,
    kw=dict(ambient=0.30, ambient_sigma=46, floor=0.12, sparkle=0.07),
    desc="Packed foam-bubble domes each swirling its own tiny soap-film rainbow. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] storm-warped tarnish swirls — paua shell chaos
 # [wow 2026-07-30] storm-grey paua: turquoise-violet flash inside churned vortex (gray/flash kept)
 "fmo_paua_storm": dict(name="Paua Storm", engine="tarnish",
    eargs=dict(freq=4.5, octaves=5, warp=30.0, ridge=0.5, pit=0.25),
    seed=938, lut=(260.0, 940.0, 0.95, 0.38, 2.3), val=0.22,
    hues=[0.50, 0.65], hspan=0.07, macro=("vortex", dict(arms=2.0, twist=9.0)), vd=(0.28, 1.20), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=48, floor=0.10, sparkle=0.14, gray=0.50, flash=(0.42, 0.68)),
    desc="Storm-churned paua swirls boiling turquoise, peacock-green and violet. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] fine high-row nacre with strong waves — oyster interior
 # [wow 2026-07-30] silver-blush-aqua waves, broad luminous bands
 "fmo_pearl_oyster": dict(name="Pearl Oyster", engine="nacre",
    eargs=dict(rows=56, aniso=2.2, mortar=0.05, jit=0.45, wave=0.34, warp=12.0),
    seed=939, lut=(300.0, 800.0, 1.05, 0.95, 4.2), val=0.24,
    hues=[0.55, 0.08], hspan=0.07, satboost=0.45, macro=("bands", dict(angle=0.6, freq=2.5, warp=0.35)), vd=(0.50, 1.10), tmod=0.35,
    kw=dict(ambient=0.32, ambient_sigma=52, floor=0.12, sparkle=0.06, mswing=2.0, mfloor=10.0),
    desc="Dense rippled oyster nacre waving silver, blush and aqua across the shell. A FRACTURED MORPHO finish."),
}

MINERAL_FLASH = {
 # [audit 2026-07-30] classic broad labradorite twin lamellae
 # [wow 2026-07-30] electric-blue flash bands over near-black feldspar
 "fmo_labradorite": dict(name="Labradorite", engine="lamellae",
    eargs=dict(bands=11, warp=9.0, twin=0.45, within=0.42, mix2=0.3, angle2=0.95),
    seed=940, lut=(280.0, 900.0, 0.95, 1.3, 1.6), val=0.17,
    hues=[0.56], hspan=0.06, macro=("bands", dict(angle=0.75, freq=2.0, warp=0.3, lo=0.35, hi=0.7)), vd=(0.12, 1.30), tmod=0.40,
    kw=dict(ambient=0.28, ambient_sigma=48, floor=0.10, sparkle=0.07),
    desc="Broad twin lamellae flashing electric blue and gold across dark feldspar. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] small vivid opal domains on dark ground — black opal
 # [wow 2026-07-30] pinfire multi-hue domains over jet black (flash dial = sparse fire)
 "fmo_black_opal": dict(name="Black Opal", engine="opal",
    eargs=dict(cells=34, jit=1.1, dome=0.65, rings=2.5, speck=0.14),
    seed=941, lut=(250.0, 1250.0, 0.9, 1.2, 0.3), val=0.16,
    hues=[0.0, 0.33, 0.58], hspan=0.07, satboost=1.6, macro=("domains", dict(cells=7)), vd=(0.14, 1.35), tmod=0.40,
    kw=dict(ambient=0.26, ambient_sigma=44, floor=0.10, sparkle=0.22, gray=0.90, flash=(0.42, 0.68)),
    desc="Pinfire play-of-color domains igniting red, green and violet over jet black. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] coarse fractured platelet plates — ammolite dragon skin
 # [wow 2026-07-30] red-green-gold fossil fire in fractured plate continents
 "fmo_ammolite_skin": dict(name="Ammolite Skin", engine="platelets",
    eargs=dict(cells=18, jit=1.0, rings=3.5, ring_amp=0.4, gap=0.2),
    seed=942, lut=(240.0, 1350.0, 0.95, 1.35, 3.8), val=0.18,
    hues=[0.04, 0.30, 0.58], hspan=0.06, macro=("continents", dict(base=3, cells=4.0)), vd=(0.18, 1.22), tmod=0.40,
    kw=dict(ambient=0.26, ambient_sigma=44, floor=0.10, sparkle=0.08),
    desc="Fractured fossil plates stained in full-spectrum ammolite fire with dark seams. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] slow dusk tarnish — alexandrite teal-to-wine shift
 # [wow 2026-07-30] teal-to-wine dusk continents
 "fmo_alexandrite_dusk": dict(name="Alexandrite Dusk", engine="tarnish",
    eargs=dict(freq=3.0, octaves=5, warp=16.0, ridge=0.35, pit=0.15, fine=0.10),
    seed=943, lut=(300.0, 880.0, 1.05, 1.1, 5.1), val=0.17,
    hues=[0.48, 0.92], hspan=0.06, macro=("continents", dict(base=2, cells=3.0, lo=0.42, hi=0.58)), vd=(0.20, 1.18), tmod=0.35,
    kw=dict(ambient=0.32, ambient_sigma=56, floor=0.10, sparkle=0.14),
    desc="Slow dusk blotches shifting deep teal to wine-red under changing light. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] soft glowing low-freq film — moonstone adularescence
 # [wow 2026-07-30] floating blue-white adularescent glow band
 "fmo_moonstone_adular": dict(name="Moonstone Adular", engine="film",
    eargs=dict(freq=3.5, octaves=2, amt=0.14, steps=2, grain=0.08),
    seed=944, lut=(300.0, 780.0, 1.1, 1.0, 2.9), val=0.24,
    hues=[0.58], hspan=0.08, satboost=0.65, macro=("bands", dict(angle=0.3, freq=1.5, warp=0.5, lo=0.3, hi=0.75)), vd=(0.35, 1.20), tmod=0.35,
    kw=dict(ambient=0.36, ambient_sigma=62, floor=0.12, sparkle=0.07),
    desc="A floating blue-white adularescent glow drifting over fine silver schiller. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] glittering barbule flecks — sunstone aventurescence
 # [wow 2026-07-30] copper-gold aventurescence glitter field
 "fmo_sunstone_glitter": dict(name="Sunstone Glitter", engine="barbules",
    eargs=dict(pitch=4.0, warp=24.0, second=0.55, sangle=1.4, bundle=0.27, drift=0.7, fine=0.12),
    seed=945, lut=(280.0, 940.0, 0.95, 1.3, 0.7), val=0.20,
    hues=[0.08], hspan=0.05, macro=("domains", dict(cells=6)), vd=(0.22, 1.25), tmod=0.35,
    kw=dict(ambient=0.26, ambient_sigma=42, floor=0.10, sparkle=0.28),
    desc="A storm of glittering copper flecks spangling orange-gold interference sparks. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] botryoidal warped ridge bubbles — fire agate
 # [wow 2026-07-30] ember+green fire in botryoidal bubble rings
 "fmo_fire_agate": dict(name="Fire Agate", engine="ridges",
    eargs=dict(bands=36, warp=26.0, jit=0.6, lam=8.0, lam_amp=0.12, sharp=2.2, mix2=0.3, angle2=1.3),
    seed=946, lut=(320.0, 720.0, 0.95, 0.9, 4.9), val=0.16,
    hues=[0.06, 0.33], hspan=0.05, macro=("rings", dict(freq=6.0)), vd=(0.16, 1.25), tmod=0.40,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.08, gray=0.70),
    desc="Botryoidal bubble ridges bubbling with ember, green and violet fire. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] fine crossed lamellae veins — spectrolite
 # [wow 2026-07-30] full-spectrum flash in crossed vein bands
 "fmo_spectrolite_vein": dict(name="Spectrolite Vein", engine="lamellae",
    eargs=dict(bands=20, warp=16.0, twin=0.55, within=0.38, mix2=0.5, angle2=1.2),
    seed=947, lut=(270.0, 920.0, 0.95, 1.35, 2.6), val=0.16,
    hues=[0.55, 0.68, 0.35], hspan=0.07, macro=("bands", dict(angle=1.3, freq=3.0, warp=0.35)), vd=(0.14, 1.28), tmod=0.45,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.08),
    desc="Fine crossed spectral veins flashing the full labradorescent spectrum. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] classic bornite peacock-ore tarnish blotches
 # [wow 2026-07-30] purple-blue-copper peacock-ore continents
 "fmo_bornite_patina": dict(name="Bornite Patina", engine="tarnish",
    eargs=dict(freq=3.2, octaves=5, warp=22.0, ridge=0.45, pit=0.3, fine=0.07),
    seed=948, lut=(250.0, 1000.0, 1.0, 1.25, 1.3), val=0.16,
    hues=[0.75, 0.58, 0.10], hspan=0.07, macro=("continents", dict(base=3, cells=4.0)), vd=(0.25, 1.18), tmod=0.40,
    kw=dict(ambient=0.28, ambient_sigma=48, floor=0.10, sparkle=0.07),
    desc="Peacock-ore tarnish blotching purple, blue and copper across raw mineral. A FRACTURED MORPHO finish."),
 # [audit 2026-07-30] brassy platelet domains with pitting — chalcopyrite
 # [wow 2026-07-30] brass facets with magenta bloom domains
 "fmo_chalcopyrite": dict(name="Chalcopyrite", engine="platelets",
    eargs=dict(cells=40, jit=0.8, rings=2.5, ring_amp=0.3, gap=0.15, fine=0.08),
    seed=949, lut=(290.0, 950.0, 1.0, 1.2, 5.9), val=0.17,
    hues=[0.11, 0.80], hspan=0.06, macro=("domains", dict(cells=8)), vd=(0.20, 1.20), tmod=0.35,
    kw=dict(ambient=0.28, ambient_sigma=46, floor=0.10, sparkle=0.08),
    desc="Brassy crystal facets tarnished with magenta and teal iridescent bloom. A FRACTURED MORPHO finish."),
}

GROUPS = {
    "LEPIDOPTERA": LEPIDOPTERA,
    "COLEOPTERA": COLEOPTERA,
    "AVIAN": AVIAN,
    "NACRE & FILM": NACRE_FILM,
    "MINERAL FLASH": MINERAL_FLASH,
}

# id -> recipe across every group (built from the literals above at import).
ALL = {}
for _grp in GROUPS.values():
    ALL.update(_grp)


# ════════════════════════════════════════════════════════════════════════════
# ART ASSEMBLY — thickness field -> interference LUT -> iridescent RGB art.
# Cached per finish id; paint_fn and spec_fn share it (spec mirrors paint).
#
# AESTHETIC REBUILD (owner verdict 2026-07-30: "runs together, no wow factor"):
#   1. HERO HUE — every recipe declares a RESTRICTED hue window (hues/hspan).
#      The thin-film phase still drives hue, but compressed around the
#      namesake's real gamut (a morpho is BLUE with violet edges, not rainbow).
#      Multi-anchor recipes pick the anchor per macro DOMAIN (coherent patches,
#      not per-pixel confetti).
#   2. MACRO COMPOSITION — a cheap low-res (_MAC) composition layer (rings,
#      bands, margin, rachis, vortex, continents, domains) drives BOTH the
#      interference phase offset (color follows form) and the value drama
#      (deep blacks vs luminous flash zones). Fine structure rides ON it.
#   3. MACRO CLEARCOAT — spec_fn carves Cc primarily from the blocky domain
#      map (big coherent env-travel cells), micro/hue only as accent.
# ════════════════════════════════════════════════════════════════════════════

_MAC = 192          # macro composition layer resolution (then cubic-up, speed law)


def _macro_maps(d):
    """Composition layer for one recipe -> (Mval, Ddom) at _GEN res.

    Mval: smooth 0..1 value/composition map (value drama + phase offset).
    Ddom: 0..1 blocky domain map (hue-anchor pick + clearcoat carve cells).
    """
    seed = int(d["seed"])
    kind, mp = d.get("macro", ("none", {}))
    r = _MAC
    yy, xx = _coords(r)
    u, v = xx / r, yy / r
    rng = _rng(seed, 501)

    def _polar(cx, cy):
        dx = (u - cx) * float(mp.get("squish", 1.0))
        dy = v - cy
        return np.hypot(dx, dy), np.arctan2(dy, dx)

    if kind == "rings":
        # concentric eye-spot rings around 1-2 centers; ring index = domain
        cx, cy = float(mp.get("cx", 0.5)), float(mp.get("cy", 0.5))
        dist, _ = _polar(cx, cy)
        if mp.get("two"):
            d2, _ = _polar(float(mp.get("cx2", 0.72)), float(mp.get("cy2", 0.30)))
            dist = np.minimum(dist, d2 * 1.15)
        freq = float(mp.get("freq", 9.0))
        band = 0.5 + 0.5 * np.cos(2.0 * np.pi * freq * dist)
        M = _sstep(0.25, 0.75, band)
        M = M * np.clip(1.3 - dist, 0.0, 1.0)                    # fade outward
        D = _n01(_h2(np.floor(dist * freq), dist * 0.0, 7)
                 + _frac(dist * freq) * 0.4
                 + _fbm(r, r, _rng(seed, 502), 2, 3) * 0.10)
    elif kind == "bands":
        # broad diagonal flash bands over near-black; band index = domain
        ang = float(mp.get("angle", 0.6))
        ru, rv = _rot((yy, xx), ang)
        p = ru / r + _fbm(r, r, _rng(seed, 503), 3, 3) * float(mp.get("warp", 0.22))
        freq = float(mp.get("freq", 3.0))
        w = 0.5 + 0.5 * np.cos(2.0 * np.pi * freq * p)
        M = _sstep(float(mp.get("lo", 0.42)), float(mp.get("hi", 0.72)), w)
        M = M * (0.75 + 0.25 * _fbm(r, r, _rng(seed, 504), 2, 4))
        D = _n01(_h2(np.floor(p * freq), 0, 11) + _frac(p * freq) * 0.25)
    elif kind == "margin":
        # concentric wing-margin banding: luminous band inside a dark rim
        cx, cy = float(mp.get("cx", 0.5)), float(mp.get("cy", 0.52))
        dist, _ = _polar(cx, cy)
        dist = dist / max(float(mp.get("radius", 0.72)), 1e-3)
        ring = 0.5 + 0.5 * np.cos(2.0 * np.pi * float(mp.get("freq", 3.0)) * (1.0 - dist))
        M = _sstep(0.30, 0.80, ring) * _sstep(1.15, 0.55, dist)  # dark outside rim
        D = _n01(_h2(np.floor((1.0 - dist) * float(mp.get("freq", 3.0))), 0, 13)
                 + _fbm(r, r, _rng(seed, 505), 2, 3) * 0.15)
    elif kind == "rachis":
        # central shaft + directional falloff (feather vane); lanes = domain
        ang = float(mp.get("angle", 0.0))
        ru, rv = _rot((yy - r * 0.5, xx - r * 0.5), ang)
        shaft = np.exp(-((rv / r) ** 2) * float(mp.get("shaft", 900.0)))
        flow = 0.5 + 0.5 * np.sin(ru / r * float(mp.get("sweep", 4.0)) + _fbm(r, r, _rng(seed, 506), 2, 3) * 3.0)
        M = np.clip(shaft * 1.2 + flow * 0.55 * (1.0 - shaft * 0.4), 0.0, 1.0)
        D = _n01(_h2(np.floor((rv / r + 0.5) * float(mp.get("lanes", 6.0))), 0, 17)
                 + _frac((rv / r + 0.5) * float(mp.get("lanes", 6.0))) * 0.2)
    elif kind == "vortex":
        # 1-2 big curl vortices; angular sectors = domain
        cx, cy = float(mp.get("cx", 0.5)), float(mp.get("cy", 0.5))
        dist, angv = _polar(cx, cy)
        spiral = 0.5 + 0.5 * np.cos(angv * float(mp.get("arms", 2.0))
                                    + dist * float(mp.get("twist", 10.0)))
        M = _sstep(0.30, 0.75, spiral) * np.clip(1.25 - dist * 1.1, 0.15, 1.0)
        if mp.get("two"):
            d2, a2 = _polar(float(mp.get("cx2", 0.75)), float(mp.get("cy2", 0.72)))
            s2 = 0.5 + 0.5 * np.cos(a2 * float(mp.get("arms", 2.0)) + d2 * float(mp.get("twist", 10.0)))
            M = np.maximum(M, _sstep(0.35, 0.75, s2) * np.clip(1.1 - d2 * 1.4, 0.0, 1.0))
        D = _n01(_h2(np.floor((angv / np.pi + 1.0) * float(mp.get("sectors", 5.0))), 0, 19)
                 + dist * 0.3)
    elif kind == "continents":
        # big tarnish landmasses; per-continent random = domain
        f = _fbm(r, r, _rng(seed, 507), int(mp.get("oct", 4)), int(mp.get("base", 3)))
        f = f + _warp_pair(r, seed, 508, 6.0)[0] * 0.02
        M = _sstep(float(mp.get("lo", 0.38)), float(mp.get("hi", 0.62)), f)
        q = np.clip((f * float(mp.get("cells", 4.0))).astype(np.int32), 0, 63)
        D = _n01(_h2(q, 0, 23) + M * 0.25)
    elif kind == "domains":
        # coarse worley cells; per-cell random = domain, cell value = Mval
        cells = int(mp.get("cells", 10))
        _, cid = _worley(r, seed, cells, int(mp.get("salt", 29)))
        cv = _h2(cid, 0, 31)
        M = _n01(_gauss(cv, 1.2))                                 # smooth-ish patches
        D = _n01(_h2(cid, 0, 87))   # different salt: brightness NOT locked to anchor
    else:  # "none" — gentle low-freq variation only
        f = _fbm(r, r, _rng(seed, 509), 2, 3)
        M = 0.45 + 0.35 * (f - 0.5)
        D = _n01(np.clip((f * 5.0).astype(np.int32), 0, 63).astype(np.float32) / 8.0)

    Mval = cv2.resize(np.clip(M, 0.0, 1.0).astype(np.float32), (_GEN, _GEN),
                      interpolation=cv2.INTER_CUBIC)
    Ddom = cv2.resize(np.clip(D, 0.0, 1.0).astype(np.float32), (_GEN, _GEN),
                      interpolation=cv2.INTER_NEAREST)  # keep domains blocky
    return Mval.astype(np.float32), Ddom.astype(np.float32)


@lru_cache(maxsize=16)
def _macro_cached(fid):
    return _macro_maps(ALL[fid])


def _art_work(fid):
    """Work-res iridescent art (0..1 HxWx3 float32)."""
    d = ALL[fid]
    seed = int(d["seed"])
    Mval, Ddom = _macro_cached(fid)
    T = ENGINES[d["engine"]](_GEN, seed, **d.get("eargs", {}))
    # phase follows the macro form: color bands align with the composition
    T = _frac(np.asarray(T, np.float32) + Mval * float(d.get("tmod", 0.30)))
    lut = _thinfilm_lut(*d["lut"])
    idx = np.clip((T * (_LUT_N - 1)).astype(np.int32), 0, _LUT_N - 1)
    rgb = lut[idx]                                                # 640^2 RGB
    # HERO HUE WINDOW: remap the interference hue into the recipe's restricted
    # gamut (anchor per macro domain when several). Thin-film phase still
    # drives hue travel INSIDE the window; saturation pushed up (mud out).
    hues = d.get("hues")
    if hues:
        anchors = np.asarray(hues, np.float32)
        hspan = float(d.get("hspan", 0.07))
        # keep the thin-film's own luma texture: the HSV roundtrip + satboost
        # would otherwise compress fine-scale luma detail (fineness gate).
        Lpre = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])
        hsv = cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8),
                           cv2.COLOR_RGB2HSV).astype(np.float32)
        h = hsv[:, :, 0] * (1.0 / 179.0)
        if len(anchors) > 1:
            ai = np.clip((Ddom * len(anchors)).astype(np.int32), 0, len(anchors) - 1)
            c = anchors[ai]
        else:
            c = np.full_like(h, anchors[0])
        dh = ((h - c + 0.5) % 1.0) - 0.5
        hn = (c + dh * (hspan * 2.0)) % 1.0
        s = np.clip(hsv[:, :, 1] * (1.0 / 255.0) * float(d.get("satboost", 1.35)) + 0.08, 0, 1)
        hsv_out = np.stack([hn * 179.0, s * 255.0, hsv[:, :, 2]], axis=2)
        rgb = cv2.cvtColor(hsv_out.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32) * (1.0 / 255.0)
        Lpost = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])
        rgb = rgb * (Lpre / np.maximum(Lpost, 1e-3))[..., None]
    # VALUE DRAMA: deep blacks against luminous flash zones (macro-driven).
    shadow, flashv = d.get("vd", (0.30, 1.10))
    rgb = rgb * (float(shadow) + (float(flashv) - float(shadow)) * Mval)[..., None]
    kw = d.get("kw", {})
    # ambient bloom floor (fractured_math.colorize doctrine): a soft wide bloom
    # keeps even the darkest interference nulls off dead-black -> full coverage.
    # All finishing runs at _GEN (speed law: nothing iterates at render res);
    # ONE cubic upscale to _WORK at the end.
    sc = _GEN / float(_WORK)
    # M7 audit revision (2026-07-30): bloom mix halved. The old full-strength
    # mix washed 26-36% of every pixel through a sigma~46 blur, flattening the
    # micro-contrast the structural generators produce (measured paint fine
    # energy ~0.011 vs catalog median ~3x that). The anti-dead-black floor
    # below is untouched, so coverage holds.
    amb = float(kw.get("ambient", 0.30)) * 0.5
    bloom = cv2.GaussianBlur(rgb, (0, 0), float(kw.get("ambient_sigma", 48)) * sc)
    rgb = rgb * (1.0 - amb) + bloom * amb
    floor = float(kw.get("floor", 0.10))
    L = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])
    lift = np.clip(floor - L, 0.0, 1.0)[..., None]
    rgb = rgb + lift * bloom.mean(axis=(0, 1), keepdims=True) * 2.0
    # crushed micro sparkle — the highest of >=3 frequency bands
    spark = _fbm(_GEN, _GEN, _rng(seed, 777), 2, 320)
    rgb = rgb + (spark - 0.5)[..., None] * float(kw.get("sparkle", 0.07))
    # gray dial (2026-07-30 M7 audit): per-recipe chroma pull toward the pixel's
    # OWN luma — physical story is scattering in aged/thick dielectric stacks
    # (black opal potch, storm-grey paua, moondust). Luma micro-structure is
    # fully preserved, unlike ambient washing, so fine energy and the fineness
    # gate are unaffected. Used only by honestly dark-bodied recipes.
    Lg = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])[..., None]
    gray = float(kw.get("gray", 0.0))
    if gray > 0.0:
        rgb = rgb * (1.0 - gray) + Lg * gray
    # flash dial (2026-07-30 M7 audit): chroma gated by luma PEAKS — true
    # thin-film behavior: interference only fires at resonance maxima; the
    # dark body between flashes is dead gray potch. This is how a black opal
    # honestly reaches low MEAN saturation while keeping vivid pinfire:
    # chroma lives in sparse flash domains, not everywhere.
    fl_r = kw.get("flash")
    if fl_r:
        fl = _sstep(float(fl_r[0]), float(fl_r[1]), Lg)
        rgb = Lg + (rgb - Lg) * fl
    rgb = cv2.resize(np.clip(rgb, 0.0, 1.0), (_WORK, _WORK), interpolation=cv2.INTER_CUBIC)
    return np.clip(rgb, 0.0, 1.0).astype(np.float32)


@lru_cache(maxsize=8)
def _art_work_cached(fid):
    return _art_work(fid)


def _mk_legacy(fid):
    """Historical thin-film lab renderer retained as callable provenance."""
    val = float(ALL[fid].get("val", 0.16))

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and src.max() > 1.5:
            src = src / 255.0
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        art = cv2.resize(_art_work_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        # PAINT VALUE = the color mixer (SOULS doctrine): crush the iridescent
        # art to the recipe value, saturation kept — color fires through reveals.
        # _VAL_GAIN (2026-07-30 M7 audit): uniform recalibration — see constant.
        crushed = art * (min(val * _VAL_GAIN, 0.85) / max(float(art.max()), 1e-6))
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        out = src * (1.0 - kk) + crushed * kk
        return np.clip(out, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (_WORK, _WORK):
            m2 = cv2.resize(m2, (_WORK, _WORK), interpolation=cv2.INTER_LINEAR)
        # carve at _WORK from the cached art (no render-res iteration), one
        # uint8 resize at the end — the speed law that keeps 2048 under 3s.
        art = _art_work_cached(fid)
        L = (0.299 * art[:, :, 0] + 0.587 * art[:, :, 1] + 0.114 * art[:, :, 2]).astype(np.float32)
        # percentile stretch (not min-max): the interference luma histograms are
        # tight mid-band — stretching to p2/p98 gives the carve real travel.
        _lo, _hi = np.percentile(L, 2.0), np.percentile(L, 98.0)
        pattern = np.clip((L - _lo) / max(float(_hi - _lo), 1e-6), 0.0, 1.0)
        fl = _gauss(pattern, 1.2)
        gx = cv2.Sobel(fl, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(fl, cv2.CV_32F, 0, 1, ksize=3)
        edge = _n01(np.hypot(gx, gy))
        micro = _n01(pattern - _gauss(pattern, 2.5))
        # M7 audit revision (2026-07-30): hue-domain map. Carving every spec
        # channel from the same luma pattern left the channels correlated
        # (measured independence ~0.14). Clearcoat travel now follows the
        # interference HUE domains (saturation-weighted) — physically where
        # the color shift lives — so Cc decorrelates from luma-derived M/R.
        hsv = cv2.cvtColor((art * 255.0).astype(np.uint8), cv2.COLOR_RGB2HSV)
        hue = hsv[:, :, 0].astype(np.float32) * (1.0 / 179.0)
        # satn normalized PER IMAGE: gray-dialed recipes (black opal, luna dust)
        # keep their hue-domain structure readable to the clearcoat carve even
        # at low absolute chroma (fixes Cc-std collapse measured 2026-07-30).
        satn = _n01(hsv[:, :, 1].astype(np.float32))
        hdom = _n01(_gauss(hue * satn, 1.0))
        smf = float(sm)
        # MACRO CLEARCOAT (2026-07-30 wow rebuild): Cc carved primarily from
        # the blocky macro domain map -> env-reflection travel sweeps the car
        # in big coherent cells (100-400px @2048), not uniform micro shimmer.
        # Hue domains remain as accent for channel decorrelation (M6 profile
        # needs specCcRange HI + independence HI).
        _, _dd = _macro_cached(fid)
        domw = cv2.resize(_dd, (_WORK, _WORK), interpolation=cv2.INTER_NEAREST)
        hfield = _n01(0.72 * domw + 0.28 * hdom)
        # Per-recipe spec-swing dials (2026-07-30 M7 audit): finishes whose
        # NAMES promise metal/roughness travel (flash, pearl, gold, scale…)
        # widen ONLY their own M/R carve. Kept per-recipe after the global
        # widen experiment regressed M5 coherence catalog-wide (spec channels
        # outrunning the paint channel).
        rkw = ALL[fid].get("kw", {})
        msw = float(rkw.get("mswing", 1.0))
        rsw = float(rkw.get("rswing", 1.0))
        # ccpat: for heavily gray-dialed (low-chroma) recipes the hue domains
        # are too weak to carve clearcoat travel — blend the luma relief back
        # in. Physical story: in low-chroma stacks the env travel follows the
        # structural relief, not the color domains. (luna_dust Cc-std fix.)
        ccp = float(rkw.get("ccpat", 0.0))
        cfield = hfield * (1.0 - ccp) + pattern * ccp if ccp > 0.0 else hfield
        # mfloor/ccboost: per-recipe floor/boost escapes. mfloor drops the M
        # clip floor for metal-promise names whose swing otherwise bottoms out
        # at the shared 40 floor (measured: every mswing>=1.5 finish pinned at
        # range exactly 215 = 255-40). ccboost widens the Cc carve for
        # low-chroma recipes whose hue domains are subtle but REAL (preferred
        # over ccpat — keeps Cc hue-driven so channel independence holds).
        mfl = float(rkw.get("mfloor", 40.0))
        ccb = float(rkw.get("ccboost", 1.0))
        rcl = float(rkw.get("rceil", 195.0))
        # THE GHOST-SHIFT CONTRACT (owner-proven dials):
        #   METAL = the color amplifier. Mean near the lab's magic band; swings
        #   come from the SAME art (micro/edge/pattern) so the finish reads at
        #   macro scale and the catalog std gate (>=20) holds. Clip widened
        #   100..255 -> 60..255: metalness travel across an interference field
        #   is physically large (dielectric nulls to metallic peaks).
        M = np.clip(215.0 + ((micro - 0.5) * 320.0 + edge * 128.0 - (1.0 - pattern) * 96.0) * msw, mfl, 255.0)
        #   ROUGHNESS = the angular aperture: lane-driven, wider travel.
        lane = np.clip((pattern * 0.85 + edge * 0.75 - 0.42) * 1.9, 0.0, 1.0)
        R = np.clip(18.0 + (150.0 * lane + (micro - 0.5) * 40.0 - edge * 12.0) * rsw, 6.0, rcl)
        #   CLEARCOAT = the power supply, carved by the hue domains — the env
        #   travel across interference color cells IS the color shift.
        Cc = np.clip(224.0 - cfield * 190.0 * ccb + micro * 22.0, 16.0, 255.0)
        out = np.zeros((_WORK, _WORK, 4), np.uint8)
        mk = np.clip(m2, 0.0, 1.0)
        inv = 1.0 - mk
        out[:, :, 0] = np.clip(M * mk + 4.0 * inv, 0, 255).astype(np.uint8)
        out[:, :, 1] = np.clip(R * mk + 120.0 * inv, 0, 255).astype(np.uint8)
        out[:, :, 2] = np.clip(Cc * mk + 16.0 * inv, 0, 255).astype(np.uint8)
        out[:, :, 3] = 255
        if (fh, fw) != (_WORK, _WORK):
            out = cv2.resize(out, (fw, fh), interpolation=cv2.INTER_LINEAR)
        return out

    return spec_fn, paint_fn


def _mk(fid):
    # SPB-WILDS 2026-08-23 tick W-1. Owner: "Too much redundancy way too
    # similar looks. Must be VERY UNIQUE" and retain FRACTURED color flipping.
    # Replaces the repeated 100-400px ring/band/wedge composition grammar with
    # ID-specific seven-family micro glyphs and independent eight-tier M/R/CC.
    # Measured worst structural NN 0.787 -> 0.414, all-70 M7 minimum 85.0,
    # native-2048 max 0.702s; full evidence: _wilds_work/report.json.
    return _wilds_entry(fid, ALL[fid], "morpho")


def install_into_engine(mono_reg, base_reg=None):
    """Register every FRACTURED MORPHO finish into the monolithic + fusion
    registries (mirrors fractured_themes_2026.install_into_engine)."""
    regs = [mono_reg]
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys as _sys
    _eng = _sys.modules.get("shokker_engine_v2")
    if _eng is not None and hasattr(_eng, "FUSION_REGISTRY"):
        regs.append(_eng.FUSION_REGISTRY)
    n = 0
    for fid in ALL:
        entry = _mk(fid)
        for reg in regs:
            reg[fid] = entry
        n += 1
    counts = ", ".join(f"{g}:{len(d)}" for g, d in GROUPS.items())
    return f"fractured-morpho: {n} structural-color finishes live ({counts})"
