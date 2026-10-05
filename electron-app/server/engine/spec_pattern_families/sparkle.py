"""Sparkle / facet spec pattern family for Shokker Paint Booth.

This module is imported by engine.spec_patterns so PATTERN_CATALOG keeps
the legacy public keys while the central spec registry shrinks.

SPB-106 (owner mandate 2026-05-20): "DO NOT GROW engine/spec_patterns.py"
— new sparkle-category rebuilds go here and re-export through the
central registry.
"""
import numpy as np

from ..spec_patterns import (
    _flat,
    _normalize,
    _sm_scale,
    _validate_spec_output,
)


def diamond_dust(shape, seed, sm, density=0.003, **kwargs):
    """diamond_dust.

    identity: R6-Loop owner-rebuild — TRUE DIAMOND POWDER. Owner: "doesn't
    match name / boring / too sparse". Fix: deep-jeweler-velvet dark
    substrate (composite-dark, was bright green!) + dense fine 2-4 px
    crystal carpet + new HERO BRILLIANT-CUT pavilion facet stars
    (geometric optical illusion: a regular octagon outline filled with 8
    radial pavilion triangles that read as a true brilliant-cut diamond
    from above). Plus rainbow dispersion halos and a pinpoint fire
    carpet for old-school diamond fire.

    Tiers (all 8-32 px features):
      1) deep jeweler-velvet dark base (M=0.08, R=0.10, CC=0.06)
      2) dense fine 2-4 px crystal carpet (~10k crystals)
      3) HERO new — BRILLIANT-CUT PAVILION STARS: octagonal outline +
         8 radial pavilion-facet triangles, 14-22 px diameter, 10-16
         hero stars, optical-illusion geometric jewel motif
      4) RAINBOW DISPERSION HALOS — 3-ring prismatic surround each hero
      5) pinpoint single-px fire carpet (vectorized)
      6) dim trench specks (vectorized)

    Per-crystal TIGHT chroma uniform (±0.05) from bright icy zone palette.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(int(seed) + (hash("diamond_dust_r6_v2") % 10000))
    mn = min(h, w); scale = max(mn / 256.0, 0.6)
    # Density tuned for 256 thumb — many fine crystals but capped.
    n_crystals = min(max(4000, int(h * w * 0.10)), 12000)

    cy = rng.uniform(1, h - 2, n_crystals).astype(np.float32)
    cx = rng.uniform(1, w - 2, n_crystals).astype(np.float32)
    sizes = (rng.uniform(1.4, 3.4, n_crystals) * scale).astype(np.float32)
    sizes = np.clip(sizes, 1.0, 3.2)
    rots = rng.uniform(0, np.pi / 2, n_crystals).astype(np.float32)

    # Per-crystal TIGHT chroma uniform — icy bright zone
    cM = (0.82 + rng.uniform(-0.10, 0.10, n_crystals)).astype(np.float32)
    cR = (0.14 + rng.uniform(-0.06, 0.06, n_crystals)).astype(np.float32)
    cC = (0.55 + rng.uniform(-0.12, 0.20, n_crystals)).astype(np.float32)

    # DEEP JEWELER-VELVET BASE — composite-dark, NOT bright green
    grain = (np.random.RandomState(int(seed) + 3127).rand(h, w).astype(np.float32) - 0.5) * 0.06
    M = np.clip(0.08 + grain, 0, 1)
    R_ch = np.clip(0.10 + grain * 0.5, 0, 1)
    CC = np.clip(0.06 + grain * 0.4, 0, 1)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for i in range(n_crystals):
        s = float(sizes[i]); reach = int(s * 1.4) + 1
        cyi = int(cy[i]); cxi = int(cx[i])
        ya = max(0, cyi - reach); yb = min(h, cyi + reach + 1)
        xa = max(0, cxi - reach); xb = min(w, cxi + reach + 1)
        if xa >= xb or ya >= yb:
            continue
        ly = yy[ya:yb, xa:xb] - cy[i]
        lx = xx[ya:yb, xa:xb] - cx[i]
        ca, sa = np.cos(rots[i]), np.sin(rots[i])
        u = lx * ca + ly * sa
        v = -lx * sa + ly * ca
        facet = np.maximum(0.0, 1.0 - (np.abs(u) + np.abs(v)) / s)
        f = facet ** 0.6
        M[ya:yb, xa:xb] = np.maximum(M[ya:yb, xa:xb], f * cM[i])
        R_ch[ya:yb, xa:xb] = np.minimum(R_ch[ya:yb, xa:xb], 1.0 - f * (1.0 - cR[i]))
        CC[ya:yb, xa:xb] = np.maximum(CC[ya:yb, xa:xb], f * cC[i])
        if 0 <= cyi < h and 0 <= cxi < w:
            M[cyi, cxi] = max(M[cyi, cxi], float(cM[i]))

    # DENSE PINPOINT FIRE CARPET — single-pixel chroma diversity
    n_fire = max(8000, int(h * w / 70))
    fy = rng.integers(0, h, n_fire); fx = rng.integers(0, w, n_fire)
    M[fy, fx] = np.maximum(M[fy, fx], rng.uniform(0.65, 0.99, n_fire).astype(np.float32))
    R_ch[fy, fx] = np.minimum(R_ch[fy, fx], rng.uniform(0.04, 0.30, n_fire).astype(np.float32))
    CC[fy, fx] = np.maximum(CC[fy, fx], rng.uniform(0.40, 0.96, n_fire).astype(np.float32))

    # DIM TRENCH SPECKS — chroma-diverse shadows between crystals
    n_dk = int(np.clip(mn * mn * 0.0030, 4500, 28000))
    ddy = rng.integers(0, h, n_dk); ddx = rng.integers(0, w, n_dk)
    M[ddy, ddx]  = np.minimum(M[ddy, ddx],  np.random.default_rng(int(seed) + 99).uniform(0.05, 0.28, n_dk).astype(np.float32))
    CC[ddy, ddx] = np.minimum(CC[ddy, ddx], np.random.default_rng(int(seed) + 199).uniform(0.05, 0.30, n_dk).astype(np.float32))

    # HERO — BRILLIANT-CUT PAVILION STARS (new geometric motif). Each is
    # an octagonal outline + 8 radial pavilion triangles meeting at center,
    # producing a real brilliant-cut diamond table-view. 10-16 across.
    # Try cv2 if available; fall back to numpy circles otherwise.
    try:
        import cv2 as _cv2_local
        _HAS_CV2 = True
    except Exception:
        _HAS_CV2 = False
    n_stars = int(rng.integers(10, 17))
    for i in range(n_stars):
        sx_ = int(rng.uniform(0.08, 0.92) * w); sy_ = int(rng.uniform(0.08, 0.92) * h)
        radius = int(np.clip(rng.uniform(8.0, 11.0) * scale, 7, 11))
        rot = float(rng.uniform(0, np.pi / 4))
        # Per-hero TIGHT chroma uniform — bright jewel zone
        hM = float(np.clip(0.92 + rng.uniform(-0.05, 0.05), 0, 1))
        hR = float(np.clip(0.08 + rng.uniform(-0.04, 0.04), 0, 1))
        hCC = float(np.clip(0.78 + rng.uniform(-0.06, 0.10), 0, 1))

        # 3 concentric prismatic dispersion rings around hero
        if _HAS_CV2:
            for ridx, r_ring in enumerate((radius + 2, radius + 4, radius + 6)):
                if r_ring > min(w, h) / 2: continue
                # Each ring an INDEPENDENT CC (spectral split: blue/white/cyan)
                rrM = float(np.clip(0.66 + rng.uniform(-0.06, 0.06), 0, 1))
                rrR = float(np.clip(0.18 + rng.uniform(-0.06, 0.06), 0, 1))
                # CC across spectral band (this is intentional WIDE — dispersion)
                rrCC = float(np.clip([0.42, 0.66, 0.88][ridx] + rng.uniform(-0.06, 0.06), 0, 1))
                _cv2_local.circle(M, (sx_, sy_), r_ring, rrM, 1, lineType=_cv2_local.LINE_AA)
                _cv2_local.circle(R_ch, (sx_, sy_), r_ring, rrR, 1, lineType=_cv2_local.LINE_AA)
                _cv2_local.circle(CC, (sx_, sy_), r_ring, rrCC, 1, lineType=_cv2_local.LINE_AA)

            # Octagonal outline — 8 vertices around radius
            verts = []
            for k in range(8):
                ang = rot + k * (2 * np.pi / 8)
                vx = int(sx_ + np.cos(ang) * radius)
                vy = int(sy_ + np.sin(ang) * radius)
                verts.append((vx, vy))
            # Outline polygon
            pts = np.array(verts, dtype=np.int32).reshape(-1, 1, 2)
            _cv2_local.polylines(M, [pts], True, hM, 1, lineType=_cv2_local.LINE_AA)
            _cv2_local.polylines(R_ch, [pts], True, hR, 1, lineType=_cv2_local.LINE_AA)
            _cv2_local.polylines(CC, [pts], True, hCC, 1, lineType=_cv2_local.LINE_AA)
            # 8 PAVILION FACET RADII — spokes from center to each vertex
            for (vx, vy) in verts:
                _cv2_local.line(M, (sx_, sy_), (vx, vy), hM, 1, lineType=_cv2_local.LINE_AA)
                _cv2_local.line(R_ch, (sx_, sy_), (vx, vy), hR, 1, lineType=_cv2_local.LINE_AA)
                _cv2_local.line(CC, (sx_, sy_), (vx, vy), hCC, 1, lineType=_cv2_local.LINE_AA)
            # Bright center culet
            _cv2_local.circle(M, (sx_, sy_), 2, min(0.99, hM + 0.05), -1, lineType=_cv2_local.LINE_AA)
            _cv2_local.circle(CC, (sx_, sy_), 2, min(0.95, hCC + 0.10), -1, lineType=_cv2_local.LINE_AA)
        else:
            # Fallback: bright dot
            if 0 <= sx_ < w and 0 <= sy_ < h:
                M[sy_, sx_] = max(float(M[sy_, sx_]), hM)
                CC[sy_, sx_] = max(float(CC[sy_, sx_]), hCC)

    out = np.stack([np.clip(M, 0, 1), np.clip(R_ch, 0, 1), np.clip(CC, 0, 1)], axis=-1).astype(np.float32)
    return _sm_scale(out, sm)
diamond_dust._spb_concept_complete = True


__all__ = ["diamond_dust"]
