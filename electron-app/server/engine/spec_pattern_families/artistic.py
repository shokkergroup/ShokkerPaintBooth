"""Artistic spec pattern family for Shokker Paint Booth.

This module is imported by engine.spec_patterns so PATTERN_CATALOG keeps
the legacy public keys while the central spec registry shrinks.
"""
import numpy as np

from ..spec_patterns import (
    _CV2_OK,
    _cv2,
    _flat,
    _gauss,
    _normalize,
    _sm_scale,
    _validate_spec_output,
    multi_scale_noise,
)


def _spb_fast_line_distance(coord, period, width, phase=0.0):
    r = np.abs(np.mod(coord + phase, period) - period * 0.5)
    return np.clip(1.0 - r / max(width, 1e-6), 0.0, 1.0).astype(np.float32)

# ARTISTIC (6 patterns)
# ----------------------------------------------------------------------------

def brushstroke_bold(shape, seed, sm, n_strokes=14, stroke_width=0.022,
                      **kwargs):
    """brushstroke_bold.

    identity: R6 OWNER-CORRECTIVE — owner rated 3/REBUILD: "too sparse,
    features too big (panel-scale), boring". Old version had 90-200 px
    scrape bands violating the 8-32 px doctrine. Rewritten as a DENSE
    field of HUNDREDS of small bold brushstrokes (10-26 px each) using
    a NEW HERO motif: every stroke is a stamped TAPERED BRUSH MARK
    with a narrow start (1 px) widening to a heavy heel (3-5 px), drawn
    as 4 stacked sub-segments, so each mark has the chunky calligrapher
    profile of a real loaded brush. Composite-dark canvas. Five tiers:
    (1) composite-dark linen ground, (2) HERO 250-450 tapered brush
    marks 10-26 px, (3) hatched bristle drag flecks 4-8 px in the gaps,
    (4) tiny pigment-granulation spatter, (5) micro varnish gloss
    pinpoints. Each mark has INDEPENDENT M/R/CC chroma.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 21275)
    mn = min(h, w)
    scale = max(mn / 256.0, 0.5)

    # 1) Composite-DARK linen ground (M, R, CC all low)
    g = _normalize(multi_scale_noise(shape, [2.0, 4.5, 10.0], [0.45, 0.32, 0.23], int(seed) + 21281))
    M = (0.14 + g * 0.06).astype(np.float32)
    R_ch = (0.62 + g * 0.10).astype(np.float32)
    CC = (0.10 + g * 0.06).astype(np.float32)

    if _CV2_OK:
        # 2) HERO TAPERED BRUSH MARKS — dense, 10-26 px each
        n_marks = int(np.clip(350 * (mn / 256.0) ** 2, 250, 1400))
        for _ in range(n_marks):
            cx_g = float(rng.uniform(0, w)); cy_g = float(rng.uniform(0, h))
            ang = float(rng.uniform(0, 2 * np.pi))
            length = float(rng.uniform(10.0, 26.0))  # FINE 10-26 px
            ca, sa = float(np.cos(ang)), float(np.sin(ang))
            # Stroke endpoints
            x0 = cx_g - ca * length * 0.5
            y0 = cy_g - sa * length * 0.5
            x1 = cx_g + ca * length * 0.5
            y1 = cy_g + sa * length * 0.5
            # Per-mark INDEPENDENT chroma
            m_v = float(rng.uniform(0.35, 0.96))
            r_v = float(rng.uniform(0.05, 0.45))
            c_v = float(rng.uniform(0.40, 0.98))
            # 4 sub-segments with tapered thickness: 1px -> 2 -> 3 -> 4 -> 2
            n_sub = 4
            thicks = [1, 2, 3, 4]
            for k in range(n_sub):
                t0 = k / n_sub; t1 = (k + 1) / n_sub
                sx0 = int(x0 + (x1 - x0) * t0)
                sy0 = int(y0 + (y1 - y0) * t0)
                sx1 = int(x0 + (x1 - x0) * t1)
                sy1 = int(y0 + (y1 - y0) * t1)
                _cv2.line(M, (sx0, sy0), (sx1, sy1), m_v, thicks[k], lineType=_cv2.LINE_AA)
                _cv2.line(R_ch, (sx0, sy0), (sx1, sy1), r_v, thicks[k], lineType=_cv2.LINE_AA)
                _cv2.line(CC, (sx0, sy0), (sx1, sy1), c_v, thicks[k], lineType=_cv2.LINE_AA)
            # Heel pinpoint (loaded paint pool at the end of the stroke)
            _cv2.circle(M, (int(x1), int(y1)), 2, float(np.clip(m_v + 0.10, 0, 1)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (int(x1), int(y1)), 2, float(np.clip(c_v + 0.08, 0, 1)), -1, lineType=_cv2.LINE_AA)

        # 3) HATCHED BRISTLE DRAG flecks — fine 4-8 px line clusters in the gaps
        n_drag = int(np.clip(900 * (mn / 256.0) ** 2, 600, 3500))
        for _ in range(n_drag):
            cx_d = int(rng.uniform(0, w)); cy_d = int(rng.uniform(0, h))
            ang_d = float(rng.uniform(0, 2 * np.pi))
            length_d = float(rng.uniform(4.0, 8.0))
            x1d = int(cx_d + np.cos(ang_d) * length_d)
            y1d = int(cy_d + np.sin(ang_d) * length_d)
            _cv2.line(M, (cx_d, cy_d), (x1d, y1d), float(rng.uniform(0.25, 0.75)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx_d, cy_d), (x1d, y1d), float(rng.uniform(0.20, 0.78)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (cx_d, cy_d), (x1d, y1d), float(rng.uniform(0.15, 0.55)), 1, lineType=_cv2.LINE_AA)

    # 4) PIGMENT SPATTER — tiny flecks
    n_fl = int(np.clip(1800 * (mn / 256.0) ** 2, 800, 6000))
    fy_a = rng.integers(0, h, n_fl); fx_a = rng.integers(0, w, n_fl)
    fm_a = rng.uniform(0.30, 0.95, n_fl).astype(np.float32)
    fr_a = rng.uniform(0.06, 0.45, n_fl).astype(np.float32)
    fc_a = rng.uniform(0.35, 0.96, n_fl).astype(np.float32)
    M[fy_a, fx_a] = np.maximum(M[fy_a, fx_a], fm_a)
    R_ch[fy_a, fx_a] = np.minimum(R_ch[fy_a, fx_a], fr_a)
    CC[fy_a, fx_a] = np.maximum(CC[fy_a, fx_a], fc_a)

    # 5) Micro varnish gloss pinpoints
    if _CV2_OK:
        n_sheen = int(np.clip(80 * (mn / 256.0) ** 2, 30, 250))
        for _ in range(n_sheen):
            sx = int(rng.uniform(0, w)); sy = int(rng.uniform(0, h))
            rr = max(1, int(rng.uniform(2, 4)))
            _cv2.circle(CC, (sx, sy), rr, float(rng.uniform(0.85, 0.99)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(M, (sx, sy), rr, float(rng.uniform(0.78, 0.97)), -1, lineType=_cv2.LINE_AA)

    out = np.stack([np.clip(M, 0, 1), np.clip(R_ch, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "brushstroke_bold")
brushstroke_bold._spb_concept_complete = True


def crayon_wax_resist(shape, seed, sm, rub_density=0.35, streak_len=0.12, **kwargs):
    """crayon_wax_resist.

    identity (R6 creative rebuild): Push the child-art crayon-rubbing further
    with a HERO 'crayon-stick streak' motif — 10-18 long parallel waxy stripe
    SWATHES (24-44 px each) carving across the canvas like a kid dragged a
    crayon side-on across the paper, each swath in its own crayon hue with
    independent M/R/CC. UNDER the swathes: dense classic rub field (short
    10-22 px directional strokes). ABOVE the swathes: NEW broken-crayon WAX
    FLAKES — 4-9 px irregular hex-ish chips with bright waxy facet highlights.
    Plus tooth-gap paper exposure, crosshatch accents, paper-fiber flecks, and
    NEW resist-spot puddles where wax repels imaginary paint (2-5 px dark voids
    ringed by bright pigment halos). Six feature tiers, fine 1-44 px, full
    canvas coverage, wide chroma diversity per stroke.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("crayon_wax_resist_r6") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) Paper-grain substrate — independent M/R/CC
    fM = _normalize(multi_scale_noise(shape, [0.7, 1.8, 5.5, 18.0], [0.42, 0.30, 0.20, 0.08], int(seed) + 9721))
    fR = _normalize(multi_scale_noise(shape, [0.7, 1.8, 5.5, 18.0], [0.42, 0.30, 0.20, 0.08], int(seed) + 9722))
    fCC = _normalize(multi_scale_noise(shape, [0.7, 1.8, 5.5, 18.0], [0.42, 0.30, 0.20, 0.08], int(seed) + 9723))
    M = (0.40 + (fM - 0.5) * 0.20).astype(np.float32)
    R_ch = (0.60 + (fR - 0.5) * 0.20).astype(np.float32)
    CC = (0.50 + (fCC - 0.5) * 0.20).astype(np.float32)

    if _CV2_OK:
        # 2) HERO — CRAYON-STICK SWATHES (10-18 long parallel waxy stripes)
        n_sw = int(rng.integers(10, 19))
        for _ in range(n_sw):
            cx = float(rng.uniform(0.05, 0.95) * w)
            cy = float(rng.uniform(0.05, 0.95) * h)
            length = float(rng.uniform(24.0, 44.0) * scale)
            ang = float(rng.uniform(0, 2 * np.pi))
            dx = np.cos(ang) * length * 0.5; dy = np.sin(ang) * length * 0.5
            # crayon-stick swath = 3-4 parallel stripes 2-4 px apart
            n_stripes = int(rng.integers(3, 5))
            offset_step = float(rng.uniform(2.0, 4.0) * scale)
            # independent crayon hue (continuous uniforms)
            cM = float(rng.uniform(0.18, 0.92))
            cR = float(rng.uniform(0.15, 0.85))
            cCC = float(rng.uniform(0.10, 0.85))
            perp_x = -np.sin(ang); perp_y = np.cos(ang)
            for si in range(n_stripes):
                off = (si - (n_stripes - 1) * 0.5) * offset_step
                px0 = int(cx - dx + perp_x * off); py0 = int(cy - dy + perp_y * off)
                px1 = int(cx + dx + perp_x * off); py1 = int(cy + dy + perp_y * off)
                # tiny per-stripe brightness jitter — keeps the swath cohesive but lively
                jit = float(rng.uniform(-0.08, 0.08))
                _cv2.line(M, (px0, py0), (px1, py1), float(np.clip(cM + jit, 0.05, 0.95)), max(1, int(scale)), lineType=_cv2.LINE_AA)
                _cv2.line(R_ch, (px0, py0), (px1, py1), float(np.clip(cR + jit, 0.05, 0.95)), max(1, int(scale)), lineType=_cv2.LINE_AA)
                _cv2.line(CC, (px0, py0), (px1, py1), float(np.clip(cCC + jit, 0.05, 0.95)), max(1, int(scale)), lineType=_cv2.LINE_AA)

        # 3) CLASSIC RUB STROKES — many short directional 10-22 px (kept dense)
        n_strokes = int(np.clip(rub_density * h * w * 0.0036, 800, 14000))
        drifts = [0.05, 0.18, -0.12, 0.42, -0.30]
        for _ in range(n_strokes):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            length = float(rng.uniform(10.0, 22.0) * scale)
            ang = float(rng.choice(drifts)) + float(rng.normal(0, 0.08))
            x1 = int(np.clip(cx + np.cos(ang) * length, 0, w - 1))
            y1 = int(np.clip(cy + np.sin(ang) * length, 0, h - 1))
            _cv2.line(M, (cx, cy), (x1, y1), float(rng.uniform(0.12, 0.88)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (cx, cy), (x1, y1), float(rng.uniform(0.25, 0.92)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (x1, y1), float(rng.uniform(0.10, 0.92)), 1, lineType=_cv2.LINE_AA)

        # 4) WAX-PILE DABS — 2-4 px round wax accumulations
        n_dabs = int(np.clip(900 * (mn / 2048.0) ** 2, 320, 2800))
        for _ in range(n_dabs):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1.5, 3.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.08, 0.42)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(rng.uniform(0.50, 0.92)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.30, 0.78)), -1, lineType=_cv2.LINE_AA)

        # 5) NEW — BROKEN WAX FLAKES (4-9 px irregular polygon chips with bright facet)
        n_flake = int(np.clip(700 * (mn / 2048.0) ** 2, 250, 2200))
        for _ in range(n_flake):
            cx = int(rng.integers(2, w - 2)); cy = int(rng.integers(2, h - 2))
            r = max(2, int(rng.uniform(2.0, 4.5) * scale))
            # 5-7 vertex irregular polygon
            n_v = int(rng.integers(5, 8))
            angles = np.sort(rng.uniform(0, 2 * np.pi, n_v))
            radii = rng.uniform(r * 0.6, r * 1.1, n_v)
            pts = np.stack([
                np.clip(cx + np.cos(angles) * radii, 0, w - 1),
                np.clip(cy + np.sin(angles) * radii, 0, h - 1)
            ], axis=-1).astype(np.int32)
            flM = float(rng.uniform(0.18, 0.78))
            flR = float(rng.uniform(0.42, 0.88))
            flCC = float(rng.uniform(0.20, 0.72))
            _cv2.fillPoly(M, [pts], flM, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R_ch, [pts], flR, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts], flCC, lineType=_cv2.LINE_AA)
            # bright waxy facet — small inner circle
            _cv2.circle(M, (cx, cy), max(1, r // 2), float(rng.uniform(0.72, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), max(1, r // 2), float(rng.uniform(0.10, 0.32)), -1, lineType=_cv2.LINE_AA)

        # 6) CROSSHATCH ACCENT STROKES — short crossed 5-10 px
        n_cross = int(np.clip(550 * (mn / 2048.0) ** 2, 200, 1600))
        for _ in range(n_cross):
            cx = float(rng.uniform(4, w - 4)); cy = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(5.0, 10.0) * scale)
            ang = float(rng.choice([np.pi * 0.25, -np.pi * 0.25])) + float(rng.normal(0, 0.12))
            x0s = int(cx - np.cos(ang) * length * 0.5)
            y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5)
            y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.20, 0.82)), 1, lineType=_cv2.LINE_AA)

        # 7) NEW — RESIST-SPOT PUDDLES (2-5 px dark void ringed by bright pigment halo)
        n_resist = int(np.clip(400 * (mn / 2048.0) ** 2, 140, 1200))
        for _ in range(n_resist):
            cx = int(rng.integers(3, w - 3)); cy = int(rng.integers(3, h - 3))
            r_inner = max(1, int(rng.uniform(1.5, 2.8) * scale))
            r_outer = r_inner + max(1, int(rng.uniform(1.2, 2.4) * scale))
            # bright halo first
            _cv2.circle(M, (cx, cy), r_outer, float(rng.uniform(0.62, 0.94)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r_outer, float(rng.uniform(0.18, 0.45)), -1, lineType=_cv2.LINE_AA)
            # dark void overlaid
            _cv2.circle(M, (cx, cy), r_inner, float(rng.uniform(0.05, 0.20)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r_inner, float(rng.uniform(0.62, 0.92)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_inner, float(rng.uniform(0.55, 0.88)), -1, lineType=_cv2.LINE_AA)

    # 8) TOOTH GAPS — paper exposure mask
    tooth = multi_scale_noise(shape, [1.0, 2.2], [0.55, 0.45], int(seed) + 9724)
    tooth_mask = (tooth > np.quantile(tooth, 0.84)).astype(np.float32)
    M = np.clip(M - tooth_mask * 0.22, 0, 1)
    R_ch = np.clip(R_ch + tooth_mask * 0.20, 0, 1)
    CC = np.clip(CC - tooth_mask * 0.15, 0, 1)

    # 9) PAPER FIBER FLECKS — vectorized
    n_flecks = int(np.clip(2200 * (mn / 2048.0) ** 2, 800, 6200))
    fx = rng.integers(0, w, n_flecks); fy = rng.integers(0, h, n_flecks)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.45, 0.88, n_flecks).astype(np.float32))
    R_ch[fy, fx] = np.clip(R_ch[fy, fx] + rng.uniform(-0.15, 0.20, n_flecks).astype(np.float32), 0, 1)

    out = np.stack([M, R_ch, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
crayon_wax_resist._spb_concept_complete = True


def airbrush_gradient_bloom(shape, seed, sm, **kwargs):
    """airbrush_gradient_bloom.

    identity (R6 CREATIVE rebuild): airbrush pigment haze with TWO HERO
    motifs — (1) STENCIL FRISKET HARD-EDGE patches: sharp polygonal cut-
    outs (16-40 px) where the airbrush was masked off, creating crisp
    high-contrast borders between bloom-soaked zones and clean substrate
    (a real airbrush hallmark); (2) NEEDLE-SPLATTER STARBURSTS:
    accidental tap-splatter where a tiny bright droplet has a 6-12 px
    radial spray of micro-droplets fanning around it. Stacked: (a)
    independent-channel FBM mist substrate, (b) soft bloom host zones
    40-110 px, (c) HERO frisket polygons with razor edges, (d) HERO
    needle-splatter starbursts, (e) dense 6-16 px pigment beads, (f)
    fine-tip 8-20 px needle hair strokes, (g) pigment micro-flecks +
    dropout pits. Per-feature INDEPENDENT continuous M/R/CC across wide
    chroma. Full canvas coverage.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("airbrush_gradient_bloom_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # 1) THREE-CHANNEL INDEPENDENT MIST SUBSTRATE
    mistM = _normalize(multi_scale_noise(shape, [4.0, 12.0, 28.0], [0.45, 0.35, 0.20], int(seed) + 7711))
    mistR = _normalize(multi_scale_noise(shape, [4.0, 12.0, 28.0], [0.45, 0.35, 0.20], int(seed) + 7713))
    mistCC = _normalize(multi_scale_noise(shape, [4.0, 12.0, 28.0], [0.45, 0.35, 0.20], int(seed) + 7715))
    M  = (0.42 + (mistM  - 0.5) * 0.26).astype(np.float32)
    R  = (0.52 + (mistR  - 0.5) * 0.22).astype(np.float32)
    CC = (0.40 + (mistCC - 0.5) * 0.26).astype(np.float32)

    # 2) BLOOM HOST ZONES — 10-16 soft radial color hosts with independent triples
    n_bloom = int(rng.integers(10, 17))
    for _ in range(n_bloom):
        cx = float(rng.uniform(0.02, 0.98) * w)
        cy = float(rng.uniform(0.02, 0.98) * h)
        radius = float(rng.uniform(40.0, 110.0) * scale)
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        falloff = np.exp(-(d / radius) ** 2 * 1.7).astype(np.float32)
        bM = float(rng.uniform(0.15, 0.92))
        bR = float(rng.uniform(0.12, 0.78))
        bCC = float(rng.uniform(0.05, 0.62))
        M  = M  * (1 - falloff * 0.62) + bM  * falloff * 0.62
        R  = R  * (1 - falloff * 0.62) + bR  * falloff * 0.62
        CC = CC * (1 - falloff * 0.62) + bCC * falloff * 0.62

    if _CV2_OK:
        # 2b) HERO STENCIL FRISKET POLYGONS — sharp-edged masked zones
        # 16-40 px polygons stamping crisp high-contrast cutouts.
        n_frisk = int(np.clip(180 * (mn / 2048.0) ** 2, 70, 600))
        for _ in range(n_frisk):
            cx = float(rng.uniform(0.04, 0.96) * w)
            cy = float(rng.uniform(0.04, 0.96) * h)
            r_fr = float(rng.uniform(8.0, 20.0) * scale)
            n_vert = int(rng.integers(3, 7))
            ang0 = float(rng.uniform(0, 2 * np.pi))
            verts = []
            for k in range(n_vert):
                a = ang0 + (k * 2 * np.pi / n_vert) + float(rng.uniform(-0.25, 0.25))
                rj = r_fr * float(rng.uniform(0.55, 1.0))
                verts.append([int(np.clip(cx + np.cos(a) * rj, 0, w - 1)),
                              int(np.clip(cy + np.sin(a) * rj, 0, h - 1))])
            poly = np.array([verts], dtype=np.int32)
            # 60/40: either a CLEAN cutout (low M, high R, low CC) or
            # a hard chroma slap (high M)
            if rng.random() < 0.55:
                _cv2.fillPoly(M, poly, float(rng.uniform(0.10, 0.30)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, poly, float(rng.uniform(0.62, 0.95)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, poly, float(rng.uniform(0.06, 0.32)), lineType=_cv2.LINE_AA)
            else:
                _cv2.fillPoly(M, poly, float(rng.uniform(0.65, 0.95)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, poly, float(rng.uniform(0.08, 0.32)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, poly, float(rng.uniform(0.35, 0.78)), lineType=_cv2.LINE_AA)
            # razor edge outline
            _cv2.polylines(M, poly, True, float(rng.uniform(0.85, 0.99)), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(R, poly, True, float(rng.uniform(0.04, 0.18)), 1, lineType=_cv2.LINE_AA)

        # 2c) HERO NEEDLE-SPLATTER STARBURSTS — accidental tap splatter:
        # bright droplet at center + 5-9 micro-droplet ejecta in a cone.
        n_splat = int(np.clip(220 * (mn / 2048.0) ** 2, 80, 700))
        for _ in range(n_splat):
            cx = int(rng.uniform(0.03, 0.97) * w); cy = int(rng.uniform(0.03, 0.97) * h)
            r_main = max(1, int(rng.uniform(1.5, 3.0) * scale))
            # Bright pigment droplet
            _cv2.circle(M, (cx, cy), r_main, float(rng.uniform(0.78, 0.99)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r_main, float(rng.uniform(0.04, 0.20)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_main, float(rng.uniform(0.04, 0.22)), -1, lineType=_cv2.LINE_AA)
            # Cone of ejecta micro-droplets
            cone_ang = float(rng.uniform(0, 2 * np.pi))
            cone_spread = float(np.pi * 0.6)
            n_eject = int(rng.integers(5, 10))
            for _e in range(n_eject):
                a = cone_ang + float(rng.uniform(-cone_spread * 0.5, cone_spread * 0.5))
                d = float(rng.uniform(3.0, 12.0) * scale)
                ex = int(np.clip(cx + np.cos(a) * d, 0, w - 1))
                ey = int(np.clip(cy + np.sin(a) * d, 0, h - 1))
                r_e = max(1, int(rng.uniform(0.6, 1.4) * scale))
                _cv2.circle(M, (ex, ey), r_e, float(rng.uniform(0.62, 0.95)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (ex, ey), r_e, float(rng.uniform(0.06, 0.28)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (ex, ey), r_e, float(rng.uniform(0.04, 0.30)), -1, lineType=_cv2.LINE_AA)

        # 3) DENSE FINE BLOOM BEADS (5x density, 6-16 px)
        n_dot = int(np.clip(4200 * (mn / 2048.0) ** 2, 1400, 14000))
        # Use vectorized stamps for speed: half via cv2 loop, half via pixel
        for _ in range(n_dot):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(3.0, 8.0) * scale))
            _cv2.circle(M,  (cx, cy), r, float(rng.uniform(0.30, 0.95)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R,  (cx, cy), r, float(rng.uniform(0.12, 0.62)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.06, 0.50)), -1, lineType=_cv2.LINE_AA)

        # 4) FINE-TIP NEEDLE HAIRS — short curved 8-20 px strokes
        n_hair = int(np.clip(1800 * (mn / 2048.0) ** 2, 600, 5400))
        for _ in range(n_hair):
            cxh = float(rng.uniform(4, w - 4)); cyh = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(8.0, 20.0) * scale)
            ang = float(rng.uniform(0, 2 * np.pi))
            dx = np.cos(ang) * length * 0.5; dy = np.sin(ang) * length * 0.5
            p0 = (int(cxh - dx), int(cyh - dy)); p1 = (int(cxh + dx), int(cyh + dy))
            _cv2.line(M, p0, p1, float(rng.uniform(0.45, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, p0, p1, float(rng.uniform(0.12, 0.42)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, p0, p1, float(rng.uniform(0.05, 0.30)), 1, lineType=_cv2.LINE_AA)

    # 5) PIGMENT MICRO-FLECKS + DROPOUT PITS — vectorized
    n_fl = int(np.clip(4500 * (mn / 2048.0) ** 2, 1500, 15000))
    fx = rng.integers(0, w, n_fl); fy = rng.integers(0, h, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.62, 0.98, n_fl).astype(np.float32))
    CC[fy, fx] = np.minimum(CC[fy, fx], rng.uniform(0.04, 0.20, n_fl).astype(np.float32))
    n_dr = int(np.clip(2200 * (mn / 2048.0) ** 2, 700, 7200))
    dx_ = rng.integers(0, w, n_dr); dy_ = rng.integers(0, h, n_dr)
    M[dy_, dx_] = np.minimum(M[dy_, dx_], rng.uniform(0.06, 0.20, n_dr).astype(np.float32))
    R[dy_, dx_] = np.maximum(R[dy_, dx_], rng.uniform(0.58, 0.92, n_dr).astype(np.float32))

    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)


airbrush_gradient_bloom._spb_concept_complete = True


def spray_paint_drip(shape, seed, sm, num_drips=9, drip_len=0.40, **kwargs):
    """spray_paint_drip.

    identity (R6 creative rebuild): A graffiti-tagged panel with the drip
    anatomy intact (bead + tail + puddle teardrops) PLUS new HERO motifs that
    sell the spray-tag story at thumbnail scale: (HERO-A) CASCADING DRIP
    COLUMNS — 6-12 vertical columns where 3-5 drips stack head-to-tail down
    the panel sharing a chroma, reading as a single long paint run that broke
    into pearls; (HERO-B) NOZZLE-BURST ROSETTES — 8-14 small radial bursts
    where the can sputtered, with 8-12 short 4-10 px radial streaks emanating
    from a bright center bead. Plus 2.5x classic teardrop drips, 1.8x
    overspray dots, dark nozzle-grit specks, micro-trickle hairlines, and
    aerosol mist single-pixel pepper. Per-feature INDEPENDENT continuous
    M/R/CC. Every primitive 1-22 px.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 50219)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) AEROSOL MIST SUBSTRATE — INDEPENDENT M/R/CC
    mistM = _normalize(multi_scale_noise(shape, [2.0, 5.5, 14.0], [0.50, 0.30, 0.20], int(seed) + 9741))
    mistR = _normalize(multi_scale_noise(shape, [2.5, 6.0, 16.0], [0.48, 0.32, 0.20], int(seed) + 9742))
    mistCC = _normalize(multi_scale_noise(shape, [3.0, 7.0, 18.0], [0.46, 0.32, 0.22], int(seed) + 9743))
    overspray = _normalize(multi_scale_noise(shape, [6.0, 22.0], [0.6, 0.4], int(seed) + 9745))
    M = (0.42 + (mistM - 0.5) * 0.20 + (overspray - 0.5) * 0.10).astype(np.float32)
    R = (0.40 + (mistR - 0.5) * 0.14 - (overspray - 0.5) * 0.10).astype(np.float32)
    CC = (0.32 + (mistCC - 0.5) * 0.16 + (overspray - 0.5) * 0.22).astype(np.float32)

    if _CV2_OK:
        # 2) HERO-A — CASCADING DRIP COLUMNS (6-12 stacked head-to-tail drips per column)
        n_col = int(rng.integers(6, 13))
        for _ in range(n_col):
            col_x = float(rng.uniform(0.04, 0.96) * w)
            col_y = float(rng.uniform(0.02, 0.30) * h)  # start near top
            # Shared chroma for this column — looks like one paint run
            cM_col = float(rng.uniform(0.55, 0.95))
            cR_col = float(rng.uniform(0.06, 0.34))
            cCC_col = float(rng.uniform(0.08, 0.88))
            stack = int(rng.integers(3, 6))
            cur_x, cur_y = col_x, col_y
            for si in range(stack):
                seg_len = float(rng.uniform(10.0, 18.0) * scale)
                wob = float(rng.normal(0, max(1.0, w * 0.004)))
                nx_ = float(np.clip(cur_x + wob, 0, w - 1))
                ny_ = float(np.clip(cur_y + seg_len, 0, h - 1))
                jit = float(rng.uniform(-0.06, 0.06))
                seg_M = float(np.clip(cM_col + jit, 0.05, 0.98))
                seg_R = float(np.clip(cR_col + jit * 0.6, 0.02, 0.95))
                seg_CC = float(np.clip(cCC_col + jit * 0.5, 0.02, 0.95))
                thick = max(1, int(float(rng.uniform(1.0, 2.0)) * scale))
                # bead at top of segment
                br = max(2, int(float(rng.uniform(2.2, 3.6)) * scale))
                _cv2.circle(M, (int(cur_x), int(cur_y)), br, seg_M, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (int(cur_x), int(cur_y)), br, seg_R, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (int(cur_x), int(cur_y)), br, seg_CC, -1, lineType=_cv2.LINE_AA)
                # tail
                _cv2.line(M, (int(cur_x), int(cur_y)), (int(nx_), int(ny_)), seg_M, thick, lineType=_cv2.LINE_AA)
                _cv2.line(R, (int(cur_x), int(cur_y)), (int(nx_), int(ny_)), seg_R, thick, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (int(cur_x), int(cur_y)), (int(nx_), int(ny_)), seg_CC, thick, lineType=_cv2.LINE_AA)
                cur_x, cur_y = nx_, ny_
                if cur_y >= h - 4:
                    break
            # final puddle at bottom of column
            pr = max(2, int(float(rng.uniform(2.0, 3.5)) * scale))
            _cv2.circle(M, (int(cur_x), int(cur_y)), pr, cM_col, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (int(cur_x), int(cur_y)), pr, cR_col, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (int(cur_x), int(cur_y)), pr, cCC_col, -1, lineType=_cv2.LINE_AA)

        # 2b) CLASSIC DRIP BEAD + TAIL + PUDDLE — 2.5x density independent drips
        n_drip = int(np.clip(1100 * (mn / 2048.0) ** 2, 380, 3400))
        for _ in range(n_drip):
            x0 = int(rng.integers(0, w))
            y0 = int(rng.integers(0, max(1, int(h * 0.88))))
            length = int(np.clip(float(rng.uniform(10.0, 20.0)) * scale, 4, h - y0 - 1))
            wobble = int(rng.normal(0, max(1.0, w * 0.005)))
            thick = max(1, int(float(rng.uniform(1.0, 2.2)) * scale))
            x1 = int(np.clip(x0 + wobble, 0, w - 1))
            y1 = int(np.clip(y0 + length, 0, h - 1))
            mM = float(rng.uniform(0.55, 0.95))
            mR = float(rng.uniform(0.06, 0.34))
            mCC = float(rng.uniform(0.08, 0.88))
            # Bead head — wider
            br = max(2, int(float(rng.uniform(2.0, 3.5)) * scale))
            _cv2.circle(M, (x0, y0), br, mM, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (x0, y0), br, mR, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (x0, y0), br, mCC, -1, lineType=_cv2.LINE_AA)
            # Vertical tail
            _cv2.line(M, (x0, y0), (x1, y1), mM, thick, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0, y0), (x1, y1), mR, thick, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), mCC, thick, lineType=_cv2.LINE_AA)
            # Puddle droplet at end
            pr = max(1, int(float(rng.uniform(1.5, 2.8)) * scale))
            _cv2.circle(M, (x1, y1), pr, mM, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (x1, y1), pr, mR, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (x1, y1), pr, mCC, -1, lineType=_cv2.LINE_AA)

        # 2c) HERO-B — NOZZLE-BURST ROSETTES (8-14 small radial bursts)
        n_rose = int(rng.integers(8, 15))
        for _ in range(n_rose):
            rcx = int(rng.uniform(0.04, 0.96) * w)
            rcy = int(rng.uniform(0.04, 0.96) * h)
            n_ray = int(rng.integers(8, 13))
            rM = float(rng.uniform(0.60, 0.95))
            rR = float(rng.uniform(0.08, 0.30))
            rCC = float(rng.uniform(0.08, 0.85))
            # bright center bead
            cr = max(2, int(float(rng.uniform(2.0, 3.2)) * scale))
            _cv2.circle(M, (rcx, rcy), cr, rM, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (rcx, rcy), cr, rR, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (rcx, rcy), cr, rCC, -1, lineType=_cv2.LINE_AA)
            # rays
            for k in range(n_ray):
                ang = float(k * (2 * np.pi / n_ray) + rng.uniform(-0.15, 0.15))
                L = float(rng.uniform(4.0, 10.0) * scale)
                rx2 = int(np.clip(rcx + np.cos(ang) * L, 0, w - 1))
                ry2 = int(np.clip(rcy + np.sin(ang) * L, 0, h - 1))
                jit = float(rng.uniform(-0.10, 0.10))
                _cv2.line(M, (rcx, rcy), (rx2, ry2), float(np.clip(rM + jit, 0.1, 0.97)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (rcx, rcy), (rx2, ry2), float(np.clip(rR + jit * 0.5, 0.04, 0.5)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (rcx, rcy), (rx2, ry2), float(np.clip(rCC + jit, 0.05, 0.95)), 1, lineType=_cv2.LINE_AA)

        # 3) AEROSOL OVERSPRAY DOTS — 1.8x density, 2-4 px
        n_ov = int(np.clip(2500 * (mn / 2048.0) ** 2, 900, 6300))
        for _ in range(n_ov):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r_s = max(1, int(float(rng.uniform(1.4, 3.0)) * scale))
            _cv2.circle(M, (cx, cy), r_s, float(rng.uniform(0.42, 0.92)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r_s, float(rng.uniform(0.08, 0.42)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_s, float(rng.uniform(0.12, 0.88)), -1, lineType=_cv2.LINE_AA)

        # 4) NOZZLE SPLATTER FLECKS — 1-2 px dark grit
        n_sp = int(np.clip(1700 * (mn / 2048.0) ** 2, 580, 4100))
        for _ in range(n_sp):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r_s = max(1, int(float(rng.uniform(1.0, 1.8)) * scale))
            _cv2.circle(M, (cx, cy), r_s, float(rng.uniform(0.08, 0.34)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r_s, float(rng.uniform(0.55, 0.94)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_s, float(rng.uniform(0.48, 0.92)), -1, lineType=_cv2.LINE_AA)

        # 5) MICRO-TRICKLE — NEW 3-6 px short downward dribbles
        n_tr = int(np.clip(800 * (mn / 2048.0) ** 2, 280, 2400))
        for _ in range(n_tr):
            x0 = int(rng.integers(0, w)); y0 = int(rng.integers(0, max(1, h - 8)))
            length = int(float(rng.uniform(3.0, 6.0)) * scale)
            x1 = int(np.clip(x0 + int(rng.normal(0, max(0.5, w * 0.002))), 0, w - 1))
            y1 = int(np.clip(y0 + length, 0, h - 1))
            _cv2.line(M, (x0, y0), (x1, y1), float(rng.uniform(0.50, 0.90)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.15, 0.80)), 1, lineType=_cv2.LINE_AA)

    # 6) DENSE OVERSPRAY MIST SPECKS — single pixel
    n_fl = int(np.clip(2800 * (mn / 2048.0) ** 2, 950, 6500))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.42, 0.95, n_fl).astype(np.float32))
    R[fy, fx] = np.minimum(R[fy, fx], rng.uniform(0.08, 0.38, n_fl).astype(np.float32))
    CC[fy, fx] = np.maximum(CC[fy, fx], rng.uniform(0.12, 0.88, n_fl).astype(np.float32))

    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)


spray_paint_drip._spb_concept_complete = True


def stippled_dots_fine(shape, seed, sm, dot_density=0.04, dot_radius=1.2,
                         **kwargs):
    """stippled_dots_fine.

    identity (R6 creative rebuild): a true Seurat-style pointillist panel where
    SIGNATURE differentiators are (a) CHROMATIC CONCENTRATION ZONES — three
    overlapping low-freq scalar maps decide where warm vs cool vs neutral
    dots are densest, producing distinct color regions you can actually see
    (vs uniform mixing); (b) TONAL HALOS — soft 6-10 px ellipse pools under
    dense dot clusters giving paper a glow; (c) PEN-INK STIPPLE HATCHING
    — short 4-7 px directional stipple chains in shadow zones. Layers:
    (1) paper substrate + cluster density wash, (2) tonal halo pools (NEW),
    (3) WARM zone-biased dots, (4) COOL zone-biased dots, (5) NEUTRAL
    zone-biased dots, (6) pepper grit dark dots, (7) chroma sub-clusters,
    (8) PEN-INK STIPPLE HATCH CHAINS (NEW), (9) dense single-pixel speckle.
    Per-dot INDEPENDENT continuous M/R/CC. Every primitive 1-3 px (chains
    are 4-7 px directional but still 1 px thick).
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 50220)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) PAPER SUBSTRATE + cluster wash
    paper = _normalize(multi_scale_noise(shape, [1.5, 4.0, 12.0], [0.50, 0.32, 0.18], int(seed) + 9751))
    paperR = _normalize(multi_scale_noise(shape, [1.8, 5.0, 14.0], [0.48, 0.32, 0.20], int(seed) + 9753))
    clusters = _normalize(multi_scale_noise(shape, [10.0, 32.0], [0.60, 0.40], int(seed) + 9752))
    M = (0.34 + (paper - 0.5) * 0.12 + (clusters - 0.5) * 0.10).astype(np.float32)
    R = (0.52 + (paperR - 0.5) * 0.10 - (clusters - 0.5) * 0.10).astype(np.float32)
    CC = (0.42 + (clusters - 0.5) * 0.20).astype(np.float32)

    # 1b) CHROMATIC CONCENTRATION ZONES — three low-freq scalar maps
    warm_zone = _normalize(multi_scale_noise(shape, [1.1, 2.5], [0.7, 0.3], int(seed) + 50301))
    cool_zone = _normalize(multi_scale_noise(shape, [1.3, 2.8], [0.7, 0.3], int(seed) + 50311))
    neut_zone = _normalize(multi_scale_noise(shape, [1.5, 3.0], [0.7, 0.3], int(seed) + 50321))

    def _zone_sample(zone_map, n_total):
        # Rejection-sample biased toward higher zone values
        out_x = np.empty(n_total, dtype=np.int32)
        out_y = np.empty(n_total, dtype=np.int32)
        got = 0
        attempts = 0
        while got < n_total and attempts < n_total * 6:
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            if zone_map[cy, cx] > rng.uniform(0.30, 0.55):
                out_x[got] = cx; out_y[got] = cy; got += 1
            attempts += 1
        # Fill any remaining with uniform
        if got < n_total:
            out_x[got:] = rng.integers(0, w, n_total - got)
            out_y[got:] = rng.integers(0, h, n_total - got)
        return out_x, out_y

    if _CV2_OK:
        # 2) TONAL HALO POOLS — soft ellipse pools where dot density highest (NEW)
        n_halo = int(np.clip(140 * (mn / 2048.0) ** 2, 50, 400))
        for _ in range(n_halo):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            ax = max(3, int(rng.uniform(3.0, 5.0) * scale))
            ay = max(2, int(rng.uniform(2.0, 4.0) * scale))
            ang_e = float(rng.uniform(0, np.pi))
            _cv2.ellipse(M, (cx, cy), (ax, ay), float(np.degrees(ang_e)), 0, 360, float(rng.uniform(0.42, 0.62)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (ax, ay), float(np.degrees(ang_e)), 0, 360, float(rng.uniform(0.35, 0.55)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (ax, ay), float(np.degrees(ang_e)), 0, 360, float(rng.uniform(0.30, 0.55)), -1, lineType=_cv2.LINE_AA)

        # 3) WARM zone-biased dots — high M, low CC, bright
        n_warm = int(np.clip(5500 * (mn / 2048.0) ** 2, 1800, 12000))
        wx, wy = _zone_sample(warm_zone, n_warm)
        for i in range(n_warm):
            cx = int(wx[i]); cy = int(wy[i])
            r_s = max(1, int(float(rng.uniform(1.0, 1.8)) * scale))
            _cv2.circle(M, (cx, cy), r_s, float(rng.uniform(0.65, 0.95)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r_s, float(rng.uniform(0.10, 0.30)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_s, float(rng.uniform(0.10, 0.32)), -1, lineType=_cv2.LINE_AA)

        # 4) COOL zone-biased dots — high CC, mid M
        n_cool = int(np.clip(5500 * (mn / 2048.0) ** 2, 1800, 12000))
        cxs, cys = _zone_sample(cool_zone, n_cool)
        for i in range(n_cool):
            cx = int(cxs[i]); cy = int(cys[i])
            r_s = max(1, int(float(rng.uniform(1.0, 1.8)) * scale))
            _cv2.circle(M, (cx, cy), r_s, float(rng.uniform(0.42, 0.72)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r_s, float(rng.uniform(0.18, 0.40)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_s, float(rng.uniform(0.62, 0.92)), -1, lineType=_cv2.LINE_AA)

        # 5) NEUTRAL zone-biased dots — mid M, mid CC
        n_neut = int(np.clip(4500 * (mn / 2048.0) ** 2, 1500, 10000))
        nxs, nys = _zone_sample(neut_zone, n_neut)
        for i in range(n_neut):
            cx = int(nxs[i]); cy = int(nys[i])
            r_s = max(1, int(float(rng.uniform(1.0, 1.6)) * scale))
            _cv2.circle(M, (cx, cy), r_s, float(rng.uniform(0.32, 0.60)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r_s, float(rng.uniform(0.30, 0.55)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_s, float(rng.uniform(0.35, 0.65)), -1, lineType=_cv2.LINE_AA)

        # 5b) PEN-INK STIPPLE HATCH CHAINS — 4-7 px directional chains (NEW)
        n_chain = int(np.clip(700 * (mn / 2048.0) ** 2, 240, 2000))
        for _ in range(n_chain):
            cx = float(rng.uniform(2, w - 2)); cy = float(rng.uniform(2, h - 2))
            n_dots = int(rng.integers(3, 6))
            ang_c = float(rng.uniform(0, 2 * np.pi))
            dvm = float(rng.uniform(0.08, 0.30))   # dark dots (shadow stipple)
            dvr = float(rng.uniform(0.55, 0.85))
            dvcc = float(rng.uniform(0.45, 0.78))
            for k in range(n_dots):
                ox = int(np.clip(cx + np.cos(ang_c) * k * 1.6 * scale, 0, w - 1))
                oy = int(np.clip(cy + np.sin(ang_c) * k * 1.6 * scale, 0, h - 1))
                _cv2.circle(M, (ox, oy), 1, dvm + float(rng.uniform(-0.04, 0.04)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (ox, oy), 1, dvr + float(rng.uniform(-0.05, 0.05)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (ox, oy), 1, dvcc + float(rng.uniform(-0.05, 0.05)), -1, lineType=_cv2.LINE_AA)

        # 5) PEPPER GRIT — dark 1-2 px
        n_pep = int(np.clip(3000 * (mn / 2048.0) ** 2, 1000, 6800))
        for _ in range(n_pep):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r_s = max(1, int(float(rng.uniform(1.0, 1.6)) * scale))
            _cv2.circle(M, (cx, cy), r_s, float(rng.uniform(0.06, 0.22)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r_s, float(rng.uniform(0.55, 0.92)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_s, float(rng.uniform(0.50, 0.92)), -1, lineType=_cv2.LINE_AA)

        # 6) CHROMA SUB-CLUSTERS — NEW 2-3 px tight groupings (3 dots within 4 px)
        n_clu = int(np.clip(900 * (mn / 2048.0) ** 2, 320, 2400))
        for _ in range(n_clu):
            cx = int(rng.integers(2, max(3, w - 2))); cy = int(rng.integers(2, max(3, h - 2)))
            band_M = float(rng.uniform(0.45, 0.92))
            band_R = float(rng.uniform(0.08, 0.40))
            band_CC = float(rng.uniform(0.12, 0.85))
            for kx, ky in [(0, 0), (1, 1), (-1, 1)]:
                xx = int(np.clip(cx + kx, 0, w - 1)); yy = int(np.clip(cy + ky, 0, h - 1))
                _cv2.circle(M, (xx, yy), 1, band_M + float(rng.uniform(-0.05, 0.05)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (xx, yy), 1, band_R + float(rng.uniform(-0.05, 0.05)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (xx, yy), 1, band_CC + float(rng.uniform(-0.05, 0.05)), -1, lineType=_cv2.LINE_AA)

    # 7) DENSE SINGLE-PIXEL MICRO SPECKLE
    n_fl = int(np.clip(3500 * (mn / 2048.0) ** 2, 1200, 8000))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.50, 0.96, n_fl).astype(np.float32))
    R[fy, fx] = np.minimum(R[fy, fx], rng.uniform(0.04, 0.32, n_fl).astype(np.float32))
    CC[fy, fx] = np.maximum(CC[fy, fx], rng.uniform(0.08, 0.88, n_fl).astype(np.float32))

    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)


stippled_dots_fine._spb_concept_complete = True


def halftone_print(shape, seed, sm, cell=12, dot_max=0.45, **kwargs):
    """halftone_print.

    identity (R6 creative rebuild): Pop-art Lichtenstein halftone with the
    full comic-book printing-press story. HERO motifs added: (A) three
    OFFSET CMY plate-registration GRIDS — three halftone dot fields at
    slightly different rotation angles and chroma each, so the eye reads
    cyan-magenta-yellow misregistration over the same field; (B) BURST/STAR
    BANG SHAPES — 4-8 spiky 16-28 px starbursts (Lichtenstein 'POW!' frames)
    in independent chroma. Plus dense 3-5 px halftone cells, micro ink-blots,
    misprint drag hairlines, registration-cross marks, and dust flecks. Wide
    chroma diversity, fine 1-28 px features, full canvas coverage.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 67820)
    scale = max(min(h, w) / 2048.0, 0.25)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    angle = float(rng.uniform(-0.35, 0.35))
    xr = xx * np.cos(angle) - yy * np.sin(angle)
    yr = xx * np.sin(angle) + yy * np.cos(angle)
    # FORCE tight 3-5 px halftone cell (was based on `cell` param — too big)
    fine_cell = max(3.0, min(5.0, float(cell) * 0.30))
    # INDEPENDENT M/R/CC tone fields
    tone_M = _normalize(multi_scale_noise(shape, [3, 9, 22], [0.50, 0.32, 0.18], int(seed) + 9761))
    tone_R = _normalize(multi_scale_noise(shape, [4, 10, 24], [0.50, 0.32, 0.18], int(seed) + 9763))
    tone_CC = _normalize(multi_scale_noise(shape, [3, 8, 20], [0.50, 0.32, 0.18], int(seed) + 9765))
    cx_d = np.mod(xr + np.sin(yr * 0.020 + seed) * 1.4, fine_cell) - fine_cell * 0.5
    cy_d = np.mod(yr + np.sin(xr * 0.018 - seed) * 1.2, fine_cell) - fine_cell * 0.5
    dist = np.sqrt(cx_d * cx_d + cy_d * cy_d)
    target_r = fine_cell * (0.10 + dot_max * 0.55 * tone_M)
    dot = np.clip(1.0 - (dist - target_r) / max(0.55, fine_cell * 0.07), 0, 1)

    # 1) Paper substrate with INDEPENDENT M/R/CC
    paper = _normalize(multi_scale_noise(shape, [1.0, 3.0], [0.6, 0.4], int(seed) + 9762))
    M = (0.30 + dot * 0.55 + (paper - 0.5) * 0.08).astype(np.float32)
    R = (0.55 - dot * 0.30 + (tone_R - 0.5) * 0.18).astype(np.float32)
    CC = (0.40 + dot * 0.25 + (tone_CC - 0.5) * 0.18).astype(np.float32)

    # 2) Cross-rosette — TIGHTER rosette frequencies (fine_cell now smaller)
    rosette = np.maximum(
        _spb_fast_line_distance(xr + yr * 0.18, fine_cell * 1.8, 0.45, seed),
        _spb_fast_line_distance(xr - yr * 0.22, fine_cell * 2.4, 0.40, seed * 0.31),
    )
    M = np.clip(M + rosette * 0.12, 0, 1)
    CC = np.clip(CC + rosette * 0.10, 0, 1)

    if _CV2_OK:
        # 3) HERO-A — OFFSET CMY plate REGISTRATION DOTS (three rotated halftone grids)
        plate_palette = [
            (0.75, 0.18, 0.20),  # Cyan-ish: high M, low R, low CC
            (0.55, 0.62, 0.55),  # Magenta-ish
            (0.45, 0.25, 0.18),  # Yellow-ish
        ]
        for plate_idx, (pm, pr, pc) in enumerate(plate_palette):
            plate_ang = angle + float(rng.uniform(-0.5, 0.5))
            xrp = xx * np.cos(plate_ang) - yy * np.sin(plate_ang)
            yrp = xx * np.sin(plate_ang) + yy * np.cos(plate_ang)
            plate_cell = fine_cell * float(rng.uniform(0.95, 1.15))
            # subpixel offset = misregistration
            shift_x = float(rng.uniform(-1.8, 1.8))
            shift_y = float(rng.uniform(-1.8, 1.8))
            cx_p = np.mod(xrp + shift_x, plate_cell) - plate_cell * 0.5
            cy_p = np.mod(yrp + shift_y, plate_cell) - plate_cell * 0.5
            d_p = np.sqrt(cx_p * cx_p + cy_p * cy_p)
            tgt = plate_cell * 0.25
            plate_dot = np.clip(1.0 - (d_p - tgt) / 0.6, 0, 1).astype(np.float32)
            # blend each plate's chroma into the field
            wgt = float(rng.uniform(0.10, 0.22))
            M = np.clip(M * (1 - plate_dot * wgt) + pm * plate_dot * wgt, 0, 1)
            R = np.clip(R * (1 - plate_dot * wgt) + pr * plate_dot * wgt, 0, 1)
            CC = np.clip(CC * (1 - plate_dot * wgt) + pc * plate_dot * wgt, 0, 1)

        # 4) HERO-B — STAR-BURST 'POW!' BANGS (4-8 spiky 16-28 px starbursts)
        n_bang = int(rng.integers(4, 9))
        for _ in range(n_bang):
            bcx = int(rng.uniform(0.06, 0.94) * w)
            bcy = int(rng.uniform(0.06, 0.94) * h)
            n_spike = int(rng.integers(8, 14))
            r_in = float(rng.uniform(4.0, 7.0) * scale)
            r_out = float(rng.uniform(10.0, 16.0) * scale)
            bM = float(rng.uniform(0.55, 0.95))
            bR = float(rng.uniform(0.10, 0.35))
            bCC = float(rng.uniform(0.10, 0.78))
            pts = []
            for k in range(2 * n_spike):
                ang = k * (np.pi / n_spike)
                r_pt = r_out if (k % 2 == 0) else r_in
                pts.append([
                    int(np.clip(bcx + np.cos(ang) * r_pt, 0, w - 1)),
                    int(np.clip(bcy + np.sin(ang) * r_pt, 0, h - 1))
                ])
            pts_arr = np.array(pts, dtype=np.int32)
            _cv2.fillPoly(M, [pts_arr], bM, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [pts_arr], bR, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts_arr], bCC, lineType=_cv2.LINE_AA)
            # bright inner highlight
            _cv2.circle(M, (bcx, bcy), max(1, int(r_in * 0.5)), float(rng.uniform(0.75, 0.98)), -1, lineType=_cv2.LINE_AA)

        # 5) MICRO INK-BLOTS — 2-5 px, 3x density
        n_blot = int(np.clip(2700 * (min(h, w) / 2048.0) ** 2, 800, 7000))
        for _ in range(n_blot):
            cxi = int(rng.integers(0, w)); cyi = int(rng.integers(0, h))
            r = int(max(1, rng.uniform(2.0, 5.0) * scale * 0.5))
            _cv2.circle(M, (cxi, cyi), r, float(rng.uniform(0.55, 0.95)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cxi, cyi), r, float(rng.uniform(0.08, 0.40)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cxi, cyi), r, float(rng.uniform(0.06, 0.32)), -1, lineType=_cv2.LINE_AA)
        # 6) MISPRINT HAIRLINE DRAG — 2-5 px, 3x density
        n_dr = int(np.clip(1500 * (min(h, w) / 2048.0) ** 2, 500, 4000))
        for _ in range(n_dr):
            cxd = float(rng.uniform(2, w - 2)); cyd = float(rng.uniform(2, h - 2))
            length = float(rng.uniform(2.0, 5.0) * scale)
            ang = float(rng.uniform(0, 2 * np.pi))
            x0 = int(cxd - np.cos(ang) * length * 0.5); y0 = int(cyd - np.sin(ang) * length * 0.5)
            x1 = int(cxd + np.cos(ang) * length * 0.5); y1 = int(cyd + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0, y0), (x1, y1), float(rng.uniform(0.40, 0.85)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0, y0), (x1, y1), float(rng.uniform(0.18, 0.55)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.12, 0.50)), 1, lineType=_cv2.LINE_AA)

        # 7) REGISTRATION-CROSS MARKS — a handful of tiny 4-7 px cross marks
        n_reg = int(rng.integers(6, 12))
        for _ in range(n_reg):
            rcx = int(rng.uniform(0.04, 0.96) * w)
            rcy = int(rng.uniform(0.04, 0.96) * h)
            rL = max(2, int(float(rng.uniform(3.0, 6.0)) * scale))
            _cv2.line(M, (rcx - rL, rcy), (rcx + rL, rcy), 0.12, 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, (rcx, rcy - rL), (rcx, rcy + rL), 0.12, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (rcx - rL, rcy), (rcx + rL, rcy), 0.85, 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (rcx, rcy - rL), (rcx, rcy + rL), 0.85, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (rcx - rL, rcy), (rcx + rL, rcy), 0.70, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (rcx, rcy - rL), (rcx, rcy + rL), 0.70, 1, lineType=_cv2.LINE_AA)

    # 5) MISPRINT DUST FLECKS — denser, per-pixel INDEPENDENT uniforms
    n_f = max(2200, int(h * w / 1400))
    fy = rng.integers(0, h, n_f); fx = rng.integers(0, w, n_f)
    M[fy, fx] = rng.uniform(0.08, 0.32, n_f).astype(np.float32)
    R[fy, fx] = rng.uniform(0.55, 0.92, n_f).astype(np.float32)
    CC[fy, fx] = rng.uniform(0.40, 0.88, n_f).astype(np.float32)

    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
halftone_print._spb_concept_complete = True


# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------

ARTISTIC_PATTERNS = {
    'brushstroke_bold': brushstroke_bold,
    'crayon_wax_resist': crayon_wax_resist,
    'airbrush_gradient_bloom': airbrush_gradient_bloom,
    'spray_paint_drip': spray_paint_drip,
    'stippled_dots_fine': stippled_dots_fine,
    'halftone_print': halftone_print,
}

__all__ = [
    'ARTISTIC_PATTERNS',
    'brushstroke_bold',
    'crayon_wax_resist',
    'airbrush_gradient_bloom',
    'spray_paint_drip',
    'stippled_dots_fine',
    'halftone_print',
]

