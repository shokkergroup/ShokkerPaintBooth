"""SPB_RATE_10 Codex heartbeat loop 7 final hidden-pending rebuilds.

SPB-105 / SPB-RATE10 / 2026-05-27-codex-loop7: finishes still hidden pending
owner-rated REBUILD after loop6. These recipes keep the marks fine for a
2048x2048 car canvas, use several spec shade tiers, and replace broad/noisy
ideas with named finish language.
"""
from __future__ import annotations

import math

import numpy as np

from ..spec_patterns import _CV2_OK, _cv2, _normalize, multi_scale_noise
from .rate10_codex_batch import _dot_noise, _finish, _line_distance, _scale, _star
from .rate10_codex_loop2 import _base, _machined, _occult, _pins, _prism


def _grime_tracks(shape, seed, name):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 71000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.18, 0.20, 0.16, 0.12)
    if _CV2_OK:
        for _ in range(int(np.clip(3100 * (h * w / (2048 * 2048)), 520, 3100))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            ln = float(rng.uniform(7, 26) * sc)
            ang = float(rng.normal(0.12, 0.22))
            x2 = int(np.clip(cx + math.cos(ang) * ln, 0, w - 1))
            y2 = int(np.clip(cy + math.sin(ang) * ln, 0, h - 1))
            tier = float(rng.choice([0.14, 0.22, 0.34, 0.48, 0.62, 0.78]))
            _cv2.line(M, (cx, cy), (x2, y2), tier * 0.72, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy), (x2, y2), tier * 0.68, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (x2, y2), tier * 0.40, 1, lineType=_cv2.LINE_AA)
        for _ in range(int(np.clip(1300 * (h * w / (2048 * 2048)), 240, 1300))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(1.5, 4.6) * sc))
            _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.12, 0.74)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), rr, float(rng.uniform(0.18, 0.54)), -1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2600, "mixed")
    return _finish(name, M, R, CC, 1.0)


def _fine_brush(shape, seed, name):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 72000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.18, 0.12, 0.24, 0.12)
    if _CV2_OK:
        for _ in range(int(np.clip(2600 * (h * w / (2048 * 2048)), 420, 2600))):
            x = int(rng.integers(0, w)); y = int(rng.integers(0, h))
            tier = float(rng.choice([0.22, 0.34, 0.46, 0.58, 0.72, 0.88]))
            last = (x, y)
            for k in range(int(rng.integers(3, 7))):
                ln = float(rng.uniform(4, 10) * sc)
                ang = float(rng.normal(-0.10, 0.46) + math.sin(k * 0.9) * 0.22)
                x = int(np.clip(x + math.cos(ang) * ln, 0, w - 1))
                y = int(np.clip(y + math.sin(ang) * ln, 0, h - 1))
                _cv2.line(M, last, (x, y), tier, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, last, (x, y), tier * 0.18, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, last, (x, y), min(0.98, tier + 0.04), 1, lineType=_cv2.LINE_AA)
                last = (x, y)
    _dot_noise(M, R, CC, rng, 3200, 0.026)
    return _finish(name, M, R, CC, 1.0)


def _retro_wave(shape, seed, name):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(int(seed) + 73000 + len(name))
    sc = _scale(shape)
    warp = _normalize(multi_scale_noise(shape, [5, 11, 25], [0.44, 0.34, 0.22], int(seed) + 19))
    phase = (yy + np.sin(xx / max(1.0, 35 * sc)) * 14 * sc + (warp - 0.5) * 10 * sc) * (2 * math.pi / max(1.0, 12.0 * sc))
    micro = (xx * 0.36 - yy * 0.08) * (2 * math.pi / max(1.0, 7.0 * sc))
    M = np.clip(0.17 + (np.sin(phase) + 1) * 0.16 + (np.sin(micro) + 1) * 0.05, 0, 1).astype(np.float32)
    R = np.clip(0.10 + (np.sin(phase + 2.1) + 1) * 0.07 + (np.sin(micro + 1.4) + 1) * 0.04, 0, 1).astype(np.float32)
    CC = np.clip(0.25 + (np.sin(phase + 4.0) + 1) * 0.21 + (np.sin(micro + 3.1) + 1) * 0.05, 0, 1).astype(np.float32)
    if _CV2_OK:
        for y in range(0, h, max(6, int(14 * sc))):
            wob = int(math.sin(y / max(1.0, 48 * sc)) * 11 * sc)
            tier = float(rng.uniform(0.42, 0.90))
            _cv2.line(M, (0, y), (w - 1, int(np.clip(y + wob, 0, h - 1))), tier, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (0, y), (w - 1, int(np.clip(y + wob, 0, h - 1))), tier * 0.16, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (0, y), (w - 1, int(np.clip(y + wob, 0, h - 1))), min(0.98, tier + 0.04), 1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2600, "glass")
    return _finish(name, M, R, CC, 1.0)


def _forged_carbon(shape, seed, name):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 74000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.16, 0.12, 0.28, 0.08)
    if _CV2_OK:
        for _ in range(int(np.clip(3600 * (h * w / (2048 * 2048)), 560, 3600))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(2, int(rng.uniform(4, 12) * sc))
            sides = int(rng.integers(3, 7))
            pts = _star(cx, cy, rr, max(1, rr // 3), sides, rng.uniform(0, math.pi))
            tier = float(rng.choice([0.18, 0.26, 0.38, 0.52, 0.66, 0.82, 0.94]))
            _cv2.fillPoly(M, [pts], tier * 0.72, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [pts], tier * 0.22, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts], min(0.98, tier * 0.88 + 0.06), lineType=_cv2.LINE_AA)
            if rng.random() < 0.35:
                _cv2.polylines(M, [pts], True, min(0.98, tier + 0.08), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, min(0.98, tier + 0.12), 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 4600, 0.024)
    return _finish(name, M, R, CC, 1.0)


def _scale_skin(shape, seed, name, mode="snake"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 75000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.18, 0.12, 0.30, 0.10)
    if _CV2_OK:
        step = max(8, int((22 if mode == "snake" else 26) * sc))
        for row, y in enumerate(range(-step, h + step, step)):
            off = step // 2 if row % 2 else 0
            for x in range(-step, w + step, step):
                cx = x + off
                if mode == "pangolin":
                    pts = np.array([[cx, y - step // 2], [cx + step // 2, y], [cx + step // 4, y + step // 2], [cx - step // 4, y + step // 2], [cx - step // 2, y]], dtype=np.int32)
                else:
                    pts = np.array([[cx, y - step // 2], [cx + step // 2, y], [cx, y + step // 2], [cx - step // 2, y]], dtype=np.int32)
                tier = float(rng.choice([0.24, 0.36, 0.48, 0.62, 0.76, 0.92]))
                _cv2.fillPoly(M, [pts], tier * 0.48, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts], tier * 0.20, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], tier * 0.62, lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [pts], True, min(0.98, tier + 0.06), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [pts], True, tier * 0.28, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, min(0.98, tier + 0.10), 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 4200, 0.025)
    return _finish(name, M, R, CC, 1.0)


def _hellfire(shape, seed, name):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 76000 + len(name))
    M, R, CC = _base(shape, int(seed), 0.28, 0.08, 0.13, 0.12)
    if _CV2_OK:
        sc = _scale(shape)
        for _ in range(int(np.clip(2600 * (h * w / (2048 * 2048)), 430, 2600))):
            x = int(rng.integers(0, w)); y = int(rng.integers(0, h))
            tier = float(rng.choice([0.26, 0.38, 0.50, 0.64, 0.80, 0.96]))
            for _seg in range(int(rng.integers(2, 6))):
                ln = float(rng.uniform(5, 16) * sc)
                ang = float(rng.choice([math.pi / 2, math.pi / 3, 2 * math.pi / 3]) + rng.normal(0, 0.28))
                x2 = int(np.clip(x + math.cos(ang) * ln, 0, w - 1))
                y2 = int(np.clip(y - abs(math.sin(ang) * ln), 0, h - 1))
                _cv2.line(M, (x, y), (x2, y2), tier, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x, y), (x2, y2), tier * 0.12, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x, y), (x2, y2), tier * 0.40, 1, lineType=_cv2.LINE_AA)
                x, y = x2, y2
    _pins(M, R, CC, rng, 2800, "hot")
    return _finish(name, M, R, CC, 1.0)


def _razor_wire(shape, seed, name):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 77000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.26, 0.21, 0.30, 0.08)
    if _CV2_OK:
        for row in range(22):
            y0 = int((row + 0.5) * h / 22 + rng.uniform(-4, 4) * sc)
            amp = float(rng.uniform(5, 12) * sc)
            period = max(10, int(rng.uniform(22, 36) * sc))
            pts = []
            for x in range(0, w, max(3, int(5 * sc))):
                y = int(np.clip(y0 + math.sin(x / period * 2 * math.pi) * amp, 0, h - 1))
                pts.append((x, y))
            for a, b in zip(pts, pts[1:]):
                tier = float(rng.uniform(0.42, 0.94))
                _cv2.line(M, a, b, tier, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, a, b, tier * 0.60, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, a, b, min(0.98, tier + 0.04), 1, lineType=_cv2.LINE_AA)
            for x, y in pts[::max(2, int(4 * sc))]:
                ln = max(3, int(rng.uniform(4, 9) * sc))
                _cv2.line(M, (x - ln, y - ln), (x + ln, y + ln), 0.94, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x - ln, y + ln), (x + ln, y - ln), 0.96, 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 2400, 0.02)
    return _finish(name, M, R, CC, 1.0)


def _demon_eyes(shape, seed, name):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 78000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.23, 0.06, 0.17, 0.13)
    if _CV2_OK:
        for _ in range(int(np.clip(1650 * (h * w / (2048 * 2048)), 280, 1650))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rx = max(3, int(rng.uniform(5, 13) * sc))
            ry = max(1, int(rng.uniform(2, 5) * sc))
            rot = float(rng.uniform(-28, 28))
            tier = float(rng.choice([0.28, 0.40, 0.54, 0.68, 0.82, 0.96]))
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 0, 360, tier, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rx, ry), rot, 0, 360, tier * 0.08, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, tier * 0.48, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(M, (cx, cy), max(1, int(1.8 * sc)), min(0.98, tier + 0.06), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), max(1, int(1.8 * sc)), min(0.92, tier + 0.02), -1, lineType=_cv2.LINE_AA)
        for _ in range(int(np.clip(1200 * (h * w / (2048 * 2048)), 220, 1200))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            ln = float(rng.uniform(7, 21) * sc)
            ang = float(rng.uniform(0, math.pi))
            x2 = int(np.clip(cx + math.cos(ang) * ln, 0, w - 1))
            y2 = int(np.clip(cy + math.sin(ang) * ln, 0, h - 1))
            _cv2.line(M, (cx, cy), (x2, y2), float(rng.uniform(0.28, 0.78)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (x2, y2), float(rng.uniform(0.22, 0.62)), 1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2600, "hot")
    return _finish(name, M, R, CC, 1.0)


def codex_engine_bay_grime_loop7(shape, seed, sm, **kwargs): return _grime_tracks(shape, seed + 1, "engine_bay_grime")
def codex_brushstroke_bold_loop7(shape, seed, sm, **kwargs): return _fine_brush(shape, seed + 2, "brushstroke_bold")
def codex_abstract_retro_wave_loop7(shape, seed, sm, **kwargs): return _retro_wave(shape, seed + 3, "abstract_retro_wave")
def codex_forged_carbon_chip_loop7(shape, seed, sm, **kwargs): return _forged_carbon(shape, seed + 4, "forged_carbon_chip")
def codex_snake_scale_diamond_loop7(shape, seed, sm, **kwargs): return _scale_skin(shape, seed + 5, "snake_scale_diamond", "snake")
def codex_pangolin_armor_loop7(shape, seed, sm, **kwargs): return _scale_skin(shape, seed + 6, "pangolin_armor", "pangolin")
def codex_hellfire_crackle_loop7(shape, seed, sm, **kwargs): return _hellfire(shape, seed + 7, "hellfire_crackle")
def codex_demon_eye_field_loop7(shape, seed, sm, **kwargs): return _demon_eyes(shape, seed + 8, "demon_eye_field")
def codex_nordic_rune_field_loop7(shape, seed, sm, **kwargs): return _occult(shape, seed + 9, "nordic_rune_field", "frost", 440, 2200)
def codex_razor_wire_coil_loop7(shape, seed, sm, **kwargs): return _razor_wire(shape, seed + 10, "razor_wire_coil")
