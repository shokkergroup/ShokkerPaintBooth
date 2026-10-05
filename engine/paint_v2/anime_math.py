"""ANIME MATH v2 — the ★ ANIME INSPIRED 25-structure generative library.

[SPB ANIME OVERHAUL 2026-08-25 — owner mandate: "expand the 19 we have to 25 designs and make
them mind melting… NO REPEATS, NO LAZINESS."] Full rewrite of the 2026-06-19 8-structure module
(which rendered at 760–1152 px then upscaled — mush — and had no married specs). Ledger of all
25 mechanisms + collision watchlist: docs/ANIME_OVERHAUL_2026-08-25.md.

Contract per structure:
  _b_<key>(shape, seed) -> {'rgb': float32 (h,w,3) in 0..1, 'spec': float32 (h,w,3) in 0..255 (M,R,CC)}
computed in ONE pass from shared geometry (married spec — the catalog fingerprint 'trace' is high
by construction). `build(key, shape, seed)` caches so paint_fn+spec_fn share one compute.
ALL feature sizes scale with h/2048: native-resolution generation at any size, fine detail
8–32 px at 2048 (owner Universal Law), no upscale softening. Budget ≤ ~2.5 s @2048 per structure.

Public: ANIME_STRUCTURES[key](shape, seed)->rgb, ANIME_SPECS[key](shape, seed)->spec,
COVERAGE_EXEMPT / FINE_DETAIL_EXEMPT (deliberate, documented opt-outs — currently empty).
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
    """Value-noise layer: random grid upscaled smoothly to shape."""
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
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / max(hi - lo, 1e-6)


def _mg(shape):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return yy, xx


def _band_ink(band_id, ksz=2):
    """Ink lines where an integer band field changes (Sobel edge of band id)."""
    gx = cv2.Sobel(band_id.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(band_id.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    ink = np.clip(np.sqrt(gx * gx + gy * gy), 0, 1)
    if ksz > 1:
        ink = cv2.dilate(ink, np.ones((ksz, ksz), np.float32))
    return ink


def _glow(img, sigma, gain):
    """Additive bloom of the bright content."""
    b = cv2.GaussianBlur(img, (0, 0), max(0.6, sigma))
    return np.clip(img + b * gain, 0, 1)


def _ramp(t, stops):
    """Piecewise-linear colour ramp through N RGB stops, t in 0..1."""
    stops = np.asarray(stops, np.float32)
    n = len(stops) - 1
    t = np.clip(t, 0, 1) * n
    i = np.clip(np.floor(t).astype(np.int32), 0, n - 1)
    f = (t - i)[..., None]
    return stops[i] * (1 - f) + stops[i + 1] * f


def _spec_pack(M, R, CC):
    """Stack M/R/CC planes -> float32 (h,w,3) 0..255 with engine-safe floors (CC>=16 unless 0-15 'none')."""
    M = np.clip(np.asarray(M, np.float32), 0, 255)
    R = np.clip(np.asarray(R, np.float32), 6, 255)
    CC = np.clip(np.asarray(CC, np.float32), 16, 255)
    return np.stack([M, R, CC], axis=2)


def _flake(built, shape, seed, amp=0.10, dens=1.0, amp_add=0.02):
    """Micro-flake clear layer over paint+spec: +-amp multiplicative luma glitter PLUS an
    additive +-amp_add term (so dark designs still carry 1-px energy), sparse 1-px chrome
    flecks (M252/R8) and dead pits (M2/R235) -> automotive sparkle + full spec spans."""
    h, w = shape
    r = _rng(seed * 4241 + 99)
    jit = r.random((h, w)).astype(np.float32)
    rgb = np.clip(built["rgb"] * (1.0 + (jit[..., None] - 0.5) * 2 * amp)
                  + (jit[..., None] - 0.5) * 2 * amp_add, 0, 1)
    fl = jit > 1.0 - 0.016 * dens
    pit = jit < 0.010 * dens
    rgb[fl] = np.minimum(rgb[fl] * 1.5 + 0.22, 1.0)
    rgb[pit] *= 0.45
    spec = built["spec"].copy()
    spec[..., 0][fl] = 252.0
    spec[..., 1][fl] = 8.0
    spec[..., 2][fl] = 16.0
    spec[..., 0][pit] = 2.0
    spec[..., 1][pit] = 235.0
    spec[..., 2][pit] = 245.0
    return {"rgb": rgb.astype(np.float32), "spec": spec}


def _pop(rgb, shape, seed, sat=1.15, grain=0.035):
    """Anime pop pass: saturation push + 1-px luma grain (vivid cel colour + micro fine energy)."""
    mean = rgb.mean(axis=2, keepdims=True)
    out = np.clip(mean + (rgb - mean) * sat, 0, 1)
    if grain > 0:
        h, w = shape
        g = (_vgrid(shape, seed * 977 + 13, h // 2, w // 2) - 0.5) * 2 * grain
        out = np.clip(out + g[..., None], 0, 1)
    return out.astype(np.float32)


# 8-tier ladders (owner Rule 2: MANY distinct spec/brightness values, not 2)
_LADDER8 = np.array([0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], np.float32)


def _tier8(r, lo=0.0, hi=1.0):
    """Pick one of 8 ladder values scaled into [lo,hi] (per-feature diversity)."""
    return float(lo + (hi - lo) * _LADDER8[int(r.integers(0, 8))])


# ============================================================================ 01 cel_terminator
# MECHANISM: multi-light posterized warp-field cel bands + SDF ink terminators + hatch penumbra
# + chrome toon highlight streaks. (anime_cel_shade_chrome)

@_structure("cel_terminator")
def _b_cel_terminator(shape, seed):
    h, w = shape
    S = h / 2048.0
    yy, xx = _mg(shape)
    # domain-warped luminous field lit by TWO rigs (directional + off-corner radial)
    warp = _fbm(shape, seed * 3 + 11, octaves=4, freq=4.0)
    wx = cv2.Sobel(warp, cv2.CV_32F, 1, 0, ksize=5)
    wy = cv2.Sobel(warp, cv2.CV_32F, 0, 1, ksize=5)
    l1 = (1.0 - yy / h) * 0.55 + (xx / w) * 0.45
    cxr, cyr = w * 1.15, -h * 0.2
    l2 = 1.0 - np.sqrt((xx - cxr) ** 2 + (yy - cyr) ** 2) / (1.6 * h)
    light = 0.58 * l1 + 0.42 * l2 + 90.0 * S * (wx + wy) + 0.22 * (_fbm(shape, seed * 5 + 3, 3, 7.0) - 0.5)
    light = _norm(cv2.GaussianBlur(light, (0, 0), 2.0 * S + 0.5))
    BANDS = 6
    q = np.clip(np.floor(light * BANDS), 0, BANDS - 1)
    t = q / (BANDS - 1)
    # cool body -> WARM rim highlight (the anime twilight lighting cliché; kills the topo-map read)
    pal = [(0.05, 0.04, 0.16), (0.13, 0.13, 0.38), (0.24, 0.29, 0.62),
           (0.46, 0.51, 0.80), (0.80, 0.68, 0.82), (1.00, 0.87, 0.70)]
    rgb = _ramp(t, pal)
    # double linework: bold ink at 6-band terminators + fine half-tone ink at 12-band sub-steps
    ink = _band_ink(q, max(2, int(4 * S)))
    q12 = np.clip(np.floor(light * 12), 0, 11)
    ink_fine = _band_ink(q12, 1) * 0.42
    # penumbra hatching: diagonal gratings hugging the DARK side of each terminator
    edge_d = cv2.distanceTransform((ink < 0.5).astype(np.uint8), cv2.DIST_L2, 3)
    near = np.clip(1.0 - edge_d / max(1.0, 26.0 * S), 0, 1)
    ph = 7.0 * S + 0.35
    hatch1 = ((np.sin((xx + yy) / ph) > 0.35) & (near > 0.25) & (t < 0.55)).astype(np.float32)
    hatch2 = ((np.sin((xx - yy) / (ph * 0.8)) > 0.55) & (near > 0.45) & (t < 0.30)).astype(np.float32)
    hatch = np.clip(hatch1 * 0.5 + hatch2 * 0.5, 0, 1) * (1.0 - ink)
    # chrome toon highlight: horizontal-streaked white core on the hottest cells + star glints
    hot = (light > 0.87).astype(np.float32)
    streak = cv2.blur(hot, (max(3, int(90 * S)), max(1, int(6 * S))))
    streak = np.clip(streak * 2.4 - 0.45, 0, 1)
    r = _rng(seed * 17 + 5)
    glint = np.zeros((h, w), np.float32)
    ys, xs = np.where(hot > 0.5)
    if len(ys):
        for _ in range(min(220, max(30, int(160 * S * S)))):
            i = int(r.integers(0, len(ys)))
            gy, gx = int(ys[i]), int(xs[i])
            L = int(6 + 16 * r.random() * S + 2)
            cv2.line(glint, (gx - L, gy), (gx + L, gy), 1.0, 1, cv2.LINE_AA)
            cv2.line(glint, (gx, gy - L), (gx, gy + L), 1.0, 1, cv2.LINE_AA)
    grain = (_vgrid(shape, seed * 29 + 7, h // 2, w // 2) - 0.5) * 0.045
    ink_c = np.array([0.02, 0.02, 0.06], np.float32)
    rgb = rgb * (1 - ink[..., None]) + ink_c * ink[..., None]
    rgb = rgb * (1 - ink_fine[..., None] * 0.55)
    rgb = rgb * (1 - hatch[..., None] * 0.48)
    rgb = np.clip(rgb + streak[..., None] * np.array([0.5, 0.55, 0.6]) + glint[..., None] * 0.75 + grain[..., None], 0, 1)
    rgb = _glow(rgb, 6 * S + 1, 0.10)
    rgb = _pop(rgb, shape, seed, sat=1.22, grain=0.012)
    # ---- married spec: per-band metal ladder; ink = dead dielectric gaps; highlight = chrome
    m_lad = np.array([12, 52, 96, 148, 205, 250], np.float32)
    r_lad = np.array([210, 55, 165, 40, 110, 20], np.float32)   # parity lacquer: alternating matte/gloss cels
    c_lad = np.array([225, 130, 16, 195, 70, 150], np.float32)  # period-3 lacquer cels (decorrelated from M AND R)
    qi = q.astype(np.int32)
    M = m_lad[qi] + (_vgrid(shape, seed * 31 + 9, 96, 96) - 0.5) * 26
    R = r_lad[qi] + (_vgrid(shape, seed * 37 + 4, 128, 128) - 0.5) * 30
    CC = c_lad[qi]
    M = M * (1 - ink) + 14 * ink
    R = R * (1 - ink) + 218 * ink
    CC = CC * (1 - ink) + 236 * ink
    R = R + hatch * 52
    hotm = np.clip(streak + glint, 0, 1)
    M = M * (1 - hotm) + 252 * hotm
    R = R * (1 - hotm) + 9 * hotm
    CC = CC * (1 - hotm) + 16 * hotm
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(M, R, CC)}


# ============================================================================ 02 speedline_storm
# MECHANISM: 3–5 focal radial line systems INTERFERING; concentration-density waves; per-line
# weight/tier; dash breakup. (anime_speed_lines)

@_structure("speedline_storm")
def _b_speedline_storm(shape, seed):
    h, w = shape
    S = h / 2048.0
    yy, xx = _mg(shape)
    r = _rng(seed * 7 + 3)
    base = np.zeros((h, w, 3), np.float32) + np.array([0.03, 0.04, 0.22], np.float32)
    veil = _fbm(shape, seed * 11 + 2, 3, 5.0)
    base += (veil[..., None] - 0.5) * np.array([0.05, 0.05, 0.09])
    line_acc = np.zeros((h, w), np.float32)     # white line intensity
    acc_accent = np.zeros((h, w), np.float32)   # crimson accent subset
    tier_map = np.zeros((h, w), np.float32)     # per-line spec tier carrier
    systems = 4
    # ONE shared density field for all systems (per-system fbm was ~0.5s of the 2048 budget)
    dens_shared = np.clip(1.55 * _norm(_fbm(shape, seed * 13 + 5, 3, 6.0)) - 0.28, 0, 1) ** 1.5
    for si in range(systems):
        fx = (r.random() * 1.7 - 0.35) * w
        fy = (r.random() * 1.7 - 0.35) * h
        n_lines = int([90, 150, 230, 330][si % 4] * (0.8 + 0.4 * r.random()))
        dyf = yy - fy
        dxf = xx - fx
        th = np.arctan2(dyf, dxf)
        rr = np.sqrt(dxf * dxf + dyf * dyf) / h
        u = (th * (n_lines / (2 * np.pi))) + n_lines * 0.5
        fr = np.abs(u - np.round(u))            # 0 at line centre
        idx = np.round(u).astype(np.int32)
        hash01 = ((idx * 40503 + si * 97 + seed) & 4095).astype(np.float32) / 4096.0
        dens = np.roll(dens_shared, (si * 353) % h, axis=0)
        wtier = _LADDER8[(hash01 * 7.999).astype(np.int32)]
        half_w = (0.05 + 0.40 * wtier) * dens
        core = np.clip(1.0 - fr / np.maximum(half_w, 1e-4), 0, 1) ** 1.6
        # radial fade-in + dash breakup
        core *= np.clip((rr - 0.05) * 9.0, 0, 1)
        dash = (np.abs(((rr * (44 + 18 * hash01)) + hash01 * 7) % 1.0) > 0.085).astype(np.float32)
        core *= dash * (hash01 > 0.10)
        acc = core * (hash01 < 0.38)
        line_acc = 1.0 - (1.0 - line_acc) * (1.0 - core * 0.92)      # screen blend
        acc_accent = np.maximum(acc_accent, acc)
        tier_map = np.maximum(tier_map, core * wtier)
    ghost = cv2.GaussianBlur(line_acc, (0, 0), 3.5 * S + 0.6) * 0.5
    lines = np.clip(line_acc + ghost, 0, 1)
    white = np.array([0.96, 0.97, 1.0], np.float32)
    crimson = np.array([0.95, 0.12, 0.22], np.float32)
    rgb = base * (1 - lines[..., None] * 0.97)
    # pale per-line tints (cyan/pink/gold) so the storm reads vivid, not gray
    tintf = np.stack([0.86 + 0.14 * np.cos(tier_map * 21), 0.84 + 0.16 * np.sin(tier_map * 13),
                      0.82 + 0.18 * np.cos(tier_map * 34)], axis=2)
    rgb += white * tintf * (lines * (1 - acc_accent))[..., None]
    rgb += crimson * np.clip(acc_accent * 1.2, 0, 1)[..., None]
    speck = (_vgrid(shape, seed * 23 + 9, h // 3, w // 3) > 0.986).astype(np.float32) * 0.5
    rgb = np.clip(rgb + speck[..., None] * 0.35, 0, 1)
    rgb = _pop(rgb, shape, seed, sat=1.12, grain=0.028)
    # ---- married spec: chrome pinstripes on rough dark bed; accent lines warmer/rougher
    lm = np.clip(line_acc, 0, 1)
    M = 22 + lm * (196 + 56 * tier_map)
    M = np.where(acc_accent > 0.25, 252.0, M)
    R = 196 - lm * (150 + 40 * tier_map) + ghost * 60
    R = np.where(acc_accent > 0.25, 46.0, R)
    CC = 205 - lm * 178
    CC = np.where(acc_accent > 0.25, 38.0, CC)
    R += (veil - 0.5) * 34
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(M, R, CC)}


# ============================================================================ 03 shoujo_sparkle
# MECHANISM: star-SDF scatter (4/5/6-point) + bubble bokeh rings + prism cross-flares + glitter
# dust, 8-tier ladders everywhere. (anime_sparkle_burst)

def _star_pts(cx, cy, n, r_out, r_in, rot):
    ang = rot + np.arange(2 * n) * (np.pi / n)
    rad = np.where(np.arange(2 * n) % 2 == 0, r_out, r_in)
    return np.stack([cx + rad * np.cos(ang), cy + rad * np.sin(ang)], axis=1).astype(np.int32)


@_structure("shoujo_sparkle")
def _b_shoujo_sparkle(shape, seed):
    h, w = shape
    S = h / 2048.0
    yy, xx = _mg(shape)
    r = _rng(seed * 5 + 1)
    neb = _fbm(shape, seed * 3 + 8, 4, 3.0)
    grad = _ramp((yy / h + 0.35 * (neb - 0.5)),
                 [(0.14, 0.07, 0.30), (0.24, 0.11, 0.42), (0.12, 0.14, 0.38), (0.07, 0.06, 0.22)])
    wisp = np.clip(_fbm(shape, seed * 11 + 6, 4, 6.0) * 1.6 - 0.75, 0, 1)
    rgb = np.clip(grad + wisp[..., None] * np.array([0.22, 0.12, 0.26]), 0, 1)
    glowbuf = np.zeros((h, w, 3), np.float32)
    specM = 22 + _norm(neb) * 130
    specR = 150 + (_fbm(shape, seed * 7 + 2, 4, 9.0) - 0.5) * 90
    specC = 60 + _norm(neb) * 130 + (wisp - 0.5) * 40   # clearcoat follows the nebula (wide CC range)
    tints = np.array([(1.0, 0.72, 0.85), (1.0, 0.92, 0.62), (0.62, 0.94, 1.0),
                      (0.80, 0.70, 1.0), (1.0, 1.0, 1.0), (0.95, 0.62, 0.75),
                      (0.70, 1.0, 0.85), (1.0, 0.82, 0.95)], np.float32)
    # glitter dust (2–5 px)
    n_dust = max(300, int(4200 * S * S))
    for _ in range(n_dust):
        x, y = int(r.random() * w), int(r.random() * h)
        b = _tier8(r, 0.35, 1.0)
        c = tints[int(r.integers(0, len(tints)))] * b
        cv2.circle(rgb, (x, y), max(1, int((1 + 1.6 * r.random()) * S + 0.5)), tuple(map(float, c)), -1, cv2.LINE_AA)
        cv2.circle(specM, (x, y), max(1, int(2 * S)), 150 + 100 * b, -1)
        cv2.circle(specR, (x, y), max(1, int(2 * S)), 20 + 90 * (1 - b), -1)
    # 4-point stars (10–34 px) with soft glow
    n4 = max(90, int(640 * S * S))
    for _ in range(n4):
        x, y = int(r.random() * w), int(r.random() * h)
        ro = (10 + 24 * r.random()) * S + 2
        b = _tier8(r, 0.45, 1.0)
        c = tints[int(r.integers(0, len(tints)))] * b
        pts = _star_pts(x, y, 4, ro, ro * 0.22, r.random() * np.pi)
        cv2.fillPoly(rgb, [pts], tuple(map(float, c)), cv2.LINE_AA)
        cv2.fillPoly(glowbuf, [pts], tuple(map(float, c * 0.9)), cv2.LINE_AA)
        cv2.fillPoly(specM, [pts], float(252), cv2.LINE_AA)
        cv2.fillPoly(specR, [pts], float(8 + 80 * (1 - b)), cv2.LINE_AA)
        cv2.fillPoly(specC, [pts], float(16 + 40 * (1 - b)), cv2.LINE_AA)
    # 5/6-point feature stars with cross flares (≤ 40 px cores — still field-scale)
    n56 = max(16, int(95 * S * S))
    for _ in range(n56):
        x, y = int(r.random() * w), int(r.random() * h)
        ro = (22 + 18 * r.random()) * S + 3
        n_p = 5 if r.random() < 0.5 else 6
        b = _tier8(r, 0.6, 1.0)
        c = tints[int(r.integers(0, len(tints)))] * b
        L = int(ro * (2.2 + 1.4 * r.random()))
        a0 = r.random() * np.pi
        for k in range(2):
            a = a0 + k * np.pi / 2
            dx, dy = int(L * np.cos(a)), int(L * np.sin(a))
            cv2.line(rgb, (x - dx, y - dy), (x + dx, y + dy), tuple(map(float, c * 0.55)), 1, cv2.LINE_AA)
            cv2.line(glowbuf, (x - dx, y - dy), (x + dx, y + dy), tuple(map(float, c * 0.5)), 1, cv2.LINE_AA)
        pts = _star_pts(x, y, n_p, ro, ro * 0.30, r.random() * np.pi)
        cv2.fillPoly(rgb, [pts], tuple(map(float, c)), cv2.LINE_AA)
        cv2.fillPoly(glowbuf, [pts], tuple(map(float, c)), cv2.LINE_AA)
        cv2.fillPoly(specM, [pts], float(252), cv2.LINE_AA)
        cv2.fillPoly(specR, [pts], float(6 + 40 * (1 - b)), cv2.LINE_AA)
        cv2.fillPoly(specC, [pts], float(16), cv2.LINE_AA)
    # bubble bokeh rings
    nb = max(24, int(150 * S * S))
    for _ in range(nb):
        x, y = int(r.random() * w), int(r.random() * h)
        rad = int((8 + 20 * r.random()) * S + 2)
        b = _tier8(r, 0.25, 0.8)
        c = tints[int(r.integers(0, len(tints)))] * b
        cv2.circle(rgb, (x, y), rad, tuple(map(float, c * 0.8)), 1, cv2.LINE_AA)
        cv2.ellipse(rgb, (x, y), (rad, rad), 0, 200, 250, tuple(map(float, np.minimum(c * 1.6, 1.0))), max(1, int(2 * S)), cv2.LINE_AA)
        cv2.circle(specM, (x, y), rad, float(40), 1, cv2.LINE_AA)
        cv2.circle(specR, (x, y), rad, float(24), 1, cv2.LINE_AA)
    rgb = np.clip(rgb + cv2.GaussianBlur(glowbuf, (0, 0), 7 * S + 1) * 0.55, 0, 1)
    for _ in range(max(260, int(1700 * S * S))):   # crisp glitter ON TOP of the bloom (1-2 px energy)
        x, y = int(r.random() * w), int(r.random() * h)
        b = _tier8(r, 0.5, 1.0)
        c = tints[int(r.integers(0, len(tints)))] * b
        cv2.circle(rgb, (x, y), max(1, int(1.1 * S)), tuple(map(float, c)), -1)
        cv2.circle(specM, (x, y), max(1, int(1.1 * S)), float(200 + 52 * b), -1)
        cv2.circle(specR, (x, y), max(1, int(1.1 * S)), float(8 + 40 * (1 - b)), -1)
    rgb = _pop(rgb, shape, seed, sat=1.18, grain=0.03)
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 04 inkbrush_strands
# MECHANISM: anisotropic streamline hair flow, angle-mapped sheen band, under-stroke crossover
# depth, flyaways. Spec painted per-segment in the SAME pass. (anime_gradient_hair)

@_structure("inkbrush_strands")
def _b_inkbrush_strands(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 9 + 4)
    ang_f = (_fbm(shape, seed * 3 + 6, 4, 3.0) - 0.5) * 2.6 + np.deg2rad(62.0)
    curl = (_fbm(shape, seed * 5 + 9, 3, 6.0) - 0.5) * 1.8
    rgb = _ramp(_fbm(shape, seed * 7 + 1, 3, 2.5),
                [(0.06, 0.03, 0.12), (0.10, 0.05, 0.20), (0.16, 0.07, 0.28)])
    specM = np.full((h, w), 34.0, np.float32)
    specR = np.full((h, w), 208.0, np.float32)
    specC = np.full((h, w), 218.0, np.float32)
    ramp_stops = [(1.00, 0.30, 0.78), (0.86, 0.22, 0.86), (0.55, 0.20, 0.92),
                  (0.30, 0.16, 0.72), (0.16, 0.10, 0.46)]
    sheen_dir = np.deg2rad(150.0)
    n_str = max(190, int(1250 * S))
    step = 3.2 * S + 0.8
    Hf, Wf = float(h - 2), float(w - 2)
    for _ in range(n_str):
        x = r.random() * w
        y = r.random() * h
        n_seg = int(60 + 90 * r.random())
        tier = _tier8(r, 0.45, 1.05)
        is_sheen_strand = r.random() < 0.06
        thick = max(1, int((1.4 + 3.4 * r.random()) * S + 0.5))
        base_c = np.array(_ramp(np.float32(y / h), ramp_stops), np.float32)
        pts = []
        for _ in range(n_seg):
            iy, ix = int(min(max(y, 0), Hf)), int(min(max(x, 0), Wf))
            a = float(ang_f[iy, ix] + curl[iy, ix])
            x += np.cos(a) * step
            y += np.sin(a) * step
            if x < -20 or x > w + 20 or y < -20 or y > h + 20:
                break
            pts.append((x, y, a))
        if len(pts) < 6:
            continue
        chunks = max(1, len(pts) // 9)
        for ci in range(chunks):
            seg = pts[ci * 9:ci * 9 + 10]
            if len(seg) < 2:
                continue
            p = np.array([(sx, sy) for sx, sy, _ in seg], np.int32)
            a_mid = seg[len(seg) // 2][2]
            sheen = float(np.exp(-((np.mod(a_mid - sheen_dir + np.pi, 2 * np.pi) - np.pi) ** 2) / 0.16))
            lum = tier * (0.75 + 0.75 * sheen)
            col = np.clip(base_c * lum + sheen * 0.55 * np.array([1.0, 0.95, 1.0]), 0, 1)
            if is_sheen_strand:
                col = np.clip(col + 0.35, 0, 1)
            # under-stroke (depth), then colour stroke
            cv2.polylines(rgb, [p], False, tuple(map(float, base_c * 0.16)), thick + max(1, int(2 * S)), cv2.LINE_AA)
            cv2.polylines(rgb, [p], False, tuple(map(float, col)), thick, cv2.LINE_AA)
            cv2.polylines(specM, [p], False, float(96 + 156 * min(1.0, tier) * (0.35 + 0.65 * sheen)), thick, cv2.LINE_AA)
            cv2.polylines(specR, [p], False, float(max(8.0, 88 - 80 * sheen - 30 * tier + 74 * ((ci + 1 + int(tier * 5)) % 2))), thick, cv2.LINE_AA)
            cv2.polylines(specC, [p], False, float(16 + 148 * ((ci + int(tier * 8)) % 2)), thick, cv2.LINE_AA)
    # flyaway wisps
    for _ in range(max(30, int(220 * S))):
        x, y = r.random() * w, r.random() * h
        p = []
        for _ in range(int(14 + 18 * r.random())):
            iy, ix = int(min(max(y, 0), Hf)), int(min(max(x, 0), Wf))
            a = float(ang_f[iy, ix] + curl[iy, ix]) + (r.random() - 0.5) * 0.8
            x += np.cos(a) * step * 0.8
            y += np.sin(a) * step * 0.8
            p.append((int(x), int(y)))
        if len(p) > 3:
            cv2.polylines(rgb, [np.array(p, np.int32)], False,
                          tuple(map(float, np.clip(np.array(ramp_stops[1]) * 1.25, 0, 1))), 1, cv2.LINE_AA)
    rgb = _glow(np.clip(rgb, 0, 1), 5 * S + 1, 0.08)
    rgb = _pop(rgb, shape, seed, sat=1.18, grain=0.05)
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 05 mecha_greeble
# MECHANISM: recursive CHAMFERED panel subdivision + rivets + vent louvers + warning chevrons +
# glowing seams + brushed anisotropic metal. (anime_mecha_plate)

@_structure("mecha_greeble")
def _b_mecha_greeble(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 11 + 6)
    rgb = np.zeros((h, w, 3), np.float32)
    specM = np.zeros((h, w), np.float32)
    specR = np.zeros((h, w), np.float32)
    specC = np.zeros((h, w), np.float32)
    glow = np.zeros((h, w, 3), np.float32)
    # recursive split
    rects = [(0, 0, w, h)]
    out_panels = []
    while rects:
        x0, y0, x1, y1 = rects.pop()
        rw, rh = x1 - x0, y1 - y0
        min_px = 150 * S + 24
        if (rw < min_px * 1.6 and rh < min_px * 1.6) or (rw < min_px or rh < min_px) or (len(out_panels) > 320):
            out_panels.append((x0, y0, x1, y1))
            continue
        if (rw > rh) or (rw == rh and r.random() < 0.5):
            cut = x0 + int(rw * (0.34 + 0.32 * r.random()))
            rects += [(x0, y0, cut, y1), (cut, y0, x1, y1)]
        else:
            cut = y0 + int(rh * (0.34 + 0.32 * r.random()))
            rects += [(x0, y0, x1, cut), (x0, cut, x1, y1)]
    grays = np.array([(0.26, 0.33, 0.46), (0.20, 0.26, 0.38), (0.34, 0.42, 0.55),
                      (0.14, 0.19, 0.30), (0.40, 0.48, 0.62), (0.24, 0.33, 0.48),
                      (0.30, 0.35, 0.44), (0.17, 0.24, 0.38)], np.float32)
    # Gundam hero-colour accent panels (the anime identity — not a gray cargo wall)
    heroes = np.array([(0.78, 0.10, 0.14), (0.10, 0.24, 0.72), (0.92, 0.92, 0.95),
                       (0.95, 0.72, 0.08), (0.05, 0.07, 0.12)], np.float32)
    seam_px = max(2, int(6 * S))
    bnoise = _fbm(shape, seed * 13 + 8, 3, 60.0, aniso=(1.0, 0.12))   # brushed anisotropic grain
    bnoise_v = _fbm(shape, seed * 17 + 2, 3, 60.0, aniso=(0.12, 1.0))
    for (x0, y0, x1, y1) in out_panels:
        rw, rh = x1 - x0, y1 - y0
        if r.random() < 0.52:
            tone = heroes[int(r.integers(0, len(heroes)))] * (0.95 + 0.25 * r.random())
        else:
            tone = grays[int(r.integers(0, len(grays)))] * (0.85 + 0.3 * r.random())
        ch = int(min(rw, rh) * (0.10 + 0.18 * r.random()))            # chamfer size
        which = int(r.integers(0, 4))
        pts = [(x0 + (ch if which == 0 else 0), y0), (x1 - (ch if which == 1 else 0), y0),
               (x1, y0 + (ch if which == 1 else 0)), (x1, y1 - (ch if which == 2 else 0)),
               (x1 - (ch if which == 2 else 0), y1), (x0 + (ch if which == 3 else 0), y1),
               (x0, y1 - (ch if which == 3 else 0)), (x0, y0 + (ch if which == 0 else 0))]
        poly = np.array(pts, np.int32)
        inset = seam_px
        cv2.fillPoly(rgb, [poly], tuple(map(float, tone * 0.35)), cv2.LINE_AA)    # seam bed
        shrink = np.array([(min(max(px, x0 + inset), x1 - inset), min(max(py, y0 + inset), y1 - inset)) for px, py in pts], np.int32)
        cv2.fillPoly(rgb, [shrink], tuple(map(float, tone)), cv2.LINE_AA)
        horiz = rw >= rh
        m_t = 150 + 90 * r.random()
        r_t = 34 + 80 * r.random()
        cv2.fillPoly(specM, [poly], float(40), cv2.LINE_AA)
        cv2.fillPoly(specR, [poly], float(225), cv2.LINE_AA)
        cv2.fillPoly(specC, [poly], float(238), cv2.LINE_AA)
        cv2.fillPoly(specM, [shrink], float(m_t), cv2.LINE_AA)
        cv2.fillPoly(specR, [shrink], float(r_t), cv2.LINE_AA)
        cv2.fillPoly(specC, [shrink], float(20 + 60 * r.random()), cv2.LINE_AA)
        gx0, gy0, gx1, gy1 = x0 + inset * 2, y0 + inset * 2, x1 - inset * 2, y1 - inset * 2
        gw, gh = gx1 - gx0, gy1 - gy0
        if gw < 20 * S or gh < 20 * S:
            continue
        kind = r.random()
        if kind < 0.24:      # rivet rows along edges
            n_riv = max(3, int((gw + gh) / (34 * S + 5)))
            for i in range(n_riv):
                t = (i + 0.5) / n_riv
                px_, py_ = (int(gx0 + t * gw), gy0 + int(6 * S)) if horiz else (gx0 + int(6 * S), int(gy0 + t * gh))
                rad = max(1, int(3.2 * S + 0.6))
                cv2.circle(rgb, (px_, py_), rad, tuple(map(float, tone * 1.5)), -1, cv2.LINE_AA)
                cv2.circle(rgb, (px_ + 1, py_ + 1), rad, tuple(map(float, tone * 0.4)), 1, cv2.LINE_AA)
                cv2.circle(specM, (px_, py_), rad, float(252), -1)
                cv2.circle(specR, (px_, py_), rad, float(28), -1)
        elif kind < 0.44:    # vent louvers
            n_l = max(3, int(gh / (16 * S + 3))) if horiz else max(3, int(gw / (16 * S + 3)))
            for i in range(n_l):
                if horiz:
                    ly = gy0 + int((i + 0.5) * gh / n_l)
                    cv2.line(rgb, (gx0 + int(8 * S), ly), (gx1 - int(8 * S), ly), tuple(map(float, tone * 0.25)), max(1, int(5 * S)), cv2.LINE_AA)
                    cv2.line(rgb, (gx0 + int(8 * S), ly - max(1, int(3 * S))), (gx1 - int(8 * S), ly - max(1, int(3 * S))), tuple(map(float, tone * 1.5)), 1, cv2.LINE_AA)
                    cv2.line(specR, (gx0, ly), (gx1, ly), float(200), max(1, int(5 * S)))
                else:
                    lx = gx0 + int((i + 0.5) * gw / n_l)
                    cv2.line(rgb, (lx, gy0 + int(8 * S)), (lx, gy1 - int(8 * S)), tuple(map(float, tone * 0.25)), max(1, int(5 * S)), cv2.LINE_AA)
                    cv2.line(rgb, (lx - max(1, int(3 * S)), gy0 + int(8 * S)), (lx - max(1, int(3 * S)), gy1 - int(8 * S)), tuple(map(float, tone * 1.5)), 1, cv2.LINE_AA)
                    cv2.line(specR, (lx, gy0), (lx, gy1), float(200), max(1, int(5 * S)))
        elif kind < 0.58:    # warning chevron strip
            band_h = max(6, int(min(gh, 26 * S + 4)))
            by = gy0 + int(r.random() * max(1, gh - band_h))
            stripe = np.zeros((band_h, gw, 3), np.float32)
            yy2, xx2 = np.mgrid[0:band_h, 0:gw].astype(np.float32)
            ph = ((xx2 + yy2) / max(2.0, 16 * S)) % 2 < 1
            stripe[ph] = (0.95, 0.75, 0.10)
            stripe[~ph] = (0.10, 0.10, 0.12)
            rgb[by:by + band_h, gx0:gx0 + gw] = stripe
            specM[by:by + band_h, gx0:gx0 + gw] = 58
            specR[by:by + band_h, gx0:gx0 + gw] = 130
            specC[by:by + band_h, gx0:gx0 + gw] = 80
        elif kind < 0.76:    # glowing seam segment
            gc = np.array([(0.15, 0.95, 1.0), (1.0, 0.45, 0.12), (0.55, 1.0, 0.25)][int(r.integers(0, 3))], np.float32) * 1.4
            if horiz:
                ly = int((gy0 + gy1) / 2)
                cv2.line(glow, (gx0, ly), (gx1, ly), tuple(map(float, gc)), max(1, int(3 * S)), cv2.LINE_AA)
                cv2.line(specM, (gx0, ly), (gx1, ly), float(252), max(1, int(3 * S)))
                cv2.line(specR, (gx0, ly), (gx1, ly), float(10), max(1, int(3 * S)))
                cv2.line(specC, (gx0, ly), (gx1, ly), float(16), max(1, int(3 * S)))
            else:
                lx = int((gx0 + gx1) / 2)
                cv2.line(glow, (lx, gy0), (lx, gy1), tuple(map(float, gc)), max(1, int(3 * S)), cv2.LINE_AA)
                cv2.line(specM, (lx, gy0), (lx, gy1), float(252), max(1, int(3 * S)))
                cv2.line(specR, (lx, gy0), (lx, gy1), float(10), max(1, int(3 * S)))
                cv2.line(specC, (lx, gy0), (lx, gy1), float(16), max(1, int(3 * S)))
        elif kind < 0.84:    # circular port rings
            n_p = 1 + int(r.integers(0, 3))
            for _ in range(n_p):
                px_ = int(gx0 + r.random() * gw)
                py_ = int(gy0 + r.random() * gh)
                rad = int((8 + 12 * r.random()) * S + 2)
                cv2.circle(rgb, (px_, py_), rad, tuple(map(float, tone * 0.3)), max(1, int(2 * S)), cv2.LINE_AA)
                cv2.circle(rgb, (px_, py_), max(1, rad - int(4 * S)), tuple(map(float, tone * 1.35)), 1, cv2.LINE_AA)
                cv2.circle(specM, (px_, py_), rad, float(252), max(1, int(2 * S)))
                cv2.circle(specR, (px_, py_), rad, float(30), max(1, int(2 * S)))
        else:                # scribe grid + ID plate
            n_s = 2 + int(r.integers(0, 3))
            for i in range(n_s):
                if horiz:
                    lx = gx0 + int((i + 1) * gw / (n_s + 1))
                    cv2.line(rgb, (lx, gy0), (lx, gy1), tuple(map(float, tone * 1.25)), 1, cv2.LINE_AA)
                else:
                    ly = gy0 + int((i + 1) * gh / (n_s + 1))
                    cv2.line(rgb, (gx0, ly), (gx1, ly), tuple(map(float, tone * 1.25)), 1, cv2.LINE_AA)
            pw, ph_ = int(min(gw * 0.4, 60 * S + 8)), int(min(gh * 0.3, 22 * S + 4))
            px_ = gx0 + int(r.random() * max(1, gw - pw))
            py_ = gy0 + int(r.random() * max(1, gh - ph_))
            cv2.rectangle(rgb, (px_, py_), (px_ + pw, py_ + ph_), tuple(map(float, tone * 1.6)), -1, cv2.LINE_AA)
            for i in range(max(2, pw // max(3, int(10 * S)))):
                tx = px_ + int((i + 0.5) * max(3, int(10 * S)))
                cv2.line(rgb, (tx, py_ + 2), (tx, py_ + ph_ - 2), tuple(map(float, tone * 0.5)), 1)
    # brushed anisotropic grain modulates colour + roughness per panel orientation
    rgb = np.clip(rgb * (0.92 + 0.16 * bnoise[..., None]), 0, 1)
    specR = np.clip(specR + (bnoise - 0.5) * 44 + (bnoise_v - 0.5) * 18, 6, 255)
    rgb = np.clip(rgb + cv2.GaussianBlur(glow, (0, 0), 9 * S + 1.2) * 0.9 + glow * 0.8, 0, 1)
    rgb = _pop(rgb, shape, seed, sat=1.14, grain=0.02)
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 06 sakura_hurricane
# MECHANISM: curl-advected petal storm; TRUE 5-notch petal polygons; 3 depth layers; wind
# streaks; two-tone petal shading. (anime_sakura_scatter)

def _petal_poly(cx, cy, L, W, ang):
    """Sakura petal: rounded teardrop with a V-notch at the tip."""
    t = np.array([0.0, 0.14, 0.30, 0.48, 0.66, 0.82, 0.90, 1.00, 0.90, 0.82, 0.66, 0.48, 0.30, 0.14], np.float32)
    wdt = np.array([0.06, 0.42, 0.75, 0.98, 0.92, 0.66, 0.38, 0.02, -0.38, -0.66, -0.92, -0.98, -0.75, -0.42], np.float32)
    xs = t * L
    ys = wdt * W * 0.5
    xs[7] = L * 0.86          # V-notch: pull the tip vertex back
    ca, sa = np.cos(ang), np.sin(ang)
    px = cx + xs * ca - ys * sa
    py = cy + xs * sa + ys * ca
    return np.stack([px, py], axis=1).astype(np.int32)


@_structure("sakura_hurricane")
def _b_sakura_hurricane(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 13 + 2)
    yy, xx = _mg(shape)
    # dusk gradient with warm horizon band
    tgrad = yy / h
    rgb = _ramp(tgrad, [(0.30, 0.10, 0.32), (0.48, 0.16, 0.38), (0.72, 0.32, 0.42), (0.24, 0.08, 0.28)])
    rgb += (_fbm(shape, seed * 3 + 4, 3, 4.0)[..., None] - 0.5) * 0.09
    shimmer = _norm(_fbm(shape, seed * 5 + 5, 4, 8.0))
    specM = 26 + shimmer * 74          # pearl shimmer bands under the storm (wide M range)
    specR = 165 + (shimmer - 0.5) * 90
    specC = 150 + (shimmer - 0.5) * 110
    # hurricane flow: spiral around an off-canvas eye + curl turbulence
    ex, ey = w * 1.25, h * 0.35
    dx, dy = xx - ex, yy - ey
    base_ang = np.arctan2(dy, dx) + np.pi / 2.0
    curl = (_fbm(shape, seed * 7 + 7, 4, 5.0) - 0.5) * 2.2
    ang_f = base_ang + curl
    Hf, Wf = float(h - 2), float(w - 2)
    # wind streaks under petals
    for _ in range(max(90, int(600 * S))):
        x, y = r.random() * w, r.random() * h
        p = []
        for _ in range(int(20 + 30 * r.random())):
            iy, ix = int(min(max(y, 0), Hf)), int(min(max(x, 0), Wf))
            a = float(ang_f[iy, ix])
            x += np.cos(a) * 4.5 * S
            y += np.sin(a) * 4.5 * S
            p.append((int(x), int(y)))
        if len(p) > 3:
            pp = np.array(p, np.int32)
            cv2.polylines(rgb, [pp], False, (0.88, 0.58, 0.68), 1, cv2.LINE_AA)
            cv2.polylines(specM, [pp], False, float(120), 1, cv2.LINE_AA)
    layers = [  # (count, Lmin, Lmax, desat, blur, outline)
        (max(320, int(2600 * S * S)), 7, 12, 0.55, 1.6, False),
        (max(220, int(1700 * S * S)), 12, 22, 0.82, 0.0, False),
        (max(120, int(900 * S * S)), 18, 40, 1.00, 0.0, True),
    ]
    pink_hi = np.array([1.00, 0.92, 0.95], np.float32)
    for count, lmin, lmax, sat, blur, outline in layers:
        buf = rgb if blur == 0 else np.zeros((h, w, 3), np.float32)
        used_buf = buf is not rgb
        for _ in range(count):
            x, y = r.random() * w, r.random() * h
            iy, ix = int(min(max(y, 0), Hf)), int(min(max(x, 0), Wf))
            a = float(ang_f[iy, ix]) + (r.random() - 0.5) * 0.5
            L = (lmin + (lmax - lmin) * r.random()) * S + 2
            W_ = L * (0.55 + 0.25 * r.random())
            tier = _tier8(r, 0.5, 1.0)
            gold = r.random() < 0.03
            base_c = (np.array([1.0, 0.80, 0.30], np.float32) if gold else
                      np.array([1.00, 0.45, 0.68], np.float32) * tier + pink_hi * (1 - tier))
            c = base_c * sat + np.array([0.42, 0.18, 0.36]) * (1 - sat)
            poly = _petal_poly(x, y, L, W_, a)
            if outline:
                cv2.polylines(buf, [poly], True, tuple(map(float, c * 0.35)), max(1, int(2 * S)), cv2.LINE_AA)
            cv2.fillPoly(buf, [poly], tuple(map(float, c)), cv2.LINE_AA)
            hi_poly = _petal_poly(x - L * 0.08, y - L * 0.08, L * 0.62, W_ * 0.55, a)
            cv2.fillPoly(buf, [hi_poly], tuple(map(float, np.clip(c * 1.25, 0, 1))), cv2.LINE_AA)
            mval = 252.0 if gold else (60 + 120 * tier)
            cv2.fillPoly(specM, [poly], float(mval * sat + 24 * (1 - sat)), cv2.LINE_AA)
            cv2.fillPoly(specR, [poly], float(26 if gold else (34 + 60 * (1 - tier))), cv2.LINE_AA)
            cv2.fillPoly(specC, [poly], float(16 + 40 * (1 - tier)), cv2.LINE_AA)
        if used_buf:
            bb = cv2.GaussianBlur(buf, (0, 0), blur * S + 0.4)
            m = bb.max(axis=2, keepdims=True)
            rgb = rgb * (1 - np.clip(m * 1.2, 0, 1)) + bb * np.clip(m * 1.2, 0, 1) / np.maximum(m, 1e-4) * m
    rgb = _pop(np.clip(rgb, 0, 1), shape, seed, sat=1.24, grain=0.03)
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 07 ki_corona
# MECHANISM: upward-advected aura tongues posterized into hard shells (double corona: gold core /
# cyan outer) + jagged electric filaments + rising ember teardrops. (anime_energy_aura)

@_structure("ki_corona")
def _b_ki_corona(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 15 + 8)
    yy, xx = _mg(shape)
    # charge cores spread across the full width (coverage), stretched vertical
    field = np.zeros((h, w), np.float32)
    n_cores = 7
    for i in range(n_cores):
        cx = (i + 0.5 + (r.random() - 0.5) * 0.6) / n_cores * w
        cy = h * (0.25 + 0.6 * r.random())
        sx = w * (0.05 + 0.05 * r.random())
        sy = h * (0.22 + 0.22 * r.random())
        amp = 0.7 + 0.5 * r.random()
        field += amp * np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2))
    # upward flame advection: sample the field displaced by curl + rise
    curl = (_fbm(shape, seed * 3 + 5, 4, 6.0) - 0.5)
    rise = _fbm(shape, seed * 7 + 9, 4, 8.0)
    map_x = (xx + curl * 180 * S).astype(np.float32)
    map_y = (yy + rise * 260 * S + 120 * S).astype(np.float32)
    field = cv2.remap(field, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    field = _norm(field + 0.22 * (_fbm(shape, seed * 11 + 4, 4, 12.0) - 0.5))
    SH = 5
    shell = np.clip(np.floor(field * SH), 0, SH - 1).astype(np.int32)
    # double corona palette: void -> cyan outer -> blue -> gold -> white-hot core
    pal = np.array([(0.02, 0.03, 0.10), (0.05, 0.35, 0.55), (0.10, 0.60, 0.95),
                    (1.00, 0.72, 0.18), (1.00, 0.97, 0.80)], np.float32)
    rgb = pal[shell]
    ink = _band_ink(shell.astype(np.float32), max(1, int(3 * S)))
    rgb = rgb * (1 - ink[..., None] * 0.75)
    # electric filaments: jagged walks seeded on shell boundaries
    fil = np.zeros((h, w), np.float32)
    ys, xs = np.where(ink > 0.4)
    n_fil = min(64, max(18, int(46 * S + 6)))
    if len(ys):
        for _ in range(n_fil):
            i = int(r.integers(0, len(ys)))
            x, y = float(xs[i]), float(ys[i])
            a = r.random() * 2 * np.pi
            p = [(int(x), int(y))]
            for _ in range(int(14 + 26 * r.random())):
                a += (r.random() - 0.5) * 2.4
                step = (9 + 14 * r.random()) * S + 2
                x += np.cos(a) * step
                y += np.sin(a) * step
                p.append((int(x), int(y)))
                if r.random() < 0.22 and len(p) > 2:   # fork
                    fa = a + (r.random() - 0.5) * 2.0
                    fx2, fy2 = x + np.cos(fa) * step * 2.2, y + np.sin(fa) * step * 2.2
                    cv2.line(fil, p[-1], (int(fx2), int(fy2)), 0.8, 1, cv2.LINE_AA)
            cv2.polylines(fil, [np.array(p, np.int32)], False, 1.0, max(1, int(2 * S)), cv2.LINE_AA)
    # rising embers: small upward teardrops
    emb = np.zeros((h, w, 3), np.float32)
    for _ in range(max(120, int(760 * S * S))):
        x, y = int(r.random() * w), int(r.random() * h)
        L = (4 + 9 * r.random()) * S + 1
        b = _tier8(r, 0.4, 1.0)
        c = np.array([1.0, 0.85, 0.45], np.float32) * b if r.random() < 0.6 else np.array([0.55, 0.9, 1.0], np.float32) * b
        cv2.ellipse(emb, (x, y), (max(1, int(L * 0.35)), max(1, int(L))), 0, 0, 360, tuple(map(float, c)), -1, cv2.LINE_AA)
    rgb = np.clip(rgb + emb, 0, 1)
    filb = cv2.GaussianBlur(fil, (0, 0), 5 * S + 1)
    rgb = np.clip(rgb + fil[..., None] * np.array([0.85, 0.95, 1.0]) + filb[..., None] * np.array([0.2, 0.5, 0.9]), 0, 1)
    rgb = _glow(rgb, 10 * S + 1.5, 0.16)
    rgb = _pop(rgb, shape, seed, sat=1.12, grain=0.025)
    # ---- married spec: shells ladder M inward, filaments chrome, embers metal sparks
    m_lad = np.array([26, 84, 140, 208, 252], np.float32)
    r_lad = np.array([198, 150, 96, 44, 12], np.float32)
    c_lad = np.array([225, 170, 110, 48, 16], np.float32)
    M = m_lad[shell].astype(np.float32)
    R = r_lad[shell] + (curl * 40)
    CC = c_lad[shell].astype(np.float32)
    M = np.maximum(M, fil * 252)
    R = np.where(fil > 0.35, 8.0, R)
    CC = np.where(fil > 0.35, 16.0, CC)
    el = emb.max(axis=2)
    M = np.maximum(M, el * 250)
    R = np.where(el > 0.4, 24.0, R)
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(M, R, CC)}


# ============================================================================ 08 screentone_moire
# MECHANISM: two INTERFERING rotated Ben-Day dot lattices, radius modulated by a posterised tone
# field; ink cross-hatch pockets in shadow tone; red spot-colour dot band. (anime_comic_halftone)

def _dot_lattice(xx, yy, angle_deg, cell, radius01):
    a = np.deg2rad(angle_deg)
    u = (xx * np.cos(a) + yy * np.sin(a)) / cell
    v = (-xx * np.sin(a) + yy * np.cos(a)) / cell
    du = u - np.round(u)
    dv = v - np.round(v)
    d = np.sqrt(du * du + dv * dv)
    return np.clip((radius01 * 0.72 - d) * cell * 1.6, 0, 1)   # AA-ish dot mask


@_structure("screentone_moire")
def _b_screentone_moire(shape, seed):
    h, w = shape
    S = h / 2048.0
    yy, xx = _mg(shape)
    tone_f = _fbm(shape, seed * 3 + 2, 4, 3.2)
    tone_f = _norm(tone_f + 0.35 * (_fbm(shape, seed * 5 + 7, 3, 8.0) - 0.5))
    T = np.clip(np.floor(tone_f * 5), 0, 4).astype(np.int32)   # 0=shadow .. 4=light
    t01 = T / 4.0
    paper = np.array([1.00, 0.90, 0.70], np.float32)
    fiber = (_vgrid(shape, seed * 7 + 3, h // 3, w // 3) - 0.5) * 0.05
    rgb = np.ones((h, w, 3), np.float32) * paper + fiber[..., None]
    ink_c = np.array([0.15, 0.055, 0.10], np.float32)
    cellA = max(6.0, 13.0 * S)
    cellB = max(4.5, 9.0 * S)
    radA = (1.0 - t01) * 0.95           # dark tone -> big dots
    radB = np.clip(0.75 - np.abs(t01 - 0.5) * 1.5, 0, 1) * 0.8   # mid tones -> lattice B joins = moiré
    dotsA = _dot_lattice(xx, yy, 15.0, cellA, radA)
    dotsB = _dot_lattice(xx, yy, 75.0, cellB, radB)
    dots = np.clip(dotsA + dotsB * 0.85, 0, 1)
    # shadow pockets: cross-hatch instead of dots
    ph = max(4.0, 9.0 * S)
    hatch = ((np.sin((xx + yy) / ph) > 0.2) | (np.sin((xx - yy) / (ph * 1.35)) > 0.55)).astype(np.float32)
    shadow = (T == 0).astype(np.float32)
    dots = dots * (1 - shadow) + hatch * shadow
    # highlight zone: sparse white sparkle holes stay paper + tiny accent dots
    red_band = (T == 3).astype(np.float32)
    cyan_band = (T == 1).astype(np.float32)
    yell_band = (T == 2).astype(np.float32)
    red = np.array([0.92, 0.08, 0.24], np.float32)
    cyan = np.array([0.04, 0.58, 0.95], np.float32)
    yell = np.array([0.96, 0.72, 0.08], np.float32)
    ink_mask = np.clip(dots, 0, 1)
    col = (ink_c[None, None, :] * (1 - red_band[..., None] - cyan_band[..., None] - yell_band[..., None])
           + red[None, None, :] * red_band[..., None] + cyan[None, None, :] * cyan_band[..., None]
           + yell[None, None, :] * yell_band[..., None])
    rgb = rgb * (1 - ink_mask[..., None]) + col * ink_mask[..., None]
    # panel-corner ink splashes for macro rhythm (rare, small)
    r = _rng(seed * 13 + 1)
    for _ in range(max(6, int(26 * S * S))):
        x, y = int(r.random() * w), int(r.random() * h)
        rad = int((14 + 26 * r.random()) * S + 3)
        if T[min(y, h - 1), min(x, w - 1)] <= 1:
            cv2.circle(rgb, (x, y), rad, tuple(map(float, ink_c)), -1, cv2.LINE_AA)
            spl = _star_pts(x, y, 9, rad * 1.7, rad * 0.9, r.random() * np.pi)
            cv2.fillPoly(rgb, [spl], tuple(map(float, ink_c)), cv2.LINE_AA)
    # ---- married spec: dots are metal, paper is soft matte; tone bands ladder everything
    m_lad = np.array([248, 205, 165, 252, 90], np.float32)      # per-tone dot metal (red band pops)
    r_dot = np.array([26, 40, 58, 34, 90], np.float32)
    M = 22 + ink_mask * (m_lad[T] - 22)
    R = 205 - ink_mask * (205 - r_dot[T]) + fiber * 120
    CC = 212 - ink_mask * 176 - t01 * 40
    return {"rgb": np.clip(rgb, 0, 1).astype(np.float32), "spec": _spec_pack(M, R, CC)}


# ============================================================================ 09 neo_tokyo_glow
# MECHANISM: aerial night-city sprawl — jittered street grid corridors, dark blocks packed with
# tiny lit-window clusters, neon sign strokes with bloom, wet vertical reflection smear.
# (anime_neon_outline)

@_structure("neo_tokyo_glow")
def _b_neo_tokyo_glow(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 17 + 4)
    haze = _fbm(shape, seed * 3 + 9, 3, 4.0)
    rgb = _ramp(haze, [(0.03, 0.03, 0.09), (0.06, 0.05, 0.15), (0.10, 0.07, 0.20)])
    specM = np.full((h, w), 30.0, np.float32)
    specR = np.full((h, w), 205.0, np.float32)
    specC = np.full((h, w), 225.0, np.float32)
    glow = np.zeros((h, w, 3), np.float32)
    # street grid: two jittered families of corridors
    streets = np.zeros((h, w), np.float32)
    for horiz in (True, False):
        pos = 0.0
        while pos < (h if horiz else w):
            pos += (90 + 150 * r.random()) * S + 20
            p = int(pos)
            wd = max(2, int((4 + 8 * r.random()) * S))
            jit = int((r.random() - 0.5) * 30 * S)
            if horiz:
                cv2.line(streets, (0, p + jit), (w, p - jit), 1.0, wd, cv2.LINE_AA)
            else:
                cv2.line(streets, (p + jit, 0), (p - jit, h), 1.0, wd, cv2.LINE_AA)
    warm = np.array([1.0, 0.62, 0.28], np.float32)
    rgb += streets[..., None] * warm * 0.35
    glow += streets[..., None] * warm * 0.5
    specR -= streets * 160          # wet asphalt corridors are glossy
    specC -= streets * 190
    specM += streets * 60
    # window clusters: blocks of tiny lit windows everywhere off-street
    n_blocks = max(60, int(420 * S * S))
    cools = np.array([(0.65, 0.85, 1.0), (1.0, 0.85, 0.55), (0.95, 0.95, 1.0), (1.0, 0.7, 0.4)], np.float32)
    for _ in range(n_blocks):
        bx, by = int(r.random() * w), int(r.random() * h)
        bw = int((26 + 70 * r.random()) * S + 6)
        bh = int((26 + 70 * r.random()) * S + 6)
        cv2.rectangle(rgb, (bx, by), (bx + bw, by + bh), (0.05, 0.05, 0.10), -1)
        cv2.rectangle(specR, (bx, by), (bx + bw, by + bh), float(235), -1)
        wp = max(3, int(7 * S + 1))
        gp = max(2, int(4 * S + 1))
        tint = cools[int(r.integers(0, len(cools)))]
        lit_p = 0.25 + 0.5 * r.random()
        for wy in range(by + gp, by + bh - wp, wp + gp):
            for wx in range(bx + gp, bx + bw - wp, wp + gp):
                if r.random() < lit_p:
                    b = _tier8(r, 0.35, 1.0)
                    cv2.rectangle(rgb, (wx, wy), (wx + wp - 1, wy + wp - 1), tuple(map(float, tint * b)), -1)
                    cv2.rectangle(specM, (wx, wy), (wx + wp - 1, wy + wp - 1), float(140 + 110 * b), -1)
                    cv2.rectangle(specR, (wx, wy), (wx + wp - 1, wy + wp - 1), float(20 + 60 * (1 - b)), -1)
    # neon signage: glowing strokes / arcs / rings
    neons = np.array([(1.0, 0.15, 0.62), (0.10, 0.95, 1.0), (1.0, 0.45, 0.10),
                      (0.45, 1.0, 0.35), (0.75, 0.30, 1.0)], np.float32)
    for _ in range(max(30, int(190 * S * S))):
        x, y = int(r.random() * w), int(r.random() * h)
        c = neons[int(r.integers(0, len(neons)))] * (0.8 + 0.4 * r.random())
        kind = r.random()
        th = max(1, int(2.5 * S))
        if kind < 0.4:
            L = int((16 + 40 * r.random()) * S + 4)
            a = r.random() * np.pi
            dx, dy = int(L * np.cos(a)), int(L * np.sin(a))
            cv2.line(rgb, (x - dx, y - dy), (x + dx, y + dy), tuple(map(float, c)), th, cv2.LINE_AA)
            cv2.line(glow, (x - dx, y - dy), (x + dx, y + dy), tuple(map(float, c)), th, cv2.LINE_AA)
            cv2.line(specM, (x - dx, y - dy), (x + dx, y + dy), float(252), th)
            cv2.line(specR, (x - dx, y - dy), (x + dx, y + dy), float(10), th)
        elif kind < 0.7:
            rad = int((8 + 22 * r.random()) * S + 3)
            cv2.circle(rgb, (x, y), rad, tuple(map(float, c)), th, cv2.LINE_AA)
            cv2.circle(glow, (x, y), rad, tuple(map(float, c)), th, cv2.LINE_AA)
            cv2.circle(specM, (x, y), rad, float(252), th)
            cv2.circle(specR, (x, y), rad, float(10), th)
        else:
            rad = int((10 + 26 * r.random()) * S + 3)
            a0 = r.random() * 360
            cv2.ellipse(rgb, (x, y), (rad, int(rad * 0.6)), a0, 0, 220, tuple(map(float, c)), th, cv2.LINE_AA)
            cv2.ellipse(glow, (x, y), (rad, int(rad * 0.6)), a0, 0, 220, tuple(map(float, c)), th, cv2.LINE_AA)
            cv2.ellipse(specM, (x, y), (rad, int(rad * 0.6)), a0, 0, 220, float(252), th)
            cv2.ellipse(specR, (x, y), (rad, int(rad * 0.6)), a0, 0, 220, float(10), th)
    # wet reflection: vertical smear of the glow layer, displaced down
    smear = cv2.blur(glow, (1, max(4, int(70 * S))))
    smear = np.roll(smear, int(30 * S), axis=0) * 0.5
    rgb = np.clip(rgb + smear, 0, 1)
    rgb = np.clip(rgb + cv2.GaussianBlur(glow, (0, 0), 8 * S + 1.2) * 0.85, 0, 1)
    rgb = _pop(rgb, shape, seed, sat=1.10, grain=0.02)
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 10 shard_cascade
# MECHANISM: Voronoi shatter (label-map) with per-shard refraction stripe systems + per-shard
# luminance gradients + glint edge lines + prism edges + micro-facet dust. (anime_crystal_facet)

@_structure("shard_cascade")
def _b_shard_cascade(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 19 + 2)
    yy, xx = _mg(shape)
    n_seeds = max(90, int(620 * S * S))
    pts = np.stack([r.random(n_seeds) * h, r.random(n_seeds) * w], axis=1)
    seedmap = np.ones((h, w), np.uint8)
    seedmap[np.clip(pts[:, 0].astype(int), 0, h - 1), np.clip(pts[:, 1].astype(int), 0, w - 1)] = 0
    dist, labels = cv2.distanceTransformWithLabels(seedmap, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    labels = labels.astype(np.int64)
    n_lab = int(labels.max()) + 1
    # per-cell properties
    cell_hue = r.random(n_lab).astype(np.float32)
    cell_tier = _LADDER8[r.integers(0, 8, n_lab)].astype(np.float32)
    cell_ang = (r.random(n_lab) * np.pi).astype(np.float32)
    cell_pitch = (6 + 10 * r.random(n_lab)).astype(np.float32) * S + 2
    jewels = np.array([(0.62, 0.28, 0.95), (0.20, 0.85, 0.85), (0.95, 0.35, 0.62),
                       (0.98, 0.78, 0.25), (0.30, 0.55, 0.98), (0.45, 0.95, 0.55),
                       (0.90, 0.90, 0.98), (0.75, 0.25, 0.35)], np.float32)
    cell_col = jewels[(cell_hue * 7.999).astype(np.int32)]
    hue_m = cell_col[labels]
    tier_m = cell_tier[labels]
    ang_m = cell_ang[labels]
    pitch_m = cell_pitch[labels]
    # refraction stripes + per-cell gradient
    stripes = 0.5 + 0.5 * np.sin((xx * np.cos(ang_m) + yy * np.sin(ang_m)) / np.maximum(pitch_m, 1.5) * 2 * np.pi)
    stripes = np.clip(np.floor(stripes * 3) / 2, 0, 1)          # hard 3-step refraction bands
    sweep = _norm(xx + yy * 0.6 + (_fbm(shape, seed * 23 + 5, 3, 3.0) - 0.5) * 500 * S)
    lum = (0.35 + 0.75 * tier_m) * (0.75 + 0.45 * stripes) * (0.6 + 0.5 * sweep)
    rgb = np.clip(hue_m * lum[..., None], 0, 1)
    # edges: glint + dark under-edge + prism lines on a subset
    eek = _band_ink(labels.astype(np.float32) % 97, max(1, int(2 * S)))
    under = np.roll(eek, max(1, int(2 * S)), axis=0)
    rgb = rgb * (1 - under[..., None] * 0.55)
    rgb = np.clip(rgb + eek[..., None] * np.array([0.9, 0.95, 1.0]) * 0.85, 0, 1)
    prism_cells = (cell_hue[labels] * 13) % 1 < 0.22
    pe = eek * prism_cells
    rgb[..., 0] = np.clip(rgb[..., 0] + np.roll(pe, 1, axis=1) * 0.5, 0, 1)
    rgb[..., 2] = np.clip(rgb[..., 2] + np.roll(pe, -1, axis=1) * 0.5, 0, 1)
    # micro-facet dust
    dust = np.zeros((h, w), np.float32)
    for _ in range(max(260, int(2100 * S * S))):
        x, y = int(r.random() * w), int(r.random() * h)
        sz = (2.5 + 6 * r.random()) * S + 1
        a = r.random() * 2 * np.pi
        tri = np.array([[x + sz * np.cos(a), y + sz * np.sin(a)],
                        [x + sz * np.cos(a + 2.1), y + sz * np.sin(a + 2.1)],
                        [x + sz * np.cos(a + 4.2), y + sz * np.sin(a + 4.2)]], np.int32)
        cv2.fillPoly(dust, [tri], float(_tier8(r, 0.3, 1.0)), cv2.LINE_AA)
    rgb = np.clip(rgb + dust[..., None] * np.array([0.9, 0.92, 1.0]) * 0.55, 0, 1)
    rgb = _glow(rgb, 6 * S + 1, 0.10)
    rgb = _pop(rgb, shape, seed, sat=1.16, grain=0.03)
    # ---- married spec: per-cell metal tiers, stripes carve roughness, edges chrome, dust sparks
    glass = tier_m < 0.30          # lowest-tier shards read as deep dielectric glass (full M span)
    M = np.where(glass, 14 + stripes * 26, 110 + tier_m * 130 + stripes * 20)
    R = np.where(glass, 20 + stripes * 30, 66 - stripes * 46 + (1 - tier_m) * 60)
    CC = 16 + (1 - tier_m) * 150 + stripes * 46 - sweep * 30
    M = np.maximum(M, eek * 252)
    R = np.where(eek > 0.45, 6.0, R)
    M = np.maximum(M, dust * 250)
    R = np.where(dust > 0.5, 14.0, R)
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(M, R, CC)}


# ============================================================================ 11 cel_cloud_sea
# MECHANISM: stacked cauliflower cloudlet clusters cel-shaded into 3 hard tones via mass-offset
# (lit top / cream mid / lavender underside) + ink rims + cirrus streaks + tiny birds.
# (anime2_cel_shade "Cel Cloud Sea")

@_structure("cel_cloud_sea")
def _b_cel_cloud_sea(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 21 + 3)
    yy, xx = _mg(shape)
    sky = _ramp(yy / h, [(0.16, 0.42, 0.82), (0.30, 0.58, 0.92), (0.55, 0.76, 0.97), (0.82, 0.90, 0.99)])
    rgb = sky.copy()
    mass = np.zeros((h, w), np.float32)
    # STRATIFIED cloud sea: clusters clump along horizontal bands so the canvas reads as layered
    # cloud decks (not lonely blobs on sky) — target ~2/3 mass coverage
    n_bands = 6
    band_ys = [(i + 0.5) / n_bands * h + (r.random() - 0.5) * h * 0.10 for i in range(n_bands)]
    n_cl = max(90, int(330 * S * S))
    for ci in range(n_cl):
        by = band_ys[int(r.integers(0, n_bands))]
        cx = r.random() * w
        cy = by + (r.random() - 0.5) * h * 0.14
        base_r = (20 + 48 * r.random()) * S + 5
        n_p = 5 + int(r.integers(0, 6))
        for i in range(n_p):
            a = (i / n_p) * np.pi + r.random() * 0.8
            px = cx + (i - n_p / 2) * base_r * 0.55 + (r.random() - 0.5) * base_r * 0.4
            py = cy - abs(np.sin(a)) * base_r * 0.40 + (r.random() - 0.55) * base_r * 0.3
            rr_ = base_r * (0.32 + 0.40 * r.random())
            cv2.circle(mass, (int(px), int(py)), max(2, int(rr_)), 1.0, -1, cv2.LINE_AA)
    for _ in range(max(160, int(800 * S * S))):    # micro puffs everywhere
        cv2.circle(mass, (int(r.random() * w), int(r.random() * h)),
                   max(1, int((4 + 10 * r.random()) * S + 1)), 1.0, -1, cv2.LINE_AA)
    mass = np.clip(mass, 0, 1)
    off = max(3, int(18 * S))
    lit_m = (mass > 0.5) & (np.roll(mass, off, axis=0) < 0.5)              # top rims lit
    shad_m = (mass > 0.5) & (np.roll(mass, -int(off * 1.6), axis=0) < 0.5)  # undersides shadowed
    mid_m = (mass > 0.5) & ~lit_m & ~shad_m
    c_lit = np.array([0.99, 0.99, 1.00], np.float32)
    c_mid = np.array([0.93, 0.91, 0.96], np.float32)
    c_shd = np.array([0.66, 0.66, 0.84], np.float32)
    rgb[lit_m] = c_lit
    rgb[mid_m] = c_mid
    rgb[shad_m] = c_shd
    ink = _band_ink((mass > 0.5).astype(np.float32), 1)
    rgb = rgb * (1 - ink[..., None] * 0.5)
    # sun-stipple on lit rims + tone-edge ink between cel tones (fine detail on the cloud tops)
    tink = _band_ink(lit_m.astype(np.float32) + shad_m.astype(np.float32) * 2, 1)
    rgb = rgb * (1 - tink[..., None] * 0.18)
    ys_, xs_ = np.where(lit_m)
    if len(ys_):
        for _ in range(max(900, int(6200 * S * S))):
            i = int(r.integers(0, len(ys_)))
            cv2.circle(rgb, (int(xs_[i]), int(ys_[i])), max(1, int(2.0 * S)), (1.0, 1.0, 0.98), -1)
    # cauliflower dapple: small shadow flecks through the cloud BODIES (kills the flat interiors)
    ym_, xm_ = np.where(mid_m)
    if len(ym_):
        for _ in range(max(700, int(4200 * S * S))):
            i = int(r.integers(0, len(ym_)))
            fl = c_shd if r.random() < 0.6 else np.minimum(c_lit * 1.01, 1.0)
            cv2.circle(rgb, (int(xm_[i]), int(ym_[i])), max(1, int((1.4 + 1.8 * r.random()) * S)),
                       tuple(map(float, fl)), -1)
    # cirrus streaks + birds
    for _ in range(max(20, int(120 * S * S))):
        x, y = int(r.random() * w), int(r.random() * h)
        L = int((40 + 120 * r.random()) * S + 8)
        cv2.line(rgb, (x, y), (x + L, y + int((r.random() - 0.5) * 8 * S)), (0.97, 0.97, 1.0), 1, cv2.LINE_AA)
    for _ in range(max(8, int(42 * S * S))):
        x, y = int(r.random() * w), int(r.random() * h)
        L = max(2, int((5 + 5 * r.random()) * S + 1))
        c = (0.12, 0.14, 0.24)
        cv2.line(rgb, (x - L, y), (x, y - int(L * 0.7)), c, max(1, int(1.5 * S)), cv2.LINE_AA)
        cv2.line(rgb, (x, y - int(L * 0.7)), (x + L, y), c, max(1, int(1.5 * S)), cv2.LINE_AA)
    # ---- married spec: cel tones ladder R; lit tops pearl-metal; sky glossy gradient
    M = np.full((h, w), 36.0, np.float32)
    R = 42 + (yy / h) * 30
    CC = 36 + (yy / h) * 110
    M[mass > 0.5] = 58
    M[lit_m] = 158
    R[lit_m] = 48
    R[mid_m] = 112
    R[shad_m] = 172
    CC[mass > 0.5] = 150
    CC[lit_m] = 70
    M = M + (_vgrid(shape, seed * 5 + 6, 128, 128) - 0.5) * 24 + (mass > 0.5) * (_vgrid(shape, seed * 7 + 9, 256, 256) - 0.5) * 44
    R = R + ink * 60
    return {"rgb": np.clip(rgb, 0, 1).astype(np.float32), "spec": _spec_pack(M, R, CC)}


# ============================================================================ 12 impact_frames
# MECHANISM: discrete manga impact-burst cells — jagged spike outlines, alternating B/W angular
# sectors, local radial rays, halftone interiors, yellow flash accents. (anime2_screentone)

@_structure("impact_frames")
def _b_impact_frames(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 23 + 6)
    yy, xx = _mg(shape)
    rgb = np.ones((h, w, 3), np.float32) * np.array([0.94, 0.93, 0.90], np.float32)
    specM = np.full((h, w), 26.0, np.float32)
    specR = np.full((h, w), 200.0, np.float32)
    specC = np.full((h, w), 215.0, np.float32)
    n_b = max(8, int(19 * (S ** 1.2) + 4))
    cxs = r.random(n_b) * w
    cys = r.random(n_b) * h
    rads = (0.16 + 0.22 * r.random(n_b)) * h
    ink = np.array([0.06, 0.06, 0.10], np.float32)
    for bi in range(n_b):
        cx, cy, R_ = float(cxs[bi]), float(cys[bi]), float(rads[bi])
        x0, x1 = max(0, int(cx - R_)), min(w, int(cx + R_))
        y0, y1 = max(0, int(cy - R_)), min(h, int(cy + R_))
        if x1 <= x0 or y1 <= y0:
            continue
        lx = xx[y0:y1, x0:x1] - cx
        ly = yy[y0:y1, x0:x1] - cy
        rr_ = np.sqrt(lx * lx + ly * ly)
        th = np.arctan2(ly, lx)
        n_spk = int(12 + r.integers(0, 12))
        spike = 1.0 + 0.28 * np.sin(th * n_spk + r.random() * 7)
        inside = rr_ < R_ * 0.72 * spike
        style = int(r.integers(0, 3))
        yellow = r.random() < 0.22
        n_sect = int(10 + r.integers(0, 14))
        sect = ((th / (2 * np.pi) + 0.5) * n_sect + r.random() * 3).astype(np.int32) % 2
        n_ray = int(50 + r.integers(0, 60))
        u = (th / (2 * np.pi) + 0.5) * n_ray
        fr = np.abs(u - np.round(u))
        rays = (fr < 0.14 * (0.4 + rr_ / max(R_, 1))) & (rr_ > R_ * 0.16)
        cell = max(3.0, 8.0 * S)
        du = (lx / cell) - np.round(lx / cell)
        dv = (ly / cell) - np.round(ly / cell)
        dots = np.sqrt(du * du + dv * dv) < 0.30
        sub = rgb[y0:y1, x0:x1]
        sM = specM[y0:y1, x0:x1]
        sR = specR[y0:y1, x0:x1]
        sC = specC[y0:y1, x0:x1]
        if style == 0:      # B/W inverted sectors
            dark = inside & (sect == 0)
            lite = inside & (sect == 1)
            sub[dark] = ink
            sub[lite] = (1.0, 1.0, 1.0) if not yellow else (1.0, 0.90, 0.20)
            sub[inside & rays] = (1.0, 1.0, 1.0)
            sM[dark] = 210; sR[dark] = 40; sC[dark] = 30
            sM[lite] = 70; sR[lite] = 120; sC[lite] = 90
        elif style == 1:    # ink rays on paper + halftone ring
            ringz = inside & (rr_ > R_ * 0.40)
            sub[ringz & dots] = ink
            sub[inside & rays] = ink
            core = rr_ < R_ * 0.22
            sub[core] = (1.0, 0.90, 0.20) if yellow else (1.0, 1.0, 1.0)
            sM[inside & rays] = 235; sR[inside & rays] = 30
            sM[ringz & dots] = 190; sR[ringz & dots] = 50
            sM[core] = 252; sR[core] = 18; sC[core] = 16
        else:               # black flash card with white burst
            card = inside
            sub[card] = ink
            sub[card & rays] = (1.0, 1.0, 1.0)
            sub[card & dots & (rr_ > R_ * 0.35)] = (0.75, 0.75, 0.80)
            sM[card] = 46; sR[card] = 180; sC[card] = 160
            sM[card & rays] = 252; sR[card & rays] = 10; sC[card & rays] = 16
        # bold jagged outline
        edge = np.abs(rr_ - R_ * 0.72 * spike) < max(1.5, 3.0 * S)
        sub[edge] = ink
        sM[edge] = 20; sR[edge] = 225; sC[edge] = 235
    # gutter speckle so the paper isn't empty between bursts
    spk = (_vgrid(shape, seed * 9 + 8, h // 3, w // 3) > 0.985)
    rgb[spk] = ink
    return {"rgb": np.clip(rgb, 0, 1).astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 13 hanami_night
# MECHANISM: festival night — branch silhouette fractal + glowing ribbed paper lanterns on
# strings + firefly bokeh + smoke wisps + minor petal garnish. (anime2_sakura "Hanami Night")

@_structure("hanami_night")
def _b_hanami_night(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 25 + 7)
    yy, xx = _mg(shape)
    rgb = _ramp(_norm(yy + 300 * S * (_fbm(shape, seed * 3 + 3, 3, 3.0) - 0.5)),
                [(0.05, 0.04, 0.14), (0.09, 0.06, 0.20), (0.13, 0.07, 0.22), (0.07, 0.04, 0.15)])
    specM = np.full((h, w), 22.0, np.float32)
    wispf = _norm(_fbm(shape, seed * 5 + 2, 4, 5.0))
    specR = 175 + (wispf - 0.5) * 80
    specC = 170 + (wispf - 0.5) * 100
    # smoke wisps
    wisp = np.clip(_fbm(shape, seed * 7 + 6, 4, 7.0) * 1.7 - 0.85, 0, 1)
    rgb += wisp[..., None] * np.array([0.10, 0.08, 0.14])
    # branch silhouettes: recursive forks
    def branch(x, y, a, L, d, thick):
        if d <= 0 or L < 4:
            return
        x2, y2 = x + np.cos(a) * L, y + np.sin(a) * L
        cv2.line(rgb, (int(x), int(y)), (int(x2), int(y2)), (0.03, 0.02, 0.06), max(1, int(thick)), cv2.LINE_AA)
        cv2.line(specR, (int(x), int(y)), (int(x2), int(y2)), float(235), max(1, int(thick)))
        n_f = 2 + int(r.integers(0, 2))
        for _ in range(n_f):
            branch(x2, y2, a + (r.random() - 0.5) * 1.5, L * (0.55 + 0.25 * r.random()), d - 1, thick * 0.6)
    for _ in range(max(9, int(24 * S + 3))):
        ex = r.random() * w
        ey = r.random() * h
        branch(ex, ey, r.random() * 2 * np.pi, (70 + 90 * r.random()) * S + 10, 4, 4 * S + 1)
    glow = np.zeros((h, w, 3), np.float32)
    # lantern strings
    lantern_pts = []
    for _ in range(max(10, int(34 * S * S) + 4)):
        x0, y0 = r.random() * w, r.random() * h * 0.9
        x1, y1 = x0 + (0.2 + 0.5 * r.random()) * w * (1 if r.random() < 0.5 else -1), y0 + (r.random() - 0.4) * h * 0.25
        n_l = 3 + int(r.integers(0, 5))
        for i in range(n_l + 1):
            t = i / n_l
            sx = x0 + (x1 - x0) * t
            sy = y0 + (y1 - y0) * t + np.sin(t * np.pi) * 40 * S
            if 0 <= sx < w and 0 <= sy < h:
                lantern_pts.append((sx, sy))
            if i < n_l:
                t2 = (i + 1) / n_l
                ex2 = x0 + (x1 - x0) * t2
                ey2 = y0 + (y1 - y0) * t2 + np.sin(t2 * np.pi) * 40 * S
                cv2.line(rgb, (int(sx), int(sy)), (int(ex2), int(ey2)), (0.16, 0.12, 0.10), 1, cv2.LINE_AA)
    # scattered solo lanterns for coverage
    for _ in range(max(46, int(150 * S * S))):
        lantern_pts.append((r.random() * w, r.random() * h))
    warm = np.array([(1.0, 0.55, 0.18), (1.0, 0.32, 0.22), (1.0, 0.75, 0.30), (0.95, 0.85, 0.55)], np.float32)
    for (lx, ly) in lantern_pts:
        lw_ = (7 + 12 * r.random()) * S + 2
        lh_ = lw_ * (1.25 + 0.35 * r.random())
        c = warm[int(r.integers(0, len(warm)))] * _tier8(r, 0.55, 1.05)
        cx_, cy_ = int(lx), int(ly)
        cv2.ellipse(rgb, (cx_, cy_), (int(lw_), int(lh_)), 0, 0, 360, tuple(map(float, c)), -1, cv2.LINE_AA)
        cv2.ellipse(glow, (cx_, cy_), (int(lw_), int(lh_)), 0, 0, 360, tuple(map(float, c * 0.8)), -1, cv2.LINE_AA)
        cv2.ellipse(rgb, (cx_, cy_), (int(lw_), int(lh_)), 0, 0, 360, tuple(map(float, c * 0.45)), 1, cv2.LINE_AA)
        for k in (-0.5, 0.0, 0.5):    # paper ribs
            rx = int(lw_ * (0.85 - 0.25 * abs(k)))
            cv2.ellipse(rgb, (cx_, cy_ + int(k * lh_ * 0.6)), (rx, max(1, int(lh_ * 0.16))), 0, 0, 360,
                        tuple(map(float, c * 0.55)), 1, cv2.LINE_AA)
        cv2.rectangle(rgb, (cx_ - int(lw_ * 0.4), cy_ - int(lh_) - max(1, int(3 * S))),
                      (cx_ + int(lw_ * 0.4), cy_ - int(lh_)), (0.25, 0.18, 0.10), -1)
        cv2.ellipse(specM, (cx_, cy_), (int(lw_), int(lh_)), 0, 0, 360, float(240), -1)
        cv2.ellipse(specR, (cx_, cy_), (int(lw_), int(lh_)), 0, 0, 360, float(24), -1)
        cv2.ellipse(specC, (cx_, cy_), (int(lw_), int(lh_)), 0, 0, 360, float(16), -1)
    # fireflies
    for _ in range(max(200, int(1250 * S * S))):
        x, y = int(r.random() * w), int(r.random() * h)
        b = _tier8(r, 0.3, 1.0)
        c = np.array([0.75, 1.0, 0.35], np.float32) * b if r.random() < 0.5 else np.array([1.0, 0.85, 0.35], np.float32) * b
        rad = max(1, int((1.2 + 2.2 * r.random()) * S + 0.5))
        cv2.circle(rgb, (x, y), rad, tuple(map(float, c)), -1, cv2.LINE_AA)
        cv2.circle(glow, (x, y), rad + 1, tuple(map(float, c * 0.7)), -1, cv2.LINE_AA)
        cv2.circle(specM, (x, y), rad, float(150 + 100 * b), -1)
        cv2.circle(specR, (x, y), rad, float(30), -1)
    # petal garnish (minor)
    for _ in range(max(40, int(210 * S * S))):
        x, y = r.random() * w, r.random() * h
        poly = _petal_poly(x, y, (5 + 8 * r.random()) * S + 1.5, (4 + 5 * r.random()) * S + 1, r.random() * 2 * np.pi)
        cv2.fillPoly(rgb, [poly], (0.72, 0.42, 0.52), cv2.LINE_AA)
        cv2.fillPoly(specM, [poly], float(90), cv2.LINE_AA)
    rgb = np.clip(rgb + cv2.GaussianBlur(glow, (0, 0), 11 * S + 1.5) * 0.85, 0, 1)
    rgb = _pop(rgb, shape, seed, sat=1.12, grain=0.025)
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 14 mecha_hologrid
# MECHANISM: holographic CAD space — depth-faded perspective grids, wireframe primitives with
# vertex dots, targeting reticles, dimension ticks, pseudo-7-seg dash groups, scan band.
# (anime2_mecha "Mecha Hologrid")

@_structure("mecha_hologrid")
def _b_mecha_hologrid(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 27 + 9)
    yy, xx = _mg(shape)
    rgb = _ramp(_fbm(shape, seed * 3 + 7, 3, 2.5), [(0.01, 0.03, 0.07), (0.02, 0.05, 0.11), (0.04, 0.08, 0.16)])
    cyan = np.array([0.15, 0.9, 1.0], np.float32)
    teal = np.array([0.2, 0.75, 0.8], np.float32)
    mag = np.array([1.0, 0.25, 0.85], np.float32)
    glow = np.zeros((h, w, 3), np.float32)
    specM = np.full((h, w), 24.0, np.float32)
    specR = np.full((h, w), 212.0, np.float32)
    specC = np.full((h, w), 232.0, np.float32)

    def stroke(img, pts, c, th=1):
        cv2.polylines(img, [np.array(pts, np.int32)], False, tuple(map(float, c)), th, cv2.LINE_AA)

    # two perspective grid families (floor + ceiling) with depth fade
    for flip in (1, -1):
        vy = h * (0.5 - flip * 0.65)
        n_v = int(26 * (0.8 + 0.4 * r.random()))
        for i in range(n_v):
            x0 = (i / (n_v - 1)) * w * 1.6 - w * 0.3
            fade = 0.25 + 0.5 * abs(i / n_v - 0.5)
            c = teal * fade
            cv2.line(rgb, (int(x0), int(h * 0.5 + flip * h * 0.55)), (int(w * 0.5 + (x0 - w * 0.5) * 0.15), int(vy)),
                     tuple(map(float, c)), 1, cv2.LINE_AA)
        for i in range(14):
            t = (i / 13.0) ** 1.8
            ly = h * 0.5 + flip * (h * 0.06 + t * h * 0.5)
            fade = 0.15 + 0.75 * t
            cv2.line(rgb, (0, int(ly)), (w, int(ly)), tuple(map(float, teal * fade)), 1, cv2.LINE_AA)
            cv2.line(specM, (0, int(ly)), (w, int(ly)), float(90 + 130 * fade), 1)
    # wireframe boxes / cylinders
    for _ in range(max(26, int(92 * S * S) + 10)):
        x, y = int(r.random() * w), int(r.random() * h)
        sz = int((18 + 52 * r.random()) * S + 6)
        dp = int(sz * (0.35 + 0.3 * r.random()))
        c = np.minimum(cyan * (0.75 + 0.45 * r.random()), 1.0)
        if r.random() < 0.7:   # box
            f = [(x, y), (x + sz, y), (x + sz, y + sz), (x, y + sz)]
            b = [(px + dp, py - dp) for px, py in f]
            for a_, b_ in zip(f, f[1:] + f[:1]):
                stroke(rgb, [a_, b_], c); stroke(glow, [a_, b_], c * 0.7)
            for a_, b_ in zip(b, b[1:] + b[:1]):
                stroke(rgb, [a_, b_], c * 0.55)
            for a_, b_ in zip(f, b):
                stroke(rgb, [a_, b_], c * 0.7)
            for px, py in f + b:
                cv2.circle(rgb, (px, py), max(1, int(2 * S)), tuple(map(float, np.minimum(c * 1.6, 1))), -1, cv2.LINE_AA)
                cv2.circle(specM, (px, py), max(1, int(2 * S)), float(252), -1)
        else:                  # cylinder
            rx, ry = sz, max(2, int(sz * 0.3))
            cv2.ellipse(rgb, (x, y), (rx, ry), 0, 0, 360, tuple(map(float, c)), 1, cv2.LINE_AA)
            cv2.ellipse(rgb, (x, y + sz), (rx, ry), 0, 0, 180, tuple(map(float, c * 0.6)), 1, cv2.LINE_AA)
            cv2.line(rgb, (x - rx, y), (x - rx, y + sz), tuple(map(float, c * 0.8)), 1, cv2.LINE_AA)
            cv2.line(rgb, (x + rx, y), (x + rx, y + sz), tuple(map(float, c * 0.8)), 1, cv2.LINE_AA)
        cv2.line(specR, (x, y), (x + sz, y), float(30), 1)
    # targeting reticles
    for _ in range(max(15, int(54 * S * S) + 5)):
        x, y = int(r.random() * w), int(r.random() * h)
        rad = int((14 + 30 * r.random()) * S + 5)
        c = (mag if r.random() < 0.18 else cyan) * (0.6 + 0.4 * r.random())
        a0 = r.random() * 360
        for k in range(3):
            cv2.ellipse(rgb, (x, y), (rad - k * max(2, int(4 * S)), rad - k * max(2, int(4 * S))), 0,
                        a0 + k * 40, a0 + k * 40 + 240 - k * 50, tuple(map(float, c * (1 - 0.22 * k))), 1, cv2.LINE_AA)
        for ang in range(0, 360, 30):
            a_r = np.deg2rad(ang + a0)
            r0, r1_ = rad, rad + max(2, int(5 * S))
            cv2.line(rgb, (int(x + r0 * np.cos(a_r)), int(y + r0 * np.sin(a_r))),
                     (int(x + r1_ * np.cos(a_r)), int(y + r1_ * np.sin(a_r))), tuple(map(float, c)), 1, cv2.LINE_AA)
        cv2.line(rgb, (x - rad // 2, y), (x + rad // 2, y), tuple(map(float, c * 1.2)), 1, cv2.LINE_AA)
        cv2.line(rgb, (x, y - rad // 2), (x, y + rad // 2), tuple(map(float, c * 1.2)), 1, cv2.LINE_AA)
        cv2.circle(specM, (x, y), rad, float(220), 1)
        cv2.circle(specR, (x, y), rad, float(26), 1)
    # dimension ticks + pseudo-7seg dash clusters
    for _ in range(max(30, int(130 * S * S) + 12)):
        x, y = int(r.random() * w), int(r.random() * h)
        c = teal * (0.5 + 0.5 * r.random())
        if r.random() < 0.5:
            L = int((20 + 50 * r.random()) * S + 6)
            cv2.line(rgb, (x, y), (x + L, y), tuple(map(float, c)), 1, cv2.LINE_AA)
            cv2.line(rgb, (x, y - max(2, int(4 * S))), (x, y + max(2, int(4 * S))), tuple(map(float, c)), 1, cv2.LINE_AA)
            cv2.line(rgb, (x + L, y - max(2, int(4 * S))), (x + L, y + max(2, int(4 * S))), tuple(map(float, c)), 1, cv2.LINE_AA)
        else:
            for d in range(int(3 + r.integers(0, 5))):
                dx = x + d * max(3, int(7 * S))
                seg_h = max(2, int(5 * S))
                if r.random() < 0.7:
                    cv2.line(rgb, (dx, y), (dx, y + seg_h), tuple(map(float, c)), 1)
                if r.random() < 0.5:
                    cv2.line(rgb, (dx, y + seg_h), (dx + max(1, int(3 * S)), y + seg_h), tuple(map(float, c)), 1)
    # scan band: one hot horizontal sweep + minor rolling bands
    band_y = int(h * (0.25 + 0.5 * (seed % 7) / 7.0))
    band = np.exp(-((yy - band_y) / (26.0 * S + 4)) ** 2)
    rgb = np.clip(rgb + band[..., None] * cyan * 0.35, 0, 1)
    roll = (np.sin(yy / max(2.0, 6 * S)) > 0.6).astype(np.float32) * 0.03
    rgb = np.clip(rgb + roll[..., None], 0, 1)
    specM = np.clip(specM + band * 70, 0, 255)
    specR = np.clip(specR - band * 90, 6, 255)
    rgb = np.clip(rgb + cv2.GaussianBlur(glow, (0, 0), 7 * S + 1) * 0.8, 0, 1)
    lum = rgb.mean(axis=2)
    specM = np.maximum(specM, np.clip(lum * 2.2 - 0.35, 0, 1) * 252)
    specR = np.minimum(specR, 232 - np.clip(lum * 2.0 - 0.3, 0, 1) * 200)
    specC = 232 - np.clip(lum * 1.8, 0, 1) * 200
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 15 shuriken_storm
# MECHANISM: 4-blade shuriken star SDFs with 2-tone blade faces + spin arc-trails + kunai +
# embed cracks + crimson ribbon accents. (anime2_speed_lines "Shuriken Storm")

@_structure("shuriken_storm")
def _b_shuriken_storm(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 29 + 5)
    steelbg = _fbm(shape, seed * 3 + 1, 4, 4.0, aniso=(1.0, 0.35))
    rgb = _ramp(steelbg, [(0.15, 0.17, 0.22), (0.23, 0.25, 0.31), (0.33, 0.36, 0.43)])
    specM = 40 + steelbg * 110
    specR = 150 + (steelbg - 0.5) * 130
    specC = 170 + (steelbg - 0.5) * 130
    # diagonal motion wash
    yy, xx = _mg(shape)
    wash = (np.sin((xx + yy * 0.4) / max(3.0, 26 * S)) > 0.86).astype(np.float32)
    rgb += wash[..., None] * 0.03
    crim = np.array([0.78, 0.10, 0.16], np.float32)
    # crimson ribbons (rare, flowing)
    for _ in range(max(5, int(14 * S + 2))):
        x, y = r.random() * w, r.random() * h
        a = r.random() * 2 * np.pi
        p = []
        for _ in range(int(30 + 40 * r.random())):
            a += (r.random() - 0.5) * 0.5
            x += np.cos(a) * 7 * S
            y += np.sin(a) * 7 * S
            p.append((int(x), int(y)))
        cv2.polylines(rgb, [np.array(p, np.int32)], False, tuple(map(float, crim)), max(1, int(3.5 * S)), cv2.LINE_AA)
        cv2.polylines(specM, [np.array(p, np.int32)], False, float(170), max(1, int(3.5 * S)))
        cv2.polylines(specR, [np.array(p, np.int32)], False, float(70), max(1, int(3.5 * S)))
    def blade_star(cx, cy, R_, rot, sub_rgb=None):
        # concave 4-blade: alternate long spike / deep notch with curve points
        ang = rot + np.arange(16) * (np.pi / 8)
        rad = np.tile([1.0, 0.62, 0.28, 0.62], 4) * R_
        px = cx + rad * np.cos(ang)
        py = cy + rad * np.sin(ang)
        return np.stack([px, py], axis=1).astype(np.int32)
    n_sh = max(110, int(420 * S * S) + 20)
    for _ in range(n_sh):
        x, y = r.random() * w, r.random() * h
        R_ = (10 + 19 * r.random()) * S + 3.5
        rot = r.random() * np.pi
        tier = _tier8(r, 0.60, 1.15)
        c_lit = np.minimum(np.array([0.86, 0.90, 0.97], np.float32) * tier, 1.0)
        c_drk = c_lit * 0.45
        # spin trails first (behind)
        n_tr = 2 + int(r.integers(0, 2))
        for k in range(n_tr):
            tr = int(R_ * (1.5 + 0.8 * k))
            a0 = np.rad2deg(rot) + k * 30 + r.random() * 40
            cv2.ellipse(rgb, (int(x), int(y)), (tr, tr), 0, a0, a0 + 90 + 60 * r.random(),
                        tuple(map(float, c_lit * 0.65)), max(1, int(1.5 * S)), cv2.LINE_AA)
            cv2.ellipse(specR, (int(x), int(y)), (tr, tr), 0, a0, a0 + 120, float(24 + 70 * r.random()), 1)
            cv2.ellipse(specM, (int(x), int(y)), (tr, tr), 0, a0, a0 + 120, float(120 + 120 * r.random()), 1)
        poly = blade_star(x, y, R_, rot)
        cv2.fillPoly(rgb, [poly], tuple(map(float, c_drk)), cv2.LINE_AA)
        poly2 = blade_star(x, y, R_ * 0.86, rot + 0.10)
        cv2.fillPoly(rgb, [poly2], tuple(map(float, c_lit)), cv2.LINE_AA)
        cv2.circle(rgb, (int(x), int(y)), max(1, int(R_ * 0.18)), (0.05, 0.05, 0.07), -1, cv2.LINE_AA)
        cv2.fillPoly(specM, [poly], float(140 + 112 * tier), cv2.LINE_AA)
        cv2.fillPoly(specR, [poly], float(10 + 70 * (1 - tier)), cv2.LINE_AA)
        cv2.fillPoly(specC, [poly], float(16 + 90 * (1 - tier)), cv2.LINE_AA)
        # embed cracks behind the largest
        if R_ > 16 * S + 2 and r.random() < 0.5:
            for _ in range(int(3 + r.integers(0, 4))):
                a = r.random() * 2 * np.pi
                L = R_ * (1.6 + 1.4 * r.random())
                mx = x + np.cos(a) * R_ * 1.1
                my = y + np.sin(a) * R_ * 1.1
                ex = x + np.cos(a + (r.random() - 0.5) * 0.5) * L
                ey = y + np.sin(a + (r.random() - 0.5) * 0.5) * L
                cv2.line(rgb, (int(mx), int(my)), (int(ex), int(ey)), (0.04, 0.04, 0.06), 1, cv2.LINE_AA)
    # kunai blades
    for _ in range(max(18, int(66 * S * S) + 6)):
        x, y = r.random() * w, r.random() * h
        a = r.random() * 2 * np.pi
        L = (16 + 18 * r.random()) * S + 4
        ca, sa = np.cos(a), np.sin(a)
        tier = _tier8(r, 0.5, 1.0)
        c = np.array([0.75, 0.80, 0.88], np.float32) * tier
        tip = (x + ca * L, y + sa * L)
        b1 = (x - sa * L * 0.16, y + ca * L * 0.16)
        b2 = (x + sa * L * 0.16, y - ca * L * 0.16)
        poly = np.array([tip, b1, b2], np.int32)
        cv2.fillPoly(rgb, [poly], tuple(map(float, c)), cv2.LINE_AA)
        hx, hy = x - ca * L * 0.45, y - sa * L * 0.45
        cv2.line(rgb, (int(x), int(y)), (int(hx), int(hy)), tuple(map(float, c * 0.5)), max(1, int(3 * S)), cv2.LINE_AA)
        cv2.circle(rgb, (int(hx), int(hy)), max(1, int(3.5 * S)), tuple(map(float, c * 0.8)), 1, cv2.LINE_AA)
        cv2.fillPoly(specM, [poly], float(252), cv2.LINE_AA)
        cv2.fillPoly(specR, [poly], float(12 + 30 * (1 - tier)), cv2.LINE_AA)
    return {"rgb": np.clip(rgb, 0, 1).astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 16 raiton_lightning
# MECHANISM: dendritic stepped-zigzag lightning nest — recursive forks, white-hot core in cyan
# sheath, mauve echo bolts, ionization sparks. (anime2_energy_aura "Raiton Lightning")

@_structure("raiton_lightning")
def _b_raiton_lightning(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 31 + 8)
    cloud = _fbm(shape, seed * 3 + 6, 4, 3.5)
    rgb = _ramp(cloud, [(0.03, 0.03, 0.09), (0.06, 0.05, 0.14), (0.10, 0.08, 0.20), (0.05, 0.04, 0.12)])
    specM = np.full((h, w), 26.0, np.float32)
    specR = 205 + (cloud - 0.5) * 60
    specC = 220 + (cloud - 0.5) * 50
    sheath = np.zeros((h, w), np.float32)
    core = np.zeros((h, w), np.float32)
    echo = np.zeros((h, w), np.float32)

    def bolt(x, y, a, L_total, depth, buf, th):
        # stepped zigzag: hard segments with sharp angle breaks (anime lightning)
        p = [(int(x), int(y))]
        travelled = 0.0
        while travelled < L_total:
            seg = (9 + 15 * r.random()) * S + 3
            a += (r.random() - 0.5) * 1.5
            x += np.cos(a) * seg
            y += np.sin(a) * seg
            travelled += seg
            p.append((int(x), int(y)))
            if depth > 0 and r.random() < 0.30:
                bolt(x, y, a + (0.7 + 0.8 * r.random()) * (1 if r.random() < 0.5 else -1),
                     L_total * (0.30 + 0.25 * r.random()), depth - 1, buf, max(1, th - 1))
        cv2.polylines(buf, [np.array(p, np.int32)], False, 1.0, th, cv2.LINE_AA)
        return x, y

    n_main = max(10, int(24 * S + 5))
    for _ in range(n_main):
        edge = int(r.integers(0, 4))
        if edge == 0: x, y, a = r.random() * w, -10.0, np.pi / 2
        elif edge == 1: x, y, a = r.random() * w, h + 10.0, -np.pi / 2
        elif edge == 2: x, y, a = -10.0, r.random() * h, 0.0
        else: x, y, a = w + 10.0, r.random() * h, np.pi
        a += (r.random() - 0.5) * 0.8
        L = (0.5 + 0.6 * r.random()) * h
        bolt(x, y, a, L, 3, sheath, max(2, int(5 * S)))
        bolt(x, y, a, L * 0.98, 2, core, max(1, int(2 * S)))
    for _ in range(n_main * 2):
        x, y = r.random() * w, r.random() * h
        bolt(x, y, r.random() * 2 * np.pi, (0.12 + 0.2 * r.random()) * h, 1, echo, 1)
    # ionization sparks at random points on the core
    ys, xs = np.where(core > 0.5)
    if len(ys):
        for _ in range(max(60, int(300 * S * S))):
            i = int(r.integers(0, len(ys)))
            cv2.circle(rgb, (int(xs[i]), int(ys[i])), max(1, int(2 * S)),
                       (0.8, 0.95, 1.0), -1, cv2.LINE_AA)
    shb = cv2.GaussianBlur(sheath, (0, 0), 9 * S + 1.5)
    rgb = np.clip(rgb + shb[..., None] * np.array([0.10, 0.35, 0.75]) * 1.2, 0, 1)
    rgb = np.clip(rgb + sheath[..., None] * np.array([0.15, 0.55, 0.95]) * 0.8, 0, 1)
    rgb = np.clip(rgb + echo[..., None] * np.array([0.45, 0.30, 0.65]) * 0.5, 0, 1)
    rgb = np.clip(rgb + core[..., None] * np.array([0.95, 0.98, 1.0]), 0, 1)
    specM = np.maximum(specM, sheath * 170)
    specM = np.maximum(specM, core * 252)
    specM = np.maximum(specM, echo * 110)
    specR = np.where(core > 0.4, 6.0, np.where(sheath > 0.4, 34.0, specR))
    specC = np.where(core > 0.4, 16.0, np.where(sheath > 0.4, 40.0, specC))
    specR = specR - shb * 60
    rgb = _pop(rgb, shape, seed, sat=1.08, grain=0.02)
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 17 iris_gem_field
# MECHANISM: packed anime-eye irises — limbal ring, radial fiber spokes, jewel heterochromia,
# offset window catchlights; lash-dark gaps with sparkle dust. (anime2_crystal "Iris Gem Field")

@_structure("iris_gem_field")
def _b_iris_gem_field(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 33 + 2)
    rgb = _ramp(_fbm(shape, seed * 3 + 4, 4, 6.0), [(0.05, 0.03, 0.09), (0.10, 0.06, 0.15), (0.16, 0.09, 0.20)])
    specM = 30 + _fbm(shape, seed * 5 + 1, 3, 8.0) * 40
    specR = np.full((h, w), 195.0, np.float32)
    specC = np.full((h, w), 205.0, np.float32)
    jewels = np.array([(0.15, 0.75, 0.45), (0.85, 0.18, 0.30), (0.20, 0.45, 0.95),
                       (0.95, 0.65, 0.15), (0.60, 0.25, 0.90), (0.10, 0.75, 0.80),
                       (0.95, 0.35, 0.60), (0.75, 0.80, 0.30)], np.float32)
    # occupancy-jittered placement (loose packing)
    cell = int(90 * S + 18)
    n_dust = max(300, int(1900 * S * S))
    for _ in range(n_dust):
        x, y = int(r.random() * w), int(r.random() * h)
        cv2.circle(rgb, (x, y), max(1, int(1.4 * S)), tuple(map(float, jewels[int(r.integers(0, 8))] * _tier8(r, 0.2, 0.7))), -1)
    for gy in range(0, h + cell, cell):
        for gx in range(0, w + cell, cell):
            if r.random() < 0.14:
                continue
            cx = gx + int(r.random() * cell * 0.7)
            cy = gy + int(r.random() * cell * 0.7)
            R_ = (16 + 26 * r.random()) * S + 5
            base = jewels[int(r.integers(0, len(jewels)))]
            tier = _tier8(r, 0.55, 1.05)
            n_fib = int(26 + r.integers(0, 34))
            # iris body with radial fibers (drawn as angular wedge lines)
            cv2.circle(rgb, (cx, cy), int(R_), tuple(map(float, base * 0.35 * tier)), -1, cv2.LINE_AA)
            for fi in range(n_fib):
                a = fi / n_fib * 2 * np.pi + r.random() * 0.08
                b = 0.5 + 0.6 * _LADDER8[int(r.integers(0, 8))]
                c = np.minimum(base * b * tier, 1.0)
                x0 = cx + np.cos(a) * R_ * 0.30
                y0 = cy + np.sin(a) * R_ * 0.30
                x1 = cx + np.cos(a) * R_ * 0.94
                y1 = cy + np.sin(a) * R_ * 0.94
                cv2.line(rgb, (int(x0), int(y0)), (int(x1), int(y1)), tuple(map(float, c)), max(1, int(1.6 * S)), cv2.LINE_AA)
                cv2.line(specM, (int(x0), int(y0)), (int(x1), int(y1)), float(90 + 162 * b), max(1, int(1.6 * S)))
                cv2.line(specR, (int(x0), int(y0)), (int(x1), int(y1)), float(20 + 70 * (1 - b)), max(1, int(1.6 * S)))
            # limbal ring + inner shade ring + pupil
            cv2.circle(rgb, (cx, cy), int(R_), tuple(map(float, base * 0.12)), max(1, int(2.5 * S)), cv2.LINE_AA)
            cv2.circle(rgb, (cx, cy), int(R_ * 0.55), tuple(map(float, base * 0.55 * tier)), max(1, int(1.5 * S)), cv2.LINE_AA)
            cv2.circle(rgb, (cx, cy), max(2, int(R_ * 0.26)), (0.03, 0.02, 0.05), -1, cv2.LINE_AA)
            cv2.circle(specR, (cx, cy), int(R_), float(160), max(1, int(2.5 * S)))
            cv2.circle(specM, (cx, cy), max(2, int(R_ * 0.26)), float(10), -1)
            cv2.circle(specR, (cx, cy), max(2, int(R_ * 0.26)), float(60), -1)
            cv2.circle(specC, (cx, cy), max(2, int(R_ * 0.26)), float(16), -1)
            # window catchlights (THE anime eye signature)
            hx = cx - int(R_ * 0.38)
            hy = cy - int(R_ * 0.38)
            cv2.circle(rgb, (hx, hy), max(2, int(R_ * 0.20)), (1.0, 1.0, 1.0), -1, cv2.LINE_AA)
            cv2.circle(rgb, (cx + int(R_ * 0.30), cy + int(R_ * 0.34)), max(1, int(R_ * 0.10)), (0.95, 0.97, 1.0), -1, cv2.LINE_AA)
            cv2.ellipse(rgb, (cx, cy), (int(R_ * 0.74), int(R_ * 0.74)), 0, 300, 345, (0.9, 0.94, 1.0), max(1, int(1.5 * S)), cv2.LINE_AA)
            cv2.circle(specM, (hx, hy), max(2, int(R_ * 0.20)), float(252), -1)
            cv2.circle(specR, (hx, hy), max(2, int(R_ * 0.20)), float(6), -1)
            cv2.circle(specC, (hx, hy), max(2, int(R_ * 0.20)), float(16), -1)
    rgb = _glow(np.clip(rgb, 0, 1), 5 * S + 1, 0.08)
    rgb = _pop(rgb, shape, seed, sat=1.15, grain=0.03)
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 18 holo_idol_foil
# MECHANISM: holographic sticker foil — warped diagonal rainbow bands + thin interference
# fringes + micro-prism facet lattice + sticker star/heart confetti. (anime2_gradient_hair)

@_structure("holo_idol_foil")
def _b_holo_idol_foil(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 35 + 6)
    yy, xx = _mg(shape)
    diag = (xx + yy * 0.8) / (w + h * 0.8)
    warp = (_fbm(shape, seed * 3 + 8, 4, 4.0) - 0.5) * 0.35
    t = (diag + warp) * 3.0 % 1.0
    rainbow = [(1.0, 0.55, 0.70), (1.0, 0.80, 0.45), (0.95, 0.98, 0.55), (0.55, 0.95, 0.70),
               (0.50, 0.85, 1.0), (0.65, 0.60, 1.0), (0.95, 0.60, 0.95), (1.0, 0.55, 0.70)]
    rgb = _ramp(t, rainbow)
    fringe = 0.5 + 0.5 * np.sin((diag + warp) * np.pi * 2 * max(60, 140 * S))
    rgb *= (0.82 + 0.28 * fringe[..., None])
    # micro-prism facet lattice: two rotated square lattices -> facet id -> hue nudge + dark edge
    cellpx = max(5.0, 11.0 * S)
    a1, a2 = np.deg2rad(8.0), np.deg2rad(53.0)
    u1 = np.floor((xx * np.cos(a1) + yy * np.sin(a1)) / cellpx)
    v1 = np.floor((-xx * np.sin(a1) + yy * np.cos(a1)) / cellpx)
    u2 = np.floor((xx * np.cos(a2) + yy * np.sin(a2)) / (cellpx * 1.35))
    fid = (u1 * 73856093 + v1 * 19349663 + u2 * 83492791) % 8
    nudge = (fid.astype(np.float32) / 8.0 - 0.5) * 0.16
    rgb = np.clip(_ramp((t + nudge) % 1.0, rainbow) * (0.82 + 0.28 * fringe[..., None]) * 0.55 + rgb * 0.45, 0, 1)
    e1 = _band_ink(fid.astype(np.float32), 1)
    rgb *= (1 - e1[..., None] * 0.42)
    rgb = np.clip(rgb * (0.90 + 0.20 * (fid.astype(np.float32) / 7.0 - 0.5)[..., None]), 0, 1)
    # glint sparks along band boundaries
    bandedge = np.abs(fringe - 0.5) < 0.06
    ys_, xs_ = np.where(bandedge)
    if len(ys_):
        for _ in range(max(260, int(1500 * S * S))):
            i = int(r.integers(0, len(ys_)))
            x, y = int(xs_[i]), int(ys_[i])
            L = max(2, int((3 + 5 * r.random()) * S + 1))
            cv2.line(rgb, (x - L, y), (x + L, y), (1.0, 1.0, 1.0), 1, cv2.LINE_AA)
            cv2.line(rgb, (x, y - L), (x, y + L), (1.0, 1.0, 1.0), 1, cv2.LINE_AA)
    # sticker confetti: outlined stars + hearts (dielectric patches on the foil)
    conf_mask = np.zeros((h, w), np.float32)
    for _ in range(max(50, int(300 * S * S))):
        x, y = int(r.random() * w), int(r.random() * h)
        sz = (7 + 12 * r.random()) * S + 2.5
        gold = r.random() < 0.4
        c = (1.0, 0.85, 0.35) if gold else (1.0, 1.0, 1.0)
        if r.random() < 0.6:
            pts = _star_pts(x, y, 4 if r.random() < 0.7 else 5, sz, sz * 0.4, r.random() * np.pi)
            cv2.fillPoly(rgb, [pts], c, cv2.LINE_AA)
            cv2.fillPoly(conf_mask, [pts], 1.0, cv2.LINE_AA)
        else:
            rr_ = max(1, int(sz * 0.42))
            cv2.circle(rgb, (x - rr_, y - rr_ // 2), rr_, c, -1, cv2.LINE_AA)
            cv2.circle(rgb, (x + rr_, y - rr_ // 2), rr_, c, -1, cv2.LINE_AA)
            tri = np.array([[x - rr_ * 2, y - rr_ // 4], [x + rr_ * 2, y - rr_ // 4], [x, y + int(sz)]], np.int32)
            cv2.fillPoly(rgb, [tri], c, cv2.LINE_AA)
            cv2.fillPoly(conf_mask, [tri], 1.0, cv2.LINE_AA)
            cv2.circle(conf_mask, (x - rr_, y - rr_ // 2), rr_, 1.0, -1, cv2.LINE_AA)
            cv2.circle(conf_mask, (x + rr_, y - rr_ // 2), rr_, 1.0, -1, cv2.LINE_AA)
    # ---- married spec: foil = metal with fringe-modulated roughness; confetti = paint patches
    M = 205 + fringe * 47 - nudge * 60
    R = 10 + (1 - fringe) * 52 + e1 * 70
    CC = 16 + (fid.astype(np.float32) / 7.0) * 96 + (1 - fringe) * 42
    M = M * (1 - conf_mask) + 18 * conf_mask
    R = R * (1 - conf_mask) + 128 * conf_mask
    CC = CC * (1 - conf_mask) + 90 * conf_mask
    return {"rgb": np.clip(rgb, 0, 1).astype(np.float32), "spec": _spec_pack(M, R, CC)}


# ============================================================================ 19 kanji_rain
# MECHANISM: procedural pseudo-glyph stroke assembly (bars/hooks/ticks/radical boxes — NOT real
# text) falling in washi columns with echo trails + motion streaks. (anime2_kanji_rain)

def _pseudo_glyph(targets, x, y, K, th, r):
    """2–5 kanji-ish strokes in a KxK box (h/v bars, hooks, diagonal ticks, radical boxes),
    drawn identically into every (img, colour) target — rgb + spec planes in one pass."""
    n_strokes = 2 + int(r.integers(0, 4))
    prims = []
    for _ in range(n_strokes):
        kind = r.random()
        if kind < 0.30:      # horizontal bar
            fy = y + int(K * (0.15 + 0.7 * r.random()))
            prims.append(("l", (x + int(K * 0.08), fy), (x + int(K * 0.92), fy)))
        elif kind < 0.55:    # vertical bar
            fx = x + int(K * (0.2 + 0.6 * r.random()))
            prims.append(("l", (fx, y + int(K * 0.08)), (fx, y + int(K * 0.92))))
        elif kind < 0.75:    # hook (L with foot)
            fx = x + int(K * (0.25 + 0.5 * r.random()))
            fy = y + int(K * (0.15 + 0.3 * r.random()))
            fy2 = fy + int(K * (0.3 + 0.35 * r.random()))
            prims.append(("p", np.array([(fx, fy), (fx, fy2), (fx + int(K * 0.22), fy2 + int(K * 0.06))], np.int32), None))
        elif kind < 0.90:    # diagonal tick pair
            fx = x + int(K * (0.2 + 0.4 * r.random()))
            fy = y + int(K * (0.2 + 0.4 * r.random()))
            d = int(K * 0.22)
            prims.append(("l", (fx, fy), (fx + d, fy + d)))
            prims.append(("l", (fx + int(K * 0.3), fy), (fx + int(K * 0.3) - d, fy + d)))
        else:                # radical box
            bx = x + int(K * 0.2)
            by = y + int(K * 0.2)
            prims.append(("r", (bx, by), (bx + int(K * 0.45), by + int(K * 0.45))))
    for img, c in targets:
        for kind, a, b in prims:
            if kind == "l":
                cv2.line(img, a, b, c, th, cv2.LINE_AA)
            elif kind == "p":
                cv2.polylines(img, [a], False, c, th, cv2.LINE_AA)
            else:
                cv2.rectangle(img, a, b, c, th)


@_structure("kanji_rain")
def _b_kanji_rain(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 37 + 1)
    fiber = _fbm(shape, seed * 3 + 5, 4, 30.0, aniso=(1.0, 0.25))
    rgb = np.ones((h, w, 3), np.float32) * np.array([0.93, 0.89, 0.80], np.float32)
    rgb *= (0.93 + 0.10 * fiber[..., None])
    yyk, xxk = _mg(shape)
    screen = (np.sin(yyk / max(2.0, 5.5 * S)) > 0.55).astype(np.float32) * 0.085 +              (np.sin(xxk / max(3.0, 46 * S)) > 0.90).astype(np.float32) * 0.07
    rgb *= (1.0 - screen[..., None])
    specM = np.full((h, w), 24.0, np.float32)
    specR = 195 + (fiber - 0.5) * 60
    specC = np.full((h, w), 205.0, np.float32)
    ink = (0.10, 0.08, 0.10)
    verm = (0.80, 0.16, 0.12)
    faded = (0.62, 0.58, 0.54)
    colw = max(11, int(26 * S + 5))
    x = int(r.random() * colw * 0.5)
    while x < w:
        K = int(colw * (0.55 + 0.3 * r.random()))
        gap = int(K * (0.10 + 0.28 * r.random()))
        y = -int(r.random() * K * 3)
        col_kind = r.random()
        # vertical motion streaks beside the column
        if r.random() < 0.5:
            sx = x + K + max(1, int(3 * S))
            cv2.line(rgb, (sx, 0), (sx, h), (0.80, 0.74, 0.66), 1, cv2.LINE_AA)
        glyph_i = 0
        head = int(r.random() * 9) + 3
        while y < h:
            if r.random() < 0.07:
                y += int(K * (1.2 + 1.5 * r.random()))
                continue
            if col_kind < 0.14:
                c, th, mv, rv = verm, max(1, int(2.4 * S)), 252, 30
            elif col_kind < 0.30:
                c, th, mv, rv = faded, 1, 110, 110
            else:
                c, th, mv, rv = ink, max(1, int(2.0 * S)), 215, 45
            if glyph_i == head:      # bright leading glyph
                c = verm if col_kind >= 0.30 else ink
                th = max(1, int(2.8 * S))
                mv = 252
            mj = float(np.clip(mv + (_LADDER8[int(r.integers(0, 8))] - 0.5) * 40, 0, 255))
            _pseudo_glyph([(rgb, c), (specM, mj), (specR, float(rv)), (specC, float(30 + 60 * r.random()))],
                          x, y, K, th, r)
            y += K + gap
            glyph_i += 1
        x += colw + int(colw * 0.25 * r.random())
    # washi flecks (paper fibre speckle — fine detail between columns)
    for _ in range(max(400, int(2600 * S * S))):
        x2, y2 = int(r.random() * w), int(r.random() * h)
        cv2.circle(rgb, (x2, y2), max(1, int(1.2 * S)), (0.80, 0.74, 0.63), -1)
    # hanko seals scattered
    for _ in range(max(4, int(14 * S * S) + 2)):
        sx, sy = int(r.random() * w), int(r.random() * h)
        sz = int((22 + 20 * r.random()) * S + 6)
        cv2.rectangle(rgb, (sx, sy), (sx + sz, sy + sz), verm, -1, cv2.LINE_AA)
        _pseudo_glyph([(rgb, (0.93, 0.89, 0.80))], sx + 2, sy + 2, sz - 4, max(1, int(2 * S)), r)
        specM[sy:sy + sz, sx:sx + sz] = 70
        specR[sy:sy + sz, sx:sx + sz] = 140
    return {"rgb": np.clip(rgb, 0, 1).astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 20 onomatopoeia
# MECHANISM: dense overlapping jagged comic burst balloons — double outlines, halftone/pop
# fills, slash marks, mini dust-pops. (anime2_onomatopoeia "Onomatopoeia Riot")

@_structure("onomatopoeia")
def _b_onomatopoeia(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 39 + 7)
    yy, xx = _mg(shape)
    rgb = np.ones((h, w, 3), np.float32) * np.array([0.93, 0.90, 0.84], np.float32)
    lanes = (np.sin((xx * 0.35 + yy) / max(2.5, 7 * S)) > 0.75).astype(np.float32)
    rgb -= lanes[..., None] * 0.05
    specM = np.full((h, w), 26.0, np.float32)
    specR = np.full((h, w), 200.0, np.float32)
    specC = np.full((h, w), 212.0, np.float32)
    ink = np.array([0.07, 0.06, 0.09], np.float32)
    newsprint = _dot_lattice(xx, yy, 40.0, max(3.5, 7.5 * S), np.float32(0.42))
    rgb *= (1.0 - newsprint[..., None] * 0.24)
    grain_o = (_vgrid(shape, seed * 47 + 5, h // 2, w // 2) - 0.5) * 0.09
    rgb = np.clip(rgb + grain_o[..., None], 0, 1)
    pops = np.array([(1.0, 0.85, 0.10), (0.20, 0.85, 0.95), (0.95, 0.30, 0.60),
                     (1.0, 1.0, 1.0), (0.95, 0.45, 0.12), (0.55, 0.90, 0.30)], np.float32)
    pop_m = [250, 205, 230, 60, 245, 190]
    pop_r = [28, 45, 38, 130, 32, 55]

    def burst(cx, cy, R_, filled=True):
        n_spk = int(9 + r.integers(0, 10))
        ang = np.arange(2 * n_spk) * (np.pi / n_spk) + r.random() * np.pi
        dep = 0.30 + 0.35 * r.random()
        rad = np.where(np.arange(2 * n_spk) % 2 == 0, R_, R_ * (1 - dep))
        rad = rad * (0.85 + 0.3 * r.random(2 * n_spk))
        pts = np.stack([cx + rad * np.cos(ang), cy + rad * np.sin(ang)], axis=1).astype(np.int32)
        pi = int(r.integers(0, len(pops)))
        c = pops[pi]
        # double outline: fat ink, white gap, fill
        cv2.fillPoly(rgb, [pts], tuple(map(float, ink)), cv2.LINE_AA)
        pts2 = ((pts - [cx, cy]) * 0.90 + [cx, cy]).astype(np.int32)
        cv2.fillPoly(rgb, [pts2], (0.97, 0.96, 0.93), cv2.LINE_AA)
        pts3 = ((pts - [cx, cy]) * 0.80 + [cx, cy]).astype(np.int32)
        if filled:
            cv2.fillPoly(rgb, [pts3], tuple(map(float, c)), cv2.LINE_AA)
            cv2.fillPoly(specM, [pts3], float(pop_m[pi]), cv2.LINE_AA)
            cv2.fillPoly(specR, [pts3], float(pop_r[pi]), cv2.LINE_AA)
            cv2.fillPoly(specC, [pts3], float(16 + 40 * (pi % 3)), cv2.LINE_AA)
            # interior: halftone or slash marks
            x0, x1 = max(0, int(cx - R_)), min(w, int(cx + R_))
            y0, y1 = max(0, int(cy - R_)), min(h, int(cy + R_))
            if x1 > x0 and y1 > y0:
                inner = np.zeros((h, w), np.uint8)
                cv2.fillPoly(inner, [pts3], 1)
                sub = inner[y0:y1, x0:x1].astype(bool)
                cellp = max(2.6, 5.6 * S)
                du = (xx[y0:y1, x0:x1] / cellp) % 1.0 - 0.5
                dv = (yy[y0:y1, x0:x1] / cellp) % 1.0 - 0.5
                lxs = xx[y0:y1, x0:x1] - cx
                lys = yy[y0:y1, x0:x1] - cy
                shade = (lxs + lys) > R_ * 0.25          # lower-right comic shading crescent
                dots = (np.sqrt(du * du + dv * dv) < np.where(shade, 0.30, 0.16)) & sub
                rgb[y0:y1, x0:x1][dots] = ink * 0.9 + c * 0.1
                specM[y0:y1, x0:x1][dots] = 180
                if r.random() < 0.5:
                    n_sl = 2 + int(r.integers(0, 3))
                    for _ in range(n_sl):
                        a = r.random() * np.pi
                        L = R_ * (0.45 + 0.25 * r.random())
                        mx = cx + (r.random() - 0.5) * R_ * 0.5
                        my = cy + (r.random() - 0.5) * R_ * 0.5
                        cv2.line(rgb, (int(mx - L * np.cos(a)), int(my - L * np.sin(a))),
                                 (int(mx + L * np.cos(a)), int(my + L * np.sin(a))),
                                 tuple(map(float, ink)), max(2, int(5 * S)), cv2.LINE_AA)
        else:
            cv2.fillPoly(rgb, [pts3], (0.97, 0.96, 0.93), cv2.LINE_AA)
            st = _star_pts(int(cx), int(cy), 4, R_ * 0.35, R_ * 0.12, r.random() * np.pi)
            cv2.fillPoly(rgb, [st], tuple(map(float, c)), cv2.LINE_AA)
            cv2.fillPoly(specM, [st], float(pop_m[pi]), cv2.LINE_AA)

    n_big = max(70, int(300 * S * S) + 20)
    order = []
    for _ in range(n_big):
        order.append((r.random() * w, r.random() * h, (16 + 34 * r.random()) * S + 5, True))
    for _ in range(max(100, int(520 * S * S))):
        order.append((r.random() * w, r.random() * h, (7 + 12 * r.random()) * S + 2.5, False))
    r.shuffle(order)
    for cx, cy, R_, big in order:
        burst(cx, cy, R_, big)
    # action dashes + speckle between bursts (kills the flat-fill read)
    for _ in range(max(600, int(3400 * S * S))):
        x, y = int(r.random() * w), int(r.random() * h)
        a = r.random() * np.pi
        L = max(2, int((4 + 8 * r.random()) * S + 1))
        cv2.line(rgb, (int(x - L * np.cos(a)), int(y - L * np.sin(a))), (int(x + L * np.cos(a)), int(y + L * np.sin(a))),
                 tuple(map(float, ink)), 1, cv2.LINE_AA)
    return {"rgb": np.clip(rgb, 0, 1).astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 21 cyber_glitch
# MECHANISM: slice-displacement with RGB split applied to PAINT AND SPEC TOGETHER + pixel-sort
# streak runs + corrupted neon block mosaics + inverted rects. (anime2_glitch "Cyber Glitch")

@_structure("cyber_glitch")
def _b_cyber_glitch(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 41 + 3)
    yy, xx = _mg(shape)
    base = _fbm(shape, seed * 3 + 2, 4, 5.0)
    rgb = _ramp(base, [(0.02, 0.02, 0.05), (0.06, 0.05, 0.12), (0.10, 0.10, 0.18), (0.05, 0.04, 0.10)])
    circuit = (_fbm(shape, seed * 5 + 8, 3, 24.0, aniso=(0.15, 1.0)) > 0.62).astype(np.float32)
    base_r = _fbm(shape, seed * 13 + 6, 4, 7.0)   # independent roughness carrier (spec channel independence)
    base_cc = _fbm(shape, seed * 17 + 9, 4, 5.5)  # independent clearcoat carrier
    rgb += circuit[..., None] * np.array([0.02, 0.10, 0.08])
    neon = np.array([(1.0, 0.10, 0.65), (0.10, 0.95, 1.0), (0.55, 1.0, 0.15), (0.95, 0.95, 1.0)], np.float32)
    M = 30 + base * 50 + circuit * 90
    R = 205 - base_r * 130 - circuit * 60
    CC = 225 - base_cc * 160 - circuit * 40
    # pixel-sort streak runs (horizontal luminance ramps from random seeds)
    for _ in range(max(180, int(950 * S * S))):
        x, y = int(r.random() * w), int(r.random() * h)
        L = int((18 + 90 * r.random()) * S + 6)
        c = neon[int(r.integers(0, len(neon)))] * _tier8(r, 0.4, 1.0)
        x1 = min(w - 1, x + L)
        if x1 <= x:
            continue
        ramp_v = np.linspace(1.0, 0.15, x1 - x, dtype=np.float32)[None, :, None]
        yy0 = min(y, h - 1)
        band = max(1, int(1.5 * S))
        y1_ = min(h, yy0 + band)
        rgb[yy0:y1_, x:x1] = rgb[yy0:y1_, x:x1] * (1 - ramp_v) + c[None, None, :] * ramp_v
        sch = int(r.integers(0, 3))   # each pixel-sort streak hits ONE spec channel
        if sch == 0:
            M[yy0:y1_, x:x1] = np.maximum(M[yy0:y1_, x:x1], 252 * ramp_v[:, :, 0])
        elif sch == 1:
            R[yy0:y1_, x:x1] = np.minimum(R[yy0:y1_, x:x1], 12 + 150 * (1 - ramp_v[:, :, 0]))
        else:
            CC[yy0:y1_, x:x1] = np.minimum(CC[yy0:y1_, x:x1], 16 + 190 * (1 - ramp_v[:, :, 0]))
    # corrupted block mosaics: neon mini-checkers
    for _ in range(max(60, int(300 * S * S))):
        bx, by = int(r.random() * w), int(r.random() * h)
        bw = int((8 + 30 * r.random()) * S + 3)
        bh = int((6 + 22 * r.random()) * S + 3)
        sub = max(2, int(bw / (2 + int(r.integers(0, 3)))))
        for cy2 in range(by, min(h, by + bh), sub):
            for cx2 in range(bx, min(w, bx + bw), sub):
                if r.random() < 0.85:
                    c = neon[int(r.integers(0, len(neon)))] * _tier8(r, 0.3, 1.0)
                    cv2.rectangle(rgb, (cx2, cy2), (min(w - 1, cx2 + sub - 1), min(h - 1, cy2 + sub - 1)),
                                  tuple(map(float, c)), -1)
                    ch = int(r.integers(0, 3))   # corrupt ONE spec channel per cell (RGB-split in the SPEC)
                    tgt = (M, R, CC)[ch]
                    val = (252.0, 8.0, 16.0)[ch] if r.random() < 0.5 else (4.0, 235.0, 240.0)[ch]
                    cv2.rectangle(tgt, (cx2, cy2), (min(w - 1, cx2 + sub - 1), min(h - 1, cy2 + sub - 1)), float(val), -1)
    # inverted rects
    for _ in range(max(6, int(22 * S * S) + 2)):
        bx, by = int(r.random() * w), int(r.random() * h)
        bw, bh = int((30 + 80 * r.random()) * S + 8), int((10 + 30 * r.random()) * S + 4)
        x1_, y1_ = min(w, bx + bw), min(h, by + bh)
        rgb[by:y1_, bx:x1_] = 1.0 - rgb[by:y1_, bx:x1_]
        R[by:y1_, bx:x1_] = 255 - R[by:y1_, bx:x1_]
    # THE GLITCH: slice displacement + RGB split applied to rgb AND spec identically
    n_slices = max(14, int(34 * S + 8))
    for _ in range(n_slices):
        sy = int(r.random() * h)
        sh_ = int((5 + 55 * r.random()) * S + 2)
        y1_ = min(h, sy + sh_)
        dx = int((r.random() - 0.5) * 240 * S)
        dr = dx + int((r.random() - 0.5) * 30 * S)
        db = dx - int((r.random() - 0.5) * 30 * S)
        rgb[sy:y1_, :, 0] = np.roll(rgb[sy:y1_, :, 0], dr, axis=1)
        rgb[sy:y1_, :, 1] = np.roll(rgb[sy:y1_, :, 1], dx, axis=1)
        rgb[sy:y1_, :, 2] = np.roll(rgb[sy:y1_, :, 2], db, axis=1)
        M[sy:y1_] = np.roll(M[sy:y1_], dx, axis=1)
        R[sy:y1_] = np.roll(R[sy:y1_], dr, axis=1)
        CC[sy:y1_] = np.roll(CC[sy:y1_], db, axis=1)
        if r.random() < 0.25:   # duplicated echo slice
            ey = int(r.random() * h)
            e1_ = min(h, ey + (y1_ - sy))
            span = e1_ - ey
            rgb[ey:e1_] = np.clip(rgb[ey:e1_] * 0.4 + rgb[sy:sy + span] * 0.6, 0, 1)
    # channel-desync: a few slices roll ONLY one spec channel (spec-side RGB split)
    for _ in range(max(22, int(48 * S + 8))):
        sy = int(r.random() * h)
        y1_ = min(h, sy + int((6 + 40 * r.random()) * S + 2))
        dx = int((r.random() - 0.5) * 300 * S)
        tgt = (M, R, CC)[int(r.integers(0, 3))]
        tgt[sy:y1_] = np.roll(tgt[sy:y1_], dx, axis=1)
    # scanline dither
    scan = (yy.astype(np.int32) % max(3, int(6 * S))) == 0
    rgb[scan] *= 0.82
    rgb = _pop(rgb, shape, seed, sat=1.10, grain=0.02)
    return {"rgb": np.clip(rgb, 0, 1).astype(np.float32), "spec": _spec_pack(M, R, CC)}


# ============================================================================ 22 retro_broadcast
# MECHANISM: CRT raster — phosphor RGB stripe triads over fragmented test-bar patches, scanlines,
# interlace jitter bands, chroma aberration, static bursts, rolling band. (anime2_broadcast)

@_structure("retro_broadcast")
def _b_retro_broadcast(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 43 + 9)
    yy, xx = _mg(shape)
    # underlying 'image': fragmented rotated test-bar patches on warm dark
    rgb = _ramp(_fbm(shape, seed * 3 + 3, 3, 3.0), [(0.06, 0.04, 0.05), (0.10, 0.07, 0.08), (0.14, 0.10, 0.10)])
    bars = np.array([(0.75, 0.75, 0.75), (0.75, 0.75, 0.10), (0.10, 0.75, 0.75), (0.10, 0.75, 0.10),
                     (0.75, 0.10, 0.75), (0.75, 0.10, 0.10), (0.10, 0.10, 0.75), (0.05, 0.05, 0.05)], np.float32)
    bar_m = [70, 220, 190, 160, 235, 245, 205, 30]
    M = np.full((h, w), 40.0, np.float32)
    R = np.full((h, w), 190.0, np.float32)
    CC = np.full((h, w), 200.0, np.float32)
    for _ in range(max(14, int(46 * S * S) + 6)):
        cx, cy = int(r.random() * w), int(r.random() * h)
        pw = int((60 + 160 * r.random()) * S + 16)
        ph_ = int((30 + 90 * r.random()) * S + 10)
        ang = (r.random() - 0.5) * 40
        n_bars = 4 + int(r.integers(0, 5))
        patch = np.zeros((ph_, pw, 3), np.float32)
        patchM = np.zeros((ph_, pw), np.float32)
        bw_ = max(2, pw // n_bars)
        idx0 = int(r.integers(0, 8))
        for bi in range(n_bars):
            c = bars[(idx0 + bi) % 8]
            patch[:, bi * bw_:(bi + 1) * bw_] = c
            patchM[:, bi * bw_:(bi + 1) * bw_] = bar_m[(idx0 + bi) % 8]
        Mrot = cv2.getRotationMatrix2D((pw / 2, ph_ / 2), ang, 1.0)
        patch = cv2.warpAffine(patch, Mrot, (pw, ph_), borderValue=(0, 0, 0))
        patchM2 = cv2.warpAffine(patchM, Mrot, (pw, ph_), borderValue=0)
        x0, y0 = cx - pw // 2, cy - ph_ // 2
        xa, ya = max(0, x0), max(0, y0)
        xb, yb = min(w, x0 + pw), min(h, y0 + ph_)
        if xb <= xa or yb <= ya:
            continue
        ps = patch[ya - y0:yb - y0, xa - x0:xb - x0]
        pm = patchM2[ya - y0:yb - y0, xa - x0:xb - x0]
        msk = (ps.max(axis=2) > 0.02)[..., None].astype(np.float32) * 0.9
        rgb[ya:yb, xa:xb] = rgb[ya:yb, xa:xb] * (1 - msk) + ps * msk
        M[ya:yb, xa:xb] = np.maximum(M[ya:yb, xa:xb], pm)
        R[ya:yb, xa:xb] = np.where(pm > 50, 60 - pm / 8, R[ya:yb, xa:xb])
        CC[ya:yb, xa:xb] = np.where(pm > 50, 16 + pm / 2.2, CC[ya:yb, xa:xb])
    # ghost copy + chroma aberration
    gsh = int(14 * S + 3)
    rgb = np.clip(rgb + np.roll(rgb, (0, gsh), (0, 1)) * 0.18, 0, 1)
    rgb[..., 0] = np.roll(rgb[..., 0], int(3 * S + 1), axis=1)
    rgb[..., 2] = np.roll(rgb[..., 2], -int(3 * S + 1), axis=1)
    # static bursts (noise bands)
    for _ in range(max(5, int(14 * S + 3))):
        sy = int(r.random() * h)
        sh_ = int((4 + 26 * r.random()) * S + 2)
        y1_ = min(h, sy + sh_)
        noise = r.random((y1_ - sy, w)).astype(np.float32)
        rgb[sy:y1_] = rgb[sy:y1_] * 0.35 + noise[..., None] * 0.65
        M[sy:y1_] = 15 + noise * 237
        R[sy:y1_] = 12 + noise * 220
        CC[sy:y1_] = 16 + noise * 225
    # interlace jitter bands
    for _ in range(max(6, int(18 * S + 4))):
        sy = int(r.random() * h)
        sh_ = int((8 + 40 * r.random()) * S + 3)
        y1_ = min(h, sy + sh_)
        dx = int((r.random() - 0.5) * 26 * S)
        odd = (np.arange(sy, y1_) % 2).astype(bool)
        seg = rgb[sy:y1_]
        seg[odd] = np.roll(seg[odd], dx, axis=1)
        rgb[sy:y1_] = seg
    # phosphor triads + scanlines + rolling band
    px_ = (xx.astype(np.int32) % max(3, int(5 * S + 1)))
    tri = np.stack([(px_ == 0), (px_ == 1), (px_ == 2)], axis=2).astype(np.float32)
    rgb = np.clip(rgb * (0.55 + 0.85 * tri), 0, 1)
    M = M * (0.75 + 0.5 * tri[:, :, 1])
    scan = (yy.astype(np.int32) % max(3, int(7 * S))) < max(1, int(2 * S))
    rgb[scan] *= 0.6
    R[scan] = np.minimum(R[scan] + 40, 255)
    CC[scan] = np.minimum(CC[scan] + 46, 255)
    band_y = (seed * 331) % h
    band = np.exp(-((yy - band_y) / (60.0 * S + 10)) ** 2)
    rgb = np.clip(rgb + band[..., None] * 0.13, 0, 1)
    vig = 1.0 - 0.35 * (((xx / w - 0.5) ** 2 + (yy / h - 0.5) ** 2) * 2.2)
    rgb = np.clip(rgb * vig[..., None], 0, 1)
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(M, R, CC)}


# ============================================================================ 23 blood_moon
# MECHANISM: a FIELD of multiplied eclipse moons — cel-banded craters, bright rim arcs, cloud
# wisps crossing in front, silhouette flocks, star pinpricks. (anime2_blood_moon)

@_structure("blood_moon")
def _b_blood_moon(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 45 + 4)
    sky_f = _fbm(shape, seed * 3 + 6, 4, 3.5)
    rgb = _ramp(sky_f, [(0.07, 0.02, 0.06), (0.15, 0.04, 0.09), (0.26, 0.06, 0.11), (0.10, 0.02, 0.07)])
    specM = np.full((h, w), 24.0, np.float32)
    specR = 210 + (sky_f - 0.5) * 60
    specC = 215 + (sky_f - 0.5) * 60
    # star pinpricks
    for _ in range(max(450, int(2800 * S * S))):
        x, y = int(r.random() * w), int(r.random() * h)
        b = _tier8(r, 0.25, 0.9)
        cv2.circle(rgb, (x, y), max(1, int(1.2 * S)), (0.9 * b, 0.75 * b, 0.7 * b), -1)
        cv2.circle(specM, (x, y), max(1, int(1.2 * S)), float(140 + 100 * b), -1)
    # the moon field
    glow = np.zeros((h, w, 3), np.float32)
    n_moons = max(40, int(120 * S * S) + 16)
    for _ in range(n_moons):
        cx, cy = int(r.random() * w), int(r.random() * h)
        R_ = (20 + 52 * r.random()) * S + 8
        gold = r.random() < 0.10
        tier = _tier8(r, 0.55, 1.0)
        base = np.array([0.98, 0.72, 0.25], np.float32) if gold else np.array([0.85, 0.13, 0.10], np.float32)
        deep = base * 0.35
        cv2.circle(rgb, (cx, cy), int(R_), tuple(map(float, deep * tier)), -1, cv2.LINE_AA)
        cv2.circle(rgb, (cx, cy), int(R_ * 0.82), tuple(map(float, base * 0.65 * tier)), -1, cv2.LINE_AA)
        cv2.circle(rgb, (cx, cy), int(R_ * 0.60), tuple(map(float, base * 0.9 * tier)), -1, cv2.LINE_AA)
        cv2.circle(glow, (cx, cy), int(R_ * 1.06), tuple(map(float, base * 0.5)), max(2, int(4 * S)), cv2.LINE_AA)
        # cel-banded craters
        for _ in range(int(4 + r.integers(0, 6))):
            a = r.random() * 2 * np.pi
            d = r.random() * R_ * 0.62
            crx, cry = int(cx + np.cos(a) * d), int(cy + np.sin(a) * d)
            cr = max(1, int(R_ * (0.07 + 0.14 * r.random())))
            cv2.circle(rgb, (crx, cry), cr, tuple(map(float, base * 0.45 * tier)), -1, cv2.LINE_AA)
            cv2.circle(rgb, (crx, cry), cr, tuple(map(float, base * 1.05 * tier)), 1, cv2.LINE_AA)
            cv2.circle(specR, (crx, cry), cr, float(120 + 60 * r.random()), -1)
        # eclipse rim arc (bright)
        a0 = r.random() * 360
        rimc = (1.0, 0.85, 0.55) if not gold else (1.0, 0.95, 0.75)
        cv2.ellipse(rgb, (cx, cy), (int(R_), int(R_)), 0, a0, a0 + 100 + 80 * r.random(), rimc, max(1, int(2.5 * S)), cv2.LINE_AA)
        cv2.ellipse(glow, (cx, cy), (int(R_), int(R_)), 0, a0, a0 + 140, rimc, max(1, int(2.5 * S)), cv2.LINE_AA)
        cv2.circle(specM, (cx, cy), int(R_), float(55 + 180 * tier), -1)
        cv2.circle(specR, (cx, cy), int(R_), float(60 + 60 * (1 - tier)), -1)
        cv2.circle(specC, (cx, cy), int(R_), float(20 + 60 * (1 - tier)), -1)
        cv2.ellipse(specM, (cx, cy), (int(R_), int(R_)), 0, a0, a0 + 140, float(252), max(1, int(2.5 * S)))
        cv2.ellipse(specR, (cx, cy), (int(R_), int(R_)), 0, a0, a0 + 140, float(8), max(1, int(2.5 * S)))
    # cloud wisps crossing IN FRONT of moons (depth) — dark streaky bands
    wisp = np.clip(_fbm(shape, seed * 7 + 8, 4, 5.0, aniso=(0.25, 1.0)) * 1.9 - 0.95, 0, 1)
    rgb = rgb * (1 - wisp[..., None] * 0.75) + np.array([0.05, 0.01, 0.04]) * wisp[..., None] * 0.75
    specR = specR * (1 - wisp) + 225 * wisp
    specM = specM * (1 - wisp) + 26 * wisp
    # silhouette flocks
    for _ in range(max(30, int(160 * S * S))):
        x, y = int(r.random() * w), int(r.random() * h)
        L = max(2, int((4 + 6 * r.random()) * S + 1))
        c = (0.02, 0.01, 0.02)
        cv2.line(rgb, (x - L, y), (x, y - int(L * 0.6)), c, max(1, int(1.4 * S)), cv2.LINE_AA)
        cv2.line(rgb, (x, y - int(L * 0.6)), (x + L, y), c, max(1, int(1.4 * S)), cv2.LINE_AA)
    rgb = np.clip(rgb + cv2.GaussianBlur(glow, (0, 0), 10 * S + 1.5) * 0.7, 0, 1)
    rgb = _pop(rgb, shape, seed, sat=1.15, grain=0.025)
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 24 oni_sumi
# MECHANISM: sumi-e dry-brush ribbon strokes (tapered width profiles + bristle gaps) forming
# horn/fang/brow motifs + enso rings + ink flick splatter + vermillion accents + hanko seals.
# (anime2_oni_sumi "Oni Sumi-e")

def _brush_stroke(targets, pts_f, width0, r, bristle=True):
    """Tapered ribbon along pts_f with dry-brush bristle streaks. targets = [(img, colour)]."""
    n = len(pts_f)
    if n < 3:
        return
    left, right = [], []
    for i, (x, y) in enumerate(pts_f):
        t = i / (n - 1)
        wd = width0 * (0.15 + 0.85 * np.sin(np.pi * min(1.0, 0.15 + t * 0.85)))   # taper both ends
        if i == 0:
            dx, dy = pts_f[1][0] - x, pts_f[1][1] - y
        else:
            dx, dy = x - pts_f[i - 1][0], y - pts_f[i - 1][1]
        L = max(1e-3, np.hypot(dx, dy))
        nx, ny = -dy / L, dx / L
        left.append((x + nx * wd, y + ny * wd))
        right.append((x - nx * wd, y - ny * wd))
    poly = np.array(left + right[::-1], np.int32)
    for img, c in targets:
        cv2.fillPoly(img, [poly], c, cv2.LINE_AA)
    if bristle:
        # dry-brush bristle gaps: thin paper-coloured streaks re-opened along the stroke tail
        n_b = 2 + int(r.integers(0, 3))
        for k in range(n_b):
            off = (k + 1) / (n_b + 1) * 1.4 - 0.7
            bp = []
            for i in range(0, n, 2):
                x, y = pts_f[i]
                if i == 0:
                    dx, dy = pts_f[1][0] - x, pts_f[1][1] - y
                else:
                    dx, dy = x - pts_f[i - 1][0], y - pts_f[i - 1][1]
                L = max(1e-3, np.hypot(dx, dy))
                bp.append((int(x - dy / L * width0 * off), int(y + dx / L * width0 * off)))
            if len(bp) > 2 and r.random() < 0.8:
                seg = np.array(bp[int(len(bp) * 0.35):], np.int32)
                cv2.polylines(targets[0][0], [seg], False, (0.88, 0.84, 0.72), 1, cv2.LINE_AA)


@_structure("oni_sumi")
def _b_oni_sumi(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 47 + 6)
    fiber = _fbm(shape, seed * 3 + 7, 4, 26.0, aniso=(1.0, 0.3))
    mottle = _fbm(shape, seed * 5 + 4, 3, 3.0)
    paper = np.array([0.91, 0.86, 0.72], np.float32)
    rgb = np.ones((h, w, 3), np.float32) * paper
    rgb *= (0.90 + 0.12 * fiber[..., None]) * (0.94 + 0.10 * mottle[..., None])
    specM = np.full((h, w), 22.0, np.float32)
    specR = 190 + (fiber - 0.5) * 70
    specC = 200 + (mottle - 0.5) * 70
    ink = (0.08, 0.06, 0.08)
    verm = (0.78, 0.15, 0.10)
    # pale gray under-sweeps (diluted-ink layer) + bamboo screen for tooth
    yyo, xxo = _mg(shape)
    screen_o = (np.sin(yyo / max(2.0, 6 * S)) > 0.6).astype(np.float32) * 0.08
    rgb *= (1.0 - screen_o[..., None])

    def curve_pts(x0, y0, a, L, bend, n=26):
        pts = []
        x, y = x0, y0
        aa = a
        for i in range(n):
            pts.append((x, y))
            aa += bend / n
            x += np.cos(aa) * (L / n)
            y += np.sin(aa) * (L / n)
        return pts

    # diluted-ink under-sweeps: broad pale gray strokes beneath the bold layer (sumi layering)
    for _ in range(max(24, int(80 * S * S) + 10)):
        x0, y0 = r.random() * w, r.random() * h
        L = (90 + 140 * r.random()) * S + 20
        a = r.random() * np.pi
        pts = curve_pts(x0, y0, a, L, (r.random() - 0.5) * 1.2, n=30)
        pale = 0.55 + 0.18 * r.random()
        _brush_stroke([(rgb, (pale, pale * 0.97, pale * 0.88)),
                       (specR, float(150 + 60 * r.random()))], pts, (14 + 12 * r.random()) * S + 3, r, bristle=False)
    n_motif = max(80, int(300 * S * S) + 30)
    for _ in range(n_motif):
        x0, y0 = r.random() * w, r.random() * h
        kind = r.random()
        is_verm = r.random() < 0.16
        tier = _tier8(r, 0.6, 1.0)
        c = verm if is_verm else tuple(v * (1.3 - tier) for v in ink)
        mv = 230 if not is_verm else 252
        rv = 26 + 90 * (1 - tier)
        tg = [(rgb, c), (specM, float(mv * tier)), (specR, float(rv)), (specC, float(20 + 60 * (1 - tier)))]
        if kind < 0.40:      # horn pair: two curved tapering strokes converging
            L = (70 + 110 * r.random()) * S + 16
            a = r.random() * 2 * np.pi
            for sgn in (1, -1):
                pts = curve_pts(x0 + sgn * L * 0.25, y0, a - sgn * 0.5, L, sgn * (1.1 + 0.6 * r.random()))
                _brush_stroke(tg, pts, (9 + 8 * r.random()) * S + 2.5, r)
        elif kind < 0.62:    # brow / slash strokes
            L = (60 + 90 * r.random()) * S + 14
            a = r.random() * np.pi
            pts = curve_pts(x0, y0, a, L, (r.random() - 0.5) * 0.8)
            _brush_stroke(tg, pts, (11 + 9 * r.random()) * S + 2.5, r)
        elif kind < 0.80:    # fang triple: short converging spikes
            L = (30 + 44 * r.random()) * S + 8
            a = r.random() * 2 * np.pi
            for k in range(3):
                pts = curve_pts(x0 + (k - 1) * L * 0.4, y0, a + (k - 1) * 0.25, L, (r.random() - 0.5) * 0.4, n=12)
                _brush_stroke(tg, pts, (6 + 5 * r.random()) * S + 1.5, r)
        else:                # enso partial ring
            R_ = (28 + 52 * r.random()) * S + 8
            a0 = r.random() * 2 * np.pi
            span = 4.2 + 1.6 * r.random()
            pts = [(x0 + np.cos(a0 + t / 24 * span) * R_, y0 + np.sin(a0 + t / 24 * span) * R_) for t in range(25)]
            _brush_stroke(tg, pts, (7 + 6 * r.random()) * S + 2, r)
        # ink flicks at motif end
        for _ in range(int(6 + r.integers(0, 9))):
            fa = r.random() * 2 * np.pi
            fd = (8 + 26 * r.random()) * S
            fx, fy = int(x0 + np.cos(fa) * fd), int(y0 + np.sin(fa) * fd)
            cv2.circle(rgb, (fx, fy), max(1, int((1 + 2.2 * r.random()) * S)), c, -1, cv2.LINE_AA)
            cv2.circle(specM, (fx, fy), max(1, int(2 * S)), float(mv), -1)
    # ink mist: fine speckle spray across the sheet
    for _ in range(max(500, int(3200 * S * S))):
        x2, y2 = int(r.random() * w), int(r.random() * h)
        cv2.circle(rgb, (x2, y2), max(1, int(1.1 * S)), (0.30, 0.27, 0.28), -1)
    # hanko seals
    for _ in range(max(5, int(16 * S * S) + 3)):
        sx, sy = int(r.random() * w), int(r.random() * h)
        sz = int((20 + 18 * r.random()) * S + 6)
        cv2.rectangle(rgb, (sx, sy), (sx + sz, sy + sz), verm, -1, cv2.LINE_AA)
        _pseudo_glyph([(rgb, tuple(map(float, paper)))], sx + 2, sy + 2, sz - 4, max(1, int(2 * S)), r)
        specM[sy:sy + sz, sx:sx + sz] = 80
        specR[sy:sy + sz, sx:sx + sz] = 130
        specC[sy:sy + sz, sx:sx + sz] = 60
    return {"rgb": np.clip(rgb, 0, 1).astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ 25 manga_page
# MECHANISM: recursive axis-aligned panel tiling with white gutters + black borders; EVERY panel
# a different micro-tone fill (mini speedlines / halftone gradients / hatch / black-streak /
# checker / dash cluster / rings / spot-colour). (anime2_manga_page "Manga Page Chaos")

@_structure("manga_page")
def _b_manga_page(shape, seed):
    h, w = shape
    S = h / 2048.0
    r = _rng(seed * 49 + 8)
    yy, xx = _mg(shape)
    gut = np.array([0.96, 0.95, 0.92], np.float32)
    rgb = np.ones((h, w, 3), np.float32) * gut
    specM = np.full((h, w), 24.0, np.float32)
    specR = np.full((h, w), 198.0, np.float32)
    specC = np.full((h, w), 210.0, np.float32)
    ink = np.array([0.06, 0.06, 0.09], np.float32)
    spot = np.array([(0.90, 0.15, 0.25), (0.15, 0.75, 0.90), (1.0, 0.80, 0.15)], np.float32)
    rects = [(0, 0, w, h)]
    panels = []
    while rects:
        x0, y0, x1, y1 = rects.pop()
        rw, rh = x1 - x0, y1 - y0
        min_px = 170 * S + 30
        if (rw < min_px * 1.7 and rh < min_px * 1.7) or len(panels) > 220:
            panels.append((x0, y0, x1, y1))
            continue
        if rw > rh:
            cut = x0 + int(rw * (0.30 + 0.40 * r.random()))
            rects += [(x0, y0, cut, y1), (cut, y0, x1, y1)]
        else:
            cut = y0 + int(rh * (0.30 + 0.40 * r.random()))
            rects += [(x0, y0, x1, cut), (x0, cut, x1, y1)]
    g = max(3, int(10 * S))
    b_ = max(1, int(3 * S))
    for (x0, y0, x1, y1) in panels:
        px0, py0, px1, py1 = x0 + g, y0 + g, x1 - g, y1 - g
        if px1 - px0 < 8 or py1 - py0 < 8:
            continue
        cv2.rectangle(rgb, (px0, py0), (px1, py1), tuple(map(float, ink)), b_ * 2)
        ix0, iy0, ix1, iy1 = px0 + b_, py0 + b_, px1 - b_, py1 - b_
        lx = xx[iy0:iy1, ix0:ix1] - ix0
        ly = yy[iy0:iy1, ix0:ix1] - iy0
        pw_, ph_ = ix1 - ix0, iy1 - iy0
        sub = rgb[iy0:iy1, ix0:ix1]
        sM = specM[iy0:iy1, ix0:ix1]
        sR = specR[iy0:iy1, ix0:ix1]
        sC = specC[iy0:iy1, ix0:ix1]
        style = int(r.integers(0, 9))
        spot_c = spot[int(r.integers(0, 3))]
        use_spot = r.random() < 0.22
        base_fill = spot_c * 0.9 if use_spot else np.array([0.97, 0.96, 0.93], np.float32)
        sub[:] = base_fill
        if style == 0:      # mini radial speedlines
            cx_, cy_ = pw_ * r.random(), ph_ * r.random()
            th = np.arctan2(ly - cy_, lx - cx_)
            n_l = int(40 + r.integers(0, 50))
            fr = np.abs((th / (2 * np.pi) + 0.5) * n_l % 1 - 0.5)
            m = fr < 0.11
            sub[m] = ink
            sM[m] = 235; sR[m] = 26; sC[m] = 20
        elif style == 1:    # halftone gradient
            cellp = max(3.0, 8.0 * S)
            t = (lx + ly) / max(1.0, pw_ + ph_)
            du = (lx / cellp) % 1.0 - 0.5
            dv = (ly / cellp) % 1.0 - 0.5
            m = np.sqrt(du * du + dv * dv) < (0.14 + 0.32 * t)
            sub[m] = ink
            sM[m] = 200; sR[m] = 42
        elif style == 2:    # diagonal hatch (one or cross)
            phh = max(3.0, 8.0 * S)
            m = np.sin((lx + ly) / phh) > 0.45
            if r.random() < 0.5:
                m = m | (np.sin((lx - ly) / (phh * 1.3)) > 0.6)
            sub[m] = ink
            sR[m] = 220; sM[m] = 60
        elif style == 3:    # solid black with white speed streaks
            sub[:] = ink
            sM[:] = 48; sR[:] = 170; sC[:] = 16
            n_s = int(6 + r.integers(0, 10))
            for _ in range(n_s):
                sy_ = iy0 + int(r.random() * ph_)
                cv2.line(rgb, (ix0, sy_), (ix1, sy_ + int((r.random() - 0.5) * ph_ * 0.3)), (0.95, 0.95, 0.97), max(1, int(1.6 * S)), cv2.LINE_AA)
                cv2.line(specM, (ix0, sy_), (ix1, sy_), float(252), max(1, int(1.6 * S)))
        elif style == 4:    # screentone sky + cloud blob
            cellp = max(3.0, 7.0 * S)
            t = ly / max(1.0, ph_)
            du = (lx / cellp) % 1.0 - 0.5
            dv = (ly / cellp) % 1.0 - 0.5
            m = np.sqrt(du * du + dv * dv) < (0.34 * (1 - t))
            sub[m] = ink * 0.5 + base_fill * 0.5
            for _ in range(int(2 + r.integers(0, 3))):
                bx_, by_ = ix0 + int(r.random() * pw_), iy0 + int(r.random() * ph_)
                brr = max(3, int(min(pw_, ph_) * (0.10 + 0.12 * r.random())))
                cv2.circle(rgb, (bx_, by_), brr, (0.99, 0.99, 0.99), -1, cv2.LINE_AA)
                cv2.circle(rgb, (bx_, by_), brr, tuple(map(float, ink)), 1, cv2.LINE_AA)
        elif style == 5:    # action dash cluster
            for _ in range(int(30 + r.integers(0, 40))):
                dx_ = ix0 + int(r.random() * pw_)
                dy_ = iy0 + int(r.random() * ph_)
                a = r.random() * np.pi
                L = max(2, int((5 + 9 * r.random()) * S + 1))
                cv2.line(rgb, (int(dx_ - L * np.cos(a)), int(dy_ - L * np.sin(a))),
                         (int(dx_ + L * np.cos(a)), int(dy_ + L * np.sin(a))), tuple(map(float, ink)), 1, cv2.LINE_AA)
        elif style == 6:    # concentration rings
            cx_, cy_ = ix0 + pw_ // 2, iy0 + ph_ // 2
            for k in range(int(5 + r.integers(0, 6))):
                cv2.circle(rgb, (cx_, cy_), max(2, int((k + 1) * min(pw_, ph_) / 14)), tuple(map(float, ink)), 1, cv2.LINE_AA)
                cv2.circle(specM, (cx_, cy_), max(2, int((k + 1) * min(pw_, ph_) / 14)), float(210), 1)
        elif style == 7:    # checker
            cellp = max(4, int(12 * S))
            m = (((lx // cellp) + (ly // cellp)) % 2) == 0
            sub[m] = ink
            sM[m] = 180; sR[m] = 60
        else:               # blank with ink blob + drips
            bx_, by_ = ix0 + int(r.random() * pw_), iy0 + int(r.random() * ph_ * 0.5)
            brr = max(3, int(min(pw_, ph_) * (0.10 + 0.10 * r.random())))
            cv2.circle(rgb, (bx_, by_), brr, tuple(map(float, ink)), -1, cv2.LINE_AA)
            for _ in range(int(2 + r.integers(0, 3))):
                dxp = bx_ + int((r.random() - 0.5) * brr * 2)
                cv2.line(rgb, (dxp, by_), (dxp, by_ + int(brr * (1.5 + 2.5 * r.random()))), tuple(map(float, ink)), max(1, int(2 * S)), cv2.LINE_AA)
        if use_spot and style in (0, 2, 5, 6, 8):
            wash = np.zeros_like(sub)
            wash[:] = spot_c
            sub[:] = np.clip(sub * 0.72 + wash * 0.28, 0, 1)
            sM[:] = np.clip(sM + 50, 0, 255)
            sC[:] = 40
    # page grain
    grain = (_vgrid(shape, seed * 51 + 2, h // 2, w // 2) - 0.5) * 0.05
    rgb = np.clip(rgb + grain[..., None], 0, 1)
    return {"rgb": rgb.astype(np.float32), "spec": _spec_pack(specM, specR, specC)}


# ============================================================================ registry + cache

def _shape2(shape):
    return (int(shape[0]), int(shape[1]))


# per-structure flake tuning: (amp, density). cel stays clean (chrome-band identity),
# strand/sparkle designs lean into glitter (their 1-px energy IS the look)
_FLAKE_TUNE = {  # (mult amp, density, additive amp)
    "cel_terminator": (0.0, 0.35, 0.0),
    "inkbrush_strands": (0.16, 1.6, 0.14),
    "shoujo_sparkle": (0.15, 1.5, 0.10),
    "cyber_glitch": (0.12, 0.45, 0.08),
    "retro_broadcast": (0.12, 1.3, 0.08),
    "shuriken_storm": (0.12, 1.2, 0.08),
}


@lru_cache(maxsize=4)
def _build_cached(key, hh, ww, seed):
    built = _BUILDERS[key]((hh, ww), int(seed))
    # [SPB ANIME OVERHAUL 2026-08-25] category-wide micro-flake clear layer (owner Universal Law:
    # sub-pixel sparkle everywhere) — also guarantees full-span married specs (M 2..252, R 8..235)
    amp, dens, amp_add = _FLAKE_TUNE.get(key, (0.10, 1.0, 0.02))
    return _flake(built, (hh, ww), int(seed), amp=amp, dens=dens, amp_add=amp_add)


def build(key, shape, seed=7):
    h, w = _shape2(shape)
    return _build_cached(key, h, w, int(seed))


build.cache_clear = _build_cached.cache_clear  # harness convenience


class _LazyMap(dict):
    def __init__(self, field):
        super().__init__()
        self._field = field

    def __getitem__(self, key):
        if key not in _BUILDERS:
            raise KeyError(key)
        field = self._field
        return lambda shape, seed=7, _k=key: build(_k, shape, seed)[field]

    def __contains__(self, key):
        return key in _BUILDERS

    def keys(self):
        return _BUILDERS.keys()

    def __iter__(self):
        return iter(_BUILDERS)

    def __len__(self):
        return len(_BUILDERS)

    def items(self):
        return ((k, self[k]) for k in _BUILDERS)


ANIME_STRUCTURES = _LazyMap("rgb")
ANIME_SPECS = _LazyMap("spec")
