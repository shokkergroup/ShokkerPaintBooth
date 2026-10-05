"""Racing-pivot batch 2 — 10 PREDATOR + GOTHIC race-livery spec patterns.

Owner directive 2026-05-26 (afternoon): replace 10 abstract/brushed slots
with NEW predator skins and gothic/horror motifs. Per-pattern doctrine:
  - ONE coherent palette (no Lisa-Frank rainbow per-feature rolls)
  - Strict 8-32 px primitives (sub-features 1-12 px)
  - 3+ stacked feature types per pattern
  - Tight ±0.04-0.06 jitter per-feature off a SINGLE racing-coherent base
  - Render <200 ms at 256²

Slots being replaced (old_name -> new_name):
    abstract_futurist_motion    -> shark_denticle           PREDATOR
    abstract_ink_wash_gradient  -> raptor_feather           PREDATOR
    abstract_minimalist_stripe  -> jaguar_rosette           PREDATOR
    abstract_mondrian_grid      -> pangolin_armor           PREDATOR
    abstract_suprematism        -> viper_pit_hex            PREDATOR
    acid_etch                   -> skull_tessellation       GOTHIC
    bead_blast_uniform          -> hellfire_crackle         GOTHIC
    brushed_arc                 -> voodoo_bone_fetish       GOTHIC
    brushed_linear              -> demon_eye_field          GOTHIC
    brushed_linear_warm         -> crypt_brick              GOTHIC

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
# PERF (2026-06-13, racing_pivot_v2 lane). Look-preserving speedups only:
#   * Per-feature scalar color clamps `float(np.clip(v, 0, 1))` -> `_c01(v)`
#     (and `_clip(v, lo, hi)`): bit-identical, but avoids full numpy ufunc
#     dispatch on every scalar in the tight cv2 draw loops. Biggest win on the
#     loop-heavy patterns (crypt_brick draws ~17k blocks @2048 -> ~50k clips).
#   * tiger_stripe_field: rotated-coord trig field built from 1D broadcast
#     ramps instead of two full-res np.mgrid int64 grids (dtype-matched float64
#     -> bit-identical).
# NOTE: the full-res multi_scale_noise substrate/field calls were left EXACT.
# Generating them at bounded res + upscale was tried per-finish and FAILED the
# SSIM>=0.997 gate (the FBM substrate is visible between motifs / feeds hard
# thresholds): tiger fur 0.9946, viper belly 0.973, demon smoke 0.947,
# tiger fbm_mod 0.887. See per-call PERF NOTE comments at each kept-exact site.
# RNG draw order, feature counts, palettes and thresholds are unchanged.
# ----------------------------------------------------------------------------
def _c01(x):
    """Scalar clamp to [0, 1] -- bit-identical to ``float(np.clip(x, 0, 1))``
    for a Python/NumPy scalar (incl. NaN), but ~1000x cheaper (np.clip on a
    scalar pays full ufunc dispatch). Used only on per-feature scalar color
    values inside the tight draw loops; array clipping still uses np.clip.
    RNG-neutral.
    """
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else float(x))


def _clip(x, lo, hi):
    """Scalar clamp to [lo, hi] -- bit-identical to ``float(np.clip(x, lo, hi))``."""
    return lo if x < lo else (hi if x > hi else float(x))
from .racing_pivot_v1 import _finalize


# ============================================================================
# 1) SHARK_DENTICLE  (Predator — replaces abstract_futurist_motion)
# ============================================================================

def pattern_shark_denticle(shape, seed, sm, **kwargs):
    """shark_denticle.

    R6 CREATIVE SECOND-PASS 2026-05-26: shark hide + FLUID-DYNAMICS twist.
    Hundreds of small tooth-shaped denticles 8-14 px all oriented head-to-
    tail. NEW: each denticle TRAILS a tiny Karman-vortex micro-wake (1-2 px
    paired curl marks behind the tip, physics-inspired). Cool blue-grey
    deep-water substrate. HERO: 12-20 enlarged lead denticles 16-22 px
    with extra-bright keel + visible turbulent wake trail.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 880101)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)

    # Cool blue-grey deep-water shark substrate (composite-cool, low all)
    M = np.full((h, w), 0.10, dtype=np.float32)
    R = np.full((h, w), 0.14, dtype=np.float32)
    CC = np.full((h, w), 0.14, dtype=np.float32)  # slight CC lift = cool blue tone
    BASE_M, BASE_R, BASE_C = 0.48, 0.40, 0.36  # cool steel-grey shark hide

    if _CV2_OK:
        # Flow direction (denticles all point this way)
        flow_a = float(rng.uniform(0, 2 * np.pi))
        cos_f, sin_f = np.cos(flow_a), np.sin(flow_a)
        # perpendicular for width
        cos_p, sin_p = np.cos(flow_a + np.pi / 2), np.sin(flow_a + np.pi / 2)

        pitch_x = max(7, int(9 * s))
        pitch_y = max(6, int(7 * s))
        cols = w // pitch_x + 2
        rows = h // pitch_y + 2
        leads = []
        for ry in range(rows):
            row_offset = (ry % 2) * (pitch_x // 2)
            for cxi in range(cols):
                cx = row_offset + cxi * pitch_x + int(rng.integers(-1, 2))
                cy = ry * pitch_y + int(rng.integers(-1, 2))
                if not (4 < cx < w - 4 and 4 < cy < h - 4):
                    continue
                size = int(rng.uniform(4.5, 7.5) * s)  # half-len 4-7 → 8-14 px denticle
                size = max(4, min(size, 7))
                # Triangle pointing along flow_a, curved trailing
                tip = (cx + int(cos_f * size * 1.1), cy + int(sin_f * size * 1.1))
                base_l = (cx + int(cos_p * size * 0.7) - int(cos_f * size * 0.4),
                          cy + int(sin_p * size * 0.7) - int(sin_f * size * 0.4))
                base_r = (cx - int(cos_p * size * 0.7) - int(cos_f * size * 0.4),
                          cy - int(sin_p * size * 0.7) - int(sin_f * size * 0.4))
                tri = np.array([tip, base_l, base_r], dtype=np.int32)
                pM = _c01(BASE_M + rng.uniform(-0.05, 0.05))
                pR = _c01(BASE_R + rng.uniform(-0.05, 0.05))
                pC = _c01(BASE_C + rng.uniform(-0.05, 0.05))
                _cv2.fillPoly(M, [tri], pM, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [tri], pR, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [tri], pC, lineType=_cv2.LINE_AA)
                # Bright keel ridge from center to tip
                _cv2.line(M, (cx, cy), tip, min(0.95, pM + 0.25), 1, lineType=_cv2.LINE_AA)
                # Dark trailing edge
                _cv2.line(M, base_l, base_r, max(0.0, pM * 0.40), 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, base_l, base_r, min(0.99, pR + 0.20), 1, lineType=_cv2.LINE_AA)
                leads.append((cx, cy, size, tip, base_l, base_r))

        # HERO — 12-20 enlarged lead denticles
        n_hero = int(rng.integers(12, 21))
        if leads:
            picks = rng.choice(len(leads), size=min(n_hero, len(leads)), replace=False)
            for idx in picks:
                cx, cy, sz, tip, bl, br = leads[idx]
                hsize = int(sz * 1.5)
                hsize = max(7, min(hsize, 11))  # 14-22 px
                htip = (cx + int(cos_f * hsize * 1.15), cy + int(sin_f * hsize * 1.15))
                hbl = (cx + int(cos_p * hsize * 0.75) - int(cos_f * hsize * 0.40),
                       cy + int(sin_p * hsize * 0.75) - int(sin_f * hsize * 0.40))
                hbr = (cx - int(cos_p * hsize * 0.75) - int(cos_f * hsize * 0.40),
                       cy - int(sin_p * hsize * 0.75) - int(sin_f * hsize * 0.40))
                htri = np.array([htip, hbl, hbr], dtype=np.int32)
                _cv2.fillPoly(M, [htri], min(0.95, BASE_M + 0.20), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [htri], max(0.04, BASE_R - 0.10), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [htri], min(0.95, BASE_C + 0.18), lineType=_cv2.LINE_AA)
                _cv2.line(M, (cx, cy), htip, 0.97, 2, lineType=_cv2.LINE_AA)
                _cv2.polylines(M, [htri], True, 0.10, 1, lineType=_cv2.LINE_AA)

        # === NEW: Karman vortex micro-wakes behind random denticles ===
        # Physics-inspired alternating vortex pair trailing each (subset of)
        # denticle tip. Sub-feature 1-2 px paired curl marks.
        if leads:
            n_wake = int(np.clip(len(leads) * 0.35, 50, 220))
            wake_picks = rng.choice(len(leads), size=min(n_wake, len(leads)), replace=False)
            # perpendicular for vortex pair offset
            for idx in wake_picks:
                cx, cy, sz, tip, _bl, _br = leads[idx]
                # 3 stations along the wake trail behind the tip
                for k in range(1, 4):
                    # alternate side (k odd = left, k even = right) — von Karman
                    sign = 1 if (k % 2) == 1 else -1
                    off_along = k * 3
                    off_perp = sign * 2
                    wx = tip[0] + int(cos_f * off_along) + int(cos_p * off_perp)
                    wy = tip[1] + int(sin_f * off_along) + int(sin_p * off_perp)
                    if not (0 <= wx < w and 0 <= wy < h):
                        continue
                    # tiny curl arc (1-2 px)
                    intensity = 0.55 - k * 0.10
                    _cv2.circle(M, (wx, wy), 1, _clip(BASE_M + intensity, 0, 0.85), -1)
                    _cv2.circle(CC, (wx, wy), 1, _clip(BASE_C + intensity * 0.5, 0, 0.85), -1)

    # subtle micro-grain
    n_g = int(np.clip(h * w / 800.0, 200, 1500))
    gy = rng.integers(0, h, n_g); gx = rng.integers(0, w, n_g)
    M[gy, gx] = np.clip(M[gy, gx] + rng.uniform(-0.03, 0.03, n_g).astype(np.float32), 0, 1)
    R[gy, gx] = np.clip(R[gy, gx] + rng.uniform(-0.03, 0.03, n_g).astype(np.float32), 0, 1)
    return _finalize(M, R, CC, sm, "shark_denticle")
pattern_shark_denticle._spb_concept_complete = True


# ============================================================================
# 2) RAPTOR_FEATHER  (Predator — replaces abstract_ink_wash_gradient)
# ============================================================================

def pattern_raptor_feather(shape, seed, sm, **kwargs):
    """raptor_feather.

    identity: R6 tick 2026-05-26 — owner rated 3/REBUILD ("generic noise,
    features too small, chroma flat, doesn't match name, boring").
    REBUILD: BIGGER, READABLE flight-feather silhouettes 16-32 px each
    with actual VISIBLE feather anatomy — bright central shaft, slanted
    BARB CHEVRONS along both sides of the shaft (each barb a 2-4 px
    angled stroke), dark tip taper, light-catch quill bulge at base.
    HERO: 14-22 enlarged 30-44 px primary feathers with FULL barb fronds
    (8-14 visible barbs per side). Cohesive predator palette (raven-black
    main, warm-brown back, bronze breast). Zone-painted from low-freq
    field. Tight ±0.05 chroma jitter per feather. Each feather is
    UNMISTAKABLY a feather, not a triangle.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 880201)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)

    # Dark warm-brown undercoat — composite-dark
    M = np.full((h, w), 0.10, dtype=np.float32)
    R = np.full((h, w), 0.14, dtype=np.float32)
    CC = np.full((h, w), 0.08, dtype=np.float32)

    # 3-zone raptor palette (raven / warm-brown / bronze)
    zone_bases = [
        (0.42, 0.34, 0.20),   # raven-black main wing
        (0.58, 0.32, 0.26),   # warm-brown back
        (0.74, 0.30, 0.34),   # bronze breast accent
    ]
    zy = np.linspace(0, 3.0, h, dtype=np.float32)
    zx = np.linspace(0, 3.0, w, dtype=np.float32)
    XX, YY = np.meshgrid(zx, zy)
    z_phase = float(rng.uniform(0, 6.28))
    z_field = np.sin(XX * 1.4 + z_phase) + 0.5 * np.cos(YY * 1.7 + z_phase * 0.6)
    z_norm = (z_field - z_field.min()) / max(1e-6, float(np.ptp(z_field)))
    zone_map = np.clip((z_norm * 3).astype(np.int32), 0, 2)

    def _draw_feather(cx, cy, length, half_w, tilt, base_M, base_R, base_C, n_barbs, shaft_bright):
        """Draw a single anatomically-correct feather:
        - long teardrop body
        - bright central shaft (rachis)
        - barb chevrons spreading outward both sides of shaft
        """
        cos_t = np.cos(tilt - np.pi / 2)
        sin_t = np.sin(tilt - np.pi / 2)
        # perpendicular axis (for barb width)
        per_x = -sin_t
        per_y = cos_t
        tip = (cx + int(cos_t * length), cy + int(sin_t * length))
        # quill butt (slight bulge below cy)
        butt_off = int(length * 0.20)
        butt = (cx - int(cos_t * butt_off), cy - int(sin_t * butt_off))
        # body silhouette — diamond/teardrop (5 verts)
        mid_x = (cx + tip[0]) // 2
        mid_y = (cy + tip[1]) // 2
        body = np.array([
            tip,
            (mid_x + int(per_x * half_w), mid_y + int(per_y * half_w)),
            butt,
            (mid_x - int(per_x * half_w), mid_y - int(per_y * half_w)),
        ], dtype=np.int32)
        pM = _c01(base_M + rng.uniform(-0.05, 0.05))
        pR = _c01(base_R + rng.uniform(-0.05, 0.05))
        pC = _c01(base_C + rng.uniform(-0.05, 0.05))
        _cv2.fillPoly(M, [body], pM, lineType=_cv2.LINE_AA)
        _cv2.fillPoly(R, [body], pR, lineType=_cv2.LINE_AA)
        _cv2.fillPoly(CC, [body], pC, lineType=_cv2.LINE_AA)
        # bright shaft (rachis) from butt to tip
        _cv2.line(M, butt, tip, _clip(pM + shaft_bright, 0, 0.98), max(1, int(s)), lineType=_cv2.LINE_AA)
        _cv2.line(CC, butt, tip, _clip(pC + shaft_bright * 0.6, 0, 0.95), max(1, int(s)), lineType=_cv2.LINE_AA)
        # BARB CHEVRONS — each side gets n_barbs slanted strokes
        for i in range(n_barbs):
            t = (i + 0.5) / n_barbs  # 0..1 along shaft (butt→tip)
            anchor_x = butt[0] + (tip[0] - butt[0]) * t
            anchor_y = butt[1] + (tip[1] - butt[1]) * t
            # barb length shrinks toward tip
            barb_len = half_w * (1.0 - 0.4 * t) * 0.95
            # barb slants TOWARD the tip (chevron pattern, like real feather)
            barb_tilt = 0.35  # slope toward tip
            # left barb
            bx_l = anchor_x + per_x * barb_len + cos_t * barb_len * barb_tilt
            by_l = anchor_y + per_y * barb_len + sin_t * barb_len * barb_tilt
            _cv2.line(M, (int(anchor_x), int(anchor_y)), (int(bx_l), int(by_l)),
                      _clip(pM + 0.10, 0, 0.95), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (int(anchor_x), int(anchor_y)), (int(bx_l), int(by_l)),
                      _clip(pC + 0.08, 0, 0.90), 1, lineType=_cv2.LINE_AA)
            # right barb
            bx_r = anchor_x - per_x * barb_len + cos_t * barb_len * barb_tilt
            by_r = anchor_y - per_y * barb_len + sin_t * barb_len * barb_tilt
            _cv2.line(M, (int(anchor_x), int(anchor_y)), (int(bx_r), int(by_r)),
                      _clip(pM + 0.10, 0, 0.95), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (int(anchor_x), int(anchor_y)), (int(bx_r), int(by_r)),
                      _clip(pC + 0.08, 0, 0.90), 1, lineType=_cv2.LINE_AA)

    if _CV2_OK:
        # 1) Field of small-medium feathers — 16-24 px each
        pitch_x = max(7, int(10 * s))
        pitch_y = max(11, int(15 * s))
        cols = w // pitch_x + 2
        rows = h // pitch_y + 2
        flock_tilt = float(rng.uniform(-0.25, 0.25))  # cohesive flight direction
        for ry in range(rows):
            offset = (ry % 2) * (pitch_x // 2)
            for cxi in range(cols):
                cx = offset + cxi * pitch_x + int(rng.integers(-2, 3))
                cy = ry * pitch_y + int(rng.integers(-2, 3))
                if not (4 < cx < w - 4 and 7 < cy < h - 7):
                    continue
                length = int(rng.uniform(8.0, 12.0) * s)  # 16-24 px feather
                length = max(8, min(length, 14))
                half_w = max(2, int(length * 0.28))
                tilt = flock_tilt + float(rng.uniform(-0.12, 0.12))
                zone_id = int(zone_map[min(cy, h - 1), min(cx, w - 1)])
                bM, bR, bC = zone_bases[zone_id]
                _draw_feather(cx, cy, length, half_w, tilt, bM, bR, bC,
                              n_barbs=int(rng.integers(3, 6)),
                              shaft_bright=0.20)

        # 2) HERO — 14-22 enlarged 30-44 px primary feathers
        n_hero = int(rng.integers(14, 23))
        for _ in range(n_hero):
            hx = int(rng.integers(20, w - 20))
            hy = int(rng.integers(20, h - 20))
            hlength = int(rng.uniform(15, 22) * s)  # 30-44 px
            hlength = max(15, min(hlength, 26))
            hhw = max(4, int(hlength * 0.30))
            htilt = flock_tilt + float(rng.uniform(-0.18, 0.18))
            zone_id = int(zone_map[min(hy, h - 1), min(hx, w - 1)])
            bM, bR, bC = zone_bases[zone_id]
            # brighter zone variant for hero
            bM = min(0.88, bM + 0.10)
            bC = min(0.78, bC + 0.10)
            _draw_feather(hx, hy, hlength, hhw, htilt, bM, bR, bC,
                          n_barbs=int(rng.integers(8, 15)),
                          shaft_bright=0.28)

    return _finalize(M, R, CC, sm, "raptor_feather")
pattern_raptor_feather._spb_concept_complete = True


# ============================================================================
# 3) JAGUAR_ROSETTE  (Predator — replaces abstract_minimalist_stripe)
# ============================================================================

def pattern_jaguar_rosette(shape, seed, sm, **kwargs):
    """jaguar_rosette.

    identity: OWNER CORRECTIVE — owner said: generic noise, doesn't match
    name, sparse, boring. Now BIG and CLEARLY jaguar — every rosette is a
    sharp BLACK RING of 4-6 spots around a darker centre, drawn at 18-30
    px so they read instantly. Warm tan-gold base. Stacked tiers:
      (1) Dense field of 140-200 well-spaced rosettes (18-26 px each)
      (2) HERO 16-22 enlarged 28-40 px rosettes with bright tan rim halo
          AND a small inner second-ring (real jaguar coats double up)
      (3) NEW: scattered PREDATOR-EYE markings between rosettes — 12-18
          slit-pupil amber eyes (10-14 px each) to give the coat
          unmistakable jaguar/cat character
      (4) Fine tan-gold fur grain substrate (8-14 px scratches)
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 880301)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    # Warm tan-gold jaguar base
    M = np.full((h, w), 0.55, dtype=np.float32)
    R = np.full((h, w), 0.42, dtype=np.float32)
    CC = np.full((h, w), 0.28, dtype=np.float32)

    # Substrate variation for organic-fur quality
    fur = _normalize(multi_scale_noise(shape, [2.5, 5.5, 11.0], [0.5, 0.3, 0.2], int(seed) + 880305))
    M = np.clip(M + (fur - 0.5) * 0.10, 0, 1)
    R = np.clip(R + (fur - 0.5) * 0.08, 0, 1)

    if _CV2_OK:
        # FINE FUR GRAIN — short tan strokes 8-14 px for organic substrate
        n_fur = int(np.clip(900 * s * s, 600, 1800))
        for _ in range(n_fur):
            cx = float(rng.uniform(0, w)); cy = float(rng.uniform(0, h))
            fl = float(rng.uniform(8.0, 14.0) * s * 0.6)
            fa = float(rng.uniform(0, 2*np.pi))
            x0 = int(cx - np.cos(fa)*fl*0.5); y0 = int(cy - np.sin(fa)*fl*0.5)
            x1 = int(cx + np.cos(fa)*fl*0.5); y1 = int(cy + np.sin(fa)*fl*0.5)
            _cv2.line(M, (x0, y0), (x1, y1), float(rng.uniform(0.45, 0.66)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (x0, y0), (x1, y1), float(rng.uniform(0.36, 0.50)), 1, lineType=_cv2.LINE_AA)

        # Rosettes — dense Poisson-ish placement, MUCH BIGGER and CLEARER
        n_rosettes = int(np.clip(180 * s * s, 130, 260))
        placed = []
        attempts = 0
        max_attempts = n_rosettes * 10
        while len(placed) < n_rosettes and attempts < max_attempts:
            attempts += 1
            rx = int(rng.integers(12, w - 12))
            ry = int(rng.integers(12, h - 12))
            # 18-26 px rosette (was 12-20)
            radius = float(rng.uniform(9.0, 13.0) * s)
            min_d_sq = (radius * 1.5) ** 2
            ok = True
            for (px, py, pr) in placed[-60:]:
                if (rx - px) ** 2 + (ry - py) ** 2 < min_d_sq:
                    ok = False; break
            if not ok: continue
            # Slightly darker center spot — composite-dark (low M+R+CC)
            _cv2.circle(M, (rx, ry), max(2, int(radius * 0.22)), 0.10, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (rx, ry), max(2, int(radius * 0.22)), 0.14, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (rx, ry), max(2, int(radius * 0.22)), 0.06, -1, lineType=_cv2.LINE_AA)
            # 4-6 BLACK spots in a ring around center
            n_spots = int(rng.integers(4, 7))
            spot_r = max(2, int(radius * 0.26))
            phase = float(rng.uniform(0, 2 * np.pi))
            for k in range(n_spots):
                a = phase + k * (2 * np.pi / n_spots) + float(rng.uniform(-0.2, 0.2))
                sx = int(rx + np.cos(a) * radius * 0.70)
                sy = int(ry + np.sin(a) * radius * 0.70)
                _cv2.circle(M, (sx, sy), spot_r, 0.05, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (sx, sy), spot_r, 0.10, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (sx, sy), spot_r, 0.03, -1, lineType=_cv2.LINE_AA)
            placed.append((rx, ry, radius))

        # HERO — 16-22 enlarged 28-40 px rosettes with bright tan rim + double ring
        n_hero = int(rng.integers(16, 23))
        for _ in range(n_hero):
            rx = int(rng.integers(20, w - 20))
            ry = int(rng.integers(20, h - 20))
            hr = float(rng.uniform(14.0, 19.0) * s)
            # Bright tan rim — clear gold halo
            _cv2.circle(M, (rx, ry), int(hr) + 3, 0.82, 2, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (rx, ry), int(hr) + 3, 0.30, 2, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (rx, ry), int(hr) + 3, 0.55, 2, lineType=_cv2.LINE_AA)
            # Composite-dark center
            _cv2.circle(M, (rx, ry), max(3, int(hr * 0.22)), 0.06, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (rx, ry), max(3, int(hr * 0.22)), 0.10, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (rx, ry), max(3, int(hr * 0.22)), 0.04, -1, lineType=_cv2.LINE_AA)
            # 5-7 black ring spots
            n_spots = int(rng.integers(5, 8))
            spot_r = max(3, int(hr * 0.25))
            phase = float(rng.uniform(0, 2 * np.pi))
            for k in range(n_spots):
                a = phase + k * (2 * np.pi / n_spots) + float(rng.uniform(-0.15, 0.15))
                sx = int(rx + np.cos(a) * hr * 0.72)
                sy = int(ry + np.sin(a) * hr * 0.72)
                _cv2.circle(M, (sx, sy), spot_r, 0.04, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (sx, sy), spot_r, 0.10, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (sx, sy), spot_r, 0.03, -1, lineType=_cv2.LINE_AA)
            # SECONDARY inner ring (real jaguar coats double up) — 3-4 small spots
            n_in = int(rng.integers(3, 5))
            phase2 = float(rng.uniform(0, 2 * np.pi))
            sr_in = max(2, int(hr * 0.16))
            for k in range(n_in):
                a = phase2 + k * (2 * np.pi / n_in)
                sx = int(rx + np.cos(a) * hr * 0.40)
                sy = int(ry + np.sin(a) * hr * 0.40)
                _cv2.circle(M, (sx, sy), sr_in, 0.08, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (sx, sy), sr_in, 0.05, -1, lineType=_cv2.LINE_AA)

        # NEW HERO TIER — PREDATOR-EYE MARKINGS (12-18 amber slit-pupil eyes
        # scattered between rosettes for unmistakable jaguar identity)
        n_eye = int(rng.integers(12, 19))
        for _ in range(n_eye):
            ex = int(rng.integers(10, w - 10))
            ey = int(rng.integers(10, h - 10))
            er_long = float(rng.uniform(5.0, 7.5) * s)
            er_short = er_long * 0.50
            eye_rot = float(rng.uniform(-15, 15))
            # amber/gold eye iris (M bright + warm R)
            _cv2.ellipse(M, (ex, ey), (int(er_long), int(er_short)), eye_rot, 0, 360, 0.85, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (ex, ey), (int(er_long), int(er_short)), eye_rot, 0, 360, 0.32, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (ex, ey), (int(er_long), int(er_short)), eye_rot, 0, 360, 0.60, -1, lineType=_cv2.LINE_AA)
            # black slit pupil — narrow vertical (rotated)
            _cv2.ellipse(M, (ex, ey), (max(1, int(er_long * 0.55)), max(1, int(er_short * 0.18))), eye_rot, 0, 360, 0.05, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (ex, ey), (max(1, int(er_long * 0.55)), max(1, int(er_short * 0.18))), eye_rot, 0, 360, 0.10, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (ex, ey), (max(1, int(er_long * 0.55)), max(1, int(er_short * 0.18))), eye_rot, 0, 360, 0.04, -1, lineType=_cv2.LINE_AA)
            # bright catchlight pinpoint
            _cv2.circle(M, (ex - 1, ey - 1), 1, 0.96, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (ex - 1, ey - 1), 1, 0.96, -1, lineType=_cv2.LINE_AA)

    return _finalize(M, R, CC, sm, "jaguar_rosette")
pattern_jaguar_rosette._spb_concept_complete = True


# ============================================================================
# 4) PANGOLIN_ARMOR  (Predator — replaces abstract_mondrian_grid)
# ============================================================================

def pattern_pangolin_armor(shape, seed, sm, **kwargs):
    """pangolin_armor.

    identity: OWNER CORRECTIVE — owner said: too sparse, boring. Now DENSE
    overlapping pangolin armor scales packed like a real pinecone. Each
    spearhead-shaped plate 12-22 px with sharp keel ridge, KERATIN
    STRIATION lines (3 parallel grooves on each scale — the pangolin
    fingerprint signature), and a SHEDDING-EDGE BRIGHT TAN HIGHLIGHT
    along the trailing edge (real pangolin scales catch sun on the lip).
    Cohesive dark-brass + bronze palette.
    Stacked tiers:
      (1) Underlay scale layer (small 8-12 px back-row scales)
      (2) Main scale layer DENSE rows (12-18 px)
      (3) HERO 14-22 enlarged 22-30 px lead scales with extra-bright keel
          + sharp KERATIN STRIATION grooves + shedding bright tan rim
      (4) Composite-dark inter-scale seams (the under-armor void)
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 880401)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    # Dark armor undercoat — shows as seams between scales
    M = np.full((h, w), 0.10, dtype=np.float32)
    R = np.full((h, w), 0.14, dtype=np.float32)
    CC = np.full((h, w), 0.08, dtype=np.float32)
    BASE_M, BASE_R, BASE_C = 0.62, 0.36, 0.22  # bronze pangolin

    if _CV2_OK:
        # All scales oriented same direction (pinecone overlap)
        flow_a = float(rng.uniform(0, 2 * np.pi))
        cos_f, sin_f = np.cos(flow_a), np.sin(flow_a)
        cos_p, sin_p = np.cos(flow_a + np.pi / 2), np.sin(flow_a + np.pi / 2)

        # TIER 1 — UNDERLAY back-row small scales (denser, smaller)
        u_pitch_x = max(5, int(7 * s))
        u_pitch_y = max(4, int(5 * s))
        u_cols = w // u_pitch_x + 2
        u_rows = h // u_pitch_y + 2
        for ry in range(u_rows):
            offset = (ry % 2) * (u_pitch_x // 2)
            for cxi in range(u_cols):
                cx = offset + cxi * u_pitch_x + int(rng.integers(-1, 2))
                cy = ry * u_pitch_y + int(rng.integers(-1, 2))
                if not (4 < cx < w - 4 and 4 < cy < h - 4): continue
                sl = max(4, int(rng.uniform(4.0, 6.0) * s))
                sw = max(3, int(sl * 0.65))
                tip = (cx + int(cos_f * sl), cy + int(sin_f * sl))
                bl = (cx - int(cos_f * sl * 0.5) + int(cos_p * sw), cy - int(sin_f * sl * 0.5) + int(sin_p * sw))
                br = (cx - int(cos_f * sl * 0.5) - int(cos_p * sw), cy - int(sin_f * sl * 0.5) - int(sin_p * sw))
                bb = (cx - int(cos_f * sl * 0.95), cy - int(sin_f * sl * 0.95))
                pent = np.array([tip, bl, bb, br], dtype=np.int32)
                pM = _c01(BASE_M * 0.85 + rng.uniform(-0.04, 0.04))
                pR = _c01(BASE_R + rng.uniform(-0.04, 0.04))
                pC = _c01(BASE_C * 0.80 + rng.uniform(-0.04, 0.04))
                _cv2.fillPoly(M, [pent], pM, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pent], pR, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pent], pC, lineType=_cv2.LINE_AA)

        # TIER 2 — MAIN scale layer, denser packing
        pitch_x = max(7, int(9 * s))  # tightened from 11 → 9
        pitch_y = max(5, int(7 * s))  # tightened from 8 → 7
        cols = w // pitch_x + 2
        rows = h // pitch_y + 2
        leads = []
        for ry in range(rows):
            offset = (ry % 2) * (pitch_x // 2)
            for cxi in range(cols):
                cx = offset + cxi * pitch_x + int(rng.integers(-1, 2))
                cy = ry * pitch_y + int(rng.integers(-1, 2))
                if not (6 < cx < w - 6 and 6 < cy < h - 6):
                    continue
                size_long = max(6, int(rng.uniform(6.5, 9.5) * s))
                size_wide = max(4, int(size_long * float(rng.uniform(0.55, 0.72))))
                tip = (cx + int(cos_f * size_long), cy + int(sin_f * size_long))
                back_l = (cx - int(cos_f * size_long * 0.55) + int(cos_p * size_wide),
                          cy - int(sin_f * size_long * 0.55) + int(sin_p * size_wide))
                back_r = (cx - int(cos_f * size_long * 0.55) - int(cos_p * size_wide),
                          cy - int(sin_f * size_long * 0.55) - int(sin_p * size_wide))
                back_b = (cx - int(cos_f * size_long * 0.95),
                          cy - int(sin_f * size_long * 0.95))
                pent = np.array([tip, back_l, back_b, back_r], dtype=np.int32)
                pM = _c01(BASE_M + rng.uniform(-0.05, 0.05))
                pR = _c01(BASE_R + rng.uniform(-0.05, 0.05))
                pC = _c01(BASE_C + rng.uniform(-0.05, 0.05))
                _cv2.fillPoly(M, [pent], pM, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pent], pR, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pent], pC, lineType=_cv2.LINE_AA)
                # Sharp keel ridge from back-base to tip
                _cv2.line(M, back_b, tip, min(0.95, pM + 0.25), 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, back_b, tip, min(0.95, pC + 0.30), 1, lineType=_cv2.LINE_AA)
                # KERATIN STRIATION — 2 short side-grooves parallel to keel
                for off in (-1, 1):
                    sl_x = (back_b[0] + int(cos_p * off * size_wide * 0.45),
                            back_b[1] + int(sin_p * off * size_wide * 0.45))
                    sl_t = (tip[0] + int(cos_p * off * size_wide * 0.30),
                            tip[1] + int(sin_p * off * size_wide * 0.30))
                    _cv2.line(M, sl_x, sl_t, max(0.0, pM * 0.55), 1, lineType=_cv2.LINE_AA)
                # SHEDDING EDGE — bright tan rim along leading edges
                _cv2.line(M, tip, back_l, min(0.95, pM + 0.18), 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, tip, back_r, min(0.95, pM + 0.18), 1, lineType=_cv2.LINE_AA)
                # Dark trailing seam
                _cv2.line(M, back_l, back_r, max(0.0, pM * 0.30), 1, lineType=_cv2.LINE_AA)
                leads.append((cx, cy, size_long, size_wide))

        # TIER 3 — HERO 14-22 enlarged lead scales
        n_hero = int(rng.integers(14, 23))
        if leads:
            picks = rng.choice(len(leads), size=min(n_hero, len(leads)), replace=False)
            for idx in picks:
                cx, cy, sl, sw = leads[idx]
                hsl = max(10, int(sl * 1.6))
                hsw = max(6, int(sw * 1.4))
                tip = (cx + int(cos_f * hsl), cy + int(sin_f * hsl))
                back_l = (cx - int(cos_f * hsl * 0.55) + int(cos_p * hsw),
                          cy - int(sin_f * hsl * 0.55) + int(sin_p * hsw))
                back_r = (cx - int(cos_f * hsl * 0.55) - int(cos_p * hsw),
                          cy - int(sin_f * hsl * 0.55) - int(sin_p * hsw))
                back_b = (cx - int(cos_f * hsl * 0.95), cy - int(sin_f * hsl * 0.95))
                pent = np.array([tip, back_l, back_b, back_r], dtype=np.int32)
                _cv2.fillPoly(M, [pent], min(0.90, BASE_M + 0.20), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pent], max(0.06, BASE_R - 0.12), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pent], min(0.82, BASE_C + 0.22), lineType=_cv2.LINE_AA)
                # Extra-bright keel
                _cv2.line(M, back_b, tip, 0.97, 2, lineType=_cv2.LINE_AA)
                _cv2.line(CC, back_b, tip, 0.92, 2, lineType=_cv2.LINE_AA)
                # 3 keratin striations
                for off in (-1, 0, 1):
                    if off == 0: continue
                    sl_x = (back_b[0] + int(cos_p * off * hsw * 0.55),
                            back_b[1] + int(sin_p * off * hsw * 0.55))
                    sl_t = (tip[0] + int(cos_p * off * hsw * 0.30),
                            tip[1] + int(sin_p * off * hsw * 0.30))
                    _cv2.line(M, sl_x, sl_t, 0.30, 1, lineType=_cv2.LINE_AA)
                # bright tan shedding rim (full outline)
                _cv2.polylines(M, [pent], True, 0.88, 1, lineType=_cv2.LINE_AA)
                # composite-dark inner seam (under-shadow)
                _cv2.line(M, back_l, back_r, 0.08, 1, lineType=_cv2.LINE_AA)

    return _finalize(M, R, CC, sm, "pangolin_armor")
pattern_pangolin_armor._spb_concept_complete = True


# ============================================================================
# 5) VIPER_PIT_HEX  (Predator — replaces abstract_suprematism)
# ============================================================================

def pattern_viper_pit_hex(shape, seed, sm, **kwargs):
    """viper_pit_hex.

    R6 CREATIVE SECOND-PASS 2026-05-26: pit-viper belly-scale tessellation
    using SUPERELLIPSE/LAMÉ-CURVE diamonds (math motif) instead of plain
    polygon hexes. Three tiered scale sizes packed dense (anti-clone:
    each tier has distinct silhouette curvature). Cool teal-jade substrate
    (composite-cool). Hero: 6-10 enlarged 'fang scales' with lenticular
    venom-yellow gloss highlight crescent. Sub-features: 1-3 px belly-ridge
    keratin ridges per scale. All features 8-22 px, 200-360 primaries.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 880501)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)

    # Cool dark teal-jade viper substrate (composite-dark, low all-channel)
    M = np.full((h, w), 0.09, dtype=np.float32)
    R = np.full((h, w), 0.11, dtype=np.float32)
    CC = np.full((h, w), 0.07, dtype=np.float32)

    # subtle FBM belly variation (large-scale viper coloration zones)
    # PERF NOTE: kept full-res — downsampled FBM substrate shows between the
    # small scales (gate SSIM 0.973 FAIL). Must stay exact.
    if mn >= 96:
        belly = _normalize(multi_scale_noise(shape, [1.5, 3.2, 6.4], [0.55, 0.3, 0.15], int(seed) + 880511))
        M = np.clip(M + (belly - 0.5) * 0.06, 0, 1)
        R = np.clip(R + (belly - 0.5) * 0.04, 0, 1)

    BASE_M, BASE_R, BASE_C = 0.36, 0.46, 0.28  # cool teal-jade scale tone

    def _superellipse(cx, cy, a, b, n_exp, n_pts=24):
        """Lamé-curve / superellipse parametric (|x/a|^n + |y/b|^n = 1)."""
        t = np.linspace(0, 2 * np.pi, n_pts, endpoint=False)
        ct = np.cos(t); st = np.sin(t)
        x = cx + np.sign(ct) * (np.abs(ct) ** (2.0 / n_exp)) * a
        y = cy + np.sign(st) * (np.abs(st) ** (2.0 / n_exp)) * b
        return np.stack([x, y], axis=1).astype(np.int32)

    if _CV2_OK:
        # === Tier 1: tiny pinhead scales packed dense (8-12 px) ===
        pitch_x = max(7, int(8 * s))
        pitch_y = max(6, int(7 * s))
        cols = w // pitch_x + 2
        rows = h // pitch_y + 2
        kings = []
        for ry in range(rows):
            offset = (ry % 2) * (pitch_x // 2)
            for cxi in range(cols):
                cx = offset + cxi * pitch_x + int(rng.integers(-1, 2))
                cy = ry * pitch_y + int(rng.integers(-1, 2))
                if not (4 < cx < w - 4 and 4 < cy < h - 4):
                    continue
                a = max(3, int(rng.uniform(3.0, 5.0) * s))
                b = max(3, int(a * rng.uniform(1.1, 1.4)))
                a = min(a, 6); b = min(b, 8)
                # superellipse exponent varies — squarer for fang scales,
                # rounder for belly scales (anti-clone silhouette diversity)
                n_exp = float(rng.uniform(2.2, 3.4))
                pts = _superellipse(cx, cy, a, b, n_exp, 18)
                pM = _c01(BASE_M + rng.uniform(-0.05, 0.05))
                pR = _c01(BASE_R + rng.uniform(-0.05, 0.05))
                pC = _c01(BASE_C + rng.uniform(-0.05, 0.05))
                _cv2.fillPoly(M, [pts], pM, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts], pR, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], pC, lineType=_cv2.LINE_AA)
                # central keratin ridge (1-2 px bright vertical)
                _cv2.line(M, (cx, cy - b + 1), (cx, cy + b - 1),
                          min(0.78, pM + 0.18), 1, lineType=_cv2.LINE_AA)
                # dark scale-seam outline
                _cv2.polylines(M, [pts], True, max(0.0, pM * 0.40), 1, lineType=_cv2.LINE_AA)
                kings.append((cx, cy, a, b))

        # === Tier 2: medium between-tier diamond scales (10-16 px) ===
        # scattered between the grid using offset positions
        n_mid = int(np.clip(120 * s * s, 70, 220))
        for _ in range(n_mid):
            cx = int(rng.integers(6, w - 6))
            cy = int(rng.integers(6, h - 6))
            a = int(rng.uniform(5, 8) * s); a = max(4, min(a, 8))
            b = int(a * rng.uniform(1.15, 1.45)); b = max(5, min(b, 10))
            n_exp = float(rng.uniform(2.6, 3.8))  # squarer = more diamond-like
            pts = _superellipse(cx, cy, a, b, n_exp, 20)
            pM = _c01(BASE_M + 0.10 + rng.uniform(-0.04, 0.04))
            pR = _c01(BASE_R - 0.06 + rng.uniform(-0.04, 0.04))
            pC = _c01(BASE_C + 0.06 + rng.uniform(-0.04, 0.04))
            _cv2.fillPoly(M, [pts], pM, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [pts], pR, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [pts], pC, lineType=_cv2.LINE_AA)
            # bright top-arc lenticular gloss (half-ring)
            _cv2.ellipse(M, (cx, cy - b // 3), (a, max(1, b // 3)), 0, 180, 360,
                         min(0.82, pM + 0.20), 1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (cx, cy - b // 3), (a, max(1, b // 3)), 0, 180, 360,
                         min(0.82, pC + 0.20), 1, lineType=_cv2.LINE_AA)

        # === HERO Tier 3: 'fang scales' 16-22 px with venom-yellow lenticular gloss ===
        n_hero = int(rng.integers(6, 11))
        if kings:
            picks = rng.choice(len(kings), size=min(n_hero, len(kings)), replace=False)
            for idx in picks:
                cx, cy, a0, b0 = kings[idx]
                a = max(7, min(int(a0 * 2.1), 10))
                b = max(8, min(int(b0 * 1.9), 11))
                n_exp = float(rng.uniform(3.0, 4.2))
                pts = _superellipse(cx, cy, a, b, n_exp, 24)
                _cv2.fillPoly(M, [pts], min(0.66, BASE_M + 0.28), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts], max(0.18, BASE_R - 0.24), lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], min(0.68, BASE_C + 0.32), lineType=_cv2.LINE_AA)
                # venom-yellow lenticular gloss crescent (the "fang" highlight)
                gloss_h = max(2, b // 3)
                _cv2.ellipse(M, (cx, cy - b // 2), (a, gloss_h), 0, 200, 340,
                             0.92, max(1, int(s)), lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy - b // 2), (a, gloss_h), 0, 200, 340,
                             0.88, max(1, int(s)), lineType=_cv2.LINE_AA)
                # tiny twin venom-fang puncture marks (sub-feature, 1 px)
                pp = max(1, a // 3)
                _cv2.circle(M, (cx - pp, cy + b // 3), 1, 0.04, -1)
                _cv2.circle(M, (cx + pp, cy + b // 3), 1, 0.04, -1)
                _cv2.circle(R, (cx - pp, cy + b // 3), 1, 0.92, -1)
                _cv2.circle(R, (cx + pp, cy + b // 3), 1, 0.92, -1)
                _cv2.polylines(M, [pts], True, 0.08, 1, lineType=_cv2.LINE_AA)

    return _finalize(M, R, CC, sm, "viper_pit_hex")
pattern_viper_pit_hex._spb_concept_complete = True


# ============================================================================
# 6) SKULL_TESSELLATION  (Gothic — replaces acid_etch)
# ============================================================================

def pattern_skull_tessellation(shape, seed, sm, **kwargs):
    """skull_tessellation.

    identity: stylized small skull silhouettes tessellated tight across
    canvas. Each skull 10-18 px: oval cranium + jaw + 2 dark eye sockets.
    Matte-black gothic substrate. HERO: 6-12 larger 18-26 px skulls with
    bright cracked-bone CC highlight.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 880601)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    # Matte black gothic substrate
    # Matte gothic black substrate (composite-dark)
    M = np.full((h, w), 0.10, dtype=np.float32)
    R = np.full((h, w), 0.12, dtype=np.float32)
    CC = np.full((h, w), 0.08, dtype=np.float32)
    BONE_M, BONE_R, BONE_C = 0.78, 0.55, 0.45  # bone-white (mid R for warmth)

    if _CV2_OK:
        pitch_x = max(7, int(9 * s))
        pitch_y = max(8, int(11 * s))
        cols = w // pitch_x + 2
        rows = h // pitch_y + 2
        kings = []
        for ry in range(rows):
            offset = (ry % 2) * (pitch_x // 2)
            for cxi in range(cols):
                cx = offset + cxi * pitch_x + int(rng.integers(-1, 2))
                cy = ry * pitch_y + int(rng.integers(-1, 2))
                if not (6 < cx < w - 6 and 7 < cy < h - 7):
                    continue
                skull_r = int(rng.uniform(4.0, 6.5) * s)
                skull_r = max(4, min(skull_r, 6))
                pM = _c01(BONE_M + rng.uniform(-0.05, 0.05))
                pR = _c01(BONE_R + rng.uniform(-0.05, 0.05))
                pC = _c01(BONE_C + rng.uniform(-0.06, 0.06))
                # Cranium (slightly squashed circle)
                _cv2.ellipse(M, (cx, cy - 1), (skull_r, int(skull_r * 0.95)), 0, 0, 360,
                             pM, -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy - 1), (skull_r, int(skull_r * 0.95)), 0, 0, 360,
                             pR, -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy - 1), (skull_r, int(skull_r * 0.95)), 0, 0, 360,
                             pC, -1, lineType=_cv2.LINE_AA)
                # Jaw (smaller half-ellipse below)
                jaw_y = cy + int(skull_r * 0.6)
                jaw_w = int(skull_r * 0.7)
                jaw_h = int(skull_r * 0.4)
                if jaw_y + jaw_h < h - 1 and jaw_w > 0:
                    _cv2.ellipse(M, (cx, jaw_y), (jaw_w, jaw_h), 0, 0, 360, pM, -1, lineType=_cv2.LINE_AA)
                    _cv2.ellipse(R, (cx, jaw_y), (jaw_w, jaw_h), 0, 0, 360, pR, -1, lineType=_cv2.LINE_AA)
                # 2 dark eye sockets
                eye_off = max(1, int(skull_r * 0.4))
                eye_r = max(1, int(skull_r * 0.30))
                for sign in (-1, 1):
                    ex = cx + sign * eye_off
                    ey = cy - 1
                    _cv2.circle(M, (ex, ey), eye_r, 0.04, -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(R, (ex, ey), eye_r, 0.08, -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (ex, ey), eye_r, 0.03, -1, lineType=_cv2.LINE_AA)
                kings.append((cx, cy, skull_r))

        # HERO — 6-12 enlarged skulls with cracked-bone CC highlights
        n_hero = int(rng.integers(6, 13))
        if kings:
            picks = rng.choice(len(kings), size=min(n_hero, len(kings)), replace=False)
            for idx in picks:
                cx, cy, br = kings[idx]
                hr = int(br * 1.6)
                hr = max(7, min(hr, 11))
                _cv2.ellipse(M, (cx, cy - 1), (hr, int(hr * 0.95)), 0, 0, 360,
                             min(0.85, BONE_M + 0.20), -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (cx, cy - 1), (hr, int(hr * 0.95)), 0, 0, 360,
                             max(0.10, BONE_R - 0.12), -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (cx, cy - 1), (hr, int(hr * 0.95)), 0, 0, 360,
                             min(0.85, BONE_C + 0.22), -1, lineType=_cv2.LINE_AA)
                jy = cy + int(hr * 0.6)
                jw = int(hr * 0.7)
                jh = int(hr * 0.4)
                if jy + jh < h - 1 and jw > 0:
                    _cv2.ellipse(M, (cx, jy), (jw, jh), 0, 0, 360, min(0.85, BONE_M + 0.20), -1, lineType=_cv2.LINE_AA)
                eye_off = max(2, int(hr * 0.4))
                eye_r = max(2, int(hr * 0.32))
                for sign in (-1, 1):
                    ex = cx + sign * eye_off
                    _cv2.circle(M, (ex, cy - 1), eye_r, 0.02, -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(R, (ex, cy - 1), eye_r, 0.06, -1, lineType=_cv2.LINE_AA)
                    _cv2.circle(CC, (ex, cy - 1), eye_r, 0.02, -1, lineType=_cv2.LINE_AA)
                # cracked-bone hairlines
                for _ in range(int(rng.integers(2, 5))):
                    a1 = float(rng.uniform(0, 2 * np.pi))
                    a2 = a1 + float(rng.uniform(0.6, 1.8))
                    x0 = int(cx + np.cos(a1) * hr * 0.6)
                    y0 = int(cy - 1 + np.sin(a1) * hr * 0.6)
                    x1 = int(cx + np.cos(a2) * hr * 0.6)
                    y1 = int(cy - 1 + np.sin(a2) * hr * 0.6)
                    _cv2.line(M, (x0, y0), (x1, y1), 0.18, 1, lineType=_cv2.LINE_AA)

    return _finalize(M, R, CC, sm, "skull_tessellation")
pattern_skull_tessellation._spb_concept_complete = True


# ============================================================================
# 7) HELLFIRE_CRACKLE  (Gothic — replaces bead_blast_uniform)
# ============================================================================

def pattern_hellfire_crackle(shape, seed, sm, **kwargs):
    """hellfire_crackle.

    identity: R6 OWNER-REBUILD — *molten lava skin*. A charred basalt crust
    fractured by an INTRICATE FINE crack network glowing with multi-tier
    heat colors (cherry-red trough, orange flow, yellow-white peaks).
    Owner complaint addressed: was "sparse, too big, no spec coloring,
    doesn't show up". Fix: 280-440 short fissures + 320-560 micro
    capillaries + 50-90 bright junction nodes + dense ember pinpricks +
    char flake scatter. Crack thickness 1 px (sub-pixel AA), feature
    cluster reach 6-22 px. WIDE 7-tier heat palette so spec map sings.
    Every primitive sub-resolution to fine — composite reads as a real
    cooling magma surface, not bare lines on black.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 880701)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)

    # === SUBSTRATE: charred basalt with FBM heat-zone variation ===
    # base near-black (composite-dark) — but spatial heat zones so some
    # patches glow warmer than others (mimics cooling lava skin).
    M = np.full((h, w), 0.07, dtype=np.float32)
    R = np.full((h, w), 0.09, dtype=np.float32)
    CC = np.full((h, w), 0.05, dtype=np.float32)
    # heat-zone FBM (large soft regions of dim warmth)
    heat = _normalize(multi_scale_noise(shape, [1.5, 3.6, 7.4], [0.55, 0.3, 0.15], int(seed) + 880711))
    heat_mask = np.clip((heat - 0.45) * 2.2, 0.0, 1.0).astype(np.float32)
    # add gentle ember underglow ONLY where heat_mask is strong
    M += heat_mask * 0.08
    R += heat_mask * 0.06

    # 7-tier heat palette (cold->white-hot) used for per-feature jitter
    HEAT_M = (0.32, 0.45, 0.58, 0.70, 0.80, 0.90, 0.99)
    HEAT_R = (0.65, 0.55, 0.42, 0.30, 0.20, 0.12, 0.06)  # G channel = ROUGH; hot = mirror low
    HEAT_C = (0.07, 0.09, 0.12, 0.16, 0.22, 0.30, 0.42)

    if _CV2_OK:
        # === FRACTURE NETWORK — dense fine crack mesh ===
        # Build using Voronoi-like polygon edges: drop seed points, connect
        # nearest neighbors with crack lines. This produces a believable
        # cooling-skin web rather than random scatter.
        n_seeds = int(np.clip(180 * s * s, 110, 360))
        sx_pts = rng.uniform(0, w, n_seeds).astype(np.float32)
        sy_pts = rng.uniform(0, h, n_seeds).astype(np.float32)

        # Index spatially for nearest-neighbor (cheap N^2 with caps)
        junctions = []
        # For each seed, link 2-3 closest neighbors with a wobbly crack
        for i in range(n_seeds):
            ax_, ay_ = sx_pts[i], sy_pts[i]
            # candidate distances to all subsequent seeds (avoid dup pairs)
            dxs = sx_pts - ax_
            dys = sy_pts - ay_
            d2 = dxs * dxs + dys * dys
            d2[i] = 1e9
            # take 3 nearest
            knn = np.argpartition(d2, 3)[:3]
            for j in knn:
                if d2[j] > 28.0 * 28.0:  # cap to keep fissures FINE not panel-spanning
                    continue
                if rng.random() < 0.55:  # not every pair → irregular web
                    continue
                # heat tier (random per crack)
                t_idx = int(rng.integers(0, 7))
                glow_M = _c01(HEAT_M[t_idx] + rng.uniform(-0.05, 0.05))
                glow_R_v = _c01(HEAT_R[t_idx] + rng.uniform(-0.05, 0.05))
                glow_CC = _c01(HEAT_C[t_idx] + rng.uniform(-0.04, 0.04))
                # 3-segment wobbly walk
                bx, by = float(sx_pts[j]), float(sy_pts[j])
                pts = [(int(ax_), int(ay_))]
                for t in (0.33, 0.66):
                    px = ax_ + (bx - ax_) * t + float(rng.uniform(-1.5, 1.5))
                    py = ay_ + (by - ay_) * t + float(rng.uniform(-1.5, 1.5))
                    pts.append((int(_clip(px, 0, w - 1)), int(_clip(py, 0, h - 1))))
                pts.append((int(bx), int(by)))
                for k in range(len(pts) - 1):
                    _cv2.line(M, pts[k], pts[k + 1], glow_M, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(R, pts[k], pts[k + 1], glow_R_v, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(CC, pts[k], pts[k + 1], glow_CC, 1, lineType=_cv2.LINE_AA)
            junctions.append((int(ax_), int(ay_)))

        # === MICRO CAPILLARIES — short 3-8 px hairline fissures filling gaps ===
        n_cap = int(np.clip(420 * s * s, 280, 720))
        for _ in range(n_cap):
            cx = int(rng.integers(0, w))
            cy = int(rng.integers(0, h))
            a = float(rng.uniform(0, 2 * np.pi))
            L = float(rng.uniform(3, 8))
            nx = int(_clip(cx + np.cos(a) * L, 0, w - 1))
            ny = int(_clip(cy + np.sin(a) * L, 0, h - 1))
            t_idx = int(rng.integers(0, 6))  # bias slightly cooler
            _cv2.line(M, (cx, cy), (nx, ny), float(HEAT_M[t_idx] + rng.uniform(-0.04, 0.04)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(R, (cx, cy), (nx, ny), float(HEAT_R[t_idx] + rng.uniform(-0.04, 0.04)), 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, (cx, cy), (nx, ny), float(HEAT_C[t_idx] + rng.uniform(-0.03, 0.03)), 1, lineType=_cv2.LINE_AA)

        # === JUNCTION NODES — 50-90 bright white-hot vent points ===
        n_hero = int(np.clip(70 * s * s, 50, 110))
        if junctions:
            picks = rng.choice(len(junctions), size=min(n_hero, len(junctions)), replace=False)
            for idx in picks:
                jx, jy = junctions[idx]
                # outer warm halo 4-6 px
                r_halo = int(rng.uniform(3, 5))
                _cv2.circle(M, (jx, jy), r_halo, _c01(0.78 + rng.uniform(-0.05, 0.05)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (jx, jy), r_halo, _c01(0.40 + rng.uniform(-0.05, 0.05)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (jx, jy), r_halo, _c01(0.18 + rng.uniform(-0.04, 0.04)), -1, lineType=_cv2.LINE_AA)
                # bright orange ring 2-3 px
                _cv2.circle(M, (jx, jy), max(1, r_halo - 2), _c01(0.93 + rng.uniform(-0.04, 0.03)), -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (jx, jy), max(1, r_halo - 2), _c01(0.22 + rng.uniform(-0.05, 0.05)), -1, lineType=_cv2.LINE_AA)
                # pure white-hot 1 px core
                M[max(0, jy - 1):min(h, jy + 2), max(0, jx - 1):min(w, jx + 2)] = 0.99
                R[max(0, jy - 1):min(h, jy + 2), max(0, jx - 1):min(w, jx + 2)] = 0.08
                CC[max(0, jy - 1):min(h, jy + 2), max(0, jx - 1):min(w, jx + 2)] = 0.38

    # === EMBER PINPRICKS — dense bright dots distributed weighted by heat_mask ===
    n_em = int(np.clip(h * w / 220.0, 380, 2200))
    ey = rng.integers(0, h, n_em); ex = rng.integers(0, w, n_em)
    # accept-reject weighted by heat_mask so embers cluster in hot zones
    accept = rng.random(n_em).astype(np.float32) < (0.35 + 0.65 * heat_mask[ey, ex])
    ey = ey[accept]; ex = ex[accept]
    t_choice = rng.integers(3, 7, ey.shape[0])
    ember_M = np.array([HEAT_M[i] for i in t_choice], dtype=np.float32) + rng.uniform(-0.04, 0.04, ey.shape[0]).astype(np.float32)
    ember_R = np.array([HEAT_R[i] for i in t_choice], dtype=np.float32) + rng.uniform(-0.04, 0.04, ey.shape[0]).astype(np.float32)
    ember_C = np.array([HEAT_C[i] for i in t_choice], dtype=np.float32) + rng.uniform(-0.04, 0.04, ey.shape[0]).astype(np.float32)
    M[ey, ex] = np.maximum(M[ey, ex], np.clip(ember_M, 0, 1))
    R[ey, ex] = np.minimum(R[ey, ex], np.clip(ember_R, 0, 1))
    CC[ey, ex] = np.clip(ember_C, 0, 1)

    # === CHAR FLAKE GRAIN — fine dark scatter for crust texture ===
    n_g = int(np.clip(h * w / 320.0, 400, 2200))
    gy = rng.integers(0, h, n_g); gx = rng.integers(0, w, n_g)
    M[gy, gx] = np.clip(M[gy, gx] - rng.uniform(0.0, 0.06, n_g).astype(np.float32), 0, 1)
    R[gy, gx] = np.clip(R[gy, gx] + rng.uniform(-0.04, 0.04, n_g).astype(np.float32), 0, 1)

    return _finalize(M, R, CC, sm, "hellfire_crackle")
pattern_hellfire_crackle._spb_concept_complete = True


# ============================================================================
# 8) VOODOO_BONE_FETISH  (Gothic — replaces brushed_arc)
# ============================================================================

def pattern_voodoo_bone_fetish(shape, seed, sm, **kwargs):
    """voodoo_bone_fetish.

    identity: scattered bone-fragment relics — femurs, vertebrae,
    tooth-pieces, knuckle bones at 10-20 px on weathered dark-wood
    substrate. Each fragment: bright bone-white with darker shadow side.
    HERO: 6-12 larger 22-30 px bones with binding-cord wrap details.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 880801)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    # Weathered dark-wood altar substrate
    # Dark altar-wood substrate (composite-dark with warm tint)
    M = np.full((h, w), 0.22, dtype=np.float32)
    R = np.full((h, w), 0.18, dtype=np.float32)
    CC = np.full((h, w), 0.10, dtype=np.float32)
    # Wood-grain variation
    wood = _normalize(multi_scale_noise(shape, [1.4, 3.0, 6.5], [0.5, 0.3, 0.2], int(seed) + 880805))
    M = np.clip(M + (wood - 0.5) * 0.10, 0, 1)
    R = np.clip(R + (wood - 0.5) * 0.08, 0, 1)

    BONE_M, BONE_R, BONE_C = 0.65, 0.30, 0.50  # bone-white-warm

    if _CV2_OK:
        n_bones = int(np.clip(120 * s * s, 80, 200))
        kings = []
        for _ in range(n_bones):
            bx = int(rng.integers(6, w - 6))
            by = int(rng.integers(6, h - 6))
            kind = int(rng.integers(0, 4))
            angle = float(rng.uniform(0, np.pi))
            pM = _c01(BONE_M + rng.uniform(-0.05, 0.05))
            pR = _c01(BONE_R + rng.uniform(-0.05, 0.05))
            pC = _c01(BONE_C + rng.uniform(-0.06, 0.06))
            if kind == 0:  # femur (long bone with knob ends)
                length = int(rng.uniform(5, 9) * s)
                length = max(5, min(length, 9))
                cos_a, sin_a = np.cos(angle), np.sin(angle)
                p0 = (int(bx - cos_a * length), int(by - sin_a * length))
                p1 = (int(bx + cos_a * length), int(by + sin_a * length))
                _cv2.line(M, p0, p1, pM, 2, lineType=_cv2.LINE_AA)
                _cv2.line(R, p0, p1, pR, 2, lineType=_cv2.LINE_AA)
                _cv2.line(CC, p0, p1, pC, 2, lineType=_cv2.LINE_AA)
                _cv2.circle(M, p0, 2, pM, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, p1, 2, pM, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, p0, 2, pR, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, p1, 2, pR, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, p0, 2, pC, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, p1, 2, pC, -1, lineType=_cv2.LINE_AA)
            elif kind == 1:  # vertebra (small donut)
                vr = int(rng.uniform(3, 5) * s)
                vr = max(3, min(vr, 5))
                _cv2.circle(M, (bx, by), vr, pM, 2, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (bx, by), vr, pR, 2, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (bx, by), vr, pC, 2, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (bx, by), max(1, vr // 2), 0.06, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (bx, by), max(1, vr // 2), 0.10, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (bx, by), max(1, vr // 2), 0.04, -1, lineType=_cv2.LINE_AA)
            elif kind == 2:  # tooth (triangle)
                tlen = int(rng.uniform(4, 7) * s)
                tlen = max(4, min(tlen, 7))
                cos_a, sin_a = np.cos(angle), np.sin(angle)
                tip = (int(bx + cos_a * tlen), int(by + sin_a * tlen))
                bL = (int(bx - cos_a * tlen * 0.3 + sin_a * tlen * 0.45),
                      int(by - sin_a * tlen * 0.3 - cos_a * tlen * 0.45))
                bR = (int(bx - cos_a * tlen * 0.3 - sin_a * tlen * 0.45),
                      int(by - sin_a * tlen * 0.3 + cos_a * tlen * 0.45))
                tri = np.array([tip, bL, bR], dtype=np.int32)
                _cv2.fillPoly(M, [tri], pM, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [tri], pR, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [tri], pC, lineType=_cv2.LINE_AA)
            else:  # knuckle bone (small irregular blob)
                kr = int(rng.uniform(3, 5) * s)
                kr = max(3, min(kr, 5))
                _cv2.ellipse(M, (bx, by), (kr, int(kr * 0.7)), float(np.degrees(angle)),
                             0, 360, pM, -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (bx, by), (kr, int(kr * 0.7)), float(np.degrees(angle)),
                             0, 360, pR, -1, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (bx, by), (kr, int(kr * 0.7)), float(np.degrees(angle)),
                             0, 360, pC, -1, lineType=_cv2.LINE_AA)
            kings.append((bx, by, kind, angle))

        # HERO — 6-12 large femurs with binding-cord wraps
        n_hero = int(rng.integers(6, 13))
        for _ in range(n_hero):
            bx = int(rng.integers(14, w - 14))
            by = int(rng.integers(14, h - 14))
            length = int(rng.uniform(10, 14) * s)
            length = max(10, min(length, 14))
            angle = float(rng.uniform(0, np.pi))
            cos_a, sin_a = np.cos(angle), np.sin(angle)
            p0 = (int(bx - cos_a * length), int(by - sin_a * length))
            p1 = (int(bx + cos_a * length), int(by + sin_a * length))
            _cv2.line(M, p0, p1, min(0.92, BONE_M + 0.18), 3, lineType=_cv2.LINE_AA)
            _cv2.line(R, p0, p1, max(0.10, BONE_R - 0.10), 3, lineType=_cv2.LINE_AA)
            _cv2.line(CC, p0, p1, min(0.85, BONE_C + 0.18), 3, lineType=_cv2.LINE_AA)
            _cv2.circle(M, p0, 3, min(0.92, BONE_M + 0.18), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(M, p1, 3, min(0.92, BONE_M + 0.18), -1, lineType=_cv2.LINE_AA)
            # Binding cord — 3-4 perpendicular ticks along the shaft
            for k in range(int(rng.integers(3, 5))):
                t = (k + 1) / 5.0
                mx = int(p0[0] + (p1[0] - p0[0]) * t)
                my = int(p0[1] + (p1[1] - p0[1]) * t)
                # perpendicular short tick
                cos_p, sin_p = np.cos(angle + np.pi / 2), np.sin(angle + np.pi / 2)
                cp0 = (int(mx + cos_p * 3), int(my + sin_p * 3))
                cp1 = (int(mx - cos_p * 3), int(my - sin_p * 3))
                _cv2.line(M, cp0, cp1, 0.20, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, cp0, cp1, 0.20, 1, lineType=_cv2.LINE_AA)
                _cv2.line(CC, cp0, cp1, 0.10, 1, lineType=_cv2.LINE_AA)

    return _finalize(M, R, CC, sm, "voodoo_bone_fetish")
pattern_voodoo_bone_fetish._spb_concept_complete = True


# ============================================================================
# 9) DEMON_EYE_FIELD  (Gothic — replaces brushed_linear)
# ============================================================================

def pattern_demon_eye_field(shape, seed, sm, **kwargs):
    """demon_eye_field.

    identity: 40-80 demon eyes scattered across a smoky dark substrate.
    Each eye 10-18 px tall x 6-12 px wide: bright outer sclera ring +
    dark center with vertical-slit pupil. HERO: 8-14 larger 18-24 px
    eyes with glowing iris ring and SHARP slit pupil.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 880901)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    # Smoky dark-red substrate (hellish atmosphere)
    # Smoky dark-red substrate (composite reads as deep maroon)
    M = np.full((h, w), 0.32, dtype=np.float32)
    R = np.full((h, w), 0.12, dtype=np.float32)
    CC = np.full((h, w), 0.10, dtype=np.float32)
    # PERF NOTE: kept full-res — visible smoky substrate between eyes
    # (gate SSIM 0.947 FAIL on downsample). Must stay exact.
    smoke = _normalize(multi_scale_noise(shape, [2.5, 5.5, 11.0], [0.5, 0.3, 0.2], int(seed) + 880905))
    M = np.clip(M + (smoke - 0.5) * 0.12, 0, 1)
    R = np.clip(R + (smoke - 0.5) * 0.08, 0, 1)

    if _CV2_OK:
        # R6 OWNER REBUILD 2026-05-26: owner said "needs about 50x more eyes"
        # → 5-10x density boost. 380 base → 250-600 eyes per canvas.
        n_eyes = int(np.clip(380 * s * s, 250, 600))
        kings = []
        placed = []
        attempts = 0
        while len(placed) < n_eyes and attempts < n_eyes * 6:
            attempts += 1
            ex = int(rng.integers(8, w - 8))
            ey = int(rng.integers(8, h - 8))
            ew = int(rng.uniform(3.5, 6.0) * s)  # half-width 3-6 → 6-12 px width
            eh = int(rng.uniform(5.0, 9.0) * s)  # half-height 5-9 → 10-18 px height
            ew = max(3, min(ew, 6))
            eh = max(5, min(eh, 9))
            angle = float(rng.uniform(-0.25, 0.25))  # mostly vertical
            # TIGHTER packing — was 2.2, now 1.35 so eyes can pack closer
            min_d_sq = (max(ew, eh) * 1.35) ** 2
            ok = True
            for (px, py, _, _) in placed[-30:]:
                if (ex - px) ** 2 + (ey - py) ** 2 < min_d_sq:
                    ok = False
                    break
            if not ok:
                continue
            # Sclera (outer eye — bright bone-white)
            _cv2.ellipse(M, (ex, ey), (ew, eh), float(np.degrees(angle)), 0, 360, 0.75, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (ex, ey), (ew, eh), float(np.degrees(angle)), 0, 360, 0.28, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (ex, ey), (ew, eh), float(np.degrees(angle)), 0, 360, 0.55, -1, lineType=_cv2.LINE_AA)
            # Iris ring (warm yellow-orange)
            iris_w = max(2, int(ew * 0.75))
            iris_h = max(3, int(eh * 0.75))
            _cv2.ellipse(M, (ex, ey), (iris_w, iris_h), float(np.degrees(angle)), 0, 360, 0.92, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (ex, ey), (iris_w, iris_h), float(np.degrees(angle)), 0, 360, 0.55, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (ex, ey), (iris_w, iris_h), float(np.degrees(angle)), 0, 360, 0.10, -1, lineType=_cv2.LINE_AA)
            # Vertical slit pupil (very dark, narrow)
            pupil_w = max(1, int(ew * 0.18))
            pupil_h = max(2, int(eh * 0.78))
            _cv2.ellipse(M, (ex, ey), (pupil_w, pupil_h), float(np.degrees(angle)), 0, 360, 0.03, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (ex, ey), (pupil_w, pupil_h), float(np.degrees(angle)), 0, 360, 0.06, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (ex, ey), (pupil_w, pupil_h), float(np.degrees(angle)), 0, 360, 0.02, -1, lineType=_cv2.LINE_AA)
            placed.append((ex, ey, ew, eh))

        # HERO — 8-14 enlarged demon eyes
        n_hero = int(rng.integers(8, 15))
        for _ in range(n_hero):
            ex = int(rng.integers(14, w - 14))
            ey = int(rng.integers(14, h - 14))
            ew = int(rng.uniform(6.0, 9.0) * s)
            eh = int(rng.uniform(9.0, 12.0) * s)
            ew = max(6, min(ew, 9))
            eh = max(9, min(eh, 12))
            angle = float(rng.uniform(-0.18, 0.18))
            # Outer sclera
            _cv2.ellipse(M, (ex, ey), (ew, eh), float(np.degrees(angle)), 0, 360, 0.82, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (ex, ey), (ew, eh), float(np.degrees(angle)), 0, 360, 0.20, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (ex, ey), (ew, eh), float(np.degrees(angle)), 0, 360, 0.62, -1, lineType=_cv2.LINE_AA)
            # Glowing iris
            iris_w = max(3, int(ew * 0.75))
            iris_h = max(4, int(eh * 0.75))
            _cv2.ellipse(M, (ex, ey), (iris_w, iris_h), float(np.degrees(angle)), 0, 360, 0.97, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (ex, ey), (iris_w, iris_h), float(np.degrees(angle)), 0, 360, 0.62, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (ex, ey), (iris_w, iris_h), float(np.degrees(angle)), 0, 360, 0.08, -1, lineType=_cv2.LINE_AA)
            # Sharp slit pupil
            pupil_w = max(1, int(ew * 0.16))
            pupil_h = max(3, int(eh * 0.82))
            _cv2.ellipse(M, (ex, ey), (pupil_w, pupil_h), float(np.degrees(angle)), 0, 360, 0.02, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (ex, ey), (pupil_w, pupil_h), float(np.degrees(angle)), 0, 360, 0.04, -1, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (ex, ey), (pupil_w, pupil_h), float(np.degrees(angle)), 0, 360, 0.02, -1, lineType=_cv2.LINE_AA)

    return _finalize(M, R, CC, sm, "demon_eye_field")
pattern_demon_eye_field._spb_concept_complete = True


# ============================================================================
# 10) CRYPT_BRICK  (Gothic — replaces brushed_linear_warm)
# ============================================================================

def pattern_crypt_brick(shape, seed, sm, **kwargs):
    """crypt_brick.

    identity: heavy stone-block masonry — dark cold-grey blocks 18-30 px
    wide x 10-16 px tall in staggered courses, with deep dark mortar
    seams between. Cohesive cold-grey palette. HERO: 6-10 cracked/chipped
    blocks with bare-stone exposure and subtle moss-green CC accent.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 881001)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)
    # Deep cold-grey mortar substrate
    # Dark mortar substrate (composite-dark)
    M = np.full((h, w), 0.08, dtype=np.float32)
    R = np.full((h, w), 0.10, dtype=np.float32)
    CC = np.full((h, w), 0.06, dtype=np.float32)
    BASE_M, BASE_R, BASE_C = 0.45, 0.35, 0.22  # cold stone-grey (composite-readable)

    if _CV2_OK:
        course_h = max(7, int(11 * s))
        course_h = min(course_h, 13)  # 14-22 px tall blocks (with 1-2 mortar seam)
        rows = h // course_h + 2
        kings = []
        for ry in range(rows):
            row_offset = (ry % 2) * int(course_h * 0.7)
            cx = row_offset
            while cx < w + course_h:
                block_w = int(rng.uniform(11.0, 16.0) * s)  # 22-30 px wide
                block_w = max(10, min(block_w, 18))
                x0 = cx + int(rng.integers(-1, 2))
                y0 = ry * course_h + int(rng.integers(-1, 2))
                x1 = x0 + block_w
                y1 = y0 + int(course_h * 0.82)  # leave space for mortar seam
                if x0 < 0 or y0 < 0 or x1 >= w or y1 >= h:
                    cx += block_w + 1
                    continue
                pts = np.array([
                    [x0 + int(rng.uniform(0, 2)), y0 + int(rng.uniform(0, 2))],
                    [x1 - int(rng.uniform(0, 2)), y0 + int(rng.uniform(0, 2))],
                    [x1 - int(rng.uniform(0, 2)), y1 - int(rng.uniform(0, 2))],
                    [x0 + int(rng.uniform(0, 2)), y1 - int(rng.uniform(0, 2))],
                ], dtype=np.int32)
                pM = _c01(BASE_M + rng.uniform(-0.05, 0.05))
                pR = _c01(BASE_R + rng.uniform(-0.05, 0.05))
                pC = _c01(BASE_C + rng.uniform(-0.04, 0.04))
                _cv2.fillPoly(M, [pts], pM, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(R, [pts], pR, lineType=_cv2.LINE_AA)
                _cv2.fillPoly(CC, [pts], pC, lineType=_cv2.LINE_AA)
                # Top-edge highlight (sun-catch)
                _cv2.line(M, (pts[0][0], pts[0][1]), (pts[1][0], pts[1][1]),
                          min(0.55, pM + 0.18), 1, lineType=_cv2.LINE_AA)
                # Bottom-edge shadow
                _cv2.line(M, (pts[3][0], pts[3][1]), (pts[2][0], pts[2][1]),
                          max(0.0, pM * 0.40), 1, lineType=_cv2.LINE_AA)
                # 2-4 surface pock marks
                if rng.random() < 0.7:
                    for _ in range(int(rng.integers(2, 5))):
                        dx = int(rng.uniform(x0 + 2, x1 - 2))
                        dy = int(rng.uniform(y0 + 2, y1 - 2))
                        dr = int(rng.uniform(1, 3))
                        _cv2.circle(M, (dx, dy), dr, max(0.0, pM * 0.40), -1, lineType=_cv2.LINE_AA)
                        _cv2.circle(R, (dx, dy), dr, max(0.0, pR * 0.40), -1, lineType=_cv2.LINE_AA)
                kings.append((x0, y0, block_w, int(course_h * 0.82)))
                cx += block_w + max(1, int(course_h * 0.10))

        # HERO — 6-10 cracked blocks with moss-green CC accents
        n_hero = int(rng.integers(6, 11))
        if kings:
            picks = rng.choice(len(kings), size=min(n_hero, len(kings)), replace=False)
            for idx in picks:
                x0, y0, bw, bh = kings[idx]
                # Crack line zig-zagging across block
                start = (x0 + int(bw * float(rng.uniform(0.1, 0.4))),
                         y0 + int(bh * float(rng.uniform(0.0, 0.3))))
                end = (x0 + int(bw * float(rng.uniform(0.6, 0.95))),
                       y0 + int(bh * float(rng.uniform(0.6, 1.0))))
                # 3-segment zigzag
                m1 = (int((start[0] + end[0]) * 0.4 + rng.integers(-2, 3)),
                      int((start[1] + end[1]) * 0.4 + rng.integers(-2, 3)))
                m2 = (int((start[0] + end[0]) * 0.7 + rng.integers(-2, 3)),
                      int((start[1] + end[1]) * 0.7 + rng.integers(-2, 3)))
                _cv2.line(M, start, m1, 0.04, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, m1, m2, 0.04, 1, lineType=_cv2.LINE_AA)
                _cv2.line(M, m2, end, 0.04, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, start, m1, 0.10, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, m1, m2, 0.10, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, m2, end, 0.10, 1, lineType=_cv2.LINE_AA)
                # Moss-green CC accent (subtle algae growth) on bottom corner
                moss_cx = x0 + int(bw * 0.15)
                moss_cy = y0 + bh - 2
                moss_r = max(2, int(min(bw, bh) * 0.18))
                _cv2.circle(CC, (moss_cx, moss_cy), moss_r, 0.55, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (moss_cx, moss_cy), moss_r, 0.45, 1, lineType=_cv2.LINE_AA)

    return _finalize(M, R, CC, sm, "crypt_brick")
pattern_crypt_brick._spb_concept_complete = True


# ============================================================================
# RACING-PIVOT BATCH 3 (2026-05-26 R6 owner tick)
# 5 new replacements driven by owner Mode-A ratings + sparkle diversification.
#   aniso_grain                 -> chainmail_armor          (PREDATOR — replaces 'boring' aniso_grain)
#   airbrush_gradient_bloom     -> engine_turn_starburst    (ENGINE-TURN — owner asked for engine-turn)
#   sparkle_champagne           -> tiger_stripe_field       (PREDATOR — sparkle cluster diversification)
#   brushed_sparkle             -> nordic_rune_field        (GOTHIC — sparkle cluster diversification)
#   sparkle_shattered           -> razor_wire_coil          (PREDATOR/MILITARY — sparkle cluster diversification)
# ============================================================================


# ----------------------------------------------------------------------------
# 11) CHAINMAIL_ARMOR  (Predator/Armor — replaces aniso_grain)
# ----------------------------------------------------------------------------

def pattern_chainmail_armor(shape, seed, sm, **kwargs):
    """chainmail_armor.

    identity: R6-Loop owner-rebuild — TRUE INTERLOCKING MAIL. Owner:
    "doesn't match name, sparse, boring". Fix: rings rendered as
    DOUBLE-STROKE (outer dark + inner bright rim) so each ring reads as a
    real metal loop on the thumb. Tighter European-4-in-1 weave packing
    so rings actually OVERLAP like real mail. NEW HERO motif: 2-3
    PATTERN-WELDED DAMASCUS RIBBONS (long undulating bands of folded
    light/dark steel) wind diagonally through the mail — unexpected
    metallurgy/fashion-print mix. Plus 8-12 enlarged polished hero
    rings + 4-6 broken ring chunks for combat damage character.

    Per-feature TIGHT chroma uniform (±0.05) from blued-steel zone palette.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 881131)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)

    # DARK substrate (composite-dark: blackened steel undercoat)
    M = np.full((h, w), 0.10, dtype=np.float32)
    R = np.full((h, w), 0.12, dtype=np.float32)
    CC = np.full((h, w), 0.08, dtype=np.float32)
    BASE_M, BASE_R, BASE_C = 0.62, 0.28, 0.30  # blued-steel rim

    if _CV2_OK:
        # NEW HERO — 2-3 DAMASCUS PATTERN-WELDED RIBBONS first (underneath
        # the mail so the mail rings sit on top — proper layering).
        n_ribbons = int(rng.integers(2, 4))
        for _rib in range(n_ribbons):
            # Long diagonal ribbon — phase-offset sin wave
            ang = float(rng.choice([np.deg2rad(35), np.deg2rad(-35), np.deg2rad(55)]))
            ribbon_y0 = int(rng.uniform(0.15, 0.85) * h)
            ribbon_width = int(np.clip(rng.uniform(6, 10), 5, 10))
            # Sample sparsely — trace the ribbon centerline once, then dashes
            n_samples = max(20, int(max(w, h) / 6))
            wave_amp = float(rng.uniform(6.0, 12.0))
            wave_period = float(rng.uniform(60.0, 100.0))
            pts = []
            for k in range(n_samples):
                t = k / float(n_samples - 1)
                x_base = -mn * 0.2 + t * (mn * 1.4)
                y_base = ribbon_y0 + np.tan(ang) * (x_base - w * 0.5)
                wave = np.sin(t * np.pi * 2 * (mn / wave_period)) * wave_amp
                px = x_base - np.sin(ang) * wave
                py = y_base + np.cos(ang) * wave
                pts.append((int(px), int(py)))
            # Paint damascus banded line — alternating light/dark segments
            for k in range(len(pts) - 1):
                t = k / float(len(pts))
                phase = (t * 6.0) % 1.0  # 6 light/dark bands per ribbon
                if phase < 0.5:
                    dM = _c01(0.30 + rng.uniform(-0.04, 0.04))
                    dR = _c01(0.42 + rng.uniform(-0.04, 0.04))
                    dCC = _c01(0.20 + rng.uniform(-0.05, 0.05))
                else:
                    dM = _c01(0.72 + rng.uniform(-0.04, 0.04))
                    dR = _c01(0.20 + rng.uniform(-0.04, 0.04))
                    dCC = _c01(0.48 + rng.uniform(-0.05, 0.05))
                _cv2.line(M, pts[k], pts[k + 1], dM, ribbon_width, lineType=_cv2.LINE_AA)
                _cv2.line(R, pts[k], pts[k + 1], dR, ribbon_width, lineType=_cv2.LINE_AA)
                _cv2.line(CC, pts[k], pts[k + 1], dCC, ribbon_width, lineType=_cv2.LINE_AA)

        # Mail ring grid — European 4-in-1 weave: visible overlapping rings.
        # Rings sized big enough to read as rings on 256 thumb.
        ring_r = max(8, int(9.0 * s))
        ring_r = min(ring_r, 12)
        pitch_x = max(11, int(ring_r * 1.55))  # looser pitch so rings READ as rings
        pitch_y = max(10, int(ring_r * 1.35))
        cols = w // pitch_x + 2
        rows = h // pitch_y + 2
        polished_candidates = []
        for ry in range(rows):
            row_offset = (ry % 2) * (pitch_x // 2)
            for cxi in range(cols):
                cx = row_offset + cxi * pitch_x + int(rng.integers(-1, 2))
                cy = ry * pitch_y + int(rng.integers(-1, 2))
                if not (ring_r < cx < w - ring_r and ring_r < cy < h - ring_r):
                    continue
                # TIGHT chroma uniform per ring
                pM = _c01(BASE_M + rng.uniform(-0.05, 0.05))
                pR = _c01(BASE_R + rng.uniform(-0.05, 0.05))
                pC = _c01(BASE_C + rng.uniform(-0.05, 0.05))
                # OUTER dark stroke (defines ring edge against substrate)
                _cv2.circle(M, (cx, cy), ring_r, pM * 0.55, 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), ring_r, min(0.95, pR + 0.18), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), ring_r, pC * 0.6, 1, lineType=_cv2.LINE_AA)
                # INNER bright stroke (the metal rim itself, brighter)
                _cv2.circle(M, (cx, cy), ring_r - 1, pM, 2, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), ring_r - 1, pR, 2, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), ring_r - 1, pC, 2, lineType=_cv2.LINE_AA)
                # Bright specular kick (one side)
                hi_a = float(rng.uniform(195, 285))
                _cv2.ellipse(M, (cx, cy), (ring_r - 1, ring_r - 1), 0,
                             hi_a, hi_a + 65, min(0.95, pM + 0.30), 2, lineType=_cv2.LINE_AA)
                polished_candidates.append((cx, cy))

        # HERO — enlarged polished rings (the show-off mail accents)
        n_hero = int(rng.integers(8, 13))
        if polished_candidates:
            picks = rng.choice(len(polished_candidates),
                               size=min(n_hero, len(polished_candidates)),
                               replace=False)
            for idx in picks:
                cx, cy = polished_candidates[idx]
                hr = int(ring_r * 1.4)
                hr = max(7, min(hr, 12))
                # Double-stroke hero
                _cv2.circle(M, (cx, cy), hr, min(0.94, BASE_M + 0.28), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), hr, max(0.06, BASE_R - 0.14), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), hr, min(0.88, BASE_C + 0.30), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(M, (cx, cy), hr - 1, min(0.96, BASE_M + 0.32), 2, lineType=_cv2.LINE_AA)
                # Bright sharp specular arc
                _cv2.ellipse(M, (cx, cy), (hr, hr), 0, 200, 260, 0.98, 2, lineType=_cv2.LINE_AA)

        # 4-6 broken/torn ring chunks (combat damage)
        n_broken = int(rng.integers(4, 7))
        for _ in range(n_broken):
            bx = int(rng.integers(8, w - 8))
            by = int(rng.integers(8, h - 8))
            br = int(rng.uniform(4, 7) * s)
            br = max(3, min(br, 6))
            a0 = float(rng.uniform(0, 360))
            a1 = a0 + float(rng.uniform(80, 180))
            _cv2.ellipse(M, (bx, by), (br, br), 0, a0, a1, 0.85, 2, lineType=_cv2.LINE_AA)
            _cv2.ellipse(R, (bx, by), (br, br), 0, a0, a1, 0.22, 2, lineType=_cv2.LINE_AA)
            _cv2.ellipse(CC, (bx, by), (br, br), 0, a0, a1, 0.45, 2, lineType=_cv2.LINE_AA)

    return _finalize(M, R, CC, sm, "chainmail_armor")
pattern_chainmail_armor._spb_concept_complete = True


# ----------------------------------------------------------------------------
# 12) ENGINE_TURN_STARBURST  (Engine-Turn — replaces airbrush_gradient_bloom)
# ----------------------------------------------------------------------------

def pattern_engine_turn_starburst(shape, seed, sm, **kwargs):
    """engine_turn_starburst — R6 rebuild (owner 1/REBUILD).

    identity: Bugatti dashboard guilloche — POLISHED CIRCULAR DISCS
    (10-22 px) packed in a brick-staggered grid covering the WHOLE
    canvas. Each disc has a CONCENTRIC RING set of fly-cut tool marks
    (3-5 nested rings) plus a tiny center pivot DOT plus a bright
    leading-edge crescent (the "starburst" arc of light reflecting off
    one side). Per-disc INDEPENDENT chroma TIGHT-jittered from polished
    billet steel base. HERO: 8-14 oversized 26-32 px hub-cap discs with
    extra crisp ring count and brighter crescents. ANTI-CLONE:
    DISTINCTLY CIRCULAR, brick-staggered, concentric rings — NOT radial
    rays, NOT pentagonal scales, NOT diamond tessellation.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 881201)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)

    # Dark polished-steel substrate so circular discs pop bright
    M = np.full((h, w), 0.12, dtype=np.float32)
    R = np.full((h, w), 0.14, dtype=np.float32)
    CC = np.full((h, w), 0.10, dtype=np.float32)
    BASE_M, BASE_R, BASE_C = 0.66, 0.22, 0.34  # polished billet

    if _CV2_OK:
        # Brick-staggered grid of CIRCULAR DISCS covering whole canvas
        disc_d = max(10, int(11 * s))  # ~11 px at 256, scales up
        if disc_d % 2 == 0:
            disc_d += 1
        step_x = int(disc_d * 0.92)  # tight overlap
        step_y = int(disc_d * 0.82)
        for row_i, ry in enumerate(range(disc_d // 2, h - disc_d // 2, step_y)):
            row_offset = (disc_d // 2) if (row_i % 2 == 1) else 0
            for rx in range(disc_d // 2 + row_offset, w - disc_d // 2, step_x):
                cx = rx + int(rng.integers(-2, 3))
                cy = ry + int(rng.integers(-2, 3))
                radius = disc_d // 2 + int(rng.integers(-1, 2))
                radius = max(4, min(radius, 16))
                # Per-disc INDEPENDENT chroma tight jitter
                cM = _c01(BASE_M + rng.uniform(-0.05, 0.05))
                cR = _c01(BASE_R + rng.uniform(-0.04, 0.04))
                cC = _c01(BASE_C + rng.uniform(-0.05, 0.05))
                # Disc body
                _cv2.circle(M, (cx, cy), radius, cM, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (cx, cy), radius, cR, -1, lineType=_cv2.LINE_AA)
                _cv2.circle(CC, (cx, cy), radius, cC, -1, lineType=_cv2.LINE_AA)
                # CONCENTRIC RING tool-marks — 3-4 nested rings
                n_rings = int(rng.integers(3, 5))
                for k in range(n_rings):
                    rr = max(1, int(radius * (0.30 + k * 0.20)))
                    if rr >= radius - 1: break
                    ring_M = _c01(cM + rng.uniform(-0.03, 0.06))
                    _cv2.circle(M, (cx, cy), rr, ring_M, 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(R, (cx, cy), rr, _c01(cR - 0.04), 1, lineType=_cv2.LINE_AA)
                # LEADING-EDGE CRESCENT — bright arc on one side
                cres_phase = float(rng.uniform(0, 360))
                _cv2.ellipse(M, (cx, cy), (radius, radius), cres_phase,
                             -45, 45, _c01(cM + 0.22),
                             max(1, radius // 5), lineType=_cv2.LINE_AA)
                # DARK rim (disc edge shadow)
                _cv2.circle(M, (cx, cy), radius, _c01(cM * 0.35), 1, lineType=_cv2.LINE_AA)
                # Center pivot dot
                _cv2.circle(M, (cx, cy), max(1, radius // 6),
                            _c01(cM + 0.14), -1, lineType=_cv2.LINE_AA)

        # HERO — 8-14 oversized 26-32 px hub-cap discs
        n_hero = int(rng.integers(8, 15))
        for _ in range(n_hero):
            hx = int(rng.integers(20, w - 20))
            hy = int(rng.integers(20, h - 20))
            hr = int(rng.uniform(13, 17) * (s * 0.9 + 0.1))
            hr = max(13, min(hr, 18))
            cM = _c01(BASE_M + rng.uniform(-0.03, 0.05))
            cR = _c01(BASE_R + rng.uniform(-0.03, 0.03))
            cC = _c01(BASE_C + rng.uniform(-0.03, 0.05))
            _cv2.circle(M, (hx, hy), hr, cM, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (hx, hy), hr, cR, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (hx, hy), hr, cC, -1, lineType=_cv2.LINE_AA)
            # 5-7 concentric rings, crisp
            n_rings = int(rng.integers(5, 8))
            for k in range(n_rings):
                rr = max(2, int(hr * (0.16 + k * 0.13)))
                if rr >= hr - 1: break
                _cv2.circle(M, (hx, hy), rr, _c01(cM + 0.08), 1, lineType=_cv2.LINE_AA)
                _cv2.circle(R, (hx, hy), rr, _c01(cR - 0.06), 1, lineType=_cv2.LINE_AA)
            # Big crescent
            cres_phase = float(rng.uniform(0, 360))
            _cv2.ellipse(M, (hx, hy), (hr, hr), cres_phase,
                         -55, 55, 0.96, max(2, hr // 4), lineType=_cv2.LINE_AA)
            # Dark rim + bright pivot center
            _cv2.circle(M, (hx, hy), hr, float(cM * 0.30), 1, lineType=_cv2.LINE_AA)
            _cv2.circle(M, (hx, hy), max(2, hr // 6), 0.95, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (hx, hy), max(2, hr // 6), 0.70, -1, lineType=_cv2.LINE_AA)

    return _finalize(M, R, CC, sm, "engine_turn_starburst")
pattern_engine_turn_starburst._spb_concept_complete = True


# ----------------------------------------------------------------------------
# 13) TIGER_STRIPE_FIELD  (Predator — replaces sparkle_champagne)
# ----------------------------------------------------------------------------

def pattern_tiger_stripe_field(shape, seed, sm, **kwargs):
    """tiger_stripe_field.

    R6 CREATIVE SECOND-PASS 2026-05-26: tiger fur driven by REACTION-
    DIFFUSION (Turing-pattern) wavefronts — biology motif. The stripe
    placement field comes from anisotropic FBM thresholded along a
    preferred axis, producing organic forking/Y-branching stripes like
    real mammal coats. Stripes are 4-8 px black bands on warm tan-orange
    fur substrate with FBM fur-grain. HERO: 8-12 extra-bold cheek-stripes
    with subtle orange edge halo. All features 4-22 px.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 881301)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)

    # Warm tan fur substrate (cap M<=0.50 anti-magenta, cap R<=0.45)
    M = np.full((h, w), 0.50, dtype=np.float32)
    R = np.full((h, w), 0.30, dtype=np.float32)
    CC = np.full((h, w), 0.18, dtype=np.float32)

    # Fur grain variation
    # PERF NOTE: kept at full-res multi_scale_noise — the bare-fur tan
    # substrate is the dominant visible texture between stripes, so
    # downsampling drops SSIM to ~0.9946 (gate FAIL). Must stay exact.
    fur = _normalize(multi_scale_noise(shape, [3.0, 7.0, 14.0], [0.5, 0.3, 0.2], int(seed) + 881305))
    M = np.clip(M + (fur - 0.5) * 0.10, 0, 1)
    R = np.clip(R + (fur - 0.5) * 0.06, 0, 1)

    # === TURING-FIELD STRIPE MAP ===
    # Anisotropic FBM thresholded along a preferred axis = organic stripes
    # PERF: build rotated coords from 1D broadcast ramps instead of
    # materializing two full-res np.mgrid int64 grids — mathematically
    # identical (float32), just avoids the 2x 2048^2 grid allocation + cast.
    flow_a = float(rng.uniform(-0.35, 0.35))  # near-vertical with slight tilt
    # Match the original dtype EXACTLY: np.mgrid grids were float32, multiplied
    # by Python-float (float64) cos/sin -> float64 rotated coords. Keep the
    # ramps float32 and the scalars float64 so the broadcast promotes to the
    # same float64 result (bit-identical), just without allocating the grids.
    _xc = np.arange(w, dtype=np.float32)
    _yc = np.arange(h, dtype=np.float32)
    _cos_a = np.cos(flow_a)
    _sin_a = np.sin(flow_a)
    # rotated coords (broadcast outer combination)
    rxx = _xc[None, :] * _cos_a - _yc[:, None] * _sin_a
    ryy = _xc[None, :] * _sin_a + _yc[:, None] * _cos_a
    # high-frequency stripe carrier on rxx axis
    stripe_freq = float(rng.uniform(0.30, 0.46))
    stripe_carrier = np.sin(rxx * stripe_freq + np.sin(ryy * 0.05) * 1.4)
    # modulate by low-frequency FBM (forking)
    # PERF NOTE: kept at full-res multi_scale_noise — this field is HARD-
    # thresholded (>0.35) into the stripe mask, so downsampling flips mask
    # edges (gate measured SSIM 0.887). Must stay exact.
    fbm_mod = _normalize(multi_scale_noise(shape, [2.4, 5.0, 10.0], [0.55, 0.3, 0.15], int(seed) + 881306))
    stripe_mask = ((stripe_carrier > 0.55) & (fbm_mod > 0.35)).astype(np.float32)
    # Soften so the mask only marks stripe interiors (anti-aliased edges)
    if _CV2_OK:
        stripe_mask = _cv2.GaussianBlur(stripe_mask, (0, 0), 0.7)

    STRIPE_M, STRIPE_R, STRIPE_C = 0.08, 0.10, 0.05  # dark tiger stripe (composite-dark)
    M = np.where(stripe_mask > 0.4, STRIPE_M + (stripe_mask - 0.4) * 0.0, M)
    R = np.where(stripe_mask > 0.4, STRIPE_R, R)
    CC = np.where(stripe_mask > 0.4, STRIPE_C, CC)

    if _CV2_OK:
        # Short stub stripes (80-150 of them) — accent darts
        n_stub = int(np.clip(110 * s * s, 80, 150))
        for _ in range(n_stub):
            cx = int(rng.integers(4, w - 4))
            cy = int(rng.integers(4, h - 4))
            stub_len = int(rng.uniform(6, 14) * s)
            stub_len = max(5, min(stub_len, 14))
            tilt = float(rng.uniform(-0.25, 0.25))
            cos_t = np.cos(tilt - np.pi / 2)
            sin_t = np.sin(tilt - np.pi / 2)
            p0 = (cx - int(cos_t * stub_len / 2), cy - int(sin_t * stub_len / 2))
            p1 = (cx + int(cos_t * stub_len / 2), cy + int(sin_t * stub_len / 2))
            stub_w = int(rng.uniform(2, 4) * s)
            stub_w = max(2, min(stub_w, 4))
            sM = _c01(STRIPE_M + rng.uniform(-0.04, 0.04))
            sR = _c01(STRIPE_R + rng.uniform(-0.04, 0.04))
            _cv2.line(M, p0, p1, sM, stub_w, lineType=_cv2.LINE_AA)
            _cv2.line(R, p0, p1, sR, stub_w, lineType=_cv2.LINE_AA)
            _cv2.line(CC, p0, p1, STRIPE_C, stub_w, lineType=_cv2.LINE_AA)

        # HERO — 6-10 extra-bold stripes with bright orange edge halo
        n_hero = int(rng.integers(6, 11))
        for _ in range(n_hero):
            base_x = int(rng.uniform(12, w - 12))
            cur_x = base_x
            cur_y = int(rng.uniform(-8, 8))
            tilt = float(rng.uniform(-0.18, 0.18))
            n_segs = int(rng.integers(10, 18))
            pts = []
            for k in range(n_segs):
                cur_x += int(np.sin(k * 0.6 + tilt * 3.0) * 5 + rng.integers(-2, 3))
                cur_y += int(h / n_segs) + int(rng.integers(-2, 3))
                if 0 <= cur_x < w and 0 <= cur_y < h:
                    pts.append((cur_x, cur_y))
            if len(pts) < 2:
                continue
            arr = np.array(pts, dtype=np.int32)
            # Bright orange edge halo first (wider)
            halo_w = int(rng.uniform(5, 8) * s)
            halo_w = max(5, min(halo_w, 8))
            _cv2.polylines(M, [arr], False, 0.85, halo_w, lineType=_cv2.LINE_AA)
            _cv2.polylines(R, [arr], False, 0.45, halo_w, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [arr], False, 0.10, halo_w, lineType=_cv2.LINE_AA)
            # Dark core stripe inside
            core_w = max(2, halo_w - 3)
            _cv2.polylines(M, [arr], False, 0.06, core_w, lineType=_cv2.LINE_AA)
            _cv2.polylines(R, [arr], False, 0.08, core_w, lineType=_cv2.LINE_AA)
            _cv2.polylines(CC, [arr], False, 0.04, core_w, lineType=_cv2.LINE_AA)

    return _finalize(M, R, CC, sm, "tiger_stripe_field")
pattern_tiger_stripe_field._spb_concept_complete = True


# ----------------------------------------------------------------------------
# 14) NORDIC_RUNE_FIELD  (Gothic — replaces brushed_sparkle)
# ----------------------------------------------------------------------------

def pattern_nordic_rune_field(shape, seed, sm, **kwargs):
    """nordic_rune_field.

    identity: R6 tick 2026-05-26 — owner rated 3/REBUILD ("very sparse,
    hardly anything comes through, don't like the pattern either").
    REBUILD: TRIPLE the rune density, much higher contrast bone-white
    runes on composite-dark stone, bigger HERO runes, and a NEW
    CREATIVE HERO motif: ley-line connector grid — thin glowing arcane
    lines linking the hero runes into a constellation graph (like a
    Viking ritual stone with runic circuit etched between them). Plus
    9 rune shapes (added Berkana, Kenaz, Mannaz). Tight ±0.05 chroma
    jitter from a single bone+blood palette.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 881401)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)

    # Dark slate substrate — composite-dark
    M = np.full((h, w), 0.18, dtype=np.float32)
    R = np.full((h, w), 0.15, dtype=np.float32)
    CC = np.full((h, w), 0.10, dtype=np.float32)
    grain = _normalize(multi_scale_noise(shape, [3.5, 8.0, 16.0], [0.5, 0.3, 0.2], int(seed) + 881405))
    M = np.clip(M + (grain - 0.5) * 0.08, 0, 1)
    R = np.clip(R + (grain - 0.5) * 0.05, 0, 1)

    # Bone-white rune colour (BRIGHTER for contrast)
    RUNE_M, RUNE_R, RUNE_C = 0.92, 0.22, 0.62
    # Blood-magic colour
    BLOOD_M, BLOOD_R, BLOOD_C = 0.95, 0.34, 0.18
    # Ley-line colour (cool arcane blue glow)
    LEY_M, LEY_R, LEY_C = 0.55, 0.40, 0.70

    rune_shapes = [
        # Algiz (Y)
        [[(0.5, 1.0), (0.5, 0.5)], [(0.5, 0.5), (0.0, 0.0)], [(0.5, 0.5), (1.0, 0.0)]],
        # Tiwaz (arrow up)
        [[(0.5, 1.0), (0.5, 0.0)], [(0.5, 0.0), (0.0, 0.3)], [(0.5, 0.0), (1.0, 0.3)]],
        # Othala (diamond+legs)
        [[(0.5, 0.0), (1.0, 0.4)], [(1.0, 0.4), (0.5, 0.8)], [(0.5, 0.8), (0.0, 0.4)], [(0.0, 0.4), (0.5, 0.0)], [(0.5, 0.8), (0.0, 1.0)], [(0.5, 0.8), (1.0, 1.0)]],
        # Eihwaz (Z)
        [[(0.0, 0.0), (1.0, 0.0)], [(1.0, 0.0), (0.0, 1.0)], [(0.0, 1.0), (1.0, 1.0)]],
        # Ansuz (F)
        [[(0.0, 0.0), (0.0, 1.0)], [(0.0, 0.0), (1.0, 0.3)], [(0.0, 0.45), (0.8, 0.6)]],
        # Sowilo (S-zigzag)
        [[(1.0, 0.0), (0.0, 0.4)], [(0.0, 0.4), (1.0, 0.6)], [(1.0, 0.6), (0.0, 1.0)]],
        # Raidho (R)
        [[(0.0, 0.0), (0.0, 1.0)], [(0.0, 0.0), (0.8, 0.4)], [(0.8, 0.4), (0.0, 0.5)], [(0.0, 0.5), (0.8, 1.0)]],
        # Hagalaz (H+diag)
        [[(0.0, 0.0), (0.0, 1.0)], [(1.0, 0.0), (1.0, 1.0)], [(0.0, 0.3), (1.0, 0.7)]],
        # Berkana (B)
        [[(0.0, 0.0), (0.0, 1.0)], [(0.0, 0.0), (0.8, 0.25)], [(0.8, 0.25), (0.0, 0.5)], [(0.0, 0.5), (0.8, 0.75)], [(0.8, 0.75), (0.0, 1.0)]],
        # Kenaz (<)
        [[(1.0, 0.0), (0.0, 0.5)], [(0.0, 0.5), (1.0, 1.0)]],
        # Mannaz (M)
        [[(0.0, 0.0), (0.0, 1.0)], [(1.0, 0.0), (1.0, 1.0)], [(0.0, 0.0), (1.0, 0.6)], [(1.0, 0.0), (0.0, 0.6)]],
    ]

    def _draw_rune(img_M, img_R, img_C, cx, cy, size, M_val, R_val, C_val, thick, shape_pts):
        for seg in shape_pts:
            (sx0, sy0), (sx1, sy1) = seg
            p0 = (int(cx + (sx0 - 0.5) * size), int(cy + (sy0 - 0.5) * size))
            p1 = (int(cx + (sx1 - 0.5) * size), int(cy + (sy1 - 0.5) * size))
            _cv2.line(img_M, p0, p1, M_val, thick, lineType=_cv2.LINE_AA)
            _cv2.line(img_R, p0, p1, R_val, thick, lineType=_cv2.LINE_AA)
            _cv2.line(img_C, p0, p1, C_val, thick, lineType=_cv2.LINE_AA)

    if _CV2_OK:
        # 1) HERO LEY-LINE CONNECTOR GRAPH — draw the underlay first
        # Pick 8-12 hero anchor points across the canvas
        n_anchors = int(rng.integers(8, 13))
        anchors = []
        for _ in range(n_anchors):
            ax = int(rng.integers(20, w - 20))
            ay = int(rng.integers(20, h - 20))
            anchors.append((ax, ay))
        # Draw faint ley lines connecting each anchor to its 2-3 nearest neighbours
        for i, (ax, ay) in enumerate(anchors):
            # find 2 nearest others
            dists = sorted(
                [(j, (ax - bx) ** 2 + (ay - by) ** 2) for j, (bx, by) in enumerate(anchors) if j != i],
                key=lambda x: x[1]
            )[:2]
            for j, _d in dists:
                bx, by = anchors[j]
                # ley line — faint glowing arcane connection
                ley_thick = max(1, int(2 * s))
                _cv2.line(M, (ax, ay), (bx, by), LEY_M, ley_thick, lineType=_cv2.LINE_AA)
                _cv2.line(R, (ax, ay), (bx, by), LEY_R, ley_thick, lineType=_cv2.LINE_AA)
                _cv2.line(CC, (ax, ay), (bx, by), LEY_C, ley_thick, lineType=_cv2.LINE_AA)

        # 2) TRIPLE-DENSITY rune field — 240-380 runes
        n_runes = int(np.clip(320 * s * s, 240, 400))
        placed = []
        attempts = 0
        while len(placed) < n_runes and attempts < n_runes * 6:
            attempts += 1
            rx = int(rng.integers(10, w - 10))
            ry = int(rng.integers(10, h - 10))
            rsize = int(rng.uniform(8, 13) * s)  # 16-26 px (LARGER)
            rsize = max(7, min(rsize, 14))
            min_d_sq = (rsize * 1.2) ** 2
            ok = True
            for (px, py, _) in placed[-40:]:
                if (rx - px) ** 2 + (ry - py) ** 2 < min_d_sq:
                    ok = False
                    break
            if not ok:
                continue
            shape_id = int(rng.integers(0, len(rune_shapes)))
            rM = _c01(RUNE_M + rng.uniform(-0.05, 0.05))
            rR = _c01(RUNE_R + rng.uniform(-0.04, 0.04))
            rC = _c01(RUNE_C + rng.uniform(-0.05, 0.05))
            thick = max(1, int(s))
            _draw_rune(M, R, CC, rx, ry, rsize, rM, rR, rC, thick, rune_shapes[shape_id])
            placed.append((rx, ry, rsize))

        # 3) HERO RUNES — sit on the ley-line anchor points (8-12 of them)
        for (hx, hy) in anchors:
            hsize = int(rng.uniform(16, 22) * s)  # 32-44 px
            hsize = max(14, min(hsize, 22))
            shape_id = int(rng.integers(0, len(rune_shapes)))
            # Halo thick underlayer
            _draw_rune(M, R, CC, hx, hy, hsize, 0.55, 0.30, 0.42, max(3, int(4 * s)), rune_shapes[shape_id])
            # Bone-white main
            _draw_rune(M, R, CC, hx, hy, hsize, 0.97, 0.22, 0.68, max(2, int(2 * s)), rune_shapes[shape_id])

        # 4) 4-7 BLOOD-MAGIC red runes
        n_blood = int(rng.integers(4, 8))
        for _ in range(n_blood):
            bx = int(rng.integers(16, w - 16))
            by = int(rng.integers(16, h - 16))
            bsize = int(rng.uniform(13, 17) * s)  # 26-34 px
            bsize = max(11, min(bsize, 18))
            shape_id = int(rng.integers(0, len(rune_shapes)))
            # Glow halo
            _draw_rune(M, R, CC, bx, by, bsize, 0.68, 0.36, 0.12, max(3, int(4 * s)), rune_shapes[shape_id])
            # Blood-red core
            _draw_rune(M, R, CC, bx, by, bsize, BLOOD_M, BLOOD_R, BLOOD_C, max(2, int(2 * s)), rune_shapes[shape_id])

    return _finalize(M, R, CC, sm, "nordic_rune_field")
pattern_nordic_rune_field._spb_concept_complete = True


# ----------------------------------------------------------------------------
# 15) RAZOR_WIRE_COIL  (Predator/Military — replaces sparkle_shattered)
# ----------------------------------------------------------------------------

def pattern_razor_wire_coil(shape, seed, sm, **kwargs):
    """razor_wire_coil.

    identity: R6 OWNER-REBUILD — *military concertina razor wire on
    matte-black ballistic panel*. Owner complaint addressed: previous
    looked "like a toddler drew razor wire" — caused by jittery sin
    waves and uneven coil distribution. Fix: build coils as PROPER
    PARAMETRIC HELICES (true coil mathematics, not random wobble), with
    discrete crisp blade triangles at FIXED pitch along each coil, plus
    a CLEAN diagonal bundle skeleton in the background. 18-26 helical
    coil arcs each 60-160 px long, blade pitch 6-9 px, blade size 5-8 px.
    Tight gunmetal palette ±0.04 jitter so the surface reads as one
    weapon, not confetti.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + 881501)
    mn = min(h, w)
    s = max(mn / 256.0, 0.6)

    # Military matte-black ballistic panel substrate with faint vertical brush grain
    M = np.full((h, w), 0.10, dtype=np.float32)
    R = np.full((h, w), 0.18, dtype=np.float32)
    CC = np.full((h, w), 0.06, dtype=np.float32)
    grain = _normalize(multi_scale_noise(shape, [0.8, 2.4], [0.6, 0.4], int(seed) + 881521))
    M = np.clip(M + (grain - 0.5) * 0.05, 0, 1)
    R = np.clip(R + (grain - 0.5) * 0.04, 0, 1)
    COIL_M, COIL_R, COIL_C = 0.58, 0.30, 0.22   # gunmetal base
    RAZOR_M, RAZOR_R, RAZOR_C = 0.82, 0.18, 0.34  # polished steel blade
    HIGHLIGHT_M = 0.96  # mirror crest along blade leading edge

    if _CV2_OK:
        # === COIL HELICES — true parametric helix geometry, NOT sin wobble ===
        # A helix viewed from the side projects to: stacked half-arcs alternating
        # over/under. We draw it as a SERIES of half-loop arcs along a diagonal
        # spine, which is what real concertina wire looks like in projection.
        # Diagonal master direction (cohesive across canvas)
        master_a = float(rng.uniform(-0.35, 0.35)) + (np.pi / 6.0)  # bias toward NE-SW
        cos_m, sin_m = float(np.cos(master_a)), float(np.sin(master_a))
        perp_m = (-sin_m, cos_m)

        # Coil bands — 4-7 parallel bands across canvas
        n_bands = int(np.clip(rng.integers(4, 8), 4, 7))
        # Band offsets perpendicular to master direction, evenly spaced + jitter
        band_step = float(min(h, w) / (n_bands + 1))
        coil_centers = []
        blade_attach = []  # (cx, cy, tangent_x, tangent_y, side)
        for bi in range(n_bands):
            # Anchor at left/top edge plus perpendicular offset
            off = (bi + 0.5) * band_step + float(rng.uniform(-band_step * 0.18, band_step * 0.18))
            # Origin: cross the canvas diagonally
            ox = -16.0 + perp_m[0] * (off - band_step * (n_bands - 1) * 0.5)
            oy = (h * 0.5) + perp_m[1] * (off - band_step * (n_bands - 1) * 0.5)
            # Step ONE LOOP at a time
            loop_pitch = _clip(rng.uniform(14, 22) * s, 12, 26)  # 12-26 px between loop centers
            loop_radius = int(np.clip(rng.uniform(5, 8) * s, 5, 9))  # 5-9 px arc radius
            n_loops = int(np.clip((w + h) / loop_pitch, 6, 32))
            cM_band = _c01(COIL_M + rng.uniform(-0.04, 0.04))
            cR_band = _c01(COIL_R + rng.uniform(-0.04, 0.04))
            cC_band = _c01(COIL_C + rng.uniform(-0.04, 0.04))
            for li in range(n_loops):
                t = li * loop_pitch
                cx = ox + cos_m * t
                cy = oy + sin_m * t
                if not (-loop_radius < cx < w + loop_radius and -loop_radius < cy < h + loop_radius):
                    continue
                # Each loop = half-arc above the spine then half-arc below — alternating
                # so consecutive loops look like a single coiled spring viewed from side.
                arc_start_deg = float(np.degrees(master_a) - 180)
                arc_end_deg = arc_start_deg + 200  # slightly past 180 for visual overlap
                rot_deg = float(np.degrees(master_a))
                # Coil body — 2 px thick
                _cv2.ellipse(M, (int(cx), int(cy)), (loop_radius, loop_radius), rot_deg, arc_start_deg, arc_end_deg, cM_band, 2, lineType=_cv2.LINE_AA)
                _cv2.ellipse(R, (int(cx), int(cy)), (loop_radius, loop_radius), rot_deg, arc_start_deg, arc_end_deg, cR_band, 2, lineType=_cv2.LINE_AA)
                _cv2.ellipse(CC, (int(cx), int(cy)), (loop_radius, loop_radius), rot_deg, arc_start_deg, arc_end_deg, cC_band, 2, lineType=_cv2.LINE_AA)
                # Bright top highlight — 1 px above the spine
                _cv2.ellipse(M, (int(cx), int(cy)), (loop_radius, loop_radius), rot_deg, arc_start_deg + 30, arc_end_deg - 90, HIGHLIGHT_M, 1, lineType=_cv2.LINE_AA)
                # Dark underside shadow
                _cv2.ellipse(M, (int(cx), int(cy)), (loop_radius, loop_radius), rot_deg, arc_end_deg - 30, arc_end_deg, max(0.0, cM_band * 0.45), 1, lineType=_cv2.LINE_AA)
                # Register blade attach points (top of arc, perpendicular outward)
                # 3 blade slots per loop at +60, +120, +180 deg from arc_start
                for blade_deg_off in (50, 110, 170):
                    bang = np.radians(arc_start_deg + blade_deg_off) + master_a  # rotated frame
                    bax = cx + np.cos(bang) * loop_radius
                    bay = cy + np.sin(bang) * loop_radius
                    if 0 <= bax < w and 0 <= bay < h:
                        # outward perpendicular to coil tangent
                        tang_a = bang + np.pi / 2
                        blade_attach.append((float(bax), float(bay), float(np.cos(tang_a)), float(np.sin(tang_a))))
                coil_centers.append((int(cx), int(cy), loop_radius))

        # === DIAMOND-PROFILE RAZOR BLADES — fixed pitch, crisp triangles ===
        # Per attach point: drop a blade if random gate passes (so it's not over-busy)
        for (bax, bay, dx, dy) in blade_attach:
            if rng.random() > 0.55:
                continue
            blade_len = _clip(rng.uniform(4.5, 7.5) * s, 4, 9)
            base_w = _clip(rng.uniform(1.3, 2.0) * s, 1.2, 2.4)
            # tangent (perpendicular to outward)
            tx, ty = -dy, dx
            p_tip = (int(bax + dx * blade_len), int(bay + dy * blade_len))
            p_b0 = (int(bax + tx * base_w), int(bay + ty * base_w))
            p_b1 = (int(bax - tx * base_w), int(bay - ty * base_w))
            if not (0 <= p_tip[0] < w and 0 <= p_tip[1] < h):
                continue
            tri = np.array([p_b0, p_b1, p_tip], dtype=np.int32)
            rM = _c01(RAZOR_M + rng.uniform(-0.04, 0.04))
            rR = _c01(RAZOR_R + rng.uniform(-0.04, 0.04))
            rC = _c01(RAZOR_C + rng.uniform(-0.04, 0.04))
            _cv2.fillPoly(M, [tri], rM, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(R, [tri], rR, lineType=_cv2.LINE_AA)
            _cv2.fillPoly(CC, [tri], rC, lineType=_cv2.LINE_AA)
            # mirror-bright keen edge along the leading face
            _cv2.line(M, p_b0, p_tip, HIGHLIGHT_M, 1, lineType=_cv2.LINE_AA)
            _cv2.line(CC, p_b0, p_tip, _c01(RAZOR_C + 0.20), 1, lineType=_cv2.LINE_AA)
            # dark trailing edge
            _cv2.line(M, p_b1, p_tip, _c01(RAZOR_M * 0.55), 1, lineType=_cv2.LINE_AA)

        # === BUNDLE CROSSING KNOTS — where adjacent coils tie together ===
        # 5-8 deliberate bundle knots: small disc + radial barb stubs
        n_knot = int(rng.integers(5, 9))
        for _ in range(n_knot):
            bx = int(rng.integers(20, max(21, w - 20)))
            by = int(rng.integers(20, max(21, h - 20)))
            br = int(np.clip(rng.uniform(4, 6) * s, 3, 7))
            _cv2.circle(M, (bx, by), br, 0.62, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (bx, by), br, 0.24, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(CC, (bx, by), br, 0.30, -1, lineType=_cv2.LINE_AA)
            _cv2.circle(M, (bx, by), br, HIGHLIGHT_M, 1, lineType=_cv2.LINE_AA)
            # tight ring of 5 short barbs
            for k in range(5):
                a = k * (2 * np.pi / 5.0) + float(rng.uniform(-0.15, 0.15))
                tip = (int(bx + np.cos(a) * (br + 3)), int(by + np.sin(a) * (br + 3)))
                _cv2.line(M, (bx, by), tip, 0.82, 1, lineType=_cv2.LINE_AA)
                _cv2.line(R, (bx, by), tip, 0.22, 1, lineType=_cv2.LINE_AA)

        # === PANEL RIVETS — 18-30 small fastener dots scattered (military feel) ===
        n_rivet = int(np.clip(24 * s * s, 14, 40))
        for _ in range(n_rivet):
            rx = int(rng.integers(2, w - 2))
            ry = int(rng.integers(2, h - 2))
            rr = max(1, int(1.5 * s))
            _cv2.circle(M, (rx, ry), rr, _c01(0.42 + rng.uniform(-0.03, 0.03)), -1, lineType=_cv2.LINE_AA)
            _cv2.circle(R, (rx, ry), rr, _c01(0.38 + rng.uniform(-0.03, 0.03)), -1, lineType=_cv2.LINE_AA)
            # tiny bright catchlight
            M[ry, rx] = 0.78

        # === PANEL HAIRLINE WEAR SCRATCHES — 80-180 short 3-7 px diagonal lines ===
        n_scr = int(np.clip(140 * s * s, 70, 220))
        for _ in range(n_scr):
            sx = int(rng.integers(0, w))
            sy = int(rng.integers(0, h))
            # roughly aligned with master direction so they read as wear streaks
            a = master_a + float(rng.uniform(-0.4, 0.4))
            L = float(rng.uniform(3, 7))
            ex = int(_clip(sx + np.cos(a) * L, 0, w - 1))
            ey = int(_clip(sy + np.sin(a) * L, 0, h - 1))
            _cv2.line(M, (sx, sy), (ex, ey), _c01(0.32 + rng.uniform(-0.05, 0.05)), 1, lineType=_cv2.LINE_AA)

    return _finalize(M, R, CC, sm, "razor_wire_coil")
pattern_razor_wire_coil._spb_concept_complete = True
