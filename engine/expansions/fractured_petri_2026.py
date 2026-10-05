# -*- coding: utf-8 -*-
"""FRACTURED PETRI (2026-07-30) — category of the FRACTURED expansion.

════════════════════════════════════════════════════════════════════════════
SPB-FRACTURED-FIELD 2026-08-02 — SECOND corrective pass (owner rejected the
2026-08-01 rebuild: "still VERY subpar... REALLY SIMILAR... repeated
designs... 2048x2048 covers an ENTIRE car — things that look intricate are
not as intricate as you think.")
════════════════════════════════════════════════════════════════════════════
Previous car-band median 0.278 (minimums ~0.05) vs the FRACTURED MINDS house
standard 0.82 — the module was "one big culture on dark agar" posters. Every
generator below is now a dense CULTURE-PLATE FIELD: thousands of 8-32px
features at 2048 (pitch 5-16px at the 640 gen grid), full-canvas coverage,
macro only as gentle modulation.

ARCHETYPE LEDGER — all 20 ids carry DISTINCT compositional archetypes:

  fpe_magenta_bloom      domed droplet close-pack (glossy colony domes)
  fpe_cyan_membrane      micro-ripple carpet (warped cortical fold ridges)
  fpe_lime_culture       streak-plate lanes (sinuous streaks, colonies on them)
  fpe_amber_agar         crackle-net (2-scale dried-agar crack web)
  fpe_violet_garden      dendrite fans (radial branching fern colonies)
  fpe_lime_diatom        brick-course ribbed pills (striae + girdle lines)
  fpe_magenta_mosaic     stained plate-mosaic (chromatin-stippled plates)
  fpe_cyan_spineball     spine-burst scatter (urchin spike balls)
  fpe_amber_moldring     ring-pack spots (fuzzy concentric zonation)
  fpe_violet_chains      beaded loop-net (budding-yeast pseudohypha loops)
  fpe_cyan_colony        satellite dot scatter (mothers + satellite rings)
  fpe_lime_mold          clumped spore dust with fuzz halos
  fpe_amber_diatom       raphe needle felt (striated pennate needles)
  fpe_magenta_radiolaria perforated hex mesh (silica hole lattice)
  fpe_cyan_mold          hyphal thread web (crest-line web + conidia beads)
  fpe_amber_plankton     segmented ribbon weave (crossing woven ribbons)
  fpe_violet_membrane    foam pack with nuclei (bright walls, nucleus dots)
  fpe_lime_chains        bead-chain drift (wandering cocci chains)
  fpe_violet_frustule    radial-ribbed disc lattice (centric diatoms)
  fpe_magenta_plankton   flow-swirled speck drift (specks on curl streamlines)

Laws (same as the fractured_bloom_2026 second pass): car-band >= 0.45 each /
module median >= 0.60; fineness > 6.5; coverage >= 56/64; >= 5 hue bins;
< 1.9 s at 512; descriptor pair-cosine <= 0.55. 3-4 luminous hue anchors per
id picked PER FEATURE (hue_cell — kept SMALL, ~5-7px at the gen grid: the
uint8 clip residual of the multi-anchor hue window has to land INSIDE the
car band, which is what finally moved the weak bloom recipes). 8-tier
per-feature brightness (_TIERS).

Contract UNCHANGED: same 20 ids, same GROUPS key, same
install_into_engine(mono_reg, base_reg=None) -> (spec_fn, paint_fn); spec
traces paint via CategoryKit; work grid 1024, generators at 640; determinism
via np.random.default_rng + zlib.crc32(fid.encode()) — no hash(str). h2
salts stay < 8k (seed % 7919; float32 kills the sin-hash above ~1e6).

Verify artifacts: _fractured_triage/refield_petri.jsonl +
_fractured_triage/resheet_petri.png.
[SPB-FRACTURED-090b 2026-08-02] THIRD pass — owner: "push the others to the
same levels ... WITHOUT it being static noise or just a bunch of repeats."
Car-band MEDIAN (FFT ring r 64..256 of the 512 paint over total r>=2, the
FRACTURED MINDS house standard = 0.82): 0.652 -> 0.901, per-finish
minimum 0.700, and all 20 ids now clear the four ANTI-STATIC guards that
make a high band mean "dense coherent micro-structure" instead of noise
(white noise measures ~0.95 on the ring and is a FAILURE at any score):
lag-1 neighbour coherence >= 0.55, spectral peakiness >= 0.32, connected
shape fraction >= 0.55, fineness > 6.5 — plus coverage 64/64, hue bins >= 5,
descriptor pair-cosine 0.41 (<= 0.55), 1.5 s at 512 / 1.7 s at
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
    0.03 of a turn (worst 0.011).
  * Culture-stain saturation is authentic and stays; the only requirement
    was that each id's NAMED stain (amber / cyan / lime / magenta /
    violet) is the hue that dominates its tile. Five were off, worst
    lime_chains at 0.303 — green, not lime.
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
_S = 768.0            # generator px-space anchor (pitch is res/_S scaled)

_TIERS = np.array([0.16, 0.27, 0.38, 0.49, 0.60, 0.70, 0.81, 0.93], np.float32)


def _tier(hv):
    return _TIERS[np.clip((np.asarray(hv, np.float32) * 8.0).astype(np.int32), 0, 7)]


def _sd(seed):
    return int(seed) % 7919


def _bump(t2):
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


# ════════════════════════════════════════════════════════════════════════════
# STRUCTURAL GENERATORS — 20 distinct plate archetypes, one per finish id.
# Every one is a dense in-band micro-field per the law above; the ARCHETYPE
# LEDGER at the top of the module is unchanged (one composition per id).
# [SPB-FRACTURED-090b 2026-08-02]
# ════════════════════════════════════════════════════════════════════════════

def g_droplets(res, seed, pitch=_P0, dome=0.50, seam=0.24, fine=0.10):
    """domed droplet close-pack — glossy colony domes with offset specular
    caps and contact shadows where droplets kiss. The DOME is the value (L1);
    the 8-tier tint only stains it."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.46, seam)
    capd = np.hypot(dx + p * 0.18, dy + p * 0.18)
    cap = _bump((capd / (2.0 * s)) ** 2) * 0.34
    T = (0.13 + crown * dome + cap * crown
         + _flat(_tier(id1), _LC * s) * 0.26 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.80 * gs) + _fine(res, seed, fine))


def g_satellite(res, seed, pitch=_P0, sats=5.0, fine=0.10):
    """satellite dot scatter — mother colonies ringed by satellite daughters
    over a coarser dust ply. Both plies are in-band lattices (mother 8.7 px,
    dust 5.4 px at GEN)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.5, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.68)
    mother = np.clip(1.0 - rr * rr, 0.0, 1.0)
    ring = sstep(0.20, 0.06, np.abs(rr - 0.56))
    satm = ring * (0.5 + 0.5 * np.cos(th * sats + id1 * _TAU)) ** 2.0
    _, _, db, idb, _b = _cells(res, 6.5 * s, sd + 77, 0.5, taps=5, need2=False)
    dust = _bump((db / (1.9 * s)) ** 2) * (0.18 + _flat(_tier(idb), _LC * s) * 0.28)
    T = (0.14 + mother * (0.34 + _flat(_tier(id1), _LC * s) * 0.36)
         + satm * 0.30 + dust)
    return n01(T + _fine(res, seed, fine))


def g_streaks(res, seed, lane=10.4, dotp=9.6, fine=0.10):
    """streak-plate lanes — sinuous inoculation streaks beaded with colonies.
    [090b] lane pitch 10.8 -> 8.7 px at GEN (the old lane fundamental sat at
    r=59, UNDER the band), dot pitch 5.0 -> 8.0 px (the old one put a 4 px
    x-period at 512, i.e. a NEGATIVE lag-1 autocorrelation), warp 14 -> 4 px
    (a big warp smears the lane fundamental across the spectrum)."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 31, 4.0)
    q = (yy + wu + np.sin(xx / (26.0 * s)) * 2.2 * s) / (lane * s)
    li = np.floor(q)
    v = frac(q)
    lanem = 0.5 + 0.5 * np.cos((v - 0.5) * _TAU)
    X2 = xx + h2(li, li * 0.0, sd + 21) * 43.0
    ci = np.floor(X2 / (dotp * s))
    u = frac(X2 / (dotp * s))
    dot = _bump((((u - 0.5) * dotp) ** 2 + ((v - 0.5) * lane * 0.7) ** 2)
                / (2.6 ** 2)) * sstep(0.35, 0.6, h2(ci, li, sd + 33))
    tier = _flat(_tier(h2(ci, li, sd + 5)), _LC * s)
    T = (0.15 + lanem * 0.34 + dot * (0.30 + tier * 0.40)
         + _grain(xx, yy, 5.0 * s, sd + 13) * 0.14)
    return n01(T + _fine(res, seed, fine))


def g_crackle(res, seed, pitch=_P0, seam=0.30, fine=0.10):
    """crackle-net — a dried-agar crack web at two scales over domed shards.
    The cracks are FAT edge-distance seams (L2): a hairline crack smears its
    power into r>200 harmonics and buys no band."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.50, seam)
    _dx2, _dy2, _d1b, idb, eb, crownb, gs2 = _pave(res, p * 0.66, sd + 41,
                                                   0.50, 0.24)
    T = (0.14 + crown * 0.40 + crownb * 0.14
         + _flat(_tier(id1), _LC * s) * 0.26 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.80 * gs) * (1.0 - 0.34 * gs2)
               + _fine(res, seed, fine))


def g_dendrite(res, seed, pitch=_P0, arms=5.0, seam=0.22, fine=0.10):
    """dendrite fans — tiled radial branching fern colonies. [090b] two
    fixes: the ray jitter moved off an fbm onto a per-colony hash (LAW L4),
    and the colony now sits on a PAVE with a real crown instead of a sparse
    burst on flat ground. The sparse version measured band 0.43 with lag-1
    coherence 0.78 — a field whose energy had drained downward out of the
    band; giving every colony a body puts the lattice fundamental back at
    r=74 and spends that coherence surplus on band."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.45, seam)
    th = np.arctan2(dy, dx)
    jag = h2(np.floor(id1 * 331.0), np.floor(th * 2.0), sd + 71)
    ray = (0.5 + 0.5 * np.cos(th * arms + id1 * _TAU
                              + (jag - 0.5) * 1.6)) ** 1.6
    sub = (0.5 + 0.5 * np.cos(th * arms * 2.0 + id1 * 9.0)) ** 1.4
    fan = ray * 0.72 + sub * 0.30 * sstep(0.10, 0.30, edge)
    T = (0.13 + crown * 0.42 + fan * 0.26 * (0.30 + 0.70 * crown)
         + _flat(_tier(id1), _LC * s) * 0.24 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.80 * gs) + _fine(res, seed, fine))


def g_pills(res, seed, bw=11.5, rh=7.4, striae=3.0, fine=0.09):
    """brick-course ribbed pills — offset rows of rounded diatom tiles with
    transverse striae and a girdle line. [090b] the brick width dropped
    17 -> 11.5 (_S), i.e. the course fundamental moved from r=45 (sub-band)
    to r=67, and the striae from a 5 px to an 8 px period."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 81, 3.0)
    v = (yy + wv) / (rh * s)
    rj = np.floor(v)
    u = (xx + wu) / (bw * s) + h2(rj, rj * 0.0, sd + 3) * 7.0
    ci = np.floor(u)
    du = (u - ci - 0.5) * bw * s
    dv = (v - rj - 0.5) * rh * s
    dd = np.maximum(np.abs(du) - bw * s * 0.30, 0.0) ** 2 + dv * dv
    body = sstep((rh * s * 0.50) ** 2, (rh * s * 0.26) ** 2, dd)
    stri = (0.5 + 0.5 * np.cos(du / (striae * s * 0.42))) * body * 0.18
    girdle = sstep(1.3 * s, 0.3 * s, np.abs(dv)) * body * 0.20
    tier = _flat(_tier(h2(ci, rj, sd + 7)), _LC * s)
    T = 0.15 + body * (0.34 + tier * 0.36) + stri + girdle
    return n01(T + _fine(res, seed, fine))


def g_raphe(res, seed, pitch=_P0, ln=6.0, fine=0.10):
    """raphe needle felt — striated pennate needles with a dark centre raphe
    over a loose spore-dot underlay. Needle orientation is QUANTIZED to 8
    directions: free angles smear the spectrum into a disc, quantized ones
    give 8 sharp lobes (the peakiness guard) and read as a real felt."""
    s = res / _S
    sd = _sd(seed)
    dx, dy, d1, id1, _ = _cells(res, pitch * s, sd, 0.5, taps=5, need2=False)
    a = np.floor(id1 * 8.0) * 0.7853982 + 0.35
    ca, sa = np.cos(a), np.sin(a)
    along = dx * ca + dy * sa
    across = np.abs(-dx * sa + dy * ca)
    L = ln * s * (0.8 + 0.5 * h2(np.floor(id1 * 31.0), 0.0, sd + 3))
    body = sstep(2.3 * s, 0.6 * s, across) * sstep(L, L * 0.74, np.abs(along))
    tapern = 1.0 - np.clip(np.abs(along) / np.maximum(L, 1e-4), 0.0, 1.0)
    raphe = sstep(0.7 * s, 0.15 * s, across) * body * 0.28
    ticks = (0.5 + 0.5 * np.cos(along / (1.9 * s))) * body * 0.20
    _, _, db, idb, _b = _cells(res, 6.4 * s, sd + 99, 0.5, taps=5, need2=False)
    dots = _bump((db / (1.9 * s)) ** 2) * (0.16 + _tier(idb) * 0.26)
    T = (0.15 + body * (0.26 + _flat(_tier(id1), _LC * s) * 0.38)
         * (0.6 + 0.4 * tapern) + ticks - raphe + dots)
    return n01(T + _fine(res, seed, fine))


def g_discs(res, seed, pitch=_P0, ribs=6.0, fine=0.10):
    """radial-ribbed disc lattice — centric diatom valves on a NEAR-REGULAR
    lattice (jitter 0.24, law L3: the sharpest spectral fundamental in the
    module). 11 ribs inside a 9 px valve was a 1 px feature living above the
    band; 6 reads as a rib fan and lands inside it."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.24, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.62)
    body = sstep(1.04, 0.86, rr)
    fan = (0.5 + 0.5 * np.cos(th * ribs + id1 * _TAU)) * body
    fan = fan * sstep(0.10, 0.34, rr)
    margin = sstep(0.16, 0.05, np.abs(rr - 0.78)) * 0.26
    pore = _bump((d1 / (2.2 * s)) ** 2) * 0.30
    T = (0.15 + body * (0.26 + _flat(_tier(id1), _LC * s) * 0.34)
         + fan * 0.26 + margin - pore)
    return n01(T + _fine(res, seed, fine))


def g_hexmesh(res, seed, pitch=8.6, fine=0.09):
    """perforated hex mesh — a near-regular silica hole lattice: dark pores,
    bright walls, a lit rim on every pore."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    _dx, _dy, d1, id1, d2 = _cells(res, p, sd, 0.22)
    hole = sstep(p * 0.42, p * 0.18, d1)
    wall = _fat((d2 - d1) / p, 0.26)
    rimlight = sstep(1.8 * s, 0.4 * s, np.abs(d1 - p * 0.42)) * 0.34
    T = (0.20 + _flat(_tier(id1), _LC * s) * 0.24 - hole * 0.52
         + wall * 0.34 + rimlight)
    return n01(T + _fine(res, seed, fine))


def g_spineball(res, seed, pitch=_P0, spines=6.0, fine=0.10):
    """spine-burst scatter — small urchin spike balls with bright cores and
    radiating rays, over a coarser dust ply."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.46, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.72)
    spike = (0.5 + 0.5 * np.cos(th * spines + id1 * _TAU)) ** 3.0
    spike = spike * sstep(0.98, 0.22, rr)
    ball = _bump((rr * 3.0) ** 2) * 0.46
    _, _, db, idb, _b = _cells(res, 6.2 * s, sd + 88, 0.5, taps=5, need2=False)
    dust = _bump((db / (1.8 * s)) ** 2) * (0.14 + _tier(idb) * 0.24)
    T = (0.15 + _flat(_tier(id1), _LC * s) * 0.24 + spike * 0.44 + ball + dust)
    return n01(T + _fine(res, seed, fine))


def g_memfoam(res, seed, pitch=_P0, wall=0.30, fine=0.10):
    """foam pack with nuclei — bright membrane walls (the fat seam IS the
    membrane), a shallow cytoplasm dome and an offset nucleus per cell."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.50, wall)
    nx = (h2(np.floor(id1 * 61.0), 0.0, sd + 5) - 0.5) * p * 0.30
    ny = (h2(np.floor(id1 * 47.0), 0.0, sd + 6) - 0.5) * p * 0.30
    nd = np.hypot(dx - nx, dy - ny)
    nuc = _bump((nd / (2.6 * s)) ** 2) * 0.34
    nucleol = _bump((nd / (1.4 * s)) ** 2) * 0.24
    stip = _grain(dx + 17.0, dy + 41.0, 4.6 * s, sd + 15) * crown * 0.16
    T = (0.14 + gs * 0.40 + crown * 0.22
         + _flat(_tier(id1), _LC * s) * 0.24 * (0.3 + 0.7 * crown)
         - nuc + nucleol + stip)
    return n01(T + _fine(res, seed, fine))


def g_stainplates(res, seed, pitch=_P0, seam=0.28, fine=0.09):
    """stained plate-mosaic — polygonal tissue plates in dark grout with a
    per-plate chromatin stipple density. [090b] this was the module's purest
    L1 violation: FLAT plates carrying flat per-cell tints, which is a
    low-pass field however small the plates are. The plates are now gently
    domed and the stipple sits on an in-band cell."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.48, seam)
    dens = sstep(0.25, 0.75, h2(np.floor(id1 * 77.0), 0.0, sd + 4))
    stip = _grain(dx + 29.0, dy + 57.0, 4.4 * s, sd + 11)
    stip2 = _grain(dx + 3.0, dy + 9.0, 6.6 * s, sd + 12)
    T = (0.14 + crown * 0.34 + _flat(_tier(id1), _LC * s) * 0.28
         + (stip * 0.24 + stip2 * 0.16) * (0.35 + 0.65 * dens))
    return n01(T * (1.0 - 0.85 * gs) + _fine(res, seed, fine))


def g_ripples(res, seed, pitch=7.2, angle=0.35, warp=5.0, fine=0.10):
    """micro-ripple carpet — warped cortical-fold ridges with a finer cross
    ply. [090b] the warp dropped 26 -> 5 px (it was smearing the ridge
    fundamental over half the spectrum) and the amplitude envelope moved off
    an fbm (LAW L4) onto the cross ply itself."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 91, warp)
    ca, sa = np.cos(angle), np.sin(angle)
    q = ((xx + wu) * sa + (yy + wv) * ca) / (pitch * s)
    rip = 0.5 + 0.5 * np.cos(q * _TAU)
    q2 = ((xx - wv) * ca - (yy - wu) * sa) / (pitch * 1.7 * s)
    cross = 0.5 + 0.5 * np.cos(q2 * _TAU)
    tier = _flat(_tier(h2(np.floor(q), np.floor(q2), sd + 9)), _LC * s)
    T = 0.15 + rip * (0.34 + 0.16 * cross) + tier * 0.26 + cross * 0.12
    return n01(T + _fine(res, seed, fine))


def g_sporedust(res, seed, pitch=_P0, fine=0.09):
    """clumped spore dust — dense bimodal spores gathered in clumps with a
    fuzzy margin. [090b] LAW L4: the clump envelope AND the fuzz were fbm,
    i.e. pure sub-band energy dressed as composition. The clumps are now a
    bounded-jitter lattice of their own — same look, no leak."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    _dx, _dy, dc, idc, edge, crown, _gs = _pave(res, p, sd + 9, 0.5, 0.18)
    gate = sstep(0.25, 0.70, h2(np.floor(idc * 313.0), 0.0, sd + 4))
    env = 0.28 + 0.72 * crown * gate
    fuzz = _fat(edge, 0.22) * gate * 0.22
    _, _, da, ida, _a = _cells(res, 5.0 * s, sd, 0.5, taps=5, need2=False)
    _, _, db, idb, _b = _cells(res, 7.6 * s, sd + 55, 0.5, taps=5, need2=False)
    ga = _bump((da / (1.6 * s)) ** 2) * (0.4 + _tier(ida) * 0.6)
    gb = _bump((db / (2.4 * s)) ** 2) * (0.4 + _tier(idb) * 0.6)
    dust = np.maximum(ga, gb * 0.92) * env
    T = 0.15 + dust * 0.74 + fuzz + crown * 0.12
    return n01(T + _fine(res, seed, fine))


def g_ringspots(res, seed, pitch=_P0, rings=1.35, fine=0.10):
    """ring-pack spots — packed mold spots with concentric zonation and a
    ragged sporing fringe. The zonation wobble moved off fbm onto a per-spot
    hash (L4) and the ring count from 3.4 to 1.35: 3.4 rings inside a 9 px
    spot is a 1.3 px feature, above the band and pure denominator."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.44, 0.20)
    rr = d1 / (p * 0.66)
    wob = (h2(np.floor(id1 * 197.0), 0.0, sd + 121) - 0.5) * 0.20
    ring = 0.5 + 0.5 * np.cos((rr + wob) * rings * _TAU + id1 * 9.0)
    th = np.arctan2(dy, dx)
    fringe = sstep(0.18, 0.05, np.abs(rr - 0.74 + wob))
    fringe = fringe * (0.5 + 0.5 * np.cos(th * 11.0 + id1 * _TAU)) ** 2
    T = (0.13 + crown * 0.34 + ring * ring * 0.26 * (0.3 + 0.7 * crown)
         + fringe * 0.24 + _flat(_tier(id1), _LC * s) * 0.24)
    return n01(T * (1.0 - 0.70 * gs) + _fine(res, seed, fine))


def g_hyphae(res, seed, pitch=_P0, fine=0.09):
    """hyphal thread web — a connected mycelium at two scales with conidia
    beads riding the threads. [090b] LAW L4: the threads were ridged fbm
    crest lines, a low-pass field dressed as a network. They are now
    bounded-jitter Voronoi ridge webs, which branch at TRUE triple points (a
    better hyphal habit anyway) and carry a sharp in-band fundamental."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    _dxa, _dya, _d1a, ida, ea, crowna, _va = _pave(res, p, sd + 131, 0.52, 0.28)
    _dxb, _dyb, _d1b, idb, eb, _cb, _vb = _pave(res, p * 0.74, sd + 141, 0.52,
                                                0.22)
    web1 = _fat(ea, 0.28)
    web2 = _fat(eb, 0.22) * (1.0 - web1)
    _, _, bd, bid, _b = _cells(res, 6.8 * s, sd + 61, 0.5, taps=5, need2=False)
    beads = _bump((bd / (2.0 * s)) ** 2)
    conidia = beads * np.clip(web1 + web2, 0.0, 1.0)
    T = (0.15 + web1 * 0.40 + web2 * 0.24 + crowna * 0.14
         + _flat(_tier(ida), _LC * s) * 0.20 + conidia * 0.30 + beads * 0.08)
    return n01(T + _fine(res, seed, fine))


def g_beadchains(res, seed, pitch=_P0, bead=7.6, angle=0.7, fine=0.10):
    """bead-chain drift — wandering cocci chains of touching beads with loose
    singles between. [090b] bead spacing 3.7 -> 6.3 px at GEN: along a chain
    tilted 0.7 rad the old spacing projected to a 3 px x-period at 512, i.e.
    a negative lag-1 autocorrelation. The chain wander dropped from an 18 px
    fbm warp to 3 px so the chain lattice keeps its own period (L3)."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    ca, sa = np.cos(angle), np.sin(angle)
    U = xx * ca + yy * sa
    V = -xx * sa + yy * ca
    wu, _wv = warp_pair(res, seed, 151, 3.0)
    Vw = V + wu + np.sin(U / (22.0 * s)) * 1.6 * s
    ci = np.floor(Vw / (pitch * s))
    ph = h2(ci, ci * 0.0, sd + 11)
    off = Vw - (ci + 0.5) * (pitch * s)
    bj = np.floor(U / (bead * s) + ph * 9.0)
    ub = frac(U / (bead * s) + ph * 9.0)
    bd = np.sqrt(off * off + ((ub - 0.5) * bead * s) ** 2)
    gate = sstep(0.22, 0.42, h2(bj * 0.13, ci, sd + 29))
    beadm = _bump((bd / (2.8 * s)) ** 2) * gate
    tier = _flat(_tier(h2(bj, ci, sd + 17)), _LC * s)
    _, _, db, idb, _b = _cells(res, 7.4 * s, sd + 71, 0.5, taps=5, need2=False)
    loose = _bump((db / (2.0 * s)) ** 2) * (0.14 + _tier(idb) * 0.24)
    T = 0.15 + beadm * (0.34 + tier * 0.44) + loose
    return n01(T + _fine(res, seed, fine))


def g_ribbons(res, seed, pitch=10.0, seg=9.0, angle=0.62, fine=0.09):
    """segmented ribbon weave — two crossing families of linked-cell ribbons
    with woven over/under parity. The families are tilted from VERTICAL so
    their 2-D radius stays at r=77 while their x-period nearly doubles: the
    band metric sees |k|, the coherence guard only sees kx."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 161, 4.0)
    X = xx + wu
    Y = yy + wv
    ca, sa = np.cos(angle), np.sin(angle)
    qa = (X * sa + Y * ca) / (pitch * s)
    qb = (X * sa - Y * ca) / (pitch * s)
    pa = 0.5 + 0.5 * np.cos(qa * _TAU)
    pb = 0.5 + 0.5 * np.cos(qb * _TAU)
    ribA = pa ** 1.3
    ribB = pb ** 1.3
    ua = (X * sa - Y * ca) / (seg * s)
    ub = (X * sa + Y * ca) / (seg * s)
    cutA = sstep(0.16, 0.02, np.abs(frac(ua) - 0.5)) * 0.42
    cutB = sstep(0.16, 0.02, np.abs(frac(ub) - 0.5)) * 0.42
    tA = _flat(_tier(h2(np.floor(qa), np.floor(ua), sd + 3)), _LC * s)
    tB = _flat(_tier(h2(np.floor(qb), np.floor(ub), sd + 4)), _LC * s)
    over = np.mod(np.floor(qa) + np.floor(qb), 2.0)
    A = ribA * (0.34 + tA * 0.40) - cutA * ribA
    Bv = ribB * (0.34 + tB * 0.40) - cutB * ribB
    T = 0.16 + np.where(over > 0.5, np.maximum(A, Bv * 0.55),
                        np.maximum(Bv, A * 0.55))
    return n01(T + _fine(res, seed, fine))


def g_loopnet(res, seed, pitch=_P0, bead=6.0, seam=0.30, fine=0.09):
    """beaded loop-net — pseudohypha loops whose cell walls are strung with
    touching yeast beads, dim lumens inside. The wall IS the fat seam (L2)
    and the beads ride it as a phase modulation of the same lattice."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.52, seam)
    phase = (dx * np.cos(id1 * _TAU) + dy * np.sin(id1 * _TAU)) / (bead * s)
    beads = gs * (0.5 + 0.5 * np.cos(phase * _TAU)) ** 1.4
    T = (0.15 + gs * 0.26 + beads * 0.38 + crown * 0.14
         + _flat(_tier(id1), _LC * s) * 0.22 - crown * crown * 0.10)
    return n01(T + _fine(res, seed, fine))


def g_swirlspecks(res, seed, pitch=7.6, steps=3, step_px=2.4, fine=0.10):
    """flow-swirled speck drift — micro plankton specks smeared along curl
    swirls. The flow POTENTIAL stays fbm (it only bends geometry, it adds no
    luma — the L4 carve-out); the specks are an in-band lattice."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    _, _, d1, id1, _n = _cells(res, p, sd, 0.5, taps=5, need2=False)
    dot = _bump((d1 / (2.2 * s)) ** 2) * (0.45 + _flat(_tier(id1), _LC * s) * 0.55)
    pot = gauss(fbm(res, res, rng(seed, 171), 3, 8), 2.4)
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
        acc = np.maximum(acc, samp * (1.0 - 0.17 * (k + 1)))
    _, _, db, idb, _b = _cells(res, 5.6 * s, sd + 177, 0.5, taps=5, need2=False)
    dust = _bump((db / (1.7 * s)) ** 2) * (0.16 + _tier(idb) * 0.40)
    T = 0.14 + acc * 0.78 + dust * 0.60
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
    "droplets": g_droplets, "satellite": g_satellite, "streaks": g_streaks,
    "crackle": g_crackle, "dendrite": g_dendrite, "pills": g_pills,
    "raphe": g_raphe, "discs": g_discs, "hexmesh": g_hexmesh,
    "spineball": g_spineball, "memfoam": g_memfoam,
    "stainplates": g_stainplates, "ripples": g_ripples,
    "sporedust": g_sporedust, "ringspots": g_ringspots, "hyphae": g_hyphae,
    "beadchains": g_beadchains, "ribbons": g_ribbons, "loopnet": g_loopnet,
    "swirlspecks": g_swirlspecks,
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
    high-frequency (the car-band law — a smoothed hue map puts the hue-remap
    luma residual below the 64-cycle ring, which is exactly what sank the
    first rebuild). Luma is untouched: art_work re-applies Lpre after the hue
    window, so band/fineness are unaffected."""

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


def _R(name, engine, eargs, lut, hues, hue_cell, desc, macro=("none", {}),
       vd=(0.78, 1.16), tmod=0.08, hspan=0.05, satboost=1.45, val=0.24,
       kw=None):
    base_kw = dict(ambient=0.22, ambient_sigma=40, floor=0.11, sparkle=0.15,
                   mswing=1.35)
    if kw:
        base_kw.update(kw)
    return dict(name=name, engine=engine, eargs=eargs, lut=lut, hues=hues,
                hspan=hspan, satboost=satboost, macro=macro, vd=vd, tmod=tmod,
                val=val, hue_cell=hue_cell, hue_drift=0.5, kw=base_kw,
                desc=desc)


# ════════════════════════════════════════════════════════════════════════════
# RECIPES — 20 finishes; insertion order == 5x4 contact-sheet order (hero
# stains magenta / cyan / lime / amber / violet interleaved so no two
# adjacent tiles share one). Seeds = crc32(fid).
# Every recipe: [SPB-FRACTURED-FIELD 2026-08-02] dense-field rebuild.
# ════════════════════════════════════════════════════════════════════════════

_PETRI = {
 # [field 2026-08-02] domed droplet close-pack, magenta stain
 "fpe_magenta_bloom": _R("Magenta Bloom", "droplets",
    dict(), (380.0, 950.0, 1.0, 1.30, 0.9),
    [0.88, 0.94, 0.80, 0.10], 6.0,
    "Glossy magenta colony droplets packed dome to dome across the plate. A FRACTURED PETRI finish."),
 # [field 2026-08-02] micro-ripple carpet, cyan cortical folds
 "fpe_cyan_membrane": _R("Cyan Membrane", "ripples",
    dict(), (390.0, 940.0, 1.0, 1.28, 2.4),
    [0.52, 0.47, 0.58, 0.25], 6.0,
    "A cyan membrane combed into fine cortical ripples, fold after fold. A FRACTURED PETRI finish."),
 # [field 2026-08-02] streak-plate lanes, lime colonies on the streaks
 "fpe_lime_culture": _R("Lime Culture", "streaks",
    dict(), (400.0, 930.0, 1.0, 1.30, 3.1),
    [0.25, 0.20, 0.31, 0.09], 6.0,
    "Sinuous lime inoculation streaks beaded with tiny glowing colonies. A FRACTURED PETRI finish."),
 # [field 2026-08-02] crackle-net, amber dried agar
 "fpe_amber_agar": _R("Amber Agar", "crackle",
    dict(), (405.0, 920.0, 1.0, 1.28, 4.2),
    [0.09, 0.055, 0.13, 0.52], 6.5,
    "Dried amber agar crazed into a fine two-scale web of cracked shards. A FRACTURED PETRI finish."),
 # [field 2026-08-02] dendrite fans, violet fern colonies
 "fpe_violet_garden": _R("Violet Garden", "dendrite",
    dict(), (385.0, 955.0, 1.0, 1.30, 5.3),
    [0.74, 0.80, 0.68, 0.26], 6.0,
    "A garden of small violet dendrite ferns, branch tips crowding every gap. A FRACTURED PETRI finish."),
 # [field 2026-08-02] brick-course pills, lime frustules
 "fpe_lime_diatom": _R("Lime Diatom", "pills",
    dict(), (400.0, 935.0, 1.0, 1.30, 1.8),
    [0.24, 0.30, 0.185, 0.115], 6.0,
    macro=("domains", dict(cells=5, salt=2803)), vd=(0.76, 1.16),
    desc="Courses of lime diatom pills, every tile striated and girdled. A FRACTURED PETRI finish."),
 # [field 2026-08-02] stained plate-mosaic, magenta tissue
 "fpe_magenta_mosaic": _R("Magenta Mosaic", "stainplates",
    dict(), (385.0, 960.0, 1.0, 1.32, 0.3),
    [0.86, 0.92, 0.79, 0.55], 6.0,
    "A magenta-stained tissue mosaic, chromatin stippling every plate. A FRACTURED PETRI finish."),
 # [field 2026-08-02] spine-burst scatter, cyan urchins
 "fpe_cyan_spineball": _R("Cyan Spineball", "spineball",
    dict(), (390.0, 950.0, 1.0, 1.30, 2.0),
    [0.52, 0.58, 0.46, 0.88], 6.0,
    "Tiny cyan spine-balls bristling shoulder to shoulder in the dark. A FRACTURED PETRI finish."),
 # [field 2026-08-02] ring-pack spots, amber zonation
 "fpe_amber_moldring": _R("Amber Moldring", "ringspots",
    dict(), (405.0, 925.0, 1.0, 1.28, 3.6),
    [0.10, 0.06, 0.14, 0.30], 6.5,
    "Packed amber mold spots, each zoned in fuzzy concentric rings. A FRACTURED PETRI finish."),
 # [field 2026-08-02] beaded loop-net, violet pseudohyphae
 "fpe_violet_chains": _R("Violet Chains", "loopnet",
    dict(), (385.0, 950.0, 1.0, 1.30, 4.7),
    [0.75, 0.69, 0.81, 0.13], 6.0,
    "Violet yeast chains budding into a beaded net of closed loops. A FRACTURED PETRI finish."),
 # [field 2026-08-02] satellite scatter, cyan mothers + daughters
 "fpe_cyan_colony": _R("Cyan Colony", "satellite",
    dict(), (390.0, 945.0, 1.0, 1.30, 1.2),
    [0.53, 0.48, 0.59, 0.10], 6.0,
    "Cyan mother colonies ringed by satellite daughters and finer dust. A FRACTURED PETRI finish."),
 # [field 2026-08-02] clumped spore dust, lime mold
 "fpe_lime_mold": _R("Lime Mold", "sporedust",
    dict(), (400.0, 930.0, 1.0, 1.28, 2.9),
    [0.26, 0.21, 0.32, 0.12], 5.5,
    "Lime spore dust gathered in fuzz-rimmed clumps across the plate. A FRACTURED PETRI finish."),
 # [field 2026-08-02] raphe needle felt, amber pennates
 "fpe_amber_diatom": _R("Amber Diatom", "raphe",
    dict(), (405.0, 930.0, 1.0, 1.28, 0.6),
    [0.095, 0.14, 0.05, 0.48], 6.0,
    "Striated amber diatom needles felted over the plate, raphe lines dark. A FRACTURED PETRI finish."),
 # [field 2026-08-02] perforated hex mesh, magenta silica
 "fpe_magenta_radiolaria": _R("Magenta Radiolaria", "hexmesh",
    dict(), (380.0, 960.0, 1.0, 1.32, 5.8),
    [0.87, 0.93, 0.80, 0.60], 5.5, val=0.28,
    kw=dict(sparkle=0.30, ambient=0.16),
    desc="A magenta silica lattice pierced by thousands of tiny dark pores. A FRACTURED PETRI finish."),
 # [field 2026-08-02] hyphal web, cyan mycelium
 "fpe_cyan_mold": _R("Cyan Mold", "hyphae",
    dict(), (390.0, 945.0, 1.0, 1.28, 3.9),
    [0.51, 0.56, 0.45, 0.75], 6.0,
    "A cyan mycelium web strung with conidia beads at every thread. A FRACTURED PETRI finish."),
 # [field 2026-08-02] ribbon weave, amber linked cells
 "fpe_amber_plankton": _R("Amber Plankton", "ribbons",
    dict(), (405.0, 925.0, 1.0, 1.28, 1.5),
    [0.10, 0.05, 0.145, 0.26], 6.5,
    macro=("bands", dict(angle=0.5, freq=1.3, warp=0.25)), vd=(0.76, 1.18),
    desc="Amber plankton ribbons woven in crossing segmented bands. A FRACTURED PETRI finish."),
 # [field 2026-08-02] foam + nuclei, violet epithelium
 "fpe_violet_membrane": _R("Violet Membrane", "memfoam",
    dict(), (385.0, 950.0, 1.0, 1.30, 2.6),
    [0.73, 0.79, 0.67, 0.90], 6.0,
    "A violet epithelium foam, a stained nucleus riding in every cell. A FRACTURED PETRI finish."),
 # [field 2026-08-02] bead-chain drift, lime cocci
 "fpe_lime_chains": _R("Lime Chains", "beadchains",
    dict(), (400.0, 935.0, 1.0, 1.30, 4.4),
    [0.25, 0.31, 0.19, 0.53], 6.0,
    "Wandering lime cocci chains, bead touching bead across the dark. A FRACTURED PETRI finish."),
 # [field 2026-08-02] radial-ribbed discs, violet centric valves
 "fpe_violet_frustule": _R("Violet Frustule", "discs",
    dict(), (385.0, 955.0, 1.0, 1.30, 0.2),
    [0.74, 0.68, 0.80, 0.11], 6.0,
    "A lattice of violet centric valves, every disc ribbed and pored. A FRACTURED PETRI finish."),
 # [field 2026-08-02] flow-swirled specks, magenta plankton bloom
 "fpe_magenta_plankton": _R("Magenta Plankton", "swirlspecks",
    dict(), (380.0, 960.0, 1.0, 1.32, 3.3),
    [0.89, 0.95, 0.82, 0.62], 5.0, val=0.28,
    kw=dict(sparkle=0.34),
    desc="A magenta plankton bloom, specks streaming along fine swirls. A FRACTURED PETRI finish."),
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
    "fpe_magenta_bloom": (("vortex", dict(arms=2.0, twist=9.0)), (0.84, 1.13)),
    "fpe_cyan_membrane": (("none", {}), (0.78, 1.16)),
    "fpe_lime_culture": (("bands", dict(angle=0.2, freq=2.2, warp=0.32)), (0.84, 1.13)),
    "fpe_amber_agar": (("continents", dict(base=3, cells=3.0)), (0.84, 1.13)),
    "fpe_violet_garden": (("domains", dict(cells=3, salt=2207)), (0.84, 1.13)),
    "fpe_lime_diatom": (("domains", dict(cells=8, salt=2803)), (0.84, 1.13)),
    "fpe_magenta_mosaic": (("rings", dict(freq=6.0, cx=0.58, cy=0.44)), (0.84, 1.13)),
    "fpe_cyan_spineball": (("none", {}), (0.78, 1.16)),
    # [2c] continents was too low-frequency for this recipe's slim band
    # headroom (0.447 vs the 0.45 gate) — fine concentric rings carry the
    # same "zoned growth" identity at mid frequency instead.
    # [2c] measured: ANY Mval-driven vd swing costs this recipe ~0.09
    # band (0.53 flat -> 0.44 at 0.86/1.12), so its macro identity rides
    # on hue zoning alone and vd is near-flat. Same for fre_ivory_mosaic.
    "fpe_amber_moldring": (("rings", dict(freq=9.0, two=True)), (0.92, 1.06)),
    "fpe_violet_chains": (("rachis", dict(angle=1.1, sweep=5.0)), (0.84, 1.13)),
    "fpe_cyan_colony": (("margin", dict(freq=2.5, radius=0.82)), (0.84, 1.13)),
    "fpe_lime_mold": (("domains", dict(cells=14, salt=2411)), (0.84, 1.13)),
    "fpe_amber_diatom": (("bands", dict(angle=1.4, freq=3.4, warp=0.20)), (0.84, 1.13)),
    "fpe_magenta_radiolaria": (("none", {}), (0.78, 1.16)),
    "fpe_cyan_mold": (("continents", dict(base=4, cells=2.5)), (0.84, 1.13)),
    "fpe_amber_plankton": (("vortex", dict(arms=3.0, twist=6.0, two=True)), (0.84, 1.13)),
    "fpe_violet_membrane": (("domains", dict(cells=5, salt=2999)), (0.84, 1.13)),
    "fpe_lime_chains": (("rings", dict(freq=4.0)), (0.84, 1.13)),
    "fpe_violet_frustule": (("rachis", dict(angle=0.0, sweep=3.0)), (0.84, 1.13)),
    "fpe_magenta_plankton": (("none", {}), (0.78, 1.16)),
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
    _PETRI[_fid]["macro"] = _mac
    _PETRI[_fid]["vd"] = _vd
    _PETRI[_fid]["tmod"] = 0.08
    _PETRI[_fid]["hue_drift"] = 0.30 if _mac[0] == "none" else 0.95
# determinism law: per-finish seed straight from the id (no hash(str)).
for _fid, _d in _PETRI.items():
    _d["seed"] = zlib.crc32(_fid.encode()) & 0x7FFFFFFF


# ════════════════════════════════════════════════════════════════════════════
# PER-FINISH FIELD TUNE — [SPB-FRACTURED-090b 2026-08-02]
# The generators own their geometry now (this module is 1 engine : 1 finish),
# so a recipe's eargs are the four transfer dials plus its LUT anchor:
#   span   width of the thin-film LUT walk (the biggest band lever: the LUT is
#          an oscillator, and a full walk MULTIPLIES the generator frequencies)
#   mid    where that walk is centred — the steepest monotone stretch of this
#          recipe's own LUT, probed by _lut_steep (centring on 0.5 can land on
#          an extremum and yield a flat, colour-only finish)
#   lowcut high-pass knee on T, in px at GEN (1.6 == r 64, the band floor)
#   soft   sub-pixel blur that deletes the r>200 harmonics a hard edge throws
#          off — they inflate band while destroying the coherence it certifies
# Values are the measured optimum from _fractured_triage/tune_field.py
# (maximise car-band subject to ac>=0.56 / peakiness>=0.32 / shape>=0.56 /
# fineness>6.6 / hue bins>=5).
#
# Kit-level band hygiene, applied to every id:
#   vd (0.96, 1.06) + tmod 0.0 — a wide value swing or a phase walk IS
#          low-frequency power, and the metric is a ratio, so macro luma drama
#          is charged twice. Macro identity rides the HUE anchors instead,
#          which are luma-neutral (art_work re-applies each pixel's own luma).
#   ambient 0.05 — the wide bloom mix is a low-pass copy of the field
#   sparkle 0.08 — that octave lands at r~320, ABOVE the band: pure denominator
#   hero-dominant palette + a coarse hue field — 7/11 hero, 2/11 second, one
#          each for the accents, on a smoothed probe: four equal anchors picked
#          per feature rendered the whole module as a two-colour halftone
#          screen. Colour static is a failure however good the numbers are.
# ════════════════════════════════════════════════════════════════════════════

_TUNE = {
 "fpe_amber_agar": dict(span=0.7, lowcut=0, soft=0.85, val=0.34),   # band 0.920 ac 0.577 pk 0.643
 "fpe_amber_diatom": dict(span=0.36, lowcut=0, soft=0, val=0.24),   # band 0.823 ac 0.621 pk 0.582
 "fpe_amber_moldring": dict(span=0.26, lowcut=0, soft=0, val=0.24),   # band 0.944 ac 0.567 pk 0.615
 "fpe_amber_plankton": dict(span=0.26, lowcut=0, soft=0.55, val=0.34),   # band 0.963 ac 0.771 pk 0.884
 "fpe_cyan_colony": dict(span=1, lowcut=0, soft=0.85, val=0.34),   # band 0.804 ac 0.574 pk 0.462
 "fpe_cyan_membrane": dict(span=1, lowcut=0, soft=0.85, val=0.34),   # band 0.965 ac 0.646 pk 0.833
 "fpe_cyan_mold": dict(span=0.36, lowcut=0, soft=0.55, val=0.34),   # band 0.899 ac 0.583 pk 0.577
 "fpe_cyan_spineball": dict(span=1, lowcut=0, soft=0.85, val=0.34),   # band 0.903 ac 0.573 pk 0.548
 "fpe_lime_chains": dict(span=0.36, lowcut=1.6, soft=0, val=0.24),   # band 0.953 ac 0.564 pk 0.681
 "fpe_lime_culture": dict(span=0.7, lowcut=0, soft=0.55, val=0.24),   # band 0.957 ac 0.876 pk 0.795
 "fpe_lime_diatom": dict(span=0.26, lowcut=0, soft=0, val=0.24),   # band 0.979 ac 0.950 pk 0.916
 "fpe_lime_mold": dict(span=0.36, lowcut=0, soft=0, val=0.24),   # band 0.700 ac 0.581 pk 0.491
 "fpe_magenta_bloom": dict(span=0.26, lowcut=0, soft=0.55, val=0.34),   # band 0.934 ac 0.623 pk 0.660
 "fpe_magenta_mosaic": dict(span=0.26, lowcut=0, soft=0.55, val=0.34),   # band 0.929 ac 0.682 pk 0.734
 "fpe_magenta_plankton": dict(span=0.7, lowcut=0, soft=0.85, val=0.34),   # band 0.763 ac 0.616 pk 0.555
 "fpe_magenta_radiolaria": dict(span=0.36, lowcut=0, soft=0.55, val=0.34),   # band 0.878 ac 0.624 pk 0.814
 "fpe_violet_chains": dict(span=0.7, lowcut=0, soft=0, val=0.24),   # band 0.849 ac 0.586 pk 0.585
 "fpe_violet_frustule": dict(span=0.36, lowcut=0, soft=0.55, val=0.34),   # band 0.713 ac 0.654 pk 0.678
 "fpe_violet_garden": dict(span=0.7, lowcut=1, soft=0.55, val=0.34),   # band 0.736 ac 0.578 pk 0.447
 "fpe_violet_membrane": dict(span=0.5, lowcut=0, soft=0.55, val=0.24),   # band 0.757 ac 0.611 pk 0.524
}

for _fid, _e in _TUNE.items():
    _e = dict(_e)
    _PETRI[_fid]["val"] = _e.pop("val")
    _e["mid"] = _lut_steep(_PETRI[_fid]["lut"], _e.get("span", 1.0))
    _PETRI[_fid]["eargs"] = _e
# ════════════════════════════════════════════════════════════════════════════
# NAME ACCURACY — [SPB-FRACTURED-090c 2026-08-02] parent visual review.
# Culture-stain saturation is authentic and stays; the requirement is that
# each id's NAMED hue (amber / cyan / lime / magenta / violet) is the hue that
# actually DOMINATES the tile. Measured against the saturation-weighted
# circular-mean hue of the 512 paint, five ids were off by more than 0.03 of a
# turn — lime_chains rendered at 0.303, which is green, not lime.
# _HUEFIX is that measured per-id correction (the LUT's hue distribution
# inside a hero window is asymmetric, so the anchor you SET is not the hue
# that RENDERS). Luma-neutral: the hue window re-applies each pixel's own
# luma, so no band / coherence / peakiness / shape number moves.
# ════════════════════════════════════════════════════════════════════════════

_HUEFIX = {
 "fpe_amber_diatom": -0.0113,
 "fpe_amber_moldring": -0.0069,
 "fpe_amber_plankton": -0.0212,
 "fpe_cyan_mold": -0.0135,
 "fpe_cyan_spineball": -0.0079,
 "fpe_lime_chains": -0.0796,
 "fpe_lime_diatom": -0.0221,
 "fpe_magenta_bloom": -0.0118,
 "fpe_magenta_mosaic": +0.0315,
 "fpe_magenta_plankton": -0.0101,
 "fpe_violet_chains": -0.0085,
 "fpe_violet_garden": -0.0473,
 "fpe_violet_membrane": -0.0349,
}

for _profile, (_fid, _d) in enumerate(_PETRI.items()):
    # SPB-WILDS, tick 2 (2026-08-23). Owner: "Too much redundancy way too
    # similar looks. Must be VERY UNIQUE. And must have the 'Fractured' color
    # flipping stuff." Broad category-kit domains were the repeated macro
    # silhouette. wild_profile selects a unique six-family 8-32px signature;
    # final audited before->after movement is recorded beside KIT below.
    _d["id"] = _fid
    _d["wild_profile"] = _profile
    _d["wild_variant"] = _profile + 20
    _d["vd"] = (0.48 + 0.02 * (_profile % 3), 1.26 - 0.02 * (_profile % 4))
    _d["tmod"] = 0.10
    _d["kw"]["ambient"] = 0.02
    _d["kw"]["sparkle"] = 0.08
    _fx = float(_HUEFIX.get(_fid, 0.0))
    _h = [(_x + _fx) % 1.0 for _x in _d["hues"][:4]]
    _d["hues"] = [_h[0]] * 4 + [_h[1]] * 2 + [_h[2], _h[3]]
    _d["hspan"] = max(float(_d.get("hspan", 0.05)), 0.075 + 0.008 * (_profile % 5))
    _d["hue_levels"] = 0.9
    _d["hue_jit"] = 0.10
    _d["hue_blur"] = 3.2
    _d["hue_cell"] = max(float(_d.get("hue_cell", 8.0)), 14.0)

assert len(_PETRI) == 20

GROUPS = {
    "FRACTURED PETRI": _PETRI,
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
KIT = wildkit.FineFractureKit(engines=ENGINES, groups=GROUPS, tag="fractured-petri",
                # [field 2026-08-02] gen 768 -> 640: every generator
                # scales its pitch by res/_S, so the look is identical
                # while the whole module gains ~30% render headroom.
                work=1024, gen=640)

ALL = KIT.ALL
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
