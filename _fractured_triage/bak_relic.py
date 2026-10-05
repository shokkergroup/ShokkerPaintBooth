# -*- coding: utf-8 -*-
"""FRACTURED RELIC (2026-08-01) — category of the FRACTURED expansion.

════════════════════════════════════════════════════════════════════════════
SPB-FRACTURED-FIELD 2026-08-02 — SECOND corrective pass (owner rejected the
2026-08-01 rebuild: "still VERY subpar... REALLY SIMILAR... repeated
designs... 2048x2048 covers an ENTIRE car — things that look intricate are
not as intricate as you think.")
════════════════════════════════════════════════════════════════════════════
Previous car-band median 0.209 — the WORST of the three modules, and the most
poster-like: single large glyph slabs, one big ziggurat, one wide inlay band.
On a whole car that reads as a smeared logo, not a relic.

Owner's own words are the spec for this category: "a whole TABLET of 10-24px
glyphs is PERFECT — one giant glyph is banned." Every generator below is now
a PAVE: hundreds-to-thousands of small tesserae, inlay chips, glyph cells,
leaf flakes and carved units at 8-32px on the 2048 canvas (pitch 6-16px on
the 768 gen grid), aged in place (chips / patina / tooth) so it still reads
as antiquity rather than wallpaper.

ARCHETYPE LEDGER — all 20 ids carry DISTINCT compositional archetypes:

  fre_lapis_inlay        chip-inlay pave (irregular stone chips in dark mastic)
  fre_gold_inlay         thread-drift wire inlay (fine wires combed over stone)
  fre_turquoise_inlay    granular micro-mosaic dust (sand-grade tesserae)
  fre_terracotta_inlay   banded strata laminae (fine sediment ply + grit)
  fre_malachite_mosaic   square tesserae grid (grouted, per-tile shade)
  fre_ivory_mosaic       scale imbrication (shingled ivory plaques)
  fre_lapis_mosaic       opus-vermiculatum worms (curved courses of chips)
  fre_gold_mosaic        star-lattice rosette pave (small tessellated stars)
  fre_turquoise_leaf     crackle-net gilding (leaf craquelure web)
  fre_terracotta_leaf    torn-flake pack (overlapping leaf flakes + tears)
  fre_malachite_leaf     micro-billow malachite bands (banded lens cushions)
  fre_ivory_leaf         needle-felt bone inlay (fine bone slivers)
  fre_lapis_glyphs       glyph tablet grid (10-24px cuneiform cells)
  fre_gold_glyphs        column-register glyph strips (vertical cartouches)
  fre_turquoise_glyphs   ring-pack seal impressions (stamped cylinder seals)
  fre_terracotta_glyphs  wedge-cuneiform dust field (impressed wedges)
  fre_malachite_ziggurat chevron pleats (stepped herringbone terraces)
  fre_ivory_ziggurat     stepped micro-terrace pave (tiny stepped pyramids)
  fre_lapis_ziggurat     interlocking meander cells (fret-key pack)
  fre_gold_ziggurat      dentil course lattice (rows of carved dentils)

Laws (as fractured_bloom_2026 / fractured_petri_2026 second pass): car-band
>= 0.45 each / module median >= 0.60; fineness > 6.5; coverage >= 56/64;
>= 5 hue bins; < 1.9 s at 512; descriptor pair-cosine <= 0.55. 3-4 luminous
hue anchors per id picked PER FEATURE (small hue_cell), 8-tier per-feature
brightness (_TIERS), and the _age() ply (chips + patina + tooth) on every
finish so the pave still reads aged.

Contract UNCHANGED: same 20 ids, same GROUPS key, same
install_into_engine(mono_reg, base_reg=None) -> (spec_fn, paint_fn); spec
traces paint via CategoryKit; work grid 1024, generators at 640; determinism
via np.random.default_rng + zlib.crc32(fid.encode()) — no hash(str).

Verify artifacts: _fractured_triage/refield_relic.jsonl +
_fractured_triage/resheet_relic.png.
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


def _age(res, seed, chip=0.22, tooth=0.14):
    """Antiquity ply: small dark chips/losses + fine stone tooth. Deliberately
    HIGH-frequency (chips 2-5px at the gen grid == 5-13px at 2048) so aging
    adds car-band energy instead of macro blotches."""
    s = res / _S
    sd = _sd(seed)
    _, _, cd, cid, _c = _cells(res, 9.0 * s, sd + 303, 0.95, taps=5,
                               need2=False)
    chips = _bump((cd / (1.5 * s)) ** 2) * sstep(0.55, 0.85,
                                                 h2(cid * 37.0, cid * 11.0,
                                                    sd + 7))
    grit = fbm(res, res, rng(seed, 313), 1, 300)
    return (-chips * float(chip) + (grit - 0.5) * float(tooth)).astype(np.float32)


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
# STRUCTURAL GENERATORS — 20 distinct relic-pave archetypes.
# [SPB-FRACTURED-FIELD 2026-08-02]
# ════════════════════════════════════════════════════════════════════════════

def g_chipinlay(res, seed, pitch=11.0, fine=0.11):
    """chip-inlay pave: irregular polished stone chips bedded in dark mastic,
    beveled edges, per-chip shade."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, d2 = _cells(res, p, sd, 1.0)
    mastic = sstep(2.6 * s, 0.7 * s, d2 - d1)
    bevel = sstep(4.0 * s, 1.2 * s, d2 - d1) * 0.26
    face = np.clip(1.0 - (d1 / (p * 0.85)) ** 2 * 0.5, 0.0, 1.0)
    polish = _grain(dx + 21.0, dy + 33.0, 2.4 * s, sd + 11) * 0.16
    T = (_tier(id1) * 0.50 + face * 0.24 + bevel - mastic * 0.60 + polish)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_wireinlay(res, seed, pitch=6.4, steps=4, step_px=3.0, fine=0.11):
    """thread-drift wire inlay: fine gold wires combed across a stone ground
    on a curl field, with hammer stipple."""
    s = res / _S
    sd = _sd(seed)
    _, _, d1, id1, _n = _cells(res, pitch * s, sd, 0.95, taps=5, need2=False)
    dot = _bump((d1 / (1.5 * s)) ** 2) * (0.45 + _tier(id1) * 0.55)
    pot = gauss(fbm(res, res, rng(seed, 171), 3, 7), 2.6)
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
        acc = np.maximum(acc, samp * (1.0 - 0.12 * (k + 1)))
    stone = _grain(xx, yy, 2.2 * s, sd + 5) * 0.18
    T = 0.20 + acc * 0.80 + stone
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_microdust(res, seed, fine=0.11):
    """granular micro-mosaic dust: sand-grade tesserae at two grades, no
    macro form at all — the finest pave in the module."""
    s = res / _S
    sd = _sd(seed)
    _, _, da, ida, _a = _cells(res, 4.0 * s, sd, 0.95, taps=5, need2=False)
    _, _, db, idb, _b = _cells(res, 7.2 * s, sd + 51, 0.95, taps=5, need2=False)
    ga = _bump((da / (1.15 * s)) ** 2) * (0.35 + _tier(ida) * 0.65)
    gb = _bump((db / (2.0 * s)) ** 2) * (0.35 + _tier(idb) * 0.65)
    T = 0.20 + np.maximum(ga, gb * 0.92) * 0.80
    return n01(T + _age(res, seed, chip=0.16) + _fine(res, seed, fine))


def g_strata(res, seed, pitch=5.0, warp=16.0, fine=0.11):
    """banded strata laminae: fine sediment plies with grit inclusions and
    per-lamina shade — a directional field, no big band."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 41, warp)
    q = (yy + wu * 2.2) / (pitch * s)
    lam = (1.0 - np.abs(2.0 * frac(q) - 1.0)) ** 1.5
    tier = _tier(h2(np.floor(q), np.floor(q * 0.09), sd + 9))
    grit = _grain(xx + wv, yy, 2.0 * s, sd + 13) * 0.20
    seam = sstep(0.06, 0.0, np.abs(frac(q * 0.5) - 0.5)) * 0.22
    T = 0.24 + lam * 0.42 + tier * 0.28 + grit - seam
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_tessgrid(res, seed, cell=12.0, gap=0.16, fine=0.11):
    """square tesserae grid: regular grouted tile pave, per-tile shade and
    a chipped corner nick on some tiles."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 61, 5.0)
    u = (xx + wu) / (cell * s)
    v = (yy + wv) / (cell * s)
    cu = np.floor(u)
    cv_ = np.floor(v)
    fu = np.abs(u - cu - 0.5)
    fv = np.abs(v - cv_ - 0.5)
    edge = np.maximum(fu, fv)
    tile = sstep(0.5 - gap * 0.5, 0.5 - gap, edge)
    bev = sstep(0.5 - gap, 0.5 - gap * 2.4, edge) * 0.22
    tier = _tier(h2(cu, cv_, sd + 3))
    nick = _bump(((fu - 0.42) ** 2 + (fv - 0.42) ** 2) / (0.05 ** 2))
    nick = nick * sstep(0.6, 0.85, h2(cu, cv_, sd + 17)) * 0.35
    stip = _grain(xx, yy, 2.3 * s, sd + 21) * tile * 0.16
    T = 0.20 + tile * (0.26 + tier * 0.46) + bev + stip - nick
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_shingle(res, seed, sw=12.0, rh=8.0, fine=0.11):
    """scale imbrication: shingled ivory plaques in offset rows, each with a
    ribbed grain and a lit leading edge."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 71, 6.0)
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
        rr = np.hypot(du, dv * 0.9) / (sw * s * 0.60)
        inside = sstep(1.0, 0.92, rr)
        grain = (0.5 + 0.5 * np.cos(du / (0.9 * s) + h2(cu, cv_, sd + 5) * 6.0))
        lead = sstep(1.0, 0.80, rr) * sstep(0.0, -1.4 * s, dv) * 0.22
        val = (_tier(h2(cu, cv_, sd)) * 0.48
               + np.clip(1.0 - rr, 0.0, 1.0) ** 0.8 * 0.28
               + grain * 0.16 + lead)
        T = T + val * inside * (1.0 - done)
        done = np.clip(done + inside, 0.0, 1.0)
    T = T + (1.0 - done) * 0.12
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_vermiculatum(res, seed, pitch=5.4, chip=4.2, fine=0.11):
    """opus-vermiculatum worms: curved courses of small chips following a
    warped flow — mosaic laid in worm rows."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 81, 30.0)
    q = (yy + wu * 3.0) / (pitch * s)
    ci = np.floor(q)
    v = frac(q)
    U = (xx + wv * 1.2) / (chip * s) + h2(ci, ci * 0.0, sd + 11) * 5.0
    ui = np.floor(U)
    u = frac(U)
    body = sstep(0.46, 0.30, np.hypot(u - 0.5, (v - 0.5) * (pitch / chip)))
    tier = _tier(h2(ui, ci, sd + 3))
    T = 0.22 + body * (0.28 + tier * 0.50)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_starpave(res, seed, pitch=13.0, points=8.0, fine=0.11):
    """star-lattice rosette pave: small tessellated stars with bright cores
    and dark interstices."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.20, taps=5, need2=False)
    th = np.arctan2(dy, dx)
    rr = d1 / (p * 0.68)
    prof = rr - 0.26 * np.abs(np.cos(th * points * 0.5 + id1 * _TAU)) ** 1.6
    body = sstep(0.62, 0.46, prof)
    rim = sstep(0.06, 0.0, np.abs(prof - 0.62)) * 0.24
    core = _bump((rr * 3.0) ** 2) * 0.32
    T = 0.20 + body * (0.26 + _tier(id1) * 0.46) + rim + core
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_craquelure(res, seed, pitch=10.0, fine=0.11):
    """crackle-net gilding: leaf craquelure at two scales over slightly
    domed gilded islands."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, d2 = _cells(res, p, sd, 1.0)
    crack = sstep(1.9 * s, 0.4 * s, d2 - d1)
    island = np.clip(1.0 - (d1 / (p * 0.8)) ** 2 * 0.7, 0.0, 1.0)
    # secondary craquelure on a HALF-res grid then cubic-up: it is a soft
    # hairline web, so half-res costs nothing visually and keeps this finish
    # (the heaviest in the module: two worley passes + aging) inside budget.
    h = max(res // 2, 64)
    _dx2, _dy2, d1b, _idb, d2b = _cells(h, 5.0 * (h / _S), sd + 41, 1.0, taps=5)
    crack2 = cv2.resize(sstep(1.1 * (h / _S), 0.25 * (h / _S), d2b - d1b),
                        (res, res), interpolation=cv2.INTER_CUBIC)
    burnish = _grain(dx + 7.0, dy + 19.0, 2.0 * s, sd + 9) * 0.16
    T = (_tier(id1) * 0.46 + island * 0.28 - crack * 0.50 - crack2 * 0.22
         + burnish)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_tornflake(res, seed, pitch=13.0, fine=0.11):
    """torn-flake pack: overlapping leaf flakes with ragged torn edges and
    lifted, brighter corners."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, d2 = _cells(res, p, sd, 1.0)
    rag = (fbm(res, res, rng(seed, 121), 2, 200) - 0.5) * 2.4 * s
    edge = d2 - d1 + rag
    flake = sstep(0.6 * s, 2.4 * s, edge)
    lift = sstep(2.6 * s, 0.8 * s, edge) * 0.30
    a = id1 * _TAU
    lam = np.clip((dx * np.cos(a) + dy * np.sin(a)) / np.maximum(d1, 1e-4),
                  -1.0, 1.0)
    T = (0.20 + flake * (0.26 + _tier(id1) * 0.48) + lift
         + lam * 0.12 * flake)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_bandlens(res, seed, pitch=12.0, bands=3.2, fine=0.11):
    """micro-billow malachite bands: cushioned lenses, each ringed by its own
    concentric malachite banding."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, d2 = _cells(res, p, sd, 0.85)
    rr = d1 / (p * 0.74)
    wob = (fbm(res, res, rng(seed, 131), 2, 170) - 0.5) * 0.18
    ring = 0.5 + 0.5 * np.cos((rr + wob) * bands * _TAU + id1 * 13.0)
    dome = np.clip(1.0 - rr * rr, 0.0, 1.0)
    contact = sstep(2.0 * s, 0.4 * s, d2 - d1) * 0.24
    T = _tier(id1) * 0.42 + dome * 0.22 + ring * ring * 0.44 - contact
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_slivers(res, seed, pitch=12.0, ln=8.0, fine=0.11):
    """needle-felt bone inlay: fine bone slivers in two crossed plies with
    longitudinal grain lines."""
    s = res / _S
    sd = _sd(seed)

    def ply(pi, salt, lnk, wd):
        dx, dy, _d1, id1, _ = _cells(res, pi * s, salt, 0.9, taps=5,
                                     need2=False)
        a = id1 * _TAU
        ca, sa = np.cos(a), np.sin(a)
        along = dx * ca + dy * sa
        across = np.abs(-dx * sa + dy * ca)
        L = lnk * s * (0.6 + 0.8 * h2(id1 * 31.0, id1 * 17.0, salt + 3))
        body = sstep(wd * s, wd * s * 0.3, across) * sstep(L, L * 0.82,
                                                           np.abs(along))
        grain = (0.5 + 0.5 * np.cos(across / (0.5 * s))) * body * 0.20
        return body * (0.28 + _tier(id1) * 0.48) + grain

    a1 = ply(pitch, sd, ln, 1.5)
    a2 = ply(pitch * 0.8, sd + 101, ln * 0.75, 1.2)
    T = 0.20 + np.maximum(a1, a2 * 0.9)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def _glyph_cell(res, sd, cu, cv_, du, dv, cw, ch, strokes=4):
    """Small carved glyph inside one cell: a few axis-aligned + wedge strokes
    picked per cell hash. Feature scale 10-24px at 2048 (owner's spec)."""
    g = np.zeros_like(du)
    for k in range(int(strokes)):
        hsel = h2(cu * 1.0 + k * 13.0, cv_ * 1.0 + k * 7.0, sd + 31 + k)
        hx = h2(cu + k * 3.0, cv_ - k * 5.0, sd + 61 + k)
        hy = h2(cu - k * 2.0, cv_ + k * 9.0, sd + 91 + k)
        on = sstep(0.34, 0.42, hsel)
        px = (hx - 0.5) * cw * 0.56
        py = (hy - 0.5) * ch * 0.56
        horiz = hsel > 0.66
        w = np.where(horiz, cw * 0.30, ch * 0.06)
        h = np.where(horiz, cw * 0.055, ch * 0.30)
        bar = (sstep(w, w * 0.35, np.abs(du - px))
               * sstep(h, h * 0.35, np.abs(dv - py)))
        g = np.maximum(g, bar * on)
    return g


def g_tablet(res, seed, cw=15.0, ch=13.0, fine=0.11):
    """glyph tablet grid: a whole TABLET of small carved glyph cells with
    ruled register lines (owner spec: 10-24px glyphs, never one giant)."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 91, 4.0)
    u = (xx + wu) / (cw * s)
    v = (yy + wv) / (ch * s)
    cu = np.floor(u)
    cv_ = np.floor(v)
    du = (u - cu - 0.5) * cw * s
    dv = (v - cv_ - 0.5) * ch * s
    gl = _glyph_cell(res, sd, cu, cv_, du, dv, cw * s, ch * s, 4)
    rule = sstep(0.9 * s, 0.2 * s, np.abs(dv - ch * s * 0.5)) * 0.26
    tier = _tier(h2(cu, cv_, sd + 3))
    stone = _grain(xx, yy, 2.4 * s, sd + 7) * 0.18
    T = 0.24 + gl * (0.34 + tier * 0.44) + rule + stone
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_cartouche(res, seed, colw=13.0, ch=10.0, fine=0.11):
    """column-register glyph strips: vertical cartouche columns divided by
    engraved borders, glyph cells stacked inside."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 101, 4.0)
    u = (xx + wu) / (colw * s)
    ci = np.floor(u)
    fu = u - ci - 0.5
    border = sstep(0.46, 0.40, np.abs(fu)) * 0.0 + sstep(
        0.40, 0.46, np.abs(fu)) * 0.34
    v = (yy + wv) / (ch * s) + h2(ci, ci * 0.0, sd + 11) * 3.0
    rj = np.floor(v)
    du = fu * colw * s
    dv = (v - rj - 0.5) * ch * s
    gl = _glyph_cell(res, sd, ci, rj, du, dv, colw * s * 0.72, ch * s, 3)
    tier = _tier(h2(ci, rj, sd + 5))
    T = 0.24 + gl * (0.34 + tier * 0.44) + border
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_seals(res, seed, pitch=13.0, rings=2.6, fine=0.11):
    """ring-pack seal impressions: stamped cylinder-seal discs with concentric
    ridges and a beaded rim."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, d1, id1, _ = _cells(res, p, sd, 0.65, need2=False)
    rr = d1 / (p * 0.72)
    th = np.arctan2(dy, dx)
    ring = 0.5 + 0.5 * np.cos(rr * rings * _TAU + id1 * 17.0)
    body = sstep(1.05, 0.92, rr)
    beads = sstep(0.09, 0.03, np.abs(rr - 0.82))
    beads = beads * (0.5 + 0.5 * np.cos(th * 17.0 + id1 * _TAU)) ** 2 * 0.32
    press = sstep(0.16, 0.30, rr) * 0.10
    T = (0.22 + body * (0.20 + _tier(id1) * 0.40) + ring * ring * 0.30
         + beads - press)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_wedges(res, seed, pitch=8.0, fine=0.11):
    """wedge-cuneiform dust field: impressed triangular wedges in mixed
    orientations, dense over the whole tablet."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, _d1, id1, _ = _cells(res, p, sd, 0.9, need2=False)
    a = np.floor(id1 * 4.0) * (np.pi * 0.5) + 0.35
    ca, sa = np.cos(a), np.sin(a)
    U = dx * ca + dy * sa
    V = -dx * sa + dy * ca
    wl = p * 0.40
    tri = sstep(0.0, -0.9 * s, np.abs(V) - (wl - U) * 0.42)
    tri = tri * sstep(wl, wl * 0.75, U) * sstep(-wl * 0.55, -wl * 0.30, U)
    shade = np.clip((V / (wl * 0.5)) * 0.5 + 0.5, 0.0, 1.0)
    tail = _bump(((U + wl * 0.5) ** 2 + V * V) / (1.4 * s) ** 2) * 0.26
    T = (0.24 + tri * (0.26 + _tier(id1) * 0.44) * (0.55 + 0.45 * shade)
         + tail)
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_terracepleat(res, seed, col=14.0, step=4.4, fine=0.11):
    """chevron pleats: stepped herringbone terraces — zigzag columns of
    quantized terrace steps."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 111, 7.0)
    X = xx + wu
    Y = yy + wv
    cw = col * s
    ci = np.floor(X / cw)
    u = frac(X / cw)
    sign = 1.0 - 2.0 * np.mod(ci, 2.0)
    q = Y / (step * s) + sign * u * (cw / (step * s)) * 0.9
    tread = np.floor(q)
    riser = sstep(0.12, 0.0, np.abs(frac(q) - 0.5)) * 0.30
    lip = sstep(0.10, 0.02, frac(q)) * 0.24
    tier = _tier(h2(ci, tread, sd + 3))
    seam = sstep(0.06, 0.0, np.minimum(u, 1.0 - u)) * 0.30
    T = 0.24 + tier * 0.44 + lip - riser - seam
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_microterrace(res, seed, pitch=9.5, steps=5.0, fine=0.13):
    """stepped micro-terrace pave: tiny stepped pyramids (quantized square
    distance) with lit top plates and shadowed east faces."""
    s = res / _S
    sd = _sd(seed)
    p = pitch * s
    dx, dy, _d1, id1, d2 = _cells(res, p, sd, 0.35)
    cheb = np.maximum(np.abs(dx), np.abs(dy)) / (p * 0.52)
    lvl = np.floor(np.clip(1.0 - cheb, 0.0, 1.0) * steps) / steps
    face = sstep(0.0, 0.9 * s, dx) * 0.14
    top = sstep(0.20, 0.05, cheb) * 0.20
    T = 0.22 + _tier(id1) * 0.30 + lvl * 0.46 + top - face
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_meander(res, seed, cell=15.0, fine=0.11):
    """interlocking meander cells: a Greek-key fret pack — per-cell L/T
    grooves with quadrant rotation, carved and shadowed."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 121, 4.0)
    u = (xx + wu) / (cell * s)
    v = (yy + wv) / (cell * s)
    cu = np.floor(u)
    cv_ = np.floor(v)
    du = (u - cu - 0.5)
    dv = (v - cv_ - 0.5)
    rot = np.floor(h2(cu, cv_, sd + 3) * 4.0)
    for k in (1.0, 2.0, 3.0):
        m = rot == k
        du2 = np.where(m, dv, du)
        dv2 = np.where(m, -du, dv)
        du, dv = du2, dv2
    w = 0.09
    armA = sstep(w, w * 0.4, np.abs(dv - 0.22)) * sstep(0.40, 0.34, np.abs(du))
    armB = sstep(w, w * 0.4, np.abs(du - 0.22)) * sstep(0.40, 0.34, np.abs(dv))
    armC = sstep(w, w * 0.4, np.abs(dv + 0.10)) * sstep(0.16, 0.10, np.abs(du))
    key = np.clip(armA + armB + armC, 0.0, 1.0)
    tier = _tier(h2(cu, cv_, sd + 7))
    shadow = sstep(w * 2.2, w * 1.1, np.abs(dv - 0.22)) * 0.10
    T = 0.26 + tier * 0.34 + key * 0.46 - shadow
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


def g_dentils(res, seed, rh=11.0, bw=7.0, fine=0.11):
    """dentil course lattice: rows of small carved dentil blocks separated by
    fillets, each block lit on top and shadowed below."""
    s = res / _S
    sd = _sd(seed)
    yy, xx = coords(res)
    wu, wv = warp_pair(res, seed, 131, 5.0)
    v = (yy + wv) / (rh * s)
    rj = np.floor(v)
    fv = v - rj
    u = (xx + wu) / (bw * s) + h2(rj, rj * 0.0, sd + 11) * 4.0
    ci = np.floor(u)
    fu = np.abs(u - ci - 0.5)
    block = sstep(0.40, 0.32, fu) * sstep(0.72, 0.62, np.abs(fv - 0.40))
    top = sstep(0.16, 0.06, np.abs(fv - 0.16)) * block * 0.28
    under = sstep(0.10, 0.02, np.abs(fv - 0.70)) * 0.22
    fillet = sstep(0.06, 0.0, np.abs(fv - 0.88)) * 0.18
    tier = _tier(h2(ci, rj, sd + 5))
    T = 0.24 + block * (0.26 + tier * 0.44) + top + fillet - under
    return n01(T + _age(res, seed) + _fine(res, seed, fine))


ENGINES = {
    "chipinlay": g_chipinlay, "wireinlay": g_wireinlay,
    "microdust": g_microdust, "strata": g_strata, "tessgrid": g_tessgrid,
    "shingle": g_shingle, "vermiculatum": g_vermiculatum,
    "starpave": g_starpave, "craquelure": g_craquelure,
    "tornflake": g_tornflake, "bandlens": g_bandlens, "slivers": g_slivers,
    "tablet": g_tablet, "cartouche": g_cartouche, "seals": g_seals,
    "wedges": g_wedges, "terracepleat": g_terracepleat,
    "microterrace": g_microterrace, "meander": g_meander, "dentils": g_dentils,
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
       vd=(0.78, 1.16), tmod=0.08, hspan=0.05, satboost=1.40, val=0.24,
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
# materials lapis / gold / turquoise / terracotta / malachite / ivory
# interleaved). Seeds = crc32(fid).
# Every recipe: [SPB-FRACTURED-FIELD 2026-08-02] dense-pave rebuild.
# ════════════════════════════════════════════════════════════════════════════

_RELIC = {
 # [field 2026-08-02] chip-inlay pave, lapis + gold flecks + patina
 "fre_lapis_inlay": _R("Lapis Inlay", "chipinlay",
    dict(pitch=11.0), (390.0, 940.0, 1.0, 1.26, 0.6),
    [0.62, 0.57, 0.115, 0.68], 6.0,
    "Thousands of small lapis chips bedded chip by chip in dark mastic. A FRACTURED RELIC finish."),
 # [field 2026-08-02] thread-drift wire inlay, gold over stone
 "fre_gold_inlay": _R("Gold Inlay", "wireinlay",
    dict(pitch=6.4), (405.0, 915.0, 1.0, 1.28, 2.2),
    [0.105, 0.08, 0.14, 0.45], 5.5, val=0.27,
    kw=dict(sparkle=0.30),
    desc="Fine gold wire inlay combed in drifting threads across old stone. A FRACTURED RELIC finish."),
 # [field 2026-08-02] granular micro-mosaic, turquoise sand tesserae
 "fre_turquoise_inlay": _R("Turquoise Inlay", "microdust",
    dict(), (395.0, 935.0, 1.0, 1.28, 3.5),
    [0.48, 0.53, 0.42, 0.09], 5.0,
    "Sand-grade turquoise tesserae packed grain against grain. A FRACTURED RELIC finish."),
 # [field 2026-08-02] banded strata laminae, terracotta sediment
 "fre_terracotta_inlay": _R("Terracotta Inlay", "strata",
    dict(pitch=5.0), (410.0, 910.0, 1.0, 1.26, 4.8),
    [0.035, 0.06, 0.015, 0.10], 5.5,
    "Fine terracotta strata laid ply on ply, grit caught in every lamina. A FRACTURED RELIC finish."),
 # [field 2026-08-02] square tesserae grid, malachite grouted tiles
 "fre_malachite_mosaic": _R("Malachite Mosaic", "tessgrid",
    dict(cell=12.0), (400.0, 930.0, 1.0, 1.28, 1.4),
    [0.38, 0.44, 0.32, 0.115], 6.0,
    macro=("domains", dict(cells=5, salt=3391)), vd=(0.76, 1.16),
    desc="A grouted malachite tessera grid, every tile a different green. A FRACTURED RELIC finish."),
 # [field 2026-08-02] scale imbrication, ivory plaques
 "fre_ivory_mosaic": _R("Ivory Mosaic", "shingle",
    dict(sw=12.0, rh=8.0), (400.0, 895.0, 0.95, 1.12, 3.0),
    [0.12, 0.09, 0.55, 0.30], 6.0, satboost=1.10, val=0.26,
    kw=dict(floor=0.14),
    desc="Ivory plaques shingled row over row, each one grained and lit. A FRACTURED RELIC finish."),
 # [field 2026-08-02] opus vermiculatum, lapis worm courses
 "fre_lapis_mosaic": _R("Lapis Mosaic", "vermiculatum",
    dict(pitch=5.4, chip=4.2), (390.0, 945.0, 1.0, 1.28, 5.1),
    [0.63, 0.58, 0.68, 0.115], 5.5,
    "Lapis chips laid in curving vermiculatum courses, worm row on worm row. A FRACTURED RELIC finish."),
 # [field 2026-08-02] star-lattice rosette pave, gold stars
 "fre_gold_mosaic": _R("Gold Mosaic", "starpave",
    dict(pitch=13.0, points=8.0), (405.0, 920.0, 1.0, 1.28, 0.9),
    [0.10, 0.13, 0.075, 0.52], 6.0,
    "A pave of small gold tessellated stars, dark grout between the points. A FRACTURED RELIC finish."),
 # [field 2026-08-02] crackle-net gilding, turquoise craquelure
 "fre_turquoise_leaf": _R("Turquoise Leaf", "craquelure",
    dict(pitch=10.0), (395.0, 930.0, 1.0, 1.28, 2.7),
    [0.47, 0.52, 0.42, 0.115], 6.0,
    "Turquoise gilding crazed into a fine craquelure of tiny islands. A FRACTURED RELIC finish."),
 # [field 2026-08-02] torn-flake pack, terracotta leaf
 "fre_terracotta_leaf": _R("Terracotta Leaf", "tornflake",
    dict(pitch=13.0), (410.0, 905.0, 1.0, 1.26, 4.3),
    [0.04, 0.07, 0.02, 0.30], 6.0,
    "Torn terracotta leaf flakes overlapping edge on ragged edge. A FRACTURED RELIC finish."),
 # [field 2026-08-02] micro-billow bands, malachite lenses
 "fre_malachite_leaf": _R("Malachite Leaf", "bandlens",
    dict(pitch=12.0, bands=3.2), (400.0, 930.0, 1.0, 1.28, 5.6),
    [0.39, 0.45, 0.33, 0.52], 6.0,
    "Small malachite lenses, every cushion banded in its own green rings. A FRACTURED RELIC finish."),
 # [field 2026-08-02] needle felt, ivory bone slivers
 "fre_ivory_leaf": _R("Ivory Leaf", "slivers",
    dict(pitch=12.0, ln=8.0), (400.0, 895.0, 0.95, 1.12, 1.9),
    [0.11, 0.14, 0.58, 0.08], 6.0, satboost=1.10, val=0.26,
    kw=dict(floor=0.14),
    desc="A felt of fine ivory bone slivers crossed ply over ply. A FRACTURED RELIC finish."),
 # [field 2026-08-02] glyph tablet grid, lapis cuneiform cells
 "fre_lapis_glyphs": _R("Lapis Glyphs", "tablet",
    dict(cw=15.0, ch=13.0), (390.0, 940.0, 1.0, 1.28, 3.8),
    [0.61, 0.66, 0.56, 0.115], 6.0,
    "A whole lapis tablet ruled into registers of small carved glyphs. A FRACTURED RELIC finish."),
 # [field 2026-08-02] column registers, gold cartouches
 "fre_gold_glyphs": _R("Gold Glyphs", "cartouche",
    dict(colw=13.0, ch=10.0), (405.0, 915.0, 1.0, 1.28, 5.4),
    [0.10, 0.135, 0.07, 0.44], 6.0,
    "Columns of gold cartouches, glyph cell stacked on glyph cell. A FRACTURED RELIC finish."),
 # [field 2026-08-02] seal impressions, turquoise stamps
 "fre_turquoise_glyphs": _R("Turquoise Glyphs", "seals",
    dict(pitch=13.0, rings=2.6), (395.0, 935.0, 1.0, 1.28, 1.1),
    [0.49, 0.44, 0.54, 0.10], 6.0,
    "Turquoise cylinder-seal impressions stamped rim to beaded rim. A FRACTURED RELIC finish."),
 # [field 2026-08-02] wedge cuneiform dust, terracotta tablet
 "fre_terracotta_glyphs": _R("Terracotta Glyphs", "wedges",
    dict(pitch=8.0), (410.0, 905.0, 1.0, 1.26, 2.4),
    [0.045, 0.02, 0.08, 0.115], 5.5,
    "A terracotta tablet impressed all over with tiny cuneiform wedges. A FRACTURED RELIC finish."),
 # [field 2026-08-02] chevron pleats, malachite stepped terraces
 "fre_malachite_ziggurat": _R("Malachite Ziggurat", "terracepleat",
    dict(col=14.0, step=4.4), (400.0, 930.0, 1.0, 1.28, 0.3),
    [0.40, 0.34, 0.46, 0.10], 6.0,
    "Malachite terraces pleated into stepped herringbone columns. A FRACTURED RELIC finish."),
 # [field 2026-08-02] micro terraces, ivory step pyramids
 "fre_ivory_ziggurat": _R("Ivory Ziggurat", "microterrace",
    dict(pitch=9.5, steps=5.0), (400.0, 895.0, 0.95, 1.12, 4.6),
    [0.13, 0.10, 0.56, 0.34], 6.0, satboost=1.10, val=0.26,
    kw=dict(floor=0.14),
    desc="A pave of tiny ivory step-pyramids, terrace on lit terrace. A FRACTURED RELIC finish."),
 # [field 2026-08-02] meander fret pack, lapis keys
 "fre_lapis_ziggurat": _R("Lapis Ziggurat", "meander",
    dict(cell=15.0), (390.0, 945.0, 1.0, 1.28, 2.0),
    [0.60, 0.65, 0.55, 0.13], 6.0,
    "Interlocking lapis meander keys carved cell into cell. A FRACTURED RELIC finish."),
 # [field 2026-08-02] dentil courses, gold cornice blocks
 "fre_gold_ziggurat": _R("Gold Ziggurat", "dentils",
    dict(rh=11.0, bw=7.0), (405.0, 920.0, 1.0, 1.28, 3.2),
    [0.11, 0.085, 0.145, 0.50], 6.0,
    macro=("bands", dict(angle=0.15, freq=1.2, warp=0.2)), vd=(0.76, 1.18),
    desc="Course after course of small gold dentil blocks, each one lit on top. A FRACTURED RELIC finish."),
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
    "fre_lapis_inlay": (("continents", dict(base=3, cells=3.0)), (0.84, 1.13)),
    "fre_gold_inlay": (("vortex", dict(arms=2.0, twist=7.0)), (0.84, 1.13)),
    "fre_turquoise_inlay": (("none", {}), (0.78, 1.16)),
    "fre_terracotta_inlay": (("bands", dict(angle=0.05, freq=2.0, warp=0.36)), (0.84, 1.13)),
    "fre_malachite_mosaic": (("domains", dict(cells=8, salt=3391)), (0.84, 1.13)),
    # [2c] margin is a single big radial falloff — the lowest-frequency
    # device in catlib, and this pale recipe had no band headroom for it.
    # Tight directional drift instead (distinct angle+freq from the other
    # three band ids in this module).
    # [2c] see fpe_amber_moldring: pale low-chroma recipes have no band
    # headroom for value drama — macro identity via hue zoning only.
    "fre_ivory_mosaic": (("bands", dict(angle=1.05, freq=5.5, warp=0.26)), (0.92, 1.06)),
    "fre_lapis_mosaic": (("domains", dict(cells=3, salt=3067)), (0.84, 1.13)),
    "fre_gold_mosaic": (("rings", dict(freq=6.5)), (0.84, 1.13)),
    "fre_turquoise_leaf": (("continents", dict(base=5, cells=6.0)), (0.84, 1.13)),
    "fre_terracotta_leaf": (("none", {}), (0.78, 1.16)),
    "fre_malachite_leaf": (("domains", dict(cells=14, salt=3529)), (0.84, 1.13)),
    "fre_ivory_leaf": (("rachis", dict(angle=0.8, sweep=4.5)), (0.84, 1.13)),
    "fre_lapis_glyphs": (("bands", dict(angle=1.5, freq=3.0, warp=0.18)), (0.84, 1.13)),
    "fre_gold_glyphs": (("none", {}), (0.78, 1.16)),
    "fre_turquoise_glyphs": (("vortex", dict(arms=3.0, twist=5.0, two=True)), (0.84, 1.13)),
    "fre_terracotta_glyphs": (("continents", dict(base=4, cells=2.5)), (0.84, 1.13)),
    "fre_malachite_ziggurat": (("rings", dict(freq=4.5, two=True)), (0.84, 1.13)),
    "fre_ivory_ziggurat": (("domains", dict(cells=5, salt=3701)), (0.84, 1.13)),
    "fre_lapis_ziggurat": (("none", {}), (0.78, 1.16)),
    "fre_gold_ziggurat": (("bands", dict(angle=0.15, freq=1.4, warp=0.20)), (0.84, 1.13)),
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
    _RELIC[_fid]["macro"] = _mac
    _RELIC[_fid]["vd"] = _vd
    _RELIC[_fid]["tmod"] = 0.08
    _RELIC[_fid]["hue_drift"] = 0.30 if _mac[0] == "none" else 0.95
# determinism law: per-finish seed straight from the id (no hash(str)).
for _fid, _d in _RELIC.items():
    _d["seed"] = zlib.crc32(_fid.encode()) & 0x7FFFFFFF

assert len(_RELIC) == 20

GROUPS = {
    "FRACTURED RELIC": _RELIC,
}

KIT = _FieldKit(engines=ENGINES, groups=GROUPS, tag="fractured-relic",
                # [field 2026-08-02] gen 768 -> 640: every generator
                # scales its pitch by res/_S, so the look is identical
                # while the whole module gains ~30% render headroom.
                work=1024, gen=640)

ALL = KIT.ALL
art_work_cached = KIT.art_work_cached


def install_into_engine(mono_reg, base_reg=None):
    """Registry entry point (shokker_engine_v2 install block contract)."""
    return KIT.install_into_engine(mono_reg, base_reg)
