"""Racing-pivot batch 1 — RACE-LIVERY aesthetic spec patterns.

Owner directive 2026-05-26: shift to race-livery looks.
This module ships the FIRST 10 race-livery rebuilds, replacing 10
abstract / academic slots whose IDs have been renamed-and-aliased in
PATTERN_CATALOG. Backward-compat is preserved by `spec_pattern_aliases.py`
+ alias entries in PATTERN_CATALOG.

HARD SIZE DOCTRINE (re-committed 2026-05-26):
    - Every primitive feature: 8-32 px at 256² (sub-features 1-12 px)
    - At larger canvases, features scale by `mn / 256.0` (so 8-32 stays
      perceptually small on car panels)
    - NO macro / panel-scale / chunky-blob features

Families this module covers (in priority order):
    PREDATOR SKINS:  dragon_scale_macro, alligator_hide, snake_scale_diamond
    GOTHIC / HORROR: voodoo_sigil_field, hex_blood_drip
    ENGINE-TURN:     engine_turn_radial_arc, jeweled_guilloche
    FIRE / HEAT:     ember_field
    CARBON UNIQUE:   forged_carbon_chip
    HOLO / SHIFT:    holo_prism_shift

All signatures: (shape, seed, sm, **kwargs) -> float32 (h, w, 3) in [0, 1].
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


# ----------------------------------------------------------------------------
# helper — irregular dropped-fleck base substrate (independent M/R/CC FBM)
# ----------------------------------------------------------------------------

def _make_substrate(shape, seed, m_base, r_base, cc_base, span=0.10):
    """Build a low-amplitude per-channel FBM substrate. Returns (M, R, CC)."""
    h, w = shape
    nm = _normalize(multi_scale_noise(shape, [1.6, 3.4, 7.2], [0.5, 0.3, 0.2], int(seed) + 1101))
    nr = _normalize(multi_scale_noise(shape, [1.7, 3.6, 7.8], [0.5, 0.3, 0.2], int(seed) + 1102))
    nc = _normalize(multi_scale_noise(shape, [1.8, 3.8, 8.4], [0.5, 0.3, 0.2], int(seed) + 1103))
    M = (m_base + (nm - 0.5) * span).astype(np.float32)
    R = (r_base + (nr - 0.5) * span).astype(np.float32)
    CC = (cc_base + (nc - 0.5) * span).astype(np.float32)
    return M, R, CC


def _finalize(M, R, CC, sm, name):
    out = np.stack([
        np.clip(M, 0.0, 1.0),
        np.clip(R, 0.0, 1.0),
        np.clip(CC, 0.0, 1.0),
    ], axis=-1).astype(np.float32)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), name)


# ============================================================================
# 1) VOODOO_SIGIL_FIELD  (Gothic)
# ============================================================================

def pattern_voodoo_sigil_field(shape, seed, sm, **kwargs):
    """voodoo_sigil_field.

    identity: dense field of ritual/occult sigils (pentagrams, hex-stars,
    crossbones, eye-glyphs) at 10-22 px each, scattered across the canvas
    with per-sigil INDEPENDENT M/R/CC and rotation. Ink-bleed halos.
    HERO: 8-14 'blood' spatters (deep red CC) where the rituals converge.
    Every primitive 1-22 px. Race-livery occult aesthetic.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 770101)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    M, R, CC = _make_substrate(shape, seed, 0.22, 0.62, 0.20, 0.10)

    n_sig = int(np.clip(110 * s * s, 60, 260))
    if _CV2_OK:
        for _ in range(n_sig):
            cx = int(rng.integers(8, w - 8))
            cy = int(rng.integers(8, h - 8))
            rad = int(rng.uniform(5.0, 11.0) * s)  # 5-11 sigil radius => 10-22 px feature
            rad = max(5, min(rad, 16))
            sm_M = float(rng.uniform(0.55, 0.99))
            sm_R = float(rng.uniform(0.05, 0.30))
            sm_C = float(rng.uniform(0.08, 0.95))
            kind = int(rng.integers(0, 5))
            rot = float(rng.uniform(0, 2 * np.pi))

            # ink halo (soft dark wash 2-3 px outside)
            _cv2.circle(M, (cx, cy), rad + 2, float(sm_M * 0.4), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), rad + 2, float(sm_R + 0.18), 1, lineType=_cv2.LINE_AA)

            if kind == 0:
                # PENTAGRAM 5-point star
                pts = []
                for k in range(5):
                    a = rot + k * (2 * np.pi / 5) - np.pi / 2
                    pts.append([cx + int(np.cos(a) * rad), cy + int(np.sin(a) * rad)])
                # connect every 2nd vertex to draw star
                order = [0, 2, 4, 1, 3, 0]
                star_pts = np.array([pts[i] for i in order], dtype=np.int32)
                _cv2.polylines(M, [star_pts], False, sm_M, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [star_pts], False, sm_R, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [star_pts], False, sm_C, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (cx, cy), rad, sm_M, 1, lineType=_cv2.LINE_AA)
            elif kind == 1:
                # HEX STAR (Star of David)
                pts1 = []
                pts2 = []
                for k in range(3):
                    a1 = rot + k * (2 * np.pi / 3) - np.pi / 2
                    a2 = rot + k * (2 * np.pi / 3) + np.pi / 6
                    pts1.append([cx + int(np.cos(a1) * rad), cy + int(np.sin(a1) * rad)])
                    pts2.append([cx + int(np.cos(a2) * rad), cy + int(np.sin(a2) * rad)])
                tri1 = np.array(pts1, dtype=np.int32)
                tri2 = np.array(pts2, dtype=np.int32)
                _cv2.polylines(M, [tri1], True, sm_M, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [tri2], True, sm_M, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [tri1], True, sm_R, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(R, [tri2], True, sm_R, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [tri1], True, sm_C, 1, lineType=_cv2.LINE_AA)
                _cv2.polylines(CC, [tri2], True, sm_C, 1, lineType=_cv2.LINE_AA)
            elif kind == 2:
                # CROSSBONES — a small X with end-knobs
                for sign in (-1, 1):
                    x0 = cx + int(np.cos(rot + sign * 0.6) * rad)
                    y0 = cy + int(np.sin(rot + sign * 0.6) * rad)
                    x1 = cx - int(np.cos(rot + sign * 0.6) * rad)
                    y1 = cy - int(np.sin(rot + sign * 0.6) * rad)
                    _cv2.line(M, (x0, y0), (x1, y1), sm_M, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, (x0, y0), (x1, y1), sm_R, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, (x0, y0), (x1, y1), sm_C, 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(M, (x0, y0), max(1, rad // 4), sm_M, -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(M, (x1, y1), max(1, rad // 4), sm_M, -1, lineType=_cv2.LINE_AA)
            elif kind == 3:
                # EYE GLYPH — almond outline + pupil
                ax = rad
                ay = max(2, rad // 2)
                ellipse_rect = ((cx, cy), (ax * 2, ay * 2), float(np.degrees(rot)))
                _cv2.ellipse(M, ellipse_rect, sm_M, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, ellipse_rect, sm_R, 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, ellipse_rect, sm_C, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (cx, cy), max(1, rad // 3), sm_M, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), max(1, rad // 3), sm_C, -1, lineType=_cv2.LINE_AA)
            else:
                # INVERTED-CROSS HEX
                _cv2.line(M, (cx, cy - rad), (cx, cy + rad), sm_M, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx - rad // 2, cy + rad // 3), (cx + rad // 2, cy + rad // 3), sm_M, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx, cy - rad), (cx, cy + rad), sm_R, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (cx - rad // 2, cy + rad // 3), (cx + rad // 2, cy + rad // 3), sm_R, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx, cy - rad), (cx, cy + rad), sm_C, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (cx - rad // 2, cy + rad // 3), (cx + rad // 2, cy + rad // 3), sm_C, 1, lineType=_cv2.LINE_AA)

        # HERO — 8-14 blood spatters (red CC = deep red, low M, high R)
        n_blood = int(rng.integers(8, 15))
        for _ in range(n_blood):
            bx = int(rng.integers(6, w - 6))
            by = int(rng.integers(6, h - 6))
            br = int(rng.uniform(4.0, 9.0) * s)
            br = max(3, min(br, 12))
            _cv2.circle(M, (bx, by), br, float(rng.uniform(0.08, 0.30)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (bx, by), br, float(rng.uniform(0.75, 0.96)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (bx, by), br, float(rng.uniform(0.04, 0.20)), -1, lineType=_cv2.LINE_AA)
            # micro spatter satellites (1-3 px each)
            for _s in range(int(rng.integers(4, 9))):
                sa = float(rng.uniform(0, 2 * np.pi))
                sd = float(rng.uniform(br * 1.2, br * 2.4))
                sxp = int(np.clip(bx + np.cos(sa) * sd, 0, w - 1))
                syp = int(np.clip(by + np.sin(sa) * sd, 0, h - 1))
                rr_s = max(1, int(rng.uniform(0.8, 2.4) * s))
                _cv2.circle(M, (sxp, syp), rr_s, float(rng.uniform(0.10, 0.25)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (sxp, syp), rr_s, float(rng.uniform(0.70, 0.95)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (sxp, syp), rr_s, float(rng.uniform(0.05, 0.18)), -1, lineType=_cv2.LINE_AA)

    # per-pixel ink-grain flecks
    n_fl = int(np.clip(h * w / 220.0, 600, 5000))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(-0.18, 0.22, n_fl).astype(np.float32), 0, 1)
    R[fy, fx] = np.clip(R[fy, fx] + rng.uniform(-0.18, 0.22, n_fl).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.18, 0.22, n_fl).astype(np.float32), 0, 1)

    return _finalize(M, R, CC, sm, "voodoo_sigil_field")
pattern_voodoo_sigil_field._spb_concept_complete = True


# ============================================================================
# 2) HEX_BLOOD_DRIP  (Gothic)
# ============================================================================

def pattern_hex_blood_drip(shape, seed, sm, **kwargs):
    """hex_blood_drip.

    identity: viscous dark-fluid streaks descending. 30-60 narrow drip
    trails 4-10 px wide x 24-80 px long, terminating in heavy bead tips.
    HERO: 4-8 small occult symbols inscribed (10-18 px) where drips
    converge. Per-drip INDEPENDENT M/R/CC. Per-feature 4-80 px (height
    capped to 80px; width 4-10 px keeps the streak silhouette fine).
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 770201)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    M, R, CC = _make_substrate(shape, seed, 0.18, 0.66, 0.22, 0.08)

    n_drip = int(np.clip(46 * s * s, 30, 90))
    drip_xs = []  # for hero placement
    if _CV2_OK:
        for _ in range(n_drip):
            x = int(rng.integers(2, w - 2))
            # Drips start ANYWHERE on canvas — fixes edge-anchoring bug
            # (was: y_start in top h//3 → bottom 2/3 empty)
            y_start = int(rng.integers(0, max(1, h - 12)))
            # Length capped at remaining canvas so drip doesn't get cut off
            max_len = h - y_start - 2
            length = int(min(max_len, rng.uniform(16.0, 60.0) * s * 0.6))
            length = max(8, length)
            width = int(rng.uniform(2.0, 5.0) * s)
            width = max(2, min(width, 5))
            dM = float(rng.uniform(0.12, 0.32))
            dR = float(rng.uniform(0.72, 0.96))
            dCC = float(rng.uniform(0.05, 0.20))
            # head bead
            _cv2.circle(M, (x, y_start), width + 1, dM, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (x, y_start), width + 1, dR, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (x, y_start), width + 1, dCC, -1, lineType=_cv2.LINE_AA)
            # streak body (taper)
            steps = max(8, length)
            wob = np.cumsum(rng.uniform(-0.35, 0.35, steps)) * 0.6
            for i in range(steps):
                t = i / max(steps - 1, 1)
                yi = y_start + i
                if yi >= h:
                    break
                taper = (1.0 - t) ** 0.7
                hw = max(1, int(width * taper))
                xc = int(np.clip(x + wob[i], hw, w - hw - 1))
                lo = max(0, xc - hw); hi = min(w, xc + hw + 1)
                a = 0.65 * taper + 0.15
                M[yi, lo:hi] = M[yi, lo:hi] * (1 - a) + dM * a
                R[yi, lo:hi] = R[yi, lo:hi] * (1 - a) + dR * a
                CC[yi, lo:hi] = CC[yi, lo:hi] * (1 - a) + dCC * a
            # heavy bead tip
            y_end = min(h - 1, y_start + steps)
            tip_r = max(2, width + 2)
            _cv2.circle(M, (int(np.clip(x + wob[-1], 0, w - 1)), y_end), tip_r, float(dM * 0.6), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (int(np.clip(x + wob[-1], 0, w - 1)), y_end), tip_r, float(dR * 1.0), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (int(np.clip(x + wob[-1], 0, w - 1)), y_end), tip_r, float(dCC * 0.7), -1, lineType=_cv2.LINE_AA)
            drip_xs.append((int(np.clip(x + wob[-1], 0, w - 1)), y_end))

        # HERO — 4-8 inscribed occult symbols near drip convergence
        n_sym = int(rng.integers(4, 9))
        for _ in range(n_sym):
            if drip_xs:
                base = drip_xs[int(rng.integers(0, len(drip_xs)))]
                hx = int(np.clip(base[0] + rng.integers(-12, 13), 8, w - 8))
                hy = int(np.clip(base[1] + rng.integers(-8, 9), 8, h - 8))
            else:
                hx = int(rng.integers(8, w - 8))
                hy = int(rng.integers(8, h - 8))
            rr = int(rng.uniform(5.0, 9.0) * s)
            rr = max(5, min(rr, 9))
            sm_M = float(rng.uniform(0.75, 0.99))
            sm_R = float(rng.uniform(0.04, 0.18))
            sm_C = float(rng.uniform(0.12, 0.90))
            # ring + cross + inner tick (sigil-like)
            _cv2.circle(M, (hx, hy), rr, sm_M, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (hx, hy), rr, sm_R, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (hx, hy), rr, sm_C, 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, (hx - rr, hy), (hx + rr, hy), sm_M, 1, lineType=_cv2.LINE_AA)
            _cv2.line(M, (hx, hy - rr), (hx, hy + rr), sm_M, 1, lineType=_cv2.LINE_AA)
            _cv2.circle(M, (hx, hy), max(1, rr // 3), sm_M, -1, lineType=_cv2.LINE_AA)

    # micro splatter dots (1-3 px) — extra fine grain
    n_sp = int(np.clip(h * w / 280.0, 400, 4000))
    sy = rng.integers(0, h, n_sp); sx = rng.integers(0, w, n_sp)
    M[sy, sx] = np.clip(M[sy, sx] + rng.uniform(-0.10, 0.20, n_sp).astype(np.float32), 0, 1)
    R[sy, sx] = np.clip(R[sy, sx] + rng.uniform(-0.10, 0.20, n_sp).astype(np.float32), 0, 1)
    CC[sy, sx] = np.clip(CC[sy, sx] + rng.uniform(-0.10, 0.20, n_sp).astype(np.float32), 0, 1)

    return _finalize(M, R, CC, sm, "hex_blood_drip")
pattern_hex_blood_drip._spb_concept_complete = True


# ============================================================================
# 3) EMBER_FIELD  (Fire / Heat)
# ============================================================================

def pattern_ember_field(shape, seed, sm, **kwargs):
    """ember_field.

    identity: 200-400 glowing embers 3-8 px with hot bright CC cores +
    cooling outer halos. Vertical motion smear suggests heat rise. 8-14
    'burning coal' hot-spots at 10-18 px. All features 3-18 px. Per-ember
    INDEPENDENT chroma (cores white-hot → red-hot → ash via CC sweep).
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 770301)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    # Dark char/coal substrate — should read as nearly BLACK in thumbnail composite
    # (M=0.10 → R-band ~26, R=0.20 → G-band ~51, CC=0.05 → B-band ~13 = very dark)
    M = np.full((h, w), 0.10, dtype=np.float32)
    R = np.full((h, w), 0.20, dtype=np.float32)
    CC = np.full((h, w), 0.05, dtype=np.float32)

    if _CV2_OK:
        # subtle vertical heat-rise smear in M (heat haze)
        smear = _normalize(multi_scale_noise(shape, [2.5, 7.0, 18.0], [0.45, 0.35, 0.20], int(seed) + 770305))
        smear = _gauss(smear.astype(np.float32), sigma=max(2.0, s * 1.4))
        smear = _normalize(smear)
        M = np.clip(M + (smear - 0.5) * 0.08, 0, 1)

        n_ember = int(np.clip(300 * s * s, 200, 520))
        for _ in range(n_ember):
            ex = int(rng.integers(2, w - 2))
            ey = int(rng.integers(2, h - 2))
            er = int(rng.uniform(1.5, 4.0) * s)
            er = max(2, min(er, 5))
            # FIRE PALETTE - thumbnail should READ as orange/red/yellow:
            #   M (R-band) HIGH  → strong red channel
            #   R (G-band) MID   → orange (red+green)
            #   CC (B-band) LOW  → no blue, so it stays orange not pink
            # hot=1 → white-yellow (R+G high). hot=0 → red (R high, G low).
            hot = float(rng.uniform(0.2, 1.0))
            core_M = float(0.92 + 0.07 * hot)        # ~0.93-0.99 (always very red)
            core_R = float(0.30 + 0.50 * hot)         # 0.30 (cool red) → 0.80 (hot yellow)
            core_C = float(0.04 + 0.06 * hot)         # ~0.04-0.10 (always very low blue)
            halo_M = float(0.50 + 0.25 * hot)         # dim red glow
            halo_R = float(0.18 + 0.20 * hot)         # slight green for orange tint
            halo_C = float(0.03 + 0.05 * hot)         # near-zero blue
            # outer cooling halo
            _cv2.circle(M, (ex, ey), er + 2, halo_M, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (ex, ey), er + 2, halo_R, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (ex, ey), er + 2, halo_C, -1, lineType=_cv2.LINE_AA)
            # hot core
            _cv2.circle(M, (ex, ey), er, core_M, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (ex, ey), er, core_R, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (ex, ey), er, core_C, -1, lineType=_cv2.LINE_AA)
            # tiny upward spark trail (1-2 px) on hottest embers
            if hot > 0.6 and rng.random() < 0.4:
                for k in range(int(rng.integers(2, 5))):
                    ty = ey - int(k * rng.uniform(1.5, 3.0) * s)
                    tx = ex + int(rng.uniform(-1.5, 1.5))
                    if 0 <= ty < h and 0 <= tx < w:
                        _cv2.circle(M, (tx, ty), 1, float(0.85 - k * 0.10), -1, lineType=_cv2.LINE_AA)
                        _cv2.circle(CC, (tx, ty), 1, float(0.70 - k * 0.08), -1, lineType=_cv2.LINE_AA)

        # HERO — 8-14 burning coal hot-spots (10-18 px) with extra-bright cores
        n_coal = int(rng.integers(8, 15))
        for _ in range(n_coal):
            cx = int(rng.integers(8, w - 8))
            cy = int(rng.integers(8, h - 8))
            cr = int(rng.uniform(5.0, 9.0) * s)
            cr = max(5, min(cr, 9))
            # outer thermal halo (orange-red glow — M+R rise, CC stays low)
            for ring in range(3):
                rr = cr + (ring + 1) * 2
                a = (3 - ring) / 4.0
                _cv2.circle(M, (cx, cy), rr, float(0.55 + 0.25 * a), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), rr, float(0.30 + 0.20 * a), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), rr, float(0.05 + 0.05 * a), 1, lineType=_cv2.LINE_AA)
            # Hot coal — white-hot core in thumbnail (M+R high, CC low → yellow-white)
            _cv2.circle(M, (cx, cy), cr, float(rng.uniform(0.95, 0.99)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), cr, float(rng.uniform(0.70, 0.95)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), cr, float(rng.uniform(0.05, 0.18)), -1, lineType=_cv2.LINE_AA)
            # ultra-bright pinhole (white-hot center)
            _cv2.circle(M, (cx, cy), max(1, cr // 3), 0.99, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (cx, cy), max(1, cr // 3), 0.95, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (cx, cy), max(1, cr // 3), 0.10, -1, lineType=_cv2.LINE_AA)

    # ash speckle (per-pixel chroma)
    n_ash = int(np.clip(h * w / 360.0, 400, 3500))
    ay = rng.integers(0, h, n_ash); ax = rng.integers(0, w, n_ash)
    M[ay, ax] = np.clip(M[ay, ax] + rng.uniform(-0.15, 0.05, n_ash).astype(np.float32), 0, 1)
    R[ay, ax] = np.clip(R[ay, ax] + rng.uniform(-0.05, 0.18, n_ash).astype(np.float32), 0, 1)
    CC[ay, ax] = np.clip(CC[ay, ax] + rng.uniform(-0.12, 0.18, n_ash).astype(np.float32), 0, 1)

    return _finalize(M, R, CC, sm, "ember_field")
pattern_ember_field._spb_concept_complete = True


# ============================================================================
# 4) DRAGON_SCALE_MACRO  (Predator — HIGHEST PRIORITY)
# ============================================================================

def pattern_dragon_scale_macro(shape, seed, sm, **kwargs):
    """dragon_scale_macro.

    identity: R6 OWNER-REBUILD — *unmistakable dragon scale armor*. Owner
    complaint: "not even close to its name". Previous version drew hex
    pentagons in 4 zones which read as confetti. Fix: classical FISH-SCALE
    D-shape (rounded teardrop with flat top) drawn via FILLED ELLIPSE +
    crescent overlay, packed in a TIGHT staggered grid like real reptile
    skin. ALL scales same orientation (head-up = standard scale flow). One
    cohesive iridescent serpent palette (jade-green base with subtle violet
    iridescence per scale) — NO 4-zone confetti. Each scale 10-16 px tall:
    body fill, bright crescent top-rim highlight, dark crescent bottom-tuck
    shadow, central keel ridge bullet, fine fleck for keratin grain. HERO:
    18-28 spine-crest scales 14-20 px with extra-bright keel + tiny barb.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 770401)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)

    # === SUBSTRATE: dark seam undercoat (composite-dark) ===
    M = np.full((h, w), 0.10, dtype=np.float32)
    R = np.full((h, w), 0.55, dtype=np.float32)
    CC = np.full((h, w), 0.18, dtype=np.float32)
    # subtle iridescent FBM substrate so the gaps between scales aren't dead
    irid = _normalize(multi_scale_noise(shape, [2.0, 4.5, 8.5], [0.5, 0.3, 0.2], int(seed) + 770411))
    CC = np.clip(CC + (irid - 0.5) * 0.10, 0, 1)

    # === ONE cohesive serpent palette (jade-green-violet iridescent) ===
    # Single base — TIGHT ±0.04 per scale so it reads as ONE beast.
    BASE_M, BASE_R, BASE_C = 0.74, 0.20, 0.50  # iridescent jade

    if _CV2_OK:
        # === FISH-SCALE STAGGERED GRID ===
        # Real reptile scales: each scale's TOP curve is exposed, BOTTOM tucks
        # under the row below. Step y by ~0.62 * scale_h so adjacent rows
        # overlap ~38% (canonical fish-scale ratio).
        scale_w = int(np.clip(7 * s, 6, 9))     # half-width (full = 12-18)
        scale_h = int(np.clip(7 * s, 6, 9))     # half-height
        pitch_x = int(scale_w * 1.7)             # horizontal pitch (touching)
        pitch_y = int(scale_h * 1.05)            # vertical pitch (overlap)
        rows = int(h / pitch_y) + 3
        cols = int(w / pitch_x) + 3
        hero_candidates = []
        for ry in range(rows):
            cy = ry * pitch_y - scale_h
            row_off = (ry % 2) * (pitch_x // 2)
            for cxi in range(cols):
                cx = row_off + cxi * pitch_x - scale_w
                if not (-scale_w < cx < w + scale_w and -scale_h < cy < h + scale_h):
                    continue
                # tiny per-scale position jitter
                cx_j = cx + int(rng.integers(-1, 2))
                cy_j = cy + int(rng.integers(-1, 2))

                # TIGHT chroma jitter — same beast everywhere
                pM = float(np.clip(BASE_M + rng.uniform(-0.04, 0.04), 0, 1))
                pR = float(np.clip(BASE_R + rng.uniform(-0.04, 0.04), 0, 1))
                pC = float(np.clip(BASE_C + rng.uniform(-0.05, 0.05), 0, 1))

                # 1) FULL ELLIPSE body — slightly taller than wide (teardrop feel)
                _cv2.ellipse(M, (cx_j, cy_j), (scale_w, scale_h), 0, 0, 360, pM, -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx_j, cy_j), (scale_w, scale_h), 0, 0, 360, pR, -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx_j, cy_j), (scale_w, scale_h), 0, 0, 360, pC, -1, lineType=_cv2.LINE_AA)

                # 2) BRIGHT TOP-RIM CRESCENT — upper half arc (200..340 deg = upper)
                # In cv2 ellipse, 0 deg is +x, angles go clockwise (y down)
                _cv2.ellipse(M, (cx_j, cy_j), (scale_w, scale_h), 0, 195, 345, float(min(0.98, pM + 0.18)), 2, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx_j, cy_j), (scale_w, scale_h), 0, 195, 345, float(min(0.98, pC + 0.22)), 1, lineType=_cv2.LINE_AA)

                # 3) DARK BOTTOM TUCK SHADOW — lower half arc (15..165 deg = lower)
                _cv2.ellipse(M, (cx_j, cy_j), (scale_w, scale_h), 0, 15, 165, float(max(0.03, pM * 0.28)), 2, lineType=_cv2.LINE_AA)

                # 4) CENTRAL KEEL — small bright vertical bullet 2-3 px
                keel_top = (cx_j, cy_j - int(scale_h * 0.55))
                keel_bot = (cx_j, cy_j + int(scale_h * 0.30))
                _cv2.line(M, keel_top, keel_bot, float(min(0.99, pM + 0.22)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, keel_top, keel_bot, float(min(0.99, pC + 0.15)), 1, lineType=_cv2.LINE_AA)

                # 5) MICRO KERATIN POINT — single bright pinprick at scale apex
                if 0 <= cx_j < w and 0 <= keel_top[1] < h and 0 <= keel_top[1]:
                    apex_y = max(0, keel_top[1] + 1)
                    if 0 <= apex_y < h:
                        M[apex_y, max(0, min(w - 1, cx_j))] = 0.96

                # Track for hero promotion
                hero_candidates.append((cx_j, cy_j, scale_w, scale_h))

        # === HERO SPINE CRESTS — 18-28 amplified scales w/ barb spike ===
        n_hero = int(np.clip(rng.integers(18, 29), 16, 32))
        if hero_candidates:
            picks = rng.choice(len(hero_candidates), size=min(n_hero, len(hero_candidates)), replace=False)
            for idx in picks:
                cx, cy, sw_, sh_ = hero_candidates[idx]
                hsw = int(min(sw_ + 2, 10))
                hsh = int(min(sh_ + 2, 11))
                # extra-bright top rim
                _cv2.ellipse(M, (cx, cy), (hsw, hsh), 0, 200, 340, 0.97, 2, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (hsw, hsh), 0, 200, 340, 0.92, 1, lineType=_cv2.LINE_AA)
                # tiny barb spike protruding from apex
                spike_h = int(rng.uniform(3, 5) * s)
                spike_h = max(2, min(spike_h, 5))
                base_l = (cx - 1, cy - hsh)
                base_r = (cx + 1, cy - hsh)
                tip = (cx, cy - hsh - spike_h)
                if tip[1] >= -2:
                    spike = np.array([base_l, base_r, tip], dtype=np.int32)
                    _cv2.fillPoly(M, [spike], 0.94, lineType=_cv2.LINE_AA)
                    _cv2.fillPoly(R, [spike], 0.16, lineType=_cv2.LINE_AA)
                    _cv2.fillPoly(CC, [spike], 0.68, lineType=_cv2.LINE_AA)

    # === FINE BATTLE-WEAR PITTING ===
    n_fl = int(np.clip(h * w / 360.0, 380, 2400))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(-0.06, 0.06, n_fl).astype(np.float32), 0, 1)
    R[fy, fx] = np.clip(R[fy, fx] + rng.uniform(-0.05, 0.05, n_fl).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.06, 0.06, n_fl).astype(np.float32), 0, 1)

    return _finalize(M, R, CC, sm, "dragon_scale_macro")
pattern_dragon_scale_macro._spb_concept_complete = True


# ============================================================================
# 5) ALLIGATOR_HIDE  (Predator — HIGHEST PRIORITY)
# ============================================================================

def pattern_alligator_hide(shape, seed, sm, **kwargs):
    """alligator_hide.

    identity: fine 8-14 px rectangular leathery plates in COHESIVE
    olive-khaki palette (real alligator hide, not Lisa-Frank rainbow).
    Deep dark fissure cracks between plates run the canvas as visible
    seams. Subtle ±0.04 per-plate jitter on a single olive base.
    ~20% of plates get a brighter dorsal-ridge stripe; sub-plate
    micro-pitting on most plates. Optional darker "belly stripe" zone
    via low-freq noise.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 770501)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)

    # DARK fissure substrate — these show through between plates as seams
    M = np.full((h, w), 0.08, dtype=np.float32)
    R = np.full((h, w), 0.90, dtype=np.float32)
    CC = np.full((h, w), 0.14, dtype=np.float32)

    # Two real-alligator zones: dorsal (olive-green) + flank (khaki-olive-brown)
    # Low-freq noise picks zone per region
    zy = np.linspace(0, 3.0, h, dtype=np.float32)
    zx = np.linspace(0, 3.0, w, dtype=np.float32)
    XX, YY = np.meshgrid(zx, zy)
    z_phase = float(rng.uniform(0, 6.28))
    z_field = np.sin(XX * 1.4 + z_phase) + 0.5 * np.cos(YY * 1.9 + z_phase * 0.6)
    z_norm = (z_field - z_field.min()) / max(1e-6, float(np.ptp(z_field)))
    zone_map = (z_norm > 0.5).astype(np.int32)  # 0 = dorsal, 1 = flank

    # Real alligator bases — olive and khaki, NO neon pink/magenta nonsense
    zone_bases = [
        (0.35, 0.62, 0.18),  # dorsal olive-green (M low-mid, R high matte, CC low)
        (0.28, 0.72, 0.22),  # flank khaki-brown (M lower, R higher matte, CC mid-low)
    ]

    if _CV2_OK:
        # OWNER 2026-06-03: "pattern way too big" -> shrink the intrinsic plate
        # size so the alligator scales read smaller/finer at car scale
        # (was 9-12 px @256; now ~6-8 px @256, ~40% finer).
        pitch = max(5, int(rng.uniform(6.0, 8.0) * s))
        cols = w // pitch + 2
        rows = h // pitch + 2
        for ry in range(rows):
            for cxi in range(cols):
                jx = int(rng.uniform(-pitch * 0.15, pitch * 0.15))
                jy = int(rng.uniform(-pitch * 0.15, pitch * 0.15))
                x0 = cxi * pitch + jx
                y0 = ry * pitch + jy
                pw = int(pitch * rng.uniform(0.75, 0.92))
                ph = int(pitch * rng.uniform(0.75, 0.92))
                if x0 < 0 or y0 < 0 or x0 + pw >= w or y0 + ph >= h:
                    continue
                # irregular quad — corner displacement for leathery feel
                pts = np.array([
                    [x0 + int(rng.uniform(0, 2)), y0 + int(rng.uniform(0, 2))],
                    [x0 + pw - int(rng.uniform(0, 2)), y0 + int(rng.uniform(0, 2))],
                    [x0 + pw - int(rng.uniform(0, 2)), y0 + ph - int(rng.uniform(0, 2))],
                    [x0 + int(rng.uniform(0, 2)), y0 + ph - int(rng.uniform(0, 2))],
                ], dtype=np.int32)
                # Zone-based palette pick + TIGHT jitter
                cx_center = x0 + pw // 2
                cy_center = y0 + ph // 2
                zone_id = int(zone_map[min(cy_center, h - 1), min(cx_center, w - 1)])
                bM, bR, bC = zone_bases[zone_id]
                pM = float(np.clip(bM + rng.uniform(-0.04, 0.04), 0, 1))
                pR = float(np.clip(bR + rng.uniform(-0.04, 0.04), 0, 1))
                pC = float(np.clip(bC + rng.uniform(-0.05, 0.05), 0, 1))
                _cv2.fillPoly(M, [pts], pM, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts], pR, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], pC, lineType=_cv2.LINE_AA)
                # The dark fissure substrate already shows between plates because
                # plates are slightly smaller than pitch (pw/ph ~ 0.75-0.92).
                # Reinforce the leading-edge SHADOW (top edge darker)
                _cv2.line(M, (pts[0][0], pts[0][1]), (pts[1][0], pts[1][1]),
                          max(0.0, pM * 0.40), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (pts[0][0], pts[0][1]), (pts[1][0], pts[1][1]),
                          min(0.99, pR + 0.20), 1, lineType=_cv2.LINE_AA)

                # 20% of plates get a brighter DORSAL RIDGE stripe (top-edge highlight)
                if rng.random() < 0.20:
                    _cv2.line(M, (pts[3][0], pts[3][1]), (pts[2][0], pts[2][1]),
                              min(0.85, pM + 0.20), 1, lineType=_cv2.LINE_AA)

                # SUB-PLATE micro-pitting — 60% of plates get 1-2 pits
                if rng.random() < 0.60:
                    for _ in range(int(rng.integers(1, 3))):
                        dx = int(rng.uniform(x0 + 1, x0 + pw - 1))
                        dy = int(rng.uniform(y0 + 1, y0 + ph - 1))
                        drr = int(rng.uniform(1, 2))
                        _cv2.circle(M, (dx, dy), drr, max(0.0, pM * 0.50), -1, lineType=_cv2.LINE_AA)
                        _cv2.circle(R, (dx, dy), drr, min(0.99, pR + 0.10), -1, lineType=_cv2.LINE_AA)

    # leathery substrate micro-grain
    n_g = int(np.clip(h * w / 600.0, 400, 2500))
    gy = rng.integers(0, h, n_g); gx = rng.integers(0, w, n_g)
    M[gy, gx] = np.clip(M[gy, gx] + rng.uniform(-0.04, 0.04, n_g).astype(np.float32), 0, 1)
    R[gy, gx] = np.clip(R[gy, gx] + rng.uniform(-0.04, 0.04, n_g).astype(np.float32), 0, 1)
    CC[gy, gx] = np.clip(CC[gy, gx] + rng.uniform(-0.04, 0.04, n_g).astype(np.float32), 0, 1)

    return _finalize(M, R, CC, sm, "alligator_hide")
pattern_alligator_hide._spb_concept_complete = True


# ============================================================================
# 6) ENGINE_TURN_RADIAL_ARC  (Engine-Turn)
# ============================================================================

def pattern_engine_turn_radial_arc(shape, seed, sm, **kwargs):
    """engine_turn_radial_arc — R6-Loop tick-81 second-pass creative refinement.

    identity: R6 OWNER-REBUILD — *true* engine-turn / jewelling / damaskeening
    as seen on a Bugatti dashboard or Patek caseback. Owner complaint
    addressed: previous "wasn't engine turn" because it scattered random
    arcs. Real engine-turn is a STAGGERED GRID of OVERLAPPING POLISHED
    CIRCULAR DISCS, each disc carrying concentric ring tool-marks and a
    bright leading crescent. Layout: brick-staggered grid, disc pitch 14
    px (so adjacent discs overlap ~25%, producing the classic "fish-scale
    of circles" look). Each disc: 8-10 px radius, 3 concentric ring tool
    marks, bright crescent on UPPER-LEFT (uniform light source), tiny
    pivot dot in center. Per-disc TIGHT ±0.04 jitter from single
    machined-aluminum base.

    TICK-81 SECOND-PASS HERO: GUILLOCHE WAVE-NEST OVERLAY — a watchmaker's
    secondary engraving inscribed between the disc rows. Two phase-locked
    sine-rose curves (cos(a*t)*cos(t), cos(a*t)*sin(t)) trace overlapping
    wave-nests with VIOLET accent CC, the literal cousin of engine-turn
    from luxury dial faces. Anti-clone: no other pattern has a Lissajous-
    rose overlay on top of jewelling.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 770601)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    # Polished machined-aluminum base — slightly warmer
    M, R, CC = _make_substrate(shape, seed, 0.55, 0.36, 0.32, 0.06)

    # Cohesive light direction (upper-left, so all discs share the same lighting)
    LIGHT_A = -2.35  # ~135° below x axis = upper-left source

    if _CV2_OK:
        # === BRICK-STAGGERED GRID OF DISCS ===
        # Disc geometric params
        disc_r = int(np.clip(8 * s, 7, 11))      # 7-11 px radius
        pitch = int(np.clip(12 * s, 10, 14))     # 10-14 px between centers
        # Row offset = pitch/2 every other row for brick stagger
        rows = int(h / pitch) + 3
        cols = int(w / pitch) + 3
        for ry in range(rows):
            row_off = (ry % 2) * (pitch // 2)
            cy = ry * pitch - pitch // 2
            if cy < -disc_r or cy >= h + disc_r:
                continue
            for cxi in range(cols):
                cx = row_off + cxi * pitch - pitch // 2
                if cx < -disc_r or cx >= w + disc_r:
                    continue
                # tiny jitter so it's not robotic
                cx_j = cx + int(rng.integers(-1, 2))
                cy_j = cy + int(rng.integers(-1, 2))
                # disc base — TIGHT jitter from machined base
                dM = float(np.clip(0.62 + rng.uniform(-0.04, 0.04), 0, 1))
                dR = float(np.clip(0.34 + rng.uniform(-0.04, 0.04), 0, 1))
                dC = float(np.clip(0.30 + rng.uniform(-0.04, 0.04), 0, 1))
                # 1) filled disc body
                _cv2.circle(M, (cx_j, cy_j), disc_r, dM, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx_j, cy_j), disc_r, dR, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx_j, cy_j), disc_r, dC, -1, lineType=_cv2.LINE_AA)
                # 2) THREE concentric ring tool-marks (fly-cut spiral traces)
                # Slightly brighter rings, single-pixel
                for ring_r in (disc_r - 2, disc_r - 4, disc_r - 6):
                    if ring_r < 1:
                        continue
                    _cv2.circle(M, (cx_j, cy_j), ring_r, float(min(0.98, dM + 0.18)), 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (cx_j, cy_j), ring_r, float(min(0.99, dC + 0.12)), 1, lineType=_cv2.LINE_AA)
                # 3) Dark outer trough between discs — single-pixel border (creates the seam)
                _cv2.circle(M, (cx_j, cy_j), disc_r, float(max(0.0, dM * 0.35)), 1, lineType=_cv2.LINE_AA)
                # 4) UPPER-LEFT bright crescent (uniform light source) — 60° arc
                cres_start = float(np.degrees(LIGHT_A)) - 30
                cres_end = cres_start + 90
                _cv2.ellipse(M, (cx_j, cy_j), (disc_r, disc_r), 0, cres_start, cres_end, float(min(0.99, dM + 0.32)), 2, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx_j, cy_j), (disc_r, disc_r), 0, cres_start, cres_end, float(min(0.99, dC + 0.30)), 1, lineType=_cv2.LINE_AA)
                # 5) DARK lower-right shadow — 60° arc
                shad_start = cres_start + 180
                shad_end = shad_start + 90
                _cv2.ellipse(M, (cx_j, cy_j), (disc_r, disc_r), 0, shad_start, shad_end, float(max(0.0, dM * 0.45)), 2, lineType=_cv2.LINE_AA)
                # 6) Center pivot dot — single dark pinpoint
                if 0 <= cx_j < w and 0 <= cy_j < h:
                    M[cy_j, cx_j] = 0.22
                    CC[cy_j, cx_j] = 0.18

    # === FINE GRAIN — machined turning swarf micro-flecks ===
    n_sw = int(np.clip(h * w / 380.0, 380, 2400))
    sy = rng.integers(0, h, n_sw); sx = rng.integers(0, w, n_sw)
    M[sy, sx] = np.clip(M[sy, sx] + rng.uniform(-0.06, 0.10, n_sw).astype(np.float32), 0, 1)
    R[sy, sx] = np.clip(R[sy, sx] + rng.uniform(-0.05, 0.05, n_sw).astype(np.float32), 0, 1)
    CC[sy, sx] = np.clip(CC[sy, sx] + rng.uniform(-0.05, 0.10, n_sw).astype(np.float32), 0, 1)

    # === TICK-81 HERO: GUILLOCHE WAVE-NEST OVERLAY ===
    # Inscribed sine-rose curves between disc rows. Each rosette: ~7 short
    # arc segments per period, traced as 1-px violet-tinted CC ridges.
    if _CV2_OK:
        VIOLET_M, VIOLET_R, VIOLET_CC = 0.45, 0.15, 0.62
        JIT_V = 0.05
        n_rose = int(np.clip(46 * (min(h, w) / 256.0) ** 2, 22, 180))
        for _ in range(n_rose):
            rcx = float(rng.integers(10, max(11, w - 10)))
            rcy = float(rng.integers(10, max(11, h - 10)))
            radius = float(rng.uniform(7.0, 12.0))
            petals = int(rng.choice([3, 4, 5, 7]))
            phi0 = float(rng.uniform(0, 2 * np.pi))
            # trace rose curve: r(t) = radius * cos(petals * t)
            n_steps = 56
            ts = np.linspace(0, 2 * np.pi, n_steps, dtype=np.float32)
            rr = radius * np.cos(petals * ts)
            xs = rcx + rr * np.cos(ts + phi0)
            ys = rcy + rr * np.sin(ts + phi0)
            mv = float(np.clip(VIOLET_M + rng.uniform(-JIT_V, JIT_V) + 0.18, 0.05, 0.95))
            cv = float(np.clip(VIOLET_CC + rng.uniform(-JIT_V, JIT_V) + 0.22, 0.10, 0.99))
            rv = float(np.clip(VIOLET_R + rng.uniform(-JIT_V, JIT_V), 0.02, 0.40))
            for k in range(n_steps - 1):
                x1 = int(np.clip(xs[k], 0, w - 1))
                y1 = int(np.clip(ys[k], 0, h - 1))
                x2 = int(np.clip(xs[k + 1], 0, w - 1))
                y2 = int(np.clip(ys[k + 1], 0, h - 1))
                _cv2.line(M, (x1, y1), (x2, y2), mv, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (x1, y1), (x2, y2), cv, 1, lineType=_cv2.LINE_AA)
                if k % 7 == 0:
                    _cv2.line(R, (x1, y1), (x2, y2), rv, 1, lineType=_cv2.LINE_AA)

    return _finalize(M, R, CC, sm, "engine_turn_radial_arc")
pattern_engine_turn_radial_arc._spb_concept_complete = True


# ============================================================================
# 7) FORGED_CARBON_CHIP  (Carbon — UNIQUE)
# ============================================================================

def pattern_forged_carbon_chip(shape, seed, sm, **kwargs):
    """forged_carbon_chip — R6 rebuild (owner 3/REBUILD "too sparse / boring").

    identity: DENSE 3x packed forged-carbon flakes with crisp internal
    weave. Three chip-tier sizes (small 6-10 px, medium 10-16 px, hero
    16-22 px exposed-fiber show-piece) so the surface reads layered and
    not uniform. INTERNAL biaxial weave — every chip gets primary
    weave stripes AND a perpendicular cross-weave so the carbon-cloth
    twill reads even on tiny chips. CC RESIN MENISCUS micro-pools fill
    the gaps. Per-chip INDEPENDENT M/R/CC TIGHT-jittered from one
    forged-carbon palette (no rainbow). ANTI-SPARSE: 3x more chips
    than before, edge-clipped fills so coverage is total.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 770701)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    # Forged-carbon substrate — composite-DARK (all three channels low)
    M = np.full((h, w), 0.12, dtype=np.float32)
    R = np.full((h, w), 0.14, dtype=np.float32)
    CC = np.full((h, w), 0.10, dtype=np.float32)
    BASE_M, BASE_R, BASE_C = 0.50, 0.28, 0.26  # forged-carbon semi-metallic

    if _CV2_OK:
        chip_centers = []

        def _draw_chip(cx, cy, chip_w, chip_h, rot, jitter):
            cM = float(np.clip(BASE_M + rng.uniform(-jitter, jitter), 0, 1))
            cR = float(np.clip(BASE_R + rng.uniform(-jitter, jitter), 0, 1))
            cC = float(np.clip(BASE_C + rng.uniform(-jitter, jitter), 0, 1))
            rect = ((cx, cy), (chip_w * 2, chip_h * 2), float(np.degrees(rot)))
            box = _cv2.boxPoints(rect).astype(np.int32)
            _cv2.fillPoly(M, [box], cM, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [box], cR, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [box], cC, lineType=_cv2.LINE_AA)
            # WEAVE micro-stripes — primary axis
            n_stripes = int(rng.integers(3, 6))
            for k in range(n_stripes):
                off = (k - (n_stripes - 1) / 2.0) * chip_h * 0.30
                x0 = cx - int(np.cos(rot) * chip_w * 0.88) + int(np.cos(rot + np.pi / 2) * off)
                y0 = cy - int(np.sin(rot) * chip_w * 0.88) + int(np.sin(rot + np.pi / 2) * off)
                x1 = cx + int(np.cos(rot) * chip_w * 0.88) + int(np.cos(rot + np.pi / 2) * off)
                y1 = cy + int(np.sin(rot) * chip_w * 0.88) + int(np.sin(rot + np.pi / 2) * off)
                _cv2.line(M, (x0, y0), (x1, y1), float(min(0.97, cM + 0.16)), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (x0, y0), (x1, y1), float(max(0.02, cR - 0.10)), 1, lineType=_cv2.LINE_AA)
            # CROSS-WEAVE — perpendicular axis (biaxial twill)
            n_cross = max(2, n_stripes - 1)
            for k in range(n_cross):
                off = (k - (n_cross - 1) / 2.0) * chip_w * 0.30
                x0 = cx - int(np.cos(rot + np.pi / 2) * chip_h * 0.85) + int(np.cos(rot) * off)
                y0 = cy - int(np.sin(rot + np.pi / 2) * chip_h * 0.85) + int(np.sin(rot) * off)
                x1 = cx + int(np.cos(rot + np.pi / 2) * chip_h * 0.85) + int(np.cos(rot) * off)
                y1 = cy + int(np.sin(rot + np.pi / 2) * chip_h * 0.85) + int(np.sin(rot) * off)
                _cv2.line(M, (x0, y0), (x1, y1), float(min(0.95, cM + 0.10)), 1, lineType=_cv2.LINE_AA)
            # edge darkening
            _cv2.polylines(M, [box], True, float(cM * 0.40), 1, lineType=_cv2.LINE_AA)
            return cM, cR, cC

        # SMALL chips — densest layer
        n_small = int(np.clip(900 * s * s, 600, 1600))
        for _ in range(n_small):
            cx = int(rng.integers(2, w - 2))
            cy = int(rng.integers(2, h - 2))
            cw = max(3, int(rng.uniform(3.0, 5.0) * s))
            cw = min(cw, 5)
            ch = max(3, int(rng.uniform(3.0, 5.0) * s))
            ch = min(ch, 5)
            rot = float(rng.uniform(0, np.pi))
            _draw_chip(cx, cy, cw, ch, rot, 0.07)
            chip_centers.append((cx, cy, cw, rot))

        # MEDIUM chips — middle layer (overlays smalls)
        n_med = int(np.clip(420 * s * s, 280, 700))
        for _ in range(n_med):
            cx = int(rng.integers(4, w - 4))
            cy = int(rng.integers(4, h - 4))
            cw = max(5, int(rng.uniform(5.0, 8.0) * s))
            cw = min(cw, 8)
            ch = max(5, int(rng.uniform(5.0, 8.0) * s))
            ch = min(ch, 8)
            rot = float(rng.uniform(0, np.pi))
            _draw_chip(cx, cy, cw, ch, rot, 0.06)
            chip_centers.append((cx, cy, cw, rot))

        # HERO — 12-22 exposed-fiber chips, larger and with bright CC halo
        n_hero = int(rng.integers(12, 23))
        for _ in range(n_hero):
            cx = int(rng.integers(8, w - 8))
            cy = int(rng.integers(8, h - 8))
            cw = max(8, int(rng.uniform(8.0, 11.0) * s))
            cw = min(cw, 11)
            ch = max(8, int(rng.uniform(8.0, 11.0) * s))
            ch = min(ch, 11)
            rot = float(rng.uniform(0, np.pi))
            cM, cR, cC = _draw_chip(cx, cy, cw, ch, rot, 0.05)
            # bright CC edge halo
            rect2 = ((cx, cy), (cw * 2 + 2, cw * 2 + 2), float(np.degrees(rot)))
            box2 = _cv2.boxPoints(rect2).astype(np.int32)
            _cv2.polylines(CC, [box2], True, float(rng.uniform(0.78, 0.96)), 1, lineType=_cv2.LINE_AA)
            # ultra-crisp 5-6 cross weave
            for k in range(6):
                off = (k - 2.5) * cw * 0.22
                x0 = cx - int(np.cos(rot + np.pi / 2) * cw * 0.88) + int(np.cos(rot) * off)
                y0 = cy - int(np.sin(rot + np.pi / 2) * cw * 0.88) + int(np.sin(rot) * off)
                x1 = cx + int(np.cos(rot + np.pi / 2) * cw * 0.88) + int(np.cos(rot) * off)
                y1 = cy + int(np.sin(rot + np.pi / 2) * cw * 0.88) + int(np.sin(rot) * off)
                _cv2.line(M, (x0, y0), (x1, y1), 0.92, 1, lineType=_cv2.LINE_AA)

        # CLEAR-RESIN POOL meniscus — small CC bumps in gaps (avoid neon blue)
        n_pool = int(np.clip(180 * s * s, 80, 360))
        for _ in range(n_pool):
            px = int(rng.integers(2, w - 2))
            py = int(rng.integers(2, h - 2))
            pr = int(rng.uniform(1.5, 3.0) * s)
            pr = max(1, min(pr, 4))
            _cv2.circle(CC, (px, py), pr, float(rng.uniform(0.40, 0.58)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (px, py), pr, float(rng.uniform(0.20, 0.32)), -1, lineType=_cv2.LINE_AA)

    return _finalize(M, R, CC, sm, "forged_carbon_chip")
pattern_forged_carbon_chip._spb_concept_complete = True


# ============================================================================
# 8) SNAKE_SCALE_DIAMOND  (Predator — HIGHEST PRIORITY)
# ============================================================================

def pattern_snake_scale_diamond(shape, seed, sm, **kwargs):
    """snake_scale_diamond.

    identity: R6 CREATIVE SECOND-PASS — fine diamond-tessellated snake
    scales (4-8 px) with a NEW HERO motif: KINGSNAKE/CORAL-SNAKE
    BANDED CHROMATIC SHIFT — irregular horizontal bands of 8-18 px
    height re-tint full rows of scales (alternating red / black /
    yellow / pearl in the coral-snake order, with random band widths
    so silhouette stays unique, not just a tessellation clone). Each
    scale still picks INDEPENDENT M/R/CC from its band base ± tight
    0.05 jitter. Plus crown-highlight + dark-shadow + CC keel stripe.
    Plus 24-80 'king-scale' zones (slightly enlarged 1.25x). Plus
    micro chroma grain. Composite-dark substrate.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 770801)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    # Dark snake-belly substrate — composite-dark (low M, R, CC)
    M = np.full((h, w), 0.12, dtype=np.float32)
    R = np.full((h, w), 0.18, dtype=np.float32)
    CC = np.full((h, w), 0.10, dtype=np.float32)

    # NEW band-shift driver — kingsnake/coral bands (irregular horizontal stripes)
    band_palette = [
        (0.42, 0.22, 0.20),   # coral red
        (0.16, 0.30, 0.10),   # black band (very dark)
        (0.52, 0.18, 0.22),   # cream-yellow (warm bright)
        (0.30, 0.22, 0.45),   # iridescent pearl (cool)
        (0.28, 0.24, 0.18),   # python olive
    ]
    # build band_map[y] = palette index, with irregular widths
    band_map = np.zeros(h, dtype=np.int32)
    yi = 0
    while yi < h:
        bw = int(rng.integers(max(6, int(8 * s)), max(8, int(20 * s)) + 1))
        bi = int(rng.integers(0, len(band_palette)))
        band_map[yi:min(h, yi + bw)] = bi
        yi += bw
    # Compatibility — keep zone_map as the band_map projected so downstream
    # zone_map[cy,cx] lookups keep working without restructuring everything.
    zone_map = np.tile(band_map[:, None], (1, w))
    zone_bases = band_palette  # rename for downstream access

    if _CV2_OK:
        # FINE diamond pitch — 4-8 px wide, 3-5 px tall (TIGHT tessellation).
        # At 256² s≈1.0 so dw=3 means 6-px diamonds total. At 2048² dw=6 means 12-px.
        dw = max(3, int(rng.uniform(3.0, 4.5) * s))  # half-width 3-4 -> 6-8 px scales
        dh = max(2, int(rng.uniform(2.0, 3.0) * s))  # half-height 2-3 -> 4-6 px tall
        # hard cap (anti-panel-scale insurance)
        dw = min(dw, max(3, int(4.5 * s)))
        dh = min(dh, max(2, int(3.0 * s)))
        cols = w // max(1, (dw * 2)) + 2
        rows = h // max(1, dh) + 2
        kings = []
        for ry in range(rows):
            offset_x = (ry % 2) * dw
            for ci in range(cols):
                cx = offset_x + ci * dw * 2
                cy = ry * dh
                if not (2 < cx < w - 2 and 2 < cy < h - 2):
                    continue
                inner_w = max(2, int(dw * 0.88))
                inner_h = max(1, int(dh * 0.88))
                top = (cx, cy - inner_h)
                rgt = (cx + inner_w, cy)
                bot = (cx, cy + inner_h)
                lft = (cx - inner_w, cy)
                poly = np.array([top, rgt, bot, lft], dtype=np.int32)
                # Band-driven palette with TIGHT jitter (snake coral-banding HERO)
                zone_id = int(zone_map[min(cy, h - 1), min(cx, w - 1)])
                zone_id = zone_id % len(zone_bases)
                bM, bR, bC = zone_bases[zone_id]
                pM = float(np.clip(bM + rng.uniform(-0.05, 0.05), 0, 1))
                pR = float(np.clip(bR + rng.uniform(-0.05, 0.05), 0, 1))
                pC = float(np.clip(bC + rng.uniform(-0.05, 0.05), 0, 1))
                _cv2.fillPoly(M, [poly], pM, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [poly], pR, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [poly], pC, lineType=_cv2.LINE_AA)
                # crown highlight (top edge bright)
                crown = float(min(0.92, pM + 0.18))
                _cv2.line(M, lft, top, crown, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, top, rgt, crown, 1, lineType=_cv2.LINE_AA)
                # dark base shadow
                _cv2.line(M, bot, lft, float(pM * 0.45), 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, rgt, bot, float(pM * 0.45), 1, lineType=_cv2.LINE_AA)
                # CC keel hint — only on every other scale to avoid clutter
                if ((cx ^ cy) & 1) == 0:
                    _cv2.line(CC, top, bot, float(min(0.85, pC + 0.12)), 1, lineType=_cv2.LINE_AA)
                kings.append((cx, cy, dw, dh, pM, pR, pC, zone_id))

        # HERO — many more king-scales (30-50) but still SMALL (1.2-1.4x pitch)
        n_king = int(np.clip(40 * s, 24, 80))
        if kings:
            picks = rng.choice(len(kings), size=min(n_king, len(kings)), replace=False)
            for idx in picks:
                cx, cy, dwk, dhk, _, _, _, zone_id = kings[idx]
                kw = max(3, int(dwk * 1.25))
                kh = max(2, int(dhk * 1.25))
                top = (cx, cy - kh)
                rgt = (cx + kw, cy)
                bot = (cx, cy + kh)
                lft = (cx - kw, cy)
                poly = np.array([top, rgt, bot, lft], dtype=np.int32)
                bM, bR, bC = zone_bases[zone_id % len(zone_bases)]
                _cv2.fillPoly(M, [poly], float(min(0.94, bM + 0.18)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [poly], float(max(0.05, bR - 0.06)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [poly], float(min(0.92, bC + 0.18)), lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [poly], True, 0.10, 1, lineType=_cv2.LINE_AA)

    # micro chroma grain — fine pinpoint sparkle
    n_fl = int(np.clip(h * w / 600.0, 300, 2000))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(-0.04, 0.04, n_fl).astype(np.float32), 0, 1)
    R[fy, fx] = np.clip(R[fy, fx] + rng.uniform(-0.04, 0.04, n_fl).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.05, 0.05, n_fl).astype(np.float32), 0, 1)

    return _finalize(M, R, CC, sm, "snake_scale_diamond")
pattern_snake_scale_diamond._spb_concept_complete = True


# ============================================================================
# 9) JEWELED_GUILLOCHE  (Engine-Turn)
# ============================================================================

def pattern_jeweled_guilloche(shape, seed, sm, **kwargs):
    """jeweled_guilloche.

    identity: overlapping nested guilloché arcs at 4-7 phase centers.
    8-14 px ring widths. Micro-jewel sparks at arc intersections.
    Per-arc-set INDEPENDENT CC chroma. All arc widths 1 px; ring radii
    grow in steps of 4-7 px so the BAND between rings stays in doctrine.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 770901)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    # Polished metal base
    M, R, CC = _make_substrate(shape, seed, 0.70, 0.22, 0.50, 0.06)

    intersection_points = []
    if _CV2_OK:
        n_centers = int(rng.integers(4, 8))
        for _ in range(n_centers):
            cx = int(rng.integers(8, w - 8))
            cy = int(rng.integers(8, h - 8))
            base_C = float(rng.uniform(0.10, 0.95))  # set's chroma identity
            base_M = float(rng.uniform(0.55, 0.95))
            base_R = float(rng.uniform(0.08, 0.28))
            # nested ring stack
            step = int(rng.uniform(4.0, 7.0) * s)
            step = max(3, min(step, 7))
            max_r = int(rng.uniform(18.0, 30.0) * s)
            n_rings = int(np.clip(max_r // step, 4, 9))
            for ri in range(1, n_rings + 1):
                rr = ri * step
                # full-circle arc with slight angular gap
                ang_start = float(rng.uniform(0, 360))
                ang_end = ang_start + 360 - float(rng.uniform(5, 30))
                _cv2.ellipse(M, (cx, cy), (rr, rr), 0, ang_start, ang_end,
                             float(np.clip(base_M + rng.uniform(-0.10, 0.10), 0, 1)), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy), (rr, rr), 0, ang_start, ang_end,
                             float(np.clip(base_R + rng.uniform(-0.04, 0.04), 0, 1)), 1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy), (rr, rr), 0, ang_start, ang_end,
                             float(np.clip(base_C + rng.uniform(-0.08, 0.08), 0, 1)), 1, lineType=_cv2.LINE_AA)
                # record candidate intersection sample points along each ring
                for _samp in range(2):
                    sa = float(rng.uniform(0, 2 * np.pi))
                    ix = int(cx + np.cos(sa) * rr)
                    iy = int(cy + np.sin(sa) * rr)
                    if 0 <= ix < w and 0 <= iy < h:
                        intersection_points.append((ix, iy))

        # JEWEL SPARKS at intersections — fine 1-3 px bright dots
        n_jewels = min(len(intersection_points), int(np.clip(180 * s * s, 80, 280)))
        if intersection_points and n_jewels:
            picks = rng.choice(len(intersection_points), size=n_jewels, replace=False)
            for idx in picks:
                ix, iy = intersection_points[idx]
                jr = int(rng.uniform(1, 3))
                _cv2.circle(M, (ix, iy), jr, 0.98, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (ix, iy), jr, 0.06, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (ix, iy), jr, float(rng.uniform(0.75, 0.99)), -1, lineType=_cv2.LINE_AA)

    # polish grain
    n_fl = int(np.clip(h * w / 360.0, 400, 3500))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    M[fy, fx] = np.clip(M[fy, fx] + rng.uniform(-0.08, 0.10, n_fl).astype(np.float32), 0, 1)
    CC[fy, fx] = np.clip(CC[fy, fx] + rng.uniform(-0.10, 0.14, n_fl).astype(np.float32), 0, 1)

    return _finalize(M, R, CC, sm, "jeweled_guilloche")
pattern_jeweled_guilloche._spb_concept_complete = True


# ============================================================================
# 10) HOLO_PRISM_SHIFT  (Holographic)
# ============================================================================

def pattern_holo_prism_shift(shape, seed, sm, **kwargs):
    """holo_prism_shift.

    identity: small dense 4-10 px prism flecks scattered across canvas.
    Per-fleck INDEPENDENT CC chroma sweep (rainbow). High M, low R.
    HERO: 6-12 'facet cluster' zones 16-22 px where prisms pack tighter
    with SHARP ANGULAR boundaries giving the holo 'shift on viewing
    angle' feel. All features 4-22 px.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 771001)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    # Glossy mirror base
    M, R, CC = _make_substrate(shape, seed, 0.80, 0.18, 0.55, 0.06)

    if _CV2_OK:
        # main scatter of prism flecks
        n_flecks = int(np.clip(800 * s * s, 600, 1400))
        for _ in range(n_flecks):
            fx_ = int(rng.integers(2, w - 2))
            fy_ = int(rng.integers(2, h - 2))
            fr = int(rng.uniform(2.0, 5.0) * s)  # 2-5 → 4-10 px effective
            fr = max(2, min(fr, 5))
            # rainbow chroma sweep — full hue range via CC
            chroma = float(rng.uniform(0.05, 0.99))
            _cv2.circle(M, (fx_, fy_), fr, float(rng.uniform(0.82, 0.99)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (fx_, fy_), fr, float(rng.uniform(0.02, 0.18)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (fx_, fy_), fr, chroma, -1, lineType=_cv2.LINE_AA)

        # HERO — 6-12 angular facet clusters
        n_clusters = int(rng.integers(6, 13))
        for _ in range(n_clusters):
            ccx = int(rng.integers(12, w - 12))
            ccy = int(rng.integers(12, h - 12))
            cluster_r = int(rng.uniform(8.0, 11.0) * s)
            cluster_r = max(8, min(cluster_r, 11))
            # Build 3-5 angular facet polygons inside cluster_r
            n_facets = int(rng.integers(3, 6))
            for k in range(n_facets):
                a0 = (k / n_facets) * 2 * np.pi + float(rng.uniform(-0.2, 0.2))
                a1 = ((k + 1) / n_facets) * 2 * np.pi + float(rng.uniform(-0.2, 0.2))
                pts = np.array([
                    [ccx, ccy],
                    [ccx + int(np.cos(a0) * cluster_r), ccy + int(np.sin(a0) * cluster_r)],
                    [ccx + int(np.cos(a1) * cluster_r), ccy + int(np.sin(a1) * cluster_r)],
                ], dtype=np.int32)
                facet_C = float(rng.uniform(0.05, 0.99))
                _cv2.fillPoly(M, [pts], float(rng.uniform(0.88, 0.99)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts], float(rng.uniform(0.02, 0.12)), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], facet_C, lineType=_cv2.LINE_AA)
                # sharp angular edge
                _cv2.polylines(M, [pts], True, 0.20, 1, lineType=_cv2.LINE_AA)

    # micro chroma jitter per pixel (extra rainbow sparkle)
    n_fl = int(np.clip(h * w / 240.0, 800, 6000))
    fy = rng.integers(0, h, n_fl); fx = rng.integers(0, w, n_fl)
    CC[fy, fx] = rng.uniform(0.05, 0.99, n_fl).astype(np.float32)

    return _finalize(M, R, CC, sm, "holo_prism_shift")
pattern_holo_prism_shift._spb_concept_complete = True


# ============================================================================
# REGISTRY — both NEW canonical names + LEGACY aliases (racing-pivot 2026-05-26)
# ============================================================================

# Canonical name -> function
RACING_PIVOT_V1_PATTERNS = {
    "voodoo_sigil_field":      pattern_voodoo_sigil_field,
    "hex_blood_drip":          pattern_hex_blood_drip,
    "ember_field":             pattern_ember_field,
    "dragon_scale_macro":      pattern_dragon_scale_macro,
    "alligator_hide":          pattern_alligator_hide,
    "engine_turn_radial_arc":  pattern_engine_turn_radial_arc,
    "forged_carbon_chip":      pattern_forged_carbon_chip,
    "snake_scale_diamond":     pattern_snake_scale_diamond,
    "jeweled_guilloche":       pattern_jeweled_guilloche,
    "holo_prism_shift":        pattern_holo_prism_shift,
}


__all__ = [
    "RACING_PIVOT_V1_PATTERNS",
    "pattern_voodoo_sigil_field",
    "pattern_hex_blood_drip",
    "pattern_ember_field",
    "pattern_dragon_scale_macro",
    "pattern_alligator_hide",
    "pattern_engine_turn_radial_arc",
    "pattern_forged_carbon_chip",
    "pattern_snake_scale_diamond",
    "pattern_jeweled_guilloche",
    "pattern_holo_prism_shift",
]
