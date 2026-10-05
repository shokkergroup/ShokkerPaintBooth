# -*- coding: utf-8 -*-
"""FRACTURED MINDS (2026-06-11) — the owner's flagship color-shift category.

50 finishes wearing the owner-discovered Ghost Fracture color-shift contract
(high metal everywhere + pattern-CARVED clearcoat + low roughness; user crushes
the base color near black -> the carved cells flash the environment: sky-teal
at one angle, sun-gold at another).

ENHANCED contract (owner feedback on the proof batch):
  * RAMPED EDGES — graded multi-band intensity flowing along every cell
    border, not a single hairline (the "color ramping edges").
  * INTERIOR FLAKES — sparse micro glints INSIDE the carved cells so color
    flashes from within perceived shapes as the car moves.
  * SLASH MARKS — short directional dashes through cells, another flash
    population at a different scale.
  * FINENESS IS A HARD GATE — features are measured (median connected-cell
    diameter at 2048) and must land 8-44 px. "Remember we are dealing with
    2048x2048 canvases. EVERY detail has to be crushed much smaller than you
    think."

Paint: near-neutral (the user's color + brightness crush does the work) with a
2-3 tone accent ghost (~10%%) that hints the flash palette per finish.
"""
import numpy as np
import cv2

from engine.expansions.redesign_wave2_2026 import (
    _rng, _noise, _n01, _sstep, _gauss, _coords, _warp, _crystal, _gray_scott,
    _flow_theta, _flowlines, _curves, _dendrites, _seed_int, _sr,
)

_WORKF = 1024
_FM_CACHE = {}


def _fm_fields(fid, h, w, s):
    key = (fid, h, w, s)
    if key in _FM_CACHE:
        return _FM_CACHE[key]
    if len(_FM_CACHE) > 6:
        _FM_CACHE.pop(next(iter(_FM_CACHE)))
    out = FM_PATTERNS[fid](h, w, s)
    if not isinstance(out, tuple):
        out = (out, None)
    pattern, vein = out
    pattern = np.clip(np.asarray(pattern, np.float32), 0, 1)
    gy, gx = np.gradient(_gauss(pattern, 1.2))
    e1 = np.clip(_n01(np.abs(gx) + np.abs(gy)) * 2.4, 0, 1)
    e2 = np.clip(_gauss(e1, 2.5) * 1.6, 0, 1)
    e3 = np.clip(_gauss(e1, 6.0) * 1.8, 0, 1)
    ramp = np.clip(e1 + (e2 - e1) * 0.6 + (e3 - e2) * 0.3, 0, 1)   # flowing graded border
    detail = _noise(h, w, s ^ 0x44, (6, 14, 32))
    micro = _noise(h, w, s ^ 0x55, (1.8, 3.6))
    flake = (_noise(h, w, s ^ 0x66, (1.5, 3.0)) > 0.80).astype(np.float32)
    # slash marks: short dashes at scattered angles (cheap: thresholded
    # directionally-stretched noise at two angles)
    rng = _rng(s, 9)
    sl = np.zeros((h, w), np.float32)
    for a in (rng.uniform(0, np.pi), rng.uniform(0, np.pi)):
        k = max(3, int(7 * _sr(h, w))) | 1
        kern = np.zeros((k, k), np.float32)
        c = k // 2
        for t in range(k):
            x = int(round(c + np.cos(a) * (t - c))); y = int(round(c + np.sin(a) * (t - c)))
            if 0 <= x < k and 0 <= y < k:
                kern[y, x] = 1.0
        kern /= max(kern.sum(), 1)
        sl = np.maximum(sl, (cv2.filter2D(_noise(h, w, s ^ int(a * 997), (1.6, 3.2)), -1, kern) > 0.62).astype(np.float32))
    vein = np.clip(np.asarray(vein, np.float32), 0, 1) if vein is not None else np.zeros((h, w), np.float32)
    out = (pattern, ramp, detail, micro, flake, sl, vein)
    _FM_CACHE[key] = out
    return out


def _make_fm(fid, base_m, base_g, tint_a, tint_b):
    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        flds = _fm_fields(fid, _WORKF, _WORKF, _seed_int(seed))
        pattern, ramp, detail, micro, flake, sl, vein = [
            cv2.resize(a, (fw, fh), interpolation=cv2.INTER_LINEAR) for a in flds]
        smf = float(sm)
        inside = _sstep(0.55, 0.8, pattern)             # the carved-cell interiors
        M = np.clip(base_m + detail * 40.0 * smf + ramp * 70.0 * smf
                    + sl * 50.0 + flake * 40.0 + vein * 60.0, 0, 255)
        G = np.clip(base_g + (1.0 - detail) * 50.0 - ramp * 20.0
                    - flake * 30.0 - vein * 16.0, 0, 255)
        B = np.clip(212.0 - pattern * 148.0 + ramp * 52.0 + micro * 14.0
                    + flake * inside * 110.0 + sl * inside * 70.0 + vein * 80.0, 16, 255)
        out = np.zeros((fh, fw, 4), np.uint8)
        mm = np.clip(m2, 0, 1)
        inv = 1.0 - mm
        out[:, :, 0] = np.clip(M * mm + 4.0 * inv, 0, 255)
        out[:, :, 1] = np.clip(G * mm + 120.0 * inv, 0, 255)
        out[:, :, 2] = np.clip(B * mm + 16.0 * inv, 0, 255)
        out[:, :, 3] = 255
        return out

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.max() > 1.5:
            src = src / 255.0
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        flds = _fm_fields(fid, _WORKF, _WORKF, _seed_int(seed))
        pattern, ramp, detail, micro, flake, sl, vein = [
            cv2.resize(a, (fw, fh), interpolation=cv2.INTER_LINEAR) for a in flds]
        strength = np.clip(m2 * float(pm), 0, 1)
        # 2-3 tone accent ghost (~10%): cells lean tint_a, borders lean tint_b —
        # hints the flash palette while the USER's color stays in charge
        ta = np.float32(tint_a); tb = np.float32(tint_b)
        ga = np.clip((pattern - 0.45) * 1.4, 0, 1) * 0.10 * strength
        gbb = np.clip(ramp * 0.12, 0, 1) * strength
        out = src * (1.0 - ga[..., None]) + ta[None, None, :] * ga[..., None]
        out = out * (1.0 - gbb[..., None]) + tb[None, None, :] * gbb[..., None]
        out = np.clip(out + (flake * 0.03 + vein * 0.04 - (1 - pattern) * 0.02)[..., None] * strength[..., None], 0, 1)
        return out.astype(np.float32)

    return spec_fn, paint_fn


# ════════════════════════════════════════════════════════ 50 PATTERN BUILDERS
# Contract: fn(h, w, s) -> pattern in [0,1] (coherent cells, features 4-22 px
# at the 1024 work grid = 8-44 px on the 2048 canvas) or (pattern, veins).

def _uv(h, w, s, warp_px=8):
    yy, xx = _coords(h, w)
    if warp_px > 0:
        return _warp(yy, xx, h, w, s, warp_px * _sr(h, w))
    return yy, xx


def _rotuv(h, w, s, warp_px=8):
    wy, wx = _uv(h, w, s, warp_px)
    a = float(_rng(s, 2).uniform(0, np.pi))
    return (wx * np.cos(a) + wy * np.sin(a), -wx * np.sin(a) + wy * np.cos(a))


def _binz(x, lo=0.46, hi=0.54):
    return _sstep(lo, hi, _n01(x))


def _linebands(lines, sr, width=2.5, lo=0.30, hi=0.62):
    """Thin line art -> flowing corridor bands. SELF-CALIBRATING: thresholds at
    fixed percentiles of the blurred field, so the carve lands ~35-40%% no
    matter how sparse or clustered the source linework is."""
    g = _gauss(np.clip(lines, 0, 1), width * sr)
    t_lo = float(np.percentile(g, 58))
    t_hi = float(np.percentile(g, 76))
    if t_hi <= t_lo:
        t_hi = t_lo + 1e-4
    return _sstep(t_lo, t_hi, g)


FM_PATTERNS = {}


def _fm(name):
    def deco(fn):
        FM_PATTERNS[name] = fn
        return fn
    return deco


# ── rebuilt six (feedback applied) ─────────────────────────────────────────
@_fm("fm_tessellate")
def _p_tess(h, w, s):
    sr = _sr(h, w)
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=5200, aniso=2.0, res=0.5)
    per = _n01(np.sin(cid * 12.99) + 1)
    veins = 1.0 - _sstep(0.02, 0.07, edge)
    return _sstep(0.48, 0.52, per), veins * 0.7


@_fm("fm_riverine")
def _p_riv(h, w, s):
    rd = _gray_scott(h, w, s, "maze", iters=440, grid=448, seeds=40, fine=0.72, speckle=0.06)
    return _sstep(0.46, 0.58, rd)


@_fm("fm_checkerflash")
def _p_check(h, w, s):
    u, v = _rotuv(h, w, s, 4)
    p = 8.0 * _sr(h, w)
    return ((np.floor(u / p) + np.floor(v / p)) % 2).astype(np.float32)


@_fm("fm_magma")
def _p_magma(h, w, s):
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=9000, aniso=1.5, res=0.5)
    per = _n01(np.sin(cid * 12.99) + 1)
    veins = np.maximum(1.0 - _sstep(0.02, 0.08, edge),
                       _dendrites(h, w, s ^ 0x77, n_roots=160, depth=5,
                                  seg=16 * _sr(h, w), thick=1))
    return _sstep(0.42, 0.50, per), veins


@_fm("fm_serpentine")
def _p_serp(h, w, s):
    u, v = _rotuv(h, w, s, 18)
    p = 7.0 * _sr(h, w)
    return _sstep(0.40, 0.60, 0.5 + 0.5 * np.sin(u * (2 * np.pi / p)))


@_fm("fm_gyro_cage")
def _p_gyro(h, w, s):
    u, v = _rotuv(h, w, s, 6)
    sr = _sr(h, w)
    g = (np.sin(u * 2 * np.pi / (17 * sr)) * np.cos(v * 2 * np.pi / (13 * sr))
         + np.sin(v * 2 * np.pi / (19 * sr)) * np.cos(u * 2 * np.pi / (11 * sr)))
    return _binz(g, 0.42, 0.58)


# ── textures the owner named ───────────────────────────────────────────────
@_fm("fm_barbed_wire")
def _p_barb(h, w, s):
    sr = _sr(h, w)
    rng = _rng(s, 7)
    polys = []
    for _ in range(int(700 * sr * sr) + 90):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        a = rng.uniform(0, 2 * np.pi)
        tt = np.linspace(0, 1, 12).astype(np.float32)
        ln = rng.uniform(40, 100) * sr
        wig = np.sin(tt * rng.uniform(6, 11)) * 2.5 * sr
        ax, ay = np.cos(a), np.sin(a)
        pts = np.stack([x + ax * ln * tt - ay * wig, y + ay * ln * tt + ax * wig], -1)
        polys.append(pts)
        for bt in np.arange(0.08, 1.0, 0.13):
            bx, by = pts[int(bt * 11), 0], pts[int(bt * 11), 1]
            for dba in (-0.5, 0.5):
                ba = a + dba + np.pi / 2
                polys.append(np.float32([[bx - np.cos(ba) * 2.6 * sr, by - np.sin(ba) * 2.6 * sr],
                                         [bx + np.cos(ba) * 2.6 * sr, by + np.sin(ba) * 2.6 * sr]]))
    wire = _curves(h, w, polys, thick=1)
    return _linebands(wire, sr, 1.8)


@_fm("fm_chainmail")
def _p_chain(h, w, s):
    u, v = _rotuv(h, w, s, 3)
    sr = _sr(h, w)
    p = 11.0 * sr
    row = np.floor(v / p)
    uo = u + (row % 2) * p * 0.5
    cu = (uo / p - np.floor(uo / p + 0.5)) * p
    cv_ = (v / p - np.floor(v / p + 0.5)) * p
    r = np.sqrt(cu * cu + cv_ * cv_)
    ring = (np.abs(r - p * 0.42) < p * 0.13).astype(np.float32)
    return ring


@_fm("fm_carbon_weave")
def _p_carbon(h, w, s):
    u, v = _rotuv(h, w, s, 2)
    p = 9.0 * _sr(h, w)
    tu = np.floor(u / p); tv = np.floor(v / p)
    twill = ((tu + tv * 2) % 4 < 2).astype(np.float32)
    sheen = 0.5 + 0.5 * np.sin((u + v * (2 * twill - 1)) * (2 * np.pi / (3.2 * _sr(h, w))))
    return np.clip(twill * 0.7 + sheen * 0.3, 0, 1)


@_fm("fm_graphene")
def _p_graphene(h, w, s):
    u, v = _rotuv(h, w, s, 2)
    sr = _sr(h, w)
    p = 7.5 * sr
    hx = u / p; hy = v / p * 1.1547
    row = np.floor(hy); hxo = hx + (row % 2) * 0.5
    du = hxo - np.floor(hxo + 0.5); dv = hy - np.floor(hy + 0.5)
    d = np.sqrt(du * du + dv * dv)
    return (d > 0.30).astype(np.float32)     # hex bonds = carved walls


@_fm("fm_lattice")
def _p_lattice(h, w, s):
    u, v = _rotuv(h, w, s, 5)
    p = 10.0 * _sr(h, w)
    bu = np.abs((u / p) - np.floor(u / p + 0.5)) * p
    bv = np.abs((v / p) - np.floor(v / p + 0.5)) * p
    bars = ((bu < 1.6 * _sr(h, w)) | (bv < 1.6 * _sr(h, w))).astype(np.float32)
    return bars


@_fm("fm_wiremesh")
def _p_mesh(h, w, s):
    u, v = _rotuv(h, w, s, 7)
    p = 6.5 * _sr(h, w)
    m1 = 0.5 + 0.5 * np.sin(u * 2 * np.pi / p)
    m2 = 0.5 + 0.5 * np.sin(v * 2 * np.pi / p)
    return _sstep(0.62, 0.8, np.maximum(m1, m2))


@_fm("fm_fiber_optic")
def _p_fiber(h, w, s):
    sr = _sr(h, w)
    rng = _rng(s, 7)
    th = _flow_theta(h, w, s, scale=100, turns=1.5, swirls=3)
    fl = _flowlines(h, w, s, n=int(7000 * sr * sr), steps=26, step_len=2.0,
                    theta=th, thick=1)
    tips = np.zeros((h, w), np.float32)
    n_t = int(2600 * sr * sr) + 200
    tx = rng.uniform(0, w - 1, n_t).astype(np.int32)
    ty = rng.uniform(0, h - 1, n_t).astype(np.int32)
    tips[ty, tx] = 1.0
    tips = np.clip(_gauss(tips, 1.4 * sr) * 6.0, 0, 1) * _sstep(0.2, 0.5, _gauss(fl, 2))
    return _linebands(fl, sr, 1.8), tips


@_fm("fm_hammered")
def _p_hammer(h, w, s):
    n = _noise(h, w, s ^ 0x88, (7, 15))
    return _sstep(0.42, 0.58, n)


@_fm("fm_hexcore")
def _p_hexcore(h, w, s):
    u, v = _rotuv(h, w, s, 3)
    sr = _sr(h, w)
    p = 8.0 * sr
    hx = u / p; hy = v / p * 1.1547
    row = np.floor(hy); hxo = hx + (row % 2) * 0.5
    du = np.abs(hxo - np.floor(hxo + 0.5)); dv = np.abs(hy - np.floor(hy + 0.5))
    cell = np.maximum(du, dv * 0.9)
    per = _n01(np.sin((np.floor(hxo + 0.5) * 31 + np.floor(hy + 0.5) * 17) * 0.731) + 1)
    return ((cell < 0.40) & (per > 0.5)).astype(np.float32)


@_fm("fm_code_cascade")
def _p_code(h, w, s):
    u, v = _rotuv(h, w, s, 2)
    sr = _sr(h, w)
    col = np.floor(u / (5.5 * sr))
    seg = np.floor(v / (4.0 * sr))
    rndv = _n01(np.sin(col * 12.99 + seg * 7.31) + 1)
    stream = _n01(np.sin(col * 3.7) + _noise(h, w, s ^ 0x91, (40, 120)))
    return ((rndv > 0.45) & (stream > 0.5)).astype(np.float32)


@_fm("fm_flame_lick")
def _p_flame1(h, w, s):
    u, v = _rotuv(h, w, s, 26)
    sr = _sr(h, w)
    tongues = 0.5 + 0.5 * np.sin(u * 2 * np.pi / (6 * sr) + np.sin(v * 2 * np.pi / (24 * sr)) * 2.2)
    taper = _noise(h, w, s ^ 0x21, (30, 80))
    return _sstep(0.55, 0.72, _n01(tongues + taper * 0.7))


@_fm("fm_flame_wall")
def _p_flame2(h, w, s):
    rd = _gray_scott(h, w, s, "worms", iters=420, grid=448, seeds=90, fine=0.6, speckle=0.16)
    u, v = _rotuv(h, w, s, 30)
    lick = 0.5 + 0.5 * np.sin(v * 2 * np.pi / (12 * _sr(h, w)))
    return _sstep(0.40, 0.54, _n01(rd + lick * 0.4))


@_fm("fm_flame_helix")
def _p_flame3(h, w, s):
    u, v = _rotuv(h, w, s, 14)
    sr = _sr(h, w)
    tw = np.sin(u * 2 * np.pi / (9 * sr) + v * 2 * np.pi / (52 * sr)) \
        + np.sin(u * 2 * np.pi / (9 * sr) - v * 2 * np.pi / (52 * sr))
    return _binz(tw, 0.44, 0.56)


@_fm("fm_sonar")
def _p_sonar(h, w, s):
    sr = _sr(h, w)
    rng = _rng(s, 3)
    yy, xx = _coords(h, w)
    acc = np.zeros((h, w), np.float32)
    for _ in range(7):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        acc += np.sin(r * 2 * np.pi / (9.5 * sr)) * np.exp(-r / (300 * sr))
    return _binz(acc, 0.45, 0.55)


@_fm("fm_tsunami")
def _p_tsu(h, w, s):
    u, v = _rotuv(h, w, s, 22)
    sr = _sr(h, w)
    crest = 0.5 + 0.5 * np.sin(u * 2 * np.pi / (7.5 * sr) + np.sin(v * 2 * np.pi / (34 * sr)) * 3.0)
    return _sstep(0.50, 0.66, crest)


@_fm("fm_sine_surge")
def _p_sine(h, w, s):
    u, v = _rotuv(h, w, s, 5)
    sr = _sr(h, w)
    g = np.sin(u * 2 * np.pi / (10 * sr)) + np.sin((u * 0.5 + v * 0.866) * 2 * np.pi / (10 * sr))
    return _binz(g, 0.46, 0.54)


@_fm("fm_ripple_rain")
def _p_ripple(h, w, s):
    sr = _sr(h, w)
    rng = _rng(s, 11)
    yy, xx = _coords(h, w)
    acc = np.zeros((h, w), np.float32)
    for _ in range(int(38 * sr * sr) + 10):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        acc += np.sin(r * 2 * np.pi / (7.5 * sr)) * np.exp(-r / (45 * sr))
    return _binz(acc, 0.46, 0.54)


@_fm("fm_honeycomb")
def _p_honey1(h, w, s):
    u, v = _rotuv(h, w, s, 3)
    sr = _sr(h, w)
    p = 13.0 * sr
    hx = u / p; hy = v / p * 1.1547
    row = np.floor(hy); hxo = hx + (row % 2) * 0.5
    du = np.abs(hxo - np.floor(hxo + 0.5)); dv = np.abs(hy - np.floor(hy + 0.5))
    cell = np.maximum(du * 1.05, du * 0.55 + dv * 0.83)      # true hex metric
    walls = ((cell > 0.34) & (cell < 0.50)).astype(np.float32)
    return np.clip(walls + (cell <= 0.20) * 0.55, 0, 1)      # walls + honey pools


@_fm("fm_honeycomb_double")
def _p_honey2(h, w, s):
    a = _p_honey1(h, w, s)
    u, v = _rotuv(h, w, s ^ 0x9, 3)
    sr = _sr(h, w)
    p = 22.0 * sr
    hx = u / p; hy = v / p * 1.1547
    row = np.floor(hy); hxo = hx + (row % 2) * 0.5
    du = np.abs(hxo - np.floor(hxo + 0.5)); dv = np.abs(hy - np.floor(hy + 0.5))
    b = (np.maximum(du, dv * 0.9) < 0.40).astype(np.float32)
    return np.clip(a * 0.7 + b * 0.3, 0, 1)


@_fm("fm_honeycomb_burst")
def _p_honey3(h, w, s):
    base = _p_honey1(h, w, s)
    sr = _sr(h, w)
    rng = _rng(s, 19)
    yy, xx = _coords(h, w)
    blast = np.zeros((h, w), np.float32)
    for _ in range(int(22 * sr * sr) + 6):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        R0 = rng.uniform(18, 44) * sr
        blast = np.maximum(blast, np.clip(1 - r / R0, 0, 1))
    crack = _dendrites(h, w, s ^ 0x77, n_roots=300, depth=4, seg=11 * sr, thick=1)
    return np.clip(np.where(blast > 0.45, 1.0 - base, base) + crack * 0.5, 0, 1)


@_fm("fm_nanoweave")
def _p_nano(h, w, s):
    u, v = _rotuv(h, w, s, 2)
    p = 4.5 * _sr(h, w)
    tu = np.floor(u / p); tv = np.floor(v / p)
    return ((tu + tv) % 2).astype(np.float32)


# ── beyond the named list: unique texture worlds ───────────────────────────
@_fm("fm_circuit_maze")
def _p_circuit(h, w, s):
    sr = _sr(h, w)
    rng = _rng(s, 13)
    polys = []
    for _ in range(int(1400 * sr * sr) + 200):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        pts = [[x, y]]
        for _k in range(int(rng.uniform(2, 5))):
            ln = rng.uniform(8, 30) * sr
            if rng.random() < 0.5:
                x = np.clip(x + rng.choice([-1, 1]) * ln, 0, w - 1)
            else:
                y = np.clip(y + rng.choice([-1, 1]) * ln, 0, h - 1)
            pts.append([x, y])
        polys.append(np.float32(pts))
    tr = _curves(h, w, polys, thick=max(1, int(1.5 * sr)))
    return _linebands(tr, _sr(h, w), 3.0)


@_fm("fm_scale_armor")
def _p_scale(h, w, s):
    u, v = _rotuv(h, w, s, 4)
    sr = _sr(h, w)
    p = 10.0 * sr
    row = np.floor(v / p)
    uo = u + (row % 2) * p * 0.5
    cu = (uo / p - np.floor(uo / p + 0.5)) * p
    cv_ = v - np.floor(v / p) * p
    r = np.sqrt(cu * cu + (cv_ - p) ** 2)
    return (r < p * 0.68).astype(np.float32)


@_fm("fm_diamond_plate")
def _p_diamond(h, w, s):
    u, v = _rotuv(h, w, s, 2)
    sr = _sr(h, w)
    p = 10.0 * sr
    lu = ((u / p) - np.floor(u / p + 0.5)) * p
    lv = ((v / p) - np.floor(v / p + 0.5)) * p
    loz = (np.abs(lu) / 1.5 + np.abs(lv)) < p * 0.34
    # 4-facet bevel: each quadrant of the stud has its own brightness
    facet = np.where(np.abs(lu) / 1.5 > np.abs(lv),
                     np.where(lu > 0, 1.0, 0.58),
                     np.where(lv > 0, 0.80, 0.32))
    edge_v = np.clip(1 - (np.abs(np.abs(lu) / 1.5 - np.abs(lv))) / (1.2 * sr), 0, 1) * loz
    return np.clip(loz * facet, 0, 1).astype(np.float32), np.clip(edge_v, 0, 1).astype(np.float32)


@_fm("fm_knurl")
def _p_knurl(h, w, s):
    u, v = _rotuv(h, w, s, 1)
    sr = _sr(h, w)
    g = np.sin((u + v) * 2 * np.pi / (5.5 * sr)) * np.sin((u - v) * 2 * np.pi / (5.5 * sr))
    return _binz(g, 0.48, 0.52)


@_fm("fm_rivet_array")
def _p_rivet(h, w, s):
    u, v = _rotuv(h, w, s, 2)
    sr = _sr(h, w)
    p = 13.0 * sr
    du = (u / p - np.floor(u / p + 0.5)) * p
    dv = (v / p - np.floor(v / p + 0.5)) * p
    r = np.sqrt(du * du + dv * dv)
    panel = ((np.abs(du) > p * 0.46) | (np.abs(dv) > p * 0.46)).astype(np.float32)
    return np.clip((r < 3.2 * sr).astype(np.float32) + panel * 0.8, 0, 1)


@_fm("fm_herringbone")
def _p_herr(h, w, s):
    u, v = _rotuv(h, w, s, 2)
    sr = _sr(h, w)
    band = np.floor(v / (5.5 * sr)) % 2
    uu = np.where(band == 0, u + v, u - v)
    return (np.floor(uu / (4.0 * sr)) % 2).astype(np.float32)


@_fm("fm_basketweave")
def _p_basket(h, w, s):
    u, v = _rotuv(h, w, s, 3)
    sr = _sr(h, w)
    p = 6.5 * sr
    tu = np.floor(u / p); tv = np.floor(v / p)
    horiz = ((tu + tv) % 2 == 0)
    s1 = 0.5 + 0.5 * np.sin(v * 2 * np.pi / (4.5 * sr))
    s2 = 0.5 + 0.5 * np.sin(u * 2 * np.pi / (4.5 * sr))
    return _sstep(0.55, 0.75, np.where(horiz, s1, s2))


@_fm("fm_chainlink")
def _p_chainlink(h, w, s):
    u, v = _rotuv(h, w, s, 5)
    sr = _sr(h, w)
    p = 12.0 * sr
    d1 = np.abs(((u + v) / p) - np.floor((u + v) / p + 0.5)) * p
    d2 = np.abs(((u - v) / p) - np.floor((u - v) / p + 0.5)) * p
    return ((d1 < 1.7 * sr) | (d2 < 1.7 * sr)).astype(np.float32)


@_fm("fm_spiderweb")
def _p_web(h, w, s):
    sr = _sr(h, w)
    rng = _rng(s, 17)
    yy, xx = _coords(h, w)
    out = np.zeros((h, w), np.float32)
    polys = []
    for _ in range(int(150 * sr * sr) + 24):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        n_sp = int(rng.uniform(7, 11))
        a0 = rng.uniform(0, 2 * np.pi)
        Rm = rng.uniform(20, 44) * sr
        for k in range(n_sp):
            a = a0 + 2 * np.pi * k / n_sp
            polys.append(np.float32([[cx, cy], [cx + np.cos(a) * Rm, cy + np.sin(a) * Rm]]))
        for rr in np.arange(0.18, 1.0, 0.16):
            aa = np.linspace(0, 2 * np.pi, 30)
            sag = 1 + 0.06 * np.sin(aa * n_sp / 2)
            polys.append(np.stack([cx + np.cos(aa) * Rm * rr * sag,
                                   cy + np.sin(aa) * Rm * rr * sag], -1))
    return _linebands(_curves(h, w, polys, thick=1), sr, 3.0)


@_fm("fm_shatter_web")
def _p_shatter(h, w, s):
    den = _dendrites(h, w, s, n_roots=900, depth=5, seg=14 * _sr(h, w), thick=1)
    return _linebands(den, _sr(h, w), 3.0)


@_fm("fm_crosshatch")
def _p_cross(h, w, s):
    u, v = _rotuv(h, w, s, 6)
    sr = _sr(h, w)
    l1 = (np.abs((u / (6 * sr)) - np.floor(u / (6 * sr) + 0.5)) < 0.16).astype(np.float32)
    l2 = (np.abs((v / (8 * sr)) - np.floor(v / (8 * sr) + 0.5)) < 0.16).astype(np.float32)
    l3 = (np.abs(((u + v) / (10 * sr)) - np.floor((u + v) / (10 * sr) + 0.5)) < 0.13).astype(np.float32)
    return np.clip(l1 + l2 + l3, 0, 1)


@_fm("fm_damascus")
def _p_dam(h, w, s):
    u, v = _rotuv(h, w, s, 40)
    sr = _sr(h, w)
    fold = np.sin(u * 2 * np.pi / (4.5 * sr) + _noise(h, w, s ^ 0x61, (40, 100)) * 9)
    return _binz(fold, 0.46, 0.54)


@_fm("fm_topo_lines")
def _p_topo(h, w, s):
    e = _noise(h, w, s ^ 0x71, (70, 170, 380))
    band = (e * 38) % 1.0
    return (band < 0.45).astype(np.float32)


@_fm("fm_labyrinth")
def _p_lab(h, w, s):
    rd = _gray_scott(h, w, s, "fingerprint", iters=460, grid=448, seeds=60, fine=0.45, speckle=0.14)
    pat = _sstep(0.46, 0.56, rd)
    gy, gx = np.gradient(_gauss(pat, 1.2))
    walls = np.clip(_n01(np.abs(gx) + np.abs(gy)) * 2.2, 0, 1)
    return pat, walls


@_fm("fm_gyroid")
def _p_gyroid(h, w, s):
    u, v = _rotuv(h, w, s, 4)
    sr = _sr(h, w)
    z = _noise(h, w, s ^ 0x81, (40, 100)) * 2 * np.pi
    g = (np.sin(u * 2 * np.pi / (9 * sr)) * np.cos(v * 2 * np.pi / (9 * sr))
         + np.sin(v * 2 * np.pi / (9 * sr)) * np.cos(z)
         + np.sin(z) * np.cos(u * 2 * np.pi / (9 * sr)))
    return _binz(g, 0.46, 0.54)


@_fm("fm_rope_coil")
def _p_rope(h, w, s):
    u, v = _rotuv(h, w, s, 10)
    sr = _sr(h, w)
    strand = 0.5 + 0.5 * np.sin((u * 0.9 + v * 0.45) * 2 * np.pi / (6 * sr))
    rope = np.floor(v / (11 * sr)) % 2
    return _sstep(0.55, 0.72, np.where(rope == 0, strand, 1 - strand))


@_fm("fm_cable_knit")
def _p_knit(h, w, s):
    u, v = _rotuv(h, w, s, 3)
    sr = _sr(h, w)
    p = 6.0 * sr
    col = np.floor(u / p)
    ph = (col % 2) * np.pi
    loop = 0.5 + 0.5 * np.sin(v * 2 * np.pi / (8 * sr) + ph) * np.cos((u / p - np.floor(u / p + 0.5)) * np.pi)
    return _sstep(0.55, 0.7, loop)


@_fm("fm_dragon_scale")
def _p_dragon(h, w, s):
    u, v = _rotuv(h, w, s, 9)
    sr = _sr(h, w)
    p = 11.0 * sr
    row = np.floor(v / (p * 0.58))
    uo = u + (row % 2) * p * 0.5
    cu = (uo / p - np.floor(uo / p + 0.5)) * p
    cv_ = v - np.floor(v / (p * 0.58)) * (p * 0.58)
    # pointed scale: diamond-tipped teardrop, crescent shadow at the overlap
    tip = np.clip(1 - (np.abs(cu) * 1.6 + np.clip(cv_ - p * 0.30, 0, None) * 1.4) / (p * 0.62), 0, 1)
    crescent = np.clip(1 - np.abs(cv_ - p * 0.12) / (2.2 * sr), 0, 1) * (np.abs(cu) < p * 0.34)
    keel = np.clip(1 - np.abs(cu) / (1.1 * sr), 0, 1) * (tip > 0.05)
    scale = _sstep(0.10, 0.45, tip)
    veins = np.clip(keel + crescent * 0.7, 0, 1)
    return np.clip(scale * 0.9 + keel * 0.2, 0, 1), veins


@_fm("fm_pin_matrix")
def _p_pin(h, w, s):
    u, v = _rotuv(h, w, s, 1)
    sr = _sr(h, w)
    p = 6.0 * sr
    du = (u / p - np.floor(u / p + 0.5)) * p
    dv = (v / p - np.floor(v / p + 0.5)) * p
    ht = _noise(h, w, s ^ 0x91, (30, 80))
    return ((np.sqrt(du * du + dv * dv) < 2.0 * sr) & (ht > 0.42)).astype(np.float32)


@_fm("fm_perforated")
def _p_perf(h, w, s):
    u, v = _rotuv(h, w, s, 1)
    sr = _sr(h, w)
    p = 7.0 * sr
    row = np.floor(v / p)
    uo = u + (row % 2) * p * 0.5
    du = (uo / p - np.floor(uo / p + 0.5)) * p
    dv = (v / p - np.floor(v / p + 0.5)) * p
    return (np.sqrt(du * du + dv * dv) > 2.4 * sr).astype(np.float32)


@_fm("fm_tread_plate")
def _p_tread(h, w, s):
    u, v = _rotuv(h, w, s, 2)
    sr = _sr(h, w)
    p = 14.0 * sr
    cell_u = np.floor(u / p); cell_v = np.floor(v / p)
    par = ((cell_u + cell_v) % 2).astype(np.float32)
    lu = (u / p - np.floor(u / p) - 0.5) * p
    lv = (v / p - np.floor(v / p) - 0.5) * p
    bar_a = (np.abs(lu + lv) < 3.4 * sr) & (np.abs(lu - lv) < p * 0.42)
    bar_b = (np.abs(lu - lv) < 3.4 * sr) & (np.abs(lu + lv) < p * 0.42)
    return np.where(par > 0.5, bar_a, bar_b).astype(np.float32)


@_fm("fm_origami")
def _p_ori(h, w, s):
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=2200, aniso=3.2, res=0.5)
    stria = 0.5 + 0.5 * np.sin(axial * 4.0)
    per = _n01(np.sin(cid * 12.99) + 1)
    return _sstep(0.48, 0.52, _n01(per + stria * 0.25))


@_fm("fm_static_burst")
def _p_static(h, w, s):
    u, v = _rotuv(h, w, s, 0)
    sr = _sr(h, w)
    seg = (_noise(h, w, s ^ 0xA1, (1.5, 3)) > 0.52).astype(np.float32)
    lines = (np.abs((v / (5.0 * sr)) - np.floor(v / (5.0 * sr) + 0.5)) < 0.3).astype(np.float32)
    return np.clip(seg * lines * 1.6, 0, 1)


# ── more unique worlds to reach 50 ─────────────────────────────────────────
@_fm("fm_voronoi_silk")
def _p_vsilk(h, w, s):
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=6500, aniso=1.3, res=0.5)
    return 1.0 - _sstep(0.05, 0.16, edge)


@_fm("fm_stitchwork")
def _p_stitch(h, w, s):
    u, v = _rotuv(h, w, s, 4)
    sr = _sr(h, w)
    pu, pv = 12.0 * sr, 7.0 * sr
    dash = (np.abs((u / pu) - np.floor(u / pu + 0.5)) < 0.34) & \
           (np.abs((v / pv) - np.floor(v / pv + 0.5)) < 0.20)
    return dash.astype(np.float32)


@_fm("fm_maze_runner")
def _p_mazer(h, w, s):
    u, v = _rotuv(h, w, s, 1)
    sr = _sr(h, w)
    p = 8.0 * sr
    cu = np.floor(u / p); cv2_ = np.floor(v / p)
    rnd = _n01(np.sin(cu * 12.99 + cv2_ * 78.23) + 1)
    d1 = np.abs(((u + v) / p) - np.floor((u + v) / p + 0.5))
    d2 = np.abs(((u - v) / p) - np.floor((u - v) / p + 0.5))
    return np.where(rnd > 0.5, (d1 < 0.30).astype(np.float32), (d2 < 0.30).astype(np.float32))


@_fm("fm_thorn_bramble")
def _p_thorn(h, w, s):
    den = _dendrites(h, w, s, n_roots=1100, depth=4, seg=11 * _sr(h, w), thick=1, spread=0.95)
    return _linebands(den, _sr(h, w), 2.8)


@_fm("fm_glass_rain")
def _p_grain(h, w, s):
    u, v = _rotuv(h, w, s, 3)
    sr = _sr(h, w)
    pu = 4.0 * sr
    col = np.floor(u / pu)
    rnd = _n01(np.sin(col * 12.99) + 1)
    seg = ((v / (30 * sr) + rnd * 7) % 1.0)
    return ((seg < 0.45) & (np.abs((u / pu) - np.floor(u / pu + 0.5)) < 0.22)).astype(np.float32)


@_fm("fm_moth_eye")
def _p_moth(h, w, s):
    u, v = _rotuv(h, w, s, 1)
    sr = _sr(h, w)
    p = 5.0 * sr
    row = np.floor(v / p)
    uo = u + (row % 2) * p * 0.5
    du = (uo / p - np.floor(uo / p + 0.5)) * p
    dv = (v / p - np.floor(v / p + 0.5)) * p
    return (np.sqrt(du * du + dv * dv) < 1.9 * sr).astype(np.float32)


@_fm("fm_tiger_slash")
def _p_tiger(h, w, s):
    u, v = _rotuv(h, w, s, 24)
    sr = _sr(h, w)
    band = np.sin(u * 2 * np.pi / (7 * sr) + _noise(h, w, s ^ 0xB1, (35, 90)) * 5)
    taper = _noise(h, w, s ^ 0xB2, (25, 70))
    return _sstep(0.58, 0.72, _n01(band + taper * 0.5))


@_fm("fm_feather_fall")
def _p_feather(h, w, s):
    sr = _sr(h, w)
    rng = _rng(s, 7)
    polys = []
    for _ in range(int(900 * sr * sr) + 100):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        a = rng.uniform(0, 2 * np.pi)
        L = rng.uniform(10, 22) * sr
        ax, ay = np.cos(a), np.sin(a)
        polys.append(np.float32([[cx - ax * L * 0.5, cy - ay * L * 0.5],
                                 [cx + ax * L * 0.5, cy + ay * L * 0.5]]))
        for bt in np.arange(-0.35, 0.45, 0.16):
            bx, by = cx + ax * L * bt, cy + ay * L * bt
            for sgn in (-1, 1):
                ba = a + sgn * 0.85
                bl = L * 0.30 * (1 - abs(bt))
                polys.append(np.float32([[bx, by],
                                         [bx + np.cos(ba) * bl, by + np.sin(ba) * bl]]))
    fe = _curves(h, w, polys, thick=1)
    return _linebands(fe, sr, 1.6)


@_fm("fm_pixel_storm")
def _p_pixel(h, w, s):
    u, v = _rotuv(h, w, s, 0)
    sr = _sr(h, w)
    p = 6.0 * sr
    cu = np.floor(u / p); cv_ = np.floor(v / p)
    rnd = _n01(np.sin(cu * 12.99 + cv_ * 78.23) + 1)
    drift = _noise(h, w, s ^ 0xC1, (60, 150))
    return (rnd > _sstep(0.2, 0.8, drift) * 0.7 + 0.15).astype(np.float32)


@_fm("fm_orbit_swarm")
def _p_orbitsw(h, w, s):
    sr = _sr(h, w)
    rng = _rng(s, 29)
    polys = []
    for _ in range(int(900 * sr * sr) + 120):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(4, 14) * sr
        a0 = rng.uniform(0, 2 * np.pi)
        aa = np.linspace(a0, a0 + rng.uniform(3.5, 6.28), 16)
        sq = rng.uniform(0.5, 1.0)
        polys.append(np.stack([cx + np.cos(aa) * r, cy + np.sin(aa) * r * sq], -1))
    return _linebands(_curves(h, w, polys, thick=1), sr, 2.4)


@_fm("fm_inferno_veins")
def _p_inferno(h, w, s):
    cid, edge, orient, axial = _crystal(h, w, s, n_sites=8000, aniso=1.8, res=0.5)
    per = _n01(np.sin(cid * 12.99) + 1)
    cracks = 1.0 - _sstep(0.02, 0.07, edge)
    veins = _dendrites(h, w, s ^ 0x99, n_roots=600, depth=5, seg=11 * _sr(h, w), thick=1)
    return _sstep(0.45, 0.55, per), np.clip(cracks + veins, 0, 1)


@_fm("fm_frost_feather")
def _p_frost(h, w, s):
    den = _dendrites(h, w, s, n_roots=1500, depth=5, seg=10 * _sr(h, w), thick=1, spread=0.5)
    return _linebands(den, _sr(h, w), 1.8)


# ════════════════════════════════════════════════════════ DEFS + INSTALL
# (mode-free: every id has its own pattern builder above)
_T = {
    "teal":  ((0.45, 0.85, 0.90), (1.00, 0.85, 0.55)),
    "mag":   ((0.95, 0.45, 0.80), (0.55, 0.90, 0.95)),
    "gold":  ((0.95, 0.80, 0.45), (0.50, 0.75, 0.95)),
    "ice":   ((0.70, 0.88, 1.00), (0.95, 0.70, 0.80)),
    "lime":  ((0.65, 0.95, 0.55), (0.90, 0.60, 0.95)),
    "ember": ((1.00, 0.60, 0.35), (0.45, 0.80, 0.95)),
}
_TK = list(_T)

_FM_DROPPED = {  # trimmed to exactly 50 (owner's number) — weakest/duplicative cut
    "fm_spiderweb", "fm_moth_eye", "fm_honeycomb_double", "fm_pixel_storm",
    "fm_maze_runner", "fm_knurl", "fm_sine_surge", "fm_glass_rain",
    "fm_stitchwork", "fm_ripple_rain", "fm_hammered", "fm_crosshatch",
}

FRACTURED_MINDS_DEFS = {}
for _i, _fid in enumerate(sorted(k for k in FM_PATTERNS if k not in _FM_DROPPED)):
    _bm = 170 + (_i * 7) % 26            # 170-195 sweet spot sweep
    _bg = 60 + (_i * 5) % 26             # 60-85
    _ta, _tb = _T[_TK[_i % len(_TK)]]
    FRACTURED_MINDS_DEFS[_fid] = (_bm, _bg, _ta, _tb)




# ════════════════════════════════════════════════ v2: LAYERED SPEC SYSTEM
# Owner (2026-06-11): "MUCH more spec diversity... think of it as layering in
# the spec channel... gradients throughout... where's the blue/purple?"
#
# THE BLUE INSIGHT: in the spec view (R=metal, G=rough, B=clearcoat), metal-
# high-everywhere renders every CC peak MAGENTA. Pure BLUE needs metal to DIP
# where clearcoat peaks — and physically that's the HARDEST environment flash
# (dielectric mirror, zero paint tint). So v2 styles deliberately carve metal
# DOWN in chosen CC zones: blue presence + a third flash personality.
#
# Layer vocabulary (each returns dM, dG, dB contributions at 1024):
#   _ly_streaks   flow ribbons through the spec (any channel mix)
#   _ly_halo      ramped multi-band aura hugging the pattern borders
#   _ly_cellrole  per-cell channel ROLE assignment (M-heavy / B-heavy / G-art)
#   _ly_grad      large smooth gradients modulating layer amplitude across
#                 the whole canvas ("gradients throughout the spec")
#   _ly_flakepop  flake populations targeted at channel combos (yellow = M+G,
#                 blue = B alone, white = M+B+G...)
#   _ly_corering  per-cell radial core (deep interior -> hottest)
#   _ly_counter   a SECOND geometry living only in the spec

def _ly_grad(h, w, s, k=2):
    """k large smooth direction gradients, each 0..1."""
    rng = _rng(s, 31)
    yy, xx = _coords(h, w)
    outs = []
    for i in range(k):
        a = rng.uniform(0, 2 * np.pi)
        g = _n01((xx * np.cos(a) + yy * np.sin(a)) +
                 _noise(h, w, s ^ (0x100 + i), (300, 700)) * 0.6 * max(h, w))
        outs.append(g.astype(np.float32))
    return outs


def _ly_streaks(h, w, s, n=1600, steps=34, thick=1, scale=140, turns=1.4):
    th = _flow_theta(h, w, s ^ 0x214, scale=scale, turns=turns)
    fl = _flowlines(h, w, s ^ 0x215, n=int(n * _sr(h, w) ** 2), steps=steps,
                    step_len=2.2, theta=th, thick=thick, fade=True)
    return np.clip(fl * 1.5, 0, 1)


def _ly_corering(pattern, depth_px=6.0):
    """Per-cell interior depth 0..1 (1 = deep core) via distance transform."""
    binp = (pattern > 0.5).astype(np.uint8)
    dt_ = cv2.distanceTransform(binp, cv2.DIST_L2, 3)
    return np.clip(dt_ / max(depth_px, 1.0), 0, 1).astype(np.float32)


def _ly_cellrole(h, w, s, pattern, n_roles=3):
    """Stable per-cell role id 0..n-1 (connected-component hash)."""
    binp = (pattern > 0.5).astype(np.uint8)
    n, lab = cv2.connectedComponents(binp, 8)
    rng = _rng(s, 37)
    lut = rng.integers(0, n_roles, max(n, 1)).astype(np.float32)
    return lut[lab] * binp


# ── style recipes: name -> fn(fields, s) -> (M, G, B) at 1024 ──────────────
def _phys_floor(M, G, B):
    """The proven color-shift physics floor: strong carved CC contrast, low-mid
    rough, metal HIGH on average but ALLOWED to dip (that's where blue lives)."""
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(G, 16, 200).astype(np.float32),
            np.clip(B, 16, 255).astype(np.float32))


def _style_violet_halo(F, s, h, w):
    """Hot purple streak-halos around the pattern, yellow flakes inside, blue
    pools in the cell cores — the owner's exact ask."""
    pattern, ramp, detail, micro, flake, sl, vein = F
    core = np.clip(_gauss(pattern, 2.0) * 1.3, 0, 1)
    g1, g2 = _ly_grad(h, w, s, 2)
    M = 135 + 70 * detail - 145 * core * g1 + 55 * ramp          # cell dips -> blue
    G = 55 + 60 * (1 - detail) + 95 * flake * pattern            # yellow flakes (M+G)
    B = 70 + 150 * ramp * (0.5 + 0.5 * g2) + 175 * core + 90 * flake * pattern + 40 * sl
    M = M + 55 * ramp                                            # purple halo = M+B on ramp
    return _phys_floor(M, G, B)


def _style_dual_gradient(F, s, h, w):
    """Two opposing macro gradients sweep the spec: pink->purple->blue travel
    across the whole car."""
    pattern, ramp, detail, micro, flake, sl, vein = F
    g1, g2 = _ly_grad(h, w, s, 2)
    M = 120 + 110 * g1 - 150 * g2 * pattern + 50 * ramp + 40 * sl
    G = 50 + 55 * (1 - detail) + 70 * flake
    B = 60 + 170 * g2 * pattern + 70 * ramp * g1 + 100 * flake * (1 - g1)
    return _phys_floor(M, G, B)


def _style_counter_weave(F, s, h, w):
    """A second geometry lives ONLY in the spec: diagonal ribbon lattice crossing
    the paint pattern — two designs revealed at different angles."""
    pattern, ramp, detail, micro, flake, sl, vein = F
    u, v = _rotuv(h, w, s ^ 0x99, 8)
    p2 = 11.0 * _sr(h, w)
    counter = _sstep(0.42, 0.58, 0.5 + 0.5 * np.sin(u * (2 * np.pi / p2)))
    M = 165 + 60 * detail - 120 * counter * (1 - pattern) + 60 * ramp
    G = 55 + 50 * (1 - detail) + 80 * flake * counter
    B = 75 + 145 * counter + 95 * (1 - pattern) * ramp + 85 * flake
    return _phys_floor(M, G, B)


def _style_ember_core(F, s, h, w):
    """Blue-hot cell cores with pink rims, gold flake dust between cells."""
    pattern, ramp, detail, micro, flake, sl, vein = F
    core = np.clip(_gauss(pattern, 1.8) * 1.4 - 0.25, 0, 1)
    g1 = _ly_grad(h, w, s, 1)[0]
    M = 185 + 55 * ramp - 175 * core + 30 * detail
    G = 50 + 95 * flake * (1 - pattern) + 45 * (1 - detail)
    B = 60 + 205 * core + 70 * ramp * g1 + 110 * flake * (1 - pattern)
    return _phys_floor(M, G, B)


def _style_ribbon_storm(F, s, h, w):
    """Blue flow-rivers cut through pink metal; shadow ribbons interleave."""
    pattern, ramp, detail, micro, flake, sl, vein = F
    rib1 = _ly_streaks(h, w, s, n=2000, steps=40, thick=2)
    rib2 = _ly_streaks(h, w, s ^ 0x33, n=1400, steps=30, thick=1)
    M = 190 + 40 * detail - 160 * rib1 + 40 * ramp
    G = 60 + 60 * rib2 + 60 * flake
    B = 80 + 165 * rib1 + 70 * ramp + 70 * flake * pattern + 35 * sl
    return _phys_floor(M, G, B)


def _style_split_spectrum(F, s, h, w):
    """Per-cell roles: a third of the cells go BLUE (metal dip + CC max), a third
    PINK (metal max), a third GOLD-textured (rough art) — tri-color patchwork."""
    pattern, ramp, detail, micro, flake, sl, vein = F
    role = _ly_cellrole(h, w, s, pattern, 3)
    r0 = (role == 0) * pattern; r1 = (role == 1) * pattern; r2 = (role == 2) * pattern
    M = 95 + 140 * r1 + 60 * ramp - 70 * r0 + 60 * detail * (1 - pattern)
    G = 45 + 110 * r2 * detail + 70 * flake * r2
    B = 60 + 180 * r0 + 80 * ramp + 90 * flake * r1 + 30 * micro
    return _phys_floor(M, G, B)


def _style_pulse_rings(F, s, h, w):
    """Sonar-like macro intensity rings pulse the whole spec's amplitude."""
    pattern, ramp, detail, micro, flake, sl, vein = F
    rng = _rng(s, 41)
    yy, xx = _coords(h, w)
    cx, cy = rng.uniform(0, w), rng.uniform(0, h)
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    pulse = (0.5 + 0.5 * np.sin(r * 2 * np.pi / (210 * _sr(h, w)))).astype(np.float32)
    M = 130 + 90 * pulse - 90 * pattern * (1 - pulse) + 65 * ramp
    G = 55 + 55 * (1 - detail) + 75 * flake * pulse
    B = 60 + 160 * pattern * (0.35 + 0.65 * (1 - pulse)) + 75 * ramp + 80 * flake
    return _phys_floor(M, G, B)


def _style_acid_etch(F, s, h, w):
    """The G channel becomes its own etched art (adds the green/gold dimension)
    over a deep blue-carved base."""
    pattern, ramp, detail, micro, flake, sl, vein = F
    etch = _sstep(0.5, 0.62, _noise(h, w, s ^ 0x51, (4, 9, 20)))
    M = 175 + 50 * ramp - 120 * pattern * (1 - detail)
    G = 40 + 130 * etch * (1 - pattern) + 60 * flake
    B = 70 + 160 * pattern + 80 * ramp + 60 * sl
    return _phys_floor(M, G, B)


def _style_vein_surge(F, s, h, w):
    """Electric vein networks near-max CC with purple ramps; spark flakes."""
    pattern, ramp, detail, micro, flake, sl, vein = F
    vv = vein if vein.max() > 0.05 else _dendrites(h, w, s ^ 0x61, n_roots=700, depth=4,
                                                   seg=12 * _sr(h, w), thick=1)
    vglow = np.clip(_gauss(vv, 3) * 2.0, 0, 1)
    g1 = _ly_grad(h, w, s, 1)[0]
    M = 165 + 55 * detail - 175 * vglow + 30 * ramp
    G = 55 + 55 * (1 - detail) + 80 * flake * pattern
    B = 65 + 200 * vv + 130 * vglow * g1 + 85 * flake * pattern
    return _phys_floor(M, G, B)


def _style_tide_shift(F, s, h, w):
    """A macro diagonal gradient CROSSFADES two personalities: carve-dominant on
    one side of the car, streak-dominant on the other."""
    pattern, ramp, detail, micro, flake, sl, vein = F
    g1 = _ly_grad(h, w, s, 1)[0]
    rib = _ly_streaks(h, w, s ^ 0x71, n=1700, steps=36)
    Ma = 190 + 40 * detail - 120 * pattern; Ba = 70 + 175 * pattern + 70 * ramp
    Mb = 200 - 150 * rib; Bb = 75 + 175 * rib + 60 * flake
    M = Ma * (1 - g1) + Mb * g1
    G = 50 + 60 * (1 - detail) + 70 * flake * g1
    B = Ba * (1 - g1) + Bb * g1 + 60 * flake
    return _phys_floor(M, G, B)


_FM_STYLES = {
    "violet_halo": _style_violet_halo, "dual_gradient": _style_dual_gradient,
    "counter_weave": _style_counter_weave, "ember_core": _style_ember_core,
    "ribbon_storm": _style_ribbon_storm, "split_spectrum": _style_split_spectrum,
    "pulse_rings": _style_pulse_rings, "acid_etch": _style_acid_etch,
    "vein_surge": _style_vein_surge, "tide_shift": _style_tide_shift,
}

# owner keeps (frozen — legacy contract + ghost paint stay exactly as rated)
_FM_KEEP = {"fm_chainlink", "fm_chainmail", "fm_checkerflash", "fm_circuit_maze",
            "fm_code_cascade", "fm_damascus", "fm_flame_lick", "fm_graphene",
            "fm_gyro_cage", "fm_gyroid", "fm_hexcore"}

# style + wild-paint palette per non-keep finish (assigned for max variety)
_FM_V2 = {}
_V2_STYLE_KEYS = list(_FM_STYLES)
_V2_PALETTES = [
    ((0.55, 0.10, 0.85), (0.10, 0.45, 0.95), (1.00, 0.85, 0.25)),   # violet/blue/gold
    ((0.95, 0.15, 0.45), (0.15, 0.85, 0.85), (0.95, 0.95, 0.95)),   # punch pink/teal/white
    ((0.10, 0.90, 0.45), (0.60, 0.15, 0.95), (1.00, 0.55, 0.10)),   # acid green/purple/orange
    ((0.95, 0.75, 0.15), (0.20, 0.30, 0.95), (0.90, 0.10, 0.30)),   # gold/cobalt/crimson
    ((0.15, 0.95, 0.90), (0.95, 0.30, 0.80), (0.45, 0.95, 0.30)),   # cyan/magenta/lime
    ((1.00, 0.40, 0.05), (0.05, 0.55, 1.00), (0.85, 0.85, 0.90)),   # flame orange/electric blue/silver
]


def _fm_v2_paint(fid, style_key, pal):
    """Wild 2-3 color paint that still respects the crush ritual: tints scale
    with the source's brightness, so dragging the color dark kills the paint to
    black while mid-brightness shows the full multi-color art."""
    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.max() > 1.5:
            src = src / 255.0
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        flds = _fm_fields(fid, _WORKF, _WORKF, _seed_int(seed))
        pattern, ramp, detail, micro, flake, sl, vein = [
            cv2.resize(a, (fw, fh), interpolation=cv2.INTER_LINEAR) for a in flds]
        strength = np.clip(m2 * float(pm), 0, 1)
        lum = np.clip(src.mean(2, keepdims=True) * 2.2, 0, 1)
        c1, c2, c3 = (np.float32(pal[0]), np.float32(pal[1]), np.float32(pal[2]))
        art = (c1[None, None, :] * pattern[..., None]
               + c2[None, None, :] * (ramp * 1.2)[..., None]
               + c3[None, None, :] * (flake * pattern + sl * 0.5)[..., None])
        art = np.clip(art, 0, 1) * lum
        k = (0.50 * strength * np.clip(pattern + ramp + flake, 0, 1))[..., None]
        out = np.clip(src * (1.0 - k) + art * k, 0, 1)
        return out.astype(np.float32)
    return paint_fn


def _fm_v2_spec(fid, style_key):
    style = _FM_STYLES[style_key]

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        F = _fm_fields(fid, _WORKF, _WORKF, _seed_int(seed))
        M, G, B = style(F, _seed_int(seed), _WORKF, _WORKF)
        smf = float(sm)
        if abs(smf - 1.0) > 0.01:   # damped, never clipping (x2-aware)
            M = np.clip(128 + (M - 128) * (1 + (min(smf, 2.0) - 1) * 0.42), 0, 255)
        M, G, B = [cv2.resize(a, (fw, fh), interpolation=cv2.INTER_LINEAR) for a in (M, G, B)]
        out = np.zeros((fh, fw, 4), np.uint8)
        mm = np.clip(m2, 0, 1)
        inv = 1.0 - mm
        out[:, :, 0] = np.clip(M * mm + 4.0 * inv, 0, 255)
        out[:, :, 1] = np.clip(G * mm + 120.0 * inv, 0, 255)
        out[:, :, 2] = np.clip(B * mm + 16.0 * inv, 0, 255)
        out[:, :, 3] = 255
        return out
    return spec_fn


def _fm_v2_assign():
    """Deterministic diverse style/palette assignment across non-keep ids."""
    ids = sorted(k for k in FRACTURED_MINDS_DEFS if k not in _FM_KEEP)
    for i, fid in enumerate(ids):
        _FM_V2[fid] = (_V2_STYLE_KEYS[i % len(_V2_STYLE_KEYS)],
                       _V2_PALETTES[(i // len(_V2_STYLE_KEYS) + i) % len(_V2_PALETTES)])


_fm_v2_assign()


def install_into_engine(mono_reg, base_reg=None):
    entries = {}
    for fid, (bm, bg, ta, tb) in FRACTURED_MINDS_DEFS.items():
        if fid in _FM_V2:   # v2: layered spec style + wild crush-aware paint
            style_key, pal = _FM_V2[fid]
            entries[fid] = (_fm_v2_spec(fid, style_key), _fm_v2_paint(fid, style_key, pal))
        else:               # owner keeps: frozen as rated
            entries[fid] = _make_fm(fid, bm, bg, ta, tb)
        mono_reg[fid] = entries[fid]
    # retire the ghost_shift proof six (superseded by FRACTURED MINDS)
    for old in ("ghost_shift_tessellate", "ghost_shift_riverine", "ghost_shift_weave",
                "ghost_shift_magma", "ghost_shift_serpentine", "ghost_shift_orbital"):
        mono_reg.pop(old, None)
    try:
        import engine.expansions.fusions as _fus
        _fus.FUSION_REGISTRY.update(entries)
        for old in ("ghost_shift_tessellate", "ghost_shift_riverine", "ghost_shift_weave",
                    "ghost_shift_magma", "ghost_shift_serpentine", "ghost_shift_orbital"):
            _fus.FUSION_REGISTRY.pop(old, None)
    except Exception:
        pass
    return "fractured-minds: %d flagship color-shift finishes registered" % len(entries)
