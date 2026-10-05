"""SPB_RATE_10 Codex heartbeat loop 4 spec-overlay rebuilds."""
from __future__ import annotations

import math

import numpy as np

from ..spec_patterns import _CV2_OK, _cv2, _flat, _normalize, multi_scale_noise
from .rate10_codex_batch import _dot_noise, _finish, _line_distance, _scale, _star
from .rate10_codex_loop2 import _base, _machined, _occult, _pins, _prism, _track
from .rate10_codex_loop3 import _carbon, _predator, _surface


def _fracture(shape, seed, name, palette="cold"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 41000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.20, 0.14, 0.28, 0.12)
    if _CV2_OK:
        for _ in range(int(np.clip(1200 * (h * w / (2048 * 2048)), 260, 1200))):
            x = int(rng.integers(0, w)); y = int(rng.integers(0, h))
            tier = float(rng.uniform(0.36, 0.96))
            for _seg in range(int(rng.integers(2, 6))):
                length = float(rng.uniform(7, 20) * sc)
                ang = float(rng.choice([0, math.pi / 4, -math.pi / 4, math.pi / 2]) + rng.normal(0, 0.23))
                x2 = int(np.clip(x + math.cos(ang) * length, 0, w - 1))
                y2 = int(np.clip(y + math.sin(ang) * length, 0, h - 1))
                _cv2.line(M, (x, y), (x2, y2), tier, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x, y), (x2, y2), tier * (0.18 if palette == "cold" else 0.42), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x, y), (x2, y2), min(0.98, tier + 0.04), 1, lineType=_cv2.LINE_AA)
                x, y = x2, y2
    _pins(M, R, CC, rng, 2600, "mixed")
    return _finish(name, M, R, CC, 1.0)


def _industrial(shape, seed, name, mode="rivet"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 42000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.25, 0.27, 0.25, 0.08)
    if _CV2_OK:
        if mode == "rivet":
            step = max(10, int(42 * sc)); rad = max(2, int(5 * sc))
            for y in range(step // 2, h, step):
                for x in range(step // 2, w, step):
                    tier = float(rng.uniform(0.48, 0.96))
                    _cv2.circle(M, (x, y), rad + 1, tier, 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(R, (x, y), rad, tier * 0.72, -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (x, y), rad + 1, min(0.98, tier + 0.04), 1, lineType=_cv2.LINE_AA)
        elif mode == "weld":
            for row in range(24):
                y = int((row + 0.5) * h / 24 + rng.uniform(-3, 3) * sc)
                for x in range(0, w, max(5, int(13 * sc))):
                    rr = max(2, int(rng.uniform(3, 6) * sc))
                    tier = float(rng.uniform(0.36, 0.88))
                    _cv2.ellipse(M, (x, y), (rr, max(1, rr // 2)), 0, 0, 360, tier, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(R, (x, y), (rr, max(1, rr // 2)), 0, 0, 360, tier * 0.70, 1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(CC, (x, y), (rr, max(1, rr // 2)), 0, 0, 360, min(0.96, tier + 0.06), 1, lineType=_cv2.LINE_AA)
        else:
            for _ in range(int(np.clip(1800 * (h * w / (2048 * 2048)), 320, 1800))):
                cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
                rr = max(1, int(rng.uniform(1.4, 4.0) * sc))
                _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.15, 0.86)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), rr, float(rng.uniform(0.12, 0.58)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.10, 0.80)), -1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2600, "mixed")
    return _finish(name, M, R, CC, 1.0)


def _sponsor(shape, seed, name, mode="tape"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 43000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.22, 0.16, 0.26, 0.10)
    if _CV2_OK:
        for _ in range(int(np.clip(2400 * (h * w / (2048 * 2048)), 420, 2400))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rw = max(4, int(rng.uniform(8, 20) * sc)); rh = max(2, int(rng.uniform(3, 8) * sc))
            ang = float(rng.uniform(-35, 35))
            box = _cv2.boxPoints(((cx, cy), (rw, rh), ang)).astype(np.int32)
            tier = float(rng.uniform(0.34, 0.94))
            if mode == "deboss":
                _cv2.polylines(M, [box], True, tier, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [box], True, tier * 0.44, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [box], True, min(0.98, tier + 0.04), 1, lineType=_cv2.LINE_AA)
            else:
                _cv2.fillPoly(M, [box], tier * 0.72, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [box], tier * 0.42, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [box], min(0.92, tier + 0.02), lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 4200, 0.03)
    return _finish(name, M, R, CC, 1.0)


def codex_spec_light_leak(shape, seed, sm, **kwargs): return _prism(shape, seed + 1, "spec_light_leak", 8.0)
def codex_spec_liquid_metal(shape, seed, sm, **kwargs): return _machined(shape, seed + 2, "spec_liquid_metal", "lathe")
def codex_spec_magnetic_ferrofluid(shape, seed, sm, **kwargs): return _occult(shape, seed + 3, "spec_magnetic_ferrofluid", "violet", 180, 3000)
def codex_spec_oxidized_pitting(shape, seed, sm, **kwargs): return _industrial(shape, seed + 4, "spec_oxidized_pitting", "pitting")
def codex_spec_patina_verdigris(shape, seed, sm, **kwargs): return _occult(shape, seed + 5, "spec_patina_verdigris", "gold", 160, 2600)
def codex_spec_peeling_clear(shape, seed, sm, **kwargs): return _fracture(shape, seed + 6, "spec_peeling_clear", "cold")
def codex_spec_powder_coat_texture(shape, seed, sm, **kwargs): return _surface(shape, seed + 7, "spec_powder_coat_texture", "cast")
def codex_spec_riveted_plate(shape, seed, sm, **kwargs): return _industrial(shape, seed + 8, "spec_riveted_plate", "rivet")
def codex_spec_rust_bloom(shape, seed, sm, **kwargs): return _occult(shape, seed + 9, "spec_rust_bloom", "blood", 140, 2700)
def codex_spec_shot_peened(shape, seed, sm, **kwargs): return _industrial(shape, seed + 10, "spec_shot_peened", "pitting")
def codex_spec_snake_scales(shape, seed, sm, **kwargs): return _predator(shape, seed + 11, "spec_snake_scales", "denticle")
def codex_spec_sparkle_flake(shape, seed, sm, **kwargs): return _prism(shape, seed + 12, "spec_sparkle_flake", 5.0)
def codex_spec_stone_granite(shape, seed, sm, **kwargs): return _surface(shape, seed + 13, "spec_stone_granite", "cast")
def codex_spec_stress_fractures(shape, seed, sm, **kwargs): return _fracture(shape, seed + 14, "spec_stress_fractures", "cold")
def codex_spec_subsurface_depth(shape, seed, sm, **kwargs): return _occult(shape, seed + 15, "spec_subsurface_depth", "frost", 100, 3200)
def codex_spec_terrain_erosion(shape, seed, sm, **kwargs): return _fracture(shape, seed + 16, "spec_terrain_erosion", "earth")
def codex_spec_thermal_spray(shape, seed, sm, **kwargs): return _industrial(shape, seed + 17, "spec_thermal_spray", "pitting")
def codex_spec_weld_seam(shape, seed, sm, **kwargs): return _industrial(shape, seed + 18, "spec_weld_seam", "weld")
def codex_spec_worn_edges(shape, seed, sm, **kwargs): return _fracture(shape, seed + 19, "spec_worn_edges", "earth")
def codex_spiral_sweep(shape, seed, sm, **kwargs): return _machined(shape, seed + 20, "spiral_sweep", "lathe")
def codex_split_bands(shape, seed, sm, **kwargs): return _prism(shape, seed + 21, "split_bands", 7.0)
def codex_sponsor_deboss(shape, seed, sm, **kwargs): return _sponsor(shape, seed + 22, "sponsor_deboss", "deboss")
def codex_sponsor_emboss_v2(shape, seed, sm, **kwargs): return _sponsor(shape, seed + 23, "sponsor_emboss_v2", "emboss")
def codex_sponsor_tape_vinyl(shape, seed, sm, **kwargs): return _sponsor(shape, seed + 24, "sponsor_tape_vinyl", "tape")
def codex_spray_paint_drip(shape, seed, sm, **kwargs): return _fracture(shape, seed + 25, "spray_paint_drip", "earth")
