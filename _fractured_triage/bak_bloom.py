# -*- coding: utf-8 -*-
"""FRACTURED BLOOM (2026-07-30) — category 3/10 of the FRACTURED expansion.

════════════════════════════════════════════════════════════════════════════
SPB-FRACTURED-FIELD 2026-08-02 — SECOND corrective pass (owner rejected the
2026-08-01 rebuild: "still VERY subpar... REALLY SIMILAR... repeated designs...
2048x2048 covers an ENTIRE car — things that look intricate are not as
intricate as you think.")
════════════════════════════════════════════════════════════════════════════
Diagnosis vs the flagship FRACTURED MINDS (house standard = a dense
HOMOGENEOUS MICRO-TEXTURE FIELD, thousands of 8-32px features at 2048):
MINDS car-band 0.82; this module's previous median 0.381 with minimums to
~0.05, plus repeated "one big form on dark ground" composition archetypes.

REBUILD LAW APPLIED (all hard):
  * FIELD, NOT POSTER — no feature > ~80px at 2048 unless repeated >= 25x.
    Every generator below is a canvas-filling MEADOW: dominant feature pitch
    5-15px at the 768 gen grid == 13-40px pitch at 2048, feature bodies
    8-32px at 2048.
  * CAR-BAND GATE (fail-closed): FFT ring r in [64,256] at 512 >= 0.45 per
    finish, module median >= 0.60. Macro composition survives only as GENTLE
    modulation (tight vd, low tmod) so low-frequency energy stays small.
  * ARCHETYPE LEDGER — all 20 ids carry DISTINCT compositional archetypes:

      fbl_magenta_whorl   rosette tier-pack (scalloped concentric ring whorls)
      fbl_leafvine_drape  woven trellis cross (two stem families + leaf knots)
      fbl_butter_pollen   echinate dust scatter (bimodal spiky grains + dust)
      fbl_pink_rose       directional lamina eddies (warp-combed petal sheets)
      fbl_coral_cluster   polyp foam pack (walled foam + mouth pores)
      fbl_butter_mosaic   plate-mosaic with floret stamps (grouted plates)
      fbl_pink_pollen     flow-smeared thread-drift (grains advected to trails)
      fbl_white_whorl     micro-billows (shaded cupped petal cushions)
      fbl_coral_stamen    needle felt (two crossed anther-tipped needle plies)
      fbl_lilac_rose      reaction-diffusion petal labyrinth
      fbl_coral_vine      branching stem mesh (3-scale ridge-crest venation)
      fbl_lilac_stamen    star-lattice sparks (near-regular ray bursts)
      fbl_magenta_mosaic  interlocking petal-cross cells (4-lobe cell pack)
      fbl_leaf_whorl      chevron pleats (herringbone pinnate leaflets)
      fbl_white_pollen    clumped structured dust (density-gated grain packs)
      fbl_pink_stamen     comb-fringe rows (banded filament combs + beads)
      fbl_blush_rose      scale imbrication (shingled fan-ribbed petals)
      fbl_lilac_vine      hanging bead-strand curtain (swaying racemes)
      fbl_butter_whorl    pinwheel curl pave (tiny log-spiral whorls)
      fbl_magenta_pollen  porate close-pack grains (reticulate + germ pores)

  * PALETTES — 3-4 distinct hue anchors per id (luminous, not muddy) picked
    per FEATURE via the hue_cell Ddom refinement below, plus the 8-tier
    per-feature brightness law (_TIERS).
  * CONTRACT UNCHANGED — same 20 ids, same GROUPS key, same
    install_into_engine(mono_reg, base_reg=None) -> (spec_fn, paint_fn).
    Spec traces paint (CategoryKit carves from the same cached art).
    Work grid 1024 (kit work=1024, generators at 640). Determinism:
    per-finish seed = zlib.crc32(fid.encode()) — np.random.default_rng only,
    no hash(str) anywhere. h2 salts are kept < 8k (seed % 7919): float32
    precision destroys the sin-hash above ~1e6.

Verify artifacts: _fractured_triage/refield_bloom.jsonl (per-finish verdicts)
and _fractured_triage/resheet_bloom.png (5x4 labeled contact sheet).
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
_S = 768.0            # generator px-space anchor (pitch is res/_S scaled)            # generator px-space anchor (kit gen=768)

# owner doctrine: 8-tier per-feature brightness palette — never 1-2 levels.
_TIERS = np.array([0.16, 0.27, 0.38, 0.49, 0.60, 0.70, 0.81, 0.93], np.float32)


def _tier(hv):
    return _TIERS[np.clip((np.asarray(hv, np.float32) * 8.0).astype(np.int32), 0, 7)]


def _sd(seed):
    """Small deterministic h2 salt from the crc32 finish seed (float32-safe)."""
    return int(seed) % 7919


def _bump(t2):
    """Compact smooth bump ~= exp(-t2), 3 cheap array ops (perf doctrine)."""
    return np.clip(1.0 - np.asarray(t2, np.float32) * 0.45, 0.0, 1.0) ** 2


def _grain(xx, yy, cell, salt, thr=0.62):
    """Crisp per-cell speckle at `cell` px — highest structural band."""
    g = h2(np.floor(xx / float(cell)), np.floor(yy / float(cell)), salt)
    return sstep(thr, min(thr + 0.18, 0.999), g)


def _fine(res, seed, k=0.13):
    """Closing micro-stack: ridged mid band + crisp noise band. Keeps every
    square inch of ground alive (coverage law) without low-freq energy."""
    r1 = fbm(res, res, rng(seed, 811), 2, 180)
    ridge = (1.0 - np.abs(2.0 * r1 - 1.0)) ** 2
    n2 = fbm(res, res, rng(seed, 823), 1, 320)
    return (ridge * 0.6 + n2 * 0.4).astype(np.float32) * float(k)


def _cells(res, pitch, salt, jit=0.85, taps=9, need2=True):
    """Jittered-grid nearest-feature field. Returns (dx, dy, d1, id1, d2):
    offset to / distance to the nearest feature point in px, per-feature hash
    id, and second-nearest distance (None when need2=False). The one kernel
    that lets a generator stamp THOUSANDS of 8-32px features vectorized.
    Perf [field 2026-08-02 pass 2]: the per-cell hashes are computed ONCE on
    the coarse cell grid and gathered per tap (27 full-res sin evals -> 3
    tiny grids + cheap int gathers); dot-stamp layers can run taps=5 (cross
    neighborhood) / need2=False — a missed diagonal dot in a dense field is
    invisible, and it cut the 2-layer generators from ~2.1 s to budget."""
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
# STRUCTURAL GENERATORS — 20 distinct field archetypes, one per finish id.
# Every one: dominant pitch <= ~15px at 768, per-feature 8-tier value, 3+
# frequency bands, full-canvas coverage. [SPB-FRACTURED-FIELD 2026-08-02]
# ════════════════════════════════════════════════════════════════════════════

def g_rosette(res, seed, pitch=12.0, rings=2.6, petals=7.0, fine=0.15):
    """rosette tier-pack: pave of small scalloped concentric-ring whorls."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _2 = _cells(res, p, sd, 0.75, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.70)
    scal = 0.11 * np.cos(th * petals + id1 * 61.0)
    ring = 0.5 + 0.5 * np.cos((rr + scal) * rings * _TAU + id1 * 11.0)
    body = np.clip(1.10 - rr, 0.0, 1.0)
    rim = sstep(0.12, 0.03, np.abs(rr - 0.70)) * 0.30
    T = _tier(id1) * 0.40 + body * (0.14 + 0.55 * ring * ring) + rim
    return n01(T + _fine(res, seed, fine))


def g_pleat(res, seed, col=13.0, rib=4.6, fine=0.13):
    """chevron pleats: herringbone columns of fine pinnate leaflet ribs."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 23, 10.0)
    X = xx + wu
    Y = yy + wv
    cw = col * s
    ci = np.floor(X / cw)
    u = frac(X / cw)
    sign = 1.0 - 2.0 * np.mod(ci, 2.0)
    q = Y / (rib * s) + sign * u * (cw / (rib * s)) * 0.85
    ribs = (1.0 - np.abs(2.0 * frac(q) - 1.0)) ** 1.7
    seam = sstep(0.10, 0.0, np.minimum(u, 1.0 - u)) * 0.55
    mid = sstep(0.06, 0.015, np.abs(u - 0.5)) * 0.50
    tier = _tier(h2(ci, np.floor(q), sd + 5))
    T = 0.30 + tier * 0.34 + ribs * 0.34 - seam + mid
    return n01(T + _fine(res, seed, fine))


def g_pinwheel(res, seed, pitch=13.0, arms=5.0, twist=2.0, fine=0.14):
    """pinwheel curl pave: field of tiny log-spiral petal whorls."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.7, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.68)
    sp = (0.5 + 0.5 * np.cos(th * arms + rr * twist * _TAU + id1 * 43.0)) ** 2.2
    body = np.clip(1.06 - rr, 0.0, 1.0)
    core = _bump((rr * 3.2) ** 2) * 0.35
    T = _tier(id1) * 0.50 + body * (0.14 + 0.52 * sp) + core
    return n01(T + _fine(res, seed, fine))


def g_billow(res, seed, pitch=12.0, lx=0.62, ly=0.79, fine=0.12):
    """micro-billows: close-packed shaded petal cushions + kissing shadows."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, d2 = _cells(res, p, sd, 0.85)
    rr = d1 / (p * 0.72)
    dome = np.clip(1.0 - rr * rr, 0.0, 1.0)
    lam = np.clip((dx * lx + dy * ly) / np.maximum(d1, 1e-4), -1.0, 1.0)
    lam = lam * np.sqrt(np.clip(rr, 0.0, 1.0))
    crease = (0.5 + 0.5 * np.cos(rr * 2.0 * _TAU + id1 * 17.0)) * 0.18
    contact = sstep(2.2 * s, 0.4 * s, d2 - d1) * 0.30
    T = _tier(id1) * 0.46 + dome * 0.42 + lam * 0.20 + crease - contact
    return n01(T + _fine(res, seed, fine))


def g_lamina(res, seed, pitch=5.0, angle=0.9, warp=24.0, fine=0.15):
    """directional lamina eddies: warp-combed fine petal sheets."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 41, warp)
    ca, sa = np.cos(angle), np.sin(angle)
    q = ((xx + wu * 2.4) * ca + (yy + wv * 2.4) * sa) / (pitch * s)
    lam = (1.0 - np.abs(2.0 * frac(q) - 1.0)) ** 1.5
    tier = _tier(h2(np.floor(q), np.floor(q * 0.13), sd + 9))
    q2 = ((xx - wv * 1.8) * sa - (yy - wu * 1.8) * ca) / (pitch * 1.6 * s)
    cross = (1.0 - np.abs(2.0 * frac(q2) - 1.0)) ** 2.0
    T = 0.26 + tier * 0.24 + lam * 0.46 + cross * 0.16
    return n01(T + _fine(res, seed, fine))


def g_rdlab(res, seed, sig=2.3, iters=4, gain=1.9, fine=0.11):
    """reaction-diffusion petal labyrinth: DoG-sharpened stripe maze."""
    s = res / _S
    sd = _sd(seed)
    f = fbm(res, res, rng(seed, 55), 3, 64)
    for _ in range(int(iters)):
        f = np.clip(f + gain * (f - gauss(f, sig * s)), 0.0, 1.0)
    lab = sstep(0.35, 0.65, f)
    edge = 1.0 - np.abs(2.0 * lab - 1.0)
    tier = _tier(h2(np.floor(gauss(f, 6.0 * s) * 24.0), f * 0.0, sd + 3))
    T = 0.24 + lab * 0.42 + edge * 0.22 + tier * 0.22
    return n01(T + _fine(res, seed, fine))


def g_imbric(res, seed, sw=11.0, rh=8.0, ribs=9.0, fine=0.11):
    """scale imbrication: shingled fan-ribbed petal scales in offset rows."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 61, 6.0)
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
        rrad = np.hypot(du, dv * 0.9) / (sw * s * 0.62)
        inside = sstep(1.0, 0.92, rrad)
        th = np.arctan2(du, dv + 1e-4)
        fan = 0.5 + 0.5 * np.cos(th * ribs + h2(cu, cv_, sd + 7) * 6.0)
        val = (_tier(h2(cu, cv_, sd)) * 0.50
               + np.clip(1.0 - rrad, 0.0, 1.0) ** 0.8 * 0.34
               + fan * 0.14 * np.clip(1.0 - rrad, 0.0, 1.0))
        T = T + val * inside * (1.0 - done)
        done = np.clip(done + inside, 0.0, 1.0)
    T = T + (1.0 - done) * 0.12
    return n01(T + _fine(res, seed, fine))


def g_foam(res, seed, pitch=10.0, fine=0.12):
    """polyp foam pack: bright-walled foam cells with dark mouth pores."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, d2 = _cells(res, p, sd, 0.95)
    wall = sstep(2.6 * s, 0.7 * s, d2 - d1)
    rr = d1 / (p * 0.75)
    dome = np.clip(1.0 - rr * rr, 0.0, 1.0)
    mouth = _bump((d1 / (1.8 * s)) ** 2) * 0.40
    T = _tier(id1) * 0.42 + dome * 0.34 + wall * 0.34 - mouth
    return n01(T + _fine(res, seed, fine))


def g_platemosaic(res, seed, pitch=14.0, petals=8.0, fine=0.11):
    """plate-mosaic: grouted worley plates, each stamped with a ray floret."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, d2 = _cells(res, p, sd, 0.62)
    grout = sstep(2.4 * s, 0.6 * s, d2 - d1)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.62)
    ring = sstep(0.14, 0.04, np.abs(rr - 0.46))
    ring = ring * (0.55 + 0.45 * np.cos(th * petals + id1 * 31.0))
    disc = sstep(0.20, 0.10, rr)
    disc = disc * (0.55 + 0.45 * _grain(dx + 31.0, dy + 47.0, 2.2 * s, sd + 13))
    T = 0.24 + _tier(id1) * 0.40 + ring * 0.34 + disc * 0.30 - grout * 0.55
    return n01(T + _fine(res, seed, fine))


def g_petalcells(res, seed, pitch=12.0, fine=0.11):
    """interlocking petal-cross cells: packed 4-lobe florets + veins + eye."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, d2 = _cells(res, p, sd, 0.55)
    th = np.arctan2(dy, dx)
    a0 = id1 * _TAU
    lobe = np.abs(np.cos((th - a0) * 2.0)) ** 1.3
    rr = d1 / (p * 0.72)
    body = np.clip(1.05 - rr, 0.0, 1.0)
    vein = sstep(0.10, 0.02, np.abs(np.sin((th - a0) * 2.0))) * body * 0.30
    wall = sstep(2.0 * s, 0.5 * s, d2 - d1) * 0.50
    eye = _bump((d1 / (2.0 * s)) ** 2) * 0.35
    T = _tier(id1) * 0.42 + body * lobe * 0.44 + vein + eye - wall
    return n01(T + _fine(res, seed, fine))


def _needles(res, pitch, sd, ln, wd, s):
    dx, dy, d1, id1, _ = _cells(res, pitch * s, sd, 0.9, taps=5, need2=False)
    a = id1 * _TAU
    ca, sa = np.cos(a), np.sin(a)
    along = dx * ca + dy * sa
    across = np.abs(-dx * sa + dy * ca)
    L = ln * s * (0.6 + 0.8 * h2(id1 * 31.0, id1 * 17.0, sd + 3))
    body = sstep(wd * s, wd * s * 0.25, across) * sstep(L, L * 0.82, np.abs(along))
    tipd = np.hypot(dx - ca * L, dy - sa * L)
    anther = _bump((tipd / (2.3 * s)) ** 2)
    return body, anther, id1


def g_needlefelt(res, seed, pitch=13.0, ln=7.5, fine=0.12):
    """needle felt: two crossed plies of anther-tipped stamen needles."""
    s = res / _S
    sd = _sd(seed)
    b1, a1, i1 = _needles(res, pitch, sd, ln, 1.3, s)
    b2, a2, i2 = _needles(res, pitch * 0.78, sd + 101, ln * 0.8, 1.1, s)
    T = (0.22 + np.maximum(b1 * (0.35 + _tier(i1) * 0.45),
                           b2 * (0.30 + _tier(i2) * 0.40))
         + np.maximum(a1, a2 * 0.85) * 0.50)
    return n01(T + _fine(res, seed, fine))


def g_starlat(res, seed, pitch=12.0, rays=7.0, fine=0.12):
    """star-lattice sparks: near-regular lattice of fine ray bursts."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.25, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.72)
    star = (0.5 + 0.5 * np.cos(th * rays + id1 * _TAU)) ** 3.5
    star = star * np.clip(1.0 - rr, 0.0, 1.0)
    core = _bump((rr * 4.0) ** 2) * 0.50
    halo = sstep(0.16, 0.05, np.abs(rr - 0.62)) * 0.10
    T = 0.22 + _tier(id1) * 0.34 + star * 0.55 + core + halo
    return n01(T + _fine(res, seed, fine))


def g_fringe(res, seed, rh=15.0, fw=4.2, fine=0.11):
    """comb-fringe rows: banded filament combs, anther bead at every tip."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 71, 7.0)
    X = xx + wu
    Y = yy + wv
    rj = np.floor(Y / (rh * s))
    v = frac(Y / (rh * s))
    X2 = X + h2(rj, rj * 0.0, sd + 21) * 37.0
    fi = np.floor(X2 / (fw * s))
    u = frac(X2 / (fw * s))
    fil = (1.0 - np.abs(2.0 * u - 1.0)) ** 2.2
    fil = fil * sstep(0.06, 0.16, v) * sstep(0.95, 0.80, v)
    tier = _tier(h2(fi, rj, sd + 33))
    bead = _bump(((v - 0.82) * rh / 2.0) ** 2 + ((u - 0.5) * fw / 1.8) ** 2)
    base = sstep(0.10, 0.02, v) * 0.35
    T = 0.22 + fil * (0.30 + tier * 0.42) + bead * 0.55 + base
    return n01(T + _fine(res, seed, fine))


def g_echinate(res, seed, pitch=9.5, spikes=9.0, fine=0.10):
    """echinate dust scatter: spiky pollen grains + a finer dust ply."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.9, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.62)
    prof = rr - 0.20 * np.maximum(np.cos(th * spikes + id1 * _TAU), 0.0) ** 3
    body = sstep(0.58, 0.44, prof)
    core = _bump((rr * 2.6) ** 2) * 0.25
    _, _, db, idb, _2 = _cells(res, 4.2 * s, sd + 77, 0.95, taps=5, need2=False)
    dust = _bump((db / (1.25 * s)) ** 2)
    T = (0.20 + body * (0.28 + _tier(id1) * 0.44) + core
         + dust * (0.18 + _tier(idb) * 0.28))
    return n01(T + _fine(res, seed, fine))


def g_threaddrift(res, seed, pitch=6.8, steps=5, step_px=2.6, fine=0.15):
    """flow-smeared thread-drift: grains advected into fading comet trails."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.95, taps=5, need2=False)
    dot = _bump((d1 / (2.2 * s)) ** 2) * (0.50 + _tier(id1) * 0.50)
    pot = gauss(fbm(res, res, rng(seed, 91), 3, 6), 3.0)
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
        acc = np.maximum(acc, samp * (1.0 - 0.13 * (k + 1)))
    _, _, db2, idb2, _b2 = _cells(res, 3.6 * s, sd + 177, 0.95, taps=5,
                                  need2=False)
    dust = _bump((db2 / (1.1 * s)) ** 2) * (0.18 + _tier(idb2) * 0.50)
    T = 0.16 + acc * 0.85 + dust * 0.85
    return n01(T + _fine(res, seed, fine))


def g_dustclump(res, seed, fine=0.11):
    """clumped structured dust: two grain plies breathing with a shallow
    clump envelope (voids kept small — car-band law)."""
    s = res / _S
    sd = _sd(seed)
    env = sstep(0.30, 0.75, fbm(res, res, rng(seed, 101), 3, 20))
    _, _, da, ida, _a = _cells(res, 5.2 * s, sd, 0.95, taps=5, need2=False)
    _, _, db, idb, _b = _cells(res, 9.5 * s, sd + 55, 0.95, taps=5, need2=False)
    ga = _bump((da / (1.5 * s)) ** 2) * (0.4 + _tier(ida) * 0.6)
    gb = _bump((db / (2.6 * s)) ** 2) * (0.4 + _tier(idb) * 0.6)
    dust = np.maximum(ga * (0.45 + 0.55 * env), gb * (0.25 + 0.75 * env))
    T = 0.20 + dust * 0.78 + env * 0.10
    return n01(T + _fine(res, seed, fine))


def g_porate(res, seed, pitch=10.5, pores=3, fine=0.10):
    """porate close-pack grains: reticulate near-touching grains, germ pores."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _2 = _cells(res, p, sd, 0.55, need2=False)
    rr = d1 / (p * 0.70)
    body = sstep(0.78, 0.62, rr)
    rim = sstep(0.10, 0.03, np.abs(rr - 0.66)) * 0.28
    ret = _grain(dx + 13.0, dy + 71.0, 2.0 * s, sd + 5) * body * 0.22
    T = 0.20 + body * (0.30 + _tier(id1) * 0.40) + rim + ret
    for k in range(int(pores)):
        a = id1 * _TAU + k * 2.4
        pd = np.hypot(dx - np.cos(a) * p * 0.30, dy - np.sin(a) * p * 0.30)
        T = T - _bump((pd / (1.5 * s)) ** 2) * 0.30 * body
    return n01(T + _fine(res, seed, fine))


def g_trellis(res, seed, pitch=13.0, angle=0.55, fine=0.11):
    """woven trellis cross: two stem families, dark knots, leaf specks."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 111, 9.0)
    X = xx + wu
    Y = yy + wv
    ca, sa = np.cos(angle), np.sin(angle)
    qa = (X * ca + Y * sa) / (pitch * s)
    qb = (X * ca - Y * sa) / (pitch * s)
    pa = 1.0 - np.abs(2.0 * frac(qa) - 1.0)
    pb = 1.0 - np.abs(2.0 * frac(qb) - 1.0)
    stemA = pa ** 3.0
    stemB = pb ** 3.0
    tA = _tier(h2(np.floor(qa), qa * 0.0, sd + 3))
    tB = _tier(h2(np.floor(qb), qb * 0.0, sd + 4))
    stem = np.maximum(stemA * (0.40 + tA * 0.50), stemB * (0.40 + tB * 0.50))
    knot = (pa * pb) ** 3.0
    gate = sstep(0.35, 0.55, h2(np.floor(qa + 0.5), np.floor(qb + 0.5), sd + 9))
    T = 0.22 + stem * 0.55 + knot * gate * 0.45 - stemA * stemB * 0.18
    return n01(T + _fine(res, seed, fine))


def g_stemmesh(res, seed, fine=0.11):
    """branching stem mesh: 3-scale ridge-crest venation + bud dots."""
    s = res / _S
    sd = _sd(seed)

    def crest(base, salt, w):
        f = fbm(res, res, rng(seed, salt), 2, base)
        r = 1.0 - np.abs(2.0 * f - 1.0)
        return sstep(1.0 - w, 1.0 - w * 0.35, r)

    macrov = crest(24, 121, 0.16) * 0.50
    midv = crest(56, 131, 0.14) * 0.80
    finev = crest(120, 141, 0.12)
    _, _, bd, bid, _b = _cells(res, 7.0 * s, sd + 61, 0.95, taps=5, need2=False)
    buds = _bump((bd / (1.8 * s)) ** 2)
    buds = buds * sstep(0.30, 0.70, h2(bid * 91.0, bid * 47.0, sd + 8))
    T = 0.24 + macrov * 0.30 + midv * 0.38 + finev * 0.30 + buds * 0.45
    return n01(T + _fine(res, seed, fine))


def g_beadcurtain(res, seed, pitch=11.0, bead=7.0, fine=0.11):
    """hanging bead-strand curtain: swaying strands of tiered pea blossoms."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    ci = np.floor(xx / (pitch * s))
    ph = h2(ci, ci * 0.0, sd + 11)
    sway = (np.sin(yy / (34.0 * s) + ph * _TAU) * 2.4 * s
            + np.sin(yy / (9.0 * s) + ph * 9.0) * 0.8 * s)
    u = xx - (ci + 0.5) * (pitch * s) - sway
    strand = sstep(1.4 * s, 0.4 * s, np.abs(u))
    bj = np.floor(yy / (bead * s) + ph * 7.0)
    vb = frac(yy / (bead * s) + ph * 7.0)
    tap = 0.55 + 0.45 * h2(ci, np.floor(yy / (64.0 * s)), sd + 31)
    brad = (2.6 * s) * tap
    bd = np.sqrt(u * u + ((vb - 0.5) * bead * s) ** 2)
    beadm = _bump((bd / np.maximum(brad, 1e-3)) ** 2)
    tier = _tier(h2(ci, bj, sd + 17))
    T = 0.22 + strand * 0.30 + beadm * (0.35 + tier * 0.45)
    return n01(T + _fine(res, seed, fine))


ENGINES = {
    "rosette": g_rosette, "pleat": g_pleat, "pinwheel": g_pinwheel,
    "billow": g_billow, "lamina": g_lamina, "rdlab": g_rdlab,
    "imbric": g_imbric, "foam": g_foam, "platemosaic": g_platemosaic,
    "petalcells": g_petalcells, "needlefelt": g_needlefelt,
    "starlat": g_starlat, "fringe": g_fringe, "echinate": g_echinate,
    "threaddrift": g_threaddrift, "dustclump": g_dustclump,
    "porate": g_porate, "trellis": g_trellis, "stemmesh": g_stemmesh,
    "beadcurtain": g_beadcurtain,
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
       vd=(0.78, 1.16), tmod=0.10, hspan=0.05, satboost=1.45, val=0.24,
       kw=None):
    base_kw = dict(ambient=0.22, ambient_sigma=40, floor=0.11, sparkle=0.14,
                   mswing=1.35)
    if kw:
        base_kw.update(kw)
    return dict(name=name, engine=engine, eargs=eargs, lut=lut, hues=hues,
                hspan=hspan, satboost=satboost, macro=macro, vd=vd, tmod=tmod,
                val=val, hue_cell=hue_cell, hue_drift=0.5, kw=base_kw,
                desc=desc)


# ════════════════════════════════════════════════════════════════════════════
# RECIPES — 20 finishes. Insertion order == 5x4 contact-sheet order (no two
# adjacent tiles share a hero hue). All seeds = crc32(fid). Every recipe:
# [SPB-FRACTURED-FIELD 2026-08-02] dense-field rebuild, archetype per ledger.
# ════════════════════════════════════════════════════════════════════════════

_BLOOM = {
 # [field 2026-08-02] rosette tier-pack, magenta/violet/pink over leaf dark
 "fbl_magenta_whorl": _R("Magenta Whorl", "rosette",
    dict(pitch=12.0, rings=2.6, petals=7.0), (380.0, 940.0, 1.0, 1.30, 0.6),
    [0.87, 0.78, 0.30, 0.92], 6.0,
    "A pave of tiny magenta rose whorls, ring on scalloped ring, shoulder to shoulder. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] woven trellis, leaf/chartreuse/teal + amber knots
 "fbl_leafvine_drape": _R("Leafvine Drape", "trellis",
    dict(pitch=13.0, angle=0.55), (395.0, 930.0, 1.0, 1.28, 2.2),
    [0.30, 0.22, 0.42, 0.10], 13.0,
    "A woven trellis of fine green vine stems, a leaf knotted at every crossing. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] echinate scatter, butter/amber/lemon dust
 "fbl_butter_pollen": _R("Butter Pollen", "echinate",
    dict(pitch=9.5, spikes=9.0), (410.0, 920.0, 1.0, 1.30, 2.8),
    [0.115, 0.09, 0.16, 0.05], 9.5,
    "A dense butter-yellow fall of spiky pollen grains with finer dust sifted between. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] lamina eddies, pink/rose/magenta sheets
 "fbl_pink_rose": _R("Pink Rose Spiral", "lamina",
    dict(pitch=5.5, angle=0.9, warp=30.0), (385.0, 960.0, 1.0, 1.32, 1.1),
    [0.93, 0.97, 0.86, 0.30], 5.0,
    "Fine pink petal sheets combed into a thousand small rose eddies. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] polyp foam, coral/apricot/pink walls
 "fbl_coral_cluster": _R("Coral Cluster", "foam",
    dict(pitch=10.0), (380.0, 950.0, 1.0, 1.30, 3.4),
    [0.035, 0.075, 0.98, 0.30], 6.0,
    "A packed coral foam of tiny florets, every cell walled bright with a dark mouth. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] plate mosaic, butter/orange/leaf grouted florets
 "fbl_butter_mosaic": _R("Butter Mosaic", "platemosaic",
    dict(pitch=14.0, petals=8.0), (415.0, 915.0, 1.0, 1.30, 4.0),
    [0.115, 0.05, 0.30, 0.14], 14.0,
    macro=("domains", dict(cells=5, salt=1471)), vd=(0.76, 1.16),
    desc="A grouted mosaic of small butter tiles, a ray floret stamped in every plate. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] thread-drift, pink/rose/orchid comet grains
 "fbl_pink_pollen": _R("Pink Pollen Drift", "threaddrift",
    dict(pitch=8.0, steps=5, step_px=2.6), (385.0, 965.0, 1.0, 1.30, 5.0),
    [0.90, 0.96, 0.83, 0.74], 5.0, val=0.30,
    kw=dict(sparkle=0.44),
    desc="Pink pollen grains smeared into fine drifting comet trails across dark silk. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] micro-billows, pearl gardenia — tinted, NOT chroma-dead
 "fbl_white_whorl": _R("Gardenia Whorl", "billow",
    dict(pitch=12.0), (400.0, 890.0, 0.95, 1.10, 3.0),
    [0.12, 0.55, 0.93, 0.30], 12.0, satboost=1.05, val=0.26,
    kw=dict(floor=0.14, sparkle=0.12),
    desc="Cushioned gardenia petals packed edge to edge, pearl light on every cup. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] needle felt, red-coral/gold anthers
 "fbl_coral_stamen": _R("Coral Stamen", "needlefelt",
    dict(pitch=13.0, ln=7.5), (380.0, 970.0, 1.0, 1.30, 1.6),
    [0.02, 0.06, 0.115, 0.97], 13.0,
    "A felt of fine coral stamen needles, a gold anther bead at every tip. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] RD petal labyrinth, lilac/violet walls
 "fbl_lilac_rose": _R("Lilac Rose Spiral", "rdlab",
    dict(sig=2.3, iters=4), (390.0, 945.0, 1.0, 1.30, 4.4),
    [0.74, 0.80, 0.68, 0.33], 6.0,
    "A lilac labyrinth of packed rose-petal walls winding over the whole panel. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] branching stem mesh, leaf/coral/amber veins
 "fbl_coral_vine": _R("Coral Vine Drape", "stemmesh",
    dict(), (380.0, 975.0, 1.0, 1.28, 5.2),
    [0.30, 0.04, 0.085, 0.44], 9.0,
    "A climbing mesh of branching coral vine veins, buds glowing at the nodes. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] star-lattice, lilac/violet/gold sparks
 "fbl_lilac_stamen": _R("Lilac Starburst", "starlat",
    dict(pitch=12.0, rays=7.0), (390.0, 950.0, 1.0, 1.32, 3.8),
    [0.72, 0.78, 0.13, 0.85], 6.0,
    macro=("bands", dict(angle=0.4, freq=1.2, warp=0.25)), vd=(0.76, 1.18),
    desc="A lattice of tiny lilac stamen bursts, gold-tipped rays on every spark. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] petal-cross cells, magenta/violet/pink pack
 "fbl_magenta_mosaic": _R("Magenta Mosaic", "petalcells",
    dict(pitch=12.0), (385.0, 960.0, 1.0, 1.32, 0.3),
    [0.86, 0.78, 0.92, 0.27], 6.0,
    "Interlocking magenta hydrangea florets, four petals to a cell, packed tight. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] chevron pleats, leaf/emerald herringbone
 "fbl_leaf_whorl": _R("Leaf Whorl", "pleat",
    dict(col=13.0, rib=4.6), (395.0, 935.0, 1.0, 1.28, 2.0),
    [0.28, 0.35, 0.20, 0.115], 13.0,
    "Herringbone pleats of fine green leaflets, rib after rib after rib. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] structured dust, moonlit blue/cream clumps
 "fbl_white_pollen": _R("Moon Pollen", "dustclump",
    dict(), (400.0, 895.0, 0.95, 1.10, 3.2),
    [0.55, 0.13, 0.44, 0.65], 7.0, satboost=1.05, val=0.26,
    kw=dict(floor=0.14, sparkle=0.12),
    desc="Moon-white pollen dust gathered in silver clumps and small dark voids. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] comb-fringe rows, pink/gold filament combs
 "fbl_pink_stamen": _R("Pink Stamen Star", "fringe",
    dict(rh=15.0, fw=4.2), (380.0, 980.0, 1.0, 1.32, 0.1),
    [0.92, 0.97, 0.13, 0.86], 6.0,
    "Row upon row of fine pink stamen combs, a gold bead at every filament tip. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] scale imbrication, blush/peach shingles
 "fbl_blush_rose": _R("Blush Rose Spiral", "imbric",
    dict(sw=11.0, rh=8.0, ribs=9.0), (400.0, 900.0, 0.95, 1.18, 1.7),
    [0.95, 0.02, 0.90, 0.33], 6.0, satboost=1.30, val=0.25,
    desc="Blush rose petals shingled like fish scales, a ribbed fan in every one. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] bead-strand curtain, wisteria lilac racemes
 "fbl_lilac_vine": _R("Wisteria Drape", "beadcurtain",
    dict(pitch=11.0, bead=7.0), (390.0, 950.0, 1.0, 1.30, 4.1),
    [0.72, 0.79, 0.66, 0.30], 11.0,
    "A curtain of swaying wisteria strands strung with tiny lilac pea blossoms. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] pinwheel curl pave, butter/amber spirals
 "fbl_butter_whorl": _R("Butter Whorl", "pinwheel",
    dict(pitch=13.0, arms=5.0, twist=2.0), (415.0, 920.0, 1.0, 1.30, 2.6),
    [0.115, 0.085, 0.15, 0.30], 6.0,
    "A pave of tiny butter-gold pinwheel whorls, every curl spun tight. A FRACTURED BLOOM finish."),
 # [field 2026-08-02] porate close-pack, magenta/violet grains
 "fbl_magenta_pollen": _R("Magenta Pollen", "porate",
    dict(pitch=10.5, pores=3), (385.0, 960.0, 1.0, 1.32, 4.9),
    [0.83, 0.89, 0.95, 0.74], 6.0,
    "Magenta pollen grains packed grain on grain, each reticulate and pored. A FRACTURED BLOOM finish."),
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
    "fbl_magenta_whorl": (("continents", dict(base=3, cells=3.0)), (0.84, 1.13)),
    "fbl_leafvine_drape": (("none", {}), (0.78, 1.16)),
    "fbl_butter_pollen": (("rings", dict(freq=5.0, cx=0.42, cy=0.55)), (0.84, 1.13)),
    "fbl_pink_rose": (("bands", dict(angle=0.9, freq=2.4, warp=0.30)), (0.84, 1.13)),
    "fbl_coral_cluster": (("domains", dict(cells=3, salt=1201)), (0.84, 1.13)),
    "fbl_butter_mosaic": (("domains", dict(cells=8, salt=1471)), (0.84, 1.13)),
    "fbl_pink_pollen": (("vortex", dict(arms=2.0, twist=8.0)), (0.84, 1.13)),
    "fbl_white_whorl": (("margin", dict(freq=3.0, radius=0.78)), (0.84, 1.13)),
    "fbl_coral_stamen": (("rachis", dict(angle=0.5, sweep=4.0)), (0.84, 1.13)),
    "fbl_lilac_rose": (("continents", dict(base=4, cells=5.0)), (0.84, 1.13)),
    "fbl_coral_vine": (("none", {}), (0.78, 1.16)),
    "fbl_lilac_stamen": (("bands", dict(angle=1.5, freq=3.6, warp=0.22)), (0.84, 1.13)),
    "fbl_magenta_mosaic": (("domains", dict(cells=14, salt=1733)), (0.84, 1.13)),
    "fbl_leaf_whorl": (("none", {}), (0.78, 1.16)),
    "fbl_white_pollen": (("continents", dict(base=5, cells=2.5)), (0.84, 1.13)),
    "fbl_pink_stamen": (("rings", dict(freq=7.5, two=True)), (0.84, 1.13)),
    "fbl_blush_rose": (("vortex", dict(arms=3.0, twist=5.0, two=True)), (0.84, 1.13)),
    "fbl_lilac_vine": (("bands", dict(angle=0.1, freq=1.8, warp=0.34)), (0.84, 1.13)),
    "fbl_butter_whorl": (("domains", dict(cells=5, salt=1987)), (0.84, 1.13)),
    "fbl_magenta_pollen": (("none", {}), (0.78, 1.16)),
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
    _BLOOM[_fid]["macro"] = _mac
    _BLOOM[_fid]["vd"] = _vd
    _BLOOM[_fid]["tmod"] = 0.08
    _BLOOM[_fid]["hue_drift"] = 0.30 if _mac[0] == "none" else 0.95
# determinism law: per-finish seed straight from the id (no hash(str)).
for _fid, _d in _BLOOM.items():
    _d["seed"] = zlib.crc32(_fid.encode()) & 0x7FFFFFFF

assert len(_BLOOM) == 20

GROUPS = {
    "FRACTURED BLOOM": _BLOOM,
}

KIT = _FieldKit(engines=ENGINES, groups=GROUPS, tag="fractured-bloom",
                # [field 2026-08-02] gen 768 -> 640: every generator
                # scales its pitch by res/_S, so the look is identical
                # while the whole module gains ~30% render headroom.
                work=1024, gen=640)

ALL = KIT.ALL
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
