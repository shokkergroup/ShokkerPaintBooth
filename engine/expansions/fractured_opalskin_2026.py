# -*- coding: utf-8 -*-
"""FRACTURED OPALSKIN (2026-08-03) — 25 recognizable-pattern crush-law flips.

THE MISSION (owner on-track discovery, 2026-08-02 night session): the
color-flip color is a property of DARKNESS LEVEL, not paint hue. Under a
near-uniform metallic "night-carrier" spec (the FRACTURED SOULS contract:
M~242 amplifier / G~30 laser-pin aperture / B~246 power supply), each
distinct dark shade crosses from diffuse-dominant to specular-dominant at a
DIFFERENT viewing angle. Many quantized dark shades at fine scale = multiple
flip colors firing simultaneously, cascading in motion (MIP blending at
distance adds intermediate states). So this module renders RECOGNIZABLE
MATERIAL PATTERNS — snake skins, diamond plates, carbon weaves, chainmail,
damascus, houndstooth... — where the pattern is the STRUCTURE and a terraced
dark-value LADDER is the paint: every element face sits on one of 8 quantized
art-luma rungs, deep black pits between elements, a sparse worn-bright vein
population on top. Six rainbow ids run the same law with full-hue-wheel
per-cell anchors ("go totally crazy" lane): the rainbow read comes from the
LADDERS, not from bright candy.

[SPEC-MIRROR EXEMPTION — CRUSH LAW 2026-08-03]
ALL 25 ids of this module ship a NEAR-UNIFORM night-carrier spec instead of a
spec that mirrors the paint geometry:
  fsk_snakeskin, fsk_diamond_plate, fsk_carbon_weave, fsk_dragon_scale,
  fsk_chainmail, fsk_stingray, fsk_croc_hide, fsk_damascus, fsk_hex_mesh,
  fsk_knurl, fsk_herringbone, fsk_houndstooth, fsk_basket_weave,
  fsk_chesterfield, fsk_feather_mantle, fsk_scale_mail, fsk_spider_silk,
  fsk_circuit_trace, fsk_mosaic_glass, fsk_prism_shatter, fsk_oilslick_weave,
  fsk_aurora_veil, fsk_opal_pave, fsk_spectrum_scales, fsk_nebula_prism
REASON: the flip mechanism REQUIRES a flat spec. The paint's quantized dark
ladder does the angular work — each rung crosses diffuse->specular at its own
angle under one uniform metallic carrier (measured reference
fs_core_crimson spec @512: M/G/B medians 242/30/246, std 0). Any spec texture
would re-couple rungs to local spec values and collapse the cascade into one
flip angle. Dither <=4 std; optional two-population G (+8 rougher in pits,
median unchanged) keeps pit floors from reading as glass while staying inside
the +-6/+-10/+-6 tolerance of the reference. Verified per finish by
_fractured_triage/verify_guard.py (crush mode: smed/sstd columns).

ARCHETYPE LEDGER (25 ids, no two structures alike — element shape / pitch at
GEN / overlap law all distinct; every scale-family id differs in geometry):
  fsk_snakeskin       pointed-oval keeled scales   7.8x5.9 offset rows, tip-down imbrication
  fsk_diamond_plate   raised lozenge treadplate    8.6 parity grid, alternating lozenge pairs
  fsk_carbon_weave    2x2 twill carbon tows        5.2 tow, over-under floats + resin pits
  fsk_dragon_scale    flat-top pentagon scales     8.8x6.8 rows, 3-facet keel + rim light arc
  fsk_chainmail       interlocked ring rows        8.4 pitch, euro rows, odd rows over even
  fsk_stingray        shagreen granule pave        6.6 dots + 15 px sparse crown beads
  fsk_croc_hide       irregular rect scutes        8.6x6.6 jittered grid, deep creases
  fsk_damascus        folded-steel contour bands   7.2 laminar pitch, etched band parity
  fsk_hex_mesh        honeycomb walls dark         5.0 axial hex, laddered domed floors
  fsk_knurl           machined diamond knurl       7.4 crossed +-32 deg, 4-facet pyramids
  fsk_herringbone     chevron twill dashes         6.2 rib / 12 col, direction flips per column
  fsk_houndstooth     2-2 block twill check        4.8 thread, true warp/weft block coloring
  fsk_basket_weave    2-strand rattan blocks       4.6 strip / 9.2 block, tucked ends
  fsk_chesterfield    buttoned tufted leather      8.8 diamond grid, fold creases + buttons
  fsk_feather_mantle  barbed feather shingles      6.2x8.7 tall rows, rachis + barb comb
  fsk_scale_mail      half-moon lamellae           7.4x5.6 wide rows, crescent underline shadow
  fsk_spider_silk     orb-web mesh cells           8.2 cells over a 5.4 silk granule pave
  fsk_circuit_trace   PCB traces/vias/pads         6.6 lane pitch, dashed copper on dark mask
  fsk_mosaic_glass    grouted micro-tesserae       7.3 squarish tiles, bevel terrace + glints
  fsk_prism_shatter   elongated glass shards       6.6 aniso voronoi (0.93/1.18), tilt facets, lit slivers
  fsk_oilslick_weave  spectral satin floats        6.3 tow, 5-step interlace dimples
  fsk_aurora_veil     combed spectral curtains     6.9 strand, sine-swayed folds, ordered wheel
  fsk_opal_pave       black-opal potch + fire     6.4 grain in 20 px gated play-of-color patches
  fsk_spectrum_scales rhombic snake-gradient       8.8 45-deg diamonds, wheel walks the diagonal
  fsk_nebula_prism    terraced spectral cells      8.4 voronoi, 3 concentric facet terraces

THE CRUSH-LAW LADDER (verified by verify_guard crush gates, seed=1234 @512):
  * engines emit ART-LUMA TARGET fields directly; a per-recipe WALK map
    (_walkmap) inverts the thin-film LUT's steepest quasi-monotone luma
    stretch, so terraces land at authored luma EXACTLY (LUT nonlinearity
    cannot merge rungs). T = (idx+0.5)/1023 keeps the round trip exact.
  * 8 rungs _LAD 0.082..0.464 art luma (bin-CENTER aligned under the
    capped 0.85 crush scale - off-center rungs alias onto histogram bin
    boundaries and split their peaks), pits 0.035, veins 0.985; after the
    paint crush (val 0.30 -> x2.4 gain) that lands median <=0.32, pits
    (<0.06) 3-30%, veins (>0.65) 0.5-8%, >=6 terraced histogram levels.
  * rung assignment is CHECKER-MIXED (_rung): neighbouring cells draw from
    opposite ladder halves, which pushes the tier field's power to the
    lattice fundamental instead of DC (the flat-per-cell sub-band leak the
    FROST pass measured at 0.36) — quantization survives, clumping dies.
  * one dominant pitch per engine, 4.7-11.2 px at GEN (band r58-r85 @512),
    every packed-unit pattern on its OWN pitch (pair-cosine law); fat pit
    seams at the pitch; NO fbm luma, NO smooth macro value gradients
    (vd 0.98/1.03, tmod=0 everywhere); `soft` 0.4-0.7 trims edge ringing.
  * hue rides the HERO WINDOW only (hspan half-width, wrap-safe % 1.0
    ladders): named ids get 16-rung within-family fans, the 6 rainbow ids get
    the 16-anchor wheel picked per ELEMENT by a hires domain map that
    REBUILDS the engine's own lattice at GEN (perfect cell alignment, no
    192-res patch camo) — spectrum from hue anchors, never from satboost
    (<=0.95, chroma measured).

Contract: install_into_engine(registry) as every sibling; (spec_fn, paint_fn)
pairs manufactured by an OpalskinKit subclass of catlib.CategoryKit (paint =
catlib art pipeline; spec = the uniform night carrier above). Determinism:
catlib.rng (np.random.default_rng) + zlib.crc32 salts — never hash(str).
GROUPS key "FRACTURED OPALFIRE" (one category with the sibling fof_ module;
the parent merges them in the UI). Per-finish numbers:
_fractured_triage/guard_opalskin.json; UN-NORMALIZED contact sheet:
_fractured_triage/resheet_opalskin.png; build log:
_fractured_triage/opalskin_build.jsonl.
"""
from __future__ import annotations

import zlib
from functools import lru_cache

import cv2
import numpy as np

from engine.expansions import fractured_catlib_2026 as catlib
from engine.expansions.fractured_catlib_2026 import (
    coords, frac, gauss, h2, n01, rng, rot, sstep, thinfilm_lut,
)

# ── crush-law constants (art-luma space; see header) ────────────────────────
# [round 2, measured] _PIT is the resting canvas; pit LANES blend to 0.0 so
# the `soft` blur cannot lift a 1-2 px core back over the pit gate. _VEIN
# 0.93 -> 0.985 and full-strength blends: the vein population was eroded to
# zero by k<1 blends x soft blur x the crush scale. Rung spacing 0.0514 so
# the 64-bin histogram keeps a clear gap bin between terraces.
_PIT = 0.035
_VEIN = 1.0
# [OWNER RAMP MANDATE 2026-08-03 pass 2] "very bright to near black, all
# across the spectrum — like a color ramp gradient." Ladder extended from the
# dark half [0.083,0.450] to the FULL range, ends double-weighted (25% of
# rung area darkest + 25% brightest). Crush 0.85 -> 0.93 in mk; the final-res
# snap anchors below are re-derived from THIS array (single source).
_LAD = np.float32([0.045, 0.045, 0.227, 0.409, 0.591, 0.773, 0.955, 0.955])
_ZOOM = 1.6           # default-scale bake: 1/1.6 center crop of WORK — owner
                      # "defaults too small"; zone scale-down recovers fine

# night-carrier spec contract (measured fs_core_crimson @512: 242/30/246)
_SPEC_M = 242.0
_SPEC_G = 30.0
_SPEC_B = 246.0
_SPEC_G_PIT = 8.0     # optional two-population G: pits +8 rougher

CRUSH_GATES = True
SPEC_REF = (_SPEC_M, _SPEC_G, _SPEC_B)
RAINBOW_IDS = frozenset({
    "fsk_prism_shatter", "fsk_oilslick_weave", "fsk_aurora_veil",
    "fsk_opal_pave", "fsk_spectrum_scales", "fsk_nebula_prism"})

_WHEEL16 = [round((k + 0.5) / 16.0, 4) for k in range(16)]


def _crc(tag):
    """Deterministic string salt (no hash(str) — owner determinism law)."""
    return zlib.crc32(str(tag).encode()) & 0xFFFF


# ════════════════════════════════════════════════════════════════════════════
# WALK MACHINERY — engines author art-luma targets; the walk inverts the
# LUT's steepest quasi-monotone luma stretch so the terraces survive exactly.
# ════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=32)
def _walkmap(lut_key):
    """luma target (1024 bins, 0..1) -> LUT T value ((idx+0.5)/1023)."""
    lut = thinfilm_lut(*lut_key)
    lum = 0.299 * lut[:, 0] + 0.587 * lut[:, 1] + 0.114 * lut[:, 2]
    n = len(lum)
    best, i0, hi = (0.0, 0, n - 1), 0, lum[0]
    for i in range(1, n):
        if lum[i] < hi - 0.010:
            gain = hi - lum[i0:i].min()
            if gain > best[0]:
                j0 = int(np.argmin(lum[i0:i])) + i0
                best = (gain, j0, i - 1)
            i0, hi = i, lum[i]
        else:
            hi = max(hi, lum[i])
    gain = hi - lum[i0:].min()
    if gain > best[0]:
        best = (gain, int(np.argmin(lum[i0:])) + i0, n - 1)
    _g, j0, j1 = best
    seg = np.maximum.accumulate(lum[j0:j1 + 1]).astype(np.float32)
    tgt = np.linspace(0.0, 1.0, 1024, dtype=np.float32)
    idx = j0 + np.clip(np.searchsorted(seg, tgt), 0, j1 - j0)
    return ((idx.astype(np.float32) + 0.5) / 1023.0)


@lru_cache(maxsize=2)
def _snapmap():
    """1024-entry luma -> luma map that CONSOLIDATES plateau mass onto the
    ladder anchors (pit floor, 8 rungs, vein). [r7, measured] the AA sweeps
    of every face/seam edge spread 50-65% of the mass into a smooth
    continuum and the 64-bin histogram read 0-3 terraces on fields authored
    with 8. Pixels within 0.010 of an anchor are pulled ON it, the pull
    fades to zero by 0.030 (with 4-bin rung spacing that consolidates ~82%
    of face mass onto the rungs — the histogram comb),
    so the blur cannot un-quantize the ladder. This IS the crush law
    ("many quantized dark shades"), enforced where it is measured."""
    anchors = np.concatenate(([0.006], _LAD.astype(np.float64), [0.985]))
    x = np.linspace(0.0, 1.0, 1024)
    d = np.abs(x[:, None] - anchors[None, :])
    j = np.argmin(d, axis=1)
    near = anchors[j]
    dist = np.abs(x - near)
    t = np.clip((dist - 0.034) / (0.016 - 0.034), 0.0, 1.0)
    q = t * t * (3.0 - 2.0 * t)
    return (x + q * (near - x)).astype(np.float32)


def _walk(fn):
    """Wrap an art-luma engine into the catlib T contract. Pops `lut` (the
    recipe's own LUT tuple, duplicated into eargs by _R) and `soft` (edge
    AA blur at GEN — trims the r>256 ringing that kills lag-1 coherence).
    Order: blur -> rung-snap -> LUT walk."""
    def g(res, seed, lut=None, soft=0.0, **kw):
        L = np.asarray(fn(res, seed, **kw), np.float32)
        if float(soft) > 0.0:
            L = gauss(L, float(soft))
        L = _snapmap()[np.clip((L * 1023.0).astype(np.int32), 0, 1023)]
        tv = _walkmap(tuple(lut))
        T = tv[np.clip((L * 1023.0).astype(np.int32), 0, 1023)]
        return np.clip(T, 0.0, 0.9995)
    g.__name__ = fn.__name__
    g.__doc__ = fn.__doc__
    g.__wrapped__ = fn
    return g


# ════════════════════════════════════════════════════════════════════════════
# LATTICE TOOLKIT — bounded-jitter grids at the band pitch (in-band lattice
# law, measured by the FROST pass; adapted here for quantized-ladder output).
# ════════════════════════════════════════════════════════════════════════════

def _cg(n, salt, dj=0, di=0):
    ii = np.arange(n, dtype=np.float32)
    g = h2(ii[None, :], ii[:, None], salt)
    if dj or di:
        g = np.roll(np.roll(g, -dj, 0), -di, 1)
    return np.ascontiguousarray(g, np.float32)


def _up(g, res):
    return cv2.resize(g, (res, res), interpolation=cv2.INTER_NEAREST)


def _celln(res, cell):
    n = max(2, int(round(float(res) / float(cell))))
    return n, float(res) / n


def _rungi(hv, ci, cj, lo=0, hi=8):
    """ORDERED integer ladder rung: a quasi-periodic (3i+5j) walk through the
    [lo,hi) rung window with a +-1 hash jitter. [round 2, measured] random
    per-cell tiers leaked lo=0.38-0.64 sub-band (cells clump); the ordered
    walk puts the tier field's power AT the lattice fundamental while keeping
    values QUANTIZED — the crush-ladder replacement for FROST's banned
    _flat() de-drift. Returns the integer rung index (engines may terrace by
    index arithmetic and stay ON-ladder)."""
    span = max(1, int(hi) - int(lo))
    idx = np.floor(np.asarray(ci, np.float32) * 3.0
                   + np.asarray(cj, np.float32) * 5.0
                   + np.floor(np.asarray(hv, np.float32) * 1.999)) % span
    return np.clip(idx + float(lo), 0, 7).astype(np.int32)


def _rung(hv, ci, cj, lo=0, hi=8):
    return _LAD[_rungi(hv, ci, cj, lo, hi)]


def _plate(prof, lo=0.15, hi=0.45):
    """PLATEAU an element profile: flat 1 over the interior, falling only at
    the edges. [round 2] cylinder/dome shading (0.42+0.58*sin) turned every
    rung into a broad luma RAMP — the 64-bin histogram read 0-2 terraces on
    a field authored with 8. Ladder law: plateaus carry the rung, edges are
    carried by the pit lanes."""
    return sstep(float(lo), float(hi), prof)


def _fat(d, w, soft=0.62):
    """Fat smooth ridge/seam profile from a distance field (0 = centre)."""
    w = np.asarray(w, np.float32)
    t = np.clip((d - w) / np.minimum(w * (float(soft) - 1.0), -1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _voro(res, cell, jit, salt, ax=1.0, ay=1.0, ang=0.0):
    """Bounded-jitter Voronoi -> (F1/cell, (F2-F1)/cell, winning-cell hash).
    ax/ay/ang stretch+rotate the domain (anisotropic shards)."""
    yy, xx = coords(res)
    if ang:
        u, v = rot((yy, xx), float(ang))
    else:
        u, v = xx, yy
    u = u * float(ax)
    v = v * float(ay)
    n, c = _celln(res, cell)
    ci = np.floor(u / c)
    cj = np.floor(v / c)
    f1 = np.full((res, res), 1e12, np.float32)
    f2 = np.full((res, res), 1e12, np.float32)
    idw = np.zeros((res, res), np.float32)
    wci = np.zeros((res, res), np.float32)
    wcj = np.zeros((res, res), np.float32)
    j = float(jit)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            axh = h2(ci + di, cj + dj, salt)
            ayh = h2(ci + di, cj + dj, salt + 40)
            dx = (ci + di + 0.5 + (axh - 0.5) * j) * c - u
            dy = (cj + dj + 0.5 + (ayh - 0.5) * j) * c - v
            d = dx * dx + dy * dy
            m = d < f1
            np.minimum(f2, np.maximum(f1, d), out=f2)
            np.minimum(f1, d, out=f1)
            idw = np.where(m, h2(ci + di, cj + dj, salt + 80), idw)
            wci = np.where(m, ci + di, wci)
            wcj = np.where(m, cj + dj, wcj)
    f1 = np.sqrt(f1, out=f1)
    f2 = np.sqrt(f2, out=f2)
    return (np.clip(f1 / c, 0.0, 1.5).astype(np.float32),
            np.clip((f2 - f1) / c, 0.0, 1.5).astype(np.float32), idw, wci, wcj)


def _dots(res, cell, jit, salt):
    """Jittered-lattice dot field -> (radial distance 0..1+, cell hash,
    cell i, cell j)."""
    n, c = _celln(res, cell)
    yy, xx = coords(res)
    ci = np.floor(xx / c)
    cj = np.floor(yy / c)
    jx = (h2(ci, cj, salt) - 0.5) * float(jit) * c
    jy = (h2(ci, cj, salt + 11) - 0.5) * float(jit) * c
    d = np.hypot(xx - (ci + 0.5) * c - jx, yy - (cj + 0.5) * c - jy) / (c * 0.62)
    return (np.clip(d, 0.0, 2.0).astype(np.float32), h2(ci, cj, salt + 23),
            ci, cj)


def _rows(res, seed, salt, sw, sh, warp=2.4):
    """Offset-row (imbrication) frame -> (cu -1..1 across element, cy 0..1 down
    row, col index, row index, element hash, parity). The scale-family chassis;
    each scale engine renders a DIFFERENT element on it."""
    yy, xx = coords(res)
    a = float(rng(seed, salt).uniform(0, np.pi))
    u, v = rot((yy, xx), a)
    if warp > 0.0:
        wob = (np.sin(v / 47.0 + a * 5.0) + np.sin(u / 31.0 - a * 3.0)) * (warp * 0.5)
        u = u + wob
    row = np.floor(v / float(sh))
    xo = u + (row % 2) * float(sw) * 0.5
    col = np.floor(xo / float(sw))
    cu = (frac(xo / float(sw)) - 0.5) * 2.0
    cy = frac(v / float(sh))
    hv = h2(col, row, salt + 7)
    return cu, cy, col, row, hv, (col + row) % 2.0


def _uv(res, seed, salt, extra=0.0):
    yy, xx = coords(res)
    a = float(rng(seed, salt).uniform(0, np.pi)) + float(extra)
    return rot((yy, xx), a)


def _jline(t, jit, salt):
    """Irregular 1-D grid: edge k sits at k + (hash(k)-0.5)*jit. -> (cell
    index, 0..1 position inside the cell). Vectorized, deterministic."""
    i = np.floor(t)
    e0 = i + (h2(i, i * 0.0, salt) - 0.5) * jit

    def edge(k):
        return k + (h2(k, k * 0.0, salt) - 0.5) * jit
    below = t < e0
    col = np.where(below, i - 1, i)
    lo = np.where(below, edge(i - 1), e0)
    hi = np.where(below, e0, edge(i + 1))
    return col, np.clip((t - lo) / np.maximum(hi - lo, 1e-4), 0.0, 1.0)


def _pitb(L, g, k=1.0):
    """Pit LANE: blend toward 0.0 (not _PIT) — the soft blur lifts a 1-2 px
    core by ~2x, so lanes are dug past the gate and land at it. [round 2]"""
    return L + np.clip(g, 0.0, 1.0) * float(k) * (0.0 - L)


def _veinb(L, g, k=1.0):
    return L + np.clip(g, 0.0, 1.0) * float(k) * (_VEIN - L)


# ════════════════════════════════════════════════════════════════════════════
# 19 NAMED-PATTERN ENGINES — art-luma fields. One archetype each (ledger in
# the header): the pattern is the STRUCTURE, the crush ladder is the PAINT.
# ════════════════════════════════════════════════════════════════════════════

def e_snakeskin(res, seed, sw=8.0, sh=6.0):
    """[fsk_snakeskin] Pointed-oval keeled scales in offset rows, tip-down
    imbrication; per-scale ladder rung, keel ridge, tip glint."""
    cu, cy, col, row, hv, _par = _rows(res, seed, 211, sw, sh)
    d = np.hypot(cu * (1.02 + 0.55 * cy), (cy - 0.30) * 1.50)
    face = sstep(0.98, 0.88, d)
    ri = _rungi(hv, col, row, 2, 8)
    rung = _LAD[np.clip(ri - (cy < 0.16).astype(np.int32), 0, 7)]
    keel = _fat(np.abs(cu) * (0.85 + 0.9 * cy), 0.40) * face
    L = _PIT + face * (rung + 0.008 * (1.0 - d) - _PIT)
    L = L + keel * 0.006
    glint = keel * sstep(0.30, 0.46, cy) * sstep(0.97, 0.88, cy)
    return _veinb(L, glint)


def e_diamond_plate(res, seed, cell=9.5):
    """[fsk_diamond_plate] Raised lozenge treadplate on a parity grid — dark
    valley moats, laddered floors, worn-bright crowns (the vein lane)."""
    u, v = _uv(res, seed, 221)
    _n, c = _celln(res, cell)
    ci, cj = np.floor(u / c), np.floor(v / c)
    par = (ci + cj) % 2.0
    du = (frac(u / c) - 0.5) * 2.0
    dv = (frac(v / c) - 0.5) * 2.0
    lu = np.where(par < 1.0, du, dv)
    lv = np.where(par < 1.0, dv, du)
    dl = (np.abs(lu) / 0.86) ** 2.4 + (np.abs(lv) / 0.34) ** 2.4
    top = sstep(1.10, 0.72, dl)
    base_r = _rung(h2(ci, cj, 227), ci, cj, 0, 4)
    loz_r = _rung(h2(ci, cj, 223), ci + 1.0, cj, 5, 8)
    L = base_r + top * (loz_r + 0.008 * (1.0 - np.clip(dl, 0.0, 1.0)) - base_r)
    dls = (np.abs(lu - 0.40) / 0.86) ** 2.4 + (np.abs(lv - 0.26) / 0.34) ** 2.4
    shadow = sstep(1.40, 0.85, dls) * (1.0 - top)
    L = _pitb(L, shadow, 1.0)
    crown = sstep(1.05, 0.55, (np.abs(lu) / 0.72) ** 2.0 + (np.abs(lv) / 0.22) ** 2.0)
    wear = np.floor(sstep(0.12, 0.55, h2(ci, cj, 229)) * 2.999) * 0.5
    return _veinb(L, crown * wear)


def e_carbon_weave(res, seed, tow=4.7):
    """[fsk_carbon_weave] 2x2 twill carbon: alternating warp/weft darkness
    (two ladder windows), resin pit dots at crossings, fiber sheen."""
    u, v = _uv(res, seed, 231)
    i, j = np.floor(u / tow), np.floor(v / tow)
    fu, fv = frac(u / tow), frac(v / tow)
    wtop = ((i - j) % 4.0) < 2.0
    prof_w = np.sin(np.pi * fu).astype(np.float32)
    prof_f = np.sin(np.pi * fv).astype(np.float32)
    # [r3] segment ladder at tow*2.0 (in-band): a tow*3 segment rate sat at
    # r~37 @512 and leaked its whole value swing under the band.
    vseg = np.floor(v / (tow * 2.0))
    useg = np.floor(u / (tow * 2.0))
    rw = _rung(h2(i, vseg, 233), i, vseg, 3, 8)
    rf = _rung(h2(j, useg, 237), j, useg, 0, 5)
    L = np.where(wtop, rw * (0.16 + 0.84 * _plate(prof_w)),
                 rf * (0.16 + 0.84 * _plate(prof_f))).astype(np.float32)
    dc = np.hypot(np.minimum(fu, 1.0 - fu), np.minimum(fv, 1.0 - fv)) * tow
    resin = _fat(dc, 1.05) * (h2(np.round(u / tow), np.round(v / tow), 239) > 0.35)
    L = _pitb(L, resin)
    sheen_g = np.where(wtop, h2(i, vseg, 241), h2(j, useg, 243))
    sheen = np.where(wtop, sstep(0.93, 0.99, prof_w),
                     sstep(0.93, 0.99, prof_f)) * (sheen_g > 0.72)
    return _veinb(L, sheen)


def e_dragon_scale(res, seed, sw=11.2, sh=8.6):
    """[fsk_dragon_scale] Large flat-top pentagon scales, 3-facet keel, tip
    terrace (one rung down, ON-ladder), RIM LIGHT arc on the exposed edge —
    geometry, pitch and overlap law all distinct from fsk_snakeskin."""
    cu, cy, col, row, hv, _par = _rows(res, seed, 241, sw, sh, warp=3.0)
    half = (0.90 - 0.90 * np.clip((cy - 0.42) / 0.64, 0.0, 1.0) ** 1.3).astype(np.float32)
    m = np.abs(cu) - half
    face = sstep(0.05, -0.05, m)
    ri = _rungi(hv, col, row, 0, 8)
    tip = sstep(0.60, 0.68, cy)
    rung = _LAD[np.clip(ri - (tip > 0.5).astype(np.int32), 0, 7)]
    facet = 0.007 * np.sign(cu).astype(np.float32) * sstep(0.06, 0.20, np.abs(cu))
    keel = _fat(np.abs(cu), 0.075)
    L = _PIT + face * (rung + facet + 0.006 * keel - _PIT)
    L = _pitb(L, _fat(np.abs(m - 0.04), 0.22) * sstep(0.28, 0.46, cy), 0.97)
    rim = _fat(np.abs(m + 0.26), 0.30) * sstep(0.38, 0.60, cy) \
        * (h2(col, row, 247) > 0.30)
    return _veinb(L, rim)


def e_chainmail(res, seed, cell=9.0):
    """[fsk_chainmail] Interlocked ring rows (euro pattern): odd rows ride
    over even, plateau-lit rings, per-ring rung, gated top-arc glints."""
    u, v = _uv(res, seed, 251)
    rh = cell * 0.54
    R, w = cell * 0.42, cell * 0.19
    r0 = np.floor(v / rh)
    L = np.full((res, res), 0.008, np.float32)
    for ph in (0.0, 1.0):                      # even rows first, odd on top
        for dr in (-1.0, 0.0, 1.0):
            r = r0 + dr
            sel = (r % 2.0) == ph
            if not np.any(sel):
                continue
            dy = v - (r + 0.5) * rh
            xo = u + (r % 2.0) * cell * 0.5
            ki = np.floor(xo / cell)
            dx = xo - (ki + 0.5) * cell
            d = np.hypot(dx, dy)
            band = _fat(np.abs(d - R), w) * sel
            crest = (0.5 + 0.5 * np.cos(np.pi * np.clip((d - R) / w, -1.0, 1.0)))
            hv = h2(ki, r, 253)
            rung = _rung(hv, ki, r, 1, 7)
            shade = rung + 0.006 * crest
            L = L + band * (shade - L)
            db = np.hypot(dx, dy - R)
            bead = _fat(db, w * 1.3) * (hv > 0.40)
            L = _veinb(L, bead * sel)
    return L


def e_stingray(res, seed, cell=7.6, crown=23.0):
    """[fsk_stingray] Shagreen: dense round granule pave with a sparse second
    lattice of larger crown beads, calcified bright caps."""
    d1, h1, c1i, c1j = _dots(res, cell, 0.55, 261)
    dome = sstep(0.86, 0.62, d1)
    rung = _rung(h1, c1i, c1j)
    L = _PIT + dome * (rung + 0.008 * (1.0 - np.clip(d1, 0.0, 1.0)) ** 2 - _PIT)
    # [r3] crown lattice 23 -> recipe ~15 px and the bead BODY dropped to a
    # quiet +0 step (_LAD[4]): the 23 px high-contrast bodies alone carried
    # lo=0.62-0.64 sub-band. The bright cap keeps the archetype read.
    d2, h2v, _c2i, _c2j = _dots(res, crown, 0.35, 265)
    bead = sstep(0.34, 0.20, d2)
    L = L + bead * (_LAD[4] - L) * 0.60
    cap = sstep(0.21, 0.09, d2)
    return _veinb(L, cap)


def e_croc_hide(res, seed, cw=10.8, ch=8.2):
    """[fsk_croc_hide] Irregular rectangular scutes on a jittered grid, deep
    crease seams, plateau faces with wrinkle arcs, sparse gloss."""
    u, v = _uv(res, seed, 271)
    col, fu = _jline(u / cw, 0.25, 273)        # [r3] 0.42 edge jitter made
    row, fv = _jline(v / ch, 0.25, 277)        # the lattice aperiodic (lo .62)
    du = (fu - 0.5) * 2.0
    dv = (fv - 0.5) * 2.0
    d = (np.abs(du) ** 3.2 + np.abs(dv) ** 3.2)
    face = sstep(1.00, 0.74, d)
    hv = h2(col, row, 279)
    rung = _rung(hv, col, row)
    th = np.arctan2(dv, du + 1e-6)
    wr = 0.016 * np.clip(np.sin(th * 2.0 + hv * 6.2831853), 0.0, 1.0) \
        * sstep(0.15, 0.45, d) * sstep(0.95, 0.60, d)
    L = _PIT + face * (rung + 0.008 * (1.0 - np.clip(d, 0.0, 1.0)) - wr - _PIT)
    gloss = sstep(0.34, 0.12, np.hypot(du + 0.3, dv + 0.25)) * (hv > 0.25)
    return _veinb(L, gloss)


def e_damascus(res, seed, p=8.7):
    """[fsk_damascus] Folded-steel contour banding: warped laminar bands,
    acid-etched ordered ladder, gated bright etch lines, groove pits."""
    u, v = _uv(res, seed, 281)
    s = u + 14.0 * np.sin(v / 53.0) + 7.0 * np.sin(v / 23.0 + 2.1) \
        + 3.0 * np.sin((u + v) / 37.0)
    t = s / float(p)
    bi = np.floor(t)
    ft = frac(t)
    vseg = np.floor(v / (p * 1.35))            # [r3] in-band segment rate
    rung = _rung(h2(bi, vseg, 283), bi, vseg)
    ridge = (0.5 + 0.5 * np.cos(6.2831853 * ft)).astype(np.float32)
    L = rung * (0.14 + 0.86 * _plate(ridge, 0.14, 0.38))
    groove = _fat(np.minimum(ft, 1.0 - ft) * p, 0.55)
    L = _pitb(L, groove, 0.95)
    etch = _fat(np.abs(ft - 0.150) * p, 0.60) \
        * (h2(bi, np.floor(v / (p * 6.0)), 287) > 0.28)
    return _veinb(L, etch)


def e_hex_mesh(res, seed, p=9.9):
    """[fsk_hex_mesh] Honeycomb: fat dark walls (the pit lane), laddered
    plateau floors, gated wall-crest glints + centre dew dots."""
    u, v = _uv(res, seed, 291)
    hx = u / float(p)
    hy = v / float(p) * 1.1547
    row = np.floor(hy)
    hxo = hx + (row % 2) * 0.5
    cu = hxo - np.floor(hxo + 0.5)
    cvv = hy - np.floor(hy + 0.5)
    d = np.sqrt(cu * cu + cvv * cvv)
    ci = np.floor(hxo + 0.5)
    hv = h2(ci, row, 293)
    rung = _rung(hv, ci, row)
    floor_m = sstep(0.475, 0.415, d)
    L = _PIT + floor_m * (rung + 0.008 * (1.0 - (d / 0.36) ** 2) - _PIT)
    crest = _fat(np.abs(d - 0.500), 0.075) * (((ci + row * 2.0) % 3.0) < 1.0) * (hv > 0.30)
    L = _veinb(L, crest)
    dew = sstep(0.10, 0.035, d) * (((ci * 2.0 + row) % 3.0) < 1.0) * (hv > 0.25)
    return _veinb(L, dew)


def e_knurl(res, seed, p=6.6):
    """[fsk_knurl] Machined diamond knurl: crossed +-32 deg V-grooves, 4-facet
    pyramids (directional facet light), crest-tip glints."""
    u, v = _uv(res, seed, 301)
    ca, sa = np.cos(0.56), np.sin(0.56)
    s1 = (u * ca + v * sa) / float(p)
    s2 = (u * ca - v * sa) / float(p)
    t1 = np.abs(frac(s1) - 0.5) * 2.0
    t2 = np.abs(frac(s2) - 0.5) * 2.0
    pyr = np.minimum(t1, t2)
    i, j = np.floor(s1), np.floor(s2)
    ri = _rungi(h2(i, j, 303), i, j, 2, 8)
    fid = ((frac(s1) > 0.5) * 1.0 + (frac(s2) > 0.5) * 2.0)
    foff = np.float32([0.007, 0.003, -0.003, -0.007])[fid.astype(np.int32)]
    q = np.floor(np.clip(pyr, 0.0, 0.999) * 3.0).astype(np.int32)
    rung = _LAD[np.clip(ri - (2 - q), 0, 7)]
    face = sstep(0.05, 0.13, pyr)
    L = 0.012 + face * (rung + foff - 0.012)
    tip = sstep(0.55, 0.78, pyr) * (h2(i, j, 307) > 0.10)
    return _veinb(L, tip)


def e_herringbone(res, seed, colw=21.0, p=7.9):
    """[fsk_herringbone] Chevron twill: diagonal yarn dashes flipping
    direction per column, zipper seam at the flip, sparse nep flecks."""
    u, v = _uv(res, seed, 311)
    col = np.floor(u / colw)
    fu = frac(u / colw)
    sgn = (1.0 - 2.0 * (col % 2.0)).astype(np.float32)
    dg = (v * 0.7071 + sgn * u * 0.7071) / float(p)
    rib = np.floor(dg)
    fd = frac(dg)
    along = (v * 0.7071 - sgn * u * 0.7071)
    dash = np.floor(along / 8.4)
    rung = _rung(h2(rib, dash + col * 13.0, 313), rib, dash)
    prof = np.sin(np.pi * fd).astype(np.float32)
    L = rung * (0.14 + 0.86 * _plate(prof)) + 0.004
    gap = _fat(np.minimum(fd, 1.0 - fd) * p, 0.78)
    L = _pitb(L, gap, 0.97)
    ce = _fat(np.minimum(fu, 1.0 - fu) * colw, 0.55)
    L = _pitb(L, ce, 0.90)
    dn, hn, _ni, _nj = _dots(res, 17.0, 0.85, 317)
    nep = sstep(0.20, 0.08, dn) * (hn > 0.55)
    return _veinb(L, nep)


def e_houndstooth(res, seed, s=5.6):
    """[fsk_houndstooth] TRUE houndstooth: 2-dark/2-light block-dyed threads
    woven 2/2 twill — the classic broken check emerges at thread scale.
    Families OVERLAP (dark 0-4, light 3-7): the check reads at +-2 rungs,
    which keeps the 22 px motif from dumping its whole swing sub-band."""
    u, v = _uv(res, seed, 321)
    i, j = np.floor(u / s), np.floor(v / s)
    fu, fv = frac(u / s), frac(v / s)
    wtop = ((i - j) % 4.0) < 2.0
    colf = np.where(wtop, np.floor(i / 2.0) % 2.0, np.floor(j / 2.0) % 2.0)
    prof = np.where(wtop, np.sin(np.pi * fu), np.sin(np.pi * fv)).astype(np.float32)
    thr = np.where(wtop, i, j)
    seg = np.where(wtop, np.floor(v / (s * 3.0)), np.floor(u / (s * 3.0)))
    hvv = h2(thr, seg + 31.0 * colf, 323)
    idx = _rungi(hvv, thr, seg, 0, 5)
    rung = _LAD[np.clip(idx + (colf * 3.0).astype(np.int32), 0, 7)]
    L = rung * (0.14 + 0.86 * _plate(prof)) + 0.004
    edge = np.where(wtop, _fat(np.minimum(fu, 1.0 - fu) * s, 0.72),
                    _fat(np.minimum(fv, 1.0 - fv) * s, 0.72))
    L = _pitb(L, edge, 1.0)
    crest = (colf > 0.5) * sstep(0.93, 0.99, prof) * (hvv > 0.78)
    return _veinb(L, crest)


def e_basket_weave(res, seed, strip=5.3):
    """[fsk_basket_weave] 2-strand rattan blocks alternating over/under,
    tucked strand ends shading into the crossing, corner hole pits."""
    u, v = _uv(res, seed, 331)
    B = strip * 2.0
    bi, bj = np.floor(u / B), np.floor(v / B)
    horiz = ((bi + bj) % 2.0) < 1.0
    lu, lv = frac(u / B), frac(v / B)

    def lane(par_axis, run_axis, bid_run, bid_par):
        sv = frac(par_axis * 2.0)
        strand = np.floor(par_axis * 2.0)
        prof = np.sin(np.pi * sv).astype(np.float32)
        tuck = 1.0 - 0.12 * (sstep(0.12, 0.0, run_axis) + sstep(0.88, 1.0, run_axis))
        rung = _rung(h2(bid_par * 2.0 + strand, bid_run, 333),
                     bid_par * 2.0 + strand, bid_run, 1, 8)
        Ls = rung * (0.16 + 0.84 * _plate(prof)) * tuck + 0.004
        gap = _fat(np.minimum(sv, 1.0 - sv) * strip, 0.80)
        return _pitb(Ls, gap, 0.96)

    Lh = lane(lv, lu, bi, bj)
    Lv = lane(lu, lv, bj, bi)
    L = np.where(horiz, Lh, Lv).astype(np.float32)
    dc = np.hypot(np.minimum(lu, 1.0 - lu), np.minimum(lv, 1.0 - lv)) * B
    L = _pitb(L, _fat(dc, 1.30), 0.95)
    sheen = np.where(horiz, _fat(np.abs(frac(lv * 2.0) - 0.5) * strip, 0.75),
                     _fat(np.abs(frac(lu * 2.0) - 0.5) * strip, 0.75))
    gate = h2(bi * 2.0 + bj, np.floor(np.where(horiz, lu, lv) * 2.0), 337) > 0.62
    return _veinb(L, sheen * gate)


def e_chesterfield(res, seed, p=10.0):
    """[fsk_chesterfield] Deep-buttoned tufted leather on the 45-deg diamond:
    ON-LADDER terraced pillow rolls (idx-2/-1/0), fold crease pits between
    buttons, button gloss dots."""
    u, v = _uv(res, seed, 341, extra=0.7853982)
    ci, cj = np.floor(u / p), np.floor(v / p)
    fu, fv = frac(u / p), frac(v / p)
    du = np.abs(fu - 0.5) * 2.0
    dv = np.abs(fv - 0.5) * 2.0
    dinf = np.maximum(du, dv)
    hv = h2(ci, cj, 343)
    ri = _rungi(hv, ci, cj, 2, 8)
    qi = np.floor(np.clip(1.0 - dinf, 0.0, 0.999) * 2.0).astype(np.int32)
    rung = _LAD[np.clip(ri - (1 - qi), 0, 7)]
    L = rung + 0.008 * (1.0 - dinf * dinf)
    crease = _fat(np.minimum(np.minimum(fu, 1.0 - fu),
                             np.minimum(fv, 1.0 - fv)) * p, 1.15, 0.42)
    L = _pitb(L, crease, 0.90)
    db = np.hypot(np.minimum(fu, 1.0 - fu), np.minimum(fv, 1.0 - fv)) * p
    button = _fat(db, 1.85, 0.30)
    L = L + button * (0.030 - L)
    gloss = _fat(db, 1.55)
    return _veinb(L, gloss)


def e_feather_mantle(res, seed, fw=7.2, fh=10.4):
    """[fsk_feather_mantle] Overlapping barbed feathers: tall shingle rows,
    bright rachis spine, diagonal barb comb, tip one rung down (ON-ladder)."""
    cu, cy, col, row, hv, _par = _rows(res, seed, 351, fw, fh, warp=2.0)
    half = (0.90 - 0.52 * np.clip(cy * 1.12 - 0.18, 0.0, 1.0) ** 1.6).astype(np.float32)
    m = np.abs(cu) - half
    face = sstep(0.05, -0.05, m)
    ri = _rungi(hv, col, row)
    tip = sstep(0.66, 0.74, cy)
    rung = _LAD[np.clip(ri - (tip > 0.5).astype(np.int32), 0, 7)]
    bo = np.abs(frac((cy * fh * 0.5 + np.abs(cu) * fw * 0.62) / 3.3) - 0.5) * 2.0
    barb = (0.5 + 0.5 * np.cos(np.pi * bo)).astype(np.float32) * 0.006
    L = _PIT + face * (rung + barb - _PIT)
    rachis = _fat(np.abs(cu), 0.30) * face
    L = L + rachis * 0.006
    rgl = rachis * sstep(0.18, 0.40, cy) * sstep(0.94, 0.78, cy) * (hv > 0.15)
    return _veinb(L, rgl)


def e_scale_mail(res, seed, sw=9.4, sh=5.8):
    """[fsk_scale_mail] Wide half-moon lamellae rows: flat tops tucked under
    the row above, crescent shadow under each exposed bottom, polished rim."""
    cu, cy, col, row, hv, _par = _rows(res, seed, 361, sw, sh, warp=2.0)
    r = np.hypot(cu * 1.02, np.maximum(cy - 0.28, 0.0) * 1.30)
    face = sstep(1.00, 0.90, r)
    rung = _rung(hv, col, row, 0, 7)
    brush = 0.008 * np.cos(r * 9.0).astype(np.float32)   # [r3] 22rad ripple
    # sat past r200 and was the ac=0.52 killer on this id.
    L = _PIT + face * (rung + brush + 0.008 * (1.0 - r) - _PIT)
    under = _fat(np.abs(r - 0.97), 0.14) * sstep(0.42, 0.58, cy)
    L = _pitb(L, under, 1.0)
    rim = _fat(np.abs(r - 0.80), 0.22) * sstep(0.30, 0.52, cy) * (hv > 0.35)
    return _veinb(L, rim)


def e_spider_silk(res, seed, cell=8.2, gcell=5.4):
    """[fsk_spider_silk] Layered orb-web mesh over a SILK GRANULE PAVE — one
    small orb per cell, fat plateau spokes + two rings, dew nodes. [r5] the
    flat per-cell background made the whole id thread-dependent (hairlines:
    ac 0.31-0.42 at any soft); the in-band granule pave now carries band+ac
    on its own and its gaps are the pit lane."""
    n, c = _celln(res, cell)
    yy, xx = coords(res)
    ci, cj = np.floor(xx / c), np.floor(yy / c)
    jx = (h2(ci, cj, 371) - 0.5) * 0.5 * c
    jy = (h2(ci, cj, 373) - 0.5) * 0.5 * c
    dx = xx - (ci + 0.5) * c - jx
    dy = yy - (cj + 0.5) * c - jy
    rl = np.hypot(dx, dy) / (c * 0.62)
    th = np.arctan2(dy, dx)
    hv = h2(ci, cj, 377)
    karm = 5.0 + np.floor(h2(ci, cj, 379) * 3.0)
    spoke = (0.5 + 0.5 * np.cos(th * karm + hv * 6.2831853)) ** 5 \
        * sstep(1.30, 0.25, rl)
    ring = np.maximum(_fat(np.abs(rl - 0.40), 0.13),
                      _fat(np.abs(rl - 0.76), 0.11))
    dg, hg, gi, gj = _dots(res, gcell, 0.80, 389)
    gdome = sstep(0.92, 0.74, dg)
    bg = 0.010 + gdome * (_rung(hg, gi, gj, 0, 4) - 0.010)
    thread = _plate(np.maximum(spoke, ring), 0.22, 0.52)
    tr = _rung(h2(ci, cj, 383), ci + 1.0, cj, 4, 8)
    L = bg + thread * (tr - bg)
    # [SPB-OPALSKIN-002] dew NODES as true FILLED DISCS at the spoke-ring
    # crossing points (the archetype's natural bright anchor). Ring-shaped
    # marks have dark on BOTH sides and blur-erode below the vein line at any
    # width (measured 4 rounds); a 2.6 px-radius disc at each crossing keeps
    # its core above it. Angular distance to the nearest spoke crest is
    # analytic; ONE disc per web at a hash-chosen ring angle (radius 1.6 px
    # keeps the web centre, 2 px away, dark).
    dth = (np.mod(th - hv * 6.2831853 + np.pi, 6.2831853) - np.pi)
    arcpx = np.abs(dth) * rl * (c * 0.62)
    dnode = np.hypot((rl - 0.40) * (c * 0.62), arcpx)
    varc = _fat(dnode, 1.6)
    return _veinb(L, varc)


def e_circuit_trace(res, seed, p=6.9):
    """[fsk_circuit_trace] Dense PCB: dashed copper lanes with clearance-gap
    pits, via annuli with dark drill holes, pads with tinned glints."""
    u, v = _uv(res, seed, 391)
    lane = np.floor(v / p)
    fy = frac(v / p)
    seg = np.floor(u / (p * 1.6))              # [r3] in-band dash rate
    on = (h2(lane, seg, 393) > 0.10).astype(np.float32)
    tr = _fat(np.abs(fy - 0.5) * p, 1.25) * on
    copper = _rung(h2(lane, seg, 397), lane, seg, 3, 8)
    bgc = np.floor(u / (p * 1.2))
    bg = _rung(h2(bgc, lane, 399), bgc, lane, 0, 3) + 0.004
    L = bg + tr * (copper * (0.16 + 0.84 * _plate(np.sin(np.pi * fy))) - bg)
    clr = _fat(np.abs(np.abs(fy - 0.5) * p - 1.45), 0.42) * on
    L = _pitb(L, clr, 0.85)
    dvia, hvia, _vi, _vj = _dots(res, p * 3.1, 0.7, 401)
    ring = _fat(np.abs(dvia - 0.30), 0.10) * (hvia > 0.35)
    L = L + ring * (_LAD[6] - L)
    hole = sstep(0.20, 0.08, dvia) * (hvia > 0.35)
    L = _pitb(L, hole)
    dpad, hpad, _pi, _pj = _dots(res, p * 5.3, 0.6, 403)
    pad = sstep(0.27, 0.19, dpad) * (hpad > 0.5)
    L = L + pad * (_LAD[6] - L)
    L = _pitb(L, sstep(0.12, 0.045, dpad) * (hpad > 0.5), 0.95)
    glint = _fat(np.abs(dpad - 0.21), 0.07) * (hpad > 0.70)
    return _veinb(L, glint)


def e_mosaic_glass(res, seed, cell=8.9):
    """[fsk_mosaic_glass] Grouted micro-tesserae: squarish low-jitter pave,
    fat grout pits, per-tile rung with an ON-LADDER bevel terrace (idx-1 on
    the edge ring), corner glints."""
    f1, e1, idw, wci, wcj = _voro(res, cell, 0.30, 411)
    face = sstep(0.045, 0.150, e1)
    ri = _rungi(h2(np.floor(idw * 997.0), 0.0, 413), wci, wcj, 1, 8)
    bev = (e1 < 0.26).astype(np.int32)
    rung = _LAD[np.clip(ri - bev, 0, 7)]
    L = _PIT + face * (rung + 0.004 * sstep(0.55, 0.10, f1) - _PIT)
    grout = _fat(e1, 0.150)
    L = _pitb(L, grout, 0.94)
    gl = _fat(f1, 0.18) * (h2(np.floor(idw * 997.0), 2.0, 417) > 0.28)
    return _veinb(L, gl)


# ════════════════════════════════════════════════════════════════════════════
# RAINBOW LANE — 6 full-wheel structures. Each builder returns (L, D): the
# art-luma field AND a per-ELEMENT hue-anchor domain D=(k+0.5)/16 built from
# the SAME lattice (perfect alignment — no 192-res patch camo). The spectrum
# comes from the 16 wheel anchors; the ladders stay dark-dominant (owner:
# "the rainbow read comes from the LADDERS, not from bright candy").
# ════════════════════════════════════════════════════════════════════════════

def _rb_prism(res, seed, cell=9.7):
    """[fsk_prism_shatter] Elongated glass shards (anisotropic voronoi),
    plateau faces, fat fracture gulfs, gated lit slivers."""
    a = float(rng(seed, 421).uniform(0, np.pi))
    # [r3] elongation 0.60/1.52 put the long-axis fundamental at r~40 (deep
    # sub-band) and smeared peakiness to 0.295; 0.82/1.45 keeps the shard
    # read with both axes at or inside the band edge.
    f1, e1, idw, wci, wcj = _voro(res, cell, 0.50, 423, ax=0.93, ay=1.18, ang=a)
    cid = np.floor(idw * 997.0)
    rung = _rung(h2(cid, 0.0, 425), wci, wcj, 0, 7)
    # [SPB-OPALSKIN-002] shard-gap grout deepened to true black pits (pit
    # was 0.024 < 0.03): wider non-face gap + wider dug seam core.
    face = sstep(0.055, 0.165, e1)
    L = _PIT + face * (rung + 0.008 * sstep(0.85, 0.10, f1) - _PIT)
    L = _pitb(L, _fat(e1, 0.350), 1.0)
    sliver = _fat(np.abs(e1 - 0.170), 0.115) * (h2(cid, 3.0, 427) > 0.32)
    L = _veinb(L, sliver)
    D = (np.floor(h2(cid, 5.0, 429) * 15.999) + 0.5) / 16.0
    return L.astype(np.float32), D.astype(np.float32)


def _rb_oilslick(res, seed, tow=7.3):
    """[fsk_oilslick_weave] Spectral satin: long weft floats with 5-step
    staggered interlace dimples, per-float-segment wheel anchors."""
    u, v = _uv(res, seed, 431)
    j = np.floor(v / tow)
    fv = frac(v / tow)
    i = np.floor(u / tow)
    useg = np.floor(u / (tow * 1.5))           # [r3] in-band segment rate
    dimple = ((i + j * 2.0) % 5.0) < 1.0
    prof = np.sin(np.pi * fv).astype(np.float32)
    rung = _rung(h2(j, useg, 433), j, useg)
    L = rung * (0.16 + 0.84 * _plate(prof)) + 0.004
    gap = _fat(np.minimum(fv, 1.0 - fv) * tow, 0.60)
    L = _pitb(L, gap, 0.92)
    dnotch = np.hypot((frac(u / tow) - 0.5) * tow, (fv - 0.5) * tow)
    L = _pitb(L, _fat(dnotch, 1.30) * dimple, 0.95)
    sheen = sstep(0.93, 0.99, prof) * (h2(j, useg, 437) > 0.70)
    L = _veinb(L, sheen)
    D = (np.floor(h2(j, useg, 439) * 15.999) + 0.5) / 16.0
    return L.astype(np.float32), D.astype(np.float32)


def _rb_aurora(res, seed, p=8.3):
    """[fsk_aurora_veil] Combed spectral curtains: sine-swayed strand comb,
    per-strand-segment ladder, ORDERED wheel walk across strands (golden
    step) — evenly spread hue bins by construction."""
    u, v = _uv(res, seed, 441)
    r0 = rng(seed, 443)
    ph1, ph2 = float(r0.uniform(0, 6.28)), float(r0.uniform(0, 6.28))
    uf = u + 6.2 * np.sin(v / 89.0 + ph1) + 3.4 * np.sin(v / 41.0 + ph2)
    si = np.floor(uf / p)
    fs = frac(uf / p)
    seg = np.floor(v / 9.0)                    # [r3] in-band segment rate
    rung = _rung(h2(si, seg, 445), si, seg, 0, 7)
    prof = np.sin(np.pi * fs).astype(np.float32)
    L = rung * (0.16 + 0.84 * _plate(prof)) + 0.004
    L = _pitb(L, _fat(np.minimum(fs, 1.0 - fs) * p, 1.05), 0.97)
    crest = _fat(np.abs(fs - 0.5) * p, 1.10) * (h2(si, seg, 447) > 0.42)
    L = _veinb(L, crest)
    D = (((si * 5.0) % 16.0 + np.floor(h2(si, seg * 0.0, 449) * 1.999)) % 16.0 + 0.5) / 16.0
    return L.astype(np.float32), D.astype(np.float32)


def _rb_opal(res, seed, grain=7.7, patch=26.0):
    """[fsk_opal_pave] Black-opal potch with play-of-color: gated patches of
    laddered diffraction grain over near-black potch terraces + crack pits."""
    dg, hg, gi, gj = _dots(res, grain, 0.75, 451)
    n, c = _celln(res, patch)
    yy, xx = coords(res)
    pi, pj = np.floor(xx / c), np.floor(yy / c)
    hp = h2(pi, pj, 453)
    dx = xx - (pi + 0.5) * c - (h2(pi, pj, 455) - 0.5) * 0.4 * c
    dy = yy - (pj + 0.5) * c - (h2(pi, pj, 457) - 0.5) * 0.4 * c
    denv = np.hypot(dx, dy) / (c * 0.68)
    fire = (hp > 0.36).astype(np.float32) * sstep(0.90, 0.78, denv)
    potch = _rung(hg, gi, gj, 0, 3) + 0.010
    dome = sstep(0.82, 0.38, dg)
    grain_r = _rung(h2(gi, gj + 57.0, 459), gi, gj, 3, 7)
    L = potch + fire * dome * (grain_r - potch)
    _f1, e1, _iw, _wi, _wj = _voro(res, 19.0, 0.55, 461)
    L = _pitb(L, _fat(e1, 0.085), 0.94)
    spark = sstep(0.48, 0.20, dg) * fire * (hg > 0.55)
    L = _veinb(L, spark)
    D = (np.floor(h2(pi, pj, 463) * 15.999) + 0.5) / 16.0
    return L.astype(np.float32), D.astype(np.float32)


def _rb_spectrum(res, seed, p=8.5):
    """[fsk_spectrum_scales] Rhombic scales — TRUE diamond tiling (two
    interleaved square lattices; every pixel belongs to its nearest diamond,
    zero uncovered corners — [r3] the single-lattice version left 50% of the
    plane outside every scale and measured pit=0.495). 2-facet ridge, wheel
    WALKING the diagonals (snake-gradient) with jitter."""
    u, v = _uv(res, seed, 471, extra=0.7853982)
    aA, bA = np.floor(u / p), np.floor(v / p)
    duA = (frac(u / p) - 0.5) * 2.0
    dvA = (frac(v / p) - 0.5) * 2.0
    ddA = np.abs(duA) + np.abs(dvA)
    aB, bB = np.floor(u / p + 0.5), np.floor(v / p + 0.5)
    duB = (frac(u / p + 0.5) - 0.5) * 2.0
    dvB = (frac(v / p + 0.5) - 0.5) * 2.0
    ddB = np.abs(duB) + np.abs(dvB)
    inA = ddA <= ddB
    ai = np.where(inA, aA, aB + 3117.0)        # B lattice keyed apart
    bj = np.where(inA, bA, bB)
    du = np.where(inA, duA, duB).astype(np.float32)
    dd = np.minimum(ddA, ddB).astype(np.float32)
    pyr = 1.0 - np.minimum(dd, 1.0)
    hv = h2(ai, bj, 473)
    rung = _rung(hv, ai, bj, 2, 8)
    facet = 0.004 * np.sign(du).astype(np.float32) * sstep(0.04, 0.20, np.abs(du))
    L = rung + facet + 0.004 * pyr
    L = _pitb(L, _fat(np.abs(dd - 1.0) * p * 0.5, 1.55), 1.0)
    ridge = _fat(np.abs(du), 0.40) * sstep(0.24, 0.62, pyr)
    tip = ridge * (hv > 0.25)
    L = _veinb(L, tip)
    D = (((ai + bj * 3.0) % 16.0 + np.floor(h2(ai, bj, 477) * 2.999)) % 16.0 + 0.5) / 16.0
    return L.astype(np.float32), D.astype(np.float32)


def _rb_nebula(res, seed, cell=10.9):
    """[fsk_nebula_prism] Spectral cellular: 3 concentric ON-LADDER facet
    terraces per cell stepping down to fat black gulfs, bright nuclei."""
    f1, e1, idw, wci, wcj = _voro(res, cell, 0.50, 481)
    cid = np.floor(idw * 997.0)
    ri = _rungi(h2(cid, 0.0, 483), wci, wcj, 1, 7)
    q = np.floor(np.clip(f1 * 2.2, 0.0, 0.999) * 3.0).astype(np.int32)
    rung = _LAD[np.clip(ri - q, 0, 7)]
    face = sstep(0.030, 0.085, e1)
    L = _PIT + face * (rung + 0.008 - _PIT)
    L = _pitb(L, _fat(e1, 0.130), 0.95)
    nuc = sstep(0.20, 0.08, f1) * (h2(cid, 7.0, 485) > 0.12)
    L = _veinb(L, nuc)
    D = (np.floor(h2(cid, 9.0, 487) * 15.999) + 0.5) / 16.0
    return L.astype(np.float32), D.astype(np.float32)


_RB = {"prism": _rb_prism, "oilslick": _rb_oilslick, "aurora": _rb_aurora,
       "opal": _rb_opal, "spectrum": _rb_spectrum, "nebula": _rb_nebula}


@lru_cache(maxsize=12)
def _rb(kind, res, seed, kwt):
    return _RB[kind](res, int(seed), **dict(kwt))


def e_rainbow(res, seed, kind="prism", **kw):
    """Dispatcher engine for the 6 rainbow ids (walk-wrapped like the rest)."""
    return _rb(kind, res, int(seed), tuple(sorted(kw.items())))[0]


# ════════════════════════════════════════════════════════════════════════════
# MACRO KINDS — soft hue-domain drivers for the named ids (anchor-ladder
# families drift in soft patches), plus the HIRES rainbow domain that reuses
# the engine's own lattice (m_rbdom; served at GEN by OpalskinKit).
# ════════════════════════════════════════════════════════════════════════════

def m_clouds(r, mp, seed, K):
    """Soft luminance clouds: smooth fbm domain map — anchor switches follow
    fuzzy contours (anti patch-camo). Mval kept near-flat (crush law: no
    macro value gradients; vd is 0.98/1.03 everywhere)."""
    f = K.fbm(r, r, K.rng(seed, int(mp.get("salt", 641))), 3, int(mp.get("base", 3)))
    M = 0.5 + (K.n01(f) - 0.5) * 0.30
    D = K.n01(K.gauss(f, 2.0))
    return M, D


def m_drift(r, mp, seed, K):
    """Directional drift: hue-ladder anchors grade along one heading."""
    yy, xx = K.coords(r)
    _u, v = K.rot((yy, xx), float(mp.get("angle", 0.5)))
    p = K.n01(v) + (K.fbm(r, r, K.rng(seed, int(mp.get("salt", 643))), 2, 3) - 0.5) \
        * float(mp.get("warp", 0.25))
    M = 0.5 + (K.n01(p) - 0.5) * 0.24
    D = K.n01(p)
    return M, D


def m_rbdom(r, mp, seed, K):
    """HIRES rainbow domain: rebuild the engine's own lattice at GEN and
    serve its per-element wheel anchor as Ddom. Mval flat (no value macro)."""
    kw = {k: v for k, v in mp.items() if k not in ("hires", "kind")}
    _L, D = _rb(mp["kind"], r, int(seed), tuple(sorted(kw.items())))
    return np.full((r, r), 0.5, np.float32), D


ENGINES = {
    "e_snakeskin": e_snakeskin, "e_diamond_plate": e_diamond_plate,
    "e_carbon_weave": e_carbon_weave, "e_dragon_scale": e_dragon_scale,
    "e_chainmail": e_chainmail, "e_stingray": e_stingray,
    "e_croc_hide": e_croc_hide, "e_damascus": e_damascus,
    "e_hex_mesh": e_hex_mesh, "e_knurl": e_knurl,
    "e_herringbone": e_herringbone, "e_houndstooth": e_houndstooth,
    "e_basket_weave": e_basket_weave, "e_chesterfield": e_chesterfield,
    "e_feather_mantle": e_feather_mantle, "e_scale_mail": e_scale_mail,
    "e_spider_silk": e_spider_silk, "e_circuit_trace": e_circuit_trace,
    "e_mosaic_glass": e_mosaic_glass, "e_rainbow": e_rainbow,
}
ENGINES = {k: _walk(v) for k, v in ENGINES.items()}


# ════════════════════════════════════════════════════════════════════════════
# RECIPES — 25 finishes, ids fsk_*, seeds 1300-1324. Every recipe: vd near
# flat (0.98/1.03), tmod=0 (a phase offset would shear the walk ladder),
# satboost <= 0.95 (chroma from hue anchors + LUT sat, never sat clipping),
# hspan is a HALF-width, warm fans wrap through 0.0 via % 1.0 (wrap-safe).
# ════════════════════════════════════════════════════════════════════════════

def _fan(base, offs):
    """9-deep spine + 7-rung within-family fan (wrap-safe)."""
    return [round(base % 1.0, 4)] * 9 + [round((base + o) % 1.0, 4) for o in offs]


def _R(name, engine, eargs, seed, lut, hues, hspan, satboost, macro,
       val=0.37, soft=0.45, desc=""):
    e = dict(eargs)
    e["lut"] = lut
    e["soft"] = soft
    return dict(name=name, engine=engine, eargs=e, seed=seed, lut=lut, val=val,
                hues=hues, hspan=hspan, satboost=satboost, macro=macro,
                vd=(0.98, 1.03), tmod=0.0,
                kw=dict(ambient=0.04, ambient_sigma=40, floor=0.03, sparkle=0.012),
                desc=desc)


OPALSKIN = {
 # ── 19 named-pattern flips: the pattern is the STRUCTURE, the ladder is the
 # paint. [SPB-OPALSKIN-001 2026-08-03 owner mission: "snake skins, diamond
 # plates, carbon weaves... blend all of them"]
 "fsk_snakeskin": _R("Opal Snakeskin", "e_snakeskin", dict(sw=9.4, sh=7.1),
    1300, (0.0, 340.0, 0.9, 1.0, 0.0),
    _fan(0.30, (-0.04, 0.04, -0.08, 0.08, -0.11, 0.12, -0.15)), 0.035, 0.62,
    ("clouds", dict(base=7, salt=1300)), soft=0.55,
    desc="Emerald snakeskin — keeled scale rows, every scale its own dark rung; the ladder flips hue by shade on track. A FRACTURED OPALFIRE finish."),
 "fsk_diamond_plate": _R("Opal Diamond Plate", "e_diamond_plate", dict(cell=8.6),
    1301, (0.0, 300.0, 0.9, 0.7, 3.2),
    _fan(0.585, (0.02, -0.02, 0.045, -0.045, 0.07, -0.07, -0.10)), 0.030, 0.36,
    ("continents", dict(base=5, cells=5.0)), soft=0.66,
    desc="Steel treadplate — raised lozenges over dark valleys, worn crowns blazing; each wear level flips at its own angle. A FRACTURED OPALFIRE finish."),
 "fsk_carbon_weave": _R("Opal Carbon Weave", "e_carbon_weave", dict(tow=5.2),
    1302, (0.0, 260.0, 1.1, 0.7, 0.0),
    _fan(0.60, (0.018, -0.018, 0.04, -0.04, 0.06, -0.055, 0.08)), 0.028, 0.36,
    ("drift", dict(angle=0.4, salt=1302)), soft=0.50,
    desc="2x2 twill carbon — warp dark, weft darker, resin pits black; the weave cascade fires shade by shade. A FRACTURED OPALFIRE finish."),
 "fsk_dragon_scale": _R("Opal Dragon Scale", "e_dragon_scale", dict(sw=8.8, sh=6.8),
    1303, (0.0, 360.0, 0.9, 1.05, 3.2),
    _fan(0.42, (-0.05, 0.05, -0.09, 0.08, -0.13, 0.12, 0.16)), 0.035, 0.62,
    ("clouds", dict(base=6, salt=1303)), soft=0.55,
    desc="Faceted dragon scales — keeled pentagons rim-lit at the exposed edge, tip terraces a rung darker. A FRACTURED OPALFIRE finish."),
 "fsk_chainmail": _R("Opal Chainmail", "e_chainmail", dict(cell=8.4),
    1304, (0.0, 280.0, 1.1, 0.75, 3.2),
    _fan(0.60, (0.018, -0.018, 0.038, -0.038, 0.058, -0.05, 0.078)), 0.028, 0.32,
    ("continents", dict(base=5, cells=6.0)), soft=0.55,
    desc="Interlocked ring rows — torus-lit steel links over black skin, gated glints riding the crowns. A FRACTURED OPALFIRE finish."),
 "fsk_stingray": _R("Opal Stingray", "e_stingray", dict(cell=6.6, crown=15.0),
    1305, (0.0, 300.0, 0.9, 0.8, 0.0),
    _fan(0.57, (0.02, -0.02, 0.045, -0.045, 0.07, -0.50, -0.485)), 0.030, 0.34,
    ("clouds", dict(base=8, salt=1305)), soft=0.45,
    desc="Shagreen pave — thousands of laddered granules with calcified crown beads shining bone-bright. A FRACTURED OPALFIRE finish."),
 "fsk_croc_hide": _R("Opal Croc Hide", "e_croc_hide", dict(cw=8.6, ch=6.6),
    1306, (0.0, 330.0, 1.1, 1.0, 0.0),
    _fan(0.055, (0.02, -0.02, 0.035, -0.035, 0.05, -0.04, 0.065)), 0.032, 0.55,
    ("clouds", dict(base=6, salt=1306)),
    desc="Umber croc scutes — irregular rectangles split by deep creases, every scute its own dark rung. A FRACTURED OPALFIRE finish."),
 "fsk_damascus": _R("Opal Damascus", "e_damascus", dict(p=7.2),
    1307, (0.0, 290.0, 0.9, 0.85, 3.2),
    _fan(0.61, (0.02, -0.02, 0.045, -0.045, 0.07, -0.535, -0.52)), 0.030, 0.42,
    ("drift", dict(angle=0.9, salt=1307)),
    desc="Folded-steel banding — acid-etched ladder rungs alternating along the billet folds, bronze etch lines firing. A FRACTURED OPALFIRE finish."),
 "fsk_hex_mesh": _R("Opal Hex Mesh", "e_hex_mesh", dict(p=5.0),
    1308, (0.0, 340.0, 1.1, 1.05, 0.0),
    _fan(0.09, (0.02, -0.02, 0.035, -0.035, 0.05, -0.045, 0.065)), 0.032, 0.60,
    ("continents", dict(base=5, cells=5.0)), soft=0.50,
    desc="Amber honeycomb — black cell walls, laddered domed floors, dew points on the gated cells. A FRACTURED OPALFIRE finish."),
 "fsk_knurl": _R("Opal Knurl", "e_knurl", dict(p=7.4),
    1309, (0.0, 270.0, 0.9, 0.7, 3.2),
    _fan(0.62, (0.015, -0.015, 0.032, -0.032, 0.05, -0.045, 0.068)), 0.034, 0.48,
    ("continents", dict(base=6, cells=6.0)), soft=0.60,
    desc="Machined diamond knurl — crossed V-grooves, four facet lights per pyramid, crest tips glinting. A FRACTURED OPALFIRE finish."),
 "fsk_herringbone": _R("Opal Herringbone", "e_herringbone", dict(colw=12.0, p=6.2),
    1310, (0.0, 320.0, 1.1, 0.95, 0.0),
    _fan(0.06, (0.02, -0.02, 0.04, -0.035, 0.055, 0.27, 0.29)), 0.032, 0.50,
    ("drift", dict(angle=0.2, salt=1310)),
    desc="Tweed herringbone — chevron yarn dashes flipping per column, moss neps bright in the weave. A FRACTURED OPALFIRE finish."),
 "fsk_houndstooth": _R("Opal Houndstooth", "e_houndstooth", dict(s=4.8),
    1311, (0.0, 250.0, 0.9, 0.6, 0.0),
    _fan(0.10, (0.015, -0.015, 0.03, -0.03, 0.045, -0.04, 0.06)), 0.025, 0.34,
    ("clouds", dict(base=7, salt=1311)), soft=0.45,
    desc="The classic broken check executed micro — block-dyed threads in a 2/2 twill, dark family versus light. A FRACTURED OPALFIRE finish."),
 "fsk_basket_weave": _R("Opal Basket Weave", "e_basket_weave", dict(strip=4.6),
    1312, (0.0, 330.0, 0.9, 1.0, 3.2),
    _fan(0.095, (0.02, -0.02, 0.04, -0.04, 0.055, -0.035, 0.07)), 0.032, 0.58,
    ("continents", dict(base=6, cells=5.0)), soft=0.52,
    desc="Rattan basket weave — paired strands tucking over and under, corner holes black, sheen on the crests. A FRACTURED OPALFIRE finish."),
 "fsk_chesterfield": _R("Opal Chesterfield", "e_chesterfield", dict(p=8.8),
    1313, (0.0, 360.0, 1.1, 1.05, 0.0),
    _fan(0.985, (0.02, -0.02, 0.035, -0.045, 0.05, -0.065, 0.075)), 0.032, 0.60,
    ("clouds", dict(base=6, salt=1313)), soft=0.66,
    desc="Oxblood chesterfield — tufted diamond pillows in terraced leather rolls, folds black, buttons glossed. A FRACTURED OPALFIRE finish."),
 "fsk_feather_mantle": _R("Opal Feather Mantle", "e_feather_mantle", dict(fw=6.2, fh=8.7),
    1314, (0.0, 310.0, 0.9, 1.05, 3.2),
    _fan(0.70, (-0.04, 0.04, -0.09, 0.07, -0.16, -0.22, -0.34)), 0.035, 0.55,
    ("clouds", dict(base=7, salt=1314)), soft=0.44,
    desc="Raven feather mantle — barbed shingles with bright rachis spines, the sheen fanning violet to green. A FRACTURED OPALFIRE finish."),
 "fsk_scale_mail": _R("Opal Scale Mail", "e_scale_mail", dict(sw=7.4, sh=5.6),
    1315, (0.0, 300.0, 1.1, 0.95, 0.0),
    _fan(0.075, (0.015, -0.015, 0.03, -0.025, 0.045, -0.035, 0.06)), 0.030, 0.52,
    ("continents", dict(base=5, cells=6.0)), soft=0.55,
    desc="Bronze scale mail — wide half-moon lamellae, crescent shadows beneath, polished rims firing. A FRACTURED OPALFIRE finish."),
 "fsk_spider_silk": _R("Opal Spider Silk", "e_spider_silk", dict(cell=8.2),
    1316, (0.0, 280.0, 0.9, 0.7, 0.0),
    _fan(0.575, (0.024, -0.024, 0.05, -0.05, 0.072, -0.065, 0.098)), 0.034, 0.55,
    ("clouds", dict(base=8, salt=1316)), soft=0.61,
    desc="Layered orb webs — spokes and spiral rings over black silk sheet, dew nodes burning at the crossings. A FRACTURED OPALFIRE finish."),
 "fsk_circuit_trace": _R("Opal Circuit Trace", "e_circuit_trace", dict(p=6.6),
    1317, (0.0, 320.0, 1.1, 1.0, 3.2),
    _fan(0.055, (0.015, -0.015, 0.03, -0.025, 0.045, 0.305, 0.32)), 0.030, 0.55,
    ("drift", dict(angle=1.2, salt=1317)),
    desc="Dense PCB — dashed copper lanes, via rings, tinned pads; laddered copper on near-black solder mask. A FRACTURED OPALFIRE finish."),
 "fsk_mosaic_glass": _R("Opal Mosaic Glass", "e_mosaic_glass", dict(cell=7.3),
    1318, (0.0, 340.0, 0.9, 1.05, 0.0),
    _fan(0.50, (-0.06, 0.06, -0.03, 0.03, 0.12, -0.41, -0.395)), 0.034, 0.62,
    ("clouds", dict(base=6, salt=1318)), soft=0.44,
    desc="Grouted micro-tesserae — teal glass tiles with bevel terraces, grout black, corner glints live. A FRACTURED OPALFIRE finish."),
 # ── 6 rainbow flips (the "go totally crazy" lane): full 16-anchor wheel,
 # every hue carrying the same dark ladder, black pits between. Hue lives on
 # the ELEMENT (hires m_rbdom rebuilds the engine lattice — no patch camo).
 "fsk_prism_shatter": _R("Prism Shatter", "e_rainbow", dict(kind="prism", cell=6.6),
    1319, (0.0, 360.0, 1.0, 1.15, 0.0), list(_WHEEL16), 0.020, 0.62,
    ("rbdom", dict(hires=1, kind="prism", cell=6.6)), soft=0.62,
    desc="Shattered spectral glass — elongated shards, each its own wheel hue on the same dark ladder, gulfs black. A FRACTURED OPALFIRE finish."),
 "fsk_oilslick_weave": _R("Oilslick Weave", "e_rainbow", dict(kind="oilslick", tow=6.3),
    1320, (0.0, 300.0, 1.0, 1.15, 3.2), list(_WHEEL16), 0.020, 0.88,
    ("rbdom", dict(hires=1, kind="oilslick", tow=6.3)), soft=0.50,
    desc="Spectral satin — long woven floats stepping the hue wheel segment by segment, dimples black. A FRACTURED OPALFIRE finish."),
 "fsk_aurora_veil": _R("Aurora Veil", "e_rainbow", dict(kind="aurora", p=6.9),
    1321, (0.0, 330.0, 1.0, 1.1, 0.0), list(_WHEEL16), 0.020, 0.62,
    ("rbdom", dict(hires=1, kind="aurora", p=6.9)), soft=0.68,
    desc="Combed spectral curtains — swaying strands walking the whole wheel in golden steps, crests firing. A FRACTURED OPALFIRE finish."),
 "fsk_opal_pave": _R("Black Opal Pave", "e_rainbow", dict(kind="opal", grain=6.4, patch=20.0),
    1322, (0.0, 310.0, 1.0, 1.2, 3.2), list(_WHEEL16), 0.020, 0.75,
    ("rbdom", dict(hires=1, kind="opal", grain=6.4, patch=20.0)),
    desc="Black opal — near-black potch split by cracks, play-of-color patches of laddered diffraction grain. A FRACTURED OPALFIRE finish."),
 "fsk_spectrum_scales": _R("Spectrum Scales", "e_rainbow", dict(kind="spectrum", p=9.6),
    1323, (0.0, 340.0, 1.0, 1.15, 0.0), list(_WHEEL16), 0.020, 0.62,
    ("rbdom", dict(hires=1, kind="spectrum", p=9.6)), soft=0.85,
    desc="Rainbow snake-gradient — rhombic scales walking the wheel down every diagonal, seams black. A FRACTURED OPALFIRE finish."),
 "fsk_nebula_prism": _R("Nebula Prism", "e_rainbow", dict(kind="nebula", cell=8.4),
    1324, (0.0, 320.0, 1.0, 1.1, 3.2), list(_WHEEL16), 0.020, 0.70,
    ("rbdom", dict(hires=1, kind="nebula", cell=8.4)), soft=0.52,
    desc="Spectral cellular — terraced facet cells stepping down to black gulfs, one wheel hue per cell, nuclei alight. A FRACTURED OPALFIRE finish."),
}

GROUPS = {
    "FRACTURED OPALFIRE": OPALSKIN,
}


# ════════════════════════════════════════════════════════════════════════════
# KIT — CategoryKit subclass: hires rainbow domains + the NEAR-UNIFORM
# night-carrier spec (see [SPEC-MIRROR EXEMPTION] in the module header).
# ════════════════════════════════════════════════════════════════════════════

# [SPB-OPALSKIN-002 2026-08-03, parent verification round] ids that receive
# the WORK-scale POST-COMPOSITE snap-to-ladder in art_work below. These five
# archetypes measured a wide dark SPREAD (15-22 mass bins) but only 1-2
# PROMINENT terraces at 1024 — wide-but-smooth is the crush-law failure mode
# (a continuum collapses into one mushy flip on track). fsk_prism_shatter is
# included for the same terrace requirement alongside its pit deepening.
# The other 19 ids are accepted and MUST NOT change: the pass is fid-gated.
_RESNAP_IDS = frozenset({
    "fsk_snakeskin", "fsk_spectrum_scales", "fsk_knurl", "fsk_hex_mesh",
    "fsk_spider_silk", "fsk_prism_shatter",
    # [RAMP 2026-08-03] widening the ladder to full range spread these five's
    # sparse terraces below peak prominence — the dual snap re-terraces them.
    "fsk_damascus", "fsk_diamond_plate", "fsk_circuit_trace",
    "fsk_nebula_prism", "fsk_opal_pave", "fsk_chesterfield"})


class OpalskinKit(catlib.CategoryKit):

    def macro_maps(self, d):
        kind, mp = d.get("macro", ("none", {}))
        if mp.get("hires") and kind in self.extra_macro:
            M, D = self.extra_macro[kind](self.GEN, mp, int(d["seed"]), self)
            return (np.clip(M, 0.0, 1.0).astype(np.float32),
                    np.clip(D, 0.0, 1.0).astype(np.float32))
        return catlib.CategoryKit.macro_maps(self, d)

    def art_work(self, fid):
        """[SPB-OPALSKIN-002] WORK-scale snap-to-ladder AFTER the full
        composite, mirrored from the sibling fof_ module's proven pass: the
        GEN-stage snap in _walk was un-quantized downstream by the thin-film
        LUT roundtrip, the cubic upscale ringing, bloom and sparkle. Here the
        art is finished, so the snap is the LAST luma op: quantize the dark
        range onto the 6-rung bin-centered grid, luma-only multiplicative
        rescale (hue untouched); pits (< art 0.066) and veins / bright
        shoulders (> art 0.55) excluded; the unsnapped mid-gap sliver stays
        as the anti-alias line. fid-gated — the accepted 19 ship byte-same."""
        rgb = catlib.CategoryKit.art_work(self, fid)
        if fid not in _RESNAP_IDS:
            return rgb
        L0 = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1]
              + 0.114 * rgb[:, :, 2]).astype(np.float32)
        rgbq = cv2.GaussianBlur(rgb, (0, 0), 0.55)
        Ls = (0.299 * rgbq[:, :, 0] + 0.587 * rgbq[:, :, 1]
              + 0.114 * rgbq[:, :, 2]).astype(np.float32)
        # [RAMP 2026-08-03] re-derived from the full-range _LAD: unique rungs
        # 0.045 + k*0.182 art (k=0..5); window scales with the spacing; the
        # vein-preserve line moves above the new top rung (0.955).
        r0, stp = 0.045, 0.182
        tgt = r0 + np.clip(np.round((Ls - r0) / stp), 0.0, 5.0) * stp
        ms = (np.abs(tgt - Ls) <= 0.060) & (Ls > 0.12) & (Ls < 0.975)
        rgbq = rgbq * np.where(ms, tgt / np.maximum(Ls, 1e-4), 1.0)[..., None]
        # vein preserve: bright pixels keep pre-blur values
        rgb = np.where((L0 > 0.975)[..., None], rgb, rgbq)
        return np.clip(rgb, 0.0, 1.0).astype(np.float32)

    def mk(self, fid):
        """paint_fn: catlib crush pipeline unchanged. spec_fn: the measured
        fs_core_crimson night carrier (242/30/246) + <=4-std dither + a
        two-population G (+8 in paint pits, median unchanged). The paint's
        quantized dark ladder does ALL the angular work — that is the flip."""
        _spec0, _paint0 = catlib.CategoryKit.mk(self, fid)
        W = self.WORK
        salt = _crc(fid)
        kit = self

        def paint_fn(paint, shape, mask, seed, pm, bb):
            # [r6] FIXED crush denominator. catlib's paint_fn divides by
            # art.max(), which varies 0.70-0.99 with each finish's vein
            # strength — every finish got its OWN ladder scale, the
            # rung-to-histogram-bin alignment broke per id, and weak-vein ids
            # were rescaled BRIGHT (measured: scale_mail medL 0.361, pits 0).
            # art is already clipped <= 1, so a fixed x0.85 is the same cap
            # with a deterministic scale: final luma = art luma * 0.85.
            fh, fw = int(shape[0]), int(shape[1])
            srcp = np.asarray(paint, np.float32)[:, :, :3]
            if srcp.size and srcp.max() > 1.5:
                srcp = srcp / 255.0
            m2 = np.asarray(mask, np.float32)
            if m2.ndim == 3:
                m2 = m2[:, :, 0]
            if m2.shape[:2] != (fh, fw):
                m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
            aw = kit.art_work_cached(fid)
            # [RAMP 2026-08-03] 1.6x default zoom (center crop) + crush 0.93
            cz = int(round(W / _ZOOM)); oz = (W - cz) // 2
            art = cv2.resize(aw[oz:oz + cz, oz:oz + cz], (fw, fh),
                             interpolation=cv2.INTER_LINEAR)
            crushed = art * 0.93
            if fid in _RESNAP_IDS:
                # [SPB-OPALSKIN-002b] FINAL-RES snap: the WORK->render resize
                # blends plateau borders AFTER the WORK-scale snap (1152->1024
                # blends 1 pixel in 8) and rebuilt a 2-4 percent/bin continuum
                # between the terraces. This is the true END of the luma
                # pipeline — nothing mixes after it, so the ladder is razor at
                # every render res. Anchors = _LAD*0.85 = histogram bin
                # centers 4,8,...,24. Pits (<0.056) and veins (>0.47) exempt.
                Lf = (0.299 * crushed[:, :, 0] + 0.587 * crushed[:, :, 1]
                      + 0.114 * crushed[:, :, 2]).astype(np.float32)
                # [RAMP 2026-08-03] anchors re-derived: unique rungs = 0.045 +
                # k*0.182 art (k=0..5), x0.93 crush -> 0.0419 + k*0.1693 final.
                # Snap rungs 1-5 only (window widened with the spacing); the
                # bottom rung sits 0.009 above the pit floor, so it is left to
                # the WORK snap to avoid pulling pits up.
                r0f, stpf = 0.0419, 0.1693
                tgtf = r0f + np.clip(np.round((Lf - r0f) / stpf), 0.0, 5.0) * stpf
                msf = (np.abs(tgtf - Lf) <= 0.055) & (Lf > 0.12) & (Lf < 0.91)
                crushed = crushed * np.where(
                    msf, tgtf / np.maximum(Lf, 1e-4), 1.0)[..., None]
            kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
            out = srcp * (1.0 - kk) + crushed * kk
            return np.clip(out, 0.0, 1.0).astype(np.float32)

        def spec_fn(shape, mask, seed, sm):
            fh, fw = int(shape[0]), int(shape[1])
            m2 = np.asarray(mask, np.float32)
            if m2.ndim == 3:
                m2 = m2[:, :, 0]
            if m2.shape[:2] != (W, W):
                m2 = cv2.resize(m2, (W, W), interpolation=cv2.INTER_LINEAR)
            aw = kit.art_work_cached(fid)
            # [RAMP 2026-08-03] same 1.6x center crop as paint_fn — the pit
            # G-population must track the zoomed paint.
            cz = int(round(W / _ZOOM)); oz = (W - cz) // 2
            Lc = (0.299 * aw[oz:oz + cz, oz:oz + cz, 0]
                  + 0.587 * aw[oz:oz + cz, oz:oz + cz, 1]
                  + 0.114 * aw[oz:oz + cz, oz:oz + cz, 2]).astype(np.float32)
            pitm = cv2.resize((Lc < 0.10).astype(np.float32), (W, W),
                              interpolation=cv2.INTER_LINEAR)
            yy, xx = coords(W)
            dith = h2(np.floor(xx / 2.0), np.floor(yy / 2.0), salt) - 0.5
            M = _SPEC_M + dith * 4.0
            G = _SPEC_G + pitm * _SPEC_G_PIT + dith * 3.0
            B = _SPEC_B + dith * 4.0
            out = np.zeros((W, W, 4), np.uint8)
            mk_ = np.clip(m2, 0.0, 1.0)
            inv = 1.0 - mk_
            out[:, :, 0] = np.clip(M * mk_ + 4.0 * inv, 0, 255).astype(np.uint8)
            out[:, :, 1] = np.clip(G * mk_ + 120.0 * inv, 0, 255).astype(np.uint8)
            out[:, :, 2] = np.clip(B * mk_ + 16.0 * inv, 0, 255).astype(np.uint8)
            out[:, :, 3] = 255
            if (fh, fw) != (W, W):
                out = cv2.resize(out, (fw, fh), interpolation=cv2.INTER_LINEAR)
            return out

        return spec_fn, paint_fn


KIT = OpalskinKit(engines=ENGINES, groups=GROUPS, tag="fractured-opalskin",
                  extra_macro={"clouds": m_clouds, "drift": m_drift,
                               "rbdom": m_rbdom})

ALL = KIT.ALL

# ════════════════════════════════════════════════════════════════════════════
# MEASURED HUE CORRECTION — the anchor a recipe SETS is not the hue that
# RENDERS (asymmetric LUT hue density inside the hero window). Residuals are
# measured by _fractured_triage/colorfix.py and folded back here by
# apply_colorfix.py until every named id sits within 0.03 turn. Rainbow ids
# are gated on spread (>=8 even bins), not on a single target, and are not
# in the colorfix TARGET table. Hue-only: art_work re-applies per-pixel luma,
# so this moves NO band / ac / pk / sf / ladder metric.
_HUEFIX = {
 "fsk_basket_weave": -0.0174,
 "fsk_chainmail": -0.0276,
 "fsk_chesterfield": +0.0219,
 "fsk_circuit_trace": +0.0131,
 "fsk_croc_hide": +0.0254,
 "fsk_damascus": -0.0333,
 "fsk_diamond_plate": +0.0191,
 "fsk_feather_mantle": +0.0136,
 "fsk_herringbone": +0.0217,
 "fsk_hex_mesh": -0.0118,
 "fsk_knurl": -0.0123,
 "fsk_snakeskin": -0.0128,
 "fsk_stingray": -0.0098,
}

for _fid, _off in _HUEFIX.items():
    _r = ALL[_fid]
    _r["hues"] = [round((_h + _off) % 1.0, 4) for _h in _r["hues"]]

_ACCFIX = {
 "fsk_circuit_trace": -0.0382,
}

for _fid, _off in _ACCFIX.items():
    _r = ALL[_fid]
    _r["hues"] = _r["hues"][:-2] + [round((_h + _off) % 1.0, 4)
                                    for _h in _r["hues"][-2:]]

art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
