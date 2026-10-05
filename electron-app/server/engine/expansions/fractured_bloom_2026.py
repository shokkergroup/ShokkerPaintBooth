# -*- coding: utf-8 -*-
"""FRACTURED BLOOM (2026-07-30) — category 3/10 of the FRACTURED expansion.

════════════════════════════════════════════════════════════════════════════
SPB-FRACTURED-FIELD 2026-08-02 — SECOND corrective pass (owner rejected the
2026-08-01 rebuild: "still VERY subpar... REALLY SIMILAR... repeated designs...
2048x2048 covers an ENTIRE car — things that look intricate are not as
intricate as you think.")
════════════════════════════════════════════════════════════════════════════
Diagnosis vs the flagship FRACTURED MINDS (house standard = a dense
HOMOGENEOUS MICRO-TEXTURE FIELD, thousands of 8-32px features at 2048):
MINDS car-band 0.82; this module's previous median 0.381 with minimums to
~0.05, plus repeated "one big form on dark ground" composition archetypes.

REBUILD LAW APPLIED (all hard):
  * FIELD, NOT POSTER — no feature > ~80px at 2048 unless repeated >= 25x.
    Every generator below is a canvas-filling MEADOW: dominant feature pitch
    5-15px at the 768 gen grid == 13-40px pitch at 2048, feature bodies
    8-32px at 2048.
  * CAR-BAND GATE (fail-closed): FFT ring r in [64,256] at 512 >= 0.45 per
    finish, module median >= 0.60. Macro composition survives only as GENTLE
    modulation (tight vd, low tmod) so low-frequency energy stays small.
  * ARCHETYPE LEDGER — all 20 ids carry DISTINCT compositional archetypes:

      fbl_magenta_whorl   rosette tier-pack (scalloped concentric ring whorls)
      fbl_leafvine_drape  woven trellis cross (two stem families + leaf knots)
      fbl_butter_pollen   echinate dust scatter (bimodal spiky grains + dust)
      fbl_pink_rose       directional lamina eddies (warp-combed petal sheets)
      fbl_coral_cluster   polyp foam pack (walled foam + mouth pores)
      fbl_butter_mosaic   plate-mosaic with floret stamps (grouted plates)
      fbl_pink_pollen     flow-smeared thread-drift (grains advected to trails)
      fbl_white_whorl     micro-billows (shaded cupped petal cushions)
      fbl_coral_stamen    needle felt (two crossed anther-tipped needle plies)
      fbl_lilac_rose      reaction-diffusion petal labyrinth
      fbl_coral_vine      branching stem mesh (3-scale ridge-crest venation)
      fbl_lilac_stamen    star-lattice sparks (near-regular ray bursts)
      fbl_magenta_mosaic  interlocking petal-cross cells (4-lobe cell pack)
      fbl_leaf_whorl      chevron pleats (herringbone pinnate leaflets)
      fbl_white_pollen    clumped structured dust (density-gated grain packs)
      fbl_pink_stamen     comb-fringe rows (banded filament combs + beads)
      fbl_blush_rose      scale imbrication (shingled fan-ribbed petals)
      fbl_lilac_vine      hanging bead-strand curtain (swaying racemes)
      fbl_butter_whorl    pinwheel curl pave (tiny log-spiral whorls)
      fbl_magenta_pollen  porate close-pack grains (reticulate + germ pores)

  * PALETTES — 3-4 distinct hue anchors per id (luminous, not muddy) picked
    per FEATURE via the hue_cell Ddom refinement below, plus the 8-tier
    per-feature brightness law (_TIERS).
  * CONTRACT UNCHANGED — same 20 ids, same GROUPS key, same
    install_into_engine(mono_reg, base_reg=None) -> (spec_fn, paint_fn).
    Spec traces paint (CategoryKit carves from the same cached art).
    Work grid 1024 (kit work=1024, generators at 640). Determinism:
    per-finish seed = zlib.crc32(fid.encode()) — np.random.default_rng only,
    no hash(str) anywhere. h2 salts are kept < 8k (seed % 7919): float32
    precision destroys the sin-hash above ~1e6.

Verify artifacts: _fractured_triage/refield_bloom.jsonl (per-finish verdicts)
and _fractured_triage/resheet_bloom.png (5x4 labeled contact sheet).
[SPB-FRACTURED-090b 2026-08-02] THIRD pass — owner: "push the others to the
same levels ... WITHOUT it being static noise or just a bunch of repeats."
Car-band MEDIAN (FFT ring r 64..256 of the 512 paint over total r>=2, the
FRACTURED MINDS house standard = 0.82): 0.672 -> 0.866, per-finish
minimum 0.701, and all 20 ids now clear the four ANTI-STATIC guards that
make a high band mean "dense coherent micro-structure" instead of noise
(white noise measures ~0.95 on the ring and is a FAILURE at any score):
lag-1 neighbour coherence >= 0.55, spectral peakiness >= 0.32, connected
shape fraction >= 0.55, fineness > 6.5 — plus coverage 64/64, hue bins >= 5,
descriptor pair-cosine 0.45 (<= 0.55), 1.5 s at 512 / 1.9 s at
2048. The gain is STRUCTURAL, not grain: see THE IN-BAND FIELD LAW below for
the four measured laws (relief not tint, fat seams, bounded jitter, no fbm in
the luma) and the PER-FINISH FIELD TUNE block under the recipes for the
transfer dials (span / mid / lowcut / soft) the LUT forced on top of them.
The 20 archetypes in the ledger above are UNCHANGED — one composition per id.


[SPB-FRACTURED-090c 2026-08-02] COLOUR-IDENTITY pass (parent visual review:
"the geometry is excellent and independently confirmed — keep all of it; this
is a colour fix only"). Every band / coherence / peakiness / shape number is
unchanged, because all of it is luma-neutral: the hero-hue window re-applies
each pixel's own luma. What moved:
  * MEASURED hue, not eyeballed. The thin-film LUT's hue distribution inside a
    hero window is asymmetric, so the anchor a recipe SETS is not the hue it
    RENDERS. _fractured_triage/huefix.py measures the saturation-weighted
    CIRCULAR-MEAN hue of each finish's 512 paint against the hue its NAME
    claims; _HUEFIX is the damped per-id correction. All 20 ids land within
    0.03 of a turn (worst 0.012).
  * The pale families got their own CHROMA. "White" and "butter" are defined
    by LOW chroma, not by hue: fbl_white_pollen was rendering CYAN (mean
    hue 0.553) and the butter ids were rendering ORANGE at chroma 0.99.
    Flowers keep their saturation — that part was right.
"""
from __future__ import annotations

import zlib

import cv2
import numpy as np

from engine.expansions import fractured_catlib_2026 as catlib
from engine.expansions import fractured_wilds_microkit_2026 as wildkit
from engine.expansions.fractured_catlib_2026 import (
    coords, fbm, frac, gauss, h2, n01, rng, sstep, warp_pair,
)

_TAU = 6.283185307179586
_S = 768.0            # generator px-space anchor (pitch is res/_S scaled)            # generator px-space anchor (kit gen=768)

# owner doctrine: 8-tier per-feature brightness palette — never 1-2 levels.
_TIERS = np.array([0.16, 0.27, 0.38, 0.49, 0.60, 0.70, 0.81, 0.93], np.float32)


def _tier(hv):
    return _TIERS[np.clip((np.asarray(hv, np.float32) * 8.0).astype(np.int32), 0, 7)]


def _sd(seed):
    """Small deterministic h2 salt from the crc32 finish seed (float32-safe)."""
    return int(seed) % 7919


def _bump(t2):
    """Compact smooth bump ~= exp(-t2), 3 cheap array ops (perf doctrine)."""
    return np.clip(1.0 - np.asarray(t2, np.float32) * 0.45, 0.0, 1.0) ** 2


# ════════════════════════════════════════════════════════════════════════════
# THE IN-BAND FIELD LAW  [SPB-FRACTURED-090b 2026-08-02] — owner: "push the
# others to the same levels ... WITHOUT it being static noise or just a bunch
# of repeats." Measured frequency budget of the 512 paint (FFT power of luma,
# ring r in [64,256] over total r >= 2):
#
#     r =  64  <=> period 8.0 px at 512 <=> 10.0 px at GEN 640 <=> 32 px @2048
#     r = 256  <=> period 2.0 px at 512 <=>  2.5 px at GEN 640 <=>  8 px @2048
#
# and the anti-static guard (lag-1 horizontal autocorrelation >= 0.55, because
# white noise scores band ~0.95 and is a FAILURE) puts a CEILING on the same
# axis: an isotropic ring at radius r contributes J0(2*pi*r/512) to that
# autocorrelation — r=74 pays 0.80, r=128 pays 0.47, r=200 pays -0.03. So the
# whole field has to live in a 6-10 px window at GEN (== _P0 below), and the
# ONE shape that beats the trade is a TILTED stripe/lattice: its 2-D radius
# sits high in the band while its x-period stays long (high coherence).
#
# Four laws, none of which is "add noise":
#   L1 RELIEF, NOT TINT — value rides a SMOOTH PERIODIC relief inside each
#      cell (dome / rib / crown / bevel). A flat per-cell tint is a LOW-pass
#      field: its power sits under r=64 (a raw 8-tier pave measures band 0.15).
#   L2 FAT SEAMS — cells are separated by a WIDE smooth edge-distance seam.
#      Fat seams concentrate power at the lattice fundamental; hairlines smear
#      it into r>200 harmonics that buy no band and wreck coherence.
#   L3 BOUNDED JITTER — jitter <= ~0.5 cell keeps a preferred period, i.e. a
#      sharp spectral fundamental (the peakiness guard). Free worley smears it.
#   L4 NO fbm IN THE LUMA — an fbm pyramid is 1/f: most of its power lands
#      UNDER the band. Every fbm-derived luma term (fine grain, tiers,
#      turbulence, ridged veins, clump envelopes, wobbles) is replaced by an
#      in-band lattice equivalent. fbm survives only as a domain-warp or a
#      flow-direction field, where it moves geometry instead of adding luma.
#
# Identity is carried by HUE anchors that follow the geometry (hue_drift /
# the hue-probe in _FieldKit), never by value swings (vd) or interference
# phase (tmod) — both are low-frequency, and the metric is a ratio, so macro
# luma drama is charged twice.
# ════════════════════════════════════════════════════════════════════════════

_P0 = 10.4   # canonical lattice pitch in _S units == 8.7 px at GEN 640
             # == 6.9 px at 512 == r 74 (J0 0.80) == 28 px on a 2048 car.


_LC = 1.9   # low-cut sigma in _S units: x - gauss(x, sigma) is a HIGH-pass
            # with cutoff r ~ res/(2*pi*sigma), so 1.9 (== 1.58 px at GEN 640)
            # puts the knee exactly at r=64 — the bottom of the car band. A
            # larger sigma leaves a 40-64 skirt behind, which is where half
            # this module's remaining sub-band power was hiding.


def _flat(x, s=1.6):
    """LOW-CUT a value field: subtract its own local mean, keep the global
    mean. Not a sharpen and not noise — every shape and edge survives; only
    the slow wander that lands under r=64 is deleted (law L1/L3)."""
    x = np.asarray(x, np.float32)
    return x - gauss(x, float(s)) + float(x.mean())


def _fat(d, w, soft=0.34):
    """Fat smooth seam profile from a 0..1 edge-distance field (0 = seam
    centre) -> 1 on the seam, 0 inside the cell (law L2)."""
    w = np.asarray(w, np.float32)
    t = np.clip((d - w) / np.minimum(w * (float(soft) - 1.0), -1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _grain(xx, yy, cell, salt, thr=0.62):
    """Per-cell speckle — [090b] now DOMED and floored INSIDE the car band.
    A hard hash step on a 2 px cell at GEN puts all of its power above r=256
    (pure denominator); a smooth bump on a >= 4 px cell carries the lattice
    fundamental instead. Signature unchanged."""
    res = int(np.asarray(xx).shape[0])
    c = max(float(cell), 4.0 * res / 640.0)
    du = frac(xx / c) - 0.5
    dv = frac(yy / c) - 0.5
    dome = np.clip(1.0 - 3.6 * (du * du + dv * dv), 0.0, 1.0)
    g = h2(np.floor(xx / c), np.floor(yy / c), salt)
    return sstep(thr, min(thr + 0.18, 0.999), g) * dome


def _fine(res, seed, k=0.13):
    """Closing micro-relief — TWO dome lattices at 6.4 and 4.4 px at GEN
    (fundamentals r=100 and r=145), random amplitude per cell.

    [090b] LAW L4, and the arithmetic that makes it binding: a value-noise
    grid of n cells carries at most n/2 cycles per image and its power peaks
    near 0.35n, so the old `fbm(base 180) ridge + fbm(base 320)` pair peaked
    around r=63 and r=112 with a long 1/f skirt UNDER the band — measured as
    14-48%% of the total sitting at r 32-64 on half this module. A dome
    lattice has its power AT its own period by construction, and a random
    per-cell amplitude is a shape field (thousands of 8-14 px domes on a
    2048 car), never a per-pixel noise term."""
    s = res / 640.0
    sd = _sd(seed)
    yy, xx = coords(res)
    acc = np.zeros((res, res), np.float32)
    for c, w, salt in ((7.6, 0.62, 811), (5.2, 0.38, 823)):   # r 84 / 123
        cc = c * s
        du = frac(xx / cc) - 0.5
        dv = frac(yy / cc) - 0.5
        dome = np.clip(1.0 - 3.4 * (du * du + dv * dv), 0.0, 1.0)
        g = h2(np.floor(xx / cc), np.floor(yy / cc), sd + salt)
        acc += (g - 0.5) * dome * w
    return (acc * (1.15 * float(k))).astype(np.float32)


def _ptier(res, cell, salt, ang=0.0, relief=0.55, jit=0.30):
    """8-tier tint on an IN-BAND domed patch lattice (law L1): the tint
    arrives WITH its own smooth relief, so it is band-pass instead of the
    low-pass skirt a flat per-cell value leaves behind."""
    yy, xx = coords(res)
    if ang:
        ca, sa = np.cos(float(ang)), np.sin(float(ang))
        u, v = xx * ca + yy * sa, -xx * sa + yy * ca
    else:
        u, v = xx, yy
    c = float(cell)
    ci, cj = np.floor(u / c), np.floor(v / c)
    jx = (h2(ci, cj, salt + 3) - 0.5) * float(jit)
    jy = (h2(ci, cj, salt + 7) - 0.5) * float(jit)
    d = np.maximum(np.abs(frac(u / c) - 0.5 + jx),
                   np.abs(frac(v / c) - 0.5 + jy)) * 2.0
    return _tier(h2(ci, cj, salt)) * (1.0 - relief + relief * sstep(1.02, 0.24, d))


def _cells(res, pitch, salt, jit=0.85, taps=9, need2=True):
    """Jittered-grid nearest-feature field. Returns (dx, dy, d1, id1, d2):
    offset to / distance to the nearest feature point in px, per-feature hash
    id, and second-nearest distance (None when need2=False). The one kernel
    that lets a generator stamp THOUSANDS of 8-32px features vectorized.
    Perf: the per-cell hashes are computed ONCE on the coarse cell grid and
    gathered per tap (27 full-res sin evals -> 3 tiny grids + cheap int
    gathers); dot-stamp layers can run taps=5 / need2=False.
    [090b] callers now pass BOUNDED jitter (<= ~0.55, law L3) so the lattice
    keeps a sharp spectral fundamental."""
    g = float(pitch)
    yy, xx = coords(res)
    cu = np.floor(xx / g)
    cv_ = np.floor(yy / g)
    n = int(np.ceil(res / g)) + 4
    ii = np.arange(-1, n, dtype=np.float32)
    CU, CV = np.meshgrid(ii, ii)
    JX = h2(CU, CV, salt)
    JY = h2(CU, CV, salt + 57)
    JB = h2(CU, CV, salt + 91)
    iu = cu.astype(np.int32) + 1
    iv = cv_.astype(np.int32) + 1
    best = np.full((res, res), 1e9, np.float32)
    second = np.full((res, res), 1e9, np.float32) if need2 else None
    bdx = np.zeros((res, res), np.float32)
    bdy = np.zeros((res, res), np.float32)
    bid = np.zeros((res, res), np.float32)
    offs = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (1, -1), (-1, 1), (1, 1))[:int(taps)]
    for di, dj in offs:
        ix = np.clip(iu + di, 0, n)
        iy = np.clip(iv + dj, 0, n)
        jx = JX[iy, ix]
        jy = JY[iy, ix]
        fx = (cu + (di + 0.5) + (jx - 0.5) * jit) * g
        fy = (cv_ + (dj + 0.5) + (jy - 0.5) * jit) * g
        ddx = xx - fx
        ddy = yy - fy
        d = ddx * ddx + ddy * ddy
        m = d < best
        if need2:
            second = np.where(m, best, np.minimum(second, d))
        best = np.where(m, d, best)
        bdx = np.where(m, ddx, bdx)
        bdy = np.where(m, ddy, bdy)
        bid = np.where(m, JB[iy, ix], bid)
    return (bdx, bdy, np.sqrt(best), bid,
            np.sqrt(second) if need2 else None)


def _pave(res, p, salt, jit=0.45, seam=0.22, taps=9):
    """THE workhorse of the rebuild: a bounded-jitter cell pave carrying its
    own in-cell RELIEF and a fat edge-distance seam (laws L1-L3). Returns
    (dx, dy, d1, id1, edge, crown, seam_mask) where `edge` is 0 on the
    polygon boundary and `crown` is the smooth dome whose period IS the
    lattice fundamental — the term that moved this module's value off flat
    per-cell tints and into the car band."""
    dx, dy, d1, id1, d2 = _cells(res, p, salt, jit, taps=taps, need2=True)
    edge = (d2 - d1) / p
    return dx, dy, d1, id1, edge, sstep(0.02, 0.40, edge), _fat(edge, float(seam))


# ════════════════════════════════════════════════════════════════════════════
# STRUCTURAL GENERATORS — 20 distinct field archetypes, one per finish id.
# Every one: a dense in-band micro-field per the law above; the ARCHETYPE
# LEDGER at the top of the module is unchanged (one composition per id).
# [SPB-FRACTURED-090b 2026-08-02]
# ════════════════════════════════════════════════════════════════════════════

def g_rosette(res, seed, pitch=_P0, rings=1.30, petals=7.0, dome=0.46,
              body=0.24, seam=0.20, fine=0.11):
    """rosette tier-pack — a pave of small scalloped ring whorls, each DOMED
    (L1) and cut from its neighbours by a fat petal-gap seam (L2)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.42, seam)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.62)
    scal = 0.09 * np.cos(th * petals + id1 * 61.0)
    ring = 0.5 + 0.5 * np.cos((rr + scal) * rings * _TAU + id1 * 11.0)
    T = (0.12 + crown * dome + ring * ring * 0.24 * (0.30 + 0.70 * crown)
         + _flat(_tier(id1), _LC * s) * body * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.85 * gs) + _fine(res, seed, fine))


def g_pleat(res, seed, col=13.0, rib=9.2, slope=0.45, dome=0.36, fine=0.11):
    """chevron pleats — herringbone columns of pinnate leaflet ribs. [090b]
    rib pitch 3.8 -> 7.7 px at GEN and chevron slope 0.85 -> 0.45: the old
    geometry put its x-period at 3.6 px at 512, which is a NEGATIVE lag-1
    autocorrelation (this finish measured 0.035, the module's worst). A
    tilted stripe keeps its 2-D radius in the band while its x-period stays
    long — the one shape that wins both gates at once."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 23, 4.0)
    X = xx + wu
    Y = yy + wv
    cw = col * s
    ci = np.floor(X / cw)
    u = frac(X / cw)
    sign = 1.0 - 2.0 * np.mod(ci, 2.0)
    q = Y / (rib * s) + sign * u * (cw / (rib * s)) * slope
    ribs = 0.5 + 0.5 * np.cos(q * _TAU)
    seam = sstep(0.09, 0.0, np.minimum(u, 1.0 - u))
    tier = _flat(_tier(h2(ci, np.floor(q), sd + 5)), _LC * s)
    T = 0.16 + ribs * dome + tier * 0.30 * (0.30 + 0.70 * ribs)
    return n01(T * (1.0 - 0.55 * seam) + _fine(res, seed, fine))


def g_pinwheel(res, seed, pitch=_P0, arms=4.0, twist=1.1, dome=0.44,
               seam=0.20, fine=0.11):
    """pinwheel curl pave — a field of tiny log-spiral petal whorls, the
    spiral cut INTO the cell dome instead of drawn on a flat tint."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.40, seam)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.60)
    sp = (0.5 + 0.5 * np.cos(th * arms + rr * twist * _TAU + id1 * 43.0)) ** 1.6
    T = (0.12 + crown * dome + sp * 0.26 * (0.25 + 0.75 * crown)
         + _flat(_tier(id1), _LC * s) * 0.24 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.85 * gs) + _fine(res, seed, fine))


def g_billow(res, seed, pitch=_P0, lx=0.62, ly=0.79, dome=0.50, seam=0.24,
             fine=0.10):
    """micro-billows — close-packed shaded petal cushions with kissing
    contact shadows. The cushion IS the relief (L1); the light term is a
    lambert tilt across the same dome, so it adds no extra frequency."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.48, seam)
    rr = d1 / (p * 0.70)
    lam = np.clip((dx * lx + dy * ly) / np.maximum(d1, 1e-4), -1.0, 1.0)
    lam = lam * np.sqrt(np.clip(rr, 0.0, 1.0))
    T = (0.13 + crown * dome + lam * 0.16 * crown
         + _flat(_tier(id1), _LC * s) * 0.26 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.80 * gs) + _fine(res, seed, fine))


def g_lamina(res, seed, pitch=7.6, angle=0.9, warp=5.0, cross=0.65,
             fine=0.12):
    """directional lamina eddies — warp-combed fine petal sheets. [090b] the
    warp amplitude dropped 30 -> 5 px: a big warp smears the stripe
    fundamental across the whole spectrum (it was costing both band and
    peakiness), while a small one still bends the sheets into eddies."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 41, warp)
    ca, sa = np.cos(angle), np.sin(angle)
    q = ((xx + wu) * ca + (yy + wv) * sa) / (pitch * s)
    lam = 0.5 + 0.5 * np.cos(q * _TAU)
    q2 = ((xx - wv) * sa - (yy - wu) * ca) / (pitch * cross * s)
    xl = 0.5 + 0.5 * np.cos(q2 * _TAU)
    tier = _flat(_tier(h2(np.floor(q), np.floor(q2 * 0.5), sd + 9)), _LC * s)
    T = 0.14 + lam * 0.44 + xl * 0.14 * lam + tier * 0.26 * (0.30 + 0.70 * lam)
    return n01(T + _fine(res, seed, fine))


def g_rdlab(res, seed, cell=2.0, iters=5, gain=1.5, sig=3.6, fine=0.10):
    """reaction-diffusion petal labyrinth. [090b] LAW L4: the RD seed was a
    3-octave fbm, so the maze inherited the pyramid's sub-band skirt and grew
    at whatever coarse scale the seed happened to carry (measured: 48%% of
    this finish's power sat at r 32-64). A Turing system can only amplify a
    wavelength that EXISTS in its seed, so the seed grid is now fine (2 px
    cells at GEN = up to 160 cycles) and the DoG radius alone selects the
    maze period — one unstable wavelength, which is the real physics."""
    s = res / _S
    sd = _sd(seed)
    n = max(8, int(round(res / max(cell * s, 1.2))))
    f = fbm(res, res, rng(seed, 55), 1, n)
    f = n01(f - gauss(f, 2.2 * s))
    for _ in range(int(iters)):
        f = np.clip(f + gain * (f - gauss(f, sig * s)), 0.0, 1.0)
    lab = sstep(0.34, 0.66, f)
    rim = 1.0 - np.abs(2.0 * lab - 1.0)
    T = (0.16 + lab * 0.44 + rim * 0.20
         + _ptier(res, 9.0 * s, sd + 3, relief=0.7) * 0.24)
    return n01(T + _fine(res, seed, fine))


def g_imbric(res, seed, sw=10.6, rh=7.2, ribs=2.0, fine=0.08):
    """scale imbrication — shingled fan-ribbed petal scales in offset rows.
    [090b] 9 fan ribs inside a 9 px scale is a 1 px feature (above the band
    and pure denominator); 3 ribs is a 3 px feature that reads as a fan and
    lands in the band."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 61, 4.0)
    u = (xx + wu) / (sw * s)
    v = (yy + wv) / (rh * s)
    T = np.zeros((res, res), np.float32)
    done = np.zeros((res, res), np.float32)
    for k in (1, 0):
        uu = u + 0.5 * k
        vv = v + 0.5 * k
        cu = np.floor(uu)
        cv_ = np.floor(vv)
        du = (uu - cu - 0.5) * (sw * s)
        dv = (vv - cv_ - 0.15) * (rh * s)
        rrad = np.hypot(du, dv * 0.9) / (sw * s * 0.60)
        inside = sstep(1.02, 0.90, rrad)
        th = np.arctan2(du, dv + 1e-4)
        fan = 0.5 + 0.5 * np.cos(th * ribs + h2(cu, cv_, sd + 7) * 6.0)
        crown = np.clip(1.0 - rrad * rrad, 0.0, 1.0)
        val = (0.14 + crown * 0.46 + fan * 0.14 * crown
               + _flat(_tier(h2(cu, cv_, sd)), _LC * s) * 0.26
               * (0.25 + 0.75 * crown))
        T = T + val * inside * (1.0 - done)
        done = np.clip(done + inside, 0.0, 1.0)
    return n01(T + (1.0 - done) * 0.10 + _fine(res, seed, fine))


def g_foam(res, seed, pitch=_P0, wall=0.30, fine=0.10):
    """polyp foam pack — bright-walled foam cells with dark mouth pores. The
    WALL is the fat seam (L2) and the cell floor is a shallow inverted dome,
    so the wall lattice fundamental carries the value."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.52, wall)
    rr = d1 / (p * 0.72)
    mouth = _bump((d1 / (2.0 * s)) ** 2) * 0.30
    T = (0.14 + gs * 0.44 + (1.0 - crown) * 0.10
         + _flat(_tier(id1), _LC * s) * 0.26 * (0.30 + 0.70 * crown)
         + crown * 0.20 - mouth)
    return n01(T + _fine(res, seed, fine))


def g_platemosaic(res, seed, pitch=11.0, petals=6.0, seam=0.26, fine=0.10):
    """plate-mosaic — grouted plates, each stamped with a ray floret. The
    plate now carries a crown (L1) and the grout is fat (L2)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.44, seam)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.60)
    ring = sstep(0.20, 0.06, np.abs(rr - 0.44))
    ring = ring * (0.55 + 0.45 * np.cos(th * petals + id1 * 31.0))
    disc = sstep(0.26, 0.12, rr) * 0.24
    T = (0.13 + crown * 0.40 + ring * 0.24 + disc
         + _flat(_tier(id1), _LC * s) * 0.26 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.90 * gs) + _fine(res, seed, fine))


def g_petalcells(res, seed, pitch=_P0, seam=0.22, fine=0.10):
    """interlocking petal-cross cells — packed 4-lobe florets. The lobe
    pattern MODULATES the cell dome rather than sitting on a flat tint."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.38, seam)
    th = np.arctan2(dy, dx)
    a0 = id1 * _TAU
    lobe = np.abs(np.cos((th - a0) * 2.0)) ** 1.2
    vein = sstep(0.12, 0.02, np.abs(np.sin((th - a0) * 2.0))) * crown * 0.20
    eye = _bump((d1 / (2.2 * s)) ** 2) * 0.26
    T = (0.13 + crown * (0.26 + 0.26 * lobe) + vein + eye
         + _flat(_tier(id1), _LC * s) * 0.24 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.85 * gs) + _fine(res, seed, fine))


def _needles(res, pitch, sd, ln, wd, s):
    """One ply of oriented needles on a bounded-jitter lattice: (body, tip
    bead, cell id). [090b] the ply is wider (1.8 px at GEN, not 1.3) and
    shorter — a hairline needle throws its power above r=256."""
    dx, dy, d1, id1, _ = _cells(res, pitch * s, sd, 0.5, taps=5, need2=False)
    a = np.floor(id1 * 8.0) * 0.7853982 + 0.2
    ca, sa = np.cos(a), np.sin(a)
    along = dx * ca + dy * sa
    across = np.abs(-dx * sa + dy * ca)
    L = ln * s * (0.75 + 0.5 * h2(np.floor(id1 * 31.0), 0.0, sd + 3))
    body = sstep(wd * s, wd * s * 0.35, across) * sstep(L, L * 0.72,
                                                        np.abs(along))
    tipd = np.hypot(dx - ca * L, dy - sa * L)
    return body, _bump((tipd / (2.4 * s)) ** 2), id1


def g_needlefelt(res, seed, pitch=_P0, ln=5.6, fine=0.11):
    """needle felt — two crossed plies of anther-tipped stamen needles. The
    orientation is QUANTIZED to 8 directions [090b]: free angles smear the
    needle spectrum into a disc, quantized ones give 8 sharp lobes (the
    peakiness guard) and read as a real carded felt."""
    s = res / _S
    sd = _sd(seed)
    b1, a1, i1 = _needles(res, pitch, sd, ln, 1.9, s)
    b2, a2, i2 = _needles(res, pitch * 0.82, sd + 101, ln * 0.8, 1.6, s)
    T = (0.18 + np.maximum(b1 * (0.34 + _flat(_tier(i1), _LC * s) * 0.44),
                           b2 * (0.30 + _flat(_tier(i2), _LC * s) * 0.40))
         + np.maximum(a1, a2 * 0.85) * 0.42)
    return n01(T + _fine(res, seed, fine))


def g_starlat(res, seed, pitch=_P0, rays=5.0, fine=0.11):
    """star-lattice sparks — a NEAR-REGULAR lattice (jitter 0.22) of fine ray
    bursts. Low jitter is deliberate: it is the module's sharpest spectral
    fundamental, which is what the peakiness guard measures (L3)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.22, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.68)
    star = (0.5 + 0.5 * np.cos(th * rays + id1 * _TAU)) ** 2.4
    star = star * np.clip(1.0 - rr, 0.0, 1.0)
    core = _bump((rr * 3.0) ** 2) * 0.42
    halo = sstep(0.20, 0.06, np.abs(rr - 0.60)) * 0.12
    T = (0.16 + star * 0.42 + core + halo
         + _flat(_tier(id1), _LC * s) * 0.26)
    return n01(T + _fine(res, seed, fine))


def g_fringe(res, seed, rh=10.6, fw=9.6, fine=0.10):
    """comb-fringe rows — banded filament combs with an anther bead at every
    tip. [090b] filament pitch 3.5 -> 8.0 px at GEN: at the old pitch the
    comb was a 2.8 px x-period at 512 (lag-1 autocorrelation NEGATIVE). At 25
    px on a 2048 car it still reads as a comb, and now it is coherent."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 71, 4.0)
    X = xx + wu
    Y = yy + wv
    rj = np.floor(Y / (rh * s))
    v = frac(Y / (rh * s))
    X2 = X + h2(rj, rj * 0.0, sd + 21) * 37.0
    fi = np.floor(X2 / (fw * s))
    u = frac(X2 / (fw * s))
    fil = 0.5 + 0.5 * np.cos((u - 0.5) * _TAU)
    fil = fil * sstep(0.08, 0.22, v) * sstep(0.97, 0.82, v)
    tier = _flat(_tier(h2(fi, rj, sd + 33)), _LC * s)
    bead = _bump(((v - 0.80) * rh / 2.2) ** 2 + ((u - 0.5) * fw / 2.2) ** 2)
    base = sstep(0.12, 0.02, v) * 0.28
    T = 0.16 + fil * (0.30 + tier * 0.38) + bead * 0.42 + base
    return n01(T + _fine(res, seed, fine))


def g_echinate(res, seed, pitch=_P0, spikes=7.0, fine=0.10):
    """echinate dust scatter — spiky pollen grains over a coarser dust ply.
    Both plies now sit in the band (grain 8.7 px, dust 5.4 px at GEN)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.5, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.58)
    prof = rr - 0.20 * np.maximum(np.cos(th * spikes + id1 * _TAU), 0.0) ** 2
    body = sstep(0.66, 0.42, prof)
    dome = np.clip(1.0 - rr * rr, 0.0, 1.0)
    _, _, db, idb, _2 = _cells(res, 6.5 * s, sd + 77, 0.5, taps=5, need2=False)
    dust = _bump((db / (1.9 * s)) ** 2)
    T = (0.15 + body * (0.24 + _flat(_tier(id1), _LC * s) * 0.40)
         + dome * 0.16 + dust * (0.16 + _flat(_tier(idb), _LC * s) * 0.24))
    return n01(T + _fine(res, seed, fine))


def g_threaddrift(res, seed, pitch=9.6, steps=3, step_px=2.4, fine=0.10):
    """flow-smeared thread-drift — grains advected into fading comet trails.
    The flow POTENTIAL stays fbm (it only bends geometry, it adds no luma —
    the L4 carve-out); the grains themselves are an in-band lattice."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.55, taps=5, need2=False)
    dot = _bump((d1 / (2.6 * s)) ** 2) * (0.50 + _flat(_tier(id1), _LC * s) * 0.50)
    pot = gauss(fbm(res, res, rng(seed, 91), 3, 6), 3.0)
    gx = cv2.Sobel(pot, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(pot, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy) + 1e-6
    vx, vy = -gy / mag, gx / mag
    yy, xx = coords(res)
    acc = dot.copy()
    mx, my = xx.copy(), yy.copy()
    for k in range(int(steps)):
        mx = (mx - vx * step_px * s) % res
        my = (my - vy * step_px * s) % res
        samp = cv2.remap(dot, mx.astype(np.float32), my.astype(np.float32),
                         cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        acc = np.maximum(acc, samp * (1.0 - 0.16 * (k + 1)))
    _, _, db2, idb2, _b2 = _cells(res, 6.6 * s, sd + 177, 0.55, taps=5,
                                  need2=False)
    dust = _bump((db2 / (1.7 * s)) ** 2) * (0.18 + _tier(idb2) * 0.44)
    T = 0.14 + acc * 0.80 + dust * 0.72
    return n01(T + _fine(res, seed, fine))


def g_dustclump(res, seed, pitch=_P0, fine=0.10):
    """clumped structured dust — grains gathered into clumps. [090b] LAW L4:
    the clump ENVELOPE was a 32 px fbm, i.e. pure sub-band energy dressed as
    composition. The clumps are now a bounded-jitter lattice of their own, so
    the clumping reads exactly the same and costs nothing below r=64."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    _dx, _dy, dc, idc, edge, crown, _gs = _pave(res, p, sd + 9, 0.5, 0.18)
    env = 0.30 + 0.70 * crown * sstep(0.25, 0.70, h2(np.floor(idc * 313.0),
                                                     0.0, sd + 4))
    _, _, da, ida, _a = _cells(res, 4.6 * s, sd, 0.55, taps=5, need2=False)
    _, _, db, idb, _b = _cells(res, 7.4 * s, sd + 55, 0.55, taps=5, need2=False)
    ga = _bump((da / (1.6 * s)) ** 2) * (0.4 + _tier(ida) * 0.6)
    gb = _bump((db / (2.4 * s)) ** 2) * (0.4 + _tier(idb) * 0.6)
    dust = np.maximum(ga, gb * 0.92) * env
    T = 0.16 + dust * 0.78 + crown * 0.14
    return n01(T + _fine(res, seed, fine))


def g_porate(res, seed, pitch=_P0, pores=3, seam=0.20, fine=0.10):
    """porate close-pack grains — reticulate near-touching grains with germ
    pores. The grain body is the cell crown; the pores are small craters."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.40, seam)
    rr = d1 / (p * 0.66)
    rim = sstep(0.20, 0.06, np.abs(rr - 0.62)) * 0.18
    ret = _grain(dx + 13.0, dy + 71.0, 5.8 * s, sd + 5) * crown * 0.16
    T = (0.13 + crown * 0.46 + rim + ret
         + _flat(_tier(id1), _LC * s) * 0.26 * (0.25 + 0.75 * crown))
    for k in range(int(pores)):
        a = id1 * _TAU + k * 2.4
        pd = np.hypot(dx - np.cos(a) * p * 0.26, dy - np.sin(a) * p * 0.26)
        T = T - _bump((pd / (2.5 * s)) ** 2) * 0.20 * crown
    return n01(T * (1.0 - 0.80 * gs) + _fine(res, seed, fine))


def g_trellis(res, seed, pitch=9.8, angle=0.55, fine=0.10):
    """woven trellis cross — two stem families with knotted crossings.
    [090b] pitch 10.8 -> 8.2 px at GEN: at the old pitch the lattice
    fundamental sat at r=59, i.e. UNDER the car band, and the whole finish
    was paying for a structure the metric could not see."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 111, 4.0)
    X = xx + wu
    Y = yy + wv
    # [090b] the two families are tilted from VERTICAL, not from horizontal:
    # a wave vector's 2-D radius (== its car-band position) is |k|, but the
    # lag-1 coherence guard only sees its X component. Rotating the same
    # lattice so kx is the SMALL component keeps r=74 and moves the guard
    # from cos(2pi/7.7px)=0.66 to cos(2pi/12.6px)=0.88 — free coherence, and
    # a climbing trellis reads better upright anyway.
    ca, sa = np.cos(angle), np.sin(angle)
    qa = (X * sa + Y * ca) / (pitch * s)
    qb = (X * sa - Y * ca) / (pitch * s)
    pa = 0.5 + 0.5 * np.cos(qa * _TAU)
    pb = 0.5 + 0.5 * np.cos(qb * _TAU)
    stemA = pa ** 1.3
    stemB = pb ** 1.3
    tA = _flat(_tier(h2(np.floor(qa), np.floor(qb * 0.5), sd + 3)), _LC * s)
    tB = _flat(_tier(h2(np.floor(qb), np.floor(qa * 0.5), sd + 4)), _LC * s)
    stem = np.maximum(stemA * (0.38 + tA * 0.44), stemB * (0.34 + tB * 0.40))
    knot = (pa * pb) ** 1.3
    gate = sstep(0.35, 0.55, h2(np.floor(qa + 0.5), np.floor(qb + 0.5), sd + 9))
    T = 0.16 + stem * 0.52 + knot * gate * 0.40 - stemA * stemB * 0.14
    return n01(T + _fine(res, seed, fine))


def g_stemmesh(res, seed, pitch=_P0, fine=0.07):
    """branching stem mesh — 3-scale venation. [090b] LAW L4: the veins were
    ridged fbm at base 24/56/120, i.e. a low-pass field dressed as a network
    (this finish could not pass 0.62 through three tunings). They are now
    bounded-jitter Voronoi ridge webs, which branch at TRUE triple points (a
    better vein habit anyway) and carry a sharp in-band fundamental."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    # [090b] ONE wide primary web (r=74) with the secondary veinlets riding
    # INSIDE the areoles instead of a second full-strength web: two competing
    # webs plus a sharp node product spread this finish's power from r=64 to
    # r=250 and it could not clear the coherence guard at any LUT span
    # (measured 0.30-0.40 across the whole sweep).
    _dxa, _dya, _d1a, ida, ea, crowna, _va = _pave(res, p, sd + 121, 0.50, 0.30)
    _dxb, _dyb, _d1b, idb, eb, _cb, _vb = _pave(res, p * 0.78, sd + 131, 0.50,
                                                0.24)
    vein = _fat(ea, 0.30)
    veinlet = _fat(eb, 0.24) * (1.0 - vein)
    _, _, bd, bid, _b = _cells(res, 8.4 * s, sd + 61, 0.5, taps=5, need2=False)
    buds = _bump((bd / (2.4 * s)) ** 2)
    buds = buds * sstep(0.30, 0.70, h2(np.floor(bid * 91.0), 0.0, sd + 8))
    T = (0.15 + vein * 0.44 + veinlet * 0.24 + crowna * 0.16
         + _flat(_tier(ida), _LC * s) * 0.20 + buds * 0.24)
    return n01(T + _fine(res, seed, fine))


def g_beadcurtain(res, seed, pitch=9.6, bead=7.2, fine=0.10):
    """hanging bead-strand curtain — swaying strands of tiered pea blossoms.
    Sway amplitude cut to ~1 px at GEN: a big sway walks the strand lattice
    off its own period and smears the fundamental (L3)."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    ci = np.floor(xx / (pitch * s))
    ph = h2(ci, ci * 0.0, sd + 11)
    sway = (np.sin(yy / (30.0 * s) + ph * _TAU) * 1.1 * s
            + np.sin(yy / (11.0 * s) + ph * 9.0) * 0.5 * s)
    u = xx - (ci + 0.5) * (pitch * s) - sway
    # [090b] the strand is FAT (3.2 px at GEN of an 8 px pitch) and the gap
    # carries its own shallow relief: a 1.6 px thread on an 8 px pitch left
    # 80%% of the canvas flat, and a sparse field drains its power downward
    # out of the band however fine the thread is.
    strand = sstep(3.2 * s, 0.6 * s, np.abs(u))
    gapre = 0.5 + 0.5 * np.cos((u / (pitch * s)) * _TAU)
    bj = np.floor(yy / (bead * s) + ph * 7.0)
    vb = frac(yy / (bead * s) + ph * 7.0)
    tap = 0.62 + 0.38 * h2(ci, np.floor(yy / (12.0 * s)), sd + 31)
    brad = (3.4 * s) * tap
    bd = np.sqrt(u * u + ((vb - 0.5) * bead * s) ** 2)
    beadm = _bump((bd / np.maximum(brad, 1e-3)) ** 2)
    tier = _flat(_tier(h2(ci, bj, sd + 17)), _LC * s)
    T = (0.14 + strand * 0.30 + gapre * 0.16 + beadm * (0.32 + tier * 0.44))
    return n01(T + _fine(res, seed, fine))


def _lowcut(fn):
    """Universal LOW-CUT knob (`lowcut` px at GEN) wrapped around every
    generator. [090b] the one dial that trades neighbour coherence for
    car-band energy: it subtracts the field's own slow local mean (keeping
    the global mean, so the LUT walk is unchanged) and therefore deletes
    power UNDER r=64 without touching a single shape or edge. Archetypes
    that still carry an unavoidable sub-band skirt after their geometry is
    fixed spend their coherence surplus here.

    Second knob, `span` — the LUT TRAVERSAL width, and the single biggest
    band lever found in this pass. The thin-film LUT is an OSCILLATOR: over a
    typical 400-950 nm recipe it runs ~2 sin^2 cycles, so mapping a full 0..1
    T field through it MULTIPLIES the generator's frequencies (measured on the
    pinwheel pave: T carried 53%% of its power at r 64-90 and the paint came
    out with 49%% at r 160-256 — the geometry was right and the LUT moved it
    out of the coherent end of the band). Compressing T about its midpoint
    traverses fewer LUT cycles, so the paint keeps the frequency the generator
    designed. Hue travel is unaffected in practice: the hero-hue window
    re-anchors hue anyway, and luma contrast is preserved because a shorter
    walk sits on a steeper part of the curve.
    The walk is centred on `mid`, not on 0.5: see _lut_steep() under the
    recipes. Compressing about an arbitrary point can land on an EXTREMUM of
    the sin^2 curve, where dL/dT ~ 0 — measured on the rosette pave, span 0.5
    about 0.5 left the paint luma nearly flat (fineness 1.3 with a mono
    palette: every visible texture was coming from the hue remap, not from
    the relief). Centred on the steepest monotone stretch instead, the same
    span gives maximum luma contrast per unit T AND the most linear transfer,
    which is what keeps the generator's frequencies where it put them.

    Third knob, `soft` — a sub-pixel blur at GEN that trims the r>200
    harmonics a hard edge throws off. Those harmonics are technically INSIDE
    the car band, so they inflate the score while destroying the coherence it
    is supposed to certify (that is exactly the hole white noise walks
    through). Spending a little band to delete them is the honest direction.
    """
    def g(res, seed, lowcut=0.0, span=1.0, soft=0.0, mid=0.5, **kw):
        T = fn(res, seed, **kw)
        lc = float(lowcut)
        if lc > 0.0:
            T = np.asarray(T, np.float32)
            T = T - (gauss(T, lc * res / 640.0) - float(T.mean()))
            T = np.clip(T, 0.002, 0.998)
        if float(soft) > 0.0:
            T = gauss(np.asarray(T, np.float32), float(soft) * res / 640.0)
        sp = float(span)
        if sp != 1.0:
            T = np.clip(float(mid) + (np.asarray(T, np.float32) - 0.5) * sp,
                        0.002, 0.998)
        return T
    g.__name__ = fn.__name__
    g.__doc__ = fn.__doc__
    g.__wrapped__ = fn
    return g

ENGINES = {
    "rosette": g_rosette, "pleat": g_pleat, "pinwheel": g_pinwheel,
    "billow": g_billow, "lamina": g_lamina, "rdlab": g_rdlab,
    "imbric": g_imbric, "foam": g_foam, "platemosaic": g_platemosaic,
    "petalcells": g_petalcells, "needlefelt": g_needlefelt,
    "starlat": g_starlat, "fringe": g_fringe, "echinate": g_echinate,
    "threaddrift": g_threaddrift, "dustclump": g_dustclump,
    "porate": g_porate, "trellis": g_trellis, "stemmesh": g_stemmesh,
    "beadcurtain": g_beadcurtain,
}
ENGINES = {k: _lowcut(v) for k, v in ENGINES.items()}


class _FieldKit(catlib.CategoryKit):
    """[SPB-FRACTURED-FIELD 2026-08-02] STRUCTURE-FOLLOWING hue anchors.

    Pass 2a picked the hue anchor from an axis-aligned hash lattice; at 1:1 on
    a 2048 canvas that read as a checkerboard of colour squares slicing THROUGH
    the features. Pass 2b runs the finish's own generator at a cheap 192^2
    (~6% of the GEN cost) and picks the anchor from frac(T * hue_levels),
    jittered by a small per-cell hash and the macro domain: the colour now
    changes feature to feature and follows the geometry, while staying
    high-frequency. Luma is untouched: art_work re-applies Lpre after the hue
    window, so band / fineness / every guard are unaffected by ANYTHING in
    here — this method is pure look, which is why it can be fixed freely.

    [SPB-FRACTURED-090b 2026-08-02] Pass 2b was wrong at BOTH ends. It
    NEAREST-upscaled a 192 probe (3.3 px hue blocks at GEN) and ran
    hue_levels=3, so frac(T*3) swept all four anchors ACROSS EVERY SINGLE
    8 px feature: on the contact sheet the whole module read as a two-colour
    halftone screen — colour static, which is a failure however good the
    numbers are. Two fixes, both from the kintsugi palette law:
      * the probe is SMOOTHED and linearly upscaled, and hue_levels drops to
        ~1.4, so one hue holds across a patch of several features
        (~30-70 px on a 2048 car) — you read a coloured material, not dither;
      * the anchor list is HERO-DOMINANT (see the loop under the recipes):
        7/11 hero, 2/11 second, 1 each for the two accents, so a finish is
        one flower colour with accents instead of a confetti of four."""

    def macro_maps(self, d):
        Mval, Ddom = super().macro_maps(d)
        g = float(d.get("hue_cell", 0.0))
        if g <= 0.0:
            return Mval, Ddom
        r = 192      # hue-follow probe res (cheap: ~6% of a GEN run)
        sd = _sd(int(d["seed"]))
        T = np.asarray(self.engines[d["engine"]](r, int(d["seed"]),
                                                 **d.get("eargs", {})),
                       np.float32)
        T = n01(gauss(n01(T), float(d.get("hue_blur", 2.2))))
        T = cv2.resize(T, (self.GEN, self.GEN),
                       interpolation=cv2.INTER_LINEAR)
        yy, xx = coords(self.GEN)
        jit = h2(np.floor(xx / g), np.floor(yy / g), sd + 421)
        drift = gauss(Ddom, self.GEN / 48.0)
        D = frac(T * float(d.get("hue_levels", 1.4))
                 + jit * float(d.get("hue_jit", 0.14))
                 + drift * float(d.get("hue_drift", 0.5)))
        return Mval, np.clip(D, 0.0, 1.0).astype(np.float32)


def _lut_steep(lut, span=0.5):
    """T position (0..1) of the STEEPEST monotone stretch of a thin-film LUT's
    luma, for a walk of width `span`. [SPB-FRACTURED-090b 2026-08-02] The LUT
    is an oscillator: where it turns over, dL/dT = 0 and a compressed walk
    produces a flat, colour-only finish; a third of the way along a limb it is
    steep and near-linear, which is both the most contrast and the least
    harmonic distortion. Probed from the LUT itself so it stays correct if a
    recipe's film stack is retuned."""
    t = catlib.thinfilm_lut(*lut)
    L = t[:, 0] * 0.299 + t[:, 1] * 0.587 + t[:, 2] * 0.114
    g = np.abs(np.diff(L.astype(np.float64)))
    w = max(4, int(float(span) * len(L)))
    k = np.convolve(g, np.ones(w) / w, mode="valid")
    return float(int(np.argmax(k)) + w // 2) / float(len(L) - 1)


def _R(name, engine, eargs, lut, hues, hue_cell, desc, macro=("none", {}),
       vd=(0.78, 1.16), tmod=0.10, hspan=0.05, satboost=1.45, val=0.24,
       kw=None):
    base_kw = dict(ambient=0.22, ambient_sigma=40, floor=0.11, sparkle=0.14,
                   mswing=1.35)
    if kw:
        base_kw.update(kw)
    return dict(name=name, engine=engine, eargs=eargs, lut=lut, hues=hues,
                hspan=hspan, satboost=satboost, macro=macro, vd=vd, tmod=tmod,
                val=val, hue_cell=hue_cell, hue_drift=0.5, kw=base_kw,
                desc=desc)


# ════════════════════════════════════════════════════════════════════════════
# RECIPES — 20 finishes. Insertion order == 5x4 contact-sheet order (no two
# adjacent tiles share a hero hue). All seeds = crc32(fid). Every recipe:
# [SPB-FRACTURED-FIELD 2026-08-02] dense-field rebuild, archetype per ledger.
# ════════════════════════════════════════════════════════════════════════════

_BLOOM = {
 # [field 2026-08-02] rosette tier-pack, magenta/violet/pink over leaf dark
 "fbl_magenta_whorl": _R("Magenta Whorl", "rosette",
    dict(), (380.0, 940.0, 1.0, 1.30, 0.6),
    [0.87, 0.78, 0.30, 0.92], 6.0,
    "A pave of tiny magenta rose whorls, ring on scalloped ring, shoulder to shoulder. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] woven trellis, leaf/chartreuse/teal + amber knots
 "fbl_leafvine_drape": _R("Leafvine Drape", "trellis",
    dict(), (395.0, 930.0, 1.0, 1.28, 2.2),
    [0.30, 0.22, 0.42, 0.10], 13.0,
    "A woven trellis of fine green vine stems, a leaf knotted at every crossing. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] echinate scatter, butter/amber/lemon dust
 "fbl_butter_pollen": _R("Butter Pollen", "echinate",
    dict(), (410.0, 920.0, 1.0, 1.30, 2.8),
    [0.115, 0.09, 0.16, 0.05], 9.5,
    "A dense butter-yellow fall of spiky pollen grains with finer dust sifted between. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] lamina eddies, pink/rose/magenta sheets
 "fbl_pink_rose": _R("Pink Rose Spiral", "lamina",
    dict(), (385.0, 960.0, 1.0, 1.32, 1.1),
    [0.93, 0.97, 0.86, 0.30], 5.0,
    "Fine pink petal sheets combed into a thousand small rose eddies. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] polyp foam, coral/apricot/pink walls
 "fbl_coral_cluster": _R("Coral Cluster", "foam",
    dict(), (380.0, 950.0, 1.0, 1.30, 3.4),
    [0.035, 0.075, 0.98, 0.30], 6.0,
    "A packed coral foam of tiny florets, every cell walled bright with a dark mouth. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] plate mosaic, butter/orange/leaf grouted florets
 "fbl_butter_mosaic": _R("Butter Mosaic", "platemosaic",
    dict(), (415.0, 915.0, 1.0, 1.30, 4.0),
    [0.115, 0.05, 0.30, 0.14], 14.0,
    macro=("domains", dict(cells=5, salt=1471)), vd=(0.76, 1.16),
    desc="A grouted mosaic of small butter tiles, a ray floret stamped in every plate. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] thread-drift, pink/rose/orchid comet grains
 "fbl_pink_pollen": _R("Pink Pollen Drift", "threaddrift",
    dict(), (385.0, 965.0, 1.0, 1.30, 5.0),
    [0.90, 0.96, 0.83, 0.74], 5.0, val=0.30,
    kw=dict(sparkle=0.44),
    desc="Pink pollen grains smeared into fine drifting comet trails across dark silk. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] micro-billows, pearl gardenia — tinted, NOT chroma-dead
 "fbl_white_whorl": _R("Gardenia Whorl", "billow",
    dict(), (400.0, 890.0, 0.95, 1.10, 3.0),
    [0.12, 0.55, 0.93, 0.30], 12.0, satboost=1.05, val=0.26,
    kw=dict(floor=0.14, sparkle=0.12),
    desc="Cushioned gardenia petals packed edge to edge, pearl light on every cup. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] needle felt, red-coral/gold anthers
 "fbl_coral_stamen": _R("Coral Stamen", "needlefelt",
    dict(), (380.0, 970.0, 1.0, 1.30, 1.6),
    [0.02, 0.06, 0.115, 0.97], 13.0,
    "A felt of fine coral stamen needles, a gold anther bead at every tip. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] RD petal labyrinth, lilac/violet walls
 "fbl_lilac_rose": _R("Lilac Rose Spiral", "rdlab",
    dict(), (390.0, 945.0, 1.0, 1.30, 4.4),
    [0.74, 0.80, 0.68, 0.33], 6.0,
    "A lilac labyrinth of packed rose-petal walls winding over the whole panel. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] branching stem mesh, leaf/coral/amber veins
 "fbl_coral_vine": _R("Coral Vine Drape", "stemmesh",
    dict(), (380.0, 975.0, 1.0, 1.28, 5.2),
    [0.30, 0.04, 0.085, 0.44], 9.0,
    "A climbing mesh of branching coral vine veins, buds glowing at the nodes. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] star-lattice, lilac/violet/gold sparks
 "fbl_lilac_stamen": _R("Lilac Starburst", "starlat",
    dict(), (390.0, 950.0, 1.0, 1.32, 3.8),
    [0.72, 0.78, 0.13, 0.85], 6.0,
    macro=("bands", dict(angle=0.4, freq=1.2, warp=0.25)), vd=(0.76, 1.18),
    desc="A lattice of tiny lilac stamen bursts, gold-tipped rays on every spark. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] petal-cross cells, magenta/violet/pink pack
 "fbl_magenta_mosaic": _R("Magenta Mosaic", "petalcells",
    dict(), (385.0, 960.0, 1.0, 1.32, 0.3),
    [0.86, 0.78, 0.92, 0.27], 6.0,
    "Interlocking magenta hydrangea florets, four petals to a cell, packed tight. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] chevron pleats, leaf/emerald herringbone
 "fbl_leaf_whorl": _R("Leaf Whorl", "pleat",
    dict(), (395.0, 935.0, 1.0, 1.28, 2.0),
    [0.28, 0.35, 0.20, 0.115], 13.0,
    "Herringbone pleats of fine green leaflets, rib after rib after rib. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] structured dust, moonlit blue/cream clumps
 "fbl_white_pollen": _R("Moon Pollen", "dustclump",
    dict(), (400.0, 895.0, 0.95, 1.10, 3.2),
    [0.55, 0.13, 0.44, 0.65], 7.0, satboost=1.05, val=0.26,
    kw=dict(floor=0.14, sparkle=0.12),
    desc="Moon-white pollen dust gathered in silver clumps and small dark voids. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] comb-fringe rows, pink/gold filament combs
 "fbl_pink_stamen": _R("Pink Stamen Star", "fringe",
    dict(), (380.0, 980.0, 1.0, 1.32, 0.1),
    [0.92, 0.97, 0.13, 0.86], 6.0,
    "Row upon row of fine pink stamen combs, a gold bead at every filament tip. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] scale imbrication, blush/peach shingles
 "fbl_blush_rose": _R("Blush Rose Spiral", "imbric",
    dict(), (400.0, 900.0, 0.95, 1.18, 1.7),
    [0.95, 0.02, 0.90, 0.33], 6.0, satboost=1.30, val=0.25,
    desc="Blush rose petals shingled like fish scales, a ribbed fan in every one. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] bead-strand curtain, wisteria lilac racemes
 "fbl_lilac_vine": _R("Wisteria Drape", "beadcurtain",
    dict(), (390.0, 950.0, 1.0, 1.30, 4.1),
    [0.72, 0.79, 0.66, 0.30], 11.0,
    "A curtain of swaying wisteria strands strung with tiny lilac pea blossoms. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] pinwheel curl pave, butter/amber spirals
 "fbl_butter_whorl": _R("Butter Whorl", "pinwheel",
    dict(), (415.0, 920.0, 1.0, 1.30, 2.6),
    [0.115, 0.085, 0.15, 0.30], 6.0,
    "A pave of tiny butter-gold pinwheel whorls, every curl spun tight. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] porate close-pack, magenta/violet grains
 "fbl_magenta_pollen": _R("Magenta Pollen", "porate",
    dict(), (385.0, 960.0, 1.0, 1.32, 4.9),
    [0.83, 0.89, 0.95, 0.74], 6.0,
    "Magenta pollen grains packed grain on grain, each reticulate and pored. A FRACTURED BLOOM finish."),
}


# ════════════════════════════════════════════════════════════════════════════
# MACRO IDENTITY PLAN — [SPB-FRACTURED-FIELD 2026-08-02 pass 2c]
# Parent visual review of the frost/nebula/tempest trio: every numeric gate was
# green, yet 12-17 of 20 tiles per module leaned on the SAME macro device
# (catlib's Voronoi "domains" patchwork), so the family still read as one
# finish recolored. The pair-cosine gate cannot see this; only the eye can.
# Binding rule applied here:
#   * "domains" on AT MOST 4 ids per module, and those 4 vary the device
#     wildly (cells 3 / 5 / 8 / 14 == ~350 / 210 / 130 / 75 px domains at
#     2048, soft through hard-edged).
#   * every other id gets a DIFFERENT macro identity or NONE (pure continuous
#     micro-field — the MINDS house default and the strongest look).
#   * catlib.worley IGNORES its `seed` arg, so every domains/worley macro MUST
#     carry its own `salt` or unrelated finishes share one domain map.
# vd widens only on the macro'd ids (the macro has to be visible at thumbnail
# size) and stays tight elsewhere so car-band energy holds.
# ════════════════════════════════════════════════════════════════════════════

_MACRO_PLAN = {
    "fbl_magenta_whorl": (("continents", dict(base=3, cells=3.0)), (0.84, 1.13)),
    "fbl_leafvine_drape": (("none", {}), (0.78, 1.16)),
    "fbl_butter_pollen": (("rings", dict(freq=5.0, cx=0.42, cy=0.55)), (0.84, 1.13)),
    "fbl_pink_rose": (("bands", dict(angle=0.9, freq=2.4, warp=0.30)), (0.84, 1.13)),
    "fbl_coral_cluster": (("domains", dict(cells=3, salt=1201)), (0.84, 1.13)),
    "fbl_butter_mosaic": (("domains", dict(cells=8, salt=1471)), (0.84, 1.13)),
    "fbl_pink_pollen": (("vortex", dict(arms=2.0, twist=8.0)), (0.84, 1.13)),
    "fbl_white_whorl": (("margin", dict(freq=3.0, radius=0.78)), (0.84, 1.13)),
    "fbl_coral_stamen": (("rachis", dict(angle=0.5, sweep=4.0)), (0.84, 1.13)),
    "fbl_lilac_rose": (("continents", dict(base=4, cells=5.0)), (0.84, 1.13)),
    "fbl_coral_vine": (("none", {}), (0.78, 1.16)),
    "fbl_lilac_stamen": (("bands", dict(angle=1.5, freq=3.6, warp=0.22)), (0.84, 1.13)),
    "fbl_magenta_mosaic": (("domains", dict(cells=14, salt=1733)), (0.84, 1.13)),
    "fbl_leaf_whorl": (("none", {}), (0.78, 1.16)),
    "fbl_white_pollen": (("continents", dict(base=5, cells=2.5)), (0.84, 1.13)),
    "fbl_pink_stamen": (("rings", dict(freq=7.5, two=True)), (0.84, 1.13)),
    "fbl_blush_rose": (("vortex", dict(arms=3.0, twist=5.0, two=True)), (0.84, 1.13)),
    "fbl_lilac_vine": (("bands", dict(angle=0.1, freq=1.8, warp=0.34)), (0.84, 1.13)),
    "fbl_butter_whorl": (("domains", dict(cells=5, salt=1987)), (0.84, 1.13)),
    "fbl_magenta_pollen": (("none", {}), (0.78, 1.16)),
}

# Macro identity is carried by the HUE-ANCHOR field, not by value drama
# and not by interference phase. Pass 2c tried both of those first and
# the band medians collapsed (bloom 0.71 -> 0.56 on wide vd, -> 0.60 on
# tmod 0.30): a big smooth luma swing IS low-frequency energy, and the
# car-band metric is a ratio, so anything macro that touches luma pays
# for itself twice. Driving the macro through hue_drift instead makes
# the macro regions pick DIFFERENT palette anchors — clearly visible
# colour zoning at thumbnail size, which is what the glance test needs
# — while art_work re-applies the pre-remap luma (Lpre), so the micro
# field keeps 100% of its band energy.
for _fid, (_mac, _vd) in _MACRO_PLAN.items():
    _BLOOM[_fid]["macro"] = _mac
    _BLOOM[_fid]["vd"] = _vd
    _BLOOM[_fid]["tmod"] = 0.08
    _BLOOM[_fid]["hue_drift"] = 0.30 if _mac[0] == "none" else 0.95
# determinism law: per-finish seed straight from the id (no hash(str)).
for _fid, _d in _BLOOM.items():
    _d["seed"] = zlib.crc32(_fid.encode()) & 0x7FFFFFFF


# ════════════════════════════════════════════════════════════════════════════
# PER-FINISH FIELD TUNE — [SPB-FRACTURED-090b 2026-08-02]
# The generators own their geometry now (this module is 1 engine : 1 finish),
# so a recipe's eargs are its LOW-CUT dial plus any deliberate per-finish
# deviation. Values below are the measured optimum from the sweep in
# _fractured_triage/tune_field.py (band vs the four anti-static guards).
# Kit-level band hygiene, applied to every id:
#   vd  (0.96, 1.06)  a wide value swing IS low-frequency power, and the
#                     metric is a ratio, so macro luma drama is charged twice
#   tmod 0.0          same argument for interference phase
#   ambient 0.05      the wide bloom mix is a low-pass copy of the field
#   sparkle 0.08      the sparkle octave lands at r~320, ABOVE the band —
#                     pure denominator; fine detail now comes from shapes
# Macro identity survives 100% through the HUE anchors (hue_drift + the
# geometry-following hue probe), which are luma-neutral by construction.
# ════════════════════════════════════════════════════════════════════════════

_TUNE = {
 "fbl_blush_rose": dict(span=0.26, lowcut=1.6, soft=0, val=0.25),   # band 0.798 ac 0.614 pk 0.572
 "fbl_butter_mosaic": dict(span=0.5, lowcut=0, soft=0.55, val=0.24),   # band 0.941 ac 0.590 pk 0.641
 "fbl_butter_pollen": dict(span=0.26, lowcut=1.6, soft=0, val=0.24),   # band 0.877 ac 0.563 pk 0.623
 "fbl_butter_whorl": dict(span=0.5, lowcut=0, soft=0.55, val=0.34),   # band 0.960 ac 0.565 pk 0.656
 "fbl_coral_cluster": dict(span=0.26, lowcut=0, soft=0.55, val=0.34),   # band 0.905 ac 0.670 pk 0.743
 "fbl_coral_stamen": dict(span=0.36, lowcut=0, soft=0, val=0.24),   # band 0.815 ac 0.560 pk 0.446
 "fbl_coral_vine": dict(span=1, lowcut=0, soft=0.85, val=0.34),   # band 0.811 ac 0.615 pk 0.566
 "fbl_leaf_whorl": dict(span=0.7, lowcut=1.6, soft=0, val=0.34),   # band 0.967 ac 0.685 pk 0.844
 "fbl_leafvine_drape": dict(span=0.26, lowcut=1.6, soft=0, val=0.24),   # band 0.977 ac 0.807 pk 0.883
 "fbl_lilac_rose": dict(span=0.5, lowcut=0, soft=0.85, val=0.34),   # band 0.752 ac 0.564 pk 0.393
 "fbl_lilac_stamen": dict(span=0.7, lowcut=0, soft=0.85, val=0.34),   # band 0.807 ac 0.579 pk 0.602
 "fbl_lilac_vine": dict(span=0.26, lowcut=0, soft=0.55, val=0.34),   # band 0.820 ac 0.558 pk 0.885
 "fbl_magenta_mosaic": dict(span=0.26, lowcut=0, soft=0.55, val=0.34),   # band 0.924 ac 0.691 pk 0.791
 "fbl_magenta_pollen": dict(span=1, lowcut=0, soft=0.85, val=0.34),   # band 0.760 ac 0.602 pk 0.605
 "fbl_magenta_whorl": dict(span=0.26, lowcut=0, soft=0.55, val=0.34),   # band 0.934 ac 0.566 pk 0.624
 "fbl_pink_pollen": dict(span=0.7, lowcut=0, soft=0, val=0.3),   # band 0.709 ac 0.627 pk 0.527
 "fbl_pink_rose": dict(span=0.26, lowcut=1.6, soft=0, val=0.24),   # band 0.972 ac 0.680 pk 0.950
 "fbl_pink_stamen": dict(span=0.7, lowcut=1, soft=0.55, val=0.34),   # band 0.828 ac 0.655 pk 0.617
 "fbl_white_pollen": dict(span=0.36, lowcut=0, soft=0, val=0.34),   # band 0.848 ac 0.572 pk 0.547
 "fbl_white_whorl": dict(span=0.26, lowcut=0, soft=0, val=0.34),   # band 0.944 ac 0.619 pk 0.663
}

for _fid, _e in _TUNE.items():
    _e = dict(_e)
    _BLOOM[_fid]["val"] = _e.pop("val")
    _e["mid"] = _lut_steep(_BLOOM[_fid]["lut"], _e.get("span", 1.0))
    _BLOOM[_fid]["eargs"] = _e
# ════════════════════════════════════════════════════════════════════════════
# NAME ACCURACY — [SPB-FRACTURED-090c 2026-08-02] parent visual review.
# Flowers ARE saturated and that stays; what failed is that the colour a
# finish RENDERS was not the colour its NAME claims:
#   * fbl_white_pollen measured a saturation-weighted mean hue of 0.553 —
#     CYAN — against a "moon white" name, and fbl_white_whorl sat at hue
#     0.124 with chroma 0.97, which is ORANGE, not gardenia;
#   * the three butter ids ran chroma 0.99 at hue 0.10-0.12, i.e. ORANGE
#     rather than a soft pale yellow;
#   * fbl_coral_vine rendered at 0.139 (yellow-green) because its hero anchor
#     was the leaf, not the coral.
# The white and butter families get their own chroma — a pale flower is
# defined by LOW chroma, and no hue correction makes a chroma-1.0 pixel read
# pale — and three ids get corrected anchors. _HUEFIX is the MEASURED per-id
# correction from _fractured_triage/huefix.py: the LUT's hue distribution
# inside a hero window is asymmetric, so the anchor you SET is not the hue
# that RENDERS. Every id is held to <= 0.03 of a turn.
# All of it is luma-neutral (the hue window re-applies each pixel's own luma),
# so no band / coherence / peakiness / shape number moves.
# ════════════════════════════════════════════════════════════════════════════

_PALETTE = {
    # moon-white pollen: cream hero, straw, warm, ONE sparse moonlight blue
    "fbl_white_pollen": (0.105, 0.128, 0.085, 0.560),
    "fbl_white_whorl": (0.108, 0.145, 0.072, 0.545),      # gardenia cream
    # coral vine: the CORAL is the hero, the leaf green is the accent
    "fbl_coral_vine": (0.020, 0.040, 0.300, 0.090),
}
# fbl_coral_vine also gets its chroma pulled: a chroma-1.0 coral hero drives
# a big share of the field out of gamut, and the clip is where the hue window
# stops being luma-neutral — it cost this id 0.22 of car-band. 1.05 keeps the
# coral and gives the band back.
_SATF = {"white": 0.50, "butter": 0.62}
_SATID = {"fbl_coral_vine": 0.85}
_GRAYF = {"white": 0.26, "butter": 0.12}
# a pale family needs a WIDER intra-window travel to clear the >=5 hue-bin
# gate: at low chroma most pixels fall under the sat>0.15 cut, so the few that
# survive have to span more of the wheel (gardenia measured 4 bins at 0.05).
_HSPANF = {"white": 0.100}

_HUEFIX = {
 "fbl_blush_rose": +0.0201,
 "fbl_butter_mosaic": +0.0074,
 "fbl_butter_pollen": +0.0298,
 "fbl_butter_whorl": +0.0091,
 "fbl_coral_stamen": -0.0075,
 "fbl_coral_vine": -0.0366,
 "fbl_leaf_whorl": +0.0384,
 "fbl_lilac_stamen": -0.0088,
 "fbl_magenta_pollen": +0.0209,
 "fbl_magenta_whorl": +0.0080,
 "fbl_pink_pollen": +0.0469,
 "fbl_white_pollen": +0.0206,
 "fbl_white_whorl": +0.0161,
}

for _profile, (_fid, _d) in enumerate(_BLOOM.items()):
    # SPB-WILDS, tick 2 (2026-08-23). Owner: "Too much redundancy way too
    # similar looks. Must be VERY UNIQUE. And must have the 'Fractured' color
    # flipping stuff." Broad category-kit domains were the repeated macro
    # silhouette. wild_profile selects a unique six-family 8-32px signature;
    # final audited before->after movement is recorded beside KIT below.
    _d["id"] = _fid
    _d["wild_profile"] = _profile
    _d["wild_variant"] = _profile
    _d["vd"] = (0.48 + 0.02 * (_profile % 3), 1.26 - 0.02 * (_profile % 4))
    _d["tmod"] = 0.10
    _d["kw"]["ambient"] = 0.02
    _d["kw"]["sparkle"] = 0.08
    _fam = _fid.split("_")[1]
    if _fam in _SATF:
        _d["satboost"] = _SATF[_fam]
        _d["kw"]["gray"] = _GRAYF[_fam]
    if _fam in _HSPANF:
        _d["hspan"] = _HSPANF[_fam]
    if _fid in _SATID:
        _d["satboost"] = _SATID[_fid]
    # HERO-DOMINANT PALETTE [090b] — kintsugi's palette law. Four equal
    # anchors picked per feature is a confetti; 7/11 hero + 2 second + 1 each
    # for the accents is a flower colour with accents. Metric-neutral (the
    # hue window re-applies each pixel's own luma), pure look.
    _fx = float(_HUEFIX.get(_fid, 0.0))
    _h = [(_x + _fx) % 1.0 for _x in _PALETTE.get(_fid, _d["hues"])[:4]]
    _d["hues"] = [_h[0]] * 4 + [_h[1]] * 2 + [_h[2], _h[3]]
    _d["hspan"] = max(float(_d.get("hspan", 0.05)), 0.075 + 0.008 * (_profile % 5))
    _d["hue_levels"] = 0.9
    _d["hue_jit"] = 0.10
    _d["hue_blur"] = 3.2
    _d["hue_cell"] = max(float(_d.get("hue_cell", 8.0)), 14.0)

assert len(_BLOOM) == 20

GROUPS = {
    "FRACTURED BLOOM": _BLOOM,
}

# SPB-WILDS, tick 3 final audit (2026-08-23). Owner: "Too much redundancy way
# too similar looks. Must be VERY UNIQUE. And must have the 'Fractured' color
# flipping stuff." Native-2048 BLOOM+PETRI combined movement: hue-only
# chroma-layout NN median/max 70.589/76.274 -> 68.149/70.929 (lower is better);
# white-excluded opponent-hue travel median/min 12.767/0.678deg ->
# 113.679/59.557deg; materially occupied M/R/Cc tiers 7/6/4 -> 8/8/8 and final
# std floors 41.023/39.213/44.395. Render median/max 0.8603/1.2049s ->
# 1.4399/1.6327s. Isolated current-render M7 63.3-85.2 (1/40 >=85) ->
# 85.9-90.5 (40/40 >=85); INTERNAL machine/visual pass only. The owner had
# not reviewed this result and rejected its shared topology on 2026-08-24.
KIT = wildkit.FineFractureKit(engines=ENGINES, groups=GROUPS, tag="fractured-bloom",
                # [field 2026-08-02] gen 768 -> 640: every generator
                # scales its pitch by res/_S, so the look is identical
                # while the whole module gains ~30% render headroom.
                work=1024, gen=640)

ALL = KIT.ALL
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
