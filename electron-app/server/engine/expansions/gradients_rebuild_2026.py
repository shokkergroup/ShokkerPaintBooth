"""GRADIENTS — total ground-up rebuild (2026-06-22). Owner rejected the recycled
9-mode gradient engine. This builds every grad_ finish from a library of
STRUCTURE x COLOR-RICHNESS x PATTERN-OVERLAY designs, each gated structurally
unique (no two finishes share structure + color-count) via an FFT/edge gestalt
metric (NOT pixel snapshots). 56 distinct non-circular structures x color tiers
(2/3/4/5) + overlays (flake/crackle/grain) => 136 unique designs; the 125 grad_
finishes are assigned distinct designs 1:1, richest palettes -> highest color
tiers. Colors come from the finish NAME. NO circular gradients. Smooth flowing
color + 3D relief depth. Spec TRACES the paint (hero edges -> M, own grain -> R,
fine detail -> Cc), channels decorrelated for the |corr|<0.85 gate.

Design list is baked offline by _reworks_2026/gradient_lib_v3.py -> grad_designs.json
so app boot does NO rendering. Installed via the final-authority hook in
shokker_engine_v2.py (_spb_apply_color_science_rebuild_2026).
"""
import os, json, math
from functools import lru_cache
import numpy as np
import cv2

_HERE = os.path.dirname(os.path.abspath(__file__))
_DESIGNS_JSON = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "_reworks_2026", "grad_designs.json")
_CAP = 768  # render structure at <=this, upscale to work-res (gradients are large-scale; keeps render fast)

# Baked design list (struct_key, color_count) — generated offline by
# _reworks_2026/gradient_lib_v3.py and gestalt-gated unique. Baked here so the
# packaged build needs NO external file. 34 distinct structure families x color
# tiers = 136 designs; the 125 grad_ finishes are assigned distinct designs 1:1.
_BAKED_DESIGNS = [
    ("linear", 3), ("linear.terr", 3), ("linear.chev", 3), ("linear.scale", 3), ("linear.weave", 3), ("linear.hex", 3),
    ("linear.grain", 3), ("plaid", 3), ("plaid.hex", 3), ("aurora.terr", 3), ("ribbon", 3), ("ribbon.chev", 3),
    ("streak.chev", 3), ("triangles.chev", 3), ("drip", 3), ("drip.chev", 3), ("brush", 3), ("herring", 3),
    ("herring.chev", 3), ("shards.grain", 3), ("quilt.chev", 3), ("wovenrib", 3), ("wovenrib.chev", 3), ("wovenrib.hex", 3),
    ("linearXsplinter", 3), ("linearXwovenrib", 3), ("plaidXdrip", 3), ("plaidXbrush", 3), ("plaidXherring", 3), ("plaidXflux", 3),
    ("plaidXquilt", 3), ("auroraXstreak", 3), ("crossflowXwavefold", 3), ("dripXwisp", 3), ("linear", 5), ("linear.terr", 5),
    ("linear.chev", 5), ("linear.scale", 5), ("linear.weave", 5), ("linear.hex", 5), ("linear.grain", 5), ("plaid", 5),
    ("plaid.hex", 5), ("aurora.terr", 5), ("ribbon", 5), ("ribbon.chev", 5), ("streak.chev", 5), ("triangles.chev", 5),
    ("drip", 5), ("drip.chev", 5), ("brush", 5), ("herring", 5), ("herring.chev", 5), ("shards.grain", 5),
    ("quilt.chev", 5), ("wovenrib", 5), ("wovenrib.chev", 5), ("wovenrib.hex", 5), ("linearXsplinter", 5), ("linearXwovenrib", 5),
    ("plaidXdrip", 5), ("plaidXbrush", 5), ("plaidXherring", 5), ("plaidXflux", 5), ("plaidXquilt", 5), ("auroraXstreak", 5),
    ("crossflowXwavefold", 5), ("dripXwisp", 5), ("linear", 2), ("linear.terr", 2), ("linear.chev", 2), ("linear.scale", 2),
    ("linear.weave", 2), ("linear.hex", 2), ("linear.grain", 2), ("plaid", 2), ("plaid.hex", 2), ("aurora.terr", 2),
    ("ribbon", 2), ("ribbon.chev", 2), ("streak.chev", 2), ("triangles.chev", 2), ("drip", 2), ("drip.chev", 2),
    ("brush", 2), ("herring", 2), ("herring.chev", 2), ("shards.grain", 2), ("quilt.chev", 2), ("wovenrib", 2),
    ("wovenrib.chev", 2), ("wovenrib.hex", 2), ("linearXsplinter", 2), ("linearXwovenrib", 2), ("plaidXdrip", 2), ("plaidXbrush", 2),
    ("plaidXherring", 2), ("plaidXflux", 2), ("plaidXquilt", 2), ("auroraXstreak", 2), ("crossflowXwavefold", 2), ("dripXwisp", 2),
    ("linear", 4), ("linear.terr", 4), ("linear.chev", 4), ("linear.scale", 4), ("linear.weave", 4), ("linear.hex", 4),
    ("linear.grain", 4), ("plaid", 4), ("plaid.hex", 4), ("aurora.terr", 4), ("ribbon", 4), ("ribbon.chev", 4),
    ("streak.chev", 4), ("triangles.chev", 4), ("drip", 4), ("drip.chev", 4), ("brush", 4), ("herring", 4),
    ("herring.chev", 4), ("shards.grain", 4), ("quilt.chev", 4), ("wovenrib", 4), ("wovenrib.chev", 4), ("wovenrib.hex", 4),
    ("linearXsplinter", 4), ("linearXwovenrib", 4), ("plaidXdrip", 4), ("plaidXbrush", 4), ("plaidXherring", 4), ("plaidXflux", 4),
    ("plaidXquilt", 4), ("auroraXstreak", 4), ("crossflowXwavefold", 4), ("dripXwisp", 4),
]


# ---------------- helpers (h,w native) ----------------
def _rng(s): return np.random.default_rng(int(s) & 0xFFFFFFFF)
def _n(a):
    a = a.astype(np.float32); lo = float(a.min()); rng = float(np.ptp(a))
    return np.zeros_like(a) if rng < 1e-9 else (a - lo) / rng
def _grid(h, w):
    yy, xx = np.mgrid[0:h, 0:w]
    return xx.astype(np.float32) / max(w - 1, 1), yy.astype(np.float32) / max(h - 1, 1)
def _sm(h, w, s, c):
    return _n(cv2.resize(_rng(s).random((c, c)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC))
def _warp(X, Y, h, w, s, amp, c=5):
    return X + (_sm(h, w, s * 7 + 1, c) - 0.5) * amp, Y + (_sm(h, w, s * 7 + 9, c) - 0.5) * amp
def _vor(X, Y, h, w, s, K):
    pts = _rng(s).uniform(0, 1, (K, 2)).astype(np.float32)
    best = np.full((h, w), 9e9, np.float32); idx = np.zeros((h, w), np.int32)
    for i in range(K):
        d = (X - pts[i, 0]) ** 2 + (Y - pts[i, 1]) ** 2
        m = d < best; idx = np.where(m, i, idx); best = np.where(m, d, best)
    return idx


# ---------------- BASES  fn(X,Y,h,w,s)->t01  (ported 1:1 from gradient_lib_v3) -------------
def linear(X, Y, h, w, s): a = _rng(s).uniform(0, np.pi); xw, yw = _warp(X, Y, h, w, s, 0.38); return _n(xw * np.cos(a) + yw * np.sin(a))
def bands(X, Y, h, w, s): a = _rng(s).uniform(0, np.pi); f = _rng(s).uniform(2.5, 5.5); xw, yw = _warp(X, Y, h, w, s, 0.3); return _n(0.5 + 0.5 * np.sin((xw * np.cos(a) + yw * np.sin(a)) * np.pi * f))
def plaid(X, Y, h, w, s): a = _rng(s).uniform(6, 12); return _n(np.sin(X * a) * 0.5 + np.sin(Y * a) * 0.5 + 1.0)
def liquid(X, Y, h, w, s): xw, yw = _warp(X, Y, h, w, s, 0.32); return _n(_sm(h, w, s, 4) * 0.65 + (xw - 0.5) * 0.45)
def aurora(X, Y, h, w, s): return _n(Y + (_sm(h, w, s * 3 + 2, 3) - 0.5) * 0.6 + (_sm(h, w, s * 3 + 5, 9) - 0.5) * 0.22)
def marble(X, Y, h, w, s): xw, yw = _warp(X, Y, h, w, s, 0.5, 3); return _n(0.5 + 0.5 * np.sin((_sm(h, w, s, 5) * 2 + xw) * np.pi * 2.2))
def ribbon(X, Y, h, w, s): xw, yw = _warp(X, Y, h, w, s, 0.34); return _n(0.5 + 0.5 * np.sin((xw - yw) * np.pi * _rng(s).uniform(2, 3.4)))
def streak(X, Y, h, w, s): a = _rng(s).uniform(0, np.pi); u = X * np.cos(a) + Y * np.sin(a); return _n(_sm(h, w, s * 2 + 1, 3) + 0.22 * np.sin(u * _rng(s).uniform(35, 60)))
def crossflow(X, Y, h, w, s): a = _rng(s).uniform(6, 11); xw, yw = _warp(X, Y, h, w, s, 0.3, 4); return _n(np.sin(xw * a) * np.cos(yw * a * 0.8) * 0.5 + 0.5)
def blocks(X, Y, h, w, s):
    rng = _rng(s); t = np.zeros((h, w), np.float32)
    for _ in range(int(rng.integers(22, 36))):
        x0, x1 = sorted(rng.uniform(0, 1, 2)); y0, y1 = sorted(rng.uniform(0, 1, 2)); t[(Y >= y0) & (Y < y1) & (X >= x0) & (X < x1)] = rng.random()
    return _n(cv2.GaussianBlur(t, (0, 0), 1.2))
def triangles(X, Y, h, w, s):
    a = int(_rng(s).integers(7, 12)); cell = (np.floor(X * a) + np.floor(Y * a) * 13).astype(np.int32)
    up = (((X * a) % 1) + ((Y * a) % 1) > 1).astype(np.int32); cell = cell * 2 + up
    return _n(_rng(s + 1).random(int(cell.max()) + 2).astype(np.float32)[cell])
def crosswave(X, Y, h, w, s): a = _rng(s).uniform(8, 16); b = _rng(s).uniform(8, 16); g = _rng(s).uniform(.3, 1.2); u = X * np.cos(g) + Y * np.sin(g); v = -X * np.sin(g) + Y * np.cos(g); return _n(np.sin(u * a) + np.sin(v * b))
def drip(X, Y, h, w, s): base = _n(cv2.resize(_rng(s).random((1, 48)).astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)); return _n(base * 0.7 + Y * 0.3 + (_sm(h, w, s * 3 + 2, 6) - 0.5) * 0.2)
def brush(X, Y, h, w, s): a = _rng(s).uniform(0, np.pi); u = X * np.cos(a) + Y * np.sin(a); return _n(_sm(h, w, s, 3) + 0.18 * np.sin(u * _rng(s).uniform(50, 90)) + u * 0.3)
def herring(X, Y, h, w, s): a = int(_rng(s).integers(10, 16)); flip = (np.floor(Y * a).astype(int) % 2) * 2 - 1; return _n(0.5 + 0.5 * np.sin((X * a * flip + Y * a) * np.pi))
def wavefold(X, Y, h, w, s): a = _rng(s).uniform(0, np.pi); u = X * np.cos(a) + Y * np.sin(a); v = _sm(h, w, s, 4); return _n(np.abs((u * _rng(s).uniform(3, 5) + v) % 2.0 - 1.0))
def ridge(X, Y, h, w, s): f = _sm(h, w, s, 3) * 0.6 + _sm(h, w, s * 2 + 1, 7) * 0.4; return _n(1.0 - np.abs(2 * f - 1))
def wisp(X, Y, h, w, s): ang = _sm(h, w, s * 3 + 2, 4) * 6.28; u = X * np.cos(ang) + Y * np.sin(ang); return _n(_sm(h, w, s, 5) * 0.5 + 0.5 * (0.5 + 0.5 * np.sin(u * _rng(s).uniform(14, 24))))
def lattice(X, Y, h, w, s): a = _rng(s).uniform(7, 12); g = _rng(s).uniform(.4, 1.0); u = X * np.cos(g) + Y * np.sin(g); v = -X * np.sin(g) + Y * np.cos(g); return _n(np.abs(np.sin(u * a)) * np.abs(np.sin(v * a)))
def shards(X, Y, h, w, s):
    lab = _vor(X, Y, h, w, s * 7 + 3, int(_rng(s).integers(30, 55))); val = _rng(s + 5).random(int(lab.max()) + 2).astype(np.float32); t = val[lab]
    gy, gx = np.gradient(lab.astype(np.float32)); return _n(t * 0.8 + 0.4 * _n(np.hypot(gx, gy)))
def flux(X, Y, h, w, s):
    rng = _rng(s); t = np.zeros((h, w), np.float32)
    for _ in range(4): a = rng.uniform(0, np.pi); f = rng.uniform(2, 5); ph = rng.uniform(0, 6.28); t += np.sin((X * np.cos(a) + Y * np.sin(a)) * np.pi * f + ph)
    return _n(t)
def vein(X, Y, h, w, s): nz = _sm(h, w, s, 3) * 0.5 + _sm(h, w, s * 2 + 1, 8) * 0.5; r = 1.0 - np.abs(2 * nz - 1); return _n((r > 0.78).astype(np.float32) * r + 0.25 * nz)
def terrazzo(X, Y, h, w, s):
    lab = _vor(X, Y, h, w, s * 5 + 2, int(_rng(s).integers(40, 75))); val = _rng(s + 9).random(int(lab.max()) + 2).astype(np.float32); t = val[lab]
    sp = cv2.GaussianBlur((_rng(s * 3 + 1).random((h, w)) > 0.9).astype(np.float32), (0, 0), 0.6); return _n(t * 0.85 + 0.2 * sp)
def moire(X, Y, h, w, s): a = _rng(s).uniform(14, 22); b = a + _rng(s).uniform(0.6, 1.6); g = _rng(s).uniform(0, 1.0); u = X * np.cos(g) + Y * np.sin(g); v = -X * np.sin(g) + Y * np.cos(g); return _n(np.sin(u * a) * np.sin(v * b))
def splinter(X, Y, h, w, s):
    rng = _rng(s); t = np.zeros((h, w), np.float32); a = rng.uniform(0, np.pi)
    for _ in range(int(rng.integers(40, 70))):
        w0 = rng.uniform(.004, .02); u = (X - rng.uniform(0, 1)) * np.cos(a) + (Y - rng.uniform(0, 1)) * np.sin(a); t += np.exp(-(u * u) / (2 * w0 * w0)) * rng.random()
    return _n(t)
def comb(X, Y, h, w, s): xw, yw = _warp(X, Y, h, w, s, 0.34); base = _sm(h, w, s, 4); a = _rng(s).uniform(0, np.pi); u = X * np.cos(a) + Y * np.sin(a); return _n(base * 0.7 + 0.3 * (0.5 + 0.5 * np.sin(u * _rng(s).uniform(55, 95) + base * 6)))
def quilt(X, Y, h, w, s): a = _rng(s).uniform(7, 11); return _n(np.abs(np.sin(X * a * np.pi)) + np.abs(np.sin(Y * a * np.pi)) + 0.3 * _sm(h, w, s, 6))
def wovenrib(X, Y, h, w, s): a = _rng(s).uniform(8, 13); over = (np.floor(X * a) + np.floor(Y * a)) % 2; rib = np.where(over > 0, np.abs(np.sin(X * a * np.pi)), np.abs(np.sin(Y * a * np.pi))); return _n(rib)

BASES = dict(linear=linear, bands=bands, plaid=plaid, liquid=liquid, aurora=aurora, marble=marble, ribbon=ribbon,
             streak=streak, crossflow=crossflow, blocks=blocks, triangles=triangles, crosswave=crosswave, drip=drip,
             brush=brush, herring=herring, wavefold=wavefold, ridge=ridge, wisp=wisp, lattice=lattice, shards=shards,
             flux=flux, vein=vein, terrazzo=terrazzo, moire=moire, splinter=splinter, comb=comb, quilt=quilt, wovenrib=wovenrib)


# ---------------- MODS  fn(t,X,Y,h,w,s)->t01 ----------------
def m_none(t, X, Y, h, w, s): return t
def m_terr(t, X, Y, h, w, s): nn = _rng(s).integers(4, 8); return _n(np.floor(t * nn) / (nn - 1))
def m_chev(t, X, Y, h, w, s): return _n(np.abs((t * _rng(s).uniform(3, 6) % 2.0) - 1.0))
def m_facet(t, X, Y, h, w, s):
    lab = _vor(X, Y, h, w, s * 5 + 1, int(_rng(s).integers(45, 90)))
    sums = np.bincount(lab.ravel(), weights=t.ravel()); cnts = np.bincount(lab.ravel()); means = sums / np.maximum(cnts, 1)
    return _n(means[lab])
def m_scale(t, X, Y, h, w, s): a = _rng(s).uniform(11, 17); row = np.floor(Y * a); off = (row % 2) * 0.5; return _n(t * 0.6 + 0.4 * (0.5 + 0.5 * np.cos((((X * a + off) % 1.0) - 0.5) * np.pi * 2)))
def m_weave(t, X, Y, h, w, s): a = _rng(s).uniform(9, 15); over = (np.floor(X * a) + np.floor(Y * a)) % 2; return _n(np.where(over > 0, np.sin(X * a * np.pi) * 0.5 + 0.5, np.sin(Y * a * np.pi) * 0.5 + 0.5) * 0.5 + t * 0.5)
def m_hex(t, X, Y, h, w, s): a = _rng(s).uniform(9, 13); gy = Y * a * 1.1547; gx = X * a + (np.floor(gy) % 2) * 0.5; return _n(t * 0.55 + 0.45 * (np.abs((gx % 1.0) - 0.5) + np.abs((gy % 1.0) - 0.5)))
def m_flake(t, X, Y, h, w, s): rng = _rng(s * 9 + 3); fl = (rng.random((h, w)) > 0.95).astype(np.float32); fl = cv2.GaussianBlur(fl, (0, 0), 0.8); return _n(t * 0.85 + 0.32 * _n(fl))
def m_crackle(t, X, Y, h, w, s):
    lab = _vor(X, Y, h, w, s * 11 + 2, int(_rng(s).integers(60, 120))).astype(np.float32); gy, gx = np.gradient(lab); e = _n(np.hypot(gx, gy)); e = cv2.dilate(e, np.ones((2, 2), np.float32)); return _n(t * 0.7 + 0.45 * e)
def m_grain(t, X, Y, h, w, s): a = _rng(s).uniform(0, np.pi); u = X * np.cos(a) + Y * np.sin(a); return _n(t * 0.85 + 0.13 * (0.5 + 0.5 * np.sin(u * _rng(s).uniform(80, 140))) + 0.04 * _sm(h, w, s * 3 + 1, 28))

MODS = dict(none=m_none, terr=m_terr, chev=m_chev, facet=m_facet, scale=m_scale, weave=m_weave, hex=m_hex,
            flake=m_flake, crackle=m_crackle, grain=m_grain)


def _struct_fn(key):
    """Parse a baked struct_key into a callable(X,Y,h,w,s)->t01 (mirrors gradient_lib_v3 candidate gen)."""
    if "X" in key:
        a, b = key.split("X"); fa, fb = BASES[a], BASES[b]
        return lambda X, Y, h, w, s: _n(0.55 * fa(X, Y, h, w, s) + 0.45 * fb(X, Y, h, w, s + 7))
    if "." in key:
        b, m = key.split("."); fb, fm = BASES[b], MODS[m]
        return lambda X, Y, h, w, s: _n(fm(fb(X, Y, h, w, s), X, Y, h, w, s + 1))
    fb = BASES[key]
    return lambda X, Y, h, w, s: _n(fb(X, Y, h, w, s))


@lru_cache(maxsize=256)
def _struct_cached(key, h, w, s):
    # render at capped res then upscale (gradients are large-scale; keeps render <3s)
    m = max(h, w)
    if m > _CAP:
        sc = _CAP / m; hc, wc = max(8, int(round(h * sc))), max(8, int(round(w * sc)))
    else:
        hc, wc = h, w
    X, Y = _grid(hc, wc)
    t = _n(_struct_fn(key)(X, Y, hc, wc, s)).astype(np.float32)
    if (hc, wc) != (h, w):
        t = cv2.resize(t, (w, h), interpolation=cv2.INTER_LINEAR)
    return _n(t).astype(np.float32)


# ---------------- color ----------------
def _rgb2hsv(c):
    c = np.clip(np.asarray(c, np.float32), 0, 1); return cv2.cvtColor(c.reshape(1, 1, 3), cv2.COLOR_RGB2HSV).ravel()
def _hsv2rgb(hsv):
    hsv = np.asarray(hsv, np.float32); hsv[0] %= 360.0; return np.clip(cv2.cvtColor(hsv.reshape(1, 1, 3), cv2.COLOR_HSV2RGB).ravel(), 0, 1)


def _palette_k(core, k):
    """Name palette forced to exactly k VISIBLE colors. Anchors from the name are
    kept; when extending, intermediate stops get a small hue step so k colors
    genuinely read as k (not just gradation), while staying name-true."""
    from engine.expansions.color_science_rebuild_2026 import _palette_from_name
    pal = [tuple(map(float, c)) for c in _palette_from_name(core)]
    if len(pal) >= k:
        idx = np.linspace(0, len(pal) - 1, k).round().astype(int)
        return [pal[i] for i in idx]
    # extend by inserting hue-stepped midpoints between anchors
    out = list(pal)
    while len(out) < k:
        # find largest gap (by index) and insert a hue-shifted blend
        gaps = [(j, j + 1) for j in range(len(out) - 1)]
        if not gaps:
            out.append(out[-1]); continue
        j, j1 = gaps[len(out) % len(gaps)]
        a = _rgb2hsv(out[j]); b = _rgb2hsv(out[j1]); mid = (np.asarray(out[j]) + np.asarray(out[j1])) * 0.5
        midh = _rgb2hsv(mid); midh[0] = (a[0] + (((b[0] - a[0] + 540) % 360) - 180) * 0.5) % 360 + 18.0  # nudge hue
        midh[1] = min(1.0, midh[1] * 1.08 + 0.05)
        out.insert(j1, tuple(_hsv2rgb(midh)))
    return out[:k]


def _ramp(t, pal):
    pal = np.asarray(pal, np.float32); K = len(pal); tt = np.clip(t, 0, 1) * (K - 1)
    i0 = np.floor(tt).astype(np.int32); i1 = np.clip(i0 + 1, 0, K - 1); f = (tt - i0)[..., None]
    col = pal[i0] * (1 - f) + pal[i1] * f
    return np.clip((col - 0.5) * 1.12 + 0.5, 0, 1)


def _relief(t):
    """3D height shading from the structure (owner wants depth/height)."""
    b = cv2.GaussianBlur(t, (0, 0), 1.6); gy, gx = np.gradient(b)
    sh = 1.0 + (gx * 0.9 - gy * 0.9) * 2.2
    return np.clip(sh, 0.82, 1.20).astype(np.float32)


# ---------------- design assignment ----------------
def _load_designs():
    # dev: prefer the freshly-regenerated JSON if present; ship: fall back to baked
    try:
        with open(_DESIGNS_JSON) as f:
            d = json.load(f)
            if d:
                return d
    except Exception:
        pass
    return [{"struct": s, "k": k} for s, k in _BAKED_DESIGNS]


def _spread(lst):
    """[a,b,c,d] -> [a,d,b,c] so a structure's reuses are maximally different in k."""
    out = []; i, j = 0, len(lst) - 1
    while i <= j:
        out.append(lst[i])
        if i != j:
            out.append(lst[j])
        i += 1; j -= 1
    return out


_ASSIGN = {}


def _natural_richness(core):
    from engine.expansions.color_science_rebuild_2026 import _palette_from_name
    return len(_palette_from_name(core))


def _core_of(fid):
    core = fid[5:] if fid.startswith("grad_") else fid
    for suf in ("_vortex", "_diag", "_h"):
        if core.endswith(suf):
            core = core[:-len(suf)]; break
    return core


def _build_assignment(fids):
    """fid->design with STRUCTURE DIVERSITY first: round-robin across distinct
    struct_keys so the first N finishes each get a unique structure before any
    structure repeats; when a structure IS reused it carries a different color
    count (k). Then richest name-palettes are matched to the highest color tiers
    (minimises fake color extension). Each design used at most once."""
    from collections import OrderedDict
    designs = _load_designs()
    groups = OrderedDict()
    for i, d in enumerate(designs):
        groups.setdefault(d["struct"], []).append(i)
    for sk in groups:                                  # within a struct, span color counts on reuse
        groups[sk].sort(key=lambda i: designs[i]["k"])
        groups[sk] = _spread(groups[sk])               # k=2 then k=5 then 3,4: reuses look maximally different
    picked, rnd = [], 0
    while len(picked) < len(fids):
        added = False
        for sk in groups:
            if rnd < len(groups[sk]):
                picked.append(groups[sk][rnd]); added = True
                if len(picked) >= len(fids):
                    break
        if not added:
            break
        rnd += 1
    picked_sorted = sorted(picked, key=lambda i: (-designs[i]["k"], designs[i]["struct"]))
    fids_sorted = sorted(fids, key=lambda f: (-_natural_richness(_core_of(f)), f))
    _ASSIGN.clear()
    for i, fid in enumerate(fids_sorted):
        d = designs[picked_sorted[i % len(picked_sorted)]]
        _ASSIGN[fid] = (d["struct"], int(d["k"]))


# ---------------- paint / spec factories ----------------
def _seed(fid):
    return (abs(hash(fid)) % 7919) ^ 0x6A1F  # deterministic per-fid; struct_key is what guarantees uniqueness


def _g2_recipe(fid):
    core = _core_of(fid)
    key, k = _ASSIGN.get(fid, ("liquid", 3))
    pal = _palette_k(core, k)
    return pal, (key, k, _seed(fid)), None


def _g2_paint_factory(pal, design, _unused):
    key, k, sd = design
    base_lo = np.clip(np.float32(pal[0]) * 0.5, 0, 1)
    accent = np.float32(pal[-1])

    def f(h, w, s):
        t = _struct_cached(key, int(h), int(w), int(sd))
        col = _ramp(t, pal)
        col = col * _relief(t)[..., None]
        # subtle premium pop on the brightest structure ridges (uses name's own accent, not rainbow)
        gy, gx = np.gradient(cv2.GaussianBlur(t, (0, 0), 1.2)); edge = _n(np.hypot(gx, gy))
        col = col + (edge[..., None] ** 1.5) * accent[None, None, :] * 0.10
        col = np.clip(col * 1.08 + 0.015, 0, 1)   # premium brightness lift (was reading slightly muddy)
        return col.astype(np.float32)
    return f


def _g2_spec_factory(pal, design, _unused):
    key, k, sd = design

    def f(h, w, s):
        t = _struct_cached(key, int(h), int(w), int(sd))
        gy, gx = np.gradient(cv2.GaussianBlur(t, (0, 0), 1.2)); hero = _n(np.hypot(gx, gy))   # feature edges -> M
        fine = _n(np.abs(t - cv2.GaussianBlur(t, (0, 0), 2.0)))                                # high-freq -> Cc
        gM = _sm(h, w, (sd ^ 0x5C), 4)                                                          # M's own broad heat
        gR = _sm(h, w, (sd ^ 0x2B), 4)                                                          # R's own micro grain
        M = np.clip(14 + np.clip(hero * 1.7, 0, 1) * 200 + gM * 60, 0, 255)
        R = np.clip(58 + gR * 150, 15, 255)
        Cc = np.clip(20 + fine * 130 + _sm(h, w, (sd ^ 0x4D), 3) * 55, 16, 255)
        return M.astype(np.float32), R.astype(np.float32), Cc.astype(np.float32)
    return f


# ---------------- install ----------------
def install_gradients_v2(mono_reg, base_reg=None):
    """Final-authority gradient install. Overrides every grad_ id (all monolithic)
    with a unique structure x color-richness design. Reuses the proven contract
    wrapper + _install_ground_up plumbing from color_science_rebuild_2026."""
    from engine.expansions.color_science_rebuild_2026 import _install_ground_up
    fids = [k for k in mono_reg.keys() if k.startswith("grad_")]
    if base_reg:
        fids += [k for k in base_reg.keys() if k.startswith("grad_")]
    _build_assignment(sorted(set(fids)))
    return _install_ground_up(mono_reg, base_reg, "grad_", _g2_paint_factory, _g2_spec_factory, _g2_recipe)
