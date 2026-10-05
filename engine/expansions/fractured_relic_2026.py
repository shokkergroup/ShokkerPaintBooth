# -*- coding: utf-8 -*-
"""FRACTURED RELIC (2026-08-01) — category of the FRACTURED expansion.

════════════════════════════════════════════════════════════════════════════
SPB-FRACTURED-FIELD 2026-08-02 — SECOND corrective pass (owner rejected the
2026-08-01 rebuild: "still VERY subpar... REALLY SIMILAR... repeated
designs... 2048x2048 covers an ENTIRE car — things that look intricate are
not as intricate as you think.")
════════════════════════════════════════════════════════════════════════════
Previous car-band median 0.209 — the WORST of the three modules, and the most
poster-like: single large glyph slabs, one big ziggurat, one wide inlay band.
On a whole car that reads as a smeared logo, not a relic.

Owner's own words are the spec for this category: "a whole TABLET of 10-24px
glyphs is PERFECT — one giant glyph is banned." Every generator below is now
a PAVE: hundreds-to-thousands of small tesserae, inlay chips, glyph cells,
leaf flakes and carved units at 8-32px on the 2048 canvas (pitch 6-16px on
the 768 gen grid), aged in place (chips / patina / tooth) so it still reads
as antiquity rather than wallpaper.

ARCHETYPE LEDGER — all 20 ids carry DISTINCT compositional archetypes:

  fre_lapis_inlay        chip-inlay pave (irregular stone chips in dark mastic)
  fre_gold_inlay         thread-drift wire inlay (fine wires combed over stone)
  fre_turquoise_inlay    granular micro-mosaic dust (sand-grade tesserae)
  fre_terracotta_inlay   banded strata laminae (fine sediment ply + grit)
  fre_malachite_mosaic   square tesserae grid (grouted, per-tile shade)
  fre_ivory_mosaic       scale imbrication (shingled ivory plaques)
  fre_lapis_mosaic       opus-vermiculatum worms (curved courses of chips)
  fre_gold_mosaic        star-lattice rosette pave (small tessellated stars)
  fre_turquoise_leaf     crackle-net gilding (leaf craquelure web)
  fre_terracotta_leaf    torn-flake pack (overlapping leaf flakes + tears)
  fre_malachite_leaf     micro-billow malachite bands (banded lens cushions)
  fre_ivory_leaf         needle-felt bone inlay (fine bone slivers)
  fre_lapis_glyphs       glyph tablet grid (10-24px cuneiform cells)
  fre_gold_glyphs        column-register glyph strips (vertical cartouches)
  fre_turquoise_glyphs   ring-pack seal impressions (stamped cylinder seals)
  fre_terracotta_glyphs  wedge-cuneiform dust field (impressed wedges)
  fre_malachite_ziggurat chevron pleats (stepped herringbone terraces)
  fre_ivory_ziggurat     stepped micro-terrace pave (tiny stepped pyramids)
  fre_lapis_ziggurat     interlocking meander cells (fret-key pack)
  fre_gold_ziggurat      dentil course lattice (rows of carved dentils)

Laws (as fractured_bloom_2026 / fractured_petri_2026 second pass): car-band
>= 0.45 each / module median >= 0.60; fineness > 6.5; coverage >= 56/64;
>= 5 hue bins; < 1.9 s at 512; descriptor pair-cosine <= 0.55. 3-4 luminous
hue anchors per id picked PER FEATURE (small hue_cell), 8-tier per-feature
brightness (_TIERS), and the _age() ply (chips + patina + tooth) on every
finish so the pave still reads aged.

Contract UNCHANGED: same 20 ids, same GROUPS key, same
install_into_engine(mono_reg, base_reg=None) -> (spec_fn, paint_fn); spec
traces paint via CategoryKit; work grid 1024, generators at 640; determinism
via np.random.default_rng + zlib.crc32(fid.encode()) — no hash(str).

Verify artifacts: _fractured_triage/refield_relic.jsonl +
_fractured_triage/resheet_relic.png.
[SPB-FRACTURED-090b 2026-08-02] THIRD pass — owner: "push the others to the
same levels ... WITHOUT it being static noise or just a bunch of repeats."
Car-band MEDIAN (FFT ring r 64..256 of the 512 paint over total r>=2, the
FRACTURED MINDS house standard = 0.82): 0.660 -> 0.895, per-finish
minimum 0.785, and all 20 ids now clear the four ANTI-STATIC guards that
make a high band mean "dense coherent micro-structure" instead of noise
(white noise measures ~0.95 on the ring and is a FAILURE at any score):
lag-1 neighbour coherence >= 0.55, spectral peakiness >= 0.32, connected
shape fraction >= 0.55, fineness > 6.5 — plus coverage 64/64, hue bins >= 5,
descriptor pair-cosine 0.54 (<= 0.55), 1.8 s at 512 / 1.9 s at
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
  * Excavated materials are MUTED, EARTHY and DARK, and this module was
    rendering fluorescent candy. Three measured causes: chroma was pinned
    at the ceiling (0.96-0.99 on all 20 — satboost 1.40 on a LUT that
    already returns S~1); every family carried a COMPLEMENTARY accent
    (malachite+orange, ivory+electric blue, gold+cyan) which at a 9 px
    hue cell is electric speckle, not an accent; and the warm families
    walked their hue window straight past 0.0 into MAGENTA, which is
    where the salmon-pink filaments came from. Now: per-material chroma,
    per-material value, wrap-safe windows, and five WEATHERING anchors
    per family (patina, soil stain, sun-bleach, oxidation, co-occurring
    mineral) which is what earns the >=5 hue-bin gate instead of a
    complement. fre_gold_mosaic was also repitched 10.4 -> 8.4 to break a
    0.542 descriptor pair against the seal pack (pitch is the driver).
"""
from __future__ import annotations

import zlib

import cv2
import numpy as np

from engine.expansions import fractured_catlib_2026 as catlib
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


def _age(res, seed, chip=0.20, tooth=0.12):
    """Antiquity ply: small dark chips / losses plus fine stone tooth.
    [SPB-FRACTURED-090b 2026-08-02] LAW L4 — the tooth was fbm(base 300),
    whose power peaks near r=105 but drags a 1/f skirt under the band, and
    the chips ran on a free-jitter lattice. Both are now bounded-jitter
    in-band lattices, so aging ADDS car-band energy instead of a low skirt
    (measured on the module: aging alone was worth -0.04 to -0.09 band)."""
    s = res / _S
    sd = _sd(seed)
    _, _, cd, cid, _c = _cells(res, 8.6 * s, sd + 303, 0.5, taps=5,
                               need2=False)
    chips = _bump((cd / (2.0 * s)) ** 2) * sstep(0.55, 0.85,
                                                 h2(np.floor(cid * 37.0), 0.0,
                                                    sd + 7))
    grit = _fine(res, seed + 313, 1.0)
    return (-chips * float(chip) + grit * float(tooth)).astype(np.float32)


# ════════════════════════════════════════════════════════════════════════════
# STRUCTURAL GENERATORS — 20 distinct relic-pave archetypes, one per finish.
# Every one is a dense in-band micro-field per the law above; the ARCHETYPE
# LEDGER at the top of the module is unchanged (one composition per id).
# [SPB-FRACTURED-090b 2026-08-02]
# ════════════════════════════════════════════════════════════════════════════

def g_chipinlay(res, seed, pitch=_P0, seam=0.28, fine=0.09):
    """chip-inlay pave — irregular polished stone chips bedded in dark
    mastic, every chip beveled and crowned (L1), the mastic a fat seam (L2)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.50, seam)
    bevel = sstep(0.02, 0.16, edge) * 0.18
    polish = _grain(dx + 21.0, dy + 33.0, 4.8 * s, sd + 11) * crown * 0.14
    T = (0.13 + crown * 0.42 + bevel + polish
         + _flat(_tier(id1), _LC * s) * 0.28 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.85 * gs) + _age(res, seed) + _fine(res, seed, fine))


def g_wireinlay(res, seed, pitch=9.0, steps=3, step_px=2.6, fine=0.09):
    """thread-drift wire inlay — fine gold wires combed across old stone on a
    curl field. The flow POTENTIAL stays fbm (it bends geometry and adds no
    luma — the L4 carve-out); the wire seeds are an in-band lattice."""
    s = res / _S
    sd = _sd(seed)
    _, _, d1, id1, _n = _cells(res, pitch * s, sd, 0.5, taps=5, need2=False)
    dot = _bump((d1 / (2.3 * s)) ** 2) * (0.45 + _flat(_tier(id1), _LC * s) * 0.55)
    pot = gauss(fbm(res, res, rng(seed, 171), 3, 7), 2.6)
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
        acc = np.maximum(acc, samp * (1.0 - 0.14 * (k + 1)))
    stone = _grain(xx, yy, 5.2 * s, sd + 5) * 0.16
    T = 0.15 + acc * 0.76 + stone
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_microdust(res, seed, fine=0.09):
    """granular micro-mosaic — sand-grade tesserae at two grades, no macro
    form at all: the finest pave in the module. Both grades moved into the
    band (4.7 and 7.5 px at GEN == 15 and 24 px on a 2048 car)."""
    s = res / _S
    sd = _sd(seed)
    _, _, da, ida, _a = _cells(res, 5.6 * s, sd, 0.5, taps=5, need2=False)
    _, _, db, idb, _b = _cells(res, 9.0 * s, sd + 51, 0.5, taps=5, need2=False)
    ga = _bump((da / (1.8 * s)) ** 2) * (0.35 + _flat(_tier(ida), _LC * s) * 0.65)
    gb = _bump((db / (2.8 * s)) ** 2) * (0.35 + _flat(_tier(idb), _LC * s) * 0.65)
    T = 0.16 + np.maximum(ga, gb * 0.92) * 0.76
    return n01(T + _age(res, seed, chip=0.14) + _fine(res, seed, fine))


def g_strata(res, seed, pitch=7.4, angle=0.30, warp=4.0, fine=0.09):
    """banded strata laminae — fine sediment plies with grit inclusions and a
    per-lamina shade. [090b] the warp dropped 16 -> 4 px (it was smearing the
    lamina fundamental) and the plies are tilted a little off horizontal so
    the courses read as bedding rather than a scanline."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 41, warp)
    ca, sa = np.cos(angle), np.sin(angle)
    q = ((xx + wu) * sa + (yy + wv) * ca) / (pitch * s)
    lam = 0.5 + 0.5 * np.cos(q * _TAU)
    tier = _flat(_tier(h2(np.floor(q), np.floor(q * 0.09), sd + 9)), _LC * s)
    grit = _grain(xx + wv, yy, 4.6 * s, sd + 13) * 0.16
    seam = sstep(0.10, 0.0, np.abs(frac(q * 0.5) - 0.5)) * 0.20
    T = 0.15 + lam * 0.42 + tier * 0.28 + grit - seam
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_tessgrid(res, seed, cell=10.6, gap=0.20, fine=0.09):
    """square tesserae grid — a regular grouted tile pave with per-tile shade
    and a chipped corner nick on some tiles. [090b] cell 10 -> 8.8 px at GEN
    (r 64 -> 73, off the band edge) and every tile now carries a crown."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 61, 3.0)
    u = (xx + wu) / (cell * s)
    v = (yy + wv) / (cell * s)
    cu = np.floor(u)
    cv_ = np.floor(v)
    fu = np.abs(u - cu - 0.5)
    fv = np.abs(v - cv_ - 0.5)
    edge = np.maximum(fu, fv)
    tile = sstep(0.5 - gap * 0.4, 0.5 - gap, edge)
    crown = sstep(0.5 - gap, 0.10, edge)
    nick = _bump(((fu - 0.42) ** 2 + (fv - 0.42) ** 2) / (0.06 ** 2))
    nick = nick * sstep(0.6, 0.85, h2(cu, cv_, sd + 17)) * 0.30
    stip = _grain(xx, yy, 4.4 * s, sd + 21) * tile * 0.14
    T = (0.14 + tile * 0.22 + crown * 0.26 + stip - nick
         + _flat(_tier(h2(cu, cv_, sd + 3)), _LC * s) * 0.30 * tile)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_shingle(res, seed, sw=10.6, rh=7.0, fine=0.08):
    """scale imbrication — shingled ivory plaques in offset rows, each with a
    ribbed grain and a lit leading edge. The grain period moved from 3 to
    7.5 px at GEN; the old one lived above the band and only cost coherence."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 71, 3.0)
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
        rr = np.hypot(du, dv * 0.9) / (sw * s * 0.58)
        inside = sstep(1.02, 0.90, rr)
        grain = 0.5 + 0.5 * np.cos(du / (1.2 * s) + h2(cu, cv_, sd + 5) * 6.0)
        lead = sstep(1.0, 0.78, rr) * sstep(0.0, -1.8 * s, dv) * 0.18
        crown = np.clip(1.0 - rr * rr, 0.0, 1.0)
        val = (0.13 + crown * 0.42 + grain * 0.12 * crown + lead
               + _flat(_tier(h2(cu, cv_, sd)), _LC * s) * 0.26
               * (0.25 + 0.75 * crown))
        T = T + val * inside * (1.0 - done)
        done = np.clip(done + inside, 0.0, 1.0)
    T = T + (1.0 - done) * 0.10
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_vermiculatum(res, seed, pitch=7.6, chip=7.0, warp=5.0, angle=0.28,
                   fine=0.09):
    """opus-vermiculatum worms — curved courses of small chips following a
    warped flow, mosaic laid in worm rows. [090b] the warp dropped 30 -> 5 px
    and the chip pitch rose 3.5 -> 5.8 px at GEN: the old course was a 2.8 px
    x-period at 512, i.e. a NEGATIVE lag-1 autocorrelation."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 81, warp)
    ca, sa = np.cos(angle), np.sin(angle)
    q = ((xx + wv) * sa + (yy + wu) * ca) / (pitch * s)
    ci = np.floor(q)
    v = frac(q)
    U = ((xx + wv) * ca - (yy + wu) * sa) / (chip * s) \
        + h2(ci, ci * 0.0, sd + 11) * 5.0
    ui = np.floor(U)
    u = frac(U)
    rr = np.hypot((u - 0.5) * 1.9, (v - 0.5) * 2.0)
    body = np.clip(1.0 - rr * rr, 0.0, 1.0)
    tier = _flat(_tier(h2(ui, ci, sd + 3)), _LC * s)
    T = 0.14 + body * 0.42 + tier * 0.28 * (0.25 + 0.75 * body)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_starpave(res, seed, pitch=8.4, points=8.0, fine=0.09):
    """star-lattice rosette pave — small tessellated stars with bright cores
    and dark interstices, on a NEAR-REGULAR lattice (jitter 0.20): the
    sharpest spectral fundamental in the module (the peakiness guard).
    [SPB-FRACTURED-090c 2026-08-02] pitch 10.4 -> 8.4 and 6 -> 8 points: this
    pave sat at descriptor cosine 0.542 against the seal pack (0.55 ceiling)
    because both were packed radial units on the SAME pitch. Pitch is the
    real driver of that convergence — separating the two lattices by 2 px at
    GEN separates the pair, and the star now reads finer than the seal."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.20, taps=5, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.64)
    prof = rr - 0.28 * np.abs(np.cos(th * points * 0.5 + id1 * _TAU)) ** 1.1
    body = sstep(0.74, 0.34, prof)
    rim = sstep(0.12, 0.0, np.abs(prof - 0.70)) * 0.24
    core = _bump((rr * 3.4) ** 2) * 0.22
    T = (0.15 + body * (0.30 + _flat(_tier(id1), _LC * s) * 0.40) + rim + core)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_craquelure(res, seed, pitch=_P0, seam=0.28, fine=0.09):
    """crackle-net gilding — leaf craquelure at two scales over slightly
    domed gilded islands. Both crack scales are fat edge-distance seams (L2):
    a hairline craquelure smears its power into r>200 harmonics."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.50, seam)
    _dx2, _dy2, _d2, idb, eb, crownb, gs2 = _pave(res, p * 0.68, sd + 41,
                                                  0.50, 0.20)
    burnish = _grain(dx + 7.0, dy + 19.0, 4.4 * s, sd + 9) * crown * 0.14
    T = (0.14 + crown * 0.40 + crownb * 0.12 + burnish
         + _flat(_tier(id1), _LC * s) * 0.28 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.80 * gs) * (1.0 - 0.30 * gs2)
               + _age(res, seed) + _fine(res, seed, fine))


def g_tornflake(res, seed, pitch=_P0, fine=0.09):
    """torn-flake pack — overlapping leaf flakes with ragged torn edges and
    lifted, brighter corners. [090b] LAW L4: the ragged edge was an fbm
    displacement feeding straight into the luma; it is now a per-flake
    angular hash, which tears crisper and costs nothing below the band."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.50, 0.20)
    th = np.arctan2(dy, dx)
    # [090b] 2.5 angular sectors per flake made the tear a COARSE chunk (its
    # own sub-band term); 6 sectors tear at the flake's own scale.
    rag = (h2(np.floor(id1 * 419.0), np.floor(th * 6.0), sd + 121) - 0.5) * 0.10
    e2 = edge + rag
    flake = sstep(0.02, 0.22, e2)
    lift = sstep(0.34, 0.08, e2) * 0.22
    a = id1 * _TAU
    lam = np.clip((dx * np.cos(a) + dy * np.sin(a)) / np.maximum(d1, 1e-4),
                  -1.0, 1.0)
    T = (0.13 + crown * 0.26 + flake * (0.30 + _flat(_tier(id1), _LC * s) * 0.34)
         + lift + lam * 0.08 * flake)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_bandlens(res, seed, pitch=_P0, bands=1.35, fine=0.09):
    """micro-billow malachite bands — cushioned lenses, each ringed by its own
    concentric banding. The wobble moved off fbm onto a per-lens hash (L4)
    and the band count from 3.2 to 1.35: 3.2 rings inside a 9 px lens is a
    1.4 px feature, above the band and pure denominator."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.48, 0.22)
    rr = d1 / (p * 0.70)
    wob = (h2(np.floor(id1 * 197.0), 0.0, sd + 131) - 0.5) * 0.20
    ring = 0.5 + 0.5 * np.cos((rr + wob) * bands * _TAU + id1 * 13.0)
    T = (0.13 + crown * 0.36 + ring * ring * 0.28 * (0.3 + 0.7 * crown)
         + _flat(_tier(id1), _LC * s) * 0.26 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.75 * gs) + _age(res, seed) + _fine(res, seed, fine))


def g_slivers(res, seed, pitch=_P0, ln=6.0, fine=0.09):
    """needle-felt bone inlay — fine bone slivers in two crossed plies with
    longitudinal grain lines. Sliver orientation is QUANTIZED to 8 directions:
    free angles smear the spectrum into a disc, quantized ones give 8 sharp
    lobes (the peakiness guard) and read as a real laid inlay."""
    s = res / _S
    sd = _sd(seed)

    def ply(pi, salt, lnk, wd):
        dx, dy, _d1, id1, _ = _cells(res, pi * s, salt, 0.5, taps=5,
                                     need2=False)
        a = np.floor(id1 * 8.0) * 0.7853982 + 0.15
        ca, sa = np.cos(a), np.sin(a)
        along = dx * ca + dy * sa
        across = np.abs(-dx * sa + dy * ca)
        L = lnk * s * (0.8 + 0.5 * h2(np.floor(id1 * 31.0), 0.0, salt + 3))
        body = sstep(wd * s, wd * s * 0.35, across) * sstep(L, L * 0.74,
                                                            np.abs(along))
        grain = (0.5 + 0.5 * np.cos(across / (1.1 * s))) * body * 0.16
        return body * (0.28 + _flat(_tier(id1), _LC * s) * 0.42) + grain

    a1 = ply(pitch, sd, ln, 2.1)
    a2 = ply(pitch * 0.82, sd + 101, ln * 0.78, 1.7)
    T = 0.16 + np.maximum(a1, a2 * 0.9)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def _glyph_cell(res, sd, cu, cv_, du, dv, cw, ch, strokes=4):
    """Small carved glyph inside one cell: a few axis-aligned strokes picked
    per cell hash. [090b/090c] the strokes are FAT — 0.17 of the cell, ~2.4 px
    at GEN. A hairline stroke on a 9 px cell is a sub-2px feature whose
    x-period lands at 4 px in the 512 paint, i.e. a NEGATIVE lag-1
    autocorrelation; fre_gold_glyphs measured ac 0.053 with the thin ones."""
    g = np.zeros_like(du)
    for k in range(int(strokes)):
        hsel = h2(cu * 1.0 + k * 13.0, cv_ * 1.0 + k * 7.0, sd + 31 + k)
        hx = h2(cu + k * 3.0, cv_ - k * 5.0, sd + 61 + k)
        hy = h2(cu - k * 2.0, cv_ + k * 9.0, sd + 91 + k)
        on = sstep(0.34, 0.42, hsel)
        px = (hx - 0.5) * cw * 0.50
        py = (hy - 0.5) * ch * 0.50
        horiz = hsel > 0.66
        w = np.where(horiz, cw * 0.30, ch * 0.17)
        h = np.where(horiz, cw * 0.17, ch * 0.30)
        bar = (sstep(w, w * 0.30, np.abs(du - px))
               * sstep(h, h * 0.30, np.abs(dv - py)))
        g = np.maximum(g, bar * on)
    return g


def g_tablet(res, seed, cw=10.6, ch=9.6, fine=0.09):
    """glyph tablet grid — a whole TABLET of small carved glyph cells with
    ruled register lines. [090b] the cell dropped 12.5 -> 8.8 px at GEN (the
    old register fundamental sat at r=51, under the band) and every cell now
    carries a face crown so the tablet lattice itself is band-pass."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 91, 3.0)
    u = (xx + wu) / (cw * s)
    v = (yy + wv) / (ch * s)
    cu = np.floor(u)
    cv_ = np.floor(v)
    du = (u - cu - 0.5) * cw * s
    dv = (v - cv_ - 0.5) * ch * s
    face = np.clip(1.0 - (np.maximum(np.abs(du) / (cw * s),
                                     np.abs(dv) / (ch * s)) * 2.2) ** 2,
                   0.0, 1.0)
    gl = _glyph_cell(res, sd, cu, cv_, du, dv, cw * s, ch * s, 4)
    rule = sstep(1.2 * s, 0.3 * s, np.abs(dv - ch * s * 0.5)) * 0.22
    tier = _flat(_tier(h2(cu, cv_, sd + 3)), _LC * s)
    stone = _grain(xx, yy, 4.8 * s, sd + 7) * 0.14
    T = 0.14 + face * 0.26 + gl * (0.30 + tier * 0.34) + rule + stone
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_cartouche(res, seed, colw=10.4, ch=8.6, fine=0.09):
    """column-register glyph strips — vertical cartouche columns divided by
    engraved borders, glyph cells stacked inside. The column pitch moved from
    r=59 (sub-band) to r=74, and the border is a fat seam."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 101, 3.0)
    u = (xx + wu) / (colw * s)
    ci = np.floor(u)
    fu = u - ci - 0.5
    border = _fat(0.5 - np.abs(fu), 0.26) * 0.30
    v = (yy + wv) / (ch * s) + h2(ci, ci * 0.0, sd + 11) * 3.0
    rj = np.floor(v)
    du = fu * colw * s
    dv = (v - rj - 0.5) * ch * s
    face = np.clip(1.0 - (np.abs(fu) * 2.1) ** 2, 0.0, 1.0)
    gl = _glyph_cell(res, sd, ci, rj, du, dv, colw * s * 0.70, ch * s, 3)
    tier = _flat(_tier(h2(ci, rj, sd + 5)), _LC * s)
    T = 0.14 + face * 0.26 + gl * (0.30 + tier * 0.36) + border
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_seals(res, seed, pitch=_P0, rings=1.30, fine=0.09):
    """ring-pack seal impressions — stamped cylinder-seal discs with
    concentric ridges and a beaded rim, each disc pressed into its own crown.
    Ring count 2.6 -> 1.30 and rim beads 17 -> 9: the old sub-features were
    ~1 px at GEN, above the band and pure denominator."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, edge, crown, gs = _pave(res, p, sd, 0.44, 0.20)
    rr = d1 / (p * 0.66)
    th = np.arctan2(dy, dx)
    ring = 0.5 + 0.5 * np.cos(rr * rings * _TAU + id1 * 17.0)
    beads = sstep(0.14, 0.04, np.abs(rr - 0.76))
    beads = beads * (0.5 + 0.5 * np.cos(th * 9.0 + id1 * _TAU)) ** 2 * 0.26
    T = (0.13 + crown * 0.36 + ring * ring * 0.24 * (0.3 + 0.7 * crown)
         + beads + _flat(_tier(id1), _LC * s) * 0.26 * (0.25 + 0.75 * crown))
    return n01(T * (1.0 - 0.70 * gs) + _age(res, seed) + _fine(res, seed, fine))


def g_wedges(res, seed, pitch=8.8, fine=0.09):
    """wedge-cuneiform dust field — impressed triangular wedges in four
    quantized orientations, dense over the whole tablet. The quantized
    orientation set gives four sharp spectral lobes instead of a smeared
    disc (the peakiness guard)."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, _d1, id1, _ = _cells(res, p, sd, 0.45, need2=False)
    a = np.floor(id1 * 4.0) * (np.pi * 0.5) + 0.35
    ca, sa = np.cos(a), np.sin(a)
    U = dx * ca + dy * sa
    V = -dx * sa + dy * ca
    wl = p * 0.44
    tri = sstep(0.0, -1.4 * s, np.abs(V) - (wl - U) * 0.42)
    tri = tri * sstep(wl, wl * 0.70, U) * sstep(-wl * 0.60, -wl * 0.28, U)
    shade = np.clip((V / (wl * 0.5)) * 0.5 + 0.5, 0.0, 1.0)
    tail = _bump(((U + wl * 0.5) ** 2 + V * V) / (2.2 * s) ** 2) * 0.24
    T = (0.15 + tri * (0.30 + _flat(_tier(id1), _LC * s) * 0.38)
         * (0.55 + 0.45 * shade) + tail)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_terracepleat(res, seed, col=12.0, step=8.0, slope=0.45, fine=0.09):
    """chevron pleats — stepped herringbone terraces, zigzag columns of
    quantized terrace steps. [090b] the tread pitch moved 3.7 -> 6.7 px at
    GEN and the chevron slope 0.9 -> 0.45: the old geometry put a 3 px
    x-period at 512, which is a NEGATIVE lag-1 autocorrelation. A tilted
    stair keeps its 2-D radius in the band and its x-period long."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 111, 4.0)
    X = xx + wu
    Y = yy + wv
    cw = col * s
    ci = np.floor(X / cw)
    u = frac(X / cw)
    sign = 1.0 - 2.0 * np.mod(ci, 2.0)
    q = Y / (step * s) + sign * u * (cw / (step * s)) * slope
    tread = np.floor(q)
    riser = 0.5 + 0.5 * np.cos(frac(q) * _TAU)
    lip = sstep(0.18, 0.02, frac(q)) * 0.20
    tier = _flat(_tier(h2(ci, tread, sd + 3)), _LC * s)
    seam = sstep(0.09, 0.0, np.minimum(u, 1.0 - u)) * 0.26
    T = 0.15 + riser * 0.34 + tier * 0.34 + lip
    return n01(T * (1.0 - seam) + _age(res, seed) + _fine(res, seed, fine))


def g_microterrace(res, seed, pitch=_P0, steps=3.0, fine=0.09):
    """stepped micro-terrace pave — tiny stepped pyramids (quantized Chebyshev
    distance) with lit top plates and shadowed east faces. Step count 5 -> 3:
    five terraces inside a 9 px pyramid is a sub-pixel riser."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, _d1, id1, d2 = _cells(res, p, sd, 0.30)
    cheb = np.maximum(np.abs(dx), np.abs(dy)) / (p * 0.54)
    lvl = np.floor(np.clip(1.0 - cheb, 0.0, 1.0) * steps) / steps
    face = sstep(0.0, 1.6 * s, dx) * 0.12
    top = sstep(0.26, 0.06, cheb) * 0.18
    T = (0.14 + _flat(_tier(id1), _LC * s) * 0.26 + lvl * 0.44 + top - face)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_meander(res, seed, cell=10.8, w=0.155, fine=0.09):
    """interlocking meander cells — a Greek-key fret pack: per-cell L/T
    grooves with quadrant rotation, carved and shadowed. [090b] the cell
    dropped 12.5 -> 9.0 px at GEN (r 51 -> 71) and the key arm widened
    0.09 -> 0.155 of the cell so the fret is a real 1.4 px groove at GEN
    (4.5 px on a 2048 car) instead of a sub-pixel scratch."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 121, 3.0)
    u = (xx + wu) / (cell * s)
    v = (yy + wv) / (cell * s)
    cu = np.floor(u)
    cv_ = np.floor(v)
    du = (u - cu - 0.5)
    dv = (v - cv_ - 0.5)
    rot = np.floor(h2(cu, cv_, sd + 3) * 4.0)
    for k in (1.0, 2.0, 3.0):
        m = rot == k
        du2 = np.where(m, dv, du)
        dv2 = np.where(m, -du, dv)
        du, dv = du2, dv2
    armA = sstep(w, w * 0.4, np.abs(dv - 0.22)) * sstep(0.42, 0.32, np.abs(du))
    armB = sstep(w, w * 0.4, np.abs(du - 0.22)) * sstep(0.42, 0.32, np.abs(dv))
    armC = sstep(w, w * 0.4, np.abs(dv + 0.12)) * sstep(0.20, 0.10, np.abs(du))
    key = np.clip(armA + armB + armC, 0.0, 1.0)
    field = np.clip(1.0 - (np.maximum(np.abs(du), np.abs(dv)) * 2.1) ** 2,
                    0.0, 1.0)
    tier = _flat(_tier(h2(cu, cv_, sd + 7)), _LC * s)
    T = 0.15 + field * 0.22 + tier * 0.30 + key * 0.36
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_dentils(res, seed, rh=9.0, bw=9.4, fine=0.09):
    """dentil course lattice — rows of small carved dentil blocks separated by
    fillets, each block lit on top and shadowed below. The block pitch moved
    to 7.8 px at GEN so the course lattice sits at r=82 with an x-period long
    enough to keep the coherence guard happy."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 131, 3.0)
    v = (yy + wv) / (rh * s)
    rj = np.floor(v)
    fv = v - rj
    u = (xx + wu) / (bw * s) + h2(rj, rj * 0.0, sd + 11) * 4.0
    ci = np.floor(u)
    fu = np.abs(u - ci - 0.5)
    block = sstep(0.42, 0.28, fu) * sstep(0.74, 0.58, np.abs(fv - 0.40))
    crown = np.clip(1.0 - (fu * 2.4) ** 2, 0.0, 1.0) * block
    top = sstep(0.20, 0.06, np.abs(fv - 0.16)) * block * 0.24
    under = sstep(0.14, 0.02, np.abs(fv - 0.72)) * 0.18
    tier = _flat(_tier(h2(ci, rj, sd + 5)), _LC * s)
    T = 0.15 + block * 0.24 + crown * 0.24 + tier * 0.30 * block + top - under
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


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
    "chipinlay": g_chipinlay, "wireinlay": g_wireinlay,
    "microdust": g_microdust, "strata": g_strata, "tessgrid": g_tessgrid,
    "shingle": g_shingle, "vermiculatum": g_vermiculatum,
    "starpave": g_starpave, "craquelure": g_craquelure,
    "tornflake": g_tornflake, "bandlens": g_bandlens, "slivers": g_slivers,
    "tablet": g_tablet, "cartouche": g_cartouche, "seals": g_seals,
    "wedges": g_wedges, "terracepleat": g_terracepleat,
    "microterrace": g_microterrace, "meander": g_meander, "dentils": g_dentils,
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
       vd=(0.78, 1.16), tmod=0.08, hspan=0.05, satboost=1.40, val=0.24,
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
# materials lapis / gold / turquoise / terracotta / malachite / ivory
# interleaved). Seeds = crc32(fid).
# Every recipe: [SPB-FRACTURED-FIELD 2026-08-02] dense-pave rebuild.
# ════════════════════════════════════════════════════════════════════════════

_RELIC = {
 # [field 2026-08-02] chip-inlay pave, lapis + gold flecks + patina
 "fre_lapis_inlay": _R("Lapis Inlay", "chipinlay",
    dict(), (390.0, 940.0, 1.0, 1.26, 0.6),
    [0.62, 0.57, 0.115, 0.68], 6.0,
    "Thousands of small lapis chips bedded chip by chip in dark mastic. A FRACTURED RELIC finish."),
 # [field 2026-08-02] thread-drift wire inlay, gold over stone
 "fre_gold_inlay": _R("Gold Inlay", "wireinlay",
    dict(), (405.0, 915.0, 1.0, 1.28, 2.2),
    [0.105, 0.08, 0.14, 0.45], 5.5, val=0.27,
    kw=dict(sparkle=0.30),
    desc="Fine gold wire inlay combed in drifting threads across old stone. A FRACTURED RELIC finish."),
 # [field 2026-08-02] granular micro-mosaic, turquoise sand tesserae
 "fre_turquoise_inlay": _R("Turquoise Inlay", "microdust",
    dict(), (395.0, 935.0, 1.0, 1.28, 3.5),
    [0.48, 0.53, 0.42, 0.09], 5.0,
    "Sand-grade turquoise tesserae packed grain against grain. A FRACTURED RELIC finish."),
 # [field 2026-08-02] banded strata laminae, terracotta sediment
 "fre_terracotta_inlay": _R("Terracotta Inlay", "strata",
    dict(), (410.0, 910.0, 1.0, 1.26, 4.8),
    [0.035, 0.06, 0.015, 0.10], 5.5,
    "Fine terracotta strata laid ply on ply, grit caught in every lamina. A FRACTURED RELIC finish."),
 # [field 2026-08-02] square tesserae grid, malachite grouted tiles
 "fre_malachite_mosaic": _R("Malachite Mosaic", "tessgrid",
    dict(), (400.0, 930.0, 1.0, 1.28, 1.4),
    [0.38, 0.44, 0.32, 0.115], 6.0,
    macro=("domains", dict(cells=5, salt=3391)), vd=(0.76, 1.16),
    desc="A grouted malachite tessera grid, every tile a different green. A FRACTURED RELIC finish."),
 # [field 2026-08-02] scale imbrication, ivory plaques
 "fre_ivory_mosaic": _R("Ivory Mosaic", "shingle",
    dict(), (400.0, 895.0, 0.95, 1.12, 3.0),
    [0.12, 0.09, 0.55, 0.30], 6.0, satboost=1.10, val=0.26,
    kw=dict(floor=0.14),
    desc="Ivory plaques shingled row over row, each one grained and lit. A FRACTURED RELIC finish."),
 # [field 2026-08-02] opus vermiculatum, lapis worm courses
 "fre_lapis_mosaic": _R("Lapis Mosaic", "vermiculatum",
    dict(), (390.0, 945.0, 1.0, 1.28, 5.1),
    [0.63, 0.58, 0.68, 0.115], 5.5,
    "Lapis chips laid in curving vermiculatum courses, worm row on worm row. A FRACTURED RELIC finish."),
 # [field 2026-08-02] star-lattice rosette pave, gold stars
 "fre_gold_mosaic": _R("Gold Mosaic", "starpave",
    dict(), (405.0, 920.0, 1.0, 1.28, 0.9),
    [0.10, 0.13, 0.075, 0.52], 6.0,
    "A pave of small gold tessellated stars, dark grout between the points. A FRACTURED RELIC finish."),
 # [field 2026-08-02] crackle-net gilding, turquoise craquelure
 "fre_turquoise_leaf": _R("Turquoise Leaf", "craquelure",
    dict(), (395.0, 930.0, 1.0, 1.28, 2.7),
    [0.47, 0.52, 0.42, 0.115], 6.0,
    "Turquoise gilding crazed into a fine craquelure of tiny islands. A FRACTURED RELIC finish."),
 # [field 2026-08-02] torn-flake pack, terracotta leaf
 "fre_terracotta_leaf": _R("Terracotta Leaf", "tornflake",
    dict(), (410.0, 905.0, 1.0, 1.26, 4.3),
    [0.04, 0.07, 0.02, 0.30], 6.0,
    "Torn terracotta leaf flakes overlapping edge on ragged edge. A FRACTURED RELIC finish."),
 # [field 2026-08-02] micro-billow bands, malachite lenses
 "fre_malachite_leaf": _R("Malachite Leaf", "bandlens",
    dict(), (400.0, 930.0, 1.0, 1.28, 5.6),
    [0.39, 0.45, 0.33, 0.52], 6.0,
    "Small malachite lenses, every cushion banded in its own green rings. A FRACTURED RELIC finish."),
 # [field 2026-08-02] needle felt, ivory bone slivers
 "fre_ivory_leaf": _R("Ivory Leaf", "slivers",
    dict(), (400.0, 895.0, 0.95, 1.12, 1.9),
    [0.11, 0.14, 0.58, 0.08], 6.0, satboost=1.10, val=0.26,
    kw=dict(floor=0.14),
    desc="A felt of fine ivory bone slivers crossed ply over ply. A FRACTURED RELIC finish."),
 # [field 2026-08-02] glyph tablet grid, lapis cuneiform cells
 "fre_lapis_glyphs": _R("Lapis Glyphs", "tablet",
    dict(), (390.0, 940.0, 1.0, 1.28, 3.8),
    [0.61, 0.66, 0.56, 0.115], 6.0,
    "A whole lapis tablet ruled into registers of small carved glyphs. A FRACTURED RELIC finish."),
 # [field 2026-08-02] column registers, gold cartouches
 "fre_gold_glyphs": _R("Gold Glyphs", "cartouche",
    dict(), (405.0, 915.0, 1.0, 1.28, 5.4),
    [0.10, 0.135, 0.07, 0.44], 6.0,
    "Columns of gold cartouches, glyph cell stacked on glyph cell. A FRACTURED RELIC finish."),
 # [field 2026-08-02] seal impressions, turquoise stamps
 "fre_turquoise_glyphs": _R("Turquoise Glyphs", "seals",
    dict(), (395.0, 935.0, 1.0, 1.28, 1.1),
    [0.49, 0.44, 0.54, 0.10], 6.0,
    "Turquoise cylinder-seal impressions stamped rim to beaded rim. A FRACTURED RELIC finish."),
 # [field 2026-08-02] wedge cuneiform dust, terracotta tablet
 "fre_terracotta_glyphs": _R("Terracotta Glyphs", "wedges",
    dict(), (410.0, 905.0, 1.0, 1.26, 2.4),
    [0.045, 0.02, 0.08, 0.115], 5.5,
    "A terracotta tablet impressed all over with tiny cuneiform wedges. A FRACTURED RELIC finish."),
 # [field 2026-08-02] chevron pleats, malachite stepped terraces
 "fre_malachite_ziggurat": _R("Malachite Ziggurat", "terracepleat",
    dict(), (400.0, 930.0, 1.0, 1.28, 0.3),
    [0.40, 0.34, 0.46, 0.10], 6.0,
    "Malachite terraces pleated into stepped herringbone columns. A FRACTURED RELIC finish."),
 # [field 2026-08-02] micro terraces, ivory step pyramids
 "fre_ivory_ziggurat": _R("Ivory Ziggurat", "microterrace",
    dict(), (400.0, 895.0, 0.95, 1.12, 4.6),
    [0.13, 0.10, 0.56, 0.34], 6.0, satboost=1.10, val=0.26,
    kw=dict(floor=0.14),
    desc="A pave of tiny ivory step-pyramids, terrace on lit terrace. A FRACTURED RELIC finish."),
 # [field 2026-08-02] meander fret pack, lapis keys
 "fre_lapis_ziggurat": _R("Lapis Ziggurat", "meander",
    dict(), (390.0, 945.0, 1.0, 1.28, 2.0),
    [0.60, 0.65, 0.55, 0.13], 6.0,
    "Interlocking lapis meander keys carved cell into cell. A FRACTURED RELIC finish."),
 # [field 2026-08-02] dentil courses, gold cornice blocks
 "fre_gold_ziggurat": _R("Gold Ziggurat", "dentils",
    dict(), (405.0, 920.0, 1.0, 1.28, 3.2),
    [0.11, 0.085, 0.145, 0.50], 6.0,
    macro=("bands", dict(angle=0.15, freq=1.2, warp=0.2)), vd=(0.76, 1.18),
    desc="Course after course of small gold dentil blocks, each one lit on top. A FRACTURED RELIC finish."),
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
    "fre_lapis_inlay": (("continents", dict(base=3, cells=3.0)), (0.84, 1.13)),
    "fre_gold_inlay": (("vortex", dict(arms=2.0, twist=7.0)), (0.84, 1.13)),
    "fre_turquoise_inlay": (("none", {}), (0.78, 1.16)),
    "fre_terracotta_inlay": (("bands", dict(angle=0.05, freq=2.0, warp=0.36)), (0.84, 1.13)),
    "fre_malachite_mosaic": (("domains", dict(cells=8, salt=3391)), (0.84, 1.13)),
    # [2c] margin is a single big radial falloff — the lowest-frequency
    # device in catlib, and this pale recipe had no band headroom for it.
    # Tight directional drift instead (distinct angle+freq from the other
    # three band ids in this module).
    # [2c] see fpe_amber_moldring: pale low-chroma recipes have no band
    # headroom for value drama — macro identity via hue zoning only.
    "fre_ivory_mosaic": (("bands", dict(angle=1.05, freq=5.5, warp=0.26)), (0.92, 1.06)),
    "fre_lapis_mosaic": (("domains", dict(cells=3, salt=3067)), (0.84, 1.13)),
    "fre_gold_mosaic": (("rings", dict(freq=6.5)), (0.84, 1.13)),
    "fre_turquoise_leaf": (("continents", dict(base=5, cells=6.0)), (0.84, 1.13)),
    "fre_terracotta_leaf": (("none", {}), (0.78, 1.16)),
    "fre_malachite_leaf": (("domains", dict(cells=14, salt=3529)), (0.84, 1.13)),
    "fre_ivory_leaf": (("rachis", dict(angle=0.8, sweep=4.5)), (0.84, 1.13)),
    "fre_lapis_glyphs": (("bands", dict(angle=1.5, freq=3.0, warp=0.18)), (0.84, 1.13)),
    "fre_gold_glyphs": (("none", {}), (0.78, 1.16)),
    "fre_turquoise_glyphs": (("vortex", dict(arms=3.0, twist=5.0, two=True)), (0.84, 1.13)),
    "fre_terracotta_glyphs": (("continents", dict(base=4, cells=2.5)), (0.84, 1.13)),
    "fre_malachite_ziggurat": (("rings", dict(freq=4.5, two=True)), (0.84, 1.13)),
    "fre_ivory_ziggurat": (("domains", dict(cells=5, salt=3701)), (0.84, 1.13)),
    "fre_lapis_ziggurat": (("none", {}), (0.78, 1.16)),
    "fre_gold_ziggurat": (("bands", dict(angle=0.15, freq=1.4, warp=0.20)), (0.84, 1.13)),
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
    _RELIC[_fid]["macro"] = _mac
    _RELIC[_fid]["vd"] = _vd
    _RELIC[_fid]["tmod"] = 0.08
    _RELIC[_fid]["hue_drift"] = 0.30 if _mac[0] == "none" else 0.95
# determinism law: per-finish seed straight from the id (no hash(str)).
for _fid, _d in _RELIC.items():
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
 "fre_gold_glyphs": dict(span=0.7, lowcut=0, soft=0.85, val=0.34),   # band 0.786 ac 0.650 pk 0.604
 "fre_gold_inlay": dict(span=0.26, lowcut=1.6, soft=0, val=0.27),   # band 0.881 ac 0.574 pk 0.509
 "fre_gold_mosaic": dict(span=0.36, lowcut=0, soft=0.55, val=0.34),   # band 0.937 ac 0.636 pk 0.857
 "fre_gold_ziggurat": dict(span=0.5, lowcut=1.6, soft=0, val=0.24),   # band 0.958 ac 0.588 pk 0.649
 "fre_ivory_leaf": dict(span=0.7, lowcut=0, soft=0.85, val=0.34),   # band 0.849 ac 0.577 pk 0.489
 "fre_ivory_mosaic": dict(span=0.7, lowcut=0, soft=0.55, val=0.26),   # band 0.926 ac 0.608 pk 0.811
 "fre_ivory_ziggurat": dict(span=0.7, lowcut=1.6, soft=0, val=0.26),   # band 0.925 ac 0.558 pk 0.669
 "fre_lapis_glyphs": dict(span=0.7, lowcut=1.6, soft=0, val=0.24),   # band 0.931 ac 0.573 pk 0.557
 "fre_lapis_inlay": dict(span=0.5, lowcut=0, soft=0.55, val=0.221),   # band 0.938 ac 0.652 pk 0.727
 "fre_lapis_mosaic": dict(span=0.7, lowcut=0, soft=0.55, val=0.24),   # band 0.976 ac 0.556 pk 0.819
 "fre_lapis_ziggurat": dict(span=0.5, lowcut=0, soft=0.85, val=0.34),   # band 0.971 ac 0.687 pk 0.866
 "fre_malachite_leaf": dict(span=0.5, lowcut=0, soft=0, val=0.24),   # band 0.944 ac 0.604 pk 0.649
 "fre_malachite_mosaic": dict(span=0.7, lowcut=0, soft=0.85, val=0.34),   # band 0.977 ac 0.723 pk 0.949
 "fre_malachite_ziggurat": dict(span=0.7, lowcut=1, soft=0.55, val=0.34),   # band 0.960 ac 0.625 pk 0.805
 "fre_terracotta_glyphs": dict(span=0.7, lowcut=0, soft=0.55, val=0.24),   # band 0.864 ac 0.642 pk 0.629
 "fre_terracotta_inlay": dict(span=0.7, lowcut=1.6, soft=0, val=0.24),   # band 0.946 ac 0.856 pk 0.893
 "fre_terracotta_leaf": dict(span=0.7, lowcut=0, soft=0.85, val=0.255),   # band 0.863 ac 0.662 pk 0.666
 "fre_turquoise_glyphs": dict(span=0.5, lowcut=0, soft=0.55, val=0.24),   # band 0.950 ac 0.637 pk 0.708
 "fre_turquoise_inlay": dict(span=0.26, lowcut=0, soft=0.55, val=0.34),   # band 0.859 ac 0.603 pk 0.617
 "fre_turquoise_leaf": dict(span=0.5, lowcut=0, soft=0, val=0.24),   # band 0.941 ac 0.604 pk 0.633
}

for _fid, _e in _TUNE.items():
    _e = dict(_e)
    _RELIC[_fid]["val"] = _e.pop("val")
    _e["mid"] = _lut_steep(_RELIC[_fid]["lut"], _e.get("span", 1.0))
    _RELIC[_fid]["eargs"] = _e
# ════════════════════════════════════════════════════════════════════════════
# MATERIAL PALETTE — [SPB-FRACTURED-090c 2026-08-02] parent visual review:
# "reads as fluorescent candy, not excavated artifacts."
#
# Two measured causes, both fixed here (luma is untouched — the hue window
# re-applies each pixel's own luma — so every band/guard number is unchanged):
#
# 1. SATURATION WAS PINNED AT THE CEILING. Measured mean chroma was 0.96-0.99
#    on all 20 ids: catlib computes s = S*satboost + 0.08 and the thin-film
#    LUT already returns S near 1, so satboost 1.40 clipped everything to full
#    chroma. Ancient materials are low-chroma. satboost 1.40 -> 0.55 plus
#    gray 0.30 lands mean chroma near 0.44 — dug-up stone, not neon.
# 2. THE ACCENT WAS A COMPLEMENTARY. Every family carried one anchor on the
#    far side of the wheel (malachite green + 0.115 ORANGE, ivory cream +
#    0.55 BLUE, gold + 0.45 CYAN). At a ~9 px hue cell that is not an accent,
#    it is electric speckle. Accents are now NEIGHBOURS on the mineral
#    continuum, and the >= 5 hue-bin gate is earned from WEATHERING instead:
#    patina, soil staining, sun-bleach, oxidation — real reasons a buried
#    object varies in hue.
# 3. The anchor you SET is not the hue that RENDERS (the LUT's hue
#    distribution inside a hero window is asymmetric). _HUEFIX is the
#    MEASURED per-id correction from _fractured_triage/huefix.py — the
#    saturation-weighted circular-mean hue of the 512 paint against the id's
#    material target. Every id is held to <= 0.03 of a turn.
# ════════════════════════════════════════════════════════════════════════════

# (hero x6, second x2, accent, weathering1, weathering2) — every non-hero
# anchor is a NEIGHBOUR on the mineral continuum or a real weathering product
# of the hero material. No complementaries: at a ~9 px hue cell a complement
# is electric speckle, not an accent.
# [090c r2] every weathering anchor stays WARM-NEUTRAL. Hue 0.00-0.03 is
# "dark red-brown" only when it is also dark; at the mid luma this category
# renders at it reads PINK, and the first pass put salmon speckle through the
# whole gold/ivory/terracotta half of the module. Iron-oxide staining is
# carried by the low VALUE (see _VAL) instead, where it belongs.
_LAPIS = (0.625, 0.650, 0.598, 0.120, 0.565)   # + pyrite fleck, calcite vein
_GOLD = (0.115, 0.098, 0.152, 0.088, 0.132)    # + sun-bleach, bronze, brass
_TURQ = (0.470, 0.448, 0.498, 0.100, 0.415)    # + ochre host rock, green ox
_TERRA = (0.045, 0.030, 0.088, 0.118, 0.062)   # + dark clay, bleach, dust
_MALA = (0.360, 0.335, 0.392, 0.300, 0.432)    # + near-black, azurite (real
                                               #   co-occurring mineral pair)
_IVORY = (0.105, 0.088, 0.155, 0.072, 0.130)   # + tea stain, straw, bone

_PALETTE = {}
for _pre, _pal in (("lapis", _LAPIS), ("gold", _GOLD), ("turquoise", _TURQ),
                   ("terracotta", _TERRA), ("malachite", _MALA),
                   ("ivory", _IVORY)):
    for _f in _RELIC:
        if _f.split("_")[1] == _pre:
            _PALETTE[_f] = _pal

# [090c r3] chroma is PER MATERIAL, not per module. One global satboost made
# lapis read cornflower (ultramarine is a SATURATED mineral — what makes it
# "deep" is low VALUE, which _VAL handles) while ivory stayed khaki (ivory is
# nearly achromatic and only its warmth should survive). Ditto hspan: the
# warm families sit next to the red wrap, so a wide intra-window travel throws
# salmon-pink filaments; they get a narrow window and earn their hue bins from
# the five weathering anchors instead.
_SATBOOST = {"lapis": 0.58, "malachite": 0.50, "turquoise": 0.58,
             "terracotta": 0.48, "gold": 0.48, "ivory": 0.34}
_GRAY = {"lapis": 0.34, "malachite": 0.42, "turquoise": 0.30,
         "terracotta": 0.42, "gold": 0.34, "ivory": 0.38}
# [090c r4] THE PINK. hspan is a HALF-WIDTH in turns, so a warm family whose
# hero sits at 0.045-0.115 walks its window straight past 0.0 and wraps into
# MAGENTA — that is the salmon-pink filament through the whole gold /
# terracotta / ivory half of the sheet, and no amount of desaturation removes
# it because the hue itself is wrong. Warm windows are now clamped so the
# walk cannot cross the red wrap; the >= 5 hue-bin gate is carried by the
# five weathering anchors instead. lapis is narrow for the mirror reason
# (a wide walk went past 0.71 into violet).
_HSPANF = {"lapis": 0.062, "malachite": 0.075, "turquoise": 0.085,
           "terracotta": 0.028, "gold": 0.045, "ivory": 0.048}

# [090c r2] VALUE is the other half of "excavated". Chroma alone still read as
# pastel candy: lapis came out cornflower instead of deep ultramarine,
# malachite mint instead of banded green, terracotta salmon instead of clay.
# Deep minerals are DARK; only ivory and gold are light. The anti-dead-black
# floor also drops 0.11 -> 0.04 so the shadow half can actually go dark —
# which RAISES micro-contrast, so the fineness gate gains rather than loses.
_VAL = {"lapis": 0.190, "malachite": 0.205, "terracotta": 0.235,
        "turquoise": 0.255, "gold": 0.295, "ivory": 0.335}
# Per-id lightness trim, MEASURED (apply_valfix.py): catlib crushes the art by
# its MAX, so equal `val` renders at unequal mean luma — the spread across the
# four lapis ids was 0.19 to 0.37, i.e. ultramarine to cornflower. This targets
# the MEAN so a family reads as one material.
_VALFIX = {
 "fre_gold_glyphs": 0.674,
 "fre_gold_inlay": 0.711,
 "fre_gold_mosaic": 1.154,
 "fre_ivory_leaf": 0.900,
 "fre_ivory_mosaic": 1.043,
 "fre_ivory_ziggurat": 0.873,
 "fre_lapis_glyphs": 1.079,
 "fre_lapis_inlay": 0.841,
 "fre_lapis_mosaic": 0.686,
 "fre_lapis_ziggurat": 0.600,
 "fre_malachite_leaf": 0.766,
 "fre_malachite_mosaic": 0.651,
 "fre_malachite_ziggurat": 1.165,
 "fre_terracotta_glyphs": 0.653,
 "fre_terracotta_inlay": 0.748,
 "fre_turquoise_glyphs": 0.942,
 "fre_turquoise_inlay": 0.880,
 "fre_turquoise_leaf": 0.853,
}

_HUEFIX = {
 "fre_gold_glyphs": +0.0134,
 "fre_gold_inlay": -0.0431,
 "fre_gold_mosaic": +0.0153,
 "fre_ivory_leaf": +0.0095,
 "fre_ivory_ziggurat": +0.0123,
 "fre_lapis_inlay": +0.0174,
 "fre_lapis_mosaic": +0.0123,
 "fre_lapis_ziggurat": +0.0182,
 "fre_malachite_leaf": +0.0022,
 "fre_malachite_mosaic": +0.0120,
 "fre_malachite_ziggurat": -0.0515,
 "fre_terracotta_glyphs": -0.0176,
 "fre_terracotta_inlay": -0.0131,
 "fre_terracotta_leaf": +0.0199,
 "fre_turquoise_inlay": +0.0552,
 "fre_turquoise_leaf": +0.0192,
}

for _fid, _d in _RELIC.items():
    _d["vd"] = (0.96, 1.06)
    _d["tmod"] = 0.0
    _d["kw"]["ambient"] = 0.05
    _d["kw"]["sparkle"] = 0.08
    _fam = _fid.split("_")[1]
    _d["kw"]["gray"] = _GRAY[_fam]
    _d["kw"]["floor"] = 0.04
    _d["satboost"] = _SATBOOST[_fam]
    _d["hspan"] = _HSPANF[_fam]
    _d["val"] = _VAL[_fam] * float(_VALFIX.get(_fid, 1.0))
    _fx = float(_HUEFIX.get(_fid, 0.0))
    _p = _PALETTE.get(_fid, _d["hues"])
    _h = [(_x + _fx) % 1.0 for _x in (list(_p) + list(_p))[:5]]
    _d["hues"] = [_h[0]] * 6 + [_h[1]] * 2 + [_h[2], _h[3], _h[4]]
    _d["hue_levels"] = 0.9
    _d["hue_jit"] = 0.10
    _d["hue_blur"] = 3.2
    _d["hue_cell"] = max(float(_d.get("hue_cell", 8.0)), 14.0)

assert len(_RELIC) == 20

GROUPS = {
    "FRACTURED RELIC": _RELIC,
}

KIT = _FieldKit(engines=ENGINES, groups=GROUPS, tag="fractured-relic",
                # [field 2026-08-02] gen 768 -> 640: every generator
                # scales its pitch by res/_S, so the look is identical
                # while the whole module gains ~30% render headroom.
                work=1024, gen=640)

ALL = KIT.ALL
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
