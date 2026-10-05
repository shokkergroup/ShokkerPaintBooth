"""
engine/expansions/wild_specs/liquid_tech.py — wild-spec-v2 family 'liquid_tech'.

wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity), demands
many-hue triplet zones. Family: mercury, shokk_mirage, shokk_phase,
shokk_tesseract_v2, shokk_apex, shokk_dual, solar_panel, shokk_venom.

DOCTRINE (binding):
  * Composite view = RGB stack (R=M metallic, G=R roughness, B=Cc clearcoat).
    high M -> red, high R -> green, high Cc -> blue, M+R -> yellow,
    M+Cc -> magenta, R+Cc -> cyan, all-high -> white, all-low -> black.
    Every finish carves 3-5 MOTIF ZONES, each with its OWN (M,R,Cc) triplet, so
    the map reads MANY HUES, not one.
  * CHANNELS CARRY DIFFERENT GEOMETRY. M, R, Cc are NOT one field rescaled three
    ways. Per finish they are deliberately decorrelated (e.g. mercury: M=bead
    cells, Cc=meniscus rims via distance transform, R=inter-bead troughs).
  * FREQUENCY: canvas 2048 = a whole car body. Macro bands at 128/256/512 plus a
    FULL-RES finest band (micro-flake / nano sparkle / 1px wireframe) added AFTER
    upscale so fine detail is real at mip-0. At least 3 distinct bands per finish.
  * x2.0-AWARE: compose passes sm (~2.0 default) straight through. We design on a
    fixed [0,255] scale and use sm ONLY as a damped contrast knob
    (contrast = 1 + (sm-1)*SM_CONTRAST_GAIN). Post-sm clip<1% at 255.
  * Channel clips: M[0,255], R[15,255], Cc[16,255]. Return (M,R,CC) float32 2D.
  * PERF: macro/mid bands at a downscaled work shape (~512), finest band at full
    res with cheap vectorized ops. 2048^2 must finish < 2.5s. No pixel loops.
  * DETERMINISM: all rng seeded from (seed, finish hash). No runtime randomness.
  * SAFETY: paint_fn untouched; compose.py never edited (Trouble Log T13). The
    v1 harness wraps each of these in try/except -> original spec on any error.
"""

import numpy as np

try:
    import cv2
    _HAVE_CV2 = True
except Exception:  # pragma: no cover - cv2 always present in app
    _HAVE_CV2 = False

# Reuse v1 perf helpers + the sm-contrast constant so behaviour matches the lab.
from engine.expansions.wild_spec_lab import (
    _wild_work_shape,
    _wild_upscale,
    SM_CONTRAST_GAIN,
)

# Structural-color angle-reveal primitives (for the angle mechanics).
from engine.paint_v2.structural_color import (
    _cx_directional_mask,
    _cx_fine_spec_pins,
    _cx_buried_reveal_gate,
)


# ═══════════════════════════════════════════════════════════════════════════
# Shared low-level helpers (cheap, vectorized, deterministic).
# These are GEOMETRY PRIMITIVES — each finish composes them differently so the
# three channels of a single finish carry different structures.
# ═══════════════════════════════════════════════════════════════════════════

_WORK_MAX = 512  # macro/mid bands built here; finest band added at full res.


def _fid_hash(finish_id):
    """Stable small int from a finish id string (determinism, no runtime rng)."""
    h = 2166136261
    for ch in finish_id:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def _contrast(sm):
    sm_f = float(sm) if sm and sm > 0 else 1.0
    c = 1.0 + (sm_f - 1.0) * SM_CONTRAST_GAIN
    return float(np.clip(c, 0.55, 1.75))


def _xy(h, w):
    """Normalized [0,1] coordinate grids (broadcasting shapes)."""
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    return x, y


def _hash01(h, w, seed, salt=0):
    """Deterministic per-pixel uniform hash in [0,1) (value-noise sine hash)."""
    x, y = _xy(h, w)
    s = float(seed + salt) * 0.00131
    n = np.sin((x * (127.1 + (salt % 13) * 3.3) +
                y * (311.7 + (salt % 7) * 5.7) + s) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _smooth_noise(h, w, cell, seed, salt=0):
    """Value noise at feature size ~`cell` px, bilinear-smoothed to (h,w).
    Cheap band generator: random grid -> resize. cell sets the frequency band."""
    gh = max(2, int(round(h / float(cell))) + 1)
    gw = max(2, int(round(w / float(cell))) + 1)
    g = _hash01(gh, gw, seed, salt)
    if _HAVE_CV2:
        return cv2.resize(g, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    yi = np.linspace(0, gh - 1, h).astype(np.int32)
    xi = np.linspace(0, gw - 1, w).astype(np.int32)
    return g[yi][:, xi].astype(np.float32)


def _fbm(h, w, cells, weights, seed, salt=0):
    """Fractional Brownian motion: weighted sum of value-noise octaves.
    `cells` = list of feature sizes in px (frequency bands). Normalized [0,1]."""
    acc = np.zeros((h, w), dtype=np.float32)
    wsum = 0.0
    for i, (c, wt) in enumerate(zip(cells, weights)):
        acc += _smooth_noise(h, w, c, seed + i * 97, salt + i * 31) * wt
        wsum += wt
    acc /= max(wsum, 1e-6)
    return np.clip(acc, 0.0, 1.0).astype(np.float32)


def _voronoi(h, w, n_sites, seed, jitter=1.0):
    """Jittered-grid Voronoi. Returns (f1, cell_id, edge_dist) all (h,w):
      f1       : normalized distance to nearest site [0,1] (0 at site center).
      cell_id  : integer-ish id of owning cell (float for vectorized use).
      edge_dist: f2 - f1, the distance-to-border proxy (small near cell edges).
    Vectorized over a small candidate neighborhood — no python pixel loops."""
    x, y = _xy(h, w)
    g = max(2, int(round(np.sqrt(max(1, n_sites)))))
    # site positions on a jittered grid
    gi = np.arange(g, dtype=np.float32)
    sx = (gi.reshape(1, g) + 0.5) / g
    sy = (gi.reshape(g, 1) + 0.5) / g
    jx = (_hash01(g, g, seed, 11) - 0.5) * (jitter / g)
    jy = (_hash01(g, g, seed, 29) - 0.5) * (jitter / g)
    sites_x = (sx + jx).astype(np.float32)  # (g,g)
    sites_y = (sy + jy).astype(np.float32)
    # which grid cell each pixel falls in
    cgx = np.clip((x * g).astype(np.int32), 0, g - 1)  # (1,w)
    cgy = np.clip((y * g).astype(np.int32), 0, g - 1)  # (h,1)
    cgx = np.broadcast_to(cgx, (h, w))
    cgy = np.broadcast_to(cgy, (h, w))
    best1 = np.full((h, w), 1e9, dtype=np.float32)
    best2 = np.full((h, w), 1e9, dtype=np.float32)
    best_id = np.zeros((h, w), dtype=np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ngx = np.clip(cgx + dx, 0, g - 1)
            ngy = np.clip(cgy + dy, 0, g - 1)
            spx = sites_x[ngy, ngx]
            spy = sites_y[ngy, ngx]
            d = (x - spx) ** 2 + (y - spy) ** 2
            sid = (ngy * g + ngx).astype(np.float32)
            closer1 = d < best1
            # demote old best1 -> best2 where we found a new best1
            best2 = np.where(closer1, best1, np.minimum(best2, d))
            best_id = np.where(closer1, sid, best_id)
            best1 = np.where(closer1, d, best1)
    f1 = np.sqrt(best1)
    f2 = np.sqrt(best2)
    edge = f2 - f1  # ~0 on cell borders, large at cell centers
    fn = f1 / max(float(f1.max()), 1e-6)
    return fn.astype(np.float32), best_id.astype(np.float32), edge.astype(np.float32)


def _ridge(field):
    """Folded ridge of a [0,1] field: bright where field crosses 0.5."""
    return (1.0 - np.abs(field * 2.0 - 1.0)).astype(np.float32)


def _sparse_dots(h, w, seed, thresh=0.992, salt=0):
    """Full-res sparse 1px sparkle grid (NEAREST in spirit — built at full res so
    specks stay crisp at mip-0). Returns binary-ish (h,w)."""
    g = _hash01(h, w, seed, salt)
    return (g > thresh).astype(np.float32)


def _norm(a):
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-6:
        return np.zeros_like(a, dtype=np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _chan(comp, lo, hi, c, gamma=1.0):
    """Map a [0,1] geometry composite to a DESIGNED 0-255 channel with damped
    sm-contrast applied around the channel midpoint — clip-safe by construction.

      comp  : [0,1] composite of this channel's own geometry (clamped here).
      lo,hi : designed value range for this channel's motif zones.
      c     : damped contrast (1 + (sm-1)*0.42); breathes the midpoint.
      gamma : optional shaping (<1 lifts darks, >1 deepens) before contrast.

    Designing on a fixed range and applying contrast INSIDE [0,1] keeps the post-
    contrast output within a known band so <1% clips at 255 (x2.0-aware). The
    finest FULL-RES band is added afterwards as a small +/- delta, then clipped.
    """
    comp = np.clip(comp, 0.0, 1.0).astype(np.float32)
    if gamma != 1.0:
        comp = np.power(comp, gamma)
    comp = np.clip((comp - 0.5) * c + 0.5, 0.0, 1.0)
    return (lo + comp * (hi - lo)).astype(np.float32)


def _clip_out(M, R, CC):
    M = np.clip(M, 0, 255).astype(np.float32)
    R = np.clip(R, 15, 255).astype(np.float32)
    CC = np.clip(CC, 16, 255).astype(np.float32)
    return M, R, CC


# ═══════════════════════════════════════════════════════════════════════════
# 1) MERCURY — liquid quicksilver. Voronoi beads (M), distance-transform
#    MENISCUS rims (Cc), inter-bead troughs (R). Arbiter: promote OXIDE-SKIN to
#    a DOMINANT CYAN, make metaball merge necks visible (flowing, not static).
# ═══════════════════════════════════════════════════════════════════════════
def spec_mercury(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. SIGNATURE: per-cell distance-transform
    # meniscus rim in Cc (no other finish derives clearcoat from a cell DT).
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    fid = _fid_hash("mercury")
    s = int(seed) ^ fid
    c = _contrast(sm)
    wh, ww = _wild_work_shape(h, w)

    # ---- macro/mid bands at work shape ----
    # Band 128: macro voronoi pools (bead-sized). sites scaled so beads ~ side-mirror.
    n_sites = max(9, int((wh * ww) / (96.0 * 96.0)))
    f1, cid, edge = _voronoi(wh, ww, n_sites, s + 101, jitter=0.95)

    # metaball merge field: adjacent beads coalesce (necks). low-freq warp of f1.
    merge = _fbm(wh, ww, [80, 40], [0.6, 0.4], s + 202)
    bead_fill = 1.0 - np.clip(f1 * (1.05 - merge * 0.45), 0.0, 1.0)  # high inside cells
    bead_fill = np.clip((bead_fill - 0.18) * 1.6, 0.0, 1.0)          # crisp interiors

    # meniscus rim = bright thin ring on cell borders (small edge_dist).
    rim = np.exp(-(edge * 9.0) ** 2)                                  # ridge on borders
    rim = np.clip(rim, 0.0, 1.0).astype(np.float32)

    # inter-bead trough network = widened voronoi edges. R structure is the GAPS,
    # but given its OWN matte roughness texture so it is not a pure (1-M) inverse.
    trough = np.clip(rim * 0.55 + (1.0 - bead_fill) * 0.55, 0.0, 1.0)
    trough = np.clip((trough - 0.40) * 1.6, 0.0, 1.0)
    trough_grain = _fbm(wh, ww, [64, 24], [0.5, 0.5], s + 350)   # matte micro-roughness

    # oxide-skin film (Arbiter: DOMINANT cyan): slow low-freq mottle on pools.
    oxide = _fbm(wh, ww, [256, 110], [0.6, 0.4], s + 303)
    oxide_mask = np.clip((oxide - 0.50) * 3.0, 0.0, 1.0) * (bead_fill > 0.30)

    # satellite micro-beads (secondary tiny beads -> Z4 yellow): sparse blobs.
    sat = _smooth_noise(wh, ww, 22, s + 404, 7)
    sat = np.clip((sat - 0.80) * 6.0, 0.0, 1.0)

    # --- assemble channels at work shape (each from DIFFERENT geometry) ---
    # M: bead interiors (high) + satellite beads, low in troughs, oxide pulls down.
    m_comp = bead_fill * 0.80 + sat * 0.78 - trough * 0.40 - oxide_mask * 0.45
    M = _chan(m_comp + 0.08, 8, 232, c)
    # R: troughs (matte/high) + oxide (mid-high, cyan) + own grain; satellites low.
    # trough_grain + oxide are independent of M's bead geometry -> keeps |MR| clear
    # of the 0.85 ceiling (R's bright structure is the GAPS, not -M).
    r_comp = trough * 0.58 + oxide_mask * 0.70 + trough_grain * 0.40 - sat * 0.30
    R = _chan(r_comp + 0.10, 22, 240, c)
    # Cc: meniscus rim ridge (the unique DT clearcoat) + oxide film (blue).
    # rim and oxide occupy DIFFERENT regions (rim=borders, oxide=pool centers) so
    # they rarely co-saturate; keep weights sub-unity for headroom + good spread.
    cc_comp = rim * 0.60 + bead_fill * 0.20 + oxide_mask * 0.62 - trough * 0.12
    CC = _chan(cc_comp + 0.05, 30, 226, c)

    M, R, CC = _wild_upscale(M, h, w), _wild_upscale(R, h, w), _wild_upscale(CC, h, w)

    # ---- FULL-RES finest band: micro-bead quicksilver glints (mip-0 sparkle) ----
    glint = _sparse_dots(h, w, s + 5050, thresh=0.9965, salt=3)
    # angle mechanic: satellite beads on fine spec pins -> flare at one pan angle.
    pins = _cx_fine_spec_pins((h, w), s + 707, 7303, density=0.0060, layers=4)
    rim_dir = _cx_directional_mask((h, w), "u", s + 11, freq=44.0)  # meniscus along u
    M = M + glint * 60.0 + pins * 20.0
    CC = CC + glint * 30.0 + (rim_dir - 0.5) * 22.0
    R = R - glint * 30.0
    return _clip_out(M, R, CC)


# ═══════════════════════════════════════════════════════════════════════════
# 2) SHOKK_MIRAGE — DESERT HEAT-MIRAGE with STRUCTURE (STRAGGLER REBUILD). The
#    prior redo was still the BLOBBIEST of all 44: a soft low-frequency multi-hue
#    haze with no motif (violated the no-blobby-fields doctrine). This rebuild
#    EARNS the shimmer with hard geometry — four named MOTIF ZONES split by a
#    crisp HORIZON SHEAR LINE:
#      ZONE-SKY    (above horizon)  -> R+Cc cyan : cool gradient + thin cirrus.
#      ZONE-GROUND (below horizon)  -> M+Cc magenta : hot refracted SLIVERS —
#                       vertically-stretched, horizontally-DISPLACED duplicate
#                       columns with SHARP step edges (the classic mirage tear).
#      ZONE-SHIMMER (high band)     -> fine VERTICAL heat-ripple columns rising off
#                       the ground (the finest, full-res band, sharp & directional).
#      ZONE-POOL   (mirror lake)    -> ALL-HIGH white : a brilliant reflective pool
#                       low on the ground with a CRISP shoreline, where the sky is
#                       mirror-inverted (the wet illusion that is never really there).
#    Geometry is DECORRELATED: M = ground-sliver bodies + pool fill, R = sky cool
#    field + sliver SHEAR seams (a DIFFERENT structure than M's sliver bodies —
#    seams are the step EDGES between slivers), Cc = horizon glow + caustic pool
#    rims + sky cirrus (glassy LINES, not M's fills). Three frequency bands: macro
#    horizon/zone split, mid sliver columns + pool, full-res vertical heat-ripple.
# ═══════════════════════════════════════════════════════════════════════════
def spec_shokk_mirage(shape, seed, sm, base_m, base_r):
    # wild-spec-v2-straggler-fix 2026-06-07: this finish was the BLOBBIEST of all
    # 44 (soft low-freq multi-hue haze, no motif — violated no-blobby-fields).
    # STRAGGLER REBUILD per directive: a DESERT HEAT-MIRAGE earned with geometry,
    # not a haze. A hard HORIZON SHEAR LINE splits the canvas; below it the GROUND
    # zone carries vertically-stretched REFRACTED SLIVERS (columns of horizontally
    # DISPLACED duplicates with SHARP step edges — the mirage tear); fine VERTICAL
    # heat-shimmer ripple columns are the full-res high band; a brilliant mirror
    # POOL zone (all-high white-read triplet) sits low with a CRISP shoreline; the
    # SKY zone reads cool R+Cc cyan vs the hot GROUND M+Cc magenta. Keeps a shimmer
    # FEEL but the structure is real (slivers, shear seams, shoreline, ripples) —
    # the channels carry DIFFERENT geometry (M=sliver bodies+pool, R=sky+shear
    # seams, Cc=horizon glow+pool rims+cirrus) so no channel is a rescale of another.
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    fid = _fid_hash("shokk_mirage")
    s = int(seed) ^ fid
    c = _contrast(sm)
    wh, ww = _wild_work_shape(h, w)
    x, y = _xy(wh, ww)

    # --- HARD HORIZON SHEAR LINE (band ~256): a single dominant horizontal divide,
    # gently meandered by a low-freq warp so it reads as a real desert horizon, not
    # a ruled line. above = sky, below = baking ground. The line itself is a thin
    # bright glow seam. ---
    horizon_warp = _fbm(wh, ww, [320, 130], [0.66, 0.34], s + 102)
    horizon_y = 0.46 + (horizon_warp - 0.5) * 0.10                 # meandered horizon
    hd = y - horizon_y                                             # <0 sky, >0 ground
    sky = (hd < 0.0).astype(np.float32)
    ground = 1.0 - sky
    horizon_glow = np.clip(1.0 - np.abs(hd) / 0.022, 0.0, 1.0)     # thin hot seam

    # --- REFRACTED SLIVERS (the GROUND motif): vertical columns whose horizontal
    # position is DISPLACED per-column by a stepped warp, with SHARP edges. We
    # quantize a low-freq column-warp into discrete column ids, then give each
    # column id a hard displacement -> adjacent columns tear/slip past each other
    # (the heat-mirage duplicate-and-shear). Columns stretch vertically (the warp
    # is near-constant in y) so they read as rising refracted bars, not blobs. ---
    col_warp = _smooth_noise(wh, ww, 120, s + 110, 3)             # smooth column drift
    col_warp_fine = _smooth_noise(wh, ww, 40, s + 111, 5)         # finer sub-columns
    # discrete sliver id: bin x (shifted by the slow warp) into ~26 hard columns.
    sliver_phase = x * 26.0 + (col_warp - 0.5) * 5.0
    sliver_id = np.floor(sliver_phase)
    sliver_frac = sliver_phase - sliver_id                        # 0..1 within column
    # per-column hard displacement (each sliver id gets its OWN offset) -> the
    # duplicated-and-slipped look. Hash the integer id for a deterministic offset.
    id_hash = np.sin((sliver_id * 12.9898 + 7.13) * 43758.5453)
    id_hash = id_hash - np.floor(id_hash)                         # 0..1 per column
    # sliver BODY: bright bar in the inner part of each column, SHARP edges via a
    # hard threshold on the within-column fraction (not a smooth ridge).
    body_lo = 0.16 + id_hash * 0.10
    body_hi = 0.74 + id_hash * 0.10
    sliver_body = ((sliver_frac > body_lo) & (sliver_frac < body_hi)).astype(np.float32)
    # SHEAR SEAM = the hard step edge between adjacent slivers (R's structure —
    # different geometry than M's bar bodies: seams are the borders, not the fills).
    seam = (((sliver_frac < body_lo) & (sliver_frac > body_lo - 0.06)) |
            ((sliver_frac > body_hi) & (sliver_frac < body_hi + 0.06))).astype(np.float32)
    # vertical intensity variation so slivers shimmer along their length (still
    # sharp-edged horizontally) — keeps them from being flat bars.
    sliver_shade = 0.55 + 0.45 * col_warp_fine
    sliver_body = sliver_body * sliver_shade * ground
    seam = seam * ground

    # --- MIRROR POOL zone (the wet illusion): a reflective lake low on the ground
    # where the slivers smear into an all-high glassy sheet. A low-freq blob field
    # thresholded -> a few coherent pool regions with a CRISP shoreline (hard edge),
    # weighted to settle near the bottom (gravity / lowest ground). ---
    pool_field = _fbm(wh, ww, [220, 90], [0.6, 0.4], s + 130)
    pool_low = np.clip((y - horizon_y) / 0.55, 0.0, 1.0)          # 0 at horizon, 1 low
    pool_raw = pool_field * (0.30 + pool_low * 1.1) * ground
    pool = (pool_raw > 0.62).astype(np.float32)                  # crisp pool body
    # CRISP shoreline = the thin border of the pool (hard band around the threshold).
    shore = ((pool_raw > 0.56) & (pool_raw < 0.68)).astype(np.float32) * ground

    # --- SKY zone (cool): a smooth cool gradient (cooler toward the top) plus thin
    # high CIRRUS streaks (horizontal wisps) for Cc — a DIFFERENT geometry than the
    # vertical ground slivers, so sky and ground never share structure. ---
    sky_grad = np.clip(1.0 - (y / np.clip(horizon_y, 0.1, 0.9)), 0.0, 1.0) * sky
    cirrus = np.abs(np.sin((y * 70.0 + _smooth_noise(wh, ww, 80, s + 140, 6) * 6.0) * np.pi))
    cirrus = np.clip((cirrus - 0.72) * 4.0, 0.0, 1.0) * sky * np.clip(1.0 - y * 1.4, 0.0, 1.0)

    # --- assemble: four motif zones, each its OWN triplet (many hues) ---
    # M (red): GROUND sliver BODIES (with Cc horizon glow -> magenta hot ground) +
    #          POOL fill (with R+Cc -> white pool). ~0 in the cool sky -> sky reads
    #          cyan. M lives in sliver-bar interiors + pool sheets.
    m_comp = (sliver_body * 0.74 + pool * 0.66 + horizon_glow * 0.34
              + shore * 0.20 - sky_grad * 0.10)
    M = _chan(m_comp + 0.06, 16, 232, c)
    # R (green): SKY cool field (with Cc -> cyan sky) + sliver SHEAR SEAMS (the step
    #            edges between slivers — DIFFERENT pixels than M's bar bodies) + pool
    #            (white). Independent seam/sky geometry, NOT 1-M.
    r_comp = (sky_grad * 0.64 + seam * 0.50 + pool * 0.58 + shore * 0.22
              - sliver_body * 0.12)
    R = _chan(r_comp + 0.10, 20, 232, c)
    # Cc (blue): HORIZON glow seam + POOL shoreline RIMS + SKY cirrus + pool fill —
    #            glassy LINE/edge geometry (horizon, shore, cirrus) plus the pool
    #            sheet, decorrelated from both M (sliver fills) and R (sky field).
    cc_comp = (horizon_glow * 0.56 + shore * 0.54 + cirrus * 0.46
               + pool * 0.50 + sky_grad * 0.18 - sliver_body * 0.10)
    CC = _chan(cc_comp + 0.05, 24, 228, c)

    M, R, CC = _wild_upscale(M, h, w), _wild_upscale(R, h, w), _wild_upscale(CC, h, w)
    pool_full = _wild_upscale(pool, h, w)
    ground_full = _wild_upscale(ground, h, w)

    # ---- FULL-RES finest band: fine VERTICAL heat-shimmer ripple columns rising
    #      off the GROUND (the high band). These are SHARP, directional vertical
    #      ripples (high x-freq, low y-freq, hash-wavered) — NOT a haze and NOT a
    #      row-grid. They live only on the ground (sky stays clean). Plus a crisp
    #      mirror-glint sparkle ON the pool surface (mip-0). ----
    fx, fy = _xy(h, w)
    ripple_jit = _hash01(h, w, s + 909, 7)
    # vertical ripple columns: high horizontal frequency, gently waver in y so the
    # columns shimmer/snake upward (rising heat), sharp via a high threshold.
    ripple = np.abs(np.sin((fx * 210.0 + np.sin(fy * 9.0 * np.pi) * 2.2
                            + ripple_jit * 4.0) * np.pi))
    ripple = np.clip((ripple - 0.74) * 5.0, 0.0, 1.0) * ground_full
    ripple = ripple * np.clip(1.0 - (fy - 0.46) * 0.6, 0.0, 1.0)  # stronger near horizon
    pool_glint = _sparse_dots(h, w, s + 5050, thresh=0.9955, salt=3) * pool_full
    # angle mechanic: the heat columns rise/lean on v (vertical pan reveals the
    # shimmer); the mirror pool flares into focus on a buried-reveal gate so the
    # "water" appears at one angle and vanishes at another (the true mirage trick).
    gate = _cx_buried_reveal_gate((h, w), s + 33, 7318, density=0.0060, layers=4)
    rise_dir = _cx_directional_mask((h, w), "v", s + 7, freq=64.0)  # columns rise on v
    M = M + ripple * 22.0 + pool_glint * 60.0 + ground_full * (rise_dir - 0.5) * 14.0
    CC = CC + pool_glint * 40.0 + gate * pool_full * 44.0 + ripple * 10.0
    R = R + ripple * 14.0 - gate * 16.0 + ground_full * (rise_dir - 0.5) * 12.0
    return _clip_out(M, R, CC)


# ═══════════════════════════════════════════════════════════════════════════
# 3) SHOKK_PHASE — PHASE BOUNDARY / state change (ROUND-2 REDO). Old phase read
#    as a zigzag/chevron PLAID (collided w/ apex + spectrum as parallel bands).
#    Now: ONE sharp diagonal INTERFACE — CRYSTALLINE SOLID (hard voronoi facets)
#    on one side, FLUID (smooth domain-warped melt) on the other, OPPOSITE
#    triplets (solid M+Cc magenta / fluid R+Cc cyan / front M+R amber mush). A
#    single dominant divide, NOT repeated parallel chevrons.
# ═══════════════════════════════════════════════════════════════════════════
def spec_shokk_phase(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. ROUND-2 REDO (judge collision): the old
    # phase read as a ZIGZAG/CHEVRON BANDED field (a 2-plane-wave plaid) and
    # clustered with shokk_apex (diagonal wave bands) + shokk_spectrum (vertical
    # rainbow drip) as "parallel wavy color bands." FIX = make it literally a
    # PHASE BOUNDARY (state change): ONE sharp diagonal INTERFACE, not repeated
    # parallel chevrons. Side A = CRYSTALLINE SOLID (hard voronoi facets, faceted);
    # side B = FLUID (smooth domain-warped melt). The two domains carry OPPOSITE
    # (M,R,Cc) triplets (solid = M+Cc magenta crystal / fluid = R+Cc cyan melt),
    # with a glowing supercooled MUSH band on the interface (M+R amber). A single
    # dominant divide -> the parallel-band silhouette it shared with apex/spectrum
    # is gone. The plane-wave sum is removed entirely.
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    fid = _fid_hash("shokk_phase")
    s = int(seed) ^ fid
    c = _contrast(sm)
    wh, ww = _wild_work_shape(h, w)
    x, y = _xy(wh, ww)

    # --- ONE sharp diagonal PHASE INTERFACE. A single divide along a dominant
    # diagonal, gently meandered by a low-freq warp so the boundary is organic
    # (a freezing front), NOT a periodic chevron set. side=0 solid, side=1 fluid. ---
    front_warp = _fbm(wh, ww, [256, 110], [0.62, 0.38], s + 140)
    # signed distance to the meandering front line (diagonal: x + y = const).
    front = (x * 0.62 + y * 0.55) + (front_warp - 0.5) * 0.34
    iso = 0.62                                                    # where the front sits
    sd = front - iso                                             # <0 solid, >0 fluid
    side = (sd > 0.0).astype(np.float32)                         # 1 = fluid domain
    interface = np.clip(1.0 - np.abs(sd) / 0.06, 0.0, 1.0)       # hot mush band on front

    # --- SOLID domain (crystalline): hard voronoi FACETS with crisp shard edges.
    # This geometry lives only where side==0; its facet plates + edges give the
    # solid a faceted-crystal read. ---
    n_sites = max(14, int((wh * ww) / (74.0 * 74.0)))
    f1, cid, edge = _voronoi(wh, ww, n_sites, s + 141, jitter=1.0)
    facet = np.clip(1.0 - f1 * 1.35, 0.0, 1.0)                   # crystal plate interiors
    facet = np.clip((facet - 0.12) * 1.5, 0.0, 1.0)
    facet_edge = np.exp(-(edge * 11.0) ** 2)                     # bright shard borders
    solid = (1.0 - side)                                         # solid mask

    # --- FLUID domain (melt): smooth domain-warped flow, NO sharp edges. Gentle
    # curl of a low-freq field -> liquid mottle. Lives only where side==1. ---
    flow = _fbm(wh, ww, [180, 70], [0.6, 0.4], s + 143)
    melt = np.clip(flow * 0.7 + _smooth_noise(wh, ww, 120, s + 144, 7) * 0.3, 0.0, 1.0)
    melt = np.clip(0.5 + (melt - 0.5) * 1.3, 0.0, 1.0)          # soft smooth flow
    fluid = side                                                 # fluid mask

    # --- assemble: OPPOSITE triplets across the divide + amber mush on the front.
    # Solid -> M+Cc (magenta crystal): facet interiors in M, shard edges in Cc.
    # Fluid -> R+Cc (cyan melt): smooth flow in R, wet sheen in Cc.
    # Interface -> M+R (amber supercooled mush) so the front itself is a third hue.
    # M (red): solid facet bodies + interface mush. ~0 in the fluid -> fluid reads
    #          cyan (R+Cc), solid reads magenta (M+Cc). Single divide drives hue.
    m_comp = (solid * facet * 0.70 + interface * 0.42 + solid * 0.06)
    M = _chan(m_comp + 0.05, 16, 224, c)
    # R (green): fluid melt flow + interface mush. Independent melt geometry (not
    #            -M): lives in the OTHER half, so M and R rarely co-occupy a pixel.
    r_comp = (fluid * melt * 0.66 + interface * 0.40 + fluid * 0.10
              - solid * facet * 0.10)
    R = _chan(r_comp + 0.10, 20, 232, c)
    # Cc (blue): BOTH domains are glassy but via DIFFERENT geometry — solid shard
    #            EDGES vs fluid sheen — so Cc carries structure decorrelated from
    #            both M (facet interiors) and R (melt bodies).
    cc_comp = (solid * facet_edge * 0.58 + fluid * (1.0 - melt) * 0.50
               + interface * 0.18)
    CC = _chan(cc_comp + 0.06, 24, 226, c)

    M, R, CC = _wild_upscale(M, h, w), _wild_upscale(R, h, w), _wild_upscale(CC, h, w)
    interface_full = _wild_upscale(interface, h, w)
    side_full = _wild_upscale(side, h, w)

    # ---- FULL-RES finest band: crisp crystal facet micro-glint on the SOLID half
    #      + smooth melt micro-ripple on the FLUID half (two DIFFERENT fine bands,
    #      one per domain, mip-0). The interface gets a hot nano-fringe. ----
    fx, fy = _xy(h, w)
    crystal_spark = _sparse_dots(h, w, s + 7171, thresh=0.9968, salt=5) * (1.0 - side_full)
    melt_ripple = np.abs(np.sin((fx * 90.0 + fy * 70.0
                                 + _hash01(h, w, s + 7, 1) * 6.28) * np.pi))
    melt_ripple = np.clip((melt_ripple - 0.7) * 3.0, 0.0, 1.0) * side_full
    front_nano = np.abs(np.sin((fx * 300.0 - fy * 280.0) * np.pi)) * interface_full
    front_nano = np.clip((front_nano - 0.5) * 2.5, 0.0, 1.0)
    # angle mechanic: solid catches light on diag_a, fluid on diag_b -> the two
    # phases flip character (and the front glints) as you pan across the boundary.
    sdir = _cx_directional_mask((h, w), "diag_a", s + 19, freq=72.0)
    fdir = _cx_directional_mask((h, w), "diag_b", s + 23, freq=72.0)
    M = M + crystal_spark * 62.0 + interface_full * 16.0 + (1.0 - side_full) * (sdir - 0.5) * 24.0
    R = R + melt_ripple * 22.0 + interface_full * 16.0 + side_full * (fdir - 0.5) * 28.0
    CC = CC + front_nano * 28.0 + crystal_spark * 26.0 + (sdir - fdir) * 16.0
    return _clip_out(M, R, CC)


# ═══════════════════════════════════════════════════════════════════════════
# 4) SHOKK_TESSERACT_V2 — 4D hypercube wireframe. Cc = crisp rectilinear EDGE
#    wireframe + inner nested cube, M = vertex nodes + inner-cube fill, R = FACE
#    interiors (complement of the wireframe). Diagonal 4D struts. Architectural.
# ═══════════════════════════════════════════════════════════════════════════
def spec_shokk_tesseract_v2(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. SIGNATURE: hard rectilinear NESTED-CUBE
    # wireframe (axis-aligned box lattice + perspective inner cube + 4D struts).
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    fid = _fid_hash("shokk_tesseract_v2")
    s = int(seed) ^ fid
    c = _contrast(sm)
    wh, ww = _wild_work_shape(h, w)
    x, y = _xy(wh, ww)

    cells = 6.0  # outer cube grid (band 128: large boxes)

    def _grid_lines(freq, thick):
        fxp = np.abs(((x * freq) % 1.0) - 0.5) * 2.0   # 0 at line, 1 mid-cell
        fyp = np.abs(((y * freq) % 1.0) - 0.5) * 2.0
        lx = np.clip(1.0 - fxp / thick, 0.0, 1.0)
        ly = np.clip(1.0 - fyp / thick, 0.0, 1.0)
        return np.maximum(lx, ly), (fxp, fyp)

    # outer cube edges
    outer_edge, (ox, oy) = _grid_lines(cells, 0.10)
    # inner nested cube: shrink toward each cell center (perspective nest).
    cell_u = (x * cells) % 1.0
    cell_v = (y * cells) % 1.0
    inner_lo, inner_hi = 0.22, 0.78
    inner_edge = (
        (np.abs(cell_u - inner_lo) < 0.03) | (np.abs(cell_u - inner_hi) < 0.03) |
        (np.abs(cell_v - inner_lo) < 0.03) | (np.abs(cell_v - inner_hi) < 0.03)
    ).astype(np.float32)
    # diagonal 4D struts connecting outer<->inner corners.
    strut_a = (np.abs(((x + y) * cells * 1.0) % 1.0 - 0.5) < 0.04).astype(np.float32)
    strut_b = (np.abs(((x - y) * cells * 1.0) % 1.0 - 0.5) < 0.04).astype(np.float32)

    wireframe = np.clip(outer_edge + inner_edge * 0.9 + strut_a * 0.5 + strut_b * 0.5, 0.0, 1.0)

    # vertices: where grid lines intersect (both ox and oy small).
    vert = ((ox < 0.10) & (oy < 0.10)).astype(np.float32)
    # inner-cube FILL (interior of nested cube) for M.
    inner_fill = ((cell_u > inner_lo) & (cell_u < inner_hi) &
                  (cell_v > inner_lo) & (cell_v < inner_hi)).astype(np.float32)

    # face interiors = complement of wireframe (R structure, divergent from Cc).
    # Per-face brightness varies (outer faces matte-bright, inner faces darker)
    # via a per-cell mottle so R is NOT a pure linear -Cc.
    face_mottle = _smooth_noise(wh, ww, 70, s + 200, 4)        # per-face shading
    face = np.clip(1.0 - wireframe, 0.0, 1.0)
    face = face * (0.55 + 0.45 * face_mottle) * (1.0 - inner_fill * 0.55)

    # --- channels diverge: Cc=edges, M=vertices+inner, R=faces ---
    m_comp = vert * 0.78 + inner_fill * 0.52 + strut_a * 0.28 + strut_b * 0.28
    M = _chan(m_comp + 0.08, 14, 232, c)
    r_comp = face * 0.56 + face_mottle * 0.48 - wireframe * 0.16
    R = _chan(r_comp + 0.08, 22, 234, c)
    cc_comp = wireframe * 0.72 + vert * 0.18 - face * 0.16
    CC = _chan(cc_comp + 0.05, 26, 228, c)

    M, R, CC = _wild_upscale(M, h, w), _wild_upscale(R, h, w), _wild_upscale(CC, h, w)

    # ---- FULL-RES: re-stamp wireframe crisp (1px) + micro-vertex sparkle ----
    fx, fy = _xy(h, w)
    fcells = cells
    fox = np.abs(((fx * fcells) % 1.0) - 0.5) * 2.0
    foy = np.abs(((fy * fcells) % 1.0) - 0.5) * 2.0
    crisp = ((fox > 0.985) | (foy > 0.985)).astype(np.float32)   # 1px-ish hard line
    spark = _sparse_dots(h, w, s + 4242, thresh=0.9975, salt=5)
    # angle mechanic: two strut sets gated by opposing diagonals -> 4D rotation.
    da = _cx_directional_mask((h, w), "diag_a", s + 21, freq=90.0)
    db = _cx_directional_mask((h, w), "diag_b", s + 22, freq=90.0)
    CC = CC + crisp * 36.0 + (da - db) * 24.0
    M = M + spark * 75.0 + (db - da) * 22.0
    R = R - crisp * 24.0
    return _clip_out(M, R, CC)


# ═══════════════════════════════════════════════════════════════════════════
# 5) SHOKK_APEX — mountain summit. A directional MOUNTAIN-RIDGE corridor system
#    converging on a bright PEAK with falling-off flanks. Three named MOTIF ZONES,
#    each a DIFFERENT (M,R,Cc) triplet so the composite shows several hues:
#      ZONE-PEAK  (summit cap)      -> M+Cc magenta : faceted snow plates + halo.
#      ZONE-RIDGE (edge-light crest)-> R+Cc cyan    : hard ridge corridors w/ cores
#                                                      + protective halos + edge-light.
#      ZONE-FLANK (sloped scree)    -> M+R  yellow  : anisotropic talus grain.
#    Geometry is genuinely DECORRELATED: M = faceted aspect plates (ridge-cell
#    interiors), R = the inter-ridge VALLEY/scree network (NOT 1-M of the same
#    field — it is a separate valley distance field + grain), Cc = the thin
#    edge-light RIDGE CRESTS + peak halo (a folded-ridge of a warped height field,
#    so its bright pixels lie on the ridge LINES, not on M's plate INTERIORS).
#    Three frequency bands: macro ridge corridors (256), mid facet plates (128),
#    full-res micro-facet sparkle (mip-0). Pre-rejected v1 was a soft radial blob;
#    this REDO replaces it with intentional ridge/peak/flank structure.
# ═══════════════════════════════════════════════════════════════════════════
def spec_shokk_apex(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. REDO of the rejected soft-blob apex.
    # SIGNATURE: directional ridge-corridor MOUNTAIN with a peak-cap zone,
    # ridge-crest edge-light, and flank scree — M=aspect facet plates,
    # R=valley/scree network, Cc=ridge crest-lines + peak halo (all decorrelated).
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    fid = _fid_hash("shokk_apex")
    s = int(seed) ^ fid
    c = _contrast(sm)
    wh, ww = _wild_work_shape(h, w)
    x, y = _xy(wh, ww)

    # --- directional mountain HEIGHT field: ridges run along a dominant diagonal
    # so the corridors are clearly directional (the "apex/summit" reads as a
    # mountain mass, not a radial bullseye). Anisotropic: stretched on the ridge
    # axis (warp the sampling so noise features are long ridges, not blobs). ---
    ridge_axis = (x * 0.80 + y * 0.55)                       # dominant ridge direction
    cross_axis = (x * 0.55 - y * 0.80)                       # across-ridge
    # warp the height field so ridges are long corridors (low freq along, high across)
    warp = _fbm(wh, ww, [256, 110], [0.6, 0.4], s + 90)      # macro terrain (band 256)
    height = (np.sin((cross_axis * 6.0 + warp * 2.2) * np.pi) * 0.5 + 0.5)
    height = np.clip(height * 0.62 + warp * 0.38, 0.0, 1.0)

    # ridge CREST lines = folded ridge of the height field (bright on the lines
    # where height crosses its mid-level -> thin corridors, NOT broad areas).
    crest = _ridge(height)                                   # 1 on ridge spines
    crest = np.clip((crest - 0.55) * 2.6, 0.0, 1.0)          # crisp thin corridors
    # protective HALO around each crest core (edge-light corridor): dilate-ish via
    # a softer threshold band that surrounds the hard core.
    crest_halo = np.clip((_ridge(height) - 0.20) * 1.4, 0.0, 1.0) - crest
    crest_halo = np.clip(crest_halo, 0.0, 1.0)

    # PEAK zone: a single off-center summit mass where the terrain height is
    # highest AND near the apex point -> the hot cap.
    ax, ay = 0.40, 0.34
    pdist = np.sqrt((x - ax) ** 2 + (y - ay) ** 2)
    peak_cap = np.clip(1.0 - pdist / 0.42, 0.0, 1.0) * np.clip((height - 0.45) * 2.2, 0.0, 1.0)
    peak_cap = np.clip(peak_cap * 1.5, 0.0, 1.0)             # bright summit cap
    peak_halo = np.clip(np.exp(-(pdist * 2.0) ** 2), 0.0, 1.0)  # smooth summit sheen

    # ASPECT facet plates (M zone): which way a slope faces. Quantize the gradient
    # direction of the height field into faceted plates -> blocky aspect cells that
    # sit in the ridge-cell INTERIORS (decorrelated from the crest LINES).
    gy, gx = np.gradient(height.astype(np.float32))
    aspect = np.arctan2(gy, gx + 1e-6)                       # slope-facing direction
    facet = np.abs(np.sin(aspect * 3.0))                     # faceted aspect bands
    facet = facet * (1.0 - crest)                            # plates live between crests
    facet_mottle = _smooth_noise(wh, ww, 128, s + 92, 4)     # band 128: plate shading
    facet = np.clip(facet * (0.5 + 0.5 * facet_mottle), 0.0, 1.0)

    # VALLEY / scree network (R zone): the low ground between ridges, with its OWN
    # anisotropic talus grain (NOT a pure inverse of M). Valleys = low height that
    # is also off the crest, given a directional scree micro-texture.
    valley = np.clip((0.55 - height) * 2.2, 0.0, 1.0) * (1.0 - crest)
    scree = np.abs(np.sin((ridge_axis * 60.0 + warp * 3.0) * np.pi))  # talus streaks
    scree = np.clip(scree, 0.0, 1.0)
    valley = np.clip(valley * (0.45 + 0.55 * scree), 0.0, 1.0)

    # --- assemble: three motif zones, each its OWN triplet (many hues) ---
    # M (red): aspect facet PLATES + peak cap + flank scree (M+R yellow on flanks,
    #          M+Cc magenta on peak).  Low on bare ridge lines & deep valley.
    m_comp = (facet * 0.50 + peak_cap * 0.62 + scree * valley * 0.40
              - crest * 0.18)
    M = _chan(m_comp + 0.10, 12, 234, c)
    # R (green): VALLEY/scree network + flank grain (R+Cc cyan in shaded valleys,
    #            M+R yellow on lit flanks). Independent valley geometry.
    r_comp = (valley * 0.58 + scree * 0.30 + facet_mottle * 0.18
              - peak_cap * 0.20 - crest * 0.10)
    R = _chan(r_comp + 0.14, 20, 232, c)
    # Cc (blue): ridge CREST edge-light corridors + halos + peak sheen (R+Cc cyan
    #            on shaded crests, M+Cc magenta at the peak). Crest-LINE geometry.
    cc_comp = (crest * 0.58 + crest_halo * 0.26 + peak_halo * 0.26
               - valley * 0.10)
    CC = _chan(cc_comp + 0.04, 24, 222, c)

    M, R, CC = _wild_upscale(M, h, w), _wild_upscale(R, h, w), _wild_upscale(CC, h, w)
    peak_full = _wild_upscale(peak_cap, h, w)
    crest_full = _wild_upscale(crest, h, w)

    # ---- FULL-RES finest band: micro-facet snow sparkle (mip-0) on plates +
    #      crisp 1px ridge re-stamp so crest corridors stay sharp after upscale ----
    fx, fy = _xy(h, w)
    fheight = (np.sin((fx * 0.55 - fy * 0.80) * 6.0 * np.pi
                      + _hash01(h, w, s + 90, 1) * 4.0) * 0.5 + 0.5)
    fcrest = _ridge(fheight)
    crisp_crest = (fcrest > 0.985).astype(np.float32)        # 1px-ish hard crest line
    micro_facet = _sparse_dots(h, w, s + 4848, thresh=0.9968, salt=5)  # snow sparkle
    # angle mechanic: ridge crests catch light along the ridge axis; flanks flip on
    # the opposing diagonal so the surface reads differently as you pan.
    crest_dir = _cx_directional_mask((h, w), "diag_a", s + 31, freq=88.0)
    flank_dir = _cx_directional_mask((h, w), "diag_b", s + 33, freq=88.0)
    M = M + micro_facet * 70.0 + peak_full * 26.0 + (flank_dir - 0.5) * 22.0
    CC = CC + crisp_crest * 30.0 + crest_full * (crest_dir * 26.0) + peak_full * 16.0
    R = R + (flank_dir - 0.5) * 18.0 - crisp_crest * 22.0
    return _clip_out(M, R, CC)


# ═══════════════════════════════════════════════════════════════════════════
# 6) SHOKK_DUAL — two opposed generators welded at an interlocking puzzle seam.
#    Domain A = curl-flow molten cells (warm). Domain B = voronoi facets (cold).
#    M high in A, Cc high in B (mirror anti-correlated). R = the SEAM + bleed.
#    Arbiter: interlocking puzzle-teeth seam HERO, halves SWAP on pan (A=u, B=v).
# ═══════════════════════════════════════════════════════════════════════════
def spec_shokk_dual(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. SIGNATURE: ONE canvas split by an
    # interlocking turbulent seam running TWO different generators (curl-flow vs
    # voronoi-facets), M and Cc mirror-anti-correlated across the divide.
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    fid = _fid_hash("shokk_dual")
    s = int(seed) ^ fid
    c = _contrast(sm)
    wh, ww = _wild_work_shape(h, w)
    x, y = _xy(wh, ww)

    # interlocking puzzle-teeth seam: vertical divide perturbed by high-freq noise.
    seam_x = 0.5 + (_smooth_noise(wh, ww, 18, s + 150, 2) - 0.5) * 0.30  # teeth wobble
    seam_x = seam_x + np.sin(y * 14.0 * np.pi) * 0.05                     # interlock comb
    side = (x > seam_x).astype(np.float32)                               # 0=A(left),1=B(right)
    seam_dist = np.abs(x - seam_x)
    seam = np.clip(1.0 - seam_dist / 0.035, 0.0, 1.0)                     # bright contested edge

    # Domain A: curl-flow organic molten cells (warm blobs).
    flow = _fbm(wh, ww, [110, 50], [0.6, 0.4], s + 160)
    curl = np.abs(np.sin((flow * 8.0 + y * 3.0) * np.pi))
    domA = np.clip(curl * 0.6 + flow * 0.4, 0.0, 1.0)

    # Domain B: crystalline voronoi facets (hard shards).
    f1b, cidb, edgeb = _voronoi(wh, ww, max(16, int((wh * ww) / (70.0 * 70.0))), s + 170, jitter=1.0)
    facet = np.clip(1.0 - f1b * 1.3, 0.0, 1.0)
    facet_edge = np.exp(-(edgeb * 11.0) ** 2)

    # bleed: A tendrils into B and B shards into A, near the seam.
    bleed_band = np.clip(1.0 - seam_dist / 0.16, 0.0, 1.0)
    a_bleed = bleed_band * side * (domA > 0.55)            # organic in B territory
    b_bleed = bleed_band * (1.0 - side) * (facet > 0.55)   # crystal in A territory

    # --- M high in A, Cc high in B (mirror), R = seam + interface ---
    m_comp = (1.0 - side) * (domA * 0.80) + a_bleed * 0.70 + seam * 0.30 + side * 0.10
    M = _chan(m_comp, 16, 244, c)
    r_comp = (seam * 0.66 + (1.0 - side) * (domA * 0.28) +
              side * ((1.0 - facet) * 0.55) + b_bleed * 0.55)
    R = _chan(r_comp + 0.06, 22, 240, c)
    cc_comp = side * (facet * 0.62 + facet_edge * 0.22) + a_bleed * 0.45 + seam * 0.30
    CC = _chan(cc_comp, 26, 228, c)

    M, R, CC = _wild_upscale(M, h, w), _wild_upscale(R, h, w), _wild_upscale(CC, h, w)

    # ---- FULL-RES: seam sparkle + per-domain micro-flake (DIFFERENT each half) ----
    fx, fy = _xy(h, w)
    fseam = 0.5 + (_smooth_noise(h, w, 18, s + 150, 2) - 0.5) * 0.30 + np.sin(fy * 14.0 * np.pi) * 0.05
    fside = (fx > fseam).astype(np.float32)
    seam_glint = (np.abs(fx - fseam) < 0.004).astype(np.float32) * _sparse_dots(h, w, s + 3131, 0.85, 8)
    flakeA = _sparse_dots(h, w, s + 3232, 0.9955, 9) * (1.0 - fside)   # left flake
    facetB = np.abs(np.sin((fx * 200.0 + fy * 160.0) * np.pi)) * fside  # right faceting
    facetB = np.clip((facetB - 0.7) * 3.0, 0.0, 1.0)
    # angle mechanic: A lit on u, B lit on v -> personality flip on pan.
    du = _cx_directional_mask((h, w), "u", s + 41, freq=60.0)
    dv = _cx_directional_mask((h, w), "v", s + 42, freq=60.0)
    M = M + flakeA * 95.0 + seam_glint * 80.0 + (1.0 - fside) * (du - 0.5) * 46.0
    CC = CC + facetB * 40.0 + seam_glint * 50.0 + fside * (dv - 0.5) * 44.0
    R = R + seam_glint * 30.0
    return _clip_out(M, R, CC)


# ═══════════════════════════════════════════════════════════════════════════
# 7) SOLAR_PANEL — literal photovoltaic array. Cc = cell-silicon fill (AR glass),
#    M = busbar strips + finger combs (conductor grid), R = AR-pyramid micro-facet
#    + inter-cell gaps. Hard rectilinear PV geometry. Recognizable as a panel.
# ═══════════════════════════════════════════════════════════════════════════
def spec_solar_panel(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. SIGNATURE: real PV-cell geometry —
    # three-busbar + finger-comb conductors (M) over AR-pyramid relief (R).
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    fid = _fid_hash("solar_panel")
    s = int(seed) ^ fid
    c = _contrast(sm)
    wh, ww = _wild_work_shape(h, w)
    x, y = _xy(wh, ww)

    cells = 6.0  # PV cell grid (each cell = large square, band 128)
    cu = (x * cells) % 1.0
    cv = (y * cells) % 1.0

    # cell-gap grid (bright backing between cells) + chamfered monocrystalline corners.
    gap = ((cu < 0.04) | (cu > 0.96) | (cv < 0.04) | (cv > 0.96)).astype(np.float32)
    corner = (((cu < 0.10) & (cv < 0.10)) | ((cu > 0.90) & (cv < 0.10)) |
              ((cu < 0.10) & (cv > 0.90)) | ((cu > 0.90) & (cv > 0.90))).astype(np.float32)
    cell_in = (1.0 - gap) * (1.0 - corner)                  # silicon body area

    # silicon fill (Cc): high inside each cell (glassy AR coating), drops at edges.
    edge_fade = np.clip(np.minimum(np.minimum(cu, 1 - cu), np.minimum(cv, 1 - cv)) * 12.0, 0.0, 1.0)
    silicon = cell_in * (0.55 + 0.45 * edge_fade)

    # conductors (M): 3 vertical busbars per cell + horizontal finger combs.
    busbar = (((np.abs(cu - 0.25) < 0.018) | (np.abs(cu - 0.5) < 0.018) |
               (np.abs(cu - 0.75) < 0.018))).astype(np.float32) * cell_in
    fingers = (np.abs(((y * cells * 14.0) % 1.0) - 0.5) > 0.46).astype(np.float32) * cell_in
    conductor = np.clip(busbar * 1.0 + fingers * 0.7, 0.0, 1.0)

    # AR-glint micro-facet (R): angular anti-reflective pyramid texture + gaps.
    ar = np.abs(np.sin((x * 90.0 + y * 90.0) * np.pi)) * np.abs(np.sin((x - y) * 70.0 * np.pi))
    ar = np.clip(ar, 0.0, 1.0) * cell_in

    # --- channels diverge: Cc=cells, M=busbars+fingers, R=AR-facet+gaps ---
    # wild-spec-v2-straggler-fix 2026-06-07: busbar/finger M plus the full-res
    # finger_crisp pin pushed raw M clip to ~1.43% (>1%); trimmed designed M ceiling
    # 246->238 (and finger_crisp pin below) so conductors read bright but <1% clip.
    m_comp = conductor * 0.90 + corner * 0.30
    M = _chan(m_comp + 0.10, 18, 238, c)
    r_comp = ar * 0.55 + gap * 0.55 - silicon * 0.18 - conductor * 0.12
    R = _chan(r_comp + 0.22, 24, 232, c)
    cc_comp = silicon * 0.74 + conductor * 0.30 + gap * 0.24 - ar * 0.10
    CC = _chan(cc_comp, 26, 228, c)

    M, R, CC = _wild_upscale(M, h, w), _wild_upscale(R, h, w), _wild_upscale(CC, h, w)

    # ---- FULL-RES: AR pyramid micro-relief + 1px finger lines (NEAREST-crisp) ----
    fx, fy = _xy(h, w)
    fcu = (fx * cells) % 1.0
    fcell = ((fcu > 0.04) & (fcu < 0.96))
    finger_crisp = (np.abs(((fy * cells * 14.0) % 1.0) - 0.5) > 0.49).astype(np.float32) * fcell
    pyr = np.abs(np.sin((fx * 260.0) * np.pi) * np.sin((fy * 260.0) * np.pi))
    pyr = np.clip((pyr - 0.6) * 3.0, 0.0, 1.0)
    # angle mechanic: AR silicon glints in angular sheets per cell; wiring constant.
    ar_dir = _cx_directional_mask((h, w), "u", s + 51, freq=72.0)
    # straggler-fix 2026-06-07: the crisp finger lines fall ON the already-bright
    # busbar/finger conductor band (designed ~238), so an ADDITIVE pin re-pinned M
    # to 255 (~1.4% clip). Apply the finger highlight as a clamped LIFT toward a 250
    # ceiling (np.maximum) instead of stacking — fingers still read as the brightest
    # crisp lines but can never exceed 250, so raw M clip at 255 stays well under 1%.
    M = np.maximum(M, finger_crisp * 250.0)
    R = R + pyr * 24.0
    CC = CC + (ar_dir - 0.5) * 40.0 * fcell + pyr * 14.0
    return _clip_out(M, R, CC)


# ═══════════════════════════════════════════════════════════════════════════
# 8) SHOKK_VENOM — toxic corrosive biome. Three TOXIC MOTIF ZONES partition the
#    surface (a low-freq zone-map assigns each region one identity), each a
#    DIFFERENT (M,R,Cc) triplet so the composite is MULTI-HUE (not one green plane):
#      GLAND SACS    -> M+Cc magenta : turgid venom blisters (voronoi cell bodies
#                       with bright meniscus rims), the wet glossy reservoirs.
#      VENOM CHANNELS-> M+R  amber   : gravity-fed DRIP/CORROSION corridors that
#                       eat downward across zones (the dripping toxic streaks).
#      ACID SKIN     -> R+Cc cyan    : sickly pitted/corroded matte hide between
#                       sacs (pock-marked roughness, the eaten-away surface).
#    Channel geometry is genuinely DECORRELATED: M = sac BODIES + drip cores,
#    R = corroded SKIN pits + drip channels, Cc = sac RIMS (distance-transform-ish
#    meniscus) + drip wet sheen. The three live in different places per the
#    zone-map, so no channel is a rescale of another and the field is many-hued.
#    Three frequency bands: macro zone-map (256) + sac voronoi (128), mid pitting
#    (64), full-res micro venom-droplet beads (mip-0). REDO of the rejected
#    "single green field + dot grid" venom.
# ═══════════════════════════════════════════════════════════════════════════
def spec_shokk_venom(shape, seed, sm, base_m, base_r):
    # wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity),
    # demands many-hue triplet zones. REDO of the rejected green-plane-plus-dots
    # venom. SIGNATURE: a low-freq zone-map partitions the surface into three
    # TOXIC identities (gland sacs M+Cc / venom drip channels M+R / acid skin
    # R+Cc), each with its own geometry -> multi-hue corrosive biome.
    h, w = (shape[:2] if len(shape) > 2 else shape)
    h, w = int(h), int(w)
    fid = _fid_hash("shokk_venom")
    s = int(seed) ^ fid
    c = _contrast(sm)
    wh, ww = _wild_work_shape(h, w)
    x, y = _xy(wh, ww)

    # --- ZONE MAP (band 256): three biome territories. Two soft thresholds on a
    # low-freq field carve sac / channel / skin regions so each hue lives in its
    # OWN place (this is what makes the composite multi-hue, not one field). ---
    biome = _fbm(wh, ww, [256, 120], [0.62, 0.38], s + 170)
    z_sac = np.clip((biome - 0.60) * 4.0, 0.0, 1.0)          # high ground -> sacs
    z_skin = np.clip((0.42 - biome) * 4.0, 0.0, 1.0)         # low ground -> acid skin
    # channels run in the mid band AND wherever drips carve (added below).

    # --- GLAND SACS (voronoi cell bodies + meniscus rims), gated to z_sac ---
    n_sites = max(12, int((wh * ww) / (78.0 * 78.0)))        # sac-sized cells
    f1, cid, edge = _voronoi(wh, ww, n_sites, s + 171, jitter=0.95)
    sac_body = np.clip(1.0 - f1 * 1.35, 0.0, 1.0)            # turgid blister interiors
    sac_body = np.clip((sac_body - 0.15) * 1.5, 0.0, 1.0)
    sac_rim = np.exp(-(edge * 10.0) ** 2)                    # bright meniscus ring
    sac_rim = np.clip(sac_rim, 0.0, 1.0)
    sac_body = sac_body * z_sac
    sac_rim = sac_rim * z_sac

    # --- ACID SKIN: pitted/corroded matte hide, gated to z_skin. Pitting = sharp
    # sparse depressions (its OWN geometry: a thresholded mid-freq field), so R is
    # not an inverse of M. ---
    pit_field = _fbm(wh, ww, [64, 26], [0.5, 0.5], s + 174)  # band 64 corrosion
    pits = np.clip((pit_field - 0.52) * 3.0, 0.0, 1.0)       # corroded pock-marks
    skin = (0.40 + 0.60 * pits) * z_skin                     # rough eaten surface
    skin_sheen = _smooth_noise(wh, ww, 90, s + 176, 4)       # uneven sickly shading

    # --- VENOM DRIP / CORROSION CHANNELS: gravity-fed vertical corridors that
    # cross ALL zones (independent of sac/skin geometry). Downward-brightening
    # wavering streaks -> the "dripping toxic" read. These define a THIRD region. ---
    drip_warp = _smooth_noise(wh, ww, 46, s + 178, 3)
    drip = np.abs(np.sin((x * 20.0 + drip_warp * 2.2) * np.pi))
    drip = np.clip((drip - 0.62) * 5.0, 0.0, 1.0)
    drip = drip * np.clip(0.30 + y * 0.95, 0.0, 1.0)         # gravity: heavier low
    drip_core = np.clip((drip - 0.4) * 2.0, 0.0, 1.0)        # the wet streak core
    # corrosion etch flanking each drip (eaten edges) -> ties drips to skin pitting.
    drip_etch = np.clip(drip * 0.7 + pits * 0.3, 0.0, 1.0)

    # --- assemble: each channel a DIFFERENT combination so the three zones read
    # as three different hues (sacs magenta=M+Cc, channels amber=M+R, skin cyan=R+Cc) ---
    # M (red): sac BODIES (with Cc rim -> magenta sacs) + drip CORES (with R ->
    #          amber channels). Low on bare acid skin (lets skin read cyan). The
    #          drip CORE (not the wet rim/sheen) is M's slice of the channel so M
    #          and Cc don't both ride the same drip term.
    m_comp = (sac_body * 0.76 + drip_core * 0.46 + sac_rim * 0.12
              - skin * 0.18)
    M = _chan(m_comp + 0.06, 14, 234, c)
    # R (green): acid SKIN pitting (with Cc -> cyan) + drip CHANNELS (with M ->
    #            amber) + drip etch. Independent pit/etch geometry, NOT 1-M.
    r_comp = (skin * 0.62 + drip_etch * 0.34 + skin_sheen * z_skin * 0.18
              - sac_body * 0.14)
    R = _chan(r_comp + 0.10, 20, 234, c)
    # Cc (blue): sac RIMS / wet meniscus (with M -> magenta) + acid-skin glassy
    #            sheen (with R -> cyan). Rim-LINE & skin geometry — DELIBERATELY
    #            NOT fed by the drip core (that is M+R's amber), so Cc lives in
    #            different pixels than M (rims/skin, not sac interiors) -> low corr.
    cc_comp = (sac_rim * 0.74 + skin * skin_sheen * 0.58 + skin * 0.18
               - sac_body * 0.22 - drip_core * 0.12)
    CC = _chan(cc_comp + 0.04, 22, 230, c)

    M, R, CC = _wild_upscale(M, h, w), _wild_upscale(R, h, w), _wild_upscale(CC, h, w)
    drip_full = _wild_upscale(drip_core, h, w)

    # ---- FULL-RES finest band: venom micro-droplet beads (sparse crisp) on the
    #      drips + keratin micro-grain on skin (mip-0 sparkle over a MULTI-HUE base) ----
    beads = _sparse_dots(h, w, s + 6161, thresh=0.9962, salt=11)
    keratin = (_hash01(h, w, s + 6262, 13) - 0.5)
    # angle mechanic: drip corridors flash downward on v; sac rims twinkle on pins.
    vdir = _cx_directional_mask((h, w), "v", s + 61, freq=58.0)
    pins = _cx_fine_spec_pins((h, w), s + 62, 7308, density=0.0055, layers=4)
    # M takes the drip-axis flash (amber channels); Cc takes the rim pins (magenta
    # sacs) -> the full-res sparkle ALSO lands in different channels' pixels.
    M = M + beads * 78.0 + drip_full * (vdir * 30.0) + keratin * 8.0
    CC = CC + beads * 48.0 + pins * 40.0
    R = R + keratin * 14.0 - beads * 18.0
    return _clip_out(M, R, CC)


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTS — finish_id -> dedicated spec function.
# ═══════════════════════════════════════════════════════════════════════════
EXPORTS = {
    "mercury": spec_mercury,
    "shokk_mirage": spec_shokk_mirage,
    "shokk_phase": spec_shokk_phase,
    "shokk_tesseract_v2": spec_shokk_tesseract_v2,
    "shokk_apex": spec_shokk_apex,
    "shokk_dual": spec_shokk_dual,
    "solar_panel": spec_solar_panel,
    "shokk_venom": spec_shokk_venom,
}
