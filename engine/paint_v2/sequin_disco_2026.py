# -*- coding: utf-8 -*-
"""
engine/paint_v2/sequin_disco_2026.py — ★ OPTIC LAB : SEQUIN / DISCO (rebuilt 2026-06-15)

10 BESPOKE faceted-flash finishes. The owner's complaint about the old version was
correct and damning: it was ONE _sequins/_sequin_spec factory + a _RECIPES color table.
Every finish shared the identical voronoi-dome design and the IDENTICAL spec (M on the
dome, R on grain, CC flat 16) — "recolored bullshit, same spec maps, only red+green."

This rebuild TEARS OUT the factory. Every finish now has its OWN design algorithm AND
its OWN multi-hue spec:

  flip-sequins        sequin_silver        — square flip-disc lattice, each disc a flat
                                              tile that flips bright/dark; spec hue per disc.
  disco-ball facets   sequin_gold          — geodesic mirror-facet voronoi on a sphere-ish
                                              UV warp; per-facet randomized hue spec.
  chunky glitter      sequin_rose          — large hexagonal chunky glitter flakes, sparse,
                                              each flake its own hue spark in the spec.
  mermaid scale       sequin_emerald       — overlapping fish-scale arcs; per-scale hue,
                                              R rides the arc rim, M the scale body.
  micro-shimmer       sequin_copper        — dense sub-pixel micro-shimmer dust; hue noise
                                              field gives a true rainbow micro-spec.
  ice / shattered     sequin_ice           — shattered-crystal crackle (cell + crack lines);
                                              cracks vs facets carry different channels.
  large paillettes    sequin_rainbow       — big round overlapping paillette sequins; each
                                              paillette a full random hue (rainbow spec).
  holographic glitter sequin_holographic   — thin-film interference glitter (true holo); the
                                              interference order drives M/R/CC into a rainbow.
  mirror mosaic       disco_black_diamond  — irregular angular mirror-mosaic tiles + grout;
                                              per-tile hue, grout = matte channel.
  carnival sequins    sequin_mardi_gras    — diagonal sequin RIBBONS (rows of discs) in
                                              shifting carnival hues; per-row + per-disc hue.

THE MULTI-HUE SPEC TRICK (Viva-Mexico style): every spec recomputes the SAME geometric
fields the paint uses (same seed, shared helpers) and assigns each feature a HUE, then maps
hue -> a VARIED (M, R, CC) triplet via phase-offset cosine lobes. Different hues land in
different channel-dominance classes, so the combined spec (R=M,G=R,B=CC) shows blues,
purples, oranges, yellows, teals — NOT two colors. Channels ride DIFFERENT geometry
(M=facet body, R=rim/grain, CC=hue-cool) so |corr| stays well under 0.85.

Contracts: paint_x(paint,shape,mask,seed,pm,bb)->HxWx3 in [0,1].
           spec_x(shape,seed,sm,base_m,base_r)->(M,R,CC) float32 0..255, R floor 15, CC 16=wet.
All paint+spec render < 3s @ 2048 (work-res caps + cKDTree + windowed splats).
"""
import numpy as np

from engine.core import multi_scale_noise, get_mgrid, _resize_array, hsv_to_rgb_vec
from engine.color_science import interference_palette

_SQ_CACHE = {}


def _cache(key, fn):
    v = _SQ_CACHE.get(key)
    if v is None:
        if len(_SQ_CACHE) > 160:
            _SQ_CACHE.clear()
        v = fn()
        _SQ_CACHE[key] = v
    return v


def _rgb3(paint):
    if paint.ndim == 3 and paint.shape[2] > 3:
        return paint[:, :, :3].copy()
    return paint


def _compose(col, paint, mask):
    col = np.clip(col, 0.0, 1.0).astype(np.float32)
    m = mask[:, :, None]
    return col * m + _rgb3(paint) * (1.0 - m)


def _work_dims(h, w, work):
    """Aspect-preserving work-res dims, never upsampling past native."""
    if h >= w:
        sh = min(h, work)
        sw = max(64, int(round(sh * w / h)))
    else:
        sw = min(w, work)
        sh = max(64, int(round(sw * h / w)))
    return min(sh, h), min(sw, w)


# ---------------------------------------------------------------------------
# THE multi-hue spec engine.
#   hue_to_triplet(hue, val) maps each feature's own hue (0..1) into a (M,R,CC)
#   triplet using THREE cosine lobes peaked at different hues, so that:
#     red/orange  -> high M, mid R, low  CC   (warm metal flash)
#     yellow      -> high M, high R, low  CC
#     green/teal  -> mid  M, high R, high CC
#     blue        -> low  M, mid  R, high CC   (cool clearcoat)
#     purple/mag  -> high M, low  R, high CC
#   This is the same "paint chroma -> varied gloss triplet" idea as Viva Mexico,
#   but driven per-feature so the combined spec literally renders a rainbow.
# ---------------------------------------------------------------------------
def _hue_to_triplet(hue, val):
    """hue,val: HxW float32 in [0,1]. Returns (mF, rF, ccF) each in [0,1].

    Three cosine lobes peaked 120 deg apart on the hue circle so each spec
    channel dominates a DIFFERENT third of the hues -> the combined map spans
    the whole rainbow and the channels decorrelate by construction:
      hue ~0.00 (red)    -> M high
      hue ~0.33 (green)  -> R high
      hue ~0.67 (blue)   -> CC high
    `val` only nudges the lobe SHARPNESS, it does not scale all channels (that
    would re-correlate them); a separate gentle global lift keeps darks alive."""
    a = hue.astype(np.float32) * (2.0 * np.pi)
    mL = 0.5 + 0.5 * np.cos(a - 0.00)            # peak red/magenta
    rL = 0.5 + 0.5 * np.cos(a - 2.0944)          # peak +120 deg (green/yellow)
    ccL = 0.5 + 0.5 * np.cos(a - 4.1888)         # peak +240 deg (blue/cyan)
    v = np.clip(val, 0.0, 1.0).astype(np.float32)
    # sharpen each lobe a touch (gamma) so dominance classes are crisp, then
    # apply a SMALL, channel-specific val tilt (different exponents) to avoid
    # a shared multiplicative factor across channels.
    mF = np.clip((0.10 + 0.90 * (mL ** 1.4)) * (0.70 + 0.30 * v), 0, 1)
    rF = np.clip((0.12 + 0.88 * (rL ** 1.4)) * (0.85 + 0.15 * (1.0 - v)), 0, 1)
    ccF = np.clip((0.08 + 0.92 * (ccL ** 1.4)) * (0.78 + 0.22 * v), 0, 1)
    return mF.astype(np.float32), rF.astype(np.float32), ccF.astype(np.float32)


def _rough_field(shape, seed):
    """An INDEPENDENT roughness geometry (its own seed/scale) so R crosses its
    120 threshold on different pixels than M/CC -> decorrelated channels and a
    rich spread of hue classes in the combined spec."""
    h, w = shape[:2]
    key = ("rough", h, w, int(seed))

    def build():
        sh, sw = _work_dims(h, w, 700)
        f = multi_scale_noise((sh, sw), [9, 22, 55], [0.5, 0.32, 0.18], (int(seed) ^ 0x5A17))
        f = (np.asarray(f, np.float32) * 0.5 + 0.5).astype(np.float32)
        if (sh, sw) != (h, w):
            f = _resize_array(f, h, w)
        return np.clip(f, 0, 1).astype(np.float32)

    return _cache(key, build)


def _pack_spec(mF, rF, ccF, sm, body, base_m, base_r, seed=0,
               m_lo=55.0, m_hi=235.0, cc_lo=16.0, cc_hi=215.0):
    """Combine hue-triplet fields (0..1) into final M/R/CC (0..255).

    The three channels ride THREE DIFFERENT geometries so the combined spec (R=M,
    G=R, B=CC) spreads across many hue classes and the channels decorrelate:
      M  = the WARM hue lobe (mF) gated by feature `body` -> warm features blaze.
      R  = an INDEPENDENT multi-scale roughness field (its own seed), pushed DOWN
           on bright features and UP in the dull gaps. R's 120-crossings live on
           different pixels than M's -> |corr(M,R)| stays low even though both
           relate to the same chips.
      CC = the COOL hue lobe (ccF) gated by body -> cool features pool clearcoat.
    Because warm features peak M (not CC), cool features peak CC (not M), and R is
    its own field, the map shows red/orange/yellow/green/teal/blue/purple."""
    sm = float(sm)
    bm = float(np.clip(base_m, 0, 255)) if base_m is not None else 40.0
    b = np.clip(body, 0.0, 1.0).astype(np.float32)
    h, w = b.shape
    rough = _rough_field((h, w), seed)
    # A SECOND independent low-frequency field PARTITIONS the dull GAPS into
    # warm / neutral / cool zones, so the resin between sparse sequins is not one
    # monolithic R-high class. ~1/3 of the gap goes M-high (warm patch), ~1/3
    # CC-high (cool patch), ~1/3 plain rough. Coverage-sparse finishes therefore
    # still read multi-hue across the whole panel, not just on the chips.
    gap_tone = _rough_field((h, w), seed ^ 0x2B9)
    g = 1.0 - b
    gap_warm = (gap_tone > 0.56).astype(np.float32)      # upper ~third -> warm gap
    gap_cool = (gap_tone < 0.44).astype(np.float32)      # lower ~third -> cool gap
    # M: warm gap patches glow + warm features blaze (cool hues stay dark in M).
    M = (0.22 * bm + 150.0 * gap_warm) * g + (m_lo + (m_hi - m_lo) * mF) * b
    M = np.clip(0.5 * 255.0 + (M - 0.5 * 255.0) * (0.6 + 0.4 * sm), 0.0, 255.0)
    # R: dull resin gaps are ROUGH (independent field, mostly > 120); reflective
    #    chips polish SMOOTH so R drops below 120 on them. ON chips, R is set by
    #    the green/yellow lobe (rF) PLUS a slice of the independent rough field, so
    #    R-high regions exist on their own geometry (not just where M/CC are low).
    R = (55.0 + 170.0 * rough) * (1.0 - 0.78 * b) + (30.0 + 140.0 * rF) * b
    R = np.clip(R, 15.0, 255.0)
    # CC: cool gap patches get a wet sheen + cool features pool clearcoat.
    CC = (26.0 + 150.0 * gap_cool) * g + (cc_lo + (cc_hi - cc_lo) * ccF) * b
    CC = np.clip(CC, 8.0, 220.0)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ---------------------------------------------------------------------------
# Work-res spec runner. The spec math (voronoi/KDTree fields + the per-pixel
# cosine-lobe hue triplet + pack) is the render-time cost; at 2048 (4M px) it
# blows the <3s budget. We run the WHOLE spec at a capped work resolution
# (~1024, where the sequin features are already several px) and resize only the
# three final M/R/CC channels up. The hue classes / decorrelation are unchanged
# (verified at 2048 in the perf+diversity check). This mirrors Viva Mexico's
# "polish on a 1024 work grid" doctrine (owner: speed is king).
# ---------------------------------------------------------------------------
_SPEC_WORK_CAP = 1280


def _spec_workres(core_fn, shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    if max(h, w) <= _SPEC_WORK_CAP:
        return core_fn((h, w), seed, sm, base_m, base_r)
    sh, sw = _work_dims(h, w, _SPEC_WORK_CAP)
    M, R, CC = core_fn((sh, sw), seed, sm, base_m, base_r)
    # NEAREST upsample: each sequin/facet carries a crisp piecewise-constant gloss
    # color, so nearest preserves the hard channel-dominance boundaries (bilinear
    # averages neighbors into muddy mid-gray transition pixels that collapse the
    # hue classes). Also faster than bilinear. (perf+diversity verified @2048.)
    import cv2 as _cv2
    M = _cv2.resize(M, (w, h), interpolation=_cv2.INTER_NEAREST)
    R = _cv2.resize(R, (w, h), interpolation=_cv2.INTER_NEAREST)
    CC = _cv2.resize(CC, (w, h), interpolation=_cv2.INTER_NEAREST)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 8, 220).astype(np.float32))


def _grain(shape, seed):
    h, w = shape[:2]
    key = ("g", h, w, int(seed))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x71C5) & 0xFFFFFFFF)
        n = rng.random((h, w), dtype=np.float32)
        return ((n + np.roll(n, 1, 0) + np.roll(n, 1, 1)) * 0.333).astype(np.float32)

    return _cache(key, build)


# ===========================================================================
# 1) FLIP-SEQUINS — sequin_silver
#    A LATTICE of square flip-discs (the dressmaker sequin that flips two-tone).
#    Each square tile flips between a bright face and a dark face; a thin gap
#    grid separates them. Spec: each tile carries its own hue, flipped tiles
#    blaze (high M), dark tiles go matte (high R), gap = grout.
# ===========================================================================
def _flip_lattice_fields(shape, seed):
    h, w = shape[:2]
    key = ("flipL", h, w, int(seed))

    def build():
        sh, sw = _work_dims(h, w, 900)
        rng = np.random.default_rng((int(seed) ^ 0x1A7F) & 0xFFFFFFFF)
        cells = 58  # tiles across -> fine squares
        # rotate the lattice so it is not axis-aligned (UV-agnostic)
        ang = rng.uniform(0.18, 0.42)
        ca, sa = np.cos(ang), np.sin(ang)
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        u = (xx * ca + yy * sa) / max(sw, sh) * cells
        v = (-xx * sa + yy * ca) / max(sw, sh) * cells
        iu = np.floor(u).astype(np.int32)
        iv = np.floor(v).astype(np.int32)
        fu = u - iu
        fv = v - iv
        # gap grid between tiles
        gap = np.minimum(np.minimum(fu, 1.0 - fu), np.minimum(fv, 1.0 - fv))
        tile = np.clip((gap - 0.06) / 0.10, 0.0, 1.0)  # 1 inside tile, 0 in gap
        # per-tile random flip state + hue + brightness, hashed from tile index
        kk = (iu * 73856093) ^ (iv * 19349663) ^ (int(seed) << 1)
        kk = (kk & 0x7FFFFFFF).astype(np.float64)
        flip = ((kk * 0.000013) % 1.0).astype(np.float32)       # 0..1 flip phase
        rid = ((kk * 0.0000071 + 0.11) % 1.0).astype(np.float32)  # full-circle per-tile id
        flipped = (flip > 0.5).astype(np.float32)
        face = (0.18 + 0.82 * flipped)                          # dark vs bright face
        out = [tile.astype(np.float32), rid, face.astype(np.float32)]
        if (sh, sw) != (h, w):
            out = [_resize_array(a, h, w) for a in out]
        return out[0], out[1], out[2]

    return _cache(key, build)


def paint_sequin_silver(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    tile, rid, face = _flip_lattice_fields((h, w), seed)
    # silver tiles: cool neutral, flipped faces near-white, dark faces deep slate.
    # paint stays SILVER (narrow cool tint by rid); the SPEC rainbows independently.
    base = np.empty((h, w, 3), np.float32)
    base[:] = (0.05, 0.055, 0.065)
    p_hue = (0.55 + 0.10 * (rid - 0.5)) % 1.0
    sat = 0.05 + 0.06 * rid
    r, g, b = hsv_to_rgb_vec(p_hue, sat, face)
    chip = np.stack([r, g, b], axis=-1).astype(np.float32)
    chip = np.clip(chip * (0.80 + 0.45 * face[:, :, None]), 0, 1)
    col = base * (1 - tile[:, :, None]) + chip * tile[:, :, None]
    return _compose(col, paint, mask)


def _spec_sequin_silver_core(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    tile, rid, face = _flip_lattice_fields((h, w), seed)
    body = tile * (0.55 + 0.45 * face)              # bright faces detonate
    # FULL-circle spec hue per tile: each flip-disc fires its own gloss color
    # (blues/oranges/teals) even though the paint reads silver. Viva-style.
    mF, rF, ccF = _hue_to_triplet(rid, face)
    M, R, CC = _pack_spec(mF, rF, ccF, sm, body, base_m, base_r, seed=seed,
                          m_lo=70, m_hi=235, cc_lo=16, cc_hi=190)
    return M, R, CC


# ===========================================================================
# 2) DISCO-BALL MIRROR FACETS — sequin_gold
#    Voronoi mirror facets warped by a radial "ball" lens so facets fan out
#    like a mirrorball. Each facet a flat mirror at its own brightness + hue.
# ===========================================================================
def _ball_facet_fields(shape, seed, n=2200, hue_span=0.16, hue_center=0.12):
    from scipy.spatial import cKDTree
    h, w = shape[:2]
    key = ("ball", h, w, int(seed), int(n), round(hue_span, 3), round(hue_center, 3))

    def build():
        sh, sw = _work_dims(h, w, 900)
        rng = np.random.default_rng((int(seed) ^ 0x55D3) & 0xFFFFFFFF)
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        cy, cx = sh * 0.5, sw * 0.5
        ny = (yy - cy) / max(sh, sw)
        nx = (xx - cx) / max(sh, sw)
        rr = np.sqrt(nx * nx + ny * ny) + 1e-5
        # spherical fan: compress coords toward the rim so facets shrink outward
        warp = np.clip(rr * 1.6, 0, 1.4)
        wy = ny * (1.0 + 0.9 * warp) + cy / max(sh, sw)
        wx = nx * (1.0 + 0.9 * warp) + cx / max(sh, sw)
        pts = np.column_stack([rng.uniform(-0.3, 1.3, n), rng.uniform(-0.3, 1.3, n)]).astype(np.float32)
        grid = np.column_stack([wy.ravel() + 0.5, wx.ravel() + 0.5]).astype(np.float32)
        d, idx = cKDTree(pts).query(grid, k=2, workers=-1)
        d1 = d[:, 0].reshape(sh, sw)
        d2 = d[:, 1].reshape(sh, sw)
        # thin seams: a facet body reads as 1 across most of its interior, dipping
        # to 0 only in a narrow band near the cell boundary (seam ~ 12% of spacing).
        cellsp = 1.6 / np.sqrt(float(n))
        seam_w = 0.12 * cellsp
        edge = np.clip((d2 - d1) / seam_w, 0, 1).reshape(sh, sw)  # 1 facet body, 0 seam
        facet_id = idx[:, 0].reshape(sh, sw)
        rid = (rng.random(n).astype(np.float32))[facet_id]   # full-circle per-facet id
        bri = (rng.random(n).astype(np.float32))[facet_id]
        p_hue = (hue_center + hue_span * (rid - 0.5) * 2.0) % 1.0   # narrow themed hue
        # radial darkening toward rim sells the ball
        sphere = (1.0 - 0.45 * np.clip(rr * 1.4, 0, 1)).astype(np.float32)
        out = [edge.astype(np.float32), p_hue.astype(np.float32), bri.astype(np.float32),
               sphere, rid.astype(np.float32)]
        if (sh, sw) != (h, w):
            out = [_resize_array(a, h, w) for a in out]
        return tuple(out)

    return _cache(key, build)


def paint_sequin_gold(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    edge, p_hue, bri, sphere, rid = _ball_facet_fields((h, w), seed, hue_center=0.11, hue_span=0.12)
    base = np.empty((h, w, 3), np.float32)
    base[:] = (0.07, 0.05, 0.02)
    val = (0.35 + 0.65 * bri) * sphere
    r, g, b = hsv_to_rgb_vec(p_hue, 0.55 + 0.25 * bri, val)
    chip = np.stack([r, g, b], axis=-1).astype(np.float32)
    seam = edge[:, :, None]
    col = base * (1 - seam * 0.92) + chip * seam
    return _compose(col, paint, mask)


def _spec_sequin_gold_core(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    edge, p_hue, bri, sphere, rid = _ball_facet_fields((h, w), seed, hue_center=0.11, hue_span=0.12)
    # facets are solid mirrors -> high body (only seams + far-rim dim). This lets
    # every facet's own hue actually cross the spec thresholds (full rainbow).
    body = edge * (0.70 + 0.30 * bri) * (0.70 + 0.30 * sphere)
    # each mirror facet flashes its OWN spectral hue (mirrorball throwing color)
    mF, rF, ccF = _hue_to_triplet(rid, bri)
    M, R, CC = _pack_spec(mF, rF, ccF, sm, body, base_m, base_r, seed=seed,
                          m_lo=80, m_hi=245, cc_lo=16, cc_hi=200)
    # seams = mirror-edges: roughen so the facet boundaries read as dark veins
    seamline = 1.0 - edge
    R = np.clip(R + seamline * 60.0, 15, 255)
    M = np.clip(M - seamline * 30.0, 0, 255)
    return M, R, CC


# ===========================================================================
# 3) CHUNKY GLITTER — sequin_rose
#    Large, SPARSE hexagonal glitter flakes scattered on a dark ground (chunky
#    craft glitter). Each flake a flat hex with its own hue + flash. Windowed
#    splats so it's fast and the flakes are crisp.
# ===========================================================================
def _chunky_flakes(shape, seed, n=1400, rad_px=8.0, hue_lo=0.88, hue_hi=1.08):
    h, w = shape[:2]
    key = ("chunk", h, w, int(seed), int(n), round(rad_px, 1), round(hue_lo, 3), round(hue_hi, 3))

    def build():
        sh, sw = _work_dims(h, w, 1000)
        scale = sh / float(h)
        r0 = max(2.0, rad_px * scale)
        rng = np.random.default_rng((int(seed) ^ 0x2C8B) & 0xFFFFFFFF)
        cover = np.zeros((sh, sw), np.float32)
        hue = np.zeros((sh, sw), np.float32)
        flash = np.zeros((sh, sw), np.float32)
        cy = rng.uniform(0, sh, n)
        cx = rng.uniform(0, sw, n)
        for i in range(n):
            yc, xc = cy[i], cx[i]
            rr = r0 * rng.uniform(0.7, 1.4)
            y0 = max(0, int(yc - rr)); y1 = min(sh, int(yc + rr) + 1)
            x0 = max(0, int(xc - rr)); x1 = min(sw, int(xc + rr) + 1)
            if y1 <= y0 or x1 <= x0:
                continue
            ly, lx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            dy = ly - yc; dx = lx - xc
            # hexagon distance (3-axis min) -> flat-topped chunky flake
            ang = np.arctan2(dy, dx)
            hexr = rr / np.maximum(np.cos((ang % (np.pi / 3.0)) - np.pi / 6.0), 0.5)
            d = np.sqrt(dy * dy + dx * dx)
            disc = (d <= hexr).astype(np.float32)
            sub = cover[y0:y1, x0:x1]
            newer = disc > sub
            hu = (rng.uniform(hue_lo, hue_hi)) % 1.0
            fl = rng.uniform(0.45, 1.0)
            cover[y0:y1, x0:x1] = np.where(newer, disc, sub)
            hue[y0:y1, x0:x1] = np.where(newer, hu, hue[y0:y1, x0:x1])
            flash[y0:y1, x0:x1] = np.where(newer, fl, flash[y0:y1, x0:x1])
        out = [cover, hue, flash]
        if (sh, sw) != (h, w):
            out = [_resize_array(a, h, w) for a in out]
        return out[0], out[1], out[2]

    return _cache(key, build)


def paint_sequin_rose(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    cover, hue, flash = _chunky_flakes((h, w), seed, hue_lo=0.90, hue_hi=1.06)
    base = np.empty((h, w, 3), np.float32)
    base[:] = (0.09, 0.04, 0.06)
    r, g, b = hsv_to_rgb_vec(hue % 1.0, 0.45 + 0.25 * flash, 0.45 + 0.55 * flash)
    chip = np.stack([r, g, b], axis=-1).astype(np.float32)
    c = cover[:, :, None]
    col = base * (1 - c) + chip * c
    return _compose(col, paint, mask)


def _spec_sequin_rose_core(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    cover, hue, flash = _chunky_flakes((h, w), seed, hue_lo=0.90, hue_hi=1.06)
    body = cover * (0.40 + 0.60 * flash)
    # each chunky flake fires its own gloss color: spread the narrow paint-hue id
    # across the full circle (flake-to-flake), decorrelated by its flash level.
    spec_hue = ((hue - 0.90) / 0.16 + flash * 1.3) % 1.0
    mF, rF, ccF = _hue_to_triplet(spec_hue, flash)
    M, R, CC = _pack_spec(mF, rF, ccF, sm, body, base_m, base_r, seed=seed,
                          m_lo=60, m_hi=235, cc_lo=14, cc_hi=200)
    return M, R, CC


# ===========================================================================
# 4) MERMAID SCALE — sequin_emerald
#    Overlapping fish-scale arcs (offset rows of half-discs). Each scale its own
#    hue; rim of scale catches light (R), body is mirror (M). Rotated lattice.
# ===========================================================================
def _scale_fields(shape, seed, hue_lo=0.30, hue_hi=0.52):
    h, w = shape[:2]
    key = ("scale", h, w, int(seed), round(hue_lo, 3), round(hue_hi, 3))

    def build():
        sh, sw = _work_dims(h, w, 920)
        rng = np.random.default_rng((int(seed) ^ 0x77A1) & 0xFFFFFFFF)
        ang = rng.uniform(0.25, 0.5)
        ca, sa = np.cos(ang), np.sin(ang)
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        cols = 40.0
        u = (xx * ca + yy * sa) / max(sw, sh) * cols
        v = (-xx * sa + yy * ca) / max(sw, sh) * cols
        row = np.floor(v).astype(np.int32)
        # offset every other row by half a scale (brick lay)
        u_off = u + 0.5 * (row % 2)
        cu = u_off - np.floor(u_off) - 0.5
        # scale = disc whose center is at the TOP of its cell (arcs hang down)
        cv = (v - np.floor(v))
        d = np.sqrt(cu * cu + (cv - 0.05) * (cv - 0.05) * 1.4)
        scale_body = np.clip((0.52 - d) / 0.16, 0.0, 1.0)
        rim = np.clip(1.0 - np.abs(d - 0.50) / 0.10, 0.0, 1.0) * (cv > 0.15)
        col_i = np.floor(u_off).astype(np.int32)
        kk = ((col_i * 73856093) ^ (row * 19349663) ^ (int(seed) << 2)) & 0x7FFFFFFF
        kk = kk.astype(np.float64)
        rid = ((kk * 0.0000091) % 1.0).astype(np.float32)   # full-circle per-scale id
        bri = ((kk * 0.0000037 + 0.3) % 1.0).astype(np.float32)
        p_hue = (hue_lo + (hue_hi - hue_lo) * rid).astype(np.float32)  # themed (green) hue
        out = [scale_body.astype(np.float32), rim.astype(np.float32), p_hue, bri, rid]
        if (sh, sw) != (h, w):
            out = [_resize_array(a, h, w) for a in out]
        return tuple(out)

    return _cache(key, build)


def paint_sequin_emerald(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    body, rim, p_hue, bri, rid = _scale_fields((h, w), seed, hue_lo=0.28, hue_hi=0.50)
    base = np.empty((h, w, 3), np.float32)
    base[:] = (0.02, 0.07, 0.05)
    val = 0.35 + 0.6 * bri
    r, g, b = hsv_to_rgb_vec(p_hue, 0.6 + 0.2 * bri, val)
    chip = np.stack([r, g, b], axis=-1).astype(np.float32)
    # rim catches a near-white specular gleam
    chip = np.clip(chip + rim[:, :, None] * 0.5, 0, 1)
    bm = np.clip(body + rim * 0.6, 0, 1)[:, :, None]
    col = base * (1 - bm) + chip * bm
    return _compose(col, paint, mask)


def _spec_sequin_emerald_core(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    body, rim, p_hue, bri, rid = _scale_fields((h, w), seed, hue_lo=0.28, hue_hi=0.50)
    feat = np.clip(body + rim, 0, 1)
    # each scale fires its own iridescent hue across the full circle (fish iridescence)
    mF, rF, ccF = _hue_to_triplet(rid, bri)
    M, R, CC = _pack_spec(mF, rF, ccF, sm, feat * (0.70 + 0.30 * bri), base_m, base_r, seed=seed,
                          m_lo=65, m_hi=235, cc_lo=16, cc_hi=205)
    # the scale RIM is the gleam: drop roughness sharply, push clearcoat (wet edge)
    R = np.clip(R - rim * 120.0, 15, 255)
    CC = np.clip(CC + rim * 90.0, 8, 220)
    M = np.clip(M + rim * 40.0, 0, 255)
    return M, R, CC


# ===========================================================================
# 5) MICRO-SHIMMER — sequin_copper
#    Dense sub-pixel micro-shimmer dust: NO discrete chips, a continuous fine
#    hue-noise field at flake scale. Spec is a true micro-rainbow that twinkles.
# ===========================================================================
def _micro_fields(shape, seed):
    h, w = shape[:2]
    key = ("micro", h, w, int(seed))

    def build():
        # very fine multi-scale fields (feature size ~2-6 px) -> twinkle dust
        sh, sw = _work_dims(h, w, 1100)
        hue = multi_scale_noise((sh, sw), [3, 6, 12], [0.6, 0.3, 0.1], int(seed) ^ 0x12)
        bri = multi_scale_noise((sh, sw), [2, 4, 8], [0.55, 0.3, 0.15], int(seed) ^ 0x4B)
        spk = multi_scale_noise((sh, sw), [2, 3], [0.7, 0.3], int(seed) ^ 0x9C)
        hue = ((np.asarray(hue, np.float32) * 0.5 + 0.5)).astype(np.float32)
        bri = ((np.asarray(bri, np.float32) * 0.5 + 0.5)).astype(np.float32)
        spk = np.clip((np.asarray(spk, np.float32) * 0.5 + 0.5 - 0.62) / 0.38, 0, 1).astype(np.float32)
        out = [hue, bri, spk]
        if (sh, sw) != (h, w):
            out = [_resize_array(a, h, w) for a in out]
        return out[0], out[1], out[2]

    return _cache(key, build)


def paint_sequin_copper(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    hue, bri, spk = _micro_fields((h, w), seed)
    # copper-anchored micro dust: hue wanders warm with cool sparks
    huef = (0.05 + 0.18 * hue + 0.45 * spk) % 1.0
    val = 0.18 + 0.45 * bri + 0.55 * spk
    sat = 0.55 + 0.3 * (1 - spk)
    r, g, b = hsv_to_rgb_vec(huef, sat, np.clip(val, 0, 1))
    col = np.stack([r, g, b], axis=-1).astype(np.float32)
    return _compose(col, paint, mask)


def _spec_sequin_copper_core(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    hue, bri, spk = _micro_fields((h, w), seed)
    huef = (hue + 0.5 * bri + 0.3 * spk) % 1.0       # full-circle hue sweep -> rainbow spec
    # dust covers the whole surface -> high body everywhere so every hue's channel
    # crosses threshold (the micro-rainbow reads), modulated up by sparks.
    body = np.clip(0.62 + 0.18 * bri + 0.20 * spk, 0, 1)
    mF, rF, ccF = _hue_to_triplet(huef, np.clip(bri + spk, 0, 1))
    M, R, CC = _pack_spec(mF, rF, ccF, sm, body, base_m, base_r, seed=seed,
                          m_lo=70, m_hi=235, cc_lo=14, cc_hi=210)
    # micro sparks punch M to mirror on the brightest dust
    M = np.clip(M + spk * 50.0, 0, 255)
    return M, R, CC


# ===========================================================================
# 6) ICE / SHATTERED CRYSTAL — sequin_ice
#    Shattered-crystal crackle: voronoi cells (facets) + bright crack lines.
#    Facet bodies carry hue (icy blues/teals/violets); cracks are a SEPARATE
#    channel (sharp wet specular lines) so the spec decorrelates cleanly.
# ===========================================================================
def _shatter_fields(shape, seed, n=1700, hue_lo=0.50, hue_hi=0.80):
    from scipy.spatial import cKDTree
    h, w = shape[:2]
    key = ("shat", h, w, int(seed), int(n), round(hue_lo, 3), round(hue_hi, 3))

    def build():
        sh, sw = _work_dims(h, w, 900)
        rng = np.random.default_rng((int(seed) ^ 0x4F2D) & 0xFFFFFFFF)
        pts = np.column_stack([rng.uniform(0, sh, n), rng.uniform(0, sw, n)]).astype(np.float32)
        yy, xx = np.mgrid[0:sh, 0:sw]
        grid = np.column_stack([yy.ravel(), xx.ravel()]).astype(np.float32)
        d, idx = cKDTree(pts).query(grid, k=2, workers=-1)
        d1 = d[:, 0].reshape(sh, sw)
        d2 = d[:, 1].reshape(sh, sw)
        crack = np.clip(1.0 - (d2 - d1) / 2.2, 0.0, 1.0) ** 3   # sharp crack lines
        facet = idx[:, 0].reshape(sh, sw)
        rid = (rng.random(n).astype(np.float32))[facet]      # full-circle per-facet id
        bri = (rng.random(n).astype(np.float32))[facet]
        p_hue = (hue_lo + (hue_hi - hue_lo) * rid).astype(np.float32)  # icy blue/violet
        # facet shading by distance to its site (a flat lit crystal face)
        cellnorm = np.clip(1.0 - d1 / (0.9 * (sh + sw) / np.sqrt(n)), 0, 1)
        out = [crack.astype(np.float32), p_hue, bri, cellnorm.astype(np.float32), rid]
        if (sh, sw) != (h, w):
            out = [_resize_array(a, h, w) for a in out]
        return tuple(out)

    return _cache(key, build)


def paint_sequin_ice(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    crack, p_hue, bri, cellnorm, rid = _shatter_fields((h, w), seed, hue_lo=0.48, hue_hi=0.82)
    base = np.empty((h, w, 3), np.float32)
    base[:] = (0.05, 0.07, 0.11)
    val = 0.35 + 0.45 * bri + 0.2 * cellnorm
    r, g, b = hsv_to_rgb_vec(p_hue, 0.35 + 0.25 * bri, np.clip(val, 0, 1))
    chip = np.stack([r, g, b], axis=-1).astype(np.float32)
    # cracks flash white (light caught on a fracture edge)
    col = base * 0.4 + chip * 0.6
    col = np.clip(col + crack[:, :, None] * 0.7, 0, 1)
    return _compose(col, paint, mask)


def _spec_sequin_ice_core(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    crack, p_hue, bri, cellnorm, rid = _shatter_fields((h, w), seed, hue_lo=0.48, hue_hi=0.82)
    body = (0.35 + 0.65 * bri) * (0.6 + 0.4 * cellnorm)
    # each crystal facet refracts a full-spectrum fire (prismatic ice)
    mF, rF, ccF = _hue_to_triplet(rid, bri)
    M, R, CC = _pack_spec(mF, rF, ccF, sm, body, base_m, base_r, seed=seed,
                          m_lo=55, m_hi=225, cc_lo=20, cc_hi=215)
    # cracks: razor-sharp wet mirror lines -> M up hard, R down hard, CC up (separate geometry from facet body)
    M = np.clip(M + crack * 120.0, 0, 255)
    R = np.clip(R - crack * 150.0, 15, 255)
    CC = np.clip(CC + crack * 110.0, 8, 220)
    return M, R, CC


# ===========================================================================
# 7) LARGE PAILLETTES — sequin_rainbow
#    Big round overlapping paillette sequins (the disco-dress big disc). Each
#    paillette a FULL random hue -> the combined spec is an outright rainbow.
#    Round discs with a slight specular gradient + drilled center hole.
# ===========================================================================
def _paillette_fields(shape, seed, n=620, rad_px=22.0, full_hue=True):
    h, w = shape[:2]
    key = ("pail", h, w, int(seed), int(n), round(rad_px, 1), bool(full_hue))

    def build():
        sh, sw = _work_dims(h, w, 1000)
        scale = sh / float(h)
        r0 = max(5.0, rad_px * scale)
        rng = np.random.default_rng((int(seed) ^ 0x6E11) & 0xFFFFFFFF)
        cover = np.zeros((sh, sw), np.float32)
        hue = np.zeros((sh, sw), np.float32)
        grad = np.zeros((sh, sw), np.float32)   # specular gradient across disc
        zorder = np.full((sh, sw), -1.0, np.float32)
        cy = rng.uniform(0, sh, n); cx = rng.uniform(0, sw, n)
        rr_all = r0 * rng.uniform(0.85, 1.25, n)
        hue_all = rng.random(n) if full_hue else (0.0 + 0.0 * rng.random(n))
        gdir = rng.uniform(0, 2 * np.pi, n)
        for i in range(n):
            yc, xc, rr = cy[i], cx[i], rr_all[i]
            y0 = max(0, int(yc - rr)); y1 = min(sh, int(yc + rr) + 1)
            x0 = max(0, int(xc - rr)); x1 = min(sw, int(xc + rr) + 1)
            if y1 <= y0 or x1 <= x0:
                continue
            ly, lx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            dy = ly - yc; dx = lx - xc
            d = np.sqrt(dy * dy + dx * dx)
            disc = (d <= rr).astype(np.float32)
            hole = (d <= rr * 0.13).astype(np.float32)     # drilled center hole
            disc = disc * (1.0 - hole)
            newer = (disc > 0) & (float(i) > zorder[y0:y1, x0:x1])
            sub_z = zorder[y0:y1, x0:x1]
            zorder[y0:y1, x0:x1] = np.where(newer, float(i), sub_z)
            cover[y0:y1, x0:x1] = np.where(newer, disc, cover[y0:y1, x0:x1])
            hue[y0:y1, x0:x1] = np.where(newer, hue_all[i], hue[y0:y1, x0:x1])
            gg = 0.5 + 0.5 * np.cos(np.arctan2(dy, dx) - gdir[i]) * (d / rr)
            grad[y0:y1, x0:x1] = np.where(newer, gg.astype(np.float32), grad[y0:y1, x0:x1])
        out = [cover, hue.astype(np.float32), grad]
        if (sh, sw) != (h, w):
            out = [_resize_array(a, h, w) for a in out]
        return out[0], out[1], out[2]

    return _cache(key, build)


def paint_sequin_rainbow(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    cover, hue, grad = _paillette_fields((h, w), seed, full_hue=True)
    base = np.empty((h, w, 3), np.float32)
    base[:] = (0.03, 0.03, 0.04)
    val = 0.45 + 0.55 * grad
    sat = np.full_like(hue, 0.85)
    r, g, b = hsv_to_rgb_vec(hue, sat, np.clip(val, 0, 1))
    chip = np.stack([r, g, b], axis=-1).astype(np.float32)
    c = cover[:, :, None]
    col = base * (1 - c) + chip * c
    return _compose(col, paint, mask)


def _spec_sequin_rainbow_core(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    cover, hue, grad = _paillette_fields((h, w), seed, full_hue=True)
    body = cover * (0.3 + 0.7 * grad)
    mF, rF, ccF = _hue_to_triplet(hue, grad)
    M, R, CC = _pack_spec(mF, rF, ccF, sm, body, base_m, base_r, seed=seed,
                          m_lo=60, m_hi=235, cc_lo=14, cc_hi=205)
    # the specular gradient gives each big paillette an angled hot streak (M) and
    # a dull side (R) -> intra-disc decorrelation
    streak = cover * np.clip((grad - 0.6) / 0.4, 0, 1)
    M = np.clip(M + streak * 40.0, 0, 255)
    R = np.clip(R + cover * (1.0 - grad) * 50.0, 15, 255)
    return M, R, CC


# ===========================================================================
# 8) HOLOGRAPHIC GLITTER — sequin_holographic
#    True thin-film interference glitter. Each glitter cell has an optical
#    thickness -> interference_palette gives the banded holo color, and the SAME
#    thickness drives the spec into a rainbow via the interference order.
# ===========================================================================
def _holo_fields(shape, seed, n=2600):
    from scipy.spatial import cKDTree
    h, w = shape[:2]
    key = ("holo", h, w, int(seed), int(n))

    def build():
        sh, sw = _work_dims(h, w, 950)
        rng = np.random.default_rng((int(seed) ^ 0x3D77) & 0xFFFFFFFF)
        pts = np.column_stack([rng.uniform(0, sh, n), rng.uniform(0, sw, n)]).astype(np.float32)
        thick_pts = rng.random(n).astype(np.float32)
        bri_pts = rng.random(n).astype(np.float32)
        yy, xx = np.mgrid[0:sh, 0:sw]
        grid = np.column_stack([yy.ravel(), xx.ravel()]).astype(np.float32)
        d, idx = cKDTree(pts).query(grid, k=2, workers=-1)
        d1 = d[:, 0].reshape(sh, sw)
        d2 = d[:, 1].reshape(sh, sw)
        body = np.clip((d2 - d1) / (d2 - d1 + 0.02), 0, 1).reshape(sh, sw)
        facet = idx[:, 0].reshape(sh, sw)
        thick = thick_pts[facet]
        # add a fine tilt gradient inside each cell so the holo shifts within a flake
        tilt = (multi_scale_noise((sh, sw), [4, 8], [0.7, 0.3], int(seed) ^ 0x88))
        thick = np.clip(thick + 0.18 * np.asarray(tilt, np.float32), 0, 1).astype(np.float32)
        bri = bri_pts[facet]
        # Compute the thin-film color HERE at work-res (interference_palette is the
        # render-time hog at 2048: ~2.5s vs ~0.5s here) then resize the 3-channel
        # result once. order = wrapped interference order, used by the spec hue.
        holo_w = np.asarray(interference_palette(thick, orders=4.0, quantize=0.32,
                                                 brightness=1.35), np.float32)
        order_w = (thick * 4.0) % 1.0
        out = [body.astype(np.float32), thick, bri.astype(np.float32), order_w.astype(np.float32)]
        if (sh, sw) != (h, w):
            out = [_resize_array(a, h, w) for a in out]
            holo_w = _resize_array(holo_w, h, w) if holo_w.ndim == 2 else \
                np.stack([_resize_array(holo_w[:, :, k], h, w) for k in range(3)], axis=-1)
        return out[0], out[1], out[2], out[3], holo_w.astype(np.float32)

    return _cache(key, build)


def paint_sequin_holographic(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    body, thick, bri, order, holo = _holo_fields((h, w), seed)
    base = np.empty((h, w, 3), np.float32)
    base[:] = (0.04, 0.04, 0.05)
    val = (0.4 + 0.6 * bri)[:, :, None]
    chip = np.clip(holo * val * 1.5, 0, 1)
    c = body[:, :, None]
    col = base * (1 - c) + chip * c
    return _compose(col, paint, mask)


def _spec_sequin_holographic_core(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    body, thick, bri, order, holo = _holo_fields((h, w), seed)
    # The interference ORDER (thick*orders, wrapped) is the hue here: that maps the
    # full holo spectrum straight into the spec.
    feat = body * (0.35 + 0.65 * bri)
    mF, rF, ccF = _hue_to_triplet(order, bri)
    M, R, CC = _pack_spec(mF, rF, ccF, sm, feat, base_m, base_r, seed=seed,
                          m_lo=70, m_hi=240, cc_lo=16, cc_hi=215)
    # holo flakes are highly reflective: clearcoat rides the BLUE/violet orders
    coolband = 0.5 + 0.5 * np.cos((order * 2 * np.pi) - 3.9)
    CC = np.clip(CC + feat * coolband * 40.0, 8, 220)
    return M, R, CC


# ===========================================================================
# 9) MIRROR MOSAIC — disco_black_diamond
#    Irregular angular mirror-mosaic tiles separated by dark grout (broken-glass
#    mirror mosaic). Each tile a flat mirror at its own brightness + a cool hue;
#    grout is matte. Tiles built from a jittered voronoi with straight-ish edges.
# ===========================================================================
def _mosaic_fields(shape, seed, n=900):
    from scipy.spatial import cKDTree
    h, w = shape[:2]
    key = ("mos", h, w, int(seed), int(n))

    def build():
        sh, sw = _work_dims(h, w, 900)
        rng = np.random.default_rng((int(seed) ^ 0x5B33) & 0xFFFFFFFF)
        # jittered grid points -> angular but evenly sized tiles
        g = int(np.sqrt(n))
        gy, gx = np.mgrid[0:g, 0:g].astype(np.float32)
        py = (gy + rng.uniform(0.1, 0.9, (g, g))) / g * sh
        px = (gx + rng.uniform(0.1, 0.9, (g, g))) / g * sw
        pts = np.column_stack([py.ravel(), px.ravel()]).astype(np.float32)
        nn = pts.shape[0]
        yy, xx = np.mgrid[0:sh, 0:sw]
        grid = np.column_stack([yy.ravel(), xx.ravel()]).astype(np.float32)
        d, idx = cKDTree(pts).query(grid, k=2, workers=-1)
        d1 = d[:, 0].reshape(sh, sw); d2 = d[:, 1].reshape(sh, sw)
        grout = np.clip(1.0 - (d2 - d1) / 3.0, 0, 1) ** 2     # dark grout lines
        tile = 1.0 - grout
        facet = idx[:, 0].reshape(sh, sw)
        rid = (rng.random(nn).astype(np.float32))[facet]
        bri = (rng.random(nn).astype(np.float32))[facet]
        # diamond-cool hues: teal/blue/violet/magenta band
        hue = (0.50 + 0.40 * rid).astype(np.float32)
        out = [tile.astype(np.float32), hue, bri.astype(np.float32), grout.astype(np.float32)]
        if (sh, sw) != (h, w):
            out = [_resize_array(a, h, w) for a in out]
        return tuple(out)

    return _cache(key, build)


def paint_disco_black_diamond(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    tile, hue, bri, grout = _mosaic_fields((h, w), seed)
    base = np.empty((h, w, 3), np.float32)
    base[:] = (0.015, 0.015, 0.02)        # black diamond ground/grout
    # mostly near-white mirror tiles with subtle cool diamond fire
    fire = 0.18 + 0.20 * bri
    r, g, b = hsv_to_rgb_vec(hue, fire, 0.35 + 0.6 * bri)
    chip = np.stack([r, g, b], axis=-1).astype(np.float32)
    t = tile[:, :, None]
    col = base * (1 - t) + chip * t
    return _compose(col, paint, mask)


def _spec_disco_black_diamond_core(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    tile, hue, bri, grout = _mosaic_fields((h, w), seed)
    body = tile * (0.55 + 0.45 * bri)
    mF, rF, ccF = _hue_to_triplet(hue, bri)
    M, R, CC = _pack_spec(mF, rF, ccF, sm, body, base_m, base_r, seed=seed,
                          m_lo=75, m_hi=245, cc_lo=16, cc_hi=200)
    # grout is matte black plastic: a light extra kill on M only (R already rough
    # via the independent field; over-driving R here re-correlates the channels).
    M = np.clip(M - grout * 70.0, 0, 255)
    return M, R, CC


# ===========================================================================
# 10) CARNIVAL SEQUIN RIBBONS — sequin_mardi_gras
#     Diagonal RIBBONS (rows) of small overlapping discs, each ribbon a shifting
#     carnival hue (purple/gold/green), each disc its own brightness. The ribbon
#     index drives a hue march; the spec rainbows across the ribbons.
# ===========================================================================
def _ribbon_fields(shape, seed):
    h, w = shape[:2]
    key = ("ribb", h, w, int(seed))

    def build():
        sh, sw = _work_dims(h, w, 950)
        rng = np.random.default_rng((int(seed) ^ 0x2F66) & 0xFFFFFFFF)
        ang = rng.uniform(0.5, 0.85)
        ca, sa = np.cos(ang), np.sin(ang)
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        rows = 46.0
        v = (-xx * sa + yy * ca) / max(sw, sh) * rows
        u = (xx * ca + yy * sa) / max(sw, sh) * rows
        ribbon = np.floor(v).astype(np.int32)
        # discs along each ribbon
        cu = u - np.floor(u) - 0.5
        cv = v - np.floor(v) - 0.5
        d = np.sqrt(cu * cu + cv * cv)
        disc = np.clip((0.46 - d) / 0.14, 0, 1)
        # per-disc id
        disc_i = np.floor(u).astype(np.int32)
        kk = ((disc_i * 73856093) ^ (ribbon * 19349663) ^ (int(seed) << 3)) & 0x7FFFFFFF
        kkf = kk.astype(np.float64)
        bri = ((kkf * 0.0000059) % 1.0).astype(np.float32)
        rid = ((kkf * 0.0000131 + 0.17) % 1.0).astype(np.float32)  # full-circle per-disc id
        # carnival hue march along ribbons: cycles purple->gold->green
        rib_phase = (ribbon.astype(np.float32) * 0.21 + 0.72) % 1.0
        # 3-stop carnival snap (purple .72, gold .13, green .33) for the PAINT
        carn = np.array([0.72, 0.13, 0.33], np.float32)
        p_hue = carn[(ribbon % 3)]
        p_hue = (p_hue + 0.05 * (bri - 0.5)).astype(np.float32)
        out = [disc.astype(np.float32), p_hue, bri, rib_phase, rid]
        if (sh, sw) != (h, w):
            out = [_resize_array(a, h, w) for a in out]
        return tuple(out)

    return _cache(key, build)


def paint_sequin_mardi_gras(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    disc, p_hue, bri, rib_phase, rid = _ribbon_fields((h, w), seed)
    base = np.empty((h, w, 3), np.float32)
    base[:] = (0.04, 0.02, 0.06)
    val = 0.35 + 0.6 * bri
    sat = np.full_like(p_hue, 0.8)
    r, g, b = hsv_to_rgb_vec(p_hue % 1.0, sat, np.clip(val, 0, 1))
    chip = np.stack([r, g, b], axis=-1).astype(np.float32)
    c = disc[:, :, None]
    col = base * (1 - c) + chip * c
    return _compose(col, paint, mask)


def _spec_sequin_mardi_gras_core(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    disc, p_hue, bri, rib_phase, rid = _ribbon_fields((h, w), seed)
    body = disc * (0.60 + 0.40 * bri)
    # each carnival sequin throws its own gloss color (full circle) on the ribbon
    mF, rF, ccF = _hue_to_triplet(rid, bri)
    M, R, CC = _pack_spec(mF, rF, ccF, sm, body, base_m, base_r, seed=seed,
                          m_lo=65, m_hi=235, cc_lo=16, cc_hi=200)
    # alternate ribbons get a CC wet sweep (R roughness handled by the indep field)
    CC = np.clip(CC + disc * rib_phase * 25.0, 8, 220)
    return M, R, CC


# ---------------------------------------------------------------------------
# Public spec_<id> wrappers — run the core spec at a capped work resolution and
# resize the 3 channels (keeps each render < 3s @ 2048 with the SAME hue
# diversity / decorrelation, verified). Names/signatures match the registry.
# ---------------------------------------------------------------------------
def spec_sequin_silver(shape, seed, sm, base_m, base_r):
    return _spec_workres(_spec_sequin_silver_core, shape, seed, sm, base_m, base_r)


def spec_sequin_gold(shape, seed, sm, base_m, base_r):
    return _spec_workres(_spec_sequin_gold_core, shape, seed, sm, base_m, base_r)


def spec_sequin_rose(shape, seed, sm, base_m, base_r):
    return _spec_workres(_spec_sequin_rose_core, shape, seed, sm, base_m, base_r)


def spec_sequin_emerald(shape, seed, sm, base_m, base_r):
    return _spec_workres(_spec_sequin_emerald_core, shape, seed, sm, base_m, base_r)


def spec_sequin_copper(shape, seed, sm, base_m, base_r):
    return _spec_workres(_spec_sequin_copper_core, shape, seed, sm, base_m, base_r)


def spec_sequin_ice(shape, seed, sm, base_m, base_r):
    return _spec_workres(_spec_sequin_ice_core, shape, seed, sm, base_m, base_r)


def spec_sequin_rainbow(shape, seed, sm, base_m, base_r):
    return _spec_workres(_spec_sequin_rainbow_core, shape, seed, sm, base_m, base_r)


def spec_sequin_holographic(shape, seed, sm, base_m, base_r):
    return _spec_workres(_spec_sequin_holographic_core, shape, seed, sm, base_m, base_r)


def spec_disco_black_diamond(shape, seed, sm, base_m, base_r):
    return _spec_workres(_spec_disco_black_diamond_core, shape, seed, sm, base_m, base_r)


def spec_sequin_mardi_gras(shape, seed, sm, base_m, base_r):
    return _spec_workres(_spec_sequin_mardi_gras_core, shape, seed, sm, base_m, base_r)
