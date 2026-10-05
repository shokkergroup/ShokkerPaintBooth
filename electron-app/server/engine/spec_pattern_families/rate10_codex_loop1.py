"""SPB_RATE_10 Codex heartbeat loop 1 spec-overlay rebuilds.

SPB-RATE10 tick 2026-05-27-codex-loop1.
Owner direction:
  - treat remaining visible cards as unwanted until proven otherwise
  - redo owner REBUILD/MIXED first, then unrated visible cards
  - push dark magic / voodoo / spirits / Affliction-era motifs
  - add more engine-turn, machined, cultural, predator, heat, and carbon-adjacent finishes
  - keep features fine for 2048x2048 car canvases.
"""
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


def _base(shape, seed, m=0.20, r=0.34, c=0.22, span=0.10):
    n1 = _normalize(multi_scale_noise(shape, [3.0, 7.0, 15.0], [0.46, 0.33, 0.21], seed + 31))
    n2 = _normalize(multi_scale_noise(shape, [3.4, 8.0, 18.0], [0.44, 0.34, 0.22], seed + 37))
    n3 = _normalize(multi_scale_noise(shape, [4.0, 9.0, 21.0], [0.42, 0.34, 0.24], seed + 41))
    return (
        (m + (n1 - 0.5) * span).astype(np.float32),
        (r + (n2 - 0.5) * span).astype(np.float32),
        (c + (n3 - 0.5) * span).astype(np.float32),
    )


def _scatter_pins(M, R, CC, rng, count, hot=False):
    h, w = M.shape
    n = int(np.clip(count * (h * w / (2048 * 2048)), 140, count))
    y = rng.integers(0, h, n)
    x = rng.integers(0, w, n)
    if hot:
        M[y, x] = rng.uniform(0.62, 0.98, n)
        R[y, x] = rng.uniform(0.34, 0.76, n)
        CC[y, x] = rng.uniform(0.04, 0.24, n)
    else:
        M[y, x] = rng.uniform(0.12, 0.92, n)
        R[y, x] = rng.uniform(0.08, 0.82, n)
        CC[y, x] = rng.uniform(0.10, 0.94, n)


def _draw_tiny_cross(M, R, CC, cx, cy, size, vals):
    if not _CV2_OK:
        return
    m, r, c = vals
    _cv2.line(M, (cx - size, cy), (cx + size, cy), m, 1, lineType=_cv2.LINE_AA)
    _cv2.line(M, (cx, cy - size), (cx, cy + size), m, 1, lineType=_cv2.LINE_AA)
    _cv2.line(R, (cx - size, cy), (cx + size, cy), r, 1, lineType=_cv2.LINE_AA)
    _cv2.line(R, (cx, cy - size), (cx, cy + size), r, 1, lineType=_cv2.LINE_AA)
    _cv2.line(CC, (cx - size, cy), (cx + size, cy), c, 1, lineType=_cv2.LINE_AA)
    _cv2.line(CC, (cx, cy - size), (cx, cy + size), c, 1, lineType=_cv2.LINE_AA)


def _occult_field(shape, seed, name, palette="violet", sigils=260, threads=1800):
    h, w = shape
    if _scale(shape) < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 14401 + len(name))
    sc = _scale(shape)
    if palette == "copper":
        M, R, CC = _base(shape, int(seed), 0.28, 0.24, 0.14, 0.14)
    elif palette == "frost":
        M, R, CC = _base(shape, int(seed), 0.16, 0.22, 0.34, 0.14)
    else:
        M, R, CC = _base(shape, int(seed), 0.16, 0.12, 0.24, 0.14)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    veil = _line_distance(xx * 0.42 + yy * 0.23, 19.0 * sc, 0.65 * sc, seed * 0.07)
    lace_a = _line_distance(xx * 0.67 + yy * 0.11, 13.0 * sc, 0.46 * sc, seed * 0.11)
    lace_b = _line_distance(xx * 0.19 - yy * 0.61, 17.0 * sc, 0.50 * sc, seed * 0.17)
    M = np.clip(M + veil * 0.10 + lace_a * 0.10 + lace_b * 0.06, 0, 1)
    R = np.clip(R + lace_b * 0.035 - veil * 0.025, 0, 1)
    CC = np.clip(CC + veil * 0.13 + lace_a * 0.08 + lace_b * 0.09, 0, 1)
    if _CV2_OK:
        for _ in range(int(np.clip(threads * (h * w / (2048 * 2048)), 420, threads))):
            cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
            length = float(rng.uniform(8.0, 26.0) * sc)
            ang = float(rng.choice([0, math.pi / 4, -math.pi / 4, math.pi / 2]) + rng.normal(0, 0.18))
            x2 = int(np.clip(cx + math.cos(ang) * length, 0, w - 1))
            y2 = int(np.clip(cy + math.sin(ang) * length, 0, h - 1))
            tier = float(rng.choice([0.18, 0.26, 0.36, 0.48, 0.62, 0.78, 0.92]))
            if palette == "copper":
                vals = (tier, min(0.76, tier * 0.78), min(0.54, tier * 0.42))
            elif palette == "frost":
                vals = (tier * 0.50, min(0.68, tier * 0.52), min(0.98, tier + 0.10))
            else:
                vals = (tier * 0.74, max(0.04, tier * 0.22), min(0.96, tier + 0.06))
            _cv2.line(M, (int(cx), int(cy)), (x2, y2), vals[0], 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (int(cx), int(cy)), (x2, y2), vals[1], 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (int(cx), int(cy)), (x2, y2), vals[2], 1, lineType=_cv2.LINE_AA)
        for _ in range(int(np.clip(sigils * (h * w / (2048 * 2048)), 90, sigils))):
            cx = int(rng.integers(8, max(9, w - 8))); cy = int(rng.integers(8, max(9, h - 8)))
            rr = max(3, int(rng.uniform(5, 12) * sc))
            tier = float(rng.choice([0.34, 0.46, 0.58, 0.70, 0.84, 0.96]))
            vals = (tier * 0.76, tier * 0.22, min(0.98, tier + 0.04))
            if rng.random() < 0.35:
                pts = _star(cx, cy, rr, max(1, rr // 2), 5, rng.uniform(0, math.pi))
                _cv2.polylines(M, [pts], True, vals[0], 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [pts], True, vals[1], 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, vals[2], 1, lineType=_cv2.LINE_AA)
            elif rng.random() < 0.60:
                _cv2.circle(M, (cx, cy), rr, vals[0], 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), rr, vals[1], 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), rr, vals[2], 1, lineType=_cv2.LINE_AA)
                _draw_tiny_cross(M, R, CC, cx, cy, max(2, rr // 2), vals)
            else:
                _draw_tiny_cross(M, R, CC, cx, cy, rr, vals)
    _scatter_pins(M, R, CC, rng, 3200)
    return _finish(name, M, R, CC, 1.0)


def _machined_field(shape, seed, name, mode="turn"):
    h, w = shape
    if _scale(shape) < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 15501 + len(name))
    sc = _scale(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    M, R, CC = _base(shape, int(seed), 0.30, 0.30, 0.32, 0.06)
    grain = _line_distance(xx * 0.85 + yy * 0.08, 8.0 * sc, 0.45 * sc, seed)
    M = np.clip(M + grain * 0.12, 0, 1)
    CC = np.clip(CC + grain * 0.10, 0, 1)
    if _CV2_OK:
        if mode == "dimple":
            step = max(7, int(28 * sc)); rad = max(2, int(6 * sc))
            for row, y in enumerate(range(step // 2, h, step)):
                off = step // 2 if row % 2 else 0
                for x in range(step // 2 + off, w, step):
                    tier = float(rng.choice([0.26, 0.38, 0.50, 0.62, 0.76, 0.90]))
                    _cv2.circle(M, (x, y), rad, min(0.98, tier + 0.16), 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(R, (x, y), max(1, rad - 1), min(0.82, tier * 0.72), -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (x, y), rad, min(0.98, tier + 0.10), 1, lineType=_cv2.LINE_AA)
        else:
            step = max(10, int(44 * sc)); rad = max(5, int(18 * sc))
            for y in range(step // 2, h + step, step):
                for x in range(step // 2, w + step, step):
                    rr = int(rad * rng.uniform(0.75, 1.15))
                    for k in range(3):
                        start = float(rng.uniform(0, 120) + k * 92)
                        end = start + float(rng.uniform(42, 86))
                        tier = float(rng.choice([0.42, 0.54, 0.66, 0.78, 0.92]))
                        _cv2.ellipse(M, (x, y), (rr, rr), 0, start, end, tier, 1, lineType=_cv2.LINE_AA)
                        _cv2.ellipse(R, (x, y), (rr, rr), 0, start, end, min(0.82, tier * 0.74), 1, lineType=_cv2.LINE_AA)
                        _cv2.ellipse(CC, (x, y), (rr, rr), 0, start, end, min(0.98, tier + 0.06), 1, lineType=_cv2.LINE_AA)
                    if mode == "flycut":
                        ang = rng.uniform(0, math.pi)
                        length = max(6, int(rng.uniform(10, 24) * sc))
                        _cv2.line(M, (x, y), (int(x + math.cos(ang) * length), int(y + math.sin(ang) * length)), 0.96, 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 4500, 0.035)
    return _finish(name, M, R, CC, 1.0)


def _thermal_field(shape, seed, name, scale_period=18.0, beads=False):
    h, w = shape
    if _scale(shape) < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 16601 + len(name))
    sc = _scale(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = _normalize(multi_scale_noise(shape, [6.0, 13.0, 29.0], [0.45, 0.34, 0.21], int(seed) + 71))
    bands = (xx * 0.38 + yy * 0.16 + (warp - 0.5) * 16.0 * sc) * (2.0 * math.pi / max(1.0, scale_period * sc))
    micro = (xx * 0.74 - yy * 0.21 + (warp - 0.5) * 8.0 * sc) * (2.0 * math.pi / max(1.0, 5.5 * sc))
    M = np.clip(0.22 + (np.sin(bands) + 1) * 0.16 + (np.sin(micro + 0.7) + 1) * 0.05, 0, 1).astype(np.float32)
    R = np.clip(0.20 + (np.sin(bands + 1.7) + 1) * 0.12 + (np.sin(micro + 2.4) + 1) * 0.04, 0, 1).astype(np.float32)
    CC = np.clip(0.16 + (np.sin(bands + 3.7) + 1) * 0.18 + (np.sin(micro + 4.0) + 1) * 0.05, 0, 1).astype(np.float32)
    edge = _line_distance(xx * 0.95 - yy * 0.18, 11.0 * sc, 0.55 * sc, seed)
    M = np.clip(M + edge * 0.12, 0, 1)
    CC = np.clip(CC + edge * 0.08, 0, 1)
    if beads and _CV2_OK:
        for _ in range(int(np.clip(900 * (h * w / (2048 * 2048)), 220, 900))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(2.0, 5.0) * sc))
            _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.44, 0.84)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.22, 0.70)), 1, lineType=_cv2.LINE_AA)
    _scatter_pins(M, R, CC, rng, 2200, hot=True)
    return _finish(name, M, R, CC, 1.0)


def codex_abstract_expressionist_splatter(shape, seed, sm, **kwargs):
    """Replaced with blackthorn occult filigree, not gallery-paint splatter."""
    return _sm_scale(_occult_field(shape, seed + 1, "abstract_expressionist_splatter", "violet", 360, 2300), sm)


def codex_cc_masking_edge(shape, seed, sm, **kwargs):
    """Fine torn tape ghosts: tiny serrations and adhesive edge glints."""
    h, w = shape
    rng = np.random.default_rng(int(seed) + 17002)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.18, 0.50, 0.28, 0.08)
    if _CV2_OK:
        for lane in range(14):
            y = int((lane + 0.5) * h / 14 + rng.uniform(-10, 10) * sc)
            for x in range(-20, w + 20, max(6, int(15 * sc))):
                amp = int(rng.uniform(-5, 5) * sc)
                x2 = x + max(5, int(rng.uniform(8, 18) * sc))
                vals = (float(rng.uniform(0.48, 0.88)), float(rng.uniform(0.12, 0.38)), float(rng.uniform(0.38, 0.86)))
                _cv2.line(M, (x, y + amp), (x2, y - amp), vals[0], 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x, y + amp), (x2, y - amp), vals[1], 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x, y + amp), (x2, y - amp), vals[2], 1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.35:
                    _cv2.circle(M, (x2, y - amp), max(1, int(2 * sc)), 0.75, -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (x2, y - amp), max(1, int(2 * sc)), 0.68, -1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 2800, 0.045)
    return _finish("cc_masking_edge", M, R, CC, sm)


def codex_cc_spot_polish(shape, seed, sm, **kwargs):
    """Dense jeweling polish discs; about 4x more discs than the rejected pass."""
    return _machined_field(shape, seed + 3, "cc_spot_polish", "turn")


def codex_cloud_wisps(shape, seed, sm, **kwargs):
    """Ghostly ectoplasm veil with fine spirit threads and small ritual marks."""
    return _sm_scale(_occult_field(shape, seed + 4, "cloud_wisps", "frost", 180, 2600), sm)


def codex_copper_patina_drip(shape, seed, sm, **kwargs):
    """Verdigris voodoo copper: fine corrosion veins, no fat paint drips."""
    return _sm_scale(_occult_field(shape, seed + 5, "copper_patina_drip", "copper", 210, 2500), sm)


def codex_diamond_dust_loop1(shape, seed, sm, **kwargs):
    """Denser black-diamond dust with many tiny angular chips."""
    h, w = shape
    rng = np.random.default_rng(int(seed) + 17006)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.14, 0.24, 0.20, 0.06)
    if _CV2_OK:
        for _ in range(int(np.clip(5600 * (h * w / (2048 * 2048)), 500, 5600))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(1.5, 4.5) * sc))
            pts = np.array([[cx, cy - rr], [cx + rr, cy], [cx, cy + rr], [cx - rr, cy]], dtype=np.int32)
            _cv2.fillPoly(M, [pts], float(rng.uniform(0.46, 0.98)), lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [pts], float(rng.uniform(0.04, 0.26)), lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts], float(rng.uniform(0.42, 0.98)), lineType=_cv2.LINE_AA)
    _scatter_pins(M, R, CC, rng, 4200)
    return _finish("diamond_dust", M, R, CC, sm)


def codex_heat_discoloration_loop1(shape, seed, sm, **kwargs):
    """Tight exhaust temper bands, cleaner than the rejected heat wash."""
    return _thermal_field(shape, seed + 7, "heat_discoloration", 13.0, False)


def codex_spec_heat_scale_loop1(shape, seed, sm, **kwargs):
    """Fine weld-scale heat ripples with no random large circles."""
    return _thermal_field(shape, seed + 8, "spec_heat_scale", 10.0, False)


def codex_spec_mesh_perforated_loop1(shape, seed, sm, **kwargs):
    """Clean perforated race mesh: small holes, crisp rims, no messy confetti."""
    h, w = shape
    rng = np.random.default_rng(int(seed) + 17009)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.25, 0.27, 0.26, 0.05)
    if _CV2_OK:
        step = max(7, int(24 * sc)); rad = max(2, int(5 * sc))
        for row, y in enumerate(range(step // 2, h, step)):
            off = step // 2 if row % 2 else 0
            for x in range(step // 2 + off, w, step):
                _cv2.circle(M, (x, y), rad + 1, 0.76, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (x, y), rad + 1, 0.68, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (x, y), rad + 1, 0.72, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (x, y), rad, 0.12, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (x, y), rad, 0.08, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (x, y), rad, 0.10, -1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 6000, 0.025)
    return _finish("spec_mesh_perforated", M, R, CC, sm)


def codex_aniso_grain_deep(shape, seed, sm, **kwargs):
    """Deep engine-turned anisotropic grain with overlapping machined arcs."""
    return _machined_field(shape, seed + 10, "aniso_grain_deep", "flycut")


def codex_concentric_ripple(shape, seed, sm, **kwargs):
    """Spirit-board ripple rings: many small planchette circles and hairlines."""
    return _sm_scale(_occult_field(shape, seed + 11, "concentric_ripple", "violet", 300, 1600), sm)


def codex_crayon_wax_resist(shape, seed, sm, **kwargs):
    """Wax-resist ritual scrawl: scratched sigils instead of childish crayon."""
    return _sm_scale(_occult_field(shape, seed + 12, "crayon_wax_resist", "copper", 330, 2200), sm)


def codex_crushed_glass(shape, seed, sm, **kwargs):
    """Cursed mirror shard field with fine angular glints."""
    h, w = shape
    rng = np.random.default_rng(int(seed) + 17013)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.18, 0.20, 0.32, 0.07)
    if _CV2_OK:
        for _ in range(int(np.clip(2200 * (h * w / (2048 * 2048)), 350, 2200))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(3, int(rng.uniform(5, 14) * sc))
            pts = _star(cx, cy, rr, max(1, rr // 3), int(rng.integers(3, 5)), rng.uniform(0, math.pi))
            _cv2.polylines(M, [pts], True, float(rng.uniform(0.42, 0.96)), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(R, [pts], True, float(rng.uniform(0.04, 0.22)), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [pts], True, float(rng.uniform(0.52, 0.98)), 1, lineType=_cv2.LINE_AA)
    _scatter_pins(M, R, CC, rng, 3600)
    return _finish("crushed_glass", M, R, CC, sm)


def codex_depth_gradient(shape, seed, sm, **kwargs):
    """Ghost veil depth: layered transparent shrouds with small spectral pores."""
    return _sm_scale(_occult_field(shape, seed + 14, "depth_gradient", "frost", 140, 1900), sm)


def codex_drag_strip_burnout(shape, seed, sm, **kwargs):
    """Dark tire-lay streaks, hot rubber flecks, and clean track grit."""
    h, w = shape
    rng = np.random.default_rng(int(seed) + 17015)
    M, R, CC = _base(shape, int(seed), 0.24, 0.24, 0.22, 0.08)
    sc = _scale(shape)
    if _CV2_OK:
        for _ in range(9):
            y = int(rng.uniform(0.08, 0.92) * h)
            x = int(rng.uniform(-0.15, 0.15) * w)
            for _seg in range(100):
                length = float(rng.uniform(10, 22) * sc)
                ang = rng.normal(0, 0.05)
                x2 = int(x + math.cos(ang) * length); y2 = int(y + math.sin(ang) * length)
                _cv2.line(M, (x, y), (x2, y2), 0.08, max(1, int(2 * sc)), lineType=_cv2.LINE_AA)
                _cv2.line(R, (x, y), (x2, y2), 0.18, max(1, int(2 * sc)), lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x, y), (x2, y2), 0.10, max(1, int(2 * sc)), lineType=_cv2.LINE_AA)
                x, y = x2, y2
                if x > w + 20:
                    break
    _scatter_pins(M, R, CC, rng, 4800, hot=True)
    return _finish("drag_strip_burnout", M, R, CC, sm)


def codex_edm_dimple(shape, seed, sm, **kwargs):
    """Electrical-discharge-machined dimples with crisp tiny crater lips."""
    return _machined_field(shape, seed + 16, "edm_dimple", "dimple")


def codex_electric_branches(shape, seed, sm, **kwargs):
    """Witch-light branch filaments: lightning roots and spectral beads."""
    return _sm_scale(_occult_field(shape, seed + 17, "electric_branches", "frost", 210, 3100), sm)


def codex_ember_field(shape, seed, sm, **kwargs):
    """Fine ember ash with tiny hot coal cores, no random large blobs."""
    return _thermal_field(shape, seed + 18, "ember_field", 8.0, True)


def codex_exhaust_pipe_scorch(shape, seed, sm, **kwargs):
    """Pipe-scorch blue/straw heat haze with soot pin texture."""
    return _thermal_field(shape, seed + 19, "exhaust_pipe_scorch", 11.0, True)


def codex_flow_lines(shape, seed, sm, **kwargs):
    """Black-ink spirit flow lines: fine calligraphic streams and glossy edges."""
    return _sm_scale(_occult_field(shape, seed + 20, "flow_lines", "violet", 190, 2800), sm)


def codex_fly_cut_arcs(shape, seed, sm, **kwargs):
    """Machined fly-cut arcs with small overlapping cutter passes."""
    return _machined_field(shape, seed + 21, "fly_cut_arcs", "flycut")


def codex_fractal_discharge(shape, seed, sm, **kwargs):
    """Haunted corona discharge: dense branching spectral scratches."""
    return _sm_scale(_occult_field(shape, seed + 22, "fractal_discharge", "frost", 240, 3400), sm)


def codex_frosted_glass_etch(shape, seed, sm, **kwargs):
    """Frost-etched rune glass with dense micro-scratches."""
    return _sm_scale(_occult_field(shape, seed + 23, "frosted_glass_etch", "frost", 320, 2400), sm)


def codex_fungal_network(shape, seed, sm, **kwargs):
    """Mycelium spirit-root network: fine organic branching, not blob noise."""
    return _sm_scale(_occult_field(shape, seed + 24, "fungal_network", "copper", 160, 3600), sm)


def codex_gold_leaf_torn(shape, seed, sm, **kwargs):
    """Kintsugi shrine leaf: torn cultural gold seams and tiny foil islands."""
    h, w = shape
    rng = np.random.default_rng(int(seed) + 17025)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.22, 0.34, 0.20, 0.07)
    if _CV2_OK:
        for _ in range(int(np.clip(1500 * (h * w / (2048 * 2048)), 260, 1500))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rw = max(2, int(rng.uniform(4, 12) * sc))
            rh = max(1, int(rng.uniform(2, 7) * sc))
            pts = _star(cx, cy, rw, max(1, rh), int(rng.integers(3, 6)), rng.uniform(0, math.pi))
            _cv2.fillPoly(M, [pts], float(rng.uniform(0.68, 0.98)), lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [pts], float(rng.uniform(0.48, 0.86)), lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts], float(rng.uniform(0.08, 0.34)), lineType=_cv2.LINE_AA)
        for _ in range(int(np.clip(520 * (h * w / (2048 * 2048)), 120, 520))):
            x = int(rng.integers(0, w)); y = int(rng.integers(0, h))
            for _seg in range(int(rng.integers(3, 8))):
                length = float(rng.uniform(8, 22) * sc)
                ang = float(rng.choice([0, math.pi / 4, -math.pi / 4, math.pi / 2]) + rng.normal(0, 0.22))
                x2 = int(np.clip(x + math.cos(ang) * length, 0, w - 1))
                y2 = int(np.clip(y + math.sin(ang) * length, 0, h - 1))
                _cv2.line(M, (x, y), (x2, y2), float(rng.uniform(0.72, 0.99)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x, y), (x2, y2), float(rng.uniform(0.46, 0.82)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x, y), (x2, y2), float(rng.uniform(0.08, 0.38)), 1, lineType=_cv2.LINE_AA)
                x, y = x2, y2
    _scatter_pins(M, R, CC, rng, 2600)
    return _finish("gold_leaf_torn", M, R, CC, sm)
