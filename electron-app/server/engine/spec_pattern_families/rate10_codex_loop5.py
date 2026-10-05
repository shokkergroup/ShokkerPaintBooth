"""SPB_RATE_10 Codex heartbeat loop 5 final broad spec-overlay rebuilds.

SPB-105 / SPB-RATE10 / 2026-05-27-codex-loop5: owner asked for the remaining
visible unrated cards to be rebuilt with 8-32 px feature language, many spec
shades, and no generic noise. This batch leaves the spec_stone_marble rename as
metadata cleanup and concentrates on rubber, vinyl, predator, voodoo, wet-gloss,
and machined finishes.
"""
from __future__ import annotations

import math

import numpy as np

from ..spec_patterns import _CV2_OK, _cv2, _flat, _normalize, multi_scale_noise
from .rate10_codex_batch import _dot_noise, _finish, _line_distance, _scale, _star
from .rate10_codex_loop2 import _base, _machined, _occult, _pins, _prism, _track
from .rate10_codex_loop3 import _predator
from .rate10_codex_loop4 import _fracture, _industrial, _sponsor


def _stipple(shape, seed, name, mode="dots"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 50500 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.23, 0.19, 0.22, 0.11)
    if _CV2_OK:
        count = int(np.clip(5200 * (h * w / (2048 * 2048)), 700, 5200))
        for _ in range(count):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(1.2, 3.6) * sc))
            tier = float(rng.choice([0.16, 0.25, 0.36, 0.48, 0.62, 0.78, 0.92]))
            if mode == "rust":
                _cv2.circle(M, (cx, cy), rr + 1, min(0.96, tier + 0.06), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), rr, tier * 0.74, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), rr, tier * 0.34, 1, lineType=_cv2.LINE_AA)
            else:
                _cv2.circle(M, (cx, cy), rr, tier, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), rr, tier * rng.uniform(0.18, 0.58), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), rr, tier * rng.uniform(0.28, 0.92), -1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 3200, "mixed")
    return _finish(name, M, R, CC, 1.0)


def _tire(shape, seed, name, mode="transfer"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 51000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.22, 0.22, 0.18, 0.10)
    if _CV2_OK:
        lanes = 24 if mode != "smoke" else 18
        for row in range(lanes):
            y = int((row + 0.5) * h / lanes + rng.uniform(-6, 6) * sc)
            step = max(4, int(rng.uniform(7, 14) * sc))
            for x in range(0, w, step):
                length = float(rng.uniform(7, 23) * sc)
                ang = float(rng.normal(-0.05, 0.13))
                if mode == "smoke":
                    ang += rng.uniform(-0.28, 0.28)
                x2 = int(np.clip(x + math.cos(ang) * length, 0, w - 1))
                y2 = int(np.clip(y + math.sin(ang) * length, 0, h - 1))
                tier = float(rng.uniform(0.12, 0.82))
                _cv2.line(M, (x, y), (x2, y2), tier * 0.55, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x, y), (x2, y2), tier * 0.42, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x, y), (x2, y2), tier * 0.40, 1, lineType=_cv2.LINE_AA)
        if mode == "smoke":
            for _ in range(int(np.clip(900 * (h * w / (2048 * 2048)), 170, 900))):
                cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
                rr = max(2, int(rng.uniform(3, 8) * sc))
                _cv2.ellipse(M, (cx, cy), (rr * 2, rr), rng.uniform(-18, 18), 0, 360, float(rng.uniform(0.18, 0.58)), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (rr * 2, rr), rng.uniform(-18, 18), 0, 360, float(rng.uniform(0.22, 0.66)), 1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2200, "mixed")
    return _finish(name, M, R, CC, 1.0)


def _vinyl(shape, seed, name, mode="seam"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 52000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.24, 0.16, 0.32, 0.10)
    if _CV2_OK:
        for _ in range(int(np.clip(1800 * (h * w / (2048 * 2048)), 320, 1800))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            length = float(rng.uniform(7, 22) * sc)
            ang = float(rng.choice([0, math.pi / 4, -math.pi / 4, math.pi / 2]) + rng.normal(0, 0.10))
            x2 = int(np.clip(cx + math.cos(ang) * length, 0, w - 1))
            y2 = int(np.clip(cy + math.sin(ang) * length, 0, h - 1))
            tier = float(rng.uniform(0.34, 0.96))
            _cv2.line(M, (cx, cy), (x2, y2), tier * 0.72, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy), (x2, y2), tier * 0.30, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (x2, y2), min(0.98, tier + 0.05), 1, lineType=_cv2.LINE_AA)
        if mode == "bubble":
            for _ in range(int(np.clip(360 * (h * w / (2048 * 2048)), 80, 360))):
                cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
                rr = max(2, int(rng.uniform(3, 9) * sc))
                _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.30, 0.80)), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.55, 0.98)), 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 4200, 0.03)
    return _finish(name, M, R, CC, 1.0)


def _tiger_stripes(shape, seed, name):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(int(seed) + 52500 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.19, 0.12, 0.31, 0.10)
    warp = _normalize(multi_scale_noise(shape, [5, 11, 23], [0.46, 0.33, 0.21], int(seed) + 19))
    phase = (xx * 0.82 + yy * 0.10 + (warp - 0.5) * 20.0 * sc) / max(1.0, 17.0 * sc)
    stripe = np.maximum(0.0, 1.0 - np.abs((phase % 1.0) - 0.5) * 5.2)
    micro = _line_distance(xx * 0.28 - yy * 0.66, 9.0 * sc, 0.60 * sc, seed * 0.31)
    M = np.clip(M + stripe * 0.46 + micro * 0.13, 0, 1)
    R = np.clip(R + stripe * 0.18 + micro * 0.04, 0, 1)
    CC = np.clip(CC + stripe * 0.34 + micro * 0.15, 0, 1)
    if _CV2_OK:
        for _ in range(int(np.clip(650 * (h * w / (2048 * 2048)), 110, 650))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            ln = float(rng.uniform(8, 26) * sc)
            ang = float(-0.25 + rng.normal(0, 0.24))
            x2 = int(np.clip(cx + math.cos(ang) * ln, 0, w - 1))
            y2 = int(np.clip(cy + math.sin(ang) * ln, 0, h - 1))
            tier = float(rng.uniform(0.34, 0.92))
            _cv2.line(M, (cx, cy), (x2, y2), tier, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy), (x2, y2), tier * 0.18, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (x2, y2), min(0.98, tier + 0.04), 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 4800, 0.028)
    return _finish(name, M, R, CC, 1.0)


def _voodoo_relic(shape, seed, name, bones=False):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 53000 + len(name))
    M = _occult(shape, seed, name, "violet", 460 if not bones else 280, 2700)
    arr = np.array(M, copy=True)
    if _CV2_OK:
        sc = _scale(shape)
        Mch, Rch, Cch = arr[..., 0].copy(), arr[..., 1].copy(), arr[..., 2].copy()
        for _ in range(int(np.clip(260 * (h * w / (2048 * 2048)), 80, 260))):
            cx = int(rng.integers(10, w - 10)); cy = int(rng.integers(10, h - 10))
            rr = max(3, int(rng.uniform(5, 12) * sc))
            pts = _star(cx, cy, rr, max(1, rr // 2), 5, rng.uniform(0, math.pi))
            _cv2.polylines(Mch, [pts], True, 0.92, 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(Rch, [pts], True, 0.22, 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(Cch, [pts], True, 0.98, 1, lineType=_cv2.LINE_AA)
        if bones:
            for _ in range(int(np.clip(420 * (h * w / (2048 * 2048)), 120, 420))):
                cx = int(rng.integers(8, w - 8)); cy = int(rng.integers(8, h - 8))
                ln = float(rng.uniform(8, 24) * sc); ang = float(rng.uniform(0, math.pi))
                x2 = int(np.clip(cx + math.cos(ang) * ln, 0, w - 1))
                y2 = int(np.clip(cy + math.sin(ang) * ln, 0, h - 1))
                _cv2.line(Mch, (cx, cy), (x2, y2), float(rng.uniform(0.48, 0.94)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(Rch, (cx, cy), (x2, y2), float(rng.uniform(0.10, 0.34)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(Cch, (cx, cy), (x2, y2), float(rng.uniform(0.42, 0.96)), 1, lineType=_cv2.LINE_AA)
                for px, py in ((cx, cy), (x2, y2)):
                    rr = max(1, int(rng.uniform(2, 4) * sc))
                    _cv2.circle(Mch, (px, py), rr, 0.88, 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(Cch, (px, py), rr, 0.96, 1, lineType=_cv2.LINE_AA)
        arr[..., 0], arr[..., 1], arr[..., 2] = Mch, Rch, Cch
    return _finish(name, arr[..., 0], arr[..., 1], arr[..., 2], 1.0)


def _starfield(shape, seed, name):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 53500 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.17, 0.12, 0.28, 0.09)
    if _CV2_OK:
        for _ in range(int(np.clip(4600 * (h * w / (2048 * 2048)), 680, 4600))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            tier = float(rng.choice([0.30, 0.42, 0.55, 0.68, 0.82, 0.96]))
            if rng.random() < 0.30:
                ln = max(2, int(rng.uniform(3, 8) * sc))
                _cv2.line(M, (max(0, cx - ln), cy), (min(w - 1, cx + ln), cy), tier, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx, max(0, cy - ln)), (cx, min(h - 1, cy + ln)), min(0.98, tier + 0.02), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), 1, tier * 0.22, -1, lineType=_cv2.LINE_AA)
            else:
                M[cy, cx] = tier
                R[cy, cx] = tier * rng.uniform(0.12, 0.44)
                CC[cy, cx] = min(0.98, tier + rng.uniform(-0.04, 0.10))
        for _ in range(int(np.clip(170 * (h * w / (2048 * 2048)), 50, 170))):
            cx = int(rng.integers(12, w - 12)); cy = int(rng.integers(12, h - 12))
            rr = max(3, int(rng.uniform(5, 11) * sc))
            start = float(rng.uniform(0, 360)); end = start + float(rng.uniform(24, 58))
            _cv2.ellipse(M, (cx, cy), (rr * 2, rr), rng.uniform(0, 180), start, end, float(rng.uniform(0.40, 0.86)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rr * 2, rr), rng.uniform(0, 180), start, end, float(rng.uniform(0.44, 0.94)), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, 1.0)


def _wave_lacquer(shape, seed, name):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(int(seed) + 53700 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.18, 0.13, 0.34, 0.10)
    ripple = _line_distance(xx * 0.42 + yy * 0.58, 13.0 * sc, 0.72 * sc, seed)
    cross = _line_distance(xx * 0.66 - yy * 0.21, 21.0 * sc, 0.58 * sc, seed * 0.73)
    M = np.clip(M + ripple * 0.32 + cross * 0.10, 0, 1)
    R = np.clip(R + ripple * 0.10 + cross * 0.04, 0, 1)
    CC = np.clip(CC + ripple * 0.42 + cross * 0.18, 0, 1)
    if _CV2_OK:
        for _ in range(int(np.clip(520 * (h * w / (2048 * 2048)), 100, 520))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(3, int(rng.uniform(4, 10) * sc))
            _cv2.ellipse(M, (cx, cy), (rr * 2, rr), rng.uniform(-35, 35), 0, 360, float(rng.uniform(0.30, 0.72)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rr * 2, rr), rng.uniform(-35, 35), 0, 360, float(rng.uniform(0.56, 0.98)), 1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2400, "glass")
    return _finish(name, M, R, CC, 1.0)


def _wet_gloss(shape, seed, name):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 54000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.18, 0.12, 0.38, 0.13)
    if _CV2_OK:
        for _ in range(int(np.clip(2100 * (h * w / (2048 * 2048)), 360, 2100))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(2, int(rng.uniform(2.5, 8.5) * sc))
            tier = float(rng.uniform(0.36, 0.96))
            _cv2.ellipse(M, (cx, cy), (rr, max(1, rr // 2)), rng.uniform(-20, 20), 0, 360, tier * 0.62, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rr, max(1, rr // 2)), rng.uniform(-20, 20), 0, 360, tier * 0.16, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rr, max(1, rr // 2)), rng.uniform(-20, 20), 0, 360, min(0.98, tier + 0.04), 1, lineType=_cv2.LINE_AA)
        for _ in range(int(np.clip(460 * (h * w / (2048 * 2048)), 90, 460))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            ln = float(rng.uniform(9, 28) * sc)
            x2 = int(np.clip(cx + ln, 0, w - 1)); y2 = int(np.clip(cy + rng.uniform(-2, 2) * sc, 0, h - 1))
            _cv2.line(M, (cx, cy), (x2, y2), float(rng.uniform(0.32, 0.74)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (x2, y2), float(rng.uniform(0.62, 0.98)), 1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2800, "glass")
    return _finish(name, M, R, CC, 1.0)


def codex_stardust_fine(shape, seed, sm, **kwargs): return _starfield(shape, seed + 1, "stardust_fine")
def codex_sticker_bubble_film(shape, seed, sm, **kwargs): return _vinyl(shape, seed + 2, "sticker_bubble_film", "bubble")
def codex_stippled_dots_fine(shape, seed, sm, **kwargs): return _stipple(shape, seed + 3, "stippled_dots_fine", "dots")
def codex_suspension_rust_ring(shape, seed, sm, **kwargs): return _stipple(shape, seed + 4, "suspension_rust_ring", "rust")
def codex_tarmac_grit_embed(shape, seed, sm, **kwargs): return _track(shape, seed + 5, "tarmac_grit_embed", "grit")
def codex_tiger_stripe_field(shape, seed, sm, **kwargs): return _tiger_stripes(shape, seed + 6, "tiger_stripe_field")
def codex_tire_rubber_transfer(shape, seed, sm, **kwargs): return _tire(shape, seed + 7, "tire_rubber_transfer", "transfer")
def codex_tire_smoke_residue(shape, seed, sm, **kwargs): return _tire(shape, seed + 8, "tire_smoke_residue", "smoke")
def codex_tire_smoke_streaks(shape, seed, sm, **kwargs): return _tire(shape, seed + 9, "tire_smoke_streaks", "smoke")
def codex_track_grime(shape, seed, sm, **kwargs): return _track(shape, seed + 10, "track_grime", "grit")
def codex_undercarriage_spray(shape, seed, sm, **kwargs): return _fracture(shape, seed + 11, "undercarriage_spray", "earth")
def codex_vinyl_seam(shape, seed, sm, **kwargs): return _vinyl(shape, seed + 12, "vinyl_seam", "seam")
def codex_vinyl_wrap_texture(shape, seed, sm, **kwargs): return _vinyl(shape, seed + 13, "vinyl_wrap_texture", "bubble")
def codex_viper_pit_hex(shape, seed, sm, **kwargs): return _predator(shape, seed + 14, "viper_pit_hex", "denticle")
def codex_voodoo_bone_fetish_loop5(shape, seed, sm, **kwargs): return _voodoo_relic(shape, seed + 15, "voodoo_bone_fetish", True)
def codex_voodoo_sigil_field_loop5(shape, seed, sm, **kwargs): return _voodoo_relic(shape, seed + 16, "voodoo_sigil_field", False)
def codex_wave_ripple(shape, seed, sm, **kwargs): return _wave_lacquer(shape, seed + 17, "wave_ripple")
def codex_wax_streak_polish(shape, seed, sm, **kwargs): return _machined(shape, seed + 18, "wax_streak_polish", "straight")
def codex_wet_track_gloss(shape, seed, sm, **kwargs): return _wet_gloss(shape, seed + 19, "wet_track_gloss")
def codex_wire_brushed_coarse(shape, seed, sm, **kwargs): return _machined(shape, seed + 20, "wire_brushed_coarse", "straight")
