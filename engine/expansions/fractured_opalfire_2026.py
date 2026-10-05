# -*- coding: utf-8 -*-
"""FRACTURED OPALFIRE (2026-08-03) — the CRUSH-LAW category. 25 finishes, fof_*.

[SPB-OPALFIRE-001 2026-08-03] Owner on-track discovery, verbatim intent: the
color-flip color is a property of DARKNESS LEVEL, not paint hue. Under a
near-uniform metallic "night-carrier" spec, each distinct dark shade of paint
crosses from diffuse-dominant to specular-dominant at a DIFFERENT viewing
angle. Many quantized dark shades at fine scale = multiple flip colors firing
simultaneously and cascading as the car rotates; MIP blending at track
distance creates intermediate darks = even more states in motion. Proof
recipe: Soul Core Crimson's solid spec + Lava Flow paint crushed to 0.25x.
Owner: "This MAY be the way to sell hundreds of copies. Melt people's minds."

Every finish here is therefore a DARK QUANTIZED-LADDER FIELD:
  * a bounded-jitter lattice at the band pitch (8.5-11 px at GEN=640 =
    27-35 px on the 2048 car) whose cells each carry ONE of 6-8 distinct dark
    value levels (the LADDER — value steps at cell boundaries are in-band and
    band-positive; smooth macro value swings are sub-band and banned),
  * parity-interleaved level assignment (adjacent cells always differ by >=1
    level: the ladder itself concentrates spectral power AT the lattice
    fundamental instead of leaking a clumped i.i.d. skirt under r=64),
  * deep black PITS (seams / grout / craters, luma < 0.06) and thin BRIGHT
    VEINS (hot accents > 0.65 luma, 0.5-8 percent) — the two ladder ends,
  * smooth intra-cell RELIEF (amp ~0.03, sub-step so the terracing survives).

[SPEC-MIRROR EXEMPTION — CRUSH LAW 2026-08-03]
ALL 25 ids below ship a near-UNIFORM night-carrier spec instead of a spec
that mirrors the paint geometry. This is DELIBERATE and is the mechanism of
the whole category: the uniform metallic carrier (measured from
fs_core_crimson via the engine registry @512, 2026-08-03: median M=242.0
G=30.0 B=246.0, std 0.00 each) is what makes every distinct dark paint shade
flip at its own viewing angle. Any spec texture would fight the paint ladder
and localize the flip. The ONLY spec variation permitted is a subtle
two-population roughness bump (+10 G) on the deepest pits (paint-following,
fraction-capped at 15 percent so G std stays <= 4), which widens the pit
population's angular aperture — flip physics, not decoration.
Exempt ids (all 25):
  fof_molten_core, fof_gilded_pave, fof_copper_pahoehoe, fof_crimson_columns,
  fof_sapphire_shatter, fof_teal_drainage, fof_emerald_braid,
  fof_violet_burstfoam, fof_magenta_anticline, fof_amber_shardglass,
  fof_argent_hammer, fof_bronze_keels, fof_acid_circuit, fof_gilded_abyss,
  fof_ember_reef, fof_royal_terraces, fof_orchid_kagome, fof_frosted_pennies,
  fof_abyssal_vents, fof_petrol_swirl, fof_regalia_roundels,
  fof_patina_guilloche, fof_toxic_drips, fof_treasure_facets,
  fof_nebula_swirls

CRUSH-LAW GATES (category-specific, verified per finish at 512, seed=1234,
mask=ones, PYTHONHASHSEED=0, by _fractured_triage/verify_opalfire.py):
  median luma <= 0.32 | >=6 distinct 64-bin ladder levels in [0, 0.55]
  (each >=2 percent, SEPARATED into >=5 terrace clusters) | pit fraction
  (luma<0.06) in [0.03, 0.30] | vein fraction (luma>0.65) in [0.005, 0.08]
plus the house FRACTURED gates: car-band >= 0.65 per finish — MEASURED
MODULE FRONTIER (2026-08-03, 13 tuning rounds): median 0.7151, min 0.6525,
max 0.8628, all 25 >= 0.65. The 0.80 house median is NOT reachable for this
category without breaking its own gates: the defining components (deep pit
networks, discrete bright veins, hard rung steps) are broadband, and every
push past ~0.75 band bought sub-0.55 lag-1 ac (measured seesaw, e.g.
fof_petrol_swirl band 0.798/ac 0.504 vs shipped 0.863/0.633 only after the
spoke-hairline redesign; crack-web archetypes cap ~0.65-0.70). Documented
per the frontier clause. Other gates:
lag-1 ac >= 0.55, peakiness >= 0.30, shape fraction >= 0.55, fineness > 6.5,
coverage >= 56/64 (measured on the PAINT luma for this module — the spec is
exempt-uniform by design, so spec-channel coverage is meaningless here),
intra-module descriptor pair-cosine <= 0.55, < 2.0 s @512, <= 2.5 s @2048.

ARCHETYPE LEDGER (one DISTINCT compositional archetype per id — no repeats,
and deliberately differentiated from the sibling FROST/TEMPEST lattices):
  fof_molten_core      hierarchical crack-web   (THE FOUNDER: lava crack web at
                       4x classic frequency, amber ladder plates, gold vein seams)
  fof_gilded_pave      jittered brick cobbles   (chamfered rung-stepped bricks, sparse mortar veins)
  fof_copper_pahoehoe  buckled rope coils       (folded pahoehoe cords, incandescent grooves)
  fof_crimson_columns  polygonal columnar joints (near-regular columns, cracked rim rings, core dots)
  fof_sapphire_shatter biaxial shard lattice    (two rotated cut families, facet ramps, point glints)
  fof_teal_drainage    two-scale channel web    (dark drainage channels, levee lips, pond glints)
  fof_emerald_braid    lateral braid weave      (parallel cords swaying across each other)
  fof_violet_burstfoam burst-bubble craters     (popped domes, crescent rims, crater pits)
  fof_magenta_anticline folded ridge trains     (anticline ridges, terraced flanks, crest veins)
  fof_amber_shardglass elongated glass facets   (2.6:1 stretched shards, per-facet ramps, edge flashes)
  fof_argent_hammer    hammered dent field      (inverted dents, rim glints, pewter terraces)
  fof_bronze_keels     keeled hex scales        (pointed scales with raised keel midribs)
  fof_acid_circuit     rectilinear etched maze  (axis-aligned conduits, solder-node veins)
  fof_gilded_abyss     dark mudcrack net        (fat dark cracks, plate-parity families, core threads)
  fof_ember_reef       ember dome lattice       (checkered coal domes in terraced cold matrix)
  fof_royal_terraces   fault-block staircases   (diagonal strips of terraced steps, lit risers)
  fof_orchid_kagome    triaxial kagome weave    (three cord families at 60 degrees)
  fof_frosted_pennies  milled disc lattice      (coin discs, milled edge rings, icy ground)
  fof_abyssal_vents    vent plumes              (vent nodes, rising wavering dash plumes)
  fof_petrol_swirl     spiral-sector rosettes   (twisted hue sectors, straight grout, core glints)
  fof_regalia_roundels nested roundel rings     (2-3 concentric rings per cell, family per ring)
  fof_patina_guilloche engine-turned arc combs  (overlapping circular-brush rosette rows)
  fof_toxic_drips      beaded runnel drips      (vertical wavy stripes with drip beads)
  fof_treasure_facets  facet-fan gems           (per-cell brilliant-cut angular facet fans)
  fof_nebula_swirls    twin-arm spiral cells    (per-cell log-spiral swirls, cluster families)

CONTRACT: same as every FRACTURED module — install_into_engine(mono_reg,
base_reg=None), (spec_fn, paint_fn) pairs via the CategoryKit factory,
GROUPS key exactly "FRACTURED OPALFIRE". Determinism: catlib.rng
(np.random.default_rng) + coarse h2 cell hashes + zlib.crc32(fid) salts —
no hash(str) anywhere. Paint colorization is DIRECT value/hue ladder
composition (no thin-film LUT: its luma oscillation would un-quantize the
ladder, and the ladder IS the product). Hue therefore renders exactly at the
authored anchor (hueErr measured <= 0.03 turn in the harness, no damped-gain
iteration needed). satboost/LUT traps do not apply; saturation is authored
per family and value-fitted per pixel so dark rungs hold hue identity
un-clipped (the pale-vein solve keeps vein luma >= 0.87 pre-crush).

RECIPE SCHEMA (this module):
  name / engine / eargs (incl. salt=_crc(fid)) / seed / val (0.36 -> crush
  factor exactly 0.85 since art peaks at 1.0 in the vein cores) /
  families=[(hue_turns, sat), ...] / veinh=[hue per family] / veinsat /
  hdrift (hue drift per luma unit: darker rungs warmer/cooler) / jitamp /
  desc. Engines return (VAL, FAM, JIT, VEIN) at GEN=640: VAL = target art
  luma 0..1 (ladder + relief + pits), FAM = family index per pixel, JIT =
  per-cell 0..1 hash (hue jitter), VEIN = bright-accent blend weight.
"""
from __future__ import annotations

import zlib

import cv2
import numpy as np

from engine.expansions import fractured_catlib_2026 as catlib
from engine.expansions.fractured_catlib_2026 import (
    coords, fbm, frac, gauss, h2, n01, rng, rot, sstep, warp_pair,
)

_GEN = 640

# Night-carrier spec constants — MEASURED from fs_core_crimson via the engine
# registry @512 (2026-08-03): median M=242.0 G=30.0 B=246.0, std 0.00 each.
# Category tolerance: +-6 metal / +-10 rough / +-6 coat, std <= 4.
NIGHT_M = 242.0
NIGHT_G = 30.0
NIGHT_B = 246.0
PIT_G_BUMP = 10.0      # two-population roughness: deepest pits only (<=15%)
# [OWNER RAMP MANDATE 2026-08-03 pass 2] "bright colors MUCH brighter, darks
# much darker — like a color ramp gradient for a color, very bright to near
# black." Ladder extended from the dark half [0.105,0.555] to the FULL value
# range; veins white-hot; crush cap raised 0.85 -> 0.93 in this kit's mk.
_VEIN_L = 0.99         # vein-core target ART luma (0.93 crush -> 0.92 final)
_LAD_LO = 0.045        # global 8-rung ladder grid (art luma) — every
_LAD_HI = 0.955        # engine authors on it, the WORK snap enforces it
_ZOOM = 1.6            # default-scale bake: owner "defaults too small" — a
                       # 1/1.6 center crop of WORK = features 1.6x larger at
                       # zone scale 1.00 (scale DOWN in-app recovers fine)


def _crc(tag):
    """Deterministic string salt (no hash(str) — owner determinism law)."""
    return zlib.crc32(str(tag).encode()) & 0xFFFF


# ════════════════════════════════════════════════════════════════════════════
# IN-BAND LATTICE TOOLKIT — adapted from fractured_frost_2026 [SPB-FRACTURED-
# 090] (coarse-hash grids expanded INTER_NEAREST: identical field, ~6x cheaper)
# with one OPALFIRE addition: every lattice ALSO returns the winning cell's
# PARITY ((ci+cj) mod 2) so the ladder can parity-interleave its levels.
# ════════════════════════════════════════════════════════════════════════════

def _cg(n, salt, dj=0, di=0):
    """n x n deterministic cell-hash grid, rolled to address a neighbour tap."""
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


def _fat(d, w, soft=0.34):
    """Fat smooth ridge/seam profile from a distance field (0 = centre)."""
    w = np.asarray(w, np.float32)
    t = np.clip((d - w) / np.minimum(w * (float(soft) - 1.0), -1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _voro(res, cell, jit, salt):
    """Bounded-jitter Voronoi -> (F1/cell, (F2-F1)/cell edge distance,
    winning-cell hash, winning-cell parity)."""
    n, c = _celln(res, cell)
    yy, xx = coords(res)
    ci = np.floor(xx / c)
    cj = np.floor(yy / c)
    f1 = np.full((res, res), 1e12, np.float32)
    f2 = np.full((res, res), 1e12, np.float32)
    idw = np.zeros((res, res), np.float32)
    par = np.zeros((res, res), np.float32)
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
            par = np.where(m, ((ci + di + cj + dj) % 2.0).astype(np.float32), par)
    f1 = np.sqrt(f1, out=f1)
    f2 = np.sqrt(f2, out=f2)
    return (np.clip(f1 / c, 0.0, 1.5).astype(np.float32),
            np.clip((f2 - f1) / c, 0.0, 1.5).astype(np.float32), idw, par)


def _dots(res, cell, jit, salt):
    """Single-tap jittered dot lattice -> (0..1 radial dist, hash, parity)."""
    n, c = _celln(res, cell)
    yy, xx = coords(res)
    ci = np.floor(xx / c)
    cj = np.floor(yy / c)
    jx = (_up(_cg(n, salt), res) - 0.5) * float(jit) * c
    jy = (_up(_cg(n, salt + 11), res) - 0.5) * float(jit) * c
    d = np.hypot(xx - (ci + 0.5) * c - jx, yy - (cj + 0.5) * c - jy) / (c * 0.62)
    return (np.clip(d, 0.0, 1.0).astype(np.float32), _up(_cg(n, salt + 23), res),
            ((ci + cj) % 2.0).astype(np.float32))


def _polar_cells(res, cell, jit, salt, spin=0.0):
    """Per-cell local polar frame -> (radius/cell, angle, hash, parity)."""
    n, c = _celln(res, cell)
    yy, xx = coords(res)
    ci = np.floor(xx / c)
    cj = np.floor(yy / c)
    jx = (_up(_cg(n, salt), res) - 0.5) * float(jit) * c
    jy = (_up(_cg(n, salt + 11), res) - 0.5) * float(jit) * c
    dx = xx - (ci + 0.5) * c - jx
    dy = yy - (cj + 0.5) * c - jy
    rl = np.hypot(dx, dy) / (c * 0.62)
    th = np.arctan2(dy, dx)
    if spin:
        th = th + _up(_cg(n, salt + 29), res) * (6.2831853 * float(spin))
    return (np.clip(rl, 0.0, 2.2).astype(np.float32), th.astype(np.float32),
            _up(_cg(n, salt + 23), res), ((ci + cj) % 2.0).astype(np.float32))


def _uvrot(res, seed, salt, warp=0.0):
    yy, xx = coords(res)
    a = float(rng(seed, salt).uniform(0, np.pi))
    u, v = rot((yy, xx), a)
    if warp > 0.0:
        wu, wv = warp_pair(res, seed, salt + 1, warp)
        u = u + wu
        v = v + wv
    return u.astype(np.float32), v.astype(np.float32)


# ── THE LADDER (the category mechanism) ─────────────────────────────────────

# ── THE LADDER (the category mechanism) ─────────────────────────────────────
# [SPB-OPALFIRE-001b 2026-08-03, measured] A per-cell i.i.d. rung assignment
# leaks ~half its power under r=64 (smoke run: sub-band share 0.37-0.68, band
# 0.32-0.62 — FAIL). Fix: the rung ladder lives on its own FINE lattice
# (default 4.8 px at GEN = 15 px on the 2048 car, in the 8-32 px house band)
# with a BALANCED-BLOCK Latin design: every 2x2 super-block holds one full
# permutation of the four even rungs (rank-of-hash), so the block mean is
# CONSTANT (rank sum 0+1+2+3 = 6 always) and the i.i.d. clumping skirt under
# r=64 cancels exactly; the cell-parity bit interleaves the odd rungs on top
# -> K=8 levels whose spectral power sits AT the lattice fundamental
# (r ~ 107-133 at 512) and at the 2-cell block scale (r ~ 66) — both in-band.
# Structure (bricks / ropes / craters / webs, 8.5-10.5 px pitch) shifts the
# ladder only through small INTEGER zone biases, so every value in the field
# stays ON the 8-rung grid and the terracing survives verbatim.

def _rungs(res, salt, cell=4.2, pitc=0.0, veinc=0.0):
    """Balanced-block ladder lattice -> (idx 0..7, cellhash, pitcell mask,
    veincell mask). pitc/veinc gate a deterministic fraction of rung cells to
    the pit floor / vein flash (micro-pits and micro-flecks that survive any
    downsample, independent of structural seam width)."""
    n, c = _celln(res, cell)
    yy, xx = coords(res)
    ci = np.floor(xx / c)
    cj = np.floor(yy / c)
    sci = np.floor(ci / 2.0)
    scj = np.floor(cj / 2.0)
    pos = (ci % 2.0) + 2.0 * (cj % 2.0)
    q = h2(sci * 4.0 + pos, scj, salt + 101)
    r = np.zeros_like(q)
    for o in range(4):
        qo = h2(sci * 4.0 + float(o), scj, salt + 101)
        r += (q > qo).astype(np.float32) * (pos != float(o))
    par = ((ci + cj) % 2.0).astype(np.float32)
    idx = np.minimum(r * 2.0 + par, 7.0).astype(np.float32)
    hv = h2(ci, cj, salt + 113)
    g = h2(ci, cj, salt + 127)
    pc = (g < float(pitc)).astype(np.float32) if pitc > 0.0 else np.zeros_like(g)
    vcm = (g > 1.0 - float(veinc)).astype(np.float32) if veinc > 0.0 else np.zeros_like(g)
    return idx, hv, pc, vcm


def _lval(idx, K, lo, hi):
    """Ladder level -> target art luma (evenly spaced dark rungs)."""
    return (float(lo) + (float(hi) - float(lo))
            * np.asarray(idx, np.float32) / max(float(K - 1), 1.0)).astype(np.float32)


def _pitmix(v, pitmask, pitv):
    """Sink masked areas to pit luma (deep black, still hue-carrying).
    [SPB-OPALFIRE-001c, measured] the mask is BINARIZED (> 0.55): a soft pit
    edge is a continuous luma ramp from rung to pit — thousands of off-grid
    values that erase the histogram terracing (runsW 1-3). Hard chips + the
    resize AA line are the crush-law look."""
    m = (np.asarray(pitmask, np.float32) > 0.55).astype(np.float32)
    return v * (1.0 - m) + np.asarray(pitv, np.float32) * m


def _b3(hv, lo=-1.0):
    """Small integer zone bias from a hash: {lo, lo+1, lo+2} (default -1/0/+1).
    One-rung amplitude only, so the structural-scale i.i.d. skirt it adds is
    ~50x smaller than the full-ladder leak it replaces."""
    return (np.floor(np.asarray(hv, np.float32) * 3.0) + float(lo)).astype(np.float32)


# ════════════════════════════════════════════════════════════════════════════
# DIRECT HSV COLORIZE — vectorized, exact-luma (luma(hsv(h,s,v)) is LINEAR in
# both v and s: rgb = v*((1-s) + s*rgb_pure(h))), so the ladder rungs land on
# their authored luma EXACTLY and dark rungs keep their hue identity.
# ════════════════════════════════════════════════════════════════════════════

_LW = np.array([0.299, 0.587, 0.114], np.float32)


def _hsv_rgb(h, s, v):
    """Vectorized HSV -> RGB. h in turns, s/v 0..1. Any matching shapes."""
    h6 = (np.asarray(h, np.float32) % 1.0) * 6.0
    i = np.floor(h6)
    f = h6 - i
    s = np.asarray(s, np.float32)
    v = np.asarray(v, np.float32)
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i.astype(np.int32) % 6
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1).astype(np.float32)


def _luma_pure(h):
    """Luma of the fully saturated hue h (s=1, v=1)."""
    rgb = _hsv_rgb(h, np.ones_like(np.asarray(h, np.float32)),
                   np.ones_like(np.asarray(h, np.float32)))
    return (rgb[..., 0] * _LW[0] + rgb[..., 1] * _LW[1] + rgb[..., 2] * _LW[2])


class OpalfireKit(catlib.CategoryKit):
    """CategoryKit with the OPALFIRE art pipeline + night-carrier spec.

    art_work: direct ladder colorize (no thin-film LUT — see module header).
    mk:       paint_fn = parent crush contract; spec_fn = the near-uniform
              night-carrier (SPEC-MIRROR EXEMPTION above).
    """

    def art_work(self, fid):
        d = self.ALL[fid]
        seed = int(d["seed"])
        GEN = self.GEN
        VAL, FAM, JIT, VEIN = self.engines[d["engine"]](GEN, seed, **d.get("eargs", {}))
        fams = d["families"]
        ah = np.array([f[0] for f in fams], np.float32)
        asat = np.array([f[1] for f in fams], np.float32)
        fi = np.clip(np.asarray(FAM, np.float32).astype(np.int32), 0, len(fams) - 1)
        hue = (ah[fi] + (np.asarray(JIT, np.float32) - 0.5) * float(d.get("jitamp", 0.022))
               + float(d.get("hdrift", 0.0)) * (np.asarray(VAL, np.float32) - 0.35)) % 1.0
        sat = asat[fi]
        L = np.clip(np.asarray(VAL, np.float32), 0.012, 0.97)
        lfp = _luma_pure(hue)
        lf = (1.0 - sat) + sat * lfp
        V = L / np.maximum(lf, 1e-4)
        # value-fit: where the requested luma cannot be reached at the family
        # saturation (cool hues, bright rungs), desaturate JUST enough —
        # physically "brighter = paler", and the rung luma stays exact.
        over = V > 0.97
        satfit = np.clip((1.0 - L / 0.97)
                         / np.maximum(1.0 - lfp, 1e-4), 0.0, sat)
        # [OWNER RAMP MANDATE 2026-08-03] saturation FLOOR on bright rungs:
        # a bright red must stay RED, not drift pink — keep >=55% of family
        # sat and accept the luma miss (V caps at 0.97, so deep hues compress
        # their top rungs toward the vivid hue maximum instead of washing out).
        sat = np.where(over, np.maximum(satfit, sat * 0.55), sat)
        lf = (1.0 - sat) + sat * lfp
        V = np.minimum(L / np.maximum(lf, 1e-4), 0.97)
        rgb = _hsv_rgb(hue, sat, V)
        # BRIGHT VEINS: pale-hot per family, luma >= _VEIN_L at the cores so
        # the vein gate survives the 0.85 crush. Sat capped by the same
        # linear-luma solve. Core weight 1.0 -> art.max() == 1.0 exactly, so
        # the paint_fn crush factor is deterministic (val 0.36 * 2.4 -> 0.85).
        vh = np.asarray(d.get("veinh", [f[0] for f in fams]), np.float32)
        vlfp = _luma_pure(vh)
        # [RAMP 2026-08-03] vein sat floor 0.35x: white-hot cores keep a hue cast
        vsat = np.maximum(np.minimum(np.float32(d.get("veinsat", 0.42)),
                                     (1.0 - _VEIN_L) / np.maximum(1.0 - vlfp, 1e-4)),
                          np.float32(d.get("veinsat", 0.42)) * 0.35)
        vrgb = _hsv_rgb(vh, vsat, np.ones_like(vh))
        # [SPB-OPALFIRE-001c] vein weights QUANTIZED to {0, glow 0.45, core 1}:
        # a gaussian vein tail is a continuous luma sweep through every gap of
        # the ladder (runsW collapse). One glow tier = 8 more discrete states
        # (rung x glow), exactly the crush-law goal.
        Vq = np.clip(np.asarray(VEIN, np.float32), 0.0, 1.0)
        wq = np.where(Vq > 0.70, 1.0, np.where(Vq > 0.28, 0.45, 0.0)).astype(np.float32)
        w = wq[..., None]
        rgb = rgb * (1.0 - w) + vrgb[fi] * w
        rgb = cv2.resize(np.clip(rgb, 0.0, 1.0), (self.WORK, self.WORK),
                         interpolation=cv2.INTER_CUBIC)
        # SNAP-TO-LADDER [SPB-OPALFIRE-001b, measured]: the GEN->WORK cubic
        # resize smears every rung border into intermediate lumas (runsW 1-4,
        # terracing gone). Snap every pixel within +-0.026 of a rung back onto
        # the 8-rung grid (luma-only scale, hue untouched); pits (<0.062) and
        # veins (>0.70) excluded, the unsnapped mid-gap sliver stays as a thin
        # anti-alias line. Everything in the shipped art lies ON the ladder.
        rgb = cv2.GaussianBlur(rgb, (0, 0), 0.55)
        Ls = (rgb[:, :, 0] * _LW[0] + rgb[:, :, 1] * _LW[1]
              + rgb[:, :, 2] * _LW[2]).astype(np.float32)
        stp = (_LAD_HI - _LAD_LO) / 7.0
        tgt = _LAD_LO + np.clip(np.round((Ls - _LAD_LO) / stp), 0.0, 7.0) * stp
        dd = tgt - Ls
        wsn = cv2.resize(wq, (self.WORK, self.WORK), interpolation=cv2.INTER_LINEAR)
        # [RAMP 2026-08-03] window/bounds rescaled with the full-range grid
        # (stp 0.064 -> 0.130): top bound rises above the new top rung 0.955,
        # vein exclusion moves to >0.975 (veins now 0.99).
        ms = (np.abs(dd) <= 0.050) & (Ls > 0.062) & (Ls < 0.975) & (wsn < 0.2)
        rgb = rgb * np.where(ms, tgt / np.maximum(Ls, 1e-4), 1.0)[..., None]
        return np.clip(rgb, 0.0, 1.0).astype(np.float32)

    def mk(self, fid):
        """(spec_fn, paint_fn): parent crush paint + night-carrier spec."""
        val = float(self.ALL[fid].get("val", 0.36))
        WORK = self.WORK
        VAL_GAIN = self.VAL_GAIN
        kit = self

        def paint_fn(paint, shape, mask, seed, pm, bb):
            fh, fw = int(shape[0]), int(shape[1])
            src = np.asarray(paint, np.float32)[:, :, :3]
            if src.size and src.max() > 1.5:
                src = src / 255.0
            m2 = np.asarray(mask, np.float32)
            if m2.ndim == 3:
                m2 = m2[:, :, 0]
            if m2.shape[:2] != (fh, fw):
                m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
            aw = kit.art_work_cached(fid)
            # [RAMP 2026-08-03] 1.6x default zoom (center crop) + crush 0.93
            c = int(round(WORK / _ZOOM)); o = (WORK - c) // 2
            art = cv2.resize(aw[o:o + c, o:o + c], (fw, fh),
                             interpolation=cv2.INTER_LINEAR)
            crushed = art * (min(val * VAL_GAIN, 0.93) / max(float(art.max()), 1e-6))
            kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
            out = src * (1.0 - kk) + crushed * kk
            return np.clip(out, 0.0, 1.0).astype(np.float32)

        def spec_fn(shape, mask, seed, sm):
            # [SPEC-MIRROR EXEMPTION — CRUSH LAW 2026-08-03] near-uniform
            # night-carrier (fs_core_crimson class): M 242 / G 30 / B 246.
            # Only variation: +10 G on the deepest pit population (<=15% of
            # pixels, paint-following) — G std stays <= 3.6, median exact.
            fh, fw = int(shape[0]), int(shape[1])
            m2 = np.asarray(mask, np.float32)
            if m2.ndim == 3:
                m2 = m2[:, :, 0]
            if m2.shape[:2] != (fh, fw):
                m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
            aw = kit.art_work_cached(fid)
            # [RAMP 2026-08-03] same 1.6x center crop as paint_fn: the pit
            # G-population must stay aligned with the zoomed paint. Pit thr
            # tightened 0.045 -> 0.030 (bottom rung now sits AT 0.045 art).
            c = int(round(WORK / _ZOOM)); o = (WORK - c) // 2
            art = aw[o:o + c, o:o + c]
            L = (art[:, :, 0] * _LW[0] + art[:, :, 1] * _LW[1]
                 + art[:, :, 2] * _LW[2]).astype(np.float32)
            thr = min(0.030, float(np.percentile(L, 15.0)))
            pit = (L < thr).astype(np.float32)
            if pit.shape[:2] != (fh, fw):
                pit = cv2.resize(pit, (fw, fh), interpolation=cv2.INTER_LINEAR)
            G = NIGHT_G + PIT_G_BUMP * pit
            out = np.zeros((fh, fw, 4), np.uint8)
            mm = np.clip(m2, 0.0, 1.0)
            inv = 1.0 - mm
            out[:, :, 0] = np.clip(NIGHT_M * mm + 4.0 * inv, 0, 255).astype(np.uint8)
            out[:, :, 1] = np.clip(G * mm + 120.0 * inv, 0, 255).astype(np.uint8)
            out[:, :, 2] = np.clip(NIGHT_B * mm + 16.0 * inv, 0, 255).astype(np.uint8)
            out[:, :, 3] = 255
            return out

        return spec_fn, paint_fn


# ════════════════════════════════════════════════════════════════════════════
# 25 FIELD ENGINES — one per id, one archetype each (ledger in header).
# Contract: fn(res, seed, **eargs) -> (VAL, FAM, JIT, VEIN) float32 at res^2.
# VAL = 8-rung balanced ladder (integer zone biases only) + relief (<=0.03,
# sub-step) - pits; VEIN separate. Structure pitch 8.5-10.5 px at GEN.
# ════════════════════════════════════════════════════════════════════════════

def e_founder_web(res, seed, salt=0, c1=17.0, c2=7.8, vw=0.10, pw=0.15,
                  lo=_LAD_LO, hi=_LAD_HI, pit=0.030, relief=0.014, pitc=0.04):
    """[fof_molten_core] THE FOUNDER — the owner's exact discovery, baked:
    Lava Flow's glowing crack-web between cooled plates at 4x its classic
    frequency (classic = 121 px cells at 1152 work = 215 px on the 2048 car;
    4x -> ~54 px on car = 17 px at GEN, measured on flm_lava_flow_ignite
    _classic 2026-08-03), so 1.00x zone scale ships the owner's crushed 0.25x
    look. Plates carry an amber/brown 8-rung ladder pave with interior craze
    pits; the primary web itself is the GOLD VEIN system, with per-crack heat
    (some cracks run hotter — lava_flow's own law)."""
    _f1, e1, _h1, _p1 = _voro(res, c1, 0.50, salt + 1)
    f2, e2, hv2, _p2 = _voro(res, c2, 0.46, salt + 5)
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    idx = np.clip(ridx + _b3(hv2), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    dome = 0.5 + 0.5 * np.cos(np.clip(f2, 0.0, 1.0) * 3.14159)
    v = v + (dome - 0.5) * 2.0 * float(relief)
    craze = np.clip(_fat(e2, pw) + pc, 0.0, 1.0)
    v = _pitmix(v, craze, float(pit) * (0.7 + 0.6 * h2(np.floor(hv2 * 997.0), 1.0, salt + 9)))
    heat = 0.52 + 0.48 * fbm(res, res, rng(seed, salt + 11), 2, 5)
    vein = np.clip(_fat(e1, vw) * heat * 1.35, 0.0, 1.0)
    lip = np.clip(_fat(e1, vw * 2.6) - _fat(e1, vw), 0.0, 1.0)
    v = np.clip(v + (lip > 0.5).astype(np.float32) * 0.0643, 0.0, 1.0)
    return v, np.zeros_like(v), rhv, vein


def e_brick_pave(res, seed, salt=0, bw=7.6, bh=6.8, lo=_LAD_LO, hi=_LAD_HI,
                 mortar=0.26, pit=0.032, relief=0.014, vgate=0.78,
                 pitc=0.03, veinc=0.008):
    """[fof_gilded_pave] Jittered BRICK COBBLES: offset-row brick lattice,
    every brick domed and rung-biased, mortar joints are deep pits, and a
    SPARSE subset of joints runs molten (mortar veins)."""
    u, v0 = _uvrot(res, seed, salt + 1, 3.0)
    row = np.floor(v0 / float(bh))
    rj = (h2(row, 0.0, salt + 3) - 0.5) * 0.55 * float(bw)
    ux = u + (row % 2.0) * float(bw) * 0.5 + rj
    col = np.floor(ux / float(bw))
    cu = (frac(ux / float(bw)) - 0.5) * 2.0
    cvv = (frac(v0 / float(bh)) - 0.5) * 2.0
    # chamfered corners + a 0.7 px pre-snap soften: the rigid brick grid's
    # square-wave joint harmonics land past r=196 where lag-1 J0 goes
    # negative (ac 0.52 measured) — round them off, snap restores rungs
    dedge = (np.abs(cu) ** 3 + np.abs(cvv) ** 3) ** (1.0 / 3.0)
    dome = sstep(1.0, 0.30, dedge)
    ridx, rhv, pc, vc = _rungs(res, salt, 4.2, pitc, veinc)
    idx = np.clip(ridx + _b3(h2(col, row, salt + 5))
                  + np.round(1.5 * dome) - 1.0, 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    v = v + (dome - 0.55) * float(relief) * 2.0
    joint = np.clip(_fat(np.clip(1.0 - dedge, 0.0, 1.0), mortar) + pc, 0.0, 1.0)
    v = _pitmix(v, joint, float(pit) * (0.7 + 0.5 * h2(col, row, salt + 7)))
    hot = (h2(col, row, salt + 9) > float(vgate)).astype(np.float32)
    vein = np.clip(_fat(np.clip(1.0 - dedge, 0.0, 1.0), mortar * 0.55) * hot * 1.5
                   + vc, 0.0, 1.0)
    return np.clip(gauss(v, 0.7), 0.0, 1.0), np.zeros_like(v), rhv, vein


def e_rope_coils(res, seed, salt=0, p=9.6, fold=14.0, foldp=52.0, dash=15.0,
                 lo=_LAD_LO, hi=_LAD_HI, pit=0.030, relief=0.014, vgate=0.84,
                 pitc=0.018, veinc=0.005):
    """[fof_copper_pahoehoe] BUCKLED ROPE COILS: pahoehoe cords folded into
    nested arcs by a slow lateral buckle, per-dash rung bias, grooves between
    cords running deep; hot dash crests glow incandescent."""
    u, v0 = _uvrot(res, seed, salt + 1, 0.0)
    buck = np.sin(u / float(foldp) * 6.2831853
                  + fbm(res, res, rng(seed, salt + 3), 2, 4) * 2.6) * float(fold)
    q = (v0 + buck) / float(p)
    gloss = 0.5 + 0.5 * np.cos(6.2831853 * frac(q))
    ci = np.floor(q)
    cj = np.floor(u / float(dash))
    ridx, rhv, pc, vc = _rungs(res, salt, 4.2, pitc, veinc)
    idx = np.clip(ridx + _b3(h2(ci, cj, salt + 5)), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi) + (gloss - 0.5) * 2.0 * float(relief)
    groove = np.clip(1.0 - _fat(np.abs(frac(q) - 0.5), 0.44) + pc, 0.0, 1.0)
    v = _pitmix(v, np.clip(groove, 0.0, 1.0),
                float(pit) * (0.7 + 0.5 * h2(ci, cj, salt + 7)))
    hot = (h2(ci, cj, salt + 9) > float(vgate)).astype(np.float32)
    crest = _fat(np.abs(frac(q) - 0.5), 0.14)
    vein = np.clip(crest * hot * 1.6 + vc, 0.0, 1.0)
    return np.clip(v, 0.0, 1.0), np.zeros_like(v), rhv, vein


def e_columns(res, seed, salt=0, cell=8.4, lo=_LAD_LO, hi=_LAD_HI, rimw=0.13,
              pit=0.030, relief=0.014, vgate=0.82, corer=0.17, pitc=0.02):
    """[fof_crimson_columns] POLYGONAL COLUMNAR JOINTS: near-regular columns
    (low-jitter Voronoi), per-column rung bias with a domed cap, every column
    separated by a cracked RIM RING pit; hot columns carry a molten core."""
    f1, e1, hv, _par = _voro(res, cell, 0.30, salt + 1)
    cid = np.floor(hv * 997.0)
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    idx = np.clip(ridx + _b3(hv), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    cap = sstep(0.85, 0.15, f1)
    v = v + (cap - 0.5) * float(relief) * 2.0
    rim = np.clip(_fat(e1, rimw) + pc, 0.0, 1.0)
    v = _pitmix(v, rim, float(pit) * (0.7 + 0.5 * h2(cid, 2.0, salt + 5)))
    hot = (h2(cid, 3.0, salt + 7) > float(vgate)).astype(np.float32)
    core = np.exp(-((f1 / float(corer)) ** 2)) * hot
    vein = np.clip(core * 1.6, 0.0, 1.0)
    return np.clip(v, 0.0, 1.0), np.zeros_like(v), rhv, vein


def e_shatter(res, seed, salt=0, p1=7.8, p2=7.0, dang=0.96, lo=_LAD_LO,
              hi=_LAD_HI, cw=0.165, pit=0.028, ramp=0.012, vgate=0.78,
              pitc=0.015, veinc=0.004):
    """[fof_sapphire_shatter] BIAXIAL SHARD LATTICE: two rotated stripe-cut
    families dice the pane into angular shards; per-shard rung bias + a small
    facet ramp, cuts are thin pits, crossings glint."""
    u, v0 = _uvrot(res, seed, salt + 1, 4.0)
    c, s = np.cos(dang), np.sin(dang)
    a1 = u / float(p1)
    a2 = (u * c + v0 * s) / float(p2)
    s1 = np.floor(a1)
    s2 = np.floor(a2)
    ridx, rhv, pc, vc = _rungs(res, salt, 4.2, pitc, veinc)
    idx = np.clip(ridx + _b3(h2(s1, s2, salt + 3)), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    r1 = frac(a1)
    r2 = frac(a2)
    gdir = h2(s1, s2, salt + 5)
    v = v + ((r1 - 0.5) * np.cos(gdir * 6.2831853)
             + (r2 - 0.5) * np.sin(gdir * 6.2831853)) * float(ramp) * 2.0
    cut1 = _fat(np.abs(r1 - 0.5), cw)
    cut2 = _fat(np.abs(r2 - 0.5), cw)
    cut = np.clip(np.maximum(cut1, cut2) + pc, 0.0, 1.0)
    v = _pitmix(v, cut, float(pit) * (0.7 + 0.5 * h2(s1, s2, salt + 7)))
    hot = (h2(s1, s2, salt + 9) > float(vgate)).astype(np.float32)
    x1 = _fat(np.abs(r1 - 0.5), cw * 1.8)
    x2 = _fat(np.abs(r2 - 0.5), cw * 1.8)
    vein = np.clip(x1 * x2 * 2.8 * hot + vc, 0.0, 1.0)
    return np.clip(gauss(v, 0.50), 0.0, 1.0), np.zeros_like(v), rhv, vein


def e_drainage(res, seed, salt=0, c1=10.2, c2=6.2, w1=0.20, w2=0.13, lo=0.11,
               hi=0.56, pit=0.028, relief=0.013, pond=0.88, pitc=0.02,
               veinc=0.006):
    """[fof_teal_drainage] TWO-SCALE CHANNEL WEB: wide main drainage channels
    with narrow tributaries joining between them, channels running DEEP
    (pits), interfluve pads rung-biased with bright levee lips beside every
    channel; some pads hold a pond glint (vein)."""
    _fa, e1, _ha, _pa = _voro(res, c1, 0.55, salt + 1)
    f2, e2, hv, _p2 = _voro(res, c2, 0.50, salt + 5)
    cid = np.floor(hv * 997.0)
    ridx, rhv, pc, vc = _rungs(res, salt, 4.2, pitc, veinc)
    idx = np.clip(ridx + _b3(hv), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    pad = 0.5 + 0.5 * np.cos(np.clip(f2, 0.0, 1.0) * 3.14159)
    v = v + (pad - 0.5) * 2.0 * float(relief)
    main = _fat(e1, w1)
    trib = _fat(e2, w2) * (1.0 - main * 0.85)
    chan = np.clip(main + trib * 0.85 + pc, 0.0, 1.0)
    lev1 = np.clip(_fat(e1, w1 * 2.2) - _fat(e1, w1), 0.0, 1.0)
    v = np.clip(v + (lev1 > 0.5).astype(np.float32) * 0.0643, 0.0, 1.0)
    v = _pitmix(v, chan, float(pit) * (0.7 + 0.5 * h2(cid, 1.0, salt + 7)))
    hot = (h2(cid, 4.0, salt + 9) > float(pond)).astype(np.float32)
    vein = np.clip(np.exp(-((f2 / 0.22) ** 2)) * hot * 1.5 + vc, 0.0, 1.0)
    return v, np.zeros_like(v), rhv, vein


def e_braid(res, seed, salt=0, p=9.8, sway=3.4, wl=34.0, dash=14.0, lo=_LAD_LO,
            hi=_LAD_HI, duty=0.33, pit=0.028, relief=0.014, vgate=0.82,
            pitc=0.02, veinc=0.005):
    """[fof_emerald_braid] LATERAL BRAID WEAVE: two cord families running the
    SAME direction, swaying in antiphase so they cross and weave over-under
    (checker rise), per-dash rung bias; the gaps where neither cord covers
    run deep, crossings glint on hot segments."""
    u, v0 = _uvrot(res, seed, salt + 1, 0.0)
    sw = np.sin(u / float(wl) * 6.2831853
                + fbm(res, res, rng(seed, salt + 3), 2, 4) * 2.0) * float(sway)
    qA = (v0 + sw) / float(p)
    qB = (v0 - sw + float(p) * 0.5) / float(p)
    cordA = _fat(np.abs(frac(qA) - 0.5), duty)
    cordB = _fat(np.abs(frac(qB) - 0.5), duty)
    rise = 0.5 + 0.5 * np.sin(u / float(wl) * 6.2831853)
    topA = cordA * (0.55 + 0.45 * rise)
    topB = cordB * (1.0 - 0.45 * rise)
    isA = (topA >= topB).astype(np.float32)
    ci = np.where(isA > 0.5, np.floor(qA), np.floor(qB))
    cj = np.floor(u / float(dash))
    ridx, rhv, pc, vc = _rungs(res, salt, 4.2, pitc, veinc)
    idx = np.clip(ridx + _b3(h2(ci, cj + isA * 37.0, salt + 5)), 0.0, 7.0)
    gloss = np.where(isA > 0.5, 0.5 + 0.5 * np.cos(6.2831853 * frac(qA)),
                     0.5 + 0.5 * np.cos(6.2831853 * frac(qB)))
    v = _lval(idx, 8, lo, hi) + (gloss - 0.5) * 2.0 * float(relief)
    gap = np.clip(1.0 - np.maximum(cordA, cordB) * 1.30 + pc, 0.0, 1.0)
    v = _pitmix(v, gap, float(pit) * (0.7 + 0.5 * h2(ci, cj, salt + 7)))
    hot = (h2(ci, cj, salt + 9) > float(vgate)).astype(np.float32)
    vein = np.clip(cordA * cordB * 2.6 * hot + vc, 0.0, 1.0)
    return np.clip(v, 0.0, 1.0), np.zeros_like(v), rhv, vein


def e_burstfoam(res, seed, salt=0, cell=9.8, lo=_LAD_LO, hi=_LAD_HI, rimw=0.16,
                pit=0.026, relief=0.014, vgate=0.70, pitc=0.02):
    """[fof_violet_burstfoam] BURST-BUBBLE CRATERS: every cell a popped dome —
    crater floor sunk to pit dark, a bright CRESCENT rim arc on the lit side
    only, rung-terraced ground between craters; hot craters flash."""
    d, hv, _par = _dots(res, cell, 0.52, salt + 1)
    n, c = _celln(res, cell)
    yy, xx = coords(res)
    ci = np.floor(xx / c)
    cj = np.floor(yy / c)
    jx = (_up(_cg(n, salt + 1), res) - 0.5) * 0.52 * c
    jy = (_up(_cg(n, salt + 1 + 11), res) - 0.5) * 0.52 * c
    th = np.arctan2(yy - (cj + 0.5) * c - jy, xx - (ci + 0.5) * c - jx)
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    idx = np.clip(ridx + _b3(hv), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    flank = np.clip(sstep(0.95, 0.55, d) - sstep(0.50, 0.20, d), 0.0, 1.0)
    v = v + flank * float(relief) * 2.0
    crater = np.clip(sstep(0.48, 0.30, d) + pc, 0.0, 1.0)
    v = _pitmix(v, crater, float(pit) * (0.7 + 0.5 * h2(ci, cj, salt + 5)))
    lit = np.clip(np.cos(th - h2(ci, cj, salt + 7) * 6.2831853), 0.0, 1.0) ** 1.0
    rim = _fat(np.abs(d - 0.52), rimw) * lit
    v = np.clip(v + ((rim > 0.45) & (lit > 0.30)).astype(np.float32) * 0.0643, 0.0, 1.0)
    hot = (h2(ci, cj, salt + 9) > float(vgate)).astype(np.float32)
    vein = np.clip(rim * hot * 1.8, 0.0, 1.0)
    return v, np.zeros_like(v), rhv, vein


def e_anticline(res, seed, salt=0, p=9.8, dash=11.0, drift=5.0, lo=_LAD_LO,
                hi=_LAD_HI, pit=0.028, vgate=0.78, pitc=0.02, veinc=0.004):
    """[fof_magenta_anticline] FOLDED RIDGE TRAINS: parallel anticline ridges;
    each flank a 2-step terrace staircase (quantized distance from the crest,
    stacked on the rung field), gutters between ridges run deep, hot segments
    carry a lit crest vein."""
    u, v0 = _uvrot(res, seed, salt + 1, 0.0)
    wu, _wv = warp_pair(res, seed, salt + 3, float(drift))
    q = (v0 + wu) / float(p)
    tri = np.abs(frac(q) - 0.5) * 2.0          # 0 at crest, 1 in gutter
    ci = np.floor(q)
    cj = np.floor(u / float(dash))
    ridx, rhv, pc, vc = _rungs(res, salt, 4.2, pitc, veinc)
    step = np.clip(np.floor((1.0 - tri) * 3.0) - 1.0, -1.0, 1.0)
    idx = np.clip(ridx + step + _b3(h2(ci, cj, salt + 5)) * 0.0, 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    gutter = np.clip(sstep(0.80, 0.97, tri) + pc, 0.0, 1.0)
    v = _pitmix(v, gutter, float(pit) * (0.7 + 0.5 * h2(ci, cj, salt + 7)))
    hot = (h2(ci, cj, salt + 9) > float(vgate)).astype(np.float32)
    crest = _fat(tri, 0.18)
    vein = np.clip(crest * hot * 1.7 + vc, 0.0, 1.0)
    return np.clip(v, 0.0, 1.0), np.zeros_like(v), rhv, vein


def _voro_aniso(res, cw, ch, jit, salt):
    """Anisotropic bounded-jitter Voronoi (separate cell width/height in px)
    -> (F1 norm, edge norm, hash, parity). For elongated shard archetypes."""
    nx = max(2, int(round(float(res) / float(cw))))
    ny = max(2, int(round(float(res) / float(ch))))
    cx = float(res) / nx
    cy = float(res) / ny
    yy, xx = coords(res)
    ci = np.floor(xx / cx)
    cj = np.floor(yy / cy)
    f1 = np.full((res, res), 1e12, np.float32)
    f2 = np.full((res, res), 1e12, np.float32)
    idw = np.zeros((res, res), np.float32)
    par = np.zeros((res, res), np.float32)
    j = float(jit)
    ii = np.arange(max(nx, ny), dtype=np.float32)

    def cgrid(s, dj, di):
        g = h2(ii[None, :nx], ii[:ny, None], s)
        if dj or di:
            g = np.roll(np.roll(g, -dj, 0), -di, 1)
        return cv2.resize(np.ascontiguousarray(g, np.float32), (res, res),
                          interpolation=cv2.INTER_NEAREST)

    sc = min(cx, cy)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            ax = cgrid(salt, dj, di)
            ay = cgrid(salt + 40, dj, di)
            dx = (ci + di + 0.5 + (ax - 0.5) * j) * cx - xx
            dy = (cj + dj + 0.5 + (ay - 0.5) * j) * cy - yy
            d = (dx / cx * sc) ** 2 + (dy / cy * sc) ** 2
            m = d < f1
            np.minimum(f2, np.maximum(f1, d), out=f2)
            np.minimum(f1, d, out=f1)
            idw = np.where(m, cgrid(salt + 80, dj, di), idw)
            par = np.where(m, ((ci + di + cj + dj) % 2.0).astype(np.float32), par)
    f1 = np.sqrt(f1, out=f1)
    f2 = np.sqrt(f2, out=f2)
    return (np.clip(f1 / sc, 0.0, 1.5).astype(np.float32),
            np.clip((f2 - f1) / sc, 0.0, 1.5).astype(np.float32), idw, par)


def e_shardglass(res, seed, salt=0, cw=8.8, ch=4.4, lo=_LAD_LO, hi=_LAD_HI,
                 gw=0.11, pit=0.028, ramp=0.014, vgate=0.80, pitc=0.02,
                 veinc=0.004):
    """[fof_amber_shardglass] ELONGATED GLASS FACETS: 2.5:1 stretched shards
    (anisotropic Voronoi), per-facet rung bias + a small tilted ramp, thin
    pit gaps between facets; hot facet edges flash."""
    f1, e1, hv, _par = _voro_aniso(res, cw, ch, 0.62, salt + 1)
    cid = np.floor(hv * 997.0)
    ridx, rhv, pc, vc = _rungs(res, salt, 4.2, pitc, veinc)
    idx = np.clip(ridx + _b3(hv), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    yy, xx = coords(res)
    gdir = h2(cid, 5.0, salt + 3) * 6.2831853
    rmp = np.cos(gdir) * (xx / res - 0.5) + np.sin(gdir) * (yy / res - 0.5)
    rmp = frac(rmp * (res / 9.0) * 0.14 + hv * 7.0)
    v = v + (rmp - 0.5) * 2.0 * float(ramp)
    cut = np.clip(_fat(e1, gw) + pc, 0.0, 1.0)
    v = _pitmix(v, cut, float(pit) * (0.7 + 0.5 * h2(cid, 1.0, salt + 5)))
    hot = (h2(cid, 2.0, salt + 7) > float(vgate)).astype(np.float32)
    edge = np.clip(_fat(e1, gw * 2.0) - _fat(e1, gw), 0.0, 1.0)
    vein = np.clip(edge * hot * 2.0 + vc, 0.0, 1.0)
    return np.clip(v, 0.0, 1.0), np.zeros_like(v), rhv, vein


def e_hammer(res, seed, salt=0, cell=6.2, lo=_LAD_LO, hi=_LAD_HI, rimw=0.16,
             pit=0.030, vgate=0.70, deep=0.86, pitc=0.02):
    """[fof_argent_hammer] HAMMERED DENT FIELD: inverted dents on a jittered
    lattice, every dent floor 2 rungs darker (a sparse deepest population
    drops to pit), a lit rim glint arc on the strike side; hot dents spark."""
    d, hv, _par = _dots(res, cell, 0.50, salt + 1)
    n, c = _celln(res, cell)
    yy, xx = coords(res)
    ci = np.floor(xx / c)
    cj = np.floor(yy / c)
    jx = (_up(_cg(n, salt + 1), res) - 0.5) * 0.50 * c
    jy = (_up(_cg(n, salt + 1 + 11), res) - 0.5) * 0.50 * c
    th = np.arctan2(yy - (cj + 0.5) * c - jy, xx - (ci + 0.5) * c - jx)
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    dent = sstep(0.78, 0.30, d)
    idx = np.clip(ridx - np.round(2.0 * dent), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    isdeep = (h2(ci, cj, salt + 5) > float(deep)).astype(np.float32)
    v = _pitmix(v, np.clip(dent * isdeep + pc, 0.0, 1.0),
                float(pit) * (0.8 + 0.4 * h2(ci, cj, salt + 6)))
    lit = np.clip(np.cos(th - 0.9), 0.0, 1.0) ** 2
    rim = _fat(np.abs(d - 0.66), rimw) * lit
    v = np.clip(v + ((rim > 0.45) & (lit > 0.30)).astype(np.float32) * 0.0643, 0.0, 1.0)
    hot = (h2(ci, cj, salt + 7) > float(vgate)).astype(np.float32)
    vein = np.clip(rim * hot * 2.0, 0.0, 1.0)
    return v, np.zeros_like(v), rhv, vein


def e_keels(res, seed, salt=0, p=10.0, lo=_LAD_LO, hi=_LAD_HI, keelw=0.14,
            gw=0.10, pit=0.028, relief=0.015, vgate=0.76, pitc=0.02):
    """[fof_bronze_keels] KEELED HEX SCALES: hex-packed pointed scales, each
    with a raised keel midrib at its own heading, faces sloping keel-to-grout,
    per-scale rung bias; hot scales run their keel incandescent."""
    u, v0 = _uvrot(res, seed, salt + 1, 3.0)
    hx = u / float(p)
    hy = v0 / float(p) * 1.1547
    row = np.floor(hy)
    hxo = hx + (row % 2) * 0.5
    col = np.floor(hxo + 0.5)
    cu = hxo - col
    cvv = hy - np.floor(hy + 0.5)
    dc = np.sqrt(cu * cu + cvv * cvv)
    hvx = h2(col, row, salt + 3)
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    idx = np.clip(ridx + _b3(hvx), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    kdir = h2(col, row, salt + 5) * 3.14159
    dline = np.abs(-np.sin(kdir) * cu + np.cos(kdir) * cvv)
    v = v + (1.0 - np.clip(dline * 3.2, 0.0, 1.0)) * float(relief) \
        - np.clip(dc * 1.6, 0.0, 1.0) * float(relief) * 0.7
    keel = _fat(dline, keelw) * sstep(0.52, 0.30, dc)
    v = np.clip(v + (keel > 0.5).astype(np.float32) * 0.0643, 0.0, 1.0)
    grout = np.clip(_fat(np.clip(0.55 - dc, 0.0, 1.0), gw) + pc, 0.0, 1.0)
    v = _pitmix(v, grout, float(pit) * (0.7 + 0.5 * h2(col, row, salt + 7)))
    hot = (h2(col, row, salt + 9) > float(vgate)).astype(np.float32)
    vein = np.clip(keel * hot * 1.9, 0.0, 1.0)
    return v, np.zeros_like(v), rhv, vein


def e_circuit(res, seed, salt=0, cell=6.2, lo=_LAD_LO, hi=_LAD_HI, tw=0.17,
              pit=0.026, relief=0.012, node=0.84, pitc=0.035):
    """[fof_acid_circuit] RECTILINEAR ETCHED MAZE: axis-aligned conduit traces
    (each grid cell owns a horizontal OR vertical trace, hash-chosen, so
    traces meander in right angles) biased +2 rungs over an etched substrate
    biased -1; trace edges etched deep; junction cells carry a solder node."""
    u, v0 = _uvrot(res, seed, salt + 1, 0.0)
    c = float(cell)
    ci = np.floor(u / c)
    cj = np.floor(v0 / c)
    cu = (frac(u / c) - 0.5) * 2.0
    cvv = (frac(v0 / c) - 0.5) * 2.0
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    # checker the trace directions: an i.i.d. direction gate chains same-
    # direction cells into long corridors = sub-band stripes (measured)
    chk = ((ci + cj) % 2.0).astype(np.float32)
    flp = (h2(ci, cj, salt + 5) < 0.25).astype(np.float32)
    horiz = np.abs(chk - flp)
    tH = _fat(np.abs(cvv), tw) * horiz
    tV = _fat(np.abs(cu), tw) * (1.0 - horiz)
    trace = np.clip(tH + tV, 0.0, 1.0)
    idx = np.clip(ridx - 1.0 + np.round(3.0 * sstep(0.35, 0.75, trace)), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    v = v + (np.cos(cu * 3.14159) * np.cos(cvv * 3.14159)) * float(relief)
    etch = np.clip(np.maximum(_fat(np.abs(cvv), tw * 2.2) * horiz,
                              _fat(np.abs(cu), tw * 1.9) * (1.0 - horiz)) - trace
                   + pc, 0.0, 1.0)
    v = _pitmix(v, etch, float(pit) * (0.7 + 0.5 * h2(ci, cj, salt + 9)))
    isnode = (h2(ci, cj, salt + 11) > float(node)).astype(np.float32)
    nd = np.exp(-(((cu * cu + cvv * cvv) / 0.10) ** 1.2)) * isnode
    vein = np.clip(nd * 1.8, 0.0, 1.0)
    return np.clip(v, 0.0, 1.0), np.zeros_like(v), rhv, vein


# ── MULTI-HUE ENGINES (families follow the geometry) ────────────────────────

def e_mudcrack(res, seed, salt=0, cell=7.2, lo=_LAD_LO, hi=_LAD_HI, cw=0.24,
               pit=0.026, relief=0.014, vw=0.13, vgate=0.52, pitc=0.035):
    """[fof_gilded_abyss] DARK MUDCRACK NET: fat dark cracks between rung-
    terraced plates; the FAMILY follows plate parity (gold plates interleaved
    with sapphire plates), thin molten threads along crack cores on a sparse
    heat gate. Value-inverse of the founder (dark seams, no bright web)."""
    f1, e1, hv, par = _voro(res, cell, 0.52, salt + 1)
    cid = np.floor(hv * 997.0)
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    idx = np.clip(ridx + _b3(hv), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    dome = 0.5 + 0.5 * np.cos(np.clip(f1, 0.0, 1.0) * 3.14159)
    v = v + (dome - 0.5) * 2.0 * float(relief)
    crack = np.clip(_fat(e1, cw) + pc, 0.0, 1.0)
    v = _pitmix(v, crack, float(pit) * (0.7 + 0.5 * h2(cid, 1.0, salt + 3)))
    # per-plate hash heat gate: an fbm heat field clustered the molten
    # threads at MACRO scale (probe: r0-4 held 26% of sub-band power)
    # per-PLATE heat gate: a 20px heat lattice made the bright veins cluster
    # at r~26 (sub-band envelope of the highest-contrast component)
    hd20, hhv20, _hp20 = _dots(res, 12.0, 0.5, salt + 5)
    heat = hhv20
    thr = (heat > float(vgate)).astype(np.float32)
    vein = np.clip(_fat(e1, vw) * thr * 1.6, 0.0, 1.0)
    return np.clip(v, 0.0, 1.0), par, rhv, vein


def e_ember_reef(res, seed, salt=0, cell=6.4, lo=_LAD_LO, hi=_LAD_HI, emb=0.55,
                 pit=0.028, relief=0.013, vgate=0.74, pitc=0.02):
    """[fof_ember_reef] EMBER DOME LATTICE: glowing coal domes (crimson
    family, +2 rung bias) packed among rung-terraced cold matrix pads (teal
    family, -1); inter-cell gaps run black, the hottest coals carry a
    white-gold core vein."""
    d, hv, _par = _dots(res, cell, 0.55, salt + 1)
    n, c = _celln(res, cell)
    yy, xx = coords(res)
    ci = np.floor(xx / c)
    cj = np.floor(yy / c)
    chk = ((ci + cj) % 2.0).astype(np.float32)
    flip = (h2(ci, cj, salt + 3) < 0.08).astype(np.float32)
    isemb = np.abs(chk - flip) * np.clip(float(emb) * 2.0, 0.0, 1.0)
    dome = sstep(0.88, 0.30, d) * isemb
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    idx = np.clip(ridx + np.round(2.0 * dome) - 1.0 * (1.0 - isemb), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    v = v + (0.5 + 0.5 * np.cos(np.clip(d, 0.0, 1.0) * 3.14159) - 0.5) \
        * 2.0 * float(relief) * (1.0 - isemb)
    gap = np.clip(sstep(0.86, 0.99, d) * isemb + pc, 0.0, 1.0)
    v = _pitmix(v, gap, float(pit) * (0.7 + 0.5 * h2(ci, cj, salt + 5)))
    hot = (h2(ci, cj, salt + 7) > float(vgate)).astype(np.float32) * isemb
    vein = np.clip(np.exp(-((d / 0.32) ** 2)) * hot * 1.6, 0.0, 1.0)
    fam = 1.0 - isemb  # 0 = ember (crimson), 1 = matrix (teal)
    return np.clip(v, 0.0, 1.0), fam, rhv, vein


def e_terrace_strips(res, seed, salt=0, sw=6.6, sh=6.2, lo=_LAD_LO, hi=_LAD_HI,
                     riser=0.10, pit=0.028, vgate=0.66, pitc=0.03,
                     veinc=0.004):
    """[fof_royal_terraces] FAULT-BLOCK STAIRCASES: diagonal strips, each a
    run of rung-biased step tiles (random per tile — no sawtooth macro),
    risers etched deep with a lit top edge on hot tiles; FAMILY alternates
    per strip (violet / amber)."""
    u, v0 = _uvrot(res, seed, salt + 1, 2.5)
    strip = np.floor(u / float(sw))
    jump = h2(strip, 0.0, salt + 3) * float(sh)
    step = np.floor((v0 + jump) / float(sh))
    ridx, rhv, pc, vc = _rungs(res, salt, 4.2, pitc, veinc)
    idx = np.clip(ridx + _b3(h2(strip, step, salt + 5)), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    sv = frac((v0 + jump) / float(sh))
    rz = _fat(np.abs(sv - 0.5), riser * 0.5)
    wall = _fat(np.abs(frac(u / float(sw)) - 0.5), 0.06)
    v = _pitmix(v, np.clip(rz + wall + pc, 0.0, 1.0),
                float(pit) * (0.7 + 0.5 * h2(strip, step, salt + 7)))
    hot = (h2(strip, step, salt + 9) > float(vgate)).astype(np.float32)
    lip = np.clip(_fat(np.abs(sv - 0.44), 0.10), 0.0, 1.0)
    vein = np.clip(lip * hot * 1.8 + vc, 0.0, 1.0)
    fam = (strip % 2.0).astype(np.float32)  # violet / amber by strip
    return np.clip(v, 0.0, 1.0), fam, rhv, vein


def e_kagome(res, seed, salt=0, p=8.6, duty=0.24, dash=11.0, lo=_LAD_LO,
             hi=_LAD_HI, pit=0.024, relief=0.013, vgate=0.86, pitc=0.015,
             veinc=0.004):
    """[fof_orchid_kagome] TRIAXIAL KAGOME WEAVE: three cord families at 60
    degrees, each family its own hue (emerald / magenta / orchid), triangular
    holes between cords running deep; hot cord dashes glint."""
    u, v0 = _uvrot(res, seed, salt + 1, 3.0)
    best = np.full(u.shape, -1.0, np.float32)
    fam = np.zeros_like(u)
    ci_w = np.zeros_like(u)
    cj_w = np.zeros_like(u)
    ph_w = np.zeros_like(u)
    for k in range(3):
        a = k * 1.0471976
        qk = (u * np.cos(a) + v0 * np.sin(a)) / float(p)
        ck = _fat(np.abs(frac(qk) - 0.5), duty) * (1.0 - 0.06 * k)
        m = ck > best
        best = np.where(m, ck, best)
        fam = np.where(m, float(k), fam)
        ci_w = np.where(m, np.floor(qk), ci_w)
        pk = (u * np.cos(a + 1.5707963) + v0 * np.sin(a + 1.5707963)) / float(dash)
        cj_w = np.where(m, np.floor(pk), cj_w)
        ph_w = np.where(m, frac(qk), ph_w)
    ridx, rhv, pc, vc = _rungs(res, salt, 4.2, pitc, veinc)
    idx = np.clip(ridx + _b3(h2(ci_w, cj_w + fam * 53.0, salt + 3)), 0.0, 7.0)
    gloss = 0.5 + 0.5 * np.cos(6.2831853 * ph_w)
    v = _lval(idx, 8, lo, hi) + (gloss - 0.5) * 2.0 * float(relief)
    hole = np.clip(1.0 - best * 1.25 + pc, 0.0, 1.0)
    v = _pitmix(v, hole, float(pit) * (0.7 + 0.5 * h2(ci_w, cj_w, salt + 5)))
    hot = (h2(ci_w, cj_w + fam * 11.0, salt + 7) > float(vgate)).astype(np.float32)
    vein = np.clip(best * hot * 1.4 * sstep(0.55, 0.95, best) + vc, 0.0, 1.0)
    return np.clip(v, 0.0, 1.0), fam, rhv, vein


def e_pennies(res, seed, salt=0, cell=9.2, gcell=6.6, lo=_LAD_LO, hi=_LAD_HI,
              pit=0.028, relief=0.012, vgate=0.52, pitc=0.015):
    """[fof_frosted_pennies] MILLED DISC LATTICE: flat coin discs (+2 rung
    bias, copper family) with a milled edge ring, dropped onto icy rung-
    terraced ground (pale ice family, -1), a dark shadow moat around every
    coin; hot coins throw an edge glint arc."""
    d, hv, _par = _dots(res, cell, 0.38, salt + 1)
    n, c = _celln(res, cell)
    yy, xx = coords(res)
    ci = np.floor(xx / c)
    cj = np.floor(yy / c)
    jx = (_up(_cg(n, salt + 1), res) - 0.5) * 0.38 * c
    jy = (_up(_cg(n, salt + 1 + 11), res) - 0.5) * 0.38 * c
    th = np.arctan2(yy - (cj + 0.5) * c - jy, xx - (ci + 0.5) * c - jx)
    _fg, eg, hg, _pg = _voro(res, gcell, 0.50, salt + 21)
    disc = sstep(0.70, 0.62, d)
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    idx = np.clip(ridx + np.round(3.0 * disc) - 1.0, 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    v = v + (0.5 + 0.5 * np.cos(np.clip(_fg, 0.0, 1.0) * 3.14159) - 0.5) \
        * 2.0 * float(relief) * (1.0 - disc) + (0.5 - d) * float(relief) * disc
    mill = _fat(np.abs(d - 0.60), 0.10)
    v = np.clip(v + mill * 0.05, 0.0, 1.0)
    gseam = _fat(eg, 0.10) * (1.0 - disc)
    moat = _fat(np.abs(d - 0.76), 0.075) * (1.0 - disc)
    v = _pitmix(v, np.clip(gseam + moat + pc, 0.0, 1.0),
                float(pit) * (0.8 + 0.4 * hg))
    fam = 1.0 - disc  # 0 = coin (copper), 1 = ground (ice)
    lit = np.clip(np.cos(th - h2(ci, cj, salt + 5) * 6.2831853), 0.0, 1.0) ** 1.0
    hot = (h2(ci, cj, salt + 7) > float(vgate)).astype(np.float32)
    vein = np.clip(mill * lit * hot * 3.4, 0.0, 1.0)
    return np.clip(v, 0.0, 1.0), fam, np.where(disc > 0.5, rhv, hg), vein


def e_vents(res, seed, salt=0, p=6.4, wl=36.0, sway=1.4, dl=7.0, bed=6.4,
            lo=_LAD_LO, hi=_LAD_HI, pit=0.026, relief=0.012, ventc=22.0,
            vgate=0.60, pitc=0.02):
    """[fof_abyssal_vents] VENT PLUMES: ember dash plumes rising vertically
    with a slow sway (+2 rung bias, ember family) over a deep-blue rung-
    terraced bed (blue family, -1); vent mouths on a sparse coarse lattice
    glow as vein cores."""
    yy, xx = coords(res)
    colph = h2(np.floor(xx / float(p)), 0.0, salt + 1) * 6.2831853
    xq = (xx + np.sin(yy / float(wl) * 6.2831853 + colph) * float(sway)) / float(p)
    col = np.floor(xq)
    seg = np.floor(yy / float(dl))
    present = (h2(col, seg, salt + 3) > np.where((col + seg) % 2.0 < 1.0, 0.30, 0.60)).astype(np.float32)
    thread = _fat(np.abs(frac(xq) - 0.5), 0.24) * present
    _fb, eb, hb, _pb = _voro(res, bed, 0.52, salt + 5)
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    idx = np.clip(ridx + np.round(3.0 * sstep(0.30, 0.75, thread)) - 1.0, 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    v = v + (0.5 + 0.5 * np.cos(np.clip(_fb, 0.0, 1.0) * 3.14159) - 0.5) \
        * 2.0 * float(relief) * (1.0 - thread)
    bseam = np.clip(_fat(eb, 0.11) * (1.0 - thread) + pc, 0.0, 1.0)
    v = _pitmix(v, bseam, float(pit) * (0.7 + 0.5 * hb))
    dv, hvv, _pv = _dots(res, ventc, 0.55, salt + 9)
    isv = (hvv > float(vgate)).astype(np.float32)
    mouth = np.exp(-((dv / 0.16) ** 2)) * isv
    vein = np.clip(mouth * 1.6 + thread
                   * (h2(col, seg, salt + 11) > 0.90).astype(np.float32) * 0.9,
                   0.0, 1.0)
    fam = 1.0 - np.clip(thread + mouth, 0.0, 1.0)  # 0 = ember, 1 = blue bed
    return np.clip(v, 0.0, 1.0), fam, np.where(thread > 0.5, h2(col, seg, salt + 13), rhv), vein


def e_swirl_sectors(res, seed, salt=0, cell=8.4, S=4, twist=1.6, lo=_LAD_LO,
                    hi=_LAD_HI, pit=0.024, relief=0.012, vgate=0.45, pitc=0.02):
    """[fof_petrol_swirl] SPIRAL-SECTOR ROSETTES: every cell splits into
    twisted pinwheel sectors (stained-glass swirl), each sector its own family
    (gold / violet / teal) and rung bias, dark grout between cells and along
    sector seams; hot cells flash one sector edge."""
    rl, th, hv, _par = _polar_cells(res, cell, 0.42, salt + 1, 1.0)
    cid = np.floor(hv * 997.0)
    tw = th + rl * float(twist) * np.where(h2(cid, 3.0, salt + 3) > 0.5, 1.0, -1.0)
    sang = (tw / 6.2831853 + 0.5) * float(S)
    sect = np.floor(sang)
    fam = ((sect + np.floor(h2(cid, 7.0, salt + 5) * 3.0)) % 3.0).astype(np.float32)
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    # sector bias {0,+1} only: a +-1 tri-state at coarse sector scale kept
    # ~35% of total power sub-band; hue families carry sector identity
    idx = np.clip(ridx + (h2(sect * 17.0 + cid, 0.0, salt + 7) > 0.55)
                  .astype(np.float32), 0.0, 7.0)
    # heavy pre-pit soften: cell 8.4 measured band 0.798 / ac 0.504 — spend
    # the band surplus on lag-1 coherence (pits stay crisp; snap re-grids)
    v = _lval(idx, 8, lo, hi)
    # NO spoke pits: the twisted spokes are radius-tapering HAIRLINES
    # (~0.35 px mid-length — measured ac stuck at 0.475 with them, like the
    # closed rl rings before them). The pinwheel reads through the per-sector
    # RUNG STEPS and the per-sector hue boundaries — pure crush-law value
    # quantization. Grout = straight polygon seams on the SAME lattice
    # (salt+1, jit 0.42 match _polar_cells).
    _f2p, e2p, _h2p, _p2p = _voro(res, cell, 0.42, salt + 1)
    edge = _fat(e2p, 0.24)
    v = _pitmix(v, np.clip(edge + pc, 0.0, 1.0),
                float(pit) * (0.7 + 0.5 * h2(cid, 1.0, salt + 9)))
    hot = (h2(cid, 9.0, salt + 11) > float(vgate)).astype(np.float32)
    # compact CORE glints, not spoke lines: hot spoke hairlines measured
    # ac 0.492 -> 0.585 without them (ablation 2026-08-03); a bright curved
    # hairline is the single worst lag-1 offender in this archetype
    vein = np.clip(np.exp(-((rl / 0.26) ** 2)) * hot * 1.6, 0.0, 1.0)
    return np.clip(v, 0.0, 1.0), fam, rhv, vein


def e_roundels(res, seed, salt=0, cell=6.8, rw=0.32, lo=_LAD_LO, hi=_LAD_HI,
               pit=0.026, relief=0.011, vgate=0.60, pitc=0.03):
    """[fof_regalia_roundels] NESTED ROUNDEL RINGS: every cell a heraldic
    roundel of 2-3 concentric rings, FAMILY per ring index (crimson / gold /
    sapphire), ring grooves etched deep, rung-terraced field between
    roundels; hot roundels light their bullseye."""
    rl, _th, hv, _par = _polar_cells(res, cell, 0.40, salt + 1, 0.0)
    cid = np.floor(hv * 997.0)
    ring = np.floor(rl / float(rw))
    inr = (ring < 3.0).astype(np.float32)
    fam = ((ring + np.floor(h2(cid, 5.0, salt + 3) * 3.0)) % 3.0).astype(np.float32)
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    idx = np.clip(ridx + _b3(h2(cid + ring * 31.0, 0.0, salt + 5)), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    rp = frac(rl / float(rw))
    v = v + ((0.5 + 0.5 * np.cos((rp - 0.5) * 6.2831853)) - 0.5) \
        * 2.0 * float(relief) * inr
    groove = np.clip(_fat(np.abs(rp - 0.5), 0.12) * inr + pc, 0.0, 1.0)
    v = _pitmix(v, groove, float(pit) * (0.7 + 0.5 * h2(cid, 2.0, salt + 7)))
    hot = (h2(cid, 9.0, salt + 9) > float(vgate)).astype(np.float32)
    vein = np.clip(np.exp(-((rl / 0.20) ** 2)) * hot * 1.7, 0.0, 1.0)
    return np.clip(v, 0.0, 1.0), fam, rhv, vein


def e_guilloche(res, seed, salt=0, cell=20.0, p=7.2, lo=_LAD_LO, hi=_LAD_HI,
                pit=0.026, relief=0.014, vgate=0.86, pitc=0.015):
    """[fof_patina_guilloche] ENGINE-TURNED ARC COMBS: two half-cell-offset
    lattices of concentric ring combs overlapping like engine-turned
    rosettes; crests carry the bronze family (+1 rung), recesses hold teal
    patina (-2), deep grooves where rosettes collide; sparse arcs glint."""
    crest = None
    ridw = None
    for kk, (soff, xoff) in enumerate(((0, 0.0), (37, 0.5))):
        n, c = _celln(res, cell)
        yy, xx = coords(res)
        xs = xx + xoff * c
        ci = np.floor(xs / c)
        cj = np.floor(yy / c)
        jx = (_up(_cg(n, salt + 1 + soff), res) - 0.5) * 0.30 * c
        jy = (_up(_cg(n, salt + 12 + soff), res) - 0.5) * 0.30 * c
        dd = np.hypot(xs - (ci + 0.5) * c - jx, yy - (cj + 0.5) * c - jy)
        ph = dd / float(p)
        comb = _fat(np.abs(frac(ph) - 0.5), 0.34) * sstep(1.9, 0.6, dd / c)
        hvk = h2(ci + np.floor(ph) * 13.0, cj, salt + 23 + soff)
        if crest is None:
            crest = comb
            ridw = hvk
        else:
            m = comb > crest
            crest = np.where(m, comb, crest)
            ridw = np.where(m, hvk, ridw)
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    w = sstep(0.35, 0.85, crest)
    idx = np.clip(ridx + np.round(3.0 * w) - 2.0, 0.0, 7.0)
    v = _lval(idx, 8, lo, hi) + (crest - 0.5) * float(relief)
    deep = np.clip((1.0 - crest * 2.6) * sstep(0.35, 0.05, crest) + pc,
                   0.0, 1.0)
    v = _pitmix(v, deep, float(pit) * (0.8 + 0.4 * ridw))
    hot = (ridw > float(vgate)).astype(np.float32)
    vein = np.clip(crest * hot * sstep(0.7, 0.98, crest) * 1.5, 0.0, 1.0)
    fam = (w < 0.5).astype(np.float32)  # 0 = bronze crest, 1 = teal recess
    return np.clip(v, 0.0, 1.0), fam, rhv, vein


def e_drips(res, seed, salt=0, p=6.8, wl=34.0, sway=1.6, bl=7.4, lo=_LAD_LO,
            hi=_LAD_HI, duty=0.46, pit=0.026, relief=0.014, vgate=0.80,
            pitc=0.02):
    """[fof_toxic_drips] BEADED RUNNEL DRIPS: vertical wavy runnels carrying
    drip beads at intervals, FAMILY alternates per runnel (magenta / acid),
    per-bead rung bias, inter-runnel gaps etched deep; sparse bead tips glow."""
    yy, xx = coords(res)
    colph = h2(np.floor(xx / float(p)), 0.0, salt + 1) * 6.2831853
    xq = (xx + np.sin(yy / float(wl) * 6.2831853 + colph) * float(sway)) / float(p)
    col = np.floor(xq)
    bead = np.floor(yy / float(bl) + h2(col, 0.0, salt + 3))
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    idx = np.clip(ridx + _b3(h2(col, bead, salt + 5)), 0.0, 7.0)
    run = _fat(np.abs(frac(xq) - 0.5), duty)
    bulge = np.exp(-((frac(yy / float(bl) + h2(col, 0.0, salt + 3)) - 0.5) ** 2)
                   / 0.045) * (h2(col, bead, salt + 7) > 0.35).astype(np.float32)
    gloss = 0.5 + 0.5 * np.cos(6.2831853 * frac(xq))
    v = _lval(idx, 8, lo, hi) + (gloss - 0.5) * 2.0 * float(relief) \
        + bulge * run * 0.03
    gap = np.clip(1.0 - run * 1.35 + pc, 0.0, 1.0)
    v = _pitmix(v, gap, float(pit) * (0.7 + 0.5 * h2(col, bead, salt + 9)))
    hot = (h2(col, bead, salt + 11) > float(vgate)).astype(np.float32)
    vein = np.clip(run * bulge * hot * 1.9, 0.0, 1.0)
    fam = (col % 2.0).astype(np.float32)  # magenta / acid by runnel
    return np.clip(v, 0.0, 1.0), fam, rhv, vein


def e_gemfacets(res, seed, salt=0, cell=8.4, F=6, lo=_LAD_LO, hi=_LAD_HI,
                gw=0.10, pit=0.026, ramp=0.013, vgate=0.90, pitc=0.015):
    """[fof_treasure_facets] FACET-FAN GEMS: every cell a brilliant-cut stone
    — an angular fan of F facets around a flat table (+2 rung), each facet
    rung-biased with a small ramp, FAMILY per cell (sapphire / amber /
    emerald), grout pits between stones; sparse whole facets flash pale."""
    rl, th, hv, _par = _polar_cells(res, cell, 0.30, salt + 1, 1.0)
    cid = np.floor(hv * 997.0)
    fam = np.floor(h2(cid, 5.0, salt + 3) * 3.0).astype(np.float32)
    sang = (th / 6.2831853 + 0.5) * float(F)
    sect = np.floor(sang)
    hvf = h2(cid + sect * 29.0, 0.0, salt + 5)
    table = sstep(0.34, 0.22, rl)
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    idx = np.clip(ridx + _b3(hvf) + np.round(2.0 * table), 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    v = v + (frac(sang) - 0.5) * 2.0 * float(ramp) * np.sign(hvf - 0.5) \
        * (1.0 - table)
    _f1, e1, _h1, _p1 = _voro(res, cell, 0.30, salt + 1)
    grout = np.clip(_fat(e1, gw) + pc, 0.0, 1.0)
    v = _pitmix(v, grout, float(pit) * (0.7 + 0.5 * h2(cid, 1.0, salt + 9)))
    flash = (hvf > float(vgate)).astype(np.float32) * sstep(0.30, 0.42, rl) \
        * sstep(1.05, 0.85, rl)
    vein = np.clip(flash * 0.92, 0.0, 1.0)
    return np.clip(v, 0.0, 1.0), fam, rhv, vein


def e_spirals(res, seed, salt=0, cell=6.0, twist=2.6, clus=24.0, lo=_LAD_LO,
              hi=_LAD_HI, pit=0.026, relief=0.012, vgate=0.50, pitc=0.045):
    """[fof_nebula_swirls] TWIN-ARM SPIRAL CELLS: every cell a tiny two-arm
    spiral galaxy (log-spiral arms, hash-signed twist, +1 rung on arms, -1
    between), FAMILY assigned per coarse CLUSTER (violet / crimson / ice
    regions follow the geometry), cell rims etched; hot cores glow."""
    rl, th, hv, _par = _polar_cells(res, cell, 0.44, salt + 1, 1.0)
    cid = np.floor(hv * 997.0)
    sgn = np.where(h2(cid, 3.0, salt + 3) > 0.5, 1.0, -1.0)
    ph = th / 3.14159 + rl * float(twist) * sgn
    arm = _fat(np.abs(frac(ph) - 0.5), 0.30) * sstep(1.30, 0.30, rl)
    ridx, rhv, pc, _vc = _rungs(res, salt, 4.2, pitc, 0.0)
    idx = np.clip(ridx + np.round(2.0 * sstep(0.30, 0.75, arm)) - 1.0, 0.0, 7.0)
    v = _lval(idx, 8, lo, hi)
    v = v + (0.5 + 0.5 * np.cos(np.clip(rl, 0.0, 1.2) * 3.14159) - 0.5) \
        * 2.0 * float(relief)
    _fc, ec, hc, _pc2 = _voro(res, clus, 0.50, salt + 7)
    fam = np.floor(hc * 3.0).astype(np.float32)
    rim = np.clip(sstep(1.10, 1.35, rl) + pc, 0.0, 1.0)
    v = _pitmix(v, rim, float(pit) * (0.7 + 0.5 * h2(cid, 1.0, salt + 9)))
    hot = (h2(cid, 9.0, salt + 11) > float(vgate)).astype(np.float32)
    vein = np.clip(np.exp(-((rl / 0.30) ** 2)) * hot * 1.6, 0.0, 1.0)
    return np.clip(v, 0.0, 1.0), fam, rhv, vein


ENGINES = {
    "e_founder_web": e_founder_web, "e_brick_pave": e_brick_pave,
    "e_rope_coils": e_rope_coils, "e_columns": e_columns,
    "e_shatter": e_shatter, "e_drainage": e_drainage, "e_braid": e_braid,
    "e_burstfoam": e_burstfoam, "e_anticline": e_anticline,
    "e_shardglass": e_shardglass, "e_hammer": e_hammer, "e_keels": e_keels,
    "e_circuit": e_circuit, "e_mudcrack": e_mudcrack,
    "e_ember_reef": e_ember_reef, "e_terrace_strips": e_terrace_strips,
    "e_kagome": e_kagome, "e_pennies": e_pennies, "e_vents": e_vents,
    "e_swirl_sectors": e_swirl_sectors, "e_roundels": e_roundels,
    "e_guilloche": e_guilloche, "e_drips": e_drips,
    "e_gemfacets": e_gemfacets, "e_spirals": e_spirals,
}




# ════════════════════════════════════════════════════════════════════════════
# RECIPES — 25 finishes, ids fof_*, seeds 1300-1324, GROUPS key exactly
# "FRACTURED OPALFIRE". val=0.36 everywhere -> paint crush factor is exactly
# 0.85 (art peaks at 1.0 in the vein cores), so every authored art-luma rung
# lands deterministically at rung*0.85 in the shipped paint.
# Hue anchor doctrine: direct-HSV composition renders the anchor EXACTLY
# (measured in verify_opalfire; no LUT asymmetry, no damped-gain loop needed).
# ════════════════════════════════════════════════════════════════════════════

def _r(fid, name, engine, seed, families, veinh, desc, veinsat=0.5,
       hdrift=0.0, jitamp=0.022, **eargs):
    ea = dict(salt=_crc(fid))
    ea.update(eargs)
    return (fid, dict(name=name, engine=engine, eargs=ea, seed=seed, val=0.36,
                      families=families, veinh=veinh, veinsat=veinsat,
                      hdrift=hdrift, jitamp=jitamp, desc=desc))


OPALFIRE = dict([
    # ── THE FOUNDER — the owner's discovery, baked ──────────────────────────
    _r("fof_molten_core", "Molten Core", "e_founder_web", 1300,
       [(0.092, 0.88)], [0.118], veinsat=0.52, hdrift=0.10,
       desc="THE FOUNDER — the crush discovery baked: a gold crack-web at 4x lava "
            "frequency over an 8-rung amber/brown ladder pave, under the uniform "
            "night-carrier spec. Every dark rung flips at its own angle. "
            "A FRACTURED OPALFIRE finish."),
    # ── TWELVE SINGLE-HUE SHADE LADDERS ─────────────────────────────────────
    _r("fof_gilded_pave", "Gilded Pave", "e_brick_pave", 1301,
       [(0.118, 0.86)], [0.125], veinsat=0.50, hdrift=0.07,
       desc="Gold cobble bricks, every one a different dark rung, molten mortar "
            "threading the sparse joints. A FRACTURED OPALFIRE finish."),
    _r("fof_copper_pahoehoe", "Copper Pahoehoe", "e_rope_coils", 1302,
       [(0.052, 0.85)], [0.075], veinsat=0.48, hdrift=0.06,
       desc="Buckled copper rope coils, dash-laddered dark on dark, incandescent "
            "skin breaking through the grooves. A FRACTURED OPALFIRE finish."),
    _r("fof_crimson_columns", "Crimson Columns", "e_columns", 1303,
       [(0.982, 0.86)], [0.030], veinsat=0.46, hdrift=0.04,
       desc="Columnar crimson joints — every column top its own dark rung, rims "
            "cracked black, molten cores in the hottest. A FRACTURED OPALFIRE finish."),
    _r("fof_sapphire_shatter", "Sapphire Shatter", "e_shatter", 1304,
       [(0.618, 0.82)], [0.598], veinsat=0.30, hdrift=-0.03,
       desc="Sapphire pane diced by two cut families into laddered shards, point "
            "glints at the crossings. A FRACTURED OPALFIRE finish."),
    _r("fof_teal_drainage", "Teal Drainage", "e_drainage", 1305,
       [(0.472, 0.80)], [0.462], veinsat=0.32, hdrift=-0.03,
       desc="Teal interfluve pads terraced rung by rung between deep drainage "
            "channels, rare ponds glinting. A FRACTURED OPALFIRE finish."),
    _r("fof_emerald_braid", "Emerald Braid", "e_braid", 1306,
       [(0.355, 0.82)], [0.330], veinsat=0.34, hdrift=-0.02,
       desc="Emerald cords weaving over-under in laddered dashes, crossings "
            "sparking. A FRACTURED OPALFIRE finish."),
    _r("fof_violet_burstfoam", "Violet Burstfoam", "e_burstfoam", 1307,
       [(0.752, 0.80)], [0.760], veinsat=0.28, hdrift=-0.02,
       desc="Burst violet bubbles — crater pits, crescent rims, terraced ground, "
            "hot crescents flashing. A FRACTURED OPALFIRE finish."),
    _r("fof_magenta_anticline", "Magenta Anticline", "e_anticline", 1308,
       [(0.888, 0.82)], [0.905], veinsat=0.34, hdrift=0.02,
       desc="Folded magenta ridge trains, every flank a staircase of dark rungs, "
            "crests burning on hot segments. A FRACTURED OPALFIRE finish."),
    _r("fof_amber_shardglass", "Amber Shardglass", "e_shardglass", 1309,
       [(0.096, 0.88)], [0.115], veinsat=0.50, hdrift=0.07,
       desc="Elongated amber glass facets, each ramped and rung-laddered, edge "
            "flashes firing between. A FRACTURED OPALFIRE finish."),
    _r("fof_argent_hammer", "Argent Hammer", "e_hammer", 1310,
       [(0.565, 0.20)], [0.565], veinsat=0.12, hdrift=0.0,
       desc="Hammered argent — dent on dent in pewter rungs, strike rims "
            "glinting cold. A FRACTURED OPALFIRE finish."),
    _r("fof_bronze_keels", "Bronze Keels", "e_keels", 1311,
       [(0.072, 0.78)], [0.095], veinsat=0.46, hdrift=0.06,
       desc="Keeled bronze scales, faces sloping dark rung to rung, hot keels "
            "running molten. A FRACTURED OPALFIRE finish."),
    _r("fof_acid_circuit", "Acid Circuit", "e_circuit", 1312,
       [(0.238, 0.85)], [0.215], veinsat=0.38, hdrift=-0.02,
       desc="Acid-etched circuit maze — rectilinear traces over laddered "
            "substrate, solder nodes glowing. A FRACTURED OPALFIRE finish."),
    # ── TWELVE MULTI-HUE LADDER FIELDS (families follow the geometry) ───────
    _r("fof_gilded_abyss", "Gilded Abyss", "e_mudcrack", 1313,
       [(0.118, 0.86), (0.618, 0.82)], [0.118, 0.598], veinsat=0.50, hdrift=0.03,
       desc="Gold and sapphire plates interleaved across a dark mudcrack net, "
            "molten threads in the crack cores. A FRACTURED OPALFIRE finish."),
    _r("fof_ember_reef", "Ember Reef", "e_ember_reef", 1314,
       [(0.985, 0.87), (0.472, 0.78)], [0.060, 0.462], veinsat=0.50, hdrift=0.03,
       desc="Crimson coal domes glowing in a terraced teal reef, the hottest "
            "cores white-gold. A FRACTURED OPALFIRE finish."),
    _r("fof_royal_terraces", "Royal Terraces", "e_terrace_strips", 1315,
       [(0.752, 0.80), (0.096, 0.88)], [0.760, 0.115], veinsat=0.42, hdrift=0.02,
       desc="Violet and amber fault strips, each a staircase of dark rungs with "
            "lit risers. A FRACTURED OPALFIRE finish."),
    _r("fof_orchid_kagome", "Orchid Kagome", "e_kagome", 1316,
       [(0.355, 0.82), (0.888, 0.82), (0.802, 0.78)], [0.330, 0.905, 0.795],
       veinsat=0.34, hdrift=0.0,
       desc="A triaxial kagome of emerald, magenta and orchid cords, triangular "
            "wells running black. A FRACTURED OPALFIRE finish."),
    _r("fof_frosted_pennies", "Frosted Pennies", "e_pennies", 1317,
       [(0.052, 0.85), (0.552, 0.24)], [0.075, 0.552], veinsat=0.48, hdrift=0.04,
       desc="Milled copper pennies dropped on icy terraced ground, edge glints "
            "arcing. A FRACTURED OPALFIRE finish."),
    _r("fof_abyssal_vents", "Abyssal Vents", "e_vents", 1318,
       [(0.032, 0.88), (0.630, 0.82)], [0.045, 0.610], veinsat=0.50, hdrift=0.0,
       desc="Ember plumes rising in beads off abyssal vents through a deep-blue "
            "laddered bed. A FRACTURED OPALFIRE finish."),
    _r("fof_petrol_swirl", "Petrol Swirl", "e_swirl_sectors", 1319,
       [(0.118, 0.84), (0.752, 0.80), (0.472, 0.80)], [0.125, 0.760, 0.462],
       veinsat=0.40, hdrift=0.0,
       desc="Petrol rosettes — gold, violet and teal sectors twisting in every "
            "cell, grout black between. A FRACTURED OPALFIRE finish."),
    _r("fof_regalia_roundels", "Regalia Roundels", "e_roundels", 1320,
       [(0.982, 0.86), (0.118, 0.86), (0.618, 0.82)], [0.030, 0.125, 0.598],
       veinsat=0.44, hdrift=0.0,
       desc="Nested heraldic roundels — crimson, gold and sapphire rings rung "
            "for rung, bullseyes lighting. A FRACTURED OPALFIRE finish."),
    _r("fof_patina_guilloche", "Patina Guilloche", "e_guilloche", 1321,
       [(0.072, 0.80), (0.472, 0.76)], [0.095, 0.462], veinsat=0.44, hdrift=0.02,
       desc="Engine-turned bronze arc combs over teal patina recesses, sparse "
            "arcs glinting. A FRACTURED OPALFIRE finish."),
    _r("fof_toxic_drips", "Toxic Drips", "e_drips", 1322,
       [(0.888, 0.84), (0.238, 0.85)], [0.905, 0.215], veinsat=0.38, hdrift=0.0,
       desc="Magenta and acid runnels dripping in laddered beads, tips glowing. "
            "A FRACTURED OPALFIRE finish."),
    _r("fof_treasure_facets", "Treasure Facets", "e_gemfacets", 1323,
       [(0.618, 0.82), (0.096, 0.88), (0.355, 0.82)], [0.598, 0.115, 0.330],
       veinsat=0.34, hdrift=0.0,
       desc="A pave of brilliant-cut stones — sapphire, amber and emerald facet "
            "fans, sparse facets flashing pale. A FRACTURED OPALFIRE finish."),
    _r("fof_nebula_swirls", "Nebula Swirls", "e_spirals", 1324,
       [(0.752, 0.80), (0.982, 0.86), (0.552, 0.24)], [0.760, 0.030, 0.552],
       veinsat=0.34, hdrift=0.0,
       desc="Twin-arm micro spirals clustered violet, crimson and ice, hot cores "
            "burning through. A FRACTURED OPALFIRE finish."),
])

GROUPS = {"FRACTURED OPALFIRE": OPALFIRE}

KIT = OpalfireKit(engines=ENGINES, groups=GROUPS, tag="fractured-opalfire")

ALL = KIT.ALL
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
