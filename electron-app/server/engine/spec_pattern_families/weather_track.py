"""Weather and track spec pattern family for Shokker Paint Booth.

This module is imported by engine.spec_patterns so PATTERN_CATALOG keeps
the legacy public keys while the central spec registry shrinks.
"""
import numpy as np

from ..spec_patterns import (
    _flat,
    _gauss,
    _normalize,
    _sm_scale,
    _validate_spec_output,
    multi_scale_noise,
    _CV2_OK,
    _cv2,
)


def _spb_fast_line_distance(coord, period, width, phase=0.0):
    r = np.abs(np.mod(coord + phase, period) - period * 0.5)
    return np.clip(1.0 - r / max(width, 1e-6), 0.0, 1.0).astype(np.float32)

# WEATHER & TRACK (6 patterns)
# ----------------------------------------------------------------------------

def rain_droplet_beads(shape, seed, sm, density=0.0015, min_r=2.5,
                        max_r=6.5, **kwargs):
    """rain_droplet_beads — R6-Loop tick-81 second-pass creative refinement.

    identity: Round-6 creative rebuild — a rain-pelted glossy hood with
    a SIZE-CLASS PYRAMID of crystal-clear water beads: HERO beads
    (10-16 px) anchor the panel with full bright crescent glint,
    secondary mid-beads (6-10 px), tertiary fine beads (3-6 px), and a
    spray-mist micro carpet (1-2 px). Each bead carries a top sky-glint
    cap (bright CC, low R), a darker gravity crescent under the body,
    and a capillary-bond chain that connects neighboring beads via
    short 3-8 px liquid bridges where they nearly touch. Vertical drip
    trails (12-36 px) descend from the HERO tier. Cross-pattern wetness
    bands (broad FBM) give regional wet/dry contrast. Per-bead INDEPENDENT
    continuous M/R/CC uniforms — no palette tiers. Full-canvas coverage.

    TICK-81 SECOND-PASS HERO: THIN-FILM INTERFERENCE IRIDESCENT HALOS.
    Around each HERO bead, a soap-film color-shift ring is drawn as 3-4
    concentric thin CC rings whose chroma marches through a COOL DEEP-
    VIOLET → ICE-BLUE sweep (mimicking Newton's-ring optical interference
    at varying film thickness). The halo overlay tilts the panel from
    plain wet-glossy to fuel-spill iridescent — a Round-2 prismatic
    physics motif previously absent from the bead family.
    """
    from engine.spec_patterns import (
        _flat, _normalize, _sm_scale, multi_scale_noise, _CV2_OK, _cv2,
    )
    import numpy as np

    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 70411)
    mn = min(h, w)
    scale = max(mn / 2048.0, 0.25)

    # 1) Wet-panel substrate — three INDEPENDENT FBM channels for wide chroma
    wM = _normalize(multi_scale_noise((h, w), [5.0, 14.0, 38.0],
                                       [0.42, 0.32, 0.26], int(seed) + 7711))
    wR = _normalize(multi_scale_noise((h, w), [6.0, 16.0, 42.0],
                                       [0.42, 0.32, 0.26], int(seed) + 7712))
    wCC = _normalize(multi_scale_noise((h, w), [6.5, 17.0, 44.0],
                                       [0.42, 0.32, 0.26], int(seed) + 7713))
    M = (0.34 + (wM - 0.5) * 0.28).astype(np.float32)
    R = (0.38 + (wR - 0.5) * 0.30).astype(np.float32)
    CC = (0.24 + (wCC - 0.5) * 0.22).astype(np.float32)

    # Bead position cache for capillary bridges (HERO + mid only)
    bead_xy = []

    if _CV2_OK:
        # 2) HERO BEADS (10-16 px) — anchors the panel
        n_hero = int(np.clip(140 * (mn / 2048.0) ** 2, 60, 400))
        for _ in range(n_hero):
            cx = int(rng.uniform(0.03, 0.97) * w)
            cy = int(rng.uniform(0.03, 0.97) * h)
            r_b = max(5, int(rng.uniform(10.0, 16.0) * scale))
            # bead body — INDEPENDENT continuous M/R/CC
            _cv2.circle(M, (cx, cy), r_b, float(rng.uniform(0.20, 0.62)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r_b, float(rng.uniform(0.08, 0.36)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_b, float(rng.uniform(0.04, 0.22)), -1, lineType=_cv2.LINE_AA)
            # Sky-glint top cap (bright)
            gx = int(cx + r_b * 0.30); gy = int(cy - r_b * 0.42)
            g_r = max(2, int(r_b * 0.35))
            _cv2.circle(M, (gx, gy), g_r, float(rng.uniform(0.62, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (gx, gy), g_r, float(rng.uniform(0.04, 0.18)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (gx, gy), g_r, float(rng.uniform(0.02, 0.12)), -1, lineType=_cv2.LINE_AA)
            # Gravity crescent under bead
            sx = int(cx - r_b * 0.10); sy = int(cy + r_b * 0.55)
            s_r = max(2, int(r_b * 0.60))
            _cv2.circle(R, (sx, sy), s_r, float(rng.uniform(0.48, 0.88)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(M, (sx, sy), s_r, float(rng.uniform(0.12, 0.38)), -1, lineType=_cv2.LINE_AA)
            bead_xy.append((cx, cy, r_b))

        # 3) MID BEADS (6-10 px)
        n_mid = int(np.clip(520 * (mn / 2048.0) ** 2, 200, 1400))
        for _ in range(n_mid):
            cx = int(rng.uniform(0.02, 0.98) * w)
            cy = int(rng.uniform(0.02, 0.98) * h)
            r_b = max(3, int(rng.uniform(6.0, 10.0) * scale))
            _cv2.circle(M, (cx, cy), r_b, float(rng.uniform(0.18, 0.58)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r_b, float(rng.uniform(0.10, 0.34)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_b, float(rng.uniform(0.06, 0.22)), -1, lineType=_cv2.LINE_AA)
            gx = int(cx + r_b * 0.30); gy = int(cy - r_b * 0.40)
            g_r = max(1, int(r_b * 0.32))
            _cv2.circle(M, (gx, gy), g_r, float(rng.uniform(0.55, 0.92)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (gx, gy), g_r, float(rng.uniform(0.05, 0.18)), -1, lineType=_cv2.LINE_AA)
            sx = int(cx - r_b * 0.12); sy = int(cy + r_b * 0.50)
            s_r = max(1, int(r_b * 0.55))
            _cv2.circle(R, (sx, sy), s_r, float(rng.uniform(0.42, 0.82)), -1, lineType=_cv2.LINE_AA)
            if len(bead_xy) < 900:
                bead_xy.append((cx, cy, r_b))

        # 4) FINE BEADS (3-6 px) — dense
        n_fine = int(np.clip(1800 * (mn / 2048.0) ** 2, 700, 4500))
        for _ in range(n_fine):
            cx = int(rng.uniform(0.01, 0.99) * w)
            cy = int(rng.uniform(0.01, 0.99) * h)
            r_b = max(2, int(rng.uniform(3.0, 6.0) * scale))
            _cv2.circle(M, (cx, cy), r_b, float(rng.uniform(0.16, 0.55)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), r_b, float(rng.uniform(0.10, 0.36)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r_b, float(rng.uniform(0.06, 0.24)), -1, lineType=_cv2.LINE_AA)
            # small glint
            gx = int(cx + r_b * 0.35); gy = int(cy - r_b * 0.35)
            _cv2.circle(M, (gx, gy), max(1, int(r_b * 0.30)), float(rng.uniform(0.48, 0.88)), -1, lineType=_cv2.LINE_AA)

        # 5) NEW — CAPILLARY BRIDGES between nearby beads
        if len(bead_xy) > 1:
            arr = np.array(bead_xy)
            # Random sampling pass — for each bead, find a near neighbor
            sample_n = min(len(bead_xy), 400)
            idxs = rng.choice(len(bead_xy), sample_n, replace=False)
            for i in idxs:
                cx, cy, rb = bead_xy[i]
                # check up to 3 random candidates
                cand = rng.choice(len(bead_xy), min(6, len(bead_xy)), replace=False)
                for j in cand:
                    if j == i: continue
                    nx, ny, nr = bead_xy[j]
                    d = float(np.hypot(nx - cx, ny - cy))
                    if d < (rb + nr + 8 * scale) and d > (rb + nr - 2):
                        _cv2.line(M, (cx, cy), (nx, ny), float(rng.uniform(0.38, 0.78)), 1, lineType=_cv2.LINE_AA)
                        _cv2.line(R, (cx, cy), (nx, ny), float(rng.uniform(0.12, 0.40)), 1, lineType=_cv2.LINE_AA)
                        _cv2.line(CC, (cx, cy), (nx, ny), float(rng.uniform(0.06, 0.24)), 1, lineType=_cv2.LINE_AA)
                        break

        # 6) DRIP TRAILS from HERO tier (12-36 px vertical)
        n_trail = int(np.clip(160 * (mn / 2048.0) ** 2, 50, 600))
        for _ in range(n_trail):
            cx = int(rng.uniform(0.03, 0.97) * w)
            cy = int(rng.uniform(0.02, 0.80) * h)
            length = int(rng.uniform(12.0, 36.0) * scale)
            yy_end = min(h - 1, cy + length)
            _cv2.line(R, (cx, cy), (cx, yy_end), float(rng.uniform(0.22, 0.55)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (cx, yy_end), float(rng.uniform(0.04, 0.16)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, (cx, cy), (cx, yy_end), float(rng.uniform(0.30, 0.62)), 1, lineType=_cv2.LINE_AA)

    # 7) SPRAY-MIST micro-carpet (1-2 px)
    n_mist = int(np.clip(4200 * (mn / 2048.0) ** 2, 1500, 9000))
    my = rng.integers(0, h, n_mist); mx = rng.integers(0, w, n_mist)
    M[my, mx] = np.maximum(M[my, mx], rng.uniform(0.32, 0.85, n_mist).astype(np.float32))
    R[my, mx] = np.minimum(R[my, mx], rng.uniform(0.12, 0.38, n_mist).astype(np.float32))
    CC[my, mx] = np.minimum(CC[my, mx], rng.uniform(0.04, 0.22, n_mist).astype(np.float32))

    # === TICK-81 HERO: THIN-FILM INTERFERENCE IRIDESCENT HALOS ===
    # Around each HERO/mid bead, 3-4 concentric soap-film rings, COOL
    # deep-violet -> ice-blue CC sweep. Per-ring TIGHT chroma jitter.
    if _CV2_OK and len(bead_xy) > 0:
        VIOLET_CC, ICE_CC = 0.62, 0.78
        # Take the first HERO entries (size-sorted descending so HEROS first)
        bead_arr = sorted(bead_xy, key=lambda t: -t[2])
        n_halo = min(len(bead_arr), int(np.clip(220 * (mn / 2048.0) ** 2, 60, 600)))
        for k in range(n_halo):
            cx_h, cy_h, rb_h = bead_arr[k]
            if rb_h < 4:
                continue
            n_rings = int(rng.integers(3, 5))
            for ri in range(n_rings):
                halo_r = int(rb_h + 1 + ri * max(1, int(0.6 * scale + 1)))
                if halo_r >= max(h, w):
                    continue
                # Sweep CC from violet -> ice across rings
                t_sweep = ri / max(n_rings - 1, 1)
                cc_val = float(np.clip(VIOLET_CC * (1 - t_sweep) + ICE_CC * t_sweep
                                       + rng.uniform(-0.05, 0.05), 0.30, 0.99))
                m_val = float(np.clip(0.30 + rng.uniform(-0.04, 0.04), 0.10, 0.55))
                r_val = float(np.clip(0.18 + rng.uniform(-0.04, 0.04), 0.04, 0.40))
                _cv2.circle(CC, (cx_h, cy_h), halo_r, cc_val, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (cx_h, cy_h), halo_r, m_val, 1, lineType=_cv2.LINE_AA)
                if ri == n_rings - 1:
                    _cv2.circle(R, (cx_h, cy_h), halo_r, r_val, 1, lineType=_cv2.LINE_AA)

    out = np.stack([np.clip(M, 0, 1), np.clip(R, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(out, sm)
rain_droplet_beads._spb_concept_complete = True


def mud_splatter_random(shape, seed, sm, num_splats=60, splat_size=0.04,
                         **kwargs):
    """mud_splatter_random.

    identity: R6-CREATIVE — KINETIC MUD STORM. Wet-mud splatter
    with stacked motion vocabulary:
      • Jagged-edged hero blobs (irregular star-polygon shape, 8-24 px,
        not soft ellipses) — the chunky core impact signature.
      • Drip-streak hanging from the BOTTOM of each blob (gravity-pulled
        teardrop tail dripping straight down).
      • Comet droplet trails radiating from the impact direction
        (satellite fan, length 4-5x blob radius).
      • Ricochet ARCS — curved kinetic spray (Bezier arc droplet
        chains, suggesting bouncing/spinning mud).
      • Tiny secondary satellites 1-2 px (fine dispersion).
      • Sun-baked CRACK HAIRLINES on the dried blobs (interior detail).
    Per-impact independent M/R/CC. Differentiates from sibling weather
    patterns by the gravity-drip + ricochet-arc combination.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("mud_splatter_random_storm_r6") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) WET FENDER SUBSTRATE — dark, low gloss, INDEPENDENT per-channel FBM
    fM  = _normalize(multi_scale_noise(shape, [2.5, 6.0, 14.0], [0.45, 0.35, 0.20], int(seed) + 11510))
    fR  = _normalize(multi_scale_noise(shape, [2.5, 6.0, 14.0], [0.45, 0.35, 0.20], int(seed) + 11512))
    fCC = _normalize(multi_scale_noise(shape, [2.5, 6.0, 14.0], [0.45, 0.35, 0.20], int(seed) + 11514))
    M    = (0.38 + (fM  - 0.5) * 0.28).astype(np.float32)
    R_ch = (0.72 + (fR  - 0.5) * 0.24).astype(np.float32)
    CC   = (0.42 + (fCC - 0.5) * 0.30).astype(np.float32)

    if _CV2_OK:
        # 2) HERO IMPACT BLOBS — jagged star-polygons + gravity drip + comet trail
        n_impacts = int(np.clip(200 * (mn / 2048.0) ** 2, 80, 760))
        for _ in range(n_impacts):
            ix = float(rng.uniform(0.04, 0.96) * w)
            iy = float(rng.uniform(0.04, 0.85) * h)  # leave room for drip
            blob_M  = float(rng.uniform(0.08, 0.30))
            blob_R  = float(rng.uniform(0.78, 0.96))
            blob_CC = float(rng.uniform(0.06, 0.32))
            core_r  = max(2, int(rng.uniform(4.0, 12.0) * scale))
            # JAGGED STAR-POLYGON CORE
            n_v = int(rng.integers(7, 13))
            pts = []
            a0 = float(rng.uniform(0, 2 * np.pi))
            for k in range(n_v):
                ang = a0 + (k * 2 * np.pi / n_v)
                # Alternate near/far vertices for jagged star feel
                rk = core_r * (float(rng.uniform(0.55, 1.0)) if k % 2 == 0 else float(rng.uniform(1.0, 1.5)))
                pts.append([int(np.clip(ix + np.cos(ang) * rk, 0, w - 1)),
                            int(np.clip(iy + np.sin(ang) * rk, 0, h - 1))])
            poly = np.array(pts, dtype=np.int32)
            _cv2.fillPoly(M,    [poly], blob_M, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R_ch, [poly], blob_R, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC,   [poly], blob_CC, lineType=_cv2.LINE_AA)

            # GRAVITY DRIP — teardrop tail straight down from the bottom of the blob
            drip_len = int(rng.uniform(core_r * 1.5, core_r * 4.0))
            drip_w0 = max(1, int(core_r * 0.45))
            for ti in range(drip_len):
                yi = int(iy) + core_r + ti
                if yi >= h: break
                t = ti / max(drip_len - 1, 1)
                taper = (1.0 - t) ** 1.4
                hw = max(0, int(drip_w0 * taper))
                if hw <= 0: continue
                xc = int(ix) + int(rng.uniform(-0.5, 0.5))
                lo = max(0, xc - hw); hi_ = min(w, xc + hw + 1)
                a = 0.70 * taper + 0.15
                M[yi, lo:hi_]    = M[yi, lo:hi_]    * (1 - a) + blob_M * a
                R_ch[yi, lo:hi_] = R_ch[yi, lo:hi_] * (1 - a) + blob_R * a
                CC[yi, lo:hi_]   = CC[yi, lo:hi_]   * (1 - a) + blob_CC * a
            # drip terminal bulb
            by_end = min(h - 1, int(iy) + core_r + drip_len)
            _cv2.circle(M,    (int(ix), by_end), max(1, drip_w0 // 2 + 1), blob_M, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (int(ix), by_end), max(1, drip_w0 // 2 + 1), blob_R, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC,   (int(ix), by_end), max(1, drip_w0 // 2 + 1), blob_CC, -1, lineType=_cv2.LINE_AA)

            # COMET DROPLET TRAIL — radiating fan from impact direction
            trail_ang = float(rng.uniform(0, 2 * np.pi))
            spread = float(rng.uniform(0.18, 0.55))
            n_drops = int(rng.integers(6, 16))
            for k in range(n_drops):
                r_dist = float(rng.uniform(core_r * 1.2, core_r * 5.0))
                a = trail_ang + float(rng.uniform(-spread, spread))
                dx = ix + np.cos(a) * r_dist
                dy = iy + np.sin(a) * r_dist
                if 0 <= dx < w and 0 <= dy < h:
                    dr = max(1, int(rng.uniform(1.0, 3.5) * scale))
                    _cv2.circle(M,    (int(dx), int(dy)), dr, blob_M + float(rng.uniform(-0.06, 0.06)), -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(R_ch, (int(dx), int(dy)), dr, blob_R + float(rng.uniform(-0.05, 0.05)), -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC,   (int(dx), int(dy)), dr, blob_CC + float(rng.uniform(-0.06, 0.06)), -1, lineType=_cv2.LINE_AA)

            # SUN-BAKED CRACK HAIRLINE — fine crack across the blob interior
            if rng.random() < 0.6:
                ca = float(rng.uniform(0, np.pi))
                cl = core_r * 0.9
                cx1 = int(ix + np.cos(ca) * cl); cy1 = int(iy + np.sin(ca) * cl)
                cx2 = int(ix - np.cos(ca) * cl); cy2 = int(iy - np.sin(ca) * cl)
                _cv2.line(M,    (cx1, cy1), (cx2, cy2), float(np.clip(blob_M + 0.15, 0, 1)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R_ch, (cx1, cy1), (cx2, cy2), float(np.clip(blob_R - 0.05, 0, 1)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC,   (cx1, cy1), (cx2, cy2), float(np.clip(blob_CC + 0.15, 0, 1)), 1, lineType=_cv2.LINE_AA)

        # 3) RICOCHET ARCS — curved kinetic spray (Bezier-ish droplet chains)
        n_arcs = int(np.clip(80 * (mn / 256.0), 25, 200))
        for _ in range(n_arcs):
            x0 = float(rng.uniform(0.05, 0.95) * w); y0 = float(rng.uniform(0.05, 0.95) * h)
            arc_len = float(rng.uniform(12.0, 30.0) * scale)
            ang0 = float(rng.uniform(0, 2 * np.pi))
            curv = float(rng.uniform(-0.06, 0.06))
            n_steps = int(rng.uniform(5, 12))
            aM = float(rng.uniform(0.10, 0.30))
            aR = float(rng.uniform(0.78, 0.96))
            aCC = float(rng.uniform(0.08, 0.32))
            for s in range(n_steps):
                tt = s / max(n_steps - 1, 1)
                ang = ang0 + curv * s
                px = int(np.clip(x0 + np.cos(ang) * arc_len * tt, 0, w - 1))
                py = int(np.clip(y0 + np.sin(ang) * arc_len * tt, 0, h - 1))
                dr = max(1, int(rng.uniform(1.0, 2.5) * scale))
                _cv2.circle(M,    (px, py), dr, aM, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R_ch, (px, py), dr, aR, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC,   (px, py), dr, aCC, -1, lineType=_cv2.LINE_AA)

        # 4) TINY SECONDARY SATELLITES — vectorized fine spray
        n_sec = int(np.clip(mn * mn * 0.012, 5000, 90000))
        ssy = rng.integers(0, h, n_sec); ssx = rng.integers(0, w, n_sec)
        M[ssy, ssx]    = np.minimum(M[ssy, ssx],    rng.uniform(0.10, 0.32, n_sec).astype(np.float32))
        R_ch[ssy, ssx] = np.maximum(R_ch[ssy, ssx], rng.uniform(0.75, 0.95, n_sec).astype(np.float32))
        CC[ssy, ssx]   = np.minimum(CC[ssy, ssx],   rng.uniform(0.08, 0.32, n_sec).astype(np.float32))

    # 5) GRIT PEPPER — vectorized bright pinpoints (sand/silica catches the light)
    n_b = int(np.clip(1200 * (mn / 2048.0) ** 2, 400, 3800))
    bx = rng.integers(0, w, n_b); by = rng.integers(0, h, n_b)
    M[by, bx] = np.maximum(M[by, bx], rng.uniform(0.55, 0.88, n_b).astype(np.float32))
    CC[by, bx] = np.maximum(CC[by, bx], rng.uniform(0.40, 0.75, n_b).astype(np.float32))

    out = np.stack([np.clip(M, 0, 1), np.clip(R_ch, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)


mud_splatter_random._spb_concept_complete = True


def wet_track_gloss(shape, seed, sm, **kwargs):
    """wet_track_gloss — R6 CREATIVE rebuild.

    identity: A RAIN-SOAKED NIGHT TRACK CATCHING STREETLIGHT REFLECTIONS.
    Hero motif now: VERTICAL STRETCHED REFLECTION SLASHES (the long
    smeared shine of a streetlight pulled across wet pavement) — 6-18 px
    tall, 1-2 px wide, scattered across the canvas like phantom lampposts
    streaked into the puddles. Stacked: (1) wet black tarmac FBM
    substrate (low M, very low R, very low CC = mirror-wet), (2) VERTICAL
    REFLECTION SLASHES (the hero — per-slash chroma + brightness gradient
    along height), (3) circular RAIN IMPACT RINGS (3-6 px) scattered to
    show active rainfall, (4) elongated puddle islands as flatter mirror
    ellipses (6-14 px), (5) micro spray bead 1-2 px clusters above
    impacts, (6) tiny dark cooled-water dimples (2-3 px), (7) oil-sheen
    modulator on CC for rainbow hint, (8) bright sky-glint pinpoints
    (1 px). Per-feature INDEPENDENT continuous M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 92017)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) WET BLACK TARMAC BASE
    fM = _normalize(multi_scale_noise(shape, [1.6, 4.4, 12.0, 28.0], [0.35, 0.30, 0.21, 0.14], int(seed) + 8811))
    fR = _normalize(multi_scale_noise(shape, [1.8, 4.8, 13.0, 30.0], [0.36, 0.30, 0.20, 0.14], int(seed) + 8912))
    fCC = _normalize(multi_scale_noise(shape, [2.1, 5.4, 14.0, 32.0], [0.36, 0.28, 0.22, 0.14], int(seed) + 9013))
    M  = (0.18 + (fM - 0.5) * 0.18).astype(np.float32)
    R_ch = (0.24 + (fR - 0.5) * 0.20).astype(np.float32)   # wet => low roughness
    CC = (0.14 + (fCC - 0.5) * 0.16).astype(np.float32)    # bright clearcoat (low B)

    if _CV2_OK:
        # 2) VERTICAL REFLECTION SLASHES — HERO
        n_slash = int(np.clip(380 * (mn / 2048.0) ** 2, 120, 1100))
        for _ in range(n_slash):
            cx = int(rng.uniform(0.02, 0.98) * w)
            cy = int(rng.uniform(0.05, 0.95) * h)
            height = int(rng.uniform(6.0, 18.0) * scale)
            half = max(2, height // 2)
            slash_M_top = float(rng.uniform(0.78, 0.99))
            slash_M_bot = float(rng.uniform(0.30, 0.55))
            slash_R = float(rng.uniform(0.04, 0.16))
            slash_CC = float(rng.uniform(0.03, 0.14))
            # draw 4-6 vertical sub-segments with falloff
            n_segs = max(4, int(height / 3))
            for s in range(n_segs):
                t = s / max(n_segs - 1, 1)
                yy = int(np.clip(cy - half + t * height, 0, h - 1))
                # taper width: thinner at top/bottom, slightly thicker at middle
                w_jitter = float(rng.uniform(-1.0, 1.0))
                # subtle horizontal jitter to feel painted
                xx = int(np.clip(cx + w_jitter * 0.5, 0, w - 1))
                mv = float(slash_M_top * (1 - t) + slash_M_bot * t)
                M[yy, xx] = max(M[yy, xx], mv)
                R_ch[yy, xx] = min(R_ch[yy, xx], slash_R)
                CC[yy, xx] = min(CC[yy, xx], slash_CC)
                # 1-px wider where bright
                if t < 0.4 and xx + 1 < w:
                    M[yy, xx + 1] = max(M[yy, xx + 1], mv * 0.85)
                    CC[yy, xx + 1] = min(CC[yy, xx + 1], slash_CC + 0.04)
                if t < 0.4 and xx - 1 >= 0:
                    M[yy, xx - 1] = max(M[yy, xx - 1], mv * 0.85)
                    CC[yy, xx - 1] = min(CC[yy, xx - 1], slash_CC + 0.04)

        # 3) RAIN IMPACT RINGS — 3-6 px
        n_ring = int(np.clip(2200 * (mn / 2048.0) ** 2, 800, 6000))
        for _ in range(n_ring):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r_outer = max(2, int(rng.uniform(2.5, 5.0) * scale))
            _cv2.circle(M,    (cx, cy), r_outer, float(rng.uniform(0.55, 0.95)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r_outer, float(rng.uniform(0.04, 0.18)), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC,   (cx, cy), r_outer, float(rng.uniform(0.04, 0.16)), 1, lineType=_cv2.LINE_AA)
            if r_outer >= 3:
                _cv2.circle(M, (cx, cy), max(1, r_outer - 2), float(rng.uniform(0.62, 0.97)), 1, lineType=_cv2.LINE_AA)

        # 4) PUDDLE ISLANDS — flatter ellipses, 6-14 px
        n_pud = int(np.clip(420 * (mn / 2048.0) ** 2, 140, 1200))
        for _ in range(n_pud):
            cx = int(rng.uniform(0.04, 0.96) * w); cy = int(rng.uniform(0.04, 0.96) * h)
            r1 = int(max(3, rng.uniform(6, 14) * scale * 0.5))
            r2 = int(max(2, rng.uniform(3, 8) * scale * 0.5))
            ang = float(rng.uniform(0, 180))
            _cv2.ellipse(M,    (cx, cy), (r1, r2), ang, 0, 360, float(rng.uniform(0.40, 0.85)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R_ch, (cx, cy), (r1, r2), ang, 0, 360, float(rng.uniform(0.03, 0.16)), -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC,   (cx, cy), (r1, r2), ang, 0, 360, float(rng.uniform(0.03, 0.14)), -1, lineType=_cv2.LINE_AA)

        # 5) COOLED-WATER DIMPLES — 2-3 px dark
        n_dim = int(np.clip(800 * (mn / 2048.0) ** 2, 280, 2600))
        for _ in range(n_dim):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1.2, 2.4) * scale))
            _cv2.circle(M,    (cx, cy), r, float(rng.uniform(0.12, 0.30)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(rng.uniform(0.55, 0.85)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC,   (cx, cy), r, float(rng.uniform(0.35, 0.65)), -1, lineType=_cv2.LINE_AA)

    # 6) SPRAY BEAD MICRO-DROPLETS
    n_b = int(np.clip(5200 * (mn / 2048.0) ** 2, 1700, 14000))
    bx = rng.integers(0, w, n_b); by = rng.integers(0, h, n_b)
    M[by, bx]    = np.maximum(M[by, bx],    rng.uniform(0.55, 0.95, n_b).astype(np.float32))
    R_ch[by, bx] = np.minimum(R_ch[by, bx], rng.uniform(0.04, 0.20, n_b).astype(np.float32))
    CC[by, bx]   = np.minimum(CC[by, bx],   rng.uniform(0.03, 0.18, n_b).astype(np.float32))

    # 7) SKY-GLINT PINPOINTS — 1 px brightest
    n_g = int(np.clip(2400 * (mn / 2048.0) ** 2, 800, 7000))
    gy = rng.integers(0, h, n_g); gx = rng.integers(0, w, n_g)
    M[gy, gx] = np.maximum(M[gy, gx], rng.uniform(0.72, 0.99, n_g).astype(np.float32))
    CC[gy, gx] = np.minimum(CC[gy, gx], rng.uniform(0.02, 0.12, n_g).astype(np.float32))

    # 8) OIL SHEEN MODULATION
    sheen = _normalize(multi_scale_noise(shape, [10.0, 24.0], [0.6, 0.4], int(seed) + 8820))
    CC = CC + (sheen - 0.5) * 0.10
    R_ch = R_ch + (sheen - 0.5) * 0.06

    # R6 TICK 54 SECOND-PASS HERO — BOKEH HEADLIGHT GHOSTS
    # 14-32 soft circular glow blobs (5-10 px) reading like distant car
    # headlights bouncing off wet pavement. Each ghost is a layered disc:
    # outer halo + bright core + ultra-bright pinpoint, all with INDEPENDENT
    # M/R/CC continuous uniforms in WIDE range so adjacent ghosts pick up
    # warm/cool/white tints (different lamps of different distances). Plus
    # 22-44 wet-ripple INTERFERENCE PATCHES (3-6 px ovals) where two
    # rain-ring waves crossed.
    if _CV2_OK:
        n_ghost = int(np.clip(22 * (mn / 256.0), 14, 38))
        for _ in range(n_ghost):
            gcx = int(rng.uniform(0.04, 0.96) * w)
            gcy = int(rng.uniform(0.04, 0.96) * h)
            r_out = max(3, int(rng.uniform(5.0, 10.0) * scale * 0.5))
            r_core = max(2, int(r_out * 0.55))
            r_pin = max(1, r_out // 4)
            haloM = float(rng.uniform(0.55, 0.85))
            haloR = float(rng.uniform(0.04, 0.18))
            haloCC = float(rng.uniform(0.04, 0.18))
            _cv2.circle(M,    (gcx, gcy), r_out,  haloM, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (gcx, gcy), r_out,  haloR, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC,   (gcx, gcy), r_out,  haloCC, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(M,    (gcx, gcy), r_core, float(rng.uniform(0.78, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (gcx, gcy), r_core, float(rng.uniform(0.02, 0.10)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC,   (gcx, gcy), r_core, float(rng.uniform(0.02, 0.10)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(M,    (gcx, gcy), r_pin,  float(rng.uniform(0.92, 0.99)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (gcx, gcy), r_pin,  float(rng.uniform(0.01, 0.05)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC,   (gcx, gcy), r_pin,  float(rng.uniform(0.01, 0.04)), -1, lineType=_cv2.LINE_AA)

        # WET-RIPPLE INTERFERENCE PATCHES
        n_intf = int(np.clip(34 * (mn / 256.0), 22, 56))
        for _ in range(n_intf):
            icx = int(rng.uniform(0.02, 0.98) * w)
            icy = int(rng.uniform(0.02, 0.98) * h)
            irx = max(2, int(rng.uniform(2.5, 5.5) * scale))
            iry = max(1, int(rng.uniform(1.5, 3.5) * scale))
            iang = float(rng.uniform(0, 180))
            _cv2.ellipse(M,    (icx, icy), (irx, iry), iang, 0, 360, float(rng.uniform(0.48, 0.86)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R_ch, (icx, icy), (irx, iry), iang, 0, 360, float(rng.uniform(0.04, 0.18)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC,   (icx, icy), (irx, iry), iang, 0, 360, float(rng.uniform(0.04, 0.18)), 1, lineType=_cv2.LINE_AA)

    out = np.stack([np.clip(M, 0, 1), np.clip(R_ch, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)
wet_track_gloss._spb_concept_complete = True


def dry_dust_film(shape, seed, sm, density=0.45, **kwargs):
    """Dry dust film — corrective 5x grit carpet with wipe streak storm.

    identity: A panel buried in dust. Every pixel sits under fine pale haze
    with 5x denser sub-pixel grit specks (15000+ vectorized pinpoints),
    layered finger-wipe drag streaks (4-18 px, near-horizontal) at high
    density, smaller fingerprint loop arcs (3-7 px curves), darker
    fingerprint smudge clusters where someone touched the panel, and
    bright pollen-or-dust-mote highlights catching the light. Settled
    drift bands subtly modulate the whole field. Per-feature continuous
    M/R/CC uniforms.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 77107)
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) BASE — pale dust haze (composite-dark warm-tan substrate)
    # FIX 2026-05-26: substrate had R=0.75 producing neon-green composite.
    # Now M=0.22/R=0.18/CC=0.20 for dark warm dust-tone composite.
    fM = _normalize(multi_scale_noise(shape, [1.2, 3.5, 9.0, 22.0], [0.35, 0.30, 0.22, 0.13], int(seed) + 77111))
    fR = _normalize(multi_scale_noise(shape, [1.2, 3.5, 9.0, 22.0], [0.35, 0.30, 0.22, 0.13], int(seed) + 77113))
    fCC = _normalize(multi_scale_noise(shape, [1.2, 3.5, 9.0, 22.0], [0.35, 0.30, 0.22, 0.13], int(seed) + 77115))
    M = (0.22 + (fM - 0.5) * 0.14).astype(np.float32)
    R_ch = (0.18 + (fR - 0.5) * 0.12).astype(np.float32)
    CC = (0.20 + (fCC - 0.5) * 0.12).astype(np.float32)

    # 2) GRIT CARPET — moderate density vectorized (was 5x, now sane)
    n_grit = int(np.clip(h * w / 28, 4000, 12000))
    gx = rng.integers(0, w, n_grit); gy = rng.integers(0, h, n_grit)
    M[gy, gx] = np.maximum(M[gy, gx], rng.uniform(0.30, 0.62, n_grit).astype(np.float32))
    R_ch[gy, gx] = np.maximum(R_ch[gy, gx], rng.uniform(0.22, 0.40, n_grit).astype(np.float32))
    CC[gy, gx] = np.maximum(CC[gy, gx], rng.uniform(0.18, 0.45, n_grit).astype(np.float32))

    # Bright pollen-mote highlights — sparse
    n_mote = int(np.clip(h * w / 120, 600, 3000))
    py = rng.integers(0, h, n_mote); px = rng.integers(0, w, n_mote)
    M[py, px] = np.maximum(M[py, px], rng.uniform(0.55, 0.82, n_mote).astype(np.float32))
    CC[py, px] = np.maximum(CC[py, px], rng.uniform(0.45, 0.78, n_mote).astype(np.float32))

    if _CV2_OK:
        # 3) WIPE-STREAK STORM (4-18 px) — 5x density
        n_drag = int(np.clip(2200 * (mn / 2048.0) ** 2, 700, 5000))
        for _ in range(n_drag):
            cx = int(rng.uniform(2, w - 2)); cy = int(rng.uniform(2, h - 2))
            length = int(rng.uniform(4.0, 18.0) * scale)
            ang = float(rng.uniform(-0.20, 0.20))
            x2 = int(np.clip(cx + np.cos(ang) * length, 0, w - 1))
            y2 = int(np.clip(cy + np.sin(ang) * length, 0, h - 1))
            _cv2.line(M, (cx, cy), (x2, y2), float(rng.uniform(0.40, 0.80)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R_ch, (cx, cy), (x2, y2), float(rng.uniform(0.18, 0.35)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (x2, y2), float(rng.uniform(0.35, 0.65)), 1, lineType=_cv2.LINE_AA)

        # 4) FINGERPRINT LOOP ARCS — small curved 3-7 px
        n_loop = int(np.clip(900 * (mn / 2048.0) ** 2, 300, 2000))
        for _ in range(n_loop):
            cx = int(rng.uniform(3, w - 3)); cy = int(rng.uniform(3, h - 3))
            r = max(1, int(rng.uniform(1.5, 3.0) * scale))
            a0 = float(rng.uniform(0, 360)); a1 = a0 + float(rng.uniform(80, 170))
            _cv2.ellipse(M, (cx, cy), (r, r), 0, a0, a1, float(rng.uniform(0.35, 0.65)), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R_ch, (cx, cy), (r, r), 0, a0, a1, float(rng.uniform(0.18, 0.32)), 1, lineType=_cv2.LINE_AA)

        # 5) FINGERPRINT SMUDGE CLUSTERS — darker oily patches (R kept LOW to stay composite-dark)
        n_smudge = int(np.clip(450 * (mn / 2048.0) ** 2, 150, 1100))
        for _ in range(n_smudge):
            cx = int(rng.uniform(0.04, 0.96) * w); cy = int(rng.uniform(0.04, 0.96) * h)
            r = max(2, int(rng.uniform(4.0, 10.0) * scale))
            _cv2.circle(M, (cx, cy), r, float(rng.uniform(0.15, 0.38)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(rng.uniform(0.18, 0.32)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), r, float(rng.uniform(0.22, 0.45)), -1, lineType=_cv2.LINE_AA)

    # 6) Settled-dust drift band
    band = _normalize(multi_scale_noise(shape, [38.0], [1.0], int(seed) + 77119))
    M = M + (band - 0.5) * 0.10
    R_ch = R_ch + (band - 0.5) * 0.08
    CC = CC + (band - 0.5) * 0.08

    # 7) NEW HERO (R6-Loop tick 2026-05-26): SWIRL-VORTEX HAND-WIPE SPIRALS.
    #    Unexpected motif: instead of just straight wipe streaks, a few
    #    circular hand-polish vortex spirals (parametric Archimedean curve
    #    r = a + b*t) plotted as polylines — like someone wiped the dust
    #    in tight circles with a rag. 8-16 spirals at 14-22 px radius,
    #    TIGHT per-spiral chroma jitter (±0.05 from a clean-wipe palette).
    if _CV2_OK:
        n_swirl = int(rng.integers(8, 17))
        for _ in range(n_swirl):
            cx_s = float(rng.uniform(0.08, 0.92) * w)
            cy_s = float(rng.uniform(0.08, 0.92) * h)
            r_max = float(rng.uniform(14.0, 22.0)) * scale
            turns = float(rng.uniform(1.8, 2.8))
            steps = 36
            t_vals = np.linspace(0.0, turns * 2.0 * np.pi, steps, dtype=np.float32)
            rad_vals = (t_vals / (turns * 2.0 * np.pi)) * r_max
            xs = (cx_s + np.cos(t_vals) * rad_vals).astype(np.int32)
            ys = (cy_s + np.sin(t_vals) * rad_vals).astype(np.int32)
            pts = np.stack([xs, ys], axis=-1)
            base_M = 0.78 + float(rng.uniform(-0.05, 0.05))
            base_R = 0.18 + float(rng.uniform(-0.05, 0.05))
            base_CC = 0.72 + float(rng.uniform(-0.05, 0.05))
            _cv2.polylines(M, [pts], False, float(np.clip(base_M, 0, 1)), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(R_ch, [pts], False, float(np.clip(base_R, 0, 1)), 1, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [pts], False, float(np.clip(base_CC, 0, 1)), 1, lineType=_cv2.LINE_AA)

    out = np.stack([M, R_ch, CC], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)

dry_dust_film._spb_concept_complete = True


def morning_dew_fog(shape, seed, sm, fog_density=0.55, **kwargs):
    """morning_dew_fog.

    identity: R6-CREATIVE — DEW-COVERED WINDSHIELD AT DAWN. Thousands of
    1-4 px round water beads with bright top-left specular highlight and
    dark crescent underbelly carpet the canvas. NEW HERO motifs:
    (HERO A) 12-22 LARGE HERO DEW DROPS — 6-10 px chubby beads with full
    bright lit-cap, dark lensing shadow, and a 2-3 px secondary
    reflection point inside (sells the optical lens effect); (HERO B)
    DEW STREAK TRAILS — 4-8 short 14-22 px linear bead chains where a
    drop slid before stopping (chain of 4-6 contiguous beads, decreasing
    size); (HERO C) FAINT BLOOM HALOS around the largest drops, indicating
    surface tension / capillary spreading. Plus original mini beads,
    coalescence patches, and fog micro-sparkle. Per-feature INDEPENDENT
    continuous M/R/CC.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("morning_dew_fog_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) COOL MISTY SUBSTRATE — quiet low-contrast wash
    fM  = _normalize(multi_scale_noise(shape, [4.0, 12.0, 26.0], [0.45, 0.35, 0.20], int(seed) + 11410))
    fR  = _normalize(multi_scale_noise(shape, [4.0, 12.0, 26.0], [0.45, 0.35, 0.20], int(seed) + 11412))
    fCC = _normalize(multi_scale_noise(shape, [4.0, 12.0, 26.0], [0.45, 0.35, 0.20], int(seed) + 11414))
    M    = (0.30 + (fM  - 0.5) * 0.14).astype(np.float32)
    R_ch = (0.72 + (fR  - 0.5) * 0.16).astype(np.float32)
    CC   = (0.52 + (fCC - 0.5) * 0.22).astype(np.float32)

    if _CV2_OK:
        # 2) TINY ROUND BEADS — primary identity. Dense 1-4 px water beads
        n_beads = int(np.clip(5200 * (mn / 2048.0) ** 2, 1800, 18000))
        # Vectorized prep
        bxs = rng.uniform(2, w - 2, n_beads)
        bys = rng.uniform(2, h - 2, n_beads)
        rs = rng.uniform(1.2, 3.8, n_beads) * scale
        # Per-bead independent M/R/CC continuous uniforms
        bMs = rng.uniform(0.18, 0.42, n_beads).astype(np.float32)     # bead body M
        bRs = rng.uniform(0.06, 0.20, n_beads).astype(np.float32)     # smooth water
        bCCs = rng.uniform(0.80, 0.98, n_beads).astype(np.float32)    # mirror gloss
        hM = rng.uniform(0.85, 0.99, n_beads).astype(np.float32)      # highlight specular
        for i in range(n_beads):
            cx = int(bxs[i]); cy = int(bys[i])
            r = max(1, int(rs[i]))
            # Bead body (round filled circle)
            _cv2.circle(M,    (cx, cy), r, float(bMs[i]), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(bRs[i]), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC,   (cx, cy), r, float(bCCs[i]), -1, lineType=_cv2.LINE_AA)
            # Specular highlight pixel at top-left (always offset)
            if r >= 2:
                hx = max(0, min(w - 1, cx - max(1, r // 2)))
                hy = max(0, min(h - 1, cy - max(1, r // 2)))
                M[hy, hx] = float(hM[i])
                CC[hy, hx] = 0.05  # mirror highlight = CC very low (full gloss)
                # Dark crescent underbelly (bottom-right)
                ux = max(0, min(w - 1, cx + max(1, r // 2)))
                uy = max(0, min(h - 1, cy + max(1, r // 2)))
                M[uy, ux] = float(rng.uniform(0.04, 0.14))

        # 3) OVERLAPPING-BEAD COALESCENCE PATCHES — slightly larger beads where
        # multiple beads merged. NOT drips. Round, just larger (4-7 px).
        n_big = int(np.clip(400 * (mn / 2048.0) ** 2, 140, 1400))
        for _ in range(n_big):
            cx = int(rng.uniform(2, w - 2)); cy = int(rng.uniform(2, h - 2))
            r = max(2, int(rng.uniform(4.0, 7.0) * scale))
            _cv2.circle(M,    (cx, cy), r, float(rng.uniform(0.20, 0.40)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(rng.uniform(0.05, 0.18)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC,   (cx, cy), r, float(rng.uniform(0.82, 0.98)), -1, lineType=_cv2.LINE_AA)
            # bright highlight pip at top-left
            hx = max(0, min(w - 1, cx - r // 2))
            hy = max(0, min(h - 1, cy - r // 2))
            _cv2.circle(M, (hx, hy), max(1, r // 3), float(rng.uniform(0.88, 0.99)), -1, lineType=_cv2.LINE_AA)

    # 4) FOG MICRO-SPARKLE — extreme-tiny pinpoint flecks across the canvas
    n_sp = int(np.clip(3000 * (mn / 2048.0) ** 2, 1100, 11000))
    fx = rng.integers(0, w, n_sp); fy = rng.integers(0, h, n_sp)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.45, 0.78, n_sp).astype(np.float32))
    CC[fy, fx] = np.minimum(CC[fy, fx], rng.uniform(0.10, 0.40, n_sp).astype(np.float32))

    # 5) HERO A — LARGE HERO DEW DROPS with internal secondary reflection
    if _CV2_OK:
        n_hero = int(rng.integers(12, 23))
        for _ in range(n_hero):
            cx = int(rng.uniform(0.05, 0.95) * w); cy = int(rng.uniform(0.05, 0.95) * h)
            rH = max(3, int(rng.uniform(6.0, 10.0) * scale))
            # Faint bloom halo (HERO C inline with each big drop)
            _cv2.circle(M, (cx, cy), rH + 3, float(rng.uniform(0.35, 0.50)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rH + 3, float(rng.uniform(0.55, 0.72)), -1, lineType=_cv2.LINE_AA)
            # Bead body
            _cv2.circle(M, (cx, cy), rH, float(rng.uniform(0.22, 0.42)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), rH, float(rng.uniform(0.05, 0.18)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), rH, float(rng.uniform(0.84, 0.99)), -1, lineType=_cv2.LINE_AA)
            # Bright lit cap top-left
            hxs = max(0, cx - rH // 2); hys = max(0, cy - rH // 2)
            _cv2.circle(M, (hxs, hys), max(1, rH // 2), float(rng.uniform(0.88, 0.99)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (hxs, hys), max(1, rH // 2), float(rng.uniform(0.02, 0.10)), -1, lineType=_cv2.LINE_AA)
            # Secondary internal reflection (small bright dot inside, lower-right of cap)
            sxs = max(0, cx - rH // 4); sys = max(0, cy - rH // 4)
            M[sys, sxs] = float(rng.uniform(0.92, 0.99))
            CC[sys, sxs] = 0.03
            # Dark underbelly crescent (bottom-right outside)
            uxs = min(w - 1, cx + max(1, rH // 2)); uys = min(h - 1, cy + max(1, rH // 2))
            _cv2.circle(M, (uxs, uys), max(1, rH // 3), float(rng.uniform(0.04, 0.13)), -1, lineType=_cv2.LINE_AA)

        # HERO B — DEW STREAK TRAILS: 4-8 chains of decreasing beads
        n_trail = int(rng.integers(4, 9))
        for _ in range(n_trail):
            sx = float(rng.uniform(0.10, 0.90) * w)
            sy = float(rng.uniform(0.10, 0.85) * h)
            ang = float(rng.uniform(np.pi * 0.20, np.pi * 0.80))  # mostly downward
            length = float(rng.uniform(14.0, 22.0) * scale)
            n_in = int(rng.integers(4, 7))
            for k in range(n_in):
                t = k / max(n_in - 1, 1)
                tx = int(np.clip(sx + np.cos(ang) * length * t, 0, w - 1))
                ty = int(np.clip(sy + np.sin(ang) * length * t, 0, h - 1))
                rT = max(1, int((4.0 - 3.0 * t) * scale))  # 4 -> 1 px
                _cv2.circle(M, (tx, ty), rT, float(rng.uniform(0.22, 0.40)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R_ch, (tx, ty), rT, float(rng.uniform(0.05, 0.16)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (tx, ty), rT, float(rng.uniform(0.82, 0.98)), -1, lineType=_cv2.LINE_AA)
                # Tiny lit cap
                if rT >= 2:
                    hxs2 = max(0, tx - 1); hys2 = max(0, ty - 1)
                    M[hys2, hxs2] = float(rng.uniform(0.85, 0.98))

    out = np.stack([np.clip(M, 0, 1), np.clip(R_ch, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)


morning_dew_fog._spb_concept_complete = True


def tarmac_grit_embed(shape, seed, sm, grit_density=0.005, **kwargs):
    """tarmac_grit_embed.

    identity: Round-6 CREATIVE rebuild — fresh blacktop with HERO TIRE-LINE
    GROOVES carved through and HERO BOULDER AGGREGATE (8-12 px star-shaped
    stone chunks with full lit/shadow shading) embedded in the surface,
    surrounded by a dense field of sharp angular shards 4-14 px. New
    differentiators on top of the embedded-aggregate identity: tire-track
    streaks (rough darker bands), bright lit-edge rim per boulder, full
    star-polygon stone shapes (not just triangles). Stacked: (A) glossy
    clearcoat substrate, INDEPENDENT M/R/CC, (B) HERO BOULDERS — 6-14
    star-polygon stones 8-12 px with dramatic lit-rim + shadow-seat, (C)
    HERO TIRE-LINE GROOVES — 2-4 parallel band streaks across the panel
    (each band 2-3 px thick, length 60-110 px) where tires darkened and
    roughened the surface, (D) standard angular shards 4-14 px sunken into
    coat with lit/shadow edges, (E) dark press-pits 1-3 px round indents,
    (F) micro-aggregate dust carpet, (G) glossy clearcoat highlight sparks.
    Per-feature INDEPENDENT continuous M/R/CC with WIDE chroma.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("tarmac_grit_embed_r5") % 10000))
    mn = min(h, w); scale = max(mn / 2048.0, 0.25)

    # 1) GLOSSY CLEARCOAT SUBSTRATE
    fM  = _normalize(multi_scale_noise(shape, [2.0, 6.0, 14.0], [0.45, 0.35, 0.20], int(seed) + 9661))
    fR  = _normalize(multi_scale_noise(shape, [2.5, 7.0, 18.0], [0.45, 0.35, 0.20], int(seed) + 9662))
    fCC = _normalize(multi_scale_noise(shape, [3.0, 8.0, 20.0], [0.45, 0.35, 0.20], int(seed) + 9663))
    M    = (0.50 + (fM  - 0.5) * 0.18).astype(np.float32)
    R_ch = (0.30 + (fR  - 0.5) * 0.16).astype(np.float32)
    CC   = (0.22 + (fCC - 0.5) * 0.18).astype(np.float32)

    if _CV2_OK:
        # 1.5) HERO TIRE-LINE GROOVES — 2-4 darker rougher bands across the panel
        n_tracks = int(rng.integers(2, 5))
        for _ in range(n_tracks):
            track_ang = float(rng.uniform(-0.3, 0.3))  # near-horizontal
            if rng.random() < 0.4:
                track_ang = float(np.pi * 0.5 + rng.uniform(-0.3, 0.3))  # vertical alt
            cx0 = float(rng.uniform(0.0, 1.0) * w)
            cy0 = float(rng.uniform(0.0, 1.0) * h)
            L = float(rng.uniform(60.0, 110.0) * scale)
            n_strands = int(rng.integers(2, 5))
            base_offset = float(rng.uniform(0, 2 * np.pi))
            for s in range(n_strands):
                # parallel strands of the tire pattern
                perp = (np.cos(track_ang + np.pi / 2.0), np.sin(track_ang + np.pi / 2.0))
                off = (s - n_strands / 2.0) * float(rng.uniform(1.5, 2.5) * scale)
                sx0 = cx0 + perp[0] * off
                sy0 = cy0 + perp[1] * off
                sx1 = sx0 + np.cos(track_ang) * L
                sy1 = sy0 + np.sin(track_ang) * L
                thick = max(1, int(scale * 1.5))
                _cv2.line(M, (int(sx0), int(sy0)), (int(sx1), int(sy1)),
                          float(rng.uniform(0.10, 0.28)), thick, lineType=_cv2.LINE_AA)
                _cv2.line(R_ch, (int(sx0), int(sy0)), (int(sx1), int(sy1)),
                          float(rng.uniform(0.78, 0.96)), thick, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (int(sx0), int(sy0)), (int(sx1), int(sy1)),
                          float(rng.uniform(0.55, 0.82)), thick, lineType=_cv2.LINE_AA)

        # 1.6) HERO BOULDERS — large star-polygon aggregate stones 8-12 px
        n_boulders = int(rng.integers(6, 15))
        for _ in range(n_boulders):
            cx = float(rng.uniform(0.05, 0.95) * w)
            cy = float(rng.uniform(0.05, 0.95) * h)
            base_r = float(rng.uniform(4.5, 6.5) * scale)
            n_verts = int(rng.integers(5, 9))
            base_ang = float(rng.uniform(0, 2 * np.pi))
            verts = []
            for k in range(n_verts):
                a = base_ang + k * (2 * np.pi / n_verts) + float(rng.uniform(-0.3, 0.3))
                rr = base_r * float(rng.uniform(0.55, 1.15))
                verts.append([int(np.clip(cx + np.cos(a) * rr, 0, w - 1)),
                              int(np.clip(cy + np.sin(a) * rr, 0, h - 1))])
            pts = np.array([verts], dtype=np.int32)
            bM = float(rng.uniform(0.22, 0.45))
            bR = float(rng.uniform(0.70, 0.92))
            bCC = float(rng.uniform(0.55, 0.80))
            _cv2.fillPoly(M, pts, bM, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R_ch, pts, bR, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, pts, bCC, lineType=_cv2.LINE_AA)
            # Dramatic lit-edge rim on lit side
            light_dir = float(rng.uniform(0, 2 * np.pi))
            for i in range(n_verts):
                v1 = verts[i]; v2 = verts[(i + 1) % n_verts]
                midx = (v1[0] + v2[0]) * 0.5 - cx
                midy = (v1[1] + v2[1]) * 0.5 - cy
                lit_dot = midx * np.cos(light_dir) + midy * np.sin(light_dir)
                if lit_dot > 0:
                    _cv2.line(M, tuple(v1), tuple(v2),
                              float(rng.uniform(0.82, 0.98)), 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, tuple(v1), tuple(v2),
                              float(rng.uniform(0.05, 0.18)), 1, lineType=_cv2.LINE_AA)
                else:
                    _cv2.line(M, tuple(v1), tuple(v2),
                              float(rng.uniform(0.04, 0.14)), 1, lineType=_cv2.LINE_AA)

        # 2) ANGULAR AGGREGATE SHARDS — sharp polygons embedded into the coat
        n_shards = int(np.clip(1200 * (mn / 2048.0) ** 2, 450, 4800))
        for _ in range(n_shards):
            cx = float(rng.uniform(0.02, 0.98) * w)
            cy = float(rng.uniform(0.02, 0.98) * h)
            base_r = float(rng.uniform(2.0, 7.0) * scale)
            n_verts = int(rng.integers(3, 6))  # triangles, quads, pentagons
            base_ang = float(rng.uniform(0, 2 * np.pi))
            verts = []
            for k in range(n_verts):
                a = base_ang + k * (2 * np.pi / n_verts) + float(rng.uniform(-0.4, 0.4))
                rr = base_r * float(rng.uniform(0.55, 1.0))  # irregular
                verts.append([int(np.clip(cx + np.cos(a) * rr, 0, w - 1)),
                              int(np.clip(cy + np.sin(a) * rr, 0, h - 1))])
            pts = np.array([verts], dtype=np.int32)
            sh_M = float(rng.uniform(0.18, 0.45))   # dark stone body
            sh_R = float(rng.uniform(0.72, 0.94))   # rough aggregate
            sh_CC = float(rng.uniform(0.55, 0.82))  # dull
            _cv2.fillPoly(M,    pts, sh_M, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R_ch, pts, sh_R, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC,   pts, sh_CC, lineType=_cv2.LINE_AA)
            # Shadow edge (dark) on one side
            light_ang = base_ang + np.pi  # opposite side gets shadow
            # Bright lit-edge on lit side — draw one polyline segment
            lit_idx = 0
            shadow_idx = (n_verts // 2) % n_verts
            if n_verts >= 2:
                v1 = tuple(verts[lit_idx]); v2 = tuple(verts[(lit_idx + 1) % n_verts])
                _cv2.line(M, v1, v2, float(rng.uniform(0.80, 0.96)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, v1, v2, float(rng.uniform(0.06, 0.20)), 1, lineType=_cv2.LINE_AA)
                v3 = tuple(verts[shadow_idx]); v4 = tuple(verts[(shadow_idx + 1) % n_verts])
                _cv2.line(M, v3, v4, float(rng.uniform(0.04, 0.14)), 1, lineType=_cv2.LINE_AA)

        # 3) SMALL DARK PRESS-PITS — round indents where small grit sunk
        n_pits = int(np.clip(900 * (mn / 2048.0) ** 2, 300, 3000))
        for _ in range(n_pits):
            cx = int(rng.integers(0, w)); cy = int(rng.integers(0, h))
            r = max(1, int(rng.uniform(1.0, 2.5) * scale))
            _cv2.circle(M,    (cx, cy), r, float(rng.uniform(0.10, 0.26)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R_ch, (cx, cy), r, float(rng.uniform(0.74, 0.94)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC,   (cx, cy), r, float(rng.uniform(0.45, 0.75)), -1, lineType=_cv2.LINE_AA)

    # 4) MICRO-AGGREGATE DUST — fine vectorized grit
    n_d = int(np.clip(3500 * (mn / 2048.0) ** 2, 1200, 12000))
    dx = rng.integers(0, w, n_d); dy = rng.integers(0, h, n_d)
    M[dy, dx] = np.minimum(M[dy, dx], rng.uniform(0.18, 0.40, n_d).astype(np.float32))
    R_ch[dy, dx] = np.maximum(R_ch[dy, dx], rng.uniform(0.65, 0.92, n_d).astype(np.float32))

    # 5) GLOSSY CLEARCOAT HIGHLIGHTS — bright pixel sparks between shards
    n_fl = int(np.clip(900 * (mn / 2048.0) ** 2, 300, 3000))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.65, 0.92, n_fl).astype(np.float32))
    CC[fy, fx] = np.minimum(CC[fy, fx], rng.uniform(0.04, 0.18, n_fl).astype(np.float32))

    out = np.stack([np.clip(M, 0, 1), np.clip(R_ch, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(np.clip(out, 0.0, 1.0), sm)


tarmac_grit_embed._spb_concept_complete = True


# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------

WEATHER_TRACK_PATTERNS = {
    'rain_droplet_beads': rain_droplet_beads,
    'mud_splatter_random': mud_splatter_random,
    'wet_track_gloss': wet_track_gloss,
    'dry_dust_film': dry_dust_film,
    'morning_dew_fog': morning_dew_fog,
    'tarmac_grit_embed': tarmac_grit_embed,
}

__all__ = [
    'WEATHER_TRACK_PATTERNS',
    'rain_droplet_beads',
    'mud_splatter_random',
    'wet_track_gloss',
    'dry_dust_film',
    'morning_dew_fog',
    'tarmac_grit_embed',
]

