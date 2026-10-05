"""RATE10 Codex first-strike rebuilds for weak spec overlays.

SPB-RATE10 tick 2026-05-26-codex-1.
Owner verdict snippets driving this file:
  - "the finishes don't do what they say"
  - "fine details... clean for the most part"
  - "a ton of random noise... bullshit people would use as a finish"
  - jaguar_rosette 4/REBUILD, pangolin_armor 4/REBUILD,
    raptor_feather 3/REBUILD, hellfire_crackle 1/REBUILD,
    engine_turn_starburst 3/REBUILD, guilloche_waves 3/REBUILD,
    heat_discoloration 3/REBUILD, forged_carbon_chip 3/REBUILD.

Metric movement is recorded in CHANGELOG after re-render because the before
snapshot comes from _rate10_thumbs/manifest.json and the after snapshot is
created by scripts/render_rate10_thumbs.py.
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


def _scale(shape):
    return max(min(shape) / 2048.0, 0.25)


def _grid(h, w):
    """Bit-identical, allocation-light replacement for
    ``yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)``.

    ``np.mgrid`` materialises two full HxW int64 arrays (~67 MB each at 2048)
    and then ``.astype(float32)`` allocates two more — ~400 ms of pure
    bookkeeping at 2048. Returning 1-D broadcast operands (a column vector for
    rows, a row vector for columns) lets every downstream arithmetic
    expression (``xx + yy * 0.37`` etc.) broadcast to the exact same float32
    result without the intermediate full grids. Any expression that combines
    ``xx`` and ``yy`` yields a full HxW float32 array identical to the old
    code; ``np.array_equal`` verified. Perf-only, look-neutral.
    """
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    return yy, xx


def _base(shape, seed, m=0.22, r=0.56, c=0.24, span=0.10):
    nm = _normalize(multi_scale_noise(shape, [2.0, 5.0, 11.0], [0.48, 0.32, 0.20], seed + 11))
    nr = _normalize(multi_scale_noise(shape, [2.4, 6.0, 13.0], [0.46, 0.32, 0.22], seed + 17))
    nc = _normalize(multi_scale_noise(shape, [2.8, 6.8, 15.0], [0.44, 0.32, 0.24], seed + 23))
    return (
        (m + (nm - 0.5) * span).astype(np.float32),
        (r + (nr - 0.5) * span).astype(np.float32),
        (c + (nc - 0.5) * span).astype(np.float32),
    )


def _finish(name, M, R, CC, sm):
    # Bit-identical to the previous
    #   np.stack([clip(M),clip(R),clip(CC)], axis=-1).astype(float32)
    # but clips each channel directly into a preallocated float32 HxWx3 buffer
    # instead of allocating 3 clipped temporaries + a concatenating stack +
    # a redundant astype copy. Perf-only; np.array_equal verified across
    # sm in {0.7, 1.0, 1.4}. Shared by this file's codex_* fns and the
    # rate10_codex_loop*/reference_rescue families, so all benefit.
    out = np.empty((M.shape[0], M.shape[1], 3), dtype=np.float32)
    np.clip(M, 0, 1, out=out[..., 0])
    np.clip(R, 0, 1, out=out[..., 1])
    np.clip(CC, 0, 1, out=out[..., 2])
    return _validate_spec_output(_sm_scale(out, sm), name)


def _dot_noise(M, R, CC, rng, density=1800, span=0.16):
    h, w = M.shape
    n = int(np.clip(h * w / density, 180, 6000))
    y = rng.integers(0, h, n)
    x = rng.integers(0, w, n)
    M[y, x] = np.clip(M[y, x] + rng.uniform(-span, span, n).astype(np.float32), 0, 1)
    R[y, x] = np.clip(R[y, x] + rng.uniform(-span, span, n).astype(np.float32), 0, 1)
    CC[y, x] = np.clip(CC[y, x] + rng.uniform(-span, span, n).astype(np.float32), 0, 1)


def _line_distance(coord, period, width, phase=0.0):
    d = np.abs(np.mod(coord + phase, period) - period * 0.5)
    return np.clip(1.0 - d / max(width, 1e-6), 0.0, 1.0).astype(np.float32)


def _star(cx, cy, r_outer, r_inner, points, rot=0.0):
    pts = []
    for i in range(points * 2):
        rr = r_outer if i % 2 == 0 else r_inner
        a = rot + i * math.pi / points
        pts.append([int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr)])
    return np.asarray(pts, dtype=np.int32)


def codex_jaguar_rosette(shape, seed, sm, **kwargs):
    """Dense leopard/jaguar rosettes: grouped broken rings, not random dots."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99101)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.34, 0.42, 0.26, 0.06)
    if _CV2_OK:
        pitch = max(14, int(56 * sc))
        for y in range(-pitch, h + pitch, pitch):
            for x in range(-pitch, w + pitch, pitch):
                cx = int(x + rng.uniform(-5, 5) * sc)
                cy = int(y + rng.uniform(-5, 5) * sc)
                if not (0 <= cx < w and 0 <= cy < h):
                    continue
                rad = max(4, int(rng.uniform(16, 24) * sc))
                spots = int(rng.integers(5, 8))
                ring_palette = rng.choice([0, 1, 2])
                if ring_palette == 0:
                    m0, r0, c0 = 0.12, 0.24, 0.12
                elif ring_palette == 1:
                    m0, r0, c0 = 0.20, 0.32, 0.18
                else:
                    m0, r0, c0 = 0.52, 0.44, 0.28
                for k in range(spots):
                    a = rng.uniform(0, 2 * math.pi) + k * 2 * math.pi / spots
                    px = int(cx + math.cos(a) * rad)
                    py = int(cy + math.sin(a) * rad * rng.uniform(0.72, 1.18))
                    rr = max(1, int(rng.uniform(4.0, 7.0) * sc))
                    jitter = float(rng.uniform(-0.035, 0.035))
                    _cv2.ellipse(M, (px, py), (rr + 1, rr), rng.uniform(0, 180), 0, 360, m0, -1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(R, (px, py), (rr + 1, rr), rng.uniform(0, 180), 0, 360, np.clip(r0 + jitter, 0, 1), -1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(CC, (px, py), (rr + 1, rr), rng.uniform(0, 180), 0, 360, np.clip(c0 - jitter, 0, 1), -1, lineType=_cv2.LINE_AA)
                if rng.random() < 0.70:
                    _cv2.circle(M, (cx, cy), max(1, int(4.0 * sc)), 0.58, -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(R, (cx, cy), max(1, int(4.0 * sc)), 0.44, -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (cx, cy), max(1, int(4.0 * sc)), 0.30, -1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 5000, 0.035)
    return _finish("jaguar_rosette", M, R, CC, sm)


def codex_pangolin_armor(shape, seed, sm, **kwargs):
    """Offset rows of small overlapping armor scales with bright tips."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99102)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.28, 0.46, 0.20, 0.08)
    if _CV2_OK:
        pw = max(7, int(30 * sc))
        ph = max(5, int(22 * sc))
        for row, y in enumerate(range(-ph, h + ph, ph)):
            offset = (pw // 2) if row % 2 else 0
            for x in range(-pw, w + pw, pw):
                cx = x + offset + int(rng.uniform(-2, 2) * sc)
                cy = y + int(rng.uniform(-2, 2) * sc)
                pts = np.array([
                    [cx, cy - ph // 2],
                    [cx + pw // 2, cy],
                    [cx + max(1, pw // 4), cy + ph // 2],
                    [cx - max(1, pw // 4), cy + ph // 2],
                    [cx - pw // 2, cy],
                ], dtype=np.int32)
                tier = float(rng.choice([0.26, 0.34, 0.42, 0.52, 0.64, 0.76]))
                jitter = float(rng.uniform(-0.035, 0.035))
                m = float(np.clip(tier + 0.06 + jitter, 0, 1))
                r = float(np.clip(tier - 0.02 - jitter * 0.5, 0, 1))
                c = float(np.clip(tier - 0.10 + jitter * 0.4, 0, 1))
                _cv2.fillPoly(M, [pts], m, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts], r, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], c, lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [pts], True, min(0.98, m + 0.20), 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx, cy - ph // 2), (cx, cy + ph // 3), min(0.98, m + 0.28), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx, cy - ph // 2), (cx, cy + ph // 3), max(0.05, r - 0.16), 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 6000, 0.035)
    return _finish("pangolin_armor", M, R, CC, sm)


def codex_raptor_feather(shape, seed, sm, **kwargs):
    """Readable small feather silhouettes with shafts and barbs."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99103)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.18, 0.36, 0.18, 0.08)
    if _CV2_OK:
        spacing_x = max(7, int(30 * sc))
        spacing_y = max(8, int(34 * sc))
        flow = float(rng.uniform(-0.8, 0.8))
        for y in range(0, h + spacing_y, spacing_y):
            for x in range(0, w + spacing_x, spacing_x):
                cx = int(x + rng.uniform(-4, 4) * sc)
                cy = int(y + rng.uniform(-4, 4) * sc)
                length = max(4, int(rng.uniform(18, 30) * sc))
                half = max(2, int(length * 0.30))
                a = flow + rng.uniform(-0.22, 0.22) - math.pi / 2
                ux, uy = math.cos(a), math.sin(a)
                px, py = -uy, ux
                tip = (int(cx + ux * length), int(cy + uy * length))
                butt = (int(cx - ux * length * 0.22), int(cy - uy * length * 0.22))
                mid = (int(cx + ux * length * 0.35), int(cy + uy * length * 0.35))
                body = np.array([
                    tip,
                    [int(mid[0] + px * half), int(mid[1] + py * half)],
                    butt,
                    [int(mid[0] - px * half), int(mid[1] - py * half)],
                ], dtype=np.int32)
                tier = float(rng.choice([0.24, 0.34, 0.44, 0.56, 0.68, 0.80]))
                jitter = float(rng.uniform(-0.04, 0.04))
                m = float(np.clip(tier + 0.04 + jitter, 0, 1))
                r = float(np.clip(tier - 0.08 - jitter * 0.5, 0, 1))
                c = float(np.clip(tier - 0.12 + jitter * 0.5, 0, 1))
                _cv2.fillPoly(M, [body], m, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [body], r, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [body], c, lineType=_cv2.LINE_AA)
                _cv2.line(M, butt, tip, min(0.96, m + 0.24), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, butt, tip, min(0.90, c + 0.18), 1, lineType=_cv2.LINE_AA)
                for t in np.linspace(0.22, 0.82, 5):
                    ax = butt[0] + (tip[0] - butt[0]) * t
                    ay = butt[1] + (tip[1] - butt[1]) * t
                    bl = half * (1.05 - t * 0.55)
                    for side in (-1, 1):
                        bx = int(ax + px * bl * side + ux * bl * 0.45)
                        by = int(ay + py * bl * side + uy * bl * 0.45)
                        _cv2.line(M, (int(ax), int(ay)), (bx, by), min(0.94, m + 0.14), 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 6200, 0.035)
    return _finish("raptor_feather", M, R, CC, sm)


def codex_hellfire_crackle(shape, seed, sm, **kwargs):
    """Fine molten crack network with ember nodes and heat rims."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99104)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.08, 0.06, 0.035, 0.05)
    yy, xx = _grid(h, w)
    sc_safe = max(sc, 0.25)
    fine_cracks = np.maximum(
        _line_distance(xx + yy * 0.37, 17.0 * sc_safe, 1.3 * sc_safe, seed * 0.11),
        _line_distance(xx - yy * 0.49, 23.0 * sc_safe, 1.1 * sc_safe, seed * 0.17),
    )
    M = np.clip(M + fine_cracks * 0.68, 0, 1)
    R = np.clip(R + fine_cracks * 0.10, 0, 1)
    CC = np.clip(CC + fine_cracks * 0.06, 0, 1)
    if _CV2_OK:
        n_paths = int(np.clip(h * w / 3600, 70, 650))
        for _ in range(n_paths):
            x = float(rng.uniform(0, w))
            y = float(rng.uniform(0, h))
            a = float(rng.uniform(0, 2 * math.pi))
            steps = int(rng.integers(3, 8))
            pts = []
            for _s in range(steps):
                pts.append((int(x), int(y)))
                a += float(rng.normal(0, 0.55))
                d = float(rng.uniform(7, 18) * sc)
                x = np.clip(x + math.cos(a) * d, 0, w - 1)
                y = np.clip(y + math.sin(a) * d, 0, h - 1)
            for p0, p1 in zip(pts, pts[1:]):
                _cv2.line(M, p0, p1, float(rng.uniform(0.76, 0.99)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, p0, p1, float(rng.uniform(0.08, 0.24)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, p0, p1, float(rng.uniform(0.04, 0.18)), 1, lineType=_cv2.LINE_AA)
        n_embers = int(np.clip(h * w / 2400, 120, 900))
        for _ in range(n_embers):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(2, 5) * sc))
            _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.78, 1.00)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), rr, float(rng.uniform(0.10, 0.28)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.04, 0.16)), -1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 900, 0.12)
    return _finish("hellfire_crackle", M, R, CC, sm)


def codex_engine_turn_starburst(shape, seed, sm, **kwargs):
    """Engine-turned fields built from many small polished swirl discs."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99105)
    sc = _scale(shape)
    yy, xx = _grid(h, w)
    pitch = max(4.0, 18.0 * sc)
    cx = (np.mod(xx + (np.floor(yy / pitch) % 2.0) * pitch * 0.5, pitch) - pitch * 0.5)
    cy = (np.mod(yy, pitch) - pitch * 0.5)
    rr = np.sqrt(cx * cx + cy * cy) / max(pitch * 0.48, 1.0)
    th = np.arctan2(cy, cx)
    rings = np.clip(1.0 - np.abs(rr - 0.62) / 0.24, 0, 1)
    swirl = (np.sin(th * 9.0 + rr * 17.0 + seed * 0.013) + 1.0) * 0.5
    cut = rings * np.clip((swirl - 0.36) / 0.34, 0, 1)
    center = np.clip(1.0 - rr / 0.22, 0, 1)
    grain = _normalize(multi_scale_noise(shape, [9, 19, 39], [0.44, 0.34, 0.22], int(seed) + 405))
    M = np.clip(0.28 + cut * 0.58 + center * 0.25 + (grain - 0.5) * 0.16, 0, 1).astype(np.float32)
    R = np.clip(0.48 - cut * 0.34 - center * 0.12 + (grain - 0.5) * 0.08, 0, 1).astype(np.float32)
    CC = np.clip(0.30 + cut * 0.44 + center * 0.20 + (grain - 0.5) * 0.14, 0, 1).astype(np.float32)
    _dot_noise(M, R, CC, rng, 3000, 0.05)
    return _finish("engine_turn_starburst", M, R, CC, sm)


def codex_guilloche_waves(shape, seed, sm, **kwargs):
    """Clean watch-dial guilloche: fine wave lattices, no crossed razor ribbons."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99106)
    yy, xx = _grid(h, w)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.26, 0.46, 0.30, 0.04)
    pitch = max(4.0, 14.0 * sc)
    amp = 9.0 * sc
    field = (yy + np.sin(xx / max(1.0, 38.0 * sc)) * amp) / pitch
    frac = np.abs((field % 1.0) - 0.5)
    line = np.clip(1.0 - frac / 0.13, 0, 1)
    field2 = (xx + np.sin(yy / max(1.0, 52.0 * sc)) * amp * 0.55) / (pitch * 1.45)
    frac2 = np.abs((field2 % 1.0) - 0.5)
    lace = np.clip(1.0 - frac2 / 0.08, 0, 1) * 0.45
    M = np.clip(M + line * 0.42 + lace * 0.28, 0, 1)
    R = np.clip(R - line * 0.26 + lace * 0.10, 0, 1)
    CC = np.clip(CC + line * 0.26 + lace * 0.36, 0, 1)
    _dot_noise(M, R, CC, rng, 3000, 0.04)
    return _finish("guilloche_waves", M, R, CC, sm)


def codex_heat_discoloration(shape, seed, sm, **kwargs):
    """Tempered metal islands with tiny weld scales, not generic blobs."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99107)
    yy, xx = _grid(h, w)
    sc = _scale(shape)
    band = (yy * 0.016 / sc + np.sin(xx * 0.010 / sc) * 1.5)
    phase = (np.sin(band) + 1.0) * 0.5
    n = _normalize(multi_scale_noise(shape, [4, 9, 18], [0.45, 0.35, 0.20], int(seed) + 700))
    M = (0.30 + phase * 0.46 + (n - 0.5) * 0.14).astype(np.float32)
    R = (0.55 - phase * 0.34 + (n - 0.5) * 0.10).astype(np.float32)
    CC = (0.22 + np.sin(band + 2.1) * 0.20 + (n - 0.5) * 0.16).astype(np.float32)
    if _CV2_OK:
        for _ in range(int(np.clip(h * w / 2600, 110, 900))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(2, 6) * sc))
            _cv2.ellipse(M, (cx, cy), (rr * 2, rr), rng.uniform(0, 180), 0, 360, float(rng.uniform(0.58, 0.96)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rr * 2, rr), rng.uniform(0, 180), 0, 360, float(rng.uniform(0.08, 0.38)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rr * 2, rr), rng.uniform(0, 180), 0, 360, float(rng.uniform(0.28, 0.80)), 1, lineType=_cv2.LINE_AA)
    return _finish("heat_discoloration", M, R, CC, sm)


def codex_spec_heat_scale(shape, seed, sm, **kwargs):
    """Fine straw-blue heat scale with no large random circles."""
    return codex_heat_discoloration(shape, int(seed) + 431, sm, **kwargs)


def codex_forged_carbon_chip(shape, seed, sm, **kwargs):
    """Dense chopped forged carbon chips with resin glints."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99108)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.14, 0.36, 0.20, 0.16)
    yy, xx = _grid(h, w)
    fiber = np.maximum(
        _line_distance(xx + yy * 0.62, 12.0 * sc, 1.1 * sc, seed * 0.19),
        _line_distance(xx - yy * 0.58, 16.0 * sc, 1.0 * sc, seed * 0.23),
    )
    M = np.clip(M + fiber * 0.20, 0, 1)
    R = np.clip(R - fiber * 0.12, 0, 1)
    CC = np.clip(CC + fiber * 0.14, 0, 1)
    if _CV2_OK:
        n = int(np.clip(h * w / 560, 450, 8000))
        for _ in range(n):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            length = max(2, int(rng.uniform(8, 22) * sc))
            width = max(1, int(rng.uniform(2, 5) * sc))
            ang = float(rng.uniform(0, math.pi))
            ux, uy = math.cos(ang), math.sin(ang)
            px, py = -uy, ux
            pts = np.array([
                [int(cx - ux * length + px * width), int(cy - uy * length + py * width)],
                [int(cx + ux * length + px * width * 0.6), int(cy + uy * length + py * width * 0.6)],
                [int(cx + ux * length - px * width), int(cy + uy * length - py * width)],
                [int(cx - ux * length - px * width * 0.5), int(cy - uy * length - py * width * 0.5)],
            ], dtype=np.int32)
            m = float(rng.choice([0.06, 0.18, 0.34, 0.56, 0.78, 0.96]))
            r = float(rng.choice([0.08, 0.18, 0.34, 0.56, 0.74]))
            c = float(rng.choice([0.05, 0.18, 0.36, 0.62, 0.86]))
            _cv2.fillPoly(M, [pts], m, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [pts], r, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts], c, lineType=_cv2.LINE_AA)
            if rng.random() < 0.45:
                _cv2.line(CC, tuple(pts[0]), tuple(pts[1]), min(0.98, c + 0.24), 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 140, 0.22)
    return _finish("forged_carbon_chip", M, R, CC, sm)


def codex_holo_prism_shift(shape, seed, sm, **kwargs):
    """Prismatic foil shards with spectral carrier lines and clean color shift."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99109)
    yy, xx = _grid(h, w)
    sc = _scale(shape)
    carrier = np.sin((xx * 0.040 + yy * 0.025) / sc)
    M = (0.26 + carrier * 0.18).astype(np.float32)
    R = (0.38 + np.sin((xx * 0.032 - yy * 0.045) / sc + 1.8) * 0.18).astype(np.float32)
    CC = (0.42 + np.sin((xx * 0.052 + yy * 0.015) / sc + 3.3) * 0.24).astype(np.float32)
    if _CV2_OK:
        for _ in range(int(np.clip(h * w / 1800, 150, 1400))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(2, int(rng.uniform(5, 14) * sc))
            rot = float(rng.uniform(0, 2 * math.pi))
            pts = _star(cx, cy, rr, max(1, rr // 2), 3, rot)
            _cv2.polylines(M, [pts], True, float(rng.uniform(0.45, 0.98)), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(R, [pts], True, float(rng.uniform(0.08, 0.55)), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [pts], True, float(rng.uniform(0.30, 0.98)), 1, lineType=_cv2.LINE_AA)
    return _finish("holo_prism_shift", M, R, CC, sm)


def codex_skull_tessellation(shape, seed, sm, **kwargs):
    """skull_tessellation.

    R6 CREATIVE SECOND-PASS 2026-05-26: ditch banned 8-tier palette and
    eliminate clone-skulls. Each skull is one of FIVE distinct DEATH-MASK
    silhouettes (plain, horned, top-hat jester, fanged, jeweled-eye)
    chosen per-cell — anti-clone mandate satisfied. Cool deep-violet
    occult substrate (composite-cool). Per-skull TIGHT ±0.05 chroma jitter
    from ONE bone-ivory base. 10-22 px per skull. HERO: 6-10 enlarged
    skulls 18-26 px with cracked-bone CC hairlines and glow-eye R-spec.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99110)
    sc = _scale(shape)
    # Cool deep-violet occult substrate (composite-cool: M=0.18, R=0.18, CC=0.36)
    M, R, CC = _base(shape, int(seed), 0.18, 0.20, 0.32, 0.05)

    # ONE bone-ivory base — tight jitter, NO 8-tier rolls
    # cap BONE_M moderate to keep canvas M-mean < 0.45 anti-magenta
    BONE_M, BONE_R, BONE_C = 0.58, 0.36, 0.34

    def _draw_skull_plain(cx, cy, rr, pM, pR, pC):
        _cv2.ellipse(M, (cx, cy - rr // 4), (rr, int(rr * 0.92)), 0, 0, 360, pM, -1, lineType=_cv2.LINE_AA)
        _cv2.ellipse(R, (cx, cy - rr // 4), (rr, int(rr * 0.92)), 0, 0, 360, pR, -1, lineType=_cv2.LINE_AA)
        _cv2.ellipse(CC, (cx, cy - rr // 4), (rr, int(rr * 0.92)), 0, 0, 360, pC, -1, lineType=_cv2.LINE_AA)
        jaw = np.array([[cx - rr // 2, cy + rr // 3], [cx + rr // 2, cy + rr // 3],
                        [cx + rr // 3, cy + rr], [cx - rr // 3, cy + rr]], dtype=np.int32)
        _cv2.fillPoly(M, [jaw], pM, lineType=_cv2.LINE_AA)
        _cv2.fillPoly(R, [jaw], pR, lineType=_cv2.LINE_AA)
        _cv2.fillPoly(CC, [jaw], pC, lineType=_cv2.LINE_AA)

    def _draw_eyes(cx, cy, rr, glow=False):
        eye = max(1, rr // 4)
        for sx in (-1, 1):
            ex = cx + sx * rr // 3
            ey = cy - rr // 4
            _cv2.circle(M, (ex, ey), eye, 0.04, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (ex, ey), eye, 0.06, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (ex, ey), eye, 0.04, -1, lineType=_cv2.LINE_AA)
            if glow:
                # bright pupil glow (mirror-R)
                _cv2.circle(R, (ex, ey), max(1, eye // 2), 0.92, -1)
                _cv2.circle(CC, (ex, ey), max(1, eye // 2), 0.78, -1)

    if _CV2_OK:
        # Larger spacing + larger skulls so silhouettes read clearly at 256²
        step = max(14, int(44 * sc))
        kings = []
        for row, y in enumerate(range(step // 2, h, step)):
            for x in range(step // 2 + (row % 2) * step // 2, w, step):
                cx = int(x + rng.uniform(-3, 3) * sc); cy = int(y + rng.uniform(-3, 3) * sc)
                if not (6 < cx < w - 6 and 8 < cy < h - 8):
                    continue
                rr = max(6, int(rng.uniform(7, 10) * sc))
                rr = min(rr, 11)
                pM = float(np.clip(BONE_M + rng.uniform(-0.05, 0.05), 0, 1))
                pR = float(np.clip(BONE_R + rng.uniform(-0.05, 0.05), 0, 1))
                pC = float(np.clip(BONE_C + rng.uniform(-0.05, 0.05), 0, 1))
                kind = int(rng.integers(0, 5))
                _draw_skull_plain(cx, cy, rr, pM, pR, pC)
                # variant accessories per kind
                if kind == 1:  # HORNED
                    # twin horns curling up-out from cranium top
                    hl = max(2, int(rr * 0.7))
                    _cv2.line(M, (cx - rr // 2, cy - rr),
                              (cx - rr - hl // 2, cy - rr - hl), pM, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(M, (cx + rr // 2, cy - rr),
                              (cx + rr + hl // 2, cy - rr - hl), pM, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, (cx - rr // 2, cy - rr),
                              (cx - rr - hl // 2, cy - rr - hl), pC, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, (cx + rr // 2, cy - rr),
                              (cx + rr + hl // 2, cy - rr - hl), pC, 1, lineType=_cv2.LINE_AA)
                elif kind == 2:  # TOP-HAT JESTER
                    # tiny crown / hat above cranium (rectangular bar)
                    htop = cy - rr - max(2, rr // 2)
                    _cv2.rectangle(M, (cx - rr // 2, htop), (cx + rr // 2, cy - rr),
                                   pM, -1, lineType=_cv2.LINE_AA)
                    _cv2.rectangle(CC, (cx - rr // 2, htop), (cx + rr // 2, cy - rr),
                                   pC, -1, lineType=_cv2.LINE_AA)
                    # brim
                    _cv2.line(M, (cx - rr, cy - rr), (cx + rr, cy - rr), pM, 1, lineType=_cv2.LINE_AA)
                elif kind == 3:  # FANGED — tiny fang downward triangles from jaw
                    for off in (-rr // 3, rr // 3):
                        fang = np.array([[cx + off - 1, cy + rr // 3],
                                         [cx + off + 1, cy + rr // 3],
                                         [cx + off, cy + rr - 1]], dtype=np.int32)
                        _cv2.fillPoly(M, [fang], pM, lineType=_cv2.LINE_AA)
                        _cv2.fillPoly(CC, [fang], pC, lineType=_cv2.LINE_AA)
                elif kind == 4:  # JEWELED-EYE — gem inset in one eye
                    _draw_eyes(cx, cy, rr, glow=False)
                    # gem accent
                    gx = cx - rr // 3
                    gy = cy - rr // 4
                    _cv2.circle(CC, (gx, gy), max(1, rr // 5), 0.95, -1)
                    _cv2.circle(R, (gx, gy), max(1, rr // 5), 0.10, -1)
                if kind != 4:
                    _draw_eyes(cx, cy, rr, glow=False)
                # nose triangle (anti-clone — only on some kinds)
                if kind in (0, 1, 3):
                    _cv2.line(M, (cx - rr // 4, cy + rr // 6),
                              (cx + rr // 4, cy + rr // 6), 0.10, 1, lineType=_cv2.LINE_AA)
                kings.append((cx, cy, rr, kind))

        # HERO — 6-10 enlarged skulls with cracked-bone CC hairlines + glow eyes
        n_hero = int(rng.integers(6, 11))
        if kings:
            picks = rng.choice(len(kings), size=min(n_hero, len(kings)), replace=False)
            for idx in picks:
                cx, cy, rr0, kind = kings[idx]
                rr = max(8, min(int(rr0 * 1.6), 13))
                pM = float(np.clip(BONE_M + 0.10 + rng.uniform(-0.04, 0.04), 0, 1))
                pR = float(np.clip(BONE_R - 0.08 + rng.uniform(-0.04, 0.04), 0, 1))
                pC = float(np.clip(BONE_C + 0.16 + rng.uniform(-0.04, 0.04), 0, 1))
                _draw_skull_plain(cx, cy, rr, pM, pR, pC)
                _draw_eyes(cx, cy, rr, glow=True)
                # cracked-bone hairlines (3-5 short arcs)
                for _ in range(int(rng.integers(3, 6))):
                    a1 = float(rng.uniform(0, 2 * np.pi))
                    a2 = a1 + float(rng.uniform(0.5, 1.6))
                    x0 = int(cx + np.cos(a1) * rr * 0.6)
                    y0 = int(cy - rr // 4 + np.sin(a1) * rr * 0.6)
                    x1 = int(cx + np.cos(a2) * rr * 0.6)
                    y1 = int(cy - rr // 4 + np.sin(a2) * rr * 0.6)
                    _cv2.line(M, (x0, y0), (x1, y1), 0.18, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, (x0, y0), (x1, y1), 0.20, 1, lineType=_cv2.LINE_AA)

    return _finish("skull_tessellation", M, R, CC, sm)


def codex_voodoo_bone_fetish(shape, seed, sm, **kwargs):
    """voodoo_bone_fetish.

    R6 CREATIVE SECOND-PASS 2026-05-26: ditch the banned 8-tier palette
    and rebuild as STRUNG-BONE FETISH JEWELRY — dangling finger-bone
    charms hung on CATENARY ROPE CURVES (math motif: hyperbolic cosine
    sag) with bead-knot clusters. Storm-grey weathered substrate
    (composite-cool). Per-feature TIGHT ±0.05 chroma jitter from ONE
    bone-ivory base. 4 feature tiers: catenary cords, finger bones,
    bead knots, sigil tags. All features 6-22 px.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99111)
    sc = _scale(shape)
    # Storm-grey weathered fetish-altar substrate (composite-dark cool)
    M, R, CC = _base(shape, int(seed), 0.16, 0.20, 0.20, 0.06)

    # ONE bone-ivory palette base (tight jitter, NO 8-tier rolls)
    BONE_M, BONE_R, BONE_C = 0.72, 0.38, 0.34  # weathered ivory
    CORD_M, CORD_R, CORD_C = 0.32, 0.58, 0.18  # dark hemp cord
    BEAD_M, BEAD_R, BEAD_C = 0.58, 0.30, 0.42  # blood-bead

    if _CV2_OK:
        # === TIER 1: 7-12 CATENARY CORD STRANDS spanning canvas (denser) ===
        # cosh-based sag curves — real hanging rope physics
        n_cords = int(rng.integers(7, 13))
        cords_data = []
        for ci in range(n_cords):
            # spread cords vertically to cover whole canvas — bias toward
            # different y-bands so cords don't pile up in the middle
            band = (ci + 0.5) / max(1, n_cords)  # 0..1
            ay = int(band * h + rng.uniform(-h * 0.08, h * 0.08))
            by = int(band * h + rng.uniform(-h * 0.10, h * 0.10))
            ay = max(8, min(h - 16, ay))
            by = max(8, min(h - 16, by))
            ax = int(rng.uniform(0, w * 0.20))
            bx = int(rng.uniform(w * 0.80, w))
            # cosh sag depth proportional to span
            span = max(1, bx - ax)
            sag = float(rng.uniform(0.08, 0.22)) * span
            n_pts = max(16, span // 6)
            ts = np.linspace(-1.5, 1.5, n_pts)
            cosh_vals = (np.cosh(ts) - 1.0) / (np.cosh(1.5) - 1.0)  # 0..1 V-shape
            xs = np.linspace(ax, bx, n_pts).astype(np.int32)
            ys = (np.linspace(ay, by, n_pts) + cosh_vals * sag).astype(np.int32)
            ys = np.clip(ys, 1, h - 2)
            pts = np.stack([xs, ys], axis=1).astype(np.int32)
            cM = float(np.clip(CORD_M + rng.uniform(-0.05, 0.05), 0, 1))
            cR = float(np.clip(CORD_R + rng.uniform(-0.05, 0.05), 0, 1))
            cC = float(np.clip(CORD_C + rng.uniform(-0.05, 0.05), 0, 1))
            cord_w = max(1, int(2 * sc))
            _cv2.polylines(M, [pts], False, cM, cord_w, lineType=_cv2.LINE_AA)
            _cv2.polylines(R, [pts], False, cR, cord_w, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [pts], False, cC, cord_w, lineType=_cv2.LINE_AA)
            cords_data.append(pts)

        # === TIER 2: BEAD KNOTS along each cord (5-12 per cord) ===
        for cord_pts in cords_data:
            n_beads = int(rng.integers(5, 13))
            if len(cord_pts) < 2:
                continue
            idxs = np.linspace(2, len(cord_pts) - 3, n_beads).astype(int)
            for ii in idxs:
                bx, by = int(cord_pts[ii][0]), int(cord_pts[ii][1])
                br = max(2, int(rng.uniform(2.0, 3.5) * sc))
                br = min(br, 4)
                bM = float(np.clip(BEAD_M + rng.uniform(-0.05, 0.05), 0, 1))
                bR = float(np.clip(BEAD_R + rng.uniform(-0.05, 0.05), 0, 1))
                bC = float(np.clip(BEAD_C + rng.uniform(-0.05, 0.05), 0, 1))
                _cv2.circle(M, (bx, by), br, bM, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (bx, by), br, bR, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (bx, by), br, bC, -1, lineType=_cv2.LINE_AA)
                # bright spec point on bead
                _cv2.circle(M, (bx - 1, by - 1), 1, min(0.95, bM + 0.25), -1)
                _cv2.circle(CC, (bx - 1, by - 1), 1, min(0.95, bC + 0.30), -1)

        # === TIER 3: DANGLING FINGER-BONE CHARMS hung from cords ===
        # tapered dumbbell silhouettes (8-18 px long). Hang DOWN with gravity.
        for cord_pts in cords_data:
            n_bones = int(rng.integers(8, 16))
            if len(cord_pts) < 2:
                continue
            idxs = np.linspace(1, len(cord_pts) - 2, n_bones).astype(int)
            for ii in idxs:
                hx, hy = int(cord_pts[ii][0]), int(cord_pts[ii][1])
                length = max(6, int(rng.uniform(8, 16) * sc))
                length = min(length, 16)
                # bone hangs down with slight tilt
                tilt = float(rng.uniform(-0.30, 0.30))
                tx = max(2, min(w - 2, hx + int(np.sin(tilt) * length)))
                ty = max(2, min(h - 2, hy + int(np.cos(tilt) * length)))
                bM = float(np.clip(BONE_M + rng.uniform(-0.05, 0.05), 0, 1))
                bR = float(np.clip(BONE_R + rng.uniform(-0.05, 0.05), 0, 1))
                bC = float(np.clip(BONE_C + rng.uniform(-0.05, 0.05), 0, 1))
                # bone shaft
                _cv2.line(M, (hx, hy + 1), (tx, ty), bM, max(1, int(1.5 * sc)), lineType=_cv2.LINE_AA)
                _cv2.line(R, (hx, hy + 1), (tx, ty), bR, max(1, int(1.5 * sc)), lineType=_cv2.LINE_AA)
                _cv2.line(CC, (hx, hy + 1), (tx, ty), bC, max(1, int(1.5 * sc)), lineType=_cv2.LINE_AA)
                # knuckle bulge top
                _cv2.circle(M, (hx, hy + 1), max(1, int(1.5 * sc)),
                            min(0.95, bM + 0.10), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (hx, hy + 1), max(1, int(1.5 * sc)),
                            min(0.95, bC + 0.10), -1, lineType=_cv2.LINE_AA)
                # knuckle bulge bottom (slightly larger)
                _cv2.circle(M, (tx, ty), max(2, int(2 * sc)),
                            min(0.95, bM + 0.10), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (tx, ty), max(2, int(2 * sc)),
                            min(0.95, bC + 0.15), -1, lineType=_cv2.LINE_AA)
                # bright keel highlight along bone
                _cv2.line(M, (hx, hy + 1), (tx, ty), min(0.96, bM + 0.18), 1, lineType=_cv2.LINE_AA)

        # === TIER 4: SCATTERED SIGIL TAGS (sub-feature 4-8 px crosses/X) ===
        n_tag = int(np.clip(140 * sc * sc, 80, 240))
        for _ in range(n_tag):
            tx = int(rng.integers(4, w - 4))
            ty = int(rng.integers(4, h - 4))
            tsz = max(2, int(rng.uniform(2, 4) * sc))
            tsz = min(tsz, 4)
            tM = float(np.clip(BONE_M - 0.15 + rng.uniform(-0.05, 0.05), 0, 1))
            tR = float(np.clip(BONE_R + rng.uniform(-0.05, 0.05), 0, 1))
            tC = float(np.clip(BONE_C - 0.06 + rng.uniform(-0.05, 0.05), 0, 1))
            sigil_kind = rng.integers(0, 4)
            if sigil_kind == 0:  # cross
                _cv2.line(M, (tx - tsz, ty), (tx + tsz, ty), tM, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (tx, ty - tsz), (tx, ty + tsz), tM, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (tx - tsz, ty), (tx + tsz, ty), tC, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (tx, ty - tsz), (tx, ty + tsz), tC, 1, lineType=_cv2.LINE_AA)
            elif sigil_kind == 1:  # X
                _cv2.line(M, (tx - tsz, ty - tsz), (tx + tsz, ty + tsz), tM, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (tx + tsz, ty - tsz), (tx - tsz, ty + tsz), tM, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (tx - tsz, ty - tsz), (tx + tsz, ty + tsz), tR, 1, lineType=_cv2.LINE_AA)
            elif sigil_kind == 2:  # tiny circle (binding-ring)
                _cv2.circle(M, (tx, ty), tsz, tM, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (tx, ty), tsz, tC, 1, lineType=_cv2.LINE_AA)
            else:  # triangle (warding-rune)
                tri = np.array([[tx, ty - tsz], [tx - tsz, ty + tsz], [tx + tsz, ty + tsz]], dtype=np.int32)
                _cv2.polylines(M, [tri], True, tM, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [tri], True, tC, 1, lineType=_cv2.LINE_AA)

    _dot_noise(M, R, CC, rng, 60, 0.20)
    return _finish("voodoo_bone_fetish", M, R, CC, sm)


def codex_voodoo_sigil_field(shape, seed, sm, **kwargs):
    """Cleaner dense sigil field with repeated usable dark-magic icons."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99112)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.20, 0.64, 0.20, 0.14)
    yy, xx = _grid(h, w)
    ritual_grid = np.maximum.reduce([
        _line_distance(xx + yy * 0.33, 18.0 * sc, 1.0 * sc, seed * 0.41),
        _line_distance(xx - yy * 0.41, 24.0 * sc, 1.0 * sc, seed * 0.43),
        # yy alone is a (h,1) broadcast operand under _grid; expand to full
        # (h,w) so np.maximum.reduce sees matching shapes (bit-identical to
        # the old np.mgrid full-grid yy).
        _line_distance(np.broadcast_to(yy, (h, w)), 31.0 * sc, 1.0 * sc, seed * 0.47),
    ])
    M = np.clip(M + ritual_grid * 0.30, 0, 1)
    R = np.clip(R - ritual_grid * 0.20, 0, 1)
    CC = np.clip(CC + ritual_grid * 0.30, 0, 1)
    if _CV2_OK:
        for _ in range(int(np.clip(h * w / 1250, 220, 2200))):
            cx = int(rng.integers(5, max(6, w - 5)))
            cy = int(rng.integers(5, max(6, h - 5)))
            rr = max(2, int(rng.uniform(5, 11) * sc))
            m = float(rng.choice([0.36, 0.52, 0.68, 0.84, 0.96]))
            r = float(rng.choice([0.08, 0.20, 0.34, 0.52]))
            c = float(rng.choice([0.12, 0.32, 0.56, 0.84]))
            kind = int(rng.integers(0, 4))
            if kind == 0:
                pts = _star(cx, cy, rr, max(1, rr // 2), 5, rng.uniform(0, math.pi))
                _cv2.polylines(M, [pts], True, m, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [pts], True, r, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [pts], True, c, 1, lineType=_cv2.LINE_AA)
            elif kind == 1:
                _cv2.circle(M, (cx, cy), rr, m, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx - rr, cy), (cx + rr, cy), m, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx, cy - rr), (cx, cy + rr), m, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), rr, c, 1, lineType=_cv2.LINE_AA)
            elif kind == 2:
                _cv2.ellipse(M, (cx, cy), (rr, max(1, rr // 2)), rng.uniform(0, 180), 0, 360, m, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (cx, cy), max(1, rr // 3), m, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), max(1, rr // 3), c, -1, lineType=_cv2.LINE_AA)
            else:
                _cv2.line(M, (cx, cy - rr), (cx, cy + rr), m, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx - rr // 2, cy + rr // 3), (cx + rr // 2, cy + rr // 3), m, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx, cy - rr), (cx, cy + rr), c, 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 76, 0.32)
    return _finish("voodoo_sigil_field", M, R, CC, sm)


def codex_razor_wire_coil(shape, seed, sm, **kwargs):
    """Taut diagonal razor-wire lanes with tiny triangular barbs."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99201)
    sc = _scale(shape)
    yy, xx = _grid(h, w)
    M, R, CC = _base(shape, int(seed), 0.18, 0.22, 0.18, 0.07)
    lane = np.maximum(
        _line_distance(xx - yy * 0.55, 92.0 * sc, 1.4 * sc, seed * 0.13),
        _line_distance(xx - yy * 0.55 + 5.0 * sc, 92.0 * sc, 1.1 * sc, seed * 0.19),
    )
    shadow = _line_distance(xx - yy * 0.55 + 8.0 * sc, 92.0 * sc, 1.0 * sc, seed * 0.13)
    barb_seed = np.maximum(
        _line_distance(xx + yy * 0.20, 19.0 * sc, 1.1 * sc, seed * 0.29),
        _line_distance(xx + yy * 0.20 + 7.0 * sc, 19.0 * sc, 1.1 * sc, seed * 0.31),
    )
    barbs = lane * barb_seed
    M = np.clip(M + lane * 0.54 + barbs * 0.62 - shadow * 0.10, 0, 1)
    R = np.clip(R + lane * 0.10 + barbs * 0.06 + shadow * 0.04, 0, 1)
    CC = np.clip(CC + lane * 0.44 + barbs * 0.52, 0, 1)
    if _CV2_OK:
        for c in np.arange(-h * 0.55, w + 92.0 * sc, 92.0 * sc):
            for x0 in np.arange(0, w, 28.0 * sc):
                y0 = (x0 - c) / 0.55
                if not (2 <= y0 < h - 2):
                    continue
                x0i = int(x0); y0i = int(y0)
                barb = max(2, int(5 * sc))
                # Paired triangular cuts on alternating sides of the wire.
                side = -1 if int((x0 / max(1.0, 28.0 * sc))) % 2 else 1
                p1 = (int(x0i + 4 * sc), int(y0i + 2 * sc))
                p2 = (int(x0i + side * barb), int(y0i - side * barb))
                _cv2.line(M, (x0i, y0i), p1, 0.86, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x0i, y0i), p1, 0.72, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (x0i, y0i), p2, 0.94, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x0i, y0i), p2, 0.80, 1, lineType=_cv2.LINE_AA)
        # Small intermittent red warning wraps, not big decorative curls.
        for _ in range(int(np.clip(h * w / 36000, 18, 160))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(2, int(rng.uniform(4, 8) * sc))
            _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.50, 0.80)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), rr, float(rng.uniform(0.18, 0.38)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.10, 0.28)), 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 1800, 0.05)
    return _finish("razor_wire_coil", M, R, CC, sm)


def codex_nordic_rune_field(shape, seed, sm, **kwargs):
    """Small etched runes in icy rows and binding lines, not neon poster glyphs."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99202)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.16, 0.22, 0.22, 0.08)
    if _CV2_OK:
        step = max(8, int(28 * sc))
        for y in range(step // 2, h, step):
            for x in range(step // 2, w, step):
                if rng.random() < 0.18:
                    continue
                cx = int(x + rng.uniform(-4, 4) * sc)
                cy = int(y + rng.uniform(-4, 4) * sc)
                sz = max(3, int(rng.uniform(7, 13) * sc))
                m = float(rng.uniform(0.48, 0.88))
                r = float(rng.uniform(0.12, 0.30))
                c = float(rng.uniform(0.38, 0.78))
                kind = int(rng.integers(0, 6))
                # Stem
                _cv2.line(M, (cx, cy - sz), (cx, cy + sz), m, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx, cy - sz), (cx, cy + sz), r, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx, cy - sz), (cx, cy + sz), c, 1, lineType=_cv2.LINE_AA)
                if kind in (0, 1, 2):
                    _cv2.line(M, (cx, cy - sz // 2), (cx + sz, cy - sz), m, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, (cx, cy - sz // 2), (cx + sz, cy - sz), c, 1, lineType=_cv2.LINE_AA)
                if kind in (1, 3, 4):
                    _cv2.line(M, (cx, cy), (cx + sz, cy + sz // 2), m, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, (cx, cy), (cx + sz, cy + sz // 2), c, 1, lineType=_cv2.LINE_AA)
                if kind in (2, 4, 5):
                    _cv2.line(M, (cx - sz // 2, cy + sz // 2), (cx + sz // 2, cy - sz // 2), m, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, (cx - sz // 2, cy + sz // 2), (cx + sz // 2, cy - sz // 2), c, 1, lineType=_cv2.LINE_AA)
        for _ in range(int(np.clip(h * w / 70000, 10, 90))):
            x0 = int(rng.integers(0, w)); y0 = int(rng.integers(0, h))
            x1 = int(np.clip(x0 + rng.uniform(-80, 80) * sc, 0, w - 1))
            y1 = int(np.clip(y0 + rng.uniform(-80, 80) * sc, 0, h - 1))
            _cv2.line(M, (x0, y0), (x1, y1), 0.34, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), 0.52, 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 2200, 0.06)
    return _finish("nordic_rune_field", M, R, CC, sm)


def codex_snake_scale_diamond(shape, seed, sm, **kwargs):
    """Tight diamond snake scales with no macro blobs."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99203)
    sc = _scale(shape)
    yy, xx = _grid(h, w)
    M, R, CC = _base(shape, int(seed), 0.22, 0.20, 0.18, 0.07)
    diamond = np.maximum(
        _line_distance(xx + yy, 18.0 * sc, 1.0 * sc, seed * 0.17),
        _line_distance(xx - yy, 18.0 * sc, 1.0 * sc, seed * 0.23),
    )
    belly = _line_distance(yy + np.sin(xx / max(1.0, 46.0 * sc)) * 6.0 * sc, 72.0 * sc, 10.0 * sc, seed)
    M = np.clip(M + diamond * 0.32 + belly * 0.10, 0, 1)
    R = np.clip(R + diamond * 0.05 + belly * 0.04, 0, 1)
    CC = np.clip(CC + diamond * 0.22 + belly * 0.06, 0, 1)
    _dot_noise(M, R, CC, rng, 1600, 0.06)
    return _finish("snake_scale_diamond", M, R, CC, sm)


def codex_spec_mesh_perforated(shape, seed, sm, **kwargs):
    """Clean perforated metal sheet: organized holes, restrained channel color."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99204)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.34, 0.24, 0.30, 0.04)
    if _CV2_OK:
        pitch = max(7, int(24 * sc))
        rad = max(2, int(6 * sc))
        for row, y in enumerate(range(pitch // 2, h, pitch)):
            offset = pitch // 2 if row % 2 else 0
            for x in range(pitch // 2 + offset, w, pitch):
                _cv2.circle(M, (x, y), rad, 0.06, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (x, y), rad, 0.12, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (x, y), rad, 0.08, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (x, y), rad + 1, 0.72, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (x, y), rad + 1, 0.62, 1, lineType=_cv2.LINE_AA)
    _yy, _xx = _grid(h, w)
    brushed = _line_distance(_xx + _yy * 0.08, 13.0 * sc, 0.8 * sc, seed)
    M = np.clip(M + brushed * 0.10, 0, 1)
    R = np.clip(R + brushed * 0.03, 0, 1)
    _dot_noise(M, R, CC, rng, 3500, 0.035)
    return _finish("spec_mesh_perforated", M, R, CC, sm)


def codex_brushed_diagonal(shape, seed, sm, **kwargs):
    """One disciplined diagonal brushed grain with fine damascus undertone."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99205)
    sc = _scale(shape)
    yy, xx = _grid(h, w)
    carrier = xx + yy * 0.82 + np.sin((xx - yy) / max(1.0, 70.0 * sc)) * 4.0 * sc
    hair = _line_distance(carrier, 9.0 * sc, 0.9 * sc, seed)
    water = _line_distance(carrier + np.sin(yy / max(1.0, 52.0 * sc)) * 9.0 * sc, 44.0 * sc, 1.8 * sc, seed * 0.4)
    M = np.clip(0.34 + hair * 0.40 + water * 0.18, 0, 1).astype(np.float32)
    R = np.clip(0.26 + hair * 0.08 + water * 0.05, 0, 1).astype(np.float32)
    CC = np.clip(0.34 + hair * 0.30 + water * 0.16, 0, 1).astype(np.float32)
    _dot_noise(M, R, CC, rng, 2600, 0.04)
    return _finish("brushed_diagonal", M, R, CC, sm)


def codex_hairline_polish(shape, seed, sm, **kwargs):
    """Calm stainless hairlines: dense single-direction polish, no scribbles."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99206)
    sc = _scale(shape)
    yy, xx = _grid(h, w)
    phase = yy + np.sin(xx / max(1.0, 96.0 * sc)) * 2.0 * sc
    hair = _line_distance(phase, 7.0 * sc, 0.72 * sc, seed)
    fine = _line_distance(phase + xx * 0.04, 15.0 * sc, 0.45 * sc, seed * 0.37)
    M = np.clip(0.30 + hair * 0.28 + fine * 0.14, 0, 1).astype(np.float32)
    R = np.clip(0.25 + hair * 0.06 + fine * 0.04, 0, 1).astype(np.float32)
    CC = np.clip(0.30 + hair * 0.20 + fine * 0.12, 0, 1).astype(np.float32)
    _dot_noise(M, R, CC, rng, 5000, 0.025)
    return _finish("hairline_polish", M, R, CC, sm)


def codex_hand_polished(shape, seed, sm, **kwargs):
    """Overlapping DA/buffer swirl marks, clean enough for show-car polish."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99207)
    sc = _scale(shape)
    yy, xx = _grid(h, w)
    M, R, CC = _base(shape, int(seed), 0.28, 0.24, 0.30, 0.04)
    pitch = max(10.0, 42.0 * sc)
    cx = np.mod(xx + (np.floor(yy / pitch) % 2.0) * pitch * 0.5, pitch) - pitch * 0.5
    cy = np.mod(yy, pitch) - pitch * 0.5
    rr = np.sqrt(cx * cx + cy * cy) / max(1.0, pitch * 0.42)
    th = np.arctan2(cy, cx)
    arcs = np.clip(1.0 - np.abs(rr - 0.72) / 0.18, 0, 1) * np.clip((np.sin(th * 5.0 + rr * 13.0) + 0.2) / 1.2, 0, 1)
    M = np.clip(M + arcs * 0.42, 0, 1)
    R = np.clip(R + arcs * 0.06, 0, 1)
    CC = np.clip(CC + arcs * 0.34, 0, 1)
    _dot_noise(M, R, CC, rng, 3500, 0.03)
    return _finish("hand_polished", M, R, CC, sm)


def codex_spec_faceted_diamond(shape, seed, sm, **kwargs):
    """Tight rhombus diamond tessellation with many small bright facets."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99208)
    sc = _scale(shape)
    yy, xx = _grid(h, w)
    base = _normalize(multi_scale_noise(shape, [4, 10, 22], [0.45, 0.33, 0.22], int(seed) + 808))
    grid = np.maximum(
        _line_distance(xx + yy, 30.0 * sc, 1.15 * sc, seed * 0.17),
        _line_distance(xx - yy, 30.0 * sc, 1.15 * sc, seed * 0.23),
    )
    facet = _line_distance(xx * 0.35 + yy * 0.12, 17.0 * sc, 0.9 * sc, seed * 0.31)
    M = np.clip(0.20 + base * 0.22 + grid * 0.52 + facet * 0.18, 0, 1).astype(np.float32)
    R = np.clip(0.34 - grid * 0.18 + base * 0.12, 0, 1).astype(np.float32)
    CC = np.clip(0.30 + grid * 0.48 + facet * 0.26, 0, 1).astype(np.float32)
    _dot_noise(M, R, CC, rng, 2200, 0.06)
    return _finish("spec_faceted_diamond", M, R, CC, sm)


def codex_chainmail_armor(shape, seed, sm, **kwargs):
    """Interlocked chainmail rings: clear armor identity at race-car scale."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99209)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.22, 0.24, 0.23, 0.04)
    if _CV2_OK:
        step_x = max(7, int(28 * sc))
        step_y = max(6, int(22 * sc))
        rad = max(3, int(9 * sc))
        for row, y in enumerate(range(step_y // 2, h, step_y)):
            offset = step_x // 2 if row % 2 else 0
            for x in range(step_x // 2 + offset, w, step_x):
                tier = float(rng.choice([0.38, 0.48, 0.58, 0.68, 0.80, 0.92]))
                rx = (rad, max(2, rad // 2))
                ry = (max(2, rad // 2), rad)
                _cv2.ellipse(M, (x + 1, y + 1), rx, 0, 0, 360, 0.12, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (x + 1, y + 1), rx, 0, 0, 360, 0.14, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (x + 1, y + 1), rx, 0, 0, 360, 0.13, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (x, y), rx, 0, 0, 360, min(0.98, tier + 0.04), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (x, y), rx, 0, 0, 360, min(0.95, tier + 0.02), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (x, y), rx, 0, 0, 360, min(0.96, tier + 0.06), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (x, y), ry, 0, 0, 360, tier * 0.78, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (x, y), ry, 0, 0, 360, tier * 0.82, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (x, y), ry, 0, 0, 360, tier * 0.80, 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 2800, 0.04)
    return _finish("chainmail_armor", M, R, CC, sm)


def codex_dragon_scale_macro(shape, seed, sm, **kwargs):
    """Dense dragon scales with bright ridges; no macro plates."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99210)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.16, 0.24, 0.16, 0.06)
    if _CV2_OK:
        sw = max(7, int(26 * sc))
        sh = max(6, int(22 * sc))
        for row, y in enumerate(range(0, h + sh, sh)):
            offset = sw // 2 if row % 2 else 0
            for x in range(-sw, w + sw, sw):
                cx = x + offset
                cy = y
                pts = np.array([
                    [cx, cy - sh // 2],
                    [cx + sw // 2, cy],
                    [cx, cy + sh // 2],
                    [cx - sw // 2, cy],
                ], dtype=np.int32)
                tier = float(rng.choice([0.24, 0.34, 0.44, 0.54, 0.66, 0.78]))
                _cv2.fillPoly(M, [pts], min(0.70, tier * 0.72), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts], min(0.88, tier + 0.16), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], min(0.66, tier * 0.70), lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [pts], True, min(0.88, tier + 0.22), 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [pts], True, min(0.96, tier + 0.28), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx, cy - sh // 2), (cx, cy + sh // 3), min(0.82, tier + 0.16), 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 1800, 0.05)
    return _finish("dragon_scale_macro", M, R, CC, sm)


def codex_brushed_sparkle(shape, seed, sm, **kwargs):
    """Brushed metal plus tiny aligned sparkle chips, not generic glitter."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99211)
    sc = _scale(shape)
    yy, xx = _grid(h, w)
    grain = _line_distance(yy + np.sin(xx / max(1.0, 80.0 * sc)) * 3.0 * sc, 8.0 * sc, 0.7 * sc, seed)
    fleck = (_normalize(multi_scale_noise(shape, [22, 47, 93], [0.4, 0.35, 0.25], int(seed) + 912)) > 0.965).astype(np.float32)
    M = np.clip(0.30 + grain * 0.30 + fleck * 0.46, 0, 1).astype(np.float32)
    R = np.clip(0.24 + grain * 0.06 - fleck * 0.10, 0, 1).astype(np.float32)
    CC = np.clip(0.32 + grain * 0.18 + fleck * 0.42, 0, 1).astype(np.float32)
    _dot_noise(M, R, CC, rng, 3500, 0.03)
    return _finish("brushed_sparkle", M, R, CC, sm)


def codex_diamond_dust(shape, seed, sm, **kwargs):
    """Dense tiny diamond chips and star glints over dark clear."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99212)
    sc = _scale(shape)
    M, R, CC = _base(shape, int(seed), 0.18, 0.16, 0.20, 0.06)
    if _CV2_OK:
        n = int(np.clip(h * w / 1400, 260, 4500))
        for _ in range(n):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(2.0, 5.0) * sc))
            pts = np.array([[cx, cy - rr], [cx + rr, cy], [cx, cy + rr], [cx - rr, cy]], dtype=np.int32)
            m = float(rng.uniform(0.55, 0.98)); c = float(rng.uniform(0.50, 0.98))
            _cv2.fillPoly(M, [pts], m, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts], c, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [pts], float(rng.uniform(0.05, 0.22)), lineType=_cv2.LINE_AA)
            if rng.random() < 0.18:
                _cv2.line(M, (cx - rr * 2, cy), (cx + rr * 2, cy), 0.98, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx, cy - rr * 2), (cx, cy + rr * 2), 0.98, 1, lineType=_cv2.LINE_AA)
    _dot_noise(M, R, CC, rng, 1700, 0.06)
    return _finish("diamond_dust", M, R, CC, sm)


def codex_spec_holographic_foil(shape, seed, sm, **kwargs):
    """Angular holographic foil facets with spectral grating carriers."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99213)
    yy, xx = _grid(h, w)
    sc = _scale(shape)
    grating = _line_distance(xx * 0.8 + yy * 0.25, 10.0 * sc, 0.8 * sc, seed)
    phase = np.sin((xx * 0.020 + yy * 0.035) / sc + seed * 0.01)
    M = np.clip(0.22 + grating * 0.36 + (phase + 1) * 0.10, 0, 1).astype(np.float32)
    R = np.clip(0.18 + grating * 0.08 + (np.sin(phase + 2.0) + 1) * 0.05, 0, 1).astype(np.float32)
    CC = np.clip(0.30 + grating * 0.46 + (np.sin(phase + 4.0) + 1) * 0.12, 0, 1).astype(np.float32)
    if _CV2_OK:
        for _ in range(int(np.clip(h * w / 9000, 45, 420))):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(3, int(rng.uniform(8, 20) * sc))
            pts = _star(cx, cy, rr, max(1, rr // 2), 3, rng.uniform(0, math.pi))
            _cv2.polylines(M, [pts], True, float(rng.uniform(0.55, 0.98)), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [pts], True, float(rng.uniform(0.55, 0.98)), 1, lineType=_cv2.LINE_AA)
    return _finish("spec_holographic_foil", M, R, CC, sm)


def codex_spec_iridescent_film(shape, seed, sm, **kwargs):
    """Thin-film interference bands that visibly shift, not a flat/broken overlay."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 99214)
    yy, xx = _grid(h, w)
    sc = _scale(shape)
    warp = np.sin(xx / max(1.0, 58.0 * sc)) * 4.0 * sc + np.sin(yy / max(1.0, 47.0 * sc)) * 3.0 * sc
    bands = (yy + warp + xx * 0.22) / max(1.0, 14.0 * sc)
    micro = (xx * 0.55 - yy * 0.18 + warp * 0.7) / max(1.0, 7.0 * sc)
    M = np.clip(0.22 + (np.sin(bands) + 1) * 0.17 + (np.sin(micro + 0.4) + 1) * 0.06, 0, 1).astype(np.float32)
    R = np.clip(0.20 + (np.sin(bands + 2.1) + 1) * 0.11 + (np.sin(micro + 2.2) + 1) * 0.05, 0, 1).astype(np.float32)
    CC = np.clip(0.24 + (np.sin(bands + 4.2) + 1) * 0.18 + (np.sin(micro + 4.1) + 1) * 0.06, 0, 1).astype(np.float32)
    pores = (_normalize(multi_scale_noise(shape, [9, 21, 43], [0.45, 0.33, 0.22], int(seed) + 914)) > 0.91).astype(np.float32)
    M = np.clip(M - pores * 0.10, 0, 1)
    R = np.clip(R + pores * 0.04, 0, 1)
    CC = np.clip(CC - pores * 0.08, 0, 1)
    _dot_noise(M, R, CC, rng, 3000, 0.04)
    return _finish("spec_iridescent_film", M, R, CC, sm)
