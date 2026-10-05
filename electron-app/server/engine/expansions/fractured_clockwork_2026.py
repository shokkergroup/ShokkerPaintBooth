# -*- coding: utf-8 -*-
"""FRACTURED CLOCKWORK (2026-07-30) — category 1/10 of the FRACTURED expansion.

[SPB-FRACTURED-090 2026-08-02] THIRD pass — the FLAGSHIP push. Pass 2 made
clockwork a field instead of a poster (car-band median 0.101 -> 0.656) but
sat well under the FRACTURED MINDS flagship. Parent brief: reach median
>= 0.82 "WITHOUT it being static noise or just a bunch of repeats". Result:
median 0.656 -> 0.891, per-finish min 0.749, 20/20 through every guard.

    car-band  = FFT power of (luma - mean) of the 512 paint,
                radial ring r in [64,256] over total r >= 2.

FIVE MEASURED CAUSES, in the order they mattered. Sub-band leak (r < 64) was
essentially the whole loss: at pass 2 the above-band share was only ~0.02
while `low` ran 0.20-0.53.

  C1 THE GRAIN WAS NOT IN THE BAND AT ALL. fbm()'s `base` is the random-GRID
     SIZE, so an N x N grid only reaches r = N/2 at 512. The grain ran at
     base 80 -> everything it produced sat at r <= 40, entirely under the
     band; measured on its own it scored band 0.012 with 0.80 of its power in
     r=32..64. Raising the base fixes the spectrum but turns the term into
     per-pixel noise and costs 0.06-0.10 of lag-1 coherence module-wide, so
     _grain is now an in-band LATTICE of tool marks, not noise (see _grain).
  C2 FLAT PER-CELL TINTS ARE LOW-PASS. A piecewise-constant 8-tier tint on an
     a-px lattice is a sinc main lobe spanning r = 0..640/a, so ~90 pct of its
     energy is under the band however good the shape it tints (measured on the
     plate pave: raw tint 0.135, low-cut tint 0.644, tinted crown 0.585 ->
     0.922). Every tint now goes through _ctier.
  C3 THE LUT WALK FOLDS. T -> thin-film LUT is oscillatory, so band vs `body`
     is NON-MONOTONE: the hobnail measured 0.45 / 0.43 / 0.46 / 0.60 / 0.80
     across body 0.28..1.18, and the tempering id 0.88 / 0.69 / 0.21 / 0.14 /
     0.44 across 0.22..0.64. `body` is a spectral dial, not just a contrast
     dial, and has to be swept per finish.
  C4 frac() WRAPPED ~5 PCT OF PIXELS at the top of the LUT — a full-scale luma
     cliff scattered at random, worth 0.06 band (0.917 -> 0.858) for no visual
     gain. _T now MIRRORS at the LUT ends instead (C0-continuous).
  C5 HAIRLINE FEATURES cost coherence and buy nothing: the band stops at
     r=256, so a 1-2 px rail/seam/glint dumps its power above the band and
     drags lag-1 down (the truss sat at ac 0.26). Everything is fat now (L3).

Lattice jitter and the macro dials (vd, ambient, floor, sparkle) were each
tested and are NOT material (jit 0.0 vs 0.42 moved band by 0.01-0.02; the four
pipeline dials together by <= 0.013). Two band-shaping dials, swept per
finish, do the rest — see _bandshape: `soft` trims above-band harmonics (buys
coherence, costs nothing), `lowcut` deletes sub-band drift (buys band, spends
coherence). vd (0.93,1.11) -> (0.96,1.06) and sparkle 0.28 -> 0.08 anyway,
since both were pure denominator.

GATES (fail-closed, per finish at 512; anti-cheat guards included because
white noise scores ~0.95 on band and a static-looking finish is a FAILURE at
any score): car-band >= 0.70; lag-1 horizontal autocorrelation >= 0.55;
spectral peakiness (top-20 pct of 4 px radial bins over the in-band total)
>= 0.30; connected-shape fraction (Otsu components >= 12 px) >= 0.55;
fineness > 6.5; coverage >= 56/64; hue bins >= 5; < 2.0 s @512 and <= 2.5 s
@2048 (worst measured 1.86 s); intra-module descriptor pair <= 0.55
(worst measured 0.43).

ARCHETYPE LEDGER — 20 ids, 20 DISTINCT compositional archetypes (no two ids
share one; descriptor-verified):
  fcw_brass_geartrain    gear-pack           (offset-row wall of small crowned toothed gears)
  fcw_verdigris_rivets   granular scatter    (dome-rivet field + half-scale patina pitting)
  fcw_copper_escapement  ratchet rows        (sawtooth tooth rows on domed courses)
  fcw_gold_guilloche     rosette carpet      (engine-turned rosettes, fixed-pitch petal rings)
  fcw_gunmetal_mainspring directional-lamina (rolled blued-spring bands, fat coil edges)
  fcw_bronze_scroll      contour damascene   (folded-billet contour line-work, fixed pitch)
  fcw_brass_escapement   truss lattice       (triple-rail truss, node bosses, domed panels)
  fcw_ruby_guilloche     jewel chaton pack   (cabochon domes, setting rings, côtes plate)
  fcw_copper_rivets      plate-mosaic        (bounded-Voronoi plate pave, rivets on the seams)
  fcw_gold_mainspring    hairspring drift    (curl-drifted spring threads, normalised drift)
  fcw_verdigris_scroll   engraved branching  (Voronoi acanthus grooves + engraver's hatch)
  fcw_bronze_geartrain   woven-cross         (cross-milled band weave, over/under, mill grooves)
  fcw_brass_balance      screw-head pack     (packed slotted screw heads)
  fcw_gunmetal_guilloche clous-de-paris      (hobnail pyramid waffle, 4-facet lighting)
  fcw_copper_scroll      satin sunburst      (one brush stroke per cell on a turning grain field)
  fcw_gold_geartrain     chain-mail          (overlapping interlocked ring rows)
  fcw_ruby_mainspring    tempering fringes   (constant-pitch bluing fringes + oxide pools + jewels)
  fcw_bronze_rivets      perlage             (overlapping stamped circles; spec stays macro-led)
  fcw_brass_guilloche    barleycorn lattice  (offset lens grain-d'orge engine turning)
  fcw_verdigris_gears    dendrite forest     (patina dendrites over côtes circulaires)

HIGHLIGHT-PEAK DOCTRINE: bright machined features (rim lights, jewel glints,
polished tops) sit at the LUT luma PEAK (peak_t probed per LUT, dynamic);
bodies walk below it. tmod=0.0 across the category — a macro phase shift
would walk the highlights off the peak and convert macro form into luma
banding through the oscillating LUT (kintsugi gold-peak / cathedral
dark-lead precedent).

Hue-domain DEVICE varies per id (parent correction 2026-08-02: at most 4
domain-patchwork ids; others per-cell confetti / directional flow / soft
cloud — see _ClockworkKit.macro_maps).
Palette law [SPB-FRACTURED-090 2026-08-02, parent colour review]: every
palette is the NAMED ALLOY and nothing else. The first attempt at this module
put three complementary accents (cyan/blue/magenta) in each 11-anchor palette
— 27 pct of hue cells, which at a ~9 px hue cell reads as neon confetti — and
ran satboost 1.15-1.40. Parent verdict: "nothing on this sheet reads as
METAL". Three rules now:
  * ALLOY CONTINUUM. All 11 anchors sit inside the named metal's real range
    (red brass -> yellow brass -> tarnished greenish brass, etc). The hue-bin
    gate is paid for with alloy and tarnish variation, plus genuine heat tint
    (straw / purple / blue on steel), never with complementary confetti.
  * LOW CHROMA, HIGH VALUE CONTRAST. Metal reads from specular highlight
    against dark recess, not from saturation: satboost 0.30-0.66, per-alloy
    gray 0.28-0.58 (gunmetal and blued steel are near-neutral, measured mean
    saturation 0.15-0.26), floor 0.11 -> 0.06 for deeper recesses, and `val`
    is now per-alloy so gold/brass are bright metals and gunmetal/blued steel
    are dark (measured median luma 0.43 vs 0.25).
  * JEWEL COLOUR IS AN ACCENT. Crimson appears on 2 of 11 anchors over a
    blued-steel field on the two ruby ids — a jewel bearing, never a body.
Anchors are PRE-COMPENSATED against measurement: the thin-film hue
distribution inside each hero window is not symmetric, so the palette is
corrected by the measured saturation-weighted circular-mean hue of the 512
paint until it lands on the alloy target (brass drifted -0.043 turn before
correction; all 20 now sit within ~0.03, most within 0.01). Hue is
luma-renormalised in catlib, so none of this moves a spectral gate — verified:
band median identical to 4 decimals across the whole colour rebuild.
Machined-metal spec kept from pass 1 (_ClockworkKit): polished faces GLOSSY
(R low), recesses matte, all-metal M with micro swing; fcw_bronze_rivets
keeps its macro-led spec (specmacro dial — known metric-blind dust cluster).

Built on engine/expansions/fractured_catlib_2026.py. ids, seeds (1060-1079),
GROUPS, install_into_engine and the (spec_fn, paint_fn) contract are all
UNCHANGED; spec still traces paint (measured corr(M, paint luma) 0.96).
Determinism: all randomness via catlib.rng(seed, salt) (np.random.default_rng)
and zlib-free integer cell hashes, integer salts only, no hash(str) anywhere —
verified by rebuilding each finish twice and comparing bit-for-bit. Fully
vectorized at GEN=640; only small bounded Python loops (<= 3 dilation steps,
<= 6 stroke orientations, 3 lattice scales).
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
    """T position (0..1) of the LUT luma peak — the highlight anchor.
    [SPB-FRACTURED-FIELD 2026-08-02]"""
    t = catlib.thinfilm_lut(*lut)
    L = t[:, 0] * 0.299 + t[:, 1] * 0.587 + t[:, 2] * 0.114
    return float(np.argmax(L)) / float(len(L) - 1)


# ════════════════════════════════════════════════════════════════════════════
# THE MICRO-FIELD LAW  [SPB-FRACTURED-090 2026-08-02] — parent brief: push
# clockwork to the FRACTURED MINDS flagship level (car-band median >= 0.82)
# "WITHOUT it being static noise or just a bunch of repeats". Measured
# frequency budget of the 512 paint (FFT power of luma, ring r in [64,256]
# over total r >= 2), given GEN=640 -> 512 (x0.8):
#
#     period p px at GEN  <->  r = 640 / p at 512
#     p = 10 -> r = 64 (band floor)   p = 8.6 -> r = 74   p = 2.5 -> r = 256
#
# so EVERY structure lives at 8-9.5 px at GEN (26-30 px at 2048) with its
# harmonics filling the rest of the band, or at a secondary in-band carrier of
# 2.9-3.6 px (r 180-220 — engine-turned line-work, côtes circulaires, mill
# grooves). Pass-1 measurement said the leak is almost ENTIRELY sub-band
# (low 0.20-0.53 of total power vs above-band 0.02), so the fix is four
# mechanical laws — none of which is "add noise" (white noise scores ~0.95 on
# band and FAILS every coherence guard; a static-looking finish is a failure
# at any score):
#
#   L1 SCALE     — a lattice coarser than ~10 px at GEN drops its fundamental
#                  under r=64 and the band collapses. Every cell/pitch here is
#                  8.0-9.2 px.
#   L2 RELIEF    — value must ride a SMOOTH PERIODIC RELIEF inside each cell
#                  (dome / crown / roll / pyramid / lens), never a flat
#                  per-cell tint: a flat 8-tier lattice is a low-pass field
#                  (measures band ~0.15). The 8-tier palette now TINTS the
#                  relief instead of carrying the value.
#   L3 FAT EDGES — seams, rims, rails, slots and glints get a wide smooth
#                  profile (_fat, ~2-3 px full width at GEN). Hairlines dump
#                  their power above r=256 and cost lag-1 coherence.
#   L4 LOW-CUT   — every remaining slow drift (fbm grain, warp wander, macro
#                  value) is subtracted with _flat / the `lowcut` dial, which
#                  deletes power UNDER r=64 without touching a single shape
#                  edge. Recipe-side: sparkle 0.28 -> 0.08 (the sparkle octave
#                  lands at r~320, pure denominator) and vd (0.93,1.11) ->
#                  (0.96,1.06) (macro value swing is sub-band twice over).
# ════════════════════════════════════════════════════════════════════════════

def _flat(x, s=3.0):
    """LOW-CUT a value field: subtract its own local mean (drift coarser than
    ~4s px at GEN), keep the global mean. Not a sharpen and not a noise term —
    every shape and edge survives; only the field-wide wander that lands under
    the car band is deleted. [SPB-FRACTURED-090 2026-08-02]"""
    x = np.asarray(x, np.float32)
    return x - gauss(x, float(s)) + float(x.mean())


def _fat(d, w, soft=0.34):
    """Fat, smooth edge profile from a distance field (0 = centre line): full
    for d <= 0.34w, zero past d = w. See L3. [SPB-FRACTURED-090 2026-08-02]"""
    w = np.asarray(w, np.float32)
    t = np.clip((d - w) / np.minimum(w * (float(soft) - 1.0), -1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _grain(res, seed, salt, amt=0.16, cell=7.4):
    """IN-BAND tool-mark micro-lattice — the fbm grain's replacement, and the
    correction that mattered most across all 20 ids.
    [SPB-FRACTURED-090 2026-08-02] `base` in fbm() is the random-GRID SIZE, so
    an N x N grid only reaches r = N/2 at 512: the original base-80 grain
    topped out at r=40 and lay ENTIRELY under the car band (its own band score
    measured 0.012, with 0.80 of its power sitting in r=32..64). Pushing the
    base up to 300 fixed the band but turned the term into what is effectively
    per-pixel noise, and the lag-1 coherence guard fell 0.06-0.10 across the
    module — which is the guard that separates a finish from static. So the
    grain is now a LATTICE, not noise: one soft tool mark per 7.4 px cell
    (r~86, the coherent end of the band) carrying an 8-tier value, low-cut and
    renormalised so the visible mottle is unchanged."""
    d, iv = _dot01(res, float(cell), 0.62, int(salt) + (int(seed) % 97))
    m = ((1.0 - d) ** 1.3) * (_tier(iv) - 0.55) * 2.0
    m = _flat(m, 2.4)
    return (m / (float(m.std()) + 1e-6)) * (0.34 * float(amt))


def _ctier(hv, s=2.2):
    """8-tier per-cell tint, LOW-CUT — measured, the module's biggest single
    leak after the grain. [SPB-FRACTURED-090 2026-08-02] a FLAT per-cell value
    on an a-px lattice is piecewise constant, so its power spectrum is a sinc
    main lobe spanning r = 0..640/a: ~90 pct of an 8-tier tint's energy sits
    BELOW the car band no matter how good the shape it tints (measured on the
    plate pave: raw tint band 0.135 / low-cut tint band 0.644, and the tinted
    crown 0.585 -> 0.922). _flat deletes that lobe and keeps the cell-to-cell
    contrast, so neighbouring parts CONTRAST instead of wandering — which is
    also what a real batch of machined components looks like."""
    return _flat(_tier(hv), s)


def _lat(res, cell, jit, salt, ang=0.0, rowoff=0.0, rowh=1.0):
    """Bounded-jitter point lattice -> (dx, dy, d, ci, cj) in px, odd rows
    offset by `rowoff` cells. BOUNDED jitter is a gate, not a taste call: an
    unbounded pack smears a third of its power under the car band, a bounded
    lattice keeps a sharp spectral fundamental (peakiness guard).
    [SPB-FRACTURED-090 2026-08-02]"""
    yy, xx = coords(res)
    u, v = rot((yy, xx), float(ang)) if ang else (xx, yy)
    g = float(cell)
    rh = g * float(rowh)
    cj = np.floor(v / rh)
    uo = u + np.mod(cj, 2.0) * float(rowoff) * g
    ci = np.floor(uo / g)
    jx = (h2(ci, cj, salt) - 0.5) * float(jit) * g
    jy = (h2(ci, cj, salt + 37) - 0.5) * float(jit) * rh
    dx = uo - (ci + 0.5) * g - jx
    dy = v - (cj + 0.5) * rh - jy
    return dx, dy, np.hypot(dx, dy).astype(np.float32), ci, cj


def _dot01(res, cell, jit, salt):
    """Single-tap jittered lattice -> (0..1 radial distance, cell hash). One
    ninth the cost of _voro; used for secondary scales.
    [SPB-FRACTURED-090 2026-08-02]"""
    yy, xx = coords(res)
    c = float(cell)
    ci, cj = np.floor(xx / c), np.floor(yy / c)
    jx = (h2(ci, cj, salt) - 0.5) * float(jit) * c
    jy = (h2(ci, cj, salt + 11) - 0.5) * float(jit) * c
    d = np.hypot(xx - (ci + 0.5) * c - jx, yy - (cj + 0.5) * c - jy) / (c * 0.62)
    return np.clip(d, 0.0, 1.0).astype(np.float32), h2(ci, cj, salt + 23)


def _cellhash(res, cell, salts):
    """Per-CELL hash table (small integer grid) + the per-pixel integer cell
    index. [SPB-FRACTURED-090 2026-08-02 perf] h2() is a sin over the whole
    res^2 array; _voro called it 27 times per invocation (0.2 s each, and the
    engraved-web recipe uses two webs -> 2.4 s, over the render budget). The
    hash only ever depends on the integer cell coords, so it is evaluated on a
    ~76x76 grid and gathered."""
    g = float(cell)
    yy, xx = coords(res)
    ci = np.floor(xx / g).astype(np.int32)
    cj = np.floor(yy / g).astype(np.int32)
    nc = int(res / g) + 4
    ii, jj = np.meshgrid(np.arange(-1, nc, dtype=np.float32),
                         np.arange(-1, nc, dtype=np.float32), indexing="xy")
    return ci, cj, nc, [h2(ii, jj, sl) for sl in salts]


def _voro(res, cell, jit, salt, need_id=True):
    """Bounded-jitter Voronoi -> (F1/cell, (F2-F1)/cell polygon-edge distance,
    winning-cell hash). F2-F1 gives every seam the SAME width — a real parting
    line / engraved groove instead of a morphological hairline. BOUNDED jitter
    is a gate, not a taste call: an unbounded pack smears its fundamental
    across (and under) the car band. [SPB-FRACTURED-090 2026-08-02]"""
    yy, xx = coords(res)
    g = float(cell)
    ci, cj, nc, (JX, JY, ID) = _cellhash(res, cell, (salt, salt + 40, salt + 80))
    # [SPB-FRACTURED-090 2026-08-02 perf] site COORDINATES precomputed on the
    # cell grid. The previous form evaluated (a + 0.5 + (jx - 0.5) * jit) * g
    # on the full res^2 array inside all nine taps — 27 whole-canvas ops that
    # only ever depend on the integer cell. The engraved-web recipe builds two
    # webs and was the one finish over the render budget (2.33 s @512).
    ii = np.arange(-1, nc, dtype=np.float32)
    PX = (ii[None, :] + 0.5 + (JX - 0.5) * float(jit)) * g
    PY = (ii[:, None] + 0.5 + (JY - 0.5) * float(jit)) * g
    ci1, cj1 = ci + 1, cj + 1
    f1 = np.full((res, res), 1e12, np.float32)
    f2 = np.full((res, res), 1e12, np.float32)
    idw = np.zeros((res, res), np.float32)
    for dj in (-1, 0, 1):
        bi = np.clip(cj1 + dj, 0, nc)
        for di in (-1, 0, 1):
            ai = np.clip(ci1 + di, 0, nc)
            dxq = xx - PX[bi, ai]
            dyq = yy - PY[bi, ai]
            d = dxq * dxq                                    # squared: 2 sqrts
            d += dyq * dyq                                   # total, not 9
            m = d < f1
            np.minimum(f2, d, out=f2)
            f2 = np.where(m, f1, f2)
            if need_id:
                idw = np.where(m, ID[bi, ai], idw)
            f1 = np.where(m, d, f1)
    f1 = np.sqrt(f1, dtype=np.float32)
    f2 = np.sqrt(f2, dtype=np.float32)
    return (np.clip(f1 / g, 0.0, 1.5), np.clip((f2 - f1) / g, 0.0, 1.5), idw)


def _ptier(res, cell, salt, ang=0.0, relief=0.55, jit=0.30):
    """Per-patch 8-tier metal tint on an IN-BAND lattice, each patch carrying
    its own soft dome (L2): the tint never appears as a flat cell value.
    [SPB-FRACTURED-090 2026-08-02]"""
    yy, xx = coords(res)
    u, v = rot((yy, xx), float(ang)) if ang else (xx, yy)
    c = float(cell)
    ci, cj = np.floor(u / c), np.floor(v / c)
    jx = (h2(ci, cj, salt + 3) - 0.5) * float(jit)
    jy = (h2(ci, cj, salt + 7) - 0.5) * float(jit)
    d = np.maximum(np.abs(frac(u / c) - 0.5 + jx), np.abs(frac(v / c) - 0.5 + jy)) * 2.0
    bump = sstep(1.02, 0.24, d)
    return _ctier(h2(ci, cj, salt)) * (1.0 - float(relief) + float(relief) * bump)


def _cotes(res, cx, cy, pitch, phase=0.0):
    """Côtes circulaires — concentric machined grain at a CONSTANT pitch about
    an off-canvas centre. The one watch-finishing texture that is band-pass by
    construction at any radius (r = 640/pitch), used as the secondary carrier
    under sparse archetypes. [SPB-FRACTURED-090 2026-08-02]"""
    yy, xx = coords(res)
    rad = np.hypot(xx - res * float(cx), yy - res * float(cy))
    return (0.5 + 0.5 * np.cos(rad / float(pitch) * 6.2831853 + float(phase))).astype(np.float32), rad


def _T(peak_t, bodyT, hi=0.0):
    """Compose the optical-thickness field: bright machined highlights pinned
    at the LUT luma peak, bodies walking below it.

    [SPB-FRACTURED-090 2026-08-02] the walk MIRRORS at the ends of the LUT
    instead of wrapping. frac() wrapped ~5 pct of pixels (the brightest bodies,
    wherever peak_t + body crossed 1.0) and each wrap is a full-scale luma
    cliff scattered at random across the canvas — measured cost 0.06 band
    (0.917 -> 0.858) for no visual gain. A reflection is C0-continuous, uses
    the whole LUT, and keeps the highlight anchor exactly on the peak."""
    u = float(peak_t) + np.clip(bodyT, 0.02, 0.99) * (1.0 - np.clip(hi, 0.0, 1.0))
    return (1.0 - np.abs(1.0 - np.mod(u, 2.0))).astype(np.float32)


# ════════════════════════════════════════════════════════════════════════════
# STRUCTURAL GENERATORS — every one a dense homogeneous micro-field built to
# L1-L4. T convention: highlights AT peak_t; bodies walk below.
# ════════════════════════════════════════════════════════════════════════════

def g_gearpack(res, seed, cell=9.2, jit=0.24, peak_t=0.0, body=0.62, fine=0.16):
    """gear-pack — an offset-row WALL of small toothed wheels (~28 px at 2048):
    each wheel a DOMED blank with beveled teeth, a raised hub and a jewel
    centre, packed until the flanks nearly touch.
    [SPB-FRACTURED-090 2026-08-02] band 0.636 -> gate. Pass-2 carried the value
    on a flat per-gear tint and a two-octave fbm grain (both low-pass, low
    0.343); the wheel DOME now carries it (L2), teeth and jewels are fat (L3)
    and the local tooth angle is measured from the real cell centre (pass 2
    used a global-x angle, which sheared every wheel)."""
    dx, dy, d, ci, cj = _lat(res, cell, jit, 311, rowoff=0.5)
    g = float(cell)
    th = np.arctan2(dy, dx)
    N = 5.0 + np.floor(h2(ci, cj, 312) * 3.0)                  # 5-7 fat teeth
    tri = 1.0 - np.abs(2.0 * frac(th * N / 6.2831853 + h2(ci, cj, 313)) - 1.0)
    rr = g * (0.40 + 0.05 * h2(ci, cj, 314))
    redge = rr * (0.84 + 0.16 * tri)                           # toothed outline
    inb = (redge - d) / g
    # the blank is CROWNED from tooth root to hub (a chamfered gear face): a
    # saturated plateau made the face a flat per-cell tint = low-pass (L2).
    dome = np.clip(inb / 0.40, 0.0, 1.0) ** 0.55 * sstep(0.0, 0.05, inb)
    bevel = _fat(np.abs(d - redge) / g, 0.115)                 # fat tooth bevel
    hub = sstep(0.01, 0.10, (rr * 0.42 - d) / g)
    jewel = _fat(d / g, 0.090)
    tier = _ctier(h2(ci, cj, 315))
    face = dome * (0.28 + 0.72 * tier) + hub * 0.24
    hi = np.clip(bevel * 0.85 + jewel * 0.95, 0.0, 1.0)
    return _T(peak_t, 0.13 + face * float(body) + _grain(res, seed, 316, fine), hi)


def g_rivetfield(res, seed, cell=8.6, jit=0.28, peak_t=0.0, body=0.60, fine=0.16):
    """granular scatter — a dense dome-rivet field: a driven rivet head in
    every lattice cell with a shadow collar and an off-axis glint, patina
    pitting on a half-scale lattice between them.
    [SPB-FRACTURED-090 2026-08-02] band 0.712 -> gate. cell 6.5 -> 8.6 (L1) and
    the inter-rivet ground, which was an fbm mottle, is now a second in-band
    pit lattice so there is no low-pass filler anywhere."""
    dx, dy, d, ci, cj = _lat(res, cell, jit, 321, rowoff=0.5)
    g = float(cell)
    rr = g * (0.34 + 0.06 * h2(ci, cj, 322))
    dome = np.clip(1.0 - (d / np.maximum(rr, 1e-3)) ** 2, 0.0, 1.0) ** 0.6
    collar = _fat(np.abs(d - rr * 1.08) / g, 0.115)
    glint = _fat(np.hypot(dx + rr * 0.32, dy + rr * 0.32) / g, 0.05) * (dome > 0.25)
    tier = _ctier(h2(ci, cj, 324))
    d2, i2 = _dot01(res, g * 0.62, 0.55, 327)
    pit = sstep(0.62, 0.06, d2) * _tier(i2)
    face = (dome * (0.16 + 0.84 * tier) - collar * 0.36
            + (1.0 - dome) * pit * 0.66)
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 326, fine), glint)


def g_ratchet(res, seed, pitch=8.6, rowh=9.2, angle=0.25, peak_t=0.0,
              body=0.62, fine=0.16):
    """ratchet rows — courses of fine sawtooth teeth, direction alternating per
    row, each row a domed rail with pawl-tip glints.
    [SPB-FRACTURED-090 2026-08-02] band 0.547 -> gate. pitch 4.5 -> 8.6 (the
    old fundamental sat at r~142 with every harmonic ABOVE the band) and the
    row now carries a domed cross-section, so the 9.2 px course spacing is a
    second in-band fundamental instead of a flat stripe."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 331, 2.5)
    u, v = rot((yy + wv, xx + wu), float(angle))
    row = np.floor(v / float(rowh))
    sgn = np.where(np.mod(row, 2.0) > 0.5, 1.0, -1.0)
    q = (u * sgn + row * 3.7) / float(pitch)
    ti, saw = np.floor(q), frac(q)
    fv = frac(v / float(rowh))
    rail = sstep(0.02, 0.34, 0.5 - np.abs(fv - 0.5))           # domed course
    tier = _ctier(h2(ti, row, 332))
    tooth = saw ** 0.55                                        # asymmetric ramp
    tip = _fat(np.abs(saw - 0.92), 0.07) * (h2(ti, row, 333) > 0.28)
    face = rail * (0.22 + 0.78 * tooth) * (0.28 + 0.72 * tier) + rail * 0.16
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 334, fine),
              tip * rail)


def g_rosette(res, seed, cell=9.0, rings=4.6, petals=6.0, peak_t=0.0,
              body=0.60, fine=0.16):
    """rosette carpet — true engine-turned line-work: every lattice cell holds
    a rosette whose petal-warped grooves run at a CONSTANT 2.9 px radial pitch
    (r~220), the cell itself crowned.
    [SPB-FRACTURED-090 2026-08-02] band 0.529 / pk 0.248 -> gate. Pass 2 used
    cos(d/g * rings) — a pitch that stretched with the cell, so no sharp
    fundamental anywhere. Fixing the pitch in PIXELS is what buys the
    peakiness; the grooves are also fat now (L3)."""
    dx, dy, d, ci, cj = _lat(res, cell, 0.16, 341, rowoff=0.5)
    g = float(cell)
    th = np.arctan2(dy, dx)
    q = (d + np.cos(th * float(petals) + h2(ci, cj, 342) * 6.2831853) * 1.15) / float(rings)
    line = _fat(np.abs(frac(q) - 0.5), 0.30)
    crown = sstep(0.01, 0.30, (g * 0.54 - d) / g)
    tier = _ctier(h2(ci, cj, 343))
    face = crown * (0.28 + 0.72 * tier) + (0.5 + 0.5 * np.cos(q * 6.2831853)) * 0.18
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 344, fine),
              line * 0.85)


def g_springband(res, seed, pitch=8.6, seg=9.2, angle=0.55, peak_t=0.0,
                 body=0.62, fine=0.16):
    """directional-lamina — rolled blued-spring stock laid band on band: an
    asymmetric rolled cross-section, a fat bright top edge on every coil and
    per-segment relief across the coil so the field is 2D, not a stripe.
    [SPB-FRACTURED-090 2026-08-02] band 0.533 -> gate. pitch 5.5 -> 8.6 (L1),
    the per-segment 8-tier tint moved onto a segment DOME (L2), and the edge
    light went from a 1 px hairline to a 2.2 px poured highlight (L3)."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 351, 3.0)
    u, v = rot((yy + wv, xx + wu), float(angle))
    li, fv = np.floor(v / float(pitch)), frac(v / float(pitch))
    si, fu = np.floor(u / float(seg)), frac(u / float(seg))
    tier = _ctier(h2(li, si, 352))
    roll = sstep(0.02, 0.52, fv) * sstep(1.04, 0.60, fv)       # rolled profile
    segd = 0.66 + 0.34 * sstep(0.02, 0.30, 0.5 - np.abs(fu - 0.5))
    edge = _fat(np.abs(fv - 0.10), 0.17)                       # bright coil edge
    screw = _fat(np.hypot(fu - 0.5, fv - 0.5), 0.16) * (h2(si, li, 354) > 0.82)
    face = roll * segd * (0.26 + 0.74 * tier)
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 355, fine),
              np.clip(edge * 0.9 + screw, 0.0, 1.0))


def g_contour(res, seed, period=8.4, fold=10.0, base=6, peak_t=0.0, body=0.60,
              fine=0.16):
    """contour damascene — the folded-billet look: fat bright contour lines at
    a controlled 7.2 px pitch flowing around a bounded fold displacement, each
    lamination tinted.
    [SPB-FRACTURED-090 2026-08-02] band 0.652 / pk 0.270 -> gate. Pass 2 sliced
    levels out of an fbm, so the contour SPACING was whatever the noise
    gradient happened to be (mostly sub-band). Here the pitch is fixed in
    pixels and only the fold DISPLACEMENT is noise — bounded so the local
    period stays inside 5.3-11.2 px."""
    yy, xx = coords(res)
    u, v = rot((yy, xx), float(rng(seed, 360).uniform(0, np.pi)))
    f1 = fbm(res, res, rng(seed, 361), 2, int(base))
    f2 = fbm(res, res, rng(seed, 362), 2, int(base) * 3)
    q = (v + (f1 - 0.5) * float(fold) * 2.0
         + (f2 - 0.5) * float(fold) * 0.55) / float(period)
    li, fq = np.floor(q), frac(q)
    line = _fat(np.abs(fq - 0.5), 0.24)
    relief = sstep(0.02, 0.42, np.abs(fq - 0.5) * 2.0)
    tier = _ctier(h2(li, np.floor(u / 26.0), 363))
    face = relief * (0.28 + 0.72 * tier)
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 364, fine),
              line)


def g_truss(res, seed, pitch=8.4, drop=0.10, peak_t=0.0, body=0.60, fine=0.16):
    """truss lattice — a triple-rail bridge truss at three orientations, node
    bosses where rails cross and a domed panel inside every opening.
    [SPB-FRACTURED-090 2026-08-02] band 0.693 / ac 0.489 -> gate. The rails
    were hairlines (their power lands past r=256 and costs neighbour
    coherence); fat rails plus a panel dome inside the cells put it back."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 371, 2.5)
    a0 = float(rng(seed, 372).uniform(0, np.pi))
    lat = np.zeros((res, res), np.float32)
    acc = np.zeros((res, res), np.float32)
    idsum = np.zeros((res, res), np.float32)
    panel = np.ones((res, res), np.float32)
    for k in range(3):
        u, v = rot((yy + wv, xx + wu), a0 + k * np.pi / 3.0)
        pv = v / float(pitch)
        iv = np.floor(pv)
        dv = np.abs(frac(pv) - 0.5)
        rail = np.maximum(_fat(np.abs(dv - 0.30), 0.18), _fat(dv, 0.13) * 0.75)
        rail = rail * (h2(iv, float(k), 373 + k) > float(drop))
        lat = np.maximum(lat, rail)
        acc = acc + rail
        idsum = idsum + iv * (k + 1.0)
        panel = np.minimum(panel, sstep(0.04, 0.26, dv))
    node = sstep(1.25, 1.75, acc)
    tier = _ctier(h2(idsum, 0.0, 377))
    face = panel * (0.20 + 0.80 * tier) * (0.45 + 0.55 * panel) + lat * 0.34
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 378, fine),
              np.clip(lat * 0.75 + node, 0.0, 1.0))


def g_chatons(res, seed, cell=8.6, jit=0.22, peak_t=0.0, body=0.60, fine=0.16,
              cot=5.4, plw=0.34):
    """jewel chaton pack — packed jewel bearings: ROSE-CUT faceted crown, fat setting
    ring, off-axis glint, and the mainplate between them machined with côtes
    circulaires so there is no dead ground.
    [SPB-FRACTURED-090 2026-08-02, parent review] cell 8.6 -> 7.6 and the
    crown ROSE-CUT rather than domed: this id and the screw-head pack had both
    converged on packed domes at the same 8.6 px pitch (descriptor pair 0.46).
    A finer pave + faceted crown separates them outright — measured pair
    0.458 -> -0.055 with car-band unchanged at 0.88.
    Band 0.700 / sf 0.511 / fine 9.84 -> gate.
    The old dome was a bare quadratic on a flat plate, which Otsu split into
    thousands of sub-12 px specks (shape-fraction guard); the côtes carrier
    plus a fat ring give real connected structure."""
    dx, dy, d, ci, cj = _lat(res, cell, jit, 381, rowoff=0.5)
    g = float(cell)
    rr = g * (0.30 + 0.05 * h2(ci, cj, 382))
    crown = np.clip(1.0 - (d / np.maximum(rr, 1e-3)) ** 2, 0.0, 1.0)
    fth = np.arctan2(dy, dx) / 6.2831853 * 8.0 + h2(ci, cj, 386)
    facet = 1.0 - np.abs(2.0 * frac(fth) - 1.0)            # 8 rose-cut panels
    dome = crown ** 0.42 * (0.60 + 0.40 * facet)           # flat panels, not a dome
    girdle = _fat(np.abs(frac(fth) - 0.5), 0.20) * crown   # bright facet edges
    setr = _fat(np.abs(d - rr * 1.24) / g, 0.11)
    glint = _fat(np.hypot(dx + rr * 0.34, dy + rr * 0.34) / g, 0.075)
    plate, _rad = _cotes(res, 0.30, 1.22, float(cot))
    tier = _ctier(h2(ci, cj, 383))
    # plw: the côtes plate between the jewels. Otsu was binarising the ring
    # arcs as their own sub-12 px components rather than separating jewel from
    # plate (sf 0.33), so the plate's contrast is a dial and the jewel crown
    # carries a clear whole-unit lift above it.
    face = (dome * (0.34 + 0.66 * tier) + 0.10 - setr * 0.26
            + (1.0 - crown) * plate * float(plw))
    return _T(peak_t, 0.15 + face * float(body) + _grain(res, seed, 384, fine),
              np.clip(glint + girdle * 0.45, 0.0, 1.0))


def g_platepave(res, seed, cell=8.8, jit=0.42, peak_t=0.0, body=0.62,
                fine=0.16):
    """plate-mosaic — a pave of small machined plates on a bounded-jitter
    Voronoi: every plate crowned and brushed on its own axis, dark parting
    seams, rivet rows stitched along every seam.
    [SPB-FRACTURED-090 2026-08-02] band 0.660 -> gate. Moved off the catlib
    (unbounded) worley — an unbounded pack smears a third of its power under
    r=64 — onto _voro, whose F2-F1 seam is the same width everywhere."""
    f1, edge, bid = _voro(res, float(cell), float(jit), 391)
    crown = sstep(0.02, 0.38, edge)
    seam = _fat(edge, 0.21)
    tier = _ctier(h2(np.floor(bid * 997.0), 0.0, 393))
    yy, xx = coords(res)
    ang = bid * 6.2831853
    brush = 0.5 + 0.5 * np.cos((xx * np.cos(ang) + yy * np.sin(ang)) / 5.6 * 6.2831853)
    d2, i2 = _dot01(res, float(cell) * 0.62, 0.30, 396)
    rivet = sstep(0.62, 0.10, d2) * sstep(0.40, 0.10, edge) * (i2 > 0.25)
    face = crown * (0.26 + 0.74 * tier) + brush * crown * 0.18 - seam * 0.30
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 394, fine),
              rivet)


def g_hairspring(res, seed, pitch=8.6, curl=15.0, peak_t=0.0, body=0.60,
                 fine=0.16):
    """hairspring drift — fine spring threads drifting on a curl field: fat
    thread bodies, dark gaps, per-segment tiers and a gleam on the top tier.
    [SPB-FRACTURED-090 2026-08-02] band 0.682 -> gate. The drift is now
    NORMALISED to a fixed pixel amplitude (pass 2 scaled a raw fbm gradient,
    so the local pitch wandered far under the band); pitch 5.5 -> 8.6."""
    yy, xx = coords(res)
    a = fbm(res, res, rng(seed, 401), 2, 8)
    cy, cx = np.gradient(gauss(a, 4.0))
    n = float(curl) / (float(np.hypot(cx, cy).mean()) + 1e-6)
    v, u = yy + cx * n, xx - cy * n
    ti, fv = np.floor(v / float(pitch)), frac(v / float(pitch))
    seg = np.floor(u / 9.2)
    thread = _fat(np.abs(fv - 0.5), 0.21)
    tier = _ctier(h2(ti, seg, 403))
    gleam = thread * (h2(ti, seg, 402) > 0.74)
    face = thread * (0.26 + 0.74 * tier) + 0.12
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 404, fine),
              gleam)


def g_vinemesh(res, seed, cell=9.2, cell2=7.4, thr=0.27, peak_t=0.0, body=0.62,
               fine=0.16):
    """engraved branching — hand-engraved acanthus: DARK cut grooves branching
    at true triple points on two bounded-jitter Voronoi webs, burrs glinting
    beside every cut, and shading HATCH at a 3.3 px pitch inside each cell on
    its own axis (the engraver's fill).
    [SPB-FRACTURED-090 2026-08-02] band 0.573 -> gate. The vein carrier moved
    off ridged fbm — a low-pass field dressed as a network — and the cell
    interiors, which were bare, now carry the hatch."""
    f1, e1, i1 = _voro(res, float(cell), 0.85, 411)
    f2, e2, _i2 = _voro(res, float(cell2), 0.90, 415, need_id=False)
    groove = np.clip(_fat(e1, float(thr)) + _fat(e2, float(thr) * 0.80) * 0.8,
                     0.0, 1.0)
    burr = _fat(np.abs(e1 - float(thr) * 1.9), float(thr) * 0.45) * (1.0 - groove)
    yy, xx = coords(res)
    ang = np.floor(i1 * 4.0) * (np.pi / 4.0)
    hatch = 0.5 + 0.5 * np.cos((xx * np.cos(ang) + yy * np.sin(ang)) / 5.6 * 6.2831853)
    tier = _ctier(h2(np.floor(i1 * 997.0), 0.0, 413))
    relief = sstep(0.02, 0.40, e1)
    face = relief * (0.26 + 0.74 * tier) \
        + hatch * (0.20 + 0.34 * _ctier(h2(np.floor(i1 * 991.0), 3.0, 417))) \
        - groove * 0.44
    return _T(peak_t, 0.16 + face * float(body) + _grain(res, seed, 414, fine),
              burr * 0.55)


def g_crossmill(res, seed, pitch=8.8, gap=0.26, angle=0.20, mill=4.6,
                peak_t=0.0, body=0.60, fine=0.16):
    """cross-mill weave — two orthogonal sets of milled bands going over and
    under by cell parity, each band cut with 2.9 px mill grooves and burnished
    on its crown.
    [SPB-FRACTURED-090 2026-08-02] band 0.674 -> gate. The under-set is now
    actually visible in the gaps (a real weave, not a checkerboard mask) and
    the mill groove pitch is fixed in pixels at r~220."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 421, 2.0)
    u, v = rot((yy + wv, xx + wu), float(angle))
    pu, pv = u / float(pitch), v / float(pitch)
    iu, iv = np.floor(pu), np.floor(pv)
    fu, fv = frac(pu), frac(pv)
    bu = sstep(float(gap) * 0.5, float(gap) * 0.5 + 0.16, 0.5 - np.abs(fu - 0.5))
    bv = sstep(float(gap) * 0.5, float(gap) * 0.5 + 0.16, 0.5 - np.abs(fv - 0.5))
    par = np.mod(iu + iv, 2.0) > 0.5
    top = np.where(par, bu, bv)
    bot = np.where(par, bv, bu)
    vis = np.maximum(top, bot * 0.55)
    grv = np.where(par, 0.5 + 0.5 * np.cos(u / float(mill) * 6.2831853),
                   0.5 + 0.5 * np.cos(v / float(mill) * 6.2831853))
    tier = _ctier(np.where(par, h2(iu, iv, 422), h2(iv, iu, 423)))
    burn = _fat(np.abs(np.where(par, fu, fv) - 0.5), 0.19) * top \
        * (h2(iu, iv, 424) > 0.45)
    face = vis * (0.24 + 0.76 * tier) * (0.70 + 0.30 * grv)
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 425, fine),
              burn)


def g_screwpack(res, seed, cell=8.6, jit=0.24, peak_t=0.0, body=0.60,
                fine=0.16):
    """screw-head pack — a plate packed edge to edge with slotted screw heads:
    domed head, fat dark slot at a per-screw angle, fat rim glint.
    [SPB-FRACTURED-090 2026-08-02] band 0.716 / ac 0.520 -> gate. Head radius
    0.30 -> 0.38 cell (heads now nearly touch, so there is no low-pass ground
    between them) and the slot/rim went fat (L3)."""
    dx, dy, d, ci, cj = _lat(res, cell, jit, 431, rowoff=0.5)
    g = float(cell)
    rr = g * (0.38 + 0.05 * h2(ci, cj, 432))
    head = sstep(0.01, 0.12, (rr - d) / g)
    dome = sstep(0.02, 0.20, (rr - d) / g)
    sa = h2(ci, cj, 433) * np.pi
    sv = dx * np.sin(sa) - dy * np.cos(sa)
    slot = _fat(np.abs(sv) / g, 0.115) * head
    rim = _fat(np.abs(d - rr) / g, 0.090) * (h2(ci, cj, 434) > 0.28)
    tier = _ctier(h2(ci, cj, 435))
    face = head * (0.28 + 0.72 * tier) * (0.74 + 0.26 * dome) - slot * 0.34 + 0.10
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 436, fine),
              rim)


def g_hobnail(res, seed, pitch=9.2, angle=0.79, warp=0.0, peak_t=0.0,
              body=0.62, fine=0.16):
    """clous de Paris — a hobnail waffle of little truncated pyramids with
    4-facet directional lighting, fat facet ridges and lit tips.
    [SPB-FRACTURED-090 2026-08-02] band 0.635 / fine 9.84 -> gate. The facet
    shading was smoothed almost flat by an sstep on the facet difference;
    hard facets plus fat ridges restore both the fineness and the harmonics."""
    yy, xx = coords(res)
    # [SPB-FRACTURED-090] warp default 2.0 -> 0.0: a domain warp is
    # low-frequency PHASE noise on the waffle, and it smeared the
    # fundamental's skirt under r=64 (low 0.32).
    if float(warp) > 0.0:
        wu, wv = warp_pair(res, seed, 441, float(warp))
        u, v = rot((yy + wv, xx + wu), float(angle))
    else:
        u, v = rot((yy, xx), float(angle))
    fu = frac(u / float(pitch)) - 0.5
    fv = frac(v / float(pitch)) - 0.5
    iu, iv = np.floor(u / float(pitch)), np.floor(v / float(pitch))
    hgt = 0.5 - np.maximum(np.abs(fu), np.abs(fv))
    lit = np.where(np.abs(fu) > np.abs(fv), -np.sign(fu), -np.sign(fv))
    shade = 0.5 + 0.5 * lit * sstep(0.01, 0.07, np.abs(np.abs(fu) - np.abs(fv)))
    ridge = _fat(np.abs(np.abs(fu) - np.abs(fv)), 0.095)
    tip = sstep(0.34, 0.47, hgt)
    tier = _ctier(h2(iu, iv, 442), 1.5)
    face = (0.28 + 0.72 * tier) * (0.45 * shade + 0.55 * sstep(0.0, 0.5, hgt))
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 443, fine),
              np.clip(tip * 0.8 + ridge * 0.5 * (shade > 0.6), 0.0, 1.0))


def g_scratchfelt(res, seed, cell=8.6, ln=9, peak_t=0.0, body=0.60, fine=0.16,
                  jit=0.62, cot=5.0):
    """satin sunburst — one short brush stroke per lattice cell, oriented
    TANGENT to a slowly turning grain field (soleil satin), over a burnish
    ripple of côtes circulaires at 3.4 px.
    [SPB-FRACTURED-090 2026-08-02] band 0.676 -> gate; this is the archetype
    the brief flagged as capped near 0.75-0.80. A 2.2 pct random scatter of
    strokes is a sparse field on quiet ground = low-pass; a stroke in EVERY
    8.6 px cell with a COHERENT direction is the same satin at the car-band
    scale, and the coherent direction is what buys the peakiness back."""
    yy, xx = coords(res)
    dx, dy, d, ci, cj = _lat(res, cell, jit, 451)
    ang0 = np.arctan2(yy - res * 1.35, xx - res * 0.22) + np.pi * 0.5
    ob = np.mod(ang0, np.pi) / (np.pi / 6.0) + (h2(ci, cj, 452) - 0.5) * 0.9
    ori = np.clip(ob.astype(np.int32), 0, 5)
    val = 0.35 + 0.65 * _ctier(h2(ci, cj, 453))
    dot = (d < 0.95)
    felt = np.zeros((res, res), np.float32)
    gl = np.zeros((res, res), np.float32)
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
        if k % 2 == 0:
            gl = np.maximum(gl, st * (h2(ci, cj, 454) > 0.70))
    felt = gauss(felt, 0.6)
    gl = gauss(gl, 0.6)
    burn, _r = _cotes(res, 0.22, 1.35, float(cot))
    tier = _ptier(res, 8.8, 455, 0.7, 0.60)
    face = np.clip(felt, 0.0, 1.2) * 0.48 + tier * 0.40 + burn * 0.24
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 456, fine),
              np.clip(gl * 1.3, 0.0, 1.0))


def g_chainmail(res, seed, cell=8.8, peak_t=0.0, body=0.60, fine=0.16):
    """chain-mail — overlapping interlocked ring rows (imbrication): fat wire
    bands, the lower row shadowed under the upper, link crowns gleaming.
    [SPB-FRACTURED-090 2026-08-02] band 0.745 (module best) -> pushed further:
    the ring band went from an sstep hairline to a fat _fat wire and the link
    crown highlight is its own inner band."""
    yy, xx = coords(res)
    g = float(cell)
    rowh = g * 0.58
    ring = np.zeros((res, res), np.float32)
    tierf = np.zeros((res, res), np.float32)
    top = np.zeros((res, res), np.float32)
    for o in (0, 1):
        row = np.floor((yy - o * rowh) / (rowh * 2.0))
        yc = (row + 0.5) * rowh * 2.0 + o * rowh
        sh = np.mod(row + o, 2.0) * 0.5 * g
        ci = np.floor((xx + sh) / g)
        d = np.hypot(xx - ((ci + 0.5) * g - sh), yy - yc)
        rr = g * 0.44
        band = _fat(np.abs(d - rr), g * 0.20)
        vis = band * (1.0 - o * 0.30)
        m = vis > ring
        ring = np.where(m, vis, ring)
        tierf = np.where(m, _ctier(h2(ci, row + o * 31.0, 471)), tierf)
        top = np.where(m, _fat(np.abs(d - rr * 0.88), g * 0.10) * band, top)
    face = ring * (0.24 + 0.76 * tierf) + 0.10
    hi = top * (h2(np.floor(xx / 4.4), np.floor(yy / 4.4), 472) > 0.45)
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 473, fine),
              hi)


def g_temperbillow(res, seed, cell=9.4, pitch=4.8, peak_t=0.0, body=0.64,
                   fine=0.16, jewel=9.0):
    """tempering fringes — spring bluing: concentric heat fringes sweeping the
    whole panel at a fixed 4.8 px pitch, each fringe carrying its own oxide
    tier (straw -> brown -> purple -> blue, the real bluing sequence), oxide
    pools mottling them on a 9.4 px lattice, jewel domes set through.
    [SPB-FRACTURED-090 2026-08-02] the module's stubborn id — FOUR carriers
    measured before this one: 3-octave fbm 0.47; three-scale metaballs 0.61
    ceiling (pools ran several cells wide at every jitter and exponent);
    wide-spaced posterised fringes 0.24 (the 8-tier quantiser put 8 steps
    inside one 4.8 px ring = sub-pixel aliasing, and the 17 px halo carrying
    the value was pure sub-band); per-cell fringes 0.53 (a source lattice at
    the cell pitch means the radius never spans more than ~1.4 rings, so the
    'fringe' degenerates to one dome per cell). The fix is to DECOUPLE the two
    scales: fringe curvature comes from a far off-canvas centre, so the ring
    PITCH is constant in pixels and lands at r~133 wherever you look, while
    the pools keep their own 9.4 px fundamental at r~68."""
    cot, rad = _cotes(res, 1.42, -0.28, float(pitch))
    bandi = np.floor(rad / float(pitch))
    tier = _ctier(h2(bandi, np.floor(rad / (float(pitch) * 9.0)), 483))
    step = _fat(np.abs(cot - 0.5), 0.20)
    dx, dy, d, ci, cj = _lat(res, cell, 0.40, 481, rowoff=0.5)
    pool = np.clip(1.0 - d / (float(cell) * 0.64), 0.0, 1.0) ** 0.55
    ptier = _ctier(h2(ci, cj, 484))
    dxj, dyj, dj, ji, jj = _lat(res, float(jewel), 0.45, 492)
    jm = (h2(ji, jj, 493) > 0.62).astype(np.float32)
    jw = np.clip(1.0 - (dj / (float(jewel) * 0.28)) ** 2, 0.0, 1.0) ** 0.6 * jm
    glint = np.clip(_fat(dj / float(jewel), 0.09) * jm, 0.0, 1.0)
    face = ((0.26 + 0.74 * tier) * (0.52 + 0.48 * cot)
            + pool * (0.18 + 0.82 * ptier) * 0.42 - step * 0.10 + jw * 0.34)
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 486, fine),
              glint)


def g_perlage(res, seed, cell=8.6, peak_t=0.0, body=0.60, fine=0.16,
              swirl=4.6):
    """perlage — offset rows of overlapping polished circles, each stamped over
    the last: a shallow dome per circle, its cutting arc fat and bright, a
    2.9 px lapping swirl inside, swarf dust on a 3.6 px lattice between.
    [SPB-FRACTURED-090 2026-08-02] band 0.520 -> gate. The swirl pitch was
    tied to the cell (so no fixed fundamental) and the dust was a single-pixel
    threshold (indistinguishable from noise on a car, and above the band).
    NOTE this id keeps its macro-led SPEC (specmacro) — only the paint is a
    field. """
    yy, xx = coords(res)
    g = float(cell)
    rh = g * 0.68
    row = np.floor(yy / rh)
    xo = xx + np.mod(row, 2.0) * 0.5 * g
    ci = np.floor(xo / g)
    dx, dy = xo - (ci + 0.5) * g, yy - (row + 0.5) * rh
    d = np.hypot(dx, dy)
    rr = g * 0.54
    # each stamp is a shallow DISH, not a flat disc: a saturated `inside` mask
    # turned the field back into a flat per-cell tint (L2).
    inside = np.clip((rr - d) / (g * 0.54), 0.0, 1.0) ** 0.5
    arc = _fat(np.abs(d - rr) / g, 0.145)
    sw = 0.5 + 0.5 * np.cos(d / float(swirl) * 6.2831853
                            + h2(ci, row, 491) * 6.2831853)
    tier = _ctier(h2(ci, row, 493))
    dd, di = _dot01(res, 5.6, 0.85, 494)
    dust = sstep(0.88, 0.18, dd) * (di > 0.62)
    face = inside * (0.22 + 0.78 * tier) * (0.66 + 0.34 * sw) + dust * 0.30
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 495, fine),
              np.clip(arc * 0.85 + dust * 0.55 * (di > 0.90), 0.0, 1.0))


def g_barleycorn(res, seed, cell=8.6, angle=0.3, peak_t=0.0, body=0.60,
                 fine=0.16):
    """barleycorn — grain d'orge engine turning: offset rows of little
    lens-shaped grains, stretch alternating per row, each lens domed with an
    internal crest ring and a fat groove between neighbours.
    [SPB-FRACTURED-090 2026-08-02] band 0.759 (module best) -> pushed further:
    the lens now carries a real dome and the inter-grain groove is fat, so the
    8.6 px fundamental and its second harmonic both sit inside the band."""
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 501, 2.0)
    u, v = rot((yy + wv, xx + wu), float(angle))
    g = float(cell)
    rh = g * 0.60
    row = np.floor(v / rh)
    uo = u + np.mod(row, 2.0) * 0.5 * g
    ci = np.floor(uo / g)
    du, dv = frac(uo / g) - 0.5, frac(v / rh) - 0.5
    sq = np.where(np.mod(row, 2.0) > 0.5, 1.25, 0.80)
    q = np.sqrt(np.maximum((du * 2.0 * sq) ** 2 + (dv * 2.0 / sq) ** 2, 0.0))
    dome = np.clip(1.0 - q * q, 0.0, 1.0) ** 0.38
    groove = _fat(np.abs(q - 1.0), 0.24)
    ridge = 0.5 + 0.5 * np.cos(q * 1.0 * 6.2831853 + h2(ci, row, 502) * 6.2831853)
    crest = _fat(np.abs(q - 0.34), 0.28) * (h2(ci, row, 504) > 0.30)
    tier = _ctier(h2(ci, row, 503))
    face = dome * (0.18 + 0.82 * tier) * (0.72 + 0.28 * ridge) - groove * 0.58
    return _T(peak_t, 0.14 + face * float(body) + _grain(res, seed, 505, fine),
              crest)


def g_patinadendrite(res, seed, cell=9.0, iters=3, peak_t=0.0, body=0.62,
                     fine=0.16, cot=5.6):
    """patina dendrites — a verdigris crystal grown in EVERY lattice cell by
    gated anisotropic dilation (per-cell habit axis), eating a bronze plate
    machined with côtes circulaires; fresh metal glints at the crystal rims.
    [SPB-FRACTURED-090 2026-08-02] band 0.460 (module worst) -> gate; the
    brief flags patina dendrites as a capped archetype. A 0.2 pct seed scatter
    is sparse features on quiet ground = low-pass, and the old ground was an
    fbm tier. One crystal per 9 px cell keeps the crystal HABIT exactly while
    making the forest dense, and the côtes carrier under it is band-pass by
    construction, so the sparse channel no longer has to carry the band."""
    dx, dy, d, ci, cj = _lat(res, cell, 0.55, 511)
    acc = (d < 1.75).astype(np.float32) * (0.55 + 0.45 * h2(ci, cj, 512))
    k1 = np.array([[0, 1, 0], [0, 1, 0], [0, 1, 0]], np.uint8)
    k2 = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], np.uint8)
    k3 = np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]], np.uint8)
    ks = (k1, k1.T, k2, k3)
    axis = np.clip((h2(ci, cj, 513) * 4.0).astype(np.int32), 0, 3)
    for i in range(int(iters)):
        grow = np.zeros_like(acc)
        for a in range(4):
            grow = np.maximum(grow, cv2.dilate(acc * (axis == a), ks[(a + i) % 4]))
        acc = np.maximum(acc, grow * 0.93)
    acc = gauss(acc, 1.15)
    plate, _rad = _cotes(res, 1.28, 0.18, float(cot))
    tier = _ptier(res, 8.8, 514, 0.4, 0.55)
    pat = np.clip(acc * 1.6, 0.0, 1.0) * sstep(0.10, 0.30, acc)
    rimg = _fat(np.abs(acc - 0.26), 0.16)
    face = plate * 0.32 + tier * 0.46 - pat * 0.46
    return _T(peak_t, 0.16 + face * float(body) + _grain(res, seed, 515, fine),
              rimg * 0.55)


def _bandshape(fn):
    """Wrap a generator with the two BAND-SHAPING dials. [SPB-FRACTURED-090
    2026-08-02] Neither touches a shape or an edge position; together they are
    the whole tuning surface, swept per finish:

      soft   — trims the r>256 harmonics a hard edge throws off. They cost
               lag-1 neighbour coherence and buy no band energy, because the
               band stops at r=256. Cheap ac, paid for in nothing.
      lowcut — subtracts the field's own slow local mean (keeping the global
               mean, so the LUT walk and the highlight anchor are unchanged),
               deleting power UNDER r=64. Buys band, spends coherence — so it
               is only spendable once `soft` has banked the surplus.
    """
    def g(res, seed, lowcut=0.0, soft=0.0, **kw):
        T = np.asarray(fn(res, seed, **kw), np.float32)
        if float(soft) > 0.0:
            T = gauss(T, float(soft))
        if float(lowcut) > 0.0:
            T = T - (gauss(T, float(lowcut)) - float(T.mean()))
            T = np.clip(T, 0.002, 0.998)
        return T
    g.__name__ = fn.__name__
    g.__doc__ = fn.__doc__
    g.__wrapped__ = fn
    return g


ENGINES = {
    "gearpack": g_gearpack, "rivetfield": g_rivetfield, "ratchet": g_ratchet,
    "rosette": g_rosette, "springband": g_springband, "contour": g_contour,
    "truss": g_truss, "chatons": g_chatons, "platepave": g_platepave,
    "hairspring": g_hairspring, "vinemesh": g_vinemesh,
    "crossmill": g_crossmill, "screwpack": g_screwpack, "hobnail": g_hobnail,
    "scratchfelt": g_scratchfelt, "chainmail": g_chainmail,
    "temperbillow": g_temperbillow, "perlage": g_perlage,
    "barleycorn": g_barleycorn, "patinadendrite": g_patinadendrite,
}
# [SPB-FRACTURED-090 2026-08-02] every engine gets the two band-shaping dials.
ENGINES = {k: _bandshape(v) for k, v in ENGINES.items()}


# ════════════════════════════════════════════════════════════════════════════
# CATEGORY-SPECIFIC MACRO KIND — dial. [SPB-FRACTURED-FIELD 2026-08-02] kept
# for the extra_macro contract; used only as GENTLE modulation (narrow vd).
# ════════════════════════════════════════════════════════════════════════════

def m_dial(r, mp, seed, K):
    """Watch dial: luminous center medallion + chapter ring + dim outer
    track; 12 hour sectors = domain."""
    yy, xx = K.coords(r)
    cx, cy = float(mp.get("cx", 0.5)), float(mp.get("cy", 0.5))
    dist = np.hypot((xx / r) - cx, (yy / r) - cy) / max(float(mp.get("radius", 0.46)), 1e-3)
    ang = np.arctan2((yy / r) - cy, (xx / r) - cx)
    med = K.sstep(0.55, 0.15, dist) * float(mp.get("med", 0.9))
    chapter = np.exp(-((dist - 0.82) ** 2) * float(mp.get("ring_sharp", 40.0)))
    track = K.sstep(0.95, 1.30, dist) * 0.30
    M = np.clip(med + chapter * 1.05 + track + 0.06, 0.0, 1.0)
    D = K.n01(K.h2(np.floor((ang / np.pi + 1.0) * 6.0), np.floor(dist * 3.0), 53)
              + dist * 0.20)
    return M, D


# ════════════════════════════════════════════════════════════════════════════
# MACHINED-METAL SPEC KIT — kept from pass 1 (the good physics): polished
# faces GLOSSY (R low), recesses matte, all-metal M with micro swing;
# specmacro = opt-in macro-led spec (fcw_bronze_rivets, metric-blind dust
# cluster). [SPB-FRACTURED-FIELD 2026-08-02] adds the shard-scale hue-domain
# override (kintsugi precedent): per-cell anchor pick = alloy mottle, not
# giant camo patches.
# ════════════════════════════════════════════════════════════════════════════

class _ClockworkKit(catlib.CategoryKit):
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
            cfield = n01(0.72 * domw + 0.28 * hdom)
            msw = float(rkw.get("mswing", 1.0))
            mfl = float(rkw.get("mfloor", 30.0))
            ccb = float(rkw.get("ccboost", 1.0))
            rcl = float(rkw.get("rceil", 210.0))
            # machined metal: everything metallic, texture rides the micro
            M = np.clip(150.0 + (pattern - 0.5) * 130.0
                        + (micro - 0.5) * 130.0 * msw + edge * 70.0, mfl, 255.0)
            # polished faces glossy, recesses matte, tool edges lightly rough
            R = np.clip(38.0 + (1.0 - pattern) * 130.0 + (0.5 - micro) * 44.0
                        + edge * 30.0, 8.0, rcl)
            # [uniq r3 2026-08-01] opt-in per-recipe (fcw_bronze_rivets):
            # specmacro pushes M and R the SAME direction along a blurred
            # macro field so the spec luma carries macro geometry (the
            # fmo_luna_dust dust-cluster escape). Default 0.0 = untouched.
            smac = float(rkw.get("specmacro", 0.0))
            if smac > 0.0:
                macroL = gauss(pattern, 5.0)
                M = np.clip(M + (macroL - 0.5) * 220.0 * smac
                            - edge * 70.0 * smac - (micro - 0.5) * 130.0 * msw * smac,
                            mfl, 255.0)
                R = np.clip(R + (macroL - 0.5) * 180.0 * smac
                            - edge * 30.0 * smac - (0.5 - micro) * 44.0 * smac,
                            8.0, rcl)
            Cc = np.clip(222.0 - cfield * 195.0 * ccb + micro * 24.0, 16.0, 255.0)
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
# RECIPES — 20 finishes, ids fcw_*, seeds 1060-1079 (UNCHANGED ids/seeds).
# [SPB-FRACTURED-FIELD 2026-08-02] one archetype per id (ledger at top),
# highlights pinned at the LUT luma peak (peak_t), tmod=0.0, vd (0.93, 1.11),
# weighted 11-anchor metal palettes.
# ════════════════════════════════════════════════════════════════════════════

# LUT families + probed luma-peak highlight anchors (dynamic).
LUT_B = (390.0, 950.0, 1.00, 1.30, 0.6)    # brass
LUT_V = (400.0, 925.0, 1.05, 1.30, 3.1)    # verdigris
LUT_C = (380.0, 955.0, 1.00, 1.35, 1.8)    # copper
LUT_G = (400.0, 940.0, 0.95, 1.30, 2.4)    # gold
LUT_S = (400.0, 900.0, 1.00, 1.05, 4.2)    # gunmetal / steel
LUT_R = (380.0, 965.0, 1.00, 1.35, 5.8)    # ruby-steel
LUT_Z = (390.0, 945.0, 1.05, 1.20, 4.1)    # bronze
P_B = _lut_peak(LUT_B); P_V = _lut_peak(LUT_V); P_C = _lut_peak(LUT_C)
P_G = _lut_peak(LUT_G); P_S = _lut_peak(LUT_S); P_R = _lut_peak(LUT_R)
P_Z = _lut_peak(LUT_Z)

# weighted 11-anchor metal families (~73 pct family, ~7 pct accents, 5 bins)
BRASS = "hues=[0.125, 0.138, 0.148, 0.157, 0.165, 0.172, 0.180, 0.188, 0.197, 0.208, 0.112]"
VERDI = "hues=[0.445, 0.455, 0.463, 0.470, 0.470, 0.477, 0.485, 0.495, 0.507, 0.100, 0.088]"
COPPR = "hues=[0.004, 0.015, 0.025, 0.033, 0.042, 0.050, 0.058, 0.068, 0.080, 0.094, 0.112]"
GOLDM = "hues=[0.102, 0.114, 0.124, 0.132, 0.138, 0.144, 0.150, 0.158, 0.168, 0.180, 0.090]"
GUNMT = "hues=[0.560, 0.567, 0.573, 0.578, 0.583, 0.590, 0.599, 0.112, 0.095, 0.680, 0.640]"
RUBYS = "hues=[0.558, 0.565, 0.571, 0.577, 0.583, 0.590, 0.598, 0.606, 0.615, 0.985, 0.995]"
BRONZ = "hues=[0.057, 0.071, 0.083, 0.093, 0.102, 0.110, 0.119, 0.129, 0.141, 0.157, 0.045]"

# [SPB-FRACTURED-090 2026-08-02] gray 0.22: eyeball pass against the shipped
# FRACTURED MINDS flagship — clockwork was reading as saturated plastic, not
# metal. catlib's gray dial pulls chroma toward each pixel's OWN luma, so it
# is luma-neutral and moves no spectral gate. sparkle 0.28 -> 0.08: the
# sparkle octave lands at r~320, above the band, so it was pure denominator.
_KW = dict(ambient=0.05, ambient_sigma=44, floor=0.06, sparkle=0.08)

ROW1 = {
 # [SPB-FRACTURED-FIELD 2026-08-02] gear-pack (band 0.16-cat -> gate) — the
 # single big gear train is now a WALL of small toothed gears.
 "fcw_brass_geartrain": dict(huemode="macro", huecell=9.5, name="Brass Gear Train", engine="gearpack",
    eargs=dict(cell=9.2, jit=0.24, peak_t=P_B, body=0.62, fine=0.16, lowcut=1.2, soft=0.9),
    seed=1060, lut=LUT_B, val=0.355,
    hues=None, hspan=0.055, satboost=0.62,
    macro=("continents", dict(base=3, cells=3.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.34, mswing=1.5, **_KW),
    desc="A solid wall of small brass gears, every tooth, rim and jewel picked out in light. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] granular scatter — dense dome rivets.
 "fcw_verdigris_rivets": dict(huemode="macro", huecell=6.5, name="Verdigris Rivets", engine="rivetfield",
    eargs=dict(cell=8.6, jit=0.28, peak_t=P_V, body=0.60, fine=0.16, lowcut=1.2, soft=0.9),
    seed=1061, lut=LUT_V, val=0.300,
    hues=None, hspan=0.055, satboost=0.54,
    macro=("domains", dict(cells=6, salt=1061)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.40, mswing=1.4, **_KW),
    desc="Thousands of small rivet domes glinting through a verdigris patina field. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] ratchet rows — fine sawtooth courses.
 "fcw_copper_escapement": dict(huemode="flow", huedir=0.25, huecell=8.0, name="Copper Escapement", engine="ratchet",
    eargs=dict(pitch=8.6, rowh=9.2, angle=0.25, peak_t=P_C, body=0.62, fine=0.16, lowcut=2.6, soft=0.9),
    seed=1062, lut=LUT_C, val=0.335,
    hues=None, hspan=0.055, satboost=0.66,
    macro=("bands", dict(angle=0.25, freq=2.5, warp=0.25)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.32, mswing=1.5, **_KW),
    desc="Row after row of fine copper ratchet teeth, every pawl tip catching light. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] rosette carpet — engine-turned cells.
 "fcw_gold_guilloche": dict(huecell=10.0, name="Gold Guilloché", engine="rosette",
    eargs=dict(cell=9.0, rings=4.6, petals=6.0, peak_t=P_G, body=0.60, fine=0.16, lowcut=2.6, soft=1.4),
    seed=1063, lut=LUT_G, val=0.375,
    hues=None, hspan=0.055, satboost=0.64,
    macro=("rings", dict(freq=4.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.28, mswing=1.6, mfloor=10.0, **_KW),
    desc="A carpet of tiny gold engine-turned rosettes, crest after crest in ordered rows. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] directional-lamina — rolled spring bands.
 "fcw_gunmetal_mainspring": dict(huemode="flow", huedir=0.55, huecell=9.0, name="Gunmetal Mainspring", engine="springband",
    eargs=dict(pitch=8.6, seg=9.2, angle=0.55, peak_t=P_S, body=0.62, fine=0.16, lowcut=0.0, soft=0.5),
    seed=1064, lut=LUT_S, val=0.255,
    hues=None, hspan=0.055, satboost=0.30,
    macro=("rachis", dict(angle=0.55, lanes=6.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.58, mswing=1.4, **_KW),
    desc="Fine rolled gunmetal spring stock laid band on band, bright edges up. A FRACTURED CLOCKWORK finish."),
}

ROW2 = {
 # [SPB-FRACTURED-FIELD 2026-08-02] contour damascene — onion line-work.
 "fcw_bronze_scroll": dict(huemode="cloud", huebase=4, huecell=9.0, name="Bronze Scroll", engine="contour",
    eargs=dict(period=8.4, fold=10.0, base=6, peak_t=P_Z, body=0.60, fine=0.16, lowcut=1.8, soft=1.4),
    seed=1065, lut=LUT_Z, val=0.315,
    hues=None, hspan=0.055, satboost=0.60,
    macro=("continents", dict(base=3, cells=3.5)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.36, mswing=1.4, **_KW),
    desc="Bronze damascene — a thousand fine contour lines flowing around every fold. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] truss lattice — double-rail truss.
 "fcw_brass_escapement": dict(huemode="cloud", huebase=6, huecell=8.0, name="Brass Escapement", engine="truss",
    eargs=dict(pitch=9.4, drop=0.10, peak_t=P_B, body=0.70, fine=0.16, lowcut=2.6, soft=0.9),
    seed=1066, lut=LUT_B, val=0.355,
    hues=None, hspan=0.070, satboost=0.62,
    macro=("bands", dict(angle=0.9, freq=2.5, warp=0.25)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.34, mswing=1.5, **_KW),
    desc="A fine brass truss lattice, twin rails and slotted node screws everywhere. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] jewel chaton pack — packed jewel domes.
 "fcw_ruby_guilloche": dict(huecell=8.0, name="Ruby Guilloché", engine="chatons",
    eargs=dict(cell=7.6, jit=0.22, cot=5.4, peak_t=P_R, body=0.60, fine=0.16, lowcut=0.0, soft=0.9),
    seed=1067, lut=LUT_R, val=0.265,
    hues=None, hspan=0.055, satboost=0.40,
    macro=("domains", dict(cells=7, salt=1067)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.52, mswing=1.5, **_KW),
    desc="A pave of small ruby jewel bearings, each dome glinting in its setting ring. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] plate-mosaic — riveted plate pave.
 "fcw_copper_rivets": dict(huecell=7.5, name="Copper Rivet Plate", engine="platepave",
    eargs=dict(cell=8.8, jit=0.42, peak_t=P_C, body=0.62, fine=0.16, lowcut=1.8, soft=0.9),
    seed=1068, lut=LUT_C, val=0.335,
    hues=None, hspan=0.055, satboost=0.66,
    macro=("continents", dict(base=3, cells=3.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.32, mswing=1.4, **_KW),
    desc="Small copper plates parted by dark seams, rivet rows stitching every joint. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] hairspring drift — curl-drifted threads.
 "fcw_gold_mainspring": dict(huemode="flow", huedir=1.00, huecell=9.0, name="Gold Mainspring", engine="hairspring",
    eargs=dict(pitch=8.6, curl=15.0, peak_t=P_G, body=0.60, fine=0.16, lowcut=0.0, soft=0.5),
    seed=1069, lut=LUT_G, val=0.375,
    hues=None, hspan=0.055, satboost=0.64,
    macro=("vortex", dict(arms=2.0, twist=7.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.28, mswing=1.6, mfloor=10.0, **_KW),
    desc="Fine gold hairspring threads drifting in slow curls across the plate. A FRACTURED CLOCKWORK finish."),
}

ROW3 = {
 # [SPB-FRACTURED-FIELD 2026-08-02] branching-mesh — engraved vein web.
 "fcw_verdigris_scroll": dict(huemode="cloud", huebase=3, huecell=12.0, name="Verdigris Scroll", engine="vinemesh",
    eargs=dict(cell=9.2, cell2=7.4, thr=0.27, peak_t=P_V, body=0.62, fine=0.16, lowcut=1.8, soft=0.9),
    seed=1070, lut=LUT_V, val=0.300,
    hues=None, hspan=0.055, satboost=0.54,
    macro=("bands", dict(angle=0.2, freq=2.0, warp=0.30)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.40, mswing=1.4, **_KW),
    desc="An engraved acanthus web cut dark into verdigris plate, burrs glinting beside every groove. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] woven-cross — cross-milled weave.
 "fcw_bronze_geartrain": dict(huemode="flow", huedir=0.20, huecell=8.5, name="Bronze Gear Train", engine="crossmill",
    eargs=dict(pitch=8.8, gap=0.26, angle=0.20, mill=4.6, peak_t=P_Z, body=0.60, fine=0.16, lowcut=1.8, soft=0.9),
    seed=1071, lut=LUT_Z, val=0.315,
    hues=None, hspan=0.055, satboost=0.60,
    macro=("continents", dict(base=3, cells=4.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.36, mswing=1.5, **_KW),
    desc="Bronze bands cross-milled warp over weft, burnished tops shining. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] screw-head pack — packed slot screws.
 "fcw_brass_balance": dict(huemode="macro", huecell=7.5, name="Brass Balance Wheel", engine="screwpack",
    eargs=dict(cell=8.6, jit=0.24, peak_t=P_B, body=0.60, fine=0.12, lowcut=0.0, soft=0.9),
    seed=1072, lut=LUT_B, val=0.355,
    hues=None, hspan=0.055, satboost=0.62,
    macro=("continents", dict(base=4, cells=3.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.34, mswing=1.5, **_KW),
    desc="A field of small brass balance screws, every slot at its own angle. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] clous-de-paris — hobnail waffle.
 "fcw_gunmetal_guilloche": dict(huemode="cloud", huebase=5, huecell=7.0, name="Gunmetal Guilloché", engine="hobnail",
    eargs=dict(pitch=8.6, angle=0.79, peak_t=P_S, body=1.10, fine=0.16, lowcut=0.0, soft=0.9),
    seed=1073, lut=LUT_S, val=0.255,
    hues=None, hspan=0.055, satboost=0.30,
    macro=("bands", dict(angle=0.6, freq=3.0, warp=0.25)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.58, mswing=1.4, **_KW),
    desc="Gunmetal clous de Paris — a waffle of tiny pyramids, lit facet by facet. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] scratch felt — multi-angle satin.
 "fcw_copper_scroll": dict(huemode="flow", huedir=0.30, huecell=11.0, name="Copper Scroll Plate", engine="scratchfelt",
    eargs=dict(cell=8.6, ln=9, cot=5.0, peak_t=P_C, body=0.60, fine=0.16, lowcut=1.2, soft=0.5),
    seed=1074, lut=LUT_C, val=0.335,
    hues=None, hspan=0.055, satboost=0.66,
    macro=("rachis", dict(angle=0.3, lanes=6.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.32, mswing=1.4, **_KW),
    desc="Copper plate brushed a thousand strokes at every angle, the fresh cuts glinting. A FRACTURED CLOCKWORK finish."),
}

ROW4 = {
 # [SPB-FRACTURED-FIELD 2026-08-02] chain-mail — interlocked ring rows.
 "fcw_gold_geartrain": dict(huecell=8.5, name="Gold Gear Train", engine="chainmail",
    eargs=dict(cell=8.8, peak_t=P_G, body=0.60, fine=0.16, lowcut=1.8, soft=0.9),
    seed=1075, lut=LUT_G, val=0.375,
    hues=None, hspan=0.055, satboost=0.64,
    macro=("continents", dict(base=3, cells=3.5)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.28, mswing=1.6, mfloor=10.0, **_KW),
    desc="Golden mail — overlapping ring rows locked link over link across the whole plate. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] micro-billows — tempering pools + jewels.
 "fcw_ruby_mainspring": dict(huemode="cloud", huebase=8, huecell=14.0, name="Ruby Mainspring", engine="temperbillow",
    eargs=dict(cell=9.4, pitch=4.8, jewel=9.0, peak_t=P_R, body=0.26, fine=0.16, lowcut=1.8, soft=0.9),
    seed=1076, lut=LUT_R, val=0.265,
    hues=None, hspan=0.055, satboost=0.40,
    macro=("rachis", dict(angle=0.3, lanes=6.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.52, mswing=1.5, **_KW),
    desc="Ruby tempering pools in eight heat tiers, small jewels glinting through the blue. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] structured dust (perlage) — paint is a
 # field; SPEC stays macro-led via specmacro (metric-blind dust cluster).
 "fcw_bronze_rivets": dict(huemode="macro", huecell=8.0, name="Bronze Rivet Plate", engine="perlage",
    eargs=dict(cell=8.6, swirl=4.6, peak_t=P_Z, body=0.74, fine=0.16, lowcut=1.2, soft=0.9),
    seed=1077, lut=LUT_Z, val=0.315,
    hues=None, hspan=0.055, satboost=0.60,
    macro=("domains", dict(cells=6, salt=1077)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.36, mswing=0.45, mfloor=10.0, ccboost=1.15, specmacro=0.85, **_KW),
    desc="Bronze perlage — overlapping polished circles row on row, swarf dust between. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] barleycorn lattice — lens engine turning.
 "fcw_brass_guilloche": dict(huecell=8.0, name="Brass Guilloché", engine="barleycorn",
    eargs=dict(cell=8.6, angle=0.3, peak_t=P_B, body=0.62, fine=0.16, lowcut=1.2, soft=0.9),
    seed=1078, lut=LUT_B, val=0.355,
    hues=None, hspan=0.055, satboost=0.62,
    macro=("bands", dict(angle=0.9, freq=3.0, warp=0.30)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.34, mswing=1.5, **_KW),
    desc="Brass barleycorn — thousands of tiny engine-turned grains in alternating rows. A FRACTURED CLOCKWORK finish."),
 # [SPB-FRACTURED-FIELD 2026-08-02] dendrite forest — patina dendrites.
 "fcw_verdigris_gears": dict(huecell=12.0, name="Verdigris Gears", engine="patinadendrite",
    eargs=dict(cell=9.0, iters=3, cot=5.6, peak_t=P_V, body=0.62, fine=0.16, lowcut=1.8, soft=0.9),
    seed=1079, lut=LUT_V, val=0.300,
    hues=None, hspan=0.055, satboost=0.54,
    macro=("bands", dict(angle=0.2, freq=2.5, warp=0.25)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(gray=0.40, mswing=1.4, **_KW),
    desc="Verdigris dendrites feathering dark over bright machined bronze grain. A FRACTURED CLOCKWORK finish."),
}

# weighted family palettes wired in (kept separate for readability)
for _fid, _pal in [
    ("fcw_brass_geartrain", BRASS), ("fcw_verdigris_rivets", VERDI),
    ("fcw_copper_escapement", COPPR), ("fcw_gold_guilloche", GOLDM),
    ("fcw_gunmetal_mainspring", GUNMT), ("fcw_bronze_scroll", BRONZ),
    ("fcw_brass_escapement", BRASS), ("fcw_ruby_guilloche", RUBYS),
    ("fcw_copper_rivets", COPPR), ("fcw_gold_mainspring", GOLDM),
    ("fcw_verdigris_scroll", VERDI), ("fcw_bronze_geartrain", BRONZ),
    ("fcw_brass_balance", BRASS), ("fcw_gunmetal_guilloche", GUNMT),
    ("fcw_copper_scroll", COPPR), ("fcw_gold_geartrain", GOLDM),
    ("fcw_ruby_mainspring", RUBYS), ("fcw_bronze_rivets", BRONZ),
    ("fcw_brass_guilloche", BRASS), ("fcw_verdigris_gears", VERDI),
]:
    for _row in (ROW1, ROW2, ROW3, ROW4):
        if _fid in _row:
            _row[_fid]["hues"] = [float(x) for x in
                                  _pal.split("[")[1].split("]")[0].split(",")]

GROUPS = {
    "BRASS & VERDIGRIS": ROW1,
    "BRONZE & RUBY": ROW2,
    "GUNMETAL & GOLD": ROW3,
    "JEWEL & PATINA": ROW4,
}

KIT = _ClockworkKit(engines=ENGINES, groups=GROUPS, tag="fractured-clockwork",
                    extra_macro={"dial": m_dial}, work=1024)

ALL = KIT.ALL
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
