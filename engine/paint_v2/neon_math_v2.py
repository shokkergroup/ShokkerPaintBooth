"""NEON MATH v2 — the ★ NEON UNDERGROUND 25-structure rebuild library.

[SPB NEON REBUILD 2026-08-27 — owner mandate: "Totally REBUILD NEON UNDERGROUND and the 20
finishes it has plus invent 5 new one's for a total of 25… Make a couple of the finishes at
least racing specific."] Owner-judged vs Codex's Fractured Wilds. Ledger + design laws:
docs/NEON_UNDERGROUND_REBUILD_2026-08-27.md.

OWNER CALIBRATION (2026-08-27, binding): CLEAN LINES FIRST — grit/noise is a rationed spice,
never a base; brights genuinely BRIGHT off dark grounds; intricacy from PATTERN (8-32px clean
elements), not garbage texture; spec follows the paint anatomy (married, one build pass); wide
8-tier spec color movement per channel.

Contract per structure (same as anime_math, proven 2026-08-25):
  _b_<key>(shape, seed) -> {'rgb': float32 (h,w,3) in 0..1, 'spec': float32 (h,w,3) 0..255 (M,R,CC)}
ONE pass from shared geometry; `build(key, shape, seed)` lru-cached so paint_fn+spec_fn share a
compute. ALL feature sizes scale h/2048 (native-res at any size). Budget <= ~2.5s @2048.

This file deliberately does NOT touch engine/paint_v2/neon_math.py — the old library keeps the
shipped finishes rendering until the wiring turn swaps neon_underground.py + neon_catalog_2026.py
over (zero-breakage window if the owner restarts mid-lane).

Public: NEON_STRUCTURES[key](shape, seed)->rgb, NEON_SPECS[key](shape, seed)->spec,
COVERAGE_EXEMPT / FINE_DETAIL_EXEMPT (deliberate, documented opt-outs).
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

# ============================================================================ shared core

_BUILDERS: dict = {}
COVERAGE_EXEMPT: dict = {}      # key -> reason (deliberate non-full-canvas designs; none yet)
FINE_DETAIL_EXEMPT: dict = {}   # key -> reason (deliberately smooth designs; none yet)


def _structure(key):
    def deco(fn):
        _BUILDERS[key] = fn
        return fn
    return deco


def _rng(seed):
    return np.random.default_rng(int(seed) & 0x7FFFFFFF)


def _vgrid(shape, seed, fy, fx):
    h, w = shape
    r = _rng(seed)
    g = r.random((int(fy) + 2, int(fx) + 2)).astype(np.float32)
    return cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)


def _fbm(shape, seed, octaves=4, freq=3.0, gain=0.5, aniso=(1.0, 1.0)):
    h, w = shape
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        fy = max(1, int(round(freq * (2 ** o) * aniso[0])))
        fx = max(1, int(round(freq * (2 ** o) * aniso[1])))
        out += amp * _vgrid(shape, seed * 1013 + o * 7919 + 17, fy, fx)
        tot += amp
        amp *= gain
    return out / max(tot, 1e-6)


def _norm(a):
    a = a.astype(np.float32)
    if a.size == 0:
        return a
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / max(hi - lo, 1e-6)


def _ramp(t, stops):
    stops = np.asarray(stops, np.float32)
    n = len(stops) - 1
    t = np.clip(t, 0, 1) * n
    i = np.clip(np.floor(t).astype(np.int32), 0, n - 1)
    f = (t - i)[..., None]
    return stops[i] * (1 - f) + stops[i + 1] * f


def _spec_pack(M, R, CC):
    M = np.clip(np.asarray(M, np.float32), 0, 255)
    R = np.clip(np.asarray(R, np.float32), 6, 255)
    CC = np.clip(np.asarray(CC, np.float32), 16, 255)
    return np.stack([M, R, CC], axis=2)


# 8-tier ladders (owner Rule 2: many shades, never two levels)
_L_M = np.asarray((7, 33, 67, 104, 142, 181, 219, 253), np.float32)
_L_R = np.asarray((8, 30, 61, 99, 140, 179, 220, 251), np.float32)
_L_C = np.asarray((16, 34, 65, 103, 143, 181, 217, 254), np.float32)


def _tiers(field, ladder, lo=0, hi=7):
    """Map a 0..1 field onto a slice of an 8-tier ladder -> wide, stepped channel movement."""
    idx = np.clip((_norm(field) * (hi - lo + 0.999)).astype(np.int32) + lo, 0, len(ladder) - 1)
    return ladder[idx]


def _scatter(rng, n, w, h, min_d, margin=0.16):
    """Poisson-ish center scatter incl. off-canvas margin (features cross edges — no framing)."""
    pts = []
    for _ in range(n * 40):
        if len(pts) >= n:
            break
        x = rng.uniform(-margin * w, (1 + margin) * w)
        y = rng.uniform(-margin * h, (1 + margin) * h)
        if all((x - p[0]) ** 2 + (y - p[1]) ** 2 > min_d * min_d for p in pts):
            pts.append((x, y))
    return pts


def _sub(shape, cx, cy, pad):
    """Clipped subwindow around (cx,cy) -> (y0,y1,x0,x1) or None if fully off-canvas."""
    h, w = shape
    x0, x1 = int(max(0, cx - pad)), int(min(w, cx + pad))
    y0, y1 = int(max(0, cy - pad)), int(min(h, cy + pad))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    return y0, y1, x0, x1


def _polar(y0, y1, x0, x1, cx, cy):
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = xx - cx, yy - cy
    return np.sqrt(dx * dx + dy * dy), np.arctan2(dy, dx)


def _dt(mask_u8):
    """Distance (px) to the nearest ON pixel of mask_u8."""
    return cv2.distanceTransform((mask_u8 == 0).astype(np.uint8), cv2.DIST_L2, 3)


def _glow_add(rgb, mask01, color, sigma, gain):
    """Clean additive halation of a mask, no grain."""
    b = cv2.GaussianBlur(mask01.astype(np.float32), (0, 0), max(0.8, sigma))
    rgb += b[..., None] * np.asarray(color, np.float32) * gain
    return rgb


def _chaikin(pts, iters=3):
    """Corner-cutting smoothing — polylines lose their elbow joints (clean curves, no kinks)."""
    p = np.asarray(pts, np.float32)
    for _ in range(iters):
        q = np.empty((2 * len(p) - 2, 2), np.float32)
        q[0::2] = p[:-1] * 0.75 + p[1:] * 0.25
        q[1::2] = p[:-1] * 0.25 + p[1:] * 0.75
        p = q
    return p.astype(np.int32)


def _walk(rng, w, h, n_pts, step, start=None, heading=None, turn=0.55):
    """Smooth persistent random-walk polyline (int32 pts for cv2)."""
    if start is None:
        start = (rng.uniform(-0.1 * w, 1.1 * w), rng.uniform(-0.1 * h, 1.1 * h))
    a = rng.uniform(0, 2 * np.pi) if heading is None else heading
    pts = [start]
    for _ in range(n_pts - 1):
        a += rng.uniform(-turn, turn)
        pts.append((pts[-1][0] + np.cos(a) * step * rng.uniform(0.7, 1.3),
                    pts[-1][1] + np.sin(a) * step * rng.uniform(0.7, 1.3)))
    return np.asarray(pts, np.int32)


def _sheen(shape, seed, ang, wav, amp):
    """Broad brushed sheen bands (smooth macro light that fine detail rides on) — lifts the
    90th-percentile luma of every cell so the field reads lit, not void."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ph = (xx * np.cos(ang) + yy * np.sin(ang)) / max(8.0, wav)
    f = _fbm(shape, seed, octaves=2, freq=2.0)
    return (0.5 + 0.5 * np.sin(ph * 2 * np.pi + f * 3.0)).astype(np.float32) * amp


def _asphalt(shape, seed, base=(0.024, 0.028, 0.040), speckle=0.05, amp=0.020):
    """Night asphalt ground: smooth stain pools + RATIONED structured speckle (clean, sparse
    1-2px two-tone points — the only grit these racing designs get)."""
    h, w = shape
    rgb = np.zeros((h, w, 3), np.float32) + np.asarray(base, np.float32)
    pools = (_fbm(shape, seed * 31 + 5, octaves=3, freq=2.5) - 0.5) * 0.020
    rgb += pools[..., None]
    r = _rng(seed * 77 + 3)
    fine = r.random((h, w)).astype(np.float32)
    lit = (fine > 1.0 - speckle * 0.5).astype(np.float32)
    dark = (fine < speckle * 0.5).astype(np.float32)
    rgb += (lit * amp - dark * amp)[..., None]
    return np.clip(rgb, 0, 1), pools, lit


# ============================================================================ 9 ★ REDLINE TACH
# FIELD of tachometers: 3 size tiers (max ~160px) tiling the whole sheet over a brushed
# instrument-panel micro-ground. Mark families: tube arcs w/ dim->blazing ramp, tick combs,
# hatched redline sectors, needle+ghosts, mini checker ribbons, bezels, faces, panel seams.
@_structure("redline_tach")
def _b_redline_tach(shape, seed):
    h, w = shape
    s = h / 2048.0
    rng = _rng(seed * 101 + 9)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rgb = np.zeros((h, w, 3), np.float32) + np.asarray((0.052, 0.050, 0.068), np.float32)
    weave = (np.abs(((xx / (5.5 * s)) % 2) - 1) + np.abs(((yy / (5.5 * s)) % 2) - 1)) * 0.5
    rgb += ((weave - 0.5) * 0.052)[..., None]
    rgb += ((_fbm(shape, seed * 13 + 1, octaves=4, freq=5.0) - 0.5) * 0.030)[..., None]
    rng_bg = _rng(seed * 503 + 11)
    for _ in range(9):
        x0 = int(rng_bg.uniform(0, w))
        a0 = rng_bg.uniform(-0.25, 0.25)
        cv2.line(rgb, (x0, 0), (int(x0 + a0 * h), h), (0.088, 0.072, 0.060), max(1, int(2 * s)), cv2.LINE_AA)
    sh = _sheen(shape, seed * 331 + 7, rng_bg.uniform(0, np.pi), 340 * s, 0.155)
    rgb += sh[..., None] * np.asarray((0.75, 0.82, 1.0), np.float32)

    gnd = _fbm(shape, seed * 57 + 8, octaves=3, freq=5.0)
    M = _tiers(gnd, _L_M, 0, 2).copy()
    R = _tiers(1 - gnd, _L_R, 5, 7).copy()
    CC = _tiers(gnd, _L_C, 5, 7).copy()

    arc_ramp = np.asarray([(0.30, 0.020, 0.035), (0.62, 0.045, 0.050), (0.95, 0.16, 0.05),
                           (1.00, 0.52, 0.10), (1.00, 0.94, 0.78)], np.float32)
    tiers_spec = [(8, 118, 162), (22, 62, 100), (80, 28, 48)]
    for (cnt, rlo, rhi) in tiers_spec:
        centers = _scatter(rng, cnt, w, h, rlo * 1.35 * s, margin=0.08)
        for (cx, cy) in centers:
            Rg = rng.uniform(rlo, rhi) * s
            win = _sub(shape, cx, cy, Rg * 1.30)
            if win is None:
                continue
            y0, y1, x0, x1 = win
            rad, ang = _polar(y0, y1, x0, x1, cx, cy)
            a0 = rng.uniform(0, 2 * np.pi)
            span = rng.uniform(1.45, 1.70) * np.pi
            u = ((ang - a0) % (2 * np.pi)) / span
            inswp = (u <= 1.0)
            col3 = _ramp(u, arc_ramp)
            hot = np.clip(u * 1.15, 0.15 if Rg > 55 * s else 0.42, 1.0)[..., None]
            gain = rng.uniform(0.78, 1.05)
            sub_rgb = rgb[y0:y1, x0:x1]
            subM, subR, subC = M[y0:y1, x0:x1], R[y0:y1, x0:x1], CC[y0:y1, x0:x1]
            big, mid = Rg > 90 * s, Rg > 55 * s
            tb = max(2.0, Rg * 0.055)

            face = rad < Rg * 0.62
            sub_rgb[face] += np.asarray((0.020, 0.018, 0.027), np.float32)
            subM[face] = 33
            if Rg > 40 * s:
                hub = rad < max(2.0, Rg * 0.035)
                sub_rgb[hub] = (0.55, 0.50, 0.48)
                subM[hub] = 253
                subR[hub] = 45

            # outer tube band
            bd = np.abs(rad - Rg)
            glass = (bd < tb) & inswp
            core = (bd < tb * 0.42) & inswp & (u > 0.10)
            sub_rgb[glass] = np.maximum(sub_rgb[glass], (col3 * hot * gain)[glass])
            sub_rgb[core] = np.maximum(sub_rgb[core], (col3 * 0.4 + 0.6)[core])
            halo = np.exp(-bd / (tb * 3.0)) * inswp * np.clip(u, 0.12, 1.0)
            sub_rgb += halo[..., None] * col3 * (0.30 * gain)
            subM[glass] = _tiers(u, _L_M, 2, 4)[glass]
            subR[glass] = _tiers(1 - u, _L_R, 0, 1)[glass]
            subC[glass] = 18

            # checker ribbon band (cells stay >=3px)
            if mid and tb * 1.5 >= 3:
                Rc = Rg * (0.74 if big else 0.78)
                cell = tb * 1.5
                bdc = np.abs(rad - Rc)
                onb = (bdc < cell) & inswp
                row = np.floor((rad - (Rc - cell)) / cell)
                colq = np.floor(u * (span * Rc) / cell)
                chk = ((row + colq) % 2 < 1) & onb
                sub_rgb[chk] = (0.90, 0.90, 0.84)
                sub_rgb[onb & ~chk] = (0.055, 0.055, 0.065)
                subR[chk] = 40
                subR[onb & ~chk] = 220
                subC[onb] = 30
                subM[chk] = 150

            # second glass band on the big tier
            if big:
                R2 = Rg * 0.87
                bd2 = np.abs(rad - R2)
                g2 = (bd2 < tb * 0.75) & inswp
                sub_rgb[g2] = np.maximum(sub_rgb[g2], (col3 * hot * (0.75 * gain))[g2])
                subM[g2] = _tiers(u, _L_M, 3, 5)[g2]
                subR[g2] = 30
                subC[g2] = 20

            # hatched redline sector
            if mid:
                sect = (rad < Rg - tb) & (rad > Rg * 0.80) & (u > 0.82) & inswp
                hx = ((xx[y0:y1, x0:x1] + yy[y0:y1, x0:x1]) / (max(4.0, Rg * 0.06))) % 1.0 < 0.5
                sub_rgb[sect & hx] = np.maximum(sub_rgb[sect & hx], (0.44, 0.020, 0.035))
                sub_rgb[sect & ~hx] = np.maximum(sub_rgb[sect & ~hx], (0.16, 0.012, 0.022))
                subR[sect] = np.where(hx[sect], 140.0, 99.0)
                subC[sect] = 120.0
                subM[sect] = 67.0

            # tick combs
            N = int(np.clip(Rg / (4.0 * s), 12, 44))
            tlen = max(3.0, Rg * 0.09)
            minor = ((u * N) % 1 < 0.11) & (rad > Rg + tb) & (rad < Rg + tb + tlen) & inswp
            major = ((u * max(6, N // 6)) % 1 < 0.055) & (rad > Rg + tb) & (rad < Rg + tb + tlen * 1.8) & inswp
            sub_rgb[minor] = np.maximum(sub_rgb[minor], (0.46, 0.47, 0.52))
            sub_rgb[major] = np.maximum(sub_rgb[major], col3[major] * 0.5 + 0.42)
            subM[minor] = 181
            subM[major] = 253
            subR[minor | major] = 45
            subC[minor | major] = 40

            # needle + ghosts
            un = rng.uniform(0.84, 0.96)
            ghosts = ((1.0, 0.45, 0.20) if mid else (1.0, 0.40))
            for k, alpha in enumerate(ghosts):
                uk = un - k * 0.05
                nm = (np.abs(u - uk) < max(0.0045, 0.30 / max(N, 12))) & (rad < Rg * 0.97) & (rad > Rg * 0.14)
                sub_rgb[nm] = np.maximum(sub_rgb[nm], np.asarray((1.0, 0.88, 0.70), np.float32) * alpha * gain)
                if k == 0:
                    subM[nm] = 253
                    subR[nm] = 30
                    subC[nm] = 24

            # bezel
            bez = np.abs(rad - (Rg + tb + tlen * 2.1)) < max(1.2, 1.6 * s)
            sub_rgb[bez] = np.maximum(sub_rgb[bez], (0.30, 0.32, 0.38))
            subM[bez] = 219
            subR[bez] = 61
            subC[bez] = 65

    # micro-tier: LED indicator lamps peppering the panel between gauges
    rng_led = _rng(seed * 811 + 3)
    led_cols = np.asarray([(1.0, 0.62, 0.15), (1.0, 0.20, 0.12), (0.20, 1.0, 0.45),
                           (0.15, 0.75, 1.0), (1.0, 0.90, 0.40)], np.float32)
    for _ in range(320):
        lx, ly = rng_led.uniform(-0.04, 1.04) * w, rng_led.uniform(-0.04, 1.04) * h
        rr2 = rng_led.uniform(3, 7) * s
        win = _sub(shape, lx, ly, rr2 * 5)
        if win is None:
            continue
        y0, y1, x0, x1 = win
        rad, _a = _polar(y0, y1, x0, x1, lx, ly)
        colL = led_cols[int(rng_led.integers(0, len(led_cols)))]
        disc = rad < rr2
        subL = rgb[y0:y1, x0:x1]
        subL[disc] = colL * 0.5 + 0.45
        subL += np.exp(-rad / (rr2 * 2.0))[..., None] * colL * 0.5
        M[y0:y1, x0:x1][disc] = 104
        R[y0:y1, x0:x1][disc] = 12
        CC[y0:y1, x0:x1][disc] = 16

    rgb = np.clip(rgb, 0, 1)
    return {"rgb": rgb, "spec": _spec_pack(M, R, CC)}


# ============================================================================ 17 ★ BOOST SPOOL
# FIELD of turbo plumbing: 37 thin pipe runs in 3 radius classes weaving the whole sheet over a
# dense background-conduit lattice. Mark families: cylinder steel + specular stripe, glass
# spool-flow sections, clamp bars, heat-wrap sleeves, BOV blooms, ambient spill.
@_structure("boost_spool")
def _b_boost_spool(shape, seed):
    h, w = shape
    s = h / 2048.0
    rng = _rng(seed * 211 + 17)
    rgb = np.zeros((h, w, 3), np.float32) + np.asarray((0.026, 0.030, 0.052), np.float32)
    band = np.sin(np.mgrid[0:h, 0:w][0].astype(np.float32) / (260 * s))
    rgb += (band * 0.008)[..., None]
    rgb += ((_fbm(shape, seed * 19 + 2, octaves=3, freq=2.5) - 0.5) * 0.012)[..., None]

    gnd = _fbm(shape, seed * 61 + 4, octaves=3, freq=4.0)
    M = _tiers(gnd, _L_M, 0, 1).copy()
    R = _tiers(1 - gnd, _L_R, 5, 7).copy()
    CC = _tiers(gnd, _L_C, 5, 6).copy()
    rgb += _sheen(shape, seed * 733 + 9, 0.35, 380 * s, 0.14)[..., None] * np.asarray((0.55, 0.75, 1.0), np.float32)
    # dense distant conduit lattice fills the interstitial ground (own rng stream)
    rng_bg = _rng(seed * 977 + 41)
    for _ in range(88):
        bx0, by0 = int(rng_bg.uniform(-0.1, 1.1) * w), int(rng_bg.uniform(-0.1, 1.1) * h)
        aa0 = rng_bg.uniform(0, np.pi)
        bx1, by1 = int(bx0 + np.cos(aa0) * 3 * w), int(by0 + np.sin(aa0) * 3 * w)
        cc0 = 0.150 + 0.065 * rng_bg.random()
        cv2.line(rgb, (bx0, by0), (bx1, by1), (cc0, cc0 * 1.08, cc0 * 1.45), max(1, int(3 * s)), cv2.LINE_AA)
        cv2.line(rgb, (bx0 + int(6 * s), by0 + int(6 * s)), (bx1 + int(6 * s), by1 + int(6 * s)),
                 (cc0 * 0.7, cc0 * 0.75, cc0 * 1.0), max(1, int(1.5 * s)), cv2.LINE_AA)
        cv2.line(rgb, (bx0 - int(3 * s), by0 - int(3 * s)), (bx1 - int(3 * s), by1 - int(3 * s)),
                 (0.20, 0.23, 0.30), 1, cv2.LINE_AA)

    rng_gl = _rng(seed * 663 + 29)
    for _ in range(420):
        gx0, gy0 = int(rng_gl.uniform(0, w)), int(rng_gl.uniform(0, h))
        rr3 = max(1, int(rng_gl.uniform(1.5, 3.5) * s))
        cv2.circle(rgb, (gx0, gy0), rr3, (0.34, 0.38, 0.48), -1, cv2.LINE_AA)
        cv2.circle(rgb, (gx0 - rr3 // 2, gy0 - rr3 // 2), max(1, rr3 // 2), (0.55, 0.60, 0.70), -1, cv2.LINE_AA)
        M[max(0, gy0 - rr3):gy0 + rr3, max(0, gx0 - rr3):gx0 + rr3] = 219
    classes = [(8 * s, 26), (12 * s, 20), (17 * s, 14)]
    glass_class = 1
    pipe_dirs, clamp_bars, bloom_pts = [], [], []
    dists, masks, wrapmasks = [], [], []
    for ci, (rp, cnt) in enumerate(classes):
        mask = np.zeros((h, w), np.uint8)
        wmask = np.zeros((h, w), np.uint8)
        dirs = []
        for _ in range(cnt):
            raw = _walk(rng, w, h, int(rng.integers(5, 8)), rng.uniform(260, 430) * s, turn=0.5)
            pts = _chaikin(raw, 2)
            cv2.polylines(mask, [pts], False, 255, 1, cv2.LINE_AA)
            seg = (raw[-1] - raw[0]).astype(np.float32)
            dirs.append(np.arctan2(seg[1], seg[0]) if np.any(seg) else 0.0)
            step_i = max(4, len(pts) // 5)
            for i in range(2, len(pts) - 2, step_i):
                d2 = (pts[min(i + 2, len(pts) - 1)] - pts[i - 2]).astype(np.float32)
                clamp_bars.append((pts[i], np.arctan2(d2[1], d2[0]), rp))
            if ci != glass_class and rng.random() < 0.7:
                i0 = int(rng.integers(0, max(1, len(pts) - 8)))
                chunk = pts[i0:i0 + int(rng.integers(5, 9))]
                if len(chunk) >= 2:
                    cv2.polylines(wmask, [chunk], False, 255, max(3, int(rp * 2.6)), cv2.LINE_AA)
            if rng.random() < 0.7 and len(bloom_pts) < 20:
                j = int(rng.integers(1, len(pts)))
                bloom_pts.append(tuple(pts[j]))
        pipe_dirs.append(dirs)
        dists.append(_dt(mask))
        masks.append(mask)
        wrapmasks.append(wmask)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for ci, (rp, cnt) in enumerate(classes):
        d = dists[ci]
        body = d < rp
        if not body.any():
            continue
        shade = np.sqrt(np.clip(1 - (d / rp) ** 2, 0, 1)).astype(np.float32)
        if ci == glass_class:
            gcol = np.asarray((0.045, 0.075, 0.115), np.float32)
            rgb[body] = gcol * (0.5 + 0.5 * shade[body, None])
            th = pipe_dirs[ci][0] if pipe_dirs[ci] else 0.9
            proj = xx * np.cos(th) + yy * np.sin(th)
            flow = 0.5 + 0.5 * np.sin(proj / (6.5 * s))
            swirl = ((proj / (26 * s)) % 1 < 0.16) & ((d / rp) % 0.5 < 0.2)
            inner = d < rp * 0.8
            fcol = np.asarray((0.10, 0.85, 1.0), np.float32)
            rgb[inner] += (flow[inner, None] * fcol * 0.60 * shade[inner, None])
            rgb[inner & swirl] = np.maximum(rgb[inner & swirl], (0.55, 0.98, 1.0))
            _glow_add(rgb, (inner & (flow > 0.8)).astype(np.float32), fcol, 6 * s, 0.30)
            M[inner] = _tiers(flow, _L_M, 2, 4)[inner]
            R[body] = _tiers(shade, _L_R, 0, 1)[body]
            CC[body] = 18
            M[inner & swirl] = 219
        else:
            steel = np.asarray((0.19, 0.21, 0.25), np.float32)
            rgb[body] = steel * (0.35 + 0.85 * shade[body, None])
            wrapm = body & (wrapmasks[ci] > 0)
            bandw = ((xx + yy) / (10.0 * s)) % 1 < 0.55
            wl = np.asarray((0.34, 0.28, 0.16), np.float32)
            wd = np.asarray((0.115, 0.100, 0.075), np.float32)
            rgb[wrapm] = np.where(bandw[wrapm, None], wl, wd) * (0.45 + 0.75 * shade[wrapm, None])
            stripe = (d < rp * 0.22)
            rgb[stripe] = np.maximum(rgb[stripe], (0.62, 0.67, 0.74))
            M[body] = _tiers(shade, _L_M, 4, 7)[body]
            R[body] = _tiers(1 - shade, _L_R, 1, 3)[body]
            CC[body] = 40
            R[wrapm] = _tiers(shade, _L_R, 5, 7)[wrapm]
            M[wrapm] = _tiers(shade, _L_M, 1, 2)[wrapm]
            CC[wrapm] = 170
            M[stripe] = 253

    clampmask = np.zeros((h, w), np.uint8)
    for (pt, th2, rp) in clamp_bars[::2]:
        px, py = int(pt[0]), int(pt[1])
        if not (-60 <= px < w + 60 and -60 <= py < h + 60):
            continue
        nx, ny = -np.sin(th2), np.cos(th2)
        L = rp * 1.35
        cv2.line(clampmask, (int(px - nx * L), int(py - ny * L)), (int(px + nx * L), int(py + ny * L)),
                 255, max(2, int(4 * s)), cv2.LINE_AA)
    dmin = np.minimum.reduce(dists)
    clampm = (clampmask > 0) & (dmin < 19 * s)
    rgb[clampm] = np.maximum(rgb[clampm], (0.46, 0.49, 0.55))
    M[clampm] = 253
    R[clampm] = 30
    CC[clampm] = 30

    gl_small = cv2.resize((dists[glass_class] < classes[glass_class][0]).astype(np.float32),
                          (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    spill = cv2.resize(cv2.GaussianBlur(gl_small, (0, 0), 22), (w, h), interpolation=cv2.INTER_LINEAR)
    rgb += spill[..., None] * np.asarray((0.06, 0.30, 0.38), np.float32) * 0.48

    for (bx, by) in bloom_pts:
        Rb = rng.uniform(26, 60) * s
        win = _sub(shape, bx, by, Rb)
        if win is None:
            continue
        y0, y1, x0, x1 = win
        rad, ang = _polar(y0, y1, x0, x1, bx, by)
        rays = (((ang * 10 / (2 * np.pi)) % 1) < 0.17) & (rad < Rb)
        fall = np.clip(1 - rad / Rb, 0, 1) ** 2
        sub = rgb[y0:y1, x0:x1]
        sub += (rays * fall)[..., None] * np.asarray((0.75, 0.95, 1.0), np.float32) * 0.8
        core = rad < max(2.0, 4 * s)
        sub[core] = (1.0, 1.0, 1.0)
        _glow_add(sub, core.astype(np.float32), (0.6, 0.9, 1.0), 6 * s, 0.8)
        M[y0:y1, x0:x1][rays] = 142
        R[y0:y1, x0:x1][rays] = 40

    rgb = np.clip(rgb, 0, 1)
    return {"rgb": rgb, "spec": _spec_pack(M, R, CC)}


# ============================================================================ 21 ★ QUARTER MILE
# FIELD drag-strip collage: 11 speed-warped checker ribbons at varied angles, 44 small
# christmas-tree stacks with reflection pools, 16 timing beams, 9 rubber laydown arcs with
# sheen, visible asphalt micro-grain + lane seams. Everything interleaved, no voids.
@_structure("quarter_mile")
def _b_quarter_mile(shape, seed):
    h, w = shape
    s = h / 2048.0
    rng = _rng(seed * 307 + 21)
    rgb, pools, _ = _asphalt(shape, seed, base=(0.040, 0.045, 0.062), speckle=0.10, amp=0.030)
    rgb += _sheen(shape, seed * 449 + 5, np.pi / 2 + 0.2, 360 * s, 0.10)[..., None] * np.asarray((0.80, 0.85, 1.0), np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    M = _tiers(pools, _L_M, 0, 1).copy()
    R = _tiers(1 - pools, _L_R, 5, 7).copy()
    CC = _tiers(pools, _L_C, 5, 7).copy()

    seam = np.zeros((h, w), np.uint8)
    for _ in range(10):
        p0 = (int(rng.uniform(-0.1, 1.1) * w), -50)
        p1 = (int(p0[0] + rng.uniform(-0.30, 0.30) * w), h + 50)
        cv2.line(seam, p0, p1, 255, max(1, int(2 * s)), cv2.LINE_AA)
    sm = seam > 0
    rgb[sm] *= 0.72
    R[sm] = 235

    th = rng.uniform(-0.35, 0.35) + (np.pi / 2 if rng.random() < 0.5 else 0.0)
    proj = xx * np.cos(th) + yy * np.sin(th)
    streak = ((proj / (5.0 * s)) % 1 < 0.5).astype(np.float32) * 0.016 - 0.008
    heading = th + rng.uniform(-0.2, 0.2)
    mask = np.zeros((h, w), np.uint8)
    for _ in range(9):
        pts = _walk(rng, w, h, 4, rng.uniform(450, 750) * s, heading=heading + rng.uniform(-0.35, 0.35), turn=0.22)
        cv2.polylines(mask, [pts], False, 255, int(rng.uniform(40, 95) * s), cv2.LINE_AA)
    small = cv2.resize(mask, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    soft = cv2.resize(cv2.GaussianBlur(small.astype(np.float32) / 255.0, (0, 0), max(1.0, 4.0 * s)),
                      (w, h), interpolation=cv2.INTER_LINEAR)
    rgb *= (1 - soft * 0.50)[..., None]
    rgb += (soft * streak)[..., None]
    rgb += (soft ** 2)[..., None] * np.asarray((0.042, 0.036, 0.056), np.float32)
    rm = soft > 0.35
    if rm.any():
        R[rm] = _tiers(proj[rm], _L_R, 6, 7)
    CC[rm] = 210
    M[rm] = 12

    for _ in range(13):
        yb = rng.uniform(0.02, 0.95) * h
        bh = rng.uniform(34, 72) * s
        cell = rng.uniform(8, 16) * s
        tilt = rng.uniform(-0.35, 0.35)
        ry0 = int(np.clip(yb - bh / 2 - abs(tilt) * w - 2, 0, h))
        ry1 = int(np.clip(yb + bh / 2 + abs(tilt) * w + 2, 0, h))
        if ry1 <= ry0:
            continue
        xs, ys = xx[ry0:ry1], yy[ry0:ry1]
        ymid = ys - (yb + tilt * xs)
        inband = np.abs(ymid) < bh / 2
        stretch = 1.0 + rng.uniform(1.4, 2.8) * np.clip(xs / w, 0, 1)
        uu = np.floor((xs / (cell * stretch)) + 0.35 * np.sin(ys / (70 * s)))
        vv = np.floor(ymid / cell)
        chk = ((uu + vv) % 2 < 1) & inband
        dkc = inband & ~chk
        rgb[ry0:ry1][chk] = (0.90, 0.90, 0.86)
        rgb[ry0:ry1][dkc] = (0.050, 0.050, 0.060)
        R[ry0:ry1][chk] = 40
        R[ry0:ry1][dkc] = 205
        CC[ry0:ry1][inband] = 34
        M[ry0:ry1][chk] = 104

    tree_pts = _scatter(rng, 56, w, h, 135 * s, margin=0.06)
    lamp_rows = [((1.00, 0.72, 0.20), 8, 2), ((1.00, 0.72, 0.20), 12, 3),
                 ((0.25, 1.00, 0.35), 12, 1), ((1.00, 0.16, 0.14), 12, 1)]
    pole = np.zeros((h, w), np.uint8)
    scales = [rng.uniform(0.22, 0.52) for _ in tree_pts]
    for (tx, ty), sc in zip(tree_pts, scales):
        cv2.line(pole, (int(tx), int(ty) - int(20 * s * sc)), (int(tx), int(ty) + int(300 * s * sc)), 255, max(1, int(2 * s)))
    pm = pole > 0
    rgb[pm] = np.maximum(rgb[pm], (0.14, 0.15, 0.18))
    M[pm] = 181
    for (tx, ty), sc in zip(tree_pts, scales):
        drop = 0
        for rowi, (col, rr, cnt) in enumerate(lamp_rows):
            for _ in range(cnt):
                for dxs in (-1, 1):
                    lx, ly = tx + dxs * 17 * s * sc, ty + drop
                    rr2 = max(1.6, rr * s * sc)
                    win = _sub(shape, lx, ly, rr2 * 6)
                    if win is None:
                        continue
                    y0, y1, x0, x1 = win
                    rad, _a = _polar(y0, y1, x0, x1, lx, ly)
                    disc = rad < rr2
                    halo = np.exp(-rad / (rr2 * 2.1))
                    sub = rgb[y0:y1, x0:x1]
                    sub[disc] = np.asarray(col, np.float32) * 0.55 + 0.45
                    sub += halo[..., None] * np.asarray(col, np.float32) * 0.55
                    R[y0:y1, x0:x1][disc] = 12
                    CC[y0:y1, x0:x1][disc] = 16
                    M[y0:y1, x0:x1][disc] = 67
                    ry0 = int(np.clip(ly + rr2 * 2, 0, h))
                    ry1 = int(np.clip(ly + rr2 * 2 + 430 * s * sc, 0, h))
                    xw0 = int(np.clip(lx - 5 * rr2, 0, w))
                    xw1 = int(np.clip(lx + 5 * rr2, 0, w))
                    if rowi > 0 and ry1 > ry0 and xw1 > xw0:
                        gx = np.exp(-((np.arange(xw0, xw1) - lx) ** 2) / (2 * (rr2 * 1.4) ** 2)).astype(np.float32)
                        full = max(1.0, 430 * s * sc)
                        drop0 = float(ry0 - (ly + rr2 * 2))
                        gy = (0.30 * np.clip(1 - (drop0 + np.arange(ry1 - ry0)) / full, 0, 1)).astype(np.float32)
                        refl = gy[:, None] * gx[None, :]
                        rgb[ry0:ry1, xw0:xw1] += refl[..., None] * np.asarray(col, np.float32)
                        ccw = CC[ry0:ry1, xw0:xw1]
                        CC[ry0:ry1, xw0:xw1] = np.where(refl > 0.02, np.minimum(ccw, 90.0), ccw)
                drop += rr * s * sc * 2.6

    beam_glow = np.zeros((h, w, 3), np.float32)
    for _ in range(16):
        by = rng.uniform(0.02, 0.98) * h
        col = (1.0, 0.15, 0.15) if rng.random() < 0.5 else (0.15, 0.9, 1.0)
        pulse = (0.55 + 0.45 * np.sin(xx[0] / (150 * s) + rng.uniform(0, 6))) * rng.uniform(0.6, 1.0)
        yl = int(np.clip(by, 1, h - 2))
        t2 = max(1, int(1.5 * s))
        addv = pulse[None, :, None] * np.asarray(col, np.float32)
        rgb[yl - t2:yl + t2] += addv * 0.9
        beam_glow[yl - t2:yl + t2] += addv
        bm2 = pulse > 0.3
        M[yl - t2:yl + t2, bm2] = 250
        R[yl - t2:yl + t2, bm2] = 25
        ex = int(rng.uniform(0.05, 0.95) * w)
        cv2.rectangle(rgb, (ex - int(6 * s), yl - int(9 * s)), (ex + int(6 * s), yl + int(9 * s)),
                      (0.32, 0.34, 0.38), -1)
        M[yl - int(9 * s):yl + int(9 * s), ex - int(6 * s):ex + int(6 * s)] = 219
    rgb += cv2.GaussianBlur(beam_glow, (0, 0), 5 * s) * 0.55

    rgb = np.clip(rgb, 0, 1)
    return {"rgb": rgb, "spec": _spec_pack(M, R, CC)}


# ============================================================================ 22 ★ BURNOUT RING
# FIELD of donut scars: ~106 overlapping annuli (46 dim ghost + 60 live) with 4-9px tread
# blocks, blacklight-fresh violet vs old-gray alternation, cyan sheen crests, underglow pools,
# smooth smoke curls, anchored sparks. Asphalt palimpsest, edge to edge.
@_structure("burnout_ring")
def _b_burnout_ring(shape, seed):
    h, w = shape
    s = h / 2048.0
    rng = _rng(seed * 401 + 22)
    rgb, pools, _ = _asphalt(shape, seed + 5, base=(0.034, 0.039, 0.056), speckle=0.07, amp=0.022)
    rgb += _sheen(shape, seed * 557 + 13, 1.1, 400 * s, 0.15)[..., None] * np.asarray((0.75, 0.60, 1.0), np.float32)

    M = _tiers(pools, _L_M, 0, 1).copy()
    R = _tiers(1 - pools, _L_R, 5, 7).copy()
    CC = _tiers(pools, _L_C, 5, 7).copy()

    ring_specs = []
    ghosts = _scatter(rng, 70, w, h, 100 * s, margin=0.10)
    for (cx, cy) in ghosts:
        ring_specs.append((cx, cy, rng.uniform(40, 130) * s, rng.uniform(12, 30) * s, 0.20, 0.48))
    mains = _scatter(rng, 86, w, h, 112 * s, margin=0.10)
    for ri, (cx, cy) in enumerate(mains):
        fresh = (ri % 2) * 0.5 + rng.random() * 0.5
        ring_specs.append((cx, cy, rng.uniform(45, 165) * s, rng.uniform(14, 44) * s, fresh, 1.0))

    for (cx, cy, Rr, bw, fresh, dim) in ring_specs:
        win = _sub(shape, cx, cy, Rr + bw)
        if win is None:
            continue
        y0, y1, x0, x1 = win
        rad, ang = _polar(y0, y1, x0, x1, cx, cy)
        a0 = rng.uniform(0, 2 * np.pi)
        span = rng.uniform(0.62, 1.0) * 2 * np.pi
        u = ((ang - a0) % (2 * np.pi)) / (2 * np.pi)
        aspan = u < span / (2 * np.pi)
        fade = np.clip((span / (2 * np.pi) - u) / 0.10, 0, 1) * np.clip(u / 0.06, 0, 1) * dim
        band = (np.abs(rad - Rr) < bw / 2) & aspan
        rowpos = (rad - (Rr - bw / 2)) / bw
        na = max(14, int(2 * np.pi * Rr / (9 * s)))
        blocks = np.zeros_like(band)
        pb = np.zeros_like(rad)
        ring_i = int((cx * 7 + cy * 13) % 977)
        rows_spec = ((0.00, 0.30, 0.0, 0.62), (0.42, 0.58, 0.5, 0.55), (0.70, 1.00, 0.25, 0.62))             if dim >= 1.0 else ((0.08, 0.92, 0.0, 0.58),)
        for (r0, r1, off, duty) in rows_spec:
            rowm = (rowpos >= r0) & (rowpos <= r1)
            bidx = np.floor(u * na + off)
            blk = ((u * na + off) % 1) < duty
            m = band & rowm & blk
            blocks |= m
            pb[m] = (np.mod(bidx * 7919 + ring_i, 8) / 7.0)[m]
        sub = rgb[y0:y1, x0:x1]
        bm = blocks & (fade > 0.03)
        gm = band & ~blocks & (fade > 0.03)
        bd = np.abs(rad - Rr)
        if fresh > 0.5:
            body = np.asarray((0.34, 0.07, 0.50), np.float32)
            sub[bm] = np.maximum(sub[bm], body * (0.45 + 0.95 * pb[bm, None]) * (0.35 + 0.65 * fade[bm, None]))
            hotb = bm & (pb > 0.85)
            sub[hotb] = (0.85, 0.55, 0.95)
            R[y0:y1, x0:x1][hotb] = 61
            sub[gm] = (0.030, 0.020, 0.050)
            edge0 = np.clip(((Rr + bw) - rad) / (0.30 * Rr), 0, 1)
            halo = np.exp(-bd / (bw * 1.3)) * fade * (edge0 * edge0 * (3 - 2 * edge0))
            sub += halo[..., None] * np.asarray((0.80, 0.10, 0.72), np.float32) * 0.45
            M[y0:y1, x0:x1][bm] = _tiers(pb, _L_M, 2, 6)[bm]
            CC[y0:y1, x0:x1][bm] = _tiers(pb, _L_C, 3, 5)[bm]
        else:
            body = np.asarray((0.190, 0.200, 0.235), np.float32)
            sub[bm] = np.maximum(sub[bm], body * (0.55 + 0.65 * pb[bm, None]) * (0.35 + 0.65 * fade[bm, None]))
            sub[gm] *= 0.80
            sheen = (np.abs(rad - (Rr - bw / 2)) < max(1.5, 2.2 * s)) & aspan & (fade > 0.05)
            sub[sheen] = np.maximum(sub[sheen], (0.14, 0.50, 0.58))
            M[y0:y1, x0:x1][bm] = _tiers(pb, _L_M, 0, 3)[bm]
            CC[y0:y1, x0:x1][bm] = 205
            M[y0:y1, x0:x1][sheen] = 181
            R[y0:y1, x0:x1][sheen] = 30
            CC[y0:y1, x0:x1][sheen] = 34
        R[y0:y1, x0:x1][bm] = _tiers(pb, _L_R, 5, 7)[bm]
        R[y0:y1, x0:x1][gm] = 240
        if dim >= 1.0:
            edge = np.clip(((Rr + bw) - rad) / (0.35 * Rr), 0, 1)
            edge = edge * edge * (3 - 2 * edge)
            pool = np.exp(-(rad / (Rr * 0.60)) ** 2) * edge * (0.10 if fresh > 0.5 else 0.07)
            pcol = np.asarray((0.75, 0.12, 0.70), np.float32) if fresh > 0.5 else np.asarray((0.12, 0.58, 0.78), np.float32)
            sub += pool[..., None] * pcol

    yy = np.mgrid[0:h, 0:w][0].astype(np.float32)
    tcol = (yy / h)[..., None]
    wisp_cols = np.asarray((0.85, 0.12, 0.80), np.float32)[None, None, :] * (1 - tcol) + \
        np.asarray((0.10, 0.75, 0.95), np.float32)[None, None, :] * tcol
    for wclass, (width, alpha) in enumerate(((14 * s, 0.30), (26 * s, 0.20), (42 * s, 0.14))):
        mask = np.zeros((h, w), np.uint8)
        for _ in range(10):
            pts = _chaikin(_walk(rng, w, h, 9, 200 * s, turn=0.9), 3)
            cv2.polylines(mask, [pts], False, 255, 1, cv2.LINE_AA)
        d = _dt(mask)
        rib = np.exp(-(d / width) ** 2).astype(np.float32)
        rgb += rib[..., None] * wisp_cols * alpha
        if wclass == 0:
            core = np.clip((rib - 0.72) / 0.28, 0, 1)
            rgb += core[..., None] * np.asarray((0.9, 0.85, 0.95), np.float32) * 0.18
        wm = rib > 0.4
        CC[wm] = np.minimum(CC[wm], 150)

    centers = mains
    for _ in range(30):
        if not centers:
            break
        cx0, cy0 = centers[int(rng.integers(0, len(centers)))]
        aa = rng.uniform(0, 2 * np.pi)
        rr0 = rng.uniform(0.4, 1.15) * 150 * s
        px, py = int(cx0 + np.cos(aa) * rr0), int(cy0 + np.sin(aa) * rr0)
        if not (0 <= px < w and 0 <= py < h):
            continue
        ln = int(rng.uniform(4, 10) * s)
        cv2.line(rgb, (px, py), (int(px + np.cos(aa) * ln), int(py + np.sin(aa) * ln)),
                 (1.0, 0.75, 0.30), 1, cv2.LINE_AA)
        M[max(0, py - 1):py + 2, max(0, px - 1):px + 2] = 250

    rgb = np.clip(rgb, 0, 1)
    return {"rgb": rgb, "spec": _spec_pack(M, R, CC)}


# ============================================================================ public API

@lru_cache(maxsize=4)
def build(key, shape, seed):
    fn = _BUILDERS.get(key)
    if fn is None:
        raise KeyError(f"neon_math_v2: unknown structure '{key}'")
    out = fn(tuple(shape), int(seed))
    out["rgb"] = np.clip(np.asarray(out["rgb"], np.float32), 0, 1)
    out["spec"] = np.asarray(out["spec"], np.float32)
    return out


class _LazyMap(dict):
    def __init__(self, kind):
        super().__init__({k: None for k in _BUILDERS})
        self._kind = kind

    def __getitem__(self, key):
        def fn(shape, seed, _k=key):
            b = build(_k, tuple(shape), int(seed))
            return b["rgb"] if self._kind == "rgb" else b["spec"]
        return fn


NEON_STRUCTURES = _LazyMap("rgb")
NEON_SPECS = _LazyMap("spec")
