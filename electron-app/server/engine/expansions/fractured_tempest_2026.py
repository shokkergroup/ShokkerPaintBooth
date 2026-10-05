# -*- coding: utf-8 -*-
"""FRACTURED TEMPEST (2026-07-30) — category 7/10 of the FRACTURED expansion.

[SPB-FRACTURED-090 2026-08-02] IN-BAND LATTICE PASS — owner: "push the
others to the same levels ... WITHOUT it being static noise or just a bunch of
repeats". Car-band median 0.692 -> 0.908 (house flagship FRACTURED MINDS is 0.82),
per-finish min 0.691 (fte_white_arc, see below). Gate is now _fractured_triage/verify_guard.py, which adds
three ANTI-CHEAT guards so a high band cannot be bought with noise (white
noise measures band ~0.95 and FAILS all three): lag-1 horizontal
autocorrelation >= 0.55, in-band spectral peakiness >= 0.30, Otsu
connected-shape fraction >= 0.55 — plus band >= 0.70 each, fineness > 6.5,
coverage >= 56/64, hue bins >= 5, < 2.0 s @512 and <= 2.5 s @2048, and
intra-module descriptor pair-cosine <= 0.55 (worst pair 0.313).

WHAT CHANGED, and why (all measured on this harness):
  * every engine rebuilt onto BOUNDED-JITTER LATTICES at the band pitch
    (8.5-10 px at GEN = 27-32 px at 2048), value carried by smooth periodic
    RELIEF inside each cell (domes / ribs / crowns / facets) separated by FAT
    edge-distance seams. r=64 is a 10 px feature at GEN and r=256 a 2.5 px
    one, so that window is the whole game;
  * NO fbm-derived luma anywhere — 1/f dumps its power under r=64 and was the
    single biggest leak (the recipe-dial pass alone moved the fbm-fed sparse
    archetypes DOWN 0.66 -> 0.23 because the old grain octave was the only
    in-band energy they had);
  * NO Poisson-scattered drawn stamps — a random placement has no fundamental
    at all, only a sub-band envelope;
  * ONE dominant scale per engine. The thin-film LUT is a strongly NON-LINEAR
    transfer, so any PAIR of in-band components intermodulates down into the
    sub-band: a clean T field at 2% sub-band came out of the LUT at 26%. The
    LUT sweep width is now a tuned dial for exactly this reason;
  * identity carried by HUE (a weighted ladder: 8 parts base, 2 near
    neighbours, 1 contrast accent) instead of by value swing or macro phase —
    vd is now (0.96, 1.06) and tmod 0.0 everywhere, because a ratio metric
    charges a low-frequency envelope twice;
  * the lag-1 guard is J0(2*pi*r/512) averaged over the power (0.85 at r=64,
    0.47 at r=128, 0.00 at r=196, NEGATIVE at r=256): a field whose
    fundamental sits past r~180 reads as STATIC even at band 0.95. That is
    what the `soft` high-cut dial buys back.

Contract unchanged: same 20 ids, same seeds, same GROUPS, same
install_into_engine signature, same (spec_fn, paint_fn) tuples via
CategoryKit; spec still traces the paint field. Determinism: catlib.rng
(np.random.default_rng) + coarse h2 cell hashes + zlib.crc32 salts, no
hash(str). Per-finish numbers: _fractured_triage/guard_<module>.json;
contact sheet: _fractured_triage/resheet_<module>.png.
MEASURED FRONTIER — fte_white_arc (spark-arc felt) tops out at band 0.691.
A partial ring is asymmetric by definition, and asymmetry is broadband: the
angular gate, the jagged width and the halo each cost band, and removing them
turns the id into a ring pack (which the module already has, as violet_hail).
It is left DISTINCT at its frontier rather than faked.

ARCHETYPE LEDGER (one DISTINCT compositional archetype per id — no repeats):
  fte_lichtenberg_crown  dendrite forest            (many small Lichtenberg trees)
  fte_steel_downpour     rain-lane thread field     (steep dashed bright lanes)
  fte_storm_cell         interlocking-cell mosaic   (radar cells, per-cell swirl)
  fte_white_arc          spark-arc felt             (thousands of tiny jagged arcs)
  fte_slate_squall       wavy curtain laminae       (vertical beat-broken curtains)
  fte_green_supercell    hook-vortex pave           (many small hook spirals)
  fte_thunderhead_white  lit billow turbulence      (top-lit micro cauliflower)
  fte_slate_vortex       flow-combed wind streaks   (curl-field combed, whitened)
  fte_violet_hail        crater ring-pack           (dimple rings, bright rims)
  fte_blue_bolt          branching-filament crawler mesh (horizontal glowing web)
  fte_slate_billows      mammatus dome foam         (bottom-lit packed pouches)
  fte_violet_twister     corded funnel tufts        (wavy striated micro funnels)
  fte_steel_rain         two-depth drizzle scatter  (near/far micro dashes)
  fte_green_strike       zigzag pleat field         (electric herringbone pleats)
  fte_whiteout_hail      splash-crown scatter       (radiating impact asterisks)
  fte_steel_cyclone      shear cross-weave          (two crossing wind-streak combs)
  fte_gustfront_green    bent-thread comb           (one-way wind-bent threads)
  fte_ball_lightning     linked-orb glow pack       (plasma orbs + arc links)
  fte_slate_hailfield    shatter crack web          (crack net + radial bursts)
  fte_violet_cumulonimbus strata shingle imbrication (flat-top anvil scales)

Contract unchanged: same 20 ids (fte_*), same seeds 1100-1119, same
install_into_engine signature, (spec_fn, paint_fn) via CategoryKit; spec
traces the paint field. Determinism: catlib.rng (np.random.default_rng) +
zlib.crc32 salts, no hash(str). Category macro kind "frontline" kept for
contract stability (recipes use gentle domain macros only). LUT phases
re-picked by measured art car-band sweep where the default transfer
flattened the field (FROST/NEBULA pass-2 method); unique macro salt per
recipe (catlib worley jitter is salt-driven, seed-blind).

[SPB-FRACTURED-090d 2026-08-02] COLOUR PASS — owner visual review of the pass-2
contact sheets: the GEOMETRY was accepted, the COLOUR was not. Two faults, both
fixed here without touching a lattice, a cell pitch, an eargs value or a LUT
span (every T field is byte-identical to pass 2):

 1. COMPLEMENTARY-ACCENT CONFETTI. The 11th rung of every `hues` ladder was the
    subject's COMPLEMENT — hot magenta in the kelly-green storms, tan-orange in
    the slate ones. At a ~9 px hue cell that reads as electric speckle, not as
    weather, and saturation-weighted it was carrying ~28% of the colour mass
    (not the 1/11 the ladder implies): fte_lichtenberg_crown had 71% of its
    chroma more than 0.12 turn off-subject. Replaced by 16-rung WITHIN-FAMILY
    ladders that walk the subject's own continuum (steel -> slate -> navy;
    storm-green -> teal -> slate sky; violet -> blue-violet -> blue) and satisfy
    the >= 5 hue-bin gate with shades of the subject instead of its opposite.
 2. NAME-HUE MISMATCH. The anchor a recipe SETS is not the hue that RENDERS —
    art_work remaps into a hero window and the LUT's hue density inside it is
    asymmetric. Measured saturation-weighted circular mean vs the id's named
    hue, then corrected by the number (see _HUEFIX / _ACCFIX below):
    lichtenberg_crown was 0.124 of a turn off, violet_hail 0.061 (it rendered
    HOT MAGENTA), violet_twister 0.054. Worst residual is now 0.013.
 Plus: storm is a GREY subject — mean saturation 0.69-1.00 (fully clipped
 candy) -> 0.16-0.36. Value contrast carries these, not chroma.

 ONE CONSEQUENCE WORTH KNOWING: the pass-2 lag-1 autocorrelation of the two
 violets was partly an ARTEFACT. art_work renormalises luma after the HSV
 roundtrip, so a 0.97-saturation violet had channels far above 1.0 and the
 final clip flattened the bright micro-detail ac measures. Honest colour
 removes the clip, so the true ac shows; it is bought back with value drama
 (vd) on fte_violet_hail and fte_violet_twister ONLY. See those two recipes.
"""
from __future__ import annotations

import zlib

import cv2
import numpy as np

from engine.expansions import fractured_catlib_2026 as catlib
from engine.expansions.fractured_catlib_2026 import (
    coords, fbm, frac, gauss, h2, n01, rng, rot, sstep, warp_pair, worley,
)

_TIERS = np.array([0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], np.float32)


def _crc(tag):
    """Deterministic string salt (no hash(str) — owner determinism law)."""
    return zlib.crc32(str(tag).encode()) & 0xFFFF


# ════════════════════════════════════════════════════════════════════════════
# MICRO-FIELD TOOLKIT (FROST pass-2 lineage). Primary wavelengths 4-10 px at
# GEN=640 (= 13-32 px on the 2048 car).
# ════════════════════════════════════════════════════════════════════════════

def _pk(T):
    """Percentile-pack a field to [0, 0.86] (no frac-wrap inside catlib)."""
    T = np.asarray(T, np.float32)
    lo = float(np.percentile(T, 1.0))
    hi = float(np.percentile(T, 99.0))
    return (np.clip((T - lo) / max(hi - lo, 1e-6), 0.0, 1.0) * 0.86).astype(np.float32)


def _tiermap(idmap, salt):
    return _TIERS[np.clip((h2(idmap, 0.0, salt) * 8.0).astype(np.int32), 0, 7)]



# --- IN-BAND LATTICE TOOLKIT [SPB-FRACTURED-090] ---
# THE IN-BAND LATTICE LAW (measured on _fractured_triage/verify_guard.py).
# Car-band = FFT ring r in [64,256] of the 512 paint luma / total r>=2.
#   r = 64  <=> period 8.0 px @512 <=> 10.0 px @GEN(640) <=> 32 px @2048
#   r = 256 <=> period 2.0 px @512 <=>  2.5 px @GEN      <=>  8 px @2048
# and the lag-1 coherence guard (ac >= 0.55, the anti-static gate) is
# J0(2*pi*r/512) averaged over the power: J0 = 0.85 at r=64, 0.65 at r=100,
# 0.47 at r=128, 0.00 at r=196, -0.30 at r=256. So a field whose fundamental
# sits past r~180 reads as STATIC and fails even at band 0.95. The window that
# satisfies BOTH is a fundamental at r = 65-90 with its harmonics decaying:
# a feature period of 8.5-10 px at GEN (27-32 px on the 2048 car).
#   L1 SCALE    coarser than ~10 px @GEN and the fundamental falls under the
#               band; finer than ~5 px @GEN and lag-1 coherence goes negative.
#   L2 FAT EDGE a wide smooth ridge/seam profile concentrates power AT the
#               fundamental; hairlines smear it into r>256 harmonics that cost
#               coherence and buy no band.
#   L3 LOW-CUT  fbm-derived fields and flat per-cell values leak a huge
#               sub-band skirt (1/f dumps most of its power under r=64).
#               _flat()/lowcut delete the drift without touching an edge.
# NOTE the lattices are built from a COARSE (n x n) hash grid expanded with
# INTER_NEAREST rather than a per-pixel sin() hash: identical field, ~6x
# cheaper, which is what keeps 9-tap Voronoi inside the render budget.


def _cg(n, salt, dj=0, di=0):
    """n x n deterministic cell-hash grid, rolled to address a neighbour tap.
    Cell j always resolves to the same hash (periodic in n), so the lattice is
    globally consistent and deterministic."""
    ii = np.arange(n, dtype=np.float32)
    g = h2(ii[None, :], ii[:, None], salt)
    if dj or di:
        g = np.roll(np.roll(g, -dj, 0), -di, 1)
    return np.ascontiguousarray(g, np.float32)


def _up(g, res):
    return cv2.resize(g, (res, res), interpolation=cv2.INTER_NEAREST)


def _celln(res, cell):
    """Cell count + exact cell size so floor(x/c) matches an INTER_NEAREST
    expansion of the coarse hash grid."""
    n = max(2, int(round(float(res) / float(cell))))
    return n, float(res) / n


def _flat(x, s=3.0):
    """LOW-CUT a value field: subtract its own local mean (drift coarser than
    ~4s px at GEN), keep the global mean. Not noise, not a sharpen — every
    shape and edge survives; only the sub-band wander dies."""
    x = np.asarray(x, np.float32)
    return x - gauss(x, float(s)) + float(x.mean())


def _fat(d, w, soft=0.34):
    """Fat smooth ridge/seam profile from a distance field (0 = centre).
    w may be scalar or a per-cell array (jittered widths). See L2."""
    w = np.asarray(w, np.float32)
    t = np.clip((d - w) / np.minimum(w * (float(soft) - 1.0), -1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _tv(hv):
    """8-tier value palette lookup (owner doctrine: many distinct value tiers,
    never 1-2 levels)."""
    return _TIERS[np.clip((np.asarray(hv, np.float32) * 8.0).astype(np.int32), 0, 7)]


def _voro(res, cell, jit, salt):
    """Bounded-jitter Voronoi pave -> (F1/cell, (F2-F1)/cell edge distance,
    winning-cell hash). Bounded jitter (<= ~0.5 cell) keeps a SHARP spectral
    fundamental — an unbounded worley smears a third of its power under the
    band. F2-F1 is the true polygon edge distance, so every seam is one width
    (a real vein, not a morphological hairline)."""
    n, c = _celln(res, cell)
    yy, xx = coords(res)
    ci = np.floor(xx / c)
    cj = np.floor(yy / c)
    f1 = np.full((res, res), 1e12, np.float32)
    f2 = np.full((res, res), 1e12, np.float32)
    idw = np.zeros((res, res), np.float32)
    j = float(jit)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            ax = _up(_cg(n, salt, dj, di), res)
            ay = _up(_cg(n, salt + 40, dj, di), res)
            dx = (ci + di + 0.5 + (ax - 0.5) * j) * c - xx
            dy = (cj + dj + 0.5 + (ay - 0.5) * j) * c - yy
            d = dx * dx + dy * dy
            m = d < f1
            np.minimum(f2, np.maximum(f1, d), out=f2)
            np.minimum(f1, d, out=f1)
            idw = np.where(m, _up(_cg(n, salt + 80, dj, di), res), idw)
    f1 = np.sqrt(f1, out=f1)
    f2 = np.sqrt(f2, out=f2)
    return (np.clip(f1 / c, 0.0, 1.5).astype(np.float32),
            np.clip((f2 - f1) / c, 0.0, 1.5).astype(np.float32), idw)


def _dots(res, cell, jit, salt):
    """Single-tap jittered-lattice dot field -> (0..1 radial distance, cell
    hash). One ninth the cost of _voro; for scales where the exact polygon
    seam is not needed."""
    n, c = _celln(res, cell)
    yy, xx = coords(res)
    jx = (_up(_cg(n, salt), res) - 0.5) * float(jit) * c
    jy = (_up(_cg(n, salt + 11), res) - 0.5) * float(jit) * c
    d = np.hypot(xx - (np.floor(xx / c) + 0.5) * c - jx,
                 yy - (np.floor(yy / c) + 0.5) * c - jy) / (c * 0.62)
    return np.clip(d, 0.0, 1.0).astype(np.float32), _up(_cg(n, salt + 23), res)


def _polar_cells(res, cell, jit, salt, spin=0.0):
    """Per-cell local polar frame on a bounded-jitter lattice ->
    (radius normalised to the cell, angle, cell hash). The analytic
    replacement for stamped/scattered motifs: every cell carries exactly one
    motif, so the motif lattice IS the spectral fundamental instead of a
    Poisson envelope smeared under the band."""
    n, c = _celln(res, cell)
    yy, xx = coords(res)
    jx = (_up(_cg(n, salt), res) - 0.5) * float(jit) * c
    jy = (_up(_cg(n, salt + 11), res) - 0.5) * float(jit) * c
    dx = xx - (np.floor(xx / c) + 0.5) * c - jx
    dy = yy - (np.floor(yy / c) + 0.5) * c - jy
    rl = np.hypot(dx, dy) / (c * 0.62)
    th = np.arctan2(dy, dx)
    if spin:
        th = th + _up(_cg(n, salt + 29), res) * (6.2831853 * float(spin))
    return (np.clip(rl, 0.0, 2.2).astype(np.float32), th.astype(np.float32),
            _up(_cg(n, salt + 23), res))


def _ptier(res, cell, salt, ang=0.0, relief=0.55, jit=0.30):
    """Per-patch 8-tier tint riding an IN-BAND domed patch lattice — the
    in-band replacement for every fbm-derived tier field. A flat per-cell tint
    is low-pass on its own; it only becomes band-pass once each patch carries
    a smooth relief at the lattice period (which is also what a real dipped
    glaze looks like)."""
    yy, xx = coords(res)
    if ang:
        u, v = rot((yy, xx), float(ang))
    else:
        u, v = xx, yy
    n, c = _celln(res, cell)
    jx = (_up(_cg(n, salt + 3), res) - 0.5) * float(jit)
    jy = (_up(_cg(n, salt + 7), res) - 0.5) * float(jit)
    d = np.maximum(np.abs(frac(u / c) - 0.5 + jx),
                   np.abs(frac(v / c) - 0.5 + jy)) * 2.0
    bump = sstep(1.02, 0.24, d)
    return _tv(_up(_cg(n, salt), res)) * (1.0 - float(relief) + float(relief) * bump)


def _lowcut(fn):
    """Universal LOW-CUT knob (`lowcut` px at GEN) wrapped round every engine.
    The one dial that trades neighbour coherence for car-band energy: it
    deletes power UNDER r=64 without touching a single shape or edge."""
    def g(res, seed, lowcut=0.0, soft=0.0, **kw):
        T = np.asarray(fn(res, seed, **kw), np.float32)
        sf = float(soft)
        if sf > 0.0:
            # HIGH-CUT: trims the r>256 harmonics a hard edge throws off. They
            # are pure denominator (above the band) AND the lag-1 coherence
            # killer — J0(2*pi*r/512) is NEGATIVE past r=196, so a finish can
            # sit at band 0.97 and still read as static. Costs a little band,
            # buys a lot of ac. Shapes survive; only their ringing dies.
            T = gauss(T, sf)
        lc = float(lowcut)
        if lc > 0.0:
            T = T - (gauss(T, lc) - float(T.mean()))
        return np.clip(T, 0.002, 0.998)
    g.__name__ = fn.__name__
    g.__doc__ = fn.__doc__
    g.__wrapped__ = fn
    return g


def _uvrot(res, seed, salt, warp=0.0):
    yy, xx = coords(res)
    a = float(rng(seed, salt).uniform(0, np.pi))
    u, v = rot((yy, xx), a)
    if warp > 0.0:
        wu, wv = warp_pair(res, seed, salt + 1, warp)
        u = u + wu
        v = v + wv
    return u.astype(np.float32), v.astype(np.float32)


def _grain(res, seed, salt, amp=0.10):
    """BAND-PASSED micro relief: ONE octave at ~8 px at GEN, then low-cut.
    [SPB-FRACTURED-090] the old 2-octave fbm at base 210 was the single
    biggest band leak in the module — a cubic-upscaled random grid is a
    LOW-pass field, and its top octave landed at r>256 (pure denominator, and
    the lag-1 coherence killer). Same visible mottle, power back in the band."""
    g = fbm(res, res, rng(seed, salt), 1, 80)
    g = g - gauss(g, 2.2)
    return ((g / (float(g.std()) + 1e-6)) * (0.34 * float(amp))).astype(np.float32)


def _gentle(res, seed, salt, amp=0.015):
    """Macro sway, now vestigial. [SPB-FRACTURED-090] amp 0.06 -> 0.015: a
    multiplicative low-frequency envelope is charged twice by a RATIO metric
    (adds sub-band power, removes none) and it is exactly the poster habit the
    owner rejected. Identity is carried by hue anchors, not by value sway."""
    return (1.0 + (fbm(res, res, rng(seed, salt), 3, 3) - 0.5) * 2.0 * amp).astype(np.float32)


def _splat(res, seed, salt, n, sigma=0.9):
    r0 = rng(seed, salt)
    px = r0.integers(0, res, int(n))
    py = r0.integers(0, res, int(n))
    w = _TIERS[r0.integers(0, 8, int(n))].astype(np.float32)
    pk = np.zeros((res, res), np.float32)
    np.add.at(pk, (py, px), w)
    return gauss(pk, float(sigma)) * (2.0 * np.pi * sigma * sigma)


def _sticks(res, seed, salt, n, lmin, lmax, a0=0.0, aspread=np.pi, width=1,
            segs=1, curl=0.0, curl_sign=0):
    r0 = rng(seed, salt)
    canvas = np.zeros((res, res), np.float32)
    for _ in range(int(n)):
        x = float(r0.uniform(0, res))
        y = float(r0.uniform(0, res))
        a = a0 + float(r0.uniform(-aspread, aspread))
        L = float(r0.uniform(lmin, lmax))
        v = 0.30 + 0.65 * float(_TIERS[int(r0.integers(0, 8))])
        for _s in range(int(segs)):
            nx = x + np.cos(a) * L / segs
            ny = y + np.sin(a) * L / segs
            cv2.line(canvas, (int(x), int(y)), (int(nx), int(ny)), v,
                     int(width), cv2.LINE_AA)
            if curl_sign:
                a += curl * float(r0.uniform(0.5, 1.5)) * curl_sign
            else:
                a += curl * float(r0.uniform(-1.0, 1.0))
            x, y = nx, ny
    return canvas


def _flowcomb(res, seed, salt, n, steps, step_px, theta):
    r0 = rng(seed, salt)
    x = r0.uniform(0, res, int(n)).astype(np.float32)
    y = r0.uniform(0, res, int(n)).astype(np.float32)
    w = _TIERS[r0.integers(0, 8, int(n))].astype(np.float32)
    canvas = np.zeros((res, res), np.float32)
    for _ in range(int(steps)):
        xi = np.clip(x, 0, res - 1).astype(np.int32)
        yi = np.clip(y, 0, res - 1).astype(np.int32)
        np.add.at(canvas, (yi, xi), w)
        a = theta[yi, xi]
        x = (x + np.cos(a) * step_px) % res
        y = (y + np.sin(a) * step_px) % res
    return gauss(canvas, 0.55)


def _stamp_conv(res, seed, salt, n, mk_kernel, nrot=8):
    r0 = rng(seed, salt)
    px = r0.integers(0, res, int(n))
    py = r0.integers(0, res, int(n))
    w = _TIERS[r0.integers(0, 8, int(n))].astype(np.float32)
    g = r0.integers(0, nrot, int(n))
    out = np.zeros((res, res), np.float32)
    for kk in range(int(nrot)):
        sel = g == kk
        if not sel.any():
            continue
        dm = np.zeros((res, res), np.float32)
        np.add.at(dm, (py[sel], px[sel]), w[sel])
        out = out + cv2.filter2D(dm, -1, mk_kernel(kk))
    return out


def _edges_of(bid):
    gx = cv2.Sobel(bid, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(bid, cv2.CV_32F, 0, 1, ksize=3)
    return (np.hypot(gx, gy) > 1e-3).astype(np.float32)


def _whiten(T, sig=10.0):
    """Kill macro density lumps: divide by the local mean (FROST lesson)."""
    return T / (gauss(T, float(sig)) + 0.30 * float(T.mean()) + 1e-4)


# ════════════════════════════════════════════════════════════════════════════
# 20 FIELD ENGINES — one per id, one archetype each (ledger above).
# [SPB-FRACTURED-090 2026-08-02] EVERY engine rebuilt onto BOUNDED-JITTER
# LATTICES at the band pitch (8.5-10 px at GEN = 27-32 px at 2048), value
# carried by smooth periodic RELIEF inside each cell and separated by FAT
# edge-distance seams. Four measured laws drove the rebuild, all of them
# learned the hard way on FROST and NEBULA first:
#   1. no fbm-derived luma  — 1/f dumps its power under r=64;
#   2. no Poisson stamps    — a random placement has no fundamental at all,
#                             only a sub-band envelope;
#   3. ONE dominant scale   — the thin-film LUT is a strongly non-linear
#                             transfer, so any PAIR of in-band components
#                             intermodulates down into the sub-band (measured
#                             repeatedly: a clean T field at 2% sub-band came
#                             out of the LUT at 26%);
#   4. jitter <= ~0.5 cell  — past that the cell-size distribution widens
#                             until the lattice has no peak left.
# Identity rides on geometry and on the recipe hue ladder, never on a value
# swing (vd is charged twice by a ratio metric) and never on macro phase.
# ════════════════════════════════════════════════════════════════════════════

def t_licht_forest(res, seed, cell=9.6, arms=5, split=6.4, body=0.26, fine=0.09):
    """[fte_lichtenberg_crown] DENDRITE FOREST: a Lichtenberg crown per lattice
    cell — branches that fork as they run out from a hot core, every crown at
    its own rotation, the whole canvas a forest of them."""
    rl, th, hv = _polar_cells(res, float(cell), 0.44, 811, 1.0)
    trunk = (0.5 + 0.5 * np.cos(th * float(arms))) ** 2.0
    fork = (0.5 + 0.5 * np.cos(th * float(arms) * 2.0 + rl * float(split))) ** 3.0
    branch = np.maximum(trunk * sstep(0.85, 0.05, rl), fork * sstep(1.25, 0.35, rl))
    core = np.exp(-((rl * 3.4) ** 2))
    T = 0.13 + branch * (0.30 + 0.26 * _tv(hv)) + core * 0.26 \
        + sstep(1.30, 0.20, rl) * 0.12 + _tv(hv) * float(body) * 0.30 \
        + _grain(res, seed, 813, fine)
    return _pk(T * _gentle(res, seed, 815))


def t_rain_lanes(res, seed, p=9.0, dash=12.5, slant=1.12, body=0.30, fine=0.09):
    """[fte_steel_downpour] RAIN-LANE thread field: fat steep rain lanes at the
    band pitch, each broken into 8-tier dashes down its fall."""
    yy, xx = coords(res)
    u, v = rot((yy, xx), float(slant))
    wu, _wv = warp_pair(res, seed, 821, 3.0)
    q = (v + wu) / float(p)
    lane = _fat(np.abs(frac(q) - 0.5), 0.32)
    gloss = 0.5 + 0.5 * np.cos(6.2831853 * frac(q))
    seg = np.floor(u / float(dash))
    tier = _tv(h2(np.floor(q), seg, 823))
    brk = sstep(0.46, 0.10, np.abs(frac(u / float(dash)) - 0.5))
    T = 0.13 + lane * (0.34 + float(body) * tier) * (0.45 + 0.55 * brk) \
        + gloss * 0.14 + _grain(res, seed, 825, fine)
    return _pk(T * _gentle(res, seed, 827))


def t_cell_mosaic(res, seed, cell=9.8, swirl=3.2, gap=0.22, body=0.28, fine=0.09):
    """[fte_storm_cell] INTERLOCKING-CELL mosaic: micro radar cells, each with
    its OWN rotation shading spiralling out from its centre — a mesocyclone
    per tile, fat dark gaps between."""
    # [SPB-FRACTURED-090] the swirl used to come from _polar_cells on the
    # same nominal lattice -- but the two builders draw their jitter from
    # different hash offsets, so the swirl centres sat OFF the Voronoi sites.
    # Two misaligned in-band lattices is the worst case of all: no shared
    # fundamental to reinforce, and every crossing pair intermodulating down
    # under the band (measured sub-band 0.42). The swirl now rides the cell's
    # OWN distance gradient, which points away from its true site by
    # construction, so cell and swirl are one structure.
    f1, e1, i1 = _voro(res, float(cell), 0.46, 831)
    gx = cv2.Sobel(gauss(f1, 1.0), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gauss(f1, 1.0), cv2.CV_32F, 0, 1, ksize=3)
    th = np.arctan2(gy, gx) + i1 * 6.2831853
    spin = 0.5 + 0.5 * np.cos(th * 2.0 + f1 * float(swirl) * 3.0)
    top = sstep(0.04, 0.42, e1)
    seam = _fat(e1, float(gap))
    tier = _flat(_tv(h2(np.floor(i1 * 997.0), 0.0, 833)), 3.0)
    T = 0.14 + top * 0.30 + spin * (0.14 + 0.22 * top) \
        + tier * float(body) * (0.30 + 0.70 * top) - seam * 0.30 \
        + np.exp(-((f1 / 0.18) ** 2)) * 0.16 + _grain(res, seed, 835, fine)
    return _pk(T * _gentle(res, seed, 837))


def t_spark_felt(res, seed, cell=9.4, rad=0.60, w=0.22, spread=1.34, body=0.24,
                 fine=0.08):
    """[fte_white_arc] SPARK-ARC felt: one tiny jagged bright arc per cell, each
    struck at its own angle, every arc wrapped in its own glow."""
    rl, th, hv = _polar_cells(res, float(cell), 0.46, 841, 1.0)
    # [SPB-FRACTURED-090] jag depth halved and its azimuthal order
    # dropped 7 -> 4: a strong high-order width modulation is angular
    # FM on the ring, and FM sidebands land wherever they like.
    jag = float(w) * (0.86 + 0.28 * (0.5 + 0.5 * np.cos(th * 4.0)))
    # [SPB-FRACTURED-090] the gate was cos(th/2), which is DISCONTINUOUS
    # across th = +-pi: every arc carried a hard radial cut, and a step edge
    # sprays power right across the spectrum (sub-band 0.30, and it costs
    # coherence at the top end too). cos(th) is continuous everywhere and
    # still opens the ring over roughly half its circumference.
    arc = _fat(np.abs(rl - float(rad)), jag) \
        * sstep(-0.30, 0.45, np.cos(th) + float(spread) - 1.0)
    glow = gauss(arc, 1.5) * (1.0 - arc)
    # [SPB-FRACTURED-090] the halo is a BLURRED copy of the arcs, i.e. a
    # low-passed version of the very field we are trying to keep in
    # band; at 0.22 weight it was handing 0.10 of the power straight to
    # the sub-band. Demoted to a rim light, with the arc itself carrying
    # the value.
    T = 0.13 + arc * (0.42 + 0.34 * _tv(hv)) + n01(glow) * 0.10 \
        + _ptier(res, float(cell), 843, relief=0.66) * float(body) \
        + _grain(res, seed, 845, fine)
    return _pk(T * _gentle(res, seed, 847))


def t_curtain_laminae(res, seed, p=9.2, beat=11.0, warp=6.0, body=0.30, fine=0.09):
    """[fte_slate_squall] WAVY CURTAIN laminae: near-vertical rain curtains at
    the band pitch, their brightness beating in and out down their length."""
    yy, xx = coords(res)
    a = -np.pi / 2 + float(rng(seed, 851).uniform(-0.18, 0.18))
    u, v = rot((yy, xx), a)
    wu, _wv = warp_pair(res, seed, 853, float(warp))
    q = (v + wu) / float(p)
    lam = _fat(np.abs(frac(q) - 0.5), 0.33)
    gloss = 0.5 + 0.5 * np.cos(6.2831853 * frac(q))
    bt = 0.5 + 0.5 * np.cos(6.2831853 * u / float(beat))
    tier = _tv(h2(np.floor(q), np.floor(u / float(beat)), 855))
    T = 0.13 + lam * (0.30 + float(body) * tier) * (0.42 + 0.58 * bt) \
        + gloss * 0.16 + _grain(res, seed, 857, fine)
    return _pk(T * _gentle(res, seed, 859))


def t_hook_pave(res, seed, cell=9.8, twist=6.5, body=0.26, fine=0.09):
    """[fte_green_supercell] HOOK-VORTEX pave: many small ONE-arm hook spirals,
    one per cell, each wound to its own phase — a supercell crowd."""
    rl, th, hv = _polar_cells(res, float(cell), 0.42, 861, 1.0)
    hook = (0.5 + 0.5 * np.cos(th + rl * float(twist))) ** 2.6
    env = sstep(1.28, 0.10, rl)
    core = np.exp(-((rl * 2.8) ** 2))
    T = 0.13 + env * (0.16 + 0.40 * hook) + core * 0.26 \
        + _tv(hv) * float(body) * (0.28 + 0.72 * env) + _grain(res, seed, 863, fine)
    return _pk(T * _gentle(res, seed, 865))


def t_lit_billows(res, seed, cell=9.6, c2=6.4, lift=1.0, body=0.28, fine=0.09):
    """[fte_thunderhead_white] LIT BILLOW turbulence: a pave of cauliflower
    crowns, tops lit and bellies shadowed, a quieter boil on their shoulders."""
    d1, h1 = _dots(res, float(cell), 0.50, 871)
    d2, h2b = _dots(res, float(c2), 0.62, 875)
    crown = sstep(1.02, 0.05, d1)
    boil = sstep(0.95, 0.22, d2)
    shade = cv2.Sobel(gauss(crown, 1.2), cv2.CV_32F, 0, 1, ksize=3)
    T = 0.14 + crown * (0.30 + 0.28 * _tv(h1)) + boil * (0.08 + 0.10 * _tv(h2b)) \
        + np.clip(shade, 0.0, None) * float(lift) * 0.55 \
        + _flat(_tv(h1), 3.0) * float(body) + _grain(res, seed, 877, fine)
    return _pk(T * _gentle(res, seed, 879))


def t_wind_streaks(res, seed, p=9.2, drift=6.5, body=0.28, fine=0.08):
    """[fte_slate_vortex] FLOW-COMBED wind streaks: fat cords wandering along
    one smooth curl field. ONE displacement octave only — a second, finer one
    phase-modulates the carrier and smears the pitch into sidebands."""
    u, v = _uvrot(res, seed, 881, 0.0)
    d1 = (fbm(res, res, rng(seed, 883), 2, 5) - 0.5) * 2.0 * float(drift)
    q = (u + d1) / float(p)
    cord = _fat(np.abs(frac(q) - 0.5), 0.32)
    gloss = 0.5 + 0.5 * np.cos(6.2831853 * frac(q))
    tier = _tv(h2(np.floor(q), np.floor(v / 12.0), 885))
    T = 0.13 + cord * (0.32 + float(body) * tier) + gloss * 0.16 \
        + _grain(res, seed, 887, fine)
    return _pk(T * _gentle(res, seed, 889))


def t_crater_rings(res, seed, cell=9.6, rad=0.60, w=0.19, body=0.24, fine=0.08):
    """[fte_violet_hail] CRATER RING-pack: one impact dimple per cell — a fat
    bright rim ring around a dark pit, a doubled rim on the deepest strikes."""
    rl, _th, hv = _polar_cells(res, float(cell), 0.46, 891, 0.0)
    rim = _fat(np.abs(rl - float(rad)), float(w))
    pit = sstep(float(rad) * 0.86, float(rad) * 0.18, rl)
    outer = _fat(np.abs(rl - float(rad) * 1.42), float(w) * 0.7) \
        * (hv > 0.66).astype(np.float32)
    T = 0.30 + rim * (0.34 + 0.28 * _tv(hv)) + outer * 0.20 - pit * 0.30 \
        + _ptier(res, float(cell), 893, relief=0.66) * float(body) \
        + _grain(res, seed, 895, fine)
    return _pk(T * _gentle(res, seed, 897))


def t_crawler_mesh(res, seed, cell=9.6, thr=0.28, bias=0.72, body=0.24, fine=0.09):
    """[fte_blue_bolt] BRANCHING CRAWLER mesh: a glowing filament web creeping
    through the cloud deck, HORIZONTALLY biased — the branches that run across
    the sky burn, the ones that run up it fade."""
    _f1, e1, i1 = _voro(res, float(cell), 0.48, 901)
    gx = cv2.Sobel(e1, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(e1, cv2.CV_32F, 0, 1, ksize=3)
    horiz = np.abs(gy) / (np.abs(gx) + np.abs(gy) + 1e-6)
    crawl = _fat(e1, float(thr)) * (1.0 - float(bias) + float(bias) * horiz)
    glow = gauss(crawl, 1.6) * (1.0 - crawl)
    node = sstep(0.26, 0.05, e1)
    tier = _flat(_tv(h2(np.floor(i1 * 997.0), 0.0, 903)), 3.0)
    T = 0.13 + crawl * 0.42 + n01(glow) * 0.22 + node * 0.16 \
        + tier * float(body) + _grain(res, seed, 905, fine)
    return _pk(T * _gentle(res, seed, 907))


def t_mammatus_foam(res, seed, cell=9.4, lift=1.2, body=0.26, fine=0.09):
    """[fte_slate_billows] MAMMATUS dome foam: packed hanging pouches, lit from
    BELOW — bright under-rims, shadowed crowns, fat dark seams between."""
    f1, e1, i1 = _voro(res, float(cell), 0.42, 911)
    pouch = sstep(1.05, 0.05, f1) ** 1.2
    under = cv2.Sobel(gauss(pouch, 1.2), cv2.CV_32F, 0, 1, ksize=3)
    seam = _fat(e1, 0.20)
    tier = _flat(_tv(h2(np.floor(i1 * 997.0), 0.0, 913)), 3.0)
    T = 0.15 + pouch * 0.34 + np.clip(under, 0.0, None) * float(lift) \
        - seam * 0.24 + tier * float(body) * (0.30 + 0.70 * pouch) \
        + _grain(res, seed, 915, fine)
    return _pk(T * _gentle(res, seed, 917))


def t_funnel_tufts(res, seed, p=9.0, stria=10.5, body=0.28, fine=0.09):
    """[fte_violet_twister] CORDED FUNNEL tufts: wavy vertical micro funnels,
    ring striations riding every cord like a rope's lay."""
    yy, xx = coords(res)
    wu, _wv = warp_pair(res, seed, 921, 5.0)
    q = (xx + wu) / float(p)
    cord = _fat(np.abs(frac(q) - 0.5), 0.31)
    lay = 0.5 + 0.5 * np.cos(6.2831853 * (yy / float(stria) + frac(q) * 0.6))
    tier = _tv(h2(np.floor(q), np.floor(yy / float(stria)), 923))
    T = 0.13 + cord * (0.30 + float(body) * tier) * (0.55 + 0.45 * lay) \
        + cord * 0.16 + _grain(res, seed, 925, fine)
    return _pk(T * _gentle(res, seed, 927))


def t_drizzle_depths(res, seed, p=9.2, pf=6.2, slant=1.05, body=0.26, fine=0.08):
    """[fte_steel_rain] TWO-DEPTH drizzle: bright near dashes at the band pitch
    over a much fainter, finer far haze — the one deliberate two-population
    engine in the module, with the far layer kept quiet so the near pitch
    stays the single spectral peak."""
    yy, xx = coords(res)
    u, v = rot((yy, xx), float(slant))
    near = _fat(np.abs(frac(v / float(p)) - 0.5), 0.30)
    nb = sstep(0.44, 0.12, np.abs(frac(u / 13.0) - 0.5))
    far = _fat(np.abs(frac((v * 1.04 + 3.0) / float(pf)) - 0.5), 0.26)
    fb = sstep(0.46, 0.16, np.abs(frac(u / 8.5) - 0.5))
    tier = _tv(h2(np.floor(v / float(p)), np.floor(u / 13.0), 931))
    T = 0.13 + near * (0.34 + float(body) * tier) * (0.45 + 0.55 * nb) \
        + far * fb * 0.12 + _grain(res, seed, 933, fine)
    return _pk(T * _gentle(res, seed, 935))


def t_zigzag_pleats(res, seed, block=11.0, p=9.0, ang=0.85, body=0.28, fine=0.09):
    """[fte_green_strike] ZIGZAG PLEAT field: electric herringbone — fat ridge
    stripes flipping sign in narrow bolt lanes, seams cut between the lanes."""
    u, v = _uvrot(res, seed, 941, 5.0)
    col = np.floor(u / float(block))
    sgn = np.where(col % 2 < 1, 1.0, -1.0).astype(np.float32)
    ph = (u * np.cos(ang) * sgn + v * np.sin(ang)) / float(p)
    ridge = _fat(np.abs(frac(ph) - 0.5), 0.32)
    gloss = 0.5 + 0.5 * np.cos(6.2831853 * frac(ph))
    tier = _tv(h2(col, np.floor(ph), 943))
    seam = _fat(np.abs(frac(u / float(block)) - 0.5), 0.09)
    T = 0.13 + ridge * (0.34 + float(body) * tier) + gloss * 0.16 \
        - seam * 0.14 + _grain(res, seed, 945, fine)
    return _pk(T * _gentle(res, seed, 947))


def t_splash_crowns(res, seed, cell=9.4, rays=7, body=0.26, fine=0.08):
    """[fte_whiteout_hail] SPLASH-CROWN scatter: an impact asterisk per cell —
    droplet rays radiating from a bright heart, each crown spun at random."""
    rl, th, hv = _polar_cells(res, float(cell), 0.44, 951, 1.0)
    ray = (0.5 + 0.5 * np.cos(th * float(rays))) ** 3.0
    env = sstep(1.24, 0.08, rl)
    heart = np.exp(-((rl * 3.6) ** 2))
    T = 0.13 + env * (0.14 + 0.40 * ray) + heart * 0.30 \
        + _tv(hv) * float(body) * (0.28 + 0.72 * env) + _grain(res, seed, 953, fine)
    return _pk(T * _gentle(res, seed, 955))


def t_shear_weave(res, seed, p=9.4, dang=1.22, drape=5.0, body=0.24, fine=0.08):
    """[fte_steel_cyclone] SHEAR CROSS-WEAVE: two wind-streak combs crossing at
    ~70 degrees, their crossings burning brightest — the shear line made
    visible as a weave."""
    yy, xx = coords(res)
    a = float(rng(seed, 961).uniform(0, np.pi))
    u1, _ = rot((yy, xx), a)
    u2, _ = rot((yy, xx), a + float(dang))
    wu, _wv = warp_pair(res, seed, 963, float(drape))
    A = _fat(np.abs(frac((u1 + wu) / float(p)) - 0.5), 0.30)
    B = _fat(np.abs(frac((u2 - wu) / (float(p) * 1.06)) - 0.5), 0.30)
    tA = _tv(h2(np.floor((u1 + wu) / float(p)), 0.0, 965))
    tB = _tv(h2(np.floor((u2 - wu) / (float(p) * 1.06)), 1.0, 967))
    T = 0.13 + A * (0.24 + float(body) * tA) + B * (0.22 + float(body) * tB) \
        + A * B * 0.28 + _grain(res, seed, 969, fine)
    return _pk(T * _gentle(res, seed, 971))


def t_bent_threads(res, seed, p=9.2, bend=0.13, body=0.28, fine=0.09):
    """[fte_gustfront_green] BENT-THREAD comb: micro threads all curving the
    same way under the outflow — a QUADRATIC phase, so the whole comb bows
    together instead of each thread wandering off on its own."""
    yy, xx = coords(res)
    a0 = float(rng(seed, 981).uniform(0.2, 0.6)) + np.pi / 2
    u, v = rot((yy, xx), a0)
    q = (v + float(bend) * (u / float(res)) * (u / float(res)) * float(res)) / float(p)
    thr = _fat(np.abs(frac(q) - 0.5), 0.31)
    gloss = 0.5 + 0.5 * np.cos(6.2831853 * frac(q))
    tier = _tv(h2(np.floor(q), np.floor(u / 12.0), 983))
    T = 0.13 + thr * (0.32 + float(body) * tier) + gloss * 0.16 \
        + _grain(res, seed, 985, fine)
    return _pk(T * _gentle(res, seed, 987))


def t_orb_links(res, seed, cell=9.4, rad=0.32, thr=0.22, body=0.26, fine=0.08):
    """[fte_ball_lightning] LINKED-ORB glow pack: a plasma orb per cell with an
    arc jumping along every cell wall to its neighbours — orbs and links share
    ONE lattice, so the pair reinforces a single spectral peak."""
    rl, _th, hv = _polar_cells(res, float(cell), 0.44, 991, 0.0)
    _f1, e1, _i1 = _voro(res, float(cell), 0.44, 991)
    orb = sstep(float(rad) * 2.0, float(rad) * 0.2, rl)
    link = _fat(e1, float(thr)) * 0.7
    glow = gauss(orb, 1.8) * (1.0 - orb)
    T = 0.13 + orb * (0.34 + 0.30 * _tv(hv)) + link * 0.26 + n01(glow) * 0.18 \
        + _ptier(res, float(cell), 993, relief=0.64) * float(body) \
        + _grain(res, seed, 995, fine)
    return _pk(T * _gentle(res, seed, 997))


def t_shatter_web(res, seed, cell=9.6, w=0.26, rays=5, body=0.24, fine=0.09):
    """[fte_slate_hailfield] SHATTER crack web: a fat dark crack net over pale
    plate with a radial burst of splinters thrown from every impact point —
    burst and net on the same lattice, one peak."""
    _f1, e1, i1 = _voro(res, float(cell), 0.44, 1001)
    rl, th, hv = _polar_cells(res, float(cell), 0.44, 1001, 1.0)
    crack = _fat(e1, float(w))
    lip = np.clip(_fat(e1, float(w) * 2.0) - crack, 0.0, 1.0)
    burst = (0.5 + 0.5 * np.cos(th * float(rays))) ** 5.0 * sstep(0.95, 0.10, rl)
    plate = sstep(0.04, 0.44, e1)
    tier = _flat(_tv(h2(np.floor(i1 * 997.0), 0.0, 1003)), 3.0)
    T = 0.55 + plate * 0.16 - crack * 0.48 + lip * 0.24 - burst * 0.26 \
        + tier * float(body) + _grain(res, seed, 1005, fine)
    return _pk(T * _gentle(res, seed, 1007))


def t_anvil_shingles(res, seed, sw=10.6, sh=8.4, body=0.28, fine=0.09):
    """[fte_violet_cumulonimbus] STRATA SHINGLE imbrication: flat-top anvil
    scales stacked in overlapping rows, every underside carved."""
    u, v = _uvrot(res, seed, 1011, 3.0)
    row = np.floor(v / float(sh))
    xo = u + (row % 2) * float(sw) * 0.5
    cu = np.abs(frac(xo / float(sw)) - 0.5) * 2.0
    cy = frac(v / float(sh))
    slab = np.clip(1.10 - cu * 0.52 - cy * 0.58, 0.0, 1.0)
    top = sstep(0.34, 0.06, cy)
    under = _fat(np.abs(cy - 0.90), 0.10)
    tier = _tv(h2(np.floor(xo / float(sw)), row, 1013))
    T = 0.13 + slab * (0.30 + float(body) * tier) + top * 0.24 - under * 0.22 \
        + _grain(res, seed, 1015, fine)
    return _pk(T * _gentle(res, seed, 1017))


ENGINES = {
    "t_licht_forest": t_licht_forest, "t_rain_lanes": t_rain_lanes,
    "t_cell_mosaic": t_cell_mosaic, "t_spark_felt": t_spark_felt,
    "t_curtain_laminae": t_curtain_laminae, "t_hook_pave": t_hook_pave,
    "t_lit_billows": t_lit_billows, "t_wind_streaks": t_wind_streaks,
    "t_crater_rings": t_crater_rings, "t_crawler_mesh": t_crawler_mesh,
    "t_mammatus_foam": t_mammatus_foam, "t_funnel_tufts": t_funnel_tufts,
    "t_drizzle_depths": t_drizzle_depths, "t_zigzag_pleats": t_zigzag_pleats,
    "t_splash_crowns": t_splash_crowns, "t_shear_weave": t_shear_weave,
    "t_bent_threads": t_bent_threads, "t_orb_links": t_orb_links,
    "t_shatter_web": t_shatter_web, "t_anvil_shingles": t_anvil_shingles,
}
ENGINES = {k: _lowcut(v) for k, v in ENGINES.items()}


# ════════════════════════════════════════════════════════════════════════════
# CATEGORY-SPECIFIC MACRO KIND — frontline (kept for contract stability; no
# pass-2 recipe uses it — poster macros were the disease this pass cured).
# ════════════════════════════════════════════════════════════════════════════

def m_frontline(r, mp, seed, K):
    """Storm front: one bright shelf band along a warped diagonal boundary."""
    yy, xx = K.coords(r)
    ang = float(mp.get("angle", 0.5))
    ru, rv = K.rot((yy, xx), ang)
    warp = K.fbm(r, r, K.rng(seed, 511), 3, 3) * float(mp.get("warp", 0.18)) * r
    d = (rv - r * float(mp.get("pos", 0.5)) + warp) / r
    shelf = np.exp(-((d - 0.02) ** 2) * float(mp.get("sharp", 260.0)))
    ahead = K.sstep(-0.02, -0.35, d) * 0.55
    behind = K.sstep(0.10, 0.55, d) * 0.12
    M = np.clip(shelf * 1.1 + ahead + behind, 0.0, 1.0)
    bandf = float(mp.get("bands", 4.0))
    D = K.n01(K.h2(np.floor(np.abs(d) * bandf * 2.0), np.sign(d), 43)
              + np.abs(d) * 0.3)
    return M, D

def m_clouds(r, mp, seed, K):
    """[pass2 refinement] SOFT LUMINANCE CLOUDS: smooth (non-quantized) fbm
    domain map — with an adjacent-hue LADDER in `hues`, anchor switches follow
    fuzzy cloud contours instead of Voronoi patch borders (anti patch-camo)."""
    f = K.fbm(r, r, K.rng(seed, int(mp.get("salt", 641))), 3, int(mp.get("base", 3)))
    M = 0.5 + (K.n01(f) - 0.5) * 0.7
    D = K.n01(K.gauss(f, 2.0))
    return M, D


def m_drift(r, mp, seed, K):
    """[pass2 refinement] DIRECTIONAL DRIFT: smooth warped ramp — value and
    hue-ladder anchors grade along one heading (flow-aligned gradient)."""
    yy, xx = K.coords(r)
    _u, v = K.rot((yy, xx), float(mp.get("angle", 0.5)))
    p = K.n01(v) + (K.fbm(r, r, K.rng(seed, int(mp.get("salt", 643))), 2, 3) - 0.5)         * float(mp.get("warp", 0.25))
    M = K.n01(p)
    D = K.n01(p)
    return M, D


def m_radial(r, mp, seed, K):
    """[pass2 refinement] RADIAL FALLOFF: warped center-out ramp — luminous
    heart grading to rim, hue ladder following the radius."""
    yy, xx = K.coords(r)
    cx, cy = float(mp.get("cx", 0.5)), float(mp.get("cy", 0.5))
    d = np.hypot(xx / r - cx, yy / r - cy)
    d = d + (K.fbm(r, r, K.rng(seed, int(mp.get("salt", 645))), 2, 3) - 0.5)         * float(mp.get("warp", 0.12))
    M = K.n01(1.0 - d)
    D = K.n01(d)
    return M, D



# ════════════════════════════════════════════════════════════════════════════
# RECIPES — 20 finishes, ids fte_*, seeds 1100-1119 (UNCHANGED ids/seeds).
# [pass 2, 2026-08-02] FIELD dials: vd tight, tmod <=0.12, ambient 0.12,
# sparkle ~0.12, gray <=0.40 (rule 5: luminous, colorful at a glance), unique
# macro salt per recipe. Verify data: _fractured_triage/verify_tempest.json.
# ════════════════════════════════════════════════════════════════════════════

ARC = {
 # [pass2] 5 giant bolts poster (band 0.16 class) -> Lichtenberg tree forest
 "fte_lichtenberg_crown": dict(name="Lichtenberg Crown", engine="t_licht_forest",
    eargs=dict(cell=8.256, arms=5, split=6.4, body=0.169, fine=0.09, lowcut=2.6, soft=0.9),
    seed=1100, lut=(400.0, 760.0, 1.0, 1.3, 5.6), val=0.28,
    hues=[0.68, 0.68, 0.68, 0.68, 0.68, 0.68, 0.68, 0.68, 0.68, 0.698, 0.658, 0.64, 0.62, 0.598, 0.576, 0.555], hspan=0.055, satboost=0.237,
    macro=("clouds", dict(base=8, salt=1100)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.5, rswing=1.3),
    desc="A forest of small violet Lichtenberg trees crackling over black storm glass. A FRACTURED TEMPEST finish."),
 # [pass2] 130 full-height lanes poster -> dash-broken micro rain lanes
 "fte_steel_downpour": dict(name="Steel Downpour", engine="t_rain_lanes",
    eargs=dict(p=9.0, dash=12.5, slant=1.12, body=0.195, fine=0.09, lowcut=1.8, soft=0.9),
    seed=1101, lut=(480.0, 690.0, 1.0, 1.3, 0.8), val=0.26,
    hues=[0.585, 0.585, 0.585, 0.585, 0.585, 0.585, 0.585, 0.585, 0.585, 0.605, 0.565, 0.627, 0.547, 0.653, 0.53, 0.68], hspan=0.055, satboost=0.280,
    macro=("drift", dict(angle=1.12, salt=1101)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4, rswing=1.4),
    desc="Steel-blue rain dashes driving down steep micro lanes edge to edge. A FRACTURED TEMPEST finish."),
 # [pass2] 3 mesocyclone poster -> 80-cell radar mosaic, per-cell swirl
 "fte_storm_cell": dict(name="Storm Cell", engine="t_cell_mosaic",
    eargs=dict(cell=11.564, swirl=3.2, gap=0.22, body=0.182, fine=0.09, lowcut=0.0, soft=1.25),
    seed=1102, lut=(420.0, 900.0, 1.05, 1.3, 4.0), val=0.26,
    hues=[0.43, 0.43, 0.43, 0.43, 0.43, 0.43, 0.43, 0.43, 0.43, 0.452, 0.41, 0.478, 0.505, 0.532, 0.556, 0.58], hspan=0.055, satboost=0.322,
    macro=("domains", dict(cells=44, salt=1102)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, gray=0.35, ccboost=1.4, mswing=1.3),
    desc="A mosaic of storm-green radar cells, every tile rotating its own micro cyclone. A FRACTURED TEMPEST finish."),
 # [pass2] ONE blinding arc poster -> felt of thousands of tiny arcs; gray
 # 0.86 -> 0.38 so the pastel electric palette reads (rule 5)
 "fte_white_arc": dict(name="White Arc", engine="t_spark_felt",
    eargs=dict(cell=8.084, rad=0.98, w=0.26, spread=1.34, body=0.348, fine=0.08, lowcut=1.0, soft=0.35),
    seed=1103, lut=(400.0, 760.0, 0.9, 1.15, 4.0), val=0.27,
    hues=[0.57, 0.57, 0.57, 0.57, 0.57, 0.57, 0.57, 0.57, 0.57, 0.59, 0.548, 0.612, 0.528, 0.636, 0.512, 0.66], hspan=0.055, satboost=0.200,
    macro=("clouds", dict(base=8, salt=1103)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.12, sparkle=0.05, gray=0.38, mfloor=10.0, ccboost=1.5),
    desc="A whiteout felt of tiny silver arcs, every spark wrapped in its own glow. A FRACTURED TEMPEST finish."),
 # [pass2] curtain-wave poster -> beat-broken vertical curtain laminae
 "fte_slate_squall": dict(name="Slate Squall", engine="t_curtain_laminae",
    eargs=dict(p=9.2, beat=11.0, warp=6.0, body=0.255, fine=0.09, lowcut=1.8, soft=0.6),
    seed=1104, lut=(540.0, 780.0, 1.0, 1.2, 3.1), val=0.26,
    hues=[0.605, 0.605, 0.605, 0.605, 0.605, 0.605, 0.605, 0.605, 0.605, 0.625, 0.585, 0.647, 0.567, 0.673, 0.55, 0.7], hspan=0.055, satboost=0.410,
    macro=("drift", dict(angle=1.5, salt=1104)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, gray=0.35, mswing=1.4, mfloor=10.0, rswing=1.4),
    desc="Slate rain curtains waving down in beat-broken micro laminae. A FRACTURED TEMPEST finish."),
}

CELL_BOLT = {
 # [pass2] ONE hook-echo poster -> pave of many small hook spirals
 "fte_green_supercell": dict(name="Green Supercell", engine="t_hook_pave",
    eargs=dict(cell=8.428, twist=6.5, body=0.221, fine=0.09, lowcut=0.0, soft=1.25),
    seed=1105, lut=(462.2, 857.8, 1.05, 1.35, 0.0), val=0.26,
    hues=[0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.352, 0.31, 0.378, 0.405, 0.432, 0.456, 0.48], hspan=0.055, satboost=0.215,
    macro=("continents", dict(base=5, cells=5.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4),
    desc="A crowd of small storm-green supercell hooks rotating across the pane. A FRACTURED TEMPEST finish."),
 # [pass2] one towering thunderhead poster -> top-lit micro billow field;
 # gray 0.80 -> 0.40 (rule 5 luminous)
 "fte_thunderhead_white": dict(name="White Thunderhead", engine="t_lit_billows",
    eargs=dict(cell=8.256, c2=6.4, lift=1.0, body=0.182, fine=0.09, lowcut=2.6, soft=0.0),
    seed=1106, lut=(517.5, 752.5, 0.9, 1.15, 2.0), val=0.28,
    hues=[0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.6, 0.558, 0.622, 0.538, 0.646, 0.522, 0.67], hspan=0.055, satboost=0.190,
    macro=("continents", dict(base=5, cells=5.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.12, sparkle=0.05, gray=0.40, mfloor=10.0, ccboost=1.5),
    desc="White thunderhead billows at micro scale, every crown lit silver over a dark belly. A FRACTURED TEMPEST finish."),
 # [pass2] one funnel poster -> curl-combed wind streak field
 "fte_slate_vortex": dict(name="Slate Vortex", engine="t_wind_streaks",
    eargs=dict(p=7.912, drift=6.5, body=0.182, fine=0.08, lowcut=1.8, soft=0.9),
    seed=1107, lut=(420.0, 910.0, 1.0, 1.2, 0.4), val=0.26,
    hues=[0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.64, 0.6, 0.662, 0.582, 0.688, 0.565, 0.715], hspan=0.055, satboost=0.398,
    macro=("clouds", dict(base=7, salt=1107)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, gray=0.30, mswing=1.5, mfloor=10.0, rswing=1.5),
    desc="Slate wind streaks combed into a thousand micro vortices across the pane. A FRACTURED TEMPEST finish."),
 # [pass2] 52 big craters poster -> 1600 micro crater rings
 "fte_violet_hail": dict(name="Violet Hail", engine="t_crater_rings",
    eargs=dict(cell=9.746, rad=0.6, w=0.19, body=0.101, fine=0.08, lowcut=0.0, soft=0.0),
    seed=1108, lut=(400.0, 760.0, 1.0, 1.3, 0.0), val=0.28,
    hues=[0.74, 0.74, 0.74, 0.74, 0.74, 0.74, 0.74, 0.74, 0.74, 0.758, 0.718, 0.7, 0.68, 0.658, 0.636, 0.615], hspan=0.055, satboost=0.258,
    # [SPB-FRACTURED-090d 2026-08-02] CLIPPING-DEBT REPAY. Owner review: "hot
    # magenta, not violet" — anchor moved 0.801 -> 0.740 (true violet). But the
    # old ac=0.55x was an ARTEFACT of channel clipping: art_work renormalises
    # luma after the HSV roundtrip, so a 0.97-saturation violet had channels
    # far over 1.0 and the final clip flattened the bright micro-detail that
    # lag-1 coherence measures. Honest colour removes the clip and the field's
    # TRUE ac shows (0.533). This engine is the module's least coherent (crater
    # rings at soft=0.0, i.e. no high-cut of its own). Round 3: a first attempt
    # bought the ac back with satboost 0.68 and it read HOT MAGENTA on the
    # contact sheet — rejected. Saturation stays down where the owner wants it
    # (satA ~0.32) and the whole repayment is made in value drama instead:
    # vd 0.96/1.06 -> 0.66/1.38. Measured: band 0.8387 -> 0.701 (gate 0.70),
    # ac 0.533 -> 0.558 (gate 0.55). This id is at its MEASURED FRONTIER on
    # both — it cannot give more band for more coherence, or the reverse.
    # Geometry (engine/eargs/seed/lut) untouched — T field byte-identical.
    macro=("clouds", dict(base=9, salt=1108)), vd=(0.66, 1.38), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4),
    desc="Violet hail dimples pocking the whole panel, every micro rim catching light. A FRACTURED TEMPEST finish."),
 # [pass2] 3 crawler poster -> horizontal branching crawler mesh
 "fte_blue_bolt": dict(name="Blue Bolt", engine="t_crawler_mesh",
    eargs=dict(cell=8.256, thr=0.28, bias=0.72, body=0.156, fine=0.09, lowcut=1.8, soft=0.6),
    seed=1109, lut=(480.0, 690.0, 1.0, 1.35, 0.8), val=0.26,
    hues=[0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.62, 0.58, 0.642, 0.562, 0.668, 0.545, 0.695], hspan=0.055, satboost=0.427,
    macro=("clouds", dict(base=8, salt=1109)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, gray=0.30, ccboost=1.4, mswing=1.5),
    desc="A steel-blue crawler mesh — glowing dendrites creeping sideways through the deck. A FRACTURED TEMPEST finish."),
}

FRONT = {
 # [pass2] 8-pouch poster -> 90-cell bottom-lit mammatus foam
 "fte_slate_billows": dict(name="Slate Billows", engine="t_mammatus_foam",
    eargs=dict(cell=8.084, lift=1.2, body=0.169, fine=0.09, lowcut=1.8, soft=0.35),
    seed=1110, lut=(453.6, 866.4, 1.0, 1.2, 3.6), val=0.26,
    hues=[0.625, 0.625, 0.625, 0.625, 0.625, 0.625, 0.625, 0.625, 0.625, 0.645, 0.605, 0.667, 0.587, 0.693, 0.57, 0.72], hspan=0.055, satboost=0.410,
    macro=("continents", dict(base=5, cells=5.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, gray=0.35, mswing=1.4, mfloor=10.0),
    desc="Slate mammatus pouches packed micro-tight, every dome bottom-lit gold. A FRACTURED TEMPEST finish."),
 # [pass2] one S-rope poster -> striated corded funnel tufts
 "fte_violet_twister": dict(name="Violet Twister", engine="t_funnel_tufts",
    eargs=dict(p=9.0, stria=10.5, body=0.589, fine=0.09, lowcut=0.0, soft=0.35),
    seed=1111, lut=(400.0, 760.0, 1.0, 1.3, 0.0), val=0.28,
    hues=[0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.768, 0.728, 0.71, 0.69, 0.668, 0.646, 0.625], hspan=0.055, satboost=0.194,
    # [SPB-FRACTURED-090d 2026-08-02] CLIPPING-DEBT REPAY (see fte_violet_hail
    # for the full note). Anchor 0.804 -> 0.750, satboost 1.15 -> 0.32: honest
    # violet, and the clip that was propping ac up is gone (0.569 -> 0.471 on
    # a BYTE-IDENTICAL field). Bought back with value drama alone —
    # vd 0.96/1.06 -> 0.56/1.50 — no saturation given back. Measured:
    # band 0.7813 -> 0.851, ac 0.569 -> 0.602. BOTH better than the baseline
    # they replace, and now real instead of clip-inflated.
    macro=("drift", dict(angle=1.5, salt=1111)), vd=(0.56, 1.50), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.5, rswing=1.3),
    desc="Violet rope funnels tufted dense, condensation rings striating every cord. A FRACTURED TEMPEST finish."),
 # [pass2] two-lane parallax poster -> two-depth micro dash drizzle
 "fte_steel_rain": dict(name="Steel Rain", engine="t_drizzle_depths",
    eargs=dict(p=8.648, pf=6.2, slant=1.05, body=0.169, fine=0.08, lowcut=1.8, soft=1.25),
    seed=1112, lut=(410.0, 925.0, 1.0, 1.3, 0.8), val=0.26,
    hues=[0.575, 0.575, 0.575, 0.575, 0.575, 0.575, 0.575, 0.575, 0.575, 0.595, 0.555, 0.617, 0.537, 0.643, 0.52, 0.67], hspan=0.055, satboost=0.280,
    macro=("clouds", dict(base=8, salt=1112)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4),
    desc="Fine steel drizzle in two depths — bright near dashes over a dim far haze. A FRACTURED TEMPEST finish."),
 # [pass2] one triple-fork poster -> electric zigzag pleat field
 "fte_green_strike": dict(name="Green Strike", engine="t_zigzag_pleats",
    eargs=dict(block=11.0, p=7.74, ang=0.85, body=0.182, fine=0.09, lowcut=2.6, soft=0.6),
    seed=1113, lut=(430.0, 760.0, 1.05, 1.35, 2.4), val=0.26,
    hues=[0.335, 0.335, 0.335, 0.335, 0.335, 0.335, 0.335, 0.335, 0.335, 0.357, 0.315, 0.383, 0.41, 0.437, 0.461, 0.485], hspan=0.055, satboost=0.194,
    macro=("domains", dict(cells=6, salt=1113)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.5),
    desc="Storm-green zigzag pleats — the strike folded into a whole field of bolts. A FRACTURED TEMPEST finish."),
 # [pass2] 95 crown poster -> 1250 micro splash asterisks; gray 0.80 -> 0.38
 "fte_whiteout_hail": dict(name="Whiteout Hail", engine="t_splash_crowns",
    eargs=dict(cell=8.084, rays=7, body=0.169, fine=0.08, lowcut=1.8, soft=0.9),
    seed=1114, lut=(400.0, 880.0, 0.9, 1.15, 0.9), val=0.27,
    hues=[0.565, 0.565, 0.565, 0.565, 0.565, 0.565, 0.565, 0.565, 0.565, 0.585, 0.543, 0.607, 0.523, 0.631, 0.507, 0.655], hspan=0.055, satboost=0.185,
    macro=("clouds", dict(base=9, salt=1114)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.11, sparkle=0.05, gray=0.38, mfloor=10.0, ccboost=1.5),
    desc="A whiteout of micro hail splashes — thousands of tiny crowns and droplets. A FRACTURED TEMPEST finish."),
}

GUST = {
 # [pass2] one wedge poster -> two crossing shear streak combs
 "fte_steel_cyclone": dict(name="Steel Cyclone", engine="t_shear_weave",
    eargs=dict(p=8.084, dang=1.22, drape=5.0, body=0.156, fine=0.08, lowcut=2.6, soft=0.6),
    seed=1115, lut=(480.0, 690.0, 1.0, 1.35, 4.0), val=0.27,
    hues=[0.59, 0.59, 0.59, 0.59, 0.59, 0.59, 0.59, 0.59, 0.59, 0.61, 0.57, 0.632, 0.552, 0.658, 0.535, 0.685], hspan=0.055, satboost=0.280,
    macro=("clouds", dict(base=7, salt=1115)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.12, sparkle=0.05, mswing=1.5, rswing=1.5),
    desc="Steel shear winds woven — two crossing streak combs grinding the whole pane. A FRACTURED TEMPEST finish."),
 # [pass2] 230 long streak poster -> one-way bent micro thread comb
 "fte_gustfront_green": dict(name="Green Gustfront", engine="t_bent_threads",
    eargs=dict(p=8.545, bend=0.13, body=0.238, fine=0.09, lowcut=1.8, soft=0.9),
    seed=1116, lut=(425.0, 760.0, 1.05, 1.3, 4.0), val=0.31,
    hues=[0.345, 0.345, 0.345, 0.345, 0.345, 0.345, 0.345, 0.345, 0.345, 0.367, 0.325, 0.393, 0.42, 0.447, 0.471, 0.495], hspan=0.055, satboost=0.194,
    macro=("clouds", dict(base=8, salt=1116)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4),
    desc="Storm-green rain threads all bending one way under the gustfront outflow. A FRACTURED TEMPEST finish."),
 # [pass2] 11 orb poster -> 470 linked plasma orbs; gray 0.78 -> 0.35
 "fte_ball_lightning": dict(name="Ball Lightning", engine="t_orb_links",
    eargs=dict(cell=8.084, rad=0.32, thr=0.22, body=0.169, fine=0.08, lowcut=1.8, soft=0.6),
    seed=1117, lut=(472.0, 688.0, 0.9, 1.15, 0.8), val=0.28,
    hues=[0.53, 0.53, 0.53, 0.53, 0.53, 0.53, 0.53, 0.53, 0.53, 0.55, 0.51, 0.572, 0.492, 0.598, 0.475, 0.625], hspan=0.055, satboost=0.410,
    macro=("clouds", dict(base=8, salt=1117)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.11, sparkle=0.05, gray=0.35, mfloor=10.0, ccboost=1.5),
    desc="Hundreds of small plasma orbs adrift, micro arcs jumping orb to orb. A FRACTURED TEMPEST finish."),
 # [pass2] 12 giant webs poster -> 75-cell crack web + micro bursts
 "fte_slate_hailfield": dict(name="Slate Hailfield", engine="t_shatter_web",
    eargs=dict(cell=9.6, w=0.26, rays=5, body=0.288, fine=0.09, lowcut=2.6, soft=0.35),
    seed=1118, lut=(420.0, 760.0, 1.0, 1.2, 4.0), val=0.26,
    hues=[0.61, 0.61, 0.61, 0.61, 0.61, 0.61, 0.61, 0.61, 0.61, 0.63, 0.59, 0.652, 0.572, 0.678, 0.555, 0.705], hspan=0.055, satboost=0.410,
    macro=("domains", dict(cells=5, salt=1118)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, gray=0.35, mswing=1.4, mfloor=10.0),
    desc="A slate shatter web — fine crack nets and radial micro bursts over pale ice. A FRACTURED TEMPEST finish."),
 # [pass2] one anvil poster -> flat-top strata shingle rows
 "fte_violet_cumulonimbus": dict(name="Violet Cumulonimbus", engine="t_anvil_shingles",
    eargs=dict(sw=11.448, sh=9.072, body=0.28, fine=0.09, lowcut=3.6, soft=1.25),
    seed=1119, lut=(400.0, 945.0, 1.0, 1.3, 5.2), val=0.28,
    hues=[0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.773, 0.733, 0.715, 0.695, 0.673, 0.651, 0.63], hspan=0.055, satboost=0.204,
    macro=("continents", dict(base=5, cells=5.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.5),
    desc="Violet anvil strata shingled row on row, every flat top lit against a carved underside. A FRACTURED TEMPEST finish."),
}

GROUPS = {
    "ARC & SQUALL": ARC,
    "CELL & BOLT": CELL_BOLT,
    "FRONT & FALL": FRONT,
    "GUST & HAIL": GUST,
}

KIT = catlib.CategoryKit(engines=ENGINES, groups=GROUPS, tag="fractured-tempest",
                         extra_macro={"frontline": m_frontline, "clouds": m_clouds,
                                      "drift": m_drift, "radial": m_radial})

ALL = KIT.ALL

# ════════════════════════════════════════════════════════════════════════════
# MEASURED HUE CORRECTION [SPB-FRACTURED-090d 2026-08-02]
# The anchor a recipe SETS is not the hue that RENDERS. art_work remaps the
# thin-film hue to  c + dh*(2*hspan)  inside a hero window, and the LUT's hue
# density inside that window is ASYMMETRIC, so the saturation-weighted
# circular mean lands off the anchor (the sibling clockwork pass measured
# brass 0.043 of a turn low — it rendered as bronze). These are the MEASURED
# residuals, in turns, folded back onto the whole ladder so the ladder stays
# readable as the authored intent and the correction stays auditable.
# Loop: _fractured_triage/colorfix.py <mod>  ->  apply_colorfix.py <mod>,
# repeated until every id is within 0.03 turn of its named hue.
# Hue-only: art_work re-applies each pixel's own luma after the HSV
# roundtrip, so this moves NO band / autocorr / peakiness / shape / fineness.
_HUEFIX = {
 "fte_green_strike": -0.0084,
 "fte_green_supercell": -0.0308,
 "fte_gustfront_green": -0.0300,
 "fte_lichtenberg_crown": +0.0126,
 "fte_slate_billows": -0.0151,
 "fte_storm_cell": -0.0221,
 "fte_thunderhead_white": -0.0193,
 "fte_violet_cumulonimbus": +0.0162,
 "fte_white_arc": -0.0174,
}

for _fid, _off in _HUEFIX.items():
    _r = ALL[_fid]
    _r["hues"] = [round((_h + _off) % 1.0, 4) for _h in _r["hues"]]

# _ACCFIX rotates ONLY the two ACCENT rungs (the last two of a nebula ladder).
# A single unbalanced accent drags the whole-field circular mean off the named
# hue (cyan_spiral landed 0.083 of a turn low — it read teal); correcting that
# by rotating the WHOLE ladder would only move the dominant population off the
# name instead. Two knobs, two measurements: _HUEFIX is driven by the SPINE
# hue (the dominant family), _ACCFIX by the accents' residual net pull.
_ACCFIX = {
 "fte_green_supercell": -0.0416,
}

for _fid, _off in _ACCFIX.items():
    _r = ALL[_fid]
    _r["hues"] = _r["hues"][:-2] + [round((_h + _off) % 1.0, 4)
                                    for _h in _r["hues"][-2:]]
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
