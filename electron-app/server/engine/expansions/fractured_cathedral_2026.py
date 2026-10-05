# -*- coding: utf-8 -*-
"""FRACTURED CATHEDRAL (2026-07-30) — category 7/10 of the FRACTURED expansion.

[SPB-FRACTURED-090 2026-08-02] THIRD pass — owner: "if MINDS sits at 0.82 I
want you to try to achieve 0.90 — we STRIVE to get better." Pass 2 left the
module at car-band MEDIAN 0.639 (FFT ring 64..256 of the 512 paint, over
total r>=2) against the FRACTURED MINDS flagship at 0.82. This pass measures
where the missing power actually sat and moves it, WITHOUT cheating: white
noise scores ~0.95 on that ring and is a failure at any score, so every
finish is now also held to four anti-static guards (lag-1 neighbour
coherence, spectral peakiness, connected-shape fraction, fineness).

RESULT: car-band median 0.639 -> 0.817, min 0.346 -> 0.709, and every finish
clears peakiness >= 0.32 / shape-fraction >= 0.55 / fineness > 6.5 / coverage
64 of 64 / hue bins >= 5 / < 1.6 s at 512 (0.8-1.1 s at 2048); coherence
clears 0.55 on 19 of 20 (fca_crown_violet 0.513). 6 of 20 clear the full 0.85
band bar; the rest sit 0.71-0.85. The gain is structural, not grain — see THE
MICRO-FIELD LAW below. The binding wall is the joint constraint: band >= 0.85
needs power ABOVE r=64 while coherence >= 0.55 needs it BELOW r~130, so the
whole wall of glass has to live in a 4-8 px window at GEN.

ARCHETYPE LEDGER — 20 ids, 20 DISTINCT compositional archetypes (no two ids
share one; descriptor-verified):
  fca_ruby_lights     quarry pave         (diamond diaper of small domed quarries)
  fca_cobalt_oculus   ring-pack           (MANY tiny came-ringed oculi, no rose window)
  fca_emerald_streak  directional-lamina  (fine drawn-glass striae bands)
  fca_crown_amber     scale imbrication   (overlapping small pantile crown scales)
  fca_bottle_violet   foam pack           (packed seedy bubbles, meniscus walls)
  fca_amber_kiln      granular scatter    (confetti frit chips in a clear matrix)
  fca_emerald_wheel   star-lattice        (60-degree tracery mesh, glass triangles)
  fca_jewel_streak    flow-combed strands (combed opalescent strand glass)
  fca_crown_cobalt    micro-ripple carpet (spun ripples from many centres)
  fca_bottle_ruby     interlocking-cells  (millefiori cane pack, dark gaps)
  fca_emerald_quarry  woven-cross         (leaded basket weave, came over came)
  fca_violet_rose     chevron pleats      (pleated drapery-glass herringbone)
  fca_amber_slag      micro-billows       (posterized slag marbling pools)
  fca_crown_jewels    structured dust     (3-scale faceted jewel-chip dust)
  fca_bottle_cobalt   thread-drift        (trailed cane threads drifting)
  fca_jewel_lights    crackle-net         (two-scale ice-crackle came web)
  fca_ruby_rose       dendrite forest     (glue-chip frost ferns, many small)
  fca_cobalt_streak   RD labyrinth        (reamy labyrinth stripe glass)
  fca_crown_violet    needle felt         (fused stringer needles, 6 angles)
  fca_bottle_emerald  branching-mesh      (ream vein web at two scales)

DARK LEAD DOCTRINE (kept from pass 1, now DYNAMIC): the thin-film LUT has a
deep luma null; every generator puts the CAMES exactly at that null
(lead_t = probed argmin per LUT at import) and lifts panes to +0.22..+0.9,
so leading reads near-black against jewel glass for ANY recipe. tmod=0.0
across the category — a macro phase shift would walk the cames off the null
AND convert macro form into luma banding through the oscillating LUT.

Palette law: 4-6 glass hues per finish (weighted lists, 5+ distinct hue
bins), anchor pick per hue DEVICE (parent correction 2026-08-02: at most 4
domain-patchwork ids; others per-pane confetti / directional flow / soft
cloud — see _CathedralKit.macro_maps) — the most colorful category of the
ten. Lead-vs-glass spec kept from pass 1
(_CathedralKit): cames dull rough metal, panes glossy dielectric.

Built on engine/expansions/fractured_catlib_2026.py. Determinism: all
randomness via catlib.rng(seed, salt) (np.random.default_rng), integer salts
only, no hash(str) anywhere. Fully vectorized at GEN=640; only small bounded
Python loops (<= 8 dilation steps, <= 6 stroke orientations, 3 dust scales).
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions import fractured_catlib_2026 as catlib
from engine.expansions.fractured_catlib_2026 import (
    coords, fbm, frac, gauss, h2, n01, rng, rot, sstep, warp_pair, worley,
)

# 8-tier per-pane brightness palette (owner doctrine).
_TIERS = np.array([0.16, 0.26, 0.36, 0.46, 0.56, 0.66, 0.78, 0.92], np.float32)


def _tier(hv):
    return _TIERS[np.clip((np.asarray(hv, np.float32) * 8.0).astype(np.int32), 0, 7)]


def _lut_null(lut):
    """T position (0..1) of the LUT luma NULL — the dark-lead came anchor
    (dynamic probe; replaces pass 1's hardcoded LT constants).
    [SPB-FRACTURED-FIELD 2026-08-02]"""
    t = catlib.thinfilm_lut(*lut)
    L = t[:, 0] * 0.299 + t[:, 1] * 0.587 + t[:, 2] * 0.114
    return float(np.argmin(L)) / float(len(L) - 1)


# ════════════════════════════════════════════════════════════════════════════
# THE MICRO-FIELD LAW  [SPB-FRACTURED-090 2026-08-02] — owner: "if MINDS sits
# at 0.82 I want 0.90". Measured frequency budget of the 512 paint (FFT power
# of luma, ring r in [64,256] over total r >= 2):
#
#   * r = 64  <=> period 8 px at 512 <=> 10 px at GEN(640) <=> 32 px at 2048
#   * r = 256 <=> period 2 px at 512 <=>  2.5 px at GEN    <=>  8 px at 2048
#
# so every pane, cane, quarry and came has to live at 7.5-9.5 px at GEN
# (24-30 px at 2048) with its harmonics filling the rest of the band. Four
# measured laws, none of which is "add noise" (white noise scores ~0.95 on
# band and FAILS every coherence guard — a static-looking window is a failure
# at any score):
#
#   L1 SCALE    — a lattice coarser than ~10 px at GEN drops its fundamental
#                 UNDER r=64 and the band collapses (cw 10.5 -> band 0.38 vs
#                 cw 9.0 -> 0.92 on the same field).
#   L2 FAT CAME — a WIDE, smooth came concentrates power at the lattice
#                 fundamental; hairline leading smears it into r>200 harmonics
#                 that wreck lag-1 coherence (w 0.12 -> band 0.69/ac 0.58,
#                 w 0.30 -> band 0.89/ac 0.72). Fat lead is the honest look.
#   L3 RELIEF   — a FLAT per-pane tint is a low-pass field (a raw 8-tier
#                 lattice measures band 0.15). The pane's own RELIEF must carry
#                 the value; the tier only tints it. Every generator here that
#                 already cleared 0.90 is one whose value is a smooth periodic
#                 profile.
#   L4 NO FBM   — a cubic-upscaled noise grid is low-pass by construction, so
#                 fbm CARRIERS (ream, slag, frost) cannot clear the band no
#                 matter how they are posterised. They are rebuilt on bounded
#                 jitter lattices (metaballs / Voronoi ridges), which billow
#                 and branch the same way with a fundamental in the band.
# ════════════════════════════════════════════════════════════════════════════

def _flat(x, s=3.0):
    """LOW-CUT on a value field: subtract its own local mean (drift coarser
    than ~4s px at GEN) and put the global mean back. NOT a noise term and not
    a sharpen — every shape and every edge survives untouched; only the slow
    field-wide wander that lands under the car band is deleted.
    [SPB-FRACTURED-090 2026-08-02]"""
    x = np.asarray(x, np.float32)
    return x - gauss(x, float(s)) + float(x.mean())


def _fat(d, w, soft=0.34):
    """Fat, smooth came profile from a 0..1 edge-distance field (0 = came
    centre). w may be scalar or a per-cell array. See L2.
    [SPB-FRACTURED-090 2026-08-02]"""
    w = np.asarray(w, np.float32)
    t = np.clip((d - w) / np.minimum(w * (float(soft) - 1.0), -1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _voro(res, cell, jit, salt):
    """Bounded-jitter Voronoi -> (F1/cell, (F2-F1)/cell edge distance, cell
    hash). [SPB-FRACTURED-090 2026-08-02] two properties the catlib worley
    cannot give, both of them gates: the jitter is BOUNDED so the glass
    lattice keeps a sharp spectral fundamental (an unbounded pack smears a
    third of its power under the car band), and F2-F1 is the true polygon edge
    distance, so every came is the SAME width — real leading instead of a
    morphological hairline."""
    yy, xx = coords(res)
    g = float(cell)
    ci, cj = np.floor(xx / g), np.floor(yy / g)
    f1 = np.full((res, res), 1e9, np.float32)
    f2 = np.full((res, res), 1e9, np.float32)
    idw = np.zeros((res, res), np.float32)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            a, b = ci + di, cj + dj
            px = (a + 0.5 + (h2(a, b, salt) - 0.5) * float(jit)) * g
            py = (b + 0.5 + (h2(a, b, salt + 40) - 0.5) * float(jit)) * g
            d = np.hypot(xx - px, yy - py).astype(np.float32)
            m = d < f1
            f2 = np.where(m, f1, np.minimum(f2, d))
            idw = np.where(m, h2(a, b, salt + 80), idw)
            f1 = np.where(m, d, f1)
    return np.clip(f1 / g, 0.0, 1.5), np.clip((f2 - f1) / g, 0.0, 1.5), idw


def _dots(res, cell, jit, salt):
    """Single-tap jittered-lattice dot field -> (0..1 radial distance, cell
    hash). One ninth the cost of _voro; used for second scales and for
    metaball carriers. [SPB-FRACTURED-090 2026-08-02 perf]"""
    yy, xx = coords(res)
    c = float(cell)
    ci, cj = np.floor(xx / c), np.floor(yy / c)
    jx = (h2(ci, cj, salt) - 0.5) * float(jit) * c
    jy = (h2(ci, cj, salt + 11) - 0.5) * float(jit) * c
    d = np.hypot(xx - (ci + 0.5) * c - jx, yy - (cj + 0.5) * c - jy) / (c * 0.62)
    return np.clip(d, 0.0, 1.0), h2(ci, cj, salt + 23)


def _ptier(res, cell, salt, ang=0.0, relief=0.55, jit=0.30):
    """Per-patch 8-tier glass tint on an IN-BAND pave (patch = cell px at GEN,
    softly domed, jittered). [SPB-FRACTURED-090 2026-08-02] replaces every
    fbm-derived tier: noise grids are low-pass (L4) and flat per-cell tints are
    low-pass too (L3), so the tint arrives with its own domed pane."""
    yy, xx = coords(res)
    if ang:
        u, v = rot((yy, xx), float(ang))
    else:
        u, v = xx, yy
    c = float(cell)
    ci, cj = np.floor(u / c), np.floor(v / c)
    jx = (h2(ci, cj, salt + 3) - 0.5) * float(jit)
    jy = (h2(ci, cj, salt + 7) - 0.5) * float(jit)
    d = np.maximum(np.abs(frac(u / c) - 0.5 + jx), np.abs(frac(v / c) - 0.5 + jy)) * 2.0
    bump = sstep(1.02, 0.24, d)
    return _tier(h2(ci, cj, salt)) * (1.0 - float(relief) + float(relief) * bump)


def _grain(res, seed, salt, amt=0.14, base=80):
    """BAND-PASSED glass relief: one octave at ~8 px at GEN, then low-cut.
    [SPB-FRACTURED-090 2026-08-02] the old 2-octave/base-130 grain was the
    single biggest leak in the module — a cubic-upscaled random grid is a
    LOW-pass field, so it dumped most of its power under r=64. Low-cutting
    keeps every visible seed and ream and returns the power to the band;
    amplitude is re-normalised so the look is unchanged."""
    g = fbm(res, res, rng(seed, salt), 1, int(base))
    g = g - gauss(g, 2.2)
    return (g / (float(g.std()) + 1e-6)) * (0.34 * float(amt))


def _hexlattice(res, cell, jit, salt):
    """Offset-row point lattice: (dist px, ci, cj)."""
    yy, xx = coords(res)
    g = float(cell)
    row = np.floor(yy / g)
    xo = xx + np.mod(row, 2.0) * 0.5 * g
    ci = np.floor(xo / g)
    jx = (h2(ci, row, salt) - 0.5) * float(jit) * g
    jy = (h2(ci, row, salt + 3) - 0.5) * float(jit) * g
    d = np.hypot(xo - (ci + 0.5) * g - jx, yy - (row + 0.5) * g - jy)
    return d, ci, row


def _T(lead_t, pane, came, span=0.62):
    """Dark-lead assembly: cames at the LUT null, panes lifted above it."""
    return frac(lead_t + (0.22 + np.clip(pane, 0.0, 1.15) * float(span))
                * (1.0 - np.clip(came, 0.0, 1.0)))


# ════════════════════════════════════════════════════════════════════════════
# STRUCTURAL GENERATORS — every one a dense wall of small glass, built to the
# micro-field law above. [SPB-FRACTURED-090 2026-08-02]
# ════════════════════════════════════════════════════════════════════════════

def g_quarrypave(res, seed, cell=8.6, lead=0.30, dome=0.50, lead_t=0.0,
                 fine=0.12, body=0.30):
    """quarry pave — a diamond diaper of small domed quarries (~28 px at
    2048), fat cames between. [SPB-FRACTURED-090] lead 0.16 -> 0.30 and the
    quarry's own dome carries the value (L2, L3)."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 311, 2.5)
    u, v = rot((yy + wv, xx + wu), 0.785)
    g = float(cell)
    ci, cj = np.floor(u / g), np.floor(v / g)
    fi, fj = frac(u / g), frac(v / g)
    db = np.minimum(np.minimum(fi, 1.0 - fi), np.minimum(fj, 1.0 - fj))
    came = _fat(db, float(lead))
    prof = (1.0 - (2.0 * fi - 1.0) ** 2) * (1.0 - (2.0 * fj - 1.0) ** 2)
    tier = _tier(h2(ci, cj, 312))
    pane = prof * float(dome) + tier * float(body) * (0.28 + 0.72 * prof) \
        + _grain(res, seed, 313, fine)
    return _T(lead_t, pane, came)


def g_oculipack(res, seed, cell=9.0, jit=0.24, lead_t=0.0, fine=0.12,
                body=0.30, rw=2.0):
    """ring-pack — many tiny came-ringed oculi with glowing domed discs; never
    one rose window. [SPB-FRACTURED-090] the came ring is a fat annulus and the
    disc is domed (L2, L3)."""
    d, ci, cj = _hexlattice(res, cell, jit, 321)
    g = float(cell)
    rr = g * (0.33 + 0.07 * h2(ci, cj, 322))
    ring = _fat(np.abs(d - rr) / float(rw), 1.0)
    dome = np.clip(1.0 - (d / np.maximum(rr, 1e-3)) ** 2, 0.0, 1.0)
    span_t = _tier(h2(ci, cj, 324))
    tier = _tier(h2(ci, cj, 323))
    pane = dome * 0.50 + (tier * 0.7 + span_t * 0.3) * float(body) * (0.28 + 0.72 * dome) \
        + _grain(res, seed, 325, fine)
    return _T(lead_t, pane, ring)


def g_striae(res, seed, pitch=8.6, angle=0.5, lead_t=0.0, fine=0.12,
             body=0.30):
    """directional-lamina — drawn-glass striae bands with per-segment tiers and
    came rules. [SPB-FRACTURED-090] pitch 4.8 -> 8.6 (a 5-px stria sits at
    r~128, past the coherent half of the band) and the band profile carries the
    value."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 331, 3.5)
    u, v = rot((yy + wv, xx + wu), float(angle))
    p = v / float(pitch)
    li = np.floor(p)
    fv = frac(p)
    tier = _tier(h2(li, np.floor(u / float(pitch * 1.4)), 332))
    prof = 1.0 - np.abs(2.0 * fv - 1.0)
    rule = _fat(np.abs(fv - 0.5), 0.26) * (h2(li, 0.0, 333) > 0.55)
    pane = prof * 0.44 + tier * float(body) * (0.28 + 0.72 * prof) \
        + _grain(res, seed, 335, fine)
    return _T(lead_t, pane, rule)


def g_pantiles(res, seed, cw=8.8, lead_t=0.0, fine=0.12, body=0.30):
    """scale imbrication — overlapping crown scales, came along every scallop,
    spun ripple inside each scale. [SPB-FRACTURED-090] the scale DOME carries
    the value and the scallop came is fat."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 341, 2.5)
    u = xx + wu; v = yy + wv
    g = float(cw)
    row = np.floor(v / g)
    uo = u + np.mod(row, 2.0) * 0.5 * g
    iu = np.floor(uo / g)
    fu = frac(uo / g) - 0.5
    fv = frac(v / g)
    sd = np.hypot(fu * 1.12, fv * 0.92)
    came = _fat(np.abs(sd - 0.5), 0.17)
    dome = np.clip(1.0 - sd * 1.9, 0.0, 1.0) ** 0.8
    rip = 0.5 + 0.5 * np.cos(sd * (7.0 + 3.0 * h2(iu, row, 342)) + h2(iu, row, 343) * 6.28)
    tier = _tier(h2(iu, row, 344))
    pane = dome * 0.44 + rip * 0.14 + tier * float(body) * (0.28 + 0.72 * dome) \
        + _grain(res, seed, 345, fine)
    return _T(lead_t, pane, came)


def g_seedfoam(res, seed, cells=70, cells2=112, lead_t=0.0, fine=0.12,
               body=0.26):
    """foam pack — packed seedy bubble glass with dark meniscus walls and a
    dust of seeds inside. [SPB-FRACTURED-090] both scales moved onto bounded
    lattices with true F2-F1 menisci (L1, L2)."""
    f1, e1, i1 = _voro(res, float(res) / float(cells), 0.50, 351)
    d2, i2 = _dots(res, float(res) / float(cells2), 0.55, 356)
    e2 = 1.0 - d2
    t1 = _tier(h2(np.floor(i1 * 997.0), 0.0, 354))
    t2 = _tier(h2(np.floor(i2 * 991.0), 5.0, 352))
    dome = sstep(0.02, 0.46, e1) * 0.80 + sstep(0.05, 0.55, e2) * 0.30
    wall = np.clip(_fat(e1, 0.22) + _fat(e2, 0.26) * 0.45, 0.0, 1.0)
    pane = dome * 0.50 + (t1 * 0.60 + t2 * 0.30) * float(body) * (0.28 + 0.72 * dome) \
        + _grain(res, seed, 355, fine)
    return _T(lead_t, pane, wall)


def g_frit(res, seed, cw0=9.0, lead_t=0.0, fine=0.12, body=0.62):
    """granular scatter — confetti frit: faceted glass chips at three scales
    fused in a clear matrix. [SPB-FRACTURED-090] every chip is a FACETED plate
    inset in its cell with a matrix gap around it; flat chips that fill their
    whole cell are a low-pass field (L3). The coarse scale is a full pave so
    there is no dead ground."""
    yy, xx = coords(res)
    pane = np.zeros((res, res), np.float32)
    for k, cw in enumerate((float(cw0), float(cw0) * 0.66, float(cw0) * 0.45)):
        u, v = rot((yy, xx), 0.3 + k * 0.9)
        ci, cj = np.floor(u / cw), np.floor(v / cw)
        dch = np.maximum(np.abs(frac(u / cw) - 0.5), np.abs(frac(v / cw) - 0.5)) * 2.0
        facet = sstep(0.92, 0.18, dch) * (0.55 + 0.45 * (1.0 - dch))
        pres = 1.0 if k == 0 else (h2(ci, cj, 361 + k * 7) > (0.30 + 0.22 * k)).astype(np.float32)
        pane = pane + pres * facet * _tier(h2(ci, cj, 363 + k * 7)) * (0.62 - 0.17 * k)
    pane = pane * float(body) + _grain(res, seed, 368, fine)
    edges = sstep(0.12, 0.30, np.abs(cv2.Laplacian(gauss(pane, 0.8), cv2.CV_32F)))
    return _T(lead_t, pane, edges * 0.5)


def g_tracery(res, seed, pitch=8.8, drop=0.10, lead_t=0.0, fine=0.12,
              body=0.30, lw=0.30):
    """star-lattice — a 60-degree tracery mesh: fat came bars, glass triangles
    with per-cell tiers and an interior swell. [SPB-FRACTURED-090] bars 0.10 ->
    0.30 of the pitch (L2) and the triangle swell carries the value (L3)."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 371, 2.5)
    a0 = float(rng(seed, 372).uniform(0, np.pi))
    came = np.zeros((res, res), np.float32)
    swell = np.zeros((res, res), np.float32)
    idsum = np.zeros((res, res), np.float32)
    for k in range(3):
        u, v = rot((yy + wv, xx + wu), a0 + k * np.pi / 3.0)
        pv = v / float(pitch)
        iv = np.floor(pv)
        dv = np.abs(frac(pv) - 0.5)
        bar = _fat(dv, float(lw)) * (h2(iv, float(k), 373 + k) > float(drop))
        came = np.maximum(came, bar)
        swell = swell + sstep(float(lw), 0.5, dv)
        idsum = idsum + iv * (k + 1.0)
    sw = swell * (1.0 / 3.0)
    tier = _tier(h2(idsum, 0.0, 377))
    pane = sw * 0.50 + tier * float(body) * (0.28 + 0.72 * sw) + _grain(res, seed, 378, fine)
    return _T(lead_t, pane, came)


def g_combglass(res, seed, pitch=8.4, amp=4.0, angle=0.95, lead_t=0.0,
                fine=0.12, body=0.30):
    """flow-combed strands — combed opalescent strand glass with per-segment
    tiers and dashed pull cames. [SPB-FRACTURED-090] pitch 4.2 -> 8.4 and comb
    amplitude 8 -> 4: a 4-px strand sits at r~150 and a big comb displacement
    smears the fundamental (L1)."""
    yy, xx = coords(res)
    u, v = rot((yy, xx), float(angle))
    flow = (fbm(res, res, rng(seed, 381), 3, 18) - 0.5) * float(amp)
    p = (v + flow) / float(pitch)
    si = np.floor(p)
    sg = np.floor(u / float(pitch * 1.4))
    prof = (1.0 - np.abs(2.0 * frac(p) - 1.0)) ** 1.1
    tier = _tier(h2(si, sg, 382))
    pull = _fat(np.abs(frac(p) - 0.5), 0.26) * (h2(si, sg, 383) > 0.72)
    pane = prof * 0.44 + tier * float(body) * (0.28 + 0.72 * prof) \
        + _grain(res, seed, 384, fine)
    return _T(lead_t, pane, pull)


def g_spunfield(res, seed, centers=5, freq=0.88, lead_t=0.0, fine=0.12,
                body=0.55):
    """micro-ripple carpet — spun-glass ripples from many centres interfering;
    fat came at the deepest troughs. [SPB-FRACTURED-090] ripple period 6.0 ->
    7.1 px at GEN and the trough came is fat."""
    yy, xx = coords(res)
    r0 = rng(seed, 391)
    g = res / float(centers)
    ph = np.zeros((res, res), np.float32)
    wsum = np.zeros((res, res), np.float32)
    for j in range(int(centers)):
        for i in range(int(centers)):
            cx = (i + 0.5 + float(r0.uniform(-0.35, 0.35))) * g
            cy = (j + 0.5 + float(r0.uniform(-0.35, 0.35))) * g
            d = np.hypot(xx - cx, yy - cy)
            w = np.exp(-(d / (g * 1.15)) ** 2)
            ph = ph + np.cos(d * float(freq) + float(r0.uniform(0, 6.28))) * w
            wsum = wsum + w
    rip = ph / np.maximum(wsum, 1e-4)
    env = np.sqrt(gauss(rip * rip, 9.0)) + 1e-4
    rip = np.clip(rip / env, -1.6, 1.6) * 0.6
    crest = n01(rip)
    tier = _TIERS[np.clip((crest * 8.0).astype(np.int32), 0, 7)]
    came = _fat(np.abs(rip + 0.55), 0.16)
    pane = crest * 0.30 + tier * float(body) + _grain(res, seed, 392, fine)
    return _T(lead_t, pane, came)


def g_canepack(res, seed, cells=76, lead_t=0.0, fine=0.12, body=0.34,
               jit=0.36):
    """interlocking-cells — a millefiori cane pack: small rounded cane faces
    with an inner ring and dark interstices. [SPB-FRACTURED-090] moved onto a
    bounded lattice with a true F2-F1 interstice (L1) — the unbounded worley
    pack smeared half its power under the band."""
    f1, edge, bid = _voro(res, float(res) / float(cells), float(jit), 401)
    face = sstep(0.03, 0.30, edge)
    dome = sstep(0.02, 0.46, edge)
    innr = _fat(np.abs(edge - 0.24), 0.10) * 0.55
    tier = _tier(h2(np.floor(bid * 997.0), 0.0, 402))
    tier2 = _tier(h2(np.floor(bid * 991.0), 3.0, 403))
    gap = np.clip(_fat(edge, 0.20) * 1.15, 0.0, 1.0)
    pane = dome * 0.50 + innr * tier2 * 0.30 \
        + tier * face * float(body) * (0.28 + 0.72 * dome) + _grain(res, seed, 404, fine)
    return _T(lead_t, pane, gap)


def g_leadweave(res, seed, pitch=9.5, gap=0.34, angle=0.15, lead_t=0.0,
                fine=0.12, body=0.30):
    """woven-cross — a leaded basket weave: glass bands passing over and under,
    came shadows at every crossing. [SPB-FRACTURED-090] the band's own
    over/under RIDGE carries the value (L3)."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 411, 2.5)
    u, v = rot((yy + wv, xx + wu), float(angle))
    pu, pv = u / float(pitch), v / float(pitch)
    iu, iv = np.floor(pu), np.floor(pv)
    fu, fv = frac(pu), frac(pv)
    bu = sstep(float(gap) * 0.5, float(gap) * 0.5 + 0.18, 0.5 - np.abs(fu - 0.5))
    bv = sstep(float(gap) * 0.5, float(gap) * 0.5 + 0.18, 0.5 - np.abs(fv - 0.5))
    par = np.mod(iu + iv, 2.0)
    ridgeu = 1.0 - np.abs(2.0 * fu - 1.0)
    ridgev = 1.0 - np.abs(2.0 * fv - 1.0)
    over = np.where(par > 0.5, bu * (0.40 + 0.60 * ridgeu), bv * (0.40 + 0.60 * ridgev))
    tier = _tier(np.where(par > 0.5, h2(iu, 0.0, 412), h2(iv, 1.0, 413)))
    came = sstep(0.42, 0.86, 1.0 - np.maximum(bu, bv))
    pane = over * 0.50 + tier * float(body) * (0.28 + 0.72 * over) \
        + _grain(res, seed, 414, fine)
    return _T(lead_t, pane, came)


def g_pleats(res, seed, pitch=8.0, rowh=11.0, angle=0.6, lead_t=0.0,
             fine=0.12, body=0.30):
    """chevron pleats — pleated drapery-glass herringbone, came at the pleat
    junctions. [SPB-FRACTURED-090] hatch 4.5 -> 8.0 px (L1) and the pleat
    ridge carries the value with a fat junction came."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 421, 2.5)
    u, v = rot((yy + wv, xx + wu), float(angle))
    row = np.floor(v / float(rowh))
    sgn = np.where(np.mod(row, 2.0) > 0.5, 1.0, -1.0)
    hatch = u * 0.9 * sgn + v * 0.45
    hi = np.floor(hatch / float(pitch))
    prof = 1.0 - np.abs(2.0 * frac(hatch / float(pitch)) - 1.0)
    tier = _tier(h2(hi, row, 422))
    junc = _fat(np.abs(frac(v / float(rowh)) - 0.5), 0.22)
    pane = prof * 0.50 + tier * float(body) * (0.28 + 0.72 * prof) \
        + _grain(res, seed, 423, fine)
    return _T(lead_t, pane, junc * 0.9)


def g_slagpool(res, seed, cell=9.5, lead_t=0.0, fine=0.12, body=0.58,
               flat=1.1, soft=1.3):
    """micro-billows — posterised slag-glass marbling pools in 8 tiers with
    dark cord lines at the steepest gradients. [SPB-FRACTURED-090] the marbling
    carrier moved OFF fbm onto a three-scale METABALL field (L4): posterising a
    noise grid fixes the histogram, not the spectrum."""
    a1, i1 = _dots(res, float(cell), 0.85, 431)
    a2, i2 = _dots(res, float(cell) * 0.66, 0.90, 435)
    a3, i3 = _dots(res, float(cell) * 0.45, 0.95, 439)
    t = ((1.0 - a1) ** 1.5 * (0.45 + 0.55 * i1) * 0.50
         + (1.0 - a2) ** 1.5 * (0.45 + 0.55 * i2) * 0.32
         + (1.0 - a3) ** 1.5 * (0.45 + 0.55 * i3) * 0.18)
    if soft > 0.0:
        t = gauss(t, soft)
    t = n01(_flat(t, flat))
    tier = _TIERS[np.clip((t * 8.0).astype(np.int32), 0, 7)]
    gy, gx = np.gradient(gauss(t, 1.2))
    cord = sstep(0.55, 0.90, n01(np.hypot(gx, gy)))
    pane = t * 0.40 + tier * float(body) * 0.55 + _grain(res, seed, 434, fine)
    return _T(lead_t, pane, cord * 0.7)


def g_jeweldust(res, seed, cw0=9.0, lead_t=0.0, fine=0.12, body=0.95):
    """structured dust — faceted jewel-chip dust at three scales, each chip its
    own tier, came flash between the largest chips. [SPB-FRACTURED-090] chips
    are faceted plates inset in their cells (L3) and the coarse scale is a full
    pave, so there is no dead ground."""
    yy, xx = coords(res)
    u, v = rot((yy, xx), 0.785)
    order = 0.5 + 0.5 * np.cos(u / 24.0) * np.cos(v / 24.0)
    pane = np.zeros((res, res), np.float32)
    big = np.zeros((res, res), np.float32)
    for k, cw in enumerate((float(cw0), float(cw0) * 0.66, float(cw0) * 0.45)):
        ci, cj = np.floor(xx / cw), np.floor(yy / cw)
        dch = np.maximum(np.abs(frac(xx / cw) - 0.5), np.abs(frac(yy / cw) - 0.5)) * 2.0
        facet = sstep(0.92, 0.18, dch) * (0.55 + 0.45 * (1.0 - dch))
        pres = 1.0 if k == 0 else (h2(ci, cj, 441 + k * 5) > (0.30 + 0.22 * k)).astype(np.float32)
        chip = pres * facet
        pane = pane + chip * _tier(h2(ci, cj, 443 + k * 5)) * (0.62 - 0.17 * k)
        if k == 0:
            big = chip
    came = sstep(0.5, 0.9, gauss(1.0 - big, 0.8)) * 0.55
    pane = pane * float(body) * (0.88 + 0.12 * order) + _grain(res, seed, 449, fine)
    return _T(lead_t, pane, came)


def g_trailthreads(res, seed, pitch=8.6, drift=7.0, lead_t=0.0, fine=0.12,
                   body=0.30):
    """thread-drift — trailed cane threads drifting across the sheet, every
    segment its own glass tier, came where threads pinch.
    [SPB-FRACTURED-090] drift 22 -> 7 px: a big smooth displacement SMEARS the
    thread lattice's fundamental under r=64 (L1)."""
    yy, xx = coords(res)
    flow = (fbm(res, res, rng(seed, 451), 3, 16) - 0.5) * float(drift)
    flow2 = (fbm(res, res, rng(seed, 452), 2, 40) - 0.5) * float(drift) * 0.45
    p = (yy + flow + flow2) / float(pitch)
    ti = np.floor(p)
    seg = np.floor(xx / float(pitch * 1.4))
    prof = sstep(0.30, 0.86, 1.0 - np.abs(2.0 * frac(p) - 1.0))
    tier = _tier(h2(ti, seg, 453))
    pinch = _fat(np.abs(frac(p) - 0.5), 0.30) * (h2(ti, seg + 9.0, 454) > 0.45)
    pane = prof * 0.44 + tier * float(body) * (0.28 + 0.72 * prof) \
        + _grain(res, seed, 455, fine)
    return _T(lead_t, pane, pinch)


def g_icecrackle(res, seed, cells=72, drop=0.20, width=0.30, angle=0.3,
                 lead_t=0.0, fine=0.12, body=0.40):
    """crackle-net — a two-scale ice-crackle came web over tiered glass plates
    (~28 px at 2048). [SPB-FRACTURED-090] the crack is a SMOOTH profile of the
    distance to the cell wall (not a hard frac<w test) so every came is an
    even-width lead line, and the plates curl up off the cracks (L2, L3)."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 461, 3.0)

    def web(cw, a, dropv, salt):
        u, v = rot((yy + wv, xx + wu), a)
        iu, iv = np.floor(u / cw), np.floor(v / cw)
        fu, fv = frac(u / cw), frac(v / cw)
        wu_ = float(width) * (0.7 + 0.6 * h2(iu, iv, salt))
        wv2 = float(width) * (0.7 + 0.6 * h2(iv, iu, salt + 1))
        ev = _fat(np.abs(fu - 0.5), wu_) * (h2(iu, iv, salt + 2) > dropv)
        eh = _fat(np.abs(fv - 0.5), wv2) * (h2(iv, iu, salt + 4) > dropv)
        return np.maximum(ev, eh), h2(iu, iv, salt + 6)
    cw1 = res / float(cells)
    w1, t1 = web(cw1, float(angle), float(drop), 462)
    w2, _ = web(cw1 * 0.55, float(angle) + 0.4, float(drop) + 0.32, 469)
    came = np.clip(w1 + w2 * 0.45, 0.0, 1.0)
    curl = 1.0 - came
    pane = curl * 0.42 + _tier(t1) * float(body) * (0.30 + 0.70 * curl) \
        + _grain(res, seed, 463, fine)
    return _T(lead_t, pane, came)


def g_frostfern(res, seed, cell=9.0, iters=3, lead_t=0.0, fine=0.12,
                body=0.34, thick=0.6, jit=0.55):
    """dendrite forest — glue-chip frost ferns: a bright feathery crystal grown
    in EVERY lattice cell, arms interlocking wall to wall.
    [SPB-FRACTURED-090] the old scatter (0.2 pct seed density) made a few large
    sparse ferns — sparse features on quiet ground are a low-pass field. One
    fern per 9-px cell with a per-cell growth axis keeps the habit and fills
    the sheet (which the coverage law wants anyway)."""
    yy, xx = coords(res)
    c = float(cell)
    ci, cj = np.floor(xx / c), np.floor(yy / c)
    jx = (h2(ci, cj, 471) - 0.5) * float(jit) * c
    jy = (h2(ci, cj, 476) - 0.5) * float(jit) * c
    d = np.hypot(xx - (ci + 0.5) * c - jx, yy - (cj + 0.5) * c - jy)
    acc = (d < 0.9).astype(np.float32) * (0.55 + 0.45 * h2(ci, cj, 472))
    k1 = np.array([[0, 1, 0], [0, 1, 0], [0, 1, 0]], np.uint8)
    k2 = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], np.uint8)
    k3 = np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]], np.uint8)
    ks = (k1, k1.T, k2, k3)
    axis = np.clip((h2(ci, cj, 477) * 4.0).astype(np.int32), 0, 3)
    for i in range(int(iters)):
        grow = np.zeros_like(acc)
        for a in range(4):
            grow = np.maximum(grow, cv2.dilate(acc * (axis == a), ks[(a + i) % 4]))
        acc = np.maximum(acc, grow * 0.93)
    if thick > 0.0:
        acc = gauss(acc, thick)
    fern = np.clip(acc * 1.7, 0.0, 1.0)
    tier = _ptier(res, 8.4, 474, 0.35)
    pane = fern * 0.44 + tier * float(body) * 0.70 + _grain(res, seed, 475, fine)
    shadow = sstep(0.10, 0.28, gauss(fern, 1.5)) * (1.0 - fern) * 0.5
    return _T(lead_t, pane, shadow)


def g_reamy(res, seed, sig=0.45, iters=8, lead_t=0.0, fine=0.12, body=0.34):
    """RD labyrinth — reamy labyrinth glass: Turing stripes of thick and thin
    glass, came in the deepest channels. [SPB-FRACTURED-090] the Turing
    wavelength scales WITH sig; 0.65 produced a 12-px stripe whose fundamental
    fell under r=64. 0.45 lands it at ~8 px at GEN, the came is fat and the
    glass tier moved onto an in-band pave."""
    x = fbm(res, res, rng(seed, 481), 3, 24) - 0.5
    for _ in range(int(iters)):
        x = np.tanh((gauss(x, float(sig)) - gauss(x, float(sig) * 2.6)) * 14.0)
    stripe = 0.5 + 0.5 * x
    came = _fat(np.abs(stripe - 0.18), 0.22)
    wallprof = sstep(0.70, 0.10, stripe)
    tier = _ptier(res, 8.8, 482, 1.1)
    pane = wallprof * 0.50 + tier * float(body) * (0.28 + 0.72 * wallprof) \
        + _grain(res, seed, 483, fine)
    return _T(lead_t, pane, came)


def g_stringerfelt(res, seed, cell=8.0, ln=7, lead_t=0.0, fine=0.12,
                   body=0.55, thick=0.6, jit=0.60):
    """needle felt — one fused glass stringer laid in EVERY lattice cell (3
    clustered orientations, an anisotropic fall), came dust between.
    [SPB-FRACTURED-090] the old scatter left big quiet gaps between stringers,
    so the felt read as a low-pass field; a stringer per 8-px cell is the same
    felt at the car-band scale with no dead ground, and 7 px is the longest a
    needle can be before its own axis falls under r=64."""
    yy, xx = coords(res)
    c = float(cell)
    ci, cj = np.floor(xx / c), np.floor(yy / c)
    jx = (h2(ci, cj, 491) - 0.5) * float(jit) * c
    jy = (h2(ci, cj, 495) - 0.5) * float(jit) * c
    dot = (np.hypot(xx - (ci + 0.5) * c - jx, yy - (cj + 0.5) * c - jy) < 0.9)
    ori = np.clip((h2(ci, cj, 497) * 3.0).astype(np.int32), 0, 2)
    val = (0.35 + 0.65 * _tier(h2(ci, cj, 498)))
    felt = np.zeros((res, res), np.float32)
    L = int(ln) | 1
    # [pair gate] 3 CLUSTERED orientations = a strongly anisotropic stringer
    # fall; 6 even ones read isotropic and collided with the pleats id.
    for k in range(3):
        m = (dot & (ori == k)).astype(np.float32) * val
        ker = np.zeros((L, L), np.float32)
        a = 2.05 + k * 0.35
        cs, sn = np.cos(a), np.sin(a)
        for t in range(L):
            px = int(round((L - 1) / 2 + (t - (L - 1) / 2) * cs))
            py = int(round((L - 1) / 2 + (t - (L - 1) / 2) * sn))
            ker[np.clip(py, 0, L - 1), np.clip(px, 0, L - 1)] = 1.0
        ker /= max(ker.sum(), 1.0)
        felt = np.maximum(felt, cv2.filter2D(m, -1, ker) * float(L) * 0.85)
    if thick > 0.0:
        felt = gauss(felt, thick)
    tier = _ptier(res, 8.6, 504, 0.85)
    dust = _fat(np.abs(frac(xx / 9.0) - 0.5), 0.10) * (h2(ci, cj, 505) > 0.86)
    pane = np.clip(felt, 0, 1.2) * 0.42 + tier * 0.55 * float(body) \
        + _grain(res, seed, 506, fine)
    return _T(lead_t, pane, dust * 0.7)


def g_veinweb(res, seed, cells1=74, cells2=124, thr=0.30, lead_t=0.0,
              fine=0.12, body=0.34):
    """branching-mesh — a ream vein web: bright thick-glass veins at two scales
    over tiered ground, came shadowing each vein flank.
    [SPB-FRACTURED-090] the vein carrier moved OFF ridged fbm onto two
    bounded-jitter Voronoi ridge webs (L4). A ridged fbm is a low-pass field
    dressed as a network; Voronoi ridges branch at true triple points (a better
    ream habit anyway) with a sharp in-band fundamental."""
    f1, e1, i1 = _voro(res, float(res) / float(cells1), 0.55, 511)
    f2, e2, i2 = _voro(res, float(res) / float(cells2), 0.62, 515)
    v1 = _fat(e1, float(thr))
    v2 = _fat(e2, float(thr) * 0.78)
    vein = np.maximum(v1, v2 * 0.85)
    flank = np.clip(_fat(e1, float(thr) * 1.9) - v1, 0.0, 1.0)
    relief = sstep(0.02, 0.44, e1)
    tier = _tier(h2(np.floor(i1 * 997.0), 0.0, 513))
    pane = relief * 0.42 + vein * 0.30 + tier * float(body) * (0.30 + 0.70 * relief) \
        + _grain(res, seed, 514, fine)
    return _T(lead_t, pane, flank * 0.55)


def _lowcut(fn):
    """Wrap a generator with the universal LOW-CUT knob (`lowcut` px at GEN).
    [SPB-FRACTURED-090 2026-08-02] the one dial that trades neighbour coherence
    for car-band energy: it subtracts the field's own slow local mean (keeping
    the global mean, so the LUT walk and the dark-lead anchor are unchanged)
    and therefore deletes power UNDER r=64 without touching a single shape or
    edge."""
    def g(res, seed, lowcut=0.0, **kw):
        T = fn(res, seed, **kw)
        lc = float(lowcut)
        if lc > 0.0:
            T = np.asarray(T, np.float32)
            T = T - (gauss(T, lc) - float(T.mean()))
            T = np.clip(T, 0.002, 0.998)
        return T
    g.__name__ = fn.__name__
    g.__doc__ = fn.__doc__
    g.__wrapped__ = fn
    return g


ENGINES = {
    "quarrypave": g_quarrypave, "oculipack": g_oculipack, "striae": g_striae,
    "pantiles": g_pantiles, "seedfoam": g_seedfoam, "frit": g_frit,
    "tracery": g_tracery, "combglass": g_combglass, "spunfield": g_spunfield,
    "canepack": g_canepack, "leadweave": g_leadweave, "pleats": g_pleats,
    "slagpool": g_slagpool, "jeweldust": g_jeweldust,
    "trailthreads": g_trailthreads, "icecrackle": g_icecrackle,
    "frostfern": g_frostfern, "reamy": g_reamy,
    "stringerfelt": g_stringerfelt, "veinweb": g_veinweb,
}
ENGINES = {k: _lowcut(v) for k, v in ENGINES.items()}


# ════════════════════════════════════════════════════════════════════════════
# CATEGORY-SPECIFIC MACRO KIND — lancet. [SPB-FRACTURED-FIELD 2026-08-02]
# kept for the extra_macro contract; used only as GENTLE modulation.
# ════════════════════════════════════════════════════════════════════════════

def m_lancet(r, mp, seed, K):
    """Pointed-arch lancet window: luminous parabolic-point arch on a dark
    wall; horizontal course bands = domain."""
    yy, xx = K.coords(r)
    u = (xx / r) - 0.5
    v = 1.0 - (yy / r)
    halfw = float(mp.get("halfw", 0.24))
    spring = float(mp.get("spring", 0.42))
    apex = float(mp.get("apex", 0.92))
    base = float(mp.get("base", 0.06))
    top = spring + (apex - spring) * np.clip(1.0 - (u / halfw) ** 2, 0.0, 1.0)
    inside = (np.abs(u) < halfw) & (v > base) & (v < top)
    du = np.clip(np.abs(u) - halfw, 0.0, 1.0)
    dv = np.clip(v - top, 0.0, 1.0) + np.clip(base - v, 0.0, 1.0)
    glow = np.exp(-((du * 3.0) ** 2 + (dv * 2.0) ** 2) * 6.0)
    M = np.clip(inside.astype(np.float32) * 1.05 + glow * 0.35, 0.0, 1.0)
    courses = float(mp.get("courses", 6.0))
    D = K.n01(K.h2(np.floor(v * courses), np.floor((u / halfw + 1.0) * 2.0), 43)
              + v * 0.15)
    return M, D


# ════════════════════════════════════════════════════════════════════════════
# LEAD-VS-GLASS SPEC KIT — kept from pass 1 (the good physics): the LUT luma
# null identifies the cames (dull rough metal: M up, R high, Cc dull); panes
# carve as dielectric GLASS (M low, R low = glossy, Cc toward 16 with
# macro-domain travel). [SPB-FRACTURED-FIELD 2026-08-02] adds the pane-scale
# hue-domain override — every little pane its own glass color.
# ════════════════════════════════════════════════════════════════════════════

class _CathedralKit(catlib.CategoryKit):
    def macro_maps(self, d):
        # [SPB-FRACTURED-FIELD 2026-08-02 r2] hue-domain DEVICE per recipe
        # (parent visual review: one shared device = 20 siblings). Modes:
        #   cell  — per-shard/pane confetti (uniform: frac(U + x) is uniform)
        #   macro — domain patchwork (AT MOST 4 ids per module)
        #   flow  — directional hue drift (banding along huedir)
        #   cloud — soft hue clouds (fbm regions, huebase = scale)
        M, D = catlib.CategoryKit.macro_maps(self, d)
        g = self.GEN
        yy, xx = coords(g)
        sd = int(d["seed"])
        cw = float(d.get("huecell", 10.0))
        Df = h2(np.floor(xx / cw), np.floor(yy / cw), sd % 977)
        mode = d.get("huemode", "cell")
        if mode == "macro":
            Dm = frac(D + Df * float(d.get("huedither", 0.15)))
        elif mode == "flow":
            u, _v = rot((yy, xx), float(d.get("huedir", 0.6)))
            Dm = frac(u / float(d.get("huespan", g * 0.9)) + Df * 0.22 + D * 0.10)
        elif mode == "cloud":
            c = fbm(g, g, rng(sd, 881), 3, int(d.get("huebase", 4)))
            Dm = frac(c * 1.6 + Df * 0.32)   # dithered edges: cloud, not patchwork
        else:
            Dm = frac(Df + D * 0.28)
        return M, Dm

    def mk(self, fid):
        _spec0, paint_fn = catlib.CategoryKit.mk(self, fid)
        WORK = self.WORK
        rkw = self.ALL[fid].get("kw", {})

        def spec_fn(shape, mask, seed, sm):
            fh, fw = int(shape[0]), int(shape[1])
            m2 = np.asarray(mask, np.float32)
            if m2.ndim == 3:
                m2 = m2[:, :, 0]
            if m2.shape[:2] != (WORK, WORK):
                m2 = cv2.resize(m2, (WORK, WORK), interpolation=cv2.INTER_LINEAR)
            art = self.art_work_cached(fid)
            L = (0.299 * art[:, :, 0] + 0.587 * art[:, :, 1]
                 + 0.114 * art[:, :, 2]).astype(np.float32)
            _lo, _hi = np.percentile(L, 2.0), np.percentile(L, 98.0)
            pattern = np.clip((L - _lo) / max(float(_hi - _lo), 1e-6), 0.0, 1.0)
            fl = gauss(pattern, 1.2)
            gx = cv2.Sobel(fl, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(fl, cv2.CV_32F, 0, 1, ksize=3)
            edge = n01(np.hypot(gx, gy))
            micro = n01(pattern - gauss(pattern, 2.5))
            hsv = cv2.cvtColor((art * 255.0).astype(np.uint8), cv2.COLOR_RGB2HSV)
            hue = hsv[:, :, 0].astype(np.float32) * (1.0 / 179.0)
            satn = n01(hsv[:, :, 1].astype(np.float32))
            hdom = n01(gauss(hue * satn, 1.0))
            _, _dd = self.macro_cached(fid)
            domw = cv2.resize(_dd, (WORK, WORK), interpolation=cv2.INTER_NEAREST)
            msw = float(rkw.get("mswing", 1.2))
            came = sstep(0.30, 0.08, pattern)                # the dark lead skeleton
            # lead = dull metal; glass = dielectric with micro flake
            M = np.clip(26.0 + came * 150.0 + (micro - 0.5) * 60.0 * msw
                        + edge * 50.0, 6.0, 255.0)
            # panes GLOSSY, cames rough
            R = np.clip(30.0 + came * 190.0 + (0.5 - micro) * 36.0
                        + edge * 24.0, 8.0, 235.0)
            # clearcoat: wet glass on the panes, dead dull on the lead
            Cc = np.clip(18.0 + came * 210.0
                         + (1.0 - came) * (domw * 80.0 + hdom * 40.0)
                         + micro * 16.0, 16.0, 255.0)
            out = np.zeros((WORK, WORK, 4), np.uint8)
            mk_ = np.clip(m2, 0.0, 1.0)
            inv = 1.0 - mk_
            out[:, :, 0] = np.clip(M * mk_ + 4.0 * inv, 0, 255).astype(np.uint8)
            out[:, :, 1] = np.clip(R * mk_ + 120.0 * inv, 0, 255).astype(np.uint8)
            out[:, :, 2] = np.clip(Cc * mk_ + 16.0 * inv, 0, 255).astype(np.uint8)
            out[:, :, 3] = 255
            if (fh, fw) != (WORK, WORK):
                out = cv2.resize(out, (fw, fh), interpolation=cv2.INTER_LINEAR)
            return out

        return spec_fn, paint_fn


# ════════════════════════════════════════════════════════════════════════════
# RECIPES — 20 finishes, ids fca_*, seeds 1120-1139 (UNCHANGED ids/seeds).
# [SPB-FRACTURED-FIELD 2026-08-02] one archetype per id (ledger at top),
# cames pinned at the LUT luma null (lead_t, DYNAMIC probe), tmod=0.0,
# vd (0.93, 1.11), weighted jewel palettes picked per pane.
# ════════════════════════════════════════════════════════════════════════════

# gamma-2.0 LUT families (deep luma null) + probed null positions (dynamic).
L1 = (380.0, 970.0, 2.0, 1.35, 1.9)
L2 = (430.0, 905.0, 2.0, 1.35, 4.7)
L3 = (400.0, 940.0, 2.0, 1.35, 2.1)
L4 = (390.0, 960.0, 2.0, 1.35, 4.4)
L5 = (420.0, 900.0, 2.0, 1.35, 3.8)
LT1 = _lut_null(L1); LT2 = _lut_null(L2); LT3 = _lut_null(L3)
LT4 = _lut_null(L4); LT5 = _lut_null(L5)

# weighted jewel palettes (~43 pct hero + 4-5 jewel accents, 5+ hue bins) —
# "cathedral is inherently multi-color glass"
# [SPB-FRACTURED-090 2026-08-02] these were dead STRINGS and every recipe ran
# hues=None, i.e. the raw thin-film rainbow — "Ruby Lights" was not ruby. They
# are live weighted lists now: 8/11 of the panes wear the window's hero jewel,
# 3/11 are accents, so each window reads as ONE glass colour leaded in dark
# came. Metric-neutral: the hue window re-applies each pixel's own luma.
RUBY = [0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.055, 0.10, 0.78]
COBL = [0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.55, 0.47, 0.78]
EMER = [0.38, 0.38, 0.38, 0.38, 0.38, 0.38, 0.38, 0.38, 0.30, 0.47, 0.10]
AMBR = [0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.055, 0.16, 0.62]
VIOL = [0.78, 0.78, 0.78, 0.78, 0.78, 0.78, 0.78, 0.78, 0.72, 0.85, 0.62]
JEWL = [0.99, 0.99, 0.62, 0.62, 0.38, 0.38, 0.10, 0.10, 0.78, 0.78, 0.47]

_KW = dict(ambient=0.05, ambient_sigma=44, floor=0.11, sparkle=0.28)

NAVE_WINDOWS = {
 # [SPB-FRACTURED-FIELD 2026-08-02] quarry pave — small diamond quarries.
 "fca_ruby_lights": dict(huemode="macro", huecell=8.5, name="Ruby Lights", engine="quarrypave",
    eargs=dict(lead_t=LT3, cell=9.632, body=0.54, lowcut=0.0),
    seed=1120, lut=L3, val=0.30, hues=RUBY, hspan=0.045, satboost=0.98,
    macro=("bands", dict(angle=0.6, freq=2.5, warp=0.25)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.5, **_KW),
    desc="A wall of small ruby diamond quarries, jewel light in every pane. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] ring-pack — MANY tiny oculi (the grand
 # rose window is BANNED).
 "fca_cobalt_oculus": dict(huemode="macro", huecell=9.5, name="Cobalt Oculus", engine="oculipack",
    eargs=dict(lead_t=LT1, cell=11.52, body=0.45, lowcut=0.0),
    seed=1121, lut=L1, val=0.30, hues=COBL, hspan=0.045, satboost=0.98,
    macro=("continents", dict(base=4, cells=3.0)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Hundreds of tiny cobalt oculi, each ringed in dark lead and glowing. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] directional-lamina — drawn striae.
 "fca_emerald_streak": dict(huemode="flow", huedir=0.50, huecell=9.0, name="Emerald Streak", engine="striae",
    eargs=dict(lead_t=LT2, pitch=8.6, body=0.166, lowcut=0.0),
    seed=1122, lut=L2, val=0.30, hues=EMER, hspan=0.045, satboost=0.98,
    macro=("rachis", dict(angle=0.5, lanes=6.0)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.3, **_KW),
    desc="Fine drawn emerald striae, band on band of streaky poured glass. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] scale imbrication — small pantiles.
 "fca_crown_amber": dict(huecell=8.0, name="Crown Amber", engine="pantiles",
    eargs=dict(lead_t=LT5, cw=9.856, body=0.166, lowcut=0.0),
    seed=1123, lut=L5, val=0.30, hues=AMBR, hspan=0.045, satboost=0.98,
    macro=("domains", dict(cells=6, salt=1123)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.6, **_KW),
    desc="Small amber crown scales lapped row over row, spun ripples in each. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] foam pack — seedy bubble glass.
 "fca_bottle_violet": dict(huecell=7.5, name="Bottle Violet", engine="seedfoam",
    eargs=dict(lead_t=LT4, cells=44.0, body=0.468, lowcut=1.8),
    seed=1124, lut=L4, val=0.30, hues=VIOL, hspan=0.045, satboost=0.98,
    macro=("continents", dict(base=3, cells=3.5)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Violet bottle glass packed with bubbles, dark meniscus walls between. A FRACTURED CATHEDRAL finish."),
}

TRANSEPT_GLASS = {
 # [SPB-FRACTURED-FIELD 2026-08-02] granular scatter — confetti frit.
 "fca_amber_kiln": dict(huemode="macro", huecell=6.0, name="Amber Kiln", engine="frit",
    eargs=dict(lead_t=LT1, cw0=9.0, body=1.116, lowcut=1.8),
    seed=1125, lut=L1, val=0.30, hues=AMBR, hspan=0.045, satboost=0.98,
    macro=("continents", dict(base=3, cells=3.0)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Kiln-fused amber confetti frit, a thousand glass chips in clear matrix. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] star-lattice — fine tracery mesh.
 "fca_emerald_wheel": dict(huemode="cloud", huebase=4, huecell=9.0, name="Emerald Wheel", engine="tracery",
    eargs=dict(lead_t=LT3, pitch=9.856, body=0.166, lowcut=2.5),
    seed=1126, lut=L3, val=0.30, hues=EMER, hspan=0.045, satboost=0.98,
    macro=("vortex", dict(arms=2.0, twist=7.0)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="A fine emerald tracery mesh, glass triangles glowing between dark bars. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] flow-combed strands — combed opal glass.
 "fca_jewel_streak": dict(huemode="flow", huedir=0.95, huecell=9.0, name="Jewel Streak", engine="combglass",
    eargs=dict(lead_t=LT2, pitch=7.56, body=0.54, lowcut=0.0),
    seed=1127, lut=L2, val=0.30, hues=JEWL, hspan=0.05, satboost=1.25,
    macro=("bands", dict(angle=0.95, freq=2.5, warp=0.25)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Opalescent strands combed fine, every pull a different jewel. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] micro-ripple carpet — spun ripples.
 "fca_crown_cobalt": dict(huemode="cloud", huebase=3, huecell=13.0, name="Crown Cobalt", engine="spunfield",
    eargs=dict(lead_t=LT4, freq=0.688, body=0.468, lowcut=1.8),
    seed=1128, lut=L4, val=0.30, hues=COBL, hspan=0.045, satboost=0.98,
    macro=("domains", dict(cells=7, salt=1128)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Cobalt spun-glass ripples from many centres, interfering wave on wave. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] interlocking-cells — cane pack.
 "fca_bottle_ruby": dict(huecell=6.5, name="Bottle Ruby", engine="canepack",
    eargs=dict(lead_t=LT1, cells=76.0, body=0.408, lowcut=0.0),
    seed=1129, lut=L1, val=0.30, hues=RUBY, hspan=0.045, satboost=0.98,
    macro=("margin", dict(freq=3.0, radius=0.72)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="A millefiori pack of small ruby cane faces, dark glass between. A FRACTURED CATHEDRAL finish."),
}

CHOIR_LIGHTS = {
 # [SPB-FRACTURED-FIELD 2026-08-02] woven-cross — leaded weave.
 "fca_emerald_quarry": dict(huecell=9.5, name="Emerald Quarry", engine="leadweave",
    eargs=dict(lead_t=LT4, pitch=9.5, body=0.45, lowcut=1.8),
    seed=1130, lut=L4, val=0.30, hues=EMER, hspan=0.045, satboost=0.98,
    macro=("continents", dict(base=3, cells=4.0)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Emerald glass bands woven through dark lead, over and under. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] chevron pleats — drapery herringbone.
 "fca_violet_rose": dict(huemode="flow", huedir=0.60, huecell=8.5, name="Violet Rose", engine="pleats",
    eargs=dict(lead_t=LT2, pitch=9.0, body=0.54, lowcut=2.5),
    seed=1131, lut=L2, val=0.30, hues=VIOL, hspan=0.045, satboost=0.98,
    macro=("continents", dict(base=3, cells=4.5)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Violet drapery glass pleated fine, herringbone folds catching light. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] micro-billows — slag marbling.
 "fca_amber_slag": dict(huemode="cloud", huebase=6, huecell=14.0, name="Amber Slag", engine="slagpool",
    eargs=dict(lead_t=LT3, cell=8.299, body=1.044, lowcut=1.0),
    seed=1132, lut=L3, val=0.30, hues=AMBR, hspan=0.045, satboost=0.98,
    macro=("continents", dict(base=3, cells=3.5)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Amber slag glass marbled in eight tiers, dark cords at every fold. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] structured dust — jewel chips.
 "fca_crown_jewels": dict(huecell=6.0, name="Crown Jewels", engine="jeweldust",
    eargs=dict(lead_t=LT1, cw0=9.0, body=0.524, lowcut=0.0),
    seed=1133, lut=L1, val=0.30, hues=JEWL, hspan=0.05, satboost=1.25,
    macro=("margin", dict(freq=2.5, radius=0.72)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.5, **_KW),
    desc="Faceted jewel chips at three sizes, dusted edge to edge in quiet order. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] thread-drift — trailed canes.
 "fca_bottle_cobalt": dict(huemode="flow", huedir=0.30, huecell=9.0, name="Bottle Cobalt", engine="trailthreads",
    eargs=dict(lead_t=LT2, pitch=6.037, body=0.36, lowcut=0.0),
    seed=1134, lut=L2, val=0.30, hues=COBL, hspan=0.045, satboost=0.98,
    macro=("river", None) if False else ("rachis", dict(angle=0.3, lanes=6.0)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Cobalt cane threads trailed across the sheet, drifting in slow current. A FRACTURED CATHEDRAL finish."),
}

APSE_ROUNDS = {
 # [SPB-FRACTURED-FIELD 2026-08-02] crackle-net — ice crackle.
 "fca_jewel_lights": dict(huemode="macro", huecell=8.0, name="Jewel Lights", engine="icecrackle",
    eargs=dict(lead_t=LT3, cells=72.0, body=0.72, lowcut=0.0),
    seed=1135, lut=L3, val=0.30, hues=JEWL, hspan=0.05, satboost=1.25,
    macro=("domains", dict(cells=6, salt=1135)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.5, **_KW),
    desc="Ice-crackle cames webbing a wall of small jewel plates. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] dendrite forest — frost ferns.
 "fca_ruby_rose": dict(huemode="cloud", huebase=5, huecell=12.0, name="Ruby Rose", engine="frostfern",
    eargs=dict(lead_t=LT4, cell=6.318, body=0.289, lowcut=2.5),
    seed=1136, lut=L4, val=0.30, hues=RUBY, hspan=0.045, satboost=0.98,
    macro=("continents", dict(base=3, cells=3.0)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Glue-chip frost ferns feathering bright across ruby glass. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] RD labyrinth — reamy stripes.
 "fca_cobalt_streak": dict(huemode="cloud", huebase=8, huecell=12.0, name="Cobalt Streak", engine="reamy",
    eargs=dict(lead_t=LT1, sig=0.576, body=0.408, lowcut=0.0),
    seed=1137, lut=L1, val=0.30, hues=COBL, hspan=0.045, satboost=0.98,
    macro=("bands", dict(angle=0.9, freq=2.5, warp=0.30)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Reamy cobalt labyrinth — thick and thin glass winding everywhere at once. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] needle felt — fused stringers.
 "fca_crown_violet": dict(huecell=11.0, name="Crown Violet", engine="stringerfelt",
    eargs=dict(lead_t=LT2, cell=9.5, ln=9, thick=1.0, body=0.99, lowcut=2.5),
    seed=1138, lut=L2, val=0.30, hues=VIOL, hspan=0.045, satboost=0.98,
    macro=("rings", dict(freq=3.5, two=True)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Violet stringer needles fused thousands deep across the sheet. A FRACTURED CATHEDRAL finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] branching-mesh — ream veins.
 "fca_bottle_emerald": dict(huecell=12.0, name="Bottle Emerald", engine="veinweb",
    eargs=dict(lead_t=LT3, cells1=74.0, body=0.612, lowcut=2.5),
    seed=1139, lut=L3, val=0.30, hues=EMER, hspan=0.045, satboost=0.98,
    macro=("vortex", dict(arms=1.0, twist=6.0)), vd=(0.93, 1.11), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Bright ream veins webbing emerald bottle glass at two scales. A FRACTURED CATHEDRAL finish."),
}

# weighted jewel palettes wired in
for _fid, _pal in [
    ("fca_ruby_lights", RUBY), ("fca_cobalt_oculus", COBL),
    ("fca_emerald_streak", EMER), ("fca_crown_amber", AMBR),
    ("fca_bottle_violet", VIOL), ("fca_amber_kiln", AMBR),
    ("fca_emerald_wheel", EMER), ("fca_jewel_streak", RUBY),
    ("fca_crown_cobalt", COBL), ("fca_bottle_ruby", RUBY),
    ("fca_emerald_quarry", EMER), ("fca_violet_rose", VIOL),
    ("fca_amber_slag", AMBR), ("fca_crown_jewels", COBL),
    ("fca_bottle_cobalt", COBL), ("fca_jewel_lights", VIOL),
    ("fca_ruby_rose", RUBY), ("fca_cobalt_streak", COBL),
    ("fca_crown_violet", VIOL), ("fca_bottle_emerald", EMER),
]:
    for _row in (NAVE_WINDOWS, TRANSEPT_GLASS, CHOIR_LIGHTS, APSE_ROUNDS):
        if _fid in _row:
            # [SPB-FRACTURED-090 2026-08-02] the palettes are real weighted
            # lists now (they used to be STRINGS parsed here), 8/11 hero jewel
            # + 3 accents so each window reads as ONE glass colour.
            _row[_fid]["hues"] = list(_pal)

GROUPS = {
    "NAVE WINDOWS": NAVE_WINDOWS,
    "TRANSEPT GLASS": TRANSEPT_GLASS,
    "CHOIR LIGHTS": CHOIR_LIGHTS,
    "APSE ROUNDS": APSE_ROUNDS,
}

KIT = _CathedralKit(engines=ENGINES, groups=GROUPS, tag="fractured-cathedral",
                    extra_macro={"lancet": m_lancet}, work=1024)

ALL = KIT.ALL
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)


# [wave-agent convenience 2026-07-30] bake_cat_thumbs imports THIS module
# before rebuild_thumbnails boots the engine; central JS/engine wiring lands
# later. When (and ONLY when) the thumbnail bake harness or the uniqueness
# gate is the entry point, self-register into
# shokker_engine_v2.MONOLITHIC_REGISTRY so those tools can resolve fca_* keys
# (engine.registry copies that dict AFTER this import, so entries propagate;
# the gate reads eng.MONOLITHIC_REGISTRY directly). Idempotent; a no-op in
# every other context (verify/montage install into a bare dict themselves).
def _bake_self_register():
    import sys as _sys
    if not any(("bake_cat_thumbs" in a or "rebuild_thumbnails" in a
                or "spb_uniqueness_gate" in a) for a in _sys.argv[:1]):
        return
    try:
        import shokker_engine_v2 as _e2
        install_into_engine(_e2.MONOLITHIC_REGISTRY)
    except Exception:
        pass


_bake_self_register()
