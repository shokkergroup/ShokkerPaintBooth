"""Mechanical spec pattern family for Shokker Paint Booth.

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

# MECHANICAL (6 patterns)
# ----------------------------------------------------------------------------

def exhaust_pipe_scorch(shape, seed, sm, num_vents=2, heat_radius=0.18,
                         **kwargs):
    """exhaust_pipe_scorch — R6 CREATIVE rebuild.

    identity: A scorched exhaust panel with vertical heat gradient AND
    HERO flame-tongue story. Top half is cool soot field; mid is blue-
    temper; lower is straw-yellow into red-bottom. HEROES: (1) FLAME-
    TONGUE ARCS — sparse 12-24 px curved bright streaks sweeping upward
    from the hot bottom (3-segment polyline arc, brightest at base
    fading toward tip), giving the panel the feel of LICK marks of fire
    that scorched the metal. (2) RUST-BUBBLE BLISTERS — irregular 4-8 px
    raised blobs where heat boiled the metal, with dark crater pits in
    the centers. Plus: hot-metal pinpoint carpet, temper discs (4-10 px),
    soot pock-clusters (2-5 px), oxide hairlines (4-12 px), and unburned
    aluminum flecks. Per-feature INDEPENDENT continuous M/R/CC uniforms.
    Reads as real temper coloring with flame story, not generic scatter.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 95117)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)
    yy_n = np.arange(h, dtype=np.float32).reshape(h, 1) / max(h - 1, 1)
    heat_grad = (yy_n ** 1.4).astype(np.float32)

    # 1) Substrate: heat-tinted with vertical band shift
    bM = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.5, 0.3, 0.2], int(seed) + 95121))
    bR = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.5, 0.3, 0.2], int(seed) + 95123))
    bC = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.5, 0.3, 0.2], int(seed) + 95125))
    # Heat-zone CC shift: cool/dull at top → hot/bright at bottom
    M = (0.42 + (bM - 0.5) * 0.22 + heat_grad * 0.20).astype(np.float32)
    R = (0.58 + (bR - 0.5) * 0.22 - heat_grad * 0.18).astype(np.float32)
    CC = (0.45 + (bC - 0.5) * 0.22 + heat_grad * 0.18).astype(np.float32)

    # 2) HOT-METAL PINPOINT CARPET — 5x density, bottom-biased
    n_hot_px = max(12000, int(h * w / 10))
    # bias toward bottom
    rand_y = (rng.random(n_hot_px) ** 0.55) * h
    hpy = rand_y.astype(np.int32)
    hpx = rng.integers(0, w, n_hot_px)
    M[hpy, hpx] = np.maximum(M[hpy, hpx], rng.uniform(0.65, 0.98, n_hot_px).astype(np.float32))
    R[hpy, hpx] = np.minimum(R[hpy, hpx], rng.uniform(0.10, 0.35, n_hot_px).astype(np.float32))
    CC[hpy, hpx] = np.maximum(CC[hpy, hpx], rng.uniform(0.40, 0.70, n_hot_px).astype(np.float32))

    if _CV2_OK:
        # 3) TEMPER DISCS — 4-10 px with continuous chroma uniforms
        n_hot = int(np.clip(2500 * (mn / 2048.0) ** 2, 850, 5500))
        for _ in range(n_hot):
            cx = int(rng.integers(0, w))
            cy_v = float(rng.random()) ** 0.5
            cy = int(np.clip(h * (0.30 + cy_v * 0.65), 0, h - 1))
            r = max(1, int(rng.uniform(2.0, 5.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.60, 0.97)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.10, 0.45)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.20, 0.65)), -1, lineType=_cv2.LINE_AA)

        # 4) SOOT POCK CLUSTERS — denser (2-5 px)
        n_soot = int(np.clip(2400 * (mn / 2048.0) ** 2, 850, 5200))
        for _ in range(n_soot):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1.0, 3.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.05, 0.20)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.78, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.70, 0.92)), -1, lineType=_cv2.LINE_AA)

        # 5) OXIDE HAIRLINES — 4-12 px curling lines
        n_ox = int(np.clip(1500 * (mn / 2048.0) ** 2, 500, 3500))
        for _ in range(n_ox):
            cx = float(rng.uniform(2, w - 2)); cy = float(rng.uniform(2, h - 2))
            length = float(rng.uniform(4.0, 12.0) * scale)
            ang = float(rng.uniform(0, 2 * np.pi))
            x0s = int(cx - np.cos(ang) * length * 0.5); y0s = int(cy - np.sin(ang) * length * 0.5)
            x1s = int(cx + np.cos(ang) * length * 0.5); y1s = int(cy + np.sin(ang) * length * 0.5)
            _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.30, 0.65)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.30, 0.60)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.30, 0.65)), 1, lineType=_cv2.LINE_AA)

        # 6) HERO: FLAME-TONGUE ARCS — curved bright streaks sweeping upward from bottom
        n_flame = int(np.clip(900 * (mn / 2048.0) ** 2, 320, 2400))
        for _ in range(n_flame):
            # base point biased bottom 60%
            base_x = float(rng.uniform(2, w - 2))
            base_y = float(rng.uniform(h * 0.40, h - 4))
            # tongue length & curvature
            length = float(rng.uniform(12.0, 24.0) * scale)
            curve = float(rng.uniform(-0.45, 0.45))
            # 3-segment polyline curving upward
            seg_len = length / 3.0
            ang0 = -np.pi * 0.5 + float(rng.normal(0, 0.30))
            pts = [(base_x, base_y)]
            cur_x, cur_y, cur_a = base_x, base_y, ang0
            for s in range(3):
                cur_a = cur_a + curve * 0.4
                cur_x = cur_x + np.cos(cur_a) * seg_len
                cur_y = cur_y + np.sin(cur_a) * seg_len
                pts.append((cur_x, cur_y))
            # draw with brightness fading along
            for s in range(len(pts) - 1):
                t = s / max(len(pts) - 2, 1)
                bright = 1.0 - t * 0.55
                _cv2.line(M,
                          (int(pts[s][0]), int(pts[s][1])),
                          (int(pts[s + 1][0]), int(pts[s + 1][1])),
                          float(rng.uniform(0.55, 0.95)) * bright, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R,
                          (int(pts[s][0]), int(pts[s][1])),
                          (int(pts[s + 1][0]), int(pts[s + 1][1])),
                          float(rng.uniform(0.10, 0.32)) * (1.0 + (1 - bright) * 0.5), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC,
                          (int(pts[s][0]), int(pts[s][1])),
                          (int(pts[s + 1][0]), int(pts[s + 1][1])),
                          float(rng.uniform(0.40, 0.80)) * bright, 1, lineType=_cv2.LINE_AA)

        # 7) HERO: RUST-BUBBLE BLISTERS — irregular raised blobs with dark crater pit
        n_blist = int(np.clip(500 * (mn / 2048.0) ** 2, 180, 1400))
        for _ in range(n_blist):
            cx = int(rng.uniform(4, w - 4))
            cy_v = float(rng.random()) ** 0.7
            cy = int(np.clip(h * (0.30 + cy_v * 0.65), 0, h - 1))
            r_b = max(2, int(rng.uniform(3.0, 5.0) * scale))
            ax = max(2, int(r_b * rng.uniform(0.7, 1.4)))
            ay = max(2, int(r_b * rng.uniform(0.7, 1.4)))
            ang_deg = float(rng.uniform(0, 360))
            # Bubble dome (rust-bronze color)
            _cv2.ellipse(M, (cx, cy), (ax, ay), ang_deg, 0, 360, float(rng.uniform(0.32, 0.62)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (cx, cy), (ax, ay), ang_deg, 0, 360, float(rng.uniform(0.50, 0.80)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (ax, ay), ang_deg, 0, 360, float(rng.uniform(0.30, 0.62)), -1, lineType=_cv2.LINE_AA)
            # Dark crater pit in center
            _cv2.circle(M, (cx, cy), max(1, ax // 3), float(rng.uniform(0.05, 0.18)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), max(1, ax // 3), float(rng.uniform(0.78, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), max(1, ax // 3), float(rng.uniform(0.68, 0.90)), -1, lineType=_cv2.LINE_AA)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)

exhaust_pipe_scorch._spb_concept_complete = True


def radiator_grille_mesh(shape, seed=0, sm=1.0, **kwargs):
    """radiator_grille_mesh — R6 CREATIVE rebuild.

    identity: A premium 3D-stamped automotive grille — HORIZONTAL CHROME
    SLATS (10-14 px pitch) running across the canvas, each slat with a
    bright top edge, a darker bottom shadow, and a soft midline highlight
    where the chrome catches light (classic 3-tone slat profile). HERO:
    every 5th slat is a wider, brighter STATEMENT BAR with embossed bezel
    edges. Between slats: dark RECESSED VOIDS reading as the radiator
    behind the grille, peppered with hex-mesh background dots (2-3 px,
    organized in a finer secondary grid). Layered on top: short BRIGHT
    BOLT-NODE rivets (2-4 px) at slat ends, micro-grit fleck carpet,
    chrome-polish scuff arcs (4-8 px), and a few stress hairline cracks.
    Per-feature INDEPENDENT continuous M/R/CC for chroma variety.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("radiator_grille_mesh_r6") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)
    yy = np.arange(h, dtype=np.float32)[:, None]; xx = np.arange(w, dtype=np.float32)[None, :]

    # 1) HORIZONTAL SLAT PROFILE — period 10-14 px, 3-tone shading
    slat_period = max(10.0, 12.0 * scale)
    phase_y = yy / slat_period
    slat_idx = np.floor(phase_y).astype(np.int32)
    frac = phase_y - slat_idx.astype(np.float32)  # 0..1 across one slat
    # 3-tone profile:
    #   0.00-0.25 -> bright top edge
    #   0.25-0.55 -> midline soft highlight
    #   0.55-1.00 -> deep shadow void
    top_edge = np.exp(-((frac - 0.05) ** 2) / (2.0 * 0.025))
    midline = np.exp(-((frac - 0.40) ** 2) / (2.0 * 0.020))
    void_mask = np.clip((frac - 0.62) / 0.30, 0.0, 1.0)
    void_mask = void_mask * void_mask * (3.0 - 2.0 * void_mask)

    # Every 5th slat = statement bar (wider influence + extra glow)
    is_statement = ((slat_idx % 5) == 0).astype(np.float32)
    statement_glow = midline * is_statement

    # 2) PER-SLAT CHROMA TINT (Weyl)
    seed64 = np.uint64(int(seed) & 0xFFFFFFFF)
    slat64 = (slat_idx.astype(np.uint64) & np.uint64(0xFFFFFFFF))
    hsh = (slat64 * np.uint64(0x9E3779B1)) ^ seed64
    tint_M = ((hsh * np.uint64(2654435761)) & np.uint64(0xFFFFFF)).astype(np.float32) / float(0xFFFFFF)
    tint_R = ((hsh * np.uint64(1597334677)) & np.uint64(0xFFFFFF)).astype(np.float32) / float(0xFFFFFF)
    tint_C = ((hsh * np.uint64(374761393)) & np.uint64(0xFFFFFF)).astype(np.float32) / float(0xFFFFFF)

    # 3) FBM grain (independent M/R/CC)
    g1 = _normalize(multi_scale_noise(shape, [3.0, 7.0, 14.0], [0.42, 0.32, 0.26], seed + 801))
    g2 = _normalize(multi_scale_noise(shape, [4.0, 8.5, 17.0], [0.38, 0.32, 0.30], seed + 802))
    g3 = _normalize(multi_scale_noise(shape, [3.5, 7.5, 15.0], [0.40, 0.32, 0.28], seed + 803))

    # R6-loop tick (owner 6/KEEP refinement): substrate cooled to keep mean M
    # well below 0.45 cap. Bright chrome highlights remain bright via features;
    # global field reads as a darker chrome-on-shadow grille instead of magenta-leaning.
    M  = (0.12 + top_edge * 0.42 + midline * 0.30 + statement_glow * 0.14
          - void_mask * 0.14 + (tint_M - 0.5) * 0.14 + (g1 - 0.5) * 0.10).astype(np.float32)
    R  = (0.52 - top_edge * 0.30 - midline * 0.22 - statement_glow * 0.10
          + void_mask * 0.18 + (tint_R - 0.5) * 0.12 + (g2 - 0.5) * 0.12).astype(np.float32)
    CC = (0.36 - top_edge * 0.26 - midline * 0.16 + void_mask * 0.22
          + (tint_C - 0.5) * 0.16 + (g3 - 0.5) * 0.14).astype(np.float32)

    # 4) HEX-MESH BACKGROUND DOTS — fine secondary subgrid, visible inside void zones
    sub_sp = max(5.0, 6.5 * scale)
    sub_row = np.floor(yy / sub_sp).astype(np.int32)
    sub_col = np.floor((xx - (sub_row & 1) * sub_sp * 0.5) / sub_sp).astype(np.int32)
    sub_cx = (sub_col + 0.5) * sub_sp + (sub_row & 1) * sub_sp * 0.5
    sub_cy = (sub_row + 0.5) * sub_sp
    sub_d = np.sqrt((xx - sub_cx) ** 2 + (yy - sub_cy) ** 2)
    sub_mask = np.exp(-(sub_d ** 2) / (2.0 * (sub_sp * 0.18) ** 2)) * void_mask
    M = M - sub_mask * 0.30
    R = R + sub_mask * 0.22

    if _CV2_OK:
        # 5) BRIGHT BOLT-NODE rivets at slat ends (2-4 px)
        n_bolt = int(np.clip(900 * (mn / 2048.0) ** 2, 320, 2400))
        for _ in range(n_bolt):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(2.0, 4.0) * scale * 0.5))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.72, 0.98)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.05, 0.22)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.04, 0.22)), -1, lineType=_cv2.LINE_AA)

        # 6) CHROME-POLISH SCUFF arcs (4-8 px)
        n_scuff = int(np.clip(1400 * (mn / 2048.0) ** 2, 500, 3600))
        for _ in range(n_scuff):
            cx = float(rng.uniform(2, w - 2)); cy = float(rng.uniform(2, h - 2))
            length = float(rng.uniform(4.0, 8.0) * scale)
            ang = float(rng.uniform(-0.35, 0.35))  # mostly horizontal
            x2 = int(cx + np.cos(ang) * length); y2 = int(cy + np.sin(ang) * length)
            _cv2.line(M, (int(cx), int(cy)), (x2, y2), float(rng.uniform(0.50, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (int(cx), int(cy)), (x2, y2), float(rng.uniform(0.08, 0.30)), 1, lineType=_cv2.LINE_AA)

        # 7) STRESS HAIRLINE cracks — a few short jagged fractures
        n_crack = int(np.clip(60 * (mn / 1024.0), 20, 160))
        for _ in range(n_crack):
            cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
            n_seg = int(rng.integers(2, 5))
            for s in range(n_seg):
                ang = float(rng.uniform(0, 2 * np.pi))
                length = float(rng.uniform(3.0, 7.0) * scale)
                x2 = int(cx + np.cos(ang) * length); y2 = int(cy + np.sin(ang) * length)
                _cv2.line(M, (int(cx), int(cy)), (x2, y2), float(rng.uniform(0.10, 0.32)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (int(cx), int(cy)), (x2, y2), float(rng.uniform(0.55, 0.88)), 1, lineType=_cv2.LINE_AA)
                cx, cy = x2, y2

    # 8) MICRO-GRIT carpet (vectorized)
    n_fl = int(np.clip(1800 * (mn / 2048.0) ** 2, 600, 4000))
    fx = rng.integers(0, w, n_fl); fy = rng.integers(0, h, n_fl)
    M[fy, fx] = rng.uniform(0.15, 0.92, n_fl).astype(np.float32)
    R[fy, fx] = rng.uniform(0.10, 0.85, n_fl).astype(np.float32)
    CC[fy, fx] = rng.uniform(0.06, 0.80, n_fl).astype(np.float32)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm).astype(np.float32), "radiator_grille_mesh")
radiator_grille_mesh._spb_concept_complete = True


def engine_bay_grime(shape, seed, sm, buildup=0.55, **kwargs):
    """engine_bay_grime — R6 GOTHIC rebuild (owner 2/REBUILD).

    Owner directive: "TURN THIS INTO A GOTHIC STYLE FINISH WE DON'T
    CURRENTLY HAVE." Identity REPURPOSED — name kept for catalog
    stability but the visual is now CATHEDRAL GOTHIC TRACERY:

    HERO: pointed-arch GOTHIC WINDOWS (lancets, 16-28 px tall) packed
    across the canvas like cathedral facade tracery. Each lancet is a
    bright-leaded outline with a vertical mullion and a small ROSE
    quatrefoil at the apex. Filling between: stylized FLEUR-DE-LIS
    motifs (12-20 px), pointed CROSS-PATTÉE pendants (8-14 px),
    candle-soot bleed halos, and tiny iron NAIL studs marching the
    seams. Per-feature INDEPENDENT continuous M/R/CC TIGHT-jittered
    from a single midnight-iron palette (deep slate base, leaded
    silver lines, faint blue verre-cathédrale gleam). Composite-dark
    substrate. No noise haze — every pixel has architecture.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 88012)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)
    s = max(mn / 256.0, 0.6)

    # 1) BASE — composite-dark slate (midnight iron) so leaded silver pops
    bM = _normalize(multi_scale_noise(shape, [3.0, 8.0, 18.0], [0.45, 0.32, 0.23], int(seed) + 9524))
    bR = _normalize(multi_scale_noise(shape, [3.5, 9.0, 20.0], [0.45, 0.32, 0.23], int(seed) + 9525))
    bC = _normalize(multi_scale_noise(shape, [4.0, 10.0, 22.0], [0.45, 0.32, 0.23], int(seed) + 9526))
    # composite-DARK substrate: M=0.10, R=0.12, CC=0.08 (deep cathedral shadow)
    M = (0.10 + (bM - 0.5) * 0.05).astype(np.float32)
    R = (0.12 + (bR - 0.5) * 0.05).astype(np.float32)
    CC = (0.08 + (bC - 0.5) * 0.04).astype(np.float32)
    # Gothic palette base (leaded silver tracery)
    L_M, L_R, L_C = 0.78, 0.22, 0.50  # leaded silver
    G_M, G_R, G_C = 0.36, 0.30, 0.62  # cathedral-glass blue gleam

    if _CV2_OK:
        # 2) HERO: pointed-arch GOTHIC LANCETS — brick-staggered grid across canvas
        lancet_w = max(8, int(10 * s))  # arch width 10-20 px
        lancet_h = int(lancet_w * 2.0)   # arch height
        step_x = int(lancet_w * 1.10)
        step_y = int(lancet_h * 0.95)
        for row_i, ly in enumerate(range(2, h - lancet_h, step_y)):
            row_off = (lancet_w // 2) if (row_i % 2 == 1) else 0
            for lx in range(2 + row_off, w - lancet_w, step_x):
                cx = lx + lancet_w // 2 + int(rng.integers(-1, 2))
                # bottom of lancet
                ybot = min(h - 1, ly + lancet_h)
                ytop = ly
                wh = lancet_w // 2  # half-width
                # Per-lancet TIGHT jitter around leaded silver base
                aM = float(np.clip(L_M + rng.uniform(-0.05, 0.05), 0, 1))
                aR = float(np.clip(L_R + rng.uniform(-0.04, 0.04), 0, 1))
                aC = float(np.clip(L_C + rng.uniform(-0.05, 0.05), 0, 1))
                # Glass tint inside lancet
                gM = float(np.clip(G_M + rng.uniform(-0.05, 0.05), 0, 1))
                gR = float(np.clip(G_R + rng.uniform(-0.04, 0.04), 0, 1))
                gC = float(np.clip(G_C + rng.uniform(-0.05, 0.05), 0, 1))
                # Fill glass interior — straight sides
                shaft_top = ytop + wh  # below the arch start
                if shaft_top < ybot:
                    _cv2.rectangle(M, (cx - wh + 1, shaft_top), (cx + wh - 1, ybot), gM, -1, lineType=_cv2.LINE_AA)
                    _cv2.rectangle(R, (cx - wh + 1, shaft_top), (cx + wh - 1, ybot), gR, -1, lineType=_cv2.LINE_AA)
                    _cv2.rectangle(CC, (cx - wh + 1, shaft_top), (cx + wh - 1, ybot), gC, -1, lineType=_cv2.LINE_AA)
                # Pointed-arch top (two ellipse arcs meeting at apex)
                # Left arc: center at (cx+wh, ytop+wh), radius wh, sweep from 180 to 270
                _cv2.ellipse(M, (cx + wh, ytop + wh), (wh, wh), 0, 180, 270, gM, -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx + wh, ytop + wh), (wh, wh), 0, 180, 270, gR, -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx + wh, ytop + wh), (wh, wh), 0, 180, 270, gC, -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx - wh, ytop + wh), (wh, wh), 0, 270, 360, gM, -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx - wh, ytop + wh), (wh, wh), 0, 270, 360, gR, -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx - wh, ytop + wh), (wh, wh), 0, 270, 360, gC, -1, lineType=_cv2.LINE_AA)
                # Leaded outline — bright silver tracery (1px)
                # Side jambs
                _cv2.line(M, (cx - wh, shaft_top), (cx - wh, ybot), aM, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx + wh, shaft_top), (cx + wh, ybot), aM, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx - wh, shaft_top), (cx - wh, ybot), aR, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx + wh, shaft_top), (cx + wh, ybot), aR, 1, lineType=_cv2.LINE_AA)
                # Arch outline
                _cv2.ellipse(M, (cx + wh, ytop + wh), (wh, wh), 0, 180, 270, aM, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(M, (cx - wh, ytop + wh), (wh, wh), 0, 270, 360, aM, 1, lineType=_cv2.LINE_AA)
                # Central MULLION (vertical bright line down middle)
                _cv2.line(M, (cx, shaft_top), (cx, ybot - 1), float(np.clip(aM + 0.08, 0, 1)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx, shaft_top), (cx, ybot - 1), float(np.clip(aC + 0.10, 0, 1)), 1, lineType=_cv2.LINE_AA)
                # ROSE quatrefoil at apex (tiny 4-lobe ring)
                rose_r = max(1, lancet_w // 6)
                _cv2.circle(M, (cx, ytop + max(1, lancet_w // 4)), rose_r,
                            float(np.clip(aM + 0.10, 0, 1)), 1, lineType=_cv2.LINE_AA)
                # bottom sill highlight
                _cv2.line(M, (cx - wh, ybot), (cx + wh, ybot), float(np.clip(aM + 0.05, 0, 1)), 1, lineType=_cv2.LINE_AA)

        # 3) FLEUR-DE-LIS motifs scattered in gaps — 12-20 px
        n_fleur = int(np.clip(60 * s * s, 30, 130))
        for _ in range(n_fleur):
            fx = int(rng.integers(8, w - 8))
            fy = int(rng.integers(8, h - 8))
            fr = max(4, int(rng.uniform(5, 9) * (s * 0.8 + 0.2)))
            fr = min(fr, 10)
            fM = float(np.clip(L_M + rng.uniform(-0.06, 0.06), 0, 1))
            fC = float(np.clip(L_C + rng.uniform(-0.05, 0.05), 0, 1))
            # central petal (tall ellipse)
            _cv2.ellipse(M, (fx, fy), (max(1, fr // 3), fr), 0, 0, 360, fM, 1, lineType=_cv2.LINE_AA)
            # side petals (curved)
            _cv2.ellipse(M, (fx - fr // 2, fy), (fr // 2, fr - 1), -25, 90, 270, fM, 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(M, (fx + fr // 2, fy), (fr // 2, fr - 1), 25, 270, 450, fM, 1, lineType=_cv2.LINE_AA)
            # waistband
            _cv2.line(M, (fx - fr, fy + fr // 3), (fx + fr, fy + fr // 3), fM, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (fx - fr, fy + fr // 3), (fx + fr, fy + fr // 3), fC, 1, lineType=_cv2.LINE_AA)

        # 4) CROSS-PATTÉE pendants (8-14 px) — bright equal-armed crosses with flared ends
        n_cross = int(np.clip(80 * s * s, 40, 200))
        for _ in range(n_cross):
            cx = int(rng.integers(4, w - 4))
            cy = int(rng.integers(4, h - 4))
            r = max(3, int(rng.uniform(4, 7) * (s * 0.7 + 0.3)))
            r = min(r, 7)
            xM = float(np.clip(L_M + rng.uniform(-0.04, 0.06), 0, 1))
            xC = float(np.clip(L_C + rng.uniform(-0.04, 0.06), 0, 1))
            _cv2.line(M, (cx - r, cy), (cx + r, cy), xM, 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, (cx, cy - r), (cx, cy + r), xM, 1, lineType=_cv2.LINE_AA)
            # flared ends (small perpendicular caps)
            for sign in (-1, 1):
                _cv2.line(M, (cx + sign * r, cy - 1), (cx + sign * r, cy + 1), xM, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx - 1, cy + sign * r), (cx + 1, cy + sign * r), xM, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), 1, xC, -1, lineType=_cv2.LINE_AA)

        # 5) IRON NAIL studs marching along vertical seams (every step_x)
        n_nail = int(np.clip(200 * s * s, 80, 400))
        for _ in range(n_nail):
            nx = int(rng.integers(2, w - 2))
            ny = int(rng.integers(2, h - 2))
            nM = float(np.clip(L_M + rng.uniform(-0.05, 0.10), 0, 1))
            _cv2.circle(M, (nx, ny), 1, nM, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (nx, ny), 1, float(np.clip(L_R + 0.08, 0, 1)), -1, lineType=_cv2.LINE_AA)

        # 6) CANDLE-SOOT bleed halos — faint dark blooms (sparse)
        n_soot = int(np.clip(18 * s * s, 8, 36))
        for _ in range(n_soot):
            sx = int(rng.integers(8, w - 8))
            sy = int(rng.integers(8, h - 8))
            sr = int(rng.uniform(6, 12) * s)
            sr = min(sr, 14)
            ttype = max(1, sr // 2)
            tyy, txx = np.mgrid[max(0, sy - sr):min(h, sy + sr + 1), max(0, sx - sr):min(w, sx + sr + 1)].astype(np.float32)
            d2 = ((txx - sx) ** 2 + (tyy - sy) ** 2) / (sr * sr + 1e-6)
            alpha = np.exp(-d2 * 2.0) * 0.18
            ys, ye = max(0, sy - sr), min(h, sy + sr + 1)
            xs, xe = max(0, sx - sr), min(w, sx + sr + 1)
            M[ys:ye, xs:xe] = np.clip(M[ys:ye, xs:xe] * (1.0 - alpha), 0, 1)
            CC[ys:ye, xs:xe] = np.clip(CC[ys:ye, xs:xe] * (1.0 - alpha * 0.6), 0, 1)

    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
engine_bay_grime._spb_concept_complete = True


def tire_smoke_streaks(shape, seed, sm, num_streaks=14, taper=0.35, **kwargs):
    """tire_smoke_streaks — R6 CREATIVE rebuild.

    identity: A burnout-line story rendered as DIRECTIONAL SMOKE LAYERS
    with dramatic motion. HEROES: (1) BLACK RUBBER LAY-DOWN STRIPES —
    8-14 thick darker bands running edge-to-edge along the master tire
    direction, the namesake racing stripe the tire left as it dragged.
    (2) BURNOUT FLAMETIP CURL — at the trailing end of each stripe, the
    smoke curls upward in small organic crescents (5-12 px C-arc), like
    a wisp lifting off hot rubber. Light-grey directional WISPS (50-130
    px long, all parallel to master) fill the middle field. Plus: bright
    HOT-RUBBER FLECKS (sparse warm-tinted glints), CHEMICAL-BURN SCORCH
    spots (darker irregular blots), and ash-pinpoint fleck carpet. Per-
    feature INDEPENDENT continuous M/R/CC; smoke chroma varies cool-to-
    warm so the field does not read as one flat grey. Seven stacked tiers.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 60281)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) Sooty asphalt substrate
    fM = _normalize(multi_scale_noise(shape, [3.0, 7.0, 14.0], [0.45, 0.32, 0.23], int(seed) + 9531))
    fR = _normalize(multi_scale_noise(shape, [3.5, 8.0, 16.0], [0.45, 0.32, 0.23], int(seed) + 9533))
    fCC = _normalize(multi_scale_noise(shape, [4.0, 9.0, 18.0], [0.45, 0.32, 0.23], int(seed) + 9535))
    M = (0.32 + (fM - 0.5) * 0.22).astype(np.float32)
    R_ch = (0.66 + (fR - 0.5) * 0.22).astype(np.float32)
    CC = (0.62 + (fCC - 0.5) * 0.22).astype(np.float32)

    master_ang = float(rng.uniform(-0.18, 0.18))
    cos_m = float(np.cos(master_ang)); sin_m = float(np.sin(master_ang))

    if _CV2_OK:
        # 2) HERO: BLACK RUBBER LAY-DOWN STRIPES — thick edge-to-edge bands
        n_stripes = int(rng.integers(8, 15))
        stripe_ys = []
        for _ in range(n_stripes):
            sy = float(rng.uniform(0.05, 0.95) * h)
            stripe_ys.append(sy)
            x1 = -10
            y1 = int(np.clip(sy - sin_m * 10.0, 0, h - 1))
            x2 = w + 10
            y2 = int(np.clip(sy + sin_m * (w + 10.0), 0, h - 1))
            stripe_thick = max(2, int(rng.uniform(3.0, 6.5) * scale))
            _cv2.line(M, (x1, y1), (x2, y2), float(rng.uniform(0.06, 0.22)), stripe_thick, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (x1, y1), (x2, y2), float(rng.uniform(0.82, 0.97)), stripe_thick, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x1, y1), (x2, y2), float(rng.uniform(0.74, 0.92)), stripe_thick, lineType=_cv2.LINE_AA)

        # 3) BURNOUT FLAMETIP CURLS — wisp lifts at trailing end of each stripe
        for sy in stripe_ys:
            n_curls = int(rng.integers(3, 8))
            for _ in range(n_curls):
                tx = float(rng.uniform(0.1, 0.9) * w)
                ty = sy + float(rng.uniform(-2.0, 2.0))
                curl_size = float(rng.uniform(5.0, 12.0) * scale)
                a0 = float(rng.uniform(-110, -40))
                a1 = a0 + float(rng.uniform(60, 140))
                _cv2.ellipse(M, (int(tx), int(ty)), (max(1, int(curl_size)), max(1, int(curl_size * 0.6))), 0,
                             a0, a1, float(rng.uniform(0.55, 0.82)), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R_ch, (int(tx), int(ty)), (max(1, int(curl_size)), max(1, int(curl_size * 0.6))), 0,
                             a0, a1, float(rng.uniform(0.70, 0.92)), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (int(tx), int(ty)), (max(1, int(curl_size)), max(1, int(curl_size * 0.6))), 0,
                             a0, a1, float(rng.uniform(0.55, 0.88)), 1, lineType=_cv2.LINE_AA)

        # 4) LONG DIRECTIONAL WISPS — light grey smoke
        n_long = int(np.clip(480 * (mn / 2048.0), 160, 1000))
        for _ in range(n_long):
            cx = rng.uniform(0.0, 1.0) * w; cy = rng.uniform(0.02, 0.98) * h
            length = float(rng.uniform(50.0, 130.0) * scale)
            jitter = float(rng.uniform(-0.14, 0.14))
            ang = master_ang + jitter
            x1 = int(np.clip(cx - np.cos(ang) * length * 0.5, 0, w - 1))
            y1 = int(np.clip(cy - np.sin(ang) * length * 0.5, 0, h - 1))
            x2 = int(np.clip(cx + np.cos(ang) * length * 0.5, 0, w - 1))
            y2 = int(np.clip(cy + np.sin(ang) * length * 0.5, 0, h - 1))
            thick = max(1, int(rng.uniform(1.0, 2.2) * scale))
            _cv2.line(M, (x1, y1), (x2, y2), float(rng.uniform(0.42, 0.72)), thick, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (x1, y1), (x2, y2), float(rng.uniform(0.78, 0.95)), thick, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (x1, y1), (x2, y2), float(rng.uniform(0.50, 0.92)), thick, lineType=_cv2.LINE_AA)

        # 5) MEDIUM ALIGNED WISPS — denser fill, 20-50 px
        n_med = int(np.clip(1100 * (mn / 2048.0) ** 2, 380, 2800))
        for _ in range(n_med):
            cx = rng.uniform(0.0, 1.0) * w; cy = rng.uniform(0.02, 0.98) * h
            length = float(rng.uniform(20.0, 50.0) * scale)
            ang = master_ang + float(rng.uniform(-0.20, 0.20))
            x2 = int(np.clip(cx + np.cos(ang) * length, 0, w - 1))
            y2 = int(np.clip(cy + np.sin(ang) * length, 0, h - 1))
            _cv2.line(M, (int(cx), int(cy)), (x2, y2), float(rng.uniform(0.45, 0.78)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (int(cx), int(cy)), (x2, y2), float(rng.uniform(0.72, 0.94)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (int(cx), int(cy)), (x2, y2), float(rng.uniform(0.50, 0.92)), 1, lineType=_cv2.LINE_AA)

        # 6) CHEMICAL-BURN SCORCH SPOTS — darker irregular blots
        n_scorch = int(np.clip(160 * (mn / 2048.0) ** 2, 50, 480))
        for _ in range(n_scorch):
            cx = int(rng.uniform(0.04, 0.96) * w); cy = int(rng.uniform(0.04, 0.96) * h)
            ax = max(2, int(rng.uniform(3.5, 7.0) * scale))
            ay = max(1, int(rng.uniform(2.0, 4.5) * scale))
            ang = float(rng.uniform(0, 360))
            _cv2.ellipse(M, (cx, cy), (ax, ay), ang, 0, 360, float(rng.uniform(0.08, 0.20)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R_ch, (cx, cy), (ax, ay), ang, 0, 360, float(rng.uniform(0.82, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy), (ax, ay), ang, 0, 360, float(rng.uniform(0.65, 0.88)), -1, lineType=_cv2.LINE_AA)

        # 7) HOT-RUBBER FLECKS — sparse warm-tinted glints
        n_hot = int(np.clip(550 * (mn / 2048.0) ** 2, 180, 1600))
        for _ in range(n_hot):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(1, int(rng.uniform(1.0, 2.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.55, 0.82)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(rng.uniform(0.30, 0.55)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.18, 0.42)), -1, lineType=_cv2.LINE_AA)

    # 8) Ash fleck pinpoints
    n_fl = int(np.clip(1100 * (mn / 2048.0) ** 2, 380, 3300))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.55, 0.85, n_fl).astype(np.float32))
    R_ch[fy, fx] = np.minimum(R_ch[fy, fx], rng.uniform(0.30, 0.55, n_fl).astype(np.float32))
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.12, 0.12, n_fl).astype(np.float32), 0, 1)

    # 9) R6-CREATIVE NEW: LISSAJOUS TIRE-DEBRIS ARCS � rubber chunks
    # ejected in tight 8-28 px math-curve loops (Lissajous x=A*sin(a*t+d),
    # y=B*sin(b*t)). 8-18 small arcs scattered above the burnout zone.
    # Each arc plotted as ~22 short polyline segs, per-arc INDEPENDENT
    # continuous M/R/CC. Goes weird without breaking the burnout identity.
    if _CV2_OK:
        n_liss = int(np.clip(14 * scale + 4, 6, 22))
        for _ in range(n_liss):
            cx = float(rng.uniform(0.05, 0.95) * w)
            cy = float(rng.uniform(0.05, 0.95) * h)
            A  = float(rng.uniform(4.0, 14.0) * scale)
            B  = float(rng.uniform(3.0, 12.0) * scale)
            a_f = float(rng.integers(2, 6))
            b_f = float(rng.integers(1, 5))
            delta = float(rng.uniform(0, np.pi))
            arcM  = float(rng.uniform(0.10, 0.78))
            arcR  = float(rng.uniform(0.55, 0.96))
            arcCC = float(rng.uniform(0.18, 0.82))
            n_seg = 22
            ts = np.linspace(0.0, 2.0 * np.pi, n_seg + 1, dtype=np.float32)
            xs = cx + A * np.sin(a_f * ts + delta)
            ys = cy + B * np.sin(b_f * ts)
            for k in range(n_seg):
                x0 = int(np.clip(xs[k], 0, w - 1)); y0 = int(np.clip(ys[k], 0, h - 1))
                x1 = int(np.clip(xs[k+1], 0, w - 1)); y1 = int(np.clip(ys[k+1], 0, h - 1))
                _cv2.line(M,    (x0, y0), (x1, y1),
                          float(np.clip(arcM  + rng.uniform(-0.06, 0.06), 0, 1)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R_ch, (x0, y0), (x1, y1),
                          float(np.clip(arcR  + rng.uniform(-0.05, 0.05), 0, 1)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC,   (x0, y0), (x1, y1),
                          float(np.clip(arcCC + rng.uniform(-0.06, 0.06), 0, 1)), 1, lineType=_cv2.LINE_AA)

    out = np.stack([np.clip(M, 0, 1), np.clip(R_ch, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)


tire_smoke_streaks._spb_concept_complete = True


def undercarriage_spray(shape, seed, sm, spray_density=0.0025,
                         fan_height=0.55, **kwargs):
    """undercarriage_spray — R6 tick-81 second-pass creative refinement.

    identity: R6 tick-50 second-pass — CAKED MUD CHUNKS WITH DIRECTIONAL
    SPRAY CONES, now stacked with NEW HERO. Original heroes: polygonal
    CLAY-MUD CHUNK GLOBS (6-14 px) each casting SPRAY CONE TAILS in a
    shared wind direction. HERO (tick-50): TIRE-TREAD STAMP
    IMPRINTS — short parallel rectangle clusters (12-22 px overall, 3-5
    blocks per stamp) pressed into the wet grime at random stamp
    orientations, each block with INDEPENDENT M/R/CC plus a bright
    squeeze-out fringe rim. Captures the literal undercarriage tread
    mark. Plus: wet-grime FBM substrate, micro-pebble gravel grit,
    salty-water bright beads, salt-flake pinpoints, long motion-blur
    streaks at the global wind angle. Per-feature INDEPENDENT
    continuous M/R/CC.

    TICK-81 SECOND-PASS HERO: TIRE SIDEWALL LETTERFORM ARCS — small
    curved chains of 4-8 thin rectangular "letter" stamps arrayed along
    a shallow arc (mimicking molded raised lettering on a tire sidewall
    pressed into mud). Each letter slot is 3-5 px wide x 5-8 px tall
    with INDEPENDENT M/R/CC plus a bright squeeze-out rim. Reads as
    literal POMP-style raised lettering left behind by a flexing tire.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 50229)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # global wind direction — same for all chunks so field reads as motion
    wind_angle = float(rng.uniform(-0.6, 0.6))  # mostly horizontal
    wdx = float(np.cos(wind_angle)); wdy = float(np.sin(wind_angle))

    # 1) WET-GRIME FBM SUBSTRATE
    fM = _normalize(multi_scale_noise(shape, [1.7, 4.5, 12.0, 28.0], [0.36, 0.30, 0.22, 0.12], int(seed) + 9551))
    fR = _normalize(multi_scale_noise(shape, [2.1, 6.4, 15.0, 30.0], [0.38, 0.30, 0.20, 0.12], int(seed) + 9553))
    fCC = _normalize(multi_scale_noise(shape, [2.6, 8.4, 18.0, 36.0], [0.40, 0.28, 0.20, 0.12], int(seed) + 9555))
    M = (0.40 + (fM - 0.5) * 0.30).astype(np.float32)
    R_ch = (0.62 + (fR - 0.5) * 0.30).astype(np.float32)
    CC = (0.55 + (fCC - 0.5) * 0.32).astype(np.float32)

    chunk_centers = []

    if _CV2_OK:
        # 2) MUD CHUNK GLOBS — irregular polygons 6-14 px
        n_chunks = int(np.clip(380 * (mn / 2048.0) ** 2, 130, 1100))
        for _ in range(n_chunks):
            cx = float(rng.uniform(0.04, 0.96) * w)
            cy = float(rng.uniform(0.04, 0.96) * h)
            chunk_centers.append((cx, cy))
            # 5-8 vertex irregular polygon
            n_v = int(rng.integers(5, 9))
            base_r = float(rng.uniform(3.0, 7.0) * scale)
            angles = np.sort(rng.uniform(0, 2 * np.pi, n_v))
            radii = base_r * rng.uniform(0.65, 1.20, n_v)
            pts = np.stack([
                cx + np.cos(angles) * radii,
                cy + np.sin(angles) * radii
            ], axis=-1).astype(np.int32)
            pts = pts.reshape(-1, 1, 2)
            chunk_M = float(rng.uniform(0.10, 0.34))  # dark mud
            chunk_R = float(rng.uniform(0.70, 0.95))  # very rough
            chunk_CC = float(rng.uniform(0.55, 0.88))
            _cv2.fillPoly(M,    [pts], chunk_M, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R_ch, [pts], chunk_R, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC,   [pts], chunk_CC, lineType=_cv2.LINE_AA)

        # 3) DIRECTIONAL SPRAY CONES — fanned specks behind each chunk
        # vectorized via offsets
        n_specks_per = 14
        for (cx, cy) in chunk_centers:
            for _ in range(n_specks_per):
                # in the wind direction (positive scalar) with lateral fan
                dist = float(rng.uniform(2.0, 12.0) * scale)
                lateral = float(rng.normal(0, 1.6 * scale))
                # rotate lateral perpendicular to wind
                perp_x = -wdy; perp_y = wdx
                sx = int(np.clip(cx + wdx * dist + perp_x * lateral, 0, w - 1))
                sy = int(np.clip(cy + wdy * dist + perp_y * lateral, 0, h - 1))
                if rng.random() < 0.6:
                    # dark grit speck
                    M[sy, sx]    = float(rng.uniform(0.10, 0.32))
                    R_ch[sy, sx] = float(rng.uniform(0.70, 0.94))
                    CC[sy, sx]   = float(rng.uniform(0.50, 0.85))
                else:
                    # bright water spray speck
                    M[sy, sx]    = float(rng.uniform(0.55, 0.92))
                    R_ch[sy, sx] = float(rng.uniform(0.08, 0.30))
                    CC[sy, sx]   = float(rng.uniform(0.06, 0.30))

        # 4) MICRO-PEBBLE GRAVEL — 1-2 px dark dots
        n_grit = int(np.clip(1300 * (mn / 2048.0) ** 2, 450, 3800))
        for _ in range(n_grit):
            cx_p = int(rng.uniform(0.01, 0.99) * w); cy_p = int(rng.uniform(0.01, 0.99) * h)
            r = max(1, int(rng.uniform(1.0, 1.8) * scale))
            _cv2.circle(M,    (cx_p, cy_p), r, float(rng.uniform(0.06, 0.24)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx_p, cy_p), r, float(rng.uniform(0.74, 0.96)), -1, lineType=_cv2.LINE_AA)

        # 5) SALTY-WATER BEADS — bright 2-3 px
        n_bead = int(np.clip(600 * (mn / 2048.0) ** 2, 200, 1800))
        for _ in range(n_bead):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(1, int(float(rng.uniform(1.5, 2.5)) * scale))
            _cv2.circle(M,    (cx, cy), r, float(rng.uniform(0.60, 0.92)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(rng.uniform(0.06, 0.24)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC,   (cx, cy), r, float(rng.uniform(0.05, 0.28)), -1, lineType=_cv2.LINE_AA)

        # 7) LONG MOTION-BLUR STREAKS at global wind angle, 10-18 px
        n_motion = int(np.clip(620 * (mn / 2048.0) ** 2, 200, 1800))
        for _ in range(n_motion):
            cx_p = int(rng.uniform(0.02, 0.98) * w); cy_p = int(rng.uniform(0.02, 0.98) * h)
            length = int(rng.uniform(10.0, 18.0) * scale)
            ang = wind_angle + float(rng.uniform(-0.15, 0.15))
            x2 = int(np.clip(cx_p + np.cos(ang) * length, 0, w - 1))
            y2 = int(np.clip(cy_p + np.sin(ang) * length, 0, h - 1))
            _cv2.line(M,    (cx_p, cy_p), (x2, y2), float(rng.uniform(0.18, 0.42)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (cx_p, cy_p), (x2, y2), float(rng.uniform(0.65, 0.92)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC,   (cx_p, cy_p), (x2, y2), float(rng.uniform(0.55, 0.85)), 1, lineType=_cv2.LINE_AA)

        # 8) R6-TICK50 NEW HERO — TIRE-TREAD STAMP IMPRINTS.
        # Short parallel rectangle clusters (12-22 px overall) reading as
        # tread chunks pressed into the wet grime. Each cluster has 3-5
        # parallel rect blocks at a stamp-orientation with per-block
        # INDEPENDENT M/R/CC. Captures literal undercarriage tread mark.
        n_tread = int(np.clip(180 * (mn / 2048.0) ** 2, 50, 480))
        for _ in range(n_tread):
            scx = float(rng.uniform(0.06, 0.94) * w)
            scy = float(rng.uniform(0.06, 0.94) * h)
            stamp_ang = float(rng.uniform(0, 2 * np.pi))
            cdx = float(np.cos(stamp_ang)); cdy = float(np.sin(stamp_ang))
            pdx = -cdy; pdy = cdx
            n_blocks = int(rng.integers(3, 6))
            block_l = float(rng.uniform(3.5, 5.5) * scale)
            block_w_px = float(rng.uniform(1.4, 2.4) * scale)
            gap = float(rng.uniform(1.6, 2.6) * scale)
            for bi in range(n_blocks):
                offset = (bi - n_blocks / 2.0) * (block_w_px + gap)
                bcx = scx + pdx * offset
                bcy = scy + pdy * offset
                # rect corners (oriented along stamp_ang)
                hl = block_l * 0.5; hw = block_w_px * 0.5
                corners = np.array([
                    [bcx + cdx * hl + pdx * hw, bcy + cdy * hl + pdy * hw],
                    [bcx + cdx * hl - pdx * hw, bcy + cdy * hl - pdy * hw],
                    [bcx - cdx * hl - pdx * hw, bcy - cdy * hl - pdy * hw],
                    [bcx - cdx * hl + pdx * hw, bcy - cdy * hl + pdy * hw],
                ], dtype=np.int32)
                # Pressed-in mud = dark M, high R, mid-high CC, INDEPENDENT
                _cv2.fillPoly(M,    [corners], float(rng.uniform(0.05, 0.22)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R_ch, [corners], float(rng.uniform(0.72, 0.95)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC,   [corners], float(rng.uniform(0.50, 0.88)), lineType=_cv2.LINE_AA)
                # bright squeeze-out fringe rim along long edge (1 px)
                rim_x1 = int(bcx + cdx * hl - pdx * hw)
                rim_y1 = int(bcy + cdy * hl - pdy * hw)
                rim_x2 = int(bcx - cdx * hl - pdx * hw)
                rim_y2 = int(bcy - cdy * hl - pdy * hw)
                _cv2.line(M, (rim_x1, rim_y1), (rim_x2, rim_y2), float(rng.uniform(0.55, 0.85)), 1, lineType=_cv2.LINE_AA)

    # 6) SALT-FLAKE BRIGHT 1 PX HIGHLIGHTS
    n_fl = int(np.clip(1500 * (mn / 2048.0) ** 2, 500, 4400))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.55, 0.94, n_fl).astype(np.float32))
    R_ch[fy, fx] = np.minimum(R_ch[fy, fx], rng.uniform(0.10, 0.36, n_fl).astype(np.float32))
    CC[fy, fx] = np.minimum(CC[fy, fx], rng.uniform(0.06, 0.32, n_fl).astype(np.float32))

    # === TICK-81 HERO: TIRE SIDEWALL LETTERFORM ARCS ===
    # Curved chains of 4-8 thin "letter" rectangles arrayed along a shallow arc,
    # mimicking molded sidewall lettering pressed into mud (POMP / Goodyear etc).
    if _CV2_OK:
        n_arc = int(np.clip(90 * (mn / 2048.0) ** 2, 22, 280))
        for _ in range(n_arc):
            acx = float(rng.integers(20, max(21, w - 20)))
            acy = float(rng.integers(20, max(21, h - 20)))
            arc_r = float(rng.uniform(14.0, 26.0) * scale)
            a0 = float(rng.uniform(0, 2 * np.pi))
            arc_span = float(rng.uniform(0.7, 1.4))  # radians
            n_letters = int(rng.integers(4, 9))
            letter_h = float(rng.uniform(5.0, 8.0) * scale)
            letter_w = float(rng.uniform(3.0, 5.0) * scale)
            for li in range(n_letters):
                t = a0 + arc_span * (li / max(n_letters - 1, 1) - 0.5)
                lcx = acx + np.cos(t) * arc_r
                lcy = acy + np.sin(t) * arc_r
                # local letter axis = tangent to arc
                tx, ty = -np.sin(t), np.cos(t)
                nx, ny = np.cos(t), np.sin(t)
                hw_l = letter_w * 0.5; hh_l = letter_h * 0.5
                corners = np.array([
                    [lcx + tx * hw_l + nx * hh_l, lcy + ty * hw_l + ny * hh_l],
                    [lcx + tx * hw_l - nx * hh_l, lcy + ty * hw_l - ny * hh_l],
                    [lcx - tx * hw_l - nx * hh_l, lcy - ty * hw_l - ny * hh_l],
                    [lcx - tx * hw_l + nx * hh_l, lcy - ty * hw_l + ny * hh_l],
                ], dtype=np.int32)
                # impressed letter: dark M, rough, mid CC, INDEPENDENT
                _cv2.fillPoly(M, [corners], float(rng.uniform(0.08, 0.24)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R_ch, [corners], float(rng.uniform(0.74, 0.96)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [corners], float(rng.uniform(0.52, 0.86)), lineType=_cv2.LINE_AA)
                # bright squeeze-out rim across the leading edge
                rim_x1 = int(lcx + tx * hw_l + nx * hh_l)
                rim_y1 = int(lcy + ty * hw_l + ny * hh_l)
                rim_x2 = int(lcx - tx * hw_l + nx * hh_l)
                rim_y2 = int(lcy - ty * hw_l + ny * hh_l)
                _cv2.line(M, (rim_x1, rim_y1), (rim_x2, rim_y2),
                          float(rng.uniform(0.58, 0.88)), 1, lineType=_cv2.LINE_AA)

    out = np.stack([np.clip(M, 0, 1), np.clip(R_ch, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)


# Concept already complete (3-channel direct rebuild); flag preserved.
undercarriage_spray._spb_concept_complete = True


def suspension_rust_ring(shape, seed, sm, num_rings=5, ring_spread=0.18,
                          **kwargs):
    """suspension_rust_ring.

    identity: ROUND-6 CREATIVE rebuild — old suspension steelwork seized
    in place under decades of rusty buildup. HERO motif: BOLT + LOCK
    WASHER + TRIPLE CORROSION HALO + downhill RUNOFF DRIP (4-tier bolt
    anatomy unique to this pattern). Stacked: (a) rusted-steel FBM
    substrate INDEPENDENT per channel, (b) 220-2200 bolt heads 4-9 px
    hex-notched, (c) lock-washer star-tooth ring at radius head+1
    (NEW differentiator — 6 short spokes), (d) inner+middle+outer
    corrosion rings 6-18 px each with INDEPENDENT chroma, (e) rust
    runoff drips 4-10 px below outer ring, (f) angular rust flake
    shards 6-14 px, (g) dark pit specks 1-2 px, (h) metallic single
    pixel flecks. Per-feature INDEPENDENT continuous M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 50222)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) RUSTED-STEEL FBM SUBSTRATE — INDEPENDENT M/R/CC
    fM = _normalize(multi_scale_noise(shape, [1.5, 4.0, 11.0, 28.0], [0.35, 0.30, 0.22, 0.13], int(seed) + 9551))
    fR = _normalize(multi_scale_noise(shape, [2.0, 6.0, 16.0, 32.0], [0.40, 0.28, 0.20, 0.12], int(seed) + 9552))
    fCC = _normalize(multi_scale_noise(shape, [1.5, 5.0, 14.0, 30.0], [0.36, 0.30, 0.22, 0.12], int(seed) + 9553))
    M = (0.42 + (fM - 0.5) * 0.36).astype(np.float32)
    R_ch = (0.60 + (fR - 0.5) * 0.32).astype(np.float32)
    CC = (0.55 + (fCC - 0.5) * 0.34).astype(np.float32)

    if _CV2_OK:
        # 2) HERO: BOLT + LOCK WASHER + TRIPLE RING + RUNOFF DRIP
        n_bolts = int(np.clip(680 * (mn / 2048.0) ** 2, 220, 2200))
        for _ in range(n_bolts):
            cx = int(rng.uniform(0.03, 0.97) * w); cy = int(rng.uniform(0.03, 0.97) * h)
            r_head = max(2, int(rng.uniform(2.0, 4.5) * scale))
            r_lock = r_head + max(1, int(rng.uniform(1.0, 2.0) * scale))
            r_inner = r_lock + max(2, int(rng.uniform(2.0, 4.0) * scale))
            r_mid = r_inner + max(1, int(rng.uniform(1.0, 2.5) * scale))
            r_outer = r_mid + max(2, int(rng.uniform(2.0, 4.0) * scale))
            # Outer faint stain halo
            _cv2.circle(M,  (cx, cy), r_outer, float(rng.uniform(0.28, 0.50)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch,(cx, cy), r_outer, float(rng.uniform(0.55, 0.88)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_outer, float(rng.uniform(0.50, 0.85)), 1, lineType=_cv2.LINE_AA)
            # Middle ring (NEW)
            _cv2.circle(M,  (cx, cy), r_mid, float(rng.uniform(0.22, 0.46)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch,(cx, cy), r_mid, float(rng.uniform(0.62, 0.92)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_mid, float(rng.uniform(0.55, 0.88)), 1, lineType=_cv2.LINE_AA)
            # Inner corrosion ring
            _cv2.circle(M,  (cx, cy), r_inner, float(rng.uniform(0.18, 0.42)), 2, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch,(cx, cy), r_inner, float(rng.uniform(0.65, 0.95)), 2, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_inner, float(rng.uniform(0.55, 0.90)), 2, lineType=_cv2.LINE_AA)
            # LOCK WASHER — 6 short spoke ticks at r_lock (NEW differentiator)
            if r_lock >= 3:
                for si in range(6):
                    ang_s = (np.pi * 2 * si / 6) + float(rng.uniform(-0.18, 0.18))
                    x0s = int(cx + np.cos(ang_s) * (r_head + 0.5))
                    y0s = int(cy + np.sin(ang_s) * (r_head + 0.5))
                    x1s = int(cx + np.cos(ang_s) * (r_lock + 0.5))
                    y1s = int(cy + np.sin(ang_s) * (r_lock + 0.5))
                    _cv2.line(M, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.55, 0.90)), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R_ch, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.20, 0.50)), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, (x0s, y0s), (x1s, y1s), float(rng.uniform(0.15, 0.55)), 1, lineType=_cv2.LINE_AA)
            # Bolt head — bright metallic
            _cv2.circle(M,  (cx, cy), r_head, float(rng.uniform(0.65, 0.97)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch,(cx, cy), r_head, float(rng.uniform(0.12, 0.42)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_head, float(rng.uniform(0.12, 0.50)), -1, lineType=_cv2.LINE_AA)
            # Hex notch slash
            if rng.random() < 0.55 and r_head >= 3:
                ang_n = float(rng.uniform(0, np.pi))
                dx = int(np.cos(ang_n) * r_head * 0.8); dy = int(np.sin(ang_n) * r_head * 0.8)
                _cv2.line(M,  (cx - dx, cy - dy), (cx + dx, cy + dy), float(rng.uniform(0.18, 0.42)), 1, lineType=_cv2.LINE_AA)
            # Runoff drip
            if rng.random() < 0.62:
                dy_drip = int(float(rng.uniform(4.0, 10.0)) * scale)
                yd = int(np.clip(cy + r_outer + dy_drip, 0, h - 1))
                dx_j = int(rng.integers(-1, 2))
                _cv2.line(M,   (cx, cy + r_outer), (cx + dx_j, yd), float(rng.uniform(0.20, 0.42)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R_ch,(cx, cy + r_outer), (cx + dx_j, yd), float(rng.uniform(0.65, 0.92)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC,  (cx, cy + r_outer), (cx + dx_j, yd), float(rng.uniform(0.55, 0.85)), 1, lineType=_cv2.LINE_AA)

        # 3) RUST FLAKE SHARDS — 6-14 px angular dark-rust lines
        n_flakes = int(np.clip(1000 * (mn / 2048.0) ** 2, 350, 2900))
        for _ in range(n_flakes):
            cx_p = rng.uniform(0.02, 0.98) * w; cy_p = rng.uniform(0.02, 0.98) * h
            length = float(rng.uniform(6.0, 14.0) * scale)
            ang = float(rng.uniform(0, 2 * np.pi))
            x2 = int(np.clip(cx_p + np.cos(ang) * length, 0, w - 1))
            y2 = int(np.clip(cy_p + np.sin(ang) * length, 0, h - 1))
            _cv2.line(M,  (int(cx_p), int(cy_p)), (x2, y2), float(rng.uniform(0.20, 0.55)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch,(int(cx_p), int(cy_p)), (x2, y2), float(rng.uniform(0.55, 0.92)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (int(cx_p), int(cy_p)), (x2, y2), float(rng.uniform(0.50, 0.88)), 1, lineType=_cv2.LINE_AA)

        # 4) DARK PIT SPECKS — 1-2 px
        n_pits = int(np.clip(1200 * (mn / 2048.0) ** 2, 400, 3500))
        for _ in range(n_pits):
            cx = int(rng.uniform(0.02, 0.98) * w); cy = int(rng.uniform(0.02, 0.98) * h)
            r = max(1, int(rng.uniform(1.0, 2.0) * scale))
            _cv2.circle(M,  (cx, cy), r, float(rng.uniform(0.08, 0.30)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch,(cx, cy), r, float(rng.uniform(0.68, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.55, 0.88)), -1, lineType=_cv2.LINE_AA)

    # 5) METALLIC FLECK ACCENT
    n_fl = int(np.clip(1600 * (mn / 2048.0) ** 2, 550, 4500))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.55, 0.96, n_fl).astype(np.float32))
    R_ch[fy, fx] = np.minimum(R_ch[fy, fx], rng.uniform(0.10, 0.42, n_fl).astype(np.float32))
    CC[fy, fx] = np.minimum(CC[fy, fx], rng.uniform(0.08, 0.40, n_fl).astype(np.float32))

    out = np.stack([np.clip(M, 0, 1), np.clip(R_ch, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)


suspension_rust_ring._spb_concept_complete = True

def spec_corrugated_panel(shape, seed, sm, **kwargs):
    """spec_corrugated_panel.

    identity: R6-CREATIVE — A WEATHERED INDUSTRIAL CORRUGATED SHEET with a
    creative twist: ridges are slightly DIAGONAL (5-8 deg shear) so they
    don't read as a sterile vertical grid, and the hero accents are FOUR
    distinct identity tiers: (1) RIVET-ROW BANDS — horizontal rows of
    paired round-head rivets every ~30 px, each rivet with a bright
    M crown + dark CC shadow + occasional rust drip below (the literal
    "panel screwed to frame" identity reads instantly); (2) VERTICAL
    RUST STREAKS — long 12-22 px tapering drips with high-R / saturated
    CC orange-brown chroma running down from rivet rows; (3) BLISTERED
    PAINT FLAKES — bright bare-metal polygons (4-8 px) chipped off the
    weathered coating, scattered in clusters; (4) CONDENSATION DROPLET
    BEADS — small bright low-CC pinpoints with shadow tails. Stacked
    underneath: fine 8 px-pitch ridges, dents, dark pits, grain flecks,
    chroma-diverse pore carpet. Per-feature INDEPENDENT continuous M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("spec_corrugated_panel_r6c") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    # 1) DIAGONAL ridges (slight shear) — fine pitch ~8 px
    pitch_px = max(6.0, 8.0 * scale)
    shear_ang = float(rng.uniform(0.06, 0.14))  # ~3.5-8 deg
    proj = xx * np.cos(shear_ang) + yy * np.sin(shear_ang)
    ridge = (np.sin(proj * (2.0 * np.pi / pitch_px)) * 0.5 + 0.5)
    amp_env = _normalize(multi_scale_noise(shape, [8.0, 22.0, 55.0],
                                            [0.45, 0.35, 0.20], int(seed) + 4801))
    ridge_mod = ridge * (0.45 + amp_env * 0.55)
    grit = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0],
                                         [0.4, 0.32, 0.28], int(seed) + 4803))
    grit2 = _normalize(multi_scale_noise(shape, [3.0, 8.0, 18.0],
                                          [0.4, 0.32, 0.28], int(seed) + 4805))
    M = (0.50 + (ridge_mod - 0.5) * 0.55 + (grit - 0.5) * 0.14).astype(np.float32)
    R = (0.46 - (ridge_mod - 0.5) * 0.35 + (grit - 0.5) * 0.20).astype(np.float32)
    CC = (0.46 + (ridge_mod - 0.5) * 0.40 + (grit2 - 0.5) * 0.16).astype(np.float32)
    if _CV2_OK:
        # 2) RIVET-ROW BANDS — horizontal rivet pairs along bands ~28-40 px apart
        band_pitch = max(24, int(34 * scale))
        n_bands = max(2, h // band_pitch)
        band_ys = [int((i + 0.5) * band_pitch + rng.uniform(-2, 2)) for i in range(n_bands)]
        rivet_step = max(10, int(14 * scale))
        for by_idx, band_y in enumerate(band_ys):
            x_cur = int(rng.uniform(0, rivet_step))
            while x_cur < w - 2:
                cx = int(np.clip(x_cur + rng.uniform(-1.5, 1.5), 1, w - 2))
                cy = int(np.clip(band_y + rng.uniform(-1.0, 1.0), 1, h - 2))
                r = max(2, int(rng.uniform(2.0, 3.2) * scale))
                # bright crown
                _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.70, 0.97)),
                            -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.12, 0.40)),
                            -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.42, 0.95)),
                            -1, lineType=_cv2.LINE_AA)
                # shadow under-ring
                _cv2.circle(M, (cx, cy + 1), r + 1, float(rng.uniform(0.10, 0.30)),
                            1, lineType=_cv2.LINE_AA)
                # rust drip below rivet (frequent)
                if rng.random() < 0.55:
                    drip_len = int(rng.uniform(10.0, 22.0) * scale)
                    # tapered drip — draw with shrinking circles
                    steps = max(4, drip_len // 2)
                    for s in range(steps):
                        t = s / max(1, steps - 1)
                        dx_ = cx + int(rng.uniform(-1, 1))
                        dy_ = cy + int(t * drip_len)
                        if dy_ >= h:
                            break
                        rr = max(1, int((1.0 - t * 0.7) * 1.6 * scale))
                        _cv2.circle(M, (dx_, dy_), rr, float(rng.uniform(0.08, 0.30)),
                                    -1, lineType=_cv2.LINE_AA)
                        _cv2.circle(R, (dx_, dy_), rr, float(rng.uniform(0.60, 0.95)),
                                    -1, lineType=_cv2.LINE_AA)
                        _cv2.circle(CC, (dx_, dy_), rr, float(rng.uniform(0.30, 0.78)),
                                    -1, lineType=_cv2.LINE_AA)
                x_cur += rivet_step + int(rng.uniform(-1, 1))

        # 3) BLISTERED PAINT FLAKES — bright bare-metal polygons in clusters
        n_clusters_flake = int(np.clip(28 * (mn / 256.0), 12, 70))
        for _ in range(n_clusters_flake):
            ccx = float(rng.uniform(0.05, 0.95) * w)
            ccy = float(rng.uniform(0.05, 0.95) * h)
            n_flakes = int(rng.integers(4, 10))
            for _f in range(n_flakes):
                cx = int(np.clip(ccx + rng.uniform(-12, 12) * scale, 0, w - 1))
                cy = int(np.clip(ccy + rng.uniform(-12, 12) * scale, 0, h - 1))
                n_sides = int(rng.integers(5, 8))
                rr = float(rng.uniform(2.0, 4.0)) * scale
                a0 = float(rng.uniform(0, 2 * np.pi))
                poly = []
                for k in range(n_sides):
                    a = a0 + k * (2 * np.pi / n_sides)
                    px = int(np.clip(cx + np.cos(a) * rr, 0, w - 1))
                    py = int(np.clip(cy + np.sin(a) * rr, 0, h - 1))
                    poly.append([px, py])
                pts = np.array([poly], dtype=np.int32)
                _cv2.fillPoly(M, pts, float(rng.uniform(0.72, 0.97)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, pts, float(rng.uniform(0.05, 0.25)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, pts, float(rng.uniform(0.04, 0.45)), lineType=_cv2.LINE_AA)

        # 4) CONDENSATION DROPLETS — small bright low-CC pinpoints with tails
        n_dewdrop = int(np.clip(600 * (mn / 256.0), 220, 1500))
        for _ in range(n_dewdrop):
            cx = int(rng.integers(2, w - 2)); cy = int(rng.integers(2, h - 4))
            r = max(1, int(rng.uniform(1.3, 2.2) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.78, 0.98)),
                        -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.06, 0.18)),
                        -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.04, 0.18)),
                        -1, lineType=_cv2.LINE_AA)
            # small tail shadow below
            if rng.random() < 0.5 and cy + 4 < h:
                _cv2.line(M, (cx, cy + 1), (cx, min(h - 1, cy + 3)),
                          float(rng.uniform(0.20, 0.45)), 1, lineType=_cv2.LINE_AA)

        # 5) Smaller dents — 3-7 px denser
        n_dent = max(900, int(h * w / 2200))
        for _ in range(n_dent):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1.0, 3.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.08, 0.38)),
                         -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r, float(rng.uniform(0.55, 0.97)),
                         -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.30, 0.85)),
                         -1, lineType=_cv2.LINE_AA)
    # 6) Single-pixel grain flecks
    n_fl = max(8000, int(h * w / 80))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.40, 0.92, n_fl).astype(np.float32))
    # 7) Chroma-diverse micro-pore carpet
    n_pore = max(7000, int(h * w / 100))
    py = rng.integers(0, h, n_pore); px = rng.integers(0, w, n_pore)
    CC[py, px] = np.clip(CC[py, px] + rng.uniform(-0.35, 0.35, n_pore).astype(np.float32), 0, 1)
    R[py, px] = np.clip(R[py, px] + rng.uniform(-0.30, 0.30, n_pore).astype(np.float32), 0, 1)
    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
spec_corrugated_panel._spb_concept_complete = True


# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------

MECHANICAL_PATTERNS = {
    'exhaust_pipe_scorch': exhaust_pipe_scorch,
    'radiator_grille_mesh': radiator_grille_mesh,
    'engine_bay_grime': engine_bay_grime,
    'tire_smoke_streaks': tire_smoke_streaks,
    'undercarriage_spray': undercarriage_spray,
    'suspension_rust_ring': suspension_rust_ring,
    'spec_corrugated_panel': spec_corrugated_panel,
}

__all__ = [
    'MECHANICAL_PATTERNS',
    'exhaust_pipe_scorch',
    'radiator_grille_mesh',
    'engine_bay_grime',
    'tire_smoke_streaks',
    'undercarriage_spray',
    'suspension_rust_ring',
    'spec_corrugated_panel',
]

