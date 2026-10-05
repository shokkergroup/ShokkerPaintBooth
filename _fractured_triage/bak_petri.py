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


def _grain(xx, yy, cell, salt, thr=0.62):
    g = h2(np.floor(xx / float(cell)), np.floor(yy / float(cell)), salt)
    return sstep(thr, min(thr + 0.18, 0.999), g)


def _fine(res, seed, k=0.13):
    r1 = fbm(res, res, rng(seed, 811), 2, 180)
    ridge = (1.0 - np.abs(2.0 * r1 - 1.0)) ** 2
    n2 = fbm(res, res, rng(seed, 823), 1, 320)
    return (ridge * 0.6 + n2 * 0.4).astype(np.float32) * float(k)


def _cells(res, pitch, salt, jit=0.85, taps=9, need2=True):
    """Jittered-grid nearest-feature field -> (dx, dy, d1, id1, d2). Coarse
    cell-grid hashes gathered per tap (perf); taps=5 / need2=False for pure
    dot layers. See fractured_bloom_2026 for the pass-2 rationale."""
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


# ════════════════════════════════════════════════════════════════════════════
# STRUCTURAL GENERATORS — 20 distinct culture-field archetypes.
# [SPB-FRACTURED-FIELD 2026-08-02]
# ════════════════════════════════════════════════════════════════════════════

def g_droplets(res, seed, pitch=11.0, fine=0.12):
    """domed droplet close-pack: glossy colony domes, offset specular caps,
    contact shadows where droplets kiss."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, d2 = _cells(res, p, sd, 0.8)
    rr = d1 / (p * 0.72)
    dome = np.clip(1.0 - rr * rr, 0.0, 1.0)
    capd = np.hypot(dx + p * 0.16, dy + p * 0.16)
    cap = _bump((capd / (1.6 * s)) ** 2) * 0.45
    contact = sstep(2.4 * s, 0.5 * s, d2 - d1) * 0.32
    ringr = sstep(0.10, 0.03, np.abs(rr - 0.80)) * 0.18
    T = _tier(id1) * 0.44 + dome * 0.42 + cap + ringr - contact
    return n01(T + _fine(res, seed, fine))


def g_satellite(res, seed, pitch=14.0, sats=7.0, fine=0.12):
    """satellite dot scatter: mother colonies ringed by satellite daughters,
    a finer dust ply between."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.8, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.70)
    mother = _bump((rr * 2.2) ** 2)
    ring = sstep(0.14, 0.05, np.abs(rr - 0.58))
    satm = ring * (0.5 + 0.5 * np.cos(th * sats + id1 * _TAU)) ** 3.0
    _, _, db, idb, _b = _cells(res, 4.6 * s, sd + 77, 0.95, taps=5, need2=False)
    dust = _bump((db / (1.2 * s)) ** 2) * (0.20 + _tier(idb) * 0.30)
    T = 0.20 + mother * (0.34 + _tier(id1) * 0.42) + satm * 0.42 + dust
    return n01(T + _fine(res, seed, fine))


def g_streaks(res, seed, lane=13.0, dotp=6.0, fine=0.12):
    """streak-plate lanes: sinuous inoculation streaks with colony dots
    growing along them, agar granulation between."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 31, 14.0)
    q = (yy + wu * 2.0 + np.sin(xx / (52.0 * s)) * 9.0 * s) / (lane * s)
    li = np.floor(q)
    v = frac(q)
    lanem = (1.0 - np.abs(2.0 * v - 1.0)) ** 2.5
    X2 = xx + h2(li, li * 0.0, sd + 21) * 43.0
    ci = np.floor(X2 / (dotp * s))
    u = frac(X2 / (dotp * s))
    dot = _bump((((u - 0.5) * dotp) ** 2 + ((v - 0.5) * lane * 0.6) ** 2)
                / (2.1 ** 2)) * sstep(0.35, 0.6, h2(ci, li, sd + 33))
    tier = _tier(h2(ci, li, sd + 5))
    T = (0.24 + lanem * 0.30 + dot * (0.34 + tier * 0.44)
         + _grain(xx, yy, 2.6 * s, sd + 13) * 0.16)
    return n01(T + _fine(res, seed, fine))


def g_crackle(res, seed, pitch=13.0, fine=0.12):
    """crackle-net: dried-agar crack web at two scales over domed shards."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, d2 = _cells(res, p, sd, 1.0)
    crack = sstep(2.2 * s, 0.5 * s, d2 - d1)
    rr = d1 / (p * 0.75)
    shard = np.clip(1.0 - rr * rr * 0.8, 0.0, 1.0)
    _dx2, _dy2, d1b, _idb, d2b = _cells(res, 6.0 * s, sd + 41, 1.0)
    crack2 = sstep(1.3 * s, 0.3 * s, d2b - d1b)
    T = (_tier(id1) * 0.44 + shard * 0.30 - crack * 0.52 - crack2 * 0.22
         + _grain(dx, dy, 2.2 * s, sd + 9) * 0.14)
    return n01(T + _fine(res, seed, fine))


def g_dendrite(res, seed, pitch=15.0, arms=5.0, fine=0.12):
    """dendrite fans: tiled radial branching fern colonies — jagged primary
    rays with finer side rays toward the tips."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.6, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.72)
    jag = fbm(res, res, rng(seed, 71), 2, 160)
    ray = (0.5 + 0.5 * np.cos(th * arms + id1 * _TAU + (jag - 0.5) * 3.0)) ** 2.6
    sub = (0.5 + 0.5 * np.cos(th * arms * 3.0 + id1 * 9.0)) ** 2.0
    fan = (ray * 0.75 + sub * 0.45 * sstep(0.35, 0.6, rr)) * np.clip(
        1.05 - rr, 0.0, 1.0)
    core = _bump((rr * 3.5) ** 2) * 0.4
    T = 0.22 + _tier(id1) * 0.34 + fan * 0.55 + core
    return n01(T + _fine(res, seed, fine))


def g_pills(res, seed, bw=17.0, rh=8.0, striae=6.5, fine=0.11):
    """brick-course ribbed pills: offset rows of rounded diatom tiles with
    transverse striae and a girdle line."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 81, 5.0)
    v = (yy + wv) / (rh * s)
    rj = np.floor(v)
    u = (xx + wu) / (bw * s) + h2(rj, rj * 0.0, sd + 3) * 7.0
    ci = np.floor(u)
    du = (u - ci - 0.5) * bw * s
    dv = (v - rj - 0.5) * rh * s
    dd = np.maximum(np.abs(du) - bw * s * 0.34, 0.0) ** 2 + dv * dv
    body = sstep((rh * s * 0.46) ** 2, (rh * s * 0.30) ** 2, dd)
    stri = (0.5 + 0.5 * np.cos(du / (striae * s * 0.16))) * body * 0.22
    girdle = sstep(0.9 * s, 0.2 * s, np.abs(dv)) * body * 0.24
    tier = _tier(h2(ci, rj, sd + 7))
    T = 0.22 + body * (0.30 + tier * 0.44) + stri + girdle
    return n01(T + _fine(res, seed, fine))


def g_raphe(res, seed, pitch=14.0, ln=9.0, fine=0.12):
    """raphe needle felt: striated pennate needles with a dark centre raphe,
    plus a loose spore-dot underlay."""
    s = res / _S
    sd = _sd(seed)
    dx, dy, d1, id1, _ = _cells(res, pitch * s, sd, 0.85, taps=5, need2=False)
    a = id1 * _TAU
    ca, sa = np.cos(a), np.sin(a)
    along = dx * ca + dy * sa
    across = np.abs(-dx * sa + dy * ca)
    L = ln * s * (0.7 + 0.7 * h2(id1 * 31.0, id1 * 17.0, sd + 3))
    body = sstep(1.8 * s, 0.5 * s, across) * sstep(L, L * 0.80, np.abs(along))
    tapern = 1.0 - np.clip(np.abs(along) / np.maximum(L, 1e-4), 0.0, 1.0)
    raphe = sstep(0.5 * s, 0.1 * s, across) * body * 0.35
    ticks = (0.5 + 0.5 * np.cos(along / (1.1 * s))) * body * 0.25
    _, _, db, idb, _b = _cells(res, 5.0 * s, sd + 99, 0.95, taps=5, need2=False)
    dots = _bump((db / (1.3 * s)) ** 2) * (0.18 + _tier(idb) * 0.26)
    T = (0.22 + body * (0.26 + _tier(id1) * 0.40) * (0.6 + 0.4 * tapern)
         + ticks - raphe + dots)
    return n01(T + _fine(res, seed, fine))


def g_discs(res, seed, pitch=12.0, ribs=11.0, fine=0.12):
    """radial-ribbed disc lattice: centric diatom valves — rib fan, margin
    ring, dark central pore."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.35, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.66)
    body = sstep(1.0, 0.88, rr)
    fan = (0.5 + 0.5 * np.cos(th * ribs + id1 * _TAU)) * body
    fan = fan * sstep(0.10, 0.30, rr)
    margin = sstep(0.10, 0.03, np.abs(rr - 0.80)) * 0.30
    pore = _bump((d1 / (1.6 * s)) ** 2) * 0.38
    T = 0.22 + body * (0.24 + _tier(id1) * 0.38) + fan * 0.30 + margin - pore
    return n01(T + _fine(res, seed, fine))


def g_hexmesh(res, seed, pitch=8.0, fine=0.11):
    """perforated hex mesh: near-regular silica hole lattice — dark pores,
    bright walls, secondary micro-pores pitting the walls."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    p = pitch * s
    _dx, _dy, d1, id1, d2 = _cells(res, p, sd, 0.22)
    hole = sstep(p * 0.40, p * 0.16, d1)
    wall = sstep(1.3 * s, 0.25 * s, d2 - d1)
    rimlight = sstep(1.4 * s, 0.3 * s, np.abs(d1 - p * 0.40)) * 0.42
    _, _, db, _idb, _b = _cells(res, 3.4 * s, sd + 61, 0.9, taps=5, need2=False)
    micro = _bump((db / (0.9 * s)) ** 2) * 0.25
    patch = _tier(h2(np.floor(xx / (26.0 * s)), np.floor(yy / (26.0 * s)),
                     sd + 5))
    T = (0.28 + patch * 0.20 + _tier(id1) * 0.26 - hole * 0.66
         + wall * 0.34 + rimlight - micro)
    return n01(T + _fine(res, seed, fine))


def g_spineball(res, seed, pitch=13.0, spines=11.0, fine=0.12):
    """spine-burst scatter: small urchin spike balls with bright cores and
    long thin rays, dust underlay."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.75, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.75)
    spike = (0.5 + 0.5 * np.cos(th * spines + id1 * _TAU)) ** 7.0
    spike = spike * sstep(0.95, 0.25, rr)
    ball = _bump((rr * 3.6) ** 2) * 0.55
    _, _, db, idb, _b = _cells(res, 4.4 * s, sd + 88, 0.95, taps=5, need2=False)
    dust = _bump((db / (1.1 * s)) ** 2) * (0.16 + _tier(idb) * 0.24)
    T = 0.20 + _tier(id1) * 0.30 + spike * 0.60 + ball + dust
    return n01(T + _fine(res, seed, fine))


def g_memfoam(res, seed, pitch=11.0, fine=0.11):
    """foam pack with nuclei: bright membrane walls, cytoplasm stipple, an
    offset nucleus (+nucleolus) in every cell."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, d2 = _cells(res, p, sd, 0.9)
    wall = sstep(2.8 * s, 0.8 * s, d2 - d1)
    rr = d1 / (p * 0.75)
    cyto = np.clip(1.0 - rr * 0.7, 0.0, 1.0)
    nx = (h2(id1 * 61.0, id1 * 23.0, sd + 5) - 0.5) * p * 0.34
    ny = (h2(id1 * 47.0, id1 * 91.0, sd + 6) - 0.5) * p * 0.34
    nd = np.hypot(dx - nx, dy - ny)
    nuc = _bump((nd / (2.2 * s)) ** 2) * 0.45
    nucleol = _bump((nd / (0.9 * s)) ** 2) * 0.30
    stip = _grain(dx + 17.0, dy + 41.0, 1.9 * s, sd + 15) * cyto * 0.18
    T = _tier(id1) * 0.40 + cyto * 0.26 + wall * 0.38 - nuc + nucleol + stip
    return n01(T + _fine(res, seed, fine))


def g_stainplates(res, seed, pitch=12.0, fine=0.11):
    """stained plate-mosaic: flat polygonal tissue plates, dark grout, and a
    per-plate chromatin stipple density."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, d2 = _cells(res, p, sd, 0.6)
    grout = sstep(2.2 * s, 0.6 * s, d2 - d1)
    dens = sstep(0.25, 0.75, h2(id1 * 77.0, id1 * 13.0, sd + 4))
    stip = _grain(dx + 29.0, dy + 57.0, 2.1 * s, sd + 11)
    stip2 = _grain(dx + 3.0, dy + 9.0, 3.6 * s, sd + 12)
    T = (0.26 + _tier(id1) * 0.42 - grout * 0.55
         + (stip * 0.26 + stip2 * 0.18) * (0.35 + 0.65 * dens))
    return n01(T + _fine(res, seed, fine))


def g_ripples(res, seed, pitch=6.0, fine=0.12):
    """micro-ripple carpet: warped parallel cortical-fold ridges, amplitude
    breathing, a finer cross ply."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 91, 26.0)
    q = (yy + wu * 2.6) / (pitch * s)
    rip = (1.0 - np.abs(2.0 * frac(q) - 1.0)) ** 1.6
    tier = _tier(h2(np.floor(q), np.floor(q * 0.11), sd + 9))
    amp = 0.65 + 0.35 * fbm(res, res, rng(seed, 95), 2, 24)
    crossq = (xx + wv * 1.8) / (pitch * 2.1 * s)
    cross = (1.0 - np.abs(2.0 * frac(crossq) - 1.0)) ** 2.4
    T = 0.26 + rip * amp * 0.48 + tier * 0.24 + cross * 0.14
    return n01(T + _fine(res, seed, fine))


def g_sporedust(res, seed, fine=0.11):
    """clumped spore dust: dense bimodal spores gathered in clumps with a
    fuzz-ridge halo at every clump margin (voids stay small — car-band law)."""
    s = res / _S
    sd = _sd(seed)
    env = sstep(0.32, 0.72, fbm(res, res, rng(seed, 101), 3, 22))
    edge = 1.0 - np.abs(2.0 * env - 1.0)
    fuzz = edge * (1.0 - np.abs(2.0 * fbm(res, res, rng(seed, 107), 2, 220)
                                - 1.0)) ** 2 * 0.35
    _, _, da, ida, _a = _cells(res, 4.6 * s, sd, 0.95, taps=5, need2=False)
    _, _, db, idb, _b = _cells(res, 8.5 * s, sd + 55, 0.95, taps=5, need2=False)
    ga = _bump((da / (1.3 * s)) ** 2) * (0.4 + _tier(ida) * 0.6)
    gb = _bump((db / (2.3 * s)) ** 2) * (0.4 + _tier(idb) * 0.6)
    dust = np.maximum(ga * (0.42 + 0.58 * env), gb * (0.25 + 0.75 * env))
    T = 0.20 + dust * 0.72 + fuzz + env * 0.08
    return n01(T + _fine(res, seed, fine))


def g_ringspots(res, seed, pitch=14.0, rings=3.4, fine=0.12):
    """ring-pack spots: packed mold spots with fuzzy concentric zonation and
    a ragged sporing fringe."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.7, need2=False)
    rr = d1 / (p * 0.72)
    wob = (fbm(res, res, rng(seed, 121), 2, 180) - 0.5) * 0.16
    ring = 0.5 + 0.5 * np.cos((rr + wob) * rings * _TAU + id1 * 9.0)
    body = np.clip(1.08 - rr, 0.0, 1.0)
    th = np.arctan2(dy, dx)
    fringe = sstep(0.12, 0.04, np.abs(rr - 0.78 + wob))
    fringe = fringe * (0.5 + 0.5 * np.cos(th * 23.0 + id1 * _TAU)) ** 2
    T = _tier(id1) * 0.40 + body * (0.16 + 0.42 * ring * ring) + fringe * 0.30
    return n01(T + _fine(res, seed, fine))


def g_hyphae(res, seed, fine=0.11):
    """hyphal thread web: isotropic crest-line webs at two scales with
    conidia beads riding the threads."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)

    def crest(base, salt, w):
        f = fbm(res, res, rng(seed, salt), 2, base)
        r = 1.0 - np.abs(2.0 * f - 1.0)
        return sstep(1.0 - w, 1.0 - w * 0.3, r)

    web1 = crest(48, 131, 0.10)
    web2 = crest(110, 141, 0.10)
    _, _, bd, _bid, _b = _cells(res, 5.4 * s, sd + 61, 0.95, taps=5,
                                need2=False)
    beads = _bump((bd / (1.2 * s)) ** 2)
    conidia = beads * np.clip(web1 + web2, 0.0, 1.0)
    tier = _tier(h2(np.floor(xx / (20.0 * s)), np.floor(yy / (20.0 * s)),
                    sd + 2))
    T = (0.24 + tier * 0.16 + web1 * 0.42 + web2 * 0.34 + conidia * 0.45
         + beads * 0.12)
    return n01(T + _fine(res, seed, fine))


def g_beadchains(res, seed, pitch=12.0, bead=4.4, fine=0.12):
    """bead-chain drift: wandering diagonal cocci chains, touching beads on
    sinuous paths, loose singles between."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    ang = 0.7
    ca, sa = np.cos(ang), np.sin(ang)
    U = xx * ca + yy * sa
    V = -xx * sa + yy * ca
    wu, _wv = warp_pair(res, seed, 151, 18.0)
    Vw = V + wu * 2.2 + np.sin(U / (40.0 * s)) * 6.0 * s
    ci = np.floor(Vw / (pitch * s))
    ph = h2(ci, ci * 0.0, sd + 11)
    off = Vw - (ci + 0.5) * (pitch * s)
    bj = np.floor(U / (bead * s) + ph * 9.0)
    ub = frac(U / (bead * s) + ph * 9.0)
    bd = np.sqrt(off * off + ((ub - 0.5) * bead * s) ** 2)
    gate = sstep(0.25, 0.45, h2(bj * 0.13, ci, sd + 29))
    beadm = _bump((bd / (2.1 * s)) ** 2) * gate
    tier = _tier(h2(bj, ci, sd + 17))
    _, _, db, idb, _b = _cells(res, 6.5 * s, sd + 71, 0.95, taps=5, need2=False)
    loose = _bump((db / (1.4 * s)) ** 2) * (0.14 + _tier(idb) * 0.22)
    T = 0.22 + beadm * (0.36 + tier * 0.48) + loose
    return n01(T + _fine(res, seed, fine))


def g_ribbons(res, seed, pitch=15.0, seg=6.0, fine=0.11):
    """segmented ribbon weave: two crossing families of linked-cell ribbons,
    cut into segments, with woven over/under parity."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 161, 8.0)
    X = xx + wu
    Y = yy + wv
    ang = 0.62
    ca, sa = np.cos(ang), np.sin(ang)
    qa = (X * ca + Y * sa) / (pitch * s)
    qb = (X * ca - Y * sa) / (pitch * s)
    pa = 1.0 - np.abs(2.0 * frac(qa) - 1.0)
    pb = 1.0 - np.abs(2.0 * frac(qb) - 1.0)
    ribA = sstep(0.42, 0.62, pa)
    ribB = sstep(0.42, 0.62, pb)
    ua = (X * ca - Y * sa) / (seg * s)
    ub = (X * ca + Y * sa) / (seg * s)
    cutA = sstep(0.10, 0.0, np.abs(frac(ua) - 0.5)) * 0.5
    cutB = sstep(0.10, 0.0, np.abs(frac(ub) - 0.5)) * 0.5
    tA = _tier(h2(np.floor(qa), np.floor(ua), sd + 3))
    tB = _tier(h2(np.floor(qb), np.floor(ub), sd + 4))
    over = np.mod(np.floor(qa) + np.floor(qb), 2.0)
    A = ribA * (0.36 + tA * 0.44) - cutA * ribA
    Bv = ribB * (0.36 + tB * 0.44) - cutB * ribB
    T = 0.24 + np.where(over > 0.5, np.maximum(A, Bv * 0.55),
                        np.maximum(Bv, A * 0.55))
    return n01(T + _fine(res, seed, fine))


def g_loopnet(res, seed, pitch=14.0, bead=3.6, fine=0.11):
    """beaded loop-net: irregular pseudohypha loops — cell walls strung with
    touching yeast beads, dim lumens inside."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, d2 = _cells(res, p, sd, 1.0)
    wall = sstep(2.6 * s, 0.6 * s, d2 - d1)
    phase = (dx * np.cos(id1 * _TAU) + dy * np.sin(id1 * _TAU)) / (bead * s)
    beads = wall * (0.5 + 0.5 * np.cos(phase * _TAU)) ** 2.0
    lumen = sstep(0.30, 0.75, d1 / (p * 0.7)) * 0.14
    T = 0.24 + _tier(id1) * 0.24 + wall * 0.26 + beads * 0.50 - lumen
    return n01(T + _fine(res, seed, fine))


def g_swirlspecks(res, seed, pitch=5.6, steps=5, step_px=2.4, fine=0.13):
    """flow-swirled speck drift: micro plankton specks smeared along curl
    swirls, faint streamline threads behind them."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    _, _, d1, id1, _n = _cells(res, p, sd, 0.95, taps=5, need2=False)
    dot = _bump((d1 / (1.6 * s)) ** 2) * (0.45 + _tier(id1) * 0.55)
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
        acc = np.maximum(acc, samp * (1.0 - 0.14 * (k + 1)))
    streaml = (1.0 - np.abs(2.0 * frac(pot * 26.0) - 1.0)) ** 3.0 * 0.16
    T = 0.18 + acc * 0.80 + streaml
    return n01(T + _fine(res, seed, fine))


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
        T = cv2.resize(n01(T), (self.GEN, self.GEN),
                       interpolation=cv2.INTER_NEAREST)
        yy, xx = coords(self.GEN)
        jit = h2(np.floor(xx / g), np.floor(yy / g), sd + 421)
        drift = gauss(Ddom, self.GEN / 48.0)
        D = frac(T * float(d.get("hue_levels", 3.0))
                 + jit * float(d.get("hue_jit", 0.22))
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
    dict(pitch=11.0), (380.0, 950.0, 1.0, 1.30, 0.9),
    [0.88, 0.94, 0.80, 0.10], 6.0,
    "Glossy magenta colony droplets packed dome to dome across the plate. A FRACTURED PETRI finish."),
 # [field 2026-08-02] micro-ripple carpet, cyan cortical folds
 "fpe_cyan_membrane": _R("Cyan Membrane", "ripples",
    dict(pitch=6.0), (390.0, 940.0, 1.0, 1.28, 2.4),
    [0.52, 0.47, 0.58, 0.25], 6.0,
    "A cyan membrane combed into fine cortical ripples, fold after fold. A FRACTURED PETRI finish."),
 # [field 2026-08-02] streak-plate lanes, lime colonies on the streaks
 "fpe_lime_culture": _R("Lime Culture", "streaks",
    dict(lane=13.0, dotp=6.0), (400.0, 930.0, 1.0, 1.30, 3.1),
    [0.25, 0.20, 0.31, 0.09], 6.0,
    "Sinuous lime inoculation streaks beaded with tiny glowing colonies. A FRACTURED PETRI finish."),
 # [field 2026-08-02] crackle-net, amber dried agar
 "fpe_amber_agar": _R("Amber Agar", "crackle",
    dict(pitch=13.0), (405.0, 920.0, 1.0, 1.28, 4.2),
    [0.09, 0.055, 0.13, 0.52], 6.5,
    "Dried amber agar crazed into a fine two-scale web of cracked shards. A FRACTURED PETRI finish."),
 # [field 2026-08-02] dendrite fans, violet fern colonies
 "fpe_violet_garden": _R("Violet Garden", "dendrite",
    dict(pitch=15.0, arms=5.0), (385.0, 955.0, 1.0, 1.30, 5.3),
    [0.74, 0.80, 0.68, 0.26], 6.0,
    "A garden of small violet dendrite ferns, branch tips crowding every gap. A FRACTURED PETRI finish."),
 # [field 2026-08-02] brick-course pills, lime frustules
 "fpe_lime_diatom": _R("Lime Diatom", "pills",
    dict(bw=17.0, rh=8.0), (400.0, 935.0, 1.0, 1.30, 1.8),
    [0.24, 0.30, 0.185, 0.115], 6.0,
    macro=("domains", dict(cells=5, salt=2803)), vd=(0.76, 1.16),
    desc="Courses of lime diatom pills, every tile striated and girdled. A FRACTURED PETRI finish."),
 # [field 2026-08-02] stained plate-mosaic, magenta tissue
 "fpe_magenta_mosaic": _R("Magenta Mosaic", "stainplates",
    dict(pitch=12.0), (385.0, 960.0, 1.0, 1.32, 0.3),
    [0.86, 0.92, 0.79, 0.55], 6.0,
    "A magenta-stained tissue mosaic, chromatin stippling every plate. A FRACTURED PETRI finish."),
 # [field 2026-08-02] spine-burst scatter, cyan urchins
 "fpe_cyan_spineball": _R("Cyan Spineball", "spineball",
    dict(pitch=13.0, spines=11.0), (390.0, 950.0, 1.0, 1.30, 2.0),
    [0.52, 0.58, 0.46, 0.88], 6.0,
    "Tiny cyan spine-balls bristling shoulder to shoulder in the dark. A FRACTURED PETRI finish."),
 # [field 2026-08-02] ring-pack spots, amber zonation
 "fpe_amber_moldring": _R("Amber Moldring", "ringspots",
    dict(pitch=14.0, rings=3.4), (405.0, 925.0, 1.0, 1.28, 3.6),
    [0.10, 0.06, 0.14, 0.30], 6.5,
    "Packed amber mold spots, each zoned in fuzzy concentric rings. A FRACTURED PETRI finish."),
 # [field 2026-08-02] beaded loop-net, violet pseudohyphae
 "fpe_violet_chains": _R("Violet Chains", "loopnet",
    dict(pitch=14.0, bead=3.6), (385.0, 950.0, 1.0, 1.30, 4.7),
    [0.75, 0.69, 0.81, 0.13], 6.0,
    "Violet yeast chains budding into a beaded net of closed loops. A FRACTURED PETRI finish."),
 # [field 2026-08-02] satellite scatter, cyan mothers + daughters
 "fpe_cyan_colony": _R("Cyan Colony", "satellite",
    dict(pitch=14.0, sats=7.0), (390.0, 945.0, 1.0, 1.30, 1.2),
    [0.53, 0.48, 0.59, 0.10], 6.0,
    "Cyan mother colonies ringed by satellite daughters and finer dust. A FRACTURED PETRI finish."),
 # [field 2026-08-02] clumped spore dust, lime mold
 "fpe_lime_mold": _R("Lime Mold", "sporedust",
    dict(), (400.0, 930.0, 1.0, 1.28, 2.9),
    [0.26, 0.21, 0.32, 0.12], 5.5,
    "Lime spore dust gathered in fuzz-rimmed clumps across the plate. A FRACTURED PETRI finish."),
 # [field 2026-08-02] raphe needle felt, amber pennates
 "fpe_amber_diatom": _R("Amber Diatom", "raphe",
    dict(pitch=14.0, ln=9.0), (405.0, 930.0, 1.0, 1.28, 0.6),
    [0.095, 0.14, 0.05, 0.48], 6.0,
    "Striated amber diatom needles felted over the plate, raphe lines dark. A FRACTURED PETRI finish."),
 # [field 2026-08-02] perforated hex mesh, magenta silica
 "fpe_magenta_radiolaria": _R("Magenta Radiolaria", "hexmesh",
    dict(pitch=9.5), (380.0, 960.0, 1.0, 1.32, 5.8),
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
    dict(pitch=15.0, seg=6.0), (405.0, 925.0, 1.0, 1.28, 1.5),
    [0.10, 0.05, 0.145, 0.26], 6.5,
    macro=("bands", dict(angle=0.5, freq=1.3, warp=0.25)), vd=(0.76, 1.18),
    desc="Amber plankton ribbons woven in crossing segmented bands. A FRACTURED PETRI finish."),
 # [field 2026-08-02] foam + nuclei, violet epithelium
 "fpe_violet_membrane": _R("Violet Membrane", "memfoam",
    dict(pitch=11.0), (385.0, 950.0, 1.0, 1.30, 2.6),
    [0.73, 0.79, 0.67, 0.90], 6.0,
    "A violet epithelium foam, a stained nucleus riding in every cell. A FRACTURED PETRI finish."),
 # [field 2026-08-02] bead-chain drift, lime cocci
 "fpe_lime_chains": _R("Lime Chains", "beadchains",
    dict(pitch=12.0, bead=4.4), (400.0, 935.0, 1.0, 1.30, 4.4),
    [0.25, 0.31, 0.19, 0.53], 6.0,
    "Wandering lime cocci chains, bead touching bead across the dark. A FRACTURED PETRI finish."),
 # [field 2026-08-02] radial-ribbed discs, violet centric valves
 "fpe_violet_frustule": _R("Violet Frustule", "discs",
    dict(pitch=12.0, ribs=11.0), (385.0, 955.0, 1.0, 1.30, 0.2),
    [0.74, 0.68, 0.80, 0.11], 6.0,
    "A lattice of violet centric valves, every disc ribbed and pored. A FRACTURED PETRI finish."),
 # [field 2026-08-02] flow-swirled specks, magenta plankton bloom
 "fpe_magenta_plankton": _R("Magenta Plankton", "swirlspecks",
    dict(pitch=5.6, steps=5), (380.0, 960.0, 1.0, 1.32, 3.3),
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

assert len(_PETRI) == 20

GROUPS = {
    "FRACTURED PETRI": _PETRI,
}

KIT = _FieldKit(engines=ENGINES, groups=GROUPS, tag="fractured-petri",
                # [field 2026-08-02] gen 768 -> 640: every generator
                # scales its pitch by res/_S, so the look is identical
                # while the whole module gains ~30% render headroom.
                work=1024, gen=640)

ALL = KIT.ALL
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
