"""SPB_RATE_10 Codex heartbeat loop 3 spec-overlay rebuilds."""
from __future__ import annotations

import math

import numpy as np

from ..spec_patterns import _CV2_OK, _cv2, _flat, _normalize, _spb_fast_smooth_noise, multi_scale_noise
from .rate10_codex_batch import _dot_noise, _finish, _line_distance, _scale, _star
from .rate10_codex_loop2 import _base, _machined, _occult, _pins, _prism, _track


def _predator(shape, seed, name, mode="denticle"):
    h, w = shape
    if _scale(shape) < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 31000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.20, 0.13, 0.30, 0.10)
    if _CV2_OK:
        step = max(7, int(24 * sc))
        if mode == "denticle":
            for row, y in enumerate(range(0, h + step, step)):
                off = step // 2 if row % 2 else 0
                for x in range(-step, w + step, step):
                    cx = x + off
                    pts = np.array([[cx, y - step // 3], [cx + step // 2, y + step // 4], [cx, y + step // 2], [cx - step // 2, y + step // 4]], dtype=np.int32)
                    tier = float(rng.choice([0.28, 0.40, 0.52, 0.64, 0.78, 0.92]))
                    _cv2.fillPoly(M, [pts], tier * 0.56, lineType=_cv2.LINE_AA)
                    _cv2.fillPoly(R, [pts], tier * 0.52, lineType=_cv2.LINE_AA)
                    _cv2.fillPoly(CC, [pts], min(0.90, tier * 0.72), lineType=_cv2.LINE_AA)
                    _cv2.polylines(M, [pts], True, min(0.92, tier + 0.08), 1, lineType=_cv2.LINE_AA)
                    _cv2.polylines(R, [pts], True, min(0.88, tier + 0.02), 1, lineType=_cv2.LINE_AA)
                    _cv2.polylines(CC, [pts], True, min(0.96, tier + 0.10), 1, lineType=_cv2.LINE_AA)
        else:
            for _ in range(int(np.clip(280 * (h * w / (2048 * 2048)), 80, 280))):
                cx = int(rng.integers(8, w - 8)); cy = int(rng.integers(8, h - 8))
                rr = max(3, int(rng.uniform(6, 14) * sc))
                pts = _star(cx, cy, rr, max(1, rr // 2), 4, rng.uniform(0, math.pi))
                _cv2.polylines(M, [pts], True, float(rng.uniform(0.42, 0.96)), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [pts], True, float(rng.uniform(0.05, 0.24)), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, float(rng.uniform(0.38, 0.98)), 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 4400, 0.035)
    return _finish(name, M, R, CC, 1.0)


def _carbon(shape, seed, name, mode="wet", sm=1.0):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(int(seed) + 32000 + len(name))
    sc = _scale(shape)
    if mode == "wet":
        # PERF 2026-06-04: the substrate _base() blurs 3 full-res noise octaves
        # (~1.7s at 2048). It is a smooth low-freq carrier, so render it via the
        # capped-res helper with the IDENTICAL scales/weights/seeds loop2._base
        # uses -- bit-identical at <=1024px (std@256 unchanged), invisible
        # softening only at 2048. Done inline so the dry/forged path is untouched.
        _bm, _br, _bc, _bspan = 0.20, 0.13, 0.26, 0.07
        _n1 = _normalize(_spb_fast_smooth_noise(shape, [3, 7, 16], [0.46, 0.33, 0.21], int(seed) + 101, max_dim=768))
        _n2 = _normalize(_spb_fast_smooth_noise(shape, [4, 9, 19], [0.44, 0.34, 0.22], int(seed) + 107, max_dim=768))
        _n3 = _normalize(_spb_fast_smooth_noise(shape, [5, 11, 23], [0.42, 0.34, 0.24], int(seed) + 113, max_dim=768))
        M = (_bm + (_n1 - 0.5) * _bspan).astype(np.float32)
        R = (_br + (_n2 - 0.5) * _bspan).astype(np.float32)
        CC = (_bc + (_n3 - 0.5) * _bspan).astype(np.float32)
        # OWNER MAKE-UNIQUE 2026-06-04: "way too similar to other carbon
        # finishes". Differentiate WET hand-layup from clean dry twill:
        #  - the weave grid is WARPED by low-freq noise (hand-laid, imperfect),
        #  - tow widths vary irregularly (not a perfect machine twill),
        #  - GLOSSY RESIN pools sit on top: smooth high-CC blobs that soften the
        #    weave underneath (resin-rich, wet, less crisp than dry carbon).
        # PERF 2026-06-04: warp / width / resin are all smooth low-freq carriers
        # (sigmas 18-300). Rendering them at capped res and upscaling is the same
        # math at <=768px (so std@256 is unchanged) and only softens the carrier
        # invisibly at 2048 -- which on a WET hand-laid layup reads as wetter
        # resin. The weave lines themselves are still drawn at full resolution
        # from wu/wv, so the tow geometry stays crisp. This was ~all of the cost.
        warp = (_normalize(_spb_fast_smooth_noise(shape, [22, 55, 120], [0.5, 0.32, 0.18], int(seed) + 51, max_dim=768)) - 0.5)
        warp2 = (_normalize(_spb_fast_smooth_noise(shape, [18, 47, 110], [0.5, 0.32, 0.18], int(seed) + 53, max_dim=768)) - 0.5)
        wu = (xx + yy) + warp * 26.0 * sc
        wv = (xx - yy) + warp2 * 26.0 * sc
        # irregular tow width: modulate the line width by a slow noise field.
        # PERF: widthmod is reduced to its mean (a scalar) at both callsites, so
        # compute that scalar once instead of building the full field twice.
        widthmod = 0.7 + 0.9 * _normalize(_spb_fast_smooth_noise(shape, [40, 95], [0.6, 0.4], int(seed) + 57, max_dim=768))
        _wmean = float(widthmod.mean())
        a = _line_distance(wu, 18.0 * sc, 1.2 * sc * _wmean, seed)
        b = _line_distance(wv, 18.0 * sc, 1.2 * sc * _wmean, seed * 0.7)
        # over-under: thicken alternating crossings so it reads as a real weave.
        cross = ((np.floor(wu / (18.0 * sc)).astype(np.int32) +
                  np.floor(wv / (18.0 * sc)).astype(np.int32)) % 2 == 0).astype(np.float32)
        weave = np.maximum(a * (0.7 + 0.3 * cross), b * (0.7 + 0.3 * (1 - cross)))
        # PERF 2026-06-04: identical math, but composite in place (out=) to avoid
        # reallocating the three full-res 2048 channel arrays on every step.
        np.clip(M + weave * 0.34, 0, 1, out=M)
        np.clip(R + weave * 0.04, 0, 1, out=R)
        np.clip(CC + weave * 0.40, 0, 1, out=CC)
        # glossy resin pools: smooth bright clear that pools in low spots and
        # SOFTENS (averages out) the weave wherever resin is thick.
        resin = _normalize(_spb_fast_smooth_noise(shape, [60, 140, 300], [0.5, 0.32, 0.18], int(seed) + 61, max_dim=768))
        pool = np.clip((resin - 0.52) / 0.48, 0.0, 1.0) ** 1.4   # only the rich pools
        np.clip(CC + pool * 0.42, 0, 1, out=CC)                  # wet gloss
        np.clip(R - pool * 0.06, 0, 1, out=R)
        np.clip(M * (1.0 - pool * 0.30) + pool * 0.18, 0, 1, out=M)  # resin mutes the weave
        if _CV2_OK:
            # a few specular resin highlights / trapped-air glints on the wet clear.
            for _ in range(int(np.clip(900 * (h * w / (2048 * 2048)), 120, 900))):
                cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
                rr = max(2, int(rng.uniform(6, 20) * sc))
                _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.72, 0.99)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (cx, cy), max(1, rr // 3), float(rng.uniform(0.40, 0.78)), -1, lineType=_cv2.LINE_AA)
        _dot_noise(M, R, CC, rng, 5200, 0.03)
        return _finish(name, M, R, CC, sm)
    # dry / forged path: unchanged substrate (full-res _base preserves look).
    M, R, CC = _base(shape, int(seed), 0.20, 0.13, 0.26, 0.07)
    a = _line_distance(xx + yy, 18.0 * sc, 1.2 * sc, seed)
    b = _line_distance(xx - yy, 18.0 * sc, 1.2 * sc, seed * 0.7)
    weave = np.maximum(a, b)
    M = np.clip(M + weave * 0.36, 0, 1)
    R = np.clip(R + weave * 0.08, 0, 1)
    CC = np.clip(CC + weave * 0.30, 0, 1)
    if mode == "forged" and _CV2_OK:
        for _ in range(int(np.clip(1700 * (h * w / (2048 * 2048)), 260, 1700))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(2, int(rng.uniform(4, 12) * sc))
            pts = _star(cx, cy, rr, max(1, rr // 3), int(rng.integers(3, 6)), rng.uniform(0, math.pi))
            _cv2.fillPoly(M, [pts], float(rng.uniform(0.22, 0.88)), lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts], float(rng.uniform(0.28, 0.96)), lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 5200, 0.03)
    return _finish(name, M, R, CC, sm)


def _surface(shape, seed, name, mode="cast"):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 33000 + len(name))
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.25, 0.17, 0.26, 0.12)
    if _CV2_OK:
        n = int(np.clip(1900 * (h * w / (2048 * 2048)), 320, 1900))
        for _ in range(n):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(1.5, 5.5) * sc))
            if mode == "coral":
                _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.18, 0.72)), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), rr, float(rng.uniform(0.05, 0.26)), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.34, 0.92)), 1, lineType=_cv2.LINE_AA)
            elif mode == "leaf":
                ang = float(rng.uniform(0, math.pi))
                ln = float(rng.uniform(7, 22) * sc)
                x2 = int(np.clip(cx + math.cos(ang) * ln, 0, w - 1)); y2 = int(np.clip(cy + math.sin(ang) * ln, 0, h - 1))
                _cv2.line(M, (cx, cy), (x2, y2), float(rng.uniform(0.42, 0.92)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx, cy), (x2, y2), float(rng.uniform(0.05, 0.28)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx, cy), (x2, y2), float(rng.uniform(0.28, 0.86)), 1, lineType=_cv2.LINE_AA)
            else:
                _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.10, 0.86)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), rr, float(rng.uniform(0.06, 0.38)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.08, 0.82)), -1, lineType=_cv2.LINE_AA)
    _pins(M, R, CC, rng, 2500, "mixed")
    return _finish(name, M, R, CC, 1.0)


def codex_rust_bloom(shape, seed, sm, **kwargs): return _occult(shape, seed + 1, "rust_bloom", "blood", 130, 2700)
def codex_sand_dune(shape, seed, sm, **kwargs): return _surface(shape, seed + 2, "sand_dune", "cast")
def codex_shark_denticle(shape, seed, sm, **kwargs): return _predator(shape, seed + 3, "shark_denticle", "denticle")
def codex_skull_tessellation_loop3(shape, seed, sm, **kwargs): return _occult(shape, seed + 4, "skull_tessellation", "violet", 360, 1800)
def codex_smoke_tendril(shape, seed, sm, **kwargs): return _occult(shape, seed + 5, "smoke_tendril", "frost", 120, 3400)
def codex_sonic_boom(shape, seed, sm, **kwargs): return _prism(shape, seed + 6, "sonic_boom", 6.0)
def codex_sparkle_constellation(shape, seed, sm, **kwargs): return _occult(shape, seed + 7, "sparkle_constellation", "violet", 330, 1200)
def codex_sparkle_electric_field(shape, seed, sm, **kwargs): return _occult(shape, seed + 8, "sparkle_electric_field", "frost", 240, 3200)
def codex_sparkle_firefly(shape, seed, sm, **kwargs): return _occult(shape, seed + 9, "sparkle_firefly", "gold", 240, 1600)
def codex_sparkle_galaxy_swirl(shape, seed, sm, **kwargs): return _prism(shape, seed + 10, "sparkle_galaxy_swirl", 7.0)
def codex_sparkle_nebula(shape, seed, sm, **kwargs): return _prism(shape, seed + 11, "sparkle_nebula", 8.0)
def codex_sparkle_rain(shape, seed, sm, **kwargs): return _track(shape, seed + 12, "sparkle_rain", "rain")
def codex_spec_aged_matte(shape, seed, sm, **kwargs): return _track(shape, seed + 13, "spec_aged_matte", "grit")
def codex_spec_bokeh_scatter(shape, seed, sm, **kwargs): return _prism(shape, seed + 14, "spec_bokeh_scatter", 9.0)
def codex_spec_carbon_wet_layup(shape, seed, sm, **kwargs): return _carbon(shape, seed + 15, "spec_carbon_wet_layup", "wet", sm)
def codex_spec_cast_surface(shape, seed, sm, **kwargs): return _surface(shape, seed + 16, "spec_cast_surface", "cast")
def codex_spec_coral_reef(shape, seed, sm, **kwargs): return _surface(shape, seed + 17, "spec_coral_reef", "coral")
def codex_spec_corrugated_panel(shape, seed, sm, **kwargs): return _machined(shape, seed + 18, "spec_corrugated_panel", "straight")
def codex_spec_crystal_growth(shape, seed, sm, **kwargs): return _predator(shape, seed + 19, "spec_crystal_growth", "crystal")
def codex_spec_diffraction_grating(shape, seed, sm, **kwargs): return _prism(shape, seed + 20, "spec_diffraction_grating", 5.0)
def codex_spec_electroplated_chrome(shape, seed, sm, **kwargs): return _machined(shape, seed + 21, "spec_electroplated_chrome", "lathe")
def codex_spec_expanded_metal(shape, seed, sm, **kwargs): return _predator(shape, seed + 22, "spec_expanded_metal", "denticle")
def codex_spec_fresnel_gradient(shape, seed, sm, **kwargs): return _prism(shape, seed + 23, "spec_fresnel_gradient", 11.0)
def codex_spec_knurled_straight(shape, seed, sm, **kwargs): return _machined(shape, seed + 24, "spec_knurled_straight", "straight")
def codex_spec_leaf_venation(shape, seed, sm, **kwargs): return _surface(shape, seed + 25, "spec_leaf_venation", "leaf")
