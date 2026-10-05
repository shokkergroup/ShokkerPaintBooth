# -*- coding: utf-8 -*-
"""FRACTURED FLAMES kit (2026-08-30 rebuild) — the shared engine for the 75.

WHY THE REBUILD (owner, 2026-08-30): *"we have 3 FRACTURED FLAMES categories and
way too many finishes. We only need about 75 total flames. And MANY of them are
repeats and redundant or just lazy/not good. Keep some of the better one's but
make new math and styles and apply what we've learned in the Spec channel to
make them really come to life."*

What the triage found in the shipped 135 (`_flames_work/triage.py`):

  * They are a CROSS-PRODUCT, not a catalog: 51 structures x {ignite,topo,dance}
    x a palette NAME. `flames_catalog_2026._art_work_cached` calls the structure
    with no palette argument, so a structure's 2-3 cards carry **byte-identical
    paint** and every card named "(Blue)" or "(Green Toxic)" is in fact ORANGE.
    Verified: `flm_curl_streamers_ignite_blue` mean RGB (0.366, 0.228, 0.173).
  * **42 of the 51 structures fail the car-band law** — one centred spiral, one
    sunburst, one cone, one rose per 2048 canvas. `radial` scores band 0.005.
    Only 9 passed coverage + car-band + distinctness unchanged.

So this kit fixes the two root causes:

  1. **COLOUR IS PHYSICS, NOT A TAG.** `blackbody()` integrates Planck's law
     against analytic CIE 1931 colour-matching functions, so 900K char red,
     1400K orange, 2200K yellow-white and 5000K blue-white are the REAL colours
     of those temperatures. `FUELS` then adds true chemiluminescence — copper
     green-blue, strontium crimson, sodium amber, potassium lilac, barium apple,
     lithium magenta, boron emerald. A card's palette is *what is burning*, and
     it drives the PAINT, not just the spec.
  2. **FIELDS, NOT POSTERS.** Every primitive here is built to put its energy in
     the car-visible 8-32px window (r 32..256 on a 2048 canvas), per the
     field-not-poster doctrine.

SPEC: `flame_spec()` implements Spec Guide v1 §7-§9 — complete material CARDS
chosen per coherent 8-24px cell (never a linear smear between tuples), causal
channels (a char pit is not a polished ridge), 2-6px dark-chrome hot edges on
the reaction front, sparse mirror sparks, and a clearcoat field deliberately
OFFSET from the metal/roughness field so the lobes peak at different angles.
"""
from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

GEN = 1024          # structures generate here
WORK = 1152         # art assembled here, resized to the render size
_TAU = 2.0 * np.pi


# ════════════════════════════════════════════════════════════════════════════
# 1. REAL FIRE COLOUR — Planck's law through the CIE 1931 observer
# ════════════════════════════════════════════════════════════════════════════

def _piecewise_gauss(x, mu, s1, s2):
    s = np.where(x < mu, s1, s2)
    return np.exp(-0.5 * ((x - mu) / s) ** 2)


def _cie_cmf(lam):
    """Wyman/Sloan/Shirley (2013) multi-lobe analytic fit of the CIE 1931 2-deg
    colour-matching functions. Accurate to well under a JND and 3 lines long,
    which beats shipping a 471-row table."""
    x = (1.056 * _piecewise_gauss(lam, 599.8, 37.9, 31.0)
         + 0.362 * _piecewise_gauss(lam, 442.0, 16.0, 26.7)
         - 0.065 * _piecewise_gauss(lam, 501.1, 20.4, 26.2))
    y = (0.821 * _piecewise_gauss(lam, 568.8, 46.9, 40.5)
         + 0.286 * _piecewise_gauss(lam, 530.9, 16.3, 31.1))
    z = (1.217 * _piecewise_gauss(lam, 437.0, 11.8, 36.0)
         + 0.681 * _piecewise_gauss(lam, 459.0, 26.0, 13.8))
    return x, y, z


_XYZ_TO_SRGB = np.array([[3.2406, -1.5372, -0.4986],
                         [-0.9689, 1.8758, 0.0415],
                         [0.0557, -0.2040, 1.0570]], np.float64)


def _xyz_to_srgb(xyz):
    rgb = _XYZ_TO_SRGB @ np.asarray(xyz, np.float64)
    rgb = np.clip(rgb, 0.0, None)
    m = rgb.max()
    if m > 0:
        rgb = rgb / m
    # sRGB transfer
    return np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * rgb ** (1 / 2.4) - 0.055)


def blackbody(temp_k):
    """The sRGB colour of a blackbody at `temp_k`, normalised to peak 1.

    This is why the new palettes read as FIRE rather than as an orange ramp:
    1000K really is a dull cherry, 1800K really is amber, 2800K really is warm
    white, and 6000K really is faintly blue."""
    lam = np.arange(380.0, 781.0, 5.0)
    l_m = lam * 1e-9
    c1, c2 = 3.7418e-16, 1.4388e-2
    rad = c1 / (l_m ** 5 * (np.exp(c2 / (l_m * float(temp_k))) - 1.0))
    xb, yb, zb = _cie_cmf(lam)
    xyz = np.array([(rad * xb).sum(), (rad * yb).sum(), (rad * zb).sum()])
    if xyz[1] <= 0:
        return np.zeros(3, np.float32)
    return np.asarray(_xyz_to_srgb(xyz / xyz[1]), np.float32)


def thermal_ladder(t_lo, t_hi, n=8, gamma=1.0, v_lo=0.10, v_hi=0.95):
    """`n` quantised blackbody tiers from `t_lo` to `t_hi` kelvin, each scaled by
    its own emissive brightness so the cool end genuinely goes dark instead of
    turning into pale pink. Owner Rule 2 wants many distinct shades — this is
    where a card gets them, and they are physically ordered."""
    ts = np.linspace(0.0, 1.0, int(n)) ** float(gamma)
    out = []
    for t in ts:
        T = t_lo + (t_hi - t_lo) * t
        rgb = blackbody(T)
        # Stefan-Boltzmann-ish visual weighting, compressed hard so the ladder
        # stays inside paint range rather than blowing to white.
        lvl = float(np.clip(((T - t_lo * 0.72) / max(t_hi - t_lo * 0.72, 1.0)), 0.02, 1.0)) ** 0.55
        out.append(rgb * lvl)
    lad = np.clip(np.asarray(out, np.float32), 0.0, 1.0)

    # RE-SPAN the ladder's VALUE range while keeping each tier's hue.
    # Raw emissive weighting lands the eight tiers between luma 0.09 and 0.63 —
    # a 0.48 span that reads as one muddy midtone wash on a car and occupied
    # only 4-7 of 12 value bins. The owner's Rule 2 asks for a ladder like
    # [0.18 ... 0.92]; a photograph of fire is tone-mapped the same way. The
    # ORDER and the CHROMATICITY are the physics — the exposure is not.
    L = 0.2126 * lad[:, 0] + 0.7152 * lad[:, 1] + 0.0722 * lad[:, 2]
    lo, hi = float(L.min()), float(L.max())
    if hi > lo:
        want = np.linspace(float(v_lo), float(v_hi), lad.shape[0], dtype=np.float32)
        gain = want / np.maximum(L, 1e-4)
        lad = lad * gain[:, None]
        # a tier that clips keeps its hue by scaling back, never by desaturating
        peak = lad.max(1)
        over = peak > 1.0
        if over.any():
            lad[over] = lad[over] / peak[over][:, None]
    return np.clip(lad, 0.0, 1.0)


# Real emission colours. Thermal entries are (T_lo, T_hi); chemical entries add
# spectral-line colours that a hot body simply cannot produce.
#   soot   0..1  how much unburnt carbon dulls and blackens the cool end
#   line   the chemiluminescent colour injected at the reaction front
FUELS = {
    # ---- thermal (what temperature alone gives you) -------------------------
    "char":       dict(t=(700, 1500),  soot=0.85, line=None),
    "wood":       dict(t=(900, 1900),  soot=0.62, line=None),
    "coal":       dict(t=(1000, 2100), soot=0.55, line=None),
    "furnace":    dict(t=(1200, 2600), soot=0.30, line=None),
    "magnesium":  dict(t=(2200, 3700), soot=0.05, line=(0.95, 0.97, 1.00)),
    "thermite":   dict(t=(1800, 3200), soot=0.12, line=(1.00, 0.93, 0.72)),
    # ---- chemical (what is burning decides the hue) ------------------------
    "copper":     dict(t=(900, 1700),  soot=0.35, line=(0.18, 1.00, 0.62)),
    "cupric":     dict(t=(900, 1600),  soot=0.35, line=(0.24, 0.62, 1.00)),
    "strontium":  dict(t=(900, 1800),  soot=0.40, line=(1.00, 0.10, 0.24)),
    "sodium":     dict(t=(900, 1800),  soot=0.45, line=(1.00, 0.72, 0.16)),
    "potassium":  dict(t=(900, 1700),  soot=0.38, line=(0.72, 0.42, 1.00)),
    "barium":     dict(t=(950, 1800),  soot=0.34, line=(0.55, 1.00, 0.24)),
    "lithium":    dict(t=(900, 1750),  soot=0.40, line=(1.00, 0.22, 0.62)),
    "boron":      dict(t=(950, 1900),  soot=0.28, line=(0.20, 1.00, 0.40)),
    "methane":    dict(t=(1100, 2200), soot=0.18, line=(0.28, 0.55, 1.00)),
    "sulfur":     dict(t=(900, 1600),  soot=0.30, line=(0.42, 0.52, 1.00)),
    "plasma":     dict(t=(1600, 3400), soot=0.06, line=(0.72, 0.42, 1.00)),
    "quench":     dict(t=(800, 1600),  soot=0.70, line=(0.30, 0.85, 0.95)),
}


def cell_mean(field, lab):
    """Average a field WITHIN each label — the piece that turns a per-pixel
    decision into a coherent 8-24px material patch.

    Spec Guide v1 §8 is explicit: "then organize choices into coherent 8-24px
    cells, not per-pixel noise". Without this the heat varies pixel to pixel, so
    the band map hands neighbouring pixels different material cards and the
    whole canvas reads as confetti — which is exactly what the first contact
    sheet of this rebuild looked like, gates green and all.
    """
    l = np.asarray(lab, np.int64).ravel()
    f = np.asarray(field, np.float32).ravel()
    # Densify sparse label spaces before counting. A hashed lattice can carry
    # label values in the hundreds of millions while holding only a few thousand
    # distinct cells, and bincount sizes its output by the MAXIMUM label, not by
    # the count — which turned a 0.1s call into 20+ seconds.
    if int(l.max(initial=0)) > 4 * l.size:
        l = np.unique(l, return_inverse=True)[1]
    n = int(l.max(initial=0)) + 1
    tot = np.bincount(l, weights=f, minlength=n)
    cnt = np.bincount(l, minlength=n).astype(np.float32)
    return (tot / np.maximum(cnt, 1.0)).astype(np.float32)[l].reshape(np.asarray(field).shape)


def emit(heat, fuel="wood", tiers=8, cells=None, jitter=0.10, line_at=0.72,
         line_amt=0.85, seed=7, mix_fuel=None, mix_frac=0.28, tint=0.16,
         substrate=None, sub_at=0.30):
    """Heat field (0..1) -> RGB paint through a fuel's real emission ladder.

    `cells` is an optional integer label field; when supplied, the tier is
    chosen PER CELL so the shades land as coherent 8-24px material patches
    rather than per-pixel confetti (Spec Guide v1 §8: vary the ratio of complete
    states, not a smear). `line_at` is where the chemiluminescent reaction front
    starts winning over thermal emission."""
    f = FUELS.get(fuel, FUELS["wood"])
    lad = thermal_ladder(f["t"][0], f["t"][1], tiers)
    h = np.clip(np.asarray(heat, np.float32), 0.0, 1.0)

    if cells is not None:
        # ONE tier per cell, taken at the cell's OWN mean heat. Reading the
        # pixel's heat here (what this did first) scatters neighbouring pixels
        # across the whole ladder and the card reads as speckle.
        hcell = cell_mean(h, cells)
        idx = np.clip((hcell * (tiers - 1) + 0.5).astype(np.int32), 0, tiers - 1)
    else:
        idx = np.clip((h * (tiers - 1) + 0.5).astype(np.int32), 0, tiers - 1)
    rgb = lad[idx]

    if jitter > 0:
        j = (_h1(np.asarray(cells, np.int64), 57 + seed) if cells is not None
             else _value_noise(h.shape, 256, seed + 3))
        rgb = rgb * (1.0 - jitter + 2.0 * jitter * j[..., None])

    # soot: unburnt carbon kills the cool end (this is what makes wood fire read
    # as fire and not as a glowing gradient)
    s = float(f["soot"])
    if s > 0:
        dark = np.clip((line_at - h) / max(line_at, 1e-6), 0.0, 1.0) ** 1.4
        rgb = rgb * (1.0 - s * dark)[..., None]

    if f["line"] is not None and line_amt > 0:
        w = np.clip((h - line_at) / max(1.0 - line_at, 1e-6), 0.0, 1.0) ** 0.8
        ln = np.asarray(f["line"], np.float32)[None, None, :]
        rgb = rgb * (1.0 - (w * line_amt)[..., None]) + ln * (w * line_amt)[..., None]

    # ── MIXED FUEL BED ──────────────────────────────────────────────────────
    # A real fire is never one chemistry: a copper nail in a bonfire genuinely
    # burns green, driftwood burns lilac from sea salt, treated timber throws
    # its own colours. A minority of CELLS therefore burn a second fuel. This is
    # also what answers the owner's standing note — "more shades, more colour
    # variation" — without inventing a colour that combustion can't make.
    if mix_fuel and cells is not None and mix_frac > 0:
        # Heavy soot (char at 0.85) blacks out the host's own colour, so a card
        # built on it needs a bigger doped population to carry any hue at all.
        if s > 0.55:
            mix_frac = min(0.52, float(mix_frac) * (1.0 + (s - 0.55) * 2.4))
        g = FUELS.get(mix_fuel)
        if g is not None:
            # REGIONS, not random cells. A fire bed is chemically zoned — a
            # length of treated timber here, salt-soaked driftwood there — so
            # the doped population arrives in coherent 60-200px patches that a
            # cell either falls inside or does not. Scattering it per cell put
            # two chemistries in adjacent 10px cells, which is the confetti the
            # owner explicitly rejects; region mixing carries the same chroma
            # spread and reads as material.
            reg = fbm(h.shape, seed + 311, octaves=(14, 28, 56, 112),
                      weights=(1.0, 0.8, 0.5, 0.3))
            reg = cell_mean(reg, np.asarray(cells, np.int64))
            thr = float(np.percentile(reg, 100.0 * (1.0 - float(mix_frac))))
            sel = reg > thr
            lad2 = thermal_ladder(g["t"][0], g["t"][1], tiers)
            alt = lad2[idx]
            if g["line"] is not None:
                # A salt-doped cell emits its line as soon as the salt
                # vaporises, which is well BELOW peak flame temperature — so the
                # doped population takes over much lower than the host fuel's
                # own line threshold. Without this the second chemistry only
                # showed in the few hottest pixels and the card still read as
                # one hue (measured: 2 hue bins).
                # A doped region emits its line wherever it is burning AT ALL,
                # not only in the hot tail. Tying the threshold to the host's
                # line_at meant that on a card whose field is mostly cool — a
                # sparse dendrite bed, say — the doped cells were cool too, so
                # they came out the same red as the host and contributed 0.7%
                # of the canvas instead of the 34% they were allocated.
                at2 = 0.16
                w2 = np.clip((h - at2) / max(1.0 - at2, 1e-6), 0.0, 1.0) ** 0.65
                ln2 = np.asarray(g["line"], np.float32)[None, None, :]
                amt2 = min(0.97, float(line_amt) * 1.12)
                alt = alt * (1.0 - (w2 * amt2)[..., None]) + ln2 * (w2 * amt2)[..., None]
            s2 = float(g["soot"])
            if s2 > 0:
                d2 = np.clip((line_at - h) / max(line_at, 1e-6), 0.0, 1.0) ** 1.4
                alt = alt * (1.0 - s2 * d2)[..., None]
            rgb = np.where(sel[..., None], alt, rgb)

    # ── THE UNBURNT SUBSTRATE ───────────────────────────────────────────────
    # Fire happens ON something, and that something has its own colour until the
    # heat reaches it — green wood, blue-painted steel, rust, firebrick. Giving
    # the coldest tiers the substrate colour is both physically honest and the
    # single biggest source of chroma range in a card, because a blackbody
    # ladder is one hue family by construction.
    if substrate is not None:
        sub = np.asarray(substrate, np.float32)[None, None, :]
        cold = np.clip((sub_at - h) / max(sub_at, 1e-6), 0.0, 1.0) ** 1.8
        if cells is not None:
            cold = cold * (0.55 + 0.50 * _h1(np.asarray(cells, np.int64), 199 + seed))
        rgb = rgb * (1.0 - cold[..., None]) + sub * cold[..., None]

    # ── per-cell TINT ───────────────────────────────────────────────────────
    # Independent of brightness (owner Rule 2 asks for both): each cell leans a
    # little warm or cool so a field of one fuel still carries chroma spread.
    if tint > 0 and cells is not None and cv2 is not None:
        lab = np.asarray(cells, np.int64)
        hsv = cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
        hsv[..., 0] = np.mod(hsv[..., 0] + (_h1(lab, 97 + seed) - 0.5) * 2.0 * float(tint) * 38.0, 360.0)
        hsv[..., 1] = np.clip(hsv[..., 1] * (0.90 + 0.22 * _h1(lab, 149 + seed)), 0.0, 1.0)
        rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    return np.clip(rgb, 0.0, 1.0).astype(np.float32)


# ════════════════════════════════════════════════════════════════════════════
# 2. FIELD PRIMITIVES — all tuned to the car-visible 8-32px window
# ════════════════════════════════════════════════════════════════════════════

def rng(seed):
    return np.random.default_rng(int(seed) & 0x7FFFFFFF)


def _h1(lab, salt):
    """Deterministic 0..1 hash of an integer label field."""
    v = (np.asarray(lab, np.int64) * np.int64(2654435761) + np.int64(salt) * np.int64(40503))
    v = (v ^ (v >> 13)) * np.int64(1274126177)
    return ((v ^ (v >> 16)) & np.int64(0xFFFFFF)).astype(np.float32) / float(0xFFFFFF)


def _value_noise(shape, freq, seed):
    """One octave of smooth value noise at `freq` cells across the canvas."""
    h, w = shape[0], shape[1]
    g = rng(seed).random((int(freq) + 1, int(freq) + 1)).astype(np.float32)
    if cv2 is None:
        return np.resize(g, (h, w))
    return cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)


def fbm(shape, seed, octaves=(8, 16, 32, 64, 128, 256, 512), gain=0.55, weights=None):
    """Multi-octave value noise. The default octave stack runs all the way to
    512 because the owner's law is fine detail: an octave of 8 is macro
    structure only, and something must ride on top of it."""
    h, w = shape[0], shape[1]
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for i, f in enumerate(octaves):
        a = amp if weights is None else float(weights[i])
        out += a * _value_noise((h, w), f, seed + i * 977)
        tot += a
        amp *= gain
    out /= max(tot, 1e-6)
    return n01(out)


def n01(a):
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / (hi - lo) if hi > lo else np.zeros_like(a)


def pct(a, lo=1.0, hi=99.0):
    """Percentile stretch — far more reliable than min/max when a field has a
    couple of extreme pixels (which every advection scheme produces)."""
    a = np.asarray(a, np.float32)
    p0, p1 = np.percentile(a, lo), np.percentile(a, hi)
    return np.clip((a - p0) / max(p1 - p0, 1e-6), 0.0, 1.0).astype(np.float32)


def curl(shape, seed, scale=64, steps=18, step_px=2.2, seed_field=None, decay=0.0):
    """Advect a scalar along a divergence-free (curl) noise field.

    This is the honest way to get turbulent flame structure: the streamlines
    never cross and never pool, so you get the wispy filament texture of real
    combustion instead of smeared blobs."""
    h, w = shape[0], shape[1]
    pot = fbm((h, w), seed, octaves=(scale // 8 or 1, scale // 4 or 2, scale, scale * 2))
    gy, gx = np.gradient(pot.astype(np.float32))
    vx, vy = gy, -gx                                         # curl of a scalar potential
    nrm = np.hypot(vx, vy) + 1e-6
    vx, vy = vx / nrm, vy / nrm

    # The source must already be FINE — advection can only move detail around,
    # it cannot create it, and averaging along a streamline destroys it. Octaves
    # run to 512 so the carried grain is 2-4px at GEN.
    src = fbm((h, w), seed + 31, octaves=(32, 64, 128, 256, 512),
              weights=(0.55, 0.75, 1.0, 0.9, 0.7)) if seed_field is None \
        else np.asarray(seed_field, np.float32)
    # Integrate the streamlines at HALF resolution. The velocity field is smooth
    # by construction (it is the curl of a band-limited potential), so the
    # trajectory is identical to within a pixel — but the loop runs 30 times
    # over 4x fewer points, which is what took the curl-heavy cards from 4.4s to
    # inside the 3s budget. The final SAMPLE is still at full resolution, so no
    # grain is lost.
    hh, ww = max(256, h // 2), max(256, w // 2)
    sc = float(w) / ww
    vxs = cv2.resize(vx, (ww, hh), interpolation=cv2.INTER_LINEAR) if cv2 is not None else vx
    vys = cv2.resize(vy, (ww, hh), interpolation=cv2.INTER_LINEAR) if cv2 is not None else vy
    ys, xs = np.mgrid[0:hh, 0:ww].astype(np.float32)
    px, py = xs.copy(), ys.copy()
    st = float(step_px) / sc
    for _i in range(int(steps)):
        ix = np.clip(px.astype(np.int32), 0, ww - 1)
        iy = np.clip(py.astype(np.int32), 0, hh - 1)
        px = (px + vxs[iy, ix] * st) % ww
        py = (py + vys[iy, ix] * st) % hh
    if cv2 is not None and (hh != h or ww != w):
        px = cv2.resize(px * sc, (w, h), interpolation=cv2.INTER_LINEAR)
        py = cv2.resize(py * sc, (w, h), interpolation=cv2.INTER_LINEAR)
    # SAMPLE at the end of the streamline (a smear of every step in between is
    # what turned the old flame fields into soft macro wallpaper); then beat it
    # against an unadvected fine octave so the grain stays crisp.
    warped = src[py.astype(np.int32) % h, px.astype(np.int32) % w]
    grain = fbm((h, w), seed + 91, octaves=(128, 256, 512), weights=(0.6, 1.0, 0.8))
    acc = warped * (1.0 - float(decay)) + warped * grain * (0.55 + float(decay))
    return pct(acc)


def worley(shape, seed, cells=90, kind="f2f1", jitter=1.0):
    """Cellular / Worley distance field — the backbone for flame cells, ember
    lattices and quench crack networks. `cells` counts ACROSS the canvas, so
    cells=90 on 1024 is an ~11px cell: inside the owner's 8-32px window.

    Solved by the 3x3 NEIGHBOUR-CELL method: each feature point is jittered
    inside its own lattice cell, so a pixel's two nearest points can only live
    in its own cell or the eight around it. That is 9 vectorised distance
    evaluations per pixel *regardless of cell count* — the naive
    every-point-against-every-pixel loop this replaced took 49s at cells=90 and
    349s inside anneal_crack, which would have blown the 3s render budget on
    its own."""
    h, w = shape[0], shape[1]
    n = int(max(2, cells))
    r = rng(seed)
    jx = (r.random((n, n)).astype(np.float32) - 0.5) * float(jitter)
    jy = (r.random((n, n)).astype(np.float32) - 0.5) * float(jitter)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cw, ch = w / float(n), h / float(n)
    ci = np.clip((xx / cw).astype(np.int32), 0, n - 1)
    cj = np.clip((yy / ch).astype(np.int32), 0, n - 1)

    d1 = np.full((h, w), np.float32(1e18))
    d2 = np.full((h, w), np.float32(1e18))
    lab = np.zeros((h, w), np.int32)
    # Scratch buffers reused across all 9 offsets — this loop runs on 4M pixels
    # at 2048 and fresh allocations were most of its cost.
    d = np.empty((h, w), np.float32)
    tmp = np.empty((h, w), np.float32)
    nid = np.empty((h, w), np.int32)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            ni = (ci + di) % n
            nj = (cj + dj) % n
            np.subtract(xx, (ni.astype(np.float32) + 0.5 + jx[nj, ni]) * cw + (ci + di - ni) * cw, out=d)
            np.multiply(d, d, out=d)
            np.subtract(yy, (nj.astype(np.float32) + 0.5 + jy[nj, ni]) * ch + (cj + dj - nj) * ch, out=tmp)
            np.multiply(tmp, tmp, out=tmp)
            np.add(d, tmp, out=d)
            closer = d < d1
            np.minimum(d2, d, out=d2)                # d2 <- min(d2, d)
            np.copyto(d2, d1, where=closer)          # ...then old d1 if d displaced it
            np.multiply(nj, n, out=nid, casting="unsafe")
            np.add(nid, ni, out=nid, casting="unsafe")
            np.copyto(lab, nid, where=closer)
            np.copyto(d1, d, where=closer)
    np.sqrt(d1, out=d1)
    np.sqrt(d2, out=d2)
    out = (d2 - d1) if kind == "f2f1" else (d1 if kind == "f1" else d2)
    return pct(out), lab.astype(np.int64)


def wrinkle(shape, seed, k=0.9, steps=14, scale=180):
    """Michelson-Sivashinsky flame-front wrinkling: a front that is unstable to
    its own curvature, so it grows CUSPS at a preferred scale.

    The signal is the cusp field |grad u|, NOT u itself. u is a smooth potential
    whose energy sits at the macro end; its slope discontinuities are the actual
    flame creases, and they land exactly in the 8-32px window. (Reading u
    directly is what made the old `curl_streamers`/`tongues` score band 0.017.)
    """
    h, w = shape[0], shape[1]
    u = (fbm((h, w), seed, octaves=(scale // 4 or 1, scale // 2 or 2, scale, scale * 2),
             weights=(0.4, 0.7, 1.0, 0.8)) - 0.5).astype(np.float32)
    for _ in range(int(steps)):
        lap = (np.roll(u, 1, 0) + np.roll(u, -1, 0) + np.roll(u, 1, 1) + np.roll(u, -1, 1) - 4 * u)
        gy, gx = np.gradient(u)
        u = u + 0.16 * lap - 0.05 * (gx * gx + gy * gy) * float(k)
        u -= u.mean()
        m = np.abs(u).max()
        if m > 4.0:
            u /= m
    gy, gx = np.gradient(u)
    cusp = np.hypot(gx, gy)
    # NOTE on `steps`: fewer is BOTH faster and finer. Measured at 1024 —
    # 26 steps: 0.82s / car-band 0.589;  14 steps: ~0.45s / 0.66. The extra
    # diffusion was only smoothing away the cusps this primitive exists to
    # make. Do not "improve" it by running the PDE longer.
    return pct(cusp ** 0.6)


def eden(shape, seed, seeds=900, steps=14, aniso=(1.0, 1.0)):
    """Eden / KPZ cluster growth — a burn front eating outward from many ignition
    points. The interface is rough at every scale, which is exactly what a real
    char edge looks like."""
    h, w = shape[0], shape[1]
    r = rng(seed)
    # Grow at FULL resolution. Solving small and upscaling (what this did first)
    # smooths the interface away, and the rough interface IS the whole point of
    # Eden growth — it scored band 0.015 that way.
    occ = np.zeros((h, w), np.float32)
    occ[r.integers(0, h, int(seeds)), r.integers(0, w, int(seeds))] = 1.0
    age = occ.copy()
    kx = max(1, int(round(3 * aniso[0])))
    ky = max(1, int(round(3 * aniso[1])))
    ker = np.ones((ky, kx), np.float32)
    for i in range(int(steps)):
        if cv2 is None:
            break
        grow = cv2.dilate(occ, ker)
        noise = r.random((h, w)).astype(np.float32)
        newly = ((grow > 0) & (occ == 0) & (noise < 0.55)).astype(np.float32)
        occ = np.clip(occ + newly, 0, 1)
        age += newly * (1.0 - i / float(steps))
    # the ragged BURN LINE carries the fine energy; age alone is a soft ramp
    if cv2 is not None:
        edge = np.abs(occ - cv2.GaussianBlur(occ, (0, 0), 1.4))
        age = age * 0.55 + pct(edge) * 0.95
    return pct(age)


def sparks(shape, seed, n=1600, life=44, g=0.55, drag=0.06, spread=1.5, width=0.9):
    """Ballistic ember tracks: launch, gravity, air drag, and a cooling tail.
    Tracks are 1-3px wide and 8-40px long, so a whole car reads as a storm of
    embers rather than as a few big streaks."""
    h, w = shape[0], shape[1]
    out = np.zeros((h, w), np.float32)
    r = rng(seed)
    x = r.random(n) * w
    y = r.random(n) * h
    a = r.random(n) * _TAU
    sp = (0.6 + 1.4 * r.random(n)) * spread
    vx, vy = np.cos(a) * sp, np.sin(a) * sp
    heat = 0.55 + 0.45 * r.random(n)
    for i in range(int(life)):
        vy += g * 0.02
        vx *= (1.0 - drag * 0.1)
        vy *= (1.0 - drag * 0.1)
        x = (x + vx) % w
        y = (y + vy) % h
        heat *= 0.975
        xi, yi = x.astype(np.int32), y.astype(np.int32)
        np.add.at(out, (yi, xi), heat)
    if cv2 is not None and width > 0:
        out = cv2.GaussianBlur(out, (0, 0), float(width))
    return pct(out)


def dla(shape, seed, seeds=520, walkers=14000, steps=42):
    """Diffusion-limited aggregation — soot inception. Fractal carbon dendrites
    that branch at every scale; nothing else looks like real soot."""
    h, w = shape[0], shape[1]
    ss = max(1, min(h, w) // 768)
    hs, ws = h // ss, w // ss
    r = rng(seed)
    occ = np.zeros((hs, ws), np.float32)
    occ[r.integers(0, hs, int(seeds)), r.integers(0, ws, int(seeds))] = 1.0
    px = r.integers(0, ws, int(walkers)).astype(np.int32)
    py = r.integers(0, hs, int(walkers)).astype(np.int32)
    for _ in range(int(steps)):
        px = (px + r.integers(-1, 2, px.size)) % ws
        py = (py + r.integers(-1, 2, py.size)) % hs
        near = (occ[(py - 1) % hs, px] + occ[(py + 1) % hs, px]
                + occ[py, (px - 1) % ws] + occ[py, (px + 1) % ws]) > 0
        if near.any():
            occ[py[near], px[near]] = 1.0
            keep = ~near
            px, py = px[keep], py[keep]
            if px.size == 0:
                break
    if cv2 is not None:
        occ = cv2.GaussianBlur(occ, (0, 0), 0.55)
        if ss > 1:
            occ = cv2.resize(occ, (w, h), interpolation=cv2.INTER_LINEAR)
        # Real soot is not binary: density falls off around every aggregate, so
        # the field needs intermediate levels. Bare occupancy gave a card only
        # 4-6 distinct shades because almost every pixel was 0 or 1.
        halo = cv2.GaussianBlur(occ, (0, 0), max(1.2, min(h, w) / 620.0))
        occ = occ * 0.72 + pct(halo) * 0.40
    return pct(occ)


def filaments(shape, seed, n=280, length=46, wander=0.30, width=1.3):
    """Thin reaction sheets — where fuel meets oxidiser in a diffusion flame the
    burn is a SURFACE, not a volume. Fine, curving, non-crossing ribbons."""
    h, w = shape[0], shape[1]
    out = np.zeros((h, w), np.float32)
    r = rng(seed)
    flow = fbm((h, w), seed + 17, octaves=(8, 16, 32, 64))
    gy, gx = np.gradient(flow)
    for _ in range(int(n)):
        x, y = r.random() * w, r.random() * h
        ang = r.random() * _TAU
        amp = 0.55 + 0.45 * r.random()
        for _s in range(int(length)):
            xi, yi = int(x) % w, int(y) % h
            ang += wander * (gx[yi, xi] * np.sin(ang) - gy[yi, xi] * np.cos(ang)) * 6.0
            x = (x + np.cos(ang) * 1.7) % w
            y = (y + np.sin(ang) * 1.7) % h
            out[int(y) % h, int(x) % w] += amp
    if cv2 is not None:
        out = cv2.GaussianBlur(out, (0, 0), float(width))
    return pct(out)


def percolate(shape, seed, cells=170, p=0.42, rounds=3):
    """Site percolation on a cell lattice, then relaxed — an ember bed where the
    burn has connected through some clusters and died in others."""
    d, lab = worley(shape, seed, cells=cells)
    lit = (_h1(lab, 11) < float(p)).astype(np.float32)
    for _ in range(int(rounds)):
        if cv2 is None:
            break
        sm = cv2.GaussianBlur(lit, (0, 0), 1.1)
        lit = (sm > 0.48).astype(np.float32)
    # An ember does not glow uniformly: it is hottest at the cell core and dark
    # at the seam. Modulating by the cell's own distance field keeps the fine
    # boundary energy that a plain blur (sigma 2.2) was erasing.
    core = np.clip(1.0 - d * 1.35, 0.0, 1.0)
    heat = lit * (0.42 + 0.58 * core) + (1.0 - lit) * core * 0.16
    if cv2 is not None:
        heat = cv2.GaussianBlur(heat, (0, 0), 0.7)
    return pct(heat), lab


def rt_fingers(shape, seed, n=110, gain=1.5, stalks=1.0):
    """Rayleigh-Taylor fingering: hot gas punching up through cold.

    The plume anatomy is the INTERFACE between the rising and falling phases,
    so the returned field is the interface sharpness, not the smooth phase ramp
    (which scored band 0.008). Many small fingers, never one macro mushroom."""
    h, w = shape[0], shape[1]
    base = fbm((h, w), seed, octaves=(n // 4 or 1, n // 2 or 2, n, n * 2, n * 4),
               weights=(0.35, 0.6, 1.0, 0.85, 0.6))
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    phase = np.clip(yy + (base - 0.5) * gain * 0.35, 0, 1)
    # finger walls: where the phase boundary is steep across x
    gy, gx = np.gradient(phase.astype(np.float32))
    wall = pct(np.abs(gx) ** 0.55)
    spine = fbm((h, w), seed + 41, octaves=(n, n * 2, n * 4), weights=(0.7, 1.0, 0.8))
    return pct(wall * (0.55 + 0.75 * float(stalks)) + spine * 0.45 * (1.0 - phase))


def kh_braid(shape, seed, layers=96, shear=3.2):
    """Kelvin-Helmholtz braids at a shear layer — the rolled-up billows on the
    edge of every jet flame. `layers` counts braids across the canvas, so 96 on
    1024 is a ~10px braid: many small rolls, never one big one."""
    h, w = shape[0], shape[1]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ph = fbm((h, w), seed, octaves=(24, 48, 96, 192), weights=(0.4, 0.7, 1.0, 0.7))
    k = _TAU * layers / float(h)
    roll = np.sin(k * yy + shear * np.sin(_TAU * xx / float(w) * layers * 0.5 + ph * _TAU))
    fine = fbm((h, w), seed + 5, octaves=(128, 256, 512), weights=(0.6, 1.0, 0.75))
    # SIGNED, not rectified. Folding the sine through abs() doubled the spatial
    # frequency but spiked the histogram at both ends, which halved the
    # car-band energy (0.87 -> 0.42) AND left the spec's percentile bands
    # landing inside flat plateaus, so the material map stopped following the
    # design. Measured both ways; signed wins on both counts.
    return pct((0.5 + 0.5 * roll) * 0.75 + fine * 0.45)


def anneal_crack(shape, seed, cells=64, width=2.4, gen=2):
    """Quench / craze crack network: cool a hot skin fast and it cracks along
    cell boundaries, then sub-cracks appear inside the biggest fragments."""
    h, w = shape[0], shape[1]
    d, lab = worley(shape, seed, cells=cells, kind="f2f1")
    crack = np.exp(-(d * float(cells) / 12.0) ** 2 / max(width, 0.2))
    # Sub-generations solve at HALF resolution and upscale. They are finer cell
    # networks weighted 0.62^g, so the 2x softening is invisible, and it takes
    # this primitive from 1.9s to 0.8s at 1024 — the difference between Quench
    # Craze making the 3s budget and blowing it.
    hs = max(384, h // 2), max(384, w // 2)
    for g in range(1, int(gen) + 1):
        c2 = cells * (g + 1)
        d2, _l2 = worley(hs, seed + 700 * g, cells=max(4, int(c2 * hs[0] / float(h))))
        sub = np.exp(-(d2 * c2 * hs[0] / float(h) / 12.0) ** 2 / max(width, 0.2)) * (0.62 ** g)
        if cv2 is not None and hs[0] != h:
            sub = cv2.resize(sub.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        crack = np.maximum(crack, sub)
    # The plates are not featureless: each carries its own distance gradient, so
    # the field has a usable histogram instead of a spike at zero. Without this
    # the spec's percentile bands cut arbitrarily through one flat plate.
    # Plates also sit at DIFFERENT levels. A quenched surface does not cool
    # evenly — each fragment holds its own temperature — and without that
    # between-plate spread every cell averages to the same value, so the spec's
    # per-cell band assignment becomes a coin toss (Quench Craze traced 0.214).
    level = _h1(lab, 5) * 0.42
    return pct(crack * 0.74 + (1.0 - d) * 0.26 + level), lab


def spall(shape, seed, cells=78, lift=0.55):
    """Oxide scale lifting off hot steel: plates that curl at their edges, so
    each plate has a bright rim and a dark shadowed side."""
    d, lab = worley(shape, seed, cells=cells, kind="f1")
    tilt = _h1(lab, 23) * _TAU
    gy, gx = np.gradient(d.astype(np.float32))
    shade = np.cos(tilt) * gx + np.sin(tilt) * gy
    return pct(d * (1.0 - lift) + n01(shade) * lift), lab


# ════════════════════════════════════════════════════════════════════════════
# 3. THE SPEC — Spec Guide v1 §7-§9, made causal
# ════════════════════════════════════════════════════════════════════════════
#
# Complete material CARDS (M / Rough / Cc). Never interpolated into each other:
# a pixel gets ONE card, chosen per coherent cell, exactly as §8 prescribes.
CARDS = {
    # dielectric rest states
    "flat":      (0, 220, 210),      # clear-matte rest  (F0)
    "porous":    (8, 238, 226),      # burnt-out, dead   (F1)
    "ash":       (0, 246, 240),      # powder, no coat
    "soot":      (12, 250, 250),     # unburnt carbon: the deadest thing here
    # coated / glossy
    "gloss":     (0, 30, 16),        # high-gloss island (G0)
    "wet":       (0, 18, 16),        # wet lip / fresh melt (G1)
    "glaze":     (0, 46, 22),        # vitrified skin
    "satin":     (0, 96, 60),
    # metal
    "steel":     (196, 62, 40),
    "scale":     (168, 128, 96),     # oxide scale on hot metal
    "bronze":    (214, 54, 34),
    "hotedge":   (250, 15, 40),      # dark-chrome hot edge (E0)
    "spark":     (255, 2, 16),       # mirror spark (E1)
    "razor":     (40, 16, 16),       # white clearcoat razor (W0)
    # fractured carriers (the night-flip population)
    "carrier0":  (242, 78, 246),
    "carrier1":  (248, 46, 250),
    "carrier2":  (255, 22, 255),
}


def _dilate(a, px):
    if cv2 is None or px <= 0:
        return a
    k = int(max(1, round(px)))
    return cv2.dilate(a.astype(np.float32), np.ones((k, k), np.float32))


def flame_spec(heat, cells, recipe, res, seed=7):
    """Build the spec map from the SAME field that made the paint.

    Causality (Spec Guide v1 §7): a pixel's material is decided by what the fire
    DID there — the reaction front is a polished hot edge, the burnt-out cool
    zone is porous and coat-free, the vitrified mid-band is glazed, and soot is
    the deadest state in the catalog. Channels are not clones of each other: the
    clearcoat field is deliberately OFFSET from the metal/roughness field (§8)
    so the two lobes peak at different view angles.
    """
    h = np.clip(np.asarray(heat, np.float32), 0.0, 1.0)
    lab = np.asarray(cells, np.int64) if cells is not None else None
    H, W = h.shape[:2]

    bands = recipe.get("bands", (("soot", 0.14), ("porous", 0.34), ("flat", 0.56),
                                 ("glaze", 0.74), ("gloss", 0.88), ("wet", 1.01)))

    # per-CELL heat so a whole cell takes one card (no per-pixel confetti)
    hc = h
    if lab is not None:
        # The material card is chosen for the CELL, from the cell's own mean
        # heat. Blurring the pixel field (what this did first) leaves a
        # continuous surface, so the band edges cut through the middle of
        # plates and the spec map came out as noise rather than as material.
        hc = cell_mean(h, lab)
        hc = np.clip(hc + (_h1(lab, 91 + seed) - 0.5) * float(recipe.get("cell_jit", 0.06)), 0, 1)

    # Band assignment by SEARCHSORTED + one fancy index, not one boolean mask
    # per band. At 2048 that is 6 passes over 4M pixels turned into 1.
    #
    # The edges are read as PERCENTILES of this card's own heat distribution,
    # not as absolute levels. Every card's field has a different histogram —
    # Weld Pool's heat piles up in one band, Ember Bed's spreads — and with
    # absolute edges the piled-up cards handed almost every pixel the same
    # material (measured: roughness std 14.3, clearcoat std 9.1, i.e. a
    # near-uniform spec). Percentile edges guarantee each card populates its
    # bands in the DESIGNED proportions, whatever its own field looks like.
    edges = np.asarray([u for _n, u in bands], np.float32)
    deck = np.asarray([CARDS[recipe.get("cards", {}).get(n, n)] for n, _u in bands], np.float32)
    qs = np.percentile(hc[::4, ::4], np.clip(edges * 100.0, 0.0, 100.0))
    qs = np.maximum.accumulate(np.asarray(qs, np.float32))
    bi = np.searchsorted(qs, hc.ravel(), side="left")
    np.clip(bi, 0, len(bands) - 1, out=bi)
    out = deck[bi].reshape(H, W, 3)

    # ---- the reaction front: a 2-6px dark-chrome lip on the steepest gradient
    if cv2 is not None:
        hs = max(512, H // 2)
        hh = cv2.resize(h, (hs, hs), interpolation=cv2.INTER_AREA) if hs != H else h
        gy, gx = np.gradient(cv2.GaussianBlur(hh, (0, 0), 1.2))
        grad = np.hypot(gx, gy)
        # percentiles on a strided subsample — identical to 3 decimal places on
        # a 4M-pixel field and ~16x cheaper
        gsub = grad[::4, ::4].ravel()
        thr = float(np.percentile(gsub, recipe.get("edge_pct", 97.0)))
        lip = (grad > thr).astype(np.float32)
        # A reaction front is THIN. On a periodic field (braids, ladders) the
        # percentile mask can claim a fifth of the canvas and bury the band map
        # underneath it — Laminar Ladder traced 0.235 that way. Raise the
        # threshold until the lip is at most `edge_max` of the surface.
        emax = float(recipe.get("edge_max", 0.075))
        for _q in (99.0, 99.4, 99.7):
            if lip.mean() <= emax:
                break
            lip = (grad > float(np.percentile(gsub, _q))).astype(np.float32)
        lip = _dilate(lip, max(2.0, res / 700.0 * hs / float(H)))
        if hs != H:
            lip = cv2.resize(lip, (W, H), interpolation=cv2.INTER_NEAREST)
        ename = recipe.get("edge", "hotedge")
        if ename:
            out[lip > 0] = np.asarray(CARDS[ename], np.float32)
        # the hottest corners only: mirror sparks, deliberately sparse
        sp = ((grad > float(np.percentile(gsub, 99.72))) & (hh > 0.72)).astype(np.float32)
        sp = _dilate(sp, max(1.0, res / 1400.0 * hs / float(H)))
        if hs != H:
            sp = cv2.resize(sp, (W, H), interpolation=cv2.INTER_NEAREST)
        out[sp > 0] = np.asarray(CARDS[recipe.get("spark", "spark")], np.float32)
        # white clearcoat razors on a DIFFERENT sparse subset (§9 step 5)
        if recipe.get("razor", 0.0) > 0 and lab is not None:
            rz = ((_h1(lab, 131 + seed) < float(recipe["razor"])) & (lip > 0)).astype(np.float32)
            out[rz > 0] = np.asarray(CARDS["razor"], np.float32)

    # ---- channel independence: shift the clearcoat structure off the M/R one
    off = int(recipe.get("cc_offset", max(3, res // 340)))
    if off:
        out[..., 2] = np.roll(np.roll(out[..., 2], off, axis=0), -off, axis=1)

    # ---- fine per-cell roughness spread so no card is one flat value
    if lab is not None:
        # The spread is a FRACTION of each card's own roughness, not an absolute
        # step. An absolute +/-13 was wider than the gap between neighbouring
        # cards — 'gloss' is 30 and 'wet' is 18 — so the two stopped being
        # distinguishable, on the metric AND on the car, and the band map the
        # spec was designed around dissolved. Proportional spread also happens
        # to be true: a rough surface varies far more than a polished one.
        frac = float(recipe.get("r_spread", 26.0)) / 255.0
        out[..., 1] = np.clip(out[..., 1] * (1.0 + (_h1(lab, 173 + seed) - 0.5) * 2.0 * frac), 0, 255)
        out[..., 0] = np.clip(out[..., 0] * (0.93 + 0.14 * _h1(lab, 211 + seed)), 0, 255)

    return iron_safe(out)


def iron_safe(spec):
    """The two legalisation rules from Spec Guide v1 §3: roughness floors at 15
    unless the pixel is chrome-tier (M >= 240), and an ACTIVE clearcoat may
    never land in the illegal 1..15 band."""
    s = np.asarray(spec, np.float32)
    mirror = s[..., 0] >= 240.0
    s[..., 1] = np.where(mirror, np.clip(s[..., 1], 0, 255), np.clip(s[..., 1], 15, 255))
    cc = s[..., 2]
    s[..., 2] = np.where((cc > 0) & (cc < 16), 16.0, cc)
    return np.clip(s, 0, 255).astype(np.uint8)


def upscale(a, res):
    """Fields generate at GEN and must be resized to the render size. Labels are
    integer and take NEAREST; everything else takes LINEAR."""
    a = np.asarray(a)
    if a.shape[0] == res:
        return a
    if cv2 is None:
        return a
    if a.dtype.kind in "iu":
        return cv2.resize(a.astype(np.float32), (res, res),
                          interpolation=cv2.INTER_NEAREST).astype(np.int64)
    return cv2.resize(a.astype(np.float32), (res, res), interpolation=cv2.INTER_LINEAR)
