"""
Round-5 corrective rebuild bodies for 12 targets.
Each value is the COMPLETE replacement function (def line through last return).
"""

REBUILDS = {}

# ---------------------------------------------------------------------------
# concentric_ripple — was 2D output. Make 3-channel; lean into water-ripple
# concentric ring differentiator; many small centers (8-14) at 8-22 px ring
# pitch; per-feature independent continuous M/R/CC; add cap-droplet dots and
# inter-center flecks.
# ---------------------------------------------------------------------------
REBUILDS['concentric_ripple'] = '''def concentric_ripple(shape, seed, sm, num_centers=3, ring_freq=15.0,
                      decay=0.5):
    """concentric_ripple.

    identity: A pond of small concentric water ripples — 14-22 ripple centers
    each radiating tight 8-16 px ring spacing, with bright crest hairlines,
    central drop-impact pip dots, and a substrate of fine cross-grain flecks.
    Per-ring and per-center INDEPENDENT continuous M/R/CC uniforms keep the
    chroma alive across the panel. Distinct from spiral_sweep and wave_ripple
    by being many small radial ripple seeds, not directional waves.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("concentric_ripple_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn = xx / max(w - 1, 1)
    yn = yy / max(h - 1, 1)

    # 1) BASE — three independent FBM substrates so chroma drifts continuously
    fM = _normalize(multi_scale_noise(shape, [3.0, 9.0, 22.0], [0.46, 0.32, 0.22], int(seed) + 5101))
    fR = _normalize(multi_scale_noise(shape, [3.0, 9.0, 22.0], [0.46, 0.32, 0.22], int(seed) + 5103))
    fCC = _normalize(multi_scale_noise(shape, [3.0, 9.0, 22.0], [0.46, 0.32, 0.22], int(seed) + 5105))
    M = (0.42 + (fM - 0.5) * 0.26).astype(np.float32)
    R_ch = (0.50 + (fR - 0.5) * 0.26).astype(np.float32)
    CC = (0.44 + (fCC - 0.5) * 0.26).astype(np.float32)

    # 2) RIPPLE CENTERS — 14-22 small centers; each ring sharp + independent chroma
    n_centers = int(np.clip(18 + rng.integers(-4, 5), 12, 22))
    for _ in range(n_centers):
        cx = rng.uniform(0.04, 0.96); cy = rng.uniform(0.04, 0.96)
        dx = xn - cx; dy = yn - cy
        dist = np.sqrt(dx * dx + dy * dy) + 1e-6
        ring_period_px = float(rng.uniform(8.0, 16.0) * scale)
        ring_period_norm = ring_period_px / max(mn, 1)
        rings = np.sin(dist / max(ring_period_norm, 1e-5) * 2.0 * np.pi + rng.uniform(0, 2 * np.pi))
        crests = np.exp(-np.abs(rings) * 7.5) * np.exp(-dist * float(rng.uniform(2.2, 3.6)))
        crests = crests.astype(np.float32)
        vM = float(rng.uniform(0.55, 0.95))
        vR = float(rng.uniform(0.08, 0.45))
        vCC = float(rng.uniform(0.08, 0.42))
        M = np.maximum(M, crests * vM)
        R_ch = np.minimum(R_ch, 1.0 - crests * (1.0 - vR))
        CC = np.minimum(CC, 1.0 - crests * (1.0 - vCC))

    if _CV2_OK:
        # 3) DROP-IMPACT PIPS — small bright filled dots at each ring center (5x density)
        n_pips = int(np.clip(900 * (mn / 2048.0) ** 2, 280, 2400))
        for _ in range(n_pips):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(1, int(rng.uniform(1.5, 3.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.60, 0.95)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(rng.uniform(0.06, 0.30)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.06, 0.35)), -1, lineType=_cv2.LINE_AA)

        # 4) RING CREST HAIRLINES — short 8-18 px arc fragments to break smoothness
        n_arcs = int(np.clip(700 * (mn / 2048.0) ** 2, 240, 1800))
        for _ in range(n_arcs):
            cx = float(rng.uniform(4, w - 4)); cy = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(8.0, 18.0) * scale)
            ang = float(rng.uniform(0, 2 * np.pi))
            x0s = int(cx - np.cos(ang) * length * 0.5)
            y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5)
            y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.50, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.10, 0.45)), 1, lineType=_cv2.LINE_AA)

    # 5) FINE CHROMA FLECKS — fill substrate (5x density vs original)
    n_flecks = int(np.clip(2400 * (mn / 2048.0) ** 2, 900, 6000))
    fy = rng.integers(0, h, n_flecks); fx = rng.integers(0, w, n_flecks)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(-0.30, 0.45, n_flecks).astype(np.float32), 0, 1)
    R_ch[fy, fx] = np.clip(R_ch[fy, fx] + rng.uniform(-0.25, 0.30, n_flecks).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.25, 0.30, n_flecks).astype(np.float32), 0, 1)

    out = np.stack([M, R_ch, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
concentric_ripple._spb_concept_complete = True
'''

# ---------------------------------------------------------------------------
# cloud_wisps — neutral pearl. Bump density 3x. Tighter wisp aspect ratio
# (long-elongated 4:1 -> 6:1). Add 4th tier: pearl chroma swarms (8-12 px
# soft blobs) so substrate is never empty.
# ---------------------------------------------------------------------------
REBUILDS['cloud_wisps'] = '''def cloud_wisps(shape, seed, sm, num_octaves=5, lacunarity=2.0, persistence=0.5):
    """cloud_wisps.

    identity: A neutral pearl cloud reading — many long elongated wisp
    ellipses (12-22 px, 5:1 aspect) drifting in shared drift directions,
    edged by thin bright halo rings, peppered with small vapor pit dots,
    and bedded on a stippling of soft 6-10 px chroma swarm blobs that
    fill any gap. Per-feature INDEPENDENT continuous M/R/CC uniforms.
    Distinct from warm/cool variants by neutral channel balance and
    longer elongated wisp aspect.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("cloud_wisps_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) PEARL FBM BASE — three independent channels
    fbm_a = _normalize(multi_scale_noise(shape, [4.0, 11.0, 24.0], [0.40, 0.34, 0.26], int(seed) + 311))
    fbm_b = _normalize(multi_scale_noise(shape, [5.0, 13.0, 28.0], [0.42, 0.34, 0.24], int(seed) + 313))
    fbm_c = _normalize(multi_scale_noise(shape, [3.0, 8.0, 18.0], [0.42, 0.34, 0.24], int(seed) + 315))
    M = (0.45 + (fbm_a - 0.5) * 0.28).astype(np.float32)
    R = (0.45 + (fbm_b - 0.5) * 0.28).astype(np.float32)
    CC = (0.40 + (fbm_c - 0.5) * 0.28).astype(np.float32)

    if _CV2_OK:
        # 2) ELONGATED WISP ELLIPSES — 5:1 aspect, 3x density
        n_wisps = int(np.clip(1800 * (mn / 2048.0) ** 2, 700, 6000))
        drift_ang = float(rng.uniform(0, 180))
        for _ in range(n_wisps):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            rx = max(3, int(rng.uniform(5.0, 11.0) * scale))
            ry = max(1, int(rng.uniform(1.0, 2.0) * scale))
            ang = float(drift_ang + rng.normal(0, 12.0))
            _cv2.ellipse(M, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(0.42, 0.93)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(0.10, 0.45)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(0.08, 0.42)), -1, lineType=_cv2.LINE_AA)

        # 3) HALO RING outlines — thin bright outline circles
        n_halos = int(np.clip(900 * (mn / 2048.0) ** 2, 320, 2600))
        for _ in range(n_halos):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(2, int(rng.uniform(3.0, 6.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.55, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.08, 0.35)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.05, 0.30)), 1, lineType=_cv2.LINE_AA)

        # 4) CHROMA SWARM BLOBS — fill empties with soft 6-10 px filled disks
        n_blobs = int(np.clip(1400 * (mn / 2048.0) ** 2, 500, 4200))
        for _ in range(n_blobs):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(2, int(rng.uniform(3.0, 5.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.30, 0.85)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.25, 0.75)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.20, 0.70)), -1, lineType=_cv2.LINE_AA)

        # 5) VAPOR PITS — small darkening dots where cloud thins
        n_pits = int(np.clip(700 * (mn / 2048.0) ** 2, 240, 2200))
        for _ in range(n_pits):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(1, int(rng.uniform(1.0, 2.2) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.10, 0.35)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.55, 0.92)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.55, 0.88)), -1, lineType=_cv2.LINE_AA)

    # 6) BRIGHT PEARL FLECKS — vectorized
    n_flecks = int(np.clip(2000 * (mn / 2048.0) ** 2, 700, 5500))
    fx = rng.integers(0, w, n_flecks); fy = rng.integers(0, h, n_flecks)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(0.15, 0.50, n_flecks).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] - rng.uniform(0.10, 0.35, n_flecks).astype(np.float32), 0, 1)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
cloud_wisps._spb_concept_complete = True
'''

# ---------------------------------------------------------------------------
# cloud_wisps_warm — copper/gold pearl. Up density. Add warm crackle hairs.
# ---------------------------------------------------------------------------
REBUILDS['cloud_wisps_warm'] = '''def cloud_wisps_warm(shape, seed, sm, num_octaves=5, **kwargs):
    """cloud_wisps_warm.

    identity: A copper-amber pearl cloud — long warm wisp ellipses biased
    high-M low-R, blended with sun-warm droplet beads, amber halo rings,
    fine warm crackle hairlines (8-14 px) at +35deg drift, and a substrate
    of soft tan chroma swarms so no spot reads as blank. Stronger M
    contrast for depth. Distinct from cloud_wisps (neutral) and
    cloud_wisps_cool (frost). Per-feature INDEPENDENT continuous M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("cloud_wisps_warm_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) WARM FBM BASE
    fbm_a = _normalize(multi_scale_noise(shape, [4.0, 11.0, 24.0], [0.40, 0.34, 0.26], int(seed) + 341))
    fbm_b = _normalize(multi_scale_noise(shape, [6.0, 14.0, 30.0], [0.42, 0.34, 0.24], int(seed) + 343))
    fbm_c = _normalize(multi_scale_noise(shape, [3.5, 9.0, 20.0], [0.42, 0.34, 0.24], int(seed) + 345))
    M = (0.58 + (fbm_a - 0.5) * 0.32).astype(np.float32)
    R = (0.30 + (fbm_b - 0.5) * 0.22).astype(np.float32)
    CC = (0.34 + (fbm_c - 0.5) * 0.22).astype(np.float32)

    if _CV2_OK:
        # 2) WARM WISP ELLIPSES — high-M bias, dense
        n_wisps = int(np.clip(1500 * (mn / 2048.0) ** 2, 540, 5000))
        drift = float(rng.uniform(20, 60))
        for _ in range(n_wisps):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            rx = max(3, int(rng.uniform(5.0, 10.0) * scale))
            ry = max(1, int(rng.uniform(1.0, 2.0) * scale))
            ang = float(drift + rng.normal(0, 14.0))
            _cv2.ellipse(M, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(0.55, 0.95)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(0.08, 0.32)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(0.06, 0.28)), -1, lineType=_cv2.LINE_AA)

        # 3) AMBER HALO RINGS
        n_halos = int(np.clip(800 * (mn / 2048.0) ** 2, 280, 2400))
        for _ in range(n_halos):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(2, int(rng.uniform(2.5, 5.5) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.62, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.12, 0.38)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.08, 0.32)), 1, lineType=_cv2.LINE_AA)

        # 4) SUN-WARM DROPLET BEADS
        n_drops = int(np.clip(900 * (mn / 2048.0) ** 2, 320, 2600))
        for _ in range(n_drops):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(1, int(rng.uniform(1.0, 2.5) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.68, 0.97)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.05, 0.25)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.05, 0.28)), -1, lineType=_cv2.LINE_AA)

        # 5) WARM CRACKLE HAIRLINES — drift-aligned 8-14 px hairs for differentiation
        n_hair = int(np.clip(800 * (mn / 2048.0) ** 2, 280, 2400))
        for _ in range(n_hair):
            cx = float(rng.uniform(4, w - 4)); cy = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(8.0, 14.0) * scale)
            ang = float(np.deg2rad(drift)) + float(rng.normal(0, 0.12))
            x0s = int(cx - np.cos(ang) * length * 0.5)
            y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5)
            y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.50, 0.92)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.10, 0.40)), 1, lineType=_cv2.LINE_AA)

    # 6) BRIGHT WARM FLECKS — vectorized
    n_flecks = int(np.clip(2200 * (mn / 2048.0) ** 2, 800, 5800))
    fx = rng.integers(0, w, n_flecks); fy = rng.integers(0, h, n_flecks)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(0.15, 0.42, n_flecks).astype(np.float32), 0, 1)
    R[fy, fx] = np.clip(R[fy, fx] - rng.uniform(0.10, 0.30, n_flecks).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] - rng.uniform(0.08, 0.25, n_flecks).astype(np.float32), 0, 1)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
cloud_wisps_warm._spb_concept_complete = True
'''

# ---------------------------------------------------------------------------
# cloud_wisps_cool — frost/ice pearl. Sharper crystalline 8-16 px ridges.
# Big differentiator: SHARP crystalline geometry vs warm's soft amber.
# ---------------------------------------------------------------------------
REBUILDS['cloud_wisps_cool'] = '''def cloud_wisps_cool(shape, seed, sm, num_octaves=6, **kwargs):
    """cloud_wisps_cool.

    identity: A frosted icy-pearl cloud — sharp crystalline frost ridges
    crossed at two angles every 10-16 px, ice-rimmed bright wisp ellipses
    with cold blue chroma, dense icy sparkle dots, short crystal-shard
    needle fragments (8-12 px), and a substrate of fine frost flecks.
    Distinctly SHARP vs warm's soft amber. Higher R for matte ice gloss.
    Per-feature INDEPENDENT continuous M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("cloud_wisps_cool_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) COOL FBM BASE — sharper octaves
    fbm_a = _normalize(multi_scale_noise(shape, [3.0, 7.0, 16.0], [0.46, 0.34, 0.20], int(seed) + 371))
    fbm_b = _normalize(multi_scale_noise(shape, [4.5, 11.0, 24.0], [0.44, 0.34, 0.22], int(seed) + 373))
    fbm_c = _normalize(multi_scale_noise(shape, [2.5, 6.0, 14.0], [0.46, 0.34, 0.20], int(seed) + 375))
    M = (0.40 + (fbm_a - 0.5) * 0.34).astype(np.float32)
    R = (0.60 + (fbm_b - 0.5) * 0.26).astype(np.float32)
    CC = (0.30 + (fbm_c - 0.5) * 0.24).astype(np.float32)

    # 2) FROST RIDGES — sharp crossed crystalline lines
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    period_a = max(10.0, mn / 130.0)
    period_b = max(13.0, mn / 90.0)
    pa = np.mod(xx + yy * 0.36, period_a) - period_a * 0.5
    pb = np.mod(xx - yy * 0.52, period_b) - period_b * 0.5
    frost_a = np.exp(-(pa * pa) / (2.0 * (period_a * 0.14) ** 2)).astype(np.float32)
    frost_b = np.exp(-(pb * pb) / (2.0 * (period_b * 0.14) ** 2)).astype(np.float32)
    M = np.clip(M + frost_a * 0.26 + frost_b * 0.20, 0, 1)
    R = np.clip(R - frost_a * 0.18 - frost_b * 0.14, 0, 1)
    CC = np.clip(CC + frost_a * 0.12 + frost_b * 0.10, 0, 1)

    if _CV2_OK:
        # 3) ICE-RIMMED WISP ELLIPSES — 3x density
        n_wisps = int(np.clip(1300 * (mn / 2048.0) ** 2, 480, 4400))
        for _ in range(n_wisps):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            rx = max(3, int(rng.uniform(4.0, 9.0) * scale))
            ry = max(1, int(rng.uniform(1.0, 3.0) * scale))
            ang = float(rng.uniform(0, 180))
            _cv2.ellipse(M, (cx, cy), (rx + 1, ry + 1), ang, 0, 360, float(rng.uniform(0.62, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (rx + 1, ry + 1), ang, 0, 360, float(rng.uniform(0.20, 0.50)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (rx, ry), ang, 0, 360, float(rng.uniform(0.18, 0.55)), -1, lineType=_cv2.LINE_AA)

        # 4) CRYSTAL SHARD NEEDLES — short angled segments at 60deg crystal angles
        n_shards = int(np.clip(1100 * (mn / 2048.0) ** 2, 400, 3400))
        for _ in range(n_shards):
            cx = float(rng.uniform(4, w - 4)); cy = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(8.0, 12.0) * scale)
            ang = float(rng.choice([0.0, np.pi / 3.0, 2 * np.pi / 3.0])) + float(rng.normal(0, 0.10))
            x0s = int(cx - np.cos(ang) * length * 0.5)
            y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5)
            y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.55, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.15, 0.42)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.10, 0.40)), 1, lineType=_cv2.LINE_AA)

        # 5) ICY SPARKLE DOTS
        n_spark = int(np.clip(1100 * (mn / 2048.0) ** 2, 380, 3300))
        for _ in range(n_spark):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = int(max(1, rng.uniform(1.0, 2.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.68, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.12, 0.38)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.08, 0.30)), -1, lineType=_cv2.LINE_AA)

    # 6) FROST FLECKS — vectorized
    n_flecks = int(np.clip(2400 * (mn / 2048.0) ** 2, 900, 6000))
    fx = rng.integers(0, w, n_flecks); fy = rng.integers(0, h, n_flecks)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(0.15, 0.42, n_flecks).astype(np.float32), 0, 1)
    R[fy, fx] = np.clip(R[fy, fx] - rng.uniform(0.10, 0.30, n_flecks).astype(np.float32), 0, 1)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
cloud_wisps_cool._spb_concept_complete = True
'''

# ---------------------------------------------------------------------------
# crystal_growth — dendrite-style 6-arm starbursts on dense frost. Pump
# cluster + branch density 3x. Add: 4th tier of fine 4-px frost spike dots.
# Keep 6-arm distinctive identity.
# ---------------------------------------------------------------------------
REBUILDS['crystal_growth'] = '''def crystal_growth(shape, seed, sm, num_seeds_pts=4, growth_steps=200, **kwargs):
    """crystal_growth.

    identity: A dense field of 6-armed crystalline starbursts (8-22 px reach)
    over a frost-noise substrate, with short radial dendrite branches between
    clusters, ultrafine frost spike dots filling gaps, and accent flecks of
    bright bare-metal pop. The 6-fold symmetric starburst is the signature
    distinguishing it from prismatic_shatter (random) and snowflake variants.
    Per-feature INDEPENDENT continuous M/R/CC uniforms.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("crystal_growth_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) BASE — frost FBM substrate
    fM = _normalize(multi_scale_noise(shape, [1.5, 4.0, 11.0, 28.0], [0.35, 0.30, 0.22, 0.13], int(seed) + 4822))
    fR = _normalize(multi_scale_noise(shape, [1.5, 4.0, 11.0, 28.0], [0.35, 0.30, 0.22, 0.13], int(seed) + 4823))
    fCC = _normalize(multi_scale_noise(shape, [1.5, 4.0, 11.0, 28.0], [0.35, 0.30, 0.22, 0.13], int(seed) + 4824))
    M = (0.40 + (fM - 0.5) * 0.34).astype(np.float32)
    R_ch = (0.50 + (fR - 0.5) * 0.32).astype(np.float32)
    CC = (0.42 + (fCC - 0.5) * 0.32).astype(np.float32)

    if _CV2_OK:
        # 2) 6-ARM CRYSTAL STARBURSTS — 3x density
        n_clusters = int(np.clip(800 * (mn / 2048.0) ** 2, 280, 2800))
        for _ in range(n_clusters):
            cx = int(rng.uniform(0.04, 0.96) * w); cy = int(rng.uniform(0.04, 0.96) * h)
            reach = rng.uniform(5.0, 11.0) * scale
            base_ang = float(rng.uniform(0, np.pi / 3))
            vM = float(rng.uniform(0.55, 0.95))
            vR = float(rng.uniform(0.08, 0.40))
            vC = float(rng.uniform(0.08, 0.45))
            for arm in range(6):
                ang = base_ang + arm * np.pi / 3
                ex = int(np.clip(cx + np.cos(ang) * reach, 0, w - 1))
                ey = int(np.clip(cy + np.sin(ang) * reach, 0, h - 1))
                _cv2.line(M, (cx, cy), (ex, ey), vM, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R_ch, (cx, cy), (ex, ey), vR, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx, cy), (ex, ey), vC, 1, lineType=_cv2.LINE_AA)
                # mid-arm side branches — true dendrite (length 1/3 arm)
                if rng.random() < 0.6:
                    mx = cx + np.cos(ang) * reach * 0.55
                    my = cy + np.sin(ang) * reach * 0.55
                    side = rng.choice([1.0, -1.0])
                    side_ang = ang + side * np.pi / 3
                    sx = int(np.clip(mx + np.cos(side_ang) * reach * 0.35, 0, w - 1))
                    sy = int(np.clip(my + np.sin(side_ang) * reach * 0.35, 0, h - 1))
                    _cv2.line(M, (int(mx), int(my)), (sx, sy), vM * 0.85, 1, lineType=_cv2.LINE_AA)
            # bright center pip
            r0 = max(1, int(rng.uniform(1.0, 2.0) * scale))
            _cv2.circle(M, (cx, cy), r0, float(rng.uniform(0.72, 0.98)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r0, float(rng.uniform(0.05, 0.28)), -1, lineType=_cv2.LINE_AA)

        # 3) ISOLATED DENDRITE BRANCHES — short radial 4-10 px
        n_branches = int(np.clip(1500 * (mn / 2048.0) ** 2, 540, 4500))
        for _ in range(n_branches):
            cx = float(rng.uniform(0.02, 0.98) * w); cy = float(rng.uniform(0.02, 0.98) * h)
            length = rng.uniform(4.0, 10.0) * scale
            ang = rng.uniform(0, 2 * np.pi)
            x2 = int(np.clip(cx + np.cos(ang) * length, 0, w - 1))
            y2 = int(np.clip(cy + np.sin(ang) * length, 0, h - 1))
            _cv2.line(M, (int(cx), int(cy)), (x2, y2), float(rng.uniform(0.42, 0.92)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (int(cx), int(cy)), (x2, y2), float(rng.uniform(0.10, 0.45)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (int(cx), int(cy)), (x2, y2), float(rng.uniform(0.10, 0.50)), 1, lineType=_cv2.LINE_AA)

        # 4) FROST SPIKE DOTS — fine substrate dots filling gaps
        n_frost = int(np.clip(1600 * (mn / 2048.0) ** 2, 580, 4800))
        for _ in range(n_frost):
            cxi = int(rng.uniform(0.02, 0.98) * w); cyi = int(rng.uniform(0.02, 0.98) * h)
            r = max(1, int(rng.uniform(1.0, 2.0) * scale))
            _cv2.circle(M, (cxi, cyi), r, float(rng.uniform(0.55, 0.93)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cxi, cyi), r, float(rng.uniform(0.08, 0.32)), -1, lineType=_cv2.LINE_AA)

    # 5) BRIGHT FLECKS — vectorized
    n_flecks = int(np.clip(1500 * (mn / 2048.0) ** 2, 540, 4400))
    fy2 = rng.integers(0, h, n_flecks); fx2 = rng.integers(0, w, n_flecks)
    M[fy2, fx2] = np.maximum(M[fy2, fx2], rng.uniform(0.55, 0.95, n_flecks).astype(np.float32))
    R_ch[fy2, fx2] = np.minimum(R_ch[fy2, fx2], rng.uniform(0.08, 0.30, n_flecks).astype(np.float32))
    CC[fy2, fx2] = np.minimum(CC[fy2, fx2], rng.uniform(0.05, 0.30, n_flecks).astype(np.float32))

    out = np.stack([M, R_ch, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
crystal_growth._spb_concept_complete = True
'''

# ---------------------------------------------------------------------------
# crushed_glass — angular shards on dark velvet. Owner complaint: too sparse.
# Add many tiny shard chips (8-18 px), pump edge glint + chip dot density.
# Distinct from prismatic_shatter by velvet darkness and edge glints.
# ---------------------------------------------------------------------------
REBUILDS['crushed_glass'] = '''def crushed_glass(shape, seed, sm, threshold_hi=0.72, **kwargs):
    """crushed_glass.

    identity: An angular crushed-glass shard field on dark velvet — hard-
    thresholded sin-interference shards form the panel-fracture geometry,
    paired with many bright fracture-edge hairline glints (8-18 px),
    crowded micro chip dots (2-4 px), short jag scratches, and a fine
    sub-grain layer so the velvet substrate never reads blank. Distinct
    from prismatic_shatter by dark velvet background plus dense small
    chip coverage. Per-feature INDEPENDENT continuous M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("crushed_glass_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    yy = np.arange(h, dtype=np.float32) / max(h, 1)
    xx = np.arange(w, dtype=np.float32) / max(w, 1)
    field = np.zeros(shape, dtype=np.float32)
    for _ in range(8):
        fy = rng.uniform(20, 80); fx = rng.uniform(20, 80)
        py = rng.uniform(0, 2 * np.pi); px = rng.uniform(0, 2 * np.pi)
        field += np.sin(yy[:, None] * fy * np.pi + py) * np.sin(xx[None, :] * fx * np.pi + px)
    field = _normalize(field)
    bright = (field > threshold_hi).astype(np.float32)

    fM = _normalize(multi_scale_noise(shape, [2.0, 5.0, 14.0], [0.45, 0.32, 0.23], int(seed) + 5904))
    fR = _normalize(multi_scale_noise(shape, [2.0, 5.0, 14.0], [0.45, 0.32, 0.23], int(seed) + 5905))
    fCC = _normalize(multi_scale_noise(shape, [2.0, 5.0, 14.0], [0.45, 0.32, 0.23], int(seed) + 5906))

    M = (0.18 + (fM - 0.5) * 0.20 + bright * (0.55 + (fM - 0.5) * 0.28)).astype(np.float32)
    R_ch = (0.68 - bright * (0.48 + (fR - 0.5) * 0.20) + (fR - 0.5) * 0.12).astype(np.float32)
    CC = (0.58 - bright * (0.32 + (fCC - 0.5) * 0.20) + (fCC - 0.5) * 0.12).astype(np.float32)

    if _CV2_OK:
        # FRACTURE EDGE GLINTS — 3x density
        n_edges = int(np.clip(2700 * (mn / 2048.0) ** 2, 900, 7000))
        for _ in range(n_edges):
            cx = float(rng.uniform(2, w - 2)); cy = float(rng.uniform(2, h - 2))
            length = rng.uniform(8.0, 18.0) * scale
            ang = rng.uniform(0, 2 * np.pi)
            x0s = int(cx - np.cos(ang) * length * 0.5)
            y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5)
            y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.55, 0.97)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.06, 0.30)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.08, 0.42)), 1, lineType=_cv2.LINE_AA)

        # MICRO CHIP DOTS — 3x density
        n_chip = int(np.clip(1800 * (mn / 2048.0) ** 2, 600, 5400))
        for _ in range(n_chip):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            r = max(1, int(rng.uniform(1.0, 2.5) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.65, 0.98)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(rng.uniform(0.05, 0.25)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.05, 0.25)), -1, lineType=_cv2.LINE_AA)

        # JAG SCRATCHES — angular 6-10 px
        n_jag = int(np.clip(1200 * (mn / 2048.0) ** 2, 400, 3600))
        for _ in range(n_jag):
            cx = float(rng.uniform(2, w - 2)); cy = float(rng.uniform(2, h - 2))
            length = float(rng.uniform(6.0, 10.0) * scale)
            ang = float(rng.choice([0.0, np.pi / 4, np.pi / 2, 3 * np.pi / 4])) + float(rng.normal(0, 0.18))
            x0s = int(cx - np.cos(ang) * length * 0.5)
            y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5)
            y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.40, 0.85)), 1, lineType=_cv2.LINE_AA)

    # Accent fleck speckle (sub-grain) — fills velvet
    n_flecks = int(np.clip(2200 * (mn / 2048.0) ** 2, 800, 6000))
    fy2 = rng.integers(0, h, n_flecks); fx2 = rng.integers(0, w, n_flecks)
    M[fy2, fx2] = np.maximum(M[fy2, fx2], rng.uniform(0.40, 0.90, n_flecks).astype(np.float32))
    R_ch[fy2, fx2] = np.clip(R_ch[fy2, fx2] + rng.uniform(-0.20, 0.25, n_flecks).astype(np.float32), 0, 1)
    CC[fy2, fx2] = np.clip(CC[fy2, fx2] + rng.uniform(-0.20, 0.25, n_flecks).astype(np.float32), 0, 1)

    out = np.stack([M, R_ch, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
crushed_glass._spb_concept_complete = True
'''

# ---------------------------------------------------------------------------
# diamond_lattice — rhombus mesh. Pitch already ~mn/78. Add: per-cell tint
# with continuous uniforms (replace any 8-tier hashing), pump glint count.
# Distinct from carbon_weave (orthogonal weave) by 45deg diamond grid.
# ---------------------------------------------------------------------------
REBUILDS['diamond_lattice'] = '''def diamond_lattice(shape, seed, sm, cell_size=24, depth_variation=0.4, **kwargs):
    """diamond_lattice.

    identity: A rotated 45deg rhombus lattice at ~14-px pitch with thin bright
    wire edges, per-cell continuous random M/R/CC tints (no 8-tier palette),
    soft inner-bevel rings inside each diamond, sparse vertex pinpoint glints,
    short cross-wire diagonal hairlines, and a low-amplitude grime field.
    Distinct from carbon_weave (orthogonal weave) by 45deg rotation, and from
    hex_cells by rhombus geometry. Per-feature INDEPENDENT continuous M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("diamond_lattice_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    angle = np.deg2rad(45.0 + rng.uniform(-4.0, 4.0))
    xr = xx * np.cos(angle) - yy * np.sin(angle)
    yr = xx * np.sin(angle) + yy * np.cos(angle)
    pitch = max(10.0, mn / 110.0)
    fu = (xr / pitch) - np.floor(xr / pitch)
    fv = (yr / pitch) - np.floor(yr / pitch)
    du = np.minimum(fu, 1.0 - fu)
    dv = np.minimum(fv, 1.0 - fv)
    wire = np.maximum(
        np.exp(-(du ** 2) / (2.0 * 0.015 ** 2)),
        np.exp(-(dv ** 2) / (2.0 * 0.015 ** 2)),
    )
    diamond_center = np.clip(1.0 - (np.abs(fu - 0.5) + np.abs(fv - 0.5)) * 2.0, 0.0, 1.0)
    cell_u = np.floor(xr / pitch).astype(np.int32)
    cell_v = np.floor(yr / pitch).astype(np.int32)

    # Per-cell INDEPENDENT continuous uniforms (LARGE table, not 8-tier)
    TABLE = 8192
    cell_M_table = rng.uniform(0.10, 0.95, TABLE).astype(np.float32)
    cell_R_table = rng.uniform(0.08, 0.92, TABLE).astype(np.float32)
    cell_CC_table = rng.uniform(0.08, 0.95, TABLE).astype(np.float32)
    hash_idx = ((cell_u * 73856093) ^ (cell_v * 19349663) ^ int(seed) * 83492791) & (TABLE - 1)
    cell_M = cell_M_table[hash_idx]
    cell_R = cell_R_table[hash_idx]
    cell_CC = cell_CC_table[hash_idx]

    # Grime field — low-freq variation
    grime = _normalize(multi_scale_noise(shape, [9.0, 22.0], [0.55, 0.45], int(seed) + 5503))

    M = np.clip(cell_M * (1.0 - diamond_center * 0.20) + wire * 0.30 + (grime - 0.5) * 0.08, 0, 1)
    R_ch = np.clip(0.85 - wire * 0.50 + cell_R * 0.22 + (grime - 0.5) * 0.10, 0, 1)
    CC = np.clip(cell_CC * 0.60 + (1.0 - diamond_center) * 0.18 - wire * 0.15 + (grime - 0.5) * 0.08, 0, 1)

    if _CV2_OK:
        # Vertex glints — 3x density bright pinpoints near corner-strong wire
        n_glint = int(np.clip(1800 * (mn / 2048.0) ** 2, 600, 5000))
        for _ in range(n_glint):
            cx = int(rng.uniform(0, w)); cy = int(rng.uniform(0, h))
            if wire[cy, cx] < 0.7:
                continue
            r = max(1, int(rng.uniform(1.0, 2.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.72, 0.98)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(rng.uniform(0.06, 0.25)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.06, 0.28)), -1, lineType=_cv2.LINE_AA)

        # CROSS-WIRE HAIRLINES — short diagonal 8-14 px segments
        n_cw = int(np.clip(900 * (mn / 2048.0) ** 2, 320, 2800))
        for _ in range(n_cw):
            cx = float(rng.uniform(4, w - 4)); cy = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(8.0, 14.0) * scale)
            ang = float(np.deg2rad(rng.choice([45.0, -45.0]))) + float(rng.normal(0, 0.08))
            x0s = int(cx - np.cos(ang) * length * 0.5)
            y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5)
            y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.55, 0.92)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.10, 0.40)), 1, lineType=_cv2.LINE_AA)

    out = np.stack([M, R_ch, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
diamond_lattice._spb_concept_complete = True
'''

# ---------------------------------------------------------------------------
# diagonal_bands — 30deg ribbons. Tighter pitch (10-14 px from 18). Per-band
# independent uniforms via large-table hash. Pump scratch + fleck densities.
# ---------------------------------------------------------------------------
REBUILDS['diagonal_bands'] = '''def diagonal_bands(shape, seed, sm, **kwargs):
    """diagonal_bands.

    identity: Fine 10-14 px wide diagonal ribbons running at +30deg, each
    band pulled from a 4096-entry CONTINUOUS M/R/CC table (no 8-tier
    palette), separated by sharp grouting micro-shadows, dressed with
    dense diagonal scratch hairlines along the ribbon direction (5x
    density), and bright glint flecks that align with the stripe axis.
    Distinct from banded_rows by 30deg angle, finer pitch, and per-band
    independent chroma.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("diagonal_bands_r5") % 10000))
    scale = max(min(h, w) / 2048.0, 0.25)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    ca, sa = float(np.cos(np.deg2rad(30.0))), float(np.sin(np.deg2rad(30.0)))
    u = xx * ca + yy * sa

    # Base FBM
    bM = _normalize(multi_scale_noise(shape, [3.0, 8.0, 18.0], [0.5, 0.3, 0.2], int(seed) + 311))
    bR = _normalize(multi_scale_noise(shape, [3.0, 8.0, 18.0], [0.5, 0.3, 0.2], int(seed) + 312))
    bC = _normalize(multi_scale_noise(shape, [3.0, 8.0, 18.0], [0.5, 0.3, 0.2], int(seed) + 313))

    # Ribbon pitch — tighter to be finer per owner doctrine
    pitch = max(10.0, 12.0 * scale)
    band_idx = np.floor(u / pitch).astype(np.int32)
    # Large continuous table per band — no 8-tier hashing
    TABLE = 4096
    bM_table = rng.uniform(0.10, 0.95, TABLE).astype(np.float32)
    bR_table = rng.uniform(0.08, 0.92, TABLE).astype(np.float32)
    bC_table = rng.uniform(0.08, 0.95, TABLE).astype(np.float32)
    hidx = ((band_idx * 73856093) ^ int(seed) * 83492791) & (TABLE - 1)
    M = bM_table[hidx]
    R = bR_table[hidx]
    CC = bC_table[hidx]
    # blend small FBM substrate variation
    M = np.clip(M + (bM - 0.5) * 0.10, 0, 1)
    R = np.clip(R + (bR - 0.5) * 0.10, 0, 1)
    CC = np.clip(CC + (bC - 0.5) * 0.10, 0, 1)

    # GROUT — sharp shadow at ribbon edges
    edge_d = np.abs((u % pitch) - pitch * 0.5)
    grout = np.clip(1.0 - edge_d / (pitch * 0.10), 0, 1)
    M = M * (1.0 - grout * 0.55)
    R = np.clip(R + grout * 0.30, 0, 1)
    CC = CC * (1.0 - grout * 0.45) + grout * 0.85

    # GLINT FLECKS — vectorized, 3x density
    n_fl = max(4500, int(h * w / 300))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.55, 0.98, n_fl).astype(np.float32))
    R[fy, fx] = np.minimum(R[fy, fx], rng.uniform(0.05, 0.28, n_fl).astype(np.float32))
    CC[fy, fx] = np.minimum(CC[fy, fx], rng.uniform(0.04, 0.30, n_fl).astype(np.float32))

    if _CV2_OK:
        # SCRATCH HAIRLINES — 5x density along stripe direction
        n_str = int(np.clip(2400 * (min(h, w) / 2048.0) ** 2, 900, 6500))
        for _ in range(n_str):
            cx = float(rng.uniform(6, w - 6)); cy = float(rng.uniform(6, h - 6))
            length = float(rng.uniform(8.0, 18.0) * scale)
            ang = float(np.deg2rad(30.0)) + float(rng.normal(0.0, 0.06))
            x0s = int(cx - np.cos(ang) * length * 0.5); y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5); y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.18, 0.92)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.10, 0.85)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.10, 0.92)), 1, lineType=_cv2.LINE_AA)

        # CROSS-RIBBON DOT NICKS — small bright dots breaking band boredom
        n_dot = int(np.clip(900 * (min(h, w) / 2048.0) ** 2, 320, 2700))
        for _ in range(n_dot):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1.0, 2.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.60, 0.95)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.06, 0.28)), -1, lineType=_cv2.LINE_AA)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
diagonal_bands._spb_concept_complete = True
'''

# ---------------------------------------------------------------------------
# diffraction_grating — multi-zone CD/DVD ruling. Tighter 8-12 px pitch.
# Per-zone independent continuous chroma. 5x fleck density.
# ---------------------------------------------------------------------------
REBUILDS['diffraction_grating'] = '''def diffraction_grating(shape, seed, sm, line_freq=80.0, num_orders=5, **kwargs):
    """diffraction_grating.

    identity: A 4-zone CD/DVD diffractive surface — each zone rules at a
    different angle and fine 6-12 px pitch, with high-contrast bright land /
    dark groove M-R inversion, dense per-fleck continuous M/R/CC pinpoints
    scattered between, and many short CD-track arc segments crossing zone
    boundaries. No 8-tier palette — every zone bias and fleck pulls
    continuous uniforms.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("diffraction_grating_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]

    fbm_M = _normalize(multi_scale_noise(shape, [4.0, 10.0, 22.0], [0.5, 0.32, 0.18], int(seed) + 30510))
    fbm_R = _normalize(multi_scale_noise(shape, [4.0, 10.0, 22.0], [0.5, 0.32, 0.18], int(seed) + 30512))
    fbm_CC = _normalize(multi_scale_noise(shape, [4.0, 10.0, 22.0], [0.5, 0.32, 0.18], int(seed) + 30514))
    M = (0.50 + (fbm_M - 0.5) * 0.22).astype(np.float32)
    R_ch = (0.40 + (fbm_R - 0.5) * 0.22).astype(np.float32)
    CC = (0.42 + (fbm_CC - 0.5) * 0.22).astype(np.float32)

    zone_field = _normalize(multi_scale_noise(shape, [8.0, 18.0], [0.6, 0.4], int(seed) + 30520))
    zone_idx = (zone_field * 4.0).astype(np.int32)
    zone_angles = rng.uniform(0.0, np.pi, 4).astype(np.float32)
    zone_pitch = (rng.uniform(6.0, 12.0, 4) * scale).astype(np.float32)
    zone_phase = rng.uniform(0.0, 2 * np.pi, 4).astype(np.float32)
    zone_cc_bias = rng.uniform(0.10, 0.95, 4).astype(np.float32)
    zone_m_bias = rng.uniform(0.10, 0.95, 4).astype(np.float32)
    zone_r_bias = rng.uniform(0.08, 0.92, 4).astype(np.float32)
    for z in range(4):
        m = (zone_idx == z)
        if not np.any(m):
            continue
        a = float(zone_angles[z]); p = max(float(zone_pitch[z]), 2.0); ph = float(zone_phase[z])
        u = xx * np.cos(a) + yy * np.sin(a)
        groove = np.sin(u * (2.0 * np.pi / p) + ph)
        gs = np.power(np.clip(0.5 + groove * 0.5, 0.0, 1.0), 1.8)
        M = np.where(m, np.clip(0.08 + gs * 0.90 * float(zone_m_bias[z]) + (M - 0.5) * 0.12, 0, 1), M)
        R_ch = np.where(m, np.clip(0.88 - gs * 0.75 * float(zone_r_bias[z]) + (R_ch - 0.5) * 0.12, 0, 1), R_ch)
        CC = np.where(m, np.clip(0.18 + gs * 0.72 * float(zone_cc_bias[z]) + (CC - 0.5) * 0.12, 0, 1), CC)

    if _CV2_OK:
        # Pinpoint flecks — 3x density continuous uniforms
        n_fleck = max(6000, int(h * w / 25))
        fy = rng.integers(0, h, n_fleck); fx = rng.integers(0, w, n_fleck)
        bm = rng.uniform(0.08, 0.95, n_fleck).astype(np.float32)
        br = rng.uniform(0.06, 0.93, n_fleck).astype(np.float32)
        bc = rng.uniform(0.06, 0.96, n_fleck).astype(np.float32)
        M[fy, fx] = np.maximum(M[fy, fx], bm)
        R_ch[fy, fx] = np.minimum(R_ch[fy, fx], br)
        CC[fy, fx] = np.maximum(CC[fy, fx], bc)

        # CD-TRACK ARC SEGMENTS — many short 8-22 px
        n_arc = max(600, int(h * w / 1500))
        for _ in range(n_arc):
            cx = float(rng.uniform(2, w - 2)); cy = float(rng.uniform(2, h - 2))
            length = float(rng.uniform(8.0, 22.0) * scale)
            ang = float(rng.uniform(0, 2 * np.pi))
            x0s = int(cx - np.cos(ang) * length * 0.5)
            y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5)
            y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.10, 0.96)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.06, 0.92)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.08, 0.95)), 1, lineType=_cv2.LINE_AA)

    out = np.stack([M, R_ch, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
diffraction_grating._spb_concept_complete = True
'''

# ---------------------------------------------------------------------------
# decal_lift_edge — peel sticker borders. Up density 2x. Add CURLED EDGE
# arcs (8-16 px) as new differentiating tier.
# ---------------------------------------------------------------------------
REBUILDS['decal_lift_edge'] = '''def decal_lift_edge(shape, seed, sm, num_decals=4, edge_softness=0.004,
                    lift_strength=0.55, **kwargs):
    """decal_lift_edge.

    identity: A peeling sticker surface — many short axis-aligned bright
    rectangular edge ridges (10-22 px), curled corner arc fragments
    (8-14 px) at random rotations, dark adhesive specks under the lift,
    bright trapped-air bubble dots, short scratch slivers, plus a dense
    accent fleck layer. The CURLED EDGE arc is the new differentiator
    from a generic edge field. Per-feature INDEPENDENT continuous M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("decal_lift_edge_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    fM = _normalize(multi_scale_noise(shape, [1.5, 4.0, 11.0, 28.0], [0.35, 0.30, 0.22, 0.13], int(seed) + 9302))
    fR = _normalize(multi_scale_noise(shape, [1.5, 4.0, 11.0, 28.0], [0.35, 0.30, 0.22, 0.13], int(seed) + 9303))
    fCC = _normalize(multi_scale_noise(shape, [1.5, 4.0, 11.0, 28.0], [0.35, 0.30, 0.22, 0.13], int(seed) + 9304))
    M = (0.42 + (fM - 0.5) * 0.34).astype(np.float32)
    R_ch = (0.55 + (fR - 0.5) * 0.32).astype(np.float32)
    CC = (0.50 + (fCC - 0.5) * 0.32).astype(np.float32)

    if _CV2_OK:
        # 1) EDGE FRAGMENTS — 2x density
        n_edges = int(np.clip(1500 * (mn / 2048.0) ** 2, 540, 4500))
        for _ in range(n_edges):
            cx = float(rng.uniform(0.02, 0.98) * w); cy = float(rng.uniform(0.02, 0.98) * h)
            length = rng.uniform(10.0, 22.0) * scale
            ang_choice = int(rng.integers(0, 4))
            if ang_choice == 0:
                ang = float(rng.uniform(-0.15, 0.15))
            elif ang_choice == 1:
                ang = float(np.pi * 0.5 + rng.uniform(-0.15, 0.15))
            elif ang_choice == 2:
                ang = float(np.pi * 0.25 + rng.uniform(-0.08, 0.08))
            else:
                ang = float(-np.pi * 0.25 + rng.uniform(-0.08, 0.08))
            x2 = int(np.clip(cx + np.cos(ang) * length, 0, w - 1))
            y2 = int(np.clip(cy + np.sin(ang) * length, 0, h - 1))
            thick = max(1, int(scale * 1.5))
            _cv2.line(M, (int(cx), int(cy)), (x2, y2), float(rng.uniform(0.55, 0.95)), thick, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (int(cx), int(cy)), (x2, y2), float(rng.uniform(0.08, 0.32)), thick, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (int(cx), int(cy)), (x2, y2), float(rng.uniform(0.06, 0.35)), thick, lineType=_cv2.LINE_AA)

        # 2) CURLED CORNER ARCS — small arc fragments (differentiator)
        n_curls = int(np.clip(700 * (mn / 2048.0) ** 2, 240, 2200))
        for _ in range(n_curls):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(3, int(rng.uniform(4.0, 7.0) * scale))
            start_ang = int(rng.uniform(0, 360))
            sweep_ang = int(rng.uniform(60, 120))
            _cv2.ellipse(M, (cx, cy), (r, r), 0, start_ang, start_ang + sweep_ang, float(rng.uniform(0.60, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R_ch, (cx, cy), (r, r), 0, start_ang, start_ang + sweep_ang, float(rng.uniform(0.08, 0.30)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (r, r), 0, start_ang, start_ang + sweep_ang, float(rng.uniform(0.06, 0.32)), 1, lineType=_cv2.LINE_AA)

        # 3) ADHESIVE SPECKS — dark dots
        n_specks = int(np.clip(900 * (mn / 2048.0) ** 2, 320, 2700))
        for _ in range(n_specks):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(1, int(rng.uniform(1.0, 2.5) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.08, 0.32)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(rng.uniform(0.55, 0.92)), -1, lineType=_cv2.LINE_AA)

        # 4) BUBBLE DOTS — bright
        n_bubbles = int(np.clip(700 * (mn / 2048.0) ** 2, 240, 2200))
        for _ in range(n_bubbles):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(1, int(rng.uniform(1.5, 3.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.55, 0.95)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.05, 0.28)), -1, lineType=_cv2.LINE_AA)

        # 5) SHORT SCRATCH LINES
        n_scr = int(np.clip(600 * (mn / 2048.0) ** 2, 200, 1800))
        for _ in range(n_scr):
            cx = float(rng.uniform(4, w - 4)); cy = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(5.0, 10.0) * scale)
            ang = float(rng.uniform(0, 2 * np.pi))
            x0s = int(cx - np.cos(ang) * length * 0.5)
            y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5)
            y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(R_ch, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.10, 0.42)), 1, lineType=_cv2.LINE_AA)

    # 6) ACCENT FLECKS — vectorized
    n_flecks = int(np.clip(1500 * (mn / 2048.0) ** 2, 540, 4400))
    fx = rng.integers(0, w, n_flecks); fy = rng.integers(0, h, n_flecks)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(-0.25, 0.40, n_flecks).astype(np.float32), 0, 1)
    R_ch[fy, fx] = np.clip(R_ch[fy, fx] + rng.uniform(-0.20, 0.30, n_flecks).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.20, 0.30, n_flecks).astype(np.float32), 0, 1)

    out = np.stack([M, R_ch, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
decal_lift_edge._spb_concept_complete = True
'''

# ---------------------------------------------------------------------------
# drag_strip_burnout — race burnout. Pump streak + pit + chevron + pebble.
# Distinctive: tightly bunched DARK rubber smears (NOT just streaks like
# brushed_metal). Heavy near-horizontal density with sooty patches.
# ---------------------------------------------------------------------------
REBUILDS['drag_strip_burnout'] = '''def drag_strip_burnout(shape, seed, sm, **kwargs):
    """drag_strip_burnout.

    identity: A horizontal patch of laid rubber from a launch burnout —
    DENSE near-horizontal smear streaks (10-22 px) of variable soot
    brightness, dark grip pit dots where the contact patch grabbed
    pavement, crossed chevron tread imprint fragments (8-16 px), bright
    asphalt-aggregate pebble flecks poking through the rubber film, plus
    a low-freq sooty patch substrate (dark wash) that keeps the whole
    field gritty and not blank. Differentiator vs aniso_grain: rubber
    soot (high R, low M, dark wash), NOT polished metal.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("drag_strip_burnout_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) BASE — sooty asphalt FBM, independent M/R/CC
    bM = _normalize(multi_scale_noise(shape, [3.0, 9.0, 18.0], [0.45, 0.35, 0.20], int(seed) + 8801))
    bR = _normalize(multi_scale_noise(shape, [3.0, 9.0, 18.0], [0.45, 0.35, 0.20], int(seed) + 8802))
    bC = _normalize(multi_scale_noise(shape, [3.0, 9.0, 18.0], [0.45, 0.35, 0.20], int(seed) + 8803))
    # add sooty patch wash — large-scale dark blobs
    soot = _normalize(multi_scale_noise(shape, [14.0, 28.0], [0.6, 0.4], int(seed) + 8810))
    M = (0.25 + (bM - 0.5) * 0.22 - soot * 0.08).astype(np.float32)
    R = (0.74 + (bR - 0.5) * 0.22 + soot * 0.08).astype(np.float32)
    CC = (0.78 + (bC - 0.5) * 0.20 + soot * 0.06).astype(np.float32)
    np.clip(M, 0, 1, out=M); np.clip(R, 0, 1, out=R); np.clip(CC, 0, 1, out=CC)

    if _CV2_OK:
        # 2) HORIZONTAL SMEAR STREAKS — 3x density
        n_str = int(np.clip(2700 * (min(h, w) / 2048.0) ** 2, 900, 7000))
        for _ in range(n_str):
            cx = float(rng.uniform(4, w - 4)); cy = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(10.0, 22.0) * scale)
            ang = float(rng.normal(0.0, 0.08))  # near horizontal
            x0s = int(cx - np.cos(ang) * length * 0.5); y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5); y1s = int(cy + np.sin(ang) * length * 0.5)
            tw = int(rng.choice([1, 2]))
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.08, 0.40)), tw, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.58, 0.96)), tw, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.55, 0.94)), tw, lineType=_cv2.LINE_AA)

        # 3) GRIP PIT DOTS — 3x density
        n_pit = int(np.clip(1800 * (min(h, w) / 2048.0) ** 2, 600, 5400))
        for _ in range(n_pit):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1.5, 3.5) * scale * 0.5))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.04, 0.18)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.80, 0.98)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.78, 0.95)), -1, lineType=_cv2.LINE_AA)

        # 4) CHEVRON TREAD FRAGMENTS — 3x density
        n_tr = int(np.clip(1200 * (min(h, w) / 2048.0) ** 2, 420, 3600))
        for _ in range(n_tr):
            cx = float(rng.uniform(4, w - 4)); cy = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(8.0, 16.0) * scale)
            ang = float(rng.choice([0.6, -0.6])) + float(rng.normal(0.0, 0.10))
            x0s = int(cx - np.cos(ang) * length * 0.5); y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5); y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.15, 0.42)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.60, 0.88)), 1, lineType=_cv2.LINE_AA)

    # 5) PEBBLE FLECKS — bright asphalt pokes (vectorized, 3x density)
    n_pebble = max(4500, int(h * w / 250))
    fy = rng.integers(0, h, n_pebble); fx = rng.integers(0, w, n_pebble)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.42, 0.92, n_pebble).astype(np.float32))
    R[fy, fx] = np.minimum(R[fy, fx], rng.uniform(0.15, 0.44, n_pebble).astype(np.float32))
    CC[fy, fx] = np.minimum(CC[fy, fx], rng.uniform(0.20, 0.55, n_pebble).astype(np.float32))

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
drag_strip_burnout._spb_concept_complete = True
'''

# ---------------------------------------------------------------------------
# crayon_wax_resist — artistic family — needs density bump.
# ---------------------------------------------------------------------------
REBUILDS['crayon_wax_resist'] = '''def crayon_wax_resist(shape, seed, sm, rub_density=0.35, streak_len=0.12, **kwargs):
    """crayon_wax_resist.

    identity: A wax-crayon rubbing field — many short directional rub
    strokes (10-22 px) in faintly parallel clusters with multiple drift
    angles, dense darker wax-pile micro dabs (2-4 px), low-freq tooth-gap
    paper exposure, fine paper-fiber bright flecks, plus short crosshatch
    accent strokes for texture stack. Per-stroke INDEPENDENT continuous
    M/R/CC uniforms imitate crayon hue palette without 8-tier quantising.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("crayon_wax_resist_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) Paper-grain substrate
    fM = _normalize(multi_scale_noise(shape, [0.7, 1.8, 5.5, 18.0], [0.42, 0.30, 0.20, 0.08], int(seed) + 9721))
    fR = _normalize(multi_scale_noise(shape, [0.7, 1.8, 5.5, 18.0], [0.42, 0.30, 0.20, 0.08], int(seed) + 9722))
    fCC = _normalize(multi_scale_noise(shape, [0.7, 1.8, 5.5, 18.0], [0.42, 0.30, 0.20, 0.08], int(seed) + 9723))
    M = (0.40 + (fM - 0.5) * 0.20).astype(np.float32)
    R_ch = (0.60 + (fR - 0.5) * 0.20).astype(np.float32)
    CC = (0.50 + (fCC - 0.5) * 0.20).astype(np.float32)

    if _CV2_OK:
        # 2) RUB STROKES — 3x density, multiple drift angles
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

        # 3) WAX-PILE DABS — 3x density
        n_dabs = int(np.clip(800 * (mn / 2048.0) ** 2, 280, 2600))
        for _ in range(n_dabs):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1.5, 3.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.08, 0.42)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(rng.uniform(0.50, 0.92)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.30, 0.78)), -1, lineType=_cv2.LINE_AA)

        # 4) CROSSHATCH ACCENT STROKES — short crossed 5-10 px
        n_cross = int(np.clip(500 * (mn / 2048.0) ** 2, 180, 1500))
        for _ in range(n_cross):
            cx = float(rng.uniform(4, w - 4)); cy = float(rng.uniform(4, h - 4))
            length = float(rng.uniform(5.0, 10.0) * scale)
            ang = float(rng.choice([np.pi * 0.25, -np.pi * 0.25])) + float(rng.normal(0, 0.12))
            x0s = int(cx - np.cos(ang) * length * 0.5)
            y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5)
            y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.20, 0.82)), 1, lineType=_cv2.LINE_AA)

    # 5) TOOTH GAPS — paper exposure mask
    tooth = multi_scale_noise(shape, [1.0, 2.2], [0.55, 0.45], int(seed) + 9724)
    tooth_mask = (tooth > np.quantile(tooth, 0.84)).astype(np.float32)
    M = np.clip(M - tooth_mask * 0.22, 0, 1)
    R_ch = np.clip(R_ch + tooth_mask * 0.20, 0, 1)
    CC = np.clip(CC - tooth_mask * 0.15, 0, 1)

    # 6) PAPER FIBER FLECKS — vectorized 3x density
    n_flecks = int(np.clip(2000 * (mn / 2048.0) ** 2, 700, 5800))
    fx = rng.integers(0, w, n_flecks); fy = rng.integers(0, h, n_flecks)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.45, 0.88, n_flecks).astype(np.float32))
    R_ch[fy, fx] = np.clip(R_ch[fy, fx] + rng.uniform(-0.15, 0.20, n_flecks).astype(np.float32), 0, 1)

    out = np.stack([M, R_ch, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
crayon_wax_resist._spb_concept_complete = True
'''


if __name__ == '__main__':
    print(f"Loaded {len(REBUILDS)} rebuild bodies")
    for name in REBUILDS:
        print(f"  - {name}: {len(REBUILDS[name].splitlines())} lines")
