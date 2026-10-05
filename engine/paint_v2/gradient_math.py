"""GRADIENT MATH ENGINE (2026-06-18) — distinctive gradients, not boring linear ramps.

Owner brief: "our gradients don't need to look like everyone else's, they are boring."
The fix is three things ordinary gradients lack:
  1. PERCEPTUAL colour — interpolate in OKLab, so a blue->orange ramp travels through clean
     hues instead of the muddy grey sRGB-lerp produces. No dead mid-tones.
  2. WARP — the ramp coordinate drifts along a noise/curl flow (and is radial/diagonal, never a
     dead-straight up-down band) so it reads organic + UV-orientation-agnostic on a scattered car.
  3. STRUCTURE — ridged contour bands, fine dither-grain, iridescent hue-travel, or multi-source
     mesh bleed riding on top, so it's a designed SURFACE, not a flat fade.

Self-contained (numpy + cv2; reuses flame_math's noise). Each generator returns HxWx3 float 0..1
RGB paint, deterministic per seed, renders < 3s at 2048. UV-agnostic.
"""
from __future__ import annotations

import numpy as np
import cv2

from engine.paint_v2.flame_math import _fbm, _norm, _rng


# =====================================================================  OKLab perceptual colour
def _srgb_to_linear(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1.0 / 2.4) - 0.055)


def srgb_to_oklab(rgb):
    """HxWx3 (or Nx3) sRGB 0..1 -> OKLab (L, a, b)."""
    r, g, b = [_srgb_to_linear(rgb[..., i]) for i in range(3)]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return np.stack([L, a, bb], axis=-1)


def oklab_to_srgb(lab):
    """OKLab -> sRGB 0..1 (clipped)."""
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return np.clip(np.stack([_linear_to_srgb(r), _linear_to_srgb(g), _linear_to_srgb(bb)], axis=-1), 0.0, 1.0)


def oklab_ramp(t, stops_rgb, lut_n=512):
    """t: HxW float 0..1. stops_rgb: list of (pos, (r,g,b)) sRGB 0..1. Returns HxWx3 sRGB,
    interpolated PERCEPTUALLY in OKLab (clean hue travel, no muddy mids). Implemented as a 1D LUT
    (OKLab interp at lut_n points, converted once) then a fast gather — so a full 2048 ramp costs a
    lookup, not a per-pixel OKLab conversion (keeps every generator well under the render budget)."""
    ts = np.linspace(0.0, 1.0, lut_n).astype(np.float32)
    labs = [(p, srgb_to_oklab(np.array(c, np.float32)[None, None, :])[0, 0]) for p, c in stops_rgb]
    lut_lab = np.zeros((lut_n, 3), np.float32)
    lut_lab[:] = labs[0][1]
    for i in range(len(labs) - 1):
        p0, c0 = labs[i]
        p1, c1 = labs[i + 1]
        m = ts >= p0
        f = np.clip((ts - p0) / max(1e-6, p1 - p0), 0.0, 1.0)
        for ch in range(3):
            lut_lab[m, ch] = c0[ch] + (c1[ch] - c0[ch]) * f[m]
    lut_rgb = oklab_to_srgb(lut_lab[None, :, :])[0]            # lut_n x 3 sRGB, one conversion
    idx = np.clip((np.clip(t, 0.0, 1.0) * (lut_n - 1)).astype(np.int32), 0, lut_n - 1)
    return lut_rgb[idx]


# =====================================================================  palettes (tasteful, multi-hue)
PALETTES = {
    "sunset_drift":   [(0.0, (0.05, 0.02, 0.18)), (0.35, (0.55, 0.10, 0.42)), (0.7, (0.98, 0.42, 0.18)), (1.0, (1.0, 0.86, 0.45))],
    "aurora":         [(0.0, (0.02, 0.05, 0.12)), (0.4, (0.05, 0.55, 0.55)), (0.72, (0.35, 0.95, 0.55)), (1.0, (0.85, 0.95, 0.70))],
    "oilslick":       [(0.0, (0.10, 0.05, 0.30)), (0.3, (0.10, 0.45, 0.55)), (0.55, (0.20, 0.70, 0.35)), (0.78, (0.85, 0.55, 0.15)), (1.0, (0.65, 0.15, 0.45))],
    "ember_steel":    [(0.0, (0.06, 0.07, 0.10)), (0.5, (0.35, 0.20, 0.22)), (0.8, (0.92, 0.40, 0.12)), (1.0, (1.0, 0.82, 0.40))],
    "deep_sea":       [(0.0, (0.01, 0.03, 0.08)), (0.45, (0.02, 0.22, 0.40)), (0.78, (0.05, 0.55, 0.62)), (1.0, (0.55, 0.92, 0.85))],
    "candy_chrome":   [(0.0, (0.20, 0.05, 0.35)), (0.4, (0.85, 0.20, 0.55)), (0.7, (1.0, 0.55, 0.65)), (1.0, (0.95, 0.92, 0.98))],
    # --- color-diversity expansion 2026-06-18 (owner: "some of everything") ---
    "molten":         [(0.0, (0.08, 0.01, 0.02)), (0.4, (0.55, 0.06, 0.04)), (0.72, (0.98, 0.38, 0.06)), (1.0, (1.0, 0.88, 0.45))],
    "chrome_ice":     [(0.0, (0.04, 0.06, 0.10)), (0.45, (0.30, 0.42, 0.52)), (0.78, (0.70, 0.85, 0.95)), (1.0, (0.95, 0.99, 1.0))],
    "toxic":          [(0.0, (0.03, 0.10, 0.02)), (0.42, (0.20, 0.55, 0.05)), (0.72, (0.65, 0.95, 0.10)), (1.0, (0.92, 1.0, 0.55))],
    "royal":          [(0.0, (0.06, 0.02, 0.16)), (0.4, (0.35, 0.05, 0.45)), (0.7, (0.80, 0.20, 0.55)), (1.0, (0.98, 0.82, 0.40))],
    "miami":          [(0.0, (0.06, 0.10, 0.30)), (0.38, (0.10, 0.65, 0.70)), (0.68, (0.95, 0.35, 0.65)), (1.0, (1.0, 0.80, 0.55))],
}


def _grid(shape):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return yy, xx, xx / max(1, w - 1), yy / max(1, h - 1)


# =====================================================================  GRADIENT GENERATORS
def grad_oklab_flow(shape, seed=7, palette="sunset_drift"):
    """A perceptual OKLab ramp whose coordinate DRIFTS along a curl-noise flow — the gradient
    flows organically across the panel instead of a dead-straight band. UV-agnostic (diagonal base)."""
    h, w = shape
    yy, xx, xn, yn = _grid(shape)
    base = 0.5 * xn + 0.5 * yn                                   # diagonal base ramp
    warp = (_fbm((h, w), seed * 3 + 1, octaves=4, freq=2.2) - 0.5) * 0.55  # the drift
    t = _norm(base + warp)
    return oklab_ramp(t, PALETTES[palette])


def grad_iridescent(shape, seed=7, palette="oilslick", cycles=2.2):
    """OIL-SLICK / holographic: the hue TRAVELS through the spectrum multiple times along a
    warped radial coordinate, OKLab-smooth, with a thin-film sheen. Reads as iridescent metal film."""
    h, w = shape
    yy, xx, xn, yn = _grid(shape)
    cx, cy = 0.5 + 0.0, 0.5
    rad = np.sqrt((xn - cx) ** 2 + (yn - cy) ** 2) * 1.42
    warp = (_fbm((h, w), seed * 5 + 1, octaves=4, freq=3.0) - 0.5) * 0.4
    phase = (rad * cycles + warp) % 1.0                         # repeated hue travel = iridescence
    sheen = 0.5 + 0.5 * np.cos((rad * cycles + warp) * 2.0 * np.pi)
    rgb = oklab_ramp(phase, PALETTES[palette] + [(1.0, PALETTES[palette][0][1])])  # loop the ramp
    return np.clip(rgb * (0.75 + 0.30 * sheen[..., None]), 0, 1)


def grad_ridged_contour(shape, seed=7, palette="deep_sea", bands=11):
    """STRUCTURED: a warped ramp quantised into smooth CONTOUR bands (topographic ridges) with a
    bright ridge-line where bands meet — a designed surface, not a flat fade. Distinct banded look."""
    h, w = shape
    yy, xx, xn, yn = _grid(shape)
    field = _norm(0.6 * xn + 0.4 * yn + (_fbm((h, w), seed * 7 + 1, octaves=4, freq=2.6) - 0.5) * 0.7)
    q = field * bands
    band_id = np.floor(q)
    frac = q - band_id
    ridge = np.power(1.0 - np.abs(2.0 * frac - 1.0), 6.0)       # bright line at band centre
    t = _norm(band_id / max(1, bands - 1))
    rgb = oklab_ramp(t, PALETTES[palette])
    return np.clip(rgb * (0.78 + 0.0) + ridge[..., None] * 0.35, 0, 1)  # ridge highlight rides the bands


def grad_mesh_bleed(shape, seed=7, palette="aurora", sources=5):
    """GRADIENT MESH: several colour SOURCES bleed into each other (inverse-distance weighted),
    so colour pools and flows between points — a multi-source field, not a single-axis ramp."""
    h, w = shape
    yy, xx, xn, yn = _grid(shape)
    r = _rng(seed * 11 + 1)
    stops = PALETTES[palette]
    wsum = np.zeros((h, w), np.float32)
    acc = np.zeros((h, w, 3), np.float32)
    labs = [srgb_to_oklab(np.array(c, np.float32)[None, None, :])[0, 0] for _, c in stops]
    for i in range(sources):
        px, py = r.random(), r.random()
        col = labs[i % len(labs)]
        d = np.sqrt((xn - px) ** 2 + (yn - py) ** 2) + 0.04
        wgt = 1.0 / (d ** 2)
        wsum += wgt
        acc += wgt[..., None] * col
    lab = acc / wsum[..., None]
    lab[..., 0] = np.clip(lab[..., 0] + 0.07, 0, 1)             # lift L so the pools aren't muddy/dark
    return oklab_to_srgb(lab)


_SPECTRUM = [(0.0, (1.0, 0.05, 0.10)), (0.18, (1.0, 0.55, 0.0)), (0.34, (0.92, 0.92, 0.0)),
             (0.5, (0.05, 0.85, 0.25)), (0.66, (0.0, 0.80, 0.92)), (0.83, (0.15, 0.25, 1.0)),
             (1.0, (0.65, 0.05, 0.92))]


def grad_chromatic_aberration(shape, seed=7, palette="oilslick"):
    """CHROMATIC ABERRATION / prism split: sample the SAME warped ramp at three slightly different
    offsets, one per channel, so R/G/B diverge where the gradient bends — prismatic colour fringing
    like a lens edge or a glitch. Distinct from a clean ramp (the channels are mis-registered)."""
    h, w = shape
    yy, xx, xn, yn = _grid(shape)
    warp = (_fbm((h, w), seed * 17 + 1, octaves=4, freq=2.4) - 0.5) * 0.5
    base = 0.55 * xn + 0.45 * yn + warp
    chans = []
    for ci, off in enumerate((-0.055, 0.0, 0.055)):            # per-channel displacement = the split
        t = _norm(base + off)
        chans.append(oklab_ramp(t, PALETTES[palette])[..., ci])
    return np.clip(np.stack(chans, axis=2), 0, 1)


def grad_spectral_sweep(shape, seed=7, bend=1.0):
    """A full-SPECTRUM rainbow sweeping ONCE along a warped diagonal (directional travel), OKLab-
    smooth so the hues stay clean. Distinct from the concentric oil-slick iridescent — this is a
    single flowing rainbow band, not rings."""
    h, w = shape
    yy, xx, xn, yn = _grid(shape)
    warp = (_fbm((h, w), seed * 19 + 1, octaves=4, freq=2.6) - 0.5) * 0.5
    t = _norm(0.62 * xn + 0.38 * yn + warp * bend)
    return oklab_ramp(t, _SPECTRUM)


def grad_liquid_marble(shape, seed=7, palette="oilslick"):
    """LIQUID MARBLE: iteratively domain-WARP the coordinates (each pass folds the field into the
    last) then read a multi-hue OKLab ramp off swirled veins — stirred-paint marbling. Distinct from
    the single-warp flow (this folds repeatedly into chaotic swirls)."""
    h, w = shape
    yy, xx, xn, yn = _grid(shape)
    fx, fy = xn.copy(), yn.copy()
    for i in range(3):
        fx = fx + 0.40 * (_fbm((h, w), seed * 23 + 1 + i, octaves=4, freq=2.5 + i) - 0.5)
        fy = fy + 0.40 * (_fbm((h, w), seed * 23 + 11 + i, octaves=4, freq=2.5 + i) - 0.5)
    t = _norm(0.5 + 0.5 * np.sin((fx * 3.0 + fy * 2.0) * 2.0 * np.pi))   # swirled marble veins
    return oklab_ramp(t, PALETTES[palette])


def grad_moire_interference(shape, seed=7, palette="deep_sea"):
    """MOIRÉ INTERFERENCE: two crossed wave fields at near-orthogonal frequencies beat against each
    other into shimmering interference bands, coloured by an OKLab ramp. A woven optical pattern
    distinct from any single-axis ramp or colour field."""
    h, w = shape
    yy, xx, xn, yn = _grid(shape)
    warp = (_fbm((h, w), seed * 31 + 1, octaves=3, freq=2.2) - 0.5) * 0.35
    a1 = np.sin((xn * 17.0 + yn * 4.0) * 2.0 * np.pi + warp * 6.0)
    a2 = np.sin((xn * 4.0 + yn * 17.0) * 2.0 * np.pi + warp * 6.0)
    moire = _norm(a1 * a2)                                       # beat pattern
    t = _norm(0.45 * (0.5 * xn + 0.5 * yn) + 0.55 * moire)
    return oklab_ramp(t, PALETTES[palette])


def grad_holo_foil(shape, seed=7, stripes=8):
    """HOLOGRAPHIC FOIL: fine REPEATED diagonal rainbow strips (the spectrum loops several times
    across the panel) with a crossing sheen band — like a holo sticker catching light. Distinct
    from the single-pass spectral sweep (this repeats) and the concentric oil-slick (this is striped)."""
    h, w = shape
    yy, xx, xn, yn = _grid(shape)
    warp = (_fbm((h, w), seed * 37 + 1, octaves=3, freq=2.4) - 0.5) * 0.30
    phase = ((xn * 0.72 + yn * 0.28) * stripes + warp) % 1.0     # repeated rainbow strips
    rgb = oklab_ramp(phase, _SPECTRUM + [(1.0, _SPECTRUM[0][1])])
    sheen = 0.62 + 0.38 * np.cos((xn - yn) * 5.0 * 2.0 * np.pi)  # crossing holo sheen
    return np.clip(rgb * (0.80 + 0.25 * sheen[..., None]), 0, 1)


def grad_radial_burst(shape, seed=7, palette="candy_chrome"):
    """RADIAL BURST: colour swept by ANGLE around a point (a colour wheel) with a bright radial
    burst falling off outward — a starburst of colour. Distinct from the concentric rings (iridescent)
    and the directional sweeps (this is angular + radial)."""
    h, w = shape
    yy, xx, xn, yn = _grid(shape)
    cx, cy = 0.5, 0.5
    warp = (_fbm((h, w), seed * 41 + 1, octaves=3, freq=2.5) - 0.5) * 0.35
    th = np.arctan2(yn - cy, xn - cx)
    rad = np.sqrt((xn - cx) ** 2 + (yn - cy) ** 2) * 1.42
    t = _norm((th / (2.0 * np.pi) + 0.5) + warp * 0.3)           # hue by angle
    rgb = oklab_ramp(t, PALETTES[palette] + [(1.0, PALETTES[palette][0][1])])
    burst = np.clip(1.0 - rad * 0.7, 0.18, 1.0)
    return np.clip(rgb * (0.5 + 0.6 * burst[..., None]), 0, 1)


def grad_duotone_grain(shape, seed=7, palette="candy_chrome"):
    """DUOTONE-with-TEXTURE: a two-anchor OKLab ramp along a gently warped diagonal, broken up by
    fine ordered dither-GRAIN so the transition shimmers with micro-texture (premium, not flat)."""
    h, w = shape
    yy, xx, xn, yn = _grid(shape)
    stops = PALETTES[palette]
    duo = [stops[0], stops[-1]]
    warp = (_fbm((h, w), seed * 13 + 1, octaves=3, freq=2.5) - 0.5) * 0.5
    t = _norm(0.55 * xn + 0.45 * (1.0 - yn) + warp)
    # visible premium texture: coarse-ish flow grain + a fine high-freq sparkle, both ride the ramp
    grain = (_fbm((h, w), seed * 13 + 5, octaves=3, freq=24.0) - 0.5) * 0.22
    sparkle = (_fbm((h, w), seed * 13 + 9, octaves=2, freq=64.0) - 0.5) * 0.12
    rgb = oklab_ramp(np.clip(t + grain + sparkle, 0, 1), [(0.0, duo[0][1]), (1.0, duo[1][1])])
    return np.clip(rgb, 0, 1)


GRADIENT_STRUCTURES = {
    "oklab_flow":           grad_oklab_flow,
    "iridescent":           grad_iridescent,
    "ridged_contour":       grad_ridged_contour,
    "mesh_bleed":           grad_mesh_bleed,
    "duotone_grain":        grad_duotone_grain,
    "chromatic_aberration": grad_chromatic_aberration,
    "spectral_sweep":       grad_spectral_sweep,
    "liquid_marble":        grad_liquid_marble,
    "moire_interference":   grad_moire_interference,
    "holo_foil":            grad_holo_foil,
    "radial_burst":         grad_radial_burst,
}


# =====================================================================  GATE (mechanical, fail-closed)
# Owner mandate parallels the flames: distinct from each other + NOT a boring linear ramp + <3s.
MAX_GRAD_SIMILARITY = 0.85   # pairwise RGB-fingerprint correlation (colour-AWARE) above this = too similar
MIN_GRAD_STRUCTURE = 0.06    # fraction of colour variance NOT explained by a best-fit linear plane:
                             #   a flat linear ramp ~0 (boring -> FAIL); warp/bands/mesh/grain lift it.


def gradient_fingerprint(img):
    """Colour-AWARE fingerprint: 24x24x3 area-downsample, per-channel z-scored, flattened.
    Captures both layout AND colour so two same-layout different-colour ramps read as distinct."""
    a = cv2.resize(np.asarray(img, np.float32), (24, 24), interpolation=cv2.INTER_AREA)
    v = []
    for ch in range(3):
        c = a[..., ch]
        c = (c - c.mean()) / (c.std() + 1e-6)
        v.append(c.ravel())
    return np.concatenate(v)


def gradient_similarity(a, b):
    """|correlation| of two gradients' colour-aware fingerprints, in [0,1]."""
    fa, fb = gradient_fingerprint(a), gradient_fingerprint(b)
    if fa.std() < 1e-6 or fb.std() < 1e-6:
        return 0.0
    return abs(float(np.corrcoef(fa, fb)[0, 1]))


def gradient_structure(img):
    """Fraction of colour variance NOT explained by the best-fit LINEAR PLANE (a + b*x + c*y) per
    channel — i.e. how much warp / banding / mesh / grain rides on top of a plain ramp. A boring
    straight linear gradient fits a plane almost perfectly -> ~0. Higher = more designed structure."""
    a = cv2.resize(np.asarray(img, np.float32), (96, 96), interpolation=cv2.INTER_AREA)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    A = np.stack([np.ones_like(xx).ravel(), (xx / w).ravel(), (yy / h).ravel()], axis=1)
    resid_frac = []
    for ch in range(3):
        z = a[..., ch].ravel()
        var = z.var()
        if var < 1e-8:
            continue
        coef, *_ = np.linalg.lstsq(A, z, rcond=None)
        resid = z - A @ coef
        resid_frac.append(float(resid.var() / var))
    return float(np.mean(resid_frac)) if resid_frac else 0.0
