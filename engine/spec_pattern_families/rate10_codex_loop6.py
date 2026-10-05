"""SPB_RATE_10 Codex heartbeat loop 6 hidden-pending rebuilds.

SPB-105 / SPB-RATE10 / 2026-05-27-codex-loop6: owner-rated REBUILD/MIXED
patterns were still hidden pending a post-rating rebuild. These renderers favor
8-32 px marks, dense but named finish language, and multiple spec shades per
feature instead of generic noise.
"""
from __future__ import annotations

import math

import numpy as np

from ..spec_patterns import _CV2_OK, _cv2, _flat, _normalize, multi_scale_noise
from .rate10_codex_batch import _dot_noise, _finish, _line_distance, _scale, _star
from .rate10_codex_loop2 import _base, _machined, _occult, _pins, _prism, _track
from .rate10_codex_loop3 import _carbon, _predator, _surface
from .rate10_codex_loop4 import _fracture, _industrial, _sponsor
from .rate10_codex_loop5 import _stipple, _wet_gloss


def _fine_flake(shape, seed, name, mode="silver"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 61000 + len(name))
    sc = _scale(shape)
    if mode == "holo":
        M, R, CC = _prism(shape, seed, name, 5.0).transpose(2, 0, 1)
        M, R, CC = M.copy(), R.copy(), CC.copy()
    else:
        M, R, CC = _base(shape, int(seed), 0.22, 0.18, 0.29, 0.12)
    if _CV2_OK:
        count = int(np.clip(3600 * (h * w / (2048 * 2048)), 520, 3600))
        for _ in range(count):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(1.4, 4.2) * sc))
            sides = int(rng.integers(3, 6))
            pts = _star(cx, cy, rr, max(1, rr // 2), sides, rng.uniform(0, math.pi))
            tier = float(rng.choice([0.28, 0.40, 0.52, 0.64, 0.78, 0.92]))
            _cv2.fillPoly(M, [pts], tier, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [pts], tier * (0.72 if mode == "silver" else rng.uniform(0.16, 0.62)), lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts], min(0.98, tier + rng.uniform(-0.05, 0.09)), lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2400, "glass" if mode == "holo" else "mixed")
    return _finish(name, M, R, CC, 1.0)


def _scuffed_clear(shape, seed, name, mode="scuff"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 62000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.18, 0.16, 0.30, 0.10)
    if _CV2_OK:
        count = int(np.clip(2400 * (h * w / (2048 * 2048)), 420, 2400))
        for _ in range(count):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            ln = float(rng.uniform(8, 28) * sc)
            ang = float(rng.choice([0, math.pi / 5, -math.pi / 5, math.pi / 2]) + rng.normal(0, 0.18))
            x2 = int(np.clip(cx + math.cos(ang) * ln, 0, w - 1))
            y2 = int(np.clip(cy + math.sin(ang) * ln, 0, h - 1))
            tier = float(rng.uniform(0.22, 0.90))
            rv = tier * (0.22 if mode != "dust" else 0.52)
            cv = min(0.98, tier + 0.07) if mode in {"gloss", "fish"} else tier * rng.uniform(0.36, 0.82)
            _cv2.line(M, (cx, cy), (x2, y2), tier * 0.72, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy), (x2, y2), rv, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (x2, y2), cv, 1, lineType=_cv2.LINE_AA)
        if mode == "fish":
            for _ in range(int(np.clip(520 * (h * w / (2048 * 2048)), 110, 520))):
                cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
                rr = max(2, int(rng.uniform(3, 9) * sc))
                _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.18, 0.62)), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), rr, float(rng.uniform(0.04, 0.20)), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.62, 0.98)), 1, lineType=_cv2.LINE_AA)
        elif mode == "gloss":
            for y in range(0, h, max(14, int(48 * sc))):
                _cv2.line(CC, (0, y), (w - 1, int(np.clip(y + 8 * sc, 0, h - 1))), 0.94, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (0, y), (w - 1, int(np.clip(y + 8 * sc, 0, h - 1))), 0.56, 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 3200, 0.026)
    return _finish(name, M, R, CC, 1.0)


def _tech_network(shape, seed, name, mode="circuit"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 63000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.17, 0.13, 0.27, 0.11)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    if mode == "magnetic":
        field = _line_distance(xx * 0.42 + np.sin(yy / max(1.0, 26 * sc)) * 24 * sc, 17 * sc, 0.78 * sc, seed)
        M = np.clip(M + field * 0.30, 0, 1); R = np.clip(R + field * 0.08, 0, 1); CC = np.clip(CC + field * 0.34, 0, 1)
    elif mode == "neural":
        dend = _line_distance(xx * 0.36 - yy * 0.54, 15 * sc, 0.70 * sc, seed)
        M = np.clip(M + dend * 0.26, 0, 1); CC = np.clip(CC + dend * 0.30, 0, 1)
    if _CV2_OK:
        count = int(np.clip(1600 * (h * w / (2048 * 2048)), 300, 1600))
        dirs = [0, math.pi / 2, math.pi / 4, -math.pi / 4] if mode == "circuit" else [rng.uniform(0, math.pi) for _ in range(12)]
        for _ in range(count):
            x = int(rng.integers(0, w)); y = int(rng.integers(0, h))
            tier = float(rng.choice([0.24, 0.36, 0.48, 0.62, 0.78, 0.94]))
            for _seg in range(int(rng.integers(1, 4))):
                ang = float(rng.choice(dirs) + rng.normal(0, 0.08 if mode == "circuit" else 0.22))
                ln = float(rng.uniform(7, 23) * sc)
                x2 = int(np.clip(x + math.cos(ang) * ln, 0, w - 1))
                y2 = int(np.clip(y + math.sin(ang) * ln, 0, h - 1))
                _cv2.line(M, (x, y), (x2, y2), tier, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x, y), (x2, y2), tier * (0.18 if mode != "magnetic" else 0.42), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x, y), (x2, y2), min(0.98, tier + 0.04), 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.22:
                    _cv2.circle(CC, (x2, y2), max(1, int(2.6 * sc)), min(0.98, tier + 0.08), 1, lineType=_cv2.LINE_AA)
                x, y = x2, y2
    _pins(M, R, CC, rng, 2600, "mixed")
    return _finish(name, M, R, CC, 1.0)


def _diamond_micro(shape, seed, name, mode="lattice"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 64000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.21, 0.20, 0.31, 0.08)
    if _CV2_OK:
        step = max(8, int(25 * sc))
        for y in range(-step, h + step, step):
            for x in range(-step, w + step, step):
                pts = np.array([[x, y - step // 2], [x + step // 2, y], [x, y + step // 2], [x - step // 2, y]], dtype=np.int32)
                tier = float(rng.choice([0.28, 0.40, 0.54, 0.68, 0.82, 0.96]))
                if mode == "facet" and rng.random() < 0.55:
                    _cv2.fillPoly(M, [pts], tier * 0.52, lineType=_cv2.LINE_AA)
                    _cv2.fillPoly(CC, [pts], min(0.92, tier * 0.74), lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [pts], True, min(0.98, tier + 0.04), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [pts], True, tier * 0.58, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, min(0.98, tier + 0.10), 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 3200, 0.026)
    return _finish(name, M, R, CC, 1.0)


def _wood_or_pearl(shape, seed, name, mode="wood"):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(int(seed) + 65000 + len(name))
    sc = _scale(shape)
    if mode == "wood":
        M, R, CC = _base(shape, int(seed), 0.25, 0.20, 0.20, 0.11)
        warp = _normalize(multi_scale_noise(shape, [4, 9, 21], [0.45, 0.34, 0.21], int(seed) + 7))
        grain = _line_distance(xx * 0.54 + (warp - 0.5) * 34 * sc, 11 * sc, 0.72 * sc, seed)
        rings = _line_distance(xx * 0.22 + yy * 0.08 + (warp - 0.5) * 22 * sc, 21 * sc, 0.62 * sc, seed * 0.4)
        M = np.clip(M + grain * 0.30 + rings * 0.10, 0, 1)
        R = np.clip(R + grain * 0.16 + rings * 0.06, 0, 1)
        CC = np.clip(CC + grain * 0.12 + rings * 0.08, 0, 1)
    else:
        M, R, CC = _prism(shape, seed, name, 7.0).transpose(2, 0, 1)
        M, R, CC = M.copy(), R.copy(), CC.copy()
        if _CV2_OK:
            for _ in range(int(np.clip(780 * (h * w / (2048 * 2048)), 160, 780))):
                cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
                rr = max(3, int(rng.uniform(4, 11) * sc))
                _cv2.ellipse(M, (cx, cy), (rr * 2, rr), rng.uniform(0, 180), 0, 360, float(rng.uniform(0.26, 0.78)), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (rr * 2, rr), rng.uniform(0, 180), 0, 360, float(rng.uniform(0.56, 0.98)), 1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2400, "mixed")
    return _finish(name, M, R, CC, 1.0)


def _comet_field(shape, seed, name):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 66000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.16, 0.11, 0.30, 0.11)
    if _CV2_OK:
        for _ in range(int(np.clip(1700 * (h * w / (2048 * 2048)), 300, 1700))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            ln = float(rng.uniform(6, 20) * sc)
            ang = float(rng.uniform(-0.65, 0.35))
            x2 = int(np.clip(cx - math.cos(ang) * ln, 0, w - 1))
            y2 = int(np.clip(cy - math.sin(ang) * ln, 0, h - 1))
            tier = float(rng.choice([0.32, 0.44, 0.58, 0.72, 0.86, 0.98]))
            _cv2.line(M, (cx, cy), (x2, y2), tier * 0.62, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy), (x2, y2), tier * 0.18, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (x2, y2), min(0.98, tier + 0.02), 1, lineType=_cv2.LINE_AA)
            if rng.random() < 0.55:
                _cv2.circle(M, (cx, cy), max(1, int(2.2 * sc)), tier, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), max(1, int(2.2 * sc)), min(0.98, tier + 0.04), -1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 3200, "glass")
    return _finish(name, M, R, CC, 1.0)


def _oil_film_dense(shape, seed, name):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(int(seed) + 67000 + len(name))
    sc = _scale(shape)
    warp = _normalize(multi_scale_noise(shape, [5, 12, 27], [0.44, 0.34, 0.22], int(seed) + 31))
    phase_a = (xx * 0.44 + yy * 0.18 + (warp - 0.5) * 18 * sc) * (2 * math.pi / max(1.0, 8.0 * sc))
    phase_b = (xx * -0.16 + yy * 0.58 + (warp - 0.5) * 12 * sc) * (2 * math.pi / max(1.0, 13.0 * sc))
    M = np.clip(0.20 + (np.sin(phase_a) + 1) * 0.17 + (np.sin(phase_b) + 1) * 0.08, 0, 1).astype(np.float32)
    R = np.clip(0.10 + (np.sin(phase_a + 2.2) + 1) * 0.08 + (np.sin(phase_b + 1.0) + 1) * 0.04, 0, 1).astype(np.float32)
    CC = np.clip(0.28 + (np.sin(phase_a + 4.1) + 1) * 0.21 + (np.sin(phase_b + 3.0) + 1) * 0.07, 0, 1).astype(np.float32)
    if _CV2_OK:
        for _ in range(int(np.clip(520 * (h * w / (2048 * 2048)), 110, 520))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(3, int(rng.uniform(4, 12) * sc))
            _cv2.ellipse(M, (cx, cy), (rr * 2, rr), rng.uniform(0, 180), 0, 360, float(rng.uniform(0.32, 0.84)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rr * 2, rr), rng.uniform(0, 180), 0, 360, float(rng.uniform(0.54, 0.98)), 1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2200, "glass")
    return _finish(name, M, R, CC, 1.0)


def _ember_wisps(shape, seed, name):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 68000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.23, 0.10, 0.20, 0.12)
    if _CV2_OK:
        for _ in range(int(np.clip(2600 * (h * w / (2048 * 2048)), 440, 2600))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            ln = float(rng.uniform(8, 24) * sc)
            ang = float(rng.uniform(-0.25, 0.55) + rng.normal(0, 0.18))
            x2 = int(np.clip(cx + math.cos(ang) * ln, 0, w - 1))
            y2 = int(np.clip(cy + math.sin(ang) * ln, 0, h - 1))
            tier = float(rng.uniform(0.24, 0.88))
            _cv2.line(M, (cx, cy), (x2, y2), tier * 0.76, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy), (x2, y2), tier * 0.18, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (x2, y2), tier * 0.60, 1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2600, "hot")
    return _finish(name, M, R, CC, 1.0)


def codex_flake_scatter_loop6(shape, seed, sm, **kwargs): return _fine_flake(shape, seed + 1, "flake_scatter", "silver")
def codex_wear_scuff_loop6(shape, seed, sm, **kwargs): return _scuffed_clear(shape, seed + 2, "wear_scuff", "scuff")
def codex_crackle_network_loop6(shape, seed, sm, **kwargs): return _fracture(shape, seed + 3, "crackle_network", "cold")
def codex_diamond_lattice_loop6(shape, seed, sm, **kwargs): return _diamond_micro(shape, seed + 4, "diamond_lattice", "lattice")
def codex_magnetic_field_loop6(shape, seed, sm, **kwargs): return _tech_network(shape, seed + 5, "magnetic_field", "magnetic")
def codex_neural_dendrite_loop6(shape, seed, sm, **kwargs): return _tech_network(shape, seed + 6, "neural_dendrite", "neural")
def codex_circuit_trace_loop6(shape, seed, sm, **kwargs): return _tech_network(shape, seed + 7, "circuit_trace", "circuit")
def codex_crystal_growth_loop6(shape, seed, sm, **kwargs): return _predator(shape, seed + 8, "crystal_growth", "crystal")
def codex_brushed_sparkle_loop6(shape, seed, sm, **kwargs): return _fine_flake(shape, seed + 9, "brushed_sparkle", "holo")
def codex_sparkle_comet_loop6(shape, seed, sm, **kwargs): return _comet_field(shape, seed + 10, "sparkle_comet")
def codex_brushed_cross_loop6(shape, seed, sm, **kwargs): return _machined(shape, seed + 11, "brushed_cross", "knurl")
def codex_hairline_polish_loop6(shape, seed, sm, **kwargs): return _machined(shape, seed + 12, "hairline_polish", "straight")
def codex_buffer_swirl_loop6(shape, seed, sm, **kwargs): return _machined(shape, seed + 13, "buffer_swirl", "lathe")
def codex_hand_polished_loop6(shape, seed, sm, **kwargs): return _machined(shape, seed + 14, "hand_polished", "straight")
def codex_cc_fish_eye_loop6(shape, seed, sm, **kwargs): return _scuffed_clear(shape, seed + 15, "cc_fish_eye", "fish")
def codex_cc_gloss_stripe_loop6(shape, seed, sm, **kwargs): return _scuffed_clear(shape, seed + 16, "cc_gloss_stripe", "gloss")
def codex_spec_faceted_diamond_loop6(shape, seed, sm, **kwargs): return _diamond_micro(shape, seed + 17, "spec_faceted_diamond", "facet")
def codex_spec_wood_grain_fine_loop6(shape, seed, sm, **kwargs): return _wood_or_pearl(shape, seed + 18, "spec_wood_grain_fine", "wood")
def codex_spec_holographic_foil_loop6(shape, seed, sm, **kwargs): return _fine_flake(shape, seed + 19, "spec_holographic_foil", "holo")
def codex_spec_oil_film_thick_loop6(shape, seed, sm, **kwargs): return _oil_film_dense(shape, seed + 20, "spec_oil_film_thick")
def codex_paint_drip_edge_loop6(shape, seed, sm, **kwargs): return _fracture(shape, seed + 21, "paint_drip_edge", "earth")
def codex_decal_lift_edge_loop6(shape, seed, sm, **kwargs): return _sponsor(shape, seed + 22, "decal_lift_edge", "deboss")
def codex_brake_dust_buildup_loop6(shape, seed, sm, **kwargs): return _stipple(shape, seed + 23, "brake_dust_buildup", "rust")
def codex_mother_of_pearl_inlay_loop6(shape, seed, sm, **kwargs): return _wood_or_pearl(shape, seed + 24, "mother_of_pearl_inlay", "pearl")
def codex_cloud_wisps_warm_loop6(shape, seed, sm, **kwargs): return _ember_wisps(shape, seed + 25, "cloud_wisps_warm")
def codex_cloud_wisps_cool_loop6(shape, seed, sm, **kwargs): return _occult(shape, seed + 26, "cloud_wisps_cool", "frost", 120, 3400)
