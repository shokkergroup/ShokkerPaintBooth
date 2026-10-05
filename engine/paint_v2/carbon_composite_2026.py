# -*- coding: utf-8 -*-
"""
engine/paint_v2/carbon_composite_2026.py — ★ CARBON & COMPOSITE (rebuild 2026-06-14)

Owner mandate: the old carbon was a crude axis-aligned sin/cos ripple with a baked-in
bb sheen — plain, upright, low-detail. This rebuild gives every finish REAL woven-tow
geometry (±45° twill / plain / spread-tow / forged / hex) with crisp fiber striations,
and puts the anisotropic sheen in the SPEC (no albedo sheen). 20 finishes, diverse:
black/charcoal/grey/gunmetal carbons + matte + RED/BLUE tinted + gold aramid/kevlar +
RED-kevlar & blue hybrids + bronze basalt + white dyneema + milky fiberglass + graphene
mirror + gold honeycomb.

Same contracts as the rest of the engine:
  paint_x(paint, shape, mask, seed, pm, bb) -> HxWx3 float 0..1  (static fine-detail albedo)
  spec_x(shape, seed, sm, base_m, base_r)  -> (M, R, CC) float32 0..255  (R>=15, M<=255)
Married: paint+spec share seed/kind/period/angle so the spec's crown sheen lands on the
exact tow crowns the albedo weaves. Decorrelated M(crown)/R(gap+stria)/CC. <3s @2048
(weave is analytic full-res = crisp & cheap; only forged/ceramic use cached broad noise).
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid, _resize_array

_CC_CACHE = {}


def _cache(key, fn):
    v = _CC_CACHE.get(key)
    if v is None:
        if len(_CC_CACHE) > 160:
            _CC_CACHE.clear()
        v = fn()
        _CC_CACHE[key] = v
    return v


def _norm01(a):
    a = np.asarray(a, dtype=np.float32)
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-7:
        return np.zeros_like(a, dtype=np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _broad(shape, scales, weights, seed, cap=640):
    h, w = shape[:2]
    key = ("b", h, w, tuple(scales), tuple(weights), int(seed), int(cap))

    def build():
        work = min(int(cap), h, w)
        if work < min(h, w):
            sh = max(64, int(round(h * work / max(h, w))))
            sw = max(64, int(round(w * work / max(h, w))))
            f = multi_scale_noise((sh, sw), scales, weights, seed)
            return _resize_array(np.asarray(f, np.float32), h, w)
        return np.asarray(multi_scale_noise((h, w), scales, weights, seed), np.float32)

    return _cache(key, build)


def _flake(shape, seed, density, lo=0.3, hi=1.0):
    h, w = shape[:2]
    key = ("fl", h, w, int(seed), float(density), float(lo))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x7C13) & 0xFFFFFFFF)
        n = min(int(h * w * float(density)), 150000)
        out = np.zeros((h, w), np.float32)
        if n > 0:
            yy = rng.integers(0, h, n); xx = rng.integers(0, w, n)
            out[yy, xx] = rng.uniform(lo, hi, n).astype(np.float32)
            out = np.maximum.reduce([out, np.roll(out, 1, 0) * 0.4, np.roll(out, 1, 1) * 0.4])
        return out.astype(np.float32)

    return _cache(key, build)


def _grain(shape, seed):
    """Independent full-res fine roughness field (0..1) — gives the spec R channel its
    OWN geometry so it decorrelates from M's tow-crown structure (|corr|<0.85 gate)."""
    h, w = shape[:2]
    key = ("g", h, w, int(seed))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x33A1) & 0xFFFFFFFF)
        n = rng.random((h, w), dtype=np.float32)
        n = (n + np.roll(n, 1, 0) + np.roll(n, -1, 0) + np.roll(n, 1, 1) + np.roll(n, -1, 1)) * 0.2
        return n.astype(np.float32)

    return _cache(key, build)


# ---------- weave geometry (analytic, full-res = crisp fine detail) ----------

def _weave_field(shape, seed, kind, period, angle, fil):
    """Return (crown 0..1, sel 0..1 warp/weft, across 0..1) for the weave kind."""
    h, w = shape[:2]
    key = ("wf", h, w, int(seed), kind, float(period), float(angle), float(fil))

    def build():
        y, x = get_mgrid((h, w))
        if kind == "hex":
            s = (2.0 * np.pi) / float(period)
            g = (np.cos(x * s) + np.cos((0.5 * x + 0.866 * y) * s)
                 + np.cos((0.5 * x - 0.866 * y) * s)) / 3.0
            edge = np.clip(1.0 - np.abs(g) * 2.2, 0, 1).astype(np.float32)   # bright cell walls
            return edge, None, edge
        if kind == "forged":
            base = _norm01(_broad((h, w), [max(2, int(period // 5)), int(period // 2)],
                                  [0.5, 0.5], seed + 71))
            ang = _broad((h, w), [int(period)], [1.0], seed + 72) * np.pi
            stria = (0.5 + 0.5 * np.cos((x * np.cos(ang) + y * np.sin(ang)) * 0.55)).astype(np.float32)
            crown = np.clip(base * 0.62 + stria * 0.38, 0, 1).astype(np.float32)
            return crown, None, stria
        a = np.deg2rad(float(angle))
        ca, sa = np.cos(a), np.sin(a)
        u = (x * ca + y * sa) / float(period)
        v = (-x * sa + y * ca) / float(period)
        iu = np.floor(u); iv = np.floor(v)
        fu = (u - iu).astype(np.float32); fv = (v - iv).astype(np.float32)

        def tow(frac, width):
            d = frac - 0.5
            return np.exp(-(d * d) / (2.0 * width * width)).astype(np.float32)

        if kind == "spread":
            tu = np.clip(tow(fu, 0.42) * 1.25, 0, 1); tv = np.clip(tow(fv, 0.42) * 1.25, 0, 1)
            k = 2
        elif kind == "plain":
            tu = tow(fu, 0.32); tv = tow(fv, 0.32); k = 1
        else:  # twill 2x2
            tu = tow(fu, 0.30); tv = tow(fv, 0.30); k = 2
        stagger = np.mod(iu - iv, 2 * k)
        warp_top = stagger < k
        crown = np.where(warp_top, tu, tv).astype(np.float32)
        sel = warp_top.astype(np.float32)
        across = np.where(warp_top, fu, fv).astype(np.float32)
        # fine filament striation across each tow (the crisp carbon micro-detail)
        stria = (0.5 + 0.5 * np.cos(across * fil * 2.0 * np.pi)).astype(np.float32)
        crown = np.clip(crown * (0.80 + 0.20 * stria), 0, 1).astype(np.float32)
        return crown, sel, across

    return _cache(key, build)


# ---------- paint + spec cores ----------

def _weave(paint, shape, mask, seed, pm, bb, tow_rgb, gap_rgb, kind="twill", period=16,
           angle=45, tow2_rgb=None, stria=0.45, fil=7.0, speckle=0.0,
           speckle_rgb=(0.8, 0.8, 0.82)):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    paint = paint.astype(np.float32)
    h, w = shape[:2]
    crown, sel, across = _weave_field((h, w), seed, kind, period, angle, fil)

    if tow2_rgb is not None and sel is not None:
        a = np.asarray(tow_rgb, np.float32); b = np.asarray(tow2_rgb, np.float32)
        towc = a[None, None, :] * sel[:, :, None] + b[None, None, :] * (1 - sel[:, :, None])
    else:
        towc = np.asarray(tow_rgb, np.float32)[None, None, :]
    gap = np.asarray(gap_rgb, np.float32)[None, None, :]
    c = crown[:, :, None]
    col = gap * (1 - c) + towc * c
    if stria > 0 and across is not None and kind not in ("hex",):
        fine = (0.5 + 0.5 * np.cos(across * fil * 2.0 * np.pi))[:, :, None]
        col = col * (1.0 - stria * 0.16 * (1.0 - fine))
    if speckle > 0:
        sp = _flake((h, w), seed + 9, speckle, lo=0.3)
        col = np.clip(col + sp[:, :, None] * np.asarray(speckle_rgb, np.float32)[None, None, :] * 0.5, 0, 1)
    col = np.clip(col, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)


def _weave_spec(shape, seed, sm, base_m, base_r, kind="twill", period=16, angle=45, fil=7.0,
                m_crown=150.0, m_gap=45.0, r_crown=24.0, r_gap=72.0, cc=16.0, speckle=0.0):
    h, w = shape[:2]
    crown, sel, across = _weave_field((h, w), seed, kind, period, angle, fil)
    # M rides the tow crowns (conductive fiber catches light); gaps = matte resin
    M = np.clip(m_gap + (m_crown - m_gap) * crown * sm, 0, 255)
    # R rides an INDEPENDENT fine-grain field (its own geometry) so it decorrelates
    # from M's tow-crown structure; only a small gloss-on-crown dip is kept.
    grain = _grain((h, w), seed + 5)
    r_mid = 0.5 * (r_crown + r_gap)
    r_amp = 0.5 * (r_gap - r_crown)
    R = r_mid + r_amp * (grain - 0.5) * 2.0 * sm
    R = R - 0.18 * (r_gap - r_crown) * crown * sm
    R = np.clip(R, 15, 255)
    CCv = np.full((h, w), float(cc), np.float32)
    if speckle > 0:                                   # ceramic dust pits the clear
        sp = np.clip(_flake((h, w), seed + 9, speckle, lo=0.3), 0, 1)
        R = np.clip(R + sp * 60.0 * sm, 15, 255)
    return M.astype(np.float32), R.astype(np.float32), CCv.astype(np.float32)


# =====================================================================
# THE 20
# =====================================================================
# tow/gap palettes
_K = dict  # alias for brevity

# ---- 1. carbon_base — black 2x2 twill, clearcoat gloss (hero) ----
def paint_carbon_base(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.20, 0.20, 0.22), (0.035, 0.035, 0.045),
                  kind="twill", period=15, fil=7.0)
def spec_carbon_base(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="twill", period=15, fil=7.0,
                       m_crown=150, m_gap=42, r_crown=22, r_gap=74, cc=16)

# ---- 2. carbon_weave — charcoal plain weave ----
def paint_carbon_weave(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.27, 0.27, 0.29), (0.05, 0.05, 0.06),
                  kind="plain", period=20, fil=6.0)
def spec_carbon_weave(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="plain", period=20, fil=6.0,
                       m_crown=145, m_gap=44, r_crown=26, r_gap=76, cc=16)

# ---- 3. carbon_3k_fine — fine tight twill (NEW) ----
def paint_carbon_3k_fine(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.21, 0.21, 0.24), (0.04, 0.04, 0.05),
                  kind="twill", period=9, fil=9.0)
def spec_carbon_3k_fine(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="twill", period=9, fil=9.0,
                       m_crown=152, m_gap=42, r_crown=22, r_gap=74, cc=16)

# ---- 4. carbon_satin — matte/satin clear black twill (NEW) ----
def paint_carbon_satin(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.17, 0.17, 0.19), (0.045, 0.045, 0.05),
                  kind="twill", period=15, fil=7.0)
def spec_carbon_satin(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="twill", period=15, fil=7.0,
                       m_crown=120, m_gap=40, r_crown=95, r_gap=140, cc=120)

# ---- 5. carbon_red — candy-red tinted carbon twill (NEW) ----
def paint_carbon_red(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.55, 0.10, 0.10), (0.10, 0.015, 0.015),
                  kind="twill", period=15, fil=7.0)
def spec_carbon_red(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="twill", period=15, fil=7.0,
                       m_crown=150, m_gap=40, r_crown=22, r_gap=72, cc=16)

# ---- 6. carbon_blue — candy-blue tinted carbon twill (NEW) ----
def paint_carbon_blue(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.10, 0.20, 0.58), (0.02, 0.03, 0.11),
                  kind="twill", period=15, fil=7.0)
def spec_carbon_blue(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="twill", period=15, fil=7.0,
                       m_crown=150, m_gap=40, r_crown=22, r_gap=72, cc=16)

# ---- 7. spread_tow — wide flat spread-tow ribbons (NEW) ----
def paint_spread_tow(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.22, 0.22, 0.24), (0.05, 0.05, 0.06),
                  kind="spread", period=44, fil=5.0)
def spec_spread_tow(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="spread", period=44, fil=5.0,
                       m_crown=150, m_gap=46, r_crown=24, r_gap=70, cc=16)

# ---- 8. carbon_ceramic — light grey ceramic-speckle twill, matte ----
def paint_carbon_ceramic(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.52, 0.52, 0.54), (0.30, 0.30, 0.32),
                  kind="twill", period=16, fil=6.0, speckle=0.05, speckle_rgb=(0.85, 0.85, 0.88))
def spec_carbon_ceramic(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="twill", period=16, fil=6.0,
                       m_crown=110, m_gap=60, r_crown=70, r_gap=130, cc=90, speckle=0.05)

# ---- 9. forged_carbon_vis — gunmetal forged, clearcoat ----
def paint_forged_carbon_vis(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.32, 0.33, 0.36), (0.10, 0.10, 0.12),
                  kind="forged", period=46, fil=5.0)
def spec_forged_carbon_vis(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="forged", period=46, fil=5.0,
                       m_crown=160, m_gap=70, r_crown=30, r_gap=85, cc=16)

# ---- 10. forged_composite — coarse forged, low gloss ----
def paint_forged_composite(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.26, 0.26, 0.27), (0.09, 0.09, 0.10),
                  kind="forged", period=70, fil=4.0)
def spec_forged_composite(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="forged", period=70, fil=4.0,
                       m_crown=130, m_gap=64, r_crown=55, r_gap=110, cc=60)

# ---- 11. forged_blue — forged with blue resin (NEW) ----
def paint_forged_blue(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.20, 0.26, 0.46), (0.04, 0.05, 0.12),
                  kind="forged", period=48, fil=5.0)
def spec_forged_blue(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="forged", period=48, fil=5.0,
                       m_crown=150, m_gap=64, r_crown=32, r_gap=88, cc=16)

# ---- 12. graphene — hex lattice, near-mirror dark ----
def paint_graphene(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.55, 0.57, 0.64), (0.05, 0.05, 0.08),
                  kind="hex", period=10, fil=0.0)
def spec_graphene(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="hex", period=10,
                       m_crown=215, m_gap=70, r_crown=18, r_gap=55, cc=16)

# ---- 13. nomex_honeycomb — gold aramid honeycomb hex (NEW) ----
def paint_nomex_honeycomb(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.82, 0.62, 0.18), (0.12, 0.09, 0.03),
                  kind="hex", period=30, fil=0.0)
def spec_nomex_honeycomb(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="hex", period=30,
                       m_crown=70, m_gap=30, r_crown=70, r_gap=120, cc=70)

# ---- 14. aramid — gold Kevlar plain weave, satin ----
def paint_aramid(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.84, 0.63, 0.13), (0.28, 0.20, 0.04),
                  kind="plain", period=18, fil=7.0)
def spec_aramid(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="plain", period=18, fil=7.0,
                       m_crown=60, m_gap=28, r_crown=55, r_gap=105, cc=40)

# ---- 15. kevlar_base — raw gold macro weave, matte ----
def paint_kevlar_base(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.80, 0.60, 0.14), (0.24, 0.17, 0.04),
                  kind="plain", period=28, fil=6.0)
def spec_kevlar_base(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="plain", period=28, fil=6.0,
                       m_crown=45, m_gap=22, r_crown=95, r_gap=150, cc=120)

# ---- 16. kevlar_red — carbon + RED kevlar hybrid (NEW) ----
def paint_kevlar_red(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.62, 0.07, 0.07), (0.05, 0.05, 0.06),
                  kind="twill", period=17, fil=7.0, tow2_rgb=(0.17, 0.17, 0.19))
def spec_kevlar_red(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="twill", period=17, fil=7.0,
                       m_crown=120, m_gap=40, r_crown=40, r_gap=90, cc=16)

# ---- 17. hybrid_weave — carbon + BLUE tracer hybrid ----
def paint_hybrid_weave(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.10, 0.30, 0.72), (0.05, 0.05, 0.06),
                  kind="twill", period=17, fil=7.0, tow2_rgb=(0.18, 0.18, 0.20))
def spec_hybrid_weave(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="twill", period=17, fil=7.0,
                       m_crown=130, m_gap=40, r_crown=34, r_gap=88, cc=16)

# ---- 18. basalt_weave — bronze/gold-grey basalt twill (NEW) ----
def paint_basalt_weave(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.46, 0.39, 0.30), (0.12, 0.10, 0.08),
                  kind="twill", period=16, fil=7.0)
def spec_basalt_weave(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="twill", period=16, fil=7.0,
                       m_crown=125, m_gap=50, r_crown=40, r_gap=95, cc=40)

# ---- 19. dyneema_white — white UHMWPE technical weave, matte (NEW) ----
def paint_dyneema_white(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.84, 0.85, 0.87), (0.50, 0.51, 0.54),
                  kind="plain", period=20, fil=7.0)
def spec_dyneema_white(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="plain", period=20, fil=7.0,
                       m_crown=20, m_gap=8, r_crown=90, r_gap=150, cc=110)

# ---- 20. fiberglass — milky translucent + glass strands, glossy ----
def paint_fiberglass(paint, shape, mask, seed, pm, bb):
    return _weave(paint, shape, mask, seed, pm, bb, (0.72, 0.74, 0.75), (0.50, 0.52, 0.54),
                  kind="forged", period=40, fil=5.0, speckle=0.06, speckle_rgb=(0.92, 0.94, 0.96))
def spec_fiberglass(shape, seed, sm, base_m, base_r):
    return _weave_spec(shape, seed, sm, base_m, base_r, kind="forged", period=40, fil=5.0,
                       m_crown=25, m_gap=8, r_crown=30, r_gap=70, cc=16, speckle=0.06)
