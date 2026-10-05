"""Optical spec pattern family for Shokker Paint Booth.

This module is imported by engine.spec_patterns so PATTERN_CATALOG keeps
the legacy public keys while the central spec registry shrinks.

SPB-106 (owner mandate 2026-05-20): "DO NOT GROW engine/spec_patterns.py"
— optical effect rebuilds (chromatic aberration, diffraction, fresnel,
caustic, retroreflective, light leak, etc.) live here.
"""
import numpy as np

try:
    import cv2 as _cv2
    _CV2_OK = True
except ImportError:
    _CV2_OK = False

from ..spec_patterns import (
    _flat,
    _normalize,
    _sm_scale,
    _validate_spec_output,
    multi_scale_noise,
)


def spec_chromatic_aberration(shape, seed, sm, inner_radius=0.30, fringe_period=0.04,
                               fringe_octaves=3, **kwargs):
    """spec_chromatic_aberration.

    identity: R6-creative-v2 rebuild - LENS-FAULT CHROMATIC STORM. Real
    chromatic aberration radiates from an optical center; this rebuild
    leans into that LITERAL optical signature. Seven stacked tiers:
    (1) chroma-drifting substrate, (2) RADIAL CA GRADIENT - a faint
    lens-center-anchored chroma-shift field where M/R/CC each carry their
    own radial-distance gradient (M brighter near center, CC brighter at
    edges, R inverted - the literal lens fault), (3) bright feature SPOTS
    with 3-axis channel-offset halos, (4) multi-scale fringe streaks,
    (5) HERO PRISMATIC SPECTRUM FANS - rare bright wedge-shaped 12-20 px
    arcs (the actual rainbow split visible at a hot spot), (6) prismatic
    ring-stamps + diffraction filaments, (7) single-pixel rainbow fleck
    carpet. Wide per-feature M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("spec_chromatic_aberration_r6v2") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)
    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))
    # Base - chroma-rich per-channel drift. R6-loop tick (owner 6/KEEP refinement):
    # substrate M pulled 0.48->0.30 to prevent magenta cast (mean M was 0.597,
    # well over the 0.45 ceiling). The radial CA gradient still adds +0.18 M
    # at the lens center so the optical signature reads, but global field stays
    # darker and the rainbow features pop on a cool ground.
    M = (0.30 + (_fbm(8701, 5.0) - 0.5) * 0.26).astype(np.float32)
    R_ch = (0.42 + (_fbm(8703, 5.0) - 0.5) * 0.28).astype(np.float32)
    CC = (0.40 + (_fbm(8705, 5.0) - 0.5) * 0.32).astype(np.float32)

    # 2) RADIAL CA GRADIENT - the lens-fault signature
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    cx_lens = float(rng.uniform(0.30, 0.70)) * w
    cy_lens = float(rng.uniform(0.30, 0.70)) * h
    rdist = np.sqrt((xx - cx_lens) ** 2 + (yy - cy_lens) ** 2)
    r_norm = (rdist / max(mn * 0.5, 1.0)).astype(np.float32)
    r_norm = np.clip(r_norm, 0, 1.4)
    # M peaks at center, falls off. Anti-magenta refinement: trimmed +0.18 -> +0.10
    # so the global field can't lift mean M past 0.45.
    M = np.clip(M + (1.0 - np.clip(r_norm, 0, 1.0)) * 0.10, 0, 1)
    # R inverted: rough at edges (where CA fringing is worst)
    R_ch = np.clip(R_ch + np.clip(r_norm, 0, 1.0) * 0.14, 0, 1)
    # CC builds at edges - chromatic fringe haze (boosted to keep cool aberration ring)
    CC = np.clip(CC + np.clip(r_norm, 0, 1.0) * 0.26, 0, 1)

    if _CV2_OK:
        # 1) Bright feature spots — anchor points. Density halved + M range cooled
        # (0.62-0.98 -> 0.45-0.85) to keep mean M ≤ 0.45 cap.
        n_spot = max(560, int(h * w / 2570))
        spots = []
        for _ in range(n_spot):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(2, int(rng.uniform(3.0, 8.0) * scale))
            spots.append((cx, cy, rr))
            _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.45, 0.85)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), rr, float(rng.uniform(0.05, 0.28)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.10, 0.96)), -1, lineType=_cv2.LINE_AA)
        # 2) RGB shift fringes — 3 axes per spot, independent offset
        for (cx, cy, rr) in spots:
            ax_M = float(rng.uniform(0, 2 * np.pi))
            ax_R = ax_M + float(rng.uniform(0.5, 2.5))
            ax_CC = ax_M + float(rng.uniform(-2.5, -0.5))
            off_M = rng.uniform(2.0, 6.0) * scale
            off_R = rng.uniform(2.0, 6.0) * scale
            off_CC = rng.uniform(2.0, 6.0) * scale
            r_halo = max(rr + 1, int(rr * 1.6))
            ci_M = (int(cx + np.cos(ax_M) * off_M), int(cy + np.sin(ax_M) * off_M))
            _cv2.circle(M, ci_M, r_halo, float(rng.uniform(0.55, 0.95)), 1, lineType=_cv2.LINE_AA)
            ci_R = (int(cx + np.cos(ax_R) * off_R), int(cy + np.sin(ax_R) * off_R))
            _cv2.circle(R_ch, ci_R, r_halo, float(rng.uniform(0.05, 0.30)), 1, lineType=_cv2.LINE_AA)
            ci_CC = (int(cx + np.cos(ax_CC) * off_CC), int(cy + np.sin(ax_CC) * off_CC))
            _cv2.circle(CC, ci_CC, r_halo, float(rng.uniform(0.10, 0.95)), 1, lineType=_cv2.LINE_AA)
        # 3) Multi-scale fringe zones — 3 scales of short fringe lines
        for scale_mult in (1.0, 1.8, 2.8):
            n_fr = max(2800, int(h * w / 170))
            for _ in range(n_fr):
                cx = rng.uniform(2, w - 2); cy = rng.uniform(2, h - 2)
                length = float(rng.uniform(6.0, 14.0) * scale * scale_mult)
                ang = float(rng.uniform(0, 2 * np.pi))
                x0s = int(cx - np.cos(ang) * length * 0.5)
                y0s = int(cy - np.sin(ang) * length * 0.5)
                x1s = int(cx + np.cos(ang) * length * 0.5)
                y1s = int(cy + np.sin(ang) * length * 0.5)
                # Anti-magenta: M range tightened so multi-scale fringes don't dominate mean.
                _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.08, 0.55)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R_ch, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.08, 0.85)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.20, 0.95)), 1, lineType=_cv2.LINE_AA)
        # 4) RAINBOW LADDER bands — 8-14 px parallel chevron pairs
        n_ladder = max(900, int(h * w / 360))
        for _ in range(n_ladder):
            cx = float(rng.uniform(6, w - 6)); cy = float(rng.uniform(6, h - 6))
            length = float(rng.uniform(8.0, 14.0) * scale)
            ang = float(rng.uniform(0, 2 * np.pi))
            offset = float(rng.uniform(2.0, 4.0) * scale)
            perp = ang + np.pi * 0.5
            # band 1
            ox1 = np.cos(perp) * offset; oy1 = np.sin(perp) * offset
            x0a = int(cx - np.cos(ang) * length * 0.5 + ox1)
            y0a = int(cy - np.sin(ang) * length * 0.5 + oy1)
            x1a = int(cx + np.cos(ang) * length * 0.5 + ox1)
            y1a = int(cy + np.sin(ang) * length * 0.5 + oy1)
            _cv2.line(M, (x0a, y0a), (x1a, y1a), float(rng.uniform(0.60, 0.96)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0a, y0a), (x1a, y1a), float(rng.uniform(0.65, 0.96)), 1, lineType=_cv2.LINE_AA)
            # band 2 (opposite side, different chroma)
            x0b = int(cx - np.cos(ang) * length * 0.5 - ox1)
            y0b = int(cy - np.sin(ang) * length * 0.5 - oy1)
            x1b = int(cx + np.cos(ang) * length * 0.5 - ox1)
            y1b = int(cy + np.sin(ang) * length * 0.5 - oy1)
            _cv2.line(M, (x0b, y0b), (x1b, y1b), float(rng.uniform(0.30, 0.80)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (x0b, y0b), (x1b, y1b), float(rng.uniform(0.10, 0.60)), 1, lineType=_cv2.LINE_AA)
        # 4b) HERO PRISMATIC SPECTRUM FANS - wedge-shaped arcs (the literal rainbow split)
        n_fan = int(np.clip(48 * (mn / 256.0) ** 2, 28, 220))
        for _ in range(n_fan):
            fx = float(rng.uniform(0.10, 0.90) * w); fy = float(rng.uniform(0.10, 0.90) * h)
            r0 = float(rng.uniform(6.0, 10.0) * scale)
            ang_start = float(rng.uniform(0, 2 * np.pi))
            ang_span = float(rng.uniform(0.4, 1.1))
            # Draw 3 concentric arc bands, each with different chroma (the prism split)
            for k in range(3):
                rk = r0 + k * max(1, int(2.0 * scale))
                start_deg = float(np.degrees(ang_start))
                end_deg = float(np.degrees(ang_start + ang_span))
                if k == 0:
                    cM = float(rng.uniform(0.65, 0.95)); cR = float(rng.uniform(0.18, 0.40)); cCC = float(rng.uniform(0.65, 0.92))
                elif k == 1:
                    cM = float(rng.uniform(0.55, 0.90)); cR = float(rng.uniform(0.12, 0.32)); cCC = float(rng.uniform(0.25, 0.60))
                else:
                    cM = float(rng.uniform(0.45, 0.85)); cR = float(rng.uniform(0.08, 0.28)); cCC = float(rng.uniform(0.10, 0.35))
                _cv2.ellipse(M, (int(fx), int(fy)), (int(rk), int(rk)), 0.0, start_deg, end_deg, cM, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R_ch, (int(fx), int(fy)), (int(rk), int(rk)), 0.0, start_deg, end_deg, cR, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (int(fx), int(fy)), (int(rk), int(rk)), 0.0, start_deg, end_deg, cCC, 1, lineType=_cv2.LINE_AA)

        # 5) PRISMATIC RING-STAMPS — concentric triplets 5-10 px, each ring different chroma
        n_ring = max(360, int(h * w / 800))
        for _ in range(n_ring):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            r1 = max(2, int(rng.uniform(2.0, 3.5) * scale))
            r2 = r1 + max(1, int(rng.uniform(1.0, 2.0) * scale))
            r3 = r2 + max(1, int(rng.uniform(1.0, 2.0) * scale))
            _cv2.circle(M, (cx, cy), r1, float(rng.uniform(0.55, 0.94)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r2, float(rng.uniform(0.55, 0.88)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r3, float(rng.uniform(0.55, 0.96)), 1, lineType=_cv2.LINE_AA)
        # 6) DIFFRACTION FILAMENTS — short 3-segment curves
        n_fil = max(380, int(h * w / 720))
        for _ in range(n_fil):
            cx = float(rng.uniform(6, w - 6)); cy = float(rng.uniform(6, h - 6))
            ang = float(rng.uniform(0, 2 * np.pi))
            curve = float(rng.uniform(-0.30, 0.30))
            step = float(rng.uniform(2.2, 3.6)) * scale
            fM = float(rng.uniform(0.40, 0.96))
            fCC = float(rng.uniform(0.20, 0.95))
            px, py = cx, cy
            for _s in range(3):
                ang += curve
                nx = px + np.cos(ang) * step
                ny = py + np.sin(ang) * step
                _cv2.line(M,  (int(px), int(py)), (int(nx), int(ny)), fM, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (int(px), int(py)), (int(nx), int(ny)), fCC, 1, lineType=_cv2.LINE_AA)
                px, py = nx, ny
        # 7) Single-pixel rainbow flecks
        n_fl = max(8000, int(h * w / 80))
        fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
        M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.10, 0.95, n_fl).astype(np.float32))
        R_ch[fy, fx] = np.minimum(R_ch[fy, fx], rng.uniform(0.08, 0.85, n_fl).astype(np.float32))
        CC[fy, fx] = np.maximum(CC[fy, fx], rng.uniform(0.10, 0.95, n_fl).astype(np.float32))
    out = np.stack([np.clip(M, 0, 1), np.clip(R_ch, 0, 1), np.clip(CC, 0, 1)], axis=2).astype(np.float32)
    if sm != 1.0:
        out = out * float(sm) + 0.5 * (1.0 - float(sm))
    return np.clip(out, 0, 1).astype(np.float32)
spec_chromatic_aberration._spb_concept_complete = True


__all__ = ["spec_chromatic_aberration"]
