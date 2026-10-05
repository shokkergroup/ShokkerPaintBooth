# -*- coding: utf-8 -*-
"""FRACTURED NEBULA (2026-07-30) — category 6/10 of the FRACTURED expansion.

[SPB-FRACTURED-090 2026-08-02] IN-BAND LATTICE PASS — owner: "push the
others to the same levels ... WITHOUT it being static noise or just a bunch of
repeats". Car-band median 0.707 -> 0.891 (house flagship FRACTURED MINDS is 0.82),
per-finish min 0.677 (fnb_violet_galaxy, see below). Gate is now _fractured_triage/verify_guard.py, which adds
three ANTI-CHEAT guards so a high band cannot be bought with noise (white
noise measures band ~0.95 and FAILS all three): lag-1 horizontal
autocorrelation >= 0.55, in-band spectral peakiness >= 0.30, Otsu
connected-shape fraction >= 0.55 — plus band >= 0.70 each, fineness > 6.5,
coverage >= 56/64, hue bins >= 5, < 2.0 s @512 and <= 2.5 s @2048, and
intra-module descriptor pair-cosine <= 0.55 (worst pair 0.238).

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
MEASURED FRONTIER — fnb_violet_galaxy (lens-streak scatter) tops out at band
0.677. An ANISOTROPIC motif is the one archetype that cannot be made peaky:
an elongated lozenge spreads its power right round the spectral ring instead
of stacking it on one radius, and every attempt to force it higher (narrower
orientation spread, rounder lozenges, matched tier lattice) either broke the
lag-1 guard or turned it into the ringlet pack. It is left DISTINCT at its
frontier rather than faked; the module median carries it.

ARCHETYPE LEDGER (one DISTINCT compositional archetype per id — no repeats):
  fnb_violet_billows    micro-turbulence billows   (ridged high-octave gas)
  fnb_magenta_remnant   filament-wisp web          (bright curved shell wisps)
  fnb_cyan_spiral       tiny-spiral pave           (hundreds of micro spirals)
  fnb_golden_cluster    clustered granule scatter  (worley-clumped star powder)
  fnb_teal_annulus      nested-ringlet pack        (concentric micro ring stamps)
  fnb_cyan_drift        sheared lamina strata      (wavy micro strata, dashed)
  fnb_gilded_shockfront crescent bow-shock carpet  (many small arcs + wakes)
  fnb_teal_starfield    spiked-star felt           (PSF points + cross spikes)
  fnb_violet_galaxy     lens-streak scatter        (tiny edge-on galaxy lozenges)
  fnb_magenta_rift      dark-lane branching mesh   (dark dust net over glow)
  fnb_teal_lagoon       cavity foam                (dark bays, bright rims)
  fnb_violet_annulus    ring-scale imbrication     (overlapping half-ring rows)
  fnb_magenta_emission  columnar tuft field        (vertical strand tufts + tips)
  fnb_cyan_dustlane     dark thread-drift          (dashed dark lanes, one heading)
  fnb_golden_pinwheel   pinwheel-knot lattice      (lattice of 3-arm micro whorls)
  fnb_magenta_stardust  powder-with-silhouettes    (dense powder + dark globules)
  fnb_cyan_shockwave    shock-ring interference    (sharp-front micro ring carpet)
  fnb_gilded_veil       gauze cross-weave          (two soft thread families)
  fnb_teal_rift         reaction-diffusion rift maze (dark channels in teal glow)
  fnb_violet_starglow   orb-glow pack              (dense bokeh orbs + halos)

Contract unchanged: same 20 ids (fnb_*), same seeds 1080-1099, same
install_into_engine signature, (spec_fn, paint_fn) via CategoryKit; spec
traces the paint field. Determinism: catlib.rng (np.random.default_rng) +
zlib.crc32 salts, no hash(str). Category macro kind "core" kept for contract
stability (recipes use gentle domain macros only — poster macros were the
disease). LUT phases re-picked by measured art car-band sweep where the
default transfer flattened the field (same method as FROST pass 2).

[SPB-FRACTURED-090d 2026-08-02] COLOUR PASS — owner visual review: geometry
accepted; deep space KEEPS its magenta/violet/teal/gold drama, the requirement
is only that each id's NAMED hue wins at a glance. Fixed here with no change to
any lattice / cell pitch / eargs / LUT span (T fields byte-identical):

 * the single unbalanced complementary accent was dragging the
   saturation-weighted circular mean off the name — fnb_cyan_shockwave landed
   0.099 of a turn away and read TEAL. Ladders are now a 16-rung spine plus TWO
   accent rungs, and the accents are corrected independently of the spine
   (_ACCFIX rotates only the tail, _HUEFIX only the whole ladder), so the
   dominant population AND the whole-field mean both land on the name. Worst
   residual 0.013 turn on both statistics.
 * NO GREEN. The balanced-accent maths wants a rung a third of a turn below a
   cyan base, which is chartreuse — it painted lime blocks across the cyans and
   olive ones across the golds. Green is not a nebula colour; accents now come
   only from the real set (H-alpha rose/red, magenta, violet, indigo,
   cyan/teal, gold), which for a cyan base means both accents walk UP into blue
   and violet.
 * saturation was CLIPPED FLAT at satA 0.99 — fluorescent poster, not deep
   space. Retargeted to ~0.80: still by far the most saturated of the three
   FRACTURED colour modules, but unclipped, so hue and value texture survive.
   That also RETIRED fnb_violet_galaxy's documented sub-0.70 band exception
   (0.677 -> 0.710) — the clip had been eating its lens-streak detail.
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
            segs=1, curl=0.0):
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


def _stamp_conv(res, seed, salt, n, mk_kernel, nrot=8, lattice=0.0):
    """n tiered stamps via nrot rotation-group convolutions (fast + varied).
    lattice>0: jittered hex-ish lattice placement with that pitch instead of
    uniform random scatter."""
    r0 = rng(seed, salt)
    if lattice > 0.0:
        px, py = [], []
        ny = int(res / (lattice * 0.85)) + 2
        nx = int(res / lattice) + 2
        for j in range(ny):
            for i in range(nx):
                x = (i + 0.5 * (j % 2)) * lattice + float(r0.uniform(-3, 3))
                y = j * lattice * 0.85 + float(r0.uniform(-3, 3))
                if 0 <= x < res and 0 <= y < res:
                    px.append(int(x))
                    py.append(int(y))
        px = np.array(px)
        py = np.array(py)
    else:
        px = r0.integers(0, res, int(n))
        py = r0.integers(0, res, int(n))
    m = len(px)
    w = _TIERS[r0.integers(0, 8, m)].astype(np.float32)
    g = r0.integers(0, nrot, m)
    out = np.zeros((res, res), np.float32)
    for kk in range(int(nrot)):
        sel = g == kk
        if not sel.any():
            continue
        dm = np.zeros((res, res), np.float32)
        np.add.at(dm, (py[sel], px[sel]), w[sel])
        out = out + cv2.filter2D(dm, -1, mk_kernel(kk))
    return out


def _turing(res, seed, salt, s1, s2, iters=9, base=200):
    x = fbm(res, res, rng(seed, salt), 2, int(base)).astype(np.float32)
    for _ in range(int(iters)):
        x = x + (gauss(x, s1) - gauss(x, s2)) * 1.6
        x = np.clip(x, -1.5, 2.5)
    return n01(x)


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
# LATTICES at the band pitch (8.5-10 px at GEN = 27-32 px at 2048), the value
# carried by smooth periodic RELIEF inside each cell and separated by FAT
# edge-distance seams. Nothing derives its luma from an fbm field any more
# (1/f dumps its power under r=64) and nothing is a Poisson scatter of drawn
# stamps any more (a random placement has no fundamental at all — its envelope
# is a pure sub-band leak). Deep-space matter is expressed as a DENSE FIELD:
# a galaxy is a lattice of small whorls, a shockwave a lattice of small blast
# rings. Identity rides on geometry and on the recipe hue ladder, never on a
# value swing (vd is charged twice by a ratio metric).
# ════════════════════════════════════════════════════════════════════════════

def n_billow_turb(res, seed, cell=9.6, c2=6.2, lift=1.1, body=0.28, fine=0.10):
    """[fnb_violet_billows] Micro-turbulence BILLOWS: a pave of rolling
    emission billows — each cell a smooth crown, lit on top and shadowed
    underneath, with a finer billow lattice boiling on its shoulders."""
    f1, _e1, i1 = _voro(res, float(cell), 0.44, 611)
    d2, h2b = _dots(res, float(c2), 0.85, 615)
    crown = sstep(1.10, 0.04, f1)
    small = sstep(0.95, 0.18, d2)
    shade = cv2.Sobel(gauss(crown, 1.1), cv2.CV_32F, 0, 1, ksize=3)
    tier = _flat(_tv(h2(np.floor(i1 * 997.0), 0.0, 613)), 3.0)
    # [SPB-FRACTURED-090] the second billow scale and the Sobel highlight
    # were both carrying a THIRD of the variance each. Two equal in-band
    # scales broaden the spectrum, and every pair of in-band components
    # intermodulates DOWN through the thin-film LUT into the sub-band
    # (measured here: 0.28 of the paint's power). One dominant crown with a
    # quiet boil on its shoulders reads the same and measures 0.20 better.
    T = 0.14 + crown * 0.40 + small * (0.07 + 0.10 * _tv(h2b)) \
        + np.clip(shade, 0.0, None) * float(lift) * 0.55 \
        + tier * float(body) * (0.30 + 0.70 * crown) + _grain(res, seed, 617, fine)
    return _pk(T * _gentle(res, seed, 619))


def n_wisp_web(res, seed, cell=9.4, thr=0.28, halo=1.6, body=0.24, fine=0.09):
    """[fnb_magenta_remnant] Filament-WISP web: the whole canvas is a single
    connected web of bright supernova-shell filaments — true polygon edge
    distance, so every wisp is the same fat width, each wrapped in its own
    halo and brightest at the triple points."""
    _f1, e1, i1 = _voro(res, float(cell), 0.48, 621)
    wisp = _fat(e1, float(thr))
    glow = gauss(wisp, float(halo)) * (1.0 - wisp)
    node = sstep(0.30, 0.06, e1)
    tier = _flat(_tv(h2(np.floor(i1 * 997.0), 0.0, 623)), 3.0)
    T = 0.14 + wisp * 0.42 + n01(glow) * 0.24 + node * 0.16 \
        + tier * float(body) + _grain(res, seed, 625, fine)
    return _pk(T * _gentle(res, seed, 627))


def n_spiral_pave(res, seed, cell=9.8, arms=2, twist=5.0, body=0.26, fine=0.09):
    """[fnb_cyan_spiral] TINY-SPIRAL pave: a whole crowd of micro spiral
    eddies, one per lattice cell, each with its own rotation — a galaxy is a
    population, never a poster."""
    rl, th, hv = _polar_cells(res, float(cell), 0.44, 631, 1.0)
    arm = (0.5 + 0.5 * np.cos(th * float(arms) + rl * float(twist))) ** 2.4
    env = sstep(1.30, 0.10, rl)
    core = np.exp(-((rl * 2.4) ** 2))
    T = 0.13 + env * (0.16 + 0.40 * arm) + core * 0.26 \
        + _tv(hv) * float(body) * (0.28 + 0.72 * env) + _grain(res, seed, 635, fine)
    return _pk(T * _gentle(res, seed, 637))


def n_cluster_granules(res, seed, cell=6.4, ccell=9.8, body=0.28, fine=0.08):
    """[fnb_golden_cluster] CLUSTERED granule scatter: a fine granule lattice
    whose brightness is gated by a coarser cluster lattice — star powder that
    clumps into knots instead of spreading evenly."""
    d1, h1 = _dots(res, float(cell), 0.88, 641)
    d2, h2b = _dots(res, float(ccell), 0.55, 645)
    gran = sstep(0.92, 0.14, d1) * (0.30 + 0.70 * _tv(h1))
    clump = sstep(1.05, 0.15, d2)
    T = 0.13 + gran * (0.24 + 0.34 * clump) + clump * 0.16 \
        + _flat(_tv(h2b), 3.0) * float(body) * (0.3 + 0.7 * clump) \
        + _grain(res, seed, 647, fine)
    return _pk(T * _gentle(res, seed, 649))


def n_ringlet_pack(res, seed, cell=9.6, r1=0.66, r2=0.34, w=0.17, body=0.24,
                   fine=0.08):
    """[fnb_teal_annulus] NESTED-RINGLET pack: a small concentric ring system
    per cell — two fat hoops and a core dot, packed edge to edge."""
    rl, _th, hv = _polar_cells(res, float(cell), 0.46, 651, 0.0)
    hoop1 = _fat(np.abs(rl - float(r1)), float(w))
    hoop2 = _fat(np.abs(rl - float(r2)), float(w) * 0.82)
    core = np.exp(-((rl * 5.0) ** 2))
    T = 0.13 + hoop1 * (0.30 + 0.28 * _tv(hv)) + hoop2 * 0.24 + core * 0.22 \
        + _ptier(res, 6.4, 653, relief=0.62) * float(body) \
        + _grain(res, seed, 655, fine)
    return _pk(T * _gentle(res, seed, 657))


def n_strata_laminae(res, seed, p=9.2, dash=12.0, warp=6.0, body=0.30, fine=0.09):
    """[fnb_cyan_drift] Sheared LAMINA strata: fat wavy strata at the band
    pitch broken into drifting 8-tier dashes down their length."""
    u, v = _uvrot(res, seed, 661, float(warp))
    ph = u / float(p)
    lam = _fat(np.abs(frac(ph) - 0.5), 0.33)
    gloss = 0.5 + 0.5 * np.cos(6.2831853 * frac(ph))
    seg = np.floor(v / float(dash))
    tier = _tv(h2(np.floor(ph), seg, 663))
    brk = sstep(0.44, 0.12, np.abs(frac(v / float(dash)) - 0.5))
    T = 0.13 + lam * (0.34 + float(body) * tier) * (0.50 + 0.50 * brk) \
        + gloss * 0.14 + _grain(res, seed, 665, fine)
    return _pk(T * _gentle(res, seed, 667))


def n_bowshock_carpet(res, seed, cell=9.8, rad=0.62, w=0.20, body=0.24, fine=0.09):
    """[fnb_gilded_shockfront] Crescent BOW-SHOCK carpet: one small open arc
    per cell, every arc facing the same wind, each dragging a soft wake into
    the lee — a carpet of tiny bow shocks."""
    rl, th, hv = _polar_cells(res, float(cell), 0.50, 671, 0.0)
    head = float(rng(seed, 673).uniform(0, np.pi))
    face = np.cos(th - head)
    arc = _fat(np.abs(rl - float(rad)), float(w)) * sstep(-0.10, 0.55, face)
    wake = sstep(1.30, 0.30, rl) * sstep(0.30, -0.60, face) * 0.7
    T = 0.13 + arc * (0.34 + 0.30 * _tv(hv)) + wake * 0.20 \
        + _ptier(res, 6.6, 675, relief=0.60, ang=head) * float(body) \
        + _grain(res, seed, 677, fine)
    return _pk(T * _gentle(res, seed, 679))


def n_star_felt(res, seed, cell=9.4, sp=0.95, body=0.24, fine=0.08):
    """[fnb_teal_starfield] SPIKED-STAR felt: a PSF star per cell, the hot half
    of the population growing four fat diffraction spikes."""
    rl, th, hv = _polar_cells(res, float(cell), 0.62, 681, 0.0)
    core = np.exp(-((rl * 4.2) ** 2))
    spike = (np.abs(np.cos(2.0 * th)) ** 6) * sstep(1.20, 0.05, rl) \
        * (hv > (1.0 - float(sp) * 0.55)).astype(np.float32)
    halo = sstep(1.05, 0.10, rl) * 0.30
    T = 0.13 + core * (0.30 + 0.30 * _tv(hv)) + spike * 0.30 + halo * 0.22 \
        + _ptier(res, 6.2, 683, relief=0.64) * float(body) \
        + _grain(res, seed, 685, fine)
    return _pk(T * _gentle(res, seed, 687))


def n_lens_streaks(res, seed, cell=9.6, ecc=2.6, body=0.26, fine=0.09):
    """[fnb_violet_galaxy] LENS-STREAK scatter: a tiny edge-on galaxy lozenge
    per cell, each at its own angle — soft glow body, hot core, and a dark
    dust midline cutting it lengthways."""
    # [SPB-FRACTURED-090] orientation spread 2*pi -> +-0.75 rad about one
    # heading. An anisotropic motif at a FREE angle spreads its power right
    # round the spectral ring, so the lattice never builds a peak anywhere and
    # a third of the field falls under the band (measured 0.34). Preferring a
    # heading is also the honest habit of a lensed cluster field.
    rl, th, hv = _polar_cells(res, float(cell), 0.46, 691, 0.0)
    a = float(rng(seed, 699).uniform(0, np.pi)) + (hv - 0.5) * 0.34
    ex = rl * np.cos(th - a)
    ey = rl * np.sin(th - a) * float(ecc)
    d = np.hypot(ex, ey)
    body_ = sstep(1.10, 0.05, d)
    dust = np.exp(-((ey * 3.4) ** 2)) * body_
    core = np.exp(-((d * 4.0) ** 2))
    # [SPB-FRACTURED-090] the tier patch lattice sat at 6.4 px while the
    # lozenges sit at 9.6: two competing in-band fundamentals, and the
    # thin-film LUT intermodulates the pair straight down under the band.
    # Matching the patch pitch to the lozenge pitch leaves ONE peak.
    T = 0.13 + body_ * (0.30 + 0.30 * _tv(hv)) + core * 0.28 - dust * 0.14 \
        + _ptier(res, 9.6, 693, relief=0.66) * float(body) \
        + _grain(res, seed, 695, fine)
    return _pk(T * _gentle(res, seed, 697))


def n_darklane_mesh(res, seed, cell=9.6, c2=6.4, thr=0.28, body=0.24, fine=0.10):
    """[fnb_magenta_rift] DARK-LANE branching mesh: the inverse of the wisp web
    — a net of DARK dust filaments at two scales cut into bright fine
    emission, every bank rim-lit where the lane undercuts it."""
    _f1, e1, i1 = _voro(res, float(cell), 0.44, 701)
    _f2, e2, _i2 = _voro(res, float(c2), 0.48, 705)
    # [SPB-FRACTURED-090] the fine lane web was an equal partner and cost
    # 0.22 of band through the same broad-spectrum route. It is now a faint
    # tributary net, which is the honest dust habit anyway.
    lane = np.maximum(_fat(e1, float(thr)), _fat(e2, float(thr) * 0.62) * 0.42)
    rim = np.clip(_fat(e1, float(thr) * 2.0) - lane, 0.0, 1.0)
    glow = sstep(0.04, 0.46, e1)
    tier = _flat(_tv(h2(np.floor(i1 * 997.0), 0.0, 703)), 3.0)
    T = 0.52 + glow * 0.22 + rim * 0.26 - lane * 0.50 \
        + tier * float(body) + _grain(res, seed, 707, fine)
    return _pk(T * _gentle(res, seed, 709))


def n_cavity_foam(res, seed, cell=9.2, body=0.26, fine=0.09):
    """[fnb_teal_lagoon] CAVITY foam: dark blown bays packed over the whole
    pane, every rim photoevaporation-bright — a foam read as holes, not
    bubbles (the inverse relief of the ringlet pack)."""
    f1, e1, i1 = _voro(res, float(cell), 0.44, 711)
    cav = sstep(1.00, 0.06, f1) ** 1.2
    rim = _fat(np.abs(f1 - 0.62), 0.18)
    tier = _flat(_tv(h2(np.floor(i1 * 997.0), 0.0, 713)), 3.0)
    T = 0.50 + rim * 0.40 - cav * 0.46 * (0.45 + 0.55 * _tv(h2(np.floor(i1 * 997.0), 1.0, 715))) \
        + tier * float(body) + _grain(res, seed, 717, fine)
    return _pk(T * _gentle(res, seed, 719))


def n_ringscale_rows(res, seed, sw=10.4, sh=8.2, body=0.28, fine=0.09):
    """[fnb_violet_annulus] RING-SCALE imbrication: rows of overlapping
    half-ring shingles — an annulus field laid like roof scales, each shingle
    with a fat hoop and a carved lip."""
    u, v = _uvrot(res, seed, 721, 3.0)
    row = np.floor(v / float(sh))
    xo = u + (row % 2) * float(sw) * 0.5
    cu = (frac(xo / float(sw)) - 0.5) * float(sw)
    cy = frac(v / float(sh)) * float(sh)
    d = np.hypot(cu, cy) / (float(sw) * 0.5)
    hoop = _fat(np.abs(d - 0.74), 0.20)
    inner = _fat(np.abs(d - 0.38), 0.16) * 0.7
    tier = _tv(h2(np.floor(xo / float(sw)), row, 723))
    T = 0.13 + hoop * (0.32 + float(body) * tier) + inner * 0.22 \
        + sstep(1.15, 0.30, d) * 0.14 + _grain(res, seed, 725, fine)
    return _pk(T * _gentle(res, seed, 727))


def n_column_tufts(res, seed, p=9.0, tip=10.5, body=0.28, fine=0.09):
    """[fnb_magenta_emission] COLUMNAR tuft field: dense vertical elephant-trunk
    cords at the band pitch, every eroded tip glinting — pillars as a crowd."""
    yy, xx = coords(res)
    wu, _wv = warp_pair(res, seed, 731, 4.0)
    q = (xx + wu) / float(p)
    cord = _fat(np.abs(frac(q) - 0.5), 0.32)
    gloss = 0.5 + 0.5 * np.cos(6.2831853 * frac(q))
    seg = np.floor(yy / float(tip))
    tier = _tv(h2(np.floor(q), seg, 733))
    tipg = np.exp(-(((frac(yy / float(tip)) - 0.18) * 6.5) ** 2)) * cord
    T = 0.13 + cord * (0.30 + float(body) * tier) + gloss * 0.14 + tipg * 0.26 \
        + _grain(res, seed, 735, fine)
    return _pk(T * _gentle(res, seed, 737))


def n_dark_threads(res, seed, p=9.2, dash=13.0, body=0.24, fine=0.10):
    """[fnb_cyan_dustlane] DARK THREAD-DRIFT: dashed DARK dust threads all
    sharing one heading, incised into a bright fine emission lattice — the
    photographic negative of the column tufts."""
    u, v = _uvrot(res, seed, 741, 5.0)
    q = v / float(p)
    lane = _fat(np.abs(frac(q) - 0.5), 0.28)
    seg = np.floor(u / float(dash))
    brk = sstep(0.46, 0.10, np.abs(frac(u / float(dash)) - 0.5))
    d2, h2b = _dots(res, 6.2, 0.86, 743)
    emis = sstep(0.92, 0.16, d2) * (0.35 + 0.65 * _tv(h2b))
    T = 0.52 + emis * 0.26 - lane * brk * 0.48 + lane * (1.0 - brk) * 0.10 \
        + _flat(_tv(h2(np.floor(q), seg, 745)), 3.0) * float(body) \
        + _grain(res, seed, 747, fine)
    return _pk(T * _gentle(res, seed, 749))


def n_pinwheel_lattice(res, seed, cell=9.6, arms=3, twist=3.6, body=0.26,
                       fine=0.08):
    """[fnb_golden_pinwheel] PINWHEEL-KNOT lattice: a tiny three-arm flocculent
    whorl per cell, cores hot, every whorl spun to its own phase."""
    rl, th, hv = _polar_cells(res, float(cell), 0.34, 751, 1.0)
    arm = (0.5 + 0.5 * np.cos(th * float(arms) + rl * float(twist))) ** 2.2
    env = sstep(1.22, 0.08, rl)
    core = np.exp(-((rl * 2.9) ** 2))
    T = 0.13 + env * (0.14 + 0.42 * arm) + core * 0.30 \
        + _tv(hv) * float(body) * (0.26 + 0.74 * env) + _grain(res, seed, 753, fine)
    return _pk(T * _gentle(res, seed, 755))


def n_powder_globules(res, seed, cell=6.8, gcell=10.4, body=0.26, fine=0.07):
    """[fnb_magenta_stardust] POWDER-with-silhouettes: an ultra-fine powder
    lattice with small dark Bok globules floating in front of it on a coarser
    lattice — the only two-population engine in the module."""
    d1, h1 = _dots(res, float(cell), 0.90, 761)
    d2, h2b = _dots(res, float(gcell), 0.58, 765)
    powder = sstep(0.90, 0.12, d1) * (0.30 + 0.70 * _tv(h1))
    glob = sstep(0.72, 0.20, d2) * (h2b > 0.42).astype(np.float32)
    # [SPB-FRACTURED-090] the globule silhouettes are the identity of this
    # id, so they stay -- but at 0.34 they were an equal second population and
    # the pair intermodulated 0.29 of the power under the band. Demoted to a
    # true foreground accent (they read stronger, not weaker, because the
    # powder behind them is no longer fighting them).
    T = 0.16 + powder * 0.50 - glob * 0.22 \
        + _flat(_tv(h1), 3.0) * float(body) + _grain(res, seed, 767, fine)
    return _pk(T * _gentle(res, seed, 769))


def n_shockring_carpet(res, seed, cell=12.6, p=9.0, body=0.24, fine=0.08):
    """[fnb_cyan_shockwave] SHOCK-RING interference carpet: one blast per
    lattice cell, its fronts at the band pitch, neighbouring blasts
    interfering where their envelopes overlap."""
    rl, _th, hv = _polar_cells(res, float(cell), 0.44, 771, 0.0)
    # [SPB-FRACTURED-090] the per-blast ENVELOPE is deleted, not shrunk. An
    # envelope is a SECOND periodic field at the blast pitch, i.e. far coarser
    # than the fronts it modulates, so it always lands under r=64 whatever its
    # cell size -- it was the whole of this id's 0.32 leak. The blasts now
    # fill their cells and carry a per-blast PHASE instead: neighbouring
    # wavefronts meet out of step at the cell seams, which is what an
    # interfering shock carpet actually looks like.
    dist = rl * float(cell) * 0.62
    ph = dist / float(p) + hv
    front = _fat(np.abs(frac(ph) - 0.42), 0.24)
    ramp = np.clip(frac(ph), 0.0, 1.0) ** 2
    env = 1.0
    # [SPB-FRACTURED-090] blast cell 19 -> 12.6 px at GEN and the envelope
    # demoted. A per-blast ENVELOPE is a second, much coarser periodic field
    # riding under the fronts; at cell 19 its fundamental sat at r~34, i.e.
    # squarely in the sub-band, and it took a third of the module's worst
    # leak (0.34) with it.
    T = 0.14 + front * 0.46 * (0.45 + 0.55 * _tv(hv)) + ramp * 0.12 \
        + _ptier(res, 6.6, 773, relief=0.60) * float(body) \
        + _grain(res, seed, 775, fine)
    return _pk(T * _gentle(res, seed, 777))


def n_gauze_weave(res, seed, p=9.4, dang=0.42, drape=5.0, body=0.24, fine=0.08):
    """[fnb_gilded_veil] GAUZE cross-weave: two draped thread families crossing
    at a shallow angle, their crossings brightest — a woven veil of gold."""
    yy, xx = coords(res)
    a = float(rng(seed, 781).uniform(0, np.pi))
    u1, _ = rot((yy, xx), a)
    u2, _ = rot((yy, xx), a + float(dang))
    wu, _wv = warp_pair(res, seed, 783, float(drape))
    A = _fat(np.abs(frac((u1 + wu) / float(p)) - 0.5), 0.30)
    B = _fat(np.abs(frac((u2 - wu) / (float(p) * 1.12)) - 0.5), 0.30)
    tA = _tv(h2(np.floor((u1 + wu) / float(p)), 0.0, 785))
    tB = _tv(h2(np.floor((u2 - wu) / (float(p) * 1.12)), 1.0, 787))
    T = 0.13 + A * (0.24 + float(body) * tA) + B * (0.22 + float(body) * tB) \
        + A * B * 0.26 + _grain(res, seed, 789, fine)
    return _pk(T * _gentle(res, seed, 791))


def n_rift_maze(res, seed, s1=1.3, s2=2.7, iters=10, body=0.22, fine=0.09):
    """[fnb_teal_rift] Reaction-diffusion RIFT maze: dark dust channels
    wandering through bright teal emission, banks rim-lit. The reactor is
    de-drifted at the band edge — a blur-difference reactor has UNIT gain at
    DC, so the whole low-frequency mountain of its seed survives otherwise."""
    x = _turing(res, seed, 793, float(s1), float(s2), int(iters), 110)
    x = n01(_flat(x, 2.4))
    chan = 1.0 - sstep(0.40, 0.60, x)
    lip = n01(np.abs(cv2.Sobel(gauss(chan, 1.1), cv2.CV_32F, 1, 0, ksize=3))
              + np.abs(cv2.Sobel(gauss(chan, 1.1), cv2.CV_32F, 0, 1, ksize=3)))
    T = 0.58 - chan * 0.44 + lip * 0.28 \
        + _ptier(res, 6.8, 795, relief=0.62) * float(body) \
        + _grain(res, seed, 797, fine)
    return _pk(T * _gentle(res, seed, 799))


def n_orb_pack(res, seed, cell=9.4, rad=0.30, halo=0.78, body=0.26, fine=0.08):
    """[fnb_violet_starglow] ORB-GLOW pack: dense bokeh suns — a soft glow orb
    per cell inside its own faint halo hoop, packed edge to edge."""
    rl, _th, hv = _polar_cells(res, float(cell), 0.48, 801, 0.0)
    orb = sstep(float(rad) * 1.9, float(rad) * 0.2, rl)
    hoop = _fat(np.abs(rl - float(halo)), 0.16) * 0.7
    T = 0.13 + orb * (0.34 + 0.32 * _tv(hv)) + hoop * 0.24 \
        + _ptier(res, 6.0, 803, relief=0.62) * float(body) \
        + _grain(res, seed, 805, fine)
    return _pk(T * _gentle(res, seed, 807))


ENGINES = {
    "n_billow_turb": n_billow_turb, "n_wisp_web": n_wisp_web,
    "n_spiral_pave": n_spiral_pave, "n_cluster_granules": n_cluster_granules,
    "n_ringlet_pack": n_ringlet_pack, "n_strata_laminae": n_strata_laminae,
    "n_bowshock_carpet": n_bowshock_carpet, "n_star_felt": n_star_felt,
    "n_lens_streaks": n_lens_streaks, "n_darklane_mesh": n_darklane_mesh,
    "n_cavity_foam": n_cavity_foam, "n_ringscale_rows": n_ringscale_rows,
    "n_column_tufts": n_column_tufts, "n_dark_threads": n_dark_threads,
    "n_pinwheel_lattice": n_pinwheel_lattice, "n_powder_globules": n_powder_globules,
    "n_shockring_carpet": n_shockring_carpet, "n_gauze_weave": n_gauze_weave,
    "n_rift_maze": n_rift_maze, "n_orb_pack": n_orb_pack,
}
ENGINES = {k: _lowcut(v) for k, v in ENGINES.items()}


# ════════════════════════════════════════════════════════════════════════════
# CATEGORY-SPECIFIC MACRO KIND — core (kept for contract stability; no pass-2
# recipe uses it — poster macros were the disease this pass cured).
# ════════════════════════════════════════════════════════════════════════════

def m_core(r, mp, seed, K):
    """Galactic core: brilliant nucleus with exponential falloff."""
    yy, xx = K.coords(r)
    cx, cy = float(mp.get("cx", 0.5)), float(mp.get("cy", 0.5))
    dx = (xx / r) - cx
    dy = (yy / r) - cy
    dist = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)
    M = np.exp(-dist * float(mp.get("falloff", 3.0))) * 1.15 + 0.10
    jet = float(mp.get("jet", 0.0))
    if jet > 0.0:
        ja = float(mp.get("jet_angle", 0.0))
        ca, sa = np.cos(ja), np.sin(ja)
        along = dx * ca + dy * sa
        across = -dx * sa + dy * ca
        beam = np.exp(-((across / 0.06) ** 2)) * np.clip(1.2 - np.abs(along), 0.0, 1.0)
        M = M + beam * jet
    M = np.clip(M, 0.0, 1.0)
    sect = float(mp.get("sectors", 6.0))
    D = K.n01(K.h2(np.floor((ang / np.pi + 1.0) * sect), np.floor(dist * 4.0), 53)
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
# RECIPES — 20 finishes, ids fnb_*, seeds 1080-1099 (UNCHANGED ids/seeds).
# [pass 2, 2026-08-02] FIELD standard dials: vd tight, tmod <=0.12, ambient
# 0.12, sparkle ~0.12, gray <=0.35; unique macro salt per recipe (catlib
# worley jitter is salt-driven, seed-blind — shared salts = identical macro
# domains = descriptor collisions, the FROST pass-2 discovery). Verify data:
# _fractured_triage/verify_nebula.json.
# ════════════════════════════════════════════════════════════════════════════

EMISSION_CLOUDS = {
 # [pass2] rim-lit lobe poster (band 0.14 class) -> micro billow turbulence
 "fnb_violet_billows": dict(name="Violet Billows", engine="n_billow_turb",
    eargs=dict(cell=7.761, c2=6.2, lift=1.1, body=0.264, fine=0.1, lowcut=1.8, soft=0.6),
    seed=1080, lut=(360.0, 980.0, 1.0, 1.3, 0.7), val=0.27,
    hues=[0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.785, 0.725, 0.817, 0.697, 0.93, 0.66], hspan=0.055, satboost=0.774,
    macro=("clouds", dict(base=8, salt=1080)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4),
    desc="Violet emission billows boiling at micro scale, every roll rim-bright. A FRACTURED NEBULA finish."),
 # [pass2] 3-shell remnant poster -> curved filament wisp web
 "fnb_magenta_remnant": dict(name="Magenta Remnant", engine="n_wisp_web",
    eargs=dict(cell=8.836, thr=0.28, halo=1.6, body=0.296, fine=0.09, lowcut=1.8, soft=0.6),
    seed=1081, lut=(370.0, 960.0, 1.0, 1.3, 3.9), val=0.25,
    hues=[0.88, 0.88, 0.88, 0.88, 0.88, 0.88, 0.88, 0.88, 0.88, 0.88, 0.91, 0.85, 0.942, 0.822, 0.99, 0.785], hspan=0.055, satboost=0.774,
    macro=("clouds", dict(base=7, salt=1081)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.5, mfloor=10.0),
    desc="A magenta remnant web — curved shock wisps meshing the whole dark pane. A FRACTURED NEBULA finish."),
 # [pass2] ONE grand spiral poster -> pave of hundreds of tiny spirals
 "fnb_cyan_spiral": dict(name="Cyan Spiral", engine="n_spiral_pave",
    eargs=dict(cell=8.428, arms=2, twist=5.0, body=0.169, fine=0.09, lowcut=1.8, soft=0.6),
    seed=1082, lut=(458.6, 841.4, 0.95, 1.3, 5.6), val=0.25,
    hues=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.53, 0.47, 0.562, 0.442, 0.7, 0.64], hspan=0.055, satboost=0.774,
    macro=("continents", dict(base=5, cells=5.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4, rswing=1.4),
    desc="A crowd of tiny cyan spiral eddies paving space — every whorl its own galaxy. A FRACTURED NEBULA finish."),
 # [pass2] King-profile blob poster -> worley-clumped granule scatter
 "fnb_golden_cluster": dict(name="Golden Cluster", engine="n_cluster_granules",
    eargs=dict(cell=5.504, ccell=9.8, body=0.182, fine=0.08, lowcut=1.8, soft=0.6),
    seed=1083, lut=(471.8, 828.2, 1.0, 1.25, 0.8), val=0.25,
    hues=[0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.13, 0.07, 0.162, 0.042, 0.165, 0.045], hspan=0.055, satboost=1.053,
    macro=("clouds", dict(base=7, salt=1083)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, gray=0.30, mswing=1.7, mfloor=10.0, ccboost=1.4),
    desc="Golden star granules clumping in clusters across the dark, blue strays powdered through. A FRACTURED NEBULA finish."),
 # [pass2] inclined ring-system poster -> packed nested ringlets
 "fnb_teal_annulus": dict(name="Teal Annulus", engine="n_ringlet_pack",
    eargs=dict(cell=8.483, r1=0.66, r2=0.34, w=0.17, body=0.288, fine=0.08, lowcut=0.0, soft=0.9),
    seed=1084, lut=(370.0, 760.0, 1.0, 1.3, 4.0), val=0.25,
    hues=[0.47, 0.47, 0.47, 0.47, 0.47, 0.47, 0.47, 0.47, 0.47, 0.47, 0.5, 0.44, 0.532, 0.412, 0.66, 0.6], hspan=0.055, satboost=0.774,
    macro=("clouds", dict(base=9, salt=1084)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4),
    desc="Teal ring systems packed small — nested hoops and cores tiling the pane. A FRACTURED NEBULA finish."),
}

STARFIELDS_SHOCKS = {
 # [pass2] layered strata poster -> dashed micro strata laminae
 "fnb_cyan_drift": dict(name="Cyan Drift", engine="n_strata_laminae",
    eargs=dict(p=8.648, dash=11.28, warp=6.0, body=0.36, fine=0.09, lowcut=2.6, soft=0.35),
    seed=1085, lut=(428.0, 692.0, 0.95, 1.3, 3.2), val=0.25,
    hues=[0.52, 0.52, 0.52, 0.52, 0.52, 0.52, 0.52, 0.52, 0.52, 0.52, 0.55, 0.49, 0.582, 0.462, 0.715, 0.655], hspan=0.055, satboost=0.774,
    macro=("drift", dict(angle=0.3, salt=1085)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.3, rswing=1.4),
    desc="Cyan gas strata sheared into drifting micro laminae, dash-broken by the wind. A FRACTURED NEBULA finish."),
 # [pass2] single bow shock poster -> carpet of small crescent shocks + wakes
 "fnb_gilded_shockfront": dict(name="Gilded Shockfront", engine="n_bowshock_carpet",
    eargs=dict(cell=9.8, rad=0.62, w=0.2, body=0.24, fine=0.09, lowcut=0.0, soft=0.9),
    seed=1086, lut=(380.0, 910.0, 1.0, 1.3, 1.1), val=0.25,
    hues=[0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.13, 0.07, 0.162, 0.042, 0.165, 0.045], hspan=0.055, satboost=1.003,
    macro=("continents", dict(base=3, cells=4.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, gray=0.25, mswing=1.6, mfloor=10.0, ccboost=1.4),
    desc="A gilded carpet of small bow shocks all driving one way, wakes smearing behind. A FRACTURED NEBULA finish."),
 # [pass2] open-cluster poster -> uniform spiked-star felt
 "fnb_teal_starfield": dict(name="Teal Starfield", engine="n_star_felt",
    eargs=dict(cell=8.084, sp=0.95, body=0.348, fine=0.08, lowcut=1.8, soft=0.9),
    seed=1087, lut=(405.1, 724.9, 1.0, 1.3, 1.6), val=0.28,
    hues=[0.46, 0.46, 0.46, 0.46, 0.46, 0.46, 0.46, 0.46, 0.46, 0.46, 0.49, 0.43, 0.522, 0.402, 0.665, 0.605], hspan=0.055, satboost=0.774,
    macro=("domains", dict(cells=11, salt=1087)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.6, mfloor=10.0, rswing=1.4),
    desc="A teal star felt — thousands of pinpoint suns, the hot ones spiking cross-rays. A FRACTURED NEBULA finish."),
 # [pass2] barred-spiral poster -> tiny edge-on lens streak scatter
 "fnb_violet_galaxy": dict(name="Violet Galaxy", engine="n_lens_streaks",
    eargs=dict(cell=7.875, ecc=3.2, body=0.464, fine=0.09, lowcut=0.0, soft=0.9),
    seed=1088, lut=(360.0, 970.0, 1.0, 1.3, 4.0), val=0.25,
    hues=[0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.795, 0.735, 0.827, 0.707, 0.94, 0.67], hspan=0.085, satboost=0.774,
    # [SPB-FRACTURED-090d 2026-08-02] The MEASURED FRONTIER below is RETIRED.
    # This id was the module's documented sub-0.70 exception (band 0.677)
    # because a 1.00-saturation violet clips hard after art_work's luma
    # renormalisation, and the clip was eating the lens-streak micro-detail.
    # Backing satboost off the clip (the module-wide satA 0.99 -> 0.80 pass)
    # and restoring this id's original 0.085 hue window takes the clip out:
    # band 0.677 -> 0.71+, ac 0.665 -> 0.676, pk 0.418 -> 0.431,
    # fine 8.9 -> 13.4, hue bins 7 -> 8. It now CLEARS the 0.70 gate on its own
    # — no exception needed. Geometry untouched (eargs/seed/lut identical).
    macro=("clouds", dict(base=8, salt=1088)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.5, mfloor=10.0, ccboost=1.4, rswing=1.4),
    desc="Hundreds of tiny violet galaxies seen edge-on — glowing lozenges, dark dust midlines. A FRACTURED NEBULA finish."),
 # [pass2] lane-web poster -> dark branching dust net over bright glow
 "fnb_magenta_rift": dict(name="Magenta Rift", engine="n_darklane_mesh",
    eargs=dict(cell=9.539, c2=6.0, thr=0.26, body=0.101, fine=0.1, lowcut=2.6, soft=0.0),
    seed=1089, lut=(370.0, 760.0, 1.0, 1.32, 4.8), val=0.35,
    hues=[0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.93, 0.87, 0.962, 0.842, 0.01, 0.805], hspan=0.055, satboost=0.774,
    # [SPB-FRACTURED-090d 2026-08-02] This id leaned hardest on the channel
    # clipping that a satA-0.99 magenta produces after art_work's luma
    # renormalisation: taking the module off the clip (satA -> 0.80) dropped
    # its lag-1 coherence to 0.527, below the 0.55 gate, on a BYTE-IDENTICAL
    # field. It has the band surplus to pay for real coherence instead of
    # clipped coherence — vd 0.96/1.06 -> 0.62/1.42 gives ac 0.567 at
    # band 0.819 (gate 0.70). Margin, not a pass-by-rounding.
    macro=("drift", dict(angle=1.1, salt=1089)), vd=(0.62, 1.42), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4),
    desc="A magenta rift net — dark dust filaments branching over glowing micro emission. A FRACTURED NEBULA finish."),
}

GALAXIES_RIFTS = {
 # [pass2] one carved lagoon poster -> packed dark-cavity foam
 "fnb_teal_lagoon": dict(name="Teal Lagoon", engine="n_cavity_foam",
    eargs=dict(cell=7.912, body=0.169, fine=0.09, lowcut=1.8, soft=0.9),
    seed=1090, lut=(370.0, 960.0, 1.0, 1.3, 4.1), val=0.26,
    hues=[0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.48, 0.42, 0.512, 0.392, 0.655, 0.595], hspan=0.055, satboost=0.774,
    macro=("clouds", dict(base=7, salt=1090)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4),
    desc="Teal lagoon foam — dark blown bays packed tight, every rim glowing. A FRACTURED NEBULA finish."),
 # [pass2] edge-on plane poster -> overlapping ring-scale shingle rows
 "fnb_violet_annulus": dict(name="Violet Annulus", engine="n_ringscale_rows",
    eargs=dict(sw=8.944, sh=7.052, body=0.336, fine=0.09, lowcut=2.6, soft=0.6),
    seed=1091, lut=(360.0, 760.0, 1.05, 1.3, 3.2), val=0.25,
    hues=[0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.765, 0.795, 0.735, 0.827, 0.707, 0.95, 0.68], hspan=0.055, satboost=0.774,
    macro=("clouds", dict(base=8, salt=1091)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.5, mfloor=10.0),
    desc="Violet ring scales shingled row on row — an annulus field laid like armor. A FRACTURED NEBULA finish."),
 # [pass2] 4 giant pillars poster -> dense columnar tuft field
 "fnb_magenta_emission": dict(name="Magenta Emission", engine="n_column_tufts",
    eargs=dict(p=9.72, tip=10.5, body=0.118, fine=0.09, lowcut=1.8, soft=0.6),
    seed=1092, lut=(370.0, 940.0, 0.95, 1.32, 0.8), val=0.25,
    hues=[0.875, 0.875, 0.875, 0.875, 0.875, 0.875, 0.875, 0.875, 0.875, 0.875, 0.905, 0.845, 0.937, 0.817, 0.985, 0.78], hspan=0.055, satboost=0.774,
    macro=("clouds", dict(base=9, salt=1092)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4, rswing=1.3),
    desc="Magenta emission tufts rising in thousands of small columns, tips star-lit. A FRACTURED NEBULA finish."),
 # [pass2] ONE great dust river poster -> dashed dark thread lanes
 "fnb_cyan_dustlane": dict(name="Cyan Dust Lane", engine="n_dark_threads",
    eargs=dict(p=9.2, dash=13.0, body=0.226, fine=0.1, lowcut=0.0, soft=0.9),
    seed=1093, lut=(360.0, 760.0, 1.0, 1.3, 1.6), val=0.26,
    hues=[0.51, 0.51, 0.51, 0.51, 0.51, 0.51, 0.51, 0.51, 0.51, 0.51, 0.54, 0.48, 0.572, 0.452, 0.71, 0.65], hspan=0.055, satboost=0.774,
    macro=("clouds", dict(base=8, salt=1093)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.5, mfloor=10.0),
    desc="Cyan glow crossed by dashed dark dust threads, all drifting one way. A FRACTURED NEBULA finish."),
 # [pass2] face-on pinwheel poster -> lattice of tiny 3-arm whorls
 "fnb_golden_pinwheel": dict(name="Golden Pinwheel", engine="n_pinwheel_lattice",
    eargs=dict(cell=9.024, arms=3, twist=3.6, body=0.221, fine=0.08, lowcut=3.6, soft=0.9),
    seed=1094, lut=(414.2, 725.8, 1.0, 1.28, 4.0), val=0.25,
    hues=[0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.13, 0.07, 0.162, 0.042, 0.165, 0.045], hspan=0.055, satboost=1.003,
    macro=("domains", dict(cells=5, salt=1094)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, gray=0.25, mswing=1.8, mfloor=10.0, ccboost=1.4),
    desc="A golden lattice of tiny pinwheel whorls, every core burning. A FRACTURED NEBULA finish."),
}

RINGS_STARGLOW = {
 # [pass2] core-glow powder poster -> uniform powder + dark Bok silhouettes
 "fnb_magenta_stardust": dict(name="Magenta Stardust", engine="n_powder_globules",
    eargs=dict(cell=5.723, gcell=9.8, body=0.159, fine=0.07, lowcut=1.8, soft=0.9),
    seed=1095, lut=(433.9, 696.1, 1.0, 1.3, 0.8), val=0.28,
    hues=[0.89, 0.89, 0.89, 0.89, 0.89, 0.89, 0.89, 0.89, 0.89, 0.89, 0.92, 0.86, 0.952, 0.832, 0, 0.795], hspan=0.055, satboost=0.774,
    macro=("clouds", dict(base=9, salt=1095)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.5, mfloor=10.0),
    desc="Magenta stardust powder with small dark globules adrift in front. A FRACTURED NEBULA finish."),
 # [pass2] one caged blast poster -> interfering sharp shock-ring carpet
 "fnb_cyan_shockwave": dict(name="Cyan Shockwave", engine="n_shockring_carpet",
    eargs=dict(cell=26.456, p=9.0, body=0.505, fine=0.08, lowcut=3.6, soft=0.9),
    seed=1096, lut=(396.0, 724.0, 1.0, 1.3, 0.8), val=0.25,
    hues=[0.495, 0.495, 0.495, 0.495, 0.495, 0.495, 0.495, 0.495, 0.495, 0.495, 0.525, 0.465, 0.557, 0.437, 0.695, 0.635], hspan=0.055, satboost=0.774,
    macro=("continents", dict(base=5, cells=5.0)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.5, mfloor=10.0, ccboost=1.4),
    desc="A carpet of small cyan shockwaves — sharp blast rings interfering everywhere. A FRACTURED NEBULA finish."),
 # [pass2] one swirl veil poster -> two-family gauze weave
 "fnb_gilded_veil": dict(name="Gilded Veil", engine="n_gauze_weave",
    eargs=dict(p=8.084, dang=0.42, drape=5.0, body=0.156, fine=0.08, lowcut=2.6, soft=0.9),
    seed=1097, lut=(539.0, 751.0, 0.95, 1.28, 3.4), val=0.26,
    hues=[0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.135, 0.075, 0.167, 0.047, 0.17, 0.05], hspan=0.055, satboost=0.774,
    macro=("clouds", dict(base=7, salt=1097)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.7, mfloor=10.0, rswing=1.4),
    desc="A gilded gauze — two soft gold thread families woven through the dark. A FRACTURED NEBULA finish."),
 # [pass2] crosshatch lane poster -> reaction-diffusion rift maze
 "fnb_teal_rift": dict(name="Teal Rift", engine="n_rift_maze",
    eargs=dict(s1=1.118, s2=2.322, iters=10, body=0.319, fine=0.09, lowcut=1.0, soft=0.9),
    seed=1098, lut=(421.3, 888.7, 1.0, 1.3, 3.2), val=0.26,
    hues=[0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.48, 0.42, 0.512, 0.392, 0.655, 0.595], hspan=0.055, satboost=0.774,
    macro=("drift", dict(angle=0.7, salt=1098)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, mswing=1.4, rswing=1.3),
    desc="A teal rift maze — dark dust channels crazing bright emission edge to edge. A FRACTURED NEBULA finish."),
 # [pass2] few hero suns poster -> dense bokeh orb-glow pack
 "fnb_violet_starglow": dict(name="Violet Starglow", engine="n_orb_pack",
    eargs=dict(cell=8.084, rad=0.3, halo=0.78, body=0.377, fine=0.08, lowcut=1.8, soft=0.9),
    seed=1099, lut=(360.0, 980.0, 1.0, 1.3, 0.8), val=0.25,
    hues=[0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.755, 0.785, 0.725, 0.817, 0.697, 0.93, 0.66], hspan=0.055, satboost=1.003,
    macro=("clouds", dict(base=8, salt=1099)), vd=(0.96, 1.06), tmod=0.0,
    kw=dict(ambient=0.05, ambient_sigma=40, floor=0.10, sparkle=0.05, gray=0.25, mswing=1.5, mfloor=10.0, ccboost=1.5),
    desc="Violet starglow bokeh — hundreds of soft suns and halo hoops packed deep. A FRACTURED NEBULA finish."),
}

GROUPS = {
    "EMISSION CLOUDS": EMISSION_CLOUDS,
    "STARFIELDS & SHOCKS": STARFIELDS_SHOCKS,
    "GALAXIES & RIFTS": GALAXIES_RIFTS,
    "RINGS & STARGLOW": RINGS_STARGLOW,
}

KIT = catlib.CategoryKit(engines=ENGINES, groups=GROUPS, tag="fractured-nebula",
                         extra_macro={"core": m_core, "clouds": m_clouds,
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
 "fnb_cyan_dustlane": +0.0115,
 "fnb_cyan_shockwave": -0.0274,
 "fnb_gilded_shockfront": +0.0192,
 "fnb_gilded_veil": -0.0094,
 "fnb_golden_cluster": -0.0122,
 "fnb_magenta_emission": +0.0151,
 "fnb_magenta_remnant": +0.0118,
 "fnb_magenta_rift": +0.0095,
 "fnb_magenta_stardust": +0.0230,
 "fnb_teal_annulus": -0.0111,
 "fnb_teal_rift": -0.0103,
 "fnb_teal_starfield": -0.0147,
 "fnb_violet_annulus": -0.0277,
 "fnb_violet_billows": -0.0119,
 "fnb_violet_galaxy": -0.0122,
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
 "fnb_cyan_shockwave": -0.0440,
 "fnb_cyan_spiral": -0.0629,
}

for _fid, _off in _ACCFIX.items():
    _r = ALL[_fid]
    _r["hues"] = _r["hues"][:-2] + [round((_h + _off) % 1.0, 4)
                                    for _h in _r["hues"][-2:]]
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
