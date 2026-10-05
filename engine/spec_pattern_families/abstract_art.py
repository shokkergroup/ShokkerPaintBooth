"""Abstract-art spec pattern family for Shokker Paint Booth.

This module is imported by engine.spec_patterns so the legacy public
PATTERN_CATALOG keys stay stable while the former monster registry shrinks.
"""
import numpy as np
from scipy.spatial import cKDTree

from ..spec_patterns import (
    _CV2_OK,
    _cv2,
    _flat,
    _gauss,
    _normalize,
    _spb_fast_smooth_noise,
    _sm_scale,
    _smoothstep,
    _validate_spec_output,
    multi_scale_noise,
)


def _spb_fast_line_distance(coord, period, width, phase=0.0):
    r = np.abs(np.mod(coord + phase, period) - period * 0.5)
    return np.clip(1.0 - r / max(width, 1e-6), 0.0, 1.0).astype(np.float32)

# ABSTRACT ART (17 patterns) — art-history-inspired spec overlays.
#   expressionist_splatter, cubist_facets, rothko_field, kandinsky_shapes,
#   mondrian_grid, op_art_circles, op_art_waves, suprematism, futurist_motion,
#   minimalist_stripe, hard_edge_field, color_field_bleed, fluid_acrylic_pour,
#   ink_wash_gradient, neon_glitch, retro_wave, bauhaus_forms
# All signatures: (shape, seed, sm, **kwargs) -> float32 (h,w) in [0,1].
# ----------------------------------------------------------------------------

def abstract_expressionist_splatter(shape, seed, sm, **kwargs):
    """abstract_expressionist_splatter.

    OWNER REBUILD (R6-Tick): owner HATED the Pollock-style splatter. Same
    function name, completely new identity — VOODOO HEX SIGILS on burnt
    black gothic ground. Racing-livery friendly horror motif:
    (1) near-black metallic substrate (composite-dark — M/R/CC all low),
    (2) HERO TIER: 4-7 small VEVE-style ritual sigils (12-22 px wide
    intricate occult diagrams — crossed bones, eye-of-providence ovals,
    crescent + dagger glyphs) drawn in blood-red metallic ink, (3)
    GOTHIC PIN-NAIL field — 8-14 px clusters of upright iron-cross
    flecks (small + signed bright-spec heads), (4) HEX-SCRATCH circles
    — thin 6-12 px ritual circles inscribed with radial tick marks,
    (5) CANDLE-DROP wax beads (4-8 px) trickling between sigils, (6)
    BONE-WHITE fleck dust (1-2 px) for ash micro-detail. Per-feature
    INDEPENDENT continuous M/R/CC, all features 4-22 px (no panel-scale).
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 81231)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) BURNT-BLACK GOTHIC GROUND — composite-dark substrate (all 3 low)
    g_m = _normalize(multi_scale_noise(shape, [3.0, 8.0, 18.0], [0.50, 0.34, 0.16], int(seed) + 10101))
    g_r = _normalize(multi_scale_noise(shape, [3.5, 9.0, 20.0], [0.50, 0.34, 0.16], int(seed) + 10102))
    g_c = _normalize(multi_scale_noise(shape, [4.0, 10.0, 22.0], [0.50, 0.34, 0.16], int(seed) + 10103))
    # Composite-dark: keep ALL THREE channels low (no neon green)
    M = (0.12 + (g_m - 0.5) * 0.08).astype(np.float32)
    R = (0.15 + (g_r - 0.5) * 0.10).astype(np.float32)
    CC = (0.10 + (g_c - 0.5) * 0.08).astype(np.float32)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    if _CV2_OK:
        # 2) HERO — VOODOO VEVE SIGILS (5-9 occult diagrams,
        # sized at 5-10% min-dim so visible at any thumbnail resolution)
        n_sig = int(rng.integers(5, 10))
        for _ in range(n_sig):
            cx = int(rng.uniform(0.10, 0.90) * w)
            cy = int(rng.uniform(0.10, 0.90) * h)
            base_r = max(6, int(rng.uniform(0.05, 0.10) * mn))
            kind = int(rng.integers(0, 4))
            # Blood-red metallic ink: M high, R mid-high (rust), CC low-mid
            mM = float(rng.uniform(0.62, 0.92))
            mR = float(rng.uniform(0.40, 0.70))
            mCC = float(rng.uniform(0.18, 0.45))
            if kind == 0:
                # CROSSED BONES — two diagonals + four end-knobs
                _cv2.line(M, (cx - base_r, cy - base_r), (cx + base_r, cy + base_r), mM, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx - base_r, cy - base_r), (cx + base_r, cy + base_r), mR, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx - base_r, cy - base_r), (cx + base_r, cy + base_r), mCC, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx - base_r, cy + base_r), (cx + base_r, cy - base_r), mM, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx - base_r, cy + base_r), (cx + base_r, cy - base_r), mR, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx - base_r, cy + base_r), (cx + base_r, cy - base_r), mCC, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
                for sx, sy in [(-1, -1), (1, 1), (-1, 1), (1, -1)]:
                    kn = max(2, int(scale * 2.0))
                    _cv2.circle(M, (cx + sx * base_r, cy + sy * base_r), kn, mM, -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(R, (cx + sx * base_r, cy + sy * base_r), kn, mR, -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (cx + sx * base_r, cy + sy * base_r), kn, mCC, -1, lineType=_cv2.LINE_AA)
            elif kind == 1:
                # EYE-OF-PROVIDENCE — outer almond + central iris
                ax_ = base_r; ay_ = max(3, int(base_r * 0.5))
                _cv2.ellipse(M, (cx, cy), (ax_, ay_), 0, 0, 360, mM, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (ax_, ay_), 0, 0, 360, mR, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (ax_, ay_), 0, 0, 360, mCC, 1, lineType=_cv2.LINE_AA)
                ir = max(2, int(base_r * 0.35))
                _cv2.circle(M, (cx, cy), ir, mM, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), ir, mR, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), ir, mCC, -1, lineType=_cv2.LINE_AA)
                # pupil dot — bright
                pup = max(1, int(base_r * 0.15))
                _cv2.circle(M, (cx, cy), pup, float(rng.uniform(0.75, 0.95)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), pup, float(rng.uniform(0.55, 0.80)), -1, lineType=_cv2.LINE_AA)
            elif kind == 2:
                # CRESCENT + DAGGER — moon arc with vertical blade
                _cv2.ellipse(M, (cx, cy), (base_r, base_r), 0, 30, 330, mM, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (base_r, base_r), 0, 30, 330, mR, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (base_r, base_r), 0, 30, 330, mCC, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx, cy - base_r), (cx, cy + base_r), mM, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx, cy - base_r), (cx, cy + base_r), mR, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx, cy - base_r), (cx, cy + base_r), mCC, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
                # crossguard
                cg = max(2, int(base_r * 0.4))
                _cv2.line(M, (cx - cg, cy - base_r + 2), (cx + cg, cy - base_r + 2), mM, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx - cg, cy - base_r + 2), (cx + cg, cy - base_r + 2), mR, max(1, int(scale * 1.3)), lineType=_cv2.LINE_AA)
            else:
                # PENTAGRAM-IN-CIRCLE — star with surrounding ring
                _cv2.circle(M, (cx, cy), base_r, mM, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), base_r, mR, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), base_r, mCC, 1, lineType=_cv2.LINE_AA)
                pts5 = []
                for k in range(5):
                    ang = -np.pi / 2 + k * 2 * np.pi / 5
                    pts5.append((cx + np.cos(ang) * base_r, cy + np.sin(ang) * base_r))
                # connect 0-2-4-1-3-0
                order = [0, 2, 4, 1, 3, 0]
                for k in range(5):
                    p0 = pts5[order[k]]; p1 = pts5[order[k + 1]]
                    _cv2.line(M, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), mM, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), mR, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), mCC, 1, lineType=_cv2.LINE_AA)

        # 3) GOTHIC PIN-NAIL FIELD — small upright iron-cross flecks
        n_nail = int(np.clip(2800 * (mn / 2048.0) ** 2, 1100, 6500))
        for _ in range(n_nail):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            sz = max(2, int(rng.uniform(4.0, 8.0) * scale))
            nM = float(rng.uniform(0.45, 0.92))
            nR = float(rng.uniform(0.18, 0.55))
            nCC = float(rng.uniform(0.22, 0.62))
            # vertical stem + short crossbar
            _cv2.line(M, (cx, cy - sz), (cx, cy + sz), nM, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy - sz), (cx, cy + sz), nR, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy - sz), (cx, cy + sz), nCC, 1, lineType=_cv2.LINE_AA)
            cb = max(1, int(sz * 0.55))
            _cv2.line(M, (cx - cb, cy - int(sz * 0.3)), (cx + cb, cy - int(sz * 0.3)), nM, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx - cb, cy - int(sz * 0.3)), (cx + cb, cy - int(sz * 0.3)), nR, 1, lineType=_cv2.LINE_AA)

        # 4) HEX-SCRATCH RITUAL CIRCLES — small ringed glyphs 6-12 px
        n_hex = int(np.clip(1400 * (mn / 2048.0) ** 2, 500, 3800))
        for _ in range(n_hex):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            r = max(3, int(rng.uniform(6.0, 12.0) * scale))
            hM = float(rng.uniform(0.30, 0.85))
            hR = float(rng.uniform(0.42, 0.85))
            hCC = float(rng.uniform(0.10, 0.42))
            _cv2.circle(M, (cx, cy), r, hM, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, hR, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, hCC, 1, lineType=_cv2.LINE_AA)
            # 3-6 radial tick marks
            n_tick = int(rng.integers(3, 7))
            for ti in range(n_tick):
                a = ti * 2 * np.pi / n_tick + float(rng.uniform(0, 0.3))
                x0 = int(cx + np.cos(a) * r)
                y0 = int(cy + np.sin(a) * r)
                x1 = int(cx + np.cos(a) * (r + max(1, int(scale * 1.8))))
                y1 = int(cy + np.sin(a) * (r + max(1, int(scale * 1.8))))
                _cv2.line(M, (x0, y0), (x1, y1), hM, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x0, y0), (x1, y1), hR, 1, lineType=_cv2.LINE_AA)

        # 5) CANDLE-WAX DROP BEADS — 4-8 px tear-drop drips
        n_wax = int(np.clip(1100 * (mn / 2048.0) ** 2, 360, 3400))
        for _ in range(n_wax):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            r = max(2, int(rng.uniform(3.0, 7.0) * scale))
            # wax = pale, low-R but moderate CC
            wM = float(rng.uniform(0.55, 0.88))
            wR = float(rng.uniform(0.15, 0.40))
            wCC = float(rng.uniform(0.35, 0.72))
            _cv2.circle(M, (cx, cy), r, wM, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, wR, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, wCC, -1, lineType=_cv2.LINE_AA)
            # short downward tail (gravity drip)
            tail = int(rng.uniform(3, 8) * scale)
            _cv2.line(M, (cx, cy), (cx, cy + tail), wM, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy), (cx, cy + tail), wR, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (cx, cy + tail), wCC, 1, lineType=_cv2.LINE_AA)

    # 6) BONE-WHITE ASH FLECKS — vectorized
    n_ash = int(np.clip(7000 * (mn / 2048.0) ** 2, 2500, 18000))
    fx = rng.integers(0, w, n_ash); fy = rng.integers(0, h, n_ash)
    M[fy, fx] = rng.uniform(0.40, 0.88, n_ash).astype(np.float32)
    R[fy, fx] = rng.uniform(0.10, 0.45, n_ash).astype(np.float32)
    CC[fy, fx] = rng.uniform(0.20, 0.65, n_ash).astype(np.float32)

    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_expressionist_splatter")
abstract_expressionist_splatter._spb_concept_complete = True


def abstract_cubist_facets(shape, seed, sm, **kwargs):
    """abstract_cubist_facets.

    identity: R6 creative rebuild — Picasso/Braque ANALYTIC CUBIST
    canvas with HEAVY BLACK LINE FRAGMENTATION. Six feature tiers
    layered on an independent-FBM papery ground: (1) long
    GLOBAL-SLICING black contour lines (full-canvas straight crossings
    in 6-12 quasi-parallel sets fanning at slightly different angles,
    the way Cubist drawings dissect a guitar or violin); (2) filled
    angular SHARDS (triangles, irregular quads, 4-10 px) packed dense;
    (3) shorter 6-14 px secondary edge SLIVERS to chip the shards apart;
    (4) chiaroscuro PIN-SPOTS (1-3 px) for tonal flicker; (5)
    OVERLAPPING translucent quad PLATES (8-14 px) for the
    "transparent-plane stacking" Cubist hallmark; (6) per-pixel chroma
    fleck. Per-feature INDEPENDENT continuous M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 790502)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) PAPERY GROUND — INDEPENDENT per-channel FBM
    region_m = _normalize(multi_scale_noise(shape, [12, 26], [0.6, 0.4], int(seed) + 101111))
    region_r = _normalize(multi_scale_noise(shape, [14, 30], [0.6, 0.4], int(seed) + 101112))
    region_cc = _normalize(multi_scale_noise(shape, [13, 28], [0.6, 0.4], int(seed) + 101113))
    grain = _normalize(multi_scale_noise(shape, [1.4, 3.2, 6.5], [0.45, 0.35, 0.20], int(seed) + 101114)) - 0.5
    M = (0.34 + region_m * 0.38 + grain * 0.10).astype(np.float32)
    R = (0.34 + region_r * 0.42 + grain * 0.12).astype(np.float32)
    CC = (0.30 + region_cc * 0.44 + grain * 0.10).astype(np.float32)

    if _CV2_OK:
        # 2) OVERLAPPING TRANSLUCENT QUAD PLATES — 8-14 px stacked planes
        n_plate = int(np.clip(2200 * scale * scale, 700, 5500))
        for _ in range(n_plate):
            cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
            ang = float(rng.uniform(0, np.pi))
            sw_ = float(rng.uniform(8.0, 14.0) * scale)
            sh_ = float(rng.uniform(6.0, 12.0) * scale)
            rect = ((cx, cy), (sw_, sh_), np.degrees(ang))
            box = _cv2.boxPoints(rect).astype(np.int32)
            # Soft translucent fill: blend half-strength
            ovM = float(rng.uniform(0.20, 0.90))
            ovR = float(rng.uniform(0.18, 0.88))
            ovC = float(rng.uniform(0.18, 0.88))
            # Get mask region influence: just fill with slightly less aggressive value
            _cv2.fillPoly(M, [box], ovM, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [box], ovR, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [box], ovC, lineType=_cv2.LINE_AA)

        # 3) ANGULAR SHARDS — filled triangles/quads
        n_shard = int(np.clip(5400 * scale * scale, 1800, 11000))
        for _ in range(n_shard):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            size = max(2, int(rng.uniform(2.5, 6.0) * scale))
            n_v = int(rng.integers(3, 5))
            base_a = float(rng.uniform(0, 2 * np.pi))
            pts = []
            for k in range(n_v):
                a = base_a + k * (2 * np.pi / n_v) + float(rng.uniform(-0.45, 0.45))
                rr = size * float(rng.uniform(0.55, 1.25))
                pts.append([int(cx + np.cos(a) * rr), int(cy + np.sin(a) * rr)])
            pts = np.array(pts, dtype=np.int32)
            pm = float(rng.uniform(0.15, 0.96))
            pr = float(rng.uniform(0.10, 0.94))
            pc = float(rng.uniform(0.08, 0.92))
            _cv2.fillPoly(M, [pts], pm)
            _cv2.fillPoly(R, [pts], pr)
            _cv2.fillPoly(CC, [pts], pc)
            # Razor edge — heavy black contour
            _cv2.polylines(M, [pts], True, float(rng.uniform(0.04, 0.20)), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(R, [pts], True, float(rng.uniform(0.62, 0.95)), 1, lineType=_cv2.LINE_AA)

        # 4) GLOBAL CUBIST SLICING LINES — long full-canvas contour cuts
        n_sets = int(rng.integers(6, 13))
        # Each set fans at a slightly different angle
        for _set in range(n_sets):
            set_ang = float(rng.uniform(0, np.pi))
            n_in_set = int(rng.integers(2, 5))
            for _line in range(n_in_set):
                # Random offset perpendicular to set_ang
                offset_d = float(rng.uniform(-mn * 0.5, mn * 0.5))
                # Pick a center, draw long line
                ccx = w * 0.5 + np.cos(set_ang + np.pi * 0.5) * offset_d
                ccy = h * 0.5 + np.sin(set_ang + np.pi * 0.5) * offset_d
                # Extend across canvas
                ext = float(mn * 1.5)
                x0 = int(ccx - np.cos(set_ang) * ext); y0 = int(ccy - np.sin(set_ang) * ext)
                x1 = int(ccx + np.cos(set_ang) * ext); y1 = int(ccy + np.sin(set_ang) * ext)
                lw = int(rng.choice([1, 1, 1, 2]))
                _cv2.line(M, (x0, y0), (x1, y1), float(rng.uniform(0.04, 0.18)), lw, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x0, y0), (x1, y1), float(rng.uniform(0.66, 0.96)), lw, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.55, 0.90)), lw, lineType=_cv2.LINE_AA)

        # 5) SECONDARY EDGE SLIVERS — 6-14 px short angular hairlines
        n_edge = int(np.clip(3200 * scale * scale, 1100, 7200))
        for _ in range(n_edge):
            cx = rng.uniform(2, w - 2); cy = rng.uniform(2, h - 2)
            length = float(rng.uniform(6.0, 14.0) * scale)
            ang = float(rng.uniform(0, 2 * np.pi))
            x0 = int(cx - np.cos(ang) * length * 0.5); y0 = int(cy - np.sin(ang) * length * 0.5)
            x1 = int(cx + np.cos(ang) * length * 0.5); y1 = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0, y0), (x1, y1), float(rng.uniform(0.20, 0.96)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0, y0), (x1, y1), float(rng.uniform(0.08, 0.45)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.08, 0.48)), 1, lineType=_cv2.LINE_AA)

        # 6) CHIAROSCURO PIN-SPOTS — 1-3 px tonal flicker
        n_spot = int(np.clip(2400 * scale * scale, 800, 6000))
        for _ in range(n_spot):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(1.0, 3.0) * scale))
            polarity = rng.random() < 0.5
            pm = float(rng.uniform(0.68, 0.99) if polarity else rng.uniform(0.04, 0.26))
            pr = float(rng.uniform(0.04, 0.30) if polarity else rng.uniform(0.55, 0.96))
            pc = float(rng.uniform(0.06, 0.32) if polarity else rng.uniform(0.50, 0.94))
            _cv2.circle(M, (cx, cy), rr, pm, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), rr, pr, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rr, pc, -1, lineType=_cv2.LINE_AA)

    # 7) PER-PIXEL CHROMA FLECK — INDEPENDENT M/R/CC
    n_fl = max(3200, int(h * w / 1000))
    fx = rng.integers(0, w, n_fl); fy = rng.integers(0, h, n_fl)
    M[fy, fx] = rng.uniform(0.15, 0.98, n_fl).astype(np.float32)
    R[fy, fx] = rng.uniform(0.06, 0.96, n_fl).astype(np.float32)
    CC[fy, fx] = rng.uniform(0.06, 0.96, n_fl).astype(np.float32)

    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_cubist_facets")
abstract_cubist_facets._spb_concept_complete = True


def abstract_rothko_field(shape, seed, sm, num_fields=3, feather=0.12,
                           **kwargs):
    """Rothko - UNMISTAKABLE soft horizontal color-field bands.

    identity: R6-CREATIVE — Rothko field with VAPOR-BREATHING EDGES.
    Two or three wide horizontal color-field bands stacked vertically,
    each band a full canvas-width slab with deeply feathered seams.
    On top of the bands: very thin vertical paint-pour drip trails
    leaking out of the high-contrast seams (the dried-paint signature
    of a Rothko on a vertically-hung canvas) + a subtle vertical
    feather glow on the LEFT and RIGHT canvas edges (atmospheric vignette
    creating the "the bands hover" illusion). Per-band INDEPENDENT
    M/R/CC. Horizontal scumble brushwork stays inside its band (no
    cross-band brush). Painted weight, not printed.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("abstract_rothko_field_r6") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    n_bands = max(2, int(num_fields))
    # Asymmetric band heights (Rothko signature - smaller top, larger middle, narrower bottom)
    raw = rng.uniform(0.55, 1.7, n_bands)
    raw = raw / raw.sum()
    band_edges = [0.0]
    cum = 0.0
    for v in raw:
        cum += float(v); band_edges.append(cum)
    band_edges[-1] = 1.0

    # Per-band INDEPENDENT M/R/CC with WIDER chroma range
    band_M  = rng.uniform(0.15, 0.92, n_bands).astype(np.float32)
    band_R  = rng.uniform(0.12, 0.78, n_bands).astype(np.float32)
    band_CC = rng.uniform(0.06, 0.68, n_bands).astype(np.float32)

    yy = np.arange(h, dtype=np.float32) / max(h - 1, 1)
    M_col = np.zeros(h, dtype=np.float32)
    R_col = np.zeros(h, dtype=np.float32)
    CC_col = np.zeros(h, dtype=np.float32)
    band_idx_per_row = np.zeros(h, dtype=np.int32)
    for i in range(n_bands):
        lo = band_edges[i]; hi = band_edges[i + 1]
        if i == n_bands - 1:
            idx = np.where(yy >= lo)[0]
        else:
            idx = np.where((yy >= lo) & (yy < hi))[0]
        M_col[idx] = band_M[i]
        R_col[idx] = band_R[i]
        CC_col[idx] = band_CC[i]
        band_idx_per_row[idx] = i

    # DEEP feather - Rothko signature seam glow
    feather_px = max(8, int(feather * h))
    kk = np.exp(-np.arange(-feather_px, feather_px + 1) ** 2 / (2.0 * (feather_px * 0.5) ** 2)).astype(np.float32)
    kk /= kk.sum()
    M_col = np.convolve(M_col, kk, mode='same').astype(np.float32)
    R_col = np.convolve(R_col, kk, mode='same').astype(np.float32)
    CC_col = np.convolve(CC_col, kk, mode='same').astype(np.float32)

    M  = np.broadcast_to(M_col[:, None],  (h, w)).copy()
    R  = np.broadcast_to(R_col[:, None],  (h, w)).copy()
    CC = np.broadcast_to(CC_col[:, None], (h, w)).copy()

    # Soft atmospheric canvas-tooth grain (subtle)
    tooth = _normalize(multi_scale_noise(shape, [3.0, 9.0, 22.0], [0.5, 0.3, 0.2], int(seed) + 10121))
    M = np.clip(M + (tooth - 0.5) * 0.08, 0, 1)
    R = np.clip(R + (tooth - 0.5) * 0.08, 0, 1)
    CC = np.clip(CC + (tooth - 0.5) * 0.06, 0, 1)

    # Per-row micro-jitter so bands feel painted not printed
    jitter = rng.normal(0, 0.018, size=h).astype(np.float32)
    M  += jitter[:, None]
    R  += jitter[:, None] * 0.7
    CC += jitter[:, None] * 0.5

    # SIDE VIGNETTE — soft vertical feather glow at left and right edges
    xx = np.arange(w, dtype=np.float32) / max(w - 1, 1)
    edge_glow = (1.0 - 4.0 * (xx - 0.5) ** 2).clip(0.0, 1.0)  # darker near edges
    edge_alpha = (1.0 - edge_glow) * 0.18
    M  = M  * (1 - edge_alpha[None, :]) + (M  * 0.6) * edge_alpha[None, :]
    R  = R  * (1 - edge_alpha[None, :]) + (R  * 0.6) * edge_alpha[None, :]
    CC = CC * (1 - edge_alpha[None, :]) + (CC * 0.6) * edge_alpha[None, :]

    if _CV2_OK:
        # ATMOSPHERIC horizontal scumble - strict horizontal only (Rothko axis)
        n_brush = int(np.clip(1100 * (mn / 2048.0) ** 2, 380, 2900))
        for _ in range(n_brush):
            cx = float(rng.uniform(2, w - 2)); cy = float(rng.uniform(2, h - 2))
            length = float(rng.uniform(10.0, 24.0) * scale)
            x0s = int(cx - length * 0.5); y0s = int(cy)
            x1s = int(cx + length * 0.5); y1s = int(cy)
            base_m = float(M[y0s % h, x0s % w])
            base_r = float(R[y0s % h, x0s % w])
            base_c = float(CC[y0s % h, x0s % w])
            _cv2.line(M,  (x0s, y0s), (x1s, y1s), float(np.clip(base_m + rng.uniform(-0.12, 0.12), 0.05, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R,  (x0s, y0s), (x1s, y1s), float(np.clip(base_r + rng.uniform(-0.12, 0.12), 0.05, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0s, y0s), (x1s, y1s), float(np.clip(base_c + rng.uniform(-0.12, 0.12), 0.05, 0.95)), 1, lineType=_cv2.LINE_AA)

        # PAINT-POUR DRIP TRAILS — thin vertical leak streaks from seams
        # Pick the actual seam y positions
        seam_ys = []
        for i in range(1, n_bands):
            seam_y = int(band_edges[i] * h)
            seam_ys.append(seam_y)
        n_drip = int(np.clip(40 * (mn / 256.0), 16, 110))
        for _ in range(n_drip):
            if not seam_ys: break
            seam_y = int(rng.choice(seam_ys))
            x_drip = int(rng.uniform(0.02, 0.98) * w)
            drip_len = int(rng.uniform(0.05, 0.18) * h)
            y_end = min(h - 1, seam_y + drip_len)
            # Drip color = band BELOW the seam, darkened slightly
            i_below = band_idx_per_row[min(h - 1, seam_y + 1)]
            dM = float(np.clip(band_M[i_below] * float(rng.uniform(0.55, 0.85)), 0, 1))
            dR = float(np.clip(band_R[i_below] * float(rng.uniform(0.85, 1.05)), 0, 1))
            dCC = float(np.clip(band_CC[i_below] * float(rng.uniform(0.55, 0.85)), 0, 1))
            wob = np.cumsum(rng.uniform(-0.4, 0.4, drip_len)) * scale
            for ti in range(drip_len):
                yi = seam_y + ti
                if yi >= h: break
                t = ti / max(drip_len - 1, 1)
                taper = (1.0 - t) ** 1.3
                hw = max(0, int(rng.uniform(0.5, 1.5) * scale * taper + 0.5))
                xc = int(np.clip(x_drip + wob[ti], hw, w - hw - 1))
                lo = max(0, xc - hw); hi_ = min(w, xc + hw + 1)
                a = 0.55 * taper
                M[yi, lo:hi_]  = M[yi, lo:hi_]  * (1 - a) + dM * a
                R[yi, lo:hi_]  = R[yi, lo:hi_]  * (1 - a) + dR * a
                CC[yi, lo:hi_] = CC[yi, lo:hi_] * (1 - a) + dCC * a

    # Pigment flecks (atmospheric)
    n_fl = int(np.clip(1100 * (mn / 2048.0) ** 2, 360, 2400))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx]  = np.clip(M[fy, fx]  + rng.uniform(-0.12, 0.18, n_fl).astype(np.float32), 0, 1)
    R[fy, fx]  = np.clip(R[fy, fx]  + rng.uniform(-0.12, 0.18, n_fl).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.12, 0.18, n_fl).astype(np.float32), 0, 1)

    # R6-CREATIVE NEW: MYCELIUM SEAM FIBERS � biological mycelium threads
    # climbing along the high-contrast band seams. Each thread is an 8-22
    # step wandering polyline using random-walk turns (hyphal foraging).
    # 14-48 fibers seeded near the seam y-coordinates with light vertical
    # drift up or down into adjacent bands. Per-fiber INDEPENDENT
    # continuous M/R/CC. Layers biology-weird detail onto the painterly
    # Rothko base without compromising the band identity.
    try:
        _seam_pool = seam_ys  # type: ignore[name-defined]
    except NameError:
        _seam_pool = []
    # Fall back to evenly-spaced seam approximation if not in scope
    if not _seam_pool:
        _seam_pool = [int((i + 1) / n_bands * h) for i in range(n_bands - 1)]

    if _CV2_OK and _seam_pool:
        n_myc = int(np.clip(28 * (mn / 256.0), 14, 48))
        for _ in range(n_myc):
            sy_root = int(rng.choice(_seam_pool))
            mx = float(rng.uniform(0.02, 0.98) * w)
            my = float(sy_root + rng.uniform(-3.0, 3.0))
            ang = float(rng.uniform(-np.pi / 2, np.pi / 2))
            if rng.random() > 0.5: ang = -ang
            fibM  = float(rng.uniform(0.35, 0.88))
            fibR  = float(rng.uniform(0.18, 0.62))
            fibCC = float(rng.uniform(0.10, 0.55))
            n_steps = int(rng.integers(8, 23))
            step_len = float(rng.uniform(0.9, 1.6) * scale)
            for s in range(n_steps):
                nx = mx + np.cos(ang) * step_len
                ny = my + np.sin(ang) * step_len
                if not (0 <= int(nx) < w and 0 <= int(ny) < h): break
                _cv2.line(M,  (int(mx), int(my)), (int(nx), int(ny)),
                          float(np.clip(fibM  + rng.uniform(-0.05, 0.05), 0, 1)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R,  (int(mx), int(my)), (int(nx), int(ny)),
                          float(np.clip(fibR  + rng.uniform(-0.05, 0.05), 0, 1)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (int(mx), int(my)), (int(nx), int(ny)),
                          float(np.clip(fibCC + rng.uniform(-0.05, 0.05), 0, 1)), 1, lineType=_cv2.LINE_AA)
                mx, my = nx, ny
                ang += float(rng.normal(0.0, 0.38))

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
abstract_rothko_field._spb_concept_complete = True

def abstract_kandinsky_shapes(shape, seed, sm, n_circles=12, n_lines=10,
                                n_triangles=6, **kwargs):
    """Kandinsky — R6 fix: denser BOLD geometric forms + wider chroma swings.

    identity: R6 owner-fix rebuild — owner flagged "Too sparse" and
    "Wrong/weak color variation (chroma flat)". New build pushes 2-3x
    denser primitives across all tiers AND widens each chroma family's
    M/R/CC sampling envelope so red, blue, yellow, green, orange, magenta,
    cyan, black ink each read as DISTINCT saturated paints (not muddled
    pastel). Vocabulary: pale tempera ground, concentric ring families
    8-22 px, filled triangles 8-22 px, bold diagonal shards 8-22 px,
    HERO crosshatch grid bands (10-26 px) as Kandinsky's compositional
    spine, small polychrome dots 2-5 px, polychrome flecks. Each primitive
    uses INDEPENDENT continuous M/R/CC from its color family.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 10130)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # PALE TEMPERA GROUND (cream / off-white so primaries pop) — slightly more textured
    grain = _normalize(multi_scale_noise(shape, [1.6, 3.2, 6.4], [0.45, 0.35, 0.20], int(seed) + 10131))
    M = np.full(shape, 0.22, dtype=np.float32) + (grain - 0.5) * 0.10
    R = np.full(shape, 0.62, dtype=np.float32) + (grain - 0.5) * 0.10
    CC = np.full(shape, 0.35, dtype=np.float32) + (grain - 0.5) * 0.08

    # Kandinsky palette WIDENED — 8 chroma families with broader M/R/CC envelopes
    def _kand_color():
        roll = rng.random()
        if roll < 0.16:   # red — wider M range, deeper CC bottom
            return float(rng.uniform(0.30, 0.72)), float(rng.uniform(0.48, 0.88)), float(rng.uniform(0.12, 0.55))
        elif roll < 0.30: # cobalt blue
            return float(rng.uniform(0.60, 0.94)), float(rng.uniform(0.15, 0.48)), float(rng.uniform(0.06, 0.40))
        elif roll < 0.46: # vivid yellow
            return float(rng.uniform(0.48, 0.86)), float(rng.uniform(0.12, 0.42)), float(rng.uniform(0.04, 0.36))
        elif roll < 0.58: # green
            return float(rng.uniform(0.38, 0.78)), float(rng.uniform(0.22, 0.62)), float(rng.uniform(0.08, 0.48))
        elif roll < 0.70: # orange
            return float(rng.uniform(0.32, 0.72)), float(rng.uniform(0.40, 0.78)), float(rng.uniform(0.14, 0.55))
        elif roll < 0.80: # magenta-violet
            return float(rng.uniform(0.42, 0.82)), float(rng.uniform(0.28, 0.65)), float(rng.uniform(0.60, 0.96))
        elif roll < 0.90: # cyan
            return float(rng.uniform(0.55, 0.92)), float(rng.uniform(0.10, 0.40)), float(rng.uniform(0.45, 0.85))
        else:             # black ink
            return float(rng.uniform(0.04, 0.22)), float(rng.uniform(0.12, 0.32)), float(rng.uniform(0.42, 0.78))

    if _CV2_OK:
        # CONCENTRIC RING FAMILIES (Kandinsky signature) — 8-22 px — 2.2x denser
        n_ring = int(np.clip(1400 * scale * scale, 540, 3300))
        for _ in range(n_ring):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r_outer = max(4, int(rng.uniform(4.0, 11.0) * scale))
            thick = 1 + int(rng.random() < 0.40)
            cm, cr, cc = _kand_color()
            _cv2.circle(M, (cx, cy), r_outer, cm, thick, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r_outer, cr, thick, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_outer, cc, thick, lineType=_cv2.LINE_AA)
            # tiny inner dot with separate Kandinsky-primary chroma
            r_in = max(1, r_outer // 3)
            cm2, cr2, cc2 = _kand_color()
            _cv2.circle(M, (cx, cy), r_in, cm2, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r_in, cr2, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_in, cc2, -1, lineType=_cv2.LINE_AA)

        # FILLED FLOATING TRIANGLES — 8-22 px — 2.5x denser
        n_tri = int(np.clip(2200 * scale * scale, 800, 5000))
        for _ in range(n_tri):
            cx = rng.uniform(0.03 * w, 0.97 * w); cy = rng.uniform(0.03 * h, 0.97 * h)
            size = float(rng.uniform(4.0, 11.0) * scale)
            rot = float(rng.uniform(0, 2 * np.pi))
            pts = []
            for k in range(3):
                a = rot + k * 2.0 * np.pi / 3.0
                pts.append([int(np.clip(cx + np.cos(a) * size, 0, w - 1)),
                            int(np.clip(cy + np.sin(a) * size, 0, h - 1))])
            arr_pts = [np.asarray(pts, dtype=np.int32)]
            cm, cr, cc = _kand_color()
            _cv2.fillPoly(M, arr_pts, cm, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, arr_pts, cr, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, arr_pts, cc, lineType=_cv2.LINE_AA)

        # BOLD DIAGONAL SHARDS — 8-22 px — 2.4x denser
        n_line = int(np.clip(3400 * scale * scale, 1200, 8000))
        for _ in range(n_line):
            cx = rng.uniform(2, w - 2); cy = rng.uniform(2, h - 2)
            length = float(rng.uniform(8.0, 22.0) * scale)
            ang = float(rng.uniform(0, 2 * np.pi))
            x0 = int(cx - np.cos(ang) * length * 0.5); y0 = int(cy - np.sin(ang) * length * 0.5)
            x1 = int(cx + np.cos(ang) * length * 0.5); y1 = int(cy + np.sin(ang) * length * 0.5)
            thick = 1 + int(rng.random() < 0.35)
            cm, cr, cc = _kand_color()
            _cv2.line(M, (x0, y0), (x1, y1), cm, thick, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0, y0), (x1, y1), cr, thick, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), cc, thick, lineType=_cv2.LINE_AA)

        # HERO CROSSHATCH GRID BANDS — Kandinsky compositional spine
        # Short straight color bars (10-26 px) at 4 cardinal-ish angles
        for ang_base in (0.0, np.pi * 0.5, np.pi * 0.25, np.pi * 0.75):
            n_bar = int(np.clip(800 * scale * scale, 300, 2000))
            for _ in range(n_bar):
                cx = rng.uniform(2, w - 2); cy = rng.uniform(2, h - 2)
                length = float(rng.uniform(10.0, 26.0) * scale)
                ang = ang_base + float(rng.normal(0.0, 0.06))
                x0 = int(cx - np.cos(ang) * length * 0.5); y0 = int(cy - np.sin(ang) * length * 0.5)
                x1 = int(cx + np.cos(ang) * length * 0.5); y1 = int(cy + np.sin(ang) * length * 0.5)
                thick = 1 + int(rng.random() < 0.50)
                cm, cr, cc = _kand_color()
                _cv2.line(M, (x0, y0), (x1, y1), cm, thick, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x0, y0), (x1, y1), cr, thick, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x0, y0), (x1, y1), cc, thick, lineType=_cv2.LINE_AA)

        # SMALL POLYCHROME DOTS scattered between forms (2-5 px) — 2.4x denser
        n_dot = int(np.clip(2900 * scale * scale, 1080, 7200))
        for _ in range(n_dot):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1.5, 3.0) * scale))
            cm, cr, cc = _kand_color()
            _cv2.circle(M, (cx, cy), r, cm, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, cr, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, cc, -1, lineType=_cv2.LINE_AA)

    # Pigment flecks — wider chroma range
    n_fl = int(np.clip(5000 * scale * scale, 1600, 11000))
    fx = rng.integers(0, w, n_fl); fy = rng.integers(0, h, n_fl)
    M[fy, fx] = rng.uniform(0.10, 0.97, n_fl).astype(np.float32)
    R[fy, fx] = rng.uniform(0.06, 0.92, n_fl).astype(np.float32)
    CC[fy, fx] = rng.uniform(0.06, 0.92, n_fl).astype(np.float32)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_kandinsky_shapes")
abstract_kandinsky_shapes._spb_concept_complete = True


def abstract_mondrian_grid(shape, seed, sm, min_splits=5, max_splits=9, **kwargs):
    """abstract_mondrian_grid.

    identity (R6 creative rebuild): Pure De Stijl Mondrian tableau pushed
    with extra storytelling: recursive ORTHOGONAL partition with 5 canonical
    paint stocks (white-dominant, primary red/yellow/blue accents, black ink).
    Heavy black 4-12 px grid rules between blocks. NEW HERO motifs added:
    (A) MASKING-TAPE CREASE LINES — faint parallel hairlines INSIDE the heavy
    grid stripes (where artist's tape ridged the paint) selling the
    hand-painted nature; (B) GESSO PRIME-COAT TEXTURE inside white blocks
    only (FBM-like substrate variation evoking primed canvas weave); (C)
    SIGNATURE BLOCK PUNCH — one randomly-chosen primary block gets a 12-22
    px concentric dot in a contrasting primary (the 'red square inside a
    yellow field' Mondrian-quote). Plus cardinal brushwork, impasto dots,
    and grid-crossing intersection pucks (small bright dots at every
    grid cross). All features fine 1-22 px, no curves, no diagonals.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 10140)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)
    grid_line_w = max(4, int(np.clip(9 * scale, 4, 12)))

    # RECURSIVE ORTHOGONAL PARTITION
    rects = [(0, h, 0, w, 0)]
    final = []
    while rects:
        y0, y1, x0, x1, d = rects.pop()
        rh = y1 - y0; rw = x1 - x0
        if (d >= max_splits) or (rh < 40 or rw < 40) or            (d >= min_splits and rng.random() < 0.30):
            final.append((y0, y1, x0, x1))
            continue
        ratios = [0.34, 0.40, 0.50, 0.60, 0.66]
        ratio = ratios[int(rng.integers(0, len(ratios)))]
        if rw > rh:
            split = int(x0 + rw * ratio)
            rects.append((y0, y1, x0, split, d + 1))
            rects.append((y0, y1, split, x1, d + 1))
        else:
            split = int(y0 + rh * ratio)
            rects.append((y0, split, x0, x1, d + 1))
            rects.append((split, y1, x0, x1, d + 1))

    # BLOCK FILLS - strict Mondrian palette weighting (white dominant, primaries accent)
    M = np.full(shape, 0.20, dtype=np.float32)
    R = np.full(shape, 0.70, dtype=np.float32)
    CC = np.full(shape, 0.35, dtype=np.float32)
    block_records = []  # remember per-block base for brushwork
    for (y0, y1, x0, x1) in final:
        roll = rng.random()
        if roll < 0.55:        # WHITE - dominant Mondrian field
            mv = float(rng.uniform(0.10, 0.25))
            rv = float(rng.uniform(0.62, 0.80))
            cv = float(rng.uniform(0.20, 0.40))
            tag = 'white'
        elif roll < 0.70:      # RED primary
            mv = float(rng.uniform(0.45, 0.65))
            rv = float(rng.uniform(0.58, 0.78))
            cv = float(rng.uniform(0.20, 0.40))
            tag = 'red'
        elif roll < 0.82:      # YELLOW primary
            mv = float(rng.uniform(0.50, 0.72))
            rv = float(rng.uniform(0.25, 0.45))
            cv = float(rng.uniform(0.12, 0.32))
            tag = 'yellow'
        elif roll < 0.93:      # BLUE primary
            mv = float(rng.uniform(0.65, 0.88))
            rv = float(rng.uniform(0.20, 0.40))
            cv = float(rng.uniform(0.10, 0.28))
            tag = 'blue'
        else:                  # BLACK ink
            mv = float(rng.uniform(0.10, 0.22))
            rv = float(rng.uniform(0.20, 0.35))
            cv = float(rng.uniform(0.50, 0.70))
            tag = 'black'
        M[y0:y1, x0:x1] = mv
        R[y0:y1, x0:x1] = rv
        CC[y0:y1, x0:x1] = cv
        block_records.append((y0, y1, x0, x1, mv, rv, cv, tag))

    # GESSO PRIME-COAT TEXTURE — only in white blocks (HERO-B)
    gesso = _normalize(multi_scale_noise(shape, [2.5, 7.0, 18.0], [0.5, 0.30, 0.20], int(seed) + 10141)).astype(np.float32)
    for (y0, y1, x0, x1, mv, rv, cv, tag) in block_records:
        if tag == 'white':
            block_g = gesso[y0:y1, x0:x1]
            M[y0:y1, x0:x1] = np.clip(M[y0:y1, x0:x1] + (block_g - 0.5) * 0.10, 0, 1)
            R[y0:y1, x0:x1] = np.clip(R[y0:y1, x0:x1] + (block_g - 0.5) * 0.08, 0, 1)
            CC[y0:y1, x0:x1] = np.clip(CC[y0:y1, x0:x1] + (block_g - 0.5) * 0.08, 0, 1)

    # HEAVY BLACK GRID (Mondrian signature)
    for (y0, y1, x0, x1) in final:
        if y0 > 0:
            ys = max(0, y0 - grid_line_w // 2); ye = min(h, y0 + grid_line_w // 2 + 1)
            M[ys:ye, x0:x1] = float(rng.uniform(0.08, 0.16))
            R[ys:ye, x0:x1] = float(rng.uniform(0.22, 0.36))
            CC[ys:ye, x0:x1] = float(rng.uniform(0.50, 0.68))
        if x0 > 0:
            xs = max(0, x0 - grid_line_w // 2); xe = min(w, x0 + grid_line_w // 2 + 1)
            M[y0:y1, xs:xe] = float(rng.uniform(0.08, 0.16))
            R[y0:y1, xs:xe] = float(rng.uniform(0.22, 0.36))
            CC[y0:y1, xs:xe] = float(rng.uniform(0.50, 0.68))

    # MASKING-TAPE CREASE LINES — faint parallel hairlines inside grid stripes (HERO-A)
    if _CV2_OK:
        for (y0, y1, x0, x1) in final:
            if y0 > grid_line_w + 1:
                # 1-2 px center line in the grid stripe
                ys = max(0, y0 - grid_line_w // 4)
                if ys < h:
                    _cv2.line(M, (x0, ys), (x1 - 1, ys), float(rng.uniform(0.25, 0.40)), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, (x0, ys), (x1 - 1, ys), float(rng.uniform(0.55, 0.72)), 1, lineType=_cv2.LINE_AA)
            if x0 > grid_line_w + 1:
                xs = max(0, x0 - grid_line_w // 4)
                if xs < w:
                    _cv2.line(M, (xs, y0), (xs, y1 - 1), float(rng.uniform(0.25, 0.40)), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, (xs, y0), (xs, y1 - 1), float(rng.uniform(0.55, 0.72)), 1, lineType=_cv2.LINE_AA)

    if _CV2_OK:
        # CARDINAL-ONLY brushwork inside blocks (H or V, never diagonal)
        n_brush = int(np.clip(2000 * scale * scale, 700, 5000))
        for _ in range(n_brush):
            if not block_records:
                break
            blk = block_records[int(rng.integers(0, len(block_records)))]
            y0,y1,x0,x1,mv,rv,cv,tag = blk
            if (y1 - y0) < 12 or (x1 - x0) < 12:
                continue
            cx = int(rng.uniform(x0 + 4, x1 - 4)); cy = int(rng.uniform(y0 + 4, y1 - 4))
            length = int(np.clip(rng.uniform(8.0, 18.0) * scale, 4, min(x1-x0, y1-y0) - 4))
            horizontal = rng.random() < 0.5
            if horizontal:
                p0 = (cx - length // 2, cy); p1 = (cx + length // 2, cy)
            else:
                p0 = (cx, cy - length // 2); p1 = (cx, cy + length // 2)
            # Stay near block base color (small jitter)
            _cv2.line(M, p0, p1, float(np.clip(mv + rng.uniform(-0.08, 0.08), 0.05, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, p0, p1, float(np.clip(rv + rng.uniform(-0.08, 0.08), 0.05, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, p0, p1, float(np.clip(cv + rng.uniform(-0.08, 0.08), 0.05, 0.95)), 1, lineType=_cv2.LINE_AA)

        # Small impasto dots 3-7 px
        n_dot = int(np.clip(1200 * scale * scale, 400, 3000))
        for _ in range(n_dot):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1.5, 3.5) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.10, 0.85)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.20, 0.78)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.15, 0.62)), -1, lineType=_cv2.LINE_AA)

        # HERO-C — SIGNATURE BLOCK PUNCH: random primary block gets contrasting concentric dot
        primary_blocks = [b for b in block_records if b[7] in ('red','blue','yellow')]
        if primary_blocks:
            blk = primary_blocks[int(rng.integers(0, len(primary_blocks)))]
            y0,y1,x0,x1,mv,rv,cv,tag = blk
            bw = x1 - x0; bh_ = y1 - y0
            if bw > 24 and bh_ > 24:
                cx_b = (x0 + x1) // 2; cy_b = (y0 + y1) // 2
                # pick contrasting primary
                contrasts = {'red':'blue','blue':'yellow','yellow':'red'}
                contrast_tag = contrasts[tag]
                if contrast_tag == 'red':
                    pM, pR, pCC = 0.58, 0.68, 0.30
                elif contrast_tag == 'yellow':
                    pM, pR, pCC = 0.62, 0.34, 0.20
                else:  # blue
                    pM, pR, pCC = 0.78, 0.30, 0.18
                r_outer = max(6, int(min(bw, bh_) * 0.20))
                r_outer = min(r_outer, 14)
                _cv2.circle(M, (cx_b, cy_b), r_outer, pM, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx_b, cy_b), r_outer, pR, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx_b, cy_b), r_outer, pCC, -1, lineType=_cv2.LINE_AA)
                # inner highlight 1/3 size — same chroma but punched brighter
                r_in = max(2, r_outer // 3)
                _cv2.circle(M, (cx_b, cy_b), r_in, float(np.clip(pM + 0.15, 0, 1)), -1, lineType=_cv2.LINE_AA)

        # GRID-INTERSECTION PUCKS — small bright dots at every grid cross
        # Compute corners shared between blocks
        corners = set()
        for (y0, y1, x0, x1) in final:
            if y0 > 0 and x0 > 0:
                corners.add((x0, y0))
            if y0 > 0 and x1 < w:
                corners.add((x1, y0))
            if y1 < h and x0 > 0:
                corners.add((x0, y1))
            if y1 < h and x1 < w:
                corners.add((x1, y1))
        for (cx, cy) in corners:
            r_p = max(1, int(grid_line_w * 0.30))
            _cv2.circle(M, (cx, cy), r_p, float(rng.uniform(0.65, 0.92)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r_p, float(rng.uniform(0.10, 0.24)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_p, float(rng.uniform(0.10, 0.28)), -1, lineType=_cv2.LINE_AA)

    # Impasto flecks
    n_fl = int(np.clip(2000 * scale * scale, 700, 5000))
    fx = rng.integers(0, w, n_fl); fy = rng.integers(0, h, n_fl)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(-0.10, 0.15, n_fl).astype(np.float32), 0, 1)
    R[fy, fx] = np.clip(R[fy, fx] + rng.uniform(-0.10, 0.15, n_fl).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.10, 0.15, n_fl).astype(np.float32), 0, 1)

    # HERO+ (Tick49 second-pass) DRIPPING WET-PAINT TEARS — small downward
    # tear-trails 4-10 px running south off heavy black grid lines as if
    # wet paint sagged from the rules. Each tear ends in a 2-3 px teardrop
    # bulge. Independent per-tear continuous M/R/CC uniforms. Triggered
    # only at horizontal grid edges (top of each block where the black
    # rule sits). Mondrian-doctrine pure: vertical only, never diagonal.
    if _CV2_OK:
        n_tear_target = int(np.clip(420 * scale * scale, 90, 1100))
        tears_placed = 0
        # block tops are y0 (when y0>0)
        block_tops = [(y0, x0, x1) for (y0, y1, x0, x1) in final if y0 > grid_line_w + 4]
        if block_tops:
            tries = 0
            while tears_placed < n_tear_target and tries < n_tear_target * 3:
                tries += 1
                bt = block_tops[int(rng.integers(0, len(block_tops)))]
                y0, x0, x1 = bt
                if (x1 - x0) < 6:
                    continue
                sx = int(rng.uniform(x0 + 2, x1 - 2))
                sy = int(y0 + grid_line_w // 2)
                dlen = int(np.clip(rng.uniform(4.0, 10.0) * scale, 3, 12))
                ey = min(h - 1, sy + dlen)
                mv = float(rng.uniform(0.08, 0.32))   # darker like the black rule
                rv = float(rng.uniform(0.20, 0.55))
                cv = float(rng.uniform(0.40, 0.85))
                _cv2.line(M, (sx, sy), (sx, ey), mv, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (sx, sy), (sx, ey), rv, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (sx, sy), (sx, ey), cv, 1, lineType=_cv2.LINE_AA)
                # teardrop bulge at tip
                br = 2 if dlen >= 6 else 1
                _cv2.circle(M, (sx, ey), br, float(np.clip(mv + 0.05, 0.05, 0.95)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (sx, ey), br, float(np.clip(cv + rng.uniform(0.05, 0.15), 0.05, 0.98)), -1, lineType=_cv2.LINE_AA)
                tears_placed += 1

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_mondrian_grid")
abstract_mondrian_grid._spb_concept_complete = True


def abstract_op_art_circles(shape, seed, sm, **kwargs):
    """abstract_op_art_circles.

    identity: R6 creative rebuild — Bridget-Riley meets Vasarely. 3-5 overlapping
    high-frequency ring families from off-canvas anchors generate a true MOIRE
    INTERFERENCE field with polychrome ring-by-ring shifts (each ring index draws
    INDEPENDENT continuous M/R/CC uniforms from wide ranges 0.08-0.95 — no shared
    palette across channels). HERO motif: one dominant near-center anchor renders
    as a sharp bullseye with bright crest highlights every ring crossing. Stacked
    tiers: (1) coarse 12-22 px primary rings, (2) fine 4-7 px secondary rings,
    (3) optical CREST DOTS at every ring intersection (1-3 px) with bright chroma
    spikes, (4) dense interference flecks (1-2 px) in the moire-beat zones.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 10180)
    mn = float(min(h, w))
    scale = max(mn / 2048.0, 0.25)
    px = mn / 256.0  # scale features by image size

    # Substrate — quiet metallic base
    fbm = _normalize(multi_scale_noise(shape, [3.0, 7.0, 16.0], [0.5, 0.32, 0.18], int(seed) + 81)) - 0.5
    M = (0.42 + fbm * 0.10).astype(np.float32)
    R = (0.55 + fbm * 0.09).astype(np.float32)
    CC = (0.50 + fbm * 0.08).astype(np.float32)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Ring families: 3-5 anchors, half pulled INSIDE for hero, half outside for moire
    n_anchors = int(rng.integers(3, 6))
    anchor_pts = []
    # Hero: dominant near-center anchor
    anchor_pts.append((rng.uniform(w * 0.35, w * 0.65), rng.uniform(h * 0.35, h * 0.65), True))
    for _ in range(n_anchors - 1):
        side = rng.integers(0, 4)
        if side == 0:
            cx = rng.uniform(-w * 0.4, -w * 0.05); cy = rng.uniform(-h * 0.2, h * 1.2)
        elif side == 1:
            cx = rng.uniform(w * 1.05, w * 1.4); cy = rng.uniform(-h * 0.2, h * 1.2)
        elif side == 2:
            cx = rng.uniform(-w * 0.2, w * 1.2); cy = rng.uniform(-h * 0.4, -h * 0.05)
        else:
            cx = rng.uniform(-w * 0.2, w * 1.2); cy = rng.uniform(h * 1.05, h * 1.4)
        anchor_pts.append((cx, cy, False))

    # Cache distances for later intersection synthesis
    d_list = []
    period_list = []
    for ai, (cx, cy, is_hero) in enumerate(anchor_pts):
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        # Hero gets tighter rings (more bullseye), others get coarser
        if is_hero:
            period = float(rng.uniform(8.0, 14.0) * px)
        else:
            period = float(rng.uniform(11.0, 22.0) * px)
        phase = float(rng.uniform(0, period))
        ring_idx = np.floor((d + phase) / period).astype(np.int32)
        ring_phase = ((d + phase) % period) / period
        prof = 0.5 + 0.5 * np.cos(2.0 * np.pi * ring_phase)

        # Per-ring INDEPENDENT continuous uniforms — wide ranges, each channel independent
        n_rings_total = int(np.ceil(np.sqrt(w * w + h * h) / period)) + 6
        rng_a = np.random.default_rng(int(seed) + 10180 + ai * 17)
        m_pal = rng_a.uniform(0.08, 0.95, n_rings_total).astype(np.float32)
        r_pal = rng_a.uniform(0.08, 0.95, n_rings_total).astype(np.float32)
        c_pal = rng_a.uniform(0.08, 0.95, n_rings_total).astype(np.float32)
        idx_clip = np.clip(ring_idx, 0, n_rings_total - 1)
        m_at = m_pal[idx_clip]; r_at = r_pal[idx_clip]; c_at = c_pal[idx_clip]

        strength = (0.78 if is_hero else 0.46) / n_anchors
        M = M * (1.0 - prof * strength) + m_at * prof * strength
        R = R * (1.0 - prof * strength) + r_at * prof * strength
        CC = CC * (1.0 - prof * strength) + c_at * prof * strength

        # SECOND-ORDER fine rings (half pitch) — interference depth
        period2 = period * 0.5
        ring2 = 0.5 + 0.5 * np.cos(2.0 * np.pi * ((d + phase) % period2) / period2)
        M = M + (ring2 - 0.5) * 0.06 * (1.5 if is_hero else 1.0)
        CC = CC + (ring2 - 0.5) * 0.05 * (1.5 if is_hero else 1.0)

        d_list.append(d)
        period_list.append(period)

    # MOIRE BEAT MAP — sum of ring profiles; peaks where multiple families coincide
    np.clip(M, 0, 1, out=M); np.clip(R, 0, 1, out=R); np.clip(CC, 0, 1, out=CC)

    # CREST DOTS at intersections of any two ring families
    if _CV2_OK and len(d_list) >= 2:
        # Find intersection candidates: where two distance fields BOTH land near a ring boundary
        n_dots = int(np.clip(mn * mn / 90.0, 1200, 9000))
        sy = rng.integers(0, h, size=n_dots)
        sx = rng.integers(0, w, size=n_dots)
        # Test each candidate cheaply
        for k in range(n_dots):
            y0 = int(sy[k]); x0 = int(sx[k])
            # Count families that this point sits near a ring boundary for
            hits = 0
            for di, pd in enumerate(d_list):
                rem = (pd[y0, x0]) % period_list[di]
                if rem < 1.5 or rem > period_list[di] - 1.5:
                    hits += 1
                    if hits >= 2: break
            if hits >= 2:
                rr = int(max(1, rng.uniform(1.0, 3.0) * scale))
                _cv2.circle(M, (x0, y0), rr, float(rng.uniform(0.55, 0.98)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (x0, y0), rr, float(rng.uniform(0.05, 0.25)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (x0, y0), rr, float(rng.uniform(0.60, 0.98)), -1, lineType=_cv2.LINE_AA)

        # DENSE INTERFERENCE FLECKS — 1-2 px specks salted across the whole canvas
        n_fleck = int(np.clip(mn * mn / 140.0, 1500, 6500))
        fy = rng.integers(0, h, size=n_fleck)
        fx = rng.integers(0, w, size=n_fleck)
        M[fy, fx] = rng.uniform(0.08, 0.95, size=n_fleck).astype(np.float32)
        R[fy, fx] = rng.uniform(0.08, 0.95, size=n_fleck).astype(np.float32)
        CC[fy, fx] = rng.uniform(0.08, 0.95, size=n_fleck).astype(np.float32)

    # Body grain
    grain = _normalize(multi_scale_noise(shape, [1.6, 3.5], [0.6, 0.4], int(seed) + 10185)) - 0.5
    R = R + grain * 0.05

    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_op_art_circles")
abstract_op_art_circles._spb_concept_complete = True


def abstract_op_art_waves(shape, seed, sm, **kwargs):
    """abstract_op_art_waves.

    identity (R6 creative rebuild): Bridget Riley Op Art pushed harder — THREE
    crossing wave families (not 2) at incommensurate periods/angles produce
    rich moire interference patterns. NEW HERO motifs: (A) HIGH-CONTRAST
    SIGNATURE BANDS — every Nth band of family 1 is rendered as a near-pure
    black or near-pure white stripe (Riley's signature stark bichromia
    accent), giving the eye anchor stripes at thumbnail scale; (B) PHASE-LENS
    BULGE — a soft radial mask that locally COMPRESSES the wave period
    creating a 'lens distortion' hotspot; (C) CHROMA NODES — bright punch-out
    chroma circles 6-14 px at moire interference peaks. Plus dense rub-line
    micro-strokes between band crests and pinpoint pixel pepper. Per-band
    INDEPENDENT continuous M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 10190)
    scale = max(min(h, w) / 2048.0, 0.25)
    mn = min(h, w)

    M = np.full((h, w), 0.40, dtype=np.float32)
    R = np.full((h, w), 0.55, dtype=np.float32)
    CC = np.full((h, w), 0.50, dtype=np.float32)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # PHASE-LENS BULGE — soft radial period modulator
    bcx = float(rng.uniform(0.25, 0.75) * w); bcy = float(rng.uniform(0.25, 0.75) * h)
    bulge_r = float(rng.uniform(0.20, 0.40) * mn)
    bulge = np.exp(-(((xx - bcx) ** 2 + (yy - bcy) ** 2) / (bulge_r ** 2 + 1e-6)))  # 0..1
    period_mult = 1.0 - bulge * 0.35  # period shrinks ~35% inside bulge

    # Wave family 1
    ang1 = float(rng.uniform(0, 6.28))
    base_period1 = float(rng.uniform(6.0, 12.0) * scale * (mn / 256.0))
    amp1 = float(rng.uniform(4.0, 10.0) * scale)
    freq1 = float(rng.uniform(0.04, 0.10))
    u1 = xx * np.cos(ang1) + yy * np.sin(ang1)
    v1 = -xx * np.sin(ang1) + yy * np.cos(ang1)
    warped1 = u1 + amp1 * np.sin(v1 * freq1)
    period1_field = base_period1 * period_mult
    band_idx1 = np.floor(warped1 / period1_field).astype(np.int32)
    band_phase1 = (np.mod(warped1, period1_field) + period1_field) % period1_field / np.maximum(period1_field, 1e-6)
    prof1 = 0.5 + 0.5 * np.cos(2.0 * np.pi * band_phase1)

    # Wave family 2
    ang2 = float(ang1 + rng.uniform(0.4, 1.2))
    period2 = base_period1 * float(rng.uniform(0.85, 1.15))
    amp2 = float(rng.uniform(3.0, 8.0) * scale)
    freq2 = float(rng.uniform(0.04, 0.12))
    u2 = xx * np.cos(ang2) + yy * np.sin(ang2)
    v2 = -xx * np.sin(ang2) + yy * np.cos(ang2)
    warped2 = u2 + amp2 * np.sin(v2 * freq2)
    period2_field = period2 * period_mult
    band_idx2 = np.floor(warped2 / period2_field).astype(np.int32)
    band_phase2 = (np.mod(warped2, period2_field) + period2_field) % period2_field / np.maximum(period2_field, 1e-6)
    prof2 = 0.5 + 0.5 * np.cos(2.0 * np.pi * band_phase2)

    # NEW Wave family 3 — coarser, incommensurate
    ang3 = float(ang1 + rng.uniform(2.2, 3.6))
    period3 = base_period1 * float(rng.uniform(1.4, 2.1))
    amp3 = float(rng.uniform(5.0, 12.0) * scale)
    freq3 = float(rng.uniform(0.03, 0.08))
    u3 = xx * np.cos(ang3) + yy * np.sin(ang3)
    v3 = -xx * np.sin(ang3) + yy * np.cos(ang3)
    warped3 = u3 + amp3 * np.sin(v3 * freq3)
    band_idx3 = np.floor(warped3 / period3).astype(np.int32)
    band_phase3 = (np.mod(warped3, period3) + period3) % period3 / period3
    prof3 = 0.5 + 0.5 * np.cos(2.0 * np.pi * band_phase3)

    # Per-band palettes
    n_bands = int(np.ceil(np.sqrt(w * w + h * h) / min(base_period1 * 0.6, period2 * 0.6, period3 * 0.6))) + 16
    rng_a = np.random.default_rng(int(seed) + 10191)
    m_pal = rng_a.uniform(0.10, 0.95, n_bands).astype(np.float32)
    r_pal = rng_a.uniform(0.10, 0.90, n_bands).astype(np.float32)
    c_pal = rng_a.uniform(0.15, 0.95, n_bands).astype(np.float32)

    # HERO-A — every 5th-7th band of family 1 → high contrast B/W signature
    sig_stride = int(rng.integers(5, 8))
    bw_mask = (band_idx1 % sig_stride == 0)
    # alternate black/white per occurrence (use index parity)
    bw_white = ((band_idx1 // sig_stride) % 2 == 0) & bw_mask
    bw_black = (~((band_idx1 // sig_stride) % 2 == 0)) & bw_mask
    sig_M = np.where(bw_white, 0.96, np.where(bw_black, 0.06, m_pal[np.clip(band_idx1, 0, n_bands - 1)]))
    sig_R = np.where(bw_white, 0.08, np.where(bw_black, 0.88, r_pal[np.clip(band_idx1, 0, n_bands - 1)]))
    sig_CC = np.where(bw_white, 0.06, np.where(bw_black, 0.78, c_pal[np.clip(band_idx1, 0, n_bands - 1)]))

    idx2 = np.clip(band_idx2, 0, n_bands - 1)
    idx3 = np.clip(band_idx3, 0, n_bands - 1)
    m2 = m_pal[idx2]; r2 = r_pal[idx2]; c2 = c_pal[idx2]
    m3 = m_pal[idx3]; r3 = r_pal[idx3]; c3 = c_pal[idx3]

    M = M * (1.0 - prof1 * 0.55) + sig_M * prof1 * 0.55
    R = R * (1.0 - prof1 * 0.55) + sig_R * prof1 * 0.55
    CC = CC * (1.0 - prof1 * 0.55) + sig_CC * prof1 * 0.55
    M = M * (1.0 - prof2 * 0.30) + m2 * prof2 * 0.30
    R = R * (1.0 - prof2 * 0.30) + r2 * prof2 * 0.30
    CC = CC * (1.0 - prof2 * 0.30) + c2 * prof2 * 0.30
    M = M * (1.0 - prof3 * 0.22) + m3 * prof3 * 0.22
    R = R * (1.0 - prof3 * 0.22) + r3 * prof3 * 0.22
    CC = CC * (1.0 - prof3 * 0.22) + c3 * prof3 * 0.22

    if _CV2_OK:
        # HERO-C — CHROMA NODES at moire interference peaks
        # find peaks where all three profiles align (prof1 * prof2 * prof3 high)
        interference = prof1 * prof2 * prof3
        thresh = float(np.quantile(interference, 0.985))
        peaks_y, peaks_x = np.where(interference > thresh)
        # sample a subset for performance
        n_node = min(int(rng.integers(40, 110)), len(peaks_x))
        if n_node > 0:
            idxs = rng.choice(len(peaks_x), n_node, replace=False)
            for i in idxs:
                px = int(peaks_x[i]); py = int(peaks_y[i])
                r_n = max(2, int(float(rng.uniform(3.0, 7.0)) * scale))
                _cv2.circle(M, (px, py), r_n, float(rng.uniform(0.62, 0.96)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (px, py), r_n, float(rng.uniform(0.08, 0.32)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (px, py), r_n, float(rng.uniform(0.10, 0.55)), -1, lineType=_cv2.LINE_AA)

        # Micro tick-strokes — short hairs between band crests (4-8 px) tangent to band
        n_tk = int(np.clip(2000 * (mn / 2048.0) ** 2, 700, 6000))
        for _ in range(n_tk):
            tx = int(rng.integers(0, w)); ty = int(rng.integers(0, h))
            L = float(rng.uniform(4.0, 8.0) * scale)
            tang = ang1 + float(rng.uniform(-0.2, 0.2)) + np.pi * 0.5  # tangent to family 1
            x2 = int(np.clip(tx + np.cos(tang) * L * 0.5, 0, w - 1))
            y2 = int(np.clip(ty + np.sin(tang) * L * 0.5, 0, h - 1))
            x1c = int(np.clip(tx - np.cos(tang) * L * 0.5, 0, w - 1))
            y1c = int(np.clip(ty - np.sin(tang) * L * 0.5, 0, h - 1))
            _cv2.line(M, (x1c, y1c), (x2, y2), float(rng.uniform(0.18, 0.85)), 1, lineType=_cv2.LINE_AA)

    # Single-pixel pepper for fine grain
    n_fl = int(np.clip(3000 * (mn / 2048.0) ** 2, 1000, 8000))
    fx = rng.integers(0, w, n_fl); fy = rng.integers(0, h, n_fl)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(-0.15, 0.18, n_fl).astype(np.float32), 0, 1)
    R[fy, fx] = np.clip(R[fy, fx] + rng.uniform(-0.12, 0.15, n_fl).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.12, 0.15, n_fl).astype(np.float32), 0, 1)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_op_art_waves")
abstract_op_art_waves._spb_concept_complete = True


def abstract_suprematism(shape, seed, sm, n_forms=7, **kwargs):
    """abstract_suprematism.

    identity (R6 creative rebuild): Malevich's pure-geometric aesthetic pushed
    further — a DARK void canvas with HARD-EDGED geometric forms in three
    new clarity tiers: (a) ANCHOR composition forms (large-ish 18-28 px
    titled bars + signature BLACK SQUARES + RED TRAPEZOIDS — Malevich's
    red plane), (b) MID-TIER orbital forms (12-18 px tilted bars,
    diagonals, triangles), (c) MICRO accent forms (4-9 px squares & dots
    for figure density). NEW differentiators: (i) RED TRAPEZOID — Malevich's
    "Red Square" stand-in with high-M warm-band fill, (ii) PARALLEL DIAGONAL
    BARS — clustered same-angle bars suggesting Suprematist motion vector,
    (iii) crisp aerial cluster compositions where 2-4 forms group with
    common tilt. Per-form INDEPENDENT continuous M/R/CC. Void darker than
    every form.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("abstract_suprematism_r6") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # DARK MALEVICH VOID with very subtle tooth
    tooth = _normalize(multi_scale_noise(shape, [2.5, 7.0, 18.0], [0.5, 0.3, 0.2], int(seed) + 10167))
    M = (0.14 + (tooth - 0.5) * 0.07).astype(np.float32)
    R = (0.74 + (tooth - 0.5) * 0.07).astype(np.float32)
    CC = (0.60 + (tooth - 0.5) * 0.07).astype(np.float32)

    if _CV2_OK:
        # TIER A — ANCHOR FORMS: 6-10 hero pieces with signature shapes including red trapezoid
        ang_pref = [0.0, np.pi/4, -np.pi/4, np.pi/2, np.pi/6, -np.pi/6, np.pi/3, -np.pi/3]
        n_anchors = int(rng.integers(6, 11))
        for _ in range(n_anchors):
            cx_e = float(rng.uniform(0.10 * w, 0.90 * w))
            cy_e = float(rng.uniform(0.10 * h, 0.90 * h))
            rot_e = float(ang_pref[int(rng.integers(0, len(ang_pref)))]) + float(rng.uniform(-0.10, 0.10))
            anchor_kind = int(rng.integers(0, 4))
            sz_a = float(rng.uniform(mn * 0.030, mn * 0.060))
            if anchor_kind == 0:
                # RED TRAPEZOID — high warm chroma
                rw_e = sz_a * float(rng.uniform(1.4, 2.4))
                rh_e = sz_a * float(rng.uniform(0.55, 0.85))
                taper = sz_a * float(rng.uniform(0.15, 0.45))
                ca_e, sa_e = np.cos(rot_e), np.sin(rot_e)
                pts_e = []
                for px, py in [(-rw_e, -rh_e), (rw_e - taper, -rh_e), (rw_e, rh_e), (-rw_e + taper, rh_e)]:
                    pts_e.append([int(np.clip(cx_e + px * ca_e - py * sa_e, 0, w - 1)),
                                  int(np.clip(cy_e + px * sa_e + py * ca_e, 0, h - 1))])
                pts_arr = np.asarray(pts_e, dtype=np.int32)
                _cv2.fillPoly(M, [pts_arr], float(rng.uniform(0.78, 0.96)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts_arr], float(rng.uniform(0.18, 0.40)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts_arr], float(rng.uniform(0.06, 0.22)), lineType=_cv2.LINE_AA)
            elif anchor_kind == 1:
                # ANCHOR BLACK SQUARE
                ca_e, sa_e = np.cos(rot_e * 0.3), np.sin(rot_e * 0.3)
                pts_e = np.asarray([[int(np.clip(cx_e + px * ca_e - py * sa_e, 0, w - 1)),
                                      int(np.clip(cy_e + px * sa_e + py * ca_e, 0, h - 1))]
                                     for px, py in [(-sz_a, -sz_a), (sz_a, -sz_a), (sz_a, sz_a), (-sz_a, sz_a)]],
                                    dtype=np.int32)
                _cv2.fillPoly(M, [pts_e], float(rng.uniform(0.06, 0.18)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts_e], float(rng.uniform(0.55, 0.88)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts_e], float(rng.uniform(0.45, 0.80)), lineType=_cv2.LINE_AA)
            elif anchor_kind == 2:
                # LARGE TILTED BAR
                rw_e = sz_a * float(rng.uniform(2.2, 3.5)); rh_e = sz_a * float(rng.uniform(0.20, 0.40))
                ca_e, sa_e = np.cos(rot_e), np.sin(rot_e)
                pts_e = np.asarray([[int(np.clip(cx_e + px * ca_e - py * sa_e, 0, w - 1)),
                                      int(np.clip(cy_e + px * sa_e + py * ca_e, 0, h - 1))]
                                     for px, py in [(-rw_e, -rh_e), (rw_e, -rh_e), (rw_e, rh_e), (-rw_e, rh_e)]],
                                    dtype=np.int32)
                _cv2.fillPoly(M, [pts_e], float(rng.uniform(0.45, 0.92)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts_e], float(rng.uniform(0.12, 0.55)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts_e], float(rng.uniform(0.10, 0.42)), lineType=_cv2.LINE_AA)
            else:
                # CIRCLE/DISC anchor (Malevich did circles too)
                rr_a = int(sz_a * float(rng.uniform(0.7, 1.1)))
                _cv2.circle(M, (int(cx_e), int(cy_e)), rr_a, float(rng.uniform(0.40, 0.92)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (int(cx_e), int(cy_e)), rr_a, float(rng.uniform(0.14, 0.55)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (int(cx_e), int(cy_e)), rr_a, float(rng.uniform(0.08, 0.40)), -1, lineType=_cv2.LINE_AA)

        # TIER A2 — PARALLEL DIAGONAL BAR CLUSTERS (Suprematist motion vectors, NEW)
        n_clusters = int(rng.integers(3, 6))
        for _ in range(n_clusters):
            base_ang = float(ang_pref[int(rng.integers(0, len(ang_pref)))])
            cluster_cx = float(rng.uniform(0.12 * w, 0.88 * w))
            cluster_cy = float(rng.uniform(0.12 * h, 0.88 * h))
            n_bars = int(rng.integers(3, 6))
            ca_b, sa_b = np.cos(base_ang + np.pi/2), np.sin(base_ang + np.pi/2)
            for k in range(n_bars):
                offset = (k - n_bars * 0.5) * mn * 0.014
                bcx = cluster_cx + ca_b * offset
                bcy = cluster_cy + sa_b * offset
                bl = float(rng.uniform(mn * 0.04, mn * 0.10))
                thick = max(2, int(rng.uniform(1.5, 3.0) * scale))
                x0 = int(np.clip(bcx - np.cos(base_ang) * bl * 0.5, 0, w - 1))
                y0 = int(np.clip(bcy - np.sin(base_ang) * bl * 0.5, 0, h - 1))
                x1 = int(np.clip(bcx + np.cos(base_ang) * bl * 0.5, 0, w - 1))
                y1 = int(np.clip(bcy + np.sin(base_ang) * bl * 0.5, 0, h - 1))
                _cv2.line(M, (x0, y0), (x1, y1), float(rng.uniform(0.32, 0.85)), thick, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x0, y0), (x1, y1), float(rng.uniform(0.18, 0.55)), thick, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.10, 0.45)), thick, lineType=_cv2.LINE_AA)

        # TIER B — MID-TIER FORMS (formerly the only tier)
        n_elements = int(np.clip(120 + n_forms * 8, 80, 280))
        for i in range(n_elements):
            kind = int(rng.integers(0, 4))
            cx_e = float(rng.uniform(0.04 * w, 0.96 * w))
            cy_e = float(rng.uniform(0.04 * h, 0.96 * h))
            sz = float(rng.uniform(mn * 0.012, mn * 0.045))
            # Malevich signature angles - prefer 0, 45, -45, plus tilts
            ang_pref = [0.0, np.pi/4, -np.pi/4, np.pi/2, np.pi/6, -np.pi/6]
            rot_e = float(ang_pref[int(rng.integers(0, len(ang_pref)))]) + float(rng.uniform(-0.20, 0.20))
            # INDEPENDENT continuous uniforms per form
            fM = float(rng.uniform(0.25, 0.92))
            fR = float(rng.uniform(0.15, 0.65))
            fCC = float(rng.uniform(0.06, 0.45))
            if kind == 0:  # TILTED BAR (Suprematist primary)
                rw_e = sz * float(rng.uniform(0.8, 2.6)); rh_e = sz * float(rng.uniform(0.25, 0.55))
                ca_e, sa_e = np.cos(rot_e), np.sin(rot_e)
                pts_e = np.asarray([[int(np.clip(cx_e + px * ca_e - py * sa_e, 0, w - 1)),
                                      int(np.clip(cy_e + px * sa_e + py * ca_e, 0, h - 1))]
                                     for px, py in [(-rw_e, -rh_e), (rw_e, -rh_e), (rw_e, rh_e), (-rw_e, rh_e)]],
                                    dtype=np.int32)
                _cv2.fillPoly(M, [pts_e], fM, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts_e], fR, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts_e], fCC, lineType=_cv2.LINE_AA)
            elif kind == 1:  # ANCHOR BLACK SQUARE (Malevich's most famous motif)
                ca_e, sa_e = np.cos(rot_e * 0.3), np.sin(rot_e * 0.3)
                pts_e = np.asarray([[int(np.clip(cx_e + px * ca_e - py * sa_e, 0, w - 1)),
                                      int(np.clip(cy_e + px * sa_e + py * ca_e, 0, h - 1))]
                                     for px, py in [(-sz, -sz), (sz, -sz), (sz, sz), (-sz, sz)]],
                                    dtype=np.int32)
                # Dark anchor squares - LOW M, HIGH R, MID-HIGH CC (black ink)
                _cv2.fillPoly(M, [pts_e], float(rng.uniform(0.08, 0.22)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts_e], float(rng.uniform(0.50, 0.85)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts_e], float(rng.uniform(0.45, 0.80)), lineType=_cv2.LINE_AA)
            elif kind == 2:  # DIAGONAL BAR (thick line - Suprematist vector)
                ll = sz * float(rng.uniform(2.0, 5.0))
                ex = int(np.clip(cx_e + np.cos(rot_e) * ll, 0, w - 1))
                ey = int(np.clip(cy_e + np.sin(rot_e) * ll, 0, h - 1))
                thick = max(2, int(rng.uniform(1.5, 3.5) * scale))
                _cv2.line(M, (int(cx_e), int(cy_e)), (ex, ey), fM, thick, lineType=_cv2.LINE_AA)
                _cv2.line(R, (int(cx_e), int(cy_e)), (ex, ey), fR, thick, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (int(cx_e), int(cy_e)), (ex, ey), fCC, thick, lineType=_cv2.LINE_AA)
            else:  # TRIANGLE (Malevich's third primary form)
                pts_t = []
                for k in range(3):
                    a = rot_e + k * 2.094
                    pts_t.append([int(np.clip(cx_e + np.cos(a) * sz, 0, w - 1)),
                                  int(np.clip(cy_e + np.sin(a) * sz, 0, h - 1))])
                pts_arr = np.asarray(pts_t, dtype=np.int32)
                _cv2.fillPoly(M, [pts_arr], fM, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts_arr], fR, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts_arr], fCC, lineType=_cv2.LINE_AA)

        # SECONDARY tiny geometric accents (4-9 px squares for figure density)
        n_acc = int(np.clip(700 * (mn / 2048.0) ** 2, 250, 1800))
        for _ in range(n_acc):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            ss = max(1, int(rng.uniform(2.0, 4.5) * scale))
            _cv2.rectangle(M, (cx - ss, cy - ss), (cx + ss, cy + ss), float(rng.uniform(0.25, 0.92)), -1, lineType=_cv2.LINE_AA)
            _cv2.rectangle(R, (cx - ss, cy - ss), (cx + ss, cy + ss), float(rng.uniform(0.15, 0.65)), -1, lineType=_cv2.LINE_AA)
            _cv2.rectangle(CC, (cx - ss, cy - ss), (cx + ss, cy + ss), float(rng.uniform(0.08, 0.45)), -1, lineType=_cv2.LINE_AA)

    # Pigment specks in the void
    n_fl = int(np.clip(900 * (mn / 2048.0) ** 2, 280, 2400))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx]  = np.clip(M[fy, fx]  + rng.uniform(-0.05, 0.18, n_fl).astype(np.float32), 0, 1)
    R[fy, fx]  = np.clip(R[fy, fx]  + rng.uniform(-0.10, 0.10, n_fl).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.10, 0.10, n_fl).astype(np.float32), 0, 1)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
abstract_suprematism._spb_concept_complete = True


def abstract_futurist_motion(shape, seed, sm, **kwargs):
    """abstract_futurist_motion — R6 CREATIVE rebuild.

    identity: Balla/Boccioni dynamism — but now with a clear HERO MOTIF:
    a single bold STAGGERED-MULTIPLE-EXPOSURE silhouette (echo-train of
    3-5 chevron wedge ghosts marching across the frame, each a translated
    & chromatically offset copy of the previous, like Marcel Duchamp's
    "Nude Descending a Staircase"). Around the hero echo-train: a finer
    weave of FORCE-LINE arcs (curved speed paths, not straight rays) that
    spiral around the motion axis, plus directional dust granules and
    tight chromatic-aberration twin lines. Per-feature INDEPENDENT
    continuous M/R/CC so the dynamism is polychrome, never uniform.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 10170)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) ANISOTROPIC HAZE BACKGROUND — directional FBM substrate
    motion_ang = float(rng.uniform(-0.45, 0.45))  # near-horizontal sweep
    cos_a = float(np.cos(motion_ang)); sin_a = float(np.sin(motion_ang))
    haze_m = _normalize(multi_scale_noise(shape, [3.0, 7.0, 14.0], [0.55, 0.30, 0.15], int(seed) + 10171))
    haze_r = _normalize(multi_scale_noise(shape, [3.5, 8.0, 15.0], [0.55, 0.30, 0.15], int(seed) + 10172))
    haze_c = _normalize(multi_scale_noise(shape, [4.0, 9.0, 16.0], [0.55, 0.30, 0.15], int(seed) + 10173))
    M = (0.32 + (haze_m - 0.5) * 0.30).astype(np.float32)
    R = (0.55 + (haze_r - 0.5) * 0.30).astype(np.float32)
    CC = (0.50 + (haze_c - 0.5) * 0.32).astype(np.float32)

    if _CV2_OK:
        # 2) HERO: ECHO-TRAIN OF 3-5 CHEVRON GHOSTS marching across canvas
        n_echo = int(rng.integers(3, 6))
        # Echo march path
        echo_start_x = float(rng.uniform(0.05, 0.25)) * w
        echo_start_y = float(rng.uniform(0.30, 0.70)) * h
        step_x = float(rng.uniform(0.12, 0.22)) * w
        step_y = float(rng.uniform(-0.10, 0.10)) * h
        chevron_arm_len = float(rng.uniform(14.0, 28.0) * (0.7 + scale))  # 14-32 px
        chevron_th = max(1, int(rng.uniform(1.5, 3.0)))
        for k in range(n_echo):
            # alpha fades from clear (head) to ghost (tail)
            ghost_alpha = 1.0 - (k / max(1, n_echo - 1)) * 0.55
            cx = echo_start_x + k * step_x
            cy = echo_start_y + k * step_y
            # 3-arm chevron wedge
            for arm_a in (motion_ang - 0.55, motion_ang, motion_ang + 0.55):
                ex = int(cx + np.cos(arm_a) * chevron_arm_len)
                ey = int(cy + np.sin(arm_a) * chevron_arm_len)
                eM = float(rng.uniform(0.55, 0.95)) * ghost_alpha + 0.10 * (1 - ghost_alpha)
                eR = float(rng.uniform(0.10, 0.45)) + 0.10 * (1 - ghost_alpha)
                eCC = float(rng.uniform(0.50, 0.92)) * ghost_alpha + 0.20 * (1 - ghost_alpha)
                _cv2.line(M, (int(cx), int(cy)), (ex, ey), eM, chevron_th, lineType=_cv2.LINE_AA)
                _cv2.line(R, (int(cx), int(cy)), (ex, ey), eR, chevron_th, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (int(cx), int(cy)), (ex, ey), eCC, chevron_th, lineType=_cv2.LINE_AA)
            # Add inner dot for the wedge "joint"
            _cv2.circle(M, (int(cx), int(cy)), max(2, int(chevron_arm_len * 0.18)),
                         float(rng.uniform(0.70, 0.98)) * ghost_alpha, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (int(cx), int(cy)), max(2, int(chevron_arm_len * 0.18)),
                         float(rng.uniform(0.30, 0.60)), -1, lineType=_cv2.LINE_AA)

        # 3) FORCE-LINE ARCS — curved speed paths (segmented polylines)
        n_arc = int(np.clip(80 * (mn / 256.0) ** 2, 120, 360))
        for _ in range(n_arc):
            cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
            r_arc = float(rng.uniform(20.0, 60.0))
            curvature = float(rng.uniform(-0.04, 0.04))
            ang0 = float(rng.uniform(0, 2 * np.pi))
            n_seg = int(rng.integers(3, 6))
            seg_len = float(rng.uniform(6.0, 14.0))
            pts = []
            x_cur, y_cur, a_cur = cx, cy, ang0
            for s in range(n_seg + 1):
                pts.append([int(x_cur), int(y_cur)])
                x_cur += np.cos(a_cur) * seg_len; y_cur += np.sin(a_cur) * seg_len; a_cur += curvature
            arr = np.array([pts], dtype=np.int32)
            aM = float(rng.uniform(0.20, 0.85))
            aR = float(rng.uniform(0.15, 0.50))
            aCC = float(rng.uniform(0.30, 0.85))
            _cv2.polylines(M, arr, False, aM, 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(R, arr, False, aR, 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, arr, False, aCC, 1, lineType=_cv2.LINE_AA)

        # 4) STRAIGHT SPEED STREAKS — short directional darts (8-22 px)
        n_streak = int(np.clip(320 * (mn / 256.0) ** 2, 360, 1500))
        for _ in range(n_streak):
            cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
            length = float(rng.uniform(8.0, 22.0) * (0.7 + scale))
            ang = motion_ang + float(rng.normal(0, 0.12))
            x0s = int(cx); y0s = int(cy)
            x1s = int(cx + np.cos(ang) * length); y1s = int(cy + np.sin(ang) * length)
            sM = float(rng.uniform(0.15, 0.92))
            sR = float(rng.uniform(0.10, 0.55))
            sCC = float(rng.uniform(0.25, 0.92))
            _cv2.line(M, (x0s, y0s), (x1s, y1s), sM, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0s, y0s), (x1s, y1s), sR, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0s, y0s), (x1s, y1s), sCC, 1, lineType=_cv2.LINE_AA)
            # chromatic aberration twin — small perpendicular offset (CC ghost)
            offx = int(-np.sin(ang) * 2.0); offy = int(np.cos(ang) * 2.0)
            _cv2.line(CC, (x0s + offx, y0s + offy), (x1s + offx, y1s + offy),
                       float(rng.uniform(0.40, 0.90)), 1, lineType=_cv2.LINE_AA)

        # 5) DIRECTIONAL DUST GRANULES
        n_dust = int(np.clip(1800 * (mn / 1024.0) ** 2, 800, 5400))
        dy = rng.integers(0, h, n_dust); dx = rng.integers(0, w, n_dust)
        M[dy, dx] = np.maximum(M[dy, dx], rng.uniform(0.60, 0.95, n_dust).astype(np.float32))
        CC[dy, dx] = np.maximum(CC[dy, dx], rng.uniform(0.55, 0.90, n_dust).astype(np.float32))

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_futurist_motion")
abstract_futurist_motion._spb_concept_complete = True


def abstract_minimalist_stripe(shape, seed, sm, **kwargs):
    """abstract_minimalist_stripe.

    identity: Round-6 CREATIVE rebuild — Agnes Martin minimalist evolved.
    8-14 hand-pulled parallel pencil stripes (no longer just 4-7) at varied
    widths 2-6 px, each with its own INDEPENDENT M/R/CC continuous uniform.
    Each primary stripe is shadowed by a ghost-stripe 3-6 px to one side at
    half intensity, giving a contemplative "memory of the line" doubled
    rhythm. Between the stripes: hand-laid pencil-dust speckle (1-2 px
    micro-dots), faint perpendicular cross-tick reference marks (3-6 px),
    and a quiet 3-channel grain ground. Negative space still dominates; the
    composition stays meditative, but the chroma diversity sings.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 10220)
    scale = max(min(h, w) / 2048.0, 0.25)

    # 1) QUIET GRAIN GROUND — 3 independent channels, hand-laid feel
    g_m = _normalize(multi_scale_noise(shape, [2.0, 4.5, 9.0], [0.5, 0.32, 0.18], int(seed) + 10221))
    g_r = _normalize(multi_scale_noise(shape, [2.2, 4.8, 9.5], [0.5, 0.32, 0.18], int(seed) + 10222))
    g_c = _normalize(multi_scale_noise(shape, [2.4, 5.0, 10.0], [0.5, 0.32, 0.18], int(seed) + 10223))
    M = (0.38 + (g_m - 0.5) * 0.14).astype(np.float32)
    R = (0.55 + (g_r - 0.5) * 0.14).astype(np.float32)
    CC = (0.50 + (g_c - 0.5) * 0.16).astype(np.float32)

    # 2) PRIMARY STRIPES — 8-14, each with ghost-shadow companion
    n_stripes = int(rng.integers(8, 15))
    horizontal = bool(rng.integers(0, 2))
    edge = w if horizontal else h
    perp = h if horizontal else w
    positions = sorted(rng.uniform(edge * 0.05, edge * 0.95, n_stripes))
    min_gap = edge / (n_stripes * 1.6)
    cleaned = [positions[0]]
    for p in positions[1:]:
        if p - cleaned[-1] >= min_gap:
            cleaned.append(p)
    stripe_records = []
    for p in cleaned:
        width = max(1, int(rng.uniform(2, 6) * max(scale, 1.0)))
        m_v = float(rng.uniform(0.10, 0.93))
        r_v = float(rng.uniform(0.08, 0.88))
        c_v = float(rng.uniform(0.15, 0.96))
        pi = int(p)
        if horizontal:
            x0 = max(0, pi - width); x1 = min(w, pi + width + 1)
            M[:, x0:x1] = m_v; R[:, x0:x1] = r_v; CC[:, x0:x1] = c_v
        else:
            y0 = max(0, pi - width); y1 = min(h, pi + width + 1)
            M[y0:y1, :] = m_v; R[y0:y1, :] = r_v; CC[y0:y1, :] = c_v
        stripe_records.append((pi, width, m_v, r_v, c_v))

    # 3) GHOST-STRIPES — half-strength shadow stripes offset 3-6 px from each primary
    for (pi, width, m_v, r_v, c_v) in stripe_records:
        offset = int(rng.uniform(3, 6) * max(scale, 1.0)) * int(rng.choice([-1, 1]))
        gp = pi + offset
        if gp < 1 or gp > edge - 1:
            continue
        gw = max(1, width // 2)
        # Half-strength blend with ground
        gm = float((m_v + 0.38) * 0.5 + rng.uniform(-0.04, 0.04))
        gr = float((r_v + 0.55) * 0.5 + rng.uniform(-0.04, 0.04))
        gc = float((c_v + 0.50) * 0.5 + rng.uniform(-0.04, 0.04))
        if horizontal:
            x0 = max(0, gp - gw); x1 = min(w, gp + gw + 1)
            M[:, x0:x1] = M[:, x0:x1] * 0.45 + gm * 0.55
            R[:, x0:x1] = R[:, x0:x1] * 0.45 + gr * 0.55
            CC[:, x0:x1] = CC[:, x0:x1] * 0.45 + gc * 0.55
        else:
            y0 = max(0, gp - gw); y1 = min(h, gp + gw + 1)
            M[y0:y1, :] = M[y0:y1, :] * 0.45 + gm * 0.55
            R[y0:y1, :] = R[y0:y1, :] * 0.45 + gr * 0.55
            CC[y0:y1, :] = CC[y0:y1, :] * 0.45 + gc * 0.55

    # 4) PENCIL-DUST SPECKLE — 1-2 px micro-dots scattered in negative space
    n_dust = int(np.clip(1400 * (min(h, w) / 2048.0) ** 2, 500, 3500))
    fy = rng.integers(0, h, n_dust); fx = rng.integers(0, w, n_dust)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(-0.18, 0.18, n_dust).astype(np.float32), 0, 1)
    R[fy, fx] = np.clip(R[fy, fx] + rng.uniform(-0.12, 0.20, n_dust).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.14, 0.22, n_dust).astype(np.float32), 0, 1)

    # 5) CROSS-TICK REFERENCE MARKS — short perpendicular ticks
    if _CV2_OK:
        n_tick = int(np.clip(280 * (min(h, w) / 2048.0) ** 2, 80, 600))
        for _ in range(n_tick):
            cx = int(rng.integers(2, w - 2)); cy = int(rng.integers(2, h - 2))
            tl = int(rng.uniform(3, 6) * max(scale, 1.0))
            if horizontal:
                x0, y0, x1, y1 = cx, cy - tl, cx, cy + tl
            else:
                x0, y0, x1, y1 = cx - tl, cy, cx + tl, cy
            tM = float(rng.uniform(0.20, 0.85))
            tR = float(rng.uniform(0.15, 0.78))
            tCC = float(rng.uniform(0.20, 0.92))
            _cv2.line(M, (x0, y0), (x1, y1), tM, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0, y0), (x1, y1), tR, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), tCC, 1, lineType=_cv2.LINE_AA)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_minimalist_stripe")
abstract_minimalist_stripe._spb_concept_complete = True


def abstract_hard_edge_field(shape, seed, sm, **kwargs):
    """abstract_hard_edge_field.

    identity: R6 creative rebuild (tick53 second-pass) — Ellsworth Kelly
    meets De Stijl meets Lichtenstein. NEW HERO (tick53): BEN-DAY DOT
    OVERPRINT — 1-2 random blocks receive a regular grid of 3-5 px dots
    spaced 6-9 px apart, creating a Lichtenstein-comic-print zone inside
    the otherwise flat polychrome plane. Dots have INDEPENDENT M/R/CC.
    Stacked on prior heroes: BSP 12-20 flat block field, 2-4 large
    quadrant HERO arc-cuts, 3-6 thin Mondrian-style PIPED BARS, razor
    edge piping. Each block, arc, bar, and dot carries INDEPENDENT
    continuous M/R/CC across the full gamut.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("abstract_hard_edge_field_r6") % 10000) + 10200)
    scale = max(min(h, w) / 2048.0, 0.25)

    # 1) BASE — neutral mid (will be largely overwritten)
    M = np.full((h, w), 0.40, dtype=np.float32)
    R = np.full((h, w), 0.50, dtype=np.float32)
    CC = np.full((h, w), 0.55, dtype=np.float32)

    # 2) RECURSIVE BSP BLOCK FIELD — 12-20 saturated flat blocks
    blocks = [(0, 0, w, h)]
    n_splits = int(rng.integers(11, 20))
    for _ in range(n_splits):
        blocks.sort(key=lambda b: -(b[2] - b[0]) * (b[3] - b[1]))
        x0, y0, x1, y1 = blocks.pop(0)
        if (x1 - x0) > (y1 - y0):
            sx = int(rng.uniform(0.25, 0.75) * (x1 - x0)) + x0
            blocks.append((x0, y0, sx, y1))
            blocks.append((sx, y0, x1, y1))
        else:
            sy = int(rng.uniform(0.25, 0.75) * (y1 - y0)) + y0
            blocks.append((x0, y0, x1, sy))
            blocks.append((x0, sy, x1, y1))
    for (x0, y0, x1, y1) in blocks:
        m_v = float(rng.uniform(0.08, 0.96))
        r_v = float(rng.uniform(0.08, 0.94))
        c_v = float(rng.uniform(0.10, 0.96))
        M[y0:y1, x0:x1] = m_v
        R[y0:y1, x0:x1] = r_v
        CC[y0:y1, x0:x1] = c_v
        # razor-edge contrast piping
        edge_m = float(np.clip(m_v + rng.uniform(-0.40, 0.40), 0.0, 1.0))
        edge_c = float(np.clip(c_v + rng.uniform(-0.40, 0.40), 0.0, 1.0))
        if y0 + 1 < h:
            M[y0:y0 + 1, x0:x1] = edge_m; CC[y0:y0 + 1, x0:x1] = edge_c
        if x0 + 1 < w:
            M[y0:y1, x0:x0 + 1] = edge_m; CC[y0:y1, x0:x0 + 1] = edge_c

    # 3) HERO ARC CUTS — 2-4 quadrant circles / half-circles
    yy_i, xx_i = np.mgrid[0:h, 0:w]
    yy_f = yy_i.astype(np.float32); xx_f = xx_i.astype(np.float32)
    n_arc = int(rng.integers(2, 5))
    for _ in range(n_arc):
        cx = float(rng.uniform(-w * 0.20, w * 1.20))
        cy = float(rng.uniform(-h * 0.20, h * 1.20))
        rad = float(rng.uniform(0.30, 0.70)) * min(h, w)
        d2 = (xx_f - cx) ** 2 + (yy_f - cy) ** 2
        mask = d2 <= (rad * rad)
        a_M = float(rng.uniform(0.06, 0.96))
        a_R = float(rng.uniform(0.06, 0.94))
        a_C = float(rng.uniform(0.08, 0.96))
        M[mask] = a_M
        R[mask] = a_R
        CC[mask] = a_C
        # razor-thin arc edge
        edge_mask = (np.abs(np.sqrt(d2) - rad) < max(1.2, 1.5 * scale))
        e_M = float(np.clip(a_M + rng.uniform(-0.50, 0.50), 0.0, 1.0))
        e_C = float(np.clip(a_C + rng.uniform(-0.50, 0.50), 0.0, 1.0))
        M[edge_mask] = e_M
        CC[edge_mask] = e_C

    if _CV2_OK:
        # 4) PIPED ACCENT BARS — 3-6 thin saturated bars (Mondrian-style)
        n_bar = int(rng.integers(3, 7))
        for _ in range(n_bar):
            horizontal = rng.random() < 0.5
            if horizontal:
                yb = int(rng.uniform(h * 0.05, h * 0.95))
                xb0 = int(rng.uniform(0, w * 0.30))
                xb1 = int(rng.uniform(w * 0.70, w))
                thk = max(2, int(rng.uniform(2.0, 4.0) * scale))
                bM = float(rng.uniform(0.05, 0.97))
                bR = float(rng.uniform(0.05, 0.95))
                bC = float(rng.uniform(0.05, 0.97))
                _cv2.line(M, (xb0, yb), (xb1, yb), bM, thk)
                _cv2.line(R, (xb0, yb), (xb1, yb), bR, thk)
                _cv2.line(CC, (xb0, yb), (xb1, yb), bC, thk)
            else:
                xb = int(rng.uniform(w * 0.05, w * 0.95))
                yb0 = int(rng.uniform(0, h * 0.30))
                yb1 = int(rng.uniform(h * 0.70, h))
                thk = max(2, int(rng.uniform(2.0, 4.0) * scale))
                bM = float(rng.uniform(0.05, 0.97))
                bR = float(rng.uniform(0.05, 0.95))
                bC = float(rng.uniform(0.05, 0.97))
                _cv2.line(M, (xb, yb0), (xb, yb1), bM, thk)
                _cv2.line(R, (xb, yb0), (xb, yb1), bR, thk)
                _cv2.line(CC, (xb, yb0), (xb, yb1), bC, thk)

        # 4b) NEW HERO tick53 — BEN-DAY DOT OVERPRINT inside 1-2 blocks.
        # Lichtenstein-style regular dot grid produces a comic-print zone.
        if len(blocks) >= 2:
            n_dot_blocks = int(rng.integers(1, min(3, len(blocks) + 1)))
            chosen = rng.choice(len(blocks), size=n_dot_blocks, replace=False)
            for bi in chosen:
                bx0, by0, bx1, by1 = blocks[int(bi)]
                if (bx1 - bx0) < 24 or (by1 - by0) < 24:
                    continue
                spacing = max(6, int(rng.uniform(6.5, 9.0) * scale))
                dot_r = max(2, int(rng.uniform(2.0, 3.0) * scale))
                dM = float(rng.uniform(0.08, 0.96))
                dR = float(rng.uniform(0.08, 0.94))
                dCC = float(rng.uniform(0.08, 0.96))
                for dy_ in range(by0 + spacing, by1 - spacing, spacing):
                    row_offset = (dy_ // spacing) % 2  # brick offset
                    for dx_ in range(bx0 + spacing + row_offset * (spacing // 2),
                                     bx1 - spacing, spacing):
                        _cv2.circle(M, (dx_, dy_), dot_r, dM, -1, lineType=_cv2.LINE_AA)
                        _cv2.circle(R, (dx_, dy_), dot_r, dR, -1, lineType=_cv2.LINE_AA)
                        _cv2.circle(CC, (dx_, dy_), dot_r, dCC, -1, lineType=_cv2.LINE_AA)

    # 5) FINE GRAIN — extremely subtle so planes stay flat
    grain = _normalize(multi_scale_noise(shape, [2.5, 6.0], [0.6, 0.4], int(seed) + 10202)) - 0.5
    R = R + grain * 0.04

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_hard_edge_field")
abstract_hard_edge_field._spb_concept_complete = True


def abstract_color_field_bleed(shape, seed, sm, num_fields=4, bleed=0.06,
                                 **kwargs):
    """abstract_color_field_bleed.

    identity: ROUND-6 CREATIVE REBUILD — Frankenthaler-style stain canvas
    with three HERO MOTIFS layered onto the soft Voronoi bleed:
      (1) per-channel FBM-WARPED boundaries — the Voronoi seam coordinates
          are displaced by independent FBM warp fields, producing
          watercolor-organic edges instead of disc-shaped regions;
      (2) DYE-FRONT FINGERS — wet-edge capillary fingers (short 6-14 px
          tapered lines) reaching outward from the seam in the dominant
          neighbor's chroma, like dye creeping along paper fiber;
      (3) SALT-BLEED CRYSTAL ROSETTES — small 5-12 px starburst rosettes
          (8-spoke radial sprays) scattered along the boundaries, the
          signature texture of salt thrown on wet watercolor;
      (4) paper-fold seam highlights — thin 8-20 px straight bright
          lines that cross the canvas like creases in cotton duck.
    All on top of the Gaussian-feathered soft bleed substrate with
    raw-canvas tooth and capillary speckles. Independent continuous
    M/R/CC per region AND per feature.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("abstract_color_field_bleed_r6") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # SATURATED REGION ASSIGNMENT
    # R6-TICK79 palette discipline: cap M <= 0.45 (anti-magenta) and R <= 0.30
    # (anti-neon-green) on the substrate; let HERO motifs (dendrites + folds)
    # push brightness selectively. Cool/violet/stone bias so the soft bleed
    # reads as watercolor, not racing chroma.
    n_regions = max(3, int(num_fields) + int(rng.integers(0, 3)))
    sy = rng.uniform(0, h, n_regions).astype(np.float32)
    sx = rng.uniform(0, w, n_regions).astype(np.float32)
    reg_M  = rng.uniform(0.18, 0.44, n_regions).astype(np.float32)
    reg_R  = rng.uniform(0.12, 0.28, n_regions).astype(np.float32)
    reg_CC = rng.uniform(0.20, 0.74, n_regions).astype(np.float32)

    # 1) HERO — per-channel FBM-warped boundaries
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp_m = _normalize(_spb_fast_smooth_noise(shape, [3.0, 8.0], [0.6, 0.4], int(seed) + 10210, max_dim=768))
    warp_r = _normalize(_spb_fast_smooth_noise(shape, [3.5, 9.0], [0.6, 0.4], int(seed) + 10211, max_dim=768))
    warp_c = _normalize(_spb_fast_smooth_noise(shape, [4.0, 10.0], [0.6, 0.4], int(seed) + 10212, max_dim=768))
    warp_amp = mn * 0.08
    # Apply same warp to coordinates for soft bleed weights below
    yy_w = yy + (warp_m - 0.5) * warp_amp
    xx_w = xx + (warp_r - 0.5) * warp_amp
    wsum = np.zeros((h, w), dtype=np.float32)
    acc_M = np.zeros((h, w), dtype=np.float32)
    acc_R = np.zeros((h, w), dtype=np.float32)
    acc_CC = np.zeros((h, w), dtype=np.float32)
    for i in range(n_regions):
        d2 = (yy_w - sy[i]) ** 2 + (xx_w - sx[i]) ** 2 + 1.0
        wi = (1.0 / (d2 ** 0.95)).astype(np.float32)
        wsum += wi
        acc_M += wi * reg_M[i]
        acc_R += wi * reg_R[i]
        acc_CC += wi * reg_CC[i]
    inv_wsum = 1.0 / np.maximum(wsum, 1e-6)
    M  = (acc_M * inv_wsum).astype(np.float32)
    R  = (acc_R * inv_wsum).astype(np.float32)
    CC = (acc_CC * inv_wsum).astype(np.float32)

    # GAUSSIAN FEATHER substrate
    if _CV2_OK:
        sig = max(2.0, mn * (0.005 + bleed * 0.3))
        if max(h, w) > 1024:
            blur_ds = 2
            small_size = (max(128, w // blur_ds), max(128, h // blur_ds))
            blur_sig = max(1.0, sig / blur_ds)
            def _blur_soft_field(field):
                small = _cv2.resize(field, small_size, interpolation=_cv2.INTER_AREA)
                soft = _cv2.GaussianBlur(small, (0, 0), sigmaX=blur_sig, sigmaY=blur_sig)
                return _cv2.resize(soft, (w, h), interpolation=_cv2.INTER_LINEAR)
            M = _blur_soft_field(M)
            R = _blur_soft_field(R)
            CC = _blur_soft_field(CC)
        else:
            M  = _cv2.GaussianBlur(M,  (0, 0), sigmaX=sig, sigmaY=sig)
            R  = _cv2.GaussianBlur(R,  (0, 0), sigmaX=sig, sigmaY=sig)
            CC = _cv2.GaussianBlur(CC, (0, 0), sigmaX=sig, sigmaY=sig)

    # Per-channel independent micro-warps on each channel using the OTHER warps for desync
    M = np.clip(M + (warp_r - 0.5) * 0.08, 0, 1).astype(np.float32)
    R = np.clip(R + (warp_c - 0.5) * 0.08, 0, 1).astype(np.float32)
    CC = np.clip(CC + (warp_m - 0.5) * 0.08, 0, 1).astype(np.float32)

    # Raw canvas tooth
    weave = _normalize(_spb_fast_smooth_noise(shape, [1.4, 3.0, 6.0], [0.5, 0.3, 0.2], int(seed) + 10204, max_dim=768))
    M = np.clip(M + (weave - 0.5) * 0.07, 0, 1)
    R = np.clip(R + (weave - 0.5) * 0.07, 0, 1)
    CC = np.clip(CC + (weave - 0.5) * 0.06, 0, 1)

    if _CV2_OK:
        # 2) DYE-FRONT FINGERS — tapered capillary fingers 6-14 px
        # 2026-05-30 perf pass: keep all fine motif tiers, but trim redundant
        # draw-call density. Feature size remains 1-14 px; density stays high.
        n_fingers = int(np.clip(740 * scale * scale, 280, 2200))
        for _ in range(n_fingers):
            cx = int(rng.uniform(6, w - 6)); cy = int(rng.uniform(6, h - 6))
            ang = float(rng.uniform(0, 2 * np.pi))
            length = float(rng.uniform(6.0, 14.0) * scale)
            x2 = int(np.clip(cx + np.cos(ang) * length, 0, w - 1))
            y2 = int(np.clip(cy + np.sin(ang) * length, 0, h - 1))
            base_m = float(M[cy, cx]); base_r = float(R[cy, cx]); base_c = float(CC[cy, cx])
            _cv2.line(M, (cx, cy), (x2, y2), float(np.clip(base_m + rng.uniform(-0.18, 0.18), 0.08, 0.96)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy), (x2, y2), float(np.clip(base_r + rng.uniform(-0.18, 0.18), 0.08, 0.94)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (x2, y2), float(np.clip(base_c + rng.uniform(-0.18, 0.18), 0.05, 0.90)), 1, lineType=_cv2.LINE_AA)

        # 3) SALT-BLEED CRYSTAL ROSETTES — 8-spoke radial bursts
        n_rosettes = int(np.clip(145 * scale * scale, 52, 420))
        for _ in range(n_rosettes):
            cx = int(rng.uniform(8, w - 8)); cy = int(rng.uniform(8, h - 8))
            r = max(2, int(rng.uniform(3.0, 6.0) * scale))
            n_spokes = int(rng.integers(6, 11))
            vM = float(rng.uniform(0.55, 0.95))
            vR = float(rng.uniform(0.06, 0.34))
            vCC = float(rng.uniform(0.08, 0.42))
            a0 = float(rng.uniform(0, 2 * np.pi))
            for k in range(n_spokes):
                a = a0 + k * (2 * np.pi / n_spokes)
                x2 = int(np.clip(cx + np.cos(a) * r, 0, w - 1))
                y2 = int(np.clip(cy + np.sin(a) * r, 0, h - 1))
                _cv2.line(M, (cx, cy), (x2, y2), vM, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx, cy), (x2, y2), vR, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx, cy), (x2, y2), vCC, 1, lineType=_cv2.LINE_AA)

        # 4) PAPER-FOLD seam highlights — long thin bright lines
        n_folds = int(rng.integers(4, 9))
        for _ in range(n_folds):
            x0 = int(rng.uniform(0, w)); y0 = int(rng.uniform(0, h))
            ang = float(rng.uniform(0, 2 * np.pi))
            length = float(rng.uniform(80, 180) * scale)
            x1 = int(np.clip(x0 + np.cos(ang) * length, 0, w - 1))
            y1 = int(np.clip(y0 + np.sin(ang) * length, 0, h - 1))
            _cv2.line(M, (x0, y0), (x1, y1), float(rng.uniform(0.50, 0.85)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0, y0), (x1, y1), float(rng.uniform(0.06, 0.30)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.10, 0.45)), 1, lineType=_cv2.LINE_AA)

        # 5) CAPILLARY SPECKLE — dots ringed near boundaries
        n_cap = int(np.clip(1300 * scale * scale, 560, 3600))
        for _ in range(n_cap):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(1.5, 3.5) * scale))
            base_m = float(M[cy, cx]); base_r = float(R[cy, cx]); base_c = float(CC[cy, cx])
            _cv2.circle(M, (cx, cy), rr, float(np.clip(base_m + rng.uniform(-0.14, 0.14), 0.08, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), rr, float(np.clip(base_r + rng.uniform(-0.14, 0.14), 0.08, 0.94)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rr, float(np.clip(base_c + rng.uniform(-0.14, 0.14), 0.05, 0.88)), -1, lineType=_cv2.LINE_AA)

    # 6) Raw-canvas flecks
    n_fl = int(np.clip(2400 * scale * scale, 800, 5500))
    fx = rng.integers(0, w, n_fl); fy = rng.integers(0, h, n_fl)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(-0.14, 0.18, n_fl).astype(np.float32), 0, 1)
    R[fy, fx] = np.clip(R[fy, fx] + rng.uniform(-0.14, 0.18, n_fl).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.14, 0.18, n_fl).astype(np.float32), 0, 1)

    # 7) R6-TICK79 HERO — DENDRITIC FRACTAL VEINS (biology-meets-math)
    # Tiny BRANCHING root systems sprout where dye fingers met salt; each
    # vein is a 4-stage recursive branching segment (6-14 px primary,
    # 4-8 px secondary, 2-4 px tertiary), drawn as 1-px AA lines with
    # tighter per-vein chroma jitter. Mathematical recursion + biological
    # motif = unexpected mix vs the soft Voronoi bleed substrate.
    if _CV2_OK:
        n_vein = int(np.clip(165 * scale * scale, 58, 500))
        for _ in range(n_vein):
            ox = float(rng.uniform(8, w - 8)); oy = float(rng.uniform(8, h - 8))
            ang0 = float(rng.uniform(0, 2 * np.pi))
            # per-vein independent chroma family
            vM = float(rng.uniform(0.18, 0.42))
            vR = float(rng.uniform(0.20, 0.48))
            vCC = float(rng.uniform(0.30, 0.82))
            # recursive branch tree: 4 stages, fan-out 2 per stage
            stack = [(ox, oy, ang0, float(rng.uniform(8.0, 14.0) * scale), 0)]
            while stack:
                x0, y0, a0, length, depth = stack.pop()
                if depth >= 4:
                    continue
                x1 = float(np.clip(x0 + np.cos(a0) * length, 0, w - 1))
                y1 = float(np.clip(y0 + np.sin(a0) * length, 0, h - 1))
                m_jit = float(rng.uniform(-0.05, 0.05))
                r_jit = float(rng.uniform(-0.05, 0.05))
                c_jit = float(rng.uniform(-0.05, 0.05))
                _cv2.line(M,  (int(x0), int(y0)), (int(x1), int(y1)), float(np.clip(vM + m_jit, 0.08, 0.55)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R,  (int(x0), int(y0)), (int(x1), int(y1)), float(np.clip(vR + r_jit, 0.10, 0.60)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (int(x0), int(y0)), (int(x1), int(y1)), float(np.clip(vCC + c_jit, 0.10, 0.92)), 1, lineType=_cv2.LINE_AA)
                # recursive children — 2 branches, ~ +/- 35-55 deg
                if depth < 3:
                    next_len = length * float(rng.uniform(0.50, 0.70))
                    stack.append((x1, y1, a0 + float(rng.uniform(0.55, 0.95)), next_len, depth + 1))
                    stack.append((x1, y1, a0 - float(rng.uniform(0.55, 0.95)), next_len, depth + 1))

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_color_field_bleed")
abstract_color_field_bleed._spb_concept_complete = True


def abstract_fluid_acrylic_pour(shape, seed, sm, **kwargs):
    """abstract_fluid_acrylic_pour.

    identity: Signature ouzo-effect acrylic pour with HERO SKIN-PULL TEAR —
    classic concentric cell rings forming around poured nucleation points,
    silicone-popped fish-eye spots inside each cell, marbled flow bands
    swirling between cells, tiny trapped air bubbles, PLUS the diversifier
    motif: a long meandering SKIN-PULL TEAR ribbon (a 6-10 px wide drag
    streak crossing the canvas where the paint skin separated and lifted,
    exposing raw substrate beneath with directional bristle scrape lines).
    Independent M/R/CC per cell and per ring delivers polychrome wet-paint
    look; the skin-pull tear is unique to this entry vs other abstract
    pours and marbles in the catalog.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 10110 + 8484)
    scale = max(min(h, w) / 2048.0, 0.25)

    # 1) FLOW BACKGROUND — swirling marbled gradients
    swirl_m = _normalize(multi_scale_noise(shape, [4.0, 9.0, 22.0], [0.5, 0.3, 0.2], int(seed) + 10111))
    swirl_r = _normalize(multi_scale_noise(shape, [4.5, 10.0, 24.0], [0.5, 0.3, 0.2], int(seed) + 10112))
    swirl_c = _normalize(multi_scale_noise(shape, [5.0, 11.0, 26.0], [0.5, 0.3, 0.2], int(seed) + 10113))
    M = (0.30 + swirl_m * 0.30).astype(np.float32)
    R = (0.40 + swirl_r * 0.30).astype(np.float32)
    CC = (0.45 + swirl_c * 0.30).astype(np.float32)

    # 2) OUZO CELLS — concentric ring nucleation
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    n_cells = int(np.clip(28 * (min(h, w) / 256.0) ** 2, 30, 90))
    for _ in range(n_cells):
        cx = rng.uniform(0, w); cy = rng.uniform(0, h)
        outer = rng.uniform(14.0, 30.0) * scale
        n_rings = int(rng.integers(3, 7))
        # per-cell base colors
        base_m = float(rng.uniform(0.10, 0.90))
        base_r = float(rng.uniform(0.10, 0.85))
        base_c = float(rng.uniform(0.20, 0.95))
        tile = int(outer * 1.4) + 2
        x0 = max(0, int(cx - tile)); x1 = min(w, int(cx + tile) + 1)
        y0 = max(0, int(cy - tile)); y1 = min(h, int(cy + tile) + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        d = np.sqrt((xx[y0:y1, x0:x1] - cx) ** 2 + (yy[y0:y1, x0:x1] - cy) ** 2)
        mask = d <= outer
        if not mask.any():
            continue
        # cell core fill
        core = np.exp(-(d * d) / (2.0 * (outer * 0.5) ** 2))
        M[y0:y1, x0:x1] = M[y0:y1, x0:x1] * (1.0 - core * 0.7) + base_m * core * 0.7
        R[y0:y1, x0:x1] = R[y0:y1, x0:x1] * (1.0 - core * 0.7) + base_r * core * 0.7
        CC[y0:y1, x0:x1] = CC[y0:y1, x0:x1] * (1.0 - core * 0.7) + base_c * core * 0.7
        # concentric rings — each ring has its own chroma
        for k in range(n_rings):
            r_k = outer * (k + 1) / (n_rings + 1)
            sigma_k = outer * 0.06
            ring = np.exp(-((d - r_k) ** 2) / (2.0 * sigma_k * sigma_k))
            m_v = float(rng.uniform(0.05, 0.95))
            r_v = float(rng.uniform(0.05, 0.85))
            c_v = float(rng.uniform(0.20, 0.95))
            M[y0:y1, x0:x1] = M[y0:y1, x0:x1] * (1.0 - ring * 0.6) + m_v * ring * 0.6
            R[y0:y1, x0:x1] = R[y0:y1, x0:x1] * (1.0 - ring * 0.6) + r_v * ring * 0.6
            CC[y0:y1, x0:x1] = CC[y0:y1, x0:x1] * (1.0 - ring * 0.6) + c_v * ring * 0.6

    # 3) SILICONE FISH-EYE POPS — tiny bright pops inside cells
    if _CV2_OK:
        n_pop = int(np.clip(280 * (min(h, w) / 256.0) ** 2, 320, 1400))
        for _ in range(n_pop):
            px = int(rng.uniform(0, w)); py = int(rng.uniform(0, h))
            r_p = max(1, int(rng.uniform(1.5, 3.5) * scale))
            _cv2.circle(M, (px, py), r_p, float(rng.uniform(0.40, 0.95)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (px, py), r_p, float(rng.uniform(0.05, 0.30)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (px, py), r_p, float(rng.uniform(0.60, 0.95)), -1, lineType=_cv2.LINE_AA)

        # 4) AIR BUBBLES — tiny dark ringed bubbles
        n_bub = int(np.clip(180 * (min(h, w) / 256.0) ** 2, 200, 900))
        for _ in range(n_bub):
            bx = int(rng.uniform(0, w)); by = int(rng.uniform(0, h))
            r_b = max(1, int(rng.uniform(1.0, 2.5) * scale))
            _cv2.circle(R, (bx, by), r_b, float(rng.uniform(0.55, 0.90)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (bx, by), r_b, float(rng.uniform(0.10, 0.40)), 1, lineType=_cv2.LINE_AA)

        # 5) HERO MOTIF — SKIN-PULL TEAR RIBBON with bristle scrape
        # 1-2 long meandering drag streaks crossing the canvas. Each is a
        # 6-10 px wide path with parallel bristle lines exposing substrate.
        n_tear = int(rng.integers(1, 3))
        for _ in range(n_tear):
            # Start on one edge, end on opposite edge
            edge = int(rng.integers(0, 4))
            if edge == 0:  # top->bottom
                x0 = int(rng.uniform(0.10, 0.90) * w); y0 = 0
                x1 = int(rng.uniform(0.10, 0.90) * w); y1 = h - 1
            elif edge == 1:  # left->right
                x0 = 0; y0 = int(rng.uniform(0.10, 0.90) * h)
                x1 = w - 1; y1 = int(rng.uniform(0.10, 0.90) * h)
            elif edge == 2:  # diagonal
                x0 = 0; y0 = 0; x1 = w - 1; y1 = h - 1
            else:
                x0 = w - 1; y0 = 0; x1 = 0; y1 = h - 1
            # Walk path in segments with curvature
            n_seg = 24
            px_prev, py_prev = x0, y0
            tear_width = int(rng.uniform(6.0, 10.0) * scale)
            # Per-tear independent substrate exposure chroma
            sub_M = float(rng.uniform(0.18, 0.40))
            sub_R = float(rng.uniform(0.55, 0.82))
            sub_CC = float(rng.uniform(0.25, 0.55))
            for k in range(1, n_seg + 1):
                t = k / n_seg
                # Linear interp + sine wobble
                px = int(x0 + (x1 - x0) * t + np.sin(t * 4 * np.pi) * 12.0 * scale)
                py = int(y0 + (y1 - y0) * t + np.cos(t * 3.5 * np.pi) * 12.0 * scale)
                _cv2.line(M, (px_prev, py_prev), (px, py), sub_M, tear_width, lineType=_cv2.LINE_AA)
                _cv2.line(R, (px_prev, py_prev), (px, py), sub_R, tear_width, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (px_prev, py_prev), (px, py), sub_CC, tear_width, lineType=_cv2.LINE_AA)
                # Bristle scrape lines — parallel hairlines along the tear
                n_bristle = 3
                dx = px - px_prev; dy = py - py_prev
                seg_len = max(1.0, np.sqrt(dx * dx + dy * dy))
                nx = -dy / seg_len; ny = dx / seg_len  # perpendicular
                for b in range(n_bristle):
                    off = (b - 1) * (tear_width // 2)
                    bx0 = int(px_prev + nx * off); by0 = int(py_prev + ny * off)
                    bx1 = int(px + nx * off); by1 = int(py + ny * off)
                    _cv2.line(M, (bx0, by0), (bx1, by1), float(rng.uniform(0.50, 0.88)), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, (bx0, by0), (bx1, by1), float(rng.uniform(0.15, 0.40)), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, (bx0, by0), (bx1, by1), float(rng.uniform(0.30, 0.60)), 1, lineType=_cv2.LINE_AA)
                px_prev, py_prev = px, py

        # 6) TICK52 NEW HERO — SWIRL-EYE WHIRLPOOL VORTICES + CHAIN CELLS
        # 1-3 dramatic spiraling chroma vortices (logarithmic spiral arms,
        # each arm a different chroma) — the cinematic "Dutch pour" energy.
        # Plus 2-4 chain-cell trains of close-packed ring-bubbles.
        n_vortex = int(rng.integers(1, 4))
        for _ in range(n_vortex):
            cx_v = float(rng.uniform(0.12, 0.88) * w)
            cy_v = float(rng.uniform(0.12, 0.88) * h)
            n_arms = int(rng.integers(3, 6))
            r_max_v = float(rng.uniform(36.0, 60.0) * scale)
            base_a_v = float(rng.uniform(0, 2 * np.pi))
            chirality = 1.0 if rng.random() > 0.5 else -1.0
            for k in range(n_arms):
                arm_off = k * (2 * np.pi / n_arms)
                aM = float(rng.uniform(0.10, 0.92))
                aR = float(rng.uniform(0.08, 0.88))
                aCC = float(rng.uniform(0.18, 0.95))
                n_pt = 36
                prev = None
                for s in range(n_pt):
                    t = s / float(n_pt)
                    r_s = 6.0 * scale + (r_max_v - 6.0 * scale) * t
                    theta = base_a_v + arm_off + chirality * t * 2.4 * np.pi
                    x_s = int(cx_v + np.cos(theta) * r_s)
                    y_s = int(cy_v + np.sin(theta) * r_s)
                    if not (0 <= x_s < w and 0 <= y_s < h):
                        prev = None; continue
                    if prev is not None:
                        seg_M = aM * float(rng.uniform(0.82, 1.0))
                        seg_R = aR * float(rng.uniform(0.82, 1.0))
                        seg_C = aCC * float(rng.uniform(0.82, 1.0))
                        _cv2.line(M, prev, (x_s, y_s), seg_M, 2, lineType=_cv2.LINE_AA)
                        _cv2.line(R, prev, (x_s, y_s), seg_R, 2, lineType=_cv2.LINE_AA)
                        _cv2.line(CC, prev, (x_s, y_s), seg_C, 2, lineType=_cv2.LINE_AA)
                    prev = (x_s, y_s)
            # Bright central eye-pin
            _cv2.circle(M, (int(cx_v), int(cy_v)), max(2, int(2.5 * scale)),
                        float(rng.uniform(0.78, 0.99)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (int(cx_v), int(cy_v)), max(2, int(2.5 * scale)),
                        float(rng.uniform(0.03, 0.18)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (int(cx_v), int(cy_v)), max(2, int(2.5 * scale)),
                        float(rng.uniform(0.62, 0.96)), -1, lineType=_cv2.LINE_AA)

        # Dutch-pour CHAIN CELLS — train of small ring-bubbles
        n_chain = int(rng.integers(2, 5))
        for _ in range(n_chain):
            cxc = float(rng.uniform(0.10, 0.90) * w)
            cyc = float(rng.uniform(0.10, 0.90) * h)
            chain_ang = float(rng.uniform(0, 2 * np.pi))
            n_bub = int(rng.integers(6, 15))
            for k in range(n_bub):
                step = float(rng.uniform(5.0, 9.0) * scale)
                cxc += np.cos(chain_ang) * step + float(rng.normal(0, 0.8))
                cyc += np.sin(chain_ang) * step + float(rng.normal(0, 0.8))
                chain_ang += float(rng.normal(0, 0.18))
                if not (0 <= cxc < w and 0 <= cyc < h):
                    break
                r_b = max(2, int(rng.uniform(2.5, 4.5) * scale))
                _cv2.circle(M, (int(cxc), int(cyc)), r_b,
                            float(rng.uniform(0.20, 0.88)), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (int(cxc), int(cyc)), r_b,
                            float(rng.uniform(0.15, 0.55)), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (int(cxc), int(cyc)), r_b,
                            float(rng.uniform(0.35, 0.92)), 1, lineType=_cv2.LINE_AA)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_fluid_acrylic_pour")
abstract_fluid_acrylic_pour._spb_concept_complete = True


def abstract_ink_wash_gradient(shape, seed, sm, **kwargs):
    """abstract_ink_wash_gradient.

    identity: sumi-e ink wash with HERO ENSO + KANJI STROKES — large soft tonal
    wash bands bleeding into each other, OVERLAID with 1-2 hero ENSO CIRCLES
    (the Zen one-stroke circle, drawn as a thick arc with a tapered open
    gap) AND 2-4 bold gestural CALLIGRAPHIC SLASH STROKES (long thick
    tapered diagonal brush marks evoking kanji radicals). Thin trailing
    brush hairs at wash edges, scattered ink-pool dark blooms, and
    dry-brush flecks across the rice-paper substrate. Per-feature
    INDEPENDENT M/R/CC keeps each ink layer chromatically distinct.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 10210)
    scale = max(min(h, w) / 2048.0, 0.25)

    # 1) RICE PAPER SUBSTRATE — soft warm grain
    paper_m = _normalize(multi_scale_noise(shape, [1.4, 3.0, 7.0], [0.55, 0.30, 0.15], int(seed) + 10211))
    paper_r = _normalize(multi_scale_noise(shape, [1.6, 3.2, 7.5], [0.55, 0.30, 0.15], int(seed) + 10212))
    paper_c = _normalize(multi_scale_noise(shape, [1.8, 3.4, 8.0], [0.55, 0.30, 0.15], int(seed) + 10213))
    M = (0.18 + paper_m * 0.10).astype(np.float32)
    R = (0.72 + paper_r * 0.10).astype(np.float32)
    CC = (0.55 + paper_c * 0.12).astype(np.float32)

    # 2) WASH BANDS — large soft directional gradients
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    n_wash = int(rng.integers(4, 8))
    for _ in range(n_wash):
        cx = rng.uniform(0, w); cy = rng.uniform(0, h)
        ang = rng.uniform(0, 6.28)
        # large soft elliptical wash
        u = (xx - cx) * np.cos(ang) + (yy - cy) * np.sin(ang)
        v = -(xx - cx) * np.sin(ang) + (yy - cy) * np.cos(ang)
        ax = rng.uniform(40, 90) * scale * (min(h, w) / 256.0)
        bx = rng.uniform(25, 50) * scale * (min(h, w) / 256.0)
        wash = np.exp(-(u * u) / (2.0 * ax * ax) - (v * v) / (2.0 * bx * bx))
        # per-wash continuous chroma
        m_v = float(rng.uniform(0.20, 0.80))
        r_v = float(rng.uniform(0.30, 0.85))
        c_v = float(rng.uniform(0.20, 0.85))
        strength = float(rng.uniform(0.35, 0.65))
        M = M * (1.0 - wash * strength) + m_v * wash * strength
        R = R * (1.0 - wash * strength) + r_v * wash * strength
        CC = CC * (1.0 - wash * strength) + c_v * wash * strength

    if _CV2_OK:
        # HERO TIER — ENSO CIRCLES (1-2 thick arc circles with tapered open gap)
        n_enso = int(rng.integers(1, 3))
        for _ in range(n_enso):
            ecx = int(rng.uniform(w * 0.25, w * 0.75))
            ecy = int(rng.uniform(h * 0.25, h * 0.75))
            er = int(rng.uniform(30, 60) * (min(h, w) / 256.0))
            gap_start = float(rng.uniform(0, 6.28))
            gap_size = float(rng.uniform(0.3, 0.9))  # radians of open gap
            n_step = 90
            em = float(rng.uniform(0.08, 0.30))
            er_ = float(rng.uniform(0.65, 0.92))
            ec = float(rng.uniform(0.20, 0.55))
            base_th = max(3, int(rng.uniform(4.0, 7.0) * scale))
            prev = None
            for k in range(n_step):
                t = (k / n_step) * 6.28
                # Skip the gap
                d_to_gap = ((t - gap_start) % 6.28)
                if d_to_gap < gap_size:
                    prev = None
                    continue
                # Variable thickness — tapered at start/end of stroke
                taper = 1.0
                dist_from_gap_end = ((t - (gap_start + gap_size)) % 6.28)
                if dist_from_gap_end < 0.4: taper = 0.4 + dist_from_gap_end / 0.4 * 0.6
                if (gap_start - t) % 6.28 < 0.4: taper = 0.4 + ((gap_start - t) % 6.28) / 0.4 * 0.6
                th = max(1, int(base_th * taper))
                # Slight radial wobble for organic brush feel
                rr = er + float(rng.uniform(-2, 2))
                px = int(ecx + np.cos(t) * rr)
                py = int(ecy + np.sin(t) * rr)
                if prev is not None and 0 <= px < w and 0 <= py < h:
                    _cv2.line(M, prev, (px, py), em, th, lineType=_cv2.LINE_AA)
                    _cv2.line(R, prev, (px, py), er_, th, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, prev, (px, py), ec, th, lineType=_cv2.LINE_AA)
                prev = (px, py)

        # HERO TIER — CALLIGRAPHIC SLASH STROKES (bold tapered kanji-radical
        # diagonals)
        n_slash = int(rng.integers(2, 5))
        for _ in range(n_slash):
            sx = float(rng.uniform(w * 0.05, w * 0.95))
            sy = float(rng.uniform(h * 0.05, h * 0.95))
            ang = float(rng.choice([np.pi*0.25, np.pi*0.30, np.pi*0.70, np.pi*0.75])) + float(rng.uniform(-0.15, 0.15))
            length = float(rng.uniform(50, 110)) * (min(h, w) / 256.0)
            n_step = int(length / 2.5)
            sm_ = float(rng.uniform(0.05, 0.25))
            sr = float(rng.uniform(0.70, 0.95))
            sc = float(rng.uniform(0.20, 0.50))
            prev = None
            for k in range(n_step):
                f = k / max(n_step - 1, 1)
                # Tapered thickness — fat in middle, thin at ends
                th = max(1, int((1.0 + 6.0 * np.sin(f * np.pi)) * scale * 1.5))
                px = int(sx + np.cos(ang) * length * f)
                py = int(sy + np.sin(ang) * length * f)
                if prev is not None and 0 <= px < w and 0 <= py < h:
                    _cv2.line(M, prev, (px, py), sm_, th, lineType=_cv2.LINE_AA)
                    _cv2.line(R, prev, (px, py), sr, th, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, prev, (px, py), sc, th, lineType=_cv2.LINE_AA)
                prev = (px, py)

        # 3) BRUSH-HAIR TRAILS — thin curved hairs at wash edges
        n_hair = int(np.clip(200 * (min(h, w) / 256.0) ** 2, 220, 900))
        for _ in range(n_hair):
            x0_h = rng.uniform(0, w); y0_h = rng.uniform(0, h)
            t = rng.uniform(0, 6.28)
            curve = rng.uniform(-0.04, 0.04)
            steps = int(rng.uniform(8, 20))
            pts = []
            x = x0_h; y = y0_h
            for s in range(steps):
                pts.append((int(np.clip(x, 0, w - 1)), int(np.clip(y, 0, h - 1))))
                t += curve
                x += np.cos(t) * 2.0; y += np.sin(t) * 2.0
            m_v = float(rng.uniform(0.15, 0.55))
            r_v = float(rng.uniform(0.55, 0.92))
            c_v = float(rng.uniform(0.30, 0.65))
            for k in range(len(pts) - 1):
                _cv2.line(M, pts[k], pts[k + 1], m_v, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, pts[k], pts[k + 1], r_v, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, pts[k], pts[k + 1], c_v, 1, lineType=_cv2.LINE_AA)

        # 4) INK-POOL DARK BLOOMS — pool spots
        n_pool = int(np.clip(50 * (min(h, w) / 256.0) ** 2, 55, 200))
        for _ in range(n_pool):
            px = int(rng.uniform(0, w)); py = int(rng.uniform(0, h))
            r_p = max(2, int(rng.uniform(3, 7) * scale))
            _cv2.circle(M, (px, py), r_p, float(rng.uniform(0.10, 0.35)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (px, py), r_p, float(rng.uniform(0.70, 0.95)), -1, lineType=_cv2.LINE_AA)

        # 5) DRY-BRUSH FLECKS — micro grit
        n_fl = int(np.clip(h * w / 250, 500, 8000))
        fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
        M[fy, fx] = np.minimum(M[fy, fx], rng.uniform(0.05, 0.40, n_fl).astype(np.float32))

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_ink_wash_gradient")
abstract_ink_wash_gradient._spb_concept_complete = True


def abstract_neon_glitch(shape, seed, sm, **kwargs):
    """abstract_neon_glitch.

    identity: ROUND-6 CREATIVE REBUILD — a corrupted-CRT signal cranked
    further. The HERO MOTIFS are now (a) the chromatic-aberration RGB
    channel-shift slices, (b) DATAMOSH block-shuffle rectangles where
    8x8 to 16x16 px blocks are torn from one location and stamped at
    another, and (c) a digital pixel-rain column ladder where vertical
    columns of dim cyan/magenta pixels cascade downward like the matrix.
    Seven tiers:
      (1) deep CRT phosphor substrate (cool deep magenta/teal FBM);
      (2) sub-pixel triad columns — 3-px-wide R/G/B vertical stripes;
      (3) scanlines (every 2-3 px);
      (4) RGB-shift glitch slices (each channel rolls independently);
      (5) magenta/cyan tear bars;
      (6) DATAMOSH block stamps (rip src block, paste at offset, edge
          burn);
      (7) PIXEL-RAIN CASCADE columns — vertical 1-px columns 12-40 px
          long where pixels alternate bright cyan/magenta + dim.
      (8) pixel-snow flecks across all channels.
    Independent continuous M/R/CC at every feature.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 10230)
    scale = max(min(h, w) / 2048.0, 0.25)

    # 1) DEEP CRT PHOSPHOR BASE
    base_m = _normalize(multi_scale_noise(shape, [3.0, 7.0], [0.5, 0.3], int(seed) + 10231))
    base_r = _normalize(multi_scale_noise(shape, [3.5, 8.0], [0.5, 0.3], int(seed) + 10232))
    base_c = _normalize(multi_scale_noise(shape, [4.0, 9.0], [0.5, 0.3], int(seed) + 10233))
    M = (0.16 + base_m * 0.20).astype(np.float32)
    R = (0.58 + base_r * 0.18).astype(np.float32)
    CC = (0.32 + base_c * 0.20).astype(np.float32)

    # 2) SUB-PIXEL TRIADS — 3-px vertical stripes RGB cycling
    xx = np.arange(w)
    triad = (xx % 3).astype(np.int32)  # 0,1,2 cycling
    triad_m_boost = np.where(triad == 0, 0.08, 0.0).astype(np.float32)
    triad_r_dim = np.where(triad == 1, -0.10, 0.0).astype(np.float32)
    triad_c_boost = np.where(triad == 2, 0.10, 0.0).astype(np.float32)
    M = M + triad_m_boost[None, :]
    R = R + triad_r_dim[None, :]
    CC = CC + triad_c_boost[None, :]

    # 3) SCANLINES — alternating dark/light horizontal lines
    yy = np.arange(h)[:, None].astype(np.float32)
    scan_period = max(2, int(2 + rng.uniform(0, 2)))
    scan = 0.5 + 0.5 * np.sin(yy * (np.pi / scan_period) * 2.0)
    scan = np.broadcast_to(scan, (h, w))
    M = M + (scan - 0.5) * 0.12
    R = R - (scan - 0.5) * 0.12
    CC = CC + (scan - 0.5) * 0.10

    # 4) RGB-SHIFT GLITCH SLICES — independent channel rolls
    n_slices = int(rng.integers(14, 30))
    for _ in range(n_slices):
        y0 = int(rng.uniform(0, h))
        thick = int(rng.uniform(2, 10))
        y1 = min(h, y0 + thick)
        if y1 <= y0: continue
        dx_m = int(rng.uniform(-12, 12) * scale)
        dx_r = int(rng.uniform(-12, 12) * scale)
        dx_c = int(rng.uniform(-12, 12) * scale)
        M[y0:y1, :] = np.roll(M[y0:y1, :], dx_m, axis=1)
        R[y0:y1, :] = np.roll(R[y0:y1, :], dx_r, axis=1)
        CC[y0:y1, :] = np.roll(CC[y0:y1, :], dx_c, axis=1)

    # 5) TEAR BARS — magenta/cyan
    n_tear = int(rng.integers(10, 22))
    for _ in range(n_tear):
        y0 = int(rng.uniform(0, h - 4))
        thick = int(rng.uniform(1, 3))
        y1 = min(h, y0 + thick)
        kind = rng.integers(0, 3)
        if kind == 0:  # magenta
            M[y0:y1, :] = np.clip(M[y0:y1, :] + rng.uniform(0.40, 0.70), 0.0, 1.0)
            CC[y0:y1, :] = np.clip(CC[y0:y1, :] + rng.uniform(0.35, 0.65), 0.0, 1.0)
        elif kind == 1:  # cyan
            M[y0:y1, :] = np.clip(M[y0:y1, :] - rng.uniform(0.22, 0.42), 0.0, 1.0)
            CC[y0:y1, :] = np.clip(CC[y0:y1, :] + rng.uniform(0.35, 0.65), 0.0, 1.0)
        else:  # neon-yellow stripe (high M, high R)
            M[y0:y1, :] = np.clip(M[y0:y1, :] + rng.uniform(0.30, 0.60), 0.0, 1.0)
            R[y0:y1, :] = np.clip(R[y0:y1, :] - rng.uniform(0.25, 0.50), 0.0, 1.0)

    # 6) DATAMOSH BLOCK STAMPS — copy src block to dst location
    n_mosh = int(np.clip(80 * (min(h, w) / 256.0), 18, 220))
    for _ in range(n_mosh):
        bw = int(rng.integers(8, 17)); bh = int(rng.integers(6, 15))
        sx = int(rng.integers(0, max(1, w - bw)))
        sy = int(rng.integers(0, max(1, h - bh)))
        dx = int(rng.integers(0, max(1, w - bw)))
        dy = int(rng.integers(0, max(1, h - bh)))
        # copy independently per channel (datamosh chroma desync)
        ch_pick = rng.integers(0, 4)
        if ch_pick == 0 or ch_pick == 3:
            M[dy:dy+bh, dx:dx+bw] = M[sy:sy+bh, sx:sx+bw]
        if ch_pick == 1 or ch_pick == 3:
            R[dy:dy+bh, dx:dx+bw] = R[sy:sy+bh, sx:sx+bw]
        if ch_pick == 2 or ch_pick == 3:
            CC[dy:dy+bh, dx:dx+bw] = CC[sy:sy+bh, sx:sx+bw]
        # edge burn — top row brightened
        if dy < h:
            M[dy, dx:min(w, dx+bw)] = np.clip(M[dy, dx:min(w, dx+bw)] + rng.uniform(0.20, 0.50), 0, 1)
            CC[dy, dx:min(w, dx+bw)] = np.clip(CC[dy, dx:min(w, dx+bw)] + rng.uniform(0.15, 0.40), 0, 1)

    # 7) PIXEL-RAIN CASCADE — vertical 1-px columns, 12-40 px long
    n_rain = int(np.clip(90 * (min(h, w) / 256.0), 24, 260))
    for _ in range(n_rain):
        cx = int(rng.integers(0, w))
        cy0 = int(rng.integers(0, max(1, h - 4)))
        length = int(rng.integers(12, 40) * max(scale, 0.5))
        cy1 = min(h, cy0 + length)
        # alternate bright/dim pixel column
        kind = rng.integers(0, 2)
        for py in range(cy0, cy1):
            if py >= h: break
            alt = (py - cy0) % 2
            if kind == 0:  # cyan rain
                M[py, cx] = float(0.06 if alt else 0.30)
                CC[py, cx] = float(0.85 if alt else 0.60)
                R[py, cx] = float(0.18 if alt else 0.30)
            else:  # magenta rain
                M[py, cx] = float(0.90 if alt else 0.65)
                CC[py, cx] = float(0.80 if alt else 0.55)
                R[py, cx] = float(0.18 if alt else 0.30)

    # 8) PIXEL SNOW — random flecks
    n_fl = int(np.clip(h * w / 160, 700, 14000))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = rng.uniform(0.0, 1.0, n_fl).astype(np.float32)
    R[fy, fx] = rng.uniform(0.0, 1.0, n_fl).astype(np.float32)
    CC[fy, fx] = rng.uniform(0.0, 1.0, n_fl).astype(np.float32)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_neon_glitch")
abstract_neon_glitch._spb_concept_complete = True


def _abstract_retro_wave_tile(tile_h, tile_w, rng):
    """Render one mini-synthwave panel (tile_h x tile_w). Returns (M, R, CC)."""
    h, w = tile_h, tile_w
    yy_i, xx_i = np.mgrid[0:h, 0:w].astype(np.float32)
    horizon_y = h * 0.58
    sky_t = np.clip(yy_i / horizon_y, 0.0, 1.0)
    M = (0.20 + sky_t * 0.18).astype(np.float32)
    R = (0.55 - sky_t * 0.15).astype(np.float32)
    CC = (0.42 + sky_t * 0.28).astype(np.float32)
    ground_mask = (yy_i >= horizon_y).astype(np.float32)
    M = (M * (1 - ground_mask) + 0.30 * ground_mask).astype(np.float32)
    R = (R * (1 - ground_mask) + 0.32 * ground_mask).astype(np.float32)
    CC = (CC * (1 - ground_mask) + 0.58 * ground_mask).astype(np.float32)

    # SUN — stacked horizontal bands fitted to tile size
    sun_cx = w * (0.48 + float(rng.uniform(-0.05, 0.05)))
    sun_radius = h * 0.30
    n_bands = int(rng.integers(6, 10))
    band_pal_m = np.linspace(0.95, 0.45, n_bands)
    band_pal_c = np.linspace(0.92, 0.55, n_bands)
    band_pal_r = np.linspace(0.20, 0.08, n_bands)
    for i in range(n_bands):
        band_y0 = horizon_y - sun_radius + (i / n_bands) * sun_radius
        band_y1 = horizon_y - sun_radius + ((i + 1) / n_bands) * sun_radius
        if i % 2 == 1:
            band_y0 += (band_y1 - band_y0) * 0.40  # scanline gap
        iy0 = max(0, int(band_y0)); iy1 = min(h, int(band_y1))
        if iy1 <= iy0:
            continue
        band_mid = (band_y0 + band_y1) * 0.5
        dy = band_mid - horizon_y
        rsq = sun_radius * sun_radius - dy * dy
        if rsq < 1.0:
            continue
        srad = float(np.sqrt(rsq))
        d_x = np.abs(xx_i[iy0:iy1, :] - sun_cx)
        mask = d_x < srad
        m_v = float(band_pal_m[i] + rng.uniform(-0.03, 0.03))
        c_v = float(band_pal_c[i] + rng.uniform(-0.03, 0.03))
        r_v = float(band_pal_r[i] + rng.uniform(-0.02, 0.02))
        seg_m = M[iy0:iy1, :]; seg_c = CC[iy0:iy1, :]; seg_r = R[iy0:iy1, :]
        seg_m[mask] = m_v; seg_c[mask] = c_v; seg_r[mask] = r_v
        M[iy0:iy1, :] = seg_m; CC[iy0:iy1, :] = seg_c; R[iy0:iy1, :] = seg_r

    if _CV2_OK:
        # Perspective grid — MAGENTA VERTICALS from a vanishing point
        vp_x = w * 0.5; vp_y = horizon_y
        n_v = int(rng.integers(7, 12))
        for i in range(n_v):
            t = (i - n_v * 0.5) / (n_v * 0.5)
            bottom_x = int(w * 0.5 + t * w * 2.0)
            _cv2.line(M, (int(vp_x), int(vp_y)), (bottom_x, h - 1), float(rng.uniform(0.78, 0.98)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (int(vp_x), int(vp_y)), (bottom_x, h - 1), float(rng.uniform(0.60, 0.92)), 1, lineType=_cv2.LINE_AA)
        # CYAN HORIZONTAL grid lines with foreshortening
        n_h = int(rng.integers(4, 7))
        for i in range(n_h):
            t = (i + 1) / n_h
            y_line = int(horizon_y + (h - horizon_y) * (t * t))
            if 0 <= y_line < h:
                _cv2.line(CC, (0, y_line), (w - 1, y_line), float(rng.uniform(0.85, 0.99)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (0, y_line), (w - 1, y_line), float(rng.uniform(0.15, 0.30)), 1, lineType=_cv2.LINE_AA)
        # Mountain silhouettes
        n_peaks = int(rng.integers(3, 6))
        for i in range(n_peaks):
            base_x = int((i + rng.uniform(-0.3, 0.3)) * w / n_peaks)
            peak_h = int(h * float(rng.uniform(0.06, 0.13)))
            peak_w = int(w * float(rng.uniform(0.06, 0.14)))
            pts = np.array([[base_x - peak_w, int(horizon_y)],
                            [base_x, int(horizon_y) - peak_h],
                            [base_x + peak_w, int(horizon_y)]], dtype=np.int32)
            _cv2.fillPoly(M, [pts], float(rng.uniform(0.18, 0.30)))
            _cv2.fillPoly(R, [pts], float(rng.uniform(0.62, 0.85)))
            _cv2.fillPoly(CC, [pts], float(rng.uniform(0.20, 0.42)))
            _cv2.line(CC, (base_x - peak_w, int(horizon_y)), (base_x, int(horizon_y) - peak_h),
                      float(rng.uniform(0.80, 0.98)), 1, lineType=_cv2.LINE_AA)

    # Stars
    n_star = max(20, int(h * w * 0.0025))
    sy = rng.integers(0, int(horizon_y * 0.9), n_star)
    sx = rng.integers(0, w, n_star)
    M[sy, sx] = np.maximum(M[sy, sx], rng.uniform(0.55, 0.98, n_star).astype(np.float32))
    CC[sy, sx] = np.maximum(CC[sy, sx], rng.uniform(0.65, 0.98, n_star).astype(np.float32))
    return M, R, CC


def abstract_retro_wave(shape, seed, sm, **kwargs):
    """abstract_retro_wave.

    identity: R6 OWNER-CORRECTIVE — owner said "VERY neat idea, awful
    execution due to size of the canvas". Now TILED: the panel is divided
    into a 3x3 (or 4x4 at higher res) grid of mini-synthwave vignettes —
    each tile carries its own DOUBLE-SUN, perspective vector grid,
    mountain horizon, scanline bands, and starfield, so the synthwave
    identity reads CLEARLY at thumbnail scale. NEW HERO: each tile gets
    an independently-seeded sun position and palette so the panel reads
    like a strip of 9 retro-wave postcards. Plus full-canvas scanline
    glitch + neon flecks over the top, palette stays synthwave purple/
    magenta/cyan/neon-orange.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 10240)
    scale = max(min(h, w) / 2048.0, 0.25)

    # Decide tile grid: 3x3 at <= 512px short side, 4x4 above
    n_grid = 3 if min(h, w) <= 768 else 4
    tile_h = h // n_grid
    tile_w = w // n_grid
    M = np.zeros((h, w), dtype=np.float32)
    R = np.zeros((h, w), dtype=np.float32)
    CC = np.zeros((h, w), dtype=np.float32)
    for gy in range(n_grid):
        for gx in range(n_grid):
            sub_rng = np.random.default_rng(int(seed) + 10240 + gy * 17 + gx * 31)
            y0 = gy * tile_h; y1 = (gy + 1) * tile_h if gy < n_grid - 1 else h
            x0 = gx * tile_w; x1 = (gx + 1) * tile_w if gx < n_grid - 1 else w
            tm, tr, tc = _abstract_retro_wave_tile(y1 - y0, x1 - x0, sub_rng)
            M[y0:y1, x0:x1] = tm
            R[y0:y1, x0:x1] = tr
            CC[y0:y1, x0:x1] = tc

    if _CV2_OK:
        # Full-canvas scanline glitch interference bars
        n_scan = int(rng.integers(20, 36))
        for _ in range(n_scan):
            sy_pos = int(rng.uniform(0, h))
            thick = int(rng.choice([1, 1, 2]))
            _cv2.line(CC, (0, sy_pos), (w - 1, sy_pos), float(rng.uniform(0.70, 0.98)), thick, lineType=_cv2.LINE_AA)
            _cv2.line(M, (0, sy_pos), (w - 1, sy_pos), float(rng.uniform(0.28, 0.55)), thick, lineType=_cv2.LINE_AA)
        # Tile-edge frame lines (subtle) for the 3x3 postcard read
        for gy in range(1, n_grid):
            y_line = gy * tile_h
            _cv2.line(CC, (0, y_line), (w - 1, y_line), float(rng.uniform(0.80, 0.95)), 1, lineType=_cv2.LINE_AA)
        for gx in range(1, n_grid):
            x_line = gx * tile_w
            _cv2.line(CC, (x_line, 0), (x_line, h - 1), float(rng.uniform(0.80, 0.95)), 1, lineType=_cv2.LINE_AA)

    # Neon flecks
    n_neon = int(np.clip(900 * (min(h, w) / 256.0) ** 2, 800, 3500))
    ny = rng.integers(0, h, n_neon); nx = rng.integers(0, w, n_neon)
    M[ny, nx] = np.maximum(M[ny, nx], rng.uniform(0.45, 0.92, n_neon).astype(np.float32))
    CC[ny, nx] = np.maximum(CC[ny, nx], rng.uniform(0.50, 0.95, n_neon).astype(np.float32))

    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_retro_wave")
abstract_retro_wave._spb_concept_complete = True

# Block executed: insert old function-body shell so following code parses


def abstract_bauhaus_forms(shape, seed, sm, n_primitives=9, **kwargs):
    """abstract_bauhaus_forms.

    SECOND-PASS CREATIVE REBUILD: micro-typographic silkscreen poster
    with a NEW HERO motif — OP-ART MOIRE INTERFERENCE ZONES (Bridget
    Riley nods). 5-9 small (18-28 px) zones drop concentric micro-
    rings (1 px stroke, 2-3 px spacing) clashing slightly off-centre,
    producing classic moire interference patterns. Each zone has a
    unique COOL palette base (cool blue / cool violet / cool grey).
    Plus the original Bauhaus tiers: dense 3-10 px primitive carpet
    biased now toward COOL Bauhaus (deep blue, white, mid-blue, navy,
    and small red accent), Klee diagonal slashes 5-14 px, halftone
    dot-matrix pinpricks, silkscreen ash. No feature exceeds 28 px
    (the moire ring outer radius). Hero comes from optical illusion
    PLUS density.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 73610)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) DARK SILKSCREEN GROUND — composite-dark near-black (no neon green)
    region_m = _normalize(multi_scale_noise(shape, [16, 36], [0.6, 0.4], int(seed) + 10251))
    region_r = _normalize(multi_scale_noise(shape, [18, 40], [0.6, 0.4], int(seed) + 10252))
    region_cc = _normalize(multi_scale_noise(shape, [20, 44], [0.6, 0.4], int(seed) + 10254))
    paper = _normalize(multi_scale_noise(shape, [1.2, 2.8, 5.5], [0.45, 0.35, 0.20], int(seed) + 10253))
    M = (0.12 + region_m * 0.06 + (paper - 0.5) * 0.04).astype(np.float32)
    R = (0.18 + region_r * 0.08 + (paper - 0.5) * 0.06).astype(np.float32)
    CC = (0.10 + region_cc * 0.08 + (paper - 0.5) * 0.06).astype(np.float32)

    # Bauhaus primary-color sampler (red / yellow / blue / black / white)
    def _bauhaus_primary():
        # Cool-leaning Bauhaus mix (deep blue / navy / pearl / mid-blue / red accent only)
        p = int(rng.integers(0, 10))
        if p == 0:  # red ACCENT (rare)
            return (float(rng.uniform(0.55, 0.78)), float(rng.uniform(0.30, 0.50)), float(rng.uniform(0.20, 0.38)))
        if p in (1, 2, 3):  # bright blue
            return (float(rng.uniform(0.28, 0.50)), float(rng.uniform(0.40, 0.68)), float(rng.uniform(0.72, 0.96)))
        if p == 4:  # navy (cool dark)
            return (float(rng.uniform(0.10, 0.22)), float(rng.uniform(0.55, 0.80)), float(rng.uniform(0.55, 0.85)))
        if p in (5, 6):  # white / pearl (cool)
            return (float(rng.uniform(0.62, 0.85)), float(rng.uniform(0.12, 0.28)), float(rng.uniform(0.78, 0.96)))
        if p == 7:  # black
            return (float(rng.uniform(0.08, 0.18)), float(rng.uniform(0.65, 0.85)), float(rng.uniform(0.10, 0.22)))
        # 8,9: cool grey / slate
        return (float(rng.uniform(0.30, 0.50)), float(rng.uniform(0.30, 0.55)), float(rng.uniform(0.50, 0.78)))

    if _CV2_OK:
        margin = max(3, int(4 * scale))

        # TIER A — HERO OP-ART MOIRE ZONES (Bridget Riley interference rings)
        s256 = max(min(h, w) / 256.0, 0.6)
        n_moire = int(rng.integers(5, 10))
        for _z in range(n_moire):
            zx_ = int(rng.integers(margin + 12, max(margin + 13, w - margin - 12)))
            zy_ = int(rng.integers(margin + 12, max(margin + 13, h - margin - 12)))
            outer = int(np.clip(rng.uniform(14, 22) * s256, 10, 30))
            spacing = max(2, int(rng.uniform(2.2, 3.2)))
            # zone palette — cool only
            zp = int(rng.integers(0, 4))
            if zp == 0:  # ice blue
                bM, bR, bCC = 0.38, 0.30, 0.86
            elif zp == 1:  # deep violet
                bM, bR, bCC = 0.42, 0.18, 0.62
            elif zp == 2:  # storm slate
                bM, bR, bCC = 0.25, 0.32, 0.55
            else:  # pearl
                bM, bR, bCC = 0.78, 0.15, 0.88
            # First ring set centered at zone
            r = spacing
            while r <= outer:
                vM = float(np.clip(bM + rng.uniform(-0.05, 0.05), 0.05, 0.99))
                vR = float(np.clip(bR + rng.uniform(-0.05, 0.05), 0.05, 0.99))
                vC = float(np.clip(bCC + rng.uniform(-0.06, 0.06), 0.05, 0.99))
                _cv2.circle(M, (zx_, zy_), r, vM, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (zx_, zy_), r, vR, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (zx_, zy_), r, vC, 1, lineType=_cv2.LINE_AA)
                r += spacing
            # Second ring set OFFSET 4-7 px (this creates the moire interference)
            ox = int(rng.uniform(4, 8)) * (1 if rng.random() < 0.5 else -1)
            oy = int(rng.uniform(4, 8)) * (1 if rng.random() < 0.5 else -1)
            zx2 = int(np.clip(zx_ + ox, 1, w - 2))
            zy2 = int(np.clip(zy_ + oy, 1, h - 2))
            r = spacing
            while r <= outer:
                vM = float(np.clip(bM + 0.10 + rng.uniform(-0.05, 0.05), 0.05, 0.99))
                vR = float(np.clip(bR + rng.uniform(-0.05, 0.05), 0.05, 0.99))
                vC = float(np.clip(bCC - 0.08 + rng.uniform(-0.05, 0.05), 0.05, 0.99))
                _cv2.circle(M, (zx2, zy2), r, vM, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (zx2, zy2), r, vR, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (zx2, zy2), r, vC, 1, lineType=_cv2.LINE_AA)
                r += spacing

        # TIER B — VERY DENSE TINY PRIMITIVES 3-10 px (no panel-scale medallions)
        n_dense = int(np.clip(8500 * scale * scale, 3500, 18000))
        cxs = rng.integers(margin, max(margin + 1, w - margin), n_dense)
        cys = rng.integers(margin, max(margin + 1, h - margin), n_dense)
        sizes = rng.integers(max(2, int(3 * scale)), max(4, int(7 * scale)), n_dense)
        kinds = rng.integers(0, 7, n_dense)  # 0:circle 1:square 2:triangle 3:ring 4:half-moon 5:bar 6:diamond
        for i in range(n_dense):
            cx = int(cxs[i]); cy = int(cys[i]); size = int(sizes[i]); kind = int(kinds[i])
            pm, pr_, pc = _bauhaus_primary()
            if kind == 0:  # circle
                _cv2.circle(M, (cx, cy), size, pm, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), size, pr_, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), size, pc, -1, lineType=_cv2.LINE_AA)
            elif kind == 1:  # square
                _cv2.rectangle(M, (cx - size, cy - size), (cx + size, cy + size), pm, -1, lineType=_cv2.LINE_AA)
                _cv2.rectangle(R, (cx - size, cy - size), (cx + size, cy + size), pr_, -1, lineType=_cv2.LINE_AA)
                _cv2.rectangle(CC, (cx - size, cy - size), (cx + size, cy + size), pc, -1, lineType=_cv2.LINE_AA)
            elif kind == 2:  # triangle
                pts = np.array([[cx, cy - size],
                                [int(cx - size * 0.866), int(cy + size * 0.5)],
                                [int(cx + size * 0.866), int(cy + size * 0.5)]], dtype=np.int32)
                _cv2.fillPoly(M, [pts], pm, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts], pr_, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], pc, lineType=_cv2.LINE_AA)
            elif kind == 3:  # ring
                _cv2.circle(M, (cx, cy), size, pm, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), size, pr_, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), size, pc, 1, lineType=_cv2.LINE_AA)
            elif kind == 4:  # half-moon (Bauhaus semicircle)
                a0 = float(rng.choice([0.0, 90.0, 180.0, 270.0]))
                _cv2.ellipse(M, (cx, cy), (size, size), 0, a0, a0 + 180, pm, -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (size, size), 0, a0, a0 + 180, pr_, -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (size, size), 0, a0, a0 + 180, pc, -1, lineType=_cv2.LINE_AA)
            elif kind == 5:  # bar / rectangle stripe
                bw = max(1, int(size * 0.45))
                _cv2.rectangle(M, (cx - size, cy - bw), (cx + size, cy + bw), pm, -1, lineType=_cv2.LINE_AA)
                _cv2.rectangle(R, (cx - size, cy - bw), (cx + size, cy + bw), pr_, -1, lineType=_cv2.LINE_AA)
                _cv2.rectangle(CC, (cx - size, cy - bw), (cx + size, cy + bw), pc, -1, lineType=_cv2.LINE_AA)
            else:  # 6: diamond (rotated square)
                pts = np.array([[cx, cy - size], [cx + size, cy], [cx, cy + size], [cx - size, cy]], dtype=np.int32)
                _cv2.fillPoly(M, [pts], pm, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts], pr_, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], pc, lineType=_cv2.LINE_AA)

        # TIER C — MICRO SLASH-RULE LINES (5-14 px short Klee diagonals)
        n_lines = int(np.clip(2200 * scale * scale, 900, 6000))
        for _ in range(n_lines):
            x0 = int(rng.integers(margin, max(margin + 1, w - margin)))
            y0 = int(rng.integers(margin, max(margin + 1, h - margin)))
            length = int(rng.integers(max(4, int(5 * scale)), max(8, int(14 * scale))))
            thickness = max(1, int(scale))
            pm = float(rng.uniform(0.18, 0.94))
            pr_ = float(rng.uniform(0.16, 0.88))
            pc = float(rng.uniform(0.15, 0.90))
            mode = float(rng.random())
            if mode < 0.4:
                # horizontal
                x1 = int(np.clip(x0 + length, 0, w - 1)); y1 = y0
            elif mode < 0.75:
                # vertical
                x1 = x0; y1 = int(np.clip(y0 + length, 0, h - 1))
            else:
                # Klee diagonal
                ang = float(rng.choice([np.pi * 0.25, -np.pi * 0.25, np.pi * 0.75, -np.pi * 0.75]))
                x1 = int(np.clip(x0 + np.cos(ang) * length, 0, w - 1))
                y1 = int(np.clip(y0 + np.sin(ang) * length, 0, h - 1))
            _cv2.line(M, (x0, y0), (x1, y1), pm, thickness, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0, y0), (x1, y1), pr_, thickness, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), pc, thickness, lineType=_cv2.LINE_AA)

    # TIER D — HALFTONE DOT-MATRIX pinpricks (1-px regular dot grid jittered)
    dot_pitch = max(4, int(6 * scale))
    n_dots = int((h / dot_pitch) * (w / dot_pitch))
    if n_dots > 0:
        dy = np.tile(np.arange(0, h, dot_pitch), w // dot_pitch + 1)[:n_dots]
        dx = np.repeat(np.arange(0, w, dot_pitch), h // dot_pitch + 1)[:n_dots]
        jy = (dy + rng.integers(-1, 2, n_dots)).clip(0, h - 1)
        jx = (dx + rng.integers(-1, 2, n_dots)).clip(0, w - 1)
        M[jy, jx] = np.minimum(M[jy, jx], rng.uniform(0.20, 0.50, n_dots).astype(np.float32))
        R[jy, jx] = np.maximum(R[jy, jx], rng.uniform(0.50, 0.90, n_dots).astype(np.float32))
        CC[jy, jx] = np.minimum(CC[jy, jx], rng.uniform(0.20, 0.50, n_dots).astype(np.float32))

    # TIER E — SILKSCREEN FLECK DUST with INDEPENDENT M/R/CC uniforms
    n_fl = max(3200, int(h * w / 1100))
    fx = rng.integers(0, w, n_fl); fy = rng.integers(0, h, n_fl)
    M[fy, fx] = rng.uniform(0.16, 0.95, n_fl).astype(np.float32)
    R[fy, fx] = rng.uniform(0.13, 0.90, n_fl).astype(np.float32)
    CC[fy, fx] = rng.uniform(0.10, 0.92, n_fl).astype(np.float32)

    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "abstract_bauhaus_forms")
abstract_bauhaus_forms._spb_concept_complete = True


# ============================================================================
# PATTERN CATALOG — for programmatic access
# ============================================================================


ABSTRACT_ART_PATTERNS = {
    'abstract_expressionist_splatter': abstract_expressionist_splatter,
    'abstract_cubist_facets': abstract_cubist_facets,
    'abstract_rothko_field': abstract_rothko_field,
    'abstract_kandinsky_shapes': abstract_kandinsky_shapes,
    'abstract_mondrian_grid': abstract_mondrian_grid,
    'abstract_op_art_circles': abstract_op_art_circles,
    'abstract_op_art_waves': abstract_op_art_waves,
    'abstract_suprematism': abstract_suprematism,
    'abstract_futurist_motion': abstract_futurist_motion,
    'abstract_minimalist_stripe': abstract_minimalist_stripe,
    'abstract_hard_edge_field': abstract_hard_edge_field,
    'abstract_color_field_bleed': abstract_color_field_bleed,
    'abstract_fluid_acrylic_pour': abstract_fluid_acrylic_pour,
    'abstract_ink_wash_gradient': abstract_ink_wash_gradient,
    'abstract_neon_glitch': abstract_neon_glitch,
    'abstract_retro_wave': abstract_retro_wave,
    'abstract_bauhaus_forms': abstract_bauhaus_forms,
}

__all__ = [
    'ABSTRACT_ART_PATTERNS',
    'abstract_expressionist_splatter',
    'abstract_cubist_facets',
    'abstract_rothko_field',
    'abstract_kandinsky_shapes',
    'abstract_mondrian_grid',
    'abstract_op_art_circles',
    'abstract_op_art_waves',
    'abstract_suprematism',
    'abstract_futurist_motion',
    'abstract_minimalist_stripe',
    'abstract_hard_edge_field',
    'abstract_color_field_bleed',
    'abstract_fluid_acrylic_pour',
    'abstract_ink_wash_gradient',
    'abstract_neon_glitch',
    'abstract_retro_wave',
    'abstract_bauhaus_forms',
]

