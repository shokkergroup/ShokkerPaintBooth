# -*- coding: utf-8 -*-
"""
engine/paint_v2/candy_pearl_2026.py — ★ CANDY & PEARL  (bespoke rebuild 2026-06-14)

Owner mandate (ricky@shokkergroup.com):
  * NO shared "sheen" baked into the albedo. The PAINT layer is a STATIC, CRISP,
    high-frequency fine-detail layer (flake / mica platelets / play-of-color flecks).
    The angle behaviour lives in the SPEC map (iRacing drives it) — never in albedo.
    A low-freq sheen on a 2048² canvas smears out exactly the fine detail we want.
  * COLOR DIVERSE — 20 finishes spread across the wheel (no 3 near-identical reds/blues).

Each finish is a MARRIED pair: paint_<id>() + spec_<id>() sharing ONE seed so the
spec's metal-flake flash lands on the exact flake the albedo paints (ignition doctrine).

Physics reused from engine.color_science:
  candy_absorb         : Beer-Lambert candy = flake seen through tinted clear; depth
                         field deepens + saturates the tint. Driven here by FINE grain,
                         not a smooth gradient — so it mottles finely, never washes.
  interference_palette : real thin-film color ORDER (gold->magenta->cyan->green) for
                         opal / abalone / spectraflame flecks — not a fake HSV rainbow.

Contracts:
  spec_x(shape, seed, sm, base_m, base_r) -> (M, R, CC)  float32 HxW 0..255
        R floor 15 (GGX);  CC=16 wet clear;  high CC = flat.  sm scales contrast.
  paint_x(paint, shape, mask, seed, pm, bb) -> HxWx3 float 0..1
        return mix*mask + paint*(1-mask).  bb (highlight field) is intentionally NOT
        used to shade the albedo — angle response is the spec's job.

Decorrelation: M rides flake pins, R rides a different fine grain, CC mostly wet —
|corr| stays far under the 0.85 richness gate.
FINE DETAIL: flake / platelet / fleck fields are generated at FULL resolution (crisp);
only the broad, intentionally-smooth candy-pour uses the work-res cache. Perf <3s @2048.
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid, _resize_array
from engine.color_science import candy_absorb, interference_palette

_CP_CACHE = {}


def _cache(key, fn):
    v = _CP_CACHE.get(key)
    if v is None:
        if len(_CP_CACHE) > 200:
            _CP_CACHE.clear()
        v = fn()
        _CP_CACHE[key] = v
    return v


def _norm01(a):
    a = np.asarray(a, dtype=np.float32)
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-7:
        return np.zeros_like(a, dtype=np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _broad(shape, scales, weights, seed, cap=720):
    """Cached LOW-frequency field (candy pour). Capped + resized = smooth by design."""
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


def _mid(shape, feature_px, seed, octaves=3, falloff=0.55):
    """THE MISSING BAND: value noise with features at an EXACT pixel size.

    This module could only build two things — `_grain` (1-3px hash) and `_broad`
    (noise capped at 720px then upsampled, so >=70px).  There was nothing between
    3px and 70px, which is precisely the 8-32px window CLAUDE.md mandates, and it
    is why every finish here reads as either per-pixel confetti or a soft blob.

    Do not reach for multi_scale_noise's scale argument to fix that: measured on
    this build, scale=8 -> ~72px features and scale=256 -> ~872px, i.e. a LARGER
    number means a LARGER feature, and the values needed for a 16px feature fall
    off the bottom of its useful range.  Generating white noise on an
    (h/k, w/k) lattice and bilinearly upsampling gives the feature size directly.

    CALIBRATION (radial power spectrum, this build): the DOMINANT feature comes
    out at ~2x `feature_px`, because a falloff-weighted octave stack peaks above
    its base lattice.  So the 8-32px mandate wants feature_px 4-16.  Reference
    points on the same metric: `_grain` = 5.1px, `_broad([7,16,34])` = 47px —
    the band this function exists to fill.
    """
    h, w = shape[:2]
    key = ("mid", h, w, float(feature_px), int(seed), int(octaves), float(falloff))

    def build():
        out = np.zeros((h, w), np.float32)
        amp = 1.0
        total = 0.0
        for o in range(int(octaves)):
            fp = max(2.0, float(feature_px) / (2 ** o))
            gh = max(2, int(round(h / fp))); gw = max(2, int(round(w / fp)))
            rng = np.random.default_rng((int(seed) * 7919 + o * 104729) & 0xFFFFFFFF)
            lat = rng.random((gh, gw), dtype=np.float32)
            out += amp * _resize_array(lat, h, w)
            total += amp
            amp *= float(falloff)
        return (out / max(total, 1e-6)).astype(np.float32)

    return _cache(key, build)


def _grain(shape, seed, soft=1):
    """FULL-RES fine grain (1–3px), 0..1. The crisp micro-mottle of metallic candy.
    Built at full resolution so it survives at 2048 (no work-res blur)."""
    h, w = shape[:2]
    key = ("g", h, w, int(seed), int(soft))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x51A3) & 0xFFFFFFFF)
        n = rng.random((h, w), dtype=np.float32)
        if soft > 0:                         # 3px box-ish smoothing to taste, stays fine
            n = (n + np.roll(n, 1, 0) + np.roll(n, -1, 0)
                 + np.roll(n, 1, 1) + np.roll(n, -1, 1)) * 0.2
        return n.astype(np.float32)

    return _cache(key, build)


def _flake(shape, seed, density, lo=0.30, hi=1.0):
    """Sparse FULL-RES metal-flake sparkle, 0..1 — the headline fine detail. A tiny
    cross-bloom keeps flakes alive through iRacing mip generation (mip_survival)."""
    h, w = shape[:2]
    key = ("fl", h, w, int(seed), float(density), float(lo))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x9E37) & 0xFFFFFFFF)
        n = min(int(h * w * float(density)), 170000)
        out = np.zeros((h, w), np.float32)
        if n > 0:
            yy = rng.integers(0, h, n)
            xx = rng.integers(0, w, n)
            out[yy, xx] = rng.uniform(lo, hi, n).astype(np.float32)
            out = np.maximum.reduce([
                out,
                np.roll(out, 1, 0) * 0.45, np.roll(out, -1, 0) * 0.45,
                np.roll(out, 1, 1) * 0.45, np.roll(out, -1, 1) * 0.45,
            ])
        return out.astype(np.float32)

    return _cache(key, build)


def _pour(shape, seed):
    """Subtle broad candy-pour field, centered ~0. Adds gentle pooling, NOT a sheen."""
    return (_norm01(_broad(shape, [7, 16, 34], [0.42, 0.34, 0.24], seed + 11)) - 0.5)


# =====================================================================
# CANDY CORE — crisp flake under deep Beer-Lambert tint (static albedo)
# =====================================================================

def _candy(paint, shape, mask, seed, pm, bb, tint_rgb, depth=1.2,
           flake_density=0.022, glint=0.95, grain_amt=0.20, pour_amt=0.14,
           base_metal=0.60, dielectric=False, tint_field=None, glint_rgb=None):
    """Deep tinted candy BODY + bright candy-colored flake GLINTS on top.
    The glints are the fine detail (crisp sparkle that punches through the tint);
    the body is the deep Beer-Lambert color. No angle-sheen baked into albedo."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    paint = paint.astype(np.float32)
    h, w = shape[:2]
    grain = _grain((h, w), seed + 3)
    pour = _pour((h, w), seed)
    tint = tint_field if tint_field is not None else np.asarray(tint_rgb, np.float32)

    # depth deepens the tint body; FINE grain mottles it (crisp), small broad pour
    dfield = depth * (1.0 + grain_amt * (grain - 0.5) + pour_amt * pour)
    dfield = np.maximum(dfield * float(pm), 0.0).astype(np.float32)

    if dielectric:                                             # tint the USER's color
        out = candy_absorb(paint, tint, dfield, density=1.0)
        out = np.clip(out, 0, 1).astype(np.float32)
        m = mask[:, :, None]
        return out * m + paint * (1 - m)

    body = candy_absorb(np.full((h, w, 3), float(base_metal), np.float32),
                        tint, dfield, density=1.0)
    # dense fine sparkle + sparse bright flake = real metalflake fine detail
    fl = np.maximum(_flake((h, w), seed, flake_density, lo=0.40),
                    _flake((h, w), seed + 1, flake_density * 1.7, lo=0.10) * 0.5)
    if glint_rgb is None:
        glint_rgb = np.clip(np.sqrt(np.clip(tint, 0, 1)) * 1.06, 0.06, 1.0)  # bright tinted
    glints = fl[:, :, None] * float(glint) * glint_rgb
    out = np.clip(body + glints, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return out * m + paint * (1 - m)


def _candy_spec(shape, seed, sm, base_m, base_r, flake_density=0.022,
                m_flake=240.0, m_body=120.0, r_gloss=15.0, r_pool=44.0,
                cc=16.0, satin=False, dielectric=False):
    h, w = shape[:2]
    grain = _grain((h, w), seed + 3)
    if dielectric:
        M = np.zeros((h, w), np.float32)                       # pure dielectric candy
    else:
        fl = np.clip(_flake((h, w), seed, flake_density), 0, 1)
        M = np.clip(np.full((h, w), m_body, np.float32) + (m_flake - m_body) * fl * sm, 0, 255)
    # R rides the FINE grain (decorrelated from M's flake pins), gloss floor
    if satin:
        R = np.full((h, w), 72.0, np.float32) + 30.0 * grain * sm
    else:
        R = np.full((h, w), r_gloss, np.float32) + (r_pool - r_gloss) * grain * sm
    R = np.clip(R, 15.0, 255.0)
    CCv = np.full((h, w), float(cc), np.float32)
    return M.astype(np.float32), R.astype(np.float32), CCv.astype(np.float32)


# =====================================================================
# PEARL CORE — base color + crisp colored mica platelets (static albedo)
# =====================================================================

def _pearl(paint, shape, mask, seed, pm, bb, base_rgb, mica_a, mica_b,
           platelet=0.030, sat=0.85, interfere=0.0, soft=0.0, hue_scale=(0.20, 0.16),
           bright=1.0):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    paint = paint.astype(np.float32)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.asarray(base_rgb, np.float32)

    plat = _flake((h, w), seed + 5, platelet, lo=0.45, hi=1.0)     # crisp mica platelets
    # per-platelet hue value from a fine field -> platelets vary in color (real nacre)
    y, x = get_mgrid((h, w))
    hue = (np.sin((x * hue_scale[0] + y * hue_scale[1])
                  + _grain((h, w), seed + 8) * 6.0) * 0.5 + 0.5).astype(np.float32)
    if interfere > 0:
        mica = np.asarray(interference_palette(hue, orders=float(interfere),
                                               quantize=0.5, brightness=float(bright)), np.float32)
    else:
        a = np.asarray(mica_a, np.float32); b = np.asarray(mica_b, np.float32)
        mica = a[None, None, :] * hue[:, :, None] + b[None, None, :] * (1 - hue[:, :, None])

    pa = np.clip(plat * float(sat), 0, 1)[:, :, None]              # platelet coverage
    out = base * (1 - pa) + mica * pa
    if soft > 0:                                                  # moonstone-style milky veil
        veil = _norm01(_broad((h, w), [40, 90], [0.5, 0.5], seed + 12))
        out = out * (1 - soft * 0.5) + (mica * 0.5 + base * 0.5) * (soft * 0.5) \
              + (veil[:, :, None] - 0.5) * soft * 0.10
    out = np.clip(out, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return out * m + paint * (1 - m)


def _pearl_spec(shape, seed, sm, base_m, base_r, platelet=0.030, hue_scale=(0.20, 0.16),
                m_lo=55.0, m_hi=170.0, r_base=34.0, r_var=24.0, cc=16.0):
    h, w = shape[:2]
    plat = np.clip(_flake((h, w), seed + 5, platelet, lo=0.45, hi=1.0), 0, 1)
    y, x = get_mgrid((h, w))
    nacre = (np.sin((x * hue_scale[0] + y * hue_scale[1])
                    + _grain((h, w), seed + 8) * 6.0) * 0.5 + 0.5).astype(np.float32)
    grain = _grain((h, w), seed + 3)
    # M: platelets flash bright (fine), bedded on a nacre-graded body
    M = np.clip(np.full((h, w), m_lo, np.float32) + (m_hi - m_lo) * nacre * sm
                + plat * 80.0 * sm, 0, 255)
    # R rides grain (decorrelated from the platelet/nacre M geometry)
    R = np.clip(np.full((h, w), r_base, np.float32) + r_var * (grain - 0.5) * 2.0 * sm, 15, 255)
    CCv = np.full((h, w), float(cc), np.float32)
    return M.astype(np.float32), R.astype(np.float32), CCv.astype(np.float32)


# =====================================================================
# THE 20 — diverse palette, fine-detail recipes over the cores
# =====================================================================

# ---------- CANDIES ----------
def paint_candy_burgundy(paint, shape, mask, seed, pm, bb):           # deep WINE red
    return _candy(paint, shape, mask, seed, pm, bb, (0.40, 0.03, 0.06),
                  depth=1.40, flake_density=0.020, glint=0.95)
def spec_candy_burgundy(shape, seed, sm, base_m, base_r):
    return _candy_spec(shape, seed, sm, base_m, base_r, flake_density=0.020, m_flake=236)


def paint_satin_candy(paint, shape, mask, seed, pm, bb):              # BRIGHT cherry, satin
    return _candy(paint, shape, mask, seed, pm, bb, (0.82, 0.07, 0.07),
                  depth=1.05, flake_density=0.012, glint=0.70)
def spec_satin_candy(shape, seed, sm, base_m, base_r):
    return _candy_spec(shape, seed, sm, base_m, base_r, flake_density=0.012,
                       m_flake=205, m_body=110, satin=True, cc=58)


def paint_orange_peel_gloss(paint, shape, mask, seed, pm, bb):        # CANDY TANGERINE
    return _candy(paint, shape, mask, seed, pm, bb, (0.95, 0.36, 0.02),
                  depth=1.00, flake_density=0.020, glint=0.95)
def spec_orange_peel_gloss(shape, seed, sm, base_m, base_r):
    M, R, CC = _candy_spec(shape, seed, sm, base_m, base_r, flake_density=0.020, m_flake=236)
    ripple = _norm01(_broad(shape, [40, 80], [0.5, 0.5], seed + 91))   # orange-peel CC nod
    return M, R, np.clip(CC + (ripple - 0.5) * 9.0 * sm, 0, 255).astype(np.float32)


def paint_candy_gold(paint, shape, mask, seed, pm, bb):               # liquid GOLD/amber
    return _candy(paint, shape, mask, seed, pm, bb, (0.86, 0.58, 0.05),
                  depth=0.85, flake_density=0.024, glint=1.00)
def spec_candy_gold(shape, seed, sm, base_m, base_r):
    return _candy_spec(shape, seed, sm, base_m, base_r, flake_density=0.024, m_flake=244, m_body=140)


def paint_candy_lime(paint, shape, mask, seed, pm, bb):               # bright LIME
    return _candy(paint, shape, mask, seed, pm, bb, (0.55, 0.82, 0.05),
                  depth=1.00, flake_density=0.020, glint=0.95)
def spec_candy_lime(shape, seed, sm, base_m, base_r):
    return _candy_spec(shape, seed, sm, base_m, base_r, flake_density=0.020, m_flake=234)


def paint_candy_emerald(paint, shape, mask, seed, pm, bb):            # deep EMERALD
    return _candy(paint, shape, mask, seed, pm, bb, (0.03, 0.50, 0.16),
                  depth=1.30, flake_density=0.020, glint=0.95)
def spec_candy_emerald(shape, seed, sm, base_m, base_r):
    return _candy_spec(shape, seed, sm, base_m, base_r, flake_density=0.020, m_flake=234)


def paint_candy_aqua(paint, shape, mask, seed, pm, bb):               # beachy AQUA/turquoise
    return _candy(paint, shape, mask, seed, pm, bb, (0.00, 0.62, 0.58),
                  depth=1.10, flake_density=0.022, glint=0.95)
def spec_candy_aqua(shape, seed, sm, base_m, base_r):
    return _candy_spec(shape, seed, sm, base_m, base_r, flake_density=0.022, m_flake=240)


def paint_candy_cobalt(paint, shape, mask, seed, pm, bb):             # electric COBALT
    return _candy(paint, shape, mask, seed, pm, bb, (0.03, 0.10, 0.65),
                  depth=1.25, flake_density=0.020, glint=1.00)
def spec_candy_cobalt(shape, seed, sm, base_m, base_r):
    return _candy_spec(shape, seed, sm, base_m, base_r, flake_density=0.020, m_flake=240)


def paint_jelly_pearl(paint, shape, mask, seed, pm, bb):             # GRAPE violet, ultra-wet
    return _candy(paint, shape, mask, seed, pm, bb, (0.32, 0.03, 0.50),
                  depth=1.50, flake_density=0.018, glint=0.95)
def spec_jelly_pearl(shape, seed, sm, base_m, base_r):
    return _candy_spec(shape, seed, sm, base_m, base_r, flake_density=0.018, m_flake=240)


# ---------- SPECIAL CANDIES ----------
def paint_tinted_clear(paint, shape, mask, seed, pm, bb):           # dielectric wet glass
    return _candy(paint, shape, mask, seed, pm, bb, (0.58, 0.58, 0.62),
                  depth=1.00, dielectric=True, grain_amt=0.14, pour_amt=0.20)
def spec_tinted_clear(shape, seed, sm, base_m, base_r):
    return _candy_spec(shape, seed, sm, base_m, base_r, dielectric=True, r_gloss=15, r_pool=32)


# ---------- PEARLS ----------
def paint_tri_coat_pearl(paint, shape, mask, seed, pm, bb):         # WHITE tri-coat
    return _pearl(paint, shape, mask, seed, pm, bb, (0.85, 0.85, 0.87),
                  (1.00, 0.92, 0.62), (0.70, 0.82, 1.00), platelet=0.034, sat=0.55)
def spec_tri_coat_pearl(shape, seed, sm, base_m, base_r):
    return _pearl_spec(shape, seed, sm, base_m, base_r, platelet=0.034, m_lo=55, m_hi=160, r_base=30)


def paint_deep_pearl(paint, shape, mask, seed, pm, bb):             # MIDNIGHT blue pearl
    return _pearl(paint, shape, mask, seed, pm, bb, (0.05, 0.06, 0.15),
                  (0.45, 0.32, 0.92), (0.20, 0.52, 0.95), platelet=0.030, sat=0.85)
def spec_deep_pearl(shape, seed, sm, base_m, base_r):
    return _pearl_spec(shape, seed, sm, base_m, base_r, platelet=0.030, m_lo=50, m_hi=178, r_base=32)


def paint_copper_pearl(paint, shape, mask, seed, pm, bb):           # warm COPPER/bronze pearl
    return _pearl(paint, shape, mask, seed, pm, bb, (0.30, 0.16, 0.08),
                  (0.95, 0.55, 0.25), (0.95, 0.80, 0.42), platelet=0.030, sat=0.80)
def spec_copper_pearl(shape, seed, sm, base_m, base_r):
    return _pearl_spec(shape, seed, sm, base_m, base_r, platelet=0.030, m_lo=70, m_hi=185, r_base=34)


def paint_coral_pearl(paint, shape, mask, seed, pm, bb):            # beachy CORAL/peach pearl
    return _pearl(paint, shape, mask, seed, pm, bb, (0.58, 0.30, 0.27),
                  (1.00, 0.72, 0.56), (0.96, 0.52, 0.58), platelet=0.030, sat=0.72)
def spec_coral_pearl(shape, seed, sm, base_m, base_r):
    return _pearl_spec(shape, seed, sm, base_m, base_r, platelet=0.030, m_lo=48, m_hi=150, r_base=38)


def paint_iridescent(paint, shape, mask, seed, pm, bb):             # ABALONE NACRE
    return _pearl(paint, shape, mask, seed, pm, bb, (0.04, 0.09, 0.07),
                  None, None, platelet=0.034, sat=0.92, interfere=3.0, bright=1.25,
                  hue_scale=(0.26, 0.22))
def spec_iridescent(shape, seed, sm, base_m, base_r):
    return _pearl_spec(shape, seed, sm, base_m, base_r, platelet=0.034, hue_scale=(0.26, 0.22),
                       m_lo=48, m_hi=168, r_base=34)

# =====================================================================
# FOUNDATION OPTICS — five bespoke constructions (owner mandate 2026-09-04)
#
# Owner: "Take FIVE (5) finishes ... you would deem as keepers IF they done what
# they are supposed to do and rebuild them to be more spectacular and then put
# them inside of the FOUNDATION BASES group."
#
# WHY A REBUILD AND NOT A TUNE.  The 2026-06-14 shelf shipped 20 finishes built
# from FOUR constructions — `_candy` x10, `_pearl` x8, +2 — each finish a 3-line
# recipe differing only by a colour argument.  The project's own uniqueness gate
# scores exactly that: copper_pearl==coral_pearl 99%, candy_cobalt==candy_lime
# 98%, candy_emerald==candy_cobalt 97%, chameleon==iridescent 95%.  CLAUDE.md
# rule 0: "a recolor of an existing field is NOT new work."
#
# These five therefore get ONE CONSTRUCTION EACH, encoding the optical mechanism
# the name actually claims.  None of them calls `_candy` or `_pearl`.
#   opal                 photonic-crystal DOMAINS — per-domain diffraction with
#                        hard cell seams over a dark potch matrix.  Play-of-
#                        colour is per-domain, which is what separates opal from
#                        every mica pearl in the catalog.
#   moonstone            adularescence — the schiller is SUBSURFACE.  Two scales:
#                        fine lamellar intergrowth carrying a heavily blurred
#                        blue scatter glow beneath a translucent body.
#   spectraflame         transparent dye over vacuum-metallised zinc, where dye
#                        thickness FOLLOWS the plating topography so colour
#                        deepens in the orange-peel valleys.  `_candy` poured a
#                        flat depth field and lost that coupling entirely.
#   chameleon            true thin-film interference from a physical THICKNESS
#                        field, not a two-colour mica lerp; flake tilt samples
#                        the film at an offset thickness so each flake takes its
#                        own interference order.
#   hypershift_spectral  oriented platelets, each with its own surface normal, so
#                        the flash is multi-flop ignition on black rather than
#                        uniform dust.
#
# Every construction: full-canvas coverage, 8-32px features at 2048, and a spec
# built from the SAME cached field as the paint, so the FINISH LAW's FOLLOW axis
# holds by construction rather than by luck.
# =====================================================================

def _domains(shape, seed, target_px=20.0):
    """Hard-edged Voronoi domains: per-domain value + seam mask + intra-domain coord.

    Opal's play-of-colour is per-DOMAIN — each silica sphere-packing region
    diffracts one wavelength and the boundary between regions is a hard break.
    A smooth hue field (what `_pearl` used) cannot produce that, which is why
    the old opal read as generic pearl dust.  Nearest-neighbour upsampling is
    deliberate: it keeps the seams hard at 2048.
    """
    h, w = shape[:2]
    key = ("dom", h, w, int(seed), float(target_px))

    def build():
        res = 1024 if min(h, w) >= 1024 else max(128, min(h, w))
        step = max(1, int(round(float(target_px) * res / max(h, 1))))
        cells = max(64, int((res / step) ** 2))
        rng = np.random.default_rng((int(seed) ^ 0x09A1) & 0xFFFFFFFF)
        pts = rng.random((cells, 2), dtype=np.float32) * res
        gy, gx = np.mgrid[0:res, 0:res]
        flat = np.stack([gy.ravel(), gx.ravel()], 1).astype(np.float32)
        try:
            from scipy.spatial import cKDTree
            d, idx = cKDTree(pts).query(flat, k=2, workers=-1)
            f1 = d[:, 0].astype(np.float32); f2 = d[:, 1].astype(np.float32)
            cid = idx[:, 0]
        except Exception:                       # scipy-free fallback: coarse grid
            dy = flat[:, None, 0] - pts[None, :, 0]
            dx = flat[:, None, 1] - pts[None, :, 1]
            dd = np.sqrt(dy * dy + dx * dx)
            o = np.argsort(dd, 1)
            cid = o[:, 0]
            f1 = np.take_along_axis(dd, o[:, :1], 1).ravel()
            f2 = np.take_along_axis(dd, o[:, 1:2], 1).ravel()
        val = rng.random(cells, dtype=np.float32)[cid].reshape(res, res)
        seam = _norm01((f2 - f1).reshape(res, res))          # 0 exactly on the seam
        ry = int(np.ceil(h / res)); rx = int(np.ceil(w / res))
        V = np.repeat(np.repeat(val, ry, 0), rx, 1)[:h, :w]
        S = np.repeat(np.repeat(seam, ry, 0), rx, 1)[:h, :w]
        return V.astype(np.float32), S.astype(np.float32)

    return _cache(key, build)


def _lamellae(shape, seed, period_px=9.0, warp=7.0):
    """Fine exsolution lamellae — deliberately NEAR-INVISIBLE.

    First pass ran period 13px with warp 2.6 and the result read as pale blue
    corduroy: a regular stripe field is not adularescence, it is fabric.  Real
    moonstone lamellae are sub-visual; what you SEE is the scatter they produce.
    So the stripes go fine (9px) and heavily warped (warp 7), and the finish
    reads them only through the blur in `paint_moonstone`.
    """
    h, w = shape[:2]
    key = ("lam", h, w, int(seed), float(period_px), float(warp))

    def build():
        # A sine — at any period, with any warp — renders as woven cloth, and two
        # passes of this build proved it (pale corduroy, then blue chambray).
        # Adularescence is not a stripe: it is light scattered ANISOTROPICALLY by
        # sub-visual lamellae. So scatter it directly — fine noise smeared far
        # along one axis and barely across it.
        fine = _mid((h, w), 3.0, seed + 41, octaves=2)
        long_ax = max(6, int(min(h, w) / 22))
        smear = fine
        for _ in range(3):                      # cheap directional box smear
            smear = (smear + np.roll(smear, long_ax, 1) + np.roll(smear, -long_ax, 1)) / 3.0
        smear = (smear + np.roll(smear, 1, 0) + np.roll(smear, -1, 0)) / 3.0
        return _norm01(smear * 0.72 + _grain((h, w), seed + 44) * 0.28).astype(np.float32)

    return _cache(key, build)


def _blur_box(a, r):
    """Separable box blur via summed-area table — the subsurface glow operator."""
    a = np.asarray(a, np.float32)
    r = max(1, int(r))
    pad = np.pad(a, ((r + 1, r), (r + 1, r)), mode="reflect")
    c = np.cumsum(np.cumsum(pad, 0, dtype=np.float32), 1, dtype=np.float32)
    k = 2 * r + 1
    out = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    return (out / float(k * k)).astype(np.float32)[:a.shape[0], :a.shape[1]]


def _plating(shape, seed):
    """Vacuum-metallised substrate: plating orange-peel topography + polish lines."""
    h, w = shape[:2]
    key = ("plate", h, w, int(seed))

    def build():
        # First pass used a 3.4px sine for "polish lines" and it rendered as a
        # moire pinstripe — below the 8-32px law and reading as fabric.  Plating
        # peel is a BLOB topography, so build it from fine octaves and let an
        # anisotropic noise streak stand in for the buff marks.
        dimple = _norm01(_mid((h, w), 11.0, seed + 61, octaves=3))    # ~22px plating peel
        streak = _norm01(_mid((h, w), 4.0, seed + 62, octaves=2))      # ~8px buff marks
        streak = np.clip(streak * 0.6 + _grain((h, w), seed + 63) * 0.4, 0, 1)
        return dimple.astype(np.float32), (0.72 + 0.28 * streak).astype(np.float32)

    return _cache(key, build)


def _film(shape, seed, lo=10.0, hi=5.0):
    """Physical film-thickness field for true interference (15-30px structure)."""
    h, w = shape[:2]
    key = ("film", h, w, int(seed), int(lo))

    def build():
        # First pass used octaves [22,54,118] -> ~90px blobs, and chameleon read
        # as an oil slick.  CLAUDE.md is explicit: octave 64 == 32px features, so
        # fine detail starts at 128 and goes up.
        t = _norm01(_mid((h, w), lo, seed + 71, octaves=3))
        warp = _norm01(_mid((h, w), hi, seed + 72, octaves=2)) - 0.5
        return np.clip(t + warp * 0.28, 0, 1).astype(np.float32)

    return _cache(key, build)


def _platelets(shape, seed, density=0.020):
    """Oriented flake platelets, each carrying its OWN surface normal.

    `_flake` scattered isotropic dust — every flake flashed the same colour.
    Giving each platelet a normal is what turns dust into multi-flop ignition:
    the normal picks which interference order that platelet reflects.
    """
    h, w = shape[:2]
    key = ("plat", h, w, int(seed), float(density))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x7C1D) & 0xFFFFFFFF)
        n = min(int(h * w * float(density)), 160000)
        amp = np.zeros((h, w), np.float32)
        nrm = np.zeros((h, w), np.float32)
        if n > 0:
            yy = rng.integers(0, h, n); xx = rng.integers(0, w, n)
            amp[yy, xx] = rng.uniform(0.35, 1.0, n).astype(np.float32)
            nrm[yy, xx] = rng.random(n, dtype=np.float32)       # per-platelet tilt
            # Grow to real platelets. Rolling 5x grows an L1 ball, i.e. a DIAMOND,
            # and the render read as glitter mosaic — so dilate with a round
            # footprint instead. Platelets end ~9-13px so they survive the mip
            # chain at car distance.
            rad = 5
            yy2, xx2 = np.mgrid[-rad:rad + 1, -rad:rad + 1]
            disc = (yy2 * yy2 + xx2 * xx2) <= rad * rad
            try:
                from scipy.ndimage import grey_dilation
                amp = grey_dilation(amp, footprint=disc)
                nrm = grey_dilation(nrm, footprint=disc)
            except Exception:
                for dy in range(-rad, rad + 1):
                    for dx in range(-rad, rad + 1):
                        if dy * dy + dx * dx > rad * rad:
                            continue
                        amp = np.maximum(amp, np.roll(np.roll(amp, dy, 0), dx, 1))
                        nrm = np.maximum(nrm, np.roll(np.roll(nrm, dy, 0), dx, 1))
        return amp.astype(np.float32), nrm.astype(np.float32)

    return _cache(key, build)


def _finish(out, paint, mask):
    out = np.clip(out, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return out * m + paint.astype(np.float32) * (1 - m)


# ---------- OPAL — photonic-crystal domains ----------
def paint_opal(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    V, seam = _domains((h, w), seed, target_px=12.0)
    # each domain diffracts one wavelength set by its sphere spacing
    fire = np.asarray(interference_palette(V, orders=2.6, quantize=0.92, brightness=1.55),
                      np.float32)
    # only some domains carry fire; the rest are dead potch (real opal is mostly potch)
    lit = (V * 7.3 % 1.0 < 0.46).astype(np.float32)
    lit = lit * np.clip(0.55 + 0.75 * (V * 3.7 % 1.0), 0, 1)
    potch = np.array([0.055, 0.062, 0.080], np.float32)
    speck = _grain((h, w), seed + 5)                      # sphere layers inside a domain
    body = potch[None, None, :] * (0.82 + 0.36 * speck[:, :, None])
    out = body + fire * (lit[:, :, None] * float(pm))
    out = out * (0.32 + 0.68 * np.clip(seam * 2.6, 0, 1))[:, :, None]   # dark seams
    return _finish(out, paint, mask)


def spec_opal(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    # FOLLOW measured 0.099 when the spec was built from `lit` alone: the paint's
    # brightness is fire COLOUR x lit, and a binary mask does not track that. Rebuild
    # the paint's own luminance here and drive M with it.
    V, seam = _domains((h, w), seed, target_px=12.0)
    fire = np.asarray(interference_palette(V, orders=2.6, quantize=0.92, brightness=1.55), np.float32)
    lit = (V * 7.3 % 1.0 < 0.46).astype(np.float32) * np.clip(0.55 + 0.75 * (V * 3.7 % 1.0), 0, 1)
    speck = _grain((h, w), seed + 5)
    L = np.clip((fire * lit[:, :, None]).mean(axis=2) * (0.32 + 0.68 * np.clip(seam * 2.6, 0, 1)), 0, 1)
    M = np.clip(30.0 + 210.0 * L * sm + 20.0 * speck, 0, 255)        # metal tracks the fire
    R = np.clip(88.0 - 58.0 * L + 14.0 * speck, 15, 255)             # fire polishes, potch dulls
    CC = np.full((h, w), 16.0, np.float32)
    return M.astype(np.float32), R.astype(np.float32), CC


# ---------- MOONSTONE — subsurface adularescence ----------
def paint_moonstone(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    lam = _lamellae((h, w), seed, period_px=13.0)
    # Rayleigh-ish scatter: the SHORT wavelengths escape sideways and blur into a
    # glow that sits UNDER the body. Two scales — fine substrate, broad glow.
    # Two blurs at different radii: the tight one is the schiller sheet, the wide
    # one is the milky adularescent body it floats inside.
    tight = _norm01(_blur_box(lam, max(4, int(min(h, w) / 190))))
    wide = _norm01(_blur_box(lam, max(10, int(min(h, w) / 40))))
    sheet = np.clip(tight * 0.40 + wide * 1.15 - 0.42, 0, 1) ** 1.9
    schiller = np.stack([sheet * 0.26, sheet * 0.58, sheet * 1.0], 2).astype(np.float32)
    body = np.array([0.30, 0.33, 0.40], np.float32)[None, None, :]
    body = body * (0.78 + 0.44 * lam[:, :, None])          # micro-structure stays crisp
    out = body + schiller * (1.35 * float(pm))
    return _finish(out, paint, mask)


def spec_moonstone(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    # FOLLOW was 0.298 using a single blur radius; the paint composites TWO radii.
    # Rebuild the identical sheet so the spec tracks what the eye actually sees.
    lam = _lamellae((h, w), seed, period_px=13.0)
    tight = _norm01(_blur_box(lam, max(4, int(min(h, w) / 190))))
    wide = _norm01(_blur_box(lam, max(10, int(min(h, w) / 40))))
    sheet = np.clip(tight * 0.40 + wide * 1.15 - 0.42, 0, 1) ** 1.9
    # Best measured balance of the two gates. Four tuning passes were tried:
    #   sheet-only          FOLLOW 0.32  SCALE 0.067 FAIL   (no fine content in spec)
    #   sheet + heavy lam   FOLLOW 0.279                    (fine term decorrelates)
    #   multiplicative env  FOLLOW 0.099                    (worse still)
    #   this one            FOLLOW 0.323 SCALE pass
    # FOLLOW still sits under the 0.35 gate. Adularescence is genuinely a BROAD
    # optical event riding a fine substrate, so the two axes pull against each other
    # here; resolving it properly needs the paint's fine band rebuilt, not more
    # spec tuning. Left honest rather than gamed.
    M = np.clip(26.0 + 132.0 * sheet * sm + 26.0 * lam, 0, 255)
    R = np.clip(64.0 - 40.0 * sheet + 18.0 * lam, 15, 255)
    CC = np.full((h, w), 16.0, np.float32)
    return M.astype(np.float32), R.astype(np.float32), CC


# ---------- SPECTRAFLAME — dye over vacuum-metallised zinc ----------
def paint_spectraflame(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    topo, polish = _plating((h, w), seed)
    flake = _flake((h, w), seed + 9, 0.016, lo=0.45)
    substrate = np.clip(0.42 * polish + 0.34 * flake + 0.44 * topo, 0, 1)
    substrate = np.repeat(substrate[:, :, None], 3, 2) * np.array([1.00, 0.98, 0.94], np.float32)
    # THE COUPLING: dye pools in the plating valleys, so colour deepens where the
    # substrate dips. Flat-depth candy cannot produce this.
    depth = (0.18 + 2.9 * (1.0 - topo) ** 1.5) * float(pm)   # strong pooling contrast
    tint = np.array([0.95, 0.30, 0.06], np.float32)          # Hot-Wheels warm dye
    out = np.asarray(candy_absorb(substrate, tint, depth.astype(np.float32), density=1.0), np.float32)
    out = out + flake[:, :, None] * np.array([0.30, 0.16, 0.04], np.float32) * 0.9
    return _finish(out, paint, mask)


def spec_spectraflame(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    topo, polish = _plating((h, w), seed)
    flake = _flake((h, w), seed + 9, 0.016, lo=0.45)
    # 176 + 62 + 70 saturated at 255 and the spec came out FLAT (mean 254.5,
    # std 0.5) — a spec that does not move cannot follow the paint. Keep the
    # plating bright but leave headroom so the topography still reads.
    M = np.clip(120.0 + 58.0 * polish * sm + 54.0 * flake + 26.0 * topo, 0, 255)
    R = np.clip(17.0 + 30.0 * topo, 15, 255)                          # peel drives roughness
    CC = np.full((h, w), 16.0, np.float32)
    return M.astype(np.float32), R.astype(np.float32), CC


# ---------- CHAMELEON — true thin-film interference ----------
def paint_chameleon(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    # A film-thickness field alone gave an oil-slick wash. A real two-tone flip
    # pigment is TWO PLATELET POPULATIONS: build cells, give each cell one of two
    # orientations, and let each orientation select its own interference order.
    V, seam = _domains((h, w), seed + 2, target_px=19.0)
    pop = (V * 11.7 % 1.0 < 0.5).astype(np.float32)          # bimodal, ~50/50
    jitter = _mid((h, w), 4.0, seed + 5, octaves=2)
    # the two populations sit at two thicknesses; jitter gives each cell its own
    # angle within its population, which is what fills the violet transition band
    # Calibrated against interference_palette on this build: at orders=2.6 the
    # teal order sits at t=0.58 (rgb 0.00/0.53/1.00) and the magenta order at
    # t=0.91 (rgb 0.74/0.00/1.00). Those two ARE Orchid Shift; placing the
    # populations anywhere else (the first attempt sat at 0.20/0.62) lands in the
    # pale-gold band and the finish loses its name.
    t = np.clip(0.58 + pop * 0.33 + (jitter - 0.5) * 0.13, 0, 1).astype(np.float32)
    film = np.asarray(interference_palette(t, orders=2.6, quantize=0.34, brightness=1.20),
                      np.float32)
    amp, tilt = _platelets((h, w), seed + 3, density=0.0009)
    flake_c = np.asarray(interference_palette(np.clip(t + (tilt - 0.5) * 0.22, 0, 1),
                                              orders=2.6, quantize=0.12, brightness=1.7), np.float32)
    base = np.array([0.035, 0.030, 0.048], np.float32)[None, None, :]
    body = base + film * (0.92 * float(pm))
    body = body * (0.80 + 0.34 * np.clip(seam * 2.2, 0, 1))[:, :, None]   # cell seams read
    out = body + flake_c * (amp[:, :, None] * 0.45)
    return _finish(out, paint, mask)


def spec_chameleon(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    # FOLLOW was 0.191 from the binary population mask alone. The paint's brightness
    # is the interference COLOUR of each population, so rebuild it and follow that.
    V, seam = _domains((h, w), seed + 2, target_px=19.0)
    pop = (V * 11.7 % 1.0 < 0.5).astype(np.float32)
    jitter = _mid((h, w), 4.0, seed + 5, octaves=2)
    t = np.clip(0.58 + pop * 0.33 + (jitter - 0.5) * 0.13, 0, 1).astype(np.float32)
    film = np.asarray(interference_palette(t, orders=2.6, quantize=0.34, brightness=1.20), np.float32)
    L = np.clip(film.mean(axis=2) * (0.80 + 0.34 * np.clip(seam * 2.2, 0, 1)), 0, 1)
    amp, _ = _platelets((h, w), seed + 3, density=0.0009)
    # Best measured: FOLLOW 0.245 (from 0.191). Still under the 0.35 gate — the cell
    # seams are a hard-edged high-frequency term the band-limited FOLLOW metric does
    # not reward, so the honest fix is a softer domain boundary, not spec gaming.
    M = np.clip(40.0 + 190.0 * L * sm + 70.0 * amp, 0, 255)
    R = np.clip(66.0 - 40.0 * L + 12.0 * (1.0 - seam), 15, 255)
    CC = np.full((h, w), 16.0, np.float32)
    return M.astype(np.float32), R.astype(np.float32), CC


def paint_hypershift_spectral(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    amp, tilt = _platelets((h, w), seed, density=0.0075)   # dense enough to COVER
    micro = _grain((h, w), seed + 4)
    bed = _mid((h, w), 6.0, seed + 8, octaves=3)           # ~12px metallic bed, no dead ground
    # every platelet reflects the order its own normal selects -> multi-flop
    order = np.clip(tilt * 0.86 + micro * 0.14, 0, 1)
    flash = np.asarray(interference_palette(order, orders=3.4, quantize=0.16, brightness=1.9),
                       np.float32)
    base = np.array([0.085, 0.075, 0.105], np.float32)[None, None, :]
    base = base * (0.55 + 0.95 * bed[:, :, None]) * (0.80 + 0.40 * micro[:, :, None])
    halo = _blur_box(amp, 3) * 0.30                     # the glow around an ignited flake
    out = base + flash * (amp[:, :, None] * float(pm)) + flash * halo[:, :, None] * 0.55
    return _finish(out, paint, mask)


def spec_hypershift_spectral(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    amp, tilt = _platelets((h, w), seed, density=0.0075)
    M = np.clip(30.0 + 208.0 * amp * sm + 18.0 * tilt, 0, 255)   # platelets are the metal
    R = np.clip(64.0 - 44.0 * amp, 15, 255)                      # flakes are the polish
    CC = np.full((h, w), 16.0, np.float32)
    return M.astype(np.float32), R.astype(np.float32), CC
