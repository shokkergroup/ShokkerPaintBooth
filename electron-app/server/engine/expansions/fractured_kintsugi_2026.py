# -*- coding: utf-8 -*-
"""FRACTURED KINTSUGI (2026-07-30) — category 9/10 of the FRACTURED expansion.

[SPB-FRACTURED-090 2026-08-02] THIRD pass — owner: "if MINDS sits at 0.82 I
want you to try to achieve 0.90 — we STRIVE to get better." Pass 2 left the
module at car-band MEDIAN 0.668 (FFT ring 64..256 of the 512 paint, over
total r>=2) against the FRACTURED MINDS flagship at 0.82. This pass measures
where the missing power actually sat and moves it, WITHOUT cheating: white
noise scores ~0.95 on that ring and is a failure at any score, so every
finish is now also held to four anti-static guards (lag-1 neighbour
coherence, spectral peakiness, connected-shape fraction, fineness).

RESULT: car-band median 0.668 -> 0.848, min 0.545 -> 0.677, and every finish
clears coherence >= 0.55 / peakiness >= 0.32 / shape-fraction >= 0.55 /
fineness > 6.5 / coverage 64 of 64 / hue bins >= 5 / < 1.3 s at 512 (0.9-1.1 s
at 2048). 10 of 20 clear the full 0.85 band bar; the rest sit 0.68-0.85. The
gain is structural, not grain — see THE MICRO-FIELD LAW below for the four
measured laws and the frequency budget they come from. The binding wall is
the joint constraint: band >= 0.85 needs power ABOVE r=64 while coherence
>= 0.55 needs it BELOW r~130, so the whole field has to live in a 4-8 px
window at GEN, and archetypes whose habit is naturally sparse or naturally
soft (foam, chip dust, Turing stripe, crystal forest) pay for every point.

ARCHETYPE LEDGER — 20 ids, 20 DISTINCT compositional archetypes (no two ids
share one; descriptor-verified):
  fki_golden_river         branching-mesh      (dense two-scale ridged gold vein web)
  fki_porcelain_mend       plate-mosaic        (worley shard pave, gold seams between)
  fki_cobalt_seam          directional-lamina  (fine strata + transverse gold faults)
  fki_celadon_vein         thread-drift        (drifting fine gold threads on jade)
  fki_cream_confluence     granular scatter    (ceramic grit, gold-wetted interstices)
  fki_cobalt_craquelure    crackle-net         (two-scale dropped-edge crack web)
  fki_gilded_craquelure    ring-pack           (MANY small gold rings on a jittered pack)
  fki_porcelain_craquelure scale imbrication   (tiny offset-row scallop crazing)
  fki_cream_craquelure     foam pack           (packed glaze bubbles, gold films at walls)
  fki_celadon_craquelure   star-lattice        (60-degree tri-lattice, gold nodes)
  fki_gilt_brushwork       flow-combed strands (tight combed micro-striation bundles)
  fki_cobalt_sweep         woven-cross         (micro basket weave, gold interlace)
  fki_celadon_sweep        micro-ripple carpet (interfering ripple sets from many centers)
  fki_moon_raku            micro-billows       (posterized turbulence cloudlets + rims)
  fki_golden_raku          chevron pleats      (fine herringbone pleats, gilt junctions)
  fki_cobalt_raku          interlocking-cells  (crawled glaze bead pack, carbon gaps)
  fki_celadon_raku         needle felt         (dense oriented carbon/gold needles)
  fki_gilt_shards          RD labyrinth        (Turing-stripe gold labyrinth)
  fki_cobalt_shards        dendrite forest     (many small grown gold crystals)
  fki_porcelain_shards     structured dust     (3-scale tinted chip dust, diagonal order)

Palette law [SPB-FRACTURED-090 2026-08-02]: HERO-DOMINANT 11-anchor ceramic
families — 8/11 of the shards wear the family hue, 3/11 are accents (one of
them true gold), and the hue DEVICE pools over several shards (huecell x4) so
a finish reads as one glazed body mended in gold instead of a rainbow
confetti of shards. Luma is untouched by any of that (the hue window
re-applies each pixel's own luma), so it is metric-neutral identity work + TRUE gold on the seams via the
gild pass, 8-tier per-feature brightness (_TIERS), never muddy. Gold physics kept from pass 1: gild = luma-gated warm-metal remap;
spec carves the seams METALLIC (M high) + GLOSSY (R low, Cc -> 16) over a
dielectric satin ceramic body (_KintsugiKit).

Built on engine/expansions/fractured_catlib_2026.py. Determinism: all
randomness via catlib.rng(seed, salt) (np.random.default_rng), integer salts
only, no hash(str) anywhere. All generators fully vectorized at GEN=640; the
only Python loops are small bounded ones (<= 9 dilation steps, <= 6
orientations, <= 25 ripple centers).
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions import fractured_catlib_2026 as catlib
from engine.expansions.fractured_catlib_2026 import (
    coords, fbm, frac, gauss, h2, n01, rng, rot, sstep, warp_pair, worley,
)

# 8-tier per-feature brightness palette (owner doctrine: many distinct value
# tiers, never 1-2 levels).
_TIERS = np.array([0.16, 0.26, 0.36, 0.46, 0.56, 0.66, 0.78, 0.92], np.float32)


def _tier(hv):
    return _TIERS[np.clip((np.asarray(hv, np.float32) * 8.0).astype(np.int32), 0, 7)]


def _lut_peak(lut):
    """T position (0..1) of the LUT's luma PEAK — the gold-seam anchor: seams
    pinned here are the brightest pixels, so the gild pass + the spec's
    bright-seam gate find them for ANY recipe. (Mirror of cathedral's
    dark-lead null probe.) [SPB-FRACTURED-FIELD 2026-08-02]"""
    t = catlib.thinfilm_lut(*lut)
    L = t[:, 0] * 0.299 + t[:, 1] * 0.587 + t[:, 2] * 0.114
    return float(np.argmax(L)) / float(len(L) - 1)


def _cells(res, seed, cells, salt, seamw=3):
    """Worley pave: (best distance 0..1, cell id 0..1, seam mask between cells
    via morphological gradient of the id field). [SPB-FRACTURED-090
    2026-08-02] seamw sizes the structuring element so the gold seam can be a
    real POURED vein (5-7 px at GEN) instead of a 1-px hairline — see L2 of
    the micro-field law."""
    best, bid = worley(res, seed, cells, salt)
    ks = int(seamw) | 1
    k = np.ones((ks, ks), np.uint8)
    seam = ((cv2.dilate(bid, k) - cv2.erode(bid, k)) > 1e-4).astype(np.float32)
    return best, bid, gauss(seam, max(0.6, ks * 0.30))


def _voro(res, cell, jit, salt):
    """Bounded-jitter Voronoi pave -> (F1/cell, (F2-F1)/cell edge distance,
    winning-cell hash). [SPB-FRACTURED-090 2026-08-02] two properties the
    catlib worley cannot give and both are gates:
      * jitter is BOUNDED (<= ~0.5 cell) so the shard lattice keeps a SHARP
        spectral fundamental — an unbounded pack smears a third of its power
        under the car band (measured: worley pave tops out at band 0.87 with
        lag-1 coherence 0.49, the bounded lattice clears 0.93/0.62);
      * F2-F1 is the true polygon edge distance, so every seam is the SAME
        width — a poured gold vein instead of a morphological hairline."""
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
    hash). One ninth the cost of _voro; used for SECOND scales where the exact
    polygon seam is not needed. [SPB-FRACTURED-090 2026-08-02 perf]"""
    yy, xx = coords(res)
    c = float(cell)
    ci, cj = np.floor(xx / c), np.floor(yy / c)
    jx = (h2(ci, cj, salt) - 0.5) * float(jit) * c
    jy = (h2(ci, cj, salt + 11) - 0.5) * float(jit) * c
    d = np.hypot(xx - (ci + 0.5) * c - jx, yy - (cj + 0.5) * c - jy) / (c * 0.62)
    return np.clip(d, 0.0, 1.0), h2(ci, cj, salt + 23)


def _grain(res, seed, salt, amt=0.22, base=80):
    """BAND-PASSED glaze relief: one octave at ~8 px at GEN (r ~ 78 at 512),
    then low-cut. [SPB-FRACTURED-090 2026-08-02] this term was the single
    biggest leak in the whole module — a cubic-upscaled random grid is a
    LOW-pass field, so the old grain dumped most of its power under r=64
    (measured on the shard pave: fine 0.10 -> band 0.825, fine 0 -> band
    0.921). Low-cutting it keeps every visible glaze mottle and returns the
    power to the band. Amplitude is re-normalised so the look is unchanged."""
    g = fbm(res, res, rng(seed, salt), 1, int(base))
    g = g - gauss(g, 2.2)
    return (g / (float(g.std()) + 1e-6)) * (0.34 * float(amt))


# ════════════════════════════════════════════════════════════════════════════
# THE MICRO-FIELD LAW  [SPB-FRACTURED-090 2026-08-02] — owner: "if MINDS sits
# at 0.82 I want 0.90". Measured frequency budget of the 512 paint (FFT power
# of luma, ring r in [64,256] over total r >= 2):
#
#   * r = 64  <=> period 8 px at 512 <=> 10 px at GEN(640) <=> 32 px at 2048
#   * r = 256 <=> period 2 px at 512 <=>  2.5 px at GEN    <=>  8 px at 2048
#
# so EVERY structure has to live at 7.5-9.5 px at GEN (24-30 px at 2048) with
# its harmonics filling the rest of the band. Three measured laws, none of
# which is "add noise" (white noise scores ~0.95 on band and FAILS every
# coherence guard — a static-looking finish is a failure at any score):
#
#   L1 SCALE     — a lattice coarser than ~10 px at GEN drops its fundamental
#                  UNDER r=64 and the band collapses (measured: cw 10.5 ->
#                  band 0.38 vs cw 9.0 -> 0.92).
#   L2 FAT SEAMS — a WIDE, smooth seam/came profile concentrates power at the
#                  lattice fundamental; hairlines smear it into r>200
#                  harmonics that wreck lag-1 coherence (measured, same field:
#                  w 0.12 -> band 0.69 / ac 0.58, w 0.30 -> band 0.89 / ac
#                  0.72). Fat seams are also the honest kintsugi look.
#   L3 LOW-CUT   — flat per-cell values leak a huge sub-band skirt (a raw
#                  8-tier pave field measures band 0.15 / low 0.85). _flat()
#                  deletes the drift under the band without touching a single
#                  shape edge.
# ════════════════════════════════════════════════════════════════════════════

def _flat(x, s=3.0):
    """LOW-CUT on a value field: subtract its own local mean (drift coarser
    than ~4s px at GEN) and put the global mean back. NOT a noise term and not
    a sharpen — every shape and every edge survives untouched; only the slow
    field-wide wander that lands under the car band (r < 64 at 512) is
    deleted. [SPB-FRACTURED-090 2026-08-02]"""
    x = np.asarray(x, np.float32)
    return x - gauss(x, float(s)) + float(x.mean())


def _fat(d, w, soft=0.34):
    """Fat, smooth seam profile from a 0..1 edge-distance field (0 = seam
    centre). w may be a scalar or a per-cell array (jittered seam widths).
    See L2 above. [SPB-FRACTURED-090 2026-08-02]"""
    w = np.asarray(w, np.float32)
    t = np.clip((d - w) / np.minimum(w * (float(soft) - 1.0), -1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _ptier(res, cell, salt, ang=0.0, relief=0.55, jit=0.30):
    """Per-patch 8-tier ceramic tint on an IN-BAND glaze pave (patch = cell px
    at GEN, softly domed, jittered).
    [SPB-FRACTURED-090 2026-08-02] replaces every fbm-derived tier in this
    module. Two measured reasons:
      * a cubic-upscaled noise grid is a LOW-pass field and dumps most of its
        power under r=64 (every fbm-tiered generator sat at band 0.34-0.60);
      * a FLAT per-cell tint is low-pass too (a raw 8-tier lattice measures
        band 0.15) — it only becomes band-pass once each patch carries a
        smooth relief, which is also what a real dipped glaze looks like.
    So the tint comes with its own domed patch."""
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


def _tflat(tier, s=0.0):
    """Low-cut applied to the FLAT per-shard tint only (never to the shard
    relief): flat cell values are the one component that leaks under the car
    band, and de-drifting them makes neighbouring shards CONTRAST instead of
    wandering — the same thing a glaze chemist gets from a randomised dip.
    [SPB-FRACTURED-090 2026-08-02]"""
    return _flat(tier, s) if s > 0.0 else tier


def _shape(bodyT, gold, flat=0.0, soft=0.0):
    """BAND-SHAPE the composed micro-field: `flat` low-cuts the body's slow
    drift (under the car band), `soft` trims the r>256 harmonics that a hard
    seam edge throws off (they cost lag-1 neighbour coherence and buy no band
    energy). The seam MASK is softened rather than the assembled T, so seam
    cores stay pinned exactly at seam_t — the gold anchor is untouched.
    [SPB-FRACTURED-090 2026-08-02]"""
    if flat > 0.0:
        bodyT = _flat(bodyT, flat)
    if soft > 0.0:
        bodyT = gauss(bodyT, soft)
        gold = gauss(np.clip(gold, 0.0, 1.0), soft)
    return bodyT, np.clip(gold, 0.0, 1.0)


# ════════════════════════════════════════════════════════════════════════════
# STRUCTURAL GENERATORS — every one a dense homogeneous micro-field.
# T composition convention: gold seams AT seam_t (LUT luma peak); ceramic
# body walks seam_t + 0.12..0.9 (mod 1) in 8 tiers; fine grain rides on top.
# GOLD-PEAK DOCTRINE: tmod=0.0 across the category — a macro phase shift
# would walk the seams off the luma peak and convert macro form into luma
# banding through the oscillating LUT (cathedral dark-lead precedent).
# ════════════════════════════════════════════════════════════════════════════

def g_pave(res, seed, cells=76, dome=0.46, seam_t=0.0, body=0.24, fine=0.10,
           jit=0.42, gold0=0.26, flat=0.0, soft=0.0, tflat=0.0):
    """plate-mosaic — a pave of hundreds of small worley shards (~27 px at
    2048): every shard DOMED (bright crown falling to the rim) with an 8-tier
    tint on top, poured gold in the interstices.
    [SPB-FRACTURED-090 2026-08-02] the shard DOME (a smooth bump at exactly
    the lattice period) now carries the value, the flat per-shard tier only
    tints it — flat cell values are the sub-band leak (raw 8-tier pave field
    measures band 0.15/low 0.85), a domed pave is band-pass by construction
    and reads as real glazed ceramic. band 0.81 -> gate."""
    f1, edge, bid = _voro(res, float(res) / float(cells), float(jit), 41)
    tier = _tier(h2(np.floor(bid * 997.0), 0.0, 42))
    crown = sstep(0.02, 0.42, edge)            # flat shard top, rounded rim
    gold = _fat(edge, float(gold0))
    bodyT = 0.12 + crown * float(dome) + tier * float(body) * (0.25 + 0.75 * crown) \
        + _grain(res, seed, 43, fine)
    bodyT, gold = _shape(bodyT, gold, flat, soft)
    return frac(seam_t + bodyT * (1.0 - gold))


def g_mesh(res, seed, cells1=74, cells2=124, thr=0.30, seam_t=0.0, body=0.34,
           fine=0.10):
    """branching-mesh — a connected web of ridged gold veins at two scales,
    everywhere on the canvas (no single river).
    [SPB-FRACTURED-090 2026-08-02] the vein carrier moved OFF ridged fbm onto
    two bounded-jitter Voronoi ridge webs. A ridged fbm is a low-pass field
    dressed as a network: through three tunings this finish could not pass
    band 0.71 with it. Voronoi ridges branch at true triple points (a better
    vein habit anyway) and carry a sharp in-band fundamental."""
    f1, e1, i1 = _voro(res, float(res) / float(cells1), 0.55, 51)
    f2, e2, i2 = _voro(res, float(res) / float(cells2), 0.62, 55)
    v1 = _fat(e1, float(thr))
    v2 = _fat(e2, float(thr) * 0.78)
    vein = np.maximum(v1, v2 * 0.85)
    node = sstep(1.25, 1.70, v1 + v2)
    relief = sstep(0.02, 0.44, e1)
    tier = _tier(h2(np.floor(i1 * 997.0), 0.0, 53))
    bodyT = 0.16 + relief * 0.42 + tier * float(body) * (0.30 + 0.70 * relief)
    bodyT = bodyT + _grain(res, seed, 54, fine)
    gold = np.clip(vein + node * 0.5, 0.0, 1.0)
    return frac(seam_t + bodyT * (1.0 - gold))


def g_lamina(res, seed, pitch=8.6, angle=0.5, faultgap=9.0, warp=6.0,
             seam_t=0.0, body=0.40, fine=0.10):
    """directional-lamina — ceramic strata at the band pitch (8.6 px at GEN =
    27 px at 2048) crossed by a dense ladder of jittered transverse gold
    faults. [SPB-FRACTURED-090 2026-08-02] pitch 5.0 -> 8.6 (5 px sat at
    r~128, too fine for neighbour coherence), faultgap 30 -> 9 so the faults
    are a second in-band lattice instead of rare accidents, fault profile
    fattened to a real gold vein."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 61, warp)
    u, v = rot((yy + wv, xx + wu), float(angle))
    li = np.floor(v / float(pitch))
    tier = _tier(h2(li, np.floor(u / float(faultgap)), 62))   # per-segment
    prof = 1.0 - np.abs(2.0 * frac(v / float(pitch)) - 1.0)
    fj = u / float(faultgap) + (h2(li, 1.0, 63) - 0.5) * 0.8
    fi = np.floor(fj)
    fault = _fat(np.abs(frac(fj) - 0.5), 0.30) * (h2(fi, li, 64) > 0.30)
    seamv = np.clip(fault + _fat(np.abs(frac(v / float(pitch)) - 0.5), 0.20) * 0.55,
                    0.0, 1.0)
    bodyT = 0.15 + prof * 0.42 + tier * float(body) * (0.30 + 0.70 * prof) \
        + _grain(res, seed, 65, fine)
    return frac(seam_t + bodyT * (1.0 - seamv))


def g_threads(res, seed, pitch=8.6, drift=7.0, goldfrac=0.34, seam_t=0.0,
              body=0.30, fine=0.10):
    """thread-drift — a full carpet of drifting threads; the brightest tier of
    threads runs gold, the rest ceramic-toned.
    [SPB-FRACTURED-090 2026-08-02] drift 26 -> 7 px: a big smooth displacement
    SMEARS the thread lattice's fundamental down under r=64 (band was 0.48,
    the worst in the module). Pitch 6.0 -> 8.6 and the thread profile is now a
    fat rib carrying the value, so the carpet reads at car distance."""
    yy, xx = coords(res)
    flow = (fbm(res, res, rng(seed, 71), 3, 16) - 0.5) * float(drift)
    flow2 = (fbm(res, res, rng(seed, 72), 2, 40) - 0.5) * float(drift) * 0.45
    v = yy + flow + flow2
    p = v / float(pitch)
    ti = np.floor(p)
    seg = np.floor(xx / float(pitch * 1.4))
    hv = h2(ti, seg, 73)
    rib = 1.0 - np.abs(2.0 * frac(p) - 1.0)
    prof = sstep(0.30, 0.86, rib)
    gold = _fat(np.abs(frac(p) - 0.5), 0.30) * (hv > (1.0 - float(goldfrac))).astype(np.float32)
    tier = _tier(h2(ti, seg + 31.0, 74))
    bodyT = 0.15 + prof * 0.30 + tier * float(body) * (0.40 + 0.60 * prof) \
        + _grain(res, seed, 75, fine)
    return frac(seam_t + bodyT * (1.0 - gold))


def g_grit(res, seed, cells=74, cells2=116, wet=0.34, seam_t=0.0, body=0.62,
           fine=0.10):
    """granular scatter — dense two-scale ceramic grit; gold wets the deep
    interstices between grains.
    [SPB-FRACTURED-090 2026-08-02] grain scales 4.3/2.7 px at GEN -> 8.6/5.5:
    the old grit sat at r 150-240, above the coherent half of the car band, so
    it read as sand rather than ceramic. Both scales are bounded-jitter
    lattices now (sharp fundamentals) and the gold wets the true interstice
    (F2-F1), not a distance threshold."""
    g1 = float(res) / float(cells)
    f1, e1, i1 = _voro(res, g1, 0.55, 81)
    d2, i2 = _dots(res, float(res) / float(cells2), 0.60, 86)
    e2 = 1.0 - d2
    t1 = _tier(h2(np.floor(i1 * 997.0), 0.0, 82))
    t2 = _tier(h2(np.floor(i2 * 991.0), 3.0, 84))
    dome1 = sstep(0.02, 0.40, e1)
    dome2 = sstep(0.05, 0.55, e2)
    grain_v = t1 * dome1 * 0.72 + t2 * dome2 * 0.42
    gold = np.clip(_fat(e1, 0.24) + _fat(e2, 0.30) * 0.45, 0.0, 1.0) * float(wet) * 2.2
    bodyT = 0.14 + grain_v * float(body) + _grain(res, seed, 85, fine)
    return frac(seam_t + bodyT * (1.0 - np.clip(gold, 0.0, 1.0)))


def g_cracknet(res, seed, cells=72, drop=0.22, width=0.30, angle=0.35,
               seam_t=0.0, body=0.40, fine=0.10):
    """crackle-net — a two-scale dropped-edge crack web (plate ~9 px at GEN =
    ~28 px at 2048), FAT gold pooled in every crack.
    [SPB-FRACTURED-090 2026-08-02] crack width 0.16 -> 0.30 and plate values
    low-cut: the hairline version scattered its power into r>200 harmonics."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 91, 3.0)

    def web(cw, a, dropv, salt):
        """One dropped-edge crack lattice. The crack is a SMOOTH profile of the
        distance to the cell wall (not a hard `frac < w` test) so each crack is
        an even-width poured vein instead of an aliased hairline."""
        u, v = rot((yy + wv, xx + wu), a)
        pu, pv = u / cw, v / cw
        iu, iv = np.floor(pu), np.floor(pv)
        fu, fv = frac(pu), frac(pv)
        wu_ = float(width) * (0.7 + 0.6 * h2(iu, iv, salt))
        wv2 = float(width) * (0.7 + 0.6 * h2(iv, iu, salt + 1))
        ev = _fat(np.abs(fu - 0.5), wu_) * (h2(iu, iv, salt + 2) > dropv)
        eh = _fat(np.abs(fv - 0.5), wv2) * (h2(iv, iu, salt + 4) > dropv)
        return np.maximum(ev, eh), h2(iu, iv, salt + 6)
    cw1 = res / float(cells)
    w1, t1 = web(cw1, float(angle), float(drop), 92)
    w2, _ = web(cw1 * 0.55, float(angle) + 0.35, float(drop) + 0.32, 99)
    crack = np.clip(w1 + w2 * 0.45, 0.0, 1.0)
    plate = _tier(t1) * float(body)
    curl = 1.0 - crack
    bodyT = 0.15 + curl * 0.42 + plate * (0.30 + 0.70 * curl) + _grain(res, seed, 93, fine)
    return frac(seam_t + bodyT * (1.0 - crack))


def g_ringpack(res, seed, cell=9.0, jit=0.28, seam_t=0.0, body=0.34,
               fine=0.10, rw=1.9):
    """ring-pack — MANY small gold rings (one per pack cell, ~28 px dia at
    2048), never one bullseye.
    [SPB-FRACTURED-090 2026-08-02] the ring is now a FAT annulus and the disc
    inside it is domed, so the pack reads as a smooth quasi-periodic relief at
    the lattice fundamental instead of a hairline circle throwing r>200
    harmonics (band 0.68 / coherence 0.51 / peakiness 0.41 before)."""
    yy, xx = coords(res)
    g = float(cell)
    row = np.floor(yy / g)
    xo = xx + np.mod(row, 2.0) * 0.5 * g
    ci = np.floor(xo / g)
    jx = (h2(ci, row, 101) - 0.5) * float(jit) * g
    jy = (h2(ci, row, 102) - 0.5) * float(jit) * g
    d = np.hypot(xo - (ci + 0.5) * g - jx, yy - (row + 0.5) * g - jy)
    rr = g * (0.30 + 0.10 * h2(ci, row, 103))
    ring = _fat(np.abs(d - rr) / float(rw), 1.0) * (h2(ci, row, 104) > 0.14)
    dome = np.clip(1.0 - (d / np.maximum(rr, 1e-3)) ** 2, 0.0, 1.0)
    dot = _fat(d / float(rw), 0.62) * (h2(ci, row, 105) > 0.68) * 0.9
    tier = _tier(h2(ci, row, 106))
    bodyT = 0.14 + dome * 0.50 + tier * float(body) * (0.28 + 0.72 * dome) \
        + _grain(res, seed, 107, fine)
    return frac(seam_t + bodyT * (1.0 - np.clip(ring + dot, 0.0, 1.0)))


def g_scalepack(res, seed, cw=8.8, seam_t=0.0, body=0.30, fine=0.10):
    """scale imbrication — offset-row scallop crazing (fish-scale fans ~28 px
    at 2048), gold along every scallop arc.
    [SPB-FRACTURED-090 2026-08-02] the scale now carries a real DOME (bright
    crown falling to the arc) and the arc itself is fat: value at the lattice
    fundamental, not a pair of hairline rings."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 111, 3.0)
    u = xx + wu; v = yy + wv
    g = float(cw)
    row = np.floor(v / g)
    uo = u + np.mod(row, 2.0) * 0.5 * g
    iu = np.floor(uo / g)
    fu = frac(uo / g) - 0.5
    fv = frac(v / g)
    sd = np.hypot(fu * 1.12, fv * 0.92)
    arc = _fat(np.abs(sd - 0.5), 0.17)
    arc2 = _fat(np.abs(sd - 0.28), 0.075) * 0.5            # inner growth arc
    tier = _tier(h2(iu, row, 112))
    dome = np.clip(1.0 - sd * 1.9, 0.0, 1.0) ** 0.8
    bodyT = 0.14 + dome * 0.50 + tier * float(body) * (0.28 + 0.72 * dome) \
        + _grain(res, seed, 113, fine)
    return frac(seam_t + bodyT * (1.0 - np.clip(arc + arc2, 0.0, 1.0)))


def g_foam(res, seed, cells=70, cells2=112, seam_t=0.0, body=0.26, fine=0.10):
    """foam pack — packed glaze bubbles at two sizes; the shared walls carry
    bright gold films.
    [SPB-FRACTURED-090 2026-08-02] band was already 0.88 here but neighbour
    coherence only 0.47 — the bubbles were too small and their walls too thin.
    Both scales coarsened one notch onto bounded-jitter lattices and the wall
    is the true F2-F1 meniscus, so the power sits at the low COHERENT end of
    the car band."""
    g1 = float(res) / float(cells)
    f1, e1, i1 = _voro(res, g1, 0.50, 121)
    d2, i2 = _dots(res, float(res) / float(cells2), 0.55, 126)
    e2 = 1.0 - d2
    t1 = _tier(h2(np.floor(i1 * 997.0), 0.0, 122))
    t2 = _tier(h2(np.floor(i2 * 991.0), 5.0, 124))
    dome = sstep(0.02, 0.46, e1) * 0.80 + sstep(0.05, 0.55, e2) * 0.30
    wall = np.clip(_fat(e1, 0.22) + _fat(e2, 0.26) * 0.45, 0.0, 1.0)
    bodyT = 0.14 + dome * 0.50 + (t1 * 0.60 + t2 * 0.30) * float(body) * (0.28 + 0.72 * dome) \
        + _grain(res, seed, 125, fine)
    return frac(seam_t + bodyT * (1.0 - wall))


def g_trilattice(res, seed, pitch=8.8, drop=0.14, seam_t=0.0, body=0.30,
                 fine=0.10, lw=0.30):
    """star-lattice — three line families at 60 degrees; the triangle cells
    take 8-tier fills, the nodes pool gold.
    [SPB-FRACTURED-090 2026-08-02] this was the module's WORST finish for
    neighbour coherence (0.38) and peakiness (0.38): 0.9-px rules at a 7-px
    pitch are a hairline comb whose power lands at r 200-256. Rules are now
    0.30 of the pitch (a real leaded bar), the pitch is 8.8, and each triangle
    carries a soft interior swell so value sits at the fundamental."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 131, 3.0)
    a0 = float(rng(seed, 132).uniform(0, np.pi))
    lat = np.zeros((res, res), np.float32)
    acc = np.zeros((res, res), np.float32)
    swell = np.zeros((res, res), np.float32)
    idsum = np.zeros((res, res), np.float32)
    for k in range(3):
        u, v = rot((yy + wv, xx + wu), a0 + k * np.pi / 3.0)
        pv = v / float(pitch)
        iv = np.floor(pv)
        dv = np.abs(frac(pv) - 0.5)
        line = _fat(dv, float(lw)) * (h2(iv, float(k), 133 + k) > float(drop))
        lat = np.maximum(lat, line)
        acc = acc + line
        swell = swell + sstep(float(lw), 0.5, dv)
        idsum = idsum + iv * (k + 1.0)
    node = sstep(1.3, 1.8, acc)
    tier = _tier(h2(idsum, 0.0, 137))
    sw = swell * (1.0 / 3.0)
    bodyT = 0.14 + sw * 0.50 + tier * float(body) * (0.28 + 0.72 * sw) \
        + _grain(res, seed, 138, fine)
    return frac(seam_t + bodyT * (1.0 - np.clip(lat * 0.85 + node, 0.0, 1.0)))


def g_comb(res, seed, pitch=8.4, bundle=26.0, amp=4.0, angle=0.9, seam_t=0.0,
           body=0.30, fine=0.10):
    """flow-combed strands — parallel striation gathered into tiered bundles,
    combed by a gentle flow; gold on the brightest strands.
    [SPB-FRACTURED-090 2026-08-02] pitch 4.2 -> 8.4 and comb amplitude 9 -> 4:
    a 4-px strand sits at r~150 and a big comb displacement smears the
    fundamental, which is why this finish measured coherence 0.47. The strand
    profile now carries the value directly (a real combed ridge)."""
    yy, xx = coords(res)
    u, v = rot((yy, xx), float(angle))
    flow = (fbm(res, res, rng(seed, 141), 3, 18) - 0.5) * float(amp)
    vv = v + flow
    p = vv / float(pitch)
    si = np.floor(p)
    sg = np.floor(u / float(bundle) * 2.0)
    prof = (1.0 - np.abs(2.0 * frac(p) - 1.0)) ** 1.1
    tier = _tier(h2(si, sg, 142))
    gold = _fat(np.abs(frac(p) - 0.5), 0.26) * (h2(si, sg + 7.0, 144) > 0.70)
    bodyT = 0.14 + prof * 0.32 + tier * float(body) * (0.30 + 0.70 * prof) \
        + _grain(res, seed, 145, fine)
    return frac(seam_t + bodyT * (1.0 - gold))


def g_weave(res, seed, pitch=9.0, gap=0.30, angle=0.15, seam_t=0.0, body=0.30,
            fine=0.10):
    """woven-cross — a micro basket weave (band pitch ~9 px = 29 px at 2048),
    warp over weft by cell parity, gold glinting in the interlace gaps.
    [SPB-FRACTURED-090 2026-08-02] the band's own over/under RIDGE now carries
    the value (the flat per-band tier only tints it) — flat cell values are
    the sub-band leak that held this finish at band 0.65."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 151, 4.0)
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
    tier = _tier(np.where(par > 0.5, h2(iu, 0.0, 152), h2(iv, 1.0, 153)))
    gapm = (1.0 - np.maximum(bu, bv))
    gold = sstep(0.42, 0.86, gapm)
    bodyT = 0.14 + over * 0.50 + tier * float(body) * (0.28 + 0.72 * over) \
        + _grain(res, seed, 154, fine)
    return frac(seam_t + bodyT * (1.0 - gold))


def g_ripplecarpet(res, seed, centers=5, freq=0.88, seam_t=0.0, body=0.55,
                   fine=0.10):
    """micro-ripple carpet — interfering fine ripple sets radiating from a
    grid of many centers (period ~6 px); crests tier-tinted, nodal lines
    gold. [SPB-FRACTURED-FIELD 2026-08-02]"""
    yy, xx = coords(res)
    r0 = rng(seed, 161)
    g = res / float(centers)
    ph = np.zeros((res, res), np.float32)
    ph2 = np.zeros((res, res), np.float32)
    for j in range(int(centers)):
        for i in range(int(centers)):
            cx = (i + 0.5 + float(r0.uniform(-0.35, 0.35))) * g
            cy = (j + 0.5 + float(r0.uniform(-0.35, 0.35))) * g
            d = np.hypot(xx - cx, yy - cy)
            w = np.exp(-(d / (g * 1.15)) ** 2)
            ph = ph + np.cos(d * float(freq) + float(r0.uniform(0, 6.28))) * w
            ph2 = ph2 + w
    rip = ph / np.maximum(ph2, 1e-4)
    env = np.sqrt(gauss(rip * rip, 9.0)) + 1e-4
    rip = np.clip(rip / env, -1.6, 1.6) * 0.6
    crest = n01(rip)
    q = np.clip((crest * 8.0).astype(np.int32), 0, 7)
    tier = _TIERS[q]
    # [SPB-FRACTURED-090 2026-08-02] ripple period 6.0 -> 7.1 px at GEN and a
    # FAT nodal line: band was already 0.92 here, coherence only 0.50.
    gold = _fat(np.abs(rip), 0.16)                            # nodal gold lines
    bodyT = 0.15 + tier * float(body) + _grain(res, seed, 162, fine)
    return frac(seam_t + bodyT * (1.0 - gold * 0.9))


def g_billows(res, seed, cell=9.5, seam_t=0.0, body=0.58, fine=0.10,
              flat=1.1, soft=1.3):
    """micro-billows — posterised glaze cloudlets in 8 tiers with carbon rims
    at the steepest gradients and gold at the brightest pools.
    [SPB-FRACTURED-090 2026-08-02] the cloud carrier moved OFF fbm onto a
    three-scale METABALL field on jittered lattices. Cubic-upscaled noise is a
    low-pass field, and posterising it only fixes the histogram, not the
    spectrum — this finish was stuck at band 0.44-0.73 through four tunings.
    Metaballs billow exactly the same way with a fundamental inside the car
    band."""
    a1, i1 = _dots(res, float(cell), 0.85, 171)
    a2, i2 = _dots(res, float(cell) * 0.66, 0.90, 175)
    a3, i3 = _dots(res, float(cell) * 0.45, 0.95, 179)
    t = ((1.0 - a1) ** 1.5 * (0.45 + 0.55 * i1) * 0.50
         + (1.0 - a2) ** 1.5 * (0.45 + 0.55 * i2) * 0.32
         + (1.0 - a3) ** 1.5 * (0.45 + 0.55 * i3) * 0.18)
    if soft > 0.0:
        t = gauss(t, soft)
    t = n01(_flat(t, flat))
    q = np.clip((t * 8.0).astype(np.int32), 0, 7)
    tier = _TIERS[q]
    gy, gx = np.gradient(gauss(t, 1.2))
    rim = sstep(0.50, 0.88, n01(np.hypot(gx, gy)))
    gold = sstep(0.82, 0.96, t)
    bodyT = 0.15 + t * 0.40 + tier * float(body) * 0.55 - rim * 0.10 + _grain(res, seed, 174, fine)
    return frac(seam_t + np.clip(bodyT, 0.02, 1.2) * (1.0 - gold))


def g_chevron(res, seed, pitch=8.0, rowh=11.0, angle=0.6, seam_t=0.0,
              body=0.30, fine=0.10):
    """chevron pleats — herringbone (hatch pitch 8 px = 26 px at 2048, rows
    alternating direction), gold at the pleat junctions.
    [SPB-FRACTURED-090 2026-08-02] hatch 4 -> 8 px (a 4-px pleat sits at
    r~150, above the coherent half of the band) and the pleat RIDGE now
    carries the value with a fat junction seam."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 181, 2.5)
    u, v = rot((yy + wv, xx + wu), float(angle))
    row = np.floor(v / float(rowh))
    sgn = np.where(np.mod(row, 2.0) > 0.5, 1.0, -1.0)
    hatch = u * 0.9 * sgn + v * 0.45
    hi = np.floor(hatch / float(pitch))
    prof = 1.0 - np.abs(2.0 * frac(hatch / float(pitch)) - 1.0)
    tier = _tier(h2(hi, row, 182)) * (0.65 + 0.35 * _tier(h2(row, 0.0, 183)))
    junc = _fat(np.abs(frac(v / float(rowh)) - 0.5), 0.22)
    bodyT = 0.14 + prof * 0.50 + tier * float(body) * (0.28 + 0.72 * prof) \
        + _grain(res, seed, 184, fine)
    return frac(seam_t + bodyT * (1.0 - junc * 0.9))


def g_beadpack(res, seed, cells=76, seam_t=0.0, body=0.34, fine=0.10,
               jit=0.36):
    """interlocking-cells — crawled-glaze bead pack: rounded tiered beads with
    dark carbon gaps and gold pooling at the triple points.
    [SPB-FRACTURED-090 2026-08-02] band was 0.49 — the beads sat on the
    unbounded worley pack, which smears half its power under r=64. On a
    bounded-jitter lattice with a true F2-F1 gap the same crawled-glaze idea
    is band-pass by construction."""
    g = float(res) / float(cells)
    f1, edge, bid = _voro(res, g, float(jit), 191)
    tier = _tier(h2(np.floor(bid * 997.0), 0.0, 192))
    tier2 = _tier(h2(np.floor(bid * 991.0), 7.0, 194))
    bead = sstep(0.03, 0.30, edge)
    dome = sstep(0.02, 0.46, edge)
    gold = np.clip(_fat(edge, 0.20) * 1.15, 0.0, 1.0)
    bodyT = 0.13 + dome * 0.50 + (tier * 0.85 * bead + tier2 * 0.30 * (1.0 - bead)) * (0.28 + 0.72 * dome) \
        * float(body) + _grain(res, seed, 193, fine)
    return frac(seam_t + bodyT * (1.0 - gold))


def g_needlefelt(res, seed, cell=8.0, ln=7, seam_t=0.0, body=0.55,
                 fine=0.10, thick=0.6, jit=0.60):
    """needle felt — one short oriented needle laid in EVERY lattice cell (6
    orientations picked per cell), a wall-to-wall horsehair-carbon felt with
    gold needles in the top tier.
    [SPB-FRACTURED-090 2026-08-02] the old scatter (0.2-10 pct of a 2-px grid)
    left big quiet gaps between needles, so the felt read as a low-pass field
    (band 0.42-0.61 through three attempts). A needle per 8-px cell is the same
    felt at the car-band scale with no dead ground, and 7 px is the longest a
    needle can be before its own axis falls under r=64."""
    yy, xx = coords(res)
    c = float(cell)
    ci, cj = np.floor(xx / c), np.floor(yy / c)
    jx = (h2(ci, cj, 201) - 0.5) * float(jit) * c
    jy = (h2(ci, cj, 205) - 0.5) * float(jit) * c
    dot = (np.hypot(xx - (ci + 0.5) * c - jx, yy - (cj + 0.5) * c - jy) < 0.9)
    ori = np.clip((h2(ci, cj, 207) * 6.0).astype(np.int32), 0, 5)
    val = (0.35 + 0.65 * _tier(h2(ci, cj, 208)))
    felt = np.zeros((res, res), np.float32)
    goldf = np.zeros((res, res), np.float32)
    L = int(ln) | 1
    for k in range(6):
        m = (dot & (ori == k)).astype(np.float32) * val
        ker = np.zeros((L, L), np.float32)
        a = k * np.pi / 6.0
        cs, sn = np.cos(a), np.sin(a)
        for t in range(L):
            px = int(round((L - 1) / 2 + (t - (L - 1) / 2) * cs))
            py = int(round((L - 1) / 2 + (t - (L - 1) / 2) * sn))
            ker[np.clip(py, 0, L - 1), np.clip(px, 0, L - 1)] = 1.0
        ker /= max(ker.sum(), 1.0)
        st = cv2.filter2D(m, -1, ker) * float(L)
        felt = np.maximum(felt, st * 0.85)
        if k % 3 == 0:
            goldf = np.maximum(goldf, st * (h2(ci, cj, 209) > 0.62))
    if thick > 0.0:
        felt = gauss(felt, thick)
        goldf = gauss(goldf, thick)
    tier = _ptier(res, 8.6, 214, 0.85)
    bodyT = 0.15 + np.clip(felt, 0, 1.2) * 0.42 + tier * 0.55 * float(body) + _grain(res, seed, 215, fine)
    return frac(seam_t + bodyT * (1.0 - np.clip(goldf * 1.4, 0.0, 1.0)))


def g_labyrinth(res, seed, sig=0.45, iters=8, seam_t=0.0, body=0.34, fine=0.10):
    """RD labyrinth — Turing stripes via iterated band-pass sharpening: a gold
    labyrinth channel over tiered ceramic.
    [SPB-FRACTURED-090 2026-08-02] the Turing wavelength is set by sig; 0.65
    produced a 12-px stripe whose fundamental fell UNDER r=64 (band 0.55,
    low 0.44). sig 0.95 lands the stripe at ~8 px at GEN, the gold channel is
    fat, and the ceramic tier is low-cut."""
    x = fbm(res, res, rng(seed, 221), 3, 24) - 0.5
    for _ in range(int(iters)):
        x = np.tanh((gauss(x, float(sig)) - gauss(x, float(sig) * 2.6)) * 14.0)
    stripe = 0.5 + 0.5 * x
    goldl = _fat(np.abs(stripe - 0.72), 0.22)          # fat channel line
    tier = _ptier(res, 8.8, 222, 1.1)
    wallprof = sstep(0.70, 0.10, stripe)
    bodyT = 0.14 + wallprof * 0.50 + tier * float(body) * (0.28 + 0.72 * wallprof) \
        + _grain(res, seed, 223, fine)
    return frac(seam_t + bodyT * (1.0 - goldl))


def g_dendrites(res, seed, cell=9.0, iters=3, seam_t=0.0, body=0.34,
                fine=0.10, thick=0.6, jit=0.55):
    """dendrite forest — a gold crystal grown in EVERY lattice cell by gated
    anisotropic dilation; the arms of neighbouring crystals interlock into a
    wall-to-wall forest.
    [SPB-FRACTURED-090 2026-08-02] the old version scattered ~600 crystals at
    0.2 pct seed density: sparse features on a quiet ground are a low-pass
    field and it measured band 0.20-0.45 through four attempts. One crystal
    per 9-px cell (jittered, per-cell growth axis) keeps exactly the same
    crystal HABIT while making the field dense and quasi-periodic — which is
    also what the coverage law asks for (no dead ground anywhere)."""
    yy, xx = coords(res)
    c = float(cell)
    ci, cj = np.floor(xx / c), np.floor(yy / c)
    jx = (h2(ci, cj, 231) - 0.5) * float(jit) * c
    jy = (h2(ci, cj, 236) - 0.5) * float(jit) * c
    d = np.hypot(xx - (ci + 0.5) * c - jx, yy - (cj + 0.5) * c - jy)
    acc = (d < 0.9).astype(np.float32) * (0.55 + 0.45 * h2(ci, cj, 232))
    k1 = np.array([[0, 1, 0], [0, 1, 0], [0, 1, 0]], np.uint8)
    k2 = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], np.uint8)
    k3 = np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]], np.uint8)
    ks = (k1, k1.T, k2, k3)
    # per-cell growth axis: each crystal feathers along its own habit
    axis = np.clip((h2(ci, cj, 237) * 4.0).astype(np.int32), 0, 3)
    for i in range(int(iters)):
        grow = np.zeros_like(acc)
        for a in range(4):
            grow = np.maximum(grow, cv2.dilate(acc * (axis == a), ks[(a + i) % 4]))
        acc = np.maximum(acc, grow * 0.93)
    if thick > 0.0:
        acc = gauss(acc, thick)
    tier = _ptier(res, 8.4, 234, 0.35)
    gold = np.clip(acc * 1.7, 0.0, 1.0) * sstep(0.10, 0.30, acc)
    bodyT = 0.14 + np.clip(acc, 0, 1) * 0.44 + tier * float(body) * 0.70 + _grain(res, seed, 235, fine)
    return frac(seam_t + bodyT * (1.0 - gold))


def g_dust(res, seed, seam_t=0.0, body=0.55, fine=0.10, cw0=9.0):
    """structured dust — three scales of angular tinted chips (9/6/4 px cells)
    ordered along a soft diagonal lattice, with gold micro-flecks between.
    [SPB-FRACTURED-090 2026-08-02] chip scales 8/5/3 -> 9/6/4 px at GEN with
    the weight moved onto the coarsest (the 3-px chips sat at r~213, past the
    coherent half of the band) and the flecks are 3-px grains, not single
    pixels — a pixel-scale fleck is indistinguishable from noise on a car."""
    yy, xx = coords(res)
    u, v = rot((yy, xx), 0.785)
    order = 0.5 + 0.5 * np.cos(u / 22.0) * np.cos(v / 22.0)
    acc = np.zeros((res, res), np.float32)
    for k, cw in enumerate((float(cw0), float(cw0) * 0.66, float(cw0) * 0.44)):
        ci, cj = np.floor(xx / cw), np.floor(yy / cw)
        hv = h2(ci, cj, 241 + k * 5)
        # every chip is a FACETED plate inset in its cell, with a matrix gap
        # around it: a flat chip that fills its whole cell is a low-pass field
        # (this finish measured band 0.52 / low 0.47 with flat chips).
        dchip = np.maximum(np.abs(frac(xx / cw) - 0.5), np.abs(frac(yy / cw) - 0.5)) * 2.0
        facet = sstep(0.92, 0.18, dchip) * (0.55 + 0.45 * (1.0 - dchip))
        pres = 1.0 if k == 0 else (hv > (0.30 + 0.22 * k)).astype(np.float32)
        chip = pres * facet
        acc = acc + chip * _tier(h2(ci, cj, 243 + k * 5)) * (0.62 - 0.17 * k)
    gold = (h2(np.floor(xx / 3.0), np.floor(yy / 3.0), 258) > 0.975).astype(np.float32)
    gold = np.clip(gauss(gold, 0.8) * 1.8, 0.0, 1.0)
    bodyT = 0.14 + acc * float(body) * (0.88 + 0.12 * order) \
        + _grain(res, seed, 259, fine)
    return frac(seam_t + bodyT * (1.0 - gold))


def _lowcut(fn):
    """Wrap a generator with the universal LOW-CUT knob (`lowcut` px at GEN).

    [SPB-FRACTURED-090 2026-08-02] the one dial that trades neighbour
    coherence for car-band energy. It subtracts the field's own slow local
    mean (keeping the global mean, so the LUT walk and the gold anchor are
    unchanged) and therefore deletes power UNDER r=64 without touching a
    single shape or edge. Every archetype that still carried an unavoidable
    sub-band skirt after its geometry was fixed uses this to spend its
    coherence surplus on band."""
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
    "pave": g_pave, "mesh": g_mesh, "lamina": g_lamina, "threads": g_threads,
    "grit": g_grit, "cracknet": g_cracknet, "ringpack": g_ringpack,
    "scalepack": g_scalepack, "foam": g_foam, "trilattice": g_trilattice,
    "comb": g_comb, "weave": g_weave, "ripplecarpet": g_ripplecarpet,
    "billows": g_billows, "chevron": g_chevron, "beadpack": g_beadpack,
    "needlefelt": g_needlefelt, "labyrinth": g_labyrinth,
    "dendrites": g_dendrites, "dust": g_dust,
}
ENGINES = {k: _lowcut(v) for k, v in ENGINES.items()}


# ════════════════════════════════════════════════════════════════════════════
# CATEGORY-SPECIFIC MACRO KIND — river. [SPB-FRACTURED-FIELD 2026-08-02] kept
# for the extra_macro contract, now used only as GENTLE field modulation
# (narrow vd) — never as the composition itself.
# ════════════════════════════════════════════════════════════════════════════

def m_river(r, mp, seed, K):
    yy, xx = K.coords(r)
    u = xx / r
    v = yy / r
    cy = float(mp.get("cy", 0.5))
    amp = float(mp.get("amp", 0.16))
    freq = float(mp.get("freq", 1.15))
    phase = float(mp.get("phase", 0.0))
    yc = cy + amp * np.sin(2.0 * np.pi * (freq * u + phase))
    d = np.abs(v - yc)
    width = max(float(mp.get("width", 0.11)), 1e-3)
    M = np.exp(-((d / width) ** 2))
    M = np.clip(M * 1.1 + 0.06, 0.0, 1.0)
    D = K.n01(K.h2(np.floor(u * float(mp.get("segs", 6.0))), 0.0, 53) + d * 2.0)
    return M, D


# ════════════════════════════════════════════════════════════════════════════
# KINTSUGI KIT — gilding + ceramic-vs-gold spec, kept from pass 1 (the good
# physics): gild = luma-gated warm-metal remap; spec carves gold seams
# METALLIC (M high) + GLOSSY (R low, Cc -> 16) over dielectric satin ceramic.
# ════════════════════════════════════════════════════════════════════════════

class _KintsugiKit(catlib.CategoryKit):
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

    def art_work(self, fid):
        rgb = catlib.CategoryKit.art_work(self, fid)
        g = self.ALL[fid].get("gild")
        if g:
            lo, hi, amt = float(g[0]), float(g[1]), float(g[2])
            L = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])
            m = (sstep(lo, hi, L) * amt)[..., None]
            gold = np.stack([np.clip(L * 1.16 + 0.06, 0, 1),
                             np.clip(L * 0.86 + 0.035, 0, 1),
                             np.clip(L * 0.34, 0, 1)], axis=2)
            rgb = np.clip(rgb * (1.0 - m) + gold * m, 0.0, 1.0)
        return rgb.astype(np.float32)

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
            micro = n01(pattern - gauss(pattern, 2.5))
            seam = sstep(0.55, 0.80, pattern)                 # the gold skeleton
            _, _dd = self.macro_cached(fid)
            domw = cv2.resize(_dd, (WORK, WORK), interpolation=cv2.INTER_NEAREST)
            msw = float(rkw.get("mswing", 1.2))
            # gold = metal; porcelain/celadon body = dielectric with texture
            M = np.clip(24.0 + pattern * 190.0 + (micro - 0.5) * 60.0 * msw, 8.0, 255.0)
            # gold seams GLOSSY, ceramic body satin-matte
            R = np.clip(170.0 - pattern * 130.0 - seam * 30.0
                        + (0.5 - micro) * 40.0, 10.0, 220.0)
            # clearcoat: pooled lacquer over the seams (->16), macro travel on body
            Cc = np.clip(205.0 - seam * 180.0 - domw * 60.0 + micro * 20.0, 16.0, 255.0)
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
# RECIPES — 20 finishes, ids fki_*, seeds 1160-1179 (UNCHANGED ids/seeds).
# [SPB-FRACTURED-FIELD 2026-08-02] one archetype per id (ledger at top of
# module), gold seams pinned at the LUT luma peak (seam_t), macro demoted to
# gentle modulation: vd narrow, tmod <= 0.15, ambient <= 0.24. Palettes:
# 3-4 luminous ceramic anchors + TRUE gold (gild pass).
# ════════════════════════════════════════════════════════════════════════════

# LUT families + probed luma-peak seam anchors (dynamic — stays correct if a
# lut is retuned). Peak = where the gold seams live on the LUT.
LUT_G = (400.0, 940.0, 0.95, 1.30, 2.1)    # warm gold-forward
LUT_P = (420.0, 880.0, 0.90, 1.05, 1.2)    # porcelain soft
LUT_C = (380.0, 960.0, 1.00, 1.30, 4.4)    # cobalt-deep
LUT_J = (410.0, 930.0, 0.95, 1.20, 3.1)    # jade / celadon
LUT_K = (430.0, 900.0, 1.00, 1.15, 5.0)    # cream warm
P_G = _lut_peak(LUT_G); P_P = _lut_peak(LUT_P); P_C = _lut_peak(LUT_C)
P_J = _lut_peak(LUT_J); P_K = _lut_peak(LUT_K)

# [SPB-FRACTURED-090 2026-08-02] sparkle 0.30 -> 0.08: the sparkle octave
# (fbm base 320 at GEN) lands at r ~ 320 — ABOVE the car band, so it was pure
# denominator. The fine detail now comes from real in-band shapes instead.
_KW = dict(ambient=0.05, ambient_sigma=44, floor=0.11, sparkle=0.08)

GOLD_RIVERS = {
 # [SPB-FRACTURED-FIELD 2026-08-02] branching-mesh (band 0.30 -> gate) — the
 # one great river is now a whole-canvas web of fine gold veins.
 "fki_golden_river": dict(huecell=52.0, name="Golden River", engine="mesh",
    eargs=dict(cells1=66.6, cells2=124, thr=0.3, seam_t=P_G, body=0.264, fine=0.12, lowcut=0.0),
    seed=1160, lut=LUT_G, val=0.30, gild=(0.55, 0.85, 0.85),
    hues=[0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.13, 0.09, 0.55], hspan=0.045, satboost=0.98,
    macro=("river", dict(freq=1.1, width=0.16, segs=6)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.8, mfloor=10.0, **_KW),
    desc="A whole web of fine gold rivers mending dark porcelain, bright at every joint. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] plate-mosaic (band 0.28 -> gate) — the
 # dropped plate is now a full pave of small shards, gold between every one.
 "fki_porcelain_mend": dict(huemode="macro", huecell=29.2, name="Porcelain Mend", engine="pave",
    eargs=dict(cells=76.0, dome=0.62, seam_t=P_P, body=0.099, fine=0.1, jit=0.42, gold0=0.3, lowcut=0.0),
    seed=1161, lut=LUT_P, val=0.31, gild=(0.55, 0.85, 0.85),
    hues=[0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.62, 0.47, 0.105], hspan=0.045, satboost=0.94,
    macro=("continents", dict(base=3, cells=3.5)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.5, gray=0.10, ccboost=1.3, ccpat=0.4, **_KW),
    desc="A pave of small porcelain shards rejoined in gold, seam by glowing seam. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] directional-lamina (band 0.11 -> gate) —
 # long slab faults become fine cobalt strata crossed by gold micro-faults.
 "fki_cobalt_seam": dict(huemode="flow", huedir=0.50, huecell=36.0, name="Cobalt Seam", engine="lamina",
    eargs=dict(pitch=9.907, angle=0.5, faultgap=9.0, warp=4.0, seam_t=P_C, body=0.273, fine=0.14, lowcut=1.8),
    seed=1162, lut=LUT_C, val=0.29, gild=(0.55, 0.85, 0.90),
    hues=[0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.55, 0.47, 0.105], hspan=0.045, satboost=0.96,
    macro=("continents", dict(base=3, cells=3.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Fine cobalt strata split by a thousand small gold cross-faults. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] thread-drift (band 0.18 -> gate) — the
 # single meander is now a carpet of drifting gold threads on jade.
 "fki_celadon_vein": dict(huemode="flow", huedir=1.20, huecell=36.0, name="Celadon Vein", engine="threads",
    eargs=dict(pitch=6.037, drift=7.0, goldfrac=0.34, seam_t=P_J, body=0.36, fine=0.12, lowcut=1.0),
    seed=1163, lut=LUT_J, val=0.30, gild=(0.55, 0.85, 0.85),
    hues=[0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.33, 0.47, 0.105], hspan=0.045, satboost=0.95,
    macro=("river", dict(freq=0.9, width=0.18, cy=0.46)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.3, **_KW),
    desc="Gold threads drifting through calm celadon jade like current lines in green water. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] granular scatter (band 0.20 -> gate) —
 # the confluence vortex is now dense ceramic grit with gold-wet interstices.
 "fki_cream_confluence": dict(huemode="cloud", huebase=4, huecell=22.0, name="Cream Confluence", engine="grit",
    eargs=dict(cells=66.071, cells2=116, wet=0.34, seam_t=P_K, body=0.343, fine=0.12, lowcut=2.5),
    seed=1164, lut=LUT_K, val=0.31, gild=(0.55, 0.85, 0.80),
    hues=[0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.05, 0.13, 0.55], hspan=0.045, satboost=0.94,
    macro=("vortex", dict(arms=2.0, twist=7.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.3, gray=0.08, **_KW),
    desc="Warm cream glaze ground to fine grit, gold wetting every interstice. A FRACTURED KINTSUGI finish."),
}

CRACKLE_WEBS = {
 # [SPB-FRACTURED-FIELD 2026-08-02] crackle-net (band 0.17 -> gate) — the
 # coarse plates are now a fine two-scale web, plate size ~28 px at 2048.
 "fki_cobalt_craquelure": dict(huemode="macro", huecell=29.2, name="Cobalt Craquelure", engine="cracknet",
    eargs=dict(cells=92.308, drop=0.22, width=0.3, angle=0.35, seam_t=P_C, body=0.273, fine=0.14, lowcut=0.0),
    seed=1165, lut=LUT_C, val=0.29, gild=(0.58, 0.86, 0.85),
    hues=[0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.55, 0.47, 0.105], hspan=0.045, satboost=0.96,
    macro=("domains", dict(cells=6, salt=1165)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="A fine gold crackle web over deep cobalt, hundreds of glowing plates. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] ring-pack (band 0.05 -> gate) — the polar
 # bullseye is BANNED; now MANY small gold rings packed across the canvas.
 "fki_gilded_craquelure": dict(huecell=34.0, name="Gilded Craquelure", engine="ringpack",
    eargs=dict(cell=10.368, jit=0.28, seam_t=P_G, body=0.289, fine=0.12, rw=1.9, lowcut=0.0),
    seed=1166, lut=LUT_G, val=0.30, gild=(0.58, 0.86, 0.80),
    hues=[0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.13, 0.09, 0.55], hspan=0.045, satboost=0.96,
    macro=("bands", dict(angle=0.9, freq=2.0, warp=0.30)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.8, mfloor=10.0, **_KW),
    desc="Thousands of small gilded rings packed edge to edge on dark lacquer. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] scale imbrication (band 0.09 -> gate) —
 # fish-scale crazing shrunk to true craze scale (~8 px scallops).
 "fki_porcelain_craquelure": dict(huemode="cloud", huebase=6, huecell=28.0, name="Porcelain Craquelure", engine="scalepack",
    eargs=dict(cw=7.92, seam_t=P_P, body=0.54, fine=0.12, lowcut=2.5),
    seed=1167, lut=LUT_P, val=0.31, gild=(0.58, 0.86, 0.85),
    hues=[0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.62, 0.47, 0.105], hspan=0.045, satboost=0.94,
    macro=("continents", dict(base=3, cells=4.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.4, gray=0.10, ccboost=1.3, ccpat=0.4, **_KW),
    desc="Tiny fish-scale crazing fanned across porcelain, gold on every scallop. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] foam pack (band 0.10 -> gate) — the big
 # double plates become packed glaze bubbles with gold wall films.
 "fki_cream_craquelure": dict(huecell=30.0, name="Cream Craquelure", engine="foam",
    eargs=dict(cells=38.147, cells2=112, seam_t=P_K, body=0.305, fine=0.1, lowcut=2.5),
    seed=1168, lut=LUT_K, val=0.30, gild=(0.58, 0.86, 0.80),
    hues=[0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.05, 0.13, 0.55], hspan=0.045, satboost=0.94,
    macro=("bands", dict(angle=0.9, freq=2.0, warp=0.35)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.3, gray=0.08, **_KW),
    desc="Cream glaze foamed into packed bubbles, gold films where the walls meet. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] star-lattice (band 0.08 -> gate) — the
 # triangle mesh shrunk to a fine 60-degree lattice with gold nodes.
 "fki_celadon_craquelure": dict(huecell=28.0, name="Celadon Craquelure", engine="trilattice",
    eargs=dict(pitch=9.856, drop=0.14, seam_t=P_J, body=0.195, fine=0.12, lw=0.3, lowcut=1.8),
    seed=1169, lut=LUT_J, val=0.30, gild=(0.58, 0.86, 0.80),
    hues=[0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.33, 0.47, 0.105], hspan=0.045, satboost=0.96,
    macro=("domains", dict(cells=7, salt=1169)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.3, **_KW),
    desc="A fine star lattice broken into jade triangles, gold pooling at the nodes. A FRACTURED KINTSUGI finish."),
}

BRUSHWORK = {
 # [SPB-FRACTURED-FIELD 2026-08-02] flow-combed strands (band 0.11 -> gate) —
 # broad strokes become tight combed micro-striation bundles.
 "fki_gilt_brushwork": dict(huemode="flow", huedir=0.90, huecell=36.0, name="Gilt Brushwork", engine="comb",
    eargs=dict(pitch=8.4, bundle=26.0, amp=4.0, angle=0.9, seam_t=P_G, body=0.166, fine=0.12, lowcut=0.0),
    seed=1170, lut=LUT_G, val=0.30, gild=(0.58, 0.88, 0.70),
    hues=[0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.13, 0.09, 0.55], hspan=0.045, satboost=0.96,
    macro=("bands", dict(angle=0.55, freq=2.5, warp=0.25)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.8, mfloor=10.0, **_KW),
    desc="Liquid gold combed into fine strands, every bristle line catching light. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] woven-cross (band 0.27 -> gate) — the two
 # stroke directions become a true micro basket weave.
 "fki_cobalt_sweep": dict(huemode="flow", huedir=0.15, huecell=36.0, name="Cobalt Sweep", engine="weave",
    eargs=dict(pitch=8.1, gap=0.3, angle=0.15, seam_t=P_C, body=0.255, fine=0.1, lowcut=0.0),
    seed=1171, lut=LUT_C, val=0.29, gild=(0.60, 0.88, 0.65),
    hues=[0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.55, 0.47, 0.105], hspan=0.045, satboost=0.95,
    macro=("rachis", dict(angle=0.15, lanes=6.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Cobalt bands woven warp over weft, gold glinting in every interlace gap. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] micro-ripple carpet (band 0.12 -> gate) —
 # two enso centres become an interference carpet from many centres.
 "fki_celadon_sweep": dict(huemode="cloud", huebase=3, huecell=52.0, name="Celadon Sweep", engine="ripplecarpet",
    eargs=dict(centers=5, freq=0.978, seam_t=P_J, body=0.468, fine=0.1, lowcut=2.5),
    seed=1172, lut=LUT_J, val=0.30, gild=(0.60, 0.88, 0.65),
    hues=[0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.33, 0.47, 0.105], hspan=0.045, satboost=0.95,
    macro=("vortex", dict(arms=1.0, twist=6.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.3, **_KW),
    desc="Jade ripples from many quiet centres interfering, gold on the still lines. A FRACTURED KINTSUGI finish."),
}

RAKU_PATCHES = {
 # [SPB-FRACTURED-FIELD 2026-08-02] micro-billows (band 0.09 -> gate) — the
 # big threshold blobs become posterized fine turbulence cloudlets.
 "fki_moon_raku": dict(huemode="macro", huecell=56.0, name="Moon Raku", engine="billows",
    eargs=dict(cell=6.669, seam_t=P_P, body=0.325, fine=0.14, flat=1.1, lowcut=1.8),
    seed=1173, lut=LUT_P, val=0.31, gild=(0.60, 0.90, 0.55),
    hues=[0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.62, 0.47, 0.105], hspan=0.045, satboost=0.94,
    macro=("continents", dict(base=4, cells=3.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.4, gray=0.12, ccboost=1.3, ccpat=0.4, **_KW),
    desc="Moonlit raku billows in eight glaze tiers, gold waking at the brightest pools. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] chevron pleats (band 0.14 -> gate) — the
 # drip curtain becomes fine gilt herringbone pleats.
 "fki_golden_raku": dict(huemode="flow", huedir=0.60, huecell=36.0, name="Golden Raku", engine="chevron",
    eargs=dict(pitch=8.96, rowh=11.0, angle=0.6, seam_t=P_G, body=0.166, fine=0.12, lowcut=1.8),
    seed=1174, lut=LUT_G, val=0.30, gild=(0.60, 0.90, 0.60),
    hues=[0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.13, 0.09, 0.55], hspan=0.045, satboost=0.96,
    macro=("continents", dict(base=3, cells=3.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.8, mfloor=10.0, **_KW),
    desc="Golden raku pleated into fine herringbone, gilt light at every junction. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] interlocking-cells (band 0.32 -> gate) —
 # crawled glaze kept but shrunk to a true bead pack with carbon gaps.
 "fki_cobalt_raku": dict(huecell=22.8, name="Cobalt Raku", engine="beadpack",
    eargs=dict(cells=84.444, seam_t=P_C, body=0.188, fine=0.12, jit=0.36, lowcut=0.0),
    seed=1175, lut=LUT_C, val=0.29, gild=(0.62, 0.90, 0.55),
    hues=[0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.55, 0.47, 0.105], hspan=0.045, satboost=0.95,
    macro=("domains", dict(cells=5, salt=1175)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="Cobalt glaze crawled into a bead pack, carbon breathing in the gaps, gold at the triple points. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] needle felt (band 0.06 -> gate) — a few
 # horsehair filaments become a dense oriented needle felt.
 "fki_celadon_raku": dict(huemode="cloud", huebase=5, huecell=44.0, name="Celadon Raku", engine="needlefelt",
    eargs=dict(cell=8.96, ln=7, seam_t=P_J, body=0.744, fine=0.12, lowcut=1.8),
    seed=1176, lut=LUT_J, val=0.30, gild=(0.62, 0.90, 0.50),
    hues=[0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.33, 0.47, 0.105], hspan=0.045, satboost=0.95,
    macro=("bands", dict(angle=0.3, freq=2.0, warp=0.30)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.3, **_KW),
    desc="A felt of thousands of carbon needles on jade, the finest of them gold. A FRACTURED KINTSUGI finish."),
}

SHARD_MOSAIC = {
 # [SPB-FRACTURED-FIELD 2026-08-02] RD labyrinth (band 0.18 -> gate) — the
 # kaleido folds become a Turing-stripe gold labyrinth.
 "fki_gilt_shards": dict(huemode="macro", huedither=0.45, huecell=48.0, name="Gilt Shards", engine="labyrinth",
    eargs=dict(sig=0.645, iters=8, seam_t=P_G, body=0.918, fine=0.12, lowcut=1.8),
    seed=1177, lut=LUT_G, val=0.30, gild=(0.62, 0.88, 0.70),
    hues=[0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.13, 0.09, 0.55], hspan=0.06, satboost=0.94,
    macro=("continents", dict(base=3, cells=4.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.8, mfloor=10.0, **_KW),
    desc="A gold labyrinth channel winding through dark ceramic walls, everywhere at once. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] dendrite forest (band 0.34 -> gate) — the
 # chord slabs become a forest of small grown gold crystals.
 "fki_cobalt_shards": dict(huemode="cloud", huebase=8, huecell=48.0, name="Cobalt Shards", engine="dendrites",
    eargs=dict(cell=6.318, iters=3, seam_t=P_C, body=0.179, fine=0.12, lowcut=2.5),
    seed=1178, lut=LUT_C, val=0.29, gild=(0.55, 0.85, 0.90),
    hues=[0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.55, 0.47, 0.105], hspan=0.045, satboost=0.96,
    macro=("continents", dict(base=3, cells=3.5)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.4, **_KW),
    desc="A forest of small gold crystals feathering across deep cobalt slab. A FRACTURED KINTSUGI finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] structured dust (band 0.05 -> gate) — the
 # spider mosaic becomes three-scale tinted chip dust in diagonal order.
 "fki_porcelain_shards": dict(huecell=24.0, name="Porcelain Shards", engine="dust",
    eargs=dict(seam_t=P_P, body=0.807, fine=0.14, lowcut=1.8, cw0=8.1),
    seed=1179, lut=LUT_P, val=0.31, gild=(0.55, 0.85, 0.85),
    hues=[0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.62, 0.47, 0.105], hspan=0.05, satboost=0.95,
    macro=("margin", dict(freq=2.5, radius=0.72)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(mswing=1.4, gray=0.10, ccboost=1.3, ccpat=0.4, **_KW),
    desc="Porcelain ground to structured dust, three chip sizes in quiet diagonal order, gold flecks between. A FRACTURED KINTSUGI finish."),
}

GROUPS = {
    "GOLD RIVERS": GOLD_RIVERS,
    "CRACKLE WEBS": CRACKLE_WEBS,
    "BRUSHWORK": BRUSHWORK,
    "RAKU PATCHES": RAKU_PATCHES,
    "SHARD MOSAIC": SHARD_MOSAIC,
}

KIT = _KintsugiKit(engines=ENGINES, groups=GROUPS, tag="fractured-kintsugi",
                   extra_macro={"river": m_river}, work=1024)

ALL = KIT.ALL
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
