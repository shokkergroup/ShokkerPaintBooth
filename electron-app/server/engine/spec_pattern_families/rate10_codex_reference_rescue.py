"""SPB_RATE_10 reference-driven rescue rebuilds.

SPB-105 / SPB-RATE10 / 2026-05-27-reference-rescue: owner called out weak,
repeating, lazy-looking rebuilds and supplied reference cards showing the
desired diversity: viper hex armor, luminous wave rings, occult ritual
ornament, spirit-board glamour, terrain strata, stardust, stress fractures,
snake armor, liquid metal, and Fresnel/engine-turn optics.

These overrides intentionally avoid one shared "noise with lines" grammar.
Each renderer has a separate silhouette system, uses fine 8-32 px marks on a
2048 canvas, and uses many M/R/CC shade tiers.
"""
from __future__ import annotations

import math

import numpy as np

from scipy.spatial import cKDTree

from ..spec_patterns import _CV2_OK, _cv2, _normalize, _spb_fast_smooth_noise, multi_scale_noise
from .rate10_codex_batch import _base, _dot_noise, _finish, _scale, _star


def _count(shape, per_2048, min_count=80):
    h, w = shape
    return int(np.clip(per_2048 * h * w / (2048 * 2048), min_count, per_2048))


def _safe_sm(sm):
    return 1.0 if sm is None else sm


def _polyline(img, pts, value, thickness=1):
    if len(pts) > 1:
        _cv2.polylines(img, [np.asarray(pts, dtype=np.int32)], False, float(value), thickness, lineType=_cv2.LINE_AA)


def _hex_points(cx, cy, r, rot=math.pi / 6):
    return np.asarray(
        [[int(cx + math.cos(rot + i * math.tau / 6) * r), int(cy + math.sin(rot + i * math.tau / 6) * r)] for i in range(6)],
        dtype=np.int32,
    )


def _draw_glint(M, R, CC, cx, cy, r, palette):
    for a in (0, math.pi / 2, math.pi / 4, -math.pi / 4):
        x1 = int(cx - math.cos(a) * r)
        y1 = int(cy - math.sin(a) * r)
        x2 = int(cx + math.cos(a) * r)
        y2 = int(cy + math.sin(a) * r)
        _cv2.line(M, (x1, y1), (x2, y2), palette[0], 1, lineType=_cv2.LINE_AA)
        _cv2.line(R, (x1, y1), (x2, y2), palette[1], 1, lineType=_cv2.LINE_AA)
        _cv2.line(CC, (x1, y1), (x2, y2), palette[2], 1, lineType=_cv2.LINE_AA)


def _viper_pit_hex(shape, seed, sm, name="viper_pit_hex_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81001)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.16, 0.20, 0.12, 0.08)
    if _CV2_OK:
        pitch = max(18, int(54 * sc))
        for row, y in enumerate(range(-pitch, h + pitch, pitch)):
            off = pitch // 2 if row % 2 else 0
            for x in range(-pitch, w + pitch, pitch):
                cx = x + off
                pts = _hex_points(cx, y, int(20 * sc), math.pi / 6)
                tier = float(rng.choice([0.24, 0.34, 0.46, 0.58, 0.72, 0.86, 0.96]))
                _cv2.polylines(M, [pts], True, min(0.98, tier + 0.08), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [pts], True, min(0.98, tier * 0.92), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, tier * 0.38, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.24:
                    _cv2.fillPoly(R, [pts], tier * 0.22, lineType=_cv2.LINE_AA)
                    _cv2.fillPoly(CC, [pts], tier * 0.12, lineType=_cv2.LINE_AA)
        for band in range(-2, 9):
            pts = []
            x0 = int((band - 2) * w / 5)
            for i in range(90):
                y = int(i * h / 89)
                x = int(x0 + band * 17 * sc + math.sin(i * 0.18 + band) * 80 * sc + y * 0.32)
                if -30 <= x <= w + 30:
                    pts.append((x, y))
            for a, b in zip(pts, pts[1:]):
                _cv2.line(M, a, b, 0.78, 2, lineType=_cv2.LINE_AA)
                _cv2.line(R, a, b, 0.92, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, a, b, 0.26, 1, lineType=_cv2.LINE_AA)
            for x, y in pts[8::14]:
                rx, ry = max(5, int(13 * sc)), max(2, int(5 * sc))
                _cv2.ellipse(M, (x, y), (rx, ry), -18, 0, 360, 0.90, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (x, y), (rx, ry), -18, 0, 360, 0.96, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (x, y), max(1, int(2.2 * sc)), 0.82, -1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 1250, 0.035)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _wave_pearl_ripple(shape, seed, sm, name="wave_pearl_ripple_rescue"):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(int(seed) + 81002)
    sc = _scale(shape)
    flow = _normalize(multi_scale_noise(shape, [3, 8, 19], [0.42, 0.36, 0.22], int(seed) + 44))
    M = (0.12 + 0.18 * flow).astype(np.float32)
    R = (0.34 + 0.28 * _normalize(np.sin(xx * 0.010 + flow * 4.4) + np.sin(yy * 0.013))).astype(np.float32)
    CC = (0.42 + 0.34 * _normalize(np.cos(xx * 0.009 - yy * 0.012 + flow * 6.0))).astype(np.float32)
    if _CV2_OK:
        centers = [(int(rng.integers(0, w)), int(rng.integers(0, h))) for _ in range(18)]
        for cx, cy in centers:
            for rr in range(max(7, int(14 * sc)), max(45, int(130 * sc)), max(5, int(9 * sc))):
                val = float(0.30 + 0.65 * (1.0 - rr / max(130 * sc, 1)))
                _cv2.ellipse(M, (cx, cy), (rr, max(4, int(rr * 0.55))), rng.uniform(-18, 18), 0, 360, val * 0.55, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rr, max(4, int(rr * 0.55))), rng.uniform(-18, 18), 0, 360, val * 0.86, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (rr, max(4, int(rr * 0.55))), rng.uniform(-18, 18), 0, 360, min(0.98, val + 0.12), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(M, (cx, cy), max(3, int(7 * sc)), 0.86, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), max(4, int(9 * sc)), 0.96, 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 900, 150)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(2, 6) * sc))
            _cv2.circle(R, (cx, cy), rr, float(rng.uniform(0.70, 0.98)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.78, 0.99)), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _samhain_ritual(shape, seed, sm, name="samhain_ritual_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81003)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.22, 0.08, 0.07, 0.09)
    if _CV2_OK:
        pitch = max(80, int(260 * sc))
        for y in range(-pitch // 2, h + pitch, pitch):
            for x in range(-pitch // 2, w + pitch, pitch):
                cx = int(x + pitch * 0.5)
                cy = int(y + pitch * 0.5)
                for rr in (36, 54, 75):
                    r = max(8, int(rr * sc))
                    _cv2.circle(M, (cx, cy), r, 0.80, 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(R, (cx, cy), r, 0.42, 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (cx, cy), r, 0.14, 1, lineType=_cv2.LINE_AA)
                star = _star(cx, cy, max(8, int(48 * sc)), max(3, int(17 * sc)), 6, -math.pi / 2)
                _cv2.polylines(M, [star], True, 0.92, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [star], True, 0.44, 1, lineType=_cv2.LINE_AA)
                for dx in (-58, 58):
                    bx = int(cx + dx * sc)
                    _cv2.rectangle(M, (bx - 3, cy - 27), (bx + 3, cy + 25), 0.70, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, (bx, cy - 34), (bx, cy - 46), 0.94, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(M, (bx - 4, cy - 38), (bx, cy - 50), 0.98, 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 1800, 250)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            a = float(rng.uniform(0, math.tau))
            ln = max(4, int(rng.uniform(9, 22) * sc))
            _cv2.line(M, (cx, cy), (int(cx + math.cos(a) * ln), int(cy + math.sin(a) * ln)), rng.uniform(0.42, 0.86), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy), (int(cx + math.cos(a) * ln), int(cy + math.sin(a) * ln)), rng.uniform(0.18, 0.62), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _ouija_mystic(shape, seed, sm, name="ouija_mystic_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81004)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.20, 0.16, 0.18, 0.07)
    if _CV2_OK:
        pitch_x, pitch_y = max(90, int(300 * sc)), max(85, int(270 * sc))
        for y in range(-pitch_y, h + pitch_y, pitch_y):
            for x in range(-pitch_x, w + pitch_x, pitch_x):
                cx, cy = x + pitch_x // 2, y + pitch_y // 2
                pts = np.asarray([[cx, cy - int(72 * sc)], [cx + int(54 * sc), cy - int(18 * sc)], [cx + int(26 * sc), cy + int(70 * sc)], [cx, cy + int(54 * sc)], [cx - int(26 * sc), cy + int(70 * sc)], [cx - int(54 * sc), cy - int(18 * sc)]], dtype=np.int32)
                _cv2.polylines(M, [pts], True, 0.84, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [pts], True, 0.66, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, 0.34, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (cx, cy - int(17 * sc)), max(8, int(20 * sc)), 0.86, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy - int(17 * sc)), max(5, int(12 * sc)), 0.82, 1, lineType=_cv2.LINE_AA)
                for k in range(8):
                    a = k * math.tau / 8
                    x1 = int(cx + math.cos(a) * 30 * sc)
                    y1 = int(cy + math.sin(a) * 30 * sc)
                    x2 = int(cx + math.cos(a) * 72 * sc)
                    y2 = int(cy + math.sin(a) * 72 * sc)
                    _cv2.line(M, (x1, y1), (x2, y2), 0.72, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, (x1, y1), (x2, y2), 0.40, 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 2200, 300)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rr = max(2, int(rng.uniform(3, 8) * sc))
            _draw_glint(M, R, CC, cx, cy, rr, (rng.uniform(0.50, 0.96), rng.uniform(0.36, 0.74), rng.uniform(0.28, 0.78)))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _terrain_erosion(shape, seed, sm, name="terrain_erosion_rescue"):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(int(seed) + 81005)
    sc = _scale(shape)
    warp = _normalize(multi_scale_noise(shape, [2.5, 7, 18], [0.44, 0.34, 0.22], int(seed) + 74))
    strata = np.sin((yy * 0.030 + np.sin(xx * 0.006) * 3.0 + warp * 5.5))
    M = (0.24 + 0.36 * _normalize(strata)).astype(np.float32)
    R = (0.20 + 0.30 * _normalize(np.sin(yy * 0.025 + warp * 7.0 + 2.2))).astype(np.float32)
    CC = (0.14 + 0.22 * _normalize(np.cos(yy * 0.035 - xx * 0.004 + warp * 6.3))).astype(np.float32)
    if _CV2_OK:
        for k in range(46):
            pts = []
            y0 = int((k - 4) * h / 38)
            for i in range(0, w, max(5, int(8 * sc))):
                y = int(y0 + math.sin(i * 0.010 + k) * 34 * sc + math.sin(i * 0.031 + k * 1.7) * 9 * sc)
                pts.append((i, np.clip(y, 0, h - 1)))
            tier = float(rng.choice([0.24, 0.34, 0.44, 0.56, 0.70, 0.84]))
            _polyline(M, pts, tier, 1)
            _polyline(R, [(x, int(y + 2 * sc)) for x, y in pts], tier * 0.56, 1)
            _polyline(CC, [(x, int(y - 2 * sc)) for x, y in pts], tier * 0.32, 1)
        for _ in range(_count(shape, 1700, 250)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(1, 4) * sc))
            _cv2.circle(M, (cx, cy), rr, rng.uniform(0.36, 0.88), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rr, rng.uniform(0.10, 0.36), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _stardust_fine(shape, seed, sm, name="stardust_fine_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81006)
    M, R, CC = _base(shape, int(seed), 0.10, 0.10, 0.24, 0.11)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(34):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r0 = rng.uniform(10, 34) * sc
            pts = []
            for i in range(190):
                a = i * 0.24
                rr = r0 + i * 0.42 * sc
                pts.append((int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr)))
            _polyline(M, pts, rng.uniform(0.42, 0.88), 1)
            _polyline(CC, pts, rng.uniform(0.60, 0.98), 1)
        for _ in range(_count(shape, 5200, 700)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            if rng.random() < 0.34:
                _draw_glint(M, R, CC, cx, cy, max(2, int(rng.uniform(3, 9) * sc)), (rng.uniform(0.52, 0.98), rng.uniform(0.30, 0.82), rng.uniform(0.56, 0.99)))
            else:
                _cv2.circle(CC, (cx, cy), 1, rng.uniform(0.42, 0.96), -1, lineType=_cv2.LINE_AA)
                M[cy, cx] = max(M[cy, cx], rng.uniform(0.28, 0.90))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _stress_fractures(shape, seed, sm, name="stress_fractures_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81007)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.24, 0.15, 0.20, 0.08)
    if _CV2_OK:
        for _ in range(_count(shape, 330, 70)):
            cx, cy = int(rng.integers(-30, w + 30)), int(rng.integers(-30, h + 30))
            r = int(rng.uniform(18, 58) * sc)
            sides = int(rng.integers(3, 6))
            pts = np.asarray([[int(cx + math.cos(i * math.tau / sides + rng.uniform(-0.20, 0.20)) * r * rng.uniform(0.65, 1.22)), int(cy + math.sin(i * math.tau / sides + rng.uniform(-0.20, 0.20)) * r * rng.uniform(0.65, 1.22))] for i in range(sides)], dtype=np.int32)
            tier = float(rng.choice([0.22, 0.34, 0.46, 0.62, 0.78, 0.92]))
            _cv2.fillPoly(M, [pts], tier * 0.55, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [pts], tier * 0.26, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts], tier * 0.44, lineType=_cv2.LINE_AA)
            _cv2.polylines(M, [pts], True, min(0.98, tier + 0.08), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [pts], True, min(0.98, tier + 0.12), 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 1550, 260)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            a = rng.choice([0.35, -0.62, 1.2, -1.45]) + rng.normal(0, 0.10)
            ln = rng.uniform(12, 34) * sc
            x2, y2 = int(np.clip(x + math.cos(a) * ln, 0, w - 1)), int(np.clip(y + math.sin(a) * ln, 0, h - 1))
            if rng.random() < 0.55:
                _cv2.line(M, (x, y), (x2, y2), rng.uniform(0.72, 0.98), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x, y), (x2, y2), rng.uniform(0.08, 0.22), 1, lineType=_cv2.LINE_AA)
            else:
                _cv2.line(CC, (x, y), (x2, y2), rng.uniform(0.72, 0.98), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x, y), (x2, y2), rng.uniform(0.38, 0.72), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _liquid_metal(shape, seed, sm, name="liquid_metal_rescue"):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(int(seed) + 81008)
    warp1 = _normalize(multi_scale_noise(shape, [2.2, 5.4, 13], [0.45, 0.34, 0.21], int(seed) + 87))
    warp2 = _normalize(multi_scale_noise(shape, [3.1, 8.3, 17], [0.46, 0.33, 0.21], int(seed) + 93))
    u = xx * 0.020 + warp1 * 8.0 + np.sin(yy * 0.012) * 2.5
    v = yy * 0.018 + warp2 * 8.4 + np.cos(xx * 0.011) * 2.7
    chrome = _normalize(np.sin(u) + np.cos(v) + np.sin(u * 0.55 + v * 0.40))
    M = (0.34 + chrome * 0.58).astype(np.float32)
    R = (0.08 + (1.0 - chrome) * 0.24).astype(np.float32)
    CC = (0.40 + _normalize(np.sin(u * 1.7 - v * 0.9)) * 0.54).astype(np.float32)
    if _CV2_OK:
        sc = _scale(shape)
        for _ in range(_count(shape, 700, 120)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ax, ay = int(rng.uniform(12, 44) * sc), int(rng.uniform(3, 13) * sc)
            rot = rng.uniform(-24, 24)
            _cv2.ellipse(M, (cx, cy), (ax, ay), rot, 0, 360, rng.uniform(0.72, 0.99), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (ax, ay), rot, 0, 360, rng.uniform(0.78, 0.99), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _liquid_chrome_blobs(shape, seed, sm, name="liquid_chrome_blobs_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81034)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [2.4, 6.0, 15], [0.46, 0.34, 0.20], int(seed) + 177))
    ribbons = _normalize(np.sin(xx * 0.040 + np.sin(yy * 0.015) * 5.0 + warp * 7.0))
    M = (0.16 + ribbons * 0.74).astype(np.float32)
    R = (0.07 + (1 - ribbons) * 0.20).astype(np.float32)
    CC = (0.32 + _normalize(np.cos(xx * 0.023 - yy * 0.018 + warp * 8.0)) * 0.62).astype(np.float32)
    if _CV2_OK:
        sc = _scale(shape)
        for _ in range(_count(shape, 430, 80)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ax, ay = max(10, int(rng.uniform(20, 70) * sc)), max(4, int(rng.uniform(7, 22) * sc))
            rot = rng.uniform(-35, 35)
            _cv2.ellipse(M, (cx, cy), (ax, ay), rot, 0, 360, rng.uniform(0.72, 0.99), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (ax, ay), rot, 0, 360, rng.uniform(0.04, 0.16), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (ax, ay), rot, 0, 360, rng.uniform(0.70, 0.99), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx - ax // 4, cy - ay // 3), (max(2, ax // 4), max(1, ay // 3)), rot, 0, 360, 0.98, -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _fresnel_engine_optic(shape, seed, sm, name="fresnel_engine_optic_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81009)
    M, R, CC = _base(shape, int(seed), 0.32, 0.22, 0.34, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(90, int(256 * sc))
        for y in range(-pitch // 2, h + pitch, pitch):
            for x in range(-pitch // 2, w + pitch, pitch):
                cx, cy = x + pitch // 2, y + pitch // 2
                for rr in range(max(7, int(14 * sc)), max(40, int(118 * sc)), max(3, int(6 * sc))):
                    tier = 0.20 + 0.76 * ((rr // max(1, int(6 * sc))) % 7) / 6
                    _cv2.circle(M, (cx, cy), rr, tier, 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(R, (cx, cy), rr, 0.18 + (1 - tier) * 0.72, 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (cx, cy), rr, 0.30 + abs(math.sin(rr * 0.12)) * 0.66, 1, lineType=_cv2.LINE_AA)
                for a in np.linspace(0, math.tau, 18, endpoint=False):
                    x2 = int(cx + math.cos(a) * 104 * sc)
                    y2 = int(cy + math.sin(a) * 104 * sc)
                    _cv2.line(M, (cx, cy), (x2, y2), rng.uniform(0.34, 0.96), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, (cx, cy), (x2, y2), rng.uniform(0.44, 0.98), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _machined_coin_field(shape, seed, sm, name="machined_coin_field_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81010)
    M, R, CC = _base(shape, int(seed), 0.28, 0.20, 0.32, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        step = max(18, int(44 * sc))
        for y in range(step // 2, h, step):
            for x in range(step // 2, w, step):
                cx = int(x + rng.uniform(-4, 4) * sc)
                cy = int(y + rng.uniform(-4, 4) * sc)
                r = max(5, int(rng.uniform(10, 18) * sc))
                for rr in range(3, r, max(2, int(3 * sc))):
                    val = float(rng.choice([0.22, 0.34, 0.48, 0.62, 0.78, 0.94]))
                    _cv2.ellipse(M, (cx, cy), (rr, max(2, int(rr * 0.62))), rng.uniform(0, 180), 0, 360, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(CC, (cx, cy), (rr, max(2, int(rr * 0.62))), rng.uniform(0, 180), 0, 360, min(0.98, val + 0.08), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _circuit_board(shape, seed, sm, name="circuit_board_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81011)
    M, R, CC = _base(shape, int(seed), 0.14, 0.26, 0.18, 0.07)
    sc = _scale(shape)
    if _CV2_OK:
        grid = max(9, int(24 * sc))
        for _ in range(_count(shape, 1700, 260)):
            x, y = int(rng.integers(0, w) // grid * grid), int(rng.integers(0, h) // grid * grid)
            pts = [(x, y)]
            for _seg in range(int(rng.integers(2, 7))):
                if rng.random() < 0.5:
                    x = int(np.clip(x + rng.choice([-1, 1]) * grid * int(rng.integers(1, 4)), 0, w - 1))
                else:
                    y = int(np.clip(y + rng.choice([-1, 1]) * grid * int(rng.integers(1, 4)), 0, h - 1))
                pts.append((x, y))
            val = float(rng.choice([0.28, 0.42, 0.56, 0.70, 0.84, 0.96]))
            _polyline(M, pts, val * 0.62, 1)
            _polyline(R, pts, val, 1)
            _polyline(CC, pts, val * 0.44, 1)
            if rng.random() < 0.55:
                _cv2.circle(R, pts[-1], max(2, int(4 * sc)), min(0.98, val + 0.06), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, pts[-1], max(1, int(2 * sc)), min(0.95, val), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _rune_mandala(shape, seed, sm, name="rune_mandala_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81012)
    M, R, CC = _base(shape, int(seed), 0.18, 0.13, 0.17, 0.08)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(70, int(210 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx, cy = x + pitch // 2, y + pitch // 2
                for a in np.linspace(0, math.tau, 12, endpoint=False):
                    r1, r2 = 18 * sc, 68 * sc
                    p1 = (int(cx + math.cos(a) * r1), int(cy + math.sin(a) * r1))
                    p2 = (int(cx + math.cos(a) * r2), int(cy + math.sin(a) * r2))
                    _cv2.line(M, p1, p2, 0.82, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, p1, p2, 0.42, 1, lineType=_cv2.LINE_AA)
                    tick = (int(cx + math.cos(a + 0.35) * 46 * sc), int(cy + math.sin(a + 0.35) * 46 * sc))
                    _cv2.line(M, p2, tick, 0.74, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (cx, cy), max(8, int(48 * sc)), 0.72, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), max(8, int(48 * sc)), 0.34, 1, lineType=_cv2.LINE_AA)
        _dot_noise(M, R, CC, rng, 900, 0.04)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _razor_coil(shape, seed, sm, name="razor_coil_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81013)
    M, R, CC = _base(shape, int(seed), 0.22, 0.22, 0.25, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for row in range(16):
            y0 = int((row + 0.5) * h / 16)
            pts = []
            for x in range(0, w, max(4, int(7 * sc))):
                y = int(y0 + math.sin(x * 0.028 + row * 0.8) * 22 * sc)
                pts.append((x, y))
            _polyline(M, pts, 0.88, 1)
            _polyline(R, pts, 0.46, 1)
            _polyline(CC, pts, 0.82, 1)
            for x, y in pts[4::8]:
                barb = max(4, int(8 * sc))
                _cv2.line(M, (x - barb, y - barb), (x + barb, y + barb), 0.96, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x - barb, y + barb), (x + barb, y - barb), 0.92, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _clearcoat_bubble_field(shape, seed, sm, name="clearcoat_bubble_field_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81014)
    M, R, CC = _base(shape, int(seed), 0.16, 0.18, 0.32, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 5200, 750)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(2, int(rng.uniform(4, 18) * sc))
            val = float(rng.choice([0.24, 0.36, 0.50, 0.64, 0.80, 0.96]))
            _cv2.circle(CC, (cx, cy), r, val, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), max(1, r - 1), val * 0.18, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.35:
                _cv2.circle(M, (cx - r // 3, cy - r // 3), 1, min(0.98, val + 0.08), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _masking_tape_maze(shape, seed, sm, name="masking_tape_maze_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81015)
    M, R, CC = _base(shape, int(seed), 0.24, 0.18, 0.16, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        step = max(11, int(28 * sc))
        for y in range(0, h, step):
            for x in range(0, w, step):
                if rng.random() < 0.58:
                    val = float(rng.choice([0.26, 0.38, 0.52, 0.68, 0.84]))
                    if rng.random() < 0.5:
                        p1, p2 = (x, y), (min(w - 1, x + step), y)
                    else:
                        p1, p2 = (x, y), (x, min(h - 1, y + step))
                    _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, p1, p2, val * 0.42, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, p1, p2, val * 0.18, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _field_lines(shape, seed, sm, name="field_lines_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81016)
    M, R, CC = _base(shape, int(seed), 0.12, 0.20, 0.26, 0.08)
    sc = _scale(shape)
    if _CV2_OK:
        poles = [(int(rng.integers(0, w)), int(rng.integers(0, h)), rng.choice([-1, 1])) for _ in range(20)]
        for cx, cy, sign in poles:
            _cv2.circle(R, (cx, cy), max(4, int(9 * sc)), 0.86 if sign > 0 else 0.28, 1, lineType=_cv2.LINE_AA)
            for k in range(10):
                pts = []
                a0 = k * math.tau / 10 + sign * 0.3
                for i in range(60):
                    rr = (8 + i * 2.6) * sc
                    a = a0 + sign * math.sin(i * 0.11) * 0.85
                    pts.append((int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr)))
                _polyline(M, pts, rng.uniform(0.24, 0.78), 1)
                _polyline(CC, pts, rng.uniform(0.30, 0.88), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _micro_scuff_hatch(shape, seed, sm, name="micro_scuff_hatch_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81017)
    M, R, CC = _base(shape, int(seed), 0.20, 0.26, 0.18, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 6500, 900)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ln = rng.uniform(5, 22) * sc
            a = rng.normal(-0.18, 0.42)
            x2, y2 = int(np.clip(cx + math.cos(a) * ln, 0, w - 1)), int(np.clip(cy + math.sin(a) * ln, 0, h - 1))
            val = rng.uniform(0.36, 0.96)
            _cv2.line(M, (cx, cy), (x2, y2), val, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy), (x2, y2), val * 0.34, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (x2, y2), min(0.98, val * 0.58), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _bassboat_flake(shape, seed, sm, name="bassboat_flake_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81018)
    M, R, CC = _base(shape, int(seed), 0.18, 0.18, 0.24, 0.08)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 5600, 800)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1, 5) * sc))
            pts = _star(cx, cy, max(2, r + 2), max(1, r), int(rng.integers(3, 6)), rng.uniform(0, math.tau))
            vals = rng.choice([0.24, 0.36, 0.50, 0.64, 0.78, 0.92], size=3)
            _cv2.fillPoly(M, [pts], float(vals[0]), lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [pts], float(vals[1]), lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts], float(vals[2]), lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _diamond_microdust(shape, seed, sm, name="diamond_microdust_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81035)
    M, R, CC = _base(shape, int(seed), 0.08, 0.09, 0.20, 0.09)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 7600, 1100)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1, 3.5) * sc))
            val = rng.uniform(0.42, 0.99)
            if rng.random() < 0.22:
                _draw_glint(M, R, CC, cx, cy, r + 2, (val, rng.uniform(0.20, 0.70), rng.uniform(0.58, 0.99)))
            else:
                _cv2.circle(M, (cx, cy), r, val, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), r, rng.uniform(0.44, 0.98), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _micro_wave_shimmer(shape, seed, sm, name="micro_wave_shimmer_rescue"):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(int(seed) + 81039)
    warp = _normalize(multi_scale_noise(shape, [3.5, 11, 29], [0.44, 0.34, 0.22], int(seed) + 199))
    wave = _normalize(np.sin((yy + np.sin(xx * 0.018) * 18 + warp * 34) * 0.090))
    micro = _normalize(np.sin(xx * 0.90 + yy * 0.16 + warp * 6.0))
    M = (0.10 + wave * 0.48 + micro * 0.16).astype(np.float32)
    R = (0.10 + (1 - wave) * 0.22 + micro * 0.08).astype(np.float32)
    CC = (0.28 + wave * 0.46 + micro * 0.18).astype(np.float32)
    if _CV2_OK:
        sc = _scale(shape)
        for _ in range(_count(shape, 5200, 720)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1, 3) * sc))
            val = rng.uniform(0.48, 0.98)
            _cv2.circle(M, (cx, cy), r, val, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, min(0.99, val + 0.05), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _skull_lace(shape, seed, sm, name="skull_lace_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81036)
    M, R, CC = _base(shape, int(seed), 0.18, 0.09, 0.12, 0.07)
    sc = _scale(shape)
    if _CV2_OK:
        pitch_x, pitch_y = max(56, int(150 * sc)), max(52, int(135 * sc))
        for y in range(-pitch_y, h + pitch_y, pitch_y):
            for x in range(-pitch_x, w + pitch_x, pitch_x):
                cx = x + pitch_x // 2
                cy = y + pitch_y // 2
                _cv2.ellipse(M, (cx, cy), (max(8, int(20 * sc)), max(10, int(26 * sc))), 0, 0, 360, 0.72, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (cx - int(7 * sc), cy - int(4 * sc)), max(2, int(4 * sc)), 0.92, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (cx + int(7 * sc), cy - int(4 * sc)), max(2, int(4 * sc)), 0.92, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx - int(9 * sc), cy + int(12 * sc)), (cx + int(9 * sc), cy + int(12 * sc)), 0.34, 1, lineType=_cv2.LINE_AA)
                for a in np.linspace(0, math.tau, 6, endpoint=False):
                    p2 = (int(cx + math.cos(a) * 46 * sc), int(cy + math.sin(a) * 46 * sc))
                    _cv2.line(CC, (cx, cy), p2, rng.uniform(0.30, 0.76), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _buffer_swirl_arcs(shape, seed, sm, name="buffer_swirl_arcs_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81037)
    M, R, CC = _base(shape, int(seed), 0.22, 0.18, 0.30, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1800, 260)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(5, int(rng.uniform(8, 26) * sc))
            start = rng.uniform(0, 280)
            span = rng.uniform(45, 160)
            val = rng.uniform(0.38, 0.96)
            _cv2.ellipse(M, (cx, cy), (r, max(2, int(r * rng.uniform(0.35, 0.75)))), rng.uniform(0, 180), start, start + span, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (r, max(2, int(r * rng.uniform(0.35, 0.75)))), rng.uniform(0, 180), start, start + span, min(0.98, val + 0.05), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (r, max(2, int(r * rng.uniform(0.35, 0.75)))), rng.uniform(0, 180), start, start + span, val * 0.22, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _forged_carbon_dense(shape, seed, sm, name="forged_carbon_dense_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81038)
    M, R, CC = _base(shape, int(seed), 0.12, 0.10, 0.20, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 3200, 500)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ln = rng.uniform(8, 32) * sc
            wid = rng.uniform(2, 7) * sc
            a = rng.uniform(0, math.tau)
            pts = np.asarray([
                [int(cx + math.cos(a) * ln), int(cy + math.sin(a) * ln)],
                [int(cx + math.cos(a + math.pi / 2) * wid), int(cy + math.sin(a + math.pi / 2) * wid)],
                [int(cx - math.cos(a) * ln * 0.45), int(cy - math.sin(a) * ln * 0.45)],
                [int(cx - math.cos(a + math.pi / 2) * wid), int(cy - math.sin(a + math.pi / 2) * wid)],
            ], dtype=np.int32)
            val = rng.uniform(0.20, 0.86)
            _cv2.fillPoly(M, [pts], val, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [pts], val * 0.18, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts], min(0.98, val + 0.08), lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _retro_wave_scan(shape, seed, sm, name="retro_wave_scan_rescue"):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(int(seed) + 81021)
    warp = _normalize(multi_scale_noise(shape, [2.8, 9, 23], [0.46, 0.34, 0.20], int(seed) + 121))
    bands = _normalize(np.sin((yy + np.sin(xx * 0.010) * 34 + warp * 46) * 0.045))
    micro = _normalize(np.sin(xx * 0.25 + yy * 0.035 + warp * 3.5))
    M = (0.08 + 0.58 * bands + 0.10 * micro).astype(np.float32)
    R = (0.10 + 0.30 * (1 - bands) + 0.20 * _normalize(np.sin(xx * 0.033 - yy * 0.020))).astype(np.float32)
    CC = (0.18 + 0.60 * _normalize(np.sin(xx * 0.055 + warp * 5.2)) + 0.12 * micro).astype(np.float32)
    if _CV2_OK:
        sc = _scale(shape)
        for y in range(0, h, max(5, int(12 * sc))):
            pts = [(x, int(np.clip(y + math.sin(x * 0.015 + y * 0.03) * 18 * sc, 0, h - 1))) for x in range(0, w, max(5, int(8 * sc)))]
            _polyline(M, pts, rng.uniform(0.34, 0.94), 1)
            _polyline(CC, pts, rng.uniform(0.42, 0.98), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _pinstripe_filigree(shape, seed, sm, name="pinstripe_filigree_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81022)
    M, R, CC = _base(shape, int(seed), 0.14, 0.12, 0.16, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(90, int(260 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx, cy = x + pitch // 2, y + pitch // 2
                for mirror in (-1, 1):
                    for arm in range(5):
                        pts = []
                        base_a = -math.pi / 2 + arm * 0.24 * mirror
                        for i in range(54):
                            t = i / 53
                            r = (10 + 76 * t) * sc
                            a = base_a + mirror * (t * 1.65 + math.sin(t * math.pi * 3) * 0.18)
                            pts.append((int(cx + math.cos(a) * r), int(cy + math.sin(a) * r)))
                        _polyline(M, pts, 0.78 + 0.16 * rng.random(), 1)
                        _polyline(R, pts, 0.34 + 0.28 * rng.random(), 1)
                        _polyline(CC, pts, 0.54 + 0.36 * rng.random(), 1)
                _draw_glint(M, R, CC, cx, cy, max(5, int(12 * sc)), (0.90, 0.48, 0.82))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _gloss_ribbons(shape, seed, sm, name="gloss_ribbons_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81023)
    M, R, CC = _base(shape, int(seed), 0.12, 0.12, 0.34, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for k in range(34):
            x0 = int((k + 0.5) * w / 34)
            pts = []
            for y in range(0, h, max(4, int(7 * sc))):
                x = int(x0 + math.sin(y * 0.011 + k) * 26 * sc + math.sin(y * 0.036 + k * 1.7) * 7 * sc)
                pts.append((np.clip(x, 0, w - 1), y))
            val = rng.uniform(0.46, 0.96)
            _polyline(CC, pts, min(0.99, val + 0.02), max(1, int(2 * sc)))
            _polyline(M, pts, val * 0.54, 1)
            _polyline(R, pts, val * 0.18, 1)
        for _ in range(_count(shape, 1600, 220)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(CC, (cx, cy), max(1, int(rng.uniform(1, 3) * sc)), rng.uniform(0.55, 0.98), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _hairline_satin(shape, seed, sm, name="hairline_satin_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81024)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    grain = _normalize(np.sin((xx * 0.72 + yy * 0.11) + np.sin(yy * 0.023) * 4.0))
    M = (0.20 + grain * 0.48).astype(np.float32)
    R = (0.16 + (1 - grain) * 0.20).astype(np.float32)
    CC = (0.34 + grain * 0.42).astype(np.float32)
    if _CV2_OK:
        sc = _scale(shape)
        for _ in range(_count(shape, 3200, 480)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ln = rng.uniform(9, 28) * sc
            a = 0.16 + rng.normal(0, 0.06)
            p2 = (int(np.clip(cx + math.cos(a) * ln, 0, w - 1)), int(np.clip(cy + math.sin(a) * ln, 0, h - 1)))
            val = rng.uniform(0.38, 0.92)
            _cv2.line(M, (cx, cy), p2, val, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), p2, min(0.98, val + 0.05), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _holo_fresnel_prism(shape, seed, sm, name="holo_fresnel_prism_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81025)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    M = np.full((h, w), 0.30, dtype=np.float32)
    R = np.full((h, w), 0.24, dtype=np.float32)
    CC = np.full((h, w), 0.40, dtype=np.float32)
    centers = [(w * 0.22, h * 0.22), (w * 0.78, h * 0.22), (w * 0.50, h * 0.52), (w * 0.18, h * 0.82), (w * 0.82, h * 0.82)]
    for idx, (cx, cy) in enumerate(centers):
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        rings = _normalize(np.sin(dist * 0.080 + idx))
        M = np.maximum(M, 0.18 + rings * 0.72)
        R = np.maximum(R, 0.10 + _normalize(np.sin(dist * 0.061 + 2.1)) * 0.82)
        CC = np.maximum(CC, 0.16 + _normalize(np.sin(dist * 0.047 + 4.3)) * 0.82)
    if _CV2_OK:
        sc = _scale(shape)
        for y in range(0, h, max(5, int(10 * sc))):
            _cv2.line(M, (0, y), (w - 1, int(np.clip(y + math.sin(y * 0.04) * 20 * sc, 0, h - 1))), rng.uniform(0.45, 0.98), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (0, y), (w - 1, int(np.clip(y + math.sin(y * 0.04) * 20 * sc, 0, h - 1))), rng.uniform(0.55, 0.99), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _hellfire_lava(shape, seed, sm, name="hellfire_lava_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81026)
    M, R, CC = _base(shape, int(seed), 0.20, 0.04, 0.06, 0.08)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 2300, 330)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            pts = [(x, y)]
            for _seg in range(int(rng.integers(3, 8))):
                a = rng.choice([-1.1, -0.75, -0.35, 0.35, 0.75, 1.1]) + rng.normal(0, 0.12)
                ln = rng.uniform(7, 20) * sc
                x = int(np.clip(x + math.cos(a) * ln, 0, w - 1))
                y = int(np.clip(y + math.sin(a) * ln, 0, h - 1))
                pts.append((x, y))
            val = rng.uniform(0.52, 0.99)
            _polyline(M, pts, val, 1)
            _polyline(R, pts, val * 0.10, 1)
            _polyline(CC, pts, val * 0.20, 1)
            if rng.random() < 0.20:
                _draw_glint(M, R, CC, pts[-1][0], pts[-1][1], max(2, int(5 * sc)), (0.98, 0.16, 0.22))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _overlap_snake_scales(shape, seed, sm, name="overlap_snake_scales_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81027)
    M, R, CC = _base(shape, int(seed), 0.18, 0.22, 0.20, 0.07)
    sc = _scale(shape)
    if _CV2_OK:
        step_x, step_y = max(12, int(34 * sc)), max(10, int(26 * sc))
        for row, y in enumerate(range(-step_y, h + step_y, step_y)):
            off = step_x // 2 if row % 2 else 0
            for x in range(-step_x, w + step_x, step_x):
                cx = x + off
                axes = (max(5, int(15 * sc)), max(4, int(11 * sc)))
                val = float(rng.choice([0.26, 0.38, 0.50, 0.64, 0.78, 0.92]))
                _cv2.ellipse(M, (cx, y), axes, 0, 200, 340, val * 0.64, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, y), axes, 0, 200, 340, val * 0.82, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, y), axes, 0, 200, 340, min(0.98, val + 0.05), 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.12:
                    _cv2.circle(M, (cx, y - axes[1] // 2), max(1, int(2 * sc)), 0.94, -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _diamond_snake_scales(shape, seed, sm, name="diamond_snake_scale_armor"):
    """OWNER MAKE-UNIQUE 2026-06-04: snake_scale_diamond was rendered with the
    rounded fishscale grammar (_overlap_snake_scales) and read as a cousin of the
    other scale overlays. Rebuilt as a true DIAMOND / RHOMBUS tessellation: a
    seamless interlocking rhombic lattice where every diamond scale carries its
    own directional sheen (bright keel down the long axis, dark seam grout
    between scales), like a diamondback's belly. Vectorized field + crisp keel
    lines so it reads fine at car scale."""
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81027)
    sc = _scale(shape)
    mn = min(h, w)
    s256 = max(mn / 256.0, 0.55)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Seamless DIAMOND (argyle / rotated-square) tessellation. Working in a
    # rotated lattice basis a=(x/px+y/py), b=(x/px-y/py) tiles the plane with
    # rhombi whose tips meet — a true diamond grid, NOT chevron rows.
    px = max(13.0 * s256, 5.0)        # diamond half-width
    py = max(18.0 * s256, 7.0)        # diamond half-height (taller snake lozenge)
    a = (xx / px + yy / py)
    b = (xx / px - yy / py)
    cellx = np.floor(a).astype(np.int32)
    celly = np.floor(b).astype(np.int32)
    fa = a - cellx                     # [0,1) within diamond, one axis
    fb = b - celly                     # [0,1) within diamond, other axis
    # distance from diamond center: 0 at center, 1 at the four tips/edges.
    dcen = np.maximum(np.abs(fa - 0.5), np.abs(fb - 0.5)) * 2.0
    inside = dcen < 1.0
    # per-scale domed sheen.
    crown = np.clip(1.0 - dcen, 0.0, 1.0) ** 0.6
    # per-diamond tonal variation (snake mottling) from the cell id.
    cellhash = ((cellx * 374761393 + celly * 668265263) & 0xFFFF) / 65535.0
    tone = (0.55 + 0.45 * cellhash.astype(np.float32))

    # Each diamond = bright metallic lozenge (M/CC dominant), dark grout between.
    M = (0.20 + crown * 0.72 * tone).astype(np.float32)
    R = (0.30 - crown * 0.18 * tone).astype(np.float32)
    CC = (0.22 + crown * 0.66 * tone).astype(np.float32)
    # bright keel highlight down the vertical mid-line of each diamond (spine).
    keel = np.clip(1.0 - np.abs(fa - fb) / 0.18, 0.0, 1.0) * inside * crown
    M = np.clip(M + keel * 0.20, 0, 1)
    CC = np.clip(CC + keel * 0.16, 0, 1)
    # DARK crisp seam grout where diamonds meet (dcen -> 1).
    seam = np.clip((dcen - 0.80) / 0.20, 0.0, 1.0)
    M = M * (1.0 - seam * 0.85)
    R = np.clip(R + seam * 0.52, 0.0, 1.0)             # grout rough/matte
    CC = CC * (1.0 - seam * 0.80)
    if _CV2_OK:
        # sparse bright glints on random scale crowns for snakeskin sparkle.
        for _ in range(_count(shape, 900, 160)):
            gx = int(rng.integers(0, w)); gy = int(rng.integers(0, h))
            _draw_glint(M, R, CC, gx, gy, max(2, int(3.5 * sc)), (0.92, 0.20, 0.74))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _perforated_mesh(shape, seed, sm, name="perforated_mesh_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81028)
    M, R, CC = _base(shape, int(seed), 0.26, 0.26, 0.22, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        step = max(8, int(22 * sc))
        for row, y in enumerate(range(0, h, step)):
            off = step // 2 if row % 2 else 0
            for x in range(-step, w + step, step):
                cx = x + off
                r = max(2, int(5 * sc))
                _cv2.circle(M, (cx, y), r, 0.06, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, y), r, 0.08, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, y), r, 0.10, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (cx, y), r + 1, rng.uniform(0.42, 0.88), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, y), r + 1, rng.uniform(0.34, 0.86), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _heat_temper_bands(shape, seed, sm, name="heat_temper_bands_rescue"):
    # OWNER-REBUILD 2026-06-03: "don't like the design at all, not enough fine
    # detail, low effort". TRUE tempered-steel heat tint: CONCENTRIC temper
    # bands radiating from hot torch spots, cycling the real oxide-color
    # sequence straw -> bronze -> purple -> blue -> grey as temperature falls
    # with distance, plus a layer of FINE oxide grain so it reads detailed at
    # car scale.
    h, w = shape
    rng = np.random.default_rng(int(seed) + 14277)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    mn = min(h, w)
    s256 = max(mn / 256.0, 0.6)

    # 2-4 hot centers -> nearest-center distance gives the concentric field.
    n_hot = int(rng.integers(2, 5))
    dist = np.full((h, w), 1e9, dtype=np.float32)
    for _ in range(n_hot):
        cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        dist = np.minimum(dist, d)
    # Warp the rings so they wave like real torch heat (not perfect circles).
    warp = _normalize(multi_scale_noise(shape, [6, 17, 40], [0.5, 0.32, 0.18], int(seed) + 142))
    band_pitch = float(rng.uniform(26.0, 40.0) * s256)
    t = (dist / band_pitch + (warp - 0.5) * 1.4).astype(np.float32)   # band index, continuous

    # Temper-color palette as (M, R, CC) stops; phase along t cycles through it.
    # straw(gold), bronze(orange), purple, blue, grey-blue
    stops = np.array([
        [0.86, 0.55, 0.30],   # straw / pale gold (hot, near center)
        [0.78, 0.66, 0.22],   # bronze / amber
        [0.50, 0.34, 0.74],   # purple
        [0.30, 0.18, 0.90],   # peacock blue
        [0.40, 0.46, 0.66],   # grey-blue (cool, far)
    ], dtype=np.float32)
    n_stops = stops.shape[0]
    band_f = np.clip(t, 0.0, None)
    idx = np.floor(band_f).astype(np.int32) % n_stops
    nxt = (idx + 1) % n_stops
    frac = (band_f - np.floor(band_f)).astype(np.float32)
    M = (stops[idx, 0] * (1 - frac) + stops[nxt, 0] * frac).astype(np.float32)
    R = (stops[idx, 1] * (1 - frac) + stops[nxt, 1] * frac).astype(np.float32)
    CC = (stops[idx, 2] * (1 - frac) + stops[nxt, 2] * frac).astype(np.float32)

    # Sharpen the band TRANSITIONS so the rings read as crisp tint lines.
    edge = np.abs(frac - 0.5)
    crisp = np.clip((0.18 - edge) / 0.18, 0.0, 1.0).astype(np.float32)  # bright on transitions
    M = np.clip(M + crisp * 0.18, 0, 1)
    CC = np.clip(CC + crisp * 0.10, 0, 1)

    # FINE oxide grain (the "fine detail" the owner wanted) modulated per pixel.
    grain = _normalize(multi_scale_noise(shape, [1.6, 3.5, 7.0], [0.5, 0.3, 0.2], int(seed) + 143))
    M = np.clip(M + (grain - 0.5) * 0.14, 0, 1)
    R = np.clip(R + (grain - 0.5) * 0.16, 0, 1)
    CC = np.clip(CC + (grain - 0.5) * 0.12, 0, 1)

    # Sparse bright oxide scale flecks for sparkle.
    n_fl = int(np.clip(h * w / 240.0, 300, 9000))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(0.10, 0.34, n_fl).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.20, 0.24, n_fl).astype(np.float32), 0, 1)

    return _finish(name, M, R, CC, _safe_sm(sm))


def _heat_scale_cells(shape, seed, sm, name="heat_scale_cells_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81029)
    M, R, CC = _base(shape, int(seed), 0.18, 0.08, 0.16, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        step = max(11, int(30 * sc))
        for row, y in enumerate(range(-step, h + step, step)):
            off = step // 2 if row % 2 else 0
            for x in range(-step, w + step, step):
                pts = _hex_points(x + off, y, int(13 * sc), 0)
                tier = float(rng.choice([0.24, 0.36, 0.50, 0.66, 0.82, 0.96]))
                _cv2.polylines(M, [pts], True, tier, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [pts], True, tier * 0.12, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, 0.22 + (1 - tier) * 0.58, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _crystal_needles(shape, seed, sm, name="crystal_needles_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81030)
    M, R, CC = _base(shape, int(seed), 0.18, 0.16, 0.26, 0.07)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 950, 150)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ln = rng.uniform(18, 62) * sc
            wid = rng.uniform(3, 10) * sc
            a = rng.uniform(0, math.tau)
            pts = np.asarray([
                [int(cx + math.cos(a) * ln), int(cy + math.sin(a) * ln)],
                [int(cx + math.cos(a + 2.35) * wid), int(cy + math.sin(a + 2.35) * wid)],
                [int(cx + math.cos(a + math.pi) * ln * 0.30), int(cy + math.sin(a + math.pi) * ln * 0.30)],
                [int(cx + math.cos(a - 2.35) * wid), int(cy + math.sin(a - 2.35) * wid)],
            ], dtype=np.int32)
            val = rng.uniform(0.38, 0.96)
            _cv2.fillPoly(CC, [pts], val * 0.58, lineType=_cv2.LINE_AA)
            _cv2.polylines(M, [pts], True, val, 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(R, [pts], True, val * 0.26, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _diamond_facet_lattice(shape, seed, sm, name="diamond_facet_lattice_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81031)
    M, R, CC = _base(shape, int(seed), 0.22, 0.18, 0.28, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        step = max(16, int(46 * sc))
        for y in range(-step, h + step, step):
            for x in range(-step, w + step, step):
                pts = np.asarray([[x, y + step // 2], [x + step // 2, y], [x + step, y + step // 2], [x + step // 2, y + step]], dtype=np.int32)
                val = float(rng.choice([0.22, 0.34, 0.48, 0.64, 0.80, 0.94]))
                _cv2.polylines(M, [pts], True, val, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, tuple(pts[0]), tuple(pts[2]), min(0.98, val + 0.05), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, tuple(pts[1]), tuple(pts[3]), val * 0.28, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _comet_trails(shape, seed, sm, name="comet_trails_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81032)
    M, R, CC = _base(shape, int(seed), 0.08, 0.09, 0.22, 0.10)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1200, 180)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            tail = []
            a = rng.uniform(-0.9, 0.4)
            for i in range(18):
                tail.append((int(np.clip(cx - math.cos(a + i * 0.03) * i * 4 * sc, 0, w - 1)), int(np.clip(cy - math.sin(a + i * 0.03) * i * 4 * sc, 0, h - 1))))
            _polyline(CC, tail, rng.uniform(0.46, 0.96), 1)
            _draw_glint(M, R, CC, cx, cy, max(2, int(rng.uniform(3, 8) * sc)), (0.90, rng.uniform(0.32, 0.82), 0.96))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _neural_branches(shape, seed, sm, name="neural_branches_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81033)
    M, R, CC = _base(shape, int(seed), 0.12, 0.20, 0.17, 0.08)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(120):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            angle = rng.uniform(0, math.tau)
            for branch in range(5):
                pts = [(x, y)]
                a = angle + rng.normal(0, 0.8)
                for _seg in range(24):
                    ln = rng.uniform(5, 15) * sc
                    x = int(np.clip(x + math.cos(a) * ln, 0, w - 1))
                    y = int(np.clip(y + math.sin(a) * ln, 0, h - 1))
                    a += rng.normal(0, 0.18)
                    pts.append((x, y))
                val = rng.uniform(0.30, 0.88)
                _polyline(R, pts, val, 1)
                _polyline(CC, pts, val * 0.58, 1)
                _polyline(M, pts, val * 0.40, 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _patina_drip_relic(shape, seed, sm, name="patina_drip_relic_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81019)
    M, R, CC = _base(shape, int(seed), 0.26, 0.42, 0.18, 0.12)
    sc = _scale(shape)
    if _CV2_OK:
        for x in range(0, w, max(15, int(38 * sc))):
            top = int(rng.integers(0, max(1, h // 3)))
            ln = int(rng.uniform(35, 180) * sc)
            pts = [(x, top)]
            for k in range(1, 18):
                pts.append((int(np.clip(x + math.sin(k * 0.8 + x) * 12 * sc, 0, w - 1)), int(np.clip(top + k * ln / 18, 0, h - 1))))
            val = rng.uniform(0.40, 0.94)
            _polyline(M, pts, val * 0.72, 1)
            _polyline(R, pts, min(0.98, val * 1.12), 1)
            _polyline(CC, pts, val * 0.32, 1)
        for _ in range(_count(shape, 2600, 380)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(R, (cx, cy), max(1, int(rng.uniform(2, 7) * sc)), rng.uniform(0.48, 0.96), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.28:
                _cv2.circle(CC, (cx, cy), max(1, int(rng.uniform(1, 4) * sc)), rng.uniform(0.32, 0.72), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _vinyl_edge_curl(shape, seed, sm, name="vinyl_edge_curl_rescue"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 81020)
    M, R, CC = _base(shape, int(seed), 0.16, 0.24, 0.20, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1200, 180)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            length = int(rng.uniform(18, 52) * sc)
            height = int(rng.uniform(4, 12) * sc)
            rot = rng.uniform(0, math.tau)
            pts = []
            for k in range(12):
                t = k / 11
                x = (t - 0.5) * length
                y = math.sin(t * math.pi) * height
                pts.append((int(cx + math.cos(rot) * x - math.sin(rot) * y), int(cy + math.sin(rot) * x + math.cos(rot) * y)))
            val = rng.uniform(0.42, 0.92)
            _polyline(M, pts, val, 1)
            _polyline(CC, pts, min(0.98, val + 0.04), 1)
            _polyline(R, pts, val * 0.22, 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


# Public override wrappers. Function names keep old ids stable while the
# rendered finish language changes sharply per owner feedback.
def rescue_abstract_expressionist_splatter(shape, seed, sm, **kwargs): return _skull_lace(shape, seed + 1, sm, "bone_chapel_skull_lace")
def rescue_abstract_retro_wave(shape, seed, sm, **kwargs): return _retro_wave_scan(shape, seed + 2, sm, "retro_prism_wave_scan")
def rescue_brushstroke_bold(shape, seed, sm, **kwargs): return _pinstripe_filigree(shape, seed + 3, sm, "pinstripe_spirit_filigree")
def rescue_cc_fish_eye(shape, seed, sm, **kwargs): return _clearcoat_bubble_field(shape, seed + 4, sm, "clearcoat_fisheye_bloom")
def rescue_cc_gloss_stripe(shape, seed, sm, **kwargs): return _gloss_ribbons(shape, seed + 5, sm, "clearcoat_gloss_ribbons")
def rescue_cc_masking_edge(shape, seed, sm, **kwargs): return _masking_tape_maze(shape, seed + 6, sm, "micro_tape_edge_maze")
def rescue_cc_spot_polish(shape, seed, sm, **kwargs): return _machined_coin_field(shape, seed + 7, sm, "engine_turn_spot_polish")
def rescue_circuit_trace(shape, seed, sm, **kwargs): return _circuit_board(shape, seed + 8, sm, "neon_pit_board_circuit")
def rescue_cloud_wisps(shape, seed, sm, **kwargs): return _ouija_mystic(shape, seed + 9, sm, "ouija_mystic_glamour")
def rescue_cloud_wisps_cool(shape, seed, sm, **kwargs): return _wave_pearl_ripple(shape, seed + 10, sm, "pearl_wave_ripple")
def rescue_cloud_wisps_warm(shape, seed, sm, **kwargs): return _samhain_ritual(shape, seed + 11, sm, "samhain_candle_ritual")
def rescue_copper_patina_drip(shape, seed, sm, **kwargs): return _patina_drip_relic(shape, seed + 12, sm, "oxidized_copper_relic_drip")
def rescue_crystal_growth(shape, seed, sm, **kwargs): return _crystal_needles(shape, seed + 13, sm, "crystal_needle_growth")
def rescue_decal_lift_edge(shape, seed, sm, **kwargs): return _vinyl_edge_curl(shape, seed + 14, sm, "micro_vinyl_edge_curl")
def rescue_demon_eye_field(shape, seed, sm, **kwargs): return _viper_pit_hex(shape, seed + 15, sm, "viper_pit_eye_hex")
def rescue_diamond_dust(shape, seed, sm, **kwargs): return _diamond_microdust(shape, seed + 16, sm, "diamond_microdust_field")
def rescue_flake_scatter(shape, seed, sm, **kwargs): return _bassboat_flake(shape, seed + 17, sm, "bassboat_prismatic_flake")
def rescue_forged_carbon_chip(shape, seed, sm, **kwargs): return _forged_carbon_dense(shape, seed + 18, sm, "forged_carbon_shard_plate")
def rescue_hairline_polish(shape, seed, sm, **kwargs): return _hairline_satin(shape, seed + 19, sm, "hairline_satin_polish")
def rescue_hand_polished(shape, seed, sm, **kwargs): return _buffer_swirl_arcs(shape, seed + 20, sm, "hand_polished_buffer_swirls")
def rescue_heat_discoloration(shape, seed, sm, **kwargs): return _heat_temper_bands(shape, seed + 21, sm, "heat_temper_color_bands")
def rescue_hellfire_crackle(shape, seed, sm, **kwargs): return _hellfire_lava(shape, seed + 22, sm, "hellfire_lava_crackle")
def rescue_magnetic_field(shape, seed, sm, **kwargs): return _field_lines(shape, seed + 23, sm, "magnetic_flux_pinlines")
def rescue_neural_dendrite(shape, seed, sm, **kwargs): return _neural_branches(shape, seed + 24, sm, "neural_dendrite_branches")
def rescue_nordic_rune_field(shape, seed, sm, **kwargs): return _rune_mandala(shape, seed + 25, sm, "nordic_rune_mandala")
def rescue_razor_wire_coil(shape, seed, sm, **kwargs): return _razor_coil(shape, seed + 26, sm, "razor_wire_concertina")
def rescue_snake_scale_diamond(shape, seed, sm, **kwargs): return _diamond_snake_scales(shape, seed + 27, sm, "diamond_snake_scale_armor")
def rescue_sparkle_comet(shape, seed, sm, **kwargs): return _comet_trails(shape, seed + 28, sm, "comet_trail_cartography")
def rescue_spec_faceted_diamond(shape, seed, sm, **kwargs): return _diamond_facet_lattice(shape, seed + 29, sm, "faceted_diamond_lattice")
def rescue_spec_heat_scale(shape, seed, sm, **kwargs): return _heat_scale_cells(shape, seed + 30, sm, "tempered_heat_scale_cells")
def rescue_spec_holographic_foil(shape, seed, sm, **kwargs): return _holo_fresnel_prism(shape, seed + 31, sm, "holographic_fresnel_foil")
def rescue_spec_mesh_perforated(shape, seed, sm, **kwargs): return _perforated_mesh(shape, seed + 32, sm, "perforated_metal_mesh")
def rescue_spec_oil_film_thick(shape, seed, sm, **kwargs): return _liquid_chrome_blobs(shape, seed + 33, sm, "liquid_metal_oil_slick")
def rescue_spec_wood_grain_fine(shape, seed, sm, **kwargs): return _terrain_erosion(shape, seed + 34, sm, "terrain_erosion_strata")
def rescue_wear_scuff(shape, seed, sm, **kwargs): return _micro_scuff_hatch(shape, seed + 35, sm, "micro_scuff_hatch")
def rescue_micro_sparkle(shape, seed, sm, **kwargs): return _micro_wave_shimmer(shape, seed + 36, sm, "micro_wave_shimmer")


# 2026-05-27 overnight WWRD pass 1: late redefinitions for rescue cards that
# still looked like cousins on the contact sheet. These deliberately move away
# from repeated dots/grids and into stronger individual silhouettes.
def _graveyard_cameo_lace(shape, seed, sm, name="graveyard_cameo_lace"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82001)
    M, R, CC = _base(shape, int(seed), 0.16, 0.10, 0.14, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        pitch_x, pitch_y = max(80, int(230 * sc)), max(74, int(210 * sc))
        for y in range(-pitch_y, h + pitch_y, pitch_y):
            for x in range(-pitch_x, w + pitch_x, pitch_x):
                cx, cy = x + pitch_x // 2, y + pitch_y // 2
                _cv2.ellipse(M, (cx, cy), (max(18, int(54 * sc)), max(24, int(72 * sc))), 0, 0, 360, 0.78, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (max(12, int(40 * sc)), max(18, int(56 * sc))), 0, 0, 360, 0.34, 1, lineType=_cv2.LINE_AA)
                for side in (-1, 1):
                    pts = []
                    for i in range(34):
                        t = i / 33
                        a = -1.15 + t * 2.3
                        rr = (35 + math.sin(t * math.pi) * 22) * sc
                        pts.append((int(cx + side * math.cos(a) * rr), int(cy + math.sin(a) * rr)))
                    _polyline(M, pts, 0.86, 1)
                    _polyline(R, pts, 0.32, 1)
                _cv2.circle(M, (cx - int(10 * sc), cy - int(8 * sc)), max(3, int(7 * sc)), 0.94, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (cx + int(10 * sc), cy - int(8 * sc)), max(3, int(7 * sc)), 0.94, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx - int(16 * sc), cy + int(16 * sc)), (cx + int(16 * sc), cy + int(16 * sc)), 0.82, 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 1600, 240)):
            _draw_glint(M, R, CC, int(rng.integers(0, w)), int(rng.integers(0, h)), max(2, int(rng.uniform(3, 7) * sc)), (0.72, 0.28, 0.64))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _tattoo_razor_floral(shape, seed, sm, name="tattoo_razor_floral"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82002)
    M, R, CC = _base(shape, int(seed), 0.13, 0.12, 0.16, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(72, int(190 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx, cy = x + pitch // 2, y + pitch // 2
                blade = np.asarray([[cx, cy - int(56 * sc)], [cx + int(8 * sc), cy + int(46 * sc)], [cx, cy + int(64 * sc)], [cx - int(8 * sc), cy + int(46 * sc)]], dtype=np.int32)
                _cv2.polylines(M, [blade], True, 0.90, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [blade], True, 0.62, 1, lineType=_cv2.LINE_AA)
                for side in (-1, 1):
                    for k in range(3):
                        pts = []
                        for i in range(42):
                            t = i / 41
                            a = -1.3 + t * 2.2
                            rr = (20 + k * 9 + t * 35) * sc
                            pts.append((int(cx + side * math.cos(a) * rr), int(cy - int(6 * sc) + math.sin(a) * rr)))
                        _polyline(M, pts, 0.74 + 0.08 * k, 1)
                        _polyline(R, pts, 0.28 + 0.08 * k, 1)
                _draw_glint(M, R, CC, cx, cy, max(4, int(11 * sc)), (0.92, 0.32, 0.86))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _fisheye_lens_confetti(shape, seed, sm, name="fisheye_lens_confetti"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82003)
    M, R, CC = _base(shape, int(seed), 0.12, 0.14, 0.34, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 3200, 520)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx = max(4, int(rng.uniform(6, 22) * sc))
            ry = max(2, int(rx * rng.uniform(0.32, 0.72)))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.48, 0.98)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 330, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rx, ry), rot, 0, 330, val * 0.16, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(M, (cx - rx // 3, cy - ry // 3), max(1, int(2 * sc)), min(0.98, val + 0.04), -1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 2200, 300)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(CC, (cx, cy), 1, rng.uniform(0.52, 0.96), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _rotary_spot_polish(shape, seed, sm, name="rotary_spot_polish"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82004)
    M, R, CC = _base(shape, int(seed), 0.20, 0.15, 0.34, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1650, 240)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(7, int(rng.uniform(10, 30) * sc))
            for k in range(4):
                start = rng.uniform(0, 300)
                val = rng.uniform(0.42, 0.96)
                axes = (r - k * max(1, int(3 * sc)), max(2, int((r - k * 2) * rng.uniform(0.35, 0.70))))
                _cv2.ellipse(M, (cx, cy), axes, rng.uniform(0, 180), start, start + rng.uniform(70, 210), val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), axes, rng.uniform(0, 180), start, start + rng.uniform(70, 210), min(0.98, val + 0.05), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), axes, rng.uniform(0, 180), start, start + rng.uniform(70, 210), val * 0.18, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _phantom_lace_veil(shape, seed, sm, name="phantom_lace_veil"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82005)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    veil = _normalize(np.sin(xx * 0.014 + np.sin(yy * 0.011) * 5.0) + np.sin((xx + yy) * 0.009))
    M = (0.10 + veil * 0.24).astype(np.float32)
    R = (0.12 + (1 - veil) * 0.20).astype(np.float32)
    CC = (0.20 + veil * 0.42).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 800, 120)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            pts = []
            for i in range(56):
                t = i / 55
                a = t * math.tau * 0.85 + rng.uniform(-0.04, 0.04)
                rr = (9 + 42 * t + math.sin(t * math.tau * 3) * 6) * sc
                pts.append((int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr)))
            _polyline(CC, pts, rng.uniform(0.42, 0.92), 1)
            _polyline(M, pts, rng.uniform(0.24, 0.72), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _verdigris_circuit_relic(shape, seed, sm, name="verdigris_circuit_relic"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82006)
    M, R, CC = _base(shape, int(seed), 0.24, 0.42, 0.18, 0.10)
    sc = _scale(shape)
    if _CV2_OK:
        grid = max(10, int(26 * sc))
        for _ in range(_count(shape, 2600, 380)):
            x = int(rng.integers(0, w) // grid * grid)
            y = int(rng.integers(0, h) // grid * grid)
            pts = [(x, y)]
            for _seg in range(int(rng.integers(3, 8))):
                if rng.random() < 0.55:
                    x = int(np.clip(x + rng.choice([-1, 1]) * grid * int(rng.integers(1, 4)), 0, w - 1))
                else:
                    y = int(np.clip(y + rng.choice([-1, 1]) * grid * int(rng.integers(1, 4)), 0, h - 1))
                pts.append((x, y))
            val = rng.uniform(0.42, 0.96)
            _polyline(R, pts, val, 1)
            _polyline(M, pts, val * 0.62, 1)
            _polyline(CC, pts, val * 0.26, 1)
            if rng.random() < 0.35:
                _cv2.circle(R, pts[-1], max(2, int(5 * sc)), min(0.98, val + 0.04), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _compass_flux_filings(shape, seed, sm, name="compass_flux_filings"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82007)
    M, R, CC = _base(shape, int(seed), 0.10, 0.22, 0.22, 0.07)
    sc = _scale(shape)
    if _CV2_OK:
        centers = [(int(rng.integers(0, w)), int(rng.integers(0, h))) for _ in range(18)]
        for cx, cy in centers:
            for a in np.linspace(0, math.tau, 16, endpoint=False):
                pts = []
                for i in range(42):
                    rr = (8 + i * 3.2) * sc
                    aa = a + math.sin(i * 0.17) * 0.42
                    pts.append((int(cx + math.cos(aa) * rr), int(cy + math.sin(aa) * rr)))
                _polyline(M, pts, rng.uniform(0.34, 0.86), 1)
                _polyline(CC, pts, rng.uniform(0.36, 0.92), 1)
            _draw_glint(M, R, CC, cx, cy, max(5, int(12 * sc)), (0.90, 0.38, 0.76))
        for _ in range(_count(shape, 2600, 360)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            a = rng.uniform(0, math.tau)
            ln = rng.uniform(4, 12) * sc
            _cv2.line(R, (cx, cy), (int(cx + math.cos(a) * ln), int(cy + math.sin(a) * ln)), rng.uniform(0.32, 0.90), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _nordic_knot_ironwork(shape, seed, sm, name="nordic_knot_ironwork"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82008)
    M, R, CC = _base(shape, int(seed), 0.15, 0.16, 0.13, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(76, int(210 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx, cy = x + pitch // 2, y + pitch // 2
                for rot in (0, math.pi / 2):
                    pts = []
                    for i in range(96):
                        t = i / 95
                        a = rot + (t - 0.5) * math.pi * 1.4
                        rr = (20 + 42 * abs(math.sin(t * math.pi))) * sc
                        pts.append((int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr)))
                    _polyline(M, pts, 0.82, 1)
                    _polyline(CC, pts, 0.40, 1)
                for a in np.linspace(0, math.tau, 8, endpoint=False):
                    p1 = (int(cx + math.cos(a) * 16 * sc), int(cy + math.sin(a) * 16 * sc))
                    p2 = (int(cx + math.cos(a) * 68 * sc), int(cy + math.sin(a) * 68 * sc))
                    _cv2.line(R, p1, p2, rng.uniform(0.28, 0.76), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _concertina_razor_loops(shape, seed, sm, name="concertina_razor_loops"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82009)
    M, R, CC = _base(shape, int(seed), 0.23, 0.24, 0.28, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for row in range(9):
            y0 = int((row + 0.5) * h / 9)
            for x0 in range(-60, w + 80, max(34, int(86 * sc))):
                cx = int(x0 + math.sin(row) * 20 * sc)
                for rr in range(max(8, int(18 * sc)), max(18, int(42 * sc)), max(4, int(7 * sc))):
                    _cv2.ellipse(M, (cx, y0), (rr, max(5, int(rr * 0.42))), 0, 0, 360, rng.uniform(0.44, 0.94), 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(CC, (cx, y0), (rr, max(5, int(rr * 0.42))), 0, 0, 360, rng.uniform(0.50, 0.98), 1, lineType=_cv2.LINE_AA)
                for a in (0.7, 2.4, 3.9, 5.5):
                    p1 = (int(cx + math.cos(a) * 18 * sc), int(y0 + math.sin(a) * 8 * sc))
                    p2 = (int(cx + math.cos(a) * 34 * sc), int(y0 + math.sin(a) * 18 * sc))
                    _cv2.line(M, p1, p2, 0.98, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, p1, p2, 0.42, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _pit_road_scuff_transfer(shape, seed, sm, name="pit_road_scuff_transfer"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82010)
    M, R, CC = _base(shape, int(seed), 0.15, 0.28, 0.13, 0.07)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 5200, 760)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ln = rng.uniform(9, 42) * sc
            a = rng.normal(-0.35, 0.22)
            p2 = (int(np.clip(cx + math.cos(a) * ln, 0, w - 1)), int(np.clip(cy + math.sin(a) * ln, 0, h - 1)))
            val = rng.uniform(0.36, 0.92)
            _cv2.line(R, (cx, cy), p2, val, 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, (cx, cy), p2, val * 0.48, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.42:
                _cv2.line(CC, (cx, cy), p2, val * 0.20, 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 900, 140)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(R, (cx, cy), max(1, int(rng.uniform(2, 7) * sc)), rng.uniform(0.42, 0.88), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _brake_dust_halftone(shape, seed, sm, name="brake_dust_halftone"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82011)
    M, R, CC = _base(shape, int(seed), 0.13, 0.34, 0.10, 0.07)
    sc = _scale(shape)
    if _CV2_OK:
        step = max(7, int(18 * sc))
        for y in range(0, h, step):
            for x in range(0, w, step):
                wave = 0.5 + 0.5 * math.sin(x * 0.015 + y * 0.010)
                if rng.random() < 0.22 + 0.45 * wave:
                    r = max(1, int(rng.uniform(1, 4 + 5 * wave) * sc))
                    _cv2.circle(R, (x, y), r, rng.uniform(0.38, 0.90), -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(M, (x, y), max(1, r // 2), rng.uniform(0.12, 0.36), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


# Override the weaker first rescue definitions.
def rescue_abstract_expressionist_splatter(shape, seed, sm, **kwargs): return _graveyard_cameo_lace(shape, seed + 101, sm)
def rescue_brushstroke_bold(shape, seed, sm, **kwargs): return _tattoo_razor_floral(shape, seed + 102, sm)
def rescue_cc_fish_eye(shape, seed, sm, **kwargs): return _fisheye_lens_confetti(shape, seed + 103, sm)
def rescue_cc_spot_polish(shape, seed, sm, **kwargs): return _rotary_spot_polish(shape, seed + 104, sm)
def rescue_cloud_wisps(shape, seed, sm, **kwargs): return _phantom_lace_veil(shape, seed + 105, sm)
def rescue_copper_patina_drip(shape, seed, sm, **kwargs): return _verdigris_circuit_relic(shape, seed + 106, sm)
def rescue_magnetic_field(shape, seed, sm, **kwargs): return _compass_flux_filings(shape, seed + 107, sm)
def rescue_nordic_rune_field(shape, seed, sm, **kwargs): return _nordic_knot_ironwork(shape, seed + 108, sm)
def rescue_razor_wire_coil(shape, seed, sm, **kwargs): return _concertina_razor_loops(shape, seed + 109, sm)
def rescue_wear_scuff(shape, seed, sm, **kwargs): return _pit_road_scuff_transfer(shape, seed + 110, sm)
def rescue_brake_dust_buildup(shape, seed, sm, **kwargs): return _brake_dust_halftone(shape, seed + 111, sm)


def _voodoo_sigil_wall(shape, seed, sm, name="voodoo_sigil_wall"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82101)
    M, R, CC = _base(shape, int(seed), 0.18, 0.08, 0.11, 0.08)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(92, int(245 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx = x + pitch // 2 + int(math.sin(y * 0.01) * 18 * sc)
                cy = y + pitch // 2
                for rr, val in ((22, 0.58), (38, 0.76), (62, 0.88)):
                    _cv2.circle(M, (cx, cy), max(6, int(rr * sc)), val, 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (cx, cy), max(6, int(rr * sc)), val * 0.34, 1, lineType=_cv2.LINE_AA)
                for a in np.linspace(0, math.tau, 7, endpoint=False):
                    p1 = (int(cx + math.cos(a) * 11 * sc), int(cy + math.sin(a) * 11 * sc))
                    p2 = (int(cx + math.cos(a) * 68 * sc), int(cy + math.sin(a) * 68 * sc))
                    _cv2.line(M, p1, p2, rng.uniform(0.62, 0.96), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, p1, p2, rng.uniform(0.16, 0.48), 1, lineType=_cv2.LINE_AA)
                for dx in (-42, 42):
                    bx = cx + int(dx * sc)
                    _cv2.line(M, (bx, cy - int(28 * sc)), (bx, cy + int(28 * sc)), 0.78, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(M, (bx - int(10 * sc), cy - int(10 * sc)), (bx + int(10 * sc), cy - int(10 * sc)), 0.78, 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 2200, 320)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(R, (cx, cy), 1, rng.uniform(0.38, 0.90), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _hotrod_brush_slashes(shape, seed, sm, name="hotrod_brush_slashes"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82102)
    M, R, CC = _base(shape, int(seed), 0.14, 0.17, 0.20, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 4400, 620)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ln = rng.uniform(12, 46) * sc
            curve = rng.uniform(-0.38, 0.38)
            a = rng.choice([-0.9, -0.35, 0.22, 0.75]) + rng.normal(0, 0.16)
            pts = []
            for i in range(9):
                t = i / 8
                aa = a + curve * (t - 0.5)
                pts.append((int(np.clip(cx + math.cos(aa) * ln * (t - 0.5), 0, w - 1)), int(np.clip(cy + math.sin(aa) * ln * (t - 0.5), 0, h - 1))))
            val = rng.uniform(0.36, 0.96)
            _polyline(M, pts, val, 1)
            _polyline(CC, pts, min(0.99, val + 0.06), 1)
            if rng.random() < 0.35:
                _polyline(R, pts, val * 0.24, 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _fisheye_pac_lenses(shape, seed, sm, name="fisheye_pac_lenses"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82103)
    M, R, CC = _base(shape, int(seed), 0.11, 0.12, 0.30, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 2400, 420)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(4, int(rng.uniform(8, 24) * sc))
            val = rng.uniform(0.46, 0.98)
            start = rng.uniform(20, 80)
            rot = rng.uniform(0, 180)
            _cv2.ellipse(CC, (cx, cy), (r, max(2, int(r * 0.72))), rot, start, 360 - start, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (max(2, r // 2), max(1, int(r * 0.36))), rot, start + 12, 360 - start - 12, val * 0.72, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (r, max(2, int(r * 0.72))), rot, start, 360 - start, val * 0.14, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(M, (cx - r // 3, cy - r // 3), max(1, r // 4), min(0.99, val + 0.04), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _spirit_smoke_calligraphy(shape, seed, sm, name="spirit_smoke_calligraphy"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82104)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    veil = _normalize(np.sin(xx * 0.010 + np.sin(yy * 0.012) * 4.5) + np.cos((xx - yy) * 0.010))
    M = (0.10 + veil * 0.26).astype(np.float32)
    R = (0.12 + (1 - veil) * 0.20).astype(np.float32)
    CC = (0.18 + veil * 0.48).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1350, 200)):
            cx, cy = int(rng.integers(-40, w + 40)), int(rng.integers(-40, h + 40))
            pts = []
            for i in range(84):
                t = i / 83
                a = t * math.tau * rng.uniform(0.45, 1.2) + rng.uniform(-0.10, 0.10)
                rr = (8 + 85 * t + math.sin(t * math.tau * 4) * 11) * sc
                pts.append((int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr)))
            _polyline(CC, pts, rng.uniform(0.50, 0.96), 1)
            _polyline(M, pts, rng.uniform(0.30, 0.78), 1)
            if rng.random() < 0.45:
                _polyline(R, pts, rng.uniform(0.18, 0.52), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _nordic_braidwork(shape, seed, sm, name="nordic_braidwork"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82105)
    M, R, CC = _base(shape, int(seed), 0.14, 0.16, 0.15, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-2, 10):
            x0 = int((band - 2) * w / 6)
            pts_a, pts_b = [], []
            for i in range(130):
                y = int(i * h / 129)
                center = x0 + int(y * 0.30 + math.sin(i * 0.10 + band) * 54 * sc)
                weave = math.sin(i * 0.42) * 18 * sc
                pts_a.append((int(np.clip(center + weave, 0, w - 1)), y))
                pts_b.append((int(np.clip(center - weave, 0, w - 1)), y))
            _polyline(M, pts_a, rng.uniform(0.62, 0.96), 1)
            _polyline(CC, pts_a, rng.uniform(0.32, 0.84), 1)
            _polyline(M, pts_b, rng.uniform(0.62, 0.96), 1)
            _polyline(R, pts_b, rng.uniform(0.24, 0.68), 1)
            for x, y in pts_a[8::14]:
                _cv2.line(M, (x - int(8 * sc), y), (x + int(8 * sc), y), 0.82, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x, y - int(8 * sc)), (x, y + int(8 * sc)), 0.42, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _chaos_razor_snarl(shape, seed, sm, name="chaos_razor_snarl"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82106)
    M, R, CC = _base(shape, int(seed), 0.22, 0.24, 0.27, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 900, 140)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx = max(8, int(rng.uniform(12, 30) * sc))
            ry = max(4, int(rx * rng.uniform(0.26, 0.55)))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.46, 0.98)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
            for a in (rot * math.pi / 180 + 0.75, rot * math.pi / 180 - 0.75):
                p1 = (int(cx + math.cos(a) * rx * 0.55), int(cy + math.sin(a) * ry * 0.55))
                p2 = (int(cx + math.cos(a) * rx * 1.05), int(cy + math.sin(a) * ry * 1.10))
                _cv2.line(M, p1, p2, 0.98, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, p1, p2, 0.38, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_abstract_expressionist_splatter(shape, seed, sm, **kwargs): return _voodoo_sigil_wall(shape, seed + 201, sm)
def rescue_brushstroke_bold(shape, seed, sm, **kwargs): return _hotrod_brush_slashes(shape, seed + 202, sm)
def rescue_cc_fish_eye(shape, seed, sm, **kwargs): return _fisheye_pac_lenses(shape, seed + 203, sm)
def rescue_cloud_wisps(shape, seed, sm, **kwargs): return _spirit_smoke_calligraphy(shape, seed + 204, sm)
def rescue_nordic_rune_field(shape, seed, sm, **kwargs): return _nordic_braidwork(shape, seed + 205, sm)
def rescue_razor_wire_coil(shape, seed, sm, **kwargs): return _chaos_razor_snarl(shape, seed + 206, sm)


def _damascus_satin_bands(shape, seed, sm, name="damascus_satin_bands"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82201)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [3, 9, 21], [0.46, 0.34, 0.20], int(seed) + 220))
    bands = _normalize(np.sin((xx * 0.050 + np.sin(yy * 0.012) * 3.5 + warp * 7.0)))
    grain = _normalize(np.sin(xx * 0.62 + yy * 0.08 + warp * 4.0))
    M = (0.16 + bands * 0.52 + grain * 0.12).astype(np.float32)
    R = (0.12 + (1 - bands) * 0.24 + grain * 0.08).astype(np.float32)
    CC = (0.26 + bands * 0.45 + grain * 0.16).astype(np.float32)
    if _CV2_OK:
        sc = _scale(shape)
        for y in range(0, h, max(6, int(14 * sc))):
            pts = [(x, int(np.clip(y + math.sin(x * 0.018 + y * 0.02) * 20 * sc, 0, h - 1))) for x in range(0, w, max(5, int(8 * sc)))]
            _polyline(M, pts, rng.uniform(0.36, 0.92), 1)
            _polyline(CC, pts, rng.uniform(0.42, 0.96), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _orbital_buffer_moons(shape, seed, sm, name="orbital_buffer_moons"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82202)
    M, R, CC = _base(shape, int(seed), 0.22, 0.16, 0.31, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1450, 220)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(8, int(rng.uniform(12, 34) * sc))
            rot = rng.uniform(0, 180)
            for k in range(3):
                val = rng.uniform(0.38, 0.96)
                axes = (max(3, r - k * int(4 * sc)), max(2, int((r - k * int(3 * sc)) * rng.uniform(0.35, 0.68))))
                _cv2.ellipse(M, (cx, cy), axes, rot + k * 17, rng.uniform(0, 80), rng.uniform(170, 340), val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), axes, rot + k * 17, rng.uniform(0, 80), rng.uniform(170, 340), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), axes, rot + k * 17, rng.uniform(0, 80), rng.uniform(170, 340), val * 0.18, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _oil_gasket_bolt_grime(shape, seed, sm, name="oil_gasket_bolt_grime"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82203)
    M, R, CC = _base(shape, int(seed), 0.13, 0.36, 0.10, 0.09)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 850, 130)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(5, int(rng.uniform(8, 23) * sc))
            _cv2.circle(R, (cx, cy), r, rng.uniform(0.48, 0.94), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(M, (cx, cy), max(2, r // 3), rng.uniform(0.22, 0.68), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.55:
                ln = rng.uniform(18, 70) * sc
                a = rng.normal(0.35, 0.45)
                _cv2.line(R, (cx, cy), (int(np.clip(cx + math.cos(a) * ln, 0, w - 1)), int(np.clip(cy + math.sin(a) * ln, 0, h - 1))), rng.uniform(0.44, 0.88), 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 2600, 380)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(R, (cx, cy), max(1, int(rng.uniform(1, 4) * sc)), rng.uniform(0.34, 0.84), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _ember_moth_veil(shape, seed, sm, name="ember_moth_veil"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82204)
    M, R, CC = _base(shape, int(seed), 0.17, 0.08, 0.11, 0.08)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1500, 220)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            wing = max(5, int(rng.uniform(8, 18) * sc))
            val = rng.uniform(0.46, 0.96)
            _cv2.ellipse(M, (cx - wing // 2, cy), (wing, max(2, wing // 2)), -28, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx + wing // 2, cy), (wing, max(2, wing // 2)), 28, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy - wing), (cx, cy + wing), val * 0.25, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), max(1, wing // 5), min(0.98, val + 0.04), -1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 1400, 220)):
            _draw_glint(M, R, CC, int(rng.integers(0, w)), int(rng.integers(0, h)), max(2, int(rng.uniform(3, 7) * sc)), (0.82, 0.18, 0.30))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _nacre_shard_inlay(shape, seed, sm, name="nacre_shard_inlay"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82205)
    M, R, CC = _base(shape, int(seed), 0.18, 0.18, 0.38, 0.08)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 2300, 340)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = rng.uniform(8, 28) * sc
            pts = np.asarray([[int(cx + math.cos(i * math.tau / 5 + rng.uniform(-0.25, 0.25)) * r * rng.uniform(0.45, 1.15)), int(cy + math.sin(i * math.tau / 5 + rng.uniform(-0.25, 0.25)) * r * rng.uniform(0.45, 1.15))] for i in range(5)], dtype=np.int32)
            val = rng.uniform(0.34, 0.96)
            _cv2.fillPoly(CC, [pts], val, lineType=_cv2.LINE_AA)
            _cv2.polylines(M, [pts], True, min(0.99, val + 0.02), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(R, [pts], True, val * 0.22, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _enamel_drip_curtain(shape, seed, sm, name="enamel_drip_curtain"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82206)
    M, R, CC = _base(shape, int(seed), 0.15, 0.18, 0.28, 0.07)
    sc = _scale(shape)
    if _CV2_OK:
        for x in range(0, w, max(9, int(24 * sc))):
            top = int(rng.integers(0, h))
            length = int(rng.uniform(40, 260) * sc)
            pts = [(x, top)]
            for k in range(1, 28):
                pts.append((int(np.clip(x + math.sin(k * 0.55 + x) * 8 * sc, 0, w - 1)), int(np.clip(top + k * length / 27, 0, h - 1))))
            val = rng.uniform(0.38, 0.94)
            _polyline(CC, pts, min(0.99, val + 0.04), 1)
            _polyline(M, pts, val, 1)
            _polyline(R, pts, val * 0.18, 1)
            if rng.random() < 0.60:
                end = pts[-1]
                _cv2.circle(CC, end, max(2, int(rng.uniform(3, 9) * sc)), min(0.99, val + 0.06), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _pangolin_obsidian_armor(shape, seed, sm, name="pangolin_obsidian_armor"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82207)
    M, R, CC = _base(shape, int(seed), 0.17, 0.13, 0.24, 0.07)
    sc = _scale(shape)
    if _CV2_OK:
        step_x, step_y = max(18, int(48 * sc)), max(14, int(38 * sc))
        for row, y in enumerate(range(-step_y, h + step_y, step_y)):
            off = step_x // 2 if row % 2 else 0
            for x in range(-step_x, w + step_x, step_x):
                cx = x + off
                pts = np.asarray([[cx, y - step_y // 2], [cx + step_x // 2, y], [cx + step_x // 4, y + step_y // 2], [cx, y + int(step_y * 0.72)], [cx - step_x // 4, y + step_y // 2], [cx - step_x // 2, y]], dtype=np.int32)
                val = float(rng.choice([0.24, 0.36, 0.50, 0.66, 0.82, 0.96]))
                _cv2.fillPoly(M, [pts], val * 0.58, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], min(0.98, val * 0.78), lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [pts], True, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [pts], True, val * 0.22, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _oil_slick_islands(shape, seed, sm, name="oil_slick_islands"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82208)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base = _normalize(np.sin(xx * 0.028 + np.sin(yy * 0.012) * 4.0) + np.cos(yy * 0.020))
    M = (0.16 + base * 0.58).astype(np.float32)
    R = (0.06 + (1 - base) * 0.24).astype(np.float32)
    CC = (0.30 + _normalize(np.sin(xx * 0.046 - yy * 0.033)) * 0.62).astype(np.float32)
    if _CV2_OK:
        sc = _scale(shape)
        for _ in range(_count(shape, 760, 120)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ax, ay = max(10, int(rng.uniform(16, 54) * sc)), max(5, int(rng.uniform(7, 24) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.52, 0.98)
            _cv2.ellipse(CC, (cx, cy), (ax, ay), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (ax, ay), rot, 0, 360, val * 0.72, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (ax, ay), rot, 0, 360, val * 0.12, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _jasper_burl_topography(shape, seed, sm, name="jasper_burl_topography"):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(int(seed) + 82209)
    warp = _normalize(multi_scale_noise(shape, [2.5, 8, 19], [0.46, 0.34, 0.20], int(seed) + 240))
    strata = _normalize(np.sin(yy * 0.040 + np.sin(xx * 0.009) * 5.5 + warp * 7.0))
    M = (0.22 + strata * 0.45).astype(np.float32)
    R = (0.18 + _normalize(np.cos(yy * 0.032 + warp * 5.0)) * 0.32).astype(np.float32)
    CC = (0.16 + _normalize(np.sin(xx * 0.018 - yy * 0.014 + warp * 6.0)) * 0.38).astype(np.float32)
    if _CV2_OK:
        sc = _scale(shape)
        for k in range(54):
            y0 = int((k - 5) * h / 44)
            pts = []
            for x in range(0, w, max(5, int(8 * sc))):
                y = int(y0 + math.sin(x * 0.012 + k) * 38 * sc + math.sin(x * 0.035 + k * 1.7) * 9 * sc)
                pts.append((x, np.clip(y, 0, h - 1)))
            _polyline(M, pts, rng.uniform(0.34, 0.86), 1)
            _polyline(CC, pts, rng.uniform(0.18, 0.62), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_aniso_grain_deep(shape, seed, sm, **kwargs): return _damascus_satin_bands(shape, seed + 301, sm)
def rescue_buffer_swirl(shape, seed, sm, **kwargs): return _orbital_buffer_moons(shape, seed + 302, sm)
def rescue_engine_bay_grime(shape, seed, sm, **kwargs): return _oil_gasket_bolt_grime(shape, seed + 303, sm)
def rescue_cloud_wisps_warm(shape, seed, sm, **kwargs): return _ember_moth_veil(shape, seed + 304, sm)
def rescue_mother_of_pearl_inlay(shape, seed, sm, **kwargs): return _nacre_shard_inlay(shape, seed + 305, sm)
def rescue_paint_drip_edge(shape, seed, sm, **kwargs): return _enamel_drip_curtain(shape, seed + 306, sm)
def rescue_pangolin_armor(shape, seed, sm, **kwargs): return _pangolin_obsidian_armor(shape, seed + 307, sm)
def rescue_spec_oil_film_thick(shape, seed, sm, **kwargs): return _oil_slick_islands(shape, seed + 308, sm)
def rescue_spec_wood_grain_fine(shape, seed, sm, **kwargs): return _jasper_burl_topography(shape, seed + 309, sm)


def _turbine_buffer_roses(shape, seed, sm, name="turbine_buffer_roses"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82301)
    M, R, CC = _base(shape, int(seed), 0.20, 0.14, 0.34, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(48, int(132 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx = x + pitch // 2 + int(math.sin(y * 0.015) * 12 * sc)
                cy = y + pitch // 2
                for blade in range(7):
                    a0 = blade * math.tau / 7 + rng.uniform(-0.08, 0.08)
                    pts = []
                    for i in range(32):
                        t = i / 31
                        rr = (8 + 46 * t) * sc
                        a = a0 + t * 0.72
                        pts.append((int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr)))
                    val = rng.uniform(0.46, 0.96)
                    _polyline(M, pts, val, 1)
                    _polyline(CC, pts, min(0.99, val + 0.06), 1)
                    _polyline(R, pts, val * 0.16, 1)
                _cv2.circle(CC, (cx, cy), max(3, int(8 * sc)), 0.94, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _engine_gasket_map(shape, seed, sm, name="engine_gasket_map"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82302)
    M, R, CC = _base(shape, int(seed), 0.12, 0.34, 0.10, 0.08)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 520, 90)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(10, int(rng.uniform(18, 44) * sc)), max(5, int(rng.uniform(8, 22) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.46, 0.94)
            _cv2.ellipse(R, (cx, cy), (rx, ry), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 0, 360, val * 0.48, 1, lineType=_cv2.LINE_AA)
            for k in range(3):
                a = rot * math.pi / 180 + k * math.tau / 3
                p1 = (int(cx + math.cos(a) * rx * 0.25), int(cy + math.sin(a) * ry * 0.25))
                p2 = (int(cx + math.cos(a) * rx * 1.35), int(cy + math.sin(a) * ry * 1.35))
                _cv2.line(R, p1, p2, rng.uniform(0.38, 0.88), 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 1800, 260)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(R, (cx, cy), max(1, int(rng.uniform(2, 5) * sc)), rng.uniform(0.42, 0.92), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _enamel_drip_bead_curtain(shape, seed, sm, name="enamel_drip_bead_curtain"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82303)
    M, R, CC = _base(shape, int(seed), 0.15, 0.15, 0.30, 0.07)
    sc = _scale(shape)
    if _CV2_OK:
        for x in range(0, w, max(6, int(17 * sc))):
            top = int(rng.integers(-40, h))
            length = int(rng.uniform(70, 360) * sc)
            pts = []
            for k in range(36):
                pts.append((int(np.clip(x + math.sin(k * 0.45 + x) * 7 * sc, 0, w - 1)), int(np.clip(top + k * length / 35, 0, h - 1))))
            val = rng.uniform(0.42, 0.96)
            _polyline(CC, pts, min(0.99, val + 0.04), 1)
            _polyline(M, pts, val, 1)
            _polyline(R, pts, val * 0.16, 1)
            for p in pts[8::12]:
                _cv2.circle(CC, p, max(2, int(rng.uniform(3, 8) * sc)), min(0.99, val + 0.08), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _pangolin_plate_ribbons(shape, seed, sm, name="pangolin_plate_ribbons"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82304)
    M, R, CC = _base(shape, int(seed), 0.16, 0.13, 0.25, 0.07)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-3, 12):
            x0 = int((band - 2) * w / 7)
            for i in range(-4, 50):
                cy = int(i * h / 45)
                cx = int(x0 + cy * 0.34 + math.sin(i * 0.55 + band) * 34 * sc)
                r = int(rng.uniform(18, 36) * sc)
                pts = np.asarray([[cx, cy - r], [cx + int(r * 0.72), cy - int(r * 0.15)], [cx + int(r * 0.44), cy + int(r * 0.76)], [cx, cy + r], [cx - int(r * 0.44), cy + int(r * 0.76)], [cx - int(r * 0.72), cy - int(r * 0.15)]], dtype=np.int32)
                val = rng.uniform(0.30, 0.94)
                _cv2.fillPoly(M, [pts], val * 0.58, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], min(0.98, val * 0.82), lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [pts], True, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [pts], True, val * 0.22, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_buffer_swirl(shape, seed, sm, **kwargs): return _turbine_buffer_roses(shape, seed + 401, sm)
def rescue_engine_bay_grime(shape, seed, sm, **kwargs): return _engine_gasket_map(shape, seed + 402, sm)
def rescue_paint_drip_edge(shape, seed, sm, **kwargs): return _enamel_drip_bead_curtain(shape, seed + 403, sm)
def rescue_pangolin_armor(shape, seed, sm, **kwargs): return _pangolin_plate_ribbons(shape, seed + 404, sm)


def _random_buffer_holograms(shape, seed, sm, name="random_buffer_holograms"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82401)
    M, R, CC = _base(shape, int(seed), 0.19, 0.13, 0.33, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1900, 300)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(7, int(rng.uniform(11, 31) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.42, 0.98)
            for k in range(rng.integers(1, 4)):
                start = rng.uniform(0, 260)
                span = rng.uniform(60, 220)
                axes = (max(3, r - k * max(1, int(4 * sc))), max(2, int((r - k * 2) * rng.uniform(0.30, 0.72))))
                _cv2.ellipse(M, (cx, cy), axes, rot + k * 23, start, start + span, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), axes, rot + k * 23, start, start + span, min(0.99, val + 0.07), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), axes, rot + k * 23, start, start + span, val * 0.16, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.22:
                _draw_glint(M, R, CC, cx, cy, max(2, int(5 * sc)), (0.88, 0.24, 0.94))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _overlap_pangolin_shields(shape, seed, sm, name="overlap_pangolin_shields"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82402)
    M, R, CC = _base(shape, int(seed), 0.15, 0.12, 0.23, 0.07)
    sc = _scale(shape)
    if _CV2_OK:
        step_x, step_y = max(18, int(46 * sc)), max(13, int(34 * sc))
        for row, y in enumerate(range(-step_y, h + step_y, step_y)):
            off = step_x // 2 if row % 2 else 0
            for x in range(-step_x, w + step_x, step_x):
                cx = x + off + int(math.sin(y * 0.018) * 10 * sc)
                cy = y
                r = int(rng.uniform(15, 25) * sc)
                pts = np.asarray([
                    [cx, cy - r],
                    [cx + int(r * 0.82), cy - int(r * 0.18)],
                    [cx + int(r * 0.55), cy + int(r * 0.62)],
                    [cx, cy + int(r * 0.92)],
                    [cx - int(r * 0.55), cy + int(r * 0.62)],
                    [cx - int(r * 0.82), cy - int(r * 0.18)],
                ], dtype=np.int32)
                val = rng.uniform(0.26, 0.92)
                _cv2.fillPoly(M, [pts], val * 0.58, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], min(0.98, val * 0.76), lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [pts], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [pts], True, val * 0.20, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, tuple(pts[0]), tuple(pts[3]), min(0.98, val + 0.04), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_buffer_swirl(shape, seed, sm, **kwargs): return _random_buffer_holograms(shape, seed + 501, sm)
def rescue_pangolin_armor(shape, seed, sm, **kwargs): return _overlap_pangolin_shields(shape, seed + 502, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass3:
# Owner verdict: too many rescued cards still read as weak cousin variants,
# speck fields, or simple line/noise effects. This pass deliberately gives
# each remaining weak card its own construction grammar before thumbnail bake.
def _cassette_prism_equalizer(shape, seed, sm, name="cassette_prism_equalizer"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82501)
    M, R, CC = _base(shape, int(seed), 0.12, 0.10, 0.25, 0.04)
    sc = _scale(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    bands = _normalize(np.sin((xx + yy * 0.14) * 0.035) + np.sin((xx - yy * 0.22) * 0.071))
    M[:] = np.maximum(M, 0.15 + bands * 0.26)
    CC[:] = np.maximum(CC, 0.26 + _normalize(np.sin(xx * 0.095 + yy * 0.018)) * 0.36)
    if _CV2_OK:
        pitch_x = max(42, int(118 * sc))
        pitch_y = max(38, int(96 * sc))
        for y in range(-pitch_y, h + pitch_y, pitch_y):
            for x in range(-pitch_x, w + pitch_x, pitch_x):
                cx = x + pitch_x // 2
                cy = y + pitch_y // 2
                for k, rad in enumerate((34, 25, 16, 8)):
                    r = max(3, int(rad * sc))
                    val = [0.96, 0.78, 0.56, 0.34][k]
                    _cv2.ellipse(M, (cx, cy), (r, max(3, int(r * 0.42))), -16, 205, 340, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(CC, (cx, cy), (r, max(3, int(r * 0.42))), -16, 205, 340, min(0.99, val + 0.03), 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(R, (cx, cy), (r, max(2, int(r * 0.30))), -16, 205, 340, val * 0.18, 1, lineType=_cv2.LINE_AA)
                for b in range(5):
                    bh = int(rng.uniform(7, 28) * sc)
                    bx = cx - int(23 * sc) + b * max(5, int(10 * sc))
                    _cv2.rectangle(CC, (bx, cy - bh), (bx + max(2, int(4 * sc)), cy + bh), rng.uniform(0.38, 0.95), 1, lineType=_cv2.LINE_AA)
                    _cv2.rectangle(M, (bx, cy - bh), (bx + max(2, int(4 * sc)), cy + bh), rng.uniform(0.32, 0.88), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _wet_clearcoat_speed_ribbons(shape, seed, sm, name="wet_clearcoat_speed_ribbons"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82502)
    M, R, CC = _base(shape, int(seed), 0.10, 0.07, 0.36, 0.03)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-6, 14):
            x0 = int((band - 2) * w / 9)
            pts = []
            for i in range(96):
                y = int(i * h / 95)
                x = int(x0 + y * 0.42 + math.sin(i * 0.22 + band) * 24 * sc)
                pts.append((x, y))
            for off, val in ((-6, 0.42), (-2, 0.74), (2, 0.96), (7, 0.56)):
                shifted = [(x + int(off * sc), y) for x, y in pts]
                _polyline(CC, shifted, val, 1)
                _polyline(M, shifted, val * 0.66, 1)
                _polyline(R, shifted, val * 0.10, 1)
            for x, y in pts[6::11]:
                rr = max(2, int(rng.uniform(3, 8) * sc))
                _cv2.ellipse(CC, (x, y), (rr * 2, rr), -28, 0, 360, rng.uniform(0.68, 0.99), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (x + rr // 2, y - rr // 3), max(1, rr // 2), rng.uniform(0.72, 0.98), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _torn_tape_feather_edge(shape, seed, sm, name="torn_tape_feather_edge"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82503)
    M, R, CC = _base(shape, int(seed), 0.18, 0.22, 0.16, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-3, 10):
            y0 = int((lane - 1) * h / 6)
            pts = []
            for i in range(0, w + 24, max(5, int(9 * sc))):
                y = int(y0 + i * 0.18 + math.sin(i * 0.030 + lane) * 23 * sc + rng.uniform(-8, 8) * sc)
                pts.append((i, y))
            _polyline(M, pts, rng.uniform(0.55, 0.94), 1)
            _polyline(R, pts, rng.uniform(0.20, 0.72), 1)
            _polyline(CC, pts, rng.uniform(0.32, 0.86), 1)
            for x, y in pts[1::2]:
                tooth = int(rng.uniform(5, 18) * sc)
                p2 = (x + int(rng.uniform(-4, 6) * sc), y + tooth)
                _cv2.line(M, (x, y), p2, rng.uniform(0.36, 0.92), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x, y), p2, rng.uniform(0.24, 0.76), 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.45:
                    _cv2.circle(CC, p2, max(1, int(rng.uniform(2, 5) * sc)), rng.uniform(0.48, 0.95), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _cursed_ceramic_crackle(shape, seed, sm, name="cursed_ceramic_crackle"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82504)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    glaze = _normalize(np.sin(xx * 0.018 + np.sin(yy * 0.011) * 2.4) + np.cos(yy * 0.021))
    M = (0.18 + glaze * 0.32).astype(np.float32)
    R = (0.08 + (1 - glaze) * 0.24).astype(np.float32)
    CC = (0.22 + glaze * 0.48).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1150, 180)):
            x = int(rng.integers(-20, w + 20))
            y = int(rng.integers(-20, h + 20))
            pts = [(x, y)]
            steps = int(rng.integers(4, 12))
            ang = rng.uniform(0, math.tau)
            for _s in range(steps):
                ang += rng.uniform(-0.75, 0.75)
                x += int(math.cos(ang) * rng.uniform(8, 24) * sc)
                y += int(math.sin(ang) * rng.uniform(8, 24) * sc)
                pts.append((x, y))
            val = rng.uniform(0.36, 0.96)
            _polyline(M, pts, val, 1)
            _polyline(CC, pts, min(0.99, val + 0.04), 1)
            _polyline(R, pts, val * 0.18, 1)
            if rng.random() < 0.34:
                _draw_glint(M, R, CC, pts[-1][0], pts[-1][1], max(2, int(5 * sc)), (0.82, 0.18, 0.92))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _quartz_rosette_colonies(shape, seed, sm, name="quartz_rosette_colonies"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82505)
    M, R, CC = _base(shape, int(seed), 0.13, 0.12, 0.25, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 230, 42)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            spokes = int(rng.integers(7, 16))
            for k in range(spokes):
                ang = k * math.tau / spokes + rng.uniform(-0.12, 0.12)
                length = rng.uniform(15, 44) * sc
                width = rng.uniform(3, 8) * sc
                tip = (int(cx + math.cos(ang) * length), int(cy + math.sin(ang) * length))
                left = (int(cx + math.cos(ang + math.pi / 2) * width), int(cy + math.sin(ang + math.pi / 2) * width))
                right = (int(cx - math.cos(ang + math.pi / 2) * width), int(cy - math.sin(ang + math.pi / 2) * width))
                poly = np.asarray([left, tip, right], dtype=np.int32)
                val = rng.uniform(0.34, 0.98)
                _cv2.fillPoly(M, [poly], val * 0.46, lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [poly], True, val, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [poly], True, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [poly], True, val * 0.16, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), max(2, int(5 * sc)), 0.92, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _lifting_vinyl_curl_tabs(shape, seed, sm, name="lifting_vinyl_curl_tabs"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82506)
    M, R, CC = _base(shape, int(seed), 0.16, 0.15, 0.30, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-2, 11):
            for i in range(-3, 28):
                cx = int((i * 83 + lane * 41) * sc) % (w + 80) - 40
                cy = int((lane * h / 7) + math.sin(i * 0.85 + lane) * 34 * sc + i * 14 * sc)
                if not (-40 <= cy <= h + 40):
                    continue
                rx, ry = max(5, int(rng.uniform(8, 20) * sc)), max(3, int(rng.uniform(4, 10) * sc))
                rot = rng.uniform(-35, 35)
                val = rng.uniform(0.45, 0.98)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 220, 65, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 220, 65, val * 0.72, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx - rx, cy), (cx + rx, cy + int(ry * 0.4)), val * 0.16, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.55:
                    _cv2.circle(M, (cx + rx // 2, cy - ry // 3), max(1, int(2 * sc)), min(0.99, val + 0.05), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _diamond_cut_frost_lattice(shape, seed, sm, name="diamond_cut_frost_lattice"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82507)
    M, R, CC = _base(shape, int(seed), 0.14, 0.09, 0.28, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(18, int(42 * sc)), max(15, int(34 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx = x + off
                pts = np.asarray([[cx, y - sy // 2], [cx + sx // 2, y], [cx, y + sy // 2], [cx - sx // 2, y]], dtype=np.int32)
                val = rng.uniform(0.30, 0.98)
                _cv2.polylines(M, [pts], True, val, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, tuple(pts[0]), tuple(pts[2]), val * 0.14, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.18:
                    _draw_glint(M, R, CC, cx, y, max(2, int(5 * sc)), (0.94, 0.16, 0.98))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _forged_carbon_obsidian_chips(shape, seed, sm, name="forged_carbon_obsidian_chips"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82508)
    M, R, CC = _base(shape, int(seed), 0.09, 0.13, 0.17, 0.08)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 2600, 380)):
            cx, cy = int(rng.integers(-20, w + 20)), int(rng.integers(-20, h + 20))
            n = int(rng.integers(3, 7))
            rad = rng.uniform(6, 22) * sc
            pts = []
            for k in range(n):
                a = k * math.tau / n + rng.uniform(-0.34, 0.34)
                rr = rad * rng.uniform(0.55, 1.25)
                pts.append((int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr)))
            poly = np.asarray(pts, dtype=np.int32)
            val = rng.choice([0.18, 0.24, 0.32, 0.44, 0.58, 0.74, 0.88])
            _cv2.fillPoly(M, [poly], float(val), lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, float(min(0.98, val + rng.uniform(0.08, 0.22))), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(R, [poly], True, float(val * 0.25), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _thumbprint_buff_whorls(shape, seed, sm, name="thumbprint_buff_whorls"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82509)
    M, R, CC = _base(shape, int(seed), 0.14, 0.11, 0.28, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(82, int(180 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx = x + int(rng.uniform(20, pitch - 20))
                cy = y + int(rng.uniform(20, pitch - 20))
                rot = rng.uniform(-35, 35)
                for k in range(9):
                    rx = max(7, int((13 + k * 7) * sc))
                    ry = max(4, int((7 + k * 4) * sc))
                    start = 20 + k * 13
                    end = 315 - k * 7
                    val = rng.uniform(0.34, 0.94)
                    _cv2.ellipse(M, (cx, cy), (rx, ry), rot, start, end, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, start, end, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(R, (cx, cy), (rx, ry), rot, start, end, val * 0.14, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _comet_orbit_cartography(shape, seed, sm, name="comet_orbit_cartography"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82510)
    M, R, CC = _base(shape, int(seed), 0.11, 0.10, 0.22, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 320, 60)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(16, int(rng.uniform(28, 86) * sc)), max(8, int(rng.uniform(12, 42) * sc))
            rot = rng.uniform(0, 180)
            start = rng.uniform(0, 320)
            span = rng.uniform(65, 240)
            val = rng.uniform(0.40, 0.98)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, start, start + span, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, start, start + span, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rx, ry), rot, start, start + span, val * 0.12, 1, lineType=_cv2.LINE_AA)
            a = math.radians(rot + start + span)
            head = (int(cx + math.cos(a) * rx), int(cy + math.sin(a) * ry))
            _draw_glint(M, R, CC, head[0], head[1], max(2, int(6 * sc)), (0.92, 0.16, 0.98))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _foil_bomber_flake_panels(shape, seed, sm, name="foil_bomber_flake_panels"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82511)
    M, R, CC = _base(shape, int(seed), 0.16, 0.10, 0.24, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for y in range(0, h, max(42, int(110 * sc))):
            _cv2.line(CC, (0, y), (w, y + int(math.sin(y * 0.01) * 18 * sc)), 0.36, 1, lineType=_cv2.LINE_AA)
        for x in range(0, w, max(54, int(142 * sc))):
            _cv2.line(M, (x, 0), (x + int(math.sin(x * 0.01) * 20 * sc), h), 0.42, 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 1800, 260)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rw, rh = max(2, int(rng.uniform(3, 10) * sc)), max(1, int(rng.uniform(2, 7) * sc))
            rot = rng.uniform(0, 180)
            rect = ((cx, cy), (rw, rh), rot)
            pts = _cv2.boxPoints(rect).astype(np.int32)
            val = rng.uniform(0.32, 0.98)
            _cv2.fillPoly(CC, [pts], val, lineType=_cv2.LINE_AA)
            _cv2.polylines(M, [pts], True, val * 0.75, 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(R, [pts], True, val * 0.12, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_abstract_retro_wave(shape, seed, sm, **kwargs): return _cassette_prism_equalizer(shape, seed + 601, sm)
def rescue_cc_gloss_stripe(shape, seed, sm, **kwargs): return _wet_clearcoat_speed_ribbons(shape, seed + 602, sm)
def rescue_cc_masking_edge(shape, seed, sm, **kwargs): return _torn_tape_feather_edge(shape, seed + 603, sm)
def rescue_crackle_network(shape, seed, sm, **kwargs): return _cursed_ceramic_crackle(shape, seed + 604, sm)
def rescue_crystal_growth(shape, seed, sm, **kwargs): return _quartz_rosette_colonies(shape, seed + 605, sm)
def rescue_decal_lift_edge(shape, seed, sm, **kwargs): return _lifting_vinyl_curl_tabs(shape, seed + 606, sm)
def rescue_diamond_dust(shape, seed, sm, **kwargs): return _diamond_cut_frost_lattice(shape, seed + 607, sm)
def rescue_forged_carbon_chip(shape, seed, sm, **kwargs): return _forged_carbon_obsidian_chips(shape, seed + 608, sm)
def rescue_hand_polished(shape, seed, sm, **kwargs): return _thumbprint_buff_whorls(shape, seed + 609, sm)
def rescue_sparkle_comet(shape, seed, sm, **kwargs): return _comet_orbit_cartography(shape, seed + 610, sm)
def rescue_flake_scatter(shape, seed, sm, **kwargs): return _foil_bomber_flake_panels(shape, seed + 611, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass3-iteration2:
# Visual self-check rejected the first pass for several cards that still read
# as sparse lines/dots instead of complete finish systems. These replace them
# with denser, more recognizable thumbnail silhouettes made from fine marks.
def _lens_wet_clear_racing_lanes(shape, seed, sm, name="lens_wet_clear_racing_lanes"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82601)
    M, R, CC = _base(shape, int(seed), 0.10, 0.07, 0.32, 0.025)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-5, 15):
            x0 = int((lane - 3) * w / 8)
            spine = []
            for i in range(140):
                y = int(i * h / 139)
                x = int(x0 + y * 0.36 + math.sin(i * 0.14 + lane) * 21 * sc)
                spine.append((x, y))
            for off in range(-18, 19, 4):
                val = 0.38 + 0.58 * (1.0 - abs(off) / 22.0)
                shifted = [(x + int(off * sc), y) for x, y in spine]
                _polyline(CC, shifted, min(0.99, val), 1)
                _polyline(M, shifted, val * 0.54, 1)
            for x, y in spine[4::8]:
                if rng.random() < 0.8:
                    rr = max(2, int(rng.uniform(4, 11) * sc))
                    _cv2.ellipse(CC, (x + int(rng.uniform(-14, 14) * sc), y), (rr * 2, rr), -24, 0, 360, rng.uniform(0.62, 0.99), 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(M, (x + rr, y - rr // 2), max(1, rr // 2), rng.uniform(0.70, 0.98), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _masking_tape_torn_panel_edges(shape, seed, sm, name="masking_tape_torn_panel_edges"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82602)
    M, R, CC = _base(shape, int(seed), 0.18, 0.22, 0.18, 0.055)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-2, 8):
            base_y = int(lane * h / 5)
            top = []
            bot = []
            for i in range(-10, w + 20, max(4, int(8 * sc))):
                wave = math.sin(i * 0.025 + lane) * 25 * sc + math.sin(i * 0.071 + lane * 2) * 7 * sc
                rag = rng.uniform(-6, 6) * sc
                top.append((i, int(base_y + wave + rag)))
                bot.append((i, int(base_y + wave + rag + rng.uniform(14, 29) * sc)))
            strip = np.asarray(top + list(reversed(bot)), dtype=np.int32)
            fill = rng.uniform(0.20, 0.52)
            _cv2.fillPoly(CC, [strip], fill, lineType=_cv2.LINE_AA)
            _polyline(M, top, rng.uniform(0.55, 0.95), 1)
            _polyline(M, bot, rng.uniform(0.45, 0.88), 1)
            _polyline(R, top, rng.uniform(0.18, 0.58), 1)
            for x, y in top[::2] + bot[1::2]:
                tooth = int(rng.uniform(4, 16) * sc)
                _cv2.line(M, (x, y), (x + int(rng.uniform(-6, 6) * sc), y + tooth), rng.uniform(0.38, 0.96), 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.35:
                    _cv2.circle(CC, (x, y + tooth), max(1, int(rng.uniform(2, 5) * sc)), rng.uniform(0.50, 0.94), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _quartz_cluster_garden(shape, seed, sm, name="quartz_cluster_garden"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82603)
    M, R, CC = _base(shape, int(seed), 0.12, 0.11, 0.22, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(54, int(118 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx = x + int(rng.uniform(12, pitch - 12))
                cy = y + int(rng.uniform(12, pitch - 12))
                for ring, count in enumerate((9, 14, 19)):
                    radius = (9 + ring * 12) * sc
                    for k in range(count):
                        if rng.random() < 0.55 - ring * 0.08:
                            continue
                        ang = k * math.tau / count + rng.uniform(-0.18, 0.18)
                        bx = int(cx + math.cos(ang) * radius)
                        by = int(cy + math.sin(ang) * radius)
                        length = rng.uniform(12, 34) * sc
                        width = rng.uniform(3, 8) * sc
                        tip = (int(bx + math.cos(ang) * length), int(by + math.sin(ang) * length))
                        left = (int(bx + math.cos(ang + math.pi / 2) * width), int(by + math.sin(ang + math.pi / 2) * width))
                        right = (int(bx - math.cos(ang + math.pi / 2) * width), int(by - math.sin(ang + math.pi / 2) * width))
                        poly = np.asarray([left, tip, right], dtype=np.int32)
                        val = rng.uniform(0.34, 0.99)
                        _cv2.fillPoly(M, [poly], val * 0.36, lineType=_cv2.LINE_AA)
                        _cv2.polylines(M, [poly], True, val, 1, lineType=_cv2.LINE_AA)
                        _cv2.polylines(CC, [poly], True, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                _draw_glint(M, R, CC, cx, cy, max(2, int(7 * sc)), (0.84, 0.16, 0.94))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _forged_carbon_torn_leaf_plate(shape, seed, sm, name="forged_carbon_torn_leaf_plate"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82604)
    M, R, CC = _base(shape, int(seed), 0.07, 0.12, 0.16, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1150, 180)):
            cx, cy = int(rng.integers(-10, w + 10)), int(rng.integers(-10, h + 10))
            long = rng.uniform(12, 38) * sc
            short = rng.uniform(4, 13) * sc
            ang = rng.uniform(0, math.tau)
            pts = []
            for k, (da, rr) in enumerate(((-0.25, 1.0), (0.18, 0.65), (math.pi - 0.20, 1.0), (math.pi + 0.28, 0.55))):
                a = ang + da
                pts.append((int(cx + math.cos(a) * long * rr + math.cos(a + math.pi / 2) * short * (1 if k % 2 else -1)),
                            int(cy + math.sin(a) * long * rr + math.sin(a + math.pi / 2) * short * (1 if k % 2 else -1))))
            poly = np.asarray(pts, dtype=np.int32)
            val = float(rng.choice([0.16, 0.24, 0.34, 0.48, 0.62, 0.78, 0.92]))
            _cv2.fillPoly(M, [poly], val * 0.72, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, pts[0], pts[2], val * 0.18, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _hand_buff_fingerprint_field(shape, seed, sm, name="hand_buff_fingerprint_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82605)
    M, R, CC = _base(shape, int(seed), 0.14, 0.10, 0.27, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(46, int(104 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx = x + pitch // 2 + int(math.sin(y * 0.02) * 12 * sc)
                cy = y + pitch // 2
                rot = rng.uniform(-30, 30)
                for k in range(13):
                    rx = max(5, int((8 + k * 4.2) * sc))
                    ry = max(3, int((4 + k * 2.5) * sc))
                    start = 10 + k * 5
                    end = 335 - k * 4
                    val = rng.uniform(0.28, 0.96)
                    _cv2.ellipse(M, (cx, cy), (rx, ry), rot, start, end, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, start, end, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
                for _ in range(3):
                    _cv2.line(CC, (cx + int(rng.uniform(-28, 28) * sc), cy - int(25 * sc)), (cx + int(rng.uniform(-28, 28) * sc), cy + int(25 * sc)), rng.uniform(0.30, 0.75), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_cc_gloss_stripe(shape, seed, sm, **kwargs): return _lens_wet_clear_racing_lanes(shape, seed + 701, sm)
def rescue_cc_masking_edge(shape, seed, sm, **kwargs): return _masking_tape_torn_panel_edges(shape, seed + 702, sm)
def rescue_crystal_growth(shape, seed, sm, **kwargs): return _quartz_cluster_garden(shape, seed + 703, sm)
def rescue_forged_carbon_chip(shape, seed, sm, **kwargs): return _forged_carbon_torn_leaf_plate(shape, seed + 704, sm)
def rescue_hand_polished(shape, seed, sm, **kwargs): return _hand_buff_fingerprint_field(shape, seed + 705, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass3-iteration3:
# Visual self-check rejected the grid-stamped hand-polish whorls. Hand polish
# needs irregular overlapping buff marks, not a tiled symbol field.
def _hand_polished_random_buff_blooms(shape, seed, sm, name="hand_polished_random_buff_blooms"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82701)
    M, R, CC = _base(shape, int(seed), 0.13, 0.10, 0.25, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1250, 210)):
            cx, cy = int(rng.integers(-15, w + 15)), int(rng.integers(-15, h + 15))
            rot = rng.uniform(0, 180)
            loops = int(rng.integers(2, 7))
            for k in range(loops):
                rx = max(4, int(rng.uniform(8, 28) * sc))
                ry = max(2, int(rx * rng.uniform(0.22, 0.58)))
                start = rng.uniform(0, 320)
                span = rng.uniform(40, 170)
                val = rng.uniform(0.30, 0.95)
                dx = int(rng.uniform(-10, 10) * sc)
                dy = int(rng.uniform(-10, 10) * sc)
                _cv2.ellipse(M, (cx + dx, cy + dy), (rx, ry), rot + rng.uniform(-20, 20), start, start + span, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx + dx, cy + dy), (rx, ry), rot + rng.uniform(-20, 20), start, start + span, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx + dx, cy + dy), (rx, ry), rot, start, start + span, val * 0.12, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.62:
                length = int(rng.uniform(8, 24) * sc)
                a = math.radians(rot + rng.uniform(-30, 30))
                _cv2.line(CC, (cx, cy), (int(cx + math.cos(a) * length), int(cy + math.sin(a) * length)), rng.uniform(0.34, 0.86), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_hand_polished(shape, seed, sm, **kwargs): return _hand_polished_random_buff_blooms(shape, seed + 801, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass4:
# Owner doctrine check on the full 40-card sheet still showed too many dot
# fields, plain stripes, and generic colored noise. This pass replaces those
# with recognizable, separate material grammars built from fine marks.
def _brake_rotor_soot_halos(shape, seed, sm, name="brake_rotor_soot_halos"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82801)
    M, R, CC = _base(shape, int(seed), 0.09, 0.34, 0.10, 0.05)
    sc = _scale(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    sweep = _normalize(np.sin(xx * 0.030 + yy * 0.010) + np.sin((xx - yy) * 0.018))
    R[:] = np.maximum(R, 0.22 + sweep * 0.28)
    if _CV2_OK:
        for _ in range(_count(shape, 520, 90)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            rx = max(9, int(rng.uniform(16, 42) * sc))
            ry = max(4, int(rng.uniform(7, 18) * sc))
            val = rng.uniform(0.32, 0.92)
            _cv2.ellipse(R, (cx, cy), (rx, ry), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 35, 240, val * 0.58, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.5:
                _cv2.line(R, (cx - rx, cy), (cx + rx, cy + int(ry * 0.4)), rng.uniform(0.26, 0.78), 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 2200, 320)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(1.5, 4.5) * sc))
            _cv2.circle(R, (cx, cy), rr, rng.uniform(0.24, 0.86), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _sumi_enamel_slash_field(shape, seed, sm, name="sumi_enamel_slash_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82802)
    M, R, CC = _base(shape, int(seed), 0.15, 0.12, 0.20, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-4, 14):
            x0 = int((band - 3) * w / 8)
            for i in range(-4, 42):
                y = int(i * h / 36 + rng.uniform(-18, 18) * sc)
                x = int(x0 + y * 0.28 + math.sin(i * 0.8 + band) * 34 * sc)
                length = rng.uniform(13, 33) * sc
                angle = rng.uniform(-0.85, -0.20)
                p1 = (x, y)
                p2 = (int(x + math.cos(angle) * length), int(y + math.sin(angle) * length))
                val = rng.uniform(0.32, 0.98)
                _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, p1, p2, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.32:
                    _cv2.circle(M, p1, max(1, int(rng.uniform(2, 5) * sc)), val * 0.8, -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _clearcoat_crater_lens_cells(shape, seed, sm, name="clearcoat_crater_lens_cells"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82803)
    M, R, CC = _base(shape, int(seed), 0.08, 0.07, 0.36, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(30, int(70 * sc))
        for row, y in enumerate(range(-pitch, h + pitch, pitch)):
            off = pitch // 2 if row % 2 else 0
            for x in range(-pitch, w + pitch, pitch):
                if rng.random() < 0.36:
                    continue
                cx = x + off + int(rng.uniform(-7, 7) * sc)
                cy = y + int(rng.uniform(-7, 7) * sc)
                rx = max(5, int(rng.uniform(8, 19) * sc))
                ry = max(3, int(rx * rng.uniform(0.55, 0.95)))
                val = rng.uniform(0.42, 0.96)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, val * 0.44, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx - rx // 3, cy - ry // 3), max(1, int(2 * sc)), min(0.99, val + 0.08), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), max(1, int(2 * sc)), val * 0.12, -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _rotary_spot_polish_mandala(shape, seed, sm, name="rotary_spot_polish_mandala"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82804)
    M, R, CC = _base(shape, int(seed), 0.13, 0.09, 0.30, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 360, 70)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            petals = int(rng.integers(5, 11))
            base_rot = rng.uniform(0, math.tau)
            for p in range(petals):
                ang = base_rot + p * math.tau / petals
                r = rng.uniform(10, 28) * sc
                px = int(cx + math.cos(ang) * r * 0.45)
                py = int(cy + math.sin(ang) * r * 0.45)
                val = rng.uniform(0.34, 0.98)
                _cv2.ellipse(CC, (px, py), (max(3, int(r * 0.55)), max(2, int(r * 0.18))), math.degrees(ang), 0, 330, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (px, py), (max(3, int(r * 0.55)), max(2, int(r * 0.18))), math.degrees(ang), 0, 330, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.45:
                _draw_glint(M, R, CC, cx, cy, max(2, int(4 * sc)), (0.84, 0.12, 0.94))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _ember_spirit_flame_lace(shape, seed, sm, name="ember_spirit_flame_lace"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82805)
    M, R, CC = _base(shape, int(seed), 0.24, 0.08, 0.08, 0.055)
    sc = _scale(shape)
    if _CV2_OK:
        for col in range(-3, 12):
            x0 = int((col - 2) * w / 7)
            for i in range(-2, 36):
                cx = int(x0 + i * 19 * sc + math.sin(i * 0.6 + col) * 38 * sc)
                cy = int(i * h / 32 + rng.uniform(-20, 20) * sc)
                pts = []
                for k in range(18):
                    t = k / 17
                    a = -math.pi / 2 + math.sin(t * math.pi) * rng.uniform(-0.55, 0.55)
                    rr = (4 + t * rng.uniform(18, 42)) * sc
                    pts.append((int(cx + math.cos(a) * rr + math.sin(t * 8 + col) * 7 * sc), int(cy + math.sin(a) * rr)))
                val = rng.uniform(0.38, 0.98)
                _polyline(M, pts, val, 1)
                _polyline(R, pts, val * 0.24, 1)
                _polyline(CC, pts, val * 0.18, 1)
                if rng.random() < 0.4:
                    _draw_glint(M, R, CC, cx, cy, max(2, int(5 * sc)), (0.90, 0.20, 0.38))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _leadlight_crackle_mosaic(shape, seed, sm, name="leadlight_crackle_mosaic"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82806)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    wash = _normalize(np.sin(xx * 0.012) + np.cos(yy * 0.016) + np.sin((xx + yy) * 0.009))
    M = (0.16 + wash * 0.34).astype(np.float32)
    R = (0.10 + (1 - wash) * 0.28).astype(np.float32)
    CC = (0.18 + wash * 0.42).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(28, int(72 * sc)), max(24, int(62 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx = x + off + int(rng.uniform(-8, 8) * sc)
                cy = y + int(rng.uniform(-8, 8) * sc)
                pts = _hex_points(cx, cy, int(rng.uniform(18, 34) * sc), rng.uniform(0, math.pi / 3))
                val = rng.uniform(0.30, 0.94)
                _cv2.polylines(M, [pts], True, val, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.28:
                    _cv2.line(R, tuple(pts[int(rng.integers(0, 6))]), tuple(pts[int(rng.integers(0, 6))]), val * 0.2, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _oil_gasket_brownprint(shape, seed, sm, name="oil_gasket_brownprint"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82807)
    M, R, CC = _base(shape, int(seed), 0.12, 0.30, 0.12, 0.055)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 420, 75)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx = max(12, int(rng.uniform(20, 58) * sc))
            ry = max(5, int(rng.uniform(8, 22) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.34, 0.92)
            _cv2.ellipse(R, (cx, cy), (rx, ry), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 0, 360, val * 0.52, 1, lineType=_cv2.LINE_AA)
            for k in range(4):
                a = math.radians(rot) + k * math.tau / 4
                px = int(cx + math.cos(a) * rx * 0.72)
                py = int(cy + math.sin(a) * ry * 0.72)
                _cv2.circle(R, (px, py), max(2, int(5 * sc)), rng.uniform(0.32, 0.88), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (px, py), max(1, int(3 * sc)), rng.uniform(0.22, 0.64), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _concertina_razor_ribbon_mesh(shape, seed, sm, name="concertina_razor_ribbon_mesh"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82808)
    M, R, CC = _base(shape, int(seed), 0.16, 0.12, 0.20, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-3, 12):
            y0 = int((band - 2) * h / 7)
            for i in range(-2, 40):
                cx = int(i * w / 34 + math.sin(i * 0.4 + band) * 22 * sc)
                cy = int(y0 + math.sin(i * 0.75 + band) * 31 * sc)
                rx = max(5, int(rng.uniform(9, 20) * sc))
                ry = max(3, int(rng.uniform(5, 12) * sc))
                val = rng.uniform(0.36, 0.96)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rng.uniform(-25, 25), 0, 360, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rng.uniform(-25, 25), 0, 360, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
                for a in (0, math.pi):
                    tip = (int(cx + math.cos(a) * rx * 1.4), int(cy + math.sin(a) * ry * 1.4))
                    _cv2.line(M, (cx, cy), tip, rng.uniform(0.42, 0.98), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, (cx, cy), tip, rng.uniform(0.10, 0.32), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _iridescent_pangolin_scale_mail(shape, seed, sm, name="iridescent_pangolin_scale_mail"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82809)
    M, R, CC = _base(shape, int(seed), 0.14, 0.12, 0.24, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(18, int(46 * sc)), max(14, int(34 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx = x + off + int(math.sin(y * 0.018) * 7 * sc)
                cy = y
                r = int(rng.uniform(13, 24) * sc)
                pts = np.asarray([[cx, cy - r], [cx + int(r * 0.78), cy - int(r * 0.08)], [cx + int(r * 0.45), cy + int(r * 0.70)], [cx, cy + r], [cx - int(r * 0.45), cy + int(r * 0.70)], [cx - int(r * 0.78), cy - int(r * 0.08)]], dtype=np.int32)
                val = rng.uniform(0.24, 0.94)
                _cv2.fillPoly(M, [pts], val * 0.48, lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [pts], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, min(0.99, val + 0.02), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx, cy - r), (cx, cy + r), val * 0.18, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _thick_oil_interference_islands(shape, seed, sm, name="thick_oil_interference_islands"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82810)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [3, 9, 21], [0.44, 0.34, 0.22], int(seed) + 908))
    phase = _normalize(np.sin(xx * 0.026 + warp * 5.0) + np.cos(yy * 0.031 - warp * 4.0))
    M = (0.16 + phase * 0.48).astype(np.float32)
    R = (0.06 + (1 - phase) * 0.20).astype(np.float32)
    CC = (0.26 + _normalize(np.sin(xx * 0.055 - yy * 0.039 + warp * 7.0)) * 0.64).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 540, 90)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx = max(8, int(rng.uniform(14, 38) * sc))
            ry = max(4, int(rng.uniform(5, 18) * sc))
            val = rng.uniform(0.42, 0.98)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, val * 0.72, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _burl_strata_ink_topography(shape, seed, sm, name="burl_strata_ink_topography"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82811)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [2.5, 7, 17], [0.45, 0.35, 0.20], int(seed) + 910))
    grain = _normalize(np.sin(yy * 0.045 + np.sin(xx * 0.010) * 7.0 + warp * 9.0))
    M = (0.18 + grain * 0.40).astype(np.float32)
    R = (0.16 + _normalize(np.cos(yy * 0.033 + warp * 6.0)) * 0.28).astype(np.float32)
    CC = (0.14 + _normalize(np.sin(xx * 0.015 - yy * 0.010 + warp * 5.0)) * 0.34).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for k in range(72):
            y0 = int((k - 7) * h / 58)
            pts = []
            for x in range(0, w, max(4, int(7 * sc))):
                y = int(y0 + math.sin(x * 0.011 + k) * 42 * sc + math.sin(x * 0.036 + k * 1.7) * 8 * sc)
                pts.append((x, np.clip(y, 0, h - 1)))
            _polyline(M, pts, rng.uniform(0.30, 0.90), 1)
            _polyline(CC, pts, rng.uniform(0.18, 0.62), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_brake_dust_buildup(shape, seed, sm, **kwargs): return _brake_rotor_soot_halos(shape, seed + 901, sm)
def rescue_brushstroke_bold(shape, seed, sm, **kwargs): return _sumi_enamel_slash_field(shape, seed + 902, sm)
def rescue_cc_fish_eye(shape, seed, sm, **kwargs): return _clearcoat_crater_lens_cells(shape, seed + 903, sm)
def rescue_cc_spot_polish(shape, seed, sm, **kwargs): return _rotary_spot_polish_mandala(shape, seed + 904, sm)
def rescue_cloud_wisps_warm(shape, seed, sm, **kwargs): return _ember_spirit_flame_lace(shape, seed + 905, sm)
def rescue_crackle_network(shape, seed, sm, **kwargs): return _leadlight_crackle_mosaic(shape, seed + 906, sm)
def rescue_engine_bay_grime(shape, seed, sm, **kwargs): return _oil_gasket_brownprint(shape, seed + 907, sm)
def rescue_razor_wire_coil(shape, seed, sm, **kwargs): return _concertina_razor_ribbon_mesh(shape, seed + 908, sm)
def rescue_pangolin_armor(shape, seed, sm, **kwargs): return _iridescent_pangolin_scale_mail(shape, seed + 909, sm)
def rescue_spec_oil_film_thick(shape, seed, sm, **kwargs): return _thick_oil_interference_islands(shape, seed + 910, sm)
def rescue_spec_wood_grain_fine(shape, seed, sm, **kwargs): return _burl_strata_ink_topography(shape, seed + 911, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass4-iteration2:
# Visual self-check rejected dot-grid pangolin/crackle/spot/fisheye outputs and
# the overly green or psychedelic material fields. These variants privilege
# larger readable material silhouettes made from sub-32px components.
def _graphite_brake_sweep_ghosts(shape, seed, sm, name="graphite_brake_sweep_ghosts"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82901)
    M, R, CC = _base(shape, int(seed), 0.18, 0.16, 0.14, 0.055)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-4, 13):
            cx = int((band - 2) * w / 7)
            for k in range(22):
                cy = int(k * h / 20 + rng.uniform(-26, 26) * sc)
                rx = max(14, int(rng.uniform(24, 70) * sc))
                ry = max(5, int(rng.uniform(7, 20) * sc))
                rot = rng.uniform(-18, 18)
                val = rng.uniform(0.28, 0.88)
                _cv2.ellipse(M, (cx + int(math.sin(k) * 28 * sc), cy), (rx, ry), rot, 190, 340, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx + int(math.sin(k) * 28 * sc), cy), (rx, ry), rot, 190, 340, val * 0.72, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx + int(math.sin(k) * 28 * sc), cy), (rx, ry), rot, 190, 340, val * 0.18, 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 1400, 220)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(M, (x, y), max(1, int(rng.uniform(1.2, 3.4) * sc)), rng.uniform(0.20, 0.76), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _random_clearcoat_fisheye_craters(shape, seed, sm, name="random_clearcoat_fisheye_craters"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82902)
    M, R, CC = _base(shape, int(seed), 0.08, 0.06, 0.34, 0.03)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 520, 90)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx = max(6, int(rng.uniform(9, 24) * sc))
            ry = max(4, int(rx * rng.uniform(0.48, 1.0)))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.40, 0.98)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (max(2, rx - 3), max(2, ry - 3)), rot, 0, 360, val * 0.36, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx - rx // 3, cy - ry // 3), max(1, int(2.2 * sc)), min(0.99, val + 0.08), -1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.35:
                _cv2.ellipse(CC, (cx, cy), (rx + max(2, int(5 * sc)), ry + max(2, int(4 * sc))), rot, 35, 180, val * 0.5, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _rotary_polish_shells(shape, seed, sm, name="rotary_polish_shells"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82903)
    M, R, CC = _base(shape, int(seed), 0.13, 0.08, 0.30, 0.03)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 520, 90)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            for k in range(int(rng.integers(3, 8))):
                rx = max(5, int((8 + k * rng.uniform(3, 7)) * sc))
                ry = max(2, int(rx * rng.uniform(0.22, 0.50)))
                start = rng.uniform(0, 280)
                val = rng.uniform(0.32, 0.98)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 13, start, start + rng.uniform(80, 210), val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 13, start, start + rng.uniform(80, 210), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _jagged_lead_crackle_rivers(shape, seed, sm, name="jagged_lead_crackle_rivers"):
    # OWNER STRENGTHEN 2026-06-04: "need more crackle, not coming through, needs
    # to be brighter". Rebuilt as a DENSE bright crackle NETWORK: a true
    # cell-fracture field (Voronoi cell grout) for full coverage PLUS a layer of
    # jagged bright lead rivers with frequent branching. Higher amplitude, crisper
    # brighter crack lines, dark cell interiors so the network really pops.
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82904)
    sc = _scale(shape)
    mn = min(h, w)
    s256 = max(mn / 256.0, 0.55)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # --- Layer 1: full-field Voronoi crackle cells (dense seamless network). ---
    # PERF 2026-06-04: the old per-site Python loop built a full-frame squared-
    # distance array for EVERY seed (n_seed = 7680 at 2048 -> >1 min). Replaced
    # by a single cKDTree nearest-two-sites query over the meshgrid. The grout
    # ridge is edge = d2 - d1 (distance to 2nd-nearest minus nearest site);
    # cKDTree returns the actual Euclidean distances, so this is the IDENTICAL
    # math as the old sqrt(d2_sq) - sqrt(d1_sq) -- the field is the same.
    n_seed = max(36, int(120 * (mn / 256.0) ** 2))
    jx = rng.uniform(0, w, n_seed).astype(np.float32)
    jy = rng.uniform(0, h, n_seed).astype(np.float32)
    sites = np.column_stack([jx.astype(np.float64), jy.astype(np.float64)])
    tree = cKDTree(sites)
    coords = np.column_stack([xx.ravel().astype(np.float64), yy.ravel().astype(np.float64)])
    dists, _ = tree.query(coords, k=2, workers=-1)
    edge = (dists[:, 1] - dists[:, 0]).reshape(h, w).astype(np.float32)
    crack_w = max(1.6 * s256, 1.0)
    crack = np.clip(1.0 - edge / crack_w, 0.0, 1.0) ** 1.3   # 1 on crack, 0 in cell
    # dark satin cell interiors; BRIGHT crisp metallic crack grout on top.
    M = (0.16 + crack * 0.78).astype(np.float32)
    R = (0.58 - crack * 0.44).astype(np.float32)
    CC = (0.20 + crack * 0.74).astype(np.float32)
    # gentle per-cell tone variation so cells aren't a flat plate.
    cellnoise = _normalize(_spb_fast_smooth_noise(shape, [3.0 * s256, 8.0 * s256], [0.6, 0.4], int(seed) + 311, max_dim=1024))
    M = np.clip(M + (cellnoise - 0.5) * 0.10, 0, 1).astype(np.float32)
    CC = np.clip(CC + (cellnoise - 0.5) * 0.08, 0, 1).astype(np.float32)

    # --- Layer 2: jagged bright lead rivers with dense branching on top. ---
    if _CV2_OK:
        n_root = int(np.clip(28 * (mn / 256.0) ** 1.3, 20, 60))
        for root in range(n_root):
            x = int(rng.uniform(-30, w + 30))
            y = int(rng.uniform(-40, 40) * sc)
            pts = [(x, y)]
            while y < h + 40:
                x += int(rng.uniform(-30, 36) * sc)
                y += int(rng.uniform(12, 30) * sc)
                pts.append((x, y))
                if rng.random() < 0.55:
                    branch = [(x, y)]
                    bx, by = x, y
                    bdir = rng.uniform(-1, 1)
                    for _ in range(int(rng.integers(4, 11))):
                        bx += int((bdir * 18 + rng.uniform(-22, 22)) * sc)
                        by += int(rng.uniform(6, 20) * sc)
                        branch.append((bx, by))
                    _polyline(CC, branch, rng.uniform(0.62, 0.99), 1)
                    _polyline(M, branch, rng.uniform(0.54, 0.96), 1)
                    _polyline(R, branch, rng.uniform(0.04, 0.16), 1)
            _polyline(M, pts, rng.uniform(0.66, 0.99), 2)
            _polyline(CC, pts, rng.uniform(0.62, 0.99), 2)
            _polyline(R, pts, rng.uniform(0.04, 0.18), 2)
            # bright hairline echo beside the main river for a crisp double edge.
            _polyline(M, [(px + int(2 * sc), py) for px, py in pts], rng.uniform(0.50, 0.86), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _oil_gasket_shadow_archipelago(shape, seed, sm, name="oil_gasket_shadow_archipelago"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82905)
    M, R, CC = _base(shape, int(seed), 0.14, 0.18, 0.13, 0.055)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 620, 105)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx = max(10, int(rng.uniform(18, 48) * sc))
            ry = max(4, int(rng.uniform(6, 18) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.32, 0.90)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rx, ry), rot, 0, 360, val * 0.28, 1, lineType=_cv2.LINE_AA)
            for k in range(3):
                a = math.radians(rot) + k * math.tau / 3
                _cv2.line(CC, (cx, cy), (int(cx + math.cos(a) * rx), int(cy + math.sin(a) * ry)), rng.uniform(0.22, 0.74), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _pangolin_overlapping_lamellar_plates(shape, seed, sm, name="pangolin_overlapping_lamellar_plates"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82906)
    M, R, CC = _base(shape, int(seed), 0.13, 0.11, 0.24, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(24, int(58 * sc)), max(16, int(40 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx = x + off + int(math.sin(row * 0.8) * 12 * sc)
                cy = y
                rw = int(rng.uniform(18, 31) * sc)
                rh = int(rng.uniform(13, 25) * sc)
                pts = np.asarray([[cx, cy - rh], [cx + rw, cy - int(rh * 0.15)], [cx + int(rw * 0.55), cy + rh], [cx, cy + int(rh * 0.70)], [cx - int(rw * 0.55), cy + rh], [cx - rw, cy - int(rh * 0.15)]], dtype=np.int32)
                val = rng.uniform(0.26, 0.94)
                _cv2.fillPoly(M, [pts], val * 0.62, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], val * 0.34, lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [pts], True, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, min(0.99, val + 0.12), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _liquid_oil_silver_interference(shape, seed, sm, name="liquid_oil_silver_interference"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82907)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [4, 10, 23], [0.42, 0.36, 0.22], int(seed) + 1010))
    flow = _normalize(np.sin(xx * 0.025 + warp * 7.5) + np.cos(yy * 0.021 - warp * 4.5))
    M = (0.24 + flow * 0.46).astype(np.float32)
    R = (0.08 + _normalize(np.sin(xx * 0.040 - yy * 0.030 + warp * 6.0)) * 0.16).astype(np.float32)
    CC = (0.30 + _normalize(np.cos(xx * 0.052 + yy * 0.019 + warp * 8.0)) * 0.58).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 400, 75)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(8, int(rng.uniform(12, 34) * sc)), max(3, int(rng.uniform(5, 15) * sc))
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, rng.uniform(0.52, 0.98), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _sepia_burl_relief_contours(shape, seed, sm, name="sepia_burl_relief_contours"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 82908)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [3, 8, 18], [0.42, 0.38, 0.20], int(seed) + 1012))
    strata = _normalize(np.sin(yy * 0.050 + np.sin(xx * 0.011) * 8.0 + warp * 10.0))
    M = (0.22 + strata * 0.42).astype(np.float32)
    R = (0.10 + _normalize(np.cos(yy * 0.036 + warp * 6.0)) * 0.16).astype(np.float32)
    CC = (0.16 + _normalize(np.sin(xx * 0.014 - yy * 0.012 + warp * 4.5)) * 0.30).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for k in range(70):
            y0 = int((k - 7) * h / 56)
            pts = []
            for x in range(0, w, max(4, int(7 * sc))):
                y = int(y0 + math.sin(x * 0.011 + k) * 34 * sc + math.sin(x * 0.033 + k * 1.4) * 7 * sc)
                pts.append((x, np.clip(y, 0, h - 1)))
            _polyline(M, pts, rng.uniform(0.36, 0.92), 1)
            _polyline(CC, pts, rng.uniform(0.22, 0.64), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_brake_dust_buildup(shape, seed, sm, **kwargs): return _graphite_brake_sweep_ghosts(shape, seed + 1001, sm)
def rescue_cc_fish_eye(shape, seed, sm, **kwargs): return _random_clearcoat_fisheye_craters(shape, seed + 1002, sm)
def rescue_cc_spot_polish(shape, seed, sm, **kwargs): return _rotary_polish_shells(shape, seed + 1003, sm)
def rescue_crackle_network(shape, seed, sm, **kwargs): return _jagged_lead_crackle_rivers(shape, seed + 1004, sm)
def rescue_engine_bay_grime(shape, seed, sm, **kwargs): return _oil_gasket_shadow_archipelago(shape, seed + 1005, sm)
def rescue_pangolin_armor(shape, seed, sm, **kwargs): return _pangolin_overlapping_lamellar_plates(shape, seed + 1006, sm)
def rescue_spec_oil_film_thick(shape, seed, sm, **kwargs): return _liquid_oil_silver_interference(shape, seed + 1007, sm)
def rescue_spec_wood_grain_fine(shape, seed, sm, **kwargs): return _sepia_burl_relief_contours(shape, seed + 1008, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass4-iteration3:
# Third visual self-check: pangolin still collapsed into dots, oil was noisy
# soup, and wood was too chaotic. Force readable armor plates and correlated
# channel values for clean liquid/strata previews.
def _dragon_scale_lamellar_rows(shape, seed, sm, name="dragon_scale_lamellar_rows"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83001)
    M, R, CC = _base(shape, int(seed), 0.12, 0.10, 0.22, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(34, int(78 * sc)), max(22, int(52 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx = x + off + int(math.sin(row * 0.65) * 15 * sc)
                cy = y
                rw = int(rng.uniform(22, 34) * sc)
                rh = int(rng.uniform(18, 30) * sc)
                pts = np.asarray([
                    [cx, cy - rh],
                    [cx + rw, cy - int(rh * 0.16)],
                    [cx + int(rw * 0.72), cy + int(rh * 0.55)],
                    [cx, cy + rh],
                    [cx - int(rw * 0.72), cy + int(rh * 0.55)],
                    [cx - rw, cy - int(rh * 0.16)],
                ], dtype=np.int32)
                val = rng.uniform(0.28, 0.94)
                _cv2.fillPoly(M, [pts], val * 0.74, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], val * 0.62, lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [pts], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, min(0.99, val + 0.10), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx, cy - rh), (cx, cy + rh), val * 0.18, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _clean_liquid_chrome_oil_lenses(shape, seed, sm, name="clean_liquid_chrome_oil_lenses"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83002)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [5, 13, 31], [0.46, 0.34, 0.20], int(seed) + 1200))
    ribbon = _normalize(np.sin(xx * 0.018 + yy * 0.010 + warp * 8.0) + np.sin(xx * 0.041 - yy * 0.026 + warp * 4.0))
    M = (0.20 + ribbon * 0.58).astype(np.float32)
    R = (0.08 + ribbon * 0.08).astype(np.float32)
    CC = (0.26 + ribbon * 0.62).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 260, 45)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx = max(12, int(rng.uniform(20, 58) * sc))
            ry = max(5, int(rng.uniform(7, 22) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.62, 0.99)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 0, 360, val * 0.86, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rx, ry), rot, 0, 360, val * 0.10, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _clean_burl_terrain_ridges(shape, seed, sm, name="clean_burl_terrain_ridges"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83003)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [4, 10, 24], [0.42, 0.36, 0.22], int(seed) + 1210))
    strata = _normalize(np.sin(yy * 0.042 + np.sin(xx * 0.010) * 6.0 + warp * 8.0))
    M = (0.20 + strata * 0.46).astype(np.float32)
    R = (0.10 + strata * 0.10).astype(np.float32)
    CC = (0.18 + strata * 0.42).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for k in range(58):
            y0 = int((k - 6) * h / 45)
            pts = []
            for x in range(0, w, max(5, int(9 * sc))):
                y = int(y0 + math.sin(x * 0.010 + k) * 28 * sc + math.sin(x * 0.028 + k * 1.3) * 6 * sc)
                pts.append((x, np.clip(y, 0, h - 1)))
            val = rng.uniform(0.34, 0.90)
            _polyline(M, pts, val, 1)
            _polyline(CC, pts, min(0.96, val + 0.04), 1)
        for _ in range(_count(shape, 650, 110)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(M, (x, y), max(1, int(rng.uniform(1.5, 3.5) * sc)), rng.uniform(0.30, 0.72), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_pangolin_armor(shape, seed, sm, **kwargs): return _dragon_scale_lamellar_rows(shape, seed + 1101, sm)
def rescue_spec_oil_film_thick(shape, seed, sm, **kwargs): return _clean_liquid_chrome_oil_lenses(shape, seed + 1102, sm)
def rescue_spec_wood_grain_fine(shape, seed, sm, **kwargs): return _clean_burl_terrain_ridges(shape, seed + 1103, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass4-iteration4:
# Pangolin still read as a dot lattice in thumbnail review. Convert it to
# flowing armor rivers with fine inner scale cuts so the silhouette is unique.
def _pangolin_armored_river_bands(shape, seed, sm, name="pangolin_armored_river_bands"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83101)
    M, R, CC = _base(shape, int(seed), 0.12, 0.10, 0.22, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-4, 12):
            x0 = int((band - 3) * w / 7)
            spine = []
            for i in range(120):
                y = int(i * h / 119)
                x = int(x0 + y * 0.34 + math.sin(i * 0.12 + band) * 44 * sc)
                spine.append((x, y))
            _polyline(M, spine, rng.uniform(0.34, 0.74), max(1, int(24 * sc)))
            _polyline(CC, spine, rng.uniform(0.26, 0.68), max(1, int(18 * sc)))
            for x, y in spine[3::5]:
                for side in (-1, 1):
                    cx = x + int(side * rng.uniform(7, 16) * sc)
                    cy = y + int(rng.uniform(-5, 5) * sc)
                    rw = int(rng.uniform(7, 14) * sc)
                    rh = int(rng.uniform(6, 12) * sc)
                    pts = np.asarray([[cx, cy - rh], [cx + side * rw, cy], [cx, cy + rh], [cx - side * int(rw * 0.55), cy]], dtype=np.int32)
                    val = rng.uniform(0.48, 0.98)
                    _cv2.polylines(M, [pts], True, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.polylines(CC, [pts], True, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, (cx, cy - rh), (cx, cy + rh), val * 0.16, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_pangolin_armor(shape, seed, sm, **kwargs): return _pangolin_armored_river_bands(shape, seed + 1201, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass5:
# Full-sheet WWRD review still showed several cousin families: purple speck
# curls, green circuit fields, simple stripe cards, and bright holo blur. This
# pass replaces them with separate material grammars and correlated channel
# values where needed so thumbnails read like finishes instead of noise.
def _clearcoat_lens_wake_seams(shape, seed, sm, name="clearcoat_lens_wake_seams"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83201)
    M, R, CC = _base(shape, int(seed), 0.08, 0.06, 0.34, 0.025)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-4, 13):
            y0 = int((band - 2) * h / 7)
            pts = []
            for x in range(-20, w + 24, max(5, int(9 * sc))):
                y = int(y0 + math.sin(x * 0.020 + band) * 30 * sc + math.sin(x * 0.065) * 6 * sc)
                pts.append((x, y))
            for off, val in ((-8, 0.42), (-3, 0.68), (2, 0.96), (8, 0.52)):
                shifted = [(x, y + int(off * sc)) for x, y in pts]
                _polyline(CC, shifted, val, 1)
                _polyline(M, shifted, val * 0.48, 1)
            for x, y in pts[5::10]:
                rr = max(2, int(rng.uniform(4, 9) * sc))
                _cv2.ellipse(CC, (x, y), (rr * 2, rr), rng.uniform(-18, 18), 0, 360, rng.uniform(0.64, 0.99), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (x - rr // 2, y - rr // 3), max(1, rr // 2), rng.uniform(0.68, 0.98), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _masking_adhesive_cross_torn(shape, seed, sm, name="masking_adhesive_cross_torn"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83202)
    M, R, CC = _base(shape, int(seed), 0.18, 0.18, 0.15, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for angle_deg in (-26, 31):
            angle = math.radians(angle_deg)
            for lane in range(-8, 16):
                cx0 = int(lane * w / 7)
                pts = []
                for t in range(-80, max(w, h) + 100, max(5, int(10 * sc))):
                    x = int(cx0 + math.cos(angle) * t + math.sin(angle) * 14 * math.sin(t * 0.025 + lane))
                    y = int(h * 0.5 + math.sin(angle) * t + math.cos(angle) * 25 * math.sin(t * 0.018 + lane))
                    pts.append((x, y))
                val = rng.uniform(0.36, 0.88)
                _polyline(M, pts, val, 1)
                _polyline(CC, pts, val * 0.75, 1)
                for x, y in pts[2::5]:
                    tooth = int(rng.uniform(4, 14) * sc)
                    _cv2.line(R, (x, y), (x + int(math.sin(angle) * tooth), y - int(math.cos(angle) * tooth)), rng.uniform(0.14, 0.46), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _pcb_relic_mandala_traces(shape, seed, sm, name="pcb_relic_mandala_traces"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83203)
    M, R, CC = _base(shape, int(seed), 0.12, 0.20, 0.14, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(92, int(210 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx, cy = x + pitch // 2, y + pitch // 2
                for rr in (18, 34, 54):
                    r = max(5, int(rr * sc))
                    _cv2.circle(M, (cx, cy), r, rng.uniform(0.36, 0.92), 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (cx, cy), r, rng.uniform(0.28, 0.78), 1, lineType=_cv2.LINE_AA)
                for k in range(12):
                    a = k * math.tau / 12 + rng.uniform(-0.05, 0.05)
                    p1 = (int(cx + math.cos(a) * 20 * sc), int(cy + math.sin(a) * 20 * sc))
                    p2 = (int(cx + math.cos(a) * 82 * sc), int(cy + math.sin(a) * 82 * sc))
                    _cv2.line(M, p1, p2, rng.uniform(0.34, 0.94), 1, lineType=_cv2.LINE_AA)
                    if k % 3 == 0:
                        _cv2.circle(CC, p2, max(2, int(5 * sc)), rng.uniform(0.45, 0.95), 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 850, 140)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.rectangle(M, (x, y), (x + max(3, int(9 * sc)), y + max(1, int(3 * sc))), rng.uniform(0.28, 0.82), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _verdigris_copper_island_map(shape, seed, sm, name="verdigris_copper_island_map"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83204)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [4, 11, 28], [0.42, 0.34, 0.24], int(seed) + 1400))
    field = _normalize(np.sin(xx * 0.018 + warp * 5.0) + np.cos(yy * 0.022 - warp * 4.0))
    M = (0.16 + field * 0.40).astype(np.float32)
    R = (0.20 + (1 - field) * 0.30).astype(np.float32)
    CC = (0.12 + field * 0.24).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 420, 70)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx = max(7, int(rng.uniform(12, 34) * sc))
            ry = max(3, int(rng.uniform(5, 18) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.34, 0.94)
            _cv2.ellipse(R, (cx, cy), (rx, ry), rot, 0, 360, val * 0.32, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 20, 220, val * 0.46, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _da_pigtail_buffer_haze(shape, seed, sm, name="da_pigtail_buffer_haze"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83205)
    M, R, CC = _base(shape, int(seed), 0.14, 0.10, 0.28, 0.03)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 620, 110)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, math.tau)
            pts = []
            turns = rng.uniform(1.1, 2.4)
            for i in range(42):
                t = i / 41
                a = rot + t * math.tau * turns
                r = (2 + t * rng.uniform(10, 28)) * sc
                pts.append((int(cx + math.cos(a) * r), int(cy + math.sin(a) * r * rng.uniform(0.65, 1.0))))
            val = rng.uniform(0.28, 0.96)
            _polyline(M, pts, val, 1)
            _polyline(CC, pts, min(0.99, val + 0.05), 1)
            _polyline(R, pts, val * 0.10, 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _microfiber_hand_wipe_crosshatch(shape, seed, sm, name="microfiber_hand_wipe_crosshatch"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83206)
    M, R, CC = _base(shape, int(seed), 0.13, 0.09, 0.24, 0.03)
    sc = _scale(shape)
    if _CV2_OK:
        for family, angle in enumerate((math.radians(18), math.radians(-34), math.radians(72))):
            for _ in range(_count(shape, 620, 100)):
                cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
                length = rng.uniform(10, 32) * sc
                wiggle = rng.uniform(-0.18, 0.18)
                p1 = (int(cx - math.cos(angle + wiggle) * length), int(cy - math.sin(angle + wiggle) * length))
                p2 = (int(cx + math.cos(angle + wiggle) * length), int(cy + math.sin(angle + wiggle) * length))
                val = rng.uniform(0.24, 0.90)
                _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, p1, p2, min(0.98, val + 0.06), 1, lineType=_cv2.LINE_AA)
                if family == 1:
                    _cv2.line(R, p1, p2, val * 0.08, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _forged_carbon_plate_mosaic(shape, seed, sm, name="forged_carbon_plate_mosaic"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83207)
    M, R, CC = _base(shape, int(seed), 0.08, 0.12, 0.16, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1250, 210)):
            cx, cy = int(rng.integers(-15, w + 15)), int(rng.integers(-15, h + 15))
            n = int(rng.integers(4, 7))
            rad = rng.uniform(10, 28) * sc
            rot = rng.uniform(0, math.tau)
            pts = []
            for k in range(n):
                a = rot + k * math.tau / n + rng.uniform(-0.22, 0.22)
                rr = rad * rng.uniform(0.55, 1.20)
                pts.append((int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr)))
            poly = np.asarray(pts, dtype=np.int32)
            val = float(rng.choice([0.16, 0.24, 0.34, 0.46, 0.60, 0.74, 0.88]))
            _cv2.fillPoly(M, [poly], val * 0.78, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, min(0.98, val + 0.08), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, pts[0], pts[n // 2], val * 0.16, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _nacre_tile_inlay_mosaic(shape, seed, sm, name="nacre_tile_inlay_mosaic"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83208)
    M, R, CC = _base(shape, int(seed), 0.20, 0.08, 0.32, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(26, int(62 * sc)), max(18, int(44 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off, y
                pts = np.asarray([[cx - sx // 2, cy], [cx, cy - sy // 2], [cx + sx // 2, cy], [cx, cy + sy // 2]], dtype=np.int32)
                val = rng.uniform(0.26, 0.96)
                _cv2.fillPoly(CC, [pts], val * 0.62, lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [pts], True, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, tuple(pts[0]), tuple(pts[2]), val * 0.10, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _prismatic_microflake_veil(shape, seed, sm, name="prismatic_microflake_veil"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83209)
    M, R, CC = _base(shape, int(seed), 0.16, 0.08, 0.26, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 2500, 380)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            length = rng.uniform(3, 11) * sc
            angle = rng.uniform(0, math.tau)
            val = rng.uniform(0.32, 0.98)
            p1 = (int(cx - math.cos(angle) * length), int(cy - math.sin(angle) * length))
            p2 = (int(cx + math.cos(angle) * length), int(cy + math.sin(angle) * length))
            _cv2.line(CC, p1, p2, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, p1, p2, val * 0.72, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.10:
                _draw_glint(M, R, CC, cx, cy, max(2, int(4 * sc)), (0.86, 0.12, 0.96))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _diffraction_shard_foil(shape, seed, sm, name="diffraction_shard_foil"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83210)
    M, R, CC = _base(shape, int(seed), 0.20, 0.08, 0.36, 0.025)
    sc = _scale(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    grating = _normalize(np.sin(xx * 0.10 + yy * 0.018) + np.sin((xx - yy) * 0.072))
    CC[:] = np.maximum(CC, 0.20 + grating * 0.54)
    if _CV2_OK:
        for _ in range(_count(shape, 720, 120)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            length = rng.uniform(14, 40) * sc
            width = rng.uniform(4, 11) * sc
            a = rng.uniform(0, math.tau)
            pts = np.asarray([
                [int(cx + math.cos(a) * length), int(cy + math.sin(a) * length)],
                [int(cx + math.cos(a + 2.2) * width), int(cy + math.sin(a + 2.2) * width)],
                [int(cx - math.cos(a) * length * 0.55), int(cy - math.sin(a) * length * 0.55)],
                [int(cx + math.cos(a - 2.2) * width), int(cy + math.sin(a - 2.2) * width)],
            ], dtype=np.int32)
            val = rng.uniform(0.34, 0.98)
            _cv2.polylines(CC, [pts], True, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(M, [pts], True, val * 0.82, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, tuple(pts[0]), tuple(pts[2]), val * 0.10, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _pit_wall_rubber_scuff_transfer(shape, seed, sm, name="pit_wall_rubber_scuff_transfer"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83211)
    M, R, CC = _base(shape, int(seed), 0.11, 0.20, 0.13, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-3, 13):
            y0 = int((band - 2) * h / 7)
            for i in range(36):
                cx = int(i * w / 32 + rng.uniform(-24, 24) * sc)
                cy = int(y0 + math.sin(i * 0.7 + band) * 34 * sc)
                length = rng.uniform(16, 48) * sc
                angle = rng.uniform(-0.18, 0.28)
                val = rng.uniform(0.30, 0.88)
                p1 = (cx, cy)
                p2 = (int(cx + math.cos(angle) * length), int(cy + math.sin(angle) * length))
                _cv2.line(R, p1, p2, val * 0.24, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.45:
                    _cv2.circle(CC, p2, max(1, int(rng.uniform(2, 5) * sc)), val * 0.55, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_cc_gloss_stripe(shape, seed, sm, **kwargs): return _clearcoat_lens_wake_seams(shape, seed + 1301, sm)
def rescue_cc_masking_edge(shape, seed, sm, **kwargs): return _masking_adhesive_cross_torn(shape, seed + 1302, sm)
def rescue_circuit_trace(shape, seed, sm, **kwargs): return _pcb_relic_mandala_traces(shape, seed + 1303, sm)
def rescue_copper_patina_drip(shape, seed, sm, **kwargs): return _verdigris_copper_island_map(shape, seed + 1304, sm)
def rescue_buffer_swirl(shape, seed, sm, **kwargs): return _da_pigtail_buffer_haze(shape, seed + 1305, sm)
def rescue_hand_polished(shape, seed, sm, **kwargs): return _microfiber_hand_wipe_crosshatch(shape, seed + 1306, sm)
def rescue_forged_carbon_chip(shape, seed, sm, **kwargs): return _forged_carbon_plate_mosaic(shape, seed + 1307, sm)
def rescue_mother_of_pearl_inlay(shape, seed, sm, **kwargs): return _nacre_tile_inlay_mosaic(shape, seed + 1308, sm)
def rescue_micro_sparkle(shape, seed, sm, **kwargs): return _prismatic_microflake_veil(shape, seed + 1309, sm)
def rescue_spec_holographic_foil(shape, seed, sm, **kwargs): return _diffraction_shard_foil(shape, seed + 1310, sm)
def rescue_wear_scuff(shape, seed, sm, **kwargs): return _pit_wall_rubber_scuff_transfer(shape, seed + 1311, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass5-iteration2:
# First visual pass still had five underbuilt/speck-heavy cards. Rebuild them
# with stronger thumbnail silhouettes while preserving fine 8-32 px details.
def _da_buffer_pigtail_constellations(shape, seed, sm, name="da_buffer_pigtail_constellations"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83301)
    M, R, CC = _base(shape, int(seed), 0.13, 0.09, 0.28, 0.03)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 420, 75)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, math.tau)
            for arm in range(int(rng.integers(2, 5))):
                pts = []
                phase = rot + arm * math.tau / 3 + rng.uniform(-0.25, 0.25)
                for i in range(56):
                    t = i / 55
                    a = phase + t * math.tau * rng.uniform(1.2, 2.1)
                    r = (3 + t * rng.uniform(16, 44)) * sc
                    pts.append((int(cx + math.cos(a) * r), int(cy + math.sin(a) * r * 0.72)))
                val = rng.uniform(0.34, 0.98)
                _polyline(M, pts, val, 1)
                _polyline(CC, pts, min(0.99, val + 0.06), 1)
                _polyline(R, pts, val * 0.10, 1)
            if rng.random() < 0.35:
                _draw_glint(M, R, CC, cx, cy, max(2, int(5 * sc)), (0.78, 0.10, 0.90))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _forged_carbon_torn_sheet_mosaic(shape, seed, sm, name="forged_carbon_torn_sheet_mosaic"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83302)
    M, R, CC = _base(shape, int(seed), 0.07, 0.11, 0.15, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 760, 125)):
            cx, cy = int(rng.integers(-20, w + 20)), int(rng.integers(-20, h + 20))
            long = rng.uniform(18, 54) * sc
            short = rng.uniform(6, 18) * sc
            rot = rng.uniform(0, math.tau)
            pts = []
            for k in range(6):
                a = rot + k * math.tau / 6 + rng.uniform(-0.28, 0.28)
                rr = long * rng.uniform(0.55, 1.15) if k % 2 == 0 else short * rng.uniform(0.80, 1.55)
                pts.append((int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr)))
            poly = np.asarray(pts, dtype=np.int32)
            val = float(rng.choice([0.18, 0.26, 0.36, 0.48, 0.62, 0.76, 0.90]))
            _cv2.fillPoly(M, [poly], val * 0.82, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [poly], val * 0.32, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, min(0.98, val + 0.10), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, pts[0], pts[3], val * 0.16, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _verdigris_cracked_copper_lakes(shape, seed, sm, name="verdigris_cracked_copper_lakes"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83303)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [5, 12, 30], [0.44, 0.34, 0.22], int(seed) + 1500))
    lake = _normalize(np.sin(xx * 0.016 + warp * 5.5) + np.cos(yy * 0.019 - warp * 4.8))
    M = (0.18 + lake * 0.42).astype(np.float32)
    R = (0.18 + (1 - lake) * 0.22).astype(np.float32)
    CC = (0.12 + lake * 0.28).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 360, 65)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(12, int(rng.uniform(18, 52) * sc)), max(5, int(rng.uniform(8, 24) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.36, 0.94)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rx, ry), rot, 0, 360, val * 0.24, 1, lineType=_cv2.LINE_AA)
            for k in range(3):
                a = math.radians(rot) + k * math.tau / 3
                _cv2.line(CC, (cx, cy), (int(cx + math.cos(a) * rx), int(cy + math.sin(a) * ry)), rng.uniform(0.28, 0.82), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _stardust_microprism_cartography(shape, seed, sm, name="stardust_microprism_cartography"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83304)
    M, R, CC = _base(shape, int(seed), 0.12, 0.08, 0.24, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 780, 130)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(12, int(rng.uniform(20, 64) * sc)), max(5, int(rng.uniform(8, 30) * sc))
            rot = rng.uniform(0, 180)
            start = rng.uniform(0, 310)
            span = rng.uniform(40, 160)
            val = rng.uniform(0.30, 0.90)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, start, start + span, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.55:
                _draw_glint(M, R, CC, cx, cy, max(2, int(rng.uniform(3, 7) * sc)), (0.90, 0.12, 0.96))
        for _ in range(_count(shape, 1800, 260)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(M, (cx, cy), max(1, int(rng.uniform(1.2, 3.0) * sc)), rng.uniform(0.34, 0.92), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), max(1, int(rng.uniform(1.2, 3.0) * sc)), rng.uniform(0.42, 0.98), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _rubber_wall_scuff_smeared_arcs(shape, seed, sm, name="rubber_wall_scuff_smeared_arcs"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83305)
    M, R, CC = _base(shape, int(seed), 0.11, 0.18, 0.12, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 540, 90)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(10, int(rng.uniform(18, 58) * sc)), max(4, int(rng.uniform(6, 20) * sc))
            rot = rng.uniform(-16, 16)
            val = rng.uniform(0.28, 0.86)
            start = rng.uniform(170, 240)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, start, start + rng.uniform(55, 160), val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rx, ry), rot, start, start + rng.uniform(55, 160), val * 0.20, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.35:
                _cv2.line(CC, (cx - rx, cy), (cx + rx, cy + int(ry * 0.4)), val * 0.48, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_buffer_swirl(shape, seed, sm, **kwargs): return _da_buffer_pigtail_constellations(shape, seed + 1401, sm)
def rescue_forged_carbon_chip(shape, seed, sm, **kwargs): return _forged_carbon_torn_sheet_mosaic(shape, seed + 1402, sm)
def rescue_copper_patina_drip(shape, seed, sm, **kwargs): return _verdigris_cracked_copper_lakes(shape, seed + 1403, sm)
def rescue_micro_sparkle(shape, seed, sm, **kwargs): return _stardust_microprism_cartography(shape, seed + 1404, sm)
def rescue_wear_scuff(shape, seed, sm, **kwargs): return _rubber_wall_scuff_smeared_arcs(shape, seed + 1405, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass5-iteration3:
# Contact sheet rejected buffer confetti and mushy patina. These force clear
# orbital polish and corrosion-contour silhouettes.
def _orbital_buffer_shell_rings(shape, seed, sm, name="orbital_buffer_shell_rings"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83401)
    M, R, CC = _base(shape, int(seed), 0.13, 0.09, 0.30, 0.03)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(72, int(165 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx = x + int(rng.uniform(15, pitch - 15))
                cy = y + int(rng.uniform(15, pitch - 15))
                rot = rng.uniform(0, 180)
                for k in range(8):
                    rx = max(7, int((14 + k * 6) * sc))
                    ry = max(3, int(rx * rng.uniform(0.28, 0.58)))
                    start = rng.uniform(0, 220)
                    span = rng.uniform(90, 260)
                    val = rng.uniform(0.30, 0.96)
                    _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 7, start, start + span, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 7, start, start + span, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(R, (cx, cy), (rx, ry), rot + k * 7, start, start + span, val * 0.10, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _copper_verdigris_contour_lakes(shape, seed, sm, name="copper_verdigris_contour_lakes"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83402)
    M, R, CC = _base(shape, int(seed), 0.19, 0.17, 0.13, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 260, 45)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            for k in range(int(rng.integers(3, 7))):
                rx = max(7, int((12 + k * rng.uniform(5, 11)) * sc))
                ry = max(4, int(rx * rng.uniform(0.35, 0.78)))
                val = rng.uniform(0.34, 0.92)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 4, 0, 360, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rx, ry), rot + k * 4, 0, 360, val * 0.24, 1, lineType=_cv2.LINE_AA)
                if k == 0:
                    _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 30, 230, val * 0.48, 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 900, 150)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(M, (x, y), max(1, int(rng.uniform(1.3, 3.2) * sc)), rng.uniform(0.26, 0.72), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_buffer_swirl(shape, seed, sm, **kwargs): return _orbital_buffer_shell_rings(shape, seed + 1501, sm)
def rescue_copper_patina_drip(shape, seed, sm, **kwargs): return _copper_verdigris_contour_lakes(shape, seed + 1502, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass6:
# Latest 40-card review still showed sparse clearcoat dots, purple star grids,
# big magenta hairline stripes, and noisy oil/wood previews. This pass rebuilds
# those into stronger machined, ghostly, geode, flake, and liquid grammars.
def _voodoo_grisgris_pinwheel_charms(shape, seed, sm, name="voodoo_grisgris_pinwheel_charms"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83501)
    M, R, CC = _base(shape, int(seed), 0.22, 0.08, 0.10, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(58, int(138 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx = x + pitch // 2 + int(rng.uniform(-8, 8) * sc)
                cy = y + pitch // 2 + int(rng.uniform(-8, 8) * sc)
                val = rng.uniform(0.42, 0.96)
                for rr in (10, 18, 27):
                    _cv2.circle(M, (cx, cy), max(3, int(rr * sc)), val * rng.uniform(0.65, 1.0), 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (cx, cy), max(3, int(rr * sc)), val * rng.uniform(0.25, 0.65), 1, lineType=_cv2.LINE_AA)
                for k in range(8):
                    a = k * math.tau / 8 + rng.uniform(-0.08, 0.08)
                    p2 = (int(cx + math.cos(a) * 34 * sc), int(cy + math.sin(a) * 34 * sc))
                    _cv2.line(M, (cx, cy), p2, val, 1, lineType=_cv2.LINE_AA)
                    if k % 2 == 0:
                        _cv2.circle(R, p2, max(1, int(3 * sc)), val * 0.20, -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _machined_titanium_fishscale_turns(shape, seed, sm, name="machined_titanium_fishscale_turns"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83502)
    M, R, CC = _base(shape, int(seed), 0.18, 0.08, 0.30, 0.025)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(26, int(64 * sc)), max(18, int(44 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx = x + off
                cy = y
                rot = rng.uniform(-8, 8)
                for k, rr in enumerate((10, 16, 22, 28)):
                    val = rng.uniform(0.34, 0.98) * (1 - k * 0.06)
                    _cv2.ellipse(M, (cx, cy), (max(4, int(rr * sc)), max(2, int(rr * 0.40 * sc))), rot, 195, 345, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(CC, (cx, cy), (max(4, int(rr * sc)), max(2, int(rr * 0.40 * sc))), rot, 195, 345, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(R, (cx, cy), (max(4, int(rr * sc)), max(2, int(rr * 0.40 * sc))), rot, 195, 345, val * 0.08, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _clearcoat_bubble_reef(shape, seed, sm, name="clearcoat_bubble_reef"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83503)
    M, R, CC = _base(shape, int(seed), 0.08, 0.06, 0.36, 0.03)
    sc = _scale(shape)
    if _CV2_OK:
        for cluster in range(_count(shape, 160, 28)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            for _ in range(int(rng.integers(5, 16))):
                px = cx + int(rng.normal(0, 22) * sc)
                py = cy + int(rng.normal(0, 22) * sc)
                rr = max(2, int(rng.uniform(4, 14) * sc))
                val = rng.uniform(0.42, 0.99)
                _cv2.circle(CC, (px, py), rr, val, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (px, py), max(1, rr - 2), val * 0.35, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (px - rr // 3, py - rr // 3), max(1, rr // 4), min(0.99, val + 0.05), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _compound_polish_flower_clusters(shape, seed, sm, name="compound_polish_flower_clusters"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83504)
    M, R, CC = _base(shape, int(seed), 0.13, 0.08, 0.31, 0.03)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 300, 50)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            petals = int(rng.integers(6, 12))
            rot = rng.uniform(0, math.tau)
            for k in range(petals):
                a = rot + k * math.tau / petals
                px = int(cx + math.cos(a) * rng.uniform(4, 12) * sc)
                py = int(cy + math.sin(a) * rng.uniform(4, 12) * sc)
                rx = max(3, int(rng.uniform(7, 18) * sc))
                ry = max(2, int(rng.uniform(3, 8) * sc))
                val = rng.uniform(0.34, 0.98)
                _cv2.ellipse(M, (px, py), (rx, ry), math.degrees(a), 0, 320, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (px, py), (rx, ry), math.degrees(a), 0, 320, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.45:
                _draw_glint(M, R, CC, cx, cy, max(2, int(4 * sc)), (0.82, 0.10, 0.94))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _ghost_lace_smoke_bouquets(shape, seed, sm, name="ghost_lace_smoke_bouquets"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83505)
    M, R, CC = _base(shape, int(seed), 0.16, 0.10, 0.24, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 210, 38)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            arms = int(rng.integers(5, 10))
            for arm in range(arms):
                pts = []
                a0 = arm * math.tau / arms + rng.uniform(-0.20, 0.20)
                for i in range(40):
                    t = i / 39
                    a = a0 + math.sin(t * math.pi * 2 + arm) * 0.55
                    r = (4 + t * rng.uniform(18, 56)) * sc
                    pts.append((int(cx + math.cos(a) * r), int(cy + math.sin(a) * r)))
                val = rng.uniform(0.30, 0.92)
                _polyline(CC, pts, val, 1)
                _polyline(M, pts, val * 0.72, 1)
                _polyline(R, pts, val * 0.10, 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _glacial_pearl_tide_cells(shape, seed, sm, name="glacial_pearl_tide_cells"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83506)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    flow = _normalize(np.sin(xx * 0.015 + yy * 0.010) + np.cos(xx * 0.012 - yy * 0.018))
    M = (0.10 + flow * 0.22).astype(np.float32)
    R = (0.20 + flow * 0.28).astype(np.float32)
    CC = (0.34 + flow * 0.42).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 280, 50)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(10, int(rng.uniform(18, 54) * sc)), max(5, int(rng.uniform(8, 26) * sc))
            rot = rng.uniform(-20, 20)
            val = rng.uniform(0.42, 0.96)
            for k in range(3):
                _cv2.ellipse(CC, (cx, cy), (rx + k * 5, ry + k * 2), rot, 0, 360, min(0.99, val + k * 0.02), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rx + k * 5, ry + k * 2), rot, 0, 360, val * 0.18, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _geode_quartz_seam_clusters(shape, seed, sm, name="geode_quartz_seam_clusters"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83507)
    M, R, CC = _base(shape, int(seed), 0.14, 0.10, 0.25, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for seam in range(-3, 11):
            x0 = int((seam - 2) * w / 6)
            spine = []
            for i in range(110):
                y = int(i * h / 109)
                x = int(x0 + y * 0.22 + math.sin(i * 0.16 + seam) * 42 * sc)
                spine.append((x, y))
            _polyline(CC, spine, rng.uniform(0.34, 0.84), 1)
            for x, y in spine[3::7]:
                for side in (-1, 1):
                    length = rng.uniform(8, 24) * sc
                    a = math.radians(90 + side * rng.uniform(25, 70))
                    tip = (int(x + math.cos(a) * length), int(y + math.sin(a) * length))
                    val = rng.uniform(0.42, 0.98)
                    _cv2.line(M, (x, y), tip, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, (x, y), tip, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _diamond_chip_orbit_field(shape, seed, sm, name="diamond_chip_orbit_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83508)
    M, R, CC = _base(shape, int(seed), 0.13, 0.08, 0.28, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 900, 150)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(2, int(rng.uniform(3, 9) * sc))
            pts = np.asarray([[cx, cy - r], [cx + r, cy], [cx, cy + r], [cx - r, cy]], dtype=np.int32)
            val = rng.uniform(0.36, 0.98)
            _cv2.polylines(CC, [pts], True, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(M, [pts], val * 0.44, lineType=_cv2.LINE_AA)
            if rng.random() < 0.24:
                _draw_glint(M, R, CC, cx, cy, max(2, int(5 * sc)), (0.90, 0.10, 0.96))
        for _ in range(_count(shape, 130, 28)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.ellipse(CC, (cx, cy), (max(12, int(rng.uniform(18, 48) * sc)), max(5, int(rng.uniform(7, 20) * sc))), rng.uniform(0, 180), 0, 210, rng.uniform(0.28, 0.72), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _bassboat_shattered_flake_panel(shape, seed, sm, name="bassboat_shattered_flake_panel"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83509)
    M, R, CC = _base(shape, int(seed), 0.16, 0.08, 0.26, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for y in range(0, h, max(44, int(120 * sc))):
            _cv2.line(CC, (0, y), (w, y + int(math.sin(y * 0.01) * 20 * sc)), 0.38, 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 2300, 340)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(2, int(rng.uniform(3, 9) * sc))
            n = int(rng.integers(3, 6))
            rot = rng.uniform(0, math.tau)
            pts = np.asarray([(int(cx + math.cos(rot + k * math.tau / n) * r * rng.uniform(0.7, 1.3)), int(cy + math.sin(rot + k * math.tau / n) * r * rng.uniform(0.7, 1.3))) for k in range(n)], dtype=np.int32)
            val = rng.uniform(0.32, 0.98)
            _cv2.fillPoly(CC, [pts], val, lineType=_cv2.LINE_AA)
            _cv2.polylines(M, [pts], True, val * 0.70, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _satin_hairline_crossgrain(shape, seed, sm, name="satin_hairline_crossgrain"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83510)
    M, R, CC = _base(shape, int(seed), 0.16, 0.08, 0.30, 0.025)
    sc = _scale(shape)
    if _CV2_OK:
        for family, angle in enumerate((math.radians(88), math.radians(72), math.radians(105))):
            count = _count(shape, 1450 if family == 0 else 450, 120)
            for _ in range(count):
                cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
                length = rng.uniform(12, 38) * sc
                a = angle + rng.uniform(-0.06, 0.06)
                p1 = (int(cx - math.cos(a) * length), int(cy - math.sin(a) * length))
                p2 = (int(cx + math.cos(a) * length), int(cy + math.sin(a) * length))
                val = rng.uniform(0.28, 0.96)
                _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, p1, p2, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _ferrofluid_compass_blooms(shape, seed, sm, name="ferrofluid_compass_blooms"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83511)
    M, R, CC = _base(shape, int(seed), 0.12, 0.16, 0.20, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 150, 30)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            spokes = int(rng.integers(12, 24))
            for k in range(spokes):
                a = k * math.tau / spokes + rng.uniform(-0.06, 0.06)
                r1 = rng.uniform(5, 14) * sc
                r2 = rng.uniform(18, 54) * sc
                p1 = (int(cx + math.cos(a) * r1), int(cy + math.sin(a) * r1))
                p2 = (int(cx + math.cos(a) * r2), int(cy + math.sin(a) * r2))
                val = rng.uniform(0.32, 0.94)
                _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, p1, p2, min(0.98, val + 0.04), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), max(2, int(5 * sc)), rng.uniform(0.14, 0.36), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _molten_chrome_blackcurrent(shape, seed, sm, name="molten_chrome_blackcurrent"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83512)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [5, 13, 34], [0.44, 0.34, 0.22], int(seed) + 1700))
    flow = _normalize(np.sin(xx * 0.018 + yy * 0.012 + warp * 8.0) + np.cos(xx * 0.041 - yy * 0.024 + warp * 5.0))
    M = (0.24 + flow * 0.56).astype(np.float32)
    R = (0.06 + flow * 0.07).astype(np.float32)
    CC = (0.30 + flow * 0.58).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 220, 42)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx = max(14, int(rng.uniform(24, 72) * sc))
            ry = max(5, int(rng.uniform(7, 24) * sc))
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, rng.uniform(0.62, 0.99), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _topographic_burl_neutral_strata(shape, seed, sm, name="topographic_burl_neutral_strata"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83513)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [4, 10, 24], [0.42, 0.36, 0.22], int(seed) + 1710))
    strata = _normalize(np.sin(yy * 0.044 + np.sin(xx * 0.010) * 6.5 + warp * 8.0))
    M = (0.18 + strata * 0.42).astype(np.float32)
    R = (0.10 + strata * 0.12).astype(np.float32)
    CC = (0.16 + strata * 0.34).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for k in range(64):
            y0 = int((k - 7) * h / 50)
            pts = []
            for x in range(0, w, max(5, int(9 * sc))):
                y = int(y0 + math.sin(x * 0.010 + k) * 30 * sc + math.sin(x * 0.030 + k * 1.5) * 7 * sc)
                pts.append((x, np.clip(y, 0, h - 1)))
            val = rng.uniform(0.34, 0.86)
            _polyline(M, pts, val, 1)
            _polyline(CC, pts, min(0.95, val + 0.04), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_abstract_expressionist_splatter(shape, seed, sm, **kwargs): return _voodoo_grisgris_pinwheel_charms(shape, seed + 1601, sm)
def rescue_aniso_grain_deep(shape, seed, sm, **kwargs): return _machined_titanium_fishscale_turns(shape, seed + 1602, sm)
def rescue_cc_fish_eye(shape, seed, sm, **kwargs): return _clearcoat_bubble_reef(shape, seed + 1603, sm)
def rescue_cc_spot_polish(shape, seed, sm, **kwargs): return _compound_polish_flower_clusters(shape, seed + 1604, sm)
def rescue_cloud_wisps(shape, seed, sm, **kwargs): return _ghost_lace_smoke_bouquets(shape, seed + 1605, sm)
def rescue_cloud_wisps_cool(shape, seed, sm, **kwargs): return _glacial_pearl_tide_cells(shape, seed + 1606, sm)
def rescue_crystal_growth(shape, seed, sm, **kwargs): return _geode_quartz_seam_clusters(shape, seed + 1607, sm)
def rescue_diamond_dust(shape, seed, sm, **kwargs): return _diamond_chip_orbit_field(shape, seed + 1608, sm)
def rescue_flake_scatter(shape, seed, sm, **kwargs): return _bassboat_shattered_flake_panel(shape, seed + 1609, sm)
def rescue_hairline_polish(shape, seed, sm, **kwargs): return _satin_hairline_crossgrain(shape, seed + 1610, sm)
def rescue_magnetic_field(shape, seed, sm, **kwargs): return _ferrofluid_compass_blooms(shape, seed + 1611, sm)
def rescue_spec_oil_film_thick(shape, seed, sm, **kwargs): return _molten_chrome_blackcurrent(shape, seed + 1612, sm)
def rescue_spec_wood_grain_fine(shape, seed, sm, **kwargs): return _topographic_burl_neutral_strata(shape, seed + 1613, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass6-iteration2:
# First contact sheet still collapsed multiple cards into purple dot fields.
# These replacements use large readable flow/facet silhouettes built from fine
# 1px/8-32px marks, and rebalance channels to avoid magenta soup.
def _occult_barbed_filagree_lattice(shape, seed, sm, name="occult_barbed_filagree_lattice"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83601)
    M, R, CC = _base(shape, int(seed), 0.20, 0.10, 0.12, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-4, 13):
            x0 = int((lane - 2) * w / 7)
            spine = []
            for i in range(120):
                y = int(i * h / 119)
                x = int(x0 + y * 0.26 + math.sin(i * 0.18 + lane) * 38 * sc)
                spine.append((x, y))
            _polyline(M, spine, rng.uniform(0.44, 0.94), 1)
            _polyline(CC, spine, rng.uniform(0.22, 0.62), 1)
            for x, y in spine[4::9]:
                for side in (-1, 1):
                    a = math.radians(90 + side * rng.uniform(25, 60))
                    p2 = (int(x + math.cos(a) * rng.uniform(10, 28) * sc), int(y + math.sin(a) * rng.uniform(10, 28) * sc))
                    _cv2.line(M, (x, y), p2, rng.uniform(0.36, 0.96), 1, lineType=_cv2.LINE_AA)
                    if rng.random() < 0.45:
                        _cv2.circle(R, p2, max(1, int(2 * sc)), rng.uniform(0.12, 0.32), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _rotary_compound_shell_overlaps(shape, seed, sm, name="rotary_compound_shell_overlaps"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83602)
    M, R, CC = _base(shape, int(seed), 0.13, 0.09, 0.31, 0.03)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(70, int(160 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx = x + int(rng.uniform(10, pitch - 10))
                cy = y + int(rng.uniform(10, pitch - 10))
                rot = rng.uniform(0, 180)
                for k in range(7):
                    rx = max(8, int((15 + k * 8) * sc))
                    ry = max(3, int(rx * rng.uniform(0.25, 0.48)))
                    start = rng.uniform(0, 260)
                    val = rng.uniform(0.32, 0.98)
                    _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 8, start, start + rng.uniform(75, 190), val, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 8, start, start + rng.uniform(75, 190), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _longform_ghost_tendril_script(shape, seed, sm, name="longform_ghost_tendril_script"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83603)
    M, R, CC = _base(shape, int(seed), 0.14, 0.11, 0.24, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-3, 12):
            y0 = int((lane - 1) * h / 7)
            pts = []
            for i in range(0, w + 30, max(5, int(9 * sc))):
                y = int(y0 + math.sin(i * 0.018 + lane) * 34 * sc + math.sin(i * 0.051) * 8 * sc)
                pts.append((i, y))
            val = rng.uniform(0.34, 0.92)
            _polyline(CC, pts, val, 1)
            _polyline(M, pts, val * 0.68, 1)
            for x, y in pts[3::10]:
                loop_r = max(4, int(rng.uniform(7, 18) * sc))
                _cv2.ellipse(CC, (x, y), (loop_r, max(2, loop_r // 2)), rng.uniform(-28, 28), 0, 300, val * rng.uniform(0.6, 1.0), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _blue_pearl_wave_ripple_lace(shape, seed, sm, name="blue_pearl_wave_ripple_lace"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83604)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    flow = _normalize(np.sin(xx * 0.012 + yy * 0.018) + np.sin(xx * 0.032 - yy * 0.014))
    M = (0.12 + flow * 0.26).astype(np.float32)
    R = (0.22 + flow * 0.26).astype(np.float32)
    CC = (0.32 + flow * 0.42).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-3, 12):
            y0 = int((band - 1) * h / 7)
            pts = []
            for x in range(0, w, max(5, int(9 * sc))):
                y = int(y0 + math.sin(x * 0.021 + band) * 32 * sc)
                pts.append((x, np.clip(y, 0, h - 1)))
            _polyline(CC, pts, rng.uniform(0.48, 0.98), 1)
            _polyline(R, pts, rng.uniform(0.20, 0.54), 1)
        for _ in range(_count(shape, 420, 70)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rr = max(2, int(rng.uniform(3, 8) * sc))
            _cv2.circle(CC, (cx, cy), rr, rng.uniform(0.64, 0.99), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _faceted_diamond_shatter_plate(shape, seed, sm, name="faceted_diamond_shatter_plate"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83605)
    M, R, CC = _base(shape, int(seed), 0.14, 0.10, 0.30, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 520, 85)):
            cx, cy = int(rng.integers(-20, w + 20)), int(rng.integers(-20, h + 20))
            r = rng.uniform(12, 36) * sc
            rot = rng.uniform(0, math.tau)
            pts = np.asarray([(int(cx + math.cos(rot + k * math.tau / 5) * r * rng.uniform(0.65, 1.25)), int(cy + math.sin(rot + k * math.tau / 5) * r * rng.uniform(0.65, 1.25))) for k in range(5)], dtype=np.int32)
            val = rng.uniform(0.34, 0.98)
            _cv2.fillPoly(M, [pts], val * 0.38, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [pts], True, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
            for p in pts:
                _cv2.line(M, (cx, cy), tuple(p), val, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx, cy), tuple(p), val * 0.10, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _ferrofluid_fieldline_filings(shape, seed, sm, name="ferrofluid_fieldline_filings"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83606)
    M, R, CC = _base(shape, int(seed), 0.12, 0.17, 0.19, 0.04)
    sc = _scale(shape)
    centers = [(rng.integers(0, w), rng.integers(0, h)) for _ in range(8)]
    if _CV2_OK:
        for cx, cy in centers:
            for rr in range(max(18, int(26 * sc)), max(60, int(135 * sc)), max(10, int(16 * sc))):
                _cv2.ellipse(M, (int(cx), int(cy)), (rr, max(5, int(rr * 0.46))), rng.uniform(0, 180), 0, 360, rng.uniform(0.28, 0.84), 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 1200, 180)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            a = rng.uniform(0, math.tau)
            length = rng.uniform(5, 15) * sc
            p1 = (int(cx - math.cos(a) * length), int(cy - math.sin(a) * length))
            p2 = (int(cx + math.cos(a) * length), int(cy + math.sin(a) * length))
            _cv2.line(CC, p1, p2, rng.uniform(0.28, 0.92), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _neutral_liquid_metal_ribbon_pool(shape, seed, sm, name="neutral_liquid_metal_ribbon_pool"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83607)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [6, 16, 38], [0.46, 0.34, 0.20], int(seed) + 1800))
    flow = _normalize(np.sin(xx * 0.018 + yy * 0.009 + warp * 8.0) + np.cos(xx * 0.032 - yy * 0.026 + warp * 5.0))
    M = (0.24 + flow * 0.42).astype(np.float32)
    R = (0.20 + flow * 0.26).astype(np.float32)
    CC = (0.26 + flow * 0.46).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 210, 40)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(16, int(rng.uniform(26, 76) * sc)), max(6, int(rng.uniform(9, 28) * sc))
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, rng.uniform(0.55, 0.96), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, rng.uniform(0.42, 0.88), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _neutral_terrain_strata_engraving(shape, seed, sm, name="neutral_terrain_strata_engraving"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83608)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [4, 10, 24], [0.42, 0.36, 0.22], int(seed) + 1810))
    strata = _normalize(np.sin(yy * 0.043 + np.sin(xx * 0.010) * 6.0 + warp * 8.0))
    M = (0.20 + strata * 0.34).astype(np.float32)
    R = (0.18 + strata * 0.24).astype(np.float32)
    CC = (0.18 + strata * 0.30).astype(np.float32)
    sc = _scale(shape)
    if _CV2_OK:
        for k in range(68):
            y0 = int((k - 7) * h / 52)
            pts = []
            for x in range(0, w, max(5, int(9 * sc))):
                y = int(y0 + math.sin(x * 0.011 + k) * 31 * sc + math.sin(x * 0.030 + k * 1.4) * 7 * sc)
                pts.append((x, np.clip(y, 0, h - 1)))
            val = rng.uniform(0.34, 0.84)
            _polyline(M, pts, val, 1)
            _polyline(CC, pts, min(0.93, val + 0.04), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_abstract_expressionist_splatter(shape, seed, sm, **kwargs): return _occult_barbed_filagree_lattice(shape, seed + 1701, sm)
def rescue_cc_spot_polish(shape, seed, sm, **kwargs): return _rotary_compound_shell_overlaps(shape, seed + 1702, sm)
def rescue_cloud_wisps(shape, seed, sm, **kwargs): return _longform_ghost_tendril_script(shape, seed + 1703, sm)
def rescue_cloud_wisps_cool(shape, seed, sm, **kwargs): return _blue_pearl_wave_ripple_lace(shape, seed + 1704, sm)
def rescue_diamond_dust(shape, seed, sm, **kwargs): return _faceted_diamond_shatter_plate(shape, seed + 1705, sm)
def rescue_magnetic_field(shape, seed, sm, **kwargs): return _ferrofluid_fieldline_filings(shape, seed + 1706, sm)
def rescue_spec_oil_film_thick(shape, seed, sm, **kwargs): return _neutral_liquid_metal_ribbon_pool(shape, seed + 1707, sm)
def rescue_spec_wood_grain_fine(shape, seed, sm, **kwargs): return _neutral_terrain_strata_engraving(shape, seed + 1708, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass6-iteration3:
# Final surgical rebuild for pass 6: cc_fish_eye/flake were too sparse; oil
# and wood still looked like noisy channel previews instead of clean materials.
def _clearcoat_rain_bead_wake_field(shape, seed, sm, name="clearcoat_rain_bead_wake_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83701)
    M, R, CC = _base(shape, int(seed), 0.08, 0.06, 0.35, 0.025)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-4, 13):
            y0 = int((band - 2) * h / 7)
            for i in range(42):
                cx = int(i * w / 38 + rng.uniform(-10, 10) * sc)
                cy = int(y0 + math.sin(i * 0.72 + band) * 32 * sc)
                rx = max(4, int(rng.uniform(7, 17) * sc))
                ry = max(3, int(rng.uniform(4, 12) * sc))
                rot = rng.uniform(-18, 18)
                val = rng.uniform(0.44, 0.99)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (max(2, rx - 2), max(2, ry - 2)), rot, 0, 360, val * 0.34, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx - rx // 3, cy - ry // 3), max(1, rx // 4), min(0.99, val + 0.06), -1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.38:
                    _cv2.line(CC, (cx + rx, cy), (cx + int(rx * 2.8), cy + int(rng.uniform(-2, 3) * sc)), val * 0.55, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _hex_cut_metalflake_panel(shape, seed, sm, name="hex_cut_metalflake_panel"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83702)
    M, R, CC = _base(shape, int(seed), 0.16, 0.08, 0.27, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(18, int(44 * sc)), max(16, int(38 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                if rng.random() < 0.62:
                    continue
                cx = x + off + int(rng.uniform(-3, 3) * sc)
                cy = y + int(rng.uniform(-3, 3) * sc)
                r = max(3, int(rng.uniform(4, 9) * sc))
                pts = _hex_points(cx, cy, r, rng.uniform(0, math.pi / 3))
                val = rng.uniform(0.34, 0.98)
                _cv2.fillPoly(CC, [pts], val, lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [pts], True, val * 0.72, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.16:
                    _draw_glint(M, R, CC, cx, cy, max(2, int(4 * sc)), (0.88, 0.10, 0.96))
        for y in range(0, h, max(50, int(130 * sc))):
            _cv2.line(CC, (0, y), (w, y + int(math.sin(y * 0.01) * 18 * sc)), 0.34, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _polished_oil_lens_ribbons(shape, seed, sm, name="polished_oil_lens_ribbons"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83703)
    M, R, CC = _base(shape, int(seed), 0.22, 0.18, 0.30, 0.025)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-5, 15):
            x0 = int((band - 3) * w / 8)
            spine = []
            for i in range(130):
                y = int(i * h / 129)
                x = int(x0 + y * 0.32 + math.sin(i * 0.13 + band) * 46 * sc)
                spine.append((x, y))
            for off, val in ((-11, 0.34), (-4, 0.62), (2, 0.92), (10, 0.48)):
                shifted = [(x + int(off * sc), y) for x, y in spine]
                _polyline(M, shifted, val, 1)
                _polyline(CC, shifted, min(0.98, val + 0.05), 1)
                _polyline(R, shifted, val * 0.38, 1)
            for x, y in spine[7::15]:
                rx, ry = max(8, int(rng.uniform(12, 32) * sc)), max(3, int(rng.uniform(5, 14) * sc))
                _cv2.ellipse(CC, (x, y), (rx, ry), rng.uniform(0, 180), 0, 360, rng.uniform(0.55, 0.98), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _engraved_topo_burl_lines(shape, seed, sm, name="engraved_topo_burl_lines"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83704)
    M, R, CC = _base(shape, int(seed), 0.22, 0.18, 0.20, 0.025)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-5, 18):
            y0 = int((band - 3) * h / 11)
            pts = []
            for x in range(0, w, max(5, int(9 * sc))):
                y = int(y0 + math.sin(x * 0.010 + band) * 30 * sc + math.sin(x * 0.027 + band * 1.4) * 8 * sc)
                pts.append((x, np.clip(y, 0, h - 1)))
            val = rng.uniform(0.36, 0.86)
            _polyline(M, pts, val, 1)
            _polyline(CC, pts, min(0.94, val + 0.05), 1)
            _polyline(R, pts, val * 0.55, 1)
        for _ in range(_count(shape, 520, 85)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(M, (x, y), max(1, int(rng.uniform(1.2, 3.0) * sc)), rng.uniform(0.30, 0.70), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_cc_fish_eye(shape, seed, sm, **kwargs): return _clearcoat_rain_bead_wake_field(shape, seed + 1801, sm)
def rescue_flake_scatter(shape, seed, sm, **kwargs): return _hex_cut_metalflake_panel(shape, seed + 1802, sm)
def rescue_spec_oil_film_thick(shape, seed, sm, **kwargs): return _polished_oil_lens_ribbons(shape, seed + 1803, sm)
def rescue_spec_wood_grain_fine(shape, seed, sm, **kwargs): return _engraved_topo_burl_lines(shape, seed + 1804, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass7:
# Remaining visual weak spots were mostly simple purple line grids, sparse
# pigtails, green/orange grime dots, and same-family dark speck fields. This
# pass pushes those into distinct, nameable silhouettes.
def _fresnel_turbine_equalizer_discs(shape, seed, sm, name="fresnel_turbine_equalizer_discs"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83801)
    M, R, CC = _base(shape, int(seed), 0.16, 0.08, 0.34, 0.025)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(88, int(210 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx, cy = x + pitch // 2, y + pitch // 2
                for rr in range(max(9, int(16 * sc)), max(48, int(86 * sc)), max(5, int(8 * sc))):
                    val = rng.uniform(0.34, 0.98)
                    _cv2.ellipse(M, (cx, cy), (rr, max(3, int(rr * 0.62))), rng.uniform(-8, 8), 0, 360, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(CC, (cx, cy), (rr, max(3, int(rr * 0.62))), rng.uniform(-8, 8), 0, 360, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
                for k in range(10):
                    a = k * math.tau / 10
                    _cv2.line(R, (cx, cy), (int(cx + math.cos(a) * 64 * sc), int(cy + math.sin(a) * 44 * sc)), rng.uniform(0.05, 0.18), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _lacquer_fan_brush_bursts(shape, seed, sm, name="lacquer_fan_brush_bursts"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83802)
    M, R, CC = _base(shape, int(seed), 0.15, 0.10, 0.22, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 260, 48)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            a0 = rng.uniform(-0.9, 0.2)
            for bristle in range(int(rng.integers(6, 13))):
                pts = []
                a = a0 + bristle * rng.uniform(0.035, 0.075)
                length = rng.uniform(18, 48) * sc
                for i in range(14):
                    t = i / 13
                    pts.append((int(cx + math.cos(a + math.sin(t * 3) * 0.08) * length * t),
                                int(cy + math.sin(a + math.sin(t * 3) * 0.08) * length * t)))
                val = rng.uniform(0.30, 0.96)
                _polyline(M, pts, val, 1)
                _polyline(CC, pts, min(0.99, val + 0.05), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _polish_orbital_moon_shells(shape, seed, sm, name="polish_orbital_moon_shells"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83803)
    M, R, CC = _base(shape, int(seed), 0.13, 0.09, 0.30, 0.025)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 480, 80)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            for k in range(int(rng.integers(4, 9))):
                rx = max(7, int((10 + k * rng.uniform(4, 8)) * sc))
                ry = max(3, int(rx * rng.uniform(0.28, 0.58)))
                start = rng.uniform(0, 260)
                val = rng.uniform(0.30, 0.96)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 11, start, start + rng.uniform(70, 210), val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 11, start, start + rng.uniform(70, 210), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _patina_copper_bloom_veins(shape, seed, sm, name="patina_copper_bloom_veins"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83804)
    M, R, CC = _base(shape, int(seed), 0.18, 0.16, 0.12, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 300, 55)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            for rr in (10, 18, 30, 44):
                rx, ry = max(4, int(rr * rng.uniform(0.7, 1.4) * sc)), max(3, int(rr * rng.uniform(0.35, 0.80) * sc))
                val = rng.uniform(0.30, 0.90)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, val * 0.25, 1, lineType=_cv2.LINE_AA)
            for k in range(3):
                a = rng.uniform(0, math.tau)
                _cv2.line(CC, (cx, cy), (int(cx + math.cos(a) * 42 * sc), int(cy + math.sin(a) * 22 * sc)), rng.uniform(0.24, 0.70), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _vinyl_lift_torn_edge_rivers(shape, seed, sm, name="vinyl_lift_torn_edge_rivers"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83805)
    M, R, CC = _base(shape, int(seed), 0.14, 0.12, 0.28, 0.03)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-3, 12):
            y0 = int((lane - 1) * h / 7)
            top = []
            for x in range(-20, w + 30, max(5, int(9 * sc))):
                y = int(y0 + math.sin(x * 0.021 + lane) * 30 * sc + rng.uniform(-4, 4) * sc)
                top.append((x, y))
            _polyline(CC, top, rng.uniform(0.46, 0.96), 1)
            _polyline(M, top, rng.uniform(0.34, 0.82), 1)
            for x, y in top[3::8]:
                rx, ry = max(4, int(rng.uniform(6, 16) * sc)), max(2, int(rng.uniform(3, 8) * sc))
                _cv2.ellipse(CC, (x, y), (rx, ry), rng.uniform(-20, 20), 210, 60, rng.uniform(0.50, 0.98), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x - rx, y), (x + rx, y + int(ry * 0.3)), rng.uniform(0.08, 0.22), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _gasket_grime_blueprint_loops(shape, seed, sm, name="gasket_grime_blueprint_loops"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83806)
    M, R, CC = _base(shape, int(seed), 0.11, 0.22, 0.12, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(90, int(210 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx, cy = x + pitch // 2, y + pitch // 2
                for k in range(4):
                    rx = max(14, int((25 + k * 14) * sc))
                    ry = max(6, int((11 + k * 6) * sc))
                    val = rng.uniform(0.34, 0.88)
                    _cv2.ellipse(R, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, val * 0.28, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(M, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, val, 1, lineType=_cv2.LINE_AA)
                for k in range(6):
                    a = k * math.tau / 6
                    _cv2.circle(CC, (int(cx + math.cos(a) * 54 * sc), int(cy + math.sin(a) * 24 * sc)), max(2, int(5 * sc)), rng.uniform(0.24, 0.64), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _carbon_forged_large_plate_shards(shape, seed, sm, name="carbon_forged_large_plate_shards"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83807)
    M, R, CC = _base(shape, int(seed), 0.07, 0.11, 0.16, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 580, 100)):
            cx, cy = int(rng.integers(-20, w + 20)), int(rng.integers(-20, h + 20))
            n = int(rng.integers(4, 8))
            rad = rng.uniform(16, 46) * sc
            rot = rng.uniform(0, math.tau)
            pts = np.asarray([(int(cx + math.cos(rot + k * math.tau / n + rng.uniform(-0.22, 0.22)) * rad * rng.uniform(0.55, 1.35)), int(cy + math.sin(rot + k * math.tau / n + rng.uniform(-0.22, 0.22)) * rad * rng.uniform(0.55, 1.35))) for k in range(n)], dtype=np.int32)
            val = float(rng.choice([0.16, 0.26, 0.38, 0.52, 0.66, 0.82, 0.94]))
            _cv2.fillPoly(M, [pts], val * 0.72, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts], val * 0.28, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [pts], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _neural_green_circuit_branches(shape, seed, sm, name="neural_green_circuit_branches"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83808)
    M, R, CC = _base(shape, int(seed), 0.12, 0.18, 0.15, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for root in range(-3, 12):
            x = int((root - 2) * w / 7 + rng.uniform(-25, 25) * sc)
            y = -20
            trunk = [(x, y)]
            while y < h + 20:
                x += int(rng.uniform(-24, 28) * sc)
                y += int(rng.uniform(14, 32) * sc)
                trunk.append((x, y))
                if rng.random() < 0.42:
                    bx, by = x, y
                    branch = [(bx, by)]
                    for _ in range(int(rng.integers(4, 10))):
                        bx += int(rng.uniform(-22, 22) * sc)
                        by += int(rng.uniform(7, 20) * sc)
                        branch.append((bx, by))
                    _polyline(M, branch, rng.uniform(0.34, 0.90), 1)
                    _polyline(CC, branch, rng.uniform(0.25, 0.70), 1)
            _polyline(M, trunk, rng.uniform(0.40, 0.96), 1)
            _polyline(CC, trunk, rng.uniform(0.28, 0.78), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _nordic_knotwork_medallions(shape, seed, sm, name="nordic_knotwork_medallions"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83809)
    M, R, CC = _base(shape, int(seed), 0.18, 0.10, 0.16, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        pitch = max(94, int(225 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx, cy = x + pitch // 2, y + pitch // 2
                for rr in (28, 45, 62):
                    _cv2.circle(M, (cx, cy), max(8, int(rr * sc)), rng.uniform(0.36, 0.92), 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (cx, cy), max(8, int(rr * sc)), rng.uniform(0.22, 0.60), 1, lineType=_cv2.LINE_AA)
                for k in range(8):
                    a = k * math.tau / 8
                    p1 = (int(cx + math.cos(a) * 18 * sc), int(cy + math.sin(a) * 18 * sc))
                    p2 = (int(cx + math.cos(a + 0.35) * 70 * sc), int(cy + math.sin(a + 0.35) * 70 * sc))
                    _cv2.line(M, p1, p2, rng.uniform(0.42, 0.96), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _enamel_drip_rain_beads(shape, seed, sm, name="enamel_drip_rain_beads"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83810)
    M, R, CC = _base(shape, int(seed), 0.16, 0.09, 0.28, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for x in range(-10, w + 10, max(9, int(22 * sc))):
            top = int(rng.integers(-80, h))
            length = int(rng.uniform(80, 360) * sc)
            pts = []
            for k in range(36):
                pts.append((int(np.clip(x + math.sin(k * 0.38 + x) * 8 * sc, 0, w - 1)), int(np.clip(top + k * length / 35, 0, h - 1))))
            val = rng.uniform(0.36, 0.98)
            _polyline(CC, pts, min(0.99, val + 0.06), 1)
            _polyline(M, pts, val, 1)
            for p in pts[8::12]:
                _cv2.circle(CC, p, max(2, int(rng.uniform(4, 9) * sc)), min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _barbed_wire_thorn_crowns(shape, seed, sm, name="barbed_wire_thorn_crowns"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83811)
    M, R, CC = _base(shape, int(seed), 0.15, 0.11, 0.20, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-3, 12):
            y0 = int((lane - 1) * h / 7)
            pts = []
            for x in range(0, w, max(5, int(9 * sc))):
                y = int(y0 + math.sin(x * 0.022 + lane) * 27 * sc)
                pts.append((x, y))
            _polyline(M, pts, rng.uniform(0.42, 0.96), 1)
            _polyline(CC, pts, rng.uniform(0.28, 0.80), 1)
            for x, y in pts[4::9]:
                for side in (-1, 1):
                    p2 = (int(x + side * rng.uniform(8, 20) * sc), int(y + rng.uniform(-13, 13) * sc))
                    _cv2.line(M, (x, y), p2, rng.uniform(0.48, 0.98), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, (x, y), p2, rng.uniform(0.08, 0.22), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _meteor_comet_orbital_scratches(shape, seed, sm, name="meteor_comet_orbital_scratches"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83812)
    M, R, CC = _base(shape, int(seed), 0.12, 0.08, 0.24, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 420, 70)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(18, int(rng.uniform(30, 90) * sc)), max(8, int(rng.uniform(12, 42) * sc))
            rot = rng.uniform(0, 180)
            start = rng.uniform(0, 300)
            val = rng.uniform(0.32, 0.92)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, start, start + rng.uniform(50, 190), val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, start, start + rng.uniform(50, 190), val * 0.72, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.55:
                a = math.radians(rot + start)
                _draw_glint(M, R, CC, int(cx + math.cos(a) * rx), int(cy + math.sin(a) * ry), max(2, int(5 * sc)), (0.88, 0.10, 0.94))
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_abstract_retro_wave(shape, seed, sm, **kwargs): return _fresnel_turbine_equalizer_discs(shape, seed + 1901, sm)
def rescue_brushstroke_bold(shape, seed, sm, **kwargs): return _lacquer_fan_brush_bursts(shape, seed + 1902, sm)
def rescue_buffer_swirl(shape, seed, sm, **kwargs): return _polish_orbital_moon_shells(shape, seed + 1903, sm)
def rescue_copper_patina_drip(shape, seed, sm, **kwargs): return _patina_copper_bloom_veins(shape, seed + 1904, sm)
def rescue_decal_lift_edge(shape, seed, sm, **kwargs): return _vinyl_lift_torn_edge_rivers(shape, seed + 1905, sm)
def rescue_engine_bay_grime(shape, seed, sm, **kwargs): return _gasket_grime_blueprint_loops(shape, seed + 1906, sm)
def rescue_forged_carbon_chip(shape, seed, sm, **kwargs): return _carbon_forged_large_plate_shards(shape, seed + 1907, sm)
def rescue_neural_dendrite(shape, seed, sm, **kwargs): return _neural_green_circuit_branches(shape, seed + 1908, sm)
def rescue_nordic_rune_field(shape, seed, sm, **kwargs): return _nordic_knotwork_medallions(shape, seed + 1909, sm)
def rescue_paint_drip_edge(shape, seed, sm, **kwargs): return _enamel_drip_rain_beads(shape, seed + 1910, sm)
def rescue_razor_wire_coil(shape, seed, sm, **kwargs): return _barbed_wire_thorn_crowns(shape, seed + 1911, sm)
def rescue_sparkle_comet(shape, seed, sm, **kwargs): return _meteor_comet_orbital_scratches(shape, seed + 1912, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass7-iteration2:
# Contact sheet rejected sparse brush/copper/forged/decal/razor/comet outputs.
# These make those thumbnails read as intentional material systems.
def _sumi_lacquer_ribbon_sweeps(shape, seed, sm, name="sumi_lacquer_ribbon_sweeps"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83901)
    M, R, CC = _base(shape, int(seed), 0.15, 0.10, 0.22, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-5, 15):
            x0 = int((band - 3) * w / 8)
            spine = []
            for i in range(120):
                y = int(i * h / 119)
                x = int(x0 + y * 0.38 + math.sin(i * 0.11 + band) * 50 * sc)
                spine.append((x, y))
            for off, val in ((-9, 0.34), (-4, 0.58), (2, 0.92), (8, 0.46)):
                shifted = [(x + int(off * sc), y) for x, y in spine]
                _polyline(M, shifted, val, 1)
                _polyline(CC, shifted, min(0.99, val + 0.05), 1)
            for x, y in spine[6::12]:
                _cv2.line(M, (x, y), (x + int(rng.uniform(10, 28) * sc), y + int(rng.uniform(-8, 8) * sc)), rng.uniform(0.34, 0.92), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _copper_patina_topo_lakes(shape, seed, sm, name="copper_patina_topo_lakes"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83902)
    M, R, CC = _base(shape, int(seed), 0.18, 0.16, 0.13, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 180, 34)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            for k in range(5):
                rx = max(8, int((14 + k * rng.uniform(7, 13)) * sc))
                ry = max(4, int(rx * rng.uniform(0.35, 0.78)))
                val = rng.uniform(0.34, 0.92)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 5, 0, 360, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 5, 20, 220, val * 0.55, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rx, ry), rot + k * 5, 0, 360, val * 0.22, 1, lineType=_cv2.LINE_AA)
        for lane in range(-3, 10):
            pts = []
            y0 = int((lane - 1) * h / 6)
            for x in range(0, w, max(6, int(10 * sc))):
                y = int(y0 + math.sin(x * 0.015 + lane) * 28 * sc)
                pts.append((x, np.clip(y, 0, h - 1)))
            _polyline(M, pts, rng.uniform(0.28, 0.70), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _vinyl_lift_flap_shingles(shape, seed, sm, name="vinyl_lift_flap_shingles"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83903)
    M, R, CC = _base(shape, int(seed), 0.14, 0.12, 0.30, 0.03)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(32, int(84 * sc)), max(24, int(62 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                if rng.random() < 0.28:
                    continue
                cx, cy = x + off, y
                rw, rh = int(rng.uniform(12, 27) * sc), int(rng.uniform(7, 16) * sc)
                rot = rng.uniform(-24, 24)
                val = rng.uniform(0.40, 0.98)
                _cv2.ellipse(CC, (cx, cy), (rw, rh), rot, 205, 60, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (rw, rh), rot, 205, 60, val * 0.70, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx - rw, cy), (cx + rw, cy + int(rh * 0.45)), val * 0.14, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _forged_carbon_diagonal_shingle_plates(shape, seed, sm, name="forged_carbon_diagonal_shingle_plates"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83904)
    M, R, CC = _base(shape, int(seed), 0.07, 0.11, 0.15, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-4, 14):
            x0 = int((lane - 3) * w / 8)
            for i in range(-2, 35):
                cy = int(i * h / 31)
                cx = int(x0 + cy * 0.35 + math.sin(i * 0.4 + lane) * 28 * sc)
                long = rng.uniform(20, 54) * sc
                short = rng.uniform(7, 18) * sc
                rot = math.radians(rng.uniform(-22, 22))
                pts = []
                for a, rr in ((0, long), (1.8, short), (math.pi, long * 0.8), (4.4, short)):
                    pts.append((int(cx + math.cos(rot + a) * rr), int(cy + math.sin(rot + a) * rr)))
                poly = np.asarray(pts, dtype=np.int32)
                val = float(rng.choice([0.16, 0.28, 0.40, 0.54, 0.70, 0.88]))
                _cv2.fillPoly(M, [poly], val * 0.76, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [poly], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, pts[0], pts[2], val * 0.14, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _concertina_barb_loop_crowns(shape, seed, sm, name="concertina_barb_loop_crowns"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83905)
    M, R, CC = _base(shape, int(seed), 0.15, 0.11, 0.20, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-3, 12):
            y0 = int((lane - 1) * h / 7)
            for i in range(-1, 38):
                cx = int(i * w / 34 + math.sin(i * 0.45 + lane) * 22 * sc)
                cy = int(y0 + math.sin(i * 0.72 + lane) * 30 * sc)
                rx, ry = max(5, int(rng.uniform(9, 22) * sc)), max(3, int(rng.uniform(5, 12) * sc))
                val = rng.uniform(0.36, 0.96)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rng.uniform(-28, 28), 0, 360, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rng.uniform(-28, 28), 0, 360, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
                for side in (-1, 1):
                    p2 = (cx + side * int(rx * 1.35), cy + int(rng.uniform(-ry, ry)))
                    _cv2.line(M, (cx, cy), p2, rng.uniform(0.42, 0.98), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _comet_orbital_star_charts(shape, seed, sm, name="comet_orbital_star_charts"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 83906)
    M, R, CC = _base(shape, int(seed), 0.12, 0.08, 0.24, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 360, 65)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(18, int(rng.uniform(26, 82) * sc)), max(8, int(rng.uniform(12, 38) * sc))
            rot = rng.uniform(0, 180)
            start = rng.uniform(0, 300)
            span = rng.uniform(70, 240)
            val = rng.uniform(0.32, 0.92)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, start, start + span, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, start, start + span, val * 0.75, 1, lineType=_cv2.LINE_AA)
            a = math.radians(rot + start + span)
            if rng.random() < 0.65:
                _draw_glint(M, R, CC, int(cx + math.cos(a) * rx), int(cy + math.sin(a) * ry), max(2, int(5 * sc)), (0.88, 0.10, 0.96))
        for _ in range(_count(shape, 900, 140)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(CC, (cx, cy), max(1, int(rng.uniform(1.2, 3.0) * sc)), rng.uniform(0.42, 0.98), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_brushstroke_bold(shape, seed, sm, **kwargs): return _sumi_lacquer_ribbon_sweeps(shape, seed + 2001, sm)
def rescue_copper_patina_drip(shape, seed, sm, **kwargs): return _copper_patina_topo_lakes(shape, seed + 2002, sm)
def rescue_decal_lift_edge(shape, seed, sm, **kwargs): return _vinyl_lift_flap_shingles(shape, seed + 2003, sm)
def rescue_forged_carbon_chip(shape, seed, sm, **kwargs): return _forged_carbon_diagonal_shingle_plates(shape, seed + 2004, sm)
def rescue_razor_wire_coil(shape, seed, sm, **kwargs): return _concertina_barb_loop_crowns(shape, seed + 2005, sm)
def rescue_sparkle_comet(shape, seed, sm, **kwargs): return _comet_orbital_star_charts(shape, seed + 2006, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass8:
# Owner verdict snippet: "WEAK/REPEATING/LAZY ... random noise ... EVERY new pattern MUST be 100% unique".
# Visual movement: stale REBUILD/MIXED thumbnails replaced with separate fine-detail construction grammars.
def _guilloche_engine_turn_fans(shape, seed, sm, name="guilloche_engine_turn_fans"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84001)
    M, R, CC = _base(shape, int(seed), 0.13, 0.10, 0.19, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        step = max(30, int(82 * sc))
        for row, cy in enumerate(range(-step, h + step, step)):
            for col, cx in enumerate(range(-step, w + step, step)):
                cx2 = cx + (step // 2 if row % 2 else 0)
                rot = rng.uniform(-12, 12) + ((row + col) % 4) * 22
                for k in range(9):
                    r = max(5, int((9 + k * 3.2) * sc))
                    start = 195 + k * 7
                    span = 120 + rng.uniform(-18, 18)
                    val = float(rng.choice([0.24, 0.34, 0.46, 0.58, 0.70, 0.84, 0.96]))
                    _cv2.ellipse(M, (cx2, cy), (r, max(3, int(r * 0.42))), rot, start, start + span, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(CC, (cx2, cy), (r, max(3, int(r * 0.42))), rot, start + 12, start + span - 8, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.72:
                    _draw_glint(M, R, CC, cx2, cy, max(2, int(4 * sc)), (0.74, 0.11, 0.86))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _rotor_soot_crescent_fingerprint(shape, seed, sm, name="rotor_soot_crescent_fingerprint"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84002)
    M, R, CC = _base(shape, int(seed), 0.12, 0.16, 0.12, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 190, 42)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(-35, 35)
            rx, ry = max(7, int(rng.uniform(15, 34) * sc)), max(3, int(rng.uniform(4, 10) * sc))
            val = rng.uniform(0.22, 0.82)
            for k in range(3):
                _cv2.ellipse(M, (cx, cy), (rx + int(k * 5 * sc), ry + int(k * 2 * sc)), rot + k * 4, 205, 340, val * (0.72 + k * 0.12), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rx + int(k * 5 * sc), ry + int(k * 2 * sc)), rot + k * 4, 205, 340, val * 0.22, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.65:
                for j in range(6):
                    x = int(cx + rng.normal(0, rx * 0.45))
                    y = int(cy + rng.normal(0, ry * 0.85))
                    _cv2.circle(CC, (x, y), max(1, int(rng.uniform(1.3, 2.8) * sc)), rng.uniform(0.30, 0.80), -1, lineType=_cv2.LINE_AA)
        for lane in range(-2, 11):
            pts = []
            y0 = int((lane - 1) * h / 7)
            for x in range(0, w, max(7, int(12 * sc))):
                y = int(y0 + math.sin(x * 0.018 + lane) * 18 * sc + x * 0.035)
                pts.append((x, np.clip(y, 0, h - 1)))
            _polyline(CC, pts, rng.uniform(0.24, 0.58), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _clearcoat_lens_bead_rivulets(shape, seed, sm, name="clearcoat_lens_bead_rivulets"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84003)
    M, R, CC = _base(shape, int(seed), 0.10, 0.08, 0.28, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-4, 13):
            x0 = int((lane - 2) * w / 8)
            spine = []
            for i in range(112):
                y = int(i * h / 111)
                x = int(x0 + y * 0.22 + math.sin(i * 0.17 + lane) * 24 * sc)
                spine.append((x, y))
            for off, val in ((-5, 0.30), (0, 0.82), (5, 0.48)):
                _polyline(CC, [(x + int(off * sc), y) for x, y in spine], val, 1)
            for x, y in spine[5::10]:
                r = max(2, int(rng.uniform(4, 9) * sc))
                _cv2.ellipse(CC, (x, y), (r, max(2, r // 2)), rng.uniform(-25, 25), 0, 360, rng.uniform(0.58, 0.99), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (x + int(r * 0.35), y - int(r * 0.20)), max(1, r // 3), rng.uniform(0.42, 0.86), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _polish_compound_oyster_shells(shape, seed, sm, name="polish_compound_oyster_shells"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84004)
    M, R, CC = _base(shape, int(seed), 0.14, 0.09, 0.26, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 180, 36)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            fan = rng.uniform(70, 145)
            for k in range(7):
                rx = max(4, int((7 + k * 3.2) * sc))
                ry = max(2, int(rx * rng.uniform(0.32, 0.52)))
                val = rng.uniform(0.26, 0.96)
                start = 190 - fan * 0.5
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, start, start + fan, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot, start + 10, start + fan - 8, val * 0.72, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.5:
                _cv2.line(R, (cx, cy), (cx + int(math.cos(math.radians(rot)) * 22 * sc), cy + int(math.sin(math.radians(rot)) * 22 * sc)), rng.uniform(0.08, 0.20), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _seance_smoke_sigil_threads(shape, seed, sm, name="seance_smoke_sigil_threads"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84005)
    M, R, CC = _base(shape, int(seed), 0.10, 0.07, 0.23, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 90, 18)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            pts = []
            angle = rng.uniform(0, math.tau)
            for k in range(46):
                angle += rng.uniform(-0.16, 0.22)
                rad = (k * rng.uniform(1.5, 2.4)) * sc
                x = int(cx + math.cos(angle + k * 0.10) * rad)
                y = int(cy + math.sin(angle * 0.7 + k * 0.12) * rad)
                pts.append((np.clip(x, 0, w - 1), np.clip(y, 0, h - 1)))
            _polyline(CC, pts, rng.uniform(0.30, 0.88), 1)
            _polyline(M, pts[::2], rng.uniform(0.20, 0.72), 1)
            if rng.random() < 0.58:
                r = max(4, int(rng.uniform(8, 18) * sc))
                _cv2.ellipse(M, (cx, cy), (r, max(3, int(r * 0.46))), rng.uniform(0, 180), 25, 320, rng.uniform(0.34, 0.82), 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 260, 48)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(CC, (x, y), max(1, int(rng.uniform(1, 2.5) * sc)), rng.uniform(0.28, 0.82), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _candle_ember_spirit_veils(shape, seed, sm, name="candle_ember_spirit_veils"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84006)
    M, R, CC = _base(shape, int(seed), 0.13, 0.12, 0.15, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-3, 13):
            x0 = int((lane - 2) * w / 7)
            pts = []
            for i in range(120):
                y = int(i * h / 119)
                x = int(x0 + math.sin(i * 0.13 + lane) * 34 * sc + math.sin(i * 0.041) * 15 * sc)
                pts.append((np.clip(x, 0, w - 1), y))
            _polyline(M, pts, rng.uniform(0.34, 0.92), 1)
            _polyline(CC, [(x + int(3 * sc), y) for x, y in pts], rng.uniform(0.28, 0.74), 1)
            for x, y in pts[10::17]:
                flame = np.asarray([(x, y - int(9 * sc)), (x - int(4 * sc), y + int(4 * sc)), (x, y + int(9 * sc)), (x + int(4 * sc), y + int(4 * sc))], dtype=np.int32)
                _cv2.polylines(M, [flame], True, rng.uniform(0.46, 0.98), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (x, y), max(1, int(2.5 * sc)), rng.uniform(0.60, 0.99), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _geode_quartz_fracture_nests(shape, seed, sm, name="geode_quartz_fracture_nests"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84007)
    M, R, CC = _base(shape, int(seed), 0.12, 0.09, 0.20, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 130, 25)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            arms = int(rng.integers(4, 8))
            for a in range(arms):
                ang = rng.uniform(0, math.tau)
                length = rng.uniform(18, 48) * sc
                pts = [(cx, cy)]
                for k in range(1, 5):
                    x = int(cx + math.cos(ang + rng.normal(0, 0.09)) * length * k / 4)
                    y = int(cy + math.sin(ang + rng.normal(0, 0.09)) * length * k / 4)
                    pts.append((np.clip(x, 0, w - 1), np.clip(y, 0, h - 1)))
                val = rng.uniform(0.32, 0.98)
                _polyline(CC, pts, min(0.99, val + 0.04), 1)
                _polyline(M, pts, val * 0.76, 1)
                tip = pts[-1]
                for side in (-1, 1):
                    barb = (int(tip[0] - math.cos(ang + side * 0.72) * 10 * sc), int(tip[1] - math.sin(ang + side * 0.72) * 10 * sc))
                    _cv2.line(M, tip, barb, rng.uniform(0.36, 0.90), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.5:
                _cv2.circle(R, (cx, cy), max(2, int(rng.uniform(3, 7) * sc)), rng.uniform(0.10, 0.24), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _faceted_diamond_fault_shards(shape, seed, sm, name="faceted_diamond_fault_shards"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84008)
    M, R, CC = _base(shape, int(seed), 0.11, 0.08, 0.21, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 220, 42)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = rng.uniform(8, 24) * sc
            rot = rng.uniform(0, math.tau)
            pts = []
            for k in range(4):
                rr = r * rng.uniform(0.55, 1.15)
                a = rot + k * math.pi / 2 + rng.uniform(-0.25, 0.25)
                pts.append((int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr)))
            poly = np.asarray(pts, dtype=np.int32)
            val = rng.uniform(0.24, 0.96)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(M, [poly], True, val * 0.76, 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, pts[0], pts[2], rng.uniform(0.30, 0.92), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, pts[1], pts[3], rng.uniform(0.08, 0.20), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _constellation_prism_microcharts(shape, seed, sm, name="constellation_prism_microcharts"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84009)
    M, R, CC = _base(shape, int(seed), 0.10, 0.07, 0.24, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        stars = []
        for _ in range(_count(shape, 650, 115)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            stars.append((x, y))
            r = max(1, int(rng.uniform(1.0, 3.0) * sc))
            val = rng.uniform(0.32, 0.98)
            _cv2.circle(CC, (x, y), r, min(0.99, val + 0.04), -1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.14:
                _draw_glint(M, R, CC, x, y, max(2, int(4 * sc)), (0.86, 0.10, 0.94))
        for i in range(0, len(stars) - 3, 5):
            if rng.random() < 0.46:
                chain = stars[i:i + int(rng.integers(2, 5))]
                _polyline(M, chain, rng.uniform(0.24, 0.62), 1)
        for _ in range(_count(shape, 65, 12)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(9, int(rng.uniform(14, 34) * sc)), max(4, int(rng.uniform(5, 13) * sc))
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rng.uniform(0, 180), rng.uniform(0, 90), rng.uniform(160, 310), rng.uniform(0.24, 0.78), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _pangolin_cloisonne_scale_armor(shape, seed, sm, name="pangolin_cloisonne_scale_armor"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84010)
    M, R, CC = _base(shape, int(seed), 0.14, 0.11, 0.18, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(22, int(52 * sc)), max(18, int(42 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx = x + off + int(math.sin(row * 0.8) * 7 * sc)
                cy = y
                r1, r2 = int(rng.uniform(12, 24) * sc), int(rng.uniform(9, 18) * sc)
                pts = np.asarray([
                    (cx, cy - r2),
                    (cx + r1, cy - int(r2 * 0.12)),
                    (cx + int(r1 * 0.52), cy + r2),
                    (cx, cy + int(r2 * 0.62)),
                    (cx - int(r1 * 0.52), cy + r2),
                    (cx - r1, cy - int(r2 * 0.12)),
                ], dtype=np.int32)
                val = rng.uniform(0.22, 0.94)
                _cv2.polylines(CC, [pts], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, tuple(pts[0]), tuple(pts[3]), val * 0.72, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, tuple(pts[1]), tuple(pts[5]), val * 0.18, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.36:
                    _draw_glint(M, R, CC, cx, cy, max(2, int(3.5 * sc)), (0.72, 0.12, 0.90))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _barbed_concertina_spiderwire(shape, seed, sm, name="barbed_concertina_spiderwire"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84011)
    M, R, CC = _base(shape, int(seed), 0.12, 0.10, 0.20, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-3, 11):
            base_y = int((lane - 1) * h / 6)
            for i in range(-1, 32):
                cx = int(i * w / 29 + math.sin(i * 0.7 + lane) * 20 * sc)
                cy = int(base_y + math.sin(i * 0.58 + lane) * 25 * sc)
                rx, ry = max(6, int(rng.uniform(10, 22) * sc)), max(3, int(rng.uniform(5, 11) * sc))
                rot = rng.uniform(-35, 35)
                val = rng.uniform(0.32, 0.96)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 0, 360, val * 0.72, 1, lineType=_cv2.LINE_AA)
                for a in (rot - 45, rot + 45):
                    p1 = (int(cx + math.cos(math.radians(a)) * rx * 0.75), int(cy + math.sin(math.radians(a)) * ry * 0.75))
                    p2 = (int(p1[0] + math.cos(math.radians(a + 70)) * 12 * sc), int(p1[1] + math.sin(math.radians(a + 70)) * 12 * sc))
                    _cv2.line(M, p1, p2, rng.uniform(0.46, 0.99), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, p1, p2, rng.uniform(0.08, 0.22), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _tirewall_rubber_transfer_shelves(shape, seed, sm, name="tirewall_rubber_transfer_shelves"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84012)
    M, R, CC = _base(shape, int(seed), 0.11, 0.14, 0.13, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 230, 46)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            length = rng.uniform(18, 54) * sc
            angle = rng.uniform(-0.45, 0.45)
            pts = []
            for k in range(8):
                x = int(cx + math.cos(angle) * length * (k / 7 - 0.5))
                y = int(cy + math.sin(angle) * length * (k / 7 - 0.5) + math.sin(k * 0.9) * 4 * sc)
                pts.append((np.clip(x, 0, w - 1), np.clip(y, 0, h - 1)))
            val = rng.uniform(0.24, 0.86)
            _polyline(M, pts, val, 1)
            _polyline(R, [(x, y + max(1, int(2 * sc))) for x, y in pts], val * 0.20, 1)
            if rng.random() < 0.42:
                _cv2.ellipse(CC, (cx, cy), (max(5, int(length * 0.35)), max(2, int(5 * sc))), math.degrees(angle), 190, 350, rng.uniform(0.22, 0.64), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_aniso_grain_deep(shape, seed, sm, **kwargs): return _guilloche_engine_turn_fans(shape, seed + 2101, sm)
def rescue_brake_dust_buildup(shape, seed, sm, **kwargs): return _rotor_soot_crescent_fingerprint(shape, seed + 2102, sm)
def rescue_cc_gloss_stripe(shape, seed, sm, **kwargs): return _clearcoat_lens_bead_rivulets(shape, seed + 2103, sm)
def rescue_cc_spot_polish(shape, seed, sm, **kwargs): return _polish_compound_oyster_shells(shape, seed + 2104, sm)
def rescue_cloud_wisps(shape, seed, sm, **kwargs): return _seance_smoke_sigil_threads(shape, seed + 2105, sm)
def rescue_cloud_wisps_warm(shape, seed, sm, **kwargs): return _candle_ember_spirit_veils(shape, seed + 2106, sm)
def rescue_crystal_growth(shape, seed, sm, **kwargs): return _geode_quartz_fracture_nests(shape, seed + 2107, sm)
def rescue_diamond_dust(shape, seed, sm, **kwargs): return _faceted_diamond_fault_shards(shape, seed + 2108, sm)
def rescue_micro_sparkle(shape, seed, sm, **kwargs): return _constellation_prism_microcharts(shape, seed + 2109, sm)
def rescue_pangolin_armor(shape, seed, sm, **kwargs): return _pangolin_cloisonne_scale_armor(shape, seed + 2110, sm)
def rescue_razor_wire_coil(shape, seed, sm, **kwargs): return _barbed_concertina_spiderwire(shape, seed + 2111, sm)
def rescue_wear_scuff(shape, seed, sm, **kwargs): return _tirewall_rubber_transfer_shelves(shape, seed + 2112, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass8-iteration2:
# First pass still read too faint/repeating in the contact sheet; this pass raises density and silhouette identity.
def _fan_cut_engine_turn_rosettes(shape, seed, sm, name="fan_cut_engine_turn_rosettes"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84101)
    M, R, CC = _base(shape, int(seed), 0.11, 0.08, 0.18, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        step = max(18, int(48 * sc))
        for row, cy in enumerate(range(-step, h + step, step)):
            for col, cx in enumerate(range(-step, w + step, step)):
                cx2 = cx + (step // 2 if row % 2 else 0)
                rot = -35 + ((row * 17 + col * 11) % 70)
                for k, val in enumerate((0.30, 0.42, 0.54, 0.66, 0.78, 0.92)):
                    r = max(3, int((6 + k * 2.7) * sc))
                    _cv2.ellipse(CC, (cx2, cy), (r, max(2, int(r * 0.45))), rot + k * 5, 200, 335, min(0.99, val + rng.uniform(-0.04, 0.06)), 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(M, (cx2, cy), (r, max(2, int(r * 0.45))), rot + k * 5, 205, 330, val * 0.78, 1, lineType=_cv2.LINE_AA)
                if (row + col) % 3 == 0:
                    _draw_glint(M, R, CC, cx2, cy, max(2, int(3.5 * sc)), (0.78, 0.10, 0.88))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _brake_dust_rotor_arc_storm(shape, seed, sm, name="brake_dust_rotor_arc_storm"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84102)
    M, R, CC = _base(shape, int(seed), 0.10, 0.15, 0.11, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-2, 13):
            y0 = int((lane - 1) * h / 8)
            for i in range(-2, 42):
                cx = int(i * w / 38 + math.sin(i + lane) * 8 * sc)
                cy = int(y0 + math.sin(i * 0.55 + lane) * 20 * sc)
                rx, ry = max(7, int(rng.uniform(12, 28) * sc)), max(2, int(rng.uniform(3, 8) * sc))
                rot = rng.uniform(-18, 18)
                val = rng.uniform(0.24, 0.90)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 190, 348, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rx, ry), rot, 190, 348, val * 0.22, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.42:
                    _cv2.circle(CC, (cx + int(rx * 0.45), cy), max(1, int(2 * sc)), rng.uniform(0.38, 0.82), -1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 900, 170)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(R, (x, y), max(1, int(rng.uniform(1, 2) * sc)), rng.uniform(0.08, 0.24), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _clearcoat_rain_lens_cells(shape, seed, sm, name="clearcoat_rain_lens_cells"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84103)
    M, R, CC = _base(shape, int(seed), 0.09, 0.07, 0.26, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(24, int(58 * sc)), max(18, int(42 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx = x + off + int(math.sin(row) * 7 * sc)
                cy = y + int(rng.uniform(-7, 7) * sc)
                rx, ry = max(5, int(rng.uniform(9, 21) * sc)), max(3, int(rng.uniform(4, 10) * sc))
                val = rng.uniform(0.36, 0.98)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rng.uniform(-28, 28), 0, 360, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (max(2, rx // 2), max(1, ry // 2)), rng.uniform(-28, 28), 210, 330, val * 0.66, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.58:
                    _cv2.line(CC, (cx + rx, cy), (cx + rx + int(rng.uniform(8, 20) * sc), cy + int(rng.uniform(-5, 5) * sc)), rng.uniform(0.28, 0.82), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _compound_buff_orbital_shell_field(shape, seed, sm, name="compound_buff_orbital_shell_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84104)
    M, R, CC = _base(shape, int(seed), 0.12, 0.08, 0.27, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        step = max(28, int(68 * sc))
        for row, cy in enumerate(range(-step, h + step, step)):
            for col, cx in enumerate(range(-step, w + step, step)):
                cx2 = cx + (step // 2 if row % 2 else 0)
                rot = rng.uniform(0, 180)
                for k in range(5):
                    rx = max(4, int((8 + k * 4) * sc))
                    ry = max(2, int(rx * 0.45))
                    val = rng.uniform(0.30, 0.96)
                    _cv2.ellipse(CC, (cx2, cy), (rx, ry), rot + k * 9, 25, 325, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(M, (cx2, cy), (rx, ry), rot + k * 9, 45, 250, val * 0.68, 1, lineType=_cv2.LINE_AA)
                _draw_glint(M, R, CC, cx2, cy, max(1, int(3 * sc)), (0.82, 0.11, 0.92))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _ghost_orchid_smoke_brocade(shape, seed, sm, name="ghost_orchid_smoke_brocade"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84105)
    M, R, CC = _base(shape, int(seed), 0.10, 0.07, 0.24, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-3, 12):
            y0 = int((lane - 1) * h / 6)
            for i in range(-1, 30):
                cx = int(i * w / 27 + math.sin(i * 0.7 + lane) * 22 * sc)
                cy = int(y0 + math.sin(i * 0.43 + lane) * 24 * sc)
                val = rng.uniform(0.28, 0.90)
                for petal in range(3):
                    rx = max(4, int(rng.uniform(8, 18) * sc))
                    ry = max(2, int(rng.uniform(3, 8) * sc))
                    _cv2.ellipse(CC, (cx, cy), (rx, ry), petal * 62 + rng.uniform(-20, 20), 205, 35, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(M, (cx, cy), (rx, ry), petal * 62 + rng.uniform(-20, 20), 215, 25, val * 0.68, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.45:
                    _cv2.circle(CC, (cx, cy), max(1, int(2 * sc)), rng.uniform(0.55, 0.98), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _samhain_candle_soot_moths(shape, seed, sm, name="samhain_candle_soot_moths"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84106)
    M, R, CC = _base(shape, int(seed), 0.13, 0.12, 0.14, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 260, 52)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            val = rng.uniform(0.30, 0.98)
            wing = max(4, int(rng.uniform(7, 15) * sc))
            _cv2.ellipse(M, (cx - wing // 2, cy), (wing, max(2, wing // 2)), rng.uniform(-38, -8), 185, 345, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx + wing // 2, cy), (wing, max(2, wing // 2)), rng.uniform(8, 38), 195, 355, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy - wing), (cx, cy + wing), val * 0.18, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.35:
                flame = np.asarray([(cx, cy - wing), (cx - int(3 * sc), cy), (cx, cy + wing), (cx + int(3 * sc), cy)], dtype=np.int32)
                _cv2.polylines(CC, [flame], True, rng.uniform(0.55, 0.99), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _quartz_spider_geode_mesh(shape, seed, sm, name="quartz_spider_geode_mesh"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84107)
    M, R, CC = _base(shape, int(seed), 0.11, 0.08, 0.21, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        centers = [(int(rng.integers(0, w)), int(rng.integers(0, h))) for _ in range(_count(shape, 160, 30))]
        for cx, cy in centers:
            arms = int(rng.integers(3, 7))
            for a in range(arms):
                ang = rng.uniform(0, math.tau)
                length = rng.uniform(14, 36) * sc
                p2 = (int(cx + math.cos(ang) * length), int(cy + math.sin(ang) * length))
                val = rng.uniform(0.30, 0.98)
                _cv2.line(CC, (cx, cy), p2, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx, cy), p2, val * 0.76, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), max(1, int(2.2 * sc)), rng.uniform(0.10, 0.22), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _diamond_plate_fracture_mosaic(shape, seed, sm, name="diamond_plate_fracture_mosaic"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84108)
    M, R, CC = _base(shape, int(seed), 0.10, 0.08, 0.22, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        step = max(20, int(52 * sc))
        for row, y in enumerate(range(-step, h + step, step)):
            for col, x in enumerate(range(-step, w + step, step)):
                cx = x + (step // 2 if row % 2 else 0)
                cy = y
                r = rng.uniform(9, 22) * sc
                pts = []
                for k in range(5):
                    a = -math.pi / 2 + k * math.tau / 5 + rng.uniform(-0.14, 0.14)
                    pts.append((int(cx + math.cos(a) * r * rng.uniform(0.75, 1.2)), int(cy + math.sin(a) * r * rng.uniform(0.65, 1.1))))
                poly = np.asarray(pts, dtype=np.int32)
                val = rng.uniform(0.24, 0.94)
                _cv2.polylines(CC, [poly], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx, cy), pts[int(rng.integers(0, 5))], val * 0.78, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, pts[1], pts[3], rng.uniform(0.28, 0.82), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _astral_microprism_starfield(shape, seed, sm, name="astral_microprism_starfield"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84109)
    M, R, CC = _base(shape, int(seed), 0.09, 0.06, 0.25, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for band in range(-3, 10):
            pts = []
            y0 = int((band - 1) * h / 6)
            for x in range(0, w, max(8, int(13 * sc))):
                y = int(y0 + math.sin(x * 0.018 + band) * 34 * sc)
                pts.append((x, np.clip(y, 0, h - 1)))
            _polyline(CC, pts, rng.uniform(0.22, 0.60), 1)
        for _ in range(_count(shape, 900, 150)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            val = rng.uniform(0.34, 0.99)
            _cv2.circle(CC, (x, y), max(1, int(rng.uniform(1, 2.5) * sc)), val, -1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.10:
                _draw_glint(M, R, CC, x, y, max(2, int(4 * sc)), (0.88, 0.10, 0.96))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _dragon_pangolin_scale_mail(shape, seed, sm, name="dragon_pangolin_scale_mail"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84110)
    M, R, CC = _base(shape, int(seed), 0.13, 0.10, 0.18, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(16, int(38 * sc)), max(14, int(32 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx = x + off
                cy = y
                rw, rh = max(6, int(rng.uniform(9, 17) * sc)), max(5, int(rng.uniform(8, 15) * sc))
                pts = np.asarray([(cx, cy - rh), (cx + rw, cy), (cx + int(rw * 0.35), cy + rh), (cx - int(rw * 0.35), cy + rh), (cx - rw, cy)], dtype=np.int32)
                val = rng.uniform(0.22, 0.94)
                _cv2.fillPoly(M, [pts], val * 0.38, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx, cy - rh), (cx, cy + rh), val * 0.92, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx - rw, cy), (cx + rw, cy), val * 0.18, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _razor_wire_loop_mesh_dense(shape, seed, sm, name="razor_wire_loop_mesh_dense"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84111)
    M, R, CC = _base(shape, int(seed), 0.11, 0.09, 0.21, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-3, 13):
            y0 = int((lane - 1) * h / 7)
            pts = []
            for x in range(0, w, max(8, int(14 * sc))):
                y = int(y0 + math.sin(x * 0.023 + lane) * 18 * sc)
                pts.append((x, np.clip(y, 0, h - 1)))
            _polyline(M, pts, rng.uniform(0.30, 0.78), 1)
            for x, y in pts[2::4]:
                rx, ry = max(3, int(7 * sc)), max(2, int(4 * sc))
                _cv2.ellipse(CC, (x, y), (rx, ry), rng.uniform(-18, 18), 0, 360, rng.uniform(0.40, 0.98), 1, lineType=_cv2.LINE_AA)
                for side in (-1, 1):
                    _cv2.line(M, (x, y), (x + side * int(8 * sc), y + int(rng.uniform(-5, 5) * sc)), rng.uniform(0.42, 0.96), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _rubber_wall_transfer_chatter(shape, seed, sm, name="rubber_wall_transfer_chatter"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84112)
    M, R, CC = _base(shape, int(seed), 0.10, 0.14, 0.12, 0.055)
    sc = _scale(shape)
    if _CV2_OK:
        for lane in range(-3, 13):
            y0 = int((lane - 1) * h / 7)
            for i in range(-1, 45):
                cx = int(i * w / 41 + rng.uniform(-5, 5) * sc)
                cy = int(y0 + math.sin(i * 0.48 + lane) * 19 * sc)
                length = rng.uniform(13, 36) * sc
                angle = rng.uniform(-0.35, 0.35)
                p1 = (int(cx - math.cos(angle) * length / 2), int(cy - math.sin(angle) * length / 2))
                p2 = (int(cx + math.cos(angle) * length / 2), int(cy + math.sin(angle) * length / 2))
                val = rng.uniform(0.22, 0.88)
                _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (p1[0], p1[1] + max(1, int(2 * sc))), (p2[0], p2[1] + max(1, int(2 * sc))), val * 0.22, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.34:
                    _cv2.ellipse(CC, (cx, cy), (max(4, int(length * 0.34)), max(2, int(4 * sc))), math.degrees(angle), 195, 345, rng.uniform(0.24, 0.62), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_aniso_grain_deep(shape, seed, sm, **kwargs): return _fan_cut_engine_turn_rosettes(shape, seed + 2201, sm)
def rescue_brake_dust_buildup(shape, seed, sm, **kwargs): return _brake_dust_rotor_arc_storm(shape, seed + 2202, sm)
def rescue_cc_gloss_stripe(shape, seed, sm, **kwargs): return _clearcoat_rain_lens_cells(shape, seed + 2203, sm)
def rescue_cc_spot_polish(shape, seed, sm, **kwargs): return _compound_buff_orbital_shell_field(shape, seed + 2204, sm)
def rescue_cloud_wisps(shape, seed, sm, **kwargs): return _ghost_orchid_smoke_brocade(shape, seed + 2205, sm)
def rescue_cloud_wisps_warm(shape, seed, sm, **kwargs): return _samhain_candle_soot_moths(shape, seed + 2206, sm)
def rescue_crystal_growth(shape, seed, sm, **kwargs): return _quartz_spider_geode_mesh(shape, seed + 2207, sm)
def rescue_diamond_dust(shape, seed, sm, **kwargs): return _diamond_plate_fracture_mosaic(shape, seed + 2208, sm)
def rescue_micro_sparkle(shape, seed, sm, **kwargs): return _astral_microprism_starfield(shape, seed + 2209, sm)
def rescue_pangolin_armor(shape, seed, sm, **kwargs): return _dragon_pangolin_scale_mail(shape, seed + 2210, sm)
def rescue_razor_wire_coil(shape, seed, sm, **kwargs): return _razor_wire_loop_mesh_dense(shape, seed + 2211, sm)
def rescue_wear_scuff(shape, seed, sm, **kwargs): return _rubber_wall_transfer_chatter(shape, seed + 2212, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass8-iteration3:
# Second contact sheet still had row/lane crutches. These overrides remove that family look.
def _brake_dust_rotor_ash_blooms(shape, seed, sm, name="brake_dust_rotor_ash_blooms"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84201)
    M, R, CC = _base(shape, int(seed), 0.10, 0.16, 0.11, 0.065)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 180, 35)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            for k in range(4):
                rx = max(5, int((8 + k * rng.uniform(4, 8)) * sc))
                ry = max(2, int(rx * rng.uniform(0.24, 0.52)))
                val = rng.uniform(0.22, 0.88)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 11, 185, 355, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rx, ry), rot + k * 11, 185, 355, val * 0.24, 1, lineType=_cv2.LINE_AA)
            for _dot in range(5):
                x = int(cx + rng.normal(0, 11 * sc))
                y = int(cy + rng.normal(0, 6 * sc))
                _cv2.circle(CC, (np.clip(x, 0, w - 1), np.clip(y, 0, h - 1)), max(1, int(rng.uniform(1, 2.5) * sc)), rng.uniform(0.34, 0.90), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _clearcoat_rotary_compound_bubbles(shape, seed, sm, name="clearcoat_rotary_compound_bubbles"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84202)
    M, R, CC = _base(shape, int(seed), 0.11, 0.07, 0.29, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 260, 48)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(4, int(rng.uniform(7, 17) * sc)), max(2, int(rng.uniform(3, 8) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.30, 0.98)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx + int(4 * sc), ry + int(2 * sc)), rot + 12, 25, 235, val * 0.62, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.50:
                _cv2.circle(CC, (cx + int(rx * 0.35), cy - int(ry * 0.25)), max(1, int(2.2 * sc)), rng.uniform(0.62, 0.99), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _spirit_board_planchette_lace(shape, seed, sm, name="spirit_board_planchette_lace"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84203)
    M, R, CC = _base(shape, int(seed), 0.10, 0.07, 0.23, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(34, int(88 * sc)), max(30, int(74 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx = x + off + int(math.sin(row * 0.9) * 8 * sc)
                cy = y
                r = max(7, int(rng.uniform(14, 24) * sc))
                pts = np.asarray([(cx, cy - r), (cx + int(r * 0.9), cy + int(r * 0.2)), (cx + int(r * 0.35), cy + r), (cx - int(r * 0.35), cy + r), (cx - int(r * 0.9), cy + int(r * 0.2))], dtype=np.int32)
                val = rng.uniform(0.34, 0.96)
                _cv2.polylines(CC, [pts], True, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (cx, cy + int(r * 0.25)), max(3, int(r * 0.28)), val * 0.78, 1, lineType=_cv2.LINE_AA)
                for a in (210, 270, 330):
                    p2 = (int(cx + math.cos(math.radians(a)) * r * 0.82), int(cy + math.sin(math.radians(a)) * r * 0.82))
                    _cv2.line(M, (cx, cy), p2, rng.uniform(0.28, 0.82), 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.55:
                    _draw_glint(M, R, CC, cx, cy - int(r * 0.25), max(2, int(3 * sc)), (0.80, 0.10, 0.92))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _voodoo_candle_pin_ash_field(shape, seed, sm, name="voodoo_candle_pin_ash_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84204)
    M, R, CC = _base(shape, int(seed), 0.13, 0.12, 0.14, 0.055)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 340, 62)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            val = rng.uniform(0.28, 0.96)
            length = max(5, int(rng.uniform(8, 18) * sc))
            ang = rng.uniform(0, math.tau)
            p1 = (int(cx - math.cos(ang) * length / 2), int(cy - math.sin(ang) * length / 2))
            p2 = (int(cx + math.cos(ang) * length / 2), int(cy + math.sin(ang) * length / 2))
            _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, p2, max(1, int(2.0 * sc)), min(0.99, val + 0.05), -1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.45:
                flame = np.asarray([(cx, cy - length), (cx - int(3 * sc), cy), (cx, cy + length), (cx + int(3 * sc), cy)], dtype=np.int32)
                _cv2.polylines(CC, [flame], True, rng.uniform(0.46, 0.98), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _quartz_cathedral_shards(shape, seed, sm, name="quartz_cathedral_shards"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84205)
    M, R, CC = _base(shape, int(seed), 0.10, 0.08, 0.22, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 280, 55)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            height = rng.uniform(14, 34) * sc
            width = rng.uniform(5, 13) * sc
            rot = rng.uniform(0, math.tau)
            local = [(0, -height), (width, height * 0.25), (0, height), (-width, height * 0.25)]
            pts = []
            for x, y in local:
                pts.append((int(cx + x * math.cos(rot) - y * math.sin(rot)), int(cy + x * math.sin(rot) + y * math.cos(rot))))
            poly = np.asarray(pts, dtype=np.int32)
            val = rng.uniform(0.28, 0.98)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, pts[0], pts[2], val * 0.82, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, pts[1], pts[3], val * 0.18, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _astral_spiral_microcosm(shape, seed, sm, name="astral_spiral_microcosm"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84206)
    M, R, CC = _base(shape, int(seed), 0.08, 0.06, 0.25, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 90, 18)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            pts = []
            for k in range(42):
                r = k * 0.75 * sc
                a = k * 0.42 + rng.uniform(-0.04, 0.04)
                pts.append((int(np.clip(cx + math.cos(a) * r, 0, w - 1)), int(np.clip(cy + math.sin(a) * r, 0, h - 1))))
            _polyline(CC, pts, rng.uniform(0.28, 0.82), 1)
            if rng.random() < 0.6:
                _draw_glint(M, R, CC, cx, cy, max(2, int(3.5 * sc)), (0.88, 0.10, 0.96))
        for _ in range(_count(shape, 1000, 165)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(CC, (x, y), max(1, int(rng.uniform(1, 2.3) * sc)), rng.uniform(0.34, 0.98), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _tangled_razor_crown_nests(shape, seed, sm, name="tangled_razor_crown_nests"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84207)
    M, R, CC = _base(shape, int(seed), 0.11, 0.09, 0.20, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 170, 34)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(7, int(rng.uniform(12, 26) * sc)), max(4, int(rng.uniform(6, 14) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.30, 0.96)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot + 18, 0, 360, val * 0.72, 1, lineType=_cv2.LINE_AA)
            for a in (rot, rot + 90, rot + 180):
                p1 = (int(cx + math.cos(math.radians(a)) * rx), int(cy + math.sin(math.radians(a)) * ry))
                p2 = (int(p1[0] + math.cos(math.radians(a + 60)) * 10 * sc), int(p1[1] + math.sin(math.radians(a + 60)) * 10 * sc))
                _cv2.line(M, p1, p2, rng.uniform(0.44, 0.99), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _pit_wall_rubber_islands(shape, seed, sm, name="pit_wall_rubber_islands"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84208)
    M, R, CC = _base(shape, int(seed), 0.09, 0.14, 0.12, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 310, 58)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(-35, 35)
            val = rng.uniform(0.22, 0.88)
            for k in range(int(rng.integers(2, 5))):
                rx = max(5, int(rng.uniform(9, 24) * sc))
                ry = max(2, int(rng.uniform(2, 6) * sc))
                _cv2.ellipse(M, (cx + int(rng.normal(0, 5 * sc)), cy + int(rng.normal(0, 4 * sc))), (rx, ry), rot + rng.uniform(-12, 12), 185, 355, val * rng.uniform(0.65, 1.05), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rx, ry), rot, 185, 355, val * 0.20, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.32:
                _cv2.circle(CC, (cx, cy), max(1, int(2.0 * sc)), rng.uniform(0.28, 0.72), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_brake_dust_buildup(shape, seed, sm, **kwargs): return _brake_dust_rotor_ash_blooms(shape, seed + 2301, sm)
def rescue_cc_spot_polish(shape, seed, sm, **kwargs): return _clearcoat_rotary_compound_bubbles(shape, seed + 2302, sm)
def rescue_cloud_wisps(shape, seed, sm, **kwargs): return _spirit_board_planchette_lace(shape, seed + 2303, sm)
def rescue_cloud_wisps_warm(shape, seed, sm, **kwargs): return _voodoo_candle_pin_ash_field(shape, seed + 2304, sm)
def rescue_crystal_growth(shape, seed, sm, **kwargs): return _quartz_cathedral_shards(shape, seed + 2305, sm)
def rescue_micro_sparkle(shape, seed, sm, **kwargs): return _astral_spiral_microcosm(shape, seed + 2306, sm)
def rescue_razor_wire_coil(shape, seed, sm, **kwargs): return _tangled_razor_crown_nests(shape, seed + 2307, sm)
def rescue_wear_scuff(shape, seed, sm, **kwargs): return _pit_wall_rubber_islands(shape, seed + 2308, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass8-iteration4:
# Contact-sheet minimum readability pass: preserve fine-detail intent, but avoid vanishing 1px motif fields.
def _brake_dust_ceramic_orbit_scorch(shape, seed, sm, name="brake_dust_ceramic_orbit_scorch"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84301)
    M, R, CC = _base(shape, int(seed), 0.10, 0.16, 0.11, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 210, 40)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(9, int(rng.uniform(12, 30) * sc)), max(3, int(rng.uniform(4, 9) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.28, 0.92)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 185, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (max(4, rx // 2), max(2, ry // 2)), rot + 9, 210, 340, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.55:
                _cv2.circle(R, (cx, cy), max(2, int(3.0 * sc)), val * 0.22, -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _compound_polish_peacock_eyes(shape, seed, sm, name="compound_polish_peacock_eyes"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84302)
    M, R, CC = _base(shape, int(seed), 0.11, 0.07, 0.29, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(24, int(54 * sc)), max(22, int(50 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx = x + off
                cy = y + int(math.sin(x * 0.03) * 5 * sc)
                rx, ry = max(7, int(14 * sc)), max(4, int(8 * sc))
                rot = rng.uniform(-30, 30)
                val = rng.uniform(0.34, 0.98)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (max(3, rx // 2), max(2, ry // 2)), rot, 0, 360, val * 0.88, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), max(1, int(2.2 * sc)), min(0.99, val + 0.08), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _ouija_planchette_eye_brocade(shape, seed, sm, name="ouija_planchette_eye_brocade"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84303)
    M, R, CC = _base(shape, int(seed), 0.09, 0.07, 0.24, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(42, int(88 * sc)), max(36, int(76 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off, y
                r = max(11, int(22 * sc))
                val = rng.uniform(0.32, 0.96)
                pts = np.asarray([(cx, cy - r), (cx + int(r * 0.8), cy), (cx + int(r * 0.35), cy + r), (cx - int(r * 0.35), cy + r), (cx - int(r * 0.8), cy)], dtype=np.int32)
                _cv2.polylines(CC, [pts], True, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy + int(r * 0.18)), (max(5, int(r * 0.42)), max(3, int(r * 0.22))), 0, 0, 360, val * 0.80, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy + int(r * 0.18)), max(2, int(r * 0.14)), min(0.99, val + 0.08), -1, lineType=_cv2.LINE_AA)
                for a in (230, 270, 310):
                    _cv2.line(M, (cx, cy - int(r * 0.15)), (int(cx + math.cos(math.radians(a)) * r * 0.65), int(cy + math.sin(math.radians(a)) * r * 0.65)), rng.uniform(0.28, 0.78), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _voodoo_pin_candle_sparks(shape, seed, sm, name="voodoo_pin_candle_sparks"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84304)
    M, R, CC = _base(shape, int(seed), 0.12, 0.12, 0.15, 0.052)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 430, 78)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            val = rng.uniform(0.30, 0.98)
            length = max(7, int(rng.uniform(10, 22) * sc))
            ang = rng.uniform(0, math.tau)
            p1 = (int(cx - math.cos(ang) * length / 2), int(cy - math.sin(ang) * length / 2))
            p2 = (int(cx + math.cos(ang) * length / 2), int(cy + math.sin(ang) * length / 2))
            _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, p2, max(2, int(3.0 * sc)), min(0.99, val + 0.06), -1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.28:
                _draw_glint(M, R, CC, cx, cy, max(2, int(3.5 * sc)), (0.96, 0.08, 0.72))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _quartz_prism_cathedral_field(shape, seed, sm, name="quartz_prism_cathedral_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84305)
    M, R, CC = _base(shape, int(seed), 0.10, 0.08, 0.23, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(26, int(58 * sc)), max(26, int(58 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx = x + off + int(rng.uniform(-4, 4) * sc)
                cy = y + int(rng.uniform(-4, 4) * sc)
                r = max(10, int(rng.uniform(14, 26) * sc))
                rot = rng.uniform(0, math.tau)
                pts = []
                for a in (-math.pi / 2, -0.12, math.pi / 2, math.pi + 0.12):
                    pts.append((int(cx + math.cos(a + rot) * r * (0.45 if abs(a) < 0.2 else 1.0)), int(cy + math.sin(a + rot) * r)))
                poly = np.asarray(pts, dtype=np.int32)
                val = rng.uniform(0.30, 0.98)
                _cv2.polylines(CC, [poly], True, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, pts[0], pts[2], val * 0.84, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, pts[1], pts[3], val * 0.18, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _diamond_shatter_optic_tiles(shape, seed, sm, name="diamond_shatter_optic_tiles"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84306)
    M, R, CC = _base(shape, int(seed), 0.10, 0.08, 0.22, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 330, 62)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(8, int(rng.uniform(11, 22) * sc))
            rot = rng.uniform(0, math.tau)
            pts = [(int(cx + math.cos(rot + k * math.tau / 4) * r * rng.uniform(0.75, 1.20)), int(cy + math.sin(rot + k * math.tau / 4) * r * rng.uniform(0.55, 1.05))) for k in range(4)]
            val = rng.uniform(0.30, 0.98)
            poly = np.asarray(pts, dtype=np.int32)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, pts[0], pts[2], val * 0.82, 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, pts[1], pts[3], rng.uniform(0.28, 0.84), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _astral_stardust_spiral_map(shape, seed, sm, name="astral_stardust_spiral_map"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84307)
    M, R, CC = _base(shape, int(seed), 0.08, 0.06, 0.26, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 145, 28)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            pts = []
            for k in range(44):
                r = max(1.0, k * 0.9 * sc)
                a = k * 0.45
                pts.append((int(np.clip(cx + math.cos(a) * r, 0, w - 1)), int(np.clip(cy + math.sin(a) * r, 0, h - 1))))
            _polyline(CC, pts, rng.uniform(0.28, 0.80), 1)
            if rng.random() < 0.70:
                _draw_glint(M, R, CC, cx, cy, max(2, int(4 * sc)), (0.86, 0.10, 0.96))
        for _ in range(_count(shape, 1250, 205)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(CC, (x, y), max(1, int(rng.uniform(1, 2.4) * sc)), rng.uniform(0.38, 0.99), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _concertina_barb_crown_clusters(shape, seed, sm, name="concertina_barb_crown_clusters"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84308)
    M, R, CC = _base(shape, int(seed), 0.11, 0.09, 0.21, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 240, 45)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(8, int(rng.uniform(12, 25) * sc)), max(5, int(rng.uniform(6, 13) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.32, 0.98)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot + 24, 0, 360, val * 0.76, 1, lineType=_cv2.LINE_AA)
            for a in (rot - 50, rot + 30, rot + 115):
                p1 = (int(cx + math.cos(math.radians(a)) * rx), int(cy + math.sin(math.radians(a)) * ry))
                p2 = (int(p1[0] + math.cos(math.radians(a + 65)) * max(7, int(11 * sc))), int(p1[1] + math.sin(math.radians(a + 65)) * max(7, int(11 * sc))))
                _cv2.line(M, p1, p2, rng.uniform(0.46, 0.99), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _rubber_marble_scuff_islands(shape, seed, sm, name="rubber_marble_scuff_islands"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84309)
    M, R, CC = _base(shape, int(seed), 0.09, 0.14, 0.13, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 360, 68)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.24, 0.90)
            for k in range(3):
                rx = max(8, int(rng.uniform(10, 24) * sc))
                ry = max(2, int(rng.uniform(3, 7) * sc))
                _cv2.ellipse(M, (cx + int(rng.normal(0, 4 * sc)), cy + int(rng.normal(0, 4 * sc))), (rx, ry), rot + k * rng.uniform(-10, 10), 175, 360, val * rng.uniform(0.68, 1.05), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.42:
                _cv2.circle(CC, (cx, cy), max(1, int(2.5 * sc)), rng.uniform(0.30, 0.78), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_brake_dust_buildup(shape, seed, sm, **kwargs): return _brake_dust_ceramic_orbit_scorch(shape, seed + 2401, sm)
def rescue_cc_spot_polish(shape, seed, sm, **kwargs): return _compound_polish_peacock_eyes(shape, seed + 2402, sm)
def rescue_cloud_wisps(shape, seed, sm, **kwargs): return _ouija_planchette_eye_brocade(shape, seed + 2403, sm)
def rescue_cloud_wisps_warm(shape, seed, sm, **kwargs): return _voodoo_pin_candle_sparks(shape, seed + 2404, sm)
def rescue_crystal_growth(shape, seed, sm, **kwargs): return _quartz_prism_cathedral_field(shape, seed + 2405, sm)
def rescue_diamond_dust(shape, seed, sm, **kwargs): return _diamond_shatter_optic_tiles(shape, seed + 2406, sm)
def rescue_micro_sparkle(shape, seed, sm, **kwargs): return _astral_stardust_spiral_map(shape, seed + 2407, sm)
def rescue_razor_wire_coil(shape, seed, sm, **kwargs): return _concertina_barb_crown_clusters(shape, seed + 2408, sm)
def rescue_wear_scuff(shape, seed, sm, **kwargs): return _rubber_marble_scuff_islands(shape, seed + 2409, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass9:
# Owner verdict snippet: "EVERY new finish ... 100% unique ... no lazy cousin variants".
# Metric movement note: pass starts from post-pass8 M7 where eye/doctrine beats stale clone scoring.
def _bone_shrine_pinstripe_windows(shape, seed, sm, name="bone_shrine_pinstripe_windows"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84401)
    M, R, CC = _base(shape, int(seed), 0.10, 0.07, 0.23, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(34, int(74 * sc)), max(32, int(70 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off, y
                rw, rh = max(10, int(20 * sc)), max(14, int(28 * sc))
                val = rng.uniform(0.32, 0.96)
                pts = np.asarray([(cx, cy - rh), (cx + rw, cy - int(rh * 0.2)), (cx + int(rw * 0.65), cy + rh), (cx, cy + int(rh * 0.55)), (cx - int(rw * 0.65), cy + rh), (cx - rw, cy - int(rh * 0.2))], dtype=np.int32)
                _cv2.polylines(CC, [pts], True, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (max(5, rw // 2), max(4, rh // 4)), 0, 0, 360, val * 0.76, 1, lineType=_cv2.LINE_AA)
                for a in (235, 270, 305):
                    p2 = (int(cx + math.cos(math.radians(a)) * rw * 0.85), int(cy + math.sin(math.radians(a)) * rh * 0.60))
                    _cv2.line(M, (cx, cy), p2, rng.uniform(0.28, 0.82), 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.42:
                    _draw_glint(M, R, CC, cx, cy - int(rh * 0.35), max(2, int(3.5 * sc)), (0.88, 0.09, 0.92))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _vinyl_prism_record_rosettes(shape, seed, sm, name="vinyl_prism_record_rosettes"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84402)
    M, R, CC = _base(shape, int(seed), 0.11, 0.08, 0.24, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        step = max(34, int(82 * sc))
        for row, cy in enumerate(range(-step, h + step, step)):
            for col, cx in enumerate(range(-step, w + step, step)):
                cx2 = cx + (step // 2 if row % 2 else 0)
                for k, val in enumerate((0.28, 0.38, 0.50, 0.62, 0.76, 0.92)):
                    r = max(5, int((8 + k * 4.2) * sc))
                    _cv2.ellipse(CC, (cx2, cy), (r, r), 0, 0, 360, val + rng.uniform(-0.04, 0.04), 1, lineType=_cv2.LINE_AA)
                    if k % 2 == 0:
                        _cv2.ellipse(M, (cx2, cy), (r, r), 0, 20, 155, val * 0.72, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx2 - int(20 * sc), cy), (cx2 + int(20 * sc), cy), rng.uniform(0.24, 0.66), 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.65:
                    _draw_glint(M, R, CC, cx2, cy, max(2, int(4 * sc)), (0.82, 0.10, 0.94))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _katana_lacquer_brush_fans(shape, seed, sm, name="katana_lacquer_brush_fans"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84403)
    M, R, CC = _base(shape, int(seed), 0.12, 0.08, 0.21, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 170, 34)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.30, 0.98)
            for k in range(6):
                length = rng.uniform(14, 34) * sc
                spread = (k - 2.5) * rng.uniform(4, 8)
                a = math.radians(rot + spread)
                p2 = (int(cx + math.cos(a) * length), int(cy + math.sin(a) * length))
                _cv2.line(M, (cx, cy), p2, val * rng.uniform(0.65, 1.0), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx + int(2 * sc), cy), (p2[0] + int(2 * sc), p2[1]), min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.55:
                _cv2.circle(CC, (cx, cy), max(1, int(2.5 * sc)), rng.uniform(0.48, 0.98), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _random_clearcoat_crater_reef(shape, seed, sm, name="random_clearcoat_crater_reef"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84404)
    M, R, CC = _base(shape, int(seed), 0.08, 0.07, 0.30, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 310, 58)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(5, int(rng.uniform(8, 22) * sc)), max(4, int(rng.uniform(6, 18) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.28, 0.98)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (max(2, rx // 2), max(2, ry // 2)), rot + 18, 0, 360, val * 0.70, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), max(1, int(rng.uniform(2, 4) * sc)), val * 0.16, -1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.34:
                _cv2.line(CC, (cx + rx, cy), (cx + rx + int(rng.uniform(7, 17) * sc), cy + int(rng.uniform(-6, 6) * sc)), rng.uniform(0.34, 0.86), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _glacial_pearl_tide_rosettes(shape, seed, sm, name="glacial_pearl_tide_rosettes"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84405)
    M, R, CC = _base(shape, int(seed), 0.12, 0.09, 0.27, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 190, 38)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            for k in range(5):
                rx = max(5, int((8 + k * 4.4) * sc))
                ry = max(3, int(rx * rng.uniform(0.38, 0.62)))
                val = rng.uniform(0.32, 0.98)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 7, 205, 28, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 7, 220, 12, val * 0.68, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.62:
                _cv2.circle(CC, (cx, cy), max(2, int(4 * sc)), rng.uniform(0.55, 0.99), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _oxidized_copper_fern_islands(shape, seed, sm, name="oxidized_copper_fern_islands"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84406)
    M, R, CC = _base(shape, int(seed), 0.16, 0.14, 0.15, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 150, 30)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, math.tau)
            val = rng.uniform(0.28, 0.94)
            stem = rng.uniform(18, 46) * sc
            p2 = (int(cx + math.cos(rot) * stem), int(cy + math.sin(rot) * stem))
            _cv2.line(M, (cx, cy), p2, val, 1, lineType=_cv2.LINE_AA)
            for j in range(3, 10):
                t = j / 10
                bx = int(cx + math.cos(rot) * stem * t)
                by = int(cy + math.sin(rot) * stem * t)
                for side in (-1, 1):
                    a = rot + side * rng.uniform(0.55, 0.95)
                    leaf = int(rng.uniform(6, 14) * sc)
                    _cv2.line(CC, (bx, by), (int(bx + math.cos(a) * leaf), int(by + math.sin(a) * leaf)), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.50:
                _cv2.ellipse(R, (cx, cy), (max(6, int(12 * sc)), max(3, int(6 * sc))), math.degrees(rot), 0, 360, val * 0.18, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _hammered_prismatic_flake_scales(shape, seed, sm, name="hammered_prismatic_flake_scales"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84407)
    M, R, CC = _base(shape, int(seed), 0.13, 0.10, 0.24, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(16, int(36 * sc)), max(16, int(34 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off + int(rng.uniform(-3, 3) * sc), y + int(rng.uniform(-3, 3) * sc)
                r = max(5, int(rng.uniform(7, 13) * sc))
                pts = [(int(cx + math.cos(k * math.tau / 6) * r * rng.uniform(0.7, 1.15)), int(cy + math.sin(k * math.tau / 6) * r * rng.uniform(0.7, 1.15))) for k in range(6)]
                poly = np.asarray(pts, dtype=np.int32)
                val = rng.uniform(0.26, 0.98)
                _cv2.fillPoly(M, [poly], val * 0.36, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [poly], True, min(0.99, val + 0.07), 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.30:
                    _draw_glint(M, R, CC, cx, cy, max(1, int(3 * sc)), (0.86, 0.10, 0.94))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _forged_carbon_talon_splinters(shape, seed, sm, name="forged_carbon_talon_splinters"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84408)
    M, R, CC = _base(shape, int(seed), 0.08, 0.11, 0.16, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 340, 65)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            length = rng.uniform(18, 54) * sc
            width = rng.uniform(4, 12) * sc
            rot = rng.uniform(0, math.tau)
            pts = []
            for a, rr in ((0, length), (1.9, width), (math.pi, length * rng.uniform(0.35, 0.75)), (4.3, width)):
                pts.append((int(cx + math.cos(rot + a) * rr), int(cy + math.sin(rot + a) * rr)))
            poly = np.asarray(pts, dtype=np.int32)
            val = rng.uniform(0.18, 0.88)
            _cv2.fillPoly(M, [poly], val * 0.62, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, pts[0], pts[2], val * 0.16, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _enamel_rain_drop_chainmail(shape, seed, sm, name="enamel_rain_drop_chainmail"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84409)
    M, R, CC = _base(shape, int(seed), 0.11, 0.08, 0.25, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(22, int(50 * sc)), max(24, int(54 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx = x + off + int(rng.uniform(-4, 4) * sc)
                cy = y + int(rng.uniform(-5, 5) * sc)
                r = max(5, int(rng.uniform(8, 16) * sc))
                val = rng.uniform(0.32, 0.96)
                _cv2.ellipse(CC, (cx, cy), (max(3, r // 2), r), 0, 0, 360, val, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx, cy - r), (cx, cy + r), val * 0.70, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx + int(2 * sc), cy - int(r * 0.35)), max(1, int(2.2 * sc)), min(0.99, val + 0.06), -1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.30:
                    _cv2.line(R, (cx, cy + r), (cx, cy + r + int(rng.uniform(6, 14) * sc)), val * 0.18, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _liquid_chrome_cellular_lagoons(shape, seed, sm, name="liquid_chrome_cellular_lagoons"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84410)
    M, R, CC = _base(shape, int(seed), 0.18, 0.08, 0.30, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 170, 34)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            for k in range(4):
                rx = max(8, int((12 + k * rng.uniform(5, 10)) * sc))
                ry = max(3, int(rx * rng.uniform(0.28, 0.62)))
                val = rng.uniform(0.34, 0.99)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 12, 0, 360, val, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (max(3, rx // 2), max(2, ry // 2)), rot + k * 12, 205, 350, val * 0.72, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.55:
                _draw_glint(M, R, CC, cx, cy, max(2, int(4 * sc)), (0.82, 0.10, 0.96))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _burl_terrace_kintsugi_threads(shape, seed, sm, name="burl_terrace_kintsugi_threads"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84411)
    M, R, CC = _base(shape, int(seed), 0.14, 0.13, 0.16, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 160, 30)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            for k in range(5):
                rx = max(7, int((10 + k * rng.uniform(6, 11)) * sc))
                ry = max(3, int(rx * rng.uniform(0.32, 0.70)))
                val = rng.uniform(0.24, 0.86)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 4, 0, 360, val, 1, lineType=_cv2.LINE_AA)
                if k in (1, 3):
                    _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 4, 15, 205, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.35:
                _cv2.line(CC, (cx - int(16 * sc), cy), (cx + int(16 * sc), cy + int(rng.uniform(-7, 7) * sc)), rng.uniform(0.30, 0.78), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _magnetic_compass_filings_starbursts(shape, seed, sm, name="magnetic_compass_filings_starbursts"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84412)
    M, R, CC = _base(shape, int(seed), 0.11, 0.08, 0.22, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 135, 26)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            arms = int(rng.integers(5, 9))
            val = rng.uniform(0.28, 0.94)
            for a in range(arms):
                ang = a * math.tau / arms + rng.uniform(-0.08, 0.08)
                length = rng.uniform(10, 28) * sc
                p2 = (int(cx + math.cos(ang) * length), int(cy + math.sin(ang) * length))
                _cv2.line(M, (cx, cy), p2, val * rng.uniform(0.65, 1.0), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx, cy), (int(cx + math.cos(ang) * length * 0.62), int(cy + math.sin(ang) * length * 0.62)), min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), max(1, int(2.5 * sc)), val * 0.16, -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _rune_iron_nail_constellation(shape, seed, sm, name="rune_iron_nail_constellation"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84413)
    M, R, CC = _base(shape, int(seed), 0.12, 0.09, 0.20, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(42, int(86 * sc)), max(38, int(78 * sc))
        glyphs = [((0, -1), (0, 1), (-0.45, 0.25), (0.45, -0.25)), ((-0.55, -0.65), (0, 0), (0.55, -0.65), (0, 0.75)), ((-0.5, 0.6), (0, -0.7), (0.5, 0.6))]
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off, y
                r = max(10, int(18 * sc))
                val = rng.uniform(0.30, 0.92)
                _cv2.circle(CC, (cx, cy), r, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
                g = glyphs[int(rng.integers(0, len(glyphs)))]
                pts = [(int(cx + px * r), int(cy + py * r)) for px, py in g]
                for a, b in zip(pts[::2], pts[1::2]):
                    _cv2.line(M, a, b, val, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.45:
                    _draw_glint(M, R, CC, cx, cy, max(2, int(3 * sc)), (0.78, 0.08, 0.82))
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_abstract_expressionist_splatter(shape, seed, sm, **kwargs): return _bone_shrine_pinstripe_windows(shape, seed + 2501, sm)
def rescue_abstract_retro_wave(shape, seed, sm, **kwargs): return _vinyl_prism_record_rosettes(shape, seed + 2502, sm)
def rescue_brushstroke_bold(shape, seed, sm, **kwargs): return _katana_lacquer_brush_fans(shape, seed + 2503, sm)
def rescue_cc_fish_eye(shape, seed, sm, **kwargs): return _random_clearcoat_crater_reef(shape, seed + 2504, sm)
def rescue_cloud_wisps_cool(shape, seed, sm, **kwargs): return _glacial_pearl_tide_rosettes(shape, seed + 2505, sm)
def rescue_copper_patina_drip(shape, seed, sm, **kwargs): return _oxidized_copper_fern_islands(shape, seed + 2506, sm)
def rescue_flake_scatter(shape, seed, sm, **kwargs): return _hammered_prismatic_flake_scales(shape, seed + 2507, sm)
def rescue_forged_carbon_chip(shape, seed, sm, **kwargs): return _forged_carbon_talon_splinters(shape, seed + 2508, sm)
def rescue_paint_drip_edge(shape, seed, sm, **kwargs): return _enamel_rain_drop_chainmail(shape, seed + 2509, sm)
def rescue_spec_oil_film_thick(shape, seed, sm, **kwargs): return _liquid_chrome_cellular_lagoons(shape, seed + 2510, sm)
def rescue_spec_wood_grain_fine(shape, seed, sm, **kwargs): return _burl_terrace_kintsugi_threads(shape, seed + 2511, sm)
def rescue_magnetic_field(shape, seed, sm, **kwargs): return _magnetic_compass_filings_starbursts(shape, seed + 2512, sm)
def rescue_nordic_rune_field(shape, seed, sm, **kwargs): return _rune_iron_nail_constellation(shape, seed + 2513, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass9-iteration2:
# First pass had too many sparse accents. Densify while preserving separate material identities.
def _ink_lacquer_fan_scale_field(shape, seed, sm, name="ink_lacquer_fan_scale_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84501)
    M, R, CC = _base(shape, int(seed), 0.12, 0.08, 0.22, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(24, int(54 * sc)), max(22, int(50 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off, y + int(rng.uniform(-4, 4) * sc)
                rot = rng.uniform(-35, 35)
                val = rng.uniform(0.32, 0.98)
                for k in range(5):
                    length = (9 + k * 3.6) * sc
                    a = math.radians(rot + (k - 2) * 12)
                    p2 = (int(cx + math.cos(a) * length), int(cy + math.sin(a) * length))
                    _cv2.line(M, (cx, cy), p2, val * rng.uniform(0.68, 1.0), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, (cx, cy), p2, min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), max(1, int(2.0 * sc)), rng.uniform(0.44, 0.96), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _clearcoat_bubble_chain_reef_dense(shape, seed, sm, name="clearcoat_bubble_chain_reef_dense"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84502)
    M, R, CC = _base(shape, int(seed), 0.08, 0.07, 0.30, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 520, 95)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(4, int(rng.uniform(6, 16) * sc)), max(3, int(rng.uniform(5, 14) * sc))
            val = rng.uniform(0.30, 0.99)
            rot = rng.uniform(0, 180)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (max(2, rx // 2), max(2, ry // 2)), rot, 30, 260, val * 0.70, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.40:
                _cv2.circle(CC, (cx + int(rx * 0.35), cy - int(ry * 0.25)), max(1, int(2.0 * sc)), rng.uniform(0.58, 0.99), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _blue_pearl_shell_current_field(shape, seed, sm, name="blue_pearl_shell_current_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84503)
    M, R, CC = _base(shape, int(seed), 0.12, 0.09, 0.28, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(26, int(60 * sc)), max(24, int(54 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off, y
                rot = rng.uniform(0, 180)
                val = rng.uniform(0.34, 0.98)
                for k in range(4):
                    rx = max(5, int((8 + k * 3.8) * sc))
                    ry = max(3, int(rx * 0.52))
                    _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 6, 205, 25, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 6, 215, 15, val * 0.66, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.50:
                    _cv2.circle(CC, (cx, cy), max(1, int(2.6 * sc)), rng.uniform(0.58, 0.99), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _copper_verdigris_leaf_lattice(shape, seed, sm, name="copper_verdigris_leaf_lattice"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84504)
    M, R, CC = _base(shape, int(seed), 0.16, 0.14, 0.15, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(26, int(58 * sc)), max(24, int(54 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off + int(rng.uniform(-4, 4) * sc), y + int(rng.uniform(-4, 4) * sc)
                rot = rng.uniform(0, 180)
                val = rng.uniform(0.30, 0.94)
                rx, ry = max(6, int(rng.uniform(10, 18) * sc)), max(3, int(rng.uniform(4, 9) * sc))
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, min(0.99, val + 0.07), 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (int(cx - math.cos(math.radians(rot)) * rx), int(cy - math.sin(math.radians(rot)) * ry)), (int(cx + math.cos(math.radians(rot)) * rx), int(cy + math.sin(math.radians(rot)) * ry)), val, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.35:
                    _cv2.circle(R, (cx, cy), max(1, int(2.3 * sc)), val * 0.18, -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _forged_carbon_talon_plate_swarm(shape, seed, sm, name="forged_carbon_talon_plate_swarm"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84505)
    M, R, CC = _base(shape, int(seed), 0.08, 0.11, 0.16, 0.052)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(24, int(58 * sc)), max(22, int(48 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off + int(rng.uniform(-8, 8) * sc), y + int(rng.uniform(-7, 7) * sc)
                length = rng.uniform(16, 42) * sc
                width = rng.uniform(5, 12) * sc
                rot = rng.uniform(0, math.tau)
                pts = [(int(cx + math.cos(rot) * length), int(cy + math.sin(rot) * length)),
                       (int(cx + math.cos(rot + 1.95) * width), int(cy + math.sin(rot + 1.95) * width)),
                       (int(cx - math.cos(rot) * length * 0.55), int(cy - math.sin(rot) * length * 0.55)),
                       (int(cx + math.cos(rot - 1.95) * width), int(cy + math.sin(rot - 1.95) * width))]
                poly = np.asarray(pts, dtype=np.int32)
                val = rng.uniform(0.18, 0.88)
                _cv2.fillPoly(M, [poly], val * 0.58, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [poly], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _liquid_chrome_mercury_cells_dense(shape, seed, sm, name="liquid_chrome_mercury_cells_dense"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84506)
    M, R, CC = _base(shape, int(seed), 0.18, 0.08, 0.31, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(30, int(70 * sc)), max(26, int(60 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off + int(rng.uniform(-8, 8) * sc), y + int(rng.uniform(-8, 8) * sc)
                rot = rng.uniform(0, 180)
                for k in range(3):
                    rx = max(8, int((12 + k * 7) * sc))
                    ry = max(4, int(rx * rng.uniform(0.36, 0.62)))
                    val = rng.uniform(0.36, 0.99)
                    _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 13, 0, 360, val, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(M, (cx, cy), (max(3, rx // 2), max(2, ry // 2)), rot + k * 13, 205, 350, val * 0.75, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _burl_engraved_terrace_maze(shape, seed, sm, name="burl_engraved_terrace_maze"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84507)
    M, R, CC = _base(shape, int(seed), 0.14, 0.13, 0.16, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(36, int(82 * sc)), max(30, int(70 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off, y
                rot = rng.uniform(0, 180)
                for k in range(5):
                    rx = max(7, int((10 + k * 5.4) * sc))
                    ry = max(3, int(rx * rng.uniform(0.34, 0.66)))
                    val = rng.uniform(0.24, 0.88)
                    _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 4, 0, 360, val, 1, lineType=_cv2.LINE_AA)
                    if k % 2:
                        _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 4, 15, 205, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.34:
                    _cv2.line(CC, (cx - int(18 * sc), cy), (cx + int(18 * sc), cy + int(rng.uniform(-8, 8) * sc)), rng.uniform(0.30, 0.78), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _magnetic_filing_compass_burst_field(shape, seed, sm, name="magnetic_filing_compass_burst_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84508)
    M, R, CC = _base(shape, int(seed), 0.11, 0.08, 0.22, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(34, int(76 * sc)), max(32, int(72 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off + int(rng.uniform(-6, 6) * sc), y + int(rng.uniform(-6, 6) * sc)
                val = rng.uniform(0.30, 0.94)
                arms = int(rng.integers(6, 10))
                for a in range(arms):
                    ang = a * math.tau / arms + rng.uniform(-0.10, 0.10)
                    length = rng.uniform(8, 22) * sc
                    p2 = (int(cx + math.cos(ang) * length), int(cy + math.sin(ang) * length))
                    _cv2.line(M, (cx, cy), p2, val * rng.uniform(0.65, 1.0), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), max(1, int(2.4 * sc)), min(0.99, val + 0.05), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_brushstroke_bold(shape, seed, sm, **kwargs): return _ink_lacquer_fan_scale_field(shape, seed + 2601, sm)
def rescue_cc_fish_eye(shape, seed, sm, **kwargs): return _clearcoat_bubble_chain_reef_dense(shape, seed + 2602, sm)
def rescue_cloud_wisps_cool(shape, seed, sm, **kwargs): return _blue_pearl_shell_current_field(shape, seed + 2603, sm)
def rescue_copper_patina_drip(shape, seed, sm, **kwargs): return _copper_verdigris_leaf_lattice(shape, seed + 2604, sm)
def rescue_forged_carbon_chip(shape, seed, sm, **kwargs): return _forged_carbon_talon_plate_swarm(shape, seed + 2605, sm)
def rescue_spec_oil_film_thick(shape, seed, sm, **kwargs): return _liquid_chrome_mercury_cells_dense(shape, seed + 2606, sm)
def rescue_spec_wood_grain_fine(shape, seed, sm, **kwargs): return _burl_engraved_terrace_maze(shape, seed + 2607, sm)
def rescue_magnetic_field(shape, seed, sm, **kwargs): return _magnetic_filing_compass_burst_field(shape, seed + 2608, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass9-iteration3:
# Remove the last obvious grid crutches from the pass9 target set.
def _retro_turntable_prism_collision(shape, seed, sm, name="retro_turntable_prism_collision"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84601)
    M, R, CC = _base(shape, int(seed), 0.10, 0.08, 0.25, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 170, 32)):
            cx, cy = int(rng.integers(-40, w + 40)), int(rng.integers(-40, h + 40))
            rot = rng.uniform(0, 180)
            for k in range(5):
                r = max(6, int((8 + k * rng.uniform(5, 10)) * sc))
                val = rng.uniform(0.28, 0.98)
                start = rng.uniform(0, 270)
                _cv2.ellipse(CC, (cx, cy), (r, r), rot, start, start + rng.uniform(65, 190), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                if k % 2 == 0:
                    _cv2.ellipse(M, (cx, cy), (r, r), rot, start + 12, start + rng.uniform(55, 150), val * 0.72, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.44:
                _draw_glint(M, R, CC, int(np.clip(cx, 0, w - 1)), int(np.clip(cy, 0, h - 1)), max(2, int(4 * sc)), (0.84, 0.10, 0.95))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _random_lacquer_fan_chop_field(shape, seed, sm, name="random_lacquer_fan_chop_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84602)
    M, R, CC = _base(shape, int(seed), 0.11, 0.08, 0.22, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 460, 82)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.28, 0.98)
            arms = int(rng.integers(3, 7))
            for k in range(arms):
                length = rng.uniform(8, 26) * sc
                a = math.radians(rot + (k - arms / 2) * rng.uniform(7, 15))
                p2 = (int(cx + math.cos(a) * length), int(cy + math.sin(a) * length))
                _cv2.line(M, (cx, cy), p2, val * rng.uniform(0.62, 1.0), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.38:
                _cv2.circle(CC, (cx, cy), max(1, int(2.2 * sc)), rng.uniform(0.46, 0.98), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _clearcoat_fisheye_depth_bubbles(shape, seed, sm, name="clearcoat_fisheye_depth_bubbles"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84603)
    M, R, CC = _base(shape, int(seed), 0.08, 0.07, 0.31, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 430, 80)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(5, int(rng.uniform(7, 19) * sc)), max(4, int(rng.uniform(5, 17) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.30, 0.99)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (max(2, rx // 2), max(2, ry // 2)), rot + 20, 0, 360, val * 0.62, -1 if rng.random() < 0.22 else 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), max(1, int(2.4 * sc)), val * 0.15, -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _hammered_flake_broken_ice(shape, seed, sm, name="hammered_flake_broken_ice"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84604)
    M, R, CC = _base(shape, int(seed), 0.13, 0.10, 0.24, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 620, 110)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(4, int(rng.uniform(5, 13) * sc))
            sides = int(rng.integers(4, 7))
            rot = rng.uniform(0, math.tau)
            pts = [(int(cx + math.cos(rot + k * math.tau / sides) * r * rng.uniform(0.65, 1.20)), int(cy + math.sin(rot + k * math.tau / sides) * r * rng.uniform(0.65, 1.20))) for k in range(sides)]
            poly = np.asarray(pts, dtype=np.int32)
            val = rng.uniform(0.24, 0.98)
            _cv2.fillPoly(M, [poly], val * 0.34, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.07), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _enamel_drip_gravity_threads(shape, seed, sm, name="enamel_drip_gravity_threads"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84605)
    M, R, CC = _base(shape, int(seed), 0.11, 0.08, 0.25, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 260, 48)):
            x = int(rng.integers(0, w))
            y = int(rng.integers(-20, h))
            length = int(rng.uniform(18, 90) * sc)
            pts = []
            for k in range(12):
                yy = y + int(k * length / 11)
                xx = x + int(math.sin(k * 0.85 + y) * rng.uniform(2, 8) * sc)
                pts.append((np.clip(xx, 0, w - 1), np.clip(yy, 0, h - 1)))
            val = rng.uniform(0.32, 0.98)
            _polyline(CC, pts, min(0.99, val + 0.04), 1)
            _polyline(M, pts, val * 0.68, 1)
            if rng.random() < 0.72:
                bx, by = pts[-1]
                _cv2.ellipse(CC, (bx, by), (max(2, int(4 * sc)), max(3, int(7 * sc))), 0, 0, 360, rng.uniform(0.50, 0.99), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _ferrofluid_pinwheel_filing_storm(shape, seed, sm, name="ferrofluid_pinwheel_filing_storm"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84606)
    M, R, CC = _base(shape, int(seed), 0.10, 0.08, 0.22, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 240, 45)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            val = rng.uniform(0.28, 0.94)
            for k in range(7):
                ang = k * math.tau / 7 + rng.uniform(-0.18, 0.18)
                length = rng.uniform(8, 24) * sc
                p1 = (int(cx + math.cos(ang) * 2 * sc), int(cy + math.sin(ang) * 2 * sc))
                p2 = (int(cx + math.cos(ang + 0.22) * length), int(cy + math.sin(ang + 0.22) * length))
                _cv2.line(M, p1, p2, val * rng.uniform(0.60, 1.0), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.55:
                _cv2.circle(CC, (cx, cy), max(1, int(2.5 * sc)), min(0.99, val + 0.05), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_abstract_retro_wave(shape, seed, sm, **kwargs): return _retro_turntable_prism_collision(shape, seed + 2701, sm)
def rescue_brushstroke_bold(shape, seed, sm, **kwargs): return _random_lacquer_fan_chop_field(shape, seed + 2702, sm)
def rescue_cc_fish_eye(shape, seed, sm, **kwargs): return _clearcoat_fisheye_depth_bubbles(shape, seed + 2703, sm)
def rescue_flake_scatter(shape, seed, sm, **kwargs): return _hammered_flake_broken_ice(shape, seed + 2704, sm)
def rescue_paint_drip_edge(shape, seed, sm, **kwargs): return _enamel_drip_gravity_threads(shape, seed + 2705, sm)
def rescue_magnetic_field(shape, seed, sm, **kwargs): return _ferrofluid_pinwheel_filing_storm(shape, seed + 2706, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass9-iteration4:
# Iteration3 got too quiet. Restore density without returning to perfect rows.
def _dense_retro_prism_orbit_soup(shape, seed, sm, name="dense_retro_prism_orbit_soup"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84701)
    M, R, CC = _base(shape, int(seed), 0.10, 0.08, 0.25, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 480, 88)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.30, 0.99)
            for k in range(int(rng.integers(2, 5))):
                r = max(5, int(rng.uniform(7, 20) * sc + k * 3 * sc))
                start = rng.uniform(0, 300)
                _cv2.ellipse(CC, (cx, cy), (r, r), rot, start, start + rng.uniform(80, 220), min(0.99, val + 0.04), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (r, r), rot, start + 8, start + rng.uniform(55, 170), val * 0.70, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.22:
                _draw_glint(M, R, CC, cx, cy, max(2, int(3.5 * sc)), (0.82, 0.10, 0.94))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _dense_lacquer_slash_fan_carpet(shape, seed, sm, name="dense_lacquer_slash_fan_carpet"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84702)
    M, R, CC = _base(shape, int(seed), 0.11, 0.08, 0.22, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 980, 170)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, math.tau)
            val = rng.uniform(0.28, 0.98)
            length = rng.uniform(7, 22) * sc
            p1 = (int(cx - math.cos(rot) * length * 0.25), int(cy - math.sin(rot) * length * 0.25))
            p2 = (int(cx + math.cos(rot) * length), int(cy + math.sin(rot) * length))
            _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.34:
                _cv2.line(CC, (p1[0] + 1, p1[1]), (p2[0] + 1, p2[1]), min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _clearcoat_fisheye_pearl_reef(shape, seed, sm, name="clearcoat_fisheye_pearl_reef"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84703)
    M, R, CC = _base(shape, int(seed), 0.08, 0.07, 0.31, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 620, 112)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(4, int(rng.uniform(6, 15) * sc)), max(4, int(rng.uniform(6, 15) * sc))
            val = rng.uniform(0.34, 0.99)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.38:
                _cv2.ellipse(M, (cx, cy), (max(2, rx // 2), max(2, ry // 2)), rng.uniform(0, 180), 0, 360, val * 0.62, -1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.52:
                _cv2.circle(CC, (cx + int(rx * 0.25), cy - int(ry * 0.25)), max(1, int(2 * sc)), min(0.99, val + 0.05), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _random_hammered_flake_galaxy(shape, seed, sm, name="random_hammered_flake_galaxy"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84704)
    M, R, CC = _base(shape, int(seed), 0.13, 0.10, 0.24, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 900, 160)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(3, int(rng.uniform(4, 11) * sc))
            sides = int(rng.integers(4, 7))
            rot = rng.uniform(0, math.tau)
            pts = [(int(cx + math.cos(rot + k * math.tau / sides) * r * rng.uniform(0.65, 1.25)), int(cy + math.sin(rot + k * math.tau / sides) * r * rng.uniform(0.65, 1.25))) for k in range(sides)]
            poly = np.asarray(pts, dtype=np.int32)
            val = rng.uniform(0.28, 0.99)
            _cv2.fillPoly(M, [poly], val * 0.36, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.16:
                _draw_glint(M, R, CC, cx, cy, max(1, int(2.5 * sc)), (0.86, 0.10, 0.94))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _enamel_drip_beaded_rainstorm(shape, seed, sm, name="enamel_drip_beaded_rainstorm"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84705)
    M, R, CC = _base(shape, int(seed), 0.11, 0.08, 0.26, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 430, 78)):
            x = int(rng.integers(0, w))
            y = int(rng.integers(-20, h))
            length = int(rng.uniform(22, 95) * sc)
            pts = []
            for k in range(14):
                yy = y + int(k * length / 13)
                xx = x + int(math.sin(k * 0.74 + y * 0.02) * rng.uniform(2, 7) * sc)
                pts.append((np.clip(xx, 0, w - 1), np.clip(yy, 0, h - 1)))
            val = rng.uniform(0.32, 0.98)
            _polyline(CC, pts, min(0.99, val + 0.04), 1)
            _polyline(M, pts, val * 0.66, 1)
            for bx, by in pts[3::5]:
                if rng.random() < 0.55:
                    _cv2.ellipse(CC, (bx, by), (max(2, int(3 * sc)), max(2, int(5 * sc))), 0, 0, 360, rng.uniform(0.48, 0.99), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _dense_ferrofluid_compass_storm(shape, seed, sm, name="dense_ferrofluid_compass_storm"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84706)
    M, R, CC = _base(shape, int(seed), 0.10, 0.08, 0.22, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 520, 92)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            val = rng.uniform(0.28, 0.95)
            arms = int(rng.integers(4, 8))
            for k in range(arms):
                ang = k * math.tau / arms + rng.uniform(-0.22, 0.22)
                length = rng.uniform(6, 18) * sc
                p2 = (int(cx + math.cos(ang) * length), int(cy + math.sin(ang) * length))
                _cv2.line(M, (cx, cy), p2, val * rng.uniform(0.58, 1.0), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.35:
                _cv2.circle(CC, (cx, cy), max(1, int(2 * sc)), min(0.99, val + 0.05), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_abstract_retro_wave(shape, seed, sm, **kwargs): return _dense_retro_prism_orbit_soup(shape, seed + 2801, sm)
def rescue_brushstroke_bold(shape, seed, sm, **kwargs): return _dense_lacquer_slash_fan_carpet(shape, seed + 2802, sm)
def rescue_cc_fish_eye(shape, seed, sm, **kwargs): return _clearcoat_fisheye_pearl_reef(shape, seed + 2803, sm)
def rescue_flake_scatter(shape, seed, sm, **kwargs): return _random_hammered_flake_galaxy(shape, seed + 2804, sm)
def rescue_paint_drip_edge(shape, seed, sm, **kwargs): return _enamel_drip_beaded_rainstorm(shape, seed + 2805, sm)
def rescue_magnetic_field(shape, seed, sm, **kwargs): return _dense_ferrofluid_compass_storm(shape, seed + 2806, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass10:
# Targeting remaining quiet dot/row/simple-line thumbnails with stronger material identities.
def _machined_moire_turbine_eyes(shape, seed, sm, name="machined_moire_turbine_eyes"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84801)
    M, R, CC = _base(shape, int(seed), 0.12, 0.08, 0.22, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 210, 42)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            for k in range(7):
                rx = max(5, int((7 + k * 3.4) * sc))
                ry = max(2, int(rx * rng.uniform(0.30, 0.55)))
                val = rng.uniform(0.30, 0.98)
                start = rng.uniform(0, 260)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 11, start, start + rng.uniform(70, 170), min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 11, start + 8, start + rng.uniform(55, 140), val * 0.72, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.55:
                _draw_glint(M, R, CC, cx, cy, max(2, int(3.2 * sc)), (0.78, 0.10, 0.88))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _carbon_ceramic_brake_star_pitting(shape, seed, sm, name="carbon_ceramic_brake_star_pitting"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84802)
    M, R, CC = _base(shape, int(seed), 0.10, 0.16, 0.12, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 420, 78)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            val = rng.uniform(0.24, 0.90)
            r = max(3, int(rng.uniform(4, 11) * sc))
            _cv2.circle(R, (cx, cy), r, val * 0.18, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (r * 2, max(2, r // 2)), rng.uniform(0, 180), 180, 360, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.45:
                _cv2.circle(CC, (cx + int(rng.uniform(-r, r)), cy + int(rng.uniform(-r, r))), max(1, int(2 * sc)), rng.uniform(0.36, 0.86), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _orbital_polish_thumbprint_whorls(shape, seed, sm, name="orbital_polish_thumbprint_whorls"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84803)
    M, R, CC = _base(shape, int(seed), 0.13, 0.08, 0.25, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 165, 32)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            for k in range(7):
                rx = max(6, int((8 + k * 4.1) * sc))
                ry = max(3, int(rx * rng.uniform(0.38, 0.65)))
                val = rng.uniform(0.28, 0.96)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 5, 0, 360, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                if k % 2 == 0:
                    _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 5, 35, 260, val * 0.68, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), max(1, int(2.5 * sc)), rng.uniform(0.48, 0.98), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _masking_tape_torn_adhesive_islands(shape, seed, sm, name="masking_tape_torn_adhesive_islands"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84804)
    M, R, CC = _base(shape, int(seed), 0.12, 0.10, 0.20, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 260, 50)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            length = rng.uniform(20, 62) * sc
            angle = rng.uniform(0, math.tau)
            pts = []
            for k in range(7):
                t = k / 6 - 0.5
                wob = rng.uniform(-5, 5) * sc
                x = cx + math.cos(angle) * length * t + math.cos(angle + math.pi / 2) * wob
                y = cy + math.sin(angle) * length * t + math.sin(angle + math.pi / 2) * wob
                pts.append((int(np.clip(x, 0, w - 1)), int(np.clip(y, 0, h - 1))))
            val = rng.uniform(0.26, 0.88)
            _polyline(M, pts, val, 1)
            _polyline(CC, [(x + 1, y) for x, y in pts], min(0.99, val + 0.08), 1)
            if rng.random() < 0.50:
                _cv2.ellipse(R, (cx, cy), (max(4, int(length * 0.22)), max(2, int(4 * sc))), math.degrees(angle), 0, 360, val * 0.16, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _voodoo_ember_pin_sparks_dense(shape, seed, sm, name="voodoo_ember_pin_sparks_dense"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84805)
    M, R, CC = _base(shape, int(seed), 0.12, 0.12, 0.16, 0.05)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 720, 130)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            length = rng.uniform(6, 18) * sc
            ang = rng.uniform(0, math.tau)
            val = rng.uniform(0.30, 0.98)
            p1 = (int(cx - math.cos(ang) * length * 0.25), int(cy - math.sin(ang) * length * 0.25))
            p2 = (int(cx + math.cos(ang) * length), int(cy + math.sin(ang) * length))
            _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.55:
                _cv2.circle(CC, p2, max(1, int(2.4 * sc)), min(0.99, val + 0.05), -1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.10:
                _draw_glint(M, R, CC, cx, cy, max(2, int(3 * sc)), (0.98, 0.07, 0.72))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _vinyl_lift_curl_torn_confetti(shape, seed, sm, name="vinyl_lift_curl_torn_confetti"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84806)
    M, R, CC = _base(shape, int(seed), 0.12, 0.10, 0.24, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 560, 100)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(4, int(rng.uniform(6, 15) * sc)), max(2, int(rng.uniform(3, 8) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.28, 0.96)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 190, 30, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 205, 15, val * 0.70, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.35:
                _cv2.line(R, (cx - rx, cy), (cx + rx, cy + int(ry * 0.6)), val * 0.18, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _diamond_dust_star_cut_facets(shape, seed, sm, name="diamond_dust_star_cut_facets"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84807)
    M, R, CC = _base(shape, int(seed), 0.10, 0.07, 0.23, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 660, 118)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(4, int(rng.uniform(5, 13) * sc))
            val = rng.uniform(0.30, 0.99)
            pts = []
            rot = rng.uniform(0, math.tau)
            for k in range(4):
                pts.append((int(cx + math.cos(rot + k * math.pi / 2) * r * rng.uniform(0.7, 1.2)), int(cy + math.sin(rot + k * math.pi / 2) * r * rng.uniform(0.7, 1.2))))
            poly = np.asarray(pts, dtype=np.int32)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, pts[0], pts[2], val * 0.78, 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, pts[1], pts[3], rng.uniform(0.25, 0.82), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _microfiber_hand_polish_crossfire(shape, seed, sm, name="microfiber_hand_polish_crossfire"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84808)
    M, R, CC = _base(shape, int(seed), 0.12, 0.08, 0.23, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1050, 185)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ang = rng.choice([0.25, -0.55, 1.1, -1.25]) + rng.normal(0, 0.12)
            length = rng.uniform(7, 24) * sc
            val = rng.uniform(0.24, 0.88)
            p1 = (int(cx - math.cos(ang) * length * 0.5), int(cy - math.sin(ang) * length * 0.5))
            p2 = (int(cx + math.cos(ang) * length * 0.5), int(cy + math.sin(ang) * length * 0.5))
            _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.26:
                _cv2.line(CC, (p1[0] + 1, p1[1]), (p2[0] + 1, p2[1]), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _micro_sparkle_nebula_cartography(shape, seed, sm, name="micro_sparkle_nebula_cartography"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84809)
    M, R, CC = _base(shape, int(seed), 0.08, 0.06, 0.26, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1350, 230)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            val = rng.uniform(0.35, 0.99)
            _cv2.circle(CC, (x, y), max(1, int(rng.uniform(1, 2.8) * sc)), val, -1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.11:
                _draw_glint(M, R, CC, x, y, max(2, int(3.5 * sc)), (0.88, 0.10, 0.96))
        for _ in range(_count(shape, 110, 20)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            pts = []
            for k in range(36):
                r = k * 0.85 * sc
                a = k * 0.42
                pts.append((int(np.clip(cx + math.cos(a) * r, 0, w - 1)), int(np.clip(cy + math.sin(a) * r, 0, h - 1))))
            _polyline(M, pts, rng.uniform(0.18, 0.55), 1)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _comet_scratch_orbit_chains(shape, seed, sm, name="comet_scratch_orbit_chains"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84810)
    M, R, CC = _base(shape, int(seed), 0.09, 0.06, 0.24, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 260, 48)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(10, int(rng.uniform(16, 48) * sc)), max(4, int(rng.uniform(6, 18) * sc))
            rot = rng.uniform(0, 180)
            start = rng.uniform(0, 300)
            val = rng.uniform(0.26, 0.90)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, start, start + rng.uniform(60, 180), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, start + 10, start + rng.uniform(45, 140), val * 0.70, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.42:
                a = math.radians(rot + start)
                _draw_glint(M, R, CC, int(np.clip(cx + math.cos(a) * rx, 0, w - 1)), int(np.clip(cy + math.sin(a) * ry, 0, h - 1)), max(2, int(3.5 * sc)), (0.84, 0.10, 0.96))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _holo_foil_prism_shard_weave(shape, seed, sm, name="holo_foil_prism_shard_weave"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84811)
    M, R, CC = _base(shape, int(seed), 0.15, 0.07, 0.30, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 520, 95)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            length = rng.uniform(12, 38) * sc
            width = rng.uniform(4, 11) * sc
            rot = rng.uniform(0, math.tau)
            pts = [(int(cx + math.cos(rot) * length), int(cy + math.sin(rot) * length)),
                   (int(cx + math.cos(rot + 1.8) * width), int(cy + math.sin(rot + 1.8) * width)),
                   (int(cx - math.cos(rot) * length * 0.65), int(cy - math.sin(rot) * length * 0.65)),
                   (int(cx + math.cos(rot - 1.8) * width), int(cy + math.sin(rot - 1.8) * width))]
            poly = np.asarray(pts, dtype=np.int32)
            val = rng.uniform(0.30, 0.99)
            _cv2.fillPoly(M, [poly], val * 0.30, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.22:
                _draw_glint(M, R, CC, cx, cy, max(1, int(3 * sc)), (0.90, 0.08, 0.96))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _rubber_scuff_wheel_arc_overlaps(shape, seed, sm, name="rubber_scuff_wheel_arc_overlaps"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84812)
    M, R, CC = _base(shape, int(seed), 0.09, 0.14, 0.13, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 420, 76)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(10, int(rng.uniform(14, 36) * sc)), max(3, int(rng.uniform(4, 10) * sc))
            rot = rng.uniform(-35, 35)
            val = rng.uniform(0.22, 0.88)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 185, 355, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rx, ry), rot, 185, 355, val * 0.20, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.34:
                _cv2.circle(CC, (cx, cy), max(1, int(2.2 * sc)), rng.uniform(0.28, 0.72), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_aniso_grain_deep(shape, seed, sm, **kwargs): return _machined_moire_turbine_eyes(shape, seed + 2901, sm)
def rescue_brake_dust_buildup(shape, seed, sm, **kwargs): return _carbon_ceramic_brake_star_pitting(shape, seed + 2902, sm)
def rescue_buffer_swirl(shape, seed, sm, **kwargs): return _orbital_polish_thumbprint_whorls(shape, seed + 2903, sm)
def rescue_cc_masking_edge(shape, seed, sm, **kwargs): return _masking_tape_torn_adhesive_islands(shape, seed + 2904, sm)
def rescue_cloud_wisps_warm(shape, seed, sm, **kwargs): return _voodoo_ember_pin_sparks_dense(shape, seed + 2905, sm)
def rescue_decal_lift_edge(shape, seed, sm, **kwargs): return _vinyl_lift_curl_torn_confetti(shape, seed + 2906, sm)
def rescue_diamond_dust(shape, seed, sm, **kwargs): return _diamond_dust_star_cut_facets(shape, seed + 2907, sm)
def rescue_hand_polished(shape, seed, sm, **kwargs): return _microfiber_hand_polish_crossfire(shape, seed + 2908, sm)
def rescue_micro_sparkle(shape, seed, sm, **kwargs): return _micro_sparkle_nebula_cartography(shape, seed + 2909, sm)
def rescue_sparkle_comet(shape, seed, sm, **kwargs): return _comet_scratch_orbit_chains(shape, seed + 2910, sm)
def rescue_spec_holographic_foil(shape, seed, sm, **kwargs): return _holo_foil_prism_shard_weave(shape, seed + 2911, sm)
def rescue_wear_scuff(shape, seed, sm, **kwargs): return _rubber_scuff_wheel_arc_overlaps(shape, seed + 2912, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass10-iteration2:
# First pass was too sparse at review size. Raise coverage and make the silhouettes read.
def _machined_turbine_scale_dense(shape, seed, sm, name="machined_turbine_scale_dense"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84901)
    M, R, CC = _base(shape, int(seed), 0.12, 0.08, 0.22, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(22, int(48 * sc)), max(18, int(40 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off + int(rng.uniform(-3, 3) * sc), y + int(rng.uniform(-3, 3) * sc)
                rot = rng.uniform(-28, 28)
                for k in range(5):
                    rx = max(4, int((6 + k * 2.7) * sc))
                    ry = max(2, int(rx * 0.42))
                    val = rng.uniform(0.30, 0.98)
                    _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 8, 200, 345, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 8, 210, 330, val * 0.70, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _brake_scorch_arc_pitted_dense(shape, seed, sm, name="brake_scorch_arc_pitted_dense"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84902)
    M, R, CC = _base(shape, int(seed), 0.10, 0.16, 0.12, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 760, 135)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(5, int(rng.uniform(8, 19) * sc)), max(2, int(rng.uniform(3, 7) * sc))
            val = rng.uniform(0.24, 0.90)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rng.uniform(0, 180), 185, 355, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.55:
                _cv2.circle(R, (cx, cy), max(1, int(rng.uniform(1.5, 3.5) * sc)), val * 0.20, -1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.35:
                _cv2.circle(CC, (cx, cy), max(1, int(2 * sc)), rng.uniform(0.35, 0.86), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _buffer_whorl_shell_carpet(shape, seed, sm, name="buffer_whorl_shell_carpet"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84903)
    M, R, CC = _base(shape, int(seed), 0.13, 0.08, 0.25, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(30, int(68 * sc)), max(26, int(58 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off + int(rng.uniform(-8, 8) * sc), y + int(rng.uniform(-8, 8) * sc)
                rot = rng.uniform(0, 180)
                for k in range(5):
                    rx = max(5, int((7 + k * 4) * sc))
                    ry = max(3, int(rx * rng.uniform(0.38, 0.62)))
                    val = rng.uniform(0.28, 0.96)
                    _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 7, 15, 320, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 7, 35, 250, val * 0.66, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _torn_masking_edge_crosshatch(shape, seed, sm, name="torn_masking_edge_crosshatch"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84904)
    M, R, CC = _base(shape, int(seed), 0.12, 0.10, 0.20, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 620, 110)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            length = rng.uniform(14, 44) * sc
            angle = rng.choice([0.35, -0.65, 1.15, -1.35]) + rng.normal(0, 0.12)
            val = rng.uniform(0.26, 0.88)
            p1 = (int(cx - math.cos(angle) * length / 2), int(cy - math.sin(angle) * length / 2))
            p2 = (int(cx + math.cos(angle) * length / 2), int(cy + math.sin(angle) * length / 2))
            _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (p1[0] + 1, p1[1]), (p2[0] + 1, p2[1]), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.24:
                _cv2.circle(R, (cx, cy), max(1, int(2 * sc)), val * 0.16, -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _ember_pin_sigil_dense(shape, seed, sm, name="ember_pin_sigil_dense"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84905)
    M, R, CC = _base(shape, int(seed), 0.12, 0.12, 0.16, 0.052)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1250, 215)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            length = rng.uniform(5, 16) * sc
            ang = rng.uniform(0, math.tau)
            val = rng.uniform(0.30, 0.98)
            p1 = (int(cx - math.cos(ang) * length * 0.30), int(cy - math.sin(ang) * length * 0.30))
            p2 = (int(cx + math.cos(ang) * length), int(cy + math.sin(ang) * length))
            _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.42:
                _cv2.circle(CC, p2, max(1, int(2 * sc)), min(0.99, val + 0.05), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _vinyl_curl_shingle_field(shape, seed, sm, name="vinyl_curl_shingle_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84906)
    M, R, CC = _base(shape, int(seed), 0.12, 0.10, 0.24, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(22, int(50 * sc)), max(20, int(46 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off + int(rng.uniform(-4, 4) * sc), y + int(rng.uniform(-5, 5) * sc)
                rx, ry = max(4, int(rng.uniform(6, 14) * sc)), max(2, int(rng.uniform(3, 8) * sc))
                rot = rng.uniform(-35, 35)
                val = rng.uniform(0.28, 0.96)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 190, 30, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 205, 15, val * 0.70, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _diamond_microfacet_dense_field(shape, seed, sm, name="diamond_microfacet_dense_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84907)
    M, R, CC = _base(shape, int(seed), 0.10, 0.07, 0.23, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1050, 185)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(3, int(rng.uniform(4, 10) * sc))
            rot = rng.uniform(0, math.tau)
            val = rng.uniform(0.30, 0.99)
            pts = [(int(cx + math.cos(rot + k * math.pi / 2) * r * rng.uniform(0.7, 1.2)), int(cy + math.sin(rot + k * math.pi / 2) * r * rng.uniform(0.7, 1.2))) for k in range(4)]
            poly = np.asarray(pts, dtype=np.int32)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, pts[0], pts[2], val * 0.76, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.35:
                _cv2.line(M, pts[1], pts[3], rng.uniform(0.24, 0.82), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _comet_orbit_glyph_storm(shape, seed, sm, name="comet_orbit_glyph_storm"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84908)
    M, R, CC = _base(shape, int(seed), 0.09, 0.06, 0.24, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 520, 95)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(8, int(rng.uniform(12, 34) * sc)), max(4, int(rng.uniform(5, 14) * sc))
            rot = rng.uniform(0, 180)
            start = rng.uniform(0, 300)
            val = rng.uniform(0.26, 0.92)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, start, start + rng.uniform(70, 190), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, start + 10, start + rng.uniform(50, 150), val * 0.70, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _holo_prism_shattered_leaf_field(shape, seed, sm, name="holo_prism_shattered_leaf_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84909)
    M, R, CC = _base(shape, int(seed), 0.15, 0.07, 0.30, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 820, 145)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            length = rng.uniform(9, 28) * sc
            width = rng.uniform(3, 9) * sc
            rot = rng.uniform(0, math.tau)
            pts = [(int(cx + math.cos(rot) * length), int(cy + math.sin(rot) * length)),
                   (int(cx + math.cos(rot + 1.9) * width), int(cy + math.sin(rot + 1.9) * width)),
                   (int(cx - math.cos(rot) * length * 0.62), int(cy - math.sin(rot) * length * 0.62)),
                   (int(cx + math.cos(rot - 1.9) * width), int(cy + math.sin(rot - 1.9) * width))]
            poly = np.asarray(pts, dtype=np.int32)
            val = rng.uniform(0.30, 0.99)
            _cv2.fillPoly(M, [poly], val * 0.28, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _rubber_arc_scuff_storm(shape, seed, sm, name="rubber_arc_scuff_storm"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 84910)
    M, R, CC = _base(shape, int(seed), 0.09, 0.14, 0.13, 0.06)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 720, 130)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(8, int(rng.uniform(10, 30) * sc)), max(2, int(rng.uniform(3, 8) * sc))
            rot = rng.uniform(-45, 45)
            val = rng.uniform(0.22, 0.88)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, 185, 355, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.55:
                _cv2.ellipse(R, (cx, cy), (rx, ry), rot, 185, 355, val * 0.20, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.22:
                _cv2.circle(CC, (cx, cy), max(1, int(2.2 * sc)), rng.uniform(0.28, 0.72), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_aniso_grain_deep(shape, seed, sm, **kwargs): return _machined_turbine_scale_dense(shape, seed + 3001, sm)
def rescue_brake_dust_buildup(shape, seed, sm, **kwargs): return _brake_scorch_arc_pitted_dense(shape, seed + 3002, sm)
def rescue_buffer_swirl(shape, seed, sm, **kwargs): return _buffer_whorl_shell_carpet(shape, seed + 3003, sm)
def rescue_cc_masking_edge(shape, seed, sm, **kwargs): return _torn_masking_edge_crosshatch(shape, seed + 3004, sm)
def rescue_cloud_wisps_warm(shape, seed, sm, **kwargs): return _ember_pin_sigil_dense(shape, seed + 3005, sm)
def rescue_decal_lift_edge(shape, seed, sm, **kwargs): return _vinyl_curl_shingle_field(shape, seed + 3006, sm)
def rescue_diamond_dust(shape, seed, sm, **kwargs): return _diamond_microfacet_dense_field(shape, seed + 3007, sm)
def rescue_sparkle_comet(shape, seed, sm, **kwargs): return _comet_orbit_glyph_storm(shape, seed + 3008, sm)
def rescue_spec_holographic_foil(shape, seed, sm, **kwargs): return _holo_prism_shattered_leaf_field(shape, seed + 3009, sm)
def rescue_wear_scuff(shape, seed, sm, **kwargs): return _rubber_arc_scuff_storm(shape, seed + 3010, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass11:
# Focused rescue for remaining sparse/dust-like thumbnails after pass10 visual review.
def _optical_vinyl_groove_constellations(shape, seed, sm, name="optical_vinyl_groove_constellations"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85001)
    M, R, CC = _base(shape, int(seed), 0.10, 0.07, 0.26, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 360, 66)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.30, 0.99)
            for k in range(4):
                rx = max(6, int((8 + k * rng.uniform(4, 8)) * sc))
                ry = max(3, int(rx * rng.uniform(0.38, 0.68)))
                start = rng.uniform(0, 300)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rot + k * 10, start, start + rng.uniform(90, 220), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx, cy), (rx, ry), rot + k * 10, start + 12, start + rng.uniform(65, 170), val * 0.70, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.35:
                _draw_glint(M, R, CC, cx, cy, max(2, int(3.5 * sc)), (0.82, 0.10, 0.96))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _lacquer_katana_scratch_garden(shape, seed, sm, name="lacquer_katana_scratch_garden"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85002)
    M, R, CC = _base(shape, int(seed), 0.11, 0.08, 0.22, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1400, 240)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ang = rng.choice([0.15, -0.45, 0.85, -1.10, 1.35]) + rng.normal(0, 0.12)
            length = rng.uniform(8, 24) * sc
            val = rng.uniform(0.24, 0.92)
            p1 = (int(cx - math.cos(ang) * length * 0.35), int(cy - math.sin(ang) * length * 0.35))
            p2 = (int(cx + math.cos(ang) * length), int(cy + math.sin(ang) * length))
            _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.30:
                _cv2.line(CC, (p1[0] + 1, p1[1]), (p2[0] + 1, p2[1]), min(0.99, val + 0.07), 1, lineType=_cv2.LINE_AA)
        for _ in range(_count(shape, 80, 15)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            _cv2.circle(CC, (cx, cy), max(1, int(rng.uniform(2, 4) * sc)), rng.uniform(0.42, 0.96), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _clearcoat_lens_crater_archipelago(shape, seed, sm, name="clearcoat_lens_crater_archipelago"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85003)
    M, R, CC = _base(shape, int(seed), 0.08, 0.07, 0.31, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 760, 135)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(4, int(rng.uniform(6, 17) * sc)), max(3, int(rng.uniform(5, 14) * sc))
            rot = rng.uniform(0, 180)
            val = rng.uniform(0.34, 0.99)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, 0, 360, val, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (max(2, rx // 2), max(2, ry // 2)), rot + 13, 0, 360, val * 0.58, -1 if rng.random() < 0.28 else 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.46:
                _cv2.circle(CC, (cx + int(rx * 0.3), cy - int(ry * 0.25)), max(1, int(2.1 * sc)), min(0.99, val + 0.04), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _samhain_ember_mica_ash(shape, seed, sm, name="samhain_ember_mica_ash"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85004)
    M, R, CC = _base(shape, int(seed), 0.12, 0.12, 0.16, 0.055)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1250, 220)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            val = rng.uniform(0.28, 0.98)
            if rng.random() < 0.55:
                r = max(2, int(rng.uniform(3, 8) * sc))
                _cv2.circle(CC, (cx, cy), r, min(0.99, val + 0.05), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), max(1, r // 2), val * 0.18, -1, lineType=_cv2.LINE_AA)
            else:
                ang = rng.uniform(0, math.tau)
                length = rng.uniform(6, 18) * sc
                _cv2.line(M, (int(cx - math.cos(ang) * length * 0.3), int(cy - math.sin(ang) * length * 0.3)), (int(cx + math.cos(ang) * length), int(cy + math.sin(ang) * length)), val, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _hammered_flake_confetti_platelets(shape, seed, sm, name="hammered_flake_confetti_platelets"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85005)
    M, R, CC = _base(shape, int(seed), 0.13, 0.10, 0.25, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1300, 225)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(3, int(rng.uniform(4, 11) * sc))
            sides = int(rng.integers(4, 7))
            rot = rng.uniform(0, math.tau)
            pts = [(int(cx + math.cos(rot + k * math.tau / sides) * r * rng.uniform(0.65, 1.25)), int(cy + math.sin(rot + k * math.tau / sides) * r * rng.uniform(0.65, 1.25))) for k in range(sides)]
            poly = np.asarray(pts, dtype=np.int32)
            val = rng.uniform(0.28, 0.99)
            _cv2.fillPoly(M, [poly], val * 0.34, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.07), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.10:
                _draw_glint(M, R, CC, cx, cy, max(1, int(2.5 * sc)), (0.86, 0.10, 0.94))
    return _finish(name, M, R, CC, _safe_sm(sm))


def _hand_polished_microfiber_satin_mesh(shape, seed, sm, name="hand_polished_microfiber_satin_mesh"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85006)
    M, R, CC = _base(shape, int(seed), 0.12, 0.08, 0.23, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1550, 260)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ang = rng.choice([0.20, -0.55, 1.08, -1.18]) + rng.normal(0, 0.10)
            length = rng.uniform(7, 21) * sc
            val = rng.uniform(0.22, 0.88)
            p1 = (int(cx - math.cos(ang) * length * 0.5), int(cy - math.sin(ang) * length * 0.5))
            p2 = (int(cx + math.cos(ang) * length * 0.5), int(cy + math.sin(ang) * length * 0.5))
            _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.20:
                _cv2.line(CC, (p1[0] + 1, p1[1]), (p2[0] + 1, p2[1]), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _magnetic_filing_flower_storm(shape, seed, sm, name="magnetic_filing_flower_storm"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85007)
    M, R, CC = _base(shape, int(seed), 0.10, 0.08, 0.22, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 520, 95)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            arms = int(rng.integers(5, 9))
            val = rng.uniform(0.28, 0.95)
            for k in range(arms):
                ang = k * math.tau / arms + rng.uniform(-0.16, 0.16)
                length = rng.uniform(7, 20) * sc
                _cv2.line(M, (cx, cy), (int(cx + math.cos(ang) * length), int(cy + math.sin(ang) * length)), val * rng.uniform(0.56, 1.0), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.44:
                _cv2.circle(CC, (cx, cy), max(1, int(2.2 * sc)), min(0.99, val + 0.05), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _deep_space_microprism_nebula(shape, seed, sm, name="deep_space_microprism_nebula"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85008)
    M, R, CC = _base(shape, int(seed), 0.08, 0.06, 0.27, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1800, 300)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            val = rng.uniform(0.35, 0.99)
            _cv2.circle(CC, (x, y), max(1, int(rng.uniform(1, 3.0) * sc)), val, -1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.08:
                _draw_glint(M, R, CC, x, y, max(2, int(3.5 * sc)), (0.88, 0.10, 0.96))
        for _ in range(_count(shape, 95, 18)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(10, int(rng.uniform(14, 38) * sc)), max(4, int(rng.uniform(5, 16) * sc))
            _cv2.ellipse(M, (cx, cy), (rx, ry), rng.uniform(0, 180), rng.uniform(0, 180), rng.uniform(180, 360), rng.uniform(0.18, 0.52), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _holographic_shatter_leaf_rain(shape, seed, sm, name="holographic_shatter_leaf_rain"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85009)
    M, R, CC = _base(shape, int(seed), 0.15, 0.07, 0.30, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1100, 190)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            length = rng.uniform(8, 28) * sc
            width = rng.uniform(3, 9) * sc
            rot = rng.uniform(0, math.tau)
            pts = [(int(cx + math.cos(rot) * length), int(cy + math.sin(rot) * length)),
                   (int(cx + math.cos(rot + 1.9) * width), int(cy + math.sin(rot + 1.9) * width)),
                   (int(cx - math.cos(rot) * length * 0.60), int(cy - math.sin(rot) * length * 0.60)),
                   (int(cx + math.cos(rot - 1.9) * width), int(cy + math.sin(rot - 1.9) * width))]
            poly = np.asarray(pts, dtype=np.int32)
            val = rng.uniform(0.30, 0.99)
            _cv2.fillPoly(M, [poly], val * 0.28, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _comet_orbit_scratch_celestial_map(shape, seed, sm, name="comet_orbit_scratch_celestial_map"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85010)
    M, R, CC = _base(shape, int(seed), 0.09, 0.06, 0.24, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 640, 112)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(7, int(rng.uniform(10, 32) * sc)), max(3, int(rng.uniform(4, 13) * sc))
            rot = rng.uniform(0, 180)
            start = rng.uniform(0, 300)
            val = rng.uniform(0.26, 0.92)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, start, start + rng.uniform(75, 190), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, start + 10, start + rng.uniform(50, 150), val * 0.70, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.25:
                _draw_glint(M, R, CC, cx, cy, max(1, int(2.8 * sc)), (0.84, 0.10, 0.96))
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_abstract_retro_wave(shape, seed, sm, **kwargs): return _optical_vinyl_groove_constellations(shape, seed + 3101, sm)
def rescue_brushstroke_bold(shape, seed, sm, **kwargs): return _lacquer_katana_scratch_garden(shape, seed + 3102, sm)
def rescue_cc_fish_eye(shape, seed, sm, **kwargs): return _clearcoat_lens_crater_archipelago(shape, seed + 3103, sm)
def rescue_cloud_wisps_warm(shape, seed, sm, **kwargs): return _samhain_ember_mica_ash(shape, seed + 3104, sm)
def rescue_flake_scatter(shape, seed, sm, **kwargs): return _hammered_flake_confetti_platelets(shape, seed + 3105, sm)
def rescue_hand_polished(shape, seed, sm, **kwargs): return _hand_polished_microfiber_satin_mesh(shape, seed + 3106, sm)
def rescue_magnetic_field(shape, seed, sm, **kwargs): return _magnetic_filing_flower_storm(shape, seed + 3107, sm)
def rescue_micro_sparkle(shape, seed, sm, **kwargs): return _deep_space_microprism_nebula(shape, seed + 3108, sm)
def rescue_spec_holographic_foil(shape, seed, sm, **kwargs): return _holographic_shatter_leaf_rain(shape, seed + 3109, sm)
def rescue_sparkle_comet(shape, seed, sm, **kwargs): return _comet_orbit_scratch_celestial_map(shape, seed + 3110, sm)


# SPB-RATE10 / 2026-05-27-wwrd-pass11-iteration2:
# Contact sheet rejected the sparse-dust read. Increase visible surface language per finish.
def _retro_optical_disc_pinwheel_field(shape, seed, sm, name="retro_optical_disc_pinwheel_field"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85101)
    M, R, CC = _base(shape, int(seed), 0.10, 0.07, 0.26, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(30, int(70 * sc)), max(28, int(62 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off + int(rng.uniform(-8, 8) * sc), y + int(rng.uniform(-8, 8) * sc)
                val = rng.uniform(0.30, 0.99)
                rot = rng.uniform(0, 180)
                for k in range(5):
                    r = max(5, int((7 + k * 3.7) * sc))
                    _cv2.ellipse(CC, (cx, cy), (r, r), rot, 20 + k * 8, 280 - k * 5, min(0.99, val + 0.05), 1, lineType=_cv2.LINE_AA)
                    if k % 2 == 0:
                        _cv2.ellipse(M, (cx, cy), (r, r), rot, 35 + k * 8, 205, val * 0.70, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _red_lacquer_crosscut_scratch_mesh(shape, seed, sm, name="red_lacquer_crosscut_scratch_mesh"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85102)
    M, R, CC = _base(shape, int(seed), 0.11, 0.08, 0.22, 0.048)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 2200, 360)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ang = rng.choice([-1.15, -0.55, 0.25, 0.85, 1.35]) + rng.normal(0, 0.10)
            length = rng.uniform(6, 19) * sc
            val = rng.uniform(0.22, 0.92)
            p1 = (int(cx - math.cos(ang) * length * 0.5), int(cy - math.sin(ang) * length * 0.5))
            p2 = (int(cx + math.cos(ang) * length * 0.5), int(cy + math.sin(ang) * length * 0.5))
            _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.20:
                _cv2.line(CC, (p1[0] + 1, p1[1]), (p2[0] + 1, p2[1]), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _fisheye_bubble_cellular_surface(shape, seed, sm, name="fisheye_bubble_cellular_surface"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85103)
    M, R, CC = _base(shape, int(seed), 0.08, 0.07, 0.31, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        sx, sy = max(20, int(46 * sc)), max(20, int(46 * sc))
        for row, y in enumerate(range(-sy, h + sy, sy)):
            off = sx // 2 if row % 2 else 0
            for x in range(-sx, w + sx, sx):
                cx, cy = x + off + int(rng.uniform(-5, 5) * sc), y + int(rng.uniform(-5, 5) * sc)
                rx, ry = max(4, int(rng.uniform(6, 15) * sc)), max(4, int(rng.uniform(6, 15) * sc))
                val = rng.uniform(0.34, 0.99)
                _cv2.ellipse(CC, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, 360, val, 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.42:
                    _cv2.ellipse(M, (cx, cy), (max(2, rx // 2), max(2, ry // 2)), rng.uniform(0, 180), 0, 360, val * 0.58, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), max(1, int(2 * sc)), val * 0.14, -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _ember_glass_cinder_platelets(shape, seed, sm, name="ember_glass_cinder_platelets"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85104)
    M, R, CC = _base(shape, int(seed), 0.13, 0.12, 0.16, 0.055)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1500, 250)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(2, int(rng.uniform(3, 9) * sc))
            sides = int(rng.integers(3, 6))
            rot = rng.uniform(0, math.tau)
            pts = [(int(cx + math.cos(rot + k * math.tau / sides) * r * rng.uniform(0.7, 1.2)), int(cy + math.sin(rot + k * math.tau / sides) * r * rng.uniform(0.7, 1.2))) for k in range(sides)]
            poly = np.asarray(pts, dtype=np.int32)
            val = rng.uniform(0.30, 0.98)
            _cv2.fillPoly(M, [poly], val * 0.34, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _dense_hammered_metalflake_platelets(shape, seed, sm, name="dense_hammered_metalflake_platelets"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85105)
    M, R, CC = _base(shape, int(seed), 0.13, 0.10, 0.25, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1900, 315)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(3, int(rng.uniform(4, 10) * sc))
            sides = int(rng.integers(4, 7))
            rot = rng.uniform(0, math.tau)
            pts = [(int(cx + math.cos(rot + k * math.tau / sides) * r * rng.uniform(0.65, 1.25)), int(cy + math.sin(rot + k * math.tau / sides) * r * rng.uniform(0.65, 1.25))) for k in range(sides)]
            poly = np.asarray(pts, dtype=np.int32)
            val = rng.uniform(0.26, 0.99)
            _cv2.fillPoly(M, [poly], val * 0.36, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.07), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _satin_polish_crosshatch_dense(shape, seed, sm, name="satin_polish_crosshatch_dense"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85106)
    M, R, CC = _base(shape, int(seed), 0.12, 0.08, 0.23, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 2300, 380)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            ang = rng.choice([0.0, math.pi / 2, 0.45, -0.75]) + rng.normal(0, 0.10)
            length = rng.uniform(6, 20) * sc
            val = rng.uniform(0.22, 0.88)
            p1 = (int(cx - math.cos(ang) * length * 0.5), int(cy - math.sin(ang) * length * 0.5))
            p2 = (int(cx + math.cos(ang) * length * 0.5), int(cy + math.sin(ang) * length * 0.5))
            _cv2.line(M, p1, p2, val, 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.16:
                _cv2.line(CC, (p1[0] + 1, p1[1]), (p2[0] + 1, p2[1]), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _ferrofluid_starburst_microfield(shape, seed, sm, name="ferrofluid_starburst_microfield"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85107)
    M, R, CC = _base(shape, int(seed), 0.10, 0.08, 0.22, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 840, 145)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            arms = int(rng.integers(4, 8))
            val = rng.uniform(0.28, 0.95)
            for k in range(arms):
                ang = k * math.tau / arms + rng.uniform(-0.14, 0.14)
                length = rng.uniform(6, 17) * sc
                _cv2.line(M, (cx, cy), (int(cx + math.cos(ang) * length), int(cy + math.sin(ang) * length)), val * rng.uniform(0.56, 1.0), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.36:
                _cv2.circle(CC, (cx, cy), max(1, int(2.0 * sc)), min(0.99, val + 0.05), -1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _milky_way_microprism_dense(shape, seed, sm, name="milky_way_microprism_dense"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85108)
    M, R, CC = _base(shape, int(seed), 0.08, 0.06, 0.27, 0.04)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 2300, 380)):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            val = rng.uniform(0.35, 0.99)
            _cv2.circle(CC, (x, y), max(1, int(rng.uniform(1, 2.6) * sc)), val, -1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.07:
                _draw_glint(M, R, CC, x, y, max(2, int(3.2 * sc)), (0.88, 0.10, 0.96))
        for _ in range(_count(shape, 170, 28)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(8, int(rng.uniform(10, 30) * sc)), max(3, int(rng.uniform(4, 12) * sc))
            _cv2.ellipse(M, (cx, cy), (rx, ry), rng.uniform(0, 180), 0, rng.uniform(120, 280), rng.uniform(0.18, 0.55), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _holo_prism_leafstorm_dense(shape, seed, sm, name="holo_prism_leafstorm_dense"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85109)
    M, R, CC = _base(shape, int(seed), 0.15, 0.07, 0.30, 0.035)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 1600, 270)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            length = rng.uniform(7, 22) * sc
            width = rng.uniform(3, 8) * sc
            rot = rng.uniform(0, math.tau)
            pts = [(int(cx + math.cos(rot) * length), int(cy + math.sin(rot) * length)),
                   (int(cx + math.cos(rot + 1.9) * width), int(cy + math.sin(rot + 1.9) * width)),
                   (int(cx - math.cos(rot) * length * 0.60), int(cy - math.sin(rot) * length * 0.60)),
                   (int(cx + math.cos(rot - 1.9) * width), int(cy + math.sin(rot - 1.9) * width))]
            poly = np.asarray(pts, dtype=np.int32)
            val = rng.uniform(0.30, 0.99)
            _cv2.fillPoly(M, [poly], val * 0.28, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [poly], True, min(0.99, val + 0.08), 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def _comet_orbit_scratch_map_dense(shape, seed, sm, name="comet_orbit_scratch_map_dense"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 85110)
    M, R, CC = _base(shape, int(seed), 0.09, 0.06, 0.24, 0.045)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(_count(shape, 860, 148)):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            rx, ry = max(6, int(rng.uniform(9, 28) * sc)), max(3, int(rng.uniform(4, 11) * sc))
            rot = rng.uniform(0, 180)
            start = rng.uniform(0, 300)
            val = rng.uniform(0.26, 0.92)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), rot, start, start + rng.uniform(80, 200), min(0.99, val + 0.06), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (cx, cy), (rx, ry), rot, start + 8, start + rng.uniform(50, 155), val * 0.70, 1, lineType=_cv2.LINE_AA)
    return _finish(name, M, R, CC, _safe_sm(sm))


def rescue_abstract_retro_wave(shape, seed, sm, **kwargs): return _retro_optical_disc_pinwheel_field(shape, seed + 3201, sm)
def rescue_brushstroke_bold(shape, seed, sm, **kwargs): return _red_lacquer_crosscut_scratch_mesh(shape, seed + 3202, sm)
def rescue_cc_fish_eye(shape, seed, sm, **kwargs): return _fisheye_bubble_cellular_surface(shape, seed + 3203, sm)
def rescue_cloud_wisps_warm(shape, seed, sm, **kwargs): return _ember_glass_cinder_platelets(shape, seed + 3204, sm)
def rescue_flake_scatter(shape, seed, sm, **kwargs): return _dense_hammered_metalflake_platelets(shape, seed + 3205, sm)
def rescue_hand_polished(shape, seed, sm, **kwargs): return _satin_polish_crosshatch_dense(shape, seed + 3206, sm)
def rescue_magnetic_field(shape, seed, sm, **kwargs): return _ferrofluid_starburst_microfield(shape, seed + 3207, sm)
def rescue_micro_sparkle(shape, seed, sm, **kwargs): return _milky_way_microprism_dense(shape, seed + 3208, sm)
def rescue_spec_holographic_foil(shape, seed, sm, **kwargs): return _holo_prism_leafstorm_dense(shape, seed + 3209, sm)
def rescue_sparkle_comet(shape, seed, sm, **kwargs): return _comet_orbit_scratch_map_dense(shape, seed + 3210, sm)
