"""SPB_RATE_10 Codex heartbeat loop 2 spec-overlay rebuilds."""
from __future__ import annotations

import math

import numpy as np

from ..spec_patterns import (
    _CV2_OK,
    _cv2,
    _flat,
    _normalize,
    _sm_scale,
    _validate_spec_output,
    multi_scale_noise,
)
from .rate10_codex_batch import _dot_noise, _finish, _line_distance, _scale, _star


def _base(shape, seed, m=0.22, r=0.30, c=0.24, span=0.12):
    n1 = _normalize(multi_scale_noise(shape, [3, 7, 16], [0.46, 0.33, 0.21], seed + 101))
    n2 = _normalize(multi_scale_noise(shape, [4, 9, 19], [0.44, 0.34, 0.22], seed + 107))
    n3 = _normalize(multi_scale_noise(shape, [5, 11, 23], [0.42, 0.34, 0.24], seed + 113))
    return (
        (m + (n1 - 0.5) * span).astype(np.float32),
        (r + (n2 - 0.5) * span).astype(np.float32),
        (c + (n3 - 0.5) * span).astype(np.float32),
    )


def _pins(M, R, CC, rng, count=2600, mode="mixed"):
    h, w = M.shape
    n = int(np.clip(count * (h * w / (2048 * 2048)), 120, count))
    y = rng.integers(0, h, n); x = rng.integers(0, w, n)
    if mode == "hot":
        M[y, x] = rng.uniform(0.55, 0.98, n); R[y, x] = rng.uniform(0.26, 0.78, n); CC[y, x] = rng.uniform(0.04, 0.44, n)
    elif mode == "glass":
        M[y, x] = rng.uniform(0.24, 0.95, n); R[y, x] = rng.uniform(0.04, 0.28, n); CC[y, x] = rng.uniform(0.55, 0.98, n)
    else:
        M[y, x] = rng.uniform(0.12, 0.92, n); R[y, x] = rng.uniform(0.08, 0.82, n); CC[y, x] = rng.uniform(0.10, 0.96, n)


def _occult(shape, seed, name, palette="violet", glyphs=220, threads=2100):
    h, w = shape
    if _scale(shape) < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 22000 + len(name))
    sc = _scale(shape)
    if palette == "blood":
        M, R, CC = _base(shape, int(seed), 0.30, 0.12, 0.14, 0.14)
    elif palette == "frost":
        M, R, CC = _base(shape, int(seed), 0.16, 0.23, 0.34, 0.14)
    elif palette == "gold":
        M, R, CC = _base(shape, int(seed), 0.30, 0.34, 0.16, 0.12)
    else:
        M, R, CC = _base(shape, int(seed), 0.16, 0.12, 0.26, 0.14)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lace = _line_distance(xx * 0.61 + yy * 0.17, 12.0 * sc, 0.44 * sc, seed * 0.13)
    counter = _line_distance(xx * 0.21 - yy * 0.72, 18.0 * sc, 0.52 * sc, seed * 0.19)
    M = np.clip(M + lace * 0.11 + counter * 0.06, 0, 1)
    CC = np.clip(CC + lace * 0.09 + counter * 0.10, 0, 1)
    if _CV2_OK:
        for _ in range(int(np.clip(threads * (h * w / (2048 * 2048)), 420, threads))):
            cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
            length = float(rng.uniform(8, 26) * sc)
            ang = float(rng.choice([0, math.pi / 4, -math.pi / 4, math.pi / 2]) + rng.normal(0, 0.18))
            x2 = int(np.clip(cx + math.cos(ang) * length, 0, w - 1))
            y2 = int(np.clip(cy + math.sin(ang) * length, 0, h - 1))
            tier = float(rng.choice([0.20, 0.32, 0.44, 0.58, 0.72, 0.88]))
            rv = tier * (0.18 if palette in {"violet", "blood"} else 0.56)
            cv = min(0.98, tier + 0.05) if palette != "gold" else tier * 0.45
            _cv2.line(M, (int(cx), int(cy)), (x2, y2), tier, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (int(cx), int(cy)), (x2, y2), rv, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (int(cx), int(cy)), (x2, y2), cv, 1, lineType=_cv2.LINE_AA)
        for _ in range(int(np.clip(glyphs * (h * w / (2048 * 2048)), 80, glyphs))):
            cx = int(rng.integers(8, max(9, w - 8))); cy = int(rng.integers(8, max(9, h - 8)))
            rr = max(3, int(rng.uniform(5, 13) * sc))
            tier = float(rng.uniform(0.48, 0.98))
            if rng.random() < 0.45:
                pts = _star(cx, cy, rr, max(1, rr // 2), int(rng.integers(3, 6)), rng.uniform(0, math.pi))
                _cv2.polylines(M, [pts], True, tier, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [pts], True, tier * 0.18, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, min(0.98, tier + 0.02), 1, lineType=_cv2.LINE_AA)
            else:
                _cv2.circle(M, (cx, cy), rr, tier, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), rr, tier * 0.20, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), rr, min(0.98, tier + 0.03), 1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2600)
    return _finish(name, M, R, CC, 1.0)


def _machined(shape, seed, name, mode="lathe"):
    h, w = shape
    if _scale(shape) < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 23000 + len(name))
    sc = _scale(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    M, R, CC = _base(shape, int(seed), 0.30, 0.30, 0.32, 0.07)
    grain = _line_distance(xx * 0.72 + yy * 0.10, 7.0 * sc, 0.42 * sc, seed)
    M = np.clip(M + grain * 0.13, 0, 1); CC = np.clip(CC + grain * 0.12, 0, 1)
    if _CV2_OK:
        if mode == "knurl":
            p = max(8, int(27 * sc))
            a = _line_distance(xx + yy, p, 2.0 * sc, seed)
            b = _line_distance(xx - yy, p, 2.0 * sc, seed * 0.9)
            ridge = np.maximum(a, b)
            M = np.clip(M + ridge * 0.66, 0, 1); R = np.clip(R + ridge * 0.30, 0, 1); CC = np.clip(CC + ridge * 0.54, 0, 1)
            for off in range(-h, w + h, p):
                _cv2.line(M, (off, 0), (off + h, h), 0.92, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (off, 0), (off + h, h), 0.58, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (off, 0), (off + h, h), 0.88, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (off, h), (off + h, 0), 0.82, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (off, h), (off + h, 0), 0.52, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (off, h), (off + h, 0), 0.78, 1, lineType=_cv2.LINE_AA)
        elif mode == "straight":
            p = max(7, int(15 * sc))
            ridge = _line_distance(xx, p, 1.8 * sc, seed)
            cross = _line_distance(yy * 0.22 + xx * 0.06, max(9, int(31 * sc)), 1.0 * sc, seed * 0.31)
            M = np.clip(M + ridge * 0.62 + cross * 0.16, 0, 1)
            R = np.clip(R + ridge * 0.28 + cross * 0.06, 0, 1)
            CC = np.clip(CC + ridge * 0.50 + cross * 0.12, 0, 1)
        else:
            step = max(14, int(54 * sc)); rad = max(6, int(22 * sc))
            for y in range(step // 2, h + step, step):
                for x in range(step // 2, w + step, step):
                    rr = int(rad * rng.uniform(0.75, 1.18))
                    for k in range(4):
                        start = float(rng.uniform(0, 90) + k * 90)
                        end = start + float(rng.uniform(38, 76))
                        tier = float(rng.choice([0.40, 0.52, 0.64, 0.78, 0.92]))
                        _cv2.ellipse(M, (x, y), (rr, rr), 0, start, end, tier, 1, lineType=_cv2.LINE_AA)
                        _cv2.ellipse(R, (x, y), (rr, rr), 0, start, end, min(0.82, tier * 0.72), 1, lineType=_cv2.LINE_AA)
                        _cv2.ellipse(CC, (x, y), (rr, rr), 0, start, end, min(0.98, tier + 0.05), 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 4800, 0.032)
    return _finish(name, M, R, CC, 1.0)


def _track(shape, seed, name, mode="grit"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 24000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.25, 0.18, 0.24, 0.10)
    if _CV2_OK:
        for _ in range(int(np.clip(1200 * (h * w / (2048 * 2048)), 260, 1200))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            if mode == "rain":
                rr = max(2, int(rng.uniform(3, 9) * sc))
                _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.30, 0.70)), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), rr, float(rng.uniform(0.04, 0.22)), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.70, 0.98)), 1, lineType=_cv2.LINE_AA)
            elif mode == "tape":
                length = float(rng.uniform(8, 22) * sc); ang = float(rng.choice([0, math.pi / 4, -math.pi / 4]) + rng.normal(0, 0.16))
                x2 = int(np.clip(cx + math.cos(ang) * length, 0, w - 1)); y2 = int(np.clip(cy + math.sin(ang) * length, 0, h - 1))
                _cv2.line(M, (cx, cy), (x2, y2), float(rng.uniform(0.42, 0.92)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx, cy), (x2, y2), float(rng.uniform(0.10, 0.42)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx, cy), (x2, y2), float(rng.uniform(0.18, 0.78)), 1, lineType=_cv2.LINE_AA)
            else:
                rr = max(1, int(rng.uniform(1.5, 4.5) * sc))
                _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.10, 0.88)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), rr, float(rng.uniform(0.14, 0.48)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.08, 0.72)), -1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2600, "mixed")
    return _finish(name, M, R, CC, 1.0)


def _prism(shape, seed, name, tight=10.0):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    sc = _scale(shape)
    rng = np.random.default_rng(int(seed) + 25000 + len(name))
    warp = _normalize(multi_scale_noise(shape, [7, 15, 33], [0.44, 0.34, 0.22], int(seed) + 71))
    phase = (xx * 0.52 + yy * 0.18 + (warp - 0.5) * 10 * sc) * (2 * math.pi / max(1.0, tight * sc))
    micro = (xx * 0.13 - yy * 0.72) * (2 * math.pi / max(1.0, 5.5 * sc))
    M = np.clip(0.20 + (np.sin(phase) + 1) * 0.16 + (np.sin(micro) + 1) * 0.05, 0, 1).astype(np.float32)
    R = np.clip(0.18 + (np.sin(phase + 2.1) + 1) * 0.12 + (np.sin(micro + 2.4) + 1) * 0.04, 0, 1).astype(np.float32)
    CC = np.clip(0.24 + (np.sin(phase + 4.2) + 1) * 0.20 + (np.sin(micro + 4.0) + 1) * 0.05, 0, 1).astype(np.float32)
    _pins(M, R, CC, rng, 2400, "glass")
    return _finish(name, M, R, CC, 1.0)


def codex_gradient_bands(shape, seed, sm, **kwargs): return _prism(shape, seed + 1, "gradient_bands", 8.0)
def codex_gravel_chip_field(shape, seed, sm, **kwargs): return _track(shape, seed + 2, "gravel_chip_field", "grit")
def codex_gravity_well(shape, seed, sm, **kwargs): return _occult(shape, seed + 3, "gravity_well", "violet", 320, 1800)
def codex_hex_blood_drip(shape, seed, sm, **kwargs): return _occult(shape, seed + 4, "hex_blood_drip", "blood", 280, 2200)
def codex_holo_prism_shift_loop2(shape, seed, sm, **kwargs): return _prism(shape, seed + 5, "holo_prism_shift", 7.0)
def codex_jeweled_guilloche(shape, seed, sm, **kwargs): return _machined(shape, seed + 6, "jeweled_guilloche", "lathe")
def codex_knurl_diamond(shape, seed, sm, **kwargs): return _machined(shape, seed + 7, "knurl_diamond", "knurl")
def codex_knurl_straight(shape, seed, sm, **kwargs): return _machined(shape, seed + 8, "knurl_straight", "straight")
def codex_lathe_concentric(shape, seed, sm, **kwargs): return _machined(shape, seed + 9, "lathe_concentric", "lathe")
def codex_marble_vein(shape, seed, sm, **kwargs): return _occult(shape, seed + 10, "marble_vein", "gold", 160, 3000)
def codex_meteor_impact(shape, seed, sm, **kwargs): return _track(shape, seed + 11, "meteor_impact", "grit")
def codex_micro_sparkle(shape, seed, sm, **kwargs): return _prism(shape, seed + 12, "micro_sparkle", 5.0)
def codex_micro_sparkle_cool(shape, seed, sm, **kwargs): return _prism(shape, seed + 13, "micro_sparkle_cool", 6.0)
def codex_mud_splatter_random(shape, seed, sm, **kwargs): return _track(shape, seed + 14, "mud_splatter_random", "grit")
def codex_oil_slick(shape, seed, sm, **kwargs): return _prism(shape, seed + 15, "oil_slick", 9.0)
def codex_oil_streak_panel(shape, seed, sm, **kwargs): return _track(shape, seed + 16, "oil_streak_panel", "tape")
def codex_orbital_swirl(shape, seed, sm, **kwargs): return _machined(shape, seed + 17, "orbital_swirl", "lathe")
def codex_patina_bloom(shape, seed, sm, **kwargs): return _occult(shape, seed + 18, "patina_bloom", "gold", 180, 2600)
def codex_pit_lane_stripes(shape, seed, sm, **kwargs): return _track(shape, seed + 19, "pit_lane_stripes", "tape")
def codex_plasma_turbulence(shape, seed, sm, **kwargs): return _occult(shape, seed + 20, "plasma_turbulence", "frost", 220, 3100)
def codex_prismatic_dust(shape, seed, sm, **kwargs): return _prism(shape, seed + 21, "prismatic_dust", 5.0)
def codex_race_number_ghost(shape, seed, sm, **kwargs): return _occult(shape, seed + 22, "race_number_ghost", "violet", 260, 1800)
def codex_racing_tape_residue(shape, seed, sm, **kwargs): return _track(shape, seed + 23, "racing_tape_residue", "tape")
def codex_radial_sunburst(shape, seed, sm, **kwargs): return _machined(shape, seed + 24, "radial_sunburst", "lathe")
def codex_rain_droplet_beads(shape, seed, sm, **kwargs): return _track(shape, seed + 25, "rain_droplet_beads", "rain")
