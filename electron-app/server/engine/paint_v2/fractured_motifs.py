"""FRACTURED motif generators — the dark-albedo art toolkit for the 5 new FRACTURED
categories (DEEP, REAPER, CRYPTID, UFO, RAINBOW).

DOCTRINE (Wovenlight + UV-agnostic coverage):
  * DARK base, high-contrast SATURATED motif drawn on it. fracture_spec() traces the
    motif and ignites it (near-chrome body + maxed clearcoat flashing at angle).
  * The art is a 2048x2048 sheet that UV-wraps a car whose panels are scattered/rotated/
    mirrored. So motifs MUST be SMALL, DENSE, OMNIDIRECTIONAL, and cover the ENTIRE canvas
    with NO dead zones — many tiny complete elements, never one big centered subject.

Composers return HxWx3 float32 in 0..1 (paint/albedo). Deterministic by seed.
Individual finishes are ~15-line recipes (composer + seed + palette) layered on top.
"""
from __future__ import annotations

import cv2
import numpy as np


def _rng(seed) -> np.random.Generator:
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


# ── field primitives ─────────────────────────────────────────────────────────
def _noise(h: int, w: int, scale: int, rng: np.random.Generator) -> np.ndarray:
    s = max(2, int(scale))
    n = rng.standard_normal((s, s)).astype(np.float32)
    return cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)


def _fbm(h: int, w: int, rng: np.random.Generator, octaves: int = 5, base: int = 5) -> np.ndarray:
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * _noise(h, w, base * (2 ** o), rng)
        tot += amp
        amp *= 0.5
    out /= max(tot, 1e-6)
    return (out - out.min()) / (float(np.ptp(out)) + 1e-6)


def _ridges(field: np.ndarray, sharp: float = 2.0) -> np.ndarray:
    """Thin bright ridge-lines where a smooth field crosses its mid-level."""
    return np.clip(1.0 - np.abs(field - 0.5) * 2.0 * sharp, 0.0, 1.0)


def _caustic_field(h: int, w: int, rng: np.random.Generator, fine: int = 14) -> np.ndarray:
    """Dense, full-canvas web of fine bright filaments (light caustics / currents) — the
    habitat coverage so the dark sheet is never empty and the spec has edges everywhere."""
    a = _ridges(_fbm(h, w, rng, octaves=4, base=fine), sharp=3.0)
    b = _ridges(_fbm(h, w, rng, octaves=3, base=fine * 2), sharp=3.6)
    return np.clip(a * 0.85 + b * 0.6, 0.0, 1.0)


def _ink_field(h: int, w: int, rng: np.random.Generator, fine: int = 9) -> np.ndarray:
    """Domain-warped turbulence — swirling deep-water ink. Moody murk, not bright foam."""
    base = _fbm(h, w, rng, octaves=5, base=fine)
    wx = (_fbm(h, w, rng, 4, fine + 2) - 0.5) * (w * 0.03)
    wy = (_fbm(h, w, rng, 4, fine + 2) - 0.5) * (h * 0.03)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    warped = cv2.remap(base, np.clip(xs + wx, 0, w - 1), np.clip(ys + wy, 0, h - 1),
                       cv2.INTER_LINEAR)
    fine_swirl = _ridges(_fbm(h, w, rng, octaves=4, base=fine * 2), sharp=3.2)
    return np.clip(_ridges(warped, sharp=2.6) * 0.85 + fine_swirl * 0.55, 0.0, 1.0)


# ── glow compositing ──────────────────────────────────────────────────────────
def _add_glow(light: np.ndarray, stroke: np.ndarray, color, core_gain: float = 1.0,
              glow_sigma: float = 3.0, glow_gain: float = 0.5) -> None:
    g = cv2.GaussianBlur(stroke, (0, 0), glow_sigma)
    g = g / (g.max() + 1e-6)
    add = np.clip(stroke * core_gain + g * glow_gain, 0.0, 1.5)
    for i in range(3):
        light[:, :, i] += add * (color[i] / 255.0)


def _finish(base_rgb, light) -> np.ndarray:
    h, w = light.shape[:2]
    out = np.empty((h, w, 3), np.float32)
    for i in range(3):
        out[:, :, i] = base_rgb[i] / 255.0
    return np.clip(out + light, 0.0, 1.0)


# ── scatter: jittered grid so the WHOLE canvas is covered, many small elements ─
def _scatter(h, w, rng, count):
    """Yield (cx, cy, size_px, angle) for `count` small elements over the full canvas."""
    cols = max(1, int(round(np.sqrt(count * w / h))))
    rows = max(1, int(round(count / cols)))
    cw, ch = w / cols, h / rows
    base = min(cw, ch)
    for r in range(rows):
        for c in range(cols):
            cx = (c + 0.5 + rng.uniform(-0.45, 0.45)) * cw
            cy = (r + 0.5 + rng.uniform(-0.45, 0.45)) * ch
            size = base * rng.uniform(0.66, 1.18)
            ang = rng.uniform(0, 2 * np.pi)
            yield cx, cy, size, ang


def _xf(local_pts, cx, cy, s, a):
    ca, sa = np.cos(a), np.sin(a)
    p = np.asarray(local_pts, np.float32) * s
    x = p[:, 0] * ca - p[:, 1] * sa + cx
    y = p[:, 0] * sa + p[:, 1] * ca + cy
    return np.stack([x, y], axis=1).astype(np.int32)


def _plankton(h, w, rng, density=0.04):
    """Fine bioluminescent speckle so the dark field is never empty."""
    f = _fbm(h, w, rng, octaves=3, base=48)
    spk = (f > (1.0 - density)).astype(np.float32)
    return spk


# ── small DEEP creatures (drawn into a 0..1 stroke mask) ──────────────────────
def _draw_kraken(body, suck, cx, cy, s, a, rng):
    """ABSTRACT + MENACING: writhing tapering tendrils unfurling/hooking out of shadow with
    sucker-chains. No literal body — tentacles reach and grasp (the dread is in the curl)."""
    s *= 0.62
    n = rng.integers(3, 6)
    for i in range(int(n)):
        base_ang = a + 6.283 * i / n + rng.uniform(-0.5, 0.5)
        t = np.linspace(0.0, 1.0, 26)
        curl = rng.uniform(1.6, 3.4) * (1.0 if rng.random() < 0.5 else -1.0)  # hook direction
        rad = 0.12 + 0.92 * t
        ang = base_ang + curl * t * t  # accelerating curl -> a grasping hook at the tip
        lx = np.cos(ang) * rad
        ly = np.sin(ang) * rad
        pts = _xf(np.stack([lx, ly], 1), cx, cy, s, 0.0)
        for k in range(len(pts) - 1):  # taper thick base -> thin tip
            th = max(1, int(round((1.0 - t[k]) * 3.4 + 0.6)))
            cv2.line(body, tuple(pts[k]), tuple(pts[k + 1]), 1.0, th, cv2.LINE_AA)
        for k in range(2, 26, 3):  # sucker chain
            cv2.circle(suck, tuple(pts[k]), 1, 1.0, -1, cv2.LINE_AA)


def _draw_eel(body, cx, cy, s, a, rng):
    """A small serpentine body that ripples (electric eel)."""
    s *= 0.5
    t = np.linspace(-1, 1, 28)
    amp = 0.22 + 0.12 * rng.random()
    freq = 2.0 + 2.0 * rng.random()
    lx = t
    ly = np.sin(t * freq * np.pi + rng.uniform(0, 6)) * amp * (1 - np.abs(t) * 0.4)
    cv2.polylines(body, [_xf(np.stack([lx, ly], 1), cx, cy, s, a)], False, 1.0, 2, cv2.LINE_AA)
    # a couple of discharge forks
    for _ in range(rng.integers(1, 3)):
        j = rng.integers(4, 24)
        fx = lx[j] + rng.uniform(-0.1, 0.1)
        fy = ly[j] + rng.uniform(-0.35, 0.35)
        cv2.polylines(body, [_xf(np.array([[lx[j], ly[j]], [fx, fy]]), cx, cy, s, a)],
                      False, 1.0, 1, cv2.LINE_AA)


def _draw_jelly(bell, tend, cx, cy, s, a, rng):
    """A small jellyfish: domed bell + drifting tendrils."""
    s *= 0.5
    th = np.linspace(np.pi, 2 * np.pi, 18)
    dome = np.stack([np.cos(th) * 0.30, np.sin(th) * 0.24], axis=1)
    for off in (0.0, 0.06, 0.12):
        cv2.polylines(bell, [_xf(dome * (1 - off), cx, cy, s, a)], False, 1.0, 1, cv2.LINE_AA)
    for tx in np.linspace(-0.22, 0.22, int(rng.integers(4, 7))):
        t = np.linspace(0, 1, 14)
        lx = tx + np.sin(t * 4 + rng.uniform(0, 6)) * 0.05
        ly = t * (0.5 + 0.3 * rng.random())
        cv2.polylines(tend, [_xf(np.stack([lx, ly], 1), cx, cy, s, a)], False, 1.0, 1, cv2.LINE_AA)


PALETTES = {
    "kraken":       {"base": (3, 8, 11),   "creature": (20, 165, 130), "accent": (115, 255, 170), "field": (11, 82, 72)},
    "electric_eel": {"base": (3, 7, 16),   "creature": (150, 225, 255), "accent": (240, 250, 255), "field": (22, 60, 110)},
    "jellyfish":    {"base": (7, 5, 18),   "creature": (215, 100, 255), "accent": (100, 230, 255), "field": (48, 24, 95)},
}


def motif_kraken(h, w, seed, size_mul: float = 1.6) -> np.ndarray:
    rng = _rng(seed)
    pal = PALETTES["kraken"]
    light = np.zeros((h, w, 3), np.float32)
    body = np.zeros((h, w), np.float32)
    suck = np.zeros((h, w), np.float32)
    _add_glow(light, _ink_field(h, w, rng), pal["field"], 0.62, 1.6, 0.30)
    count = max(10, int(rng.integers(98, 130) / (size_mul ** 2)))
    for cx, cy, s, a in _scatter(h, w, rng, count=count):
        _draw_kraken(body, suck, cx, cy, s * size_mul, a, rng)
    _add_glow(light, body, pal["creature"], 1.0, 2.0, 0.5)
    _add_glow(light, suck, pal["accent"], 1.2, 1.4, 0.32)
    return _finish(pal["base"], light)


def motif_electric_eel(h, w, seed, size_mul: float = 1.6) -> np.ndarray:
    rng = _rng(seed)
    pal = PALETTES["electric_eel"]
    light = np.zeros((h, w, 3), np.float32)
    body = np.zeros((h, w), np.float32)
    _add_glow(light, _caustic_field(h, w, rng, fine=15), pal["field"], 0.42, 1.3, 0.16)
    count = max(10, int(rng.integers(85, 117) / (size_mul ** 2)))
    for cx, cy, s, a in _scatter(h, w, rng, count=count):
        _draw_eel(body, cx, cy, s * size_mul, a, rng)
    _add_glow(light, _plankton(h, w, rng, 0.05), pal["creature"], 0.55, 1.6, 0.2)
    _add_glow(light, body, pal["creature"], 1.2, 1.8, 0.5)
    sparks = (body > 0) & (_fbm(h, w, rng, 3, 60) > 0.7)
    _add_glow(light, sparks.astype(np.float32), pal["accent"], 1.1, 1.4, 0.35)
    return _finish(pal["base"], light)


def motif_jellyfish(h, w, seed, size_mul: float = 1.6) -> np.ndarray:
    rng = _rng(seed)
    pal = PALETTES["jellyfish"]
    light = np.zeros((h, w, 3), np.float32)
    bell = np.zeros((h, w), np.float32)
    tend = np.zeros((h, w), np.float32)
    _add_glow(light, _caustic_field(h, w, rng, fine=17), pal["field"], 0.40, 1.3, 0.15)
    count = max(10, int(rng.integers(72, 98) / (size_mul ** 2)))
    for cx, cy, s, a in _scatter(h, w, rng, count=count):
        _draw_jelly(bell, tend, cx, cy, s * size_mul, a, rng)
    _add_glow(light, _plankton(h, w, rng, 0.045), pal["accent"], 0.55, 1.6, 0.2)
    _add_glow(light, tend, pal["creature"], 0.85, 1.8, 0.35)
    _add_glow(light, bell, pal["creature"], 1.25, 1.9, 0.5)
    return _finish(pal["base"], light)


# ── generic composer: field coverage + scattered small elements, 1.6x standard ──
def _compose(h, w, seed, drawer, pal, fieldfn, fine, base_lo, base_hi, size_mul=1.6,
             field_g=(0.5, 1.5, 0.22), cr_g=(1.0, 1.9, 0.45), ac_g=(1.2, 1.4, 0.32)):
    rng = _rng(seed)
    light = np.zeros((h, w, 3), np.float32)
    st = np.zeros((h, w), np.float32)
    ac = np.zeros((h, w), np.float32)
    _add_glow(light, fieldfn(h, w, rng, fine), pal["field"], *field_g)
    count = max(8, int(rng.integers(base_lo, base_hi) / (size_mul ** 2)))
    for cx, cy, s, a in _scatter(h, w, rng, count):
        drawer(st, ac, cx, cy, s * size_mul, a, rng)
    _add_glow(light, st, pal["creature"], *cr_g)
    _add_glow(light, ac, pal["accent"], *ac_g)
    return _finish(pal["base"], light)


# ── 17 deep-sea element drawers — signature (stroke, accent, cx, cy, s, a, rng) ──
def _el_lure(st, ac, cx, cy, s, a, rng):
    s *= 0.5
    n = int(rng.integers(7, 13))
    for i in range(n):
        ang = a + 6.283 * i / n
        L = 0.5 + 0.5 * rng.random()
        p = _xf(np.array([[0, 0], [np.cos(ang) * L, np.sin(ang) * L]]), cx, cy, s, 0.0)
        cv2.line(st, tuple(p[0]), tuple(p[1]), 1.0, 1, cv2.LINE_AA)
    cv2.circle(ac, (int(cx), int(cy)), max(1, int(s * 0.16)), 1.0, -1, cv2.LINE_AA)


def _el_spiral(st, ac, cx, cy, s, a, rng):
    s *= 0.55
    t = np.linspace(0, 1, 40)
    ang = a + rng.uniform(1.6, 2.4) * 6.283 * t
    rad = 0.06 + 0.94 * t
    pts = _xf(np.stack([np.cos(ang) * rad, np.sin(ang) * rad], 1), cx, cy, s, 0.0)
    cv2.polylines(st, [pts], False, 1.0, 2, cv2.LINE_AA)
    for k in range(0, 40, 6):
        cv2.circle(ac, tuple(pts[k]), 1, 1.0, -1, cv2.LINE_AA)


def _el_ribs(st, ac, cx, cy, s, a, rng):
    s *= 0.5
    n = int(rng.integers(4, 7))
    for i in range(n):
        off = (i / max(1, n - 1) - 0.5) * 0.9
        t = np.linspace(-1, 1, 20)
        cv2.polylines(st, [_xf(np.stack([t, off + np.sin((t + 1) * 1.57) * 0.35], 1), cx, cy, s, a)],
                      False, 1.0, 2, cv2.LINE_AA)


def _el_vent(st, ac, cx, cy, s, a, rng):
    s *= 0.55

    def br(x, y, ang, length, depth):
        if depth <= 0 or length < 0.05:
            return
        nx, ny = x + np.cos(ang) * length, y + np.sin(ang) * length
        p = _xf(np.array([[x, y], [nx, ny]]), cx, cy, s, 0.0)
        cv2.line(st, tuple(p[0]), tuple(p[1]), 1.0, max(1, depth), cv2.LINE_AA)
        cv2.circle(ac, tuple(p[1]), 1, 1.0, -1, cv2.LINE_AA)
        br(nx, ny, ang + rng.uniform(0.2, 0.6), length * 0.7, depth - 1)
        br(nx, ny, ang - rng.uniform(0.2, 0.6), length * 0.7, depth - 1)
    br(0, 0.6, a - 1.57, 0.4, 3)


def _el_ripple(st, ac, cx, cy, s, a, rng):
    s *= 0.5
    n = int(rng.integers(3, 6))
    for i in range(n):
        cv2.circle(st, (int(cx), int(cy)), max(1, int(s * (0.2 + 0.8 * i / n))), 1.0, 1, cv2.LINE_AA)


def _el_bubbles(st, ac, cx, cy, s, a, rng):
    s *= 0.5
    for _ in range(int(rng.integers(4, 9))):
        c = _xf(np.array([[rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4)]]), cx, cy, s, 0.0)[0]
        r = max(1, int(s * rng.uniform(0.1, 0.28)))
        cv2.circle(st, tuple(c), r, 1.0, 1, cv2.LINE_AA)
        cv2.circle(ac, (int(c[0] - r // 3), int(c[1] - r // 3)), 1, 1.0, -1, cv2.LINE_AA)


def _el_dendrite(st, ac, cx, cy, s, a, rng):
    s *= 0.55

    def grow(x, y, ang, length, depth):
        if depth <= 0:
            return
        nx, ny = x + np.cos(ang) * length, y + np.sin(ang) * length
        p = _xf(np.array([[x, y], [nx, ny]]), cx, cy, s, 0.0)
        cv2.line(st, tuple(p[0]), tuple(p[1]), 1.0, max(1, depth), cv2.LINE_AA)
        for _ in range(2):
            grow(nx, ny, ang + rng.uniform(-0.7, 0.7), length * 0.68, depth - 1)
    grow(0, 0, a, 0.45, 4)


def _el_wing(st, ac, cx, cy, s, a, rng):
    s *= 0.6
    t = np.linspace(-1, 1, 24)
    sgn = 1.0 if rng.random() < 0.5 else -1.0
    cv2.polylines(st, [_xf(np.stack([t, -np.cos(t * 1.57) * 0.32 * sgn], 1), cx, cy, s, a)],
                  False, 1.0, 2, cv2.LINE_AA)
    tp = _xf(np.array([[0, 0], [0, 0.6]]), cx, cy, s, a)
    cv2.line(st, tuple(tp[0]), tuple(tp[1]), 1.0, 1, cv2.LINE_AA)


def _el_crack(st, ac, cx, cy, s, a, rng):
    s *= 0.6

    def frac(x, y, ang, length, depth):
        if depth <= 0 or length < 0.04:
            return
        nx, ny = x + np.cos(ang) * length, y + np.sin(ang) * length
        p = _xf(np.array([[x, y], [nx, ny]]), cx, cy, s, 0.0)
        cv2.line(st, tuple(p[0]), tuple(p[1]), 1.0, 1, cv2.LINE_AA)
        frac(nx, ny, ang + rng.uniform(-0.5, 0.5), length * 0.78, depth - 1)
        if rng.random() < 0.4:
            frac(nx, ny, ang + rng.uniform(-1.0, 1.0), length * 0.5, depth - 1)
    frac(0, 0, a, 0.5, 5)


def _el_serpent(st, ac, cx, cy, s, a, rng):
    s *= 0.62
    t = np.linspace(0, 1, 40)
    ang = a + np.sin(t * rng.uniform(3, 5) * np.pi) * 1.2
    rad = 0.1 + 0.9 * t
    pts = _xf(np.stack([np.cos(ang) * rad, np.sin(ang) * rad], 1), cx, cy, s, 0.0)
    for k in range(len(pts) - 1):
        cv2.line(st, tuple(pts[k]), tuple(pts[k + 1]), 1.0, max(1, int((1 - t[k]) * 3 + 1)), cv2.LINE_AA)


def _el_urchin(st, ac, cx, cy, s, a, rng):
    s *= 0.5
    n = int(rng.integers(10, 18))
    for i in range(n):
        ang = a + 6.283 * i / n + rng.uniform(-0.1, 0.1)
        L = rng.uniform(0.5, 1.0)
        p = _xf(np.array([[0, 0], [np.cos(ang) * L, np.sin(ang) * L]]), cx, cy, s, 0.0)
        cv2.line(st, tuple(p[0]), tuple(p[1]), 1.0, 1, cv2.LINE_AA)
    cv2.circle(ac, (int(cx), int(cy)), max(1, int(s * 0.1)), 1.0, -1, cv2.LINE_AA)


def _el_lantern(st, ac, cx, cy, s, a, rng):
    s *= 0.45
    p = _xf(np.array([[-0.4, 0], [0.4, 0]]), cx, cy, s, a)
    cv2.line(st, tuple(p[0]), tuple(p[1]), 1.0, 2, cv2.LINE_AA)
    for ox in (-0.3, 0.0, 0.3):
        cv2.circle(ac, tuple(_xf(np.array([[ox, 0]]), cx, cy, s, a)[0]), 1, 1.0, -1, cv2.LINE_AA)


def _el_thicket(st, ac, cx, cy, s, a, rng):
    s *= 0.55
    for ox in np.linspace(-0.35, 0.35, int(rng.integers(4, 7))):
        t = np.linspace(0, 1, 22)
        lx = ox + np.sin(t * rng.uniform(3, 6) + rng.uniform(0, 6)) * 0.12
        cv2.polylines(st, [_xf(np.stack([lx, -1 + 2 * t], 1), cx, cy, s, a)], False, 1.0, 2, cv2.LINE_AA)


def _el_bloom(st, ac, cx, cy, s, a, rng):
    s *= 0.45
    cv2.circle(st, (int(cx), int(cy)), max(1, int(s * 0.4)), 1.0, 2, cv2.LINE_AA)
    n = int(rng.integers(6, 11))
    for i in range(n):
        ang = 6.283 * i / n
        cv2.circle(ac, tuple(_xf(np.array([[np.cos(ang) * 0.7, np.sin(ang) * 0.7]]), cx, cy, s, 0.0)[0]),
                   1, 1.0, -1, cv2.LINE_AA)


def _el_maw(st, ac, cx, cy, s, a, rng):
    s *= 0.55
    th = np.linspace(-1.2, 1.2, 14)
    for sgn in (-1.0, 1.0):
        jaw = np.stack([np.sin(th) * 0.5, sgn * np.abs(np.cos(th)) * 0.35], 1)
        pts = _xf(jaw, cx, cy, s, a)
        cv2.polylines(st, [pts], False, 1.0, 2, cv2.LINE_AA)
        for k in range(1, 14, 2):
            cv2.circle(ac, tuple(pts[k]), 1, 1.0, -1, cv2.LINE_AA)


def _el_pool(st, ac, cx, cy, s, a, rng):
    s *= 0.55
    for i in range(int(rng.integers(2, 5))):
        rr = (0.25 + 0.7 * i / 4)
        th = np.linspace(0, 6.283, 30)
        wob = 1 + np.sin(th * rng.uniform(3, 6) + rng.uniform(0, 6)) * 0.12
        cv2.polylines(st, [_xf(np.stack([np.cos(th) * wob * rr, np.sin(th) * wob * rr], 1), cx, cy, s, 0.0)],
                      True, 1.0, 1, cv2.LINE_AA)


def _el_anemone(st, ac, cx, cy, s, a, rng):
    s *= 0.5
    n = int(rng.integers(8, 14))
    for i in range(n):
        ang = a + 6.283 * i / n
        t = np.linspace(0, 1, 14)
        aa = ang + np.sin(t * 4) * 0.3
        rad = 0.1 + 0.8 * t
        cv2.polylines(st, [_xf(np.stack([np.cos(aa) * rad, np.sin(aa) * rad], 1), cx, cy, s, 0.0)],
                      False, 1.0, 1, cv2.LINE_AA)


# ── 17 new DEEP composers (distinct drawer + baked palette + field) ──
def motif_anglerfish(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_lure, {"base": (6, 6, 13), "creature": (50, 80, 150), "accent": (255, 205, 80), "field": (16, 34, 70)}, _caustic_field, 15, 88, 124, size_mul)


def motif_nautilus(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_spiral, {"base": (8, 12, 16), "creature": (120, 220, 210), "accent": (255, 246, 220), "field": (20, 70, 70)}, _caustic_field, 16, 84, 116, size_mul)


def motif_leviathan(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_ribs, {"base": (7, 10, 16), "creature": (150, 180, 210), "accent": (220, 235, 255), "field": (30, 50, 78)}, _ink_field, 9, 90, 126, size_mul)


def motif_vents(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_vent, {"base": (10, 5, 4), "creature": (255, 110, 30), "accent": (255, 230, 120), "field": (70, 26, 12)}, _ink_field, 9, 84, 116, size_mul,
                    field_g=(0.5, 1.7, 0.22), cr_g=(1.1, 2.0, 0.5))


def motif_siren(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_ripple, {"base": (10, 6, 18), "creature": (200, 110, 240), "accent": (255, 170, 210), "field": (50, 26, 80)}, _caustic_field, 15, 80, 112, size_mul)


def motif_bubble_veil(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_bubbles, {"base": (5, 11, 16), "creature": (130, 220, 240), "accent": (240, 255, 255), "field": (24, 70, 84)}, _caustic_field, 17, 90, 126, size_mul)


def motif_deep_coral(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_dendrite, {"base": (12, 6, 14), "creature": (255, 90, 150), "accent": (120, 240, 220), "field": (60, 24, 60)}, _caustic_field, 14, 80, 110, size_mul)


def motif_manta(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_wing, {"base": (5, 8, 16), "creature": (90, 130, 200), "accent": (210, 225, 255), "field": (22, 40, 74)}, _ink_field, 10, 80, 110, size_mul)


def motif_trench(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_crack, {"base": (3, 5, 9), "creature": (60, 170, 255), "accent": (180, 230, 255), "field": (10, 36, 64)}, _ink_field, 9, 88, 120, size_mul,
                    field_g=(0.42, 1.7, 0.18))


def motif_sea_serpent(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_serpent, {"base": (5, 12, 10), "creature": (60, 210, 130), "accent": (190, 255, 200), "field": (16, 64, 46)}, _caustic_field, 14, 82, 112, size_mul)


def motif_urchin(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_urchin, {"base": (9, 5, 14), "creature": (150, 90, 230), "accent": (220, 180, 255), "field": (44, 22, 70)}, _ink_field, 9, 96, 130, size_mul)


def motif_lanternfish(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_lantern, {"base": (4, 7, 16), "creature": (70, 110, 180), "accent": (255, 215, 110), "field": (18, 36, 72)}, _caustic_field, 18, 100, 140, size_mul)


def motif_thicket(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_thicket, {"base": (5, 11, 12), "creature": (40, 200, 160), "accent": (170, 255, 220), "field": (16, 60, 52)}, _caustic_field, 14, 84, 114, size_mul)


def motif_bloom(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_bloom, {"base": (6, 9, 18), "creature": (90, 220, 240), "accent": (255, 200, 230), "field": (24, 62, 82)}, _caustic_field, 16, 96, 132, size_mul)


def motif_gulper(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_maw, {"base": (4, 7, 5), "creature": (120, 220, 90), "accent": (210, 255, 150), "field": (24, 54, 22)}, _ink_field, 9, 80, 110, size_mul,
                    field_g=(0.42, 1.7, 0.18))


def motif_brine_pool(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_pool, {"base": (10, 11, 7), "creature": (180, 200, 120), "accent": (230, 245, 190), "field": (52, 56, 28)}, _caustic_field, 15, 80, 110, size_mul)


def motif_anemone(h, w, seed, size_mul=1.6):
    return _compose(h, w, seed, _el_anemone, {"base": (12, 6, 12), "creature": (255, 120, 190), "accent": (130, 245, 235), "field": (58, 26, 56)}, _caustic_field, 15, 86, 118, size_mul)


DEEP_MOTIFS = {
    "kraken": motif_kraken,
    "electric_eel": motif_electric_eel,
    "jellyfish": motif_jellyfish,
    "anglerfish": motif_anglerfish,
    "nautilus": motif_nautilus,
    "leviathan_ribs": motif_leviathan,
    "hydrothermal_vents": motif_vents,
    "siren_song": motif_siren,
    "bubble_veil": motif_bubble_veil,
    "deep_coral": motif_deep_coral,
    "manta_drift": motif_manta,
    "trench_cracks": motif_trench,
    "sea_serpent": motif_sea_serpent,
    "urchin_spines": motif_urchin,
    "lanternfish": motif_lanternfish,
    "tentacle_thicket": motif_thicket,
    "bioluminescent_bloom": motif_bloom,
    "gulper_maw": motif_gulper,
    "brine_pool": motif_brine_pool,
    "anemone_crown": motif_anemone,
}


def render_motif(name: str, h: int = 2048, w: int = 2048, seed: int = 1) -> np.ndarray:
    rgb = DEEP_MOTIFS[name](h, w, seed)
    return np.clip(np.round(rgb * 255.0), 0, 255).astype(np.uint8)
