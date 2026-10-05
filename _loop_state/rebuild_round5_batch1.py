"""Round-5 corrective rebuild — batch 1 (12 patterns).

Replaces 12 function bodies in engine/spec_patterns.py with corrective rewrites
addressing owner briefs (DENSITY 5-10x for 4 patterns, FEATURES TOO LARGE for 8).
"""
import re
import sys
import os

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
SRC = os.path.join(ROOT, "engine", "spec_patterns.py")

# ---- New bodies (everything from "def NAME(" through the trailing ._spb_concept_complete = True line) ----

NEW_BODIES = {}

NEW_BODIES["banded_rows"] = '''def banded_rows(shape, seed, sm, **kwargs):
    """banded_rows.

    identity: Tight 7-px brick-laid mosaic of pigment chips packed in dense
    9-px-tall horizontal courses — each tiny tile gets independent continuous
    M/R/CC so the canvas reads as thousands of fine colored shards rather
    than panel-scale bands. Per-row stagger and 1-px grout seams give the
    weave; hairline streaks (6-12 px) and pinpoint pigment specks crisp the
    detail.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 17311)
    yy = np.arange(h, dtype=np.float32)[:, np.newaxis]
    xx = np.arange(w, dtype=np.float32)[np.newaxis, :]
    scale = max(min(h, w) / 2048.0, 0.25)

    # 1) Substrate FBM
    weft = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.45, 0.32, 0.23], int(seed) + 11))

    # 2) FINE 7 x 9 px brick mosaic (was 22 x 18 — shrunk 2.5-3x)
    row_pitch = 9.0
    cell_pitch = 7.0
    row_idx = np.floor(yy / row_pitch).astype(np.int32)
    row_offset = np.mod(row_idx * 47, 100) / 100.0 * cell_pitch
    col_idx = np.floor((xx + row_offset) / cell_pitch).astype(np.int32)
    ch1 = np.mod(row_idx * 53 + col_idx * 89 + int(seed) * 13, 997).astype(np.float32) / 997.0
    ch2 = np.mod(row_idx * 71 + col_idx * 113 + int(seed) * 17, 991).astype(np.float32) / 991.0
    ch3 = np.mod(row_idx * 97 + col_idx * 131 + int(seed) * 19, 983).astype(np.float32) / 983.0
    ch4 = np.mod(row_idx * 109 + col_idx * 149 + int(seed) * 23, 977).astype(np.float32) / 977.0

    # 1-px grout
    cx_e = ((xx + row_offset) % cell_pitch) - cell_pitch * 0.5
    cy_e = (yy % row_pitch) - row_pitch * 0.5
    edge_d = np.maximum(np.abs(cx_e) - cell_pitch * 0.40, np.abs(cy_e) - row_pitch * 0.40)
    grout = np.clip(edge_d * 2.2 + 0.5, 0, 1)

    # 3) Per-cell INDEPENDENT continuous M/R/CC
    M = 0.18 + ch1 * 0.74
    R = 0.12 + ch2 * 0.68 + (weft - 0.5) * 0.14
    CC = 0.05 + ch3 * 0.62
    sub = (ch4 - 0.5) * 0.18
    M = M + sub
    R = R - sub * 0.6
    CC = CC + sub * 0.4

    M = M * (0.40 + grout * 0.60)
    R = np.clip(R + (1.0 - grout) * 0.24, 0, 1)
    CC = CC * grout + (1.0 - grout) * 0.82

    M = M.astype(np.float32); R = R.astype(np.float32); CC = CC.astype(np.float32)

    # 4) Short hairlines (6-12 px — was 10-26 px)
    if _CV2_OK:
        n_l = int(np.clip(900 * (min(h, w) / 2048.0) ** 2, 260, 2200))
        for _ in range(n_l):
            cx = float(rng.uniform(4, w - 4)); cy = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(6.0, 12.0) * scale)
            ang = float(rng.uniform(-0.22, 0.22))
            x0s = int(cx - np.cos(ang) * length * 0.5)
            y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5)
            y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.55, 0.96)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.08, 0.40)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.04, 0.32)), 1, lineType=_cv2.LINE_AA)

    # 5) Bright pigment specks (denser)
    n_fl = max(1400, int(h * w / 2800))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.65, 0.98, n_fl).astype(np.float32))
    R[fy, fx] = np.minimum(R[fy, fx], rng.uniform(0.06, 0.28, n_fl).astype(np.float32))
    CC[fy, fx] = np.minimum(CC[fy, fx], rng.uniform(0.03, 0.20, n_fl).astype(np.float32))

    # 6) Dark grout pits
    n_dk = max(900, int(h * w / 5500))
    ddy = rng.integers(0, h, n_dk); ddx = rng.integers(0, w, n_dk)
    M[ddy, ddx] = np.minimum(M[ddy, ddx], rng.uniform(0.06, 0.28, n_dk).astype(np.float32))
    R[ddy, ddx] = np.maximum(R[ddy, ddx], rng.uniform(0.58, 0.92, n_dk).astype(np.float32))

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
banded_rows._spb_concept_complete = True
'''

NEW_BODIES["depth_gradient"] = '''def depth_gradient(shape, seed, sm, direction='vertical', noise_strength=0.15, **kwargs):
    """depth_gradient.

    identity: A directional clearcoat depth pool, but the gradient is now
    cut by hundreds of fine 4-12 px micro-ribs, 3-9 px drip threads, and a
    storm of tiny 4-10 px pool-pinch specks. Per-feature INDEPENDENT M/R/CC
    so the gradient reads as a dense weave of fine flow detail rather than
    a smooth panel-scale falloff.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 5071)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) Directional gradient (the spine)
    if direction == 'radial':
        cy, cx = h / 2.0, w / 2.0
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        grad = np.sqrt(((yy - cy) / h) ** 2 + ((xx - cx) / w) ** 2)
        grad = np.clip(grad / max(grad.max(), 1e-6), 0, 1)
    else:
        grad = np.broadcast_to(np.linspace(0.0, 1.0, h, dtype=np.float32)[:, np.newaxis], shape).copy()

    cn = rng.uniform(-1, 1, size=w).astype(np.float32)
    ks = max(3, w // 50)
    cn = np.convolve(cn, np.ones(ks) / ks, mode='same')
    grad = np.clip(grad + cn[np.newaxis, :] * noise_strength, 0, 1)

    fbm_M = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.50, 0.32, 0.18], int(seed) + 511))
    fbm_R = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.50, 0.32, 0.18], int(seed) + 512))
    fbm_CC = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.50, 0.32, 0.18], int(seed) + 513))

    M = (0.30 + grad * 0.45 + (fbm_M - 0.5) * 0.22).astype(np.float32)
    R_ch = (0.65 - grad * 0.35 + (fbm_R - 0.5) * 0.22).astype(np.float32)
    CC = (0.20 + (1.0 - grad) * 0.55 + (fbm_CC - 0.5) * 0.20).astype(np.float32)

    if _CV2_OK:
        # 2) FINE 4-12 px ribs (was 10-28 px — shrunk 2.5x, count up 3x)
        n_ribs = int(np.clip(1400 * (mn / 2048.0) ** 2, 460, 3800))
        for _ in range(n_ribs):
            yb = int(rng.integers(2, h - 2))
            x0 = int(rng.uniform(0, w - 6))
            length = int(rng.uniform(4.0, 12.0) * scale)
            x1 = min(w - 1, x0 + length)
            _cv2.line(M, (x0, yb), (x1, yb), float(rng.uniform(0.10, 0.96)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (x0, yb), (x1, yb), float(rng.uniform(0.06, 0.92)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, yb), (x1, yb), float(rng.uniform(0.06, 0.95)), 1, lineType=_cv2.LINE_AA)

        # 3) FINE 3-9 px drip threads (was 8-24)
        n_drips = int(np.clip(1000 * (mn / 2048.0) ** 2, 320, 2600))
        for _ in range(n_drips):
            cx_d = int(rng.integers(2, w - 2))
            cy_d = int(rng.uniform(0, h - 10))
            length = int(rng.uniform(3.0, 9.0) * scale)
            _cv2.line(M, (cx_d, cy_d), (cx_d, min(h - 1, cy_d + length)),
                      float(rng.uniform(0.08, 0.86)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx_d, cy_d), (cx_d, min(h - 1, cy_d + length)),
                      float(rng.uniform(0.06, 0.90)), 1, lineType=_cv2.LINE_AA)

        # 4) FINE 4-10 px pinch specks (denser)
        n_specks = int(np.clip(2400 * (mn / 2048.0) ** 2, 800, 7000))
        for _ in range(n_specks):
            cx_s = int(rng.integers(0, w)); cy_s = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(2.0, 5.0) * scale * 0.5))
            _cv2.circle(M, (cx_s, cy_s), r, float(rng.uniform(0.55, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx_s, cy_s), r, float(rng.uniform(0.08, 0.36)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx_s, cy_s), r, float(rng.uniform(0.06, 0.30)), -1, lineType=_cv2.LINE_AA)

    # 5) Pinpoint flecks
    n_fl = int(np.clip(2000 * (mn / 2048.0) ** 2, 700, 5500))
    fx = rng.integers(0, w, n_fl); fy = rng.integers(0, h, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.55, 0.95, n_fl).astype(np.float32))
    CC[fy, fx] = np.minimum(CC[fy, fx], rng.uniform(0.06, 0.30, n_fl).astype(np.float32))

    out = np.stack([M, R_ch, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
depth_gradient._spb_concept_complete = True
'''

NEW_BODIES["spiral_sweep"] = '''def spiral_sweep(shape, seed, sm, num_arms=4, tightness=3.0, fade=0.3):
    """spiral_sweep.

    identity: A polished panel covered by a TIGHT 12-arm logarithmic spiral
    plus a 20-arm finer overlay (arm pitch shrunk 2.5x — was 4/8/3 arms).
    Per-arm INDEPENDENT M/R/CC. Dense field of 2-5 px crest dots, 3-9 px
    orbital arc hairlines (was 8-22), and 1-3 px dark debris dots. Reads as
    fine-grained orbital polish, not panel-scale sweeps.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 1455)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) Substrate with TIGHT spiral arms (log scale 32->96 = 3x tighter)
    cx0 = 0.5 + float(rng.uniform(-0.06, 0.06))
    cy0 = 0.5 + float(rng.uniform(-0.06, 0.06))
    yy = (np.arange(h, dtype=np.float32) / h - cy0)[:, None]
    xx = (np.arange(w, dtype=np.float32) / w - cx0)[None, :]
    theta = np.arctan2(yy, xx)
    rr = np.sqrt(yy * yy + xx * xx) + 1e-6
    arms_main = np.sin(theta * 12.0 - np.log(rr + 0.01) * 36.0 + float(rng.uniform(0, 2 * np.pi))) * 0.5 + 0.5
    arms_fine = np.sin(theta * 20.0 - np.log(rr + 0.01) * 64.0 + float(rng.uniform(0, 2 * np.pi))) * 0.5 + 0.5
    arms_counter = np.sin(-theta * 9.0 - np.log(rr + 0.01) * 28.0 + float(rng.uniform(0, 2 * np.pi))) * 0.5 + 0.5
    arms_field = (arms_main * 0.50 + arms_fine * 0.35 + arms_counter * 0.15).astype(np.float32)
    fbm_M = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.5, 0.3, 0.2], int(seed) + 4101))
    fbm_R = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.5, 0.3, 0.2], int(seed) + 4102))
    fbm_CC = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.5, 0.3, 0.2], int(seed) + 4103))

    M = (0.40 + (arms_field - 0.5) * 0.34 + (fbm_M - 0.5) * 0.14).astype(np.float32)
    R = (0.42 - (arms_field - 0.5) * 0.22 + (fbm_R - 0.5) * 0.12).astype(np.float32)
    CC = (0.32 + (arms_field - 0.5) * 0.26 + (1.0 - fbm_CC) * 0.10).astype(np.float32)

    if _CV2_OK:
        # 2) Dense crest dots (2-5 px) — denser
        n_crest = int(np.clip(4400 * (mn / 2048.0) ** 2, 1400, 10000))
        for _ in range(n_crest):
            cx_s = int(rng.integers(0, w)); cy_s = int(rng.integers(0, h))
            if arms_field[cy_s, cx_s] < 0.62:
                continue
            r_s = max(1, int(float(rng.uniform(1.0, 2.5)) * scale))
            _cv2.circle(M, (cx_s, cy_s), r_s, float(rng.uniform(0.62, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx_s, cy_s), r_s, float(rng.uniform(0.06, 0.28)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx_s, cy_s), r_s, float(rng.uniform(0.08, 0.50)), -1, lineType=_cv2.LINE_AA)

        # 3) SHORT orbital arc hairlines 3-9 px (was 8-22)
        n_arc = int(np.clip(1800 * (mn / 2048.0) ** 2, 600, 4400))
        for _ in range(n_arc):
            ax = float(rng.uniform(4, w - 4)); ay = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(3.0, 9.0)) * scale
            tx = ax / w - cx0; ty = ay / h - cy0
            ang = float(np.arctan2(ty, tx)) + np.pi * 0.5
            x0s = int(ax - np.cos(ang) * length * 0.5); y0s = int(ay - np.sin(ang) * length * 0.5)
            x1s = int(ax + np.cos(ang) * length * 0.5); y1s = int(ay + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.30, 0.90)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.10, 0.42)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.10, 0.65)), 1, lineType=_cv2.LINE_AA)

        # 4) Dark orbital debris 1-3 px
        n_dust = int(np.clip(1800 * (mn / 2048.0) ** 2, 600, 4400))
        for _ in range(n_dust):
            cx_s = int(rng.integers(0, w)); cy_s = int(rng.integers(0, h))
            r_s = max(1, int(float(rng.uniform(1.0, 2.0)) * scale))
            _cv2.circle(M, (cx_s, cy_s), r_s, float(rng.uniform(0.08, 0.28)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx_s, cy_s), r_s, float(rng.uniform(0.55, 0.92)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx_s, cy_s), r_s, float(rng.uniform(0.55, 0.92)), -1, lineType=_cv2.LINE_AA)

    # 5) Pinpoint speckles
    n_fl = int(np.clip(2400 * (mn / 2048.0) ** 2, 800, 6000))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.55, 0.96, n_fl).astype(np.float32))
    R[fy, fx] = np.minimum(R[fy, fx], rng.uniform(0.05, 0.28, n_fl).astype(np.float32))
    CC[fy, fx] = np.maximum(CC[fy, fx], rng.uniform(0.10, 0.82, n_fl).astype(np.float32))

    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
spiral_sweep._spb_concept_complete = True
'''

NEW_BODIES["wave_ripple"] = '''def wave_ripple(shape, seed, sm, num_waves=5, base_freq=6.0, choppy=0.3):
    """wave_ripple.

    identity: A water surface caught mid-ripple with TIGHT 6-14 px-period
    interference waves (was 16-30 px — shrunk ~2.5x), 18 wave layers
    instead of 12, a dense field of 2-5 px crest arcs and 1-3 px droplet
    pinpoints. Per-feature INDEPENDENT M/R/CC for chroma diversity. Reads
    as fine glassy chop, not panel-scale rollers.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 22091)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    fM = _normalize(multi_scale_noise(shape, [1.5, 4.0, 11.0, 24.0], [0.35, 0.30, 0.22, 0.13], int(seed) + 5001))
    fR = _normalize(multi_scale_noise(shape, [1.5, 4.0, 11.0, 24.0], [0.36, 0.28, 0.21, 0.15], int(seed) + 5002))
    fCC = _normalize(multi_scale_noise(shape, [1.5, 4.0, 11.0, 24.0], [0.34, 0.31, 0.23, 0.12], int(seed) + 5003))
    M  = 0.45 + (fM - 0.5) * 0.30
    R_ch = 0.55 + (fR - 0.5) * 0.30
    CC = 0.35 + (fCC - 0.5) * 0.30

    # FINE interference waves (6-14 px period — was 16-30)
    yy_n = np.arange(h, dtype=np.float32) / max(mn, 1)
    xx_n = np.arange(w, dtype=np.float32) / max(mn, 1)
    wave_field = np.zeros(shape, dtype=np.float32)
    n_waves = 18
    for _ in range(n_waves):
        angle = rng.uniform(0, np.pi)
        target_period_px = rng.uniform(6.0, 14.0) * scale
        cycles = mn / max(target_period_px, 1.0)
        phase = rng.uniform(0, 2 * np.pi)
        amp = rng.uniform(0.08, 0.22)
        proj = yy_n[:, None] * np.cos(angle) + xx_n[None, :] * np.sin(angle)
        wave = np.sin(proj * cycles * 2 * np.pi + phase)
        if choppy > 0:
            wave = np.sign(wave) * np.abs(wave) ** max(0.3, 1 - choppy * 0.5)
        wave_field += wave * amp
    wave_field = wave_field / max(1.0, n_waves * 0.18)
    R_ch = R_ch + wave_field * 0.24
    CC = CC - wave_field * 0.16
    M = M + wave_field * 0.12

    if _CV2_OK:
        # FINE crest arcs (radius 2-5 px)
        n_crests = int(np.clip(1800 * (mn / 2048.0) ** 2, 600, 4600))
        for _ in range(n_crests):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(1, int(rng.uniform(2.0, 5.0) * scale))
            a0 = float(rng.uniform(0, 360)); a1 = a0 + float(rng.uniform(50, 130))
            _cv2.ellipse(M,    (cx, cy), (r, r), 0, a0, a1, float(rng.uniform(0.30, 0.94)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R_ch, (cx, cy), (r, r), 0, a0, a1, float(rng.uniform(0.08, 0.55)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC,   (cx, cy), (r, r), 0, a0, a1, float(rng.uniform(0.06, 0.42)), 1, lineType=_cv2.LINE_AA)

        # Droplet pinpoints 1-3 px
        n_drops = int(np.clip(1400 * (mn / 2048.0) ** 2, 480, 3600))
        for _ in range(n_drops):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(1, int(rng.uniform(1.0, 2.5) * scale))
            _cv2.circle(M,    (cx, cy), r, float(rng.uniform(0.55, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(rng.uniform(0.06, 0.28)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC,   (cx, cy), r, float(rng.uniform(0.04, 0.24)), -1, lineType=_cv2.LINE_AA)

    n_fl = int(np.clip(2200 * (mn / 2048.0) ** 2, 700, 5800))
    fx = rng.integers(0, w, n_fl); fy = rng.integers(0, h, n_fl)
    M[fy, fx]    = np.maximum(M[fy, fx],    rng.uniform(0.45, 0.96, n_fl).astype(np.float32))
    R_ch[fy, fx] = np.minimum(R_ch[fy, fx], rng.uniform(0.05, 0.32, n_fl).astype(np.float32))
    CC[fy, fx]   = np.minimum(CC[fy, fx],   rng.uniform(0.05, 0.28, n_fl).astype(np.float32))

    out = np.stack([M, R_ch, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
wave_ripple._spb_concept_complete = True
'''

NEW_BODIES["metallic_sand"] = '''def metallic_sand(shape, seed, sm, block_size=2, flow_angle=0.18):
    """metallic_sand.

    identity: A SATURATED metallic sand bed — every square inch carries
    fine grain. Five stacked tiers: extreme-dense 1-px speckle (4-6x the
    prior count), 1-2 px micro-discs, 2-3 px medium grain, fine 3-5 px
    accent clusters, plus dense 4-7 px flow streaks along the drift axis.
    Per-feature INDEPENDENT continuous M/R/CC. No empty substrate.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 9217)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    def _fbm(off, sigma):
        if _CV2_OK:
            sh = max(64, h // 10); sw = max(64, w // 10)
            n = np.random.default_rng(int(seed) + off).random((sh, sw)).astype(np.float32)
            b = _cv2.GaussianBlur(n, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return _normalize(_cv2.resize(b, (w, h), interpolation=_cv2.INTER_CUBIC).astype(np.float32))
        return _normalize(multi_scale_noise(shape, [20, 40], [0.6, 0.4], int(seed) + off))

    fM = _fbm(1501, 7.0); fR = _fbm(1503, 7.0); fCC = _fbm(1505, 7.0)
    M  = (0.42 + (fM  - 0.5) * 0.26).astype(np.float32)
    R  = (0.42 + (fR  - 0.5) * 0.22).astype(np.float32)
    CC = (0.40 + (fCC - 0.5) * 0.24).astype(np.float32)

    if _CV2_OK:
        # Tier 1: ULTRA-DENSE 1 px (5x prior — was h*w/60)
        n1 = max(int(h * w / 12), 90000)
        ys = rng.integers(0, h, n1); xs = rng.integers(0, w, n1)
        M[ys, xs]  = np.maximum(M[ys, xs],  rng.uniform(0.55, 0.96, n1).astype(np.float32))
        R[ys, xs]  = np.minimum(R[ys, xs],  rng.uniform(0.08, 0.40, n1).astype(np.float32))
        CC[ys, xs] = np.maximum(CC[ys, xs], rng.uniform(0.45, 0.94, n1).astype(np.float32))

        # Tier 2: 1-2 px micro-discs (4x prior)
        n2 = max(int(h * w / 200), 7000)
        for _ in range(n2):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(1, 2) * scale))
            _cv2.circle(M,  (cx, cy), rr, float(rng.uniform(0.62, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R,  (cx, cy), rr, float(rng.uniform(0.05, 0.25)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.55, 0.92)), -1, lineType=_cv2.LINE_AA)

        # Tier 3: 2-3 px medium grain (3x prior)
        n3 = max(int(h * w / 700), 2400)
        for _ in range(n3):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(1, int(rng.uniform(2, 3) * scale))
            _cv2.circle(M,  (cx, cy), rr, float(rng.uniform(0.55, 0.92)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R,  (cx, cy), rr, float(rng.uniform(0.10, 0.35)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rr, float(rng.uniform(0.45, 0.85)), -1, lineType=_cv2.LINE_AA)

        # Tier 4: Flow streaks 4-7 px along drift (3x prior count, finer)
        ang = float(flow_angle) * np.pi + float(rng.uniform(-0.05, 0.05))
        n_st = max(int(h * w / 450), 1200)
        for _ in range(n_st):
            x0 = int(rng.integers(0, w)); y0 = int(rng.integers(0, h))
            ll = int(rng.uniform(4, 7) * scale)
            x1 = int(x0 + np.cos(ang) * ll); y1 = int(y0 + np.sin(ang) * ll)
            _cv2.line(M,  (x0, y0), (x1, y1), float(rng.uniform(0.62, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R,  (x0, y0), (x1, y1), float(rng.uniform(0.08, 0.30)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.45, 0.88)), 1, lineType=_cv2.LINE_AA)

        # Tier 5: bright accent clusters 3-5 px (3x prior)
        n_c = max(int(h * w / 1400), 460)
        for _ in range(n_c):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            rr = max(2, int(rng.uniform(2, 4) * scale))
            _cv2.circle(M, (cx, cy), rr, float(rng.uniform(0.80, 0.99)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), rr, float(rng.uniform(0.04, 0.15)), -1, lineType=_cv2.LINE_AA)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
metallic_sand._spb_concept_complete = True
'''

NEW_BODIES["gold_flake"] = '''def gold_flake(shape, seed, sm, density1=0.35, density2=0.3):
    """gold_flake.

    identity: A SATURATED gold-leaf field — five stacked tiers: 1-2 px
    micro-shimmer dust, 2-4 px fine fragments, 4-8 px primary foil chips,
    8-14 px irregular leaf shards, plus 6-12 px torn hairlines. Counts
    tripled vs prior pass (foil chips 2400 -> 7800). Per-feature
    INDEPENDENT continuous M/R/CC. No bare substrate, no confetti gaps.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 31151)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) Gold-leaning substrate
    base = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.45, 0.35, 0.20], int(seed) + 11))
    M = (0.55 + (base - 0.5) * 0.28).astype(np.float32)
    R = (0.42 + (1.0 - base) * 0.22).astype(np.float32)
    CC = (0.38 + (base - 0.5) * 0.16).astype(np.float32)

    if _CV2_OK:
        # 2) Tier A — irregular leaf shards 8-14 px (was 6-18, slightly tighter, 1.6x count)
        n_shard = int(np.clip(3800 * (mn / 2048.0) ** 2, 1200, 9000))
        for _ in range(n_shard):
            cx = int(rng.uniform(2, w - 2)); cy = int(rng.uniform(2, h - 2))
            fw = int(max(3, rng.uniform(8.0, 14.0) * scale))
            fh = int(max(3, rng.uniform(8.0, 14.0) * scale))
            ang = float(rng.uniform(0, 180))
            box = ((cx, cy), (fw, fh), ang)
            pts = _cv2.boxPoints(box).astype(np.int32)
            _cv2.fillConvexPoly(M, pts, float(rng.uniform(0.70, 0.98)), lineType=_cv2.LINE_AA)
            _cv2.fillConvexPoly(R, pts, float(rng.uniform(0.06, 0.40)), lineType=_cv2.LINE_AA)
            _cv2.fillConvexPoly(CC, pts, float(rng.uniform(0.04, 0.32)), lineType=_cv2.LINE_AA)

        # 3) Tier B — primary 4-8 px foil chips (3x prior count, smaller)
        n_chip = int(np.clip(7800 * (mn / 2048.0) ** 2, 2400, 18000))
        for _ in range(n_chip):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = int(max(2, rng.uniform(2.0, 4.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.65, 0.97)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.06, 0.36)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.04, 0.30)), -1, lineType=_cv2.LINE_AA)

        # 4) Tier C — fine 2-4 px fragments (4x prior count)
        n_frag = int(np.clip(9000 * (mn / 2048.0) ** 2, 2800, 22000))
        for _ in range(n_frag):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1.0, 2.5) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.55, 0.94)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.10, 0.45)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.06, 0.36)), -1, lineType=_cv2.LINE_AA)

        # 5) Tier D — short torn hairlines 6-12 px (was 8-18)
        n_l = int(np.clip(2400 * (mn / 2048.0) ** 2, 800, 5500))
        for _ in range(n_l):
            cx = float(rng.uniform(4, w - 4)); cy = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(6.0, 12.0) * scale)
            ang = float(rng.uniform(0, 2 * np.pi))
            x0 = int(cx - np.cos(ang) * length * 0.5); y0 = int(cy - np.sin(ang) * length * 0.5)
            x1 = int(cx + np.cos(ang) * length * 0.5); y1 = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0, y0), (x1, y1), float(rng.uniform(0.30, 0.70)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0, y0), (x1, y1), float(rng.uniform(0.35, 0.78)), 1, lineType=_cv2.LINE_AA)

    # 6) Tier E — ULTRA-DENSE pinpoint micro-shimmer dust
    n_dust = max(6000, int(h * w / 35))
    fy = rng.integers(0, h, n_dust); fx = rng.integers(0, w, n_dust)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.62, 0.98, n_dust).astype(np.float32))
    R[fy, fx] = np.minimum(R[fy, fx], rng.uniform(0.06, 0.28, n_dust).astype(np.float32))
    CC[fy, fx] = np.minimum(CC[fy, fx], rng.uniform(0.04, 0.22, n_dust).astype(np.float32))

    # 7) Substrate micro-pits
    n_pit = max(1500, int(h * w / 4000))
    py = rng.integers(0, h, n_pit); px = rng.integers(0, w, n_pit)
    M[py, px] = np.minimum(M[py, px], rng.uniform(0.08, 0.30, n_pit).astype(np.float32))
    R[py, px] = np.maximum(R[py, px], rng.uniform(0.55, 0.92, n_pit).astype(np.float32))

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
gold_flake._spb_concept_complete = True
'''

NEW_BODIES["chevron_bands"] = '''def chevron_bands(shape, seed, sm, num_bands=20, v_angle=0.6, palette_size=8):
    """chevron_bands.

    identity: A TIGHT chevron field — band pitch shrunk 2.5x (was h/34 ->
    h/14) so the panel reads as many fine V-stripes, not panel-scale
    arrowheads. Per-band INDEPENDENT M/R/CC continuous uniforms. Short
    apex crosshatches (4-10 px, was 8-18) and tighter nested hairlines
    (4-12 px, was 8-22). Dense pin specks at band centerlines.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 54311)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx = w * (0.50 + rng.uniform(-0.06, 0.06))
    effective_bands = max(int(num_bands) * 3, int(mn / 14.0))  # 2.5x tighter
    pitch = max(5.0, h / max(effective_bands, 1))
    warp = _normalize(multi_scale_noise(shape, [3.0, 9.0, 22.0], [0.34, 0.36, 0.30], int(seed) + 271))
    coord = yy + np.abs(xx - cx) * (v_angle * float(rng.uniform(0.85, 1.15))) + (warp - 0.5) * pitch * 0.6
    band_idx = np.floor(coord / pitch).astype(np.int32)
    frac = (coord / pitch) - band_idx
    stripe = 1.0 - np.abs(frac - 0.5) * 2.0
    ridge = np.clip((stripe - 0.55) / 0.45, 0, 1).astype(np.float32)
    pin = np.exp(-((frac - 0.5) ** 2) / 0.0016).astype(np.float32)

    n_bands = int(band_idx.max() - band_idx.min() + 2)
    band_M = rng.uniform(0.15, 0.95, n_bands).astype(np.float32)
    band_R = rng.uniform(0.06, 0.82, n_bands).astype(np.float32)
    band_CC = rng.uniform(0.04, 0.80, n_bands).astype(np.float32)
    bi = (band_idx - band_idx.min()).astype(np.int32)
    M = (band_M[bi] * (0.55 + ridge * 0.45) + pin * 0.18).astype(np.float32)
    R = (band_R[bi] * (1.0 - ridge * 0.30) + (warp - 0.5) * 0.14).astype(np.float32)
    CC = (band_CC[bi] * (1.0 - ridge * 0.25) + (warp - 0.5) * 0.14).astype(np.float32)
    np.clip(M, 0, 1, out=M); np.clip(R, 0, 1, out=R); np.clip(CC, 0, 1, out=CC)

    if _CV2_OK:
        # Apex crosshatch 4-10 px (was 8-18)
        n_cross = int(np.clip(1400 * (mn / 2048.0) ** 2, 460, 3500))
        for _ in range(n_cross):
            cxh = rng.uniform(max(8, cx - 50 * scale), min(w - 8, cx + 50 * scale))
            cyh = rng.uniform(4, h - 4)
            length = float(rng.uniform(4.0, 10.0) * scale)
            ang = float(rng.uniform(-np.pi, np.pi))
            x0 = int(cxh - np.cos(ang) * length * 0.5); y0 = int(cyh - np.sin(ang) * length * 0.5)
            x1 = int(cxh + np.cos(ang) * length * 0.5); y1 = int(cyh + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0, y0), (x1, y1), float(rng.uniform(0.30, 0.88)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0, y0), (x1, y1), float(rng.uniform(0.10, 0.65)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.06, 0.55)), 1, lineType=_cv2.LINE_AA)

        # Nested hairlines 4-12 px (was 8-22)
        n_hair = int(np.clip(1800 * (mn / 2048.0) ** 2, 600, 4200))
        for _ in range(n_hair):
            cxh = rng.uniform(4, w - 4); cyh = rng.uniform(4, h - 4)
            length = float(rng.uniform(4.0, 12.0) * scale)
            sign = 1.0 if cxh > cx else -1.0
            ang = float(np.arctan2(-1.0, sign * v_angle))
            x0 = int(cxh - np.cos(ang) * length * 0.5); y0 = int(cyh - np.sin(ang) * length * 0.5)
            x1 = int(cxh + np.cos(ang) * length * 0.5); y1 = int(cyh + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0, y0), (x1, y1), float(rng.uniform(0.22, 0.82)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0, y0), (x1, y1), float(rng.uniform(0.18, 0.78)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.18, 0.70)), 1, lineType=_cv2.LINE_AA)

        # Pin specks
        n_pin = int(np.clip(1000 * (mn / 2048.0) ** 2, 320, 2400))
        for _ in range(n_pin):
            cxh = int(rng.integers(0, w)); cyh = int(rng.integers(0, h))
            r = int(max(1, rng.uniform(1.5, 3.0) * scale * 0.5))
            _cv2.circle(M, (cxh, cyh), r, float(rng.uniform(0.55, 0.94)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cxh, cyh), r, float(rng.uniform(0.06, 0.28)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cxh, cyh), r, float(rng.uniform(0.04, 0.28)), -1, lineType=_cv2.LINE_AA)

    n_flecks = int(np.clip(2200 * (mn / 2048.0) ** 2, 700, 5500))
    fx = rng.integers(0, w, n_flecks); fy = rng.integers(0, h, n_flecks)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(0.10, 0.40, n_flecks).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] - rng.uniform(0.10, 0.35, n_flecks).astype(np.float32), 0, 1)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
chevron_bands._spb_concept_complete = True
'''

NEW_BODIES["wave_bands"] = '''def wave_bands(shape, seed, sm, num_bands=18, wave_freq=5.0, wave_amp=0.025,
               palette_size=8):
    """wave_bands.

    identity: A finely woven flow field of TWENTY wavy ribbons (was 8 —
    shrunk 2.5x to land in 4-12 px band width). Each ribbon carries its
    own continuous M/R/CC. Wave-positioned dabs shrunk to 4-10 px (was
    10-22), denser hairlines (4-10 px, was 10-22). Reads as a fine
    laminar weave, not panel-scale ribbons.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng2 = np.random.default_rng(int(seed) + 73111)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    fM = _normalize(multi_scale_noise(shape, [3.0, 7.0, 14.0, 22.0], [0.36, 0.30, 0.22, 0.14], int(seed) + 6222))
    fR = _normalize(multi_scale_noise(shape, [3.0, 7.0, 14.0, 22.0], [0.32, 0.32, 0.22, 0.14], int(seed) + 6223))
    fCC = _normalize(multi_scale_noise(shape, [3.0, 7.0, 14.0, 22.0], [0.30, 0.28, 0.26, 0.16], int(seed) + 6224))
    M  = 0.35 + (fM - 0.5) * 0.22
    R_ch = 0.60 + (fR - 0.5) * 0.22
    CC = 0.45 + (fCC - 0.5) * 0.22

    n_bands = 20  # was 8 — 2.5x denser ribbons
    wave_phase = [float(rng2.uniform(0, 2 * np.pi)) for _ in range(n_bands)]
    band_M = rng2.uniform(0.20, 0.95, n_bands).astype(np.float32)
    band_R = rng2.uniform(0.06, 0.60, n_bands).astype(np.float32)
    band_CC = rng2.uniform(0.06, 0.50, n_bands).astype(np.float32)

    def _wave_y_at_x(x_px, bi):
        xn = x_px / max(w - 1, 1)
        flow = (np.sin(xn * wave_freq * np.pi * 2.0 + wave_phase[bi]) * 0.03 * h
                + np.sin(xn * wave_freq * 5.4 + wave_phase[bi] * 1.3) * 0.010 * h)
        return ((bi + 0.5) / n_bands) * h + flow

    if _CV2_OK:
        # FINE 4-10 px dabs (was 10-22)
        n_dab = int(np.clip(1600 * (mn / 2048.0) ** 2, 500, 4000))
        for _ in range(n_dab):
            bi = int(rng2.integers(0, n_bands))
            x = int(rng2.integers(0, w))
            y = int(np.clip(_wave_y_at_x(x, bi) + rng2.normal(0, 4 * scale), 4, h - 4))
            r = int(max(2, rng2.uniform(4, 10) * scale * 0.5))
            mv  = float(np.clip(band_M[bi]  + rng2.uniform(-0.10, 0.10), 0.05, 0.98))
            rv  = float(np.clip(band_R[bi]  + rng2.uniform(-0.08, 0.08), 0.05, 0.95))
            ccv = float(np.clip(band_CC[bi] + rng2.uniform(-0.08, 0.08), 0.04, 0.90))
            _cv2.circle(M,    (x, y), r, mv,  -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (x, y), r, rv,  -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC,   (x, y), r, ccv, -1, lineType=_cv2.LINE_AA)

        # Edge dots 2-6 px (was 4-10)
        n_dot = int(np.clip(1200 * (mn / 2048.0) ** 2, 380, 2800))
        for _ in range(n_dot):
            cxv = int(rng2.integers(0, w)); cyv = int(rng2.integers(0, h))
            r = int(max(1, rng2.uniform(2, 6) * scale * 0.5))
            _cv2.circle(M,    (cxv, cyv), r, float(rng2.uniform(0.55, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cxv, cyv), r, float(rng2.uniform(0.06, 0.28)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC,   (cxv, cyv), r, float(rng2.uniform(0.04, 0.26)), -1, lineType=_cv2.LINE_AA)

        # Inner hairlines 4-10 px (was 10-22)
        n_hair = int(np.clip(1100 * (mn / 2048.0) ** 2, 360, 2600))
        for _ in range(n_hair):
            cxv = rng2.uniform(4, w - 4); cyv = rng2.uniform(4, h - 4)
            length = float(rng2.uniform(4.0, 10.0) * scale)
            ang = float(rng2.uniform(-0.12, 0.12))
            x0 = int(cxv - np.cos(ang) * length * 0.5); y0 = int(cyv - np.sin(ang) * length * 0.5)
            x1 = int(cxv + np.cos(ang) * length * 0.5); y1 = int(cyv + np.sin(ang) * length * 0.5)
            _cv2.line(M,    (x0, y0), (x1, y1), float(rng2.uniform(0.32, 0.86)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (x0, y0), (x1, y1), float(rng2.uniform(0.06, 0.40)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC,   (x0, y0), (x1, y1), float(rng2.uniform(0.04, 0.32)), 1, lineType=_cv2.LINE_AA)

    n_flecks = int(np.clip(2400 * (mn / 2048.0) ** 2, 800, 6000))
    fx = rng2.integers(0, w, n_flecks); fy = rng2.integers(0, h, n_flecks)
    M[fy, fx]    = np.maximum(M[fy, fx],    rng2.uniform(0.45, 0.96, n_flecks).astype(np.float32))
    R_ch[fy, fx] = np.minimum(R_ch[fy, fx], rng2.uniform(0.06, 0.28, n_flecks).astype(np.float32))
    CC[fy, fx]   = np.minimum(CC[fy, fx],   rng2.uniform(0.04, 0.22, n_flecks).astype(np.float32))

    out = np.stack([M, R_ch, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
wave_bands._spb_concept_complete = True
'''

NEW_BODIES["gradient_bands"] = '''def gradient_bands(shape, seed, sm, num_bands=16, palette_size=6):
    """gradient_bands.

    identity: A vertical falloff broken into MANY tiny shimmer ribbons —
    each ribbon now 4-10 px (was 10-22), 2.5x denser, with per-ribbon
    INDEPENDENT continuous M/R/CC. High-frequency band phase (num_bands x4)
    so the gradient reads as a fine pinstripe field of fine detail rather
    than a smooth panel sweep.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 11277)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) HIGH-FREQ banded gradient — num_bands x 4 so bands are panel-scale-small
    yn = (np.arange(h, dtype=np.float32) / max(h - 1, 1)).reshape(h, 1)
    band_phase = (np.sin(yn * num_bands * 4.0 * np.pi) * 0.5 + 0.5)
    grain = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.45, 0.35, 0.20], int(seed) + 632))
    M = (0.40 + band_phase * 0.30 + (grain - 0.5) * 0.10).astype(np.float32)
    R = (0.55 - band_phase * 0.18 + (1.0 - grain) * 0.10).astype(np.float32)
    CC = (0.45 + (1.0 - band_phase) * 0.20 + (grain - 0.5) * 0.08).astype(np.float32)
    M = np.broadcast_to(M, (h, w)).copy()
    R = np.broadcast_to(R, (h, w)).copy()
    CC = np.broadcast_to(CC, (h, w)).copy()

    if _CV2_OK:
        # 2) FINE shimmer ribbons 4-10 px (was 10-22)
        n_rib = int(np.clip(4500 * (mn / 2048.0) ** 2, 1400, 11000))
        for _ in range(n_rib):
            cxv = float(rng.uniform(4, w - 4)); cyv = float(rng.uniform(2, h - 2))
            length = float(rng.uniform(4.0, 10.0) * scale)
            ang = float(rng.uniform(-0.10, 0.10))
            x0 = int(cxv - np.cos(ang) * length * 0.5); y0 = int(cyv - np.sin(ang) * length * 0.5)
            x1 = int(cxv + np.cos(ang) * length * 0.5); y1 = int(cyv + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0, y0), (x1, y1), float(rng.uniform(0.28, 0.96)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0, y0), (x1, y1), float(rng.uniform(0.08, 0.65)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.06, 0.55)), 1, lineType=_cv2.LINE_AA)

        # 3) Cross-strands 3-7 px (was 5-12)
        n_cr = int(np.clip(1600 * (mn / 2048.0) ** 2, 500, 3600))
        for _ in range(n_cr):
            cxv = float(rng.uniform(4, w - 4)); cyv = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(3.0, 7.0) * scale)
            x0 = int(cxv); y0 = int(cyv - length * 0.5)
            x1 = int(cxv); y1 = int(cyv + length * 0.5)
            _cv2.line(M, (x0, y0), (x1, y1), float(rng.uniform(0.18, 0.55)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0, y0), (x1, y1), float(rng.uniform(0.30, 0.72)), 1, lineType=_cv2.LINE_AA)

        # 4) Sheen dots 2-5 px (was 3-7)
        n_d = int(np.clip(2000 * (mn / 2048.0) ** 2, 600, 4800))
        for _ in range(n_d):
            cxv = int(rng.integers(0, w)); cyv = int(rng.integers(0, h))
            r = int(max(1, rng.uniform(2.0, 5.0) * scale))
            _cv2.circle(M, (cxv, cyv), r, float(rng.uniform(0.55, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cxv, cyv), r, float(rng.uniform(0.08, 0.42)), -1, lineType=_cv2.LINE_AA)

    n_f = max(2000, int(h * w / 3200))
    fy = rng.integers(0, h, n_f); fx = rng.integers(0, w, n_f)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.55, 0.96, n_f).astype(np.float32))
    R[fy, fx] = np.minimum(R[fy, fx], rng.uniform(0.08, 0.28, n_f).astype(np.float32))

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
gradient_bands._spb_concept_complete = True
'''

NEW_BODIES["split_bands"] = '''def split_bands(shape, seed, sm, num_pairs=12, ratio=3.0,
                thick_bright=0.85, thin_bright=0.25, warp_strength=0.04):
    """split_bands.

    identity: A racing livery panel now packed with MANY fine stripe pairs
    — pair count ramped 2.5x (was h/92, now h/36) so each glossy stripe is
    only ~6-10 px tall, with 2-4 px matte pinstripe seams. Per-stripe
    INDEPENDENT M/R/CC continuous uniforms. Short race hairlines 4-10 px
    (was 10-22), dense small pigment discs 2-4 px, dark grit dots.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 88321)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    pairs = max(int(num_pairs) * 3, int(mn / 36.0))  # 2.5x tighter
    unit = max(2.0, h / max(pairs * (ratio + 1.0), 1.0))
    warp = (np.sin(xx / max(w, 1) * np.pi * float(rng.uniform(4.0, 8.0)) + float(seed)) +
            np.sin(xx / max(w, 1) * np.pi * float(rng.uniform(10.0, 18.0)) + float(seed) * 0.13) * 0.35) * warp_strength * h
    coord = yy + warp
    cycle = np.mod(coord, unit * (ratio + 1.0))
    thick_mask = (cycle < unit * ratio).astype(np.float32)
    edge_dist = np.minimum(np.abs(cycle - unit * ratio), np.minimum(cycle, unit * (ratio + 1.0) - cycle)) / max(unit, 1.0)
    seam = np.exp(-(edge_dist ** 2) / 0.010).astype(np.float32)

    stripe_idx = np.floor(coord / max(unit * (ratio + 1.0), 1.0)).astype(np.int32)
    n_stripes = int(stripe_idx.max() - stripe_idx.min() + 2)
    base = int(stripe_idx.min())
    stripe_M = rng.uniform(0.25, 0.96, n_stripes).astype(np.float32)
    stripe_R = rng.uniform(0.06, 0.60, n_stripes).astype(np.float32)
    stripe_CC = rng.uniform(0.06, 0.88, n_stripes).astype(np.float32)
    idx_norm = stripe_idx - base
    pM = stripe_M[idx_norm]
    pR = stripe_R[idx_norm]
    pCC = stripe_CC[idx_norm]

    fbm = _normalize(multi_scale_noise(shape, [2.0, 6.0, 16.0], [0.5, 0.3, 0.2], int(seed) + 6431))

    M = (thick_mask * pM + (1.0 - thick_mask) * (pM * 0.18 + 0.06) + (fbm - 0.5) * 0.08).astype(np.float32)
    R = (thick_mask * pR + (1.0 - thick_mask) * (pR + 0.30) + (fbm - 0.5) * 0.06).astype(np.float32)
    CC = (thick_mask * pCC + (1.0 - thick_mask) * (pCC * 0.30 + 0.15) + (fbm - 0.5) * 0.08).astype(np.float32)
    M -= seam * 0.20
    R += seam * 0.25
    CC -= seam * 0.15

    if _CV2_OK:
        # Race hairlines 4-10 px (was 10-22)
        n_hair = int(np.clip(2400 * (mn / 2048.0) ** 2, 800, 5800))
        for _ in range(n_hair):
            cx_b = float(rng.uniform(4, w - 4)); cy_b = float(rng.uniform(4, h - 4))
            length_b = float(rng.uniform(4.0, 10.0)) * scale
            ang_b = float(rng.uniform(-0.10, 0.10))
            x0b = int(cx_b - np.cos(ang_b) * length_b * 0.5); y0b = int(cy_b - np.sin(ang_b) * length_b * 0.5)
            x1b = int(cx_b + np.cos(ang_b) * length_b * 0.5); y1b = int(cy_b + np.sin(ang_b) * length_b * 0.5)
            _cv2.line(M, (x0b, y0b), (x1b, y1b), float(rng.uniform(0.40, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0b, y0b), (x1b, y1b), float(rng.uniform(0.05, 0.30)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0b, y0b), (x1b, y1b), float(rng.uniform(0.08, 0.70)), 1, lineType=_cv2.LINE_AA)

        # Pigment discs 2-4 px (was 3-7)
        n_pig = int(np.clip(1800 * (mn / 2048.0) ** 2, 600, 4400))
        for _ in range(n_pig):
            cx_b = int(rng.integers(0, w)); cy_b = int(rng.integers(0, h))
            r_b = max(1, int(float(rng.uniform(1.5, 3.0)) * scale))
            _cv2.circle(M, (cx_b, cy_b), r_b, float(rng.uniform(0.45, 0.95)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx_b, cy_b), r_b, float(rng.uniform(0.08, 0.40)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx_b, cy_b), r_b, float(rng.uniform(0.08, 0.80)), -1, lineType=_cv2.LINE_AA)

        # Grit dots 1-2 px
        n_dk = int(np.clip(1400 * (mn / 2048.0) ** 2, 460, 3500))
        for _ in range(n_dk):
            cx_b = int(rng.integers(0, w)); cy_b = int(rng.integers(0, h))
            r_b = max(1, int(float(rng.uniform(1.0, 2.0)) * scale))
            _cv2.circle(M, (cx_b, cy_b), r_b, float(rng.uniform(0.06, 0.22)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx_b, cy_b), r_b, float(rng.uniform(0.55, 0.92)), -1, lineType=_cv2.LINE_AA)

    n_fl = int(np.clip(2400 * (mn / 2048.0) ** 2, 800, 5800))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.50, 0.95, n_fl).astype(np.float32))
    R[fy, fx] = np.minimum(R[fy, fx], rng.uniform(0.05, 0.28, n_fl).astype(np.float32))
    CC[fy, fx] = np.maximum(CC[fy, fx], rng.uniform(0.15, 0.80, n_fl).astype(np.float32))

    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
split_bands._spb_concept_complete = True
'''

NEW_BODIES["bead_blast_uniform"] = '''def bead_blast_uniform(shape, seed, sm, **kwargs):
    """bead_blast_uniform.

    identity: A SATURATED bead-blasted surface — every square inch carries
    a media-impact pit. Five tiers stacked: ULTRA-DENSE 1-px speckle (5x
    prior), wide pit rims (2-5 px), pit-core dimples, dense fine 2-4 px
    secondary craters (4x prior count), and bright shiny media-grain
    residues. Per-feature INDEPENDENT continuous M/R/CC. No empty
    substrate.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 19443)
    scale = max(min(h, w) / 2048.0, 0.25)
    mn = min(h, w)

    # 1) Base matte aluminium
    bg = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.4, 0.35, 0.25], int(seed) + 3995))
    M = (0.45 + (bg - 0.5) * 0.18).astype(np.float32)
    R = (0.62 + (bg - 0.5) * 0.18).astype(np.float32)
    CC = (0.55 + (bg - 0.5) * 0.18).astype(np.float32)

    # 2) ULTRA-DENSE pit centers (5x prior — was 6500*scale^2)
    n_pits = max(12000, int(32000 * scale * scale))
    py = rng.integers(0, h, n_pits)
    px = rng.integers(0, w, n_pits)
    pv = rng.uniform(0.4, 1.0, n_pits).astype(np.float32)
    pit_centers = np.zeros(shape, dtype=np.float32)
    np.maximum.at(pit_centers, (py, px), pv)
    pit_wide = _gauss(pit_centers, sigma=max(1.2, 1.8 * scale))
    pit_narrow = _gauss(pit_centers, sigma=max(0.5, 0.9 * scale))
    pit_rim = _normalize(np.clip(pit_wide - pit_narrow * 0.6, 0, 1))
    M = np.clip(M + pit_rim * 0.34, 0, 1)
    R = np.clip(R - pit_rim * 0.24, 0, 1)
    CC = np.clip(CC - pit_rim * 0.14, 0, 1)

    pit_core = _normalize(pit_narrow)
    M = np.clip(M - pit_core * 0.22, 0, 1)
    R = np.clip(R + pit_core * 0.18, 0, 1)
    CC = np.clip(CC + pit_core * 0.08, 0, 1)

    if _CV2_OK:
        # 3) Dense secondary craters 2-4 px (4x prior — was 280)
        n_deep = int(np.clip(1200 * (mn / 2048.0) ** 2, 400, 3500))
        for _ in range(n_deep):
            cxv = int(rng.integers(0, w)); cyv = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(2.0, 4.0) * scale * 0.5))
            _cv2.circle(M, (cxv, cyv), r, float(rng.uniform(0.08, 0.30)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cxv, cyv), r, float(rng.uniform(0.65, 0.95)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cxv, cyv), r, float(rng.uniform(0.30, 0.65)), -1, lineType=_cv2.LINE_AA)

        # 4) Fine 1-2 px micro pits (additional tier)
        n_micro = int(np.clip(3000 * (mn / 2048.0) ** 2, 900, 8000))
        for _ in range(n_micro):
            cxv = int(rng.integers(0, w)); cyv = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1.0, 2.0) * scale))
            _cv2.circle(M, (cxv, cyv), r, float(rng.uniform(0.20, 0.45)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cxv, cyv), r, float(rng.uniform(0.55, 0.85)), -1, lineType=_cv2.LINE_AA)

    # 5) ULTRA-DENSE media-grain residues
    n_fl = int(np.clip(6500 * (mn / 2048.0) ** 2, 2000, 16000))
    fx = rng.integers(0, w, n_fl); fy = rng.integers(0, h, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.70, 0.96, n_fl).astype(np.float32))
    R[fy, fx] = np.minimum(R[fy, fx], rng.uniform(0.18, 0.45, n_fl).astype(np.float32))
    CC[fy, fx] = np.maximum(CC[fy, fx], rng.uniform(0.55, 0.88, n_fl).astype(np.float32))

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
bead_blast_uniform._spb_concept_complete = True
'''

NEW_BODIES["spec_sparkle_flake"] = '''def spec_sparkle_flake(shape, seed, sm, density_base=0.018, size_tiers=(3, 6, 10), **kwargs):
    """spec_sparkle_flake.

    identity: A SATURATED metallic flake field — five stacked tiers (was
    three): ULTRA-DENSE 1-px sparkle dust (5x prior), 2-3 px micro flakes
    (4x), 4-6 px small flakes (3x), 6-9 px mid flakes (2.5x), 9-12 px
    large irregular plates. Per-flake INDEPENDENT continuous M/R/CC. Dark
    void interstices fill any gaps. No confetti emptiness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 42051)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) Dark substrate
    g1 = _normalize(multi_scale_noise(shape, [2.5, 6.0, 13.0], [0.40, 0.34, 0.26], int(seed) + 8281))
    g2 = _normalize(multi_scale_noise(shape, [3.0, 7.0, 14.0], [0.40, 0.34, 0.26], int(seed) + 8282))
    g3 = _normalize(multi_scale_noise(shape, [3.5, 7.5, 15.0], [0.40, 0.34, 0.26], int(seed) + 8283))
    M  = (0.22 + (g1 - 0.5) * 0.22).astype(np.float32)
    R  = (0.42 + (g2 - 0.5) * 0.20).astype(np.float32)
    CC = (0.18 + (g3 - 0.5) * 0.18).astype(np.float32)

    if _CV2_OK:
        # 2) Large flakes 9-12 px (was 9-14, 2.5x count)
        n_lg = int(np.clip(950 * (mn / 2048.0) ** 2, 320, 2400))
        for _ in range(n_lg):
            cxp = int(rng.uniform(0.02, 0.98) * w); cyp = int(rng.uniform(0.02, 0.98) * h)
            rx = max(2, int(rng.uniform(9.0, 12.0) * scale * 0.5))
            ry = max(2, int(rx * rng.uniform(0.6, 1.0)))
            ang = float(rng.uniform(0, 180))
            _cv2.ellipse(M, (cxp, cyp), (rx, ry), ang, 0, 360, float(rng.uniform(0.80, 0.97)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cxp, cyp), (rx, ry), ang, 0, 360, float(rng.uniform(0.05, 0.22)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cxp, cyp), (rx, ry), ang, 0, 360, float(rng.uniform(0.04, 0.20)), -1, lineType=_cv2.LINE_AA)

        # 3) Mid flakes 6-9 px (2.5x count)
        n_md = int(np.clip(2300 * (mn / 2048.0) ** 2, 740, 5600))
        for _ in range(n_md):
            cxp = int(rng.uniform(0.02, 0.98) * w); cyp = int(rng.uniform(0.02, 0.98) * h)
            r_p = max(2, int(rng.uniform(6.0, 9.0) * scale * 0.5))
            _cv2.circle(M, (cxp, cyp), r_p, float(rng.uniform(0.78, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cxp, cyp), r_p, float(rng.uniform(0.06, 0.24)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cxp, cyp), r_p, float(rng.uniform(0.05, 0.22)), -1, lineType=_cv2.LINE_AA)

        # 4) Small flakes 4-6 px (3x count)
        n_sm = int(np.clip(5200 * (mn / 2048.0) ** 2, 1700, 12000))
        for _ in range(n_sm):
            cxp = int(rng.integers(0, w)); cyp = int(rng.integers(0, h))
            r_p = max(1, int(rng.uniform(4.0, 6.0) * scale * 0.5))
            _cv2.circle(M, (cxp, cyp), r_p, float(rng.uniform(0.72, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cxp, cyp), r_p, float(rng.uniform(0.08, 0.26)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cxp, cyp), r_p, float(rng.uniform(0.06, 0.24)), -1, lineType=_cv2.LINE_AA)

        # 5) Micro flakes 2-3 px (4x count)
        n_mi = int(np.clip(7800 * (mn / 2048.0) ** 2, 2500, 18000))
        for _ in range(n_mi):
            cxp = int(rng.integers(0, w)); cyp = int(rng.integers(0, h))
            r_p = max(1, int(rng.uniform(2.0, 3.0) * scale * 0.5))
            _cv2.circle(M, (cxp, cyp), r_p, float(rng.uniform(0.65, 0.94)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cxp, cyp), r_p, float(rng.uniform(0.10, 0.30)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cxp, cyp), r_p, float(rng.uniform(0.08, 0.28)), -1, lineType=_cv2.LINE_AA)

        # 6) Dark void pits to fill interstice voids
        n_v = int(np.clip(2400 * (mn / 2048.0) ** 2, 800, 5500))
        for _ in range(n_v):
            cxp = int(rng.integers(0, w)); cyp = int(rng.integers(0, h))
            r_p = max(1, int(rng.uniform(1.0, 2.5) * scale))
            _cv2.circle(M, (cxp, cyp), r_p, float(rng.uniform(0.10, 0.25)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cxp, cyp), r_p, float(rng.uniform(0.55, 0.82)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cxp, cyp), r_p, float(rng.uniform(0.40, 0.72)), -1, lineType=_cv2.LINE_AA)

    # 7) ULTRA-DENSE pinpoint sparkle dust
    n_fl = int(np.clip(9000 * (mn / 2048.0) ** 2, 3000, 22000))
    fxa = rng.integers(0, w, n_fl); fya = rng.integers(0, h, n_fl)
    M[fya, fxa] = np.maximum(M[fya, fxa], rng.uniform(0.80, 0.98, n_fl).astype(np.float32))
    R[fya, fxa] = np.minimum(R[fya, fxa], rng.uniform(0.05, 0.20, n_fl).astype(np.float32))
    CC[fya, fxa] = np.minimum(CC[fya, fxa], rng.uniform(0.04, 0.18, n_fl).astype(np.float32))

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
spec_sparkle_flake._spb_concept_complete = True
'''


# Helper to find function span in the file
def find_function_span(content, name):
    """Returns (start_idx, end_idx) for the function body including the def header.
    End is the start of the next 'def ' at column 0, OR start of '# ===' decoration, OR EOF.
    Also includes any trailing _spb_concept_complete = True assignment.
    """
    m = re.search(rf'^def {re.escape(name)}\(', content, re.MULTILINE)
    if not m:
        return None
    start = m.start()
    # Find next top-level statement after this function
    # Walk forward line by line until we see a line starting with non-whitespace
    # that is NOT part of this function (i.e., 'def ', '# ===', or other top-level)
    lines = content[start:].split('\n')
    end_line = len(lines)
    skip_first = True
    for i, line in enumerate(lines):
        if skip_first:
            skip_first = False
            continue
        # Top-level (column 0) non-blank, non-comment-only-continuation
        if line and not line[0].isspace():
            # Check: is this still part of the function (e.g. trailing decorator/assignment)?
            stripped = line.lstrip()
            if stripped.startswith(f'{name}._spb_concept_complete'):
                # Include this line, continue past it
                end_line = i + 1
                # Also include any further trailing assignments for same name
                continue
            else:
                end_line = i
                break
    end = start + sum(len(l) + 1 for l in lines[:end_line])
    # Strip trailing newlines past the last meaningful line
    return start, min(end, len(content))


def main():
    with open(SRC, 'r', encoding='utf-8') as f:
        content = f.read()

    # Process in REVERSE order of position so offsets remain valid
    spans = []
    for name in NEW_BODIES:
        s = find_function_span(content, name)
        if s is None:
            print(f"WARNING: {name} not found", file=sys.stderr)
            continue
        spans.append((s[0], s[1], name))
    spans.sort(key=lambda x: x[0], reverse=True)

    for start, end, name in spans:
        new_body = NEW_BODIES[name].rstrip() + "\n"
        old_snippet = content[start:end]
        # Preserve trailing blank line separation: if old_snippet ends with \n, keep new_body ending with \n
        content = content[:start] + new_body + content[end:]
        print(f"Replaced {name} ({end - start} -> {len(new_body)} bytes)")

    with open(SRC, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Wrote", SRC)


if __name__ == '__main__':
    main()
