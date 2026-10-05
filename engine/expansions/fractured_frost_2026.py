# -*- coding: utf-8 -*-
"""FRACTURED FROST (2026-07-30) — category 2/10 of the FRACTURED expansion.

[SPB-FRACTURED-090 2026-08-02] IN-BAND LATTICE PASS — owner: "push the
others to the same levels ... WITHOUT it being static noise or just a bunch of
repeats". Car-band median 0.689 -> 0.894 (house flagship FRACTURED MINDS is 0.82),
per-finish min 0.732 (all 20 pass). Gate is now _fractured_triage/verify_guard.py, which adds
three ANTI-CHEAT guards so a high band cannot be bought with noise (white
noise measures band ~0.95 and FAILS all three): lag-1 horizontal
autocorrelation >= 0.55, in-band spectral peakiness >= 0.30, Otsu
connected-shape fraction >= 0.55 — plus band >= 0.70 each, fineness > 6.5,
coverage >= 56/64, hue bins >= 5, < 2.0 s @512 and <= 2.5 s @2048, and
intra-module descriptor pair-cosine <= 0.55 (worst pair 0.155).

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

ARCHETYPE LEDGER (one DISTINCT compositional archetype per id — no repeats):
  ffr_window_fern     dendrite-fern forest      (many micro ferns over crystal mottle)
  ffr_cyan_frond      directional-lamina comb   (parallel feather laminae + serration)
  ffr_glacier_fern    branching-filament mesh   (curved rime filaments criss-crossing)
  ffr_violet_rime     flow-combed strands       (curl-field advected rime streaks)
  ffr_steel_flurry    granular multi-scale scatter (3-size wind-smeared flake grains)
  ffr_silver_dendrite star-lattice              (jittered lattice of tiny stellar flakes)
  ffr_diamond_dust    dust-with-structure       (glint powder + vertical micro-pillars)
  ffr_violet_sectored plate-mosaic pave         (hex micro-plates, sector wedges)
  ffr_cyan_fissure    crackle-net               (2-scale crack web, lit lips)
  ffr_whiteout_rift   chevron micro-pleats      (herringbone drift pleats)
  ffr_violet_chasm    reaction-diffusion labyrinth (frost-crazing maze channels)
  ffr_blue_serac      interlocking-cell mosaic  (worley blocks, per-cell facet ramps)
  ffr_hoarfrost_white spiculed-needle felt      (dense short needle spicules)
  ffr_silver_hoar     woven-cross comb          (two dashed needle families weaving)
  ffr_cyan_frostbloom concentric-micro-ripple carpet (interfering bloom ripples)
  ffr_ice_needles     thread-drift              (long acicular threads, one heading)
  ffr_violet_trapped  bubble-foam pack          (packed micro bubble domes)
  ffr_steel_bubbles   ring-pack                 (dense open annuli, glinting rims)
  ffr_cyan_veil       billow moire              (interfering micro sine veils)
  ffr_snowdrift_ice   stacked-scale imbrication (overlapping sastrugi scales)

Contract unchanged: same 20 ids (ffr_*), same seeds 1020-1039, same
install_into_engine signature, same (spec_fn, paint_fn) tuples via
CategoryKit; spec traces the paint field (catlib carve). Determinism:
np.random.default_rng via catlib.rng + zlib.crc32 salts, no hash(str).
Category macro kind "starburst" kept (contract stability; recipes now use
gentle domain macros only).

[SPB-FRACTURED-090d 2026-08-02] COLOUR PASS — owner visual review: geometry
accepted, colour not. Same two faults as the sibling TEMPEST module, fixed with
no change to any lattice / cell pitch / eargs / LUT span (T fields
byte-identical): the complementary 11th ladder rung (magenta and tan-orange
accents in an ICE module) is gone, replaced by 16-rung within-family ladders
(aqua -> pale cyan -> glacier -> deep blue shadow -> faint violet), and every
anchor is now corrected by the MEASURED saturation-weighted circular mean of
what actually renders (_HUEFIX / _ACCFIX below; worst residual 0.013 turn,
was 0.072 on ffr_silver_dendrite). Ice is a WHITE subject: mean saturation
0.70-1.00 -> 0.17-0.35, with the white/silver/snow ids at 0.17-0.19 (their
names are a saturation statement, not a hue one).

The frost cyans additionally needed an ASYMMETRIC fan: a symmetric one around a
0.49 anchor puts base - fan - hspan = 0.38 on the canvas, which is GRASS. The
ICE fan is upward-biased and runs a tighter 0.042 hue window, so the family
never reaches green. ffr_violet_trapped pays a clipping debt in vd — see there.
"""
from __future__ import annotations

import zlib

import cv2
import numpy as np

from engine.expansions import fractured_catlib_2026 as catlib
from engine.expansions.fractured_catlib_2026 import (
    coords, fbm, frac, gauss, h2, n01, rng, rot, sstep, warp_pair, worley,
)

# 8-tier per-feature brightness palette (owner doctrine: many distinct values)
_TIERS = np.array([0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], np.float32)


def _crc(tag):
    """Deterministic string salt (no hash(str) — owner determinism law)."""
    return zlib.crc32(str(tag).encode()) & 0xFFFF


# ════════════════════════════════════════════════════════════════════════════
# MICRO-FIELD TOOLKIT — every engine builds a dense homogeneous field from
# these. Primary wavelengths 4-10 px at GEN=640 (= 13-32 px on the 2048 car).
# ════════════════════════════════════════════════════════════════════════════

def _pk(T):
    """Percentile-pack a field to [0, 0.86] (no frac-wrap inside catlib)."""
    T = np.asarray(T, np.float32)
    lo = float(np.percentile(T, 1.0))
    hi = float(np.percentile(T, 99.0))
    return (np.clip((T - lo) / max(hi - lo, 1e-6), 0.0, 1.0) * 0.86).astype(np.float32)


def _tiermap(idmap, salt):
    """Per-cell 8-tier brightness from a cell-id map."""
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
    """n tiered gaussian micro-dots, vectorized scatter."""
    r0 = rng(seed, salt)
    px = r0.integers(0, res, int(n))
    py = r0.integers(0, res, int(n))
    w = _TIERS[r0.integers(0, 8, int(n))].astype(np.float32)
    pk = np.zeros((res, res), np.float32)
    np.add.at(pk, (py, px), w)
    return gauss(pk, float(sigma)) * (2.0 * np.pi * sigma * sigma)


def _sticks(res, seed, salt, n, lmin, lmax, a0=0.0, aspread=np.pi, width=1,
            segs=1, curl=0.0):
    """n tiered line strokes (needles / threads / filaments)."""
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
            a += curl * float(r0.uniform(0.5, 1.5))
            x, y = nx, ny
    return canvas


def _flowcomb(res, seed, salt, n, steps, step_px, theta):
    """Vectorized particle combing along an angle field -> fine strands."""
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


def _turing(res, seed, salt, s1, s2, iters=9, base=200):
    """Blur-difference reaction-diffusion labyrinth (wavelength ~2.5*s2)."""
    x = fbm(res, res, rng(seed, salt), 2, int(base)).astype(np.float32)
    for _ in range(int(iters)):
        x = x + (gauss(x, s1) - gauss(x, s2)) * 1.6
        x = np.clip(x, -1.5, 2.5)
    return n01(x)


def _edges_of(bid):
    gx = cv2.Sobel(bid, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(bid, cv2.CV_32F, 0, 1, ksize=3)
    return (np.hypot(gx, gy) > 1e-3).astype(np.float32)


def _star_kernel(rad, arms, rot0, sharp=6.0):
    k = int(rad) * 2 + 1
    yy, xx = np.mgrid[0:k, 0:k].astype(np.float32) - rad
    rr = np.hypot(xx, yy) / max(rad, 1.0)
    th = np.arctan2(yy, xx) + rot0
    arm = (0.5 + 0.5 * np.cos(th * arms)) ** sharp
    env = np.clip(1.0 - rr, 0.0, 1.0) ** 0.8
    core = np.exp(-((rr * 3.0) ** 2))
    return (arm * env + core * 0.7).astype(np.float32)


# ════════════════════════════════════════════════════════════════════════════
# 20 FIELD ENGINES — one per id, one archetype each (ledger above).
# [SPB-FRACTURED-090 2026-08-02] EVERY engine rebuilt onto BOUNDED-JITTER
# LATTICES at the band pitch (8.5-10 px at GEN = 27-32 px at 2048), value
# carried by smooth periodic RELIEF inside each cell (domes / ribs / crowns /
# facets) separated by FAT edge-distance seams. No engine derives its luma
# from an fbm field any more: 1/f dumps its power under r=64 and was the
# single biggest band leak (measured, this module: the dial pass alone moved
# the sparse fbm-fed archetypes DOWN 0.66 -> 0.23 because the old grain octave
# was the only in-band energy they had). Drawn cv2 motifs are gone too — their
# Poisson placement is a sub-band envelope. Identity now rides on GEOMETRY and
# on the recipe hue anchors, never on value swing.
# ════════════════════════════════════════════════════════════════════════════

def f_fern_forest(res, seed, cell=9.2, barbs=6, ladder=6.0, body=0.30, fine=0.10):
    """[ffr_window_fern] Dendrite-fern FOREST: a lattice of tiny window-frost
    rosettes — every cell a feathered star of radial barbs crossed by a side-rib
    ladder, crowned and 8-tier tinted. (poster fern -> forest -> in-band forest)"""
    rl, th, hv = _polar_cells(res, cell, 0.44, 311, 1.0)
    barb = (0.5 + 0.5 * np.cos(th * float(barbs))) ** 2.2
    rung = 0.5 + 0.5 * np.cos(rl * float(ladder))
    crown = sstep(1.32, 0.12, rl)
    tier = _tv(hv)
    T = 0.14 + crown * (0.24 + 0.40 * barb * (0.45 + 0.55 * rung)) \
        + tier * float(body) * (0.25 + 0.75 * crown) + _grain(res, seed, 313, fine)
    return _pk(T * _gentle(res, seed, 314))


def f_lamina_comb(res, seed, p=9.0, serr=7.0, warp=5.0, ribw=0.34, body=0.30,
                  fine=0.10):
    """[ffr_cyan_frond] Directional-lamina COMB: fat parallel feather laminae at
    the band pitch, crossed by a ladder of serration barbs. (pitch 6.5 -> 9.0,
    serration 3.5 -> 7.0: both were past r=180 where lag-1 coherence goes
    negative — measured ac 0.045 at the old pitch.)"""
    u, v = _uvrot(res, seed, 321, warp)
    ph = u / float(p)
    rib = _fat(np.abs(frac(ph) - 0.5), float(ribw))
    barb = _fat(np.abs(frac(v / float(serr)) - 0.5), 0.30)
    tier = _tv(h2(np.floor(ph), np.floor(v / float(serr)), 73))
    T = 0.13 + rib * 0.44 + barb * (0.10 + 0.32 * rib) \
        + tier * float(body) * (0.28 + 0.72 * rib) + _grain(res, seed, 323, fine)
    return _pk(T * _gentle(res, seed, 324))


def f_rime_mesh(res, seed, c1=9.6, c2=6.2, thr=0.30, body=0.26, fine=0.11):
    """[ffr_glacier_fern] Branching-filament MESH: two bounded-jitter Voronoi
    ridge webs — rime filaments branching at true triple points, fat enough to
    read on a car, plates domed between them."""
    _f1, e1, i1 = _voro(res, float(c1), 0.55, 331)
    _f2, e2, _i2 = _voro(res, float(c2), 0.62, 335)
    v1 = _fat(e1, float(thr))
    v2 = _fat(e2, float(thr) * 0.80)
    fil = np.maximum(v1, v2 * 0.82)
    node = sstep(1.25, 1.70, v1 + v2)
    relief = sstep(0.02, 0.44, e1)
    tier = _tv(h2(np.floor(i1 * 997.0), 0.0, 75))
    T = 0.15 + fil * 0.42 + node * 0.20 + relief * 0.20 \
        + tier * float(body) * (0.30 + 0.70 * relief) + _grain(res, seed, 333, fine)
    return _pk(T * _gentle(res, seed, 334))


def f_curl_strands(res, seed, p=9.0, drift=6.0, body=0.28, fine=0.09):
    """[ffr_violet_rime] Flow-combed STRANDS: fat rime cords wandering along a
    smooth curl field at the band pitch, each cord cylinder-shaded and broken
    into 8-tier lengths — wind-combed frost fur. (particle advection dropped:
    its density lumps were a pure sub-band envelope.)"""
    u, v = _uvrot(res, seed, 341, 0.0)
    # [SPB-FRACTURED-090] ONE smooth drift only. A second, finer displacement
    # octave phase-MODULATES the cord carrier, and phase modulation spreads a
    # sharp fundamental into sidebands across the whole spectrum: measured
    # ac 0.43 with it, 0.62 without, at the same band. Curvature comes from
    # the long-wavelength term, which does not smear the pitch.
    d1 = (fbm(res, res, rng(seed, 342), 2, 5) - 0.5) * 2.0 * float(drift)
    q = (u + d1) / float(p)
    cord = _fat(np.abs(frac(q) - 0.5), 0.32)
    gloss = 0.5 + 0.5 * np.cos(6.2831853 * frac(q))
    tier = _tv(h2(np.floor(q), np.floor(v / 11.0), 76))
    T = 0.13 + cord * 0.38 + gloss * 0.16 \
        + tier * float(body) * (0.30 + 0.70 * cord) + _grain(res, seed, 344, fine)
    return _pk(T * _gentle(res, seed, 345))


def f_flurry_grains(res, seed, c1=9.4, c2=6.0, c3=4.2, smear=0.40, body=0.30,
                    fine=0.09):
    """[ffr_steel_flurry] Granular multi-scale SCATTER: three flake-grain
    lattices (coarse / mid / fine), the mid population wind-smeared along one
    slant. Every grain is a domed crystal, not a splat — a Poisson splat field
    has no fundamental at all and collapsed to band 0.23."""
    d1, h1 = _dots(res, float(c1), 0.75, 351)
    d2, h2b = _dots(res, float(c2), 0.82, 355)
    d3, h3 = _dots(res, float(c3), 0.88, 359)
    g1 = sstep(0.96, 0.18, d1) * (0.35 + 0.65 * _tv(h1))
    g2 = sstep(0.92, 0.22, d2) * (0.35 + 0.65 * _tv(h2b))
    g3 = sstep(0.88, 0.30, d3) * (0.35 + 0.65 * _tv(h3))
    a = float(rng(seed, 352).uniform(0, np.pi))
    k = np.zeros((5, 5), np.float32)
    for t in range(5):
        ix = int(round(2 + np.cos(a) * (t - 2)))
        iy = int(round(2 + np.sin(a) * (t - 2)))
        k[iy, ix] = 1.0
    g2 = cv2.filter2D(g2, -1, k / k.sum()) * (1.0 + float(smear)) - g2 * float(smear)
    T = 0.13 + g1 * 0.40 + g2 * 0.28 + g3 * 0.18 \
        + _tv(h1) * float(body) * 0.35 + _grain(res, seed, 353, fine)
    return _pk(T * _gentle(res, seed, 354))


def f_star_lattice(res, seed, cell=9.6, arms=6, body=0.26, fine=0.08):
    """[ffr_silver_dendrite] STAR-LATTICE: a jittered lattice of tiny stellar
    dendrites — six analytic arms with a hot core and a soft envelope, one per
    cell so the flake pitch is the spectral fundamental."""
    rl, th, hv = _polar_cells(res, cell, 0.36, 361, 1.0)
    arm = (0.5 + 0.5 * np.cos(th * float(arms))) ** 2.6
    side = 0.5 + 0.5 * np.cos(rl * 7.4)
    env = sstep(1.28, 0.10, rl)
    core = np.exp(-((rl * 2.6) ** 2))
    T = 0.13 + env * (0.18 + 0.42 * arm * (0.5 + 0.5 * side)) + core * 0.26 \
        + _tv(hv) * float(body) * (0.28 + 0.72 * env) + _grain(res, seed, 363, fine)
    return _pk(T * _gentle(res, seed, 364))


def f_dust_struct(res, seed, cell=6.4, pcell=9.8, hot=0.60, body=0.24, fine=0.07):
    """[ffr_diamond_dust] DUST-with-structure: a dense fine lattice of glint
    grains; on a second, coarser lattice the hottest grains grow vertical
    micro light-pillars (airborne-crystal optics)."""
    d1, h1 = _dots(res, float(cell), 0.86, 371)
    glint = sstep(0.90, 0.16, d1) * (0.30 + 0.70 * _tv(h1))
    yy, xx = coords(res)
    c = float(pcell)
    ci, cj = np.floor(xx / c), np.floor(yy / c)
    hv = h2(ci, cj, 373)
    dx = xx - (ci + 0.5) * c
    dy = yy - (cj + 0.5) * c
    pil = np.exp(-((dx / 1.15) ** 2)) * np.exp(-((dy / 3.6) ** 2)) \
        * (hv > float(hot)).astype(np.float32)
    T = 0.13 + glint * 0.42 + pil * 0.34 \
        + _tv(hv) * float(body) * 0.42 + _grain(res, seed, 375, fine)
    return _pk(T * _gentle(res, seed, 376))


def f_hex_pave(res, seed, p=9.2, wall=0.30, body=0.30, fine=0.09):
    """[ffr_violet_sectored] PLATE-MOSAIC pave: hexagonal micro-plates paving
    the pane — each plate domed, split into pi/3 sector wedges of its own tier,
    with fat bond walls between. (pitch 7.2 -> 9.2, hairline wall -> fat seam.)"""
    u, v = _uvrot(res, seed, 381, 4.0)
    hx = u / float(p)
    hy = v / float(p) * 1.1547
    row = np.floor(hy)
    hxo = hx + (row % 2) * 0.5
    cu = hxo - np.floor(hxo + 0.5)
    cvv = hy - np.floor(hy + 0.5)
    d = np.sqrt(cu * cu + cvv * cvv)
    cid = h2(np.floor(hxo + 0.5), row, 77)
    th = np.arctan2(cvv, cu + 1e-6)
    sect = _tv(h2(np.floor((th + np.pi) / (np.pi / 3.0)), cid * 63.0, 79))
    dome = sstep(0.60, 0.06, d)
    seam = _fat(np.clip(0.50 - d, 0.0, 1.0), float(wall))
    T = 0.14 + dome * 0.34 + sect * float(body) * (0.30 + 0.70 * dome) \
        + _tv(cid) * 0.20 * dome - seam * 0.26 + _grain(res, seed, 383, fine)
    return _pk(T * _gentle(res, seed, 384))


def f_crackle_net(res, seed, c1=9.4, c2=6.0, w=0.26, body=0.24, fine=0.10):
    """[ffr_cyan_fissure] CRACKLE-NET: a two-scale crack web incised in bright
    ice — every fissure the same fat width (true polygon edge distance), lit
    lips outside it, a finer craze net inside the plates."""
    _f1, e1, i1 = _voro(res, float(c1), 0.42, 391)
    _f2, e2, _i2 = _voro(res, float(c2), 0.50, 395)
    crack = _fat(e1, float(w))
    craze = _fat(e2, float(w) * 0.72)
    lip = np.clip(_fat(e1, float(w) * 2.1) - crack, 0.0, 1.0)
    plate = sstep(0.04, 0.46, e1)
    T = 0.55 + plate * 0.16 + _tv(h2(np.floor(i1 * 997.0), 0.0, 81)) * float(body) \
        - crack * 0.52 - craze * 0.22 + lip * 0.26 + _grain(res, seed, 393, fine)
    return _pk(T * _gentle(res, seed, 394))


def f_chevron_pleats(res, seed, block=11.0, p=9.0, ang=0.72, body=0.28, fine=0.09):
    """[ffr_whiteout_rift] CHEVRON micro-pleats: herringbone snow pleats — fat
    ridge stripes flipping sign in narrow column blocks. (pleat pitch 5.0 ->
    9.0: at 5 px GEN the ridge sat at r~200 and lag-1 coherence went NEGATIVE,
    measured ac -0.12.)"""
    u, v = _uvrot(res, seed, 401, 6.0)
    col = np.floor(u / float(block))
    sgn = np.where(col % 2 < 1, 1.0, -1.0).astype(np.float32)
    ph = (u * np.cos(ang) * sgn + v * np.sin(ang)) / float(p)
    ridge = _fat(np.abs(frac(ph) - 0.5), 0.33)
    gloss = 0.5 + 0.5 * np.cos(6.2831853 * frac(ph))
    tier = _tv(h2(col, np.floor(ph), 83))
    seam = _fat(np.abs(frac(u / float(block)) - 0.5), 0.10)
    T = 0.14 + ridge * 0.40 + gloss * 0.14 + tier * float(body) * (0.30 + 0.70 * ridge) \
        - seam * 0.16 + _grain(res, seed, 403, fine)
    return _pk(T * _gentle(res, seed, 404))


def f_rd_labyrinth(res, seed, s1=1.3, s2=2.7, iters=10, body=0.22, fine=0.09):
    """[ffr_violet_chasm] Reaction-diffusion LABYRINTH: frost-crazing maze
    channels wandering the whole pane, walls fat and crowned, lips lit. Blur
    radii doubled so the maze wavelength lands at ~9 px at GEN instead of 5."""
    # [SPB-FRACTURED-090] the blur-difference reaction field keeps the huge
    # low-frequency wander of its fbm seed (measured sub-band share 0.30).
    # De-drifting the field BEFORE thresholding costs no channel and no lip:
    # the maze topology is set by the local balance, not by the offset.
    x = _turing(res, seed, 411, float(s1), float(s2), int(iters), 110)
    x = n01(_flat(x, 2.4))
    wall = sstep(0.40, 0.60, x)
    crown = sstep(0.46, 0.86, x)
    lip = n01(np.abs(cv2.Sobel(gauss(wall, 1.1), cv2.CV_32F, 1, 0, ksize=3))
              + np.abs(cv2.Sobel(gauss(wall, 1.1), cv2.CV_32F, 0, 1, ksize=3)))
    tier = _ptier(res, 6.6, 413, relief=0.62, jit=0.34)
    T = 0.20 + wall * 0.34 + crown * 0.20 + lip * 0.26 \
        + tier * float(body) + _grain(res, seed, 415, fine)
    return _pk(T * _gentle(res, seed, 416))


def f_serac_mosaic(res, seed, cell=9.8, ramp=8.6, gap=0.24, body=0.28, fine=0.09):
    """[ffr_blue_serac] Interlocking-cell MOSAIC: micro serac blocks — each
    block carries its OWN tilted facet ramp at the band pitch, fat dark gaps
    between, corners glinting."""
    yy, xx = coords(res)
    f1, e1, i1 = _voro(res, float(cell), 0.48, 421)
    gdir = h2(np.floor(i1 * 997.0), 0.0, 423) * 6.2831853
    rmp = frac((xx * np.cos(gdir) + yy * np.sin(gdir)) / float(ramp))
    facet = _fat(np.abs(rmp - 0.5), 0.34)
    top = sstep(0.04, 0.40, e1)
    seam = _fat(e1, float(gap))
    corner = np.exp(-((f1 / 0.16) ** 2))
    T = 0.15 + top * 0.26 + facet * 0.24 * (0.35 + 0.65 * top) \
        + _tv(h2(np.floor(i1 * 997.0), 0.0, 425)) * float(body) * (0.3 + 0.7 * top) \
        - seam * 0.30 + corner * 0.20 + _grain(res, seed, 427, fine)
    return _pk(T * _gentle(res, seed, 428))


def f_needle_felt(res, seed, c1=11.5, c2=7.6, ln=5.4, body=0.26, fine=0.08):
    """[ffr_hoarfrost_white] Spiculed-needle FELT: two matted lattices of short
    frost spicules, one per cell, each at its own angle — a felt with a real
    pitch instead of a Poisson stick pile."""
    def lay(cell, salt, half, w):
        yy, xx = coords(res)
        c = float(cell)
        ci, cj = np.floor(xx / c), np.floor(yy / c)
        jx = (h2(ci, cj, salt) - 0.5) * 0.55 * c
        jy = (h2(ci, cj, salt + 11) - 0.5) * 0.55 * c
        a = h2(ci, cj, salt + 5) * np.pi
        dx = xx - (ci + 0.5) * c - jx
        dy = yy - (cj + 0.5) * c - jy
        al = dx * np.cos(a) + dy * np.sin(a)
        ac_ = np.abs(-dx * np.sin(a) + dy * np.cos(a))
        v = _fat(ac_ / w, 0.55) * sstep(float(half) * 1.15, float(half) * 0.55,
                                        np.abs(al))
        return v, h2(ci, cj, salt + 23)

    # [SPB-FRACTURED-090] needle half-width 1.7 -> 3.4 px at GEN, and ONE
    # dominant spicule lattice with a quiet second. A 2-px needle is a
    # hairline: its power lands past r=200 where the lag-1 weight J0 is
    # negative (measured T-side ac 0.24). Two EQUAL scales are punished
    # twice over: a broad spectrum kills coherence, AND the thin-film LUT
    # (a strongly non-linear transfer) intermodulates every pair of in-band
    # components down into the sub-band -- measured on this engine, T
    # sub-band 0.02 became paint sub-band 0.26. A peaky field has nothing
    # to intermodulate with, which is exactly why the peakiest engines in
    # this module also carry the highest car-band.
    n1, h1 = lay(c1, 431, float(ln), 3.4)
    n2, h2b = lay(c2, 437, float(ln) * 0.72, 2.3)
    T = 0.14 + n1 * (0.34 + 0.34 * _tv(h1)) + n2 * (0.09 + 0.13 * _tv(h2b)) \
        + _ptier(res, 9.2, 439, relief=0.70) * float(body) + _grain(res, seed, 433, fine)
    return _pk(T * _gentle(res, seed, 434))


def f_cross_weave(res, seed, p=9.0, duty=0.34, body=0.26, fine=0.09):
    """[ffr_silver_hoar] Woven-cross COMB: two orthogonal fat needle combs
    weaving over-under at every crossing, each strand its own tier."""
    u, v = _uvrot(res, seed, 441, 4.0)
    A = _fat(np.abs(frac(u / float(p)) - 0.5), float(duty))
    B = _fat(np.abs(frac(v / float(p)) - 0.5), float(duty))
    check = ((np.floor(u / float(p)) + np.floor(v / float(p))) % 2).astype(np.float32)
    gA = 0.5 + 0.5 * np.cos(6.2831853 * frac(u / float(p)))
    gB = 0.5 + 0.5 * np.cos(6.2831853 * frac(v / float(p)))
    tA = _tv(h2(np.floor(u / float(p)), np.floor(v / (float(p) * 3.0)), 89))
    tB = _tv(h2(np.floor(v / float(p)), np.floor(u / (float(p) * 3.0)), 91))
    sA = A * (0.30 + 0.40 * gA + float(body) * tA) * (0.62 + 0.38 * check)
    sB = B * (0.30 + 0.40 * gB + float(body) * tB) * (1.0 - 0.38 * check)
    T = 0.13 + np.maximum(sA, sB) * 0.86 + _grain(res, seed, 443, fine)
    return _pk(T * _gentle(res, seed, 444))


def f_ripple_carpet(res, seed, cell=19.0, p=9.0, body=0.24, fine=0.08):
    """[ffr_cyan_frostbloom] Concentric-micro-ripple CARPET: one bloom per
    lattice cell, its rings at the band pitch, neighbours interfering at the
    cell borders. (Poisson bloom centres were a sub-band envelope: band 0.36.)"""
    rl, _th, hv = _polar_cells(res, float(cell), 0.60, 451, 0.0)
    dist = rl * float(cell) * 0.62
    ring = _fat(np.abs(frac(dist / float(p)) - 0.5), 0.32)
    env = sstep(1.35, 0.20, rl)
    T = 0.15 + ring * (0.22 + 0.34 * env) * (0.45 + 0.55 * _tv(hv)) \
        + env * 0.16 + _ptier(res, 6.8, 453, relief=0.60) * float(body) \
        + _grain(res, seed, 455, fine)
    return _pk(T * _gentle(res, seed, 456))


def f_thread_drift(res, seed, p=9.2, dash=13.0, drift=3.0, body=0.26, fine=0.09):
    """[ffr_ice_needles] THREAD-DRIFT: acicular threads all sharing one drift
    heading, fat and cylinder-shaded, broken into 8-tier dashes down their
    length — wind-laid needle ice."""
    a0 = float(rng(seed, 461).uniform(0, np.pi))
    yy, xx = coords(res)
    u, v = rot((yy, xx), a0)
    wu, _wv = warp_pair(res, seed, 462, float(drift))
    q = (v + wu) / float(p)
    thr = _fat(np.abs(frac(q) - 0.5), 0.30)
    gloss = 0.5 + 0.5 * np.cos(6.2831853 * frac(q))
    seg = np.floor(u / float(dash))
    tier = _tv(h2(np.floor(q), seg, 463))
    gap = sstep(0.42, 0.14, np.abs(frac(u / float(dash)) - 0.5))
    T = 0.14 + thr * (0.34 + 0.30 * tier) * (0.55 + 0.45 * gap) + gloss * 0.14 \
        + _ptier(res, 6.4, 465, relief=0.58) * float(body) + _grain(res, seed, 464, fine)
    return _pk(T * _gentle(res, seed, 466))


def f_foam_pack(res, seed, cell=9.0, border=0.22, body=0.26, fine=0.08):
    """[ffr_violet_trapped] Bubble-foam PACK: packed micro bubble domes, every
    Plateau border a fat bright film between neighbours."""
    # [SPB-FRACTURED-090] the Plateau film was a 1-px bright hairline sitting
    # on a hard-shouldered dome: band 0.91 but ac 0.34, i.e. it measured as
    # static. A real soap film is FAT and the dome is a smooth cap.
    # [SPB-FRACTURED-090] the two FLAT per-bubble tints are the leak here.
    # A random value per Voronoi cell looks band-limited but is not: cells
    # clump, so the tint field carries a long sub-band tail (measured
    # sub-band 0.36 with raw tints). De-drifting the TINT only -- never the
    # dome or the film -- makes neighbouring bubbles CONTRAST instead of
    # wandering, which is also what a real foam does under a light.
    f1, e1, i1 = _voro(res, float(cell), 0.34, 471)
    cid = np.floor(i1 * 997.0)
    dome = sstep(1.02, 0.06, f1) ** 1.25
    film = gauss(_fat(e1, float(border) * 1.7), 0.5)
    t1 = _flat(_tv(h2(cid, 0.0, 473)), 3.0)
    t2 = _flat(_tv(h2(cid, 1.0, 475)), 3.0)
    T = 0.12 + dome * 0.46 * (0.34 + 0.66 * t1) + film * 0.42 \
        + t2 * float(body) * dome + _grain(res, seed, 477, fine)
    return _pk(T * _gentle(res, seed, 478))


def f_ring_pack(res, seed, cell=9.6, rad=0.58, w=0.20, body=0.24, fine=0.08):
    """[ffr_steel_bubbles] RING-PACK: dense open annuli — bubble rims only, one
    per lattice cell, some doubled, all glinting."""
    rl, th, hv = _polar_cells(res, float(cell), 0.52, 481, 1.0)
    rim = _fat(np.abs(rl - float(rad)), float(w))
    inner = _fat(np.abs(rl - float(rad) * 0.52), float(w) * 0.8) \
        * (hv > 0.62).astype(np.float32)
    glint = np.clip(np.cos(th - hv * 6.2831853), 0.0, 1.0) ** 2
    T = 0.14 + rim * (0.30 + 0.34 * _tv(hv)) * (0.65 + 0.35 * glint) + inner * 0.22 \
        + _ptier(res, 6.2, 483, relief=0.62) * float(body) + _grain(res, seed, 485, fine)
    return _pk(T * _gentle(res, seed, 486))


def f_billow_moire(res, seed, p1=9.2, p2=8.4, dang=0.35, body=0.22, fine=0.08):
    """[ffr_cyan_veil] Billow MOIRE: two fat micro veils at slightly different
    pitch and heading — their beat is the shimmer, both carriers in band."""
    yy, xx = coords(res)
    a = float(rng(seed, 491).uniform(0, np.pi))
    u1, _ = rot((yy, xx), a)
    u2, _ = rot((yy, xx), a + float(dang))
    wu, _wv = warp_pair(res, seed, 493, 4.0)
    A = _fat(np.abs(frac((u1 + wu) / float(p1)) - 0.5), 0.33)
    B = _fat(np.abs(frac((u2 - wu) / float(p2)) - 0.5), 0.33)
    beat = A * B
    T = 0.14 + (A + B) * 0.20 + beat * 0.28 \
        + _ptier(res, 6.6, 495, relief=0.60, ang=a) * float(body) \
        + _grain(res, seed, 497, fine)
    return _pk(T * _gentle(res, seed, 498))


def f_scale_imbric(res, seed, sw=10.0, sh=8.0, body=0.28, fine=0.09):
    """[ffr_snowdrift_ice] Stacked-scale IMBRICATION: rows of overlapping
    sastrugi shingles, each domed with a fat carved rim at its lip."""
    u, v = _uvrot(res, seed, 501, 3.0)
    row = np.floor(v / float(sh))
    xo = u + (row % 2) * float(sw) * 0.5
    cu = (frac(xo / float(sw)) - 0.5) * 2.0
    cy = frac(v / float(sh))
    dome = np.clip(1.12 - np.hypot(cu, (cy - 0.42) * 1.9), 0.0, 1.0)
    rim = _fat(np.abs(cy - 0.90), 0.10)
    tier = _tv(h2(np.floor(xo / float(sw)), row, 503))
    T = 0.14 + dome * (0.30 + float(body) * tier) + rim * 0.26 \
        + _grain(res, seed, 505, fine)
    return _pk(T * _gentle(res, seed, 506))


ENGINES = {
    "f_fern_forest": f_fern_forest, "f_lamina_comb": f_lamina_comb,
    "f_rime_mesh": f_rime_mesh, "f_curl_strands": f_curl_strands,
    "f_flurry_grains": f_flurry_grains, "f_star_lattice": f_star_lattice,
    "f_dust_struct": f_dust_struct, "f_hex_pave": f_hex_pave,
    "f_crackle_net": f_crackle_net, "f_chevron_pleats": f_chevron_pleats,
    "f_rd_labyrinth": f_rd_labyrinth, "f_serac_mosaic": f_serac_mosaic,
    "f_needle_felt": f_needle_felt, "f_cross_weave": f_cross_weave,
    "f_ripple_carpet": f_ripple_carpet, "f_thread_drift": f_thread_drift,
    "f_foam_pack": f_foam_pack, "f_ring_pack": f_ring_pack,
    "f_billow_moire": f_billow_moire, "f_scale_imbric": f_scale_imbric,
}
ENGINES = {k: _lowcut(v) for k, v in ENGINES.items()}


# ════════════════════════════════════════════════════════════════════════════
# CATEGORY-SPECIFIC MACRO KIND — starburst (kept for contract stability;
# no pass-2 recipe uses it — poster macros are the disease we just cured).
# ════════════════════════════════════════════════════════════════════════════

def m_starburst(r, mp, seed, K):
    """Radiant core: luminous heart with an angular ray fan fading outward."""
    yy, xx = K.coords(r)
    cx, cy = float(mp.get("cx", 0.5)), float(mp.get("cy", 0.5))
    dist = np.hypot((xx / r) - cx, (yy / r) - cy)
    ang = np.arctan2((yy / r) - cy, (xx / r) - cx)
    rays_n = float(mp.get("rays", 12.0))
    ray = (0.5 + 0.5 * np.cos(ang * rays_n + float(K.h2(seed, 0, 43)) * 6.0)) ** 2.0
    core = np.exp(-((dist * float(mp.get("core_sharp", 2.6))) ** 2))
    fan = ray * np.clip(1.15 - dist * float(mp.get("fade", 1.15)), 0.0, 1.0)
    M = np.clip(core * 1.1 + fan * 0.75, 0.0, 1.0)
    sect = float(mp.get("sectors", 8.0))
    D = K.n01(K.h2(np.floor((ang / np.pi + 1.0) * sect), np.floor(dist * 3.0), 47)
              + dist * 0.2)
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
# RECIPES — 20 finishes, ids ffr_*, seeds 1020-1039 (UNCHANGED ids/seeds).
# [pass 2, 2026-08-02] all recipes re-dialed for the FIELD standard: tight
# value drama (vd ~(0.80,1.20)), tmod <=0.14, ambient 0.12, sparkle ~0.12,
# gray <=0.42 (rule 5: luminous, colorful at a glance), gentle domain macros
# only. Per-id band movement is logged in _fractured_triage/verify_frost.json.
# ════════════════════════════════════════════════════════════════════════════

FERNS = {
 # [pass2] poster window-fern (band 0.579 but poster comp) -> fern FOREST field
 "ffr_window_fern": dict(name="Window Fern", engine="f_fern_forest",
    eargs=dict(cell=7.912, barbs=6, ladder=6.0, body=0.522, fine=0.1, lowcut=1.8, soft=0.6),
    seed=1020, lut=(420.0, 920.0, 1.0, 1.20, 0.8), val=0.27,
    hues=[0.56, 0.56, 0.56, 0.56, 0.56, 0.56, 0.56, 0.56, 0.56, 0.582, 0.544, 0.608, 0.53, 0.635, 0.662, 0.69], hspan=0.042, satboost=0.258,
    macro=("clouds", dict(base=7, salt=1020)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4, ccboost=1.4),
    desc="A forest of tiny window-frost ferns feathering over blue crystal mottle. A FRACTURED FROST finish."),
 # [pass2] one giant frond poster (band 0.208) -> parallel lamina comb field
 "ffr_cyan_frond": dict(name="Cyan Frond", engine="f_lamina_comb",
    eargs=dict(p=9.72, serr=7.56, warp=5.0, ribw=0.34, body=0.283, fine=0.1, lowcut=1.8, soft=0.9),
    seed=1021, lut=(430.0, 900.0, 1.0, 1.30, 2.4), val=0.27,
    hues=[0.53, 0.53, 0.53, 0.53, 0.53, 0.53, 0.53, 0.53, 0.53, 0.552, 0.514, 0.578, 0.5, 0.605, 0.632, 0.66], hspan=0.042, satboost=0.280,
    macro=("drift", dict(angle=0.3, salt=1021)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.3),
    desc="Cyan feather laminae combed edge to edge, every barb serrated fine. A FRACTURED FROST finish."),
 # [pass2] 4-edge thicket poster (band 0.415) -> criss-cross rime filament mesh
 "ffr_glacier_fern": dict(name="Glacier Fern", engine="f_rime_mesh",
    eargs=dict(c1=12.234, c2=7.901, thr=0.3, body=0.377, fine=0.11, lowcut=2.6, soft=0.9),
    seed=1022, lut=(410.0, 940.0, 1.05, 1.30, 3.2), val=0.26,
    hues=[0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.572, 0.534, 0.598, 0.52, 0.625, 0.652, 0.68], hspan=0.042, satboost=0.258,
    macro=("continents", dict(base=5, cells=6.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.3),
    desc="An ice-blue mesh of rime filaments crossing at every angle over frozen cells. A FRACTURED FROST finish."),
 # [pass2] twin-vortex poster (band 0.587, poster comp) -> curl-combed strand fur
 "ffr_violet_rime": dict(name="Violet Rime", engine="f_curl_strands",
    eargs=dict(p=9.133, drift=6.0, body=0.155, fine=0.09, lowcut=1.8, soft=1.25),
    seed=1023, lut=(400.0, 760.0, 0.95, 1.35, 0.8), val=0.26,
    hues=[0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.773, 0.733, 0.715, 0.695, 0.673, 0.651, 0.63], hspan=0.055, satboost=0.258,
    macro=("clouds", dict(base=9, salt=1023)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.3),
    desc="Violet rime fur — thousands of wind-combed micro strands curling as one field. A FRACTURED FROST finish."),
}

FLAKES = {
 # [pass2] 46 mid flakes (band 0.141) -> 3-scale wind-smeared grain scatter
 "ffr_steel_flurry": dict(name="Steel Flurry", engine="f_flurry_grains",
    eargs=dict(c1=7.599, c2=4.85, c3=3.395, smear=0.4, body=0.127, fine=0.09, lowcut=2.6, soft=0.9),
    seed=1024, lut=(420.0, 900.0, 1.0, 1.20, 0.0), val=0.24,
    hues=[0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.62, 0.58, 0.642, 0.562, 0.668, 0.545, 0.695], hspan=0.055, satboost=0.341,
    macro=("clouds", dict(base=7, salt=1024)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.11, sparkle=0.05, gray=0.30, mswing=1.4, ccboost=1.4),
    desc="A steel-blue flurry of flake grains at three sizes, wind-smeared across the whole panel. A FRACTURED FROST finish."),
 # [pass2] ONE grand dendrite poster (band 0.254) -> lattice of tiny stellar flakes
 "ffr_silver_dendrite": dict(name="Silver Dendrite", engine="f_star_lattice",
    eargs=dict(cell=7.761, arms=6, body=0.11, fine=0.08, lowcut=2.6, soft=0.9),
    seed=1025, lut=(410.0, 760.0, 0.95, 1.15, 0.8), val=0.25,
    hues=[0.565, 0.565, 0.565, 0.565, 0.565, 0.565, 0.565, 0.565, 0.565, 0.585, 0.543, 0.607, 0.523, 0.631, 0.507, 0.655], hspan=0.055, satboost=0.191,
    macro=("continents", dict(base=5, cells=5.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.11, sparkle=0.05, gray=0.35, mswing=1.5, mfloor=10.0),
    desc="A silver lattice of thousands of tiny stellar dendrites, warm glints in the facets. A FRACTURED FROST finish."),
 # [pass2] big light pillars poster (band 0.134) -> glint powder + micro pillars
 "ffr_diamond_dust": dict(name="Diamond Dust", engine="f_dust_struct",
    eargs=dict(cell=7.099, pcell=10.87, hot=0.6, body=0.505, fine=0.07, lowcut=1.8, soft=0.9),
    seed=1026, lut=(430.0, 890.0, 1.0, 1.15, 0.2), val=0.25,
    hues=[0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.6, 0.558, 0.622, 0.538, 0.646, 0.522, 0.67], hspan=0.055, satboost=0.191,
    macro=("domains", dict(cells=40, salt=1026)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.11, sparkle=0.05, gray=0.35, mswing=1.5, mfloor=10.0, ccboost=1.5),
    desc="Prismatic diamond dust — thousands of micro glints, the hottest growing tiny light pillars. A FRACTURED FROST finish."),
 # [pass2] 4 huge plates poster (band 0.126) -> hex micro-plate pave
 "ffr_violet_sectored": dict(name="Violet Sectored Plate", engine="f_hex_pave",
    eargs=dict(p=10.731, wall=0.3, body=0.127, fine=0.09, lowcut=1.0, soft=0.0),
    seed=1027, lut=(400.0, 760.0, 1.0, 1.35, 4.0), val=0.24,
    hues=[0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.783, 0.743, 0.725, 0.705, 0.683, 0.661, 0.64], hspan=0.055, satboost=0.258,
    macro=("domains", dict(cells=5, salt=1027)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.3),
    desc="Pale-violet hexagonal micro plates paving the pane, sector wedges aglow. A FRACTURED FROST finish."),
}

CREVASSES = {
 # [pass2] 2-set parallel slots poster (band 0.411) -> 2-scale crackle net
 "ffr_cyan_fissure": dict(name="Cyan Fissure", engine="f_crackle_net",
    eargs=dict(c1=8.731, c2=5.573, w=0.26, body=0.156, fine=0.1, lowcut=2.6, soft=0.9),
    seed=1028, lut=(420.0, 940.0, 1.0, 1.30, 1.1), val=0.26,
    hues=[0.54, 0.54, 0.54, 0.54, 0.54, 0.54, 0.54, 0.54, 0.54, 0.562, 0.524, 0.588, 0.51, 0.615, 0.642, 0.67], hspan=0.042, satboost=0.280,
    macro=("clouds", dict(base=7, salt=1028)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4),
    desc="A cyan crackle net — fine crevasse fissures webbing bright ice, lips lit. A FRACTURED FROST finish."),
 # [pass2] 7-step terrace poster (band 0.156) -> herringbone drift pleats
 "ffr_whiteout_rift": dict(name="Whiteout Rift", engine="f_chevron_pleats",
    eargs=dict(block=11.0, p=9.0, ang=0.72, body=0.182, fine=0.09, lowcut=1.8, soft=1.25),
    seed=1029, lut=(410.0, 900.0, 0.95, 1.15, 2.8), val=0.25,
    hues=[0.585, 0.585, 0.585, 0.585, 0.585, 0.585, 0.585, 0.585, 0.585, 0.605, 0.563, 0.627, 0.543, 0.651, 0.527, 0.675], hspan=0.055, satboost=0.190,
    macro=("drift", dict(angle=0.9, salt=1029)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.11, sparkle=0.05, gray=0.40, mswing=1.5, mfloor=10.0),
    desc="Whiteout drift pleats — herringbone snow ridges rifted into narrow chevron lanes. A FRACTURED FROST finish."),
 # [pass2] ONE meander canyon poster (band 0.236) -> frost-crazing RD labyrinth
 "ffr_violet_chasm": dict(name="Violet Chasm", engine="f_rd_labyrinth",
    eargs=dict(s1=1.145, s2=2.29, iters=9, body=0.393, fine=0.09, lowcut=1.8, soft=0.9),
    seed=1030, lut=(400.0, 920.0, 1.0, 1.35, 5.4), val=0.28,
    hues=[0.725, 0.725, 0.725, 0.725, 0.725, 0.725, 0.725, 0.725, 0.725, 0.743, 0.703, 0.685, 0.665, 0.643, 0.621, 0.6], hspan=0.055, satboost=0.183,
    macro=("clouds", dict(base=8, salt=1030)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4),
    desc="A violet chasm labyrinth — micro maze channels crazing the whole frozen pane. A FRACTURED FROST finish."),
 # [pass2] 8 big serac blocks (band 0.314) -> 85-cell micro block mosaic
 "ffr_blue_serac": dict(name="Blue Serac", engine="f_serac_mosaic",
    eargs=dict(cell=9.212, ramp=8.6, gap=0.24, body=0.182, fine=0.09, lowcut=2.6, soft=0.6),
    seed=1031, lut=(430.0, 760.0, 1.05, 1.30, 2.4), val=0.25,
    hues=[0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.62, 0.58, 0.642, 0.562, 0.668, 0.545, 0.695], hspan=0.055, satboost=0.370,
    macro=("domains", dict(cells=12, salt=1031)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, gray=0.30, ccboost=1.4),
    desc="A blue serac mosaic — tilted micro ice blocks interlocking, gaps dark, corners glinting. A FRACTURED FROST finish."),
}

NEEDLES = {
 # [pass2] 14 star posters (band 0.237, hue 3) -> needle spicule felt; gray
 # 0.85 -> 0.40 so the pastel prism reads (rule 5: colorful at a glance)
 "ffr_hoarfrost_white": dict(name="White Hoarfrost", engine="f_needle_felt",
    eargs=dict(c1=10.538, c2=6.705, ln=4.2, body=0.072, fine=0.08, lowcut=0.0, soft=1.25),
    seed=1032, lut=(420.0, 910.0, 1.0, 1.20, 0.5), val=0.26,
    hues=[0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.6, 0.558, 0.622, 0.538, 0.646, 0.522, 0.67], hspan=0.055, satboost=0.190,
    macro=("clouds", dict(base=8, salt=1032)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.12, sparkle=0.05, gray=0.40, mswing=1.5, mfloor=10.0, ccboost=1.4),
    desc="White hoarfrost felt — thousands of pastel needle spicules matted over the panel. A FRACTURED FROST finish."),
 # [pass2] 7 wire combs poster (band 0.082, WORST) -> woven cross comb field
 "ffr_silver_hoar": dict(name="Silver Hoar", engine="f_cross_weave",
    eargs=dict(p=9.0, duty=0.34, body=0.377, fine=0.09, lowcut=1.8, soft=0.6),
    seed=1033, lut=(410.0, 900.0, 0.95, 1.15, 2.0), val=0.25,
    hues=[0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.58, 0.6, 0.558, 0.622, 0.538, 0.646, 0.522, 0.67], hspan=0.055, satboost=0.191,
    macro=("clouds", dict(base=8, salt=1033)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.11, sparkle=0.05, gray=0.35, mswing=1.4, ccboost=1.4),
    desc="Silver hoar needles woven over-under in two crossing combs, checker-glinting. A FRACTURED FROST finish."),
 # [pass2] 10 rosette posters (band 0.287) -> interfering micro ripple carpet
 "ffr_cyan_frostbloom": dict(name="Cyan Frostbloom", engine="f_ripple_carpet",
    eargs=dict(cell=20.52, p=9.0, body=0.505, fine=0.08, lowcut=1.8, soft=0.6),
    seed=1034, lut=(430.0, 930.0, 1.0, 1.30, 5.6), val=0.25,
    hues=[0.52, 0.52, 0.52, 0.52, 0.52, 0.52, 0.52, 0.52, 0.52, 0.542, 0.504, 0.568, 0.49, 0.595, 0.622, 0.65], hspan=0.042, satboost=0.280,
    macro=("clouds", dict(base=9, salt=1034)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4),
    desc="Cyan frostblooms rippling — many small ring carpets interfering across sea ice. A FRACTURED FROST finish."),
 # [pass2] 85 long shards poster (band 0.123) -> 750-thread drift field
 "ffr_ice_needles": dict(name="Ice Needles", engine="f_thread_drift",
    eargs=dict(p=9.34, dash=13.198, drift=3.0, body=0.374, fine=0.09, lowcut=1.8, soft=0.9),
    seed=1035, lut=(420.0, 760.0, 1.05, 1.30, 4.0), val=0.25,
    hues=[0.57, 0.57, 0.57, 0.57, 0.57, 0.57, 0.57, 0.57, 0.57, 0.59, 0.548, 0.612, 0.528, 0.636, 0.512, 0.66], hspan=0.055, satboost=0.256,
    macro=("drift", dict(angle=1.0, salt=1035)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, gray=0.30, mswing=1.3),
    desc="Needle ice laid by the wind — hundreds of fine threads drifting one way over frost grain. A FRACTURED FROST finish."),
}

BUBBLES = {
 # [pass2] 14 bubble trains poster (band 0.273) -> packed micro dome foam
 "ffr_violet_trapped": dict(name="Violet Trapped Ice", engine="f_foam_pack",
    eargs=dict(cell=9.137, border=0.22, body=0.094, fine=0.08, lowcut=0.0, soft=0.0),
    seed=1036, lut=(400.0, 760.0, 0.95, 1.35, 3.2), val=0.26,
    hues=[0.725, 0.725, 0.725, 0.725, 0.725, 0.725, 0.725, 0.725, 0.725, 0.743, 0.703, 0.685, 0.665, 0.643, 0.621, 0.6], hspan=0.055, satboost=0.183,
    # [SPB-FRACTURED-090d 2026-08-02] CLIPPING-DEBT REPAY. satboost 1.15 ->
    # 0.30 (ice is a grey-white subject; value carries it) took the channel
    # clipping out of art_work's luma renormalisation, and with it the ac that
    # the clip was propping up: 0.569 -> 0.528 on a BYTE-IDENTICAL field
    # (f_foam_pack runs soft=0.0, so it has no high-cut of its own). Bought
    # back with value drama only — vd 0.96/1.06 -> 0.56/1.50. Measured:
    # band 0.8280 -> 0.763, ac 0.528 -> 0.572.
    macro=("clouds", dict(base=8, salt=1036)), vd=(0.56, 1.50), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.3),
    desc="Violet methane foam — micro bubble domes packed tight, plateau borders glowing. A FRACTURED FROST finish."),
 # [pass2] 9 foam rafts poster (band 0.157) -> dense open ring pack
 "ffr_steel_bubbles": dict(name="Steel Bubbles", engine="f_ring_pack",
    eargs=dict(cell=13.367, rad=0.58, w=0.2, body=0.156, fine=0.08, lowcut=0.0, soft=0.9),
    seed=1037, lut=(420.0, 900.0, 1.0, 1.15, 3.4), val=0.25,
    hues=[0.59, 0.59, 0.59, 0.59, 0.59, 0.59, 0.59, 0.59, 0.59, 0.61, 0.57, 0.632, 0.552, 0.658, 0.535, 0.685], hspan=0.055, satboost=0.341,
    macro=("clouds", dict(base=8, salt=1037)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.11, sparkle=0.05, gray=0.30, mswing=1.4, ccboost=1.4),
    desc="Steel-blue bubble rims — a dense pack of glinting micro annuli in dark ice. A FRACTURED FROST finish."),
 # [pass2] 6 sine curtains poster (band 0.337) -> interfering micro veil moire
 "ffr_cyan_veil": dict(name="Cyan Veil", engine="f_billow_moire",
    eargs=dict(p1=7.912, p2=7.224, dang=0.35, body=0.187, fine=0.08, lowcut=1.0, soft=0.35),
    seed=1038, lut=(430.0, 920.0, 1.0, 1.30, 2.2), val=0.25,
    hues=[0.52, 0.52, 0.52, 0.52, 0.52, 0.52, 0.52, 0.52, 0.52, 0.542, 0.504, 0.568, 0.49, 0.595, 0.622, 0.65], hspan=0.042, satboost=0.280,
    macro=("clouds", dict(base=7, salt=1038)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.3),
    desc="Cyan veils of interfering micro waves shimmering through luminous frozen water. A FRACTURED FROST finish."),
 # [pass2] big discs + wide ripples poster (band 0.167) -> sastrugi scale shingles
 "ffr_snowdrift_ice": dict(name="Snowdrift Ice", engine="f_scale_imbric",
    eargs=dict(sw=9.4, sh=7.52, body=0.589, fine=0.09, lowcut=2.6, soft=0.9),
    seed=1039, lut=(410.0, 890.0, 0.95, 1.15, 5.6), val=0.25,
    hues=[0.555, 0.555, 0.555, 0.555, 0.555, 0.555, 0.555, 0.555, 0.555, 0.575, 0.533, 0.597, 0.513, 0.621, 0.497, 0.645], hspan=0.055, satboost=0.206,
    macro=("continents", dict(base=5, cells=5.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.11, sparkle=0.05, gray=0.40, mswing=1.5, mfloor=10.0),
    desc="Snowdrift shingles — overlapping wind-cut sastrugi scales stacked row on row. A FRACTURED FROST finish."),
}

GROUPS = {
    "FERNS": FERNS,
    "FLAKES": FLAKES,
    "CREVASSES": CREVASSES,
    "NEEDLES": NEEDLES,
    "BUBBLES": BUBBLES,
}

KIT = catlib.CategoryKit(engines=ENGINES, groups=GROUPS, tag="fractured-frost",
                         extra_macro={"starburst": m_starburst, "clouds": m_clouds,
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
 "ffr_cyan_fissure": -0.0085,
 "ffr_cyan_frostbloom": -0.0110,
 "ffr_diamond_dust": -0.0130,
 "ffr_glacier_fern": -0.0192,
 "ffr_hoarfrost_white": -0.0172,
 "ffr_silver_dendrite": -0.0325,
 "ffr_silver_hoar": -0.0081,
 "ffr_snowdrift_ice": -0.0227,
 "ffr_steel_flurry": -0.0093,
 "ffr_violet_rime": +0.0230,
 "ffr_violet_sectored": +0.0308,
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
}

for _fid, _off in _ACCFIX.items():
    _r = ALL[_fid]
    _r["hues"] = _r["hues"][:-2] + [round((_h + _off) % 1.0, 4)
                                    for _h in _r["hues"][-2:]]
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
