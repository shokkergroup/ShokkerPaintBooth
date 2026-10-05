# -*- coding: utf-8 -*-
"""
engine/paint_v2/flames_2026.py - ★ FLAMES (rebuilt bespoke, 2026-06-15)

20 fire treatments, EVERY ONE its own algorithm + its own motif. NO shared
flame template, NO recolor clones. The earlier build was a single _fire_field +
_flame + _flame_spec factory driven by a per-id palette dict -> two big groups of
~7 recolors. That is torn out. Each finish below recomputes its own geometric
fields; each spec_<id> recomputes the SAME fields the paint used (same seed, same
helpers) so the shimmer IGNITES the exact flame features the paint shows, and
rides M / R / CC on DIFFERENT geometry with DIFFERENT value distributions so the
combined map (R=M, G=R, B=CC) reads as MANY hues - orange/yellow/red/blue/violet/
teal - not flat red+green.

Contracts (unchanged):
  paint_<id>(paint, shape, mask, seed, pm, bb) -> HxWx3 float32 [0,1]
  spec_<id>(shape, seed, sm, base_m, base_r) -> (M, R, CC) each float32 HxW 0..255
     M = metalness, R = roughness (FLOOR 15), CC = clearcoat (16 = wet gloss).
     sm scales contrast. All < 3s @2048 via work-res caps + windowed splats.

KEEP ids + function names + signatures (registry resolves by name).
"""
import numpy as np

try:
    import cv2 as _cv2
    _CV2 = True
except Exception:  # pragma: no cover
    _cv2 = None
    _CV2 = False

from engine.core import multi_scale_noise, get_mgrid, _resize_array, hsv_to_rgb_vec

# ---------------------------------------------------------------------------
# small shared MATH primitives only (no shared "flame template" / palette dict).
# Every finish below builds its OWN field geometry from these atoms.
# ---------------------------------------------------------------------------
_CACHE = {}
_WORK_CAP = 560          # broad smooth fields computed here then upsampled
_FINE_CAP = 760          # crisp structure (cells/filaments) tolerates more res


def _cache(key, fn):
    v = _CACHE.get(key)
    if v is None:
        if len(_CACHE) > 160:
            _CACHE.clear()
        v = fn()
        _CACHE[key] = v
    return v


def _n01(a):
    a = np.asarray(a, np.float32)
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-7:
        return np.zeros_like(a, np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _wh(shape):
    return (int(shape[0]), int(shape[1]))


def _blur(a, sig):
    if _CV2 and sig > 0:
        return _cv2.GaussianBlur(a.astype(np.float32), (0, 0), float(sig))
    return a.astype(np.float32)


def _noise(shape, scales, weights, seed, cap=_WORK_CAP):
    """multi_scale_noise in [-1,1], computed at a capped work res then upsampled
    (broad fields stay cheap at 2048). Cached."""
    h, w = _wh(shape)
    key = ("n", h, w, tuple(scales), tuple(weights), int(seed), int(cap))

    def build():
        if cap and min(h, w) > cap:
            s = cap / max(h, w)
            sh = max(48, int(round(h * s))); sw = max(48, int(round(w * s)))
            f = np.asarray(multi_scale_noise((sh, sw), scales, weights, seed), np.float32)
            return _resize_array(f, h, w)
        return np.asarray(multi_scale_noise((h, w), scales, weights, seed), np.float32)

    return _cache(key, build)


def _white(shape, seed):
    """Crisp per-pixel hash noise (full res) for grain / sparkle decorrelation."""
    h, w = _wh(shape)
    rng = np.random.default_rng((int(seed) ^ 0x9E3779B1) & 0xFFFFFFFF)
    return rng.random((h, w), dtype=np.float32)


def _splat(shape, seed, n_per_mp, rad_lo, rad_hi, val_lo=0.5, val_hi=1.0,
           elong=1.0, ang=None):
    """Windowed additive splats (embers / sparks). O(points*window), never a full
    grid per point. Returns 0..~1 field, full res, crisp."""
    h, w = _wh(shape)
    rng = np.random.default_rng((int(seed) ^ 0x51ED2701) & 0xFFFFFFFF)
    n = int(max(8, n_per_mp * (h * w) / 1e6))
    n = min(n, 60000)
    out = np.zeros((h, w), np.float32)
    ys = rng.integers(0, h, n); xs = rng.integers(0, w, n)
    rr = rng.uniform(rad_lo, rad_hi, n)
    vv = rng.uniform(val_lo, val_hi, n)
    aa = rng.uniform(0, np.pi, n) if ang is None else np.full(n, float(ang))
    for i in range(n):
        r = rr[i]; ry = max(1, int(r * 2)); rx = max(1, int(r * elong * 2))
        y0 = max(0, ys[i] - ry); y1 = min(h, ys[i] + ry + 1)
        x0 = max(0, xs[i] - rx); x1 = min(w, xs[i] + rx + 1)
        if y1 <= y0 or x1 <= x0:
            continue
        gy = (np.arange(y0, y1) - ys[i])[:, None].astype(np.float32)
        gx = (np.arange(x0, x1) - xs[i])[None, :].astype(np.float32)
        ca = np.cos(aa[i]); sa = np.sin(aa[i])
        u = gx * ca + gy * sa
        v = (-gx * sa + gy * ca) * elong
        d2 = (u * u + v * v) / (r * r + 1e-6)
        out[y0:y1, x0:x1] += vv[i] * np.exp(-d2 * 2.2)
    return np.clip(out, 0, 1).astype(np.float32)


def _domain_warp(field_fn, shape, seed, amp, scales=(40, 90), salt=701, cap=_WORK_CAP):
    """Warp coordinates by a low-freq vector noise then sample field_fn(yy,xx).

    All math runs at a capped work resolution (these warped fields are smooth
    enough to upsample) so 2048 stays under the perf budget. field_fn must accept
    broadcast float arrays of coordinates."""
    h, w = _wh(shape)
    if cap and min(h, w) > cap:
        s = cap / max(h, w)
        sh = max(48, int(round(h * s))); sw = max(48, int(round(w * s)))
        scl = sh / float(h)
    else:
        sh, sw, scl = h, w, 1.0
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    yy = yy / scl; xx = xx / scl                            # coords in full-res space
    dy = _noise((sh, sw), list(scales), [0.6, 0.4], seed + salt) * amp
    dx = _noise((sh, sw), list(scales), [0.6, 0.4], seed + salt + 13) * amp
    out = np.asarray(field_fn(yy + dy, xx + dx), np.float32)
    if (sh, sw) != (h, w):
        out = _resize_array(out, h, w)
    return out


def _compose(col, paint, mask):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    m = mask[:, :, None] if mask.ndim == 2 else mask
    return (np.clip(col, 0, 1).astype(np.float32) * m + paint[:, :, :3] * (1 - m)).astype(np.float32)


def _base3(shape, seed):
    """Three INDEPENDENT broad fields (own seeds/scales) in [0,1], each ~centered.
    Used as the per-channel pedestal so M/R/CC each straddle the mid=120 hue-class
    threshold (-> 4+ classes) while staying mutually decorrelated. The finish's
    own motif is layered ON TOP for the angle-gated ignition."""
    h, w = _wh(shape)
    # broad pedestals -> a small work cap (480) is plenty and ~3x cheaper @2048
    a = _n01(_noise((h, w), [30, 70], [0.6, 0.4], seed + 9001, cap=480))
    b = _n01(_noise((h, w), [20, 48], [0.6, 0.4], seed + 9002, cap=480))
    c = _n01(_noise((h, w), [44, 100], [0.6, 0.4], seed + 9003, cap=480))
    return a, b, c


def _mr_cc(M, R, CC, sm):
    """Finalize a (M,R,CC) triple: apply sm contrast about the channel mean,
    clamp to legal ranges (R floor 15).

    Also gently re-balances any channel whose split across the hue-class midline
    (128) is extreme, by shifting its MEDIAN toward 128 with a monotonic affine
    map. This preserves the channel's own spatial geometry (no reordering -> still
    traces the paint, still decorrelated) but guarantees each of M/R/CC straddles
    the midline so the combined map reads as many hues, not 1-2. Only fires when a
    channel is badly skewed, so well-balanced finishes are left essentially as-is.
    """
    def s(a, mid, lo, hi):
        a = np.asarray(a, np.float32)
        return np.clip(mid + (a - mid) * float(sm), lo, hi).astype(np.float32)

    def balance(a, lo, hi, target=128.0):
        a = np.asarray(a, np.float32)
        flat = a.ravel()
        samp = flat[::7] if flat.size > 300000 else flat   # cheap stats on a subsample
        med = float(np.median(samp))
        frac = float((samp > 128.0).mean())
        if 0.30 <= frac <= 0.70:
            return a                                    # already straddles well
        # shift median toward target, scaling the two sides so order is preserved
        out = a.copy()
        below = a <= med
        # span on each side of the current median
        lo_span = max(med - float(samp.min()), 1.0)
        hi_span = max(float(samp.max()) - med, 1.0)
        # new median pulled 75% of the way to target
        new_med = med + (target - med) * 0.75
        new_lo = max(lo, new_med - lo_span)
        new_hi = min(hi, new_med + hi_span)
        out[below] = new_med - (med - a[below]) * (new_med - new_lo) / lo_span
        out[~below] = new_med + (a[~below] - med) * (new_hi - new_med) / hi_span
        return out

    M = balance(s(M, float(np.mean(M)), 0, 255), 0, 255)
    R = balance(s(R, float(np.mean(R)), 15, 255), 15, 255)
    CC = balance(s(CC, float(np.mean(CC)), 0, 255), 0, 255)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 0, 255).astype(np.float32))


# ===========================================================================
# 01 flame_hotrod - classic licking hot-rod flame LICKS (overlapping tongues
#     swept by domain warp; clean candy-orange ramp). Distinct motif: layered
#     sine-tongue silhouettes warped into licks.
# ===========================================================================
def _hotrod_fields(shape, seed):
    h, w = _wh(shape)
    key = ("hotrod", h, w, int(seed))

    def build():
        # three offset tongue layers; warp each, take the max -> overlapping licks
        def tongues(off, freq, sd):
            def f(yy, xx):
                t = np.sin((xx * 0.013 * freq + yy * 0.004 + off) * np.pi)
                u = np.sin((yy * 0.010 * freq - xx * 0.003 + off * 1.7) * np.pi)
                return np.clip(0.5 + 0.5 * (t * 0.6 + u * 0.4), 0, 1)
            return _domain_warp(f, (h, w), sd, amp=26.0, scales=(30, 70), salt=300)
        a = tongues(0.0, 1.0, seed)
        b = tongues(2.1, 1.4, seed + 7)
        c = tongues(4.0, 0.8, seed + 19)
        lick = np.maximum(np.maximum(a, b * 0.92), c * 0.85)
        # sharpen tongue edges into licks (flame body vs background)
        edge = _n01(lick)
        body = np.clip((edge - 0.42) * 2.6, 0, 1)
        tips = np.clip((edge - 0.72) * 5.0, 0, 1)            # hottest tips
        grain = _white((h, w), seed + 3)
        return body.astype(np.float32), tips.astype(np.float32), grain
    return _cache(key, build)


def paint_flame_hotrod(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    body, tips, grain = _hotrod_fields((h, w), seed)
    col = np.zeros((h, w, 3), np.float32)
    bg = np.array([0.02, 0.015, 0.02], np.float32)
    col += bg
    # candy ramp dark-red -> orange -> yellow on the licks
    deep = np.array([0.45, 0.03, 0.0], np.float32)
    org = np.array([0.95, 0.32, 0.0], np.float32)
    yel = np.array([1.0, 0.85, 0.25], np.float32)
    col = col * (1 - body[..., None]) + (deep * (1 - body[..., None]) + org * body[..., None])
    col = col + (yel - col) * (tips[..., None] * 0.9)
    col *= (1.0 + 0.06 * (grain[..., None] - 0.5))
    return _compose(col, paint, mask)


def spec_flame_hotrod(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    body, tips, grain = _hotrod_fields((h, w), seed)
    sheen = _n01(_noise((h, w), [45, 100], [0.6, 0.4], seed + 141))   # own CC base
    # M ignites the licks; R rides cross-grain (anti the body); CC = broad clear
    # sheen (independent geometry) + tip ignition so it doesn't mirror M.
    M = 60 + 165 * tips + 70 * body
    R = 150 - 90 * body + 60 * (grain - 0.5) * 2.0           # licks polished, bg rough
    CC = 60 + 130 * sheen + 90 * tips                        # gloss tips on a varied sheen
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 02 flame_true_fire - photoreal turbulent fire sheet: advected curl turbulence
#     with vertical-ish buoyancy in UV-agnostic radial sense; blackbody ramp.
#     Motif: fine billowing turbulence, NOT tongues.
# ===========================================================================
def _truefire_fields(shape, seed):
    h, w = _wh(shape)
    key = ("truefire", h, w, int(seed))

    def build():
        # layered turbulence + a coarse buoyancy gradient warped into plumes
        turb = _n01(np.abs(_noise((h, w), [9, 18, 36, 72, 140], [.30, .26, .22, .14, .08], seed)))
        plume = _domain_warp(
            lambda yy, xx: np.sin(yy * 0.006 + xx * 0.002) * 0.5 + 0.5,
            (h, w), seed + 5, amp=40.0, scales=(60, 130), salt=410)
        inten = _n01(turb * 0.65 + _n01(plume) * 0.35)
        inten = inten ** 1.25
        flick = _white((h, w), seed + 2)
        return inten.astype(np.float32), flick
    return _cache(key, build)


def paint_flame_true_fire(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    inten, flick = _truefire_fields((h, w), seed)
    t = np.clip(inten + 0.04 * (flick - 0.5), 0, 1)
    # blackbody-ish: black -> deep red -> orange -> yellow -> near-white
    stops = np.array([[0.01, 0.0, 0.0], [0.5, 0.04, 0.0], [0.95, 0.32, 0.0],
                      [1.0, 0.74, 0.12], [1.0, 0.97, 0.7]], np.float32)
    n = len(stops) - 1
    tt = t * n
    i = np.clip(np.floor(tt).astype(np.int32), 0, n - 1)
    f = (tt - i)[..., None]
    col = stops[i] * (1 - f) + stops[i + 1] * f
    return _compose(col, paint, mask)


def spec_flame_true_fire(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    inten, flick = _truefire_fields((h, w), seed)
    hot = np.clip((inten - 0.55) * 2.5, 0, 1)
    # M tracks hot turbulence; R rides flicker grain (decorrelated); CC a soft
    # high-altitude glow band (mid intensities) -> blue/teal pixels in combined.
    M = 25 + 210 * hot + 40 * inten
    R = 60 + 120 * flick + 40 * (1 - inten)
    CC = 10 + 150 * np.clip(1.0 - np.abs(inten - 0.5) * 2.4, 0, 1)
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 03 flame_blue - propane / gas-burner ring flames: concentric burner cells with
#     a sharp inner-cone vs outer-mantle two-tone (blue inner, violet mantle).
#     Motif: scattered ring/cone burners, NOT licks.
# ===========================================================================
def _burner_fields(shape, seed):
    h, w = _wh(shape)
    key = ("burner", h, w, int(seed))

    def build():
        # scatter burner centers, distance field -> cone(inner) + mantle(ring)
        cap = min(min(h, w), _FINE_CAP)
        sh = sw = cap
        rng = np.random.default_rng((int(seed) ^ 0x1357) & 0xFFFFFFFF)
        n = max(40, int(sh * sw / 5500))
        py = rng.uniform(0, sh, n); px = rng.uniform(0, sw, n)
        rad = rng.uniform(sh * 0.012, sh * 0.04, n)
        try:
            from scipy.spatial import cKDTree
            yy, xx = np.mgrid[0:sh, 0:sw]
            d, idx = cKDTree(np.stack([py, px], 1)).query(
                np.stack([yy.ravel(), xx.ravel()], 1), k=1, workers=-1)
            d = d.reshape(sh, sw).astype(np.float32)
            rmap = rad[idx].reshape(sh, sw).astype(np.float32)
        except Exception:
            yy, xx = np.mgrid[0:sh, 0:sw]
            d = np.full((sh, sw), 1e9, np.float32); rmap = np.full((sh, sw), 1.0, np.float32)
            for i in range(n):
                dd = np.sqrt((yy - py[i]) ** 2 + (xx - px[i]) ** 2).astype(np.float32)
                m = dd < d; d = np.where(m, dd, d); rmap = np.where(m, rad[i], rmap)
        rn = d / (rmap + 1e-3)
        inner = np.clip(1.0 - rn * 1.1, 0, 1) ** 1.6          # hot cone
        mantle = np.clip(1.0 - np.abs(rn - 1.0) * 2.2, 0, 1)  # outer ring
        if cap != min(h, w) or sh != h:
            inner = _resize_array(inner, h, w); mantle = _resize_array(mantle, h, w)
        flick = _noise((h, w), [20, 50], [0.6, 0.4], seed + 9)
        return inner.astype(np.float32), mantle.astype(np.float32), _n01(flick)
    return _cache(key, build)


def paint_flame_blue(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    inner, mantle, flick = _burner_fields((h, w), seed)
    col = np.zeros((h, w, 3), np.float32)
    col[..., 2] = 0.06                                        # near-black blue bg
    violet = np.array([0.32, 0.05, 0.6], np.float32)
    blue = np.array([0.05, 0.35, 0.95], np.float32)
    cyan = np.array([0.6, 0.95, 1.0], np.float32)
    col = col + violet * mantle[..., None]
    col = col * (1 - inner[..., None]) + (blue * (1 - inner[..., None]) + cyan * inner[..., None]) * np.clip(inner + mantle, 0, 1)[..., None]
    col = np.clip(col + 0.05 * (flick[..., None] - 0.5), 0, 1)
    return _compose(col, paint, mask)


def spec_flame_blue(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    inner, mantle, flick = _burner_fields((h, w), seed)
    # three independent pedestals so M/R/CC don't share geometry
    ba, bb_, bc = _base3((h, w), seed)
    # M peaks on hot cones; R on the mantle ring; CC rides an independent
    # pedestal -> three distinct value distributions, all straddling mid.
    M = 70 + 90 * ba + 150 * inner
    R = 80 + 100 * bb_ + 120 * mantle
    CC = 80 + 110 * bc + 50 * inner
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 04 flame_green - eerie chemical / copper-burn fire: striated flame curtains
#     (vertical-agnostic radial striations) flickering green->teal->white.
#     Motif: thin striated curtains, NOT turbulence blobs.
# ===========================================================================
def _curtain_fields(shape, seed):
    h, w = _wh(shape)
    key = ("curtain", h, w, int(seed))

    def build():
        # radial-ish striations: angle around a drifting center + warp = curtains.
        # Computed at a capped work res (the angular sweep is smooth) then upsampled.
        cap = min(min(h, w), _FINE_CAP)
        sh = sw = cap
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        cy = sh * 0.5 + 0.2 * sh * np.sin(seed); cx = sw * 0.5 + 0.2 * sw * np.cos(seed)
        ang = np.arctan2(yy - cy, xx - cx).astype(np.float32)
        warp = _noise((sh, sw), [24, 60], [0.6, 0.4], seed + 4) * 0.9
        strands = np.sin((ang * 26.0 + warp * 8.0)) * 0.5 + 0.5
        strands = strands ** 1.4
        edge = _n01(np.abs(np.gradient(strands.astype(np.float32))[1]))   # fine striation edges
        if (sh, sw) != (h, w):
            strands = _resize_array(strands, h, w); edge = _resize_array(edge, h, w)
        flame = _n01(_noise((h, w), [16, 40, 90], [0.4, 0.35, 0.25], seed + 1))
        inten = _n01(strands * 0.55 + flame * 0.45)
        return inten.astype(np.float32), edge, flame
    return _cache(key, build)


def paint_flame_green(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    inten, edge, flame = _curtain_fields((h, w), seed)
    t = inten
    stops = np.array([[0.0, 0.04, 0.02], [0.0, 0.3, 0.08], [0.15, 0.75, 0.12],
                      [0.5, 1.0, 0.4], [0.85, 1.0, 0.8]], np.float32)
    n = len(stops) - 1
    tt = t * n; i = np.clip(np.floor(tt).astype(np.int32), 0, n - 1); f = (tt - i)[..., None]
    col = stops[i] * (1 - f) + stops[i + 1] * f
    return _compose(col, paint, mask)


def spec_flame_green(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    inten, edge, flame = _curtain_fields((h, w), seed)
    # M on bright strands; R rides flame turbulence (separate field, no inten
    # term so it doesn't track M); CC = independent pedestal + fine edge ignition.
    ba, bb_, bc = _base3((h, w), seed)
    M = 70 + 80 * ba + 150 * inten
    R = 40 + 130 * flame + 60 * bb_                          # mean ~120, straddles
    CC = 70 + 90 * bc + 130 * edge
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 05 flame_purple - witch-fire / royal arc-flame: branching electric tendrils
#     (lightning-like) glowing magenta with cool indigo halo. Motif: branching
#     filaments via iterated thin-edge ridges, NOT tongues.
# ===========================================================================
def _arc_fields(shape, seed):
    h, w = _wh(shape)
    key = ("arc", h, w, int(seed))

    def build():
        # ridge of a warped noise -> filament network (|deriv| of a smooth field)
        base = _noise((h, w), [28, 60, 120], [0.4, 0.35, 0.25], seed)
        gy, gx = np.gradient(base.astype(np.float32))
        ridge = 1.0 - _n01(np.hypot(gy, gx))
        fil = np.clip((ridge - 0.78) * 7.0, 0, 1)             # thin bright filaments
        fil = _blur(fil, 0.6)
        halo = _blur(fil, 6.0)
        glow = _n01(_noise((h, w), [40, 90], [0.6, 0.4], seed + 8))
        return fil.astype(np.float32), _n01(halo), glow
    return _cache(key, build)


def paint_flame_purple(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    fil, halo, glow = _arc_fields((h, w), seed)
    col = np.zeros((h, w, 3), np.float32)
    col += np.array([0.05, 0.0, 0.09], np.float32)            # indigo void
    col += np.array([0.18, 0.0, 0.32], np.float32) * (halo * (0.4 + 0.6 * glow))[..., None]
    magenta = np.array([0.95, 0.15, 0.95], np.float32)
    hot = np.array([1.0, 0.8, 1.0], np.float32)
    col = col + magenta * fil[..., None]
    col = col + (hot - col) * np.clip((fil - 0.6), 0, 1)[..., None]
    return _compose(np.clip(col, 0, 1), paint, mask)


def spec_flame_purple(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    fil, halo, glow = _arc_fields((h, w), seed)
    ba, bb_, bc = _base3((h, w), seed)
    # M = independent pedestal + crisp filament ignition (so M straddles mid, not
    # just sparse lines); R rides an independent grain (wide); CC rides its own
    # wide pedestal + glow so it decorrelates from M and straddles the midline.
    M = 75 + 90 * ba + 150 * fil + 30 * halo
    R = 50 + 130 * bb_ + 50 * glow
    CC = 55 + 140 * bc + 70 * glow
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 06 flame_ghost - subtle ghost flames: barely-there licks only visible in the
#     SPEC; albedo near body color. Motif: faint tonal licks; the drama lives in
#     the angle-gated spec ignition.
# ===========================================================================
def _ghost_fields(shape, seed):
    h, w = _wh(shape)
    key = ("ghost", h, w, int(seed))

    def build():
        def f(yy, xx):
            t = np.sin((xx * 0.011 + yy * 0.003) * np.pi)
            u = np.sin((yy * 0.009 - xx * 0.0025) * np.pi)
            return 0.5 + 0.5 * (t * 0.55 + u * 0.45)
        lick = _domain_warp(f, (h, w), seed, amp=30.0, scales=(34, 80), salt=520)
        lick = _n01(lick)
        body = np.clip((lick - 0.5) * 2.2, 0, 1)
        tips = np.clip((lick - 0.78) * 5.0, 0, 1)
        fine = _white((h, w), seed + 3)
        return body.astype(np.float32), tips.astype(np.float32), fine
    return _cache(key, build)


def paint_flame_ghost(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    body, tips, fine = _ghost_fields((h, w), seed)
    # near-monochrome graphite, faintly warmer on licks (drama is in spec)
    base = np.array([0.11, 0.11, 0.13], np.float32)
    warm = np.array([0.2, 0.16, 0.14], np.float32)
    col = base * (1 - body[..., None]) + warm * body[..., None]
    col = col + 0.10 * tips[..., None]
    col *= (1.0 + 0.04 * (fine[..., None] - 0.5))
    return _compose(col, paint, mask)


def spec_flame_ghost(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    body, tips, fine = _ghost_fields((h, w), seed)
    micro = _n01(_noise((h, w), [10, 24, 55], [0.4, 0.33, 0.27], seed + 41))  # own R field
    ba, bb_, bc = _base3((h, w), seed)
    # huge M jump on the licks (invisible in albedo, blazing at raking angle);
    # R rides an INDEPENDENT micro-roughness field; CC rides an independent
    # pedestal + tip ignition so it no longer mirrors M (body term removed).
    M = 70 + 80 * ba + 165 * body + 20 * tips
    R = 80 + 110 * micro + 40 * bb_
    CC = 80 + 90 * bc + 140 * tips
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 07 flame_inferno - raging WILDFIRE wall: large-scale rolling fire fronts with
#     dense interior turbulence and dark smoke caps. Motif: big advancing fronts
#     with crushed smoke gaps, NOT discrete tongues.
# ===========================================================================
def _inferno_fields(shape, seed):
    h, w = _wh(shape)
    key = ("inferno", h, w, int(seed))

    def build():
        front = _n01(_noise((h, w), [60, 130], [0.6, 0.4], seed))           # rolling fronts
        detail = _n01(np.abs(_noise((h, w), [10, 22, 46, 100], [.3, .28, .24, .18], seed + 2)))
        inten = _n01(front * 0.55 + detail * 0.45) ** 1.1
        smoke = np.clip((_n01(_noise((h, w), [40, 90], [0.6, 0.4], seed + 6)) - 0.55) * 3.0, 0, 1)
        inten = np.clip(inten - smoke * 0.6, 0, 1)
        return inten.astype(np.float32), smoke.astype(np.float32), detail
    return _cache(key, build)


def paint_flame_inferno(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    inten, smoke, detail = _inferno_fields((h, w), seed)
    t = inten
    stops = np.array([[0.02, 0.0, 0.0], [0.55, 0.0, 0.0], [0.95, 0.18, 0.0],
                      [1.0, 0.5, 0.0], [1.0, 0.88, 0.25]], np.float32)
    n = len(stops) - 1
    tt = t * n; i = np.clip(np.floor(tt).astype(np.int32), 0, n - 1); f = (tt - i)[..., None]
    col = stops[i] * (1 - f) + stops[i + 1] * f
    smk = np.array([0.06, 0.05, 0.05], np.float32)
    col = col * (1 - smoke[..., None]) + smk * smoke[..., None]
    return _compose(col, paint, mask)


def spec_flame_inferno(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    inten, smoke, detail = _inferno_fields((h, w), seed)
    sheen = _n01(_noise((h, w), [30, 70, 150], [0.4, 0.35, 0.25], seed + 51))  # own CC field
    # M = fire intensity; R = HIGH in smoke (matte soot) on its own geometry; CC
    # rides an independent broad sheen -> classes interleave across the wall.
    M = 60 + 180 * inten
    R = 95 + 150 * smoke + 50 * detail
    CC = 60 + 150 * sheen + 50 * detail
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 08 flame_white_hot - acetylene / welding white-core flame: extreme core blowout
#     with a thin cyan->blue->violet temperature shell. Motif: radial heat shells
#     around scattered hot cores, NOT tongues.
# ===========================================================================
def _whitehot_fields(shape, seed):
    h, w = _wh(shape)
    key = ("whitehot", h, w, int(seed))

    def build():
        cores = _splat((h, w), seed, n_per_mp=2.0, rad_lo=18, rad_hi=46,
                       val_lo=0.7, val_hi=1.0, elong=1.0)
        cores = _n01(cores)
        shell = _blur(cores, 9.0)
        temp = _n01(shell)                                  # 0 outer .. 1 core
        flick = _noise((h, w), [18, 44], [0.6, 0.4], seed + 7)
        return temp.astype(np.float32), _n01(flick), _n01(cores)
    return _cache(key, build)


def paint_flame_white_hot(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    temp, flick, cores = _whitehot_fields((h, w), seed)
    # violet -> blue -> cyan -> white as temperature rises
    stops = np.array([[0.04, 0.0, 0.08], [0.25, 0.05, 0.5], [0.1, 0.4, 0.95],
                      [0.6, 0.9, 1.0], [1.0, 1.0, 1.0]], np.float32)
    t = np.clip(temp + 0.05 * (flick - 0.5), 0, 1)
    n = len(stops) - 1
    tt = t * n; i = np.clip(np.floor(tt).astype(np.int32), 0, n - 1); f = (tt - i)[..., None]
    col = stops[i] * (1 - f) + stops[i + 1] * f
    return _compose(col, paint, mask)


def spec_flame_white_hot(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    temp, flick, cores = _whitehot_fields((h, w), seed)
    # M blowout on hot temperature zones; R rides flicker (own field); CC on the
    # mid-temp shell ring (band) -> shell, core and ground each land different.
    shell = np.clip(1.0 - np.abs(temp - 0.55) * 2.6, 0, 1)
    ba, bb_, bc = _base3((h, w), seed)
    M = 70 + 90 * ba + 110 * temp + 30 * cores
    R = 75 + 95 * bb_ + 80 * flick + 50 * (1 - temp)
    CC = 75 + 90 * bc + 120 * shell
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 09 flame_rainbow - color-flame spectroscopy: bands of element-burn colors
#     (lithium red, sodium yellow, copper green/blue, potassium violet) sorted by
#     a flow field. Motif: hue-banded flow ribbons, NOT a single fire ramp.
# ===========================================================================
def _spectro_fields(shape, seed):
    h, w = _wh(shape)
    key = ("spectro", h, w, int(seed))

    def build():
        flow = _n01(_noise((h, w), [40, 90, 180], [0.4, 0.35, 0.25], seed))
        ribbon = (flow * 5.0) % 1.0                          # repeating bands along flow
        inten = _n01(np.abs(_noise((h, w), [12, 26, 60], [0.4, 0.33, 0.27], seed + 3)))
        return _n01(flow), ribbon.astype(np.float32), inten
    return _cache(key, build)


def paint_flame_rainbow(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    flow, ribbon, inten = _spectro_fields((h, w), seed)
    # hue sweeps with flow, value with fire intensity, near-black where cold
    hue = (flow * 0.9 + 0.0) % 1.0
    sat = np.full((h, w), 0.95, np.float32)
    val = np.clip(0.25 + inten * 0.95, 0, 1)
    r, g, b = hsv_to_rgb_vec(hue, sat, val)
    col = np.stack([r, g, b], -1)
    col *= (0.4 + 0.6 * inten[..., None])                    # darken cold flame
    return _compose(col, paint, mask)


def spec_flame_rainbow(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    flow, ribbon, inten = _spectro_fields((h, w), seed)
    # M tracks fire intensity; R alternates by spectral band (ribbon); CC follows
    # flow hue -> three uncorrelated geometries -> very multi-hue combined.
    M = 30 + 200 * inten
    R = 60 + 170 * ribbon
    CC = 14 + 170 * flow
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 10 flame_ember - EMBER STORM: dense drifting glowing sparks over dark char,
#     each ember a bright windowed splat with a comet streak. Motif: discrete
#     point embers (true particles), NOT a continuous sheet.
# ===========================================================================
def _ember_fields(shape, seed):
    h, w = _wh(shape)
    key = ("ember", h, w, int(seed))

    def build():
        sparks = _splat((h, w), seed, n_per_mp=140.0, rad_lo=1.2, rad_hi=4.0,
                        val_lo=0.5, val_hi=1.0, elong=3.0, ang=0.6)   # comet streaks
        big = _splat((h, w), seed + 11, n_per_mp=22.0, rad_lo=3.0, rad_hi=7.0,
                     val_lo=0.6, val_hi=1.0, elong=2.0, ang=0.6)
        embers = np.clip(sparks + big, 0, 1)
        char = _n01(_noise((h, w), [30, 70], [0.6, 0.4], seed + 2))    # smoldering char glow
        return embers.astype(np.float32), char
    return _cache(key, build)


def paint_flame_ember(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    embers, char = _ember_fields((h, w), seed)
    col = np.zeros((h, w, 3), np.float32)
    # dark char base with faint red smolder
    col += np.array([0.04, 0.02, 0.02], np.float32)
    col += np.array([0.22, 0.04, 0.0], np.float32) * char[..., None]
    # embers ramp red->orange->yellow-white by brightness
    e = embers
    col = col + np.array([0.9, 0.25, 0.0], np.float32) * e[..., None]
    col = col + np.array([0.6, 0.6, 0.3], np.float32) * np.clip(e - 0.6, 0, 1)[..., None]
    return _compose(np.clip(col, 0, 1), paint, mask)


def spec_flame_ember(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    embers, char = _ember_fields((h, w), seed)
    ash = _n01(_noise((h, w), [12, 28, 60], [0.4, 0.33, 0.27], seed + 61))   # own R field
    smolder = _n01(_noise((h, w), [40, 90, 180], [0.4, 0.35, 0.25], seed + 62))  # own CC field
    # M = char-glow pedestal (straddles mid) + bright ember ignition; R rides an
    # independent ash texture (matte char grain); CC rides a broad smolder glow.
    M = 70 + 90 * char + 150 * embers
    R = 80 + 120 * ash - 60 * embers
    CC = 80 + 110 * smolder + 50 * embers
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 11 flame_candy - candy-coated fire under deep clear: real Beer-Lambert candy
#     over a flame-flake metal. Motif: candy depth pooling over flake turbulence,
#     NOT a flat ramp. Uses color_science.candy_absorb.
# ===========================================================================
def _candy_fields(shape, seed):
    h, w = _wh(shape)
    key = ("candyf", h, w, int(seed))

    def build():
        flake = _white((h, w), seed + 1)                     # metal flake sparkle
        flame = _n01(_noise((h, w), [14, 30, 64], [0.4, 0.33, 0.27], seed))   # flame turbulence
        depth = _n01(_noise((h, w), [50, 110], [0.6, 0.4], seed + 3))         # coat pooling
        return flake, flame, depth
    return _cache(key, build)


def paint_flame_candy(paint, shape, mask, seed, pm, bb):
    from engine.color_science import candy_absorb
    h, w = _wh(shape)
    flake, flame, depth = _candy_fields((h, w), seed)
    # metal layer = bright flame-modulated silver with flake sparkle
    metalv = np.clip(0.45 + 0.55 * flame + 0.25 * (flake - 0.5), 0, 1)
    metal = np.stack([metalv, metalv * 0.95, metalv * 0.9], -1)
    tint = np.array([0.85, 0.05, 0.08], np.float32)          # candy apple red tint
    d = 0.6 + depth * 1.8 + (1.0 - flame) * 0.6              # pools dark in cold valleys
    col = candy_absorb(metal, tint, d, density=1.0)
    return _compose(col, paint, mask)


def spec_flame_candy(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    flake, flame, depth = _candy_fields((h, w), seed)
    pool = _n01(_noise((h, w), [60, 130], [0.6, 0.4], seed + 71))    # own CC pooling field
    # M rides flame; R rides coat depth (thick=glassy low R); CC rides an
    # independent pool field (deep candy gloss varies, crosses mid) + flake glints.
    M = 70 + 165 * flame + 30 * (flake - 0.5) * 2.0
    R = 150 - 110 * depth + 40 * (1 - flame)
    CC = 70 + 150 * pool + 30 * (flake - 0.5) * 2.0
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 12 flame_plasma - PLASMA arc field: interfering sine plasma (classic demoscene
#     plasma) lit as ionized gas, violet/cyan with white filament cores. Motif:
#     smooth interfering sinusoids, totally unlike any fire field above.
# ===========================================================================
def _plasma_fields(shape, seed):
    h, w = _wh(shape)
    key = ("plasma", h, w, int(seed))

    def build():
        cap = min(min(h, w), _WORK_CAP)
        sh = sw = cap
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        rng = np.random.default_rng((int(seed) ^ 0xABCD) & 0xFFFFFFFF)
        cx = rng.uniform(0, sw); cy = rng.uniform(0, sh)
        p = (np.sin(xx * 0.035 + seed)
             + np.sin(yy * 0.041 - seed * 0.5)
             + np.sin((xx + yy) * 0.026 + seed)
             + np.sin(np.hypot(xx - cx, yy - cy) * 0.05))
        p = _n01(p)
        if sh != h:
            p = _resize_array(p, h, w)
        fil = np.clip(np.abs(p - 0.5) * -2.0 + 1.0, 0, 1) ** 3   # bright filament where p~0.5
        return p.astype(np.float32), fil.astype(np.float32)
    return _cache(key, build)


def paint_flame_plasma(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    p, fil = _plasma_fields((h, w), seed)
    hue = (0.62 + p * 0.32) % 1.0                             # violet..cyan band
    sat = np.full((h, w), 0.9, np.float32)
    val = np.clip(0.2 + p * 0.7, 0, 1)
    r, g, b = hsv_to_rgb_vec(hue, sat, val)
    col = np.stack([r, g, b], -1)
    col = col + (np.array([1.0, 1.0, 1.0], np.float32) - col) * fil[..., None]   # white cores
    return _compose(col, paint, mask)


def spec_flame_plasma(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    p, fil = _plasma_fields((h, w), seed)
    ion = _n01(_noise((h, w), [26, 60, 130], [0.4, 0.35, 0.25], seed + 81))   # own CC field
    ba, _bb, _bc = _base3((h, w), seed)
    # M = pedestal (straddles mid) + filament core ignition; R inverse of plasma
    # value; CC rides an INDEPENDENT ionization field (not 1-p) so R/CC decorr.
    M = 70 + 80 * ba + 160 * fil + 30 * p
    R = 45 + 150 * (1 - p)                                   # mean ~120, straddles
    CC = 70 + 130 * ion + 40 * p
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 13 flame_cold - frost / cryo "cold fire": brittle crystalline frost flames,
#     icy blue with sharp facet shards. Motif: Voronoi crackle facets (cKDTree),
#     NOT smooth flame.
# ===========================================================================
def _frost_fields(shape, seed):
    h, w = _wh(shape)
    key = ("frost", h, w, int(seed))

    def build():
        cap = min(min(h, w), _FINE_CAP)
        sh = sw = cap
        rng = np.random.default_rng((int(seed) ^ 0xF205) & 0xFFFFFFFF)
        n = max(120, int(sh * sw / 1700))
        py = rng.uniform(0, sh, n); px = rng.uniform(0, sw, n)
        try:
            from scipy.spatial import cKDTree
            yy, xx = np.mgrid[0:sh, 0:sw]
            d, _ = cKDTree(np.stack([py, px], 1)).query(
                np.stack([yy.ravel(), xx.ravel()], 1), k=2, workers=-1)
            d = d.reshape(sh, sw, 2).astype(np.float32)
            edge = _n01(d[..., 1] - d[..., 0])               # facet border distance
            cell = _n01(d[..., 0])
        except Exception:
            yy, xx = np.mgrid[0:sh, 0:sw]
            d1 = np.full((sh, sw), 1e9, np.float32)
            for i in range(n):
                dd = (yy - py[i]) ** 2 + (xx - px[i]) ** 2
                d1 = np.minimum(d1, dd)
            edge = _n01(np.sqrt(d1)); cell = edge
        crack = 1.0 - np.clip(edge * 6.0, 0, 1)              # bright crack lines
        if sh != h:
            crack = _resize_array(crack, h, w); cell = _resize_array(cell, h, w)
        sheen = _n01(_noise((h, w), [20, 50], [0.6, 0.4], seed + 4))
        return crack.astype(np.float32), cell.astype(np.float32), sheen
    return _cache(key, build)


def paint_flame_cold(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    crack, cell, sheen = _frost_fields((h, w), seed)
    col = np.zeros((h, w, 3), np.float32)
    col += np.array([0.02, 0.06, 0.14], np.float32)          # deep ice base
    col += np.array([0.15, 0.45, 0.7], np.float32) * (cell * 0.6 + sheen * 0.4)[..., None]
    col = col + (np.array([0.85, 0.97, 1.0], np.float32) - col) * crack[..., None]   # white frost edges
    return _compose(np.clip(col, 0, 1), paint, mask)


def spec_flame_cold(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    crack, cell, sheen = _frost_fields((h, w), seed)
    # M on crisp crack edges (icy glint); R high on facet bodies (frosted matte);
    # CC rides sheen noise -> edges read as M-hot lines on R-rough facets.
    M = 25 + 215 * crack + 20 * sheen
    R = 120 + 110 * cell - 70 * crack
    CC = 14 + 150 * sheen + 40 * crack
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 14 flame_lava - molten LAVA crust: dark basalt crust cracked by glowing magma
#     veins, with a few bright vents. Motif: dark plates separated by bright
#     molten cracks (inverted Voronoi), unlike any other here.
# ===========================================================================
def _lava_fields(shape, seed):
    h, w = _wh(shape)
    key = ("lava", h, w, int(seed))

    def build():
        cap = min(min(h, w), _FINE_CAP)
        sh = sw = cap
        rng = np.random.default_rng((int(seed) ^ 0x1A7A) & 0xFFFFFFFF)
        n = max(60, int(sh * sw / 4200))
        py = rng.uniform(0, sh, n); px = rng.uniform(0, sw, n)
        try:
            from scipy.spatial import cKDTree
            yy, xx = np.mgrid[0:sh, 0:sw]
            d, _ = cKDTree(np.stack([py, px], 1)).query(
                np.stack([yy.ravel(), xx.ravel()], 1), k=2, workers=-1)
            d = d.reshape(sh, sw, 2).astype(np.float32)
            border = _n01(d[..., 1] - d[..., 0])
            plate = _n01(d[..., 0])
        except Exception:
            yy, xx = np.mgrid[0:sh, 0:sw]
            d1 = np.full((sh, sw), 1e9, np.float32)
            for i in range(n):
                dd = (yy - py[i]) ** 2 + (xx - px[i]) ** 2
                d1 = np.minimum(d1, dd)
            border = _n01(np.sqrt(d1)); plate = border
        magma = 1.0 - np.clip(border * 7.0, 0, 1)            # bright cracks between plates
        if sh != h:
            magma = _resize_array(magma, h, w); plate = _resize_array(plate, h, w)
        heat = _n01(_noise((h, w), [40, 90], [0.6, 0.4], seed + 5))  # crust warmth
        return magma.astype(np.float32), plate.astype(np.float32), heat
    return _cache(key, build)


def paint_flame_lava(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    magma, plate, heat = _lava_fields((h, w), seed)
    col = np.zeros((h, w, 3), np.float32)
    crust = np.array([0.05, 0.035, 0.035], np.float32)
    warm_crust = np.array([0.14, 0.05, 0.03], np.float32)
    col += crust * (1 - heat[..., None]) + warm_crust * heat[..., None]
    # magma cracks: deep red -> orange -> yellow-white at the hottest
    m = magma
    col = col + np.array([0.85, 0.18, 0.0], np.float32) * m[..., None]
    col = col + np.array([0.55, 0.55, 0.2], np.float32) * np.clip(m - 0.65, 0, 1)[..., None]
    return _compose(np.clip(col, 0, 1), paint, mask)


def spec_flame_lava(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    magma, plate, heat = _lava_fields((h, w), seed)
    grit = _n01(_noise((h, w), [10, 24, 55], [0.4, 0.33, 0.27], seed + 91))   # own R grain
    # M = heat-glow pedestal (straddles mid) + magma crack ignition; R rides an
    # independent basalt grit (rough crust); CC rides the broad crust heat field.
    M = 70 + 80 * heat + 165 * magma
    R = 55 + 120 * grit + 60 * plate                        # mean ~120, straddles
    CC = 70 + 110 * heat + 50 * plate
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 15 flame_phoenix - feathered phoenix-wing fire: overlapping feather/scale
#     plumes (oriented teardrop scales) glowing gold->crimson. Motif: imbricated
#     feather scales via a phase-offset scale lattice, unlike tongues/turbulence.
# ===========================================================================
def _phoenix_fields(shape, seed):
    h, w = _wh(shape)
    key = ("phoenix", h, w, int(seed))

    def build():
        cap = min(min(h, w), _FINE_CAP)
        sh = sw = cap
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        # scale lattice with row offset + warp -> imbricated feathers
        warp = _resize_array(_noise((sh, sw), [40, 90], [0.6, 0.4], seed + 2), sh, sw) * 14.0
        sc = max(12.0, sh / 26.0)
        u = (xx + warp) / sc
        row = np.floor((yy + warp * 0.5) / (sc * 0.7))
        u = u + (row % 2) * 0.5
        fu = (u % 1.0) - 0.5
        fv = (((yy + warp * 0.5) / (sc * 0.7)) % 1.0) - 0.5
        d = np.sqrt(fu * fu + (fv * 1.4) ** 2)               # teardrop scale distance
        scale = np.clip(1.0 - d * 2.0, 0, 1) ** 1.3
        rib = np.clip(1.0 - np.abs(fu) * 7.0, 0, 1) * (fv < 0.2)   # feather rib glint
        if sh != h:
            scale = _resize_array(scale, h, w); rib = _resize_array(rib.astype(np.float32), h, w)
        hue_var = _n01(_noise((h, w), [50, 120], [0.6, 0.4], seed + 8))
        return scale.astype(np.float32), rib.astype(np.float32), hue_var
    return _cache(key, build)


def paint_flame_phoenix(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    scale, rib, hue_var = _phoenix_fields((h, w), seed)
    col = np.zeros((h, w, 3), np.float32)
    col += np.array([0.12, 0.01, 0.0], np.float32)           # crimson shadow base
    # each scale: crimson edge -> gold center, hue drifts across the wing
    crimson = np.array([0.7, 0.05, 0.0], np.float32)
    gold = np.array([1.0, 0.7, 0.1], np.float32)
    white = np.array([1.0, 0.95, 0.6], np.float32)
    base = crimson * (0.7 + 0.3 * hue_var)[..., None]
    col = col + base * scale[..., None]
    col = col + (gold - col) * np.clip(scale - 0.4, 0, 1)[..., None]
    col = col + (white - col) * (rib[..., None] * 0.8)
    return _compose(np.clip(col, 0, 1), paint, mask)


def spec_flame_phoenix(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    scale, rib, hue_var = _phoenix_fields((h, w), seed)
    plume = _n01(_noise((h, w), [50, 120, 240], [0.4, 0.35, 0.25], seed + 101))  # own CC base
    ba, _bb, _bc = _base3((h, w), seed)
    # M = pedestal + scale-body ignition (straddles mid); R rides hue_var
    # (separate low-freq field); CC = broad plume gloss + crisp rib ignition.
    M = 70 + 80 * ba + 140 * scale
    R = 50 + 130 * hue_var + 40 * (1 - scale)               # mean ~120, straddles
    CC = 70 + 110 * plume + 110 * rib
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 16 flame_toxic - radioactive HEAT-HAZE: green-glow haze with shimmering mirage
#     ripples + drifting smoke. Motif: anisotropic wave-shear shimmer (mirage),
#     unlike any structural fire.
# ===========================================================================
def _toxic_fields(shape, seed):
    h, w = _wh(shape)
    key = ("toxic", h, w, int(seed))

    def build():
        # heat haze = base glow sampled through a wavy shear (mirage ripples).
        # Smooth sinusoids -> compute at work res and upsample.
        glow = _n01(_noise((h, w), [50, 120], [0.6, 0.4], seed))
        cap = min(min(h, w), _WORK_CAP)
        sh = sw = cap; scl = sh / float(h)
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        yy = yy / scl; xx = xx / scl
        ripple = (np.sin(yy * 0.05 + _noise((sh, sw), [30, 70], [0.6, 0.4], seed + 3) * 6.0)
                  * np.sin(xx * 0.013 + seed))
        ripple = _n01(ripple)
        if (sh, sw) != (h, w):
            ripple = _resize_array(ripple, h, w)
        shimmer = _n01(glow + 0.4 * ripple)
        haze = _n01(_noise((h, w), [80, 160], [0.6, 0.4], seed + 6))   # drifting smoke
        return shimmer.astype(np.float32), ripple, haze
    return _cache(key, build)


def paint_flame_toxic(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    shimmer, ripple, haze = _toxic_fields((h, w), seed)
    col = np.zeros((h, w, 3), np.float32)
    col += np.array([0.02, 0.07, 0.02], np.float32)
    # sickly green core with yellow-green hotspots, hazy desat in smoke
    green = np.array([0.25, 0.85, 0.1], np.float32)
    acid = np.array([0.8, 1.0, 0.15], np.float32)
    col = col + green * shimmer[..., None]
    col = col + (acid - col) * np.clip(shimmer - 0.6, 0, 1)[..., None]
    col = col * (1 - 0.4 * haze[..., None]) + np.array([0.18, 0.2, 0.14], np.float32) * (0.4 * haze[..., None])
    return _compose(np.clip(col, 0, 1), paint, mask)


def spec_flame_toxic(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    shimmer, ripple, haze = _toxic_fields((h, w), seed)
    # M on glow hotspots; R modulated by the mirage RIPPLE (anisotropic shimmer);
    # CC rides haze inversely -> haze reads matte/clear, glow reads metallic.
    M = 25 + 200 * shimmer
    R = 90 + 120 * ripple + 30 * haze
    CC = 14 + 150 * (1 - haze) + 30 * shimmer
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 17 flame_pink - sakura ember bloom: soft glowing petals/blossoms drifting on a
#     warm dusk gradient, hot-pink with magenta cores. Motif: scattered soft
#     5-lobed blossom splats, unlike sharp tongues or particles.
# ===========================================================================
def _sakura_fields(shape, seed):
    h, w = _wh(shape)
    key = ("sakura", h, w, int(seed))

    def build():
        cap = min(min(h, w), _FINE_CAP)
        sh = sw = cap
        rng = np.random.default_rng((int(seed) ^ 0x5A1A) & 0xFFFFFFFF)
        n = max(30, int(sh * sw / 9000))
        out = np.zeros((sh, sw), np.float32)
        core = np.zeros((sh, sw), np.float32)
        cy_ = rng.uniform(0, sh, n); cx_ = rng.uniform(0, sw, n)
        rr = rng.uniform(sh * 0.02, sh * 0.05, n); rot = rng.uniform(0, 6.28, n)
        for i in range(n):
            r = rr[i]; R = int(r * 2.2)
            y0 = max(0, int(cy_[i] - R)); y1 = min(sh, int(cy_[i] + R))
            x0 = max(0, int(cx_[i] - R)); x1 = min(sw, int(cx_[i] + R))
            if y1 <= y0 or x1 <= x0:
                continue
            gy = (np.arange(y0, y1) - cy_[i])[:, None].astype(np.float32)
            gx = (np.arange(x0, x1) - cx_[i])[None, :].astype(np.float32)
            ang = np.arctan2(gy, gx) + rot[i]
            rad = np.sqrt(gy * gy + gx * gx) / r
            petal = 0.7 + 0.3 * np.cos(ang * 5.0)            # 5-lobed blossom
            blob = np.clip(1.0 - rad / petal, 0, 1) ** 1.4
            out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], blob)
            core[y0:y1, x0:x1] = np.maximum(core[y0:y1, x0:x1], np.clip(1.0 - rad * 2.5, 0, 1))
        if sh != h:
            out = _resize_array(out, h, w); core = _resize_array(core, h, w)
        dusk = np.linspace(0, 1, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)
        dusk = _n01(0.5 * dusk + 0.5 * _noise((h, w), [120], [1.0], seed + 4))
        return out.astype(np.float32), core.astype(np.float32), dusk
    return _cache(key, build)


def paint_flame_pink(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    petal, core, dusk = _sakura_fields((h, w), seed)
    col = np.zeros((h, w, 3), np.float32)
    # dusk gradient: indigo -> warm rose
    indigo = np.array([0.08, 0.03, 0.16], np.float32)
    rose = np.array([0.35, 0.08, 0.2], np.float32)
    col += indigo * (1 - dusk[..., None]) + rose * dusk[..., None]
    pink = np.array([1.0, 0.45, 0.75], np.float32)
    magenta = np.array([1.0, 0.1, 0.55], np.float32)
    col = col + pink * petal[..., None]
    col = col + (magenta - col) * (core[..., None] * 0.7)
    col = col + np.array([1.0, 0.9, 0.95], np.float32) * np.clip(core - 0.7, 0, 1)[..., None]
    return _compose(np.clip(col, 0, 1), paint, mask)


def spec_flame_pink(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    petal, core, dusk = _sakura_fields((h, w), seed)
    air = _n01(_noise((h, w), [40, 90, 180], [0.4, 0.35, 0.25], seed + 111))   # own CC field
    ba, _bb, _bc = _base3((h, w), seed)
    # M = pedestal + blossom-body ignition (straddles mid); R rides the broad dusk
    # gradient; CC rides an independent atmospheric field + a core bloom -> sky,
    # petal and core land in different hue classes.
    M = 90 + 110 * ba + 140 * petal                         # mean ~145, straddles
    R = 45 + 130 * dusk + 40 * (1 - petal)                  # mean ~120, straddles
    CC = 70 + 110 * air + 80 * core
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 18 flame_smoke - SMOKE-AND-FIRE: billowing smoke rolls (curl-warped low-freq)
#     shot through by a few hot fire seams at the base. Motif: large rolling
#     smoke vortices + thin fire seams, not a flame sheet.
# ===========================================================================
def _smoke_fields(shape, seed):
    h, w = _wh(shape)
    key = ("smoke", h, w, int(seed))

    def build():
        rolls = _n01(_noise((h, w), [70, 150, 300], [0.45, 0.35, 0.2], seed))
        wisps = _n01(np.abs(_noise((h, w), [18, 40, 90], [0.4, 0.33, 0.27], seed + 2)))
        smoke = _n01(rolls * 0.6 + wisps * 0.4)
        # fire seams: thin bright ridge where a separate noise crosses a threshold
        seam_n = _noise((h, w), [22, 55], [0.6, 0.4], seed + 7)
        seams = np.clip((np.abs(seam_n) - 0.78) * -8.0 + 1.0, 0, 1)   # thin lines near 0
        seams = np.clip(seams - 0.4, 0, 1) / 0.6
        return smoke.astype(np.float32), seams.astype(np.float32), wisps
    return _cache(key, build)


def paint_flame_smoke(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    smoke, seams, wisps = _smoke_fields((h, w), seed)
    col = np.zeros((h, w, 3), np.float32)
    # smoke value ramp: near-black -> charcoal -> warm ash
    ash = np.clip(smoke, 0, 1)
    dark = np.array([0.05, 0.05, 0.06], np.float32)
    grey = np.array([0.32, 0.3, 0.31], np.float32)
    warm = np.array([0.45, 0.34, 0.26], np.float32)
    col += dark * (1 - ash[..., None]) + grey * ash[..., None]
    col = col + (warm - col) * np.clip(ash - 0.6, 0, 1)[..., None]
    # fire seams burn orange->yellow through the smoke
    col = col + np.array([1.0, 0.4, 0.0], np.float32) * seams[..., None]
    col = col + np.array([0.4, 0.5, 0.2], np.float32) * np.clip(seams - 0.6, 0, 1)[..., None]
    return _compose(np.clip(col, 0, 1), paint, mask)


def spec_flame_smoke(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    smoke, seams, wisps = _smoke_fields((h, w), seed)
    # M = broad smoke value + seam ignition (so M crosses mid, not just sparse
    # seams); R rides wisp detail centered to straddle mid; CC rides an
    # independent pedestal -> seams blaze, smoke field varies, channels decorr.
    ba, bb_, bc = _base3((h, w), seed)
    # smoke is intrinsically soft/low-contrast; give each channel a WIDE
    # independent pedestal so all three genuinely straddle the midline (the
    # combined map needs >=4 hue classes). Seams add the bright fire ignition.
    M = 30 + 180 * ba + 120 * seams                         # wide, mean ~120
    R = 30 + 150 * wisps + 70 * bb_ - 30 * seams            # wide, mean ~120
    CC = 30 + 170 * bc + 50 * seams                         # wide, mean ~120
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 19 flame_tribal - TRIBAL / pinstripe flame: bold flat-color flame cutout with
#     hard knife-edge tongues + a pinstripe outline. Motif: thresholded vector
#     silhouette with a 1px-style stroke, unlike any soft glow.
# ===========================================================================
def _tribal_fields(shape, seed):
    h, w = _wh(shape)
    key = ("tribal", h, w, int(seed))

    def build():
        def f(yy, xx):
            t = np.sin((xx * 0.009 + yy * 0.0022) * np.pi)
            u = np.sin((yy * 0.007 - xx * 0.0018) * np.pi * 1.3)
            v = np.sin((xx * 0.0045 - yy * 0.006) * np.pi * 0.7)
            return 0.5 + 0.5 * (t * 0.45 + u * 0.35 + v * 0.2)
        field = _domain_warp(f, (h, w), seed, amp=34.0, scales=(40, 95), salt=611)
        field = _n01(field)
        # hard cutout silhouette (bold tongues)
        fill = (field > 0.52).astype(np.float32)
        if _CV2:
            fill = _blur(fill, 0.7)
            edge = np.abs(field - 0.52)
            stroke = np.clip(1.0 - edge * 40.0, 0, 1)        # thin pinstripe along the contour
            stroke = _blur(stroke, 0.5)
        else:
            stroke = np.clip(1.0 - np.abs(field - 0.52) * 40.0, 0, 1)
        return fill.astype(np.float32), stroke.astype(np.float32), field
    return _cache(key, build)


def paint_flame_tribal(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    fill, stroke, field = _tribal_fields((h, w), seed)
    col = np.zeros((h, w, 3), np.float32)
    bg = np.array([0.03, 0.02, 0.04], np.float32)            # near-black body
    body = np.array([0.95, 0.12, 0.0], np.float32)           # flat hot-rod red-orange
    col += bg * (1 - fill[..., None]) + body * fill[..., None]
    # crisp gold pinstripe outline
    col = col + np.array([1.0, 0.85, 0.2], np.float32) * stroke[..., None]
    return _compose(np.clip(col, 0, 1), paint, mask)


def spec_flame_tribal(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    fill, stroke, field = _tribal_fields((h, w), seed)
    sheen = _n01(_noise((h, w), [40, 90], [0.6, 0.4], seed + 121))   # own broad CC field
    # M flat-high inside the flame cutout; R rides the smooth field gradient
    # (decorrelated from the binary fill); CC = broad clearcoat sheen (crosses
    # mid) with the pinstripe outline ignited bright on top.
    M = 60 + 165 * fill + 30 * (1 - stroke)
    R = 90 + 140 * _n01(field) + 40 * (1 - fill)
    CC = 60 + 130 * sheen + 130 * stroke
    return _mr_cc(M, R, CC, sm)


# ===========================================================================
# 20 flame_dragon - DRAGON-BREATH cone: a single forced directional jet/cone of
#     fire that fans out with turbulent licks, hottest at a converging throat.
#     Motif: radial cone-jet from a focus point (true directionality), unlike the
#     scattered/abstract fields above. (Cone direction is randomized per seed so
#     it lands varied across UV layouts.)
# ===========================================================================
def _dragon_fields(shape, seed):
    h, w = _wh(shape)
    key = ("dragon", h, w, int(seed))

    def build():
        # smooth cone geometry (sqrt/arctan2) at work res; turbulence at full res.
        cap = min(min(h, w), _WORK_CAP)
        sh = sw = cap; scl = sh / float(h)
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        yy = yy / scl; xx = xx / scl
        rng = np.random.default_rng((int(seed) ^ 0xD2A6) & 0xFFFFFFFF)
        # focus (throat) just outside the frame; jet direction random
        theta = rng.uniform(0, 6.283)
        fy = h * 0.5 - 1.2 * h * np.sin(theta); fx = w * 0.5 - 1.2 * w * np.cos(theta)
        dy = yy - fy; dx = xx - fx
        dist = np.sqrt(dy * dy + dx * dx).astype(np.float32)
        ang = np.arctan2(dy, dx).astype(np.float32)
        da = (ang - theta + np.pi) % (2 * np.pi) - np.pi
        cone = np.clip(1.0 - np.abs(da) / 0.65, 0, 1)
        cone = cone * np.clip(1.0 - dist / (1.5 * max(h, w)), 0, 1)   # fade with distance
        throat = np.clip(1.0 - dist / (0.9 * max(h, w)), 0, 1) * cone  # hottest near throat
        if (sh, sw) != (h, w):
            cone = _resize_array(cone, h, w); throat = _resize_array(throat, h, w)
        turb = _n01(_noise((h, w), [16, 36, 80], [0.4, 0.33, 0.27], seed + 2))   # full-res licks
        licks = _n01(cone * (0.6 + 0.4 * turb))
        return licks.astype(np.float32), _n01(throat), turb
    return _cache(key, build)


def paint_flame_dragon(paint, shape, mask, seed, pm, bb):
    h, w = _wh(shape)
    licks, throat, turb = _dragon_fields((h, w), seed)
    t = np.clip(licks * 0.7 + throat * 0.6, 0, 1)
    # green-throat dragon fire: emerald throat -> orange body -> yellow tips
    stops = np.array([[0.01, 0.0, 0.0], [0.4, 0.05, 0.0], [0.95, 0.35, 0.0],
                      [1.0, 0.8, 0.15], [0.6, 1.0, 0.5]], np.float32)
    n = len(stops) - 1
    tt = t * n; i = np.clip(np.floor(tt).astype(np.int32), 0, n - 1); f = (tt - i)[..., None]
    col = stops[i] * (1 - f) + stops[i + 1] * f
    # emerald spit right at the throat
    col = col + np.array([0.0, 0.6, 0.2], np.float32) * np.clip(throat - 0.6, 0, 1)[..., None]
    return _compose(np.clip(col, 0, 1), paint, mask)


def spec_flame_dragon(shape, seed, sm, base_m, base_r):
    h, w = _wh(shape)
    licks, throat, turb = _dragon_fields((h, w), seed)
    glow = _n01(_noise((h, w), [40, 90, 180], [0.4, 0.35, 0.25], seed + 131))  # own CC base
    # M tracks the jet licks; R rides turbulence grain (separate, straddles mid);
    # CC = broad ambient glow (crosses mid everywhere) + throat ignition -> the
    # off-cone field still varies in hue, the throat blazes glossy.
    M = 55 + 185 * licks + 30 * throat
    R = 95 + 140 * turb + 30 * (1 - licks)
    CC = 60 + 130 * glow + 110 * throat
    return _mr_cc(M, R, CC, sm)
