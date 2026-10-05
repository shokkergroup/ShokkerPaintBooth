"""FRACTURED NIGHTSHIFT — WAVE 2: 90 more true color-flip experiments.

Owner verdict on wave 1 (2026-08-01): "a hit. Expand from 10 to 100 within the
same category. Go CRAZY… ~10 tamer, everything else exotic, wild, out there.
DETAILED. Nature themed (ocean/waves, sun, lightning), grunge, racing — cover
the spectrum."

Same physics as wave 1 (engine/expansions/nightshift_lab_2026.py — read its
header): two interleaved pixel populations, matte dielectric day-hue skin +
M~252/Cc-dull metal night-hue lattice. This module only adds GEOMETRIES and
palettes; the factory, contract and gates are wave 1's. Wave 1 file stays
frozen — its 10 are the owner-approved "tamer" end of the hundred.

Themes: OCEAN(12) SKY/STORM(12) FIRE/EARTH(8) GRUNGE(12) RACING(12)
        TECH/GLITCH(10) ANIMAL(10) EXOTIC(14) = 90.
Every geometry is a distinct b-mask topology (uniqueness law, color-blind);
features 4-16px at the 1024 work grid = 8-32px on the 2048 canvas.
"""

from __future__ import annotations

from collections import OrderedDict

import cv2
import numpy as np

from engine.expansions.nightshift_lab_2026 import (
    _W, _aa, _cellF1F2, _hash01, _make_ns, _rng, _smooth, _xy,
)


# ------------------------------------------------------------ extra primitives
def _fbm(h, w, rng, cell, octaves=3):
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    c = cell
    for _ in range(octaves):
        acc += _smooth(h, w, rng, max(2, int(c))) * amp
        tot += amp
        amp *= 0.5
        c /= 2.1
    return acc / max(tot, 1e-6)


def _ridged(h, w, rng, cell):
    return 1.0 - np.abs(_fbm(h, w, rng, cell) * 2.0 - 1.0)


def _angfield(h, w, rng, cell):
    return _fbm(h, w, rng, cell) * 2.0 * np.pi


def _stripes(h, w, ang, period, duty=0.5, warp=None):
    """Sine stripes along a (possibly varying) angle field; returns 0..1 band."""
    x, y = _xy(h, w)
    ph = (x * np.cos(ang) + y * np.sin(ang)) * (2 * np.pi / max(period, 1e-3))
    if warp is not None:
        ph = ph + warp
    s = 0.5 + 0.5 * np.sin(ph)
    return _aa(s, 1.0 - duty, min(1.0, 1.0 - duty + 0.18))


def _disks(h, w, rng, n, rmin, rmax, val=1.0):
    img = np.zeros((h, w), np.float32)
    for _ in range(int(n)):
        cv2.circle(img, (int(rng.integers(0, w)), int(rng.integers(0, h))),
                   int(rng.integers(rmin, rmax + 1)), float(val), -1)
    return np.clip(img, 0, 1)


def _rings(h, w, rng, n, rmin, rmax, thick=2):
    img = np.zeros((h, w), np.float32)
    for _ in range(int(n)):
        cv2.circle(img, (int(rng.integers(0, w)), int(rng.integers(0, h))),
                   int(rng.integers(rmin, rmax + 1)), 1.0, int(thick))
    return np.clip(img, 0, 1)


def _streaks(h, w, rng, n, length, ang, jitter, thick=2, taper=False):
    img = np.zeros((h, w), np.float32)
    for _ in range(int(n)):
        x0, y0 = float(rng.integers(0, w)), float(rng.integers(0, h))
        a = ang + (rng.random() - 0.5) * jitter
        L = length * (0.5 + rng.random())
        x1, y1 = x0 + np.cos(a) * L, y0 + np.sin(a) * L
        if taper:
            steps = 4
            for si in range(steps):
                t0, t1 = si / steps, (si + 1) / steps
                cv2.line(img, (int(x0 + (x1 - x0) * t0), int(y0 + (y1 - y0) * t0)),
                         (int(x0 + (x1 - x0) * t1), int(y0 + (y1 - y0) * t1)),
                         1.0, max(1, int(thick * (1.0 - 0.8 * t0))))
        else:
            cv2.line(img, (int(x0), int(y0)), (int(x1), int(y1)), 1.0, int(thick))
    return np.clip(img, 0, 1)


def _bolts(h, w, rng, n, seg=14, spread=0.9, branch=0.25, thick=2):
    """Angular zigzag lightning polylines with decaying branches."""
    img = np.zeros((h, w), np.float32)

    def walk(x, y, a, steps, t):
        for _ in range(int(steps)):
            a2 = a + (rng.random() - 0.5) * spread
            nx, ny = x + np.cos(a2) * seg, y + np.sin(a2) * seg
            if 0 <= nx < w and 0 <= ny < h and 0 <= x < w and 0 <= y < h:
                cv2.line(img, (int(x), int(y)), (int(nx), int(ny)), 1.0, max(1, int(t)))
            x, y, a = nx, ny, a2
            if rng.random() < branch and t > 1:
                walk(x, y, a + (0.9 if rng.random() < 0.5 else -0.9),
                     steps // 2, t - 1)
            if not (-w * 0.2 < x < w * 1.2 and -h * 0.2 < y < h * 1.2):
                break

    for _i in range(int(n)):
        y0 = 0.0 if _i % 2 == 0 else float(rng.integers(0, h))
        walk(rng.integers(0, w), y0, np.pi / 2, rng.integers(30, 60), thick)
    return np.clip(img, 0, 1)


def _polar(h, w, cx, cy):
    x, y = _xy(h, w)
    dx, dy = x - cx, y - cy
    return np.arctan2(dy, dx), np.sqrt(dx * dx + dy * dy)


def _mirror8(f):
    h, w = f.shape
    q = f[: h // 2, : w // 2]
    top = np.concatenate([q, q[:, ::-1]], axis=1)
    out = np.concatenate([top, top[::-1, :]], axis=0)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)


def _cellF1F2_half(h, w, rng, cell):
    """Cellular fields at half resolution (4x faster) upscaled back; distances
    rescaled to full-grid pixels. For geometries stacking TWO cell fields that
    otherwise blow the render budget."""
    f1, f2, cid = _cellF1F2(h // 2, w // 2, rng, max(2, int(cell // 2)))
    up = lambda a: cv2.resize(a, (w, h), interpolation=cv2.INTER_LINEAR)
    return up(f1) * 2.0, up(f2) * 2.0, up(cid)


# ══════════════════════════════════════════════════════ OCEAN / WAVES (12)
def _g_tide_lines(h, w, rng):
    warp = (_fbm(h, w, rng, 128) - 0.5) * 9.0
    ang = np.zeros((h, w), np.float32)
    b = _stripes(h, w, ang + 0.12, 11.0, duty=0.22, warp=warp)
    return {"b": b}


def _g_breaker_curls(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(140):
        cx, cy = rng.integers(0, w), rng.integers(0, h)
        r0 = rng.integers(4, 11)
        a0 = rng.random() * 6.283
        for k in range(3):
            cv2.ellipse(img, (int(cx), int(cy)), (int(r0 + k * 2), int(r0 + k * 2)),
                        np.degrees(a0), 0, 250 - k * 40, 1.0, 1)
    return {"b": img}


def _g_caustic_net(h, w, rng):
    _f1a, f2a, ida = _cellF1F2_half(h, w, rng, 26)
    _f1b, f2b, _ = _cellF1F2_half(h, w, rng, 15)
    wa = 1.0 - _aa(f2a - _f1a, 1.0, 2.8)
    wb = (1.0 - _aa(f2b - _f1b, 0.6, 1.8)) * 0.7
    return {"b": np.clip(wa + wb, 0, 1), "id": ida}


def _g_kelp_columns(h, w, rng):
    x, y = _xy(h, w)
    b = np.zeros((h, w), np.float32)
    lane = 26.0
    off = _hash01(1, max(2, int(w // lane)), rng, 1)[0]
    sway = np.sin(y * (2 * np.pi / rng.uniform(150, 260))) * 6.0
    xc = (x + sway) % lane
    width = 3.0 + _smooth(h, w, rng, 96) * 5.0
    lane_gate = _hash01(h, w, rng, int(lane)) > 0.35
    b = _aa(width - np.abs(xc - lane / 2), 0.0, 1.5) * lane_gate
    _ = off
    return {"b": b.astype(np.float32)}


def _g_rain_rings(h, w, rng):
    b = np.zeros((h, w), np.float32)
    for _ in range(120):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        for k in range(int(rng.integers(1, 4))):
            cv2.circle(b, (cx, cy), 4 + k * int(rng.integers(3, 6)), 1.0, 1)
    return {"b": np.clip(b, 0, 1)}


def _g_maelstrom(h, w, rng):
    b = np.zeros((h, w), np.float32)
    for cx, cy in [(w * rng.random(), h * rng.random()) for _ in range(7)]:
        th, r = _polar(h, w, cx, cy)
        arm = 0.5 + 0.5 * np.sin(th * 3 + r * (2 * np.pi / 46.0))
        b = np.maximum(b, _aa(arm, 0.80, 0.94) * _aa(520 - r, 0, 240))
    return {"b": b}


def _g_foam_lace(h, w, rng):
    f1a, _f2a, ida = _cellF1F2_half(h, w, rng, 11)
    f1b, _f2b, _ = _cellF1F2_half(h, w, rng, 22)
    lace = _aa(f1a, 2.6, 3.8) * (1.0 - _aa(f1b, 6.0, 9.0) * 0.85)
    return {"b": np.clip(lace, 0, 1), "id": ida}


def _g_current_bands(h, w, rng):
    x, y = _xy(h, w)
    band = np.floor((x * 0.42 + y) / 64.0)
    parity = (band % 2).astype(np.float32)
    ang = np.full((h, w), 0.5, np.float32)
    chev = _stripes(h, w, ang, 9.0, duty=0.3)
    chev2 = _stripes(h, w, -ang, 9.0, duty=0.3)
    return {"b": np.where(parity > 0.5, chev, chev2).astype(np.float32)}


def _g_plankton_wake(h, w, rng):
    ang = _angfield(h, w, rng, 160)
    strk = _streaks(h, w, rng, 500, 16, 0.0, 6.283, 1)
    dots = _disks(h, w, rng, 900, 1, 2)
    hue = 0.45 + _smooth(h, w, rng, 128) * 0.22          # teal→green wheel slice
    _ = ang
    return {"b": np.clip(strk * 0.8 + dots, 0, 1), "hue": hue.astype(np.float32)}


def _g_jelly_drift(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(150):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        r = int(rng.integers(6, 14))
        cv2.ellipse(img, (cx, cy), (r, int(r * 0.72)), 0, 180, 360, 1.0, 2)
        for t in range(3):
            x0 = cx - r // 2 + t * (r // 2)
            cv2.line(img, (x0, cy), (x0 + int(rng.integers(-3, 4)), cy + r * 2), 1.0, 1)
    return {"b": np.clip(img, 0, 1)}


def _g_abyss_strata(h, w, rng):
    x, y = _xy(h, w)
    ragged = (_fbm(h, w, rng, 96) - 0.5) * 26.0
    band = np.sin((y + ragged) * (2 * np.pi / 58.0))
    return {"b": _aa(np.abs(band), 0.0, 0.14) * 0.0 + _aa(1 - np.abs(band), 0.90, 0.985)}


def _g_sonar_sweep(h, w, rng):
    th, r = _polar(h, w, w * 0.5, h * 0.5)
    sweep = _aa(0.5 + 0.5 * np.sin(th * 2), 0.75, 0.95)
    pings = _aa(0.5 + 0.5 * np.sin(r * (2 * np.pi / 90.0)), 0.90, 0.985)
    blips = _disks(h, w, rng, 60, 2, 4)
    return {"b": np.clip(sweep * 0.5 + pings + blips, 0, 1)}


# ══════════════════════════════════════════════════ SKY / SUN / STORM (12)
def _g_solar_granules(h, w, rng):
    f1, _f2, cid = _cellF1F2(h, w, rng, 14)
    cores = _aa(4.6 - f1, 0.0, 2.2)
    return {"b": cores, "id": cid}


def _g_corona_fan(h, w, rng):
    th, r = _polar(h, w, w * 0.5, -h * 0.35)
    rays = 0.5 + 0.5 * np.sin(th * 90.0)
    gate = _hash01(h, w, rng, 3) * 0.25
    return {"b": _aa(rays + gate, 0.86, 0.97) * _aa(r, 60, 220)}


def _g_fork_lightning(h, w, rng):
    return {"b": _bolts(h, w, rng, 16, seg=16, spread=1.1, branch=0.3, thick=3)}


def _g_thunder_topo(h, w, rng):
    f = _fbm(h, w, rng, 180, octaves=4)
    iso = 0.5 + 0.5 * np.sin(f * 46.0)
    return {"b": _aa(iso, 0.88, 0.985)}


def _g_aurora_curtain(h, w, rng):
    x, y = _xy(h, w)
    sway = (_fbm(h, w, rng, 200) - 0.5) * 120.0
    ribbon = 0.5 + 0.5 * np.sin((x + sway) * (2 * np.pi / 90.0))
    fold = 0.5 + 0.5 * np.sin((x + sway * 0.4) * (2 * np.pi / 17.0))
    hue = 0.30 + _smooth(h, w, rng, 220) * 0.45
    return {"b": _aa(ribbon, 0.62, 0.8) * _aa(fold, 0.35, 0.6),
            "hue": hue.astype(np.float32)}


def _g_star_nebula(h, w, rng):
    stars = np.clip(_disks(h, w, rng, 400, 1, 1) + _disks(h, w, rng, 120, 1, 2)
                    + _disks(h, w, rng, 30, 2, 3), 0, 1)
    wisp = _aa(_fbm(h, w, rng, 240, 4), 0.62, 0.8) * 0.55
    hue = 0.55 + _smooth(h, w, rng, 300) * 0.35
    return {"b": np.clip(stars + wisp, 0, 1), "hue": hue.astype(np.float32)}


def _g_dawn_rays(h, w, rng):
    th, _r = _polar(h, w, -w * 0.15, h * 1.15)
    widths = _hash01(h, w, rng, 5)
    rays = 0.5 + 0.5 * np.sin(th * 60.0 + widths * 2.0)
    return {"b": _aa(rays, 0.74, 0.9)}


def _g_hail_streaks(h, w, rng):
    strk = _streaks(h, w, rng, 260, 26, np.pi * 0.62, 0.16, 1)
    hits = _rings(h, w, rng, 90, 2, 5, 1)
    return {"b": np.clip(strk + hits, 0, 1)}


def _g_monsoon_cross(h, w, rng):
    ang = np.full((h, w), np.pi * 0.60, np.float32)
    a1 = _stripes(h, w, ang, 6.5, duty=0.16)
    a2 = _stripes(h, w, ang + 0.5, 8.0, duty=0.12)
    return {"b": np.clip(a1 + a2 * 0.8, 0, 1)}


def _g_cloud_gaps(h, w, rng):
    f1, _f2, cid = _cellF1F2(h, w, rng, 34)
    gaps = _aa(f1, 12.0, 16.0)
    fine = _hash01(h, w, rng, 2) > 0.55
    return {"b": np.clip(gaps * (0.6 + 0.4 * fine), 0, 1), "id": cid}


def _g_eclipse_rings(h, w, rng):
    b = np.zeros((h, w), np.float32)
    white = np.zeros((h, w), np.float32)
    for cx, cy, rr in [(w * 0.5, h * 0.5, 150), (w * 0.18, h * 0.2, 80),
                       (w * 0.82, h * 0.78, 96), (w * 0.15, h * 0.85, 60),
                       (w * 0.85, h * 0.15, 60)]:
        _th, r = _polar(h, w, cx, cy)
        for k in (1.0, 1.35, 1.8):
            b = np.maximum(b, _aa(3.5 - np.abs(r - rr * k), 0, 2.0))
        white = np.maximum(white, _aa(1.8 - np.abs(r - rr * 1.16), 0, 1.2))
    ticks = _rings(h, w, rng, 40, 3, 7, 1)
    return {"b": np.clip(b + ticks * 0.6, 0, 1), "white": white}


def _g_ion_streamlines(h, w, rng):
    ang = _angfield(h, w, rng, 220)
    lanes = _stripes(h, w, ang, 10.0, duty=0.26)
    gate = _aa(_ridged(h, w, rng, 130), 0.55, 0.8)
    return {"b": np.clip(lanes * gate * 1.4, 0, 1)}


# ══════════════════════════════════════════════════════ FIRE / EARTH (8)
def _g_magma_fissure(h, w, rng):
    ridge = _ridged(h, w, rng, 150)
    fine = _ridged(h, w, rng, 40)
    return {"b": np.clip(_aa(ridge, 0.90, 0.985) + _aa(fine, 0.94, 0.995) * 0.7, 0, 1)}


def _g_ashfall(h, w, rng):
    a = _streaks(h, w, rng, 700, 6, np.pi * 0.58, 0.3, 1)
    b2 = _disks(h, w, rng, 300, 1, 2)
    return {"b": np.clip(a * 0.7 + b2, 0, 1)}


def _g_geyser_plumes(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(85):
        x0 = int(rng.integers(0, w)); y0 = int(rng.integers(0, h))
        ht = int(rng.integers(40, 110))
        cv2.line(img, (x0, y0), (x0 + int(rng.integers(-6, 7)), y0 - ht), 1.0, 2)
        for _k in range(6):
            cv2.circle(img, (x0 + int(rng.integers(-12, 13)), y0 - ht + int(rng.integers(-8, 9))),
                       int(rng.integers(2, 6)), 1.0, 1)
    return {"b": np.clip(img, 0, 1)}


def _g_geode_bands(h, w, rng):
    b = np.zeros((h, w), np.float32)
    jag = (_fbm(h, w, rng, 70) - 0.5) * 22.0
    for cx, cy in [(w * rng.random(), h * rng.random()) for _ in range(9)]:
        _th, r = _polar(h, w, cx, cy)
        rr = r + jag
        band = 0.5 + 0.5 * np.sin(rr * (2 * np.pi / 26.0))
        b = np.maximum(b, _aa(band, 0.82, 0.95) * _aa(560 - r, 0, 320))
    return {"b": b}


def _g_dune_ripples(h, w, rng):
    x, y = _xy(h, w)
    warp = (_fbm(h, w, rng, 190) - 0.5) * 40.0
    ph = (y * 0.35 + x + warp) * (2 * np.pi / 21.0)
    saw = (np.sin(ph) + 0.55 * np.sin(2 * ph)) * 0.5 + 0.5
    return {"b": _aa(saw, 0.80, 0.93)}


def _g_strata_fault(h, w, rng):
    x, y = _xy(h, w)
    fault = np.floor(x / 170.0)
    shift = (_hash01(1, 16, rng, 1)[0, :16] * 90.0)
    off = shift[(fault % 16).astype(np.int32)]
    band = 0.5 + 0.5 * np.sin((y * 0.9 + x * 0.18 + off) * (2 * np.pi / 30.0))
    return {"b": _aa(band, 0.82, 0.94)}


def _g_obsidian_facets(h, w, rng):
    f1, f2, cid = _cellF1F2(h, w, rng, 40)
    edges = 1.0 - _aa(f2 - f1, 1.3, 3.6)
    hot = (cid > 0.82).astype(np.float32)
    return {"b": np.clip(edges + hot, 0, 1), "id": cid}


def _g_crevasse(h, w, rng):
    return {"b": _bolts(h, w, rng, 26, seg=18, spread=0.5, branch=0.25, thick=3)}


# ═════════════════════════════════════════════════════════ GRUNGE (12)
def _g_rust_bloom(h, w, rng):
    seed_dots = _disks(h, w, rng, 90, 2, 6)
    halo = cv2.dilate(seed_dots, np.ones((7, 7), np.uint8)) - seed_dots
    speck = _disks(h, w, rng, 700, 1, 2)
    return {"b": np.clip(seed_dots + halo * 0.55 + speck * 0.8, 0, 1)}


def _g_peel_flakes(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(320):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        ww, hh = int(rng.integers(5, 16)), int(rng.integers(4, 12))
        ang = float(rng.random() * 180)
        box = cv2.boxPoints(((cx, cy), (ww, hh), ang))
        cv2.polylines(img, [box.astype(np.int32)], True, 1.0, 1)
        if rng.random() < 0.4:
            cv2.fillPoly(img, [box.astype(np.int32)], 1.0)
    return {"b": np.clip(img, 0, 1)}


def _g_oil_marble(h, w, rng):
    f = _fbm(h, w, rng, 160, 4)
    swirl = 0.5 + 0.5 * np.sin(f * 34.0)
    hue = (f * 2.6) % 1.0
    return {"b": _aa(swirl, 0.72, 0.9), "hue": hue.astype(np.float32)}


def _g_concrete_patch(h, w, rng):
    f1, f2, cid = _cellF1F2(h, w, rng, 60)
    cracks = 1.0 - _aa(f2 - f1, 0.7, 1.9)
    img = np.zeros((h, w), np.float32)
    for _ in range(14):
        x0, y0 = int(rng.integers(0, w - 60)), int(rng.integers(0, h - 40))
        cv2.rectangle(img, (x0, y0), (x0 + int(rng.integers(30, 70)), y0 + int(rng.integers(20, 50))), 1.0, 1)
    return {"b": np.clip(cracks + img, 0, 1), "id": cid}


def _g_grime_drips(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(220):
        x0 = int(rng.integers(0, w)); y0 = int(rng.integers(0, h))
        ln = int(rng.integers(8, 60))
        cv2.line(img, (x0, y0), (x0 + int(rng.integers(-2, 3)), y0 + ln), 1.0, 1)
        cv2.circle(img, (x0, y0 + ln), int(rng.integers(1, 3)), 1.0, -1)
    return {"b": np.clip(img, 0, 1)}


def _g_swirl_scratches(h, w, rng):
    img = np.zeros((h, w), np.float32)
    white = np.zeros((h, w), np.float32)
    for _ in range(240):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        r = int(rng.integers(6, 26))
        cv2.ellipse(img, (cx, cy), (r, r), float(rng.random() * 360), 0, int(rng.integers(40, 140)), 1.0, 1)
    for _ in range(30):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        r = int(rng.integers(8, 20))
        cv2.ellipse(white, (cx, cy), (r, r), float(rng.random() * 360), 0, 70, 1.0, 1)
    return {"b": np.clip(img, 0, 1), "white": np.clip(white, 0, 1)}


def _g_overspray_edge(h, w, rng):
    blob = _aa(_fbm(h, w, rng, 150, 3), 0.48, 0.55)
    edge = cv2.dilate(blob, np.ones((9, 9), np.uint8)) - blob
    spray = (_hash01(h, w, rng, 2) > 0.6).astype(np.float32)
    fade = cv2.GaussianBlur(edge, (0, 0), 6)
    dust = (_hash01(h, w, rng, 2) > 0.93).astype(np.float32)
    return {"b": np.clip(edge * 0.9 + fade * spray + dust * 0.7, 0, 1)}


def _g_poster_tears(h, w, rng):
    l1 = _aa(_fbm(h, w, rng, 105, 3), 0.5, 0.53)
    l2 = _aa(_fbm(h, w, rng, 85, 3), 0.52, 0.55)
    e1 = cv2.dilate(l1, np.ones((3, 3), np.uint8)) - l1
    e2 = cv2.dilate(l2, np.ones((3, 3), np.uint8)) - l2
    sheet = l2 * (1 - l1) * (_smooth(h, w, rng, 300) > 0.6)
    return {"b": np.clip(e1 + e2 + sheet * 0.9, 0, 1)}


def _g_weld_spatter(h, w, rng):
    dots = _disks(h, w, rng, 260, 1, 3)
    img = np.zeros((h, w), np.float32)
    for _ in range(110):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        for _k in range(int(rng.integers(4, 9))):
            a = rng.random() * 6.283
            L = rng.integers(6, 22)
            cv2.line(img, (cx, cy), (int(cx + np.cos(a) * L), int(cy + np.sin(a) * L)), 1.0, 1)
    return {"b": np.clip(dots + img, 0, 1)}


def _g_acid_pits(h, w, rng):
    pits = _disks(h, w, rng, 480, 1, 3)
    rims = cv2.dilate(pits, np.ones((3, 3), np.uint8)) - pits
    return {"b": np.clip(rims + pits * 0.15, 0, 1)}


def _g_tar_seams(h, w, rng):
    f1, f2, cid = _cellF1F2(h, w, rng, 52)
    seams = 1.0 - _aa(f2 - f1, 2.2, 6.5)
    return {"b": seams, "id": cid}


def _g_dent_crescents(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(430):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        r = int(rng.integers(4, 12))
        cv2.ellipse(img, (cx, cy), (r, r), float(rng.random() * 360), 200, 340, 1.0, 2)
    return {"b": np.clip(img, 0, 1)}


# ═════════════════════════════════════════════════════════ RACING (12)
def _g_checker_warp(h, w, rng):
    x, y = _xy(h, w)
    warp = (_fbm(h, w, rng, 220) - 0.5) * 30.0
    cx_ = np.floor((x + warp) / 16.0)
    cy_ = np.floor((y - warp) / 16.0)
    par = ((cx_ + cy_) % 2).astype(np.float32)
    gx = np.abs(((x + warp) / 16.0) - np.round((x + warp) / 16.0))
    gy = np.abs(((y - warp) / 16.0) - np.round((y - warp) / 16.0))
    white = np.maximum(1.0 - _aa(gx, 0.03, 0.08), 1.0 - _aa(gy, 0.03, 0.08)) * 0.8
    return {"b": par * (1.0 - white), "white": white}


def _g_tread_chevrons(h, w, rng):
    x, y = _xy(h, w)
    row = np.floor(y / 34.0)
    flip = (row % 2 == 0)
    ang = np.where(flip, 0.6, -0.6).astype(np.float32)
    ph = (x * np.cos(ang) + y * np.sin(ang)) * (2 * np.pi / 13.0)
    blocks = _aa(0.5 + 0.5 * np.sin(ph), 0.45, 0.62)
    gap = _aa(np.abs((y / 34.0) - np.round(y / 34.0)), 0.07, 0.14)
    return {"b": (blocks * gap).astype(np.float32)}


def _g_speed_streaks(h, w, rng):
    s1 = _streaks(h, w, rng, 200, 70, 0.0, 0.06, 1, taper=True)
    s2 = _streaks(h, w, rng, 80, 120, 0.0, 0.04, 2, taper=True)
    return {"b": np.clip(s1 + s2, 0, 1)}


def _g_slipstream(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(190):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        r0 = int(rng.integers(5, 10))
        for k in range(3):
            cv2.ellipse(img, (cx - k * (r0 + 2), cy), (r0 + k * 3, r0 + k * 2),
                        0, 110, 250, 1.0, 1)
    return {"b": np.clip(img, 0, 1)}


def _g_rotor_drill(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(70):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        for ring_r, nd in ((10, 6), (18, 10), (26, 14)):
            for k in range(nd):
                a = k * 2 * np.pi / nd + rng.random() * 0.3
                cv2.circle(img, (int(cx + np.cos(a) * ring_r), int(cy + np.sin(a) * ring_r)), 2, 1.0, -1)
        cv2.circle(img, (cx, cy), 3, 1.0, 1)
    return {"b": np.clip(img, 0, 1)}


def _g_kerb_wear(h, w, rng):
    x, y = _xy(h, w)
    stripe = 0.5 + 0.5 * np.sin((x + y) * (2 * np.pi / 46.0))
    par = (stripe > 0.5).astype(np.float32)
    edge = 1.0 - _aa(np.abs(stripe - 0.5), 0.02, 0.09)
    wear = (_hash01(h, w, rng, 3) > 0.72).astype(np.float32) * par
    return {"b": np.clip(edge + wear * 0.6, 0, 1)}


def _g_apex_arrows(h, w, rng):
    x, y = _xy(h, w)
    lane = np.floor(y / 40.0)
    phase = (lane * 23.0)
    xx = (x + phase) % 46.0
    yy = y % 40.0
    tip = _aa(14.0 - np.abs(yy - 20.0) - xx * 0.55, 0.0, 2.4) * _aa(xx, 4.0, 8.0)
    return {"b": tip.astype(np.float32)}


def _g_telemetry_waves(h, w, rng):
    b = np.zeros((h, w), np.float32)
    xs = np.arange(w)
    for row in range(0, h, 36):
        f1 = rng.uniform(0.02, 0.09)
        amp = rng.uniform(6, 14)
        trace = row + 18 + np.sin(xs * f1 * 6.283) * amp + (rng.random(w) - 0.5) * 3
        pts = np.stack([xs, trace], axis=1).astype(np.int32)
        cv2.polylines(b, [pts], False, 1.0, 1)
    return {"b": b}


def _g_gear_mesh(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(110):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        r = int(rng.integers(8, 18))
        teeth = max(6, r)
        th = np.linspace(0, 2 * np.pi, teeth * 2, endpoint=False)
        rr = r + (np.arange(teeth * 2) % 2) * 4
        pts = np.stack([cx + np.cos(th) * rr, cy + np.sin(th) * rr], axis=1).astype(np.int32)
        cv2.polylines(img, [pts], True, 1.0, 1)
        cv2.circle(img, (cx, cy), max(2, r // 3), 1.0, 1)
    return {"b": np.clip(img, 0, 1)}


def _g_drift_smoke(h, w, rng):
    ang = _angfield(h, w, rng, 260)
    wisp = _stripes(h, w, ang, 15.0, duty=0.2)
    gate = _aa(_fbm(h, w, rng, 200), 0.5, 0.72)
    arcs = np.zeros((h, w), np.float32)
    for _ in range(70):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        cv2.ellipse(arcs, (cx, cy), (int(rng.integers(20, 60)), int(rng.integers(8, 16))),
                    float(rng.random() * 180), 0, 200, 1.0, 2)
    return {"b": np.clip(wisp * gate + arcs * 0.8, 0, 1)}


def _g_photo_finish(h, w, rng):
    x, _y = _xy(h, w)
    jit = _hash01(h, w, rng, 4)
    slit = 0.5 + 0.5 * np.sin((x + jit * 14.0) * (2 * np.pi / 7.0))
    wide = (_hash01(h, w, rng, 24) > 0.5).astype(np.float32)
    return {"b": (_aa(slit, 0.6, 0.8) * (0.4 + 0.6 * wide)).astype(np.float32)}


def _g_pit_matrix(h, w, rng):
    x, y = _xy(h, w)
    cellx, celly = 7.0, 7.0
    dot = _aa(2.4 - np.sqrt(((x % cellx) - cellx / 2) ** 2 + ((y % celly) - celly / 2) ** 2), 0.0, 1.0)
    lit = (_hash01(h, w, rng, 7) > 0.45).astype(np.float32)
    panel = (_hash01(h, w, rng, 64) > 0.25).astype(np.float32)
    return {"b": (dot * lit * panel).astype(np.float32)}


# ═══════════════════════════════════════════════════ TECH / GLITCH (10)
def _g_hex_nano(h, w, rng):
    x, y = _xy(h, w)
    p = 9.0
    s1 = np.abs(((x) / p) % 1.0 - 0.5)
    s2 = np.abs(((x * 0.5 + y * 0.866) / p) % 1.0 - 0.5)
    s3 = np.abs(((x * 0.5 - y * 0.866) / p) % 1.0 - 0.5)
    hexline = 1.0 - _aa(np.minimum(np.minimum(s1, s2), s3), 0.06, 0.14)
    fill = (_hash01(h, w, rng, 9) > 0.8).astype(np.float32)
    return {"b": np.clip(hexline + fill, 0, 1)}


def _g_pcb_traces(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(120):
        x0, y0 = int(rng.integers(0, w)), int(rng.integers(0, h))
        x, y = x0, y0
        for _seg in range(int(rng.integers(3, 7))):
            d = rng.integers(0, 3)
            L = int(rng.integers(10, 34))
            nx, ny = x + (L if d == 0 else (0 if d == 1 else L)), y + (0 if d == 0 else (L if d == 1 else L))
            cv2.line(img, (x, y), (min(nx, w - 1), min(ny, h - 1)), 1.0, 1)
            x, y = min(nx, w - 1), min(ny, h - 1)
        cv2.circle(img, (x, y), 2, 1.0, -1)
        cv2.circle(img, (x0, y0), 2, 1.0, 1)
    return {"b": np.clip(img, 0, 1)}


def _g_datamosh(h, w, rng):
    x, y = _xy(h, w)
    rows = np.floor(y / 12.0)
    shift = (_hash01(1, 128, rng, 1)[0, :128] * 60.0)
    off = shift[(rows % 128).astype(np.int32)]
    blocks = (np.floor((x + off) / 26.0) % 3 == 0).astype(np.float32)
    fringe = _aa(np.abs(((x + off) / 26.0) - np.round((x + off) / 26.0)), 0.42, 0.5)
    hue = ((rows * 0.13) % 1.0).astype(np.float32)
    gate = (_hash01(h, w, rng, 5) > 0.45).astype(np.float32)
    return {"b": np.clip(blocks * 0.55 + (1.0 - fringe) * 0.9, 0, 1) * gate, "hue": hue}


def _g_lissajous(h, w, rng):
    img = np.zeros((h, w), np.float32)
    t = np.linspace(0, 2 * np.pi, 900)
    for _ in range(64):
        a, bfreq = rng.integers(2, 6), rng.integers(3, 8)
        cx, cy = rng.integers(20, w - 20), rng.integers(20, h - 20)
        R = rng.integers(40, 120)
        pts = np.stack([cx + np.cos(t * a) * R, cy + np.sin(t * bfreq) * R * 0.7], axis=1).astype(np.int32)
        cv2.polylines(img, [pts], False, 1.0, 1)
    return {"b": np.clip(img, 0, 1)}


def _g_laser_horizon(h, w, rng):
    x, y = _xy(h, w)
    horiz = h * 0.42
    below = y > horiz
    depth = np.maximum(y - horiz, 1.0)
    gx = np.abs(((x - w / 2) * 180.0 / depth) % 40.0 - 20.0)
    gz = np.abs((720.0 / depth) % 1.0 - 0.5)
    grid = np.maximum(1.0 - _aa(gx, 1.2, 3.2), 1.0 - _aa(gz, 0.05, 0.14)) * below
    stars = _disks(h, w, rng, 160, 1, 1) * (~below)
    return {"b": np.clip(grid + stars, 0, 1).astype(np.float32)}


def _g_wire_terrain(h, w, rng):
    b = np.zeros((h, w), np.float32)
    xs = np.arange(w)
    base = _fbm(1, w, rng, 100)[0] * 60.0
    for row in range(0, h, 22):
        tr = row + base * (0.4 + 1.2 * row / h) + np.sin(xs * 0.05 + row) * 4
        pts = np.stack([xs, np.clip(tr, 0, h - 1)], axis=1).astype(np.int32)
        cv2.polylines(b, [pts], False, 1.0, 1)
    return {"b": b}


def _g_static_rows(h, w, rng):
    x, y = _xy(h, w)
    row = np.floor(y / 3.0)
    dash = _hash01(h, w, rng, 3)
    on = (_hash01(1, 512, rng, 1)[0, :512] > 0.5)
    gate = on[(row % 512).astype(np.int32)]
    return {"b": ((dash > 0.55) & gate).astype(np.float32)}


def _g_holo_scan(h, w, rng):
    x, y = _xy(h, w)
    bands = 0.5 + 0.5 * np.sin(y * (2 * np.pi / 90.0))
    rows = _aa(0.5 + 0.5 * np.sin(y * (2 * np.pi / 4.0)), 0.6, 0.8)
    ticks = _aa(0.5 + 0.5 * np.sin(x * (2 * np.pi / 30.0)), 0.92, 0.99) * _aa(bands, 0.75, 0.9)
    hue = (0.45 + 0.25 * np.sin(y * 0.01)).astype(np.float32)
    return {"b": np.clip(rows * _aa(bands, 0.55, 0.75) + ticks, 0, 1), "hue": hue}


def _g_binary_rain(h, w, rng):
    x, y = _xy(h, w)
    col = np.floor(x / 9.0)
    phase = (_hash01(1, 256, rng, 1)[0, :256] * 200.0)
    off = phase[(col % 256).astype(np.int32)]
    dash = 0.5 + 0.5 * np.sin((y + off) * (2 * np.pi / 11.0))
    colgate = _hash01(h, w, rng, 9) > 0.3
    return {"b": (_aa(dash, 0.55, 0.75) * colgate).astype(np.float32)}


def _g_quasilattice(h, w, rng):
    x, y = _xy(h, w)
    acc = np.zeros((h, w), np.float32)
    for k in range(5):
        a = k * np.pi / 5.0 + rng.random() * 0.2
        acc += np.cos((x * np.cos(a) + y * np.sin(a)) * (2 * np.pi / 14.0))
    return {"b": _aa(acc / 5.0, 0.42, 0.62)}


# ══════════════════════════════════════════════════ ANIMAL / ORGANIC (10)
def _g_tiger_brush(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(260):
        x0, y0 = int(rng.integers(0, w)), int(rng.integers(0, h))
        a = np.pi * 0.5 + (rng.random() - 0.5) * 0.7
        L = int(rng.integers(30, 90))
        steps = 5
        for si in range(steps):
            t0, t1 = si / steps, (si + 1) / steps
            th = max(1, int(6 * (1.0 - t0)))
            cv2.line(img, (int(x0 + np.cos(a) * L * t0), int(y0 + np.sin(a) * L * t0)),
                     (int(x0 + np.cos(a) * L * t1), int(y0 + np.sin(a) * L * t1)), 1.0, th)
    return {"b": np.clip(img, 0, 1)}


def _g_zebra_flow(h, w, rng):
    ang = _angfield(h, w, rng, 300) * 0.25 + np.pi * 0.45
    return {"b": _stripes(h, w, ang, 17.0, duty=0.42)}


def _g_leopard_rosettes(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(520):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        r = int(rng.integers(4, 9))
        for _k in range(int(rng.integers(2, 5))):
            a0 = rng.random() * 360
            cv2.ellipse(img, (cx, cy), (r, r), a0, 0, int(rng.integers(60, 140)), 1.0, 2)
    return {"b": np.clip(img, 0, 1)}


def _g_diamond_snake(h, w, rng):
    x, y = _xy(h, w)
    sway = np.sin(y * (2 * np.pi / 300.0)) * 20.0
    u = (x + sway + y) / 15.0
    v = (x + sway - y) / 15.0
    du = np.abs(u - np.round(u)); dv = np.abs(v - np.round(v))
    lattice = np.maximum(1.0 - _aa(du, 0.06, 0.16), 1.0 - _aa(dv, 0.06, 0.16))
    par = ((np.floor(u) + np.floor(v)) % 2).astype(np.float32)
    return {"b": np.clip(lattice + par * 0.25, 0, 1)}


def _g_peacock_eyes(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(240):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        r = int(rng.integers(5, 12))
        cv2.circle(img, (cx, cy), r, 1.0, 1)
        cv2.circle(img, (cx, cy), max(1, r // 3), 1.0, -1)
        cv2.line(img, (cx, cy + r), (cx + int(rng.integers(-4, 5)), cy + r + int(rng.integers(6, 16))), 1.0, 1)
    hue = _smooth(h, w, rng, 220) * 0.35 + 0.35
    return {"b": np.clip(img, 0, 1), "hue": hue.astype(np.float32)}


def _g_wing_veins(h, w, rng):
    f1, f2, cid = _cellF1F2(h, w, rng, 30)
    veins = 1.0 - _aa(f2 - f1, 0.9, 2.6)
    th, _r = _polar(h, w, w * 0.5, h * 1.1)
    ribs = _aa(0.5 + 0.5 * np.sin(th * 42.0), 0.90, 0.98)
    return {"b": np.clip(veins + ribs, 0, 1), "id": cid}


def _g_mycelium(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(760):
        x, y = float(rng.integers(0, w)), float(rng.integers(0, h))
        a = rng.random() * 6.283
        for _s in range(int(rng.integers(8, 24))):
            nx, ny = x + np.cos(a) * 5, y + np.sin(a) * 5
            if 0 <= nx < w and 0 <= ny < h:
                cv2.line(img, (int(x), int(y)), (int(nx), int(ny)), 1.0, 1)
            x, y, a = nx, ny, a + (rng.random() - 0.5) * 0.9
    return {"b": np.clip(img, 0, 1)}


def _g_dendrites(h, w, rng):
    img = np.zeros((h, w), np.float32)
    soma = _disks(h, w, rng, 40, 3, 6)
    for _ in range(430):
        x, y = float(rng.integers(0, w)), float(rng.integers(0, h))
        a = rng.random() * 6.283
        for _s in range(int(rng.integers(5, 13))):
            nx, ny = x + np.cos(a) * 8, y + np.sin(a) * 8
            if 0 <= nx < w and 0 <= ny < h:
                cv2.line(img, (int(x), int(y)), (int(nx), int(ny)), 1.0, 1)
            x, y = nx, ny
            a += (rng.random() - 0.5) * 1.4
    spark = _disks(h, w, rng, 300, 1, 1)
    return {"b": np.clip(img * 0.8 + soma + spark * 0.7, 0, 1)}


def _g_koi_scales(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for row in range(0, h + 20, 12):
        off = 9 if (row // 12) % 2 else 0
        for cx in range(off, w + 20, 18):
            cv2.ellipse(img, (cx, row), (10, 8), 0, 20, 160, 1.0, 1)
    return {"b": np.clip(img, 0, 1)}


def _g_moth_dust(h, w, rng):
    grad = _smooth(h, w, rng, 340)
    speck = (_hash01(h, w, rng, 2) > (0.35 + grad * 0.5)).astype(np.float32)
    x, y = _xy(h, w)
    bars = _aa(0.5 + 0.5 * np.sin((x * 0.25 + y) * (2 * np.pi / 120.0)), 0.84, 0.94)
    return {"b": np.clip(speck * 0.8 + bars, 0, 1)}


# ═════════════════════════════════════════════════ EXOTIC / PSYCHO (14)
def _g_moire_wheels(h, w, rng):
    _th1, r1 = _polar(h, w, w * 0.38, h * 0.44)
    _th2, r2 = _polar(h, w, w * 0.62, h * 0.56)
    g1 = 0.5 + 0.5 * np.sin(r1 * (2 * np.pi / 11.0))
    g2 = 0.5 + 0.5 * np.sin(r2 * (2 * np.pi / 11.0))
    return {"b": _aa(g1 * g2, 0.55, 0.8)}


def _g_rhomb_field(h, w, rng):
    x, y = _xy(h, w)
    acc = np.zeros((h, w), np.float32)
    for k in range(3):
        a = k * np.pi / 3.0
        ph = (x * np.cos(a) + y * np.sin(a)) / 16.0
        acc += np.floor(ph % 2)
    par = (acc % 2).astype(np.float32)
    lines = np.zeros((h, w), np.float32)
    for k in range(3):
        a = k * np.pi / 3.0
        ph = (x * np.cos(a) + y * np.sin(a)) / 16.0
        lines = np.maximum(lines, 1.0 - _aa(np.abs(ph - np.round(ph)), 0.04, 0.1))
    return {"b": np.clip(par * (1 - lines) * 0.85 + lines * 0.4, 0, 1)}


def _g_hyper_rings(h, w, rng):
    b = np.zeros((h, w), np.float32)
    for cx, cy in [(0, 0), (w, 0), (0, h), (w, h), (w * 0.5, h * 0.5)]:
        _th, r = _polar(h, w, cx, cy)
        ring = 0.5 + 0.5 * np.sin(np.log(np.maximum(r, 2.0)) * 22.0)
        b = np.maximum(b, _aa(ring, 0.86, 0.97))
    return {"b": b}


def _g_frost_feathers(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(180):
        x0, y0 = int(rng.integers(0, w)), int(rng.integers(0, h))
        a = rng.random() * 6.283
        L = int(rng.integers(20, 55))
        cv2.line(img, (x0, y0), (int(x0 + np.cos(a) * L), int(y0 + np.sin(a) * L)), 1.0, 1)
        for s in range(3, L, 4):
            px, py = x0 + np.cos(a) * s, y0 + np.sin(a) * s
            for sgn in (1, -1):
                a2 = a + sgn * 0.7
                l2 = max(2, int((L - s) * 0.35))
                cv2.line(img, (int(px), int(py)),
                         (int(px + np.cos(a2) * l2), int(py + np.sin(a2) * l2)), 1.0, 1)
    return {"b": np.clip(img, 0, 1)}


def _g_spiro_loops(h, w, rng):
    img = np.zeros((h, w), np.float32)
    t = np.linspace(0, 2 * np.pi * 7, 2400)
    for _ in range(40):
        R, rr, d = rng.integers(30, 90), rng.integers(7, 25), rng.integers(10, 40)
        cx, cy = rng.integers(30, w - 30), rng.integers(30, h - 30)
        xx = (R - rr) * np.cos(t) + d * np.cos((R - rr) / rr * t) + cx
        yy = (R - rr) * np.sin(t) - d * np.sin((R - rr) / rr * t) + cy
        pts = np.stack([xx, yy], axis=1).astype(np.int32)
        cv2.polylines(img, [pts], False, 1.0, 1)
    return {"b": np.clip(img, 0, 1)}


def _g_kaleid_fold(h, w, rng):
    base = _aa(_fbm(h, w, rng, 90, 4), 0.55, 0.72) + _disks(h, w, rng, 200, 1, 3)
    fold = _mirror8(_mirror8(np.clip(base, 0, 1)))
    hue = _mirror8(_smooth(h, w, rng, 200))
    return {"b": _aa(fold, 0.4, 0.75), "hue": hue.astype(np.float32)}


def _g_op_pulse(h, w, rng):
    x, y = _xy(h, w)
    warp = (_fbm(h, w, rng, 280) - 0.5) * 26.0
    sq = np.maximum(np.abs(x - w / 2 + warp), np.abs(y - h / 2 + warp))
    ring = 0.5 + 0.5 * np.sin(sq * (2 * np.pi / 19.0))
    return {"b": _aa(ring, 0.62, 0.82)}


def _g_iso_stairs(h, w, rng):
    x, y = _xy(h, w)
    a1 = _aa(0.5 + 0.5 * np.sin((x * 0.866 + y * 0.5) * (2 * np.pi / 22.0)), 0.55, 0.7)
    a2 = _aa(0.5 + 0.5 * np.sin((x * 0.866 - y * 0.5) * (2 * np.pi / 22.0)), 0.55, 0.7)
    a3 = _aa(0.5 + 0.5 * np.sin(y * (2 * np.pi / 22.0)), 0.55, 0.7)
    par = (np.floor((x * 0.866 + y * 0.5) / 22.0) + np.floor(y / 22.0)) % 2
    return {"b": np.clip(np.maximum(np.maximum(a1, a2), a3) * (0.4 + 0.6 * par), 0, 1).astype(np.float32)}


def _g_anamorph_rings(h, w, rng):
    x, y = _xy(h, w)
    stretch = 1.0 + (y / h) * 3.0
    r = np.sqrt(((x - w / 2) / stretch) ** 2 + (y - h * 0.35) ** 2)
    ring = 0.5 + 0.5 * np.sin(r * (2 * np.pi / 16.0))
    return {"b": _aa(ring, 0.78, 0.92)}


def _g_chroma_split(h, w, rng):
    base = _aa(_fbm(h, w, rng, 100, 3), 0.53, 0.65)
    off = 5
    r_ = np.roll(base, (-off, 0), (0, 1))
    b_ = np.roll(base, (off, 0), (0, 1))
    union = np.clip(base + r_ * 0.7 + b_ * 0.7, 0, 1)
    hue = np.clip(0.0 + (r_ - b_) * 0.5 + 0.5, 0, 1) * 0.9
    return {"b": union * 0.6, "hue": hue.astype(np.float32)}


def _g_dazzle_wedges(h, w, rng):
    _f1, _f2, cid = _cellF1F2(h, w, rng, 120)
    x, y = _xy(h, w)
    b = np.zeros((h, w), np.float32)
    for k in range(6):
        zone = np.abs(cid - (k + 0.5) / 6.0) < (0.5 / 6.0)
        a = k * np.pi / 6.0 + 0.3
        stripes = _aa(0.5 + 0.5 * np.sin((x * np.cos(a) + y * np.sin(a)) * (2 * np.pi / 15.0)), 0.5, 0.68)
        b = np.where(zone, stripes, b)
    return {"b": b.astype(np.float32), "id": cid}


def _g_ferro_rosettes(h, w, rng):
    img = np.zeros((h, w), np.float32)
    for _ in range(160):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        n = int(rng.integers(5, 9))
        R = int(rng.integers(7, 16))
        for k in range(n):
            a = k * 2 * np.pi / n
            cv2.line(img, (cx, cy), (int(cx + np.cos(a) * R), int(cy + np.sin(a) * R)), 1.0, 2)
        cv2.circle(img, (cx, cy), 2, 1.0, -1)
    return {"b": np.clip(img, 0, 1)}


def _g_singularity(h, w, rng):
    th, r = _polar(h, w, w * 0.5, h * 0.5)
    spiral = 0.5 + 0.5 * np.sin(th * 2.0 + np.log(np.maximum(r, 2.0)) * 14.0)
    disk = _aa(spiral, 0.72, 0.88)
    sparkle = _disks(h, w, rng, 260, 1, 1)
    white = _aa(4.0 - np.abs(r - 120.0), 0, 2.5)
    return {"b": np.clip(disk + sparkle * 0.7, 0, 1), "white": white}


def _g_iris_blades(h, w, rng):
    """Machine-iris: angular blade edges spiraling with radius + dilation rings.
    NOT _g_hyper_rings (log-spaced rings, no angular term) - first draft cloned
    it and the uniqueness law forbids structural reuse."""
    b = np.zeros((h, w), np.float32)
    for cx, cy in [(w * 0.5, h * 0.5), (w * 0.08, h * 0.1), (w * 0.92, h * 0.9)]:
        th, r = _polar(h, w, cx, cy)
        blades = 0.5 + 0.5 * np.sin(th * 12.0 + r * 0.055)
        rings = 0.5 + 0.5 * np.sin(r * (2 * np.pi / 34.0))
        b = np.maximum(b, _aa(blades, 0.80, 0.93) * _aa(rings, 0.35, 0.6))
    return {"b": b}


def _g_glitch_bloom(h, w, rng):
    _f1, _f2, cid = _cellF1F2(h, w, rng, 70)
    burst = np.zeros((h, w), np.float32)
    for _ in range(36):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
        for _k in range(int(rng.integers(6, 12))):
            a = rng.random() * 6.283
            L = int(rng.integers(10, 40))
            cv2.line(burst, (cx, cy), (int(cx + np.cos(a) * L), int(cy + np.sin(a) * L)), 1.0, 1)
    blocks = (cid > 0.78).astype(np.float32)
    return {"b": np.clip(burst + blocks * 0.6, 0, 1), "id": cid}


# ═══════════════════════════════════════════════ THE WAVE-2 FLEET (90)
# id: (day_rgb, night_rgb, geometry, g_lanes, tri, Name, desc, swatch)
# Descs state DAY → NIGHT so track testers know exactly what to look for.
NIGHTSHIFT2_DEFS = OrderedDict([
    # ---- OCEAN / WAVES ----
    ("ns2_tide_turner",    ((16, 62, 96),  (64, 230, 200), _g_tide_lines,   (10, 28, 48), False, "Tide Turner",    "DAY deep harbor blue with fine tide lines — NIGHT every crest glows seafoam. The ocean turning over in the dark.", "#103e60")),
    ("ns2_breaker_bay",    ((20, 80, 120), (255, 255, 255), _g_breaker_curls,(8, 24, 44),  False, "Breaker Bay",    "DAY storm-sea teal — NIGHT hundreds of curling breakers flash white foam. Surf report: firing.", "#145078")),
    ("ns2_caustic_royale", ((10, 40, 90),  (80, 200, 255), _g_caustic_net,  (10, 30, 52), False, "Caustic Royale", "DAY pool-floor navy — NIGHT the double caustic web dances electric aqua. Sunlight through water, at midnight.", "#0a285a")),
    ("ns2_kelp_cathedral", ((14, 60, 44),  (140, 255, 60), _g_kelp_columns, (12, 32, 54), False, "Kelp Cathedral", "DAY dark kelp-forest green — NIGHT the swaying columns light up lime. A dive at dusk.", "#0e3c2c")),
    ("ns2_rain_ritual",    ((44, 52, 70),  (120, 190, 255), _g_rain_rings,  (10, 26, 46), False, "Rain Ritual",    "DAY slate rain-cloud grey — NIGHT overlapping raindrop rings ripple ice blue. First drops on still water.", "#2c3446")),
    ("ns2_maelstrom",      ((18, 34, 66),  (0, 255, 190),  _g_maelstrom,    (8, 22, 42),  False, "Maelstrom",      "DAY midnight sea — NIGHT four spiral whirlpools churn glowing turquoise arms. Do not sail here.", "#122242")),
    ("ns2_foam_lace",      ((150, 170, 185),(255, 245, 235),_g_foam_lace,   (12, 34, 56), False, "Foam Lace",      "DAY weathered sea-glass grey — NIGHT the lace between bubbles burns warm white. Champagne surf.", "#96aab9")),
    ("ns2_undertow",       ((26, 46, 80),  (255, 120, 40), _g_current_bands,(10, 28, 50), False, "Undertow",       "DAY calm banded blue — NIGHT alternating current bands reveal hidden AMBER chevrons pulling sideways. The current you can't see.", "#1a2e50")),
    ("ns2_plankton_wake",  ((8, 24, 40),   (60, 255, 220), _g_plankton_wake,(8, 24, 44),  False, "Plankton Wake",  "DAY near-black abyss — NIGHT a bioluminescent wake of teal-green sparks. Every touch leaves light.", "#081828")),
    ("ns2_jelly_ballet",   ((30, 24, 60),  (255, 130, 240), _g_jelly_drift, (10, 30, 52), False, "Jelly Ballet",   "DAY deep violet water — NIGHT drifting jellyfish bells and tentacles glow neon pink. Graceful and slightly menacing.", "#1e163c")),
    ("ns2_abyss_lines",    ((12, 16, 28),  (90, 160, 255), _g_abyss_strata, (12, 30, 50), False, "Abyss Lines",    "DAY charcoal-navy void — NIGHT ragged sonar strata lines sweep pale blue. The depth chart of nowhere.", "#0c101c")),
    ("ns2_sonar_ghost",    ((10, 30, 30),  (0, 255, 140),  _g_sonar_sweep,  (8, 26, 46),  False, "Sonar Ghost",    "DAY blackout naval green — NIGHT a sonar sweep, range rings and contact blips burn radar green. Something's out there.", "#0a1e1e")),
    # ---- SKY / SUN / STORM ----
    ("ns2_granule_sun",    ((150, 60, 10), (255, 220, 80), _g_solar_granules,(8, 24, 44), False, "Granule Sun",    "DAY burnt solar orange — NIGHT every convection cell core boils gold. The surface of the sun, idling.", "#963c0a")),
    ("ns2_corona_crown",   ((90, 30, 60),  (255, 240, 180), _g_corona_fan,  (8, 22, 40),  False, "Corona Crown",   "DAY eclipse-plum dusk — NIGHT a fan of corona rays streams warm white from above. Totality, then fire.", "#5a1e3c")),
    ("ns2_fork_daddy",     ((30, 30, 44),  (200, 220, 255), _g_fork_lightning,(8, 20, 38), False, "Fork Daddy",    "DAY storm-front graphite — NIGHT forked lightning rips top to bottom in blue-white. The strike, frozen.", "#1e1e2c")),
    ("ns2_thunder_topo",   ((40, 44, 58),  (255, 200, 60), _g_thunder_topo, (10, 28, 50), False, "Thunder Topo",   "DAY brooding cloud grey — NIGHT the thunderhead's contour lines glow amber like a storm map. Weather radar couture.", "#282c3a")),
    ("ns2_aurora_veil",    ((16, 24, 44),  (80, 255, 160), _g_aurora_curtain,(10, 30, 52), False, "Aurora Veil",   "DAY polar midnight blue — NIGHT folded aurora curtains wash green-to-violet across the panels. The sky came down.", "#101c2c")),
    ("ns2_nebula_dust",    ((10, 10, 18),  (200, 120, 255), _g_star_nebula, (8, 24, 46),  False, "Nebula Dust",    "DAY starless black — NIGHT a whole starfield ignites with violet-magenta nebula wisps. Deep space on a quarter panel.", "#0a0a12")),
    ("ns2_first_light",    ((190, 120, 70),(255, 210, 120), _g_dawn_rays,   (10, 28, 48), False, "First Light",    "DAY warm adobe tan — NIGHT dawn rays fan gold across the body. Sunrise you can drive.", "#be7846")),
    ("ns2_hailstorm",      ((70, 78, 92),  (220, 240, 255), _g_hail_streaks,(8, 24, 42),  False, "Hailstorm",      "DAY cold front grey-blue — NIGHT steep hail streaks and impact rings flash ice white. Duck.", "#464e5c")),
    ("ns2_monsoon_glass",  ((24, 40, 52),  (140, 220, 255), _g_monsoon_cross,(10, 26, 48), False, "Monsoon Glass", "DAY rain-dark cyan-grey — NIGHT two crossing rain angles etch bright silver-blue. A downpour lit by headlights.", "#182834")),
    ("ns2_cloudbreak",     ((200, 205, 215),(255, 170, 60), _g_cloud_gaps,  (12, 32, 54), False, "Cloudbreak",     "DAY soft overcast white — NIGHT the gaps between clouds pour amber sunset through. The hole in the weather.", "#c8cdd7")),
    ("ns2_eclipse_order",  ((36, 30, 48),  (255, 60, 40),  _g_eclipse_rings,(8, 24, 44),  True,  "Eclipse Order",  "TRI-STATE: violet-slate day, blood-red concentric rings at night, and a razor WHITE flash ring at totality's edge. Ceremonial.", "#241e30")),
    ("ns2_ion_river",      ((20, 36, 60),  (0, 220, 255),  _g_ion_streamlines,(8, 26, 48), False, "Ion River",     "DAY deep space blue — NIGHT charged streamlines flow cyan along an invisible magnetic field. Plasma with a current.", "#14243c")),
    ("ns2_static_sky",     ((50, 50, 60),  (255, 255, 200), _g_static_rows, (10, 30, 50), False, "Static Sky",     "DAY analog-grey — NIGHT dead-channel static rows dance pale gold. Broadcast over.", "#32323c")),
    # ---- FIRE / EARTH ----
    ("ns2_fissure_king",   ((60, 24, 20),  (255, 140, 20), _g_magma_fissure,(8, 24, 44),  False, "Fissure King",   "DAY cooled basalt brown — NIGHT ridged magma fissures split open molten orange. The crust is thin here.", "#3c1814")),
    ("ns2_ash_procession", ((66, 62, 60),  (255, 90, 30),  _g_ashfall,     (10, 28, 50),  False, "Ash Procession", "DAY volcanic ash grey — NIGHT falling embers streak hot orange through the plume. After the eruption.", "#423e3c")),
    ("ns2_geyser_field",   ((80, 96, 88),  (180, 255, 240), _g_geyser_plumes,(10, 30, 52), False, "Geyser Field",  "DAY mineral sage green — NIGHT steam plumes erupt glowing white-teal. Yellowstone, floored.", "#506058")),
    ("ns2_agate_heart",    ((90, 50, 80),  (255, 180, 240), _g_geode_bands, (10, 28, 50), False, "Agate Heart",    "DAY dusty mauve stone — NIGHT jagged geode bands ring out in pink crystal light. Split the rock, find the glow.", "#5a3250")),
    ("ns2_dune_sea",       ((140, 100, 55),(255, 220, 140), _g_dune_ripples,(12, 32, 54), False, "Dune Sea",       "DAY desert ochre — NIGHT wind-carved ripple crests light pale gold. Sand under a full moon.", "#8c6437")),
    ("ns2_fault_line",     ((84, 70, 60),  (255, 80, 80),  _g_strata_fault, (10, 28, 48), False, "Fault Line",     "DAY layered canyon earth — NIGHT the strata glow red where the faults stepped them sideways. Geology with a grudge.", "#544639")),
    ("ns2_obsidian_court", ((26, 22, 30),  (180, 80, 255), _g_obsidian_facets,(8, 26, 46), False, "Obsidian Court","DAY volcanic glass black — NIGHT facet edges spark violet and random whole shards ignite. Knapped by lightning.", "#1a161e")),
    ("ns2_crevasse_blue",  ((190, 205, 215),(60, 160, 255), _g_crevasse,    (8, 24, 44),  False, "Crevasse Blue",  "DAY glacier white — NIGHT the crevasse cracks glow that impossible deep-ice blue. Beautiful. Do not step.", "#becdd7")),
    # ---- GRUNGE ----
    ("ns2_rust_prophet",   ((96, 100, 108),(255, 120, 40), _g_rust_bloom,  (10, 30, 52),  False, "Rust Prophet",   "DAY bare steel grey — NIGHT rust blooms and speckle halos burn corrosion orange. Entropy wins, gorgeously.", "#60646c")),
    ("ns2_peel_out",       ((160, 60, 50), (80, 220, 255), _g_peel_flakes, (10, 28, 50),  False, "Peel Out",       "DAY faded barn red — NIGHT the peeling paint chips flash the old cyan coat underneath. Layers of history, lit.", "#a03c32")),
    ("ns2_oil_omen",       ((18, 18, 22),  (255, 255, 255), _g_oil_marble, (8, 24, 46),   False, "Oil Omen",       "DAY wet-asphalt black — NIGHT the oil-slick marble swirls a full spectral rainbow. A puddle that means trouble.", "#121216")),
    ("ns2_patchwork_slab", ((120, 118, 112),(255, 200, 90), _g_concrete_patch,(12, 32, 54),False, "Patchwork Slab","DAY tired concrete — NIGHT the crack web and repair patches sodium-lamp amber. Infrastructure noir.", "#787670")),
    ("ns2_gutter_glam",    ((54, 58, 54),  (170, 255, 90), _g_grime_drips, (10, 28, 50),  False, "Gutter Glam",    "DAY grimy charcoal — NIGHT every drip streak runs toxic slime green. The gutter, but make it fashion.", "#363a36")),
    ("ns2_swirl_mark",     ((30, 30, 34),  (200, 200, 220), _g_swirl_scratches,(12, 34, 56),True, "Swirl Mark",    "TRI-STATE: show-car black day, silver scratch arcs at night, plus razor-white micro flashes in direct beams. Every detailer's nightmare, weaponized.", "#1e1e22")),
    ("ns2_overspray_law",  ((70, 46, 90),  (255, 240, 120), _g_overspray_edge,(10, 28, 48),False, "Overspray Law", "DAY masked-off purple — NIGHT the stencil edges and spray drift light up gold. Evidence of the crime.", "#462e5a")),
    ("ns2_wheatpaste",     ((130, 116, 96),(255, 100, 160), _g_poster_tears,(10, 30, 52), False, "Wheatpaste",     "DAY sun-bleached poster tan — NIGHT torn sheet edges and a lucky whole layer glow hot pink. Forty years of gig flyers.", "#827460")),
    ("ns2_spatter_creed",  ((40, 40, 46),  (255, 190, 60), _g_weld_spatter,(8, 26, 48),   False, "Spatter Creed",  "DAY shop-floor steel — NIGHT weld spatter and spark bursts sizzle amber. Made, not bought.", "#28282e")),
    ("ns2_acid_verdict",   ((90, 105, 90), (0, 255, 170),  _g_acid_pits,   (10, 30, 52),  False, "Acid Verdict",   "DAY etched pewter green — NIGHT every pit rim rings acid teal. The chemical peel nobody ordered.", "#5a695a")),
    ("ns2_tar_rite",       ((24, 22, 24),  (255, 60, 20),  _g_tar_seams,   (8, 24, 46),   False, "Tar Rite",       "DAY cracked blacktop — NIGHT the seams between plates run lava red. The road remembers heat.", "#181618")),
    ("ns2_hail_damage",    ((110, 116, 126),(255, 255, 210),_g_dent_crescents,(12, 32, 54),False, "Hail Damage",   "DAY insurance-claim silver — NIGHT two hundred dent crescents catch pale gold light. Totaled, beautifully.", "#6e747e")),
    # ---- RACING ----
    ("ns2_checker_reaper", ((30, 30, 32),  (255, 40, 40),  _g_checker_warp,(10, 28, 48),  True,  "Checker Reaper", "TRI-STATE: warped checker in black by day, alternate squares ignite RED at night, white razor grid seams flash in beams. The flag, possessed.", "#1e1e20")),
    ("ns2_tread_lord",     ((44, 40, 38),  (255, 160, 40), _g_tread_chevrons,(10, 30, 52),False, "Tread Lord",     "DAY tire-rubber black-brown — NIGHT the chevron tread blocks light amber like heat cycling through. Fresh off the stacker.", "#2c2826")),
    ("ns2_terminal_v",     ((20, 28, 40),  (120, 255, 255), _g_speed_streaks,(8, 22, 42), False, "Terminal V",     "DAY deep gunmetal blue — NIGHT tapered speed streaks scream cyan past the panels. The car looks fast parked. At night it looks faster.", "#141c28")),
    ("ns2_slipstream_cult",((36, 36, 52),  (255, 220, 100), _g_slipstream, (10, 28, 50),  False, "Slipstream Cult","DAY quiet indigo-grey — NIGHT nested draft arcs glow gold behind invisible cars. Tow, granted.", "#242434")),
    ("ns2_rotor_glow",     ((40, 40, 44),  (255, 90, 30),  _g_rotor_drill, (8, 26, 46),   False, "Rotor Glow",     "DAY machined grey — NIGHT drilled rotor rings burn brake-orange after the big stop. Fade is a myth.", "#28282c")),
    ("ns2_kerb_appeal",    ((150, 40, 40), (255, 250, 240), _g_kerb_wear,  (10, 30, 52),  False, "Kerb Appeal",    "DAY track-limit red — NIGHT the kerb stripe edges and rubbered-in wear flash white. Ride it harder.", "#962828")),
    ("ns2_apex_hunter",    ((26, 44, 34),  (140, 255, 60), _g_apex_arrows, (10, 28, 50),  False, "Apex Hunter",    "DAY racing green — NIGHT lanes of arrowheads point lime at every apex. The line, illuminated.", "#1a2c22")),
    ("ns2_telemetry_ghost",((22, 26, 34),  (0, 255, 200),  _g_telemetry_waves,(8, 24, 44),False, "Telemetry Ghost","DAY matte data-slate — NIGHT rows of telemetry traces scroll mint green. Your lap, haunting you.", "#161a22")),
    ("ns2_gear_church",    ((52, 48, 44),  (255, 200, 80), _g_gear_mesh,   (10, 30, 52),  False, "Gear Church",    "DAY oily bronze-grey — NIGHT interlocked gear trains shine brass. The drivetrain's cathedral.", "#34302c")),
    ("ns2_drift_sermon",   ((38, 34, 40),  (240, 240, 255), _g_drift_smoke,(10, 28, 48),  False, "Drift Sermon",   "DAY faded asphalt violet — NIGHT tire arcs and smoke wisps glow white. The angle was the point.", "#262228")),
    ("ns2_photo_verdict",  ((28, 30, 36),  (255, 230, 120), _g_photo_finish,(8, 26, 46),  False, "Photo Verdict",  "DAY dark slit-scan grey — NIGHT the finish-line slits strobe gold with jitter. Won it by the bumper.", "#1c1e24")),
    ("ns2_pit_board",      ((20, 20, 24),  (255, 170, 30), _g_pit_matrix,  (10, 30, 52),  False, "Pit Board",      "DAY blank LED panels — NIGHT the dot-matrix lights amber like a pit board mid-message. P1. BOX. PUSH.", "#141418")),
    # ---- TECH / GLITCH ----
    ("ns2_nano_hive",      ((30, 38, 44),  (0, 255, 230),  _g_hex_nano,    (10, 28, 50),  False, "Nano Hive",      "DAY carbon-teal micro hex — NIGHT the lattice and random lit cells pulse cyan. A hive of machines agreeing.", "#1e262c")),
    ("ns2_trace_route",    ((16, 40, 30),  (120, 255, 120), _g_pcb_traces, (10, 30, 52),  False, "Trace Route",    "DAY PCB-mask green-black — NIGHT routed traces and via dots light circuit green. The packet always arrives.", "#102820")),
    ("ns2_datamosh_ritual",((40, 26, 48),  (255, 60, 220), _g_datamosh,    (8, 24, 46),   False, "Datamosh Ritual","DAY corrupted plum — NIGHT displaced blocks and fringe columns tear magenta-cyan across rows. The keyframe never came.", "#281a30")),
    ("ns2_lissajous_love", ((24, 30, 40),  (255, 255, 160), _g_lissajous,  (8, 26, 46),   False, "Lissajous Love", "DAY oscilloscope navy — NIGHT sixteen phase curves trace pale gold loops. Two signals, in love.", "#181e28")),
    ("ns2_laser_horizon",  ((22, 16, 40),  (255, 60, 180), _g_laser_horizon,(8, 24, 44),  False, "Laser Horizon",  "DAY retrowave dusk purple — NIGHT the perspective grid rolls hot pink to a starfield horizon. 1986 called; it wants a ride.", "#161028")),
    ("ns2_wireframe_west", ((30, 34, 30),  (160, 255, 200), _g_wire_terrain,(10, 28, 50), False, "Wireframe West", "DAY topo-sim olive — NIGHT stacked terrain polylines glow mint with hidden-line gaps. Flying over the map, not the land.", "#1e221e")),
    ("ns2_holo_decree",    ((26, 34, 46),  (0, 220, 255),  _g_holo_scan,   (8, 26, 48),   False, "Holo Decree",    "DAY projector-off slate — NIGHT scan bands, row lines and edge ticks shimmer cyan-magenta hologram. Authenticity: verified.", "#1a222e")),
    ("ns2_rain_of_code",   ((14, 22, 16),  (60, 255, 100), _g_binary_rain, (10, 30, 52),  False, "Rain of Code",   "DAY terminal-black green — NIGHT dotted columns rain down phosphor green at different speeds. You've seen this rain before.", "#0e1610")),
    ("ns2_quasi_star",     ((40, 36, 56),  (255, 200, 255), _g_quasilattice,(10, 28, 50), False, "Quasi Star",     "DAY muted amethyst — NIGHT a five-fold quasicrystal interference lattice blooms pink-white. Order without repetition.", "#282438")),
    ("ns2_glitch_bloom",   ((30, 26, 34),  (255, 240, 80), _g_glitch_bloom,(8, 24, 46),   False, "Glitch Bloom",   "DAY dark violet static — NIGHT random cells detonate into streak fans of gold. Beautiful crash logs.", "#1e1a22")),
    # ---- ANIMAL / ORGANIC ----
    ("ns2_tiger_verdict",  ((190, 110, 30),(30, 30, 30),   _g_tiger_brush, (10, 28, 50),  False, "Tiger Verdict",  "DAY blazing tiger orange — NIGHT the brush slashes go VOID BLACK, eating the light between them. The stripes hunt after dark.", "#be6e1e")),
    ("ns2_zebra_current",  ((225, 225, 220),(40, 40, 48),  _g_zebra_flow,  (12, 32, 54),  False, "Zebra Current",  "DAY ivory white — NIGHT the flowing stripes drop to charcoal, reversing the animal. Day zebra, night negative.", "#e1e1dc")),
    ("ns2_rosette_court",  ((180, 140, 60),(255, 100, 30), _g_leopard_rosettes,(10, 30, 52),False,"Rosette Court", "DAY savanna gold — NIGHT every broken rosette ring flares ember orange. Spotted, then hunted.", "#b48c3c")),
    ("ns2_viper_lattice",  ((60, 70, 40),  (200, 255, 60), _g_diamond_snake,(10, 28, 50), False, "Viper Lattice",  "DAY olive scale-diamond weave — NIGHT the swaying lattice glows venom green. It was never rope.", "#3c4628")),
    ("ns2_peacock_court",  ((20, 40, 60),  (0, 220, 200),  _g_peacock_eyes,(8, 26, 48),   False, "Peacock Court",  "DAY deep teal-navy plumage — NIGHT a hundred feather eyes open in shifting blue-green iridescence. The tail is watching.", "#14283c")),
    ("ns2_wing_chapel",    ((70, 50, 90),  (255, 160, 255), _g_wing_veins, (10, 30, 52),  False, "Wing Chapel",    "DAY dusty violet membrane — NIGHT the wing veins and radiating ribs glow orchid. Stained glass that flies.", "#46325a")),
    ("ns2_mycelium_mind",  ((240, 238, 230),(150, 120, 255),_g_mycelium,   (12, 32, 54),  False, "Mycelium Mind",  "DAY bone white — NIGHT the fungal thread network lights lavender, thinking. The forest's internet.", "#f0eee6")),
    ("ns2_dendrite_choir", ((30, 30, 40),  (255, 220, 0),  _g_dendrites,   (8, 24, 46),   False, "Dendrite Choir", "DAY neural dark — NIGHT branches, somata and synapse sparks fire gold. A thought, mid-flight.", "#1e1e28")),
    ("ns2_koi_dynasty",    ((200, 90, 60), (255, 240, 200), _g_koi_scales, (12, 32, 54),  False, "Koi Dynasty",    "DAY koi orange-red — NIGHT the crescent scale rows shimmer pearl. Four hundred years old and showing off.", "#c85a3c")),
    ("ns2_moth_omen",      ((110, 100, 90),(255, 200, 255), _g_moth_dust,  (12, 34, 56),  False, "Moth Omen",      "DAY dusty taupe wing — NIGHT the powder gradient and wing bars glow pale orchid. Drawn to your headlights.", "#6e645a")),
    # ---- EXOTIC / PSYCHO ----
    ("ns2_moire_prophet",  ((40, 40, 46),  (0, 255, 255),  _g_moire_wheels,(8, 24, 44),   False, "Moiré Prophet",  "DAY quiet graphite — NIGHT two off-center ring gratings interfere in cyan beat patterns that move as you do. The pattern isn't ON the car.", "#28282e")),
    ("ns2_rhomb_royalty",  ((60, 44, 70),  (255, 180, 60), _g_rhomb_field, (10, 28, 50),  False, "Rhomb Royalty",  "DAY plum rhombus tiling — NIGHT alternating rhombs and seam lines ignite amber. Penrose would drive it.", "#3c2c46")),
    ("ns2_hyper_rings",    ((20, 30, 40),  (255, 120, 255), _g_hyper_rings,(8, 24, 46),   False, "Hyper Rings",    "DAY abyssal blue-grey — NIGHT log-spaced rings from five poles collapse inward in magenta. Non-Euclidean parking only.", "#141e28")),
    ("ns2_frost_sermon",   ((210, 220, 230),(120, 200, 255),_g_frost_feathers,(12, 32, 54),False,"Frost Sermon",   "DAY frosted-glass white — NIGHT feather crystals grow ice blue from every edge. Winter's handwriting.", "#d2dce6")),
    ("ns2_spiro_seance",   ((30, 24, 36),  (255, 200, 120), _g_spiro_loops,(8, 26, 46),   False, "Spiro Séance",   "DAY dark mulberry — NIGHT ten spirograph orbits trace warm gold geometry. Summoned with a pen and two gears.", "#1e1824")),
    ("ns2_kaleid_kingdom", ((44, 34, 54),  (255, 255, 255), _g_kaleid_fold,(8, 24, 46),   False, "Kaleid Kingdom", "DAY muted royal violet — NIGHT the eight-fold mirror bloom erupts in shifting rainbow symmetry. Turn the tube.", "#2c2236")),
    ("ns2_pulse_doctrine", ((34, 38, 34),  (255, 80, 120), _g_op_pulse,    (10, 28, 50),  False, "Pulse Doctrine", "DAY op-art moss grey — NIGHT warped concentric squares pulse hot rose from the center. Stare too long and it staresback.", "#222622")),
    ("ns2_stair_heresy",   ((56, 56, 64),  (160, 255, 220), _g_iso_stairs, (10, 30, 52),  False, "Stair Heresy",   "DAY isometric slate — NIGHT the impossible staircase bands glow mint, going up forever in both directions. Escher's daily driver.", "#383840")),
    ("ns2_anamorph_altar", ((46, 36, 30),  (255, 220, 90), _g_anamorph_rings,(10, 28, 50),False, "Anamorph Altar", "DAY sepia leather — NIGHT stretched rings resolve gold from exactly one viewing angle. Park it right or park it wrong.", "#2e241e")),
    ("ns2_chroma_heresy",  ((28, 28, 32),  (255, 0, 128),  _g_chroma_split,(8, 24, 44),   False, "Chroma Heresy",  "DAY soft black — NIGHT the same pattern fires three times, offset like misregistered print, hue split along the offset. Your eyes are fine. Mostly.", "#1c1c20")),
    ("ns2_dazzle_doctrine",((90, 90, 100), (255, 240, 60), _g_dazzle_wedges,(10, 30, 52), False, "Dazzle Doctrine","DAY WWI dazzle-ship grey — NIGHT each angular zone's stripes fire yellow at its own angle. Built to confuse rangefinders; still works.", "#5a5a64")),
    ("ns2_ferro_gospel",   ((30, 34, 40),  (150, 220, 255), _g_ferro_rosettes,(8, 26, 46),False, "Ferro Gospel",   "DAY magnet-black steel — NIGHT ferrofluid spike rosettes bristle silver-blue. The field made flesh.", "#1e2228")),
    ("ns2_singularity",    ((16, 16, 22),  (255, 180, 60), _g_singularity, (8, 22, 42),   True,  "Singularity",    "TRI-STATE: void black day, a full-canvas gold accretion spiral at night, and a white-hot event-horizon ring in direct light. Beyond this line, nothing escapes.", "#101016")),
    ("ns2_iris_reactor",   ((36, 20, 40),  (0, 255, 200),  _g_iris_blades, (12, 34, 56),  False, "Iris Reactor",   "DAY reactor-core plum — NIGHT the ring cascade dilates teal like a machine iris opening. Power at 108 percent.", "#241428")),
])


def _wrap_geom(geom):
    """Adaptive density: stamped 1-2px art dilutes below the factory's metal
    threshold once the 1024 work grid resizes (0.5-value lines -> M~124).
    Dilate thin masks until the carrier holds >=10% area at full value -
    geometry identity is preserved, the strokes just gain the width they
    need to survive resampling (and read as DETAIL, not dust, on the car)."""
    def wrapped(h, w, rng):
        f = geom(h, w, rng)
        b = np.asarray(f.get("b"), np.float32)
        for _ in range(3):
            if float((b > 0.5).mean()) >= 0.10:
                break
            b = cv2.dilate(b, np.ones((3, 3), np.uint8))
        f["b"] = np.clip(b, 0, 1)
        return f
    return wrapped


def install_into_engine(mono_reg, base_reg=None):
    n = 0
    for fid, d in NIGHTSHIFT2_DEFS.items():
        day, night, geom, lanes, tri = d[0], d[1], d[2], d[3], d[4]
        mono_reg[fid] = _make_ns(fid, day, night, _wrap_geom(geom), lanes, tri)
        n += 1
    try:
        import engine.expansions.fusions as _fus
        for fid in NIGHTSHIFT2_DEFS:
            _fus.FUSION_REGISTRY[fid] = mono_reg[fid]
    except Exception:
        pass
    return "nightshift-wave2: %d color-flip experiments registered" % n


def emit_js_defs():
    """Emit the JS DEFS rows for js/spb-nightshift-lab.js (single source of truth)."""
    rows = []
    for fid, d in NIGHTSHIFT2_DEFS.items():
        name, desc, swatch = d[5], d[6], d[7]
        desc = desc.replace("'", "\\'")
        rows.append("        ['%s', '%s', '%s', '%s']," % (fid, name.replace("'", "\\'"), desc, swatch))
    return "\n".join(rows)
